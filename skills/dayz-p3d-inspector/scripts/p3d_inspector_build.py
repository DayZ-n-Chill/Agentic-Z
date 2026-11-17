#!/usr/bin/env python3
"""
P3D Inspector - Recipe -> .p3d Builder
Takes a Recipe JSON (as produced by p3d_inspector_extract.py) and assembles
a fresh MLOD .p3d file via py3d.

Supported LOD types: visual_0..3, geometry, fire_geometry, view_geometry,
landcontact, roadway, paths, hitpoints, shadow, memory. Handles material_groups ->
Face, wireframe -> collision Face, memory points -> one Selection per name, and
properties. Each LOD is written at the resolution the Recipe records for it.

Mass policy:
  - The Geometry LOD gets pt.mass assigned based on bbox volume * material density
  - Density looked up by keyword match on referenced materials/textures
    (first match in DENSITY_KEYWORDS, e.g. metal/steel/iron=7800, wood=600,
    plastic=1200, glass=2500; DENSITY_DEFAULT=2000 kg/m^3 when none matches)
  - Override via recipe.meta.point_mass_default or lod.properties["_point_mass"]

Validation policy:
  - Auto-fixes inverted face winding when >50% of the faces of the first (lowest
    resolution) visual LOD have stored normals opposite to the geometric
    cross-product (reverses winding on ALL LODs).
  - For deeper validation (paths, structure, BB anchor), pipe the resulting
    .p3d through the dayz-p3d-audit skill.

py3d: the DayZ fork in this repo (scripts/tools/py3d) is used with nothing to
install; without it the installed py3d is used. Never `pip install py3d`: the PyPI
package of that name is an unrelated point-cloud library.
numpy is needed only by the auto-fix (python -m pip install numpy); without numpy
the auto-fix is skipped.

Offline tool: it reads and writes files anywhere on disk and does not touch P:\\,
DayZ Tools or the game, so it does not gate on /dayz-preflight.

Usage:
  python p3d_inspector_build.py recipe.json output.p3d [-v] [--no-autofix]

  # Or import:
  from p3d_inspector_build import build_p3d
  result = build_p3d(recipe_dict, "out.p3d", auto_fix_enabled=True, verbose=True)
"""

import importlib.util
import json
import math
import os
import sys
from pathlib import Path

# The DayZ fork of py3d kept in this repo. A plugin install that ships only
# skills/ has no such folder and falls back to the installed py3d.
REPO_FORK = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d" / "py3d" / "__init__.py"
_fork_module = None


def load_py3d():
    """py3d: the repo's DayZ fork when it is there, else the installed py3d.

    The fork is loaded from its file under a private module name, so it never
    replaces a py3d another script in the same process imported. Raises
    ImportError with an install hint when neither is found.
    """
    global _fork_module
    if REPO_FORK.is_file():
        if _fork_module is None:
            spec = importlib.util.spec_from_file_location("py3d_dayz_fork", REPO_FORK)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _fork_module = module
        return _fork_module
    try:
        import py3d
    except ImportError:
        raise ImportError(
            "py3d not found: %s is missing and no py3d is installed. Build the fork's "
            "wheel and run install_py3d.py next to this script. Never `pip install py3d`: "
            "the PyPI package of that name is an unrelated library." % REPO_FORK
        ) from None
    return py3d


# ── Material density lookup (kg/m^3) ──────────────────────────────
DENSITY_KEYWORDS = [
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
    ("concrete",2400),
    ("stone",   2600),
    ("fabric",   300),
    ("cloth",    300),
]
DENSITY_DEFAULT = 2000  # generic electrical / composite housing


def guess_density(recipe: dict) -> float:
    """Heuristic: scan referenced paths for material keywords."""
    paths = []
    refs = recipe.get("referenced_paths", {})
    paths.extend(refs.get("textures", []))
    paths.extend(refs.get("materials", []))

    blob = " ".join(paths).lower()
    for kw, d in DENSITY_KEYWORDS:
        if kw in blob:
            return d
    return DENSITY_DEFAULT


