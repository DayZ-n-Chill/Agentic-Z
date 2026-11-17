"""1.7.0: #Selected# fidelity.

`#Selected#` is the editor's current selection: one byte per point followed
by one per face, the layout of a named selection. Up to 1.6.0 py3d read it
into nothing and never wrote it back, so a file written by Object Builder
lost it on save - measured on 2026-09-02 over MLOD written by BI:
InfectedSpecialLODs.p3d -863 B (LOD1 -45, LOD2 -409, LOD3 -409) and
WeaponSpecialLODs.p3d -202 B (LOD1 -30, LOD2 -48, LOD3 -60, LOD4 -64), which
was the whole remaining delta.

Two measurements bound what this is worth:

- binarize.exe discards it. Five variants of sedanwheel_mlod.p3d differing
  only in the tag - absent, all-zero and all-one over the 8 LODs - produced
  the SAME ODOL (sha256 620d4fec1646fcdb...), while a point moved 1 cm gave
  610ae73593eed77a... and the texture cleared on the same faces gave
  ebc0c0dcc4ee18e4... So this is not about the game.
- Object Builder 2.3.0.159800 does not require it - it opens a 4-LOD file
  stripped of every #Selected#, keeps all four LODs and saves without adding
  one - but it does preserve the payload verbatim when it is there. It is
  the user's editor state, and dropping it silently discards their work.

The content therefore matters, not just the presence: regenerating the tag
as zeroes of the right length (what the reference p3d.py does) passes a
presence check and still loses the selection. Hence
`test_selected_content_is_preserved_not_zeroed`.

The independent walker (helpers.selected_payloads) reads the bytes without
going through the reader under test.
"""

import struct

import pytest

from builders import build_cube_p3d, build_memory_lod, build_multilod_p3d
from helpers import (EOF_TAG, assert_sem_inv, read_p3d, scan_taggs,
                     selected_payloads, write_bytes)


def _select(fork, lod, point_idx=(), face_idx=()):
    """Set lod.selected to a Selection over the given positional indices."""
    sel = fork.Selection(lod.points, lod.faces)
    for i in point_idx:
        sel.points[lod.points[i]] = 1
    for i in face_idx:
        sel.faces[lod.faces[i]] = 1
    lod.selected = sel
    return sel


def _tag_names(data, lod=0):
    return [name for name, _, _ in scan_taggs(data)[lod]]


def _selected_tag(payload):
    return b"\x01#Selected#\0" + struct.pack("<L", len(payload)) + payload


def _splice_before_eof(data, tag_bytes, lod=0):
    """Insert *tag_bytes* right before the #EndOfFile# tag of LOD *lod*."""
    pos = -1
    for _ in range(lod + 1):
        pos = data.index(EOF_TAG, pos + 1)
    return data[:pos] + tag_bytes + data[pos:]


# ---- round trip -------------------------------------------------------------

def test_selected_survives_read_write(fork):
    """It comes back as a Selection over the same points and faces."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    _select(fork, lod, point_idx=(0, 3, 7), face_idx=(2,))
    reread = read_p3d(fork, write_bytes(p3d))
    rlod = reread.lods[0]
    assert rlod.selected is not None
    assert sorted(rlod.points.index(p) for p in rlod.selected.points) == [0, 3, 7]
    assert sorted(rlod.faces.index(f) for f in rlod.selected.faces) == [2]


def test_selected_content_is_preserved_not_zeroed(fork):
    """The payload comes back byte for byte.

    This is the test the 1.6.0 engine fails: it wrote no tag at all. It also
    fails a codec that regenerates the tag as zeroes, because the bytes are
    compared, not the tag's presence.
    """
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    _select(fork, lod, point_idx=(1, 2, 5), face_idx=(0, 4))
    data = write_bytes(p3d)
    payload = selected_payloads(data)[0]
    assert payload is not None, "#Selected# was not written"
    expected = bytes([1 if i in (1, 2, 5) else 0 for i in range(8)]) + \
               bytes([1 if i in (0, 4) else 0 for i in range(6)])
    assert payload == expected
    assert payload != b"\0" * len(payload), \
        "an all-zero payload would be a regenerated tag, not the selection"
    # and it survives a second cycle
    assert selected_payloads(write_bytes(read_p3d(fork, data)))[0] == expected


def test_round_trip_is_byte_exact_and_the_tag_sits_before_named_selections(fork):
    """Write -> read -> write is byte-identical, and the independent walker
    finds #Selected# in the slot Object Builder writes it in: after
    #SharpEdges#, before the named selections."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.sharp_edges.append((0, 1))
    _select(fork, lod, point_idx=(4,), face_idx=(1, 3))
    first = write_bytes(p3d)
    second = write_bytes(read_p3d(fork, first))
    assert first == second

    names = _tag_names(first)
    assert names.index("#SharpEdges#") < names.index("#Selected#") \
        < names.index("Component01")


