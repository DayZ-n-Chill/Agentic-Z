# A custom player weapon animation, from Blender to the game

The whole route for a weapon animation on the playable character: author in Blender, export `.txa`, compile to `.anm` in Workbench, map it in an instance file, bind it in script, build and test. It is written for someone who has to carry out every step.

How to read it:

- A **vanilla fact** cites the file on `P:\` (DayZ 1.30).
- **Plugin** facts describe the DayZ animation plugin for Blender (`DayzAnimationTools`, in its original build and its maintained fork) and its demo mod. They cannot be checked on `P:\`; each is marked where it matters.
- **Measured** results say what was measured and on which build.
- "Open questions" at the end lists what is not confirmed.

Five common mistakes are corrected here, and each correction is explained in place:

1. Keep the `{GUID}` prefixes in instance files. Do not strip them.
2. A weapon states clip is not always exactly 3 frames.
3. The `ikpose_` keys are settings of a graph node, not of the template or any config.
4. `reloadAction` in the weapon's config does not drive the reload animation.
5. There is no supported way to pick a pose per attachment inside the register callback.

## 1. What a custom player weapon animation is

It is not wired through `config.cpp` animation keys. It reaches the player through three separate layers, and it does not edit the player graph:

1. **Authoring.** Key the player rig in Blender and export `.txa` (text) with the plugin. Workbench compiles `.txa` to `.anm` (binary).
2. **Mapping.** A text instance file (`.asi`) for the weapon maps state names of the form `WeaponOperations.<column>.<state>` to the `.anm` files, and inherits everything else from a parent chain: the weapon's instance, then `player_main_rifle.asi`, then `player_main.asi`.
3. **Binding.** One script call, `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` (`P:\scripts\3_game\dayzplayer.c:243`), binds the weapon class to the instance, an IK pose and a weapon states clip. A second, `AddItemBoneRemap(itemClass, pairs)` (`P:\scripts\3_game\dayzplayer.c:252`), maps the weapon model's part selections to the player skeleton's `Weapon_` bones. Vanilla binds every weapon this way, for example `AKM_Base` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`).

Because nothing in the graph is replaced, several weapon animation mods load together. The "one animation mod at a time" wall is about mods that replace the player graph (`anim-graph.md`, "Which changes collide"). Vehicles are not an exception: one vehicle class's rider pose can be bound through a child instance as well (`vehicle-rider-ik-pose.md`).

Three kinds of clip exist per weapon. Do not mix them up:

| Clip | What it is | Where it is named |
|---|---|---|
| IK pose | One pose: where hands and fingers sit on the gun. | The `IkPose` line of the `.asi`; the fourth argument of `AddItemInHandsProfileIK`. |
| Weapon states (`w_<weapon>_states.anm`) | Only the `Weapon_` bones, one frame per start state of the weapon (bolt closed, open, jammed). | The fifth argument; `SetInitState` reads it. |
| Action clips (reload, fire, chamber, jam) | Authored as differences, roughly from the shoulders down, played over the idle. | The `Lines` of the `.asi`. |

The action clips play on top of the weapon states clip and override those bone transforms while they play (not checked on `P:\`; consistent with the comment on `SetInitState`, `P:\scripts\3_game\human.c:1108` to `:1112`, which says each frame of the states animation is one init state).

### Two routes

| | Route A: `.txa` and Workbench | Route B: SEAnim and DayZATool |
|---|---|---|
| Authoring file | `.txa` from the plugin in Blender | SEAnim (open format) |
| To `.anm` | Workbench "Register resource and import", later "Reimport Resource" | `DayZATool --generate-anim file.seanim` |
| Tooling | The maintained plugin fork | A closed .NET program; needs .NET Framework 4.5 |
| Rig quality | Correct: the master rig with IK helpers | Extracted rigs come out wrong for anything using empties, which the IK helper bones are; local bone axes come out inverted (not checked on `P:\`) |
| Use for | Player weapon animation (this guide) | Extracting reference meshes and clips |

Use Route A. It is what the plugin's demo mod uses. Route B is the fallback when Route A is blocked; it works with the same instance file and the same packing, but its extracted rig is a reference, not a clean round trip.

Do not use `.rtm` for a player weapon animation. It is the most common wrong turn (`skeletal-rtm.md`).

## 2. Tools and setup

### Blender version: settle this first

The plugin's README says it needs at least Blender 3.6.8 and recommends exactly that. This is right for the original plugin.

The maintained fork uses newer Blender calls and does not run on 3.6.8:

- its `.txa` importer calls `action.fcurve_ensure_for_datablock(...)`, which is the slotted actions interface of Blender 4.4 and later, and has a helper named for Blender 5.1;
- its `bl_info` declares `'blender': (2, 80, 0)`, which is meaningless.

So: the maintained fork needs Blender 4.4 or later, 5.x included; the original needs 3.6.8 to 4.0 (on 4.1 and later it fails with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`). Check the plugin's import code against the Blender in use, not the declared version. That the fork fails on 3.6.8 is inferred from those calls; it was not run there.

Files saved in Blender 5.x do not open in 4.2, and the plugin's sample `.blend` files were saved in 3.6.8.

### Installing the plugin

The download is a plain folder, not a zip, so Blender's "Install from file" does not work.

1. Copy the plugin's `DayzAnimationTools` folder into Blender's addons folder: `%AppData%\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`.
2. In Blender open Edit, Preferences, Add-ons, search for "DayZ" and tick "Dayz Animation Tools".

### Where the plugin's tools are

- A menu "DayZ Animation Tools" in the 3D view's header, with Import, Export and Tools.
- File, Import and File, Export entries: "DayZ Animation (.txa)" and "DayZ Object (.txo)".
- The Event Manager: the 3D view's side panel (N), tab "Dayz Animation Tools", section "Events".

### DayZ Tools, Workbench and the work drive

The work drive is `P:\` with the vanilla data unpacked into `P:\DZ\` and `P:\scripts\`. `/dayz-preflight` checks it and `/dayz-workdrive` mounts it. The demo mod's `SetupWorkdrive.bat` makes a junction on `P:\` for any folder that holds a `Workbench\dayz.gproj`. Setting Workbench as the default program for its files gives a quick launch (F6) and kill (F10) from its resource browser.

### The vanilla files to read

- Player workspace: `P:\DZ\anims\workspaces\player\player_main\` (the `.asi`, `.ast`, `.aw`, `.agr` and `.agf` files).
- Compiled clips: `P:\DZ\anims\anm\player\`. IK poses are in `ik\weapons\`, reloads and states in `reloads\<weapon>\` (for the AKM, `w_akm_states.anm` and 22 action clips).
- Player skeleton bone list: `P:\DZ\anims\cfg\skeletons.anim.xml`, which the Workbench project names as its skeleton definitions.

### DayZATool (Route B)

`--extract-anim` (`.anm` to SEAnim), `--extract-model` (`.xob` to SEModel), `--generate-anim file.seanim` (SEAnim to `.anm`). It takes a scale as its second argument (100) and no output path: the result is written next to the input. Expect to tune the scale by hand. Blender importers: `io_scene_seanim`, `io_model_semodel`.

## 3. The rig

### Open the master rig

The plugin's sample assets include `JD_Master_Rig (No IK Bones).blend`. Its armature is the player skeleton with vanilla bone names, with custom shapes on the bones most often grabbed (hand, forearm, knee, foot).

Bone names must match the player skeleton exactly, in case and spelling, or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not move. The skeleton cannot be restructured (`tooling-and-walls.md`, walls 4 and 5).

### Bone groups

The checked list by zone is `player-skeleton.md`. In short:

| Group | Bones |
|---|---|
| Root | `Scene_Root`, `EntityPosition`, `Collision` |
| Spine | `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3` |
| Head | `Neck`, `Neck1`, `Head` |
| Arms | `LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand`, and the `Right` ones |
| Fingers | Thumb, index, middle, ring and pinky chains on each hand, plus roll and extra helpers |
| Legs | `LeftUpLeg`, `LeftUpLegRoll`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase`, and the `Right` ones |
| Hand anchors | `RightHand_Dummy`, `LeftHand_Dummy` (`P:\DZ\anims\cfg\skeletons.anim.xml:115`, `:116`) |
| Weapon | `Weapon_Root`, `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`, `Weapon_Bone_01` to `Weapon_Bone_06` (`P:\DZ\anims\cfg\skeletons.anim.xml:254` to `:264`) |

