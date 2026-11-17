"""Tests for gate_odol_sections.py and check_odol_bone_refs.py. The ODOL parser they
need is an external backend that is not in this repo, so the tests write a small
fake backend (bis_reader.py and odol_reader.py) into a temp folder and a synthetic
file whose header and LOD address table are real bytes."""
from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent


def _load(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, HERE / file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# check_odol_bone_refs.py loads the gate under this same name, so both share one module.
gate = _load("dayz_vehicles_gate_odol_sections", "gate_odol_sections.py")
bones = _load("dayz_vehicles_check_odol_bone_refs", "check_odol_bone_refs.py")


FAKE_BIS_READER = '''
import struct


class BisReader:
    def __init__(self, data):
        self.data = data
        self.position = 0

    @classmethod
    def from_file(cls, path):
        with open(path, "rb") as handle:
            return cls(handle.read())

    def read_ascii(self, count):
        out = self.data[self.position:self.position + count].decode("ascii")
        self.position += count
        return out

    def read_uint32(self):
        value = struct.unpack_from("<I", self.data, self.position)[0]
        self.position += 4
        return value

    def read_int32(self):
        value = struct.unpack_from("<i", self.data, self.position)[0]
        self.position += 4
        return value

    def read_float(self):
        value = struct.unpack_from("<f", self.data, self.position)[0]
        self.position += 4
        return value

    def read_asciiz(self):
        end = self.data.index(b"\\0", self.position)
        out = self.data[self.position:end].decode("ascii")
        self.position = end + 1
        return out
'''

FAKE_ODOL_READER = '''
from types import SimpleNamespace as NS


class ODOL_ModelInfo:
    @classmethod
    def read(cls, reader, n):
        return NS(skeleton=NS(bones=[("dashboard", ""), ("gps_marker", "dashboard"), ("nav_w00", "dashboard")]))


class _Section:
    def __init__(self, lower, upper, special, texture_index):
        self.face_lower = lower
        self.face_upper = upper
        self.special = special
        self.texture_index = texture_index
        self.material_index = 0
        self.min_bone = 0
        self.bones_count = 1
        self.area_over_tex = 1.0
        self.mat_name = ""

    def get_face_indices(self, faces):
        return list(range(self.face_lower, self.face_upper))


def _selection(name, faces, verts, sectional, sections):
    return NS(name=name, selected_faces=faces, selected_vertices=verts, is_sectional=sectional, sections=sections)


class LOD:
    READ_AT = []

    @classmethod
    def read(cls, reader, resolution):
        cls.READ_AT.append((resolution, reader.position))
        quad = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        vertices = [NS(x=x, y=y, z=z) for _ in range(3) for (x, y, z) in quad]
        faces = [NS(vertex_indices=[base, base + 1, base + 2, base + 3]) for base in (0, 4, 8)]
        faces += [NS(vertex_indices=[0, 1, 2]) for _ in range(12)]
        return NS(
            vertices=vertices,
            faces=faces,
            sections=[
                _Section(0, 1, 0x0002C000, 0),
                _Section(1, 2, 0x0000C000, 1),
                _Section(3, 15, 0x0002C000, 2),
            ],
            named_selections=[
                _selection("good", [0], [0, 1, 2, 3], True, [0]),
                _selection("nobit", [1], [4, 5, 6, 7], True, [1]),
                _selection("nosec", [2], [8, 9, 10, 11], False, []),
            ],
            textures=["mod\\\\data\\\\gps_arrow_co.paa", "#(argb,8,8,3)color(1,0,0,1,co)", "mod\\\\data\\\\cluster_co.paa"],
            materials=[NS(material_name="mod\\\\data\\\\dashboard.rvmat", emissive=(0, 0, 0, 1), diffuse=(1, 1, 1, 1))],
            uv_sets=[NS(uv_data=[0.25] * 24, is_discretized=False, min_u=0.0, max_u=1.0, min_v=0.0, max_v=1.0,
                        n_vertices=12, default_fill=False)],
            vertex_bone_ref=[NS(pairs=[(1, 255)])] * 4 + [None] * 4 + [NS(pairs=[(2, 255)])] * 4,
            b_min=NS(x=-1.0, y=-1.0, z=-1.0),
            b_max=NS(x=2.0, y=2.0, z=2.0),
            b_radius=3.0,
            or_hints=0,
            and_hints=0,
            special=0,
            proxies=[NS(model="dz\\\\vehicles\\\\wheeled\\\\proxies\\\\crew_driver", bone_index=-1, section_index=0,
                        named_selection_index=0)],
        )
'''


def _odol_bytes(resolutions=(0.0, 1100.0)):
    """Header, then the LOD address table, then one blob per LOD, last LOD first, so
    the table chains (each end is the previous start) and ends at the end of the file."""
    n = len(resolutions)
    head = b"ODOL" + struct.pack("<I", 54) + struct.pack("<i", n)
    head += b"".join(struct.pack("<f", r) for r in resolutions)
    table_at = len(head)
    blob = 40
    first_blob = table_at + n * 9
    starts = [first_blob + (n - 1 - i) * blob for i in range(n)]
    ends = [s + blob for s in starts]
    table = b"".join(struct.pack("<I", s) for s in starts) + b"".join(struct.pack("<I", e) for e in ends) + b"\0" * n
    return head + table + b"\xAB" * (n * blob), table_at, starts


@pytest.fixture
def backend(tmp_path, monkeypatch):
    root = tmp_path / "backend"
    root.mkdir()
    (root / "bis_reader.py").write_text(FAKE_BIS_READER, encoding="utf-8")
    (root / "odol_reader.py").write_text(FAKE_ODOL_READER, encoding="utf-8")
    monkeypatch.delenv(gate.BACKEND_ENV, raising=False)
    saved_path = list(sys.path)
    for name in ("bis_reader", "odol_reader"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    yield root
    sys.path[:] = saved_path
    for name in ("bis_reader", "odol_reader"):
        sys.modules.pop(name, None)


@pytest.fixture
def model(tmp_path):
    path = tmp_path / "car.p3d"
    path.write_bytes(_odol_bytes()[0])
    return path


# --- find_table -------------------------------------------------------------------

def test_find_table_finds_the_chained_table_and_its_offsets():
    data, table_at, starts = _odol_bytes()
    score, off, ls, le, pm = gate.find_table(data, 2, table_at, len(data))
    assert off == table_at
    assert ls == starts
    assert le == [s + 40 for s in starts]
    assert pm == [0, 0]
    assert score >= 150  # ends at the end of the file (100) and chains (50)


def test_find_table_prefers_the_chained_table_over_an_earlier_plausible_one():
    data, table_at, starts = _odol_bytes()
    size_after = len(data) + 18
    # A decoy that parses as a table (offsets inside the file, flags 0 or 1) but does
    # not chain and does not end at the end of the file, placed before the real one.
    decoy = struct.pack("<IIII", 30, 31, 32, 33) + b"\0\0"
    real = bytearray(data[table_at:])
    for i in range(4):  # the real table's offsets move by the decoy's 18 bytes
        value = struct.unpack_from("<I", real, i * 4)[0] + 18
        struct.pack_into("<I", real, i * 4, value)
    shifted = data[:table_at] + decoy + bytes(real)
    assert len(shifted) == size_after
    _score, off, ls, _le, _pm = gate.find_table(shifted, 2, table_at, len(shifted))
    assert off == table_at + 18
    assert ls == [s + 18 for s in starts]


def test_find_table_returns_none_when_no_table_fits():
    data = b"ODOL" + b"\0" * 64
    assert gate.find_table(data, 2, 4, len(data)) is None


# --- section helpers --------------------------------------------------------------

def _lod(special=0x0002C000, sectional=True, sections=(0,)):
    section = SimpleNamespace(special=special, texture_index=0, material_index=-1, mat_name="a.rvmat",
                              get_face_indices=lambda faces: [0])
    selection = SimpleNamespace(name="Screen_Nav", is_sectional=sectional, sections=list(sections))
    return SimpleNamespace(sections=[section], named_selections=[selection], textures=["a_co.paa"], materials=[],
                           faces=[None])


def test_selection_lookup_ignores_case():
    assert gate.ns_by_name(_lod(), "screen_nav").name == "Screen_Nav"
    assert gate.ns_by_name(_lod(), "absent") is None


def test_texture_and_material_of_a_section():
    lod = _lod()
    assert gate.tex_of(lod, lod.sections[0]) == "a_co.paa"
    assert gate.mat_of(lod, lod.sections[0]) == "a.rvmat"
    lod.sections[0].texture_index = -1
    assert gate.tex_of(lod, lod.sections[0]) == "<tex -1>"
    lod.sections[0].material_index = 5
    assert gate.mat_of(lod, lod.sections[0]) == "<mat 5>"


def test_cover_map_lists_the_sections_of_each_face():
    assert gate.cover_map(_lod()) == {0: [0]}


def test_a_drawable_selection_has_no_defect():
    assert gate.selection_defects(_lod(), "screen_nav", 0.0) == []
    assert gate.selection_defects(_lod(special=0x0002C100), "screen_nav", 0.0) == []


def test_a_section_without_the_hidden_selection_bit_is_a_defect():
    found = gate.selection_defects(_lod(special=0x0000C000), "screen_nav", 1100.0)
    assert len(found) == 1
    assert "special=0x0000C000" in found[0] and "LOD 1100.0" in found[0]


def test_a_selection_that_is_not_sectional_or_owns_no_section_is_a_defect():
    found = gate.selection_defects(_lod(sectional=False, sections=()), "screen_nav", 0.0)
    assert any("not sectional" in line for line in found)
    assert any("owns no section" in line for line in found)


def test_a_missing_selection_and_a_dangling_section_index_are_defects():
    assert "is missing" in gate.selection_defects(_lod(), "absent", 0.0)[0]
    assert "does not exist" in gate.selection_defects(_lod(sections=(7,)), "screen_nav", 0.0)[0]


def test_face_area_of_a_unit_quad():
    quad = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    lod = SimpleNamespace(vertices=[SimpleNamespace(x=x, y=y, z=z) for x, y, z in quad])
    assert gate.face_area(lod, [0, 1, 2, 3]) == pytest.approx(1.0)


# --- gate_odol_sections.py end to end ---------------------------------------------

def test_gate_passes_a_drawable_selection(backend, model, capsys):
    code = gate.main([str(model), "--backend-root", str(backend), "--selection", "good"])
    out, err = capsys.readouterr()
    assert code == 0, err
    assert "ver 54 n 2 res [0.0, 1100.0]" in out
    assert "bone[1] 'gps_marker' parent='dashboard'" in out
    assert "good: faces=1 verts=4 sectional=True sections=[0]" in out
    assert "special=0x0002C000" in out
    assert "area_mm2=1000000.0000" in out
    assert "proxy 'dz\\\\vehicles\\\\wheeled\\\\proxies\\\\crew_driver'" in out
    assert out.count("======== ODOL") == 2
    assert "FAIL" not in err


def test_gate_reads_each_lod_at_the_offset_the_table_gives(backend, model):
    assert gate.main([str(model), "--backend-root", str(backend)]) == 0
    _data, _table_at, starts = _odol_bytes()
    assert sys.modules["odol_reader"].LOD.READ_AT == [(0.0, starts[0]), (1100.0, starts[1])]


def test_gate_fails_undrawable_and_missing_selections(backend, model, capsys):
    code = gate.main([str(model), "--backend-root", str(backend), "--lod", "0",
                      "--selection", "nobit", "--selection", "nosec", "--selection", "absent"])
    _out, err = capsys.readouterr()
    assert code == 1
    assert "FAIL: LOD 0.0: selection nobit section 1 has special=0x0000C000" in err
    assert "FAIL: LOD 0.0: selection nosec is not sectional" in err
    assert "FAIL: LOD 0.0: selection nosec owns no section" in err
    assert "FAIL: LOD 0.0: selection absent is missing" in err


def test_gate_reads_the_backend_root_from_the_environment(backend, model, monkeypatch):
    monkeypatch.setenv(gate.BACKEND_ENV, str(backend))
    assert gate.main([str(model), "--selection", "good"]) == 0


def test_gate_input_errors_exit_2(backend, model, tmp_path, capsys):
    assert gate.main([]) == 2
    capsys.readouterr()

    assert gate.main([str(tmp_path / "absent.p3d"), "--backend-root", str(backend)]) == 2
    assert "INPUT_ERROR: missing file" in capsys.readouterr().err

    assert gate.main([str(model)]) == 2
    assert "no ODOL parser backend" in capsys.readouterr().err

    assert gate.main([str(model), "--backend-root", str(tmp_path)]) == 2
    assert "no odol_reader.py in backend root" in capsys.readouterr().err

    assert gate.main([str(model), "--backend-root", str(backend), "--lod", "2"]) == 2
    assert "LOD 2.0 is not in" in capsys.readouterr().err

    mlod = tmp_path / "source.p3d"
    mlod.write_bytes(b"MLOD" + b"\0" * 64)
    assert gate.main([str(mlod), "--backend-root", str(backend)]) == 2
    assert "no ODOL signature" in capsys.readouterr().err


# --- check_odol_bone_refs.py ------------------------------------------------------

def test_bone_names_of_a_vertex():
    skeleton = [("dashboard", ""), ("gps_marker", "dashboard")]
    lod = SimpleNamespace(vertex_bone_ref=[SimpleNamespace(pairs=[(1, 255)]), None, SimpleNamespace(pairs=[(9, 1)])])
    assert bones.bone_names(lod, skeleton, 0) == "gps_marker(b1,w255)"
    assert bones.bone_names(lod, skeleton, 0, with_weight=False) == "gps_marker(b1)"
    assert bones.bone_names(lod, skeleton, 1) == "NONE/static"
    assert bones.bone_names(lod, skeleton, 2) == "?(b9,w1)"
    assert bones.bone_names(lod, skeleton, 99) == "NONE/static"


def test_bone_report_lists_matching_sections_and_the_reference(backend, model, capsys):
    code = bones.main([str(model), "--backend-root", str(backend), "--lod", "0", "--texture", "gps_arrow",
                       "--texture", "cluster", "--max-faces", "2", "--reference-texture", "cluster_co.paa"])
    out, err = capsys.readouterr()
    assert code == 0, err
    assert "skeleton bones: 3" in out
    assert "=== LOD 0 ===" in out
    assert "gps_arrow sec[0] faces=[0] verts=[0, 1, 2, 3]" in out
    assert "v[0] bone=gps_marker(b1,w255)" in out
    # the cluster section has twelve faces, so --max-faces 2 leaves it out of the list
    assert "cluster sec[2]" not in out
    assert "REFERENCE(renders) sec[2] first vert bone=gps_marker(b1)" in out


def test_bone_report_without_max_faces_lists_large_sections(backend, model, capsys):
    assert bones.main([str(model), "--backend-root", str(backend), "--lod", "0", "--texture", "CLUSTER"]) == 0
    assert "cluster sec[2]" in capsys.readouterr().out


def test_bone_report_input_errors_exit_2(backend, model, tmp_path, capsys):
    assert bones.main([str(model), "--backend-root", str(backend)]) == 2
    assert "name at least one --texture" in capsys.readouterr().err

    assert bones.main([str(tmp_path / "absent.p3d"), "--texture", "x"]) == 2
    assert "INPUT_ERROR: missing file" in capsys.readouterr().err

    assert bones.main([str(model), "--texture", "x"]) == 2
    assert "no ODOL parser backend" in capsys.readouterr().err
