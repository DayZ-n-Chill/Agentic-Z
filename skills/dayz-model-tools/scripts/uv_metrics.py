"""Shared UV scorer + renderer. Every unwrap attempt is scored through this
module, so islands / overlap / stretch and the layout+uvgrid renders are
measured identically. Call score_and_render(obj, out_dir, tag).
Headless-safe: manual layout rasterizer (export_layout needs a GPU), EEVEE uvgrid.
render_uvgrid replaces the object's materials and removes every camera and light
in the scene, so save the .blend before calling it, not after.
"""
import bpy, bmesh, math, os, random, mathutils
random.seed(42)


def count_uv_islands(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    parent = list(range(len(bm.faces)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    EPS = 1e-5
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces; v1, v2 = e.verts
        def uvp(f, v):
            for lo in f.loops:
                if lo.vert == v:
                    return lo[uv].uv
            return None
        a1, a2 = uvp(f1, v1), uvp(f1, v2); b1, b2 = uvp(f2, v1), uvp(f2, v2)
        if None in (a1, a2, b1, b2):
            continue
        if (a1 - b1).length < EPS and (a2 - b2).length < EPS:
            r1, r2 = find(f1.index), find(f2.index)
            if r1 != r2:
                parent[r1] = r2
    n = len(set(find(i) for i in range(len(bm.faces))))
    bpy.ops.object.mode_set(mode='OBJECT')
    return n


def _uv_tris(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    tris3d = []; trisuv = []
    for f in bm.faces:
        loops = f.loops[:]
        p3 = [l.vert.co.copy() for l in loops]
        p2 = [l[uv].uv.copy() for l in loops]
        for i in range(1, len(loops) - 1):
            tris3d.append((p3[0], p3[i], p3[i + 1]))
            trisuv.append((p2[0], p2[i], p2[i + 1]))
    bpy.ops.object.mode_set(mode='OBJECT')
    return tris3d, trisuv


def mc_overlap(obj, spf=4):
    _, tris = _uv_tris(obj)
    def area(a, b, c):
        return abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))*0.5
    valid = [t for t in tris if area(*t) > 1e-12]
    N = 128
    from collections import defaultdict
    grid = defaultdict(list)
    for idx, (a, b, c) in enumerate(valid):
        gx0 = int(min(a[0], b[0], c[0])*(N-1)); gx1 = int(max(a[0], b[0], c[0])*(N-1))
        gy0 = int(min(a[1], b[1], c[1])*(N-1)); gy1 = int(max(a[1], b[1], c[1])*(N-1))
        for gx in range(max(0, gx0), min(N, gx1+1)):
            for gy in range(max(0, gy0), min(N, gy1+1)):
                grid[(gx, gy)].append(idx)
    def in_tri(p, a, b, c):
        d = (b[1]-a[1])*(c[0]-a[0]) - (b[0]-a[0])*(c[1]-a[1])
        if d == 0:
            return False
        w0 = (b[1]-a[1])*(p[0]-a[0]) - (b[0]-a[0])*(p[1]-a[1])
        w1 = (c[1]-b[1])*(p[0]-b[0]) - (c[0]-b[0])*(p[1]-b[1])
        w2 = (a[1]-c[1])*(p[0]-c[0]) - (a[0]-c[0])*(p[1]-c[1])
        return (w0 >= 0 and w1 >= 0 and w2 >= 0) if d > 0 else (w0 <= 0 and w1 <= 0 and w2 <= 0)
    total = over = 0
    for idx, (a, b, c) in enumerate(valid):
        for _ in range(spf):
            r1, r2 = random.random(), random.random()
            if r1 + r2 > 1:
                r1, r2 = 1-r1, 1-r2
            p = (a[0]+r1*(b[0]-a[0])+r2*(c[0]-a[0]), a[1]+r1*(b[1]-a[1])+r2*(c[1]-a[1]))
            total += 1
            gx = min(N-1, max(0, int(p[0]*(N-1)))); gy = min(N-1, max(0, int(p[1]*(N-1))))
            for j in grid.get((gx, gy), ()):
                if j != idx and in_tri(p, *valid[j]):
                    over += 1
                    break
    return (100.0*over/total) if total else 0.0


def stretch_stats(obj):
    """Per-face texel-density = uvArea/area3d, normalized to the median. p05/p95
    spread vs 1.0 = density uniformity (1.0 = perfectly uniform texel density)."""
    tris3d, trisuv = _uv_tris(obj)
    def a3(a, b, c):
        return ((b-a).cross(c-a)).length*0.5
    def a2(a, b, c):
        return abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))*0.5
    ratios = []
    for (A, B, C), (a, b, c) in zip(tris3d, trisuv):
        ar = a3(A, B, C)
        if ar > 1e-12:
            ratios.append(a2(a, b, c)/ar)
    ratios.sort()
    if not ratios:
        return (0, 0, 0)
    def pct(p):
        k = (len(ratios)-1)*p
        lo = int(k); hi = min(lo+1, len(ratios)-1)
        return ratios[lo] + (ratios[hi]-ratios[lo])*(k-lo)
    med = pct(0.5) or 1e-9
    return (pct(0.05)/med, 1.0, pct(0.95)/med)


