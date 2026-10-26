"""Tests for audit_p3d.py: LOD classification, Geometry checks, and an end-to-end
audit of a tiny synthetic MLOD file written byte by byte in the test."""
from __future__ import annotations

import importlib.util
import os
import struct
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load_audit():
    spec = importlib.util.spec_from_file_location("dayz_audit_p3d", HERE / "audit_p3d.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _load_audit()


# --- classify_lod -----------------------------------------------------------

@pytest.mark.parametrize(
    "resolution, expected",
    [
        (0.0, "Visual"),
        (1.0, "Visual"),
        (1e4, "ShadowVolume"),
        (11000.0, "ShadowVolume"),
        (1e13, "Geometry"),
        (4e13, "GeoPhys"),
        (1e15, "Memory"),
        (2e15, "LandContact"),
        (6e15, "ViewGeo"),
        (7e15, "FireGeo"),
    ],
)
def test_classify_lod_dayz_scheme(resolution, expected):
    assert audit.classify_lod(resolution) == expected


@pytest.mark.parametrize("resolution", [2e13, 3e13, 7e13, 1e10])
def test_classify_lod_rejects_arma3_ranges(resolution):
    assert audit.classify_lod(resolution).startswith("Other(")


# --- synthetic tetrahedron (closed, outward-facing) --------------------------

TETRA_POINTS = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
TETRA_FACES = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


class _Obj:
    """Hashable attribute bag; selections key points and faces by identity like py3d."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


PEN = r"dz\data\data\penetration\wood_desk.rvmat"


def _stub_lod(face_indices=TETRA_FACES, selections=None, properties=None, material=PEN):
    points = [_Obj(coords=c) for c in TETRA_POINTS]
    faces = [
        _Obj(vertices=[_Obj(point=points[i]) for i in idx], material=material)
        for idx in face_indices
    ]
    sels = {}
    for name, (pt_idx, face_idx) in (selections or {}).items():
        sels[name] = _Obj(
            points={points[i]: 1 for i in pt_idx},
            faces={faces[i]: 1 for i in face_idx},
        )
    return _Obj(points=points, faces=faces, selections=sels, properties=properties or {}, mass=None)


FULL = ([0, 1, 2, 3], [0, 1, 2, 3])


def _severities(issues):
    return [sev for sev, _ in issues]


def test_component_naming_ok():
    assert audit.check_component_naming(_stub_lod(selections={"Component01": FULL})) == []


def test_component_naming_lowercase_is_only_a_note():
    # Every binarized vanilla model on P:\ stores component01 in lowercase.
    issues = audit.check_component_naming(_stub_lod(selections={"component01": FULL}))
    assert _severities(issues) == ["NOTE"]
    assert "silently" not in issues[0][1]


@pytest.mark.parametrize("name", ["COMPONENT01", "ComPonent01"])
def test_component_naming_other_case_is_a_warning(name):
    issues = audit.check_component_naming(_stub_lod(selections={name: FULL}))
    assert _severities(issues) == ["WARNING"]
    assert f"'{name}'" in issues[0][1]


def test_component_naming_missing_is_critical():
    assert _severities(audit.check_component_naming(_stub_lod())) == ["CRITICAL"]


def test_component_coverage_partial_warns():
    lod = _stub_lod(selections={"Component01": ([0, 1, 2], [0])})
    assert _severities(audit.check_component_coverage(lod)) == ["WARNING", "WARNING"]


def test_component_coverage_counts_every_component():
    # A non-convex Geometry LOD split into two convex pieces is fully covered.
    lod = _stub_lod(selections={"Component01": ([0, 1, 2], [0]), "Component02": ([0, 1, 3, 2], [1, 2, 3])})
    assert audit.check_component_coverage(lod) == []


def test_component_coverage_ignores_non_component_selections():
    lod = _stub_lod(selections={"Component01": ([0, 1, 2], [0]), "camo": FULL})
    assert _severities(audit.check_component_coverage(lod)) == ["WARNING", "WARNING"]


def test_autocenter_property():
    assert audit.check_autocenter_prop(_stub_lod(properties={"autocenter": "0"}), True) == []
    assert _severities(audit.check_autocenter_prop(_stub_lod(), True)) == ["WARNING"]


def test_autocenter_property_with_wrong_value_is_flagged():
    issues = audit.check_autocenter_prop(_stub_lod(properties={"autocenter": "1"}), True)
    assert _severities(issues) == ["WARNING"] and "autocenter=1" in issues[0][1]


def test_autocenter_property_not_needed_without_config_autocenter():
    assert audit.check_autocenter_prop(_stub_lod()) == []
    assert audit.check_autocenter_prop(_stub_lod(), False) == []


def test_config_sets_autocenter_zero(tmp_path):
    cfg = tmp_path / "config.cpp"
    cfg.write_text('class CfgVehicles { class Inventory_Base; class MyCrate: Inventory_Base '
                   '{ model = "\\MyMod\\crate.p3d"; autocenter = 0; }; };', encoding="utf-8")
    assert audit.config_sets_autocenter_zero(str(cfg), "P:/MyMod/crate.p3d") is True
    cfg.write_text('class CfgVehicles { class MyKit { model = "\\MyMod\\kit.p3d"; autocenter = 1; }; };',
                   encoding="utf-8")
    assert audit.config_sets_autocenter_zero(str(cfg), "P:/MyMod/kit.p3d") is False
    assert audit.config_sets_autocenter_zero(None, "kit.p3d") is False


def test_config_autocenter_only_counts_classes_using_this_model(tmp_path):
    # Like P:\DZ\gear\camping\config.cpp: a proxy sets autocenter = 0, the kit does not.
    cfg = tmp_path / "config.cpp"
    cfg.write_text('class CfgVehicles { class Inventory_Base; '
                   'class TentKit: Inventory_Base { model = "\\DZ\\gear\\camping\\kit.p3d"; }; '
                   'class ProxyTent: Inventory_Base { model = "\\DZ\\gear\\camping\\proxy.p3d"; autocenter = 0; }; '
                   'class BaseCrate: Inventory_Base { model = "\\DZ\\gear\\camping\\crate.p3d"; autocenter = 0; }; '
                   'class CrateGreen: BaseCrate {}; };', encoding="utf-8")
    assert audit.config_sets_autocenter_zero(str(cfg), "P:/DZ/gear/camping/kit.p3d") is False
    assert audit.config_sets_autocenter_zero(str(cfg), "P:/DZ/gear/camping/proxy.p3d") is True
    assert audit.config_sets_autocenter_zero(str(cfg), "P:/DZ/gear/camping/crate.p3d") is True
    assert audit.config_sets_autocenter_zero(str(cfg), "P:/DZ/gear/camping/other.p3d") is False


def test_geometry_mass_reported():
    lod = _stub_lod()
    assert audit.check_geometry_mass(lod)[0][1].startswith("Geometry LOD has no mass")
    lod.mass = 12.5
    assert audit.check_geometry_mass(lod) == [("NOTE", "Geometry LOD mass: 12.500")]


def test_watertight_closed_and_open():
    assert audit.check_watertight(_stub_lod()) == []
    open_mesh = _stub_lod(face_indices=TETRA_FACES[:3])
    assert _severities(audit.check_watertight(open_mesh)) == ["WARNING"]


def test_degenerate_face_detected():
    lod = _stub_lod(face_indices=TETRA_FACES + [(0, 0, 1)])
    assert _severities(audit.check_degenerate_faces(lod)) == ["WARNING"]


def _quad_lod(coords):
    points = [_Obj(coords=c) for c in coords]
    face = _Obj(vertices=[_Obj(point=pt) for pt in points], material=PEN)
    return _Obj(points=points, faces=[face], selections={}, properties={})


def test_quad_with_collinear_first_three_vertices_is_not_degenerate():
    # The area was once taken from vertices 0, 1, 2 only, so this valid 2x1
    # quad (vertex 1 lies on the edge from 0 to 2) got a false zero-area WARNING.
    quad = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0)]
    assert audit.face_area(quad) == pytest.approx(1.0)
    assert audit.check_degenerate_faces(_quad_lod(quad)) == []


def test_quad_collapsed_by_fourth_vertex_is_degenerate():
    # Vertices 0, 1, 2 form a real triangle, but vertex 3 folds the quad into a
    # bow tie whose halves cancel; the first-three-vertex check missed it.
    quad = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]
    assert audit.face_area(quad) == pytest.approx(0.0)
    assert _severities(audit.check_degenerate_faces(_quad_lod(quad))) == ["WARNING"]


def test_face_area_of_plain_quad_and_triangle():
    assert audit.face_area([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]) == pytest.approx(1.0)
    assert audit.face_area([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]) == pytest.approx(0.5)


def test_required_lods_firegeo_note_uses_7e15():
    issues = audit.check_required_lods({"Visual": 0, "Geometry": 0, "Memory": 0, "ViewGeo": 0})
    assert issues == [("NOTE", "Missing FireGeo LOD (res ~7e15). No ballistic damage zones.")]


def test_required_lods_geophys_absence_is_not_reported():
    # Vanilla DayZ models carry no 2e13 LOD; its absence must not raise anything.
    lods = {"Visual": 0, "Geometry": 0, "Memory": 0, "ViewGeo": 0, "FireGeo": 0}
    assert audit.check_required_lods(lods) == []


def test_required_lods_missing_viewgeo_is_a_note():
    issues = audit.check_required_lods({"Visual": 0, "Geometry": 0, "Memory": 0, "FireGeo": 0})
    assert _severities(issues) == ["NOTE"]
    assert "ViewGeo LOD (res ~6e15)" in issues[0][1]


# --- Memory and Visual LOD animation checks -------------------------------------

def _points_lod(coords, selections, faces=()):
    """LOD stub whose selections map names to lists of point indices."""
    points = [_Obj(coords=c) for c in coords]
    sels = {name: _Obj(points={points[i]: 1 for i in idx}, faces={}) for name, idx in selections.items()}
    return _Obj(points=points, faces=list(faces), selections=sels, properties={})


def _memory(selections, coords=((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 2.0, 0.0))):
    base = {"pos center": [0], "box_placing_min": [0], "box_placing_max": [0]}
    return _points_lod(coords, {**base, **selections})


MODEL_CFG = """
#define _ARMA_
class CfgSkeletons { class FlagPole_skeleton { skeletonBones[] = {"flag_mast", ""}; }; };
class CfgModels
{
    class Default;
    class flagpole: Default
    {
        skeletonName = "FlagPole_skeleton";
        class Animations
        {
            class flag_mast { type = "translation"; source = "flag_mast"; selection = "flag_mast"; axis = "flag_mast_axis"; minValue = 0; maxValue = 1; };
            /* a door that inherits its type and source */
            class door_base { type = "rotation"; source = "door"; selection = "door"; axis = "door_axis"; };
            class lid: door_base { selection = "lid"; axis = ""; begin = "lid_begin"; end = "lid_end"; };
        };
    };
    class flagpole_tall: flagpole {};
};
"""


def test_model_animations_reads_cfgmodels():
    anims = audit.model_animations(MODEL_CFG, "FlagPole")
    assert sorted(anims) == ["door_base", "flag_mast", "lid"]
    assert anims["flag_mast"]["selection"] == "flag_mast" and anims["flag_mast"]["axis"] == "flag_mast_axis"
    assert anims["lid"]["type"] == "rotation" and anims["lid"]["begin"] == "lid_begin"  # inherited from door_base


def test_model_animations_inherits_from_parent_model_and_misses_unknown():
    assert sorted(audit.model_animations(MODEL_CFG, "flagpole_tall")) == ["door_base", "flag_mast", "lid"]
    assert audit.model_animations(MODEL_CFG, "other") is None
    assert audit.model_animations("class CfgModels { class box {}; };", "box") == {}


def _anim_lods(visual_sels, memory_sels):
    visual = _points_lod(TETRA_POINTS, visual_sels)
    memory = _memory(memory_sels)
    return {"Visual": (0, visual), "Memory": (1, memory)}


FLAG = {"flag_mast": {"selection": "flag_mast", "axis": "flag_mast_axis"}}


def test_animation_selection_and_axis_present_pass():
    assert audit.check_animations(FLAG, _anim_lods({"flag_mast": [0, 1]}, {"flag_mast_axis": [1, 2]})) == []


def test_animation_selection_missing_from_visual_is_critical():
    issues = audit.check_animations(FLAG, _anim_lods({}, {"flag_mast_axis": [1, 2]}))
    assert _severities(issues) == ["CRITICAL"]
    assert "Visual LOD has no 'flag_mast' selection" in issues[0][1]


def test_animation_empty_visual_selection_warns():
    issues = audit.check_animations(FLAG, _anim_lods({"flag_mast": []}, {"flag_mast_axis": [1, 2]}))
    assert _severities(issues) == ["WARNING"]


@pytest.mark.parametrize("indices", [[1], [0, 1, 2]])
def test_animation_axis_needs_exactly_two_points(indices):
    issues = audit.check_animations(FLAG, _anim_lods({"flag_mast": [0]}, {"flag_mast_axis": indices}))
    assert _severities(issues) == ["CRITICAL"]
    assert f"axis 'flag_mast_axis' has {len(indices)} points" in issues[0][1]


def test_animation_axis_missing_and_begin_end_points():
    issues = audit.check_animations(FLAG, _anim_lods({"flag_mast": [0]}, {}))
    assert _severities(issues) == ["CRITICAL"] and "no 'flag_mast_axis'" in issues[0][1]
    lid = {"lid": {"selection": "LID", "axis": "", "begin": "lid_begin", "end": "lid_end"}}
    issues = audit.check_animations(lid, _anim_lods({"lid": [0]}, {"lid_begin": [1]}))
    assert [m for _, m in issues] == ["Animation 'lid': Memory LOD has no 'lid_end' point (end of the axis)."]


def test_pos_center_checked_only_for_autocenter_zero_items():
    no_center = _points_lod([(0.0, 0.0, 0.0)], {"box_placing_min": [0], "box_placing_max": [0]})
    assert audit.check_memory_lod(no_center) == []  # ordinary item or kit
    issues = audit.check_memory_lod(no_center, wants_zero=True)
    assert _severities(issues) == ["WARNING"] and "pos center" in issues[0][1]
    off_origin = _points_lod([(0.0, 2.0, 0.0)], {"pos center": [0]})
    assert audit.check_memory_lod(off_origin) == []
    assert _severities(audit.check_memory_lod(off_origin, wants_zero=True)) == ["NOTE"]


def test_memory_points_match_without_case():
    # 'pos center' was once looked up with exact case, so 'Pos Center' on an
    # autocenter = 0 item gave a false 'Missing pos center' WARNING.
    lod = _points_lod([(0.0, 0.0, 0.0)], {"Pos Center": [0]})
    assert audit.check_memory_lod(lod, wants_zero=True) == []
    off = _points_lod([(0.0, 2.0, 0.0)], {"POS CENTER": [0]})
    assert _severities(audit.check_memory_lod(off, wants_zero=True)) == ["NOTE"]
    boxes = _points_lod([(0.0, 0.0, 0.0)], {"pos center": [0], "Box_Placing_Min": [0], "BOX_PLACING_MAX": [0]})
    assert audit.check_memory_lod(boxes, has_geometry=False) == []
    bbox = _points_lod([(0.0, 0.0, 0.0)], {"BoundingBox_Min": [0], "boundingbox_MAX": [0]})
    assert audit.check_memory_lod(bbox, has_geometry=False) == []


def test_box_placing_note_only_without_geometry_lod():
    bare = _points_lod([(0.0, 0.0, 0.0)], {"pos center": [0]})
    assert audit.check_memory_lod(bare, has_geometry=True) == []
    issues = audit.check_memory_lod(bare, has_geometry=False)
    assert _severities(issues) == ["NOTE"] and "box_placing" in issues[0][1]
    vanilla = _points_lod([(0.0, 0.0, 0.0)], {"boundingbox_min": [0], "boundingbox_max": [0]})
    assert audit.check_memory_lod(vanilla, has_geometry=False) == []


def test_memory_lod_faces_warning_text():
    lod = _points_lod([(0.0, 0.0, 0.0)], {"pos center": [0]}, faces=[object(), object()])
    assert audit.check_memory_lod(lod) == [("WARNING",
        "Memory LOD has 2 faces; it should have 0. Only single-vertex points belong in Memory LOD.")]


def test_memory_axis_without_model_cfg_is_not_guessed():
    # Without model.cfg nothing is inferred from names such as door_axis.
    assert audit.check_memory_lod(_memory({"door_axis": [1]})) == []
    assert audit.check_visual_lod(_points_lod(TETRA_POINTS, {})) == []


def test_find_model_cfg_walks_up_to_root(tmp_path):
    (tmp_path / "data" / "sub").mkdir(parents=True)
    model = tmp_path / "data" / "sub" / "box.p3d"
    assert audit.find_model_cfg(model, tmp_path) is None
    (tmp_path / "model.cfg").write_text("", encoding="utf-8")
    assert Path(audit.find_model_cfg(model, tmp_path)) == (tmp_path / "model.cfg").resolve()
    (tmp_path / "data" / "model.cfg").write_text("", encoding="utf-8")
    assert Path(audit.find_model_cfg(model, tmp_path)) == (tmp_path / "data" / "model.cfg").resolve()


def test_missing_py3d_exits_2_with_requirements_hint(monkeypatch, capsys):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "py3d":
            raise ImportError(name)
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit) as exc:
        audit.load_py3d()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "python -m pip install -r" in captured.err and "requirements.txt" in captured.err
    assert "[FAIL]" in captured.err and captured.out == ""
    assert audit.REQUIREMENTS.is_file()


def test_collision_materials_flag_faces_without_one():
    assert audit.check_collision_materials(_stub_lod(), "Geometry") == []
    issues = audit.check_collision_materials(_stub_lod(material=""), "FireGeo")
    assert [sev for sev, _ in issues] == ["CRITICAL"]
    assert "4/4 faces in the FireGeo LOD have no material" in issues[0][1]


def test_viewgeo_without_materials_is_only_a_warning():
    # Any ViewGeo face without a material once failed the run as CRITICAL,
    # though View Geometry faces commonly carry no penetration material.
    issues = audit.check_collision_materials(_stub_lod(material=""), "ViewGeo")
    assert _severities(issues) == ["WARNING"]
    assert "4/4 faces in the ViewGeo LOD have no material" in issues[0][1]
    assert audit.check_collision_materials(_stub_lod(), "ViewGeo") == []


def test_face_winding_check_removed():
    assert not hasattr(audit, "check_face_winding")


# --- end-to-end on a byte-level MLOD file -------------------------------------

def _asciiz(text: str) -> bytes:
    return text.encode("utf-8") + b"\0"


def _write_lod(resolution, points, faces, selections=(), properties=(), masses=(), material=PEN):
    out = bytearray(b"P3DM")
    out += struct.pack("<LL", 28, 256)
    out += struct.pack("<LLL", len(points), 0, len(faces))
    out += b"\0" * 4
    for p in points:
        out += struct.pack("fff", *p) + struct.pack("<L", 0)
    for idx in faces:
        out += struct.pack("<L", len(idx))
        for i in idx:
            out += struct.pack("<LL", i, 0) + struct.pack("ff", 0, 0)
        out += b"\0" * 16  # padding for the unused fourth vertex of a triangle
        out += struct.pack("<L", 0) + _asciiz("") + _asciiz(material)
    out += b"TAGG"
    for name, (pt_idx, face_idx) in selections:
        out += b"\x01" + _asciiz(name)
        out += struct.pack("<L", len(points) + len(faces))
        out += bytes(1 if i in pt_idx else 0 for i in range(len(points)))
        out += bytes(1 if i in face_idx else 0 for i in range(len(faces)))
    for key, value in properties:
        out += b"\x01" + _asciiz("#Property#") + struct.pack("<L", 128)
        out += struct.pack("64s64s", key.encode(), value.encode())
    if masses:
        out += b"" + _asciiz("#Mass#") + struct.pack("<L", 4 * len(masses))
        out += b"".join(struct.pack("f", m) for m in masses)
    out += b"\x01" + _asciiz("#EndOfFile#") + struct.pack("<L", 0)
    out += struct.pack("f", resolution)
    return bytes(out)


def _write_mlod(path: Path, lods):
    path.write_bytes(b"MLOD" + struct.pack("<LL", 257, len(lods)) + b"".join(lods))


def test_audit_p3d_end_to_end(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(
        1e13, TETRA_POINTS, TETRA_FACES,
        selections=[("Component01", FULL)], properties=[("autocenter", "0")],
    )
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [], selections=[("pos center", ([0], []))])
    visual0 = _write_lod(0.0, TETRA_POINTS, TETRA_FACES)
    visual1 = _write_lod(1.0, TETRA_POINTS[:3], [TETRA_FACES[0]])
    model = tmp_path / "tetra.p3d"
    _write_mlod(model, [visual0, visual1, geometry, memory])

    assert audit.audit_p3d(str(model)) is True
    out = capsys.readouterr().out
    assert "--- Geometry LOD[2] ---" in out
    assert "--- Visual LOD[0] ---" in out  # LOD0 kept when several Visual LODs exist
    assert "RESULT: 0 CRITICAL" in out or "ALL CHECKS PASSED" in out


def test_audit_p3d_flags_collision_lods_without_materials(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(1e13, TETRA_POINTS, TETRA_FACES, selections=[("Component01", FULL)], material="")
    geophys = _write_lod(4e13, TETRA_POINTS, TETRA_FACES)
    viewgeo = _write_lod(6e15, TETRA_POINTS, TETRA_FACES, material="")
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES, material="")  # visual LODs are not checked
    model = tmp_path / "bare.p3d"
    _write_mlod(model, [visual, geometry, geophys, viewgeo, memory])

    assert audit.audit_p3d(str(model)) is False
    out = capsys.readouterr().out
    assert "--- GeoPhys LOD[2] ---" in out
    assert "CRITICAL: 4/4 faces in the Geometry LOD have no material" in out
    assert "WARNING: 4/4 faces in the ViewGeo LOD have no material" in out
    assert "GeoPhys LOD have no material" not in out
    assert "RESULT: 1 CRITICAL" in out


def test_audit_p3d_viewgeo_without_materials_still_passes(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(1e13, TETRA_POINTS, TETRA_FACES, selections=[("Component01", FULL)])
    viewgeo = _write_lod(6e15, TETRA_POINTS, TETRA_FACES, material="")
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES)
    model = tmp_path / "viewgeo_bare.p3d"
    _write_mlod(model, [visual, geometry, viewgeo, memory])

    assert audit.audit_p3d(str(model)) is True
    out = capsys.readouterr().out
    assert "WARNING: 4/4 faces in the ViewGeo LOD have no material" in out
    assert "CRITICAL:" not in out and "RESULT: 0 CRITICAL, 1 WARNING" in out


def test_audit_p3d_reports_geometry_mass(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(
        1e13, TETRA_POINTS, TETRA_FACES,
        selections=[("Component01", FULL)], masses=[2.5, 2.5, 2.5, 2.5],
    )
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES)
    model = tmp_path / "heavy.p3d"
    _write_mlod(model, [visual, geometry, memory])

    audit.audit_p3d(str(model))
    assert "NOTE: Geometry LOD mass: 10.000" in capsys.readouterr().out


def test_audit_p3d_passes_lowercase_component(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(1e13, TETRA_POINTS, TETRA_FACES, selections=[("component01", FULL)])
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES)
    model = tmp_path / "lower.p3d"
    _write_mlod(model, [visual, geometry, memory])

    assert audit.audit_p3d(str(model)) is True
    out = capsys.readouterr().out
    assert "NOTE: Found 'component01' (lowercase). That is fine" in out
    assert "CRITICAL" not in out


def test_audit_p3d_checks_model_cfg_animations(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(1e13, TETRA_POINTS, TETRA_FACES, selections=[("Component01", FULL)])
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [],
                        selections=[("flag_mast_axis", ([0, 1], []))])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES, selections=[("flag_mast", ([0, 1], [0]))])
    model = tmp_path / "flagpole.p3d"
    _write_mlod(model, [visual, geometry, memory])
    cfg = tmp_path / "model.cfg"
    cfg.write_text(MODEL_CFG, encoding="utf-8")

    assert audit.audit_p3d(str(model), str(cfg)) is False  # door and lid parts are missing
    out = capsys.readouterr().out
    assert "3 animation(s)" in out
    assert "Animation 'flag_mast'" not in out
    assert "Animation 'door_base': Visual LOD has no 'door' selection" in out


def test_audit_p3d_rejects_odol(tmp_path, capsys):
    model = tmp_path / "binarized.p3d"
    model.write_bytes(b"ODOL" + b"\0" * 16)
    tally = {}
    assert audit.audit_p3d(str(model), tally=tally) is False
    captured = capsys.readouterr()
    err = captured.err
    assert "[FAIL]" in err and "Not MLOD" in err and "binarized ODOL model, so it was not audited" in err
    assert "Audit the MLOD source" in err
    assert "[FAIL]" not in captured.out  # [FAIL] lines go to stderr
    assert tally == {"odol": 1}


def test_audit_p3d_non_p3d_signature_is_unreadable_not_odol(tmp_path, capsys):
    # Any non-MLOD file was once counted and summarised as an 'ODOL reject'.
    model = tmp_path / "junk.p3d"
    model.write_bytes(b"\x89PNG" + b"\0" * 16)
    tally = {}
    assert audit.audit_p3d(str(model), tally=tally) is False
    assert "not a .p3d model" in capsys.readouterr().err
    assert tally == {"unreadable": 1}


def test_main_odol_only_says_not_audited(no_gate, tmp_path, capsys):
    # An ODOL-only run once ended 'ISSUES FOUND: fix before building PBO',
    # although the file was never audited.
    model = tmp_path / "binarized.p3d"
    model.write_bytes(b"ODOL" + b"\0" * 16)
    assert _run_main([str(model)]) == 1
    out = capsys.readouterr().out
    assert "OVERALL: NOT AUDITED: 1 binarized ODOL .p3d file(s)" in out
    assert "ISSUES FOUND" not in out


def test_main_odol_plus_real_issue_reports_both(no_gate, tmp_path, capsys):
    model = tmp_path / "binarized.p3d"
    model.write_bytes(b"ODOL" + b"\0" * 16)
    mat = tmp_path / "box.rvmat"
    mat.write_text(r'texture = "P:\MyMod\data\box_co.paa";', encoding="utf-8")
    assert _run_main([str(model), "--rvmat", str(mat)]) == 1
    out = capsys.readouterr().out
    assert "OVERALL: ISSUES FOUND: fix before building PBO (1 binarized ODOL .p3d file(s) not audited)" in out


@pytest.mark.parametrize("odol, other, expected", [
    (0, 0, "OVERALL: ALL PASSED"),
    (2, 0, "OVERALL: NOT AUDITED: 2 binarized ODOL .p3d file(s); audit the MLOD source instead"),
    (0, 1, "OVERALL: ISSUES FOUND: fix before building PBO"),
])
def test_overall_line(odol, other, expected):
    assert audit.overall_line(odol, other) == expected



# --- text files ----------------------------------------------------------------

def test_audit_text_file_clean(tmp_path):
    cfg = tmp_path / "config.cpp"
    cfg.write_text('model = "MyMod/data/box.p3d";', encoding="utf-8")
    assert audit.audit_text_file(str(cfg), "config.cpp") is True


def test_audit_text_file_flags_p_drive_path(tmp_path, capsys):
    cfg = tmp_path / "config.cpp"
    cfg.write_text(r'model = "P:\MyMod\data\box.p3d";', encoding="utf-8")
    assert audit.audit_text_file(str(cfg), "config.cpp") is False
    assert "Line 1: Absolute P:" in capsys.readouterr().out


def test_url_in_cfgmods_is_not_a_p_drive_path(tmp_path):
    cfg = tmp_path / "config.cpp"
    cfg.write_text('class CfgMods { class MyMod { action = "http://www.dayzgame.com"; url = "HTTPS://x.org"; }; };\n'
                   'model = "p:/MyMod/box.p3d";', encoding="utf-8")
    issues = audit.check_p_drive_paths_in_file(str(cfg))
    assert len(issues) == 1 and "Line 2" in issues[0][1] and "p:/MyMod/box.p3d" in issues[0][1]


def test_high_visual_lod_gets_no_autocenter_note():
    raised = [(x, y + 5.0, z) for x, y, z in TETRA_POINTS]
    assert audit.check_visual_lod(_points_lod(raised, {})) == []


def test_audit_text_file_read_error_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(
        audit, "check_p_drive_paths_in_file", lambda path: [("ERROR", f"Cannot read {path}: boom")]
    )
    assert audit.audit_text_file(str(tmp_path / "x.rvmat"), ".rvmat") is False


# --- CLI exit paths --------------------------------------------------------------

@pytest.fixture
def no_gate(monkeypatch):
    calls = []
    monkeypatch.setattr(audit.h, "gate_on_preflight", lambda: calls.append(1))
    return calls


def _run_main(argv):
    with pytest.raises(SystemExit) as exc:
        audit.main(argv)
    return exc.value.code


def test_main_without_inputs_exits_2_before_gate(no_gate, capsys):
    assert _run_main([]) == 2
    assert no_gate == []
    assert "nothing to audit" in capsys.readouterr().err


def test_main_missing_scan_dir_exits_1(no_gate, tmp_path, capsys):
    assert _run_main(["--scan-dir", str(tmp_path / "nope")]) == 1
    assert no_gate == []
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err and "Directory not found" in captured.err and "Directory not found" not in captured.out


@pytest.mark.parametrize("flag", ["--config", "--model-cfg", "--rvmat"])
def test_main_missing_option_file_exits_1(no_gate, tmp_path, capsys, flag):
    assert _run_main([flag, str(tmp_path / "missing.txt")]) == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err and "File not found" in captured.err and "File not found" not in captured.out


def test_main_clean_text_files_exit_0(no_gate, tmp_path):
    cfg = tmp_path / "config.cpp"
    cfg.write_text("class CfgPatches {};\n", encoding="utf-8")
    mat = tmp_path / "box.rvmat"
    mat.write_text('texture = "MyMod/data/box_co.paa";', encoding="utf-8")
    assert _run_main(["--config", str(cfg), "--rvmat", str(mat)]) == 0
    assert no_gate == [1]


def test_main_p_drive_path_exits_1(no_gate, tmp_path):
    mat = tmp_path / "box.rvmat"
    mat.write_text(r'texture = "P:\MyMod\data\box_co.paa";', encoding="utf-8")
    assert _run_main(["--rvmat", str(mat)]) == 1


def test_main_p3d_after_rvmat_is_still_audited_as_model(no_gate, tmp_path, monkeypatch):
    # `--rvmat a.rvmat model.p3d` once swallowed model.p3d into the rvmat list, so the
    # model only got the P:\ text scan and the run could exit 0 without auditing it.
    mat = tmp_path / "box.rvmat"
    mat.write_text('texture = "MyMod/data/box_co.paa";', encoding="utf-8")
    model = tmp_path / "m.p3d"
    model.write_bytes(b"MLOD" + b"\0" * 8)
    audited = []
    monkeypatch.setattr(audit, "audit_p3d", lambda f, cfg=None, config=None, tally=None: audited.append(f) or False)
    assert _run_main(["--rvmat", str(mat), str(model)]) == 1
    assert audited == [str(model)]


def test_main_rvmat_repeats_for_several_files(no_gate, tmp_path):
    clean = tmp_path / "a.rvmat"
    clean.write_text('texture = "MyMod/data/a_co.paa";', encoding="utf-8")
    bad = tmp_path / "b.rvmat"
    bad.write_text(r'texture = "P:\MyMod\data\b_co.paa";', encoding="utf-8")
    assert _run_main(["--rvmat", str(clean), "--rvmat", str(bad)]) == 1


def test_scan_dir_audits_text_files(no_gate, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
    (tmp_path / "data" / "box.rvmat").write_text(r'texture = "P:\x.paa";', encoding="utf-8")
    assert _run_main(["--scan-dir", str(tmp_path)]) == 1


def test_autocenter_checked_only_on_geometry_lod(tmp_path, monkeypatch, capsys):
    def lod(resolution, **kw):
        stub = _stub_lod(**kw)
        stub.resolution = resolution
        return stub

    config = tmp_path / "config.cpp"
    config.write_text("class CfgVehicles { class MyCrate { model = \"\\MyMod\\m.p3d\"; autocenter = 0; }; };", encoding="utf-8")

    def run(geometry_props, cfg=str(config)):
        lods = [
            lod(1e13, selections={"Component01": FULL}, properties=geometry_props),
            lod(7e15),  # FireGeo with no autocenter property: valid on its own
            lod(1e15, face_indices=[], selections={"pos center": ([0], [])}),
        ]
        fake_py3d = type("FakePy3d", (), {"P3D": staticmethod(lambda f: _Obj(lods=lods))})
        monkeypatch.setattr(audit, "load_py3d", lambda: fake_py3d)
        model = tmp_path / "m.p3d"
        model.write_bytes(b"MLOD" + b"\0" * 8)
        audit.audit_p3d(str(model), config=cfg)
        return capsys.readouterr().out

    out = run({"autocenter": "0"})
    assert "--- FireGeo LOD[1] ---" in out
    assert "autocenter=0' LOD property" not in out

    out = run({})  # the Geometry LOD still gets the check
    assert out.count("autocenter=0' LOD property") == 1

    out = run({}, cfg=None)  # no config.cpp sets autocenter = 0: kits and items get no warning
    assert "autocenter=0' LOD property" not in out
    assert "WARNING:" not in out



def test_unreadable_config_is_an_error_not_a_silent_skip(tmp_path, monkeypatch, capsys):
    # An unreadable --config was once treated as "does not set autocenter = 0",
    # so the autocenter and pos center checks were skipped without a word.
    unreadable = tmp_path / "config.cpp"
    unreadable.mkdir()  # reading a folder raises OSError, like a locked file
    with pytest.raises(OSError):
        audit.config_sets_autocenter_zero(str(unreadable), "m.p3d")

    lods = [_stub_lod(), _stub_lod(selections={"Component01": FULL}), _stub_lod(), _stub_lod(),
            _stub_lod(face_indices=[], selections={"pos center": ([0], [])})]
    for lod, res in zip(lods, (0.0, 1e13, 6e15, 7e15, 1e15)):
        lod.resolution = res
    fake_py3d = type("FakePy3d", (), {"P3D": staticmethod(lambda f: _Obj(lods=lods))})
    monkeypatch.setattr(audit, "load_py3d", lambda: fake_py3d)
    monkeypatch.setattr(audit, "check_visual_lod", lambda lod: [])
    model = tmp_path / "m.p3d"
    model.write_bytes(b"MLOD" + b"\0" * 8)

    tally = {}
    assert audit.audit_p3d(str(model), config=str(unreadable), tally=tally) is False
    out = capsys.readouterr().out
    assert f"ERROR: Cannot read config {unreadable}" in out
    assert "autocenter and pos center checks were skipped" in out
    assert "RESULT: 0 CRITICAL, 1 ERROR" in out
    assert tally["unreadable"] == 1


def test_ordinary_item_without_pos_center_passes_and_autocenter_item_does_not(tmp_path, monkeypatch, capsys):
    def lod(resolution, **kw):
        stub = _stub_lod(**kw)
        stub.resolution = resolution
        return stub

    lods = [
        lod(0.0),
        lod(1e13, selections={"Component01": FULL}, properties={"autocenter": "0"}),
        lod(6e15), lod(7e15),
        lod(1e15, face_indices=[], selections={}),  # no pos center, no box_placing
    ]
    fake_py3d = type("FakePy3d", (), {"P3D": staticmethod(lambda f: _Obj(lods=lods))})
    monkeypatch.setattr(audit, "load_py3d", lambda: fake_py3d)
    monkeypatch.setattr(audit, "check_visual_lod", lambda lod: [])  # stub faces carry no textures
    model = tmp_path / "m.p3d"
    model.write_bytes(b"MLOD" + b"\0" * 8)

    audit.audit_p3d(str(model))
    out = capsys.readouterr().out
    assert "pos center" not in out and "box_placing" not in out
    assert "ALL CHECKS PASSED" in out

    config = tmp_path / "config.cpp"
    config.write_text("class CfgVehicles { class MyCrate { model = \"\\MyMod\\m.p3d\"; autocenter = 0; }; };", encoding="utf-8")
    audit.audit_p3d(str(model), config=str(config))
    assert "WARNING: Missing 'pos center'" in capsys.readouterr().out


def test_component_coverage_matches_lowercase_components():
    # Binarized models store 'component01'; the coverage check must still run on them.
    lod = _stub_lod(selections={"component01": ([0, 1, 2], [0])})
    issues = audit.check_component_coverage(lod)
    assert _severities(issues) == ["WARNING", "WARNING"]
    assert "cover 3/4 vertices" in issues[0][1]
    full = _stub_lod(selections={"component01": ([0, 1, 2], [0]), "COMPONENT02": ([0, 1, 3, 2], [1, 2, 3])})
    assert audit.check_component_coverage(full) == []


def test_scan_dir_summary_names_odol_reject(no_gate, tmp_path, capsys):
    # A mod holding one reused vanilla (binarized, "ODOL") model once failed the
    # whole sweep as 'ISSUES FOUND' with nothing saying which file caused it.
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "basin_a.p3d").write_bytes(b"ODOL" + b"\0" * 8)
    (tmp_path / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
    assert _run_main(["--scan-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert r"SCAN SUMMARY: 1 of 2 file(s) failed: 0 CRITICAL, 0 P:\ path(s), 1 ODOL reject(s)" in out
    assert os.path.join("data", "basin_a.p3d") + ": ODOL reject" in out
    assert "OVERALL: NOT AUDITED: 1 binarized ODOL .p3d file(s)" in out


def test_scan_dir_summary_counts_critical_and_p_drive_per_file(no_gate, tmp_path, capsys, monkeypatch):
    (tmp_path / "a.p3d").write_bytes(b"MLOD")
    (tmp_path / "ok.rvmat").write_text('texture = "MyMod/data/ok_co.paa";', encoding="utf-8")
    (tmp_path / "bad.rvmat").write_text('a = "P:\\x\\a.paa";\nb = "P:\\x\\b.paa";\n', encoding="utf-8")

    def fake_audit(f, cfg=None, config=None, tally=None):
        tally.update(audit.tally_issues([("CRITICAL", "no geometry"), ("CRITICAL", "no memory"),
                                         ("WARNING", "Component name")]))
        return False

    monkeypatch.setattr(audit, "audit_p3d", fake_audit)
    assert _run_main(["--scan-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert r"SCAN SUMMARY: 2 of 3 file(s) failed: 2 CRITICAL, 2 P:\ path(s), 0 ODOL reject(s)" in out
    assert "a.p3d: 2 CRITICAL, 1 other WARNING" in out
    assert r"bad.rvmat: 2 P:\ path(s)" in out
    assert "ok.rvmat:" not in out


def test_scan_dir_clean_mod_summary_and_exit_0(no_gate, tmp_path, capsys):
    (tmp_path / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
    assert _run_main(["--scan-dir", str(tmp_path)]) == 0
    assert "SCAN SUMMARY: 0 of 1 file(s) failed" in capsys.readouterr().out


# --- P:\ paths in comments and the P-DRIVE severity ------------------------------

def test_p_drive_path_only_in_comments_exits_0(no_gate, tmp_path, capsys):
    # A config.cpp whose only P:\ reference was a commented-out old path once
    # printed 'ISSUES FOUND' and exited 1, though the engine never reads comments.
    cfg = tmp_path / "config.cpp"
    cfg.write_text('// old: P:/MyMod/data/a.paa\n'
                   '/* was:\n   texture = "P:\\MyMod\\data\\b.paa"; */\n'
                   'model = "MyMod\\data\\box.p3d"; // P:\\MyMod\\data\\box.p3d\n', encoding="utf-8")
    assert _run_main(["--config", str(cfg)]) == 0
    out = capsys.readouterr().out
    assert "OK: No P:\\ paths found." in out and "OVERALL: ALL PASSED" in out


def test_comment_stripping_keeps_line_numbers_and_strings():
    text = '/* a\nb */ x = "P:/real/one.paa";\nurl = "http://a.org"; y = "P:/two.paa";\n'
    stripped = audit.strip_comments(text)
    assert stripped.count("\n") == text.count("\n")
    assert '"http://a.org"' in stripped and '"P:/two.paa"' in stripped


def test_p_drive_after_comment_block_reports_real_line(tmp_path):
    mat = tmp_path / "a.rvmat"
    mat.write_text('/* header\n   P:/old/x.paa\n*/\ntexture = "P:\\dz\\data\\x_co.paa";\n', encoding="utf-8")
    issues = audit.check_p_drive_paths_in_file(str(mat))
    assert len(issues) == 1 and issues[0][0] == "P-DRIVE" and issues[0][1].startswith("Line 4:")


def test_p_drive_finding_is_labelled_p_drive_not_warning(tmp_path, capsys):
    # Text-file P:\ paths fail the run, while .p3d WARNINGs do not; they once
    # shared the WARNING label, so the output did not say which ones failed.
    cfg = tmp_path / "config.cpp"
    cfg.write_text('model = "P:\\MyMod\\box.p3d";\n', encoding="utf-8")
    assert audit.audit_text_file(str(cfg), "config.cpp") is False
    out = capsys.readouterr().out
    assert "P-DRIVE: Line 1:" in out and "WARNING" not in out
    assert audit.tally_issues(audit.check_p_drive_paths_in_file(str(cfg))) == {
        "critical": 0, "p_drive": 1, "warning": 0, "unreadable": 0}
