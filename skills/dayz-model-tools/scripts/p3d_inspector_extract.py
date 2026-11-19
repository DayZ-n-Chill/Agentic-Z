#!/usr/bin/env python3
"""
P3D Inspector - data extractor.

Reads a source (MLOD) .p3d with py3d and writes everything in it into one Recipe
JSON: every LOD, memory point, axis, selection, named property and referenced path.

Usage:
  python p3d_inspector_extract.py <model.p3d> [-v] [-o recipe.json]
  python p3d_inspector_extract.py --demo [out.json]     (a demo Recipe, no model needed)

py3d: the DayZ fork in this repo (scripts/tools/py3d) is used with nothing to
install; without it the installed py3d is used. Never `pip install py3d`: the PyPI
package of that name is an unrelated point-cloud library.

Offline tool: it reads and writes files anywhere on disk and does not touch P:\\,
DayZ Tools or the game, so it does not gate on /dayz-preflight.
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


# ── LOD Classification ─────────────────────────────────────────────
# Bohemia MLOD resolution values as DayZ uses them. Visual LODs are 0 to 999 and
# shadow volumes 10000 to 19999; the "special" LOD types use very large values:
#   1.0e13 = Geometry
#   1.0e15 = Memory
#   2.0e15 = LandContact
#   3.0e15 = Roadway
#   4.0e15 = Paths
#   5.0e15 = HitPoints
#   6.0e15 = ViewGeometry
#   7.0e15 = FireGeometry
LOD_THRESHOLDS = {
    "visual_0":      (0.0, 0.5),
    "visual_1":      (0.5, 2.0),
    "visual_2":      (2.0, 6.0),
    "visual_3":      (6.0, 1.0e3),
    "shadow":        (1.0e4, 2.0e4),
    "geometry":      (0.9e13, 1.1e13),
    "memory":        (0.9e15, 1.1e15),
    "landcontact":   (1.9e15, 2.1e15),
    "roadway":       (2.9e15, 3.1e15),
    "paths":         (3.9e15, 4.1e15),
    "hitpoints":     (4.9e15, 5.1e15),
    "view_geometry": (5.9e15, 6.1e15),
    "fire_geometry": (6.9e15, 7.1e15),
}

# Wireframe-style LODs (no per-vertex normals/UVs; have collision-style faces).
WIREFRAME_LOD_TYPES = (
    "geometry", "fire_geometry", "view_geometry",
    "landcontact", "roadway", "paths", "hitpoints",
)


def classify_lod(resolution: float) -> str:
    """Classify a LOD by its resolution value. See LOD_THRESHOLDS for the map."""
    # Visual LODs: 0 to 999. visual_3 holds every level from 6 up; the builder
    # writes each LOD back at its own resolution, so the levels stay apart.
    if resolution < 0.5:
        return "visual_0"
    elif resolution < 2.0:
        return "visual_1"
    elif resolution < 6.0:
        return "visual_2"
    elif resolution < 1.0e3:
        return "visual_3"
    # Shadow volumes: 10000 to 19999
    elif 1.0e4 <= resolution < 2.0e4:
        return "shadow"
    # Geometry: 1.0e13
    elif abs(resolution - 1.0e13) < 1.0e11:
        return "geometry"
    # 1e15 family — match each bucket with ±5e13 tolerance (≈5% slack)
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
        return f"unknown_{resolution:.0f}"


def classify_memory_point(selections: list) -> str:
    """Classify a memory point by its selection names."""
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


# ── Geometry Extraction ────────────────────────────────────────────

def extract_visual_geometry(lod) -> dict:
    """Extract full geometry from a visual LOD (positions, normals, UVs, material groups).

    A point used with two normals or two UVs becomes two entries, and a quad becomes
    two triangles. point_of_vertex and face_of_triangle record which point and which
    face of the LOD each entry and each triangle came from, so the builder can put
    the LOD's selections back on the same geometry.
    """
    vertex_map = {}
    positions = []
    normals = []
    uvs = []
    material_groups = {}
    point_of_vertex = []
    face_of_triangle = {}

    for face_index, face in enumerate(lod.faces):
        tex = face.texture if face.texture else ""
        mat = face.material if face.material else ""
        key = f"{tex}|{mat}"

        if key not in material_groups:
            material_groups[key] = []
            face_of_triangle[key] = []

        face_indices = []
        for vertex in face.vertices:
            pt_idx = vertex.point_index
            norm_idx = vertex.normal_index
            u, v = vertex.uv if vertex.uv else (0.0, 0.0)

            vert_key = (pt_idx, norm_idx, round(u, 6), round(v, 6))

            if vert_key not in vertex_map:
                new_idx = len(positions)
                vertex_map[vert_key] = new_idx

                pt = lod.points[pt_idx]
                positions.append(list(pt.coords))
                point_of_vertex.append(pt_idx)

                if norm_idx < len(lod.facenormals):
                    normals.append(list(lod.facenormals[norm_idx]))
                else:
                    normals.append([0.0, 1.0, 0.0])

                uvs.append([u, 1.0 - v])  # glTF V-flip

            face_indices.append(vertex_map[vert_key])

        # Triangulate
        if len(face_indices) == 3:
            material_groups[key].extend(face_indices)
        elif len(face_indices) == 4:
            material_groups[key].extend([
                face_indices[0], face_indices[1], face_indices[2],
                face_indices[0], face_indices[2], face_indices[3],
            ])
        elif len(face_indices) > 4:
            for i in range(1, len(face_indices) - 1):
                material_groups[key].extend([
                    face_indices[0], face_indices[i], face_indices[i + 1]
                ])
        triangles = len(material_groups[key]) // 3 - len(face_of_triangle[key])
        face_of_triangle[key].extend([face_index] * triangles)

    return {
        "positions": positions,
        "normals": normals,
        "uvs": uvs,
        "material_groups": material_groups,
        "point_of_vertex": point_of_vertex,
        "face_of_triangle": face_of_triangle,
    }


def extract_wireframe(lod) -> dict:
    """Extract wireframe data from a collision/shadow LOD."""
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
        "edges": [list(e) for e in edges],
        "faces": faces_data,
    }


def extract_selections(lod) -> dict:
    """Extract all named selections from a LOD with vertex indices.

    py3d LOD.selections is an OrderedDict {name: Selection}.
    Each Selection has:
      .points = {Point: weight}
      .faces  = {Face: weight}
    We translate Point/Face object keys back into indices into lod.points/lod.faces.
    """
    selections = {}

    if not hasattr(lod, 'selections'):
        return selections

    # Build id() -> index maps once (O(N) instead of O(N^2) on large LODs)
    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    fc_idx = {id(f): i for i, f in enumerate(lod.faces)}

    for name, sel in lod.selections.items():
        vertex_indices = []
        if hasattr(sel, 'points') and sel.points:
            for pt, weight in sel.points.items():
                if weight > 0:
                    idx = pt_idx.get(id(pt))
                    if idx is not None:
                        vertex_indices.append(idx)

        face_indices = []
        if hasattr(sel, 'faces') and sel.faces:
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


def extract_lod_properties(lod) -> dict:
    """Extract named properties from a LOD."""
    props = {}
    if hasattr(lod, 'properties'):
        for key, val in lod.properties.items():
            props[key] = val
    return props


# ── Memory LOD Analysis ────────────────────────────────────────────

def extract_memory_data(lod) -> tuple:
    """
    Extract memory points and axes from the Memory LOD.
    Returns (memory_points, axes).
    """
    memory_points = []
    axes = {}

    point_to_selections = {}
    selection_point_map = {}

    if hasattr(lod, 'selections'):
        # py3d selections are OrderedDict {name: Selection}; .points is {Point: weight}
        pt_idx = {id(p): i for i, p in enumerate(lod.points)}
        for name, sel in lod.selections.items():
            pts_in_sel = []
            if hasattr(sel, 'points') and sel.points:
                for pt, weight in sel.points.items():
                    if weight > 0:
                        idx = pt_idx.get(id(pt))
                        if idx is None:
                            continue
                        pts_in_sel.append(idx)
                        if idx not in point_to_selections:
                            point_to_selections[idx] = []
                        point_to_selections[idx].append(name)
            selection_point_map[name] = pts_in_sel

    for i, point in enumerate(lod.points):
        sels = point_to_selections.get(i, [])
        category = classify_memory_point(sels)
        mp = {
            "index": i,
            "position": list(point.coords),
            "selections": sels,
            "category": category,
            "label": sels[0] if sels else f"point_{i}",
        }
        memory_points.append(mp)

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


# ── Main Extraction ────────────────────────────────────────────────

def extract_recipe(p3d_path: str, verbose: bool = False) -> dict:
    """
    Extract a complete Recipe JSON from a .p3d file.
    """
    py3d_lib = load_py3d()

    if verbose:
        print(f"Reading: {p3d_path}")

    with open(p3d_path, 'rb') as f:
        p3d_file = py3d_lib.P3D(f)

    if verbose:
        print(f"LODs found: {len(p3d_file.lods)}")

    recipe = {
        "meta": {
            "source": os.path.basename(p3d_path),
            "source_path": p3d_path,
            "version": 1,
            "mode": "audit",
        },
        "lods": [],
        "memory_points": [],
        "axes": {},
        "bounding_box": None,
    }

    global_min = [float('inf')] * 3
    global_max = [float('-inf')] * 3

    for lod in p3d_file.lods:
        lod_type = classify_lod(lod.resolution)

        if verbose:
            print(f"  {lod_type}: {len(lod.points)} points, {len(lod.faces)} faces")

        lod_info = {
            "type": lod_type,
            "resolution": lod.resolution,
            "num_points": len(lod.points),
            "num_faces": len(lod.faces),
            "selections": extract_selections(lod),
            "properties": extract_lod_properties(lod),
        }

        if lod_type.startswith("visual"):
            geo = extract_visual_geometry(lod)
            lod_info["geometry"] = geo
            for pos in geo["positions"]:
                for j in range(3):
                    global_min[j] = min(global_min[j], pos[j])
                    global_max[j] = max(global_max[j], pos[j])

        elif lod_type in WIREFRAME_LOD_TYPES:
            lod_info["wireframe"] = extract_wireframe(lod)
            # Use Geometry LOD bounds as authoritative; the others contribute
            # too if no Geometry LOD is present.
            if lod_type in ("geometry", "fire_geometry", "view_geometry"):
                for pos in lod_info["wireframe"]["positions"]:
                    for j in range(3):
                        global_min[j] = min(global_min[j], pos[j])
                        global_max[j] = max(global_max[j], pos[j])

        elif lod_type == "shadow":
            lod_info["wireframe"] = extract_wireframe(lod)

        elif lod_type == "memory":
            memory_points, axes = extract_memory_data(lod)
            recipe["memory_points"] = memory_points
            recipe["axes"] = axes
            lod_info["note"] = f"{len(memory_points)} points, {len(axes)} axes"

        recipe["lods"].append(lod_info)

    if global_min[0] != float('inf'):
        recipe["bounding_box"] = {
            "min": global_min,
            "max": global_max,
            "size": [global_max[j] - global_min[j] for j in range(3)],
            "center": [(global_min[j] + global_max[j]) / 2 for j in range(3)],
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

    if verbose:
        print(f"\nRecipe summary:")
        print(f"  LODs: {len(recipe['lods'])}")
        print(f"  Memory points: {len(recipe['memory_points'])}")
        print(f"  Axes: {len(recipe['axes'])}")
        print(f"  Textures: {len(all_textures)}")
        print(f"  Materials: {len(all_materials)}")
        if recipe["bounding_box"]:
            sz = recipe["bounding_box"]["size"]
            print(f"  Bounding box: {sz[0]:.3f} x {sz[1]:.3f} x {sz[2]:.3f} m")

    return recipe


# ── Demo Data Generation ───────────────────────────────────────────

def generate_demo_recipe() -> dict:
    """
    Generate a synthetic demo recipe for testing the viewer
    without a real .p3d file. Simulates a small electrical switch.
    """
    hw, hh, hd = 0.15, 0.10, 0.10

    positions = [
        [-hw, 0, -hd], [hw, 0, -hd], [hw, 0, hd], [-hw, 0, hd],
        [-hw, hh*2, -hd], [hw, hh*2, -hd], [hw, hh*2, hd], [-hw, hh*2, hd],
        [0.00, hh*2, 0.00],
        [0.03, hh*2+0.015, 0.00],
        [0.021, hh*2+0.015, 0.021],
        [0.00, hh*2+0.015, 0.03],
        [-0.021, hh*2+0.015, 0.021],
        [-0.03, hh*2+0.015, 0.00],
        [-0.021, hh*2+0.015, -0.021],
        [0.00, hh*2+0.015, -0.03],
        [0.021, hh*2+0.015, -0.021],
        [0.00, hh*2+0.015, 0.00],
    ]

    normals = []
    for p in positions:
        l = math.sqrt(sum(x*x for x in p)) or 1
        normals.append([p[0]/l, max(0.5, p[1]/l), p[2]/l])

    uvs = [[0, 0]] * len(positions)

    housing_indices = [
        0,1,2, 0,2,3,
        4,6,5, 4,7,6,
        0,1,5, 0,5,4,
        2,3,7, 2,7,6,
        0,3,7, 0,7,4,
        1,2,6, 1,6,5,
    ]

    button_indices = []
    for i in range(8):
        i0 = 9 + i
        i1 = 9 + (i + 1) % 8
        button_indices.extend([17, i0, i1])

    geo_positions = [
        [-hw-0.01, -0.01, -hd-0.01], [hw+0.01, -0.01, -hd-0.01],
        [hw+0.01, -0.01, hd+0.01], [-hw-0.01, -0.01, hd+0.01],
        [-hw-0.01, hh*2+0.025, -hd-0.01], [hw+0.01, hh*2+0.025, -hd-0.01],
        [hw+0.01, hh*2+0.025, hd+0.01], [-hw-0.01, hh*2+0.025, hd+0.01],
    ]
    geo_edges = [
        [0,1],[1,2],[2,3],[3,0],
        [4,5],[5,6],[6,7],[7,4],
        [0,4],[1,5],[2,6],[3,7],
    ]

    return {
        "meta": {
            "source": "demo_switch.p3d",
            "version": 1,
            "mode": "demo",
        },
        "lods": [
            {
                "type": "visual_0",
                "resolution": 0.0,
                "num_points": len(positions),
                "num_faces": len(housing_indices)//3 + len(button_indices)//3,
                "geometry": {
                    "positions": positions,
                    "normals": normals,
                    "uvs": uvs,
                    "material_groups": {
                        "switch_co.paa|switch.rvmat": housing_indices,
                        "button_co.paa|button.rvmat": button_indices,
                    },
                },
                "selections": {
                    "camo": {"vertices": list(range(8)), "faces": list(range(12)), "vertex_count": 8, "face_count": 12},
                    "button_push": {"vertices": list(range(8, 18)), "faces": list(range(12, 20)), "vertex_count": 10, "face_count": 8},
                    "light_led": {"vertices": [9,10,11,12,13,14,15,16,17], "faces": list(range(12, 20)), "vertex_count": 9, "face_count": 8},
                },
                "properties": {},
            },
            {
                "type": "geometry",
                "resolution": 1.0e13,
                "num_points": 8,
                "num_faces": 6,
                "wireframe": {
                    "positions": geo_positions,
                    "edges": geo_edges,
                    "faces": [[0,1,2,3],[4,5,6,7],[0,1,5,4],[2,3,7,6],[0,3,7,4],[1,2,6,5]],
                },
                "selections": {
                    "Component01": {"vertices": list(range(8)), "faces": list(range(6)), "vertex_count": 8, "face_count": 6},
                },
                "properties": {"autocenter": "0"},
            },
            {
                "type": "memory",
                "resolution": 1.0e15,
                "num_points": 8,
                "num_faces": 0,
                "selections": {},
                "properties": {},
                "note": "8 points, 1 axes",
            },
        ],
        "memory_points": [
            {"index": 0, "position": [0.0, 0.0, 0.0], "selections": ["pos center"], "category": "center", "label": "pos center"},
            {"index": 1, "position": [0.0, 0.10, 0.0], "selections": ["ce_center"], "category": "center", "label": "ce_center"},
            {"index": 2, "position": [0.0, 0.15, 0.12], "selections": ["actionPos"], "category": "interaction", "label": "actionPos"},
            {"index": 3, "position": [-0.18, 0.0, -0.13], "selections": ["box_placing_min"], "category": "placing", "label": "box_placing_min"},
            {"index": 4, "position": [0.18, 0.23, 0.13], "selections": ["box_placing_max"], "category": "placing", "label": "box_placing_max"},
            {"index": 5, "position": [0.0, 0.20, 0.0], "selections": ["button_axis"], "category": "axis", "label": "button_axis"},
            {"index": 6, "position": [0.0, 0.215, 0.0], "selections": ["button_axis"], "category": "axis", "label": "button_axis"},
            {"index": 7, "position": [0.0, 0.05, -0.10], "selections": ["port_input"], "category": "port", "label": "port_input"},
        ],
        "axes": {
            "button_axis": {
                "points": [[0.0, 0.20, 0.0], [0.0, 0.215, 0.0]],
                "point_indices": [5, 6],
                "direction": [0.0, 1.0, 0.0],
                "length": 0.015,
            },
        },
        "bounding_box": {
            "min": [-0.15, 0.0, -0.10],
            "max": [0.15, 0.215, 0.10],
            "size": [0.30, 0.215, 0.20],
            "center": [0.0, 0.1075, 0.0],
        },
        "referenced_paths": {
            "textures": ["button_co.paa", "switch_co.paa"],
            "materials": ["button.rvmat", "switch.rvmat"],
        },
    }


if __name__ == "__main__":
    if any(arg in ("-h", "--help") for arg in sys.argv[1:]):
        print("Usage: p3d_inspector_extract.py <model.p3d> [-o recipe.json] [-v]\n"
              "       p3d_inspector_extract.py --demo [output.json]")
        sys.exit(0)
    if len(sys.argv) < 2 or sys.argv[1] == "--demo":
        print("Generating demo recipe...")
        recipe = generate_demo_recipe()
        out = sys.argv[2] if len(sys.argv) > 2 else "demo_recipe.json"
        with open(out, 'w') as f:
            json.dump(recipe, f, indent=2)
        print(f"Saved: {out}")
    else:
        p3d_path = sys.argv[1]
        verbose = "-v" in sys.argv
        out_path = None
        for i, arg in enumerate(sys.argv):
            if arg == "-o" and i + 1 < len(sys.argv):
                out_path = sys.argv[i + 1]
        try:
            recipe = extract_recipe(p3d_path, verbose=verbose)
        except ImportError as exc:
            sys.exit(f"[FAIL] {exc}")
        if out_path is None:
            out_path = os.path.splitext(p3d_path)[0] + "_recipe.json"
        with open(out_path, 'w') as f:
            json.dump(recipe, f, indent=2)
        print(f"Saved: {out_path}")
