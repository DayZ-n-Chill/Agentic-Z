"""Tests for audit_getin_wheels.py: the three exit states, the report lines and the
LOD and selection helpers, on tiny synthetic MLOD files written byte by byte."""
from __future__ import annotations

import importlib.util
import struct
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load_audit():
    spec = importlib.util.spec_from_file_location("dayz_vehicles_audit_getin_wheels", HERE / "audit_getin_wheels.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _load_audit()


# --- byte-level MLOD writer ----------------------------------------------------

def _asciiz(text: str) -> bytes:
    return text.encode("utf-8") + b"\0"


def _write_lod(resolution, points, faces=(), selections=()):
    """One P3DM LOD. selections is a list of (name, point indexes, face indexes)."""
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
    for name, pt_idx, face_idx in selections:
        out += b"\x01" + _asciiz(name)
        out += struct.pack("<L", len(points) + len(faces))
        out += bytes(1 if i in pt_idx else 0 for i in range(len(points)))
        out += bytes(1 if i in face_idx else 0 for i in range(len(faces)))
    out += b"\x01" + _asciiz("#EndOfFile#") + struct.pack("<L", 0)
    out += struct.pack("f", resolution)
    return bytes(out)


def _write_mlod(path: Path, lods) -> Path:
    path.write_bytes(b"MLOD" + struct.pack("<LL", 257, len(lods)) + b"".join(lods))
    return path


def _memory_lod(skip=(), one_point_axis=(), mirrored=()):
    """A Memory LOD with every get-in anchor (one point each) and every wheel axis
    (two points each, along +X, or along -X for the names in `mirrored`)."""
    points, selections = [], []
    for name in audit.GETIN_MEM:
        if name in skip:
            continue
        selections.append((name, [len(points)], []))
        points.append((0.5, 1.0, 0.25))
    for name in audit.WHEEL_AX:
        if name in skip:
            continue
        first = len(points)
        points.append((0.0, 0.3, 1.0))
        if name in one_point_axis:
            selections.append((name, [first], []))
            continue
        points.append((-1.0 if name in mirrored else 1.0, 0.3, 1.0))
        selections.append((name, [first, first + 1], []))
    return _write_lod(1e15, points, selections=selections)


TRIANGLE = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]


def _seat_lod(resolution, names=None):
    """A collision LOD of one triangle that every seat selection (or `names`) covers."""
    names = audit.SEAT_SEL if names is None else names
    return _write_lod(resolution, TRIANGLE, [(0, 1, 2)], [(n, [0, 1, 2], [0]) for n in names])


def _good_model(tmp_path, **memory):
    return _write_mlod(tmp_path / "car.p3d", [_write_lod(0.0, TRIANGLE, [(0, 1, 2)]), _seat_lod(1e13),
                                             _memory_lod(**memory), _seat_lod(6e15), _seat_lod(7e15)])


# --- helpers that need no model -------------------------------------------------

@pytest.mark.parametrize(
    "resolution, expected",
    [
        (0.0, "Vis0"), (1.0, "Vis1"), (1e13, "Geo"), (1e15, "Mem"), (2e15, "Land"), (6e15, "View"),
        (6999999976046592.0, "Fire"),  # FireGeometry as stored on disk, not the round 7e15
        (1100.0, "1.1e+03"),
    ],
)
def test_lodname(resolution, expected):
    assert audit.lodname(resolution) == expected


def test_axis_dir_is_a_rounded_unit_vector():
    assert audit.axis_dir([(0.0, 0.0, 0.0), (0.0, 0.0, 2.0)]) == [0.0, 0.0, 1.0]
    assert audit.axis_dir([(1.0, 1.0, 1.0), (-2.0, 1.0, 1.0)]) == [-1.0, 0.0, 0.0]
    assert audit.axis_dir([(0.0, 0.0, 0.0)]) is None


def test_no_input_is_exit_2(capsys):
    assert audit.main([]) == 2
    assert "USAGE: audit_getin_wheels.py" in capsys.readouterr().err


def test_missing_file_is_an_input_error_not_a_defect(tmp_path, capsys):
    assert audit.main([str(tmp_path / "gone.p3d")]) == 2
    captured = capsys.readouterr()
    assert "INPUT_ERROR: missing file:" in captured.err
    assert captured.out == ""


