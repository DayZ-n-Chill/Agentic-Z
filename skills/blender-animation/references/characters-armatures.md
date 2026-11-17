# Character and armature animation in Blender (bpy)

Bones, pose spaces, keyframing, Actions and the NLA, IK, cycles, baking and context overrides, for animation written as `bpy` code and run over the Blender MCP server.

Scope: authoring character/armature animation entirely through `bpy` code executed over the
MCP bridge (`execute_blender_code`), with no UI interaction available. Every API claim below
is cited to a doc URL; claims marked **[LIVE]** were additionally executed against a live,
connected Blender instance in the research session (not just read from docs).

Everything here is Blender behaviour, checked against Blender 5.1.1 and the Blender docs as
marked. None of it is a fact about the DayZ game, so nothing in this file cites `P:\`; the
DayZ side of the work is in `dayz-handoff.md`. "This session" below means the research
session of 2026-07-09 in which these facts were checked.

## Doc versions checked

- **Connected Blender instance (this session): 5.1.1** — confirmed live via `bpy.app.version == (5, 1, 1)`.
- The Blender MCP server's bundled Python API RST reference (`get_python_api_docs` /
  `search_api_docs`) ships for this same 5.1 install — e.g. the `ActionSlot` doc links
  `docs.blender.org/manual/en/5.1/animation/actions.html#action-slots` explicitly.
- **`docs.blender.org` blocked the WebFetch tool site-wide (HTTP 403) for every URL tried
  this session**, including the bare `/api/current/` index. All docs.blender.org citations
  below therefore come from one of: (a) the bundled MCP RST docs (`get_python_api_docs`/
  `search_api_docs`/`search_manual_docs` — full RST text, not snippets), which is the primary
  source for "current/5.1" facts, or (b) WebSearch results, which in this environment returned
  real extracted page text (not just link snippets) even though direct WebFetch failed — used
  mainly for historical/4.3-era pages and cross-checks.
- Where marked **[4.3]**, a fact comes from a 4.3-era or archived `docs.blender.org/api/...`
  page, or the official 4.4 migration notes on `developer.blender.org` — not executed live
  (no 4.3 instance was available to connect to).
- Where marked **[LIVE]**, the fact was executed this session against the connected 5.1.1
  instance via `execute_blender_code`, exclusively on newly created data-blocks that were
  either never linked into the scene or explicitly unlinked and removed in a `finally` block.
  Every cleanup was itself verified with a follow-up `bpy.data` existence check. No user scene
  data was read, selected, or modified beyond a transient, restored active-object/selection
  state during two tests that required Edit/Pose mode.
- **Action Slots / layered animation (the single biggest 4.3→4.4+ breaking change relevant to
  this skill)** are covered in detail in the Actions & NLA section, cited to the official
  `developer.blender.org/docs/release_notes/4.4/...` migration docs plus live confirmation that
  the legacy `Action.fcurves` accessor is gone entirely by 5.1.1.

## Workflow

Blocking → breakdowns → splining → polish maps onto concrete Blender mechanics, and Blender's
own keyframe-type vocabulary mirrors the traditional-animation terms almost 1:1 — this isn't
an analogy, it's a literal enum in the API.

**Blocking (pose-to-pose).** Key only the extreme/contact poses, spaced far apart, with
**stepped (constant) interpolation** so each pose holds fully until the next — this is how you
judge timing and silhouette before committing to in-betweens. Concretely:
- `keyframe_insert(..., keytype='EXTREME')` or `'KEYFRAME'` at sparse frames (contact poses).
- Force stepped playback by setting `Keyframe.interpolation = 'CONSTANT'` on every inserted
  key. Full enum (`bpy.types.Keyframe.interpolation`), **[LIVE]** read via
  `bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items`:
  `CONSTANT, LINEAR, BEZIER, SINE, QUAD, CUBIC, QUART, QUINT, EXPO, CIRC, BACK, BOUNCE, ELASTIC`.
- Blender's manual defines **Keyframe Types** for exactly this workflow
  (`manual/animation/keyframes/introduction.rst`, "Introduction > Keyframe Types"): *Keyframe*
  (normal), ***Breakdown*** ("Breakdown state, e.g. for transitions between key poses"),
  ***Moving Hold*** ("adds a small amount of motion around a holding pose"), ***Extreme***
  ("An 'extreme' state, or some other purpose as needed"), ***Jitter*** ("filler or baked
  keyframe for keying on ones"), ***Generated*** (tool-authored; safe to auto-remove/regenerate,
  e.g. by Copy Global Transform's "Fix to Camera"). This is the exact same enum as
  `keyframe_insert(..., keytype=...)` and `Keyframe.type` — **[LIVE]** confirmed identical:
  `['KEYFRAME', 'BREAKDOWN', 'MOVING_HOLD', 'EXTREME', 'JITTER', 'GENERATED']`.

**Breakdowns.** A breakdown pose is not the mathematical midpoint between two keys — it's
biased toward whichever extreme it "belongs" to (classic in-betweening). Blender ships
purpose-built pose operators that read the previous/next keyed pose and blend toward the
current frame by a factor, matching this workflow exactly (`bpy.ops.pose`, current):
- `breakdown(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FREE')` —
  "Create a suitable breakdown pose on the current frame."
- `push(...)` — exaggerate the current pose relative to the breakdown.
- `relax(...)` — pull the current pose toward its breakdown.
- `blend_to_neighbor(...)` / `blend_with_rest(...)` — same signature shape.

All five share an identical parameter shape: `factor` (0-1), `prev_frame`/`next_frame` (int,
the neighboring keyed frames), `channels` (`ALL|LOC|ROT|SIZE|BBONE|CUSTOM`), `axis_lock`
(`FREE|X|Y|Z`). Because these operators act on "current pose vs. keyed neighbors", they need a
real Pose-mode context (see Context overrides); a script can alternatively hand-author the same
blend by evaluating `Pose.apply_pose_from_action` / `Pose.blend_pose_from_action` directly and
skip the operator (and its context requirements) entirely. Tag the resulting keyframe with
`keytype='BREAKDOWN'` so later Dope Sheet/Graph Editor passes (and any downstream tooling) can
tell structural keys from breakdowns.

**Splining.** Switch from stepped to continuous curves and clean up arcs: iterate
`fcurve.keyframe_points`, set `kf.interpolation = 'BEZIER'`, and pick sane handle types
(`kf.handle_left_type` / `handle_right_type`, enum **[LIVE]** confirmed
`FREE, ALIGNED, VECTOR, AUTO, AUTO_CLAMPED`). `AUTO_CLAMPED` is the safe default that prevents
overshoot ("bump") artifacts on non-monotonic pose curves — the single most common cause of
ugly automatic tangents in scripted animation.

**Polish.** Per-curve handle nudges, `MOVING_HOLD` keys for held-pose micro-drift, and
staggered timing between body parts (arms/head trailing the hips) by offsetting individual
`Keyframe.co` per fcurve rather than moving whole poses — polish is inherently per-channel work,
which is exactly why it belongs at the F-Curve level rather than the whole-pose level.

*Sources: `manual/animation/keyframes/introduction.rst`; `bpy.types.Keyframe` (current);
`bpy.ops.pose` (current); live RNA enum introspection against Blender 5.1.1.*

## Posing & spaces (the matrix_basis story)

This is the part of the API that "trips everyone" — and it very nearly tripped this research
pass too (see the rotation-mode pitfall below), which is exactly why every claim here was
either read verbatim from the RNA doc text or executed live rather than recalled from memory.

### The four matrices

| Property | Space | Read/write | What it is |
|---|---|---|---|
| `Bone.matrix_local` | Armature (rest) | read-only | 4×4 **rest** matrix of the bone relative to the **armature**, not the parent. |
| `Bone.matrix` | Parent (rest) | read-only | 3×3 rest-orientation matrix relative to the parent. Rarely used directly by scripts. |
| `PoseBone.matrix_basis` | Local (relative to own rest + parent) | **read/write** | The literal composition of `location` + `rotation_quaternion`/`rotation_euler`/`rotation_axis_angle` + `scale` — i.e. exactly the channels keyframes drive. |
| `PoseBone.matrix` | **Armature object space** (not world!) | **read/write** | The final, on-screen pose after constraints and drivers — but still relative to the armature object's own origin, not the scene. |
| `PoseBone.matrix_channel` | Armature space, pre-constraint | read-only | Channels + drivers, but **before** constraints. Rarely needed. |

Exact doc text (`bpy.types.PoseBone`, current, matches connected 5.1.1):
- `matrix_basis`: *"Alternative access to location/scale/rotation relative to the parent and
  own rest bone."*
- `matrix`: *"Final 4×4 matrix after constraints and drivers are applied, in the armature
  object space."*
- `matrix_channel`: *"4×4 matrix of the bone's location/rotation/scale channels (including
  animation and drivers) and the effect of bone constraints"* — channel-only, pre-constraint,
  readonly.

