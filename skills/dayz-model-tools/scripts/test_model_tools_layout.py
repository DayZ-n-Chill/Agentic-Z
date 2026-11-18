"""Static checks for the dayz-model-tools skill. Needs only pytest: no Blender, no py3d.

Every script must parse, SKILL.md must name every shipped script, and every how-to
file SKILL.md names under skills/_shared/models/ must exist, so a script added
later cannot ship undocumented and a renamed how-to file cannot leave a dead link.

Run with: python -m pytest skills/dayz-model-tools/scripts/test_model_tools_layout.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
MODELS_PACK = SKILL_DIR.parent / "_shared" / "models"
SKILL_MD = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def _is_shipped_script(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix in {".py", ".sh"}
        and not path.name.startswith(("test_", "conftest"))
    )


SHIPPED = sorted(p for p in SCRIPTS_DIR.rglob("*") if _is_shipped_script(p) and "__pycache__" not in p.parts)
PY_SCRIPTS = [p for p in SHIPPED if p.suffix == ".py"]


def test_the_skill_ships_scripts():
    assert PY_SCRIPTS, "no scripts found next to this test"


@pytest.mark.parametrize("path", PY_SCRIPTS, ids=lambda p: p.name)
def test_script_parses(path):
    # Several scripts import bpy at module level, so they cannot all be imported here.
    # Parsing still catches a syntax error or a broken copy.
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_skill_md_names_every_script():
    missing = [p.name for p in SHIPPED if f"`{p.name}`" not in SKILL_MD]
    assert not missing, f"SKILL.md does not name these scripts: {missing}"


def test_how_to_files_named_in_skill_md_exist():
    named = set(re.findall(r"`(tools-[\w.-]+\.md)`", SKILL_MD))
    assert named, "SKILL.md names no tools-*.md how-to file"
    missing = sorted(name for name in named if not (MODELS_PACK / name).is_file())
    assert not missing, f"SKILL.md names missing how-to files: {missing}"


def test_every_how_to_file_is_named_in_skill_md():
    on_disk = sorted(p.name for p in MODELS_PACK.glob("tools-*.md"))
    missing = [name for name in on_disk if f"`{name}`" not in SKILL_MD]
    assert not missing, f"SKILL.md does not list these how-to files: {missing}"


def test_skill_md_has_the_path_note_and_frontmatter():
    assert SKILL_MD.startswith("---\nname: dayz-model-tools\n")
    head = SKILL_MD.split("---", 2)[1]
    assert "\ndescription: " in head
    assert "\nargument-hint: " in head
    assert "<!-- skill-dir-note -->" in SKILL_MD
