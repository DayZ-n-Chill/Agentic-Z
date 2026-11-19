# Keyframes, Actions and cycles in bpy

How a script inserts keys, organises them in Actions and the NLA, and loops a cycle in Blender, and how Blender's key types map onto blocking, breakdowns and polish. Bones and pose spaces are in `blender-bpy-armatures.md`; IK, baking and context overrides in `blender-bpy-ik-and-baking.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the Blender 5.1 API reference and manual, so nothing here cites `P:\`. Facts marked 4.3 come from the 4.3 reference or the 4.4 migration notes, not a 4.3 install.

## Key types match the animator's passes

Blender's key types are an enum, not an analogy (`manual/animation/keyframes/introduction.rst`, "Keyframe Types"). `keyframe_insert(..., keytype=...)` and `Keyframe.type` take the same values:

| Key type | Manual's meaning | Use |
|---|---|---|
| `KEYFRAME` | Normal key | Default. |
| `BREAKDOWN` | "Breakdown state, e.g. for transitions between key poses" | In-betweens. |
| `MOVING_HOLD` | "adds a small amount of motion around a holding pose" | Drift on holds. |
| `EXTREME` | "An 'extreme' state, or some other purpose as needed" | Contact and extreme poses while blocking. |
| `JITTER` | "filler or baked keyframe for keying on ones" | Baked keys. |
| `GENERATED` | Made by a tool, safe to remove or regenerate | Tool output. |

- Blocking: key only the extreme and contact poses, far apart, with `Keyframe.interpolation = 'CONSTANT'` so each pose holds until the next. The interpolation values are `CONSTANT`, `LINEAR`, `BEZIER`, `SINE`, `QUAD`, `CUBIC`, `QUART`, `QUINT`, `EXPO`, `CIRC`, `BACK`, `BOUNCE` and `ELASTIC`.
- Breakdowns: a breakdown leans toward the extreme it belongs to, not the midpoint. `bpy.ops.pose.breakdown(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FREE')` makes one on the current frame; `push`, `relax`, `blend_to_neighbor` and `blend_with_rest` take the same arguments (`channels` one of `ALL`, `LOC`, `ROT`, `SIZE`, `BBONE`, `CUSTOM`; `axis_lock` one of `FREE`, `X`, `Y`, `Z`). They need a Pose Mode context; `Pose.apply_pose_from_action` and `Pose.blend_pose_from_action` give the same blend without one. Tag the key `BREAKDOWN`.
- Splining: set `kf.interpolation = 'BEZIER'` and pick handle types (`FREE`, `ALIGNED`, `VECTOR`, `AUTO`, `AUTO_CLAMPED`). `AUTO_CLAMPED` stops the bumps automatic tangents make on curves that change direction.
- Polish: nudge handles, add `MOVING_HOLD` keys, and stagger body parts (arms and head behind the hips) by moving single `Keyframe.co` values per F-curve, not whole poses.

## Inserting keys

`keyframe_insert(data_path, *, index=-1, frame=bpy.context.scene.frame_current, group="", options=set(), keytype='KEYFRAME')` is on every struct, `PoseBone` and `Object` included.

| Argument | Meaning |
|---|---|
| `data_path` | `"rotation_quaternion"` called on the pose bone, or `'pose.bones["Bone1"].rotation_quaternion'` on the object. |
| `index` | −1 keys every component; a number keys one channel. |
| `frame` | Pass it to key any frame without moving the playhead; the current frame is only the default. |
| `group` | F-curve group name, for display. |
| `options` | `INSERTKEY_NEEDED` (only where the value changes), `INSERTKEY_VISUAL` (key the constraint evaluated transform), `INSERTKEY_REPLACE` (only overwrite), `INSERTKEY_AVAILABLE` (only curves that exist), `INSERTKEY_CYCLE_AWARE` (respect cyclic extrapolation). |
| `keytype` | One of the key types above. |

Bones are never keyed on their own. The reference says nested properties "must be done from the ID subclass, in this case the Armature rather than the bone". `pose_bone.keyframe_insert("rotation_quaternion", frame=1)` works because the pose bone finds its owner, and the curve it makes reads `pose.bones["Bone1"].rotation_quaternion` on the object's Action. Any `data_path` built by hand for `driver_add`, `keyframe_delete` or `fcurve_ensure_for_datablock` is relative to the armature object.

```python
pose_bone.rotation_mode = 'QUATERNION'
pose_bone.rotation_quaternion = target_quat
pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=37,
                          group=bone_name, keytype='BREAKDOWN',
                          options={'INSERTKEY_NEEDED'})
```

`FCurve.keyframe_points.insert(frame, value, *, options=set(), keyframe_type='KEYFRAME')` inserts one value on a curve you already hold, skipping the path lookup across hundreds of keys. Its options differ: `REPLACE`, `NEEDED` and `FAST`. With `FAST` it skips sorting and handle recalculation, so call `fcurve.update()` (or `sort()`, `deduplicate()`, `handles_recalc()`) once after the last insert. It also ignores the user's preferences for new keys: every key is `BEZIER` with auto clamped handles, except on integer, boolean or enum curves, which get constant keys. `keyframe_insert` uses the preferences. Set `kf.interpolation` yourself when a script must match the UI (read from Blender's source, not run).

Keying sets (`Scene.keying_sets`, `keying_sets_all`) key many paths in one call. The built in Whole Character set is "made to keyframe all properties that are likely to get animated in a character rig" and skips bones with prefixes reserved for technical bones. `bpy.ops.anim.keyframe_insert(type='DEFAULT')` uses the active set; `bpy.ops.anim.keying_set_active_set(type=...)` switches it. Explicit per bone calls do not depend on scene state, so prefer them.

