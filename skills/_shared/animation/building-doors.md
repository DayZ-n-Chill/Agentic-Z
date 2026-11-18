# Doors on buildings and static props

How the `class Doors` system works on buildings and static props: doors, hatches and lids, the buttons or levers that drive them, the LOD layout in Object Builder and the 1.30 lock rules. Use it for a new animated door on a building, a button or lever wired to a door, a building door that takes a lock, a 1.29 door mod moving to 1.30, or a door that will not open or animate.

The model side in short (names in the vanilla house, who writes each part) is `doors.md`; its model rules are `dayz-object-builder` work. `AnimationSources`, `SetAnimationPhase` and doors on items are in `animation-sources.md` and `script-hooks.md`. Vehicle doors use a different system ("Vehicle doors use a different system" below).

Vanilla script and config facts are checked on `P:\` for DayZ 1.30. The three worked patterns come from third party mods, not vanilla: their names and values cannot be checked on `P:\`, and their models are not in this repo, so the files describe them in tables.

## Which file to open

| Question | File |
|---|---|
| Which classes and keys go in `model.cfg` and `config.cpp`, which ones vanilla proves, and what are the 1.30 open and lock rules? | `door-config-and-locks.md` |
| What does each LOD need, how do I check it in Object Builder, and which memory points does 1.30 read? | `door-lods.md` |
| Which of the three patterns fits, and what is each one's config? | `door-patterns.md` |
| How does vanilla 1.30 decide a door may open, and how does the one sided check work? | `door-open-and-lock-code.md` |
| How does a building door take a combination lock or code lock, and what breaks in a 1.29 door mod? | `building-door-locks.md` |

Read `door-config-and-locks.md` before editing `model.cfg` or `config.cpp`, `door-lods.md` before editing the `.p3d`, and `door-patterns.md` when choosing a pattern.

## Five names that must line up

A door action crosses five sets of names:

1. The visible and physical named selections in the `.p3d` LODs.
2. The bones in `CfgSkeletons`.
3. The rotation classes in the `CfgModels` `class Animations` block.
4. Each animation's `source`, normally the interaction selection in View Geometry.
5. A `class Doors` entry of a `HouseNoDestruct` child in `CfgVehicles`, whose `component` matches that source.

The moving `selection` and the interactive `source` can be different names. That is what lets a button or lever beside a door drive it.

## Building a door, in order

1. Model the object. Decide what moves, what follows another bone, where the action appears and where the sound comes from.
2. Lay out the LODs. Name the visible parts in the Resolution LOD; put only parts that take up space in Geometry; put the interaction and occlusion shapes in View Geometry; put the parts that need a penetration material in Fire Geometry; put the axes, the action and sound point and the interaction point in Memory.
3. Write `model.cfg`. Give the model a skeleton of its own, list the child and parent pairs, then add one rotation class per animated selection. Reuse one source when several parts move from one action.
4. Write `config.cpp`. Inherit from `HouseNoDestruct`, set `scope` and `model`, map the model's source through `class Doors`, then define `DamageSystem`.
5. Check the names. Compare spelling and case across every LOD, skeleton bone, animation `selection`, `source`, `axis`, Doors `component`, `soundPos` and the `componentNames` of each damage zone. Run `/dayz-p3d-audit` with `--model-cfg` and `--config`.
6. Test in game: where the action appears, the closed and open motion, child motion, the phase windows, collision, occlusion, penetration, sounds, the spawn state, and the server and client RPT.

Debug in the same order: config loads, entity spawns, action appears in the right place, animation plays, collision and occlusion, then sound and damage. Do not chase a later step until the earlier one works.

## Pick a worked pattern

| Need | Pattern | What defines it |
|---|---|---|
| A door with a moving handle | Simple door | Door and handle share source `door1`; the handle is a child of `door1` and finishes at phase 0.15. |
| A door driven by a static button | Door with button | Only `door1` is a bone; the source and the Doors component are `door1_open`, at the button. |
| A door with a moving handle and a lever | Handle and lever | Door, handle and lever share `door1_open`; the handle follows the door, the lever follows nothing. |
| A building door that takes a combination lock or a code lock (1.30) | Building lock slots | Keep the `class Doors` mapping; add `relatedInventorySlots[]` per door and the entity slots `Att_CombinationLock` and `Att_CodeLock`. |

## Checklist for a new door

- [ ] The `.p3d` base name, the `CfgModels` class, the model path and the vehicle class are chosen.
- [ ] The skeleton name is unique to this `.p3d`.
- [ ] Every animated selection is a skeleton bone.
- [ ] Every child and parent pair matches the intended hierarchy.
- [ ] The Resolution LOD names every visible part.
- [ ] The Geometry, View and Fire shapes are closed and convex.
- [ ] View Geometry holds the interaction selection (the source).
- [ ] Memory holds each rotation axis, the sound and action point, and the interaction point.
- [ ] Every animation has a checked type, selection, source, axis, memory flag, phase range and angles.
- [ ] `CfgPatches` `requiredAddons[]` includes `"DZ_Data"`.
- [ ] The object inherits from `HouseNoDestruct`.
- [ ] `class Doors` maps each source through `component`.
- [ ] For a door that takes a padlock or code lock (1.30): the entity's `attachments[]` list `Att_CombinationLock`, `Att_CodeLock` or both; the entity has a `class Construction`; the `class Doors` entry sets `relatedInventorySlots[]`; Memory has `att_combinationlock` and `att_codelock`, and the `interactPositionPoint` and `interactDirPoint` pair when used.
- [ ] For 1.30, a script override of the open rules targets `CanDoorBeOpened(notnull DoorManipulationParams params)`, not only the `int` wrapper.
- [ ] The door sound names exist in `P:\DZ\sounds\hpp\config.cpp`.
- [ ] `DamageSystem` has `GlobalHealth`, `GlobalArmor` and fitting `DamageZones`.
- [ ] The in game test covers action position, motion, sounds, the physical LODs, damage, spawn state and the RPT.

## Common traps

- A button can be the source without being animated or listed in the skeleton.
- A child handle must name the door bone as its parent, or it will not follow the door.
- Only sources need a Doors entry; selections that share one source do not each need one.
- A damage zone's `componentNames[]` can name the moving geometry (`door1`) even when the action source is `door1_open`.
- Order motion with phase windows: in the simple door the handle runs 0 to 0.15, then the door runs 0.15 to 1.
- `initOpened` is a spawn probability: the door spawns open when a random number is below it (0 never, 0.5 about half the time). `initPhase` is the starting phase, not a delay. Both are engine behaviour, not visible on `P:\`.
- Keep skeleton names unique. Duplicate skeleton names are reported to crash a server; not reproduced.
- The handle and lever pattern maps one source to two Doors entries; read the warning in `door-patterns.md` before reusing it. Its lever also collides with nothing (`door-lods.md`).
- Lock traps (a locked lock blocks Open, the lockpick on a padlocked door, `EBuildingLockType` is not the lock API) are in `building-door-locks.md`.

## Furniture inside vanilla houses

Vanilla house furniture is proxy geometry inside the building's model, not a placed object. `StaticObj_Furniture_fridge: HouseNoDestruct` exists with `scope=1` and no `Doors` subclass (`P:\DZ\structures\furniture\config.cpp:547` to `:551`), but the fridges inside houses are not instances of it. The fridge model is a proxy inside 25 house models under `P:\DZ\structures` (a byte search of the `.p3d` files for `kitchen\fridge\fridge`). The copy of the Chernarus `mapgrouppos.xml` on `P:\` lists only buildings and has no fridge entry (`P:\DZ\worlds\chernarusplus\ce\mapgrouppos.xml`); a count of 1,546 fridge placements reported from a server's own file is not checked. So neither a `modded` override of `StaticObj_Furniture_fridge` nor Community Framework's `CF_ObjectManager.HideMapObject` reaches them.

Before designing doors for furniture, search the extracted house models for the furniture's model path as a proxy and count its placements. In the search pattern write `.` where the path has `\`: in shell tools an escaped backslash collapses, and then even a search that should match finds nothing.

Replacing the model by path does reach them (measured in game on 1.29, not visible on `P:\`). A normal mod PBO whose `$PBOPREFIX$` is `DZ\structures\furniture\kitchen\fridge` and which ships its own binarized `fridge.p3d` with a new memory point replaced the vanilla model both for objects created by script and for the proxies inside houses: `MemoryPointExists` was true on server and client, and the new geometry showed through house roofs. Still open: whether the house's Geometry and View LODs carry the furniture proxy; vertical `RaycastRVProxy` sweeps over seven houses never hit a 16 m marker.

## When to stop and ask

Stop and ask the user when a source, interaction selection, axis, component, LOD membership or duplicate `class Doors` mapping cannot be confirmed from the real `.p3d` and config files. Do not invent a plausible name. Mark any claim you could not confirm as not checked, in plain words.

## Vehicle doors use a different system

Vehicle doors do not use the building `class Doors` entries.

- A car door that comes off is a `CarDoor` attachment (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:568`). `ActionCarDoorsOutside` casts its target to `CarDoor` and reads the car's animation source for the aimed selection (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:34` to `:43`), so the player aims at the door item's own View Geometry.
- A car's door state is `GetCarDoorsState` and the door's animation phase (`P:\scripts\4_world\entities\vehicles\carscript.c:2243`), driven by `model.cfg` animations and `AnimationSources`, not `class Doors`.
- A door that stays part of the shell needs the mod's own vehicle actions around a pair such as `SetDoorOpen` and `IsDoorOpen`, plus `model.cfg` animations and `AnimationSources`. Vanilla declares no such pair for vehicles, so the mod writes it.

