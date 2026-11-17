"""Checks for the rip-vehicle-import skill: SKILL.md and references/ list the same files,
and the classification viewer, its export script and their reference file agree on the
GLB data contract. The export script itself runs only inside Blender, so it is parsed, not imported.

Run with: python -m pytest -q skills/rip-vehicle-import
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parent
SKILL_MD = (SKILL / "SKILL.md").read_text(encoding="utf-8")
EXPORT_SRC = (SKILL / "export_car_glb.py").read_text(encoding="utf-8")
VIEWER = (SKILL / "classify-viewer" / "index.html").read_text(encoding="utf-8")
VIEWER_DOC = (SKILL / "references" / "classify-viewer.md").read_text(encoding="utf-8")

EXTRAS = ["source_id", "dz_coll", "dz_reason", "dz_review", "dz_movable_group"]


def test_skill_md_and_references_folder_list_the_same_files():
    named = set(re.findall(r"`references/([\w.-]+\.md)`", SKILL_MD))
    on_disk = {p.name for p in (SKILL / "references").glob("*.md")}
    assert named == on_disk, (
        f"named in SKILL.md but missing: {sorted(named - on_disk)}; "
        f"in references/ but not named in SKILL.md: {sorted(on_disk - named)}"
    )


def test_every_cookbook_is_in_the_symptom_index():
    index = SKILL_MD.split("## Symptom to cookbook index", 1)[1].split("\n## ", 1)[0]
    cookbooks = {p.name for p in (SKILL / "references").glob("cookbook-*.md")}
    assert set(re.findall(r"`references/(cookbook-[\w.-]+\.md)`", index)) == cookbooks


def _string_constants(tree: ast.AST) -> set[str]:
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def test_export_script_parses_and_stamps_the_extras_it_owns():
    tree = ast.parse(EXPORT_SRC)
    strings = _string_constants(tree)
    # The script stamps these two itself; the other extras are custom properties
    # that already exist on the objects and reach the GLB through export_extras.
    assert {"dz_coll", "dz_reason", "dz_exclude_reason"} <= strings
    keywords = {k.arg for n in ast.walk(tree) if isinstance(n, ast.Call) for k in n.keywords}
    assert "export_extras" in keywords
    assert "GLB_DONE" in EXPORT_SRC, "the reference file names the GLB_DONE line the script prints"


def test_export_script_and_viewer_use_the_same_collections():
    tree = ast.parse(EXPORT_SRC)
    colls = next(
        ast.literal_eval(n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "COLLS" for t in n.targets)
    )
    colors = VIEWER.split("const COLORS = {", 1)[1].split("}", 1)[0]
    assert set(colls) == set(re.findall(r"(DZ_[A-Z]+):", colors))


def test_viewer_reads_every_extra_the_reference_documents():
    for extra in EXTRAS:
        assert f"userData.{extra}" in VIEWER, f"index.html never reads the {extra} extra"
        assert f"| `{extra}` |" in VIEWER_DOC, f"classify-viewer.md has no row for {extra}"


def test_viewer_loads_the_three_library_files_the_reference_names():
    loaded = re.findall(r'<script src="lib/([\w.]+)"></script>', VIEWER)
    assert loaded == ["three.min.js", "GLTFLoader.js", "OrbitControls.js"]
    for name in loaded:
        assert f"`{name}`" in VIEWER_DOC, f"classify-viewer.md does not say to download {name}"
    assert not (SKILL / "classify-viewer" / "lib").exists(), "Three.js is not shipped in this repo"


def test_viewer_exposes_the_deltas_the_reference_describes():
    assert "window.DZ_DELTAS = deltas" in VIEWER
    assert "window.DZ_DELTAS" in VIEWER_DOC
