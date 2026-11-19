# Rebuildable map buildings

How a map building (`BuildingBase`) gets its own construction component on 1.30, how that component saves its parts, which config keys it reads and what the game ships for it. Player built objects (fence, watchtower, your mod's wall) use a different save; they are in `base-building.md` and `base-building-1-30.md`.

Everything here was read in the scripts and configs on `P:\`. None of it has been exercised in game.

## What turns construction on

Any `CfgVehicles` class with a `Construction` subclass gets a component when the entity is created:

```c
// P:\scripts\3_game\entities\entityai.c:248
if (g_Game.ConfigIsExisting("cfgVehicles" + " " + GetType() + " " + "Construction"))
    ConstructionInit();
```

The component's class comes from `CreateConstructionComponent`: `new Rebuilding(this)` on `BuildingBase` (`P:\scripts\4_world\entities\game\super\building.c:47` to `:51`) and `new Construction(this)` on `BaseBuildingBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:871` to `:875`). From those two overrides it follows, without a test in game, that a modded building inheriting a `BuildingBase` descendant needs no script override to become rebuildable, only the config block and the model selections.

This path never goes through a kit's `OnPlacementComplete`.

## The save is a version and ten ints

`Rebuilding` holds `static int REBUILDING_STORAGE_VERSION = 1` and ten ints `m_SyncParts1` to `m_SyncParts10` (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:1` to `:16`). `BuildingBase` registers the ten as net sync variables in `RegisterConstructionSyncVariables` (`building.c:53` to `:70`).

`Rebuilding` overrides `HandleStoreSave` (`rebuilding.c:473` to `:481`), which calls `SerializeConstructionData`: the version, then the ten ints in order (`rebuilding.c:501` to `:514`). `HandleStoreLoad` reads them back, logs a failed read as corrupted data instead of failing the load, and syncs any changed parts (`:483` to `:499`). That block sits at the very start of the entity's stream, written by `EntityAI.OnStoreSave` before the energy data (see `dayz-1-30-persistence.md`).

| | `BaseBuildingBase` | `Rebuilding` on `BuildingBase` |
|---|---|---|
| Sync ints | 3 | 10 |
| Bits per part | 1 | 2, `BITWISE_SYNCINFO_SIZE_BASE` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:6`) |
| Part ids | 1 to 93 | 1 to 160 |
| Written by | the class's own `OnStoreSave`, after `super` | `SerializeConstructionData`, through the `EntityAI` construction block |
| Own version | none; gated on the game's storage version | `REBUILDING_STORAGE_VERSION` |

The 160 is worked out, not stated: `BIT_INT_SIZE = 32` (`P:\scripts\3_game\tools\bitarray.c:4`), `GetSyncDataSize()` returns 2 (`constructionpart.c:65` to `:68`), the slot is `adjustedID = (partId - 1) * GetSyncDataSize()` and the int is `adjustedID / BIT_INT_SIZE` (`rebuilding.c:146` to `:148`), so 10 ints of 32 bits at 2 bits a part give 160 ids.

The default `CalculateBitMaskOnBuild` sets only the first of the two bits (`constructionpart.c:111` to `:117`). `ConstructionPartRebuildReversibleBase`, a subclass of `ConstructionPartRebuild` (`:1035`), also puts its reversed flag `m_TempReversed` in the second bit (`:1051` to `:1058`) and reads it back with `IsReversedLocal` (`:1065` to `:1068`). A three state code (ruin, built, destroyed) is not in those methods.

Never write the ten int block from a `BaseBuildingBase` subclass, and never apply the 93 part cap to a rebuildable building.

## The version check accepts newer saves

`DeserializeConstructionData` rejects a stored version below `REBUILDING_STORAGE_VERSION` and accepts one above it (`rebuilding.c:518` to `:524`). Do not copy that as a pattern: a future build that wrote an extra int after the ten would have it read as the energy data, and every value after it would be wrong. Reject a version newer than your reader knows (`migration-matrix.md`).

## Structural support

Parts on a rebuildable building can hold each other up. `ConstructionPartStaticsSupportData` parses a `StaticsSupportData` class with `SupportProviders` and `SupportRequirements` (`P:\scripts\4_world\classes\rebuilding\constructionstatics.c:1` to `:26`). `ConstructionBase.SupportRemovalCheck` returns true by default (`P:\scripts\4_world\classes\constructionbase.c:884` to `:887`) and `Rebuilding` overrides it to refuse a removal that would leave a support requirement unmet (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:654` to `:666`), so `required_parts[]` is not the only thing that decides whether a part can be removed.

## Config keys the rebuild parts read

Paths are under `Construction`, then the main part, then the part. Readers are in `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c` unless another file is named.

