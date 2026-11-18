# Shape checks and repairs with py3d

Quick py3d checks for the commonest faults in a generated model, centring, axes, UVs and face winding, and the repairs that go with them. They are for use while generating; the gate before a build is `/dayz-p3d-audit`, which covers more and reports CRITICAL, WARNING and NOTE findings. Proxy, selection and collision checks, and a runner for all of them, are in `py3d-part-checks.md`.

Tool knowledge about MLOD files, which are not on `P:\` (every vanilla model there is binarized, as `P:\DZ\gear\camping\wooden_case.p3d` shows by starting with `ODOL`). The functions use `lod_bbox` and `classify_lod` from `py3d-reading.md` and read `model.lods[0]` as visual LOD 0, so the model's first LOD must be that one.

## Centring

DayZ expects the model roughly centred on the ground plane, Y = 0. A model that sits wholly above or below it shows offset or upside down in the item preview.

```python
def check_centering(model):
    issues = []
    lod0 = model.lods[0]
    lo, hi, center = lod_bbox(lod0)
    ys = [p.coords[1] for p in lod0.points]
    below = sum(1 for y in ys if y < 0)
    above = sum(1 for y in ys if y > 0)
    if below > len(ys) * 0.95:
        issues.append(f"MODEL BELOW GROUND: {below}/{len(ys)} vertices below Y=0, centre Y={center[1]:.4f}; "
                      f"shift all points by {-center[1]:+.4f}")
    elif above > len(ys) * 0.95 and center[1] > 0.05:
        issues.append(f"MODEL FLOATING: {above}/{len(ys)} vertices above Y=0, centre Y={center[1]:.4f}")

    mem = next((l for l in model.lods if abs(l.resolution - 1e15) < 5e13), None)
    if mem and "ce_center" in mem.selections:
        pts = [p for p, w in mem.selections["ce_center"].points.items() if w > 0]
        if pts:
            ce = pts[0].coords
            dist = sum((ce[i] - center[i]) ** 2 for i in range(3)) ** 0.5
            if dist > 0.02:
                issues.append(f"ce_center at {ce} is {dist:.3f} m from the geometric centre {center}")
    return issues
```

## Axes the same in every LOD

This finds the Blender axis map applied to the visual LODs but not the collision LODs, or the other way round: the shape of the bounding box should match in every LOD.

```python
def check_axis_consistency(model):
    issues = []
    visual = next((l for l in model.lods if l.resolution == 0.0), None)
    geo = next((l for l in model.lods if abs(l.resolution - 1e13) < 1e11), None)
    if not visual or not geo:
        return issues
    v_lo, v_hi, _ = lod_bbox(visual)
    g_lo, g_hi, _ = lod_bbox(geo)

    v_sizes = sorted(v_hi[i] - v_lo[i] for i in range(3))
    g_sizes = sorted(g_hi[i] - g_lo[i] for i in range(3))
    for i in range(3):
        if v_sizes[i] > 0.001 and not 0.7 <= g_sizes[i] / v_sizes[i] <= 1.5:
            issues.append(f"AXIS MISMATCH: visual sizes {v_sizes} against Geometry sizes {g_sizes}; "
                          f"the axis map was probably applied to some LODs only")
            break

    v_y, v_z = v_hi[1] - v_lo[1], v_hi[2] - v_lo[2]
    g_y, g_z = g_hi[1] - g_lo[1], g_hi[2] - g_lo[2]
    if abs(v_y - g_z) < 0.01 and abs(v_z - g_y) < 0.01 and abs(v_y - v_z) > 0.02:
        issues.append(f"Y AND Z SWAPPED: visual Y={v_y:.4f} Z={v_z:.4f}, Geometry Y={g_y:.4f} Z={g_z:.4f}; "
                      f"apply the same map to every LOD")
    return issues
```

It finds the visual LOD by the resolution value `0.0`, so a model whose visual LODs start at `1` gets no finding from it.

## UVs

DayZ puts V = 0 at the top. Textures made with the OpenGL convention (V = 0 at the bottom) show flipped vertically. Measured on a wall lamp model file, not in game: sampling the texture on the faces of its `light_emit` bulb, a selection with its own colour, differed from the rest of the model by 177.6 with V = 0 at the top and by 10.6 with V = 0 at the bottom, which agrees with the `(u, 1 - v)` flip below (the unit was not recorded).

```python
def check_uv_range(model):
    issues = []
    uvs = [v.uv for f in model.lods[0].faces for v in f.vertices]
    if not uvs:
        return issues
    us = [u for u, _ in uvs]
    vs = [v for _, v in uvs]
    out = sum(1 for u, v in uvs if u < -0.01 or u > 1.01 or v < -0.01 or v > 1.01)
    if out > len(uvs) * 0.1:
        issues.append(f"UV OUT OF RANGE: {out}/{len(uvs)} outside [0,1], "
                      f"U {min(us):.3f} to {max(us):.3f}, V {min(vs):.3f} to {max(vs):.3f}")
    if max(us) - min(us) < 0.01 or max(vs) - min(vs) < 0.01:
        issues.append("DEGENERATE UVs: almost no spread; the unwrap probably failed")
    return issues
