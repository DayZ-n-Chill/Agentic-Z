# DayZ 1.30 for the animation director

What DayZ 1.30 changed for anyone directing character, creature, weapon or vehicle animation, what breaks in work made for 1.29, and a migration checklist.

Each fact cites the vanilla file on `P:\` (a 1.30 unpack). Lines marked "1.30 changelog" state 1.30 engine changes that are not yet checked on `P:\`. Statements about 1.29 cannot be checked on a 1.30 `P:\`. The detail per animation domain is in `domain-gates.md`; the engine-side detail and the graph port belong to `dayz-animation-pipeline`, which wins where the two differ.

## What changes

1. **Motorbike riders.**
   - Two animation instances: `MOTO1 = 10` and `MOTO2 = 11` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13-14`), used by `Motorbike_01_ColorBase` and `Motorbike_02_ColorBase`. They model a Jawa 50 cc and the three-wheeled Jawa Bitrak (model names not checked on `P:\`).
   - A third-person vehicle camera with spring lag: `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`).
   - The handlebar grip uses continuous two-bone IK nodes, `AnimSrcNodeIK2` and `AnimSrcNodeIK2Target`, in the vehicle subgraph (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:17` and `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:31`), driven by the lean and roll variables `VehicleSteering`, `VehicleThrottle` and `VehicleSuspension` (declared at `P:\DZ\anims\workspaces\player\player_main\player_main.agr:113`, `P:\DZ\anims\workspaces\player\player_main\player_main.agr:118` and `P:\DZ\anims\workspaces\player\player_main\player_main.agr:205`).
   - One transition query: `IsTransitioning` on `HumanCommandVehicle` (`P:\scripts\3_game\human.c:735-738`).
