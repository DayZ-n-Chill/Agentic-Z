"""The three critical defects the August 2026 adversarial audit found.

Each test was written to fail BEFORE its fix:

  1. _read_asciiz hung the process at EOF with no NUL, inherited from
     upstream 7acd58b. This test carries its own timeout, so a missing fix
     fails the test instead of hanging the whole suite.
  2. ERR_WINDING_INVERTED's message advised swapping vertices[1] and
     vertices[2], which inverts a triangle but CROSSES a quad.
  3. The winding check was relative to the Visual LOD and based on the
     centroid, which assumes convexity: with EVERY LOD inverted the model
     was consistent with itself and validate() returned [].
"""

import io
import threading

import pytest

import py3d

from builders import build_cube_lod


# --------------------------------------------------------------- helpers

def _invert_winding(lod):
    """Reverse the vertex order WITHOUT touching the declared normals.

    This is exactly what a Blender Z-up to DayZ Y-up export produces: the
    handedness changes, the winding ends up inverted, and the facenormals
    still point outwards.
    """
    for fa in lod.faces:
        fa.vertices.reverse()


def _model_visual_plus_geometry(invert_all=False):
    model = py3d.P3D()
    vis = build_cube_lod(py3d, resolution=1.0)
    geo = build_cube_lod(py3d, resolution=1.0e13,
                         selection_name="Component01",
                         mass_per_point=25.0,
                         properties=(("autocenter", "0"), ("class", "house")),
                         texture="", material="")
    if invert_all:
        _invert_winding(vis)
        _invert_winding(geo)
    model.lods += [vis, geo]
    return model


def _codes(model):
    return [f.code for f in model.validate()]


# ------------------------------------------------------------- FIX-1

def test_asciiz_sin_nul_lanza_en_vez_de_colgar():
    """EOF with no NUL must raise. Under a timeout, so a hang fails the test."""
    box = {}

    def target():
        try:
            py3d._read_asciiz(io.BytesIO(b"NO_NUL_HASTA_EOF"))
            box["res"] = "returned"
        except Exception as exc:
            box["res"] = type(exc).__name__

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(5.0)

    assert not t.is_alive(), (
        "_read_asciiz is still hung after 5s on an asciiz with no NUL: the "
        "loop 'while b\"\\0\" not in bts' never ends, because read() keeps "
        "returning b'' at EOF")
    assert box.get("res") not in (None, "returned"), (
        "_read_asciiz returned instead of raising on an asciiz with no NUL")


def test_asciiz_valido_sigue_funcionando():
    """The fix must not change the happy path: that is upstream's contract."""
    assert py3d._read_asciiz(io.BytesIO(b"hola\0resto")) == "hola"
    assert py3d._read_asciiz(io.BytesIO(b"\0")) == ""
    # a string longer than the 1024-byte read block
    largo = b"x" * 3000 + b"\0"
    assert py3d._read_asciiz(io.BytesIO(largo)) == "x" * 3000


# ------------------------------------------------------------- FIX-2

def test_mensaje_de_winding_no_recomienda_el_swap_que_cruza_quads():
    """reverse() is the correct remedy; the swap crosses quads."""
    model = py3d.P3D()
    vis = build_cube_lod(py3d, resolution=1.0)
    geo = build_cube_lod(py3d, resolution=1.0e13,
                         selection_name="Component01",
                         properties=(("autocenter", "0"), ("class", "house")),
                         texture="", material="")
    _invert_winding(geo)          # collision LOD only -> a real inconsistency
    model.lods += [vis, geo]

    msgs = [f.msg for f in model.validate() if "WINDING" in f.code]
    assert msgs, "no winding finding was emitted for the inverted case"
    for msg in msgs:
        # The predicate looks for the imperative RECOMMENDATION
        # ("Fix: swap ..."), not any mention: the corrected message names
        # the swap precisely to warn against it, which is what we want.
        assert "Fix: swap vertices" not in msg, (
            "the message still recommends swapping vertices[1] and [2], "
            "which on a quad [0,1,2,3] gives [0,2,1,3] - a CROSSED face, "
            "not an inverted one: %r" % msg)
    assert any("reverse()" in m for m in msgs), (
        "no winding message recommends face.vertices.reverse(), which is "
        "the remedy that works for any number of vertices")


# ------------------------------------------------------------- FIX-3

def test_inversion_global_de_todos_los_lods_se_detecta():
    """The false negative that motivated the fork: everything inverted meant
    silence.

    With the check relative to the Visual LOD, inverting EVERY LOD leaves
    the model consistent with itself and validate() returned [].
    """
    codes = _codes(_model_visual_plus_geometry(invert_all=True))
    winding = [c for c in codes if "WINDING" in c]
    assert winding, (
        "a model with EVERY LOD inverted - the Blender Z-up to Y-up bug - "
        "produced no winding finding at all; codes=%r" % codes)


def test_modelo_sano_no_produce_falso_positivo_de_winding():
    """The counter-test: the instrument has to be able to say yes."""
    codes = _codes(_model_visual_plus_geometry(invert_all=False))
    errores = [c for c in codes if "WINDING" in c and c.startswith("ERR")]
    assert not errores, (
        "a healthy model was flagged with a winding ERROR: %r (codes=%r)"
        % (errores, codes))


def test_la_senal_de_normal_declarada_distingue_ambos_sentidos():
    """Signal B on its own: 100% on the healthy model, 0% on the inverted one.

    This is the test that tells one direction from the other. With the old
    centroid predicate both cases give the same answer, because a wholly
    inverted model is internally consistent.
    """
    sano = build_cube_lod(py3d, resolution=1.0)
    invertido = build_cube_lod(py3d, resolution=1.0)
    _invert_winding(invertido)

    pct_sano = py3d._pct_normal_agreement(sano)
    pct_inv = py3d._pct_normal_agreement(invertido)

    assert pct_sano == pytest.approx(100.0), (
        "a healthy cube should agree 100%% between winding and declared "
        "normal, got %r" % pct_sano)
    assert pct_inv == pytest.approx(0.0), (
        "a cube with inverted winding should give 0%%, got %r" % pct_inv)


def test_coherencia_de_aristas_en_malla_cerrada():
    """Signal A: in a well-built closed mesh, every shared edge is traversed
    in opposite directions by its two faces."""
    cubo = build_cube_lod(py3d, resolution=1.0)
    assert py3d._pct_edge_coherence(cubo) == pytest.approx(100.0)
