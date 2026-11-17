# Object, camera, material and driver animation in Blender (bpy)

The F-curve data model, keyframes and easing, F-curve modifiers, camera rigs, constraints, material and shape key animation, and drivers, for animation written as `bpy` code and run over the Blender MCP server.

Scope: authoring object/camera/material/driver animation entirely through `bpy` code executed
over the MCP bridge (`execute_blender_code`), no UI interaction available. Blender 4.3 is the
baseline; breaking changes in 4.4/4.5/5.0/5.1 are flagged explicitly wherever found.

Everything here is Blender behaviour. None of it is a fact about the DayZ game, so nothing in
this file cites `P:\`; the DayZ side of the work is in `dayz-handoff.md`.

## Status tags

- **[LIVE]** marks a fact that was run in Blender 5.1.1 through `execute_blender_code`; the
  result shown is what Blender returned.
- **[4.3]** marks a fact that matches the Blender 4.3 Python API reference and was not re-run
  in a 4.3 build.
- Facts with no tag are the same across the whole 4.3→5.1 range.
- **The single biggest cross-version change is Action Slots** (introduced 4.4, legacy
  `Action.fcurves`/`.groups`/`.id_root` proxy removed entirely in 5.0). Covered in full under
  F-curve object model. **[LIVE]** on 5.1.1: `hasattr(action, "fcurves")` is `False`.
- Three **version-specific facts that the 4.3 API reference does not show** (found through
  `bl_rna` introspection on 5.1.1):
  1. F-Curve **Noise modifier was reworked in Blender 4.4** — new `lacunarity`/`roughness`
     properties, old algorithm preserved via `use_legacy_noise` (defaults `True` on old files,
     `False` on new modifiers).
  2. A brand new F-Curve modifier, **`FModifierSmooth` ("Gaussian Smooth"), was added in
     Blender 5.1** and does not exist in 4.3 at all.
  3. `ShaderNodeMix.data_type` lists `ROTATION` as a valid `bl_rna` enum identifier, but
     **[LIVE]** attempting `mix.data_type = 'ROTATION'` inside a *shader* node tree raises
     `TypeError: enum "ROTATION" not found in ('FLOAT', 'VECTOR', 'RGBA')` — rotation mixing
     only works when the same underlying "Mix" node lives in a Geometry Nodes tree.

---

## F-curve object model

Blender's animation data model, from the outside in (all classes `bpy.types.*`):

```
ID (Object, Material, NodeTree, Key/"shape keys", Camera-data, Curve-data, ...)
└─ animation_data : AnimData                       # every ID has its OWN AnimData slot
   ├─ action : Action                               # the "active" action
   ├─ action_slot : ActionSlot                       # 4.4+ only, see Action Slots below
   ├─ drivers : bpy_prop_collection of FCurve         # driver f-curves — separate from Action entirely
   └─ nla_tracks : bpy_prop_collection of NlaTrack

Action (ID)
├─ 4.3 and earlier: fcurves / groups directly on the Action (removed in 5.0, see below)
└─ 4.4+: layers[ActionLayer] → strips[ActionStrip, type='KEYFRAME'] → channelbag(slot) → fcurves/groups
   └─ slots[ActionSlot]                              # which data-block(s) this Action's channels belong to

FCurve (one per animated scalar channel)
├─ data_path: str        — RNA path to the property, relative to the owning ID
├─ array_index: int       — which component of an array property (0=X,1=Y,2=Z for a Vector, etc.)
├─ keyframe_points: FCurveKeyframePoints[Keyframe]
├─ modifiers: FCurveModifiers[FModifier]
├─ extrapolation: 'CONSTANT' | 'LINEAR'
├─ group: ActionGroup | None
└─ driver: Driver | None  — populated only when this FCurve is a driver-curve, not a keyframe-curve
```

**The `data_path` + `array_index` model, concretely**: keying `obj.location` (a 3-float Vector)
with `index=-1` (default) creates **three separate `FCurve` objects**, all with
`data_path="location"`, and `array_index` 0, 1, 2 respectively — not one FCurve holding a vector.
Keying `index=1` alone creates/updates only the Y-channel FCurve. This is why
`action.fcurves.find("location", index=1)` (4.3) takes both a path and an index — the pair is the
real key, not the path alone.
`bpy.types.FCurve` [4.3, cross-checked
current — identical]:

> `array_index` — Index to the specific property affected by F-Curve if applicable (int, default 0)
> `data_path` — RNA Path to property affected by F-Curve (string)
> `keyframe_points` — User-editable keyframes (`FCurveKeyframePoints` of `Keyframe`, readonly)
> `modifiers` — Modifiers affecting the shape of the F-Curve (`FCurveModifiers` of `FModifier`, readonly)
> `extrapolation` — enum `['CONSTANT', 'LINEAR']`, default `'CONSTANT'`
> `driver` — Channel Driver (only set for Driver F-Curves), readonly

FCurve methods, same page: `evaluate(frame) -> float`, `update()` — "Ensure keyframes are sorted
in chronological order and handles are set correctly" (call after any manual `.co`/handle edits),
`range() -> Vector` (min/max time extents), `convert_to_samples(start, end)`,
`convert_to_keyframes(start, end)`, `bake(start, end, *, step=1.0, remove='NONE'|'IN_RANGE'|'OUT_RANGE'|'ALL')`.

**AnimData** — `bpy.types.AnimData` [4.3]:
`action` (Action), `action_blend_type`/`action_extrapolation`/`action_influence` (NLA blending of
the active action), `drivers` (`AnimDataDrivers` of `FCurve` — **verified this is a completely
separate collection from anything inside Action; Action Slots do not affect drivers at all**),
`nla_tracks`. 4.4+ adds `action_slot` / `action_suitable_slots` / `last_slot_identifier` (see below).

**Creating/clearing AnimData** — `bpy.types.ID`
[4.3]: `animation_data_create() -> AnimData` ("note that not all ID types support this"),
`animation_data_clear()`. `keyframe_insert`/`driver_add` auto-call the equivalent of
`animation_data_create()` internally — you rarely need to call it yourself except when building
an Action from scratch before any property has been keyed.

### Action Slots (introduced 4.4) — the load-bearing cross-version fact

Introduced in Blender 4.4; the legacy API was removed in 5.0. **[LIVE]** run end to end on 5.1.1.

**What changed and why it matters**: an Action can now animate more than one data-block
("multi-user" actions, e.g. one walk-cycle Action shared by several character rigs), so F-Curves
had to move from living directly on the Action to living under a `Slot` (one per animated
data-block) → `Layer` → keyframe `Strip` → `Channelbag`. As of 5.1.1, **only one layer with one
(infinite, unmovable) strip is actually usable** — the layering is data-model-ready but not yet a
real multi-layer NLA-like feature.

**The good news, [LIVE]-confirmed**: `obj.keyframe_insert(...)` and `bpy_struct.driver_add(...)`
are **completely unaffected in calling convention** across 4.3→5.1. `keyframe_insert` transparently
creates the Action, slot, layer, strip and channelbag as needed:

```python
suzanne.keyframe_insert("location", index=0)  # identical code on 4.3, 4.4, 5.0, 5.1
```

The only place this bites is code that reaches into `action.fcurves` / `action.groups` /
`action.id_root` **directly** (bypassing `keyframe_insert`) — e.g. to enumerate all fcurves of an
action, add a bare FCurve without keying a real property, or organize channels into named groups.

| Blender | `action.fcurves` (legacy, direct) | Modern equivalent |
|---|---|---|
| 4.3 and earlier | Works — is the only API | N/A |
| 4.4 – 4.5 | Still works, now a **proxy** for `action.slots[0]`'s channelbag (creates layer/strip/slot as needed if absent) — "considered deprecated" | `action.layers[0].strips[0].channelbag(slot, ensure=True).fcurves` |
| 5.0 and later | **Removed entirely** — `hasattr(action, "fcurves")` is `False` **[LIVE, 5.1.1]** | `action.fcurve_ensure_for_datablock(datablock, data_path, index=0, group_name='')` (simplest — auto-creates layer/strip/slot too), or `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot)` / `action_ensure_channelbag_for_slot(action, slot)` |

**[LIVE, 5.1.1]** full round-trip test (new object, never previously animated):

```python
obj.keyframe_insert("location", frame=1)          # auto-creates everything
action = obj.animation_data.action
slot   = obj.animation_data.action_slot
slot.identifier       # -> "OBTempObj"  (2-char ID-type prefix + name)
slot.target_id_type   # -> "OBJECT"
hasattr(action, "fcurves")  # -> False  (confirms legacy API gone on 5.1.1)
strip = action.layers[0].strips[0]
channelbag = strip.channelbag(slot)
[(fc.data_path, fc.array_index) for fc in channelbag.fcurves]
# -> [("location", 0), ("location", 1), ("location", 2)]
fc = action.fcurve_ensure_for_datablock(obj, "location", index=0)  # works, returns existing FCurve
```

Creating a slot/layer/strip manually from scratch (needed only for advanced cases — sharing one
Action across several objects, or building an Action before anything is keyed). The API was
introduced in 4.4 and is unchanged through 5.1.1:

```python
action = bpy.data.actions.new("SuzanneAction")
slot = action.slots.new(id_type='OBJECT', name="Suzanne")   # slot.identifier -> "OBSuzanne"
layer = action.layers.new("Layer")
strip = layer.strips.new(type='KEYFRAME')
channelbag = strip.channelbag(slot, ensure=True)
fcurve = channelbag.fcurves.new("location", index=1, group_name="Object Transform")  # group_name= exists from 5.0;
                                                                                     # on 4.4/4.5 this new() takes no group argument
