"""Tests for the whole-model checks of audit_p3d.py (vertex budget, vehicle body, wheel slots),
the extra LOD names, the py3d loader and the DayZ fork's validate() findings.

Every test runs on stand-in models; none needs py3d installed.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent


def _load_audit():
    spec = importlib.util.spec_from_file_location("dayz_audit_p3d_model_checks", HERE / "audit_p3d.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _load_audit()


class _Obj:
    """Hashable attribute bag; selections key points and faces by identity like py3d."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _lod(resolution, selections=(), faces=0, points=0, normals=1, properties=None, distinct=True):
    """A LOD stand-in: `faces` triangles over `points` points. With distinct=False every
    corner repeats the same (point, normal, uv), so the LOD resolves to one vertex."""
    pts = [_Obj(coords=(float(n), 0.0, 0.0)) for n in range(points)]
    made = []
    for n in range(faces):
        corners = [
            _Obj(point=pts[(3 * n + k) % len(pts)], point_index=(3 * n + k) if distinct else 0, normal_index=0,
                 uv=(float(3 * n + k), 0.0) if distinct else (0.0, 0.0))
            for k in range(3)
        ]
        made.append(_Obj(vertices=corners, material="m", texture=""))
    sels = {name: _Obj(points={}, faces={face: 1 for face in made[:count]}) for name, count in selections}
    return _Obj(resolution=resolution, points=pts, faces=made, facenormals=[(0.0, 1.0, 0.0)] * normals,
                selections=sels, properties=properties or {}, num_vertices=3 * faces)


def _severities(issues):
    return [sev for sev, _ in issues]


# --- LOD names ---------------------------------------------------------------

@pytest.mark.parametrize("resolution, expected", [(3e15, "Roadway"), (4e15, "Paths"), (5e15, "HitPoints")])
def test_classify_lod_names_roadway_paths_and_hitpoints(resolution, expected):
    assert audit.classify_lod(resolution) == expected


def test_classify_lod_keeps_the_neighbouring_kinds():
    assert audit.classify_lod(2e15) == "LandContact"
    assert audit.classify_lod(6e15) == "ViewGeo"
    assert audit.classify_lod(4e13) == "GeoPhys"


# --- vertex budget -------------------------------------------------------------

def test_vertex_budget_passes_a_small_model():
    assert audit.check_lod0_vertex_budget(SimpleNamespace(lods=[_lod(0.0, faces=4, points=12)])) == []
    assert audit.check_lod0_vertex_budget(SimpleNamespace(lods=[_lod(1e13, faces=4, points=12)])) == []


def test_vertex_budget_fails_over_65535_resolved_vertices():
    model = SimpleNamespace(lods=[_lod(1.0, faces=21846, points=10)])  # 65,538 distinct corners
    issues = audit.check_lod0_vertex_budget(model)
    assert _severities(issues) == ["CRITICAL"]
    assert "LOD[0] Visual resolves to 65538 unique vertices" in issues[0][1]


def test_vertex_budget_reads_the_most_detailed_visual_lod_wherever_it_sits():
    # Vanilla numbers its visual LODs from 1 as often as from 0; the lowest resolution is read.
    heavy = _lod(1.0, faces=21846, points=10)
    light = _lod(2.0, faces=4, points=12)
    assert "LOD[1] Visual" in audit.check_lod0_vertex_budget(SimpleNamespace(lods=[light, heavy]))[0][1]


def test_raw_counts_over_the_ceiling_are_only_a_warning_when_they_resolve_under_it():
    # 65,538 face corners that all resolve to one vertex: the raw count is not the limit.
    model = SimpleNamespace(lods=[_lod(0.0, faces=21846, points=10, distinct=False)])
    issues = audit.check_lod0_vertex_budget(model)
    assert _severities(issues) == ["WARNING"]
    assert "resolves to 1 unique vertices" in issues[0][1]
    assert "under the ceiling" not in issues[0][1] and "binarize" in issues[0][1]


def test_raw_count_warning_does_not_hide_the_vehicle_body_warning():
    body = SimpleNamespace(lods=[_lod(0.0, selections=[("wheel_1_1_damper", 0)], faces=21846, points=10,
                                      normals=16385, distinct=False)])
    issues = audit.check_lod0_vertex_budget(body)
    assert _severities(issues) == ["WARNING", "WARNING"]
    assert "heavy for a vehicle body" in issues[1][1]


