# Chart source: artist-style cuts = per-shell dominant-view normal clustering.
# For each connected shell, k-means cluster face normals (k chosen by normal
# spread), then split clusters into connected components -> charts. Mimics how an
# artist unwraps a body panel: one island per "view side" of each physical piece
# (top of the fender pair, its underside...), swallowing stretch on wrap edges.
# Shells where clustering shatters into many fragments (helicoids: springs) fall
# back to normal-cone region growing (strip-friendly).
import math, heapq
from collections import defaultdict
from mathutils import Vector


def _kmeans_normals(faces, normals, areas, k, iters=15):
    # seeds: farthest-point on normals
    seeds = [max(faces, key=lambda fi: areas[fi])]
    while len(seeds) < k:
        far = max(faces, key=lambda fi: min((normals[fi] - normals[s]).length for s in seeds))
        seeds.append(far)
    cents = [normals[s].copy() for s in seeds]
    assign = {}
    for _ in range(iters):
        changed = False
        for fi in faces:
            best = min(range(k), key=lambda c: (normals[fi] - cents[c]).length)
            if assign.get(fi) != best:
                assign[fi] = best
                changed = True
        for c in range(k):
            acc = Vector((0, 0, 0))
            tot = 0.0
            for fi in faces:
                if assign[fi] == c:
                    acc += normals[fi] * areas[fi]
                    tot += areas[fi]
            if tot > 0 and acc.length > 1e-12:
                cents[c] = acc.normalized()
        if not changed:
            break
    return assign


def _spread(faces, normals, areas):
    acc = Vector((0, 0, 0))
    for fi in faces:
        acc += normals[fi] * areas[fi]
    if acc.length < 1e-12:
        return math.pi
    m = acc.normalized()
    dev = 0.0
    for fi in faces:
        if normals[fi].length > 1e-9:
            a = normals[fi].angle(m)
            if a > dev:
                dev = a
    return dev


def _grow_cone(faces, normals, areas, adj, chart, start_cid, cone):
    cid = start_cid
    faceset = set(faces)
    order = sorted(faces, key=lambda i: -areas[i])
    for seed in order:
        if chart[seed] != -1:
            continue
        chart[seed] = cid
        acc = normals[seed] * max(areas[seed], 1e-9)
        heap = []
        cn = acc.normalized()
        for (nj, ei) in adj[seed]:
            if nj in faceset and chart[nj] == -1:
                heapq.heappush(heap, (-normals[nj].dot(cn), nj))
        while heap:
            _, fi = heapq.heappop(heap)
            if chart[fi] != -1:
                continue
            cn = acc.normalized()
            if cn.length > 0 and normals[fi].length > 1e-9 and normals[fi].angle(cn) > cone:
                continue
            chart[fi] = cid
            acc = acc + normals[fi] * max(areas[fi], 1e-9)
            cn = acc.normalized()
            for (nj, ei) in adj[fi]:
                if nj in faceset and chart[nj] == -1:
                    heapq.heappush(heap, (-normals[nj].dot(cn), nj))
        cid += 1
    return cid


def view_charts(nfaces, normals, areas, adj, shell, ns, cone_fallback=math.radians(100),
                frag_limit=6):
    """Returns (chart list, next_cid). Charts are contiguous ints from 0."""
    chart = [-1] * nfaces
    cid = 0
    shells = defaultdict(list)
    for fi in range(nfaces):
        shells[shell[fi]].append(fi)
    for s, faces in shells.items():
        dev = _spread(faces, normals, areas)
        if dev < math.radians(70) or len(faces) < 12:
            k = 1
        elif dev < math.radians(125):
            k = 2
        else:
            k = 3
        if k == 1:
            for fi in faces:
                chart[fi] = cid
            cid += 1
            continue
        assign = _kmeans_normals(faces, normals, areas, k)
        # split clusters into connected components
        comp_of = {}
        ncomp = 0
        faceset = set(faces)
        for fi in faces:
            if fi in comp_of:
                continue
            stack = [fi]
            comp_of[fi] = ncomp
            while stack:
                cur = stack.pop()
                for (nj, ei) in adj[cur]:
                    if nj in faceset and nj not in comp_of and assign[nj] == assign[cur]:
                        comp_of[nj] = ncomp
                        stack.append(nj)
            ncomp += 1
        if ncomp > frag_limit:
            # helicoid / shattered shell: fall back to cone growing
            cid = _grow_cone(faces, normals, areas, adj, chart, cid, cone_fallback)
            continue
        # Cap charts per shell at k: keep the largest component of each cluster as
        # a core; every other component merges into the neighbor it shares the most
        # edges with (artist behavior: a fender's steep side patches belong
        # to the top view island, not to islands of their own).
        comp_faces = defaultdict(list)
        for fi in faces:
            comp_faces[comp_of[fi]].append(fi)
        comp_cluster = {ci: assign[fl[0]] for ci, fl in comp_faces.items()}
        cores = {}
        for c in set(comp_cluster.values()):
            comps_c = [ci for ci in comp_faces if comp_cluster[ci] == c]
            cores[c] = max(comps_c, key=lambda ci: sum(areas[fi] for fi in comp_faces[ci]))
        core_ids = set(cores.values())
        merged_into = {ci: ci for ci in comp_faces}
        def root(ci):
            while merged_into[ci] != ci:
                merged_into[ci] = merged_into[merged_into[ci]]
                ci = merged_into[ci]
            return ci
        pending = [ci for ci in comp_faces if ci not in core_ids]
        # iterate: merge pending comps into their strongest neighbor until stable
        for _ in range(len(pending) + 1):
            if not pending:
                break
            still = []
            for ci in pending:
                nb = defaultdict(float)
                for fi in comp_faces[ci]:
                    for (nj, ei) in adj[fi]:
                        if nj in faceset and root(comp_of[nj]) != root(ci):
                            nb[root(comp_of[nj])] += 1.0
                if nb:
                    merged_into[root(ci)] = max(nb, key=nb.get)
                else:
                    still.append(ci)
            pending = still
        finals = {}
        for ci in comp_faces:
            r = root(ci)
            if r not in finals:
                finals[r] = cid
                cid += 1
            for fi in comp_faces[ci]:
                chart[fi] = finals[r]
    return chart, cid
