# Cloth, soft bodies and particles in bpy

How a script sets up cloth with pins, collisions and preset values, soft bodies, and particle debris in Blender, and reads deformed geometry per frame. Rigid bodies are in `blender-bpy-physics.md`; baking and export, including why FBX loses cloth, in `blender-bpy-sim-baking-export.md`.

This is Blender behaviour, run on Blender 5.1 with `blender --background` or taken from the API reference the Blender MCP server bundles and Blender's own preset files, so nothing here cites `P:\`.

## Adding cloth

```python
bpy.context.view_layer.objects.active = mesh_obj
bpy.ops.object.modifier_add(type='CLOTH')     # the default type is SUBSURF, so always pass it
```

It runs headless and names the modifier `"Cloth"`. `obj.modifiers.new("Cloth", 'CLOTH')` needs no active object; only the operator was run. The modifier has two separate parts: `settings` (`ClothSettings`, the fabric) and `collision_settings` (`ClothCollisionSettings`, how this cloth meets colliders and itself).

## Fabric settings

| `ClothSettings` field | Default | Meaning |
|---|---|---|
| `quality` | 5 | Solver steps per frame. |
| `mass` | 0.3 | Mass per vertex. |
| `air_damping` | 1.0 | Air drag on the sheet. |
| `tension_stiffness`, `compression_stiffness` (and `_max`) | 15.0 | Resist stretching and compression. |
| `shear_stiffness` (and `_max`) | 5.0 | Resists shearing. |
| `bending_stiffness` (and `_max`) | 0.5 | Resists folding. |
| `tension_damping`, `compression_damping`, `shear_damping`, `bending_damping` | 5.0, 5.0, 5.0, 0.5 | Damping per spring kind. |
| `bending_model` | `ANGULAR` | Or `LINEAR`, the older model. |
| `use_internal_springs` and `internal_*` | Off | Springs through the volume, joining opposite sides. |
| `use_pressure`, `uniform_pressure_force`, `target_volume`, `pressure_factor`, `use_pressure_volume`, `fluid_density` | Off | Pressure inside a closed mesh, like a balloon. |
| `shrink_min`, `shrink_max` | 0.0 | Shrink by a factor. |
| `use_sewing_springs`, `sewing_force_max` | Off | Pull loose edges together, for garment seams. |
| `vertex_group_mass` | `""` | The pin group. |
| `vertex_group_bending`, `_intern`, `_pressure`, `_shear_stiffness`, `_shrink`, `_structural_stiffness` | `""` | Vary those values across the mesh. |
| `goal_default`, `goal_min`, `goal_max`, `goal_spring`, `goal_friction` | 0, 0, 1, 1.0, 0 | Older goal pinning; the pin group does the job for most uses. |
| `rest_shape_key` | None | A shape key as the rest shape, for sewing patterns or pre-shaped garments. |
| `gravity` | `(0, 0, −9.81)` | Not read by the solver; see `blender-bpy-physics.md`, "Scale, origin and gravity". |
| `voxel_cell_size` | 0.1 | Voxel size for interaction effects. |
| `effector_weights` | | Response to force fields such as wind. |
| `time_scale` | 1.0 | Speed relative to scene time. |
| `use_dynamic_mesh` | Off | Follow base mesh changes from other modifiers. |

`ClothCollisionSettings` has `collection`, `collision_quality`, `damping`, `distance_min`, `friction`, `impulse_clamp`, `self_distance_min`, `self_friction`, `self_impulse_clamp`, `use_collision`, `use_self_collision`, `vertex_group_object_collisions` and `vertex_group_self_collisions`. `use_collision` and `use_self_collision` switch it on; `distance_min` and `self_distance_min` are the cloth's own gap, apart from the collider's `thickness_outer`; `collision_quality` is its own step count, apart from `settings.quality`.

## Pins and colliders

