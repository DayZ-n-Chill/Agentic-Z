#!/usr/bin/env python3

r"""Py3d-dayz - read and write Arma/DayZ .p3d files (MLOD).

A maintained fork of https://github.com/KoffeinFlummi/py3d (master 7acd58b,
MIT, unmaintained since 2018) by Felix "KoffeinFlummi" Wiegand, whose
copyright is preserved in LICENSE. The importable module is still `py3d`,
so `import py3d` keeps working; only the distribution name differs, because
`py3d` on PyPI belongs to an unrelated library.

What this fork adds on top of upstream's MLOD codec:

- Anti-corruption guards: paths that used to corrupt a .p3d silently or
  crash late now fail EARLY with an actionable message (selection weight
  validation, #Property# length limit, stale-binding detection).
- DayZ LOD constants and `LOD.kind()` / `P3D.get_lod()`. Note DayZ does NOT
  use the Arma-3-era e13 ids for FireGeo/ViewGeo: they are 7e15 / 6e15.
- Geometry helpers: `bbox`, `triangulate`, `set_selection`,
  `set_total_mass`, `set_memory_point`, and a proxy lifecycle
  (add / inspect / align / remove) with explicit raw<->engine frames.
- `blender_to_dayz()`: a model authored in Blender converted to DayZ's
  frame without mirroring it (measured in game; see its docstring).
- `P3D.validate()`, a model validator that reports `Finding`s, and a CLI:
  `python -m py3d info|validate|diff`.
- Recipe JSON (`to_dict` / `from_dict`) for inspection. See KNOWN-ISSUES:
  it is lossy and is NOT a safe persistence format yet.
- Format fidelity for UV sets: every `#UVSet#` beyond the first survives a
  read/write cycle (`Vertex.uv_sets`), and a LOD without faces gets the
  empty `#UVSet#` tag Object Builder writes (Memory, LandContact).
- Format fidelity for the editor's current selection: `#Selected#` is read
  into `LOD.selected` and written back with its payload intact, so a file
  written by Object Builder survives a read/write cycle byte for byte.

Write contract: byte-identical to upstream for valid canonical inputs, with
one deliberate exception - the empty `#UVSet#` tag in LODs without faces;
it raises where upstream would have corrupted the file or crashed later.

`IS_DAYZ_FORK = True` is provided so scripts can assert they imported this
library and not the unrelated `py3d` from PyPI.
"""


import collections
import io
import math
import os
import re
import struct
import tempfile
import warnings


__version__ = "1.10.1"
IS_DAYZ_FORK = True

_REQUIRED = object()


def _read_asciiz(f, encoding="utf-8"):
    pos = f.tell()

    bts = b""
    while b"\0" not in bts:
        chunk = f.read(1024)
        if not chunk:
            # Upstream (master 7acd58b) loops here forever: at EOF read()
            # keeps returning b"" and the process HANGS, with no traceback
            # and nothing the caller can catch. A truncated .p3d is the
            # normal way to hit this: a half-finished write, an incomplete
            # download, a bad sector.
            raise ValueError(
                "unterminated asciiz string starting at offset %d: reached "
                "EOF after %d bytes without a NUL terminator - the file is "
                "truncated or not a valid MLOD" % (pos, len(bts)))
        bts += chunk
    bts = bts[:bts.index(b"\0")]

    f.seek(pos + len(bts) + 1)

    return str(bts, encoding=encoding)



# ---------------------------------------------------------------------------
# Canonical DayZ LOD constants.
#
# Consolidated from the DayZ modelling notes and the p3d inspector
# (extract.py:32-46, build.py:80-96 - a separate tool, not in this
# repository), verified against real MLODs. Replaces the 4
# historical copies of the resolution -> LOD map, which each used a
# DIFFERENT absolute tolerance (+-1e11, +-5e13, +-1e13 and ad-hoc ranges).
# Here there is ONE relative tolerance.
#
# DayZ versus Arma 3: the legacy e13-family ids that circulate in Arma
# tooling (FireGeo/ViewGeo at 2e13/3e13/7e13) are NOT valid in DayZ. DayZ
# uses ViewGeometry=6e15 and FireGeometry=7e15. kind() returns None for
# those values and validate() emits WARN_LOD_KIND_UNKNOWN.
LOD_RESOLUTIONS = collections.OrderedDict([
    ("geometry",      1.0e13),
    ("memory",        1.0e15),
    ("landcontact",   2.0e15),
    ("roadway",       3.0e15),
    ("paths",         4.0e15),
    ("hitpoints",     5.0e15),
    ("view_geometry", 6.0e15),
    ("fire_geometry", 7.0e15),
])

#: |res - canon| <= LOD_RELATIVE_TOLERANCE * canon => ese kind.
LOD_RELATIVE_TOLERANCE = 0.05

#: Visual levels of detail (0.0, 1.0, 2.0, 4.0, 8.0, ...).
VISUAL_RESOLUTION_MAX = 1.0e3
#: ShadowVolume = 1e4 + sublevel (SV 0 -> 10000.0, SV 10 -> 10010.0).
SHADOWVOLUME_RESOLUTION_MIN = 1.0e4
SHADOWVOLUME_RESOLUTION_MAX = 2.0e4

#: The rotation by -90 degrees about X, (x,y,z) -> (x,z,-y), det=+1.
#: It is NOT a Blender -> DayZ conversion: Blender is right-handed and DayZ
#: left-handed, so any det=+1 map from one to the other MIRRORS the model
#: (measured in game 2026-10-01). For geometry authored in Blender call
#: blender_to_dayz(). This rotation is right where the mirror cancels out,
#: e.g. to undo a det=+1 DayZ -> Blender export such as (x,y,z) -> (x,-z,y).
#: Until 1.8.0 it was published as BLENDER_TO_DAYZ, which is now a
#: deprecated alias with the same value.
ROT_X_NEG90 = (
    (1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, -1.0, 0.0),
)

#: Blender -> DayZ coordinates, (x,y,z) -> (x,z,y), det=-1. Private on
#: purpose: P3D.transform() with this matrix reverses every face, which
#: leaves a Blender-authored model inside-out. blender_to_dayz() applies it
#: and then puts faces and normals into the MLOD convention.
_BLENDER_TO_DAYZ_AXES = (
    (1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0),
)


def __getattr__(name):
    # PEP 562 module attribute hook. BLENDER_TO_DAYZ keeps the value it
    # always had, so code that relied on it gets the same geometry as
    # before, and every read of it warns.
    if name == "BLENDER_TO_DAYZ":
        warnings.warn(
            "py3d.BLENDER_TO_DAYZ is deprecated: it is the det=+1 rotation "
            "(x,y,z)->(x,z,-y), and a model authored in Blender "
            "(right-handed) comes out MIRRORED in DayZ (left-handed) "
            "through it - measured in game 2026-10-01. For Blender-authored "
            "geometry call py3d.blender_to_dayz(p3d) instead of "
            "p3d.transform(...). The value is unchanged; to keep this exact "
            "rotation, e.g. to undo a det=+1 (x,-z,y) export, use "
            "py3d.ROT_X_NEG90.",
            FutureWarning, stacklevel=2)
        return ROT_X_NEG90
    raise AttributeError("module %r has no attribute %r" % (__name__, name))

#: Short aliases accepted by P3D.get_lod().
LOD_KIND_ALIASES = {
    "viewgeo": "view_geometry",
    "firegeo": "fire_geometry",
    "shadow": "shadowvolume",
}

_GEOMETRY_CLASS_KINDS = ("geometry", "view_geometry", "fire_geometry")


def classify_lod_resolution(resolution):
    """Canonical kind for an MLOD resolution, or None if unrecognised.

    Kinds: "visual", "shadowvolume" and the keys of LOD_RESOLUTIONS.
    """
    if 0.0 <= resolution < VISUAL_RESOLUTION_MAX:
        return "visual"
    if SHADOWVOLUME_RESOLUTION_MIN <= resolution < SHADOWVOLUME_RESOLUTION_MAX:
        return "shadowvolume"
    for name, canon in LOD_RESOLUTIONS.items():
        if abs(resolution - canon) <= LOD_RELATIVE_TOLERANCE * canon:
            return name
    return None


# ---------------------------------------------------------------------------
# MLOD proxy frame.
#
# 1:1 port (stdlib, no numpy) of a source-verified convention. The
# "proxy_frame.py:38-52" citations below name the script it was ported
# from, which is a separate tool and not part of this repository.
#   - derive_frame() -> proxy_frame.py:38-52 (ANGLE-SORT: the vertex with
#     the largest interior angle is the anchor; the middle one gives local
#     +Y, the smallest local +Z; x = y X z; z = x X y re-orthogonalised)
#   - canonical_triangle() -> proxy_frame.py:54-61 (anchor + scale*R[1] +
#     2*scale*R[2]: three DISTINCT angles => an unambiguous frame)
# Fuente original: Arma3ObjectBuilder utilities/proxy.py + mrcmodding
# gitbook entry on proxy coordinates.

PROXY_NAME_RE = re.compile(r"^proxy:(?P<path>.+)\.(?P<index>\d+)$",
                           re.IGNORECASE)
PROXY_ENGINE_CORRECTION = (
    (-1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0),
)
_IDENTITY_3 = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _v_norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _v_unit(v, fallback):
    n = _v_norm(v)
    if n > 1e-12:
        return (v[0] / n, v[1] / n, v[2] / n)
    return fallback


