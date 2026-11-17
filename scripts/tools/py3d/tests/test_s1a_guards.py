"""Anti-corruption guards: the Selection constructor, weight validation
on write, and the property length limit."""

import io

import pytest

from builders import build_cube_p3d
from helpers import read_p3d, write_bytes


# ---- Selection constructor -------------------------------------------------------------

def test_q1_neg_selection_noargs_raises_actionable(fork):
    """Selection() with no arguments raises TypeError with a guiding message."""
    with pytest.raises(TypeError) as ei:
        fork.Selection()
    msg = str(ei.value)
    assert "lod.points" in msg and "new_selection" in msg


def test_q1_neg_upstream_parity(upstream):
    """For the record: upstream rejects the no-arg form too, through its
    positional signature."""
    with pytest.raises(TypeError):
        upstream.Selection()


def test_q1_pos_factory_registers_and_roundtrips(fork):
    """Q1-POS: new_selection bindea, registra y sobrevive write->read."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    sel = lod.new_selection("lf_extra")
    assert lod.selections["lf_extra"] is sel
    assert sel.all_points is lod.points and sel.all_faces is lod.faces
    sel.faces[lod.faces[0]] = 1
    sel.faces[lod.faces[2]] = 1
    # get-or-create: a second call returns the SAME selection
    assert lod.new_selection("lf_extra") is sel

    reread = read_p3d(fork, write_bytes(p3d))
    rl = reread.lods[0]
    assert "lf_extra" in rl.selections
    got = sorted(rl.faces.index(fa) for fa in rl.selections["lf_extra"].faces)
    assert got == [0, 2]
    assert len(rl.selections["lf_extra"].points) == 0


# ---- selection weights --------------------------------------------------------------

def test_w_pos_weights_normalized(fork):
    """{1, 1.0, 0.5} round-trips with 1.0 coerced to int and 0.5 kept
    fractional."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    sel = lod.new_selection("lf_weights")
    sel.faces[lod.faces[0]] = 1
    sel.faces[lod.faces[1]] = 1.0
    sel.faces[lod.faces[2]] = 0.5

    reread = read_p3d(fork, write_bytes(p3d))
    rl = reread.lods[0]
    rsel = rl.selections["lf_weights"]
    by_idx = {rl.faces.index(fa): w for fa, w in rsel.faces.items()}
    assert by_idx[0] == 1 and by_idx[1] == 1
    assert abs(by_idx[2] - 0.5) <= 1.0 / 255 + 1e-9
    # the caller's dict is NOT mutated
    assert sel.faces[lod.faces[1]] == 1.0


@pytest.mark.parametrize("bad", [1.5, -0.25, 2, "x", None])
def test_w_neg_invalid_weight_early_valueerror(fork, bad):
    """An invalid weight raises ValueError early, naming the selection."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    sel = lod.new_selection("lf_bad")
    sel.faces[lod.faces[0]] = bad
    with pytest.raises(ValueError) as ei:
        write_bytes(p3d)
    msg = str(ei.value)
    assert "lf_bad" in msg and repr(bad) in msg


def test_w_upstream_crashes_late_and_cryptic(upstream):
    """Upstream blows up LATE, with a cryptic TypeError from bytes() over a
    float, for the weight 1.0. This fork turns that into success by
    coercing it, and turns invalid weights into an early ValueError."""
    p3d = build_cube_p3d(upstream)
    lod = p3d.lods[0]
    sel = upstream.Selection(lod.points, lod.faces)
    sel.faces[lod.faces[0]] = 1.0
    lod.selections["lf_up"] = sel
    with pytest.raises(TypeError):
        write_bytes(p3d)


# ---- #Property# length -----------------------------------------------------------

def test_prop_pos_63_bytes_roundtrip_exact(fork):
    """PROP-POS: valor de 63 bytes -> round-trip exacto."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    v63 = "v" * 63
    lod.properties["lodnoshadow"] = v63
    reread = read_p3d(fork, write_bytes(p3d))
    assert reread.lods[0].properties["lodnoshadow"] == v63


@pytest.mark.parametrize("key,value", [
    ("class", "x" * 70),     # valor largo
    ("k" * 64, "house"),     # clave larga
    ("class", "y" * 64),     # exactly 64: it would lose the NUL terminator
])
def test_prop_neg_over_63_bytes_raises(fork, key, value):
    """A key or value of 64 or more UTF-8 bytes raises ValueError; it used to
    truncate."""
    p3d = build_cube_p3d(fork)
    p3d.lods[0].properties[key] = value
    with pytest.raises(ValueError) as ei:
        write_bytes(p3d)
    assert "63" in str(ei.value)


def test_prop_upstream_corrupts_silently_on_write(upstream):
    """Verified upstream behaviour: it WRITES a property longer than 63
    bytes without complaining - struct '64s' truncates it and loses the NUL
    terminator - and the resulting .p3d is NOT EVEN readable again: the read
    fails on the NUL assert. Silent corruption on write, deferred failure on
    read: exactly what this fork's guard prevents."""
    p3d = build_cube_p3d(upstream)
    p3d.lods[0].properties["class"] = "x" * 70
    data = write_bytes(p3d)  # upstream does not complain
    with pytest.raises(AssertionError):
        read_p3d(upstream, data)  # the output is corrupt
