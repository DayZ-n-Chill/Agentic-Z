# Writing a `.p3d` with py3d

How to build a model in Python with the py3d in `scripts/tools/py3d`: LODs, points, faces, selections and named properties, the LOD resolution values, the build order and the checks to run on the result. No Blender or Object Builder is needed.

py3d reads and writes only the unbinarized MLOD format, and every vanilla model on `P:\` is binarized (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`), so this is tool knowledge, run against py3d 1.10.1 and measured on mod models. What vanilla models carry is in `README.md` of this pack; notes on reading an MLOD with py3d are in `_shared/py3d-mlod-notes.md`.

| Next step | File |
|---|---|
| The Blender to DayZ axis map and undoing a face reversal | `py3d-axis-map.md` |
| Proxy triangles and a minimal proxy model | `py3d-proxies.md` |
| Reading an existing file: LODs, faces, selections, bounds, paths | `py3d-reading.md` |
| Checks and repairs for centring, axes, UVs and winding | `py3d-shape-checks.md` |
| Checks for proxies, selections and collision LODs, and running them all | `py3d-part-checks.md` |
| Mass checked offline with `binarize.exe`, a collision hull, needle triangles | `py3d-collision-and-mass.md` |
| Which py3d to install, where mass may sit, replacing a section, the validator's findings | `py3d-assembly-rules.md` |

## Install

Install the copy in this repo and check it is the DayZ one (`py3d-assembly-rules.md`, "Which py3d"):

```cmd
python -m pip install -e scripts\tools\py3d
python -c "import py3d; assert py3d.IS_DAYZ_FORK"
```

Never run `pip install py3d`: the PyPI package of that name is an unrelated point cloud library (py3d 0.1.x). The repo's py3d provides `P3D`, `LOD`, `Face`, `Point`, `Selection` and `Vertex`, plus `get_lod`, `kind`, `bbox`, `triangulate`, `set_selection`, `set_total_mass`, `add_proxy`, `get_proxies`, `to_dict`, `from_dict`, `validate()` and `save(verify=True)`. The examples also use numpy, pillow and opensimplex (`python -m pip install numpy pillow opensimplex`), and scipy for a convex hull.

## The core API

```python
import py3d

p3d_file = py3d.P3D()

lod = py3d.LOD()
lod.resolution = 0.0                 # visual LOD 0

point = py3d.Point()
point.coords = (x, y, z)             # metres
point.flags = 0
point.mass = None                    # a number only on Geometry LOD points, and then on all of them
lod.points.append(point)

lod.facenormals.append((nx, ny, nz)) # unit vector, in a pool the faces index

face = py3d.Face(lod.points, lod.facenormals)
face.flags = 0
face.texture = "addon_name\\data\\textures\\my_texture_co.paa"
face.material = "addon_name\\data\\materials\\my_material.rvmat"

vertex = py3d.Vertex(lod.points, lod.facenormals)
vertex.point_index = 0               # index into lod.points
vertex.normal_index = 0              # index into lod.facenormals
vertex.uv = (u, v)
face.vertices.append(vertex)         # 3 vertices for a triangle, 4 for a quad
lod.faces.append(face)

selection = py3d.Selection(lod.points, lod.faces)
selection.points[lod.points[0]] = 1  # weight 1 = fully selected
selection.faces[lod.faces[0]] = 1
lod.selections["my_selection"] = selection

lod.properties["class"] = "house"    # named property, for example on a building's Geometry LOD

p3d_file.lods.append(lod)

with open("output.p3d", "wb") as f:
    p3d_file.write(f)

with open("output.p3d", "rb") as f:  # read it back
    print(len(py3d.P3D(f).lods))
```

