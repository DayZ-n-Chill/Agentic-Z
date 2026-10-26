"""Checks on the dayz-particles skill docs: the client-only guard matches vanilla, and every
reference file opens with a contents list that matches its headings.

Run with: py -m pytest scripts/dev/test_particles_docs.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[2] / "skills" / "dayz-particles"
DOCS = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]
REFERENCES = sorted((SKILL / "references").glob("*.md"))


def _code_lines(text: str) -> list[str]:
    """Lines inside fenced code blocks."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif fenced:
            out.append(line)
    return out


def _headings(text: str) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## ") and line != "## Contents":
            out.append(line[3:])
    return out


def _slug(heading: str) -> str:
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_guard_is_headless_or_dedicated(doc: Path) -> None:
    # Vanilla gates particles on IsHeadlessOrDedicatedServer()
    # (P:\scripts\3_Game\Particles\ParticleManager\ParticleManager.c:65); a bare
    # IsDedicatedServer() guard lets particle code run on a headless client.
    text = doc.read_text(encoding="utf-8")
    bad = [ln for ln in _code_lines(text) if re.search(r"(?<!Headless)(?<!Or)IsDedicatedServer\(", ln)]
    assert not bad, f"{doc.name} guards with IsDedicatedServer(): {bad}"
    if doc.name == "SKILL.md":
        assert "IsHeadlessOrDedicatedServer()" in text


def test_integration_patterns_use_one_client_gate() -> None:
    # SKILL.md Pitfall 1 says every pattern guards with IsHeadlessOrDedicatedServer(), but
    # Pattern D gated on IsClient() || !IsMultiplayer(), so pasted code used a different check.
    text = (SKILL / "references" / "integration-patterns.md").read_text(encoding="utf-8")
    code = _code_lines(text)
    bad = [ln for ln in code if re.search(r"\bIsClient\(|\bIsMultiplayer\(", ln)]
    assert not bad, f"integration-patterns.md gates with another client check: {bad}"
    assert any("IsHeadlessOrDedicatedServer()" in ln for ln in code)


@pytest.mark.parametrize("ref", REFERENCES, ids=lambda p: p.name)
def test_reference_has_contents_list(ref: Path) -> None:
    text = ref.read_text(encoding="utf-8")
    assert "## Contents" in text, f"{ref.name} has no contents list"
    toc = text.split("## Contents", 1)[1].split("\n## ", 1)[0]
    links = re.findall(r"- \[(.+?)\]\(#(.+?)\)", toc)
    headings = _headings(text)
    assert [h for h, _ in links] == headings
    assert [a for _, a in links] == [_slug(h) for h in headings]


INTEGRATION = SKILL / "references" / "integration-patterns.md"
PARTICLE_LIST = Path("P:/scripts/3_game/particles/particlelist.c")
PTC_DIR = Path("P:/graphics/particles")


def _undefined_mymod_names(code: str) -> list[str]:
    """MyMod_ base classes and methods that the code uses or overrides but never defines.

    Code pasted from a pattern that extends an undefined MyMod_DeviceBase, or overrides
    a MyMod_ hook no class declares, does not compile.
    """
    code = re.sub(r"//[^\n]*", "", code)
    defined = set(re.findall(r"\bclass\s+(MyMod_\w+)", code))
    defined |= {
        m.group(1)
        for m in re.finditer(r"^\s*(?:(?:protected|private|static)\s+)*\w+\s+(MyMod_\w+)\s*\(", code, re.MULTILINE)
        if not re.match(r"\s*override\b", m.group(0))
    }
    used = set(re.findall(r"(?:\bextends\s+|:\s*)(MyMod_\w+)", code))
    used |= set(re.findall(r"\boverride\s+\w+\s+(MyMod_\w+)\s*\(", code))
    used |= set(re.findall(r"\b(MyMod_\w+)\s*\(", code))
    return sorted(used - defined)


def test_undefined_mymod_check_catches_an_undefined_base_and_hook() -> None:
    code = "class MyMod_Sprinkler : MyMod_DeviceBase\n{\n    override void MyMod_OnVarSync()\n    {\n    }\n};\n"
    assert _undefined_mymod_names(code) == ["MyMod_DeviceBase", "MyMod_OnVarSync"]


def test_integration_patterns_define_every_mymod_name() -> None:
    # Patterns B to D extended MyMod_DeviceBase and overrode MyMod_OnVarSync and
    # MyMod_OnPowerCut, none of which the skill defined, so pasted code failed to compile.
    code = "\n".join(_code_lines(INTEGRATION.read_text(encoding="utf-8")))
    assert _undefined_mymod_names(code) == []


def _registered_particles() -> dict[str, str]:
    text = PARTICLE_LIST.read_text(encoding="utf-8", errors="replace")
    return dict(re.findall(r"static const int (\w+)\s*=\s*RegisterParticle\(\"([\w/]+)\"\)", text))


@pytest.mark.skipif(not PARTICLE_LIST.is_file(), reason="P: is not mounted with vanilla scripts")
def test_integration_particles_point_at_real_effects() -> None:
    # The device table recommended CAMP_STEAM_EXTINGUISH_START for a steam vent, but vanilla
    # registers it as "default_01", the placeholder particle (particlelist.c:35).
    text = INTEGRATION.read_text(encoding="utf-8")
    registered = _registered_particles()
    assert registered.get("CAMP_STEAM_EXTINGUISH_START") == "default_01"
    table = [ln for ln in text.splitlines() if ln.startswith("| ") and not ln.startswith("| Device")]
    assert table, "device table not found"
    assert not [ln for ln in table if "TBD" in ln], "device table has an untested row"
    constants = {m for ln in table for m in re.findall(r"`([A-Z][A-Z0-9_]+)`", ln.split("|")[3])}
    constants |= set(re.findall(r"ParticleList\.([A-Z][A-Z0-9_]+)", "\n".join(_code_lines(text))))
    constants.discard("MYMOD_WATER_SPRAY")  # the mod's own particle, registered in SKILL.md
    assert constants
    bad = []
    for name in sorted(constants):
        ptc = registered.get(name)
        if ptc is None or ptc == "default_01" or not (PTC_DIR / f"{ptc}.ptc").is_file():
            bad.append(f"{name} -> {ptc}")
    assert not bad, f"particles that are not a real vanilla effect: {bad}"


@pytest.mark.skipif(not PARTICLE_LIST.is_file(), reason="P: is not mounted with vanilla scripts")
def test_integration_overrides_are_vanilla_methods() -> None:
    # Every non-MyMod override must exist on EntityAI or ItemBase, the classes the patterns extend.
    vanilla = "".join(
        Path(p).read_text(encoding="utf-8", errors="replace")
        for p in ("P:/scripts/3_game/entities/entityai.c", "P:/scripts/4_world/entities/itembase.c")
    )
    code = "\n".join(_code_lines(INTEGRATION.read_text(encoding="utf-8")))
    overrides = set(re.findall(r"\boverride\s+\w+\s+(\w+)\s*\(", code))
    assert overrides
    missing = [n for n in sorted(overrides) if not re.search(rf"\bvoid\s+{n}\s*\(", vanilla)]
    assert not missing, f"overrides with no vanilla method: {missing}"
