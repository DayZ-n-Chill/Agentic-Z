"""Blender -> DayZ: blender_to_dayz(), ROT_X_NEG90 and the deprecated
BLENDER_TO_DAYZ.

The fixture is the model of the in-game test of 2026-10-01 (DayZDiag
1.29.163709): an "F" in relief on a plate, authored in Blender space -
right-handed, Z up, front at -Y, faces counter-clockwise seen from outside
and outward normals - written three ways and binarized with AddonBuilder:

  B  blender_to_dayz()                                  solid, the F reads
  A  ROT_X_NEG90, then faces reversed, normals negated  solid but MIRRORED
  C  transform(ROT_X_NEG90) alone                       inside-out AND mirrored

MEASURED holds the SHA-256 of the three MLODs that were binarized and looked
at in game, and the fixture below rebuilds them byte for byte, so these
tests are about the geometry the game showed, not about a lookalike. A and C
are the negative controls: each property check has to fail on at least one
of them, or it is not checking anything.
"""

import hashlib
import math
import os
import re
import warnings

import pytest

from builders import build_chiral_f_p3d, build_multilod_v2_p3d
from helpers import f32, read_p3d, write_bytes

MEASURED = {
    "A": "b08372a6248d826aad7557827346af030b1d448e4e0d75da3afd0a67a0c16d27",
    "B": "f1be491df6304534f2100d053e972a9792b1780e026223408f5c200b465201d7",
    "C": "ac5f0f77f6d93db93226e631ed0b02c3492c6e13d815a621bd9ed82e2b4e1da8",
}
PLATE, STEM, TOP_ARM, MID_ARM = range(4)
BLENDER_UP = (0.0, 0.0, 1.0)
DAYZ_UP = (0.0, 1.0, 0.0)
PROXY = "proxy:\\dz\\data\\proxies\\flag.001"


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def centroid(pts):
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