| Key | Reader | What the code shows |
|---|---|---|
| `custom_part_type` | `constructionparttypedholder.c:35` | the script class for the part's type data, for example the `ConstructionPartRebuild*Typed` classes |
| `can_decay_general` (on the `Construction` class) | `constructionparttypedholder.c:54` and `:55` | decay switch for the whole object |
| `can_part_decay`, `part_decay_threshold`, `part_decay_rate` | `:191`, `:197`, `:204` | decay per part |
| `insider_minMaxs` | `:162` | an inner box, beside `collision_data` (`:151`); an odd count is an error (`:177`) |
| `item_fall_trigger` | `:256` to `:262` | int, default 1; `0` takes the part out of the item fall check, as vanilla does for rubble, doors and windows (`constructionbase.c:282` to `:286`). The fall box is the `collision_data` box plus a top margin by part name (`GetItemFallDetectionBoxData` and `GetItemFallBoxMargins`, `constructionbase.c:1722` to `:1763`) |
| `essential_attachments` | `:220` | slots whose attachment is unlocked and dropped when the part is dismantled or destroyed (`constructionbase.c:1440` to `:1482`); the houses list their door lock slots |
| `related_GUI_categories` | `:231` | ties the part to `GUIInventoryAttachmentsProps` categories; a name that matches none is an error (`constructionparttypedholder.c:87` to `:104`) |
| `damage_hands_on_build` | `:242` | default true; a part built with no tool damages the gloves or may make the hands bleed (`actionbuildpart.c:184` to `:195`) |
| `is_utility` | `:251` | marks a helper part, commented "Special helper parts with invalid IDs" (`:17`); `HasDependentPart` ignores it (`constructionbase.c:874`) |
| `toggle_utility_part_update` | `:267` | int; a part with it set queues the utility part update when it changes (`constructionpart.c:883` and `:884`) |
| `hand_build_FB_anim_override`, `RequiredPartsVariants`, `build_text_override`, `dismantle_text_override`, `physics_geom_names` with `physics_geom_behaviors_invert`, `override_animsource_names`, `proxyroadway_names` | `:211`, `:276`, `:316`, `:326`, `:337` and `:344`, `:360`, `:382` | further per part options; a mismatched pair of name and invert arrays is an error (`:356`, `:401`) |
| `EffectsData` with `soundEffectPositions` and `particleEffectPositions` | `P:\scripts\4_world\classes\rebuilding\constructioneffects.c:19`, `:26` to `:28`, `:37` to `:39` | memory points for build effects |
| `StaticsSupportData`, then `SupportProviders` or `SupportRequirements`, then a child with `supportCategory` (string, hashed) and `supportStrength` (int) | `constructionstatics.c:13`, `:26`, `:37`, `:38`, `:45`, `:56`, `:57` | what a part provides and needs, by category |
| `Materials`, then a material with `skipOnRepair` and `skipOnDismantle` | `P:\scripts\4_world\classes\basebuilding\constructionmaterials.c:31` and `:32` | not needed to repair, or not refunded on dismantle |

Per part decay still obeys the server switch `disableBaseDecay` (`P:\scripts\3_game\cfggameplaydatajson.c:60`), read by `GetDisableBaseDecay` (`P:\scripts\3_game\cfggameplayhandler.c:172`) and checked by `ConstructionBasic.CanConstructionDecay` (`P:\scripts\3_game\systems\construction_basic.c:37` to `:40`).

The house configs still carry `item_falling_data[]` (for example `P:\DZ\structures_takistan\Residential\config.cpp:1011` to `:1015`), but no script on `P:\` reads it or `utility_build`; the fall box comes from `collision_data`. The server can turn item falling off with `disableItemFalling` in `cfggameplay.json` (`P:\scripts\3_game\cfggameplaydatajson.c:279`, read by `GetDisableItemFalling` at `P:\scripts\3_game\cfggameplayhandler.c:352`), which the dismantle and destroy paths check (`constructionbase.c:239` and `:254`).

A player built `BaseBuildingBase` can ignore every key in this table.

## Locks on rebuilt doors

`BuildingBase` declares the slot name prefixes `Att_CombinationLock` and `Att_CodeLock` (`building.c:10` and `:11`); a house numbers them per door and material, such as `Att_CodeLock1_Wood` (`P:\DZ\structures_takistan\Residential\config.cpp:934` to `:945`). One door cannot hold both kinds: `HasConflictingDoorAttachment` (`building.c:449` to `:461`) is checked in `CanReceiveAttachment` (`:297` to `:355`, which also refuses a lock while the door is open) and `CanDisplayAttachmentSlot` (`:357` to `:370`). `CanReleaseAttachment` keeps a locked lock in place (`:372` to `:386`) and `CanDoorBeOpened` refuses while a lock on the door is locked (`:412` to `:438`). `BuildingBase.IsLocked(int doorIndex)` returns false in every branch (`:388` to `:410`), so check `CanDoorBeOpened` instead. The door side is in `_shared/animation/building-door-locks.md`.

On load, `BuildingBase.AfterStoreLoad` releases door lock slots left locked with no lock in them and refreshes each code lock's door info (`building.c:77` to `:94`, `:133` to `:156`). `EEItemDetached` releases a combination lock's slot and unlocks the door a code lock held (`:96` to `:111`).

## What the game ships

- Script classes for the Nasdara houses (`4_World/Entities/Building/Rebuildable/House_*.c`, for example `Land_House_1M1 : BuildingSuper` at `P:\scripts\4_world\entities\building\rebuildable\house_1m1.c:1`) and `Land_IrrigationTunnel_Entrance_01 : BuildingSuper`, whose debug spawn puts a `WoodenStick` and a `Rope` in it (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1` to `:11`).
- Example part names: `Land_House_2M1_Dam2.OnDebugSpawn` builds `rubble_rubble1`, `rubble_rubble2`, `wall1_wood`, `wall2_wood`, `wall3_brick` and `roof1` with `BuildPartServerEx(null, <part>, -1)` (`P:\scripts\4_world\entities\building\rebuildable\house_2m1.c:13` to `:20`).
- `RebuildingSpawner` exists only in diag builds (`P:\scripts\4_world\classes\basebuilding\rebuildingspawner.c:1`, under `#ifdef DIAG_DEVELOPER`).
- The configs are under `P:\DZ\structures_takistan`: the houses in `Residential\config.cpp` (`class Land_House_1M1: HouseNoDestruct` at `:18`, its `class Construction` at `:988`), `Land_IrrigationTunnel_Entrance_01` in `Industrial\config.cpp:20` (its `Construction` at `:383`) and `Land_WaterWell_Brick` in `Props\config.cpp:18`. A house part from `Land_House_1M1`: main part `rebuild_door1`, part `door1_wood` with `id=1`, `conflicted_parts[]={"door1_metal"}`, `build_action_type=2`, `material_type=2` and four materials (`Residential\config.cpp:991` to `:1062`).