**[LIVE]** verified the practical relationship: on a fresh 2-bone orphan armature, setting
`pose_bone.rotation_quaternion = Quaternion((0, 1, 0), radians(30))` then reading
`pose_bone.matrix_basis.to_quaternion()` gave `[0.966, 0, 0.259, 0]` — exactly
`cos(15°), 0, sin(15°), 0`, the half-angle quaternion for a 30° rotation about Y. Confirms
`matrix_basis` is a direct, literal composition of the channel properties; there is no hidden
extra transform baked in.

### matrix is armature-space, not world-space — the actual trap

`PoseBone.matrix` is documented as being in "the armature object space", which differs from
true world space whenever the armature object itself has a non-identity `matrix_world` (i.e.
almost always — parented, moved, or simply not at the scene origin). Reading/writing
`pose_bone.matrix` and expecting world-space coordinates is the single most common mistake.
The official conversion utility, called **on the armature object**, not the bone:

```
Object.convert_space(pose_bone=None, matrix=Matrix.Identity(4),
                      from_space='WORLD', to_space='WORLD') -> Matrix
```

`from_space`/`to_space` accept `'WORLD' | 'POSE' | 'LOCAL_WITH_PARENT' | 'LOCAL'` (the
constraint-space enum minus `'CUSTOM'`). `'POSE'` space is the same space as `PoseBone.matrix`
— per the manual's own Constraint "Space Types" definition (`manual/animation/constraints/
interface/common.rst`): *"Pose Space (Bones Only): Use the transformation relative to the
armature object."* **[LIVE]** verified callable: `arm_obj.convert_space(pose_bone=pb1,
matrix=pb1.matrix, from_space='POSE', to_space='WORLD')` returns a `mathutils.Matrix`.

Practical recipe:
```python
# Bone -> true world matrix
world_mat = arm_obj.convert_space(pose_bone=pb, matrix=pb.matrix,
                                   from_space='POSE', to_space='WORLD')
# True world target -> local channel assignable to matrix_basis
local_mat = arm_obj.convert_space(pose_bone=pb, matrix=world_target,
                                   from_space='WORLD', to_space='LOCAL')
pb.matrix_basis = local_mat
```

### Setting a pose: three different tasks, three different techniques

1. **Normal procedural/keyframed posing (the large majority of cases): just set the
   channels.** Assign `pose_bone.location` / `.rotation_quaternion` (or `.rotation_euler`) /
   `.scale` directly. Blender composes `matrix_basis` for you. Do not hand-build a
   `matrix_basis` unless you have a specific reason — it is more error-prone and buys nothing
   for ordinary posing.

2. **You have a target pose expressed as an armature-space matrix** (replaying a per-frame
   solve, matching another rig, etc.) — assign directly to `.matrix` (after converting to
   POSE/armature space if it started in world space), then force a dependency update:
   ```python
   pose_bone.matrix = target_matrix
   bpy.context.view_layer.update()
   ```
   This exact pattern is Blender's own documented idiom — the official
   `PoseBone.bbone_segment_matrix` example literally comments *"Instead of: `pbone.matrix =
   matrix` / `bpy.context.view_layer.update()`"* before presenting the batch alternative (next
   point). **Caveat:** assigning `.matrix` back-solves `matrix_basis` using the parent/
   constraint state **at that instant**. It is not a live link — change a parent bone or a
   constraint afterward without re-assigning, and the previously baked `matrix_basis` will not
   adjust itself.

3. **Setting a whole-body pose in one pass, without paying for a `view_layer.update()` per
   bone** (each is a full depsgraph re-evaluation): walk the hierarchy root→leaf and use the
   pure-math conversion `Bone.convert_local_to_pose(matrix, matrix_local, parent_matrix=...,
   parent_matrix_local=..., invert=True)`, documented as *"Unlike `Object.convert_space`, this
   uses custom rest and pose matrices provided by the caller"* — meaning it needs no depsgraph
   evaluation at all; you feed it the parent's *already-computed* pose matrix from earlier in
   your own recursive walk. This is Blender's own documented pattern for exactly this problem
   (see snippet 4 below, reproduced verbatim from the `Bone.convert_local_to_pose` docs).

### Bone spaces glossary (owner_space / target_space / convert_space)

Straight from the manual (`manual/animation/constraints/interface/common.rst`, "Common > Space
> Space Types" — the authoritative definition used everywhere Blender lets you pick a space,
not just constraints):
- **World Space** — relative to the world axes.
- **Custom Space** — relative to an arbitrary object/bone (constraints only; not on
  `convert_space`).
- **Pose Space** *(bones only)* — relative to the armature object.
- **Local Space** — for a bone: relative to its rest state, *after* that rest state was
  transformed by the bone's ancestors (what the Properties editor shows in Pose Mode if the
  bone has no other constraints).
- **Local With Parent** *(bones only)* — relative to the bone's rest state, but *including*
  the rotation/location difference caused by rotating ancestor bones (unlike plain Local
  Space).
- **Local Space (Owner Orientation)** *(bone targets only)* — Local Space of the target,
  re-oriented to match the owner's rest orientation, so a Copy-Rotation-style constraint
  reproduces the same *armature-space* motion regardless of each bone's individual rest
  orientation.

`Constraint.owner_space` / `Constraint.target_space` expose the full enum
(`WORLD, CUSTOM, POSE, LOCAL_WITH_PARENT, LOCAL`, plus `LOCAL_OWNER_ORIENT` on `target_space`
only). `Object.convert_space` exposes the four-value subset without `CUSTOM`/
`LOCAL_OWNER_ORIENT`.

### Rotation modes and gimbal lock

`PoseBone.rotation_mode` default is `'QUATERNION'` (doc text + **[LIVE]** RNA enum:
`['QUATERNION', 'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX', 'AXIS_ANGLE']`). Recommendation for a
scripted rig:
- **Ball-and-socket joints** (shoulders, hips, spine) → keep **Quaternion**. No gimbal lock,
  but two caveats: (a) no single keyable "twist" axis for manual graph-editor polish; (b) the
  **double-cover problem** — `Q` and `-Q` represent the identical rotation but interpolate
  completely differently between keyframes, producing sudden flips. Blender ships
  `bpy.ops.pose.quaternions_flip()` ("Flip quaternion values to achieve desired rotations,
  while maintaining the same orientations") specifically to fix this after the fact;
  `mathutils.Quaternion.make_compatible(other)` is the scriptable, pre-emptive equivalent
  (call against the previous keyframe's quaternion before inserting a new one, to keep the
  shortest/consistent interpolation path).
- **Hinge-like joints** (elbows, knees, fingers) with one dominant axis → **Euler**, ordered
  so the least-animated axis is evaluated innermost — gives per-axis graph-editor curves
  (what you want for hand-polish), at the cost of gimbal lock if two axes align 90° apart
  mid-animation (a real risk on shoulders — avoid Euler there).

**[LIVE] Pitfall confirmed by direct test, not by memory:** calling
`bpy.ops.pose.rotation_mode_set(type='XYZ')` (the operator) correctly converts the **current
pose value** (quaternion → equivalent Euler, read back exactly as expected: 40° about Y in,
`[0, 40, 0]` Euler-degrees out) but does **not** retroactively touch existing F-Curves — the
old `rotation_quaternion` F-Curve is left in the action untouched, and no new
`rotation_euler` F-Curve is created until the next explicit `keyframe_insert`. Directly
assigning `pose_bone.rotation_mode = 'XYZ'` (data API, no operator) never touches F-Curves at
all, since a plain property assignment isn't an animation operation. **Practical rule: decide
each bone's rotation_mode before keying anything; never change rotation_mode mid-production on
an already-keyed bone without a manual re-key pass in the new mode.**

*Sources: `bpy.types.PoseBone` / `Bone` / `Object` (current, bundled docs matching connected
5.1.1); `bpy.types.Constraint` (current); `manual/animation/constraints/interface/common.rst`;
`bpy.ops.pose` (current); `mathutils.Quaternion` (current); live execution against Blender
5.1.1, this session.*

## Keyframing

**Primary API: `bpy_struct.keyframe_insert`** (inherited by every ID/nested struct, including
`PoseBone`, `Object`, `Action`, etc.):
```
keyframe_insert(data_path, *, index=-1, frame=bpy.context.scene.frame_current,
                group="", options=set(), keytype='KEYFRAME') -> bool
