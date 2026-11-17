# Blender workflow for external models (Path C)

Manual Blender steps for a mesh that came from somewhere else: import, cleanup, UVs, LODs and the OBJ export that py3d assembles. This is tool and workflow knowledge about Blender, not vanilla game data, so it carries no `P:\` citations; the Blender facts marked as measured were measured in Blender 5.1.1.

## Overview

This guide covers the manual Blender workflow for **Path C** of the DayZ model pipeline: when you have an external 3D model (from third-party sources, asset libraries, or other tools) that needs to be cleaned up and prepared for DayZ.

Before importing an FBX into Blender 5.x read `blender-import-preflight.md`: custom split normals can crash the importer, and hidden objects are skipped silently on export.

**This path is for:**
- Models downloaded from 3D asset stores
- Models created in other 3D applications (3ds Max, Maya, ZBrush, etc.)
- Externally-commissioned models
- Legacy assets needing conversion

**This path is NOT for:**
- Procedurally generated models (use Path A or B)
- Models created directly in Blender for DayZ (use Path A)

---

## Supported Import Formats

Blender can import the following formats suitable for DayZ:

| Format | Extension | Pros | Cons |
|--------|-----------|------|------|
| **Autodesk FBX** | `.fbx` | Best material/skeleton support, industry standard | Larger files, can contain junk data |
| **Wavefront OBJ** | `.obj` | Simple, widely compatible, clean | No materials or animations in file itself |
| **glTF/GLB** | `.glb` / `.gltf` | Modern, web standard, compact | Blender support varies by version |
| **Stereolithography** | `.stl` | Good for CAD imports | Geometry only, no UVs or materials |
| **Blender Native** | `.blend` | No import needed, fully compatible | Already in Blender format |

---

## Pre-Import Checklist

Before opening your model in Blender, verify these properties:

- [ ] **Model scale**: Is it in meters? Centimeters? Units unknown? (Affects DayZ scaling)
- [ ] **Polygon count**: Too many polygons will be optimized later (target: <2000 for small objects)
- [ ] **UV maps**: Are UV coordinates already present? Or will you need to unwrap?
- [ ] **Materials/textures**: Included in file? Separate files? Missing entirely?
- [ ] **Skeleton/armature**: If animated, is skeleton included and properly rigged?
- [ ] **Coordinate system**: Model created in Z-up or Y-up application? (Blender is Z-up; DayZ is Y-up)

Document these details before importing—they guide your cleanup strategy.

---

## Import Process (Blender Python Script)

Use these Python snippets to automate or semi-automate imports:

```python
import bpy

# Option 1: Clear scene and import FBX
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.fbx(filepath='/path/to/model.fbx')

# Option 2: Import OBJ
bpy.ops.wm.obj_import(filepath='/path/to/model.obj')

# Option 3: Import GLTF/GLB
bpy.ops.import_scene.gltf(filepath='/path/to/model.glb')

# Option 4: Open existing .blend file (no import, just open)
bpy.ops.wm.open_mainfile(filepath='/path/to/existing.blend')
```

**GUI Method:** File → Import → [format], then select your file.

---

## Post-Import Cleanup

After importing, your model likely needs cleanup. Follow these steps in order:

### 1. Check and Apply Scale

If the model isn't in meters, scale it to DayZ units:

```python
import bpy

obj = bpy.context.active_object

# If model was in centimeters, convert to meters (1cm = 0.01m)
obj.scale = (0.01, 0.01, 0.01)

# Apply the scale transformation
bpy.ops.object.transform_apply(scale=True)

# Verify: object should now be ~1 unit tall for a human-sized item
```

**Common conversions:**
- Centimeters → meters: multiply by 0.01
- Millimeters → meters: multiply by 0.001
- Feet → meters: multiply by 0.3048

### 2. Remove Extra Objects

Delete objects you don't need:

```python
# Deselect all first
bpy.ops.object.select_all(action='DESELECT')

# Select and delete cameras
for obj in bpy.data.objects:
    if obj.type == 'CAMERA':
        obj.select_set(True)
        bpy.ops.object.delete()

# Delete lights
for obj in bpy.data.objects:
    if obj.type == 'LIGHT':
        obj.select_set(True)
        bpy.ops.object.delete()

# Keep only mesh objects (and armature if animated)
```

### 3. Join Meshes

If the model is split into many separate mesh objects that should be one:

```python
# Select all mesh objects
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)

# Set the first mesh as active, then join
bpy.context.view_layer.objects.active = bpy.data.objects['MeshName']
bpy.ops.object.join()
```

### 4. Fix Normals

Ensure normals point outward (not inside):

```python
# Enter edit mode, select all, recalculate normals
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
```

### 5. Remove Doubles

Clean up duplicate vertices that cause artifacts:

```python
# In edit mode, remove doubles
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.object.mode_set(mode='OBJECT')
```

### 6. Check Polygon Count

Verify your model won't be too heavy for DayZ:

```python
obj = bpy.context.active_object
poly_count = len(obj.data.polygons)
print(f"Polygon count: {poly_count}")

