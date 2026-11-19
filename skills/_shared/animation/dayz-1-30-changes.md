# What DayZ 1.30 changed for animation

Which 1.30 changes touch animation work, what breaks in work made for 1.29, and what to migrate. File and script lines are checked on `P:\`; lines taken from Bohemia's 1.30 changelog say so, since the changelog is not on `P:\`.

## Graph, template and instance files have a new text format

- Sub-graphs are `.agf` files. The master graph stays `.agr` (now an `AnimSrcGraph`) and lists its sub-graphs in `GraphFilesResourceNames` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`). 1.29 already split the player graph into eight sub-graphs; they were `.agr` files in the older `$AnimGraph 7` format. No vanilla 1.30 master uses an `include` directive.
- Nodes are written as named fields in Enfusion config syntax, such as `AnimSrcNodeBlendT` and `AnimSrcNodeProcTransform`, under a `ControlTemplate AnimSrcGCT` that holds variables and commands.
- Instances are `AnimSetInstanceSource` (with `Template`, `ParentTemplates` and `Lines`) and templates are `AnimSetTemplateSource` with a named `AnimSetTemplateSource_AnimationGroup` per group. The unnamed default group is gone.
- `Buffer Save` and `Buffer Use` nodes are removed (changelog).

What the graph holds: `anim-graphs.md`. Formats, examples and the field by field port from 1.29: `anim-graph-format-1-30.md`.

## Bones

- There is no limit of 250 bones across all skeletons, and the engine takes a bone's global index from its name (changelog).
- `skeletons.anim.xml` mostly lost its `index` attributes: only `EntityPosition` keeps one in 19 of its 20 skeleton blocks, while the first block, the one the infected bind, still has them (`player-skeleton.md`, "What 1.30 changed for skeletons"). The file's remaining job is each bone's `lod` and the bones the `.xob` lacks.
- The player ragdoll is a text file, `P:\DZ\characters\bodies\human.ragdoll`: 11 bodies, 73.9 kg (table in `player-skeleton.md`).

## Script calls added in 1.30

| Call | Where | What it does |
|---|---|---|
| `SetAnimationInstanceByName(string animationInstanceName, float blendingTime)` | `Human`, `P:\scripts\3_game\human.c:1384` | Switches the player's animation instance at run time with a blend time. The source comment warns it can cause desync if misused. |
| `OnItemInHandsChanged(bool pInstant = false, bool pChangeAnimationInstance = true)` | `HumanItemAccessor`, `P:\scripts\3_game\humanitems.c:112` | Tells the engine the item in hands changed, and whether the instance should follow. |
| `EnableAutoAnimInstUpdateOnHandsChange(bool pNewValue)` | `HumanItemAccessor`, `P:\scripts\3_game\humanitems.c:115` | Turns the automatic instance change on or off. |
| `SetErectSpeedLimit(bool bShouldDisable, int pMaxErectSpeed = DayZPlayerConstants.MOVEMENTIDX_SPRINT)`, `SetCrouchSpeedLimit`, `SetProneSpeedLimit` | `HumanInputController`, `P:\scripts\3_game\human.c:230` to `:232` | Caps movement speed per stance. |
| `DisableProneCameraHorizontalRotation(bool pDisable)` | `HumanInputController`, `P:\scripts\3_game\human.c:242` | Locks horizontal camera rotation in prone. Its erect and crouch siblings carry a typo in vanilla: `DisableErectCameratHorizontalRotation` and `DisableCrouchCameratHorizontalRotation` (`:240`, `:241`). |
| `IsTag(TAnimGraphTag iTag)` | `HumanAnimInterface`, `P:\scripts\3_game\human.c:319` | Reads a graph tag bound with `BindTag` (`:318`). |
| `IsTransitioning()` | `HumanCommandVehicle`, `P:\scripts\3_game\human.c:735` | True while getting in, getting out or switching seat. |
| `PhysicsSetSimpleDeath(bool pEnable)` | `Human`, `P:\scripts\3_game\human.c:1449` | The older death handling, per its source comment. |
| `PhysicsSetRagdoll(bool pEnable)`, `PhysicsIsRagdoll()` | `Human`, `P:\scripts\3_game\human.c:1451`, `:1452` | Ragdoll on and off, and its state. |
| `IsFirstRenderFrame()` | `DayZPlayer`, `P:\scripts\3_game\dayzplayer.c:1189` | True on the first tick of a render frame, so work with no visible effect can be skipped on the other ticks. |
| `HasDirectionalInOutAction()`, `GetSeatAnimationTypeDirectional(int posIdx, int directionIndex)` | `Transport`, `P:\scripts\3_game\vehicles\transport.c:680`, `:693` | Left and right boarding for single track vehicles (`get-in-sides.md`). |

The ragdoll calls are on `Human` only (`class Human : Man`, `P:\scripts\3_game\human.c:1359`). Measured in game on 1.30, an infected graph does not get a ragdoll death: a `ragdoll` entry in its `enfanimsys` plus player death clips that carry the `Ragdoll` event still plays the full clip and freezes. Other setups, such as a custom `.ragdoll` for the infected skeleton, are not tested. The physics side is in `skills/_shared/physics/ragdoll-and-fall-damage.md`.