anim_data = suzanne.animation_data_create()
anim_data.action = action
anim_data.action_slot = anim_data.action_suitable_slots[0]  # only needed if auto-assignment picked the wrong/no slot
```

**Breaking behavior change specific to 4.4** (still true
on 5.1.1): `datablock.animation_data.action = some_action` may, depending on heuristics, **not**
auto-assign a slot, silently leaving the data-block un-animated even though the assignment
"succeeded". Force it: `anim_data.action_slot = anim_data.action_suitable_slots[0]` (only valid
*after* `.action` is assigned). NLA-strip and Action-constraint assignment (`strip.action = ...`,
`constraint.action = ...`) auto-assign a compatible slot more eagerly and don't have this gotcha.

`ActionSlot` properties (4.4+):
`identifier` (str, e.g. `"OBSuzanne"` — display name prefixed by 2 chars from the ID type),
`name_display` (str, the part after the prefix), `target_id_type` (settable only once while
`'UNSPECIFIED'`, read-only after), `handle` (int, internal numeric id used to look up the
channelbag), `active`/`select`/`show_expanded`.

---

## Keyframing & easing

### `keyframe_insert` / `keyframe_delete` / `driver_add` / `driver_remove`

All four are defined once on `bpy_struct` (the base of nearly every RNA type), which is why they
can be called on an `Object`, a `PoseBone`, a `NodeSocket`, a `ShapeKey`, etc. — anything with an
animatable property, not just ID data-blocks.
`bpy.types.bpy_struct` [4.3]:

```
keyframe_insert(data_path, index=-1, frame=bpy.context.scene.frame_current, group='', options=set(), keytype='KEYFRAME') -> bool
keyframe_delete(data_path, index=-1, frame=bpy.context.scene.frame_current, group='') -> bool
driver_add(path, index=-1) -> bpy.types.FCurve | list[bpy.types.FCurve]
driver_remove(path, index=-1) -> bool
```

- `index=-1` (default) means "all array indices at once" (or the single channel if the property
  isn't an array) — e.g. `keyframe_insert("location")` keys X, Y and Z in one call, creating 3
  FCurves. `driver_add("location")` with no index similarly returns a **list** of 3 FCurves;
  `driver_add("location", 1)` returns a single FCurve.
- `options` (set of flags): `INSERTKEY_NEEDED` (only if the value actually changed),
  `INSERTKEY_VISUAL` (bake the *visual*, constraint-affected transform instead of the raw local
  one), `INSERTKEY_XYZ_TO_RGB` ("no longer in use... here so code that uses it doesn't break" in
  4.3; **fully removed** as of the Blender 5.0 changelog — do not pass it on 5.0+: bpy checks every
  identifier in an enum-flag set and raises a `TypeError` for one it does not know),
  `INSERTKEY_REPLACE` (only update existing keys, never add new ones),
  `INSERTKEY_AVAILABLE` (only insert into F-Curves that already exist), `INSERTKEY_CYCLE_AWARE`.
- `keytype`: `'KEYFRAME' | 'BREAKDOWN' | 'MOVING_HOLD' | 'EXTREME' | 'JITTER' | 'GENERATED'`
  (same enum as `Keyframe.type`, **[LIVE]** identical on 5.1.1).
- Both `keyframe_insert` and `keyframe_delete` return a **bool** ("success"), not the created
  Keyframe object — to get the actual `Keyframe`, either use `fcurve.keyframe_points.insert(...)`
  directly (returns `Keyframe`) or look it up afterward.

**Cross-version signature nuance (not a confirmed break)**: the 4.3 doc renders
`keyframe_insert(data_path, index=-1, frame=..., ...)` (index positional-or-keyword), while the
`current` doc renders `keyframe_insert(data_path, *, index=-1, frame=..., ...)` (index
keyword-only), and `driver_add(path, index=-1)` (4.3) vs `driver_add(path, index=-1, /)` (current,
both positional-only). No 4.4/4.5/5.0/5.1 changelog entry mentions this explicitly, so this is
most likely the newer Sphinx build simply rendering a calling-convention restriction that already
existed at the C/Argument-Clinic level in 4.3, not a real behavior change — but since it cannot be
fully confirmed without a live 4.3 instance, **always call `index=` and `frame=` as keywords**
(`obj.keyframe_insert("location", index=1, frame=10)`) — safe on every version either way.

**Nested-property gotcha, verified both ways**:
- For a **custom, Python-registered `PropertyGroup`** nested under a non-ID struct (e.g. a
  `PointerProperty` you added to `bpy.types.Bone`), the Blender 4.3 API reference
  is explicit: *"Note that
  when keying data paths which contain nested properties this must be done from the ID subclass...
  rather than the bone"* — call `keyframe_insert` on the owning ID (e.g. the Armature data-block)
  with the **full path relative to that ID**: `arm.keyframe_insert(data_path='bones["Bone"].my_prop.nested', frame=1)`.
- For **built-in** nested structs that Blender itself defines (PoseBone, NodeSocket, ShapeKey),
  calling `keyframe_insert` **directly on the nested struct** works fine and is the normal idiom —
  e.g. `object.pose.bones["Arm_L"].keyframe_insert("rotation_euler", index=1, frame=1)`
  or `node.inputs["Base Color"].keyframe_insert("default_value", frame=1)`
  (**[LIVE]**, verified below in Materials). The restriction is specifically about ad-hoc custom
  PropertyGroups, not built-in RNA structs.

### The `Keyframe` object and interpolation/easing

Model: `FCurve.keyframe_points` is an `FCurveKeyframePoints` collection of `Keyframe` — a Bézier
point with two handles. `bpy.types.Keyframe` [4.3, identical live on 5.1.1]:

- `co` / `co_ui` (Vector 2: `(frame, value)`; `co_ui` also updates handles like the Graph Editor's
  transform operator does — prefer `co_ui` when nudging a key interactively-equivalently, use raw
  `co` for pure data edits where you'll fix up handles yourself)
- `handle_left` / `handle_right` (Vector 2, absolute frame/value coordinates, not deltas)
- `handle_left_type` / `handle_right_type` — enum **[LIVE-verified 5.1.1, identical to 4.3]**:
  `FREE, ALIGNED, VECTOR, AUTO, AUTO_CLAMPED` (default `FREE`)
- `interpolation` — enum **[LIVE-verified identical]**, 13 values:
  `CONSTANT, LINEAR, BEZIER` (standard), `SINE, QUAD, CUBIC, QUART, QUINT, EXPO, CIRC` (easing by
  strength, weakest→strongest), `BACK, BOUNCE, ELASTIC` (dynamic effects)
- `easing` — enum **[LIVE-verified identical]**: `AUTO, EASE_IN, EASE_OUT, EASE_IN_OUT` (default
  `AUTO` — Blender picks Ease-In for transitional types, Ease-Out for the dynamic ones)
- `amplitude` (float, ELASTIC only — "boost elastic bounces"), `back` (float, BACK only —
  overshoot amount), `period` (float, ELASTIC only — time between bounces)
- `type` — enum, same 6 values as `keytype` above (`KEYFRAME, BREAKDOWN, MOVING_HOLD, EXTREME,
  JITTER, GENERATED`) — cosmetic marker only, does not affect evaluation
- `select_control_point` / `select_left_handle` / `select_right_handle` (bool)

**When to touch `handle_left`/`handle_right` directly** vs. `handle_*_type`: set the *type* enum
when you want Blender to compute the handle position automatically (`AUTO`/`AUTO_CLAMPED` for
smooth auto-eased curves, `VECTOR` for a hard corner into/out of a key, `ALIGNED` to manually shape
both handles as one straight line through the key). Set `handle_left`/`handle_right` *directly*
only when you need a specific, non-default tangent — and to do that, the type must first be
`FREE` or `ALIGNED` (with `AUTO`/`AUTO_CLAMPED`/`VECTOR`, Blender recomputes the handle position
every evaluation and ignores whatever you wrote to `handle_left`/`handle_right`).

**Always call `fcurve.update()`** after directly mutating `.co`, `.handle_left`, or
`.handle_right` on any keyframe — its doc string is literally "Ensure keyframes are sorted in
chronological order and handles are set correctly." Moving a key's frame (`.co.x`) out of
chronological order without calling `update()` (or `keyframe_points.sort()`) leaves the curve in
an unsorted state that produces wrong evaluation.

### `FCurveKeyframePoints` — insert / add / remove / clear / sort

`bpy.types.FCurveKeyframePoints` [4.3]:

```python
fcurve.keyframe_points.insert(frame, value, options={'REPLACE'|'NEEDED'|'FAST'}, keyframe_type='KEYFRAME') -> Keyframe
fcurve.keyframe_points.add(count)          # append `count` blank points (co=(0,0)) — fast bulk pattern
fcurve.keyframe_points.remove(keyframe, fast=False)
fcurve.keyframe_points.clear()
fcurve.keyframe_points.sort()              # re-sort by frame after manual .co edits
```

`.insert()` goes through the same fcurve as `obj.keyframe_insert()` but works directly on an
`FCurve` you already have a handle to (e.g. one just created via
`action.fcurve_ensure_for_datablock(...)`), and returns the actual `Keyframe` object instead of a
bool — useful when you need to immediately set `.interpolation`/`.handle_left_type` on the point
you just made. The `.add(count)` + direct `.co` assignment pattern is the fast path for
programmatically generating many keys (e.g. baking a procedural curve) without the per-call
overhead of `.insert()`; call `.sort()` (or `fcurve.update()`) afterward.

**Deleting/moving keys in a headless/no-UI context**: `bpy.ops.action.*`/`bpy.ops.graph.*`
operators (delete, snap, etc.) require a Dope Sheet/Graph Editor area in `context` — not available
from a background/MCP script without a manual context override. The robust, UI-free path is always
direct data manipulation: `fcurve.keyframe_points.remove(kf)` to delete, or mutate `kf.co.x` (the
frame) directly then call `fcurve.update()` to move a key in time.

---

## F-curve modifiers

Base class `bpy.types.FModifier` [4.3,
identical live]: `active`, `blend_in`/`blend_out` (frames to fade influence in/out),
`frame_start`/`frame_end` (only used if `use_restricted_range=True`), `influence` (0-1, only used
if `use_influence=True`), `mute`, `name`, `show_expanded`, `type` (readonly), `is_valid` (readonly).

**Adding a modifier**: `fcurve.modifiers.new(type=...) -> FModifier`; `fcurve.modifiers.remove(modifier)`.
`bpy.types.FCurveModifiers` [4.3]
— note the official doc's one-line description for `.new()` literally reads *"Add a **constraint**
to this object"* / *"Constraint type to add"*, a copy-paste artifact from `ObjectConstraints.new()`
carried over in Blender's auto-generated docs; trust the verified `Return type: FModifier`, not
that sentence.

**`type` enum** — **[LIVE, 5.1.1]** `bl_rna.properties["type"].enum_items` returned
`['NULL', 'GENERATOR', 'FNGENERATOR', 'ENVELOPE', 'CYCLES', 'NOISE', 'LIMITS', 'STEPPED', 'SMOOTH']`
— **9 values**, one more than the 4.3 doc's 8 (`NULL` through `STEPPED`; `SMOOTH` is new, see below).

### NOISE — camera shake / idle wobble

`bpy.types.FModifierNoise` [4.3
base fields] **[LIVE-diffed against 5.1.1 — reworked in Blender 4.4, see next paragraph]**:

- `blend_type`: enum `REPLACE | ADD | SUBTRACT | MULTIPLY` (default `REPLACE`)
- `scale` (float) — "Scaling (in time) of the noise" — horizontal/time frequency; higher = slower/wider oscillation
- `strength` (float) — amplitude, the vertical scale applied to the driven property
- `phase` (float) — random seed
- `offset` (float) — time offset
- `depth` (int, 0-32767) — "fine level detail" — number of fractal octaves

**Reworked in Blender 4.4** (Blender's own release wording): *"The
algorithm for generating the values of the F-Curve Noise Modifier has been updated ... Now the
values don't exceed the -0.5/0.5 range anymore. Doing so added two new properties ... Lacunarity
and Roughness. The default values are chosen to closely resemble the previous behavior. There is a
checkbox to use the old noise, which old files will automatically have enabled."* **[LIVE,
5.1.1]** `FModifierNoise` now additionally has:
- `lacunarity` (float, default 2.0) — "Gap between successive frequencies. Depth needs to be
  greater than 0 for this to have an effect"
- `roughness` (float, default 0.5) — "Amount of high frequency detail. Depth needs to be greater
  than 0 for this to have an effect"
- `use_legacy_noise` (bool, default `False` for new modifiers / auto-`True` on old files loaded
  into 4.4+) — "Use the legacy way of generating noise. Has the issue that it can produce values
  outside of -1/1"

For **camera shake**, the common recipe is: key the base motion normally (for a camera that does
not move, insert a single key at its rest value), add a NOISE modifier to
each of the 3 rotation-axis FCurves (and/or location), and tune `strength` (shake amount) and
`scale` (shake speed — smaller `scale` = faster jitter). Use a different `phase` per axis so X/Y/Z
don't wobble in lockstep. The key is required: Blender skips an F-Curve that has no keyframes and
no generating modifier, and NOISE is not a generating modifier, so a NOISE modifier on an
un-keyed curve does nothing. The noise is added around the keyed value.

### CYCLES — perfect loops

`bpy.types.FModifierCycles`
[4.3, identical live]: `mode_before`/`mode_after` — enum **[LIVE-verified]**
`NONE | REPEAT | REPEAT_OFFSET | MIRROR` (default `NONE`); `cycles_before`/`cycles_after` (int,
`0` = infinite). `REPEAT` repeats the curve identically (true perfect loop, needs the curve's
start/end value and tangent to already match); `REPEAT_OFFSET` repeats but offsets each copy
vertically so the first keyframe of the repeat matches the last value of the previous cycle (the
right choice for something that keeps moving forward each cycle, e.g. a continuously advancing
walk cycle or a conveyor); `MIRROR` alternates forward/backward playback each cycle (good for an
idle breathing/bob loop with no hard reset).
**"Trivially Cyclic Curves"** — when both ends are `REPEAT` or `REPEAT_OFFSET` and no other option
is changed, Blender's automatic Bézier handle placement becomes cycle-aware (smooths the seam), and
the `INSERTKEY_CYCLE_AWARE` keying option (see above) starts taking the cycle into account when you
insert new keys.

**Hard mutual-exclusivity constraint**: *"The Cycles
Modifier has to be the first modifier in the list... This means this modifier is not compatible
with the Smooth (Gaussian) Modifier"* — and the Smooth modifier has the same
requirement. Both modifiers need to read the *original* keyframe positions, so whichever is applied
first blocks the other from ever being first — **you cannot use CYCLES and SMOOTH together on the
same F-Curve.**

### GENERATOR — deterministic polynomial curves

`bpy.types.FModifierGenerator`
[4.3, identical live]: `mode` enum `POLYNOMIAL | POLYNOMIAL_FACTORISED` (default `POLYNOMIAL`),
`poly_order` (int 1-100, "highest power of x"), `coefficients` (float array of 32, starting from
x^0), `use_additive` (bool — apply on top of existing curve values instead of replacing them).

### SMOOTH (Gaussian) — new in Blender 5.1, does not exist in 4.3

Added in Blender 5.1:
*"A new F-Curve modifier was added called 'Gaussian Smooth'. This allows to non-destructively
smooth F-Curves. For technical reasons, the modifier has to be in the first position of the
modifier stack to work."* **[LIVE, 5.1.1]** class is `bpy.types.FModifierSmooth`, description
*"Smooth curve using Gaussian smoothing"*, two own properties:
`sigma` (float, 0.1-100, "shape of the Gaussian distribution in frames — lower = sharper"),
`filter_width` (int, 1-32, "number of frames to average around each keyframe — higher = more
smoothing but slower"). Same first-in-stack requirement and CYCLES exclusivity as above. **On
Blender 4.3, `fcurve.modifiers.new(type='SMOOTH')` will simply fail** (not a valid enum value) —
gate any use of this on `bpy.app.version >= (5, 1, 0)`.

### LIMITS / STEPPED / ENVELOPE — brief

- `FModifierLimits` [4.3]:
  `min_x`/`max_x`/`min_y`/`max_y` + matching `use_min_x`/`use_max_x`/`use_min_y`/`use_max_y` bools
  — clamps value range and/or truncates the time range (replaced by constant extrapolation outside it).
- `FModifierStepped` [4.3]:
  `frame_step` (hold each value for N frames — the "stop-motion"/on-twos effect),
  `frame_offset`, `frame_start`/`frame_end` + `use_frame_start`/`use_frame_end`.
- `FModifierEnvelope` [4.3]:
  `reference_value`, `default_min`/`default_max` (distance from reference for 1:1 default
  influence), `control_points` (collection of `FModifierEnvelopeControlPoint`, each with `frame`
  and `min`/`max` — lets you author a time-varying gain envelope on top of the curve).

---

## Camera

### Focal length & depth of field — keyframed on `object.data`, not the `Object`

The `Camera` datablock (`object.data`, an `ID` with its own `animation_data`) holds all optical
properties — **a common mistake is calling `keyframe_insert` on the camera `Object` for these**;
it must be the camera *data* block.
`bpy.types.Camera` /
`bpy.types.CameraDOFSettings` [4.3]:

```python
cam_data = camera_object.data                      # bpy.types.Camera
cam_data.keyframe_insert(data_path="lens", frame=1)          # focal length, mm (float, >= 1)
cam_data.dof.use_dof = True
cam_data.keyframe_insert(data_path="dof.focus_distance", frame=1)  # nested struct, still keyed from the Camera ID
cam_data.keyframe_insert(data_path="dof.aperture_fstop", frame=1)
```
`CameraDOFSettings`: `use_dof` (bool), `focus_distance` (float, meters), `focus_object`
(Object — if set, distance tracks that object live instead of the fixed float),
`focus_subtarget` (str, armature bone name, used together with `focus_object`),
`aperture_fstop` (default 2.8 — lower = more background blur), `aperture_blades` (0-16, polygonal
bokeh shape), `aperture_rotation`, `aperture_ratio` (anamorphic bokeh squeeze).

### Track To vs. Damped Track

Both aim a chosen local axis of the camera at a target; the difference is in *up*-vector control.
`bpy.types.TrackToConstraint` /
`bpy.types.DampedTrackConstraint` [4.3, enums **[LIVE-verified identical 5.1.1]**]:

| | Track To | Damped Track |
|---|---|---|
| `track_axis` | enum `TRACK_X\|Y\|Z\|NEGATIVE_X\|NEGATIVE_Y\|NEGATIVE_Z` (`constraints.new()` sets `TRACK_NEGATIVE_Z`) | same 6 values (`constraints.new()` sets `TRACK_Y`) |
| `up_axis` | enum `UP_X\|UP_Y\|UP_Z` (`constraints.new()` sets `UP_Y`) | **does not exist on this constraint** |
| `use_target_z` | yes | n/a |
| roll behavior | "Up" axis stays aligned to world (or target) Z as much as possible — controllable, no flip surprises | takes the *shortest rotation path* to aim — no up-reference at all, so it can roll unpredictably as the target moves overhead, but never gimbal-locks |

Blender's manual
calls Track To *"the preferred tracking constraint, as it has a more easily controlled constraining
mechanism"* specifically because of the explicit `up_axis`.

**Camera convention**: a Blender camera looks down its **local -Z** with +Y up. The static RNA
docs list `TRACK_X`/`UP_X` as defaults, but `constraints.new()` runs the constraint's new-data
initialiser, which since Blender 2.91 sets Track To to `TRACK_NEGATIVE_Z`/`UP_Y` (made for cameras
and lights) and Damped Track to `TRACK_Y`. Set the axes explicitly anyway, so the script does not
depend on that initialiser and documents its intent:
```python
con = cam_obj.constraints.new(type='TRACK_TO')
con.target = target_obj
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
```
For a **Damped Track** on a camera, set `track_axis = 'TRACK_NEGATIVE_Z'` yourself: its initial
`TRACK_Y` aims the camera's local +Y, not its view direction, at the target.

### Follow Path — two different position-control mechanisms

`bpy.types.FollowPathConstraint`
[4.3, **[LIVE-verified defaults + numeric behavior on 5.1.1]**]: `target` (must be a Curve object),
`forward_axis` (enum `FORWARD_X|Y|Z|TRACK_NEGATIVE_X|Y|Z`, **[LIVE]** default `'FORWARD_Y'` —
note the odd mixed naming, verified exactly as documented), `up_axis` (`UP_X|Y|Z`, **[LIVE]**
default `'UP_Z'`), `use_curve_follow` (bool — also rotate to match the curve's tangent/bank, using
forward/up axis; if off, only position is affected), `use_curve_radius` (bool — scale by the
curve's per-point radius), `offset` (float, frame count), `offset_factor` (float, **[LIVE]**
default `0`), `use_fixed_location` (bool, **[LIVE]** default `False`).

Two genuinely independent ways to control where the object sits along the path — **[LIVE,
5.1.1]** numerically verified on a straight 10-unit test curve:

1. **`use_fixed_location=True` + keyframe `offset_factor` directly** (0.0 = start, 1.0 = end,
   percentage-along-curve, independent of the scene's current frame). **[LIVE]** confirmed exact:
   `offset_factor=0.5` → world position at the curve's exact midpoint; `offset_factor=0.0` → start.
   This is the **more controllable, recommended-by-default** mechanism for scripted camera
   dollies: single object, single set of keyframes on `offset_factor`, no cross-datablock
   coordination needed.
2. **`use_fixed_location=False` (default) — time-driven**: position comes from the *scene's
   current frame* mapped through the target curve's own `Curve.path_duration` (frames for one
   full traversal, `bpy.types.Curve`
   [4.3]: int, default 100, "defining the maximum value for the Evaluation Time setting") plus
   `constraint.offset` (a frame shift). For non-linear speed / ease-in-out along the path, or to
   have **multiple objects share one master timeline** (each with a different `offset`), animate
   `Curve.eval_time` directly instead (float, "Parametric position along the length of the curve
   ... evaluated by dividing by the Path Length value") — this requires keyframing the *curve
   data-block*, a different ID than the follower object(s).

A third, older, distinct mechanism (not the constraint at all): parenting an object straight to a
Curve object (`child.parent = curve_obj`) together with `Curve.use_path=True` and
`Curve.use_path_follow=True` — position/rotation driven the same way as mechanism 2 above
(scene-frame + `path_duration`/`eval_time`), but with no per-follower `offset` or `offset_factor`
control at all. Prefer the constraint for anything scripted.

### Orbit / turntable rigs, dolly/crane moves — the empty-parent pattern

Standard rig: an `Empty` at the pivot point, the camera parented to (or Child-Of / simply offset
from) the empty. Keyframe the **empty's** `rotation_euler.z` for an orbit/turntable — this
isolates "orbit" as one clean rotation channel, independent of the camera's own position/lens
animation. For a constant-speed spin, set both keys (0 and 2π) to `LINEAR` interpolation and add a
`FModifierCycles` with `mode_after='REPEAT_OFFSET'` on that one rotation FCurve: each cycle carries
on from 2π, so it spins forever with no extra keys. With the default Bezier keys the spin eases to
a stop and speeds up again every revolution. Dolly/crane moves: chain two empties
(dolly-empty carrying horizontal travel, a child crane-empty carrying vertical/height, camera as
the crane-empty's child) so each artist-facing motion axis is its own independent keyed channel
instead of one tangled camera transform.

```python
bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1.0, location=(0, 0, 1))
```
`bpy.ops.object.empty_add`
[4.3, `type` enum **[LIVE-verified identical 5.1.1]**]: `type` — 8 values, exactly
`PLAIN_AXES, ARROWS, SINGLE_ARROW, CIRCLE, CUBE, SPHERE, CONE, IMAGE`. Note: the documented
operator signature shows `scale=(0.0, 0.0, 0.0)` as its literal default — this is a redo-panel
signature artifact, **[LIVE-verified]** the actual created empty ends up at `scale == (1, 1, 1)`
regardless; `radius` (not `scale`) is what maps to the empty's visible size
(`Object.empty_display_size`, **[LIVE]** confirmed `radius=2.0` → `empty_display_size == 2`).

**Parenting jump gotcha — [LIVE-demonstrated numerically, 5.1.1]**: assigning `.parent` directly
in a script does **not** solve the parent-inverse the way `Ctrl-P`/`bpy.ops.object.parent_set()`
does in the UI:
```python
child.location = (1, 0, 0)                 # world position (1,0,0)
parent.location = (5, 5, 5)
child.parent = parent                      # naive assignment
# [LIVE] child.matrix_world.translation is now (6, 5, 5) -- JUMPED
child.matrix_parent_inverse = parent.matrix_world.inverted()
# [LIVE] child.matrix_world.translation is back to (1, 0, 0) -- fixed
```
`Object.matrix_parent_inverse` [4.3] — "Inverse of object's parent matrix at time of parenting" —
is the property that must be set; simple attribute assignment leaves it at whatever it was before
(identity for a fresh object), so the child's local transform gets silently re-interpreted inside
the new parent's space.

### Motion paths — reading computed arcs back into Python (no viewport needed)

`bpy.ops.object.paths_calculate`
[4.3, **[LIVE end-to-end round trip on 5.1.1]**]:
```python
bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE')  # operates on selected objects
mp = obj.motion_path                    # bpy.types.MotionPath, or None if not calculated
mp.frame_start, mp.frame_end, mp.length # int, int, int (cached-frame count)
mp.points[i].co                         # mathutils.Vector, WORLD-SPACE position at that cached frame
bpy.ops.object.paths_update()           # recompute after changing the animation
bpy.ops.object.paths_clear()            # -> obj.motion_path becomes None again
```
`bpy.ops.pose.paths_calculate(...)` is the bone/pose-space equivalent (same
`display_type`/`range` parameters; per-bone `PoseBone.motion_path` afterward).
**[LIVE]** verified the full loop on a 3-keyframe test object (frames 1/25/50): after
`paths_calculate`, `mp.points[0].co`, `mp.points[24].co`, `mp.points[-1].co` exactly matched the 3
keyframed world positions, and `paths_clear()` correctly reset `obj.motion_path` to `None`. This
means an **arc/overshoot audit is fully scriptable without ever opening the viewport**: compute
the path, then do finite-difference curvature or peak-deviation-from-chord analysis directly on
the list of `.co` vectors in Python.

---

## Constraints

`ObjectConstraints.new(type=) -> Constraint`; `.remove(constraint)`; `.clear()`;
`.move(from_index, to_index)`; `.copy(constraint)` (copy from another object's constraint).
`bpy.types.ObjectConstraints` [4.3].
Verified `type` string identifiers for the constraints this document covers: `TRACK_TO`,
`DAMPED_TRACK`, `FOLLOW_PATH`, `CHILD_OF`. `LOCKED_TRACK` and `CLAMP_TO` are listed for reference
only; this document does not cover them (all six are from the `Constraint Type Items` enum page,
which lists many more types).

**Base `Constraint`** fields common to every constraint type
`bpy.types.Constraint` [4.3]:
`name`, `type` (readonly), `enabled` (bool), `mute` (bool), **`influence`** (float 0-1, default
0 at RNA level but Blender's `.new()` sets it to 1 in practice — **this is the standard,
keyframable "blend a constraint in/out" channel**, e.g. fading a Track-To off over a few frames
to hand control back to manual animation), `owner_space` (enum `WORLD | CUSTOM | POSE |
LOCAL_WITH_PARENT | LOCAL`), `target_space` (the same enum plus `LOCAL_OWNER_ORIENT`), `space_object`/`space_subtarget` (used when space is
`CUSTOM`), `active`, `show_expanded`, `is_valid` (readonly), `error_location`/`error_rotation`
(readonly residual-error diagnostics, useful for detecting an unsolvable IK/constraint chain from
script without rendering anything).

### Child Of — inverse matrix, verified live with a real surprise

`bpy.types.ChildOfConstraint`
[4.3]: `target`, `subtarget`, `use_location_x/y/z`, `use_rotation_x/y/z`, `use_scale_x/y/z` (which
parent channels apply), `inverse_matrix` (Matrix 4×4 — the correction that cancels out the jump
when the constraint is added), `set_inverse_pending` (bool flag).

**[LIVE, 5.1.1]**: Child Of is commonly expected to need an explicit "Set Inverse" step, or the
object visibly snaps the moment the constraint/target is set. On 5.1.1:
```python
con = child.constraints.new(type='CHILD_OF')
con.inverse_matrix   # -> identity, immediately after .new() (NOT the all-zero value the static
                      #    4.3 RNA doc page lists as "default" -- that's a generic Matrix-property
                      #    placeholder, not the real runtime-initialized value)
