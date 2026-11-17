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


@pytest.mark.parametrize("n", [3, 4, 5, 8])
def test_excised_speck_cannot_overlap_itself(n):
    # SKILL.md stage 5: excised offenders become specks so the run can end at SAT = 0.
    # The gate tests fan triangles of one face against each other, so the corners
    # must form a convex polygon in loop order (no bowtie).
    speck_corners = _lift_function(PIPELINE, "speck_corners")
    sat_tri_overlap = _lift_function("sat_gate.py", "sat_tri_overlap")
    p = speck_corners(2.0, 2.0, n)
    fan = [(p[0], p[i], p[i + 1]) for i in range(1, n - 1)]
    for i in range(len(fan)):
        a, b, c = fan[i]
        assert (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]) > 1e-12
        for j in range(i + 1, len(fan)):
            assert not sat_tri_overlap(fan[i], fan[j]), (n, i, j)


def test_shelf_pack_pca_angle_finds_the_long_axis():
    pca_angle = _lift_function("uv_shelf_pack.py", "_pca_angle")
    angle, center = pca_angle([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)])
    assert angle == pytest.approx(math.pi / 4)
    assert center == pytest.approx((1.5, 1.5))
    angle, _ = pca_angle([(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (0.0, 1.0)])
    assert angle == pytest.approx(0.0)


def _lift_shelf_dry(panels, strips, specks):
    """Return shelf_pack's inner dry(S) bound to the given island boxes."""
    tree = ast.parse(_source("uv_shelf_pack.py"), filename="uv_shelf_pack.py")
    outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "shelf_pack")
    dry = next(n for n in outer.body if isinstance(n, ast.FunctionDef) and n.name == "dry")
    total = sum(e["area"] for e in panels) or 1e-12
    namespace = {"math": math, "panels": panels, "strips": strips, "specks": specks,
                 "total_panel_area": total, "m": math.sqrt(total) * 0.02}
    exec(compile(ast.Module(body=[dry], type_ignores=[]), "uv_shelf_pack.py", "exec"), namespace)
    return namespace["dry"]


def test_shelf_pack_strips_clear_a_panel_wider_than_the_shelf():
    # A row always takes its first panel, even one wider than the shelf width S;
    # the strip column must start right of that panel, not at S.
    def box(w, h, kind):
        return {"w": w, "h": h, "area": w * h, "kind": kind}

    panels = [box(3.871, 0.887, "panel"), box(3.495, 0.942, "panel"), box(2.652, 0.74, "panel"),
              box(0.918, 0.612, "panel"), box(0.298, 0.071, "panel")]
    strips = [box(0.05, 0.6, "strip")]
    specks = [box(0.01, 0.01, "speck")]
    dry = _lift_shelf_dry(panels, strips, specks)
    pos, scale, W, H = dry(3.257)
    rects = [(pos[id(e)][0], pos[id(e)][1], e["w"] * scale.get(id(e), 1.0),
              e["h"] * scale.get(id(e), 1.0)) for e in panels + strips + specks]
    for i in range(len(rects)):
        x0, y0, w0, h0 = rects[i]
        assert x0 + w0 <= W + 1e-9 and y0 + h0 <= H + 1e-9
        for j in range(i + 1, len(rects)):
            x1, y1, w1, h1 = rects[j]
            assert x0 + w0 <= x1 or x1 + w1 <= x0 or y0 + h0 <= y1 or y1 + h1 <= y0, (i, j)


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


def test_no_machine_paths_in_the_pipeline_scripts():
    for name in ["sat_gate.py", PIPELINE, *[f"{m}.py" for m in STAGE_MODULES]]:
        text = _source(name)
        assert not re.search(r"[A-Za-z]:\\|/home/", text), name
