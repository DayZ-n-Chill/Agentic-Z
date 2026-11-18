# Baking and exporting simulations in bpy

How a script bakes a Blender simulation's point cache, turns it into keys, reads the keys back on any version, and exports the result, and which formats keep cloth deformation. Rigid bodies are in `blender-bpy-physics.md`; cloth, soft bodies and particles in `blender-bpy-cloth-and-particles.md`.

This is Blender behaviour, run on Blender 5.1 with `blender --background` or taken from the API reference the Blender MCP server bundles, so nothing here cites `P:\`.

## The point cache

`scene.rigidbody_world.point_cache` is a `PointCache` with `frame_start` and `frame_end` (default 1 and 250), `frame_step`, `is_baked`, `is_baking`, `is_frame_skip`, `is_outdated`, `use_disk_cache` and `filepath`. Rigid body worlds, cloth and soft body modifiers, particle systems and dynamic paint surfaces all use the same type, so what follows applies to `modifier.point_cache` and `psys.point_cache` too.

## Baking the cache

Called plainly, `bpy.ops.ptcache.bake(bake=True)` fails with `RuntimeError: Operator bpy.ops.ptcache.bake.poll() failed, context is incorrect`. Supply the cache through `temp_override`; nothing else is needed:

```python
rbw = bpy.context.scene.rigidbody_world
with bpy.context.temp_override(point_cache=rbw.point_cache):
    bpy.ops.ptcache.bake(bake=True)    # rbw.point_cache.is_baked is now True
```

`bake_all(bake=True)`, `bake_from_cache()`, `free_bake()`, `free_bake_all()`, `add()` and `remove()` need the same override (only `bake` was run). The same pattern on a particle system's cache was not run.

Stepping the frames yourself (`scene.frame_set(f)` over the range) also runs the simulation and fills the cache; a cube dropped from Z 5.0 settled at about 1.0 on a floor at 0. But only an explicit bake or loading an external cache sets the baked flag (read in Blender 5.1 source, `pointcache.cc`), so `is_baked` stays `False` and a later pass can simulate again. Stepping is fine for a look. Before sampling frames for keys, bake: two passes over an unbaked simulation drifted 3.56 m apart in one run.

The cache can go stale. Adding a rigid body to the world's collection after the cache was stepped or baked, then stepping again from frame 1, sent an object that should rest on a floor through it to about −6.6; the same setup alone in a fresh Blender process rested correctly every time. The cache is one per world, shared by the whole collection. Free it (`ptcache.free_bake_all()` under the same override) or rebuild the world whenever the set of bodies changes, and do not stack unrelated experiments in one scene.

## Turning the simulation into keys

`bpy.ops.rigidbody.bake_to_keyframes(frame_start=1, frame_end=250, step=1)` (defined in Blender's startup scripts at `bl_operators\rigidbody.py:108`) fails headless even with selection and active object set:

```text
RuntimeError: Operator bpy.ops.anim.keyframe_insert_by_name.poll() failed, context is incorrect
```

It is a Python operator that calls `bpy.ops.anim.keyframe_insert_by_name(type='BUILTIN_KSI_LocRot')` inside itself (`bl_operators\rigidbody.py:165`), and context overrides on the outer operator do not reach inner `bpy.ops` calls. No override fixed it, including a real `window`, `screen`, `VIEW_3D` area and region (headless, `bpy.context.window` and `screen` exist; only `area` is `None`). Blender tracks this as bugs `T63067` and `T97382`. Whether it works inside a live GUI session through MCP is not tested, so build on one of these instead:

```python
from bpy_extras import anim_utils
action = anim_utils.bake_action(
    cube, action=None, frames=range(1, 61),
    bake_options=anim_utils.BakeOptions(
        only_selected=False, do_pose=False, do_object=True, do_visual_keying=True,
        do_constraint_clear=False, do_parents_clear=False, do_clean=False,
        do_location=True, do_rotation=True, do_scale=False, do_bbone=False, do_custom_props=False,
    ),
)
```

```python
for f in range(1, 61):
    scene.frame_set(f)
    cube.keyframe_insert(data_path="location", frame=f)
    cube.keyframe_insert(data_path="rotation_euler", frame=f)
