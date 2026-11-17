---
name: dayz-doors
description: "Reference for doors on DayZ buildings and static props: class Doors, the model.cfg skeleton and rotation animations behind it, a door opened by a button or lever, hatches and lids, the LOD contract in Object Builder, and the 1.30 lock rules (DoorManipulationParams, CanDoorBeOpened, relatedInventorySlots, combination lock and code lock on a building). Use when building an animated door on a building or prop, wiring a button or lever to a door, making a building door take a lock, moving a 1.29 door mod to 1.30, or diagnosing a door that will not open or animate. Not for vehicle doors (the vehicles pack) or general animation sources (the animation pack)."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ doors

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. The reference files are in `<skill-dir>\references\`.

It covers the `class Doors` subsystem on buildings and static props: doors, hatches, lids, and the buttons or levers that drive them. Start with the short pack file `_shared/models/doors.md` (names in the vanilla house, who writes each part); this skill holds the depth behind it.

It is not a general animation guide. For `AnimationSources`, `SetAnimationPhase` and doors on items, read `_shared/animation/animation-sources.md` and `_shared/animation/script-hooks.md`. Character and creature animation graphs, rider IK on vehicles, weapons, and RTM, ANM or TXA animation files also belong to the animation pack (`_shared/animation/`).

Vanilla script and config facts were checked on `P:\` (DayZ 1.30). The three worked patterns are third-party mod patterns, not vanilla: their names and values cannot be checked on `P:\`, and their models and configs are not files in this repo. The references describe them in tables.

## What to read

| Question | File |
|---|---|
| Which classes and keys go in `model.cfg` and `config.cpp`, which are proven, and what are the 1.30 open and lock rules? | `references/door-model-cfg-and-config.md` |
| What does each LOD need, how do I check it in Object Builder, and which memory points does 1.30 read? | `references/lods-and-object-builder.md` |
| Which of the three patterns fits, what does each one's config look like, and how do I add a lock to a building door? | `references/worked-examples.md` |

Read the contract file before editing `model.cfg` or `config.cpp`, the LOD file before editing the P3D, and the examples file when choosing a pattern.

## The core contract

A door action crosses five name domains:

1. The visible and physical named selections in the P3D's LODs.
2. The bones in `CfgSkeletons`.
3. The rotation classes in `CfgModels` > `class Animations`.
4. Each animation's `source`, normally the interaction selection in View Geometry.
5. A `class Doors` entry of a `HouseNoDestruct` child in `CfgVehicles`, whose `component` matches that source.

The moving `selection` and the interactive `source` may be different names. That is the key to a door driven by a button or lever beside it.

## Workflow

1. **Model the object.** Decide what moves, what follows another bone, where the action appears and where the sound comes from.
2. **Build the LOD contract.** Name the visible parts in the Resolution LOD; put only parts that take up space in Geometry; put the interaction and occlusion shapes in View Geometry; put the parts that need a penetration material in Fire Geometry; put the axes, the action and sound point and the interaction point in Memory.
3. **Write `model.cfg`.** Give the model a skeleton of its own, list the (child, parent) pairs, then add one rotation class per animated selection. Reuse one source when several parts move from one action.
4. **Write `config.cpp`.** Inherit from `HouseNoDestruct`, set `scope` and `model`, map the model's source through `class Doors`, then define `DamageSystem`.
5. **Check the names.** Compare exact spelling and case across every LOD, skeleton bone, animation `selection`, `source`, `axis`, Doors `component`, `soundPos` and the `componentNames` of each damage zone. Run `/dayz-p3d-audit` with `--model-cfg` and `--config`.
6. **Test in game.** Check the action's place, the closed and open motion, child motion, the phase windows, collision, occlusion, penetration, sounds, the spawn state, and the server and client RPT logs.

Debug in this order: config loads, entity spawns, action appears in the right place, animation plays, collision and occlusion, sound and damage. Do not debug a later layer before the earlier one is proven.

## Pick a worked pattern

| Need | Pattern | The mapping that defines it |
|---|---|---|
| A door with a moving handle | Simple Door | Door and handle share source **door1**; the handle is a child of **door1** and finishes at phase **0.15**. |
| A door driven by a static button | Door with Button | Only **door1** is a bone; the animation source and the Doors component are **door1_open**, at the button. |
| A door with a moving handle and a lever | Expert Mode | Door, handle and lever share **door1_open**; the handle follows the door, the lever follows nothing. |
| A building door that takes a combination lock or a code lock (1.30) | Building lock attachments | Keep the `class Doors` mapping above; add `relatedInventorySlots[]` per door, and the entity slots `Att_CombinationLock` and `Att_CodeLock`. |

## Checklist for a new door

- [ ] The P3D base name, the `CfgModels` class, the model path and the vehicle class are chosen.
- [ ] The skeleton name is unique to this P3D.
- [ ] Every animated selection is a skeleton bone.
- [ ] Every (child, parent) pair matches the intended transform hierarchy.
- [ ] The Resolution LOD names every visible component.
- [ ] The Geometry, View and Fire shapes are closed and convex.
- [ ] View Geometry holds the intended interaction selection (the source).
- [ ] Memory holds each rotation axis, the sound and action point, and the interaction point.
- [ ] Every animation has a checked type, selection, source, axis, memory flag, phase range and angles.
- [ ] `CfgPatches` `requiredAddons[]` includes `"DZ_Data"`.
- [ ] The object inherits from `HouseNoDestruct`.
- [ ] `class Doors` maps each intended source through `component`.
- [ ] (1.30, when the door should take a padlock or a code lock) the entity's `attachments[]` include `Att_CombinationLock`, `Att_CodeLock` or both; the matching `class Doors` entry sets `relatedInventorySlots[]`; Memory has the slot selections `att_combinationlock` and `att_codelock`, and the `interactPositionPoint` and `interactDirPoint` pair when used.
- [ ] (1.30) any script override of the open conditions targets `CanDoorBeOpened(notnull DoorManipulationParams params)`, not only the `int` wrapper.
- [ ] The door sound names exist in `P:\DZ\sounds\hpp\config.cpp`.
- [ ] `DamageSystem` has GlobalHealth, GlobalArmor and fitting DamageZones.
- [ ] Tests in game cover the action's position, motion, sounds, the physical LODs, damage, the spawn state and the RPT logs.

## Common traps

- A button can be the source without being animated or listed in the skeleton.
- A child handle must name the door bone as its parent, or it will not follow the door.
- Only sources need a Doors entry; animated selections that share one source do not each need one.
- `componentNames[]` of a damage zone can name the moving geometry (**door1**) even when the action source is **door1_open**.
- Use phase windows to order motion: the Simple Door handle runs **0..0.15**, then the door runs **0.15..1**.
- `initOpened` is a spawn probability: the door spawns open when a random number is below it (0 never, 0.5 about half the time). `initPhase` is the starting phase, not a delay. Both are engine behaviour, not checkable on `P:\`.
- Keep skeleton names unique. **?** Duplicate skeleton names may crash a server; this was not reproduced.
- The Expert Mode pattern maps one source to two Doors entries; read the warning in `references/worked-examples.md` before reusing it. Its lever also collides with nothing (`references/lods-and-object-builder.md`).
- A locked `DigitalCodeLock` or `CombinationLock` on a related slot makes `BuildingBase.CanDoorBeOpened` return false (`P:\scripts\4_world\entities\game\super\building.c:307` to `:333`). The lockpick is refused when an external lock is already on that door. Unlocking a combination lock is its own action, `ActionCombinationLockUnlock`, after the dials match.
- `EBuildingLockType` is still the lockpick and the ship container keys (`P:\scripts\3_game\enums\ebuildinglocktypes.c:7`). Combination and code locks are inventory attachments, not extra enum values. Do not invent `COMBINATION_LOCK = 2` or `CODE_LOCK = 4`.
- **Vanilla house furniture is proxy geometry inside the building's model, not a placed object.** `StaticObj_Furniture_fridge: HouseNoDestruct` exists with `scope=1` and no `Doors` subclass (`P:\DZ\structures\furniture\config.cpp:547` to `:551`), but the fridges inside houses are not instances of it. The fridge model path is a proxy inside about 25 house models of `DZ\structures`, and `mapgrouppos.xml` of the `dayzOffline.chernarusplus` mission has at least 1,546 `kitchen\fridge\fridge` placements (a lower bound; neither number was recounted on `P:\`). So neither a `modded` override of `StaticObj_Furniture_fridge` nor Community Framework's `CF_ObjectManager.HideMapObject` reaches them. Before designing doors for furniture, search the extracted house models for the furniture's model path as a proxy and count the placements in the world. In the search pattern write `.` where the path has `\`: in shell tools an escaped backslash collapses, and then even a control search that should match finds nothing.
- **A measured way to make house furniture interactive: replace the model by path.** Measured in game on DayZDiag 1.29.163709 (2026-09-24), not checkable on `P:\`: a normal mod PBO whose `$PBOPREFIX$` is `DZ\structures\furniture\kitchen\fridge` and which ships its own `fridge.p3d` (binarized, with a new memory point) replaced the vanilla model both for instances created by script and for the proxies inside houses. `MemoryPointExists` was true on server and client for the replaced class, the control class kept the vanilla geometry, and the replacement geometry was visible sticking out of house roofs. Open question: whether the house's Geometry and View LODs carry the furniture proxy; vertical `RaycastRVProxy` sweeps over 7 houses never hit a 16 m marker.

## Stop and ask

Stop and ask the user when a source, interaction selection, axis, component, LOD membership or duplicate `class Doors` mapping cannot be proven from the real P3D and config files. Do not invent a plausible name. Mark any unresolved technical claim with a leading **?**.

## Vehicle doors are out of scope

Vehicle doors do not use the building `class Doors` contract.

- A car door that can be taken off is a `CarDoor` attachment (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:568`). `ActionCarDoorsOutside` casts its target object to `CarDoor` and reads the car's animation source for the aimed selection (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:34` to `:43`), so the door item's own View Geometry is what the player aims at.
- Door state on a car is `GetCarDoorsState` and the door's animation phase (`P:\scripts\4_world\entities\vehicles\carscript.c:2243`), driven by `model.cfg` animations and `AnimationSources`, not by `class Doors`.
- A door that stays part of the vehicle's shell (it cannot be taken off) needs the mod's own vehicle actions around a pair of methods such as `SetDoorOpen` and `IsDoorOpen`, plus `model.cfg` animations and `AnimationSources`. Vanilla script on `P:\` declares no such pair for vehicles, so the mod writes it.

Applying building `class Doors` to a vehicle does not produce a working action, even though both mechanisms use the words `source`, `component` and `axis`. Vehicle doors are in `_shared/vehicles/attachments-and-crew.md`.

## DayZ 1.30

### What changed

- **Open API.** `DoorManipulationParams` carries `m_DoorIndex`, `m_CheckIfLocked` and `m_Caller` (`P:\scripts\3_game\entities\building.c:5` to `:10`). `Building.CanDoorBeOpened(notnull DoorManipulationParams params)` is the real check (`P:\scripts\3_game\entities\building.c:141`); the old `CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` is a wrapper that does not set `m_Caller` (`P:\scripts\3_game\entities\building.c:160`). Vanilla `ActionOpenDoors` fills the params object and also calls `DoorsDirectionalCheck` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:36` to `:52`).
- **Extra info per door.** `AdditionalDoorInfo` is read from each `class Doors` child: `relatedInventorySlots[]`, `lockCompatibilityBitMask`, `interactPositionPoint`, `interactDirPoint`, `doorConstructionPart`, `doorConstructionPhysicsSource`. When the bit mask is missing the default is `1 << EBuildingLockType.LOCKPICK` (`P:\scripts\3_game\entities\additionaldoorsinfo.c:21` to `:45`).
- **Attachment locks.** `BuildingBase` defines `Att_CombinationLock` and `Att_CodeLock` (`P:\scripts\4_world\entities\game\super\building.c:10` to `:11`). A locked lock on a related slot blocks `CanDoorBeOpened`, a second lock on the twin slot is refused, and a locked lock cannot be taken off (`CanReceiveAttachment`, `P:\scripts\4_world\entities\game\super\building.c:192`; `CanReleaseAttachment`, `:267`).
- **New item `DigitalCodeLock`.** Script class in `P:\scripts\4_world\entities\itembase\codelock.c:1`, logic in `CodeLockComponent`, menu layout `gui/layouts/day_z_digital_lock.layout`. It needs a `Battery9V` in slot `BatteryD`. The PIN is 4 to 6 digits, with two brute force stages set through `cfggameplay.json`.
- **`CombinationLock` has two sides and an unlock action.** The dials no longer drop the lock by themselves; `ActionCombinationLockUnlock` runs after the combination matches. The save stream gains `m_CombinationInside` at version 143 (`P:\scripts\4_world\entities\itembase\combinationlock.c:169`).
- **Bunker doors.** `Bunker.CanDoorBeOpened` uses `MemPointDirectionalCheck` on `<door>_action` and `<door>_inside`. The main door closes itself after `DOOR_AUTOCLOSE_TIME`, 12 s, and locks its `DigitalCodeLock_Bunker` again (`P:\scripts\4_world\entities\building\bunker.c:3`, `:47` to `:62`).
- **Doors of houses that can be rebuilt.** `Rebuilding` drives `doorConstructionPhysicsSource` when a door starts to open or close (`OnConstructionDoorOpenStart`, `P:\scripts\4_world\classes\rebuilding\rebuilding.c:439`).
- **Switching simulation off on a house.** `Entity` has the natives `DisableSimulation` and `GetIsSimulationDisabled` (`P:\scripts\3_game\entities\entity.c:3` to `:6`). 1.30 also adds a `disableSimulation` config key for houses and fixes inventory attachments on buildings created at load time; neither was checked on `P:\`.

### What breaks for a 1.29 door mod

| Break | Severity | Migration |
|---|---|---|
| An override of `CanDoorBeOpened(int, bool)` is skipped by vanilla Open | High | Override `CanDoorBeOpened(notnull DoorManipulationParams params)` and call `super`. The `int` wrapper still exists, but `ActionOpenDoors` no longer calls it. Vanilla's own `Land_WarheadStorage_Main` still overrides the `int` form on `P:\` (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_main.c:352`). |
| The door opens from the wrong side, or Open never appears | Medium | Add the Memory points named in `interactPositionPoint` and `interactDirPoint`, or leave both keys out: empty names make `MemPointDirectionalCheck` return true (`P:\scripts\4_world\static\miscgameplayfunctions.c:942` to `:967`). |
| The lockpick is still offered on a padlocked door | Medium | Set `relatedInventorySlots[]` on that Doors entry so `ActionLockDoors` and `ActionUnlockDoors` see the external lock through `IsExternalLockType()` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionlockdoors.c:40` to `:54`). |
| A custom combination lock that unlocked itself on the last dial | Medium | Run `ActionCombinationLockUnlock` after the dials match. Read `m_CombinationInside` when `version >= 143`. |
| A code lock or combination lock never attaches to a custom building | High | Declare the slots on the entity, the proxy selections `att_codelock` and `att_combinationlock`, and `relatedInventorySlots[]` on the door. `ActionAttachToConstruction` takes the slot from `AdditionalDoorInfo` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattachtoconstruction.c:151` to `:174`). |