### Weapon bones and the right hand

- An item in the right hand is a child of `RightHand_Dummy`.
- Current clips move the gun with `RightHand_Dummy`, not `Weapon_Root`, which is legacy (plugin code; not checked on `P:\`).
- The player skeleton drives the weapon's parts through `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet`, and six free slots `Weapon_Bone_01` to `Weapon_Bone_06` for any other moving part. What each slot means is per weapon; vanilla rifles map `charging` to `Weapon_Bone_01` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1579`).
- Do not use the older bones in the group marked for removal (`player-skeleton.md`, "Marked for removal: do not use").
- There are no magazine in hand bones. The engine follows the magazine through `LeftHand_Dummy`.

### "Add Survivor IK Bones": only for IK pose work

Run Tools, "Add Survivor IK Bones" with the armature selected. It creates `LeftHandOrigin` (parent `RightHand_Dummy`), `RightHandOrigin` (parent `RightShoulder`), `RightForeArmDirection` and `LeftForeArmDirection` (parents the shoulders), and adds Blender IK constraints on `LeftHand` and `RightHand` with a chain length of 5, the forearm direction bones as pole targets and pole angles of −127.9 degrees (left) and +45.3 degrees (right).

- Run it before importing or authoring any IK pose. If an IK `.txa` is imported onto a rig without these bones, the importer prints "Ignoring survivor IK bone ... because Tools > Add Survivor IK Bones is required first!" and drops those tracks.
- Do not key, or even add, these helpers for clips that are not IK poses. Stray keys corrupt full body and difference exports; the exporter and the plugin's model config generator skip them.
- The plugin exports `LeftHandIKTarget` as a copy of `LeftHandOrigin`; it is not keyed in Blender.

The game's skeleton has these helpers (`RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget` and the forearm direction bones, `P:\DZ\anims\cfg\skeletons.anim.xml:149` to `:157`); the plugin's rig without IK bones does not, which is why the tool adds them.

### The `ikpose_` keys

Which helper plays which IK role is set in the graph's weapon IK node (`AnimSrcNodeWeaponIk`), in a block of `ikpose_` keys:

```
ikpose_chainoffset        = RightHandOrigin
ikpose_weaponoffset       = RightHand_Dummy
ikpose_secchainoffset     = LeftHandIKTarget
ikpose_chainmiddledir     = RightForeArmDirection
ikpose_chainmiddlediro    = RightHandOrigin,RightForeArmDirectionOrigin
ikpose_secchainmiddledir  = LeftForeArmDirection
ikpose_secchainmiddlediro = LeftHandOrigin,LeftForeArmDirectionOrigin
```

That is `P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35` (`ikpose_chainoffset` first). The same node holds the basic setup above it (`hand = RightHand`, `weapon = RightHand_Dummy`, `weaponrotator = RightArm`, the two chains and their axes, `P:\DZ\anims\workspaces\player\player_main\combat.agf:19` to `:27`) and a comment that explains the hierarchy: the root is the right hand, which is not exported; `RightHand_Dummy` is where the weapon is; `LeftHandIKTarget` is where the left hand is on the weapon; `RightHandOrigin` is the inverse transform of where the hand originally was.

The block occurs 14 times in the 1.30 player sub-graphs (`actions.agf` 7, `combat.agf` 2, `gestures.agf` 1, `locomotion.agf` 2, `master.agf` 1, `vehicles.agf` 1). The keys are not in `player_main.ast`, the workspace, `config.cpp` or `model.cfg`, which is why a search of those finds nothing. Do not leave out the two keys ending in `diro`.

## 4. Starting from a vanilla pose or clip

### Importing a `.txa`

1. Select the armature first, or the importer stops with "Select an armature first!".
2. File, Import, "DayZ Animation (.txa)".
3. Options: Scale Factor (default 1.0); Translation and Rotation Keys (on); Scale Keys (off, because DayZ ignores scale).

The importer sets every bone to quaternion rotation, takes the scene's frame rate and range from the file, turns IK constraints off while importing and on again after, and keeps the action with a fake user. Several files import as separate actions, with the earlier one pushed to an NLA strip.

### Importing without the Blender window

To read poses from a script, with the plugin's folder at `<plugin>`:

1. Add `<plugin>` to `sys.path`, `import DayzAnimationTools`, call `DayzAnimationTools.register()`, then with the armature active call `bpy.ops.import_scene.txa(filepath=..., files=[{"name": basename}])`.
2. The importer refers to a name, `SURVIVOR_IK_ANIM_BONES`, that the plugin does not define (it defines a left and a right list), which raises `NameError`. Before importing, set it: import the plugin's `Import.ImportTxa` module and assign `SURVIVOR_IK_ANIM_BONES` the left list plus the right list from its `Types.Txa` module.
3. For the pure forward kinematics pose, which is what the `.anm` holds: the plugin turns constraints on again after import, so turn pose bone constraints off after the import, set frame 0 and read `armature.matrix_world @ pose_bone.matrix`.
4. Rotation and translation are both applied. Arm bone translation is about the rest offset, but the root's (`Pelvis`) translation is real (the soft aim pose crouches about 3.5 cm), so keep it.

### Choose the closest vanilla base

Copy the clip closest in feel; this is the recommended way to start.

- For the grip, start from the plugin's sample idle pose nearest the target, for example `Rifle_Erect_Idle_Ras (Soft_Aim).txa` (soft aim is where a reload naturally starts), or the pistol one for pistols.
- For reload and fire, take timing and feel from the nearest vanilla action.

The plugin's sample base poses cover rifle, pistol, one handed, two handed, heavy, ladder, spear, unarmed and surrender, each with erect, crouched and prone idles in lowered and raised forms, and sample scenes with IK set up for a rifle (M4), a pistol, a shovel, a sea chest and an apple.

### Putting the weapon model in the scene (optional, usual)

1. In Object Builder, split the model's moving parts (body, bolt, trigger, magazine, magazine release, bullet) each into its own empty LOD and export each as FBX with "export current LOD only", normals off, master scale 100.
2. Import each FBX into Blender. Before constraining, set its rotation to X 0, Z 90 (a part comes in with X at 90).
3. Give each part a Child Of constraint to the armature with the matching weapon bone as sub-target.

The weapon bones float in front of the right chest by default; the whole weapon hangs from `RightHand_Dummy`.

## 5. Authoring, by kind of clip

Rules that hold for all of them:

- **30 frames per second.** Set "Override Fps" to 30 in the exporter (0 uses the scene's rate). 20 to 25 gives a slower, deliberate feel; 60 is valid. Every vanilla AKM clip extracted for section 12 runs at 30.
- **Never key scale.** DayZ ignores bone scale; scale keys are off by default on import and export.
- **Leave the legs to locomotion.** Idle and aim poses key the legs only as the static idle. Reload, fire and state clips key from the shoulders down: the plugin's bone list for survivor reloads has no leg bone.

### The IK pose (grip)

Key four controls (insert keys on selected channels only):

| Control | Role |
|---|---|
| `LeftHandOrigin` | Where the support hand is. It is a child of `RightHand_Dummy`, so it follows the weapon. |
| `RightHandOrigin` | Position and rotation of the whole grip relative to the shoulder. |
| `LeftForeArmDirection` | Left elbow direction. |
| `RightForeArmDirection` | Right elbow direction. |

Export type "Survivor IK 2h" or "Survivor IK 1h". The plugin restricts the export to the survivor IK bone list, writes one keyframe and sets the end frame to 1. Do not select bones first and do not treat it as a clip of several frames.

What the pose can and cannot do, measured in game on a custom submachine gun (2026-06-17): rotating `LeftHand` or the IK helpers does not turn the support wrist, because the engine's IK lines the hand up with the weapon again. The pose visibly drives the finger curl. To change how the support hand is oriented, match the weapon's geometry to a reference whose hand already sits that way (`weapon-in-hands.md`).

A vanilla IK pose file holds 2 frames at 30 frames per second, and the second is a byte for byte copy of the first, so it is one pose (read from the extracted AKM pose). Write a duplicate frame if a tool wants at least two. Poses are shared: the AKM's instance names the `izh18` pose (`IkPose` at `P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:6`).

### The sight line

The sight camera is anchored by the weapon model's `eye` memory point (on the AKM about 5.2 cm above the bore, on the bore's Z). Alignment in the sights comes from the weapon's geometry and the IK pose, not from leg or locomotion bones. The model rules that matter: `usti hlavne` and `konec hlavne` share Y and Z, and `bolt_axis` is parallel to the bore. If the iron sights look canted, fix the weapon's frame, stock angle and the eye and bore line (`weapon-in-hands.md`).

### Fire (about 7 frames at 30)

- Key only what moves: usually the right index finger and `Weapon_Bolt`.
- Start with the trigger already pulled on frame 0.
- Move `Weapon_Bolt` out and back over the frames. The plugin's SVD sample moves it 0, 0.031, 0.090, 0.121, 0.081, 0.040 along X.
- Add the bullet eject event (`#event 1 "Weapon_BulletEject"` in that sample).
- A belt fed weapon's belt motion goes here too.

### Weapon states (`w_<name>_states`)

Author three frames, one per state of the weapon:

| Frame | State |
|---|---|
| 0 | bolt closed |
| 1 | bolt open |
| 2 | jammed |

- Only the `Weapon_` bones matter. Use the plugin's "weapon bones" selection.
- In Blender set the end frame to 2, not 1, or only two frames are written and the open and jammed states break.
- Export as Additive, "Selected Bones Only", 30 frames per second.
- At run time the engine picks a frame with `SetInitState(int pFrameIndex)` (`P:\scripts\3_game\human.c:1112`).

**The stored clip is not always 3 frames.** Three frames is the authoring intent. Workbench trims consecutive keys that are nearly the same, so across the vanilla `w_*_states.anm` clips the stored key count per channel is 2, 3 or 4 (measured on the 47 clips of 1.29; the 1.30 unpack holds 50). `w_akm_states.anm` is 2 frames with two distinct poses: `Weapon_Bolt` at (0, 0, 0) then (5.61, 0, 0), and `Weapon_Bullet` near 0 then (−17.38, −4.02, 4.03), ejected. How many start states the engine reads per weapon cannot be told from the file offline.

**The bolt's rest position comes from this clip, not from an action clip** (measured in game on a custom submachine gun, 2026-07-01). When the weapon jams the engine sets `Weapon_Bolt` to the jammed frame through `SetInitState`. An unjam clip plays on top and overrides `Weapon_Bolt` only while it plays, so its frame 0 must equal the jammed frame or the bolt jumps when the gesture starts. Take the real values from an extract of the states clip (`DayZATool --extract-anim w_<weapon>_states.anm 100`) and use them as the bolt marks when authoring; do not judge them by eye. On that weapon: closed 0, jammed −2.2 cm, open −4.3 cm along the bone's X.

### Reload, charge, chamber, jam

- Key small rotations of `Spine`, `Spine1` to `Spine3`, `Neck` and `Head`, both arms and hands, and the `Weapon_` parts that move. The small spine, neck and head motion is what makes it look human.
- The Additive export writes only bones that have keys. Bones without keys are left out.
- Use "visual location/rotation" keying for a bone that a constraint drives.
- "Additive" here is how the clip is authored, not a graph node. Vanilla reloads run on their own `CMD_Reload_` commands with nothing additive about them (`anim-graph.md`, "Reload is not additive").

Names that mislead: `ReloadMagazineDetach` maps to a clip whose file name says `mag_remove`, and that clip does not remove a magazine; it is the hand coming back from the hip (not checked on `P:\`). `FireCocked` is firing while cocked. "Bullet in chamber" is not a state (`anim-graph.md`, "Weapon state names").

### A magazine that follows the hand

There is no magazine bone to key, so fake the tracking in Blender:

1. In edit mode duplicate `LeftHand` (name it for example `LeftHandMagTrack`), parent it to `LeftHand`, and place it where the hand holds the magazine.
2. On `Weapon_Magazine` add Copy Location and Copy Rotation constraints to that tracker.
3. Key the constraints on and off over the reaching frames with "visual location/rotation" keying. Plain location and rotation keys snap when the constraints switch.
4. Bake the action with visual keying and clean curves to remove jitter.

### The "Survivor Reload" export type

The type exists in the plugin's code, but no difference from plain Additive has been seen in game. Treat reloads as Additive until a difference shows.

### Aim space

Not solved by the plugin. Editing the aim space (the grid of look directions that bows and repeaters use) turns the character into a floating lump. Do not author aim space with this tool.

### One pose per weapon class, not per attachment

A common idea is to register a different instance or IK pose for a foregrip by branching in the callback (`if (weapon.withGrip) ...`). That cannot work:

- Every item in hands call takes a class name or is global; none takes a weapon instance or a player: `SetDefaultItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:225`), `ResetItemInHandsProfiles` (`P:\scripts\3_game\dayzplayer.c:229`), `AddItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:240`), `AddItemInHandsProfileIK` (`:243`), `AddItemBoneRemap` (`:252`).
- Registration runs when the player type is set up, in `DayZPlayerTypeRegisterItems` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:334`), which calls the mod callback `RegisterFireArms` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:460`). It is not run per equipped weapon and does not react to attaching or detaching. There is no weapon object in that callback.
- The fallback that does exist is by class hierarchy: register on a base class and override on a subclass. The root is `Inventory_Base` with the apple pose (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:373`). The condition is the class name, not what is attached.
- `ResetItemInHandsProfiles` followed by adding again is global to the player type; it affects every player, not one weapon.

What is left: author one pose that reads well with and without the attachment, which is what vanilla does. Two class names with a swap of the weapon entity in `EEItemAttached` and `EEItemDetached` is possible in principle but fragile, and it multiplies with every attachment.

Since 1.30 script can switch the player's animation instance at run time with `SetAnimationInstanceByName` on `Human` (`P:\scripts\3_game\human.c:1384`), and the player gets `OnItemInHandsChanged` when the item in hands changes (`P:\scripts\3_game\entities\man.c:163`, overridden at `P:\scripts\4_world\entities\dayzplayerimplement.c:997`). That could swap a weapon's profile when a grip is mounted, without swapping classes. It has not been measured for a weapon; the measured uses are surrender (vanilla) and a vehicle rider (`vehicle-rider-ik-pose.md`), and the native's comment warns about desync. Treat it as a lead to test, not as a solved problem.

### Full body action clips on a weapon: what to leave out

Measured in game on a custom submachine gun, June and July 2026.

- **Leave the `Weapon_` bones out unless they are animated with correct values.** A full body action authored in a pipeline that treats the weapon as a rigid object following the hand exports `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet` and `Weapon_Bone_01` to `06` at the export rig's rest, which is garbage, typically collapsed to (0, 0, 0). Measured: `Weapon_Bone_01` to `06` at (0, 0, 0) against (−11.43, 0.79, −2.48) in the vanilla `p_erc_jam_cancel_pm73_ras`, about 11.7 cm off. The engine writes those values onto the bones and the weapon mesh stretches. The fix is to filter them out on the SEAnim side: extract the `.anm` with DayZATool, drop the `Weapon_` bones with `seanim_writer.py`, generate again. The weapon then stays in its base pose, held by the grip. Include `Weapon_` bones only when they carry real values, such as a bolt slide copied from the vanilla equivalent. To detect the problem, extract the clip and compare frame 0 of the `Weapon_Bone_` tracks with the weapon's vanilla clip: several centimetres off means garbage.
- **Spine up only.** Leave `EntityPosition`, `Pelvis` and the leg bones out at the SEAnim level, so the action does not fight locomotion.
- **Never animate `RightHand_Dummy`.** It is the weapon's anchor; animating it makes the grip lose the weapon. The principle is the same as for the `Weapon_` bones: remove what the export got wrong and let the IK pose and the base state place it, instead of trying to repair the value in the export.