2. **Surrender.** Up to 1.29 surrendering created an invisible `SurrenderDummyItem` in the hands. In 1.30 the class remains but is marked `Obsolete` (`P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1`), and only the obsolete `CheckEmoteLockedState` still reads it (`P:\scripts\4_world\classes\emotemanager.c:1212`). Surrender is a player state: `SetSurrenderState` on `PlayerBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:2116`) and `IsSurrendered` on `Man` (`P:\scripts\3_game\entities\man.c:67`), checked by the emote manager (`m_Player.IsSurrendered()` at `P:\scripts\4_world\classes\emotemanager.c:314`).
3. **Animation instance control, and item-in-hands changes without an instance change.**
   - `SetAnimationInstanceByName` on `Human` switches the animation instance at run time, with a blend time (`P:\scripts\3_game\human.c:1384`). An `"Empty"` profile on `player_main.asi` exists to switch back to (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1548`).
   - `OnItemInHandsChanged` on `HumanItemAccessor` takes `pInstant` and `pChangeAnimationInstance` (`P:\scripts\3_game\humanitems.c:112`), so the item can change while the instance stays.
4. **Per-stance camera rotation and speed limits.** `HumanInputController` exposes `SetErectSpeedLimit`, `SetCrouchSpeedLimit`, `SetProneSpeedLimit` (`P:\scripts\3_game\human.c:230-232`) and `DisableErectCameratHorizontalRotation` with its crouch and prone twins (`P:\scripts\3_game\human.c:240-242`; the `Camerat` spelling is vanilla's).
5. **Eleven new full-body actions.** `CMD_ACTIONFB_COMBINATIONLOCK = 256` to `CMD_ACTIONFB_WETCLOTHWELL = 266` (`P:\scripts\3_game\dayzplayer.c:889-899`): combination lock, face washing, rope ladder, brick stacking, trowel, mortar mixing, drinking from a well bucket, sharpening and wetting a cloth.
6. **Skeleton indices and creature motion.**
   - 1.30 changelog: the 250-bone limit is removed and global bone indices are resolved at run time from a hash of the bone name. On `P:\` the skeletons added in 1.30 keep `index = "0" movement = "true" lod = "0"` only on `EntityPosition` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`); the survivor skeleton `hermit_newbindpose.xob` still lists `index` values on its core bones (`Pelvis` at `P:\DZ\anims\cfg\skeletons.anim.xml:8`).
   - Quadrupeds are rotated to the terrain procedurally: `AnimSrcNodeProcTransform AlignToTerrain_Rot` with the expression `SlopeAngleX  * 0.01745329251994329576923690768489` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5-18`).
   - Infected have the mind state `MINDSTATE_COWER` (`P:\scripts\3_game\entities\dayzinfected.c:18`), new in 1.30 (not checkable on a 1.30 `P:\`).
7. **Workbench tools and physics.**
   - 1.30 changelog: the Workbench Animation Editor moved to Enfusion 2021 and can Live Edit graphs on a running client.
   - 1.30 changelog: a Workbench Ragdoll Editor edits `.ragdoll` files; vanilla ships `P:\DZ\characters\bodies\human.ragdoll`.
   - Script separates animated death from ragdoll: `PhysicsSetSimpleDeath` (`P:\scripts\3_game\human.c:1449`) against `PhysicsSetRagdoll` (`P:\scripts\3_game\human.c:1451`).

## What breaks in 1.29 contracts and assets, and how to migrate

| Broken element | Cause in 1.30 | Required action |
|---|---|---|
| Graphs kept only in the older `.agr` graph syntax (`$AnimGraph`) | Graphs are now `.agf` text files in Enfusion config syntax (`Locomotion.agf`, `Vehicles.agf` and the rest), listed by the `AnimSrcGraph` index under `GraphFilesResourceNames` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`) | Re-export the workspace from the 1.30 Workbench Animation Editor, or rebuild the changes as text in the matching `.agf` files. |
| `.ast` templates with anonymous groups | 1.30 changelog: `$groupType { #ngroupnames 0 ... }` is no longer supported | Give each group an explicit `Name` (for example `Name "Default"` or `Name ".unnamed"`; vanilla has `Name "ActionContinuous"` at `P:\DZ\anims\workspaces\player\player_main\player_main.ast:4`). |
| `.asi` files in `$animsetinstance` syntax | Instances are the `AnimSetInstanceSource` class (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`) | Convert the `#template`, `#parent` and `$animations` directives to the Enfusion config structure. |
| `Buffer Save` and `Buffer Use` nodes | 1.30 changelog: removed from the animation engine | Replace buffer logic with control variables in the graph's control template (`AnimSrcGCT`) or with direct state machine connections. |
| Anything that depends on `SurrenderDummyItem` | The dummy is no longer put in the hands; the class is `Obsolete` (`P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1`) | Replace item-in-hands checks with `SetSurrenderState` and `IsSurrendered`. |
| Fixed indices in `skeletons.anim.xml` | 1.30 changelog: manual indices are ignored except on `EntityPosition` | Remove the `index` attributes from a mod's skeleton entry and make the bone names match the `.xob` model exactly. |

## Migration checklist for the animation director

- [ ] **Weapon mappings.** Check whether the weapon or interactive prop uses a bone remap (`LugerBoneRemap` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`, `LeeEnfieldBoneRemap` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1605`) or a dedicated `.asi` (bandage, hay hook and the others listed in `domain-gates.md`).
- [ ] **Vehicle occupants.** On motorbikes, audit the relative lock of both hands to the handlebars (`AnimSrcNodeIK2`) and of the feet to the footrests through every phase that `IsTransitioning` on `HumanCommandVehicle` reports.
- [ ] **Surrender.** Confirm no offline check or fixture assumes a virtual item in the hands during the surrender state.
- [ ] **Creature terrain.** Check that animal paw contacts include the procedural rotation `AnimSrcNodeProcTransform` applies on slopes (`SlopeAngleX`).
- [ ] **Templates and instances.** Check that delivered `.ast` files declare `Name` on every group and that `.asi` files use the `AnimSetInstanceSource` class.
- [ ] **Live validation.** Use Workbench Live Editing (1.30 changelog) to check continuous blend parameters on a running client before final packaging.
