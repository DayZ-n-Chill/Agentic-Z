# Weapon animation from Blender

What a custom player weapon animation is, which route and tools it uses, how to set up Blender and the plugin, the rig and its IK helpers, and how to start from a vanilla pose. The rest of the route is split by step:

| Step | File |
|---|---|
| Authoring each kind of clip: IK pose, fire, weapon states, reload, hold actions, helper bones | `weapon-anim-authoring.md` |
| Exporting `.txa`, events, the plugin's coordinate changes, compiling in Workbench | `weapon-anim-compile.md` |
| The instance file, state names, script registration, the weapon's `model.cfg` and `config.cpp`, mod layout | `weapon-anim-wiring.md` |
| Build, test, the elbow, failure catalogue, checklist, AKM frame budget, open questions | `weapon-anim-testing.md` |

How the weapon sits in the hands, and why a bad grip is fixed in geometry, is in `weapon-in-hands.md`. Facts about the DayZ animation plugin for Blender (`DayzAnimationTools`, in its original build and its maintained fork) and its demo mod cannot be checked on `P:\` and are marked where they matter.

Five common mistakes these files correct: stripping the `{GUID}` prefixes from instance files; assuming a weapon states clip is always 3 frames; looking for the `ikpose_` keys in the template or a config; expecting `reloadAction` to drive the reload; and picking a pose per attachment inside the register callback.

## What it is

A custom player weapon animation is not wired through `config.cpp` animation keys, and it does not edit the player graph. It reaches the player in three layers:

1. Authoring: key the player rig in Blender and export `.txa` (text) with the plugin; Workbench compiles it to `.anm` (binary).
2. Mapping: a text instance file (`.asi`) for the weapon maps state names of the form `WeaponOperations.<column>.<state>` to `.anm` files and inherits the rest from a parent chain: the weapon's instance, then `player_main_rifle.asi`, then `player_main.asi`.
3. Binding: `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` (`P:\scripts\3_game\dayzplayer.c:243`) binds the weapon class to the instance, an IK pose and a weapon states clip, and `AddItemBoneRemap(itemClass, pairs)` (`:252`) maps the weapon model's part selections to the player skeleton's `Weapon_` bones. Vanilla binds every weapon this way, for example `AKM_Base` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`).

Because no graph is replaced, several weapon animation mods load together. The one graph replacement at a time wall is about mods that replace the player graph (`anim-graphs.md`, "Which changes collide"); one vehicle class's rider pose binds through a child instance as well (`rider-pose-measured.md`).

Each weapon has three kinds of clip:

| Clip | What it is | Named in |
|---|---|---|
| IK pose | One pose: where hands and fingers sit on the gun. | The `.asi` `IkPose` line and the fourth argument of `AddItemInHandsProfileIK`, which can name different poses (the AKM's do). |
| Weapon states (`w_<weapon>_states.anm`) | Only the `Weapon_` bones, one frame per start state (bolt closed, open, jammed). | The fifth argument; `SetInitState` reads it. |
| Action clips (reload, fire, chamber, jam) | Differences, roughly shoulders down, over the idle. | The `.asi` `Lines`. |

Action clips play on top of the states clip and override those bones while they play. That is not checked on `P:\`, but fits the comment on `SetInitState`, which says each frame of the states animation is one init state (`P:\scripts\3_game\human.c:1108` to `:1112`).

## Two routes

| | The `.txa` route | The SEAnim route |
|---|---|---|
| Authoring file | `.txa` from the plugin in Blender | SEAnim, an open format |
| To `.anm` | Workbench "Register resource and import", later "Reimport Resource" | `DayZATool --generate-anim file.seanim` |
| Tooling | The maintained plugin fork | A closed .NET program needing .NET Framework 4.5 |
| Rig | The master rig with IK helpers | Extracted rigs come out wrong for empties, which the IK helpers are, with inverted local bone axes (not checked on `P:\`) |
| Use for | Player weapon animation | Extracting reference meshes and clips |

Use the `.txa` route; the plugin's demo mod does. The SEAnim route is the fallback when it is blocked: same instance file and packing, but its extracted rig is a reference, not a clean round trip. Never use `.rtm` for a player weapon animation; it is the most common wrong turn (`rtm-and-character-animation.md`).

## Blender and the plugin

The plugin's README asks for Blender 3.6.8, which is right for the original plugin only. The maintained fork's `.txa` importer calls `action.fcurve_ensure_for_datablock(...)`, the slotted actions interface of Blender 4.4 and later, and has a helper named for Blender 5.1; its `bl_info` declares `'blender': (2, 80, 0)`, which means nothing. So the fork needs Blender 4.4 or later, 5.x included (that it fails on 3.6.8 is inferred, not run), and the original needs 3.6.8 to 4.0 (on 4.1 and later it fails with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`). Check the import code against the Blender in use. Files saved in Blender 5.x do not open in 4.2, and the plugin's sample `.blend` files were saved in 3.6.8.