### A hold action must carry `LoopStart` and `LoopEnd` notes

Every action the player holds a key for (unjamming is the standard case) needs `LoopStart` and `LoopEnd` notes in its clip. The reason is in the weapon's state machine:

- Unjamming is driven by a timer, not by the clip. `WeaponUnjamming` sets `m_jamTime = 5.0` when it starts (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:218`). `WeaponUnjamming_Start` adds up time in `OnUpdate` and, once `m_dtAccumulator >= m_jamTime`, posts the timeout event (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:27` to `:42`); the next state then calls `SetJammed(false)` (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:87`). If the key is released first, the same `OnUpdate` interrupts and the weapon stays jammed.
- For the timer to run, the weapon command must still be looping: `IsActionFinished()` of `HumanCommandWeapons` (`P:\scripts\3_game\human.c:1032`) has to stay false. The loop notes are what keep the clip looping. The rest is traced in the state machine: without the notes the clip plays once, the action reads as finished, the machine goes back to jammed, and with the key still held it fires again, so the player sees a loop that never unjams.
- Measured in game (2026-08-24): with the notes, the unjam completes at about 5 s. The case without the notes was not run, so "loops forever without them" is traced, not measured.
- Adding `Weapon_CanUnjam_...` or `Weapon_Unjammed` events does not fix a missing loop; the unjam machine does not use them for this.

The structure, copied from a vanilla jam clip (extract `p_erc_jam_<weapon>_ras.anm`): intro from frame 0 to `LoopStart`; the loop between `LoopStart` and `LoopEnd`, which is the struggle and repeats while the key is held; the outro from `LoopEnd` to the end, which holds `Weapon_Unjammed` (the rechamber). `LoopEnd` comes before `Weapon_Unjammed`. The note form that survives DayZATool is `LoopStart||-1` and `LoopEnd||-1`. No authoring again is needed: extract the `.anm`, add the two notes with `seanim_writer.py`, generate (checked: bones kept within 1e-3, notes kept).

When testing, hold the key. A tap plays the cancel clip and the weapon stays jammed; that is vanilla behaviour.

### Helper bones follow a fixed rule in vanilla clips

Measured offline on 8 vanilla clips (DayZ 1.30.164014):

- `ArmExtra`, `ForeArmExtra` and `WristExtra` hold half of their sibling's local rotation (a slerp halfway from identity), the siblings being `ArmRoll`, `ForeArmRoll` and `Hand`: median error 0.2 to 1 degree, at most 4.
- `ElbowExtra` holds about half of the `ForeArm` swing without its twist (median 3 to 7 degrees, up to about 26), and its rest axes differ from the forearm's by 7.32 degrees.
- `ArmRoll` and `ForeArmRoll` are pure twist about the bone's axis (swing at most 0.9 degree).

The parent table is `ofp2-manskeleton-parents.txt`. A clip that leaves the helpers still, or bends the roll bones, gives pinched or peaked elbows and stepped wrists. After authoring, work the helpers out again with that rule (roll bones as pure twist, turned toward the original elbow and wrist so they do not shift) and check the result: helper error within 1 degree (elbow within 7), roll swing within 1 degree, hands unchanged by a stable measure. That check is a design, not a measured gate.

### Splitting a rotation needs the quaternion's sign fixed first

Measured in game (DayZ 1.30.164014). `q` and `−q` are the same rotation, but `2*atan2(x, w)` puts them 360 degrees apart, so halving one leaves the halves 180 degrees apart. In game the forearm twisted like a sweet wrapper with the hand in the right place, because the total was right and the split was not (`ForeArmRoll` at −121 to −146 degrees from its parent against +49 at rest; the hand at −150 to −167). Force `w >= 0` before splitting. A test with the identity does not catch the fault; a test with `−q` fails it by 180 degrees.

### Checking that a pose survived a tool

Compare per component, not by angle. Align the sign first (if the dot product of the two quaternions is negative, negate one), then take the largest difference of any component, with a threshold near 5e-6 (rounding at six decimals). Do not use `2·acos(dot)`: near rest it turns rounding into 0.1 to 0.2 degrees, and on quaternions that are not exactly unit length it reports an angle where the components are equal (0.18 degrees reported for a true difference of 0.00). The same trap in another form: `acos` of the dot of unnormalized float32 quaternions (norms of 0.99999) reported about 0.8 degrees where the real error was about 0.002. Normalize and use `atan2`. An error that is flat across all bones points at the measuring, not at the pose.

### Continuous actions get no arm IK

Measured in game (DayZ 1.30.164014), with the graph read alongside:

- In the player graph the weapon IK node `NormalWeaponIK` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:3860`) comes before the queue `LocomotionQ` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:3602`), and `ActionMaster` enters at that queue (`:3617`). As far as the graph was read, the continuous action state machine carries no weapon IK node of its own, so during a continuous action the arms get no IK.
- Borrowing another object's animation set borrows its geometry: the hand that is not the anchor goes to that object's second grip. The pot holds 28.7 cm between the wrists, and it left the left hand of a 57.5 cm tray 33.5 cm from its grip through the whole pour. Before choosing a borrowed set, compare the wrist spacing of its IK pose with the animation's.

## 6. Exporting `.txa`, and events

### Export

File, Export, "DayZ Animation (.txa)". Set the type:

| Type | Use |
|---|---|
| Full Body | Emotes only. It adds a `Scene_Root` root bone. |
| Survivor IK 1h | One handed grip pose. |
| Survivor IK 2h | Two handed grip pose. |
| Survivor Reload | Rarely; reloads are treated as Additive. |
| Additive | Reload, charge, fire, weapon states. |

Hard rules:

- **IK export:** an IK type, and no bones selected beforehand.
- **Reload, fire, states:** Additive with "Selected Bones Only" and only the relevant bones selected.
- **Exporting every bone on a reload** makes the character "turn into a meatball" in game: the head gone, the body distorted. Full body is for emotes.
- Bones whose names end in `ik_helper` are always skipped.
- The maintained fork turns off every bone constraint before it samples and turns them on again after. Bake any pose that depends on a constraint before exporting.

### Events

In the side panel's "Events" section: Load reads the existing events, which are stored as pose markers named `Type|Args|ID`; add or remove; set frame, type, arguments and id; Save writes them back.

Events carry sound ids (mapped to the `SoundWeapon` classes under `AnimEvents` in the weapon's config) and, more important, the weapon's state changes (bullet chambered, weapon cocked). The state change events are needed even when there are no sound events at all. On export the markers become `$events { #event <frame> "Name" "Args" <ID> }` in the `.txa`.

### The `.txa` format

```
$animation "name" {
  #fps 30
  #numFrames N
  $node "BoneName" {
    $keys t q s {
      $frame start [end] { #t x y z  #q x y z w }
    }
    $node ...nested by hierarchy...
  }
  $events { #event <frame> "EventName" "userStr" <int> }
}
```

Player bones and weapon bones both appear as `$node` entries (from the plugin's samples).

### Two coordinate changes in the plugin: do not merge them

1. **The axis fix.** A matrix that turns +90 degrees about Z, swapping Blender's X and Y. It is not a swap of Y and Z. The importer, the exporter and the object exporter apply it alike.
2. **The component swap in the text.** Translation and scale are written as X Z Y. A quaternion is written as (x, z, y, −w), and reading mirrors that; the export also applies a final negation of all four components.

Treating them as one change, or assuming a plain swap of Y and Z, gives wrong rotations. A round trip outside the plugin needs both. Unit scale: the default factor is 1.0 and the demo uses 1.0; it was not confirmed against vanilla.

### `.txo` (a skeleton or object; usually not needed here)

File, Export, "DayZ Object (.txo)" is for a custom skeleton, such as a creature, with optional mesh and weights. Options: scale factor, selection or visible only, "Auto Create EntityPosition", "Auto Create HeadLook" (head look bone default `pin_lookat`, use `lookat` for vanilla infected; parent default `head`; offset default 0, 0.25, 0). It warns above 4 weights per vertex, the DayZ limit. Workbench registers it as an `.xob`. A player weapon animation reuses the vanilla skeleton, so this step is normally skipped. Creature work: `creature-animation.md`.

## 7. Compiling `.txa` to `.anm` in Workbench

In the Workbench resource browser, right click the `.txa`:

- the first time, "Register resource and import";
- after later edits, "Reimport Resource".

That writes the binary `.anm` next to the `.txa`, and an `.anm.meta` file with a `{GUID}` name and one entry per platform that names the source file. The menu wording dates from tools of 2019 to 2023; check it against the installed tools.

For a `.txo` the mechanism is the same, choosing "As Model"; for a custom skeleton tick "Export Skinning", reimport, and paste the generated entry into the skeleton XML.

### What gets lost without a word

- **Workbench trims consecutive keys that are nearly the same.** The `.anm` can have fewer frames than were authored, and hold poses can collapse. No "keep all frames" option is documented. Author keys with real differences. (Not checked on `P:\`; the plugin's exporter skips nearly equal keys as well.)
- **How much the compile changes, measured** (an unjam clip, DayZ 1.30.164014): the `.anm` Workbench compiles from a plugin `.txa` deviates by up to 0.017 per quaternion component, about 2 degrees, and 0.92 cm, because of the dropped keys (on fast frames of that clip).
- **A route that skips Workbench.** `.txa` to SEAnim to `DayZATool --generate-anim X 100`: quaternion components pass through normalized, translations are multiplied by 100 (m to cm), events become notes of the form `Name|userString|userInt`. The result is exact to float32 and reads back (2.7e-5 on rotation, 3.2e-4 cm). That `.anm` has not been played in game.
- **Scale is ignored when compiling.** It appears in the `.txa` and is dropped from the `.anm`. (Not checked on `P:\`.)
- **A new resource that does not show up:** restart Workbench.
- **Keep the `.txa` next to every `.anm`.** Workbench can only edit an `.anm` again when its `.txa` is present; otherwise a third party extractor is needed just to touch events.
- The Workbench setting "Enable net API" belongs to Bohemia's own Blender tools for another game and is not used by this plugin, which only writes files.

### Two conventions for what a key means

DayZATool extracts vanilla clips relative to the bind pose (`Spine3` with an identity rotation and a translation of (0, 0, 0); most bones without position keys). A clip compiled from the plugin is absolute (`Spine3` at (10.06, −0.67, 0) cm). So the statement "SEAnim rotations are relative to the rest pose" holds for vanilla extracts only. Comparing raw values across the two conventions gives large false differences (a constant 104 degree shoulder offset in one case). Compare in Blender, through `pose_bone.matrix_basis`, or through the bind pose.

### Looking at the player graph (never ship it)

The Workbench animation editor has a history of crashes on the player graph (an access violation on a new group, "Error opening workspace", "no TXA file found" when editing vanilla). Allow time for it. How the event table line has to be handled to open a copy of the workspace differs between 1.29 and 1.30: `anim-graph.md`, "Opening the player graph in the Workbench animation editor". Once open: double click Master Control in Sheets, set the node as running by default, press Play, and use the debug controls to fire the fire, chambering and reload commands.

Never ship a debinarized or edited vanilla workspace, model or clip. It breaks Bohemia's Workshop rules and gets a mod removed.

## 8. Wiring: instance file, script and configs

### The trap to know first

`config.cpp` does not hold the link between a weapon and its player animation. Newcomers look for a config key; the link is entirely in script, the `AddItemInHandsProfileIK` call. The weapon's config only defines the item.

### The instance file

One text file per weapon. In the 1.30 format, as vanilla writes it for the AKM (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:1` to `:9`, starting `AnimSetInstanceSource`):

```
AnimSetInstanceSource {
 Template "{F0C651DE8E24A5DE}DZ/anims/workspaces/player/player_main/player_main.ast"
 ParentTemplates {
  "{416372172B0AFA90}DZ/anims/workspaces/player/player_main/player_main_rifle.asi"
 }
 IkPose "{F7A52CEE6628658F}DZ/anims/anm/player/ik/weapons/izh18.anm"
 Lines {
  AnimSetInstanceSource_Line "WeaponOperations.ErcRas.Chambering_Closed" {
   Resource "{B3DA38AE1EEA3954}DZ/anims/anm/player/reloads/AKM/p_erc_chambering_Closed_AKM_ras.anm"
  }
```

- `Template` names the `.ast`; `ParentTemplates` names the parent instance; `IkPose` the grip pose; each line in `Lines` maps one state to one clip.
- The parent chain for a rifle: the weapon's instance, `player_main_rifle.asi`, `player_main.asi`. For other weapons the middle one is the pistol, two handed, one handed or heavy instance.
- Copy the closest vanilla weapon's instance. Weapons declare different subsets of states: the template lists all legal names and each instance uses some. The AKM's instance has 11 lines per column.
- The demo mod's instance is in the older 1.29 form (`$animsetinstance { #template ... #nparents 1 #parent ... #ikpose ... $animations { "WeaponOperations.ErcRas.Fire" "<path>.anm" ... } }`). For 1.30 write the form above; the port is described in `anim-graph.md`, "Porting a 1.29 `$AnimGraph 7` graph to 1.30".

**Keep the `{GUID}` prefixes.** Stripping the generated `{GUID}` keys from a copied instance, on the idea that DayZ does not need them, is a mistake. Vanilla shows the opposite: every `Template`, parent, `IkPose` and `Resource` value in a vanilla instance carries one (the lines quoted above). Only the hand written demo files omit them. Keep the prefixes on copied vanilla lines and let Workbench generate them for new resources. Measured for a rider pose, not for a weapon: a `Resource` line loaded with a bare path and with an invented `{GUID}` (`vehicle-rider-ik-pose.md`), so a bare path is not known to fail, but nothing is gained by removing what vanilla writes.

### State names

A line's name is `WeaponOperations.<column>.<state>`. The group has two columns, `ErcRas` (erect, weapon raised) and `PneRas` (prone, raised), declared at the end of the group (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1262` to `:1265`). There is no crouch column: crouch uses `ErcRas`, and the graph's stance machine handles the stance. Do not invent `WeaponOperations.CroRas`. Across the 86 vanilla weapon instances of 1.30 there are 701 `ErcRas` lines, 697 `PneRas` lines and none with another column.

The 42 states of the group (`Name "WeaponOperations"` at `P:\DZ\anims\workspaces\player\player_main\player_main.ast:1217`, the list from `:1219` to `:1260`):

`ChamberingBulletL`, `ChamberingBulletR`, `ChamberingCancel`, `ChamberingFast_Closed`, `ChamberingFast_Open`, `ChamberingIn`, `ChamberingLook`, `ChamberingLoop`, `ChamberingLoop1`, `ChamberingLoop_Closed_Bullet`, `ChamberingLoop_Closed_NoBullet`, `ChamberingLoop_Open_Bullet`, `ChamberingLoop_Open_NoBullet`, `ChamberingOut`, `Chambering_Closed`, `Chambering_Closed_Uncocked`, `Chambering_NoBulletL`, `Chambering_NoBulletR`, `Chambering_Open`, `Fire`, `FireCocked`, `FireEmptyAutomatic`, `FireJam`, `FireLast`, `FireUncocked`, `Jamming`, `Jamming Cancel`, `Jamming Check`, `Obstruction`, `ReloadAction_Closed`, `ReloadAction_Closed_Uncocked`, `ReloadAction_Open`, `ReloadBoltAction2`, `ReloadClipInBullet`, `ReloadClipInNoBullet`, `ReloadClipOut`, `ReloadClipPose`, `ReloadMagBullet`, `ReloadMagNoBullet`, `ReloadMagazineDetach`, `ReloadNoMagBullet`, `ReloadNoMagNoBullet`.

Names are exact, dotted and case sensitive. `Jamming Cancel` and `Jamming Check` contain a real space. A mistyped or missing name falls back to the parent's clip with no error, or breaks that operation. There is no mode switch state in the group.

### The template

`player_main.ast` is the schema: it says which state names an instance may fill. Its grammar is not documented; copy from the vanilla file. The 1.30 form is in `anim-graph.md`, "Template files (`.ast`): every group is named".

### Script registration (required)

In the mod's `4_World` scripts:

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterFireArms(pType, pBehavior);
        pType.AddItemInHandsProfileIK("MyMod_SVD_Base", "MyMod/Animations/SVD/MyMod_SVD.asi", pBehavior, "MyMod/Animations/SVD/MyMod_SVD_IK.anm", "MyMod/Animations/SVD/w_MyMod_SVD_states.anm");
    }

    override void CustomBoneRemapping(DayZPlayerType pType)
    {
        super.CustomBoneRemapping(pType);
        array<string> remap = { "bolt", "Weapon_Bolt", "magazine", "Weapon_Magazine", "trigger", "Weapon_Trigger", "charging", "Weapon_Bone_01", "bullet", "Weapon_Bullet", "mag_release", "Weapon_Bone_02", "boltrelease", "Weapon_Bone_03" };
        pType.AddItemBoneRemap("MyMod_SVD_Base", remap);
    }
}
```

- `ModItemRegisterCallbacks` is the vanilla class for this (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:305`), with `RegisterFireArms` at `:321` and `CustomBoneRemapping` at `:331`; vanilla calls the latter after its own remaps (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1646`).
- `AddItemInHandsProfileIK(string pItemClass, string pAnimInstanceName, HumanItemBehaviorCfg pBehaviorCfg, string pIkPoseAnim, string pWeaponStates = "")` (`P:\scripts\3_game\dayzplayer.c:243`). The fifth argument is for weapons; other items use four with a generic instance.
- `AddItemBoneRemap(string pItemClass, array<string> pBoneRemap)` (`P:\scripts\3_game\dayzplayer.c:252`). The pairs are, in the source's own words just above it, "bone in item's P3D first, bone in Character skeleton second".
- Register on the weapon's base class so every variant inherits and the number of calls stays low.

**The remap is why parts move.** The first name of each pair is a selection of the weapon model, declared as a bone in the weapon's own `model.cfg`; the second is a `Weapon_` bone of the player. The standard parts go to `Weapon_Bolt`, `Weapon_Magazine`, `Weapon_Trigger` and `Weapon_Bullet`; other parts take `Weapon_Bone_01` to `06`. Leaving the remap out is why bolt, magazine and trigger do not move while the hands do. A wrong name drops that part's motion with no error. A weapon that inherits a vanilla base class gets that class's remap (`Rifle_Base` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1580`).

