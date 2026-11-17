# Physics simulations as animation in Blender (bpy)

Rigid bodies, cloth, soft bodies and particles authored and baked from `bpy` code with no UI, the export of the result (keyframes, FBX, Alembic), and the cache, context and scale pitfalls.

**Scope**: programmatic (bpy-only, no UI) authoring of physics-driven animation for the
`blender-animation` skill, executed through the Blender MCP server (`execute_blender_code`) into
a live Blender instance. No UI interaction is assumed available.

Everything here is Blender behaviour, checked against Blender 5.1.1 and the Blender Python API
reference as marked. None of it is a fact about the DayZ game, so nothing in this file cites
`P:\`; the DayZ side of the work is in `dayz-handoff.md`.

**How the facts were checked**: against a working **Blender 5.1.1** (hash `b70da489d7f4`, built
2026-04-14). No Blender 4.3 executable was available, so nothing was run on 4.3. Each claim
carries one of two marks:

1. **Run live** ("empirically verified", "live-confirmed"): real `bpy` code run with
   `blender.exe --background --python <script>.py` against Blender 5.1.1. This is stronger than
   reading the API reference, most of all for the baking operators, which depend on context.
2. **API reference** ("bundled"): the Blender Python API reference that the Blender MCP server
   bundles (RST files, read with its `get_python_api_docs` and `search_api_docs` tools). Its
   enums and properties matched the running 5.1.1 wherever both were compared. Version
   boundaries come from Blender's release notes.

**Versions**: everything marked "empirically verified" was run on **5.1.1**, not 4.3. Where a
4.3-vs-5.x difference matters, the text says how it is known (release notes, or the absence or
presence of a property or operator). Where a 4.3 behaviour could not be compared, the text says so.

Blender's installed files were read directly where relevant (for example the five built-in cloth
presets, in the `scripts\presets\cloth` folder of the Blender 5.1 install).

The pure headless (`--background`) results below hold in the live MCP session too, with two
additions from later live work that `SKILL.md` records as hard rule 7: construct `BakeOptions`
in full (it is a dataclass of 12 fields with no defaults), and bake the point cache before you
sample frames to insert keys, because each pass over an unbaked simulation simulates again and
can diverge (3.56 m of drift between two passes was measured in a real run).

---

## Rigid body

### Adding objects to the rigid body world

There is **no data-API constructor** for a rigid body — `bpy.types.RigidBodyObject()` raises
`TypeError: bpy_struct.__new__(struct): expected a single argument` (empirically confirmed). The
only way to attach rigid-body physics to an object is the operator:

```python
bpy.ops.rigidbody.object_add(type='ACTIVE')   # or type='PASSIVE'
```

Signature: `bpy.ops.rigidbody.object_add(*, type='ACTIVE')` (bundled `api/bpy.ops.rigidbody.rst`, identical to live 5.1.1 introspection).

**Empirically verified: this works from a pure headless script with zero context override** —
it only needs `bpy.context.view_layer.objects.active` set to the target object (selection is not
even required for the single-object form). Tested directly in `--background` mode:

```
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 5))
cube = bpy.context.active_object
bpy.context.view_layer.objects.active = cube
bpy.ops.rigidbody.object_add(type='ACTIVE')     # -> {'FINISHED'}, no override needed
```

If `scene.rigidbody_world` does not exist yet, `object_add` **auto-creates it** (confirmed:
`scene.rigidbody_world is None` before the call, a populated `RigidBodyWorld` with a fresh
`Collection` named `"RigidBodyWorld"` after). This matches the plural form too:
`bpy.ops.rigidbody.objects_add(type='ACTIVE')` adds all *selected* objects at once.

Full `bpy.ops.rigidbody` operator set (bundled doc + live-confirmed identical to the connected
5.1.1; source lines cite `rigidbody.py` in the `bl_operators` folder of Blender's startup scripts):

| Operator | Signature | Notes |
|---|---|---|
| `object_add` | `(type='ACTIVE')` | active object only |
| `objects_add` | `(type='ACTIVE')` | all selected |
| `object_remove` / `objects_remove` | `()` | |
| `object_settings_copy` | `()` | copies active object's RB settings to other selected |
| `world_add` / `world_remove` | `()` | manual world management (usually auto-handled) |
| `constraint_add` | `(type='FIXED')` | adds a `RigidBodyConstraint` to the **active object** (normally an Empty) |
| `constraint_remove` | `()` | |
| `connect` | `(con_type='FIXED', pivot_type='CENTER', connection_pattern='SELECTED_TO_ACTIVE')` | bulk-generates constraint objects between selected rigid bodies (`SELECTED_TO_ACTIVE` or `CHAIN_DISTANCE`) — this is the fast path for e.g. procedural chains or shatter-glue, avoids hand-adding N empties |
| `shape_change` | `(type='MESH')` | bulk collision-shape change for selected objects |
| `mass_calculate` | `(material='DEFAULT', density=1.0)` | see gotcha below — `'DEFAULT'` is **not** a real enum value |
| `bake_to_keyframes` | `(frame_start=1, frame_end=250, step=1)` | see **Caching & baking** — fails headlessly |

### Active vs. passive, collision shapes, physical properties

`RigidBodyObject` (`obj.rigid_body`) properties — enumerated **live** from the running 5.1.1's
`bl_rna` (`bpy.types.RigidBodyObject.bl_rna.properties`), which is the actual ground truth the
Python API exposes, not a doc paraphrase:

```
angular_damping, collision_collections, collision_margin, collision_shape,
deactivate_angular_velocity, deactivate_linear_velocity, enabled, friction,
kinematic, linear_damping, mass, mesh_source, restitution, type,
use_deactivation, use_deform, use_margin, use_start_deactivated
```

- `type` enum (live-confirmed): `ACTIVE`, `PASSIVE`.
- `collision_shape` enum (live-confirmed, exact order): `BOX`, `SPHERE`, `CAPSULE`, `CYLINDER`,
  `CONE`, `CONVEX_HULL`, `MESH`, `COMPOUND`.
- `mesh_source` enum (only meaningful for `MESH`/`CONVEX_HULL` shapes; live-confirmed):
  `BASE`, `DEFORM`, `FINAL`. This controls whether the collision geometry tracks
  modifier-deformed geometry every frame (`DEFORM`/`FINAL`, more expensive) or stays static
  from the base mesh (`BASE`) — relevant if the rigid body object also carries a Cloth,
  Armature, or other deforming modifier.
- `restitution` is Blender's name for **bounciness** (0 = no bounce, 1 = perfectly elastic).
- `friction`, `mass`, `linear_damping`/`angular_damping`, `collision_margin` (+ `use_margin`)
  are all direct floats on `rigid_body`, no operator needed to set them once added.
- **No settable velocity property exists** — there is no `linear_velocity` / `angular_velocity`
  field on `RigidBodyObject` (empirically confirmed by enumerating all properties and checking
  for any of `linear_velocity`/`angular_velocity`/`velocity` — none present). So the *only* way to give a rigid body an initial velocity from script is the
  kinematic-keyframe handoff (see **Hybrid keyframe+physics** below) — there is no "just set the
  velocity" shortcut.

### `RigidBodyWorld` (the scene's simulation container)

`scene.rigidbody_world` properties, live-confirmed on 5.1.1 (and identical to the bundled doc):
`collection`, `constraints`, `effector_weights`, `enabled`, `point_cache`, `solver_iterations`
(int, default 10), `substeps_per_frame` (int, default 10), `time_scale` (float, default 1.0),
`use_split_impulse` (bool, default False).

**Version gotcha (important):** older Blender docs and tutorials refer to `rigidbody_world.steps_per_second`.
That property **does not exist** in 5.1.1: `getattr(rbw, 'steps_per_second', ...)`
raises `AttributeError`. It has been renamed **`substeps_per_frame`** ("Number of simulation steps
taken per frame"). The version in which the rename landed is not determined (the API reference
and the live 5.1.1 both have `substeps_per_frame`; no 4.3 executable was available to compare).
For version-safe code, don't hard-code either name:

```python
def get_substeps(rbw):
    for name in ('substeps_per_frame', 'steps_per_second'):
        if hasattr(rbw, name):
            return getattr(rbw, name)
    return 10
