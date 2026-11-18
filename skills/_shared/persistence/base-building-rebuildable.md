# Rebuildable map buildings

How a map building (`BuildingBase`) gets its own construction component on 1.30, how that component saves its parts, which config keys it reads and what the game ships for it. Player built objects (fence, watchtower, your mod's wall) use a different save; they are in `base-building.md` and `base-building-1-30.md`.

Everything here was read in the scripts on `P:\`. Unless a line says it was measured in game, none of it has been exercised in game.

## What turns construction on

Any `CfgVehicles` class with a `Construction` subclass gets a component when the entity is created:

```c
// P:\scripts\3_game\entities\entityai.c:248
if (g_Game.ConfigIsExisting("cfgVehicles" + " " + GetType() + " " + "Construction"))
    ConstructionInit();
```

The component's class comes from `CreateConstructionComponent`: `new Rebuilding(this)` on `BuildingBase` (`P:\scripts\4_world\entities\game\super\building.c:23` to `:27`) and `new Construction(this)` on `BaseBuildingBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:872` to `:876`). From those two overrides it follows, without a test in game, that a modded building inheriting a `BuildingBase` descendant needs no script override to become rebuildable, only the config block and the model selections.

This path never goes through a kit's `OnPlacementComplete`.

## The save is a version and ten ints

`Rebuilding` holds `static int REBUILDING_STORAGE_VERSION = 1` and ten ints `m_SyncParts1` to `m_SyncParts10` (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:1` to `:16`). `BuildingBase` registers the ten as net sync variables (`building.c:29` to `:46`).

`Rebuilding` overrides `HandleStoreSave` (`rebuilding.c:473`), which calls `SerializeConstructionData`: the version, then the ten ints in order (`rebuilding.c:501` to `:514`). That block sits at the very start of the entity's stream, written by `EntityAI.OnStoreSave` before the energy data (see `dayz-1-30-persistence.md`).

