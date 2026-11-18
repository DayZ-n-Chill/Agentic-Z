# Clips through `.anm`

How keyframes become a binary `.anm` clip the game plays, for characters, infected, animals and weapons. The graph that plays the clip is in `anim-graphs.md`; the full weapon walkthrough is in `weapon-anim-blender.md`.

Body and weapon motion runs on the Enfusion animation system: `.txa` text files compile to `.anm` clips, and an animation graph plays them. Facts about vanilla files cite `P:\`. Nothing about third party tools (DayZATool, the Blender plugins) is checked on `P:\`.

## Replacing a graph collides with other mods

A mod that replaces the player graph or a creature graph collides with every other mod that replaces the same graph, and two of them crash client and server (reported for third party mods, not checked on `P:\`). Say so in every plan that ships character or creature motion through a replaced graph, and ask whether the user already runs such a mod.

This applies to graph replacement only. A weapon or item clip bound through a child `.asi`, and one vehicle class's rider pose through a child `.asi`, replace no graph file and load next to other mods (`anim-graphs.md`, "Which changes collide"; `rider-pose-measured.md`, "The swap, with vanilla steering clips").

## Two routes to `.anm`

1. Key the motion in Blender against the DayZ skeleton.
2. Write an interchange file: a `.txa` from a DayZ animation plugin for Blender, or a SEAnim from `seanim_writer.py` or the SEAnim Blender plugin.
3. Turn it into `.anm`: Workbench compiles a `.txa`; `DayZATool --generate-anim` converts a SEAnim.
4. Name the `.anm` in an instance file, pack the PBO, sign it and test in game.

| Route | Who uses it | How |
|---|---|---|
| `.txa` | Bohemia's own tools | Export `.txa` with the DayZ animation plugin (`DayZAnimationPluginDemo` or its maintained fork) and let Workbench compile it. The Workbench step is in `weapon-anim-compile.md`. |
| SEAnim | An agent | Write SEAnim with `skills/dayz-animation-pipeline/scripts/seanim_writer.py`, the package in `scripts/tools/dayz-animation-formats/`, or the `io_anim_seanim` Blender plugin. The user runs `DayZATool --generate-anim file.seanim`. |

SEAnim is an open format with a public specification, so a script can write and edit it. `.anm` is closed, so the conversion is the one step the user runs. DayZATool converts in both directions.

The agent keys or edits motion in Blender run from the command line, writes or edits SEAnim, and maps bone names onto the player skeleton. The user, on Windows, runs DayZATool or Workbench, packs, signs and tests.

## Bone names must match the skeleton

The survivor skeleton is `player_testing.xob` (`skeletonName` in `P:\DZ\characters\data\config.cpp:158`), and its bone list is the block that starts at `P:\DZ\anims\cfg\skeletons.anim.xml:110`. The RPT calls the player skeleton `OFP2_ManSkeleton`; that name also appears inside binary character models such as `P:\DZ\characters\tops\shirt_m_new_anim_system.p3d`.

A bone name that does not match exactly logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not move (game behaviour, not checked on `P:\`). Take names from `player-skeleton.md`, the skeleton XML or Bohemia's public rig (the `DayZ-Misc` repository, "Rig and Animations"). Never guess one.

The vanilla skeleton cannot be restructured: a mod poses the vanilla bones, and adding or removing bones breaks the vanilla clips (not checked on `P:\`).

## Editing a vanilla `.anm`

1. `DayZATool --extract-anim file.anm` gives a SEAnim.
2. Edit it in Blender with the SEAnim plugin, or in a script (`seanim_writer.py`, or the reader in `scripts/tools/dayz-animation-formats/`).
3. `DayZATool --generate-anim edited.seanim` gives the new `.anm`.

Treat an extracted rig as a reference, not a rig to author on. Extraction is least reliable for empties and IK helper bones, the ones reload and weapon state clips use, and it inverts local bone axes. Author new work through `.txa`.

What the round trip keeps, measured on vanilla 1.30 player clips (the `MOTO2` steering pose with 119 bones, `stand2drive` with 27, and the one handed idle `p_1hd_erc_idle_low.anm` with 65):

- Rotations come back within 0.005 degrees and positions within 0.0021 cm.
- The generated file is `ANIMSET5` where the original is `ANIMSET6`; it plays in 1.30.
- It plays as an absolute pose. A clip that stores differences, as the vanilla transitions do, collapses the skeleton (`rider-pose-measured.md`, "Own clips on the rider").
- DayZATool 1.3 marks bones relative through SEAnim bone modifiers when it extracts, and drops those modifiers when it generates. On the idle the regenerated clip looked the same in game, because its relative bones carry no position keys; a clip whose relative bones do carry position keys was not tested. `seanim_writer.py` keeps the modifiers on read and write, and `test_seanim_writer.py` next to it checks that.
- On Windows, `DayZATool.exe --generate-anim f.seanim 100` runs from a script with stdin closed. It has also been seen to throw on `Console.ReadKey` after writing, so judge success by the output file, not the exit code.

## Which Blender plugin, which Blender

The `.txa` route is the one to use for player weapon animation; the plugin's demo mod uses it.

| Plugin | Blender | Note |
|---|---|---|
| `DayZAnimationPluginDemo` (original) | 3.6.8 to 4.0 | On 4.1 and later it fails with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`. |
| The maintained fork | 4.4 or later, 5.x included | Its `bl_info` says `(2, 80, 0)`; ignore that. |

Install either by copying the folder into Blender's add-ons folder as `DayzAnimationTools`. The download is a plain folder, not a zip, so "Install from file" does not work.

The other tools by name: DayZATool converts between `.anm` and SEAnim; `io_anim_seanim` is the SEAnim plugin, and its documentation defines the format; `DayZ-Misc` is Bohemia's public repository with the skeleton and rig reference.

## What 1.30 changed on this route

- Sub-graphs are `.agf` files. The master graph lists them in `GraphFilesResourceNames` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`): `locomotion.agf`, `actions.agf`, `combat.agf`, `vehicles.agf` and four more. 1.29 sub-graphs were text too, as separate `.agr` files in the older `$AnimGraph 7` syntax; 1.30 changed syntax and extension, not text against binary (`anim-graph-format-1-30.md`, "1.29 and 1.30: both text, different syntax").
- The vehicle sub-graph `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` holds the rider state machines, `MotorBikeSTM` among them (`:1582`). Types 10 and 11 are the motorbikes (`:2992` and `:2999`); the 1.29 file `vehicles.agr`, still on `P:\` after a 1.30 unpack over 1.29, ends at `"VehicleType == 9"` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agr:1741`). Reading it does not make it patchable: a new rider state or vehicle type still means replacing vanilla graph files (`tooling-and-walls.md`, "A mod cannot merge into a sub-graph").
- The 1.30 changelog says the 250 bone limit is gone and bone indices are worked out at run time from bone names. What the skeleton XML still carries is in `dayz-1-30-changes.md`, "Bones".
- The 1.30 changelog says the Workbench animation editor is the 2021 Enfusion one, with live editing against a running client and event table (`.ae`) files opened directly.