```
[`bpy.types.bpy_struct.keyframe_insert`, current] Every parameter verified against the doc
text:
- `data_path` — RNA path to the property, e.g. `"rotation_quaternion"` called **on the
  PoseBone itself**, or `'pose.bones["Bone1"].rotation_quaternion'` when constructing a path
  by hand for the owning object/Armature ID — see the nested-property gotcha below, the
  distinction matters and is explicit in the official docs.
- `index=-1` — default keys **all** array indices (e.g. all 4 quaternion or 3 location/Euler
  components) in one call; pass a specific index to key a single channel.
- `frame=bpy.context.scene.frame_current` — **this directly answers "insert at a specific
  frame without moving the playhead": pass `frame=N` explicitly.** `scene.frame_current` is
  only the *default* value used when `frame` is omitted; the call never touches the actual
  current-frame state itself.
- `group` — F-Curve/Action Group name (cosmetic grouping in Dope Sheet/Graph Editor).
- `options` — a set of flags: `INSERTKEY_NEEDED` (only insert where the value actually
  changes), `INSERTKEY_VISUAL` (key the *final*, constraint-evaluated transform instead of the
  raw channel — the data-level equivalent of "Visual Keying"), `INSERTKEY_REPLACE` (only
  overwrite existing keys, never add new ones), `INSERTKEY_AVAILABLE` (only insert into F-Curves
  that already exist), `INSERTKEY_CYCLE_AWARE` (respect cyclic extrapolation when inserting).
- `keytype` — one of `'KEYFRAME'|'BREAKDOWN'|'MOVING_HOLD'|'EXTREME'|'JITTER'|'GENERATED'`
  (see Workflow — this is literally the blocking/breakdown/polish vocabulary as a first-class
  enum). **[LIVE]** enum confirmed.

**Nested-property gotcha, straight from the official example**
(`bpy.types.bpy_struct.keyframe_insert` docs, example 2): *"Note that when keying data paths
which contain nested properties this must be done from the ID subclass, in this case the
Armature rather than the bone."* **[LIVE]** independently re-confirmed: after
`pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=1)` (called directly on the
PoseBone, which resolves correctly because PoseBone can find its own owning `id_data`), the
resulting F-Curve's `data_path` reads `pose.bones["Bone1"].rotation_quaternion` and lives on
the **object's** action (`arm_obj.animation_data.action`) — bones are never independently
keyable IDs; every bone F-Curve is always rooted at the owning **Object**.

**Lower-level alternative: `FCurve.keyframe_points.insert(frame, value, *, options=set(),
keyframe_type='KEYFRAME')`** [`bpy.types.FCurveKeyframePoints.insert`, current] — inserts one
scalar point directly on an already-obtained F-Curve. Its `options` are a *different*, smaller
set than `keyframe_insert`'s: `REPLACE`, `NEEDED`, `FAST` (skip curve resort/recalc on every
insert — batch inserts should use `FAST` then call `fcurve.update()`/`.keyframe_points.sort()`
once at the end; the sibling methods `sort()`, `deduplicate()`, `handles_recalc()` exist
specifically to support this deferred-recalculation workflow). Use this when you already hold
the target F-Curve (e.g. via `action.fcurve_ensure_for_datablock(...)`, see Actions & NLA) and
want to avoid `keyframe_insert`'s per-call data-path string resolution across hundreds of keys.

**Keying Sets** (`bpy.types.KeyingSet`, `Scene.keying_sets` / `keying_sets_all`) bundle
multiple data-paths so one call keys "everything a rig needs." Blender ships a built-in
**Whole Character** keying set for exactly this — manual (`animation/keyframes/
keying_sets.rst`): *"made to keyframe all properties that are likely to get animated in a
character rig,"* and it explicitly skips bones whose name starts with prefixes reserved for
non-animatable technical/Rigify-generated bones. From a script, `bpy.ops.anim.keyframe_insert
(type='DEFAULT')` uses the *active* keying set (or user preferences if none is active);
`bpy.ops.anim.keying_set_active_set(type=...)` switches it first. For agent-authored scripts,
per-bone explicit `keyframe_insert()` calls are simpler to reason about and do not depend on
scene-level keying-set state — prefer them unless "key everything the rig defines" in one shot
is specifically what's needed.

**`bpy_extras.anim_utils.AutoKeying`** [`bpy_extras.anim_utils`, current] is the internal
helper that Blender's own auto-key system and the "Copy Global Transform" add-on use; it is
public/importable and exposes `options(...)` (context manager forcing a keytype/loc/rot/scale
selection), `key_transformation(context, target)`, and `keyframe_channels(...)`
(locked-channel-aware insertion). It is the "correct" way to *deliberately replicate* auto-key
behavior from a script — see the Auto-keying pitfall below for why that is preferable to
toggling the scene setting.

## Actions & NLA

**Version-critical background — check this before writing any Action-touching code.**
Blender 4.4 introduced **layered Actions** with **Action Slots**
(`developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/`,
`.../4.4/python_api/`, `.../docs/features/animation/animation_system/layered/`). An Action is
no longer a flat bag of F-Curves; the structure is
`Action.layers[ActionLayer].strips[ActionStrip → ActionKeyframeStrip].channelbags
[ActionChannelbag (keyed by slot)].fcurves`. A **slot** (`bpy.types.ActionSlot`) identifies
*which datablock* a subset of the Action's channels belongs to — this is what lets one Action
drive multiple objects/bone-sets in the new model. Every animated ID gets `AnimData.action_slot`
alongside `AnimData.action`.

- **4.3 and earlier [4.3]:** `Action.fcurves` is a **direct** collection (`ActionFCurves`):
  `action.fcurves.new(data_path, index=0, action_group="")` / `.find(data_path, index)`. No
  slots, no layers.
- **4.4 [4.3]:** layered model introduced; the old `action.fcurves`/`action.groups` accessors
  are kept as a **"backward-compatible legacy API,"** explicitly marked deprecated in the
  official migration notes.
- **5.0+ — confirmed [LIVE] on the connected 5.1.1 instance:** the legacy `Action.fcurves`
  accessor is **gone** — `hasattr(bpy.data.actions.new("x"), "fcurves")` returns `False`. Code
  written against 4.3's `action.fcurves.new(...)` will raise `AttributeError` on 5.1.

**The version-safe pattern (works unchanged on 4.3 → 5.1): never touch `action.fcurves`
directly.** Use the high-level per-ID API:
```python
obj.keyframe_insert(data_path="location", index=0, frame=1)   # or pose_bone.keyframe_insert(...)
```
This transparently creates `animation_data` + `Action` + (on 4.4+) the slot/layer/strip/
channelbag, or (on 4.3) the flat fcurve — confirmed by the official `ActionSlot` doc's own
first example: *"Create animation data and an action... Slot will be automatically created."*
**[LIVE]** re-confirmed: after one `keyframe_insert` call, `action.is_action_legacy == False`,
`len(action.slots) == 1`, `len(action.layers) == 1`, and the slot's `identifier` was
auto-set to `"OBVerifyTestArmatureObj"` (an `"OB"` prefix + the object name — matches the
documented *"Identifiers start with a prefix based on the ID type, e.g. 'OB' for objects"*).

If a specific F-Curve is needed (not just "insert one keyframe"), the 4.4+-safe call is:
```python
fcurve = action.fcurve_ensure_for_datablock(datablock, data_path, index=0, group_name="")
```
[`bpy.types.Action.fcurve_ensure_for_datablock`, current] — *"Ensure that an F-Curve exists...
This function will also create the layer, keyframe strip, and action slot if necessary, and
take care of assigning the action slot too."* **[LIVE]** verified working. For a skill that
must run identically on Blender 4.3 and 5.1 installs, guard with
`hasattr(action, "fcurve_ensure_for_datablock")` and fall back to
`action.fcurves.find(...)`/`action.fcurves.new(...)` on the legacy branch — do not hardcode a
`bpy.app.version` tuple check, since the exact minor version this method first shipped in was
not independently verified in this research pass.

**Creating/assigning an Action:**
```python
action = bpy.data.actions.new("WalkCycle")   # BlendDataActions.new(name) -> Action
obj.animation_data_create()                    # ID.animation_data_create() -> AnimData | None
obj.animation_data.action = action             # AnimData.action
```
[`bpy.types.BlendDataActions.new`, `bpy.types.ID.animation_data_create`,
`bpy.types.AnimData.action` — all current, all **[LIVE]** exercised this session.]

**Fake users & "the action getting lost."** An `Action` (like any `ID`) is garbage-collected
on file reload/save once its user count drops to 0 — e.g. after `nla.action_pushdown` or
`nla.tweakmode_exit`, or after unassigning `AnimData.action`, an Action with no NLA strip
referencing it and no other user silently disappears at next load. `Action.use_fake_user`
(inherited from `ID.use_fake_user`) pins it. `bpy.ops.anim.clear_useless_actions
(only_unused=True)` is Blender's own janitor operator for the opposite case (deliberately
dropping actions with zero F-Curves). A pipeline script that builds a library of reusable
cycle actions should set `use_fake_user = True` immediately after creation, before anything
else can early-return/error and leave it orphaned.

**NLA — tracks and strips (pure data API, no operator needed for basic assembly):**
```python
track = obj.animation_data.nla_tracks.new()                 # NlaTracks.new(prev=None) -> NlaTrack
strip  = track.strips.new("WalkCycleStrip", start, action)  # NlaStrips.new(name, start, action) -> NlaStrip
```
[`bpy.types.NlaTracks.new`, `bpy.types.NlaStrips.new` — current, **[LIVE]** exercised.]
`strip.frame_end` is computed automatically from the action's frame range at creation time.
Key `NlaStrip` fields for layering (current API, all individually verified): `blend_type`
(`REPLACE|COMBINE|ADD|SUBTRACT|MULTIPLY`), `influence` (0-1), `extrapolation`
(`NOTHING|HOLD|HOLD_FORWARD`), `action_frame_start`/`action_frame_end` (source range inside the
action), `repeat` (float — see Cycles), `use_reverse`, `mute`. The equivalent one-shot operator
for "take the active action and push it down as a new strip" is
`bpy.ops.nla.action_pushdown(track_index=-1)`.

**Tweak mode** (edit an NLA strip's action in place, in context):
`bpy.ops.nla.tweakmode_enter(isolate_action=False, use_upper_stack_evaluation=False)` /
`bpy.ops.nla.tweakmode_exit(isolate_action=False)`. `AnimData.use_tweak_mode` mirrors the state
at the data level; `AnimData.action_tweak_storage` holds the action that was active before
entering tweak mode.

*Sources: `developer.blender.org` 4.4 release notes (Animation & Rigging, Python API, Slotted
Actions upgrade guide) and 5.0 Python API notes; `bpy.types.Action` / `ActionSlot` /
`ActionSlots` / `ActionLayer` / `ActionKeyframeStrip` / `ActionChannelbag` / `AnimData` /
`NlaTrack(s)` / `NlaStrip(s)` (current, bundled docs matching connected 5.1.1); live execution,
this session.*

## IK/FK

**Creating an IK constraint is pure data API — no operator, no context needed:**
```python
ik = pose_bone.constraints.new(type='IK')   # PoseBoneConstraints.new(type) -> Constraint (a KinematicConstraint)
```
[`bpy.types.PoseBoneConstraints.new`, current.] **[LIVE]** verified:
`type(ik).__name__ == 'KinematicConstraint'`; the literal string `'IK'` is confirmed present in
the live constraint-type enum read via
`bpy.types.Constraint.bl_rna.properties["type"].enum_items` →
`[..., 'DAMPED_TRACK', 'IK', 'LOCKED_TRACK', 'SPLINE_IK', ...]`. The equivalent UI/operator
path is `bpy.ops.pose.ik_add(with_targets=True)` ("Add an IK Constraint to the active Bone. The
target can be a selected bone or object") — prefer the data-API `.constraints.new('IK')` form
in scripts, since it has zero context/selection requirements.

**Key `KinematicConstraint` fields** (`bpy.types.KinematicConstraint`, current, each
individually verified against the bundled docs):
- `chain_count: int` — *"How many bones are included in the IK effect - 0 uses all bones."*
  `chain_count=2` on the end-effector bone gives a classic 2-bone arm/leg chain (that bone plus
  its parent).
- `target: Object`, `subtarget: str` — the IK goal; `subtarget` is a bone name on `target` (or
  a vertex group if `target` is a mesh), left `""` when `target` is a plain Object such as an
  Empty.
- `pole_target: Object`, `pole_subtarget: str`, `pole_angle: float` (radians, range ±π) — the
  pole/knee vector.
- `iterations: int` (0-10000), `use_stretch: bool`, `use_tail: bool` ("Include bone's tail as
  last element in chain"), `use_location`/`use_rotation: bool` ("Chain follows position/
  rotation of target"). Per-axis IK limits/stiffness (`lock_ik_x/y/z`, `ik_stiffness_x/y/z`,
  `ik_min/max_x/y/z`) live on `PoseBone`, not on the constraint itself.
- `ik_type: Literal['COPY_POSE', 'DISTANCE']` — **[LIVE]** confirmed only these two values
  exist; `'COPY_POSE'` is the default/standard chain-to-target mode, `'DISTANCE'` is the
  "stay within/outside/on a sphere" mode (paired with `distance`/`limit_mode`).

**IK target: animate the empty/bone, not the chain's FK rotations.** Once an IK constraint
exists, keyframe the **target object** (commonly an Empty) location/rotation — the constrained
bones' final pose comes from the solver and should not be keyframed directly (their
`rotation_quaternion`/`location` channels are meaningless while the IK constraint is driving
`.matrix`). If the IK result must be baked onto the bones' own channels (e.g. to disable the
constraint later, or to export FK-only data), that is exactly what Visual Keying/baking is for
(see Baking): `keyframe_insert(options={'INSERTKEY_VISUAL'})` per frame, or
`bpy.ops.nla.bake(visual_keying=True, clear_constraints=True, ...)` in bulk.

**IK/FK switching (arms vs. legs — a rigging pattern, not a dedicated bpy API):** the common
setup is two parallel bone chains (an IK chain with the constraint, a separate FK chain with
plain rotations) driven into one deform chain via Copy Rotation/Copy Transforms constraints
whose `influence` is wired to a single 0-1 "IK/FK blend" custom property. There is no Blender
operator that performs the switch generically; a script implements it by (1) matching one
chain's rotations to the other's current solved pose (via `Pose.apply_pose_from_action` or a
direct `matrix` read/convert), then (2) animating the blend property and the relevant
`Constraint.influence` F-Curves. Legs are almost always IK (foot planting/contact needs a
stable world-space target); arms are more often FK for broad acting poses, with IK reserved for
hand-plant/prop-interaction shots — this is a workflow convention, not an API distinction.

*Sources: `bpy.types.KinematicConstraint` / `PoseBoneConstraints` / `Constraint` (current,
bundled docs + **[LIVE]** enum introspection); `bpy.ops.pose.ik_add` (current);
`manual/animation/constraints/tracking/ik_solver.rst` (5.1).*

## Cycles

**Walk/run cycle breakdown** (traditional-animation craft knowledge — cited to animation
references, not `docs.blender.org`). The
canonical 4-pose breakdown per step is **Contact → Down → Passing → Up**, then Contact again
on the opposite foot. At 24 fps a standard walk is commonly blocked as a 24-frame full cycle
(two steps = one second): contact poses at frames 0/12/24, with down/passing/up spaced at
roughly 3-frame increments within each contact-to-contact half-cycle. Faster/lighter walks and
runs compress this — a run cycle is commonly 8-16 frames total, sometimes collapsing the
"double contact" phase entirely into a single flight/passing-dominant silhouette. Treat these
counts as a starting ratio to retime against reference, not a fixed law.

**Mirroring poses in Blender (the "paste flipped" equivalent, reachable from Python):**
- `bpy.ops.pose.copy()` then `bpy.ops.pose.paste(flipped=True, selected_mask=False)` —
  *"Paste the stored pose flipped on to current pose."* Direct Python-reachable equivalent of
  the UI's Paste Pose Flipped.
- `bpy.ops.pose.select_mirror(only_active=False, extend=False)` — selects the mirrored bone
  set (relies on Blender's `.L`/`.R` or `_L`/`_R` naming-convention auto-detection) without
  changing any pose; useful before a manual flip.
- `bpy.ops.pose.flip_names(do_strip_numbers=False)` — flips left/right *name* suffixes only,
  no pose change.
- `bpy.ops.pose.quaternions_flip()` — not mirroring; fixes the double-cover interpolation
  artifact (see Posing & spaces).
- For a fully scripted mirror without the clipboard operators — e.g. building a symmetric pose
  programmatically from one side, or flipping an entire baked action — `Action.flip_with_pose
  (object)` (*"Flip the action around the X axis using a pose"*, current API on `Action`,
  taking the reference armature object as its argument) is the documented one-call path,
  useful for generating e.g. a "left-lead" walk variant from a "right-lead" one.

**Looping a cycle (two independent, composable mechanisms — verified live to interact
correctly):**
1. **Action-level intent flags:** `Action.use_frame_range = True` + `frame_start`/`frame_end`
   marks the action's *intended* playback range; `Action.use_cyclic = True` marks it as
   "intended to be used as a cycle" — the doc is explicit that **enabling this alone does not
   make anything loop**, it is a flag other tools/exporters read, and it feeds the
   `INSERTKEY_CYCLE_AWARE` keying option.
2. **NLA-strip-level (the actual repetition mechanism):** `NlaStrip.repeat: float`
   (0.1-1000, default 1.0). **[LIVE]** verified: creating a strip from a 12-frame action
   (frames 1-13) and setting `strip.repeat = 4.0` automatically recalculated `strip.frame_end`
   from `13` to `49` (`1 + (13-1)*4`) — the strip now plays the action four times back-to-back
   from a single float assignment. `NlaStrip.extrapolation` (`NOTHING|HOLD|HOLD_FORWARD`)
   controls what happens *past* the strip's own extent, independent of `repeat` (which controls
   repetition *within* the strip).

For a walk-cycle pipeline: author one 12-24 frame loop action with `use_cyclic=True` and a
matching `frame_start`/`frame_end`, push it to an NLA strip, and drive distance/speed by
adjusting `strip.repeat` (or `strip.scale` — *"Scaling factor for action"*, range
0.0001-1000, which retimes the same frame range faster/slower) rather than re-authoring keys.

*Sources: `bpy.types.Action` (`use_cyclic`, `use_frame_range`, `flip_with_pose`) /
`NlaStrip` (`repeat`, `scale`, `extrapolation`) — current, **[LIVE]** exercised;
`bpy.ops.pose` (copy/paste/select_mirror/flip_names/quaternions_flip) — current;
animation-craft references (not Blender API): rustyanimator.com "Walk Cycle Animation
Blueprint", animationmentor.com human-walk-cycle tutorial.*

## Baking

Two different, non-interchangeable baking entry points.

**1. Operator: `bpy.ops.nla.bake(...)`** — for use when a normal pose-mode/object-mode context
(selection, active object) is already set up.
```
bpy.ops.nla.bake(frame_start=1, frame_end=250, step=1, only_selected=True, visual_keying=False,
                  clear_constraints=False, clear_parents=False, use_current_action=False,
                  clean_curves=False, bake_types={'POSE'},
                  channel_types={'BBONE', 'LOCATION', 'PROPS', 'ROTATION', 'SCALE'})