| | `BaseBuildingBase` | `Rebuilding` on `BuildingBase` |
|---|---|---|
| Sync ints | 3 | 10 |
| Bits per part | 1 | 2, `BITWISE_SYNCINFO_SIZE_BASE` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:6`) |
| Part ids | 1 to 93 | 1 to 160 |
| Written by | the class's own `OnStoreSave`, after `super` | `SerializeConstructionData`, through the `EntityAI` construction block |
| Own version | none; gated on the game's storage version | `REBUILDING_STORAGE_VERSION` |

The 160 is worked out, not stated: `BIT_INT_SIZE = 32` (`P:\scripts\3_game\tools\bitarray.c:4`), `GetSyncDataSize()` returns 2 (`constructionpart.c:65` to `:68`), the slot is `adjustedID = (partId - 1) * GetSyncDataSize()` and the int is `adjustedID / BIT_INT_SIZE` (`rebuilding.c:146` to `:148`), so 10 ints of 32 bits at 2 bits a part give 160 ids.

The default `CalculateBitMaskOnBuild` sets only the first of the two bits (`constructionpart.c:111` to `:117`). `ConstructionPartRebuildReversibleBase`, a subclass of `ConstructionPartRebuild` (`:1049`), also puts its reversed flag `m_TempReversed` in the second bit (`:1065` to `:1072`). A three state code (ruin, built, destroyed) is not in those methods.

Never write the ten int block from a `BaseBuildingBase` subclass, and never apply the 93 part cap to a rebuildable building.

## The version check accepts newer saves

`DeserializeConstructionData` rejects a stored version below `REBUILDING_STORAGE_VERSION` and accepts one above it (`rebuilding.c:518` to `:524`). Do not copy that as a pattern: a future build that wrote an extra int after the ten would have it read as the energy data, and every value after it would be wrong. Reject a version newer than your reader knows (`migration-matrix.md`).

## Structural support

Parts on a rebuildable building can hold each other up. `ConstructionPartStaticsSupportData` parses a `StaticsSupportData` class with `SupportProviders` and `SupportRequirements` (`P:\scripts\4_world\classes\rebuilding\constructionstatics.c:1` to `:26`). `ConstructionBase.SupportRemovalCheck` returns true by default (`P:\scripts\4_world\classes\constructionbase.c:884` to `:887`) and `Rebuilding` overrides it, so `required_parts[]` is not the only thing that decides whether a part can be removed.

## Config keys the rebuild parts read

Paths are under `Construction`, then the main part, then the part. Readers are in `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c` unless another file is named.

| Key | Reader | What the code shows |
|---|---|---|
| `custom_part_type` | `constructionparttypedholder.c:35` | the script class for the part's type data, for example the `ConstructionPartRebuild*Typed` classes |
| `can_decay_general` (on the `Construction` class) | `constructionparttypedholder.c:54` and `:55` | decay switch for the whole object |
| `can_part_decay`, `part_decay_threshold`, `part_decay_rate` | `:202`, `:208`, `:215` | decay per part |
| `insider_minMaxs` | `:162` | an inner box, beside `collision_data` (`:151`) |
| `item_falling_data` | `:191` | two memory points of the box where items fall when the part goes; `GetItemFallDetectionBoxData` uses them (`constructionbase.c:1608` to `:1631`) |
| `essential_attachments` | `:231` | read; what it does is not traced |
| `related_GUI_categories` | `:242` | ties the part to inventory GUI categories |
| `damage_hands_on_build` | `:253` | read; what it does is not traced |
| `is_utility`, `utility_build` | `:262`, `:268` | an int and a text array; what they do is not traced |
| `EffectsData` with `soundEffectPositions` and `particleEffectPositions` | `P:\scripts\4_world\classes\rebuilding\constructioneffects.c:19`, `:26` to `:28`, `:37` | memory points for build effects |
| `StaticsSupportData`, then `SupportProviders` or `SupportRequirements`, then a child with `supportCategory` (string, hashed) and `supportStrength` (int) | `constructionstatics.c:13`, `:26`, `:37`, `:38`, `:45`, `:56`, `:57` | what a part provides and needs, by category |
| `Materials`, then a material with `skipOnRepair` and `skipOnDismantle` | `P:\scripts\4_world\classes\basebuilding\constructionmaterials.c:31` and `:32` | not needed to repair, or not refunded on dismantle |

Per part decay still obeys the server switch `disableBaseDecay` (`P:\scripts\3_game\cfggameplaydatajson.c:60`), read by `GetDisableBaseDecay` (`P:\scripts\3_game\cfggameplayhandler.c:172`) and checked by `ConstructionBasic.CanConstructionDecay` (`P:\scripts\3_game\systems\construction_basic.c:37` to `:40`).

A later 1.30 update, not on `P:\` and so not checked, changes three of these: it drops `item_falling_data` and builds the fall box from `collision_data` plus margins by part category, adds `item_fall_trigger` (int, default 1; `0` takes rubble, doors and windows out of the fall check), and reads `toggle_utility_part_update` in place of the utility keys. No script on `P:\` reads `item_fall_trigger` or `toggle_utility_part_update`.

A player built `BaseBuildingBase` can ignore every key in this table.

## Locks on rebuilt doors

`BuildingBase` declares the slots `Att_CombinationLock` and `Att_CodeLock` (`building.c:10` and `:11`). One door cannot hold both: `HasConflictingDoorAttachment` (`:344` to `:356`) is called from `:228`, and `CanDoorBeOpened` is overridden (`:307`). Slot rules are in `CanReceiveAttachment` and `CanReleaseAttachment` (`building.c:192` and `:267`). How each door is wired to its slot is not traced; the door side is in `_shared/animation/building-door-locks.md`.

## What the game ships

- Script classes for the Nasdara houses (`4_World/Entities/Building/Rebuildable/House_*.c`, for example `Land_House_1M1 : BuildingSuper` at `P:\scripts\4_world\entities\building\rebuildable\house_1m1.c:1`) and `Land_IrrigationTunnel_Entrance_01 : BuildingSuper`, whose debug spawn puts a `WoodenStick` and a `Rope` in it (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1` to `:11`).
- Example part names: `Land_House_2M1_Dam2.OnDebugSpawn` builds `rubble_rubble1`, `rubble_rubble2`, `wall1_wood`, `wall2_wood`, `wall3_brick` and `roof1` with `BuildPartServerEx(null, <part>, -1)` (`P:\scripts\4_world\entities\building\rebuildable\house_2m1.c:13` to `:20`).
- `RebuildingSpawner` exists only in diag builds (`P:\scripts\4_world\classes\basebuilding\rebuildingspawner.c:1`, under `#ifdef DIAG_DEVELOPER`).
- The configs and models of these buildings are not in the unpacked `P:\DZ` data. On the first 1.30 release no unencrypted config defined `Land_House_2M1`, `Land_IrrigationTunnel_Entrance_01`, `wall1_wood` or `rubble_rubble1`, and `nasdara\addons\data_nasdara.pbo` held only the DLC `CfgMods` entry and a `mud_brick` surface.