The download is a plain folder, not a zip, so "Install from file" does not work. Copy `DayzAnimationTools` to `%AppData%\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`, then in Edit, Preferences, Add-ons search "DayZ" and tick "Dayz Animation Tools". Its tools: a "DayZ Animation Tools" menu in the 3D view header (Import, Export, Tools); File, Import and Export entries "DayZ Animation (.txa)" and "DayZ Object (.txo)"; and the Event Manager in the 3D view's side panel (N), tab "Dayz Animation Tools", section "Events".

The work drive is `P:\` with the vanilla data in `P:\DZ\` and `P:\scripts\`; `/dayz-preflight` checks it and `/dayz-workdrive` mounts it. The demo mod's `SetupWorkdrive.bat` makes a junction on `P:\` for any folder holding a `Workbench\dayz.gproj`. With Workbench as the default program for its files, F6 launches and F10 kills from its resource browser.

The vanilla files to read:

- the player workspace, `P:\DZ\anims\workspaces\player\player_main\` (`.asi`, `.ast`, `.aw`, `.agr`, `.agf`);
- compiled clips under `P:\DZ\anims\anm\player\`: IK poses in `ik\weapons\`, reloads and states in `reloads\<weapon>\` (for the AKM, `w_akm_states.anm` and 22 action clips);
- the bone list `P:\DZ\anims\cfg\skeletons.anim.xml`, which the Workbench project names as its skeleton definitions.

DayZATool: `--extract-anim` (`.anm` to SEAnim), `--extract-model` (`.xob` to SEModel), `--generate-anim file.seanim` (SEAnim to `.anm`). It takes a scale as second argument (100) and no output path, writing next to the input; expect to tune the scale. Blender importers: `io_scene_seanim`, `io_model_semodel`.

## The rig

The plugin's sample assets include `JD_Master_Rig (No IK Bones).blend`: the player skeleton with vanilla bone names and custom shapes on the bones grabbed most (hand, forearm, knee, foot). Names must match exactly, case included, or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and the bone does not move; the skeleton cannot be restructured (`tooling-and-walls.md`, "The walls"). The checked list by zone is `player-skeleton.md`; in short:

| Group | Bones |
|---|---|
| Root | `Scene_Root`, `EntityPosition`, `Collision` |
| Spine and head | `Pelvis`, `Spine` to `Spine3`, `Neck`, `Neck1`, `Head` |
| Arms | `LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand` and the right ones |
| Fingers | Five chains a hand, plus roll and extra helpers |
| Legs | `LeftUpLeg`, `LeftUpLegRoll`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase` and the right ones |
| Hand anchors | `RightHand_Dummy`, `LeftHand_Dummy` (`P:\DZ\anims\cfg\skeletons.anim.xml:115`, `:116`) |
| Weapon | `Weapon_Root`, `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`, `Weapon_Bone_01` to `Weapon_Bone_06` (`:254` to `:264`) |

