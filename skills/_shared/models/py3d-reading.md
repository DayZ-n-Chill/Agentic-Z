# Reading a `.p3d` with py3d

How to open an existing MLOD model with the py3d in `scripts/tools/py3d` and read its LODs, points, faces, selections, named properties, bounds and texture paths. The checks in `py3d-shape-checks.md` and `py3d-part-checks.md` build on the helpers here.

py3d reads only MLOD files, the ones Object Builder saves and scripts write. It does not read the binarized models under `P:\DZ\` (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`); those need an outside ODOL to MLOD converter first, which this repo does not ship.

## Open a file and list its LODs

```python
import py3d

with open("my_model.p3d", "rb") as f:
    model = py3d.P3D(f)

def classify_lod(res):
    """The LOD type of a resolution value, the same as py3d.classify_lod_resolution."""
    if res < 1e3:
        return f"Visual {res}"
    if 1e4 <= res < 2e4:
        return f"Shadow {res}"
    if abs(res - 1e13) < 1e11:
        return "Geometry"
    for value, name in ((1e15, "Memory"), (2e15, "LandContact"), (3e15, "Roadway"),
                        (4e15, "Paths"), (5e15, "Hitpoints"), (6e15, "View Geometry"),
                        (7e15, "Fire Geometry")):
        if abs(res - value) < 5e13:
            return name
    return f"Unknown ({res})"

for i, lod in enumerate(model.lods):
    print(f"LOD {i}: {classify_lod(lod.resolution)}")
    print(f"  points {len(lod.points)}, faces {len(lod.faces)}")
    print(f"  selections {list(lod.selections.keys())}")
```

## What a LOD holds

```python
lod = model.lods[0]

for pt in lod.points:
    x, y, z = pt.coords            # metres
    flags = pt.flags               # usually 0
    mass = pt.mass                 # a float, or None; meaningful on the Geometry LOD only

for i, normal in enumerate(lod.facenormals):
    nx, ny, nz = normal            # a shared pool that faces index

for face in lod.faces:             # triangles or quads
    tex = face.texture             # "addon\\data\\tex_co.paa" or ""
    mat = face.material            # "addon\\data\\mat.rvmat" or ""
    for vert in face.vertices:
        coords = lod.points[vert.point_index].coords
        normal = lod.facenormals[vert.normal_index]
        u, v = vert.uv

for name, sel in lod.selections.items():
    # sel.points and sel.faces are dicts keyed by the Point or Face object, holding the weight
    pts = [p for p, w in sel.points.items() if w > 0]
    faces = [f for f, w in sel.faces.items() if w > 0]
    print(f"  '{name}': {len(pts)} points, {len(faces)} faces")

for key, val in lod.properties.items():   # the Geometry LOD usually has class, autocenter and so on
    print(f"  {key} = {val}")
```

Count a selection's members, not just its name: tools can keep a name and drop its points (`selections.md`, "Membership lost by tools").

## Bounds

```python
def lod_bbox(lod):
    """(min_xyz, max_xyz, center_xyz) of a LOD, or None for an empty one."""
    if not lod.points:
        return None
    xs = [p.coords[0] for p in lod.points]
    ys = [p.coords[1] for p in lod.points]
    zs = [p.coords[2] for p in lod.points]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    center = tuple((lo[i] + hi[i]) / 2 for i in range(3))
    return lo, hi, center
```

## Every texture and material path

```python
def collect_paths(model):
    textures, materials = set(), set()
    for lod in model.lods:
        for face in lod.faces:
            if face.texture:
                textures.add(face.texture)
            if face.material:
                materials.add(face.material)
    return textures, materials
```

Check that each path exists in the mod with the casing it is written in; a visual face needs both a texture and a material (`py3d-assembly-rules.md`, "Visual faces carry both a texture and a material").