```

`collection` is the `Collection` holding every simulated object; `constraints` is a **separate**
`Collection` holding constraint Empties (it is `None` until the first constraint is added — live-confirmed).
`point_cache` is never `None` (`PointCache` datablock, covered in **Caching & baking**).

### Constraints (hinge, fixed, spring, ...)

A rigid body constraint is **not** a property of a physics object — it's a separate Empty object
carrying a `RigidBodyConstraint` (`obj.rigid_body_constraint`), created via:

```python
bpy.ops.object.empty_add(location=pivot)
con_obj = bpy.context.active_object
bpy.context.view_layer.objects.active = con_obj
bpy.ops.rigidbody.constraint_add(type='HINGE')   # con_obj.rigid_body_constraint now exists
con = con_obj.rigid_body_constraint
con.object1 = obj_a
con.object2 = obj_b
```

`type` enum (live-confirmed on `RigidBodyConstraint`, exact list): `FIXED`, `POINT`, `HINGE`,
`SLIDER`, `PISTON`, `GENERIC`, `GENERIC_SPRING`, `MOTOR`.
`spring_type` enum (for `GENERIC_SPRING`, live-confirmed): `SPRING1`, `SPRING2`.

Full `RigidBodyConstraint` property surface (live-enumerated, 47 fields) includes per-axis
linear/angular limits (`limit_lin_x_lower/upper`, `limit_ang_x_lower/upper`, ... for x/y/z each),
their `use_limit_*` toggles, `use_breaking` + `breaking_threshold` (impulse at which the joint
snaps), `object1`/`object2`, `solver_iterations` + `use_override_solver_iterations`, and per-axis
`spring_stiffness_*`/`spring_damping_*` (linear and angular) for `GENERIC_SPRING`, plus
`motor_lin_target_velocity`/`motor_lin_max_impulse` and their angular counterparts for `MOTOR`.

The RNA does not show **which local axis** a `HINGE` constraint rotates around: freshly created
`HINGE`/`SLIDER` constraints have all `use_limit_*` flags `False` and all three angular-limit
pairs identical (±45°) by default, so the "free" axis isn't visible as a toggled flag; it is fixed
by the constraint type in Blender's Bullet code, not exposed as a settable property. The Blender
manual (Hinge constraint page) gives Z as the Hinge's rotation axis and X as the axis Slider and
Piston translate along. That was not confirmed by a rotation test, so treat it as documented, not
measured.

### Mass calculation

```python
bpy.ops.rigidbody.mass_calculate(material='Custom', density=1.0)
```

**Gotcha, empirically caught**: the operator's own docstring says `material: Literal['DEFAULT']`
— that is misleading/incomplete. Calling it with `material='DEFAULT'` raises:
`TypeError: ... enum "DEFAULT" not found in (...)`. The **real, live enum** is a ~45-item list of
named real-world materials (`Air`, `Acrylic`, `Asphalt (Crushed)`, `Brass`, `Brick (Pressed)`,
`Concrete`, `Glass (Solid)`, `Gold`, `Steel`, `Wood`... through `Custom`). Use `'Custom'` with an
explicit `density` to get a precise, script-controlled mass.

**Empirically verified**: `mass_calculate` correctly uses the object's **world-space (scaled)
volume**, not the raw local-mesh volume — a base 2×2×2 cube scaled `(1,1,3)` (world volume 24)
gave `mass = 24.0` at `density=1.0` whether or not the scale had been `transform_apply`'d first.
This is one of the very few places where un-applied scale demonstrably does **not** bite (see
**Determinism & scale gotchas**).

Signature: `bpy.ops.rigidbody.mass_calculate(*, material='DEFAULT', density=1.0)` (bundled `api/bpy.ops.rigidbody.rst`); the live enum list was confirmed by a direct call.

## Caching & baking

Baking is notoriously context-dependent from scripts. Empirical testing confirmed exactly
that, and gave a precise, verified fix.

### The point cache

`scene.rigidbody_world.point_cache` is a `PointCache` (never `None`) with `frame_start`,
`frame_end` (defaults 1/250, live-confirmed), `frame_step`, `is_baked`, `is_baking`,
`is_frame_skip`, `is_outdated`, `use_disk_cache`, `filepath`. The identical `PointCache` type is
shared by rigid body world, `ClothModifier`, `SoftBodyModifier`, `ParticleSystem`, and
`DynamicPaintSurface` (confirmed via the type's own "References" list in the bundled docs) — so
everything below about the context-override pattern for rigid body applies unchanged to cloth/
soft body/particle point caches, since it's the exact same `bpy.ops.ptcache.*` API operating on
the exact same `PointCache` struct type, just reached via a different owner (`modifier.point_cache`
/ `psys.point_cache` instead of `rigidbody_world.point_cache`).

API reference: `bpy.types.PointCache` (bundled `api/bpy.types.PointCache.rst`).

### `bpy.ops.ptcache.bake` — reproduced failure and the verified fix

Calling it naively from a script **fails**, reproduced directly:

```python
>>> bpy.ops.ptcache.bake(bake=True)
RuntimeError: Operator bpy.ops.ptcache.bake.poll() failed, context is incorrect
```

**Verified working fix** — supply the `point_cache` context member via `temp_override`:

```python
rbw = bpy.context.scene.rigidbody_world
with bpy.context.temp_override(point_cache=rbw.point_cache):
    bpy.ops.ptcache.bake(bake=True)          # -> {'FINISHED'}
# rbw.point_cache.is_baked is now True
```

This was empirically run end-to-end in `--background` mode with **no other context members**
needed — just `point_cache` in the override. (A second attempt additionally supplying
`active_object`/`scene` also succeeded, but they weren't necessary; `point_cache` alone was
sufficient.) Doc for the operator itself: `bpy.ops.ptcache.bake(*, bake=False)` — bundled
`api/bpy.ops.ptcache.rst`.

Related operators in the same module (all share the same context requirement, not individually
re-tested beyond `bake`): `bake_all(bake=True)`, `bake_from_cache()`, `free_bake()`,
`free_bake_all()`, `add()`, `remove()`.

### Is manual `scene.frame_set()` stepping a valid alternative to baking? — Yes, verified

Stepping the frame range yourself, with **no baking and no context override at all**, correctly
drives rigid body (and cloth — see below) simulation and leaves the point cache in the same
`is_baked = True` state:

```python
scene.frame_set(scene.frame_start)
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    # read obj.matrix_world / evaluated mesh here if needed
```

Empirically verified on a falling cube: it descended from z=5.0 to a settled rest at z≈1.0 (correct
for a half-height-1 cube resting on a z=0 plane) purely from repeated `frame_set()` calls, and
`rigidbody_world.point_cache.is_baked` was `True` afterward — Blender's cache system considers a
fully frame-stepped range "baked" the same as an explicit `ptcache.bake` call. This is the
simplest possible pattern and needs zero context tricks, so it's the recommended default for a
script/MCP context whenever you don't need a disk-persisted cache file.

### `bpy.ops.rigidbody.bake_to_keyframes` — fails headlessly; this is a known Blender bug, not user error

Doc/signature (bundled `api/bpy.ops.rigidbody.rst`, source `bl_operators\rigidbody.py:108` in Blender's startup scripts):

```python
bpy.ops.rigidbody.bake_to_keyframes(frame_start=1, frame_end=250, step=1)
```

**Empirically reproduced failure**, called correctly (selection + active object both set,
rigid-body world already simulating fine via manual stepping moments earlier in the same script):

```
RuntimeError: Error: Python: Traceback (most recent call last):
  File "...\scripts\startup\bl_operators\rigidbody.py", line 165, in execute
    bpy.ops.anim.keyframe_insert_by_name(type='BUILTIN_KSI_LocRot')
RuntimeError: Operator bpy.ops.anim.keyframe_insert_by_name.poll() failed, context is incorrect
```

`bake_to_keyframes` is a **Python-defined** operator that internally calls a *second* operator
(`anim.keyframe_insert_by_name`) via `bpy.ops`. Increasingly complete `temp_override`s did not
rescue it: `point_cache` + `active_object` + `scene` + `selected_objects`, then additionally
a real `window`/`screen`/`area`(`VIEW_3D`)/`region` pulled from `bpy.context.window` itself (which
**does exist** even in `--background` mode: `bpy.context.window` and
`bpy.context.screen` ("Layout") are real objects there; only `bpy.context.area` is `None`). None of
these overrides fixed it; the inner `keyframe_insert_by_name` call kept failing identically.

This is a **known Blender limitation**, not a mistake in the override: overriding
context on an outer Python operator does not propagate into `bpy.ops.*` calls that operator makes
internally. Blender tracks it in two bug reports (the report pages were not read in full; the
failure itself was reproduced as shown above):

- `T63067`: context overrides are not passed along by `bl_operators` operators that themselves
  call `bpy.ops`.
- `T97382`: context error when running `bpy.ops.rigidbody.bake_to_keyframes()` from the command
  line.

**Practical conclusion for this skill**: do not build the physics-baking workflow around
`rigidbody.bake_to_keyframes`. It is confirmed broken in pure `--background` execution. Whether it
works when the MCP bridge executes code inside a live GUI Blender session (this skill's actual
target) depends on whether `bpy.context.area` is a valid, correctly-typed area at the moment the
bridge's code runs. That case was not tested. Treat it as **not checked in a live GUI session,
confirmed broken headless**, and default to one of the two robust alternatives below regardless,
since both work in every context tested (they never call `bpy.ops` internally for the risky part).

### Robust alternative #1 (recommended default): `bpy_extras.anim_utils.bake_action`

Blender ships this as pure-Python, data-API-only utility (it's what backs the "Bake Action" NLA
tool). Doc: `bpy_extras.anim_utils.bake_action(obj, *, action, frames, bake_options)` +
`anim_utils.BakeOptions(only_selected, do_pose, do_object, do_visual_keying, do_constraint_clear,
do_parents_clear, do_clean, do_location, do_rotation, do_scale, do_bbone, do_custom_props)` —
bundled `api/bpy_extras.anim_utils.rst`.

**Empirically verified working, zero context override, in pure `--background` mode:**

```python
from bpy_extras import anim_utils
action = anim_utils.bake_action(
    obj, action=None, frames=range(1, 21),
    bake_options=anim_utils.BakeOptions(
        only_selected=False, do_pose=False, do_object=True, do_visual_keying=True,
        do_constraint_clear=False, do_parents_clear=False, do_clean=False,
        do_location=True, do_rotation=True, do_scale=False, do_bbone=False, do_custom_props=False,
    ),
)
```

Result confirmed: a real `Action` gets created and assigned, with F-curves on exactly
`location` and `rotation_euler` (matching the object's `rotation_mode`) — i.e. functionally
identical output to what `bake_to_keyframes` is *supposed* to produce, reached through a path
that never breaks headlessly.

### Robust alternative #2 (simplest, no helper import): manual per-frame `keyframe_insert`

`bpy_struct.keyframe_insert(data_path, *, index=-1, frame=..., group="", options=set(),
keytype='KEYFRAME') -> bool` is a plain **data-API method**, not an operator — it has no `poll()`
and no context dependency at all. Doc: bundled `api/bpy.types.bpy_struct.rst`.

```python
for f in range(frame_start, frame_end + 1):
    scene.frame_set(f)
    obj.keyframe_insert(data_path="location", frame=f)
    obj.keyframe_insert(data_path="rotation_euler", frame=f)