```python
vg = obj.vertex_groups.new(name="Pin")
vg.add([0, 1, 2, 3, 4], 1.0, 'REPLACE')     # a list of indices, one weight, REPLACE, ADD or SUBTRACT
obj.modifiers["Cloth"].settings.vertex_group_mass = vg.name
```

On a hanging plane over 20 frames, the pinned top row stayed at exactly Z 0.0 while the free bottom sagged to about −1.47.

The collider gets a Collision modifier, and its settings sit on the object, not a modifier part:

```python
bpy.context.view_layer.objects.active = floor
bpy.ops.object.modifier_add(type='COLLISION')
floor.collision.thickness_outer = 0.02
```

`floor.collision` has `absorption`, `cloth_friction`, `damping`, `damping_factor`, `damping_random`, `friction_factor`, `friction_random`, `permeability`, `stickiness`, `thickness_inner`, `thickness_outer`, `use`, `use_culling`, `use_normal` and `use_particle_kill`. `thickness_outer` and `thickness_inner` set the shell around the surface (inner matters for soft bodies passing through). `cloth_friction` is what cloth feels; `friction_factor` and `damping_factor` are for particles.

## Preset values

Blender's five cloth presets are Python files in the `scripts\presets\cloth` folder of the install:

| Preset | Quality | Mass | Tension, compression, shear stiffness | Bending stiffness | Tension, compression, shear damping | Air damping |
|---|---|---|---|---|---|---|
| Cotton | 5 | 0.3 | 15, 15, 15 | 0.5 | 5, 5, 5 | 1.0 |
| Denim | 12 | 1 | 40, 40, 40 | 10 | 25, 25, 25 | 1 |
| Leather | 15 | 0.4 | 80, 80, 80 | 150 | 25, 25, 25 | 1 |
| Rubber | 7 | 3 | 15, 15, 15 | 25 | 25, 25, 25 | 1 |
| Silk | 5 | 0.15 | 5, 5, 5 | 0.05 | 0, 0, 0 | 1 |

All five share the pressure values (`use_pressure=False`, `uniform_pressure_force=76.0`, `target_volume=0.0`, `pressure_factor=1.0`, `fluid_density=0.0`) and the internal spring values. Heavy fabrics pair high stiffness with high damping and more quality steps; silk has low stiffness and no damping; rubber resists folding far more than stretching, which gives a springy sheet.

The preset files set `bpy.context.cloth.settings.X`, so they need a `context.cloth` member, the same kind of context `ptcache.bake` needs. Do not run `bpy.ops.script.execute_preset(...)` from a script; set the numbers on `modifiers["Cloth"].settings` from the table:

```python
cs = cloth_plane.modifiers["Cloth"].settings
cs.quality = 5; cs.mass = 0.3
cs.tension_stiffness = cs.compression_stiffness = cs.shear_stiffness = 15
cs.bending_stiffness = 0.5
cs.tension_damping = cs.compression_damping = cs.shear_damping = 5
cs.air_damping = 1.0
cloth_plane.modifiers["Cloth"].collision_settings.use_collision = True
cloth_plane.modifiers["Cloth"].collision_settings.distance_min = 0.015
```

## Reading deformed geometry per frame

Evaluating the depsgraph runs the solver for that frame; no bake is needed:

```python
for f in range(1, 21):
    scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = cloth_plane.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()
    verts_world = [obj_eval.matrix_world @ v.co for v in mesh_eval.vertices]
    obj_eval.to_mesh_clear()       # frees the temporary mesh
```

## Soft bodies

```python
bpy.context.view_layer.objects.active = blob
bpy.ops.object.modifier_add(type='SOFT_BODY')
sb = blob.modifiers["Softbody"].settings     # "Softbody": one word, lower case b
sb.use_goal = True
sb.goal_spring = 0.5
sb.use_edges = True
sb.pull = 0.5; sb.push = 0.5; sb.damping = 5.0
```

`"Soft Body"` or `"SoftBody"` raises `KeyError`.

