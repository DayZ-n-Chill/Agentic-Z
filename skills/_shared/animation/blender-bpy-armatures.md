# Bones and pose spaces in bpy

How a script reads and sets bone poses in Blender: which matrix lives in which space, the three ways to set a pose, the space names, and how to choose rotation modes. Keyframes, Actions and cycles are in `blender-bpy-keyframes-and-actions.md`; IK, baking and context overrides in `blender-bpy-ik-and-baking.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the Blender 5.1 API reference and manual, so nothing here cites `P:\`. The DayZ side is in `blender-txa-export.md`. When a signature is in doubt, the Blender MCP server serves the reference and manual of the connected install (`get_python_api_docs`, `search_api_docs`, `search_manual_docs`).

## The matrices

| Property | Space | Access | What it is |
|---|---|---|---|
| `Bone.matrix_local` | Armature, rest | Read only | 4×4 rest matrix of the bone relative to the armature, not the parent. |
| `Bone.matrix` | Parent, rest | Read only | 3×3 rest orientation relative to the parent. Rarely needed. |
| `PoseBone.matrix_basis` | Local, relative to own rest and parent | Read and write | The composition of `location`, the rotation channel and `scale`: exactly what keyframes drive. |
| `PoseBone.matrix` | Armature object space, not world | Read and write | The final pose after constraints and drivers, relative to the armature object's origin. |
| `PoseBone.matrix_channel` | Armature | Read only | Channels and drivers plus the effect of bone constraints. Rarely needed. |

The reference says `matrix_basis` is "Alternative access to location/scale/rotation relative to the parent and own rest bone", and `matrix` is the "Final 4x4 matrix after constraints and drivers are applied, in the armature object space".

`matrix_basis` holds nothing hidden: setting `rotation_quaternion` to 30 degrees about Y reads back from `matrix_basis.to_quaternion()` as `[0.966, 0, 0.259, 0]`, the half angle quaternion of that turn.

## `matrix` is armature space, not world space

`PoseBone.matrix` differs from world space whenever the armature object is moved, parented or away from the origin, which is almost always. Reading it as world coordinates is the most common mistake in pose scripts. Convert on the armature object, not the bone, with `Object.convert_space(pose_bone=None, matrix=Matrix.Identity(4), from_space='WORLD', to_space='WORLD')`. The spaces are `WORLD`, `POSE`, `LOCAL_WITH_PARENT` and `LOCAL`; `POSE` is the space of `PoseBone.matrix`.

```python
# Bone to true world matrix
world_mat = arm_obj.convert_space(pose_bone=pb, matrix=pb.matrix,
                                  from_space='POSE', to_space='WORLD')
# World target to a local matrix for matrix_basis
local_mat = arm_obj.convert_space(pose_bone=pb, matrix=world_target,
                                  from_space='WORLD', to_space='LOCAL')
pb.matrix_basis = local_mat
```

## Three ways to set a pose

1. Ordinary posing: set `pose_bone.location`, `rotation_quaternion` (or `rotation_euler`) and `scale`, and Blender composes `matrix_basis`. Do not build `matrix_basis` by hand without a reason.
2. A target already in armature space (replaying a solve, matching another rig): assign `pose_bone.matrix`, converting from world space first, then call `bpy.context.view_layer.update()`. This is Blender's own idiom from the `PoseBone.bbone_segment_matrix` example. Assigning `matrix` solves `matrix_basis` from the parent and constraint state at that moment; it is not a live link, so a later change to a parent or constraint does not move the bone.
3. A whole body pose in one pass without a depsgraph update per bone: walk root to leaf and use `Bone.convert_local_to_pose`, which "uses custom rest and pose matrices provided by the caller" and needs no evaluation. Feed it the parent's pose matrix from your own walk.

The third pattern, from the `Bone.convert_local_to_pose` reference (`matrix_map` maps bone names to armature space matrices):

```python
def set_pose_matrices(obj, matrix_map):
    def rec(pbone, parent_matrix):
        if pbone.name in matrix_map:
            matrix = matrix_map[pbone.name]
            if pbone.parent:
                pbone.matrix_basis = pbone.bone.convert_local_to_pose(
                    matrix, pbone.bone.matrix_local,
                    parent_matrix=parent_matrix,
                    parent_matrix_local=pbone.parent.bone.matrix_local,
                    invert=True)
            else:
                pbone.matrix_basis = pbone.bone.convert_local_to_pose(
                    matrix, pbone.bone.matrix_local, invert=True)
        else:
            if pbone.parent:
                matrix = pbone.bone.convert_local_to_pose(
                    pbone.matrix_basis, pbone.bone.matrix_local,
                    parent_matrix=parent_matrix,
                    parent_matrix_local=pbone.parent.bone.matrix_local)
            else:
                matrix = pbone.bone.convert_local_to_pose(
                    pbone.matrix_basis, pbone.bone.matrix_local)
        for child in pbone.children:
            rec(child, matrix)
    for pbone in obj.pose.bones:
        if not pbone.parent:
            rec(pbone, None)
```

## Space names

The manual's space types (`manual/animation/constraints/interface/common.rst`), used everywhere Blender offers a space:

| Space | Relative to |
|---|---|
| World | The world axes. |
| Custom | Any object or bone; constraints only, not `convert_space`. |
| Pose (bones only) | The armature object. |
| Local | For a bone, its rest state after its ancestors transformed it; what the Properties editor shows in Pose Mode. |
| Local With Parent (bones only) | The rest state, including the change made by turning ancestor bones. |
| Local Space, Owner Orientation (bone targets only) | The target's local space turned to the owner's rest orientation, so a copy rotation gives the same armature space motion whatever each bone's rest. |

`Constraint.owner_space` and `target_space` take `WORLD`, `CUSTOM`, `POSE`, `LOCAL_WITH_PARENT` and `LOCAL`, plus `LOCAL_OWNER_ORIENT` on `target_space` only. `Object.convert_space` takes the four without `CUSTOM` and `LOCAL_OWNER_ORIENT`.

## Rotation modes

`PoseBone.rotation_mode` defaults to `QUATERNION`; the others are `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY`, `ZYX` and `AXIS_ANGLE`.

- Ball joints (shoulders, hips, spine): keep quaternions. No gimbal lock, but no single twist axis to polish by hand, and `Q` and `−Q` are the same rotation yet interpolate differently, which flips the bone between keys. `bpy.ops.pose.quaternions_flip()` fixes that afterwards; `mathutils.Quaternion.make_compatible(other)`, called against the previous key's quaternion before inserting, prevents it.
- Hinge joints with one main axis (elbows, knees, fingers): Euler, ordered so the least used axis is innermost. That gives one curve per axis for polishing, at the risk of gimbal lock when two axes line up 90 degrees apart, a real risk on shoulders.

Changing the rotation mode never converts existing keys. The operator `bpy.ops.pose.rotation_mode_set(type='XYZ')` converts the current pose value exactly (40 degrees about Y in, `[0, 40, 0]` out) but leaves the old `rotation_quaternion` F-curve in the Action and creates no `rotation_euler` curve until the next `keyframe_insert`. Assigning `pose_bone.rotation_mode = 'XYZ'` also converts the current value and touches no F-curve. So decide each bone's rotation mode before keying anything, and never change it on a keyed bone without keying it all again in the new mode.
