# Preparing an outside mesh in Blender

How to take a mesh made somewhere else (an asset store, 3ds Max, Maya, ZBrush, a commissioned or legacy model) through Blender to OBJ files that py3d assembles into a `.p3d`: import, cleanup, UVs, LODs, export and textures. Generated models and models built in Blender for DayZ take the routes in `generated-model-pipeline.md` instead. This is Blender tool knowledge, measured in Blender 5.1, not vanilla game data.

Before importing an FBX, read `blender-import-preflight.md`: custom split normals can crash the importer, and hidden objects are skipped on export without a word.

## Formats

| Format | Good | Watch for |
|---|---|---|
| FBX (`.fbx`) | Best material and skeleton support | Big files, leftover junk |
| OBJ (`.obj`) | Simple and clean | No materials or animation in the file |
| glTF (`.glb`, `.gltf`) | Compact, modern | Blender support varies by version |
| STL (`.stl`) | CAD exports | Geometry only, no UVs or materials |
| Blender (`.blend`) | Opens directly | |

## Before you import

Write down what you have, because it sets the cleanup: the units (metres, centimetres, unknown), the polygon count (aim under 2,000 for a small object), whether UVs exist, whether textures are inside the file, separate or missing, whether an animated model has a rigged skeleton, and whether the source app was Z up or Y up.

```python
import bpy
bpy.ops.object.select_all(action='SELECT')        # clear the scene first
bpy.ops.object.delete()
bpy.ops.import_scene.fbx(filepath='/path/to/model.fbx')
# bpy.ops.wm.obj_import(filepath='/path/to/model.obj')
# bpy.ops.import_scene.gltf(filepath='/path/to/model.glb')
# bpy.ops.wm.open_mainfile(filepath='/path/to/existing.blend')
```

## Cleanup

Do these in order.

1. **Scale to metres** and apply it: centimetres times 0.01, millimetres times 0.001, feet times 0.3048.

   ```python
   obj = bpy.context.active_object
   obj.scale = (0.01, 0.01, 0.01)                # a model in centimetres
   bpy.ops.object.transform_apply(scale=True)
   ```

2. **Delete what is not geometry**: cameras and lights. Keep meshes, and the armature if it animates.

   ```python
   for obj in list(bpy.data.objects):
       if obj.type in {'CAMERA', 'LIGHT'}:
           bpy.data.objects.remove(obj, do_unlink=True)
   ```

3. **Join meshes** that should be one object: select the meshes, make one active, `bpy.ops.object.join()`.
4. **Normals outward in Blender**: in Edit Mode, select all and `bpy.ops.mesh.normals_make_consistent(inside=False)`. The DayZ map negates them later (`axes-and-winding.md`).
5. **Merge doubles**: in Edit Mode, `bpy.ops.mesh.remove_doubles(threshold=0.0001)`.
6. **Count polygons**: `len(obj.data.polygons)`. Aim under 2,000 for a small object and under 5,000 for a medium one; larger props need good LODs.

## Making it game ready

**Decimate only with approval.** Decimating anything the player sees is the user's call: say what you plan to reduce and by how much, and wait (`generated-model-pipeline.md`, "Before any work"). Collision and view LODs can be reduced without asking.

```python
decimate = obj.modifiers.new(name='Decimate', type='DECIMATE')
decimate.ratio = 0.5
bpy.ops.object.modifier_apply(modifier='Decimate')
```

**Delete interior faces** the player never sees: in Edit Mode, face select (`3`), select them, `X`, Delete Faces.

**Separate moving parts** (doors, switches) into their own objects: select the part's faces in Edit Mode, then `bpy.ops.mesh.separate(type='SELECTED')`.

**Name objects for their selections.** Each object name becomes a named selection later, so name them for what they are: `body`, `cover`, `light_lens`.

## UVs

An existing unwrap needs no overlapping islands (they ruin bakes), margins between islands (or textures bleed), and each material zone in its own island. With no UVs, run Smart UV Project, then pack:

```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=0.02)
bpy.ops.uv.pack_islands(margin=0.01)
bpy.ops.object.mode_set(mode='OBJECT')
```

For a DayZ visual asset someone will paint, unwrap by logical sections instead (`tools-uv-atlas.md`).

