"""1.6.0: #UVSet# fidelity.

Measured on 2026-09-01 with 1.5.0: re-saving a skinned body that carried two
UV sets dropped the second one (4,761,261 -> 4,409,836 bytes), and a Memory
LOD from a BI-authored file lost the empty #UVSet# tag that Object Builder
writes for LODs without faces. LOD.read discarded every #UVSet#; LOD.write
emitted set 0 only, and only when the LOD had faces.

The tests count tags with an independent walker (helpers.scan_taggs) so the
instrument does not share the reader under test.
"""

import glob
import os
import struct

import pytest

from builders import build_cube_p3d, build_memory_lod, build_two_uvsets_p3d
from helpers import (EMPTY_UVSET_TAG, EOF_TAG, assert_sem_inv, f32, read_p3d,
                     scan_taggs, uvset_inventory, write_bytes)


def _payload_size(lod):
    return lod.num_vertices * 8 + 4


def _uvset_tag(uv_id, payload):
    body = struct.pack("<L", uv_id) + payload
    return b"\x01#UVSet#\0" + struct.pack("<L", len(body)) + body


def _splice_before_eof(data, tag_bytes, lod=0):
    """Insert *tag_bytes* right before the #EndOfFile# tag of LOD *lod*."""
    pos = -1
    for _ in range(lod + 1):
        pos = data.index(EOF_TAG, pos + 1)
    return data[:pos] + tag_bytes + data[pos:]


# ---- round trip -------------------------------------------------------------

def test_two_uv_sets_survive_read_write(fork):
    """Set 1 comes back per vertex (f32) and uv_set_ids() reports [0, 1]."""
    p3d = build_two_uvsets_p3d(fork)
    vis = p3d.lods[0]
    assert vis.uv_set_ids() == [0, 1]
    reread = assert_sem_inv(fork, p3d)
    rvis = reread.lods[0]
    assert rvis.uv_set_ids() == [0, 1]
    for fa, fb in zip(vis.faces, rvis.faces):
        for va, vb in zip(fa.vertices, fb.vertices):
            assert vb.uv_sets[1] == tuple(f32(u) for u in va.uv_sets[1])
            assert vb.uv_sets[1] != vb.uv  # set 1 is not a copy of set 0


def test_round_trip_is_byte_exact_with_the_expected_uvset_count_per_lod(fork):
    """Write -> read -> write is byte-identical, and the independent walker
    finds the expected #UVSet# inventory: Visual [0, 1], Geometry [0],
    Memory [0] with the 4-byte payload, all placed last before #EndOfFile#."""
    p3d = build_two_uvsets_p3d(fork)
    d1 = write_bytes(p3d)
    d2 = write_bytes(read_p3d(fork, d1))
    assert d1 == d2
    vis, geo, mem = p3d.lods
    assert _payload_size(vis) == 6 * 4 * 8 + 4
    assert uvset_inventory(d1) == [
        [(0, _payload_size(vis)), (1, _payload_size(vis))],
        [(0, _payload_size(geo))],
        [(0, 4)],
    ]
    for taggs in scan_taggs(d1):
        names = [t[0] for t in taggs]
        assert names[-1] == "#EndOfFile#"
        first = names.index("#UVSet#")
        assert all(n == "#UVSet#" for n in names[first:-1])


def test_faceless_lod_writes_the_empty_uvset_tag(fork):
    """A Memory LOD (0 faces) gets exactly one #UVSet# whose payload is the
    4-byte id 0, immediately before #EndOfFile#. 1.5.0 wrote no tag."""
    p3d = fork.P3D()
    p3d.lods.append(build_memory_lod(fork, [("pos center", (0.0, 0.0, 0.0))]))
    data = write_bytes(p3d)
    assert uvset_inventory(data) == [[(0, 4)]]
    tail = EMPTY_UVSET_TAG + EOF_TAG + struct.pack("<L", 0) \
        + struct.pack("f", 1.0e15)
    assert data.endswith(tail)
    reread = read_p3d(fork, data)
    assert reread.lods[0].uv_set_ids() == [0]
    assert list(reread.lods[0].selections) == ["pos center"]


def test_upstream_reads_the_empty_uvset_tag(fork, upstream):
    """Object Builder parity must not break the upstream reader."""
    p3d = fork.P3D()
    p3d.lods.append(build_memory_lod(fork, [("pos center", (0.0, 0.0, 0.0))]))
    up = read_p3d(upstream, write_bytes(p3d))
    assert len(up.lods) == 1 and len(up.lods[0].points) == 1
    assert list(up.lods[0].selections) == ["pos center"]
    assert up.lods[0].resolution == f32(1.0e15)


