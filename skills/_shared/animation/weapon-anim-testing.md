# Testing a weapon animation

How to build, deploy and test a custom player weapon animation, how to judge the elbow, the failures that look done and are not, the RPT lines to expect, a full checklist, the timing of the vanilla AKM clips, and what is still unconfirmed. The route before this is in `weapon-anim-blender.md`.

## Build, sign, deploy

`/dayz-build-pbo` packs, `/dayz-launch-test` runs and `/dayz-logwatch` reads the logs. For an animation mod in particular:

- Pack only for scripts, layouts, `.anm`, `.paa` and sounds; binarize when configs, models or textures need converting. Binarizing an addon of scripts and clips is unnecessary, and packing a model or config addon without binarizing leaves it unconverted.
- Signing, optional for a local test: create a key pair with DayZ Tools' `DSCreateKey`, sign through Addon Builder or `DSSignFile`, check with `DSCheckSignatures`. Use lower case `addons` and `keys` folder and file names so a Linux server finds them. The exact arguments were not run.
- Addon Builder by hand: source folder, destination, prefix (`-prefix=`), project `-project=P:\` so paths across addons resolve, then `-binarize` or `-packonly`, with `-clear`, `-sign=<key.biprivatekey>` and `-include=<list>` as needed. A hand packed addon needs its prefix file at its root; the demo's tree has none because Workbench takes the prefix from the folder name.
- Deploy to `P:\Mods\@<ModName>\Addons\` (as `/dayz-build-pbo` does), with the public `.bikey` in the mod's `keys` folder when signatures are checked. A local test server has `allowFilePatching=1`, `verifySignatures=0` and BattlEye off.

File patching probably does not reload an `.anm`: loose scripts and layouts reload, but an `.anm` is a compiled resource reached through the instance file when the profile registers. The 1.30 named file systems (`-resolveFilePatchingUsingEnfusion=1`) might let Workbench load loose workspace resources; that is untested too. Until someone edits a loose `.anm`, starts the diag client with file patching and sees the weapon change without a repack, pack again after every clip change. The loop: edit in Blender, export `.txa`, "Reimport Resource" in Workbench, pack, reconnect, trigger the weapon state.

## What to test in game

Spawn the weapon, a magazine and ammunition. Chamber a round (no parts should move while chambering), attach an optic and a suppressor (they stay put), look down the sights (irons level), reload (the magazine follows the hand), fire (the bolt cycles). Then the elbow.

The pole angle of the Blender IK constraint is a preview value and is not exported; only the pose is. The forearm direction bone's position decides how far the elbow sticks out. Tune pole angle and that position, export, reimport, pack and test again. Elbow errors depend on the view, fine head on and collapsed into the ribcage from elsewhere, so run three tests: lean left and look down (the left elbow stays out of the ribcage), crouch, and throw (tap G). The plugin's IK is reverse engineered and about 90 to 95 percent accurate against the engine; expect several rounds.

## Limits

| Limit | Detail |
|---|---|
| Bone names are exact | A mismatch logs `Bone X doesn't exist in skeleton OFP2_ManSkeleton` and the bone is dead. The skeleton cannot be restructured. |
| One graph replacement at a time | Two mods that replace the player or a creature graph cannot load together. The instance file route is not affected. |
| No open `.anm` writer | Only Workbench and DayZATool write `.anm`; an agent can produce `.txa` or SEAnim. |
| No bone remap for other items | `AddItemBoneRemap` works for weapons only (not checked on `P:\`). |
| Two weapons at once | Only one weapon is assigned to the player; other clips fight it. |
| Aim space | Not solved by the plugin. |

Shipped weapon animation mods still show flaws: prone clips reusing standing or crouched poses so the gun clips into the ground, a left hand glitch on one shotgun when empty, a finger bending wrongly at the end of a chambering clip. Budget for that kind of imperfection.

## Looks done, is not

- Every bone exported on a reload: the "meatball". Selected bones only, except emotes.
- A states clip not ending on frame 2: only two frames, open and jammed break.
- Workbench trimming near equal keys: hold poses collapse.
- Bone scale: dropped when compiling.
- The Blender pole angle: not exported; check the elbow in game.
- Turning `LeftHand` or the IK helpers to fix the wrist: does nothing; fix the grip through geometry.
- A mistyped state name: falls back to the parent's clip silently. Mind the space in `Jamming Cancel`.
- No `AddItemBoneRemap`: the hands play, bolt, magazine and trigger do not.
- A lost `.txa`: the `.anm` cannot be edited again.
- A hold action without loop notes (`weapon-anim-authoring.md`, "Hold actions need loop notes").

Tool traps: the plugin README's Blender version is stale for the fork; a DayZATool extracted rig is unreliable for empties and has inverted local axes, so author with the plugin and extract only for reference; an FBX out of DayZATool taken back into Workbench as `.xob`, `.anm` or `.txa` breaks; stripped `{GUID}` prefixes; shipping edited vanilla files; animation editor crashes; magazine tracking without visual keying and a bake snaps; the weapon's skeleton confused with the player's; `.rtm` confused with `.txa` and `.anm`.

## RPT lines and symptoms

Rows 1 to 4 and 8 are confirmed; rows 5 to 7 are not checked.

| # | RPT line or symptom | Cause | Fix |
|---|---|---|---|
| 1 | `Error: Bone <name> doesn't exist in skeleton OFP2_ManSkeleton`, once per bone; that bone is still, the rest plays | The clip, model config or a selection names a bone the skeleton lacks: a typo, wrong case, a bone from another game, a remapped weapon bone never tied to a character bone | Match the skeleton's list exactly; remove or rename foreign bones. |
| 2 | `ANIMATION (E): Can't load <Mod>/Anims/cfg/skeletons.anim.xml`, then `ANIMATION (E): Failed to open file, line 0, column 0` | A skeleton or animation config path that is not packed, a wrong prefix, or a case mismatch; the same shape for a missing `.anm` named by an instance line | Check the exact path is packed with the right case (quoted from a real server RPT). |
| 3 | Blender export fails with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'` | The original plugin on Blender 4.1 or later | Blender 3.6.8 to 4.0 for the original; 4.4 or later for the fork. |
| 4 | Two animation mods crash the game, or one silently wins | Both replace the player graph | Merge the graph mods into one; instance file weapon mods are not affected. |
| 5 | Limbs snap to a default or T pose, or part of the body freezes | Not every bone the clip owns has a key | Key every bone the clip owns. |
| 6 | Arms and weapon badly wrong after a two handed clip where a one handed one is expected | Wrong handedness | Put the clip in the instance of the right kind. |
| 7 | Right in Blender, bones twist or roll wrong in game | Blender bones run along +Y, DayZ's along +X | Use the official rig and exporter, or the per rig maps in `weapon-anim-viewer.md`; check in game. |
| 8 | An extracted rig is "always incorrect" | An extract is a reference, not a clean round trip | Use it as a starting point only. |

Still to capture in an in game test: the RPT wording when an instance line names a clip that does not exist, and whatever is logged for a weapon whose bolt is dead or an IK pose imported without the IK bones.

## Checklist

Setup:

- [ ] Blender matches the plugin (fork 4.4 or later, original 3.6.8), checked against the importer's calls.
- [ ] `DayzAnimationTools` in the addons folder and enabled.
- [ ] `/dayz-preflight` passes; the Workbench project opens.

Author:

- [ ] Master rig open, or an IK sample scene for grip work; "Add Survivor IK Bones" run before any IK pose work.
- [ ] Closest vanilla pose or clip imported; weapon FBX parts attached if wanted.
- [ ] IK pose keys only `LeftHandOrigin`, `RightHandOrigin` and the two forearm direction bones.
- [ ] Fire about 7 frames, trigger pulled on frame 0, bolt cycle, eject event.
- [ ] Weapon states three frames (closed, open, jammed), end frame 2, weapon bones only.
- [ ] Reload, charge, chamber, jam: shoulders down, keyed bones only, small spine motion.
- [ ] Hold actions carry `LoopStart` and `LoopEnd`.
- [ ] No IK helper keys outside IK poses; no scale keys; helper bones recomputed and checked.
- [ ] Events set, state change events included.

Export, compile, wire:

- [ ] `.txa` with the right type at 30 fps; registered or reimported in Workbench; `.anm` and `.anm.meta` exist; `.txa` kept beside each `.anm`.
- [ ] Instance: `Template` is `player_main.ast`, matching parent, `IkPose` set, `ErcRas` and `PneRas` lines, `{GUID}` prefixes kept, state names exact.
- [ ] `RegisterFireArms` calls `AddItemInHandsProfileIK` and `CustomBoneRemapping` calls `AddItemBoneRemap`, both on the base class; the weapon's `model.cfg` bones match the remap's first names.
- [ ] `CfgMods` has the world script module; every PBO's `requiredAddons[]` is set.

Build and test:

- [ ] Packed (pack only for scripts and clips, binarize models and configs) and deployed to a server with file patching and no signature check.
- [ ] Chamber, optic, sights, reload and fire right in game; the three elbow tests pass; repack after every clip change.
- [ ] Only per weapon clips through `AddItemInHandsProfileIK`, so no conflict; any player graph change is exclusive with every other graph mod, and the user knows.

## Frame budget of the vanilla AKM clips

Extracted to SEAnim with DayZATool 1.3 and read with `seanim_writer.py`; all at 30 fps (also read from the `FPS` chunk of `w_akm_states.anm`), frame count being the last key index plus one. The clips are in `P:\DZ\anims\anm\player\reloads\AKM\` and `P:\DZ\anims\anm\player\ik\weapons\`; the numbers cannot be checked there without extracting.

| Clip | Frames | Duration | Bones | Purpose |
|---|---|---|---|---|
| `p_erc_reload_mag_remove_akm_ras` | 22 | 0.700 s | 69 | Magazine detach, the removal part |
| `p_erc_reload_mag_nobullet_akm_ras` | 55 | 1.800 s | 69 | Full magazine swap, no chambering |
| `p_erc_reloadaction_closed_akm_ras` | 44 | 1.433 s | 73 | Charging handle pull, closed bolt |
| `p_erc_chambering_closed_akm_ras` | 107 | 3.533 s | 73 | Chamber a loose round, closed bolt |
| `p_erc_fire_akm_ras` | 11 | 0.333 s | 45 | One fire cycle |
| `p_erc_jam_akm_ras` | 230 | 7.633 s | 73 | Clearing a jam |
| `w_akm_states` | 2 | 0.033 s | 10 (weapon bones) | Bolt and bullet states |
| `ik\weapons\akm` (IK pose) | 2 | 0.033 s | 43 | Grip pose registered by script for `AKM_Base` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`); the `.asi` names `izh18` (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:6`) |

The demo mod ships only `.anm` files for other kinds of clip, so frame ranges beyond its fire (7) and states (3) samples come from these extracts.

## Still unconfirmed

Do not state these as facts:

1. The full ordered bone list of the master rig against the game skeleton (inferred from sample `.txa` files and plugin code; `player-skeleton.md` is the checked list).
2. Whether the fork really fails on Blender 3.6.8.
3. The instance and template grammar beyond what demo and vanilla files show.
4. The player clip frame rate is in no workspace text file; 30 is read from clips. Whether a mismatched export rate changes speed is untested.
5. Bohemia's feedback tickets on an official IK and instance interface, animation editor bugs and the register callback stack overflow.
6. Which command or transition starts each `WeaponOperations` state.
7. A way to turn off Workbench's key trimming.
8. Scale being dropped when compiling (the plugin's default agrees).
9. Action clips playing over the states clip (consistent with the demo).
10. Whether an invalid `reloadAction` logs more than a warning.
11. "Since 0.63 all weapon animation is on the character's side, not in `model.cfg`".
12. Any in game difference between the Survivor Reload and Additive types.
13. That `ReloadMagazineDetach`'s clip is the hand coming back from the hip.
14. Swapping a weapon's profile at run time when an attachment changes.
15. What `Weapon_Bone_01` to `06` mean per weapon family beyond vanilla remaps.
16. Whether a weapon only animation ever needs its own `inputs.xml` action.
17. The translation unit factor between Blender and DayZ (1.0 assumed).
18. Whether file patching reloads an `.anm`.
19. Workbench's menu wording per tools version.
20. What custom weapon clips or many registrations cost in performance.
21. The exact arguments of the signing tools.