Never rely on autokey (`ToolSettings.use_keyframe_insert_auto`): it depends on the user's setting, changes what it keys with `auto_keying_mode` (`REPLACE_KEYS` touches only existing curves), and a data API script often never triggers it. To copy autokey on purpose, locked channels included, call `bpy_extras.anim_utils.AutoKeying.key_transformation(context, target)`; the class also has `options(...)` and `keyframe_channels(...)`.

## Actions since 4.4

4.4 made Actions layered, with slots. The path is `Action.layers`, then `strips` (an `ActionKeyframeStrip`), then `channelbags` keyed by slot, then `fcurves`. A slot (`ActionSlot`) says which datablock a set of channels belongs to, so one Action can drive several objects; every animated ID has `AnimData.action_slot` next to `AnimData.action`.

| Version | `Action.fcurves` |
|---|---|
| 4.3 and earlier | A flat collection: `action.fcurves.new(data_path, index=0, action_group="")` and `.find(data_path, index)`. |
| 4.4 | Kept as a deprecated legacy accessor. |
| 5.0 and later | Gone: `hasattr(bpy.data.actions.new("x"), "fcurves")` is `False`, and 4.3 code raises `AttributeError`. |

Never touch `action.fcurves`; `obj.keyframe_insert(...)` works on every version and creates the animation data, Action, slot, layer, strip and channelbag as needed. After one call `action.is_action_legacy` is `False`, there is one slot and one layer, and the slot's `identifier` is `"OB"` plus the object name. For a specific curve on 4.4 and later, `action.fcurve_ensure_for_datablock(datablock, data_path, index=0, group_name="")` "will also create the layer, keyframe strip, and action slot if necessary". Guard it by feature, not version number:

```python
if hasattr(action, "fcurve_ensure_for_datablock"):
    fcurve = action.fcurve_ensure_for_datablock(obj, "location", index=0)
else:
    fcurve = action.fcurves.find("location", index=0) or action.fcurves.new("location", index=0)
```

Create and assign an Action, pinned so it survives a reload:

```python
action = bpy.data.actions.new("WalkCycle")
action.use_fake_user = True
obj.animation_data_create()
obj.animation_data.action = action
obj.keyframe_insert(data_path="location", frame=1)
```

An Action with no users disappears on the next save and reload, not at once: after `nla.action_pushdown`, `nla.tweakmode_exit` or unassigning `AnimData.action`, an Action no strip uses is gone when the file reopens, though every check in the session passed. Set `use_fake_user = True` right after creating any Action meant to last. `bpy.ops.anim.clear_useless_actions(only_unused=True)` does the opposite and drops Actions with no curves.

## The NLA

Tracks and strips need no operator:

```python
track = obj.animation_data.nla_tracks.new()
strip = track.strips.new("WalkCycleStrip", start, action)
```

`strip.frame_end` comes from the Action's range. The fields for layering are `blend_type` (`REPLACE`, `COMBINE`, `ADD`, `SUBTRACT`, `MULTIPLY`), `influence` (0 to 1), `extrapolation` (`NOTHING`, `HOLD`, `HOLD_FORWARD`), `action_frame_start` and `action_frame_end`, `repeat`, `scale`, `use_reverse` and `mute`. `bpy.ops.nla.action_pushdown(track_index=-1)` pushes the active Action down as a strip. Tweak mode is `bpy.ops.nla.tweakmode_enter(isolate_action=False, use_upper_stack_evaluation=False)` and `tweakmode_exit(isolate_action=False)`; `AnimData.use_tweak_mode` mirrors it, and `AnimData.action_tweak_storage` holds the Action active before it.

## Cycles

A walk step breaks into contact, down, passing and up, then contact on the other foot. At 24 fps a walk is often a 24 frame cycle (two steps a second) with contacts at 0, 12 and 24 and the other poses about 3 frames apart; a run is often 8 to 16 frames and can drop the double contact. Treat these as starting ratios and retime against reference.

Mirroring:

- `bpy.ops.pose.copy()` then `bpy.ops.pose.paste(flipped=True, selected_mask=False)` pastes the stored pose flipped.
- `bpy.ops.pose.select_mirror(only_active=False, extend=False)` selects the mirror bones by their `.L` and `.R` or `_L` and `_R` names without posing.
- `bpy.ops.pose.flip_names(do_strip_numbers=False)` flips name suffixes only.
- `Action.flip_with_pose(object)` flips a whole Action about X using the armature as reference, for example to make a left lead walk from a right lead one.

Looping uses two separate settings:

1. On the Action, `use_frame_range = True` with `frame_start` and `frame_end` marks the intended range, and `use_cyclic = True` marks it as a cycle. That alone loops nothing; tools and exporters read it, and it feeds `INSERTKEY_CYCLE_AWARE`.
2. On the NLA strip, `repeat` (0.1 to 1000, default 1.0) repeats the Action inside the strip. A 12 frame Action on frames 1 to 13 with `repeat = 4.0` moves `frame_end` from 13 to 49. `extrapolation` decides what happens past the strip.

```python
action.use_frame_range = True
action.frame_start, action.frame_end = 1, 13
action.use_cyclic = True
track = obj.animation_data.nla_tracks.new()
strip = track.strips.new("WalkCycleStrip", 1, action)
strip.repeat = 4.0            # frame_end becomes 1 + (13 - 1) * 4 = 49
strip.extrapolation = 'HOLD'
```

For a walk, key one 12 to 24 frame loop with `use_cyclic`, push it to a strip, and set distance and speed with `strip.repeat` or `strip.scale` ("Scaling factor for action", 0.0001 to 1000) instead of keying again.
