# From a Blender action to a `.txa`

What a Blender session hands to the DayZ animation pipeline when the motion is for a DayZ character or weapon: which export route to take, what to deliver, and how the DayZ animation plugin must be set up. Which bones to key and the axis maps are in `txa-bones-and-axes.md`; loop notetracks for actions a script timer ends are in `loop-notetracks.md`. Driving Blender itself is in `blender-mcp-workflow.md`.

"The plugin" is the DayZ Animation Tools add-on for Blender in its maintained build, `DayZAnimationPlugin_MAINTAINED`; the original is `DayZAnimationPluginDemo`. "The plugin rig" is the rig it ships, `_AssetSamples\JD_Master_Rig (No IK Bones).blend`, armature object `_DayZ_Character`, 151 bones (`weapon-anim-viewer.md`). Plugin and tool behaviour is not checked on `P:\`; results measured in game say so. The vanilla skeleton the plugin rig matches is the `player_testing.xob` list in `P:\DZ\anims\cfg\skeletons.anim.xml:110`.

## Two routes to `.anm`

| Route | Steps | Use it for |
|---|---|---|
| `.txa` through the plugin | Pose the plugin rig, export `.txa` with the plugin's operator, Workbench compiles it to `.anm`. Handles root motion. | Every full body and action clip (jam, unjam, melee) and the weapon grip itself. The only route tested in game for those. |
| SEAnim | `skills/dayz-animation-pipeline/scripts/seanim_export.py` writes `.seanim`, then `DayZATool --generate-anim <f>.seanim 100` writes `.anm`. Rotations and rest offsets only. | Weapon bone tracks and partial tracks, and finger or thumb fixes baked into an `.anm` that already exists, without another Workbench run. |

A full body unjam clip exported through SEAnim played wrong in game; through `.txa` its body, head and weapon grip played right. The polish on that clip (loop, a small jerk at the loop exit, the thumb) was deployed through `.txa` but its final in game check is still to do.

The SEAnim map is exact on fingers, but `LeftHand`, the raw wrist bone, does not follow it, so never author the support hand's wrist that way. Viewer quaternions are rig local and point along +Y while DayZ's bone frame points along +X, so an SEAnim export is only right once it plays right in game.

DayZATool does not read `.txa`. It has `--extract-anim` and `--generate-anim`, both on `.seanim`, and `--extract-mdl`, which reads an `.xob` and writes a `.semodel`. It is a closed .NET program with a command line and no GUI step, so an agent on Windows can run it (`anm-clips.md`).

A `.txa` written by plain Python without the plugin (tried as `pose_to_txa.py`) does not close the root frame and the body lies down. Never write a `.txa` by hand; go through the plugin.

## The full `.txa` route

1. Pose the plugin rig in Blender, or bring poses in from the viewer (below).
2. Export with the plugin's operator, choosing the Export Type for the clip.
3. In Workbench (a step only a person does): Resource Manager, right click the `.txa`, "Register & Import" the first time and "Reimport Resource" after that. It writes `.anm` and `.anm.meta`.
4. Optional, with no GUI, for fixes the plugin does not offer (leaving bones out, notetracks): `DayZATool --extract-anim` to `.seanim`, edit it with `skills/dayz-animation-pipeline/scripts/seanim_writer.py`, then `DayZATool --generate-anim` for the final `.anm`.
5. Put the `.anm` in `<Mod>/animations/` and rebuild the PBO. File patching does not reload an `.anm`.

## What to deliver

A session that drives Blender through the MCP server poses `_DayZ_Character` with `bpy` and calls `bpy.ops.export_scene.txa(...)` directly. That operator (`ExportTxa.py`) applies the axis fix, the root frame, the component swaps and the quaternion negation; a round trip through it shows a median error of 0.0 degrees. Do not invent a JSON interchange format.

1. Preferred: the `.txa` from File, Export, DayZ Animation (.txa), exported from a keyed Action on `_DayZ_Character` (or a rig with the vanilla names) with the right Export Type, plus a note of the `.anm` it should become. The user then runs "Register & Import" in Workbench; the wiring belongs to `dayz-animation-pipeline`.
2. When posing through MCP is impractical and the user has the viewer bridge script: a world space JSON it reads unchanged.
3. Only for isolated weapon bone or partial tracks, never full body and never the support hand's wrist: the viewer animation JSON the SEAnim exporter reads.

The world space JSON for the bridge script (quaternions in `[x, y, z, w]` order; the script builds Blender's `Quaternion((q[3], q[0], q[1], q[2]))` itself, so never write Blender order):

```json
{
  "fps": 30,
  "order": ["Bone1", "Bone2"],
  "parent": {"Bone2": "Bone1"},
  "frames": [
    {"Bone1": {"q": [0, 0, 0, 1], "p": [0, 0, 0]}}
  ]
}
```

`order` may be any order (the script sorts parents first), `parent` maps each bone to its parent, and each frame holds every bone's world quaternion and position.

The viewer animation JSON for the SEAnim exporter (local, rig frame quaternions; `keyframes` lists the authored frames):

```json
{
  "fps": 30,
  "bone_order": ["Bone1"],
  "keyframes": [0, 15, 40],
  "frames": [
    {"bones": {"Bone1": [0, 0, 0, 1]}}
  ]
}
```

Run `py skills/dayz-animation-pipeline/scripts/seanim_export.py --anim <json> --rig <rig.json> --out out.seanim`, where `<rig.json>` is the rig the clip was authored on (the exporter tells the plugin rig from Bohemia's FBX rig by its rest offsets), then `DayZATool --generate-anim out.seanim 100`.

## Calling the plugin from a script

- Export is `bpy.ops.export_scene.txa` (`ExportTxa.py:69`); the IK helpers come from `bpy.ops.import_scene.addsurvivorik` (`AddSurvivorIK.py:10`); notetracks go through the plugin's Event Manager (`eventmanager.additem`, `load`, `save`).
- When the add-on is not enabled, register it from its folder (`sys.path.append`, then `DayzAnimationTools.register()`) or install it by copying the folder.
- Posing that exports correctly: constraints off while setting matrices, `rotation_mode = 'QUATERNION'` on every pose bone, autokey off, and an explicit `keyframe_insert` per bone per frame.
- Test the operator with `bpy.ops.export_scene.txa.poll()` inside `try`, never with `hasattr` (`blender-mcp-workflow.md`, "Slotted Actions and the end of `action.fcurves`").

## Setting up the plugin

- Check the code, not `bl_info`. The original build needs Blender 3.6.8 to 4.0 and breaks on 4.1 with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`. The maintained build needs Blender 4.4 or later, 5.x included, because it calls `action.fcurve_ensure_for_datablock` and a helper named `generate_fcurves_bl51`, yet its `bl_info` says `'blender': (2, 80, 0)`. The runs tested in game used Blender 5.1.
- Install by copying `BlenderPlugin/DayzAnimationTools` to `%AppData%\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`, then enable "DayZ Animation Tools" in Preferences, Add-ons. "Install from file" does not work on this download.
- Ask the user where they cloned `DayZAnimationPlugin_MAINTAINED`; the add-on and its `_AssetSamples` rig and pose files are under it. Never guess the folder.
- Pose the plugin rig: it is `OFP2_ManSkeleton` with the vanilla bone names. Bohemia's raw FBX rig `animation_rig_character.fbx` (114 bones) has a scale trap (`txa-bones-and-axes.md`).
- Run "Add Survivor IK Bones" (`import_scene.addsurvivorik`) before any IK or grip pose. It creates `LeftHandOrigin`, `RightHandOrigin` and the `...ForeArmDirection` bones and adds IK constraints on `LeftHand` and `RightHand` with pole angles of −127.9 degrees (left) and +45.3 (right). Without it, importing or authoring an IK `.txa` drops those tracks with only a printed warning.
- Measure which way the rig faces before writing any orientation fix. The plugin rig faces −Z when aimed (hip forward `(0.75, 0, −0.66)`, shoulder forward `(0.57, 0, −0.82)`), not +X; a fault that looked like roll was yaw.
- Workbench drops consecutive keys that are nearly identical, so an authored hold can lose frames. Key holds with real differences, and keep the `.txa` next to its `.anm`: Workbench can edit an `.anm` again only when the `.txa` is there.

