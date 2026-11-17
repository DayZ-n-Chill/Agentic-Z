# DayZ 1.29 to 1.30: build timeline and what each build changed

Tier 3 pack: which DayZ build a fact or a line number belongs to, and what moved between the 1.30 builds. Load it when porting a 1.29 mod to 1.30, when a vanilla citation lands on the wrong line, or when a mod that worked on one 1.30 build breaks on the next. Tier 1 and Tier 2 still apply on top.

Each row is a one-line statement of the change with the skill that holds the depth. The dates, counts and "changed in build X" statements come from comparing the vanilla script trees of those builds (2026-10-28 on 1.30.164200, 2026-11-09 on 1.30.164289).

**What `P:\` shows.** The lines below marked "on `P:\`" were opened for this file. The extraction they were checked on is a 1.30 build older than 1.30.164200: it still declares `vector.Cross` (`P:\scripts\1_core\proto\enconvert.c:239`) and has no `1_core\workbenchapi\` folder. So `P:\` confirms the "before" side of the 1.30.164200 and 1.30.164289 rows, and the "after" side is **not yet checked on `P:\`**. Run the check again after the vanilla data is re-extracted from a newer build.

## Timeline

| Build | What it is | Date |
|---|---|---|
| 1.29.0.163451 | The 1.29 vanilla script tree. A citation labelled `1.29` gives its lines. | stable until 2026-10-15 |
| 1.29.163709 | DayZDiag build of the 1.29 in-game measurements (collision boxes, winding, moving platforms). | 2026-10-01 to 2026-10-03 |
| 1.30.164014 | 1.30 Experimental, the first 1.30 extraction. Measurements labelled "1.30 Exp" were made here. | 2026-10-01 onward |
| 1.30.164078 | 1.30 reaches stable. | 2026-10-15 |
| 1.30.164200 | Stable patch. Changes 68 script files and adds 14 (13 under `1_core/workbenchapi/`, plus `constructionpartrebuildinvertedsupport.c`); removes none. | on the measuring install since 2026-10-21 |
| 1.30.164289 | Stable patch (Steam update of 2026-11-04, `DayZ_x64.exe` 1.30.164.289, DayZ Server Steam build 26220720). Changes 27 of the 3,076 script files, all `.c`; `scripts\config.cpp` is unchanged. | 2026-11-04 |

Data files between 1.30.164200 and 1.30.164289: none of the 42,357 extracted data entries (configs, layouts, XML, `.agf`, `.rvmat`) changed. 2,143 `.p3d` models, four `navmesh.nm` files and `ChernarusPlus.wrp` changed size and were not compared.

DayZ Tools: since the DayZ Tools update of 2026-10-15 (Steam build 25460346, `binarize.exe` 1.30.164.078) a model you binarize is ODOL v56, the version of the 1.30 vanilla models. Before that update the tools wrote v55, and 1.29 vanilla models are v54. A v56 file has 4 more zero bytes in the model info, so a v55 reader fails on it. Read header bytes 4 to 7 before choosing a reader. A map binarized by the same tools is OPRW v32 (1.29: v29), with 64-byte object records: the 60 bytes of v29 plus a `uint32` at +60 that was 0 in every record of the one map read. Depth: the model pipeline and P3D inspection skills.

## Which line a citation gives

A vanilla line number is only right for one build. The skills named in the Depth columns cite 1.30.164289 lines (as of 2026-11-09). A citation labelled `1.29` gives the 1.29 line; a measurement keeps the build it was made on. When a cited line does not match on `P:\`, find the symbol by name before deciding the fact is wrong: the 27 files that 1.30.164289 changed include base building, the code lock, the diag menu, heat stroke, `game.c`, `playerconstants.c` and `miscgameplayfunctions.c`.

## 1.29 to 1.30 (any 1.30 build)

| Change | On `P:\` | Depth |
|---|---|---|
| `CarFluid` is an alias of `ETransportFluid`. | `P:\scripts\3_game\vehicles\car.c:18` | `dayz-vehicles` |
| A ruined wheel becomes the class `<wheel>_Ruined`, derived from the wheel's name. Every custom wheel class needs that twin or the swap raises a script error. | not yet checked on `P:\` | `dayz-vehicles` |
| `CarScript.ToggleHeadlights()` is deleted with no `[Obsolete]` stub. An `override` of it stops the `4_World` compile. | no `ToggleHeadlights` anywhere under `P:\scripts\4_world` | `dayz-vehicles` |
| A battery car that does not override the three electricity-source methods reports `NO_BATTERY` with a battery attached. | not yet checked on `P:\` | `dayz-vehicles` |
| A script module path written with backslashes (`files[] = {"Mod\scripts\4_world"}`) loads no scripts and logs nothing. Use forward slashes. Measured in game on 1.30.164200. | measured result | `dayz-mod-workflow` |
| The camera reads its look limits from the native `GetLookLimits`. | `P:\scripts\3_game\dayzplayer.c:1319` | `enforce-script-reference` |
| Camera id 32 (`DAYZCAMERA_3RD_VEHICLE_MOTORBIKE`) is new. Vanilla uses ids 1 to 14 and 30 to 32. | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20` | `enforce-script-reference` |
| `ActionTargetsCursor.Update()` became `Update(bool fullUpdate = true)`. A 1.29 override fails with `Overloaded function 'Update' not compatible`. | `P:\scripts\5_mission\gui\actiontargetscursor.c:310` | `enforce-script-reference` |
| `EntityAI` has a `RegisterConstructionSyncVariables` hook, called from `ConstructionInit` when the type's config has a `Construction` class. `BuildingBase` registers its ten `m_SyncParts` ints there. | `P:\scripts\3_game\entities\entityai.c:3481`, `P:\scripts\3_game\entities\entityai.c:248-249`, `P:\scripts\4_world\entities\game\super\building.c:29-44` | `dayz-basebuilding` |
| The vital-parts check runs through `Transport.CheckVitalItemCallback`; `CarScript.CheckVitalItem` is obsolete. | `P:\scripts\3_game\vehicles\transport.c:420` | `dayz-aviation` |
| `CanDismantlePart` and `CanDestroyPart` also require `SupportRemovalCheck`. | `P:\scripts\4_world\classes\constructionbase.c:741` | `dayz-basebuilding` |
| `SurrenderDummyItem` is still declared, marked obsolete. 1.30 no longer puts it in the hands. | `P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1-2` | `dayz-animation-pipeline` |
| `LocalTakeEntityAsAttachmentEx` is obsolete and `Man` no longer overrides it. | the `[Obsolete]` mark and the declaration at `P:\scripts\3_game\entities\entityai.c:4880-4881`; `man.c` beside it holds no override | `enforce-script-reference` |
| `THERMAL_BIAS` takes index 11 of the player stats. | not yet checked on `P:\` | `dayz-environment-hazards` |
| The item sounds started in one frame go in one RPC. | not yet checked on `P:\` | `dayz-sound-system` |
| The 1.29 `$AnimGraph 7` text graphs become a new file set (`.agr`, `.agf`, `.ast`, `.asi`). All 187 clips of the vanilla infected instance keep their 1.29 GUID. | data files, not yet checked on `P:\` | `dayz-animation-pipeline` |
| `modded class DayZPlayerInventory` and `modded class Magazine` stop the World module: "Engine class '...' cannot be modded." Measured on DayZDiag 1.30.164200; `Transport` was refused the same way on 1.29. | measured result | `enforce-script-reference` |

## What 1.30.164200 changed (from 1.30.164014 and 1.30.164078)

| Change | On `P:\` (older build) | Depth |
|---|---|---|
| `vector.Cross` is gone. It was a script method in 1.30.164014 and 1.30.164078; a call stops the server with `Undefined function 'vector.Cross'`. | still declared: `Cross` at `P:\scripts\1_core\proto\enconvert.c:239` | `enforce-script-reference` |
| `NVTypes` gains `NV_OPTICS_UNDERGROUND_DAY` and `NV_OPTICS_UNDERGROUND_SANDSTORM_DAY` in the middle of the list, so every value after `NV_OPTICS_UNDERGROUND` has a new number. Never store or send these as raw ints across builds. | older list: `NV_OPTICS_UNDERGROUND` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:69` | `dayz-mod-workflow` |
| The `Slot_Att_CodeLock*` slots' `displayName` is `#STR_CfgVehicles_codelock0`. | older value `#STR_CodeLock0` at `P:\scripts\config.cpp:2771` | `dayz-doors` |
| A construction part reads the int `toggle_utility_part_update`. | older builds read the text array `utility_build`: `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:268` | `dayz-basebuilding` |
| Both vanilla motorbikes declare their front and brake reflector materials, `Motorbike_02_ColorBase` renames its light selections, and the bikes register the front light on its own index again. | not yet checked on `P:\` | `dayz-motorbikes` |
| The Nasdara map is installed (`nasdara\addons\`, 24 PBOs and an encrypted `worlds_nasdara.ebo`). 1.30.164014 had only a 6-file `data_nasdara.pbo`. | not on `P:\` | `dayz-underground`, `dayz-environment-hazards` |
| The SCARL, Luger, LeeEnfield and MP18, their magazines and the P1907 bayonet ship with models and configs in `nasdara\addons\weapons_nasdara.pbo` (prefix `DZ\weapons_takistan`). On 1.30.164014 they were script-only. Two config parents differ from the script ones: `SCARL_Base` and `MP18_Base` inherit `Rifle_Base`. | not on `P:\` | `dayz-weapons` |
| `day_z_hud.layout` gives widget names in `Name` lines instead of in the widget headers (5,176 lines become 5,468), rounds 115 values to three decimals, and its 12 `mtl_down` images use `mode blend` where they had `mode additive`. A layout parser has to read both forms. | not yet checked on `P:\` | `dayz-ui-development` |

## What 1.30.164289 changed (from 1.30.164200)

| Change | On `P:\` (older build) | Depth |
|---|---|---|
| Heat stroke: phase 2's `OnDeactivate` decrements the disease count (phase 1's no longer does), which fixes the sickness icon. Phase 2 deactivates below 0.38 (`STAGE_DEACTIVATION_BUFFER = 0.02`) and runs `OnActivate` again on reconnect. Phase 4 does 0.01 to 0.15 health damage per tick, down from 0.01 to 0.35. | not yet checked on `P:\` | `dayz-environment-hazards` |
| `THERMAL_BIAS_POSITIVE_HC_DECREMENT` is 0.0002 and `THERMAL_BIAS_POSITIVE_HC_LOW_INCREMENT` is 0.0002. | older values 0.0001 and 0.00022: `THERMAL_BIAS_POSITIVE_HC_DECREMENT` at `P:\scripts\3_game\playerconstants.c:206`, `THERMAL_BIAS_POSITIVE_HC_LOW_INCREMENT` at `P:\scripts\3_game\playerconstants.c:208` | `dayz-environment-hazards` |
| `HeatComfortMdfr` lowers the bias of a player with high water through the new `RecoverThermalBias`. Washing the head again while its 30 s resistance runs no longer lowers the bias or restarts the 30 s. | not yet checked on `P:\` | `dayz-environment-hazards` |
| `CollisionFlags` starts with `NONE = 0`, which moves every other value up by one. Use the enum names, never the numbers. | older enum starts at `FIRSTCONTACT`: `CollisionFlags` at `P:\scripts\1_core\proto\endebug.c:140` | `dayz-physics-engine` |
| `Land_WarheadStorage_Main` and `Land_WarheadStorage_Bunker_Facility` override the `DoorManipulationParams` form of `CanDoorBeOpened`, not the `int` form. | not yet checked on `P:\` | `dayz-doors` |
| A construction part no longer reads `item_falling_data`. The box in which items fall when the part goes is built from `collision_data` plus margins by part category, and the new int `item_fall_trigger` (default 1) takes a part out of that check with `0`. | older builds read `item_falling_data`: `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:191` | `dayz-basebuilding` |

## Rules this history teaches

- **Resolve every `override` against the target build's class chain before porting.** A deleted method (`ToggleHeadlights`) or a changed signature (`Update(bool fullUpdate = true)`) stops a whole script module, and an offline lint against the old tree passes.
- **Never persist or send an enum as a raw number across builds.** Two vanilla enums (`NVTypes`, `CollisionFlags`) were renumbered inside the 1.30 patch line.
- **A minor stable patch can remove script API.** `vector.Cross` existed for two 1.30 builds and then went away. Check the build the server runs, not the build the code was written on.
- **Compare the vanilla tree with the game's own `dta\scripts.pbo` when a lookup disagrees with the server.** An extraction left over from an earlier build answers for that build.
- **State the build with every measurement.** A result measured on DayZDiag 1.29 or on 1.30 Experimental is a lead on 1.30 stable until it is measured there.