# For small objects, target <2000 polygons
# For medium objects, target <5000 polygons
# For large props, may go higher but requires LOD optimization
```

---

## Optimization for DayZ

DayZ models must be optimized to run smoothly in-game:

### Decimate (reduce polygon count)

Decimating a mesh the player will see is the user's call: say what you plan to decimate and by how much, and wait for approval before running it (the decimation gate in `SKILL.md`). Collision and view LODs may be decimated without asking.

If your model is too dense:

```python
obj = bpy.context.active_object
decimate = obj.modifiers.new(name='Decimate', type='DECIMATE')
decimate.ratio = 0.5  # Reduce to 50% of original polygons
bpy.ops.object.modifier_apply(modifier='Decimate')
```

### Remove Interior Faces

Delete faces that will never be visible:

1. Enter edit mode (`Tab`)
2. Switch to face select mode (press `3`)
3. Select hidden/interior faces and delete them
4. Apply with `X` → Delete Faces

### Separate Moving Parts

If the model has moving parts (doors, switches, etc.), separate them into distinct objects:

```python
# In edit mode, select faces of one part
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
# Select desired faces with box select (B) or by material

# Separate into new object
bpy.ops.mesh.separate(type='SELECTED')
bpy.ops.object.mode_set(mode='OBJECT')
```

### Name Objects Meaningfully

For DayZ, name each object so it becomes a named selection later:

```python
# Rename the active object
bpy.context.active_object.name = 'body'

# List and rename multiple objects
for obj in bpy.data.objects:
    if 'Cube' in obj.name:
        obj.name = 'cover'
    elif 'Sphere' in obj.name:
        obj.name = 'light_lens'
```

---

## UV Preparation

UV maps control how textures wrap around your model. DayZ requires clean UVs:

### If Model Already Has UVs

Verify they're clean:
- No overlapping islands (causes baking artifacts)
- Proper margins between islands (prevents texture bleeding)
- Each material zone separated into its own UV island

### If Model Has No UVs

Use Smart UV Project:

```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Pack UV Islands

Ensure islands don't overlap:

```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(margin=0.01)
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## LOD Generation

DayZ uses Level-of-Detail (LOD) models to optimize performance. Create 2-4 LOD versions:

1. **LOD 0 (detailed)**: Full polygon count, used at close distance
2. **LOD 1 (medium)**: ~50% of LOD0 polygons
3. **LOD 2 (simple)**: ~25% of LOD0 polygons
4. **LOD 3 (distance)**: ~12% of LOD0 polygons (for very large objects)

### Generate LODs

```python
# Duplicate LOD0 for each LOD level
original = bpy.context.active_object

for lod_level, ratio in [(1, 0.5), (2, 0.25), (3, 0.12)]:
    # Duplicate the original, not the LOD made on the previous pass
    bpy.ops.object.select_all(action='DESELECT')
    original.select_set(True)
    bpy.context.view_layer.objects.active = original
    bpy.ops.object.duplicate()
    lod_obj = bpy.context.active_object
    lod_obj.name = f'{original.name}_lod{lod_level}'

    # Add and apply decimate
    decimate = lod_obj.modifiers.new(name='Decimate', type='DECIMATE')
    decimate.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='Decimate')
