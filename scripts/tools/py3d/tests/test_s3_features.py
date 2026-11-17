"""#Mass# outside the Geometry LOD, determinant-aware transform, and
make_double_sided.

Local helper: the sign of cross(e1,e2)*declared per face must be
PRESERVED through transform() and make_double_sided(). Neither the
round-trip invariants nor save(verify=True) compare declared normals or
normal_index, so this is checked here.
"""

import os
import subprocess
import sys

import pytest

from builders import build_cube_lod, build_memory_lod, build_multilod_v2_p3d
from helpers import f32, read_p3d, write_bytes

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, "tools", "audit_p3d.py")

MIRROR_X = ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
SHEAR = ((1.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
SCALE_NONUNIFORM = ((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
ZERO_COL = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0))


def close3(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def mass_findings(findings):
    return [f for f in findings if f.code == "ERR_MASS_ONLY_GEOMETRY"]


def vertex_orders(lod):
    return [[v.point_index for v in fa.vertices] for fa in lod.faces]


def normal_indices(lod):
    return [[v.normal_index for v in fa.vertices] for fa in lod.faces]


def winding_signs(lod):
    """The sign of cross(e1,e2)*declared, per face."""
    out = []
    for fa in lod.faces:
        a = fa.vertices[0].point.coords
        b = fa.vertices[1].point.coords
        c = fa.vertices[2].point.coords
        e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cr = (e1[1] * e2[2] - e1[2] * e2[1],
              e1[2] * e2[0] - e1[0] * e2[2],
              e1[0] * e2[1] - e1[1] * e2[0])
        n = fa.vertices[0].normal
        d = cr[0] * n[0] + cr[1] * n[1] + cr[2] * n[2]
        out.append(1 if d > 0 else (-1 if d < 0 else 0))
    return out


def run_cli(*args):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "py3d"] + list(args),
                          capture_output=True, text=True, env=env, cwd=REPO)


def run_audit(path):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, AUDIT, str(path)],
                          capture_output=True, text=True, env=env, cwd=REPO)


def write_file(p3d, path):
    with open(str(path), "wb") as f:
        p3d.write(f)
    return str(path)


def sel_positions(lod, name):
    """Positional indices of a selection's faces, by identity."""
    pos = {id(fa): i for i, fa in enumerate(lod.faces)}
    return sorted(pos[id(fa)] for fa in lod.selections[name].faces)


# ---- ERR_MASS_ONLY_GEOMETRY ------------------------------------------

def test_mass_geo_pos(fork):
    """Mass only in the Geometry LOD produces no mass finding."""
    assert mass_findings(build_multilod_v2_p3d(fork).validate()) == []


def test_mass_geo_neg_full(fork):
    """A FireGeo LOD with point.mass=0.0 on every point - the case actually
    observed - produces exactly one ERROR, with the right LOD index and a
    remedy."""
    p3d = build_multilod_v2_p3d(fork)
    fg = p3d.get_lod("firegeo")
    idx = p3d.lods.index(fg)
    for p in fg.points:
        p.mass = 0.0
    found = mass_findings(p3d.validate())
    assert len(found) == 1
    f = found[0]
    assert f.severity == "ERROR"
    assert f.lod == idx
    assert "7e+15" in f.msg
    assert "%d point(s)" % len(fg.points) in f.msg
    assert "point.mass = None" in f.msg


def test_mass_geo_partial_no_exception(fork):
    """PARTIAL mass - one 0.0, the rest None - does NOT raise TypeError, which
    the LOD.mass property would have done inside sum(), and produces
    exactly one finding with a count of 1."""
    p3d = build_multilod_v2_p3d(fork)
    fg = p3d.get_lod("firegeo")
    fg.points[0].mass = 0.0
    found = mass_findings(p3d.validate())
    assert len(found) == 1
    assert "1 point(s)" in found[0].msg


def test_mass_geo_neg2_unknown_kind(fork):
    """A LOD of unknown resolution carrying mass produces
    ERR_MASS_ONLY_GEOMETRY AS WELL AS WARN_LOD_KIND_UNKNOWN."""
    p3d = build_multilod_v2_p3d(fork)
    weird = build_cube_lod(fork, resolution=5.5e14, selection_name=None,
                           mass_per_point=0.0, texture="", material="")
    p3d.lods.append(weird)
    idx = len(p3d.lods) - 1
    findings = p3d.validate()
    assert any(f.code == "ERR_MASS_ONLY_GEOMETRY" and f.lod == idx
               for f in findings)
    assert any(f.code == "WARN_LOD_KIND_UNKNOWN" and f.lod == idx
               for f in findings)