```
[`bpy.ops.nla.bake`, current — the bundled docs cite the exact source location:
`bl_operators/anim.py:274`, in the `scripts/startup` folder of the Blender source on
`projects.blender.org`.] Parameters that change
behavior meaningfully: `visual_keying=True` bakes the **final, constraint-evaluated** transform
(what you want when baking an IK chain down to plain FK keys); `clear_constraints=True` removes
constraints after baking, and the docs explicitly warn *"To get a correct bake with this
setting Visual Keying should be enabled"* — baking raw channels and then deleting the
constraint that was producing the real motion freezes the pre-constraint pose;
`use_current_action=True` bakes into the existing action instead of creating a new one (needed
when baking only a subset of bones in an armature that already has other animated bones);
`bake_types={'POSE'}` vs. `{'OBJECT'}` selects bone vs. object transforms — not mutually
exclusive, pass both to bake an animated object with animated bones in one call.

**2. Pure-Python module: `bpy_extras.anim_utils.bake_action(obj, *, action, frames,
bake_options)`** — for calling from a script **without any operator context at all** (no
active object / selection / mode requirement — the object is passed explicitly).
```python
from bpy_extras import anim_utils
opts = anim_utils.BakeOptions(
    only_selected=False, do_pose=True, do_object=False,
    do_visual_keying=True, do_constraint_clear=False, do_parents_clear=False,
    do_clean=False, do_location=True, do_rotation=True, do_scale=True,
    do_bbone=False, do_custom_props=False,
)
new_action = anim_utils.bake_action(obj, action=None, frames=range(1, 25), bake_options=opts)
```
**[LIVE]** verified this exact call shape via `inspect.signature` →
`(obj, *, action, frames, bake_options)`, and confirmed `BakeOptions` is a **dataclass with 12
required fields and no defaults** (`only_selected, do_pose, do_object, do_visual_keying,
do_constraint_clear, do_parents_clear, do_clean, do_location, do_rotation, do_scale, do_bbone,
do_custom_props`) — constructing it with zero arguments raises
`TypeError: missing 12 required positional arguments`. `action=None` bakes into a **new**
Action; pass an existing one to bake in place. `frames` accepts any int iterable (not just a
start/end/step triple) — e.g. `range(1, 25)` or an explicit sparse frame list, which the
operator form cannot do (it only accepts a contiguous start/end/step range).

Sibling coroutine variants exist for baking many objects together while yielding per-frame
(useful for a progress callback or interleaving with other per-frame work, without Blender's
own modal-operator loop): `bake_action_objects(object_action_pairs, *, frames, bake_options)`,
`bake_action_iter(obj, *, action, bake_options)`,
`bake_action_objects_iter(object_action_pairs, bake_options)`.

**When to use which:** the pure-Python `anim_utils.bake_action` is almost always the better
choice for an MCP/agent-driven script — it sidesteps every context-override problem in the next
section. Reach for the `bpy.ops.nla.bake` operator only when its UI-level side effects are
specifically wanted (e.g. it also drives NLA strip/track placement automatically) or when
baking is a direct translation of a recorded user macro.

*Sources: `bpy.ops.nla.bake` (current, with `projects.blender.org` source citation embedded in
the bundled docs); `bpy_extras.anim_utils` (current) — signature and dataclass shape
**[LIVE]**-verified against the connected 5.1.1 instance via `inspect.signature`/
`__dataclass_fields__`.*

## Context overrides

Most `bpy.ops.*` calls used above (`pose.breakdown`, `pose.paste`, `nla.action_pushdown`,
`object.mode_set`, ...) are **operators**: they read ambient `bpy.context` (active object,
mode, selection, active area/region) through a `poll()`/`execute()` pair designed for
interactive use, and raise `RuntimeError: Operator bpy.ops.X.Y poll() failed, context is
incorrect` when run from a background script if that context is not right.

**`bpy.context.temp_override(*, window=None, screen=None, area=None, region=None,
**keywords)`** [`bpy.types.Context.temp_override`, current] is a context manager that
temporarily patches arbitrary context members (not only the four named ones — `**keywords`
accepts any context attribute, confirmed by the official example passing
`selected_objects=my_objects`) for the duration of a `with` block, restoring the previous
values automatically — including on exception. Two official example shapes (verbatim from the
docs):
```python
# Redirect an operator to a specific window (e.g. running headless / no active window yet)
with context.temp_override(window=window):
    bpy.ops.mesh.primitive_uv_sphere_add()
    bpy.ops.object.mode_set(mode='EDIT')

