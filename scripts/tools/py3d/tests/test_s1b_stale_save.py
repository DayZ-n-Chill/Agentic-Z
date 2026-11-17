"""Stale and foreign selection bindings, and the verified atomic save."""

import glob
import os

import pytest

from builders import build_cube_p3d, build_multilod_p3d
from helpers import assert_sem_inv, sha256, write_bytes


# ---- stale and foreign bindings ----------------------------------------------------------

def test_stale_1_replaced_list_raises(fork):
    """Replacing lod.points after creating the selection raises."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.points = list(lod.points)  # a NEW list, same contents
    with pytest.raises(RuntimeError) as ei:
        write_bytes(p3d)
    assert "stale" in str(ei.value) and "new_selection" in str(ei.value)


def test_stale_2_foreign_key_raises(fork):
    """A Point key from ANOTHER LOD raises; it used to lose the weight in
    silence."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    other = build_cube_p3d(fork).lods[0]
    sel = lod.new_selection("lf_foreign")
    sel.points[other.points[0]] = 1  # punto ajeno
    with pytest.raises(RuntimeError) as ei:
        write_bytes(p3d)
    assert "foreign" in str(ei.value) and "lf_foreign" in str(ei.value)


def test_stale_3_append_after_create_is_defined(fork):
    """Appending to the SAME list after creating the selection is allowed:
    the new points serialise at weight 0, that is, absent. Pinned."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    n_before = len(lod.points)
    sel = lod.selections["Component01"]  # created before the append
    p = fork.Point(); p.coords = (2.0, 2.0, 2.0)
    lod.points.append(p)  # the SAME list grows

    data = write_bytes(p3d)  # no raise
    import io
    reread = fork.P3D(io.BytesIO(data))
    rl = reread.lods[0]
    assert len(rl.points) == n_before + 1
    rsel = rl.selections["Component01"]
    # membership is the original members; the new point is NOT in it
    assert len(rsel.points) == len(sel.points) == n_before
    assert rl.points[-1] not in rsel.points


# ---- atomic save -----------------------------------------------------------

def _no_tmp_leftovers(dirpath):
    return glob.glob(os.path.join(str(dirpath), "*.tmp.*")) == []


def test_save_pos_atomic_verified(fork, tmp_path):
    """save(verify=True) leaves a valid file that reads back and holds the
    invariants."""
    p3d = build_multilod_p3d(fork)
    target = tmp_path / "stone.p3d"
    p3d.save(str(target), verify=True)
    assert target.exists() and _no_tmp_leftovers(tmp_path)
    data = target.read_bytes()
    assert data[:4] == b"MLOD"
    assert_sem_inv(fork, p3d, data=data)


def test_save_pos_backup_dir(fork, tmp_path):
    """The previous file is backed up before being overwritten."""
    p3d = build_cube_p3d(fork)
    target = tmp_path / "stone.p3d"
    backups = tmp_path / "_backups"
    p3d.save(str(target), verify=True, backup_dir=str(backups))
    first = target.read_bytes()
    assert not backups.exists() or list(backups.iterdir()) == []  # no habia previo

    p3d.lods[0].properties["lodnoshadow"] = "1"
    p3d.save(str(target), verify=True, backup_dir=str(backups))
    baks = list(backups.glob("stone.p3d.bak_*"))
    assert len(baks) == 1
    assert baks[0].read_bytes() == first  # the backup IS the previous content
    assert target.read_bytes() != first


def test_save_fail_original_intact(fork, tmp_path, monkeypatch):
    """An injected failure raises, leaves the original byte-intact, and
    removes the temporary file."""
    p3d = build_cube_p3d(fork)
    target = tmp_path / "stone.p3d"
    p3d.save(str(target), verify=True)
    sha_before = sha256(target.read_bytes())

    def broken_write(self, f):  # corrupts the LOD's stream
        f.write(b"GARBAGE")

    monkeypatch.setattr(fork.LOD, "write", broken_write)
    with pytest.raises(Exception):
        p3d.save(str(target), verify=True)

    assert sha256(target.read_bytes()) == sha_before  # not a byte touched
    assert _no_tmp_leftovers(tmp_path)


def test_save_fail_verify_catches_semantic_loss(fork, tmp_path, monkeypatch):
    """The verify step catches SEMANTIC loss even when the write does not
    fail: selections emptied in the stream."""
    p3d = build_cube_p3d(fork)
    target = tmp_path / "stone.p3d"
    p3d.save(str(target), verify=True)
    sha_before = sha256(target.read_bytes())

    orig = fork.Selection.write

    def lossy_write(self, f, name=None):
        emptied = fork.Selection(self.all_points, self.all_faces)
        return orig(emptied, f, name=name)  # names survive, membership is 0

    monkeypatch.setattr(fork.Selection, "write", lossy_write)
    with pytest.raises(ValueError) as ei:
        p3d.save(str(target), verify=True)
    assert "membership" in str(ei.value)
    assert sha256(target.read_bytes()) == sha_before
    assert _no_tmp_leftovers(tmp_path)
