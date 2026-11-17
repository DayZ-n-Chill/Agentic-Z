"""Module-agnostic synthetic model builders. No Bohemia Interactive
assets are used or required.

Every builder takes the py3d module `m` - this fork, or upstream loaded
through PY3D_UPSTREAM_PATH - so the SAME in-memory model can be serialised
by both for the byte-identity contract. It only uses API surface that
exists in upstream master 7acd58b.
"""

import math

TEXTURE = "lf\\data\\stone_co.paa"
MATERIAL = "lf\\data\\stone.rvmat"

CUBE_POINTS = [
    (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
    (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
]
CUBE_QUADS = [
    ((0, 3, 2, 1), (0.0, 0.0, -1.0)),
    ((4, 5, 6, 7), (0.0, 0.0, 1.0)),
    ((0, 1, 5, 4), (0.0, -1.0, 0.0)),
    ((2, 3, 7, 6), (0.0, 1.0, 0.0)),
    ((0, 4, 7, 3), (-1.0, 0.0, 0.0)),
    ((1, 2, 6, 5), (1.0, 0.0, 0.0)),
]
QUAD_UV = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))


def _add_face(m, lod, point_idx, normal_idx, uvs, texture, material):
    fa = m.Face(lod.points, lod.facenormals)
    for pi, uv in zip(point_idx, uvs):
        v = m.Vertex(lod.points, lod.facenormals)
        v.point_index = pi
        v.normal_index = normal_idx
        v.uv = uv
        fa.vertices.append(v)
    fa.texture = texture
    fa.material = material
    lod.faces.append(fa)
    return fa


def _select_all(m, lod, name):
    sel = m.Selection(lod.points, lod.faces)
    for p in lod.points:
        sel.points[p] = 1
    for fa in lod.faces:
        sel.faces[fa] = 1
    lod.selections[name] = sel
    return sel


def build_cube_lod(m, resolution=1.0, selection_name="Component01",
                   mass_per_point=None, properties=(),
                   texture=TEXTURE, material=MATERIAL):
    lod = m.LOD()
    lod.resolution = resolution
    for c in CUBE_POINTS:
        p = m.Point()
        p.coords = c
        if mass_per_point is not None:
            p.mass = mass_per_point
        lod.points.append(p)
    for _, n in CUBE_QUADS:
        lod.facenormals.append(n)
    for i, (quad, _) in enumerate(CUBE_QUADS):
        _add_face(m, lod, quad, i, QUAD_UV, texture, material)
    if selection_name:
        _select_all(m, lod, selection_name)
    for k, v in properties:
        lod.properties[k] = v
    return lod