# ── LOD Resolution mapping ────────────────────────────────────────
# Bohemia MLOD resolution values as DayZ uses them. The special LOD types live in
# the 1e15 family, not 1e13/2e13/3e13. Used when a Recipe LOD records no resolution.
LOD_RESOLUTION = {
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

# Wireframe-style LODs handled by build_wireframe_lod().
WIREFRAME_LOD_TYPES = (
    "geometry", "fire_geometry", "view_geometry",
    "landcontact", "roadway", "paths", "hitpoints",
    "shadow",
)
# Only the Geometry LOD carries per-point mass. Mass on the Fire Geometry LOD is a
# fault the audit reports (ERR_MASS_ONLY_GEOMETRY).
MASSED_LOD_TYPES = ("geometry",)


def lod_resolution_for_type(lod_type: str, recorded) -> float:
    """The resolution the Recipe records for the LOD, else the usual one for its type.

    Keeping the recorded value keeps two visual levels (2 and 3, say) or two shadow
    volumes apart; writing every LOD at its type's usual value would merge them.
    """
    if recorded is not None:
        return float(recorded)
    return LOD_RESOLUTION.get(lod_type, 0.0)


# ── Normal dedup ──────────────────────────────────────────────────

def dedup_normals(per_vertex_normals):
    """Return (pool, index_map) where index_map[i] = pool index for vertex i."""
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


# ── Bounding box ──────────────────────────────────────────────────

def lod_bbox(lod):
    if not lod.points:
        return None, None, None
    xs = [p.coords[0] for p in lod.points]
    ys = [p.coords[1] for p in lod.points]
    zs = [p.coords[2] for p in lod.points]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    center = ((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, (lo[2]+hi[2])/2)
    return lo, hi, center


def volume_from_bbox(lo, hi):
    v = max(1e-6, (hi[0]-lo[0]) * (hi[1]-lo[1]) * (hi[2]-lo[2]))
    return v


# ── Visual LOD builder ────────────────────────────────────────────

def build_visual_lod(lod_dict, py3d):
    """Build a visual LOD from Recipe geometry (positions + normals + uvs + material_groups)."""
    lod = py3d.LOD()
    lod.resolution = lod_resolution_for_type(lod_dict["type"], lod_dict.get("resolution"))

    geo = lod_dict.get("geometry", {})
    positions = geo.get("positions", [])
    normals = geo.get("normals", [])
    uvs = geo.get("uvs", [])
    material_groups = geo.get("material_groups", {})

    # Build points pool
    for pos in positions:
        pt = py3d.Point()
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        lod.points.append(pt)

    # Dedup per-vertex normals into a face normal pool (MLOD uses shared pool)
    pool, normal_idx_map = dedup_normals(normals)
    lod.facenormals = pool

    # Build faces from material_groups (each group is a triangulated index list)
    face_of_triangle = geo.get("face_of_triangle")
    built_face_sources = []  # the source LOD face each built face came from
    for key, indices in material_groups.items():
        sources = face_of_triangle.get(key, []) if face_of_triangle is not None else []
        if "|" in key:
            tex, mat = key.split("|", 1)
        else:
            tex, mat = key, ""

        # Walk in triangles
        for i in range(0, len(indices) - 2, 3):
            i0, i1, i2 = indices[i], indices[i+1], indices[i+2]

            face = py3d.Face(lod.points, lod.facenormals)
            face.flags = 0
            face.texture = tex
            face.material = mat

            for vi in (i0, i1, i2):
                vx = py3d.Vertex(lod.points, lod.facenormals)
                vx.point_index = vi
                vx.normal_index = normal_idx_map[vi] if vi < len(normal_idx_map) else 0
                # UV: Recipe stores glTF convention (V-flipped). Flip back for DayZ.
                if vi < len(uvs):
                    u, v = uvs[vi]
                    vx.uv = (float(u), 1.0 - float(v))
                else:
                    vx.uv = (0.0, 0.0)
                face.vertices.append(vx)

            lod.faces.append(face)
            built_face_sources.append(sources[i // 3] if i // 3 < len(sources) else None)

    # Build selections. An extracted Recipe indexes them by the source LOD's points
    # and faces, which are not the entries and triangles built above.
    point_map = face_map = None
    if geo.get("point_of_vertex") is not None:
        point_map = {}
        for built, source in enumerate(geo["point_of_vertex"]):
            point_map.setdefault(source, []).append(built)
    if face_of_triangle is not None:
        face_map = {}
        for built, source in enumerate(built_face_sources):
            face_map.setdefault(source, []).append(built)
    build_lod_selections(lod, lod_dict.get("selections", {}), py3d, point_map, face_map)

    # Properties
    for k, v in lod_dict.get("properties", {}).items():
        if not k.startswith("_"):  # skip internal overrides
            lod.properties[str(k)] = str(v)

    return lod


# ── Collision / Shadow LOD builder ────────────────────────────────

def build_wireframe_lod(lod_dict, lod_type, recipe, py3d):
    """Build a collision, contact, path, hit point or shadow LOD from wireframe data."""
    lod = py3d.LOD()
    lod.resolution = lod_resolution_for_type(lod_type, lod_dict.get("resolution"))

    wf = lod_dict.get("wireframe", {})
    positions = wf.get("positions", [])
    faces_data = wf.get("faces", [])

    # Points
    for pos in positions:
        pt = py3d.Point()
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        lod.points.append(pt)

    # Face normals: compute one per face by cross product
    # (wireframe faces don't carry normals; MLOD still needs the pool).
    # Larger polygons get their normals when they are fanned below.
    for face_indices in faces_data:
        if len(face_indices) < 3 or len(face_indices) > 4:
            continue
        nrm = _face_normal(positions, face_indices)
        lod.facenormals.append(nrm)

    # Faces (only for geometry-class LODs; shadow also has faces)
    norm_idx = 0
    for face_indices in faces_data:
        if len(face_indices) < 3 or len(face_indices) > 4:
            # MLOD only supports tri/quad; triangulate N-gons
            _append_triangulated(lod, face_indices, positions, py3d)
            continue

        face = py3d.Face(lod.points, lod.facenormals)
        face.flags = 0
        face.texture = ""
        face.material = ""
        for pi in face_indices:
            vx = py3d.Vertex(lod.points, lod.facenormals)
            vx.point_index = int(pi)
            vx.normal_index = norm_idx
            vx.uv = (0.0, 0.0)
            face.vertices.append(vx)
        lod.faces.append(face)
        norm_idx += 1

    # Mass only on the Geometry LOD.
    # FireGeo, ViewGeo, Shadow, LandContact, Roadway, Paths, HitPoints: no mass.
    if lod_type in MASSED_LOD_TYPES:
        _assign_mass(lod, lod_dict, recipe)

    # Selections
    build_lod_selections(lod, lod_dict.get("selections", {}), py3d)

    # Properties (preserve whatever was extracted)
    for k, v in lod_dict.get("properties", {}).items():
        if not k.startswith("_"):
            lod.properties[str(k)] = str(v)

    # Sensible defaults for Geometry LOD if missing
    if lod_type == "geometry":
        if "autocenter" not in lod.properties:
            lod.properties["autocenter"] = "0"
        if "class" not in lod.properties:
            lod.properties["class"] = "house"

    return lod


def _face_normal(positions, indices):
    """Compute face normal from first 3 vertices (cross product)."""
    try:
        p0 = positions[indices[0]]
        p1 = positions[indices[1]]
        p2 = positions[indices[2]]
        v1 = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
        v2 = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
        nx = v1[1]*v2[2] - v1[2]*v2[1]
        ny = v1[2]*v2[0] - v1[0]*v2[2]
        nz = v1[0]*v2[1] - v1[1]*v2[0]
        L = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        return (nx/L, ny/L, nz/L)
    except (IndexError, TypeError):
        return (0.0, 1.0, 0.0)


def _append_triangulated(lod, face_indices, positions, py3d):
    """Fan-triangulate an N-gon and append tris to lod."""
    for i in range(1, len(face_indices) - 1):
        tri = [face_indices[0], face_indices[i], face_indices[i+1]]
        nrm = _face_normal(positions, tri)
        lod.facenormals.append(nrm)
        nidx = len(lod.facenormals) - 1
        face = py3d.Face(lod.points, lod.facenormals)
        face.flags = 0
        face.texture = ""
        face.material = ""
        for pi in tri:
            vx = py3d.Vertex(lod.points, lod.facenormals)
            vx.point_index = int(pi)
            vx.normal_index = nidx
            vx.uv = (0.0, 0.0)
            face.vertices.append(vx)
        lod.faces.append(face)


def _assign_mass(lod, lod_dict, recipe):
    """Distribute mass across points based on bbox volume and material density."""
    if not lod.points:
        return

    # Priority: per-LOD override > recipe.meta override > density heuristic
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
        lo, hi, _ = lod_bbox(lod)
        vol = volume_from_bbox(lo, hi)
        density = guess_density(recipe)
        total_mass = vol * density
        per_point = max(0.1, total_mass / len(lod.points))

    for p in lod.points:
        p.mass = per_point


# ── Memory LOD builder ────────────────────────────────────────────

def build_memory_lod(recipe, py3d):
    """Build Memory LOD from recipe.memory_points (no faces, selections only)."""
    lod = py3d.LOD()
    lod.resolution = LOD_RESOLUTION["memory"]

    memory_points = recipe.get("memory_points", [])
    if not memory_points:
        return None

    # Create Point objects in the same order as recipe (index-stable)
    # Sort by original index just to be safe
    sorted_pts = sorted(memory_points, key=lambda m: m.get("index", 0))
    point_objs = []
    for mp in sorted_pts:
        pt = py3d.Point()
        pos = mp["position"]
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        point_objs.append(pt)
        lod.points.append(pt)

    # Build selections by grouping memory points by selection name
    # Each memory point can belong to multiple selections
    sel_name_to_points = {}
    for i, mp in enumerate(sorted_pts):
        for sel_name in mp.get("selections", []):
            sel_name_to_points.setdefault(sel_name, []).append(point_objs[i])

    for sel_name, pts in sel_name_to_points.items():
        sel = py3d.Selection(lod.points, lod.faces)
        for p in pts:
            sel.points[p] = 1
        lod.selections[sel_name] = sel

    return lod


# ── Generic selection builder ─────────────────────────────────────

def build_lod_selections(lod, selections_dict, py3d, point_map=None, face_map=None):
    """Attach the Recipe's selections to a LOD.

    The Recipe's vertices and faces index the LOD's own points and faces. point_map
    and face_map, when given, translate an index of the source LOD into the built
    points and faces that came from it (a visual LOD is rebuilt with split points
    and triangulated faces).
    """
    for sel_name, sel_data in selections_dict.items():
        sel = py3d.Selection(lod.points, lod.faces)
        for vi in sel_data.get("vertices", []):
            for built in ([vi] if point_map is None else point_map.get(vi, [])):
                if 0 <= built < len(lod.points):
                    sel.points[lod.points[built]] = 1
        for fi in sel_data.get("faces", []):
            for built in ([fi] if face_map is None else face_map.get(fi, [])):
                if 0 <= built < len(lod.faces):
                    sel.faces[lod.faces[built]] = 1
        lod.selections[sel_name] = sel


# ── Auto-fix / validation ─────────────────────────────────────────

def classify_lod_res(res):
    """Internal helper for verbose output. Mirrors the extractor's classifier."""
    if res < 1.0e3:
        return "visual"
    elif 1.0e4 <= res < 2.0e4:
        return "shadow"
    elif abs(res - 1.0e13) < 1.0e11:
        return "geometry"
    elif abs(res - 1.0e15) < 5.0e13:
        return "memory"
    elif abs(res - 2.0e15) < 5.0e13:
        return "landcontact"
    elif abs(res - 3.0e15) < 5.0e13:
        return "roadway"
    elif abs(res - 4.0e15) < 5.0e13:
        return "paths"
    elif abs(res - 5.0e15) < 5.0e13:
        return "hitpoints"
    elif abs(res - 6.0e15) < 5.0e13:
        return "view_geometry"
    elif abs(res - 7.0e15) < 5.0e13:
        return "fire_geometry"
    return "unknown"


def auto_fix(model, verbose=False):
    """Apply safe auto-fixes. Returns list of fixes applied."""
    fixes = []

    # Winding check: count faces with inverted normals in the first visual LOD,
    # the one with the lowest resolution (vanilla often numbers it 1.0, not 0.0).
    try:
        import numpy as np
    except ImportError:
        return fixes

    visual = [lod for lod in model.lods if classify_lod_res(lod.resolution) == "visual"]
    lod0 = min(visual, key=lambda lod: lod.resolution) if visual else None

    if lod0 is None or not lod0.faces:
        return fixes

    flipped = 0
    total = 0
    for face in lod0.faces:
        if len(face.vertices) < 3:
            continue
        pts = [lod0.points[v.point_index].coords for v in face.vertices[:3]]
        v1 = np.array(pts[1]) - np.array(pts[0])
        v2 = np.array(pts[2]) - np.array(pts[0])
        geo_n = np.cross(v1, v2)
        L = np.linalg.norm(geo_n)
        if L < 1e-10:
            continue
        geo_n = geo_n / L
        stored = np.array(lod0.facenormals[face.vertices[0].normal_index])
        total += 1
        if np.dot(geo_n, stored) < 0:
            flipped += 1

    if total > 0 and flipped > total * 0.5:
        # Reverse winding on ALL LODs
        for lod in model.lods:
            for face in lod.faces:
                face.vertices.reverse()
        fixes.append(f"auto-fix: reversed winding on all faces ({flipped}/{total} were inverted)")

    return fixes


# ── Main build ────────────────────────────────────────────────────

def build_p3d(recipe, output_path, auto_fix_enabled=True, verbose=False):
    """
    Assemble a .p3d file from a Recipe dict.
    Returns dict: { "output_path", "lods_written", "fixes_applied", "warnings" }
    """
    py3d_lib = load_py3d()

    model = py3d_lib.P3D()
    warnings = []

    for lod_dict in recipe.get("lods", []):
        lod_type = lod_dict.get("type", "unknown")

        if lod_type.startswith("visual"):
            lod = build_visual_lod(lod_dict, py3d_lib)
            model.lods.append(lod)
        elif lod_type in WIREFRAME_LOD_TYPES:
            lod = build_wireframe_lod(lod_dict, lod_type, recipe, py3d_lib)
            model.lods.append(lod)
        elif lod_type == "memory":
            # Skip — built from recipe.memory_points below, not from lod_dict
            continue
        else:
            warnings.append(f"skipped unknown LOD type: {lod_type}")

    # Always rebuild Memory LOD from recipe.memory_points
    mem_lod = build_memory_lod(recipe, py3d_lib)
    if mem_lod is not None:
        model.lods.append(mem_lod)

    # Auto-fix if enabled
    fixes_applied = []
    if auto_fix_enabled:
        fixes_applied = auto_fix(model, verbose=verbose)

    # Write
    with open(output_path, "wb") as f:
        model.write(f)

    if verbose:
        print(f"Wrote: {output_path}")
        print(f"  LODs written: {len(model.lods)}")
        for lod in model.lods:
            t = classify_lod_res(lod.resolution)
            print(f"    {t}: {len(lod.points)} pts, {len(lod.faces)} faces, {len(lod.selections)} sels")
        if fixes_applied:
            print("  Auto-fixes:")
            for fx in fixes_applied:
                print(f"    - {fx}")
        if warnings:
            print("  Warnings:")
            for w in warnings:
                print(f"    - {w}")

    return {
        "output_path": output_path,
        "lods_written": len(model.lods),
        "fixes_applied": fixes_applied,
        "warnings": warnings,
    }


# ── CLI ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: p3d_inspector_build.py recipe.json [output.p3d] [-v] [--no-autofix]")
        sys.exit(1)

    recipe_path = sys.argv[1]
    out_path = None
    verbose = False
    autofix = True
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "-v":
            verbose = True
        elif arg == "--no-autofix":
            autofix = False
        elif not arg.startswith("-") and out_path is None:
            out_path = arg

    if out_path is None:
        out_path = os.path.splitext(recipe_path)[0] + "_built.p3d"

    with open(recipe_path, "r") as f:
        recipe = json.load(f)

    try:
        result = build_p3d(recipe, out_path, auto_fix_enabled=autofix, verbose=verbose)
    except ImportError as exc:
        sys.exit(f"[FAIL] {exc}")
    print(f"\nDone. LODs={result['lods_written']}, fixes={len(result['fixes_applied'])}, warnings={len(result['warnings'])}")
