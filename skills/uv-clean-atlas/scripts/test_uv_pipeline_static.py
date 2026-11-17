"""Checks for the Track A pipeline scripts that need no Blender.

The scripts import bpy, bmesh or mathutils at module level, so they cannot be
imported under plain Python. The pure functions are lifted out of the source
with ast and run on their own; the rest is checked as text against SKILL.md.

Run with: python -m pytest skills/uv-clean-atlas/scripts/test_uv_pipeline_static.py
"""
from __future__ import annotations

import ast
import math
import re
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_MD = (SCRIPTS_DIR.parent / "SKILL.md").read_text(encoding="utf-8")

PIPELINE = "uv_clean_atlas.py"
STAGE_MODULES = ["uv_view_charts", "uv_straighten", "uv_shelf_pack", "uv_metrics"]


def _source(name: str) -> str:
    return (SCRIPTS_DIR / name).read_text(encoding="utf-8")


def _lift_function(script: str, func: str):
    """Return one top-level function of a script without importing the script."""
    tree = ast.parse(_source(script), filename=script)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func:
            namespace = {"math": math}
            exec(compile(ast.Module(body=[node], type_ignores=[]), script, "exec"), namespace)
            return namespace[func]
    raise AssertionError(f"{script} has no top-level function {func}")


UNIT = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))


@pytest.mark.parametrize(
    "other, expected",
    [
        (((0.2, 0.2), (1.2, 0.2), (0.2, 1.2)), True),   # shifted copy, interiors cross
        (((0.1, 0.1), (0.3, 0.1), (0.1, 0.3)), True),   # fully inside
        (((2.0, 2.0), (3.0, 2.0), (2.0, 3.0)), False),  # far apart
        (((1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), False),  # shares the hypotenuse only
        (((1.0, 0.0), (2.0, 0.0), (1.0, 1.0)), False),  # touches at one corner only
    ],
)
def test_sat_gate_overlap_test(other, expected):
    sat_tri_overlap = _lift_function("sat_gate.py", "sat_tri_overlap")
    assert sat_tri_overlap(UNIT, other) is expected
    assert sat_tri_overlap(other, UNIT) is expected


def test_sat_gate_skips_collapsed_triangles_at_the_threshold_skill_md_states():
    # SKILL.md tells the reader the gate drops triangles of UV area 1e-14 or less.
    assert "if area > 1e-14:" in _source("sat_gate.py")
    assert "`1e-14` or less" in SKILL_MD


def test_shelf_pack_pca_angle_finds_the_long_axis():
    pca_angle = _lift_function("uv_shelf_pack.py", "_pca_angle")
    angle, center = pca_angle([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)])
    assert angle == pytest.approx(math.pi / 4)
    assert center == pytest.approx((1.5, 1.5))
    angle, _ = pca_angle([(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (0.0, 1.0)])
    assert angle == pytest.approx(0.0)


def test_pipeline_imports_every_stage_module_and_each_is_shipped():
    imported = {
        alias.name
        for node in ast.walk(ast.parse(_source(PIPELINE)))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    for module in STAGE_MODULES:
        assert module in imported, f"{PIPELINE} no longer imports {module}"
        assert (SCRIPTS_DIR / f"{module}.py").is_file(), f"{module}.py is not shipped"


def test_log_labels_in_skill_md_are_printed_by_the_scripts():
    block = SKILL_MD.split("## Reading the output", 1)[1].split("```", 2)[1]
    labels = set(re.findall(r"^([A-Z][A-Z_]+)[:\[]", block, flags=re.MULTILINE))
    assert labels, "no log labels found under 'Reading the output'"
    printed = _source(PIPELINE) + _source("uv_metrics.py")
    # sat_finish(label) prints f"SAT_{label}: ...", so that label is built at run time.
    for built in re.findall(r'sat_finish\("([A-Z_]+)"\)', printed):
        printed += f"\nSAT_{built}"
    missing = sorted(label for label in labels if label not in printed)
    assert not missing, f"SKILL.md shows log labels the scripts do not print: {missing}"


@pytest.mark.parametrize(
    "script, needle",
    [
        ("uv_view_charts.py", "math.radians(70)"),
        ("uv_view_charts.py", "math.radians(125)"),
        ("uv_view_charts.py", "cone_fallback=math.radians(100)"),
        ("uv_view_charts.py", "frag_limit=6"),
        ("uv_straighten.py", "cap = 0.35 * local"),
        ("uv_shelf_pack.py", "STRIP_ASPECT = 6.0"),
        (PIPELINE, "EXCISE_CAP = max(40,"),
        (PIPELINE, "minority > 0.05"),
        (PIPELINE, "hits[c] / n > 0.03"),
    ],
)
def test_tuning_values_skill_md_quotes_are_still_in_the_code(script, needle):
    assert needle in _source(script), f"{script} no longer holds {needle!r}; update SKILL.md"


def test_no_machine_or_project_paths_in_the_pipeline_scripts():
    for name in ["sat_gate.py", PIPELINE, *[f"{m}.py" for m in STAGE_MODULES]]:
        text = _source(name)
        assert not re.search(r"[A-Za-z]:\\|LFQuad_dev|/home/", text), name
