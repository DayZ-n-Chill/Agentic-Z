"""Static checks for the three mod-development reference skills: dayz-mod-workflow,
dayz-mod-dev and dayz-feature-spec. Frontmatter, the path note, the references table
against the files in references/, and the error index against the error catalog.

Run with: py -m pytest skills/dayz-mod-workflow
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent
SKILL_NAMES = ["dayz-mod-workflow", "dayz-mod-dev", "dayz-feature-spec"]
SPANISH_RE = re.compile(r"\b(?:Úsala|cuando|según|Ejes|Plantilla|Reglas|Referencia cruzada|Mantenimiento|Caso real)\b")
MACHINE_PATH_RE = re.compile(r"[A-Za-z]:\\Users\\|/home/\w+|<vault>|<claude-home>")


def _skill_text(name: str) -> str:
    return (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")


def _references(name: str) -> list[Path]:
    folder = SKILLS_DIR / name / "references"
    return sorted(p for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []


def _frontmatter(text: str) -> dict[str, str]:
    out = {}
    for line in text.split("---", 2)[1].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"')
    return out


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_frontmatter_names_the_folder_and_describes_the_skill(name):
    front = _frontmatter(_skill_text(name))
    assert front["name"] == name
    assert 0 < len(front["description"]) <= 1024


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_skill_has_the_path_note(name):
    assert "<!-- skill-dir-note -->" in _skill_text(name)


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_every_reference_the_skill_names_exists(name):
    named = set(re.findall(r"`references/([\w.-]+\.md)`", _skill_text(name)))
    own = {p.name for p in _references(name)}
    # A skill may also name a reference file of a sibling skill ("dayz-build-pbo (references/x.md)");
    # only files of this skill's own folder are checked for the table, and a name that is not its own
    # must be said, on the same line, to belong to another skill.
    for ref in sorted(named - own):
        lines = [line for line in _skill_text(name).splitlines() if f"`references/{ref}`" in line]
        assert all(re.search(r"`(?:dayz|enforce|rigorous|systematic)-[a-z-]+`", line) for line in lines), (
            f"{name}/SKILL.md names references/{ref}, which is not in its folder and names no other skill"
        )


@pytest.mark.parametrize("name", [n for n in SKILL_NAMES if n != "dayz-mod-dev"])
def test_every_reference_file_is_in_the_references_table(name):
    text = _skill_text(name)
    table = text.split("## References", 1)[1].split("\n## ", 1)[0]
    listed = set(re.findall(r"`references/([\w.-]+)`", table))
    unlisted = sorted(p.name for p in _references(name) if p.name not in listed)
    assert not unlisted, f"{name}: reference files missing from the References table: {unlisted}"


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_each_reference_opens_with_a_title_and_what_it_covers(name):
    for path in _references(name):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# "), f"{path.name} must open with a title"
        assert lines[1] == "" and lines[2].strip(), f"{path.name} must say what it covers under the title"


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_files_are_english_and_have_no_machine_paths(name):
    for path in [SKILLS_DIR / name / "SKILL.md", *_references(name)]:
        text = path.read_text(encoding="utf-8")
        if path.name == "SKILL.md":
            # Spanish trigger phrases are allowed in the description only.
            text = text.split("---", 2)[2]
        assert not SPANISH_RE.search(text), f"{path.name} still holds Spanish text"
        assert not MACHINE_PATH_RE.search(text), f"{path.name} holds a machine-specific path"


def test_error_index_matches_the_catalog():
    index = set(re.findall(r"^- \*\*(E\d\d)\*\*", _skill_text("dayz-mod-workflow"), re.MULTILINE))
    catalog_text = (SKILLS_DIR / "dayz-mod-workflow" / "references" / "error-catalog.md").read_text(encoding="utf-8")
    catalog = set(re.findall(r"^\| (E\d\d) \|", catalog_text, re.MULTILINE))
    assert index == catalog == {f"E{n:02d}" for n in range(1, 36)}


def test_checklists_name_only_catalogued_errors():
    catalog = {f"E{n:02d}" for n in range(1, 36)}
    folder = SKILLS_DIR / "dayz-mod-workflow" / "references"
    for path in sorted(folder.glob("*.md")):
        used = set(re.findall(r"\bE(\d\d)\b", path.read_text(encoding="utf-8")))
        unknown = sorted(f"E{n}" for n in used if f"E{n}" not in catalog)
        assert not unknown, f"{path.name} names errors missing from the catalog: {unknown}"