## Attachment slots on the houses

Measured in game on a later 1.30 diag build, not checked on `P:\`: a server side scan of `CfgVehicles` (classes of kind `House`, `scope` 1 or more, a non empty `attachments[]`) found 32 classes.

| Classes | Slots |
|---|---|
| 22 houses, `Land_House_1M1` to `Land_House_3S2_Dam2` | `RB_LvL<n>_Log`, `_Plank`, `_Nail`, `_MetalSheet`, `_MetalWire`, plus `RB_LvL<n>_Brick` and `_MortarMix` on all but `Land_House_1M1`, `Land_House_1M2` and `Land_House_1S1`; `<n>` runs to 1 on the `1*` houses, 2 on the `2*` and 3 on the `3*`; lock slots `Att_CombinationLock<n>_Wood` or `_Metal` and `Att_CodeLock<n>_Wood` or `_Metal`, a number that varies per house |
| `Land_Bunker_Basement_*`, `Land_Bunker_Shelter_*` | `Att_CodeLock` |
| `Land_IrrigationTunnel_Entrance_01` | `RB_LvL1_Rope`, `RB_LvL1_Stick`, `RB_LvL2_Rope`, `RB_LvL2_Stick` |
| `Land_Radio_PanelBig`, `Land_Radio_PanelPAS` | `LargeBattery` |
| `Land_WaterWell_Brick` | listed by the scan |

A `Land_House_1M1` spawned on Chernarus reported the nine level 1 slots, and a `WoodenPlank` attached to `RB_LvL1_Plank`. Moves into and out of these slots reach `ItemBase.EEItemLocationChanged` with the house as the hierarchy root (`_shared/enscript/depth/dayz-1-30-inventory.md`). Not measured: the Nasdara map itself, the models, and the rebuild actions on these slots.

## Object Spawner flag

The Object Spawner now sets `ECE_OBJECT_SPAWNER = 256` (`P:\scripts\3_game\ce\centraleconomy.c:15`) on objects it creates by class name (`P:\scripts\3_game\objectspawner.c:48`). Its `.p3d` path calls `CreateStaticObjectUsingP3D` with five arguments (`objectspawner.c:44`): the last `true` is `createLocal`, and the sixth parameter `objSpawner` keeps its default `false`. `CreateObject` and `CreateStaticObjectUsingP3D` both gained `bool objSpawner = false` (`P:\scripts\3_game\global\game.c:680` and `:691`).

Script does not show what the engine does with the flag. Whether a rebuildable building placed by the Object Spawner keeps its parts across a restart is not measured.

Terrain holes, underground triggers and the underground placement block are in `_shared/world/terrain-holes.md` and `_shared/world/underground-triggers.md`.