# Override selection/active-object without touching the user's real selection
my_objects = [context.scene.camera]
with context.temp_override(selected_objects=my_objects) as override:
    bpy.ops.object.delete()
```
It also has a debugging hook: `override.logging_set(True, hide_missing=True)` inside the
`with` block prints every context member an operator actually reads — the fastest way to
discover what a failing operator needs, rather than guessing.

**Practical rule for this skill:** prefer `temp_override(active_object=..., selected_objects=
..., selected_pose_bones=...)` (or whichever members a specific operator's poll needs) over
manually mutating `view_layer.objects.active`/`obj.select_set(True)` and restoring them by hand
afterward — `temp_override` guarantees restoration even if the operator raises, whereas a
hand-rolled `try/finally` restore is one more place to introduce a bug (this session's own test
script had exactly such a bug — see Pitfalls).

**Real mode changes are not overridable this way.** `context.mode` is *derived from*
`active_object.mode`; there is no `temp_override(mode='POSE')` that fakes being in Pose Mode
without the object actually being in it. `bpy.ops.object.mode_set(mode='POSE')` genuinely
changes `obj.mode` and is not a pure context override. **[LIVE]** exercised repeatedly this
session (`mode_set(mode='EDIT')` to build bones via `armature.edit_bones`,
`mode_set(mode='POSE')` to select/pose bones and run `pose.rotation_mode_set`), always on a
freshly created, unlinked-until-tested object, always restored to `OBJECT` mode and the prior
active object/selection afterward.

**Which tasks are better done with pure data API (no operator, no context problem at all):**
- Creating constraints: `pose_bone.constraints.new(type=...)` — a plain collection method,
  works regardless of mode/selection/active object.
- Creating actions/NLA tracks/strips: `bpy.data.actions.new(...)`,
  `anim_data.nla_tracks.new()`, `track.strips.new(...)` — all plain data API.
- Keyframing: `obj.keyframe_insert(...)` / `pose_bone.keyframe_insert(...)` /
  `fcurve.keyframe_points.insert(...)` — plain data API (also why explicit keyframing is
  preferable to driving everything through `bpy.ops.anim.keyframe_insert()`, which depends on
  the active Keying Set).
- Baking: `bpy_extras.anim_utils.bake_action(obj, ...)` — takes the object as an argument; no
  ambient context needed at all (see Baking).
- Reading/writing poses: `pose_bone.matrix`/`.matrix_basis`, `Bone.convert_local_to_pose(...)`,
  `Object.convert_space(...)` — pure math, no context.

Operators remain the right (or only) tool for: breakdown/push/relax pose-blending
(`bpy.ops.pose.*` — these specifically operate on "current pose vs. neighboring keyed poses",
which has no plain data-API equivalent), mirroring via the pose clipboard
(`pose.copy`/`pose.paste`), and switching Edit/Pose/Object mode itself.

*Sources: `bpy.types.Context.temp_override` (current, both official examples reproduced
above); live execution this session (mode_set + edit_bones + pose selection, all on isolated
orphan data-blocks, fully cleaned up and verified removed).*

## Pitfalls

Ranked by how likely each is to bite a script that "looks correct" and silently produces wrong
animation:

1. **`PoseBone.matrix` is armature-object space, not world space.** Confusing the two is
   invisible until the armature object itself is moved/parented away from the world origin, at
   which point every "world-space" placement computed from raw `pose_bone.matrix` is offset by
   the armature's own transform. Fix: `Object.convert_space(pose_bone=pb, matrix=m,
   from_space='POSE', to_space='WORLD')` (verified callable **[LIVE]**).

2. **Changing `rotation_mode` never converts existing keyframes — confirmed by direct test,
   not assumption.** Live-tested both paths: the **operator**
   `bpy.ops.pose.rotation_mode_set(type='XYZ')` correctly converts the *current pose value*
   (quaternion → equivalent Euler, read back bit-exact) but leaves the old
   `rotation_quaternion` F-Curve untouched in the action and creates no new `rotation_euler`
   F-Curve — the bone's animation is silently broken at every *other* keyframe until a full
   manual re-key pass in the new mode. **Direct property assignment**
   (`pose_bone.rotation_mode = 'XYZ'`, no operator) behaves the same, minus even the
   current-frame display fix-up the operator does. Decide rotation mode per bone before keying
   anything.

3. **`Action.fcurves` does not exist from Blender 5.0 onward** (confirmed
   `hasattr(action, "fcurves") == False` **[LIVE]** on the connected 5.1.1). Code copied from a
   4.3-era tutorial that does `action.fcurves.new(...)` will `AttributeError` on a Blender 5.1
   install. Use `keyframe_insert()` (works unchanged on both) or feature-detect
   `hasattr(action, "fcurve_ensure_for_datablock")` before falling back to the legacy accessor.

4. **Nested bone properties must be keyed through the owning ID, not the bone as if it were
   independent.** `pose_bone.keyframe_insert("rotation_quaternion")` happens to work because
   `PoseBone` resolves its own `id_data` correctly, but the resulting F-Curve's `data_path` is
   always `pose.bones["Name"].prop`, stored on the **Object's** action — there is no such thing
   as a bone with its own independent Action. Any raw `data_path` string built by hand (for
   `driver_add`/`keyframe_delete`/`fcurve_ensure_for_datablock`) must always be relative to the
   armature object, never to the bone.

5. **`INSERTKEY_VISUAL` / `visual_keying` matter enormously and are easy to leave off by
   default.** Baking or keying a constrained bone *without* visual keying captures the raw,
   pre-constraint channel (frozen at whatever it happened to be), not the motion visible on
   screen — and the `bpy.ops.nla.bake` docs explicitly warn that `clear_constraints=True`
   **without** `visual_keying=True` produces a bake that does not match the pre-bake animation.

6. **Auto-Keying is a scene-global toggle (`ToolSettings.use_keyframe_insert_auto`) a script
   should never rely on** — it depends on `context.scene.tool_settings` state the user may have
   on or off for unrelated reasons, changes which properties get keyed based on
   `auto_keying_mode` (`ADD_REPLACE_KEYS` vs. `REPLACE_KEYS` — per the identifiers themselves,
   the latter only touches F-Curves that already exist rather than creating new ones), and ties
   keying to *modifying a property through the UI/operators*, which a data-API script often
   does not trigger at all. Always call `keyframe_insert()` explicitly; to deliberately
   *reproduce* Blender's auto-key semantics (e.g. respecting locked channels), call
   `bpy_extras.anim_utils.AutoKeying.key_transformation(context, target)` rather than toggling
   the scene setting.

7. **Operators fail with an opaque `poll() failed` error when context is wrong, and the fix is
   almost never "add a temp_override for every context member you can think of."** Use
   `override.logging_set(True)` (see Context overrides) to see exactly which member is missing;
   and check first whether the task can be done with pure data API instead (constraints,
   actions, NLA, keyframing, baking, and pose-space conversions all can — see the list above).

8. **Low-level `FCurveKeyframePoints.insert()` inserts do not automatically get Bezier
   handles/interpolation "for free."** This only matters when inserting via the low-level
   F-Curve API instead of `keyframe_insert()` (which follows scene/tool defaults, typically
   Bezier in a default startup file) — a programmatic low-level insert that never explicitly
   sets `kf.interpolation = 'BEZIER'` can silently produce fully stepped (constant) animation
   instead of the smooth curve the caller assumed.

9. **A pushed-down/unassigned Action with no fake user and no NLA strip referencing it
   disappears on file reload, not immediately** — a script that builds a library of cycle
   actions, pushes each to NLA, then unassigns `animation_data.action` between builds, can pass
   every in-session check yet lose actions the moment the file is saved and reopened. Set
   `action.use_fake_user = True` at creation time for anything meant to persist as a reusable
   asset.

10. **`bake_action`'s `BakeOptions` has no defaults for any of its 12 fields** (dataclass,
    confirmed **[LIVE]** — `BakeOptions()` raises `TypeError`). Every field must be passed
    explicitly every time; there is no "just bake pose+visual, defaults for the rest"
    shortcut.

## Verified bpy snippets

Each snippet was checked against the cited docs; blocks marked **[LIVE]** were additionally
executed against the connected Blender 5.1.1 instance in this research session, on throwaway,
unlinked (or immediately-cleaned-up) data-blocks — none of this touched the user's actual file.

### 1. Explicit keyframing at an arbitrary frame, without moving the playhead
```python
# docs.blender.org/api/current/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert
pose_bone.rotation_mode = 'QUATERNION'
pose_bone.rotation_quaternion = target_quat
pose_bone.keyframe_insert(
    data_path="rotation_quaternion",
    frame=37,                      # explicit frame -- scene.frame_current is untouched
    group=bone_name,
    keytype='BREAKDOWN',           # or 'KEYFRAME' / 'EXTREME' / 'MOVING_HOLD'
    options={'INSERTKEY_NEEDED'},
)
```

### 2. Setting a pose bone from a known armature-space matrix **[LIVE]**
```python
# docs.blender.org/api/current/bpy.types.PoseBone.html  (matrix / matrix_basis)
# pattern verbatim from the bpy.types.PoseBone.bbone_segment_matrix example
pose_bone.matrix = target_matrix_in_armature_space
bpy.context.view_layer.update()   # required: matrix_basis was back-solved, dependents need re-eval
```

### 3. World-space <-> pose-space conversion **[LIVE]**
```python
# docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.convert_space
world_matrix = armature_obj.convert_space(
    pose_bone=pose_bone, matrix=pose_bone.matrix,
    from_space='POSE', to_space='WORLD',
)
local_basis = armature_obj.convert_space(
    pose_bone=pose_bone, matrix=world_target_matrix,
    from_space='WORLD', to_space='LOCAL',
)
pose_bone.matrix_basis = local_basis
```

### 4. Batch whole-body pose without per-bone depsgraph updates
```python
# docs.blender.org/api/current/bpy.types.Bone.html#bpy.types.Bone.convert_local_to_pose
# (official example, reproduced from the live bundled docs;
#  matrix_map: dict[bone_name, Matrix] in armature space)
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

