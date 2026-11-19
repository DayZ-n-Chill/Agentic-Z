# Rigid bodies in bpy

How a script adds rigid bodies and their constraints in Blender, sets mass, shape and bounce, throws an object with a starting speed, and avoids the scale, origin and gravity traps. Baking and export are in `blender-bpy-sim-baking-export.md`; cloth, soft bodies and particles in `blender-bpy-cloth-and-particles.md`.

This is Blender behaviour, run on Blender 5.1 with `blender --background` or taken from the API reference the Blender MCP server bundles, so nothing here cites `P:\`. No 4.3 build was run; 4.3 differences come from release notes. The DayZ side is in `blender-txa-export.md`.

## Adding a rigid body

There is no data API constructor: `bpy.types.RigidBodyObject()` raises `TypeError: bpy_struct.__new__(struct): expected a single argument`. Use the operator, which works headless with only the active object set:

```python
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
bpy.ops.rigidbody.object_add(type='PASSIVE')

bpy.ops.mesh.primitive_cube_add(location=(0, 0, 5))
cube = bpy.context.active_object
bpy.context.view_layer.objects.active = cube
bpy.ops.rigidbody.object_add(type='ACTIVE')
cube.rigid_body.collision_shape = 'BOX'
cube.rigid_body.mass = 1.0
cube.rigid_body.friction = 0.5
cube.rigid_body.restitution = 0.3
```

`object_add` creates `scene.rigidbody_world` and its `"RigidBodyWorld"` collection when there is none.

| `bpy.ops.rigidbody` operator | Arguments | Does |
|---|---|---|
| `object_add`, `objects_add` | `type='ACTIVE'` | The active object, or every selected one. |
| `object_remove`, `objects_remove` | | Removes. |
| `object_settings_copy` | | Copies the active object's settings to the others selected. |
| `world_add`, `world_remove` | | Manages the world by hand; usually automatic. |
| `constraint_add`, `constraint_remove` | `type='FIXED'` | On the active object, normally an empty. |
| `connect` | `con_type='FIXED'`, `pivot_type='CENTER'`, `connection_pattern='SELECTED_TO_ACTIVE'` | Makes constraint objects between selected bodies (`SELECTED_TO_ACTIVE` or `CHAIN_DISTANCE`); the quick way to build chains or glue fragments. |
| `shape_change` | `type='MESH'` | Changes the shape of every selected body. |
| `mass_calculate` | `material`, `density=1.0` | See "Mass" below. |
| `bake_to_keyframes` | `frame_start=1`, `frame_end=250`, `step=1` | Fails headless (`blender-bpy-sim-baking-export.md`). |

## Body settings

`obj.rigid_body` has `angular_damping`, `collision_collections`, `collision_margin`, `collision_shape`, `deactivate_angular_velocity`, `deactivate_linear_velocity`, `enabled`, `friction`, `kinematic`, `linear_damping`, `mass`, `mesh_source`, `restitution`, `type`, `use_deactivation`, `use_deform`, `use_margin` and `use_start_deactivated`.

- `type` is `ACTIVE` or `PASSIVE`.
- `collision_shape` is `BOX`, `SPHERE`, `CAPSULE`, `CYLINDER`, `CONE`, `CONVEX_HULL`, `MESH` or `COMPOUND`.
- `mesh_source` (for `MESH` and `CONVEX_HULL`) is `BASE`, `DEFORM` or `FINAL`. `DEFORM` and `FINAL` follow deforming modifiers (cloth, armature) every frame at a cost; `BASE` stays with the undeformed mesh. Check it whenever a rigid body also deforms.
- `restitution` is bounciness: 0 none, 1 perfectly elastic.
- There is no velocity property (`linear_velocity`, `angular_velocity` or `velocity`). The only way to give a body a starting speed is the kinematic handoff below.
- There is no centre of mass setting; a primitive shape's centre of mass follows the object origin (see "Origin and centre of mass").

## The rigid body world

`scene.rigidbody_world` has `collection`, `constraints`, `effector_weights`, `enabled`, `point_cache` (never `None`), `solver_iterations` (default 10), `substeps_per_frame` (default 10), `time_scale` (1.0) and `use_split_impulse` (`False`). `constraints` is a separate collection of constraint empties, `None` until the first constraint.

Older tutorials use `steps_per_second`; on 5.1 it raises `AttributeError`, renamed `substeps_per_frame` ("Number of simulation steps taken per frame"). The version of the rename is not known, so look up either:

```python
def get_substeps(rbw):
    for name in ('substeps_per_frame', 'steps_per_second'):
        if hasattr(rbw, name):
            return getattr(rbw, name)
    return 10