def _mat_vec(m, v):
    """Producto matriz 3x3 (row-major) x vector columna."""
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def _det3(m):
    """3x3 determinant, closed form."""
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _mat_mul3(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _validate_proxy_rotation(rotation):
    try:
        rows = tuple(tuple(float(value) for value in row) for row in rotation)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proxy rotation must be a finite 3x3 matrix")
    if len(rows) != 3 or any(len(row) != 3 for row in rows):
        raise ValueError("proxy rotation must be a finite 3x3 matrix")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("proxy rotation must be a finite 3x3 matrix")
    tolerance = 1e-6
    for i in range(3):
        for j in range(3):
            dot = sum(rows[k][i] * rows[k][j] for k in range(3))
            expected = 1.0 if i == j else 0.0
            if abs(dot - expected) > tolerance:
                raise ValueError(
                    "proxy rotation must be orthonormal with determinant +1"
                )
    if abs(_det3(rows) - 1.0) > tolerance:
        raise ValueError(
            "proxy rotation must be orthonormal with determinant +1"
        )
    return rows


def proxy_frame_to_engine(rotation):
    """Convert a validated raw MLOD proxy frame to its DayZ engine frame."""
    return _mat_mul3(
        PROXY_ENGINE_CORRECTION,
        _validate_proxy_rotation(rotation),
    )


def proxy_frame_from_engine(rotation):
    """Convert a validated DayZ engine proxy frame to its raw MLOD frame."""
    return _mat_mul3(
        PROXY_ENGINE_CORRECTION,
        _validate_proxy_rotation(rotation),
    )


def _validate_proxy_anchor(anchor):
    try:
        values = tuple(float(value) for value in anchor)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proxy anchor must contain three finite numbers")
    if len(values) != 3 or any(not math.isfinite(value) for value in values):
        raise ValueError("proxy anchor must contain three finite numbers")
    return values


def _validate_proxy_scale(scale):
    if isinstance(scale, bool):
        raise ValueError("proxy scale must be finite and greater than zero")
    try:
        value = float(scale)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proxy scale must be finite and greater than zero")
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("proxy scale must be finite and greater than zero")
    try:
        packed = struct.unpack("<f", struct.pack("<f", value))[0]
    except (OverflowError, struct.error):
        raise ValueError("proxy scale must fit float32")
    if packed == 0.0:
        raise ValueError("proxy scale is degenerate after float32 packing")
    return value


def _validate_proxy_path_index(path, index):
    if not isinstance(path, str):
        raise TypeError("proxy path must be a string")
    if not path:
        raise ValueError("proxy path must not be empty")
    if "\0" in path:
        raise ValueError("proxy path must not contain NUL")
    if any(ord(char) < 32 or 0x7F <= ord(char) <= 0x9F for char in path):
        raise ValueError("proxy path must not contain control characters")
    if path.lower().endswith(".p3d"):
        raise ValueError("proxy path must omit the .p3d suffix")
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("proxy index must be an int >= 1 (bool is invalid)")
    if index < 1:
        raise ValueError("proxy index must be >= 1")
    return path, index


def _validate_transform_matrix(matrix):
    """Numeric 3x3 shape, plus the "orthogonal times uniform scale" contract:
    mutually orthogonal columns with equal, non-zero norms, to a relative
    tolerance of 1e-6. Anything outside that contract raises ValueError
    WITHOUT mutating (normals would need M^-T). Returns tuples of float."""
    try:
        rows = [tuple(float(x) for x in row) for row in matrix]
    except (TypeError, ValueError):
        raise ValueError("transform(): matrix must be 3x3 numeric")
    if len(rows) != 3 or any(len(r) != 3 for r in rows):
        raise ValueError("transform(): matrix must be 3x3 numeric")
    m = tuple(rows)
    cols = [(m[0][j], m[1][j], m[2][j]) for j in range(3)]
    norms = [_v_norm(c) for c in cols]
    s = max(norms)
    tol = 1e-6
    if s <= 0.0 or any(abs(n - s) > tol * s for n in norms):
        raise ValueError(
            "transform(): matrix must be orthogonal times uniform scale")
    for a in range(3):
        for b in range(a + 1, 3):
            dot = (cols[a][0] * cols[b][0] + cols[a][1] * cols[b][1]
                   + cols[a][2] * cols[b][2])
            if abs(dot) > tol * norms[a] * norms[b]:
                raise ValueError(
                    "transform(): matrix must be orthogonal times "
                    "uniform scale")
    return m


def _proxy_angle(u, v):
    nu = _v_norm(u)
    nv = _v_norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    c = (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (nu * nv)
    return math.acos(max(-1.0, min(1.0, c)))


def derive_proxy_frame(tri):
    """Port of proxy_frame.derive_frame (proxy_frame.py:38-52).

    tri: a sequence of 3 (x, y, z) coordinates in raw MLOD space.
    Returns (anchor list, R as rows (x, y, z) tuple-of-tuples,
    ambiguous bool, angles_deg_desc list).
    """
    P = [tuple(float(c) for c in p) for p in tri]
    ang = [_proxy_angle(_v_sub(P[(i + 1) % 3], P[i]),
                        _v_sub(P[(i + 2) % 3], P[i])) for i in range(3)]
    order = sorted(range(3), key=lambda i: ang[i], reverse=True)
    center, vy, vz = P[order[0]], P[order[1]], P[order[2]]
    deg = sorted((math.degrees(a) for a in ang), reverse=True)
    ambiguous = abs(deg[1] - deg[2]) < 1.0
    y = _v_unit(_v_sub(vy, center), (0.0, 1.0, 0.0))
    z = _v_unit(_v_sub(vz, center), (0.0, 0.0, 1.0))
    x = _v_unit(_v_cross(y, z), (1.0, 0.0, 0.0))
    zc = _v_cross(x, y)
    n = _v_norm(zc) + 1e-12
    z = (zc[0] / n, zc[1] / n, zc[2] / n)
    return list(center), (x, y, z), bool(ambiguous), [float(d) for d in deg]


def canonical_proxy_triangle(anchor, rotation=None, scale=0.001, space="raw"):
    """Port of proxy_frame.canonical_triangle (proxy_frame.py:54-61).

    An unambiguous triangle at *anchor* whose derived frame equals
    *rotation* (identity if None). Order: [anchor, vert_y (+Y, the short
    leg), vert_z (+Z, the long leg, twice as long)].
    """
    if space not in ("raw", "engine"):
        raise ValueError("proxy space must be 'raw' or 'engine'")
    a = _validate_proxy_anchor(anchor)
    raw_rotation = _IDENTITY_3 if rotation is None \
        else _validate_proxy_rotation(rotation)
    if space == "engine":
        raw_rotation = proxy_frame_from_engine(raw_rotation)
    scale = _validate_proxy_scale(scale)
    vy = (a[0] + scale * raw_rotation[1][0],
          a[1] + scale * raw_rotation[1][1],
          a[2] + scale * raw_rotation[1][2])
    vz = (a[0] + 2.0 * scale * raw_rotation[2][0],
          a[1] + 2.0 * scale * raw_rotation[2][1],
          a[2] + 2.0 * scale * raw_rotation[2][2])
    triangle = [list(a), list(vy), list(vz)]
    try:
        packed = [
            tuple(struct.unpack("<f", struct.pack("<f", value))[0]
                  for value in point)
            for point in triangle
        ]
    except (OverflowError, struct.error):
        raise ValueError("proxy scale/anchor must fit float32")
    if _v_norm(_v_cross(_v_sub(packed[1], packed[0]),
                          _v_sub(packed[2], packed[0]))) == 0.0:
        raise ValueError("proxy scale is degenerate after float32 packing")
    return triangle


# ---------------------------------------------------------------------------
# Recipe JSON v1 - compatibility layer for the DayZ p3d inspector.
#
# The inspector's schema IS the specification here. These helpers are 1:1
# ports of its extract.py / build.py (without numpy). Line references of
# the form "extract.py:91-109" below point into those inspector scripts,
# which are a separate tool and are NOT part of this repository; they are
# kept because they record exactly which behaviour was reproduced.
# _recipe_lod_type reproduces the extractor's thresholds VERBATIM
# (extract.py:55-88). It is deliberately DIFFERENT from
# classify_lod_resolution(): this one classifies for the recipe's schema
# v1, while kind() is this library's canonical classifier.
#
# What schema v1 loses, exactly as extract/build lose it today:
#   - per-point mass does not travel in the recipe; from_dict reassigns it
#     with build's policy (override, then density heuristic) to geometry
#     AND fire_geometry, so ERR_MASS_ONLY_GEOMETRY is expected on the
#     rebuilt model - kept on purpose, for parity with the inspector;
#   - point and face flags become 0; selection weights become 1;
#   - resolution is snapped to the canonical value for the type
#     (build:108-112);
#   - the Memory LOD is rebuilt from recipe["memory_points"].

_RECIPE_WIREFRAME_TYPES = (
    "geometry", "fire_geometry", "view_geometry",
    "landcontact", "roadway", "paths", "hitpoints",
)
_RECIPE_BUILD_WIREFRAME_TYPES = _RECIPE_WIREFRAME_TYPES + ("shadow",)
#: build.py assigns mass to geometry AND fire_geometry (ported verbatim).
#: This is CONSERVED for parity even though #Mass# outside the Geometry
#: LOD is wrong for DayZ -> a model produced by from_dict raises
#: ERR_MASS_ONLY_GEOMETRY, and a test pins that. The fix belongs in the
#: inspector, not here.
_RECIPE_MASSED_TYPES = ("geometry", "fire_geometry")

# build.py:80-96 (verbatim)
_RECIPE_LOD_RESOLUTION = {
    "visual_0":       0.0,
    "visual_1":       1.0,
    "visual_2":       4.0,
    "visual_3":       8.0,
    "shadow":         1.0e4,
    "shadow_close":   1.0e4,
    "shadow_far":     1.1e4,
    "geometry":       1.0e13,
    "memory":         1.0e15,
    "landcontact":    2.0e15,
    "roadway":        3.0e15,
    "paths":          4.0e15,
    "hitpoints":      5.0e15,
    "view_geometry":  6.0e15,
    "fire_geometry":  7.0e15,
}

# build.py:40-60 (verbatim)
_RECIPE_DENSITY_KEYWORDS = [
    ("steel",   7800),
    ("iron",    7800),
    ("metal",   7800),
    ("alloy",   7500),
    ("copper",  8900),
    ("brass",   8500),
    ("aluminum", 2700),
    ("alum",    2700),
    ("wood",     600),
    ("timber",   600),
    ("plank",    600),
    ("plastic", 1200),
    ("rubber",  1100),
    ("glass",   2500),
    ("concrete", 2400),
    ("stone",   2600),
    ("fabric",   300),
    ("cloth",    300),
]
_RECIPE_DENSITY_DEFAULT = 2000


def _recipe_lod_type(resolution):
    """Classifier for schema v1 (ported verbatim from extract.py:55-88)."""
    if resolution < 0.5:
        return "visual_0"
    elif resolution < 2.0:
        return "visual_1"
    elif resolution < 6.0:
        return "visual_2"
    elif resolution < 10.0:
        return "visual_3"
    elif resolution < 1.5e4:
        return "shadow"
    elif abs(resolution - 1.0e13) < 1.0e11:
        return "geometry"
    elif abs(resolution - 1.0e15) < 5.0e13:
        return "memory"
    elif abs(resolution - 2.0e15) < 5.0e13:
        return "landcontact"
    elif abs(resolution - 3.0e15) < 5.0e13:
        return "roadway"
    elif abs(resolution - 4.0e15) < 5.0e13:
        return "paths"
    elif abs(resolution - 5.0e15) < 5.0e13:
        return "hitpoints"
    elif abs(resolution - 6.0e15) < 5.0e13:
        return "view_geometry"
    elif abs(resolution - 7.0e15) < 5.0e13:
        return "fire_geometry"
    else:
        return "unknown_%.0f" % resolution


def _recipe_classify_memory_point(selections):
    """Port of extract.py:91-109."""
    for sel in selections:
        s = sel.lower()
        if "axis" in s:
            return "axis"
        if s.startswith("pos ") or s == "pos center":
            return "center"
        if s.startswith("ce_") or s == "ce_center":
            return "center"
        if "actionpos" in s or "action_pos" in s:
            return "interaction"
        if "box_placing" in s:
            return "placing"
        if "port_" in s or "cable_" in s:
            return "port"
        if "proxy" in s:
            return "proxy"
    return "other"


def _recipe_visual_geometry(lod):
    """Port of extract.py:114-173 (vertex dedup plus the glTF V flip)."""
    vertex_map = {}
    positions = []
    normals = []
    uvs = []
    material_groups = collections.OrderedDict()

    for face in lod.faces:
        tex = face.texture if face.texture else ""
        mat = face.material if face.material else ""
        key = "%s|%s" % (tex, mat)
        if key not in material_groups:
            material_groups[key] = []

        face_indices = []
        for vertex in face.vertices:
            pt_idx = vertex.point_index
            norm_idx = vertex.normal_index
            u, v = vertex.uv if vertex.uv else (0.0, 0.0)
            vert_key = (pt_idx, norm_idx, round(u, 6), round(v, 6))
            if vert_key not in vertex_map:
                vertex_map[vert_key] = len(positions)
                positions.append(list(lod.points[pt_idx].coords))
                if norm_idx < len(lod.facenormals):
                    normals.append(list(lod.facenormals[norm_idx]))
                else:
                    normals.append([0.0, 1.0, 0.0])
                uvs.append([u, 1.0 - v])  # glTF V-flip
            face_indices.append(vertex_map[vert_key])

        if len(face_indices) == 3:
            material_groups[key].extend(face_indices)
        elif len(face_indices) == 4:
            material_groups[key].extend([
                face_indices[0], face_indices[1], face_indices[2],
                face_indices[0], face_indices[2], face_indices[3],
            ])
        elif len(face_indices) > 4:
            for i in range(1, len(face_indices) - 1):
                material_groups[key].extend(
                    [face_indices[0], face_indices[i], face_indices[i + 1]])

    return {
        "positions": positions,
        "normals": normals,
        "uvs": uvs,
        "material_groups": material_groups,
    }


def _recipe_wireframe(lod):
    """Port of extract.py:176-193, with SORTED edges so the output is stable.
    The extractor emits the set's iteration order instead, which is the
    same set of edges, just not in a repeatable order."""
    positions = [list(p.coords) for p in lod.points]
    edges = set()
    faces_data = []
    for face in lod.faces:
        verts = [v.point_index for v in face.vertices]
        faces_data.append(verts)
        for i in range(len(verts)):
            edge = tuple(sorted([verts[i], verts[(i + 1) % len(verts)]]))
            edges.add(edge)
    return {
        "positions": positions,
        "edges": [list(e) for e in sorted(edges)],
        "faces": faces_data,
    }


def _recipe_selections(lod):
    """Port of extract.py:196-238 (indices via id(), weight > 0)."""
    selections = collections.OrderedDict()
    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    fc_idx = {id(f): i for i, f in enumerate(lod.faces)}
    for name, sel in lod.selections.items():
        vertex_indices = []
        for pt, weight in sel.points.items():
            if weight > 0:
                idx = pt_idx.get(id(pt))
                if idx is not None:
                    vertex_indices.append(idx)
        face_indices = []
        for fc, weight in sel.faces.items():
            if weight > 0:
                idx = fc_idx.get(id(fc))
                if idx is not None:
                    face_indices.append(idx)
        selections[name] = {
            "vertices": vertex_indices,
            "faces": face_indices,
            "vertex_count": len(vertex_indices),
            "face_count": len(face_indices),
        }
    return selections


def _recipe_memory_data(lod):
    """Port of extract.py:252-308. Returns (memory_points, axes)."""
    memory_points = []
    axes = collections.OrderedDict()
    point_to_selections = {}
    selection_point_map = collections.OrderedDict()

    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    for name, sel in lod.selections.items():
        pts_in_sel = []
        for pt, weight in sel.points.items():
            if weight > 0:
                idx = pt_idx.get(id(pt))
                if idx is None:
                    continue
                pts_in_sel.append(idx)
                point_to_selections.setdefault(idx, []).append(name)
        selection_point_map[name] = pts_in_sel

    for i, point in enumerate(lod.points):
        sels = point_to_selections.get(i, [])
        memory_points.append({
            "index": i,
            "position": list(point.coords),
            "selections": sels,
            "category": _recipe_classify_memory_point(sels),
            "label": sels[0] if sels else "point_%d" % i,
        })

    for name, pts in selection_point_map.items():
        if len(pts) == 2:
            p1 = list(lod.points[pts[0]].coords)
            p2 = list(lod.points[pts[1]].coords)
            direction = [p2[j] - p1[j] for j in range(3)]
            length = math.sqrt(sum(d * d for d in direction))
            if length > 1e-9:
                direction = [d / length for d in direction]
            axes[name] = {
                "points": [p1, p2],
                "point_indices": pts,
                "direction": direction,
                "length": length,
            }
    return memory_points, axes


def _recipe_guess_density(recipe):
    """Port of build.py:63-74."""
    paths = []
    refs = recipe.get("referenced_paths", {})
    paths.extend(refs.get("textures", []))
    paths.extend(refs.get("materials", []))
    blob = " ".join(paths).lower()
    for kw, d in _RECIPE_DENSITY_KEYWORDS:
        if kw in blob:
            return d
    return _RECIPE_DENSITY_DEFAULT


def _recipe_dedup_normals(per_vertex_normals):
    """Port of build.py:117-128."""
    pool = []
    lookup = {}
    index_map = []
    for n in per_vertex_normals:
        key = (round(n[0], 6), round(n[1], 6), round(n[2], 6))
        if key not in lookup:
            lookup[key] = len(pool)
            pool.append((float(n[0]), float(n[1]), float(n[2])))
        index_map.append(lookup[key])
    return pool, index_map


def _recipe_face_normal(positions, indices):
    """Port of build.py:286-300 (cross product)."""
    try:
        p0, p1, p2 = (positions[indices[0]], positions[indices[1]],
                      positions[indices[2]])
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        n = _v_cross(v1, v2)
        L = _v_norm(n) or 1.0
        return (n[0] / L, n[1] / L, n[2] / L)
    except (IndexError, TypeError):
        return (0.0, 1.0, 0.0)


def _recipe_build_selections(lod, selections_dict):
    """Port of build.py:397-407. Weights collapse to 1; that loss is part of
    the schema, not a bug here."""
    for sel_name, sel_data in selections_dict.items():
        sel = Selection(lod.points, lod.faces)
        for vi in sel_data.get("vertices", []):
            if 0 <= vi < len(lod.points):
                sel.points[lod.points[vi]] = 1
        for fi in sel_data.get("faces", []):
            if 0 <= fi < len(lod.faces):
                sel.faces[lod.faces[fi]] = 1
        lod.selections[sel_name] = sel


def _recipe_build_visual(lod_dict):
    """Port of build.py:152-212."""
    lod = LOD()
    lod.resolution = _RECIPE_LOD_RESOLUTION.get(
        lod_dict["type"], lod_dict.get("resolution", 0.0))
    geo = lod_dict.get("geometry", {})
    positions = geo.get("positions", [])
    normals = geo.get("normals", [])
    uvs = geo.get("uvs", [])
    material_groups = geo.get("material_groups", {})

    for pos in positions:
        pt = Point()
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        lod.points.append(pt)

    pool, normal_idx_map = _recipe_dedup_normals(normals)
    lod.facenormals = pool

    for key, indices in material_groups.items():
        if "|" in key:
            tex, mat = key.split("|", 1)
        else:
            tex, mat = key, ""
        for i in range(0, len(indices) - 2, 3):
            face = Face(lod.points, lod.facenormals)
            face.flags = 0
            face.texture = tex
            face.material = mat
            for vi in (indices[i], indices[i + 1], indices[i + 2]):
                vx = Vertex(lod.points, lod.facenormals)
                vx.point_index = vi
                vx.normal_index = (normal_idx_map[vi]
                                   if vi < len(normal_idx_map) else 0)
                if vi < len(uvs):
                    u, v = uvs[vi]
                    vx.uv = (float(u), 1.0 - float(v))  # des-flip glTF
                else:
                    vx.uv = (0.0, 0.0)
                face.vertices.append(vx)
            lod.faces.append(face)

    _recipe_build_selections(lod, lod_dict.get("selections", {}))
    for k, v in lod_dict.get("properties", {}).items():
        if not k.startswith("_"):
            lod.properties[str(k)] = str(v)
    return lod


def _recipe_assign_mass(lod, lod_dict, recipe):
    """Port of build.py:323-353 (override > meta > density heuristic)."""
    if not lod.points:
        return
    override = None
    if "_point_mass" in lod_dict.get("properties", {}):
        try:
            override = float(lod_dict["properties"]["_point_mass"])
        except (ValueError, TypeError):
            pass
    if override is None:
        meta_override = recipe.get("meta", {}).get("point_mass_default")
        if meta_override is not None:
            try:
                override = float(meta_override)
            except (ValueError, TypeError):
                pass
    if override is not None:
        per_point = override
    else:
        lo, hi, _center = lod.bbox()
        vol = max(1e-6, (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2]))
        per_point = max(0.1, vol * _recipe_guess_density(recipe)
                        / len(lod.points))
    for p in lod.points:
        p.mass = per_point


def _recipe_build_wireframe(lod_dict, lod_type, recipe):
    """Port of build.py:217-283.

    One deliberate divergence: build.py's n-gon path (303-320) leaves the
    normal_index of every later face out of step. That is a latent bug,
    unreachable from an extractor recipe because MLOD only ever emits
    triangles and quads. Here n-gons are triangulated with correct indices.
    """
    lod = LOD()
    lod.resolution = _RECIPE_LOD_RESOLUTION.get(
        lod_type, lod_dict.get("resolution", 0.0))
    wf = lod_dict.get("wireframe", {})
    positions = wf.get("positions", [])
    faces_data = wf.get("faces", [])

    for pos in positions:
        pt = Point()
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        lod.points.append(pt)

    def _append_face(indices, normal_index):
        face = Face(lod.points, lod.facenormals)
        face.flags = 0
        face.texture = ""
        face.material = ""
        for pi in indices:
            vx = Vertex(lod.points, lod.facenormals)
            vx.point_index = int(pi)
            vx.normal_index = normal_index
            vx.uv = (0.0, 0.0)
            face.vertices.append(vx)
        lod.faces.append(face)

    for face_indices in faces_data:
        if len(face_indices) < 3:
            continue
        if len(face_indices) <= 4:
            lod.facenormals.append(_recipe_face_normal(positions,
                                                       face_indices))
            _append_face(face_indices, len(lod.facenormals) - 1)
        else:
            for i in range(1, len(face_indices) - 1):
                tri = [face_indices[0], face_indices[i], face_indices[i + 1]]
                lod.facenormals.append(_recipe_face_normal(positions, tri))
                _append_face(tri, len(lod.facenormals) - 1)

    if lod_type in _RECIPE_MASSED_TYPES:
        _recipe_assign_mass(lod, lod_dict, recipe)

    _recipe_build_selections(lod, lod_dict.get("selections", {}))
    for k, v in lod_dict.get("properties", {}).items():
        if not k.startswith("_"):
            lod.properties[str(k)] = str(v)

    if lod_type == "geometry":
        if "autocenter" not in lod.properties:
            lod.properties["autocenter"] = "0"
        if "class" not in lod.properties:
            lod.properties["class"] = "house"
    return lod


def _recipe_build_memory(recipe):
    """Port of build.py:358-392."""
    memory_points = recipe.get("memory_points", [])
    if not memory_points:
        return None
    lod = LOD()
    lod.resolution = _RECIPE_LOD_RESOLUTION["memory"]
    sorted_pts = sorted(memory_points, key=lambda m: m.get("index", 0))
    point_objs = []
    for mp in sorted_pts:
        pt = Point()
        pos = mp["position"]
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        point_objs.append(pt)
        lod.points.append(pt)
    sel_name_to_points = collections.OrderedDict()
    for i, mp in enumerate(sorted_pts):
        for sel_name in mp.get("selections", []):
            sel_name_to_points.setdefault(sel_name, []).append(point_objs[i])
    for sel_name, pts in sel_name_to_points.items():
        sel = Selection(lod.points, lod.faces)
        for p in pts:
            sel.points[p] = 1
        lod.selections[sel_name] = sel
    return lod


# ---------------------------------------------------------------------------
# Parity with the audit script shipped alongside this library, pruned to
# the checks that survived review. "audit:104-171" below cites that
# script, in tools/audit_p3d.py.
#
# Checks ported, as a closed list: relative cross-product winding
# (audit:104-171), Component01 naming/coverage (174-208), autocenter
# (211-219), watertight (222-234), degenerate faces (237-253), Memory
# structure (256-307), axes against selections (310-330) and P:\ paths on
# faces (333-342). check_required_lods is NOT ported - it stays in the
# audit script with its normalised ids - and the absolute-centroid check
# is WITHDRAWN.
#
# Depuracion aplicada respecto al audit original:
#   - modern DayZ ids: the "collision" class is geometry, view_geometry
#     and fire_geometry; the audit's GeoPhys/2e13 slot was stale;
#   - autocenter is only required on the Geometry LOD - the audit also ran
#     it over FireGeo, left over from the GeoPhys-era loop;
#   - the reference visual LOD for winding is the FIRST in file order; the
#     audit used the last one, through an accidental overwrite;
#   - severities: CRITICAL -> ERROR, WARNING -> WARN. Informational NOTEs
#     are not ported, except P:\ paths and the low-confidence winding
#     branch, which is part of the ported check;
#   - component naming (1.9.0): the audit required 'Component01' and
#     flagged 'component01'; in game the case made no difference, so the
#     check now flags a missing component, on every collision LOD;
#   - component coverage (1.9.0): the audit compared 'Component01' alone
#     with the whole Geometry LOD; the check now reads the union of every
#     component selection, in any case, on Geometry, View and Fire;
#   - component coverage (1.10.0): a closed part left out of every
#     component, measured in game to collide with nothing, is an ERROR
#     (ERR_COMPONENT_COVERAGE); the rest stays a WARN.
#
# Codes added in 1.2.0 (this block):
#   ERR_WINDING_INVERTED, WARN_WINDING_MIXED, WARN_WINDING_LOWCONF,
#   ERR_COMPONENT_NAMING, WARN_COMPONENT_NAMING, WARN_COMPONENT_COVERAGE,
#   WARN_AUTOCENTER_MISSING, WARN_NOT_WATERTIGHT, WARN_DEGENERATE_FACES,
#   WARN_MEMORY_POS_CENTER, WARN_MEMORY_BOX_PLACING, ERR_MEMORY_AXIS_POINTS,
#   WARN_MEMORY_AXIS_SHORT, WARN_MEMORY_HAS_FACES,
#   ERR_AXIS_SELECTION_MISSING, WARN_AXIS_SELECTION_EMPTY,
#   WARN_PDRIVE_PATH, WARN_LOD_KIND_UNKNOWN.
# Code added in 1.10.0: ERR_COMPONENT_COVERAGE.


def _pct_outward(lod):
    """Port of audit_p3d.check_winding_vs_visual.pct_outward (117-144)."""
    if len(lod.points) == 0 or len(lod.faces) == 0:
        return None
    n = len(lod.points)
    cx = sum(p.coords[0] for p in lod.points) / n
    cy = sum(p.coords[1] for p in lod.points) / n
    cz = sum(p.coords[2] for p in lod.points) / n
    out = 0
    tot = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            continue
        v = [vx.point.coords for vx in verts]
        e1 = _v_sub(v[1], v[0])
        e2 = _v_sub(v[2], v[0])
        nx, ny, nz = _v_cross(e1, e2)
        fx = sum(c[0] for c in v) / len(v)
        fy = sum(c[1] for c in v) / len(v)
        fz = sum(c[2] for c in v) / len(v)
        dot = nx * (fx - cx) + ny * (fy - cy) + nz * (fz - cz)
        tot += 1
        if dot > 0:
            out += 1
    if tot == 0:
        return None
    return 100.0 * out / tot


def _pct_normal_agreement(lod):
    r"""Signal B: the percentage of faces whose winding agrees with their own
    DECLARED normal.

    `cross(e1,e2) . declared_normal`, with BOTH vectors in the same space.
    That is why it does not depend on handedness: the left-handed (DayZ)
    versus right-handed (Three.js) confusion cancels in the product, and
    there is no sign to "correct" per engine.

    This is the signal `_pct_outward` cannot give. That one compares against
    the LOD's centroid, which (a) assumes convexity and (b) is unchanged by
    inverting the WHOLE model - which is why the Z-up to Y-up bug was
    invisible.

    Returns None if no face can be evaluated. Degenerate faces and faces
    with a null normal do NOT vote: a check that answers without data is
    worse than one that stays quiet.
    """
    if len(lod.faces) == 0:
        return None
    agree = 0
    tot = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            continue
        v = [vx.point.coords for vx in verts]
        cx, cy, cz = _v_cross(_v_sub(v[1], v[0]), _v_sub(v[2], v[0]))
        if cx == 0.0 and cy == 0.0 and cz == 0.0:
            continue
        normal = verts[0].normal
        if normal is None:
            continue
        nx, ny, nz = normal
        if nx == 0.0 and ny == 0.0 and nz == 0.0:
            continue
        dot = cx * nx + cy * ny + cz * nz
        if dot == 0.0:
            continue
        tot += 1
        if dot > 0:
            agree += 1
    if tot == 0:
        return None
    return 100.0 * agree / tot


def _pct_edge_coherence(lod):
    r"""Signal A: the percentage of shared edges traversed in opposite
    directions by their two faces.

    Purely topological: no centroids, no normals, no convexity assumption.
    On a well-built orientable surface the value is 100%. It also locates
    WHICH faces disagree, which a global average cannot.

    Only edges used by EXACTLY two faces are scored; open borders and
    non-manifold edges are _check_watertight's business. Returns None when
    there is no shared edge to evaluate.
    """
    if len(lod.faces) == 0:
        return None
    use = {}
    for face in lod.faces:
        verts = face.vertices
        n = len(verts)
        if n < 3:
            continue
        for i in range(n):
            a = verts[i].point_index
            b = verts[(i + 1) % n].point_index
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            use.setdefault(key, []).append(1 if a < b else -1)
    tot = 0
    good = 0
    for dirs in use.values():
        if len(dirs) != 2:
            continue
        tot += 1
        if dirs[0] != dirs[1]:
            good += 1
    if tot == 0:
        return None
    return 100.0 * good / tot


def _winding_steps(kind_label):
    """How to settle the winding of a LOD of this kind, normals untouched.
    Both winding findings give it; it leaves a LOD that reads right as it
    is."""
    if kind_label == "visual":
        return ("in each closed shell, turn the vertex order of the faces "
                "that disagree with their neighbours "
                "(WARN_WINDING_EDGE_INCOHERENT), then read its signed "
                "volume by winding - negative for a solid seen from "
                "outside, positive for a room seen from inside - and if it "
                "has the other sign, face.vertices.reverse() on every face "
                "of the shell")
    return ("in each convex component, face.vertices.reverse() on every "
            "face whose cross product points outward, against face "
            "centroid minus component centroid (inward expected)")


def _normals_step():
    """The normals step both winding findings close with, once the winding
    is settled: part by part, never a corner on its own sign. A normal
    smoothed across a sharp fold can point against a face wound right - a
    flat tetrahedron wound right, with one area-weighted normal per point,
    has 6 of its 12 corners against their faces - so negating each corner
    that points against its face, the step up to 1.10.0, turns right normals
    with no finding left to say so. How a face and a part read: README,
    'Winding', step 3."""
    return ("Then the normals, part by part, never a corner on its own "
            "sign: a normal smoothed across a sharp fold can point against "
            "a face wound right. In a part that reads cleanly (py3d README, "
            "'Winding', step 3), negate the normals of the faces that read "
            "against their winding (lod.facenormals[j] = (-x, -y, -z); an "
            "entry a kept corner also uses gets a negated copy) and keep the "
            "rest; leave any other part as it is, for inspection.")


def _check_winding_absolute(lod, lod_index, kind_label):
    r"""A LOD's ABSOLUTE winding, without comparing it to any other LOD.

    This closes the false negative that motivated the fork.
    `_check_winding_vs_visual` is RELATIVE to the Visual LOD, so inverting
    EVERY LOD left the model consistent with itself and `validate()`
    returned [] - precisely the state a Blender Z-up to Y-up export
    produces when the vertex order is not reversed.

    It sees that winding and normals disagree, not which of the two is
    wrong. A det=-1 map such as (x, z, y) that keeps the face order and
    maps the outward normals leaves the vertex order right - the MLOD
    order - and the normals the side to negate; reversing the faces
    instead turns the model inside-out and silences the check. A LOD
    whose faces and normals were turned together (both outward:
    inside-out, as transform(ROT_X_NEG90) alone leaves a Blender model)
    agrees 100% and passes.

    Additive: new finding codes, leaving `_check_winding_vs_visual`'s
    alone.
    """
    findings = []
    pct = _pct_normal_agreement(lod)
    if pct is None:
        findings.append(Finding(
            "WARN_WINDING_UNVERIFIABLE", "WARN", lod_index,
            "%s LOD: winding could not be verified - no face has both a "
            "non-degenerate winding and a non-degenerate declared normal."
            % kind_label))
    elif pct < 10.0:
        findings.append(Finding(
            "ERR_WINDING_VS_NORMALS", "ERROR", lod_index,
            "%s LOD: winding and declared normals disagree (only %.0f%% "
            "of faces agree with their first corner's normal). That says "
            "they disagree, not which one is wrong: in a DayZ MLOD both "
            "cross(v1-v0, v2-v0) and the stored normals point away from "
            "the side meant to be seen. Settle the winding first, normals "
            "untouched: %s; never a vertices[1]/[2] swap (a quad becomes "
            "a crossed face). %s Reversing every face on this finding "
            "alone has turned exports whose winding was right inside-out. "
            "More: py3d README, 'Winding'."
            % (kind_label, pct, _winding_steps(kind_label),
               _normals_step())))
    elif pct <= 90.0:
        findings.append(Finding(
            "WARN_WINDING_NORMAL_MISMATCH", "WARN", lod_index,
            "%s LOD: only %.0f%% of faces agree with their own declared "
            "normal - winding is not internally consistent."
            % (kind_label, pct)))
    edge = _pct_edge_coherence(lod)
    if edge is not None and edge < 100.0:
        findings.append(Finding(
            "WARN_WINDING_EDGE_INCOHERENT", "WARN", lod_index,
            "%s LOD: only %.0f%% of shared edges are traversed in opposite "
            "directions by their two faces (100%% expected on an orientable "
            "surface) - neighbouring faces disagree on which side is out."
            % (kind_label, edge)))
    return findings


def _check_winding_vs_visual(lod, lod_index, visual_lod, visual_index,
                             kind_label):
    """Pruned port of audit_p3d.check_winding_vs_visual (104-171).

    NOTE: this check is RELATIVE to the Visual LOD and leans on
    `_pct_outward`, which assumes convex geometry. It CANNOT detect a
    global inversion, nor tell a correct hollow box from a broken one. It
    is kept so the finding codes stay stable; the signal that does
    discriminate is `_check_winding_absolute`.

    It sees that the two LODs disagree on which way is out, not which of
    the two is wrong, and it files the finding on the collision LOD either
    way. A Visual LOD turned inside-out - faces and normals together, which
    `_check_winding_absolute` passes - raises it on the healthy collision
    LODs, and reversing those to match winds them outward. So the message
    gives the winding steps of both LODs, which leave a part that reads
    right as it is, instead of a fix for this one. It names the Visual LOD
    it compared against, the one of lowest resolution, by index:
    `P3D.get_lod("visual")` returns the first in file order, which need not
    be that one.
    """
    findings = []
    col = _pct_outward(lod)
    vis = _pct_outward(visual_lod)
    if col is None or vis is None:
        return findings
    col_uniform = col > 90 or col < 10
    vis_uniform = vis > 90 or vis < 10
    col_dom = "outward" if col >= 50 else "inward"
    vis_dom = "outward" if vis >= 50 else "inward"
    if col_uniform and vis_uniform and col_dom != vis_dom:
        findings.append(Finding(
            "ERR_WINDING_INVERTED", "ERROR", lod_index,
            "%s LOD and Visual LOD %d (resolution %g, the visual LOD of "
            "lowest resolution, which this check compares against) are "
            "wound opposite ways: %.0f%% and %.0f%% of their faces wind "
            "outward from their LOD's centroid, a test that assumes convex "
            "geometry. That says they disagree on which way is out, not "
            "which one is wrong: an inside-out Visual LOD raises this on "
            "the healthy collision LODs, and reversing those to match winds "
            "them outward, where raycasts pass through them. In a DayZ MLOD "
            "both cross(v1-v0, v2-v0) and the stored normals point away from "
            "the side meant to be seen. Settle the winding of both LODs "
            "first, normals untouched; these steps leave a part that reads "
            "right as it is. Visual LOD %d: %s. %s LOD: %s. Never a "
            "vertices[1]/[2] swap (a quad becomes a crossed face). %s A "
            "part these steps cannot read - not a closed shell, not a "
            "closed convex component - leaves this unresolved: check in "
            "game, or against a model that renders right, which side it is "
            "meant to show before turning it. Only when every part of both "
            "LODs reads right is there nothing to fix: a Visual LOD meant to "
            "be seen from inside reads positive and is right. More: py3d "
            "README, 'Winding'."
            % (kind_label, visual_index, visual_lod.resolution, col, vis,
               visual_index, _winding_steps("visual"), kind_label,
               _winding_steps(kind_label), _normals_step())))
    elif not col_uniform:
        findings.append(Finding(
            "WARN_WINDING_MIXED", "WARN", lod_index,
            "%s LOD winding is MIXED (%.0f%%-outward) - not internally "
            "consistent; raycasts will be unreliable."
            % (kind_label, col)))
    elif not vis_uniform:
        findings.append(Finding(
            "WARN_WINDING_LOWCONF", "WARN", lod_index,
            "Visual LOD winding is mixed (%.0f%%-outward) so the relative "
            "winding check for the %s LOD is low-confidence."
            % (vis, kind_label)))
    return findings


#: A collision component's selection: "Component" and a number, as Object
#: Builder's Find Components names them. Matched in any case: in game the
#: case made no difference (see _check_component_naming). Use fullmatch():
#: with match() and a "$" a trailing newline would pass.
_COMPONENT_NAME_RE = re.compile(r"component\d+", re.IGNORECASE)


def _proxy_triangle_faces(lod):
    """ids of the faces that are MLOD proxy triangles: a selection named
    'proxy:<path>.<index>' that holds exactly 1 triangular face and, as its
    3 points, that triangle's 3 corners. A selection under a proxy name
    with any other shape is not a proxy, and its faces stay collision
    geometry. Normals and editing exclusivity are not required here (the
    library's strict proxy check, _resolve_proxy_anatomy, rejects real
    proxy triangles for those)."""
    out = set()
    for name, sel in lod.selections.items():
        if not PROXY_NAME_RE.match(name):
            continue
        if len(sel.points) != 3 or len(sel.faces) != 1:
            continue
        face = next(iter(sel.faces))
        if len(face.vertices) != 3:
            continue
        try:
            corners = {id(vx.point) for vx in face.vertices}
        except (IndexError, TypeError):
            continue
        if len(corners) == 3 and corners == set(map(id, sel.points)):
            out.add(id(face))
    return out


def _check_component_naming(lod, lod_index, kind_label):
    """A collision LOD (Geometry, View or Fire) with faces of its own and
    no component selection -> ERR_COMPONENT_NAMING.

    Measured in game (DayZDiag 1.29.163709, 2026-10-02; dayz-p3d-audit
    killer #2): a 2 m box whose Geometry, View and Fire LODs had no
    component took no ray in geom, view or fire, missed the physics ray
    and let the player walk through, packed unbinarized and binarized,
    and no log line said so. A LOD without a component while the other
    collision LODs have one was not measured; each LOD is checked on its
    own.

    The case of the name is not checked. On the same run 'component01'
    collided exactly like 'Component01' (rays, physics ray, walk), and
    binarize writes both as 'component01'. Up to 1.8.0 this check, a port
    of audit_p3d.check_component_naming, ran on the Geometry LOD alone
    and raised this ERROR on 'component01': a false positive.

    The ERROR needs no selection whose name starts with "component" (any
    case). WARN_COMPONENT_NAMING: there are such selections, but none is
    "Component" and a number (e.g. only 'Component_01' or
    'components_panel'), a spelling never measured.

    Proxy triangles (_proxy_triangle_faces) do not count, so a LOD with no
    faces (a Geometry LOD that only carries mass) or only proxy triangles
    gets no finding: it has no collision geometry of its own.

    A component selection counts here even if it holds none of the faces;
    whether every face belongs to a component is _check_component_coverage's
    question (ERR_COMPONENT_COVERAGE, WARN_COMPONENT_COVERAGE).
    """
    proxy_faces = _proxy_triangle_faces(lod)
    own = sum(1 for fa in lod.faces if id(fa) not in proxy_faces)
    if own == 0:
        return []
    found = [s for s in lod.selections if s.lower().startswith("component")]
    if not found:
        return [Finding(
            "ERR_COMPONENT_NAMING", "ERROR", lod_index,
            "%s LOD: %d face(s) and no ComponentNN selection. In game a "
            "box with no component in any of its collision LODs lost its "
            "collision silently: no ray hit it, the player walked through, "
            "and no log line said so (one LOD without a component while "
            "the others have one was not measured). Select each closed, "
            "convex part as its own Component01, Component02, ... (the "
            "case does not matter: component01 collides like Component01)."
            % (kind_label, own))]
    if not any(_COMPONENT_NAME_RE.fullmatch(s) for s in found):
        return [Finding(
            "WARN_COMPONENT_NAMING", "WARN", lod_index,
            "%s LOD: component selection %r is not 'Component' and a "
            "number; that spelling was never measured in game "
            "(Component01 and component01 both collide). Rename it to "
            "ComponentNN." % (kind_label, found[0]))]
    return []


def _corner(point):
    """A corner's position as an MLOD stores it (three float32), so a model
    reads the same in memory and once written: two corners that only
    float32 rounding makes equal are one position here too. Coordinates a
    float32 cannot hold are kept as they are."""
    try:
        return struct.unpack("<3f", struct.pack("<3f", *point.coords))
    except (OverflowError, struct.error):
        return tuple(point.coords)


def _face_pieces(faces):
    """*faces* grouped into pieces, in file order: two faces are in the
    same piece when they share a corner position (_corner). Positions, not
    points: a mesh whose coincident corners were never merged is still one
    piece, and a part whose corners touch another part's joins that
    part."""
    parent = {}

    def root(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for fa in faces:
        keys = [_corner(vx.point) for vx in fa.vertices]
        if not keys:
            continue
        first = root(keys[0])
        for key in keys[1:]:
            other = root(key)
            if other != first:
                parent[other] = first
    pieces = {}
    for fa in faces:
        if fa.vertices:
            key = root(_corner(fa.vertices[0].point))
        else:
            key = ("face", id(fa))
        pieces.setdefault(key, []).append(fa)
    return list(pieces.values())


#: A closed piece is a solid only when it is thicker than this many float32
#: steps at its distance from the model's origin: float32 rounding can lift
#: the corners of a flat double-sided sheet off its plane by about a step.
_SOLID_MIN_STEPS = 16


def _piece_thickness(piece):
    """(thickness, reach) of a closed piece of faces of 3+ corners: twice
    its volume over its area (a slab's thickness), and its largest
    coordinate, at least 1 m. The volume is summed with math.fsum from
    corners (_corner) taken relative to the piece's first corner, so the
    sum cancels little far from the origin: an exactly flat sheet gives 0,
    or a residue far below _SOLID_MIN_STEPS, wherever it lies. The
    thickness is None for a piece without area."""
    origin = _corner(piece[0].vertices[0].point)
    six_volume = []
    area = []
    reach = 1.0
    for fa in piece:
        corners = [_corner(vx.point) for vx in fa.vertices]
        reach = max([reach] + [abs(x) for p in corners for x in p])
        c = [_v_sub(p, origin) for p in corners]
        for j in range(1, len(c) - 1):
            n = _v_cross(c[j], c[j + 1])
            six_volume.append(c[0][0] * n[0] + c[0][1] * n[1]
                              + c[0][2] * n[2])
            area.append(_v_norm(_v_cross(_v_sub(c[j], c[0]),
                                         _v_sub(c[j + 1], c[0]))) / 2.0)
    area = math.fsum(area)
    if not area > 0.0:
        return None, reach
    return abs(math.fsum(six_volume)) / (3.0 * area), reach


def _is_closed_solid(piece):
    """True when *piece* is closed, consistently wound and encloses a
    volume: by corner position (_corner), each of its edges is used by
    exactly two of its faces, once in each direction, and the piece is
    thicker (_piece_thickness) than _SOLID_MIN_STEPS float32 steps at its
    distance from the origin, at least 1 m; so a flat double-sided sheet
    is not a solid, wherever it lies. The cutoff errs toward the WARN: a
    real part thinner than it (a 0.3 mm slab 200 m from the origin) is not
    counted as a solid either. Whether the winding runs inward or outward
    is not read."""
    used = collections.Counter()
    for fa in piece:
        keys = [_corner(vx.point) for vx in fa.vertices]
        if len(keys) < 3:
            return False
        for j, a in enumerate(keys):
            b = keys[(j + 1) % len(keys)]
            if a == b:
                return False
            used[(a, b)] += 1
    if any(n != 1 or used[(b, a)] != 1 for (a, b), n in list(used.items())):
        return False
    thickness, reach = _piece_thickness(piece)
    if thickness is None:
        return False
    return thickness > _SOLID_MIN_STEPS * 2.0 ** -23 * reach


def _check_component_coverage(lod, lod_index, kind_label):
    """A collision LOD (Geometry, View or Fire) with faces in no component
    selection -> ERR_COMPONENT_COVERAGE for the closed parts left out
    whole, WARN_COMPONENT_COVERAGE for the rest.

    Coverage is the union of every selection named "Component" and a
    number, in any case (_COMPONENT_NAME_RE), read against the LOD's faces
    that are not proxy triangles (_proxy_triangle_faces: a whole box under
    a proxy name is collision geometry) and the points those faces use. A
    face or a point counts as covered when a component holds it with a
    nonzero weight (a zero weight is not written). Points that no face
    uses are not counted: they have no face to collide with.

    The faces are grouped into pieces that share a corner position
    (_face_pieces). A piece that is a closed solid (_is_closed_solid:
    every edge used twice, once each way, around a volume; a flat
    double-sided sheet is not one) with no face and no point in any
    component is a closed part left out whole; the ERROR counts those
    parts and their faces. Measured in game (DayZDiag 1.29.163709,
    2026-10-02; dayz-p3d-audit killer #8): beside a box in Component01, a
    second box in no component, in its Geometry, View and Fire LODs, took
    no ray in geom, view or fire and no physics ray, and the player walked
    through it; the same box as Component02 took every ray and stopped the
    player. A closed lever left out of the Geometry and Fire components of
    a door model took no Geometry, Fire or physics ray either, and a
    player walking into its knob was stopped by the block behind it (a
    walk along its arm was inconclusive), while in the View LOD, where it
    is one (non-convex) component, its knob answered. No log line named
    any of them. Each LOD is read on its own
    here, but those parts were left out of all three LODs (the box) and of
    Geometry and Fire (the lever): a part left out of one LOD alone was not
    measured, and the message says so.

    Every other face in no component raises the WARN: its piece is partly
    in a component (some of its faces, or the face's own points, are in
    one) or is not counted as a closed solid (an open sheet, a stray
    triangle, a flat double-sided sheet, or a closed piece too thin for
    the cutoff at its distance from the origin). None of these was
    measured. So does a LOD whose faces are all in components
    while some of their points are in none (a component holding a face
    without its points, not measured either). One finding of each code
    per LOD at most; the WARN does not count the ERROR's faces and points.

    No finding for a LOD with no component selection, which is
    _check_component_naming's ERR_COMPONENT_NAMING, nor for one whose
    faces are all proxy triangles. That check accepts a component
    selection that holds no face, so a LOD whose component selections are
    all empty is read here like any other: its closed parts left out whole
    raise the ERROR (in game such a part collided with nothing with no
    component in its LOD, killer #2, and beside a covered one; an empty
    component selection itself was not measured). A selection spelled
    otherwise (e.g. 'Component_01', WARN_COMPONENT_NAMING) does not count
    as a component. Not checked here: that each component holds the
    points of its own faces (only that some component holds them), or
    that a component is closed and convex.

    Up to 1.9.0 every face in no component raised the WARN, whose message
    said that faces outside every component beside covered ones were not
    measured. Up to 1.8.0 this check, a port of
    audit_p3d.check_component_coverage, read the Geometry LOD only when it
    held a selection named exactly 'Component01' and compared that
    selection alone with the whole LOD: it fired whenever 'Component01'
    held fewer points or faces than the LOD, as on a healthy LOD with
    several components (the Pack's three door samples, two of them fully
    covered), never read a LOD without an exact 'Component01' (lowercase
    components included), counted proxy triangles and loose points as
    uncovered, and did not run on View or Fire.
    """
    names = [n for n in lod.selections if _COMPONENT_NAME_RE.fullmatch(n)]
    if not names:
        return []
    proxy_faces = _proxy_triangle_faces(lod)
    faces = [fa for fa in lod.faces if id(fa) not in proxy_faces]
    if not faces:
        return []
    points = {id(vx.point) for fa in faces for vx in fa.vertices}
    covered_faces = set()
    covered_points = set()
    for name in names:
        sel = lod.selections[name]
        covered_faces.update(id(fa) for fa, w in sel.faces.items() if w)
        covered_points.update(id(p) for p, w in sel.points.items() if w)
    findings = []
    outside = set()
    parts = 0
    if any(id(fa) not in covered_faces for fa in faces):
        for piece in _face_pieces(faces):
            if any(id(fa) in covered_faces for fa in piece):
                continue
            if any(id(vx.point) in covered_points
                   for fa in piece for vx in fa.vertices):
                continue
            if not _is_closed_solid(piece):
                continue
            parts += 1
            outside.update(id(fa) for fa in piece)
    if parts:
        findings.append(Finding(
            "ERR_COMPONENT_COVERAGE", "ERROR", lod_index,
            "%s LOD: %d of its %d face(s) (proxy triangles not counted) "
            "make up %d closed part(s) with no face and no point in any "
            "ComponentNN selection. In game two such parts took no ray in "
            "the LODs they were left out of and no physics ray, and no log "
            "line said so: a box left out of every component of the "
            "Geometry, View and Fire LODs beside a covered box, which the "
            "player walked through, and a lever left out of the Geometry "
            "and Fire LODs (a component in View, hit there), whose knob did "
            "not stop a player walking into it. A part left out of one LOD "
            "alone, or beside component selections that hold nothing, was "
            "not measured, nor was weapon fire. Select each closed, convex "
            "part as its own "
            "ComponentNN, the components together covering the LOD; never "
            "merge parts into one component to cover them (it would not be "
            "convex)."
            % (kind_label, len(outside), len(faces), parts)))
    rest = [fa for fa in faces if id(fa) not in outside]
    bare_faces = sum(1 for fa in rest if id(fa) not in covered_faces)
    bare_points = len({id(vx.point) for fa in rest for vx in fa.vertices}
                      - covered_points)
    besides = ("besides the closed part(s) of ERR_COMPONENT_COVERAGE, "
               if parts else "")
    if bare_faces:
        msg = ("%s LOD: %s%d of its %d face(s) (proxy triangles not "
               "counted) are in no ComponentNN selection"
               % (kind_label, besides, bare_faces, len(faces)))
        if bare_points:
            msg += (", nor are %d of the %d point(s) its faces use"
                    % (bare_points, len(points)))
        msg += (". Each lies in a part partly in a component, or in a piece "
                "that is open, wound inconsistently, flat, or too thin to "
                "count as solid at its distance from the origin; none of "
                "these was measured in game (closed parts left out whole are "
                "ERR_COMPONENT_COVERAGE). "
                "Select each closed, convex part as its own ComponentNN, "
                "the components together covering the LOD; never merge "
                "parts into one component to cover them (it would not be "
                "convex).")
    elif bare_points:
        msg = ("%s LOD: %severy face (proxy triangles not counted) is in a "
               "ComponentNN selection, but %d of the %d point(s) its faces "
               "use are in none. A component holding a face without its "
               "points was not measured in game; select each component "
               "over all of its part's points and faces."
               % (kind_label, besides, bare_points, len(points)))
    else:
        return findings
    findings.append(Finding("WARN_COMPONENT_COVERAGE", "WARN", lod_index,
                            msg))
    return findings


def _check_autocenter(lod, lod_index):
    """Port of audit_p3d.check_autocenter_prop (211-219), Geometry only."""
    if "autocenter" not in lod.properties:
        return [Finding(
            "WARN_AUTOCENTER_MISSING", "WARN", lod_index,
            "Missing 'autocenter=0' LOD property. For Inventory_Base items "
            "with autocenter=0 in config.cpp it must ALSO be in the LOD.")]
    return []


def _check_watertight(lod, lod_index):
    """Port of audit_p3d.check_watertight (222-234)."""
    edge_count = {}
    for face in lod.faces:
        pts = [id(v.point) for v in face.vertices]
        for j in range(len(pts)):
            edge = tuple(sorted([pts[j], pts[(j + 1) % len(pts)]]))
            edge_count[edge] = edge_count.get(edge, 0) + 1
    boundary = sum(1 for c in edge_count.values() if c == 1)
    if boundary > 0:
        return [Finding(
            "WARN_NOT_WATERTIGHT", "WARN", lod_index,
            "%d boundary edges - mesh not watertight (has holes)."
            % boundary)]
    return []


def _check_degenerate_faces(lod, lod_index):
    """Port of audit_p3d.check_degenerate_faces (237-253)."""
    degen = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            degen += 1
            continue
        v = [vx.point.coords for vx in verts]
        n = _v_cross(_v_sub(v[1], v[0]), _v_sub(v[2], v[0]))
        if _v_norm(n) < 1e-8:
            degen += 1
    if degen > 0:
        return [Finding(
            "WARN_DEGENERATE_FACES", "WARN", lod_index,
            "%d degenerate (zero-area) faces won't register collision."
            % degen)]
    return []


def _check_memory_structure(lod, lod_index):
    """Port of audit_p3d.check_memory_lod (256-307), without the NOTEs."""
    findings = []
    sels = list(lod.selections.keys())
    if "pos center" not in sels:
        findings.append(Finding(
            "WARN_MEMORY_POS_CENTER", "WARN", lod_index,
            "Missing 'pos center' memory point; engine auto-calculates "
            "bounding center (wrong for tall/asymmetric objects)."))
    has_min = "box_placing_min" in sels
    has_max = "box_placing_max" in sels
    if has_min != has_max:
        findings.append(Finding(
            "WARN_MEMORY_BOX_PLACING", "WARN", lod_index,
            "Only one of box_placing_min/max found; both are needed for "
            "hologram placement."))
    if "flag_mast_axis" in lod.selections:
        sel = lod.selections["flag_mast_axis"]
        if len(sel.points) != 2:
            findings.append(Finding(
                "ERR_MEMORY_AXIS_POINTS", "ERROR", lod_index,
                "flag_mast_axis has %d points, MUST have exactly 2 (start "
                "and end of the translation axis)." % len(sel.points)))
        else:
            pts = list(sel.points.keys())
            dy = abs(pts[0].coords[1] - pts[1].coords[1])
            if dy < 0.1:
                findings.append(Finding(
                    "WARN_MEMORY_AXIS_SHORT", "WARN", lod_index,
                    "flag_mast_axis points have only %.3fm Y separation - "
                    "animation travel may be too small." % dy))
    if len(lod.faces) > 0:
        findings.append(Finding(
            "WARN_MEMORY_HAS_FACES", "WARN", lod_index,
            "Memory LOD has %d faces - should have 0 (only single-vertex "
            "points belong here)." % len(lod.faces)))
    return findings


def _check_axis_selections(memory_lod, visual_lod, visual_index):
    """Port of audit_p3d.check_visual_lod (316-330): a *_axis in the Memory
    LOD requires a selection of the same name, without the suffix, holding
    vertices in the Visual LOD."""
    findings = []
    vis_sels = visual_lod.selections
    for ms in memory_lod.selections.keys():
        if not ms.endswith("_axis"):
            continue
        anim_name = ms[:-len("_axis")]
        if anim_name not in vis_sels:
            findings.append(Finding(
                "ERR_AXIS_SELECTION_MISSING", "ERROR", visual_index,
                "Memory LOD has %r axis but Visual LOD is missing the %r "
                "selection - animation will silently do nothing."
                % (ms, anim_name)))
        elif len(vis_sels[anim_name].points) == 0:
            findings.append(Finding(
                "WARN_AXIS_SELECTION_EMPTY", "WARN", visual_index,
                "Visual LOD selection %r has 0 vertices - nothing will "
                "animate." % anim_name))
    return findings


def _check_pdrive_faces(lod, lod_index):
    """Port of audit_p3d.check_visual_lod (333-342): P:\\ paths on faces."""
    count = 0
    for face in lod.faces:
        if face.texture and face.texture.upper().startswith("P:\\"):
            count += 1
        if face.material and face.material.upper().startswith("P:\\"):
            count += 1
    if count > 0:
        return [Finding(
            "WARN_PDRIVE_PATH", "WARN", lod_index,
            "%d face texture/material references use absolute P:\\ paths - "
            "they break on distribution (usually OK for MLOD source)."
            % count)]
    return []


def _lod_has_mass_tagg(lod):
    """True if the LOD will emit a #Mass# tag when written.

    Mirrors the audit script's pseudocode. Do NOT use the LOD.mass
    property as the predicate: with PARTIAL mass (a mix of 0.0 and None)
    sum() raises TypeError.
    """
    return any(p.mass is not None for p in lod.points)


def _check_mass_only_geometry(lod, lod_index):
    """A #Mass# tag outside the Geometry LOD -> ERROR.

    Observed in game on a custom quad bike: a stray #Mass# in a
    non-Geometry LOD - even with every value 0.0 - makes binarize and
    AddonBuilder bake THAT LOD's mass, producing an ODOL with
    CoM=(0,0,0) and zero inertia, so ECE_PLACE_ON_SURFACE spawns the
    object underground. Applies to EVERY kind != "geometry", including an
    unrecognised resolution (kind None).
    """
    if lod.kind() == "geometry":
        return []
    if not _lod_has_mass_tagg(lod):
        return []
    count = sum(1 for p in lod.points if p.mass is not None)
    return [Finding(
        "ERR_MASS_ONLY_GEOMETRY", "ERROR", lod_index,
        "LOD kind=%s res=%g carries a #Mass# tagg (%d point(s) with "
        "non-None mass) - #Mass# must live ONLY in the Geometry LOD. "
        "binarize bakes THIS LOD's mass -> CoM=(0,0,0), zero inertia, "
        "below-ground spawn. FIX: set point.mass = None (never 0.0); "
        "py3d emits #Mass# if ANY point.mass is not None."
        % (lod.kind() or "unknown", lod.resolution, count))]


class Finding:
    """One result from P3D.validate(). severity: "ERROR" | "WARN"."""

    def __init__(self, code, severity, lod, msg):
        self.code = code
        self.severity = severity
        self.lod = lod  # LOD index, or None when the finding is global
        self.msg = msg

    def __repr__(self):
        return "Finding(%r, %r, lod=%r, %r)" % (
            self.code, self.severity, self.lod, self.msg)


class Point:
    def __init__(self, f=None):
        self.coords = (0,0,0)
        self.flags = 0
        self.mass = None
        if f is not None:
            self.read(f)

    def read(self, f):
        self.coords = struct.unpack("fff", f.read(12))
        self.flags = struct.unpack("<L", f.read(4))[0]

    def write(self, f):
        f.write(struct.pack("fff", *self.coords))
        f.write(struct.pack("<L", self.flags))


class Vertex:
    def __init__(self, all_points, all_normals, f=None):
        self.all_points = all_points
        self.all_normals = all_normals
        self.point_index = None
        self.normal_index = None
        self.uv = (0, 0)
        # Additional UV sets keyed by set id (1, 2, ...). Set 0 is `uv`,
        # stored inline in the face record; the other sets only exist in the
        # LOD's #UVSet# tags and are re-emitted by LOD.write in id order.
        self.uv_sets = {}
        if f is not None:
            self.read(f)

    @property
    def point(self):
        return self.all_points[self.point_index]

    @point.setter
    def point(self, value):
        self.point_index = self.all_points.index(value)

    @property
    def normal(self):
        return self.all_normals[self.normal_index]

    @normal.setter
    def normal(self, value):
        self.normal_index = self.all_normals.index(value)

    def read(self, f):
        self.point_index = struct.unpack("<L", f.read(4))[0]
        self.normal_index = struct.unpack("<L", f.read(4))[0]
        self.uv = struct.unpack("ff", f.read(8))

    def write(self, f):
        f.write(struct.pack("<L", self.point_index))
        f.write(struct.pack("<L", self.normal_index))
        f.write(struct.pack("ff", *self.uv))


class Face:
    def __init__(self, all_points, all_normals, f=None):
        self.all_points = all_points
        self.all_normals = all_normals
        self.vertices = []
        self.flags = 0
        self.texture = ""
        self.material = ""
        if f is not None:
            self.read(f)

    def read(self, f):
        num_vertices = struct.unpack("<L", f.read(4))[0]
        assert num_vertices in (3,4)

        self.vertices = [Vertex(self.all_points, self.all_normals, f) for i in range(num_vertices)]

        if num_vertices == 3:
            f.seek(16, 1)

        self.flags = struct.unpack("<L", f.read(4))[0]
        self.texture = _read_asciiz(f)
        self.material = _read_asciiz(f)

    def write(self, f):
        f.write(struct.pack("<L", len(self.vertices)))
        for v in self.vertices:
            v.write(f)
        if len(self.vertices) == 3:
            f.write(b"\0" * 16)
        f.write(struct.pack("<L", self.flags))
        f.write(bytes(self.texture, encoding="utf-8") + b"\0")
        f.write(bytes(self.material, encoding="utf-8") + b"\0")


class Selection:
    def __init__(self, all_points=_REQUIRED, all_faces=_REQUIRED, f=None):
        if all_points is _REQUIRED or all_faces is _REQUIRED:
            # upstream's positional signature already made the no-arg
            # form a TypeError; the fork freezes that behaviour with an
            # actionable message instead of a bare signature error.
            raise TypeError(
                "Selection() requires the owning LOD's lists: "
                "Selection(lod.points, lod.faces). Prefer "
                "lod.new_selection(name), which binds and registers the "
                "selection correctly."
            )
        self.all_points = all_points
        self.all_faces = all_faces
        self.points = {}
        self.faces = {}
        if f is not None:
            self.read(f)

    @staticmethod
    def _normalize_weight(value, kind, name):
        """Validate/normalize a selection weight at write time.

        Accepted: int 0/1, float exactly 0.0/1.0 (coerced to int), float
        strictly between 0 and 1 (upstream fractional encoding). Anything
        else raised upstream as a cryptic late TypeError inside bytes() -
        here it is an early ValueError naming the selection.
        """
        label = "'%s'" % name if name is not None else "<unnamed>"
        if isinstance(value, float) and value in (0.0, 1.0):
            return int(value)
        if isinstance(value, int):  # bool is a valid int subclass here
            if value in (0, 1):
                return value
            raise ValueError(
                "selection %s: invalid %s weight %r - int weights must be "
                "0 or 1" % (label, kind, value))
        if isinstance(value, float):
            if 0.0 < value < 1.0:
                return value
            raise ValueError(
                "selection %s: invalid %s weight %r - float weights must "
                "be strictly between 0 and 1 (or exactly 0.0/1.0, coerced "
                "to int)" % (label, kind, value))
        raise ValueError(
            "selection %s: invalid %s weight %r - expected int 0/1 or "
            "float in (0, 1)" % (label, kind, value))

    def read(self, f):
        num_bytes = struct.unpack("<L", f.read(4))[0]

        data_points = f.read(len(self.all_points))
        data_faces = f.read(len(self.all_faces))

        self.points = {p: (lambda weight: weight if weight <= 1 else 1 - ((weight - 1) / 255))(data_points[i]) for i, p in enumerate(self.all_points) if data_points[i] > 0}
        self.faces = {fa: (lambda weight: weight if weight <= 1 else 1 - ((weight - 1) / 255))(data_faces[i]) for i, fa in enumerate(self.all_faces) if data_faces[i] > 0}

    def write(self, f, name=None):
        label = "'%s'" % name if name is not None else "<unnamed>"
        # validate weights up-front (does not mutate user dicts).
        points = {p: self._normalize_weight(w, "point", name)
                  for p, w in self.points.items()}
        faces = {fa: self._normalize_weight(w, "face", name)
                 for fa, w in self.faces.items()}

        # Keys must belong to the bound lists BY IDENTITY; otherwise
        # their weight would silently serialise as 0.
        point_ids = set(map(id, self.all_points))
        face_ids = set(map(id, self.all_faces))
        for p in points:
            if id(p) not in point_ids:
                raise RuntimeError(
                    "selection %s: foreign Point key not present (by "
                    "identity) in the bound all_points - its weight would "
                    "be silently dropped. Did it come from another LOD or "
                    "a rebuilt list?" % label)
        for fa in faces:
            if id(fa) not in face_ids:
                raise RuntimeError(
                    "selection %s: foreign Face key not present (by "
                    "identity) in the bound all_faces - its weight would "
                    "be silently dropped. Did it come from another LOD or "
                    "a rebuilt list?" % label)

        f.write(struct.pack("<L", len(self.all_points) + len(self.all_faces)))

        data_points = [(lambda weight: weight if weight in (1,0) else round((1 - weight) * 255) + 1)(points[p]) if p in points else 0 for p in self.all_points]
        f.write(bytes(data_points))

        data_faces = [(lambda weight: weight if weight in (1,0) else round((1 - weight) * 255) + 1)(faces[fa]) if fa in faces else 0 for fa in self.all_faces]
        f.write(bytes(data_faces))


class LOD:
    def __init__(self, f=None):
        self.version_major = 28
        self.version_minor = 256
        self.resolution = 1.0
        self.points = []
        self.facenormals = []
        self.faces = []
        self.sharp_edges = []
        # Ids of #UVSet# tags belonging to a LOD without faces (Memory,
        # LandContact). There are no face vertices to hang them on, so they
        # are kept here and written back as the bare 4-byte id. Set 0 is
        # always written and is not listed.
        self.faceless_uv_sets = []
        self.properties = collections.OrderedDict()
        self.selections = collections.OrderedDict()
        # The editor's current selection (`#Selected#`), or None when the
        # LOD carries no such tag. It has the same on-disk layout as a
        # named selection - one byte per point followed by one per face -
        # so it is the same type, kept apart because it is anonymous and
        # Object Builder writes it before the named ones. Its content is
        # editor state, not model data: binarize.exe discards it (measured,
        # see KNOWN-ISSUES), but Object Builder preserves it verbatim and a
        # BI-authored file may carry it or not.
        self.selected = None
        if f is not None:
            self.read(f)

    @property
    def mass(self):
        masses = [x.mass for x in self.points]
        if len([x for x in masses if x is not None]) == 0:
            return None

        return sum(masses)

    @property
    def num_vertices(self):
        return sum([len(x.vertices) for x in self.faces])

    def uv_set_ids(self):
        """Sorted ids of the UV sets write() emits for this LOD: always 0
        (the uv carried by the face vertices) plus every id found in
        `Vertex.uv_sets` and in `faceless_uv_sets`. Set 0 lives in
        `Vertex.uv`; any other id must be an integer in 1..2**32-1,
        otherwise ValueError.
        """
        ids = set(self.faceless_uv_sets)
        for fa in self.faces:
            for v in fa.vertices:
                ids.update(v.uv_sets)
        for uv_id in ids:
            if isinstance(uv_id, bool) or not isinstance(uv_id, int) \
                    or not 1 <= uv_id <= 0xFFFFFFFF:
                raise ValueError(
                    "Vertex.uv_sets: invalid UV set id %r (set 0 is "
                    "Vertex.uv; other ids must be integers in 1..2**32-1)"
                    % (uv_id,))
        return [0] + sorted(ids)

    def new_selection(self, name):
        """Helper (fork API): get-or-create a selection correctly
        bound to this LOD's point/face lists and registered under *name*.
        """
        existing = self.selections.get(name)
        if existing is not None:
            return existing
        sel = Selection(self.points, self.faces)
        self.selections[name] = sel
        return sel

    def faces_by_material(self, lower=True):
        """Dict of material -> [Face]. Keys are lower-cased by default, because
        DayZ stores them lower-case while tooling emits UPPER and
        MixedCase."""
        out = collections.OrderedDict()
        for fa in self.faces:
            key = fa.material.lower() if lower else fa.material
            out.setdefault(key, []).append(fa)
        return out

    def faces_for_material(self, name):
        """Faces whose material matches *name*, case-insensitively."""
        want = name.lower()
        return [fa for fa in self.faces if fa.material.lower() == want]

    def set_memory_point(self, name, coords):
        """Insert or update a memory point.

        What MLOD actually requires: a point in the LOD, plus a
        single-point selection carrying its name. Idempotent by name: if
        the selection exists, its first point moves to *coords* and the
        membership COLLAPSES to exactly one, pre-existing duplicates
        included; duplicate entries are never added. Points orphaned by a
        collapsed duplicate are NOT removed from lod.points, because
        removing points would reindex other faces and selections. They
        simply end up in no selection.
        """
        coords = tuple(coords)
        sel = self.selections.get(name)
        if sel is not None:
            members = [p for p in self.points if id(p) in set(map(id, sel.points))]
            if members:
                keep = members[0]
                keep.coords = coords
                sel.points = {keep: 1}
                sel.faces = {}
                return keep
        p = Point()
        p.coords = coords
        self.points.append(p)
        if sel is None:
            sel = Selection(self.points, self.faces)
            self.selections[name] = sel
        sel.points = {p: 1}
        sel.faces = {}
        return p

    def get_memory_points(self):
        """{name: coords} for every selection of exactly one point and no faces,
        which is the canonical shape of a memory point."""
        out = collections.OrderedDict()
        for name, sel in self.selections.items():
            if len(sel.points) == 1 and len(sel.faces) == 0:
                p = next(iter(sel.points))
                out[name] = p.coords
        return out

    def kind(self):
        """This LOD's canonical DayZ kind, or None if the resolution is not
        recognised - for example the legacy Arma 3 ids 2e13/3e13/7e13,
        which validate() reports as WARN_LOD_KIND_UNKNOWN."""
        return classify_lod_resolution(self.resolution)

    def bbox(self):
        """((minx,miny,minz), (maxx,maxy,maxz), centre).

        A LOD with no points raises ValueError: a silent (0,0,0) bounding
        box hides empty models.
        """
        if not self.points:
            raise ValueError("bbox(): LOD has no points")
        xs = [p.coords[0] for p in self.points]
        ys = [p.coords[1] for p in self.points]
        zs = [p.coords[2] for p in self.points]
        lo = (min(xs), min(ys), min(zs))
        hi = (max(xs), max(ys), max(zs))
        center = ((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0,
                  (lo[2] + hi[2]) / 2.0)
        return lo, hi, center

    def triangulate(self):
        """In-place fan triangulation of the quads (quad -> 2 triangles).

        Per-vertex UVs and normal_index are preserved, the membership of
        EVERY selection is remapped (a quad becomes its two triangles at
        the same weight), and lod.points / facenormals / sharp_edges are
        untouched, so point indices do not move. lod.faces is mutated in
        place, which keeps the selections' bindings valid. Returns the
        number of quads split.
        """
        quad_map = {}
        new_faces = []
        split = 0
        for fa in self.faces:
            if len(fa.vertices) != 4:
                new_faces.append(fa)
                continue
            v = fa.vertices
            tris = []
            for idxs in ((0, 1, 2), (0, 2, 3)):
                t = Face(self.points, self.facenormals)
                t.flags = fa.flags
                t.texture = fa.texture
                t.material = fa.material
                for i in idxs:
                    nv = Vertex(self.points, self.facenormals)
                    nv.point_index = v[i].point_index
                    nv.normal_index = v[i].normal_index
                    nv.uv = v[i].uv
                    nv.uv_sets = dict(v[i].uv_sets)
                    t.vertices.append(nv)
                tris.append(t)
            quad_map[id(fa)] = tris
            new_faces.extend(tris)
            split += 1
        if split == 0:
            return 0
        self.faces[:] = new_faces
        for sel in self.selections.values():
            if not sel.faces:
                continue
            remapped = {}
            for fa, w in sel.faces.items():
                for t in quad_map.get(id(fa), (fa,)):
                    remapped[t] = w
            sel.faces = remapped
        return split

    def make_double_sided(self):
        """Duplicate every face with reversed vertex order and a negated normal
        (twins), for VISUAL LODs: flags, foliage and cloth that must be
        visible from both sides without a two-sided shader.

        Only kind() == "visual"; any other LOD raises ValueError without
        touching anything, because a double-sided Geometry or collision
        LOD breaks the physics. Twins inherit flags, texture, material and
        uv (in reverse order), and the membership - at the same weight -
        of every selection that held the original face. Points and
        sharp_edges do not change; the normal pool only grows by newly
        negated entries, deduplicated on exact tuple equality. NOT
        idempotent: calling it twice quadruples the faces. The order that
        is guaranteed with triangulate() is make_double_sided() first,
        triangulate() second; the reverse is untested. Returns the number
        of faces added.
        """
        kind = self.kind()
        if kind != "visual":
            raise ValueError(
                "make_double_sided(): only visual LODs (kind()=%r)" % kind)
        pool_index = {}
        for idx, n in enumerate(self.facenormals):
            pool_index.setdefault(tuple(n), idx)
        neg_cache = {}

        def negated_index(old_index):
            if old_index in neg_cache:
                return neg_cache[old_index]
            n = self.facenormals[old_index]
            neg = (-n[0], -n[1], -n[2])
            idx = pool_index.get(neg)
            if idx is None:
                self.facenormals.append(neg)
                idx = len(self.facenormals) - 1
                pool_index[neg] = idx
            neg_cache[old_index] = idx
            return idx

        originals = list(self.faces)
        twins = {}
        for face in originals:
            twin = Face(self.points, self.facenormals)
            twin.flags = face.flags
            twin.texture = face.texture
            twin.material = face.material
            for v in reversed(face.vertices):
                tv = Vertex(self.points, self.facenormals)
                tv.point_index = v.point_index
                tv.normal_index = negated_index(v.normal_index)
                tv.uv = v.uv
                tv.uv_sets = dict(v.uv_sets)
                twin.vertices.append(tv)
            self.faces.append(twin)
            twins[id(face)] = twin
        for sel in self.selections.values():
            if not sel.faces:
                continue
            additions = {}
            for fa, w in sel.faces.items():
                tw = twins.get(id(fa))
                if tw is not None:
                    additions[tw] = w
            sel.faces.update(additions)
        return len(originals)

    def set_selection(self, name, face_idx=None, point_idx=None, weight=1):
        """Define the selection *name* by INDEX. Idempotent overwrite: it
        replaces the whole membership and never duplicates.

        An invalid weight raises ValueError, checked BEFORE anything is
        mutated. An out-of-range index raises IndexError with context.
        """
        Selection._normalize_weight(weight, "selection", name)
        face_idx = list(face_idx or ())
        point_idx = list(point_idx or ())
        for i in point_idx:
            if not 0 <= i < len(self.points):
                raise IndexError(
                    "set_selection(%r): point index %d out of range "
                    "(LOD has %d points)" % (name, i, len(self.points)))
        for i in face_idx:
            if not 0 <= i < len(self.faces):
                raise IndexError(
                    "set_selection(%r): face index %d out of range "
                    "(LOD has %d faces)" % (name, i, len(self.faces)))
        sel = self.new_selection(name)
        sel.points = {self.points[i]: weight for i in point_idx}
        sel.faces = {self.faces[i]: weight for i in face_idx}
        return sel

    def set_total_mass(self, kg):
        """Spread *kg* uniformly across THIS LOD's points. Call it on the
        Geometry LOD, which is where the engine reads #Mass#.

        A LOD with no points, or a negative kg, raises ValueError.
        """
        kg = float(kg)
        if kg < 0:
            raise ValueError("set_total_mass(): mass must be >= 0")
        if not self.points:
            raise ValueError("set_total_mass(): LOD has no points")
        per_point = kg / len(self.points)
        for p in self.points:
            p.mass = per_point
        return per_point

    def add_proxy(self, path, index=1, origin=(0.0, 0.0, 0.0),
                  rotation=None, scale=0.001, space="raw"):
        """Add a canonical MLOD proxy - the unambiguous triangle of
        proxy_frame.py:54-61 - as the selection 'proxy:<path>.<index %03d>'.

        *rotation*: rows (x, y, z), local to world, identity if None.
        Identity means the item shows upright in character space (worn).
        A duplicate name raises ValueError, rather than silently upserting
        geometry. Returns the name of the selection created.
        """
        path, index = _validate_proxy_path_index(path, index)
        tri = canonical_proxy_triangle(origin, rotation, scale, space)
        name = "proxy:%s.%03d" % (path, index)
        if PROXY_NAME_RE.match(name) is None:
            raise ValueError(
                "add_proxy: composed name does not match proxy contract"
            )
        if name in self.selections:
            raise ValueError(
                "add_proxy: selection %r already exists - remove it first "
                "or use a different index" % name)
        base = len(self.points)
        for c in tri:
            p = Point()
            p.coords = (float(c[0]), float(c[1]), float(c[2]))
            self.points.append(p)
        R = derive_proxy_frame(tri)[1]
        # geometric normal of the canonical triangle: y X z = local +x
        self.facenormals.append(tuple(float(c) for c in R[0]))
        ni = len(self.facenormals) - 1
        fa = Face(self.points, self.facenormals)
        fa.flags = 0
        fa.texture = ""
        fa.material = ""
        for i in range(3):
            vx = Vertex(self.points, self.facenormals)
            vx.point_index = base + i
            vx.normal_index = ni
            vx.uv = (0.0, 0.0)
            fa.vertices.append(vx)
        self.faces.append(fa)
        sel = self.new_selection(name)
        sel.points = {self.points[base + i]: 1 for i in range(3)}
        sel.faces = {fa: 1}
        return name

    def _resolve_proxy_anatomy(self, name, exclusive=False):
        match = PROXY_NAME_RE.match(name)
        if not match:
            raise ValueError(
                "proxy %r: name must match proxy:<path>.<index>" % name
            )
        selection = self.selections.get(name)
        if selection is None:
            raise ValueError("proxy %r: selection does not exist" % name)
        if selection.all_points is not self.points or \
                selection.all_faces is not self.faces:
            raise ValueError(
                "proxy %r: selection is not bound to the owning LOD" % name
            )
        if len(selection.points) != 3:
            raise ValueError(
                "proxy %r: selection must contain exactly 3 points" % name
            )
        if len(selection.faces) != 1:
            raise ValueError(
                "proxy %r: selection must contain exactly 1 face" % name
            )
        if any(weight != 1 for weight in selection.points.values()) or \
                any(weight != 1 for weight in selection.faces.values()):
            raise ValueError(
                "proxy %r: selection weights must all equal 1" % name
            )
        point_ids = set(map(id, self.points))
        if any(id(point) not in point_ids for point in selection.points):
            raise ValueError(
                "proxy %r: selection contains a foreign point" % name
            )
        for point in selection.points:
            if sum(point is candidate for candidate in self.points) != 1:
                raise ValueError(
                    "proxy %r: each selected point must occur exactly once "
                    "in the owning LOD" % name
                )
        face = next(iter(selection.faces))
        face_occurrences = sum(face is candidate for candidate in self.faces)
        if face_occurrences == 0:
            raise ValueError(
                "proxy %r: selection contains a foreign face" % name
            )
        if face_occurrences != 1:
            raise ValueError(
                "proxy %r: selected face must occur exactly once in the "
                "owning LOD" % name
            )
        if len(face.vertices) != 3:
            raise ValueError(
                "proxy %r: selected face must be triangular" % name
            )
        for vertex in face.vertices:
            point_index = vertex.point_index
            if isinstance(point_index, bool) or \
                    not isinstance(point_index, int) or \
                    not 0 <= point_index < len(self.points):
                raise ValueError(
                    "proxy %r: selected face has an invalid point index" % name
                )
        face_points = [
            self.points[vertex.point_index] for vertex in face.vertices
        ]
        selected_ids = set(map(id, selection.points))
        if len(set(map(id, face_points))) != 3 or \
                set(map(id, face_points)) != selected_ids:
            raise ValueError(
                "proxy %r: selected face must use exactly the selected points"
                % name
            )
        normal_indices = {vertex.normal_index for vertex in face.vertices}
        if len(normal_indices) != 1:
            raise ValueError(
                "proxy %r: selected face must use one normal" % name
            )
        normal_index = next(iter(normal_indices))
        if isinstance(normal_index, bool) or \
                not isinstance(normal_index, int) or \
                not 0 <= normal_index < len(self.facenormals):
            raise ValueError(
                "proxy %r: selected face has an invalid normal index" % name
            )
        try:
            coords = [
                tuple(float(value) for value in point.coords)
                for point in face_points
            ]
        except (TypeError, ValueError, OverflowError):
            raise ValueError(
                "proxy %r: selected points must have finite 3D coordinates"
                % name
            )
        if any(
            len(coords_value) != 3 or
            any(not math.isfinite(value) for value in coords_value)
            for coords_value in coords
        ):
            raise ValueError(
                "proxy %r: selected points must have finite 3D coordinates"
                % name
            )
        area = _v_norm(
            _v_cross(_v_sub(coords[1], coords[0]),
                     _v_sub(coords[2], coords[0]))
        )
        if area == 0.0:
            raise ValueError(
                "proxy %r: selected face must be non-degenerate" % name
            )
        anchor, raw_frame, ambiguous, angles = derive_proxy_frame(coords)
        try:
            normal = tuple(
                float(value) for value in self.facenormals[normal_index]
            )
        except (TypeError, ValueError, OverflowError):
            raise ValueError(
                "proxy %r: selected face normal must be a finite 3D vector"
                % name
            )
        if len(normal) != 3 or \
                any(not math.isfinite(value) for value in normal):
            raise ValueError(
                "proxy %r: selected face normal must be a finite 3D vector"
                % name
            )
        if _v_norm(_v_sub(normal, raw_frame[0])) > 1e-3:
            raise ValueError(
                "proxy %r: selected face normal does not match its frame"
                % name
            )
        angle_order = sorted(
            range(3),
            key=lambda index: _proxy_angle(
                _v_sub(coords[(index + 1) % 3], coords[index]),
                _v_sub(coords[(index + 2) % 3], coords[index]),
            ),
            reverse=True,
        )
        scale = _v_norm(
            _v_sub(coords[angle_order[1]], coords[angle_order[0]])
        )
        anatomy = {
            "match": match,
            "selection": selection,
            "points": tuple(face_points),
            "face": face,
            "normal_index": normal_index,
            "anchor": anchor,
            "raw_frame": raw_frame,
            "ambiguous": ambiguous,
            "angles_deg": angles,
            "scale": scale,
        }
        if not exclusive:
            return anatomy

        point_indices = {
            index for index, point in enumerate(self.points)
            if id(point) in selected_ids
        }
        for other_face in self.faces:
            if other_face is face:
                continue
            for vertex in other_face.vertices:
                point_index = vertex.point_index
                if isinstance(point_index, bool) or \
                        not isinstance(point_index, int) or \
                        not 0 <= point_index < len(self.points):
                    raise ValueError(
                        "proxy %r: another face has an invalid point index"
                        % name
                    )
                if point_index in point_indices:
                    raise ValueError(
                        "proxy %r: point is shared by another face" % name
                    )
                if vertex.normal_index == normal_index:
                    raise ValueError(
                        "proxy %r: normal is shared by another face" % name
                    )
        for other_name, other_selection in self.selections.items():
            if other_name == name:
                continue
            if other_selection is selection:
                raise ValueError(
                    "proxy %r: selection object is shared by name %r"
                    % (name, other_name)
                )
            if any(id(point) in selected_ids
                   for point in other_selection.points):
                raise ValueError(
                    "proxy %r: point is shared by selection %r"
                    % (name, other_name)
                )
            if any(other_face is face for other_face in other_selection.faces):
                raise ValueError(
                    "proxy %r: face is shared by selection %r"
                    % (name, other_name)
                )
        for edge in self.sharp_edges:
            try:
                first, second = edge
            except (TypeError, ValueError):
                raise ValueError(
                    "proxy %r: LOD contains a malformed sharp edge" % name
                )
            if any(
                isinstance(index, bool) or not isinstance(index, int) or
                not 0 <= index < len(self.points)
                for index in (first, second)
            ):
                raise ValueError(
                    "proxy %r: sharp edge has an invalid point index" % name
                )
            if first in point_indices or second in point_indices:
                raise ValueError(
                    "proxy %r: point is shared by a sharp edge" % name
                )
        anatomy["point_indices"] = point_indices
        return anatomy

    def align_proxy(self, name, origin, rotation=None, scale=0.001,
                    space="raw"):
        """Rewrite one exclusively owned canonical proxy transform in place.

        The three Point objects, selected Face, Selection and owning list
        objects retain their identities. The proxy's exclusive facenormal
        keeps its existing pool index.
        """
        triangle = canonical_proxy_triangle(origin, rotation, scale, space)
        anatomy = self._resolve_proxy_anatomy(name, exclusive=True)
        normal = derive_proxy_frame(triangle)[1][0]

        for point, coords in zip(anatomy["points"], triangle):
            point.coords = tuple(float(value) for value in coords)
        self.facenormals[anatomy["normal_index"]] = tuple(
            float(value) for value in normal
        )
        return name

    def remove_proxy(self, name):
        """Remove one exclusively owned canonical proxy without list rebinding.

        Exactly the proxy selection, triangular face and three selected points
        are removed. The normal pool is intentionally unchanged. Every
        surviving face vertex and sharp-edge point index is validated and
        remapped before the first mutation.
        """
        anatomy = self._resolve_proxy_anatomy(name, exclusive=True)
        remove_indices = anatomy["point_indices"]
        face = anatomy["face"]

        surviving_points = [
            point for index, point in enumerate(self.points)
            if index not in remove_indices
        ]
        surviving_faces = [
            candidate for candidate in self.faces if candidate is not face
        ]
        point_remap = {}
        next_index = 0
        for old_index in range(len(self.points)):
            if old_index not in remove_indices:
                point_remap[old_index] = next_index
                next_index += 1

        vertex_updates = []
        for surviving_face in surviving_faces:
            for vertex in surviving_face.vertices:
                old_index = vertex.point_index
                if old_index not in point_remap:
                    raise ValueError(
                        "proxy %r: surviving face has an invalid point index"
                        % name
                    )
                vertex_updates.append((vertex, point_remap[old_index]))

        sharp_edge_updates = []
        for first, second in self.sharp_edges:
            if first not in point_remap or second not in point_remap:
                raise ValueError(
                    "proxy %r: surviving sharp edge has an invalid point index"
                    % name
                )
            sharp_edge_updates.append(
                (point_remap[first], point_remap[second])
            )

        self.points[:] = surviving_points
        self.faces[:] = surviving_faces
        for vertex, point_index in vertex_updates:
            vertex.point_index = point_index
        self.sharp_edges[:] = sharp_edge_updates
        del self.selections[name]
        return name

    def get_proxies(self, strict=False):
        """This LOD's proxies, each with the frame derived by ANGLE-SORT
        (proxy_frame.py:38-52).

        Each entry: {name, path, index, anchor, frame (rows x,y,z),
        ambiguous, angles_deg}. ambiguous=True means the two smallest
        angles tie - a legacy isosceles triangle - so the derived
        orientation depends on the raw vertex order; re-emit it with
        add_proxy to pin it down. Only 'proxy:*' selections with exactly
        three points are listed.
        """
        out = []
        for name, sel in self.selections.items():
            m = PROXY_NAME_RE.match(name)
            if not m:
                continue
            if strict:
                anatomy = self._resolve_proxy_anatomy(name)
                anchor = anatomy["anchor"]
                R = anatomy["raw_frame"]
                ambiguous = anatomy["ambiguous"]
                deg = anatomy["angles_deg"]
                scale = anatomy["scale"]
            else:
                if len(sel.points) != 3:
                    continue
                ids = set(map(id, sel.points))
                coords = [p.coords for p in self.points if id(p) in ids]
                anchor, R, ambiguous, deg = derive_proxy_frame(coords)
                angle_order = sorted(
                    range(3),
                    key=lambda index: _proxy_angle(
                        _v_sub(coords[(index + 1) % 3], coords[index]),
                        _v_sub(coords[(index + 2) % 3], coords[index]),
                    ),
                    reverse=True,
                )
                scale = _v_norm(
                    _v_sub(coords[angle_order[1]],
                           coords[angle_order[0]])
                )
            raw_frame = [list(row) for row in R]
            out.append({
                "name": name,
                "path": m.group("path"),
                "index": int(m.group("index")),
                "anchor": anchor,
                "frame": raw_frame,
                "raw_frame": [row[:] for row in raw_frame],
                "engine_frame": [
                    list(row) for row in proxy_frame_to_engine(R)
                ],
                "scale": scale,
                "ambiguous": ambiguous,
                "angles_deg": deg,
            })
        return out

    def validate_normals_budget(self, budget=32768, severity="WARN",
                                lod_index=None):
        """Per-LOD facenormals budget.

        WARN by default: the 32768 threshold comes from a crash observed
        in one of our own models, with no primary Bohemia source
        confirming it. Use severity="ERROR" only if your project treats it
        as a contract. The exact metric is len(lod.facenormals).
        """
        if severity not in ("WARN", "ERROR"):
            raise ValueError("severity must be 'WARN' or 'ERROR'")
        n = len(self.facenormals)
        if n <= budget:
            return []
        return [Finding(
            "WARN_NORMALS_BUDGET", severity, lod_index,
            "LOD has %d facenormals (budget %d; observed crash limit - "
            "local evidence, no confirmed primary source)" % (n, budget))]

    def _scan_findings(self, lod_index):
        """Non-raising scan of selections and properties."""
        findings = []
        point_ids = set(map(id, self.points))
        face_ids = set(map(id, self.faces))
        scanned = list(self.selections.items())
        if self.selected is not None:
            # The editor's current selection carries the same staleness and
            # weight hazards as a named one, so it is scanned with them.
            scanned.insert(0, ("#Selected#", self.selected))
        for name, sel in scanned:
            if sel.all_points is not self.points or \
                    sel.all_faces is not self.faces:
                findings.append(Finding(
                    "ERR_SELECTION_STALE", "ERROR", lod_index,
                    "selection %r: stale binding (all_points/all_faces are "
                    "not this LOD's current lists)" % name))
                continue
            foreign = [p for p in sel.points if id(p) not in point_ids] + \
                      [fa for fa in sel.faces if id(fa) not in face_ids]
            if foreign:
                findings.append(Finding(
                    "ERR_SELECTION_STALE", "ERROR", lod_index,
                    "selection %r: %d key(s) not present by identity in the "
                    "LOD lists (weight would be silently dropped)"
                    % (name, len(foreign))))
            for kind, mapping in (("point", sel.points), ("face", sel.faces)):
                for w in mapping.values():
                    try:
                        Selection._normalize_weight(w, kind, name)
                    except ValueError as e:
                        findings.append(Finding(
                            "ERR_WEIGHT_RANGE", "ERROR", lod_index, str(e)))
                        break
        for k, v in self.properties.items():
            kb = len(bytes(k, "utf-8"))
            vb = len(bytes(v, "utf-8"))
            if kb >= 63 or vb >= 63:
                if kb > 63 or vb > 63:
                    msg = ("property %r: key/value exceeds 63 utf-8 bytes "
                           "(write will raise - quirk 6 guard)" % k)
                else:
                    msg = ("property %r: key/value is exactly 63 utf-8 "
                           "bytes - fingerprint of silent truncation by "
                           "other tooling (quirk 6)" % k)
                findings.append(Finding(
                    "WARN_PROPERTY_TRUNCATION", "WARN", lod_index, msg))
        return findings

    def read(self, f):
        assert f.read(4) == b"P3DM"

        self.version_major = struct.unpack("<L", f.read(4))[0]
        self.version_minor = struct.unpack("<L", f.read(4))[0]

        num_points = struct.unpack("<L", f.read(4))[0]
        num_facenormals = struct.unpack("<L", f.read(4))[0]
        num_faces = struct.unpack("<L", f.read(4))[0]

        f.seek(4, 1)

        self.points.extend([Point(f) for i in range(num_points)])
        self.facenormals.extend([struct.unpack("fff", f.read(12)) for i in range(num_facenormals)])
        self.faces.extend([Face(self.points, self.facenormals, f) for i in range(num_faces)])

        assert f.read(4) == b"TAGG"

        while True:
            f.seek(1, 1)
            taggname = _read_asciiz(f)

            if taggname[0] != "#":
                self.selections[taggname] = Selection(self.points, self.faces, f)
                continue

            num_bytes = struct.unpack("<L", f.read(4))[0]
            data = f.read(num_bytes)

            if taggname == "#EndOfFile#":
                break

            if taggname == "#SharpEdges#": #untested
                self.sharp_edges.extend([struct.unpack("<LL", data[i*8:i*8+8]) for i in range(int(num_bytes / 8))])
                continue

            if taggname == "#Property#": #untested
                assert num_bytes == 128
                k, v = data[:64], data[64:]

                assert b"\0" in k and b"\0" in v
                k, v = k[:k.index(b"\0")], v[:v.index(b"\0")]

                self.properties[str(k, "utf-8")] = str(v, "utf-8")
                continue

            if taggname == "#Mass#":
                assert num_bytes == 4 * num_points
                for i in range(num_points):
                    self.points[i].mass = struct.unpack("f", data[i*4:i*4+4])[0]
                continue

            if taggname == "#UVSet#":
                self._read_uv_set(data)
                continue

            if taggname == "#Selected#":
                self._read_selected(num_bytes, data)
                continue

            #if taggname == "#Animation#": #not supported
            #    pass

        self.resolution = struct.unpack("f", f.read(4))[0]

    def _read_uv_set(self, data):
        """Store one #UVSet# payload: a 4-byte set id followed by one (u, v)
        pair per face vertex, in face order.

        Set 0 duplicates the uv already carried by every face vertex and is
        ignored, as upstream does. Any other set is attached to the face
        vertices as `Vertex.uv_sets[id]` so that write() can emit it again;
        in a LOD without faces there is nothing to attach it to, so the id
        alone is kept in `faceless_uv_sets`. A payload whose length does not
        match the faces, or a set id that appears twice, is a corrupt LOD and
        raises instead of being dropped in silence.
        """
        if len(data) < 4:
            raise ValueError(
                "#UVSet#: payload of %d bytes is shorter than the 4-byte "
                "set id" % len(data))
        uv_id = struct.unpack("<L", data[:4])[0]
        if uv_id == 0:
            return
        num_vertices = self.num_vertices
        if num_vertices == 0:
            # No face vertices to attach it to: keep the id alone.
            if uv_id in self.faceless_uv_sets:
                raise ValueError(
                    "#UVSet# id %d appears twice in the same LOD" % uv_id)
            if len(data) != 4:
                raise ValueError(
                    "#UVSet# id %d: payload is %d bytes, expected 4 in a LOD "
                    "without faces" % (uv_id, len(data)))
            self.faceless_uv_sets.append(uv_id)
            return
        expected = 4 + num_vertices * 8
        if len(data) != expected:
            raise ValueError(
                "#UVSet# id %d: payload is %d bytes, expected %d for %d face "
                "vertices" % (uv_id, len(data), expected, num_vertices))
        offset = 4
        for fa in self.faces:
            for v in fa.vertices:
                if uv_id in v.uv_sets:
                    raise ValueError(
                        "#UVSet# id %d appears twice in the same LOD" % uv_id)
                v.uv_sets[uv_id] = struct.unpack("ff", data[offset:offset + 8])
                offset += 8

    def _read_selected(self, num_bytes, data):
        """Store the `#Selected#` payload as an anonymous Selection.

        The layout is a named selection's: one byte per point followed by
        one per face, so it is parsed by the same code and the same weight
        mapping applies. Unlike `Selection.read`, the declared length is
        checked here - a payload that does not match the LOD's point and
        face counts is a corrupt tag, and reading it anyway would bind
        weights to the wrong elements. A second `#Selected#` in one LOD is
        equally corrupt: Object Builder writes at most one.
        """
        expected = len(self.points) + len(self.faces)
        if num_bytes != expected:
            raise ValueError(
                "#Selected#: payload is %d bytes, expected %d for %d "
                "point(s) and %d face(s)"
                % (num_bytes, expected, len(self.points), len(self.faces)))
        if self.selected is not None:
            raise ValueError("#Selected# appears twice in the same LOD")
        self.selected = Selection(
            self.points, self.faces,
            io.BytesIO(struct.pack("<L", num_bytes) + data))

    def write(self, f):
        f.write(b"P3DM")
        f.write(struct.pack("<L", self.version_major))
        f.write(struct.pack("<L", self.version_minor))

        f.write(struct.pack("<L", len(self.points)))
        f.write(struct.pack("<L", len(self.facenormals)))
        f.write(struct.pack("<L", len(self.faces)))

        f.write(b"\0" * 4)

        for p in self.points:
            p.write(f)
        for fn in self.facenormals:
            f.write(struct.pack("fff", *fn))
        for fa in self.faces:
            fa.write(f)

        f.write(b"TAGG")

        if len(self.sharp_edges) > 0: #untested
            f.write(b"\x01")
            f.write(b"#SharpEdges#\0")
            f.write(struct.pack("<L", len(self.sharp_edges) * 8))
            for se in self.sharp_edges:
                f.write(struct.pack("<LL", *se))

        # The editor's current selection goes after #SharpEdges# and before
        # the named selections - the slot Object Builder writes it in, and
        # the one BI-authored files carry it in. It is anonymous, so it can
        # never also live in self.selections under that name: two tags with
        # the same name would be written and only the first read back.
        if self.selected is not None:
            if "#Selected#" in self.selections:
                raise RuntimeError(
                    "both lod.selected and a named selection '#Selected#' "
                    "are set; the editor's current selection is anonymous - "
                    "keep it in lod.selected and remove the named one")
            if self.selected.all_points is not self.points or \
                    self.selected.all_faces is not self.faces:
                raise RuntimeError(
                    "lod.selected: stale binding - its all_points/all_faces "
                    "are not this LOD's current lists (did you replace "
                    "lod.points/lod.faces after reading the file?). Re-bind "
                    "it with Selection(lod.points, lod.faces), or set "
                    "lod.selected = None to drop the editor's selection.")
            f.write(b"\x01")
            f.write(b"#Selected#\0")
            self.selected.write(f, name="#Selected#")

        for k, v in self.selections.items():
            # A selection must stay bound to the LOD's CURRENT lists;
            # replacing them leaves the selection stale.
            if v.all_points is not self.points or v.all_faces is not self.faces:
                raise RuntimeError(
                    "selection %r: stale binding - its all_points/all_faces "
                    "are not this LOD's current lists (did you replace "
                    "lod.points/lod.faces after creating it?). Re-create it "
                    "with lod.new_selection(name) or "
                    "Selection(lod.points, lod.faces)." % k)
            f.write(b"\x01")
            f.write(bytes(k, "utf-8") + b"\0")
            v.write(f, name=k)

        for k, v in self.properties.items():
            key_bytes = bytes(k, "utf-8")
            value_bytes = bytes(v, "utf-8")
            # upstream struct.pack("64s64s") silently truncates
            # anything longer (and a 64-byte value loses its NUL
            # terminator, corrupting the read side). Quirk 6.
            if len(key_bytes) > 63 or len(value_bytes) > 63:
                raise ValueError(
                    "property %r: key and value must each encode to at "
                    "most 63 UTF-8 bytes (64-byte field incl. NUL "
                    "terminator); got key=%d, value=%d bytes"
                    % (k, len(key_bytes), len(value_bytes)))
            f.write(b"\x01")
            f.write(b"#Property#\0")
            f.write(struct.pack("<L", 128))
            f.write(struct.pack("64s64s", key_bytes, value_bytes))

        if self.mass is not None:
            f.write(b"\x01")
            f.write(b"#Mass#\0")
            f.write(struct.pack("<L", len(self.points) * 4))
            for p in self.points:
                f.write(struct.pack("f", p.mass))

        # One #UVSet# per set, in id order. Set 0 is the uv carried by the
        # face vertices; the others come from Vertex.uv_sets, and a vertex
        # that lacks a set present elsewhere in the LOD gets (0, 0), which is
        # what Object Builder assigns to new faces. Object Builder also
        # writes the tag for a LOD without faces (Memory, LandContact), with
        # the 4-byte set id as its whole payload. Upstream omits it there;
        # BI-authored MLOD files carry it, so it is emitted for parity.
        num_vertices = self.num_vertices
        for uv_id in self.uv_set_ids():
            f.write(b"\x01")
            f.write(b"#UVSet#\0")
            f.write(struct.pack("<L", num_vertices * 8 + 4))
            f.write(struct.pack("<L", uv_id))
            for fa in self.faces:
                for v in fa.vertices:
                    if uv_id == 0:
                        uv = v.uv
                    else:
                        uv = v.uv_sets.get(uv_id, (0.0, 0.0))
                    f.write(struct.pack("ff", *uv))

        f.write(b"\x01")
        f.write(b"#EndOfFile#\0")
        f.write(b"\0\0\0\0")

        f.write(struct.pack("f", self.resolution))


class P3D:
    def __init__(self, f=None):
        self.lods = []
        if f is not None:
            self.read(f)

    def read(self, f):
        assert f.read(4) == b"MLOD"

        version = struct.unpack("<L", f.read(4))[0]
        num_lods = struct.unpack("<L", f.read(4))[0]

        self.lods.extend([LOD(f) for i in range(num_lods)])

    def write(self, f):
        f.write(b"MLOD")
        f.write(struct.pack("<L", 257))
        f.write(struct.pack("<L", len(self.lods)))
        for l in self.lods:
            l.write(f)

    def _verify_against(self, reread):
        """The structural invariants the verify step checks."""
        if len(reread.lods) != len(self.lods):
            raise ValueError("verify: LOD count differs")
        for i, (a, b) in enumerate(zip(self.lods, reread.lods)):
            if (len(b.points), len(b.facenormals), len(b.faces)) != \
                    (len(a.points), len(a.facenormals), len(a.faces)):
                raise ValueError("verify: stream counts differ in LOD %d" % i)
            if list(b.selections.keys()) != list(a.selections.keys()):
                raise ValueError("verify: selections differ in LOD %d" % i)
            for name in a.selections:
                sa, sb = a.selections[name], b.selections[name]
                if (len(sb.points), len(sb.faces)) != (len(sa.points), len(sa.faces)):
                    raise ValueError(
                        "verify: selection %r membership differs in LOD %d"
                        % (name, i))
            if (b.selected is None) != (a.selected is None):
                raise ValueError(
                    "verify: #Selected# presence differs in LOD %d" % i)
            if a.selected is not None and \
                    (len(b.selected.points), len(b.selected.faces)) != \
                    (len(a.selected.points), len(a.selected.faces)):
                raise ValueError(
                    "verify: #Selected# membership differs in LOD %d" % i)
            if dict(b.properties) != dict(a.properties):
                raise ValueError("verify: properties differ in LOD %d" % i)
            if b.uv_set_ids() != a.uv_set_ids():
                raise ValueError("verify: UV sets differ in LOD %d" % i)
            am, bm = a.mass, b.mass
            if (am is None) != (bm is None) or \
                    (am is not None and abs(am - bm) > 1e-3):
                raise ValueError("verify: mass differs in LOD %d" % i)

    def save(self, path, verify=True, backup_dir=None):
        r"""Verified atomic write, on both Windows and POSIX.

        Always: a temporary file in the SAME directory -> flush +
        os.fsync(fd) -> close -> (verify) reopen, parse and check the
        structural invariants -> optional backup of the previous file ->
        atomic os.replace(). On POSIX only, the directory is fsynced after
        the replace; that is not portable on Windows, where the
        reopen-and-parse verification stands in for it - the file is
        checked by CONTENT, never by mtime.

        On any failure it raises: the original file is left byte-intact
        and the temporary file is removed.
        """
        path = os.fspath(path)
        dirpath = os.path.dirname(os.path.abspath(path)) or "."
        base = os.path.basename(path)
        fd, tmp_path = tempfile.mkstemp(prefix=base + ".tmp.", dir=dirpath)
        try:
            with os.fdopen(fd, "wb") as f:
                self.write(f)
                f.flush()
                os.fsync(f.fileno())
            if verify:
                with open(tmp_path, "rb") as f:
                    reread = P3D(f)
                self._verify_against(reread)
            if backup_dir and os.path.exists(path):
                import shutil
                import time
                os.makedirs(backup_dir, exist_ok=True)
                stamp = time.strftime("%Y%m%d_%H%M%S")
                shutil.copy2(path, os.path.join(
                    backup_dir, "%s.bak_%s" % (base, stamp)))
            os.replace(tmp_path, path)
            tmp_path = None
            if hasattr(os, "O_DIRECTORY"):  # POSIX
                dfd = os.open(dirpath, os.O_DIRECTORY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
        finally:
            if tmp_path is not None and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def get_lod(self, name):
        """The first LOD, in file order, whose kind() is *name*.

        Accepts the canonical kinds ("visual", "shadowvolume" and the keys
        of LOD_RESOLUTIONS) and the short aliases ("viewgeo", "firegeo",
        "shadow"). An unrecognised name raises ValueError; no match
        returns None.
        """
        key = LOD_KIND_ALIASES.get(name.lower(), name.lower())
        valid = set(LOD_RESOLUTIONS) | {"visual", "shadowvolume"}
        if key not in valid:
            raise ValueError(
                "get_lod: unknown LOD kind %r (valid: %s)"
                % (name, ", ".join(sorted(valid | set(LOD_KIND_ALIASES)))))
        for lod in self.lods:
            if lod.kind() == key:
                return lod
        return None

    def transform(self, matrix):
        """Transform the WHOLE model in place with a 3x3 matrix.

        Column-vector convention: new_i = sum_j matrix[i][j] * old_j. It
        moves a model within ONE frame. For geometry authored in Blender
        call blender_to_dayz() instead: Blender and DayZ have opposite
        handedness, so that conversion is a reflection AND a change of face
        convention, which this generic method knows nothing about.

        Contract: axis permutations, rotations, reflections and uniform
        scale - that is, an orthogonal matrix times a scalar. Anything
        else (shear, non-uniform scale, singular) raises ValueError
        WITHOUT mutating anything.

        Winding: det<0 (a reflection) flips the handedness, so
        face.vertices.reverse() runs on EVERY face of EVERY LOD, which
        realigns the cross-product geometric normal with the declared M*n.
        det>0 (a proper rotation) does not flip.

        Applies to Point.coords - the objects are mutated in place, so
        identity is preserved and selections stay intact - and to the
        lod.facenormals pool, renormalised to unit length, with degenerate
        entries kept as they are. It does NOT touch uv, sharp_edges,
        properties, selections, flags or mass. Memory points and proxies
        are just points and faces, so they transform along with everything
        else. Returns None.
        """
        m = _validate_transform_matrix(matrix)
        det = _det3(m)
        for lod in self.lods:
            for p in lod.points:
                p.coords = _mat_vec(m, p.coords)
            for i, n in enumerate(lod.facenormals):
                moved = _mat_vec(m, n)
                lod.facenormals[i] = _v_unit(moved, tuple(n))
            if det < 0:
                for face in lod.faces:
                    face.vertices.reverse()
        return None

    def to_dict(self, source_path=None):
        """The inspector's Recipe JSON, schema v1.

        1:1 port of p3d_inspector_extract.extract_recipe (extract.py:
        313-423): meta, lods (geometry, wireframe or note, by type),
        memory_points, axes, bounding_box, referenced_paths. JSON-safe.
        What the schema loses is documented in the _recipe_* block.
        """
        recipe = {
            "meta": {
                "source": os.path.basename(source_path) if source_path
                          else "",
                "source_path": source_path or "",
                "version": 1,
                "mode": "audit",
            },
            "lods": [],
            "memory_points": [],
            "axes": {},
            "bounding_box": None,
        }
        gmin = [float("inf")] * 3
        gmax = [float("-inf")] * 3

        for lod in self.lods:
            lod_type = _recipe_lod_type(lod.resolution)
            lod_info = {
                "type": lod_type,
                "resolution": lod.resolution,
                "num_points": len(lod.points),
                "num_faces": len(lod.faces),
                "selections": _recipe_selections(lod),
                "properties": dict(lod.properties),
            }
            if lod_type.startswith("visual"):
                geo = _recipe_visual_geometry(lod)
                lod_info["geometry"] = geo
                for pos in geo["positions"]:
                    for j in range(3):
                        gmin[j] = min(gmin[j], pos[j])
                        gmax[j] = max(gmax[j], pos[j])
            elif lod_type in _RECIPE_WIREFRAME_TYPES:
                lod_info["wireframe"] = _recipe_wireframe(lod)
                if lod_type in ("geometry", "fire_geometry",
                                "view_geometry"):
                    for pos in lod_info["wireframe"]["positions"]:
                        for j in range(3):
                            gmin[j] = min(gmin[j], pos[j])
                            gmax[j] = max(gmax[j], pos[j])
            elif lod_type == "shadow":
                lod_info["wireframe"] = _recipe_wireframe(lod)
            elif lod_type == "memory":
                memory_points, axes = _recipe_memory_data(lod)
                recipe["memory_points"] = memory_points
                recipe["axes"] = axes
                lod_info["note"] = "%d points, %d axes" % (
                    len(memory_points), len(axes))
            recipe["lods"].append(lod_info)

        if gmin[0] != float("inf"):
            recipe["bounding_box"] = {
                "min": gmin,
                "max": gmax,
                "size": [gmax[j] - gmin[j] for j in range(3)],
                "center": [(gmin[j] + gmax[j]) / 2 for j in range(3)],
            }

        all_textures = set()
        all_materials = set()
        for lod_info in recipe["lods"]:
            if "geometry" in lod_info:
                for key in lod_info["geometry"]["material_groups"]:
                    tex, mat = key.split("|", 1)
                    if tex:
                        all_textures.add(tex)
                    if mat:
                        all_materials.add(mat)
        recipe["referenced_paths"] = {
            "textures": sorted(all_textures),
            "materials": sorted(all_materials),
        }
        return recipe

    @classmethod
    def from_dict(cls, recipe):
        """Build a P3D from a Recipe v1.

        1:1 port of p3d_inspector_build.build_p3d (build.py:486-545)
        WITHOUT the winding auto-fix, which stays in the inspector's own
        script; this is construction only. Unknown LOD types are OMITTED,
        as build does, which logs them as a warning. The Memory LOD is
        ALWAYS rebuilt from recipe["memory_points"].
        """
        model = cls()
        for lod_dict in recipe.get("lods", []):
            lod_type = lod_dict.get("type", "unknown")
            if lod_type.startswith("visual"):
                model.lods.append(_recipe_build_visual(lod_dict))
            elif lod_type in _RECIPE_BUILD_WIREFRAME_TYPES:
                model.lods.append(
                    _recipe_build_wireframe(lod_dict, lod_type, recipe))
            # memory: reconstruido abajo; desconocidos: omitidos (scoped)
        mem = _recipe_build_memory(recipe)
        if mem is not None:
            model.lods.append(mem)
        return model

    def _scan_v12_findings(self):
        """The checks ported from the audit script; see the parity block."""
        findings = []
        visual = None
        visual_index = None
        # The reference is the visual LOD with the LOWEST resolution
        # (LOD0, the most detailed one), not whichever appears first in
        # the file: LOD order on disk is not normative, and it was
        # changing the verdict.
        for i, lod in enumerate(self.lods):
            if lod.kind() == "visual":
                if visual is None or lod.resolution < visual.resolution:
                    visual = lod
                    visual_index = i
        for i, lod in enumerate(self.lods):
            k = lod.kind()
            findings.extend(_check_mass_only_geometry(lod, i))
            if k is None:
                findings.append(Finding(
                    "WARN_LOD_KIND_UNKNOWN", "WARN", i,
                    "unrecognized LOD resolution %g - not a known DayZ id "
                    "(Arma-3-era e13 FireGeo/ViewGeo ids are NOT valid in "
                    "DayZ: use 7e15/6e15)" % lod.resolution))
                continue
            if k in _GEOMETRY_CLASS_KINDS:
                findings.extend(_check_component_naming(lod, i, k))
                findings.extend(_check_component_coverage(lod, i, k))
            if k == "geometry":
                findings.extend(_check_autocenter(lod, i))
            if k in _GEOMETRY_CLASS_KINDS:
                findings.extend(_check_watertight(lod, i))
                findings.extend(_check_degenerate_faces(lod, i))
                findings.extend(_check_winding_absolute(lod, i, k))
                if visual is not None and lod is not visual:
                    findings.extend(_check_winding_vs_visual(
                        lod, i, visual, visual_index, k))
            if k == "memory":
                findings.extend(_check_memory_structure(lod, i))
                if visual is not None:
                    findings.extend(_check_axis_selections(
                        lod, visual, visual_index))
            if k == "visual":
                findings.extend(_check_pdrive_faces(lod, i))
                # The visual LOD is checked too, otherwise a
                # visual-only model - a simple prop with no collision LOD -
                # would get no winding check at all.
                findings.extend(_check_winding_absolute(lod, i, k))
        return findings

    def validate(self, normals_budget=32768, normals_severity="WARN"):
        r"""The model validator, 1.2.0.

        Codes from 1.1.0: ERR_SELECTION_STALE, ERR_WEIGHT_RANGE,
        WARN_NORMALS_BUDGET, WARN_PROPERTY_TRUNCATION,
        ERR_UNREADABLE_ROUNDTRIP.
        Codes from 1.2.0 (pruned parity with the audit script; see the
        "_check_*" block): ERR_WINDING_INVERTED, WARN_WINDING_MIXED,
        WARN_WINDING_LOWCONF, ERR_COMPONENT_NAMING, WARN_COMPONENT_NAMING,
        WARN_COMPONENT_COVERAGE, WARN_AUTOCENTER_MISSING,
        WARN_NOT_WATERTIGHT, WARN_DEGENERATE_FACES, WARN_MEMORY_POS_CENTER,
        WARN_MEMORY_BOX_PLACING, ERR_MEMORY_AXIS_POINTS,
        WARN_MEMORY_AXIS_SHORT, WARN_MEMORY_HAS_FACES,
        ERR_AXIS_SELECTION_MISSING, WARN_AXIS_SELECTION_EMPTY,
        WARN_PDRIVE_PATH, WARN_LOD_KIND_UNKNOWN.
        Codes from 1.3.0: ERR_MASS_ONLY_GEOMETRY (a #Mass# tag in a
        non-Geometry LOD, which makes binarize bake CoM=(0,0,0)).
        Changed in 1.9.0: ERR_COMPONENT_NAMING flags a Geometry, View or
        Fire LOD with faces outside its proxy triangles and no selection
        whose name starts with 'component' (it ran on the Geometry LOD
        alone) and no longer flags a lowercase 'component01';
        WARN_COMPONENT_NAMING only flags a LOD whose component names are
        none of them 'Component' and a number, the case ignored;
        WARN_COMPONENT_COVERAGE counts the faces that are not proxy
        triangles, and the points they use, that no ComponentNN selection
        holds (any case), on the Geometry, View and Fire LODs (it compared
        'Component01' alone with the whole Geometry LOD).
        Changed in 1.10.0: ERR_COMPONENT_COVERAGE (new) flags, on those
        LODs, a closed part with no face and no point in any ComponentNN
        selection, measured in game to collide with nothing; the other
        faces and points in no component stay WARN_COMPONENT_COVERAGE.
        Changed in 1.10.1: ERR_WINDING_VS_NORMALS and ERR_WINDING_INVERTED
        close with the normals read part by part, never a corner on its
        own sign (README, 'Winding', step 3); up to 1.10.0 they said to
        negate each corner normal that points against its face. Codes and
        severities are unchanged.

        Returns list[Finding]. It does NOT raise on findings, though it
        does raise on misuse of its own parameters. The in-memory round
        trip is only attempted when no ERROR was found already, because
        the write guards would raise.
        """
        findings = []
        for i, lod in enumerate(self.lods):
            findings.extend(lod._scan_findings(i))
            findings.extend(lod.validate_normals_budget(
                budget=normals_budget, severity=normals_severity,
                lod_index=i))
        findings.extend(self._scan_v12_findings())
        if not any(f.severity == "ERROR" for f in findings):
            import io
            try:
                buf = io.BytesIO()
                self.write(buf)
                buf.seek(0)
                self._verify_against(P3D(buf))
            except Exception as e:
                findings.append(Finding(
                    "ERR_UNREADABLE_ROUNDTRIP", "ERROR", None,
                    "in-memory round-trip failed: %s" % e))
        return findings


def blender_to_dayz(p3d):
    """Convert a model authored in Blender's frame to DayZ's, in place.

    Blender is right-handed: X right, Y depth, Z up, front at -Y. DayZ is
    left-handed: X east, Y up, Z north. Keeping the SHAPE across a change of
    handedness takes a reflection in the numbers, so points map
    (x,y,z) -> (x,z,y), det=-1. A det=+1 rotation such as ROT_X_NEG90 (the
    old BLENDER_TO_DAYZ) gives the mirror image instead: right size, right
    way up, text reading backwards.

    Faces keep their vertex order, and every normal is mapped and negated
    (near-zero ones are only negated: see the last paragraph).
    The input is what Blender stores: front faces counter-clockwise seen
    from outside, so the vertex-order cross product points outward, and
    outward normals. The reflection alone turns that cross product inward,
    which is the MLOD convention - vertex-order cross product AND shading
    normals point INWARD, measured against binarized vanilla models - so
    the order stays and only the normals change sign. P3D.transform()
    reverses every face for a det<0 matrix, which is right for a reflection
    inside one frame and wrong here; this function undoes it.

    Measured in game (DayZDiag 1.29.163709, 2026-10-01): one chiral model,
    an "F" in relief on a plate, written three ways and binarized with
    AddonBuilder.

    - this conversion: solid, and the F reads correctly;
    - ROT_X_NEG90, then every face reversed and every normal negated:
      solid but MIRRORED;
    - transform(ROT_X_NEG90) alone: inside-out AND mirrored.

    Call it once, on geometry that is in Blender space, before adding
    anything built in DayZ space - collision boxes, memory points in DayZ
    coordinates, proxies placed with LOD.add_proxy(space="engine"): it
    converts everything in the model, and a second call undoes the first
    (normals then come back unit-length, as P3D.transform() leaves them).

    Proxy triangles move like any other face - points mapped, vertex order
    kept, normal negated - and nothing more. Measured the same day with
    static proxies: a proxy drawn in Blender as this library's canonical
    raw triangle (what LOD.add_proxy(space="raw") builds in Blender
    coordinates, and what a DayZ raw triangle looks like after the swap)
    comes out of binarize with the same engine frame as
    LOD.add_proxy(space="engine") given the matching rotation, and renders
    in the pose it had in Blender. A proxy drawn another way gets whatever
    frame its triangle implies; check that one in the binarized file
    against a model that works. Collision LODs converted with this
    function register raycasts in all three collision modes; with
    transform(ROT_X_NEG90) alone they do not.

    Refuses, with ValueError and before changing anything, a model where
    one Point object or one facenormals list is listed more than once -
    shared between LODs, typically: P3D.transform() would map it once per
    listing and leave it wrong without a word. Normals come out
    unit-length, as P3D.transform() leaves them; degenerate (near-zero)
    ones are kept as it keeps them, unmapped, and then negated. Does not
    touch uv, sharp_edges, selections, properties, flags or mass. Returns
    None.
    """
    seen_points = {}
    seen_pools = {}
    for i, lod in enumerate(p3d.lods):
        pool = id(lod.facenormals)
        if pool in seen_pools:
            raise ValueError(
                "blender_to_dayz: LOD %d and LOD %d share one facenormals "
                "list, which would be mapped twice; give each LOD its own "
                "list. Nothing was changed." % (seen_pools[pool], i))
        seen_pools[pool] = i
        for p in lod.points:
            if id(p) in seen_points:
                raise ValueError(
                    "blender_to_dayz: one Point object is listed in LOD %d "
                    "and again in LOD %d, so it would be moved twice; give "
                    "each LOD its own points. Nothing was changed."
                    % (seen_points[id(p)], i))
            seen_points[id(p)] = i
    p3d.transform(_BLENDER_TO_DAYZ_AXES)
    for lod in p3d.lods:
        for face in lod.faces:
            face.vertices.reverse()
        for i, n in enumerate(lod.facenormals):
            lod.facenormals[i] = (-n[0], -n[1], -n[2])
    return None
