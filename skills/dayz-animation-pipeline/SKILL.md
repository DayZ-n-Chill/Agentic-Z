---
name: dayz-animation-pipeline
description: "Produces and changes DayZ animations end to end: model.cfg skeletons and Animations, config.cpp AnimationSources, SetAnimationPhase wiring, items in hands and hide on attach, RTM and SEAnim files, the player and creature animation graphs, vehicle rider poses and weapons in hands. Use when a part must move, an item must sit in the hands, a creature or weapon needs clips or a graph, or a CMD_ command, .asi line or bone name must be found. Not for authoring .txa keyframes in Blender (blender-animation) or retargeting Mixamo clips (mixamo-retarget)."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-animation-pipeline

DayZ has two animation systems that share no files. Mixing them up is the most common mistake in animation work, so settle which one the request is about before anything else:

- **Config driven animation** moves a named selection of one model: a door, lever, wheel, gauge or hatch. It is text: `model.cfg`, `config.cpp` and a script call.
- **Skeletal animation** moves a character, creature or weapon in the hands. It is clips (`.anm`, `.rtm`) played by an animation graph.

Follow `skills/_shared/dayz-conventions.md`. The short checked facts are in the animation pack (`skills/_shared/animation/README.md`); this skill holds the workflows, the measured results and the tools.

## What an agent delivers and what the user runs

Say where every deliverable sits on this line, and what the user must run next. Promising work an agent cannot run is the worst outcome.

| Layer | What it is | Who does it |
|---|---|---|
| 1. Text | `model.cfg` (`CfgSkeletons`, `CfgModels`, `class Animations`), `config.cpp` `AnimationSources`, the script that sets phases, item in hands registration, hide on attach, a get in action. | The agent, fully. |
| 2. Interchange files | Strict SEAnim v1 and unbinarized `RTM_0101` / `RTM_MDAT` written or inspected with the tool in `scripts/tools/dayz-animation-formats/`; keyframes authored in Blender headless; poses solved from model anchors. `.anm` itself is not read or written here. | The agent writes the file; a converter the user runs turns it into the game format. |
| 3. GUI tools and the game | Workbench (`.txa` to `.anm`), `FBXToRTMGui.exe`, DayZATool, Object Builder, PBO signing, the in-game test. | The user, from exact steps the agent writes. |

A file that round-trips through the interchange tool is not proof the game accepts it. Keep the converter and in-game check as the gate.

The `.p3d` work an animation needs is not layer 3. A config driven animation needs a named selection to move and, for a rotation or translation, an axis made of two memory points; a skeletal bone is a named selection too. Adding those to an MLOD `.p3d` is script work for the dayz-p3d-inspector or dayz-model-pipeline skills (py3d), followed by `/dayz-p3d-audit`. Offer to do it; Object Builder is the user's preference, not a requirement. A binarized (ODOL) model has to be converted to MLOD by the user first.

## The wall to flag: one graph replacement at a time

A mod that replaces the player or a creature animation graph collides with every other mod that replaces the same graph. Loading two is reported to crash client and server; whether two can coexist on 1.30 has not been measured. Any plan that ships a replacement graph says so to the user.

This wall does not apply to:

- **Config driven animation.** Doors and levers are per model.
- **Weapon and item animation through a child `.asi`.** A per item instance file maps `WeaponOperations.<stance>.<state>` to the mod's own clips and inherits everything else, and script binds it per item with `AddItemInHandsProfileIK` (`P:\scripts\3_game\dayzplayer.c:243`) and `AddItemBoneRemap` (`:252`). No graph file is replaced, so several such mods load together. Do not warn about the wall for these.
- **One vehicle class's rider pose through a child `.asi`** (`references/vehicle-rider-ik-pose.md`).

Detail: `references/anim-graph.md` ("Which changes collide").

## Marking what is checked

Half of this domain is reverse engineered. The RTM and `.anm` formats are not documented by Bohemia, and community guides disagree. So every statement in this skill is one of three kinds, and output written from it keeps the kind:

- A **vanilla fact** cites the file on `P:\` as path and line. Open the line before repeating it in a deliverable.
- A **measured result** names the project and game build it was measured on. It is evidence for that setup, not a rule.
- Anything else is marked **not checked** or **not tested**. Never turn it into a fact to make a list look complete, and never invent a config key.

## Pick the route

Ask first whether the request is about an object or a skeleton. Most "animate X" requests about an object are layer 1 and never touch a clip.

| The user wants | Open |
|---|---|
| A door, lever, wheel, turret, hatch or gauge moved by the engine or by script | `references/config-driven-animation.md` |
| A handlebar or steering wheel that turns with the steering, and its link to the rider's hands | `references/handlebar-and-steering-config.md` |
| An attached item to appear or vanish, a carried item held in the right pose, a held item that points the wrong way, or the animation instance switched from script | `references/item-ik-and-hide.md` |
| A get in action that puts the player on the correct side of a seat | `references/dual-entry-action-pattern.md` |
| Named selections precise enough for action raycasts (seat, grip, door handle) | `references/selection-painter-for-actions.md` |
| The graph layer: graph, template and instance files, `CMD_` commands, variables, tags, weapon state names, the 1.29 to 1.30 graph port | `references/anim-graph.md` |
| A scripted player command that drives the vanilla graph: locomotion, jump, sync line foot events, `Raised` | `references/scripted-command-locomotion.md` |
| A custom animal, infected or other creature: skeleton, FBX export, first graph, AI wiring | `references/creature-animation.md` |
| Player bones by zone, the hand and IK helpers, twist bones, the measured parent table, the frame an IK pose is keyed in | `references/player-skeleton.md` and `references/ofp2-manskeleton-parents.txt` |
| Keyframes authored in Blender headless, axis and handedness maps | `references/blender-authoring.md` |
| What 1.30 changed for animation and what to migrate | `references/dayz-1-30-animation-changes.md` |
| Rules learned the hard way, proxy sub-pieces, viewer tooling notes, Linux | `references/lessons-and-tooling-notes.md` |
| The old py3d 1.0.0 write quirks and the frame check for a rebake script | `references/py3d-1.0.0-quirks.md` |
| A character, infected or weapon body clip through `.anm` | `references/skeletal-anm-enfusion.md` |
| A legacy `.rtm` clip, FBXToRTM | `references/skeletal-rtm.md` |
| Which tool does what, the walls, signing | `references/tooling-and-walls.md` |
| A driver or passenger pose solved from seat, grip and footpeg anchors | `references/vehicle-rider-ik-pose.md` |
| How a custom weapon sits in the hands and in the sights | `references/weapon-in-hands.md` |
| A weapon clip posed in the interactive viewer and exported as SEAnim | `references/weapon-anim-authoring-viewer.md` |
| A complete custom player weapon animation from Blender to the game | `references/weapon-anim-blender-complete.md` |

Sibling skills: blender-animation authors `.txa` keyframes, mixamo-retarget puts FBX motion capture on a rig (its baked action is a keyframe source for layer 2), dayz-characters covers rigging a body to the player skeleton, and dayz-motorbikes covers the vehicle side of the rider.

## Layer 1 workflow

1. **Name the motion.** Which named selection moves, around or along which axis, driven by what. A hide needs no axis. Add a missing selection or axis point with the model skills above.
2. **Write the skeleton and the animation** in `model.cfg`: the bones in `CfgSkeletons`, and in `CfgModels` the `skeletonName` and a `class Animations` entry with `type`, `source`, `selection`, `axis` or `begin` and `end`, `minValue` and `maxValue`, then `angle0` and `angle1` or `offset0` and `offset1`.
3. **Declare the source** in `config.cpp` `class AnimationSources` with `source = "user"`, `animPeriod` and `initPhase` when script drives it. An engine source such as `steeringwheel` needs no entry.
4. **Drive it** with `SetAnimationPhase` on the side that owns the state.
5. **Check the names** across `model.cfg`, `config.cpp` and the script. A typo fails with no error. `gen_model_cfg.py` writes the `model.cfg` from one description so the names cannot drift.

Write `.cpp` and `.c` files into the mod's folder under `workspace\<ModName>\`. Never invent a vanilla path; check it on `P:\`.

## Layer 2 workflow

1. **Get keyframes.** Author them in Blender headless against the DayZ skeleton, solve a pose from anchors (`ik_pose_to_seanim.py`), pose in the weapon viewer, or retarget motion capture with mixamo-retarget.
2. **Write the interchange file.** Use the strict package in `scripts/tools/dayz-animation-formats/` for new format work: `read_seanim`, `write_seanim`, `read_rtm`, `write_rtm` and their `_bytes` forms, and the inspector:

   ```cmd
   cd scripts\tools\dayz-animation-formats
   python -m dayz_animation_formats inspect <file.seanim or file.rtm>
   ```

   It handles full SEAnim v1 (channels, modifiers, notes, float32 and float64) and one unbinarized `RTM_0101` block with an optional `RTM_MDAT` before it. It refuses unknown flags and blocks, bad counts, truncated files, invalid names, non-finite values, wrong RTM bone order and trailing bytes. `seanim_writer.py` in this skill is the older project helper the viewer export still uses. The viewer route reads each bone's quaternion directly, so the unfinished positions to rotations helper in `ik_pose_to_seanim.py` is not on its path.
3. **Hand it to the converter the user runs:** SEAnim to `.anm` with DayZATool (`--generate-anim`), FBX to `.rtm` with `FBXToRTMGui.exe`, or `.txa` to `.anm` in Workbench.
4. **Bone names match the target skeleton exactly**, or the RPT logs `Bone X doesn't exist` and that bone does not move. Take the names from `references/player-skeleton.md`, never from a tutorial.