```

Both run headless with no override. `bake_action` creates and assigns an Action with curves on `location` and `rotation_euler` only, the output `bake_to_keyframes` should give; a quaternion object would get `rotation_quaternion` (not run). `BakeOptions` has 12 fields and no defaults.

## Reading baked keys back

On 5.0 and later `action.fcurves` raises `AttributeError`; 4.4 kept it as a legacy accessor on the first slot, and 4.3 had only that. Since 5.0 `action.id_root` is `action_slot.target_id_type`. A reader that works on both sides:

```python
def get_fcurves(obj):
    ad = obj.animation_data
    if ad is None or ad.action is None:
        return []
    action = ad.action
    if hasattr(action, "fcurves"):            # 4.x
        return list(action.fcurves)
    from bpy_extras import anim_utils          # 5.0 and later
    slot = ad.action_slot
    cb = anim_utils.action_get_channelbag_for_slot(action, slot) if slot else None
    return list(cb.fcurves) if cb else []
```

`anim_utils.action_ensure_channelbag_for_slot(action, slot)` gets or creates one. The layer and strip walk is in `blender-bpy-fcurves.md`.

## FBX does not carry cloth

In `bpy.ops.export_scene.fbx(...)` (defined in `addons_core/io_scene_fbx/__init__.py:604`):

- `use_mesh_modifiers=True` (default) applies the modifier stack, cloth and soft body included, at the current frame only: one still shape. Its docstring warns "WARNING: prevents exporting shape keys".
- `bake_anim`, `bake_anim_use_all_bones`, `bake_anim_use_nla_strips`, `bake_anim_use_all_actions`, `bake_anim_force_startend_keying`, `bake_anim_step` and `bake_anim_simplify_factor` bake armature and Action or NLA animation, never vertex deformation.

So FBX carries object transform keys (fine for rigid body debris) and bone and shape key animation, but not cloth or soft body deformation. Blender has no built in conversion. One shape key per frame would do it but is heavy and not how it is done; this sketch was not run to completion:

```python
for f in range(frame_start, frame_end + 1):
    scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()
    sk = obj.shape_key_add(name=f"frame_{f}", from_mix=False)
    for i, v in enumerate(mesh_eval.vertices):
        sk.data[i].co = v.co
    obj_eval.to_mesh_clear()
    # then key sk.value 0, 1, 0 around frame f
```

## Alembic carries it

```python
bpy.ops.object.select_all(action='DESELECT')
cloth_plane.select_set(True)
bpy.ops.wm.alembic_export(filepath="//cloth_cache.abc", start=1, end=60, selected=True)
```

On a cloth plane whose vertices changed every frame, this wrote a real `.abc` with Alembic's `Ogawa` header. The exporter steps through `start` to `end` itself, whatever frame the scene is on.

`bpy.ops.wm.alembic_export` is missing from the MCP server's bundled reference (`get_python_api_docs` and `search_api_docs` find nothing, and the `bpy.ops.wm` listing leaves it out), yet it works. `hasattr` on `bpy.ops` proves nothing either. Treat the bundled reference as a hint and call the operator on the live process before deciding it is gone.

Its options, read from the operator's own RNA (`bpy.ops.wm.alembic_export.get_rna_type().properties`): `filepath`, `start`, `end`, `selected`, `global_scale`, `flatten`, `uvs`, `vcolors`, `normals`, `face_sets`, `subdiv_schema`, `apply_subdiv`, `curves_as_mesh`, `export_hair`, `export_particles`, `export_custom_properties`, `use_instancing`, `triangulate`, `quad_method`, `ngon_method`, `packuv`, `orcos`, `xsamples` (transform samples per frame), `gsamples` (geometry samples per frame), `sh_open` and `sh_close` (shutter), `sort_method`, `init_scene_frame_range`, `evaluation_mode`, `as_background_job`, `collection`, `display_type`, `check_existing` and `filemode`. `visible_objects_only` was removed from Alembic and USD export in 5.0.

Since 4.2, collections can also carry exporters:

```python
exporter = collection.exporters.new('IO_FH_alembic', name="AlembicExporter")
bpy.ops.wm.collection_export_all()
```

For a one off script, call `wm.alembic_export` directly; collection exporters suit an artist's export on every save.

## MDD and PC2

There is no MDD or PC2 exporter in Blender 5.1: `bpy.ops.export_shape` does not exist and `bpy.ops.export_anim` has only `bvh`. The old Lightwave point cache add-on is gone; a pipeline that needs those formats needs a third party add-on. Check the install before promising it.