# --- end to end on synthetic models ----------------------------------------------

def test_unparseable_file_is_an_input_error(tmp_path, capsys):
    pytest.importorskip("py3d")
    bad = tmp_path / "bad.p3d"
    bad.write_bytes(b"not a model")
    assert audit.main([str(bad)]) == 2
    assert "INPUT_ERROR: cannot parse" in capsys.readouterr().err


def test_complete_model_passes_and_prints_the_report(tmp_path, capsys):
    pytest.importorskip("py3d")
    model = _good_model(tmp_path)
    assert audit.main([str(model)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "car.p3d | LODs: Vis0, Geo, Mem, View, Fire" in captured.out
    assert "pos_driver         OK  n=1 centroid=(0.50,1.00,0.25)" in captured.out
    assert "wheel_1_1_axis     dir=[1.0, 0.0, 0.0] (n=2)" in captured.out
    assert f"-- View seat selections present: {audit.SEAT_SEL}" in captured.out
    assert f"-- Fire seat selections present: {audit.SEAT_SEL}" in captured.out


def test_mirrored_wheel_axes_show_in_the_report_without_failing(tmp_path, capsys):
    pytest.importorskip("py3d")
    model = _good_model(tmp_path, mirrored=("wheel_2_1_axis", "wheel_2_2_axis"))
    assert audit.main([str(model)]) == 0
    out = capsys.readouterr().out
    assert "wheel_1_1_axis     dir=[1.0, 0.0, 0.0]" in out
    assert "wheel_2_1_axis     dir=[-1.0, 0.0, 0.0]" in out


def test_model_without_memory_lod_fails(tmp_path, capsys):
    pytest.importorskip("py3d")
    model = _write_mlod(tmp_path / "nomem.p3d", [_seat_lod(1e13), _seat_lod(6e15)])
    assert audit.main([str(model)]) == 1
    captured = capsys.readouterr()
    assert "NO Memory LOD" in captured.out
    assert "FAIL: " in captured.err and "missing Memory LOD" in captured.err


def test_each_missing_piece_is_its_own_fail_line(tmp_path, capsys):
    pytest.importorskip("py3d")
    memory = _memory_lod(skip=("pos_codriver",), one_point_axis=("wheel_1_2_axis",))
    seats = ["seat_driver", "seatback_driver", "seatback_codriver"]  # no seat_codriver anywhere
    model = _write_mlod(tmp_path / "broken.p3d", [_seat_lod(1e13, seats), memory, _seat_lod(6e15, seats)])
    assert audit.main([str(model)]) == 1
    captured = capsys.readouterr()
    assert "pos_codriver       ABSENT" in captured.out
    assert "Memory selection pos_codriver missing or empty" in captured.err
    assert "wheel axis wheel_1_2_axis needs at least two points" in captured.err
    assert "seat selection seat_codriver absent from View/Geometry" in captured.err
    assert captured.err.count("FAIL: ") == 3


def test_seats_only_in_fire_geometry_do_not_count(tmp_path, capsys):
    pytest.importorskip("py3d")
    model = _write_mlod(tmp_path / "fireonly.p3d", [_memory_lod(), _seat_lod(7e15)])
    assert audit.main([str(model)]) == 1
    assert "no ViewGeometry or Geometry LOD for seat selections" in capsys.readouterr().err


def test_selection_with_faces_only_is_read_through_its_faces(tmp_path):
    py3d = pytest.importorskip("py3d")
    path = _write_mlod(tmp_path / "faces.p3d", [_write_lod(6e15, TRIANGLE, [(0, 1, 2)], [("seat_driver", [], [0])])])
    with open(path, "rb") as handle:
        lod = py3d.P3D(handle).lods[0]
    assert sorted(audit.sel_points(lod, "seat_driver")) == sorted(TRIANGLE)
    assert audit.sel_points(lod, "seat_codriver") is None


def test_one_bad_input_stops_the_run_before_any_report(tmp_path, capsys):
    pytest.importorskip("py3d")
    good = _good_model(tmp_path)
    assert audit.main([str(good), str(tmp_path / "gone.p3d")]) == 2
    assert capsys.readouterr().out == ""
