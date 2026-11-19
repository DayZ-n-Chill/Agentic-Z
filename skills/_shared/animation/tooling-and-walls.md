# Animation tools and limits

Which tool does what, which an agent runs and which the user runs, the limits no tool gets round, and what a handoff must say. Tool facts are not checked on `P:\`; vanilla file facts cite it.

## What the agent delivers and what the user runs

Say where every deliverable sits in this table and what the user runs next. Promising work the agent cannot run is the worst outcome.

| Layer | What it is | Who does it |
|---|---|---|
| 1. Text | `model.cfg` (`CfgSkeletons`, `CfgModels`, `class Animations`), `config.cpp` `AnimationSources`, the script that sets phases, item in hands registration, hide on attach, a get in action. A steering part is layer 1 too: `model.cfg` only, an engine source and two axis points (`handlebar-and-steering.md`). | The agent, fully. |
| 2. Interchange files | Strict SEAnim v1 and unbinarized `RTM_0101` / `RTM_MDAT`, written or read with the tool in `scripts/tools/dayz-animation-formats/`; keys authored with Blender from the command line; poses solved from model anchors (`rider-pose-solver.md`). `.anm` itself is not read or written here. | The agent writes the file; a converter the user runs makes the game format. |
| 3. GUI tools and the game | Workbench (`.txa` to `.anm`), `FBXToRTMGui.exe`, DayZATool, Object Builder, PBO signing, the in game test. | The user, from exact steps the agent writes. |

A file that round trips through the interchange tool is not proof the game accepts it. The only acceptance for an animation is seeing it play in game with no bone errors in the RPT.

The `.p3d` work an animation needs is not layer 3: adding a named selection or two axis points to an MLOD `.p3d` is script work (`model-cfg-animations.md`, "Naming checklist").

## Marking what is checked

The RTM and `.anm` formats are reverse engineered, Bohemia does not document them, and community guides disagree. So every statement in this pack is one of three kinds, and output written from it keeps the kind:

- A vanilla fact cites the file on `P:\` by path and line. Open the line before repeating it in a deliverable.
- A measured result says what it was measured on. It is evidence for that setup, not a rule.
- Anything else is marked not checked or not tested. Never turn it into a fact to complete a list, and never invent a config key.

## The tools

| Tool | Does | Who runs it |
|---|---|---|
| Editing `model.cfg` and `config.cpp` | Config driven animation. | The agent. |
| `gen_model_cfg.py` (`skills/dayz-animation-pipeline/scripts/`) | Writes a `model.cfg` from one description. | The agent. |
| `seanim_writer.py` (same folder) and `scripts/tools/dayz-animation-formats/` | Write and read SEAnim; the package also reads and writes unbinarized `.rtm`. | The agent. |
| Blender from the command line (`bpy`) | Author and edit keys. | The agent. |
| DayZATool | `.anm` to SEAnim (`--extract-anim`) and SEAnim to `.anm` (`--generate-anim`). Closed program, needs .NET Framework 4.5. | The user, on Windows. It also runs from a script without a window (`anm-clips.md`). |
| Arma 3 Object Builder addon | Blender 4.2 and later; imports and exports `.rtm`. | The user, in Blender. |
| ArmAToolbox | Older Blender `.rtm` export. | The user, in Blender. |
| `FBXToRTMGui.exe` (DayZ Tools) | FBX to `.rtm`. | The user. |
| DayZ animation plugin for Blender (`DayZAnimationPluginDemo` and its maintained fork) | Blender to `.txa` and `.txo`. | The user, in Blender; a command line import recipe is in `weapon-anim-blender.md`. |
| Workbench (DayZ Tools, Steam app 830640) | Compiles `.txa` to `.anm` and `.txo` to `.xob`; animation and ragdoll editors. | The user. |
| `rtm_import` | Reads `.rtm` into Blender 2.80; import only. | The user, in Blender. |
| SEAnim Blender plugin (`io_anim_seanim`) | Imports and exports SEAnim. | The user, in Blender. |
| Addon Builder and Publisher (DayZ Tools) | Pack, sign, upload. | `/dayz-build-pbo` packs; signing and upload are the user's. |

## Two clip formats, never mixed

- `.rtm` is the older Real Virtuality format: binary, reverse engineered, authored in Blender with the Object Builder addon or converted from FBX. Vanilla DayZ still uses it for face poses, lip sync and simple animals (`rtm-and-character-animation.md`).
- `.anm` and `.txa` are Enfusion. `.txa` is text that Workbench compiles to binary `.anm`. Characters, infected, animals with graphs and weapons use it. SEAnim is the open format DayZATool converts to and from `.anm`.

Most confusion comes from mixing the two. A door, lever or wheel that turns is neither: it is a `model.cfg` animation (`model-cfg-animations.md`).

## The walls

1. One graph replacement at a time. A mod that replaces the player graph or a creature graph cannot load next to another that replaces the same graph; the two crash client and server (third party mod behaviour, not checked on `P:\`). Flag it on every plan that ships a replaced graph. It does not touch config driven animation, nor weapon, item or rider animation bound through a child `.asi`: that route binds per item class in script (`AddItemInHandsProfileIK`, `P:\scripts\3_game\dayzplayer.c:243`, and `AddItemBoneRemap`, `:252`) and never edits a graph file, so several such mods load together. Do not warn about this wall on a custom weapon animation plan. One vehicle class's rider pose works the same way (`rider-pose-measured.md`). Detail: `anim-graphs.md`, "Which changes collide".
2. `.rtm` is reverse engineered. Its description is not a contract and can change between engine versions (`rtm-and-character-animation.md`).
3. `.anm` is closed. Only DayZATool and Workbench write it; there is no open source `.anm` writer.
4. Bone names are exact. A name not in the target skeleton logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not move (runtime log behaviour, not checked on `P:\`).
5. The vanilla skeleton cannot be restructured. Animation lies over the vanilla bones; adding or removing bones breaks the vanilla clips (not checked on `P:\`).
6. Some systems are reported unfinished and not rechecked: holding two weapons at once, the full bow mechanic, and custom additive locomotion (changing the additive walk and run layer easily breaks the character). A plan that touches any of them is high risk from day one (not checked on `P:\`).

## Signing and shipping

Every mod PBO on a public server is signed with the mod's key (`.biprivatekey`, `.bikey`, `.bisign`) from DayZ Tools; an animation mod is no different. `/dayz-build-pbo` packs, `/dayz-launch-test` runs the test and `/dayz-release-pack` prepares the release; the key and the upload stay with the user.

## What a handoff must say

When the agent produces an interchange file (a SEAnim, a `.txa`, a `.blend`), tell the user:

- the exact converter step that comes next, such as `DayZATool --generate-anim my.seanim`;
- the target skeleton, and that bone names must match it exactly;
- the graph wall, only when the plan replaces a graph;
- that packing, signing and an in game test are still to do.

Never suggest the agent ran Workbench, `FBXToRTMGui.exe` or a signing step when it did not.

## Which route for a player weapon animation

Use the `.txa` route: the DayZ animation plugin in Blender, then Workbench, as the plugin's demo mod does. SEAnim through DayZATool is the fallback; a rig extracted that way is a reference, not a clean round trip, because extracted rigs are wrong for empties and IK helper bones. `.rtm` is never right for a player weapon animation.

The original plugin and its fork need different Blender versions, and the fork's declared version means nothing; check the plugin's import code against the Blender in use first. Versions and install are in `anm-clips.md`, "Which Blender plugin, which Blender".

## Rules learned on projects

Project experience, not vanilla facts.

- For a vehicle boarded from both sides, add no scripted snap and no extra `pos_*_L` and `pos_*_R` points. Copy the vanilla structure: crew proxies, and seat selections and components that exist in the View Geometry and Fire Geometry. Keep the vanilla action (`get-in-sides.md` keeps the older snap as a fallback).
- Before adjusting a pose offline, list what really sets it in game: the weapon's origin, the bone remap, the IK pose, the geometry, and the stance and aim space. Build the viewer from that data; do not chain visual guesses.
- For joints the game solves with IK at run time, dump the bones' model space positions from the client and rebuild the offline pose from positions. Do not guess the elbow's swivel or trust raw rotations whose convention is not checked.
- Read a large file back after writing it and check its last line is the one intended; an editor tool has cut new text at about 5 to 8 KB without warning when the file sat in a synced cloud folder or a plugin mount.
- Reuse a viewer's baked geometry instead of parsing a large `.p3d` again, and draw overlays unlit and 5 mm off the surface (`selections-for-actions.md`).
- A written file is not a checked file. After any script writes a `.p3d`, reopen it and check the selections are not empty, the memory points are where they should be and the material count is unchanged (`_shared/py3d-mlod-notes.md`, "Check the output before calling it done").

## Workbench in 1.30

From the 1.30 changelog, not tried in Workbench unless stated:

- The animation editor is the 2021 Enfusion one and can live edit against a running game client.
- A ragdoll editor opens `.ragdoll` files; the player's is `P:\DZ\characters\bodies\human.ragdoll`.
- The editor opens event tables (`.ae`) directly. The 1.30 workspace names its table with `EventTable` (`P:\DZ\anims\workspaces\player\player_main\player_main.aw:15`); the 1.29 `#eventtable` line that had to be deleted by hand is gone (`anim-graph-format-1-30.md`, "Opening the player graph in the Workbench animation editor").

