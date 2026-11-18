# Building selections and points

The names a building or ladder model carries beyond the general ones in `selections.md`: door leaves and their points, the two ladder schemes, the points of the Paths LOD, loot and rain sound points, and the `liquid_source` selection of a well.

Every name below was read from the plain text a binarized vanilla model stores, in the models named. What a name is for is stated only where a vanilla script or config shows it; the rest is marked as format knowledge that no vanilla file shows, or as unknown. Use Object Builder to author these; an ODOL to MLOD converter can lose which points a selection holds while keeping its name (`selections.md`, "Membership lost by tools").

## Doors

| Name | LOD | What it is | Vanilla example |
|---|---|---|---|
| `doorsN` | every LOD the door exists in: visual, Geometry, View Geometry, Fire Geometry | The door leaf: the bone that moves | `doors1`, `doors2` in `P:\DZ\structures\industrial\garages\garage_small.p3d`, where `doors1` is stored 10 times in a model of 12 LODs |
| `doorsN_axis` | Memory | The two point hinge line of that leaf | `doors1_axis`, `doors2_axis` in `garage_small.p3d` |
| `doorsN_action` | Memory | The point named by `soundPos` in the door's config class | `doors1_action` to `doors6_action` in `P:\DZ\structures\industrial\farms\barn_wood1.p3d` |
| `doorstwinN` | View Geometry, where the config `component` finds it, and the other LODs of the door | One selection covering both leaves of a double door | `doorstwin1` in `garage_small.p3d` (stored 6 times) |
| `doorstwinN_action` or `twinN_action` | Memory | The sound point of the double door | `doorstwin1_action` in `P:\DZ\structures\industrial\farms\farm_cowsheda.p3d`; `twin1_action` in `garage_small.p3d` |

What the vanilla models show:

- **Numbering starts at 1** and the skeleton is named for the door count: `Skeleton2Doors` in `garage_small.p3d`, `Skeleton6Doors` in `barn_wood1.p3d`, `Skeleton7Doors` in `farm_cowsheda.p3d`.
- **A double door is two leaves and one door.** In `farm_cowsheda.p3d` the leaves `doors1` and `doors2` each have their own `doors1_axis` and `doors2_axis`, but there is no `doors1_action`: the pair is opened as `doorstwin1`, with one `doorstwin1_action`. The config side of the pairing is in `_shared/animation/doors.md`.
- **Not every door has an `_axis` point.** `barn_wood1.p3d` stores `doors1_axis`, `doors5_axis` and `doors6_axis` only, while all six doors have a `doorsN_action`. Do not assume one axis per door when reading a vanilla model.
- **The names are stored in lower case**, while the animation classes inside the model keep their capitals (`Doors1`).

Two more things are format knowledge that no vanilla file read here confirms: a `bounding` selection for the opened volume, and a standard door size of 120 by 220 cm. Treat both as hints.

The rest of the door, including the config class and who writes it, is in `_shared/animation/doors.md` and `_shared/animation/animation-sources.md`.

## Ladders

Vanilla uses two schemes, depending on whether the ladder is its own model or part of a building. Script reaches ladders by index, not by name: `GetLaddersCount`, `GetLadderPosTop` and `GetLadderPosBottom` on `Building` (`P:\scripts\3_game\entities\building.c:23` to `:25`).

| Kind | Names | Vanilla example |
|---|---|---|
| Climbable ladder prop | Memory points `start1` and `end1`, or `start` and `end`; Geometry with `component01` and `class` = `house`; a Roadway LOD | `start1`, `end1` in `P:\DZ\structures\residential\misc\ladder.p3d` and `ladder_half.p3d`; `start`, `end` in `P:\DZ\structures\residential\offices\proxy\ladderlong.p3d` |
| Ladder built into a building | A selection `ladderN` (in View Geometry, read from the model converted back to MLOD), and the points `ladderN_bottom_front`, `ladderN_top_front`, `ladderN_dir`, `ladderN_con`, `ladderN_con_dir` | `ladder1` and its five points in `P:\DZ\structures\industrial\harbour\lighthouse.p3d` and `P:\DZ\structures\military\improvised\mil_fortified_nest_watchtower.p3d` |
| The same, with a side entry on a middle floor | Adds `ladderN_middle_right` and `ladderN_middle_right_align` | `P:\DZ\structures\industrial\cementworks\cementworks_silobig1a.p3d` |
| Ladder piece used as a proxy inside a building | A selection named after the piece (`long`, `top`); a Geometry LOD with `autocenter` = `0` and no components | `P:\DZ\structures\Proxy_BuildingParts\ladders\ladder_long_proxy.p3d`, `ladder_top_proxy.p3d` |