- An item in the right hand is a child of `RightHand_Dummy`. Current clips move the gun with `RightHand_Dummy`, not the older `Weapon_Root` (plugin code, not checked on `P:\`).
- The weapon's parts move through `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet` and six free slots for anything else; what a slot means is per weapon, and vanilla rifles map `charging` to `Weapon_Bone_01` (`dayzplayercfgbase.c:1579`).
- Do not use the older bones in the group marked for removal (`player-skeleton.md`, "Bones marked for removal"). There are no magazine bones; the engine follows the magazine through `LeftHand_Dummy`.

Tools, "Add Survivor IK Bones", with the armature selected, creates `LeftHandOrigin` (parent `RightHand_Dummy`), `RightHandOrigin` (parent `RightShoulder`), `RightForeArmDirection` and `LeftForeArmDirection` (parents the shoulders), and adds IK constraints on `LeftHand` and `RightHand` with chain length 5, the forearm direction bones as pole targets and pole angles of -127.9 degrees (left) and +45.3 degrees (right). The game's skeleton has these helpers (`skeletons.anim.xml:149` to `:157`); the rig without IK bones does not.

- Run it before importing or authoring any IK pose. An IK `.txa` imported onto a rig without them prints "Ignoring survivor IK bone ... because Tools > Add Survivor IK Bones is required first!" and drops those tracks.
- Never key, or even add, these helpers for clips that are not IK poses. Stray keys corrupt full body and difference exports; the exporter and the model config generator skip them.
- The plugin exports `LeftHandIKTarget` as a copy of `LeftHandOrigin`; it is not keyed in Blender.

Which helper plays which IK role is set in the graph's weapon IK node (`AnimSrcNodeWeaponIk`), in a block of `ikpose_` keys (`P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35`):

```text
ikpose_chainoffset        = RightHandOrigin
ikpose_weaponoffset       = RightHand_Dummy
ikpose_secchainoffset     = LeftHandIKTarget
ikpose_chainmiddledir     = RightForeArmDirection
ikpose_chainmiddlediro    = RightHandOrigin,RightForeArmDirectionOrigin
ikpose_secchainmiddledir  = LeftForeArmDirection
ikpose_secchainmiddlediro = LeftHandOrigin,LeftForeArmDirectionOrigin
```

Above it the same node holds the basic setup (`hand = RightHand`, `weapon = RightHand_Dummy`, `weaponrotator = RightArm`, the two chains and their axes, `combat.agf:19` to `:27`) and a comment on the hierarchy: the root is the right hand, which is not exported; `RightHand_Dummy` is where the weapon is; `LeftHandIKTarget` is where the left hand is on the weapon; `RightHandOrigin` is the inverse transform of where the hand originally was. The block occurs 14 times in the 1.30 player sub-graphs (`actions.agf` 7, `combat.agf` 2, `gestures.agf` 1, `locomotion.agf` 2, `master.agf` 1, `vehicles.agf` 1) and nowhere in `player_main.ast`, the workspace, `config.cpp` or `model.cfg`. Never leave out the two keys ending in `diro`.

## Starting from a vanilla pose

Import a `.txa`: select the armature first (or the importer stops with "Select an armature first!"), then File, Import, "DayZ Animation (.txa)" with Scale Factor 1.0, Translation and Rotation Keys on, Scale Keys off (DayZ ignores scale). The importer sets every bone to quaternion rotation, takes frame rate and range from the file, turns IK constraints off during import and on after, and keeps the action with a fake user; several files import as separate actions, earlier ones pushed to NLA strips.

To import from a script without the window, with the plugin folder at `<plugin>`:

1. Add `<plugin>` to `sys.path`, `import DayzAnimationTools`, call `DayzAnimationTools.register()`, then with the armature active call `bpy.ops.import_scene.txa(filepath=..., files=[{"name": basename}])`.
2. The importer uses `SURVIVOR_IK_ANIM_BONES`, which the plugin never defines (it has a left and a right list), so it raises `NameError`. Before importing, import the `Import.ImportTxa` module and set `SURVIVOR_IK_ANIM_BONES` to the left list plus the right list from `Types.Txa`.
3. For the pure forward kinematics pose the `.anm` holds, turn pose bone constraints off after import (the plugin turns them back on), set frame 0 and read `armature.matrix_world @ pose_bone.matrix`.
4. Keep both rotation and translation: arm bone translation is about the rest offset, but the root's (`Pelvis`) is real; the soft aim pose crouches about 3.5 cm.

Copy the closest vanilla clip. For a grip, start from the plugin's sample idle nearest the target, such as `Rifle_Erect_Idle_Ras (Soft_Aim).txa` (soft aim is where a reload starts), or the pistol one; for reload and fire take timing from the nearest vanilla action. The samples cover rifle, pistol, one handed, two handed, heavy, ladder, spear, unarmed and surrender, each with erect, crouched and prone idles lowered and raised, plus IK scenes for an M4, a pistol, a shovel, a sea chest and an apple.

To see the weapon while posing: in Object Builder put each moving part (body, bolt, trigger, magazine, magazine release, bullet) in its own empty LOD and export each as FBX with "export current LOD only", normals off, master scale 100. Import each into Blender, set rotation to X 0, Z 90 (a part comes in at X 90), and give it a Child Of constraint to the armature with the matching weapon bone as sub-target. The weapon bones float in front of the right chest by default; the whole weapon hangs from `RightHand_Dummy`.