con.target = target
con.inverse_matrix   # -> automatically changed to target.matrix_world.inverted() at the moment
                      #    .target was assigned -- child.matrix_world did NOT jump in this test
```
So on this 5.1.1 build, a **fresh** Child Of constraint auto-solves its inverse the instant
`.target` is assigned. This was not checked on a 4.3 build — **do not rely on
this auto-solve as guaranteed** across versions or once the target has already moved since some
earlier assignment. The version-safe, explicit fix — confirmed to also work
**[LIVE]** — is the same operator the "Set Inverse" button calls:
```python
bpy.context.view_layer.objects.active = child   # operator needs the constrained object active
child.select_set(True)
bpy.ops.constraint.childof_set_inverse(constraint=con.name, owner='OBJECT')  # owner: 'OBJECT'|'BONE'
# bpy.ops.constraint.childof_clear_inverse(constraint=con.name, owner='OBJECT')  -- companion
```
`bpy.ops.constraint` [4.3]. Calling
this right after every target assignment is cheap and removes the ambiguity entirely, regardless
of whether the auto-solve already fired.

The exact same class of bug (documented under Camera above) affects **plain parenting** too —
`obj.parent = x` has the identical jump/fix shape as Child Of, just via `matrix_parent_inverse`
directly instead of an operator.

---

## Materials

### Where the animation data actually lives — verified, and it is not where it looks

A `Material` is an `ID` (has its own `animation_data`), but its shader graph lives in
`material.node_tree`, which is **itself a separate `ID`** (`NodeTree(ID)`) **with its own,
independent `animation_data`**.
`bpy.types.Material` /
`bpy.types.NodeTree` [4.3, both
confirm `animation_data: AnimData, (readonly)` independently] — **[LIVE, 5.1.1]** confirmed
concretely: after keyframing a Principled BSDF socket, `material.animation_data is None` (True —
nothing ever keyed a material-level property) while `material.node_tree.animation_data` holds the
real `Action` (auto-named `"<MaterialName>Action"`). **This is where to look when hunting for or
baking a "material animation" — `material.node_tree.animation_data.action`, never
`material.animation_data`.** The identical pattern applies to shape keys (below): the Action lives
on `mesh.shape_keys.animation_data`, not `mesh.animation_data`.

### Keyframing a node socket's `default_value` — verified working code, exact calling convention

**[LIVE, 5.1.1]** confirmed end-to-end — `keyframe_insert` is called **directly on the socket
object**, not on the node, not on `node.inputs` (the collection itself), and not via a composed
path from the node_tree:
```python
principled = material.node_tree.nodes["Principled BSDF"]
principled.inputs["Base Color"].default_value = (1.0, 0.0, 0.0, 1.0)
principled.inputs["Base Color"].keyframe_insert("default_value", frame=1)       # [LIVE] -> True
principled.inputs["Emission Strength"].default_value = 2.0
principled.inputs["Emission Strength"].keyframe_insert("default_value", frame=1)  # [LIVE] -> True
```
Calling `keyframe_insert` on the wrong target raises a clear error (the same on Compositor nodes,
which share the `NodeSocket` type with Shader nodes; not re-run in 5.1.1): `TypeError: bpy_struct.keyframe_insert() property "inputs" not animatable` when you
try to key `node.inputs` itself instead of a specific socket.
`NodeSocketFloat.default_value` and its color/vector siblings are plain, non-readonly RNA
properties `bpy.types.NodeSocketFloat`
[4.3] — that's why direct keying "just works" with no special-casing.

### Principled BSDF — full, ground-truth input socket list (do not hardcode from memory)

The static RNA class page for `ShaderNodeBsdfPrincipled` only exposes two real properties
(`distribution`, `subsurface_method`) plus `input_template(index)`/`output_template(index)`
classmethods — **the input socket names themselves are runtime node-tree data, not static RNA
properties**, and are exactly the kind of thing that must be read back via `.inputs.keys()`
rather than assumed. **[LIVE, 5.1.1]**, `[s.name for s in principled.inputs]`, complete and in
order:
```
Base Color, Metallic, Roughness, IOR, Alpha, Normal, Weight, Diffuse Roughness,
Subsurface Weight, Subsurface Radius, Subsurface Scale, Subsurface IOR, Subsurface Anisotropy,
Specular IOR Level, Specular Tint, Anisotropic, Anisotropic Rotation, Tangent,
Transmission Weight, Coat Weight, Coat Roughness, Coat IOR, Coat Tint, Coat Normal,
Sheen Weight, Sheen Roughness, Sheen Tint, Emission Color, Emission Strength,
Thin Film Thickness, Thin Film IOR
```
Note the OpenPBR-era naming: what used to be "Clearcoat" is now **"Coat Weight"/"Coat
Roughness"/etc.**, and "Transmission" is **"Transmission Weight"** — these are qualified names
specifically so multiple `Weight` inputs (Subsurface/Transmission/Coat/Sheen) don't collide by
name. Emission is split into **"Emission Color"** + **"Emission Strength"** (added Blender 2.91,
still current).
**Recommendation: always confirm the exact socket set with
`[s.name for s in node.inputs]` at runtime before keying** — Blender has renamed Principled BSDF
sockets across major versions before and will likely again.

### Mix node — Factor/A/B name ambiguity, resolved and verified live (not obvious from docs)

`ShaderNodeMix` (the modern, unified node since 3.4, replacing per-type Mix nodes) has `data_type`
(enum `FLOAT | VECTOR | RGBA | ROTATION` per its static `bl_rna` — **[LIVE, 5.1.1] but
`ROTATION` is runtime-rejected inside a *shader* node tree**: `mix.data_type = 'ROTATION'` raises
`TypeError: enum "ROTATION" not found in ('FLOAT', 'VECTOR', 'RGBA')` — rotation mixing exists on
the same underlying "Mix" node type only for Geometry Nodes trees), `blend_type` (Ramp-Blend enum,
e.g. `MIX`/`ADD`/`MULTIPLY`...), `factor_mode` (`UNIFORM | NON_UNIFORM`), `clamp_factor`,
`clamp_result`. `bpy.types.ShaderNodeMix` [4.3].

**[LIVE, 5.1.1]** the node actually carries **all four data-types' sockets simultaneously** in
`.inputs`, only enabling the ones matching the current `data_type`:
```
index 0: name="Factor", identifier="Factor_Float"   (enabled iff factor_mode uses the scalar factor)
index 1: name="Factor", identifier="Factor_Vector"
index 2: name="A", identifier="A_Float"    index 3: name="B", identifier="B_Float"
index 4: name="A", identifier="A_Vector"   index 5: name="B", identifier="B_Vector"
index 6: name="A", identifier="A_Color"    index 7: name="B", identifier="B_Color"
index 8: name="A", identifier="A_Rotation" index 9: name="B", identifier="B_Rotation"
```
Despite the duplicate display `.name` values, **[LIVE-verified]** name-based lookup
`mix.inputs["A"]` correctly resolves to the *currently enabled* one matching the live
`data_type` (e.g. after `mix.data_type = 'RGBA'`, `mix.inputs["A"].identifier == "A_Color"`, not
the first-in-list `"A_Float"`) — **provided you set `data_type` before reading `.inputs[...]` by
name**. This is easy to get wrong (a naive assumption would be "first match by name," which is wrong
here), and the Blender API reference does not describe it. Its Factor input's actual socket name
is `"Factor"` — not listed on the static RNA page (dynamic node data again).

The legacy `bpy.types.ShaderNodeMixRGB`
[4.3] still exists (for old files/scripts): `blend_type`, `use_alpha`, `use_clamp`; its factor
socket is named `"Fac"`.

### Emission strength pulse / alpha fade / mix factor animation

All three reduce to the same recipe: get the node, get `.inputs["X"]`, set `.default_value`,
`.keyframe_insert("default_value", frame=N)` — repeat per keyframe. For a *pulsing* emission
(rather than a handful of authored beats), key one or two values and add an `FModifierNoise` or
`FModifierCycles` to the resulting FCurve instead of hand-authoring every cycle — reachable via
`material.node_tree.animation_data.action.fcurve_ensure_for_datablock(...)` (4.4+ helper) or the
plain legacy `action.fcurves.find(...)` on 4.3.

---

## Drivers

`driver_add(path, index=-1) -> FCurve | list[FCurve]` / `driver_remove(path, index=-1) -> bool`,
defined on `bpy_struct` (same as `keyframe_insert`). **Drivers live in
`id.animation_data.drivers`** (`AnimDataDrivers`, a collection of `FCurve`) — **verified this is
completely separate from Actions/Action-Slots**; the driver f-curve's own `.driver` property
(populated only on driver-curves) holds the `Driver` object. `bpy.types.Driver` [4.3, enum **[LIVE-verified identical 5.1.1]**]:
`type` — `AVERAGE | SUM | SCRIPTED | MIN | MAX` (default `AVERAGE`), `expression` (str, used when
`type='SCRIPTED'`), `use_self` (adds a `self` variable referencing the driven data itself —
*"Note that dependencies for properties accessed via self may not be fully tracked"*),
`variables` (`ChannelDriverVariables`), `is_valid`, `is_simple_expression` (readonly).

**Variables and targets**
`bpy.types.DriverVariable` /
`bpy.types.DriverTarget`
[4.3, enums **[LIVE-verified identical 5.1.1]**]:
```python
var = driver.variables.new()          # -> DriverVariable, no args -- must set name/type after
var.name = "dist"                     # ASCII only, no dots/spaces -- used verbatim in `expression`
var.type = 'TRANSFORMS'               # SINGLE_PROP | TRANSFORMS | ROTATION_DIFF | LOC_DIFF | CONTEXT_PROP
target = var.targets[0]               # 1 target for SINGLE_PROP/TRANSFORMS/CONTEXT_PROP, 2 for *_DIFF
target.id = car_object                # id_type must already be set/default OBJECT
target.data_path = "..."              # only for SINGLE_PROP
target.transform_type = 'LOC_X'       # LOC_X|Y|Z, ROT_X|Y|Z|W, SCALE_X|Y|Z, SCALE_AVG -- for TRANSFORMS
target.transform_space = 'WORLD_SPACE'   # WORLD_SPACE | TRANSFORM_SPACE | LOCAL_SPACE
target.rotation_mode = 'AUTO'         # AUTO|XYZ|XZY|YXZ|YZX|ZXY|ZYX|QUATERNION|SWING_TWIST_X|Y|Z
target.use_fallback_value = True      # + target.fallback_value -- value used if data_path can't resolve
```
`driver.variables.remove(var)`. Rotation-mode Swing/Twist decomposition
(`SWING_TWIST_X/Y/Z`) is the standard rig trick for driving corrective shape keys / secondary
bones off a joint's swing-vs-twist components separately — typically produced
by a Damped-Track-then-Copy-Transforms helper-bone pair.

**Scripted-expression namespace and a real portability gotcha** (4.3, unchanged in 5.1): a fixed subset of expressions ("Simple Expressions") is
evaluated **without** the full Python interpreter — ASCII variable names, float/int literals, the
global `frame`, constants `pi`/`True`/`False`, operators `+ - * / == != < <= > >= and or not` plus
ternary-if, and the functions `min max radians degrees abs fabs floor ceil trunc round int sin cos
tan asin acos atan atan2 exp log sqrt pow fmod lerp clamp smoothstep`. *"Simple expressions are
evaluated even when Python script execution is disabled."* Anything outside that subset falls back
to a real `eval()`-based Python expression, which **is blocked by Blender's "Auto Run Python
Scripts" trust setting** in untrusted files. A driver authored today against a trusted, already-
scripting-enabled MCP-connected Blender session can silently stop evaluating if the `.blend` is
later opened elsewhere (a render farm, a colleague's default-locked-down install) without that
setting enabled — prefer the documented simple-expression subset, or the plain built-in
`AVERAGE`/`SUM`/`MIN`/`MAX` types with no expression at all, whenever the file needs to be portable.

**When a driver beats keyframes (verified end-to-end, [LIVE] 5.1.1)** — mechanical linkage, e.g. a
wheel that must spin proportionally to distance traveled rather than being separately hand-timed:
```python
fcurve = wheel.driver_add("rotation_euler", 1)     # Y-axis rotation, single FCurve (index != -1)
drv = fcurve.driver
drv.type = 'SCRIPTED'
var = drv.variables.new(); var.name = "dist"; var.type = 'TRANSFORMS'
t = var.targets[0]; t.id = car; t.transform_type = 'LOC_X'; t.transform_space = 'WORLD_SPACE'
drv.expression = "dist / 1.0"     # radius = 1m -> 1 revolution (2*pi rad) per 2*pi meters traveled
```
**[LIVE]** with the car keyframed from x=0 (frame 1) to x=2π≈6.2832 (frame 50), the wheel's
evaluated `rotation_euler.y` at frame 50 was exactly 6.2832 rad — confirms the whole recipe
numerically, not just structurally. The general rule: **keyframes are for authored/artist-timed
values; drivers are for computed values that must always stay mathematically consistent with some
other live property** — if the car's motion gets re-timed or rescaled later, a keyframed wheel
rotation would immediately desync, while the driver stays correct automatically.

---

## Shape keys

`Key` (`mesh.shape_keys`, or `curve.shape_keys`/`lattice.shape_keys`) is **itself a separate `ID`
with its own `animation_data`** — same hidden-AnimData pattern as `NodeTree` above.
`bpy.types.Key` [4.3] — **[LIVE, 5.1.1]**
confirmed: `mesh.animation_data is None` while `mesh.shape_keys.animation_data` holds the real
Action (auto-named `"<MeshName>Action"`).

```python
mesh_obj.shape_key_add(name="Basis")
sk = mesh_obj.shape_key_add(name="Smile")
sk.value = 0.0
sk.keyframe_insert(data_path="value", frame=1)      # [LIVE] called directly on the ShapeKey struct
sk.value = 1.0
sk.keyframe_insert(data_path="value", frame=20)
```
`bpy.types.ShapeKey` [4.3]: `value`
(float, default range 0-1 via `slider_min`/`slider_max`, each independently rangeable to -10..10 for
overshoot poses), `mute`, `vertex_group` (paints where the key blends in), `relative_key` (which
other `ShapeKey` this one is measured relative to — default the `Basis`), `interpolation` (enum
`KEY_LINEAR | KEY_CARDINAL | KEY_CATMULL_ROM | KEY_BSPLINE` — **only meaningful in legacy
Absolute/sequence mode** driven by `Key.eval_time`, not the common relative-value workflow above,
where blending between poses is a plain per-vertex lerp by `.value`, not an F-Curve interpolation
setting). `Key.use_relative` (bool, default `True`) toggles relative-mode (the normal workflow)
vs. absolute/sequence mode using `Key.eval_time` (float) exactly like `Curve.eval_time` above.

---

## Pitfalls

1. **Action Slots + legacy API removal (5.0)** is the single biggest cross-version trap. Prefer
   `keyframe_insert`/`driver_add` for everything — they are unchanged 4.3→5.1. Only reach for
   `action.fcurves` directly if gating on `bpy.app.version < (4, 4, 0)`; otherwise use
   `action.fcurve_ensure_for_datablock(...)` (4.4+) or `bpy_extras.anim_utils` channelbag helpers (5.0+).
2. **`hide_viewport`/`hide_render` are keyframable ID-level properties** (**[LIVE]** confirmed);
   **`hide_get()`/`hide_set()` (the Outliner "eye" icon, per-view-layer state) are methods, not
   properties**, and **[LIVE]** raise `TypeError: property "hide_get()" not found` if you try to
   keyframe them — there is no way to animate that particular visibility toggle via keyframes.
3. Keyframing a **custom Python `PropertyGroup`** nested under a non-ID struct must be done from
   the owning **ID** with the full relative path (`arm.keyframe_insert('bones["B"].my_prop.x')`);
   built-in nested structs (PoseBone, NodeSocket, ShapeKey) can be keyed **directly** on the struct.
4. **Parent-inverse jump**: both plain `obj.parent = x` and `ChildOfConstraint` can leave the
   object visibly offset unless the inverse matrix is solved — **[LIVE-demonstrated]** exact
   numeric jump and fix for plain parenting; for Child Of, `bpy.ops.constraint.childof_set_inverse(...)`
   is the version-safe explicit fix (auto-solve-on-target-assignment was observed on 5.1.1 but is
   not confirmed as guaranteed behavior on 4.3).
5. Camera **aim axes**: `constraints.new('TRACK_TO')` already sets `TRACK_NEGATIVE_Z`/`UP_Y`
   (since 2.91), but a new Damped Track sets `TRACK_Y`, which does not aim a camera's view
   direction. Set `track_axis='TRACK_NEGATIVE_Z'` (and `up_axis='UP_Y'` on Track To) explicitly
   rather than relying on the initialiser or the static RNA doc defaults.
6. **Follow Path `offset_factor` only takes effect when `use_fixed_location=True`** — otherwise
   position is driven by the current scene frame through `Curve.path_duration`/`constraint.offset`.
7. Node-socket, shape-key and node-tree animation all live on a **nested ID's own
   `animation_data`** (`material.node_tree.animation_data`, `mesh.shape_keys.animation_data`), not
   the seemingly-obvious parent (`material.animation_data`, `mesh.animation_data` — both verified
   `None` in these cases).
8. `FCurveModifiers.new()`'s one-line doc description literally says *"Add a constraint to this
   object"* (copy-paste artifact from `ObjectConstraints.new()`) — trust the verified return type
   (`FModifier`) and behavior, not that sentence, when reading the raw docs.
9. `keyframe_insert`/`driver_add`'s `index` parameter renders as keyword-only in the `current` doc
   snapshot vs. plain positional-or-keyword in 4.3 — unconfirmed whether this is a real behavior
   change or just improved doc rendering; **always pass `index=`/`frame=` as keywords** regardless.
10. Only **one layer with one (infinite, unmovable) keyframe strip** is actually usable through
    5.1.1, despite the Action Slots data model nominally supporting many — don't design a rig
    around multi-layer blending inside a single Action yet.
11. **`bpy.ops.object.empty_add`'s documented default `scale=(0.0, 0.0, 0.0)` is a redo-panel
    artifact** — **[LIVE-verified]** created empties end up at `scale == (1, 1, 1)`; `radius` (not
    `scale`) controls visible size via `Object.empty_display_size`.
12. **F-Curve `CYCLES` and `SMOOTH` (Gaussian) modifiers are mutually exclusive** — both require
    being first in the modifier stack (to see raw keyframe positions), so a curve can have at most
    one of the two.
13. `FModifierNoise` was **reworked in Blender 4.4** (new `lacunarity`/`roughness`, old algorithm
    behind `use_legacy_noise`) and `FModifierSmooth` (Gaussian) is **new in Blender 5.1** and does
    not exist at all on 4.3 — `fcurve.modifiers.new(type='SMOOTH')` will simply fail there.
14. `ShaderNodeMix.data_type` lists `ROTATION` in its static `bl_rna` enum, but **[LIVE]** setting
    it inside a *shader* node tree raises a `TypeError` — only `FLOAT`/`VECTOR`/`RGBA` are valid
    there (`ROTATION` is Geometry-Nodes-only for this node type).
15. On `ShaderNodeMix`, `.inputs["A"]`/`["B"]`/`["Factor"]` name-lookup **does** resolve to the
    currently-enabled socket for the live `data_type` (**[LIVE-verified]**, not the naive
    first-in-list match) — but only if you set `data_type` *before* looking the socket up by name.
16. Since Blender 4.4, **removing a modifier, constraint, or shape key also deletes the drivers on
    that item's own properties** (for example a driver on a constraint's `influence`) — a driver
    you added earlier can silently disappear as a side effect of an unrelated cleanup step.

---

## Verified bpy snippets

Snippets marked **[LIVE]** were run in Blender 5.1.1. The others follow the Blender Python API
reference for the version named in the comment.

```python
# --- Basic transform keyframe --- [4.3 bpy_struct.keyframe_insert doc]
obj = bpy.context.object
obj.location = (3.0, 4.0, 10.0)
obj.keyframe_insert(data_path="location", frame=1)

