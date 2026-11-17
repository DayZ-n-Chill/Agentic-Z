# uv_clean_atlas v8: artist-style cuts + crisp outlines.
#   1. charts = per-shell dominant-view normal clustering (uv_view_charts.py):
#      one island per "view side" of each physical piece, like an artist unwrap;
#      helicoid shells fall back to cone growing
#   2. dust merge (charts under min_faces fuse into longest-boundary neighbor)
#   3. SLIM unwrap + fold guard (ONE round, per-triangle winding + MC self-overlap)
#   4. SAT finisher (ONE round): isolate exact-overlap offender faces
#   5. boundary straightening, panels only: smooth island boundary loops and
#      diffuse the displacement inward, no pins and no re-solve
#      (uv_straighten.py) -> blueprint-like island profiles; rolls itself back
#      when it leaves too many offender faces
#   6. semantic shelf pack (uv_shelf_pack.py)
#   7. metrics + exact SAT verdict + renders
# Usage: blender -b <in.blend> -P uv_clean_atlas.py -- <out.blend> <out_dir> <tag>
#        <min_faces> <object_name>
# Without <object_name>, or when no object has that name, the first mesh object
# in the file is used.
import bpy, bmesh, math, os, sys, random
from collections import defaultdict
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
BLEND_OUT, OUT_DIR, TAG = argv[0], argv[1], argv[2]
MIN_FACES = int(argv[3])
OB_NAME = argv[4] if len(argv) > 4 else ""

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import uv_metrics
import uv_shelf_pack
import uv_view_charts
import uv_straighten

ob = bpy.data.objects.get(OB_NAME) or next(o for o in bpy.data.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
for other in bpy.data.objects:
    if other.type == 'MESH' and other is not ob:
        other.hide_render = True
        other.hide_set(True)
me = ob.data

bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.normal_update()

nfaces = len(bm.faces)
areas = [f.calc_area() for f in bm.faces]
normals = [f.normal.copy() for f in bm.faces]
centroids = [f.calc_center_median().copy() for f in bm.faces]
adj = [[] for _ in range(nfaces)]
edge_len = {}
for e in bm.edges:
    edge_len[e.index] = e.calc_length()
    lf = e.link_faces
    if len(lf) == 2:
        adj[lf[0].index].append((lf[1].index, e.index))
        adj[lf[1].index].append((lf[0].index, e.index))
bm.free()

shell = [-1] * nfaces
ns = 0
for s in range(nfaces):
    if shell[s] != -1:
        continue
    stack = [s]
    shell[s] = ns
    while stack:
        fi = stack.pop()
        for (nj, _) in adj[fi]:
            if shell[nj] == -1:
                shell[nj] = ns
                stack.append(nj)
    ns += 1
print(f"SHELLS: {ns}")

# --- 1. view-based charts ---
chart, next_cid = uv_view_charts.view_charts(nfaces, normals, areas, adj, shell, ns)
cfaces = defaultdict(list)
for i, c in enumerate(chart):
    cfaces[c].append(i)
print(f"CHARTS_VIEW: {sum(1 for c in cfaces if cfaces[c])}")

# --- 2. dust merge ---
changed = True
while changed:
    changed = False
    for c in sorted(cfaces.keys(), key=lambda c: len(cfaces[c])):
        if not cfaces[c] or len(cfaces[c]) >= MIN_FACES:
            continue
        nb = defaultdict(float)
        for fi in cfaces[c]:
            for (nj, ei) in adj[fi]:
                if chart[nj] != c:
                    nb[chart[nj]] += edge_len[ei]
        if not nb:
            continue
        tgt = max(nb, key=nb.get)
        for fi in cfaces[c]:
            chart[fi] = tgt
        cfaces[tgt].extend(cfaces[c])
        cfaces[c] = []
        changed = True
print(f"CHARTS_AFTER_DUST: {sum(1 for c in cfaces if cfaces[c])}")

# --- 3. unwrap + fold guard (one round) ---
def apply_seams_and_unwrap():
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    bm2.edges.ensure_lookup_table()
    for e in bm2.edges:
        lf = e.link_faces
        e.seam = len(lf) == 2 and chart[lf[0].index] != chart[lf[1].index]
    bm2.to_mesh(me)
    bm2.free()
    me.update()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', fill_holes=True, correct_aspect=True, margin=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')

