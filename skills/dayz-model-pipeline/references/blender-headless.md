# Blender headless reference

The Blender Python API (bpy) calls this skill uses to build geometry without the Blender window: primitives, modifiers, UVs, an AO bake, LODs and the OBJ export that py3d assembles into a `.p3d`. This is tool knowledge about Blender, not vanilla game data, so it carries no `P:\` citations. The snippets target Blender 3.2 and later; the notes marked as measured name the Blender version they were measured in. Example output paths are relative (`out/...`); write real output under the mod's folder in `workspace/<ModName>/`.

---

## 1. Setup & Invocation

### Running Blender in Headless Mode

```bash
blender --background --python script.py
blender --background --python script.py -- arg1 arg2 arg3
```

**Key Flags:**
- `--background`: No GUI, non-blocking render
- `--python script.py`: Execute script after startup
- `--`: Pass remaining args to script (read them with `sys.argv[sys.argv.index('--') + 1:]`)

### Initial Scene Cleanup

Always start scripts with this to reset the scene:

```python
import bpy
import sys

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Delete all mesh objects
for obj in bpy.data.objects:
    if obj.type in ('MESH', 'CAMERA', 'LIGHT', 'EMPTY'):
        bpy.data.objects.remove(obj, do_unlink=True)

# Delete orphaned data
bpy.ops.outliner.orphans_purge()

# Verify clean slate
print(f"Objects in scene: {len(bpy.context.scene.objects)}")
```

### Set Units to Metric

DayZ uses metric units internally. Establish this early:

```python
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0  # 1 Blender unit = 1 meter

# Optional: Set grid floor to 10m
scene.unit_settings.length_unit = 'METERS'
```

---

## 2. Geometry Creation Primitives

### Cube with Parameters

```python
# Add cube at origin
bpy.ops.mesh.primitive_cube_add(
    size=2.0,                          # Edge length
    location=(0, 0, 1),               # X, Y, Z position
    scale=(1, 1, 1)                   # Scale factors
)
cube = bpy.context.active_object
cube.name = "Box_01"
```

### Cylinder with Segments

```python
# Industrial cylinder: tall and precise
bpy.ops.mesh.primitive_cylinder_add(
    vertices=16,                       # Segments around circumference
    radius=0.5,                        # Base radius
    depth=2.0,                         # Height (Z-axis)
    location=(0, 0, 1.0)              # Centered on Z
)
cylinder = bpy.context.active_object
cylinder.name = "Cylinder_Tall"
```

### UV Sphere with Segments

```python
# Perfect sphere: segments = longitude rings, ring_count = latitude rings
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=0.5,
    segments=32,                       # Vertical segments (meridians)
    ring_count=16,                     # Horizontal segments (parallels)
    location=(1, 0, 0.5)
)
sphere = bpy.context.active_object
sphere.name = "Sphere_LED"
```

### Cone for Connectors

```python
bpy.ops.mesh.primitive_cone_add(
    vertices=8,                        # Base sides
    radius1=0.3,                       # Base radius
    radius2=0.0,                       # Tip radius (0 = point)
    depth=1.0,                         # Height
    location=(0, 0, 2.5)
)
cone = bpy.context.active_object
cone.name = "Connector"
```

### Custom Mesh from Vertices and Faces

For procedural geometry not in primitives:

```python
import bpy

# Define geometry
vertices = [
    (0, 0, 0),    # 0: origin
    (1, 0, 0),    # 1: +X
    (1, 1, 0),    # 2: +X, +Y
    (0, 1, 0),    # 3: +Y
    (0.5, 0.5, 1) # 4: center top (pyramid apex)
]

faces = [
    (0, 1, 2, 3),      # Base quad
    (0, 1, 4),         # Side triangle
    (1, 2, 4),         # Side triangle
    (2, 3, 4),         # Side triangle
    (3, 0, 4)          # Side triangle
]

