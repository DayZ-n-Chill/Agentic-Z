# Driving Blender for animation through MCP

How to key animation in the user's live Blender through the Blender MCP server's `execute_blender_code` tool (`mcp__Blender__execute_blender_code` when the server is registered as `Blender`). Everything goes through the `bpy` data API, with no UI and no mouse. The DayZ facts live in `blender-txa-export.md`; this file and the `blender-bpy-*` files are Blender knowledge, run against Blender 5.1 or taken from the Blender API reference and manual.

The work needs Blender and the MCP server, not `P:\` or DayZ Tools. For work that ends in DayZ, also follow `skills/_shared/dayz-conventions.md`.

## When to open another file

- Mixamo or FBX motion capture onto a rig: `mixamo-retarget.md` (same server, different job).
- Building or changing geometry: `_shared/models/blender-assembly.md`. Reviewing a static model: `_shared/models/blender-visual-review.md`.
- Object animation driven by config (doors, levers, `class Animations`, `SetAnimationPhase`): `model-cfg-animations.md`. It needs no Blender at all. For DayZ, Blender work stops at the `.txa` (`blender-txa-export.md`).

| The task is about | Read first |
|---|---|
| Bone matrices, pose spaces, rotation modes | `blender-bpy-armatures.md` |
| Key types, inserting keys, Actions, the NLA, cycles | `blender-bpy-keyframes-and-actions.md` |
| IK, baking constrained motion, operator context | `blender-bpy-ik-and-baking.md` |
| F-curves, slots, interpolation and easing | `blender-bpy-fcurves.md` |
| Noise, Cycles and the other F-curve modifiers | `blender-bpy-fcurve-modifiers.md` |
| Camera moves, constraints, parenting, motion paths | `blender-bpy-objects-camera.md` |
| Material keys, drivers, shape keys | `blender-bpy-materials-drivers.md` |
| Rigid bodies, throwing, scale and gravity | `blender-bpy-physics.md` |
| Cloth, soft bodies, particles | `blender-bpy-cloth-and-particles.md` |
| Baking simulations to keys, FBX and Alembic export | `blender-bpy-sim-baking-export.md` |
| Making motion feel alive and heavy, frame counts, camera feel | `blender-realism-and-review.md` |
| The self-audit, previews, review rounds | `blender-review-loop.md` |
| Anything meant for DayZ | `blender-txa-export.md` |

## Probe the scene first

Run this before any animation work. The version, scene state and enabled add-ons decide which API paths are safe; never assume them, and never target a leftover Blender folder with no executable in it.

```python
import bpy
ims = bpy.context.scene.render.image_settings
result = {
    "version": list(bpy.app.version),                     # decides the Action data model
    "blend_file": bpy.data.filepath or "(unsaved)",
    "fps": bpy.context.scene.render.fps,
    "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
    "autokey": bpy.context.scene.tool_settings.use_keyframe_insert_auto,
    "has_media_type": hasattr(ims, "media_type"),         # 5.x video output switch
    "addons": [a for a in bpy.context.preferences.addons.keys()
               if any(k in a.lower() for k in ("anim", "rig", "dayz"))],
    "objects": len(bpy.data.objects), "armatures": len(bpy.data.armatures),
}
```

- Autokey on: turn it off for the session and restore it at the end. Scripts insert keys explicitly, and autokey turns every scratch transform into a stray key.
- Version 4.4 or later uses slotted Actions; from 5.0 the old `action.fcurves` is gone, not just deprecated.
- In the user's open scene, prefix every scratch datablock `_anim_tmp_`, save nothing without asking, and restore every render setting you touch. Delete scratch objects, their meshes and their actions when done.

## Slotted Actions and the end of `action.fcurves`

Most tutorials and forum answers use `action.fcurves`, which raises `AttributeError` on Blender 5.1. The data model is now Action, then layers, then strips, then one channelbag per slot, then F-curves.

- Write keys with `obj.keyframe_insert(data_path, frame=N)` or `pose_bone.keyframe_insert(...)`, and drivers with `id.driver_add(path)`. The call is the same on 4.3 and 5.x and never touches the Action layout, so prefer it always.
- Read and edit curves through the channelbag:

```python
ad = obj.animation_data
cb = ad.action.layers[0].strips[0].channelbag(ad.action_slot)
fc = cb.fcurves.find("location", index=2)
```

- `from bpy_extras import anim_utils` gives `animdata_get_channelbag_for_assigned_slot(ad)` on 5.x only, and `action_get_channelbag_for_slot` from 4.4 on. On 4.3 to 4.5 fall back to `action.fcurves`, guarded by `hasattr` (`get_fcurves` in `blender-bpy-sim-baking-export.md`).
- `action.fcurve_ensure_for_datablock(...)` creates curves directly from 4.4 on.
- Assigning actions (`animation_data_create()`, `ad.action = ...`) works everywhere.
- `Bone.select` is gone on 5.x; select bones through `PoseBone.select`. The DayZ plugin's exporter reads `pose.bones[name].select` for its "Selected Bones Only" mask (`ExportTxa.py:163` to `:169`).
- Never test for a plugin operator with `hasattr(bpy.ops.export_scene, "txa")`: `bpy.ops` answers any name with a truthy value and fails only when called. Call `bpy.ops.export_scene.txa.poll()` inside `try` instead.
- `a.rotation_difference(b)` in `mathutils` returns the delta composed on the right (`a @ d == b`). For slerp or extrapolation, scale the delta through axis and angle and compose on the right.
- A reused hand pose can hide a broken finger: a distal phalanx turned 90 to 110 degrees about an axis other than its bending axis reads fine in full body stills and shows only in a hand close-up. Before reusing a hand pose, check each phalanx's rotation axis against the finger's bending axis (the phalanges of one finger share it), and render at least one close-up per hand in review.

## Runtime rules

- References go stale after a change. After `fcurve.update()` or inserting keys, a kept reference to `keyframe_points[i]` reads garbage (written `BACK` and `EASE_OUT` read back as `CONSTANT` and `''`). Fetch the F-curve and its points again after every change.
- Edit curves through the data, never `bpy.ops.graph.*`: those operators fail without a Graph Editor. Set `kp.interpolation`, `kp.easing`, `fcurve.extrapolation`, modifiers and handles directly.
- Video output on 5.x needs `ims.media_type = 'VIDEO'` first; only then is `ims.file_format = 'FFMPEG'` a valid value (otherwise it raises `TypeError`). Then set `render.ffmpeg.format = 'MPEG4'` and `render.ffmpeg.codec = 'H264'`. Test by assigning inside `try`, since enum lists differ between versions, and fall back to a PNG sequence when the build has no FFMPEG.
- Previews from a script use the scene camera. In the live MCP session `bpy.ops.render.opengl(write_still=True, view_context=False)` is fast; the default `view_context=True` renders the user's viewport with grid, outlines and gizmos. In `blender -b` there is no OpenGL context and `render.opengl` fails, so render with `bpy.ops.render.render(write_still=True)` or `(animation=True)` on Workbench or EEVEE from the scene camera.
- Never rely on autokey, and never key scale for DayZ: the plugin does not export scale keys by default, and whether binarizing drops scale is not confirmed.
- Give operators that need context `bpy.context.temp_override(...)`. It also takes selection and active object keys and restores state by itself. The pure data API avoids operator context entirely and is usually better.
- `bpy.ops.rigidbody.bake_to_keyframes` fails in background mode (a known Blender bug with nested operator context). Use `bpy_extras.anim_utils.bake_action(obj, action=None, frames=range(...), bake_options=BakeOptions(...))`; `BakeOptions` is a dataclass of 12 fields with no defaults, so fill every one. `ptcache.bake` needs `temp_override(point_cache=scene.rigidbody_world.point_cache)`. Bake the point cache before sampling frames for keys: each pass over an unbaked simulation simulates again and diverges, by 3.56 m in one run.
- Restore what you touch: frame range, `render.filepath`, `image_settings`, `resolution_percentage`, autokey. Take a snapshot before and restore it in a `finally:` block.

## Keying in passes

Quality comes from working in the right order, not one perfect pass. Frame counts are in `blender-realism-and-review.md`; the stages and checks in `blender-review-loop.md`.

1. Plan beats with frame budgets before posing, for example at 24 fps: anticipation 8 frames, action 6, overshoot 3, settle 12. A walk step is about 12 frames, a head turn 10 to 14, a hit pause 2 to 6; a jump crouches slowly and takes off fast. Weight lives in spacing, not poses.
2. Block. Key every channel of a control on each story pose with `CONSTANT` interpolation, and mark key types with `kp.type = 'EXTREME'`, `'BREAKDOWN'` or `'MOVING_HOLD'`. Render 3 to 6 key pose stills (`view_context=False`, 25 to 50 percent resolution) and read them before moving on.
3. Spline. Switch to `BEZIER`, set easing by intent (`EASE_OUT` with `BACK` gives a real overshoot and settle), and fix what the switch broke.
4. Offset. Every channel keyed on the same frames is the first sign of robotic motion. Stagger follower channels and bones by 1 to 3 frames and add follow-through keys past the stop.
5. Keep holds alive. Add drift keys of 1 to 2 percent of the move across any hold longer than 6 frames.
6. Polish. Run the self-audit, fix what it flags, render the preview, watch it or read stills at contact and extreme frames, and repeat. Expect two to four rounds.

## The self-audit numbers

Three numbers separate robotic from organic motion: a robotic test rig scores 1.0, 1.0 and 0.0, an organic one 0.0, 0.0 and 0.25. The code and thresholds are in `blender-review-loop.md`, "The self-audit".

- `linear_ratio`: share of keys with `LINEAR` interpolation; about 0 after splining.
- `keyframe_unison_ratio`: share of channels with identical key frames; about 1.0 is right while blocking and a fault after offsetting.
- `overshoot_ratio`: sample `fcurve.evaluate()` between the last two keys and see whether the value passes its target before it settles.

## Handing off to DayZ

The deliverable is a `.txa` exported with the DayZ animation plugin's own operator from the plugin's own rig, with the target `.anm` name noted. What to key, the Export Type, the loop notetracks and the axes are in `blender-txa-export.md`. Workbench import, the `.asi` and config wiring, the PBO and the in game test belong to the user and the pipeline. Never claim to have run Workbench, and say DayZATool ran only when you ran it and read the file it wrote.

## Before delivering

1. Render key pose stills at the contact and extreme frames and the final preview video, all with `view_context=False`.
2. Read the stills: silhouettes read, arcs are unbroken, nothing passes through anything, holds are alive. Judge orientation only from a still on the character's forward axis: a three quarter view foreshortens, and a palm forward wave can read as palm sideways. Work out forward from bone geometry (the shoulder line crossed with the spine, its sign fixed by the face bones); never assume it.
3. For gestures where the hand faces something (wave, salute, point, present), check the palm in numbers. Find the hand bone's palm normal axis once at rest (the normal of the knuckle plane at frame 0), then require the angle between the world palm normal and the character's forward to be 30 degrees or less on the gesture's key frames, using the hand pose bone's world matrix. Stills alone miss this.
4. Report the self-audit numbers with the delivery.
5. For DayZ, check the `.txa` exists and is not trivially small, and say which bones were left out and which Export Type was used.
6. Leave the scene clean: scratch datablocks removed, settings restored, the playhead at frame 1.

## Where it runs

- By default in the user's live Blender through MCP, so they see the work as it happens. When the server is not connected, ask the user to open Blender with the add-on, or fall back to `blender -b --python script.py` (with the full path to `blender.exe` when it is not on `PATH`) for batch work such as tests and bakes. The `bpy` code is the same, but `bake_to_keyframes` and anything that needs a window still fail there.
- Large outputs (videos, stills) go under `output/<descriptive-folder>/` or a folder the user names, never into a skill folder. Keep the `.txa` next to the `.anm` it becomes.
- On Linux, Blender is native: the batch call is `blender -b --factory-startup --python script.py`, tested with Blender 5.2 LTS. The MCP route and the `bpy` code are the same. The DayZ tool setup is in `skills/_shared/linux-proton.md`, and the `.txa` to Workbench to `.anm` handoff in `tooling-and-walls.md`, "On Linux".
