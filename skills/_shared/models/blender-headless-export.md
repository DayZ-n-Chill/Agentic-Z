# Exporting from Blender for py3d

How to export OBJ files from a windowless Blender script for py3d to assemble, how to make the LOD set, the mistakes that lose data on the way, and a script template. Starting Blender, primitives, modifiers, UVs and the AO bake are in `blender-headless.md`. This is Blender API knowledge measured in Blender 5.1, not vanilla game data.

## Export

DayZ is Y up and Blender Z up, and the two differ in handedness as well. Export the OBJ in Blender's own coordinates and convert once, in py3d, with the Blender to DayZ map (`generated-model-rules.md`, "The Blender to DayZ map"; `axes-and-winding.md`).

With one vertex at `(1, 2, 3)`, `bpy.ops.wm.obj_export` writes:

| `forward_axis`, `up_axis` | Written | After the map in py3d |
|---|---|---|
| `'Y'`, `'Z'` | `(1, 2, 3)` | Correct |
| `'NEGATIVE_Z'`, `'Y'` (the default) | `(1, 3, -2)`, the rotation `(x, z, -y)` | Lies on its back |
| `'NEGATIVE_Y'`, `'Z'` | `(-1, -2, 3)`, a half turn | Faces backwards |

Use `'Y'` and `'Z'`. The enum for minus Y is `'NEGATIVE_Y'`; `'-Y'` is rejected.

```python
def export_obj(obj, filepath):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.wm.obj_export(
        filepath=filepath,
        check_existing=False,
        export_selected_objects=True,   # this object only
        forward_axis='Y',               # with up Z: no axis conversion
        up_axis='Z',
        global_scale=1.0,
        apply_modifiers=True,
        export_uv=True,
        export_normals=True,
        export_materials=True,
    )
```

`bpy.ops.export_scene.obj()` is gone; use `bpy.ops.wm.obj_export()`. Before each export, unhide the object (`hide_viewport=False`, `hide_set(False)`): a hidden object is skipped while the call still returns `{'FINISHED'}`, so check that every file exists afterwards (`blender-import-preflight.md`).

## LODs

The usual visual set is LOD0 at 100%, LOD1 at 50%, LOD2 at 25% and LOD3 at 12%. These are visual LODs, so get the user's approval for the ratios before running the loop (`generated-model-pipeline.md`). Duplicate the source for each level, apply its modifiers, decimate, then export:

```python
import os

def generate_lods(source_objs, output_dir, lod_ratios=(1.0, 0.5, 0.25, 0.12)):
    os.makedirs(output_dir, exist_ok=True)
    for i, ratio in enumerate(lod_ratios):
        parts = []
        for source in source_objs:
            bpy.ops.object.select_all(action='DESELECT')
            source.select_set(True)
            bpy.context.view_layer.objects.active = source
            bpy.ops.object.duplicate()
            lod_obj = bpy.context.active_object
            lod_obj.name = f"{source.name}_LOD{i}"
            for mod in list(lod_obj.modifiers):
                bpy.ops.object.modifier_apply(modifier=mod.name)
            if ratio < 1.0:
                decim = lod_obj.modifiers.new(name='Decimate', type='DECIMATE')
                decim.ratio = ratio
                bpy.ops.object.modifier_apply(modifier='Decimate')
            parts.append(lod_obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in parts:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()                       # one object per LOD
        combined = bpy.context.active_object
        combined.name = f"LOD{i}"
        export_obj(combined, os.path.join(output_dir, f"LOD{i}.obj"))
```

## Mistakes that lose data

| Mistake | What happens | Fix |
|---|---|---|
| Modifiers not applied | They show in Blender and are missing from the OBJ | Apply every modifier first, or export with `apply_modifiers=True` |
| Object not active and selected | `modifier_apply.poll()` fails with a `RuntimeError` | Set `view_layer.objects.active` and `select_set(True)` before operators |
| Scale not applied | The model comes out the wrong size | `transform_apply(scale=True)` before export |
| Normals inside out in Blender | Dark or odd shading | In Edit Mode, `normals_make_consistent(inside=False)`; the DayZ map negates them later |
| Trusting the exit code | A script that crashed still exits 0 | Scan the output for `Traceback` and require the script's own end summary (`blender-headless.md`) |

Also: name objects plainly (`LOD0`, `LOD1`) so later steps can find them, save the `.blend` before a batch export so failures can be inspected, and judge LODs by vertex count, which is what the DayZ budget counts.

## Script template

```python
import bpy

bpy.ops.object.select_all(action='DESELECT')
for obj in list(bpy.data.objects):
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.scene.unit_settings.system = 'METRIC'

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.5))
obj = bpy.context.active_object
obj.name = "MyMod_Box"
obj.scale = (0.4, 0.25, 0.5)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

bevel = obj.modifiers.new(name='Bevel', type='BEVEL')
bevel.width = 0.02
bpy.ops.object.modifier_apply(modifier='Bevel')

mesh = obj.data
if not mesh.uv_layers:
    mesh.uv_layers.new(name='UVMap')
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.5708, island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.wm.obj_export(
    filepath="out/model.obj",
    forward_axis='Y',      # Blender's own coordinates; py3d applies the map
    up_axis='Z',
    apply_modifiers=True,
    export_uv=True,
    export_normals=True,
)
print("MyMod_Box exported")   # the end summary the caller checks for
```

Run it with `blender --background --python generate_box.py`.
