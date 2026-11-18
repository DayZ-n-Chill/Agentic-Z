# Cameras, constraints and parenting in bpy

How a script animates a camera in Blender (lens, focus, aim, paths, orbits), sets up constraints and parenting without the jump, and reads motion paths back for checking arcs. F-curves and easing are in `blender-bpy-fcurves.md`; materials, drivers and shape keys in `blender-bpy-materials-drivers.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the 4.3 and 5.1 API references, so nothing here cites `P:\`.

## Lens and focus are on the camera data

Optical properties live on the `Camera` datablock, `camera_object.data`, which has its own `animation_data`. Keying them on the camera object is a common mistake.

```python
cam_data = camera_object.data
cam_data.keyframe_insert(data_path="lens", frame=1)                # focal length in mm
cam_data.dof.use_dof = True
cam_data.keyframe_insert(data_path="dof.focus_distance", frame=1)  # nested, keyed from the Camera ID
cam_data.keyframe_insert(data_path="dof.aperture_fstop", frame=1)
```

`CameraDOFSettings` has `use_dof`, `focus_distance` (metres), `focus_object` (when set, focus follows that object), `focus_subtarget` (a bone name, with `focus_object`), `aperture_fstop` (default 2.8; lower blurs more), `aperture_blades` (0 to 16), `aperture_rotation` and `aperture_ratio` (anamorphic squeeze).

## Aiming: Track To or Damped Track

| | Track To | Damped Track |
|---|---|---|
| `track_axis` | `TRACK_X`, `_Y`, `_Z`, `TRACK_NEGATIVE_X`, `_Y`, `_Z`; `new()` sets `TRACK_NEGATIVE_Z` | Same values; `new()` sets `TRACK_Y` |
| `up_axis` | `UP_X`, `UP_Y`, `UP_Z`; `new()` sets `UP_Y` | None |
| `use_target_z` | Yes | No |
| Roll | Keeps the up axis toward world or target Z, so no surprise flips | Takes the shortest turn with no up reference; can roll as the target passes overhead, never gimbal locks |

The manual calls Track To "the preferred tracking constraint, as it has a more easily controlled constraining mechanism".

A Blender camera looks down its local −Z with +Y up. The static reference lists `TRACK_X` and `UP_X` as defaults, but `constraints.new()` runs an initialiser that, since 2.91, sets Track To to `TRACK_NEGATIVE_Z` and `UP_Y` and Damped Track to `TRACK_Y`. Set the axes yourself anyway; on Damped Track you must, since `TRACK_Y` aims the camera's +Y, not its view, at the target.

```python
con = cam_obj.constraints.new(type='TRACK_TO')
con.target = target_obj
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
```

## Moving along a path

`FollowPathConstraint` takes a curve object as `target`, `forward_axis` (`FORWARD_X`, `_Y`, `_Z`, `TRACK_NEGATIVE_X`, `_Y`, `_Z`; default `FORWARD_Y`), `up_axis` (default `UP_Z`), `use_curve_follow` (also turn with the curve), `use_curve_radius` (scale by the curve's point radius), `offset` (frames), `offset_factor` (default 0) and `use_fixed_location` (default `False`).

There are two ways to place the follower, checked on a straight 10 unit curve:

1. `use_fixed_location = True` and key `offset_factor`: 0 is the start, 1 the end, 0.5 exactly the middle, whatever the frame. One object, one set of keys; use this for scripted dollies.
2. `use_fixed_location = False`: the scene frame runs through the curve's `Curve.path_duration` (frames for one pass, default 100) plus the constraint's `offset`. For eased speed, or several followers on one timeline with different offsets, key `Curve.eval_time` ("Parametric position along the length of the curve") on the curve datablock instead.

`offset_factor` does nothing unless `use_fixed_location` is on. Parenting to a curve with `Curve.use_path` and `use_path_follow` works like the second way but has no per follower offset; prefer the constraint.

```python
con = cam_obj.constraints.new(type='FOLLOW_PATH')
con.target = path_curve_obj
con.use_fixed_location = True
con.forward_axis = 'FORWARD_Y'; con.up_axis = 'UP_Z'
con.offset_factor = 0.0
con.keyframe_insert(data_path="offset_factor", frame=1)
con.offset_factor = 1.0
con.keyframe_insert(data_path="offset_factor", frame=100)
```

## Orbit, dolly and crane rigs

Put an empty at the pivot and parent the camera to it, then key the empty's `rotation_euler.z` for an orbit, so the orbit is one clean channel apart from the camera's own moves. For constant speed, set both keys (0 and 2π) to `LINEAR` and add a Cycles modifier with `mode_after = 'REPEAT_OFFSET'`: each turn carries on from 2π forever. With Bézier keys the spin eases to a stop each turn. For dolly and crane moves, chain two empties, one for travel and a child for height, with the camera under the second, so each move is its own channel.

`bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1.0, location=(0, 0, 1))`; `type` takes `PLAIN_AXES`, `ARROWS`, `SINGLE_ARROW`, `CIRCLE`, `CUBE`, `SPHERE`, `CONE` and `IMAGE`. The reference shows a default `scale=(0.0, 0.0, 0.0)`; the empty still gets scale 1. `radius` sets the shown size (`Object.empty_display_size`; `radius=2.0` gives 2).

```python
bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.2, location=(0, 0, 1))
pivot = bpy.context.active_object
cam_obj.parent = pivot
cam_obj.matrix_parent_inverse = pivot.matrix_world.inverted()
pivot.rotation_euler.z = 0
pivot.keyframe_insert("rotation_euler", index=2, frame=1)
pivot.rotation_euler.z = 6.283185307
pivot.keyframe_insert("rotation_euler", index=2, frame=120)
spin = pivot.animation_data.action.fcurve_ensure_for_datablock(pivot, "rotation_euler", index=2)
for kp in spin.keyframe_points:
    kp.interpolation = 'LINEAR'