### 5. IK constraint setup — pure data API, no context needed **[LIVE]**
```python
# docs.blender.org/api/current/bpy.types.KinematicConstraint.html
# docs.blender.org/api/current/bpy.types.PoseBoneConstraints.html
ik = arm_obj.pose.bones["Hand.L"].constraints.new(type='IK')
ik.target = target_empty_or_rig
ik.subtarget = ""            # "" when target is an Object (e.g. an Empty), not another armature's bone
ik.chain_count = 2           # hand + forearm; 0 = whole chain to root
ik.pole_target = pole_empty
ik.pole_angle = math.radians(-90)
ik.use_stretch = False
```

### 6. Version-safe Action creation + keying (works on 4.3 through 5.1)
```python
# docs.blender.org/api/current/bpy.types.ID.html#bpy.types.ID.animation_data_create
# docs.blender.org/api/current/bpy.types.BlendDataActions.html
action = bpy.data.actions.new("WalkCycle")
action.use_fake_user = True                    # survives reload with zero other users
obj.animation_data_create()
obj.animation_data.action = action
obj.keyframe_insert(data_path="location", frame=1)   # creates slot/layer/strip transparently on 4.4+
```

### 7. Version-safe direct F-Curve access (4.4+ path with legacy fallback)
```python
# docs.blender.org/api/current/bpy.types.Action.html#bpy.types.Action.fcurve_ensure_for_datablock
# developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/  (legacy API removed by 5.0)
if hasattr(action, "fcurve_ensure_for_datablock"):
    fcurve = action.fcurve_ensure_for_datablock(obj, "location", index=0)
else:
    fcurve = action.fcurves.find("location", index=0) or action.fcurves.new("location", index=0)
```