# Create mesh and object
mesh = bpy.data.meshes.new("CustomPyramid")
mesh.from_pydata(vertices, [], faces)
mesh.update()

# Create object in scene
obj = bpy.data.objects.new("Pyramid", mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
```

---

## 3. Modifiers (Critical for Quality)

Modifiers transform raw polygons into production models. Order matters!

### Bevel Modifier (Hardens Edges)

```python
obj = bpy.context.active_object

# Create bevel modifier
bevel = obj.modifiers.new(name='Bevel', type='BEVEL')
bevel.width = 0.05                    # Bevel distance in units
bevel.segments = 3                    # Smoothness (higher = smoother)
bevel.limit_method = 'WEIGHT'         # Or 'ANGLE' to auto-detect

# Auto-detect edges > 30 degrees
bevel.limit_method = 'ANGLE'
bevel.angle_limit = 0.5236            # Radians (30 degrees)
bevel.segments = 2
```

### Subdivision Surface (Smooth Geometry)

```python
obj = bpy.context.active_object

# Add subdivision surface
subsurf = obj.modifiers.new(name='Subsurf', type='SUBSURF')
subsurf.levels = 2                    # Viewport subdivisions
subsurf.render_levels = 3             # Render subdivisions (higher for export)
subsurf.type = 'CATMULL_CLARK'        # Smooth type
```

**Use order:** Subdivision BEFORE Bevel for best results.

### Boolean Modifier (Combine Geometry)

```python
# Create two objects first
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
base = bpy.context.active_object
base.name = 'Base'

bpy.ops.mesh.primitive_cube_add(size=1, location=(0.75, 0, 0))
cutter = bpy.context.active_object
cutter.name = 'Cutter'

# Select base, add boolean
base.select_set(True)
bpy.context.view_layer.objects.active = base

bool_mod = base.modifiers.new(name='Bool', type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'     # 'UNION', 'INTERSECT', 'DIFFERENCE'
bool_mod.object = cutter              # Reference object

# Hide cutter from render
cutter.hide_render = True
cutter.hide_viewport = False          # Show in edit but not render
```

### Decimate Modifier (LOD Generation)

Decimating a LOD the player will see is the user's call: say which LODs and ratios you plan and wait for approval (the decimation gate in `SKILL.md`). Collision and view LODs may be decimated without asking. For curved surfaces use the COLLAPSE mode and protect the features that matter with an inverted vertex group (`blender-import-preflight.md`).

```python
obj = bpy.context.active_object

decimator = obj.modifiers.new(name='Decimate', type='DECIMATE')
decimator.ratio = 0.5                 # 50% of original faces (0.0 to 1.0)

# For aggressive LODs
decimator.ratio = 0.25                # 25%
decimator.ratio = 0.12                # 12% (extreme LOD)
```

### Solidify Modifier (Thin Walls)

```python
obj = bpy.context.active_object

solidify = obj.modifiers.new(name='Solidify', type='SOLIDIFY')
solidify.thickness = 0.02             # Wall thickness (units)
solidify.offset = 0.0                 # 0 = symmetric, 1 = outward only
solidify.use_even_offset = True
```

### Apply Modifiers

```python
# Apply modifiers before export

# Set context to object
with bpy.context.temp_override(object=obj):
    bpy.ops.object.modifier_apply(modifier='Subsurf')
    bpy.ops.object.modifier_apply(modifier='Bevel')
    bpy.ops.object.modifier_apply(modifier='Bool')
    # Order: subsurf, bevel, boolean, decimate, solidify, etc.
```

`temp_override` needs Blender 3.2 or later. Without it:

```python
def apply_modifiers(obj):
    """Apply all modifiers to an object"""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    for modifier in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    obj.select_set(False)
```

---

## 4. UV Mapping

### Smart UV Project (Auto Layout)

Smart UV Project runs in Edit mode.

```python
obj = bpy.context.active_object

# Enter edit mode
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')

# Select all faces
bpy.ops.mesh.select_all(action='SELECT')

# Apply smart project
bpy.ops.uv.smart_project(
    angle_limit=1.5708,                # ~90 degrees (radians)
    island_margin=0.02,                # Space between UV islands
    area_weight=0.0,
    stretch_limit=0.5
)

# Return to object mode
bpy.ops.object.mode_set(mode='OBJECT')
```

### Ensure UV Layer Exists

```python
obj = bpy.context.active_object
mesh = obj.data

# Create UV layer if missing
if not mesh.uv_layers:
    mesh.uv_layers.new(name='UVMap')

# Set as active
mesh.uv_layers.active = mesh.uv_layers[0]
```

### Complete UV Setup Workflow

```python
def setup_uvs(obj):
    """Complete UVs: create layer, unwrap, verify"""
    mesh = obj.data

    # Create UV layer
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='UVMap')
    mesh.uv_layers.active = mesh.uv_layers[0]

    # Unwrap
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.5708, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"UVs set for {obj.name}")

