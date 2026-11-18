# IK, baking and context in bpy

How a script sets up IK in Blender, bakes constrained motion down to keys, and runs operators that need a context, plus the traps that make a correct looking script produce wrong animation. Bones and pose spaces are in `blender-bpy-armatures.md`; keys and Actions in `blender-bpy-keyframes-and-actions.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the Blender 5.1 API reference and manual, so nothing here cites `P:\`.

## IK constraints

Create IK with the data API; it needs no context or selection: `pose_bone.constraints.new(type='IK')` returns a `KinematicConstraint`. The operator `bpy.ops.pose.ik_add(with_targets=True)` does the same from the UI.

| Field | Meaning |
|---|---|
| `chain_count` | "How many bones are included in the IK effect - 0 uses all bones". 2 on the end bone gives a two bone arm or leg. |
| `target`, `subtarget` | The goal object, and a bone on it (or a vertex group on a mesh); `""` for a plain object such as an empty. |
| `pole_target`, `pole_subtarget`, `pole_angle` | The pole; the angle in radians, ±π. |
| `iterations` | 0 to 10000. |
| `use_stretch`, `use_tail`, `use_location`, `use_rotation` | Stretch; include the bone's tail; follow the target's position and rotation. |
| `ik_type` | `COPY_POSE` (the normal chain to target) or `DISTANCE` (stay within, outside or on a sphere, with `distance` and `limit_mode`). |

Per axis IK locks, stiffness and limits (`lock_ik_x`, `ik_stiffness_x`, `ik_min_x` and so on) live on `PoseBone`, not the constraint.

```python
ik = arm_obj.pose.bones["Hand.L"].constraints.new(type='IK')
ik.target = target_empty
ik.subtarget = ""            # "" when the target is an object, not another armature's bone
ik.chain_count = 2           # hand and forearm; 0 is the whole chain
ik.pole_target = pole_empty
ik.pole_angle = math.radians(-90)
ik.use_stretch = False
```

Animate the target, not the chain. Once IK drives a chain, its bones' own rotation channels mean nothing; key the target empty or bone. To move the result onto the bones' channels (to drop the constraint or export FK only), bake it with visual keying.

IK and FK switching is a rigging pattern, not an API: an IK chain and an FK chain drive one deform chain through Copy Rotation or Copy Transforms constraints whose `influence` follows one 0 to 1 blend property. A script matches one chain to the other's solved pose (`Pose.apply_pose_from_action`, or reading and converting `matrix`), then keys the blend property and the constraints' `influence`. Legs are usually IK, since feet need a steady world target; arms are usually FK, with IK for hands planted on something.

## Baking

Two entry points, not interchangeable.

The operator, when a normal selection and mode are already set:

```python
bpy.ops.nla.bake(frame_start=1, frame_end=250, step=1, only_selected=True, visual_keying=False,
                 clear_constraints=False, clear_parents=False, use_current_action=False,
                 clean_curves=False, bake_types={'POSE'},
                 channel_types={'BBONE', 'LOCATION', 'PROPS', 'ROTATION', 'SCALE'})
```

- `visual_keying=True` bakes the final constrained transform, which is what an IK chain down to FK needs.
- `clear_constraints=True` removes the constraints afterwards; the reference warns "To get a correct bake with this setting Visual Keying should be enabled". Without it the bake freezes the pose from before the constraints.
- `use_current_action=True` bakes into the existing Action, needed when baking some bones of an armature whose other bones are animated.
- `bake_types` takes `POSE`, `OBJECT` or both.

The function `bpy_extras.anim_utils.bake_action(obj, *, action, frames, bake_options)` needs no active object, selection or mode, so it suits a script far better:

```python
from bpy_extras import anim_utils
opts = anim_utils.BakeOptions(
    only_selected=False, do_pose=True, do_object=False,
    do_visual_keying=True, do_constraint_clear=False, do_parents_clear=False,
    do_clean=True, do_location=True, do_rotation=True, do_scale=True,
    do_bbone=False, do_custom_props=False,
)
baked = anim_utils.bake_action(arm_obj, action=None, frames=range(1, 25), bake_options=opts)
```

`BakeOptions` is a dataclass with 12 fields and no defaults, so `BakeOptions()` raises `TypeError: missing 12 required positional arguments`; pass every field every time. `action=None` bakes into a new Action. `frames` takes any iterable of integers, sparse lists included, which the operator cannot. `bake_action_objects(object_action_pairs, *, frames, bake_options)`, `bake_action_iter(obj, *, action, bake_options)` and `bake_action_objects_iter(object_action_pairs, bake_options)` bake several objects or yield per frame, for progress reporting.

## Operators and context

Most `bpy.ops` calls (`pose.breakdown`, `pose.paste`, `nla.action_pushdown`, `object.mode_set`) read the active object, mode, selection and area through `poll()`, and from a script fail with `RuntimeError: Operator bpy.ops.X.Y poll() failed, context is incorrect`.

`bpy.context.temp_override(*, window=None, screen=None, area=None, region=None, **keywords)` patches any context member inside a `with` block and restores it afterwards, even on an exception:

```python
with bpy.context.temp_override(window=window):
    bpy.ops.object.mode_set(mode='EDIT')

with bpy.context.temp_override(selected_objects=[scene.camera]):
    bpy.ops.object.delete()
```

`override.logging_set(True, hide_missing=True)` inside the block prints every member the operator reads, the quickest way to find what a failing operator wants. Prefer `temp_override(active_object=..., selected_objects=..., selected_pose_bones=...)` to setting `view_layer.objects.active` and `select_set` and restoring them by hand.

Mode cannot be overridden. `context.mode` comes from `active_object.mode`, so there is no `temp_override(mode='POSE')`. `bpy.ops.object.mode_set(mode='POSE')` really changes the object's mode, even inside an override; switch back to Object Mode and restore the active object and selection afterwards.

```python
with bpy.context.temp_override(active_object=arm_obj, selected_objects=[arm_obj]):
    bpy.ops.object.mode_set(mode='POSE')
```

Done better without operators: constraints (`constraints.new`), Actions and NLA (`bpy.data.actions.new`, `nla_tracks.new`, `strips.new`), keys (`keyframe_insert`, `keyframe_points.insert`), baking (`anim_utils.bake_action`) and pose maths (`matrix`, `matrix_basis`, `convert_local_to_pose`, `convert_space`). Operators stay the only route for breakdown, push and relax, mirroring through the pose clipboard, and changing mode.

## Traps, most likely first

1. `PoseBone.matrix` is armature space. It looks right until the armature moves away from the origin; convert with `Object.convert_space(..., from_space='POSE', to_space='WORLD')`.
2. Changing `rotation_mode` converts the current value but no keys, so the bone is wrong at every other key (`blender-bpy-armatures.md`, "Rotation modes").
3. `Action.fcurves` is gone from 5.0; use `keyframe_insert` or test for `fcurve_ensure_for_datablock`.
4. Bone curves live on the object's Action with paths like `pose.bones["Name"].prop`; a hand built path is relative to the armature object.
5. Leaving out visual keying keys the raw channel under a constraint, not the motion on screen, and `clear_constraints=True` without it gives a bake that does not match.
6. Autokey depends on the user's setting and modes; key explicitly.
7. An opaque `poll() failed` is rarely fixed by overriding every member you can think of; log what the operator reads, and check whether the data API does the job.
8. `keyframe_points.insert()` ignores the user's preferences for new keys and, with `FAST`, skips handle recalculation.
9. An Action with no fake user and no strip vanishes on reload, not at once.
10. `BakeOptions` has no defaults.