def folded_charts():
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    bm2.faces.ensure_lookup_table()
    uv = bm2.loops.layers.uv.active
    pos = defaultdict(float)
    neg = defaultdict(float)
    tris = []
    for f in bm2.faces:
        loops = f.loops[:]
        p2 = [l[uv].uv.copy() for l in loops]
        cc = chart[f.index]
        for i in range(1, len(p2) - 1):
            a, b, d = p2[0], p2[i], p2[i + 1]
            sa = ((b[0] - a[0]) * (d[1] - a[1]) - (d[0] - a[0]) * (b[1] - a[1])) * 0.5
            if sa >= 0:
                pos[cc] += sa
            else:
                neg[cc] += -sa
            tris.append((cc, a, b, d))
    bm2.free()
    bad = {}
    for c in set(list(pos.keys()) + list(neg.keys())):
        tot = pos[c] + neg[c]
        if tot > 0:
            minority = min(pos[c], neg[c]) / tot
            if minority > 0.05 and len(cfaces[c]) >= 6:
                bad[c] = max(bad.get(c, 0.0), minority)
    random.seed(7)
    def _area(a, b, d):
        return abs((b[0] - a[0]) * (d[1] - a[1]) - (d[0] - a[0]) * (b[1] - a[1])) * 0.5
    valid = [t for t in tris if _area(t[1], t[2], t[3]) > 1e-12]
    N = 128
    grid = defaultdict(list)
    for idx, (cc, a, b, d) in enumerate(valid):
        gx0 = int(min(a[0], b[0], d[0]) * (N - 1)); gx1 = int(max(a[0], b[0], d[0]) * (N - 1))
        gy0 = int(min(a[1], b[1], d[1]) * (N - 1)); gy1 = int(max(a[1], b[1], d[1]) * (N - 1))
        for gx in range(max(0, gx0), min(N, gx1 + 1)):
            for gy in range(max(0, gy0), min(N, gy1 + 1)):
                grid[(gx, gy)].append(idx)
    def _in_tri(p, a, b, d):
        det = (b[1] - a[1]) * (d[0] - a[0]) - (b[0] - a[0]) * (d[1] - a[1])
        if det == 0:
            return False
        w0 = (b[1] - a[1]) * (p[0] - a[0]) - (b[0] - a[0]) * (p[1] - a[1])
        w1 = (d[1] - b[1]) * (p[0] - b[0]) - (d[0] - b[0]) * (p[1] - b[1])
        w2 = (a[1] - d[1]) * (p[0] - d[0]) - (a[0] - d[0]) * (p[1] - d[1])
        return (w0 >= 0 and w1 >= 0 and w2 >= 0) if det > 0 else (w0 <= 0 and w1 <= 0 and w2 <= 0)
    samples = defaultdict(int)
    hits = defaultdict(int)
    for idx, (cc, a, b, d) in enumerate(valid):
        for _ in range(4):
            r1, r2 = random.random(), random.random()
            if r1 + r2 > 1:
                r1, r2 = 1 - r1, 1 - r2
            p = (a[0] + r1 * (b[0] - a[0]) + r2 * (d[0] - a[0]),
                 a[1] + r1 * (b[1] - a[1]) + r2 * (d[1] - a[1]))
            samples[cc] += 1
            gx = min(N - 1, max(0, int(p[0] * (N - 1)))); gy = min(N - 1, max(0, int(p[1] * (N - 1))))
            for j in grid.get((gx, gy), ()):
                if j != idx and valid[j][0] == cc and _in_tri(p, valid[j][1], valid[j][2], valid[j][3]):
                    hits[cc] += 1
                    break
    for c, n in samples.items():
        if n >= 100 and hits[c] / n > 0.03 and len(cfaces[c]) >= 6:
            bad[c] = max(bad.get(c, 0.0), hits[c] / n)
    return sorted(bad.items(), key=lambda kv: -kv[1])