def icosphere(subdiv=2):
    """Subdivided icosahedron: subdiv=2 gives 162 vertices and 320 faces."""
    t = (1.0 + 5 ** 0.5) / 2.0
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
             (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
             (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
             (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]

    def norm(v):
        l = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5
        return (v[0] / l, v[1] / l, v[2] / l)

    verts = [norm(v) for v in verts]
    for _ in range(subdiv):
        cache = {}

        def midpoint(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                va, vb = verts[a], verts[b]
                verts.append(norm(((va[0] + vb[0]) / 2,
                                   (va[1] + vb[1]) / 2,
                                   (va[2] + vb[2]) / 2)))
                cache[key] = len(verts) - 1
            return cache[key]

        new_faces = []
        for (a, b, c) in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new_faces += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
        faces = new_faces
    return verts, faces


def _sphere_uv(v):
    u = 0.5 + math.atan2(v[2], v[0]) / (2 * math.pi)
    w = 0.5 - math.asin(max(-1.0, min(1.0, v[1]))) / math.pi
    return (u, w)


def build_icosphere_lod(m, resolution=1.0, selection_name="body"):
    verts, tris = icosphere(2)
    assert len(verts) == 162 and len(tris) == 320
    lod = m.LOD()
    lod.resolution = resolution
    for c in verts:
        p = m.Point()
        p.coords = c
        lod.points.append(p)
    for (a, b, c) in tris:
        va, vb, vc = verts[a], verts[b], verts[c]
        n = ((va[0] + vb[0] + vc[0]) / 3,
             (va[1] + vb[1] + vc[1]) / 3,
             (va[2] + vb[2] + vc[2]) / 3)
        l = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
        lod.facenormals.append((n[0] / l, n[1] / l, n[2] / l))
    for i, (a, b, c) in enumerate(tris):
        uvs = (_sphere_uv(verts[a]), _sphere_uv(verts[b]), _sphere_uv(verts[c]))
        _add_face(m, lod, (a, b, c), i, uvs, TEXTURE, MATERIAL)
    if selection_name:
        _select_all(m, lod, selection_name)
    return lod


def add_proxy_triangle(m, lod, proxy_name, origin=(0.0, 0.0, 0.0)):
    """A proxy is a 3-point triangle plus a 'proxy:...' selection (MLOD
    convention)."""
    base = len(lod.points)
    coords = [origin,
              (origin[0] + 0.1, origin[1], origin[2]),
              (origin[0], origin[1] + 0.1, origin[2])]
    for c in coords:
        p = m.Point()
        p.coords = c
        lod.points.append(p)
    lod.facenormals.append((0.0, 0.0, 1.0))
    ni = len(lod.facenormals) - 1
    fa = m.Face(lod.points, lod.facenormals)
    for i in range(3):
        v = m.Vertex(lod.points, lod.facenormals)
        v.point_index = base + i
        v.normal_index = ni
        v.uv = (0.0, 0.0)
        fa.vertices.append(v)
    fa.texture = ""
    fa.material = ""
    lod.faces.append(fa)
    sel = m.Selection(lod.points, lod.faces)
    for i in range(3):
        sel.points[lod.points[base + i]] = 1
    sel.faces[fa] = 1
    lod.selections[proxy_name] = sel
    return sel


def build_memory_lod(m, named_points, resolution=1.0e15):
    """Memory LOD: named points as single-point selections, no faces."""
    lod = m.LOD()
    lod.resolution = resolution
    for name, xyz in named_points:
        p = m.Point()
        p.coords = xyz
        lod.points.append(p)
        sel = m.Selection(lod.points, lod.faces)
        sel.points[p] = 1
        lod.selections[name] = sel
    return lod


def set_uv_set(m, lod, uv_id, fn=None):
    """Attach UV set *uv_id* to every face vertex of *lod* (fork API 1.6.0:
    `Vertex.uv_sets`). *fn*(face index, vertex index, uv0) -> (u, v); the
    default derives a value that differs from set 0 per face and vertex, so
    a dropped, duplicated or shuffled set is detectable."""
    for fi, fa in enumerate(lod.faces):
        for vi, v in enumerate(fa.vertices):
            if fn is None:
                uv = (0.5 * v.uv[0] + 0.25 + 0.001 * fi,
                      0.5 * v.uv[1] + 0.125 + 0.001 * vi)
            else:
                uv = fn(fi, vi, v.uv)
            v.uv_sets[uv_id] = uv
    return lod


def build_two_uvsets_p3d(m):
    """1.6.0 fixture: Visual cube with UV sets 0 and 1, Geometry cube
    (Component01, mass 200) and a Memory LOD without faces - the three shapes
    whose #UVSet# tags 1.5.0 dropped or omitted."""
    p3d = m.P3D()
    vis = build_cube_lod(m, resolution=1.0)
    set_uv_set(m, vis, 1)
    geo = build_cube_lod(m, resolution=1.0e13, selection_name="Component01",
                         mass_per_point=25.0,
                         properties=(("autocenter", "0"), ("class", "house")),
                         texture="", material="")
    mem = build_memory_lod(m, [
        ("pos center", (0.0, 0.0, 0.0)),
        ("dolly_axis_start", (0.0, -1.0, 0.0)),
        ("dolly_axis_end", (0.0, 1.0, 0.0)),
    ])
    p3d.lods += [vis, geo, mem]
    return p3d


def build_cube_p3d(m):
    p3d = m.P3D()
    p3d.lods.append(build_cube_lod(m))
    return p3d


def build_icosphere_p3d(m):
    p3d = m.P3D()
    p3d.lods.append(build_icosphere_lod(m))
    return p3d


def build_multilod_p3d(m):
    """Visual (icosphere plus a proxy), Geometry (cube, mass 200,
    autocenter=0) and Memory (3 named points)."""
    p3d = m.P3D()
    vis = build_icosphere_lod(m, resolution=1.0)
    add_proxy_triangle(m, vis, "proxy:\\dz\\data\\proxies\\flag.001")
    geo = build_cube_lod(m, resolution=1.0e13, selection_name="Component01",
                         mass_per_point=25.0,
                         properties=(("autocenter", "0"),),
                         texture="", material="")
    mem = build_memory_lod(m, [
        ("pos center", (0.0, 0.0, 0.0)),
        ("dolly_axis_start", (0.0, -1.0, 0.0)),
        ("dolly_axis_end", (0.0, 1.0, 0.0)),
    ])
    p3d.lods += [vis, geo, mem]
    return p3d


def build_multilod_v2_p3d(m):
    """A complete, CLEAN model for validate() and the integration tests:
    Visual (icosphere plus a proxy), Geometry (Component01, autocenter,
    class, mass 200), ViewGeo and FireGeo (Component01 each: validate()
    asks every collision LOD with faces for a component) and Memory (pos
    center, box_placing_min/max, and a two-point dolly axis)."""
    p3d = m.P3D()
    vis = build_icosphere_lod(m, resolution=1.0)
    add_proxy_triangle(m, vis, "proxy:\\dz\\data\\proxies\\flag.001")
    geo = build_cube_lod(m, resolution=1.0e13, selection_name="Component01",
                         mass_per_point=25.0,
                         properties=(("autocenter", "0"),
                                     ("class", "house")),
                         texture="", material="")
    viewgeo = build_cube_lod(m, resolution=6.0e15,
                             selection_name="Component01",
                             texture="", material="")
    firegeo = build_cube_lod(m, resolution=7.0e15,
                             selection_name="Component01",
                             texture="", material="")
    mem = build_memory_lod(m, [
        ("pos center", (0.0, 0.0, 0.0)),
        ("box_placing_min", (-0.5, -0.5, -0.5)),
        ("box_placing_max", (0.5, 0.5, 0.5)),
        ("dolly_axis_start", (0.0, -1.0, 0.0)),
        ("dolly_axis_end", (0.0, 1.0, 0.0)),
    ])
    p3d.lods += [vis, geo, viewgeo, firegeo, mem]
    return p3d


# The model of the in-game Blender -> DayZ test of 2026-10-01: an "F" in
# relief on a plate, in Blender space (x right, y depth with the front at
# -y, z up), every quad counter-clockwise seen from outside with an outward
# normal. The texture strings are the ones that test wrote, so the bytes
# match; no texture is read.
CHIRAL_F_PLATE_TEXTURE = "dz\\data\\data\\beton1_co.paa"
CHIRAL_F_GLYPH_TEXTURE = "dz\\data\\data\\black_co.paa"
CHIRAL_F_BOXES = [
    ((-0.60, 0.00, 0.00), (0.60, 0.05, 1.40), CHIRAL_F_PLATE_TEXTURE),
    ((-0.35, -0.08, 0.15), (-0.20, 0.00, 1.25), CHIRAL_F_GLYPH_TEXTURE),
    ((-0.20, -0.08, 1.10), (0.35, 0.00, 1.25), CHIRAL_F_GLYPH_TEXTURE),
    ((-0.20, -0.08, 0.60), (0.20, 0.00, 0.75), CHIRAL_F_GLYPH_TEXTURE),
]  # plate; then the F: stem on the left, top and middle arms reaching +x
BOX_QUADS = [
    ((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)),
    ((0, 1, 5, 4), (0, -1, 0)), ((2, 3, 7, 6), (0, 1, 0)),
    ((3, 0, 4, 7), (-1, 0, 0)), ((1, 2, 6, 5), (1, 0, 0)),
]
QUAD_AS_TRIANGLES = (((0, 1, 2), ((0, 1), (1, 1), (1, 0))),
                     ((0, 2, 3), ((0, 1), (1, 0), (0, 0))))


def build_chiral_f_p3d(m):
    """One visual LOD at resolution 0.0: 4 boxes of 8 points, 48 triangles."""
    p3d = m.P3D()
    lod = m.LOD()
    lod.resolution = 0.0
    for (x0, y0, z0), (x1, y1, z1), texture in CHIRAL_F_BOXES:
        base = len(lod.points)
        for c in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]:
            p = m.Point()
            p.coords = c
            p.flags = 0
            lod.points.append(p)
        for quad, n in BOX_QUADS:
            ni = len(lod.facenormals)
            lod.facenormals.append(tuple(float(v) for v in n))
            for tri, uvs in QUAD_AS_TRIANGLES:
                fa = m.Face(lod.points, lod.facenormals)
                fa.flags = 0
                fa.texture = texture
                fa.material = ""
                for k, uv in zip(tri, uvs):
                    v = m.Vertex(lod.points, lod.facenormals)
                    v.point_index = base + quad[k]
                    v.normal_index = ni
                    v.uv = uv
                    fa.vertices.append(v)
                lod.faces.append(fa)
    p3d.lods.append(lod)
    return p3d