- `N` starts at 1. `_bottom_front` is the entry at the foot and `_top_front` the exit at the top; that reading and the meaning of `ladderN_dir` are taken from the names, not from a script, and are not checked on `P:\`. The `_con` and `_con_dir` points are read by script (below).

How script enters a built in ladder (`ActionEnterLadder`, `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionenterladder.c`):

1. The target must be a `Building` (`:25` to `:27`), so a ladder on an item or a vehicle never offers the action.
2. The aimed component must belong to a selection whose name starts with `ladder` and has no `_` after it, such as `ladder1` (`:41` to `:49`). That name also gives the ladder's index to the engine (`HumanCommandLadder.DebugGetLadderIndex`, `:136`).
3. The Memory LOD must hold `ladderN_con`, and the player must stand within `UAMaxDistances.LADDERS`, 1.3 m, of one of its points (`:54` and `:66` to `:72`; `P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:117`).
4. The point of `ladderN_con_dir` nearest that entry point sets the facing: the action shows only when the player stands within 90 degrees of the line from the entry point to it (`:62` and `:84` to `:108`).
5. A `laddertype` named property on the Geometry LOD picks the climbing sound; the default is `metal`, and only `wood` changes it (`:137` to `:149`; `P:\scripts\4_world\entities\dayzplayerimplement.c:3643`). The deer stands store `laddertype` = `wood` (`P:\DZ\structures\residential\misc\misc_deerstand1.p3d`).

Without `ladderN_con` the ladder shows no enter action and logs no error; without `_con_dir` the facing point stays at its default `0 0 0`, the world origin, so whether the action shows depends on where the building stands on the map.
- All six models above that carry climb points also carry a Roadway LOD (`3.0e+15`). The furniture ladder `P:\DZ\structures\furniture\various\ladder_a_wood.p3d` has neither: only visual LODs, Geometry and View Geometry.

## Paths LOD

The names stored by the two vanilla buildings read here that have a Paths LOD (`4.0e+15`):

| Name | Vanilla example |
|---|---|
| `pos1`, `pos2`, ... | `garage_small.p3d` (two); `cementworks_silobig1a.p3d` (`pos1` to `pos8`) |
| `in1`, `in2`, ... | `garage_small.p3d` (two); `cementworks_silobig1a.p3d` (`in1`) |
| `actionbegin1`, `actionend1` | `garage_small.p3d` |

Format knowledge, not shown by a vanilla script: `posN` are the points AI can stand at inside the building, `inN` are its entry points, and `actionbeginN` with `actionendN` bound an AI action. Copy the layout from the closest vanilla building.

## Loot and rain sound points

Names that no script under `P:\scripts\3_game\` or `P:\scripts\4_world\` reads (searched for `lootcenter`, `lootaround` and `sound_rain`), so what uses them is not visible from script. By their names they are loot spawn positions and ambient sound positions; that is not checked on `P:\`.

| Name | Vanilla example |
|---|---|
| `lootcenter`, `lootaround` | `garage_small.p3d` |
| `lootground`, `loot` | `barn_wood1.p3d`, `farm_cowsheda.p3d` |
| Room names such as `lootfloor1stroom`, `lootroof`, `lootall` | `cementworks_silobig1a.p3d` |
| `sound_rainobjectinner<N><material>_<index>` | `sound_rainobjectinner3metal2_1` in `garage_small.p3d`; `sound_rainobjectinner4tile_1` to `_5` in `farm_cowsheda.p3d` |

The loot names differ from building to building, so they are labels for whoever maps the building's loot, not fixed keywords. The rain sound names end in a surface (`metal2`, `tile`, `metal1`) and a running index. A mod building that needs either should copy the names of a vanilla building of the same kind and material.

## `liquid_source` on a well

The wash, drink and fill actions on a well ask for the View Geometry components that belong to a selection named `liquid_source` (`LIQUID_SOURCE_SELECTION`, `P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:180`).

The selection narrows where the action works; it is not required:

- `CCTLiquid` treats any component of a well as valid when the model has no such selection, and checks the aimed component only when it has one (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:89` to `:94`, where an empty `componentIndices` sets `isValidInteract = true`).
- Three of the 10,626 vanilla models store the name, all on Takistan: the brick well `P:\DZ\structures_takistan\Props\misc\waterwell_brick.p3d` and the two cistern truck wrecks under `P:\DZ\structures_takistan\Wrecks\wheeled\`, whose script classes extend `Well` (`P:\scripts\4_world\entities\building\wrecks\wreck_truck01_aban1_cistern.c:1`). The other vanilla wells, such as `P:\DZ\structures\residential\misc\misc_well_pump_blue.p3d`, run on the fallback.
- The check runs only on an object whose `GetWaterSourceObjectType()` is `WELL` (`IsWell`, `P:\scripts\3_game\entities\object.c:664`), which a script class extending `Well` gives (`P:\scripts\4_world\entities\building\well.c:8` to `:11`).

Add `liquid_source` to the View Geometry components of the spout when only that part of a custom well should take the actions. A memory point of that name does nothing.

## How the names were read

Each model's file was searched for the text of its selection and point names, and the LOD list was read from the file header (`lods.md`, "Reading the LOD list of a vanilla model"). This gives names, not membership: it shows that `doors1_axis` exists, not which two points it holds. Nine of the models were also converted to MLOD and read with py3d, which gave the same names.