def test_heavy_lod_warns_only_on_a_vehicle_body():
    plain = SimpleNamespace(lods=[_lod(0.0, faces=4, points=12, normals=16385)])
    assert audit.check_lod0_vertex_budget(plain) == []
    body = SimpleNamespace(lods=[_lod(0.0, selections=[("wheel_1_1_damper", 0)], faces=4, points=12, normals=16385)])
    issues = audit.check_lod0_vertex_budget(body)
    assert _severities(issues) == ["WARNING"] and "heavy for a vehicle body" in issues[0][1]


# --- vehicle body ----------------------------------------------------------------

def test_vehicle_body_is_keyed_on_damper_selections():
    assert audit.is_vehicle_body(SimpleNamespace(lods=[_lod(1e15, selections=[("Wheel_1_1_Damper_Land", 0)])]))
    # A lone wheel model has 'wheel' selections and no damper.
    assert not audit.is_vehicle_body(SimpleNamespace(lods=[_lod(0.0, selections=[("wheel_1_1", 0)])]))


def test_class_vehicle_property_required_on_a_vehicle_body_only():
    body = [("wheel_1_1_damper", 0)]
    missing = SimpleNamespace(lods=[_lod(0.0, selections=body), _lod(1e13)])
    issues = audit.check_geometry_class_vehicle(missing)
    assert _severities(issues) == ["CRITICAL"] and "LOD[1] Geometry" in issues[0][1]
    wrong = SimpleNamespace(lods=[_lod(0.0, selections=body), _lod(1e13, properties={"class": "house"})])
    assert _severities(audit.check_geometry_class_vehicle(wrong)) == ["CRITICAL"]
    right = SimpleNamespace(lods=[_lod(0.0, selections=body), _lod(1e13, properties={"class": "Vehicle"})])
    assert audit.check_geometry_class_vehicle(right) == []
    item = SimpleNamespace(lods=[_lod(0.0), _lod(1e13)])
    assert audit.check_geometry_class_vehicle(item) == []


# --- wheel slots -------------------------------------------------------------------

VEHICLE_CONFIG = """
class CfgSlots
{
    class Slot_QuadWheel_1_1 { name = "QuadWheel_1_1"; selection = "wheel_1_1"; };
    class Slot_QuadWheel_1_2 { name = "QuadWheel_1_2"; selection = "wheel_1_2"; };
    // class Slot_Old { name = "QuadWheel_9_9"; selection = "wheel_9_9"; };
    class Slot_Battery { name = "CarBattery"; selection = "battery"; };
};
class CfgVehicles
{
    class Quad
    {
        class SimulationModule
        {
            class Axles
            {
                class Front
                {
                    class Wheels
                    {
                        class Left { inventorySlot = "QuadWheel_1_1"; };
                        class Right { inventorySlot = "QuadWheel_1_2"; };
                    };
                };
            };
        };
    };
};
"""


def test_parse_wheel_selections_follows_axles_to_cfgslots():
    sels, slots, note = audit.parse_wheel_selections(VEHICLE_CONFIG)
    assert sels == {"wheel_1_1", "wheel_1_2"}
    assert slots == {"QuadWheel_1_1", "QuadWheel_1_2"}
    assert note == ""


def test_parse_wheel_selections_says_why_it_could_not_map():
    assert "no 'class Axles' block" in audit.parse_wheel_selections("class CfgPatches {};")[2]
    assert "no inventorySlot entries" in audit.parse_wheel_selections("class Axles { class Front {}; };")[2]
    # Vanilla keeps CfgSlots in another config.cpp, so a vehicle config often has none.
    no_slots = VEHICLE_CONFIG.split("class CfgVehicles", 1)[1]
    sels, slots, note = audit.parse_wheel_selections("class CfgVehicles" + no_slots)
    assert sels == set() and slots == {"QuadWheel_1_1", "QuadWheel_1_2"} and "no CfgSlots block" in note
    other = "class CfgSlots { class Slot_X { name = \"Other\"; selection = \"x\"; }; };\nclass CfgVehicles" + no_slots
    assert "no slot named like a wheel inventorySlot" in audit.parse_wheel_selections(other)[2]


