---
name: blender-animation
description: "Authors motion in the user's live Blender through the Blender MCP server and bpy: keyframes, armature poses, IK, cycles, camera moves, drivers, material and shape key animation, physics bakes, preview renders, and the .txa export for DayZ. Use when the user says animate this, walk cycle, turntable, bake the simulation, camera shake, animation for DayZ or .txa (Spanish: anima esto, bakea la simulacion, animacion para DayZ). Not for Mixamo retargeting (mixamo-retarget), building geometry (blender-assembly) or DayZ model.cfg animation (dayz-animation-pipeline)."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Blender animation (through MCP)

Author animations in the user's live Blender through the Blender MCP server's `execute_blender_code` tool (`mcp__Blender__execute_blender_code` when the server is registered as `Blender`). Everything happens through the `bpy` data API: no UI, no mouse. The API claims in this skill were either run live against Blender 5.1.1 (2026-07-09) or name the Blender API reference or manual entry they rest on in the references. Probe the version before you start (see "Preflight"); do not assume it, and do not target a leftover Blender folder that has no executable in it.

This skill runs no script of its own, so it has no preflight gate. It needs Blender and the Blender MCP server, not `P:\` or DayZ Tools. For work that ends in DayZ, also follow `skills/_shared/dayz-conventions.md`. The deep material lives in `<skill-dir>\references\`; the table under "What to read" says which file answers which question.

## When not to use this skill

- Retargeting Mixamo or FBX mocap onto a rig: use `mixamo-retarget` (same MCP server, different job).
- Building or changing geometry: use `blender-assembly`. Visual review of a static model: use `blender-visual-review`.
- DayZ object animation driven by config (doors, levers, `model.cfg` `class Animations`, `SetAnimationPhase`): that is Layer 1 of `dayz-animation-pipeline`. This skill only authors motion in Blender; for DayZ it stops at the `.txa` (see "DayZ handoff" below).

## Preflight (run before any animation work)

Run this probe first and adapt to what it returns. The version, the scene state and the enabled add-ons decide which API paths are safe:

```python
import bpy
ims = bpy.context.scene.render.image_settings
result = {
    "version": list(bpy.app.version),                     # gates the Action data model
    "blend_file": bpy.data.filepath or "(unsaved)",
    "fps": bpy.context.scene.render.fps,
    "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
    "autokey": bpy.context.scene.tool_settings.use_keyframe_insert_auto,
    "has_media_type": hasattr(ims, "media_type"),         # 5.x video-output gate
    "addons": [a for a in bpy.context.preferences.addons.keys()
               if any(k in a.lower() for k in ("anim", "rig", "dayz"))],
    "objects": len(bpy.data.objects), "armatures": len(bpy.data.armatures),
}
```

Rules that follow from the probe:

- Autokey on: turn it off for the session and restore it at the end. Scripts insert keyframes explicitly; autokey turns every scratch transform into a stray key.
- Version (4,4) or later: slotted Actions (see the version wall below). Version (5,0) or later: the legacy `action.fcurves` is gone, not just deprecated.
- Working in the user's open scene: prefix every scratch datablock `_anim_tmp_`, save nothing without asking, and restore every scene render setting you touch (they are the user's, not yours). Delete scratch objects, their meshes and their actions when done.

## The version wall: slotted Actions (4.4+) and the end of `action.fcurves` (5.0+)

This is the biggest break in this domain. Nearly every tutorial and StackExchange answer online uses `action.fcurves`; that API raises `AttributeError` on Blender 5.1.1 (verified live). The data model is now Action → layers → strips → channelbags (one per slot) → fcurves.

Version-safe rules (all verified live on 5.1.1):

- Write keyframes with `obj.keyframe_insert(data_path, frame=N)` or `pose_bone.keyframe_insert(...)`, and drivers with `id.driver_add(path)`. The call shape is the same on 4.3 and 5.x. Prefer these always; they never touch the action layout.
- Read and edit curves through the channelbag:
  ```python
  ad = obj.animation_data
  cb = ad.action.layers[0].strips[0].channelbag(ad.action_slot)
  fc = cb.fcurves.find("location", index=2)
  ```
  or, portable across versions: `from bpy_extras import anim_utils; cb = anim_utils.animdata_get_channelbag_for_assigned_slot(ad)` (both helpers exist on 5.1.1: `animdata_get_channelbag_for_assigned_slot` and `action_get_channelbag_for_slot`). On 4.3 fall back to `action.fcurves`, guarded by `hasattr`.
- `action.fcurve_ensure_for_datablock(...)` exists from 4.4 for creating curves directly.
- Assigning actions (`animation_data_create()`, `ad.action = ...`) still works everywhere.
- `Bone.select` is gone on 5.x. Bone selection (for example for the DayZ exporter's "Selected Bones Only" mask) is set through `PoseBone.select` (verified live 2026-07-10; the DayZ plugin's own exporter reads `pose.bones[name].select`, `ExportTxa.py:163-169`).
- Never probe plugin operators with `hasattr(bpy.ops.export_scene, "txa")`. `bpy.ops` resolves attribute access dynamically and returns a truthy value for any name; it fails only when called. Probe with `bpy.ops.export_scene.txa.poll()` inside try/except (the false positive was reproduced live on 2026-07-10 with the DayZ plugin unregistered).
- `mathutils`: `a.rotation_difference(b)` returns the right-composed local delta (`a @ d == b`, not `d @ a == b`). For slerp or extrapolation, scale the delta through axis-angle and compose on the right (verified live 2026-07-10).
- Reused or inherited poses can hide broken finger channels. A distal phalanx rotated about 90 to 110° around an axis that is not its flexion axis reads fine in full-body stills and shows only in a hand close-up. Before reusing any hand pose, check each phalanx's rotation axis against the finger's flexion axis (the phalanges of one finger share it), and always render at least one close-up still per hand during review; full-body resolution cannot resolve distal phalanges (the defect was seen in live Blender, 2026-07-10).

## Hard runtime rules (each one cost a real failure)

1. **Stale references after mutation.** After `fcurve.update()` or after inserting keys, any Python reference you kept to `keyframe_points[i]` silently reads garbage (verified live: wrote `BACK`/`EASE_OUT`, the stale reference read `CONSTANT`/`''`). Fetch the fcurve and its `keyframe_points` again after every mutation, before reading or writing them.
2. **Data API only for curve editing.** `bpy.ops.graph.*` operators fail without a Graph Editor context (poll error, verified). Set `kp.interpolation`, `kp.easing`, `fcurve.extrapolation`, modifiers and handles directly on the data.
3. **Video output on 5.x is gated by `media_type`.** Set `ims.media_type = 'VIDEO'` first; only then does `ims.file_format = 'FFMPEG'` become a valid enum value (verified: without it the enum lists only image formats and raises `TypeError`). Then `render.ffmpeg.format='MPEG4'; render.ffmpeg.codec='H264'`. Probe with try/except; when FFMPEG really is missing from the build, fall back to a PNG sequence. Static enum introspection lies across versions; probing by assignment is the only reliable check.
4. **Previews from a script use the scene camera, not the viewport, and the GL path depends on where you run.** In the live MCP (GUI) session, `bpy.ops.render.opengl(write_still=True, view_context=False)` is the fast path. `view_context=True`, the default, renders the user's viewport with its overlays: grid, selection outlines, gizmos (verified by rendering one). In `blender -b` (headless) `render.opengl` fails, because there is no OpenGL context (reproduced independently by three eval runs). Render previews there with the normal engine render (`bpy.ops.render.render(write_still=True)` or `(animation=True)` on Workbench or EEVEE) from the scene camera. Same look, slightly slower, works everywhere.
5. **Never rely on autokey, and never key scale for DayZ** (the plugin does not export scale keys by default; whether binarizing drops scale is not confirmed).
6. **Operators that need context get `bpy.context.temp_override(...)`.** It accepts selection and active-object keys too, and restores the state by itself. Many tasks are better done with the pure data API, which avoids operator context entirely.
7. **Physics baking headless.** `bpy.ops.rigidbody.bake_to_keyframes` fails in background mode (a known Blender bug: nested operator context). Use `bpy_extras.anim_utils.bake_action(obj, action=None, frames=range(...), bake_options=BakeOptions(...))` (pure data API, needs no context; `BakeOptions` is a dataclass of 12 fields with no defaults, so construct it in full), or step the frames yourself and insert keys. `ptcache.bake` needs `temp_override(point_cache=scene.rigidbody_world.point_cache)`. Bake the point cache before sampling any frame for keyframing: each pass over an unbaked simulation simulates again and diverges (3.56 m of drift between two passes was measured in a real run).
8. **Restore what you touch.** Frame range, `render.filepath`, `image_settings`, `resolution_percentage`, autokey: take a snapshot before, restore in a `finally:` after.

## The authoring workflow (blocking → spline → polish)

Animation quality comes from iterating in the right order, not from one perfect pass. Full detail and timing tables: `references/realism-and-iteration.md`.

1. **Plan beats.** Write the beat sheet with frame budgets before posing (for example at 24 fps: anticipation 8f, action 6f, overshoot 3f, settle 12f). Anchors from real actions: a walk step is about 12f, a head turn 10 to 14f, a jump crouches slowly and takes off fast, a hit-stop is 2 to 6f. Weight lives in spacing (contrast in acceleration), not in poses.
2. **Blocking.** Key all channels of a control on each story pose, with interpolation `CONSTANT` (stepped). Mark the key types: `kp.type = 'EXTREME'`, `'BREAKDOWN'` or `'MOVING_HOLD'`. This is Blender's own blocking vocabulary and it can be set from a script. Gate: render 3 to 6 golden-pose stills (`view_context=False`, 25 to 50% resolution, under a second each) and look at them (read the PNGs) before splining.
3. **Spline.** Switch to `BEZIER`, set the easing by intent (`EASE_OUT` with `BACK` for overshoot and settle, verified to produce a real overshoot), and fix what the switch broke.
4. **Offset and overlap.** The first sign of robotic motion is every channel keyed on the same frames. Stagger follower channels and bones by 1 to 3 frames, and add follow-through keys past the stop.
5. **Moving holds.** A frozen hold reads as dead. Add small drift keys (1 to 2% of the move) across any hold longer than 6 frames.
6. **Polish and audit.** Run the programmatic audit below, fix what it flags, render the MP4 playblast, watch it (or read stills at the contact and extreme frames), and iterate. Expect at least 2 to 4 rounds. The gates are per stage, not one final check.

## Programmatic realism audit

Calibrated on 5.1.1: a robotic rig scored 1.0 / 1.0 / 0.0 and an organic one 0.0 / 0.0 / 0.25, a full separation. The code and the thresholds are in the self-audit section of `references/realism-and-iteration.md`.

- `linear_ratio`: the share of keys with `LINEAR` interpolation (target after splining: about 0).
- `keyframe_unison_ratio`: the share of channels with identical key frames (correct at about 1.0 during blocking, a defect after the offset pass; the thresholds depend on the stage).
- `overshoot_ratio`: sample `fcurve.evaluate()` between the last two keys; does the value pass its final target before it settles?
- Designed extras (arc jitter from `motion_path.points`, a frozen-hold detector, left/right twinning correlation, velocity discontinuities): see the reference.

## What to read

| The task is about | Read first |
|---|---|
| Bones, poses, IK, cycles, bake, NLA layers | `references/characters-armatures.md` |
| Object and camera moves, easing, noise and cycles modifiers, constraints, material keys, drivers, shape keys | `references/objects-camera-materials-drivers.md` |
| Falling, collisions, cloth, particles, bake to keyframes, Alembic export | `references/physics-sims.md` |
| "Make it feel alive, heavy, real", timing, the audit, playblast recipes | `references/realism-and-iteration.md` |
| Anything meant for DayZ | `references/dayz-handoff.md` |

Load only the file the task needs. Specifics worth knowing are in those files:

- Pose-bone matrix spaces: `matrix_basis` against `matrix`, which is armature space, not world space; cross spaces with `Object.convert_space`.
- Changing the rotation mode never converts existing fcurves.
- Material animation lives on `material.node_tree.animation_data`, not on the material.
- Node sockets are keyed with `node.inputs["X"].keyframe_insert("default_value")`.
- A camera Track To needs `TRACK_NEGATIVE_Z` and `UP_Y`; the RNA defaults are wrong for cameras.
- The parent-inverse jump and its fix.
- The wheel-roll-by-distance driver (verified numerically).
- The `NOISE` modifier was reworked in 4.4.
- Cloth presets with exact numbers, and the handoff of a thrown object from kinematic to dynamic.
- FBX cannot carry cloth deformation; Alembic can (verified).

## DayZ handoff (.txa): the default deliverable for DayZ requests

These rules were checked on 2026-07-09; the detail, the tool behaviour behind them and the vanilla facts checked on `P:\` are in `references/dayz-handoff.md`. "The plugin" below is the DayZ Animation Tools add-on for Blender.

- **Interface point**: pose the plugin's own rig and export with the plugin's own operator. The rig is `_AssetSamples\JD_Master_Rig (No IK Bones).blend` in the user's copy of the maintained plugin build, `DayZAnimationPlugin_MAINTAINED` (ask the user where it is), armature object `_DayZ_Character` (151 bones, `OFP2_ManSkeleton`). The export operator is `bpy.ops.export_scene.txa` (verified, plugin source `ExportTxa.py:69`). The IK helpers come from `bpy.ops.import_scene.addsurvivorik` (`AddSurvivorIK.py:10`). Notetracks go through the plugin's Event Manager (`eventmanager.additem`, `load`, `save`).
- The maintained plugin build needs Blender 4.4+ or 5.x (its `bl_info` wrongly says 2.80). When the add-on is not enabled, register it from its folder (`sys.path.append` plus `DayzAnimationTools.register()`) or install it by copying the folder, not from a zip.
- The posing pattern that exports correctly: disable constraints while setting matrices, `rotation_mode='QUATERNION'` on all pose bones, autokey off, an explicit `keyframe_insert` per bone per frame.
- **Hard rules that ruined real sessions** (do them right the first time):
  - Action animations are spine-up. Never key `EntityPosition`, `Pelvis` or the legs (the character flops or clips underground), and never `RightHand_Dummy` (the weapon flies to the back). Vanilla clips do carry a `RightHand_Dummy` track; leaving it out is the tested fix when you have no vanilla-derived values (see the reference).
  - The Export Type carries real weight: `FB` for emotes, `IK1H` or `IK2H` for the grip ikpose, `ADD` for reload, fire and jam with "Selected Bones Only". Exporting all bones on an action animation gives a "meatball" character.
  - Hold actions ended by a timer (unjam and the like) need `LoopStart` and `LoopEnd` notetracks (format `Name||-1`), a loop at least as long as the engine timer (about 6 s for the 5 s unjam), and the moving part settled into the outro pose well before `LoopEnd` (the micro-jerk lesson).
  - `Weapon_*` bones: correct values, or drop them entirely. Placeholder values stretch the weapon mesh. Never key scale (the plugin does not export scale keys by default; whether binarizing drops it is not confirmed).
  - 30 fps is the pipeline default. Bone names must match `OFP2_ManSkeleton` exactly.
- **This skill stops at the `.txa` plus a note of the target `.anm` name.** Workbench "Register & Import", the `.asi` and config wiring, the PBO build and the in-game test belong to `dayz-animation-pipeline` and the user. Never claim to have run Workbench. Mention DayZATool as run only when you ran it and read the file it wrote; on a Windows host it runs headless (`skills/dayz-animation-pipeline/references/skeletal-anm-enfusion.md`, 2026-09-29).

## Before you deliver

An animation is not done when the code ran. It is done when you have looked at it:

1. Render golden stills at the contact and extreme frames, and the final MP4 preview (`media_type='VIDEO'` → FFMPEG → `render.opengl(animation=True)`), all with `view_context=False`.
2. Read the stills (Read tool) and check: the silhouettes read, the arcs are unbroken, nothing interpenetrates, the holds are alive. Camera discipline: judge claims about orientation only from an on-axis still. A 3/4 angle foreshortens and misleads (in a real review a palm-forward wave read as palm-sideways from a 3/4 front-right still). At least one still must be rendered from the character's measured forward axis; compute forward from bone geometry (shoulder line cross spine, sign fixed by the face bones) and never assume it.
3. For gestures where the hand faces something (wave, salute, point, present), add the numeric palm gate. Find the palm-normal axis of the hand bone once against rest anatomy (the normal of the knuckle plane at frame 0; palms face inward or down at rest), then assert `angle(world_palm_normal, character_forward) <= 30°` across the gesture's key frames, using the world matrix of the hand pose bone. A check on stills alone cannot catch this class of defect; the numeric gate together with the on-axis still can.
4. Run the audit numbers from "Programmatic realism audit" and report them with the delivery.
5. For DayZ: check that the `.txa` file exists and is not trivially small, and state which bones were left out and which Export Type was used.
6. Leave the user's scene clean: scratch datablocks removed, their settings restored, the playhead at frame 1.

## Environment notes

- Default execution is the user's live Blender through MCP; they see the progress as it happens. When the MCP server is not connected, ask the user to open Blender with the add-on, or fall back to headless `blender -b --python script.py` (give the full path of `blender.exe` when it is not on `PATH`) for batch and deterministic work such as evals and bakes. The `bpy` code is the same, but `bake_to_keyframes` and anything that needs a window stay broken there (hard rule 7).
- Big outputs (MP4s, stills) go under `output/<descriptive-folder>/` or a folder the user names, never into the skill folder. The `.txa` goes where the user names; keep it next to the `.anm` it becomes.

## On Linux

Everything above is the Windows workflow and stays valid there. The Linux setup for DayZ tools is in the shared Linux and Proton notes (`skills/_shared/linux-proton.md`). For this skill only the headless fallback changes: Blender is native, so the batch call is `blender -b --factory-startup --python script.py` (checked 2026-11-03 with Blender 5.2.2 LTS: a script that adds a cube ran and `sys.platform` was `linux`). The MCP route and the `bpy` code are the same. The `.txa` → Workbench → `.anm` handoff is covered by the Linux notes of `dayz-animation-pipeline`.
