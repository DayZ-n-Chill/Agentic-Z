# F-curves, keys and easing in bpy

How Blender stores animation as F-curves on an Action, how slots changed that in 4.4, and how a script sets interpolation, easing and handles on keys. F-curve modifiers are in `blender-bpy-fcurve-modifiers.md`; cameras and constraints in `blender-bpy-objects-camera.md`; materials, drivers and shape keys in `blender-bpy-materials-drivers.md`; armature keying in `blender-bpy-keyframes-and-actions.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the 4.3 and 5.1 API references, so nothing here cites `P:\`. The DayZ side is in `blender-txa-export.md`.

## Where animation lives

Every ID (object, material, node tree, shape key block, camera data, curve data) has its own `animation_data`:

| `AnimData` member | Holds |
|---|---|
| `action` | The active Action. |
| `action_slot` | The slot that Action uses for this ID (4.4 and later). |
| `drivers` | Driver F-curves, a collection separate from any Action; slots do not affect drivers. |
| `nla_tracks` | NLA tracks. |
| `action_blend_type`, `action_extrapolation`, `action_influence` | How the active Action blends in the NLA. |

`ID.animation_data_create()` makes it ("not all ID types support this") and `animation_data_clear()` removes it. `keyframe_insert` and `driver_add` create it themselves, so call it only when building an Action before anything is keyed.

An F-curve animates one number. Keying `obj.location` with the default `index=-1` makes three F-curves, all with `data_path="location"` and `array_index` 0, 1 and 2. The pair of path and index is the curve's key, which is why lookups take both.

| `FCurve` member | Meaning |
|---|---|
| `data_path` | RNA path to the property, relative to the owning ID. |
| `array_index` | Which component (0 for X, 1 for Y, 2 for Z on a vector). |
| `keyframe_points` | The keys. |
| `modifiers` | The F-curve modifiers. |
| `extrapolation` | `CONSTANT` (default) or `LINEAR`. |
| `group` | Its Action group, or none. |
| `driver` | Set only on a driver curve. |

Its methods: `evaluate(frame)`, `update()` ("Ensure keyframes are sorted in chronological order and handles are set correctly"), `range()`, `convert_to_samples(start, end)`, `convert_to_keyframes(start, end)` and `bake(start, end, *, step=1.0, remove='NONE')` (`remove` also takes `IN_RANGE`, `OUT_RANGE`, `ALL`).

## Slots since 4.4

An Action can now animate several datablocks, so its F-curves sit under a slot per datablock, then a layer, then a keyframe strip, then a channelbag. In 5.1 only one layer with one endless strip is usable; the layering exists in the data but is not yet a working feature, so do not design a rig around blending layers inside one Action.

| Blender | `action.fcurves` | Use instead |
|---|---|---|
| 4.3 and earlier | The only API | |
| 4.4 and 4.5 | A deprecated proxy for the first slot's channelbag | `action.layers[0].strips[0].channelbag(slot, ensure=True).fcurves` |
| 5.0 and later | Removed; `hasattr(action, "fcurves")` is `False` | `action.fcurve_ensure_for_datablock(datablock, data_path, index=0, group_name='')`, or `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot)` and `action_ensure_channelbag_for_slot(action, slot)` |

`obj.keyframe_insert(...)` and `driver_add(...)` are called the same way on every version and create everything they need. Only code that reaches into `action.fcurves`, `action.groups` or `action.id_root` breaks.

```python
obj.keyframe_insert("location", frame=1)
action = obj.animation_data.action
slot = obj.animation_data.action_slot
slot.identifier        # "OBTempObj": two letter ID type, then the name
slot.target_id_type    # "OBJECT"
channelbag = action.layers[0].strips[0].channelbag(slot)
[(fc.data_path, fc.array_index) for fc in channelbag.fcurves]
# [("location", 0), ("location", 1), ("location", 2)]
```

Building a slot, layer and strip by hand is only needed to share one Action across objects or to build it before keying:

```python
action = bpy.data.actions.new("SuzanneAction")
slot = action.slots.new(id_type='OBJECT', name="Suzanne")   # identifier "OBSuzanne"
layer = action.layers.new("Layer")
strip = layer.strips.new(type='KEYFRAME')
channelbag = strip.channelbag(slot, ensure=True)
fcurve = channelbag.fcurves.new("location", index=1, group_name="Object Transform")
anim_data = suzanne.animation_data_create()
anim_data.action = action
anim_data.action_slot = anim_data.action_suitable_slots[0]
```

`group_name=` on `fcurves.new` exists from 5.0; on 4.4 and 4.5 it takes no group. Since 4.4, `animation_data.action = some_action` may not pick a slot, leaving the ID still and raising no error; set `anim_data.action_slot = anim_data.action_suitable_slots[0]` after assigning the Action. NLA strips and Action constraints pick a slot more readily.

`ActionSlot` has `identifier`, `name_display` (the part after the prefix), `target_id_type` (settable once while `UNSPECIFIED`), `handle` (the internal number for its channelbag), `active`, `select` and `show_expanded`.

## Inserting and deleting keys

`keyframe_insert`, `keyframe_delete`, `driver_add` and `driver_remove` are defined on `bpy_struct`, so they work on objects, pose bones, node sockets and shape keys alike:

```python
keyframe_insert(data_path, index=-1, frame=bpy.context.scene.frame_current, group='', options=set(), keytype='KEYFRAME') -> bool
keyframe_delete(data_path, index=-1, frame=bpy.context.scene.frame_current, group='') -> bool
driver_add(path, index=-1) -> FCurve | list[FCurve]
driver_remove(path, index=-1) -> bool
```

- `index=-1` covers every component: `driver_add("location")` returns a list of three curves, `driver_add("location", 1)` one.
- The options and key types are in `blender-bpy-keyframes-and-actions.md`, "Inserting keys". `INSERTKEY_XYZ_TO_RGB` was already unused in 4.3 and is removed in 5.0; passing it on 5.0 raises `TypeError`, because Blender checks every flag in the set.
- Both return a bool, not the key. To get the `Keyframe`, use `fcurve.keyframe_points.insert(...)`.
- The 5.1 reference shows `index` as keyword only, the 4.3 one does not. Whatever the cause, always pass `index=` and `frame=` as keywords.

A custom Python `PropertyGroup` nested under a non-ID struct (a `PointerProperty` added to `bpy.types.Bone`) must be keyed from the owning ID with the full path: `arm.keyframe_insert(data_path='bones["Bone"].my_prop.nested', frame=1)`. Built in nested structs (pose bone, node socket, shape key) can be keyed directly: `node.inputs["Base Color"].keyframe_insert("default_value", frame=1)`.

`hide_viewport` and `hide_render` can be keyed. `hide_get()` and `hide_set()`, the Outliner eye per view layer, are methods: keying them raises `TypeError: property "hide_get()" not found`, so that toggle cannot be animated. Give visibility keys `CONSTANT` interpolation so no frame is half hidden.

## The key and its easing

| `Keyframe` member | Meaning |
|---|---|
| `co`, `co_ui` | `(frame, value)`. `co_ui` also moves the handles as the Graph Editor would; raw `co` leaves them to you. |
| `handle_left`, `handle_right` | Absolute positions, not offsets. |
| `handle_left_type`, `handle_right_type` | `FREE` (default), `ALIGNED`, `VECTOR`, `AUTO`, `AUTO_CLAMPED`. |
| `interpolation` | `CONSTANT`, `LINEAR`, `BEZIER`; easing by strength `SINE`, `QUAD`, `CUBIC`, `QUART`, `QUINT`, `EXPO`, `CIRC`; dynamic `BACK`, `BOUNCE`, `ELASTIC`. |
| `easing` | `AUTO` (default: ease in for the strength types, ease out for the dynamic ones), `EASE_IN`, `EASE_OUT`, `EASE_IN_OUT`. |
| `back` | Overshoot amount, `BACK` only. |
| `amplitude`, `period` | Bounce boost and time between bounces, `ELASTIC` only. |
| `type` | The key type; a marker only, it does not change evaluation. |
| `select_control_point`, `select_left_handle`, `select_right_handle` | Selection. |

Set the handle type when Blender should place the handles: `AUTO` or `AUTO_CLAMPED` for smooth curves, `VECTOR` for a hard corner, `ALIGNED` for one straight line through the key. Write `handle_left` and `handle_right` only for a specific tangent, and only on `FREE` or `ALIGNED` handles; the other types recompute the position and ignore what you wrote.

Call `fcurve.update()` after any change to `co` or a handle. A key moved out of time order without it, or without `keyframe_points.sort()`, evaluates wrongly.

```python
fcurve = action.fcurve_ensure_for_datablock(obj, "location", index=2)
kf = fcurve.keyframe_points.insert(20, 5.0, keyframe_type='BREAKDOWN')
kf.interpolation = 'BACK'
kf.easing = 'EASE_OUT'
kf.back = 1.5
fcurve.update()
```

## Editing keys in bulk

```python
fcurve.keyframe_points.insert(frame, value, options={'REPLACE'}, keyframe_type='KEYFRAME')  # also 'NEEDED', 'FAST'
fcurve.keyframe_points.add(count)          # blank points at (0, 0), the fast bulk path
fcurve.keyframe_points.remove(keyframe, fast=False)
fcurve.keyframe_points.clear()
fcurve.keyframe_points.sort()
```

`insert` returns the `Keyframe`, so you can set its interpolation and handles at once. For many generated keys, `add(count)` then set each `co`, then `sort()` or `update()` once.

`bpy.ops.action.*` and `bpy.ops.graph.*` need a Dope Sheet or Graph Editor and fail from a script. Delete with `keyframe_points.remove(kf)`, move by setting `kf.co.x` then `fcurve.update()`.