def _body(fire_selections=None):
    lods = [_lod(0.0, selections=[("wheel_1_1_damper", 0), ("wheel_1_1", 1), ("wheel_1_2", 1)], faces=2, points=6)]
    if fire_selections is not None:
        lods.append(_lod(7e15, selections=fire_selections, faces=2, points=6))
    return SimpleNamespace(lods=lods)


def test_wheel_slot_selection_missing_from_fire_geometry_is_critical():
    issues = audit.check_wheel_slot_firegeo(_body([("Wheel_1_1", 1)]), VEHICLE_CONFIG)
    assert _severities(issues) == ["CRITICAL"]
    assert "'wheel_1_2' (from CfgSlots) is missing from Fire Geometry LOD[1]" in issues[0][1]


def test_wheel_slot_selection_without_faces_warns_and_a_complete_body_passes():
    issues = audit.check_wheel_slot_firegeo(_body([("wheel_1_1", 1), ("wheel_1_2", 0)]), VEHICLE_CONFIG)
    assert _severities(issues) == ["WARNING"] and "'wheel_1_2'" in issues[0][1] and "0 faces" in issues[0][1]
    assert audit.check_wheel_slot_firegeo(_body([("wheel_1_1", 1), ("wheel_1_2", 1)]), VEHICLE_CONFIG) == []


def test_wheel_slot_check_needs_a_fire_geometry_lod_and_a_vehicle_body():
    issues = audit.check_wheel_slot_firegeo(_body(), VEHICLE_CONFIG)
    assert _severities(issues) == ["CRITICAL"] and "no Fire Geometry LOD" in issues[0][1]
    item = SimpleNamespace(lods=[_lod(0.0, selections=[("wheel_1_1", 1)], faces=1, points=3)])
    assert audit.check_wheel_slot_firegeo(item, VEHICLE_CONFIG) == []


def test_wheel_slot_check_that_cannot_map_is_a_note():
    issues = audit.check_wheel_slot_firegeo(_body([]), "class CfgPatches {};")
    assert _severities(issues) == ["NOTE"] and "Wheel-slot check not run" in issues[0][1]


# --- the py3d loader -----------------------------------------------------------------

def test_load_py3d_prefers_the_repo_fork(tmp_path, monkeypatch):
    fork = tmp_path / "py3d" / "__init__.py"
    fork.parent.mkdir()
    fork.write_text("IS_DAYZ_FORK = True\n__version__ = '1.10.1'\n", encoding="utf-8")
    monkeypatch.setattr(audit, "REPO_FORK", fork)
    monkeypatch.setattr(audit, "_fork_module", None)
    loaded = audit.load_py3d()
    assert loaded.IS_DAYZ_FORK is True and Path(loaded.__file__) == fork
    assert audit.load_py3d() is loaded  # loaded once
    assert audit.fork_version(loaded) == (1, 10, 1)


def test_fork_version_is_none_for_any_other_py3d():
    assert audit.fork_version(SimpleNamespace()) is None
    assert audit.fork_version(SimpleNamespace(IS_DAYZ_FORK=True, __version__="not.a.version")) is None
    assert audit.fork_version(SimpleNamespace(IS_DAYZ_FORK=False, __version__="1.10.1")) is None


# --- the DayZ fork's validate() findings ---------------------------------------------

FORK = SimpleNamespace(IS_DAYZ_FORK=True, __version__="1.10.1")


def _finding(code, severity, lod, msg="m"):
    return SimpleNamespace(code=code, severity=severity, lod=lod, msg=msg)


def _validated(findings):
    return SimpleNamespace(validate=lambda: list(findings))


# LOD indices as audit_p3d() maps them: (index, lod) per kind.
LOD_MAP = {"Visual": (0, None), "Geometry": (1, None), "Memory": (2, None), "ViewGeo": (3, None),
           "FireGeo": (4, None), "GeoPhys": (5, None)}