Building `class Doors` on a vehicle produces no working action, even though both systems use the words `source`, `component` and `axis`. Vehicle doors are in `_shared/vehicles/attachments-and-crew.md`.

## DayZ 1.30 and simulation

What 1.30 changed for building doors, what breaks in a 1.29 door mod and the migration checklist are in `building-door-locks.md`; the open check itself is in `door-open-and-lock-code.md`.

`Entity` has the natives `DisableSimulation` and `GetIsSimulationDisabled` (`P:\scripts\3_game\entities\entity.c:3` to `:6`). The 1.30 changelog also adds a `disableSimulation` config key for houses and fixes inventory attachments on buildings created at load time. Vanilla sets `disableSimulation=1` on 30 Badlands buildings, the lockable houses among them (`P:\DZ\structures_takistan\Residential\config.cpp:21`); no script reads the key, so the engine handles it, and the attachment fix is not checked on `P:\`. A static house that must not tick can set `disableSimulation = 1`, as those houses do even though their doors open.

## On Linux

The Proton setup, tool matrix and pitfalls are in `skills/_shared/linux-proton.md`. For doors:

- Pack, sign and binarize with dayzmake 1.0.0 or later, a DayZ fork of armake2: `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Plain armake2 is no substitute: it targets Arma, and its signature hash leaves out `*.c` files. A textured cube binarized this way matched Bohemia's binarize output byte for byte; that is not an in game check of the model.
- `P:\` is a plain directory mapped by the Proton helper script, so a `P:\<Mod>\...` path is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton. Object Builder opens and displays a model; editing in it is not tested. The offline Python checks run natively.

## Building and testing the mod

To end with a mod that builds, loads and ships, use `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`.
