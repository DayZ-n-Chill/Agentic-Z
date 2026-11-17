# Exact zero-overlap gate: SAT tri-tri over the active UV layer (grid-accelerated).
# MC has a ~0.06% noise floor; "zero overlap" is only provable with SAT pairs == 0.
# Triangles with a UV area of 1e-14 or less are skipped before pairing, so a pass
# does not cover collapsed faces. SAT_INPUT reports the totals and how many were
# filtered as collapsed or NaN; the gate exits 1 when nothing is left to test.
# Usage: blender -b <file.blend> -P sat_gate.py -- <object_name>
import bpy, bmesh, sys
from collections import defaultdict

OB_NAME = sys.argv[sys.argv.index("--") + 1]
ob = bpy.data.objects[OB_NAME]
bm = bmesh.new()
bm.from_mesh(ob.data)
bm.faces.ensure_lookup_table()
uv = bm.loops.layers.uv.active

tris = []
n_faces = len(bm.faces)
n_tris = n_nan_tris = n_collapsed_tris = 0
collapsed_faces = 0  # faces none of whose triangles entered the test
for f in bm.faces:
    loops = f.loops[:]
    p2 = [l[uv].uv.copy() for l in loops]
    kept = 0
    for i in range(1, len(p2) - 1):
        a, b, c = p2[0], p2[i], p2[i + 1]
        n_tris += 1
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * 0.5
        if area != area:  # NaN UVs give a NaN area, which the filter below also drops
            n_nan_tris += 1
            continue
        if area > 1e-14:
            tris.append((f.index, ((a[0], a[1]), (b[0], b[1]), (c[0], c[1]))))
            kept += 1
        else:
            n_collapsed_tris += 1
    if kept == 0:
        collapsed_faces += 1
bm.free()

# SAT = 0 only covers the triangles that entered the test, so publish what was filtered.
print(f"SAT_INPUT: faces={n_faces} tris={n_tris} tested={len(tris)} "
      f"collapsed_tris={n_collapsed_tris} nan_tris={n_nan_tris} "
      f"collapsed_faces={collapsed_faces}/{n_faces}")
if not tris:
    print("SAT_GATE_FAIL: no triangle with a valid, non-zero UV area is left to test "
          "(the UV layer is empty, all NaN or fully collapsed)")
    sys.exit(1)

def sat_tri_overlap(t1, t2, eps=1e-9):
    for tri_a, tri_b in ((t1, t2), (t2, t1)):
        for i in range(3):
            ax, ay = tri_a[i]
            bx, by = tri_a[(i + 1) % 3]
            nx, ny = ay - by, bx - ax
            pa = [nx * p[0] + ny * p[1] for p in tri_a]
            pb = [nx * p[0] + ny * p[1] for p in tri_b]
            if max(pa) <= min(pb) + eps or max(pb) <= min(pa) + eps:
                return False
    return True

G = 200
us = [p[0] for _, t in tris for p in t]
vs = [p[1] for _, t in tris for p in t]
u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
du = (u1 - u0) or 1.0
dv = (v1 - v0) or 1.0
grid = defaultdict(list)
for ti, (fi, t) in enumerate(tris):
    gx0 = int((min(p[0] for p in t) - u0) / du * (G - 1))
    gx1 = int((max(p[0] for p in t) - u0) / du * (G - 1))
    gy0 = int((min(p[1] for p in t) - v0) / dv * (G - 1))
    gy1 = int((max(p[1] for p in t) - v0) / dv * (G - 1))
    for gx in range(gx0, gx1 + 1):
        for gy in range(gy0, gy1 + 1):
            grid[(gx, gy)].append(ti)

pairs = set()
checked = set()
for lst in grid.values():
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            ti, tj = lst[i], lst[j]
            key = (ti, tj) if ti < tj else (tj, ti)
            if key in checked:
                continue
            checked.add(key)
            fi, t1 = tris[ti]
            fj, t2 = tris[tj]
            # Same-face pairs are tested too: a folded (bowtie) face overlaps itself,
            # and fan triangles sharing an edge separate on that edge's axis.
            if sat_tri_overlap(t1, t2):
                pairs.add((min(fi, fj), max(fi, fj)))

faces = set()
for a, b in pairs:
    faces.add(a); faces.add(b)
print(f"SAT_PAIRS: {len(pairs)}  SAT_FACES: {len(faces)}  ({'ZERO OVERLAP PROVEN' if not pairs else 'residual overlap'})")

if faces:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    for fi in sorted(faces)[:40]:
        f = bm.faces[fi]
        c = f.calc_center_median()
        print(f"OFFENDER fi={fi} area3d={f.calc_area():.6f} nverts={len(f.verts)} "
              f"center=({c.x:.3f},{c.y:.3f},{c.z:.3f})")
    bm.free()