def close3(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def variant(m, tag):
    """The fixture, written the way the in-game test wrote variant *tag*."""
    p3d = build_chiral_f_p3d(m)
    if tag == "B":
        m.blender_to_dayz(p3d)
    elif tag == "A":
        p3d.transform(m.ROT_X_NEG90)
        for lod in p3d.lods:
            for fa in lod.faces:
                fa.vertices.reverse()
            for i, n in enumerate(lod.facenormals):
                lod.facenormals[i] = (-n[0], -n[1], -n[2])
    elif tag == "C":
        p3d.transform(m.ROT_X_NEG90)
    return p3d


def box_points(lod, box):
    return [p.coords for p in lod.points[8 * box:8 * box + 8]]


def inward_counts(p3d):
    """(faces, cross product inward, normal inward). Inward is measured
    against the centroid of the face's own box, and every box is convex."""
    lod = p3d.lods[0]
    faces = cross_in = normal_in = 0
    for fa in lod.faces:
        vs = [v.point.coords for v in fa.vertices]
        out = sub(centroid(vs),
                  centroid(box_points(lod, fa.vertices[0].point_index // 8)))
        cr = cross(sub(vs[1], vs[0]), sub(vs[2], vs[0]))
        faces += 1
        cross_in += dot(cr, out) < 0
        normal_in += dot(fa.vertices[0].normal, out) < 0
    return faces, cross_in, normal_in


def screen_right(toward_viewer, up, left_handed):
    """Screen-right for a viewer facing -toward_viewer with *up* up.

    Right-handed coordinates: up x toward_viewer - Blender's front view,
    looking along +Y, has +X on the right. Left-handed coordinates (DayZ:
    X east, Y up, Z north) give the same direction as toward_viewer x up,
    because there the arithmetic cross product follows the left hand:
    looking north from the south, +X - east - is on the right, as on a map.
    """
    if left_handed:
        return cross(toward_viewer, up)
    return cross(up, toward_viewer)


def reading(p3d, up, left_handed):
    """'F' or 'mirrored F', seen face-on from the side carrying the relief."""
    lod = p3d.lods[0]
    plate = box_points(lod, PLATE)
    glyph = [p for box in (STEM, TOP_ARM, MID_ARM)
             for p in box_points(lod, box)]
    size = [max(p[i] for p in plate) - min(p[i] for p in plate)
            for i in range(3)]
    depth = size.index(min(size))
    toward_viewer = [0.0, 0.0, 0.0]
    toward_viewer[depth] = (1.0 if centroid(glyph)[depth]
                            > centroid(plate)[depth] else -1.0)
    arms = sub(centroid(box_points(lod, TOP_ARM) + box_points(lod, MID_ARM)),
               centroid(box_points(lod, STEM)))
    right = screen_right(tuple(toward_viewer), up, left_handed)
    return "F" if dot(arms, right) > 0 else "mirrored F"


# ---- the fixture is the model the game showed ---------------------------

def test_b2d_writes_the_measured_bytes(fork):
    """blender_to_dayz() writes exactly the MLOD that rendered solid with a
    correctly reading F in game; the two control recipes write exactly the
    two that rendered mirrored."""
    for tag in "BAC":
        data = write_bytes(variant(fork, tag))
        assert hashlib.sha256(data).hexdigest() == MEASURED[tag], tag


def test_b2d_screen_right_rule(fork):
    """The viewing rule the chirality check rests on, against two facts:
    Blender's front view has +X on the right, and in DayZ +X is east, on
    the right of a viewer facing north. It predicted A and B correctly in
    game."""
    assert screen_right((0.0, -1.0, 0.0), BLENDER_UP, False) == (1.0, 0.0, 0.0)
    assert screen_right((0.0, 0.0, -1.0), DAYZ_UP, True) == (1.0, 0.0, 0.0)
    assert screen_right((0.0, 0.0, 1.0), DAYZ_UP, True) == (-1.0, 0.0, 0.0)


# ---- the two properties the game showed ---------------------------------

def test_b2d_keeps_handedness(fork):
    """Seen face-on from the relief side, the F reads correctly in Blender
    and, after blender_to_dayz(), in DayZ. A and C read mirrored, so the
    check can fail; up stays up in all three."""
    assert reading(build_chiral_f_p3d(fork), BLENDER_UP, False) == "F"
    readings = {}
    for tag in "BAC":
        p3d = variant(fork, tag)
        lod = p3d.lods[0]
        assert (centroid(box_points(lod, TOP_ARM))[1]
                > centroid(box_points(lod, MID_ARM))[1]), tag
        readings[tag] = reading(p3d, DAYZ_UP, True)
    assert readings == {"B": "F", "A": "mirrored F", "C": "mirrored F"}


def test_b2d_mlod_winding_points_inward(fork):
    """MLOD convention: the vertex-order cross product and the normals point
    INWARD, on all 48 faces after blender_to_dayz() - also once written and
    read back. The Blender input points outward on all 48, and so does C,
    which rendered inside-out."""
    assert inward_counts(build_chiral_f_p3d(fork)) == (48, 0, 0)
    converted = variant(fork, "B")
    assert inward_counts(converted) == (48, 48, 48)
    assert inward_counts(read_p3d(fork, write_bytes(converted))) == (48, 48, 48)
    assert inward_counts(variant(fork, "C")) == (48, 0, 0)


def test_b2d_winding_cannot_see_a_mirror(fork):
    """A passes the same inward check, 48 of 48, and is mirrored in game: a
    winding gate is not a chirality gate."""
    a = variant(fork, "A")
    assert inward_counts(a) == (48, 48, 48)
    assert reading(a, DAYZ_UP, True) == "mirrored F"


def test_b2d_reflection_alone_is_inside_out(fork):
    """transform() with the det=-1 matrix alone puts every point where
    blender_to_dayz() does but reverses every face: cross product and
    normals OUTWARD. That is why the matrix stays private."""
    p3d = build_chiral_f_p3d(fork)
    p3d.transform(fork._BLENDER_TO_DAYZ_AXES)
    assert inward_counts(p3d) == (48, 0, 0)
    assert reading(p3d, DAYZ_UP, True) == "F"
    b = variant(fork, "B")
    assert ([p.coords for p in p3d.lods[0].points]
            == [p.coords for p in b.lods[0].points])


# ---- what it does to the data ---------------------------------------------

def test_b2d_maps_points_keeps_order_negates_normals(fork):
    """Points (x,y,z) -> (x,z,y); vertex order, normal_index and uv
    unchanged; normals (nx,ny,nz) -> (-nx,-nz,-ny). Checked on the bytes
    read back, which is what AddonBuilder gets."""
    src = build_chiral_f_p3d(fork).lods[0]
    got = read_p3d(fork, write_bytes(variant(fork, "B"))).lods[0]
    for old, new in zip(src.points, got.points):
        x, y, z = old.coords
        assert new.coords == tuple(f32(c) for c in (x, z, y))
    for old, new in zip(src.facenormals, got.facenormals):
        nx, ny, nz = old
        assert new == tuple(f32(c) for c in (-nx, -nz, -ny))
    assert len(got.faces) == len(src.faces) == 48
    for old, new in zip(src.faces, got.faces):
        assert ([v.point_index for v in new.vertices]
                == [v.point_index for v in old.vertices])
        assert ([v.normal_index for v in new.vertices]
                == [v.normal_index for v in old.vertices])
        assert ([v.uv for v in new.vertices]
                == [tuple(f32(c) for c in v.uv) for v in old.vertices])


def test_b2d_multilod_every_lod_validate_clean(fork):
    """Every LOD converts - visual, the three collision LODs and the memory
    points - and validate() stays [] on the clean multi-LOD model."""
    p3d = build_multilod_v2_p3d(fork)
    assert p3d.validate() == []
    before = [([p.coords for p in lod.points], list(lod.facenormals),
               [[v.point_index for v in fa.vertices] for fa in lod.faces])
              for lod in p3d.lods]
    mem = p3d.get_lod("memory")
    mem_before = mem.get_memory_points()
    fork.blender_to_dayz(p3d)
    assert p3d.validate() == []
    kinds = [lod.kind() for lod in p3d.lods]
    assert kinds == ["visual", "geometry", "view_geometry", "fire_geometry",
                     "memory"]
    for lod, kind, (points, normals, orders) in zip(p3d.lods, kinds, before):
        assert len(lod.points) == len(points), kind
        for (x, y, z), p in zip(points, lod.points):
            assert close3(p.coords, (x, z, y)), kind
        for (nx, ny, nz), n in zip(normals, lod.facenormals):
            assert close3(n, (-nx, -nz, -ny)), kind
        assert [[v.point_index for v in fa.vertices]
                for fa in lod.faces] == orders, kind
    for name, (x, y, z) in mem_before.items():
        assert close3(mem.get_memory_points()[name], (x, z, y)), name


@pytest.mark.parametrize("shared", ["point", "facenormals"])
def test_b2d_refuses_shared_data_before_any_change(fork, shared):
    """A Point object or a facenormals list in two LODs would be mapped
    twice by transform(): (1,2,3) would come back unconverted. The call
    raises and leaves the model as it was."""
    p3d = fork.P3D()
    vis = build_chiral_f_p3d(fork).lods[0]
    other = build_chiral_f_p3d(fork).lods[0]
    other.resolution = 1.0
    if shared == "point":
        other.points[0] = vis.points[0]
    else:
        other.facenormals = vis.facenormals
    p3d.lods += [vis, other]
    snapshot = [([p.coords for p in lod.points], list(lod.facenormals),
                 [[v.point_index for v in fa.vertices] for fa in lod.faces])
                for lod in p3d.lods]
    with pytest.raises(ValueError, match="Nothing was changed"):
        fork.blender_to_dayz(p3d)
    assert snapshot == [([p.coords for p in lod.points], list(lod.facenormals),
                         [[v.point_index for v in fa.vertices]
                          for fa in lod.faces])
                        for lod in p3d.lods]


def test_b2d_second_call_undoes_the_first(fork):
    """The map is its own inverse and so is the normal sign: two calls give
    the model back - points, normals and vertex order. By value, not by
    bytes: a zero normal component can come back as -0.0. The model's
    normals are unit vectors; one that is not comes back unit-length,
    because P3D.transform() renormalizes."""
    p3d = build_chiral_f_p3d(fork)
    lod = p3d.lods[0]
    points = [p.coords for p in lod.points]
    normals = list(lod.facenormals)
    orders = [[v.point_index for v in fa.vertices] for fa in lod.faces]
    fork.blender_to_dayz(p3d)
    assert [p.coords for p in lod.points] != points
    fork.blender_to_dayz(p3d)
    assert [p.coords for p in lod.points] == points
    assert lod.facenormals == normals
    assert [[v.point_index for v in fa.vertices] for fa in lod.faces] == orders
    lod.facenormals[0] = (0.0, 2.0, 0.0)
    fork.blender_to_dayz(p3d)
    fork.blender_to_dayz(p3d)
    assert lod.facenormals[0] == (0.0, 1.0, 0.0)


# ---- ERR_WINDING_VS_NORMALS: a disagreement, not a direction ---------------

def negate_normals(lod):
    for i, n in enumerate(lod.facenormals):
        lod.facenormals[i] = (-n[0], -n[1], -n[2])


def reverse_faces(lod):
    for fa in lod.faces:
        fa.vertices.reverse()


def turned(fork, side):
    """B, the export that rendered right, with one side turned on every
    face: its normals ("normals") or its vertex order ("winding")."""
    p3d = variant(fork, "B")
    {"normals": negate_normals, "winding": reverse_faces}[side](p3d.lods[0])
    return p3d


def signed_volume(faces):
    """The sum of dot(v0, v1 x v2) / 6 over the fan triangles of *faces*:
    the signed volume by winding, when they form a closed shell."""
    total = 0.0
    for fa in faces:
        vs = [v.point.coords for v in fa.vertices]
        for i in range(1, len(vs) - 1):
            total += dot(vs[0], cross(vs[i], vs[i + 1])) / 6.0
    return total


def shell_volume(lod, box):
    """Signed volume by winding of one box, a closed shell with its own
    eight points. Negative when the cross product points into the box, the
    sign of a solid seen from outside on shipped MLODs."""
    return signed_volume([fa for fa in lod.faces
                          if fa.vertices[0].point_index // 8 == box])


def vs_normals(p3d):
    return [f for f in p3d.validate() if f.code == "ERR_WINDING_VS_NORMALS"]


def boxes(lod):
    return [[fa for fa in lod.faces if fa.vertices[0].point_index // 8 == k]
            for k in range(4)]


def corners_right(p3d):
    """Corner normals, of all 144, that point into their box: inward_counts()
    reads only each face's first corner, as the check does."""
    lod = p3d.lods[0]
    right = 0
    for fa in lod.faces:
        out = sub(centroid([v.point.coords for v in fa.vertices]),
                  centroid(box_points(lod, fa.vertices[0].point_index // 8)))
        right += sum(dot(v.normal, out) < 0 for v in fa.vertices)
    return right


def negate_normals_of(lod, faces):
    """Negate every corner normal of *faces*, whatever it points at: a pool
    entry no other face uses in place, one that another face also uses as a
    negated copy that only the corners of *faces* are re-pointed to."""
    mine = {id(fa) for fa in faces}
    kept = {v.normal_index for fa in lod.faces if id(fa) not in mine
            for v in fa.vertices}
    copies = {}
    for fa in faces:
        for v in fa.vertices:
            j = v.normal_index
            if j in kept:
                if j not in copies:
                    n = lod.facenormals[j]
                    lod.facenormals.append((-n[0], -n[1], -n[2]))
                    copies[j] = len(lod.facenormals) - 1
                v.normal_index = copies[j]
    for j in {v.normal_index for fa in faces for v in fa.vertices} - kept:
        if j not in copies.values():
            n = lod.facenormals[j]
            lod.facenormals[j] = (-n[0], -n[1], -n[2])


def negate_corners(lod, flip):
    """Negate the normals of the corners in *flip*, in the pool. An entry
    only those corners use is negated in place. An entry that a kept corner
    also uses stays, and the corner is re-pointed to a kept entry that
    already holds the negated value, or else to a negated copy."""
    mine = {id(v) for v in flip}
    keep = {v.normal_index for fa in lod.faces for v in fa.vertices
            if id(v) not in mine}
    kept_value = {}
    for j in sorted(keep):
        kept_value.setdefault(lod.facenormals[j], j)
    in_place = {v.normal_index for v in flip} - keep
    for j in in_place:
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    copies = {}
    for v in flip:
        if v.normal_index in in_place:
            continue
        n = lod.facenormals[v.normal_index]
        target = (-n[0], -n[1], -n[2])
        if target in kept_value:
            v.normal_index = kept_value[target]
            continue
        if target not in copies:
            lod.facenormals.append(target)
            copies[target] = len(lod.facenormals) - 1
        v.normal_index = copies[target]


def fix_corners(lod):
    """The normals step up to 1.10.0, once the winding is settled: negate
    each corner normal that points against its face's cross product, with
    the pool rule of negate_corners()."""
    flip = []
    for fa in lod.faces:
        vs = [v.point.coords for v in fa.vertices]
        cr = cross(sub(vs[1], vs[0]), sub(vs[2], vs[0]))
        flip += [v for v in fa.vertices if dot(cr, v.normal) < 0]
    negate_corners(lod, flip)


def unit(a):
    length = math.sqrt(dot(a, a))
    if length == 0.0:
        return None
    return (a[0] / length, a[1] / length, a[2] / length)


def vector_area(fa):
    """The sum of cross(v[j] - v[0], v[j+1] - v[0]) over the face's fan:
    twice its vector area, the same from any first corner, and turned
    exactly by a reversal."""
    vs = [v.point.coords for v in fa.vertices]
    total = (0.0, 0.0, 0.0)
    for j in range(1, len(vs) - 1):
        c = cross(sub(vs[j], vs[0]), sub(vs[j + 1], vs[0]))
        total = (total[0] + c[0], total[1] + c[1], total[2] + c[2])
    return total


def face_reading(fa):
    """README, 'Winding', step 3: the average of a face's corner normals
    against its vector area, both normalized. Returns (dot, side): side +1
    reads with its winding (dot >= 0.5), -1 against it (dot <= -0.5), 0 no
    reading - in between, or with a corner normal that is zero or whose own
    dot has the other sign or lies within 0.1 of zero."""
    area = unit(vector_area(fa))
    total = (0.0, 0.0, 0.0)
    for v in fa.vertices:
        n = v.normal
        total = (total[0] + n[0], total[1] + n[1], total[2] + n[2])
    mean = unit(total)
    if area is None or mean is None:
        return 0.0, 0
    reading = dot(area, mean)
    normals = [unit(v.normal) for v in fa.vertices]
    if None in normals:
        return reading, 0
    corners = [dot(area, n) for n in normals]
    if reading >= 0.5 and min(corners) >= 0.1:
        return reading, 1
    if reading <= -0.5 and max(corners) <= -0.1:
        return reading, -1
    return reading, 0


def fix_parts(lod, parts, groups=None):
    """README, 'Winding', step 3, once the winding is settled. *parts* are
    the parts steps 1 and 2 read, as lists of faces; *groups* maps a part's
    index to the faces step 1 or 2 found wound against the rest before
    turning any. A part reads cleanly when every face of it has a reading
    and its larger group (the whole part without one) reads all one way;
    there the normals of the faces that read against their winding are
    negated and the rest kept. Returns the indices of the parts left as
    they are, to inspect."""
    groups = groups or {}
    against, inspect = [], []
    for k, faces in enumerate(parts):
        side = {id(fa): face_reading(fa)[1] for fa in faces}
        group = {id(fa) for fa in groups.get(k, ())}
        rest = [fa for fa in faces if id(fa) not in group]
        if 2 * len(rest) == len(faces):
            inspect.append(k)
            continue
        larger = (rest if 2 * len(rest) > len(faces)
                  else [fa for fa in faces if id(fa) in group])
        if 0 in side.values() or len({side[id(fa)] for fa in larger}) != 1:
            inspect.append(k)
            continue
        against += [fa for fa in faces if side[id(fa)] < 0]
    negate_corners(lod, [v for fa in against for v in fa.vertices])
    return inspect


def smoothed(fork, points, faces):
    """A LOD of *faces* over *points* with one normal per point, shared by
    every face that uses it: the normalized sum of their vector areas, so
    the normals follow the winding."""
    lod = fork.LOD()
    lod.resolution = 0.0
    for c in points:
        p = fork.Point()
        p.coords = c
        lod.points.append(p)
    sums = [(0.0, 0.0, 0.0)] * len(points)
    for idx in faces:
        vs = [points[i] for i in idx]
        area = (0.0, 0.0, 0.0)
        for j in range(1, len(vs) - 1):
            c = cross(sub(vs[j], vs[0]), sub(vs[j + 1], vs[0]))
            area = (area[0] + c[0], area[1] + c[1], area[2] + c[2])
        for i in idx:
            s = sums[i]
            sums[i] = (s[0] + area[0], s[1] + area[1], s[2] + area[2])
    lod.facenormals[:] = [unit(s) for s in sums]
    for idx in faces:
        fa = fork.Face(lod.points, lod.facenormals)
        for i in idx:
            v = fork.Vertex(lod.points, lod.facenormals)
            v.point_index = i
            v.normal_index = i
            fa.vertices.append(v)
        lod.faces.append(fa)
    return lod


def share_pool(lod):
    """One pool entry per distinct normal, so an entry serves several
    boxes."""
    pool = []
    for fa in lod.faces:
        for v in fa.vertices:
            n = v.normal
            if n not in pool:
                pool.append(n)
            v.normal_index = pool.index(n)
    lod.facenormals[:] = pool


def faces_against_every_neighbour(lod):
    """Faces each of whose edges another face runs in the same direction: a
    face turned on its own inside a shell. A turned group of faces needs a
    flood fill over shared edges instead; none of these fixtures has one."""
    runs = {}
    for fa in lod.faces:
        idx = [v.point_index for v in fa.vertices]
        for edge in zip(idx, idx[1:] + idx[:1]):
            runs[edge] = runs.get(edge, 0) + 1
    against = []
    for fa in lod.faces:
        idx = [v.point_index for v in fa.vertices]
        if all(runs[edge] > 1 for edge in zip(idx, idx[1:] + idx[:1])):
            against.append(fa)
    return against


def test_vs_normals_cannot_tell_which_side_is_wrong(fork):
    """Normals turned and faces turned read alike: 0 % agreement and the
    same finding with the same text, though they need opposite fixes. So
    the message gives an order that works for both - the winding first,
    the normals after - not one fix. B passes."""
    assert vs_normals(variant(fork, "B")) == []
    msgs = []
    for side in ("normals", "winding"):
        p3d = turned(fork, side)
        assert fork._pct_normal_agreement(p3d.lods[0]) == 0.0, side
        found = vs_normals(p3d)
        assert [(f.severity, f.lod) for f in found] == [("ERROR", 0)], side
        msgs.append(found[0].msg)
    assert msgs[0] == msgs[1]
    for needle in ("not which one is wrong", "first corner",
                   "winding first, normals untouched",
                   "WARN_WINDING_EDGE_INCOHERENT", "signed volume",
                   "face.vertices.reverse()", "vertices[1]/[2] swap",
                   fork._normals_step(),
                   "lod.facenormals[j] = (-x, -y, -z)", "negated copy"):
        assert needle in msgs[0], needle
    assert "wound backwards" not in msgs[0]
    assert "each corner normal that still points" not in msgs[0]


def test_vs_normals_direction_picks_the_fix(fork):
    """The signed volume tells the two apart: with the normals turned every
    box keeps B's negative sign, so the winding stays; with the faces
    turned every box flips, so every face is reversed. Then the normals,
    box by box: every box reads cleanly, its faces against their winding
    where the normals were turned and with it where the faces were, and
    negating the faces that read against gives back B, cross product and
    normals inward on 48 of 48 faces; negating the faces that read with it
    instead leaves 0 of 48 normals inward. The other fix
    silences the finding just as well - 100 % agreement, validate()
    returns [] - and leaves both outward, the orientation C rendered
    inside-out with; on the normals-turned model it is the fix this
    message used to give. The signs the message gives are the ones
    measured here: B, a solid seen from outside that rendered right in
    game, is negative, and B turned deliberately inside-out, faces and
    normals, which is what a room seen from inside is, is positive."""
    b = variant(fork, "B").lods[0]
    assert all(shell_volume(b, k) < 0 for k in range(4))
    msg = vs_normals(turned(fork, "normals"))[0].msg
    assert "negative for a solid seen from outside" in msg
    room = variant(fork, "B").lods[0]
    reverse_faces(room)
    negate_normals(room)
    assert all(shell_volume(room, k) > 0 for k in range(4))
    assert "positive for a room seen from inside" in msg
    for side, winding_right in (("normals", True), ("winding", False)):
        p3d = turned(fork, side)
        lod = p3d.lods[0]
        assert ([shell_volume(lod, k) < 0 for k in range(4)]
                == [winding_right] * 4), side
        if not winding_right:
            reverse_faces(lod)
        sides = {face_reading(fa)[1] for fa in lod.faces}
        assert sides == ({-1} if winding_right else {1}), side
        swapped = turned(fork, side)
        if not winding_right:
            reverse_faces(swapped.lods[0])
        negate_corners(swapped.lods[0],
                       [v for fa in swapped.lods[0].faces
                        if face_reading(fa)[1] > 0 for v in fa.vertices])
        assert inward_counts(swapped)[2] == 0, side
        assert fix_parts(lod, boxes(lod)) == [], side
        assert inward_counts(p3d) == (48, 48, 48), side
        assert p3d.validate() == [], side
        wrong = turned(fork, side)
        if winding_right:
            reverse_faces(wrong.lods[0])
        else:
            negate_normals(wrong.lods[0])
        assert inward_counts(wrong) == (48, 0, 0), side
        assert wrong.validate() == [], side


def test_vs_normals_blind_to_faces_and_normals_turned_together(fork):
    """C rendered inside-out in game and validate() has nothing to say about
    it: its faces and normals agree on every face."""
    c = variant(fork, "C")
    assert inward_counts(c) == (48, 0, 0)
    assert fork._pct_normal_agreement(c.lods[0]) == 100.0
    assert c.validate() == []


def test_vs_normals_collision_lod_asks_for_the_component_check(fork):
    """On a collision LOD the message asks for the per-component check
    instead of the signed volume, with the sign blender_to_dayz writes: on
    the converted Geometry cube, one convex component, every face's cross
    product points inward."""
    p3d = build_multilod_v2_p3d(fork)
    fork.blender_to_dayz(p3d)
    index = [lod.kind() for lod in p3d.lods].index("geometry")
    geo = p3d.lods[index]
    middle = centroid([p.coords for p in geo.points])
    for fa in geo.faces:
        vs = [v.point.coords for v in fa.vertices]
        out = sub(centroid(vs), middle)
        assert dot(cross(sub(vs[1], vs[0]), sub(vs[2], vs[0])), out) < 0
    negate_normals(geo)
    found = vs_normals(p3d)
    assert [(f.severity, f.lod) for f in found] == [("ERROR", index)]
    assert "inward expected" in found[0].msg
    assert "convex component" in found[0].msg
    assert "signed volume" not in found[0].msg


def test_vs_normals_shared_pool_entry_gets_a_copy(fork):
    """Three boxes with their normals turned and the stem with its faces
    turned, on a pool of six entries that serve every box. Negating the
    entries of the boxes whose normals are wrong also turns the stem's,
    which were right: 75 %, its 12 faces disagreeing. Reversing the stem by
    its volume, then reading the normals box by box, gives back B: the
    three boxes read against their winding and the stem with it, and the
    corners negated are re-pointed to entries that already hold the negated
    values, so the pool stays at six."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        for k, faces in enumerate(boxes(lod)):
            if k == STEM:
                for fa in faces:
                    fa.vertices.reverse()
            else:
                negate_normals_of(lod, faces)
        share_pool(lod)
        return p3d
    p3d = broken()
    lod = p3d.lods[0]
    assert len(lod.facenormals) == 6
    assert [f.code for f in p3d.validate()] == ["ERR_WINDING_VS_NORMALS"]
    assert ([shell_volume(lod, k) < 0 for k in range(4)]
            == [k != STEM for k in range(4)])
    parts = boxes(lod)
    normals_wrong = [fa for k in range(4) if k != STEM for fa in parts[k]]
    for j in {v.normal_index for fa in normals_wrong for v in fa.vertices}:
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    for fa in parts[STEM]:
        fa.vertices.reverse()
    assert fork._pct_normal_agreement(lod) == 75.0
    assert inward_counts(p3d) == (48, 48, 36)
    p3d = broken()
    lod = p3d.lods[0]
    for fa in boxes(lod)[STEM]:
        fa.vertices.reverse()
    assert [{face_reading(fa)[1] for fa in faces} for faces in boxes(lod)] == [
        {1} if k == STEM else {-1} for k in range(4)]
    assert fix_parts(lod, boxes(lod)) == []
    assert inward_counts(p3d) == (48, 48, 48)
    assert corners_right(p3d) == 144
    assert len(lod.facenormals) == 6
    assert p3d.validate() == []


def test_vs_normals_shell_agrees_with_itself_before_its_volume_counts(fork):
    """Every normal turned, and one face of the plate turned back with an
    inward normal of its own: 0 % agreement and an incoherent edge. The
    plate keeps its negative volume, so the volume alone picks "negate the
    normals", which leaves that face inside-out and the edge warning
    standing. Turning first the vertex order of the face that disagrees
    with its neighbours makes the shell coherent; its volume then keeps the
    winding. The plate's larger group, the 11 faces left, reads against its
    winding, the turned face with it, and negating the faces that read
    against gives back B. Read without setting the turned face apart, the
    plate splits 11 against 1 and is left to inspect."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        negate_normals(lod)
        fa = lod.faces[0]
        fa.vertices.reverse()
        n = fa.vertices[0].normal
        lod.facenormals.append((-n[0], -n[1], -n[2]))
        for v in fa.vertices:
            v.normal_index = len(lod.facenormals) - 1
        return p3d
    p3d = broken()
    lod = p3d.lods[0]
    assert lod.faces[0].vertices[0].point_index // 8 == PLATE
    assert [f.code for f in p3d.validate()] == [
        "ERR_WINDING_VS_NORMALS", "WARN_WINDING_EDGE_INCOHERENT"]
    assert shell_volume(lod, PLATE) < 0
    negate_normals(lod)
    assert fork._pct_normal_agreement(lod) == 100.0
    assert [f.code for f in p3d.validate()] == ["WARN_WINDING_EDGE_INCOHERENT"]
    assert inward_counts(p3d) == (48, 47, 47)
    p3d = broken()
    lod = p3d.lods[0]
    against = faces_against_every_neighbour(lod)
    assert against == [lod.faces[0]]
    for fa in against:
        fa.vertices.reverse()
    assert [f.code for f in p3d.validate()] == ["ERR_WINDING_VS_NORMALS"]
    assert shell_volume(lod, PLATE) < 0
    plate = boxes(lod)[PLATE]
    assert [face_reading(fa)[1] for fa in plate] == [1] + [-1] * 11
    whole = broken()
    for fa in faces_against_every_neighbour(whole.lods[0]):
        fa.vertices.reverse()
    assert fix_parts(whole.lods[0], boxes(whole.lods[0])) == [PLATE]
    assert inward_counts(whole) == (48, 48, 37)
    assert fix_parts(lod, boxes(lod), {PLATE: against}) == []
    assert inward_counts(p3d) == (48, 48, 48)
    assert p3d.validate() == []


def test_vs_normals_turn_the_odd_face_without_its_normal(fork):
    """The plate with 11 of its 12 faces reversed, their normals right, and
    the other boxes with their normals turned: 2 % agreement and an
    incoherent edge. The plate's one face that disagrees with its
    neighbours is the right one. Turning it with its normal, then the
    shell by its volume, then the normals of the boxes left (the order of
    the previous message) leaves that face's normal wrong, and validate()
    returns [] at 47 of 48. Turning only its vertex order, then the shell,
    then reading the normals box by box gives back B: the plate's larger
    group, the 11 faces the shell turned once, reads with its winding, and
    so does the odd face, turned twice; the other boxes read against."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        parts = boxes(lod)
        for fa in parts[PLATE][1:]:
            fa.vertices.reverse()
        negate_normals_of(lod, [fa for k in range(4) if k != PLATE
                                for fa in parts[k]])
        return p3d
    for together in (True, False):
        p3d = broken()
        lod = p3d.lods[0]
        parts = boxes(lod)
        assert [f.code for f in p3d.validate()] == [
            "ERR_WINDING_VS_NORMALS", "WARN_WINDING_EDGE_INCOHERENT"]
        odd = faces_against_every_neighbour(lod)
        assert odd == [parts[PLATE][0]]
        for fa in odd:
            fa.vertices.reverse()
        if together:
            negate_normals_of(lod, odd)
        assert shell_volume(lod, PLATE) > 0
        for fa in parts[PLATE]:
            fa.vertices.reverse()
        if together:
            negate_normals_of(lod, [fa for k in range(4) if k != PLATE
                                    for fa in parts[k]])
            assert inward_counts(p3d) == (48, 48, 47)
        else:
            assert {face_reading(fa)[1] for fa in parts[PLATE]} == {1}
            assert fix_parts(lod, parts, {PLATE: odd}) == []
            assert inward_counts(p3d) == (48, 48, 48)
        assert p3d.validate() == []


def test_vs_normals_odd_corners_leave_their_part_to_inspect(fork):
    """B with only each face's first corner turned: the check reads 0 %, as
    it reads first corners, though 96 of 144 corners are right. Negating
    whole faces turns those too - 48 of 144 right while the check reads
    100 % and validate() returns []. Read part by part, no face has a
    reading - each has a corner on the other side of it - so every box is
    left as it is, to inspect, and the finding stands. Negating each corner
    that points against its face, the step up to 1.10.0, gives back all 144
    on these flat normals; on smoothed ones it turns right normals (the flat
    tetrahedron below)."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        for fa in lod.faces:
            n = fa.vertices[0].normal
            lod.facenormals.append((-n[0], -n[1], -n[2]))
            fa.vertices[0].normal_index = len(lod.facenormals) - 1
        return p3d
    p3d = broken()
    assert corners_right(p3d) == 96
    assert fork._pct_normal_agreement(p3d.lods[0]) == 0.0
    negate_normals_of(p3d.lods[0], p3d.lods[0].faces)
    assert fork._pct_normal_agreement(p3d.lods[0]) == 100.0
    assert corners_right(p3d) == 48
    assert p3d.validate() == []
    p3d = broken()
    lod = p3d.lods[0]
    assert {face_reading(fa)[1] for fa in lod.faces} == {0}
    assert fix_parts(lod, boxes(lod)) == [0, 1, 2, 3]
    assert corners_right(p3d) == 96
    assert [f.code for f in p3d.validate()] == ["ERR_WINDING_VS_NORMALS"]
    p3d = broken()
    fix_corners(p3d.lods[0])
    assert corners_right(p3d) == 144
    assert p3d.validate() == []


FLAT_TETRA_POINTS = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0),
                     (0.2, 0.2, 0.02)]
FLAT_TETRA_FACES = [(0, 1, 2), (3, 1, 0), (0, 2, 3), (3, 2, 1)]


def corner_normals(lod):
    return [[v.normal for v in fa.vertices] for fa in lod.faces]


def winding_codes(fork, lod):
    p3d = fork.P3D()
    p3d.lods = [lod]
    return [f.code for f in p3d.validate() if "WINDING" in f.code]


def test_normals_step_leaves_a_smoothed_flat_tetrahedron_as_it_is(fork):
    """README, 'Winding', step 3. A flat tetrahedron wound inward, the sign
    of a solid seen from outside, with one area-weighted normal per point:
    healthy, it has 6 of its 12 corners against their faces, and validate()
    reads it at 75 % (WARN_WINDING_NORMAL_MISMATCH). Reversed whole and set
    right by its volume, it reads part by part with faces that have no
    reading, so it is left as it is: the healthy model, normal for normal.
    Negating each corner that points against its face, the step up to
    1.9.0, turns six right normals through three pool copies and takes it
    to 100 % with no finding."""
    healthy = smoothed(fork, FLAT_TETRA_POINTS, FLAT_TETRA_FACES)
    assert signed_volume(healthy.faces) < 0
    assert sum(dot(vector_area(fa), v.normal) < 0
               for fa in healthy.faces for v in fa.vertices) == 6
    assert fork._pct_normal_agreement(healthy) == 75.0
    assert winding_codes(fork, healthy) == ["WARN_WINDING_NORMAL_MISMATCH"]
    reference = corner_normals(healthy)
    for repair in ("per part", "per corner"):
        lod = smoothed(fork, FLAT_TETRA_POINTS, FLAT_TETRA_FACES)
        reverse_faces(lod)
        assert signed_volume(lod.faces) > 0
        reverse_faces(lod)
        assert corner_normals(lod) == reference
        if repair == "per part":
            assert 0 in {face_reading(fa)[1] for fa in lod.faces}
            assert fix_parts(lod, [list(lod.faces)]) == [0]
            assert corner_normals(lod) == reference
            assert len(lod.facenormals) == 4
            assert winding_codes(fork, lod) == ["WARN_WINDING_NORMAL_MISMATCH"]
        else:
            fix_corners(lod)
            assert sum(n != r for got, ref in zip(corner_normals(lod),
                                                 reference)
                       for n, r in zip(got, ref)) == 6
            assert len(lod.facenormals) == 4 + 3
            assert fork._pct_normal_agreement(lod) == 100.0
            assert winding_codes(fork, lod) == []


def test_normals_step_reading_turns_with_the_face(fork):
    """A face whose winding is turned reads as before with the sign turned,
    from whichever corner the reversal starts: the vector area turns
    exactly, also on a dart quad whose first three corners point against
    it and on a twisted quad. A part whose two groups are of one size has
    no larger one, and is left to inspect."""
    quads = {
        "planar": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0),
                   (0.0, 1.0, 0.0)],
        "dart": [(0.0, 2.0, 0.0), (0.5, 1.0, 0.0), (0.0, 0.0, 0.0),
                 (2.0, 1.0, 0.0)],
        "twisted": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.3), (1.0, 1.0, 0.0),
                    (0.0, 1.0, 0.3)],
    }
    first_three = {}
    for name, points in quads.items():
        for turn in ("reverse", "keep the first corner"):
            lod = fork.LOD()
            for c in points:
                p = fork.Point()
                p.coords = c
                lod.points.append(p)
            lod.facenormals.append(unit((0.2, -0.3, 1.0)))
            fa = fork.Face(lod.points, lod.facenormals)
            for i in range(4):
                v = fork.Vertex(lod.points, lod.facenormals)
                v.point_index = i
                v.normal_index = 0
                fa.vertices.append(v)
            lod.faces.append(fa)
            vs = [v.point.coords for v in fa.vertices]
            first_three[name] = dot(cross(sub(vs[1], vs[0]),
                                          sub(vs[2], vs[0])), fa.vertices[0].normal)
            before = face_reading(fa)
            assert before[1] == 1, name
            if turn == "reverse":
                fa.vertices.reverse()
            else:
                fa.vertices[1:] = fa.vertices[:0:-1]
            after = face_reading(fa)
            assert after[0] == pytest.approx(-before[0], abs=1e-12), name
            assert after[1] == -1, (name, turn)
    assert first_three["dart"] < 0 < first_three["planar"]
    lod = variant(fork, "B").lods[0]
    plate = boxes(lod)[PLATE]
    assert fix_parts(lod, [plate], {0: plate[:6]}) == [0]
    assert fix_parts(lod, [plate], {0: plate[:5]}) == []


SMOOTH_BOX_POINTS = [(-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0),
                     (-1.0, 1.0, -1.0), (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0),
                     (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0)]
SMOOTH_BOX_FACES = [tri for quad in ((1, 2, 3, 0), (7, 6, 5, 4), (4, 5, 1, 0),
                                     (2, 6, 7, 3), (3, 7, 4, 0), (5, 6, 2, 1))
                    for tri in ((quad[0], quad[1], quad[2]),
                                (quad[0], quad[2], quad[3]))]


def test_normals_step_shared_entries_spoiled_in_place_are_inspected(fork):
    """A box smoothed with one normal per point, each shared by the three
    sides at its corner, wound inward. One side turned with its normals
    negated in place on those shared entries: once the side is turned back,
    18 of 36 corners point against their faces, on that side and on its
    four neighbours, whose faces lose their reading, so the box is left as
    it is, to inspect. Negating each corner against its face gives this
    box back, since every corner on the four entries points against its
    face. The same side turned with its normals through negated copies
    reads cleanly once turned back, and negating the two faces that read
    against gives back the box's normals."""
    healthy = smoothed(fork, SMOOTH_BOX_POINTS, SMOOTH_BOX_FACES)
    assert signed_volume(healthy.faces) < 0
    assert {face_reading(fa)[1] for fa in healthy.faces} == {1}
    reference = corner_normals(healthy)
    for how in ("in place", "copies", "in place, per corner"):
        lod = smoothed(fork, SMOOTH_BOX_POINTS, SMOOTH_BOX_FACES)
        side = lod.faces[:2]
        for fa in side:
            fa.vertices.reverse()
        if how == "copies":
            negate_normals_of(lod, side)
        else:
            for j in {v.normal_index for fa in side for v in fa.vertices}:
                n = lod.facenormals[j]
                lod.facenormals[j] = (-n[0], -n[1], -n[2])
        for fa in side:
            fa.vertices.reverse()
        if how == "copies":
            assert fix_parts(lod, [list(lod.faces)], {0: side}) == []
            assert corner_normals(lod) == reference
            continue
        assert sum(dot(vector_area(fa), v.normal) < 0
                   for fa in lod.faces for v in fa.vertices) == 18
        if how == "in place":
            spoiled = corner_normals(lod)
            assert fix_parts(lod, [list(lod.faces)], {0: side}) == [0]
            assert corner_normals(lod) == spoiled
        else:
            fix_corners(lod)
            assert corner_normals(lod) == reference


def tilted(n, along):
    """A unit normal at dot *along* with the unit normal *n*, the rest of
    it perpendicular to n."""
    other = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
    t = unit(cross(n, other))
    s = math.sqrt(1.0 - along * along)
    return (along * n[0] + s * t[0], along * n[1] + s * t[1],
            along * n[2] + s * t[2])


def own_normal(lod, corner, n):
    lod.facenormals.append(n)
    corner.normal_index = len(lod.facenormals) - 1


def unclear(fork, how):
    """B with faces that have no reading, as README step 3 defines it, and
    the groups to read them with. Every face of B is a triangle of a quad
    whose normal entry points along its vector area."""
    p3d = variant(fork, "B")
    lod = p3d.lods[0]
    plate = boxes(lod)[PLATE]
    groups = {}
    if how == "mean between, against":
        for j, n in enumerate(lod.facenormals):
            lod.facenormals[j] = tilted(n, -0.4)
    elif how == "corner within 0.1, against":
        negate_normals(lod)
        for fa in lod.faces:
            own_normal(lod, fa.vertices[0],
                       tilted(unit(vector_area(fa)), -0.05))
    elif how == "zero corner":
        own_normal(lod, lod.faces[0].vertices[0], (0.0, 0.0, 0.0))
    else:
        n = unit(vector_area(plate[0]))
        for v in plate[0].vertices:
            own_normal(lod, v, (-n[0], -n[1], -n[2]))
        groups = {PLATE: plate[:1]}
        for fa in plate[1:]:
            area = unit(vector_area(fa))
            if how == "mean between, with":
                for v in fa.vertices:
                    own_normal(lod, v, tilted(area, 0.4))
            else:
                own_normal(lod, fa.vertices[0], tilted(area, 0.05))
    return p3d, groups


def test_normals_step_unclear_faces_leave_their_part_as_it_is(fork):
    """README, 'Winding', step 3: a face has no reading when its corner
    normals average between -0.5 and 0.5 against its vector area, when one
    of them lies within 0.1 of its plane, or when one is zero, and a part
    with such a face is left as it is. On B: every normal turned to dot
    -0.4 (the faces average -0.4); every normal turned, with each face's
    first corner at -0.05 instead (the faces average -0.899, that corner
    within the margin); one corner normal zero, which validate() does not
    report; and the plate's first face turned against its winding, read as
    a group of one against the other 11, which average +0.4 or have a
    corner at +0.05. Each part with such a face is left to inspect, its
    normals as they were."""
    cases = {"mean between, against": ([0, 1, 2, 3], -0.4),
             "corner within 0.1, against": ([0, 1, 2, 3], -0.899),
             "zero corner": ([PLATE], None),
             "mean between, with": ([PLATE], 0.4),
             "corner within 0.1, with": ([PLATE], 0.899)}
    for how, (left, mean) in cases.items():
        p3d, groups = unclear(fork, how)
        lod = p3d.lods[0]
        readings = [face_reading(fa) for fa in boxes(lod)[PLATE][-1:]]
        if mean is not None:
            assert readings[0][0] == pytest.approx(mean, abs=1e-3), how
            assert readings[0][1] == 0, how
        else:
            assert face_reading(lod.faces[0])[1] == 0
            assert p3d.validate() == []
        before = corner_normals(lod)
        assert fix_parts(lod, boxes(lod), groups) == left, how
        assert corner_normals(lod) == before, how


def test_normals_step_is_one_text_in_both_findings(fork):
    """Both winding findings close with the same normals step, once each,
    and it says what README, 'Winding', step 3 does - part by part, the
    faces that read against their winding negated where the part reads
    cleanly, any other part left as it is - while the README gives the
    thresholds face_reading() uses and the tetrahedron's numbers measured
    above. The per-corner step of 1.10.0 and earlier is gone from both
    messages."""
    step = fork._normals_step()
    for needle in ("part by part, never a corner on its own sign",
                   "a normal smoothed across a sharp fold can point against "
                   "a face wound right",
                   "In a part that reads cleanly (py3d README, 'Winding', "
                   "step 3)",
                   "negate the normals of the faces that read against their "
                   "winding", "lod.facenormals[j] = (-x, -y, -z)",
                   "an entry a kept corner also uses gets a negated copy",
                   "and keep the rest",
                   "leave any other part as it is, for inspection"):
        assert needle in step, needle
    vs = vs_normals(turned(fork, "normals"))[0].msg
    inverted = multilod(fork, 0).validate()[0].msg
    for msg in (vs, inverted):
        assert msg.count(step) == 1
        assert "each corner normal that still points" not in msg
    readme = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "README.md")
    with open(readme, encoding="utf-8") as f:
        text = f.read()
    section = " ".join(text.split("3. **Normals**", 1)[1]
                       .split("\n\n", 1)[0].split())
    for needle in ("never a corner on its own sign", "`dot ≥ 0.5`",
                   "`dot ≤ −0.5`", "one of its corner normals is zero",
                   "within 0.1 of zero",
                   "its larger group of faces wound alike",
                   "two groups of one size leave no larger one",
                   "negate the normals of the faces that read against their "
                   "winding and keep the rest",
                   "Leave any other part as it is, to inspect",
                   "6 of its 12 corners", "at 75 %",
                   "through three pool copies", "to 100 % with no finding"):
        assert needle in section, needle


# ---- ERR_WINDING_INVERTED: two LODs disagree, not which one is wrong --------

def visual_shell(lod):
    """The visual LOD's shell, the icosphere. The proxy triangle is an open
    sheet and is left out."""
    proxy = lod.selections[PROXY].faces
    return [fa for fa in lod.faces if fa not in proxy]


def closed(faces):
    """Every edge of *faces* is shared by exactly two of them."""
    use = {}
    for fa in faces:
        idx = [v.point_index for v in fa.vertices]
        for a, b in zip(idx, idx[1:] + idx[:1]):
            key = (min(a, b), max(a, b))
            use[key] = use.get(key, 0) + 1
    return all(n == 2 for n in use.values())


def multilod(fork, inside_out=None):
    """The clean multi-LOD model after blender_to_dayz(), with LOD
    *inside_out* turned inside-out: faces and normals together, which the
    absolute check passes. On the visual LOD, its shell."""
    p3d = build_multilod_v2_p3d(fork)
    fork.blender_to_dayz(p3d)
    if inside_out is not None:
        lod = p3d.lods[inside_out]
        faces = visual_shell(lod) if inside_out == 0 else lod.faces
        for fa in faces:
            fa.vertices.reverse()
        negate_normals_of(lod, faces)
    return p3d


def outward_faces(lod, faces=None):
    """Faces whose cross product points away from the centroid of the LOD's
    points. Each collision LOD of the fixture is one convex box, so that is
    the per-component check."""
    middle = centroid([p.coords for p in lod.points])
    out = []
    for fa in lod.faces if faces is None else faces:
        vs = [v.point.coords for v in fa.vertices]
        if dot(cross(sub(vs[1], vs[0]), sub(vs[2], vs[0])),
               sub(centroid(vs), middle)) > 0:
            out.append(fa)
    return out


def named_visual(msg):
    """The index of the Visual LOD the message names, the same where it
    names the LOD and where it gives that LOD's steps."""
    opening = re.search(r"Visual LOD (\d+) \(resolution ", msg).group(1)
    steps = re.search(r"Visual LOD (\d+): in each closed shell", msg).group(1)
    assert opening == steps, (opening, steps)
    return int(opening)


def settle_winding(fork, p3d, visual):
    """The winding steps the message gives, normals untouched, on the
    visual LOD at index *visual* and on every collision LOD: the visual
    shell, coherent here, reversed whole if it is closed and its signed
    volume is positive (a solid seen from outside); each face of a
    collision LOD reversed if it points outward. Returns how many faces
    each of those LODs had reversed, by index."""
    turned = {}
    for i, lod in enumerate(p3d.lods):
        if i == visual:
            assert fork._pct_edge_coherence(lod) == 100.0
            shell = visual_shell(lod)
            faces = (shell if closed(shell) and signed_volume(shell) > 0
                     else [])
        elif lod.kind() in ("geometry", "view_geometry", "fire_geometry"):
            faces = outward_faces(lod)
        else:
            continue
        for fa in faces:
            fa.vertices.reverse()
        turned[i] = len(faces)
    return turned


def snapshot(p3d):
    return [([p.coords for p in lod.points], list(lod.facenormals),
             [[(v.point_index, v.normal_index, v.uv) for v in fa.vertices]
              for fa in lod.faces]) for lod in p3d.lods]


def parts_of(lod):
    """The parts the winding steps read: the visual LOD's shell when it is
    closed, and each collision LOD of the fixture, one convex box."""
    if lod.kind() == "visual":
        shell = visual_shell(lod)
        return [shell] if closed(shell) else []
    if lod.kind() in ("geometry", "view_geometry", "fire_geometry"):
        return [list(lod.faces)]
    return []


def test_inverted_cannot_tell_which_lod_is_wrong(fork):
    """The visual LOD inside-out raises the finding on the three healthy
    collision LODs and nowhere else; the geometry LOD inside-out, on the
    geometry LOD. The geometry LOD's text is the same in both, numbers
    aside - collision LOD first: 0 % and 100 % of faces wound outward in
    one, 100 % and 0 % in the other - and it gives the steps for both LODs,
    not "reverse every face of this LOD"."""
    assert multilod(fork).validate() == []
    msgs = []
    for inside_out, flagged, shares in ((0, [1, 2, 3], "0% and 100%"),
                                        (1, [1], "100% and 0%")):
        found = multilod(fork, inside_out).validate()
        assert ([(f.code, f.severity, f.lod) for f in found]
                == [("ERR_WINDING_INVERTED", "ERROR", i) for i in flagged])
        msg = found[0].msg
        assert msg.startswith(
            "geometry LOD and Visual LOD 0 (resolution 1, the visual LOD of "
            "lowest resolution, which this check compares against) are "
            "wound opposite ways: %s of their faces wind outward" % shares)
        msgs.append(msg)
    for needle in ("not which one is wrong",
                   "an inside-out Visual LOD raises this on the healthy "
                   "collision LODs",
                   "winding of both LODs first, normals untouched",
                   "Visual LOD 0: in each closed shell", "signed volume",
                   "geometry LOD: in each convex component",
                   "Never a vertices[1]/[2] swap", fork._normals_step()):
        assert needle in msgs[0], needle
    assert "on every face of this LOD" not in msgs[0]
    assert "each corner normal that still points" not in msgs[0]
    assert len({re.sub(r"\d+%", "N%", msg) for msg in msgs}) == 1


def test_inverted_steps_leave_the_part_that_reads_right(fork):
    """The signs the message gives, each next to its measurement. The clean
    model's visual shell is negative - a solid seen from outside - and no
    collision face points outward. With the visual LOD inside-out - which is
    also what a room seen from inside is - the shell reads positive and the
    collision boxes stay inward; with the geometry LOD inside-out its six
    faces read outward and the shell stays negative. Run on the LODs the
    message names, the steps reverse the turned LOD and nothing else, and
    once the normals are read part by part - every part reads cleanly - the
    model is the clean one again."""
    msg = multilod(fork, 0).validate()[0].msg
    clean = multilod(fork)
    assert signed_volume(visual_shell(clean.lods[0])) < 0
    assert "negative for a solid seen from outside" in msg
    assert [len(outward_faces(clean.lods[i])) for i in (1, 2, 3)] == [0, 0, 0]
    assert ("outward, against face centroid minus component centroid "
            "(inward expected)" in msg)
    cases = ((0, True, [0, 0, 0], {0: 320, 1: 0, 2: 0, 3: 0}),
             (1, False, [6, 0, 0], {0: 0, 1: 6, 2: 0, 3: 0}))
    for inside_out, positive, outward, turned in cases:
        p3d = multilod(fork, inside_out)
        assert (signed_volume(visual_shell(p3d.lods[0])) > 0) is positive
        assert [len(outward_faces(p3d.lods[i])) for i in (1, 2, 3)] == outward
        visual = named_visual(p3d.validate()[0].msg)
        assert visual == 0
        assert settle_winding(fork, p3d, visual) == turned, inside_out
        for lod in p3d.lods:
            assert fix_parts(lod, parts_of(lod)) == [], inside_out
        assert p3d.validate() == [], inside_out
        assert snapshot(p3d) == snapshot(clean), inside_out
    assert "positive for a room seen from inside" in msg
    assert "meant to be seen from inside reads positive and is right" in msg


def test_inverted_names_the_reference_visual_lod(fork):
    """With two visual LODs the check compares against the one of lowest
    resolution, which need not be the first in file order, the one
    get_lod("visual") returns. LOD 0 (resolution 10) is healthy and LOD 1
    (resolution 0) inside-out: every finding names LOD 1, the steps on the
    LOD it names clear them, and the same steps on get_lod("visual") change
    nothing."""
    def two_visuals():
        p3d = multilod(fork)
        p3d.lods[0].resolution = 10.0
        reference = multilod(fork, 0).lods[0]
        reference.resolution = 0.0
        p3d.lods.insert(1, reference)
        return p3d
    p3d = two_visuals()
    found = p3d.validate()
    assert ([(f.code, f.lod) for f in found]
            == [("ERR_WINDING_INVERTED", i) for i in (2, 3, 4)])
    assert all("Visual LOD 1 (resolution 0, the visual LOD of lowest "
               "resolution" in f.msg for f in found)
    assert {named_visual(f.msg) for f in found} == {1}
    first = p3d.lods.index(p3d.get_lod("visual"))
    assert first == 0
    assert settle_winding(fork, p3d, first) == {0: 0, 2: 0, 3: 0, 4: 0}
    assert [f.lod for f in p3d.validate()] == [2, 3, 4]
    p3d = two_visuals()
    assert settle_winding(fork, p3d, 1) == {1: 320, 2: 0, 3: 0, 4: 0}
    for lod in p3d.lods:
        assert fix_parts(lod, parts_of(lod)) == []
    assert p3d.validate() == []


def test_inverted_open_surface_stays_unresolved(fork):
    """The visual shell with one face removed is an open surface, with no
    closed shell for the steps to read. Turned inside-out, its 319 faces
    all wind outward and it raises the finding on the three collision LODs;
    the steps change nothing and the finding stands, so the message calls
    such a part unresolved, not right."""
    p3d = multilod(fork, 0)
    vis = p3d.lods[0]
    gone = visual_shell(vis)[0]
    vis.faces.remove(gone)
    for selection in vis.selections.values():
        selection.faces.pop(gone, None)
    shell = visual_shell(vis)
    assert len(shell) == 319 and not closed(shell)
    assert len(outward_faces(vis, shell)) == 319
    found = p3d.validate()
    assert ([(f.code, f.lod) for f in found]
            == [("ERR_WINDING_INVERTED", i) for i in (1, 2, 3)])
    assert settle_winding(fork, p3d, 0) == {0: 0, 1: 0, 2: 0, 3: 0}
    assert parts_of(vis) == []
    for lod in p3d.lods:
        assert fix_parts(lod, parts_of(lod)) == []
    assert [f.lod for f in p3d.validate()] == [1, 2, 3]
    assert len(outward_faces(vis, shell)) == 319
    assert ("A part these steps cannot read - not a closed shell, not a "
            "closed convex component - leaves this unresolved" in found[0].msg)
    assert "Only when every part of both LODs reads right" in found[0].msg


def test_inverted_old_fix_winds_the_collision_lods_outward(fork):
    """What the message used to say, on the visual case: reverse every face
    of each flagged LOD. That trades the finding for ERR_WINDING_VS_NORMALS
    on the three healthy collision LODs; with their normals negated as well,
    validate() returns [] and every LOD is wound outward - the collision
    LODs as transform(ROT_X_NEG90) alone leaves them, the map whose
    collision LODs registered no raycast in game."""
    p3d = multilod(fork, 0)
    for i in (1, 2, 3):
        reverse_faces(p3d.lods[i])
    assert ([(f.code, f.lod) for f in p3d.validate()]
            == [("ERR_WINDING_VS_NORMALS", i) for i in (1, 2, 3)])
    for i in (1, 2, 3):
        negate_normals(p3d.lods[i])
    assert p3d.validate() == []
    assert signed_volume(visual_shell(p3d.lods[0])) > 0
    assert [len(outward_faces(p3d.lods[i])) for i in (1, 2, 3)] == [6, 6, 6]
    rotated = build_multilod_v2_p3d(fork)
    rotated.transform(fork.ROT_X_NEG90)
    assert ([len(outward_faces(rotated.lods[i])) for i in (1, 2, 3)]
            == [6, 6, 6])


# ---- proxies: measured in game the same day --------------------------------

# Blender poses of the in-game proxy test: canonical raw rows (x, y, z) in
# Blender coordinates. Identity, yaw +90 about Blender Z, and yaw +90 after a
# 30 degree tilt about Blender X.
_C30, _S30 = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
BLENDER_PROXY_POSES = {
    "identity": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "yaw90": ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "yaw90_tilt30": ((0.0, 1.0, 0.0), (-_C30, 0.0, _S30), (_S30, 0.0, _C30)),
}


def swap(v):
    return (v[0], v[2], v[1])


@pytest.mark.parametrize("pose", sorted(BLENDER_PROXY_POSES))
def test_b2d_blender_proxy_equals_engine_space_proxy(fork, pose):
    """What the binarized files showed, pinned offline: a proxy drawn in
    Blender with add_proxy(space="raw") and converted with the model becomes
    the very triangle add_proxy(space="engine") builds in DayZ space for the
    frame worked out by hand - aside = M x, up = M z, dir = M y, M the swap.
    In game those proxies rendered in the pose drawn in Blender; the same
    matrices with space="raw" in DayZ space - raw frames passed off as engine
    frames - did not."""
    rows = BLENDER_PROXY_POSES[pose]
    engine_rows = (swap(rows[0]), swap(rows[2]), swap(rows[1]))
    anchor = (1.5, 2.0, 0.25)
    p3d = fork.P3D()
    lod = fork.LOD()
    lod.resolution = 1.0
    p3d.lods.append(lod)
    lod.add_proxy("\\kp\\target", 1, origin=anchor, rotation=rows, space="raw")
    fork.blender_to_dayz(p3d)
    want = fork.canonical_proxy_triangle(swap(anchor), engine_rows, 0.001,
                                         "engine")
    for got, expected in zip([p.coords for p in lod.points], want):
        assert close3(got, expected), pose
    frame = lod.get_proxies(strict=True)[0]["engine_frame"]
    for got, expected in zip(frame, engine_rows):
        assert close3(got, expected), pose
    raw_twin = fork.canonical_proxy_triangle(swap(anchor), engine_rows, 0.001,
                                             "raw")
    assert not all(close3(p.coords, q) for p, q in zip(lod.points, raw_twin))


def test_b2d_proxy_moves_like_any_face(fork):
    """A proxy triangle gets nothing special: its points are mapped and its
    vertex order kept, like every other face."""
    p3d = build_multilod_v2_p3d(fork)
    vis = p3d.lods[0]
    face = next(iter(vis.selections[PROXY].faces))
    order = [v.point_index for v in face.vertices]
    coords = [vis.points[i].coords for i in order]
    fork.blender_to_dayz(p3d)
    assert [v.point_index for v in face.vertices] == order
    for (x, y, z), i in zip(coords, order):
        assert vis.points[i].coords == (x, z, y)


def test_b2d_emits_no_warning(fork):
    """Not even for a model with a proxy."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fork.blender_to_dayz(build_multilod_v2_p3d(fork))
        fork.blender_to_dayz(build_chiral_f_p3d(fork))
    assert caught == []


# ---- the deprecated constant ------------------------------------------------

def test_blender_to_dayz_constant_deprecated_value_unchanged(fork):
    """Reading BLENDER_TO_DAYZ warns, at the caller's line, and still gives
    the det=+1 rotation it always gave - now ROT_X_NEG90."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = fork.BLENDER_TO_DAYZ
    assert len(caught) == 1
    assert caught[0].category is FutureWarning
    assert caught[0].filename == __file__
    assert "blender_to_dayz" in str(caught[0].message)
    assert "ROT_X_NEG90" in str(caught[0].message)
    assert value is fork.ROT_X_NEG90
    assert value == ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
    assert fork._det3(value) == 1.0
    assert fork._det3(fork._BLENDER_TO_DAYZ_AXES) == -1.0


def test_blender_to_dayz_constant_from_import_warns(fork):
    with pytest.warns(FutureWarning, match="MIRRORED"):
        from py3d import BLENDER_TO_DAYZ
    assert BLENDER_TO_DAYZ == fork.ROT_X_NEG90


def test_module_getattr_unknown_name_still_raises(fork):
    assert not hasattr(fork, "NO_SUCH_NAME")
    with pytest.raises(AttributeError, match="NO_SUCH_NAME"):
        fork.NO_SUCH_NAME