The RTM writer was cross read by Arma 3 Object Builder 2.5.1 with motion, phases, metadata and transforms preserved (reported by the source pack; not checked on `P:\`).

## Scripts

All in `<skill-dir>\scripts\`. The viewer steps pass files through the folder named by `DAYZ_ANIM_SCRATCH` (default `<tempdir>\dayz-anim-pipeline`). The two Blender steps take the rig FBX after `--` on the command line, or from `DAYZ_ANIM_RIG_FBX`; `extract_weapon.py` takes the `.p3d` as its argument, or from `DAYZ_ANIM_WEAPON_P3D`. Run a Blender step as `blender -b --python-exit-code 1 --python <script> -- <rig.fbx>` and stop at the first non-zero exit: without that flag an uncaught Python error still exits 0.

| Script | Needs | What it does |
|---|---|---|
| `gen_model_cfg.py` | Python | Writes a `model.cfg` from one JSON description of bones and animations (`python gen_model_cfg.py spec.json > model.cfg`; `--self-test` prints a sample). Warns on an animation type or key outside its checked set and on a selection that is not a declared bone. |
| `ik_pose_to_seanim.py` | Python | Solves a rider pose from the anchors in an `anchors.json` (seat, two grips, two feet) with two bone IK and writes one SEAnim per variant. The files hold solved joint positions and identity rotations: the step that turns positions into rotations against a rest pose is not written, with or without `--rest-pose`, so the output is a position reference, not a clip the game can play. |
| `seanim_writer.py` | Python | The older SEAnim writer used by the two exporters here. |
| `seanim_export.py` | Python | Turns a viewer animation JSON (local quaternions per bone and frame) into SEAnim through the bone frame map of the rig it reads. For weapon bone and partial tracks only, not full body actions. |
| `fbx_extract.py` | Blender | Dumps the Bohemia character rig FBX to `rig_raw.json`: rest matrices, parents, lengths, the body mesh and every empty. |
| `extract_empties.py` | Blender | Writes the helper empties' world matrices to `empties_armworld.json`. Exits 1 and writes nothing when the FBX has no `RightHand_Dummy`. |
| `build_rig_dayz.py` | Python, numpy | Converts the two JSON files to `rig_dayz.json` in the viewer's frame. That frame is right handed, so its coordinates written into a `.p3d` as they are land mirrored. |
| `extract_weapon.py` | Python, py3d | Extracts an MLOD weapon's first visual LOD and memory points to `weapon.json`. Stops when the installed py3d is not the DayZ fork. |
| `build_viewer.py` | Python, `viewer_core.py` | Builds the weapon animation viewer page from `rig_dayz.json` and `weapon.json` (`python build_viewer.py [out.html] [--viewer-core <path>]`). It looks for the viewer core under `scripts/tools/dayz-3d-viewer/` and then `skills/_shared/`. The page loads Three.js from a CDN. |
| `weapon_grip_viewer.py` | Python, py3d, `viewer_core.py` from `skills/_shared` | Compares a custom weapon's memory points, bore line and hand zones with a vanilla reference (both MLOD) and writes a viewer page plus an optional JSON report. The page loads Three.js from a CDN. |
| `install_py3d.py` | Python, pip | Installs the DayZ py3d fork from a built wheel: this skill's `wheels` folder first, then the `dist` folder of `scripts/tools/py3d/`. Stops without changing anything when there is no wheel, more than one, or an installed py3d that is not the fork. With no wheel built, `python -m pip install -e scripts/tools/py3d` installs it from source. |

The `.p3d` scripts need the DayZ fork of py3d (`scripts/tools/py3d/`, version 1.6.0 or later, `py3d.IS_DAYZ_FORK` true). `pip install py3d` installs an unrelated point cloud library from PyPI, and every geometry read then returns plausible garbage, so check the flag before trusting a result:

```cmd
python -c "import py3d; assert getattr(py3d, 'IS_DAYZ_FORK', False), py3d.__file__"
```

## Names tutorials get wrong

Correct these whenever the user repeats the tutorial spelling. Each is checked in `references/anim-graph.md` or `references/player-skeleton.md`.

| Tutorial says | Real name |
|---|---|
| "Entity Position", "Pin Look At" | `EntityPosition`, `LookAt` (`P:\DZ\anims\cfg\skeletons.anim.xml:5`, `:17`) |
| "right hand dummy" | `RightHand_Dummy` (`P:\DZ\anims\cfg\skeletons.anim.xml:115`) |
| "cmd death", "cmd success", "cmd attack" | `CMD_Death`, `CMD_AttackSuccess`, `CMD_Attack` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:63` to `:69`) |
| `discrete = 1` | `isDiscrete = 1` in `model.cfg` |
| `skeletonAnims.xml` | `skeletons.anim.xml` |
| "weapon cocked", "mag remove" as state names | `FireCocked`, `ReloadMagazineDetach` (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi:19`, `:52`) |
| "bullet in chamber" as a state | No such state; chambering is the commands `CMD_Reload_Chambering` and `CMD_Reload_ChamberingFast` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:275`, `:278`) |
| "reload is additive" | `CMD_Modifier_Additive` drives the sneeze and cough modifiers, not reloads (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5483`) |

## Building, testing and shipping

Build the mod with `/dayz-build-pbo`, run it with `/dayz-launch-test`, and read the logs with `/dayz-logwatch`; the dayz-mod-dev skill has the whole loop from `config.cpp` to the Workshop. The only acceptance for an animation is seeing it play in game with no bone errors in the RPT.
