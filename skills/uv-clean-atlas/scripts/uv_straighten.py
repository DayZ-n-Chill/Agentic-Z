# Boundary straightening: smooth each panel island's UV boundary loops (Taubin
# lambda/mu, kills triangulation jaggies, preserves arcs) and diffuse the capped
# displacement a few rings into the interior. No pins and no re-solve:
# resolve_with_pins() below is the earlier pinned-SLIM route, kept for reference
# and not called by the pipeline. Boundary loops are walked
# with the bmesh radial-walk, which passes junctions where 3+ islands meet
# (the naive vertex-degree walk rejects those loops - measured: 1 loop of ~30).
import bpy, bmesh
from collections import defaultdict


def _uv_shared(e, uv):
    if len(e.link_faces) != 2:
        return False
    f1, f2 = e.link_faces
    v1, v2 = e.verts

    def uvp(f, v):
        for lo in f.loops:
            if lo.vert == v:
                return lo[uv].uv
        return None

    a1, a2, b1, b2 = uvp(f1, v1), uvp(f1, v2), uvp(f2, v1), uvp(f2, v2)
    if None in (a1, a2, b1, b2):
        return False
    EPS = 1e-6
    return (a1 - b1).length < EPS and (a2 - b2).length < EPS


def straighten_boundaries(me, iters=12, lam=0.5, min_loop=8, rings=5):
    """Smooth the boundary loops of panel islands (60 faces or more, bbox aspect
    4 or less). Returns (loops smoothed, boundary corners displaced)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    uv = bm.loops.layers.uv.active

    boundary = {e.index: not _uv_shared(e, uv) for e in bm.edges}

    # Panel filter: straightening a THIN island (unwrapped spring/rail strip) smooths
    # each rail independently, decorrelates them and bowties the whole strip
    # (measured: ~6.9k offender faces from the springs alone). Only straighten
    # panel-like islands: enough faces and moderate bbox aspect.
    parent = list(range(len(bm.faces)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in bm.edges:
        if not boundary[e.index] and len(e.link_faces) == 2:
            r1, r2 = find(e.link_faces[0].index), find(e.link_faces[1].index)
            if r1 != r2:
                parent[r1] = r2
    isl_faces = defaultdict(int)
    isl_min = {}
    isl_max = {}
    for f in bm.faces:
        r = find(f.index)
        isl_faces[r] += 1
        for lo in f.loops:
            u, v = lo[uv].uv
            mn = isl_min.get(r)
            mx = isl_max.get(r)
            isl_min[r] = (u, v) if mn is None else (min(mn[0], u), min(mn[1], v))
            isl_max[r] = (u, v) if mx is None else (max(mx[0], u), max(mx[1], v))
    panel_isl = set()
    for r, cnt in isl_faces.items():
        w = isl_max[r][0] - isl_min[r][0]
        h = isl_max[r][1] - isl_min[r][1]
        aspect = max(w, h) / max(min(w, h), 1e-9)
        if cnt >= 60 and aspect <= 4.0:
            panel_isl.add(r)

    def next_boundary_loop(l):
        # advance around l.link_loop_next.vert inside the island until the next
        # boundary edge is hit; returns the loop whose edge is that boundary edge
        cur = l.link_loop_next
        for _ in range(64):
            if boundary[cur.edge.index]:
                return cur
            rad = cur.link_loop_radial_next
            if rad is cur:  # mesh border
                return cur
            cur = rad.link_loop_next
        return None

    def lkey(lo):
        # loop.index is not guaranteed initialized and id() recycles: corner key
        return (lo.face.index, lo.vert.index)

    visited = set()
    n_loops = 0
    n_pinned = 0
    disp = {}  # (island_root, vert_index) -> (old_uv, delta)
    for f in bm.faces:
        if find(f.index) not in panel_isl:
            continue
        for l in f.loops:
            if not boundary[l.edge.index] or lkey(l) in visited:
                continue
            # walk one closed boundary loop of this island
            chain = []
            cur = l
            ok = False
            for _ in range(len(bm.edges) + 4):
                if cur is None:
                    break
                if lkey(cur) in visited:
                    ok = (lkey(cur) == lkey(l) and len(chain) >= min_loop)
                    break
                visited.add(lkey(cur))
                chain.append(cur)
                cur = next_boundary_loop(cur)
            if not ok or len(chain) < min_loop:
                continue
            # smooth the ordered corner UVs — Taubin lambda/mu (shrink-free):
            # pure closed-curve Laplacian is curve-shortening flow and collapses
            # the boundary into the island (measured: 605k SAT pairs)
            orig = [c[uv].uv.copy() for c in chain]
            pts = [p.copy() for p in orig]
            n = len(pts)
            MU = -0.53
            for _ in range(iters):
                for step in (lam, MU):
                    new = [None] * n
                    for j in range(n):
                        lap = (pts[(j - 1) % n] + pts[(j + 1) % n]) * 0.5 - pts[j]
                        new[j] = pts[j] + lap * step
                    pts = new
            # per-loop safety: a smoothed boundary that self-intersects or changes
            # area forces SLIM to fold the interior (measured: 1302 SAT pairs at
            # concave necks). Reject those loops instead of writing them.
            def _shoelace(ps):
                s = 0.0
                for j in range(len(ps)):
                    a, b = ps[j], ps[(j + 1) % len(ps)]
                    s += a[0] * b[1] - b[0] * a[1]
                return 0.5 * s
            def _seg_int(p1, p2, p3, p4):
                d1 = (p2[0]-p1[0], p2[1]-p1[1]); d2 = (p4[0]-p3[0], p4[1]-p3[1])
                den = d1[0]*d2[1] - d1[1]*d2[0]
                if abs(den) < 1e-18:
                    return False
                t = ((p3[0]-p1[0])*d2[1] - (p3[1]-p1[1])*d2[0]) / den
                s = ((p3[0]-p1[0])*d1[1] - (p3[1]-p1[1])*d1[0]) / den
                return 1e-9 < t < 1 - 1e-9 and 1e-9 < s < 1 - 1e-9
            def _self_intersects(ps):
                m = len(ps)
                for i in range(m):
                    a1, a2 = ps[i], ps[(i + 1) % m]
                    for j in range(i + 2, m):
                        if i == 0 and j == m - 1:
                            continue
                        if _seg_int(a1, a2, ps[j], ps[(j + 1) % m]):
                            return True
                return False
            a0 = _shoelace(orig)
            a1_ = _shoelace(pts)
            ok_area = abs(a0) > 1e-14 and (a1_ / a0) > 0 and 0.85 < abs(a1_ / a0) < 1.15
            if not ok_area or _self_intersects(pts):
                continue
            # displacement per boundary corner, capped to a fraction of the LOCAL
            # boundary spacing: thin rims (hole frames 1-2 quads wide) invert when
            # a corner travels past its neighbors (measured: 215 SAT pairs uncapped)
            for j, c in enumerate(chain):
                key = (find(c.face.index), c.vert.index)
                delta = pts[j] - orig[j]
                local = min((orig[j] - orig[(j - 1) % n]).length,
                            (orig[j] - orig[(j + 1) % n]).length)
                cap = 0.35 * local
                if delta.length > cap and delta.length > 1e-12:
                    delta = delta * (cap / delta.length)
                disp[key] = (orig[j], delta)
                n_pinned += 1
            n_loops += 1

    # Interior decay: diffuse boundary displacements a few rings inward per island
    # (no solver, no pins, no repack — displacement bounded by the jaggy amplitude,
    # decays to zero, cannot explode the layout the way a pinned re-solve can).
    isl_disp = defaultdict(dict)
    for (r, vi), (old, delta) in disp.items():
        isl_disp[r][vi] = delta
    for r, bdisp in isl_disp.items():
        faces_r = [f for f in bm.faces if find(f.index) == r]
        verts_r = set()
        vadj = defaultdict(set)
        for f in faces_r:
            vs = [v.index for v in f.verts]
            verts_r.update(vs)
            for i in range(len(vs)):
                vadj[vs[i]].add(vs[(i + 1) % len(vs)])
                vadj[vs[(i + 1) % len(vs)]].add(vs[i])
        d = dict(bdisp)
        for _ in range(rings):
            newd = {}
            for v in verts_r:
                if v in bdisp:
                    continue
                acc = None
                cnt = 0
                for nv in vadj[v]:
                    if nv in d:
                        acc = d[nv].copy() if acc is None else acc + d[nv]
                        cnt += 1
                if cnt:
                    newd[v] = acc * (0.72 / cnt)
            d.update(newd)
        for f in faces_r:
            for lo in f.loops:
                delta = d.get(lo.vert.index)
                if delta is not None:
                    lo[uv].uv = lo[uv].uv + delta

    bm.to_mesh(me)
    bm.free()
    me.update()
    return n_loops, n_pinned


def resolve_with_pins():
    # no_flip is OFF by default and SLIM's 10 default iterations do not converge
    # against hard pin constraints — flipped interior triangles survive (measured:
    # 1302 SAT pairs). Guarantee injectivity and give the solver room.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', fill_holes=True, correct_aspect=True,
                      margin=0.001, no_flip=True, iterations=60)
    bpy.ops.object.mode_set(mode='OBJECT')


def clear_pins(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    for f in bm.faces:
        for lo in f.loops:
            lo[uv].pin_uv = False
    bm.to_mesh(me)
    bm.free()
    me.update()