# Use it
setup_uvs(cube)
```

---

## 5. Materials & Vertex Colors

### Create and Assign Material

```python
import bpy

# Create material
mat = bpy.data.materials.new(name='Material_Base')
mat.use_nodes = True

# Access shader tree
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)  # RGBA

# Assign to object
obj = bpy.context.active_object
if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)
```

### Assign Material to Specific Faces

```python
def assign_material_to_faces(obj, material, face_indices):
    """Assign material to specific faces by index"""
    mesh = obj.data

    # Ensure material in object
    mat_index = None
    for i, mat in enumerate(obj.data.materials):
        if mat.name == material.name:
            mat_index = i
            break
    if mat_index is None:
        obj.data.materials.append(material)
        mat_index = len(obj.data.materials) - 1

    # Assign to faces
    for face_idx in face_indices:
        mesh.polygons[face_idx].material_index = mat_index

# Usage
faces_to_paint = [0, 1, 2]  # First 3 faces
assign_material_to_faces(obj, mat, faces_to_paint)
```

### Vertex Color Layers (for AO Baking)

```python
obj = bpy.context.active_object
mesh = obj.data

# Create vertex color layer
if "AO" not in mesh.color_attributes:
    mesh.color_attributes.new(name="AO", type='FLOAT_COLOR', domain='POINT')

# Access and modify
color_layer = mesh.color_attributes["AO"]
for vertex in mesh.vertices:
    color_layer.data[vertex.index].color = (1, 1, 1, 1)  # White (no occlusion)
```

---

## 6. AO Baking (Cycles)

Complete ambient occlusion bake workflow:

```python
import bpy
import os

def bake_ao(obj, output_path, resolution=1024):
    """Bake ambient occlusion to texture and save"""

    mesh = obj.data

    # 1. Set render engine to CYCLES
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 64  # More = better quality

    # 2. Create image texture
    img = bpy.data.images.new(
        name="AO_Bake",
        width=resolution,
        height=resolution,
        alpha=False
    )

    # 3. Create material with image texture node
    mat = bpy.data.materials.new(name="AO_Material")
    mat.use_nodes = True

    # Clear default nodes
    mat.node_tree.nodes.clear()

    # Add image texture node
    img_node = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    img_node.image = img
    mat.node_tree.nodes.active = img_node  # the bake writes to the active image node

    # Add BSDF for bake reference
    bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')

    # Connect for display (not required for bake, but good practice)
    mat.node_tree.links.new(bsdf.outputs['BSDF'],
                             mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial').inputs[0])

    # 4. Ensure UV layer exists
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='UVMap')

    # 5. Assign material
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # 6. Select object for bake
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # 7. Bake ambient occlusion
    bpy.ops.object.bake(
        type='AO',
        margin=4,
        use_clear=True
    )

    # 8. Save image
    img.filepath_raw = output_path
    img.file_format = 'PNG'
    img.save()

    print(f"AO baked and saved: {output_path}")
    return img

