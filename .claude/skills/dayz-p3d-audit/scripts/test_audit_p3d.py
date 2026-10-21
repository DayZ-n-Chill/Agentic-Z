"""Tests for audit_p3d.py: LOD classification, Geometry checks, and an end-to-end
audit of a tiny synthetic MLOD file written byte by byte in the test."""
from __future__ import annotations

import importlib.util
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
        (2e13, "GeoPhys"),
        (1e15, "Memory"),
        (2e15, "LandContact"),
        (6e15, "ViewGeo"),
        (7e15, "FireGeo"),
    ],
)
def test_classify_lod_dayz_scheme(resolution, expected):
    assert audit.classify_lod(resolution) == expected


@pytest.mark.parametrize("resolution", [3e13, 7e13, 1e10])
def test_classify_lod_rejects_arma3_ranges(resolution):
    assert audit.classify_lod(resolution).startswith("Other(")


# --- synthetic tetrahedron (closed, outward-facing) --------------------------

TETRA_POINTS = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
TETRA_FACES = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


class _Obj:
    """Hashable attribute bag; selections key points and faces by identity like py3d."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _stub_lod(face_indices=TETRA_FACES, selections=None, properties=None):
    points = [_Obj(coords=c) for c in TETRA_POINTS]
    faces = [
        _Obj(vertices=[_Obj(point=points[i]) for i in idx])
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


def test_component_naming_lowercase_is_critical():
    issues = audit.check_component_naming(_stub_lod(selections={"component01": FULL}))
    assert _severities(issues) == ["CRITICAL"]


def test_component_naming_missing_is_critical():
    assert _severities(audit.check_component_naming(_stub_lod())) == ["CRITICAL"]


def test_component_coverage_partial_warns():
    lod = _stub_lod(selections={"Component01": ([0, 1, 2], [0])})
    assert _severities(audit.check_component_coverage(lod)) == ["WARNING", "WARNING"]


def test_autocenter_property():
    assert audit.check_autocenter_prop(_stub_lod(properties={"autocenter": "0"})) == []
    assert _severities(audit.check_autocenter_prop(_stub_lod())) == ["WARNING"]


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
    out = capsys.readouterr().out
    assert "python -m pip install -r" in out and "requirements.txt" in out
    assert audit.REQUIREMENTS.is_file()


def test_face_winding_check_removed():
    assert not hasattr(audit, "check_face_winding")


# --- end-to-end on a byte-level MLOD file -------------------------------------

def _asciiz(text: str) -> bytes:
    return text.encode("utf-8") + b"\0"


def _write_lod(resolution, points, faces, selections=(), properties=(), masses=()):
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
        out += struct.pack("<L", 0) + _asciiz("") + _asciiz("")
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


def test_audit_p3d_flags_lowercase_component(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(1e13, TETRA_POINTS, TETRA_FACES, selections=[("component01", FULL)])
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES)
    model = tmp_path / "bad.p3d"
    _write_mlod(model, [visual, geometry, memory])

    assert audit.audit_p3d(str(model)) is False
    assert "'component01' (lowercase)" in capsys.readouterr().out


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
    assert audit.audit_p3d(str(model)) is False
    assert "Not MLOD" in capsys.readouterr().out



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
    assert "Directory not found" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["--config", "--model-cfg", "--rvmat"])
def test_main_missing_option_file_exits_1(no_gate, tmp_path, capsys, flag):
    assert _run_main([flag, str(tmp_path / "missing.txt")]) == 1
    assert "File not found" in capsys.readouterr().out


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

    def run(geometry_props):
        lods = [
            lod(1e13, selections={"Component01": FULL}, properties=geometry_props),
            lod(7e15),  # FireGeo with no autocenter property: valid on its own
            lod(1e15, face_indices=[], selections={"pos center": ([0], [])}),
        ]
        fake_py3d = type("FakePy3d", (), {"P3D": staticmethod(lambda f: _Obj(lods=lods))})
        monkeypatch.setattr(audit, "load_py3d", lambda: fake_py3d)
        model = tmp_path / "m.p3d"
        model.write_bytes(b"MLOD" + b"\0" * 8)
        audit.audit_p3d(str(model))
        return capsys.readouterr().out

    out = run({"autocenter": "0"})
    assert "--- FireGeo LOD[1] ---" in out
    assert "autocenter=0' LOD property" not in out

    out = run({})  # the Geometry LOD still gets the check
    assert out.count("autocenter=0' LOD property") == 1