# --- Version-portable "create or find" an FCurve without touching legacy action.fcurves --- [4.4+]
action = obj.animation_data.action
fc = action.fcurve_ensure_for_datablock(obj, "location", index=0)  # works 4.4 through 5.1.1 [LIVE]

# --- Set easing/handles on a freshly-inserted key --- [4.3 Keyframe/FCurveKeyframePoints docs]
fcurve = action.fcurve_ensure_for_datablock(obj, "location", index=2)
kf = fcurve.keyframe_points.insert(20, 5.0, keyframe_type='BREAKDOWN')
kf.interpolation = 'BACK'
kf.easing = 'EASE_OUT'
kf.back = 1.5          # overshoot amount, BACK easing only
fcurve.update()        # re-sort + fix handles after manual edits

# --- Camera shake via Noise modifier --- [4.3 FModifierNoise + 4.4 rework note]
cam = bpy.context.object
for axis in range(3):
    cam.keyframe_insert("rotation_euler", index=axis, frame=1)
# (insert at least one keyframe first so the fcurve exists, then:)
fcurve = cam.animation_data.action.fcurve_ensure_for_datablock(cam, "rotation_euler", index=0)
noise = fcurve.modifiers.new(type='NOISE')
noise.scale = 6.0      # lower = faster shake
noise.strength = 0.02  # radians
noise.phase = 0.0      # vary per axis so X/Y/Z don't wobble in lockstep

