# Animated doors

What a door needs inside the model, how the names line up with `model.cfg`, `config.cpp`, the player's door actions and script, and who writes each part.

This file is the short version. The `dayz-doors` skill (`skills/dayz-doors/SKILL.md`) holds the depth: every `model.cfg` and `config.cpp` key, the LOD contract, three worked patterns and the 1.30 lock rules.

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

## The part that moves and the part you aim at can differ

Two name chains meet in a door:

- **What moves:** a named selection in the model, a skeleton bone of the same name, and the `selection` of the `model.cfg` animation.
- **What the player uses:** a named selection in the View Geometry LOD, the animation's `source`, and the `class Doors` entry.

In a plain door both chains use one name. They split when a door is opened from a button or a lever beside it: the animation keeps `selection = "door1"` but takes its `source` from the controller's View Geometry selection, for example `door1_open`, and the `class Doors` entry names that selection in `component`. A static button needs no bone and no animation; a lever that moves gets its own bone and animation on the same source. Several animations can share one source (door, handle and lever from one action), and a handle that should ride on the door names the door bone as its skeleton parent.

In vanilla the `class Doors` subclass name, its `component` and the animation source are always one name: all 1,373 `class Doors` entries in the configs under `P:\DZ` have a class name equal to their `component` apart from letter case (`class Doors5` with `component="Doors5"`, `P:\DZ\structures\residential\config.cpp:7385`). Vanilla therefore cannot show whether the engine ties the animation source to the subclass name or to `component`. Keep all three the same in a mod door.

Worked patterns for a door with a handle, a door with a button, and a door with a handle and a lever, with the pitfalls of each, are in `skills/dayz-doors/references/worked-examples.md`. They are third-party mod patterns, not vanilla.

## Model rules for a door

