"""blender_helpers.py — verified helper library for the blender-assembly skill.

Version: 2.1 (2026-06-10)
Convention: execute this whole file via the Blender MCP at session start instead
of re-pasting functions. A new helper enters this library only after it passes
a test in Blender (see "Helper library" in the skill's SKILL.md).

Validated on Blender 5.1.1. Three behaviours were fixed during that validation
and passed again afterwards: verify_mesh_integrity reports ngons as a warning
instead of a failure; verify_bounds forces a depsgraph update before reading
matrix_world; make_cable fills and welds end caps so tubes pass
require_closed=True.
"""

import bpy
import bmesh
import math
from mathutils import Vector


# ============================================================
# v1 helpers — construction (validated in prior sessions)
# ============================================================

def make_beam(name, start, end, hw=0.012, hh=0.010):
    """Build a rectangular beam from start to end — no rotations needed."""
    dx, dy, dz = end[0]-start[0], end[1]-start[1], end[2]-start[2]
    L = math.sqrt(dx*dx + dy*dy + dz*dz)
    if L < 1e-6:
        return None
    fx, fy, fz = dx/L, dy/L, dz/L
    ux, uy, uz = (0, 0, 1) if abs(fz) < 0.99 else (1, 0, 0)
    rx = fy*uz-fz*uy; ry = fz*ux-fx*uz; rz = fx*uy-fy*ux
    rL = math.sqrt(rx*rx+ry*ry+rz*rz); rx, ry, rz = rx/rL, ry/rL, rz/rL
    upx = ry*fz-rz*fy; upy = rz*fx-rx*fz; upz = rx*fy-ry*fx

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bm = bmesh.new()
    verts = []
    for base in [start, end]:
        for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            verts.append(bm.verts.new((
                base[0]+rx*hw*sx+upx*hh*sy,
                base[1]+ry*hw*sx+upy*hh*sy,
                base[2]+rz*hw*sx+upz*hh*sy,
            )))
    v = verts
    for f in [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6),
              (3, 0, 4, 7), (0, 3, 2, 1), (4, 5, 6, 7)]:
        bm.faces.new([v[i] for i in f])
    bm.to_mesh(mesh); bm.free()
    return obj


# ============================================================
# v1 helpers — verification (validated in prior sessions)
# ============================================================

def verify_bounds(name):
    """Print and return world-space bounding box."""
    # matrix_world is depsgraph-evaluated: without an update, objects whose
    # .location was just set (e.g. place_copies output) report the stale
    # pre-move matrix (measured on Blender 5.1.1).
    bpy.context.view_layer.update()
    obj = bpy.data.objects[name]
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    b = {
        'x': (min(v.x for v in vs), max(v.x for v in vs)),
        'y': (min(v.y for v in vs), max(v.y for v in vs)),
        'z': (min(v.z for v in vs), max(v.z for v in vs)),
    }
    print(f"{name}: X[{b['x'][0]:.4f},{b['x'][1]:.4f}]"
          f" Y[{b['y'][0]:.4f},{b['y'][1]:.4f}]"
          f" Z[{b['z'][0]:.4f},{b['z'][1]:.4f}]")
    return b


def verify_overlap(name_a, name_b, axis='z', min_overlap=0.005):
    """Confirm two parts physically overlap on the given axis."""
    a = verify_bounds(name_a)
    b = verify_bounds(name_b)
    overlap = min(a[axis][1], b[axis][1]) - max(a[axis][0], b[axis][0])
    ok = overlap >= min_overlap
    print(f"  {name_a} <-> {name_b} [{axis.upper()}]: "
          f"{'OK' if ok else 'GAP WARNING'} ({overlap:.4f}m)")
    return overlap


def finalize(name):
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    bpy.ops.object.shade_smooth()
    bpy.ops.object.select_all(action='DESELECT')
    return obj


