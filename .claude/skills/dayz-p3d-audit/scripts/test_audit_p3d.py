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
        (1e10, "ShadowVolume"),
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


@pytest.mark.parametrize("resolution", [3e13, 7e13])
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
    return _Obj(points=points, faces=faces, selections=sels, properties=properties or {})


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


def test_watertight_closed_and_open():
    assert audit.check_watertight(_stub_lod()) == []
    open_mesh = _stub_lod(face_indices=TETRA_FACES[:3])
    assert _severities(audit.check_watertight(open_mesh)) == ["WARNING"]


def test_degenerate_face_detected():
    lod = _stub_lod(face_indices=TETRA_FACES + [(0, 0, 1)])
    assert _severities(audit.check_degenerate_faces(lod)) == ["WARNING"]


def test_required_lods_firegeo_note_uses_7e15():
    issues = audit.check_required_lods({"Visual": 0, "Geometry": 0, "Memory": 0, "GeoPhys": 0})
    assert issues == [("NOTE", "Missing FireGeo LOD (res ~7e15). No ballistic damage zones.")]


def test_face_winding_check_removed():
    assert not hasattr(audit, "check_face_winding")


# --- end-to-end on a byte-level MLOD file -------------------------------------

def _asciiz(text: str) -> bytes:
    return text.encode("utf-8") + b"\0"


def _write_lod(resolution, points, faces, selections=(), properties=()):
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


def test_audit_p3d_flags_lowercase_component(tmp_path, capsys):
    pytest.importorskip("py3d")
    geometry = _write_lod(1e13, TETRA_POINTS, TETRA_FACES, selections=[("component01", FULL)])
    memory = _write_lod(1e15, [(0.0, 0.0, 0.0)], [])
    visual = _write_lod(0.0, TETRA_POINTS, TETRA_FACES)
    model = tmp_path / "bad.p3d"
    _write_mlod(model, [visual, geometry, memory])

    assert audit.audit_p3d(str(model)) is False
    assert "'component01' (lowercase)" in capsys.readouterr().out


def test_audit_p3d_rejects_odol(tmp_path, capsys):
    model = tmp_path / "binarized.p3d"
    model.write_bytes(b"ODOL" + b"\0" * 16)
    assert audit.audit_p3d(str(model)) is False
    assert "Not MLOD" in capsys.readouterr().out
