"""The write contract: byte-identical output against upstream, and the
semantic invariants that must survive a round trip."""

import io

import pytest

from builders import build_cube_p3d, build_icosphere_p3d, build_multilod_p3d
from helpers import (EMPTY_UVSET_TAG, EOF_TAG, assert_sem_inv, read_p3d,
                     sha256, write_bytes)

CANONICAL = [
    ("cube", build_cube_p3d),
    ("icosphere", build_icosphere_p3d),
    ("multilod", build_multilod_p3d),
]
IDS = [c[0] for c in CANONICAL]


@pytest.mark.parametrize("name,builder", CANONICAL, ids=IDS)
def test_canon_ident(fork, upstream, name, builder):
    """Same model, identical bytes from this fork and upstream, with the one
    deliberate exception introduced in 1.6.0: in a LOD without faces this
    fork emits the empty #UVSet# (a 4-byte id) that Object Builder writes
    and upstream omits. The tag is counted - one per faceless LOD - and
    the rest is compared byte for byte.
    """
    model = builder(fork)
    faceless = sum(1 for lod in model.lods if not lod.faces)
    fork_bytes = write_bytes(model)
    up_bytes = write_bytes(builder(upstream))
    marker = EMPTY_UVSET_TAG + EOF_TAG
    assert fork_bytes.count(marker) == faceless
    stripped = fork_bytes.replace(marker, EOF_TAG)
    assert len(stripped) == len(up_bytes)
    assert sha256(stripped) == sha256(up_bytes)


@pytest.mark.parametrize("name,builder", CANONICAL, ids=IDS)
def test_sem_inv(fork, name, builder):
    """SEM-INV: write -> reopen -> invariantes semanticos completos."""
    assert_sem_inv(fork, builder(fork))


@pytest.mark.parametrize("name,builder", CANONICAL, ids=IDS)
def test_sem_inv_second_roundtrip_stable(fork, name, builder):
    """After the first round trip, write(read(x)) == x: the output is stable."""
    d1 = write_bytes(builder(fork))
    d2 = write_bytes(read_p3d(fork, d1))
    assert d1 == d2


def test_fixture_files_roundtrip(fork, tmp_path):
    """make_fixtures writes readable .p3d files that hold the invariants when
    read back from disk."""
    import make_fixtures
    out = make_fixtures.main(str(tmp_path))
    import os
    for name, builder in CANONICAL:
        path = os.path.join(out, name + ".p3d")
        with open(path, "rb") as f:
            data = f.read()
        assert data[:4] == b"MLOD"
        assert_sem_inv(fork, builder(fork), data=data)