```

Empirically verified working in `--background` with no import, no override.

### Cache invalidation gotcha (empirically encountered, not just theoretical)

Adding a **new** rigid body object to `scene.rigidbody_world.collection` *after* the world's point
cache has already been stepped/baked across a frame range, then jumping back to frame 1 and
re-stepping, produced a clearly wrong result in testing (an object that should have rested on a
floor instead fell to roughly -6.6 units, i.e. straight through the floor with no collision
response at all). Isolating the exact same object/scale setup in a **fresh, single-purpose Blender
process** (no prior rigid-body stepping in that process) gave the correct resting position every
time. This strongly suggests the point cache became stale/inconsistent for the newly-added object
once other objects' frames were already cached — consistent with Blender's cache being scene-wide
and frame-indexed (confirmed structurally: `point_cache` lives once on `rigidbody_world`, shared by
the whole `collection`); the exact internal mechanism was not isolated. **Practical
rule verified by A/B testing**: don't accumulate multiple unrelated rigid-body experiments in one
long-lived scene/script without freeing the cache (`ptcache.free_bake_all()` under the same
`point_cache` override, or rebuild the rigidbody world) between them — each independent simulation
setup got a clean result only when run in its own fresh process/scene.

## Cloth

### Adding the modifier

```python
bpy.context.view_layer.objects.active = mesh_obj
bpy.ops.object.modifier_add(type='CLOTH')
```

Empirically verified working headlessly with `{'FINISHED'}`. Doc:
`bpy.ops.object.modifier_add(*, type='SUBSURF', use_selected_objects=False)` — bundled
`api/bpy.ops.object.rst` (definition block); default `type` is `SUBSURF`, so `type='CLOTH'` must
always be passed explicitly. The modifier is created with the **default name `"Cloth"`**
(live-confirmed: `obj.modifiers['Cloth']`).

There is no lower-level data-API way to add a Cloth modifier other than through this operator
(consistent with every other modifier type — modifiers in general are only addable via
`object.modifier_add` or `object.modifiers.new(name, type)`; both were not separately diffed here
since the operator path was already confirmed sufficient).

The modifier exposes **two separate sub-structs**, easy to conflate:

- `modifiers["Cloth"].settings` → `ClothSettings` — the *fabric* itself (mass, stiffness, pressure...).
- `modifiers["Cloth"].collision_settings` → `ClothCollisionSettings` — how *this* cloth reacts to
  collision objects and to itself (self-collision).

### `ClothSettings` — full verified field list (bundled `api/bpy.types.ClothSettings.rst`)

Core fabric-feel parameters (all confirmed present, with their documented ranges/defaults):

| Field | Default | Meaning |
|---|---|---|
| `quality` | 5 | solver steps per frame (higher = better/slower) |
| `mass` | 0.3 | mass per vertex |
| `air_damping` | 1.0 | air drag on the whole sheet |
| `tension_stiffness` / `_max` | 15.0 | resists stretching |
| `compression_stiffness` / `_max` | 15.0 | resists compression |
| `shear_stiffness` / `_max` | 5.0 | resists shearing |
| `bending_stiffness` / `_max` | 0.5 | resists folding/creasing |
| `tension_damping`, `compression_damping`, `shear_damping`, `bending_damping` | 5.0/5.0/5.0/0.5 | damping per spring type |
| `bending_model` | `'ANGULAR'` | `ANGULAR` (default) or `LINEAR` (legacy) |
| `use_internal_springs` + `internal_*` fields | off | simulate an internal volume structure (connects opposite sides through the mesh) |
| `use_pressure` + `uniform_pressure_force`, `target_volume`, `pressure_factor`, `use_pressure_volume`, `fluid_density` | off | closed-mesh "balloon" pressure simulation |
| `shrink_min` / `shrink_max` | 0.0 | shrink the cloth by a factor |
| `use_sewing_springs` + `sewing_force_max` | off | pulls loose/sewn edges together (garment seams) |
| `vertex_group_mass` | `""` | **this is the pin group** (see below) |
| `vertex_group_bending`, `vertex_group_intern`, `vertex_group_pressure`, `vertex_group_shear_stiffness`, `vertex_group_shrink`, `vertex_group_structural_stiffness` | `""` | spatially-varying overrides for each of those parameters |
| `goal_default`, `goal_min`, `goal_max`, `goal_spring`, `goal_friction` | 0/0/1/1.0/0 | legacy "reactor"-style goal pinning; superseded by `vertex_group_mass` pinning for most uses |
| `rest_shape_key` | `None` | use a Shape Key as the rest/reference geometry instead of the base mesh (useful for sewing patterns / pre-shaped garments) |
| `gravity` | `(0, 0, -9.81)` | **cloth has its own gravity override**, independent of `scene.gravity` — see Determinism section |
| `voxel_cell_size` | 0.1 | self-collision broad-phase grid cell size |
| `effector_weights` | — | force-field response (wind, turbulence, etc.) |
| `time_scale` | 1.0 | speeds up/slows down the sim relative to scene time |
| `use_dynamic_mesh` | off | make the sim respect base-mesh deformation from other modifiers |

### `ClothCollisionSettings` — live-enumerated fields (`modifiers["Cloth"].collision_settings`)

```
collection, collision_quality, damping, distance_min, friction, impulse_clamp,
self_distance_min, self_friction, self_impulse_clamp, use_collision, use_self_collision,
vertex_group_object_collisions, vertex_group_self_collisions
```

`use_collision`/`use_self_collision` are the master toggles; `distance_min`/`self_distance_min`
are the minimum-separation distances (Blender's cloth-vs-collider buffer, distinct from the
collider's own `thickness_outer`, see below); `collision_quality` is the collision solver's own
substep count, separate from `settings.quality`.

### Pin groups (vertex groups + weights) — empirically verified end to end

```python
vg = obj.vertex_groups.new(name="Pin")
vg.add([0, 1, 2, 3, 4], 1.0, 'REPLACE')          # index list, weight, assign mode
obj.modifiers["Cloth"].settings.vertex_group_mass = vg.name
```

`VertexGroup.add(index, weight, type)` doc (bundled `api/bpy.types.VertexGroup.rst`): `index` is a
**list** of vertex indices (not one call per vertex — batch them), `weight` a single float applied
to all listed indices, `type` one of `REPLACE`/`ADD`/`SUBTRACT`.

Verified on an actual falling/draping cloth plane: over 20 stepped frames, the pinned top-row
vertices stayed at **exactly** `z = 0.0` the entire time while the unpinned bottom of the sheet
sagged progressively down to `z ≈ -1.47` — direct proof the pin group correctly held those
vertices in place while the rest simulated freely.

### Collision objects (the *other* side — what cloth collides against)

```python
bpy.context.view_layer.objects.active = floor_obj
bpy.ops.object.modifier_add(type='COLLISION')
```

This exposes `floor_obj.collision` → `CollisionSettings` (**not** on a modifier sub-struct this
time — it's directly on the object), live-enumerated fields:

```
absorption, cloth_friction, damping, damping_factor, damping_random, friction_factor,
friction_random, permeability, stickiness, thickness_inner, thickness_outer,
use, use_culling, use_normal, use_particle_kill
```

`use` is the master enable toggle; `thickness_outer`/`thickness_inner` define the collision-shell
offset from the mesh surface (inner only matters for soft bodies passing through, per its own doc
string); `cloth_friction` is specifically the friction cloth feels against this collider (separate
from the particle-oriented `friction_factor`/`damping_factor`, which are for particle systems, not
cloth).

### Presets — exact values (read directly from Blender's own installed files, not estimated)

Blender ships five built-in cloth presets as plain Python scripts at
`<Blender 5.1 install>\5.1\scripts\presets\cloth\{Cotton,Denim,Leather,Rubber,Silk}.py`. Read verbatim
(these are the literal, authoritative numbers Blender's own "Cotton"/"Silk"/etc. preset menu
entries apply):

| Preset | quality | mass | tension/compression/shear stiffness | bending_stiffness | tension/compression/shear damping | air_damping |
|---|---|---|---|---|---|---|
| Cotton | 5 | 0.300 | 15 / 15 / 15 | 0.5 | 5 / 5 / 5 | 1.0 |
| Denim | 12 | 1 | 40 / 40 / 40 | 10 | 25 / 25 / 25 | 1 |
| Leather | 15 | 0.4 | 80 / 80 / 80 | 150 | 25 / 25 / 25 | 1 |
| Rubber | 7 | 3 | 15 / 15 / 15 | 25 | 25 / 25 / 25 | 1 |
| Silk | 5 | 0.150 | 5 / 5 / 5 | 0.05 | 0 / 0 / 0 | 1 |

(All five also set the same pressure defaults — `use_pressure=False`, `uniform_pressure_force=76.0`,
`target_volume=0.0`, `pressure_factor=1.0`, `fluid_density=0.0` — and the same
`internal_*` defaults; those fields aren't preset-differentiated.)

Reading this table: heavier/stiffer materials (Leather, Denim) pair high stiffness (40–80) with
high damping (25) and higher quality steps (12–15); Silk pairs low stiffness (5) with **zero**
damping and the cheapest quality (5); Rubber is the outlier — very high mass (3) but only
mid-range stretch stiffness, with `bending_stiffness` (25) much higher than Cotton's (0.5), i.e.
it resists *folding* far more than it resists stretching, giving a springy-sheet rather than a
drapey-fabric feel.

**Gotcha — do not call Blender's preset-execute operator from a headless script.** Every preset
file above uses `bpy.context.cloth.settings.X = value`, i.e. it expects a `context.cloth` context
member — the exact same context-member pattern that `ptcache.bake` needed `point_cache` for. Since
this was independently confirmed to be a fragile pattern for `ptcache.bake` (see **Caching &
baking**), the reliable approach is to **not** invoke `bpy.ops.script.execute_preset(...)` at all
and instead set the numeric fields on `modifiers["Cloth"].settings` directly using the table above.

### Cloth deformation — verified computable via plain frame-stepping, no baking needed

```python
depsgraph = bpy.context.evaluated_depsgraph_get()
for f in range(1, 21):
    scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = cloth_obj.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()
    zs = [v.co.z for v in mesh_eval.vertices]
    obj_eval.to_mesh_clear()          # free the temporary evaluated mesh