def test_fork_findings_not_run_without_the_fork_or_on_an_old_one():
    model = _validated([_finding("ERR_WINDING_INVERTED", "ERROR", 1)])
    assert audit.fork_findings(model, SimpleNamespace(), LOD_MAP) is None
    old = SimpleNamespace(IS_DAYZ_FORK=True, __version__="1.5.0")
    assert audit.fork_findings(model, old, LOD_MAP) is None
    assert audit.fork_findings(SimpleNamespace(), FORK, LOD_MAP) is None  # a model with no validate()


def test_fork_findings_map_severity_and_tag_the_lod_and_code():
    model = _validated([
        _finding("ERR_WINDING_INVERTED", "ERROR", 1, "wound opposite ways"),
        _finding("WARN_WINDING_MIXED", "WARN", 4, "mixed"),
        _finding("ERR_UNREADABLE_ROUNDTRIP", "ERROR", None, "round trip failed"),
    ])
    assert audit.fork_findings(model, FORK, LOD_MAP) == [
        ("CRITICAL", "LOD[1] [ERR_WINDING_INVERTED] wound opposite ways"),
        ("WARNING", "LOD[4] [WARN_WINDING_MIXED] mixed"),
        ("CRITICAL", "[ERR_UNREADABLE_ROUNDTRIP] round trip failed"),
    ]


def test_fork_findings_drop_what_this_script_checks_itself_on_the_same_lod():
    covered = [
        _finding("WARN_AUTOCENTER_MISSING", "WARN", 1),
        _finding("ERR_COMPONENT_NAMING", "ERROR", 1),
        _finding("WARN_COMPONENT_COVERAGE", "WARN", 1),
        _finding("WARN_NOT_WATERTIGHT", "WARN", 1),
        _finding("WARN_DEGENERATE_FACES", "WARN", 4),
        _finding("WARN_MEMORY_POS_CENTER", "WARN", 2),
        _finding("WARN_MEMORY_HAS_FACES", "WARN", 2),
        _finding("WARN_PDRIVE_PATH", "WARN", 0),
        _finding("WARN_LOD_KIND_UNKNOWN", "WARN", 5),
    ]
    assert audit.fork_findings(_validated(covered), FORK, LOD_MAP) == []


def test_fork_findings_keep_the_checks_this_script_does_not_make():
    kept = [
        _finding("ERR_COMPONENT_NAMING", "ERROR", 3),      # View Geometry: only the Geometry LOD is checked here
        _finding("WARN_COMPONENT_COVERAGE", "WARN", 4),
        _finding("ERR_COMPONENT_COVERAGE", "ERROR", 1),    # a closed part in no component
        _finding("WARN_NOT_WATERTIGHT", "WARN", 3),
        _finding("ERR_MASS_ONLY_GEOMETRY", "ERROR", 4),
        _finding("WARN_NORMALS_BUDGET", "WARN", 0),
        _finding("WARN_LOD_KIND_UNKNOWN", "WARN", 7),      # a LOD this script does not name either
        _finding("WARN_PDRIVE_PATH", "WARN", 6),           # a second Visual LOD, which this script does not read
    ]
    found = audit.fork_findings(_validated(kept), FORK, LOD_MAP)
    assert [re.search(r"\[([A-Z_]+)\]", msg).group(1) for _, msg in found] == [f.code for f in kept]
    assert _severities(found) == ["CRITICAL", "WARNING", "CRITICAL", "WARNING", "CRITICAL", "WARNING",
                                  "WARNING", "WARNING"]


def test_axis_name_guess_is_a_warning_without_model_cfg_and_dropped_with_it():
    guess = [_finding("ERR_AXIS_SELECTION_MISSING", "ERROR", 0, "no 'wheel_1_1' selection"),
             _finding("WARN_AXIS_SELECTION_EMPTY", "WARN", 0, "empty")]
    found = audit.fork_findings(_validated(guess), FORK, LOD_MAP)
    assert _severities(found) == ["WARNING", "WARNING"]
    assert all("pass --model-cfg" in msg for _, msg in found)
    assert audit.fork_findings(_validated(guess), FORK, LOD_MAP, model_cfg_checked=True) == []


def test_validate_that_raises_is_reported_not_fatal():
    def boom():
        raise IndexError("list index out of range")

    found = audit.fork_findings(SimpleNamespace(validate=boom), FORK, LOD_MAP)
    assert _severities(found) == ["WARNING"]
    assert "py3d validate() stopped: list index out of range" in found[0][1]