def test_set_zero_tag_stays_ignored_on_read(fork):
    """The face record is the source of set 0 (upstream behaviour kept): a
    #UVSet# id 0 payload that disagrees with the faces does not override
    them, and the next write emits the face values again."""
    p3d = build_cube_p3d(fork)
    data = write_bytes(p3d)
    lod = p3d.lods[0]
    head = b"\x01#UVSet#\0" + struct.pack("<L", _payload_size(lod)) \
        + struct.pack("<L", 0)
    start = data.index(head) + len(head)
    garbage = struct.pack("ff", 9.0, 9.0) * lod.num_vertices
    tampered = data[:start] + garbage + data[start + len(garbage):]
    assert tampered != data and len(tampered) == len(data)
    reread = read_p3d(fork, tampered)
    for fa, fb in zip(lod.faces, reread.lods[0].faces):
        for va, vb in zip(fa.vertices, fb.vertices):
            assert vb.uv == tuple(f32(u) for u in va.uv)
    assert write_bytes(reread) == data


def test_faceless_lod_keeps_a_uv_set_whose_id_is_not_zero(fork):
    """A point-only LOD can carry a #UVSet# with a non-zero id and no pairs.
    There are no face vertices to hang it on, so it lives on the LOD itself
    and is written back as the bare 4-byte id."""
    p3d = fork.P3D()
    p3d.lods.append(build_memory_lod(fork, [("pos center", (0.0, 0.0, 0.0))]))
    data = _splice_before_eof(write_bytes(p3d), _uvset_tag(2, b""))
    reread = read_p3d(fork, data)
    lod = reread.lods[0]
    assert lod.faceless_uv_sets == [2]
    assert lod.uv_set_ids() == [0, 2]
    assert write_bytes(reread) == data
    assert uvset_inventory(data) == [[(0, 4), (2, 4)]]


def test_faceless_uv_set_with_a_payload_raises(fork):
    p3d = fork.P3D()
    p3d.lods.append(build_memory_lod(fork, [("pos center", (0.0, 0.0, 0.0))]))
    bad = _splice_before_eof(write_bytes(p3d),
                             _uvset_tag(2, struct.pack("ff", 0.0, 0.0)))
    with pytest.raises(ValueError) as ei:
        read_p3d(fork, bad)
    assert "expected 4 in a LOD without faces" in str(ei.value)


def test_faceless_uv_set_declared_twice_raises(fork):
    p3d = fork.P3D()
    p3d.lods.append(build_memory_lod(fork, [("pos center", (0.0, 0.0, 0.0))]))
    tag = _uvset_tag(2, b"")
    data = _splice_before_eof(_splice_before_eof(write_bytes(p3d), tag), tag)
    with pytest.raises(ValueError) as ei:
        read_p3d(fork, data)
    assert "appears twice" in str(ei.value)


# ---- editing helpers keep the extra sets ------------------------------------

def test_triangulate_keeps_extra_uv_sets(fork):
    p3d = build_two_uvsets_p3d(fork)
    vis = p3d.lods[0]
    expected = [(fa.vertices[i].uv, fa.vertices[i].uv_sets[1])
                for fa in vis.faces for i in (0, 1, 2, 0, 2, 3)]
    assert vis.triangulate() == 6
    got = [(v.uv, v.uv_sets[1]) for fa in vis.faces for v in fa.vertices]
    assert got == expected
    assert vis.uv_set_ids() == [0, 1]
    assert_sem_inv(fork, p3d)


def test_make_double_sided_keeps_extra_uv_sets(fork):
    p3d = build_two_uvsets_p3d(fork)
    vis = p3d.lods[0]
    originals = [[(v.uv, v.uv_sets[1]) for v in fa.vertices]
                 for fa in vis.faces]
    assert vis.make_double_sided() == 6
    twins = vis.faces[6:]
    for orig, twin in zip(originals, twins):
        assert [(v.uv, v.uv_sets[1]) for v in twin.vertices] == \
            list(reversed(orig))
    assert_sem_inv(fork, p3d)