## Attachment slots on the houses

A scan of the `attachments[]` arrays in `P:\DZ\structures_takistan\*\config.cpp` and `P:\DZ\structures\specific\config.cpp` finds 32 house classes with slots.

| Classes | Slots |
|---|---|
| 22 houses, `Land_House_1M1` to `Land_House_3S2_Dam2` | `RB_LvL<n>_Log`, `_Plank`, `_Nail`, `_MetalSheet`, `_MetalWire`, plus `RB_LvL<n>_Brick` and `_MortarMix` on all but `Land_House_1M1`, `Land_House_1M2` and `Land_House_1S1`; `<n>` runs to 1 on the `1*` houses, 2 on the `2*` and 3 on the `3*`; lock slots `Att_CombinationLock<n>_Wood` or `_Metal` and `Att_CodeLock<n>_Wood` or `_Metal`, a number that varies per house |
| `Land_Bunker_Basement_*`, `Land_Bunker_Shelter_*` | `Att_CodeLock` |
| `Land_IrrigationTunnel_Entrance_01` | `RB_LvL1_Rope`, `RB_LvL1_Stick`, `RB_LvL2_Rope`, `RB_LvL2_Stick` |
| `Land_Radio_PanelBig`, `Land_Radio_PanelPAS` | `LargeBattery` |
| `Land_WaterWell_Brick` | six slots, among them `RB_LvL1_Brick` and `RB_LvL1_MortarMix` (`P:\DZ\structures_takistan\Props\config.cpp:333` to `:341`) |

`Land_House_1M1` has the nine level 1 slots (`Residential\config.cpp:934` to `:945`); the bunkers' `Att_CodeLock` is in `P:\DZ\structures_takistan\Military\config.cpp` (for example `:27`), the irrigation tunnel's slots at `Industrial\config.cpp:350` to `:356` and the radio panels' `LargeBattery` at `P:\DZ\structures\specific\config.cpp:29` and `:51`. Measured in game, not checked on `P:\`: a `Land_House_1M1` spawned on Chernarus took a `WoodenPlank` in `RB_LvL1_Plank`, and moves into and out of these slots reach `ItemBase.EEItemLocationChanged` with the house as the hierarchy root (`_shared/enscript/depth/dayz-1-30-inventory.md`). The rebuild actions on these slots have not been run in game.

## Object Spawner flag

The Object Spawner now sets `ECE_OBJECT_SPAWNER = 256` (`P:\scripts\3_game\ce\centraleconomy.c:15`) on objects it creates by class name (`P:\scripts\3_game\objectspawner.c:48`). Its `.p3d` path calls `CreateStaticObjectUsingP3D` with five arguments (`objectspawner.c:44`): the last `true` is `createLocal`, and the sixth parameter `objSpawner` keeps its default `false`. `CreateObject` and `CreateStaticObjectUsingP3D` both gained `bool objSpawner = false` (`P:\scripts\3_game\global\game.c:680` and `:691`).

Script does not show what the engine does with the flag. Whether a rebuildable building placed by the Object Spawner keeps its parts across a restart is not measured.

Terrain holes, underground triggers and the underground placement block are in `_shared/world/terrain-holes.md` and `_shared/world/underground-triggers.md`.