# Usage
bake_ao(cube, "out/ao_bake.png", resolution=2048)
```

---

## 7. Export (OBJ for DayZ)

### Core OBJ Export (Blender coordinates; py3d converts)

DayZ is Y-up and Blender Z-up, and the two also differ in handedness. Export the OBJ in
Blender's own coordinates and convert once, in py3d, with the Rule 12 map (`critical-rules.md` Rule 12). Measured
2026-10-02 in Blender 5.1.1 (`wm.obj_export`, one vertex at `(1, 2, 3)`): `forward_axis='Y', up_axis='Z'`
writes `(1, 2, 3)`; the default `'NEGATIVE_Z'`/`'Y'` writes `(1, 3, -2)`, the det=+1 rotation `(x, z, -y)`
that Rule 12 retired; `'NEGATIVE_Y'`/`'Z'` writes `(-1, -2, 3)`, a 180° turn about the vertical. Followed by
Rule 12 in py3d, the first of those two lands the model on its back and the second faces it backwards.
*(Corrected 2026-10-02: this recipe exported with `'NEGATIVE_Z'`/`'Y'` as a "DayZ axis correction", and its
calls used parameter names that Blender 5.1.1 rejects with `TypeError`.)*

```python
import bpy
import os

def export_obj(obj, filepath):
    """Export one object as OBJ in Blender's own coordinates (py3d applies Rule 12 once)."""

    # Select only this object
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=filepath,
        check_existing=False,
        export_selected_objects=True,  # this object only, not the whole scene
        forward_axis='Y',              # Y forward + Z up = no axis conversion
        up_axis='Z',
        global_scale=1.0,
        apply_modifiers=True,
        export_uv=True,
        export_normals=True,
        export_materials=True,
    )

    print(f"Exported: {filepath}")

# Usage
export_obj(cube, "out/box_LOD0.obj")
```

### Export Multiple Objects (LODs)

```python
def export_lods(objects_dict, output_dir):
    """Export multiple objects as OBJ LOD set

    Args:
        objects_dict: {'LOD0': obj1, 'LOD1': obj2, ...}
        output_dir: directory to save files
    """

    os.makedirs(output_dir, exist_ok=True)

    for lod_name, obj in objects_dict.items():
        filepath = os.path.join(output_dir, f"{lod_name}.obj")
        export_obj(obj, filepath)

# Usage
export_lods({
    'LOD0': original_box,
    'LOD1': decimated_50,
    'LOD2': decimated_25,
    'LOD3': decimated_12
}, 'out/lods/')
```

---

## 8. LOD Generation via Decimate

Complete workflow: duplicate objects, apply Decimator at different ratios.

```python
import bpy

def generate_lods(source_obj, output_dir, lod_ratios=(1.0, 0.5, 0.25, 0.12)):
    """Generate LOD objects from single mesh

    Args:
        source_obj: Original object to LOD-ify
        output_dir: Where to save OBJ files
        lod_ratios: Decimation ratios per LOD (1.0 = 100%, 0.5 = 50%, etc)

    Returns:
        dict of LOD name -> object
    """

    lod_objects = {}

    for i, ratio in enumerate(lod_ratios):

        # Duplicate source
        bpy.ops.object.select_all(action='DESELECT')
        source_obj.select_set(True)
        bpy.context.view_layer.objects.active = source_obj
        bpy.ops.object.duplicate()

        lod_obj = bpy.context.active_object
        lod_name = f"LOD{i}"
        lod_obj.name = lod_name

        # Apply existing modifiers first
        for mod in list(lod_obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)

        # Only decimate if not 100%
        if ratio < 1.0:
            decim = lod_obj.modifiers.new(name='Decimate', type='DECIMATE')
            decim.ratio = ratio

            # Apply decimator
            bpy.ops.object.modifier_apply(modifier='Decimate')

        # Export
        lod_file = f"{output_dir}/{lod_name}.obj"
        export_obj(lod_obj, lod_file)

        lod_objects[lod_name] = lod_obj
        print(f"Generated {lod_name}: {int(ratio * 100)}% faces")

    return lod_objects