New action command constants (`CMD_ACTIONFB_` and `CMD_ACTIONMOD_`): table in `anim-graphs.md`.

## Creatures

- Quadrupeds tilt to the terrain through a procedural transform, not a special node (`anim-graphs.md`, "Terrain alignment").
- The Badlands dogs, mouflon and monitor lizard run on the wolf, herbivore and ambient life graphs with instance files of their own (`P:\DZ\animals_takistan\canis_familiaris_dobermann\config.cpp:264` to `:265`; `creature-rig-to-game.md`, "A new creature on a vanilla graph").
- Infected have the mind state `MINDSTATE_COWER` (`P:\scripts\3_game\entities\dayzinfected.c:18`), listed as new in 1.30; that it is new cannot be checked on a 1.30 `P:\`.

## Surrender no longer uses a dummy item

1.30 puts nothing in the hands for the hands up emote. `SurrenderDummyItem` remains, marked obsolete (`P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1`), and only the obsolete `CheckEmoteLockedState` still looks for it (`P:\scripts\4_world\classes\emotemanager.c:1211` to `:1214`). The player switches instance instead; the code is in `items-in-hands.md`, "Switching the instance from script (1.30)".

## Workbench

Per the changelog: the animation editor is the 2021 Enfusion editor, with live editing against a running game, a "Show In Explorer" action, native event table support and a ragdoll editor. The workspace file names its event table directly (`EventTable`, `P:\DZ\anims\workspaces\player\player_main\player_main.aw:15`).

The Workbench launch parameter `-resolveFilePatchingUsingEnfusion=1` is said to help when iterating on loose `.anm` and `.asi` files. It is not checked here.

## Vehicles

- The motorbike rider is new: `VehicleType` 10 and 11 select the motorbike state machine (`Condition "VehicleType == 10 || VehicleType == 11"`, `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1570`). In script the two animation instances are `MOTO1 = 10` and `MOTO2 = 11` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13` to `:14`), used by `Motorbike_01_ColorBase` and `Motorbike_02_ColorBase`.
- The handlebar grip uses the two bone IK nodes `AnimSrcNodeIK2Target` and `AnimSrcNodeIK2` in the vehicle sub-graph (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:17`, `:31`), with the graph variables `VehicleSteering`, `VehicleThrottle` and `VehicleSuspension` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:113`, `:118`, `:205`). How the pose is read: `rider-poses.md`.
- Single track vehicles get their own third person camera (`DAYZCAMERA_3RD_VEHICLE_MOTORBIKE`, `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`).
- A per vehicle rider pose through a child `.asi`, with no graph change, is measured in `rider-pose-measured.md`.

## Moving work from 1.29 to 1.30

- [ ] Skeleton XML: do not rely on `index` values in a custom skeleton block; the engine indexes bones by name. Keep `lod`, and keep `EntityPosition` as vanilla writes it.
- [ ] Custom graphs: port to the new format, with a master `.agr`, sub-graphs as `.agf`, template and instance in the new syntax and every template group named. Whether 1.30 still loads a 1.29 format graph is not tested. Use the mapping in `anim-graph-format-1-30.md` ("Porting a 1.29 `$AnimGraph 7` graph to 1.30"); it does not cover every node type vanilla uses, and no port made with it has been loaded in game yet.
- [ ] Buffer nodes: replace them with variables or state machine transitions.
- [ ] Grip and stance tricks that swapped items in the hands: move them to `SetAnimationInstanceByName` and `OnItemInHandsChanged`.
- [ ] Vehicles boarded from both sides: implement `HasDirectionalInOutAction()` and `GetSeatAnimationTypeDirectional()` instead of a scripted snap.
- [ ] Third party graph mods: load each alone on the new version with a vanilla mission before building on it (`anim-graphs.md`, "A measured instance of that warning").
- [ ] Templates and instances: every group of a delivered `.ast` declares a `Name` (vanilla `Name "ActionContinuous"`, `P:\DZ\anims\workspaces\player\player_main\player_main.ast:4`), and every `.asi` uses the `AnimSetInstanceSource` class (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`).
- [ ] Surrender: replace any check for `SurrenderDummyItem` in the hands with `SetSurrenderState` and `IsSurrendered`, and make sure no offline check or fixture assumes an item in the hands while surrendered.
- [ ] Weapon mappings: check whether the weapon or prop uses a bone remap (`LugerBoneRemap` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`, `LeeEnfieldBoneRemap` at `:1605`) or a dedicated `.asi` (`motion-domain-gates.md`).
- [ ] Vehicle occupants: on motorbikes, check that both hands stay locked to the bars and the feet to the pegs through every phase `IsTransitioning` on `HumanCommandVehicle` reports (`P:\scripts\3_game\human.c:735`).
- [ ] Creature terrain: paw contacts of an animal include the procedural rotation the terrain alignment applies on slopes (`SlopeAngleX`).
- [ ] Live checks: use Workbench live editing (1.30 changelog) to check continuous blend parameters on a running client before final packaging.
