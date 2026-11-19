"""Checks for the pure-Python parts of project_atlas.py. No Blender needed.

project_atlas.py imports bpy, bmesh and mathutils at module level and only its
main() uses a real scene. The fixture below loads the file with stand-in
modules when Blender's are missing, then removes the stand-ins again so no
other test sees them. The tests cover the argument parser, the placement
override validator, the exact triangle clipping and the small helpers.

Run with: python -m pytest skills/dayz-model-tools/scripts/test_project_atlas.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "project_atlas.py"
BLENDER_MODULES = ("bpy", "bmesh", "mathutils", "mathutils.bvhtree")


class _Vector:
    """Stand-in for mathutils.Vector: the few 3D operations the camera table uses."""

    def __init__(self, values=(0.0, 0.0, 0.0)):
        self.xyz = [float(v) for v in values]

    def __iter__(self):
        return iter(self.xyz)

    def __getitem__(self, index):
        return self.xyz[index]

    def __neg__(self):
        return _Vector(-v for v in self.xyz)

    def dot(self, other):
        return sum(a * b for a, b in zip(self.xyz, other))

    def cross(self, other):
        ax, ay, az = self.xyz
        bx, by, bz = other
        return _Vector((ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx))

    def normalize(self):
        length = self.dot(self) ** 0.5
        if length:
            self.xyz = [v / length for v in self.xyz]


def _stand_in_modules():
    mathutils = types.ModuleType("mathutils")
    mathutils.Vector = _Vector
    bvhtree = types.ModuleType("mathutils.bvhtree")
    bvhtree.BVHTree = type("BVHTree", (), {})
    mathutils.bvhtree = bvhtree
    return {
        "bpy": types.ModuleType("bpy"),
        "bmesh": types.ModuleType("bmesh"),
        "mathutils": mathutils,
        "mathutils.bvhtree": bvhtree,
    }


@pytest.fixture(scope="module")
def atlas():
    saved = {name: sys.modules.get(name) for name in BLENDER_MODULES}
    try:
        import bpy  # noqa: F401  (real Blender: load the script as it is)
    except ImportError:
        sys.modules.update(_stand_in_modules())
    try:
        spec = importlib.util.spec_from_file_location("uvca_project_atlas", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module


# --- command line -----------------------------------------------------------

def test_parse_two_positionals(atlas):
    assert atlas.parse_project_args(["SMOKE", "out"]) == {
        "assignment": "SMOKE", "outdir": "out", "placement_override": None,
    }


def test_parse_placement_override_in_any_position(atlas):
    parsed = atlas.parse_project_args(["--placement-override", "po.json", "a.json", "out_g10"])
    assert parsed == {
        "assignment": "a.json", "outdir": "out_g10", "placement_override": "po.json",
    }


@pytest.mark.parametrize("args, message", [
    ([], "usage:"),
    (["only_one"], "usage:"),
    (["a", "b", "c"], "usage:"),
    (["a", "b", "--verbose"], "unknown option"),
    (["a", "b", "--placement-override"], "requires a JSON path"),
    (["a", "b", "--placement-override", "--x"], "requires a JSON path"),
    (["a", "b", "--placement-override", "1.json", "--placement-override", "2.json"], "only once"),
])
def test_parse_rejects_bad_command_lines(atlas, args, message):
    with pytest.raises(SystemExit) as caught:
        atlas.parse_project_args(args)
    assert message in str(caught.value)


def test_argv_payload_takes_what_follows_the_double_dash(atlas, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["blender", "-b", "x.blend", "--python", "p.py", "--", "SMOKE", "out"])
    assert atlas.argv_payload() == ["SMOKE", "out"]


# --- placement override -----------------------------------------------------

BASE_ISLANDS = [
    {"id": "S02:n+", "placement_center_uv": (0.25, 0.5)},
    {"id": "S03:n-", "placement_center_uv": (0.75, 0.5)},
]


def _override(**changes):
    payload = {
        "source": "uv_arranger",
        "base": "out_g10",
        "atlas": "A",
        "uv_space": [0.0, 0.0, 1.0, 1.0],
        "islands": [
            {"id": "S02:n+", "placement_center_uv": [0.30, 0.5], "delta_uv": [0.05, 0.0]},
            {"id": "S03:n-", "placement_center_uv": [0.75, 0.4], "delta_uv": [0.0, -0.1]},
        ],
    }
    payload.update(changes)
    return payload


def test_valid_override_is_accepted(atlas):
    result = atlas.validate_placement_override(_override(), BASE_ISLANDS)
    assert result["island_count"] == 2
    assert result["by_id"]["S02:n+"]["delta_uv"] == [0.05, 0.0]
    assert result["max_center_consistency_error_uv"] <= 2e-9


@pytest.mark.parametrize("payload, message", [
    ([], "root must be a JSON object"),
    ({"source": "uv_arranger"}, "root keys must be exactly"),
    (_override(base="out_g9"), "base must equal"),
    (_override(islands="none"), "islands must be a JSON array"),
    (_override(islands=[{"id": "S02:n+"}]), "keys must be exactly"),
    (_override(islands=[
        {"id": "S02:n+", "placement_center_uv": [0.30, 0.5], "delta_uv": [0.05, 0.0]},
        {"id": "S02:n+", "placement_center_uv": [0.30, 0.5], "delta_uv": [0.05, 0.0]},
    ]), "duplicate placement override island id"),
    (_override(islands=[
        {"id": "S99:n+", "placement_center_uv": [0.30, 0.5], "delta_uv": [0.05, 0.0]},
    ]), "unknown placement override island id"),
    (_override(islands=[
        {"id": "S02:n+", "placement_center_uv": [0.30, 0.5], "delta_uv": [0.05, 0.0]},
    ]), "must match base G10 exactly"),
    (_override(islands=[
        {"id": "S02:n+", "placement_center_uv": [0.40, 0.5], "delta_uv": [0.05, 0.0]},
        {"id": "S03:n-", "placement_center_uv": [0.75, 0.4], "delta_uv": [0.0, -0.1]},
    ]), "center/delta mismatch"),
    (_override(islands=[
        {"id": "S02:n+", "placement_center_uv": [0.30, True], "delta_uv": [0.05, 0.0]},
        {"id": "S03:n-", "placement_center_uv": [0.75, 0.4], "delta_uv": [0.0, -0.1]},
    ]), "must contain only numbers"),
    (_override(islands=[
        {"id": "S02:n+", "placement_center_uv": [0.30, 0.5], "delta_uv": [float("inf"), 0.0]},
        {"id": "S03:n-", "placement_center_uv": [0.75, 0.4], "delta_uv": [0.0, -0.1]},
    ]), "only finite numbers"),
])
def test_bad_override_is_rejected(atlas, payload, message):
    with pytest.raises(ValueError) as caught:
        atlas.validate_placement_override(payload, BASE_ISLANDS)
    assert message in str(caught.value)


# --- geometry helpers -------------------------------------------------------

UNIT_TRIANGLE = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]


def test_tri_area_2d(atlas):
    assert atlas.tri_area_2d(*UNIT_TRIANGLE) == pytest.approx(0.5)
    assert atlas.tri_area_2d((0, 0), (1, 1), (2, 2)) == 0.0


def test_triangle_clipped_by_itself_keeps_its_area(atlas):
    assert atlas._g10_triangle_intersection_area(UNIT_TRIANGLE, UNIT_TRIANGLE) == pytest.approx(0.5)
    # The clip triangle's winding must not matter.
    assert atlas._g10_triangle_intersection_area(UNIT_TRIANGLE, UNIT_TRIANGLE[::-1]) == pytest.approx(0.5)


def test_partial_overlap_area_is_exact(atlas):
    # The second triangle is the first moved by (0.5, 0); they share the
    # triangle (0.5,0) (1,0) (0.5,0.5), whose area is 0.125.
    moved = [(0.5, 0.0), (1.5, 0.0), (0.5, 1.0)]
    assert atlas._g10_triangle_intersection_area(UNIT_TRIANGLE, moved) == pytest.approx(0.125)


def test_edge_contact_and_disjoint_triangles_have_zero_area(atlas):
    mirrored = [(1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]  # shares only the diagonal
    far = [(5.0, 5.0), (6.0, 5.0), (5.0, 6.0)]
    assert atlas._g10_triangle_intersection_area(UNIT_TRIANGLE, mirrored) == pytest.approx(0.0, abs=1e-12)
    assert atlas._g10_triangle_intersection_area(UNIT_TRIANGLE, far) == 0.0


def test_useful_texels_is_sqrt_of_occupancy_times_resolution(atlas):
    assert atlas.g10_useful_texels(0.25) == {"2048": 1024.0, "4096": 2048.0, "8192": 4096.0}
    assert atlas.g10_useful_texels(-1.0)["2048"] == 0.0


def test_fixed_padding_is_eight_texels_of_a_2048_atlas(atlas):
    config = atlas.fixed_padding_config()
    assert config["pad_uv"] == pytest.approx(8 / 2048)
    assert config["label_uv"] == pytest.approx(32 / 2048)


def test_g8_panels_do_not_overlap_and_fill_the_padded_square(atlas):
    config = atlas.g8_panel_config()
    internal, skin = config["internal_bbox"], config["skin_bbox"]
    assert internal[3] < skin[1], "the separator must sit between the two panels"
    assert skin[1] - internal[3] == pytest.approx(config["separator_uv"])
    assert skin[3] == pytest.approx(1.0 - config["separator_uv"] / 3.0)  # 24-texel separator, 8-texel pad


def test_file_sha256_is_upper_case_hex(atlas, tmp_path):
    target = tmp_path / "probe.bin"
    target.write_bytes(b"uv-clean-atlas")
    assert atlas.file_sha256(str(target)) == hashlib.sha256(b"uv-clean-atlas").hexdigest().upper()


def test_opposite_cameras_are_horizontal_mirrors(atlas):
    # The property control (a) relies on: a point photographed from +Z and
    # from -Z lands at mirrored U and the same V.
    point = (0.3, -0.2, 0.7)
    u_pos, v_pos = atlas.project_co(point, "+Z")
    u_neg, v_neg = atlas.project_co(point, "-Z")
    assert u_neg == pytest.approx(-u_pos)
    assert v_neg == pytest.approx(v_pos)
    with pytest.raises(ValueError):
        atlas.camera_basis("up")


# --- English only -----------------------------------------------------------

def test_report_template_and_labels_are_english():
    text = SCRIPT.read_text(encoding="utf-8")
    for leftover in ("cero solapes", "QUE HICISTE", "PIEL", "INTERNAS", "MAS ALTA", "ninguna", "no medible", "ESTIMACION_NO_IMPLEMENTADA", "C:\\Program Files"):
        assert leftover not in text, f"untranslated or machine-specific text left: {leftover!r}"
    assert "# REPORT_G10 — zero overlaps with N frames" in text