| Group | `SoftBodySettings` fields |
|---|---|
| Goal | `use_goal`, `goal_default`, `goal_min`, `goal_max`, `goal_spring`, `goal_friction`, `vertex_group_goal`. Each vertex is pulled toward its animated or rest position by a spring, so a goal body still jiggles. |
| Edge springs (need `use_edges`) | `pull`, `push`, `damping`, `bend`, `shear`, `plastic` (lasting deformation, 0 to 100), `spring_length` (percent change of rest length), `vertex_group_spring`. |
| Collision | `use_self_collision`, `use_edge_collision`, `use_face_collision`, `ball_size`, `ball_stiff`, `ball_damp`, `collision_type` (`MANUAL`, `AVERAGE`, `MINIMAL`, `MAXIMAL`, `MINMAX`, ways to size the balls from spring length), `fuzzy` (higher is faster, less stable), `collision_collection`. |
| Solver | `step_min`, `step_max`, `use_auto_step`, `error_threshold` (lower is more precise and slower), `use_diagnose`. |
| Air | `aero`, `aerodynamics_type` (`SIMPLE`, `LIFT_FORCE`), acting on edges. |
| Mass | `mass`, `friction`, `gravity` (a float, not read by the solver), `vertex_group_mass`, `speed`. |

The values after `modifier_add` differ from the reference defaults: `gravity` 9.8 (reference 0.0), `mass` 1.0 (0.0), `use_goal` and `use_edges` `True` (`False`). Read settings back after adding the modifier.

Use soft bodies for jelly, squishy props and rope like edge chains, where the whole volume should wobble. Use cloth for anything that reads as fabric: its model is built for thin sheets and its self collision is sturdier. The two were not benchmarked against each other.

## Particles

```python
bpy.context.view_layer.objects.active = emitter
bpy.ops.object.particle_system_add()           # runs headless with only the active object
settings = emitter.particle_systems[0].settings  # a reusable ParticleSettings in bpy.data.particles
settings.count = 200
settings.physics_type = 'NEWTON'
settings.render_type = 'COLLECTION'
settings.instance_collection = debris_collection
settings.use_rotation_instance = True
settings.factor_random = 2.0
```

| Field | Values |
|---|---|
| `type` | `EMITTER` (default), `HAIR`. |
| `physics_type` | `NO`, `NEWTON` (default; point masses with gravity, drag and fields), `KEYED`, `BOIDS`, `FLUID`. |
| `emit_from` | `VERT`, `FACE` (default), `VOLUME`. |
| `count`, `frame_start`, `frame_end` | How many, and the emission window, apart from each particle's `lifetime` and `lifetime_random`. |
| `integrator` | `EULER`, `VERLET`, `MIDPOINT` (default), `RK4`. Cheap Euler visibly drifts on fast debris. |
| `damping`, `effector_weights` | Drag and field response. |
| `factor_random`, `angular_velocity_mode`, `angular_velocity_factor`, `size_random`, `rotation_factor_random` | Random start speed, tumbling, size and rotation. |
| `render_type` | `NONE`, `HALO`, `LINE`, `PATH`, `OBJECT`, `COLLECTION`. |

With `COLLECTION`, `instance_collection` cycles through the collection's members; with `OBJECT`, `instance_object` uses one. `use_whole_collection`, `use_collection_pick_random` and `use_collection_count` choose how members are spread; `use_rotation_instance`, `use_scale_instance` and `use_global_instance` keep each object's own transform.

To move a new object into a collection, unlink it from every collection it is really in first; guessing wrong raises `RuntimeError: Object 'X' not in collection 'Scene Collection'`:

```python
for c in list(obj.users_collection):
    c.objects.unlink(obj)
debris_collection.objects.link(obj)
```

For debris in the foreground that must collide, tumble and settle, give each piece its own rigid body with a thrown start (`blender-bpy-physics.md`, "Throwing an object"). Newton particles get only simple point collision against collision objects, no full rotation response, and never collide with each other. Particles suit background debris: dust, sparks, distant leaves.