```

This is the exact pattern used to obtain the pin-group proof above; it needs no cache/bake call at
all — the depsgraph evaluation triggers the cloth solver to compute that frame's state on demand.
`to_mesh_clear()` after use releases the temporary mesh; it is the documented cleanup call for
`evaluated_get().to_mesh()`.

## Soft body

### Adding the modifier

```python
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_add(type='SOFT_BODY')
```

Empirically verified working headlessly. **Gotcha**: the created modifier is named
`"Softbody"` (one word, lowercase `b`) — live-confirmed via `obj.modifiers['Softbody']`; guessing
`"Soft Body"` or `"SoftBody"` will `KeyError`.

### `SoftBodySettings` — full field list (bundled `api/bpy.types.SoftBodySettings.rst`)

Pinning / shape targeting (the primary soft-body-specific mechanism, distinct from cloth's
vertex-group pinning): `use_goal`, `goal_default`, `goal_min`, `goal_max`, `goal_spring`,
`goal_friction`, `vertex_group_goal` — each vertex is pulled toward its **animated/rest** position
by a goal spring rather than being rigidly locked, so goal-pinned soft bodies can still jiggle
around their target.

Edge-spring model (`use_edges` must be on to use mesh edges as springs at all): `pull`, `push`,
`damping`, `bend`, `shear`, `plastic` (permanent/plastic deformation, 0–100), `spring_length`
(% shrink/grow of rest length), `vertex_group_spring`.

Self/edge/face collision (soft body's own, cheaper, "ball" model — distinct from the Cloth
collision system): `use_self_collision`, `use_edge_collision`, `use_face_collision`,
`ball_size`, `ball_stiff`, `ball_damp`, `collision_type` enum
(`MANUAL`/`AVERAGE`/`MINIMAL`/`MAXIMAL`/`MINMAX` — ways to auto-derive `ball_size` from spring
length), `fuzzy` (collision fuzziness — higher is faster but less stable), `collision_collection`.

Solver quality/cost knobs: `step_min`, `step_max`, `use_auto_step`, `error_threshold` (Runge-Kutta
ODE solver tolerance — lower = more precise/slower), `use_diagnose`.

Aerodynamics (cloth-like "sail" behavior applied to edges rather than faces): `aero`,
`aerodynamics_type` (`SIMPLE` / `LIFT_FORCE`).

Mass/gravity/friction: `mass`, `friction`, `gravity` (float, **not** a vector — see below),
`vertex_group_mass`, `speed`.

**Gotcha, empirically confirmed**: the bare RNA schema defaults documented for several of these
fields are *not* what you actually get after `modifier_add(type='SOFT_BODY')`. Reading the settings
right after adding the modifier (live-confirmed):

| Field | RNA doc "default" | Actual value right after `modifier_add` |
|---|---|---|
| `gravity` | 0.0 | **9.8** |
| `mass` | 0.0 | **1.0** |
| `use_goal` | False | **True** |
| `use_edges` | False | **True** |

The add-operator's C-side initializer sets practical starting values that differ from the RNA
property's bare declared default. **Always read settings back after `modifier_add()`** rather than
assuming the documented default is what you'll actually simulate with.

### When soft body beats cloth (general guidance, not benchmarked here)

Soft body operates on the object's general edge/volume topology (springs + optional goal/volume
preservation), so it suits **volumetric, blobby, gelatinous** deformation — jelly, simple
squishy props, rope-like edge chains — where the whole solid volume should wobble, not just a thin
sheet. Cloth is purpose-built for **2-manifold sheet** behavior (its stiffness model decomposes
into tension/compression/shear/bending specifically because that maps onto a fabric surface) and
has a more robust, actively-maintained self-collision system. Soft body is the older, cheaper but
less stable option: use Cloth for anything that visually reads as fabric, and reserve Soft Body
for squishy or gelatinous solids where Cloth's sheet assumptions don't fit. Performance and
stability of the two were not benchmarked against each other; this is general guidance, not a
measured result.

---

## Particles

### Minimal setup — empirically verified working headlessly

```python
bpy.context.view_layer.objects.active = emitter_obj
bpy.ops.object.particle_system_add()          # -> {'FINISHED'}, zero context override needed
psys = emitter_obj.particle_systems[0]
settings = psys.settings                       # ParticleSettings — a reusable ID datablock (bpy.data.particles)
```

Confirmed: no selection or extra context required beyond an active object, matching the pattern
seen for rigid body/cloth/soft-body `modifier_add`/`object_add` calls.

### Key fields for debris/sparks/leaves-style use (bundled `api/bpy.types.ParticleSettings.rst`)

- `type`: `EMITTER` (default) or `HAIR`.
- `physics_type`: `NO`, `NEWTON` (default — simple ballistic point-mass physics, gravity + drag +
  effectors), `KEYED`, `BOIDS`, `FLUID`.
- `emit_from`: `VERT`, `FACE` (default), `VOLUME`.
- `count`, `frame_start`, `frame_end` (the **emission window**, independent of the particles'
  individual `lifetime`/`lifetime_random`).
- `integrator`: `EULER`, `VERLET`, `MIDPOINT` (default), `RK4` — speed vs. stability/accuracy;
  matters for fast-moving debris/sparks where cheap Euler integration can visibly diverge.
- `damping`, `effector_weights` (force-field response — wind/turbulence for e.g. sparks drifting).
- `factor_random` (initial-velocity randomization), `angular_velocity_mode` +
  `angular_velocity_factor` (tumbling debris), `size_random`, `rotation_factor_random`.

### Rendering as objects/collections — the actual "render instance" mechanism, verified

```python
settings.render_type = 'COLLECTION'            # NONE / HALO / LINE / PATH / OBJECT / COLLECTION
settings.instance_collection = debris_collection    # rotate through a Collection's members per particle
# or: settings.instance_object = single_debris_obj   # one object for every particle
```

Empirically verified: assigning a `Collection` to `instance_collection` with `render_type =
'COLLECTION'` round-trips correctly (`settings.instance_collection.name` reads back as assigned).
Related toggles that shape how collection members get distributed: `use_whole_collection`,
`use_collection_pick_random`, `use_collection_count`; and whether each instanced object's own
transform is honored: `use_rotation_instance`, `use_scale_instance`, `use_global_instance`.

**Moving a freshly-created object into a specific collection (a small but real gotcha
encountered while testing this)**: a plain `collection.objects.link(obj)` right after
`primitive_*_add()` can raise `RuntimeError: Object 'X' not in collection 'Scene Collection'`
if you assume which collection the object landed in and try to `unlink` from the wrong one. The
robust pattern is to unlink from **every** collection the object is actually in, then link it to
the target:

```python
for c in list(obj.users_collection):
    c.objects.unlink(obj)