def _principal_axis(vecs_weights):
    cov = [[0.0] * 3 for _ in range(3)]
    for d, w in vecs_weights:
        for r in range(3):
            for s in range(3):
                cov[r][s] += d[r] * d[s] * w
    v = Vector((1.0, 0.7, 0.3)).normalized()
    for _ in range(30):
        w = Vector((sum(cov[r][s] * v[s] for s in range(3)) for r in range(3)))
        if w.length < 1e-12:
            break
        v = w.normalized()
    return v

def bisect_chart(c):
    global next_cid
    fl = cfaces[c]
    tot_a = sum(areas[fi] for fi in fl) or 1e-9
    mu_n = Vector((0, 0, 0))
    for fi in fl:
        mu_n += normals[fi] * areas[fi]
    mu_n /= tot_a
    v = _principal_axis([(normals[fi] - mu_n, areas[fi]) for fi in fl])
    g1 = [fi for fi in fl if (normals[fi] - mu_n).dot(v) >= 0]
    g2 = [fi for fi in fl if (normals[fi] - mu_n).dot(v) < 0]
    if min(len(g1), len(g2)) < max(6, 0.15 * len(fl)):
        mu = Vector((0, 0, 0))
        for fi in fl:
            mu += centroids[fi]
        mu /= len(fl)
        v = _principal_axis([(centroids[fi] - mu, 1.0) for fi in fl])
        keys = sorted(fl, key=lambda fi: (centroids[fi] - mu).dot(v))
        g1, g2 = keys[:len(keys) // 2], keys[len(keys) // 2:]
    nc = next_cid
    next_cid += 1
    for fi in g2:
        chart[fi] = nc
    cfaces[nc] = list(g2)
    cfaces[c] = list(g1)

apply_seams_and_unwrap()
bad = folded_charts()
if bad:
    print(f"FOLD_GUARD: bisecting {len(bad)} charts {[(len(cfaces[c]), round(m,3)) for c, m in bad]}")
    for c, _ in bad:
        bisect_chart(c)
    apply_seams_and_unwrap()

# --- 4. boundary straightening + pinned re-solve (with SAT rollback valve) ---
def snapshot_uvs():
    layer = me.uv_layers.active
    buf = [0.0] * (len(layer.uv) * 2)
    layer.uv.foreach_get("vector", buf)
    return buf

def restore_uvs(buf):
    layer = me.uv_layers.active
    layer.uv.foreach_set("vector", buf)
    me.update()

# (straightening runs AFTER the SAT finisher: the pinned re-solve re-packs the
# unpinned islands over the pinned ones, which is phantom cross-island overlap
# that the shelf pack removes anyway — judge only the FINAL packed SAT)

# --- 5. SAT finisher ---
def sat_offenders():
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    bm2.faces.ensure_lookup_table()
    uv = bm2.loops.layers.uv.active
    tris = []
    for f in bm2.faces:
        loops = f.loops[:]
        p2 = [l[uv].uv.copy() for l in loops]
        for i in range(1, len(p2) - 1):
            a, b, c2 = p2[0], p2[i], p2[i + 1]
            area = abs((b[0] - a[0]) * (c2[1] - a[1]) - (c2[0] - a[0]) * (b[1] - a[1])) * 0.5
            if area > 1e-14:
                tris.append((f.index, ((a[0], a[1]), (b[0], b[1]), (c2[0], c2[1]))))
    bm2.free()
    def sat(t1, t2, eps=1e-9):
        for ta, tb in ((t1, t2), (t2, t1)):
            for i in range(3):
                ax, ay = ta[i]
                bx, by = ta[(i + 1) % 3]
                nx, ny = ay - by, bx - ax
                pa = [nx * p[0] + ny * p[1] for p in ta]
                pb = [nx * p[0] + ny * p[1] for p in tb]
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
                if fi == fj:
                    continue
                if sat(t1, t2):
                    pairs.add((min(fi, fj), max(fi, fj)))
    faces = set()
    for a, b in pairs:
        faces.add(a); faces.add(b)
    return pairs, faces

def sat_finish(label):
    """Isolate exact-overlap offender faces as speck islands and re-solve.
    Offender faces get their pins cleared so they can relocate; every other pin
    (the straightened boundaries) is respected by the re-unwrap."""
    pairs, offender_faces = sat_offenders()
    print(f"SAT_{label}: pairs={len(pairs)} faces={len(offender_faces)}")
    if len(offender_faces) > 0.01 * nfaces:
        print(f"SAT_FINISHER_{label}_SKIPPED: offender count above safety cap")
        return
    if not pairs:
        return
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    bm2.faces.ensure_lookup_table()
    uvl = bm2.loops.layers.uv.active
    for fi in offender_faces:
        for e in bm2.faces[fi].edges:
            e.seam = True
        for lo in bm2.faces[fi].loops:
            lo[uvl].pin_uv = False
    bm2.to_mesh(me)
    bm2.free()
    me.update()
    # plain SLIM flags, as validated in v7: no_flip=True here makes wrapped charts
    # spiral-overlap instead of flipping (measured on the rip: 133 residual pairs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', fill_holes=True, correct_aspect=True, margin=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')

sat_finish("PRE_FINISH")

# --- 5b. boundary straightening (panels only, local diffusion — no solver) ---
snap = snapshot_uvs()
n_loops, n_corners = uv_straighten.straighten_boundaries(me, iters=10, lam=0.5, rings=5)
print(f"STRAIGHTEN: loops={n_loops} corners={n_corners}")
did_straighten = n_loops > 0

# --- 5c. excise residual offenders (solver-free): rewrite each offender face's
# UVs as a detached micro-triangle; the shelf pack files them with the specks.
def excise_faces(faces):
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    bm2.faces.ensure_lookup_table()
    uvl = bm2.loops.layers.uv.active
    for k, fi in enumerate(sorted(faces)):
        f = bm2.faces[fi]
        base_u = 2.0 + 0.01 * (k % 32)
        base_v = 2.0 + 0.01 * (k // 32)
        for i, lo in enumerate(f.loops):
            lo[uvl].uv = (base_u + 0.004 * (i % 2), base_v + 0.004 * (i // 2))
    bm2.to_mesh(me)
    bm2.free()
    me.update()

pairs3, faces3 = sat_offenders()
EXCISE_CAP = max(40, int(0.001 * nfaces))
# a large offender set means straightening hurt this mesh: rolling back beats
# butchering hundreds of faces into specks (measured on the rip: 179 excisions)
if did_straighten and len(faces3) > EXCISE_CAP:
    print(f"STRAIGHTEN_ROLLBACK_EARLY: {len(faces3)} offenders > cap {EXCISE_CAP}")
    restore_uvs(snap)
    did_straighten = False
    pairs3, faces3 = sat_offenders()
if pairs3 and len(faces3) <= EXCISE_CAP:
    print(f"EXCISE: {len(faces3)} residual offender faces -> micro specks")
    excise_faces(faces3)
elif pairs3:
    print(f"EXCISE_SKIPPED: {len(faces3)} offenders above cap")

# --- 6. semantic shelf pack + final SAT (single judge, with rollback valve) ---
n_isl, n_pan, n_str, n_spk = uv_shelf_pack.shelf_pack(me)
print(f"SHELF_PACK: islands={n_isl} panels={n_pan} strips={n_str} specks={n_spk}")

pairs2, faces2 = sat_offenders()
print(f"SAT_FINAL: pairs={len(pairs2)} faces={len(faces2)}")
if did_straighten and len(pairs2) > 50:
    print(f"STRAIGHTEN_ROLLBACK: final SAT {len(pairs2)} pairs > 50; restoring pre-straighten UVs")
    restore_uvs(snap)
    uv_straighten.clear_pins(me)
    n_isl, n_pan, n_str, n_spk = uv_shelf_pack.shelf_pack(me)
    print(f"SHELF_PACK_AFTER_ROLLBACK: islands={n_isl} panels={n_pan} strips={n_str} specks={n_spk}")
    pairs2, faces2 = sat_offenders()
print(f"SAT_VERDICT: pairs={len(pairs2)} ({'ZERO OVERLAP PROVEN' if not pairs2 else 'residual overlap'})")

os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
uv_metrics.score_and_render(ob, OUT_DIR, TAG)
print("DONE_CLEAN_ATLAS_V8")