Limit (not checked on `P:\`): `AddItemBoneRemap` works for weapon classes only. A medical item or any other non weapon cannot drive a `Weapon_Bone`; its only anchors are `RightHand_Dummy` and, through constraints, `LeftHand_Dummy`.

An older way to register: call `GetDayZPlayerType().AddItemInHandsProfileIK(...)` inside a modded `PlayerBase.Init()`, guarded so it runs on the client. The callback above is the cleaner way.

### How the engine picks column and state

The graph does this, not the mod:

- The column: the group selection nodes `WeaponStanceErc` (`Group "WeaponOperations"`, `Column "ErcRas"`, `P:\DZ\anims\workspaces\player\player_main\combat.agf:1150` to `:1155`) and `WeaponStancePne` (`Column "PneRas"`, `P:\DZ\anims\workspaces\player\player_main\combat.agf:1178` to `:1183`) both play `WeaponFireSTM`; the prone one starts on `Stance == 2` (`:1172`).
- The fire state: `FireCocked` starts on `GetCommandI(CMD_WeaponFire) == 2` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:1120` to `:1123`).
- The commands, declared in the master graph: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Exit`, `CMD_Reload_Clip` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:269` to `:284`), `CMD_Weapon_Jam` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:359`) and `CMD_WeaponFire` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:365`).