debris_collection.objects.link(obj)
```

### Baking

Particle systems share the exact same `PointCache` API as rigid body/cloth/soft body
(`psys.point_cache`, confirmed via `PointCache`'s own "References" list in the bundled docs
explicitly naming `ParticleSystem.point_cache`). The same verified `ptcache.bake` context-override
pattern from **Caching & baking** applies unchanged:

```python
with bpy.context.temp_override(point_cache=psys.point_cache):
    bpy.ops.ptcache.bake(bake=True)
```

This call was not run against a live particle system. It is included because `PointCache` is the
same shared type that was verified working for rigid body. The same `scene.frame_set()`
manual-stepping alternative (verified for rigid body and cloth) should apply here for the same
structural reason.

### Practical note: particles vs. individual rigid bodies for debris

For **foreground/hero** debris that needs to convincingly collide, tumble, and settle against the
environment, the more robust and commonly-used professional pattern is to give each chunk its own
real rigid body (with an initial velocity via the kinematic-handoff trick — see **Hybrid
keyframe+physics**) rather than driving it through the particle system, because `NEWTON`-physics
particles get simplified point-mass collision against `.collision`-enabled deflector objects, not
full rigid-body rotation/collision response, and particle instances don't collide with each other.
Particles are the right tool for **background/volume** debris — many small bits where individual
collision fidelity doesn't matter (dust, sparks, falling leaves at a distance). This is a
common production pattern, not benchmarked here.

## Export/handoff of sims

### Blender 4.4+/5.x changed how F-curves are read back

Before covering export formats: any code that **inspects** baked keyframes (to verify a bake, or to
prepare data for export) needs to know this. Blender 4.4 introduced **layered/slotted Actions**;
Blender 5.0 then **removed** the backward-compatible shim. Empirically confirmed on the connected
5.1.1:

```python
>>> cube.animation_data.action.fcurves
AttributeError: 'Action' object has no attribute 'fcurves'
```

`bpy.types.Action` in 5.1.1 (bundled `api/bpy.types.Action.rst`, confirmed live) has **no**
`.fcurves`/`.groups` at all — only `.layers` (`ActionLayers[ActionLayer]`) and `.slots`
(`ActionSlots[ActionSlot]`). The real chain, confirmed via the bundled `ActionLayer`,
`ActionKeyframeStrip`, `ActionSlot`, `AnimData` docs (`ActionKeyframeStrip.channelbag(slot,
ensure=False) -> ActionChannelbag`, `ActionChannelbag.fcurves`):

```python
action = obj.animation_data.action
slot = obj.animation_data.action_slot
for layer in action.layers:
    for strip in layer.strips:
        channelbag = strip.channelbag(slot)     # None if this slot has no data on this strip
        if channelbag:
            for fc in channelbag.fcurves:
                ...
```

Or use Blender's own convenience helpers (present in the bundled `bpy_extras.anim_utils.rst`):

```python
from bpy_extras import anim_utils
channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)      # read, may be None
channelbag = anim_utils.action_ensure_channelbag_for_slot(action, slot)   # get-or-create
```

**Exact version boundary** (from Blender's release notes for 4.4 and 5.0; the 5.0 removal was
confirmed live on 5.1.1):

- **4.3 and earlier**: flat `action.fcurves`/`action.groups`/`action.id_root` — this is what
  most existing tutorials and scripts assume.
- **4.4**: introduced layers/slots/channelbags, but **kept** `action.fcurves`/`action.groups` as a
  documented "backward-compatible legacy API" operating on the first slot only (auto-creating a
  "Legacy Slot" the first time something writes through it).
- **5.0+**: the legacy shim was **removed**. `action.fcurves`/`action.groups`/`action.id_root` no
  longer exist at all; `action.id_root` became `action_slot.target_id_type`. Empirically confirmed
  on 5.1.1.

Since this skill's baseline is 4.3 and the version it was tested on is 5.1, **any code that reads
back baked animation must go through the channelbag/`anim_utils` path to work on 5.x, while still
working on 4.3** (where `action.layers`/`.slots` do not exist at all pre-4.4, so the channelbag
path is 4.4+-only). A defensive helper that works on both sides of the 4.4 boundary:

```python
def get_fcurves(obj):
    ad = obj.animation_data
    if ad is None or ad.action is None:
        return []
    action = ad.action
    if hasattr(action, "fcurves"):                 # 4.3 and earlier (flat model)
        return list(action.fcurves)
    from bpy_extras import anim_utils               # 4.4+ (layered model)
    slot = ad.action_slot
    cb = anim_utils.action_get_channelbag_for_slot(action, slot) if slot else None
    return list(cb.fcurves) if cb else []
```

### `bake_to_keyframes` output — what channels it produces

Since `bake_to_keyframes` itself is confirmed broken headlessly (see **Caching & baking**), this
was verified via the equivalent robust path (`anim_utils.bake_action`, `do_location=True,
do_rotation=True, do_scale=False`), which produces the same kind of output the native operator is
documented to produce. Confirmed result: F-curves on exactly `location` (3 channels) and
`rotation_euler` (3 channels, or `rotation_quaternion` if the object's `rotation_mode` is
quaternion-based — not itself separately tested, inferred from `keyframe_insert`'s standard
behavior of keying whatever the object's actual current rotation representation is).

### FBX export and physics sims — precisely, what does and does not survive

`bpy.ops.export_scene.fbx(...)` full signature captured live (bundled `api/bpy.ops.export_scene.rst`,
`addons_core/io_scene_fbx/__init__.py:604`). The relevant parameters for this question:

- `use_mesh_modifiers=True` (default): applies the modifier stack (including Cloth/Soft Body) to
  each mesh **at whatever frame is current at export time** — a single static snapshot. There is
  no parameter anywhere in this operator's signature that re-evaluates modifiers per exported frame
  for mesh *vertex* data.
- The operator's own doc string for `use_mesh_modifiers` explicitly warns: **"WARNING: prevents
  exporting shape keys"** — i.e. applying the modifier stack and exporting shape-key (blend shape)
  animation are **mutually exclusive** in this exporter.
- `bake_anim`, `bake_anim_use_all_bones`, `bake_anim_use_nla_strips`, `bake_anim_use_all_actions`,
  `bake_anim_force_startend_keying`, `bake_anim_step`, `bake_anim_simplify_factor` are **all**
  about baking **armature/bone Action/NLA-driven** animation into the FBX. None of them touch
  modifier-stack or per-vertex mesh deformation.

**Conclusion, precisely**: a Cloth or Soft Body
simulation's per-frame vertex deformation **does not survive FBX export as playable animation**.
FBX only carries (a) object-transform keyframes (fine for rigid-body debris baked via
`bake_action`/manual `keyframe_insert`) and (b) armature-bone animation plus hand-authored
shape-key/blend-shape animation — and neither of those is what a live modifier deformation
automatically becomes. To get cloth motion into an FBX-consuming pipeline you would have to
manually convert the simulation into a keyframed shape-key sequence yourself; Blender has no
single built-in operator that does this conversion (see next paragraph), so it's a genuinely manual,
non-trivial DIY step, not a checkbox.

**DIY shape-key bake, `[DESIGN]`, not run to completion**, built only from
independently-verified primitives (evaluated-mesh reading confirmed under Cloth above; `keyframe_insert`
confirmed under Caching & baking):

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
    # then keyframe sk.value as a 0/1/0 spike at frame f — one shape key PER FRAME,
    # which is heavy (hundreds of shape keys for a long sim) and not how this is normally done in practice.
```

Given the cost of one-shape-key-per-frame, Alembic (below) is the practical answer whenever the
target pipeline can consume it.

### Alembic export — confirmed working, correctly captures per-vertex deformation

```python
bpy.ops.wm.alembic_export(filepath=path, start=1, end=20, selected=True)
```

