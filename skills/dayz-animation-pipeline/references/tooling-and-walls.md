# Tools, who runs them, and the walls

Which tool does what, which of them an agent can run and which the user runs, the limits that no tool gets around, and what a handoff must say. The tool facts are the source pack's research from the tools' own pages (May 2026) and are not checked on `P:\`; the vanilla file facts cite `P:\`.

## Tool inventory

| Tool | Does | Who runs it |
|---|---|---|
| Editing `model.cfg` and `config.cpp` | Config driven animation (layer 1). | The agent. |
| `gen_model_cfg.py` (this skill) | Writes a `model.cfg` from one description. | The agent. |
| `seanim_writer.py` (this skill) and `scripts/tools/dayz-animation-formats/` | Write and read SEAnim; the package also reads and writes unbinarized `.rtm`. | The agent. |
| Blender headless (`bpy`) | Author and edit keyframes. | The agent. |
| DayZATool (DTZxPorter, dtzxporter.com/tools/dayzatool) | `.anm` to SEAnim (`--extract-anim`) and SEAnim to `.anm` (`--generate-anim`). Closed program, needs .NET Framework 4.5. | The user, on Windows. It also runs from a script without a window (`skeletal-anm-enfusion.md`). |
| Arma 3 Object Builder (MrClock8163, github.com/MrClock8163/Arma3ObjectBuilder) | Blender 4.2+ addon; imports and exports `.rtm`. | The user, in Blender. |
| ArmAToolbox (Alwarren, github.com/AlwarrenSidh/ArmAToolbox) | Older Blender `.rtm` export. | The user, in Blender. |
| `FBXToRTMGui.exe` (DayZ Tools) | FBX to `.rtm`. | The user. |
| DayZ animation plugin for Blender (github.com/jdfnc24/DayZAnimationPluginDemo, and its maintained fork) | Blender to `.txa` and `.txo`. | The user, in Blender; a headless import recipe is in `weapon-anim-blender-complete.md`. |
| Workbench (DayZ Tools, Steam app 830640) | Compiles `.txa` to `.anm` and `.txo` to `.xob`; animation and ragdoll editors. | The user. |
| `rtm_import` (github.com/4d4a5852/rtm_import) | Reads `.rtm` into Blender 2.80. Import only. | The user, in Blender. |
| SEAnim Blender plugin (github.com/SE2Dev/io_anim_seanim) | Imports and exports SEAnim. | The user, in Blender. |
| Addon Builder and Publisher (DayZ Tools) | Pack, sign, upload. | `/dayz-build-pbo` packs; signing and upload are the user's. |

## Two clip formats; do not mix them

- **`.rtm`** is the legacy Real Virtuality format: binary, reverse engineered, authored in Blender (Arma 3 Object Builder) or converted from FBX. In vanilla DayZ it survives for face poses, lip sync and simple animals (`skeletal-rtm.md`).
- **`.anm` and `.txa`** are Enfusion. `.txa` is text, Workbench compiles it to binary `.anm`. Characters, infected, animals with graphs and weapons use it. SEAnim is the open format that DayZATool converts to and from `.anm`.

Most confusion in community guides comes from mixing the two routes. A third thing is not a clip format at all: a door, lever or wheel that turns is a `model.cfg` animation (`config-driven-animation.md`).

## The walls

1. **One replacement of a graph at a time.** A mod that replaces the player graph or a creature graph cannot load next to another that replaces the same graph; two are reported to crash client and server (several Workshop mod descriptions say so). Flag it on every plan that ships a replaced graph. It does not touch config driven animation, and it does not touch weapon, item or rider animation bound through a child `.asi`: that route binds per item class in script (`AddItemInHandsProfileIK`, `P:\scripts\3_game\dayzplayer.c:243`, and `AddItemBoneRemap`, `:252`) and never edits a graph file, so several such mods load together. Do not warn about this wall on a custom weapon animation plan. One vehicle class's rider pose works the same way (`vehicle-rider-ik-pose.md`). Detail: `anim-graph.md`, "Which changes collide".
2. **`.rtm` is reverse engineered.** The format description is community work, not a contract, and can change between engine versions (`skeletal-rtm.md`).
3. **`.anm` is closed.** DayZATool writes it, as a closed program with its own licence terms, and Workbench writes it. There is no open source `.anm` writer.
4. **Bone names are exact.** A name that is not in the target skeleton logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not move.
5. **The vanilla skeleton cannot be restructured.** Animation is overlaid on the vanilla bones; adding or removing bones breaks the vanilla clips. Community consensus; no Bohemia document was read for it.

## Signing and shipping

Every mod PBO on a public server is signed with the mod's key (`.biprivatekey`, `.bikey`, `.bisign`) from DayZ Tools, and an animation mod is no different. `/dayz-build-pbo` packs, `/dayz-launch-test` runs the test and `/dayz-release-pack` prepares the release; the signing key and the upload stay with the user.

## What a handoff must say

When the agent produces an interchange file (a SEAnim, a `.txa`, a `.blend`), tell the user:

- the exact converter step that comes next, for example `DayZATool --generate-anim my.seanim`;
- the target skeleton, and that bone names must match it exactly;
- the graph wall, only when the plan replaces a graph;
- that packing, signing and an in-game test are still to do.

Never suggest that the agent ran Workbench, `FBXToRTMGui.exe` or a signing step when it did not.

## Which route for a player weapon animation

Use the `.txa` route: the DayZ animation plugin in Blender, then Workbench. It is what the plugin's demo mod and the community use. SEAnim through DayZATool is the fallback; a rig extracted that way is a reference, not a clean round trip (the community calls extracted rigs "always wrong" for empties and IK helper bones). `.rtm` is never right for a player weapon animation.

The original plugin and its maintained fork need different Blender versions, and the fork's declared version is meaningless; check the plugin's import code against the Blender in use before choosing. The versions and the install step are in `skeletal-anm-enfusion.md`, "Which Blender plugin, which Blender".

## 1.30: Workbench

All three from the 1.30 changelog, not tried by the source pack unless stated:

- The animation editor is the 2021 Enfusion one and supports live editing against a running game client.
- A ragdoll editor opens `.ragdoll` files; the player's is `P:\DZ\characters\bodies\human.ragdoll`.
- The editor opens event tables (`.ae`) directly. The 1.30 workspace names its table with `EventTable` (`P:\DZ\anims\workspaces\player\player_main\player_main.aw:15`); the 1.29 `#eventtable` line that tutorials said to delete is gone (`anim-graph.md`, "Opening the player graph in the Workbench animation editor").