def test_mass_cli_exit1(fork, tmp_path):
    """python -m py3d validate on the negative fixture exits 1 and prints the
    finding."""
    p3d = build_multilod_v2_p3d(fork)
    for p in p3d.get_lod("firegeo").points:
        p.mass = 0.0
    fx = write_file(p3d, tmp_path / "mass_neg.p3d")
    r = run_cli("validate", fx)
    assert r.returncode == 1
    assert any("ERROR ERR_MASS_ONLY_GEOMETRY" in ln
               for ln in r.stdout.splitlines()), r.stdout


def test_val_audit_mass_neg(fork, tmp_path):
    """The audit, delegating to this library, reports
    CRITICAL [ERR_MASS_ONLY_GEOMETRY] and exits 1 on the negative
    fixture."""
    p3d = build_multilod_v2_p3d(fork)
    for p in p3d.get_lod("firegeo").points:
        p.mass = 0.0
    fx = write_file(p3d, tmp_path / "mass_audit.p3d")
    r = run_audit(fx)
    assert r.returncode == 1, r.stdout
    assert any("CRITICAL" in ln and "[ERR_MASS_ONLY_GEOMETRY]" in ln
               for ln in r.stdout.splitlines()), r.stdout


def test_val_audit_mass_pos(fork, tmp_path):
    """The clean fixture is still ALL PASSED with the new check active."""
    fx = write_file(build_multilod_v2_p3d(fork), tmp_path / "clean.p3d")
    r = run_audit(fx)
    assert r.returncode == 0, r.stdout
    assert "OVERALL: ALL PASSED" in r.stdout


# ---- P3D.transform ----------------------------------------------------

def test_trans_pos_rot_x_neg90(fork):
    """TRANS-POS: (x,y,z)->(x,z,-y) exacto; normales M*n; winding y
    normal_index INTACTOS (det=+1); signos preservados."""
    p3d = fork.P3D()
    vis = build_cube_lod(fork, resolution=1.0)
    p3d.lods.append(vis)
    pts_before = [p.coords for p in vis.points]
    normals_before = [tuple(n) for n in vis.facenormals]
    orders_before = vertex_orders(vis)
    nidx_before = normal_indices(vis)
    signs_before = winding_signs(vis)
    p3d.transform(fork.ROT_X_NEG90)
    for old, p in zip(pts_before, vis.points):
        assert close3(p.coords, (old[0], old[2], -old[1]))
    for old, n in zip(normals_before, vis.facenormals):
        assert close3(n, (old[0], old[2], -old[1]))
    assert vertex_orders(vis) == orders_before
    assert normal_indices(vis) == nidx_before
    assert winding_signs(vis) == signs_before


def test_trans_pos_multilod_validate_clean(fork):
    """A rotated multilod_v2 still gives validate() == [], with no new winding
    findings against the empty baseline."""
    p3d = build_multilod_v2_p3d(fork)
    assert p3d.validate() == []
    p3d.transform(fork.ROT_X_NEG90)
    assert p3d.validate() == []


def test_trans_neg_mirror(fork):
    """A det=-1 mirror reverses the vertex order on EVERY face of EVERY LOD,
    negates X, leaves winding-versus-visual clean, and preserves the
    cross*declared signs."""
    p3d = build_multilod_v2_p3d(fork)
    orders_before = {i: vertex_orders(lod) for i, lod in enumerate(p3d.lods)}
    pts_before = {i: [p.coords for p in lod.points]
                  for i, lod in enumerate(p3d.lods)}
    signs_before = {i: winding_signs(lod) for i, lod in enumerate(p3d.lods)
                    if lod.faces}
    p3d.transform(MIRROR_X)
    for i, lod in enumerate(p3d.lods):
        want = [list(reversed(o)) for o in orders_before[i]]
        assert vertex_orders(lod) == want, "LOD %d" % i
        for old, p in zip(pts_before[i], lod.points):
            assert close3(p.coords, (-old[0], old[1], old[2]))
        if lod.faces:
            assert winding_signs(lod) == signs_before[i], "LOD %d" % i
    findings = p3d.validate()
    assert not any("WINDING" in f.code for f in findings), findings


@pytest.mark.parametrize("matrix", [
    SHEAR,                                  # TRANS-NONORTHO
    SCALE_NONUNIFORM,                       # TRANS-NONUNIFORM
    ZERO_COL,                               # TRANS-DET0 (norma cero)
], ids=["nonortho", "nonuniform", "zerocol"])
def test_trans_rejects_contract(fork, matrix):
    """TRANS-NONORTHO/NONUNIFORM/DET0: ValueError de contrato y
    modelo BYTE-intacto."""
    p3d = build_multilod_v2_p3d(fork)
    before = write_bytes(p3d)
    with pytest.raises(ValueError) as e:
        p3d.transform(matrix)
    assert "orthogonal times uniform scale" in str(e.value)
    assert write_bytes(p3d) == before


