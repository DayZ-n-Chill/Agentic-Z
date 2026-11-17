# Semantic shelf packer for legible "livery template" atlases. Replaces
# bpy.ops.uv.pack_islands (area-optimal but visually chaotic) with:
#   - per-island PCA rotation so the major axis is horizontal (blueprint look)
#   - big panels shelf-packed in rows, area-descending
#   - strips (aspect > STRIP_ASPECT) rotated vertical, downscaled to the panel
#     field height (strips pay the texel cost, panels keep theirs), right column
#   - specks (tiny area) clustered in a right-side grid
#   - shelf width iterated (dry-run) until the full block is roughly square,
#     then one translate pass and one global fit into [MARGIN, 1-MARGIN]
# Relative panel scale (texel density) is preserved.
import bmesh, math
from collections import defaultdict

STRIP_ASPECT = 6.0
SPECK_AREA_FRAC = 0.0008   # of total UV area
MARGIN = 0.008


def _islands(bm, uv):
    parent = list(range(len(bm.faces)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    EPS = 1e-6
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces
        v1, v2 = e.verts

        def uvp(f, v):
            for lo in f.loops:
                if lo.vert == v:
                    return lo[uv].uv
            return None

        a1, a2, b1, b2 = uvp(f1, v1), uvp(f1, v2), uvp(f2, v1), uvp(f2, v2)
        if None in (a1, a2, b1, b2):
            continue
        if (a1 - b1).length < EPS and (a2 - b2).length < EPS:
            r1, r2 = find(f1.index), find(f2.index)
            if r1 != r2:
                parent[r1] = r2
    groups = defaultdict(list)
    for f in bm.faces:
        groups[find(f.index)].append(f)
    return list(groups.values())


def _loops(faces, uv):
    for f in faces:
        for lo in f.loops:
            yield lo[uv]


def _pca_angle(pts):
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sxy = syy = 0.0
    for p in pts:
        dx, dy = p[0] - mx, p[1] - my
        sxx += dx * dx
        sxy += dx * dy
        syy += dy * dy
    return 0.5 * math.atan2(2.0 * sxy, sxx - syy), (mx, my)


def _rotate(faces, uv, ang, pivot):
    ca, sa = math.cos(ang), math.sin(ang)
    for luv in _loops(faces, uv):
        x, y = luv.uv[0] - pivot[0], luv.uv[1] - pivot[1]
        luv.uv[0] = ca * x - sa * y + pivot[0]
        luv.uv[1] = sa * x + ca * y + pivot[1]


def _bbox(faces, uv):
    xs, ys = [], []
    for luv in _loops(faces, uv):
        xs.append(luv.uv[0])
        ys.append(luv.uv[1])
    return min(xs), min(ys), max(xs), max(ys)


def _uv_area(faces, uv):
    tot = 0.0
    for f in faces:
        loops = f.loops[:]
        p = [lo[uv].uv for lo in loops]
        for i in range(1, len(p) - 1):
            a, b, c = p[0], p[i], p[i + 1]
            tot += abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * 0.5
    return tot


def shelf_pack(me):
    """Operates on me (object-mode Mesh). Returns (n_islands, n_panels, n_strips, n_specks)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.active

    islands = _islands(bm, uv)
    total_area = sum(_uv_area(fs, uv) for fs in islands) or 1e-12

    entries = []
    for fs in islands:
        pts = [tuple(luv.uv) for luv in _loops(fs, uv)]
        ang, cen = _pca_angle(pts)
        _rotate(fs, uv, -ang, cen)
        x0, y0, x1, y1 = _bbox(fs, uv)
        w, h = x1 - x0, y1 - y0
        if h > w:
            _rotate(fs, uv, math.pi / 2, ((x0 + x1) / 2, (y0 + y1) / 2))
            x0, y0, x1, y1 = _bbox(fs, uv)
            w, h = x1 - x0, y1 - y0
        area = _uv_area(fs, uv)
        aspect = (w / h) if h > 1e-9 else 999.0
        kind = 'panel'
        if area < SPECK_AREA_FRAC * total_area:
            kind = 'speck'
        elif aspect > STRIP_ASPECT:
            kind = 'strip'
        entries.append(dict(fs=fs, w=w, h=h, area=area, kind=kind))

    panels = sorted([e for e in entries if e['kind'] == 'panel'], key=lambda e: -e['area'])
    strips = sorted([e for e in entries if e['kind'] == 'strip'], key=lambda e: -max(e['w'], e['h']))
    specks = sorted([e for e in entries if e['kind'] == 'speck'], key=lambda e: -e['area'])

    # strips vertical (portrait) once, before measuring for the dry runs
    for e in strips:
        x0, y0, x1, y1 = _bbox(e['fs'], uv)
        _rotate(e['fs'], uv, math.pi / 2, ((x0 + x1) / 2, (y0 + y1) / 2))
        x0, y0, x1, y1 = _bbox(e['fs'], uv)
        e['w'], e['h'] = x1 - x0, y1 - y0

    total_panel_area = sum(e['area'] for e in panels) or 1e-12
    m = math.sqrt(total_panel_area) * 0.02

    def dry(S):
        pos = {}
        scale = {}
        cx = cy = row_h = 0.0
        for e in panels:
            if cx > 1e-12 and cx + e['w'] > S:
                cx = 0.0
                cy += row_h + m
                row_h = 0.0
            pos[id(e)] = (cx, cy)
            cx += e['w'] + m
            row_h = max(row_h, e['h'])
        ptop = cy + row_h
        field_h = max(ptop, math.sqrt(total_panel_area) * 0.5)
        sx = S + 3.0 * m
        for e in strips:
            sc = min(1.0, field_h * 0.98 / e['h']) if e['h'] > 1e-12 else 1.0
            scale[id(e)] = sc
            pos[id(e)] = (sx, 0.0)
            sx += e['w'] * sc + m
        gx0 = sx + 2.0 * m
        gx, gy, rh = gx0, 0.0, 0.0
        for e in specks:
            if gx > gx0 + S * 0.25:
                gx = gx0
                gy += rh + m
                rh = 0.0
            pos[id(e)] = (gx, gy)
            gx += e['w'] + m
            rh = max(rh, e['h'])
        W = gx if not specks else max(gx, gx0)
        W = max(W, sx)
        H = max(field_h, gy + rh)
        return pos, scale, W, H

    S = math.sqrt(total_panel_area) * 1.15
    pos = scale = None
    for _ in range(4):
        pos, scale, W, H = dry(S)
        ratio = (W / H) if H > 1e-12 else 1.0
        if 0.85 < ratio < 1.18:
            break
        S = max(S / math.sqrt(max(ratio, 0.2)), max(e['w'] for e in panels) if panels else S)

    # apply: optional strip scale about bbox min, then translate bbox min -> pos
    for e in entries:
        x0, y0, x1, y1 = _bbox(e['fs'], uv)
        sc = scale.get(id(e), 1.0)
        tx, ty = pos[id(e)]
        for luv in _loops(e['fs'], uv):
            luv.uv[0] = (luv.uv[0] - x0) * sc + tx
            luv.uv[1] = (luv.uv[1] - y0) * sc + ty

    # global fit into [MARGIN, 1-MARGIN]
    xs0, ys0, xs1, ys1 = [], [], [], []
    for e in entries:
        x0, y0, x1, y1 = _bbox(e['fs'], uv)
        xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
    X0, Y0, X1, Y1 = min(xs0), min(ys0), max(xs1), max(ys1)
    span = max(X1 - X0, Y1 - Y0) or 1.0
    sc = (1.0 - 2.0 * MARGIN) / span
    for e in entries:
        for luv in _loops(e['fs'], uv):
            luv.uv[0] = (luv.uv[0] - X0) * sc + MARGIN
            luv.uv[1] = (luv.uv[1] - Y0) * sc + MARGIN

    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(entries), len(panels), len(strips), len(specks)