## A mod cannot merge into a sub-graph

1.30 gives mods their own named file systems (the `-resolveFilePatchingUsingEnfusion=1` switch in the changelog). Sub-graphs being separate text files does not let a mod patch one without replacing the workspace; nothing in the files supports it and the evidence points the other way. Treat wall 1 as in force on 1.30.

Adding one vehicle type shows why. Every file it touches sits at a vanilla path under `P:\DZ\anims\workspaces\player\player_main\`:

- `vehicles.agf`: a new state in the `VehicleMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:2913`), which has one `StartCondition "VehicleType == N"` per type (the motorbike `Jawa_Bitrak` state at `:2996` to `:2999`).
- `vehicles.agf`: two group select nodes like `Jawa_BitrakActionG` and `Jawa_BitrakG` (`:1381` to `:1392`).
- `vehicles.agf`: the five literal conditions `VehicleType == 10 || VehicleType == 11` that send types 10 and 11 down the motorbike path (`:1429`, `:1474`, `:1529`, `:1570`, `:2806`).
- The template: both column lists naming `Jawa_05` and `Jawa_Bitrak` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1114` to `:1127`, and `:1154` to `:1167`).
- The base instance: the new column's lines in `player_main.asi`.
- Above type 12, the master graph too: it declares `VehicleType` with `MaxValue 12` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:108` to `:112`).

The player's config names one graph: `graphName` in `class enfAnimSys` of `SurvivorBase` (`P:\DZ\characters\data\config.cpp:153` to `:156`). Pointing it at a mod's copy replaces the whole graph as well.

So shipping any of these files shadows the vanilla file, which is the wall. The Workshop mod Survivor Animations does exactly that (its own files, not vanilla): its `player_main.pbo` carries the vanilla prefix `DZ\anims\workspaces\player\player_main` and prints a warning when Expansion's animation addon is also loaded. Whether a PBO with the vanilla prefix shadows file by file or the whole folder is not known. Bohemia's own 1.30 announcement says graph mods must redo their graph changes from scratch and that new limits apply, such as the number of groups; neither it nor the 1.30 notes say graph mods can be layered or merged.

## The vehicle graph is readable, not extensible

`vehicles.agf` holds the whole vehicle animation graph as text, so state machines such as `MotorBikeSTM` (`:1582`) can be read. That is not new in kind: 1.29 shipped the same sub-graph as text (`vehicles.agr`, older format). Extending it means shipping the vanilla path files above. A tour of the file is in `anim-graph-format-1-30.md`, "The vehicle graph, as a tour of the 1.30 node types".

## On Linux

Everything in this pack is the Windows workflow. What changes on Linux, measured under Proton (the setup and tool matrix are in `_shared/linux-proton.md`):

- `.rtm` and `.p3d` binarize through `dayzmake build --proton-binarize` with dayzmake 1.0.0 or later.
- Workbench starts and compiles its bundled scripts. Its animation editor, `.agr` and `.asi` editing and the `.txa` to `.anm` import are not checked there. Without `P:\dz` extracted it logs missing vanilla config entries.
- Object Builder runs.
- The tool in `scripts/tools/dayz-animation-formats/` is Python and runs natively.
- PowerShell helper scripts need translating to shell.