1. One bone per door leaf, named the same in every visual LOD. Put the same selection in the Geometry, Fire Geometry and View Geometry LODs on the parts that should move with the door, so the collision swings open too (naming checklist item 1 in `_shared/animation/model-cfg-animations.md`).
2. Name the axis `<bone>_axis`, with exactly two points on the hinge line. `/dayz-p3d-audit`, run with `--model-cfg`, reports CRITICAL when the selection or the axis an animation names is missing, or when the axis does not hold exactly two points (`check_animations` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`).
3. Build the door (or the pair of leaves) as its own closed convex part in the View Geometry LOD, keep its ComponentNN name, and add a second named selection named after the door (for example `Doors5`) that holds that part. The door action finds the door from the View Geometry component the player aims at (`GetDoorIndex`, `P:\scripts\3_game\entities\building.c:27` to `:28`).
4. Add one action point per door in the Memory LOD, named `<door>_action`, at the handle.
5. Keep door collision in the Geometry LOD thick enough to stop a player (`lods.md`, "Geometry").

## User actions

- Every player has `ActionOpenDoors`, `ActionCloseDoors` and `ActionLockedDoors` (`P:\scripts\4_world\entities\manbase\playerbase.c:1697` to `:1699`). A lockpick adds `ActionLockDoors` and `ActionUnlockDoors` (`P:\scripts\4_world\entities\itembase\gear\tools\lockpick.c:18`, `:19`). A door can be lockpicked when its `lockCompatibilityBitMask` includes `1 << EBuildingLockType.LOCKPICK`, which is the default when the key is missing from its `class Doors` entry (`P:\scripts\3_game\entities\additionaldoorsinfo.c:29` to `:32`); both actions AND the lockpick's `GetKeyCompatibilityType` with the door's `GetLockCompatibilityType` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionunlockdoors.c:55`, `actionlockdoors.c:56`).
- `ActionOpenDoors` works only on buildings: it checks `IsBuilding` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:33`), which is true for `Building` (`P:\scripts\3_game\entities\building.c:267`) and false for other objects (`P:\scripts\3_game\entities\object.c:642`). A mod building inherits a house class such as `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`).
- On the server it turns the aimed component into a door index and calls `OpenDoor` (`actionopendoors.c:67` to `:73`). A building with matching model names and `class Doors` needs no mod script.
- A door that opens from one side only reads two memory point names from its `class Doors` entry, `interactPositionPoint` and `interactDirPoint` (`additionaldoorsinfo.c:35`, `:38`), checked by `DoorsDirectionalCheck` (`P:\scripts\4_world\entities\game\super\building.c:336`). No vanilla `config.cpp` under `P:\DZ\` sets them. Add both points to the Memory LOD only when the user wants this.
- In 1.30 the open check takes a parameter object. `ActionOpenDoors` builds a `DoorManipulationParams` (`m_DoorIndex`, `m_CheckIfLocked`, `m_Caller`; `P:\scripts\3_game\entities\building.c:5` to `:10`) and calls `CanDoorBeOpened(notnull DoorManipulationParams params)` (`P:\scripts\3_game\entities\building.c:141`). The older `CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` is only a wrapper around it (`P:\scripts\3_game\entities\building.c:160`), and the open action does not call it. A mod that changes when a door may open overrides the `DoorManipulationParams` form and calls `super`; an override of the `int` form alone is never reached by the vanilla action.
- With empty or missing point names the one side check passes: `MemPointDirectionalCheck` returns true (`P:\scripts\4_world\static\miscgameplayfunctions.c:942` to `:967`).

## Building doors that take a lock (1.30)

Since 1.30 a building is a `BuildingBase` with two lock slots, `Att_CombinationLock` and `Att_CodeLock` (`P:\scripts\4_world\entities\game\super\building.c:10` to `:11`), and each `class Doors` entry can carry extra keys that script reads into an `AdditionalDoorInfo` (`Init`, `P:\scripts\3_game\entities\additionaldoorsinfo.c:21` to `:45`):

| Key in the `class Doors` entry | What it does |
|---|---|
| `relatedInventorySlots[]` | The lock slots that belong to this door. Open, the lockpick and the attach action all read it. |
| `lockCompatibilityBitMask` | Which keys fit. When it is missing, the lockpick fits (`1 << EBuildingLockType.LOCKPICK`). |
| `interactPositionPoint`, `interactDirPoint` | Memory points for a door that works from one side (above). |
| `doorConstructionPart`, `doorConstructionPhysicsSource` | For a door of a house that can be rebuilt: its construction part, and the `AnimationSources` name that switches the door's physics. |

What follows for the model and the config:

- The entity's `attachments[]` lists the slots, as the vanilla fence does (`P:\DZ\gear\camping\config.cpp:4362` to `:4368`), and the door's entry lists them again in `relatedInventorySlots[]`.
- The Memory LOD needs the slot selections `att_combinationlock` and `att_codelock`, the `selection` values of the slot classes (`Slot_Att_CombinationLock`, `P:\scripts\config.cpp:2316` to `:2321`; `Slot_Att_CodeLock`, `P:\scripts\config.cpp:2768` to `:2773`).
- A locked `DigitalCodeLock` or `CombinationLock` in a related slot stops the door from opening (`CanDoorBeOpened`, `P:\scripts\4_world\entities\game\super\building.c:307` to `:333`). A second lock on the same door is refused and a locked lock cannot be taken off (`CanReceiveAttachment`, `P:\scripts\4_world\entities\game\super\building.c:192`; `CanReleaseAttachment`, `:267`).
- Combination and code locks are inventory attachments. `EBuildingLockType` still only has `NONE`, `LOCKPICK` and the ship container keys (`P:\scripts\3_game\enums\ebuildinglocktypes.c:7` to `:16`).

No `config.cpp` under `P:\DZ\` uses `relatedInventorySlots[]`, so there is no vanilla door block to copy; the full reasoning, the lock items and the bunker door are in `skills/dayz-doors/references/worked-examples.md`.

## Spawn state

- `initPhase` is the animation phase the door has when it spawns (0 is closed), not a delay.
- `initOpened` is the chance that the door spawns open: 0 never, 0.5 about half the time. The house above uses 0.7 (`initOpened=0.69999999`, `P:\DZ\structures\residential\config.cpp:7392`).

Both meanings are Bohemia format knowledge; vanilla script does not show them.

## Furniture inside houses

A fridge or wardrobe inside a vanilla house is a proxy inside the house's model, not a placed object of its own class. `StaticObj_Furniture_fridge` exists (`P:\DZ\structures\furniture\config.cpp:547` to `:551`), but changing that class does not reach the fridges in houses. Check for this before promising doors on vanilla furniture; what was measured is in `skills/dayz-doors/SKILL.md`, "Common traps".

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
