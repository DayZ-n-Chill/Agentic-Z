# Writing a `.p3d` directly with py3d

The py3d API for building a model in Python: creating LODs, points, faces, selections and named properties, the LOD resolution values, the build order, the Blender to DayZ axis map, proxies, reading and inspecting an existing file, a set of diagnostic checks with their repairs, checking mass offline with `binarize.exe`, and building a collision LOD from a convex hull.

What is checked and what is not: this is tool knowledge about the py3d fork in `scripts/tools/py3d` (version 1.10.1 when this file was written; the code blocks were run against it) and the source author's measurements on his own mods (LF_PowerGrid, LFQuad, LFDucati, SecretRock), in game or offline. Vanilla models on `P:\` are binarized and py3d reads only the unbinarized MLOD format, so almost nothing here can be checked on `P:\`; the few lines that cite `P:\` were opened. What vanilla models carry is in the model pack (`_shared/models/README.md`), and reading notes for the upstream library are in `_shared/py3d-mlod-notes.md`.

Evidence labels: `[EXACT]` is measured or read from a file. Codes such as SP-025 and LL-080 are the source author's ticket and lesson numbers. Rule numbers (Rule 12, Rule 16, Rule 17, Rule 18) are the rules in `critical-rules.md`.

## Contents

- [Overview](#overview)
- [Core API](#core-api)
- [LOD resolution values](#lod-resolution-values)
- [Geometry generation patterns](#geometry-generation-patterns)
- [Selection patterns](#selection-patterns)
- [Memory LOD Pattern](#memory-lod-pattern)
- [Complete build order](#complete-build-order)
- [Validation checklist](#validation-checklist)
- [Blender Z-up to DayZ Y-up Rotation](#blender-z-up-to-dayz-y-up-rotation)
- [Face Winding Order Fix](#face-winding-order-fix)
- [Proxy faces for attachment rendering](#proxy-faces-for-attachment-rendering)
- [Reading and inspecting existing `.p3d` files](#reading-and-inspecting-existing-p3d-files)
- [Diagnostic and validation toolkit](#diagnostic-and-validation-toolkit)
- [Repair patterns](#repair-patterns)
- [The LOD resolution values are the DayZ ones](#the-lod-resolution-values-are-the-dayz-ones)
- [Check mass and centre of mass offline with `binarize.exe`](#check-mass-and-centre-of-mass-offline-with-binarizeexe)
- [Building a collision LOD from scratch](#building-a-collision-lod-from-scratch-sp-025)

## Overview

The `py3d` library (the DayZ fork, version 1.6.0 or later, built on KoffeinFlummi's codec) reads and writes Arma and DayZ `.p3d` files in MLOD (unbinarized) format directly from Python. No Blender, no Object Builder and no other tool is needed.

- **Where it is:** the fork ships in this repo at `scripts/tools/py3d` (1.10.1). The upstream library (github.com/KoffeinFlummi/py3d) is no longer maintained.
- **Install and check:** `py3d-assembly-rules.md`, "Which py3d". In short: `python -m pip install -e scripts\tools\py3d`, then assert `py3d.IS_DAYZ_FORK`.
- **Other packages:** numpy, pillow and opensimplex (`python -m pip install numpy pillow opensimplex`); scipy for the convex hull pattern at the end.

> **Do not run `pip install py3d`.** That installs a completely different library (a 3D visualization package, py3d 0.1.x), not the MLOD parser. The right package is the DayZ fork. It provides `P3D`, `LOD`, `Face`, `Point`, `Selection` and `Vertex`, plus the fork's own API: `get_lod` and `kind`, `bbox`, `triangulate`, `set_selection`, `set_total_mass`, `add_proxy` and `get_proxies`, `to_dict` and `from_dict`, `validate()` and `save(verify=True)`.
> Check: `python -c "import py3d; assert py3d.IS_DAYZ_FORK"`

## Core API

```python
import py3d

# Create a new P3D file
p3d_file = py3d.P3D()

# Create a LOD
lod = py3d.LOD()
lod.resolution = 0.0   # Resolution LOD 0 (full detail visual)

# Add a point (vertex)
point = py3d.Point()
point.coords = (x, y, z)    # XYZ coordinates in metres
point.flags = 0              # Point flags (usually 0)
point.mass = None            # Mass: a number on Geometry LOD points only (all of them); None here
lod.points.append(point)

# Add a face normal
lod.facenormals.append((nx, ny, nz))  # Unit vector

# Create a face (triangle or quad)
face = py3d.Face(lod.points, lod.facenormals)
face.flags = 0
face.texture = "addon_name\\data\\textures\\my_texture_co.paa"
face.material = "addon_name\\data\\materials\\my_material.rvmat"

# Add vertices to the face (3 for a triangle, 4 for a quad)
vertex = py3d.Vertex(lod.points, lod.facenormals)
vertex.point_index = 0       # Index into lod.points
vertex.normal_index = 0      # Index into lod.facenormals
vertex.uv = (u, v)           # UV coordinates
face.vertices.append(vertex)
# ... repeat for 2 more vertices (triangle)
lod.faces.append(face)

# Named selections
selection = py3d.Selection(lod.points, lod.faces)
selection.points[lod.points[0]] = 1    # Weight 1 = fully selected
selection.faces[lod.faces[0]] = 1
lod.selections["my_selection"] = selection

# Named properties (for example class=house on the Geometry LOD of a building)
lod.properties["class"] = "house"

# Add the LOD to the P3D
p3d_file.lods.append(lod)

# Write to a file
with open("output.p3d", "wb") as f:
    p3d_file.write(f)

# Verify by reading back
with open("output.p3d", "rb") as f:
    verify = py3d.P3D(f)
    print(f"LODs: {len(verify.lods)}")
```

Mass: `point.mass` is `None` by default. Set a number only on the points of the Geometry LOD, and then on all of them: the fork raises a `TypeError` when it writes a LOD in which some points have a mass and others have `None`. Any number, `0.0` included, on another LOD writes a mass entry there and breaks the binarized centre of mass (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD"). The source's example set `point.mass = 10.0` on this visual LOD with the comment "only needed for Geometry/Fire LODs"; its own later measurement corrects both.

## LOD resolution values

The engine identifies the type of a LOD by its resolution value. The same values as a table, with what each LOD is for and the Arma values not to use, are in `critical-rules.md` ("LOD resolution values"); this dictionary is the form the generation code uses:

```python
LOD_RESOLUTION = {
    "visual_0":       0.0,       # Visual, full detail
    "visual_1":       1.0,       # Visual, medium detail
    "visual_2":       4.0,       # Visual, low detail
    "visual_3":       8.0,       # Visual, very low detail
    "shadow_close":   1.0e4,     # ShadowVolume (close); only when asked for
    "shadow_far":     1.1e4,     # ShadowVolume (far); only when asked for
    "geometry":       1.0e13,    # Collision geometry
    "memory":         1.0e15,    # Memory points
    "land_contact":   2.0e15,    # LandContact
    "roadway":        3.0e15,    # Roadway
    "paths":          4.0e15,    # Paths (AI navigation)
    "hitpoints":      5.0e15,    # Hit points / damage zones
    "view_geometry":  6.0e15,    # View Geometry (DayZ; not the Arma 3 value 3e13)
    "fire_geometry":  7.0e15,    # Fire Geometry (DayZ; not the Arma 3 value 2e13)
}
```

These agree with the Tier 2 table in `_shared/conventions/assets.md` and with the LOD lists of vanilla models (`_shared/models/lods.md`, read from the headers of the models under `P:\DZ\`, for example `P:\DZ\gear\camping\wooden_case.p3d`). No vanilla model has a ShadowVolume LOD.

## Geometry generation patterns

### Cylinder (buttons, housings, pipes)

```python
def make_cylinder(radius_top, radius_bot, height, y_offset, segments):
    points, normals, faces = [], [], []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        # Bottom ring
        points.append((math.cos(angle)*radius_bot, y_offset, math.sin(angle)*radius_bot))
        normals.append((math.cos(angle), 0, math.sin(angle)))
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        # Top ring
        points.append((math.cos(angle)*radius_top, y_offset+height, math.sin(angle)*radius_top))
        normals.append((math.cos(angle), 0, math.sin(angle)))
    # Add center points for the caps, then generate the triangle faces...
    return points, normals, faces
```

A sketch: the faces are left to the caller.

### Convex box (Geometry, Fire and View LODs)

```python
def make_box(x_min, y_min, z_min, x_max, y_max, z_max):
    points = [
        (x_min,y_min,z_min), (x_max,y_min,z_min),
        (x_max,y_min,z_max), (x_min,y_min,z_max),
        (x_min,y_max,z_min), (x_max,y_max,z_min),
        (x_max,y_max,z_max), (x_min,y_max,z_max),
    ]
    # 12 triangles for 6 faces
    return points, normals, faces
```

A sketch as well: the normals and faces are left to the caller. Wind each face of a collision box so that its cross product points into the box (Rule 18).

### Dome or hemisphere (LEDs, indicator lights)

Generate rings from the equator to the pole and connect them with triangles.

## Selection patterns

### Static part (present in all visual LODs)

```python
lod.selections["zbytek"] = selection_covering_static_points
```

### Animated part (in every LOD that must move with it)

```python
for lod in [visual_lod0, visual_lod1, geometry_lod, fire_lod, view_lod, shadow_lod]:
    lod.selections["button_push"] = selection_covering_button_points
```

Each LOD needs its own `Selection`, built from that LOD's own points and faces: the fork refuses to write a selection that holds a point or face of another LOD.

### Material swap selection (for hiddenSelections)

```python
visual_lod.selections["led_indicator"] = selection_covering_led_points
```

### Geometry components

```python
geometry_lod.selections["Component01"] = selection_covering_housing
geometry_lod.selections["Component02"] = selection_covering_button
```

## Memory LOD Pattern

The Memory LOD has points but **no** faces. Each memory point is a named vertex.

```python
memory_lod = py3d.LOD()
memory_lod.resolution = 1.0e15

# Animation axis = 2 points
pt1 = py3d.Point(); pt1.coords = (0, 0.02, 0)
pt2 = py3d.Point(); pt2.coords = (0, 0.04, 0)
memory_lod.points.extend([pt1, pt2])

sel = py3d.Selection(memory_lod.points, memory_lod.faces)
sel.points[pt1] = 1
sel.points[pt2] = 1
memory_lod.selections["button_axis"] = sel

# Interaction point = 1 point
action = py3d.Point(); action.coords = (0.03, 0.03, 0)
memory_lod.points.append(action)
sel_action = py3d.Selection(memory_lod.points, memory_lod.faces)
sel_action.points[action] = 1
memory_lod.selections["actionPos"] = sel_action
```

## Complete build order

1. Create a `py3d.P3D()` instance.
2. Build Resolution LOD 0 (32 segments) and append it.
3. Build Resolution LOD 1 (16 segments) and append it.
4. Build Resolution LOD 2 (8 segments) and append it.
5. Build the Geometry LOD (convex boxes, mass, properties) and append it.
6. Build the Fire Geometry LOD (convex boxes, penetration materials) and append it.
7. Build the View Geometry LOD (a single simplified box) and append it.
8. Only when the user asked for shadow volumes: build the close shadow LOD (shrunk to 97 %) and the far one (shrunk to 97 %) and append them.
9. Build the Memory LOD (points only, no faces) and append it.
10. Write to a file.
11. Read back and verify.

LODs sit in rising resolution order in the file (`_shared/models/lods.md`, "Order"); sort `p3d_file.lods` by `resolution` before writing if they were appended in another order.

## Validation checklist

After generating, verify:

- [ ] The file reads back without errors.
- [ ] The number of LODs is right, at the DayZ resolutions: Geometry `1e13`, Memory `1e15`, LandContact `2e15`, Roadway `3e15`, Hit points `5e15`, View Geometry `6e15`, Fire Geometry `7e15`, not the Arma 3 values `2e13` and `3e13`.
- [ ] Resolution LOD 0 has the most vertices.
- [ ] The Geometry LOD has the `class=house` property (if it is a building).
- [ ] **The `autocenter=0` named property is on every collision LOD** (Geometry, Fire Geometry, View Geometry, Roadway, Hit points, LandContact) of a placed object: Rule 16. The bug it prevents: missing on Fire Geometry, the collision mesh sat about 22 cm away from the visual mesh. Rule 16 says what vanilla stores and when the property belongs on a model at all.
- [ ] **Every face in the collision LODs has a penetration `.rvmat`**: Rule 17. `face.material = "dz\\data\\data\\penetration\\<surface>.rvmat"`. Without it bullets pass through.
- [ ] The Geometry LOD points have mass, and no other LOD has any (`point.mass is None` there).
- [ ] The Memory LOD has 0 faces.
- [ ] The Memory LOD has the named points `boundingbox_min`, `boundingbox_max`, `ce_center` and `invview` (the inventory preview and the placement system use them; `_shared/models/memory-points.md`).
- [ ] Every animated selection exists in the Resolution LODs and the Memory LOD, and in each of the Geometry, Fire and View LODs that must move with it.
- [ ] Texture paths use backslashes and the `.paa` extension.
- [ ] Material paths use backslashes.
- [ ] If the geometry came from Blender: the Z-up to Y-up map was applied (see below).
- [ ] `[EXACT]` After the axis conversion, Rule 12 holds: geometry authored in Blender or FBX is mapped with the det=-1 reflection `(x,y,z)→(x,z,y)`, keeps its vertex order and gets its normals negated (measured in game 2026-10-01, DayZDiag 1.29.163709: one chiral model exported three ways; this map renders solid and reads correctly, the old det=+1 recipe renders solid but **mirrored**, and `P3D.transform(py3d.BLENDER_TO_DAYZ)` alone renders inside out and mirrored). glTF and GLB have their own section in `axes-and-winding.md`. Verify with `check_face_winding` and check chirality on an asymmetric feature.
- [ ] If the object accepts attachments: the proxy faces and selections are present in the visual LODs, and in View Geometry since 1.30.

## Blender Z-up to DayZ Y-up Rotation

Mandatory for anything exported from Blender. Blender uses Z as the up axis, DayZ uses Y. If geometry is generated in Blender, or in code with Z up, all of it must be mapped before the `.p3d` is written.

**Transform: `x' = x, y' = z, z' = y`** (det=-1)

Blender is right handed and DayZ left handed, so the map that preserves the shape is this **reflection** in the numbers, not the rotation of -90° about X (`z' = -y`), which ships a mirrored model (Rule 12, measured in game 2026-10-01). Map the vertex positions; map the normals the same way and negate them (MLOD stores normals inward); keep the vertex order of every face.

```python
def rot_coords(c):
    return (c[0], c[2], c[1])

def rot_normal(n):
    return (-n[0], -n[2], -n[1])   # mapped like the positions, then negated (MLOD: inward)

# Apply to ALL LODs (visual, geometry, fire, view, shadow, memory)
for lod in model.lods:
    for pt in lod.points:
        pt.coords = rot_coords(pt.coords)
    new_normals = []
    for n in lod.facenormals:
        new_normals.append(rot_normal(n))
    lod.facenormals = new_normals
```

With py3d itself: `model.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` maps points and normals and, because det<0, reverses every face; reverse them back and negate the normals, and the result equals the loop above. `py3d.BLENDER_TO_DAYZ` is the old det=+1 rotation: `model.transform(py3d.BLENDER_TO_DAYZ)` on its own renders inside out **and** mirrored in game (2026-10-01).

From py3d 1.8.0, `py3d.blender_to_dayz(model)` does the whole conversion in one call and keeps the vertex order of every face, proxy triangles included. Measured the same day: its collision LODs register raycasts in `geom`, `view` and `fire`, and static proxies drawn in Blender as py3d canonical raw triangles come out with the same ODOL frames as `add_proxy(space="engine")` (the binarized files are byte identical) and render in the pose drawn. A crew or wheel proxy drawn that way with the identity frame therefore gets the frame of the engine space path the LFDucati mod was driven with (LL-505, LL-506; claim CLAIM-B2D-PROXY-FRAME-EQUIV-REF): the frame only, not a drive, and the rest of the vehicle must still match a working model. `py3d.BLENDER_TO_DAYZ` is deprecated; the same value is now `py3d.ROT_X_NEG90`.

**History `[EXACT]` (superseded 2026-10-01).** 2026-07-06: "det=+1, never reverse" rendered inside out. 2026-09-26 (SP-432): "det=+1, reverse and negate" rendered solid but mirrored (its five validation models are symmetric). LL-504 (2026-09-22) and the in-game test of 2026-10-01 settled the det=-1 reflection above. The winding gates passed at every step: only an asymmetric model shows a mirror. The longer account is `axes-and-winding.md`.

## Face Winding Order Fix

Per source path; see Rule 12.

Geometry authored in Blender or FBX and mapped with Rule 12's det=-1 reflection keeps its vertex order: no reversal. Reverse faces only to repair a mesh whose cross product points **outward**, for example after `P3D.transform()` with a det<0 map, which reverses on its own, and never proxy triangles on their own account (they carry the attachment frame). The one case where proxy triangles are reversed too is undoing that `P3D.transform()` reversal, which hit them as well: reversing everything back leaves them in their authored order, as Rule 12 and `py3d.blender_to_dayz()` do (measured 2026-10-01 for py3d canonical triangles: they then render in the pose drawn in Blender; for other conventions, check the ODOL against a working model, LL-505). For glTF and GLB see `axes-and-winding.md`, "GLB and glTF imports".

The loop below is that undo and nothing else: it reverses every face of every LOD, proxy triangles included, so run it only on a model that `P3D.transform()` reversed whole. A collision LOD wound outward is repaired face by face instead (Rule 18; `dayz-p3d-audit/references/p3d-killers.md` section 1): reverse only the non proxy faces that Rule 18's per component check reads outward, set their stored normals as that section's fix says, and leave every other face and LOD alone. Run as a collision repair, the loop also turns a healthy Visual LOD inside out and alters the proxies' frames.

```python
# Undo of a whole-model P3D.transform() reversal ONLY: every face of every LOD, proxies included.
for lod in model.lods:
    for face in lod.faces:
        face.vertices.reverse()
```

Symptoms of a wrong winding order:

- textures visible only from inside the object
- the object appears transparent or invisible from outside
- the object appears solid black from outside (backface culling)

**The undo applies to all LODs**, Geometry, Fire Geometry, View Geometry and shadow LODs included, not just the visual LODs, because `P3D.transform()` reversed them all; a collision repair touches only the faces Rule 18 reads outward.

*(Aligned 2026-10-02 with Rule 18 and the audit's winding killer: the loop above used to carry no word on its scope, and this paragraph read "this applies to ALL LODs including Geometry, Fire Geometry, View Geometry, and Shadow LODs, not just visual LODs". Copied to repair a collision LOD wound outward, the loop also reversed a healthy Visual LOD and every proxy triangle.)*

## Proxy faces for attachment rendering

When an item accepts attachments (for example a cradle that holds a battery), the attached item's model must be drawn at a specific position on the parent. That takes the **proxy system**: a special face and named selection in the parent's visual LODs.

### How proxies work

1. A tiny triangle is added to the visual LODs (and to View Geometry since 1.30, `dayz-1-30-model-pipeline.md`).
2. The face is assigned to a named selection with the pattern `proxy:<addon path>\<proxy model>.NNN`.
3. The engine finds this selection, reads the position and orientation of the face, and draws the attached item's model there.
4. A minimal proxy `.p3d` must exist at the path the selection names.
5. A `CfgNonAIVehicles` class must map the `inventorySlot` to the proxy model.

The path is written without `.p3d` (`memory-and-selections.md`, "Naming convention"). The source's examples kept the extension; the fork's `add_proxy` refuses a path that ends in `.p3d`.

### Creating a proxy with py3d

The short way, with the fork: `LOD.add_proxy` writes the triangle, the selection and its name, and returns the name.

```python
for lod in [lod0, lod1, lod2, view_lod]:
    lod.add_proxy("MyAddon\\data\\MySlot", index=1, origin=(0.0, 0.05, 0.0))
# selection created: proxy:MyAddon\data\MySlot.001
```

`add_proxy` takes `rotation` (rows x, y, z; identity when left out) and `space` (`"raw"` or `"engine"`); which one gives the pose wanted in game is in `_shared/models/proxy-frames.md`. To fix proxies that already exist, use `/dayz-proxy-align`.

The long way, which shows what a proxy consists of:

```python
from py3d import Point, Face, Vertex, Selection

# The selection name follows a strict convention
proxy_sel_name = "proxy:MyAddon\\data\\MySlot.001"

# Position where the attachment should render
proxy_center = (0.0, 0.05, 0.0)  # center of the cradle or slot

# Proxy face: 3 points forming a tiny right triangle with unequal legs.
# Point 0 = position (the right angle), point 1 = the short leg (+Y, up),
# point 2 = the long leg (+Z, forward): the same triangle add_proxy writes.
proxy_pts_coords = [
    (proxy_center[0],        proxy_center[1],         proxy_center[2]),
    (proxy_center[0],        proxy_center[1] + 0.001, proxy_center[2]),
    (proxy_center[0],        proxy_center[1],         proxy_center[2] + 0.002),
]
proxy_normal = (1.0, 0.0, 0.0)

# Add to each visual LOD
for lod in [lod0, lod1, lod2]:
    proxy_point_objs = []
    for pc in proxy_pts_coords:
        pt = Point()
        pt.coords = pc
        pt.flags = 0
        lod.points.append(pt)
        proxy_point_objs.append(pt)

    lod.facenormals.append(proxy_normal)
    norm_idx = len(lod.facenormals) - 1

    proxy_face = Face(lod.points, lod.facenormals)
    proxy_face.flags = 0
    proxy_face.texture = ""
    proxy_face.material = ""

    for pi, pobj in enumerate(proxy_point_objs):
        v = Vertex(lod.points, lod.facenormals)
        v.point_index = lod.points.index(pobj)
        v.normal_index = norm_idx
        v.uv = (0.0, 0.0)
        proxy_face.vertices.append(v)

    lod.faces.append(proxy_face)

    # Named selection covering the proxy face and its points
    proxy_sel = Selection(lod.points, lod.faces)
    proxy_sel.points[proxy_point_objs[0]] = 1
    proxy_sel.points[proxy_point_objs[1]] = 1
    proxy_sel.points[proxy_point_objs[2]] = 1
    proxy_sel.faces[proxy_face] = 1
    lod.selections[proxy_sel_name] = proxy_sel
```

The source's triangle had two legs of the same length (0.001 along +Z and along +Y) and described the frame by vertex order. The frame is read from the triangle's angles, and a triangle with two equal legs is ambiguous: the attached model can come out turned (`_shared/models/proxy-frames.md`, "Ambiguous triangles"). The legs above are unequal for that reason. Checked with the fork: `LOD.get_proxies` reads the triangle above as not ambiguous, with the same anchor and the same identity raw frame as the one `add_proxy` writes.

### Creating a minimal proxy `.p3d`

The engine needs a real `.p3d` file at the proxy path. It can be minimal: a single triangle and a Memory LOD.

```python
from py3d import P3D, LOD, Point, Face, Vertex, Selection

proxy = P3D()

# Resolution LOD: 1 tiny triangle
lod = LOD()
lod.resolution = 0.0
p0 = Point(); p0.coords = (0.0, 0.0, 0.0)
p1 = Point(); p1.coords = (0.01, 0.0, 0.0)
p2 = Point(); p2.coords = (0.0, 0.01, 0.0)
lod.points.extend([p0, p1, p2])
lod.facenormals.append((0.0, 0.0, 1.0))

face = Face(lod.points, lod.facenormals)
face.texture = ""
face.material = ""
for i in range(3):
    v = Vertex(lod.points, lod.facenormals)
    v.point_index = i
    v.normal_index = 0
    v.uv = (0.0, 0.0)
    face.vertices.append(v)
lod.faces.append(face)

sel = Selection(lod.points, lod.faces)
sel.points[p0] = 1; sel.points[p1] = 1; sel.points[p2] = 1
sel.faces[face] = 1
lod.selections["zbytek"] = sel
proxy.lods.append(lod)

# Memory LOD
mem = LOD()
mem.resolution = 1.0e15
ce = Point(); ce.coords = (0.0, 0.0, 0.0)
mem.points.append(ce)
ce_sel = Selection(mem.points, mem.faces)
ce_sel.points[ce] = 1
mem.selections["ce_center"] = ce_sel
proxy.lods.append(mem)

with open("MySlot.p3d", "wb") as f:
    proxy.write(f)
```

### The config.cpp requirement

See `config-and-packing.md` for the `CfgNonAIVehicles` class that completes the proxy system.

---

## Reading and inspecting existing `.p3d` files

py3d reads MLOD `.p3d` files as easily as it writes them. This is essential for diagnosing problems in generated models. It does not read the binarized ODOL files under `P:\DZ\`.

### Basic read and LOD enumeration

```python
import py3d

with open("my_model.p3d", "rb") as f:
    model = py3d.P3D(f)

print(f"Total LODs: {len(model.lods)}")

# LOD type by resolution value
def classify_lod(res):
    # DayZ LOD resolutions (mirrors py3d.classify_lod_resolution)
    if res < 1e3:
        return f"Visual {res}"
    elif 1e4 <= res < 2e4:
        return f"Shadow {res}"
    elif abs(res - 1e13) < 1e11:
        return "Geometry"
    elif abs(res - 1e15) < 5e13:
        return "Memory"
    elif abs(res - 2e15) < 5e13:
        return "LandContact"
    elif abs(res - 3e15) < 5e13:
        return "Roadway"
    elif abs(res - 4e15) < 5e13:
        return "Paths"
    elif abs(res - 5e15) < 5e13:
        return "Hitpoints"
    elif abs(res - 6e15) < 5e13:
        return "View Geometry"
    elif abs(res - 7e15) < 5e13:
        return "Fire Geometry"
    else:
        return f"Unknown ({res})"

for i, lod in enumerate(model.lods):
    ltype = classify_lod(lod.resolution)
    print(f"LOD {i}: {ltype}")
    print(f"  Points: {len(lod.points)}, Faces: {len(lod.faces)}")
    print(f"  Selections: {list(lod.selections.keys())}")
```

### Accessing LOD data

```python
lod = model.lods[0]  # Visual LOD 0

# Vertex coordinates
for pt in lod.points:
    x, y, z = pt.coords        # tuple of 3 floats (metres)
    flags = pt.flags            # int (usually 0)
    # mass = pt.mass            # float, or None; meaningful on the Geometry LOD only

# Face normals (a shared pool, referenced by index)
for i, normal in enumerate(lod.facenormals):
    nx, ny, nz = normal         # tuple of 3 floats (unit vector)

# Faces (triangles or quads)
for face in lod.faces:
    tex = face.texture           # str: "addon\\data\\tex_co.paa" or ""
    mat = face.material          # str: "addon\\data\\mat.rvmat" or ""
    flags = face.flags           # int

    for vert in face.vertices:
        pt_idx = vert.point_index      # index into lod.points
        norm_idx = vert.normal_index   # index into lod.facenormals
        u, v = vert.uv                 # UV coordinates (floats)

        coords = lod.points[pt_idx].coords
        normal = lod.facenormals[norm_idx]

# Named selections
for name, sel in lod.selections.items():
    # sel.points is a dict {Point: weight}
    selected_pts = [p for p, w in sel.points.items() if w > 0]
    selected_faces = [f for f, w in sel.faces.items() if w > 0]
    print(f"  Selection '{name}': {len(selected_pts)} pts, {len(selected_faces)} faces")

# Properties (the Geometry LOD typically has 'class', 'autocenter' and so on)
if hasattr(lod, 'properties'):
    for key, val in lod.properties.items():
        print(f"  Property: {key} = {val}")
```

### Computing the bounding box

```python
def lod_bbox(lod):
    """Returns (min_xyz, max_xyz, center_xyz) for a LOD."""
    if not lod.points:
        return None
    xs = [p.coords[0] for p in lod.points]
    ys = [p.coords[1] for p in lod.points]
    zs = [p.coords[2] for p in lod.points]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    center = ((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, (lo[2]+hi[2])/2)
    return lo, hi, center

lo, hi, center = lod_bbox(model.lods[0])
print(f"BBox: [{lo}] to [{hi}], center={center}")
```

### Collecting all textures and materials

```python
def collect_paths(model):
    """Returns all unique texture and material paths across all LODs."""
    textures = set()
    materials = set()
    for lod in model.lods:
        for face in lod.faces:
            if face.texture:
                textures.add(face.texture)
            if face.material:
                materials.add(face.material)
    return textures, materials

textures, materials = collect_paths(model)
```

---

## Diagnostic and validation toolkit

These patterns detect the most common generation bugs. Run them on every generated `.p3d` before packaging. They are quick checks to run while generating; the gate before a build is `/dayz-p3d-audit`, which covers more and reports CRITICAL, WARNING and NOTE findings. The functions use `lod_bbox` and `classify_lod` from the section above, and they read `model.lods[0]` as the visual LOD 0, so the model's first LOD must be that one.

### 1. Model centering check

DayZ expects the model roughly centered at Y=0 (the ground plane). If the model sits entirely above or below Y=0, the item preview appears offset or inverted.

```python
def check_centering(model):
    """Check that the visual LODs are properly centered around Y=0."""
    issues = []
    lod0 = model.lods[0]
    lo, hi, center = lod_bbox(lod0)

    # Is the model entirely on one side of Y=0?
    ys = [p.coords[1] for p in lod0.points]
    below = sum(1 for y in ys if y < 0)
    above = sum(1 for y in ys if y > 0)
    total = len(ys)

    if below > total * 0.95:
        issues.append(f"MODEL BELOW GROUND: {below}/{total} vertices below Y=0. "
                       f"Center at Y={center[1]:.4f}. Fix: shift all verts by Y+{-center[1]:.4f}")
    elif above > total * 0.95 and center[1] > 0.05:
        issues.append(f"MODEL FLOATING: {above}/{total} vertices above Y=0. "
                       f"Center at Y={center[1]:.4f}")

    # Check ce_center in the Memory LOD
    mem_lod = None
    for lod in model.lods:
        if abs(lod.resolution - 1e15) < 5e13:
            mem_lod = lod
            break
    if mem_lod and "ce_center" in mem_lod.selections:
        ce_pts = [p for p, w in mem_lod.selections["ce_center"].points.items() if w > 0]
        if ce_pts:
            ce = ce_pts[0].coords
            dist = ((ce[0]-center[0])**2 + (ce[1]-center[1])**2 + (ce[2]-center[2])**2)**0.5
            if dist > 0.02:
                issues.append(f"ce_center at {ce} is {dist:.3f}m from geometric center {center}. "
                               f"Should be near the center for correct item preview.")

    return issues
```

### 2. Axis consistency check (visual against Geometry LOD)

Detects when the Blender Z to Y map was applied to the visual LODs but not to the collision LODs, or the other way round. The shape of the bounding box should be the same in all LODs.

```python
def check_axis_consistency(model):
    """Compare bounding box proportions between Visual LOD 0 and the Geometry LOD."""
    issues = []
    visual_lod = None
    geo_lod = None

    for lod in model.lods:
        if lod.resolution == 0.0:
            visual_lod = lod
        elif abs(lod.resolution - 1e13) < 1e11:
            geo_lod = lod

    if not visual_lod or not geo_lod:
        return issues

    v_lo, v_hi, _ = lod_bbox(visual_lod)
    g_lo, g_hi, _ = lod_bbox(geo_lod)

    # Axis sizes
    v_sizes = sorted([v_hi[i] - v_lo[i] for i in range(3)])
    g_sizes = sorted([g_hi[i] - g_lo[i] for i in range(3)])

    # Sizes should be proportionally similar (a margin is allowed for padding)
    for i in range(3):
        if v_sizes[i] > 0.001:
            ratio = g_sizes[i] / v_sizes[i]
            if ratio < 0.7 or ratio > 1.5:
                issues.append(
                    f"AXIS MISMATCH: Visual sorted sizes {[f'{s:.4f}' for s in v_sizes]} "
                    f"vs Geometry sorted sizes {[f'{s:.4f}' for s in g_sizes]}. "
                    f"Likely Z/Y axis rotation applied to visual but not geometry LODs.")
                break

    # Are the Y and Z ranges literally swapped?
    v_y_range = v_hi[1] - v_lo[1]
    v_z_range = v_hi[2] - v_lo[2]
    g_y_range = g_hi[1] - g_lo[1]
    g_z_range = g_hi[2] - g_lo[2]

    if (abs(v_y_range - g_z_range) < 0.01 and abs(v_z_range - g_y_range) < 0.01
            and abs(v_y_range - v_z_range) > 0.02):
        issues.append(
            f"Y/Z AXES SWAPPED: Visual Y={v_y_range:.4f} Z={v_z_range:.4f}, "
            f"Geometry Y={g_y_range:.4f} Z={g_z_range:.4f}. "
            f"Apply same rotation to ALL LODs.")

    return issues
```

It finds the visual LOD by the resolution value `0.0`; a model whose visual LODs start at `1` gets no finding from it.

### 3. UV flip detection

DayZ uses V=0 at the top. If textures were generated with the OpenGL convention (V=0 at the bottom), they appear flipped vertically.

A measurement on a file, not in game (LF_PowerGrid, 2026-09-21; claim CLAIM-P3D-UV-V-TOP-SAMPLED): sampling the texture on the faces of a selection that has its own color (the `light_emit` bulb of a wall lamp) with both readings of V gave a difference of 177.6 against the rest of the model with V=0 at the top and 10.6 with V=0 at the bottom, which agrees with the `(u, 1.0 - v)` of Fix 2. The report gives no unit for the difference, and it was not measured again here.

```python
def check_uv_range(model):
    """Check UV coordinates for out-of-range and degenerate values."""
    issues = []
    lod0 = model.lods[0]

    all_uvs = []
    for face in lod0.faces:
        for vert in face.vertices:
            all_uvs.append(vert.uv)

    if not all_uvs:
        return issues

    us = [uv[0] for uv in all_uvs]
    vs = [uv[1] for uv in all_uvs]

    # Out-of-range UVs
    out_of_range = sum(1 for u, v in all_uvs if u < -0.01 or u > 1.01 or v < -0.01 or v > 1.01)
    if out_of_range > len(all_uvs) * 0.1:
        issues.append(f"UV OUT OF RANGE: {out_of_range}/{len(all_uvs)} UVs outside [0,1]. "
                       f"U range [{min(us):.3f}, {max(us):.3f}], V range [{min(vs):.3f}, {max(vs):.3f}]")

    # Degenerate UVs (all the same coordinate)
    u_spread = max(us) - min(us)
    v_spread = max(vs) - min(vs)
    if u_spread < 0.01 or v_spread < 0.01:
        issues.append(f"DEGENERATE UVs: spread U={u_spread:.4f}, V={v_spread:.4f}. "
                       f"UV unwrap likely failed.")

    return issues
```

> `check_uv_range` only catches out-of-range and degenerate UVs on LOD0, and it does not itself detect a V flip. For the full UV audit (overlap, islands, texel density, mirrored islands) see the UV step in `dayz-p3d-audit/references/manual-checks.md` (SP-051) and `_shared/models/uv-mapping.md`.

### 4. Face Winding Verification

After Rule 12's map the faces are already in the MLOD order (cross product **inward**, normals negated to match). This check only confirms that the vertex order and the stored normals **agree**: it cannot see a mirror, and it cannot tell inward from outward when both are flipped together (Rule 12). When the vertex order points **outward** (both vectors outward, or the faces reversed after a correct export), textures render on the inside only. Normals alone pointing outward, the older convention, disagree with the vertex order and render solid, but they are not what Rule 12 writes; `dayz-p3d-audit/references/winding-diagnostics.md` (Check A) maps each case to its fix. *(Corrected 2026-10-02: this paragraph used to say any disagreement renders on the inside only.)*

The check compares the geometric normal (from the cross product) with the stored normal. *(Corrected 2026-10-02: the docstring below used to give character source MLODs the opposite sign, `< 0`, the det=+1 convention that the characters skill's `check_dayz_winding.py` encoded until it was rewritten for Rule 12 the same day.)*

It reads `model.lods[0]` only, the first LOD in file order, and only for agreement: a file whose first LOD has no faces (a Memory LOD stored first) gets no finding at all, and neither does a collision box wound outward with agreeing normals. It is not Rule 18's per component check.

```python
import numpy as np

def check_face_winding(model):
    """Verify that vertex order and stored normals agree (cross dot stored normal > 0),
    the MLOD convention of Rule 12 on every asset class, characters included. Agreement
    does not give the direction: the characters skill's check_dayz_winding.py reads it
    from the signed volume by winding of each closed shell."""
    issues = []
    lod0 = model.lods[0]

    flipped = 0
    total = 0

    for face in lod0.faces:
        if len(face.vertices) < 3:
            continue

        pts = [lod0.points[v.point_index].coords for v in face.vertices[:3]]
        v1 = np.array(pts[1]) - np.array(pts[0])
        v2 = np.array(pts[2]) - np.array(pts[0])
        geo_normal = np.cross(v1, v2)
        length = np.linalg.norm(geo_normal)
        if length < 1e-10:
            continue
        geo_normal = geo_normal / length

        stored_normal = np.array(lod0.facenormals[face.vertices[0].normal_index])
        dot = np.dot(geo_normal, stored_normal)

        total = total + 1
        if dot < 0:
            flipped = flipped + 1

    if total > 0:
        pct = flipped * 100 / total
        if pct > 50:
            issues.append(f"WINDING REVERSED: {flipped}/{total} faces ({pct:.0f}%) have "
                           f"inverted normals. Check the axis map and the normal sign "
                           f"before reversing faces: Rule 12 maps with det=-1 and "
                           f"negates the normals.")
        elif pct > 5:
            issues.append(f"PARTIAL WINDING ISSUE: {flipped}/{total} faces ({pct:.0f}%) "
                           f"have inverted normals. Some faces may render inside-out.")

    return issues
```

### 5. Proxy system validation

Checks that proxy selections have the right name format and that the proxy faces are present in all visual LODs.

```python
def check_proxy_system(model):
    """Validate proxy selections across all visual LODs."""
    issues = []

    # Find all proxy selections in LOD 0
    lod0 = model.lods[0]
    proxy_sels = [name for name in lod0.selections.keys() if name.startswith("proxy:")]

    if not proxy_sels:
        return issues  # No proxies, nothing to check

    for proxy_name in proxy_sels:
        # Name format: proxy:path\model.NNN
        head, _, index = proxy_name.rpartition(".")
        if not head or not index.isdigit() or len(index) != 3:
            issues.append(f"PROXY NAME FORMAT: '{proxy_name}' should end with .NNN "
                           f"where NNN is a 3-digit index (e.g., .001)")
        elif head.lower().endswith(".p3d"):
            issues.append(f"PROXY NAME FORMAT: '{proxy_name}' keeps .p3d before the index; "
                           f"write the path without it")

        # Presence in all visual LODs (res < 10)
        for i, lod in enumerate(model.lods):
            if lod.resolution < 10 and lod.resolution >= 0:
                if proxy_name not in lod.selections:
                    issues.append(f"PROXY MISSING in LOD {i} (res={lod.resolution}): "
                                   f"'{proxy_name}' not found. Must be in ALL visual LODs.")
                else:
                    sel = lod.selections[proxy_name]
                    pts = [p for p, w in sel.points.items() if w > 0]
                    faces = [f for f, w in sel.faces.items() if w > 0]
                    if len(pts) != 3 or len(faces) != 1:
                        issues.append(f"PROXY GEOMETRY in LOD {i}: expected 3 points + 1 face, "
                                       f"got {len(pts)} points + {len(faces)} faces")

    return issues
```

The source's version required the name to end in `.p3d.NNN`; it was changed here to the form without `.p3d`, which vanilla stores in 17,744 of its 17,891 proxy names (`_shared/models/proxies.md`) and which the fork's `add_proxy` writes.

### 6. Named selection consistency

Animated selections must exist in every LOD type that has to move with the part (visual, Geometry, Fire, View, shadow).

```python
def check_selection_consistency(model):
    """List visual selections that are missing from the collision LODs."""
    issues = []

    # Selections per LOD type
    lod_types = {}
    for lod in model.lods:
        ltype = classify_lod(lod.resolution)
        lod_types[ltype] = set(lod.selections.keys())

    # Selections in Visual 0.0 are looked for in Geometry, Fire and View (except proxies)
    visual_sels = lod_types.get("Visual 0.0", set())

    for sel_name in visual_sels:
        if sel_name.startswith("proxy:"):
            continue  # Proxies are handled by check_proxy_system
        if sel_name in ("zbytek", "AGGzbytek"):
            continue  # Default selection, not critical

        for required_type in ["Geometry", "Fire Geometry", "View Geometry"]:
            if required_type in lod_types and sel_name not in lod_types[required_type]:
                issues.append(f"SELECTION MISSING: '{sel_name}' in Visual but not in {required_type}")

    return issues
```

Read its findings as questions, not as errors: it reports every visual selection that a collision LOD lacks, and a selection used only for a texture swap (`camo`, an LED) or a part whose collision does not move has no reason to be there. An animated part that should block, be shot or be clicked while moving does.

### 7. Collision LOD property check

Validates Rule 16 (`autocenter` on all collision LODs) and Rule 17 (a penetration material on every face), and keeps the Geometry checks for mass and components. Rule 16 is this skill's default for a placed object built from scratch, not something vanilla shows on every model, so on a kit or a handheld item read the `autocenter` finding against `_shared/models/named-properties.md`.

```python
# DayZ collision LOD resolutions
COLLISION_LOD_RANGES = {
    "Geometry":     (0.99e13, 1.01e13),
    "LandContact":  (1.99e15, 2.01e15),
    "Roadway":      (2.99e15, 3.01e15),
    "Hitpoints":    (4.99e15, 5.01e15),
    "ViewGeometry": (5.99e15, 6.01e15),
    "FireGeometry": (6.99e15, 7.01e15),
}


def collision_lod_label(r):
    for name, (lo, hi) in COLLISION_LOD_RANGES.items():
        if lo < r < hi:
            return name
    return None


def check_geometry_properties(model):
    """Verify that the collision LODs have the required properties, mass and materials.
    Rule 16: autocenter=0 on every collision LOD (not just Geometry).
    Rule 17: every face in the collision LODs has a penetration .rvmat material.
    """
    issues = []

    for lod in model.lods:
        label = collision_lod_label(lod.resolution)
        if label is None:
            continue
        props = dict(lod.properties) if hasattr(lod, "properties") else {}

        # Rule 16: autocenter=0 on every collision LOD
        if props.get("autocenter") != "0":
            issues.append(f"{label}: missing 'autocenter=0' named property "
                          f"(found: {props.get('autocenter', '(none)')!r}). "
                          f"Without it the engine recenters this LOD by bbox, "
                          f"displacing collision mesh from visual (Rule 16).")

        # Rule 17: every face must have a penetration .rvmat material
        no_mat = sum(1 for f in lod.faces if not (getattr(f, 'material', '') or '').strip())
        if no_mat > 0:
            issues.append(f"{label}: {no_mat}/{len(lod.faces)} faces missing "
                          f"penetration material. Set face.material to e.g. "
                          f"'dz\\\\data\\\\data\\\\penetration\\\\wood_desk.rvmat' "
                          f"on every collision-LOD face (Rule 17).")

        # Geometry-specific extras
        if label == "Geometry":
            if "class" not in props:
                issues.append("GEOMETRY: missing 'class' property "
                              "(typically 'house' for static objects).")
            no_mass = sum(1 for p in lod.points
                          if getattr(p, 'mass', None) is None or p.mass <= 0)
            if no_mass > 0:
                issues.append(f"GEOMETRY: {no_mass}/{len(lod.points)} points "
                              f"have no mass. All Geometry LOD points need mass.")
            components = [n for n in lod.selections.keys() if n.lower().startswith("component")]
            if not components:
                issues.append("GEOMETRY: no Component selections found. "
                              "Need at least Component01 for collision to work.")

    return issues
```

Two notes on what it asks for. The `class` property is for buildings and placed statics: 821 vanilla models store `class` = `house`, and most vanilla gear stores no `class` at all (`_shared/models/named-properties.md`), so on an item that finding can be ignored. The mass check counts a point whose mass is `None`, the fork's default, as having none; the source's line compared `None` with a number and raised an error on such a point.

### Full validation runner

```python
def validate_p3d(filepath):
    """Run all validation checks on a .p3d file. Returns the list of issues."""
    with open(filepath, "rb") as f:
        model = py3d.P3D(f)

    all_issues = []
    all_issues.extend(check_centering(model))
    all_issues.extend(check_axis_consistency(model))
    all_issues.extend(check_uv_range(model))
    all_issues.extend(check_face_winding(model))
    all_issues.extend(check_proxy_system(model))
    all_issues.extend(check_selection_consistency(model))
    all_issues.extend(check_geometry_properties(model))

    if not all_issues:
        print("ALL CHECKS PASSED")
    else:
        for issue in all_issues:
            print(f"[!] {issue}")

    return all_issues
```

The fork has its own validator as well, `model.validate()`, and `save(verify=True)` reads the file back after writing; what its findings mean is in `py3d-assembly-rules.md`.

---

## Repair patterns

Common fixes that can be applied in code after detection.

### Fix 1: re-center the model at Y=0

```python
def recenter_model_y(model):
    """Shift all LODs so the visual model is centered at Y=0."""
    # Center from Visual LOD 0
    lod0 = model.lods[0]
    ys = [p.coords[1] for p in lod0.points]
    y_center = (min(ys) + max(ys)) / 2.0
    offset = -y_center

    # Apply to ALL LODs (visual, geometry, fire, view, shadow, memory)
    for lod in model.lods:
        for pt in lod.points:
            x, y, z = pt.coords
            pt.coords = (x, y + offset, z)

    print(f"Shifted all vertices by Y+{offset:.4f}")
```

### Fix 2: flip the UV V coordinate

```python
def flip_uv_v(model):
    """Invert the V coordinate on all visual and shadow LODs."""
    count = 0
    for lod in model.lods:
        if lod.resolution < 12000:  # Visual + shadow LODs
            for face in lod.faces:
                for vert in face.vertices:
                    u, v = vert.uv
                    vert.uv = (u, 1.0 - v)
                    count = count + 1
    print(f"Flipped V on {count} vertex UVs")
```

### Fix 3: apply the axis map to specific LODs

```python
def apply_axis_rotation(lod):
    """Blender Z-up to DayZ Y-up (Rule 12): the det=-1 reflection x'=x, y'=z, z'=y."""
    for pt in lod.points:
        x, y, z = pt.coords
        pt.coords = (x, z, y)

    new_normals = []
    for nx, ny, nz in lod.facenormals:
        new_normals.append((-nx, -nz, -ny))   # mapped, then negated: MLOD normals point inward
    lod.facenormals = new_normals

    # Keep the face vertex order: after this map it is already the MLOD (inward) order.
```

### Fix 4: update the Memory LOD's ce_center

```python
def fix_ce_center(model):
    """Set ce_center to the geometric center of Visual LOD 0."""
    lod0 = model.lods[0]
    lo, hi, center = lod_bbox(lod0)

    for lod in model.lods:
        if abs(lod.resolution - 1e15) < 5e13:  # Memory LOD
            if "ce_center" in lod.selections:
                pts = [p for p, w in lod.selections["ce_center"].points.items() if w > 0]
                if pts:
                    pts[0].coords = center
                    print(f"Updated ce_center to {center}")
```

The source's `check_centering` and `fix_ce_center` picked the Memory LOD with `lod.resolution > 1e14`, which is also true of LandContact, Roadway, Paths, Hit points, View Geometry and Fire Geometry. On a model without a Memory LOD, or with one of those stored before it, they read or moved a `ce_center` in the wrong LOD or found none; the test above matches the Memory value only.

---

## The LOD resolution values are the DayZ ones

(Corrected 2026-07-18.) Every LOD resolution in this file uses the DayZ set: Geometry `1e13`, Memory `1e15`, LandContact `2e15`, Roadway `3e15`, Paths `4e15`, Hit points `5e15`, View Geometry `6e15`, Fire Geometry `7e15` (visual below `1e3`; ShadowVolume about `1e4`). The old Arma 3 values `2e13` and `3e13` for Fire and View Geometry, which DayZ does not read as those LODs, are not used. The source of truth in the tool is `py3d.classify_lod_resolution`; in this repo it is the Tier 2 table in `_shared/conventions/assets.md`.

---

## Check mass and centre of mass offline with `binarize.exe`

(No PBO, no deploy. Added 2026-06-05, LL-080 and LL-081.)

Mass and centre of mass are **not** in config for a vehicle: they are baked from the vertex weights of the Geometry LOD when the model is binarized (`skills/_shared/vehicles/vehicle-config-and-modelcfg.md`). So to verify what mass and centre of mass the engine will use, the model has to be binarized, but that does not need a full PBO build, deploy and in-game cycle (about 5 minutes each). Addon Builder calls `binarize.exe` with the same bake, so calling it alone gives the identical result in about 30 seconds:

```
"<DayZ Tools>\Bin\Binarize\binarize.exe" -always -maxProcesses=0 -addon=<addonDir> <srcDir> <dstDir> <wildcard.p3d>
```

`<DayZ Tools>` is the DayZ Tools install folder, which `/dayz-preflight` finds. Then read `ModelInfo.CoM` (and the inertia) straight from the resulting ODOL.

A gotcha, confirmed in game on LFQuad: the source **must live under `P:\`** for binarize to resolve the model's material paths (`lfquad\...`). From a folder outside `P:\` the materials fail to load **but the mass bake still works** (validated against a control), so a run from outside `P:\` is fine when all that is needed is the baked centre of mass and mass, not the textures. *(2026-10-24)* Direct calls on another vehicle import, all from outside `P:\`, did not load their materials with or without `-addon`; the location is one lead among several there, and Addon Builder builds staged outside `P:\` resolved theirs (`skills/dayz-build-pbo/references/addonbuilder-rules.md`, SP-155 rules 1 and 5).

This turns a build, deploy and spawn loop of 5 minutes into an offline loop of 30 seconds for any iteration on mass, centre of mass, ride height or placement of a vehicle. Use it together with the per LOD `#Mass#` check (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD") and the `ECE_PLACE_ON_SURFACE` placement rule: the spawn height is governed by the **baked centre of mass**, not by the lowest Geometry point, LandContact or the bounding box. Empirically `h_origin ≈ CoM.y − Geometry_Ymin`. So a model whose mass never bakes (centre of mass 0) spawns with its origin at ground level, underground, and is thrown out, and no geometry change fixes that until the mass bakes. See also `dayz-p3d-audit/references/vehicle-checks.md`, LL-079 (bisecting the LODs isolated the bug), LL-080 and LL-081.

> Reference tooling in the LFQuad project (specific to it, but the pattern generalizes): a raw reader of the ODOL `ModelInfo` block that prints whether the mass was baked without a full ODOL reader, and a script that strips the mass entry from the Fire Geometry LOD. Neither file is in the imported material.

## Building a collision LOD from scratch (SP-025)

(Added 2026-06-05.) py3d can **construct** collision geometry, not only read it. The object model:

- `Point.coords`, `.flags`, `.mass`
- `Vertex.point_index`, `.normal_index`, `.uv`
- `Face(all_points, all_normals).vertices`, `.flags`, `.texture`, `.material`
- `Selection(all_points, all_faces).points`, `.faces` (both dicts)
- `LOD.resolution`, `.points`, `.facenormals`, `.faces`, `.selections`

Faces reference normals by `normal_index` into the LOD's `facenormals` pool, not inline per face.

Cylinder pattern (for example a wheel collider): build an N-gon ring in the Y-Z plane, pass the points to `scipy.spatial.ConvexHull`; its `simplices` are the faces and its `equations` give the outward normals. After construction, read every face of the hull with Rule 18's per component check (`dot(outward, cross_n) < 0` on every face) and `face.vertices.reverse()` the faces that read outward: the `simplices` come in no consistent order. Then store the **negated** `hull.equations[i, :3]` as the normal of **every** face, reversed or not: the equations point outward on every face, and Rule 12 and SP-169 want winding and normals both inward. (Measured offline 2026-10-02, scipy 1.17.1, a 12-gon cylinder: 22 of 44 faces came wound outward; reversing them and keeping the outward normals on the other 22 left py3d at 50 % agreement and `WARN_WINDING_NORMAL_MISMATCH`, while every normal negated read 100 % with no finding.) The relative comparison against the Visual LOD (`ERR_WINDING_INVERTED`) only triggers that check, and a collider is never reversed to match the Visual LOD (SP-003). Add one selection `component01` over all points and faces; add View Geometry (`6e15`) and Fire Geometry (`7e15`) copies as needed.

*(Aligned 2026-10-02 with SP-003 and the audit's winding killer: this paragraph used to say to compare the collider's winding sign against the Visual LOD of the same model and make the signs match, calling that relative comparison the operational gate.)*

### Needle triangles

(Added 2026-10-24.) Qhull can leave a needle where it triangulates a flat face of the hull with nearly collinear points on its border: a triangle whose area over the square of its longest edge is about 1e-7. A filter of degenerate faces that reads the polygons before they are triangulated does not see it. Measured in game (DayZ 1.29.163709, the SecretRock building, 2026-10-02, hulls built with py3d and `scipy.spatial.ConvexHull`): two components of a lid, with needles of 4.6e-7 and 1.6e-7 and areas of about 3e-8 m², took no `scene_raycast` ray in `geom`, `view` or `fire` all around their outline, while the lid's other two components (1.8e-4 and 8e-4) were hit. Each hull was closed and convex, had mass and was wound inward, and binarize printed nothing about it. Dropping from each component the vertex opposite the longest edge of its needle (one point per component; the hull shrank by less than 0.3 µm) and building the hull again made both components take the rays, with the lid at rest and closed, in the three LODs.

`/dayz-p3d-audit` reads every triangle of the components of the Geometry, View and Fire LODs (a quad as two) and fails one under 1e-6 m², or under 1e-4 of the square of its longest edge, naming the point to drop (`dayz-p3d-audit/references/killers-detail.md`, "Needle triangles in a collision component"). Those are the project's thresholds: the engine's limit lies between 4.6e-7, which failed, and 1.19e-4, which worked (claim CLAIM-P3D-NEEDLE-TRIANGLE-INGAME).

### A script that adds LODs is not idempotent

Running it again over output it already processed **duplicates** the LODs, which is an invalid model. Guard it (skip when a LOD of that resolution already exists) or run it only over the original or a backup. Origin: SP-025, a wheel rebuild script of the LFQuad project, 2026-06-01.