**Empirically verified**: this wrote a real 335,838-byte `.abc` file starting with the `Ogawa`
magic header bytes (`b'Ogawa\xff\x00...'` — Alembic's standard binary storage backend), exporting
the same cloth plane whose per-vertex deformation was independently confirmed varying frame-to-
frame (see **Cloth**). The exporter's own `start`/`end` parameters drive its **internal** per-frame
re-evaluation during export, independent of whatever frame the scene happened to be on when the
operator was called.

**The bundled doc index lacks this operator**: `bpy.ops.wm.alembic_export` is **absent** from
the Blender MCP server's bundled doc index. Both `get_python_api_docs("bpy.ops.wm.alembic_export")`
and a full-text `search_api_docs` for "alembic export" return nothing, and the bundled
`bpy.ops.wm` namespace listing does not include it. Only a real, successful export call against
the running Blender 5.1.1 settles it (`hasattr` on `bpy.ops` proves nothing: it is truthy for any
name, see the version wall in `SKILL.md`). Treat the bundled doc index as a hint, and call an
operator on the live process before concluding it is gone.

Full parameter list captured live via the operator's own RNA (`bpy.ops.wm.alembic_export.get_rna_type().properties`,
via the collection-exporter's `export_properties`): `filepath`, `start`, `end`, `selected`,
`visible_objects_only` is **not** present in 5.1.1 (see version note below), `global_scale`,
`flatten`, `uvs`, `vcolors`, `normals`, `face_sets`, `subdiv_schema`, `apply_subdiv`,
`curves_as_mesh`, `export_hair`, `export_particles`, `export_custom_properties`,
`use_instancing`, `triangulate`, `quad_method`, `ngon_method`, `packuv`, `orcos`, `gsamples`
(motion-blur shutter samples), `sh_open`/`sh_close` (shutter open/close), `sort_method`,
`init_scene_frame_range`, `evaluation_mode`, `as_background_job`, `display_type`,
`check_existing`, `filemode`, plus standard file-browser filter fields.

**Version note (Blender 4.2+ collection exporters)**: 5.1 also exposes Alembic (and USD) export
through a newer "Collection Exporters" system — confirmed live:

```python
exporter = collection.exporters.new('IO_FH_alembic', name="AlembicExporter")
bpy.ops.wm.collection_export_all()          # -> {'FINISHED'}, exports every collection's attached exporters
```

The `visible_objects_only` option was removed from `wm.alembic_export`/`wm.usd_export` in
Blender 5.0 (release notes; absent on the live 5.1.1). For a one-shot script/MCP export, calling
`bpy.ops.wm.alembic_export()` directly (as verified above) is simpler than setting up a collection
exporter and works the same way on 4.3 and 5.x; collection exporters are more suited to an
artist-maintained "always export this collection on save" workflow.

### MDD / PC2 point-cache export — not available in this Blender build

Checked directly: `bpy.ops.export_shape` does not exist as a module at all
(`get_python_api_docs` returns `found: false` with an **empty** available-members list), and
`bpy.ops.export_anim` only contains `bvh` (BVH motion-capture export for armatures — unrelated to
mesh vertex caches). Blender historically bundled a Lightwave Point Cache (`.mdd`)/`.pc2` exporter
add-on; it is **not present** in this 5.1.1 build. If a downstream pipeline specifically needs
MDD/PC2 rather than Alembic, that requires a third-party/legacy add-on — out of scope for a
programmatic, current-Blender skill. Don't assume this exporter exists; verify per-installation if
it matters.

## Determinism & scale gotchas

### Gravity is not one single setting

`scene.gravity` is a `Vector`, live-confirmed default `(0.0, 0.0, -9.81)` — this drives rigid body
simulation. But **Cloth and Soft Body each carry their own independent gravity override**:
`ClothSettings.gravity` (Vector, confirmed default `(0, 0, -9.81)`, matching the scene) and
`SoftBodySettings.gravity` (a **float**, not a vector — confirmed the add-operator actually
initializes it to `9.8`, not the RNA schema's stated `0.0` default, per the **Soft body** section
above). Changing `scene.gravity` alone will **not** change already-configured cloth/soft-body sims
— all three need to be set for consistency if that matters for the shot.

### The classic "scene scale" slow-motion bug (mechanism verified, symptom not reproduced here)

Blender's physics assumes **1 Blender unit = 1 real-world meter** — gravity is a fixed
`9.81` units/s² constant (confirmed above), and `rigidbody.mass_calculate`'s density presets are
real-world kg/m³ values (confirmed via the live ~45-item material enum: `Air`, `Steel`, `Gold`,
etc.). If a scene/asset was authored or imported at the wrong real-world scale (e.g., 1 Blender
unit representing 1 cm instead of 1 m, so a visually "human-sized" object is actually 100× too
small in Blender units), gravity will look wrong **relative to the object's own size**: an
object too small in Blender units falls the same fixed number of *units*/s² as anything else, so
relative to its own tiny extent it visibly crawls — this reads as slow-motion/moon-gravity. An
object modeled too *large* looks unnaturally fast/violent by the same logic. Fix: match Scene
Properties → Units → Unit Scale to the asset's real dimensions (1.0 = meters), or literally rescale
geometry so 1 Blender unit ≈ 1 meter before simulating. The mechanism (a fixed,
unit-independent gravity constant, confirmed above) is verified; the visual symptom was not
reproduced in a dedicated test.

### Per-object un-applied `object.scale` — tested, and the answer is more nuanced than blanket folklore

Ran a controlled A/B comparison (isolated, single-purpose Blender processes each — see the cache-
invalidation note in **Caching & baking** for why isolation mattered) on a default cube (base
half-extent 1) given a non-uniform `scale = (1, 1, 3)`, **not** applied, positioned so its scaled
bottom face exactly touches a passive floor at `z = 0`:

| Collision shape | Un-applied scale, final resting Z (should be 3.0) | Applied scale, final resting Z |
|---|---|---|
| `BOX` | **3.0000** (exact, every frame) | 3.0000 |
| `CONVEX_HULL` | **2.9202** (~0.08 unit / ~2.7% penetration into the floor) | 3.0001 (essentially exact) |

`mass_calculate(material='Custom', density=1.0)` gave **24.0 in every combination** (matching the
true world-space volume 2×2×6=24), confirming mass calculation correctly accounts for world-space
scale regardless of whether it's applied.

**Conclusion, evidence-based rather than folklore-repeated**: for a simple analytic `BOX` shape
with no rotation, un-applied non-uniform scale made **no measurable difference** to either mass or
collision response. For `CONVEX_HULL` (mesh-derived) collision, un-applied scale produced a real,
small, consistently reproducible penetration. The likely mechanism (not independently isolated
further) is that Blender's small fixed collision margin around hull-type shapes doesn't scale
consistently with an un-applied object transform. **Practical recommendation**: apply scale
(`bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)` — standard operator,
requires the object selected+active, confirmed working headlessly) before adding physics whenever
using `MESH`/`CONVEX_HULL`/`COMPOUND` shapes. It is not proven necessary for `BOX`/`SPHERE` on an
unrotated object by this test. Three further cases, not tested here, are reasons to apply scale as
a standing habit: non-uniform scale combined **with** rotation, rigid body constraints, and
cloth/soft-body (whose spring rest-lengths are derived from **local**-space edge lengths, so an
un-applied scale makes the stiffness sliders behave inconsistently with the sheet's real-world
size). Applying it costs nothing, so apply it by default.

### A related, smaller gotcha caught while building the scale test: stale `.dimensions` reads

Reading `obj.dimensions` **immediately** after directly setting `obj.scale = (...)` via the data API,
with no operator call and no explicit depsgraph update in between, returned the **pre-change**
bounding-box size in testing (a `(1,1,3)`-scaled 2×2×2 cube reported `dimensions = (2,2,2)`, not
`(2,2,6)`, until something else forced an update). After `transform_apply` (a full operator call)
ran, dimensions were correct immediately. This suggests `.dimensions` (and other
`matrix_world`-derived read-back properties) can be **stale** immediately after a raw data-API
transform write, until the depsgraph next refreshes — don't trust a `.dimensions`/`.matrix_world`
read placed directly after a bare property assignment without an intervening `frame_set()`,
operator call, or explicit depsgraph update.

### FPS vs. substeps

`rigidbody_world.substeps_per_frame` (confirmed live, see **Rigid body**) is named and documented
as "steps taken **per frame**", not per second — so it scales with whatever the scene's frame rate
is, not against a fixed real-time rate. Raising `substeps_per_frame`/`solver_iterations` improves
accuracy for fast-moving/thin objects (reduces tunneling) at CPU cost, independent of playback FPS.
Changing `scene.render.fps` without adjusting frame-relative parameters (particle `lifetime`,
keyframed timing, `frame_start`/`frame_end` of a cache) will change how much *wall-clock* time a
fixed frame range represents, which in turn changes how "fast" the simulated motion reads, even
though the physics stepping itself is unaffected. `scene.render.fps` is the property the preflight
probe in `SKILL.md` reads.

### Origin placement (center of mass) for rigid bodies

`RigidBodyObject` has no separate "center of mass override" property (confirmed absent from its
live-enumerated field list) — the effective center of mass for a primitive collision shape follows
the object's **origin**. `bpy.ops.object.origin_set(type=..., center='MEDIAN'|'BOUNDS')` is the
relevant operator (doc confirmed: `type` enum is `GEOMETRY_ORIGIN`, `ORIGIN_GEOMETRY`,
`ORIGIN_CURSOR`, `ORIGIN_CENTER_OF_MASS`, `ORIGIN_CENTER_OF_VOLUME`). Note the **precise documented
distinction** between the two mass-related options, easy to conflate: `ORIGIN_CENTER_OF_MASS` is
computed **"from the surface area"** (i.e. treats the object like a hollow shell), while
`ORIGIN_CENTER_OF_VOLUME` is computed **"from the volume (must be manifold geometry with
consistent normals)"**. For a solid prop with uniform assumed density, `ORIGIN_CENTER_OF_VOLUME` is
the physically-meaningful choice, not `ORIGIN_CENTER_OF_MASS` despite the more inviting name —
this was verified from the operator's own doc string, not assumed.