```

**Important**: After decimating, verify UVs didn't break. Re-pack if needed. These LODs are visual, so the decimation gate above applies to each of them.

---

## Export for py3d Assembly

After cleanup and LOD generation, export for py3d to assemble into final `.p3d`:

### Export Settings (per LOD)

```python
# Export each LOD as OBJ in Blender's own axes; py3d converts to DayZ (Rule 12, critical-rules.md)
# File > Export As > Wavefront (.obj)
```

**Critical export settings:**
- **Forward axis**: Y (no axis conversion; see Coordinate System Gotcha)
- **Up axis**: Z
- **Scale**: 1.0 (already scaled in cleanup step)
- **Apply modifiers**: Yes
- **Smooth groups**: Yes

Or via Python (Blender 5.1.1; select the LOD object first):

```python
bpy.ops.wm.obj_export(
    filepath='out/model_lod0.obj',
    export_selected_objects=True,
    forward_axis='Y',
    up_axis='Z',
    apply_modifiers=True
)
```

### Export Each LOD Separately

Export each LOD (LOD0, LOD1, LOD2, LOD3) as separate `.obj` files. py3d will combine them into the final `.p3d`.

---

## Coordinate System Gotcha

**This is critical**: Blender uses Z-up; DayZ uses Y-up.

| Application | Up Axis | Forward Axis |
|-------------|---------|--------------|
| **Blender** | Z | -Y |
| **DayZ** | Y | -Z |

When exporting OBJ for py3d assembly, use these settings:
- Forward: **Y**
- Up: **Z**

That is no conversion at all: the OBJ keeps raw Blender coordinates (Z up), and the conversion happens once, in
py3d. Measured 2026-10-02 in Blender 5.1.1 (`wm.obj_export`, one vertex at `(1, 2, 3)`): Forward Y / Up Z writes
`(1, 2, 3)`. Forward -Y / Up Z writes `(-1, -2, 3)`, a 180° turn about the vertical; after Rule 12 the model faces
backwards. The default Forward -Z / Up Y writes `(1, 3, -2)`, the det=+1 rotation `(x, z, -y)`; after Rule 12 the
model lies on its back, and on its own it is the map Rule 12 measured as shipping a mirrored model. The exporter's
Forward names the file axis that Blender's +Y becomes, not the way a model faces: a character in Blender faces -Y
(table above) and still exports with Forward Y. *(Corrected 2026-10-02: this section said Forward -Y, inferred and
not tested, and the Python example passed `'-Y'`, which Blender rejects; the enum value is `'NEGATIVE_Y'`.)*

**Transforming in py3d**: apply the Rule 12 map `x'=x, y'=z, z'=y` (det=-1) with negated normals, keeping the face order
(`critical-rules.md` Rule 12, with the measurements in `axes-and-winding.md`; the old `z'=-y` rotation ships a mirrored model).

---

## Texture Extraction and Naming

If your model came with textures, extract and rename them per DayZ conventions:

### DayZ Texture Naming

| Map Type | DayZ Suffix | Input Name Example |
|----------|-------------|-------------------|
| Diffuse/Albedo | `_co.png` | `model_co.png` |
| Normal Map | `_nohq.png` | `model_nohq.png` |
| Specular/Roughness | `_smdi.png` | `model_smdi.png` |

### Extract and Convert

1. In Blender, bake textures to image files if needed
2. Use Substance Painter, Textura, or similar for channel repacking
3. Verify the normal map convention (DirectX against OpenGL). DayZ `_nohq` maps use the DirectX one (green pointing down); Blender bakes OpenGL by default, so invert the green channel of a Blender bake. This is tool knowledge, not something a file on `P:\` states
4. Save final textures to your mod's `data/model/` directory
5. Convert each `.png` to `.paa` with `/dayz-pack-texture`

If no textures came with the model, generate procedurally (see `procedural-textures.md`).

---

## Common Problems and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| **Model appears tiny or huge** | Scale incorrect | Apply scale transform, verify units in meters |
| **Model is inside-out (black)** | Normals flipped | Recalculate normals outside: `normals_make_consistent(inside=False)` |
| **Black faces or holes** | Duplicate vertices | Run remove doubles with threshold 0.0001 |
| **UV seams visible in-game** | Tight UV margins | Re-pack islands with larger margin (0.02+) |
| **Model faces wrong direction** | Export axes converted, or the model faces another way in Blender | Re-export with Forward=Y, Up=Z (no conversion; py3d applies Rule 12 once). If it still faces wrong, turn the model in Blender so its front looks down -Y; do not fix the facing through the export axes |
| **Textures look stretched** | UVs not unwrapped properly | Run Smart UV Project, manual layout |
| **LODs are distorted** | Decimate broke geometry | Use Voxel Remesh modifier instead for preservation |
| **Smooth shading looks jagged** | Auto-smooth threshold too low | Increase auto-smooth angle (60-80 degrees typical) |

---

## Next Steps

After cleanup and export:

1. **Run py3d** to assemble OBJ files into `.p3d` with LODs
2. **Bake ambient occlusion** if textures need shading
3. **Add named selections** for interactive parts (doors, switches)
4. **Create model.cfg** for animations if applicable
5. **Audit** the `.p3d` with `/dayz-p3d-audit`
6. **Pack PBO** with `/dayz-build-pbo` and test in DayZ with `/dayz-launch-test`

See `py3d-direct-generation.md` for p3d assembly, and `config-and-packing.md` for the final DayZ config.

---

## Quick Checklist: Before Exporting

- [ ] Scale applied and verified (in meters)
- [ ] All normals recalculated (outside-facing)
- [ ] Doubles removed (threshold 0.0001)
- [ ] Interior faces deleted
- [ ] Moving parts separated and named
- [ ] UV islands packed with proper margins
- [ ] LODs generated and decimated
- [ ] Each LOD verified for geometry integrity
- [ ] Export settings: Forward=Y, Up=Z (no conversion; py3d applies Rule 12)
- [ ] Each LOD exported as separate OBJ
- [ ] Textures renamed per DayZ convention
- [ ] Ready for py3d assembly
