# Weapon animation viewer

How to pose a weapon animation interactively: a web page that shows the weapon and the character on the player skeleton, where the user poses with IK handles and a key timeline, then exports SEAnim on the way to `.anm`. Use it for "how should this weapon be held" and "how should this reload look" instead of keying bone by bone in Workbench; for a seated rider use `rider-pose-solver.md`.

This is tool behaviour and measured results, not vanilla facts `P:\` can show. Playing the clip in game is the only acceptance. The six tools are in `skills/dayz-animation-pipeline/scripts/`.

## The pipeline

| Step | What | Who |
|---|---|---|
| 1 | The viewer page: weapon, skinned character, skeleton overlay; IK handles (hands, feet, head, weapon) with two bone IK; sliders for wrist roll, finger curl, torso lean and head; a key timeline (add, scrub, play, interpolate) and JSON export. | The agent builds it. |
| 2 | An offline preview: frames captured with a browser run from the command line, as a GIF. No capture script ships here. | The agent. |
| 3 | `seanim_export.py` turns the animation JSON into a `.seanim` and reads it back as a check. | The agent. |
| 4 | `DayZATool --generate-anim X.seanim` makes `X.anm`. | The user. |
| 5 | Bind it in an instance file, pack, sign and test in game. | The user. |

## The tools, in the order they run

They pass files through the folder named by `DAYZ_ANIM_SCRATCH` (default `<tempdir>\dayz-anim-pipeline`).

1. `fbx_extract.py` (Blender) dumps the rig FBX to `rig_raw.json`: rest matrices, parents and lengths of every bone, every empty, and the body mesh.
2. `extract_empties.py` (Blender, same FBX) writes the helper empties through their parent chain to `empties_armworld.json`. It exits 1 and writes nothing when the FBX has no `RightHand_Dummy`, the weapon anchor of the survivor skeleton (`P:\DZ\anims\cfg\skeletons.anim.xml:115`). It deletes the previous run's file before the import, so a failed run leaves nothing stale for step 3; a file it cannot delete stops it with that error.
3. `build_rig_dayz.py` (numpy) aligns bones and mesh and writes `rig_dayz.json` in the viewer's frame, with the helpers as its `anchors`.
4. `extract_weapon.py` (the DayZ fork of py3d) writes the weapon's first visual LOD and memory points to `weapon.json`; it does not depend on steps 1 to 3.
5. `build_viewer.py` writes the page from `rig_dayz.json` and `weapon.json`. On load and on "Ready pose" the page puts the weapon grip at a fixed idle point, (-0.06, 1.02, 0.32) in the viewer frame. The `RightHand_Dummy` anchor is used only by `poseReady()`, which no button calls; run it from the browser console as `window.__VIEWER__.poseReady()`.
6. `seanim_export.py` turns the page's animation JSON into SEAnim; its paths are arguments.

```bat
blender -b --python-exit-code 1 --python skills\dayz-animation-pipeline\scripts\fbx_extract.py -- <animation_rig_character.fbx>
blender -b --python-exit-code 1 --python skills\dayz-animation-pipeline\scripts\extract_empties.py -- <animation_rig_character.fbx>
py skills\dayz-animation-pipeline\scripts\build_rig_dayz.py
py skills\dayz-animation-pipeline\scripts\extract_weapon.py <weapon_mlod.p3d>
py skills\dayz-animation-pipeline\scripts\build_viewer.py <out.html>
py skills\dayz-animation-pipeline\scripts\seanim_export.py --anim weapon_anim.json --rig <scratch>\rig_dayz.json --out clip.seanim
```

- The Blender steps take the FBX after `--`, from `DAYZ_ANIM_RIG_FBX`, or by file name in the current folder; give both the same FBX. `extract_weapon.py` takes the `.p3d` as its argument or from `DAYZ_ANIM_WEAPON_P3D`.
- Run Blender with `--python-exit-code 1` and stop at the first non zero exit; without the flag an uncaught Python error still exits 0.
- `build_viewer.py` needs the shared viewer core (`viewer_core.py`), looked for at `scripts/tools/dayz-3d-viewer/dayz_3d_viewer/` and then under `skills/_shared/`; `--viewer-core <path>` names another copy. The page loads three.js 0.185.1 from a CDN when it opens, so it needs a network connection.

Measured with Blender 5.1.1: steps 1 to 3 on the Bohemia rig FBX rebuild a reference `rig_dayz.json` byte for byte apart from its `space` label: the 8 helpers it holds (`LeftHandIKTarget`, the ninth name the script looks for, is not in that FBX), the 114 bones and the mesh.

## The rig and its traps

The rig is `animation_rig_character.fbx` from Bohemia's public DayZ-Misc repository: 114 bones with the player skeleton's exact names, and the `Male_body` mesh (7,499 vertices) skinned to it. Read it with Blender from the command line, not a Python FBX parser.

The importer leaves the mesh at object scale 0.01 and the armature at scale 1, so they live in separate spaces: the armature in a T pose in centimetres with its origin at the pelvis, the mesh in metres with its origin at the feet. Read bone world positions directly and the skeleton lands about 35 times off the mesh, and animating the raw rig pivots the mesh round far away points. Bind again in one space instead of trusting the FBX:

1. Read bone rest matrices in armature world (cm) and mesh vertices in mesh world (m).
2. Both are roughly a T pose, so align them with one uniform scale and a translation. Take the scale from the wrist's X against the mesh's half width (`RightHand` at about -58.6 cm, mesh edge at about ±0.703 m, so about 0.0101); match the bounding box centres and the feet's Z.
3. Turn into the viewer's Y up frame, `(x', y', z') = (x, z, -y)`. Blender and three.js are both right handed, so this is a rotation, not DayZ's change of handedness: DayZ model space is left handed and any map into it mirrors (such as the flip `(x, y, -z)` in `weapon-in-hands.md`). Coordinates from `rig_dayz.json` written into a `.p3d` as they are land mirrored.
4. Build a fresh skeleton and skinned mesh in that space; skinning and IK are then right.

The result, in metres in the viewer frame: head at 1.62, pelvis at 0.99, hands at ±0.59 across and 1.07 high, feet at about 0.09, and `RightHand_Dummy`, which is also `Weapon_Root`, at (-0.156, 1.368, 0.207).

The helpers (`RightHand_Dummy`, `Weapon_Root`, `LeftHand_Dummy` and the IK helpers) are empties parented to bones or to another helper; `Weapon_Root` hangs from `RightHand_Dummy`. Of the FBX's 38 empties, 17 import disabled in viewports (`hide_viewport`), those three among them, and keep `matrix_world` at the origin even after `view_layer.update()`; the other 21 agree with the formula below to 1e-5. So compose the world matrix by hand:

```text
armature world @ pose bone matrix @ T(0, bone length, 0) @ matrix_parent_inverse @ matrix_basis
```

For a helper parented to another helper, the parent's world replaces the first three factors. `extract_empties.py` does this and assumes one armature, parent bones without `use_relative_parent`, and every hidden helper parented.

## How the page works

For anyone maintaining `build_viewer.py`:

- It builds the skinned mesh and skeleton by hand from the rig JSON: local position and quaternion per bone, the hierarchy, four skin weights per vertex.
- Each limb has analytic two bone IK (law of cosines and a pole hint), the same maths as `ik_pose_to_seanim.py` in JavaScript. Each bone's rest direction is aimed at the solved child position, which keeps the rest roll, and its local quaternion is the parent's inverse world rotation times the wanted world rotation.
- It exports each bone's local quaternion directly, so the unfinished positions to rotations step of `ik_pose_to_seanim.py` is not on this path.
- Sliders multiply onto the IK result, so wrist roll and finger curl layer over it. The IK helpers do not roll the wrist, so wrist and finger control goes to `LeftHand`, `RightHand` and the finger bones.
- A key stores the authoring state (targets, slider values, the weapon's transform). Playback and export interpolate it, run IK and sliders again and bake local quaternions per frame and bone, so IK and sliders are the single source of truth.

`seanim_writer.py` has a working reader, `read_seanim`, for loading a rest pose. Nothing here writes `.anm`.

The viewer's quaternions are local to the rig's bones; DayZ's `.anm` and SEAnim bone frame puts a chain child on X (finger offsets in a vanilla DayZATool extract are `(length, 0, 0)`), and SEAnim translations are in centimetres. One change of basis per rig reconciles them ("Bone frame maps per rig"). A viewer SEAnim is valid in structure and right in the rig, and only the game says it is right for DayZ.

A weapon animation bound through a child `.asi` replaces no graph and loads next to other mods (`anim-graphs.md`, "Which changes collide"); do not raise the graph wall on such a plan.

## A fuller viewer

A later version of the viewer went well past what `build_viewer.py` writes. For anyone extending the page:

- Rig: the plugin's master rig (151 bones, mesh `zMale_body`, scale 1) instead of the 114 bone FBX with its two spaces.
- Start pose: the real in game grip, read off the live skeleton with a bone dump (`weapon-in-hands.md`, "The elbow cannot be derived offline"), hands and fingers within 0.4 cm of the game and the elbow as the engine's IK solved it.
- Finger sliders: absolute per finger and thumb, 0 an open hand and 100 a fist (the thumb at 100 moves to the in game aim grip), baked into the base pose rather than layered each frame.
- Overextension guard: elbow and knee by signed angle in the bending plane (limit 178 degrees), wrist by quaternion size, with a red joint dot and a warning.
- Editing: forward kinematics on any bone through a gizmo (smaller on fingers), move all, undo and redo, mirror left and right, a filterable list of the 151 bones. The weapon follows the right hand rigidly.
- Two export routes, both read back offline with the game as judge. The `.txa` route dumps the viewer's world pose and writes a `.txa` through the Blender plugin for Workbench to compile; it handles root motion and is the one for grips and full body clips (no script for it ships here). The SEAnim route is `seanim_export.py` then `DayZATool --generate-anim <f>.seanim 100`: rotations and rest only, for weapon bone and partial tracks. On the master rig its map is exact on the fingers, but `LeftHand` does not follow it, so never use it for the support wrist; and a melee strike on a rifle showed full body action clips (jam, unjam, melee) need the `.txa` route.

A grip is set by three levers (`weapon-in-hands.md`), and posing the wrist is not one: the firearms behaviour and an IK pose; geometric parity, moving the weapon to where the IK pose lands the hand (+2.4 cm on one rifle, done with the viewer's place weapon on hand function or the weapon gizmo); and finger curl, the one part of the hand the IK pose visibly drives. The viewer serves the last two. Turning `LeftHand` in the IK pose does almost nothing.

A native IK pose export is not worth it: a real IK pose keys seven IK bones the viewer's rig lacks (`LeftHandIKTarget`, the two hand origins, the two forearm directions and their origins) plus the fingers and `_Dummy` bones, and working mods reuse vanilla IK poses with matching geometry.

## Bone frame maps per rig

One change of basis per rig takes the viewer's bone frame to DayZ's. Child offsets lie on ±X in `rig_dayz.json` (the FBX rig) and on ±Y in the master rig's JSON. `--rest-pose` does not rebase rotations; it only masks bones.

`seanim_export.py` reads the rig family from the rest offsets:

- Bone axis: chain children of `Left` bones lie on the positive side of one axis and of `Right` bones on the negative side (Y on the master rig, X on the FBX rig). Only anatomical chains count, so helpers such as `RightHand_Dummy`, which the master rig holds at the grip, and its child `Weapon_Root` do not.
- Roll: through the chosen map, `LeftShoulder` to `RightShoulder` (in `Spine3`) and `RightHandRing` to `RightHandIndex1` (in each hand) must lie within 2 degrees of vanilla's across the bone direction. Both rigs read within 0.07 degrees.
- It refuses any other rig (a native Blender one, one mixing frames, one rolled 2 degrees or more on `Spine3` or a hand), an animation bone missing from the rig, and a missing `--rest-pose` file. A smaller roll passes and tilts a rotation of angle α by up to `4·asin(sin(α/2)·sin(roll/2))`, about 2.8 degrees for a 90 degree turn under a 2 degree roll.

Both maps mirror (determinant -1): offsets go through `M`, a quaternion's vector part through `-M`, and `w` is unchanged.

| Rig | Rotation `(x,y,z,w)` becomes | Rest offset `(x,y,z)` in m becomes, in cm | Status |
|---|---|---|---|
| Plugin master rig | `(-y,-z,x,w)` | `(y,z,-x)` | Calibrated against a DayZATool extract (the plugin's sample fire `.txa` against the `.anm`): exact to 0.00 degrees over 73 bone and frame pairs. |
| Bohemia FBX rig (`rig_dayz.json`) | `(-x,-z,-y,w)` | `(x,z,y)` | Derived offline from the master rig's map and the turn below. In game one `LeftArm` pose played as authored through it and wrong through the master rig's map. |

Offline, the FBX rig's bone frames are the master rig's turned 90 degrees about Z, `q_fbx = (y,-x,z,w)`: 113 of 114 rest rotations agree within 1 degree (the root `Pelvis` differs by that turn) and 109 of 113 rest offsets point the same way within 2.6 degrees (the four eyelid bones differ); the FBX rig is 1.2 percent larger. Against DayZATool extracts, the FBX rig's rest offsets match 77 of 77 bones of `p_erc_attackl_inplace_01_ras` within 5 degrees through its own map and 0 of 77 through the master's. Against frame 0 of the vanilla `p_1hd_erc_idle_low`, its rest rotations through its own map land within 0.87 degrees of the master rig's through the master's map (60 bones); through the master's map six land 90 degrees or more off. The test is `test_seanim_export.py` next to the script.

In game, one run: `LeftArm` alone keyed on the FBX rig straight ahead and 20 degrees up, a turn mostly about the bone's own X and Y where the maps disagree, was exported both ways, spliced alone into the DayZATool extract of `p_1hd_erc_idle_low.anm`, built and played through a child `.asi` of `player_main_1h_fruit.asi`. Through the FBX map the arm reached forward of the chest; through the master's it stuck out to the left. That clip's front is +Z in SEAnim space (left -X, up +Y). Only one bone and rotations were exercised.

What the maps do not cover:

- The root: `EntityPosition`, `Pelvis` and any bone without a parent are relative to the viewer's world. Neither map applies, and the script warns when it exports one.
- A full body action: a melee strike through the master's map flopped the player with root, pelvis and legs in, and sent the weapon to the back when masked to the vanilla bone set, because `RightHand_Dummy` was written at the rig's off bind offset. Head and body came right through the `.txa` route. The cause is not isolated.
- `--rest-pose <vanilla.seanim>` writes only the reference's bones (in game this fixed the flop), but every position comes from the rig. DayZATool marks most bones of vanilla action extracts RELATIVE (61 of 73 in `p_erc_jam_pm73_ras`, `Spine` to `Head` at `(0,0,0)`), an offset from rest inherited by children, while this script writes an ABSOLUTE clip (`weapon-anim-compile.md`, "Two conventions for what a key means"). Taking the reference's positions is not implemented.
- A bone the rig holds off bind is written off bind: the master rig's `RightHand_Dummy` at the grip (`(51.8, -29.3, 4.8)` cm through the map) sent the weapon to the back. Leave it and the `Weapon_` bones out of the reference.
- Bolt travel: per frame `Weapon_` positions are not exported by the page, and the script ignores per frame positions with a warning.