```

Substeps count per frame, not per second. Raising `substeps_per_frame` or `solver_iterations` stops fast or thin objects passing through things, at a CPU cost. Changing `scene.render.fps` without changing frame based values (particle `lifetime`, keyed timing, cache range) changes how much real time a frame range stands for, so the motion reads faster or slower even though the stepping is the same.

## Constraints between bodies

A rigid body constraint is a separate empty carrying `obj.rigid_body_constraint`:

```python
bpy.ops.object.empty_add(location=(1, 0, 5))
con_obj = bpy.context.active_object
bpy.context.view_layer.objects.active = con_obj
bpy.ops.rigidbody.constraint_add(type='HINGE')
con = con_obj.rigid_body_constraint
con.object1 = obj_a
con.object2 = obj_b
con.use_breaking = True
con.breaking_threshold = 50.0     # impulse at which the joint snaps
```

`type` is `FIXED`, `POINT`, `HINGE`, `SLIDER`, `PISTON`, `GENERIC`, `GENERIC_SPRING` or `MOTOR`; `spring_type` for `GENERIC_SPRING` is `SPRING1` or `SPRING2`. The 47 fields include per axis linear and angular limits (`limit_lin_x_lower` and so on) with `use_limit_*` toggles, `use_breaking` and `breaking_threshold`, `solver_iterations` with `use_override_solver_iterations`, per axis `spring_stiffness_*` and `spring_damping_*`, and `motor_lin_target_velocity`, `motor_lin_max_impulse` and their angular pair for `MOTOR`.

Which axis a hinge turns about is fixed in Blender's physics code and not exposed: a new hinge or slider has every `use_limit_*` off and the same ±45 degree angular limits on all three axes. The manual gives Z as the hinge axis and X as the slider and piston axis; no rotation test confirmed it.

## Mass

```python
bpy.ops.rigidbody.mass_calculate(material='Custom', density=1.0)
```

The operator's docstring says `material: Literal['DEFAULT']`, but `'DEFAULT'` raises `TypeError: ... enum "DEFAULT" not found`. The real list has about 45 named materials (`Air`, `Acrylic`, `Asphalt (Crushed)`, `Brass`, `Brick (Pressed)`, `Concrete`, `Glass (Solid)`, `Gold`, `Steel`, `Wood` and more) ending in `Custom`; use `Custom` with a density for an exact mass.

It uses the world space volume: a 2×2×2 cube scaled `(1, 1, 3)` gives a mass of 24.0 at density 1.0 whether or not the scale was applied.

## Throwing an object

With no velocity property, animate the body as kinematic, then key `kinematic` off on the release frame:

```python
cube.rigid_body.kinematic = True
cube.rigid_body.keyframe_insert(data_path="kinematic", frame=1)
for f in range(1, 11):                        # keyed motion, +X at 1 unit per frame
    cube.location = (1.0 * (f - 1), 0.0, 10.0)
    cube.keyframe_insert(data_path="location", frame=f)
cube.rigid_body.kinematic = False             # release
cube.rigid_body.keyframe_insert(data_path="kinematic", frame=11)
```

The body keeps the keyed speed: X went 0 to 9 over frames 1 to 10, then carried on (9.999, 10.996, 11.992, 12.986) while Z began to fall (10.0 to 6.6 by frame 30). The per frame step shrinks slowly after release (0.9973, 0.9957, 0.994), which fits the default `linear_damping`. Key at least a couple of frames of real motion before the release so there is a speed to inherit; a single still key before release is not tested.

## Scale, origin and gravity

Gravity is `scene.gravity`, default `(0.0, 0.0, -9.81)`. With `scene.use_gravity` on it drives rigid bodies, cloth and soft bodies, each scaled by its own `effector_weights.gravity`. `ClothSettings.gravity` and `SoftBodySettings.gravity` exist but the solvers do not read them (read in Blender 5.1 source, not run). Change `scene.gravity` for the shot, or one simulation's `effector_weights.gravity` for that one.

Physics assumes one Blender unit is one metre. A scene built at the wrong scale (one unit as a centimetre, so a person is 180 units tall) falls the same units per second squared as anything else, covers a tiny part of its own height per second, and reads as slow motion; too small reads as violent. Rescale the geometry to metres before simulating, or scale `scene.gravity` by the same factor (−981 on Z for centimetres). Unit Scale in the scene properties changes only displayed values and does not help.

Unapplied scale, tested on a cube scaled `(1, 1, 3)` resting on a passive floor (it should rest at Z 3.0):

| Shape | Unapplied scale | Applied scale |
|---|---|---|
| `BOX` | 3.0000 | 3.0000 |
| `CONVEX_HULL` | 2.9202, about 2.7 percent into the floor | 3.0001 |

Mass was 24.0 in every case. Apply scale before adding physics with mesh based shapes (`MESH`, `CONVEX_HULL`, `COMPOUND`): `bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)` with the object selected and active. It is not shown to matter for `BOX` or `SPHERE` on an unrotated object, but scale with rotation, constraints, and cloth or soft bodies (whose spring lengths come from local edge lengths) are untested reasons to apply it anyway; it costs nothing.

Reading `obj.dimensions` right after setting `obj.scale` through the data API returned the old size (`(2, 2, 2)` instead of `(2, 2, 6)`) until an operator ran. Do not trust `dimensions` or `matrix_world` straight after a bare transform write; call `frame_set()`, an operator, or a depsgraph update first.

## Origin and centre of mass

A primitive shape's centre of mass follows the object origin; set it with `bpy.ops.object.origin_set(type=..., center='MEDIAN')` (or `'BOUNDS'`). `type` is `GEOMETRY_ORIGIN`, `ORIGIN_GEOMETRY`, `ORIGIN_CURSOR`, `ORIGIN_CENTER_OF_MASS` or `ORIGIN_CENTER_OF_VOLUME`. `ORIGIN_CENTER_OF_MASS` is computed "from the surface area", like a hollow shell; `ORIGIN_CENTER_OF_VOLUME` "from the volume (must be manifold geometry with consistent normals)". For a solid prop of even density, use the volume option despite the names.
