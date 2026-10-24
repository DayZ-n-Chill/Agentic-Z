"""Checks on the dayz-particles skill docs: the client-only guard matches vanilla, and every
reference file opens with a contents list that matches its headings.

Run with: py -m pytest scripts/dev/test_particles_docs.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "dayz-particles"
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


@pytest.mark.parametrize("ref", REFERENCES, ids=lambda p: p.name)
def test_reference_has_contents_list(ref: Path) -> None:
    text = ref.read_text(encoding="utf-8")
    assert "## Contents" in text, f"{ref.name} has no contents list"
    toc = text.split("## Contents", 1)[1].split("\n## ", 1)[0]
    links = re.findall(r"- \[(.+?)\]\(#(.+?)\)", toc)
    headings = _headings(text)
    assert [h for h, _ in links] == headings
    assert [a for _, a in links] == [_slug(h) for h in headings]