def draw_layout(obj, path, size=1400):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    segs = []
    for f in bm.faces:
        loops = f.loops[:]; n = len(loops)
        for i in range(n):
            a = loops[i][uv].uv; b = loops[(i+1) % n][uv].uv
            segs.append((a.x, a.y, b.x, b.y))
    bpy.ops.object.mode_set(mode='OBJECT')
    buf = bytearray([255]) * (size*size*4)
    def setpx(x, y):
        if 0 <= x < size and 0 <= y < size:
            o = (y*size+x)*4; buf[o]=0; buf[o+1]=0; buf[o+2]=0; buf[o+3]=255
    def line(x0, y0, x1, y1):
        x0=int(x0*(size-1)); y0=int(y0*(size-1)); x1=int(x1*(size-1)); y1=int(y1*(size-1))
        dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx+dy
        while True:
            setpx(x0, y0)
            if x0==x1 and y0==y1:
                break
            e2=2*err
            if e2>=dy:
                err+=dy; x0+=sx
            if e2<=dx:
                err+=dx; y0+=sy
    for (ax, ay, bx, by) in segs:
        line(ax, ay, bx, by)
    img = bpy.data.images.new("Lay", size, size, alpha=True)
    img.pixels = [c/255.0 for c in buf]
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


def render_uvgrid(obj, path):
    for o in list(bpy.data.objects):
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o, do_unlink=True)
    img = bpy.data.images.new("UVGrid", 2048, 2048); img.generated_type = 'UV_GRID'
    mat = bpy.data.materials.new("UVGridMat"); mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Color']); nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.clear(); obj.data.materials.append(mat)
    dist = max(obj.dimensions)*1.6
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); bpy.context.collection.objects.link(cam)
    cam.location = (obj.location.x+dist, obj.location.y-dist, obj.location.z+dist*0.55)
    bpy.context.scene.camera = cam
    cam.rotation_euler = (mathutils.Vector(obj.location)-cam.location).to_track_quat('-Z', 'Y').to_euler()
    light = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type='SUN')); light.data.energy = 3.0
    bpy.context.collection.objects.link(light); light.rotation_euler = (0.6, 0.2, 0.6)
    sc = bpy.context.scene; sc.render.resolution_x = 1200; sc.render.resolution_y = 1200
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)


def score_and_render(obj, out_dir, tag):
    os.makedirs(out_dir, exist_ok=True)
    islands = count_uv_islands(obj)
    overlap = mc_overlap(obj)
    p05, p50, p95 = stretch_stats(obj)
    draw_layout(obj, os.path.join(out_dir, f"{tag}_uvlayout.png"))
    render_uvgrid(obj, os.path.join(out_dir, f"{tag}_uvgrid.png"))
    print(f"METRICS[{tag}] islands={islands} overlap={overlap:.2f}% density_p05/p50/p95={p05:.2f}/{p50:.2f}/{p95:.2f}")
    return dict(islands=islands, overlap=overlap, dens=(p05, p95))
