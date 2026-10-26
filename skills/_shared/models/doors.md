# Animated doors

What a door needs inside the model, how the names line up with `model.cfg`, `config.cpp`, the player's door actions and script, and who writes each part.

## Who writes what

| Part | Owner | Reference |
|---|---|---|
| Door selections in every LOD, View Geometry components, axis and action memory points, the skeleton class | `dayz-object-builder` | this file |
| `skeletonBones[]` entries for the door bones and the `class Animations` block | `dayz-animation-specialist` | `_shared/animation/model-cfg-animations.md` |
| `class Doors` for a building, or `class AnimationSources` for an item | `dayz-config-specialist`, from the names the animation specialist hands over | `_shared/animation/animation-sources.md` |
| Script, only when the door must behave differently from vanilla, or for a door on an item | `dayz-script-specialist` | `_shared/animation/script-hooks.md` |

Send the art lead the door names below once, so all four workers use the same spelling.

## The vanilla house door, name by name

`P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d` with its class `Land_HouseBlock_3F_Corner1` (`P:\DZ\structures\residential\config.cpp:7341`). The model names are stored in the `.p3d`.

| Name | Where it lives | What it does |
|---|---|---|
| `doors5` | Named selection (bone) in the visual LODs | The part that turns |
| `doors5_axis` | Two point selection in the Memory LOD | The hinge line |
| `doors5_action` | Point in the Memory LOD | Where the door sound plays; `soundPos` in `class Doors5` (`config.cpp:7385` to `:7389`) |
| `Doors5` | Named selection in the View Geometry LOD that covers the door's own convex ComponentNN part; `component` in `class Doors5` | What the player aims at to get the open prompt |
| `Doors5` animation, source `doors5` | `model.cfg` `class Animations` (written by the animation specialist) | Turns the bone; the source matches the `class Doors5` name |
| `Skeleton9Doors` | `model.cfg` skeleton | Holds the door bones |

A double door has one bone and one axis per leaf but one source, one component and one action point. In the same house, bones `doors1` and `doors2` with axes `doors1_axis` and `doors2_axis` both use source `doorstwin1`, which is `class DoorsTwin1` with `component="DoorsTwin1"` and `soundPos="doorsTwin1_action"` (`config.cpp:7359` to `:7363`).

## Model rules for a door

1. One bone per door leaf, named the same in every visual LOD. Put the same selection in the Geometry, Fire Geometry and View Geometry LODs on the parts that should move with the door, so the collision swings open too (naming checklist item 1 in `_shared/animation/model-cfg-animations.md`).
2. Name the axis `<bone>_axis`, with exactly two points on the hinge line. `/dayz-p3d-audit` reports CRITICAL when a `<name>_axis` has no `<name>` selection in the visual LOD (`check_visual_lod` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`).
3. Build the door (or the pair of leaves) as its own closed convex part in the View Geometry LOD, keep its ComponentNN name, and add a second named selection named after the door (for example `Doors5`) that holds that part. The door action finds the door from the View Geometry component the player aims at (`GetDoorIndex`, `P:\scripts\3_game\entities\building.c:27` to `:28`).
4. Add one action point per door in the Memory LOD, named `<door>_action`, at the handle.
5. Keep door collision in the Geometry LOD thick enough to stop a player (`lods.md`, "Geometry").

## User actions

- Every player has `ActionOpenDoors`, `ActionCloseDoors` and `ActionLockedDoors` (`P:\scripts\4_world\entities\manbase\playerbase.c:1697` to `:1699`). A lockpick adds `ActionLockDoors` and `ActionUnlockDoors` (`P:\scripts\4_world\entities\itembase\gear\tools\lockpick.c:18`, `:19`). A door can be lockpicked unless its `class Doors` entry sets `lockCompatibilityBitMask` (`P:\scripts\3_game\entities\additionaldoorsinfo.c:29` to `:32`).
- `ActionOpenDoors` works only on buildings: it checks `IsBuilding` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:33`), which is true for `Building` (`P:\scripts\3_game\entities\building.c:267`) and false for other objects (`P:\scripts\3_game\entities\object.c:642`). A mod building inherits a house class such as `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`).
- On the server it turns the aimed component into a door index and calls `OpenDoor` (`actionopendoors.c:67` to `:73`). A building with matching model names and `class Doors` needs no mod script.
- A door that opens from one side only reads two memory point names from its `class Doors` entry, `interactPositionPoint` and `interactDirPoint` (`additionaldoorsinfo.c:35`, `:38`), checked by `DoorsDirectionalCheck` (`P:\scripts\4_world\entities\game\super\building.c:336`). No vanilla `config.cpp` under `P:\DZ\` sets them. Add both points to the Memory LOD only when the user wants this.

## The script side

Buildings: the door state calls (`IsDoorOpen`, `LockDoor` and the rest) and the hooks such as `OnDoorOpenStart` are on `Building` (`P:\scripts\3_game\entities\building.c:34` to `:127`). Script is only needed to change behavior, for example a keypad that locks a door; that is `dayz-script-specialist` work.

Doors on an item or a placed object that is not a building, such as the base building gate or a crate lid: `class Doors` and `ActionOpenDoors` don't apply. The item declares `AnimationSources`, script calls `SetAnimationPhase`, and the item registers its own open action. Copy the barrel or fence pattern in `_shared/animation/script-hooks.md`. The model rules above still apply. The vanilla fence names its gate axis `rotate_axis` for bone `wall_gate` (names stored in `P:\DZ\gear\camping\fence.p3d`); in a mod model use `wall_gate_axis` instead, so the audit can match the axis to its bone.

## Object Builder steps to give the user

For each door, in order:

1. Visual LODs: select the door leaf faces and points, create the named selection `<bone>` in each visual LOD.
2. Geometry, Fire Geometry and View Geometry: add the moving collision part to `<bone>`. In View Geometry, also do this: build the door (or the pair of leaves) as its own closed convex part in the View Geometry LOD, keep its ComponentNN name, and add a second named selection named after the door (for example `Doors5`) that holds that part.
3. Memory LOD: add two points on the hinge as `<bone>_axis` and one point at the handle as `<door>_action`.
4. Save the MLOD file, then run `/dayz-p3d-audit` on it with `--model-cfg` and `--config`.
5. Send the art lead the bone, axis, component, action point and source names for the animation and config specialists.