def test_a_lod_without_the_tag_does_not_get_one(fork):
    """py3d never invents the tag - neither does Object Builder."""
    p3d = build_cube_p3d(fork)
    assert p3d.lods[0].selected is None
    data = write_bytes(p3d)
    assert selected_payloads(data) == [None]
    assert "#Selected#" not in _tag_names(data)


def test_per_lod_presence_is_independent(fork):
    """A BI-authored file carries the tag in some LODs and not others -
    DayzSkeleton.p3d has none at all, and the visual LOD of
    WeaponSpecialLODs.p3d has none while its four special LODs do."""
    p3d = build_multilod_p3d(fork)
    assert len(p3d.lods) >= 2
    _select(fork, p3d.lods[1], point_idx=(0,))
    data = write_bytes(p3d)
    payloads = selected_payloads(data)
    assert payloads[0] is None
    assert payloads[1] is not None
    reread = read_p3d(fork, data)
    assert reread.lods[0].selected is None
    assert reread.lods[1].selected is not None


def test_faceless_lod_carries_the_tag_over_its_points(fork):
    """A Memory LOD has no faces, so the payload is one byte per point."""
    p3d = fork.P3D()
    lod = build_memory_lod(fork, [("pilot", (0.0, 0.0, 0.0)),
                                  ("camera", (0.0, 1.0, 0.0))])
    p3d.lods.append(lod)
    _select(fork, lod, point_idx=(1,))
    data = write_bytes(p3d)
    payload = selected_payloads(data)[0]
    assert payload == b"\x00\x01"
    assert read_p3d(fork, data).lods[0].selected is not None


def test_semantic_invariants_hold_with_the_tag(fork):
    p3d = build_cube_p3d(fork)
    _select(fork, p3d.lods[0], point_idx=(0, 1), face_idx=(5,))
    assert_sem_inv(fork, p3d)


# ---- the model keeps it consistent -----------------------------------------

def test_deleting_a_face_drops_it_from_the_selection(fork):
    """Membership is by identity, as in a named selection: an element that
    leaves the LOD leaves the tag with it, and the payload stays the length
    the format requires."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    _select(fork, lod, point_idx=(0,), face_idx=(0, 1))
    doomed = lod.faces[0]
    lod.faces.remove(doomed)
    for sel in list(lod.selections.values()):
        sel.faces.pop(doomed, None)
    lod.selected.faces.pop(doomed, None)
    data = write_bytes(p3d)
    payload = selected_payloads(data)[0]
    assert len(payload) == len(lod.points) + len(lod.faces)
    reread = read_p3d(fork, data)
    assert len(reread.lods[0].selected.faces) == 1


# ---- fail closed ------------------------------------------------------------

def test_wrong_payload_length_raises(fork):
    """A payload that does not match the LOD's counts would bind weights to
    the wrong elements; upstream's Selection.read ignores the declared
    length, so the check lives here."""
    p3d = build_cube_p3d(fork)
    data = write_bytes(p3d)  # 8 points + 6 faces
    bad = _splice_before_eof(data, _selected_tag(b"\x01" * 13))
    with pytest.raises(ValueError, match=r"#Selected#.*expected 14"):
        read_p3d(fork, bad)


def test_selected_declared_twice_raises(fork):
    p3d = build_cube_p3d(fork)
    _select(fork, p3d.lods[0], point_idx=(0,))
    data = write_bytes(p3d)
    twice = _splice_before_eof(data, _selected_tag(b"\0" * 14))
    with pytest.raises(ValueError, match="appears twice"):
        read_p3d(fork, twice)


def test_stale_binding_raises_on_write(fork):
    """Replacing lod.points after reading leaves lod.selected bound to the
    old list; writing it would silently serialise every weight as 0."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    _select(fork, lod, point_idx=(0,))
    lod.points = list(lod.points)
    with pytest.raises(RuntimeError, match="lod.selected: stale binding"):
        write_bytes(p3d)


