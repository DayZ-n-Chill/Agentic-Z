# Skeletal animation through `.anm` (characters, infected, animals, weapons)

Body and weapon animation in DayZ runs on the Enfusion animation system: `.txa` text files compiled to binary `.anm` clips, played by an animation graph. This file is the route from keyframes to a clip the game loads. The graph side is in `anim-graph.md`; the complete weapon walkthrough is in `weapon-anim-blender-complete.md`.

Facts about vanilla files cite `P:\`. Results marked "measured" name the project and build they come from. Everything about third party tools (DayZATool, the Blender plugins) is the source pack's research and is not checked on `P:\`.

## The wall, first

A mod that replaces the player graph or a creature graph collides with every other mod that replaces the same graph; two are reported to crash client and server. Say so on every plan that ships a character or creature animation through a replaced graph. If the user already runs such a mod, a second one conflicts with it.

The wall is about graph replacement only. A weapon or item animation bound through a child `.asi`, and one vehicle class's rider pose through a child `.asi`, replace no graph file and load next to other mods (`anim-graph.md`, "Which changes collide"; `vehicle-rider-ik-pose.md`, "A pose for one vehicle class without a graph change").

## The pipeline

```
Blender (keyframes against the DayZ skeleton)
  -> .txa (text)            a DayZ animation plugin for Blender        or
  -> SEAnim (open format)   seanim_writer.py, or the SE2Dev Blender plugin
       -> .anm (binary)     DayZATool --generate-anim                  or
  -> Workbench compiles .txa -> .anm
       -> name the .anm in an instance file -> pack the PBO -> sign -> test in game
```

There are two ways to reach `.anm`:

1. **The `.txa` route, the one Bohemia's own tools use.** Author in Blender, export `.txa` with the DayZ animation plugin (`jdfnc24/DayZAnimationPluginDemo` on GitHub, or its maintained fork), and let Workbench compile `.txa` to `.anm`. The tool exists and is in use; the exact Workbench step is described in `weapon-anim-blender-complete.md`.
2. **The SEAnim route, the one an agent can drive.** Produce a SEAnim file, with this skill's `seanim_writer.py`, with the package in `scripts/tools/dayz-animation-formats/`, or with the SE2Dev Blender plugin. The user then runs `DayZATool --generate-anim file.seanim` to get the `.anm`. DayZATool converts in both directions.

SEAnim matters because it is an open format (the SE2Dev specification), so a script can write and edit it. `.anm` is closed; the conversion is the one step the user runs.

## Who does what

- The agent: authors or edits keyframes in Blender headless, writes or edits SEAnim, and maps bone names to the player skeleton.
- The user, on Windows: runs DayZATool or Workbench, packs, signs and tests.

## Skeleton and bones

The survivor's skeleton is `player_testing.xob` (`skeletonName` in `P:\DZ\characters\data\config.cpp:158`), and its bone list is the block that starts at `P:\DZ\anims\cfg\skeletons.anim.xml:110`. Community material and RPT messages call the player skeleton `OFP2_ManSkeleton`. A bone name that does not match exactly logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` in the RPT and that bone does not move.

Take the bone names from `player-skeleton.md`, from the skeleton XML, or from Bohemia's public rig (`BohemiaInteractive/DayZ-Misc`, "Rig and Animations"). Never guess one.

Community consensus, not checked: the vanilla skeleton cannot be restructured. A mod overlays animation on the vanilla bones; adding or removing bones breaks the vanilla clips.

## Editing or retargeting a vanilla `.anm`

1. `DayZATool --extract-anim file.anm` gives a SEAnim.
2. Edit it in Blender (the SE2Dev SEAnim plugin) or with a script (`seanim_writer.py`, or the reader in `scripts/tools/dayz-animation-formats/`).
3. `DayZATool --generate-anim edited.seanim` gives the new `.anm`.

