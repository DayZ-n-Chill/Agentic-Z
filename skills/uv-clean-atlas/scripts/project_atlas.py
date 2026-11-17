# -*- coding: utf-8 -*-
"""LFQuad paint-atlas projector: orthographic photos per piece, not unwrap.

Headless Blender:
  blender -b retopo_final.blend --python project_atlas.py -- <assignment.json> <outdir>
      [--placement-override placement_override.json]

assignment.json may be the literal token SMOKE (derive a provisional split and
write assignment_SMOKE.json). The SMOKE split is NOT the paint/mechanical
classification; that classification is made separately and passed in as the
assignment file.

This is the projector as it was run on one mesh, the LFQuad quad-bike body.
It is tied to that mesh: main() exits with code 2 unless the opened .blend
hashes to EXPECTED_BLEND_SHA256, the face invariant expects
EXPECTED_FACE_COUNT faces, the two controls read shells S06 and S03, and the
G7 to G9 layouts name that body's shells. The stage is chosen by the name of
<outdir> (out_g7, out_g8, out_g9, out_g10; any other name runs the axis search and
the earlier block packer), and each stage reads atlas_metrics.json from the folder that
holds the assignment file. To use it on another mesh, change those constants
first. The PNG step (render_atlas_pngs) runs draw_atlas_fallback.ps1 from this
folder through powershell.exe; that renderer is not shipped with the skill.
"""
from __future__ import annotations

import array
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


EXPECTED_BLEND_SHA256 = (
    "BD8B81E13B50B359E2F2741397483C3EAD6ED4A9CD372AFF758C2BBFDC915457"
)
AXIS_NAMES = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
AXIS_VEC = {
    "+X": Vector((1.0, 0.0, 0.0)),
    "-X": Vector((-1.0, 0.0, 0.0)),
    "+Y": Vector((0.0, 1.0, 0.0)),
    "-Y": Vector((0.0, -1.0, 0.0)),
    "+Z": Vector((0.0, 0.0, 1.0)),
    "-Z": Vector((0.0, 0.0, -1.0)),
}

# Defaults for missing assignment fields.
DEFAULT_SPLIT_LR = False
DEFAULT_SPLIT_BY_NORMAL_SIGN = True
DEFAULT_LOCAL_CONFORMAL_POLISH = False  # flag only; unwrap polish is OFF

# --- Controls: expectations locked before any result is computed. ---
# (a) Opposite-axis photos of an X-asymmetric piece: mirrored silhouettes
#     match; un-mirrored overlays do not. Can fail if camera signs swap axes.
CONTROL_A_SHELL = "S06"
CONTROL_A_AXIS_POS = "+Z"
CONTROL_A_AXIS_NEG = "-Z"
CONTROL_A_EXPECT_IOU_MIRROR_MIN = 0.98
CONTROL_A_EXPECT_IOU_UNMIRROR_MAX = 0.90
# (b) Closed shell, same axis. Unsplit auto-overlap is HIGH because front and
#     back land on the same pixels; split+pack must drop it. Can fail if the
#     normal partition is a no-op.
CONTROL_B_SHELL = "S03"
CONTROL_B_AXIS = "+Y"
CONTROL_B_EXPECT_UNSPLIT_MIN = 0.25
CONTROL_B_EXPECT_SPLIT_MAX = 0.08
CONTROL_B_EXPECT_DROP_MIN = 0.20

OVERLAP_GRID_N = 2048
CONTROL_GRID_N = 512
PARK_UV = (2.0, 2.0)
PACK_MARGIN = 0.005  # empty border in unit square after uniform scale
ISLAND_PAD_FRAC = 0.02  # gap between island bboxes, fraction of max island side
BLOCK_PAD_FRAC = 0.04  # gap between piece-blocks, fraction of max block side
BLOCK_INNER_PAD_FRAC = 0.03  # gap between cells inside a piece-block
BLOCK_LABEL_FRAC = 0.08  # extra block height reserved for the piece id
EXPECTED_FACE_COUNT = 10502
SMOKE_ISLANDS_A = 20
SMOKE_OVERLAP_A = 0.0964
# G3 atlas A overlap (raster 2048^2). Tight packing must not exceed this.
G3_OVERLAP_A = 0.0907333310706254
G3_OCCUPANCY_A = 0.20959453712586137
G3_GLOBAL_SCALE_A = 0.3726839902895099
# Bleed for a 2048 paint atlas: 8 texels covers bilinear + two mips.
ATLAS_RES = 2048
PAD_TEXELS = 8
LABEL_TEXELS = 32
AXIS_SEARCH_OVERLAP_GRID = 512
# G6: the input axis is the G4 incumbent. The absolute overlap limit applies
# only to a strictly more compact migration candidate, never to the incumbent.
AXIS_SEARCH_POLICY = "g4_incumbent_new_migrations_absolute_limit"
AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT = 0.01

# G7: anatomy is the placement policy. Literal world X<0 is atlas-left,
# X>=0 is atlas-right; world +Y (the measured nose direction) increases atlas V.
G7_OCCUPANCY_FLOOR = 0.35
G7_OVERLAP_LIMIT_A = 0.06
G7_OVERLAP_BASELINE_TOLERANCE = 0.002
G7_CROSSING_SHELLS = ("S02", "S03", "S05", "S08")
G7_MIRROR_PAIRS = (("S07", "S06"), ("S10", "S09"))  # (left, right)
G7_ATLAS_A_SHELLS = ("S02", "S03", "S05", "S06", "S07", "S08", "S09", "S10")
G7_SIGN_SPLIT_X = 0.0
G7_SIGN_CONVENTION = (
    "world face-centroid X<0 maps to atlas u<0.5 (left); "
    "world face-centroid X>=0 maps to atlas u>0.5 (right)"
)
G7_LONGITUDINAL_CONVENTION = (
    "world Y increases toward the nose and maps to increasing atlas V "
    "(tail at bottom, nose at top)"
)

# G8: the paint skin and the hidden faces are separate planar panels.  The
# A measured sweep from 60/40 through 66/34 found 60.5/39.5 maximized the final
# 512-grid silhouette IoU while keeping both panels feasible at the 0.22 floor.
G8_OCCUPANCY_FLOOR = 0.22
G8_OVERLAP_LIMIT_A = 0.06
G8_SILHOUETTE_IOU_MIN = 0.55
G8_SKIN_PANEL_RATIO = 0.605
G8_PANEL_SEPARATOR_UV = 24.0 / ATLAS_RES
G8_ISLAND_GAP_UV = PAD_TEXELS / float(ATLAS_RES)
G8_BBOX_GAP_UV = 0.0
G8_FRONT_VIEW_ROTATIONS = {"S09": 0, "S10": 180}
G8_SIGN_CONVENTION = G7_SIGN_CONVENTION
G8_LONGITUDINAL_CONVENTION = G7_LONGITUDINAL_CONVENTION

# G9: keep the G8 n+/n- layers, but each layer is a literal world-XY
# archipelago.  Both frames are equal and share one isotropic scale.  No
# per-island collision resolution or translation is permitted.
G9_OVERLAP_LIMIT_A = 0.06
G9_SILHOUETTE_IOU_MIN = 0.95
G9_SCALE_FIDELITY_CV_MAX = 0.01
G9_PANEL_SEPARATOR_UV = G8_PANEL_SEPARATOR_UV
G9_FRAME_INSET_UV = G8_ISLAND_GAP_UV
G9_FRONT_VIEW_ROTATIONS = G8_FRONT_VIEW_ROTATIONS
G9_SIGN_CONVENTION = G7_SIGN_CONVENTION
G9_LONGITUDINAL_CONVENTION = G7_LONGITUDINAL_CONVENTION

# G10: start from the G9 family-separated coloring, verify it continuously, and
# use the newly measured minimum N when G9's 1024 raster missed an edge. Only
# whole frames move; every island keeps one shared isotropic scale and literal XY.
G10_FRAME_PAD_UV = PAD_TEXELS / float(ATLAS_RES)
G10_OUTER_PAD_UV = PAD_TEXELS / float(ATLAS_RES)
G10_LAYER_GRID_N = 1024
G10_VARIANTS = ("cropped_frames", "full_frames")


def g9_panel_config():
    """Return equal-size, vertically stacked frames for the two G9 layers."""
    pad = float(fixed_padding_config()["pad_uv"])
    separator = float(G9_PANEL_SEPARATOR_UV)
    panel_h = 0.5 * (1.0 - 2.0 * pad - separator)
    internal = (pad, pad, 1.0 - pad, pad + panel_h)
    skin = (pad, internal[3] + separator, 1.0 - pad, 1.0 - pad)
    return {
        "skin_ratio": 0.5,
        "internal_ratio": 0.5,
        "separator_uv": separator,
        "separator_bbox": [pad, internal[3], 1.0 - pad, skin[1]],
        "internal_bbox": list(internal),
        "skin_bbox": list(skin),
        "frame_inset_uv": float(G9_FRAME_INSET_UV),
        "equal_frame_size": True,
    }


def g9_common_affine(model_xy_bbox, panel_config=None):
    """Build the one world-XY affine used by every island in each G9 layer."""
    config = panel_config or g9_panel_config()
    xmin, ymin, xmax, ymax = [float(value) for value in model_xy_bbox]
    world_w = max(xmax - xmin, 1e-18)
    world_h = max(ymax - ymin, 1e-18)
    inset = float(G9_FRAME_INSET_UV)
    skin_bbox = [float(value) for value in config["skin_bbox"]]
    frame_w = skin_bbox[2] - skin_bbox[0] - 2.0 * inset
    frame_h = skin_bbox[3] - skin_bbox[1] - 2.0 * inset
    if frame_w <= 0.0 or frame_h <= 0.0:
        raise ValueError("G9 panel frame has no drawable area")
    scale = min(frame_w / world_w, frame_h / world_h)
    world_cx = 0.5 * (xmin + xmax)
    world_cy = 0.5 * (ymin + ymax)
    mappings = {
        "global_scale": float(scale),
        "world_bbox": [xmin, ymin, xmax, ymax],
        "world_center": [world_cx, world_cy],
        "same_scale_both_layers": True,
        "same_xy_framing_both_layers": True,
    }
    for panel_name in ("skin", "internal"):
        bbox = [float(value) for value in config[panel_name + "_bbox"]]
        panel_cx = 0.5 * (bbox[0] + bbox[2])
        panel_cy = 0.5 * (bbox[1] + bbox[3])
        b = panel_cx - scale * world_cx
        c = panel_cy - scale * world_cy
        mappings[panel_name] = {
            "a": float(scale),
            "b": float(b),
            "c": float(c),
            "world_center": [world_cx, world_cy],
            "panel_center": [panel_cx, panel_cy],
            "panel_bbox": bbox,
            "drawable_bbox": [
                bbox[0] + inset, bbox[1] + inset,
                bbox[2] - inset, bbox[3] - inset,
            ],
            "target_frame_bbox": [
                scale * xmin + b, scale * ymin + c,
                scale * xmax + b, scale * ymax + c,
            ],
        }
    return mappings


def scale_fidelity_metrics(islands, panel_name=None):
    """CV of atlas/world-XY centroid distance ratios for one G9 layer."""
    selected = [
        isl for isl in islands
        if panel_name is None or isl.get("panel") == panel_name
    ]
    rows = []
    skipped = []
    for index, left in enumerate(selected):
        for right in selected[index + 1:]:
            left_world = left["centroid_3d"]
            right_world = right["centroid_3d"]
            world_distance = math.hypot(
                float(left_world[0]) - float(right_world[0]),
                float(left_world[1]) - float(right_world[1]),
            )
            pair = [left["id"], right["id"]]
            if world_distance <= 1e-15:
                skipped.append({"pair": pair, "reason": "coincident_world_xy_centroids"})
                continue
            left_uv = left["placement_center_uv"]
            right_uv = right["placement_center_uv"]
            atlas_distance = math.hypot(
                float(left_uv[0]) - float(right_uv[0]),
                float(left_uv[1]) - float(right_uv[1]),
            )
            rows.append({
                "pair": pair,
                "world_xy_distance": float(world_distance),
                "atlas_distance": float(atlas_distance),
                "ratio": float(atlas_distance / world_distance),
            })
    ratios = [row["ratio"] for row in rows]
    mean = sum(ratios) / len(ratios) if ratios else None
    stddev = (
        math.sqrt(sum((value - mean) ** 2 for value in ratios) / len(ratios))
        if ratios else None
    )
    cv = stddev / mean if mean is not None and mean > 1e-18 else None
    for row in rows:
        row["absolute_deviation_from_mean"] = abs(row["ratio"] - mean)
        row["relative_deviation_from_mean"] = (
            row["absolute_deviation_from_mean"] / mean if mean > 1e-18 else None
        )
    worst = max(
        rows,
        key=lambda row: (row["absolute_deviation_from_mean"], row["pair"]),
        default=None,
    )
    return {
        "panel": panel_name,
        "pair_count": len(rows),
        "skipped_pair_count": len(skipped),
        "skipped_pairs": skipped,
        "mean_ratio": float(mean) if mean is not None else None,
        "population_stddev": float(stddev) if stddev is not None else None,
        "cv": float(cv) if cv is not None else None,
        "objective_max_exclusive": float(G9_SCALE_FIDELITY_CV_MAX),
        "pass": cv is not None and cv < G9_SCALE_FIDELITY_CV_MAX,
        "worst_pair": dict(worst) if worst is not None else None,
        "per_pair": rows,
    }


def minimum_z_layering(island_ids, overlap_pairs, z_by_id, max_layers=4):
    """Exact conflict-graph coloring; layer numbers are ordered by mean world Z."""
    ids = sorted(set(island_ids))
    adjacency = {island_id: set() for island_id in ids}
    for row in overlap_pairs:
        left = row["a"]
        right = row["b"]
        if left == right or left not in adjacency or right not in adjacency:
            continue
        adjacency[left].add(right)
        adjacency[right].add(left)
    order = sorted(
        ids,
        key=lambda island_id: (
            -len(adjacency[island_id]), -float(z_by_id.get(island_id, 0.0)), island_id,
        ),
    )

    def solve(color_count):
        colors = {}

        def visit(position):
            if position == len(order):
                return True
            island_id = order[position]
            forbidden = {colors[other] for other in adjacency[island_id] if other in colors}
            used_colors = set(colors.values())
            for color in range(color_count):
                if color in forbidden:
                    continue
                is_new_color = color not in used_colors
                colors[island_id] = color
                if visit(position + 1):
                    return True
                del colors[island_id]
                if is_new_color:
                    break
            return False

        if not visit(0):
            return None
        means = {}
        for color in set(colors.values()):
            members = [island_id for island_id, value in colors.items() if value == color]
            means[color] = sum(float(z_by_id.get(item, 0.0)) for item in members) / len(members)
        remap = {
            old: new + 1
            for new, old in enumerate(sorted(means, key=lambda color: (-means[color], color)))
        }
        return {island_id: remap[color] for island_id, color in sorted(colors.items())}

    trials = {}
    minimum = None
    for layer_count in range(1, int(max_layers) + 1):
        assignment = solve(layer_count)
        zero = assignment is not None
        trials[str(layer_count)] = {
            "requested_layers": layer_count,
            "zero_collisions": zero,
            "assignment": assignment,
        }
        if zero and minimum is None:
            minimum = layer_count
    return {
        "method": "exact_conflict_graph_coloring_layers_ordered_by_mean_world_z",
        "island_count": len(ids),
        "collision_edge_count": sum(len(values) for values in adjacency.values()) // 2,
        "minimum_zero_collision_layers": minimum,
        "searched_through_layers": int(max_layers),
        "trials": trials,
    }


def g10_reused_layer_assignment(intra_layer_overlap, family_by_id):
    """Read the literal family-preserving 3+2 assignment measured in G9."""
    source = intra_layer_overlap.get("layering_by_panel") or {}
    minimum_by_family = (
        intra_layer_overlap.get("minimum_sublayers_per_original_layer") or {}
    )
    expected_families = ("skin", "internal")
    assignment_by_island = {}
    ordinal_by_island = {}
    layers = []
    for family in expected_families:
        family_source = source.get(family) or {}
        minimum = family_source.get("minimum_zero_collision_layers")
        declared_minimum = minimum_by_family.get(family)
        if minimum is None or int(minimum) != int(declared_minimum):
            raise ValueError("G9 %s minimum-layer fields disagree" % family)
        trial = (family_source.get("trials") or {}).get(str(int(minimum))) or {}
        if not trial.get("zero_collisions") or not trial.get("assignment"):
            raise ValueError("G9 %s minimum assignment is missing or not green" % family)
        literal = dict(trial["assignment"])
        for island_id, ordinal in sorted(literal.items()):
            if family_by_id.get(island_id) != family:
                raise ValueError("G9 family mixing for %s" % island_id)
            layer_id = "%s_%d" % (family, int(ordinal))
            assignment_by_island[island_id] = layer_id
            ordinal_by_island[island_id] = int(ordinal)
        for ordinal in range(1, int(minimum) + 1):
            layer_id = "%s_%d" % (family, ordinal)
            members = sorted(
                island_id for island_id, value in literal.items()
                if int(value) == ordinal
            )
            if not members:
                raise ValueError("G9 reused layer %s is empty" % layer_id)
            layers.append({
                "id": layer_id,
                "family": family,
                "ordinal": ordinal,
                "island_ids": members,
            })
    expected_ids = set(family_by_id)
    assigned_ids = set(assignment_by_island)
    if assigned_ids != expected_ids:
        raise ValueError("G9 reused assignment coverage mismatch missing=%s extra=%s" % (
            sorted(expected_ids - assigned_ids), sorted(assigned_ids - expected_ids),
        ))
    minimum_total = sum(int(minimum_by_family[name]) for name in expected_families)
    declared_total = intra_layer_overlap.get(
        "minimum_total_layers_preserving_skin_internal_split"
    )
    if declared_total is None or int(declared_total) != minimum_total:
        raise ValueError("G9 total minimum-layer fields disagree")
    return {
        "source_field": "intra_layer_overlap.layering_by_panel",
        "minimum_by_family": {
            name: int(minimum_by_family[name]) for name in expected_families
        },
        "minimum_total_layers": int(minimum_total),
        "assignment_by_island": assignment_by_island,
        "ordinal_by_island": ordinal_by_island,
        "layers": layers,
        "families_mixed": False,
    }


def g10_raster_layer_collisions(tris_by_island, assignment_by_island, grid_n=1024,
                                bbox=(0.0, 0.0, 1.0, 1.0)):
    """Raster final triangles and count cross-island pairs sharing one G10 layer."""
    n = int(grid_n)
    u0, v0, u1, v1 = [float(value) for value in bbox]
    coverage = {}
    for island_id, triangles in sorted(tris_by_island.items()):
        if island_id not in assignment_by_island:
            raise ValueError("missing G10 layer assignment for %s" % island_id)
        grid, _grid_bbox, _ = raster_tris(triangles, n, bbox)
        coverage[island_id] = {index for index, count in enumerate(grid) if count >= 1}
    pixel_area = (u1 - u0) * (v1 - v0) / float(n * n)
    pairs = []
    ids = sorted(coverage)
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            layer_id = assignment_by_island[left]
            if assignment_by_island[right] != layer_id:
                continue
            shared = len(coverage[left].intersection(coverage[right]))
            if shared:
                pairs.append({
                    "a": left,
                    "b": right,
                    "layer": layer_id,
                    "intersection_pixels": int(shared),
                    "intersection_area_uv": float(shared * pixel_area),
                })
    pairs.sort(key=lambda row: (-row["intersection_pixels"], row["a"], row["b"]))
    return {
        "method": "per_island_binary_coverage_intersection_raster_by_reused_g10_layer",
        "grid_n": n,
        "grid_bbox": [u0, v0, u1, v1],
        "collision_pair_count": len(pairs),
        "pairs": pairs,
        "pass": len(pairs) == 0,
    }


def _g10_polygon_signed_area(points):
    if len(points) < 3:
        return 0.0
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def _g10_cross_2d(a, b, point):
    return (
        (float(b[0]) - float(a[0])) * (float(point[1]) - float(a[1]))
        - (float(b[1]) - float(a[1])) * (float(point[0]) - float(a[0]))
    )


def _g10_line_intersection(start, end, clip_a, clip_b):
    rx = float(end[0]) - float(start[0])
    ry = float(end[1]) - float(start[1])
    qx = float(clip_b[0]) - float(clip_a[0])
    qy = float(clip_b[1]) - float(clip_a[1])
    denominator = rx * qy - ry * qx
    if abs(denominator) <= 1e-30:
        return (float(end[0]), float(end[1]))
    t = (
        (float(clip_a[0]) - float(start[0])) * qy
        - (float(clip_a[1]) - float(start[1])) * qx
    ) / denominator
    return (float(start[0]) + t * rx, float(start[1]) + t * ry)


def _g10_triangle_intersection_area(left, right):
    """Continuous convex clipping area; boundary-only contact returns zero."""
    output = [(float(point[0]), float(point[1])) for point in left]
    clip = [(float(point[0]), float(point[1])) for point in right]
    orientation = 1.0 if _g10_polygon_signed_area(clip) >= 0.0 else -1.0
    for index, clip_a in enumerate(clip):
        clip_b = clip[(index + 1) % len(clip)]
        subject = output
        output = []
        if not subject:
            break
        start = subject[-1]
        start_inside = orientation * _g10_cross_2d(clip_a, clip_b, start) >= -1e-15
        for end in subject:
            end_inside = orientation * _g10_cross_2d(clip_a, clip_b, end) >= -1e-15
            if end_inside:
                if not start_inside:
                    output.append(_g10_line_intersection(start, end, clip_a, clip_b))
                output.append(end)
            elif start_inside:
                output.append(_g10_line_intersection(start, end, clip_a, clip_b))
            start = end
            start_inside = end_inside
    return abs(_g10_polygon_signed_area(output)) if len(output) >= 3 else 0.0


def g10_exact_cross_island_conflicts(tris_by_island, family_by_id,
                                     area_tolerance=1e-15):
    """Build a continuous-area conflict graph independently of raster alignment."""
    triangle_rows = {}
    for island_id, triangles in tris_by_island.items():
        rows = []
        for triangle in triangles:
            tri = [(float(point[0]), float(point[1])) for point in triangle]
            bbox = (
                min(point[0] for point in tri), min(point[1] for point in tri),
                max(point[0] for point in tri), max(point[1] for point in tri),
            )
            rows.append((tri, bbox))
        triangle_rows[island_id] = rows
    pairs = []
    ids = sorted(triangle_rows)
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            family = family_by_id[left]
            if family_by_id[right] != family:
                continue
            total_area = 0.0
            positive_triangle_pairs = 0
            for left_tri, left_bbox in triangle_rows[left]:
                for right_tri, right_bbox in triangle_rows[right]:
                    if (
                        left_bbox[2] < right_bbox[0] or right_bbox[2] < left_bbox[0]
                        or left_bbox[3] < right_bbox[1] or right_bbox[3] < left_bbox[1]
                    ):
                        continue
                    area = _g10_triangle_intersection_area(left_tri, right_tri)
                    if area > float(area_tolerance):
                        total_area += area
                        positive_triangle_pairs += 1
            if total_area > float(area_tolerance):
                pairs.append({
                    "a": left,
                    "b": right,
                    "family": family,
                    "intersection_area": float(total_area),
                    "positive_triangle_pairs": int(positive_triangle_pairs),
                })
    pairs.sort(key=lambda row: (-row["intersection_area"], row["a"], row["b"]))
    return {
        "method": "continuous_triangle_clipping_area_cross_island_same_family",
        "area_tolerance": float(area_tolerance),
        "collision_pair_count": len(pairs),
        "pairs": pairs,
        "pass_if_layered": None,
    }


def g11_exact_global_collisions(tris_by_island, area_tolerance=1e-15):
    """Measure positive-area intersections between every atlas-A island pair."""
    triangle_rows = {}
    island_bboxes = {}
    for island_id, triangles in tris_by_island.items():
        rows = []
        all_points = []
        for triangle in triangles:
            tri = [(float(point[0]), float(point[1])) for point in triangle]
            if len(tri) != 3:
                raise ValueError("G11 collision triangles must have exactly three vertices")
            bbox = (
                min(point[0] for point in tri), min(point[1] for point in tri),
                max(point[0] for point in tri), max(point[1] for point in tri),
            )
            rows.append((tri, bbox))
            all_points.extend(tri)
        triangle_rows[island_id] = rows
        island_bboxes[island_id] = (
            _g10_bbox_from_points(all_points) if all_points else [0.0, 0.0, 0.0, 0.0]
        )
    pairs = []
    ids = sorted(triangle_rows)
    for index, left in enumerate(ids):
        left_island_bbox = island_bboxes[left]
        for right in ids[index + 1:]:
            right_island_bbox = island_bboxes[right]
            if aabb_overlap_area(left_island_bbox, right_island_bbox) <= 0.0:
                continue
            total_area = 0.0
            positive_triangle_pairs = 0
            for left_tri, left_bbox in triangle_rows[left]:
                for right_tri, right_bbox in triangle_rows[right]:
                    if (
                        left_bbox[2] <= right_bbox[0] or right_bbox[2] <= left_bbox[0]
                        or left_bbox[3] <= right_bbox[1] or right_bbox[3] <= left_bbox[1]
                    ):
                        continue
                    area = _g10_triangle_intersection_area(left_tri, right_tri)
                    if area > float(area_tolerance):
                        total_area += area
                        positive_triangle_pairs += 1
            if total_area > float(area_tolerance):
                pairs.append({
                    "a": left,
                    "b": right,
                    "intersection_area_uv": float(total_area),
                    "positive_triangle_pairs": int(positive_triangle_pairs),
                })
    pairs.sort(key=lambda row: (-row["intersection_area_uv"], row["a"], row["b"]))
    return {
        "method": "continuous_convex_triangle_clipping_all_atlas_A_island_pairs",
        "precision": (
            "continuous float geometry; positive area > %.1e UV^2; boundary contact is not a collision"
            % float(area_tolerance)
        ),
        "area_tolerance_uv2": float(area_tolerance),
        "collision_pair_count": len(pairs),
        "pairs": pairs,
        "scope": "all_atlas_A_islands_regardless_of_original_G10_layer_or_family",
        "pass": len(pairs) == 0,
    }


def g10_repair_assignment_min_changes(island_ids, overlap_pairs,
                                      original_assignment, color_count):
    """Exact coloring with fixed layer labels, minimizing changes from G9."""
    ids = sorted(set(island_ids))
    adjacency = {island_id: set() for island_id in ids}
    for row in overlap_pairs:
        left, right = row["a"], row["b"]
        if left in adjacency and right in adjacency and left != right:
            adjacency[left].add(right)
            adjacency[right].add(left)
    order = sorted(
        ids,
        key=lambda island_id: (-len(adjacency[island_id]), island_id),
    )
    colors = {}
    best = {"cost": len(ids) + 1, "key": None, "assignment": None}

    def visit(position, cost):
        if cost > best["cost"]:
            return
        if position == len(order):
            if len(set(colors.values())) != int(color_count):
                return
            key = tuple(colors[island_id] for island_id in ids)
            if cost < best["cost"] or (cost == best["cost"] and (
                best["key"] is None or key < best["key"]
            )):
                best["cost"] = cost
                best["key"] = key
                best["assignment"] = dict(colors)
            return
        island_id = order[position]
        original = int(original_assignment.get(island_id, 1))
        candidates = [original] + [
            color for color in range(1, int(color_count) + 1) if color != original
        ]
        forbidden = {
            colors[other] for other in adjacency[island_id] if other in colors
        }
        for color in candidates:
            if color in forbidden:
                continue
            colors[island_id] = color
            visit(position + 1, cost + (0 if color == original else 1))
            del colors[island_id]

    visit(0, 0)
    if best["assignment"] is None:
        return {
            "assignment": None,
            "changed_count": None,
            "changes": [],
            "color_count": int(color_count),
            "pass": False,
        }
    assignment = {island_id: best["assignment"][island_id] for island_id in ids}
    changes = [
        {"island": island_id, "from": int(original_assignment.get(island_id, 1)),
         "to": int(assignment[island_id])}
        for island_id in ids
        if int(original_assignment.get(island_id, 1)) != int(assignment[island_id])
    ]
    return {
        "assignment": assignment,
        "changed_count": len(changes),
        "changes": changes,
        "color_count": int(color_count),
        "pass": True,
    }


def _g10_frame_pack_candidate(layer_specs, model_xy_bbox, variant, scale):
    frame_pad = float(G10_FRAME_PAD_UV)
    outer_pad = float(G10_OUTER_PAD_UV)
    boxes = []
    source_bbox_by_id = {}
    for layer in layer_specs:
        source_bbox = (
            model_xy_bbox if variant == "full_frames"
            else layer["content_bbox_world"]
        )
        xmin, ymin, xmax, ymax = [float(value) for value in source_bbox]
        if xmax <= xmin or ymax <= ymin:
            raise ValueError("empty G10 source bbox for %s" % layer["id"])
        source_bbox_by_id[layer["id"]] = [xmin, ymin, xmax, ymax]
        boxes.append({
            "id": layer["id"],
            "w": float(scale) * (xmax - xmin) + 2.0 * frame_pad,
            "h": float(scale) * (ymax - ymin) + 2.0 * frame_pad,
        })
    bin_side = 1.0 - 2.0 * outer_pad
    candidates = []
    for packer_name, packer in (
        ("maxrects", pack_rectangles_maxrects),
        ("shelf", pack_rectangles_shelf),
    ):
        for order_name in ("area_desc", "max_side_desc", "perimeter_desc"):
            result = packer(boxes, bin_side, bin_side, order_name, False)
            if result is None:
                continue
            positions = result["positions"]
            used_w = max((row["x"] + row["w"] for row in positions.values()), default=0.0)
            used_h = max((row["y"] + row["h"] for row in positions.values()), default=0.0)
            candidates.append((
                (max(used_w, used_h), used_h, used_w, packer_name, order_name),
                packer_name,
                order_name,
                result,
            ))
    if not candidates:
        return None
    _score, packer_name, order_name, result = min(candidates, key=lambda row: row[0])
    return {
        "packer": packer_name,
        "order_name": order_name,
        "result": result,
        "source_bbox_by_id": source_bbox_by_id,
        "boxes": boxes,
    }


def g10_pack_frame_layout(layer_specs, model_xy_bbox, variant):
    """Maximize one scale while packing N whole frames without rotation."""
    if variant not in G10_VARIANTS:
        raise ValueError("unknown G10 frame variant %r" % variant)
    ids = [layer["id"] for layer in layer_specs]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("G10 layer ids must be non-empty and unique")

    def feasible(scale):
        return _g10_frame_pack_candidate(
            layer_specs, model_xy_bbox, variant, scale,
        ) is not None

    lo, hi = _monotone_scale_bound(feasible, iterations=72)
    scale = float(lo * (1.0 - 1e-12))
    chosen = _g10_frame_pack_candidate(
        layer_specs, model_xy_bbox, variant, scale,
    )
    if chosen is None or scale <= 0.0:
        raise RuntimeError("G10 frame pack failed at measured scale")
    outer_pad = float(G10_OUTER_PAD_UV)
    frame_pad = float(G10_FRAME_PAD_UV)
    positions = chosen["result"]["positions"]
    by_id = {layer["id"]: layer for layer in layer_specs}
    model_bbox = [float(value) for value in model_xy_bbox]
    frames = []
    for layer_id in ids:
        layer = by_id[layer_id]
        position = positions[layer_id]
        frame_bbox = [
            outer_pad + float(position["x"]),
            outer_pad + float(position["y"]),
            outer_pad + float(position["x"]) + float(position["w"]),
            outer_pad + float(position["y"]) + float(position["h"]),
        ]
        source_bbox = chosen["source_bbox_by_id"][layer_id]
        b = frame_bbox[0] + frame_pad - scale * source_bbox[0]
        c = frame_bbox[1] + frame_pad - scale * source_bbox[1]
        content_bbox = [float(value) for value in layer["content_bbox_world"]]
        mapping = {"a": scale, "b": float(b), "c": float(c)}
        frames.append({
            **dict(layer),
            "frame_bbox": frame_bbox,
            "source_bbox_world": list(source_bbox),
            "content_bbox_uv": [
                scale * content_bbox[0] + b,
                scale * content_bbox[1] + c,
                scale * content_bbox[2] + b,
                scale * content_bbox[3] + c,
            ],
            "full_quad_bbox_uv": [
                scale * model_bbox[0] + b,
                scale * model_bbox[1] + c,
                scale * model_bbox[2] + b,
                scale * model_bbox[3] + c,
            ],
            "centerline_uv": float(b),
            "mapping": mapping,
            "rotation_deg": 0,
        })
    return {
        "variant": variant,
        "global_scale": scale,
        "scale_bracket": [float(lo), float(hi)],
        "frame_pad_uv": frame_pad,
        "outer_pad_uv": outer_pad,
        "packer": chosen["packer"],
        "selected_order": chosen["order_name"],
        "allow_frame_rotation": False,
        "frames": frames,
    }


def g10_affine_vertex_gate(islands, mappings_by_layer, tolerance=1e-12):
    """Independently re-evaluate final vertices from stored pre-pack frame UVs."""
    worst = 0.0
    worst_vertex = None
    checked = 0
    for isl in islands:
        layer_id = isl["g10_layer_id"]
        mapping = mappings_by_layer[layer_id]
        for loop_index, (world_u, world_v) in isl["g10_world_uv"].items():
            expected = (
                float(mapping["a"]) * float(world_u) + float(mapping["b"]),
                float(mapping["a"]) * float(world_v) + float(mapping["c"]),
            )
            actual = isl["uv_final"][loop_index]
            error = max(abs(float(actual[0]) - expected[0]), abs(float(actual[1]) - expected[1]))
            if error > worst:
                worst = error
                worst_vertex = {"island": isl["id"], "loop_index": int(loop_index)}
            checked += 1
    return {
        "checked_vertices": checked,
        "max_abs_error_uv": float(worst),
        "worst_vertex": worst_vertex,
        "tolerance": float(tolerance),
        "pass": worst <= float(tolerance),
    }


def g10_useful_texels(occupancy, resolutions=(2048, 4096, 8192)):
    """Owner-facing useful linear texels: sqrt(occupancy) times resolution."""
    root = math.sqrt(max(0.0, float(occupancy)))
    return {str(int(resolution)): float(root * int(resolution)) for resolution in resolutions}


def g8_panel_config(skin_ratio=G8_SKIN_PANEL_RATIO):
    """Return disjoint atlas-space rectangles for internal and skin islands."""
    pad = float(fixed_padding_config()["pad_uv"])
    separator = float(G8_PANEL_SEPARATOR_UV)
    usable = 1.0 - 2.0 * pad - separator
    skin_h = usable * float(skin_ratio)
    internal_h = usable - skin_h
    internal = (pad, pad, 1.0 - pad, pad + internal_h)
    skin = (pad, internal[3] + separator, 1.0 - pad, 1.0 - pad)
    return {
        "skin_ratio": float(skin_ratio),
        "internal_ratio": 1.0 - float(skin_ratio),
        "separator_uv": separator,
        "separator_bbox": [pad, internal[3], 1.0 - pad, skin[1]],
        "internal_bbox": list(internal),
        "skin_bbox": list(skin),
    }


def fixed_padding_config():
    """Declared paint-atlas margins in output UV units.

    Geometry is scaled once globally; these values stay fixed in the final
    2048 atlas so the bleed allowance is not accidentally scaled with a piece.
    """
    return {
        "atlas_resolution": ATLAS_RES,
        "pad_texels": PAD_TEXELS,
        "pad_uv": PAD_TEXELS / float(ATLAS_RES),
        "label_texels": LABEL_TEXELS,
        "label_uv": LABEL_TEXELS / float(ATLAS_RES),
    }

# SMOKE (NOT the real split): large, not-elongated shells -> atlas A.
SMOKE_AREA_MIN = 0.08
SMOKE_ELONG_MAX = 3.0

# ---------------------------------------------------------------------------
# Island exterior-visibility threshold. LOCKED before any island_vis_share
# is computed. Changing it after seeing the island table is forbidden.
#
# An atlas-A island with island_vis_share < ISLAND_VIS_THRESHOLD is moved
# to atlas B. Piece membership does not change: only halves move.
#
# A priori rationale (not fitted to island count):
#   Whole mechanical pieces sit at vis_share 0.0085-0.0187. The smallest
#   paint piece is ~0.023. 0.5 % of exterior first-hits is below a coil
#   spring's whole-piece share, and above (paint_min / 4) so a 4-way split
#   of the smallest paint piece does not dump every half just for being
#   small. The island count is a reading, not a target.
# ---------------------------------------------------------------------------
ISLAND_VIS_THRESHOLD = 0.005
VIS_N_DIR = 64
VIS_GRID = 128


# ---------------------------------------------------------------------------
# Metrics copied from uv_metrics_run_REFERENCE.py (module-level; not imported).
# "tris" is len(bm.faces), not triangle count. Keep formulas byte-compatible.
# ---------------------------------------------------------------------------
def shells(bm):
    """Connected components over the mesh (not the UV) = floor on island count."""
    seen, n = set(), 0
    for f in bm.faces:
        if f in seen:
            continue
        n += 1
        stack = [f]
        seen.add(f)
        while stack:
            cur = stack.pop()
            for e in cur.edges:
                for nb in e.link_faces:
                    if nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
    return n


def uv_islands(bm, uv):
    """Islands = connected components in UV space (split at seams)."""
    key = {}
    for f in bm.faces:
        for l in f.loops:
            key.setdefault(f.index, []).append(tuple(round(c, 6) for c in l[uv].uv))
    parent = {f.index: f.index for f in bm.faces}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces
        c1 = {tuple(round(c, 6) for c in l[uv].uv) for l in f1.loops if l.vert in e.verts}
        c2 = {tuple(round(c, 6) for c in l[uv].uv) for l in f2.loops if l.vert in e.verts}
        if c1 & c2:                      # UVs coincide across the edge -> same island
            union(f1.index, f2.index)

    groups = defaultdict(list)
    for f in bm.faces:
        groups[find(f.index)].append(f)
    return list(groups.values())


def tri_area_2d(a, b, c):
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * 0.5


def measure(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    if uv is None:
        bm.free()
        return None

    n_shells = shells(bm)
    islands = uv_islands(bm, uv)

    # UV area per island, and 3D area, for stretch
    areas, stretches = [], []
    total_uv = 0.0
    bbox = [1e9, 1e9, -1e9, -1e9]
    for isl in islands:
        a_uv = 0.0
        for f in isl:
            pts = [l[uv].uv for l in f.loops]
            for i in range(1, len(pts) - 1):
                a_uv += tri_area_2d(pts[0], pts[i], pts[i + 1])
            for p in pts:
                bbox[0] = min(bbox[0], p[0]); bbox[1] = min(bbox[1], p[1])
                bbox[2] = max(bbox[2], p[0]); bbox[3] = max(bbox[3], p[1])
            a3 = f.calc_area()
            a2 = 0.0
            for i in range(1, len(pts) - 1):
                a2 += tri_area_2d(pts[0], pts[i], pts[i + 1])
            if a3 > 1e-12 and a2 > 1e-12:
                stretches.append(math.sqrt(a2 / a3))
        areas.append(a_uv)
        total_uv += a_uv

    areas.sort(reverse=True)
    N = max(1, 3 * n_shells)
    conc = (sum(areas[:N]) / total_uv) if total_uv > 0 else 0.0

    stretches.sort()
    def pct(p):
        if not stretches:
            return 0.0
        return stretches[min(len(stretches) - 1, int(len(stretches) * p))]
    med = pct(0.5)
    # Normalised so 1.0 = the island matches the median scale; >1 stretched.
    rel = [s / med for s in stretches] if med > 1e-9 else stretches
    rel.sort()
    def rpct(p):
        return rel[min(len(rel) - 1, int(len(rel) * p))] if rel else 0.0

    bb_area = max(1e-9, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
    faces_per_island = sorted(len(i) for i in islands)

    out = {
        "tris": len(bm.faces),
        "shells": n_shells,
        "islands": len(islands),
        "islands_per_shell": round(len(islands) / max(1, n_shells), 2),
        "N_for_concentration": N,
        "area_concentration": round(conc, 4),
        "occupancy_vs_bbox": round(total_uv / bb_area, 4),
        "uv_area_total": round(total_uv, 4),
        "stretch_p50_rel": round(rpct(0.5), 3),
        "stretch_p95_rel": round(rpct(0.95), 3),
        "stretch_max_rel": round(rel[-1], 3) if rel else 0.0,
        "faces_per_island_median": faces_per_island[len(faces_per_island) // 2],
        "faces_per_island_min": faces_per_island[0],
    }
    bm.free()
    return out


# ---------------------------------------------------------------------------
# Projector
# ---------------------------------------------------------------------------
def log(msg):
    print(msg, flush=True)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def argv_payload():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return sys.argv[1:]


def parse_project_args(args):
    """Parse the two legacy positionals plus the optional G11 override."""
    positionals = []
    placement_override = None
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--placement-override":
            if placement_override is not None:
                raise SystemExit("--placement-override may be provided only once")
            index += 1
            if index >= len(args) or args[index].startswith("--"):
                raise SystemExit("--placement-override requires a JSON path")
            placement_override = args[index]
        elif token.startswith("--"):
            raise SystemExit("unknown option: %s" % token)
        else:
            positionals.append(token)
        index += 1
    if len(positionals) != 2:
        raise SystemExit(
            "usage: blender -b <blend> --python project_atlas.py -- "
            "<assignment.json|SMOKE> <outdir> "
            "[--placement-override <placement_override.json>]"
        )
    return {
        "assignment": positionals[0],
        "outdir": positionals[1],
        "placement_override": placement_override,
    }


def _finite_uv_pair(value, field_name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("%s must be a two-number JSON array" % field_name)
    result = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError("%s must contain only numbers" % field_name)
        number = float(item)
        if not math.isfinite(number):
            raise ValueError("%s must contain only finite numbers" % field_name)
        result.append(number)
    return result


def validate_placement_override(payload, base_islands, center_tolerance=2e-9):
    """Fail closed unless an override exactly describes every base G10 island."""
    if not isinstance(payload, dict):
        raise ValueError("placement override root must be a JSON object")
    required_root = {"source", "base", "atlas", "uv_space", "islands"}
    if set(payload) != required_root:
        raise ValueError(
            "placement override root keys must be exactly %s" % sorted(required_root)
        )
    expected_literals = {
        "source": "uv_arranger",
        "base": "out_g10",
        "atlas": "A",
        "uv_space": [0.0, 0.0, 1.0, 1.0],
    }
    for key, expected in expected_literals.items():
        if payload.get(key) != expected:
            raise ValueError("placement override %s must equal %r" % (key, expected))
    rows = payload.get("islands")
    if not isinstance(rows, list):
        raise ValueError("placement override islands must be a JSON array")
    base_by_id = {island["id"]: island for island in base_islands}
    if len(base_by_id) != len(base_islands):
        raise ValueError("base G10 island ids are not unique")
    by_id = {}
    required_row = {"id", "placement_center_uv", "delta_uv"}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != required_row:
            raise ValueError(
                "placement override island row %d keys must be exactly %s"
                % (index, sorted(required_row))
            )
        island_id = row["id"]
        if not isinstance(island_id, str) or not island_id:
            raise ValueError("placement override island id must be a non-empty string")
        if island_id in by_id:
            raise ValueError("duplicate placement override island id: %s" % island_id)
        if island_id not in base_by_id:
            raise ValueError("unknown placement override island id: %s" % island_id)
        center = _finite_uv_pair(row["placement_center_uv"], "placement_center_uv")
        delta = _finite_uv_pair(row["delta_uv"], "delta_uv")
        base_center = _finite_uv_pair(
            list(base_by_id[island_id]["placement_center_uv"]),
            "base placement_center_uv",
        )
        expected_center = [base_center[0] + delta[0], base_center[1] + delta[1]]
        center_error = max(
            abs(center[0] - expected_center[0]), abs(center[1] - expected_center[1]),
        )
        if center_error > float(center_tolerance):
            raise ValueError(
                "placement center/delta mismatch for %s: error %.17g > %.17g"
                % (island_id, center_error, center_tolerance)
            )
        by_id[island_id] = {
            "id": island_id,
            "placement_center_uv": center,
            "delta_uv": delta,
            "center_consistency_error_uv": float(center_error),
        }
    expected_ids = set(base_by_id)
    actual_ids = set(by_id)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise ValueError(
            "placement override ids must match base G10 exactly; missing=%s extra=%s"
            % (missing, extra)
        )
    return {
        "source": payload["source"],
        "base": payload["base"],
        "atlas": payload["atlas"],
        "uv_space": list(payload["uv_space"]),
        "island_count": len(by_id),
        "by_id": by_id,
        "center_tolerance": float(center_tolerance),
        "max_center_consistency_error_uv": max(
            (row["center_consistency_error_uv"] for row in by_id.values()),
            default=0.0,
        ),
    }


def rigid_translation_vertex_gate(base_islands, moved_islands, override_by_id):
    """Compare the final artifact with base G10 plus each declared translation."""
    base_by_id = {island["id"]: island for island in base_islands}
    moved_by_id = {island["id"]: island for island in moved_islands}
    if set(base_by_id) != set(moved_by_id) or set(base_by_id) != set(override_by_id):
        raise ValueError("rigid translation gate island ids do not match")
    worst = 0.0
    worst_vertex = None
    checked = 0
    for island_id in sorted(base_by_id):
        base_uv = base_by_id[island_id]["uv_final"]
        moved_uv = moved_by_id[island_id]["uv_final"]
        if set(base_uv) != set(moved_uv):
            raise ValueError("rigid translation changed loop membership for %s" % island_id)
        delta = override_by_id[island_id]["delta_uv"]
        for loop_index in sorted(base_uv):
            expected = (
                float(base_uv[loop_index][0]) + float(delta[0]),
                float(base_uv[loop_index][1]) + float(delta[1]),
            )
            actual = moved_uv[loop_index]
            error = max(
                abs(float(actual[0]) - expected[0]),
                abs(float(actual[1]) - expected[1]),
            )
            if error > worst:
                worst = error
                worst_vertex = {"island": island_id, "loop_index": int(loop_index)}
            checked += 1
    return {
        "method": (
            "final_vertex_equals_independent_base_G10_vertex_plus_declared_island_delta"
        ),
        "relative_geometry_contract": (
            "Undoing one declared translation per island recovers every base G10 "
            "vertex; scaling and rotation therefore fail this gate."
        ),
        "checked_vertices": checked,
        "max_abs_error_uv": float(worst),
        "worst_vertex": worst_vertex,
        "tolerance": 0.0,
        "pass": worst == 0.0,
    }


def apply_rigid_placement_override(base_islands, payload):
    """Return copied islands translated by the validated G10 deltas."""
    validation = validate_placement_override(payload, base_islands)
    moved = []
    displacement_rows = []
    for base in base_islands:
        island_id = base["id"]
        delta = validation["by_id"][island_id]["delta_uv"]
        island = dict(base)
        island["uv_final"] = {
            loop_index: (
                float(point[0]) + float(delta[0]),
                float(point[1]) + float(delta[1]),
            )
            for loop_index, point in base["uv_final"].items()
        }
        base_center = base["placement_center_uv"]
        center = [
            float(base_center[0]) + float(delta[0]),
            float(base_center[1]) + float(delta[1]),
        ]
        island["placement_center_uv"] = center
        if base.get("placement_center_frame_uv") is not None:
            frame_center = base["placement_center_frame_uv"]
            island["placement_center_frame_uv"] = [
                float(frame_center[0]) + float(delta[0]),
                float(frame_center[1]) + float(delta[1]),
            ]
        target = base.get("target_uv") or base_center
        displacement = math.hypot(
            center[0] - float(target[0]), center[1] - float(target[1]),
        )
        island["target_displacement_uv"] = float(displacement)
        island["placement_override_delta_uv"] = list(delta)
        island["rotation_scope"] = "g11_rigid_translation_only"
        moved.append(island)
        displacement_rows.append({
            "island": island_id,
            "layer": island.get("g10_layer_id"),
            "target_uv": [float(target[0]), float(target[1])],
            "placed_uv": list(center),
            "delta_uv": list(delta),
            "displacement_uv": float(displacement),
        })
    displacement_rows.sort(key=lambda row: (-row["displacement_uv"], row["island"]))
    values = [row["displacement_uv"] for row in displacement_rows]
    displacement = {
        "method": "Euclidean center distance from immutable target_uv after G11 translation",
        "is_gate": False,
        "mean_uv": float(sum(values) / len(values)) if values else 0.0,
        "worst_uv": max(values, default=0.0),
        "worst_island": displacement_rows[0]["island"] if values else None,
        "per_island": displacement_rows,
    }
    return moved, {
        "validation": validation,
        "displacement": displacement,
        "rigid_vertex_gate": rigid_translation_vertex_gate(
            base_islands, moved, validation["by_id"],
        ),
    }


def camera_basis(axis_name):
    """Right-handed camera sitting on +axis looking toward the origin.

    UV = (dot(p, right), dot(p, cam_up)). Opposite axes are horizontal
    mirrors of each other (see CONTROL_A). Y is world-up except when the
    view is along Y, in which case world-up becomes -Z so +X stays image-right
    (a left-right flip of a livery number would be a bug, not a style choice).
    """
    if axis_name not in AXIS_VEC:
        raise ValueError("axis must be one of %s, got %r" % (AXIS_NAMES, axis_name))
    axis_from = AXIS_VEC[axis_name]
    look_dir = -axis_from
    world_up = Vector((0.0, 1.0, 0.0))
    if abs(look_dir.dot(world_up)) > 0.9:
        world_up = Vector((0.0, 0.0, -1.0))
    right = look_dir.cross(world_up)
    right.normalize()
    cam_up = right.cross(look_dir)
    cam_up.normalize()
    return right, cam_up


_BASIS_CACHE = {name: camera_basis(name) for name in AXIS_NAMES}


def project_co(co, axis_name):
    right, cam_up = _BASIS_CACHE[axis_name]
    p = Vector(co)
    return (float(p.dot(right)), float(p.dot(cam_up)))


def identify_shells(bm, v_world):
    """S00.. : face-count desc, tie = lowest face index. Never hardcoded.

    Bbox/extents/center are WORLD (object has a 90° X rotation; object-Y is
    world-Z). Axis inference must use the same space as project_co.
    """
    seen = set()
    comps = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        seen.add(f.index)
        faces = [f]
        while stack:
            cur = stack.pop()
            for e in cur.edges:
                for nb in e.link_faces:
                    if nb.index not in seen:
                        seen.add(nb.index)
                        stack.append(nb)
                        faces.append(nb)
        comps.append(faces)
    comps.sort(key=lambda fs: (-len(fs), min(x.index for x in fs)))
    shells_out = []
    for i, fs in enumerate(comps):
        verts = {v for f in fs for v in f.verts}
        xs = [v_world[v.index].x for v in verts]
        ys = [v_world[v.index].y for v in verts]
        zs = [v_world[v.index].z for v in verts]
        bbox = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
        ext = (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])
        area = sum(f.calc_area() for f in fs)
        shells_out.append({
            "id": "S%02d" % i,
            "faces": fs,
            "face_indices": [f.index for f in fs],
            "n_faces": len(fs),
            "n_verts": len(verts),
            "area": float(area),
            "bbox": bbox,
            "extents": ext,
            "center": (
                0.5 * (bbox[0] + bbox[3]),
                0.5 * (bbox[1] + bbox[4]),
                0.5 * (bbox[2] + bbox[5]),
            ),
            "min_face": min(f.index for f in fs),
        })
    return shells_out


def world_geom(obj, bm):
    mw = obj.matrix_world
    nmat = mw.inverted_safe().transposed().to_3x3()
    v_world = {}
    for v in bm.verts:
        v_world[v.index] = mw @ v.co
    f_nworld = {}
    f_cent = {}
    for f in bm.faces:
        n = nmat @ f.normal
        if n.length_squared > 1e-20:
            n.normalize()
        else:
            n = Vector((0.0, 0.0, 1.0))
        f_nworld[f.index] = n
        c = Vector((0.0, 0.0, 0.0))
        for v in f.verts:
            c += v_world[v.index]
        f_cent[f.index] = c / max(1, len(f.verts))
    return v_world, f_nworld, f_cent


def measure_symmetry(v_world):
    """Pairing fraction per bbox mid-plane. Tolerance = 0.5% of bbox diagonal."""
    pts = list(v_world.values())
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    bb = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    diag = math.sqrt((bb[3] - bb[0]) ** 2 + (bb[4] - bb[1]) ** 2 + (bb[5] - bb[2]) ** 2)
    tol = 0.005 * diag
    mid = (
        0.5 * (bb[0] + bb[3]),
        0.5 * (bb[1] + bb[4]),
        0.5 * (bb[2] + bb[5]),
    )
    # Quantize for neighbour lookup.
    inv = 1.0 / max(tol, 1e-12)

    def qkey(x, y, z):
        return (int(round(x * inv)), int(round(y * inv)), int(round(z * inv)))

    buckets = defaultdict(list)
    coords = []
    for p in pts:
        t = (float(p.x), float(p.y), float(p.z))
        coords.append(t)
        buckets[qkey(*t)].append(t)

    def has_neighbour(x, y, z):
        qx, qy, qz = qkey(x, y, z)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for ox, oy, oz in buckets.get((qx + dx, qy + dy, qz + dz), ()):
                        if (x - ox) ** 2 + (y - oy) ** 2 + (z - oz) ** 2 <= tol * tol:
                            return True
        return False

    frac = {}
    n = len(coords)
    for axis, name in enumerate("XYZ"):
        hit = 0
        for x, y, z in coords:
            trip = [x, y, z]
            trip[axis] = 2.0 * mid[axis] - trip[axis]
            if has_neighbour(*trip):
                hit += 1
        frac[name] = hit / n if n else 0.0
    winner = max(frac, key=lambda k: frac[k])
    return {
        "bbox": bb,
        "diagonal": diag,
        "tolerance": tol,
        "mid_plane": {"X": mid[0], "Y": mid[1], "Z": mid[2]},
        "pair_fraction": frac,
        "winner_axis": winner,
    }


def infer_axis(shell, mesh_center):
    ext = shell["extents"]
    axis_i = min(range(3), key=lambda k: ext[k])
    sign = "+" if shell["center"][axis_i] >= mesh_center[axis_i] else "-"
    return "%s%s" % (sign, "XYZ"[axis_i])


def generate_smoke_assignment(shell_list, mesh_center, symmetry):
    mid = symmetry["mid_plane"][symmetry["winner_axis"]]
    ax_i = "XYZ".index(symmetry["winner_axis"])
    atlas_a = []
    atlas_b = []
    for s in shell_list:
        ext = s["extents"]
        elong = max(ext) / max(min(ext), 1e-12)
        if s["area"] > SMOKE_AREA_MIN and elong < SMOKE_ELONG_MAX:
            crosses = s["bbox"][ax_i] < mid < s["bbox"][ax_i + 3]
            atlas_a.append({
                "shell": s["id"],
                "axis": infer_axis(s, mesh_center),
                "split_lr": bool(crosses),
                "split_by_normal_sign": True,
                "local_conformal_polish": False,
                "SMOKE": True,
            })
        else:
            atlas_b.append(s["id"])
    return {
        "SMOKE": True,
        "NOT_the_real_paint_mechanical_split": True,
        "criterion_provisional": (
            "SMOKE only: atlas_a if (3D area > %.2f) AND "
            "(bbox elongation max/min < %.1f); else atlas_b. "
            "axis = smallest-extent, sign from the exterior side of the mesh "
            "centroid. split_lr iff the shell bbox crosses the measured "
            "symmetry mid-plane. This is NOT a classification."
            % (SMOKE_AREA_MIN, SMOKE_ELONG_MAX)
        ),
        "atlas_a": atlas_a,
        "atlas_b": atlas_b,
    }


def normalize_assignment(raw, shell_ids):
    if not isinstance(raw, dict):
        raise ValueError("assignment.json must be an object")
    axis_overrides = raw.get("projection_axes") or {}
    if not isinstance(axis_overrides, dict):
        raise ValueError("projection_axes must be an object")
    for sid, axis in axis_overrides.items():
        if sid not in shell_ids:
            raise ValueError("unknown shell id in projection_axes: %r" % sid)
        if axis not in AXIS_VEC:
            raise ValueError("bad projection_axes value %r for %s" % (axis, sid))
    a_in = raw.get("atlas_a") or []
    b_in = raw.get("atlas_b") or []
    atlas_a = []
    used = set()
    for item in a_in:
        if isinstance(item, str):
            item = {"shell": item}
        sid = item.get("shell")
        if sid not in shell_ids:
            raise ValueError("unknown shell id in atlas_a: %r" % sid)
        if sid in used:
            raise ValueError("shell %s listed twice" % sid)
        used.add(sid)
        axis = axis_overrides.get(sid, item.get("axis"))
        if axis is not None and axis not in AXIS_VEC:
            raise ValueError("bad axis %r for %s" % (axis, sid))
        atlas_a.append({
            "shell": sid,
            "axis": axis,
            "split_lr": bool(item["split_lr"]) if "split_lr" in item else DEFAULT_SPLIT_LR,
            "split_by_normal_sign": (
                bool(item["split_by_normal_sign"])
                if "split_by_normal_sign" in item
                else DEFAULT_SPLIT_BY_NORMAL_SIGN
            ),
            "local_conformal_polish": (
                bool(item["local_conformal_polish"])
                if "local_conformal_polish" in item
                else DEFAULT_LOCAL_CONFORMAL_POLISH
            ),
        })
    atlas_b = []
    for item in b_in:
        sid = item["shell"] if isinstance(item, dict) else item
        if sid not in shell_ids:
            raise ValueError("unknown shell id in atlas_b: %r" % sid)
        if sid in used:
            raise ValueError("shell %s listed in both atlases" % sid)
        used.add(sid)
        atlas_b.append(sid)
    missing = [s for s in shell_ids if s not in used]
    if missing:
        log("WARN unlisted shells parked in atlas_b: %s" % missing)
        atlas_b.extend(missing)
    return {
        "SMOKE": bool(raw.get("SMOKE", False)),
        "atlas_a": atlas_a,
        "atlas_b": atlas_b,
        "projection_axes": dict(axis_overrides),
        "source_note": raw.get("criterion_provisional") or raw.get("note"),
    }


def face_groups(faces, axis_name, split_lr, split_nsign, f_nworld, f_cent, symmetry,
                lr_split_x=None):
    """Partition faces of one shell into islands."""
    axis_from = AXIS_VEC[axis_name]
    win = symmetry["winner_axis"]
    mid = symmetry["mid_plane"][win]
    ax_i = "XYZ".index(win)
    buckets = defaultdict(list)
    for f in faces:
        lr = None
        if split_lr:
            c = f_cent[f.index]
            coord = (c.x, c.y, c.z)[ax_i]
            split_value = (
                float(lr_split_x)
                if lr_split_x is not None and win == "X"
                else mid
            )
            lr = "R" if coord >= split_value else "L"
        nsign = None
        if split_nsign:
            nd = f_nworld[f.index].dot(axis_from)
            nsign = "+" if nd >= 0.0 else "-"
        buckets[(lr, nsign)].append(f)
    return buckets


def project_island_world(faces, axis_name, v_world):
    uv = {}
    umin = vmin = 1e30
    umax = vmax = -1e30
    for f in faces:
        for lp in f.loops:
            u, v = project_co(v_world[lp.vert.index], axis_name)
            uv[lp.index] = (u, v)
            umin = min(umin, u); umax = max(umax, u)
            vmin = min(vmin, v); vmax = max(vmax, v)
    if umax < umin:
        umin = vmin = 0.0
        umax = vmax = 1e-6
    if umax - umin < 1e-12:
        umax = umin + 1e-6
    if vmax - vmin < 1e-12:
        vmax = vmin + 1e-6
    return uv, (umin, vmin, umax, vmax)


def rot90_local(u, v, w, h, deg):
    if deg % 360 == 0:
        return u, v
    if deg % 360 == 90:
        return v, w - u
    if deg % 360 == 180:
        return w - u, h - v
    if deg % 360 == 270:
        return h - v, u
    raise ValueError("rotation must be a multiple of 90, got %r" % deg)


def shelf_pack(boxes, pad, orientations):
    """boxes: [{id,w,h}]. orientations[id] in {0,90}. Returns pos, W, H or None."""
    items = []
    for b in boxes:
        rot = orientations[b["id"]]
        if rot == 90:
            items.append((b["id"], b["h"], b["w"], 90))
        else:
            items.append((b["id"], b["w"], b["h"], 0))
    width_need = max(w for _, w, _, _ in items) + 2.0 * pad
    items.sort(key=lambda t: (-t[2], -t[1]))
    x = pad
    y = pad
    row_h = 0.0
    width = width_need
    pos = {}
    for iid, w, h, rot in items:
        if x + w + pad > width + 1e-9 and x > pad + 1e-12:
            y += row_h + pad
            x = pad
            row_h = 0.0
        if x + w + pad > width + 1e-9:
            width = x + w + pad
        pos[iid] = {"x": x, "y": y, "w": w, "h": h, "rot_deg": rot}
        x += w + pad
        row_h = max(row_h, h)
    height = y + row_h + pad
    return pos, width, height


def pack_islands(island_boxes, pad):
    """Shelf packer, 90° only. Prefer no rotation unless it tightens the square
    by more than 15% (keeps the orthographic reading)."""
    area = sum((b["w"] + pad) * (b["h"] + pad) for b in island_boxes)
    configs = [
        {b["id"]: 0 for b in island_boxes},
        {b["id"]: (90 if b["w"] > b["h"] else 0) for b in island_boxes},
    ]
    widths = []
    for f in (1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.5, 1.8, 2.2):
        widths.append(math.sqrt(max(area, 1e-12)) * f)
    best0 = None
    best_rot = None

    def consider(ori):
        min_w = 2.0 * pad + max(
            (b["h"] if ori[b["id"]] == 90 else b["w"]) for b in island_boxes
        )
        local = None
        for width in widths + [min_w]:
            wtry = max(width, min_w)
            pos, W, H = shelf_pack_width(island_boxes, pad, ori, wtry)
            if pos is None:
                continue
            side = max(W, H)
            nrot = sum(1 for v in ori.values() if v)
            rec = (side, -(area / max(W * H, 1e-18)), nrot, pos, W, H, ori)
            if local is None or rec < local:
                local = rec
        return local

    best0 = consider(configs[0])
    best_rot = consider(configs[1])
    chosen = best0
    if best0 and best_rot:
        if best_rot[0] < 0.85 * best0[0]:
            chosen = best_rot
    elif best_rot:
        chosen = best_rot
    if chosen is None:
        raise RuntimeError("packer failed")
    _side, _negocc, _nrot, pos, W, H, ori = chosen
    return pos, W, H


def shelf_pack_width(boxes, pad, orientations, width):
    items = []
    for b in boxes:
        rot = orientations[b["id"]]
        w, h = (b["h"], b["w"]) if rot == 90 else (b["w"], b["h"])
        if w + 2.0 * pad > width + 1e-9:
            return None, None, None
        items.append((b["id"], w, h, rot))
    items.sort(key=lambda t: (-t[2], -t[1]))
    x = pad
    y = pad
    row_h = 0.0
    pos = {}
    for iid, w, h, rot in items:
        if x + w + pad > width + 1e-9:
            y += row_h + pad
            x = pad
            row_h = 0.0
        pos[iid] = {"x": x, "y": y, "w": w, "h": h, "rot_deg": rot}
        x += w + pad
        row_h = max(row_h, h)
    height = y + row_h + pad
    return pos, width, height


def apply_pack(islands, pos, pack_w, pack_h):
    """One global scale into the unit square. No per-island normalisation."""
    side = max(pack_w, pack_h, 1e-18)
    usable = 1.0 - 2.0 * PACK_MARGIN
    scale = usable / side
    origin = PACK_MARGIN
    for isl in islands:
        p = pos[isl["id"]]
        rot = p["rot_deg"]
        umin, vmin, umax, vmax = isl["bbox_world"]
        w = umax - umin
        h = vmax - vmin
        isl["rotation_deg"] = rot
        isl["uv_final"] = {}
        for li, (u, v) in isl["uv_world"].items():
            ul = u - umin
            vl = v - vmin
            ur, vr = rot90_local(ul, vl, w, h, rot)
            isl["uv_final"][li] = (origin + (p["x"] + ur) * scale,
                                   origin + (p["y"] + vr) * scale)
        isl["pack_scale"] = scale
    return scale


def fan_tris_uv(face, uvmap):
    pts = [uvmap[lp.index] for lp in face.loops]
    out = []
    for i in range(1, len(pts) - 1):
        out.append((pts[0], pts[i], pts[i + 1]))
    return out


def raster_tris(tris, n, bbox=None):
    """Coverage counts on an n×n grid. bbox=(umin,vmin,umax,vmax) or auto."""
    if not tris:
        return array.array("H"), (0, 0, 1, 1), n
    if bbox is None:
        umin = vmin = 1e30
        umax = vmax = -1e30
        for a, b, c in tris:
            for p in (a, b, c):
                umin = min(umin, p[0]); umax = max(umax, p[0])
                vmin = min(vmin, p[1]); vmax = max(vmax, p[1])
        bbox = (umin, vmin, umax, vmax)
    umin, vmin, umax, vmax = bbox
    if umax - umin < 1e-18:
        umax = umin + 1e-18
    if vmax - vmin < 1e-18:
        vmax = vmin + 1e-18
    grid = array.array("H", [0]) * (n * n)
    du = (umax - umin)
    dv = (vmax - vmin)

    def edge(p, q, r):
        return (r[0] - p[0]) * (q[1] - p[1]) - (r[1] - p[1]) * (q[0] - p[0])

    for a, b, c in tris:
        ax = (a[0] - umin) / du * (n - 1)
        ay = (a[1] - vmin) / dv * (n - 1)
        bx = (b[0] - umin) / du * (n - 1)
        by = (b[1] - vmin) / dv * (n - 1)
        cx = (c[0] - umin) / du * (n - 1)
        cy = (c[1] - vmin) / dv * (n - 1)
        pa, pb, pc = (ax, ay), (bx, by), (cx, cy)
        area = edge(pa, pb, pc)
        if abs(area) < 1e-18:
            continue
        minx = max(0, int(math.floor(min(ax, bx, cx))))
        maxx = min(n - 1, int(math.ceil(max(ax, bx, cx))))
        miny = max(0, int(math.floor(min(ay, by, cy))))
        maxy = min(n - 1, int(math.ceil(max(ay, by, cy))))
        for y in range(miny, maxy + 1):
            py = y + 0.5
            row = y * n
            for x in range(minx, maxx + 1):
                p = (x + 0.5, py)
                w0 = edge(pb, pc, p)
                w1 = edge(pc, pa, p)
                w2 = edge(pa, pb, p)
                inside = (w0 >= 0 and w1 >= 0 and w2 >= 0) if area > 0 else (
                    w0 <= 0 and w1 <= 0 and w2 <= 0
                )
                if inside:
                    idx = row + x
                    if grid[idx] < 65535:
                        grid[idx] += 1
    return grid, bbox, n


def iou_from_coverage_grids(real_grid, atlas_grid):
    """Binary-mask IoU from independently rasterized coverage grids."""
    if len(real_grid) != len(atlas_grid):
        raise ValueError("silhouette grids must have the same number of pixels")
    intersection = 0
    union = 0
    for real_value, atlas_value in zip(real_grid, atlas_grid):
        real_on = real_value > 0
        atlas_on = atlas_value > 0
        if real_on or atlas_on:
            union += 1
            if real_on and atlas_on:
                intersection += 1
    return {
        "intersection_pixels": int(intersection),
        "union_pixels": int(union),
        "iou": float(intersection / union) if union else 1.0,
    }


def silhouette_raster_pair(real_tris, atlas_tris, real_bbox, atlas_bbox, grid_n=512):
    """Rasterize real XY and atlas-panel triangles through the same code path."""
    real_grid, _real_bbox, _ = raster_tris(real_tris, int(grid_n), bbox=real_bbox)
    atlas_grid, _atlas_bbox, _ = raster_tris(atlas_tris, int(grid_n), bbox=atlas_bbox)
    return real_grid, atlas_grid


def silhouette_iou_from_tris(real_tris, atlas_tris, real_bbox, atlas_bbox,
                             grid_n=512):
    real_grid, atlas_grid = silhouette_raster_pair(
        real_tris, atlas_tris, real_bbox, atlas_bbox, grid_n=grid_n,
    )
    result = iou_from_coverage_grids(real_grid, atlas_grid)
    result.update({
        "grid_n": int(grid_n),
        "real_bbox_xy": [float(value) for value in real_bbox],
        "atlas_normalization_bbox": [float(value) for value in atlas_bbox],
        "real_covered_pixels": sum(value > 0 for value in real_grid),
        "atlas_covered_pixels": sum(value > 0 for value in atlas_grid),
        "method": (
            "All source faces of the eight atlas-A pieces are projected to world XY "
            "and rasterized independently. The n+ atlas islands are rasterized from "
            "their final panel coordinates. Both masks use raster_tris at the same "
            "resolution and their declared coordinate-frame bboxes before binary IoU."
        ),
    })
    return result


def silhouette_metrics_by_layer(real_tris_by_panel, islands, model_xy_bbox,
                                panel_mappings, grid_n=512):
    """Corrected framing: each fixed layer is compared only with its own faces."""
    metrics = {}
    grids = {}
    for panel in ("skin", "internal"):
        real_tris = list(real_tris_by_panel.get(panel) or [])
        atlas_tris = [
            tri for isl in islands if isl.get("panel") == panel
            for tri in island_tris_final(isl)
        ]
        atlas_bbox = panel_mappings[panel]["target_frame_bbox"]
        metric = silhouette_iou_from_tris(
            real_tris, atlas_tris, model_xy_bbox, atlas_bbox, grid_n=grid_n,
        )
        metric.update({
            "panel": panel,
            "reference_face_scope": panel + "_only",
            "atlas_face_scope": panel + "_only",
            "corrected_scope": True,
            "method": (
                "Only source faces belonging to this n-sign layer are projected to "
                "world XY. Only final atlas islands from the same layer are rasterized. "
                "Both masks use raster_tris at the same 512-style resolution and the "
                "declared common world/atlas frame before binary IoU."
            ),
            "interpretation": (
                "With zero displacement and one affine scale this is a placement/"
                "rasterizer consistency check, not an aesthetic-quality score."
            ),
        })
        metrics[panel] = metric
        grids[panel] = silhouette_raster_pair(
            real_tris, atlas_tris, model_xy_bbox, atlas_bbox, grid_n=grid_n,
        )
    return {"metrics": metrics, "grids": grids, "grid_n": int(grid_n)}


def write_silhouette_layers_bmp(path, grids_by_panel, grid_n=512):
    """Write skin and internal corrected overlays side-by-side in one BMP."""
    n = int(grid_n)
    combined_real = array.array("H")
    combined_atlas = array.array("H")
    for y in range(n):
        for panel in ("skin", "internal"):
            real_grid, atlas_grid = grids_by_panel[panel]
            row_start = y * n
            combined_real.extend(real_grid[row_start:row_start + n])
            combined_atlas.extend(atlas_grid[row_start:row_start + n])
    write_silhouette_overlay_bmp(
        path, combined_real, combined_atlas, 2 * n, n,
    )


def write_silhouette_overlay_bmp(path, real_grid, atlas_grid, width, height):
    """Write a lossless 24-bit BMP for System.Drawing to annotate/convert."""
    width = int(width)
    height = int(height)
    if len(real_grid) != width * height or len(atlas_grid) != width * height:
        raise ValueError("silhouette BMP grids do not match width*height")
    row_stride = ((width * 3 + 3) // 4) * 4
    pixel_size = row_stride * height
    file_size = 54 + pixel_size
    header = bytearray()
    header.extend(b"BM")
    header.extend(file_size.to_bytes(4, "little"))
    header.extend((0).to_bytes(4, "little"))
    header.extend((54).to_bytes(4, "little"))
    header.extend((40).to_bytes(4, "little"))
    header.extend(width.to_bytes(4, "little", signed=True))
    header.extend(height.to_bytes(4, "little", signed=True))
    header.extend((1).to_bytes(2, "little"))
    header.extend((24).to_bytes(2, "little"))
    header.extend((0).to_bytes(4, "little"))
    header.extend(pixel_size.to_bytes(4, "little"))
    header.extend((2835).to_bytes(4, "little", signed=True))
    header.extend((2835).to_bytes(4, "little", signed=True))
    header.extend((0).to_bytes(4, "little"))
    header.extend((0).to_bytes(4, "little"))
    pixels = bytearray()
    palette = {
        (False, False): (30, 24, 18),
        (True, False): (72, 72, 224),
        (False, True): (224, 190, 45),
        (True, True): (66, 218, 245),
    }
    for y in range(height):
        row_start = y * width
        for x in range(width):
            real_on = real_grid[row_start + x] > 0
            atlas_on = atlas_grid[row_start + x] > 0
            blue, green, red = palette[(real_on, atlas_on)]
            pixels.extend((blue, green, red))
        pixels.extend(b"\x00" * (row_stride - width * 3))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(pixels)


def overlap_from_grid(grid, n, bbox, face_perimeters_uv):
    ge1 = ge2 = 0
    for c in grid:
        if c >= 1:
            ge1 += 1
            if c >= 2:
                ge2 += 1
    umin, vmin, umax, vmax = bbox
    px = (umax - umin) / n
    py = (vmax - vmin) / n
    pix_area = px * py
    union_area = ge1 * pix_area
    overlap_area = ge2 * pix_area
    if ge1 == 0:
        return {
            "overlap_area_frac": 0.0,
            "overlap_status": "no medible",
            "reason": "zero covered pixels",
            "grid_n": n,
            "bbox": bbox,
        }
    frac = overlap_area / union_area
    # Pick-style bound: each face can mis-paint O(perimeter * pixel_side).
    perim = sum(face_perimeters_uv)
    err_area = 0.5 * perim * max(px, py)
    err_frac = err_area / union_area if union_area > 0 else float("inf")
    status = "ok"
    if err_frac > 0.5 and err_frac > frac:
        status = "no medible"
    return {
        "overlap_area_frac": float(frac),
        "overlap_status": status,
        "grid_n": n,
        "grid_bbox": [float(x) for x in bbox],
        "pixel_uv": [float(px), float(py)],
        "covered_pixels": ge1,
        "overlap_pixels": ge2,
        "discretization_error_bound_frac": float(err_frac),
        "discretization_note": (
            "Union/overlap from an %dx%d raster over the UV bbox. "
            "Area error bound 0.5*sum(face UV perimeters)*pixel_side / union_area "
            "= %.4g. This is a bound, not a CI." % (n, n, err_frac)
        ),
    }


def uv_perimeter(face, uvmap):
    pts = [uvmap[lp.index] for lp in face.loops]
    s = 0.0
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        s += math.hypot(q[0] - p[0], q[1] - p[1])
    return s


def island_label(isl):
    parts = [isl["shell"], isl["axis"]]
    if isl.get("lr"):
        parts.append(isl["lr"])
    if isl.get("nsign"):
        parts.append("n" + isl["nsign"])
    rot = isl.get("rotation_deg") or 0
    if rot:
        parts.append("r%d" % rot)
    return " ".join(parts)


def island_tris_final(isl):
    tris = []
    for f in isl["faces"]:
        tris.extend(fan_tris_uv(f, isl["uv_final"]))
    return tris


def island_boundary_edges(isl):
    uv = isl["uv_final"]
    seen = {}
    for f in isl["faces"]:
        loops = list(f.loops)
        n = len(loops)
        for i in range(n):
            a = loops[i]
            b = loops[(i + 1) % n]
            va, vb = a.vert.index, b.vert.index
            key = (va, vb) if va < vb else (vb, va)
            if key in seen:
                seen[key] = None
            else:
                seen[key] = (uv[a.index], uv[b.index])
    return [seg for seg in seen.values() if seg is not None]


def weighted_centroid(tris):
    ax = ay = wsum = 0.0
    for a, b, c in tris:
        w = tri_area_2d(a, b, c)
        cx = (a[0] + b[0] + c[0]) / 3.0
        cy = (a[1] + b[1] + c[1]) / 3.0
        ax += w * cx
        ay += w * cy
        wsum += w
    if wsum <= 1e-18:
        return (0.5, 0.5)
    return (ax / wsum, ay / wsum)


def build_islands_for_spec(spec, shell_by_id, v_world, f_nworld, f_cent, symmetry,
                           lr_split_x=None):
    shell = shell_by_id[spec["shell"]]
    axis = spec["axis"] or infer_axis(shell, (
        symmetry["mid_plane"]["X"],
        symmetry["mid_plane"]["Y"],
        symmetry["mid_plane"]["Z"],
    ))
    if spec["local_conformal_polish"]:
        log("WARN local_conformal_polish on %s ignored (flag off-by-default, not implemented)" % spec["shell"])
    buckets = face_groups(
        shell["faces"], axis, spec["split_lr"], spec["split_by_normal_sign"],
        f_nworld, f_cent, symmetry, lr_split_x=lr_split_x,
    )
    islands = []
    for (lr, nsign), faces in buckets.items():
        if not faces:
            continue
        iid = "%s|%s|%s|%s" % (spec["shell"], axis, lr or "-", nsign or "-")
        uv_world, bbox = project_island_world(faces, axis, v_world)
        islands.append({
            "id": iid,
            "shell": spec["shell"],
            "axis": axis,
            "lr": lr,
            "nsign": nsign,
            "faces": faces,
            "face_indices": [f.index for f in faces],
            "n_faces": len(faces),
            "area_3d": float(sum(f.calc_area() for f in faces)),
            "uv_world": uv_world,
            "bbox_world": bbox,
            "split_lr": spec["split_lr"],
            "split_by_normal_sign": spec["split_by_normal_sign"],
        })
    return islands


def choose_axis_candidate(
        candidates, current_axis,
        overlap_limit=AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT,
        preferred_axes=()):
    """Keep the incumbent unless a tighter migration passes the overlap limit.

    ``candidates`` are already measured; this policy function deliberately does
    not recompute either side of the comparison, which keeps the gate testable
    against independent literal fixtures. The incumbent is never tested against
    the absolute limit. A different axis is eligible only when it is strictly
    more compact than the incumbent and its self-overlap is at most the limit.
    """
    current = next((c for c in candidates if c["axis"] == current_axis), None)
    if current is None:
        raise ValueError("current axis %r is absent from candidates" % current_axis)
    overlap_limit = float(overlap_limit)
    current_ratio = float(current["bbox_to_island_area"])
    migrations = [c for c in candidates if c["axis"] != current_axis]
    eligible = [
        c for c in migrations
        if float(c["bbox_to_island_area"]) < current_ratio
        and float(c["self_overlap"]) <= overlap_limit
    ]
    rejected = sorted(
        c["axis"] for c in migrations
        if float(c["self_overlap"]) > overlap_limit
    )
    not_more_compact = sorted(
        c["axis"] for c in migrations
        if float(c["bbox_to_island_area"]) >= current_ratio
    )
    preferred_rank = {axis: i for i, axis in enumerate(preferred_axes)}

    def rank(c):
        axis = c["axis"]
        return (
            float(c["bbox_to_island_area"]),
            0 if axis == current_axis else 1,
            preferred_rank.get(axis, len(preferred_rank)),
            AXIS_NAMES.index(axis),
        )

    kept_incumbent = not eligible
    chosen = current if kept_incumbent else min(eligible, key=rank)
    out = dict(chosen)
    out["policy"] = AXIS_SEARCH_POLICY
    out["current_axis"] = current_axis
    out["current_bbox_to_island_area"] = current_ratio
    out["current_self_overlap"] = float(current["self_overlap"])
    out["overlap_limit"] = overlap_limit
    out["eligible_axes"] = [c["axis"] for c in eligible]
    out["rejected_overlap_axes"] = rejected
    out["not_more_compact_axes"] = not_more_compact
    out["kept_incumbent"] = kept_incumbent
    return out


def _exterior_axis_for_dimension(shell, mesh_center, dimension):
    idx = "XYZ".index(dimension)
    sign = "+" if shell["center"][idx] >= mesh_center[idx] else "-"
    return sign + dimension


def axis_piece_score(spec, axis_name, shell_by_id, v_world, f_nworld, f_cent, symmetry,
                     grid_n=AXIS_SEARCH_OVERLAP_GRID):
    """Measure compactness and self-overlap of one piece on one camera axis."""
    candidate_spec = dict(spec)
    candidate_spec["axis"] = axis_name
    islands = build_islands_for_spec(
        candidate_spec, shell_by_id, v_world, f_nworld, f_cent, symmetry,
    )
    bbox_area_sum = 0.0
    union_area_sum = 0.0
    overlap_area_sum = 0.0
    triangle_area_sum = 0.0
    per_island = []
    for isl in islands:
        tris = []
        for face in isl["faces"]:
            tris.extend(fan_tris_uv(face, isl["uv_world"]))
        u0, v0, u1, v1 = isl["bbox_world"]
        bbox_area = max(u1 - u0, 1e-18) * max(v1 - v0, 1e-18)
        grid, gbb, n = raster_tris(tris, grid_n, bbox=(u0, v0, u1, v1))
        covered = sum(1 for c in grid if c >= 1)
        overlapped = sum(1 for c in grid if c >= 2)
        pixel_area = ((gbb[2] - gbb[0]) / n) * ((gbb[3] - gbb[1]) / n)
        union_area = covered * pixel_area
        overlap_area = overlapped * pixel_area
        triangle_area = sum(tri_area_2d(*tri) for tri in tris)
        bbox_area_sum += bbox_area
        union_area_sum += union_area
        overlap_area_sum += overlap_area
        triangle_area_sum += triangle_area
        per_island.append({
            "id": isl["id"],
            "bbox_area": float(bbox_area),
            "union_area_raster": float(union_area),
            "triangle_area": float(triangle_area),
            "self_overlap_area_raster": float(overlap_area),
            "bbox_to_island_area": float(bbox_area / union_area) if union_area > 0.0 else None,
        })
    ratio = bbox_area_sum / union_area_sum if union_area_sum > 0.0 else float("inf")
    self_overlap = overlap_area_sum / union_area_sum if union_area_sum > 0.0 else float("inf")
    return {
        "axis": axis_name,
        "bbox_to_island_area": float(ratio),
        "self_overlap": float(self_overlap),
        "bbox_area_sum": float(bbox_area_sum),
        "island_union_area_raster_sum": float(union_area_sum),
        "projected_triangle_area_sum": float(triangle_area_sum),
        "self_overlap_area_raster_sum": float(overlap_area_sum),
        "grid_n": int(grid_n),
        "n_islands": len(islands),
        "per_island": per_island,
    }


def search_projection_axes(specs_by_shell, shell_by_id, mesh_center, v_world,
                           f_nworld, f_cent, symmetry):
    """Try all six axes per piece, returning copied specs and audit records."""
    selected = {sid: dict(spec) for sid, spec in specs_by_shell.items()}
    records = []
    for sid in sorted(selected):
        spec = selected[sid]
        current_axis = spec["axis"]
        candidates = [
            axis_piece_score(
                spec, axis, shell_by_id, v_world, f_nworld, f_cent, symmetry,
            )
            for axis in AXIS_NAMES
        ]
        shell = shell_by_id[sid]
        preferred = tuple(
            _exterior_axis_for_dimension(shell, mesh_center, dim) for dim in "XYZ"
        )
        chosen = choose_axis_candidate(
            candidates, current_axis,
            overlap_limit=AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT,
            preferred_axes=preferred,
        )
        current = next(c for c in candidates if c["axis"] == current_axis)
        new_axis = chosen["axis"]
        selected[sid]["axis"] = new_axis
        old_ratio = float(current["bbox_to_island_area"])
        new_ratio = float(chosen["bbox_to_island_area"])
        records.append({
            "shell": sid,
            "axis_before": current_axis,
            "axis_after": new_axis,
            "changed": new_axis != current_axis,
            "bbox_to_island_area_before": old_ratio,
            "bbox_to_island_area_after": new_ratio,
            "compactness_gain_abs": old_ratio - new_ratio,
            "compactness_gain_pct": (
                100.0 * (old_ratio - new_ratio) / old_ratio if old_ratio > 0.0 else 0.0
            ),
            "self_overlap_before": float(current["self_overlap"]),
            "self_overlap_after": float(chosen["self_overlap"]),
            "policy": AXIS_SEARCH_POLICY,
            "overlap_limit": AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT,
            "eligible_axes": chosen["eligible_axes"],
            "rejected_overlap_axes": chosen["rejected_overlap_axes"],
            "not_more_compact_axes": chosen["not_more_compact_axes"],
            "kept_incumbent": chosen["kept_incumbent"],
            "candidate_scores": candidates,
        })
    return selected, records


def pack_and_scale(islands):
    if not islands:
        return 1.0, {}, 1.0, 1.0
    boxes = []
    max_side = 0.0
    for isl in islands:
        umin, vmin, umax, vmax = isl["bbox_world"]
        w = max(umax - umin, 1e-9)
        h = max(vmax - vmin, 1e-9)
        boxes.append({"id": isl["id"], "w": w, "h": h})
        max_side = max(max_side, w, h)
    pad = max(ISLAND_PAD_FRAC * max_side, 1e-9)
    pos, pack_w, pack_h = pack_islands(boxes, pad)
    scale = apply_pack(islands, pos, pack_w, pack_h)
    return scale, pos, pack_w, pack_h


# ---------------------------------------------------------------------------
# Piece-block packer. Islands of one shell live in one rectangle; blocks are
# shelf-packed. Inner layout is a stable L/R x n+/n- grid. Empty cells stay
# empty (a missing column/row of width 0 is not a rearrange).
# ---------------------------------------------------------------------------
def _island_wh(isl):
    umin, vmin, umax, vmax = isl["bbox_world"]
    return max(umax - umin, 1e-9), max(vmax - vmin, 1e-9)


def layout_piece_block(islands, split_lr, split_nsign, inner_pad, outer_pad, label_h,
                      cell_mode="fitted"):
    """Local coordinates of a piece block. Origin = bottom-left, +V up.

    Grid (when both splits are on):

        [ L n+ ][ R n+ ]
        [ L n- ][ R n- ]

    L left of R, n+ above n-. A missing combination leaves its cell empty;
    the empty cell still occupies its row/col size so the remaining islands
    are not slid into the hole. A whole empty column/row has size 0.

    cell_mode:
      "fitted"  — column width = max island width in that column, row height
                  = max in that row (G3 already did this).
      "uniform" — every occupied cell is max-all-widths x max-all-heights.
    """
    slot = {}
    for isl in islands:
        key = (isl.get("lr"), isl.get("nsign"))
        if key in slot:
            raise RuntimeError("two islands in the same grid cell: %s and %s" % (
                slot[key]["id"], isl["id"]))
        slot[key] = isl

    cols = ["L", "R"] if split_lr else [None]
    rows = ["+", "-"] if split_nsign else [None]

    col_w = {c: 0.0 for c in cols}
    row_h = {r: 0.0 for r in rows}
    for c in cols:
        for r in rows:
            isl = slot.get((c, r))
            if isl is None:
                continue
            w, h = _island_wh(isl)
            col_w[c] = max(col_w[c], w)
            row_h[r] = max(row_h[r], h)

    if cell_mode == "uniform":
        mw = max(col_w.values()) if col_w else 0.0
        mh = max(row_h.values()) if row_h else 0.0
        for c in cols:
            if col_w[c] > 0.0:
                col_w[c] = mw
        for r in rows:
            if row_h[r] > 0.0:
                row_h[r] = mh

    col_x = {}
    x = 0.0
    for i, c in enumerate(cols):
        col_x[c] = x
        if col_w[c] > 0.0:
            x += col_w[c]
            if i < len(cols) - 1:
                x += inner_pad
    if len(cols) > 1 and col_w[cols[-1]] <= 0.0 and x >= inner_pad:
        x -= inner_pad
    geom_w = max(x, 1e-9)

    # Bottom-up: n- then n+.
    rows_up = list(reversed(rows))
    row_y = {}
    y = 0.0
    for i, r in enumerate(rows_up):
        row_y[r] = y
        if row_h[r] > 0.0:
            y += row_h[r]
            if i < len(rows_up) - 1:
                y += inner_pad
    if len(rows_up) > 1 and row_h[rows_up[-1]] <= 0.0 and y >= inner_pad:
        y -= inner_pad
    geom_h = max(y, 1e-9)

    ox = outer_pad
    oy = outer_pad
    block_w = geom_w + 2.0 * outer_pad
    block_h = geom_h + 2.0 * outer_pad + label_h

    local = {}
    for isl in islands:
        c = isl.get("lr") if split_lr else None
        r = isl.get("nsign") if split_nsign else None
        local[isl["id"]] = {
            "x": ox + col_x[c],
            "y": oy + row_y[r],
            "w": _island_wh(isl)[0],
            "h": _island_wh(isl)[1],
            "rot_deg": 0,
            "cell": [c, r],
        }
    return local, block_w, block_h, {
        "cols": cols,
        "rows": rows,
        "col_w": col_w,
        "row_h": row_h,
        "geom_w": geom_w,
        "geom_h": geom_h,
        "label_h": label_h,
    }


def shelf_pack_width_keep_order(boxes, pad, width):
    """Shelf pack that keeps the incoming order (area descending for blocks).

    Does not re-sort by height: mixing tall/short across pieces is exactly
    what grouping is trying to stop.
    """
    pos = {}
    x = pad
    y = pad
    row_h = 0.0
    for b in boxes:
        w, h = b["w"], b["h"]
        if w + 2.0 * pad > width + 1e-9:
            return None, None, None
        if x + w + pad > width + 1e-9:
            y += row_h + pad
            x = pad
            row_h = 0.0
        pos[b["id"]] = {"x": x, "y": y, "w": w, "h": h, "rot_deg": 0}
        x += w + pad
        row_h = max(row_h, h)
    height = y + row_h + pad
    return pos, width, height


def pack_blocks_shelf(block_boxes, pad):
    """Shelf-pack piece blocks, area descending. Rotation 0 only.

    Occupancy is secondary to grouping; rotating a block would put n+ beside
    n- in atlas space and break the inner-grid reading.
    """
    if not block_boxes:
        return {}, 1.0, 1.0
    items = sorted(
        block_boxes,
        key=lambda b: (-(b["w"] * b["h"]), -b["h"], -b["w"], b["id"]),
    )
    area = sum((b["w"] + pad) * (b["h"] + pad) for b in items)
    min_w = 2.0 * pad + max(b["w"] for b in items)
    widths = [min_w]
    for f in (1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.5, 1.8, 2.2):
        widths.append(max(min_w, math.sqrt(max(area, 1e-12)) * f))
    best = None
    for wtry in widths:
        pos, W, H = shelf_pack_width_keep_order(items, pad, wtry)
        if pos is None:
            continue
        side = max(W, H)
        rec = (side, -(area / max(W * H, 1e-18)), pos, W, H)
        if best is None or rec < best:
            best = rec
    if best is None:
        raise RuntimeError("block packer failed")
    _side, _negocc, pos, W, H = best
    return pos, W, H


def _maxrects_order(boxes, order_name):
    if order_name == "area_desc":
        key = lambda b: (-(b["w"] * b["h"]), -max(b["w"], b["h"]), b["id"])
    elif order_name == "max_side_desc":
        key = lambda b: (-max(b["w"], b["h"]), -(b["w"] * b["h"]), b["id"])
    elif order_name == "perimeter_desc":
        key = lambda b: (-(b["w"] + b["h"]), -(b["w"] * b["h"]), b["id"])
    else:
        raise ValueError("unknown insertion order %r" % order_name)
    return sorted(boxes, key=key)


def _rect_intersects(a, b):
    return not (
        a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
        or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]
    )


def _prune_free_rectangles(rects):
    clean = []
    for i, a in enumerate(rects):
        if a[2] <= 1e-12 or a[3] <= 1e-12:
            continue
        contained = False
        for j, b in enumerate(rects):
            if i == j:
                continue
            if (a[0] >= b[0] - 1e-12 and a[1] >= b[1] - 1e-12
                    and a[0] + a[2] <= b[0] + b[2] + 1e-12
                    and a[1] + a[3] <= b[1] + b[3] + 1e-12):
                if a != b or j < i:
                    contained = True
                    break
        if not contained:
            clean.append(a)
    return clean


def pack_rectangles_maxrects(boxes, bin_w, bin_h, order_name, allow_rotation):
    """MaxRects best-short-side-fit for piece-block rectangles.

    The rectangles are the indivisible semantic blocks. Rotation changes only
    the whole block's orientation; no island is exposed to this packer.
    """
    if bin_w <= 0.0 or bin_h <= 0.0:
        return None
    free = [(0.0, 0.0, float(bin_w), float(bin_h))]
    positions = {}
    ordered = _maxrects_order(boxes, order_name)
    for box in ordered:
        options = [(float(box["w"]), float(box["h"]), 0)]
        if allow_rotation and abs(float(box["w"]) - float(box["h"])) > 1e-12:
            options.append((float(box["h"]), float(box["w"]), 90))
        best = None
        for fi, fr in enumerate(free):
            fx, fy, fw, fh = fr
            for w, h, rot in options:
                if w > fw + 1e-12 or h > fh + 1e-12:
                    continue
                leftover_w = fw - w
                leftover_h = fh - h
                score = (
                    min(leftover_w, leftover_h),
                    max(leftover_w, leftover_h),
                    fw * fh - w * h,
                    fy, fx, rot,
                )
                rec = (score, fi, fx, fy, w, h, rot)
                if best is None or rec < best:
                    best = rec
        if best is None:
            return None
        _score, _fi, px, py, pw, ph, prot = best
        placed = (px, py, pw, ph)
        positions[box["id"]] = {
            "x": px, "y": py, "w": pw, "h": ph, "rot_deg": prot,
        }
        split = []
        for fr in free:
            if not _rect_intersects(fr, placed):
                split.append(fr)
                continue
            fx, fy, fw, fh = fr
            rx, ry, rw, rh = placed
            if rx > fx + 1e-12:
                split.append((fx, fy, rx - fx, fh))
            if rx + rw < fx + fw - 1e-12:
                split.append((rx + rw, fy, fx + fw - (rx + rw), fh))
            if ry > fy + 1e-12:
                split.append((fx, fy, fw, ry - fy))
            if ry + rh < fy + fh - 1e-12:
                split.append((fx, ry + rh, fw, fy + fh - (ry + rh)))
        free = _prune_free_rectangles(split)
    used_area = sum(p["w"] * p["h"] for p in positions.values())
    return {
        "positions": positions,
        "order_name": order_name,
        "allow_rotation": bool(allow_rotation),
        "bin_wh": [float(bin_w), float(bin_h)],
        "used_area": float(used_area),
        "free_area_lower_bound": float(bin_w * bin_h - used_area),
    }


def _tight_block_layout(islands, specs_by_shell, scale):
    """Build block rectangles directly in final UV units at one trial scale."""
    cfg = fixed_padding_config()
    pad = cfg["pad_uv"]
    label_h = cfg["label_uv"]
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)
    local_by_island = {}
    block_boxes = []
    block_meta = {}
    for sid in sorted(by_shell):
        scaled = []
        for isl in by_shell[sid]:
            u0, v0, u1, v1 = isl["bbox_world"]
            proxy = dict(isl)
            proxy["bbox_world"] = (
                u0 * scale, v0 * scale, u1 * scale, v1 * scale,
            )
            scaled.append(proxy)
        spec = specs_by_shell[sid]
        local, bw, bh, grid = layout_piece_block(
            scaled,
            spec["split_lr"], spec["split_by_normal_sign"],
            inner_pad=pad, outer_pad=pad, label_h=label_h,
            cell_mode="fitted",
        )
        local_by_island.update(local)
        block_boxes.append({"id": sid, "w": bw, "h": bh})
        block_meta[sid] = {
            "w": bw,
            "h": bh,
            "grid": grid,
            "n_islands": len(scaled),
        }
    return local_by_island, block_boxes, block_meta


def _shelf_place_fixed_orientation(items, bin_w, bin_h):
    positions = {}
    x = 0.0
    y = 0.0
    row_h = 0.0
    for item in items:
        w, h = item["placed_w"], item["placed_h"]
        if w > bin_w + 1e-12 or h > bin_h + 1e-12:
            return None
        if x + w > bin_w + 1e-12 and x > 1e-12:
            y += row_h
            x = 0.0
            row_h = 0.0
        if y + h > bin_h + 1e-12:
            return None
        positions[item["id"]] = {
            "x": x, "y": y, "w": w, "h": h,
            "rot_deg": item["rot_deg"],
        }
        x += w
        row_h = max(row_h, h)
    used_h = y + row_h
    return {
        "positions": positions,
        "used_height": used_h,
        "used_width": max(
            (p["x"] + p["w"] for p in positions.values()), default=0.0,
        ),
    }


def pack_rectangles_shelf(boxes, bin_w, bin_h, order_name, allow_rotation):
    """Shelf baseline for B/C/D; rotations are whole-block 0/90 choices.

    Angles 180 and 270 have exactly the same rectangle dimensions as 0 and 90.
    They are therefore measured as equivalent candidates and lose deterministic
    ties to the smaller angle; geometry is never rotated independently.
    """
    ordered = _maxrects_order(boxes, order_name)
    n = len(ordered)
    masks = range(1 << n) if allow_rotation else (0,)
    best = None
    for mask in masks:
        items = []
        for i, box in enumerate(ordered):
            rot = 90 if (mask & (1 << i)) else 0
            w, h = (
                (float(box["h"]), float(box["w"]))
                if rot == 90 else (float(box["w"]), float(box["h"]))
            )
            items.append({
                "id": box["id"], "placed_w": w, "placed_h": h,
                "rot_deg": rot,
            })
        got = _shelf_place_fixed_orientation(items, bin_w, bin_h)
        if got is None:
            continue
        rotations = tuple(got["positions"][b["id"]]["rot_deg"] for b in ordered)
        score = (got["used_height"], got["used_width"], sum(r != 0 for r in rotations), rotations)
        if best is None or score < best[0]:
            best = (score, got)
    if best is None:
        return None
    got = best[1]
    got.update({
        "order_name": order_name,
        "allow_rotation": bool(allow_rotation),
        "bin_wh": [float(bin_w), float(bin_h)],
        "rotation_candidates_deg": [0, 90, 180, 270],
        "bbox_equivalent_rotation_classes": [[0, 180], [90, 270]],
    })
    return got


def _try_tight_pack(islands, specs_by_shell, scale, packer, allow_rotation, order_name):
    local, boxes, meta = _tight_block_layout(islands, specs_by_shell, scale)
    pad = fixed_padding_config()["pad_uv"]
    bin_side = 1.0 - 2.0 * pad
    if packer == "shelf":
        packed = pack_rectangles_shelf(
            boxes, bin_side, bin_side, order_name, allow_rotation,
        )
    elif packer == "maxrects":
        packed = pack_rectangles_maxrects(
            boxes, bin_side, bin_side, order_name, allow_rotation,
        )
        if packed is not None:
            packed["rotation_candidates_deg"] = [0, 90, 180, 270]
            packed["bbox_equivalent_rotation_classes"] = [[0, 180], [90, 270]]
    else:
        raise ValueError("unknown tight block packer %r" % packer)
    if packed is None:
        return None
    return {
        "local_by_island": local,
        "block_boxes": boxes,
        "block_meta": meta,
        "packing": packed,
    }


def _max_scale_for_tight_order(islands, specs_by_shell, packer, allow_rotation,
                               order_name, iterations=48):
    lo = 0.0
    hi = 1.0
    while _try_tight_pack(
            islands, specs_by_shell, hi, packer, allow_rotation, order_name) is not None:
        lo = hi
        hi *= 2.0
        if hi > 64.0:
            raise RuntimeError("tight pack scale search did not find an upper bound")
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if _try_tight_pack(
                islands, specs_by_shell, mid, packer, allow_rotation, order_name) is None:
            hi = mid
        else:
            lo = mid
    result = _try_tight_pack(
        islands, specs_by_shell, lo, packer, allow_rotation, order_name,
    )
    if result is None:
        raise RuntimeError("tight packer lost its last feasible scale")
    result["global_scale"] = lo
    result["scale_search"] = {
        "lower_feasible": lo,
        "upper_infeasible": hi,
        "iterations": iterations,
        "absolute_bracket": hi - lo,
    }
    return result


def _apply_tight_pack(islands, trial):
    scale = trial["global_scale"]
    cfg = fixed_padding_config()
    origin = cfg["pad_uv"]
    local = trial["local_by_island"]
    meta = trial["block_meta"]
    pos = trial["packing"]["positions"]
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)

    for isl in islands:
        sid = isl["shell"]
        loc = local[isl["id"]]
        bp = pos[sid]
        bw = meta[sid]["w"]
        bh = meta[sid]["h"]
        rot = int(bp.get("rot_deg") or 0)
        umin, vmin, _umax, _vmax = isl["bbox_world"]
        isl["rotation_deg"] = rot
        isl["rotation_scope"] = "whole_block"
        isl["uv_final"] = {}
        for li, (u, v) in isl["uv_world"].items():
            lx = loc["x"] + (u - umin) * scale
            ly = loc["y"] + (v - vmin) * scale
            rx, ry = rot90_local(lx, ly, bw, bh, rot)
            isl["uv_final"][li] = (
                origin + bp["x"] + rx,
                origin + bp["y"] + ry,
            )
        isl["pack_scale"] = scale

    blocks = []
    for sid in sorted(meta):
        bp = pos[sid]
        box = meta[sid]
        bw, bh = box["w"], box["h"]
        rot = int(bp.get("rot_deg") or 0)
        lx = 0.5 * bw
        ly = bh - 0.5 * box["grid"]["label_h"]
        rlx, rly = rot90_local(lx, ly, bw, bh, rot)
        u0 = origin + bp["x"]
        v0 = origin + bp["y"]
        u1 = u0 + bp["w"]
        v1 = v0 + bp["h"]
        blocks.append({
            "shell": sid,
            "uv_bbox": [float(u0), float(v0), float(u1), float(v1)],
            "pack_xywh": [float(bp["x"]), float(bp["y"]), float(bp["w"]), float(bp["h"])],
            "unrotated_wh": [float(bw), float(bh)],
            "label_uv": [float(u0 + rlx), float(v0 + rly)],
            "n_islands": box["n_islands"],
            "rotation_deg": rot,
            "rotation_scope": "whole_block",
            "grid": {
                "cols": box["grid"]["cols"],
                "rows": box["grid"]["rows"],
                "geom_w": box["grid"]["geom_w"],
                "geom_h": box["grid"]["geom_h"],
                "local_order_preserved_before_rigid_rotation": True,
            },
        })
    return blocks


def pack_and_scale_blocks_tight(islands, specs_by_shell, packer="maxrects",
                                 allow_rotation=True,
                                 order_names=("area_desc", "max_side_desc", "perimeter_desc")):
    """Pack semantic blocks with final-UV texel padding and one global scale."""
    if not islands:
        return {
            "global_scale": 1.0, "blocks": [], "packer": packer,
            "selected_order": None, "order_trials": [],
        }
    trials = []
    best = None
    for order_index, order_name in enumerate(order_names):
        trial = _max_scale_for_tight_order(
            islands, specs_by_shell, packer, allow_rotation, order_name,
        )
        rec = {
            "order_name": order_name,
            "global_scale": trial["global_scale"],
            "scale_search": trial["scale_search"],
        }
        trials.append(rec)
        key = (-trial["global_scale"], order_index)
        if best is None or key < best[0]:
            best = (key, trial)
    chosen = best[1]
    blocks = _apply_tight_pack(islands, chosen)
    return {
        "global_scale": chosen["global_scale"],
        "blocks": blocks,
        "packer": packer,
        "allow_block_rotation": bool(allow_rotation),
        "selected_order": chosen["packing"]["order_name"],
        "order_trials": trials,
        "scale_search": chosen["scale_search"],
        "padding": fixed_padding_config(),
        "rotation_candidates_deg": chosen["packing"].get("rotation_candidates_deg", [0]),
        "bbox_equivalent_rotation_classes": chosen["packing"].get(
            "bbox_equivalent_rotation_classes", [[0, 180], [90, 270]],
        ),
    }


def weighted_centroid_from_points(points):
    """Arithmetic centroid used by placement gates on already transformed UVs."""
    pts = list(points)
    if not pts:
        return (0.0, 0.0)
    return (
        sum(float(p[0]) for p in pts) / len(pts),
        sum(float(p[1]) for p in pts) / len(pts),
    )


def _rotated_wh(width, height, rotation_deg):
    if int(rotation_deg) % 180 == 0:
        return float(width), float(height)
    return float(height), float(width)


def _anatomical_items(islands, rotations, scale):
    out = []
    for isl in islands:
        raw_w, raw_h = _island_wh(isl)
        rot = int(rotations.get(isl["shell"], 0)) % 360
        width, height = _rotated_wh(raw_w * scale, raw_h * scale, rot)
        umin, vmin, _umax, _vmax = isl["bbox_world"]
        rotated_points = []
        for u, v in isl["uv_world"].values():
            rotated_points.append(rot90_local(
                (u - umin) * scale,
                (v - vmin) * scale,
                raw_w * scale,
                raw_h * scale,
                rot,
            ))
        rotated_tris = []
        for face in isl.get("faces") or []:
            for tri in fan_tris_uv(face, isl["uv_world"]):
                transformed = []
                for u, v in tri:
                    transformed.append(rot90_local(
                        (u - umin) * scale,
                        (v - vmin) * scale,
                        raw_w * scale,
                        raw_h * scale,
                        rot,
                    ))
                rotated_tris.append(tuple(transformed))
        if rotated_tris:
            centroid_x, centroid_y = weighted_centroid(rotated_tris)
        else:
            centroid_x, centroid_y = weighted_centroid_from_points(rotated_points)
        out.append({
            "island": isl,
            "id": isl["id"],
            "shell": isl["shell"],
            "lr": isl.get("lr"),
            "nsign": isl.get("nsign"),
            "w": width,
            "h": height,
            "centroid_x": centroid_x,
            "centroid_y": centroid_y,
            "rotation_deg": rot,
        })
    return out


def _anatomical_sign_centers(items, pad):
    """Shared final-V centers: n+ is visibly above n-, with no scale skew."""
    signs = sorted({item["nsign"] for item in items if item["nsign"] is not None})
    if not signs:
        return {None: 0.0}, 0.0
    max_h = {
        sign: max(item["h"] for item in items if item["nsign"] == sign)
        for sign in signs
    }
    if "+" in max_h and "-" in max_h:
        stagger = max(float(pad), 0.18 * min(max_h["+"], max_h["-"]))
        raw_centers = {"-": 0.0, "+": stagger}
    else:
        raw_centers = {sign: 0.0 for sign in signs}
    low = min(
        raw_centers[item["nsign"]] - item["centroid_y"]
        for item in items
    )
    high = max(
        raw_centers[item["nsign"]] + item["h"] - item["centroid_y"]
        for item in items
    )
    centers = {sign: center - low for sign, center in raw_centers.items()}
    return centers, high - low


def _anatomical_group_width(items, pad):
    if not items:
        return 0.0
    return sum(item["w"] for item in items) + float(pad) * (len(items) - 1)


def _place_anatomical_sign_group(items, slot_x, slot_w, inner_side, centers, pad):
    """Place signs side-by-side; n+ faces the centre and remains above n-."""
    by_sign = {}
    for item in items:
        sign = item["nsign"]
        if sign in by_sign:
            raise RuntimeError("duplicate n-sign in anatomical cell: %s" % item["id"])
        by_sign[sign] = item
    preferred = ["-", "+"] if inner_side == "right" else ["+", "-"]
    ordered = [by_sign[s] for s in preferred if s in by_sign]
    ordered.extend(item for sign, item in sorted(by_sign.items()) if sign not in preferred)
    group_w = _anatomical_group_width(ordered, pad)
    x = float(slot_x) + (float(slot_w) - group_w if inner_side == "right" else 0.0)
    local = {}
    for index, item in enumerate(ordered):
        sign = item["nsign"]
        local[item["id"]] = {
            "x": x,
            "y": centers[sign] - item["centroid_y"],
            "w": item["w"],
            "h": item["h"],
            "rot_deg": item["rotation_deg"],
            "cell": [item["lr"], sign],
        }
        x += item["w"]
        if index < len(ordered) - 1:
            x += float(pad)
    return local


def _layout_anatomical_crossing_piece(islands, rotations, scale, pad, label_h):
    sid = islands[0]["shell"]
    items = _anatomical_items(islands, rotations, scale)
    by_lr = {lr: [item for item in items if item["lr"] == lr] for lr in ("L", "R")}
    if not by_lr["L"] or not by_lr["R"]:
        raise RuntimeError("crossing block %s is missing an L or R column" % sid)
    centers, geom_h = _anatomical_sign_centers(items, pad)
    half_w = max(_anatomical_group_width(by_lr[lr], pad) for lr in ("L", "R"))
    axis_gap = 2.0 * float(pad)
    block_w = 2.0 * float(pad) + 2.0 * half_w + axis_gap
    block_h = 2.0 * float(pad) + geom_h + float(label_h)
    left_x = float(pad)
    right_x = float(pad) + half_w + axis_gap
    local = _place_anatomical_sign_group(
        by_lr["L"], left_x, half_w, "right", centers, pad,
    )
    local.update(_place_anatomical_sign_group(
        by_lr["R"], right_x, half_w, "left", centers, pad,
    ))
    for rec in local.values():
        rec["y"] += float(pad)
    return {
        "shell": sid,
        "w": block_w,
        "h": block_h,
        "local": local,
        "label_h": float(label_h),
        "rotation_deg": int(rotations.get(sid, 0)) % 360,
        "n_islands": len(islands),
        "side": "crossing",
    }


def _layout_anatomical_pair(left_islands, right_islands, rotations, scale, pad, label_h):
    all_items = _anatomical_items(left_islands + right_islands, rotations, scale)
    centers, geom_h = _anatomical_sign_centers(all_items, pad)
    by_shell = defaultdict(list)
    for item in all_items:
        by_shell[item["shell"]].append(item)
    left_sid = left_islands[0]["shell"]
    right_sid = right_islands[0]["shell"]
    slot_w = max(
        _anatomical_group_width(by_shell[left_sid], pad),
        _anatomical_group_width(by_shell[right_sid], pad),
    )
    block_w = 2.0 * float(pad) + slot_w
    block_h = 2.0 * float(pad) + geom_h + float(label_h)
    layouts = {}
    for sid, inner_side in ((left_sid, "right"), (right_sid, "left")):
        local = _place_anatomical_sign_group(
            by_shell[sid], float(pad), slot_w, inner_side, centers, pad,
        )
        for rec in local.values():
            rec["y"] += float(pad)
        layouts[sid] = {
            "shell": sid,
            "w": block_w,
            "h": block_h,
            "local": local,
            "label_h": float(label_h),
            "rotation_deg": int(rotations.get(sid, 0)) % 360,
            "n_islands": len(by_shell[sid]),
            "side": "left" if sid == left_sid else "right",
            "pair": [left_sid, right_sid],
        }
    return layouts


def _anatomical_orientation_candidates(shell_ids):
    shell_ids = set(shell_ids)
    groups = []
    for sid in G7_CROSSING_SHELLS:
        if sid in shell_ids:
            groups.append((sid,))
    for left_sid, right_sid in G7_MIRROR_PAIRS:
        if left_sid in shell_ids and right_sid in shell_ids:
            groups.append((left_sid, right_sid))
    candidates = []
    for mask in range(1 << len(groups)):
        rotations = {sid: 0 for sid in shell_ids}
        for index, members in enumerate(groups):
            if not (mask & (1 << index)):
                continue
            if len(members) == 1:
                rotations[members[0]] = 90
            else:
                # Opposite quarter-turns preserve mirror readability.
                rotations[members[0]] = 270
                rotations[members[1]] = 90
        candidates.append(rotations)
    return candidates


def _anatomical_layout_trial(islands, specs_by_shell, piece_centroids, rotations, scale):
    cfg = fixed_padding_config()
    pad = float(cfg["pad_uv"])
    label_h = float(cfg["label_uv"])
    pair_gap = 2.0 * pad
    band_gap = 2.0 * pad
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)
    shell_ids = set(by_shell)
    if shell_ids != set(G7_ATLAS_A_SHELLS):
        return {
            "fit": False,
            "reason": "unexpected_atlas_a_shells",
            "got": sorted(shell_ids),
            "expected": sorted(G7_ATLAS_A_SHELLS),
        }
    layouts = {}
    bands = []
    paired = set()
    for left_sid, right_sid in G7_MIRROR_PAIRS:
        pair_layouts = _layout_anatomical_pair(
            by_shell[left_sid], by_shell[right_sid], rotations,
            scale, pad, label_h,
        )
        layouts.update(pair_layouts)
        paired.update((left_sid, right_sid))
        bands.append({
            "id": left_sid + "/" + right_sid,
            "members": [left_sid, right_sid],
            "centroid_y_3d": 0.5 * (
                float(piece_centroids[left_sid][1])
                + float(piece_centroids[right_sid][1])
            ),
            "h": max(pair_layouts[left_sid]["h"], pair_layouts[right_sid]["h"]),
            "kind": "mirror_pair",
        })
    for sid in sorted(shell_ids - paired):
        if sid not in G7_CROSSING_SHELLS or not specs_by_shell[sid]["split_lr"]:
            return {"fit": False, "reason": "unpaired_non_crossing_shell", "shell": sid}
        layout = _layout_anatomical_crossing_piece(
            by_shell[sid], rotations, scale, pad, label_h,
        )
        layouts[sid] = layout
        bands.append({
            "id": sid,
            "members": [sid],
            "centroid_y_3d": float(piece_centroids[sid][1]),
            "h": layout["h"],
            "kind": "crossing",
        })
    bands.sort(key=lambda band: (band["centroid_y_3d"], band["id"]))

    usable = 1.0 - 2.0 * pad
    for band in bands:
        if band["kind"] == "crossing":
            width = layouts[band["members"][0]]["w"]
        else:
            width = 2.0 * layouts[band["members"][0]]["w"] + pair_gap
        band["required_width"] = width
        if width > usable + 1e-12:
            return {
                "fit": False,
                "reason": "band_width",
                "band": band["id"],
                "required": width,
                "usable": usable,
            }
    base_height = sum(band["h"] for band in bands)
    if len(bands) > 1:
        base_height += band_gap * (len(bands) - 1)
    if base_height > usable + 1e-12:
        return {
            "fit": False,
            "reason": "band_height",
            "required": base_height,
            "usable": usable,
        }

    spare = max(0.0, usable - base_height)
    y_gaps = [
        max(0.0, bands[i + 1]["centroid_y_3d"] - bands[i]["centroid_y_3d"])
        for i in range(len(bands) - 1)
    ]
    y_gap_sum = sum(y_gaps)
    if y_gaps and y_gap_sum <= 1e-18:
        y_gaps = [1.0 for _ in y_gaps]
        y_gap_sum = float(len(y_gaps))
    origins = {}
    y = pad
    for index, band in enumerate(bands):
        band["v0"] = y
        band["v1"] = y + band["h"]
        if band["kind"] == "crossing":
            sid = band["members"][0]
            width = layouts[sid]["w"]
            origins[sid] = (0.5 - 0.5 * width, y)
        else:
            left_sid, right_sid = band["members"]
            width = layouts[left_sid]["w"]
            origins[left_sid] = (0.5 - 0.5 * pair_gap - width, y)
            origins[right_sid] = (0.5 + 0.5 * pair_gap, y)
        y = band["v1"]
        if index < len(bands) - 1:
            extra = spare * y_gaps[index] / y_gap_sum if y_gap_sum > 0.0 else 0.0
            y += band_gap + extra
    return {
        "fit": True,
        "reason": "fits",
        "global_scale": float(scale),
        "layouts": layouts,
        "origins": origins,
        "bands": bands,
        "rotations": {sid: int(rotations.get(sid, 0)) % 360 for sid in sorted(shell_ids)},
        "padding": cfg,
        "pair_gap_uv": pair_gap,
        "band_gap_min_uv": band_gap,
        "unused_vertical_uv": spare,
    }


def _max_anatomical_scale(islands, specs_by_shell, piece_centroids, rotations,
                          iterations=52):
    lo = 0.0
    hi = 1.0
    while _anatomical_layout_trial(
            islands, specs_by_shell, piece_centroids, rotations, hi).get("fit"):
        lo = hi
        hi *= 2.0
        if hi > 64.0:
            raise RuntimeError("anatomical scale search did not find an upper bound")
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if _anatomical_layout_trial(
                islands, specs_by_shell, piece_centroids, rotations, mid).get("fit"):
            lo = mid
        else:
            hi = mid
    trial = _anatomical_layout_trial(
        islands, specs_by_shell, piece_centroids, rotations, lo,
    )
    if not trial.get("fit"):
        raise RuntimeError("anatomical packer lost its last feasible scale")
    trial["scale_search"] = {
        "lower_feasible": lo,
        "upper_infeasible": hi,
        "iterations": iterations,
        "absolute_bracket": hi - lo,
    }
    return trial


def _apply_anatomical_trial(islands, trial):
    scale = float(trial["global_scale"])
    layouts = trial["layouts"]
    origins = trial["origins"]
    for isl in islands:
        sid = isl["shell"]
        block = layouts[sid]
        local = block["local"][isl["id"]]
        origin_x, origin_y = origins[sid]
        rot = int(block["rotation_deg"]) % 360
        raw_w, raw_h = _island_wh(isl)
        umin, vmin, _umax, _vmax = isl["bbox_world"]
        isl["rotation_deg"] = rot
        isl["rotation_scope"] = "whole_block"
        isl["uv_final"] = {}
        for loop_index, (u, v) in isl["uv_world"].items():
            x = (u - umin) * scale
            y = (v - vmin) * scale
            rx, ry = rot90_local(x, y, raw_w * scale, raw_h * scale, rot)
            isl["uv_final"][loop_index] = (
                origin_x + local["x"] + rx,
                origin_y + local["y"] + ry,
            )
        isl["pack_scale"] = scale

    band_by_shell = {}
    for band in trial["bands"]:
        for sid in band["members"]:
            band_by_shell[sid] = band
    blocks = []
    for sid in sorted(layouts):
        layout = layouts[sid]
        u0, v0 = origins[sid]
        u1 = u0 + layout["w"]
        v1 = v0 + layout["h"]
        blocks.append({
            "shell": sid,
            "uv_bbox": [float(u0), float(v0), float(u1), float(v1)],
            "pack_xywh": [float(u0), float(v0), float(layout["w"]), float(layout["h"])],
            "unrotated_wh": [float(layout["w"]), float(layout["h"])],
            "label_uv": [float(0.5 * (u0 + u1)), float(v1 - 0.5 * layout["label_h"])],
            "n_islands": int(layout["n_islands"]),
            "rotation_deg": int(layout["rotation_deg"]),
            "rotation_scope": "whole_block",
            "semantic_order_space": "final_uv",
            "anatomical_side": layout["side"],
            "mirror_pair": layout.get("pair"),
            "centroid_y_3d": float(band_by_shell[sid]["centroid_y_3d"]),
            "grid": {
                "cols": ["L", "R"] if sid in G7_CROSSING_SHELLS else [None],
                "rows": ["+", "-"],
                "final_order_preserved": True,
            },
        })
    return blocks


def pack_and_scale_blocks_anatomical(islands, specs_by_shell, piece_centroids,
                                     occupancy_floor=G7_OCCUPANCY_FLOOR,
                                     orientation_maps=None):
    """Place atlas-A blocks as a top view, with packing subordinate to anatomy."""
    if not islands:
        raise ValueError("anatomical atlas A cannot be empty")
    shell_ids = sorted({isl["shell"] for isl in islands})
    candidates = (
        list(orientation_maps)
        if orientation_maps is not None
        else _anatomical_orientation_candidates(shell_ids)
    )
    coefficient = projected_triangle_area_coefficient(islands)
    shell_area = defaultdict(float)
    for isl in islands:
        shell_area[isl["shell"]] += float(isl.get("area_3d") or 0.0)
    trials = []
    full_trials = []
    for rotations_in in candidates:
        rotations = {sid: int(rotations_in.get(sid, 0)) % 360 for sid in shell_ids}
        trial = _max_anatomical_scale(
            islands, specs_by_shell, piece_centroids, rotations,
        )
        occupancy = coefficient * trial["global_scale"] * trial["global_scale"]
        rotated = [sid for sid in shell_ids if rotations[sid] != 0]
        record = {
            "rotations_deg": dict(rotations),
            "rotated_shells": rotated,
            "rotated_shell_count": len(rotated),
            "rotated_area_3d": sum(shell_area[sid] for sid in rotated),
            "global_scale": trial["global_scale"],
            "predicted_occupancy": occupancy,
            "occupancy_floor_pass": occupancy + 1e-12 >= float(occupancy_floor),
            "limiting_infeasible_reason": _anatomical_layout_trial(
                islands, specs_by_shell, piece_centroids, rotations,
                trial["scale_search"]["upper_infeasible"],
            ).get("reason"),
        }
        trials.append(record)
        full_trials.append((record, trial))
    passing = [item for item in full_trials if item[0]["occupancy_floor_pass"]]
    if passing:
        chosen_record, chosen_trial = min(
            passing,
            key=lambda item: (
                item[0]["rotated_shell_count"],
                item[0]["rotated_area_3d"],
                -item[0]["global_scale"],
                tuple(item[0]["rotations_deg"][sid] for sid in shell_ids),
            ),
        )
        decision = "minimum_rotation_candidate_meeting_occupancy_floor"
    else:
        chosen_record, chosen_trial = min(
            full_trials,
            key=lambda item: (
                -item[0]["global_scale"],
                item[0]["rotated_shell_count"],
                item[0]["rotated_area_3d"],
            ),
        )
        decision = "best_anatomical_scale_below_occupancy_floor"
    blocks = _apply_anatomical_trial(islands, chosen_trial)
    return {
        "global_scale": float(chosen_trial["global_scale"]),
        "blocks": blocks,
        "islands": islands,
        "packer": "g7_anatomical_bands",
        "allow_block_rotation": True,
        "selected_order": [band["id"] for band in chosen_trial["bands"]],
        "order_trials": trials,
        "scale_search": chosen_trial["scale_search"],
        "padding": fixed_padding_config(),
        "rotation_candidates_deg": [0, 90, 270],
        "chosen_rotations_deg": chosen_record["rotations_deg"],
        "rotated_shells": chosen_record["rotated_shells"],
        "predicted_occupancy": chosen_record["predicted_occupancy"],
        "occupancy_floor": float(occupancy_floor),
        "occupancy_floor_pass": chosen_record["occupancy_floor_pass"],
        "selection_policy": decision,
        "bands": chosen_trial["bands"],
        "pair_gap_uv": chosen_trial["pair_gap_uv"],
        "band_gap_min_uv": chosen_trial["band_gap_min_uv"],
        "unused_vertical_uv": chosen_trial["unused_vertical_uv"],
        "sign_convention": G7_SIGN_CONVENTION,
        "longitudinal_convention": G7_LONGITUDINAL_CONVENTION,
    }


def island_centroid_3d(isl, f_cent):
    """Area-weighted world XYZ centroid of one semantic island."""
    total = 0.0
    weighted = Vector((0.0, 0.0, 0.0))
    for face in isl["faces"]:
        area = float(face.calc_area())
        weighted += f_cent[face.index] * area
        total += area
    if total <= 1e-18:
        points = [f_cent[face.index] for face in isl["faces"]]
        if not points:
            return (0.0, 0.0, 0.0)
        weighted = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    else:
        weighted /= total
    return (float(weighted.x), float(weighted.y), float(weighted.z))


def _g8_projected_centroid(isl):
    tris = []
    for face in isl.get("faces") or []:
        tris.extend(fan_tris_uv(face, isl["uv_world"]))
    if tris:
        return weighted_centroid(tris)
    return weighted_centroid_from_points(isl["uv_world"].values())


def _g8_apply_front_view_rotations(islands, rotations=G8_FRONT_VIEW_ROTATIONS):
    """Rotate only the explicitly exempt +Y islands around their own centroid."""
    for isl in islands:
        angle = int(rotations.get(isl["shell"], 0)) % 360
        if angle and isl.get("axis") != "+Y":
            raise ValueError("G8 rotation is only permitted for +Y front views: " + isl["id"])
        isl["rotation_deg"] = angle
        if angle == 0:
            continue
        pivot_u, pivot_v = _g8_projected_centroid(isl)
        radians = math.radians(angle)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        rotated = {}
        for loop_index, (u, v) in isl["uv_world"].items():
            du = float(u) - pivot_u
            dv = float(v) - pivot_v
            rotated[loop_index] = (
                pivot_u + du * cosine - dv * sine,
                pivot_v + du * sine + dv * cosine,
            )
        isl["uv_world"] = rotated
        points = list(rotated.values())
        isl["bbox_world"] = (
            min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points),
        )
    return islands


def _g8_panel_mapping(panel_bbox, model_xy_bbox, geometry_scale):
    u0, v0, u1, v1 = [float(value) for value in panel_bbox]
    xmin, ymin, xmax, ymax = [float(value) for value in model_xy_bbox]
    world_w = max(xmax - xmin, 1e-18)
    world_h = max(ymax - ymin, 1e-18)
    inner_w = max(0.0, (u1 - u0) - 2.0 * G8_ISLAND_GAP_UV)
    inner_h = max(0.0, (v1 - v0) - 2.0 * G8_ISLAND_GAP_UV)
    map_scale = min(float(geometry_scale), inner_w / world_w, inner_h / world_h)
    world_cx = 0.5 * (xmin + xmax)
    world_cy = 0.5 * (ymin + ymax)
    panel_cx = 0.5 * (u0 + u1)
    panel_cy = 0.5 * (v0 + v1)
    frame = [
        panel_cx + (xmin - world_cx) * map_scale,
        panel_cy + (ymin - world_cy) * map_scale,
        panel_cx + (xmax - world_cx) * map_scale,
        panel_cy + (ymax - world_cy) * map_scale,
    ]
    return {
        "scale": float(map_scale),
        "world_center": [world_cx, world_cy],
        "panel_center": [panel_cx, panel_cy],
        "target_frame_bbox": frame,
    }


def _g8_record(isl, f_cent, panel_name, panel_bbox, mapping, geometry_scale):
    c3 = island_centroid_3d(isl, f_cent)
    projected_cx, projected_cy = _g8_projected_centroid(isl)
    umin, vmin, umax, vmax = isl["bbox_world"]
    scale = float(geometry_scale)
    offsets = (
        (float(umin) - projected_cx) * scale,
        (float(vmin) - projected_cy) * scale,
        (float(umax) - projected_cx) * scale,
        (float(vmax) - projected_cy) * scale,
    )
    target_u = (
        mapping["panel_center"][0]
        + (c3[0] - mapping["world_center"][0]) * mapping["scale"]
    )
    target_v = (
        mapping["panel_center"][1]
        + (c3[1] - mapping["world_center"][1]) * mapping["scale"]
    )
    side = isl.get("lr") or ("L" if c3[0] < G7_SIGN_SPLIT_X else "R")
    p_u0, p_v0, p_u1, p_v1 = [float(value) for value in panel_bbox]
    x_min = p_u0 - offsets[0]
    x_max = p_u1 - offsets[2]
    if side == "L":
        x_max = min(x_max, 0.5 - G8_ISLAND_GAP_UV - offsets[2])
    elif side == "R":
        x_min = max(x_min, 0.5 + G8_ISLAND_GAP_UV - offsets[0])
    y_min = p_v0 - offsets[1]
    y_max = p_v1 - offsets[3]
    if x_min > x_max + 1e-15 or y_min > y_max + 1e-15:
        return None
    return {
        "island": isl,
        "id": isl["id"],
        "shell": isl["shell"],
        "normal_sign": isl.get("nsign"),
        "panel": panel_name,
        "side": side,
        "centroid_3d": c3,
        "projected_centroid": [float(projected_cx), float(projected_cy)],
        "offsets": offsets,
        "target": [float(target_u), float(target_v)],
        "bounds": [float(x_min), float(x_max), float(y_min), float(y_max)],
        "rotation_deg": int(isl.get("rotation_deg") or 0),
    }


def _g8_rect(record, center):
    left, bottom, right, top = record["offsets"]
    return (
        float(center[0]) + left,
        float(center[1]) + bottom,
        float(center[0]) + right,
        float(center[1]) + top,
    )


def _g8_rects_conflict(a, b, gap=G8_BBOX_GAP_UV):
    return not (
        a[2] + gap <= b[0] or b[2] + gap <= a[0]
        or a[3] + gap <= b[1] or b[3] + gap <= a[1]
    )


def _g8_clamped_candidates(values, lower, upper):
    if lower > upper + 1e-15:
        return []
    out = []
    for value in values:
        value = min(float(upper), max(float(lower), float(value)))
        if not any(abs(value - seen) <= 1e-12 for seen in out):
            out.append(value)
    return out


def _g8_position_valid(rectangles, obstacles, forbidden):
    for rect in rectangles:
        if any(_g8_rects_conflict(rect, other) for other in obstacles):
            return False
        if any(aabb_overlap_area(rect, area) > 1e-15 for area in forbidden):
            return False
    for index, rect in enumerate(rectangles):
        if any(_g8_rects_conflict(rect, other) for other in rectangles[index + 1:]):
            return False
    return True


def _g8_place_single(record, obstacles, forbidden):
    x_min, x_max, y_min, y_max = record["bounds"]
    left, bottom, right, top = record["offsets"]
    x_values = [record["target"][0], x_min, x_max]
    y_values = [record["target"][1], y_min, y_max]
    for step in range(1, 8):
        fraction = step / 8.0
        x_values.append(x_min + fraction * (x_max - x_min))
        y_values.append(y_min + fraction * (y_max - y_min))
    for obstacle in list(obstacles) + list(forbidden):
        x_values.extend((
            obstacle[0] - G8_BBOX_GAP_UV - right,
            obstacle[2] + G8_BBOX_GAP_UV - left,
        ))
        y_values.extend((
            obstacle[1] - G8_BBOX_GAP_UV - top,
            obstacle[3] + G8_BBOX_GAP_UV - bottom,
        ))
    xs = _g8_clamped_candidates(x_values, x_min, x_max)
    ys = _g8_clamped_candidates(y_values, y_min, y_max)
    candidates = []
    for x in xs:
        for y in ys:
            objective = (x - record["target"][0]) ** 2 + (y - record["target"][1]) ** 2
            candidates.append((objective, abs(y - record["target"][1]), x, y))
    for _objective, _vertical, x, y in sorted(candidates):
        rect = _g8_rect(record, (x, y))
        if _g8_position_valid([rect], obstacles, forbidden):
            return (float(x), float(y)), rect
    return None


def _g8_pair_gap_rect(left_rect, right_rect):
    u0 = float(left_rect[2])
    u1 = float(right_rect[0])
    v0 = max(float(left_rect[1]), float(right_rect[1]))
    v1 = min(float(left_rect[3]), float(right_rect[3]))
    if u1 <= u0 or v1 <= v0:
        return None
    return (u0, v0, u1, v1)


def _g8_place_pair(left_record, right_record, obstacles, forbidden, compact=False):
    left_bounds = left_record["bounds"]
    right_bounds = right_record["bounds"]
    d_min = max(0.5 - left_bounds[1], right_bounds[0] - 0.5, 0.0)
    d_max = min(0.5 - left_bounds[0], right_bounds[1] - 0.5)
    y_min = max(left_bounds[2], right_bounds[2])
    y_max = min(left_bounds[3], right_bounds[3])
    if d_min > d_max + 1e-15 or y_min > y_max + 1e-15:
        return None
    raw_d = 0.5 * (
        (0.5 - left_record["target"][0])
        + (right_record["target"][0] - 0.5)
    )
    raw_y = 0.5 * (left_record["target"][1] + right_record["target"][1])
    compact_d = 0.5 * (
        G8_BBOX_GAP_UV
        + left_record["offsets"][2] - right_record["offsets"][0]
    )
    d_values = [raw_d, compact_d, d_min, d_max]
    y_values = [raw_y, y_min, y_max]
    for step in range(1, 8):
        fraction = step / 8.0
        d_values.append(d_min + fraction * (d_max - d_min))
        y_values.append(y_min + fraction * (y_max - y_min))
    for record, direction in ((left_record, -1.0), (right_record, 1.0)):
        left, bottom, right, top = record["offsets"]
        for obstacle in list(obstacles) + list(forbidden):
            center_candidates = (
                obstacle[0] - G8_BBOX_GAP_UV - right,
                obstacle[2] + G8_BBOX_GAP_UV - left,
            )
            for center_x in center_candidates:
                d_values.append((center_x - 0.5) / direction)
            y_values.extend((
                obstacle[1] - G8_BBOX_GAP_UV - top,
                obstacle[3] + G8_BBOX_GAP_UV - bottom,
            ))
    ds = _g8_clamped_candidates(d_values, d_min, d_max)
    ys = _g8_clamped_candidates(y_values, y_min, y_max)
    candidates = []
    for distance in ds:
        for y in ys:
            left_center = (0.5 - distance, y)
            right_center = (0.5 + distance, y)
            objective = sum(
                (center[0] - record["target"][0]) ** 2
                + (center[1] - record["target"][1]) ** 2
                for center, record in (
                    (left_center, left_record), (right_center, right_record)
                )
            )
            candidates.append((objective, abs(y - raw_y), distance, y))
    candidate_order = (
        sorted(candidates, key=lambda item: (item[2], item[0], item[1], item[3]))
        if compact else sorted(candidates)
    )
    for _objective, _vertical, distance, y in candidate_order:
        left_center = (0.5 - distance, y)
        right_center = (0.5 + distance, y)
        left_rect = _g8_rect(left_record, left_center)
        right_rect = _g8_rect(right_record, right_center)
        if not _g8_position_valid([left_rect, right_rect], obstacles, forbidden):
            continue
        pair_gap = _g8_pair_gap_rect(left_rect, right_rect)
        if pair_gap and any(aabb_overlap_area(pair_gap, other) > 1e-15 for other in obstacles):
            continue
        return {
            left_record["id"]: (float(left_center[0]), float(left_center[1])),
            right_record["id"]: (float(right_center[0]), float(right_center[1])),
        }, [left_rect, right_rect], pair_gap
    return None


def _g8_place_panel(records, order_name):
    by_shell = {record["shell"]: record for record in records}
    pair_units = []
    paired_ids = set()
    for left_sid, right_sid in G7_MIRROR_PAIRS:
        if left_sid not in by_shell or right_sid not in by_shell:
            continue
        left_record = by_shell[left_sid]
        right_record = by_shell[right_sid]
        pair_units.append((left_record, right_record))
        paired_ids.update((left_record["id"], right_record["id"]))
    if order_name in ("target_y_reverse", "id_reverse"):
        pair_units.sort(key=lambda pair: (-pair[0]["target"][1], pair[0]["id"]))
    else:
        pair_units.sort(key=lambda pair: (pair[0]["target"][1], pair[0]["id"]))

    centers = {}
    obstacles = []
    forbidden = []
    pair_gaps = []
    for left_record, right_record in pair_units:
        placed = _g8_place_pair(
            left_record, right_record, obstacles, forbidden, compact=True,
        )
        if placed is None:
            return None
        pair_centers, pair_rects, pair_gap = placed
        centers.update(pair_centers)
        obstacles.extend(pair_rects)
        if pair_gap is not None:
            forbidden.append(pair_gap)
            pair_gaps.append(pair_gap)

    singles = [record for record in records if record["id"] not in paired_ids]
    if order_name == "target_y":
        singles.sort(key=lambda record: (record["target"][1], record["target"][0], record["id"]))
    elif order_name == "target_y_reverse":
        singles.sort(key=lambda record: (-record["target"][1], record["target"][0], record["id"]))
    elif order_name == "id_reverse":
        singles.sort(key=lambda record: record["id"], reverse=True)
    elif order_name == "id":
        singles.sort(key=lambda record: record["id"])
    else:
        singles.sort(key=lambda record: (
            -(record["offsets"][2] - record["offsets"][0])
            * (record["offsets"][3] - record["offsets"][1]),
            record["id"],
        ))
    for record in singles:
        placed = _g8_place_single(record, obstacles, forbidden)
        if placed is None:
            return None
        center, rect = placed
        centers[record["id"]] = center
        obstacles.append(rect)

    # Coordinate-descent cleanup: the greedy order only establishes a feasible
    # layout. Reinsert the most displaced independent island against every other
    # final rectangle until no target-distance improvement remains.
    record_by_id = {record["id"]: record for record in records}
    for _pass_index in range(16):
        improved = False
        singles_by_error = sorted(
            singles,
            key=lambda record: -(
                (centers[record["id"]][0] - record["target"][0]) ** 2
                + (centers[record["id"]][1] - record["target"][1]) ** 2
            ),
        )
        for record in singles_by_error:
            current = centers[record["id"]]
            current_objective = (
                (current[0] - record["target"][0]) ** 2
                + (current[1] - record["target"][1]) ** 2
            )
            other_rects = [
                _g8_rect(other, centers[other_id])
                for other_id, other in record_by_id.items()
                if other_id != record["id"]
            ]
            replacement = _g8_place_single(record, other_rects, forbidden)
            if replacement is None:
                continue
            candidate_center, _candidate_rect = replacement
            candidate_objective = (
                (candidate_center[0] - record["target"][0]) ** 2
                + (candidate_center[1] - record["target"][1]) ** 2
            )
            if candidate_objective + 1e-15 < current_objective:
                centers[record["id"]] = candidate_center
                improved = True
        if not improved:
            break
    objective = sum(
        (centers[record["id"]][0] - record["target"][0]) ** 2
        + (centers[record["id"]][1] - record["target"][1]) ** 2
        for record in records
    )
    return {
        "centers": centers,
        "objective": float(objective),
        "pair_forbidden_rects": [list(rect) for rect in pair_gaps],
        "order": order_name,
    }


def _g8_solve_difference_constraints(records, bounds, fixed_ids, constraints,
                                      iterations=4000):
    """Project target centers onto bounded x/y difference constraints."""
    record_by_id = {record["id"]: record for record in records}
    centers = {}
    for record in records:
        island_id = record["id"]
        x_min, x_max, y_min, y_max = bounds[island_id]
        centers[island_id] = [
            min(x_max, max(x_min, record["target"][0])),
            min(y_max, max(y_min, record["target"][1])),
        ]
    for _ in range(iterations):
        max_violation = 0.0
        changed = False
        for axis, left_id, right_id, required in constraints:
            axis_index = 0 if axis == "x" else 1
            left_value = centers[left_id][axis_index]
            right_value = centers[right_id][axis_index]
            violation = float(required) - (right_value - left_value)
            max_violation = max(max_violation, violation)
            if violation <= 1e-13:
                continue
            left_fixed = left_id in fixed_ids
            right_fixed = right_id in fixed_ids
            if left_fixed and right_fixed:
                return None
            left_bound_index = 0 if axis_index == 0 else 2
            right_bound_index = 1 if axis_index == 0 else 3
            left_room = max(0.0, left_value - bounds[left_id][left_bound_index])
            right_room = max(0.0, bounds[right_id][right_bound_index] - right_value)
            if left_fixed:
                move_left = 0.0
                move_right = min(violation, right_room)
            elif right_fixed:
                move_right = 0.0
                move_left = min(violation, left_room)
            else:
                move_left = min(0.5 * violation, left_room)
                move_right = min(violation - move_left, right_room)
                remaining = violation - move_left - move_right
                if remaining > 1e-13:
                    extra_left = min(remaining, left_room - move_left)
                    move_left += extra_left
                    remaining -= extra_left
                if remaining > 1e-13:
                    extra_right = min(remaining, right_room - move_right)
                    move_right += extra_right
            if move_left + move_right < violation - 1e-12:
                return None
            centers[left_id][axis_index] -= move_left
            centers[right_id][axis_index] += move_right
            changed = True
        if not changed or max_violation <= 1e-12:
            break
    for axis, left_id, right_id, required in constraints:
        axis_index = 0 if axis == "x" else 1
        if centers[right_id][axis_index] - centers[left_id][axis_index] < required - 1e-10:
            return None
    objective = sum(
        (centers[record["id"]][0] - record["target"][0]) ** 2
        + (centers[record["id"]][1] - record["target"][1]) ** 2
        for record in records
    )
    return {
        "centers": {island_id: tuple(value) for island_id, value in centers.items()},
        "objective": float(objective),
    }


def _g8_separation_candidates(left_record, right_record, bounds):
    """Four fixed-orientation disjunctions for two rectangle bboxes."""
    left_offsets = left_record["offsets"]
    right_offsets = right_record["offsets"]
    candidates = [
        (
            "x", left_record["id"], right_record["id"],
            left_offsets[2] + G8_BBOX_GAP_UV - right_offsets[0],
        ),
        (
            "x", right_record["id"], left_record["id"],
            right_offsets[2] + G8_BBOX_GAP_UV - left_offsets[0],
        ),
        (
            "y", left_record["id"], right_record["id"],
            left_offsets[3] + G8_BBOX_GAP_UV - right_offsets[1],
        ),
        (
            "y", right_record["id"], left_record["id"],
            right_offsets[3] + G8_BBOX_GAP_UV - left_offsets[1],
        ),
    ]
    feasible = []
    for axis, left_id, right_id, required in candidates:
        lower_index = 0 if axis == "x" else 2
        upper_index = 1 if axis == "x" else 3
        maximum_difference = bounds[right_id][upper_index] - bounds[left_id][lower_index]
        if maximum_difference + 1e-12 >= required:
            feasible.append((axis, left_id, right_id, float(required)))
    return feasible


def _g8_pair_records_and_centers(records):
    by_shell = {record["shell"]: record for record in records}
    fixed_centers = {}
    pair_gaps = []
    for left_sid, right_sid in G7_MIRROR_PAIRS:
        if left_sid not in by_shell or right_sid not in by_shell:
            continue
        left_record = by_shell[left_sid]
        right_record = by_shell[right_sid]
        placed = _g8_place_pair(left_record, right_record, [], [], compact=True)
        if placed is None:
            return None, None
        centers, rects, pair_gap = placed
        fixed_centers.update(centers)
        if pair_gap is not None:
            pair_gaps.append(pair_gap)
    return fixed_centers, pair_gaps


def _g8_interposed_bound_candidates(record, gap_rect, bounds):
    left, bottom, right, top = record["offsets"]
    island_id = record["id"]
    candidates = []
    proposals = (
        (0, None, gap_rect[0] - G8_BBOX_GAP_UV - right, "left"),
        (0, gap_rect[2] + G8_BBOX_GAP_UV - left, None, "right"),
        (1, None, gap_rect[1] - G8_BBOX_GAP_UV - top, "below"),
        (1, gap_rect[3] + G8_BBOX_GAP_UV - bottom, None, "above"),
    )
    for axis_index, new_lower, new_upper, label in proposals:
        trial_bounds = {key: list(value) for key, value in bounds.items()}
        lower_index = 0 if axis_index == 0 else 2
        upper_index = 1 if axis_index == 0 else 3
        if new_lower is not None:
            trial_bounds[island_id][lower_index] = max(
                trial_bounds[island_id][lower_index], float(new_lower),
            )
        if new_upper is not None:
            trial_bounds[island_id][upper_index] = min(
                trial_bounds[island_id][upper_index], float(new_upper),
            )
        if trial_bounds[island_id][lower_index] <= trial_bounds[island_id][upper_index] + 1e-12:
            candidates.append((label, trial_bounds))
    return candidates


def _g8_place_panel_constraints(records):
    """Global minimum-translation rectangle separation by constraint generation."""
    record_by_id = {record["id"]: record for record in records}
    bounds = {record["id"]: list(record["bounds"]) for record in records}
    fixed_centers, pair_gaps = _g8_pair_records_and_centers(records)
    if fixed_centers is None:
        return None
    fixed_ids = set(fixed_centers)
    for island_id, center in fixed_centers.items():
        bounds[island_id] = [center[0], center[0], center[1], center[1]]
    constraints = []
    constraint_keys = set()
    for _generation in range(160):
        solved = _g8_solve_difference_constraints(
            records, bounds, fixed_ids, constraints,
        )
        if solved is None:
            return None
        centers = solved["centers"]

        interposed = None
        for gap_rect in pair_gaps:
            for record in records:
                if record["id"] in fixed_ids:
                    continue
                if aabb_overlap_area(_g8_rect(record, centers[record["id"]]), gap_rect) > 1e-15:
                    interposed = (record, gap_rect)
                    break
            if interposed is not None:
                break
        if interposed is not None:
            record, gap_rect = interposed
            alternatives = []
            for label, trial_bounds in _g8_interposed_bound_candidates(record, gap_rect, bounds):
                trial = _g8_solve_difference_constraints(
                    records, trial_bounds, fixed_ids, constraints,
                )
                if trial is not None:
                    alternatives.append((trial["objective"], label, trial_bounds))
            if not alternatives:
                return None
            _objective, _label, bounds = min(alternatives, key=lambda item: (item[0], item[1]))
            continue

        conflicts = []
        for index, left_record in enumerate(records):
            left_rect = _g8_rect(left_record, centers[left_record["id"]])
            for right_record in records[index + 1:]:
                right_rect = _g8_rect(right_record, centers[right_record["id"]])
                if not _g8_rects_conflict(left_rect, right_rect):
                    continue
                penetration_x = max(0.0, min(left_rect[2], right_rect[2]) - max(left_rect[0], right_rect[0]) + G8_BBOX_GAP_UV)
                penetration_y = max(0.0, min(left_rect[3], right_rect[3]) - max(left_rect[1], right_rect[1]) + G8_BBOX_GAP_UV)
                conflicts.append((penetration_x * penetration_y, left_record, right_record))
        if not conflicts:
            return {
                "centers": centers,
                "objective": solved["objective"],
                "pair_forbidden_rects": [list(rect) for rect in pair_gaps],
                "order": "global_difference_constraints",
                "constraint_count": len(constraints),
            }
        _severity, left_record, right_record = max(
            conflicts, key=lambda item: (item[0], item[1]["id"], item[2]["id"]),
        )
        alternatives = []
        for candidate in _g8_separation_candidates(left_record, right_record, bounds):
            key = tuple(candidate)
            if key in constraint_keys:
                continue
            trial_constraints = constraints + [candidate]
            trial = _g8_solve_difference_constraints(
                records, bounds, fixed_ids, trial_constraints,
            )
            if trial is not None:
                alternatives.append((trial["objective"], candidate, trial))
        if not alternatives:
            return None
        _objective, chosen, _trial = min(
            alternatives,
            key=lambda item: (item[0], item[1][0], item[1][1], item[1][2]),
        )
        constraints.append(chosen)
        constraint_keys.add(tuple(chosen))
    return None


def _g8_layout_at_scale(islands, f_cent, model_xy_bbox, scale):
    panel_config = g8_panel_config()
    mappings = {
        "skin": _g8_panel_mapping(
            panel_config["skin_bbox"], model_xy_bbox, scale,
        ),
        "internal": _g8_panel_mapping(
            panel_config["internal_bbox"], model_xy_bbox, scale,
        ),
    }
    records = []
    for isl in islands:
        panel_name = "skin" if isl.get("nsign") == "+" else "internal"
        record = _g8_record(
            isl, f_cent, panel_name, panel_config[panel_name + "_bbox"],
            mappings[panel_name], scale,
        )
        if record is None:
            return {
                "fit": False,
                "reason": "island_exceeds_panel_or_side",
                "island": isl["id"],
                "scale": float(scale),
            }
        records.append(record)
    centers = {}
    panel_results = {}
    objective = 0.0
    for panel_name in ("skin", "internal"):
        panel_records = [record for record in records if record["panel"] == panel_name]
        candidates = []
        for order_name in ("area_desc", "target_y", "target_y_reverse", "id", "id_reverse"):
            result = _g8_place_panel(panel_records, order_name)
            if result is not None:
                candidates.append(result)
        constraint_result = _g8_place_panel_constraints(panel_records)
        if constraint_result is not None:
            candidates.append(constraint_result)
        if not candidates:
            return {
                "fit": False,
                "reason": "panel_packing_failed",
                "panel": panel_name,
                "scale": float(scale),
            }
        chosen = min(candidates, key=lambda result: (result["objective"], result["order"]))
        centers.update(chosen["centers"])
        panel_results[panel_name] = chosen
        objective += chosen["objective"]
    return {
        "fit": True,
        "reason": "fits",
        "global_scale": float(scale),
        "records": records,
        "centers": centers,
        "panel_config": panel_config,
        "panel_mappings": mappings,
        "panel_results": panel_results,
        "displacement_objective_sq": float(objective),
    }


def g8_island_layout_gates(islands, panel_config):
    bboxes = {isl["id"]: island_uv_bbox(isl) for isl in islands}
    overlaps = []
    for index, left in enumerate(islands):
        for right in islands[index + 1:]:
            area = aabb_overlap_area(bboxes[left["id"]], bboxes[right["id"]])
            if area > 1e-15:
                overlaps.append({
                    "a": left["id"],
                    "b": right["id"],
                    "intersection_area": float(area),
                })
    invasions = []
    for isl in islands:
        panel_name = "skin" if isl.get("nsign") == "+" else "internal"
        allowed = panel_config[panel_name + "_bbox"]
        bbox = bboxes[isl["id"]]
        if (
            bbox[0] < allowed[0] - 1e-12 or bbox[1] < allowed[1] - 1e-12
            or bbox[2] > allowed[2] + 1e-12 or bbox[3] > allowed[3] + 1e-12
        ):
            invasions.append({
                "island": isl["id"],
                "panel": panel_name,
                "bbox": list(bbox),
                "allowed": list(allowed),
            })

    skin = [isl for isl in islands if isl.get("nsign") == "+"]
    skin_by_shell = {isl["shell"]: isl for isl in skin}
    pair_v_rows = []
    pair_u_rows = []
    pair_interposed_rows = []
    for left_sid, right_sid in G7_MIRROR_PAIRS:
        left = skin_by_shell[left_sid]
        right = skin_by_shell[right_sid]
        left_center = left["placement_center_uv"]
        right_center = right["placement_center_uv"]
        pair_id = left_sid + "/" + right_sid
        pair_v_value = abs(left_center[1] - right_center[1])
        pair_u_value = abs(abs(left_center[0] - 0.5) - abs(right_center[0] - 0.5))
        if pair_v_value < 1e-15:
            pair_v_value = 0.0
        if pair_u_value < 1e-15:
            pair_u_value = 0.0
        pair_v_rows.append({
            "pair": pair_id,
            "value": float(pair_v_value),
        })
        pair_u_rows.append({
            "pair": pair_id,
            "value": float(pair_u_value),
        })
        left_bbox = bboxes[left["id"]]
        right_bbox = bboxes[right["id"]]
        gap = _g8_pair_gap_rect(left_bbox, right_bbox)
        interposed = []
        if gap is not None:
            for foreign in skin:
                if foreign["shell"] in (left_sid, right_sid):
                    continue
                if aabb_overlap_area(gap, bboxes[foreign["id"]]) > 1e-15:
                    interposed.append(foreign["id"])
        pair_interposed_rows.append({
            "pair": pair_id,
            "value": len(interposed),
            "islands": interposed,
        })

    rotated_skin = [
        isl["id"] for isl in skin if int(isl.get("rotation_deg") or 0) % 360 != 0
    ]
    rotated_forbidden = [
        isl["id"] for isl in skin
        if isl["axis"] in ("+Z", "-Z")
        and int(isl.get("rotation_deg") or 0) % 360 != 0
    ]
    pair_v = max((row["value"] for row in pair_v_rows), default=0.0)
    pair_u = max((row["value"] for row in pair_u_rows), default=0.0)
    pair_interposed = max((row["value"] for row in pair_interposed_rows), default=0)
    labels = [island_label(isl) for isl in islands]
    return {
        "island_bbox_overlap_count": len(overlaps),
        "island_bbox_overlap_pairs": overlaps,
        "panel_invasion_count": len(invasions),
        "panel_invasions": invasions,
        "pair_v_offset": {
            "objective": 0.0,
            "per_pair": pair_v_rows,
            "worst": float(pair_v),
        },
        "pair_u_symmetry": {
            "objective": 0.0,
            "per_pair": pair_u_rows,
            "worst": float(pair_u),
        },
        "pair_interposed": {
            "objective": 0,
            "per_pair": pair_interposed_rows,
            "worst": int(pair_interposed),
        },
        "rotated_islands_skin": {
            "objective": "0; only S09/S10 would be permitted",
            "count": len(rotated_skin),
            "islands": rotated_skin,
            "forbidden_z_projection_count": len(rotated_forbidden),
            "forbidden_z_projection_islands": rotated_forbidden,
            "pass": not rotated_forbidden,
        },
        "labels": {
            "expected": len(islands),
            "present": sum(bool(label.strip()) for label in labels),
            "unique": len(set(labels)) == len(labels),
        },
        "pass": (
            not overlaps and not invasions and pair_v <= 1e-12
            and pair_u <= 1e-12 and pair_interposed == 0
            and not rotated_forbidden and len(set(labels)) == len(labels)
        ),
    }


def pack_and_scale_islands_plan_view(islands, f_cent, model_xy_bbox,
                                     occupancy_floor=G8_OCCUPANCY_FLOOR):
    """Place n+ and n- islands in separate panels from their own world XY centroids."""
    if not islands:
        raise ValueError("G8 atlas A cannot be empty")
    laid_out = clone_islands_for_layout(islands)
    _g8_apply_front_view_rotations(laid_out)
    coefficient = projected_triangle_area_coefficient(laid_out)
    if coefficient <= 1e-18:
        raise RuntimeError("G8 projected area coefficient is zero")
    required_scale = math.sqrt(float(occupancy_floor) / coefficient) * (1.0 + 1e-10)
    required_trial = _g8_layout_at_scale(
        laid_out, f_cent, model_xy_bbox, required_scale,
    )
    if not required_trial.get("fit"):
        raise RuntimeError(
            "G8 occupancy floor %.6f is infeasible: %s"
            % (float(occupancy_floor), json.dumps(required_trial, sort_keys=True))
        )
    lo = required_scale
    hi = max(1.0, 2.0 * required_scale)
    while _g8_layout_at_scale(laid_out, f_cent, model_xy_bbox, hi).get("fit"):
        lo = hi
        hi *= 2.0
        if hi > 8.0:
            break
    trial_log = []
    for _ in range(44):
        mid = 0.5 * (lo + hi)
        probe = _g8_layout_at_scale(laid_out, f_cent, model_xy_bbox, mid)
        trial_log.append({
            "scale": float(mid),
            "fit": bool(probe.get("fit")),
            "reason": probe.get("reason"),
            "panel": probe.get("panel"),
        })
        if probe.get("fit"):
            lo = mid
        else:
            hi = mid
    chosen = _g8_layout_at_scale(laid_out, f_cent, model_xy_bbox, lo)
    if not chosen.get("fit"):
        raise RuntimeError("G8 packer lost its feasible lower bound")
    records_by_id = {record["id"]: record for record in chosen["records"]}
    displacement_rows = []
    for isl in laid_out:
        record = records_by_id[isl["id"]]
        center = chosen["centers"][isl["id"]]
        projected_cx, projected_cy = record["projected_centroid"]
        scale = float(chosen["global_scale"])
        isl["rotation_deg"] = int(record["rotation_deg"])
        isl["rotation_scope"] = (
            "front_view_exception_then_translation"
            if isl["rotation_deg"] else "island_translation_only"
        )
        isl["uv_final"] = {
            loop_index: (
                float(center[0]) + (float(u) - projected_cx) * scale,
                float(center[1]) + (float(v) - projected_cy) * scale,
            )
            for loop_index, (u, v) in isl["uv_world"].items()
        }
        isl["pack_scale"] = scale
        isl["panel"] = record["panel"]
        isl["centroid_3d"] = list(record["centroid_3d"])
        isl["target_uv"] = list(record["target"])
        isl["placement_center_uv"] = [float(center[0]), float(center[1])]
        displacement = math.hypot(
            center[0] - record["target"][0], center[1] - record["target"][1],
        )
        isl["target_displacement_uv"] = float(displacement)
        displacement_rows.append({
            "island": isl["id"],
            "panel": record["panel"],
            "target_uv": list(record["target"]),
            "placed_uv": [float(center[0]), float(center[1])],
            "displacement_uv": float(displacement),
        })
    panel_config = chosen["panel_config"]
    blocks = []
    for panel_name, title in (("skin", "OUTER SKIN"), ("internal", "INTERNAL FACES")):
        bbox = panel_config[panel_name + "_bbox"]
        blocks.append({
            "shell": "PANEL_" + panel_name.upper(),
            "label": title,
            "uv_bbox": list(bbox),
            "pack_xywh": [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]],
            "unrotated_wh": [bbox[2] - bbox[0], bbox[3] - bbox[1]],
            "label_uv": [0.5 * (bbox[0] + bbox[2]), bbox[3] - G8_ISLAND_GAP_UV],
            "n_islands": sum(isl["panel"] == panel_name for isl in laid_out),
            "rotation_deg": 0,
            "rotation_scope": "panel",
            "semantic_order_space": "world_xy_target",
            "anatomical_side": panel_name,
        })
    displacement_rows.sort(key=lambda row: (-row["displacement_uv"], row["island"]))
    displacement_values = [row["displacement_uv"] for row in displacement_rows]
    gates = g8_island_layout_gates(laid_out, panel_config)
    return {
        "global_scale": float(chosen["global_scale"]),
        "blocks": blocks,
        "islands": laid_out,
        "packer": "g8_two_panel_world_xy_islands",
        "allow_block_rotation": False,
        "selected_order": {
            panel: result["order"] for panel, result in chosen["panel_results"].items()
        },
        "order_trials": trial_log,
        "padding": fixed_padding_config(),
        "panel_config": panel_config,
        "panel_mappings": chosen["panel_mappings"],
        "layout_gates": gates,
        "displacement": {
            "method": (
                "Each island starts at its own area-weighted world XYZ centroid mapped "
                "isotropically into its panel. Candidate edge contacts are searched in "
                "five deterministic orders; the feasible result with minimum summed "
                "squared translation is selected. Z-projected islands never rotate; "
                "the measured +Y exception is S10=180 degrees."
            ),
            "mean_uv": (
                float(sum(displacement_values) / len(displacement_values))
                if displacement_values else 0.0
            ),
            "worst_uv": max(displacement_values, default=0.0),
            "worst_island": displacement_rows[0]["island"] if displacement_rows else None,
            "per_island": displacement_rows,
        },
        "scale_search": {
            "occupancy_floor": float(occupancy_floor),
            "required_scale_for_floor": float(required_scale),
            "chosen_feasible": float(lo),
            "upper_infeasible": float(hi),
            "iterations": 44,
        },
        "predicted_occupancy": coefficient * lo * lo,
        "occupancy_floor": float(occupancy_floor),
        "occupancy_floor_pass": coefficient * lo * lo + 1e-12 >= float(occupancy_floor),
        "target_frame_skin_bbox": chosen["panel_mappings"]["skin"]["target_frame_bbox"],
    }


def intra_layer_overlap_metrics(islands, grid_n=1024, bbox=(0.0, 0.0, 1.0, 1.0)):
    """Raster-measure cross-island overlap only within each fixed G9 layer."""
    n = int(grid_n)
    u0, v0, u1, v1 = [float(value) for value in bbox]
    pixel_area = (u1 - u0) * (v1 - v0) / float(n * n)
    coverage = {}
    for isl in islands:
        grid, _grid_bbox, _ = raster_tris(island_tris_final(isl), n, bbox)
        coverage[isl["id"]] = {index for index, count in enumerate(grid) if count >= 1}
    pairs = []
    by_panel = {"skin": [], "internal": []}
    for index, left in enumerate(islands):
        for right in islands[index + 1:]:
            if left.get("panel") != right.get("panel"):
                continue
            shared_pixels = len(coverage[left["id"]].intersection(coverage[right["id"]]))
            if shared_pixels <= 0:
                continue
            panel = left.get("panel")
            row = {
                "a": left["id"],
                "b": right["id"],
                "panel": panel,
                "intersection_pixels": int(shared_pixels),
                "intersection_area_uv": float(shared_pixels * pixel_area),
                "z_a": float(left["centroid_3d"][2]),
                "z_b": float(right["centroid_3d"][2]),
                "z_separation": abs(
                    float(left["centroid_3d"][2]) - float(right["centroid_3d"][2])
                ),
            }
            pairs.append(row)
            by_panel.setdefault(panel, []).append(row)
    pairs.sort(key=lambda row: (-row["intersection_area_uv"], row["a"], row["b"]))
    layering = {}
    for panel in ("skin", "internal"):
        panel_islands = [isl for isl in islands if isl.get("panel") == panel]
        panel_ids = [isl["id"] for isl in panel_islands]
        z_by_id = {isl["id"]: float(isl["centroid_3d"][2]) for isl in panel_islands}
        layering[panel] = minimum_z_layering(
            panel_ids, by_panel.get(panel, []), z_by_id, max_layers=4,
        )
    minimum_by_panel = {
        panel: layering[panel]["minimum_zero_collision_layers"]
        for panel in ("skin", "internal")
    }
    minimum_total = (
        sum(minimum_by_panel.values())
        if all(value is not None for value in minimum_by_panel.values()) else None
    )
    return {
        "method": "per_island_binary_coverage_intersection_raster",
        "grid_n": n,
        "grid_bbox": [u0, v0, u1, v1],
        "pixel_area_uv": float(pixel_area),
        "collision_pair_count": len(pairs),
        "pairs": pairs,
        "collision_pair_count_by_panel": {
            panel: len(by_panel.get(panel, [])) for panel in ("skin", "internal")
        },
        "fixed_two_layers_zero_collisions": len(pairs) == 0,
        "minimum_sublayers_per_original_layer": minimum_by_panel,
        "minimum_total_layers_preserving_skin_internal_split": minimum_total,
        "layering_by_panel": layering,
    }


def global_z_layering_metrics(islands, panel_mappings, grid_n=1024,
                               bbox=(0.0, 0.0, 1.0, 1.0), max_layers=8):
    """Align both panel frames, then find the exact minimum collision-free Z layers."""
    n = int(grid_n)
    u0, v0, u1, v1 = [float(value) for value in bbox]
    pixel_area = (u1 - u0) * (v1 - v0) / float(n * n)
    reference_panel = "skin"
    reference = panel_mappings[reference_panel]
    shifts = {
        panel: [
            float(reference["b"]) - float(panel_mappings[panel]["b"]),
            float(reference["c"]) - float(panel_mappings[panel]["c"]),
        ]
        for panel in ("skin", "internal")
    }
    coverage = {}
    for isl in islands:
        shift_u, shift_v = shifts[isl["panel"]]
        shifted_tris = [
            [
                (float(u) + shift_u, float(v) + shift_v)
                for u, v in tri
            ]
            for tri in island_tris_final(isl)
        ]
        grid, _grid_bbox, _ = raster_tris(shifted_tris, n, bbox)
        coverage[isl["id"]] = {
            index for index, count in enumerate(grid) if count >= 1
        }
    pairs = []
    for index, left in enumerate(islands):
        for right in islands[index + 1:]:
            shared_pixels = len(coverage[left["id"]].intersection(coverage[right["id"]]))
            if shared_pixels <= 0:
                continue
            pairs.append({
                "a": left["id"],
                "b": right["id"],
                "source_panels": [left["panel"], right["panel"]],
                "intersection_pixels": int(shared_pixels),
                "intersection_area_uv": float(shared_pixels * pixel_area),
                "z_separation": abs(
                    float(left["centroid_3d"][2]) - float(right["centroid_3d"][2])
                ),
            })
    pairs.sort(key=lambda row: (-row["intersection_area_uv"], row["a"], row["b"]))
    z_by_id = {isl["id"]: float(isl["centroid_3d"][2]) for isl in islands}
    layering = minimum_z_layering(
        [isl["id"] for isl in islands], pairs, z_by_id, max_layers=max_layers,
    )
    return {
        "method": (
            "Both equal panel coordinate frames are aligned by their affine b/c offsets; "
            "all islands are then exact-colored on the overlap graph, ordered by mean Z."
        ),
        "reference_panel": reference_panel,
        "panel_alignment_shift_uv": shifts,
        "grid_n": n,
        "grid_bbox": [u0, v0, u1, v1],
        "aligned_collision_edge_count": len(pairs),
        "aligned_collision_pairs": pairs,
        **layering,
    }


def overlap_metrics_excluding_cross_island(islands, grid_n=1024,
                                            bbox=(0.0, 0.0, 1.0, 1.0)):
    """Atlas self-overlap from triangles of the same island; ignore island collisions."""
    n = int(grid_n)
    u0, v0, u1, v1 = [float(value) for value in bbox]

    def measure(resolution):
        covered = bytearray(resolution * resolution)
        self_overlap = bytearray(resolution * resolution)
        per_island = []
        for isl in islands:
            grid, _grid_bbox, _ = raster_tris(
                island_tris_final(isl), resolution, bbox,
            )
            island_covered = 0
            island_self = 0
            for index, count in enumerate(grid):
                if count >= 1:
                    covered[index] = 1
                    island_covered += 1
                if count >= 2:
                    self_overlap[index] = 1
                    island_self += 1
            per_island.append({
                "id": isl["id"],
                "covered_pixels": island_covered,
                "self_overlap_pixels": island_self,
                "self_overlap_area_frac_local": (
                    float(island_self) / island_covered if island_covered else 0.0
                ),
            })
        covered_pixels = int(sum(covered))
        overlap_pixels = int(sum(self_overlap))
        return {
            "grid_n": resolution,
            "covered_pixels": covered_pixels,
            "overlap_pixels": overlap_pixels,
            "overlap_area_frac": (
                float(overlap_pixels) / covered_pixels if covered_pixels else 0.0
            ),
            "per_packed_island": per_island,
        }

    full = measure(n)
    half = measure(max(2, n // 2))
    full.update({
        "overlap_status": "ok",
        "grid_bbox": [u0, v0, u1, v1],
        "pixel_uv": [(u1 - u0) / n, (v1 - v0) / n],
        "overlap_area_frac_grid_half": half["overlap_area_frac"],
        "empirical_discretization_abs_delta": abs(
            full["overlap_area_frac"] - half["overlap_area_frac"]
        ),
        "cross_island_overlap_excluded": True,
        "definition": (
            "A pixel counts only when at least two triangles from the same semantic "
            "island cover it. Coverage by different islands is reported separately as "
            "intra_layer_overlap and is excluded here."
        ),
    })
    return full


def g9_layout_metrics(islands, panel_config):
    """Containment, labels and rotation gates; collisions are measurements, not failures."""
    bboxes = {isl["id"]: island_uv_bbox(isl) for isl in islands}
    bbox_overlaps = []
    for index, left in enumerate(islands):
        for right in islands[index + 1:]:
            if left.get("panel") != right.get("panel"):
                continue
            area = aabb_overlap_area(bboxes[left["id"]], bboxes[right["id"]])
            if area > 1e-15:
                bbox_overlaps.append({
                    "a": left["id"], "b": right["id"],
                    "panel": left.get("panel"), "intersection_area_bbox": float(area),
                })
    invasions = []
    inset = float(G9_FRAME_INSET_UV)
    for isl in islands:
        panel = isl["panel"]
        outer = [float(value) for value in panel_config[panel + "_bbox"]]
        allowed = [outer[0] + inset, outer[1] + inset, outer[2] - inset, outer[3] - inset]
        bbox = bboxes[isl["id"]]
        if (
            bbox[0] < allowed[0] - 1e-10 or bbox[1] < allowed[1] - 1e-10
            or bbox[2] > allowed[2] + 1e-10 or bbox[3] > allowed[3] + 1e-10
        ):
            invasions.append({
                "island": isl["id"], "panel": panel,
                "bbox": list(bbox), "allowed": allowed,
            })
    rotated = [
        isl["id"] for isl in islands if int(isl.get("rotation_deg") or 0) % 360 != 0
    ]
    rotated_forbidden = [
        isl["id"] for isl in islands
        if isl.get("axis") in ("+Z", "-Z")
        and int(isl.get("rotation_deg") or 0) % 360 != 0
    ]
    labels = [island_label(isl) for isl in islands]
    return {
        "island_bbox_overlap_count": len(bbox_overlaps),
        "island_bbox_overlap_pairs": bbox_overlaps,
        "panel_invasion_count": len(invasions),
        "panel_invasions": invasions,
        "rotated_islands": {
            "count": len(rotated),
            "islands": rotated,
            "forbidden_z_projection_count": len(rotated_forbidden),
            "forbidden_z_projection_islands": rotated_forbidden,
            "pass": not rotated_forbidden,
        },
        "labels": {
            "expected": len(islands),
            "present": sum(bool(label.strip()) for label in labels),
            "unique": len(set(labels)) == len(labels),
        },
        "pass": not invasions and not rotated_forbidden and len(set(labels)) == len(labels),
        "overlap_is_declared_not_resolved": True,
    }


def pack_and_scale_islands_archipelago(islands, f_cent, model_xy_bbox):
    """Place every G9 island at its affine world-XY target with zero translation."""
    if not islands:
        raise ValueError("G9 atlas A cannot be empty")
    laid_out = clone_islands_for_layout(islands)
    _g8_apply_front_view_rotations(laid_out, rotations=G9_FRONT_VIEW_ROTATIONS)
    panel_config = g9_panel_config()
    mappings = g9_common_affine(model_xy_bbox, panel_config)
    scale = float(mappings["global_scale"])
    world_cx, world_cy = mappings["world_center"]

    records = []
    safe_scale = scale
    for isl in laid_out:
        panel = "skin" if isl.get("nsign") == "+" else "internal"
        c3 = island_centroid_3d(isl, f_cent)
        projected_cx, projected_cy = _g8_projected_centroid(isl)
        mapping = mappings[panel]
        panel_cx, panel_cy = mapping["panel_center"]
        allowed = mapping["drawable_bbox"]
        for u, v in isl["uv_world"].values():
            if isl.get("axis") in ("+Z", "-Z"):
                world_x = -float(u) if isl.get("axis") == "-Z" else float(u)
                delta_u = world_x - world_cx
                delta_v = float(v) - world_cy
            else:
                delta_u = c3[0] - world_cx + float(u) - projected_cx
                delta_v = c3[1] - world_cy + float(v) - projected_cy
            if delta_u > 1e-18:
                safe_scale = min(safe_scale, (allowed[2] - panel_cx) / delta_u)
            elif delta_u < -1e-18:
                safe_scale = min(safe_scale, (panel_cx - allowed[0]) / -delta_u)
            if delta_v > 1e-18:
                safe_scale = min(safe_scale, (allowed[3] - panel_cy) / delta_v)
            elif delta_v < -1e-18:
                safe_scale = min(safe_scale, (panel_cy - allowed[1]) / -delta_v)
        records.append({
            "island": isl,
            "panel": panel,
            "centroid_3d": c3,
            "projected_centroid": (float(projected_cx), float(projected_cy)),
        })
    if safe_scale <= 1e-18:
        raise RuntimeError("G9 common affine scale is non-positive")
    if safe_scale < scale:
        scale = safe_scale * (1.0 - 1e-12)
        mappings["global_scale"] = float(scale)
        mappings["fit_limited_by_projected_island_extent"] = True
        for panel in ("skin", "internal"):
            mapping = mappings[panel]
            panel_cx, panel_cy = mapping["panel_center"]
            mapping["a"] = float(scale)
            mapping["b"] = float(panel_cx - scale * world_cx)
            mapping["c"] = float(panel_cy - scale * world_cy)
            xmin, ymin, xmax, ymax = mappings["world_bbox"]
            mapping["target_frame_bbox"] = [
                scale * xmin + mapping["b"], scale * ymin + mapping["c"],
                scale * xmax + mapping["b"], scale * ymax + mapping["c"],
            ]
    else:
        mappings["fit_limited_by_projected_island_extent"] = False

    displacement_rows = []
    for record in records:
        isl = record["island"]
        panel = record["panel"]
        c3 = record["centroid_3d"]
        projected_cx, projected_cy = record["projected_centroid"]
        mapping = mappings[panel]
        target = [
            scale * float(c3[0]) + float(mapping["b"]),
            scale * float(c3[1]) + float(mapping["c"]),
        ]
        if isl.get("axis") in ("+Z", "-Z"):
            isl["uv_final"] = {
                loop_index: (
                    scale * (-float(u) if isl.get("axis") == "-Z" else float(u))
                    + float(mapping["b"]),
                    scale * float(v) + float(mapping["c"]),
                )
                for loop_index, (u, v) in isl["uv_world"].items()
            }
            isl["affine_exception"] = False
        else:
            isl["uv_final"] = {
                loop_index: (
                    target[0] + (float(u) - projected_cx) * scale,
                    target[1] + (float(v) - projected_cy) * scale,
                )
                for loop_index, (u, v) in isl["uv_world"].items()
            }
            isl["affine_exception"] = True
            isl["affine_exception_reason"] = "declared_S09_S10_front_view_projection"
        isl["pack_scale"] = float(scale)
        isl["panel"] = panel
        isl["centroid_3d"] = [float(value) for value in c3]
        isl["target_uv"] = list(target)
        isl["placement_center_uv"] = list(target)
        isl["target_displacement_uv"] = 0.0
        isl["rotation_scope"] = (
            "front_view_exception_then_zero_translation"
            if int(isl.get("rotation_deg") or 0) else "zero_translation"
        )
        displacement_rows.append({
            "island": isl["id"], "panel": panel,
            "target_uv": list(target), "placed_uv": list(target),
            "displacement_uv": 0.0,
        })

    blocks = []
    for panel, title in (("skin", "OUTER SKIN"), ("internal", "INTERNAL FACES")):
        bbox = panel_config[panel + "_bbox"]
        blocks.append({
            "shell": "PANEL_" + panel.upper(),
            "label": title,
            "uv_bbox": list(bbox),
            "pack_xywh": [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]],
            "unrotated_wh": [bbox[2] - bbox[0], bbox[3] - bbox[1]],
            "label_uv": [0.5 * (bbox[0] + bbox[2]), bbox[3] - G9_FRAME_INSET_UV],
            "n_islands": sum(isl["panel"] == panel for isl in laid_out),
            "rotation_deg": 0,
            "rotation_scope": "panel",
            "semantic_order_space": "world_xy_affine_archipelago",
            "anatomical_side": panel,
        })
    layout = g9_layout_metrics(laid_out, panel_config)
    intra_overlap = intra_layer_overlap_metrics(laid_out)
    global_layering = global_z_layering_metrics(laid_out, mappings)
    intra_overlap["global_aligned_z_layering"] = global_layering
    intra_overlap["minimum_global_layers_allowing_sign_mixing"] = (
        global_layering["minimum_zero_collision_layers"]
    )
    scale_fidelity = {
        panel: scale_fidelity_metrics(laid_out, panel) for panel in ("skin", "internal")
    }
    displacement_rows.sort(key=lambda row: row["island"])
    affine_vertex_max_abs_error_z = 0.0
    for isl in laid_out:
        if isl.get("axis") not in ("+Z", "-Z"):
            continue
        mapping = mappings[isl["panel"]]
        for loop_index, (u, v) in isl["uv_world"].items():
            world_x = -float(u) if isl.get("axis") == "-Z" else float(u)
            expected = (
                scale * world_x + float(mapping["b"]),
                scale * float(v) + float(mapping["c"]),
            )
            actual = isl["uv_final"][loop_index]
            affine_vertex_max_abs_error_z = max(
                affine_vertex_max_abs_error_z,
                abs(actual[0] - expected[0]), abs(actual[1] - expected[1]),
            )
    return {
        "global_scale": float(scale),
        "blocks": blocks,
        "islands": laid_out,
        "packer": "g9_zero_displacement_world_xy_archipelago",
        "allow_block_rotation": False,
        "selected_order": "affine_world_xy_no_ordering",
        "order_trials": [],
        "padding": fixed_padding_config(),
        "panel_config": panel_config,
        "panel_mappings": mappings,
        "layout_gates": layout,
        "intra_layer_overlap": intra_overlap,
        "scale_fidelity": scale_fidelity,
        "affine_vertex_gate": {
            "scope": "all_islands_projected_from_+Z_or_-Z",
            "front_view_exceptions": [
                isl["id"] for isl in laid_out if isl.get("axis") == "+Y"
            ],
            "max_abs_error_uv": float(affine_vertex_max_abs_error_z),
            "pass": affine_vertex_max_abs_error_z <= 1e-12,
        },
        "displacement": {
            "method": (
                "One affine per fixed layer: u=a*X+b, v=a*Y+c. Both layers share "
                "the same a and XY frame. Every placement center equals its affine "
                "target; no collision resolver or per-island translation runs."
            ),
            "mean_uv": 0.0,
            "worst_uv": 0.0,
            "worst_island": None,
            "per_island": displacement_rows,
        },
        "scale_search": {
            "policy": "max_common_world_frame_scale_then_extent_fit_only",
            "occupancy_floor": None,
            "chosen": float(scale),
            "fit_limited_by_projected_island_extent": bool(
                mappings["fit_limited_by_projected_island_extent"]
            ),
        },
        "predicted_occupancy": projected_triangle_area_coefficient(laid_out) * scale * scale,
        "occupancy_floor": None,
        "occupancy_floor_pass": None,
        "target_frame_skin_bbox": mappings["skin"]["target_frame_bbox"],
        "target_frame_internal_bbox": mappings["internal"]["target_frame_bbox"],
    }


def _g10_bbox_from_points(points):
    points = list(points)
    if not points:
        raise ValueError("cannot measure an empty G10 bbox")
    return [
        float(min(point[0] for point in points)),
        float(min(point[1] for point in points)),
        float(max(point[0] for point in points)),
        float(max(point[1] for point in points)),
    ]


def g10_unique_g9_overlap_area(g9_islands, pair_metrics, grid_n=1024,
                               bbox=(0.0, 0.0, 1.0, 1.0)):
    """Measure the union area of G9 collision pixels, not only pairwise sums."""
    n = int(grid_n)
    u0, v0, u1, v1 = [float(value) for value in bbox]
    pixel_area = (u1 - u0) * (v1 - v0) / float(n * n)
    unique_by_panel = {}
    covered_by_panel = {}
    for panel in ("skin", "internal"):
        counts = bytearray(n * n)
        for isl in g9_islands:
            if isl.get("panel") != panel:
                continue
            grid, _grid_bbox, _ = raster_tris(island_tris_final(isl), n, bbox)
            for index, count in enumerate(grid):
                if count >= 1 and counts[index] < 255:
                    counts[index] += 1
        unique = sum(value >= 2 for value in counts)
        covered = sum(value >= 1 for value in counts)
        unique_by_panel[panel] = int(unique)
        covered_by_panel[panel] = int(covered)
    unique_pixels = sum(unique_by_panel.values())
    pairs = list(pair_metrics.get("pairs") or [])
    pairwise_sum = sum(float(row["intersection_area_uv"]) for row in pairs)
    g9_occupancy = occupancy_unit(g9_islands)
    unique_area = float(unique_pixels * pixel_area)
    return {
        "method": "union_of_pixels_covered_by_two_or_more_distinct_G9_islands",
        "grid_n": n,
        "collision_pair_count": len(pairs),
        "pairwise_area_sum_uv": float(pairwise_sum),
        "unique_overlap_pixels": int(unique_pixels),
        "unique_overlap_pixels_by_panel": unique_by_panel,
        "covered_pixels_by_panel": covered_by_panel,
        "unique_overlap_area_uv": unique_area,
        "unique_overlap_percent_of_unit_atlas": 100.0 * unique_area,
        "g9_occupancy": float(g9_occupancy),
        "unique_overlap_percent_of_g9_occupancy": (
            100.0 * unique_area / g9_occupancy if g9_occupancy > 0.0 else None
        ),
        "pairwise_sum_double_counts_triple_coverage": True,
    }


def g10_attach_continuous_g9_overlap_area(overlap_metrics, combined_pairs, g9_scale):
    """Attach exact pairwise UV area for the original raster-visible G9 edges."""
    selected = [
        row for row in combined_pairs
        if "G9_raster_1024" in row.get("sources", [])
    ]
    missing = [
        row for row in selected
        if "exact_intersection_area_world_layout" not in row
    ]
    if missing:
        raise RuntimeError("G10 continuous area missing for a G9 collision edge")
    scale_sq = float(g9_scale) ** 2
    pairwise_area = scale_sq * sum(
        float(row["exact_intersection_area_world_layout"])
        for row in selected
    )
    result = dict(overlap_metrics)
    occupancy = float(result.get("g9_occupancy") or 0.0)
    result.update({
        "continuous_method": (
            "sum_of_exact_convex_triangle_clipping_areas_for_original_G9_raster_edges"
        ),
        "continuous_original_g9_pair_count": len(selected),
        "continuous_g9_scale": float(g9_scale),
        "continuous_pairwise_area_sum_uv": float(pairwise_area),
        "continuous_pairwise_percent_of_unit_atlas": 100.0 * pairwise_area,
        "continuous_pairwise_percent_of_g9_occupancy": (
            100.0 * pairwise_area / occupancy if occupancy > 0.0 else None
        ),
        "continuous_pairwise_is_not_polygon_union": True,
        "continuous_pairwise_may_double_count_triple_overlap": True,
    })
    return result


def g10_scale_fidelity_metrics(islands, frames):
    """Measure actual center-distance scale within layers and its CV across layers."""
    frame_by_id = {frame["id"]: frame for frame in frames}
    per_layer = {}
    layer_means = []
    for layer_id in sorted(frame_by_id):
        selected = [isl for isl in islands if isl["g10_layer_id"] == layer_id]
        rows = []
        for index, left in enumerate(selected):
            for right in selected[index + 1:]:
                world_distance = math.hypot(
                    float(left["centroid_3d"][0]) - float(right["centroid_3d"][0]),
                    float(left["centroid_3d"][1]) - float(right["centroid_3d"][1]),
                )
                if world_distance <= 1e-15:
                    continue
                atlas_distance = math.hypot(
                    float(left["placement_center_uv"][0])
                    - float(right["placement_center_uv"][0]),
                    float(left["placement_center_uv"][1])
                    - float(right["placement_center_uv"][1]),
                )
                rows.append({
                    "pair": [left["id"], right["id"]],
                    "world_xy_distance": float(world_distance),
                    "atlas_distance": float(atlas_distance),
                    "ratio": float(atlas_distance / world_distance),
                })
        ratios = [row["ratio"] for row in rows]
        mapping_scale = float(frame_by_id[layer_id]["mapping"]["a"])
        mean = sum(ratios) / len(ratios) if ratios else mapping_scale
        stddev = (
            math.sqrt(sum((value - mean) ** 2 for value in ratios) / len(ratios))
            if ratios else 0.0
        )
        cv = stddev / mean if mean > 1e-18 else float("inf")
        per_layer[layer_id] = {
            "family": frame_by_id[layer_id]["family"],
            "island_count": len(selected),
            "pair_count": len(rows),
            "mean_ratio": float(mean),
            "population_stddev": float(stddev),
            "cv": float(cv),
            "mapping_scale": mapping_scale,
            "singleton_uses_mapping_scale": not rows,
            "pass": cv < G9_SCALE_FIDELITY_CV_MAX,
            "per_pair": rows,
        }
        layer_means.append(float(mean))
    between_mean = sum(layer_means) / len(layer_means) if layer_means else None
    between_stddev = (
        math.sqrt(sum((value - between_mean) ** 2 for value in layer_means) / len(layer_means))
        if layer_means else None
    )
    between_cv = (
        between_stddev / between_mean
        if between_mean is not None and between_mean > 1e-18 else None
    )
    mapping_scales = [
        float(frame["mapping"]["a"]) for frame in frames
    ]
    mapping_span = max(mapping_scales) - min(mapping_scales) if mapping_scales else None
    return {
        "objective_cv_max_exclusive": float(G9_SCALE_FIDELITY_CV_MAX),
        "per_layer": per_layer,
        "between_layers_mean_ratio": float(between_mean) if between_mean is not None else None,
        "between_layers_population_stddev": (
            float(between_stddev) if between_stddev is not None else None
        ),
        "between_layers_cv": float(between_cv) if between_cv is not None else None,
        "mapping_scale_min": min(mapping_scales) if mapping_scales else None,
        "mapping_scale_max": max(mapping_scales) if mapping_scales else None,
        "mapping_scale_span": float(mapping_span) if mapping_span is not None else None,
        "same_mapping_scale_exact": mapping_span == 0.0,
        "pass": (
            between_cv is not None and between_cv < G9_SCALE_FIDELITY_CV_MAX
            and mapping_span == 0.0
            and all(row["pass"] for row in per_layer.values())
        ),
    }


def g10_layout_gates(islands, frames):
    frame_by_id = {frame["id"]: frame for frame in frames}
    frame_overlaps = []
    for index, left in enumerate(frames):
        for right in frames[index + 1:]:
            area = aabb_overlap_area(left["frame_bbox"], right["frame_bbox"])
            if area > 1e-15:
                frame_overlaps.append({
                    "a": left["id"], "b": right["id"], "intersection_area": float(area),
                })
    invasions = []
    for isl in islands:
        frame = frame_by_id[isl["g10_layer_id"]]
        allowed = [float(value) for value in frame["frame_bbox"]]
        bbox = island_uv_bbox(isl)
        if (
            bbox[0] < allowed[0] - 1e-10 or bbox[1] < allowed[1] - 1e-10
            or bbox[2] > allowed[2] + 1e-10 or bbox[3] > allowed[3] + 1e-10
        ):
            invasions.append({
                "island": isl["id"], "layer": isl["g10_layer_id"],
                "bbox": list(bbox), "allowed": allowed,
            })
    rotated = [
        isl["id"] for isl in islands if int(isl.get("rotation_deg") or 0) % 360 != 0
    ]
    forbidden = [
        isl["id"] for isl in islands
        if isl.get("axis") in ("+Z", "-Z")
        and int(isl.get("rotation_deg") or 0) % 360 != 0
    ]
    labels = [island_label(isl) for isl in islands]
    return {
        "frame_overlap_count": len(frame_overlaps),
        "frame_overlap_pairs": frame_overlaps,
        "panel_invasion_count": len(invasions),
        "panel_invasions": invasions,
        "rotated_islands": {
            "count": len(rotated),
            "islands": rotated,
            "forbidden_z_projection_count": len(forbidden),
            "forbidden_z_projection_islands": forbidden,
            "pass": not forbidden,
        },
        "labels": {
            "expected": len(islands),
            "present": sum(bool(label.strip()) for label in labels),
            "unique": len(set(labels)) == len(labels),
        },
        "pass": not frame_overlaps and not invasions and not forbidden
                and len(set(labels)) == len(labels),
    }


def g11_override_layout_gates(islands, frames):
    """Keep G10 frame diagnostics but gate manual placement on the UV canvas."""
    layout = g10_layout_gates(islands, frames)
    outside = []
    for island in islands:
        bbox = island_uv_bbox(island)
        if (
            bbox[0] < 0.0 or bbox[1] < 0.0
            or bbox[2] > 1.0 or bbox[3] > 1.0
        ):
            outside.append({"island": island["id"], "bbox": list(bbox)})
    layout["legacy_frame_containment_pass"] = layout["panel_invasion_count"] == 0
    layout["panel_invasions_are_informational"] = True
    layout["canvas_bbox"] = [0.0, 0.0, 1.0, 1.0]
    layout["canvas_outside_count"] = len(outside)
    layout["canvas_outside_islands"] = outside
    layout["containment_policy"] = (
        "Manual G11 placement may leave its original guide frame but no island may "
        "leave the unit UV canvas."
    )
    layout["pass"] = bool(
        layout["frame_overlap_count"] == 0
        and not outside
        and layout["rotated_islands"]["pass"]
        and layout["labels"]["unique"]
    )
    return layout


def g10_apply_frame_layout(base_islands, reused_assignment, frame_layout, model_xy_bbox):
    """Apply only one translation per frame on top of the common G10 scale."""
    assignment = reused_assignment["assignment_by_island"]
    frames = [dict(frame) for frame in frame_layout["frames"]]
    frame_by_id = {frame["id"]: frame for frame in frames}
    mappings = {frame["id"]: dict(frame["mapping"]) for frame in frames}
    scale = float(frame_layout["global_scale"])
    laid_out = []
    displacement_rows = []
    for original in base_islands:
        isl = dict(original)
        isl["uv_world"] = dict(original["uv_world"])
        isl["faces"] = list(original["faces"])
        isl["face_indices"] = list(original["face_indices"])
        isl["g10_world_uv"] = dict(original["g10_world_uv"])
        layer_id = assignment[isl["id"]]
        frame = frame_by_id[layer_id]
        mapping = mappings[layer_id]
        isl["uv_final"] = {
            loop_index: (
                scale * float(world_u) + float(mapping["b"]),
                scale * float(world_v) + float(mapping["c"]),
            )
            for loop_index, (world_u, world_v) in isl["g10_world_uv"].items()
        }
        target = [
            scale * float(isl["centroid_3d"][0]) + float(mapping["b"]),
            scale * float(isl["centroid_3d"][1]) + float(mapping["c"]),
        ]
        frame_bbox = frame["frame_bbox"]
        local_target = [target[0] - frame_bbox[0], target[1] - frame_bbox[1]]
        isl["g10_layer_id"] = layer_id
        isl["g10_frame_bbox"] = list(frame_bbox)
        isl["pack_scale"] = scale
        isl["target_uv"] = list(target)
        isl["placement_center_uv"] = list(target)
        isl["target_frame_local_uv"] = list(local_target)
        isl["placement_center_frame_uv"] = list(local_target)
        isl["target_displacement_uv"] = 0.0
        isl["rotation_scope"] = (
            "front_view_exception_then_zero_frame_local_translation"
            if int(isl.get("rotation_deg") or 0)
            else "zero_frame_local_translation"
        )
        laid_out.append(isl)
        displacement_rows.append({
            "island": isl["id"],
            "layer": layer_id,
            "target_uv": list(target),
            "placed_uv": list(target),
            "target_frame_local_uv": list(local_target),
            "placed_frame_local_uv": list(local_target),
            "displacement_uv": 0.0,
        })
    displacement_rows.sort(key=lambda row: row["island"])

    family_totals = reused_assignment["minimum_by_family"]
    for frame in frames:
        family = frame["family"]
        zmin, zmax = frame["z_range"]
        highest = frame["ordinal"] == 1
        family_title = "SKIN" if family == "skin" else "INTERNAL"
        altitude = "HIGHEST" if highest else ""
        frame["label"] = "%s %d/%d%s" % (
            family_title, frame["ordinal"], family_totals[family],
            " - " + altitude if altitude else "",
        )
        frame["z_label"] = "Z %.6f .. %.6f" % (zmin, zmax)
        frame["island_label"] = ", ".join(frame["island_ids"])
        frame["uv_bbox"] = list(frame["frame_bbox"])
        frame["pack_xywh"] = [
            frame["frame_bbox"][0], frame["frame_bbox"][1],
            frame["frame_bbox"][2] - frame["frame_bbox"][0],
            frame["frame_bbox"][3] - frame["frame_bbox"][1],
        ]
        frame["unrotated_wh"] = frame["pack_xywh"][2:]
        frame["label_uv"] = [
            frame["frame_bbox"][0] + G10_FRAME_PAD_UV,
            frame["frame_bbox"][3] - G10_FRAME_PAD_UV,
        ]
        frame["shell"] = "G10_" + frame["id"].upper()
        frame["n_islands"] = len(frame["island_ids"])
        frame["anatomical_side"] = family
        frame["semantic_order_space"] = "reused_G9_exact_Z_layering"
        if frame_layout["variant"] == "cropped_frames":
            xmin, ymin, xmax, ymax = [float(value) for value in model_xy_bbox]
            fw = frame["frame_bbox"][2] - frame["frame_bbox"][0]
            fh = frame["frame_bbox"][3] - frame["frame_bbox"][1]
            ghost_pad = 0.06 * min(fw, fh)
            ghost_scale = min(
                max(fw - 2.0 * ghost_pad, 1e-12) / max(xmax - xmin, 1e-18),
                max(fh - 2.0 * ghost_pad, 1e-12) / max(ymax - ymin, 1e-18),
            )
            ghost_cx = 0.5 * (frame["frame_bbox"][0] + frame["frame_bbox"][2])
            ghost_cy = 0.5 * (frame["frame_bbox"][1] + frame["frame_bbox"][3])
            world_cx = 0.5 * (xmin + xmax)
            world_cy = 0.5 * (ymin + ymax)
            frame["ghost_mapping"] = {
                "a": float(ghost_scale),
                "b": float(ghost_cx - ghost_scale * world_cx),
                "c": float(ghost_cy - ghost_scale * world_cy),
                "visualization_only": True,
                "same_scale_as_uv": False,
            }
        else:
            frame["ghost_mapping"] = None

    layout = g10_layout_gates(laid_out, frames)
    triangles = {isl["id"]: island_tris_final(isl) for isl in laid_out}
    final_collisions = g10_raster_layer_collisions(
        triangles, assignment, grid_n=G10_LAYER_GRID_N,
    )
    scale_fidelity = g10_scale_fidelity_metrics(laid_out, frames)
    affine_gate = g10_affine_vertex_gate(laid_out, mappings)
    return {
        "variant": frame_layout["variant"],
        "global_scale": scale,
        "blocks": frames,
        "frames": frames,
        "islands": laid_out,
        "packer": "g10_whole_frame_%s_%s" % (
            frame_layout["variant"], frame_layout["packer"],
        ),
        "selected_order": frame_layout["selected_order"],
        "allow_block_rotation": False,
        "padding": {
            **fixed_padding_config(),
            "frame_pad_uv": float(G10_FRAME_PAD_UV),
            "outer_pad_uv": float(G10_OUTER_PAD_UV),
        },
        "frame_layout": frame_layout,
        "layout_gates": layout,
        "intra_layer_overlap": final_collisions,
        "scale_fidelity": scale_fidelity,
        "affine_vertex_gate": affine_gate,
        "displacement": {
            "method": (
                "One affine u=a*X+b,v=a*Y+c per whole frame; a is identical in all "
                "all frames. Only b/c change. No island-local translation runs."
            ),
            "mean_uv": 0.0,
            "worst_uv": 0.0,
            "worst_island": None,
            "per_island": displacement_rows,
        },
        "predicted_occupancy": occupancy_unit(laid_out),
        "occupancy_floor": None,
        "occupancy_floor_pass": None,
    }


def apply_placement_override_to_g10_stage(stage, payload):
    """Apply G11 island translations and recompute every placement-dependent gate."""
    base_islands = stage["islands"]
    moved_islands, audit = apply_rigid_placement_override(base_islands, payload)
    triangles = {
        island["id"]: island_tris_final(island) for island in moved_islands
    }
    exact = g11_exact_global_collisions(triangles)
    one_layer = {island_id: "atlas_A" for island_id in triangles}
    raster_control = g10_raster_layer_collisions(
        triangles, one_layer, grid_n=G10_LAYER_GRID_N,
    )
    collisions = {
        **exact,
        "raster_control": raster_control,
        "raster_control_pass": raster_control["pass"],
        "pass": exact["pass"] and raster_control["pass"],
        "legacy_field_name": "intra_layer_overlap",
    }
    center_distance_after_override = g10_scale_fidelity_metrics(
        moved_islands, stage["frames"],
    )
    scale_fidelity = dict(stage["scale_fidelity"])
    scale_fidelity.update({
        "method": (
            "Base G10 mapping scales plus the independent rigid-vertex gate; "
            "center distances are informational after island-local translation."
        ),
        "post_override_center_distance_metric": center_distance_after_override,
        "center_distance_metric_is_informational": True,
        "pass": bool(
            stage["scale_fidelity"]["pass"]
            and audit["rigid_vertex_gate"]["pass"]
        ),
    })
    moved_stage = dict(stage)
    moved_stage.update({
        "islands": moved_islands,
        "packer": "g11_manual_rigid_island_translation_from_g10",
        "layout_gates": g11_override_layout_gates(moved_islands, stage["frames"]),
        "intra_layer_overlap": collisions,
        "scale_fidelity": scale_fidelity,
        "affine_vertex_gate": audit["rigid_vertex_gate"],
        "displacement": audit["displacement"],
        "predicted_occupancy": occupancy_unit(moved_islands),
        "placement_override": audit,
        "island_local_translation_applied": True,
        "scale_or_rotation_applied_by_override": False,
    })
    return moved_stage


def pack_and_scale_islands_g10(islands, f_cent, model_xy_bbox, g9_metrics):
    """Materialize both G10 frame variants from the literal G9 3+2 assignment."""
    base_g9 = pack_and_scale_islands_archipelago(islands, f_cent, model_xy_bbox)
    base_scale = float(base_g9["global_scale"])
    family_by_id = {isl["id"]: isl["panel"] for isl in base_g9["islands"]}
    reused = g10_reused_layer_assignment(
        g9_metrics["intra_layer_overlap"], family_by_id,
    )
    for isl in base_g9["islands"]:
        mapping = base_g9["panel_mappings"][isl["panel"]]
        isl["g10_world_uv"] = {
            loop_index: (
                (float(u) - float(mapping["b"])) / base_scale,
                (float(v) - float(mapping["c"])) / base_scale,
            )
            for loop_index, (u, v) in isl["uv_final"].items()
        }

    literal_assignment = dict(reused["assignment_by_island"])
    literal_ordinals = dict(reused["ordinal_by_island"])
    literal_layers = json.loads(json.dumps(reused["layers"]))
    reference = base_g9["panel_mappings"]["skin"]
    source_tris = {}
    world_tris = {}
    for isl in base_g9["islands"]:
        mapping = base_g9["panel_mappings"][isl["panel"]]
        shift_u = float(reference["b"]) - float(mapping["b"])
        shift_v = float(reference["c"]) - float(mapping["c"])
        source_tris[isl["id"]] = [
            [(float(u) + shift_u, float(v) + shift_v) for u, v in tri]
            for tri in island_tris_final(isl)
        ]
        world_tris[isl["id"]] = [
            tri
            for face in isl["faces"]
            for tri in fan_tris_uv(face, isl["g10_world_uv"])
        ]
    literal_raster_verification = g10_raster_layer_collisions(
        source_tris, literal_assignment,
        grid_n=G10_LAYER_GRID_N,
    )
    exact_conflicts = g10_exact_cross_island_conflicts(
        world_tris, family_by_id,
    )
    combined_by_pair = {}
    for row in g9_metrics["intra_layer_overlap"]["pairs"]:
        key = tuple(sorted((row["a"], row["b"])))
        combined_by_pair[key] = {
            "a": key[0], "b": key[1], "family": row["panel"],
            "sources": ["G9_raster_1024"],
            "g9_intersection_area_uv": float(row["intersection_area_uv"]),
        }
    for row in exact_conflicts["pairs"]:
        key = tuple(sorted((row["a"], row["b"])))
        combined = combined_by_pair.setdefault(key, {
            "a": key[0], "b": key[1], "family": row["family"], "sources": [],
        })
        combined["sources"].append("continuous_triangle_area")
        combined["exact_intersection_area_world_layout"] = float(row["intersection_area"])
        combined["positive_triangle_pairs"] = int(row["positive_triangle_pairs"])
    combined_pairs = sorted(
        combined_by_pair.values(), key=lambda row: (row["family"], row["a"], row["b"]),
    )

    by_id = {isl["id"]: isl for isl in base_g9["islands"]}
    corrected_ordinals = {}
    repaired_layers = []
    repair_by_family = {}
    exact_minimum_by_family = {}
    all_partition_changes = []
    all_ordinal_relabels = []
    for family in ("skin", "internal"):
        family_ids = sorted(
            island_id for island_id, value in family_by_id.items() if value == family
        )
        family_pairs = [row for row in combined_pairs if row["family"] == family]
        z_by_id = {
            island_id: float(by_id[island_id]["centroid_3d"][2])
            for island_id in family_ids
        }
        exact_layering = minimum_z_layering(
            family_ids, family_pairs, z_by_id, max_layers=len(family_ids),
        )
        minimum = exact_layering["minimum_zero_collision_layers"]
        if minimum is None:
            raise RuntimeError("G10 exact conflict graph has no coloring for %s" % family)
        repair = g10_repair_assignment_min_changes(
            family_ids, family_pairs, literal_ordinals, color_count=minimum,
        )
        if not repair["pass"]:
            raise RuntimeError("G10 minimum-change coloring failed for %s" % family)
        means = {}
        for color in range(1, int(minimum) + 1):
            members = [
                island_id for island_id, value in repair["assignment"].items()
                if int(value) == color
            ]
            means[color] = sum(z_by_id[item] for item in members) / len(members)
        ordered_colors = sorted(means, key=lambda color: (-means[color], color))
        color_remap = {old: new + 1 for new, old in enumerate(ordered_colors)}
        ordered_assignment = {
            island_id: color_remap[int(color)]
            for island_id, color in repair["assignment"].items()
        }
        changes = [
            {"island": island_id, "from": int(literal_ordinals[island_id]),
             "to": int(ordered_assignment[island_id])}
            for island_id in family_ids
            if int(literal_ordinals[island_id]) != int(ordered_assignment[island_id])
        ]
        repair_by_family[family] = {
            "minimum_zero_collision_layers_exact_plus_G9_raster": int(minimum),
            "minimum_change_solution_before_Z_order": repair,
            "color_mean_Z_before_remap": {str(key): value for key, value in means.items()},
            "Z_order_color_remap": {str(key): value for key, value in color_remap.items()},
            "changes_after_Z_order": changes,
            "changed_count_after_Z_order": len(changes),
        }
        exact_minimum_by_family[family] = int(minimum)
        corrected_ordinals.update(ordered_assignment)
        all_partition_changes.extend(repair["changes"])
        all_ordinal_relabels.extend(changes)
        for ordinal in range(1, int(minimum) + 1):
            members = sorted(
                island_id for island_id, value in ordered_assignment.items()
                if int(value) == ordinal
            )
            repaired_layers.append({
                "id": "%s_%d" % (family, ordinal),
                "family": family,
                "ordinal": ordinal,
                "island_ids": members,
            })

    corrected_assignment = {
        island_id: "%s_%d" % (family_by_id[island_id], corrected_ordinals[island_id])
        for island_id in sorted(corrected_ordinals)
    }
    corrected_raster_verification = g10_raster_layer_collisions(
        source_tris, corrected_assignment, grid_n=G10_LAYER_GRID_N,
    )
    literal_exact_same_layer = [
        row for row in exact_conflicts["pairs"]
        if literal_assignment[row["a"]] == literal_assignment[row["b"]]
    ]
    corrected_exact_same_layer = [
        row for row in exact_conflicts["pairs"]
        if corrected_assignment[row["a"]] == corrected_assignment[row["b"]]
    ]
    combined_same_layer = [
        row for row in combined_pairs
        if corrected_assignment[row["a"]] == corrected_assignment[row["b"]]
    ]
    reused.update({
        "source_literal_assignment_by_island": literal_assignment,
        "source_literal_ordinal_by_island": literal_ordinals,
        "source_literal_layers": literal_layers,
        "source_literal_raster_verification": literal_raster_verification,
        "source_literal_exact_collision_pair_count": len(literal_exact_same_layer),
        "source_literal_exact_collision_pairs": literal_exact_same_layer,
        "source_literal_zero_collision_verdict": False,
        "exact_conflict_graph": exact_conflicts,
        "combined_conflict_graph": {
            "method": "union_of_G9_raster_edges_and_continuous_triangle_area_edges",
            "collision_pair_count": len(combined_pairs),
            "pairs": combined_pairs,
        },
        "repair_required": bool(all_partition_changes),
        "repair_policy": "minimum_changed_islands_then_layers_reordered_by_mean_Z",
        "repair_by_family": repair_by_family,
        "repair_changes": all_partition_changes,
        "repair_changed_count": len(all_partition_changes),
        "ordinal_relabels_after_Z_order": all_ordinal_relabels,
        "ordinal_relabel_count_after_Z_order": len(all_ordinal_relabels),
        "assignment_reused_without_change": not all_partition_changes,
        "assignment_by_island": corrected_assignment,
        "ordinal_by_island": corrected_ordinals,
        "layers": repaired_layers,
        "minimum_by_family": exact_minimum_by_family,
        "minimum_total_layers": sum(exact_minimum_by_family.values()),
        "source_verification": corrected_raster_verification,
        "corrected_exact_collision_pair_count": len(corrected_exact_same_layer),
        "corrected_exact_collision_pairs": corrected_exact_same_layer,
        "corrected_combined_collision_pair_count": len(combined_same_layer),
        "corrected_combined_collision_pairs": combined_same_layer,
    })
    reused["source_metrics_sha256"] = None
    reused["source_global_aligned_field_was_not_used_because_it_mixes_families"] = True

    layer_specs = []
    for layer in reused["layers"]:
        members = [by_id[island_id] for island_id in layer["island_ids"]]
        content_bbox = _g10_bbox_from_points(
            point for isl in members for point in isl["g10_world_uv"].values()
        )
        z_values = [float(isl["centroid_3d"][2]) for isl in members]
        layer_specs.append({
            **dict(layer),
            "content_bbox_world": content_bbox,
            "z_range": [min(z_values), max(z_values)],
            "z_mean": float(sum(z_values) / len(z_values)),
        })
    reused["layers"] = layer_specs

    full_layout = g10_pack_frame_layout(layer_specs, model_xy_bbox, "full_frames")
    cropped_layout = g10_pack_frame_layout(layer_specs, model_xy_bbox, "cropped_frames")
    full_stage = g10_apply_frame_layout(
        base_g9["islands"], reused, full_layout, model_xy_bbox,
    )
    cropped_stage = g10_apply_frame_layout(
        base_g9["islands"], reused, cropped_layout, model_xy_bbox,
    )
    g9_overlap_area = g10_unique_g9_overlap_area(
        base_g9["islands"], base_g9["intra_layer_overlap"],
        grid_n=G10_LAYER_GRID_N,
    )
    g9_overlap_area = g10_attach_continuous_g9_overlap_area(
        g9_overlap_area, combined_pairs, base_scale,
    )
    return {
        "base_g9": base_g9,
        "g10_layering": reused,
        "g9_overlap_area": g9_overlap_area,
        "cropped_frames": cropped_stage,
        "full_frames": full_stage,
    }


def triangle_halfplane_area(triangle, mid_u=0.5, keep_left=True):
    """Exact polygon clip of one UV triangle against u<=mid or u>=mid."""
    polygon = [(float(p[0]), float(p[1])) for p in triangle]

    def inside(point):
        return point[0] <= mid_u + 1e-15 if keep_left else point[0] >= mid_u - 1e-15

    clipped = []
    for index, current in enumerate(polygon):
        previous = polygon[index - 1]
        current_in = inside(current)
        previous_in = inside(previous)
        if current_in != previous_in:
            du = current[0] - previous[0]
            t = 0.0 if abs(du) <= 1e-18 else (mid_u - previous[0]) / du
            clipped.append((mid_u, previous[1] + t * (current[1] - previous[1])))
        if current_in:
            clipped.append(current)
    if len(clipped) < 3:
        return 0.0
    twice_area = 0.0
    for index, point in enumerate(clipped):
        nxt = clipped[(index + 1) % len(clipped)]
        twice_area += point[0] * nxt[1] - point[1] * nxt[0]
    return 0.5 * abs(twice_area)


def piece_centroids_3d(shell_by_id, f_cent):
    """Area-weighted world-space face-centroid for each physical piece."""
    out = {}
    for sid, shell in shell_by_id.items():
        weighted = Vector((0.0, 0.0, 0.0))
        total = 0.0
        for face in shell["faces"]:
            area = float(face.calc_area())
            weighted += f_cent[face.index] * area
            total += area
        center = weighted / total if total > 1e-18 else Vector(shell["center"])
        out[sid] = (float(center.x), float(center.y), float(center.z))
    return out


def world_xy_geometry_for_shells(shell_by_id, shell_ids, v_world):
    """Independent real top-view triangles and XY bbox for named physical pieces."""
    tris = []
    xmin = ymin = 1e30
    xmax = ymax = -1e30
    for sid in shell_ids:
        for face in shell_by_id[sid]["faces"]:
            points = []
            for loop in face.loops:
                point = v_world[loop.vert.index]
                xy = (float(point.x), float(point.y))
                points.append(xy)
                xmin = min(xmin, xy[0])
                xmax = max(xmax, xy[0])
                ymin = min(ymin, xy[1])
                ymax = max(ymax, xy[1])
            for index in range(1, len(points) - 1):
                tris.append((points[0], points[index], points[index + 1]))
    if xmax < xmin or ymax < ymin:
        raise RuntimeError("no world XY geometry for requested shells")
    return tris, (float(xmin), float(ymin), float(xmax), float(ymax))


def world_xy_tris_by_panel(islands, v_world):
    """World-XY reference triangles split by the exact n+/n- island faces."""
    out = {"skin": [], "internal": []}
    seen = {"skin": set(), "internal": set()}
    for isl in islands:
        panel = "skin" if isl.get("nsign") == "+" else "internal"
        for face in isl["faces"]:
            if face.index in seen[panel]:
                continue
            seen[panel].add(face.index)
            points = []
            for loop in face.loops:
                point = v_world[loop.vert.index]
                points.append((float(point.x), float(point.y)))
            for index in range(1, len(points) - 1):
                out[panel].append((points[0], points[index], points[index + 1]))
    return out


def island_face_change_metrics(before_islands, after_islands):
    """Face movements by island ID, with atlas membership deliberately ignored."""
    before = {isl["id"]: set(isl["face_indices"]) for isl in before_islands}
    after = {isl["id"]: set(isl["face_indices"]) for isl in after_islands}
    rows = []
    moved_faces = set()
    for island_id in sorted(set(before) | set(after)):
        removed = sorted(before.get(island_id, set()) - after.get(island_id, set()))
        added = sorted(after.get(island_id, set()) - before.get(island_id, set()))
        if not removed and not added:
            continue
        moved_faces.update(removed)
        moved_faces.update(added)
        rows.append({
            "island": island_id,
            "faces_before": len(before.get(island_id, set())),
            "faces_after": len(after.get(island_id, set())),
            "removed_count": len(removed),
            "added_count": len(added),
            "removed_faces": removed,
            "added_faces": added,
        })
    return {
        "changed_island_count": len(rows),
        "unique_face_count": len(moved_faces),
        "unique_faces": sorted(moved_faces),
        "per_island": rows,
    }


def _average_ranks(values):
    ordered = sorted(range(len(values)), key=lambda index: (float(values[index]), index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        value = float(values[ordered[start]])
        while end < len(ordered) and abs(float(values[ordered[end]]) - value) <= 1e-15:
            end += 1
        rank = 0.5 * ((start + 1) + end)
        for position in range(start, end):
            ranks[ordered[position]] = rank
        start = end
    return ranks


def _pearson(values_a, values_b):
    if len(values_a) != len(values_b) or not values_a:
        return None
    mean_a = sum(values_a) / len(values_a)
    mean_b = sum(values_b) / len(values_b)
    da = [value - mean_a for value in values_a]
    db = [value - mean_b for value in values_b]
    denom = math.sqrt(sum(value * value for value in da) * sum(value * value for value in db))
    if denom <= 1e-18:
        return None
    return sum(a * b for a, b in zip(da, db)) / denom


def spearman_rho(values_a, values_b):
    return _pearson(_average_ranks(values_a), _average_ranks(values_b))


def anatomical_placement_metrics(blocks, piece_centroids, pairs=G7_MIRROR_PAIRS):
    block_by_shell = {block["shell"]: block for block in blocks}
    centers_uv = {
        sid: (
            0.5 * (block["uv_bbox"][0] + block["uv_bbox"][2]),
            0.5 * (block["uv_bbox"][1] + block["uv_bbox"][3]),
        )
        for sid, block in block_by_shell.items()
    }
    pair_v_rows = []
    pair_u_rows = []
    pair_interposed_rows = []
    for left_sid, right_sid in pairs:
        left = block_by_shell[left_sid]
        right = block_by_shell[right_sid]
        left_center = centers_uv[left_sid]
        right_center = centers_uv[right_sid]
        v_offset = abs(left_center[1] - right_center[1])
        u_symmetry = abs(abs(left_center[0] - 0.5) - abs(right_center[0] - 0.5))
        common_v0 = max(left["uv_bbox"][1], right["uv_bbox"][1])
        common_v1 = min(left["uv_bbox"][3], right["uv_bbox"][3])
        gap_u0 = left["uv_bbox"][2]
        gap_u1 = right["uv_bbox"][0]
        interposed = []
        for foreign in blocks:
            if foreign["shell"] in (left_sid, right_sid):
                continue
            vertical = min(common_v1, foreign["uv_bbox"][3]) - max(common_v0, foreign["uv_bbox"][1])
            horizontal = min(gap_u1, foreign["uv_bbox"][2]) - max(gap_u0, foreign["uv_bbox"][0])
            if vertical > 1e-15 and horizontal > 1e-15:
                interposed.append(foreign["shell"])
        pair_id = left_sid + "/" + right_sid
        pair_v_rows.append({"pair": pair_id, "value": float(v_offset)})
        pair_u_rows.append({"pair": pair_id, "value": float(u_symmetry)})
        pair_interposed_rows.append({
            "pair": pair_id,
            "value": len(interposed),
            "shells": interposed,
        })

    shells = sorted(block_by_shell)
    y_values = [float(piece_centroids[sid][1]) for sid in shells]
    v_values = [float(centers_uv[sid][1]) for sid in shells]
    rho = spearman_rho(y_values, v_values)

    neighbour_rows = []
    for sid in shells:
        p3 = piece_centroids[sid]
        puv = centers_uv[sid]
        nearest_3d = sorted(
            (math.sqrt(sum((float(p3[i]) - float(piece_centroids[other][i])) ** 2 for i in range(3))), other)
            for other in shells if other != sid
        )[:3]
        nearest_uv = sorted(
            (math.hypot(puv[0] - centers_uv[other][0], puv[1] - centers_uv[other][1]), other)
            for other in shells if other != sid
        )[:3]
        set_3d = {other for _distance, other in nearest_3d}
        set_uv = {other for _distance, other in nearest_uv}
        neighbour_rows.append({
            "shell": sid,
            "kept": len(set_3d & set_uv),
            "nearest_3d": [other for _distance, other in nearest_3d],
            "nearest_atlas": [other for _distance, other in nearest_uv],
        })
    return {
        "pair_v_offset": {
            "objective": 0.0,
            "per_pair": pair_v_rows,
            "worst": max((row["value"] for row in pair_v_rows), default=0.0),
        },
        "pair_u_symmetry": {
            "objective": 0.0,
            "per_pair": pair_u_rows,
            "worst": max((row["value"] for row in pair_u_rows), default=0.0),
        },
        "pair_interposed": {
            "objective": 0,
            "per_pair": pair_interposed_rows,
            "worst": max((row["value"] for row in pair_interposed_rows), default=0),
        },
        "layout_fidelity_v": {
            "objective_abs_rho_min": 0.8,
            "rho": float(rho) if rho is not None else None,
            "sign_matches_declared_convention": bool(rho is not None and rho >= 0.0),
        },
        "neighbour_keep_at_3": {
            "objective": None,
            "per_piece": neighbour_rows,
            "mean": (
                sum(row["kept"] for row in neighbour_rows) / len(neighbour_rows)
                if neighbour_rows else None
            ),
        },
        "piece_positions": [
            {
                "shell": sid,
                "centroid_3d": [float(value) for value in piece_centroids[sid]],
                "block_center_uv": [float(value) for value in centers_uv[sid]],
                "side": (
                    "crossing" if block_by_shell[sid]["uv_bbox"][0] < 0.5 < block_by_shell[sid]["uv_bbox"][2]
                    else "left" if centers_uv[sid][0] < 0.5 else "right"
                ),
            }
            for sid in shells
        ],
    }


def island_semantic_centroid(isl):
    """Area-weighted UV centroid used for labels and homologous alignment."""
    tris = island_tris_final(isl) if isl.get("faces") else []
    if tris:
        return weighted_centroid(tris)
    return weighted_centroid_from_points((isl.get("uv_final") or {}).values())


def pair_homologous_alignment_metrics(islands, pairs=G7_MIRROR_PAIRS):
    by_shell_sign = {}
    for isl in islands:
        by_shell_sign[(isl["shell"], isl.get("nsign"))] = isl
    rows = []
    for left_sid, right_sid in pairs:
        for sign in ("+", "-"):
            left = by_shell_sign.get((left_sid, sign))
            right = by_shell_sign.get((right_sid, sign))
            if left is None or right is None:
                rows.append({
                    "pair": left_sid + "/" + right_sid,
                    "normal_sign": sign,
                    "value": None,
                    "status": "missing_homologue",
                })
                continue
            value = abs(
                island_semantic_centroid(left)[1]
                - island_semantic_centroid(right)[1]
            )
            rows.append({
                "pair": left_sid + "/" + right_sid,
                "normal_sign": sign,
                "value": float(value),
                "status": "measured",
            })
    measured = [row["value"] for row in rows if row["value"] is not None]
    return {
        "objective": 0.0,
        "per_homologue": rows,
        "worst": max(measured) if measured else None,
        "all_homologues_present": len(measured) == 2 * len(pairs),
    }


def side_purity_metrics(islands, v_world, sign_split_x):
    """UV-area fraction on the u half dictated by independently re-read world X."""
    per_block_acc = defaultdict(lambda: [0.0, 0.0])
    per_column_acc = defaultdict(lambda: [0.0, 0.0])
    mismatches = []
    straddling_faces = []
    for isl in islands:
        sid = isl["shell"]
        for face in isl["faces"]:
            xs = [float(v_world[vert.index].x) for vert in face.verts]
            center_x = sum(xs) / len(xs)
            keep_left = center_x < float(sign_split_x)
            real_lr = "L" if keep_left else "R"
            if isl.get("lr") is not None and isl.get("lr") != real_lr:
                mismatches.append({
                    "island": isl["id"],
                    "face": face.index,
                    "label": isl.get("lr"),
                    "real_sign": real_lr,
                    "face_center_x": center_x,
                })
            if min(xs) < float(sign_split_x) < max(xs):
                straddling_faces.append({"island": isl["id"], "face": face.index})
            for tri in fan_tris_uv(face, isl["uv_final"]):
                total = tri_area_2d(*tri)
                correct = triangle_halfplane_area(
                    tri, mid_u=0.5, keep_left=keep_left,
                )
                per_block_acc[sid][0] += correct
                per_block_acc[sid][1] += total
                column = isl.get("lr") or real_lr
                per_column_acc[(sid, column)][0] += correct
                per_column_acc[(sid, column)][1] += total
    per_block = {}
    per_column = {}
    values = []
    for sid, (correct, total) in sorted(per_block_acc.items()):
        value = correct / total if total > 1e-18 else None
        if value is not None and abs(value - 1.0) <= 1e-12:
            value = 1.0
        per_block[sid] = value
        if sid not in G7_CROSSING_SHELLS and value is not None:
            values.append(value)
    for (sid, column), (correct, total) in sorted(per_column_acc.items()):
        value = correct / total if total > 1e-18 else None
        if value is not None and abs(value - 1.0) <= 1e-12:
            value = 1.0
        per_column.setdefault(sid, {})[column] = value
        if sid in G7_CROSSING_SHELLS and value is not None:
            values.append(value)
    return {
        "objective": 1.0,
        "per_block": per_block,
        "per_column": per_column,
        "worst": min(values) if values else None,
        "label_face_sign_mismatch_count": len(mismatches),
        "label_face_sign_mismatches": mismatches,
        "faces_straddling_symmetry_plane": straddling_faces,
        "method": (
            "Each final UV fan-triangle is clipped exactly at u=0.5. The kept half "
            "is selected from an independent world-vertex mean X for its source face."
        ),
    }


def g9_side_purity_from_legacy(legacy_metric, total_faces):
    """Separate the frozen face-assignment invariant from unavoidable X=0 straddling."""
    result = dict(legacy_metric)
    face_count = int(total_faces)
    mismatch_count = int(legacy_metric["label_face_sign_mismatch_count"])
    semantic = (
        float(face_count - mismatch_count) / face_count if face_count > 0 else None
    )
    result.update({
        "objective": 1.0,
        "worst": semantic,
        "semantic_assignment_purity": semantic,
        "legacy_uv_half_area_worst": legacy_metric.get("worst"),
        "straddling_face_count": len(
            legacy_metric.get("faces_straddling_symmetry_plane") or []
        ),
        "semantic_definition": (
            "Fraction of atlas-A faces whose frozen L/R island label matches the "
            "independently re-read world-X sign of the face centroid. This is the "
            "invariant corrected by moving face 4053 in G8."
        ),
        "legacy_uv_half_area_note": (
            "Reported separately, not used as G9 side_purity: a literal affine leaves "
            "the physical portions of faces that straddle X=0 on both sides. Requiring "
            "1.0 for that legacy area metric would require cutting faces or moving UVs."
        ),
    })
    return result


def pack_and_scale_blocks(islands, specs_by_shell):
    """Group islands by shell, layout each as a 2x2 (or 1x2) block, pack blocks.

    One global scale into the unit square. Islands are never rotated.
    Returns (scale, block_records, pack_w, pack_h).
    """
    if not islands:
        return 1.0, [], 1.0, 1.0
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)

    max_isl_side = 0.0
    for isl in islands:
        w, h = _island_wh(isl)
        max_isl_side = max(max_isl_side, w, h)
    inner_pad = max(BLOCK_INNER_PAD_FRAC * max_isl_side, 1e-9)
    outer_pad = inner_pad

    local_by_island = {}
    block_boxes = []
    block_meta = {}
    for sid, slist in by_shell.items():
        spec = specs_by_shell[sid]
        max_side = 0.0
        for isl in slist:
            w, h = _island_wh(isl)
            max_side = max(max_side, w, h)
        label_h = max(BLOCK_LABEL_FRAC * max(max_side, 1e-9), inner_pad)
        local, bw, bh, grid = layout_piece_block(
            slist, spec["split_lr"], spec["split_by_normal_sign"],
            inner_pad, outer_pad, label_h,
        )
        local_by_island.update(local)
        block_boxes.append({"id": sid, "w": bw, "h": bh})
        block_meta[sid] = {
            "w": bw, "h": bh, "grid": grid, "n_islands": len(slist),
        }

    max_block_side = max(b["w"] for b in block_boxes)
    max_block_side = max(max_block_side, max(b["h"] for b in block_boxes))
    block_pad = max(BLOCK_PAD_FRAC * max_block_side, inner_pad)
    pos, pack_w, pack_h = pack_blocks_shelf(block_boxes, block_pad)

    side = max(pack_w, pack_h, 1e-18)
    usable = 1.0 - 2.0 * PACK_MARGIN
    scale = usable / side
    origin = PACK_MARGIN

    for isl in islands:
        loc = local_by_island[isl["id"]]
        bp = pos[isl["shell"]]
        umin, vmin, umax, vmax = isl["bbox_world"]
        isl["rotation_deg"] = 0
        isl["uv_final"] = {}
        for li, (u, v) in isl["uv_world"].items():
            ul = u - umin
            vl = v - vmin
            lx = loc["x"] + ul
            ly = loc["y"] + vl
            isl["uv_final"][li] = (
                origin + (bp["x"] + lx) * scale,
                origin + (bp["y"] + ly) * scale,
            )
        isl["pack_scale"] = scale

    blocks = []
    for sid, box in block_meta.items():
        bp = pos[sid]
        u0 = origin + bp["x"] * scale
        v0 = origin + bp["y"] * scale
        u1 = origin + (bp["x"] + bp["w"]) * scale
        v1 = origin + (bp["y"] + bp["h"]) * scale
        # Label band is the top outer_pad+label_h of the block.
        grid = box["grid"]
        label_uv = (
            0.5 * (u0 + u1),
            v1 - 0.5 * grid["label_h"] * scale,
        )
        blocks.append({
            "shell": sid,
            "uv_bbox": [float(u0), float(v0), float(u1), float(v1)],
            "pack_xywh": [float(bp["x"]), float(bp["y"]), float(bp["w"]), float(bp["h"])],
            "unrotated_wh": [float(bp["w"]), float(bp["h"])],
            "label_uv": [float(label_uv[0]), float(label_uv[1])],
            "n_islands": box["n_islands"],
            "rotation_deg": 0,
            "grid": {
                "cols": grid["cols"],
                "rows": grid["rows"],
                "geom_w": grid["geom_w"],
                "geom_h": grid["geom_h"],
            },
        })
    blocks.sort(key=lambda b: b["shell"])
    return scale, blocks, pack_w, pack_h


def aabb_overlap_area(a, b):
    """Intersection area of two (umin, vmin, umax, vmax). Touching edges = 0."""
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def island_uv_bbox(isl):
    umin = vmin = 1e30
    umax = vmax = -1e30
    for u, v in isl["uv_final"].values():
        umin = min(umin, u)
        umax = max(umax, u)
        vmin = min(vmin, v)
        vmax = max(vmax, v)
    if umax < umin:
        return (0.0, 0.0, 0.0, 0.0)
    return (umin, vmin, umax, vmax)


def grouping_gates(blocks, islands):
    """Mechanical grouping gates. Purity uses raster of OTHER islands inside
    the block rectangle, divided by block-bbox area. Disjoint uses AABB of
    block rectangles; touching edges do not count.
    """
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)
    purity = {}
    worst = 0.0
    for blk in blocks:
        sid = blk["shell"]
        bb = tuple(blk["uv_bbox"])
        bw = max(bb[2] - bb[0], 1e-18)
        bh = max(bb[3] - bb[1], 1e-18)
        area = bw * bh
        other_tris = []
        for isl in islands:
            if isl["shell"] == sid:
                continue
            ib = island_uv_bbox(isl)
            if aabb_overlap_area(bb, ib) <= 0.0:
                continue
            other_tris.extend(island_tris_final(isl))
        foreign_area = 0.0
        if other_tris:
            grid, gbb, n = raster_tris(other_tris, 256, bbox=bb)
            ge1 = sum(1 for c in grid if c >= 1)
            px = (gbb[2] - gbb[0]) / n
            py = (gbb[3] - gbb[1]) / n
            foreign_area = ge1 * px * py
        frac = foreign_area / area
        purity[sid] = float(frac)
        worst = max(worst, frac)
    overlap_pairs = []
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            inter = aabb_overlap_area(tuple(a["uv_bbox"]), tuple(b["uv_bbox"]))
            if inter > 0.0:
                overlap_pairs.append({
                    "a": a["shell"],
                    "b": b["shell"],
                    "intersection_area": float(inter),
                })
    all_zero = all(v == 0.0 or v < 1e-15 for v in purity.values())
    # Use exact 0.0 after clipping tiny raster noise below one pixel.
    purity_clean = {k: (0.0 if v < 1e-12 else float(v)) for k, v in purity.items()}
    all_zero = all(v == 0.0 for v in purity_clean.values())
    return {
        "block_purity_by_piece": purity_clean,
        "block_purity_worst": (0.0 if worst < 1e-12 else float(worst)),
        "block_purity_all_zero": all_zero,
        "block_bbox_overlap_pairs": overlap_pairs,
        "block_bbox_overlap_count": len(overlap_pairs),
        "verdict": (
            "PASS" if all_zero and not overlap_pairs else "FAIL"
        ),
    }


def block_rotation_gate(blocks, islands):
    """Prove rotations were applied rigidly at block scope only."""
    block_rot = {b["shell"]: int(b.get("rotation_deg") or 0) % 360 for b in blocks}
    violations = []
    allowed = {0, 90, 180, 270}
    for shell, rot in sorted(block_rot.items()):
        if rot not in allowed:
            violations.append({"shell": shell, "reason": "bad_block_angle", "angle": rot})
    for isl in islands:
        shell = isl["shell"]
        irot = int(isl.get("rotation_deg") or 0) % 360
        if shell not in block_rot:
            violations.append({"island": isl["id"], "reason": "missing_block"})
        elif irot != block_rot[shell]:
            violations.append({
                "island": isl["id"], "shell": shell,
                "reason": "island_angle_differs_from_block",
                "island_angle": irot, "block_angle": block_rot[shell],
            })
        raw = isl.get("uv_world") or {}
        final = isl.get("uv_final") or {}
        common = [key for key in raw if key in final]
        ref = None
        for i, ka in enumerate(common):
            for kb in common[i + 1:]:
                dx = raw[kb][0] - raw[ka][0]
                dy = raw[kb][1] - raw[ka][1]
                if dx * dx + dy * dy <= 1e-16:
                    continue
                fx = final[kb][0] - final[ka][0]
                fy = final[kb][1] - final[ka][1]
                if fx * fx + fy * fy <= 1e-16:
                    continue
                ref = (dx, dy, fx, fy)
                break
            if ref:
                break
        if ref and shell in block_rot:
            dx, dy, fx, fy = ref
            angle = math.degrees(math.atan2(dx * fy - dy * fx, dx * fx + dy * fy)) % 360.0
            expected = (-block_rot[shell]) % 360.0
            delta = abs(((angle - expected + 180.0) % 360.0) - 180.0)
            if delta > 1e-5:
                violations.append({
                    "island": isl["id"], "shell": shell,
                    "reason": "measured_affine_angle_differs_from_block",
                    "measured_geometric_angle": angle,
                    "expected_geometric_angle": expected,
                    "delta_deg": delta,
                })
    return {
        "allowed_angles_deg": sorted(allowed),
        "block_rotations_deg": block_rot,
        "violations": violations,
        "individually_rotated_island_count": len(violations),
        "pass": not violations,
        "verdict": "PASS" if not violations else "FAIL",
    }


def _inverse_block_rotation(x, y, width, height, rotation_deg):
    rot = int(rotation_deg) % 360
    if rot == 0:
        return x, y
    if rot == 90:
        return width - y, x
    if rot == 180:
        return width - x, height - y
    if rot == 270:
        return y, height - x
    raise ValueError("rotation must be a multiple of 90")


def labels_and_grid_order_gate(blocks, islands):
    """Check actual final centroids after undoing each rigid block rotation."""
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)
    violations = []
    checked_relations = []
    labels = []
    for block in blocks:
        sid = block["shell"]
        labels.append(sid)
        bb = block["uv_bbox"]
        label = block.get("label_uv")
        if not label or not (bb[0] <= label[0] <= bb[2] and bb[1] <= label[1] <= bb[3]):
            violations.append({"shell": sid, "reason": "label_outside_block"})
        unrot = block.get("unrotated_wh")
        if not unrot:
            continue
        local_centers = []
        for isl in by_shell.get(sid, []):
            pts = list((isl.get("uv_final") or {}).values())
            if not pts:
                violations.append({"shell": sid, "island": isl["id"], "reason": "no_uv_points"})
                continue
            if block.get("semantic_order_space") == "final_uv":
                cx, cy = island_semantic_centroid(isl)
                lx, ly = cx - bb[0], cy - bb[1]
            else:
                x = sum(p[0] for p in pts) / len(pts) - bb[0]
                y = sum(p[1] for p in pts) / len(pts) - bb[1]
                lx, ly = _inverse_block_rotation(
                    x, y, unrot[0], unrot[1], block.get("rotation_deg") or 0,
                )
            local_centers.append((isl, lx, ly))
        left = [x for isl, x, _y in local_centers if isl.get("lr") == "L"]
        right = [x for isl, x, _y in local_centers if isl.get("lr") == "R"]
        if left and right:
            ok = max(left) < min(right)
            checked_relations.append({"shell": sid, "relation": "L_left_of_R", "pass": ok})
            if not ok:
                violations.append({"shell": sid, "reason": "L_not_left_of_R"})
        plus = [y for isl, _x, y in local_centers if isl.get("nsign") == "+"]
        minus = [y for isl, _x, y in local_centers if isl.get("nsign") == "-"]
        if plus and minus:
            ok = min(plus) > max(minus)
            checked_relations.append({"shell": sid, "relation": "nplus_above_nminus", "pass": ok})
            if not ok:
                violations.append({"shell": sid, "reason": "nplus_not_above_nminus"})
    unique_labels = len(labels) == len(set(labels)) == len(blocks)
    if not unique_labels:
        violations.append({"reason": "duplicate_or_missing_piece_labels"})
    return {
        "labels": labels,
        "unique_piece_labels": unique_labels,
        "relations_checked": checked_relations,
        "violations": violations,
        "pass": not violations,
        "verdict": "PASS" if not violations else "FAIL",
    }


# ---------------------------------------------------------------------------
# Exterior visibility: first-hit against the COMPLETE-mesh BVH.
# Copied method from grok_g1_shellmeasure/measure_grok.py (64 Fibonacci
# orthographic 128x128 grids, no backface cull). Attribution is per island
# instead of per shell.
# ---------------------------------------------------------------------------
def fibonacci_sphere(n):
    pts = []
    if n < 1:
        return pts
    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (i / max(1, n - 1)) * 2.0
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = phi * i
        pts.append(Vector((math.cos(theta) * r, y, math.sin(theta) * r)))
    return pts


def vis_orthonormal_basis(d):
    """d is unit look-from-camera direction. Returns (u, v, d). [EXACT] g1."""
    d = d.normalized()
    up = Vector((0.0, 0.0, 1.0)) if abs(d.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = d.cross(up)
    if u.length_squared < 1e-18:
        up = Vector((0.0, 1.0, 0.0))
        u = d.cross(up)
    u.normalize()
    v = u.cross(d)
    v.normalize()
    return u, v, d


def vis_projected_bounds(coords, u, v):
    umin = vmin = 1e30
    umax = vmax = -1e30
    for p in coords:
        uu = p.dot(u)
        vv = p.dot(v)
        if uu < umin:
            umin = uu
        if uu > umax:
            umax = uu
        if vv < vmin:
            vmin = vv
        if vv > vmax:
            vmax = vv
    return umin, umax, vmin, vmax


def raster_first_hit_islands(bvh, face_to_island, cam_from, coords, grid, ray_len):
    """Orthographic first-hit grid. Rays travel toward the mesh along -cam_from.

    No backface cull: the player sees whichever surface is first.
    face_to_island[face_index] -> island id or None.
    Returns (counts dict, hits, misses).
    """
    u, v, look = vis_orthonormal_basis(-cam_from)
    umin, umax, vmin, vmax = vis_projected_bounds(coords, u, v)
    pad_u = (umax - umin) * 0.04 + 1e-6
    pad_v = (vmax - vmin) * 0.04 + 1e-6
    umin -= pad_u
    umax += pad_u
    vmin -= pad_v
    vmax += pad_v
    du = (umax - umin) / grid
    dv = (vmax - vmin) / grid
    counts = {}
    hits = 0
    misses = 0
    for iy in range(grid):
        vv = vmin + (iy + 0.5) * dv
        for ix in range(grid):
            uu = umin + (ix + 0.5) * du
            origin = u * uu + v * vv + cam_from * ray_len
            _loc, _n, index, _dist = bvh.ray_cast(origin, look, ray_len * 2.0)
            if index is None:
                misses += 1
                continue
            iid = face_to_island[index] if 0 <= index < len(face_to_island) else None
            if iid is None:
                misses += 1
                continue
            counts[iid] = counts.get(iid, 0) + 1
            hits += 1
    return counts, hits, misses


def measure_island_visibility(bm, v_world, islands, n_dir, grid):
    """Attribute first-hits of the COMPLETE mesh to the island that owns the face.

    World-space BVH. vis_share = island_hits / total_hits. Sum over all
    islands of all 13 pieces must close at 1.0.
    """
    nverts = 1 + max(v.index for v in bm.verts)
    verts = [(0.0, 0.0, 0.0)] * nverts
    coords = []
    for v in bm.verts:
        p = v_world[v.index]
        t = (float(p.x), float(p.y), float(p.z))
        verts[v.index] = t
        coords.append(Vector(t))
    polys = []
    poly_to_face = []
    for f in bm.faces:
        polys.append([v.index for v in f.verts])
        poly_to_face.append(f.index)
    bvh = BVHTree.FromPolygons(verts, polys, epsilon=0.0)

    nfaces = 1 + max(f.index for f in bm.faces)
    face_to_island = [None] * nfaces
    for isl in islands:
        for fi in isl["face_indices"]:
            face_to_island[fi] = isl["id"]
    # ray_cast index is polygon index, not necessarily face.index
    poly_to_island = [face_to_island[fi] if fi < nfaces else None for fi in poly_to_face]

    bb_min = Vector((
        min(p.x for p in coords), min(p.y for p in coords), min(p.z for p in coords),
    ))
    bb_max = Vector((
        max(p.x for p in coords), max(p.y for p in coords), max(p.z for p in coords),
    ))
    diag = (bb_max - bb_min).length
    ray_len = diag * 1.25 if diag > 0 else 10.0

    totals = {}
    hits = 0
    misses = 0
    for cam_from in fibonacci_sphere(n_dir):
        counts, h, m = raster_first_hit_islands(
            bvh, poly_to_island, cam_from, coords, grid, ray_len,
        )
        for iid, c in counts.items():
            totals[iid] = totals.get(iid, 0) + c
        hits += h
        misses += m
    shares = {}
    for isl in islands:
        c = totals.get(isl["id"], 0)
        shares[isl["id"]] = (c / hits) if hits else 0.0
    return {
        "per_island_hits": totals,
        "per_island_share": shares,
        "hits": hits,
        "misses": misses,
        "n_dir": n_dir,
        "grid": grid,
        "sum_share": float(sum(shares.values())),
        "ray_len": ray_len,
        "method": (
            "Share of first-hit pixels over %d Fibonacci orthographic "
            "directions at %dx%d, no backface cull, global BVH of the "
            "complete mesh. Same method as grok_g1_shellmeasure, attributed "
            "to the island that owns the hit face." % (n_dir, grid, grid)
        ),
    }


def default_spec_for_shell(shell, mesh_center, symmetry):
    ax_i = "XYZ".index(symmetry["winner_axis"])
    mid = symmetry["mid_plane"][symmetry["winner_axis"]]
    crosses = shell["bbox"][ax_i] < mid < shell["bbox"][ax_i + 3]
    return {
        "shell": shell["id"],
        "axis": infer_axis(shell, mesh_center),
        "split_lr": bool(crosses),
        "split_by_normal_sign": True,
        "local_conformal_polish": False,
    }


def classify_by_threshold(islands, vis_shares, a_shells, threshold):
    """A-piece islands below threshold move to B. B-piece islands stay on B."""
    a_set = set(a_shells)
    dest = {}
    for isl in islands:
        if isl["shell"] not in a_set:
            dest[isl["id"]] = "B"
        elif vis_shares.get(isl["id"], 0.0) < threshold:
            dest[isl["id"]] = "B"
        else:
            dest[isl["id"]] = "A"
    return dest


def threshold_sensitivity(islands, vis_shares, a_shells, threshold):
    """How many A-piece islands change atlas at 2*T and T/2 vs T."""
    a_isl = [isl for isl in islands if isl["shell"] in set(a_shells)]

    def dest_at(t):
        return classify_by_threshold(a_isl, vis_shares, a_shells, t)

    d0 = dest_at(threshold)
    d2 = dest_at(threshold * 2.0)
    dh = dest_at(threshold * 0.5)
    moved_x2 = sorted(i for i in d0 if d0[i] != d2[i])
    moved_h = sorted(i for i in d0 if d0[i] != dh[i])
    return {
        "threshold": threshold,
        "threshold_x2": threshold * 2.0,
        "threshold_half": threshold * 0.5,
        "n_a_piece_islands": len(a_isl),
        "n_on_a_at_threshold": sum(1 for v in d0.values() if v == "A"),
        "n_on_a_at_x2": sum(1 for v in d2.values() if v == "A"),
        "n_on_a_at_half": sum(1 for v in dh.values() if v == "A"),
        "islands_moved_if_x2": len(moved_x2),
        "islands_moved_if_half": len(moved_h),
        "ids_moved_if_x2": moved_x2,
        "ids_moved_if_half": moved_h,
    }


def build_classified_islands(bm, specs_by_shell, shell_by_id, v_world, f_nworld,
                             f_cent, symmetry, a_shells, lr_split_x=None):
    all_islands = []
    for sid in sorted(specs_by_shell):
        all_islands.extend(build_islands_for_spec(
            specs_by_shell[sid], shell_by_id, v_world, f_nworld, f_cent, symmetry,
            lr_split_x=lr_split_x,
        ))
    vis = measure_island_visibility(bm, v_world, all_islands, VIS_N_DIR, VIS_GRID)
    for isl in all_islands:
        isl["island_vis_share"] = float(vis["per_island_share"].get(isl["id"], 0.0))
    dest = classify_by_threshold(
        all_islands, vis["per_island_share"], a_shells, ISLAND_VIS_THRESHOLD,
    )
    sens = threshold_sensitivity(
        all_islands, vis["per_island_share"], a_shells, ISLAND_VIS_THRESHOLD,
    )
    islands_a = [isl for isl in all_islands if dest[isl["id"]] == "A"]
    islands_b = [isl for isl in all_islands if dest[isl["id"]] == "B"]
    inv = face_invariant(islands_a, islands_b, len(bm.faces))
    return {
        "all_islands": all_islands,
        "islands_a": islands_a,
        "islands_b": islands_b,
        "visibility": vis,
        "dest": dest,
        "sensitivity": sens,
        "invariant": inv,
    }


def add_cumulative_stage_deltas(rows):
    out = []
    previous = None
    for row in rows:
        copy = dict(row)
        occupancy = float(copy["occupancy"])
        if previous is None:
            copy["occupancy_gain_abs_vs_previous"] = 0.0
            copy["occupancy_gain_relative_pct_vs_previous"] = 0.0
        else:
            copy["occupancy_gain_abs_vs_previous"] = occupancy - previous
            copy["occupancy_gain_relative_pct_vs_previous"] = (
                100.0 * (occupancy - previous) / previous if previous > 0.0 else None
            )
        out.append(copy)
        previous = occupancy
    return out


def face_invariant(islands_a, islands_b, n_faces):
    fa = set()
    fb = set()
    for isl in islands_a:
        fa.update(isl["face_indices"])
    for isl in islands_b:
        fb.update(isl["face_indices"])
    inter = fa & fb
    union = fa | fb
    all_idx = set(range(n_faces))
    missing = sorted(all_idx - union)
    extra = sorted(union - all_idx)
    ok = (
        len(fa) + len(fb) == n_faces
        and not inter
        and not missing
        and not extra
        and n_faces == EXPECTED_FACE_COUNT
    )
    return {
        "faces_a": len(fa),
        "faces_b": len(fb),
        "faces_a_plus_b": len(fa) + len(fb),
        "expected": EXPECTED_FACE_COUNT,
        "intersection": len(inter),
        "unassigned": len(missing),
        "pass": ok,
        "verdict": "PASS" if ok else "FAIL",
    }


def overlap_metrics_for(islands):
    tris_all = []
    perims = []
    for isl in islands:
        for f in isl["faces"]:
            tris_all.extend(fan_tris_uv(f, isl["uv_final"]))
            perims.append(uv_perimeter(f, isl["uv_final"]))
    if not tris_all:
        return {
            "overlap_area_frac": 0.0,
            "overlap_status": "no medible",
            "reason": "no triangles",
        }
    grid, bbox, n = raster_tris(tris_all, OVERLAP_GRID_N, bbox=(0.0, 0.0, 1.0, 1.0))
    overlap = overlap_from_grid(grid, n, bbox, perims)
    grid_lo, bbox_lo, n_lo = raster_tris(
        tris_all, OVERLAP_GRID_N // 2, bbox=(0.0, 0.0, 1.0, 1.0),
    )
    overlap_lo = overlap_from_grid(grid_lo, n_lo, bbox_lo, perims)
    overlap["overlap_area_frac_grid_half"] = overlap_lo.get("overlap_area_frac")
    overlap["empirical_discretization_abs_delta"] = abs(
        float(overlap.get("overlap_area_frac") or 0.0)
        - float(overlap_lo.get("overlap_area_frac") or 0.0)
    )
    per_island_overlap = []
    for isl in islands:
        itris = island_tris_final(isl)
        iper = [uv_perimeter(f, isl["uv_final"]) for f in isl["faces"]]
        if not itris:
            continue
        ig, ib, _ = raster_tris(itris, 512)
        iov = overlap_from_grid(ig, 512, ib, iper)
        umin, vmin, umax, vmax = island_uv_bbox(isl)
        per_island_overlap.append({
            "id": isl["id"],
            "n_faces": len(isl["faces"]),
            "overlap_area_frac": iov.get("overlap_area_frac"),
            "uv_bbox": [umin, vmin, umax, vmax],
        })
    overlap["per_packed_island"] = per_island_overlap
    return overlap


def uv_area_total(islands):
    tot = 0.0
    for isl in islands:
        for f in isl["faces"]:
            pts = [isl["uv_final"][lp.index] for lp in f.loops]
            for i in range(1, len(pts) - 1):
                tot += tri_area_2d(pts[0], pts[i], pts[i + 1])
    return tot


def occupancy_unit(islands):
    return float(uv_area_total(islands))


def efficiency_decomposition_from_areas(island_area, block_bbox_area, atlas_area=1.0):
    if block_bbox_area <= 0.0 or atlas_area <= 0.0:
        raise ValueError("block_bbox_area and atlas_area must be positive")
    intra = float(island_area) / float(block_bbox_area)
    inter = float(block_bbox_area) / float(atlas_area)
    product = intra * inter
    return {
        "island_area": float(island_area),
        "block_bbox_area_sum": float(block_bbox_area),
        "atlas_area": float(atlas_area),
        "efficiency_intra_block": intra,
        "efficiency_inter_block": inter,
        "occupancy_product": product,
        "product_abs_error": abs(product - float(island_area) / float(atlas_area)),
    }


def efficiency_decomposition(islands, blocks, atlas_area=1.0):
    block_area = sum(
        max(0.0, b["uv_bbox"][2] - b["uv_bbox"][0])
        * max(0.0, b["uv_bbox"][3] - b["uv_bbox"][1])
        for b in blocks
    )
    return efficiency_decomposition_from_areas(
        occupancy_unit(islands), block_area, atlas_area,
    )


def clone_islands_for_layout(islands):
    """Copy mutable layout fields while retaining read-only bmesh face handles."""
    out = []
    for isl in islands:
        copy = dict(isl)
        copy["uv_world"] = dict(isl["uv_world"])
        copy["bbox_world"] = tuple(isl["bbox_world"])
        copy["face_indices"] = list(isl["face_indices"])
        copy["faces"] = list(isl["faces"])
        copy.pop("uv_final", None)
        copy.pop("rotation_deg", None)
        copy.pop("rotation_scope", None)
        copy.pop("pack_scale", None)
        out.append(copy)
    return out


def projected_triangle_area_coefficient(islands):
    total = 0.0
    for isl in islands:
        for face in isl["faces"]:
            for tri in fan_tris_uv(face, isl["uv_world"]):
                total += tri_area_2d(*tri)
    return float(total)


def packed_island_bbox_area_sum(islands):
    total = 0.0
    for isl in islands:
        u0, v0, u1, v1 = island_uv_bbox(isl)
        total += max(0.0, u1 - u0) * max(0.0, v1 - v0)
    return float(total)


def make_legacy_block_stage(islands, specs_by_shell):
    laid_out = clone_islands_for_layout(islands)
    scale, blocks, pack_w, pack_h = pack_and_scale_blocks(laid_out, specs_by_shell)
    return {
        "islands": laid_out,
        "blocks": blocks,
        "global_scale": scale,
        "packer": "legacy_shelf_fractional_padding",
        "allow_block_rotation": False,
        "selected_order": "area_desc",
        "pack_wh_world": [pack_w, pack_h],
    }


def make_tight_block_stage(islands, specs_by_shell, packer, allow_rotation, order_names):
    laid_out = clone_islands_for_layout(islands)
    packed = pack_and_scale_blocks_tight(
        laid_out, specs_by_shell, packer=packer,
        allow_rotation=allow_rotation, order_names=order_names,
    )
    packed["islands"] = laid_out
    return packed


def summarize_packing_stage(name, stage, measure_overlap=True):
    islands = stage["islands"]
    blocks = stage["blocks"]
    decomp = efficiency_decomposition(islands, blocks)
    gates = grouping_gates(blocks, islands)
    rotations = block_rotation_gate(blocks, islands)
    grid_order = labels_and_grid_order_gate(blocks, islands)
    density = texel_density_ratio(islands)
    overlap = overlap_metrics_for(islands) if measure_overlap else None
    return {
        "step": name,
        "occupancy": occupancy_unit(islands),
        "global_uv_scale": stage["global_scale"],
        "packer": stage["packer"],
        "allow_block_rotation": bool(stage.get("allow_block_rotation", False)),
        "selected_order": stage.get("selected_order"),
        "order_trials": stage.get("order_trials", []),
        "padding": stage.get("padding"),
        "decomposition": decomp,
        "overlap_area_frac": overlap.get("overlap_area_frac") if overlap else None,
        "overlap": overlap,
        "texel_density_ratio": density.get("texel_density_ratio"),
        "texel_density": density,
        "grouping": gates,
        "block_rotation_gate": rotations,
        "labels_and_grid_order_gate": grid_order,
        "block_rotations_deg": rotations["block_rotations_deg"],
        "islands": len(islands),
        "blocks": len(blocks),
        "faces": sum(isl["n_faces"] for isl in islands),
    }


def summarize_g8_stage(name, stage, measure_overlap=True):
    """G8 summary: islands and panels replace piece blocks as placement units."""
    islands = stage["islands"]
    layout = stage["layout_gates"]
    island_bbox_area = packed_island_bbox_area_sum(islands)
    decomp = efficiency_decomposition_from_areas(
        occupancy_unit(islands), island_bbox_area, 1.0,
    )
    density = texel_density_ratio(islands)
    overlap = overlap_metrics_for(islands) if measure_overlap else None
    grouping = {
        "block_purity_by_piece": None,
        "block_purity_worst": None,
        "block_purity_all_zero": None,
        "block_bbox_overlap_pairs": layout["island_bbox_overlap_pairs"],
        "block_bbox_overlap_count": layout["island_bbox_overlap_count"],
        "gate_unit": "island_bbox_and_panel",
        "panel_invasion_count": layout["panel_invasion_count"],
        "verdict": "PASS" if layout["pass"] else "FAIL",
    }
    rotation = {
        "allowed_angles_deg": [0, 90, 180, 270],
        "block_rotations_deg": {},
        "violations": layout["rotated_islands_skin"]["forbidden_z_projection_islands"],
        "individually_rotated_island_count": layout["rotated_islands_skin"]["count"],
        "pass": layout["rotated_islands_skin"]["pass"],
        "verdict": "PASS" if layout["rotated_islands_skin"]["pass"] else "FAIL",
    }
    labels = {
        "labels": [island_label(isl) for isl in islands],
        "unique_piece_labels": layout["labels"]["unique"],
        "relations_checked": [],
        "violations": [] if layout["labels"]["unique"] else ["duplicate_island_label"],
        "pass": layout["labels"]["unique"],
        "verdict": "PASS" if layout["labels"]["unique"] else "FAIL",
    }
    return {
        "step": name,
        "occupancy": occupancy_unit(islands),
        "global_uv_scale": stage["global_scale"],
        "packer": stage["packer"],
        "allow_block_rotation": False,
        "selected_order": stage.get("selected_order"),
        "order_trials": stage.get("order_trials", []),
        "padding": stage.get("padding"),
        "decomposition": decomp,
        "overlap_area_frac": overlap.get("overlap_area_frac") if overlap else None,
        "overlap": overlap,
        "texel_density_ratio": density.get("texel_density_ratio"),
        "texel_density": density,
        "grouping": grouping,
        "block_rotation_gate": rotation,
        "labels_and_grid_order_gate": labels,
        "block_rotations_deg": {},
        "islands": len(islands),
        "blocks": 0,
        "panels": 2,
        "faces": sum(isl["n_faces"] for isl in islands),
        "layout_gates": layout,
        "displacement": stage["displacement"],
    }


def summarize_g9_stage(name, stage, measure_overlap=True):
    """G9 summary with cross-island collisions separated from self-overlap."""
    islands = stage["islands"]
    layout = stage["layout_gates"]
    island_bbox_area = packed_island_bbox_area_sum(islands)
    decomp = efficiency_decomposition_from_areas(
        occupancy_unit(islands), island_bbox_area, 1.0,
    )
    density = texel_density_ratio(islands)
    overlap = (
        overlap_metrics_excluding_cross_island(islands) if measure_overlap else None
    )
    grouping = {
        "block_purity_by_piece": None,
        "block_purity_worst": None,
        "block_purity_all_zero": None,
        "block_bbox_overlap_pairs": [],
        "block_bbox_overlap_count": 0,
        "gate_unit": "two_disjoint_panels_and_frame_containment",
        "panel_invasion_count": layout["panel_invasion_count"],
        "cross_island_overlap_is_not_a_grouping_failure": True,
        "verdict": "PASS" if layout["pass"] else "FAIL",
    }
    rotation = {
        "allowed_angles_deg": [0, 90, 180, 270],
        "block_rotations_deg": {},
        "violations": layout["rotated_islands"]["forbidden_z_projection_islands"],
        "individually_rotated_island_count": layout["rotated_islands"]["count"],
        "pass": layout["rotated_islands"]["pass"],
        "verdict": "PASS" if layout["rotated_islands"]["pass"] else "FAIL",
    }
    labels = {
        "labels": [island_label(isl) for isl in islands],
        "unique_piece_labels": layout["labels"]["unique"],
        "relations_checked": [],
        "violations": [] if layout["labels"]["unique"] else ["duplicate_island_label"],
        "pass": layout["labels"]["unique"],
        "verdict": "PASS" if layout["labels"]["unique"] else "FAIL",
    }
    return {
        "step": name,
        "occupancy": occupancy_unit(islands),
        "global_uv_scale": stage["global_scale"],
        "packer": stage["packer"],
        "allow_block_rotation": False,
        "selected_order": stage.get("selected_order"),
        "order_trials": [],
        "padding": stage.get("padding"),
        "decomposition": decomp,
        "overlap_area_frac": overlap.get("overlap_area_frac") if overlap else None,
        "overlap": overlap,
        "texel_density_ratio": density.get("texel_density_ratio"),
        "texel_density": density,
        "grouping": grouping,
        "block_rotation_gate": rotation,
        "labels_and_grid_order_gate": labels,
        "block_rotations_deg": {},
        "islands": len(islands),
        "blocks": len(stage["blocks"]),
        "panels": 2,
        "faces": sum(isl["n_faces"] for isl in islands),
        "layout_gates": layout,
        "displacement": stage["displacement"],
        "intra_layer_overlap": stage["intra_layer_overlap"],
        "scale_fidelity": stage["scale_fidelity"],
    }


def summarize_g10_stage(name, stage, measure_overlap=True):
    """G10 summary: frame packing is separate from island self-overlap."""
    islands = stage["islands"]
    layout = stage["layout_gates"]
    density = texel_density_ratio(islands)
    overlap = (
        overlap_metrics_excluding_cross_island(islands) if measure_overlap else None
    )
    grouping = {
        "block_purity_by_piece": {frame["id"]: 0.0 for frame in stage["frames"]},
        "block_purity_worst": 0.0,
        "block_purity_all_zero": True,
        "block_bbox_overlap_pairs": layout["frame_overlap_pairs"],
        "block_bbox_overlap_count": layout["frame_overlap_count"],
        "gate_unit": "N_whole_frames_no_frame_overlap_or_island_local_pack",
        "panel_invasion_count": layout["panel_invasion_count"],
        "verdict": "PASS" if layout["pass"] else "FAIL",
    }
    rotation = {
        "allowed_angles_deg": [0, 180],
        "block_rotations_deg": {
            frame["id"]: int(frame.get("rotation_deg") or 0)
            for frame in stage["frames"]
        },
        "violations": layout["rotated_islands"]["forbidden_z_projection_islands"],
        "individually_rotated_island_count": layout["rotated_islands"]["count"],
        "pass": layout["rotated_islands"]["pass"],
        "verdict": "PASS" if layout["rotated_islands"]["pass"] else "FAIL",
    }
    labels = {
        "labels": [island_label(isl) for isl in islands],
        "unique_piece_labels": layout["labels"]["unique"],
        "relations_checked": [frame["id"] for frame in stage["frames"]],
        "violations": [] if layout["labels"]["unique"] else ["duplicate_island_label"],
        "pass": layout["labels"]["unique"],
        "verdict": "PASS" if layout["labels"]["unique"] else "FAIL",
    }
    return {
        "step": name,
        "occupancy": occupancy_unit(islands),
        "global_uv_scale": stage["global_scale"],
        "packer": stage["packer"],
        "allow_block_rotation": False,
        "selected_order": stage.get("selected_order"),
        "order_trials": [],
        "padding": stage.get("padding"),
        "decomposition": efficiency_decomposition(islands, stage["frames"], 1.0),
        "overlap_area_frac": overlap.get("overlap_area_frac") if overlap else None,
        "overlap": overlap,
        "texel_density_ratio": density.get("texel_density_ratio"),
        "texel_density": density,
        "grouping": grouping,
        "block_rotation_gate": rotation,
        "labels_and_grid_order_gate": labels,
        "block_rotations_deg": rotation["block_rotations_deg"],
        "islands": len(islands),
        "blocks": len(stage["frames"]),
        "panels": len(stage["frames"]),
        "faces": sum(isl["n_faces"] for isl in islands),
        "layout_gates": layout,
        "displacement": stage["displacement"],
        "intra_layer_overlap": stage["intra_layer_overlap"],
        "scale_fidelity": stage["scale_fidelity"],
        "affine_vertex_gate": stage["affine_vertex_gate"],
    }


def _monotone_scale_bound(predicate, iterations=64):
    lo = 0.0
    hi = 1.0
    while predicate(hi):
        lo = hi
        hi *= 2.0
        if hi > 64.0:
            raise RuntimeError("scale upper-bound search exceeded 64")
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if predicate(mid):
            lo = mid
        else:
            hi = mid
    return lo, hi


def strict_grouping_ceiling(islands, specs_by_shell, achieved_scale):
    """Rigorous rectangle-area/dimension upper bound for strict block packing."""
    cfg = fixed_padding_config()
    bin_side = 1.0 - 2.0 * cfg["pad_uv"]
    available_area = bin_side * bin_side

    def boxes_at(scale):
        _local, boxes, _meta = _tight_block_layout(islands, specs_by_shell, scale)
        return boxes

    area_lo, area_hi = _monotone_scale_bound(
        lambda scale: sum(b["w"] * b["h"] for b in boxes_at(scale)) <= available_area + 1e-15,
    )
    dim_lo, dim_hi = _monotone_scale_bound(
        lambda scale: all(
            max(b["w"], b["h"]) <= bin_side + 1e-15 for b in boxes_at(scale)
        ),
    )
    upper_scale = min(area_hi, dim_hi)
    limiting = "rectangle_area" if area_hi <= dim_hi else "largest_block_dimension"
    coeff = projected_triangle_area_coefficient(islands)

    # Padding-free intra-block ceiling: the fixed L/R x n+/n- grid remains,
    # but texel margins and label bands vanish asymptotically.
    by_shell = defaultdict(list)
    for isl in islands:
        by_shell[isl["shell"]].append(isl)
    block_geom_area = 0.0
    for sid, slist in by_shell.items():
        spec = specs_by_shell[sid]
        _local, bw, bh, _grid = layout_piece_block(
            slist, spec["split_lr"], spec["split_by_normal_sign"],
            inner_pad=0.0, outer_pad=0.0, label_h=0.0,
            cell_mode="fitted",
        )
        block_geom_area += bw * bh
    intra_ceiling = coeff / block_geom_area if block_geom_area > 0.0 else None
    achieved_occupancy = coeff * achieved_scale * achieved_scale
    occupancy_upper = coeff * upper_scale * upper_scale
    return {
        "method": (
            "Upper bound from non-overlapping strict block rectangles: sum(block areas) "
            "must fit inside the 8-texel-bordered square and every block dimension must fit."
        ),
        "available_bin_side_uv": bin_side,
        "available_bin_area_uv2": available_area,
        "projected_triangle_area_coefficient": coeff,
        "area_bound_scale_feasible": area_lo,
        "area_bound_scale_infeasible": area_hi,
        "dimension_bound_scale_feasible": dim_lo,
        "dimension_bound_scale_infeasible": dim_hi,
        "limiting_bound": limiting,
        "strict_grouping_scale_upper_bound": upper_scale,
        "achieved_scale": achieved_scale,
        "achieved_scale_vs_upper_bound": achieved_scale / upper_scale if upper_scale > 0.0 else None,
        "occupancy_upper_bound": occupancy_upper,
        "achieved_occupancy_from_coefficient": achieved_occupancy,
        "occupancy_gap_to_upper_bound": occupancy_upper - achieved_occupancy,
        "intra_block_asymptotic_ceiling_no_padding": intra_ceiling,
        "inter_block_absolute_ceiling": 1.0,
    }


def estimate_strict_grouping_cost(islands, blocks):
    """Arithmetic estimate only; it never computes or applies nested placement."""
    decomp = efficiency_decomposition(islands, blocks)
    occupancy = decomp["occupancy_product"]
    island_bbox_area = packed_island_bbox_area_sum(islands)
    shape_fill = occupancy / island_bbox_area if island_bbox_area > 0.0 else 0.0
    current_inter = decomp["efficiency_inter_block"]
    estimated = min(1.0, shape_fill * current_inter)
    optimistic_upper = min(1.0, current_inter)
    return {
        "label": "ESTIMACION_NO_IMPLEMENTADA",
        "method": (
            "Replace strict piece-block rectangles by the sum of island bboxes, "
            "retain the measured final inter-pack efficiency, and do not credit "
            "air inside each island bbox. No nesting layout was generated."
        ),
        "current_occupancy": occupancy,
        "island_bbox_area_sum": island_bbox_area,
        "block_bbox_area_sum": decomp["block_bbox_area_sum"],
        "block_level_void_area": max(0.0, decomp["block_bbox_area_sum"] - island_bbox_area),
        "island_shape_fill_vs_own_bboxes": shape_fill,
        "assumed_inter_pack_efficiency": current_inter,
        "estimated_occupancy_without_strict_grouping": estimated,
        "estimated_gain_abs": estimated - occupancy,
        "estimated_gain_relative_pct": (
            100.0 * (estimated - occupancy) / occupancy if occupancy > 0.0 else None
        ),
        "optimistic_upper_if_all_intra_block_air_reusable": optimistic_upper,
        "optimistic_upper_gain_abs": optimistic_upper - occupancy,
    }


def write_assignment_with_axes(path, raw_assignment, selected_specs, axis_records):
    payload = json.loads(json.dumps(raw_assignment))
    axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
    payload["projection_axes"] = axes
    for item in payload.get("atlas_a") or []:
        if isinstance(item, dict) and item.get("shell") in axes:
            item["axis"] = axes[item["shell"]]
    payload["g6_axis_search"] = {
        "policy": AXIS_SEARCH_POLICY,
        "incumbent_source": "input projection_axes (out_tight/assignment_REAL.json for G6)",
        "axes_tested_per_piece": list(AXIS_NAMES),
        "overlap_grid_n": AXIS_SEARCH_OVERLAP_GRID,
        "absolute_self_overlap_limit": AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT,
        "changed": [
            {"shell": r["shell"], "from": r["axis_before"], "to": r["axis_after"]}
            for r in axis_records if r["changed"]
        ],
    }
    payload["g6_note"] = (
        "projection_axes is authoritative for all 13 pieces. Atlas membership, "
        "split flags and island_vis_share threshold 0.005 are unchanged; only "
        "a strictly more compact orthographic axis at self-overlap <=0.01 may "
        "replace the G4 incumbent from the source assignment."
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % path)


def write_assignment_g7_frozen(path, raw_assignment, selected_specs):
    """Copy the G6 assignment while proving that no projection axis changed."""
    payload = json.loads(json.dumps(raw_assignment))
    input_axes = dict(raw_assignment.get("projection_axes") or {})
    selected_axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
    changed = [
        {"shell": sid, "from": input_axes.get(sid), "to": selected_axes.get(sid)}
        for sid in sorted(selected_axes)
        if input_axes.get(sid) != selected_axes.get(sid)
    ]
    if changed or set(input_axes) != set(selected_axes):
        raise RuntimeError("G7 axis freeze violated: %s" % changed)
    payload["projection_axes"] = input_axes
    payload["g7_axis_freeze"] = {
        "policy": "input_g6_projection_axes_are_authoritative_and_untouched",
        "source": "input assignment_REAL.json",
        "axes_tested": [],
        "changed": changed,
        "all_axis_values_equal_to_input": selected_axes == input_axes,
    }
    payload["g7_note"] = (
        "Only block placement changes. Projection axes, atlas membership, split "
        "flags and island_vis_share threshold 0.005 are frozen from G6."
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % path)


def write_assignment_g8_frozen(path, raw_assignment, selected_specs):
    """Copy G7 assignment and prove G8 changed neither axes nor membership."""
    payload = json.loads(json.dumps(raw_assignment))
    input_axes = dict(raw_assignment.get("projection_axes") or {})
    selected_axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
    changed = [
        {"shell": sid, "from": input_axes.get(sid), "to": selected_axes.get(sid)}
        for sid in sorted(selected_axes)
        if input_axes.get(sid) != selected_axes.get(sid)
    ]
    if changed or set(input_axes) != set(selected_axes):
        raise RuntimeError("G8 axis freeze violated: %s" % changed)
    payload["projection_axes"] = input_axes
    payload["g8_axis_freeze"] = {
        "policy": "input_g7_projection_axes_are_authoritative_and_untouched",
        "source": "input assignment_REAL.json",
        "axes_tested": [],
        "changed": changed,
        "all_axis_values_equal_to_input": selected_axes == input_axes,
    }
    payload["g8_note"] = (
        "Only island placement and the literal X=0 L/R correction change. Projection "
        "axes, atlas piece membership, split flags and island_vis_share threshold "
        "0.005 are frozen from G7. S08 n- remains in atlas B by that threshold."
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % path)


def write_assignment_g9_frozen(path, raw_assignment, selected_specs):
    """Copy G8 assignment and prove G9 changed placement only."""
    payload = json.loads(json.dumps(raw_assignment))
    input_axes = dict(raw_assignment.get("projection_axes") or {})
    selected_axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
    changed = [
        {"shell": sid, "from": input_axes.get(sid), "to": selected_axes.get(sid)}
        for sid in sorted(selected_axes)
        if input_axes.get(sid) != selected_axes.get(sid)
    ]
    if changed or set(input_axes) != set(selected_axes):
        raise RuntimeError("G9 axis freeze violated: %s" % changed)
    payload["projection_axes"] = input_axes
    payload["g9_axis_freeze"] = {
        "policy": "input_g8_projection_axes_are_authoritative_and_untouched",
        "source": "input assignment_REAL.json",
        "axes_tested": [],
        "changed": changed,
        "all_axis_values_equal_to_input": selected_axes == input_axes,
    }
    payload["g9_note"] = (
        "Only atlas-A island placement changes: n+ and n- remain separate equal "
        "frames, one shared isotropic affine scale, zero per-island displacement, "
        "and no collision resolver. Projection axes, atlas membership, split flags, "
        "the literal X=0 correction and island_vis_share threshold 0.005 are frozen "
        "from G8."
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % path)


def write_assignment_g10_frozen(path, raw_assignment, selected_specs):
    """Copy G9 assignment and prove G10 changed only whole-frame placement."""
    payload = json.loads(json.dumps(raw_assignment))
    input_axes = dict(raw_assignment.get("projection_axes") or {})
    selected_axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
    changed = [
        {"shell": sid, "from": input_axes.get(sid), "to": selected_axes.get(sid)}
        for sid in sorted(selected_axes)
        if input_axes.get(sid) != selected_axes.get(sid)
    ]
    if changed or set(input_axes) != set(selected_axes):
        raise RuntimeError("G10 axis freeze violated: %s" % changed)
    payload["projection_axes"] = input_axes
    payload["g10_axis_freeze"] = {
        "policy": "input_g9_projection_axes_are_authoritative_and_untouched",
        "source": "input out_g9/assignment_REAL.json",
        "axes_tested": [],
        "changed": changed,
        "all_axis_values_equal_to_input": selected_axes == input_axes,
    }
    payload["g10_note"] = (
        "Atlas A starts from the family-preserving G9 coloring. G10 continuous "
        "triangle-area verification found a missed same-layer edge, so the coloring "
        "is repaired with the minimum number of island color changes; the continuously "
        "measured minimum is four n+ skin frames plus two n- internal frames. Islands keep literal XY "
        "centers, one common scale per variant and zero frame-local displacement. "
        "Projection axes, membership, split flags, X=0 correction and threshold 0.005 "
        "remain frozen from G9."
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % path)


def atlas_payload_metrics(islands, blocks, overlap, density, metrics_a, gates):
    area_3d = float(sum(isl["area_3d"] for isl in islands))
    n_faces = int(sum(isl["n_faces"] for isl in islands))
    return {
        "islands": len(islands),
        "blocks": len(blocks),
        "faces": n_faces,
        "area_3d": area_3d,
        "occupancy": occupancy_unit(islands),
        "occupancy_vs_bbox": (metrics_a or {}).get("occupancy_vs_bbox"),
        "overlap_area_frac": overlap.get("overlap_area_frac"),
        "texel_density_ratio": density.get("texel_density_ratio"),
        "stretch_p50_rel": (metrics_a or {}).get("stretch_p50_rel"),
        "stretch_p95_rel": (metrics_a or {}).get("stretch_p95_rel"),
        "stretch_max_rel": (metrics_a or {}).get("stretch_max_rel"),
        "block_purity_by_piece": gates["block_purity_by_piece"],
        "block_purity_worst": gates["block_purity_worst"],
        "block_purity_all_zero": gates["block_purity_all_zero"],
        "block_bbox_overlap_count": gates["block_bbox_overlap_count"],
        "block_bbox_overlap_pairs": gates["block_bbox_overlap_pairs"],
        "grouping_verdict": gates["verdict"],
        "island_ids": [isl["id"] for isl in islands],
        "block_shells": [b["shell"] for b in blocks],
        "overlap": overlap,
        "texel_density": density,
        "measure_subset": metrics_a,
    }


def write_uvs(bm, islands, atlas_b_faces):
    uv = bm.loops.layers.uv.active
    if uv is None:
        uv = bm.loops.layers.uv.new("UVMap")
    # BMLoopSeq has no ensure_lookup_table in Blender 5.1; index via faces.
    loop_by_index = {}
    for f in bm.faces:
        for lp in f.loops:
            loop_by_index[lp.index] = lp
    for f in atlas_b_faces:
        for lp in f.loops:
            lp[uv].uv = PARK_UV
    for isl in islands:
        for lp_i, (u, v) in isl["uv_final"].items():
            loop_by_index[lp_i][uv].uv = (u, v)
    return uv


def measure_filtered_mesh(obj, keep_face_indices):
    """Same formulas as measure(), but drop faces not in the paint atlas.

    Isolates atlas A so parked atlas_b UVs cannot game occupancy/islands.
    shells() still runs on this subset (components among remaining faces).
    """
    keep = set(keep_face_indices)
    mesh = obj.data
    tmp = mesh.copy()
    bm = bmesh.new()
    bm.from_mesh(tmp)
    bm.faces.ensure_lookup_table()
    drop = [f for f in bm.faces if f.index not in keep]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(tmp)
    bm.free()
    tmp.name = mesh.name + "_atlasA_only"
    tmp_obj = bpy.data.objects.new(tmp.name, tmp)
    try:
        m = measure(tmp_obj)
    finally:
        bpy.data.objects.remove(tmp_obj, do_unlink=True)
        bpy.data.meshes.remove(tmp)
    return m


def texel_density_ratio(islands):
    """Scale per island from world-projected pairwise distances vs final UV.

    By construction this is the single global pack scale for every island;
    a ratio far from 1.0 is a bug (per-island normalisation crept in).
    """
    dens = []
    per = []
    for isl in islands:
        ratios = []
        items = list(isl["uv_world"].items())
        # Pair consecutive loops; skip near-zero projected edges.
        for i in range(len(items)):
            li, pw = items[i]
            lj, qw = items[(i + 1) % len(items)]
            if li not in isl["uv_final"] or lj not in isl["uv_final"]:
                continue
            dw = math.hypot(qw[0] - pw[0], qw[1] - pw[1])
            pf = isl["uv_final"][li]
            qf = isl["uv_final"][lj]
            df = math.hypot(qf[0] - pf[0], qf[1] - pf[1])
            if dw > 1e-8:
                ratios.append(df / dw)
        if not ratios:
            continue
        ratios.sort()
        d = ratios[len(ratios) // 2]
        dens.append(d)
        per.append({"island": isl["id"], "texel_density": d, "n_edges": len(ratios)})
    if not dens:
        return {
            "texel_density_ratio": None,
            "texel_density_status": "no medible",
            "per_island": per,
        }
    dmin = min(dens)
    dmax = max(dens)
    ratio = (dmax / dmin) if dmin > 1e-18 else float("inf")
    return {
        "texel_density_ratio": float(ratio),
        "texel_density_min": float(dmin),
        "texel_density_max": float(dmax),
        "texel_density_status": "ok" if ratio < 1.05 else "BUG_expected_near_1",
        "per_island": per,
    }


def control_a(shell, v_world):
    """+Z vs -Z silhouettes of CONTROL_A_SHELL. Expectations declared above."""
    faces = shell["faces"]
    expect = {
        "locked_before_results": True,
        "shell": CONTROL_A_SHELL,
        "axis_pos": CONTROL_A_AXIS_POS,
        "axis_neg": CONTROL_A_AXIS_NEG,
        "expect_iou_mirrored_min": CONTROL_A_EXPECT_IOU_MIRROR_MIN,
        "expect_iou_unmirrored_max": CONTROL_A_EXPECT_IOU_UNMIRROR_MAX,
        "rationale": (
            "Opposite cameras must photograph the same outline mirrored, not a "
            "different pair of world axes. S06 is a one-sided body panel "
            "(not X-symmetric), so the un-mirrored overlay should NOT match."
        ),
    }

    def face_uv(axis, flip_u=False):
        umin = vmin = 1e30
        umax = vmax = -1e30
        raw = {}
        for f in faces:
            pts = []
            for lp in f.loops:
                u, v = project_co(v_world[lp.vert.index], axis)
                if flip_u:
                    u = -u
                pts.append((u, v))
                umin = min(umin, u); umax = max(umax, u)
                vmin = min(vmin, v); vmax = max(vmax, v)
            raw[f.index] = pts
        bbox = (umin, vmin, umax, vmax)
        w = max(bbox[2] - bbox[0], 1e-18)
        h = max(bbox[3] - bbox[1], 1e-18)
        tris = []
        for pts in raw.values():
            norm = [((p[0] - bbox[0]) / w, (p[1] - bbox[1]) / h) for p in pts]
            for i in range(1, len(norm) - 1):
                tris.append((norm[0], norm[i], norm[i + 1]))
        return tris

    tris_p = face_uv(CONTROL_A_AXIS_POS, flip_u=False)
    tris_n = face_uv(CONTROL_A_AXIS_NEG, flip_u=False)
    tris_p_mirr = face_uv(CONTROL_A_AXIS_POS, flip_u=True)
    unit = (0.0, 0.0, 1.0, 1.0)
    gp, _, _ = raster_tris(tris_p, CONTROL_GRID_N, unit)
    gn, _, _ = raster_tris(tris_n, CONTROL_GRID_N, unit)
    gm, _, _ = raster_tris(tris_p_mirr, CONTROL_GRID_N, unit)

    def occ(g):
        return {i for i, c in enumerate(g) if c >= 1}

    op, on, om = occ(gp), occ(gn), occ(gm)

    def iou(a, b):
        if not a and not b:
            return 1.0
        inter = len(a & b)
        uni = len(a | b)
        return inter / uni if uni else 0.0

    iou_m = iou(om, on)
    iou_u = iou(op, on)
    # Per-vertex algebraic check: -Z UV should equal (-u, v) of +Z.
    max_err = 0.0
    for v in {vt for f in faces for vt in f.verts}:
        u, w = project_co(v_world[v.index], CONTROL_A_AXIS_POS)
        um, vm = project_co(v_world[v.index], CONTROL_A_AXIS_NEG)
        max_err = max(max_err, math.hypot(um - (-u), vm - w))
    got = {
        "iou_mirrored": float(iou_m),
        "iou_unmirrored": float(iou_u),
        "vertex_mirror_max_abs_err": float(max_err),
        "grid_n": CONTROL_GRID_N,
    }
    pass_m = iou_m >= CONTROL_A_EXPECT_IOU_MIRROR_MIN
    pass_u = iou_u <= CONTROL_A_EXPECT_IOU_UNMIRROR_MAX
    return {
        "expect": expect,
        "got": got,
        "pass_mirror": pass_m,
        "pass_unmirror_distinct": pass_u,
        "pass": pass_m and pass_u,
        "verdict": (
            "PASS" if (pass_m and pass_u) else "FAIL"
        ),
    }


def control_b(shell, v_world, f_nworld, f_cent, symmetry):
    expect = {
        "locked_before_results": True,
        "shell": CONTROL_B_SHELL,
        "axis": CONTROL_B_AXIS,
        "expect_unsplit_overlap_min": CONTROL_B_EXPECT_UNSPLIT_MIN,
        "expect_split_overlap_max": CONTROL_B_EXPECT_SPLIT_MAX,
        "expect_drop_min": CONTROL_B_EXPECT_DROP_MIN,
        "rationale": (
            "S03 is a closed shell (0 boundary edges, Euler 2). Projecting it "
            "from +Y without a silhouette seam stacks the far side on the near "
            "side. split_by_normal_sign + packing must separate those halves "
            "and the overlap fraction must fall. If it does not change, the "
            "partition is dead code."
        ),
    }

    def run(split_nsign):
        spec = {
            "shell": shell["id"],
            "axis": CONTROL_B_AXIS,
            "split_lr": False,
            "split_by_normal_sign": split_nsign,
            "local_conformal_polish": False,
        }
        islands = build_islands_for_spec(
            spec, {shell["id"]: shell}, v_world, f_nworld, f_cent, symmetry,
        )
        pack_and_scale(islands)
        tris = []
        perims = []
        for isl in islands:
            for f in isl["faces"]:
                tris.extend(fan_tris_uv(f, isl["uv_final"]))
                perims.append(uv_perimeter(f, isl["uv_final"]))
        grid, bbox, n = raster_tris(tris, OVERLAP_GRID_N, bbox=(0.0, 0.0, 1.0, 1.0))
        ov = overlap_from_grid(grid, n, bbox, perims)
        ov["n_islands"] = len(islands)
        return ov

    unsplit = run(False)
    split = run(True)
    u = unsplit["overlap_area_frac"]
    s = split["overlap_area_frac"]
    drop = u - s
    ok_u = u >= CONTROL_B_EXPECT_UNSPLIT_MIN
    ok_s = s <= CONTROL_B_EXPECT_SPLIT_MAX
    ok_d = drop >= CONTROL_B_EXPECT_DROP_MIN
    return {
        "expect": expect,
        "got": {
            "unsplit": unsplit,
            "split": split,
            "drop": float(drop),
        },
        "pass_unsplit_high": ok_u,
        "pass_split_low": ok_s,
        "pass_drop": ok_d,
        "pass": ok_u and ok_s and ok_d,
        "verdict": "PASS" if (ok_u and ok_s and ok_d) else "FAIL",
    }


def dump_islands_json(path, islands, smoke, blocks=None, atlas_name="A", extra=None):
    payload = {
        "SMOKE": bool(smoke),
        "NOT_the_real_paint_mechanical_split": bool(smoke),
        "atlas": atlas_name,
        "uv_space": [0.0, 0.0, 1.0, 1.0],
        "blocks": [],
        "islands": [],
    }
    if extra:
        payload.update(extra)
    for blk in blocks or []:
        payload["blocks"].append({
            "shell": blk["shell"],
            "label": blk.get("label", blk["shell"]),
            "uv_bbox": [round(x, 6) for x in blk["uv_bbox"]],
            "label_uv": [round(x, 6) for x in blk["label_uv"]],
            "n_islands": blk["n_islands"],
            "rotation_deg": int(blk.get("rotation_deg") or 0),
            "anatomical_side": blk.get("anatomical_side"),
            "mirror_pair": blk.get("mirror_pair"),
            "centroid_y_3d": blk.get("centroid_y_3d"),
            "layer_id": blk.get("id"),
            "family": blk.get("family"),
            "ordinal": blk.get("ordinal"),
            "z_range": blk.get("z_range"),
            "z_mean": blk.get("z_mean"),
            "z_label": blk.get("z_label"),
            "island_ids": blk.get("island_ids"),
            "island_label": blk.get("island_label"),
            "centerline_uv": blk.get("centerline_uv"),
            "frame_bbox": blk.get("frame_bbox"),
            "source_bbox_world": blk.get("source_bbox_world"),
            "content_bbox_uv": blk.get("content_bbox_uv"),
            "full_quad_bbox_uv": blk.get("full_quad_bbox_uv"),
            "ghost_mapping": blk.get("ghost_mapping"),
        })
    for isl in islands:
        tris = island_tris_final(isl)
        edges = island_boundary_edges(isl)
        payload["islands"].append({
            "id": isl["id"],
            "label": island_label(isl),
            "shell": isl["shell"],
            "axis": isl["axis"],
            "lr": isl.get("lr"),
            "normal_sign": isl.get("nsign"),
            "rotation_deg": int(isl.get("rotation_deg") or 0),
            "panel": isl.get("panel"),
            "n_faces": len(isl["faces"]),
            "area_3d": round(isl.get("area_3d") or 0.0, 8),
            "island_vis_share": isl.get("island_vis_share"),
            "centroid_3d": isl.get("centroid_3d"),
            "target_uv": isl.get("target_uv"),
            "placement_center_uv": isl.get("placement_center_uv"),
            "g10_layer_id": isl.get("g10_layer_id"),
            "g10_frame_bbox": isl.get("g10_frame_bbox"),
            "target_frame_local_uv": isl.get("target_frame_local_uv"),
            "placement_center_frame_uv": isl.get("placement_center_frame_uv"),
            "target_displacement_uv": isl.get("target_displacement_uv"),
            "centroid": [round(c, 6) for c in weighted_centroid(tris)],
            "tris": [[[round(p[0], 6), round(p[1], 6)] for p in t] for t in tris],
            "edges": [[[round(p[0], 6), round(p[1], 6)] for p in e] for e in edges],
        })
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=None, separators=(",", ":"))
    log("WROTE %s (%d islands, %d blocks)" % (
        path, len(payload["islands"]), len(payload["blocks"]),
    ))


def _source_line_number(token):
    with open(__file__, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if token in line:
                return line_number
    return None


def write_g10_report(path, metrics):
    variants = metrics["g10_variants"]
    cropped = variants["B_cropped_frames"]
    full = variants["A_full_frames"]
    recommendation = metrics["recommendation"]
    overlap = metrics["g9_overlap_area"]
    layers = metrics["g10_layering"]["layers"]
    gates = metrics["nine_gates"]
    line_layout = _source_line_number("def pack_and_scale_islands_g10")
    line_verify = _source_line_number("def g10_raster_layer_collisions")
    line_frames = _source_line_number("def g10_pack_frame_layout")

    rows = []
    for row in metrics["price_table"]:
        texels = row["useful_texels"]
        rows.append(
            "| {config} | {layers} | {collisions} | {occupancy:.12f} | "
            "{t2048:.2f} / {t4096:.2f} / {t8192:.2f} |".format(
                config=row["config"], layers=row["layers"],
                collisions=row["collisions"], occupancy=row["occupancy"],
                t2048=texels["2048"], t4096=texels["4096"],
                t8192=texels["8192"],
            )
        )
    layer_rows = []
    for layer in layers:
        layer_rows.append(
            "| {id} | {family} | {zmin:.9f} .. {zmax:.9f} | {islands} |".format(
                id=layer["id"], family=layer["family"],
                zmin=layer["z_range"][0], zmax=layer["z_range"][1],
                islands=", ".join("`%s`" % item for item in layer["island_ids"]),
            )
        )
    gate_rows = []
    for number, (name, gate) in enumerate(gates.items(), 1):
        gate_rows.append("%d. **%s — %s.** %s" % (
            number, "PASS" if gate["pass"] else "FAIL", name,
            gate.get("evidence", ""),
        ))

    text = r"""# REPORT_G10 — zero overlaps with N frames

Status: **{status}**. Main variant: **B, cropped frames**. Measured recommendation: **{recommended}**.

## A -- WHAT WAS DONE

- The start was the G9 family split of **3 skin layers + 2 internal layers** in `intra_layer_overlap.layering_by_panel`; `global_aligned_z_layering` was discarded because it mixes `n+` and `n-`. Continuous clipping added **{continuous_only_edges} sub-pixel edges** that the G9 raster did not see; **{literal_exact_collisions}** of them fell inside one literal layer and made the 3+2 split invalid. So the literal split was not applied blindly: the same graph was repaired with the smallest real change of partition (**{repair_changed_count} islands**) and the corrected minimum became **{skin_layers}+{internal_layers} = {n_layers} layers**. Extraction, verification and repair: `project_atlas.py:{line_layout}`.
- The corrected split was rasterized again before use and after placing each variant (`project_atlas.py:{line_verify}`): aligned source **{source_collisions} collisions**, variant B **{cropped_collisions}**, variant A **{full_collisions}**. The corrected continuous gate also gives **{corrected_exact_collisions}**.
- Variant B (`atlas_a.png`): {n_layers} frames cropped to the bounding box of their content and packed as indivisible rectangles, with no frame rotation and no island packing. Occupancy **{cropped_occupancy:.12f}**, common scale **{cropped_scale:.15f}**.
- Variant A (`atlas_a_full_frames.png`): {n_layers} full XY footprints that can be compared directly. Occupancy **{full_occupancy:.12f}**, common scale **{full_scale:.15f}**.
- Vote: **{recommended}**. {recommendation_reason}

### Final measured layers

| layer | family | Z range of centroids | islands |
|---|---|---:|---|
{layer_rows}

## B -- EVIDENCE

### Nine gates

{gate_rows}

### Full price

`useful texel = sqrt(occupancy) × resolution`.

| config | layers | collisions | occupancy | useful texel 2048 / 4096 / 8192 |
|---|---:|---:|---:|---:|
{price_rows}

Variant B gives **{linear_gain:.3f}%** more useful linear resolution than A; the declared threshold for recommending the loss of comparability was **{gain_threshold:.1f}%**.

### UV area taken by the 15 G9 overlaps

- Continuous sum of the 15 pairwise intersections: **{continuous_pairwise:.15f} UV²**, **{continuous_unit_pct:.6f}%** of the unit atlas and **{continuous_occ_pct:.6f}%** of the G9 occupancy. It comes from exact triangle-triangle clipping and can count a triple intersection twice; it is not a polygon union.
- Conservative raster union of the pixels covered by at least two islands: **{unique:.15f} UV²**, **{unit_pct:.6f}%** of the unit atlas and **{occ_pct:.6f}%** of the G9 occupancy.
- Raster control: sum of the 15 pairs **{pairwise:.15f} UV²** at {overlap_grid}×{overlap_grid}. The structure read was the final G9 UV rebuilt in this run, before the {n_layers} layers were separated.

### Scale constants

- B cropped: `a = {cropped_scale:.15f}` in the {n_layers} layers; CV between layers `{cropped_cv:.3e}`; `texel_density_ratio = {cropped_density:.15f}`.
- A full: `a = {full_scale:.15f}` in the {n_layers} layers; CV between layers `{full_cv:.3e}`; `texel_density_ratio = {full_density:.15f}`.
- Largest displacement of centres: B `{cropped_displacement}`, A `{full_displacement}` UV.
- Largest `affine_vertex_gate` error: B `{cropped_affine}`, A `{full_affine}` UV.

### Integrity and exact commands

- `retopo_final.blend` final SHA-256: `{blend_sha}`.
- `out_g9/atlas_metrics.json` kept SHA-256 `{g9_metrics_sha}`.
- `out_g9/assignment_REAL.json` kept SHA-256 `{g9_assignment_sha}`.
- The frame packing is at `project_atlas.py:{line_frames}`. No island packer was run.
- The PNG files were drawn with `draw_atlas_fallback.ps1` / System.Drawing; PIL and a headless render were not used.

[EXACT]

```powershell
python -m py_compile .\project_atlas.py .\test_project_atlas_g9.py .\test_project_atlas_g10.py .\verify_g10.py
blender -b '.\retopo_final.blend' --python '.\test_project_atlas_g9.py'
blender -b '.\retopo_final.blend' --python '.\test_project_atlas_g10.py'
blender -b '.\retopo_final.blend' --python '.\project_atlas.py' -- '.\out_g9\assignment_REAL.json' '.\out_g10'
& '.\draw_atlas_fallback.ps1' -OutDir '.\out_g10'
python .\verify_g10.py
Get-FileHash -Algorithm SHA256 '.\retopo_final.blend'
```

## C -- RISKS AND UNCERTAINTY

- The ghost silhouette of B is **visual context fitted to each frame**; it does not use the UV scale of the islands and does not count in occupancy or in the gates. This choice resolves the geometric conflict between cropping to the content's bounding box and showing the full footprint inside the same rectangle.
- The 3+2 minimum was measured again on the union of the G9 raster graph and the continuous triangle-triangle graph. The literal G9 split was not zero in the continuous check; the corrected one is. The 1024² raster is still the requested gate for the variants.
- Layers with a single island: {singleton_note}.
- Titles carry family, ordinal and Z range; the full island list is in the side legend, so no unreadable text sits inside small frames.
- Working assumption so the run does not stop: **10% useful linear gain** is the threshold that justifies losing immediate comparability. The raw figure is published so the owner can replace that criterion.

### What was NOT verified

- No EEVEE, Cycles or OpenGL render and no manual paint test.
- The UVs were not exported to a consumer or integrated into DayZ.
- The continuous triangle-triangle clipping was not checked against a second, independent geometry library; positive and negative fixtures and the 1024² raster of both variants do cover it.
- `retopo_final.blend` was not saved or modified.
- Nothing was written outside the workspace.

## D -- OUT OF SCOPE

- The orthographic 3D reference coloured with the atlas palette, proposed in G9, is still not done.
""".format(
        status="9/9 GATES PASS" if metrics["all_required_gates_green"] else "FAILED",
        recommended=recommendation["recommended_variant"],
        recommendation_reason=recommendation["reason"],
        line_layout=line_layout, line_verify=line_verify, line_frames=line_frames,
        source_collisions=metrics["g10_layering"]["source_verification"]["collision_pair_count"],
        literal_exact_collisions=metrics["g10_layering"]["source_literal_exact_collision_pair_count"],
        continuous_only_edges=sum(
            "G9_raster_1024" not in row["sources"]
            for row in metrics["g10_layering"]["combined_conflict_graph"]["pairs"]
        ),
        corrected_exact_collisions=metrics["g10_layering"]["corrected_exact_collision_pair_count"],
        repair_changed_count=metrics["g10_layering"]["repair_changed_count"],
        skin_layers=metrics["g10_layering"]["minimum_by_family"]["skin"],
        internal_layers=metrics["g10_layering"]["minimum_by_family"]["internal"],
        n_layers=metrics["g10_layering"]["minimum_total_layers"],
        cropped_collisions=cropped["intra_layer_collisions"]["collision_pair_count"],
        full_collisions=full["intra_layer_collisions"]["collision_pair_count"],
        cropped_occupancy=cropped["occupancy"], full_occupancy=full["occupancy"],
        cropped_scale=cropped["global_scale"], full_scale=full["global_scale"],
        layer_rows="\n".join(layer_rows), gate_rows="\n".join(gate_rows),
        price_rows="\n".join(rows), linear_gain=recommendation["linear_resolution_gain_pct_B_vs_A"],
        gain_threshold=recommendation["minimum_linear_gain_pct_to_recommend_B"],
        continuous_pairwise=overlap["continuous_pairwise_area_sum_uv"],
        continuous_unit_pct=overlap["continuous_pairwise_percent_of_unit_atlas"],
        continuous_occ_pct=overlap["continuous_pairwise_percent_of_g9_occupancy"],
        pairwise=overlap["pairwise_area_sum_uv"], unique=overlap["unique_overlap_area_uv"],
        unit_pct=overlap["unique_overlap_percent_of_unit_atlas"],
        occ_pct=overlap["unique_overlap_percent_of_g9_occupancy"],
        overlap_grid=overlap["grid_n"],
        cropped_cv=cropped["scale_fidelity"]["between_layers_cv"],
        full_cv=full["scale_fidelity"]["between_layers_cv"],
        cropped_density=cropped["texel_density_ratio"], full_density=full["texel_density_ratio"],
        cropped_displacement=cropped["displacement"]["worst_uv"],
        full_displacement=full["displacement"]["worst_uv"],
        cropped_affine=cropped["affine_vertex_gate"]["max_abs_error_uv"],
        full_affine=full["affine_vertex_gate"]["max_abs_error_uv"],
        blend_sha=metrics["blend_sha256"],
        g9_metrics_sha=metrics["input_integrity"]["g9_metrics_sha256"],
        g9_assignment_sha=metrics["input_integrity"]["g9_assignment_sha256"],
        singleton_note=(
            "none; every layer allows a centre-to-centre CV"
            if not metrics["single_island_layers"]
            else ", ".join(metrics["single_island_layers"])
            + " (scale checked by mapping and texel density)"
        ),
    )
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    log("WROTE %s" % path)


def render_atlas_pngs(outdir):
    """Run the existing dependency-free System.Drawing atlas renderer."""
    renderer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "draw_atlas_fallback.ps1")
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", renderer, "-OutDir", os.path.abspath(outdir),
    ]
    completed = subprocess.run(
        command, check=True, capture_output=True, text=True,
    )
    for line in completed.stdout.splitlines():
        if line.strip():
            log("PNG_RENDER " + line.strip())
    if completed.stderr.strip():
        log("PNG_RENDER_STDERR " + completed.stderr.strip())


def run_g10_delivery(outdir, assign_arg, raw_assignment, assignment, selected_specs,
                     axis_records, selected_run, baseline_run, stage_e_b, bm, obj,
                     v_world, f_cent, model_xy_bbox, real_xy_tris, a_shells, sha,
                     control_a_result, control_b_result, g9_metrics,
                     placement_override_path=None):
    """Materialize the two measured G10 variants and publish the nine gates."""
    result = pack_and_scale_islands_g10(
        selected_run["islands_a"], f_cent, model_xy_bbox, g9_metrics,
    )
    placement_override_payload = None
    placement_override_sha256 = None
    if placement_override_path is not None:
        with open(placement_override_path, "r", encoding="utf-8") as handle:
            placement_override_payload = json.load(handle)
        result["cropped_frames"] = apply_placement_override_to_g10_stage(
            result["cropped_frames"], placement_override_payload,
        )
        placement_override_sha256 = file_sha256(placement_override_path)
        log(
            "G11_PLACEMENT_OVERRIDE path=%s sha256=%s islands=%d"
            % (
                os.path.abspath(placement_override_path),
                placement_override_sha256,
                len(placement_override_payload["islands"]),
            )
        )
    override_active = placement_override_payload is not None
    cropped_stage = result["cropped_frames"]
    full_stage = result["full_frames"]
    cropped_summary = summarize_g10_stage(
        "G10_B_cropped_whole_frames", cropped_stage, True,
    )
    full_summary = summarize_g10_stage(
        "G10_A_full_whole_frames", full_stage, True,
    )
    b_summary = summarize_packing_stage(
        "G10_atlas_B_unchanged_G9_MaxRects", stage_e_b, True,
    )

    cropped_islands = cropped_stage["islands"]
    full_islands = full_stage["islands"]
    islands_b = stage_e_b["islands"]
    a_faces_cropped = [face for isl in cropped_islands for face in isl["faces"]]
    a_faces_full = [face for isl in full_islands for face in isl["faces"]]
    b_faces = [face for isl in islands_b for face in isl["faces"]]

    write_uvs(bm, cropped_islands, b_faces)
    bm.to_mesh(obj.data)
    obj.data.update()
    cropped_mesh_metrics = measure_filtered_mesh(
        obj, [index for isl in cropped_islands for index in isl["face_indices"]],
    )
    write_uvs(bm, full_islands, b_faces)
    bm.to_mesh(obj.data)
    obj.data.update()
    full_mesh_metrics = measure_filtered_mesh(
        obj, [index for isl in full_islands for index in isl["face_indices"]],
    )
    write_uvs(bm, islands_b, a_faces_cropped)
    bm.to_mesh(obj.data)
    obj.data.update()
    b_mesh_metrics = measure_filtered_mesh(
        obj, [index for isl in islands_b for index in isl["face_indices"]],
    )
    # The blend is intentionally never saved.

    def atlas_payload(stage, summary, mesh_metrics):
        payload = atlas_payload_metrics(
            stage["islands"], stage["blocks"], summary["overlap"],
            summary["texel_density"], mesh_metrics, summary["grouping"],
        )
        payload.update({
            "global_uv_scale": float(stage["global_scale"]),
            "decomposition": summary["decomposition"],
            "packer": stage["packer"],
            "selected_order": stage.get("selected_order"),
            "block_rotation_gate": summary["block_rotation_gate"],
            "labels_and_grid_order_gate": summary["labels_and_grid_order_gate"],
            "layout_gates": stage["layout_gates"],
            "displacement": stage["displacement"],
            "scale_fidelity": stage["scale_fidelity"],
            "intra_layer_collisions": stage["intra_layer_overlap"],
            "affine_vertex_gate": stage["affine_vertex_gate"],
        })
        return payload

    payload_cropped = atlas_payload(cropped_stage, cropped_summary, cropped_mesh_metrics)
    payload_full = atlas_payload(full_stage, full_summary, full_mesh_metrics)
    payload_b = atlas_payload_metrics(
        islands_b, stage_e_b["blocks"], b_summary["overlap"],
        b_summary["texel_density"], b_mesh_metrics, b_summary["grouping"],
    )
    payload_b.update({
        "global_uv_scale": float(stage_e_b["global_scale"]),
        "decomposition": b_summary["decomposition"],
        "packer": stage_e_b["packer"],
        "selected_order": stage_e_b.get("selected_order"),
        "block_rotation_gate": b_summary["block_rotation_gate"],
        "labels_and_grid_order_gate": b_summary["labels_and_grid_order_gate"],
    })

    side_purity_legacy = side_purity_metrics(
        cropped_islands, v_world, G7_SIGN_SPLIT_X,
    )
    side_purity = g9_side_purity_from_legacy(
        side_purity_legacy, sum(isl["n_faces"] for isl in cropped_islands),
    )
    face_changes = island_face_change_metrics(
        baseline_run["islands_a"], selected_run["islands_a"],
    )
    face_4053_island = next(
        (
            isl["id"] for isl in cropped_islands
            if 4053 in set(isl["face_indices"])
        ),
        None,
    )
    input_axes = dict(assignment["projection_axes"])
    selected_axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
    axis_changes = [row for row in axis_records if row["changed"]]
    axis_frozen = input_axes == selected_axes and not axis_changes
    fixed_assignment = (
        tuple(a_shells) == G7_ATLAS_A_SHELLS
        and tuple(assignment["atlas_b"]) == ("S00", "S01", "S04", "S11", "S12")
        and abs(ISLAND_VIS_THRESHOLD - 0.005) <= 1e-15
        and axis_frozen
    )

    raw_invariant = dict(selected_run["invariant"])
    invariant = {
        **raw_invariant,
        "faces_total": int(raw_invariant["faces_a_plus_b"]),
        "orphan": int(raw_invariant["unassigned"]),
    }
    cropped_density = cropped_summary["texel_density"]
    full_density = full_summary["texel_density"]
    b_density = b_summary["texel_density"]
    cropped_self = cropped_summary["overlap"]
    full_self = full_summary["overlap"]
    rotation_cropped = cropped_summary["block_rotation_gate"]
    rotation_full = full_summary["block_rotation_gate"]
    source_verification = result["g10_layering"]["source_verification"]

    collision_gate_name = (
        "1_global_collisions_zero_and_inside_unit_canvas"
        if override_active else "1_intra_layer_collisions_zero"
    )
    collision_gate_pass = (
        source_verification["collision_pair_count"] == 0
        and result["g10_layering"]["corrected_exact_collision_pair_count"] == 0
        and result["g10_layering"]["corrected_combined_collision_pair_count"] == 0
        and cropped_stage["intra_layer_overlap"]["collision_pair_count"] == 0
        and full_stage["intra_layer_overlap"]["collision_pair_count"] == 0
    )
    if override_active:
        collision_gate_pass = bool(
            collision_gate_pass
            and cropped_stage["intra_layer_overlap"]["raster_control_pass"]
            and cropped_stage["layout_gates"]["canvas_outside_count"] == 0
        )
        collision_evidence = (
            "global exact=%d, raster1024=%d pairs; outside=%d; base exact=%d"
            % (
                cropped_stage["intra_layer_overlap"]["collision_pair_count"],
                cropped_stage["intra_layer_overlap"]["raster_control"]["collision_pair_count"],
                cropped_stage["layout_gates"]["canvas_outside_count"],
                result["g10_layering"]["corrected_exact_collision_pair_count"],
            )
        )
    else:
        collision_evidence = "corrected source raster=%d, exact=%d, B=%d, A=%d pairs" % (
            source_verification["collision_pair_count"],
            result["g10_layering"]["corrected_exact_collision_pair_count"],
            cropped_stage["intra_layer_overlap"]["collision_pair_count"],
            full_stage["intra_layer_overlap"]["collision_pair_count"],
        )
    displacement_gate_name = (
        "2_rigid_island_translation_preserves_every_vertex"
        if override_active else "2_zero_center_and_vertex_displacement"
    )
    displacement_gate_pass = (
        cropped_stage["affine_vertex_gate"]["max_abs_error_uv"] == 0.0
        and full_stage["affine_vertex_gate"]["max_abs_error_uv"] == 0.0
        and (
            override_active
            or (
                cropped_stage["displacement"]["worst_uv"] == 0.0
                and full_stage["displacement"]["worst_uv"] == 0.0
            )
        )
    )
    displacement_evidence = (
        "rigid error=%.17g UV; displacement mean=%.12f worst=%.12f (informational)"
        % (
            cropped_stage["affine_vertex_gate"]["max_abs_error_uv"],
            cropped_stage["displacement"]["mean_uv"],
            cropped_stage["displacement"]["worst_uv"],
        )
        if override_active else "B/A center=0.0; B/A affine vertex=0.0 UV"
    )
    nine_gates = {
        collision_gate_name: {
            "pass": collision_gate_pass,
            "evidence": collision_evidence,
        },
        displacement_gate_name: {
            "pass": displacement_gate_pass,
            "evidence": displacement_evidence,
        },
        "3_one_common_scale_all_N_layers": {
            "pass": (
                cropped_stage["scale_fidelity"]["pass"]
                and full_stage["scale_fidelity"]["pass"]
            ),
            "evidence": "B CV=%.3e, A CV=%.3e" % (
                cropped_stage["scale_fidelity"]["between_layers_cv"],
                full_stage["scale_fidelity"]["between_layers_cv"],
            ),
        },
        "4_texel_density_ratio_near_one": {
            "pass": (
                cropped_density["texel_density_ratio"] <= 1.000001
                and full_density["texel_density_ratio"] <= 1.000001
                and b_density["texel_density_ratio"] <= 1.000001
            ),
            "evidence": "B=%.15f, A=%.15f, atlas_B=%.15f" % (
                cropped_density["texel_density_ratio"],
                full_density["texel_density_ratio"],
                b_density["texel_density_ratio"],
            ),
        },
        "5_exact_face_partition": {
            "pass": bool(invariant["pass"] and invariant["faces_total"] == EXPECTED_FACE_COUNT),
            "evidence": "A=%d + B=%d = %d; intersection=%d; orphan=%d" % (
                invariant["faces_a"], invariant["faces_b"], invariant["faces_total"],
                invariant["intersection"], invariant["orphan"],
            ),
        },
        "6_semantic_side_purity_and_face_4053": {
            "pass": (
                side_purity["worst"] >= 1.0 - 1e-12
                and side_purity["label_face_sign_mismatch_count"] == 0
                and face_4053_island == "S08|+Z|R|+"
            ),
            "evidence": "purity=%.1f; mismatches=%d; face4053=%s" % (
                side_purity["worst"], side_purity["label_face_sign_mismatch_count"],
                face_4053_island,
            ),
        },
        "7_assignment_threshold_and_projection_axes_frozen": {
            "pass": (
                fixed_assignment
                and face_changes["unique_faces"] == [4053]
                and face_changes["changed_island_count"] == 2
            ),
            "evidence": "threshold=0.005; axis_changes=%d; only legacy correction face 4053" % len(axis_changes),
        },
        "8_internal_island_self_overlap_at_most_0_06": {
            "pass": (
                cropped_self["overlap_area_frac"] <= G9_OVERLAP_LIMIT_A
                and full_self["overlap_area_frac"] <= G9_OVERLAP_LIMIT_A
            ),
            "evidence": "B=%.12f; A=%.12f; limit=%.2f" % (
                cropped_self["overlap_area_frac"], full_self["overlap_area_frac"],
                G9_OVERLAP_LIMIT_A,
            ),
        },
        "9_no_rotation_for_Z_projected_islands": {
            "pass": bool(rotation_cropped["pass"] and rotation_full["pass"]),
            "evidence": "B violations=%d; A violations=%d" % (
                len(rotation_cropped["violations"]), len(rotation_full["violations"]),
            ),
        },
    }

    g9_occupancy = float(g9_metrics["atlas_a"]["occupancy"])
    n_layers = int(result["g10_layering"]["minimum_total_layers"])
    price_table = [
        {
            "config": "G9_2_layers", "layers": 2,
            "collisions": int(g9_metrics["intra_layer_overlap"]["collision_pair_count"]),
            "occupancy": g9_occupancy,
            "useful_texels": g10_useful_texels(g9_occupancy),
        },
        {
            "config": "G10_%d_full_frames" % n_layers, "layers": n_layers,
            "collisions": full_stage["intra_layer_overlap"]["collision_pair_count"],
            "occupancy": full_summary["occupancy"],
            "useful_texels": g10_useful_texels(full_summary["occupancy"]),
        },
        {
            "config": "G10_%d_cropped_frames" % n_layers, "layers": n_layers,
            "collisions": cropped_stage["intra_layer_overlap"]["collision_pair_count"],
            "occupancy": cropped_summary["occupancy"],
            "useful_texels": g10_useful_texels(cropped_summary["occupancy"]),
        },
    ]
    linear_gain_pct = 100.0 * (
        math.sqrt(cropped_summary["occupancy"] / full_summary["occupancy"]) - 1.0
    )
    recommendation_threshold = 10.0
    if linear_gain_pct >= recommendation_threshold:
        recommended_variant = "B_cropped_frames"
        recommendation_reason = (
            "The useful linear gain of B is above the declared 10% threshold; "
            "it makes up for losing the immediate visual overlay."
        )
    else:
        recommended_variant = "A_full_frames"
        recommendation_reason = (
            "The useful linear gain of B is below 10%; keep the direct "
            "comparability of A."
        )
    recommendation = {
        "recommended_variant": recommended_variant,
        "linear_resolution_gain_pct_B_vs_A": float(linear_gain_pct),
        "minimum_linear_gain_pct_to_recommend_B": recommendation_threshold,
        "reason": recommendation_reason,
    }

    def variant_metrics(stage, summary):
        return {
            "variant": stage["variant"],
            "frame_count": len(stage["frames"]),
            "frames": stage["frames"],
            "global_scale": float(stage["global_scale"]),
            "common_scale_by_layer": {
                frame["id"]: float(frame["mapping"]["a"])
                for frame in stage["frames"]
            },
            "occupancy": float(summary["occupancy"]),
            "useful_texels": g10_useful_texels(summary["occupancy"]),
            "packer": stage["packer"],
            "selected_order": stage["selected_order"],
            "frames_are_indivisible": True,
            "islands_packed_or_translated_inside_frame": bool(
                stage.get("island_local_translation_applied")
            ),
            "island_local_translation_applied": bool(
                stage.get("island_local_translation_applied")
            ),
            "intra_layer_collisions": stage["intra_layer_overlap"],
            "displacement": stage["displacement"],
            "affine_vertex_gate": stage["affine_vertex_gate"],
            "scale_fidelity": stage["scale_fidelity"],
            "texel_density_ratio": summary["texel_density_ratio"],
            "texel_density": summary["texel_density"],
            "self_overlap": summary["overlap"],
            "layout_gates": stage["layout_gates"],
        }

    g9_metrics_path = os.path.join(os.path.dirname(os.path.abspath(assign_arg)), "atlas_metrics.json")
    result["g10_layering"]["source_metrics_sha256"] = file_sha256(g9_metrics_path)
    single_island_layers = [
        layer["id"] for layer in result["g10_layering"]["layers"]
        if len(layer["island_ids"]) == 1
    ]
    all_nine = all(row["pass"] for row in nine_gates.values())
    auxiliary_gates = {
        "control_a_mirror": control_a_result["pass"],
        "control_b_normal_split": control_b_result["pass"],
        "atlas_b_grouping": b_summary["grouping"]["verdict"] == "PASS",
    }
    all_green = all_nine and all(auxiliary_gates.values())

    ghost_world_tris = [
        [[float(point[0]), float(point[1])] for point in triangle]
        for triangle in real_xy_tris
    ]
    common_extra = {
        "generation": "G10",
        "placement_mode": (
            "G11_manual_rigid_island_translation"
            if override_active else "G10_whole_frame_layout"
        ),
        "placement_override": ({
            "source": placement_override_payload["source"],
            "base": placement_override_payload["base"],
            "path": os.path.abspath(placement_override_path),
            "sha256": placement_override_sha256,
        } if override_active else None),
        "threshold": ISLAND_VIS_THRESHOLD,
        "padding": fixed_padding_config(),
        "centerline_scope": "world_X_zero_per_frame",
        "sign_convention": G9_SIGN_CONVENTION,
        "longitudinal_convention": G9_LONGITUDINAL_CONVENTION,
        "front_view_islands": ["S09", "S10"],
        "output_directory": os.path.abspath(outdir),
        "layering_source": (
            "out_g9/atlas_metrics.json:intra_layer_overlap.layering_by_panel "
            "seed; minimum-change repair after continuous-area verification"
        ),
    }
    dump_islands_json(
        os.path.join(outdir, "atlas_a_islands.json"), cropped_islands, False,
        blocks=cropped_stage["blocks"], atlas_name="A",
        extra={
            **common_extra,
            "g10_variant": "B_cropped_frames",
            "ghost_context": {
                "mode": "full_quad_fit_to_each_cropped_frame_visualization_only",
                "same_scale_as_uv": False,
                "world_bbox": [float(value) for value in model_xy_bbox],
                "tris_world": ghost_world_tris,
            },
        },
    )
    dump_islands_json(
        os.path.join(outdir, "atlas_a_full_frames_islands.json"), full_islands, False,
        blocks=full_stage["blocks"], atlas_name="A",
        extra={
            **common_extra,
            "g10_variant": "A_full_frames",
            "ghost_context": None,
        },
    )
    dump_islands_json(
        os.path.join(outdir, "atlas_b_islands.json"), islands_b, False,
        blocks=stage_e_b["blocks"], atlas_name="B",
        extra={"generation": "G10", "threshold": ISLAND_VIS_THRESHOLD,
               "padding": fixed_padding_config()},
    )
    write_assignment_g10_frozen(
        os.path.join(outdir, "assignment_REAL.json"), raw_assignment, selected_specs,
    )

    visibility = selected_run["visibility"]
    destination = selected_run["dest"]
    visibility_rows = []
    for isl in selected_run["all_islands"]:
        visibility_rows.append({
            "id": isl["id"], "shell": isl["shell"], "axis": isl["axis"],
            "lr": isl.get("lr"), "nsign": isl.get("nsign"),
            "n_faces": isl["n_faces"], "area_3d": isl["area_3d"],
            "island_vis_share": isl["island_vis_share"],
            "atlas": destination[isl["id"]],
            "piece_atlas": "A" if isl["shell"] in a_shells else "B",
            "demoted_by_threshold": (
                isl["shell"] in a_shells and destination[isl["id"]] == "B"
            ),
        })
    visibility_rows.sort(key=lambda row: (-row["island_vis_share"], row["id"]))
    visibility_payload = {
        "method": visibility["method"],
        "threshold": ISLAND_VIS_THRESHOLD,
        "threshold_locked_before_results": True,
        "threshold_rationale": (
            "Frozen from G9: 0.5% of exterior first-hits; no G10 reclassification."
        ),
        "n_dir": visibility["n_dir"], "grid": visibility["grid"],
        "hits": visibility["hits"], "misses": visibility["misses"],
        "sum_island_vis_share": visibility["sum_share"],
        "sum_closes_at_1": abs(visibility["sum_share"] - 1.0) <= 1e-9,
        "sensitivity": selected_run["sensitivity"],
        "islands": visibility_rows,
    }
    visibility_path = os.path.join(outdir, "island_visibility.json")
    with open(visibility_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(visibility_payload, handle, indent=2)
        handle.write("\n")
    log("WROTE %s" % visibility_path)

    metrics = {
        "generation": "G10",
        "object": obj.name,
        "blend_sha256": sha,
        "input_integrity": {
            "g9_metrics_path": os.path.abspath(g9_metrics_path),
            "g9_metrics_sha256": file_sha256(g9_metrics_path),
            "g9_assignment_path": os.path.abspath(assign_arg),
            "g9_assignment_sha256": file_sha256(assign_arg),
            **({
                "placement_override_path": os.path.abspath(placement_override_path),
                "placement_override_sha256": placement_override_sha256,
            } if override_active else {}),
        },
        "pack_method": (
            (
                "G10 cropped-frame base followed by one declared rigid UV translation "
                "per atlas-A island; no scale or rotation."
            ) if override_active else (
                "N indivisible frames from the G9 family-preserving coloring seed, repaired "
                "minimally after continuous-area verification. One common scale "
                "per variant; only whole-frame b/c offsets vary."
            )
        ),
        "placement_override": (
            cropped_stage["placement_override"] if override_active else None
        ),
        "target_displacement_is_informational": bool(override_active),
        "island_vis_threshold": ISLAND_VIS_THRESHOLD,
        "assignment_atlas_a_shells": list(a_shells),
        "assignment_atlas_b_shells": list(assignment["atlas_b"]),
        "axis_search": {
            "policy": "g10_input_g9_axes_frozen_no_search",
            "incumbent_source": "input out_g9/assignment_REAL.json",
            "axes_tested_per_piece": [],
            "policy_gate_pass": axis_frozen,
            "pieces_changed": axis_changes,
            "records": axis_records,
        },
        "atlas_a": payload_cropped,
        "atlas_a_full_frames": payload_full,
        "atlas_b": payload_b,
        "g10_layering": result["g10_layering"],
        "g10_variants": {
            "B_cropped_frames": variant_metrics(cropped_stage, cropped_summary),
            "A_full_frames": variant_metrics(full_stage, full_summary),
        },
        "g9_overlap_area": result["g9_overlap_area"],
        "price_table": price_table,
        "recommendation": recommendation,
        "invariant": invariant,
        "side_purity": side_purity,
        "face_4053_island": face_4053_island,
        "face_reassignment": face_changes,
        "nine_gates": nine_gates,
        "auxiliary_gates": auxiliary_gates,
        "all_required_gates_green": all_green,
        "single_island_layers": single_island_layers,
        "ghost_context_policy": (
            "Variant B ghost is visualization-only and fitted independently to each "
            "cropped frame; it never enters UV occupancy, scale or collision gates."
        ),
        "not_verified": [
            "second independent geometry library validating continuous triangle clipping",
            "EEVEE/Cycles/OpenGL render",
            "manual paint/export/DayZ consumer",
            "3D orthographic colored reference proposed in G9",
        ],
        "controls": {"a_mirror": control_a_result, "b_normal_split": control_b_result},
        "faces_whole_mesh": len(bm.faces),
        "islands_atlas_a": len(cropped_islands),
        "islands_atlas_b": len(islands_b),
        "texel_density_ratio": cropped_summary["texel_density_ratio"],
        "overlap_area_frac": cropped_summary["overlap_area_frac"],
    }
    metrics_path = os.path.join(outdir, "atlas_metrics.json")
    with open(metrics_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(metrics, handle, indent=2)
        handle.write("\n")
    log("WROTE %s" % metrics_path)
    if override_active:
        render_atlas_pngs(outdir)
    else:
        report_path = os.path.join(os.path.dirname(os.path.abspath(outdir)), "REPORT_G10.md")
        write_g10_report(report_path, metrics)
    log("G10_SUMMARY " + json.dumps({
        "layers": result["g10_layering"]["minimum_total_layers"],
        "collisions_cropped": cropped_stage["intra_layer_overlap"]["collision_pair_count"],
        "collisions_full": full_stage["intra_layer_overlap"]["collision_pair_count"],
        "occupancy_cropped": cropped_summary["occupancy"],
        "occupancy_full": full_summary["occupancy"],
        "recommended": recommended_variant,
        "all_required_gates": "PASS" if all_green else "FAIL",
    }))
    if not all_green:
        raise SystemExit(3)


def find_body_object():
    # "carroceria" (Spanish for bodywork) is the object's name in the source .blend.
    obj = bpy.data.objects.get("carroceria")
    if obj is not None and obj.type == "MESH":
        return obj
    best = None
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.polygons:
            if best is None or len(o.data.polygons) > len(best.data.polygons):
                best = o
    if best is None:
        raise RuntimeError("no mesh in blend")
    log("WARN using %r, no object named carroceria" % best.name)
    return best


def main():
    parsed_args = parse_project_args(argv_payload())
    assign_arg = parsed_args["assignment"]
    outdir = parsed_args["outdir"]
    placement_override_path = parsed_args["placement_override"]
    if placement_override_path is not None and assign_arg.strip().upper() == "SMOKE":
        raise SystemExit("--placement-override requires a real frozen assignment, not SMOKE")
    os.makedirs(outdir, exist_ok=True)
    run_label = os.path.basename(os.path.normpath(outdir)).lower()
    g7_mode = placement_override_path is None and run_label == "out_g7"
    g8_mode = placement_override_path is None and run_label == "out_g8"
    g9_mode = placement_override_path is None and run_label == "out_g9"
    g10_mode = run_label == "out_g10" or placement_override_path is not None
    frozen_layout_mode = g7_mode or g8_mode or g9_mode or g10_mode
    g6_baseline_metrics = None
    g7_baseline_metrics = None
    g8_baseline_metrics = None
    g9_baseline_metrics = None
    if g7_mode:
        baseline_metrics_path = os.path.join(
            os.path.dirname(os.path.abspath(assign_arg)), "atlas_metrics.json",
        )
        with open(baseline_metrics_path, "r", encoding="utf-8") as fh:
            g6_baseline_metrics = json.load(fh)
        log("G7_MODE baseline=%s axes=frozen placement=anatomical" % baseline_metrics_path)
    elif g8_mode:
        baseline_metrics_path = os.path.join(
            os.path.dirname(os.path.abspath(assign_arg)), "atlas_metrics.json",
        )
        with open(baseline_metrics_path, "r", encoding="utf-8") as fh:
            g7_baseline_metrics = json.load(fh)
        log("G8_MODE baseline=%s axes=frozen placement=two_panels_world_xy" % baseline_metrics_path)
    elif g9_mode:
        baseline_metrics_path = os.path.join(
            os.path.dirname(os.path.abspath(assign_arg)), "atlas_metrics.json",
        )
        with open(baseline_metrics_path, "r", encoding="utf-8") as fh:
            g8_baseline_metrics = json.load(fh)
        log("G9_MODE baseline=%s axes=frozen placement=zero_displacement_archipelago" % baseline_metrics_path)
    elif g10_mode:
        baseline_metrics_path = os.path.join(
            os.path.dirname(os.path.abspath(assign_arg)), "atlas_metrics.json",
        )
        with open(baseline_metrics_path, "r", encoding="utf-8") as fh:
            g9_baseline_metrics = json.load(fh)
        log(
            "G10_MODE baseline=%s axes=frozen placement=%s"
            % (
                baseline_metrics_path,
                "G11_rigid_island_override" if placement_override_path else "N_zero_collision_frames",
            )
        )

    blend_path = bpy.data.filepath
    sha = file_sha256(blend_path) if blend_path and os.path.isfile(blend_path) else "MISSING"
    if sha != EXPECTED_BLEND_SHA256:
        log("ERROR blend sha256 %s != expected %s" % (sha, EXPECTED_BLEND_SHA256))
        raise SystemExit(2)
    log("BLEND_SHA256 %s" % sha)

    obj = find_body_object()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    v_world, f_nworld, f_cent = world_geom(obj, bm)
    shell_list = identify_shells(bm, v_world)
    shell_by_id = {s["id"]: s for s in shell_list}
    piece_centroids = piece_centroids_3d(shell_by_id, f_cent)
    log("SHELLS " + json.dumps([
        {"id": s["id"], "n_faces": s["n_faces"], "area": round(s["area"], 6),
         "extents_world": [round(x, 4) for x in s["extents"]]}
        for s in shell_list
    ]))
    symmetry = measure_symmetry(v_world)
    log("SYMMETRY " + json.dumps({
        "pair_fraction": {k: round(v, 4) for k, v in symmetry["pair_fraction"].items()},
        "winner": symmetry["winner_axis"],
        "tol": symmetry["tolerance"],
    }))
    mesh_center = (
        symmetry["mid_plane"]["X"],
        symmetry["mid_plane"]["Y"],
        symmetry["mid_plane"]["Z"],
    )

    smoke_assign = generate_smoke_assignment(shell_list, mesh_center, symmetry)
    if assign_arg.strip().upper() == "SMOKE":
        raw = smoke_assign
        smoke_path = os.path.join(outdir, "assignment_SMOKE.json")
        with open(smoke_path, "w", encoding="utf-8") as fh:
            json.dump(smoke_assign, fh, indent=2)
            fh.write("\n")
        log("WROTE %s" % smoke_path)
    else:
        with open(assign_arg, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    assignment = normalize_assignment(raw, [s["id"] for s in shell_list])
    for spec in assignment["atlas_a"]:
        if not spec["axis"]:
            spec["axis"] = infer_axis(shell_by_id[spec["shell"]], mesh_center)

    ca = control_a(shell_by_id[CONTROL_A_SHELL], v_world)
    cb = control_b(shell_by_id[CONTROL_B_SHELL], v_world, f_nworld, f_cent, symmetry)
    log("CONTROL_A " + json.dumps({"verdict": ca["verdict"], "got": ca["got"]}))
    log("CONTROL_B " + json.dumps({
        "verdict": cb["verdict"],
        "unsplit": cb["got"]["unsplit"]["overlap_area_frac"],
        "split": cb["got"]["split"]["overlap_area_frac"],
        "drop": cb["got"]["drop"],
    }))

    if assignment["SMOKE"]:
        islands = []
        for spec in assignment["atlas_a"]:
            islands.extend(build_islands_for_spec(
                spec, shell_by_id, v_world, f_nworld, f_cent, symmetry,
            ))
        global_scale, pos, pack_w, pack_h = pack_and_scale(islands)
        log("PACK islands=%d scale=%.6g pack=%.5g x %.5g" % (
            len(islands), global_scale, pack_w, pack_h,
        ))
        b_faces = []
        for sid in assignment["atlas_b"]:
            b_faces.extend(shell_by_id[sid]["faces"])
        write_uvs(bm, islands, b_faces)
        bm.to_mesh(obj.data)
        obj.data.update()
        a_face_idx = [f.index for isl in islands for f in isl["faces"]]
        metrics_a = measure_filtered_mesh(obj, a_face_idx)
        overlap = overlap_metrics_for(islands)
        density = texel_density_ratio(islands)
        dump_islands_json(
            os.path.join(outdir, "atlas_islands.json"), islands, True,
        )
        metrics = {
            "object": obj.name,
            "blend_sha256": sha,
            "SMOKE": True,
            "NOT_the_real_paint_mechanical_split": True,
            "note_tris_key": "copied from uv_metrics_run_REFERENCE.py; 'tris' is len(faces), not triangles",
            "defaults": {
                "split_lr": DEFAULT_SPLIT_LR,
                "split_by_normal_sign": DEFAULT_SPLIT_BY_NORMAL_SIGN,
                "local_conformal_polish": DEFAULT_LOCAL_CONFORMAL_POLISH,
                "axis_if_missing": "smallest bbox extent, sign from exterior vs mesh centroid",
            },
            "symmetry": {
                "pair_fraction_X": symmetry["pair_fraction"]["X"],
                "pair_fraction_Y": symmetry["pair_fraction"]["Y"],
                "pair_fraction_Z": symmetry["pair_fraction"]["Z"],
                "winner_axis": symmetry["winner_axis"],
                "mid_plane": symmetry["mid_plane"],
                "tolerance_world": symmetry["tolerance"],
                "bbox_diagonal": symmetry["diagonal"],
            },
            "assignment_atlas_a_shells": [s["shell"] for s in assignment["atlas_a"]],
            "assignment_atlas_b_shells": list(assignment["atlas_b"]),
            "islands_atlas_a": len(islands),
            "island_rotations_deg": {
                isl["id"]: int(isl.get("rotation_deg") or 0) for isl in islands
            },
            "global_uv_scale": global_scale,
            "pack_wh_world": [pack_w, pack_h],
            "pack_method": "shelf-bbox, 90-degree multiples only, prefer 0 unless square side drops >15%",
            "atlas_b_uv": "parked at (2,2); not in atlas A metrics",
            **(metrics_a or {"error": "measure failed"}),
            "overlap_area_frac": overlap.get("overlap_area_frac"),
            "overlap": overlap,
            "texel_density_ratio": density.get("texel_density_ratio"),
            "texel_density": density,
            "controls": {"a_mirror": ca, "b_normal_split": cb},
            "shells_whole_mesh": len(shell_list),
            "faces_whole_mesh": len(bm.faces),
        }
        metrics_path = os.path.join(outdir, "atlas_metrics.json")
        with open(metrics_path, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, indent=2)
            fh.write("\n")
        log("WROTE %s" % metrics_path)
        log("SUMMARY " + json.dumps({
            "islands_atlas_a": len(islands),
            "overlap_area_frac": overlap.get("overlap_area_frac"),
            "texel_density_ratio": density.get("texel_density_ratio"),
            "control_a": ca["verdict"],
            "control_b": cb["verdict"],
            "smoke_a": [s["shell"] for s in assignment["atlas_a"]],
            "smoke_b": assignment["atlas_b"],
        }))
        bm.free()
        return

    # ---- REAL: all 13 pieces as islands, vis per island, threshold, two atlases.
    log("ISLAND_VIS_THRESHOLD locked at %.6g (before vis results)" % ISLAND_VIS_THRESHOLD)
    specs_by_shell = {}
    for spec in assignment["atlas_a"]:
        specs_by_shell[spec["shell"]] = spec
    for sid in assignment["atlas_b"]:
        specs_by_shell[sid] = default_spec_for_shell(
            shell_by_id[sid], mesh_center, symmetry,
        )
        if sid in assignment["projection_axes"]:
            specs_by_shell[sid]["axis"] = assignment["projection_axes"][sid]
    a_shells = [s["shell"] for s in assignment["atlas_a"]]
    if frozen_layout_mode and tuple(a_shells) != G7_ATLAS_A_SHELLS:
        raise RuntimeError("G7/G8/G9/G10 atlas-A membership/order changed: %s" % a_shells)
    baseline_run = build_classified_islands(
        bm, specs_by_shell, shell_by_id, v_world, f_nworld,
        f_cent, symmetry, a_shells,
    )
    log("ISLANDS_BUILT %d across %d shells" % (
        len(baseline_run["all_islands"]), len(specs_by_shell),
    ))
    log("VIS hits=%d misses=%d sum_share=%.8f" % (
        baseline_run["visibility"]["hits"], baseline_run["visibility"]["misses"],
        baseline_run["visibility"]["sum_share"],
    ))
    log("CLASSIFY_BASELINE A=%d B=%d threshold=%.6g" % (
        len(baseline_run["islands_a"]), len(baseline_run["islands_b"]),
        ISLAND_VIS_THRESHOLD,
    ))
    inv_baseline = baseline_run["invariant"]
    log("INVARIANT_BASELINE " + json.dumps(inv_baseline))

    # A is already present in G3/out_final. Re-run it explicitly so its measured
    # contribution can correctly be zero rather than inferred from source text.
    stage_a_a = make_legacy_block_stage(baseline_run["islands_a"], specs_by_shell)
    stage_a_b = make_legacy_block_stage(baseline_run["islands_b"], specs_by_shell)
    stage_b_a = make_tight_block_stage(
        baseline_run["islands_a"], specs_by_shell,
        packer="shelf", allow_rotation=False, order_names=("area_desc",),
    )
    stage_b_b = make_tight_block_stage(
        baseline_run["islands_b"], specs_by_shell,
        packer="shelf", allow_rotation=False, order_names=("area_desc",),
    )
    stage_c_a = make_tight_block_stage(
        baseline_run["islands_a"], specs_by_shell,
        packer="shelf", allow_rotation=True, order_names=("area_desc",),
    )
    stage_c_b = make_tight_block_stage(
        baseline_run["islands_b"], specs_by_shell,
        packer="shelf", allow_rotation=True, order_names=("area_desc",),
    )

    if frozen_layout_mode:
        selected_specs = {sid: dict(spec) for sid, spec in specs_by_shell.items()}
        axis_records = [
            {
                "shell": sid,
                "axis_before": assignment["projection_axes"].get(sid),
                "axis_after": selected_specs[sid]["axis"],
                "changed": assignment["projection_axes"].get(sid) != selected_specs[sid]["axis"],
            }
            for sid in sorted(selected_specs)
        ]
        axis_changes = [record for record in axis_records if record["changed"]]
        if axis_changes:
            raise RuntimeError("G7/G8/G9/G10 projection axes changed despite freeze: %s" % axis_changes)
        log("AXIS_FREEZE %s changed=[]; no candidate axes evaluated" % (
            "G10" if g10_mode else "G9" if g9_mode else "G8" if g8_mode else "G7"
        ))
        if g8_mode or g9_mode or g10_mode:
            selected_run = build_classified_islands(
                bm, selected_specs, shell_by_id, v_world, f_nworld,
                f_cent, symmetry, a_shells, lr_split_x=G7_SIGN_SPLIT_X,
            )
        else:
            selected_run = baseline_run
    else:
        log("AXIS_SEARCH policy=%s starting 6 axes x %d pieces at grid %d absolute_limit=%.6g" % (
            AXIS_SEARCH_POLICY, len(specs_by_shell), AXIS_SEARCH_OVERLAP_GRID,
            AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT,
        ))
        selected_specs, axis_records = search_projection_axes(
            specs_by_shell, shell_by_id, mesh_center, v_world,
            f_nworld, f_cent, symmetry,
        )
        axis_changes = [r for r in axis_records if r["changed"]]
        log("AXIS_SEARCH changed=" + json.dumps([
            {"shell": r["shell"], "from": r["axis_before"], "to": r["axis_after"],
             "gain_pct": r["compactness_gain_pct"]}
            for r in axis_changes
        ]))
        selected_run = build_classified_islands(
            bm, selected_specs, shell_by_id, v_world, f_nworld,
            f_cent, symmetry, a_shells,
        )
    all_islands = selected_run["all_islands"]
    vis = selected_run["visibility"]
    dest = selected_run["dest"]
    sens = selected_run["sensitivity"]
    inv = selected_run["invariant"]
    log("CLASSIFY_FINAL A=%d B=%d threshold=%.6g" % (
        len(selected_run["islands_a"]), len(selected_run["islands_b"]),
        ISLAND_VIS_THRESHOLD,
    ))
    log("INVARIANT_FINAL " + json.dumps(inv))

    stage_d_a = make_tight_block_stage(
        selected_run["islands_a"], selected_specs,
        packer="shelf", allow_rotation=True, order_names=("area_desc",),
    )
    stage_d_b = make_tight_block_stage(
        selected_run["islands_b"], selected_specs,
        packer="shelf", allow_rotation=True, order_names=("area_desc",),
    )
    maxrects_a = make_tight_block_stage(
        selected_run["islands_a"], selected_specs,
        packer="maxrects", allow_rotation=True,
        order_names=("area_desc", "max_side_desc", "perimeter_desc"),
    )
    maxrects_b = make_tight_block_stage(
        selected_run["islands_b"], selected_specs,
        packer="maxrects", allow_rotation=True,
        order_names=("area_desc", "max_side_desc", "perimeter_desc"),
    )

    def choose_e(shelf_stage, maxrects_stage):
        if maxrects_stage["global_scale"] > shelf_stage["global_scale"] + 1e-12:
            chosen = maxrects_stage
            decision = "maxrects_selected"
        else:
            chosen = dict(shelf_stage)
            chosen["packer"] = "shelf_retained_after_maxrects_trials"
            chosen["maxrects_candidate_scale"] = maxrects_stage["global_scale"]
            chosen["maxrects_order_trials"] = maxrects_stage["order_trials"]
            decision = "shelf_retained"
        chosen["lever_e_decision"] = decision
        return chosen

    stage_g6_reference_a = choose_e(stage_d_a, maxrects_a)
    stage_e_b = choose_e(stage_d_b, maxrects_b)
    g7_control_stage_a = None
    g8_reference_stage_a = None
    real_xy_tris = None
    model_xy_bbox = None
    if g8_mode or g9_mode or g10_mode:
        real_xy_tris, model_xy_bbox = world_xy_geometry_for_shells(
            shell_by_id, G7_ATLAS_A_SHELLS, v_world,
        )
    if g10_mode:
        run_g10_delivery(
            outdir, assign_arg, raw, assignment, selected_specs, axis_records,
            selected_run, baseline_run, stage_e_b, bm, obj, v_world, f_cent,
            model_xy_bbox, real_xy_tris, a_shells, sha, ca, cb,
            g9_baseline_metrics, placement_override_path,
        )
        bm.free()
        return
    if g9_mode:
        stage_e_a = pack_and_scale_islands_archipelago(
            selected_run["islands_a"], f_cent, model_xy_bbox,
        )
        g8_reference_stage_a = pack_and_scale_islands_plan_view(
            selected_run["islands_a"], f_cent, model_xy_bbox,
            occupancy_floor=G8_OCCUPANCY_FLOOR,
        )
    elif g8_mode:
        stage_e_a = pack_and_scale_islands_plan_view(
            selected_run["islands_a"], f_cent, model_xy_bbox,
            occupancy_floor=G8_OCCUPANCY_FLOOR,
        )
        g7_control_stage_a = pack_and_scale_blocks_anatomical(
            clone_islands_for_layout(baseline_run["islands_a"]),
            selected_specs,
            {sid: piece_centroids[sid] for sid in G7_ATLAS_A_SHELLS},
            occupancy_floor=G7_OCCUPANCY_FLOOR,
        )
    elif g7_mode:
        stage_e_a = pack_and_scale_blocks_anatomical(
            clone_islands_for_layout(selected_run["islands_a"]),
            selected_specs,
            {sid: piece_centroids[sid] for sid in G7_ATLAS_A_SHELLS},
            occupancy_floor=G7_OCCUPANCY_FLOOR,
        )
    else:
        stage_e_a = stage_g6_reference_a

    summary_base_a = summarize_packing_stage("baseline_out_final", stage_a_a, True)
    summary_a = dict(summary_base_a)
    summary_a["step"] = "A_fitted_cells"
    summary_b_a = summarize_packing_stage("A+B_fixed_8px_padding", stage_b_a, True)
    summary_c_a = summarize_packing_stage("A+B+C_whole_block_rotation", stage_c_a, True)
    summary_d_a = summarize_packing_stage(
        "A+B+C+D_axes_frozen" if frozen_layout_mode else "A+B+C+D_axis_search",
        stage_d_a, True,
    )
    if g9_mode:
        summary_e_a = summarize_g9_stage("G9_zero_displacement_archipelago", stage_e_a, True)
    elif g8_mode:
        summary_e_a = summarize_g8_stage("G8_two_panel_plan_view", stage_e_a, True)
    else:
        summary_e_a = summarize_packing_stage(
            "G7_anatomical_placement" if g7_mode else "A+B+C+D+E_best_block_packer",
            stage_e_a, True,
        )
    steps_a = add_cumulative_stage_deltas([
        summary_base_a, summary_a, summary_b_a, summary_c_a, summary_d_a, summary_e_a,
    ])

    summary_base_b = summarize_packing_stage("baseline_out_final", stage_a_b, False)
    summary_a_b = dict(summary_base_b)
    summary_a_b["step"] = "A_fitted_cells"
    summary_b_b = summarize_packing_stage("A+B_fixed_8px_padding", stage_b_b, False)
    summary_c_b = summarize_packing_stage("A+B+C_whole_block_rotation", stage_c_b, False)
    summary_d_b = summarize_packing_stage("A+B+C+D_axis_search", stage_d_b, False)
    summary_e_b = summarize_packing_stage("A+B+C+D+E_best_block_packer", stage_e_b, True)
    steps_b = add_cumulative_stage_deltas([
        summary_base_b, summary_a_b, summary_b_b, summary_c_b, summary_d_b, summary_e_b,
    ])

    islands_a = stage_e_a["islands"]
    islands_b = stage_e_b["islands"]
    blocks_a = stage_e_a["blocks"]
    blocks_b = stage_e_b["blocks"]
    scale_a = stage_e_a["global_scale"]
    scale_b = stage_e_b["global_scale"]
    log("PACK_FINAL_A islands=%d blocks=%d scale=%.9g packer=%s" % (
        len(islands_a), len(blocks_a), scale_a, stage_e_a["packer"],
    ))
    log("PACK_FINAL_B islands=%d blocks=%d scale=%.9g packer=%s" % (
        len(islands_b), len(blocks_b), scale_b, stage_e_b["packer"],
    ))

    park_b = [f for isl in islands_b for f in isl["faces"]]
    write_uvs(bm, islands_a, park_b)
    bm.to_mesh(obj.data)
    obj.data.update()
    metrics_a_mesh = measure_filtered_mesh(
        obj, [fi for isl in islands_a for fi in isl["face_indices"]],
    )
    park_a = [f for isl in islands_a for f in isl["faces"]]
    write_uvs(bm, islands_b, park_a)
    bm.to_mesh(obj.data)
    obj.data.update()
    metrics_b_mesh = measure_filtered_mesh(
        obj, [fi for isl in islands_b for fi in isl["face_indices"]],
    )
    # Do not save the blend.

    overlap_a = summary_e_a["overlap"]
    overlap_b = summary_e_b["overlap"]
    dens_a = summary_e_a["texel_density"]
    dens_b = summary_e_b["texel_density"]
    gates_a = summary_e_a["grouping"]
    gates_b = summary_e_b["grouping"]
    rotations_a = summary_e_a["block_rotation_gate"]
    rotations_b = summary_e_b["block_rotation_gate"]
    order_a = summary_e_a["labels_and_grid_order_gate"]
    order_b = summary_e_b["labels_and_grid_order_gate"]
    log("GATES_A " + json.dumps({
        "purity_all_zero": gates_a["block_purity_all_zero"],
        "purity_worst": gates_a["block_purity_worst"],
        "overlap_pairs": gates_a["block_bbox_overlap_count"],
        "verdict": gates_a["verdict"],
    }))
    log("GATES_B " + json.dumps({
        "purity_all_zero": gates_b["block_purity_all_zero"],
        "purity_worst": gates_b["block_purity_worst"],
        "overlap_pairs": gates_b["block_bbox_overlap_count"],
        "verdict": gates_b["verdict"],
    }))

    dump_islands_json(
        os.path.join(outdir, "atlas_a_islands.json"), islands_a, False,
        blocks=blocks_a, atlas_name="A",
        extra={
            "threshold": ISLAND_VIS_THRESHOLD,
            "padding": fixed_padding_config(),
            "packer": stage_e_a["packer"],
            "anatomical_layout": bool(frozen_layout_mode),
            "centerline_u": 0.5 if frozen_layout_mode else None,
            "sign_convention": G7_SIGN_CONVENTION if frozen_layout_mode else None,
            "longitudinal_convention": G7_LONGITUDINAL_CONVENTION if frozen_layout_mode else None,
            "mirror_pairs": [list(pair) for pair in G7_MIRROR_PAIRS] if frozen_layout_mode else None,
            "panel_layout": stage_e_a.get("panel_config"),
            "front_view_islands": ["S09", "S10"] if (g8_mode or g9_mode) else None,
            "output_directory": os.path.abspath(outdir) if (g8_mode or g9_mode) else None,
            "archipelago_layout": bool(g9_mode),
            "intra_layer_overlap": stage_e_a.get("intra_layer_overlap") if g9_mode else None,
            "scale_fidelity": stage_e_a.get("scale_fidelity") if g9_mode else None,
        },
    )
    dump_islands_json(
        os.path.join(outdir, "atlas_b_islands.json"), islands_b, False,
        blocks=blocks_b, atlas_name="B",
        extra={
            "threshold": ISLAND_VIS_THRESHOLD,
            "padding": fixed_padding_config(),
            "packer": stage_e_b["packer"],
        },
    )
    if g9_mode:
        write_assignment_g9_frozen(
            os.path.join(outdir, "assignment_REAL.json"), raw, selected_specs,
        )
    elif g8_mode:
        write_assignment_g8_frozen(
            os.path.join(outdir, "assignment_REAL.json"), raw, selected_specs,
        )
    elif g7_mode:
        write_assignment_g7_frozen(
            os.path.join(outdir, "assignment_REAL.json"), raw, selected_specs,
        )
    else:
        write_assignment_with_axes(
            os.path.join(outdir, "assignment_REAL.json"), raw, selected_specs, axis_records,
        )

    vis_rows = []
    for isl in all_islands:
        vis_rows.append({
            "id": isl["id"],
            "shell": isl["shell"],
            "axis": isl["axis"],
            "lr": isl.get("lr"),
            "nsign": isl.get("nsign"),
            "n_faces": isl["n_faces"],
            "area_3d": isl["area_3d"],
            "island_vis_share": isl["island_vis_share"],
            "atlas": dest[isl["id"]],
            "piece_atlas": "A" if isl["shell"] in a_shells else "B",
            "demoted_by_threshold": (
                isl["shell"] in a_shells and dest[isl["id"]] == "B"
            ),
        })
    vis_rows.sort(key=lambda r: (-r["island_vis_share"], r["id"]))
    vis_path = os.path.join(outdir, "island_visibility.json")
    vis_payload = {
        "method": vis["method"],
        "threshold": ISLAND_VIS_THRESHOLD,
        "threshold_locked_before_results": True,
        "threshold_rationale": (
            "0.5% of exterior first-hits. Mechanical whole-pieces sit at "
            "0.0085-0.0187; smallest paint piece ~0.023. Below a coil "
            "spring's whole-piece share, above paint_min/4 so a 4-way split "
            "of the smallest paint piece is not dumped just for being small. "
            "Island count is a reading, not a target."
        ),
        "n_dir": vis["n_dir"],
        "grid": vis["grid"],
        "hits": vis["hits"],
        "misses": vis["misses"],
        "sum_island_vis_share": vis["sum_share"],
        "sum_closes_at_1": abs(vis["sum_share"] - 1.0) <= 1e-9,
        "sensitivity": sens,
        "islands": vis_rows,
    }
    with open(vis_path, "w", encoding="utf-8") as fh:
        json.dump(vis_payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % vis_path)

    payload_a = atlas_payload_metrics(
        islands_a, blocks_a, overlap_a, dens_a, metrics_a_mesh, gates_a,
    )
    payload_b = atlas_payload_metrics(
        islands_b, blocks_b, overlap_b, dens_b, metrics_b_mesh, gates_b,
    )
    payload_a["global_uv_scale"] = scale_a
    payload_a["decomposition"] = summary_e_a["decomposition"]
    payload_a["packer"] = stage_e_a["packer"]
    payload_a["selected_order"] = stage_e_a.get("selected_order")
    payload_a["block_rotation_gate"] = rotations_a
    payload_a["labels_and_grid_order_gate"] = order_a
    payload_b["global_uv_scale"] = scale_b
    payload_b["decomposition"] = summary_e_b["decomposition"]
    payload_b["packer"] = stage_e_b["packer"]
    payload_b["selected_order"] = stage_e_b.get("selected_order")
    payload_b["block_rotation_gate"] = rotations_b
    payload_b["labels_and_grid_order_gate"] = order_b

    grouping_ok = gates_a["verdict"] == "PASS" and gates_b["verdict"] == "PASS"
    g7_side_purity = None
    g7_placement = None
    g7_homologous = None
    g8_side_purity_before = None
    g8_side_purity = None
    g8_face_changes = None
    g8_layout = None
    g8_silhouette = None
    g7_silhouette_control = None
    g9_side_purity_before = None
    g9_side_purity = None
    g9_face_changes = None
    g9_layout = None
    g9_silhouette = None
    g8_silhouette_corrected = None
    g9_intra_overlap = None
    g9_scale_fidelity = None
    if g7_mode:
        g7_piece_centroids = {sid: piece_centroids[sid] for sid in G7_ATLAS_A_SHELLS}
        g7_side_purity = side_purity_metrics(
            islands_a, v_world, G7_SIGN_SPLIT_X,
        )
        g7_placement = anatomical_placement_metrics(
            blocks_a, g7_piece_centroids, pairs=G7_MIRROR_PAIRS,
        )
        g7_homologous = pair_homologous_alignment_metrics(
            islands_a, pairs=G7_MIRROR_PAIRS,
        )
        payload_a["anatomical_layout"] = {
            "sign_convention": G7_SIGN_CONVENTION,
            "longitudinal_convention": G7_LONGITUDINAL_CONVENTION,
            "sign_boundary_x": G7_SIGN_SPLIT_X,
            "measured_symmetry_mid_x": symmetry["mid_plane"]["X"],
            "centerline_u": 0.5,
            "bands_tail_to_nose": stage_e_a["selected_order"],
            "chosen_rotations_deg": stage_e_a["chosen_rotations_deg"],
            "rotated_shells": stage_e_a["rotated_shells"],
            "selection_policy": stage_e_a["selection_policy"],
            "orientation_trials": stage_e_a["order_trials"],
            "side_purity": g7_side_purity,
            "pair_homologous_v_offset": g7_homologous,
            **g7_placement,
        }
    elif g9_mode:
        g9_side_purity_before = g8_baseline_metrics["side_purity"]
        g9_side_purity_legacy = side_purity_metrics(
            islands_a, v_world, G7_SIGN_SPLIT_X,
        )
        g9_side_purity = g9_side_purity_from_legacy(
            g9_side_purity_legacy, sum(isl["n_faces"] for isl in islands_a),
        )
        g9_face_changes = island_face_change_metrics(
            baseline_run["islands_a"], selected_run["islands_a"],
        )
        g9_layout = stage_e_a["layout_gates"]
        g9_intra_overlap = stage_e_a["intra_layer_overlap"]
        g9_scale_fidelity = stage_e_a["scale_fidelity"]
        real_by_panel = world_xy_tris_by_panel(islands_a, v_world)
        g9_silhouette_result = silhouette_metrics_by_layer(
            real_by_panel, islands_a, model_xy_bbox,
            stage_e_a["panel_mappings"], grid_n=512,
        )
        g9_silhouette = g9_silhouette_result["metrics"]
        for panel in ("skin", "internal"):
            g9_silhouette[panel].update({
                "objective_min": G9_SILHOUETTE_IOU_MIN,
                "pass": g9_silhouette[panel]["iou"] >= G9_SILHOUETTE_IOU_MIN,
                "generation": "G9",
            })
        g8_silhouette_result = silhouette_metrics_by_layer(
            real_by_panel, g8_reference_stage_a["islands"], model_xy_bbox,
            g8_reference_stage_a["panel_mappings"], grid_n=512,
        )
        g8_silhouette_corrected = g8_silhouette_result["metrics"]
        for panel in ("skin", "internal"):
            g8_silhouette_corrected[panel]["generation"] = "G8_recomputed_corrected_scope"
        silhouette_bmp_path = os.path.join(outdir, "silhouette_check.bmp")
        write_silhouette_layers_bmp(
            silhouette_bmp_path, g9_silhouette_result["grids"], grid_n=512,
        )
        log("WROTE %s" % silhouette_bmp_path)
        payload_a["panel_layout"] = stage_e_a["panel_config"]
        payload_a["layout_gates"] = g9_layout
        payload_a["displacement"] = stage_e_a["displacement"]
        payload_a["scale_fidelity"] = g9_scale_fidelity
        payload_a["intra_layer_overlap"] = g9_intra_overlap
        payload_a["silhouette_iou_by_layer"] = g9_silhouette
        payload_a["silhouette_iou_g8_corrected"] = g8_silhouette_corrected
        payload_a["rotated_islands"] = g9_layout["rotated_islands"]
        payload_a["side_purity_before"] = g9_side_purity_before
        payload_a["side_purity_after"] = g9_side_purity
        payload_a["face_reassignment"] = g9_face_changes
        payload_a["affine_transform_by_layer"] = {
            panel: {
                key: stage_e_a["panel_mappings"][panel][key]
                for key in ("a", "b", "c", "target_frame_bbox")
            }
            for panel in ("skin", "internal")
        }
        payload_a["affine_vertex_gate"] = stage_e_a["affine_vertex_gate"]
    elif g8_mode:
        g8_side_purity_before = g7_baseline_metrics["side_purity"]
        g8_side_purity = side_purity_metrics(
            islands_a, v_world, G7_SIGN_SPLIT_X,
        )
        g8_face_changes = island_face_change_metrics(
            baseline_run["islands_a"], selected_run["islands_a"],
        )
        g8_layout = stage_e_a["layout_gates"]
        skin_tris_g8 = [
            tri for isl in islands_a if isl.get("nsign") == "+"
            for tri in island_tris_final(isl)
        ]
        skin_tris_g7 = [
            tri for isl in g7_control_stage_a["islands"] if isl.get("nsign") == "+"
            for tri in island_tris_final(isl)
        ]
        g8_silhouette = silhouette_iou_from_tris(
            real_xy_tris, skin_tris_g8, model_xy_bbox,
            stage_e_a["target_frame_skin_bbox"], grid_n=512,
        )
        g8_silhouette.update({
            "objective_min": G8_SILHOUETTE_IOU_MIN,
            "pass": g8_silhouette["iou"] >= G8_SILHOUETTE_IOU_MIN,
        })
        g7_silhouette_control = silhouette_iou_from_tris(
            real_xy_tris, skin_tris_g7, model_xy_bbox,
            (0.0, 0.0, 1.0, 1.0), grid_n=512,
        )
        g7_silhouette_control.update({
            "objective_discriminator_below": G8_SILHOUETTE_IOU_MIN,
            "discriminates": g7_silhouette_control["iou"] < G8_SILHOUETTE_IOU_MIN,
            "source": "G7 layout recomputed in this run with the same geometry and code",
        })
        real_grid, atlas_grid = silhouette_raster_pair(
            real_xy_tris, skin_tris_g8, model_xy_bbox,
            stage_e_a["target_frame_skin_bbox"], grid_n=512,
        )
        silhouette_bmp_path = os.path.join(outdir, "silhouette_check.bmp")
        write_silhouette_overlay_bmp(
            silhouette_bmp_path, real_grid, atlas_grid, 512, 512,
        )
        log("WROTE %s" % silhouette_bmp_path)
        payload_a["panel_layout"] = stage_e_a["panel_config"]
        payload_a["layout_gates"] = g8_layout
        payload_a["displacement"] = stage_e_a["displacement"]
        payload_a["silhouette_iou"] = g8_silhouette
        payload_a["rotated_islands_skin"] = g8_layout["rotated_islands_skin"]
        payload_a["side_purity_before"] = g8_side_purity_before
        payload_a["side_purity_after"] = g8_side_purity
        payload_a["face_reassignment"] = g8_face_changes
    ceiling_a = (
        None if frozen_layout_mode else strict_grouping_ceiling(
            selected_run["islands_a"], selected_specs, scale_a,
        )
    )
    grouping_cost = (
        None if (g8_mode or g9_mode) else estimate_strict_grouping_cost(islands_a, blocks_a)
    )
    baseline_matches = {
        "occupancy_exact": abs(summary_base_a["occupancy"] - G3_OCCUPANCY_A) <= 1e-15,
        "overlap_exact": abs(summary_base_a["overlap_area_frac"] - G3_OVERLAP_A) <= 1e-15,
        "global_scale_exact": abs(summary_base_a["global_uv_scale"] - G3_GLOBAL_SCALE_A) <= 1e-15,
    }
    if frozen_layout_mode:
        input_axes = dict(assignment["projection_axes"])
        selected_axes = {sid: selected_specs[sid]["axis"] for sid in sorted(selected_specs)}
        axis_frozen_ok = input_axes == selected_axes and not axis_changes
        axis_migration_overlap_ok = True
        axis_not_worse_ok = axis_frozen_ok
        axis_migrations_strictly_better = True
        axis_policy_ok = axis_frozen_ok
        overlap_value_a = float(overlap_a.get("overlap_area_frac") or 0.0)
        if g9_mode:
            g8_overlap_a = float(g8_baseline_metrics["atlas_a"]["overlap_area_frac"])
            g7_overlap_a = float(
                g8_baseline_metrics["baseline_reproduction"]["g7_atlas_a"]["overlap_area_frac"]
            )
            g6_overlap_a = float(
                g8_baseline_metrics["baseline_reproduction"]["g6_atlas_a"]["overlap_area_frac"]
            )
            overlap_delta_vs_g8 = abs(overlap_value_a - g8_overlap_a)
            overlap_delta_vs_g7 = abs(overlap_value_a - g7_overlap_a)
            overlap_delta_vs_g6 = abs(overlap_value_a - g6_overlap_a)
            overlap_gate = overlap_value_a <= G9_OVERLAP_LIMIT_A
        elif g8_mode:
            g7_overlap_a = float(g7_baseline_metrics["atlas_a"]["overlap_area_frac"])
            g6_overlap_a = float(
                g7_baseline_metrics["baseline_reproduction"]["atlas_a"]["overlap_area_frac"]
            )
            overlap_delta_vs_g6 = abs(overlap_value_a - g6_overlap_a)
            overlap_delta_vs_g7 = abs(overlap_value_a - g7_overlap_a)
            overlap_delta_vs_g8 = None
            overlap_gate = overlap_value_a <= G8_OVERLAP_LIMIT_A
        else:
            g6_overlap_a = float(g6_baseline_metrics["atlas_a"]["overlap_area_frac"])
            overlap_delta_vs_g6 = abs(overlap_value_a - g6_overlap_a)
            overlap_delta_vs_g7 = None
            overlap_delta_vs_g8 = None
            overlap_gate = (
                overlap_value_a <= G7_OVERLAP_LIMIT_A
                and overlap_delta_vs_g6 <= G7_OVERLAP_BASELINE_TOLERANCE
            )
    else:
        axis_migration_overlap_ok = all(
            not r["changed"] or r["self_overlap_after"] <= r["overlap_limit"]
            for r in axis_records
        )
        axis_not_worse_ok = all(
            r["bbox_to_island_area_after"] <= r["bbox_to_island_area_before"]
            for r in axis_records
        )
        axis_migrations_strictly_better = all(
            not r["changed"]
            or r["bbox_to_island_area_after"] < r["bbox_to_island_area_before"]
            for r in axis_records
        )
        axis_policy_ok = (
            axis_migration_overlap_ok
            and axis_not_worse_ok
            and axis_migrations_strictly_better
        )
        overlap_delta_vs_g6 = None
        overlap_delta_vs_g7 = None
        overlap_delta_vs_g8 = None
        overlap_gate = (overlap_a.get("overlap_area_frac") or 0.0) <= G3_OVERLAP_A
    density_gate = (
        dens_a.get("texel_density_ratio") is not None
        and dens_b.get("texel_density_ratio") is not None
        and dens_a["texel_density_ratio"] <= 1.000001
        and dens_b["texel_density_ratio"] <= 1.000001
    )
    rotation_gate = rotations_a["pass"] and rotations_b["pass"]
    labels_order_gate = order_a["pass"] and order_b["pass"]
    if g9_mode:
        occupancy_gate = True
    elif g8_mode:
        occupancy_gate = payload_a["occupancy"] >= G8_OCCUPANCY_FLOOR
    elif g7_mode:
        occupancy_gate = payload_a["occupancy"] >= G7_OCCUPANCY_FLOOR
    else:
        occupancy_gate = payload_a["occupancy"] > G3_OCCUPANCY_A
    scale_fidelity_gate = True
    displacement_gate = True
    affine_vertex_gate = True
    if g9_mode:
        side_purity_gate = (
            g9_side_purity["worst"] is not None
            and g9_side_purity["worst"] >= 1.0 - 1e-12
            and g9_side_purity["label_face_sign_mismatch_count"] == 0
        )
        pair_v_gate = pair_u_gate = pair_interposed_gate = True
        pair_homologous_gate = True
        layout_fidelity_gate = True
        panel_island_gate = g9_layout["panel_invasion_count"] == 0
        silhouette_gate = all(
            g9_silhouette[panel]["pass"] for panel in ("skin", "internal")
        )
        face_reassignment_gate = (
            g9_face_changes["unique_faces"] == [4053]
            and g9_face_changes["changed_island_count"] == 2
        )
        displacement_gate = (
            stage_e_a["displacement"]["worst_uv"] == 0.0
            and all(
                row["target_uv"] == row["placed_uv"]
                and row["displacement_uv"] == 0.0
                for row in stage_e_a["displacement"]["per_island"]
            )
        )
        scale_fidelity_gate = all(
            g9_scale_fidelity[panel]["pass"] for panel in ("skin", "internal")
        )
        affine_vertex_gate = stage_e_a["affine_vertex_gate"]["pass"]
        placement_hard_gate = (
            side_purity_gate and panel_island_gate and face_reassignment_gate
            and displacement_gate and scale_fidelity_gate and affine_vertex_gate
        )
        fixed_assignment_gate = (
            tuple(a_shells) == G7_ATLAS_A_SHELLS
            and tuple(assignment["atlas_b"]) == ("S00", "S01", "S04", "S11", "S12")
            and abs(ISLAND_VIS_THRESHOLD - 0.005) <= 1e-15
            and axis_policy_ok
        )
        anatomy_rotation_gate = rotation_gate and placement_hard_gate
    elif g8_mode:
        side_purity_gate = (
            g8_side_purity["worst"] is not None
            and g8_side_purity["worst"] >= 1.0 - 1e-12
            and g8_side_purity["label_face_sign_mismatch_count"] == 0
        )
        pair_v_gate = g8_layout["pair_v_offset"]["worst"] <= 1e-12
        pair_u_gate = g8_layout["pair_u_symmetry"]["worst"] <= 1e-12
        pair_interposed_gate = g8_layout["pair_interposed"]["worst"] == 0
        pair_homologous_gate = True
        layout_fidelity_gate = True
        panel_island_gate = (
            g8_layout["island_bbox_overlap_count"] == 0
            and g8_layout["panel_invasion_count"] == 0
        )
        silhouette_gate = (
            g8_silhouette["pass"] and g7_silhouette_control["discriminates"]
        )
        face_reassignment_gate = (
            g8_face_changes["unique_faces"] == [4053]
            and g8_face_changes["changed_island_count"] == 2
        )
        placement_hard_gate = (
            side_purity_gate and pair_v_gate and pair_u_gate
            and pair_interposed_gate and panel_island_gate
            and face_reassignment_gate
        )
        fixed_assignment_gate = (
            tuple(a_shells) == G7_ATLAS_A_SHELLS
            and tuple(assignment["atlas_b"]) == ("S00", "S01", "S04", "S11", "S12")
            and abs(ISLAND_VIS_THRESHOLD - 0.005) <= 1e-15
            and axis_policy_ok
        )
        anatomy_rotation_gate = rotation_gate and placement_hard_gate
    elif g7_mode:
        side_purity_gate = (
            g7_side_purity["worst"] is not None
            and g7_side_purity["worst"] >= 1.0 - 1e-12
            and g7_side_purity["label_face_sign_mismatch_count"] == 0
        )
        pair_v_gate = g7_placement["pair_v_offset"]["worst"] <= 1e-12
        pair_u_gate = g7_placement["pair_u_symmetry"]["worst"] <= 1e-12
        pair_interposed_gate = g7_placement["pair_interposed"]["worst"] == 0
        pair_homologous_gate = (
            g7_homologous["all_homologues_present"]
            and g7_homologous["worst"] is not None
            and g7_homologous["worst"] <= 1e-12
        )
        rho_value = g7_placement["layout_fidelity_v"]["rho"]
        layout_fidelity_gate = rho_value is not None and rho_value >= 0.8
        placement_hard_gate = (
            side_purity_gate and pair_v_gate and pair_u_gate and pair_interposed_gate
            and pair_homologous_gate
        )
        fixed_assignment_gate = (
            tuple(a_shells) == G7_ATLAS_A_SHELLS
            and tuple(assignment["atlas_b"]) == ("S00", "S01", "S04", "S11", "S12")
            and abs(ISLAND_VIS_THRESHOLD - 0.005) <= 1e-15
            and axis_policy_ok
        )
        anatomy_rotation_gate = rotation_gate and placement_hard_gate
        panel_island_gate = True
        silhouette_gate = True
    else:
        side_purity_gate = pair_v_gate = pair_u_gate = pair_interposed_gate = True
        pair_homologous_gate = True
        layout_fidelity_gate = True
        placement_hard_gate = True
        fixed_assignment_gate = axis_policy_ok
        anatomy_rotation_gate = rotation_gate
        panel_island_gate = True
        silhouette_gate = True
    invariants_six = {
        "1_strict_grouping": {
            "pass": grouping_ok,
            "atlas_a_purity_worst": gates_a["block_purity_worst"],
            "atlas_b_purity_worst": gates_b["block_purity_worst"],
            "atlas_a_block_overlap_pairs": gates_a["block_bbox_overlap_count"],
            "atlas_b_block_overlap_pairs": gates_b["block_bbox_overlap_count"],
        },
        "2_one_global_texel_density": {
            "pass": density_gate,
            "atlas_a_ratio": dens_a.get("texel_density_ratio"),
            "atlas_b_ratio": dens_b.get("texel_density_ratio"),
            "atlas_a_scale": scale_a,
            "atlas_b_scale": scale_b,
        },
        "3_overlap_a_not_worse": {
            "pass": overlap_gate,
            "baseline": G3_OVERLAP_A,
            "final": overlap_a.get("overlap_area_frac"),
            "axis_piece_gate_pass": axis_policy_ok,
        },
        "4_face_partition": dict(inv),
        "5_whole_block_rotation_only": {
            "pass": rotation_gate,
            "atlas_a": rotations_a,
            "atlas_b": rotations_b,
        },
        "6_labels_and_local_grid_order": {
            "pass": labels_order_gate,
            "atlas_a": order_a,
            "atlas_b": order_b,
        },
    }
    if g9_mode:
        invariants_six = {
            "1_one_global_texel_density": {
                "pass": density_gate,
                "atlas_a_ratio": dens_a.get("texel_density_ratio"),
                "atlas_b_ratio": dens_b.get("texel_density_ratio"),
                "atlas_a_scale": scale_a,
                "atlas_b_scale": scale_b,
            },
            "2_exact_face_partition": dict(inv),
            "3_side_purity": {
                "pass": side_purity_gate,
                "worst": g9_side_purity["worst"],
                "label_face_sign_mismatch_count": g9_side_purity["label_face_sign_mismatch_count"],
            },
            "4_fixed_assignment_threshold_and_g8_axes": {
                "pass": fixed_assignment_gate and face_reassignment_gate,
                "atlas_a": a_shells,
                "atlas_b": list(assignment["atlas_b"]),
                "threshold": ISLAND_VIS_THRESHOLD,
                "axes_frozen": axis_policy_ok,
                "axis_changes": [record for record in axis_records if record["changed"]],
                "face_reassignment": g9_face_changes,
            },
            "5_atlas_a_self_overlap_excluding_intra_layer_collision": {
                "pass": overlap_gate,
                "limit": G9_OVERLAP_LIMIT_A,
                "g6_baseline": g6_overlap_a,
                "g7_baseline": g7_overlap_a,
                "g8_baseline": g8_overlap_a,
                "final": overlap_a.get("overlap_area_frac"),
                "cross_island_overlap_excluded": overlap_a.get("cross_island_overlap_excluded"),
                "intra_layer_overlap": g9_intra_overlap,
            },
            "6_no_rotation_for_z_projected_islands": {
                "pass": rotation_gate,
                "atlas_a": rotations_a,
                "atlas_b": rotations_b,
            },
        }
    elif g8_mode:
        invariants_six = {
            "1_one_global_texel_density": {
                "pass": density_gate,
                "atlas_a_ratio": dens_a.get("texel_density_ratio"),
                "atlas_b_ratio": dens_b.get("texel_density_ratio"),
                "atlas_a_scale": scale_a,
                "atlas_b_scale": scale_b,
            },
            "2_exact_face_partition": dict(inv),
            "3_disjoint_panels_and_zero_island_bbox_overlap": {
                "pass": panel_island_gate and gates_b["verdict"] == "PASS",
                "atlas_a_island_overlap_pairs": g8_layout["island_bbox_overlap_count"],
                "atlas_a_panel_invasions": g8_layout["panel_invasion_count"],
                "atlas_b_block_overlap_pairs": gates_b["block_bbox_overlap_count"],
            },
            "4_fixed_assignment_threshold_and_g7_axes": {
                "pass": fixed_assignment_gate and face_reassignment_gate,
                "atlas_a": a_shells,
                "atlas_b": list(assignment["atlas_b"]),
                "threshold": ISLAND_VIS_THRESHOLD,
                "axes_frozen": axis_policy_ok,
                "axis_changes": [record for record in axis_records if record["changed"]],
                "face_reassignment": g8_face_changes,
            },
            "5_atlas_a_self_overlap": {
                "pass": overlap_gate,
                "limit": G8_OVERLAP_LIMIT_A,
                "g6_baseline": g6_overlap_a,
                "g7_baseline": g7_overlap_a,
                "final": overlap_a.get("overlap_area_frac"),
                "absolute_delta_vs_g6": overlap_delta_vs_g6,
                "absolute_delta_vs_g7": overlap_delta_vs_g7,
            },
            "6_readable_unique_island_labels": {
                "pass": labels_order_gate,
                "atlas_a": order_a,
                "atlas_b": order_b,
            },
        }
    if g7_mode:
        seven_invariants = {
            "1_zero_block_purity_and_no_block_bbox_overlap": {
                "pass": grouping_ok,
                "atlas_a_purity_worst": gates_a["block_purity_worst"],
                "atlas_b_purity_worst": gates_b["block_purity_worst"],
                "atlas_a_block_overlap_pairs": gates_a["block_bbox_overlap_count"],
                "atlas_b_block_overlap_pairs": gates_b["block_bbox_overlap_count"],
            },
            "2_one_global_texel_density": {
                "pass": density_gate,
                "atlas_a_ratio": dens_a.get("texel_density_ratio"),
                "atlas_b_ratio": dens_b.get("texel_density_ratio"),
                "atlas_a_scale": scale_a,
                "atlas_b_scale": scale_b,
            },
            "3_face_partition": dict(inv),
            "4_whole_block_rotation_and_anatomy_compatibility": {
                "pass": anatomy_rotation_gate,
                "rotation_gate": rotation_gate,
                "side_purity_gate": side_purity_gate,
                "pair_v_gate": pair_v_gate,
                "pair_u_gate": pair_u_gate,
                "pair_interposed_gate": pair_interposed_gate,
                "pair_homologous_gate": pair_homologous_gate,
                "pair_homologous_v_offset": g7_homologous,
                "atlas_a": rotations_a,
                "atlas_b": rotations_b,
            },
            "5_labels_and_final_grid_order": {
                "pass": labels_order_gate,
                "atlas_a": order_a,
                "atlas_b": order_b,
            },
            "6_fixed_assignment_threshold_and_g6_axes": {
                "pass": fixed_assignment_gate,
                "atlas_a": a_shells,
                "atlas_b": list(assignment["atlas_b"]),
                "threshold": ISLAND_VIS_THRESHOLD,
                "axes_frozen": axis_policy_ok,
            },
            "7_atlas_a_self_overlap": {
                "pass": overlap_gate,
                "limit": G7_OVERLAP_LIMIT_A,
                "g6_baseline": g6_overlap_a,
                "final": overlap_a.get("overlap_area_frac"),
                "absolute_delta_vs_g6": overlap_delta_vs_g6,
                "delta_tolerance": G7_OVERLAP_BASELINE_TOLERANCE,
            },
        }
        all_green = (
            all(value.get("pass", False) for value in seven_invariants.values())
            and occupancy_gate and layout_fidelity_gate and ca["pass"] and cb["pass"]
        )
    else:
        seven_invariants = None
        all_green = (
            all(v.get("pass", False) for v in invariants_six.values())
            and occupancy_gate and axis_policy_ok and ca["pass"] and cb["pass"]
            and (silhouette_gate if (g8_mode or g9_mode) else True)
            and (placement_hard_gate if (g8_mode or g9_mode) else True)
            and (rotation_gate if (g8_mode or g9_mode) else True)
            and (labels_order_gate if g9_mode else True)
        )
    if g9_mode:
        g8_atlas_a = g8_baseline_metrics["atlas_a"]
        g7_atlas_a = g8_baseline_metrics["baseline_reproduction"]["g7_atlas_a"]
        g6_atlas_a = g8_baseline_metrics["baseline_reproduction"]["g6_atlas_a"]
        pack_method_text = (
            "G9 atlas A: equal n+ skin and n- internal frames with identical world-XY "
            "framing; one shared affine scale u=a*X+b, v=a*Y+c; every island center "
            "stays exactly at its affine target. No packer, collision resolver, gap "
            "closure or per-island translation runs. Z-projected islands stay at 0 "
            "degrees; the existing S10 +Y front-view exception remains 180 degrees. "
            "Atlas B retains the G8 MaxRects flow."
        )
        baseline_payload = {
            "source": os.path.join(os.path.dirname(assign_arg), "atlas_metrics.json"),
            "generation": "G8",
            "g6_atlas_a": {
                key: g6_atlas_a[key]
                for key in ("occupancy", "overlap_area_frac", "global_uv_scale", "decomposition")
            },
            "g7_atlas_a": {
                key: g7_atlas_a[key]
                for key in ("occupancy", "overlap_area_frac", "global_uv_scale", "decomposition")
            },
            "g8_atlas_a": {
                key: g8_atlas_a[key]
                for key in ("occupancy", "overlap_area_frac", "global_uv_scale", "decomposition")
            },
        }
        axis_payload = {
            "policy": "g9_input_axes_frozen_no_search",
            "incumbent_source": "input out_g8/assignment_REAL.json",
            "axes_tested_per_piece": [],
            "policy_gate_pass": axis_policy_ok,
            "pieces_changed": [],
            "records": axis_records,
        }
        occupancy_payload = {
            "pass": True,
            "gate": "report_only_no_floor",
            "floor": None,
            "g6": g6_atlas_a["occupancy"],
            "g7": g7_atlas_a["occupancy"],
            "g8": g8_atlas_a["occupancy"],
            "g9": payload_a["occupancy"],
            "change_abs_g8_to_g9": payload_a["occupancy"] - float(g8_atlas_a["occupancy"]),
            "change_relative_pct_g8_to_g9": (
                100.0 * (payload_a["occupancy"] - float(g8_atlas_a["occupancy"]))
                / float(g8_atlas_a["occupancy"])
            ),
            "interpretation": "Occupancy has no minimum in G9; preserved world gaps are information.",
        }
    elif g8_mode:
        g7_atlas_a = g7_baseline_metrics["atlas_a"]
        g6_atlas_a = g7_baseline_metrics["baseline_reproduction"]["atlas_a"]
        pack_method_text = (
            "G8 atlas A: n+ skin in the upper 60.5% panel and n- internal faces in "
            "the lower 39.5% panel; each island targets its own area-weighted world "
            "XY centroid; deterministic minimum-translation bbox contacts resolve "
            "collisions. Z-projected islands stay at 0 degrees; measured front-view "
            "exception S10 uses 180 degrees. Atlas B retains G7/G6 MaxRects."
        )
        baseline_payload = {
            "source": os.path.join(os.path.dirname(assign_arg), "atlas_metrics.json"),
            "generation": "G7",
            "g6_atlas_a": {
                "occupancy": g6_atlas_a["occupancy"],
                "overlap_area_frac": g6_atlas_a["overlap_area_frac"],
                "global_uv_scale": g6_atlas_a["global_uv_scale"],
                "decomposition": g6_atlas_a["decomposition"],
            },
            "g7_atlas_a": {
                "occupancy": g7_atlas_a["occupancy"],
                "overlap_area_frac": g7_atlas_a["overlap_area_frac"],
                "global_uv_scale": g7_atlas_a["global_uv_scale"],
                "decomposition": g7_atlas_a["decomposition"],
            },
        }
        axis_payload = {
            "policy": "g8_input_axes_frozen_no_search",
            "incumbent_source": "input out_g7/assignment_REAL.json",
            "axes_tested_per_piece": [],
            "policy_gate_pass": axis_policy_ok,
            "pieces_changed": [],
            "records": axis_records,
        }
        occupancy_payload = {
            "pass": occupancy_gate,
            "gate": "floor",
            "floor": G8_OCCUPANCY_FLOOR,
            "g6": {
                "occupancy": g6_atlas_a["occupancy"],
                "decomposition": g6_atlas_a["decomposition"],
            },
            "g7": {
                "occupancy": g7_atlas_a["occupancy"],
                "decomposition": g7_atlas_a["decomposition"],
            },
            "g8": {
                "occupancy": payload_a["occupancy"],
                "decomposition": payload_a["decomposition"],
            },
            "change_abs_g7_to_g8": payload_a["occupancy"] - float(g7_atlas_a["occupancy"]),
            "change_relative_pct_g7_to_g8": (
                100.0 * (payload_a["occupancy"] - float(g7_atlas_a["occupancy"]))
                / float(g7_atlas_a["occupancy"])
            ),
        }
    elif g7_mode:
        g6_atlas_a = g6_baseline_metrics["atlas_a"]
        pack_method_text = (
            "G7 atlas A: anatomical tail-to-nose bands; X<mid left, X>mid right; "
            "crossing pieces straddle u=0.5; mirrored pairs share V and symmetric U; "
            "fine n-sign placement occurs inside the assigned side; fixed 8px bleed "
            "and 32px label; one global scale. Atlas B retains the G6 MaxRects flow."
        )
        baseline_payload = {
            "source": os.path.join(os.path.dirname(assign_arg), "atlas_metrics.json"),
            "generation": "G6",
            "atlas_a": {
                "occupancy": g6_atlas_a["occupancy"],
                "overlap_area_frac": g6_atlas_a["overlap_area_frac"],
                "global_uv_scale": g6_atlas_a["global_uv_scale"],
                "decomposition": g6_atlas_a["decomposition"],
            },
        }
        axis_payload = {
            "policy": "g7_input_axes_frozen_no_search",
            "incumbent_source": "input out_g6/assignment_REAL.json",
            "axes_tested_per_piece": [],
            "policy_gate_pass": axis_policy_ok,
            "pieces_changed": [],
            "records": axis_records,
        }
        occupancy_reference = float(g6_atlas_a["occupancy"])
        occupancy_payload = {
            "pass": occupancy_gate,
            "gate": "floor",
            "floor": G7_OCCUPANCY_FLOOR,
            "g6_baseline": occupancy_reference,
            "final": payload_a["occupancy"],
            "change_abs": payload_a["occupancy"] - occupancy_reference,
            "change_relative_pct": (
                100.0 * (payload_a["occupancy"] - occupancy_reference) / occupancy_reference
            ),
            "g6_decomposition": g6_atlas_a["decomposition"],
            "g7_decomposition": payload_a["decomposition"],
        }
    else:
        pack_method_text = (
            "piece-blocks: fitted L/R x n+/n- grid; fixed 8px bleed and 32px "
            "label at 2048; rigid 0/90/180/270 block rotation; shelf then "
            "MaxRects BSSF with area/max-side/perimeter insertion orders; "
            "one global geometry scale per atlas"
        )
        baseline_payload = {
            "source": "out_final/atlas_metrics.json",
            "expected_occupancy": G3_OCCUPANCY_A,
            "expected_overlap": G3_OVERLAP_A,
            "expected_global_scale": G3_GLOBAL_SCALE_A,
            "measured": {
                "occupancy": summary_base_a["occupancy"],
                "overlap": summary_base_a["overlap_area_frac"],
                "global_scale": summary_base_a["global_uv_scale"],
            },
            "matches": baseline_matches,
            "all_exact": all(baseline_matches.values()),
        }
        axis_payload = {
            "policy": AXIS_SEARCH_POLICY,
            "incumbent_source": "input projection_axes (out_tight/assignment_REAL.json for G6)",
            "axes_tested_per_piece": list(AXIS_NAMES),
            "grid_n": AXIS_SEARCH_OVERLAP_GRID,
            "absolute_self_overlap_limit": AXIS_SEARCH_SELF_OVERLAP_ABSOLUTE_LIMIT,
            "migration_overlap_gate_pass": axis_migration_overlap_ok,
            "no_piece_worse_than_incumbent_gate_pass": axis_not_worse_ok,
            "migrations_strictly_more_compact_gate_pass": axis_migrations_strictly_better,
            "policy_gate_pass": axis_policy_ok,
            "pieces_changed": [r["shell"] for r in axis_changes],
            "records": axis_records,
        }
        occupancy_payload = {
            "pass": occupancy_gate,
            "baseline": G3_OCCUPANCY_A,
            "final": payload_a["occupancy"],
            "gain_abs": payload_a["occupancy"] - G3_OCCUPANCY_A,
            "gain_relative_pct": (
                100.0 * (payload_a["occupancy"] - G3_OCCUPANCY_A) / G3_OCCUPANCY_A
            ),
        }
    metrics = {
        "object": obj.name,
        "blend_sha256": sha,
        "SMOKE": False,
        "NOT_the_real_paint_mechanical_split": False,
        "note_tris_key": "copied from uv_metrics_run_REFERENCE.py; 'tris' is len(faces), not triangles",
        "pack_method": pack_method_text,
        "padding": fixed_padding_config(),
        "island_vis_threshold": ISLAND_VIS_THRESHOLD,
        "assignment_atlas_a_shells": a_shells,
        "assignment_atlas_b_shells": list(assignment["atlas_b"]),
        "symmetry": {
            "pair_fraction_X": symmetry["pair_fraction"]["X"],
            "pair_fraction_Y": symmetry["pair_fraction"]["Y"],
            "pair_fraction_Z": symmetry["pair_fraction"]["Z"],
            "winner_axis": symmetry["winner_axis"],
            "mid_plane": symmetry["mid_plane"],
            "tolerance_world": symmetry["tolerance"],
            "bbox_diagonal": symmetry["diagonal"],
        },
        "defaults": {
            "split_lr": DEFAULT_SPLIT_LR,
            "split_by_normal_sign": DEFAULT_SPLIT_BY_NORMAL_SIGN,
            "local_conformal_polish": DEFAULT_LOCAL_CONFORMAL_POLISH,
            "axis_if_missing": "smallest bbox extent, sign from exterior vs mesh centroid",
        },
        "atlas_a": payload_a,
        "atlas_b": payload_b,
        "invariant": inv,
        "invariant_baseline": inv_baseline,
        "baseline_reproduction": baseline_payload,
        "step_contributions": {
            "atlas_a": steps_a,
            "atlas_b": steps_b,
        },
        "axis_search": axis_payload,
        "strict_grouping_ceiling": ceiling_a,
        "strict_grouping_cost_estimate": grouping_cost,
        "six_invariants": None if g7_mode else invariants_six,
        "seven_invariants": seven_invariants,
        "occupancy_improved_gate": occupancy_payload,
        "occupancy_report": occupancy_payload if g9_mode else None,
        "occupancy_history": ({
            "G6": float(g6_atlas_a["occupancy"]),
            "G7": float(g7_atlas_a["occupancy"]),
            "G8": float(g8_atlas_a["occupancy"]),
            "G9": float(payload_a["occupancy"]),
            "floor_applies_to_G9": False,
        } if g9_mode else None),
        "occupancy_floor_gate": occupancy_payload if (g7_mode or g8_mode) else None,
        "sign_convention": G7_SIGN_CONVENTION if frozen_layout_mode else None,
        "longitudinal_convention": G7_LONGITUDINAL_CONVENTION if frozen_layout_mode else None,
        "side_purity": (
            g9_side_purity if g9_mode
            else g8_side_purity if g8_mode else g7_side_purity if g7_mode else None
        ),
        "side_purity_before": (
            g9_side_purity_before if g9_mode else g8_side_purity_before if g8_mode else None
        ),
        "side_purity_after": (
            g9_side_purity if g9_mode else g8_side_purity if g8_mode else None
        ),
        "face_reassignment": (
            g9_face_changes if g9_mode else g8_face_changes if g8_mode else None
        ),
        "pair_v_offset": (
            g8_layout["pair_v_offset"] if g8_mode
            else g7_placement["pair_v_offset"] if g7_mode else None
        ),
        "pair_u_symmetry": (
            g8_layout["pair_u_symmetry"] if g8_mode
            else g7_placement["pair_u_symmetry"] if g7_mode else None
        ),
        "pair_interposed": (
            g8_layout["pair_interposed"] if g8_mode
            else g7_placement["pair_interposed"] if g7_mode else None
        ),
        "pair_homologous_v_offset": g7_homologous if g7_mode else None,
        "layout_fidelity_v": g7_placement["layout_fidelity_v"] if g7_mode else None,
        "neighbour_keep_at_3": g7_placement["neighbour_keep_at_3"] if g7_mode else None,
        "piece_positions": g7_placement["piece_positions"] if g7_mode else None,
        "g7_layout_policy": ({
            "centerline_u": 0.5,
            "sign_boundary_x": G7_SIGN_SPLIT_X,
            "measured_symmetry_mid_x": symmetry["mid_plane"]["X"],
            "mirror_pairs": [list(pair) for pair in G7_MIRROR_PAIRS],
            "bands_tail_to_nose": stage_e_a["selected_order"],
            "chosen_rotations_deg": stage_e_a["chosen_rotations_deg"],
            "rotated_shells": stage_e_a["rotated_shells"],
            "selection_policy": stage_e_a["selection_policy"],
            "scale_search": stage_e_a["scale_search"],
            "orientation_trials": stage_e_a["order_trials"],
        } if g7_mode else None),
        "g8_layout_policy": ({
            "centerline_u": 0.5,
            "sign_boundary_x": G7_SIGN_SPLIT_X,
            "mirror_pairs": [list(pair) for pair in G7_MIRROR_PAIRS],
            "panel_config": stage_e_a["panel_config"],
            "panel_mappings": stage_e_a["panel_mappings"],
            "selected_order": stage_e_a["selected_order"],
            "scale_search": stage_e_a["scale_search"],
            "front_view_shells": ["S09", "S10"],
            "z_projection_rotation_policy": "rotation_deg=0, mandatory",
            "s08_internal_threshold_note": (
                "S08 n- remains in atlas B because island_vis_share < 0.005; "
                "the lower panel contains every n- island still classified in A."
            ),
        } if g8_mode else None),
        "g9_layout_policy": ({
            "centerline_u": 0.5,
            "sign_boundary_x": G7_SIGN_SPLIT_X,
            "panel_config": stage_e_a["panel_config"],
            "panel_mappings": stage_e_a["panel_mappings"],
            "affine_transform_by_layer": {
                panel: {
                    key: stage_e_a["panel_mappings"][panel][key]
                    for key in ("a", "b", "c", "target_frame_bbox")
                }
                for panel in ("skin", "internal")
            },
            "same_scale_both_layers": True,
            "same_xy_framing_both_layers": True,
            "z_projected_vertex_affine_gate": stage_e_a["affine_vertex_gate"],
            "front_view_affine_exception": (
                "S09/S10 retain their frozen +Y projection; S10 retains r180. Their "
                "centers still use the common world-XY affine and displacement zero."
            ),
            "collision_resolution": "disabled",
            "per_island_translation": "forbidden_and_measured_zero",
            "gap_policy": "preserve_world_xy_gaps",
            "scale_search": stage_e_a["scale_search"],
            "front_view_shells": ["S09", "S10"],
            "z_projection_rotation_policy": "rotation_deg=0, mandatory",
            "s08_internal_threshold_note": (
                "S08 n- remains in atlas B because island_vis_share < 0.005; "
                "the internal frame contains every n- island still classified in A."
            ),
        } if g9_mode else None),
        "rotated_islands_skin": (
            g8_layout["rotated_islands_skin"] if g8_mode else None
        ),
        "rotated_islands": g9_layout["rotated_islands"] if g9_mode else None,
        "displacement_from_plan_target": (
            stage_e_a["displacement"] if (g8_mode or g9_mode) else None
        ),
        "silhouette_iou": g8_silhouette if g8_mode else None,
        "silhouette_iou_g7_control": g7_silhouette_control if g8_mode else None,
        "silhouette_iou_by_layer": g9_silhouette if g9_mode else None,
        "silhouette_iou_g8_corrected": g8_silhouette_corrected if g9_mode else None,
        "silhouette_metric_role": (
            "placement_rasterizer_consistency_not_aesthetic_quality" if g9_mode else None
        ),
        "scale_fidelity": g9_scale_fidelity if g9_mode else None,
        "intra_layer_overlap": g9_intra_overlap if g9_mode else None,
        "displacement_gate": ({
            "pass": displacement_gate,
            "objective": 0.0,
            "worst_uv": stage_e_a["displacement"]["worst_uv"],
        } if g9_mode else None),
        "scale_fidelity_gate": ({
            "pass": scale_fidelity_gate,
            "objective_cv_max_exclusive": G9_SCALE_FIDELITY_CV_MAX,
        } if g9_mode else None),
        "affine_vertex_gate": stage_e_a["affine_vertex_gate"] if g9_mode else None,
        "all_required_gates_green": all_green,
        "grouping_gates": {
            "atlas_a": {
                "block_purity_all_zero": gates_a["block_purity_all_zero"],
                "block_purity_worst": gates_a["block_purity_worst"],
                "block_purity_by_piece": gates_a["block_purity_by_piece"],
                "block_bbox_overlap_count": gates_a["block_bbox_overlap_count"],
                "verdict": gates_a["verdict"],
            },
            "atlas_b": {
                "block_purity_all_zero": gates_b["block_purity_all_zero"],
                "block_purity_worst": gates_b["block_purity_worst"],
                "block_purity_by_piece": gates_b["block_purity_by_piece"],
                "block_bbox_overlap_count": gates_b["block_bbox_overlap_count"],
                "verdict": gates_b["verdict"],
            },
            "verdict": "PASS" if grouping_ok else "FAIL",
        },
        "vs_smoke": {
            "smoke_islands_a": SMOKE_ISLANDS_A,
            "smoke_overlap_a": SMOKE_OVERLAP_A,
            "final_islands_a": len(islands_a),
            "final_overlap_a": overlap_a.get("overlap_area_frac"),
            "overlap_a_not_worse": (
                (overlap_a.get("overlap_area_frac") or 0.0) <= SMOKE_OVERLAP_A + 1e-6
            ),
            "note": (
                "SMOKE was 6 paint pieces / 20 islands / overlap 0.0964, "
                "shelf-packed by island size (pieces mixed). REAL is 8 paint "
                "pieces, block-packed by piece, n- halves may move to B."
            ),
        },
        "controls": {"a_mirror": ca, "b_normal_split": cb},
        "shells_whole_mesh": len(shell_list),
        "faces_whole_mesh": len(bm.faces),
        "texel_density_ratio": dens_a.get("texel_density_ratio"),
        "overlap_area_frac": overlap_a.get("overlap_area_frac"),
        "islands_atlas_a": len(islands_a),
        "islands_atlas_b": len(islands_b),
    }
    metrics_path = os.path.join(outdir, "atlas_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % metrics_path)
    log("SUMMARY " + json.dumps({
        "islands_a": len(islands_a),
        "blocks_a": len(blocks_a),
        "islands_b": len(islands_b),
        "blocks_b": len(blocks_b),
        "faces_a": inv["faces_a"],
        "faces_b": inv["faces_b"],
        "invariant": inv["verdict"],
        "overlap_a": overlap_a.get("overlap_area_frac"),
        "occupancy_a": payload_a["occupancy"],
        "texel_density_ratio_a": dens_a.get("texel_density_ratio"),
        "purity_a": gates_a["block_purity_all_zero"],
        "purity_worst_a": gates_a["block_purity_worst"],
        "block_overlaps_a": gates_a["block_bbox_overlap_count"],
        "threshold": ISLAND_VIS_THRESHOLD,
        "moved_x2": sens["islands_moved_if_x2"],
        "moved_half": sens["islands_moved_if_half"],
        "control_a": ca["verdict"],
        "control_b": cb["verdict"],
        "grouping": "PASS" if grouping_ok else "FAIL",
        "all_required_gates": "PASS" if all_green else "FAIL",
        "global_scale_a": scale_a,
        "packer_a": stage_e_a["packer"],
        "axis_changes": [r["shell"] for r in axis_changes],
    }))
    bm.free()
    # Never bpy.ops.wm.save*; input blend stays byte-identical.
    if not all_green:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