spin.modifiers.new(type='CYCLES').mode_after = 'REPEAT_OFFSET'
```

## Parenting without the jump

Assigning `.parent` in a script does not solve the parent inverse the way Ctrl P or `bpy.ops.object.parent_set()` does, so the child jumps:

```python
child.location = (1, 0, 0)
parent.location = (5, 5, 5)
child.parent = parent                                     # child now sits at (6, 5, 5)
child.matrix_parent_inverse = parent.matrix_world.inverted()   # back at (1, 0, 0)
```

`Object.matrix_parent_inverse` is the "Inverse of object's parent matrix at time of parenting"; plain assignment leaves it at identity for a new object.

## Constraints

`ObjectConstraints` has `new(type=)`, `remove(constraint)`, `clear()`, `move(from_index, to_index)` and `copy(constraint)`. The types used here are `TRACK_TO`, `DAMPED_TRACK`, `FOLLOW_PATH` and `CHILD_OF`.

Every constraint has `name`, `type`, `enabled`, `mute`, `influence`, `owner_space` (`WORLD`, `CUSTOM`, `POSE`, `LOCAL_WITH_PARENT`, `LOCAL`), `target_space` (the same plus `LOCAL_OWNER_ORIENT`), `space_object` and `space_subtarget` (for `CUSTOM`), `active`, `show_expanded`, `is_valid`, and the read only `error_location` and `error_rotation`, which show from script when a chain cannot be solved. `influence` reads 0 in the reference but `new()` sets it to 1; key it to fade a constraint in or out, for example handing a Track To back to keyed motion.

`ChildOfConstraint` has `target`, `subtarget`, `use_location_x` to `_z`, `use_rotation_x` to `_z`, `use_scale_x` to `_z`, `inverse_matrix` and `set_inverse_pending`. On 5.1, `inverse_matrix` is identity right after `new()` (not the zero matrix the 4.3 page lists), and assigning `target` sets it to `target.matrix_world.inverted()`, so the child did not jump. That is not checked on 4.3 or after the target has moved, so do not rely on it. Call the Set Inverse operator after every target assignment:

```python
bpy.context.view_layer.objects.active = child
child.select_set(True)
bpy.ops.constraint.childof_set_inverse(constraint=con.name, owner='OBJECT')   # owner 'OBJECT' or 'BONE'
# bpy.ops.constraint.childof_clear_inverse(constraint=con.name, owner='OBJECT') undoes it
```

## Reading motion paths back

Motion paths give world positions per frame without a viewport, so arcs and overshoot can be checked in Python:

```python
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE')   # on selected objects
mp = obj.motion_path                          # None until calculated
mp.frame_start, mp.frame_end, mp.length
positions = [p.co.copy() for p in mp.points]  # world space
bpy.ops.object.paths_update()                 # after changing the animation
bpy.ops.object.paths_clear()                  # motion_path is None again
```

On an object keyed at frames 1, 25 and 50, `points[0]`, `points[24]` and `points[-1]` match the three keyed positions exactly. `bpy.ops.pose.paths_calculate(...)` does the same for bones, filling `PoseBone.motion_path`. Curvature or distance from the chord can then be computed on the list.