### 1.30 migration checklist (building doors)

- [ ] Search the mod for `CanDoorBeOpened(` and move building overrides to the `DoorManipulationParams` signature.
- [ ] When the door should take a lock, add `attachments[]`, `relatedInventorySlots[]` and the Memory slot selections.
- [ ] Do not treat `EBuildingLockType` as the combination or code lock API; those are attachments.
- [ ] Combination lock mods: add `ActionCombinationLockUnlock` and the version 143 read of `m_CombinationInside`.
- [ ] Doors that can be rebuilt: set `doorConstructionPart` and `doorConstructionPhysicsSource` on the Doors entry.
- [ ] Optional: `disableSimulation = 1` on static house classes that must not tick (not checked on `P:\`: no vanilla config there sets it).

## On Linux

Everything above is the Windows workflow. The Proton setup, the measured tool matrix and the pitfalls are in the Linux notes of the shared pack (`_shared/linux-proton.md`). For this skill:

- Packing, signing and binarizing use dayzmake 1.0.0 or later, a DayZ fork of armake2: `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Plain armake2 is not a substitute: it is built for Arma, and its file hash for signatures leaves out `*.c` files. A textured cube binarized this way had the same bytes as the output of Bohemia's binarize run from a `P:` root (compared on 2026-11-03); that is not an in-game check of the model.
- `P:\` is a plain directory mapped by the Proton helper script; a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton. Object Builder opened and displayed a model; editing in it was not exercised. The offline Python checks run natively.

## Building and testing the mod

When the work has to end in a mod that builds, loads and ships, use this repo's own chain: `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`.

## References

- `references/door-model-cfg-and-config.md`
- `references/lods-and-object-builder.md`
- `references/worked-examples.md`