### 8. NLA track + looping cycle strip **[LIVE]**
```python
# docs.blender.org/api/current/bpy.types.NlaTracks.html
# docs.blender.org/api/current/bpy.types.NlaStrips.html
# docs.blender.org/api/current/bpy.types.NlaStrip.html
action.use_frame_range = True
action.frame_start, action.frame_end = 1, 13
action.use_cyclic = True

track = obj.animation_data.nla_tracks.new()
strip = track.strips.new("WalkCycleStrip", 1, action)
strip.repeat = 4.0            # frame_end auto-recalculates: 1 + (13-1)*4 = 49
strip.extrapolation = 'HOLD'
```

### 9. Baking without any operator/context dependency **[LIVE]**
```python
# docs.blender.org/api/current/bpy_extras.anim_utils.html
from bpy_extras import anim_utils
opts = anim_utils.BakeOptions(
    only_selected=False, do_pose=True, do_object=False,
    do_visual_keying=True, do_constraint_clear=False, do_parents_clear=False,
    do_clean=True, do_location=True, do_rotation=True, do_scale=True,
    do_bbone=False, do_custom_props=False,
)
baked_action = anim_utils.bake_action(arm_obj, action=None, frames=range(1, 25), bake_options=opts)
```

### 10. Context override for an operator needing a specific active object/selection, without touching the user's real state
```python
# docs.blender.org/api/current/bpy.types.Context.html#bpy.types.Context.temp_override
with bpy.context.temp_override(active_object=arm_obj, selected_objects=[arm_obj]):
    bpy.ops.object.mode_set(mode='POSE')
```