# Usage
lods = generate_lods(original_box, 'out/lods/')
```

**Recommended DayZ Ratios:**
- LOD0: 100% (full detail)
- LOD1: 50% (medium)
- LOD2: 25% (low)
- LOD3: 12% (very low, far view)

These are visual LODs: get the user's approval for the ratios before running the loop.

---

## 9. Common Mistakes & Fixes

- **Headless `.py` execution and invented bpy APIs (measured in Blender 5.2.0 LTS, 2026-08-13).**
  - `blender --background --python X.py` still exits 0 when `X.py` raises an uncaught exception (an `AttributeError` mid-script still prints "Blender quit"). Do not treat `returncode` as PASS. Scan stdout+stderr for `Traceback (most recent call last)` and also require the expected output (e.g. a per-object summary) as positive proof the script reached the end.
  - `bmesh.ops.create_torus` does not exist — in 5.2 `bmesh.ops` offers only `create_circle`, `create_cone`, `create_cube`, `create_grid`, `create_icosphere`, `create_monkey`, `create_uvsphere` and `create_vert`. `bpy.ops.mesh.primitive_torus_add` is the operator; a parametric ring via `from_pydata` avoids both. Same class of failure as `BevelModifier.offset` (the field is `.width`): plausible-but-invented bpy APIs.
  - `Material.use_nodes` is marked for removal in Blender 6.0.

### Forgetting to Apply Modifiers Before Export

**Problem:** Modifiers visible in Blender but missing from exported OBJ.

```python
# WRONG
bpy.ops.wm.obj_export(filepath="model.obj", forward_axis='Y', up_axis='Z')

# RIGHT (axes as in Core OBJ Export: Blender's own coordinates)
def apply_all_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=mod.name)

apply_all_modifiers(cube)
bpy.ops.wm.obj_export(filepath="model.obj", forward_axis='Y', up_axis='Z')
```

### Not Selecting Object Before Operations

**Problem:** "RuntimeError: Operator bpy.ops.object.modifier_apply.poll() failed"

```python
# WRONG
obj = bpy.data.objects['Cube']
bpy.ops.object.modifier_apply(modifier='Bevel')  # Crashes: no context

# RIGHT
obj = bpy.data.objects['Cube']
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.modifier_apply(modifier='Bevel')  # OK
```

### Scale Not Applied

**Problem:** Object appears small in DayZ despite correct units.

```python
# WRONG
cube_obj.scale = (2, 2, 2)
export_obj(cube_obj, "model.obj")  # Scale lost

# RIGHT: Apply transform
cube_obj.scale = (2, 2, 2)
bpy.context.view_layer.objects.active = cube_obj
cube_obj.select_set(True)
bpy.ops.object.transform_apply(scale=True)
export_obj(cube_obj, "model.obj")
```

### Normals Flipped (Inside-Out)

**Problem:** Model appears dark or renders incorrectly due to inverted normals.

```python
# Fix: Recalculate normals
obj = bpy.context.active_object

bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)  # inside=False = outward
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## 10. Complete Example Script: Industrial Electrical Box

Production-ready script generates a DayZ electrical device with 4 LOD levels.