`point.mass` is `None` by default. Set a number only on the points of the Geometry LOD, and then on all of them: py3d raises a `TypeError` when a LOD mixes points with a mass and points with `None`. Any number on another LOD, `0.0` included, writes a mass entry there and breaks the binarized centre of mass (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD").

## LOD resolution values

The engine knows a LOD's type by its resolution value. The same values with what each LOD is for are in `generated-model-rules.md`, "LOD resolution values"; this is the form the generation code uses:

```python
LOD_RESOLUTION = {
    "visual_0":      0.0,
    "visual_1":      1.0,
    "visual_2":      4.0,
    "visual_3":      8.0,
    "shadow_close":  1.0e4,    # only when asked for
    "shadow_far":    1.1e4,    # only when asked for
    "geometry":      1.0e13,
    "memory":        1.0e15,
    "land_contact":  2.0e15,
    "roadway":       3.0e15,
    "paths":         4.0e15,   # AI paths
    "hitpoints":     5.0e15,
    "view_geometry": 6.0e15,
    "fire_geometry": 7.0e15,
}
```

These agree with the Tier 2 table in `_shared/conventions/assets.md` and with the LOD lists in the headers of vanilla models (`lods.md`). Some Arma era guides give `2e13` and `3e13` for Fire and View Geometry; DayZ does not read those as Fire or View Geometry (`2e13` is the buoyancy LOD of the vanilla boat), so never use them. In the tool the reference is `py3d.classify_lod_resolution`. No vanilla model has a shadow volume LOD.

## Shapes

A cylinder for buttons, housings and pipes, as a sketch that leaves the faces to the caller:

```python
def make_cylinder(radius_top, radius_bot, height, y_offset, segments):
    points, normals, faces = [], [], []
    for i in range(segments):                      # bottom ring
        a = 2 * math.pi * i / segments
        points.append((math.cos(a) * radius_bot, y_offset, math.sin(a) * radius_bot))
        normals.append((math.cos(a), 0, math.sin(a)))
    for i in range(segments):                      # top ring
        a = 2 * math.pi * i / segments
        points.append((math.cos(a) * radius_top, y_offset + height, math.sin(a) * radius_top))
        normals.append((math.cos(a), 0, math.sin(a)))
    # add the cap centres, then the triangles
    return points, normals, faces
```

A convex box for the Geometry, Fire and View Geometry LODs has eight corners and 12 triangles; wind each face so its cross product points into the box (`generated-model-rules.md`, "The per component winding check"). A dome for an LED is rings from the equator to the pole joined by triangles.

## Selections

- A static part: `lod.selections["zbytek"] = selection_of_static_points`.
- A moving part goes in every LOD that must move with it: the visual LODs, and the Geometry, Fire Geometry, View Geometry and shadow LODs where they should follow. Build a separate `Selection` from each LOD's own points and faces; py3d refuses to write a selection that holds a point or face of another LOD.
- A material swap for `hiddenSelections`: `visual_lod.selections["led_indicator"] = ...`.
- Collision pieces: `Component01`, `Component02` and so on in the Geometry LOD.

## Memory LOD points

The Memory LOD has points and no faces. Each memory point is a named vertex, and an axis is two points in one selection:

```python
memory_lod = py3d.LOD()
memory_lod.resolution = 1.0e15

pt1 = py3d.Point(); pt1.coords = (0, 0.02, 0)
pt2 = py3d.Point(); pt2.coords = (0, 0.04, 0)
memory_lod.points.extend([pt1, pt2])
axis = py3d.Selection(memory_lod.points, memory_lod.faces)
axis.points[pt1] = 1
axis.points[pt2] = 1
memory_lod.selections["button_axis"] = axis

action = py3d.Point(); action.coords = (0.03, 0.03, 0)
memory_lod.points.append(action)
point_sel = py3d.Selection(memory_lod.points, memory_lod.faces)
point_sel.points[action] = 1
memory_lod.selections["actionPos"] = point_sel
```

The names vanilla script looks up are in `memory-points.md`; `actionPos` is a mod's own name.

## Build order

1. Create a `py3d.P3D()`.
2. Build visual LOD 0 (32 segments), then LOD 1 (16) and LOD 2 (8).
3. Build the Geometry LOD: convex boxes, mass, named properties.
4. Build the Fire Geometry LOD: convex boxes with penetration materials.
5. Build the View Geometry LOD: one simplified box.
6. Only when the user asked for shadow volumes: the close and far shadow LODs, each shrunk to 97 %.
7. Build the Memory LOD: points only.
8. Write the file, read it back and run the checks.

LODs sit in rising resolution order in the file (`lods.md`, "Order"). Sort `p3d_file.lods` by `resolution` before writing if they were added in another order.

## Checklist after writing

- The file reads back without errors.
- The LOD count is right and every LOD sits at its DayZ resolution: Geometry `1e13`, Memory `1e15`, LandContact `2e15`, Roadway `3e15`, Hit points `5e15`, View Geometry `6e15`, Fire Geometry `7e15`.
- Visual LOD 0 has the most vertices.
- A building's Geometry LOD has `class=house`.
- A placed object has `autocenter=0` on every collision LOD (`generated-model-rules.md`, "`autocenter=0` on every collision LOD"). Missing on Fire Geometry, it left the collision about 22 cm away from the visible mesh on a mod model. The same rule says what vanilla stores and when the property belongs on a model at all.
- Every face of a collision LOD has a penetration material, `face.material = "dz\\data\\data\\penetration\\<surface>.rvmat"` (`generated-model-rules.md`, "A penetration material on every collision face"). Without it bullets pass through.
- The Geometry LOD points have mass and no other LOD has any.
- The Memory LOD has no faces and holds `boundingbox_min`, `boundingbox_max`, `ce_center` and `invview`, which the inventory preview and placement use (`memory-points.md`).
- Every moving selection is in the visual LODs and the Memory LOD, and in each collision LOD that must move with it.
- Texture paths use backslashes and `.paa`; material paths use backslashes.
- Geometry from Blender went through the axis map, and the result was checked with `check_face_winding` and on an asymmetric feature for mirroring (`py3d-axis-map.md`).
- A model that takes attachments has its proxy triangles in the visual LODs, and since 1.30 in View Geometry (`py3d-proxies.md`).

py3d also has its own validator, `model.validate()`, and `save(verify=True)` reads the file back after writing; what its findings mean is in `py3d-assembly-rules.md`. The gate before a build is `/dayz-p3d-audit`.