@pytest.mark.parametrize("matrix", [
    ((1.0, 0.0), (0.0, 1.0), (0.0, 0.0)),   # filas de 2
    ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),     # 2 filas
    (("a", "b", "c"), (0, 1, 0), (0, 0, 1)),  # no numerica
    None,
], ids=["row2", "rows2", "nonnumeric", "none"])
def test_trans_rejects_shape(fork, matrix):
    """TRANS-SHAPE: forma/tipo invalidos -> ValueError; modelo intacto."""
    p3d = build_multilod_v2_p3d(fork)
    before = write_bytes(p3d)
    with pytest.raises(ValueError) as e:
        p3d.transform(matrix)
    assert "3x3 numeric" in str(e.value)
    assert write_bytes(p3d) == before


def test_trans_roundtrip_mirror_twice(fork):
    """The mirror applied twice is the identity: coordinates to within 1e-6,
    net winding unchanged, normal_index intact."""
    p3d = build_multilod_v2_p3d(fork)
    pts_before = {i: [p.coords for p in lod.points]
                  for i, lod in enumerate(p3d.lods)}
    orders_before = {i: vertex_orders(lod) for i, lod in enumerate(p3d.lods)}
    nidx_before = {i: normal_indices(lod) for i, lod in enumerate(p3d.lods)}
    p3d.transform(MIRROR_X)
    p3d.transform(MIRROR_X)
    for i, lod in enumerate(p3d.lods):
        for old, p in zip(pts_before[i], lod.points):
            assert close3(p.coords, old)
        assert vertex_orders(lod) == orders_before[i]
        assert normal_indices(lod) == nidx_before[i]


def test_trans_sem_save_reopen(fork, tmp_path):
    """transform, then save(verify=True), then reopen. The normal pool is
    compared BY VALUE (f32), normal_index per vertex, and memory points
    and proxies as M*p."""
    p3d = build_multilod_v2_p3d(fork)
    mem_before = None
    for lod in p3d.lods:
        if lod.kind() == "memory":
            mem_before = lod.get_memory_points()
    vis = p3d.get_lod("visual")
    proxies_before = vis.get_proxies()
    p3d.transform(fork.ROT_X_NEG90)
    expected_normals = {i: [tuple(n) for n in lod.facenormals]
                        for i, lod in enumerate(p3d.lods)}
    expected_nidx = {i: normal_indices(lod) for i, lod in enumerate(p3d.lods)}
    path = tmp_path / "trans_sem.p3d"
    p3d.save(str(path), verify=True)
    with open(str(path), "rb") as f:
        reread = fork.P3D(f)
    for i, lod in enumerate(reread.lods):
        assert len(lod.facenormals) == len(expected_normals[i])
        for got, want in zip(lod.facenormals, expected_normals[i]):
            assert close3(got, tuple(f32(c) for c in want)), \
                "LOD %d facenormals" % i
        assert normal_indices(lod) == expected_nidx[i], "LOD %d" % i
    mem_after = None
    for lod in reread.lods:
        if lod.kind() == "memory":
            mem_after = lod.get_memory_points()
    assert sorted(mem_after) == sorted(mem_before)
    for name, old in mem_before.items():
        want = (old[0], old[2], -old[1])
        assert close3(mem_after[name], want), name
    vis_after = reread.get_lod("visual")
    proxies_after = vis_after.get_proxies()
    assert len(proxies_after) == len(proxies_before) == 1
    pb, pa = proxies_before[0], proxies_after[0]
    assert pa["path"] == pb["path"] and pa["index"] == pb["index"]
    assert pa["ambiguous"] == pb["ambiguous"]
    old_a = pb["anchor"]
    assert close3(pa["anchor"], (old_a[0], old_a[2], -old_a[1]))


# ---- LOD.make_double_sided --------------------------------------------

def test_ds_pos(fork):
    """A triangulated visual cube (12 faces) with a 3-face selection becomes
    24 faces and a 6-face selection, with exact twins and no new points."""
    lod = build_cube_lod(fork, resolution=1.0, selection_name=None)
    lod.triangulate()
    assert len(lod.faces) == 12
    lod.set_selection("petals", face_idx=[0, 1, 2])
    pts_before = len(lod.points)
    originals = list(lod.faces)
    added = lod.make_double_sided()
    assert added == 12
    assert len(lod.faces) == 24
    assert len(lod.points) == pts_before
    assert sel_positions(lod, "petals") == [0, 1, 2, 12, 13, 14]
    for orig, twin in zip(originals, lod.faces[12:]):
        assert ([v.point_index for v in twin.vertices]
                == [v.point_index for v in reversed(orig.vertices)])
        assert ([v.uv for v in twin.vertices]
                == [v.uv for v in reversed(orig.vertices)])
        for ov, tv in zip(reversed(orig.vertices), twin.vertices):
            on = ov.normal
            assert close3(tv.normal, (-on[0], -on[1], -on[2]))
        assert twin.texture == orig.texture
        assert twin.material == orig.material
        assert twin.flags == orig.flags
    # the twin's cross*declared sign matches the original's
    signs = winding_signs(lod)
    assert signs[12:] == signs[:12]