```

It catches out of range and collapsed UVs on LOD 0 only, and it does not detect a V flip by itself. The full UV audit (overlap, islands, texel density, mirrored islands) is the UV step in `dayz-p3d-audit/references/manual-checks.md` and `uv-mapping.md`.

## Face winding agreement

After the Blender axis map the faces are already in MLOD order: cross product inward, normals negated to match (`py3d-axis-map.md`). This check only confirms that vertex order and stored normal agree. It cannot see a mirror, and it cannot tell inward from outward when both are flipped together. When the vertex order points outward (both outward, or faces reversed after a correct export), textures show on the inside only. Normals alone pointing outward disagree with the vertex order and render solid, but that is not what the axis map writes; `dayz-p3d-audit/references/winding-diagnostics.md`, Check A, maps each case to its fix.

It reads only `model.lods[0]`, and only for agreement: a file whose first LOD has no faces gets no finding, and neither does a collision box wound outward with matching normals. It is not the per component check of `generated-model-rules.md`.

```python
import numpy as np

def check_face_winding(model):
    """Vertex order and stored normal agree when cross . normal > 0, on every asset class,
    characters included. Agreement does not give the direction: check_dayz_winding.py
    reads that from the signed volume of each closed shell."""
    issues = []
    lod0 = model.lods[0]
    flipped = total = 0
    for face in lod0.faces:
        if len(face.vertices) < 3:
            continue
        a, b, c = (np.array(lod0.points[v.point_index].coords) for v in face.vertices[:3])
        n = np.cross(b - a, c - a)
        length = np.linalg.norm(n)
        if length < 1e-10:
            continue
        stored = np.array(lod0.facenormals[face.vertices[0].normal_index])
        total += 1
        if np.dot(n / length, stored) < 0:
            flipped += 1
    if total:
        pct = flipped * 100 / total
        if pct > 50:
            issues.append(f"WINDING REVERSED: {flipped}/{total} faces ({pct:.0f}%) disagree with their normals; "
                          f"check the axis map and the normal sign before reversing any face")
        elif pct > 5:
            issues.append(f"PARTIAL WINDING ISSUE: {flipped}/{total} faces ({pct:.0f}%) disagree with their normals")
    return issues
```

## Repairs

Re-centre the model at Y = 0, every LOD by the same amount:

```python
def recenter_model_y(model):
    ys = [p.coords[1] for p in model.lods[0].points]
    offset = -(min(ys) + max(ys)) / 2.0
    for lod in model.lods:
        for pt in lod.points:
            x, y, z = pt.coords
            pt.coords = (x, y + offset, z)
```

Flip V on the visual and shadow LODs:

```python
def flip_uv_v(model):
    for lod in model.lods:
        if lod.resolution < 12000:
            for face in lod.faces:
                for vert in face.vertices:
                    u, v = vert.uv
                    vert.uv = (u, 1.0 - v)
```

Apply the axis map to one LOD that missed it:

```python
def apply_axis_map(lod):
    for pt in lod.points:
        x, y, z = pt.coords
        pt.coords = (x, z, y)
    lod.facenormals[:] = [(-nx, -nz, -ny) for nx, ny, nz in lod.facenormals]   # in place
    # keep the face vertex order: after this map it is already the MLOD order
```

Move `ce_center` to the geometric centre of visual LOD 0:

```python
def fix_ce_center(model):
    _, _, center = lod_bbox(model.lods[0])
    for lod in model.lods:
        if abs(lod.resolution - 1e15) < 5e13 and "ce_center" in lod.selections:
            pts = [p for p, w in lod.selections["ce_center"].points.items() if w > 0]
            if pts:
                pts[0].coords = center
```

`check_centering` and `fix_ce_center` match the Memory value only. A looser test such as `lod.resolution > 1e14` is also true of LandContact, Roadway, Paths, Hit points, View Geometry and Fire Geometry, so on a model without a Memory LOD, or with one of those stored before it, it reads or moves a `ce_center` in the wrong LOD.
