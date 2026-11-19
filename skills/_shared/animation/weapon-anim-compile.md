# Exporting and compiling weapon clips

How to export a weapon clip from Blender as `.txa`, set its events, what the plugin's two coordinate changes are, how Workbench compiles `.txa` to `.anm`, and what the compile loses. Authoring is in `weapon-anim-authoring.md`; wiring the result into the game in `weapon-anim-wiring.md`.

## Export types

File, Export, "DayZ Animation (.txa)", then pick the type:

| Type | Use |
|---|---|
| Full Body | Emotes only. Adds a `Scene_Root` root bone. |
| Survivor IK 1h | One handed grip pose. |
| Survivor IK 2h | Two handed grip pose. |
| Survivor Reload | Rarely; reloads are treated as Additive. |
| Additive | Reload, charge, fire, weapon states. |

- An IK pose: an IK type, with no bones selected beforehand.
- Reload, fire and states: Additive with "Selected Bones Only" and only the relevant bones selected. Exporting every bone on a reload makes the character "turn into a meatball" in game, head gone and body distorted; Full Body is for emotes.
- Bones whose names end in `ik_helper` are always skipped.
- The maintained fork turns every bone constraint off before sampling and on again after, so bake any pose that depends on a constraint before exporting.

## Events

In the side panel's "Events" section, Load reads the existing events, stored as pose markers named `Type|Args|ID`; add or remove them; set frame, type, arguments and id; Save writes them back. Events carry sound ids (mapped to the `SoundWeapon` classes under `AnimEvents` in the weapon's config) and, more important, the weapon's state changes (bullet chambered, weapon cocked), which are needed even with no sound at all. On export the markers become `$events { #event <frame> "Name" "Args" <ID> }`.

## The .txa format

Player and weapon bones both appear as `$node` entries (from the plugin's samples):

```text
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

## Two coordinate changes in the plugin

Keep them apart:

1. The axis fix: a +90 degree turn about Z that swaps Blender's X and Y. It is not a Y and Z swap. Importer, exporter and object exporter all apply it.
2. The component order in the text: translation and scale are written X Z Y, and a quaternion as (x, z, y, -w); reading mirrors that, and the export also negates all four components at the end.

Merging them, or assuming a plain Y and Z swap, gives wrong rotations; a round trip outside the plugin needs both. The default unit factor is 1.0, as the demo uses; it is not confirmed against vanilla.

## .txo files

File, Export, "DayZ Object (.txo)" is for a custom skeleton such as a creature, with optional mesh and weights. Options: scale, selection or visible only, "Auto Create EntityPosition", "Auto Create HeadLook" (head look bone default `pin_lookat`; use `LookAt` for vanilla infected, as `P:\DZ\anims\cfg\skeletons.anim.xml:17` spells it; parent default `head`; offset default 0, 0.25, 0). It warns above 4 weights per vertex, the DayZ limit. Workbench registers it as an `.xob`. A player weapon animation reuses the vanilla skeleton and skips this; creatures are in `creature-rig-to-game.md`.

## Compiling in Workbench

In the resource browser right click the `.txa`: "Register resource and import" the first time, "Reimport Resource" after edits. That writes the binary `.anm` next to it and an `.anm.meta` with a `{GUID}` name and one entry per platform naming the source. The menu wording comes from tools of 2019 to 2023; check it against the installed tools. A `.txo` works the same with "As Model"; for a custom skeleton tick "Export Skinning", reimport, and paste the generated entry into the skeleton XML. A new resource that does not show up needs a Workbench restart.

What the compile changes without a word:

- Workbench trims consecutive keys that are nearly the same, so an `.anm` can have fewer frames than authored and hold poses can collapse. No option to keep all frames is known; author keys with real differences. The plugin's exporter skips nearly equal keys too.
- Measured on an unjam clip, the compiled `.anm` differs from the plugin `.txa` by up to 0.017 per quaternion component, about 2 degrees, and 0.92 cm on fast frames, because of the dropped keys.
- Scale is dropped (not checked on `P:\`).
- Keep the `.txa` next to every `.anm`; Workbench can only edit an `.anm` again when its `.txa` is there, otherwise a third party extractor is needed just to touch events.
- The Workbench setting "Enable net API" belongs to Bohemia's Blender tools for another game; this plugin only writes files.

A route that skips Workbench: `.txa` to SEAnim, then `DayZATool --generate-anim X 100`. Quaternions pass through normalized, translations are multiplied by 100 (m to cm), and events become notes `Name|userString|userInt`. The result is exact to float32 and reads back (2.7e-5 on rotation, 3.2e-4 cm); it has not been played in game.

## Two conventions for what a key means

DayZATool extracts vanilla clips relative to the bind pose: `Spine3` with identity rotation and (0, 0, 0) translation, most bones without position keys. A clip compiled from the plugin is absolute (`Spine3` at (10.06, -0.67, 0) cm). So "SEAnim rotations are relative to the rest pose" holds for vanilla extracts only, and comparing raw values across the two gives large false differences, such as a constant 104 degree shoulder offset. Compare in Blender through `pose_bone.matrix_basis`, or through the bind pose.

## Looking at the player graph

The Workbench animation editor has a history of crashing on the player graph (an access violation on a new group, "Error opening workspace", "no TXA file found" when editing vanilla); allow time. How the event table line is handled to open a copy of the workspace differs between 1.29 and 1.30 (`anim-graph-format-1-30.md`, "Opening the player graph in the Workbench animation editor"). Once open, double click Master Control in Sheets, set the node as running by default, press Play, and fire the fire, chambering and reload commands from the debug controls.

Never ship a debinarized or edited vanilla workspace, model or clip; it breaks Bohemia's Workshop rules and gets a mod removed.
