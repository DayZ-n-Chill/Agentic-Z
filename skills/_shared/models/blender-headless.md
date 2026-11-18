# Running Blender without its window

How to drive Blender from a script with no window: starting it, clearing the scene, primitives, modifiers, UVs, materials and the ambient occlusion bake. The OBJ export that py3d assembles, LODs, common mistakes and a script template are in `blender-headless-export.md`. This is Blender API knowledge, not vanilla game data. The calls work from Blender 3.2; behaviour measured in a later version names it. Example paths are relative (`out/...`); write real output under `workspace/<ModName>/`.

## Starting Blender

```bash
blender --background --python script.py
blender --background --python script.py -- arg1 arg2
```

`--background` runs with no window, `--python` runs the script after start-up, and everything after `--` goes to the script (`sys.argv[sys.argv.index('--') + 1:]`).

Blender exits with code 0 even when the script raised an uncaught exception (measured in Blender 5.2): an `AttributeError` mid-script still ends with "Blender quit". Never treat the return code as a pass. Scan stdout and stderr for `Traceback (most recent call last)`, and have the script print an expected summary at the end as proof it got there.

Start every script from a clean, metric scene:

```python
import bpy
bpy.ops.object.select_all(action='DESELECT')
for obj in list(bpy.data.objects):
    if obj.type in ('MESH', 'CAMERA', 'LIGHT', 'EMPTY'):
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.outliner.orphans_purge()

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0      # 1 Blender unit is 1 metre
scene.unit_settings.length_unit = 'METERS'
```

## Primitives

| Shape | Call | Key arguments |
|---|---|---|
| Cube | `bpy.ops.mesh.primitive_cube_add` | `size`, `location`, `scale`. Use `size=2` so scale is the half extent (`blender-assembly.md`) |
| Cylinder | `bpy.ops.mesh.primitive_cylinder_add` | `vertices` (sides), `radius`, `depth` (height on Z), `location` |
| UV sphere | `bpy.ops.mesh.primitive_uv_sphere_add` | `radius`, `segments` (meridians), `ring_count` (parallels) |
| Cone | `bpy.ops.mesh.primitive_cone_add` | `vertices`, `radius1` (base), `radius2` (tip, 0 for a point), `depth` |
| Torus | `bpy.ops.mesh.primitive_torus_add` | The operator; there is no `bmesh.ops.create_torus` |

After each call, `bpy.context.active_object` is the new object; name it straight away.

Watch for bpy calls that look right and do not exist. In Blender 5.2, `bmesh.ops` offers only `create_circle`, `create_cone`, `create_cube`, `create_grid`, `create_icosphere`, `create_monkey`, `create_uvsphere` and `create_vert`. The bevel modifier's size field is `.width`, not `.offset`. A ring built from vertices with `from_pydata` avoids the torus question entirely.

For shapes no primitive gives, build the mesh from vertices and faces:

```python
vertices = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0.5, 0.5, 1)]
faces = [(0, 1, 2, 3), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
mesh = bpy.data.meshes.new("MyMod_Pyramid")
mesh.from_pydata(vertices, [], faces)
mesh.update()
obj = bpy.data.objects.new("MyMod_Pyramid", mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
```

## Modifiers

Add with `obj.modifiers.new(name=..., type=...)`. Order matters: subdivision before bevel gives the best result.

| Modifier | Settings |
|---|---|
| `BEVEL` | `width` (distance), `segments`, `limit_method` `'ANGLE'` with `angle_limit` in radians (`0.5236` is 30 degrees), or `'WEIGHT'` |
| `SUBSURF` | `levels` is what `modifier_apply` and the default OBJ export use; `render_levels` is used only by renders, or by `wm.obj_export` with `export_eval_mode='DAG_EVAL_RENDER'`; `type` `'CATMULL_CLARK'` |
| `BOOLEAN` | `operation` `'DIFFERENCE'`, `'UNION'` or `'INTERSECT'`; `object` is the cutter. Set `cutter.hide_render = True`. The safe protocol is in `blender-assembly.md` |
| `DECIMATE` | `ratio` from 0 to 1. Ask the user before decimating anything the player sees (`generated-model-pipeline.md`); on curved surfaces use COLLAPSE with an inverted vertex group (`blender-import-preflight.md`) |
| `SOLIDIFY` | `thickness`, `offset` (0 both sides, 1 outward only), `use_even_offset` |

Apply them before export, with the object active and selected:

```python
with bpy.context.temp_override(object=obj):     # Blender 3.2 or later
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
```

Without `temp_override`, make the object active and selected first (`bpy.context.view_layer.objects.active = obj`, `obj.select_set(True)`); otherwise `modifier_apply.poll()` fails with a `RuntimeError`.

## UVs

Smart UV Project runs in Edit Mode on a mesh with a UV layer:

```python
def setup_uvs(obj):
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='UVMap')
    mesh.uv_layers.active = mesh.uv_layers[0]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.5708, island_margin=0.02)   # about 90 degrees
    bpy.ops.object.mode_set(mode='OBJECT')
```

For a DayZ visual asset someone will paint, unwrap by logical sections instead (`tools-uv-atlas.md`).

## Materials

```python
mat = bpy.data.materials.new(name='MyMod_Steel')
mat.use_nodes = True                     # marked for removal in Blender 6.0
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.3, 0.3, 0.3, 1.0)
bsdf.inputs['Metallic'].default_value = 0.8
bsdf.inputs['Roughness'].default_value = 0.4
obj.data.materials.append(mat)
```

The emission input is `Emission Color` from Blender 4.0 and `Emission` before it; `bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')` works in both, with `Emission Strength` for the intensity. To paint some faces only, append the material and set `mesh.polygons[i].material_index` on those faces. A vertex colour layer is `mesh.color_attributes.new(name="AO", type='FLOAT_COLOR', domain='POINT')`.

## Baking ambient occlusion

Cycles bakes into the active image node of the object's material:

```python
def bake_ao(obj, output_path, resolution=1024):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64                        # more is cleaner
    img = bpy.data.images.new("AO_Bake", width=resolution, height=resolution, alpha=False)
    mat = bpy.data.materials.new(name="AO_Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    img_node = nodes.new(type='ShaderNodeTexImage')
    img_node.image = img
    nodes.active = img_node                          # the bake writes here
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], nodes.new(type='ShaderNodeOutputMaterial').inputs[0])
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name='UVMap')
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.bake(type='AO', margin=4, use_clear=True)
    img.filepath_raw = output_path
    img.file_format = 'PNG'
    img.save()
    return img
```

The AO image is multiplied into the `_co` (`_shared/textures/procedural-recipes.md`, "Baked AO in the color map"). The high to low normal bake is in `blender-assembly.md`, "Fine detail goes to the bake".