def test_ds_dedup_pool(fork):
    """The cube's six normals come in +-n pairs, so the negated ones ALREADY
    exist in the pool and it grows by 0, deduplicated on exact value."""
    lod = build_cube_lod(fork, resolution=1.0, selection_name=None)
    lod.triangulate()
    pool_before = len(lod.facenormals)
    lod.make_double_sided()
    assert len(lod.facenormals) == pool_before


def test_ds_grows_pool_when_needed(fork):
    """A normal with no opposite in the pool: it grows by exactly the new
    unique negated entries."""
    m = fork
    lod = m.LOD()
    lod.resolution = 1.0
    coords = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    for c in coords:
        p = m.Point()
        p.coords = c
        lod.points.append(p)
    lod.facenormals.append((0.0, 0.0, 1.0))
    fa = m.Face(lod.points, lod.facenormals)
    for pi in (0, 1, 2):
        v = m.Vertex(lod.points, lod.facenormals)
        v.point_index = pi
        v.normal_index = 0
        v.uv = (0.0, 0.0)
        fa.vertices.append(v)
    lod.faces.append(fa)
    added = lod.make_double_sided()
    assert added == 1
    assert len(lod.facenormals) == 2
    assert close3(lod.facenormals[1], (0.0, 0.0, -1.0))


def test_ds_neg_kind(fork):
    """DS-NEG-KIND: Geometry y Memory -> ValueError, LOD intacto."""
    geo = build_cube_lod(fork, resolution=1.0e13, selection_name="Component01",
                         mass_per_point=25.0, texture="", material="")
    mem = build_memory_lod(fork, [("pos center", (0.0, 0.0, 0.0))])
    for lod in (geo, mem):
        faces_before = len(lod.faces)
        pool_before = len(lod.facenormals)
        with pytest.raises(ValueError) as e:
            lod.make_double_sided()
        assert "only visual LODs" in str(e.value)
        assert len(lod.faces) == faces_before
        assert len(lod.facenormals) == pool_before


def test_ds_roundtrip(fork):
    """save and reopen preserve the twins, the membership, and the NEGATED
    normal by value (f32) through normal_index."""
    m = fork
    lod = build_cube_lod(m, resolution=1.0, selection_name=None)
    lod.triangulate()
    lod.set_selection("petals", face_idx=[0, 1, 2])
    lod.make_double_sided()
    expected_normals = [tuple(n) for n in lod.facenormals]
    expected_nidx = normal_indices(lod)
    p3d = m.P3D()
    p3d.lods.append(lod)
    reread = read_p3d(m, write_bytes(p3d))
    rlod = reread.lods[0]
    assert len(rlod.faces) == 24
    assert sel_positions(rlod, "petals") == [0, 1, 2, 12, 13, 14]
    assert normal_indices(rlod) == expected_nidx
    for got, want in zip(rlod.facenormals, expected_normals):
        assert close3(got, tuple(f32(c) for c in want))
    for orig, twin in zip(rlod.faces[:12], rlod.faces[12:]):
        for ov, tv in zip(reversed(orig.vertices), twin.vertices):
            on = ov.normal
            assert close3(tv.normal, (-on[0], -on[1], -on[2]))


def test_ds_then_triangulate(fork):
    """make_double_sided() on quads and THEN triangulate(): 24 triangles, a
    12-face selection, no new points, coherent signs, and membership that
    persists after reopening."""
    m = fork
    lod = build_cube_lod(m, resolution=1.0, selection_name=None)
    assert len(lod.faces) == 6
    lod.set_selection("petals", face_idx=[0, 1, 2])
    pts_before = len(lod.points)
    added = lod.make_double_sided()
    assert added == 6
    assert len(lod.faces) == 12
    assert sel_positions(lod, "petals") == [0, 1, 2, 6, 7, 8]
    split = lod.triangulate()
    assert split == 12
    assert len(lod.faces) == 24
    assert len(lod.points) == pts_before
    assert len(lod.selections["petals"].faces) == 12
    signs = winding_signs(lod)
    assert signs[12:] == signs[:12]
    p3d = m.P3D()
    p3d.lods.append(lod)
    reread = read_p3d(m, write_bytes(p3d))
    assert len(reread.lods[0].selections["petals"].faces) == 12