```python
#!/usr/bin/env blender --background --python

"""
DayZ Electrical Box Model Generator

Generates a realistic industrial electrical enclosure:
  - Main steel box body (beveled edges)
  - Cylindrical power connector on top
  - LED indicator light
  - Smart UV mapped
  - 4 LOD levels (100%, 50%, 25%, 12%)
"""

import bpy
import os
import sys

# Clean scene
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Set units
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0

# ============================================================================
# 1. CREATE BOX BODY
# ============================================================================

bpy.ops.mesh.primitive_cube_add(
    size=1.0,
    location=(0, 0, 0.5)
)
box_body = bpy.context.active_object
box_body.name = "Box_Body"
box_body.scale = (0.8, 0.5, 1.0)

# Apply scale
bpy.context.view_layer.objects.active = box_body
bpy.ops.object.transform_apply(scale=True)

# Add bevel for industrial look
bevel = box_body.modifiers.new(name='Bevel', type='BEVEL')
bevel.width = 0.02
bevel.segments = 3
bevel.limit_method = 'ANGLE'
bevel.angle_limit = 0.5236  # 30 degrees

# Apply bevel
bpy.ops.object.modifier_apply(modifier='Bevel')

# ============================================================================
# 2. CREATE POWER CONNECTOR (cylinder on top)
# ============================================================================

bpy.ops.mesh.primitive_cylinder_add(
    vertices=12,
    radius=0.15,
    depth=0.3,
    location=(0, 0, 1.05)
)
connector = bpy.context.active_object
connector.name = "Connector_Power"

# Bevel connector edges
conn_bevel = connector.modifiers.new(name='Bevel', type='BEVEL')
conn_bevel.width = 0.01
conn_bevel.segments = 2
bpy.ops.object.modifier_apply(modifier='Bevel')

# ============================================================================
# 3. CREATE LED INDICATOR (small sphere)
# ============================================================================

bpy.ops.mesh.primitive_uv_sphere_add(
    radius=0.05,
    segments=16,
    ring_count=8,
    location=(0.25, 0.18, 0.8)
)
led = bpy.context.active_object
led.name = "LED_Indicator"

# LED material (emissive red)
led_mat = bpy.data.materials.new(name='Material_LED')
led_mat.use_nodes = True
bsdf = led_mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)  # Red
emission = bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')  # renamed in Blender 4.0
emission.default_value = (1.0, 0.0, 0.0, 1.0)
bsdf.inputs['Emission Strength'].default_value = 2.0

led.data.materials.append(led_mat)

# ============================================================================
# 4. UV MAPPING
# ============================================================================

def setup_uvs(obj):
    """UV unwrap object"""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='UVMap')
    mesh.uv_layers.active = mesh.uv_layers[0]

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.5708, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

for obj in [box_body, connector, led]:
    setup_uvs(obj)

# ============================================================================
# 5. APPLY MATERIALS
# ============================================================================

# Main box material (steel)
steel_mat = bpy.data.materials.new(name='Material_Steel')
steel_mat.use_nodes = True
steel_bsdf = steel_mat.node_tree.nodes['Principled BSDF']
steel_bsdf.inputs['Base Color'].default_value = (0.3, 0.3, 0.3, 1.0)  # Dark gray
steel_bsdf.inputs['Metallic'].default_value = 0.8
steel_bsdf.inputs['Roughness'].default_value = 0.4

box_body.data.materials.append(steel_mat)
connector.data.materials.append(steel_mat)

# ============================================================================
# 6. GENERATE LOD VARIANTS
# ============================================================================

def export_obj(obj, filepath):
    """Export in Blender's own coordinates; py3d applies Rule 12 (see Core OBJ Export)"""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=filepath,
        check_existing=False,
        export_selected_objects=True,
        forward_axis='Y',
        up_axis='Z',
        global_scale=1.0,
        apply_modifiers=True,
        export_materials=True,
        export_uv=True,
        export_normals=True
    )
    print(f"Exported: {filepath}")

def generate_lods(source_objs, output_dir, lod_ratios=(1.0, 0.5, 0.25, 0.12)):
    """Generate LOD set from multiple source objects"""

    os.makedirs(output_dir, exist_ok=True)
    lod_dict = {f'LOD{i}': [] for i in range(len(lod_ratios))}

    for source in source_objs:
        for i, ratio in enumerate(lod_ratios):

            # Duplicate
            bpy.ops.object.select_all(action='DESELECT')
            source.select_set(True)
            bpy.context.view_layer.objects.active = source
            bpy.ops.object.duplicate()

            lod_obj = bpy.context.active_object
            lod_name = f"{source.name}_LOD{i}"
            lod_obj.name = lod_name

            # Apply modifiers
            for mod in list(lod_obj.modifiers):
                bpy.ops.object.modifier_apply(modifier=mod.name)

            # Decimate if not 100%
            if ratio < 1.0:
                decim = lod_obj.modifiers.new(name='Decimate', type='DECIMATE')
                decim.ratio = ratio
                bpy.ops.object.modifier_apply(modifier='Decimate')

            lod_dict[f'LOD{i}'].append(lod_obj)

            print(f"Generated {lod_name}: {int(ratio * 100)}% faces")

    return lod_dict

# Generate LODs
lod_dict = generate_lods([box_body, connector, led], 'out/dayz_electrical/')

# ============================================================================
# 7. EXPORT ALL LODS
# ============================================================================

for i in range(4):
    lod_name = f'LOD{i}'

    # Join all LOD objects for this level
    lod_objects = lod_dict[lod_name]

    if lod_objects:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in lod_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = lod_objects[0]

        # Join (merge into first object)
        bpy.ops.object.join()
        combined = bpy.context.active_object
        combined.name = lod_name

        # Export
        filepath = f'out/dayz_electrical/{lod_name}.obj'
        export_obj(combined, filepath)

print("\n=== COMPLETE ===")
print(f"LOD models exported to: out/dayz_electrical/")
print("LOD0.obj (100%), LOD1.obj (50%), LOD2.obj (25%), LOD3.obj (12%)")
```