# --- Idle loop via Cycles modifier --- [4.3 FModifierCycles]
# Use its own F-curve and add CYCLES before any other modifier: it must be first in the list.
# The curve's first and last keys must share value and tangent for REPEAT to loop cleanly.
bob = obj.animation_data.action.fcurve_ensure_for_datablock(obj, "location", index=2)
bob.modifiers.new(type='CYCLES').mode_after = 'REPEAT'   # same motion again each cycle, no drift

# --- Camera aim + orbit rig --- [LIVE-verified empty_add/parenting]
bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.2, location=(0, 0, 1))
pivot = bpy.context.active_object
cam_obj.parent = pivot
cam_obj.matrix_parent_inverse = pivot.matrix_world.inverted()   # avoid the parenting jump [LIVE]
con = cam_obj.constraints.new(type='TRACK_TO')
con.target = pivot
con.track_axis = 'TRACK_NEGATIVE_Z'   # camera looks down local -Z
con.up_axis = 'UP_Y'
pivot.rotation_euler.z = 0
pivot.keyframe_insert("rotation_euler", index=2, frame=1)
pivot.rotation_euler.z = 6.283185307  # 2*pi
pivot.keyframe_insert("rotation_euler", index=2, frame=120)
spin = pivot.animation_data.action.fcurve_ensure_for_datablock(pivot, "rotation_euler", index=2)
for kp in spin.keyframe_points:
    kp.interpolation = 'LINEAR'                    # constant speed; Bezier would ease in and out each turn
