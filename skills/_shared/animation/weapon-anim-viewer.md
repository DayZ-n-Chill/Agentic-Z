# Weapon animation authoring viewer (layer 2, interactive)

A repeatable way to author weapon animations: a web page that shows the weapon and the character on the player skeleton, where the user poses with IK handles and a keyframe timeline, the agent renders an offline preview, and the result is exported as SEAnim on the way to `.anm`. The six tools for it are in `skills/dayz-animation-pipeline/scripts/`.

It is the alternative to keying bone by bone in Workbench for questions like "how should this weapon be held" and "how should this reload look". For a seated rider use `rider-pose-solver.md`.

Nothing here is a vanilla fact that `P:\` can show: it is tool behaviour and measured results, each with its date and build. In-game playback is the only acceptance.

## The pipeline

```
[1] Viewer page: weapon, skinned character, skeleton overlay             agent builds
      IK handles (hands, feet, head, weapon) with two bone IK
      direct sliders (wrist roll, finger curl, torso lean, head)
      keyframe timeline (add, scrub, play, interpolate) and JSON export
[2] Offline preview: frames captured with a headless browser, as a GIF   agent
[3] seanim_export.py: animation JSON -> .seanim, read back as a check    agent
[4] DayZATool --generate-anim X.seanim -> X.anm                          user
[5] Bind it in an instance file, pack, sign, TEST IN GAME                user
```

## The tools, in the order they run

All in `skills\dayz-animation-pipeline\scripts\`. They pass their files through the folder named by `DAYZ_ANIM_SCRATCH` (default `<tempdir>\dayz-anim-pipeline`).

1. `fbx_extract.py` (Blender) dumps the rig FBX to `rig_raw.json`: rest matrices, parents and lengths of every bone, every empty, and the body mesh.
2. `extract_empties.py` (Blender, same FBX) writes the helper empties through their parent chain to `empties_armworld.json`. It exits 1 and writes nothing when the FBX has no `RightHand_Dummy` (the weapon anchor of the survivor skeleton, `P:\DZ\anims\cfg\skeletons.anim.xml:115`). It removes the previous run's file before the FBX import, read only or not, so a failed run leaves step 3 nothing stale to build on; a file it cannot remove stops it with that error.
3. `build_rig_dayz.py` (Python, numpy) aligns bones and mesh and writes `rig_dayz.json` in the viewer's frame, with the helpers as its `anchors`.
4. `extract_weapon.py` (Python, the DayZ fork of py3d) writes the weapon's first visual LOD and memory points to `weapon.json`. It is independent of steps 1 to 3.
5. `build_viewer.py` (Python) writes the page from `rig_dayz.json` and `weapon.json`. On load and on "Ready pose" the page puts the weapon grip at a fixed idle point, (-0.06, 1.02, 0.32) in the viewer frame. The `RightHand_Dummy` anchor is used only by `poseReady()`, which no button calls; run it from the browser console as `window.__VIEWER__.poseReady()`.
6. `seanim_export.py` (Python) turns the page's animation JSON into SEAnim; its paths are arguments.

```cmd
blender -b --python-exit-code 1 --python skills\dayz-animation-pipeline\scripts\fbx_extract.py -- <animation_rig_character.fbx>
blender -b --python-exit-code 1 --python skills\dayz-animation-pipeline\scripts\extract_empties.py -- <animation_rig_character.fbx>
python skills\dayz-animation-pipeline\scripts\build_rig_dayz.py
python skills\dayz-animation-pipeline\scripts\extract_weapon.py <weapon_mlod.p3d>
python skills\dayz-animation-pipeline\scripts\build_viewer.py <out.html>
python skills\dayz-animation-pipeline\scripts\seanim_export.py --anim weapon_anim.json --rig <scratch>\rig_dayz.json --out clip.seanim
```

- The two Blender steps take the FBX after `--`, or from `DAYZ_ANIM_RIG_FBX`, or by its file name in the current folder. Give both the same FBX. `extract_weapon.py` takes the `.p3d` as its argument or from `DAYZ_ANIM_WEAPON_P3D`.
- Run the Blender steps with `--python-exit-code 1` and stop at the first exit code that is not zero. Without that flag an uncaught Python error still exits 0.
- `build_viewer.py` needs the shared viewer core (`viewer_core.py`), which it looks for at `scripts/tools/dayz-3d-viewer/dayz_3d_viewer/` and then under `skills/_shared/`; `--viewer-core <path>` names another copy. The page loads three.js 0.185.1 from a CDN when it opens, so it needs a network connection; three.js is not inlined.
- No headless browser script for a self test or for the preview capture of step [2] ships here.

Measured 2026-10-02 with Blender 5.1.1: steps 1 to 3 on the Bohemia rig FBX rebuilt a reference `rig_dayz.json` byte for byte except its `space` label: the 8 helpers it holds (`LeftHandIKTarget`, the ninth name the script looks for, is not in that FBX), the 114 bones and the mesh.

## Where the rig comes from, and its traps

The source is the character rig FBX from Bohemia's public DayZ-Misc repository (`animation_rig_character.fbx`): an armature of 114 bones with the player skeleton's exact names, and the `Male_body` mesh (7,499 vertices) skinned to it. Read it with Blender headless, not a Python FBX parser.

### The FBX holds mesh and armature in different spaces

Measured 2026-06-28. The importer leaves the mesh at object scale 0.01 and the armature at scale 1, so the two live in separate spaces: the armature in a T pose, in centimetres, with its origin at the pelvis; the mesh in meters with its origin at the feet. The bones do not coincide with the mesh. Deformation works in Blender only through the modifier's relative transform, and reading bone world positions directly puts the skeleton about 35 times off the mesh. Animating the raw rig then pivots the mesh around far away points, which looks like broken deformation.

The fix is to bind again in one consistent space, not to trust the FBX's bind:

1. Read the bone rest matrices in armature world (cm) and the mesh vertices in mesh world (m).
2. Both are roughly a T pose, so align them with one uniform scale and a translation. Take the scale from a reliable pair: the wrist bone's X against the mesh's half width on X (`RightHand` at about −58.6 cm, mesh edge at about ±0.703 m, so a scale near 0.0101). Translate to match the bounding box centres, and match Z at the feet.
3. Rotate into the viewer's frame, Y up: `(x', y', z') = (x, z, −y)`. Blender's Z up frame and three.js's Y up frame are both right handed, so this is a rotation. It is not DayZ's change of handedness: DayZ model space is left handed, and any map into it mirrors (for example the flip `(x, y, −z)` in `weapon-in-hands.md`).
4. Build a fresh skeleton and skinned mesh in that space. The bind is then consistent, and skinning and IK are correct.

Landmarks of the result (viewer frame, Y up, right handed, meters): head at 1.62, pelvis at 0.99, hands at ±0.59 across and 1.07 high, feet at about 0.09. The weapon anchor `RightHand_Dummy`, which is also `Weapon_Root`, is at (−0.156, 1.368, 0.207).

Because that frame is right handed, coordinates from `rig_dayz.json` written into a `.p3d` as they are land mirrored.

### Helper "bones" are empties, and 17 of them hide their world matrix

`RightHand_Dummy`, `Weapon_Root`, `LeftHand_Dummy` and the IK helpers are empties in the FBX, parented to bones or to another helper (`Weapon_Root` hangs from `RightHand_Dummy`). Their world matrix has to be composed by hand with the child of bone formula:

```
armature world @ pose bone matrix @ T(0, bone length, 0) @ matrix_parent_inverse @ matrix_basis
```

For a helper whose parent is another helper, the parent's world takes the place of the first three factors. `extract_empties.py` does this; it assumes what this FBX has: one armature, parent bones without `use_relative_parent`, and every hidden helper parented.

Measured with Blender 5.1.1: plain `matrix_world` will not do. Of the FBX's 38 empties, 17 import disabled in viewports (`hide_viewport`), `RightHand_Dummy`, `Weapon_Root` and `LeftHand_Dummy` among them, and those keep `matrix_world` at the origin before and after `view_layer.update()`. The other 21, 16 of them parented to bones, agree with the formula to 1e-5 either way.

## The bone frame gap, and why the game is the judge

The quaternions the viewer exports are local to the rig's bones. DayZ's `.anm` and SEAnim bone frame puts a chain child on X: in a vanilla SEAnim extracted with DayZATool, finger phalanx offsets are `(length, 0, 0)`. SEAnim local translations are in centimetres (rig meters times 100), also read from that reference.

One change of basis per rig reconciles the two (established 2026-10-02). The maps are in "Route C bone-frame maps, per rig" below.

What still holds: a SEAnim from the viewer is valid in structure (it reads back, its bone names are the skeleton's, its frame rate is right) and correct in the rig, and only playing it in game confirms that it is right for DayZ. Plan the in-game check from the first day.

## How the page works

For anyone maintaining `build_viewer.py`:

- The skinned mesh and skeleton are built by hand from the rig JSON (local position and quaternion per bone, the hierarchy, and four skin weights per vertex).
- Two bone analytic IK per limb (law of cosines plus a pole hint), the same mathematics as `ik_pose_to_seanim.py`, written in JavaScript. It is applied by aiming each bone's rest direction to its child at the solved child position, which keeps the rest roll, and setting the bone's local quaternion to the parent's inverse world rotation times the wanted world rotation.
- The page exports each bone's local quaternion directly. The unfinished positions to rotations step of `ik_pose_to_seanim.py` is not on this path.
- The direct sliders multiply onto the IK result, so wrist roll and finger curl layer over the IK instead of resetting to rest. The IK helpers do not roll the wrist, so wrist and finger control goes to the raw `LeftHand` and `RightHand` and the finger bones.
- A keyframe stores the authoring state (target positions, slider values, the weapon's transform). Playback and export interpolate the state, run the IK and sliders again, and bake local quaternions per frame and bone. The IK and sliders are the single source of truth.

`seanim_writer.py` has a working reader (`read_seanim`); use it to load a rest pose. A Python SEAnim reader and writer exist here; nothing here writes `.anm`.

## The wall

The graph wall applies only when the plan replaces the player graph. A weapon animation bound through a child `.asi` replaces nothing and loads next to other mods (`anim-graphs.md`, "Which changes collide"). Do not state the wall on a weapon animation plan that binds through a child `.asi`.

## A fuller viewer: what a second pass adds

A later version of this viewer (2026-07-05) went well past the page `build_viewer.py` writes. Its state, for anyone extending that page:

- **Rig.** The plugin's master rig (151 bones, mesh `zMale_body`, scale 1) in place of the 114 bone FBX with its two spaces.
- **Start pose.** The real in-game grip, read off the live skeleton with a bone dump (`weapon-in-hands.md`, "The elbow cannot be derived offline"): hands and fingers within 0 to 0.4 cm of the game, and the elbow the one the engine's IK resolved.
- **Finger sliders.** Absolute, per finger and thumb: 0 is an open hand, 100 a fist; the thumb at 100 moves toward the in-game aim grip. They are baked into the base pose, not applied as a layer each frame.
- **Hyperextension guard.** Elbow and knee by the signed angle in the flexion plane (limit 178 degrees), the wrist by quaternion magnitude; a red joint dot and a warning line.
- **Editing.** Forward kinematics on any bone (click a joint dot for a gizmo, sized down for finger bones), move everything, undo and redo, mirror left and right, a filterable list of the 151 bones. The weapon follows the right hand rigidly.
- **Two export routes to `.anm`**, both checked by reading back offline, with the game as the judge:
  - **Route A, the standard one.** Dump the viewer's world pose and write a `.txa` through the Blender plugin; Workbench compiles it. It handles root motion. Use this for the grip. No script for this route ships here.
  - **Route C, command line.** `seanim_export.py` (`skills/dayz-animation-pipeline/scripts/`), then `DayZATool --generate-anim <f>.seanim 100`. Rotations and rest only. On the plugin's master rig the quaternion map is exact on the fingers, but `LeftHand` does not obey it (the wrist is a separate process), so do not use Route C for the support hand's wrist. Route C is also not valid for full body action clips (jam, unjam, melee): a melee strike on a rifle (2026-06-30) confirmed that full body goes through Route A. Use Route C for weapon bone and partial tracks only.

### Authoring a grip with the viewer

Verified in game on one rifle. The grip is set by three levers, and "posing the wrist" is not one of them (`weapon-in-hands.md`):

1. the firearms behaviour and an IK pose;
2. geometric parity: move the weapon to where the IK pose lands the hand (the fix on that weapon was +2.4 cm), with the viewer's place weapon on hand function or the weapon gizmo;
3. finger curl, the one thing about the hand that the IK pose drives visibly.

The viewer serves levers 2 and 3. Rotating `LeftHand` in the IK pose does almost nothing.

### A native IK pose export is not trivial

A real IK pose keys eight IK bones that the viewer's rig lacks (the two hand IK targets, the two hand origins, the two forearm directions and their origins) plus fingers and the `_Dummy` bones. A usable export would have to synthesize those eight from the viewer's pose. The return is doubtful, since working mods reuse vanilla IK poses with matching geometry.

## Route C bone-frame maps, per rig

Dated 2026-10-02. One change of basis per rig takes the viewer's bone frame to DayZ's. The bone axis differs between the two rigs: child offsets lie on ±X in `rig_dayz.json` (the FBX rig) and on ±Y in the plugin master rig's JSON. `--rest-pose` does not rebase rotations; it only masks bones.

`seanim_export.py` reads the rig family from the rest offsets:

- **Bone axis.** Chain children of `Left` bones sit on the positive side of one axis and children of `Right` bones on the negative side (Y in the master rig, X in the FBX rig). Only anatomical chains count (shoulder, arm, forearm, hand, finger, leg and foot bones and their roll bones), so helpers such as `RightHand_Dummy`, which the master rig holds at the grip, and its child `Weapon_Root` do not.
- **Roll.** Through the chosen map, the direction from `LeftShoulder` to `RightShoulder` (in `Spine3`) and from `RightHandRing` to `RightHandIndex1` (in each hand) must lie within 2 degrees of vanilla's direction across the bone. Both rigs read within 0.07 degrees.
- **Refusals.** Any other rig (a native Blender one, one mixing frames, one rolled about its bone axes by 2 degrees or more on `Spine3` or a hand), an animation bone missing from the rig, and a `--rest-pose` file that does not exist.
- **Not seen.** A smaller roll, which tilts a rotation of angle α by up to `4·asin(sin(α/2)·sin(roll/2))` (about 2.8 degrees for a 90 degree turn under a 2 degree roll), and a roll confined to bones those pairs do not reach.

Both maps mirror (determinant −1): offsets go through `M`, the vector part of a quaternion through `−M`, and `w` is unchanged.

| Rig | Rotation `(x,y,z,w)` becomes | Rest offset `(x,y,z)` in m becomes, in cm (×100) | Status |
|---|---|---|---|
| Plugin master rig | `(−y,−z,x,w)` | `(y,z,−x)` | Calibrated 2026-06-29 against a reference extracted with DayZATool (the plugin's sample fire `.txa` against the `.anm` extract): exact to 0.00 degrees over 73 bone and frame pairs. |
| Bohemia FBX rig, `rig_dayz.json` from `build_rig_dayz.py` | `(−x,−z,−y,w)` | `(x,z,y)` | Derived offline 2026-10-02: the calibrated map after the turn measured below; no rotation pair. In game the same day one `LeftArm` pose played as authored through it and wrong through the master rig's map. |

**Measured offline, 2026-10-02** (the FBX rig rebuilt by `fbx_extract.py` and `build_rig_dayz.py`). The FBX rig's bone frames are the master rig's turned 90 degrees about Z, `q_fbx = (y,−x,z,w)` of the master rig's: 113 of 114 rest rotations agree within 1 degree (the root `Pelvis`, relative to the world, differs by that turn) and 109 of 113 rest offsets point the same way within 2.6 degrees (the four eyelid bones differ). The FBX rig is 1.2 percent larger. Against DayZATool extracts of vanilla clips: rest offsets through the master rig's map match 78 of 78 bones of `p_erc_attackl_inplace_01_ras` within 5 degrees (median 0.00, length ratio 1.000); the FBX rig through that same map matches 0 of 77 (median 90 degrees), and through its own map 77 of 77 (median 0.00, ratio 1.012). A second reference splits the same way (35 of 36, 0 of 34, 34 of 34). Rotations: against frame 0 of the vanilla `p_1hd_erc_idle_low` (absolute: rest rotations of 180 degrees read 175 to 180 there), the FBX rig's rest through its own map lands within 0.87 degrees per bone of where the master rig's map lands the master rig (60 bones); through the master rig's map six bones land 90 degrees or more off (`RightShoulder` by 176.9). The regression test is `test_seanim_export.py` next to the script.

**Played in game, 2026-10-02** (DayZDiag 1.29.163709, one run). `LeftArm` alone was keyed on the FBX rig in Blender 5.1.1, straight ahead and 20 degrees above horizontal: a turn mostly about the bone's own X and Y, where the two maps disagree (the sideways raise in `blender-headless-authoring.md` turns about Z, which both maps read alike). The pose went through `seanim_export.py`, which read the rig as the FBX family, and for comparison through the master rig's map. Each output's `LeftArm` track was spliced alone into the DayZATool extract of the vanilla one handed idle `p_1hd_erc_idle_low.anm`, built with `DayZATool --generate-anim` and played through a child `.asi` of `player_main_1h_fruit.asi` on an item held in the right hand. Through the FBX map the left arm reached forward of the chest, slightly above horizontal. Through the master rig's map it stuck out to the character's left, a little behind the shoulder line. A second take of each agreed, and each landed on the side that offline forward kinematics on the vanilla idle predicted (elevation was not measured). The character's front was read as +Z of that clip's SEAnim space (left −X, up +Y): its toes point to +Z, its forearms swing toward +Z of the upper arms and its shins toward −Z of the thighs. Scope: one bone, rotations only (the bone offsets came from the vanilla clip, so the offset map was not exercised), one run; the master rig was not played.

What the maps do not cover:

- **The root.** `EntityPosition`, `Pelvis` and any bone without a parent are relative to the viewer's world. Neither map applies, and the script warns when it exports one.
- **A full body action.** In game the master rig's map has played one, a melee strike on a rifle (2026-06-30). With root, pelvis and legs included, the player flopped. Masked to the vanilla bone set, the player stood but the weapon went to the back: `RightHand_Dummy` was written at the rig's offset, which is not the bind one. Head and body came right through Route A. The bone convention is the suspected cause, but the switch changed more than the rotation map, so the cause is not isolated. Route C stays for weapon bone and partial tracks.
- **`--rest-pose <vanilla.seanim>`** writes only the reference's bones (in game this fixed the flop). Every position comes from the rig, not from the reference: DayZATool marks most bones of vanilla action extracts RELATIVE through SEAnim bone modifiers (61 of 73 in `p_erc_jam_pm73_ras`, with `Spine` to `Head` at `(0,0,0)`), and in SEAnim a RELATIVE translation is an offset from rest inherited by child bones, while this script writes an ABSOLUTE clip (`read_seanim` returns the modifiers; the export writes none). That is the split described in `weapon-anim-blender.md`, "Two conventions for what a key means". Taking the reference's positions and writing those zeros as offsets is not implemented in `seanim_export.py`.
- **A bone the viewer rig holds off bind is written off bind.** The master rig's `RightHand_Dummy`, which the viewer moved to the grip (`(51.8, −29.3, 4.8)` cm through the map), sent the weapon to the back in game. The confirmed strike dropped it, and the `Weapon_` bones, from the clip. Leave them out of the reference.
- **Bolt travel.** `Weapon_` positions per frame are not supported: the viewer page does not export them, and the script warns about and ignores positions per frame in an animation.