# --- wiring in audit_p3d() and --scan-dir ------------------------------------------------

def _component(lod):
    """Give a LOD stand-in what the per-LOD checks read: one Component01 over everything."""
    lod.selections["Component01"] = _Obj(points={pt: 1 for pt in lod.points},
                                         faces={face: 1 for face in lod.faces})
    lod.mass = None
    return lod


def test_audit_p3d_prints_fork_findings_and_fails_on_a_critical_one(tmp_path, monkeypatch, capsys):
    lods = [_lod(0.0), _component(_lod(1e13, faces=1, points=3)), _lod(1e15), _lod(6e15), _lod(7e15)]
    for lod in lods:
        lod.mass = None
    model = SimpleNamespace(lods=lods, validate=lambda: [
        _finding("ERR_WINDING_INVERTED", "ERROR", 1, "wound opposite ways"),
        _finding("WARN_AUTOCENTER_MISSING", "WARN", 1, "dropped: config.cpp decides"),
    ])
    fork = SimpleNamespace(IS_DAYZ_FORK=True, __version__="1.10.1", P3D=lambda f: model)
    monkeypatch.setattr(audit, "load_py3d", lambda: fork)
    path = tmp_path / "m.p3d"
    path.write_bytes(b"MLOD" + b"\0" * 8)

    assert audit.audit_p3d(str(path)) is False
    out = capsys.readouterr().out
    assert "--- py3d validate() ---" in out
    assert "CRITICAL: LOD[1] [ERR_WINDING_INVERTED] wound opposite ways" in out
    assert "WARN_AUTOCENTER_MISSING" not in out and "Not run:" not in out


def test_audit_p3d_says_when_the_fork_checks_did_not_run(tmp_path, monkeypatch, capsys):
    lods = [_lod(0.0), _component(_lod(1e13, faces=1, points=3)), _lod(1e15), _lod(6e15), _lod(7e15)]
    for lod in lods:
        lod.mass = None
    monkeypatch.setattr(audit, "load_py3d", lambda: SimpleNamespace(P3D=lambda f: SimpleNamespace(lods=lods)))
    path = tmp_path / "m.p3d"
    path.write_bytes(b"MLOD" + b"\0" * 8)

    audit.audit_p3d(str(path))
    out = capsys.readouterr().out
    assert "--- py3d validate() ---" in out and "Not run: this py3d is not the DayZ fork" in out


def test_audit_p3d_runs_the_wheel_slot_check_with_a_config(tmp_path, monkeypatch, capsys):
    body = _body([("wheel_1_1", 1)])
    for lod in body.lods:
        lod.mass = None
    monkeypatch.setattr(audit, "load_py3d", lambda: SimpleNamespace(P3D=lambda f: body))
    path = tmp_path / "quad.p3d"
    path.write_bytes(b"MLOD" + b"\0" * 8)
    config = tmp_path / "config.cpp"
    config.write_text(VEHICLE_CONFIG, encoding="utf-8")

    assert audit.audit_p3d(str(path), config=str(config)) is False
    out = capsys.readouterr().out
    assert "--- Whole model ---" in out
    assert "CRITICAL: Wheel-slot selection 'wheel_1_2' (from CfgSlots) is missing" in out

    audit.audit_p3d(str(path))  # no config.cpp: the check cannot run, and the output says so
    out = capsys.readouterr().out
    assert "Wheel-slot selection" not in out
    assert "the wheel-slot selections of this vehicle body were not checked" in out


def test_scan_dir_skips_backup_models(tmp_path, monkeypatch, capsys):
    (tmp_path / "old.bak").mkdir()
    for name in ("model.p3d", "model.bak.p3d", "old.bak/model.p3d"):
        (tmp_path / name).write_bytes(b"MLOD")
    audited = []
    monkeypatch.setattr(audit, "audit_p3d", lambda f, cfg=None, config=None, tally=None: audited.append(Path(f).name) or True)
    assert audit.scan_directory(str(tmp_path)) == []
    assert audited == ["model.p3d"]
    assert capsys.readouterr().out.count("Skipping backup model:") == 2