Which command or transition starts each single state (`ReloadAction_Closed` against `_Open` against `ReloadMagBullet`) is in the weapons sub-graph and was not traced state by state. Copy the wiring of the closest vanilla weapon.

### The weapon's own `model.cfg`

Two skeletons are in play; keep them apart. The weapon has its own small skeleton, the selections the remap's first names point at. The player has the player skeleton. The `.anm` animates player bones, and `AddItemBoneRemap` is the bridge.

```cpp
class CfgSkeletons
{
    class svd
    {
        skeletonInherit = "";
        isDiscrete = 1;
        SkeletonBones[] = { "magazine", "", "trigger", "", "bolt", "", "firemode", "", "bullet", "", "mag_release", "" };
    };
};
class CfgModels
{
    class Default;
    class svd: Default
    {
        skeletonName = "svd";
        sections[] = { "magazine", "zbytek", "bullet" };
    };
};
```

(The shape of the demo mod's SVD file; the `sections[]` list is shortened.) `gen_model_cfg.py` writes this kind of file.

The plugin's Tools, "Generate DayZ Model Config (model.cfg)" writes a `CfgSkeletons` and `CfgModels` stub from the selected armature, with `isDiscrete = 0`, bone and parent per bone, and a model class to rename. It skips the helper bones (`scene_root`, `entityposition`, the hand origins, the hand dummies and the forearm directions, in any case). It is meant for custom skeletons such as creatures. Note that the bones it skips still appear as animated nodes in a `.txa`: skipped in `CfgSkeletons` does not mean not animated.

### The weapon's `config.cpp`

The weapon class carries `model`, `magazines[]`, `chamberableFrom[]`, `modes[]`, the `AnimEvents` sounds and `OpticsInfo`, and no reference to an `.anm` or `.asi`. The vanilla SVD: config class `SVD_Base: Rifle_Base` (`P:\DZ\weapons\firearms\svd\config.cpp:26`), script class `SVD_Base : RifleBoltLock_Base` (`P:\scripts\4_world\entities\firearms\rifle\svd.c:1`).

### The `reloadAction` key is legacy

`reloadAction` is an old `CfgWeapons` key from the Arma line that named a reload action in the old gesture configs. It does not drive reloads here: the instance file binds clips by state name, whatever `reloadAction` says.

- Vanilla rifles do not set it. Neither `P:\DZ\weapons\firearms\ak74\config.cpp` nor `P:\DZ\weapons\firearms\svd\config.cpp` contains `reloadAction` or `shotAction`.
- It survives in two vanilla configs: `reloadAction="ReloadBow"` (`P:\DZ\data\config.cpp:4592`) and `reloadAction="ManActReloadAT"` (`P:\DZ\data\config.cpp:4756`).
- No weapon script reads it. The only hit for the word under `P:\scripts` is in the key bindings menu.
- The demo mod's SVD sets `reloadAction="ReloadSVD"`, a name that matches no vanilla class, and animates correctly through its instance file.
- `reloadAction`, `shotAction` and related keys were removed as obsolete around 1.25 to 1.26; the exact version is not confirmed.

Leave it out, as vanilla rifles do. Not checked: whether an invalid value logs more than a harmless warning.

### Mod layout

The demo mod uses one top folder per PBO:

```
<Mod>/
  Animations/   .asi, and .txa, .anm, .anm.meta per weapon; config.cpp with CfgPatches <Mod>_Animations
  Firearms/     weapon .p3d, its model config, textures; config.cpp with CfgPatches <Mod>_Firearms
  Scripts/      config.cpp with CfgPatches <Mod>_Scripts and CfgMods; the .c files
  Workbench/    the Workbench project files
```

In this repository a mod lives under `workspace\<ModName>\` and `/dayz-new-mod` or `/dayz-add-scaffold` create the layout, prefix file included.

`requiredAddons[]` per PBO:

- Animations: `DZ_Anims_Anm_Player` (`P:\DZ\anims\anm\player\config.cpp:3`), `DZ_Anims_Cfg` (`P:\DZ\anims\cfg\config.cpp:3`), `DZ_Data`, `DZ_Scripts`, so that the vanilla clips and configs load first.
- Firearms: `DZ_Weapons_Firearms`, plus magazines, muzzles, optics or launchers as used.
- Scripts: `DZ_Scripts`. The scripts config also holds `CfgMods` with a `worldScriptModule` pointing at the `4_World` folder.

`inputs.xml` is optional: the demo ships an empty one, because reload, fire and chamber reuse vanilla inputs. Only a new bindable action (an "inspect", say) would need one; that path is not tested. `stringtable.csv` is optional too, for localized names.

The Workbench project file (`dayz.gproj`) declares the work drive as its file system, the skeleton definitions file, image sets and widget styles, and the five script modules. Build and launch from Workbench so that `.txa` files compile.

## 9. Build, sign, deploy, test

Use `/dayz-build-pbo` to pack and `/dayz-launch-test` to run; `/dayz-logwatch` reads the logs. What matters for an animation mod in particular:

- **Pack only against binarize.** Pack only for scripts, layouts, `.anm`, `.paa` and sounds; binarize when configs, models or textures need converting. Binarizing an addon of scripts and clips is unnecessary, and packing a model or config addon without binarizing leaves it unconverted. Match the choice to what the addon holds.
- **Signing** (optional for a local test): create a key pair with DayZ Tools' `DSCreateKey`, sign through Addon Builder or `DSSignFile`, check with `DSCheckSignatures`. Use lower case `addons` and `keys` folder and file names so a Linux server finds them. The exact arguments were not run.
- **Addon Builder by hand**, when the skill is not used: the source folder, the destination folder, the prefix (`-prefix=`), the project folder `-project=P:\` so paths across addons resolve, then `-binarize` or `-packonly`, with `-clear`, `-sign=<key.biprivatekey>` and `-include=<list>` as needed. An addon packed by hand needs its prefix file at its root; the demo's source tree has none, because Workbench's build takes the prefix from the folder name.
- **Deploy** to `P:\Mods\@<ModName>\Addons\` (what `/dayz-build-pbo` does), with the public `.bikey` in the mod's `keys` folder when signatures are checked.
- **A local test server** has `allowFilePatching=1`, `verifySignatures=0` and BattlEye off.

### Does file patching reload an `.anm`?

Probably not: loose scripts and layouts reload, `.anm` changes do not, and the PBO must be packed again every time, or edits appear to do nothing. That is plausible and not confirmed: an `.anm` is a compiled binary resource reached through the instance file when the profile is registered, not a text file the loose loader reads. The named file systems of 1.30 (`-resolveFilePatchingUsingEnfusion=1`) may be a way for Workbench to load loose workspace resources without packing; that was not tested either. Until the test is run (edit a loose `.anm`, start the diagnostic client with file patching, see whether the weapon changes without a repack), pack again after every clip change.

The loop: edit in Blender, export `.txa`, "Reimport Resource" in Workbench, pack the PBO, reconnect, trigger the weapon state.

### What to test in game

Spawn the weapon, a magazine and ammunition. Chamber a round (no parts should move while chambering). Attach an optic and a suppressor (they stay in place). Look down the sights (the iron sights are level). Reload (the magazine follows the hand). Fire (the bolt cycles). Then the elbow tests.

### The elbow: only the game can judge it

The pole angle of the Blender IK constraint on the hands is a preview value. It is not exported; only the resulting pose is. Whether the elbow is right can only be confirmed in game. The position of the forearm direction bone decides how far the elbow sticks out. Tune the pole angle and that position, export, reimport, pack, test again. The elbow's error depends on the angle of view: fine head on, collapsed into the ribcage otherwise. Three tests show it:

1. lean left and look down (the left elbow must stay out of the ribcage);
2. crouch;
3. throw (tap G).

The plugin's IK is reverse engineered and about 90 to 95 percent accurate against the engine. Expect iterations.

## 10. Walls and failure catalogue

### Walls

| Wall | Detail |
|---|---|
| Bone names are exact | A mismatch logs `Bone X doesn't exist in skeleton OFP2_ManSkeleton` and the bone is dead. The skeleton cannot be restructured. |
| One graph replacement at a time | Two mods that replace the player or a creature graph cannot load together. This does not apply to the instance file route. |
| No open `.anm` writer | Only Workbench and DayZATool write `.anm`. An agent can produce `.txa` or SEAnim. |
| No bone remap for non weapons | `AddItemBoneRemap` works for weapons only (not checked on `P:\`). |
| Two weapons at once | Only one weapon is assigned to the player; other clips fight it. |
| Aim space | Not solved by the plugin. |

### Looks done, is not

- Exporting all bones: the "meatball". Selected bones only, except for emotes.
- Weapon states not ending on frame 2: only two frames; open and jammed break.
- Workbench trimming near equal keys: hold poses collapse.
- Scale dropped when compiling: never animate with bone scale.
- The pole angle is not exported: the Blender preview misleads; check the elbow in game.
- Turning `LeftHand` or the IK helpers to fix wrist orientation does nothing in game: fix the grip through geometry.
- A mistyped state name falls back to the parent's clip with no error. Mind the space in `Jamming Cancel`.
- No `AddItemBoneRemap`: the hands play, bolt, magazine and trigger are dead.
- A lost `.txa`: the `.anm` cannot be edited again.
- A hold action without loop notes (above).

### Tool traps

- The README's Blender version is stale for the maintained fork.
- A rig extracted with DayZATool is unreliable for empties and has inverted local bone axes. Author with the plugin; extract only for reference.
- Do not take an FBX out of DayZATool back into Workbench as `.xob`, `.anm` or `.txa`. It breaks.
- Do not strip `{GUID}` prefixes (section 8).
- Do not ship edited vanilla files.
- The animation editor crashes; allow time.
- Magazine tracking needs visual keying and a bake, or it snaps.
- Do not confuse the weapon's skeleton with the player's.
- Do not confuse `.rtm` with `.txa` and `.anm`.

### Registration at run time

- Many `AddItemInHandsProfileIK` overrides stacked across mods are reported to overflow the stack in `ModItemRegisterCallbacks` on heavily modded servers (not confirmed). Register on base classes to keep the number of calls low.
- Registration must run in the right place. The older `PlayerBase.Init` pattern needs its client guard; in the wrong place it does nothing, with no error.

### What shipped mods still show

Shipped weapon animation mods still show: prone clips reusing standing or crouched poses, so the gun clips into the ground; a left hand glitch on one shotgun when empty; a finger bending wrongly at the end of a chambering clip. Budget for imperfections of that kind.

### RPT and symptom catalogue

Rows 1 to 4 and 8 are confirmed; rows 5 to 7 are not checked.

| # | RPT line or symptom | Cause | Fix |
|---|---|---|---|
| 1 | `Error: Bone <name> doesn't exist in skeleton OFP2_ManSkeleton`, once per bone; that bone does not move, the rest plays | The clip, the model config or a selection names a bone the skeleton lacks: a typo, wrong case, a bone from another game, or a remapped weapon bone never tied to a character bone | Match the skeleton's list exactly; remove or rename foreign bones. |
| 2 | `ANIMATION (E): Can't load <Mod>/Anims/cfg/skeletons.anim.xml`, then `ANIMATION (E): Failed to open file, line 0, column 0` | A skeleton or animation config path that is not packed, a wrong prefix, or a case mismatch. The same shape for a missing `.anm` named by an instance line | Check the exact path is packed and its case is right. (Quoted from a real server RPT.) |
| 3 | Blender export fails with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'` | The original plugin on Blender 4.1 or later | Blender 3.6.8 to 4.0 for the original plugin; the maintained fork needs 4.4 or later. |
| 4 | Two animation mods crash the game, or one silently wins | Both replace the player graph | Merge the graph mods into one. Instance file weapon mods are not affected. |
| 5 | Limbs snap to a default, a T pose, or part of the body freezes during the clip | Not every bone of the skeleton has a key; bones without one fall back to a default transform | Key every bone the clip owns. |
| 6 | Arms and weapon badly wrong after a two handed clip where a one handed one is expected | Wrong handedness | Put the clip in the instance of the right kind (one handed, two handed, rifle, pistol). |
| 7 | Right in Blender, bones twist or roll wrong in game | Blender's bones run along +Y, DayZ's along +X | Go through the official rig and exporter, or the per rig maps in `weapon-anim-authoring-viewer.md`; check in game. |
| 8 | An extracted rig is "always incorrect" | Extraction with DayZATool or another extractor is a reference, not a clean round trip | Use it as a starting point only. |

Two failures have no known RPT text, to be captured during an in-game test: the exact wording when an instance line names a clip that does not exist, and whatever is logged for a weapon whose bolt is dead or an IK pose imported without the IK bones.

## 11. Checklist

**Setup**

- [ ] Blender matches the plugin fork (maintained: 4.4 or later; original: 3.6.8), checked against the importer's calls.
- [ ] `DayzAnimationTools` copied into the addons folder and enabled.
- [ ] `/dayz-preflight` passes: `P:\` mounted, vanilla data unpacked.
- [ ] The Workbench project opens.

**Author**

- [ ] The master rig is open (or an IK sample scene for grip work).
- [ ] For an IK pose: "Add Survivor IK Bones" was run before importing or authoring.
- [ ] The closest vanilla base pose or clip is imported; the weapon FBX parts are attached (optional).
- [ ] IK pose: only `LeftHandOrigin`, `RightHandOrigin` and the two forearm direction bones are keyed.
- [ ] Fire: about 7 frames, trigger pulled on frame 0, bolt cycle, eject event.
- [ ] Weapon states: three frames (closed, open, jammed), end frame 2, weapon bones only.
- [ ] Reload, charge, chamber, jam: shoulders down, keyed bones only, small spine motion.
- [ ] A hold action (unjam or any continuous one) has `LoopStart` and `LoopEnd` notes.
- [ ] No keys on IK helpers in clips that are not IK poses; no scale keys anywhere.
- [ ] Helper bones recomputed with the vanilla rule and checked.
- [ ] Events set in the Event Manager; the state change events are there.

**Export and compile**

- [ ] `.txa` exported with the right type (an IK type for the grip; Additive with selected bones for the rest), 30 frames per second.
- [ ] Workbench: register or reimport; `.anm` and `.anm.meta` exist (restart Workbench if a new resource does not appear).
- [ ] The `.txa` is kept next to every `.anm`.

**Wire**

- [ ] The weapon's instance: `Template` is `player_main.ast`, the parent is the rifle (or matching) instance, `IkPose` set, lines for `ErcRas` and `PneRas`, `{GUID}` prefixes kept.
- [ ] State names exact (mind `Jamming Cancel`).
- [ ] `RegisterFireArms` calls `AddItemInHandsProfileIK` for the base class.
- [ ] `CustomBoneRemapping` calls `AddItemBoneRemap` for the base class.
- [ ] The weapon's `model.cfg` bones match the remap's first names.
- [ ] `CfgMods` has the world script module; each PBO's `requiredAddons[]` is set.

**Build and test**

- [ ] PBO packed (pack only for scripts and clips; binarize for models and configs).
- [ ] Deployed; the test server allows file patching and does not verify signatures.
- [ ] In game: chamber, attach optic, sights, reload, fire all correct.
- [ ] Elbow tests pass: lean left and look down, crouch, throw.
- [ ] After each clip change: reimport and pack again before testing.

**Compatibility**

- [ ] Only per weapon clips through `AddItemInHandsProfileIK`: no conflict with other mods.
- [ ] Any change to the player graph: exclusive with every other graph mod; the user knows.

## 12. Frame budget of the vanilla AKM clips

Each clip was extracted to SEAnim with DayZATool 1.3 and read with `seanim_writer.py`. All run at 30 frames per second (also read from the `FPS` chunk of `w_akm_states.anm`); the frame count is the last key index plus one. Use them as the timing reference for a custom rifle. The clips are in `P:\DZ\anims\anm\player\reloads\AKM\` and `P:\DZ\anims\anm\player\ik\weapons\`; the numbers cannot be checked on `P:\` without extracting.

| Clip | Frames | Duration | Bones | Purpose |
|---|---|---|---|---|
| `p_erc_reload_mag_remove_akm_ras` | 22 | 0.700 s | 69 | Magazine detach, the removal part |
| `p_erc_reload_mag_nobullet_akm_ras` | 55 | 1.800 s | 69 | Full magazine swap, no chambering |
| `p_erc_reloadaction_closed_akm_ras` | 44 | 1.433 s | 73 | Charging handle pull, closed bolt |
| `p_erc_chambering_closed_akm_ras` | 107 | 3.533 s | 73 | Chamber a loose round, closed bolt |
| `p_erc_fire_akm_ras` | 11 | 0.333 s | 45 | One fire cycle |
| `p_erc_jam_akm_ras` | 230 | 7.633 s | 73 | Clearing a jam |
| `w_akm_states` | 2 | 0.033 s | 10 (weapon bones) | Bolt and bullet states |
| `ik\weapons\akm` (IK pose) | 2 | 0.033 s | 43 | Grip pose |

For the other kinds of clip the demo mod ships only `.anm` files, so frame ranges beyond its fire (7) and states (3) samples come from these extracts, not from authoring sources.

## 13. Open questions

These are not confirmed. Do not state them as facts.

1. The full ordered bone list of the master rig against the game's skeleton: it was inferred from sample `.txa` files and plugin code, not from opening the rig. `player-skeleton.md` is the checked list.
2. Whether the maintained fork really fails on Blender 3.6.8 (inferred from its calls).
3. The grammar of instance and template files is taken from the demo and vanilla files, with no Bohemia document behind it, so more legal lines than those listed may exist in other groups.
4. The player clip frame rate is not declared in any workspace text file; 30 is read from the clips. Whether a mismatched export rate causes speed problems was not tested.
5. The state of Bohemia's feedback tickets on an official IK and instance interface, on animation editor bugs and on the register callback stack overflow.
6. Which command or transition starts each single `WeaponOperations` state.
7. Workbench's key trimming rests on the measured compile loss above; no option to turn it off is known.
8. Scale being ignored when compiling: not checked (the plugin's default of not exporting scale keys agrees).
9. Action clips playing on top of the states clip: not checked, consistent with the demo.
10. Whether an invalid `reloadAction` logs more than a warning.
11. "Since 0.63 all weapon animation is on the character's side, not in `model.cfg`": not checked.
12. The difference between the Survivor Reload and Additive export types in game.
13. That `ReloadMagazineDetach`'s clip is the hand coming back from the hip: not checked.
14. Swapping a weapon's profile at run time when an attachment changes (above).
15. What `Weapon_Bone_01` to `06` mean per weapon family beyond the vanilla remaps.
16. Whether a weapon only animation ever needs its own `inputs.xml` action.
17. The unit factor for translations between Blender and DayZ (1.0 assumed).
18. Whether file patching reloads an `.anm` (section 9).
19. The live wording of Workbench's menu entries per tools version.
20. Performance: no measurement exists of what custom weapon clips or many registrations cost.
21. The exact arguments of the signing tools.