---

## Hybrid keyframe+physics

### Throwing an object with initial velocity — the kinematic-handoff trick, verified end to end

Since `RigidBodyObject` has no settable velocity property at all (confirmed under **Rigid body**),
the only way to give a rigid body motion at the moment it starts simulating is to animate it
normally while `kinematic = True`, then switch `kinematic` to `False` (keyframed) at the release
frame. `kinematic` is a plain bool property and is keyframeable like any other:

```python
cube.rigid_body.kinematic = True
cube.rigid_body.keyframe_insert(data_path="kinematic", frame=1)
for f in range(1, 11):                       # phase 1: fully keyframed motion, +X at 1 unit/frame
    cube.location = (1.0 * (f - 1), 0.0, 10.0)
    cube.keyframe_insert(data_path="location", frame=f)

cube.rigid_body.kinematic = False            # phase 2: hand off to the dynamic simulation
cube.rigid_body.keyframe_insert(data_path="kinematic", frame=11)
```

**Empirically verified, exact numbers**: stepping frames 1→30, X advanced exactly 0,1,2,...,9
during the keyframed phase (frames 1–10) as expected. At frame 11 (the instant `kinematic` becomes
`False`), the object's X position **continued advancing** (9.999 → 10.996 → 11.992 → 12.986 → ...),
at very nearly the same ~1 unit/frame rate established during the keyframed phase, while Z
simultaneously began falling under gravity (10.0 → 9.99 → 9.96 → ... → 6.6 by frame 30). This
conclusively confirms **Blender's rigid body system inherits velocity from the object's keyframed
motion at the exact frame the handoff happens** — it does not reset to rest. The gradual slight
decrease in the per-frame X delta after release (0.9973, 0.9957, 0.994, 0.9923, ...) is consistent
with `RigidBodyObject.linear_damping`'s default non-zero value continuously bleeding off velocity
once the object is dynamic — not a flaw in the handoff itself.

**Practical pattern derived from this test** (the specific "≥2 prior keyframes" requirement was
not separately isolated — this reflects what was actually tested, not a proven minimum): keyframe
at least a couple of frames of real motion immediately before the release frame so Blender has a
genuine position delta to compute a velocity from, then keyframe `kinematic = False` exactly on the
frame you want the throw to begin. A single static keyframe with no preceding motion would give
Blender nothing to compute a velocity from and was not tested here.

## Pitfalls

Consolidated, ranked roughly by how much damage each one does when it is not known. All numbered
items were empirically verified unless marked otherwise.

1. **`Action.fcurves` does not exist in Blender 5.0+.** The single biggest 4.3-vs-5.x breaking
   change relevant to this entire skill domain — it silently breaks *any* code that inspects or
   post-processes baked keyframes (which is most of what a physics-baking skill needs to do after
   simulating). 4.3: flat `action.fcurves` works. 4.4: still works (legacy shim). 5.0+: `AttributeError`.
   Use `bpy_extras.anim_utils.action_get_channelbag_for_slot()`/`action_ensure_channelbag_for_slot()`,
   or branch on `hasattr(action, "fcurves")`. See **Export/handoff of sims**.