### 11. Mirroring a pose (Paste Flipped equivalent)
```python
# docs.blender.org/api/current/bpy.ops.pose.html  (copy / paste)
bpy.ops.pose.copy()
bpy.ops.pose.paste(flipped=True, selected_mask=False)
```

## Sources

Blender Python API reference (bundled RST via the Blender MCP server, matching the connected
Blender **5.1.1** instance; cross-checked live where marked **[LIVE]** above):
- https://docs.blender.org/api/current/bpy.types.PoseBone.html
- https://docs.blender.org/api/current/bpy.types.Bone.html
- https://docs.blender.org/api/current/bpy.types.Pose.html
- https://docs.blender.org/api/current/bpy.types.Armature.html
- https://docs.blender.org/api/current/bpy.types.Object.html
- https://docs.blender.org/api/current/bpy.types.Action.html
- https://docs.blender.org/api/current/bpy.types.ActionSlot.html
- https://docs.blender.org/api/current/bpy.types.ActionSlots.html
- https://docs.blender.org/api/current/bpy.types.ActionLayer.html
- https://docs.blender.org/api/current/bpy.types.ActionKeyframeStrip.html
- https://docs.blender.org/api/current/bpy.types.ActionChannelbag.html
- https://docs.blender.org/api/current/bpy.types.AnimData.html
- https://docs.blender.org/api/current/bpy.types.NlaTrack.html
- https://docs.blender.org/api/current/bpy.types.NlaTracks.html
- https://docs.blender.org/api/current/bpy.types.NlaStrip.html
- https://docs.blender.org/api/current/bpy.types.NlaStrips.html
- https://docs.blender.org/api/current/bpy.types.FCurve.html
- https://docs.blender.org/api/current/bpy.types.FCurveKeyframePoints.html
- https://docs.blender.org/api/current/bpy.types.Keyframe.html
- https://docs.blender.org/api/current/bpy.types.KeyingSet.html
- https://docs.blender.org/api/current/bpy.types.ToolSettings.html
- https://docs.blender.org/api/current/bpy.types.Constraint.html
- https://docs.blender.org/api/current/bpy.types.KinematicConstraint.html
- https://docs.blender.org/api/current/bpy.types.PoseBoneConstraints.html
- https://docs.blender.org/api/current/bpy.types.Context.html
- https://docs.blender.org/api/current/bpy.types.bpy_struct.html
- https://docs.blender.org/api/current/bpy.types.ID.html
- https://docs.blender.org/api/current/bpy.types.BlendDataActions.html
- https://docs.blender.org/api/current/bpy.ops.pose.html
- https://docs.blender.org/api/current/bpy.ops.anim.html
- https://docs.blender.org/api/current/bpy.ops.nla.html
- https://docs.blender.org/api/current/bpy.ops.object.html
- https://docs.blender.org/api/current/bpy_extras.anim_utils.html
- https://docs.blender.org/api/current/mathutils.Quaternion.html
- https://docs.blender.org/api/current/mathutils.Euler.html
- https://docs.blender.org/api/current/mathutils.Matrix.html

Blender manual (5.1, via the bundled manual RST + one WebSearch-confirmed URL):
- manual/animation/keyframes/introduction.rst (Keyframe Types)
- manual/animation/keyframes/keying_sets.rst (Whole Character Keying Set)
- manual/animation/constraints/interface/common.rst (Space Types)
- manual/animation/constraints/tracking/ik_solver.rst
- https://docs.blender.org/manual/en/5.1/animation/actions.html#action-slots

Official Blender developer documentation (4.4 migration — authoritative for the Action Slots
breaking change; fetched via WebSearch since direct WebFetch to this domain was blocked this
session):
- https://developer.blender.org/docs/release_notes/4.4/animation_rigging/
- https://developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/
- https://developer.blender.org/docs/release_notes/4.4/python_api/
- https://developer.blender.org/docs/features/animation/animation_system/layered/
- https://developer.blender.org/docs/release_notes/5.0/python_api/

4.3-era / historical API confirmation (WebSearch-extracted text from archived
`docs.blender.org/api/...` version pages — WebFetch to `docs.blender.org` returned HTTP 403
site-wide in this session for every URL tried, including the bare `/api/current/` index, so
none of the `docs.blender.org` citations in this report were fetched directly; all came either
from the Blender MCP server's bundled RST mirror or from WebSearch's extracted page text):
- https://docs.blender.org/api/blender_python_api_2_63_17/bpy.types.PoseBone.html
  (matrix_basis/matrix_channel wording — historically stable across versions)
- https://docs.blender.org/api/current/bpy.types.ActionFCurves.html (legacy
  `Action.fcurves.new` signature, still documented as the "legacy" path on the current page)

Animation-craft references (not Blender API — cited separately, since these are industry
convention, not something `docs.blender.org` defines):
- https://rustyanimator.com/walk-cycle-animation/ (contact/down/passing/up frame breakdown)
- https://www.animationmentor.com/blog/tutorial-animating-human-walk-cycle/

**Live execution evidence:** every snippet marked **[LIVE]** was run in this session against
the connected Blender 5.1.1 instance via the `execute_blender_code` MCP tool, exclusively on
newly created, unlinked (or immediately-cleaned-up) armature/object/action data-blocks. No user
scene data was modified; each test's `finally` block was confirmed via a follow-up `bpy.data`
existence check to have fully removed the throwaway data-blocks (armatures, objects, and
actions), and any transient selection/active-object/mode change made to exercise Edit/Pose-mode
operators was restored to its prior state afterward.
