# Keyframes from Blender on the command line

How an agent keys or edits motion with Blender run from the command line, then hands an interchange file to a converter the user runs. The converters are in `tooling-and-walls.md`; keying in a live Blender is `blender-mcp-workflow.md`, and the `.txa` export is `blender-txa-export.md`.

Most of this file is tool behaviour and results measured in game; the vanilla facts cite `P:\`.

## What runs without a window

| Runs with `--background` | Check before relying on it |
|---|---|
| `blender --background --python script.py` building or editing keyframes on an armature. | The DayZ and Arma Blender add-ons (Arma 3 Object Builder, Bohemia's DayZ animation plugin demo, the SEAnim add-on). They are written for interactive Blender; do not assume they load headless. |
| SEAnim export through `skills/dayz-animation-pipeline/scripts/seanim_writer.py` or the tool in `scripts/tools/dayz-animation-formats/`. The file itself needs no Blender. | |
| FBX export through Blender's own exporter. | |

## The steps

1. Build an armature whose bone names match the target skeleton (`player-skeleton.md`), or load Bohemia's rig from the public `DayZ-Misc` repository or the user's own. Never guess names.
2. Set keyframes. Keep the frame rate explicit and the same everywhere.
3. Export SEAnim for the `.anm` route: write each bone's transform per frame, then the user runs `DayZATool --generate-anim`. Export FBX for the `.rtm` route with `bpy.ops.export_scene.fbx(...)`, then the user runs `FBXToRTMGui.exe`.

## Bone names

A name that does not match logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not move. Before keying, take the full bone list (for a survivor, the `player_testing.xob` block that starts at `P:\DZ\anims\cfg\skeletons.anim.xml:110`; zones and parents in `player-skeleton.md`), map the armature's names one to one onto it, and check there are no extra or renamed bones. A clip can only pose the bones the skeleton has (not tested).

## Frame rate and scale

- Give the converter the same frame rate as the scene. A mismatch changes playback speed.
- Blender works in metres. The exact scale into game space is not confirmed: round trip one known clip and compare before trusting a custom factor.

## Axes and handedness

Blender is right handed with Z up; DayZ model space is left handed with Y up. A map between them must be a reflection (determinant −1), or the result is mirrored.

For geometry the model pipeline maps `(x, y, z)` to `(x, z, y)` (`_shared/models/axes-and-winding.md`, tested in game).

For animation `seanim_export.py` carries the reflection with one map per rig, because the two rigs' bone frames differ by a quarter turn about Z:

| Rig | Rotation `(x, y, z, w)` becomes | Rest position `(x, y, z)` becomes | How it was checked |
|---|---|---|---|
| The plugin master rig (`jd_dayz.json`, the script's `jd` map) | `(−y, −z, x, w)` | `(y, z, −x)` | Calibrated against a clip extracted with DayZATool. |
| The Bohemia FBX rig built by `build_rig_dayz.py` (`rig_dayz.json`) | `(−x, −z, −y, w)` | `(x, z, y)` | Worked out offline, then played in game for one `LeftArm` pose. |

Both are determinant −1; do not add a second reflection on top. The `jd` map applied to the FBX rig puts every bone's frame a quarter turn off. Whether other exporters (Blender FBX, third party SEAnim tools) need the same reflection for DayZ skeletons is not tested.

## Testing handedness

A mirrored clip raises no error: it plays with left and right swapped. Test every new route:

1. Key one side only: raise `LeftArm`, the arm at +X on the official rig in Blender.
2. Export it and play it in game on a player holding an item.
3. The arm that rises must be the one opposite the item hand, since items sit on `RightHand_Dummy`.

What this test showed in game, with `LeftArm` raised 70 degrees on `animation_rig_character.fbx` in Blender 5.1, spliced into the SEAnim extracted from the vanilla one handed idle `p_1hd_erc_idle_low.anm`, and played through a child `.asi` of `player_main_1h_fruit.asi` (its `Locomotion.Erc.Idle` lines) on a subclass of `Apple`:

- The arm opposite the apple rose, so the route keeps a keyed track and raises the arm as keyed.
- A sideways raise cannot tell the two maps apart: it turns mostly about the bone's own Z, so both raise the arm (offline forward kinematics: +61.8 degrees with the `jd` map, +73.1 with the rig aware one).
- A forward raise does tell them apart: the rig aware map plays it forward, the `jd` map out to the side. Use a forward raise to check a map.

The full bone frame detail is in `weapon-anim-viewer.md`, in its section on the bone frame maps per rig.

## Check before shipping

Key, export, convert (the user), reference in config, play in game. The only real acceptance is playback in game with no bone errors in the RPT. As a quick offline check, read the SEAnim or FBX back and confirm the bone count, frame count and frame rate. A file is not right just because the writer raised no error.