2. **`rigidbody.bake_to_keyframes` fails in headless/background execution**, and the failure
   traces to a known Blender limitation (context overrides on an outer Python-defined operator
   do not propagate into `bpy.ops.*` calls that operator makes internally; Blender bug reports
   `T63067` and `T97382`), not a mistake in how it's called. No `temp_override` combination
   rescued it, including one supplying a real window/screen/area/region.
   Default to `bpy_extras.anim_utils.bake_action()` or a manual per-frame `keyframe_insert()` loop —
   both are pure data-API and verified working in every context tested. Whether the native operator
   works when driven by a live GUI Blender via the MCP bridge (this skill's actual target)
   was **not** checked, so do not assume it works there.

3. **`ptcache.bake(bake=True)` needs `bpy.context.temp_override(point_cache=world.point_cache)`** or
   it raises `RuntimeError: ... poll() failed, context is incorrect`. Verified minimal working fix.

4. **`rigidbody_world.steps_per_second` was renamed `substeps_per_frame`.** Confirmed absent/present
   exactly this way on 5.1.1. Use a `getattr` fallback for cross-version code; the version of the
   rename is not determined (no 4.3 executable was available to compare).

5. **`bpy.ops.wm.alembic_export` is missing from the Blender MCP server's bundled doc index**,
   even though it exists and works on the live Blender. A check against the doc index alone
   concludes, wrongly, that Alembic export was removed. A bundled doc snippet is a hint; a call
   against the live process settles the claim.

6. **FBX cannot carry Cloth/Soft-Body per-frame vertex deformation.** `use_mesh_modifiers=True`
   bakes a single static snapshot at the current frame and its own doc string says it **prevents**
   shape-key export; none of the `bake_anim_*` parameters touch modifier/vertex data, only
   armature/Action/NLA animation. Alembic (verified working, captures true per-frame deformation) or
   a manual per-frame shape-key bake (not built-in, `[DESIGN]` only) are the only paths.

7. **Directly setting `.scale`/`.location`/`.rotation_euler` via the data API can leave
   `.dimensions` (and likely other `matrix_world`-derived reads) stale** until the next depsgraph
   update/operator call/`frame_set()`. Don't read derived geometry immediately after a bare
   transform write inside the same script tick without something forcing a refresh in between.

8. **Un-applied non-uniform object scale is not a blanket physics bug** — measured **zero**
   difference for `BOX` shape (mass and resting position identical to 4 decimals with/without
   `transform_apply`), but a real, small, reproducible ~2.7%-of-half-height penetration for
   `CONVEX_HULL`. Apply scale as a standing habit for mesh/hull-derived collision shapes; it's not
   proven necessary for simple analytic shapes on an unrotated object, but costs nothing to do
   anyway.

9. **Point cache can go stale when rigid-body-world collection membership changes after a bake/step
   already ran for that range.** Empirically caught as an A/B discrepancy (identical setup gave a
   correct rest position in an isolated fresh process, but fell straight through the floor when run
   as one of several sequential rigid-body experiments sharing the same scene/world). Free/rebuild
   the point cache (or just use a fresh scene/world) whenever the set of simulated objects changes
   after any prior baking/stepping in that same world.

10. **Cloth/Soft-Body preset scripts assume a `context.cloth`/`context.soft_body` context member**
    (`bpy.context.cloth.settings.X = value`), the same fragile pattern as `ptcache.bake`'s
    `point_cache` member. Don't invoke Blender's preset-execute operator from a headless script —
    set the numeric fields directly on `modifiers["Cloth"].settings` (exact preset values are listed
    in **Cloth**, read verbatim from Blender's own installed preset files).

11. **`rigidbody.mass_calculate`'s `material` parameter is not `'DEFAULT'`** despite the operator's
    own bundled doc string literally saying `Literal['DEFAULT']`. The real, live enum is a ~45-item
    named-material list ending in `'Custom'`. Use `'Custom'` with an explicit `density` for a
    precise, script-controlled mass; calling with `material='DEFAULT'` raises `TypeError`.

12. **No built-in MDD/PC2 exporter exists in this Blender build** (`bpy.ops.export_shape` module
    doesn't exist at all; `bpy.ops.export_anim` only has `bvh`). Don't assume it's available;
    verify per-installation if a specific pipeline needs that format instead of Alembic.

13. **`RigidBodyObject.mesh_source` (`BASE`/`DEFORM`/`FINAL`) matters whenever a rigid body object
    also carries a deforming modifier** (e.g. Cloth or Armature on the same object) — `DEFORM`/
    `FINAL` track that deformation every frame (more expensive), `BASE` stays static from the
    undeformed mesh. Easy to overlook since most rigid bodies are simple rigid props where this
    never comes up.

14. **`SoftBodySettings`' actual initialized values differ from the bare RNA-documented defaults**
    right after `modifier_add(type='SOFT_BODY')` (`gravity` reads 9.8 not the doc's stated 0.0,
    `mass` reads 1.0 not 0.0, `use_goal`/`use_edges` read `True` not `False`). Always read settings
    back after adding the modifier rather than trusting the bare property doc string for "what will
    this look like out of the box."

## Verified bpy snippets

Every snippet in this section was executed against Blender 5.1.1 in `--background` mode.
The `# bpy...` comments and the "Doc:" lines name the API reference page (construct the URL as
`https://docs.blender.org/api/<version>/<identifier>.html`).

### 1. Rigid body basics — active + passive, zero context override needed

```python
import bpy
scene = bpy.context.scene

bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
bpy.ops.rigidbody.object_add(type='PASSIVE')          # bpy.ops.rigidbody.object_add

bpy.ops.mesh.primitive_cube_add(location=(0, 0, 5))
cube = bpy.context.active_object
bpy.context.view_layer.objects.active = cube
bpy.ops.rigidbody.object_add(type='ACTIVE')
cube.rigid_body.collision_shape = 'BOX'               # bpy.types.RigidBodyObject.collision_shape
cube.rigid_body.mass = 1.0
cube.rigid_body.friction = 0.5
cube.rigid_body.restitution = 0.3                     # "bounciness"
```
Doc: `bpy.ops.rigidbody.object_add`, `bpy.types.RigidBodyObject`.

### 2. Rigid body constraint (hinge) between two bodies

```python
bpy.ops.object.empty_add(location=(1, 0, 5))
con_obj = bpy.context.active_object
bpy.context.view_layer.objects.active = con_obj
bpy.ops.rigidbody.constraint_add(type='HINGE')        # bpy.ops.rigidbody.constraint_add
con = con_obj.rigid_body_constraint
con.object1 = obj_a
con.object2 = obj_b
con.use_breaking = True
con.breaking_threshold = 50.0
```
Doc: `bpy.ops.rigidbody.constraint_add`, `bpy.types.RigidBodyConstraint`.

### 3. Simulating via plain frame-stepping (no bake needed) — rigid body or cloth

```python
scene.frame_start, scene.frame_end = 1, 60
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)                                # bpy.types.Scene.frame_set (drives the sim)
    # scene.rigidbody_world.point_cache.is_baked becomes True once the full range has been stepped
```

### 4. `ptcache.bake` from script — the verified working context override

```python
rbw = scene.rigidbody_world
with bpy.context.temp_override(point_cache=rbw.point_cache):
    bpy.ops.ptcache.bake(bake=True)                   # bpy.ops.ptcache.bake — FAILS without this override
```

### 5. Robust bake-to-keyframes (works everywhere; native `rigidbody.bake_to_keyframes` does not)

```python
from bpy_extras import anim_utils
action = anim_utils.bake_action(                       # bpy_extras.anim_utils.bake_action
    cube, action=None, frames=range(1, 61),
    bake_options=anim_utils.BakeOptions(
        only_selected=False, do_pose=False, do_object=True, do_visual_keying=True,
        do_constraint_clear=False, do_parents_clear=False, do_clean=False,
        do_location=True, do_rotation=True, do_scale=False, do_bbone=False, do_custom_props=False,
    ),
)
```

Or the dependency-free manual version:

```python
for f in range(1, 61):
    scene.frame_set(f)
    cube.keyframe_insert(data_path="location", frame=f)      # bpy_struct.keyframe_insert — no operator, no poll
    cube.keyframe_insert(data_path="rotation_euler", frame=f)
```

### 6. Reading back F-curves safely across the Blender 4.3 / 4.4+ / 5.0+ Action-model split

```python
def get_fcurves(obj):
    ad = obj.animation_data
    if ad is None or ad.action is None:
        return []
    action = ad.action
    if hasattr(action, "fcurves"):            # Blender <= 4.x (4.4 kept it as a legacy shim)
        return list(action.fcurves)
    from bpy_extras import anim_utils          # Blender 5.0+ — legacy shim removed
    slot = ad.action_slot
    cb = anim_utils.action_get_channelbag_for_slot(action, slot) if slot else None
    return list(cb.fcurves) if cb else []
```
Doc: `bpy.types.Action`, `bpy.types.ActionChannelbag`, `bpy_extras.anim_utils`.

### 7. Cloth: modifier, cotton-like settings, pin group, collision floor

```python
bpy.context.view_layer.objects.active = cloth_plane
bpy.ops.object.modifier_add(type='CLOTH')             # bpy.ops.object.modifier_add
cs = cloth_plane.modifiers["Cloth"].settings           # bpy.types.ClothSettings
cs.quality = 5; cs.mass = 0.3
cs.tension_stiffness = cs.compression_stiffness = cs.shear_stiffness = 15
cs.bending_stiffness = 0.5
cs.tension_damping = cs.compression_damping = cs.shear_damping = 5
cs.air_damping = 1.0

vg = cloth_plane.vertex_groups.new(name="Pin")         # bpy.types.VertexGroup.add
vg.add([0, 1, 2, 3], 1.0, 'REPLACE')
cs.vertex_group_mass = vg.name

cloth_plane.modifiers["Cloth"].collision_settings.use_collision = True
cloth_plane.modifiers["Cloth"].collision_settings.distance_min = 0.015

bpy.context.view_layer.objects.active = floor
bpy.ops.object.modifier_add(type='COLLISION')          # collider side: object.collision, NOT a modifier sub-struct
floor.collision.thickness_outer = 0.02
```

### 8. Reading deformed cloth/soft-body geometry per frame (no baking required)

```python
for f in range(1, 21):
    scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = cloth_plane.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()
    verts_world = [obj_eval.matrix_world @ v.co for v in mesh_eval.vertices]
    obj_eval.to_mesh_clear()
```

### 9. Soft body minimal setup

```python
bpy.context.view_layer.objects.active = blob
bpy.ops.object.modifier_add(type='SOFT_BODY')          # modifier is named "Softbody" (no space)
sb = blob.modifiers["Softbody"].settings               # bpy.types.SoftBodySettings
sb.use_goal = True
sb.goal_spring = 0.5
sb.use_edges = True
sb.pull = 0.5; sb.push = 0.5; sb.damping = 5.0
```

### 10. Particle debris using a collection of instanced objects

```python
bpy.context.view_layer.objects.active = emitter
bpy.ops.object.particle_system_add()                   # bpy.ops.object.particle_system_add
settings = emitter.particle_systems[0].settings         # bpy.types.ParticleSettings
settings.count = 200
settings.physics_type = 'NEWTON'
settings.render_type = 'COLLECTION'
settings.instance_collection = debris_collection
settings.use_rotation_instance = True
settings.factor_random = 2.0
```

### 11. Alembic export (survives cloth/soft-body deformation; FBX does not)

```python
bpy.ops.object.select_all(action='DESELECT')
cloth_plane.select_set(True)
bpy.ops.wm.alembic_export(                              # bpy.ops.wm.alembic_export
    filepath="//cloth_cache.abc", start=1, end=60, selected=True,
)
```

### 12. Applying scale before adding rigid body physics (recommended default habit)

```python
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # bpy.ops.object.transform_apply
bpy.ops.rigidbody.object_add(type='ACTIVE')
obj.rigid_body.collision_shape = 'CONVEX_HULL'
```

### 13. Kinematic-handoff "throw" — the only way to give a rigid body initial velocity

```python
obj.rigid_body.kinematic = True
obj.rigid_body.keyframe_insert(data_path="kinematic", frame=1)
for f in range(1, 11):                                  # establish a real velocity over ≥2 frames
    obj.location = start + velocity * (f - 1)
    obj.keyframe_insert(data_path="location", frame=f)
obj.rigid_body.kinematic = False                        # release — sim inherits the established velocity
obj.rigid_body.keyframe_insert(data_path="kinematic", frame=11)
```

## Not verified

- Any behaviour specific to Blender **4.3 as an executable**. Every 4.3-vs-5.x difference above
  comes from release notes or from the API reference, not from a 4.3 run. If precise 4.3 behaviour
  matters, run the snippets under **Verified bpy snippets** on Blender 4.3.
- Whether `rigidbody.bake_to_keyframes` succeeds when driven by a live GUI Blender through the MCP
  bridge (`mcp__Blender__execute_blender_code`). Only `--background` execution was exercised. Run a
  one-time live-session smoke test before relying on it there.
- Soft body against cloth for performance and stability, and `ptcache.bake` on a particle system:
  the first is general guidance, the second follows from the shared `PointCache` type; neither
  was benchmarked or run.
- The Blender version in which `steps_per_second` became `substeps_per_frame`.
- The Hinge rotation axis (Z in the Blender manual; no rotation test was run).
