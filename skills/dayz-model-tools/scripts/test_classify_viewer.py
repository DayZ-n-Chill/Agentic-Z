"""Checks for the ripped car classification viewer: the viewer page, its export script and
their how-to file in the vehicles pack agree on the GLB data contract, and the family B
runbook names five symptom files that exist. The export script runs only inside Blender,
so it is parsed, not imported.

Run with: py -m pytest -q skills/dayz-model-tools/scripts/test_classify_viewer.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VEHICLES = SCRIPTS.parents[1] / "_shared" / "vehicles"
EXPORT_SRC = (SCRIPTS / "export_car_glb.py").read_text(encoding="utf-8")
VIEWER = (SCRIPTS / "classify-viewer" / "index.html").read_text(encoding="utf-8")
VIEWER_DOC = (VEHICLES / "rip-classify-viewer.md").read_text(encoding="utf-8")
RUNBOOK = (VEHICLES / "rip-family-b-runbook.md").read_text(encoding="utf-8")

EXTRAS = ["source_id", "dz_coll", "dz_reason", "dz_review", "dz_movable_group"]


def test_runbook_names_five_symptom_files_that_exist():
    section = RUNBOOK.split("## Symptoms", 1)[1].split("\n## ", 1)[0]
    named = set(re.findall(r"`(symptom-[\w.-]+\.md)`", section))
    assert len(named) == 5
    assert [n for n in named if not (VEHICLES / n).is_file()] == []


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
    assert "GLB_DONE" in EXPORT_SRC, "the how-to file names the GLB_DONE line the script prints"


def test_export_script_and_viewer_use_the_same_collections():
    tree = ast.parse(EXPORT_SRC)
    colls = next(
        ast.literal_eval(n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "COLLS" for t in n.targets)
    )
    colors = VIEWER.split("const COLORS = {", 1)[1].split("}", 1)[0]
    assert set(colls) == set(re.findall(r"(DZ_[A-Z]+):", colors))


def test_viewer_reads_every_extra_the_how_to_documents():
    for extra in EXTRAS:
        assert f"userData.{extra}" in VIEWER, f"index.html never reads the {extra} extra"
        assert f"| `{extra}` |" in VIEWER_DOC, f"rip-classify-viewer.md has no row for {extra}"


def test_viewer_loads_the_three_library_files_the_how_to_names():
    loaded = re.findall(r'<script src="lib/([\w.]+)"></script>', VIEWER)
    assert loaded == ["three.min.js", "GLTFLoader.js", "OrbitControls.js"]
    for name in loaded:
        assert f"`{name}`" in VIEWER_DOC, f"rip-classify-viewer.md does not say to download {name}"
    assert not (SCRIPTS / "classify-viewer" / "lib").exists(), "Three.js is not shipped in this repo"


def test_viewer_exposes_the_deltas_the_how_to_describes():
    assert "window.DZ_DELTAS = deltas" in VIEWER
    assert "window.DZ_DELTAS" in VIEWER_DOC