A community note (the MRTsBackflip mod's description) says rigs extracted with DayZATool are "always incorrect". Treat an extract as a starting point and check the rig. The source pack confirmed the scope of that warning: DayZATool and Mikero's extraction are worst for empties and IK helper bones, the ones weapon reload and state clips use, and they invert local bone axes. Use an extract as a reference and author through `.txa`.

### Measured: the round trip keeps the values, as an absolute pose

Measured by the LFRider project on two vanilla 1.30 player clips (the `MOTO2` steering pose, 119 bones, and `stand2drive`, 27 bones), 2026-09-28:

- Extract then generate kept rotations within 0.005 degrees and positions within 0.0021 cm.
- The generated file is `ANIMSET5`; the originals are `ANIMSET6`. It plays in 1.30.
- It plays as an absolute pose. A clip that holds differences, as the vanilla transitions do, collapses the skeleton (`vehicle-rider-ik-pose.md`, "Own clips on the rider").
- On a Windows host DayZATool runs without a window from a script: `DayZATool.exe --generate-anim f.seanim 100` with stdin closed returned 0 and wrote the file (2026-09-29). An earlier session saw it throw on `Console.ReadKey` after writing. Judge by the output file, not the exit code.

### Measured: DayZATool drops SEAnim bone modifiers when it generates

Measured by the source pack, 2026-10-03, on `p_1hd_erc_idle_low.anm`:

- DayZATool 1.3 marks bones RELATIVE through SEAnim bone modifiers when it extracts a vanilla clip. The extract has an ABSOLUTE header and 60 RELATIVE modifiers on its 65 bones. The five without one (`Scene_Root`, `EntityPosition`, `Collision`, `Pelvis`, `LeftHand_Dummy`) are the only bones with position keys.
- That SEAnim, unchanged, through `--generate-anim 100` gives an `.anm` of the same 209,300 bytes as the vanilla file with a different hash. It extracts again with no modifier: the same 65 bones, rotations within 0.0035 degrees, positions within 0.0016 cm on any axis (0.0027 cm as a distance).
- In game (DayZDiag 1.29.163709, 2026-10-02) the regenerated idle looked like the vanilla one. This clip could not show a difference, because its RELATIVE bones carry no position keys. What the loss does to a clip whose RELATIVE bones do carry them was not measured.
- Until 2026-10-03 `seanim_writer.py` dropped the modifiers too, on read and on write. It now keeps them: that extract read and written back is byte identical, and `test_seanim_writer.py` next to the script checks the same on synthetic clips.

## Which Blender plugin, which Blender

The `.txa` route is the recommended one for player weapon animation; it is what the plugin's demo mod and the community use.

- The original plugin (`jdfnc24/DayZAnimationPluginDemo`, by MrTea) needs Blender 3.6.8 to 4.0. On 4.1 and later it fails with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`.
- The maintained fork (Sanitoeter05) is the opposite: it needs Blender 4.4 or later, including 5.x. Its `bl_info` says `(2, 80, 0)`, which means nothing.
- Install either one by copying the folder into Blender's addons folder as `DayzAnimationTools`. The download is a plain folder, not a zip, so "Install from file" does not work.

## Where the tools come from

- DayZATool: dtzxporter.com/tools/dayzatool
- SEAnim Blender plugin, which also defines the SEAnim format: github.com/SE2Dev/io_anim_seanim
- DayZ `.txa` Blender plugin: github.com/jdfnc24/DayZAnimationPluginDemo
- Skeleton and rig reference: github.com/BohemiaInteractive/DayZ-Misc

## What 1.30 changed on this route

- **Sub-graphs are `.agf` files.** The master graph lists them in `GraphFilesResourceNames` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`): `locomotion.agf`, `actions.agf`, `combat.agf`, `vehicles.agf` and four more. They were text in 1.29 as well (separate `.agr` files in the older `$AnimGraph 7` format, listed by the root graph); 1.30 changed the syntax and the extension, not text against binary. Detail: `anim-graph.md`, "1.29 and 1.30: both text, different syntax".
- **The vehicle sub-graph can be read.** `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` holds the rider state machines, `MotorBikeSTM` among them (`:1582`). What 1.30 adds is the motorbike rider; the 1.29 graph stopped at vehicle type 10 and had no `Jawa_` column. Readable does not mean patchable: a new rider state or vehicle type still means replacing vanilla graph files (`tooling-and-walls.md`, "A mod cannot merge into a sub-graph").
- **Bones.** Per the 1.30 changelog the limit of 250 bones is gone and bone indices are worked out at run time from the bone names. What the skeleton XML still carries is in `dayz-1-30-animation-changes.md`, "Bones".
- **Workbench.** Per the 1.30 changelog the animation editor is the 2021 Enfusion one, with live editing against a running game client and event table (`.ae`) files opened directly.