def test_a_named_selection_called_selected_collides(fork):
    """The editor's selection is anonymous. Two tags with that name would be
    written and only the first read back."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    _select(fork, lod, point_idx=(0,))
    lod.selections["#Selected#"] = fork.Selection(lod.points, lod.faces)
    with pytest.raises(RuntimeError, match="anonymous"):
        write_bytes(p3d)


def test_validate_reports_a_stale_selected(fork):
    """validate() scans it with the named selections instead of ignoring it.

    The named selections are cleared first: with Component01 still in place,
    replacing lod.points makes IT stale too and the finding would come from
    there, so the test would pass without the tag being scanned at all.
    """
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.selections.clear()
    _select(fork, lod, point_idx=(0,))
    assert [f.code for f in p3d.validate()
            if f.code == "ERR_SELECTION_STALE"] == []
    lod.points = list(lod.points)
    stale = [f for f in p3d.validate() if f.code == "ERR_SELECTION_STALE"]
    assert len(stale) == 1
    assert "#Selected#" in stale[0].msg


def test_save_verify_catches_a_dropped_selected(fork, tmp_path, monkeypatch):
    """The gate that was blind in BUG-041: save(verify=True) now compares the
    tag, so a write that loses it raises instead of reporting success."""
    p3d = build_cube_p3d(fork)
    _select(fork, p3d.lods[0], point_idx=(0, 1))
    target = tmp_path / "cube.p3d"

    original = fork.LOD.write

    def drop_selected(self, f):
        # writes the file without the tag, leaving the in-memory model
        # intact - which is exactly what 1.6.0 did.
        keep, self.selected = self.selected, None
        try:
            return original(self, f)
        finally:
            self.selected = keep

    monkeypatch.setattr(fork.LOD, "write", drop_selected)
    with pytest.raises(ValueError, match="#Selected# presence differs"):
        p3d.save(str(target))
    assert not target.exists(), "a failed save must leave no file behind"


# ---- CLI --------------------------------------------------------------------

def test_cli_info_and_diff_report_selected(fork, tmp_path):
    """info prints lod.N.selected, and diff sees the tag disappear - the two
    instruments that reported `total: 0` while the UV sets were being lost."""
    import test_s2_cli as cli

    with_tag = build_cube_p3d(fork)
    _select(fork, with_tag.lods[0], point_idx=(0, 2), face_idx=(1,))
    a = cli.write(fork, with_tag, tmp_path / "a.p3d")
    b = cli.write(fork, build_cube_p3d(fork), tmp_path / "b.p3d")

    r = cli.run_cli("info", a)
    assert r.returncode == 0
    assert "lod.0.selected: 2p/1f" in r.stdout.splitlines()

    r = cli.run_cli("info", b)
    assert "lod.0.selected: -" in r.stdout.splitlines()

    r = cli.run_cli("diff", a, b)
    assert r.returncode == 1
    assert any("#Selected#" in line for line in r.stdout.splitlines()), \
        "diff must name the tag that vanished:\n%s" % r.stdout