def test_vertices_without_the_set_are_written_as_zero_zero(fork):
    """add_proxy() appends a face whose vertices carry no set 1: it is
    written as (0, 0), what Object Builder assigns to new faces, and reads
    back as such. The other vertices keep their values."""
    p3d = build_two_uvsets_p3d(fork)
    vis = p3d.lods[0]
    vis.add_proxy("\\dz\\data\\proxies\\flag", 1)
    proxy_face = vis.faces[-1]
    assert all(1 not in v.uv_sets for v in proxy_face.vertices)
    reread = read_p3d(fork, write_bytes(p3d))
    rvis = reread.lods[0]
    assert rvis.uv_set_ids() == [0, 1]
    assert [v.uv_sets[1] for v in rvis.faces[-1].vertices] == [(0.0, 0.0)] * 3
    for fa, fb in zip(vis.faces[:-1], rvis.faces[:-1]):
        for va, vb in zip(fa.vertices, fb.vertices):
            assert vb.uv_sets[1] == tuple(f32(u) for u in va.uv_sets[1])


# ---- fail closed ------------------------------------------------------------

def test_extra_set_with_the_wrong_payload_length_raises(fork):
    data = write_bytes(build_cube_p3d(fork))
    bad = _splice_before_eof(data, _uvset_tag(1, b"\0" * 8 * 5))
    with pytest.raises(ValueError) as ei:
        read_p3d(fork, bad)
    msg = str(ei.value)
    assert "#UVSet# id 1" in msg and "24 face vertices" in msg


def test_extra_set_declared_twice_raises(fork):
    data = write_bytes(build_cube_p3d(fork))
    tag = _uvset_tag(1, struct.pack("ff", 0.25, 0.75) * 24)
    twice = _splice_before_eof(_splice_before_eof(data, tag), tag)
    with pytest.raises(ValueError) as ei:
        read_p3d(fork, twice)
    assert "appears twice" in str(ei.value)


def test_uvset_shorter_than_its_id_raises(fork):
    data = write_bytes(build_cube_p3d(fork))
    bad = _splice_before_eof(
        data, b"\x01#UVSet#\0" + struct.pack("<L", 2) + b"\0\0")
    with pytest.raises(ValueError) as ei:
        read_p3d(fork, bad)
    assert "shorter than the 4-byte" in str(ei.value)


@pytest.mark.parametrize("bad_id", [0, -1, "1", 1.0, True, 2 ** 32],
                         ids=["zero", "negative", "str", "float", "bool",
                              "too-big"])
def test_invalid_uv_set_id_is_rejected_on_write(fork, bad_id):
    p3d = build_cube_p3d(fork)
    p3d.lods[0].faces[0].vertices[0].uv_sets[bad_id] = (0.0, 0.0)
    with pytest.raises(ValueError) as ei:
        write_bytes(p3d)
    assert "invalid UV set id" in str(ei.value)


def test_save_verify_catches_a_dropped_uv_set(fork, tmp_path, monkeypatch):
    """save(verify=True) refuses a write that lost a UV set (the 1.5.0
    defect, reproduced by monkeypatch) and leaves the previous file intact."""
    p3d = build_two_uvsets_p3d(fork)
    target = tmp_path / "two.p3d"
    p3d.save(str(target), verify=True)
    before = target.read_bytes()
    orig_write = fork.LOD.write

    def lossy_write(self, f):
        saved = [(v, v.uv_sets) for fa in self.faces for v in fa.vertices]
        for v, _ in saved:
            v.uv_sets = {}
        try:
            return orig_write(self, f)
        finally:
            for v, sets in saved:
                v.uv_sets = sets

    monkeypatch.setattr(fork.LOD, "write", lossy_write)
    with pytest.raises(ValueError) as ei:
        p3d.save(str(target), verify=True)
    assert "UV sets differ in LOD 0" in str(ei.value)
    assert target.read_bytes() == before
    assert glob.glob(os.path.join(str(tmp_path), "*.tmp.*")) == []


# ---- CLI --------------------------------------------------------------------

def test_cli_info_and_diff_report_uv_sets(fork, tmp_path):
    from test_s2_cli import run_cli, write
    two = write(fork, build_two_uvsets_p3d(fork), tmp_path / "two.p3d")
    out = run_cli("info", two).stdout.splitlines()
    assert "lod.0.uv_sets: 0;1" in out
    assert "lod.1.uv_sets: 0" in out
    assert "lod.2.uv_sets: 0" in out

    one = build_two_uvsets_p3d(fork)
    for fa in one.lods[0].faces:
        for v in fa.vertices:
            v.uv_sets.clear()
    one_path = write(fork, one, tmp_path / "one.p3d")
    r = run_cli("diff", two, one_path)
    assert r.returncode == 1
    assert r.stdout.splitlines() == ["diff.lod.0.uv_sets: 0;1 != 0",
                                     "total: 1"]
    assert run_cli("diff", two, two).stdout.splitlines() == ["total: 0"]