def audit_all():
    """Final check — all parts should have rotation (0,0,0) and scale (1,1,1)."""
    meshes = sorted([o for o in bpy.data.objects if o.type == 'MESH'],
                    key=lambda o: o.name)
    all_ok = True
    for obj in meshes:
        rot = tuple(round(c, 3) for c in obj.rotation_euler)
        scl = tuple(round(c, 3) for c in obj.scale)
        ok = rot == (0.0, 0.0, 0.0) and scl == (1.0, 1.0, 1.0)
        if not ok:
            all_ok = False
        print(f"  [{'OK' if ok else '!!'}] {obj.name:30s} rot={rot} scl={scl}")
    print(f"\nAll transforms clean: {all_ok}")
    return all_ok


# ============================================================
# v2 helpers — detail toolbox (Rules 6-10)
# ============================================================

def add_bevel(obj, width=0.003, segments=2, angle_deg=40):
    """Rule 6 — angle-limited bevel, applied. Scale must already be applied."""
    mod = obj.modifiers.new("Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(angle_deg)
    mod.miter_outer = 'MITER_ARC'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def panel_recess(obj, near_point, inset=0.01, depth=0.005):
    """Rule 7 — inset the face whose center is nearest to near_point (world)
    and sink it along -normal. Use +normal translate for a raised panel."""
    bpy.context.view_layer.update()  # matrix_world is stale after an API move
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    target = obj.matrix_world.inverted() @ Vector(near_point)
    face = min(bm.faces, key=lambda f: (f.calc_center_median() - target).length)
    bmesh.ops.inset_region(bm, faces=[face], thickness=inset, use_even_offset=True)
    bmesh.ops.translate(bm, verts=list(face.verts), vec=-face.normal * depth)
    bm.to_mesh(obj.data); bm.free()


def place_copies(src, positions):
    """Rule 8 — explicit-loop placement of repeated hardware (bolts, rivets)."""
    out = []
    for i, p in enumerate(positions):
        dup = src.copy(); dup.data = src.data.copy()
        dup.name = f"{src.name}_{i:02d}"
        dup.location = p
        bpy.context.collection.objects.link(dup)
        out.append(dup)
    return out


def make_cable(name, points, radius=0.006):
    """Rule 8 — Bezier curve through explicit points, beveled, converted to mesh."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.bevel_depth = radius; cu.bevel_resolution = 3; cu.resolution_u = 12
    # Closed tube: without fill caps the converted mesh has two open end rings
    # (boundary_edges=20 at the integrity gate, measured on Blender 5.1.1).
    cu.use_fill_caps = True
    obj = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    # Fill caps convert as unwelded discs (duplicate ring verts + boundary
    # edges at the gate, Blender 5.1.1) — weld to close the tube.
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.to_mesh(obj.data); bm.free()
    return obj


def boolean_cut(target, cutter, op='DIFFERENCE'):
    """Rule 9 — EXACT boolean with mandatory cleanup. Cutter must overshoot
    every cut surface by >=1mm; scale applied on both operands first."""
    mod = target.modifiers.new("Bool", 'BOOLEAN')
    mod.operation = op; mod.solver = 'EXACT'; mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bm = bmesh.new(); bm.from_mesh(target.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bm.to_mesh(target.data); bm.free()


def ellipse_profile(rx, ry, n=12):
    """Rule 10 — 2D ellipse profile for loft_profile."""
    return [(math.cos(2*math.pi*i/n)*rx, math.sin(2*math.pi*i/n)*ry)
            for i in range(n)]


def rounded_rect_profile(hw, hh, r=0.004, seg=2):
    """Rule 10 — 2D rounded-rectangle profile for loft_profile."""
    pts = []
    for cx, cy, a0 in [(hw-r, hh-r, 0), (-(hw-r), hh-r, 90),
                       (-(hw-r), -(hh-r), 180), (hw-r, -(hh-r), 270)]:
        for k in range(seg+1):
            a = math.radians(a0 + 90*k/seg)
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts


def loft_profile(name, profile, path, scales=None, close_caps=True):
    """Rule 10 — sweep a 2D profile (local XY) through 3D path points with
    per-point uniform scale. The technique for grips, stocks, handles, bottles.
    Run verify_mesh_integrity after every loft."""
    if scales is None:
        scales = [1.0]*len(path)
    mesh = bpy.data.meshes.new(name); obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new(); rings = []; n = len(profile)
    for i, p in enumerate(path):
        p = Vector(p)
        fwd = (Vector(path[min(i+1, len(path)-1)]) -
               Vector(path[max(i-1, 0)])).normalized()
        up = Vector((0, 0, 1)) if abs(fwd.z) < 0.99 else Vector((1, 0, 0))
        right = fwd.cross(up).normalized(); up = right.cross(fwd).normalized()
        rings.append([bm.verts.new(p + (right*px + up*py)*scales[i])
                      for px, py in profile])
    for a, b in zip(rings, rings[1:]):
        for j in range(n):
            bm.faces.new([a[j], a[(j+1) % n], b[(j+1) % n], b[j]])
    if close_caps:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh); bm.free()
    # Active and selected, like make_beam and make_cable, so finalize(name)
    # acts on the loft.
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    return obj


# ============================================================
# v2 helpers — bake pass (Rule 11)
# ============================================================

def smart_uv(obj, angle=66, margin=0.02):
    """Rule 11 — Smart UV Project the whole object (acceptable for hard surface)."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_map(high, low, kind='NORMAL', size=2048, ray=0.01, path=None):
    """Rule 11 — bake kind ('NORMAL' or 'AO') from high onto low's UVs.
    Low MUST have UVs (smart_uv first). Blender bakes OpenGL-convention (Y+)
    tangent normals; DayZ _nohq is DirectX-convention (Y-), so invert the
    green channel before export (SKILL.md Rule 11)."""
    scene = bpy.context.scene
    img = bpy.data.images.new(f"{low.name}_{kind.lower()}", size, size, alpha=False)
    if kind == 'NORMAL':
        img.colorspace_settings.name = 'Non-Color'
    if not low.data.materials:
        m = bpy.data.materials.new(f"{low.name}_bake"); m.use_nodes = True
        low.data.materials.append(m)
    mat = low.data.materials[0]; mat.use_nodes = True
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = img; mat.node_tree.nodes.active = node
    scene.render.engine = 'CYCLES'
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.max_ray_distance = ray
    scene.render.bake.cage_extrusion = ray * 0.5
    bpy.ops.object.select_all(action='DESELECT')
    high.select_set(True); low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.bake(type=kind)
    if path:
        img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    return img


# ============================================================
# v2 helpers — integrity gate
# ============================================================

def verify_mesh_integrity(name, require_closed=True, allow_ngons=False):
    """The broken-geometry gate. Run after every boolean, every modifier apply,
    every loft, and once per part at finalization."""
    obj = bpy.data.objects[name]
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    r = {
        'non_manifold_edges': sum(1 for e in bm.edges
                                  if not e.is_manifold and not e.is_boundary),
        'boundary_edges':     sum(1 for e in bm.edges if e.is_boundary),
        'loose_verts':        sum(1 for v in bm.verts if not v.link_edges),
        'zero_area_faces':    sum(1 for f in bm.faces if f.calc_area() < 1e-9),
        'ngons':              sum(1 for f in bm.faces if len(f.verts) > 4),
    }
    n_before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)  # copy only
    r['duplicate_verts'] = n_before - len(bm.verts)
    bm.free()

    fails = []
    if r['non_manifold_edges']:
        fails.append('non-manifold')
    if r['duplicate_verts']:
        fails.append('duplicate verts')
    if r['zero_area_faces']:
        fails.append('degenerate faces')
    if r['loose_verts']:
        fails.append('loose verts')
    if require_closed and r['boundary_edges']:
        fails.append('open boundary')
    # Ngons report as a warning, never a failure: EXACT booleans on flat faces
    # emit ring ngons as normal output (measured on Blender 5.1.1).
    # Shading/decimation risk applies to curved surfaces only — judged at the
    # visual checkpoint, not by this gate.
    warns = []
    if not allow_ngons and r['ngons']:
        warns.append('ngons')

    status = 'OK' if not fails else 'FAIL: ' + ', '.join(fails)
    if warns:
        status += ' (warn: ' + ', '.join(warns) + ')'
    print(f"{name}: [{status}] {r}")
    return (len(fails) == 0), r