**Run it:**
```bash
blender --background --python generate_electrical_box.py
```

---

## Tips & Best Practices

1. **Always apply modifiers before export** — hidden data will be lost
2. **Subdivision first, then bevel** — order matters for quality
3. **Test axis handling** — export in Blender's own coordinates and convert once in py3d (Rule 12); check an asymmetric feature in game
4. **Use Smart UV Project** — faster than manual mapping
5. **Keep LOD ratios consistent** — 0.5, 0.25, 0.12 work well
6. **Check normals** — flipped normals cause rendering artifacts
7. **Name objects clearly** — "LOD0", "LOD1" makes automation easier
8. **Save .blend before batch export** — debugging is easier
9. **Use vertex count as metric** — decimate ratio affects export size
10. **Bake AO as separate pass** — texture baking is separate from geometry

---

## Reference: Blender 3.x+ API Versions

This guide targets **Blender 3.2+**.

**Replaced:**
- `bpy.ops.export_scene.obj()` → use `bpy.ops.wm.obj_export()`
- The Principled BSDF input `Emission` → `Emission Color` from Blender 4.0

**Current (3.2+):**
- `bpy.context.temp_override()` for context-safe ops
- Image bake with `bpy.ops.object.bake()`

---

## Quick Reference: Full Script Template

```python
#!/usr/bin/env blender --background --python

import bpy
import os

# Clean
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Setup
bpy.context.scene.unit_settings.system = 'METRIC'

# Create geometry
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
obj = bpy.context.active_object
obj.name = "Model"

# Modify
bevel = obj.modifiers.new(name='Bevel', type='BEVEL')
bevel.width = 0.02
bpy.ops.object.modifier_apply(modifier='Bevel')

# UV Map
mesh = obj.data
if not mesh.uv_layers:
    mesh.uv_layers.new(name='UVMap')

bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.5708, island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')

# Export
bpy.ops.wm.obj_export(
    filepath="out/model.obj",
    forward_axis='Y',   # Blender's own coordinates; py3d applies Rule 12
    up_axis='Z',
    apply_modifiers=True,
    export_uv=True,
    export_normals=True
)

print("Done!")
```
