# Authoring keyframes in Blender headless (layer 2)

How an agent authors or edits keyframes with Blender run from the command line, before handing an interchange file to a converter the user runs. The converters are in `tooling-and-walls.md`. Interactive `.txa` authoring in Blender is the blender-animation skill.

Nothing in this file is a vanilla fact on `P:\`: it is tool behaviour and results measured in game by the source pack, each with its build.

## What runs headless and what does not

| Runs headless | Does not, without checking first |
|---|---|
| `blender --background --python script.py` building or editing keyframes on an armature. | The DayZ and Arma Blender add-ons (Arma 3 Object Builder, Bohemia's DayZ animation plugin demo, the SEAnim add-on). They are written for interactive Blender; do not assume they load headless. |
| SEAnim export through this skill's writer or the tool in `scripts/tools/dayz-animation-formats/` (no Blender needed for the file itself). | |
| FBX export through Blender's own exporter. | |

## The path

1. Build an armature whose bone names match the target skeleton (`player-skeleton.md`), or load the official rig from Bohemia's public `DayZ-Misc` repository or the user's own. Never guess names.
2. Set keyframes. Keep the frame rate explicit and the same everywhere.
3. Export:
   - **SEAnim**, the bridge to `.anm`: collect each bone's transform per frame and write the file. The user runs `DayZATool --generate-anim`.
   - **FBX**, the bridge to `.rtm`: `bpy.ops.export_scene.fbx(...)`. The user runs `FBXToRTMGui.exe`.

## Bone names

A name that does not match logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does not animate. Before authoring: take the authoritative bone list, map the armature's names one to one onto it, and check there are no extra or renamed bones. The vanilla skeleton cannot be restructured; a clip can only pose the bones it has (as the source pack understands it; not tested).

## Frame rate and scale

- Set the scene's frame rate and give the same value to the converter. A mismatch changes playback speed.
- Blender works in metres. The exact scale into the game's space is not confirmed: round trip one known clip and compare before trusting a custom factor.

## Axes and handedness

Blender is right handed with Z up. DayZ model space is left handed with Y up. A map between them must be a reflection (determinant −1), or the result is mirrored.

**Geometry.** The model pipeline maps `(x, y, z)` to `(x, z, y)` (the dayz-model-pipeline skill, tested in game by the source pack on 2026-10-01). An earlier version of this note gave `x' = x, y' = z, z' = -y`, a determinant +1 map that mirrors.

**Animation.** `seanim_export.py` carries the reflection, with one map per rig, because the two rigs' bone frames differ by a quarter turn about Z:

| Rig | Rotation `(x, y, z, w)` becomes | Rest position `(x, y, z)` becomes | Status |
|---|---|---|---|
| The JD master rig (`jd_dayz.json`) | `(−y, −z, x, w)` | `(y, z, −x)` | Calibrated 2026-06-29 against a clip extracted with DayZATool. |
| The Bohemia FBX rig built by `build_rig_dayz.py` (`rig_dayz.json`) | `(−x, −z, −y, w)` | `(x, z, y)` | Derived offline 2026-10-02 and played in game the same day for one `LeftArm` pose. |

Both are determinant −1. Do not add a second reflection on top. An earlier version of this note said the script wrote the viewer frame unchanged, and gave the JD map without naming its rig; applied to the FBX rig, that map puts every bone's frame a quarter turn off. Whether other exporters (Blender FBX, third party SEAnim tools) need the same reflection for DayZ skeletons is not tested.

**A mirrored clip raises no error.** It plays with left and right swapped. So test handedness on any new route:

1. Key one side only: raise `LeftArm`, the arm at +X on the official rig in Blender.
2. Export and play it in game on a player holding an item.
3. The arm that rises must be the one opposite the item hand, since items sit on `RightHand_Dummy`.

**The run that was made** (2026-10-02, DayZDiag 1.29.163709):

- Only `LeftArm` was keyed, 70 degrees above horizontal, on `animation_rig_character.fbx` in Blender 5.1. That rig's rest local rotations equal the viewer rig's on all 114 bones.
- It was exported with the calibrated script, spliced as the one changed rotation track into the SEAnim that `DayZATool --extract-anim` gives for the vanilla one handed standing idle `p_1hd_erc_idle_low.anm`, built with `DayZATool --generate-anim`, and played through a child `.asi` of `player_main_1h_fruit.asi` (its `Locomotion.Erc.Idle` lines) on a subclass of `Apple`.
- The arm opposite the apple rose.
- The same pose through the uncalibrated script left that arm at shoulder height, and the vanilla idle round tripped through DayZATool showed the vanilla standing pose.

**What that run does and does not show:**

- It shows the route keeps the keyed track on `LeftArm` and raises that arm as keyed.
- It says nothing about the handedness of the frame change: the bone offsets came from the vanilla clip, and a rotation map reads the same whether the change is a reflection or not.
- It does not show the formula fits the FBX rig's bone frames. The 2026-06-29 calibration ran on the JD rig, whose bone frames are the FBX rig's turned a quarter turn about Z (105 of 113 bones within 0.5 degrees), and this raise turns mostly about the bone's own Z, so both maps raise the arm (offline forward kinematics on the idle: +61.8 degrees with the JD map, +73.1 with the rig aware one).
- A forward raise in a second run the same day told the two maps apart: the rig aware map played it forward, the JD map out to the side.

Detail: `weapon-anim-authoring-viewer.md`, its section on the bone frame maps per rig.

## Check before shipping

Author, export, convert (the user), reference in config, play in game. The only real acceptance is playback in game with no bone errors in the RPT. As a quick offline check, read the SEAnim or FBX back and confirm the bone count, frame count and frame rate are what was intended. A file is not correct just because the writer raised no error.