spin.modifiers.new(type='CYCLES').mode_after = 'REPEAT_OFFSET'   # each turn continues from 2*pi

# --- Dolly along a path, most controllable form --- [4.3 FollowPathConstraint, LIVE-verified numerically]
con = cam_obj.constraints.new(type='FOLLOW_PATH')
con.target = path_curve_obj
con.use_fixed_location = True
con.forward_axis = 'FORWARD_Y'; con.up_axis = 'UP_Z'   # or set to match your rig's forward convention
con.offset_factor = 0.0
con.keyframe_insert(data_path="offset_factor", frame=1)
con.offset_factor = 1.0
con.keyframe_insert(data_path="offset_factor", frame=100)  # [LIVE] 0.5 landed exactly at the path midpoint

# --- Keyframe a Principled BSDF socket directly --- [LIVE, 5.1.1]
principled = material.node_tree.nodes["Principled BSDF"]
principled.inputs["Emission Strength"].default_value = 2.0
principled.inputs["Emission Strength"].keyframe_insert("default_value", frame=1)
# Action lives at: material.node_tree.animation_data.action  (NOT material.animation_data, which stays None) [LIVE]

# --- Wheel spins by distance traveled (driver beats keyframes) --- [LIVE, 5.1.1, numerically verified]
fcurve = wheel.driver_add("rotation_euler", 1)
drv = fcurve.driver
drv.type = 'SCRIPTED'
var = drv.variables.new(); var.name = "dist"; var.type = 'TRANSFORMS'
t = var.targets[0]; t.id = car_obj; t.transform_type = 'LOC_X'; t.transform_space = 'WORLD_SPACE'
drv.expression = "dist / 1.0"     # divide by the wheel radius in meters, written as a number

# --- Shape key value keyframe --- [LIVE, 5.1.1]
mesh_obj.shape_key_add(name="Basis")
sk = mesh_obj.shape_key_add(name="Smile")
sk.value = 0.0; sk.keyframe_insert(data_path="value", frame=1)
sk.value = 1.0; sk.keyframe_insert(data_path="value", frame=20)
# Action lives at: mesh_obj.data.shape_keys.animation_data.action [LIVE]

# --- Motion path arc audit, no viewport needed --- [LIVE, 5.1.1]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE')
positions = [p.co.copy() for p in obj.motion_path.points]   # world-space Vectors, ready for Python analysis
bpy.ops.object.paths_clear()

# --- Boolean/visibility keyframe: keep it CONSTANT so there's no ambiguous half-hidden frame ---
obj.hide_viewport = True
obj.keyframe_insert(data_path="hide_viewport", frame=30)
fc = obj.animation_data.action.fcurve_ensure_for_datablock(obj, "hide_viewport", index=0)  # non-array property: array_index 0
for kp in fc.keyframe_points:
    kp.interpolation = 'CONSTANT'
```