## LODs

Make 2 to 4 visual LODs: LOD0 at full count, LOD1 about 50%, LOD2 about 25%, LOD3 about 12% for large objects. Each one is a visual decimation, so each needs the user's approval. Duplicate the original each time, never the previous LOD:

```python
original = bpy.context.active_object
for lod_level, ratio in [(1, 0.5), (2, 0.25), (3, 0.12)]:
    bpy.ops.object.select_all(action='DESELECT')
    original.select_set(True)
    bpy.context.view_layer.objects.active = original
    bpy.ops.object.duplicate()
    lod_obj = bpy.context.active_object
    lod_obj.name = f'{original.name}_lod{lod_level}'
    decimate = lod_obj.modifiers.new(name='Decimate', type='DECIMATE')
    decimate.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='Decimate')
```

Check the UVs after each decimation and pack again if they broke.

## Export for py3d

Export each LOD as its own OBJ in Blender's own axes, with forward Y and up Z, scale 1.0, modifiers applied and smooth groups on. py3d then applies the Blender to DayZ map once (`generated-model-rules.md`, "The Blender to DayZ map"; `axes-and-winding.md`).

```python
bpy.ops.wm.obj_export(
    filepath='out/model_lod0.obj',
    export_selected_objects=True,
    forward_axis='Y',
    up_axis='Z',
    apply_modifiers=True
)
```

| App | Up | Forward |
|---|---|---|
| Blender | Z | -Y |
| DayZ | Y | -Z |

Forward Y and up Z is no conversion at all: the OBJ keeps raw Blender coordinates. With one vertex at `(1, 2, 3)`, forward Y writes `(1, 2, 3)`; forward -Y writes `(-1, -2, 3)`, a half turn, so the model faces backwards after the map; the default forward -Z, up Y writes `(1, 3, -2)`, the rotation `(x, z, -y)`, so the model lies on its back after the map, and on its own it ships mirrored. The exporter's forward setting names the file axis Blender's +Y becomes, not where the model faces: a character facing -Y in Blender still exports with forward Y. In Python the enum for minus Y is `'NEGATIVE_Y'`; `'-Y'` is rejected.

## Textures

If the model came with textures, rename them to the DayZ suffixes: colour to `_co`, normal to `_nohq`, specular and gloss to `_smdi` (`_shared/textures/suffixes-and-sizes.md`). Bake to images in Blender if needed, repack channels in Substance Painter or a similar tool, save them under the mod's `data\` folder, and convert each `.png` with `/dayz-pack-texture`. DayZ `_nohq` maps are green down (DirectX) and Blender bakes green up, so invert green on a Blender bake; this is tool knowledge, not stated by a file on `P:\`. With no textures, generate them (`_shared/textures/procedural-textures.md`).

## Common problems

| Problem | Cause | Fix |
|---|---|---|
| Tiny or huge | Wrong units | Scale to metres and apply |
| Inside out or black in Blender | Normals flipped | `normals_make_consistent(inside=False)` |
| Black faces or holes | Doubled vertices | Merge doubles at 0.0001 |
| UV seams show in game | Margins too tight | Pack again with 0.02 or more |
| Faces the wrong way | Export axes converted, or the model faces another way in Blender | Export again with forward Y, up Z. If it still faces wrong, turn the model in Blender so its front looks down -Y; never fix facing through the export axes |
| Stretched textures | Bad unwrap | Smart UV Project, or lay it out by hand |
| Distorted LODs | Decimate broke the shape | Try a Voxel Remesh modifier instead |
| Jagged smooth shading | Auto smooth angle too low | Raise it to 60 to 80 degrees |

## Before you export

- Scale applied, in metres; normals outward; doubles merged; interior faces gone.
- Moving parts separated and named; UV islands packed with margins.
- LODs made with approval and checked; each exported as its own OBJ with forward Y and up Z.
- Textures renamed to DayZ suffixes.

Then assemble with py3d (`py3d-generation.md`), add selections and the `model.cfg`, audit with `/dayz-p3d-audit`, and pack and test with `/dayz-build-pbo` and `/dayz-launch-test`. The config side is in `model-config-and-packing.md`.