## Export Type

| Type | For | Notes |
|---|---|---|
| `FB` | Full body, emotes only | Adds a `Scene_Root`. |
| `IK1H`, `IK2H` | Grip IK pose, one keyframe | The plugin limits the export to the IK bones itself; do not select bones first. |
| `RL` | Rarely used | Treated as `ADD` in practice. |
| `ADD` | Reload, fire, chamber, jam, weapon states | Use "Selected Bones Only". |

Exporting every bone on a reload or action clip collapses the character into a ball in game.

## What the session never does

- Never write the `.asi` wiring, the `AddItemInHandsProfileIK` or `AddItemBoneRemap` calls, `config.cpp` or `model.cfg`; those are in `items-in-hands.md`, `anim-graphs.md` and `model-cfg-animations.md`.
- Never claim to have run Workbench or the in game test, and say DayZATool ran only when you ran it and read the file it wrote.
- Never work out the axis fix and quaternion swap again from scratch; the numbers are in `txa-bones-and-axes.md`.

## Not covered or not tested

- Character import and rigging: `skills/_shared/wearables/references/body-rigging.md` and `canonical-bind.md`. The import scale `f=0.7901` with orientation `T2=(−x, z, y)` belongs to the mesh import of one large custom infected, not to clip authoring; do not apply it here.
- The SEAnim add-on for Blender (`io_anim_seanim`) is not tested here. Everything tested in game went through the plugin or the standalone `seanim_writer.py`.
- The viewer's finger and thumb sliders and its overextension guard are not described here; read `skills/dayz-animation-pipeline/scripts/build_viewer.py` to match them in Blender.
- The `CMD_` and `.asi` grammar is in `anim-graphs.md`. The bones are in `player-skeleton.md`, the `.anm` tools in `anm-clips.md`, the grip in `weapon-in-hands.md`, the full weapon route in `weapon-anim-blender.md` and the headless route in `blender-headless-authoring.md`.
