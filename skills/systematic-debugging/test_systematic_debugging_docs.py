"""Static checks for the systematic-debugging skill: frontmatter, and the "What to read" table
against the files in references/.

Run with: py -m pytest skills/systematic-debugging
"""
from __future__ import annotations

import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
REFERENCES = sorted(p for p in (SKILL_DIR / "references").iterdir() if p.is_file())


def _frontmatter() -> dict[str, str]:
    block = SKILL.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"')
    return out


def test_frontmatter_names_the_folder_and_describes_the_skill():
    front = _frontmatter()
    assert front["name"] == SKILL_DIR.name
    assert 0 < len(front["description"]) <= 1024


def test_skill_has_the_path_note():
    assert "<!-- skill-dir-note -->" in SKILL


def test_every_reference_the_skill_names_exists():
    named = set(re.findall(r"`references/([\w.-]+)`", SKILL))
    assert named, "SKILL.md must name its reference files"
    missing = sorted(name for name in named if not (SKILL_DIR / "references" / name).is_file())
    assert not missing, f"SKILL.md names missing reference files: {missing}"


def test_every_reference_file_is_in_the_what_to_read_table():
    table = SKILL.split("## What to read", 1)[1].split("\n## ", 1)[0]
    listed = set(re.findall(r"`references/([\w.-]+)`", table))
    unlisted = sorted(p.name for p in REFERENCES if p.name not in listed)
    assert not unlisted, f"reference files missing from the What to read table: {unlisted}"


def test_each_reference_note_opens_with_a_title_and_what_it_covers():
    for path in REFERENCES:
        if path.suffix != ".md":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# "), f"{path.name} must open with a title"
        assert lines[1] == "" and lines[2].strip(), f"{path.name} must say what it covers under the title"