## A mod cannot merge into a sub-graph

1.30 gives mods their own named file systems (the `-resolveFilePatchingUsingEnfusion=1` switch, per the changelog). An earlier version of the source pack concluded that, because sub-graphs are separate text files, a mod could patch one sub-graph without replacing the workspace. Nothing in the files supports that, and the evidence points the other way. Treat wall 1 as in force on 1.30.

Adding one vehicle type shows why. Every file it touches sits at a vanilla path under `P:\DZ\anims\workspaces\player\player_main\`:

- In `vehicles.agf`: a new state in the `VehicleMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:2913`), which has one `StartCondition "VehicleType == N"` per type (the motorbike `Jawa_Bitrak` state at `:2996` to `:2999`).
- In `vehicles.agf`: two group selection nodes like `Jawa_BitrakActionG` and `Jawa_BitrakG` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1381` to `:1392`).
- In `vehicles.agf`: the five literal conditions `VehicleType == 10 || VehicleType == 11` that send types 10 and 11 down the motorbike path (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1429`, `:1474`, `:1529`, `:1570`, `:2806`).
- In the template: both column lists that name `Jawa_05` and `Jawa_Bitrak` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1114` to `:1127`, and `:1154` to `:1167`).
- In the base instance: the lines of the new column in `player_main.asi`.
- Above type 12, the master graph too: it declares `VehicleType` with `MaxValue 12` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:108` to `:112`).

The player's config names one graph: `graphName` in `class enfAnimSys` of `SurvivorBase` (`P:\DZ\characters\data\config.cpp:153` to `:156`). Pointing it at a mod's copy replaces the whole graph as well.

So shipping any of these files means shadowing the vanilla file, which is the wall. The Workshop mod Survivor Animations does exactly this: per the source pack, its `player_main.pbo` carries the vanilla prefix `DZ\anims\workspaces\player\player_main` and prints a warning when Expansion's animation addon is also loaded. Whether a PBO with the vanilla prefix shadows file by file or the whole folder is not established.

Bohemia's own statement points the same way: the official DayZ post of 2026-09-16 says graph mods must redo their graph changes from scratch for 1.30 and that new limits apply, such as the number of groups. Neither that post nor the 1.30 notes say graph mods can now be layered or merged.

## The vehicle graph is readable, not extensible

`P:\DZ\anims\workspaces\player\player_main\vehicles.agf` holds the whole vehicle animation graph as text, so state machines such as `MotorBikeSTM` (`:1582`) can be inspected. That is not new in kind: 1.29 shipped the same sub-graph as text too (`vehicles.agr`, in the older format). Extending the state machine means shipping the vanilla path files listed above. A tour of the file is in `anim-graph.md`, "The vehicle graph, as a tour of the 1.30 node types".
