"""Static checks for the uv-clean-atlas skill. No Blender needed.

Every script must parse, and SKILL.md must name every script and every reference
file, so a file added later cannot ship undocumented.

Run with: python -m pytest skills/uv-clean-atlas/scripts/test_uv_clean_atlas_layout.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
REFERENCES_DIR = SKILL_DIR / "references"
SKILL_MD = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def _is_shipped_script(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix in {".py", ".sh"}
        and not path.name.startswith(("test_", "conftest"))
    )


SHIPPED = sorted(p for p in SCRIPTS_DIR.iterdir() if _is_shipped_script(p))
PY_SCRIPTS = [p for p in SHIPPED if p.suffix == ".py"]


def test_the_skill_ships_scripts():
    assert PY_SCRIPTS, "no scripts found next to this test"


@pytest.mark.parametrize("path", PY_SCRIPTS, ids=lambda p: p.name)
def test_script_parses(path):
    # The scripts import bpy at module level, so they cannot be imported here.
    # Parsing still catches a syntax error or a broken copy.
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_skill_md_names_every_script():
    missing = [p.name for p in SHIPPED if f"`{p.name}`" not in SKILL_MD]
    assert not missing, f"SKILL.md does not name these scripts: {missing}"


def test_skill_md_names_every_reference_file():
    on_disk = sorted(p.name for p in REFERENCES_DIR.glob("*.md"))
    assert on_disk, "references/ holds no .md files"
    missing = [name for name in on_disk if f"`references/{name}`" not in SKILL_MD]
    assert not missing, f"SKILL.md does not list these reference files: {missing}"


def test_reference_files_named_in_skill_md_exist():
    named = set(re.findall(r"`references/([\w.-]+\.md)`", SKILL_MD))
    missing = sorted(name for name in named if not (REFERENCES_DIR / name).is_file())
    assert not missing, f"SKILL.md names missing reference files: {missing}"


def test_skill_md_has_the_path_note_and_frontmatter():
    assert SKILL_MD.startswith("---\nname: uv-clean-atlas\n")
    assert "\ndescription: " in SKILL_MD.split("---", 2)[1]
    assert "<!-- skill-dir-note -->" in SKILL_MD
