# Locks on building doors

How a 1.30 building door takes a combination lock or a code lock: the slots, the `class Doors` keys, the memory names script looks up, the two lock items, the bunker door, and what breaks when a 1.29 door mod moves to 1.30. The open check itself is in `door-open-and-lock-code.md`; the rest of the door keys are in `door-config-and-locks.md`.

Facts cite `P:\` (DayZ 1.30). The three worked patterns in `door-patterns.md` have no lock slots.

## Lock slots on a building

In 1.30 `House` is a `BuildingBase`, which takes `CombinationLock` and `DigitalCodeLock` as attachments and ties them to a door through `AdditionalDoorInfo`. Before 1.30 a world building's door locked only through the engine's `LockDoor` and `UnlockDoor` with a lockpick (that build is not on `P:\`, so this is not checked there).

| Slot | Constant | `CfgSlots` selection | Source |
|---|---|---|---|
| `Att_CombinationLock` | `ATTACHMENT_SLOT_COMBINATION_LOCK` | `att_combinationlock` | `P:\scripts\4_world\entities\game\super\building.c:10`; `P:\scripts\config.cpp:2316` to `:2321` |
| `Att_CodeLock` | `ATTACHMENT_SLOT_CODE_LOCK` | `att_codelock` | `building.c:11`; `P:\scripts\config.cpp:2768` to `:2773` |

Every `Slot_Att_CodeLock*` slot has the `displayName` `"#STR_CfgVehicles_codelock0"` (`P:\scripts\config.cpp:2771`).

The vanilla fence, a player built gate, lists both slots at entity level, not inside `class Doors`: its whole `attachments[]` is `Wall_Barbedwire_1`, `Wall_Barbedwire_2`, `Wall_Camonet`, `Att_CombinationLock`, `Att_CodeLock`, `Material_Nails`, `Material_WoodenPlanks`, `Material_MetalSheets`, `Material_WoodenLogs` and `Material_MetalWire` (`P:\DZ\gear\camping\config.cpp:4362` to `:4368`).

## Door keys the lock code reads

`Building.InitializeDoorInfos` reads an `AdditionalDoorInfo` once per building type for each `class Doors` child (`P:\scripts\3_game\entities\building.c:302` to `:310`). `AdditionalDoorInfo.Init` reads these keys (`P:\scripts\3_game\entities\additionaldoorsinfo.c:21` to `:45`):

| Key | Member | When missing |
|---|---|---|
| `relatedInventorySlots[]` | `m_RelatedInventorySlotNames` | Stays null; no slot belongs to the door. |
| `lockCompatibilityBitMask` | `m_LockCompatibilityBitMask` | `1 << EBuildingLockType.LOCKPICK`; the vanilla comment says "default behavior if not configured". |
| `interactPositionPoint` | `m_InteractLimitingPositionPoint` | Empty; the door opens from both sides. |
| `interactDirPoint` | `m_InteractLimitingDirPoint` | Empty. |
| `doorConstructionPart` | `m_DoorConstructionPartName` | Empty. |
| `doorConstructionPhysicsSource` | `m_DoorConstructionPhysicsSource` | Empty. |

The Badlands houses that can be rebuilt are the vanilla example, all in `P:\DZ\structures_takistan\Residential\config.cpp` (150 `relatedInventorySlots[]` entries, the only ones under `P:\DZ`). `Land_House_1M1` (`:18`) gives its door `door1_door_wood` (`:25`) the slots `Att_CodeLock1_Wood` and `Att_CombinationLock1_Wood` (`:37` to `:41`), `lockCompatibilityBitMask=0` so no lockpick fits (`:42`), and `doorConstructionPart` and `doorConstructionPhysicsSource` (`:43`, `:44`). Its windows set `interactPositionPoint` and `interactDirPoint` (`:80`, `:81`). The entity lists the numbered lock slots in `attachments[]` (`:934` to `:945`) and has a `class Construction` (`:988`).

## Adding a lock to a mod building door

On top of the `class Doors` block from `door-patterns.md`, following `Land_House_1M1` above:

1. List `Att_CombinationLock`, `Att_CodeLock` or both in the entity's `attachments[]`, with the numbered wood and metal variants when you copy the slot naming of the houses that can be rebuilt.
2. Give the entity a `class Construction`. Only then does `EntityAI` create the construction component (`P:\scripts\3_game\entities\entityai.c:248` to `:249`; `BuildingBase` makes it a `Rebuilding`, `P:\scripts\4_world\entities\game\super\building.c:47` to `:51`), and without it `CanUseConstruction()` is false (`entityai.c:3485` to `:3488`), so the attach action skips the building.
3. On that door's Doors child set `relatedInventorySlots[] = {"Att_CombinationLock","Att_CodeLock"};` so Open, the lockpick and the attach action know which slots belong to which door.
4. Set `lockCompatibilityBitMask` only when the lockpick or ship container keys should differ from the default; vanilla sets 0 on lockable house doors.
5. Add the Memory selections `att_combinationlock` and `att_codelock`, and usually a proxy in the Resolution LOD under the same name.
6. Add `interactPositionPoint` and `interactDirPoint` only for a door that works from one side.

## How the lock behaves on the door

- Attaching: the building branch of `ActionAttachToConstruction` takes the slot from the door's `m_RelatedInventorySlotNames`, only for an `IsExternalLockType()` item, and only while the door is closed and not engine locked. A door with no related slots returns `InventorySlots.INVALID` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattachtoconstruction.c:151` to `:174`).
- A second lock: `BuildingBase.CanReceiveAttachment` refuses a lock on the twin slot and any external lock while the door is open (`P:\scripts\4_world\entities\game\super\building.c:297` to `:355`). `HasConflictingDoorAttachment` (`:449`) swaps the `Att_CodeLock` and `Att_CombinationLock` parts of the slot name to find the twin.
- Removing: `CanReleaseAttachment` refuses while `DigitalCodeLock.IsLocked()` or `CombinationLock.IsLocked()` is true (`building.c:372` to `:386`).
- Opening: a locked lock in a related slot makes `BuildingBase.CanDoorBeOpened` return false (`building.c:412` to `:438`).
- The attach branch also needs `CanUseConstruction()` to be true on the building (`actionattachtoconstruction.c:151`); the same call decides whether the building's inventory and health show at all (`P:\scripts\3_game\entities\building.c:282` to `:331`).
- The lockpick: `ActionLockDoors` and `ActionUnlockDoors` stop offering the lockpick when a related slot holds an external lock, but only when the door lists that slot in `relatedInventorySlots[]`, which script reads as `m_RelatedInventorySlotNames` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionlockdoors.c:40` to `:54`).

`EBuildingLockType` holds only `NONE`, `LOCKPICK` and the ship container keys (`P:\scripts\3_game\enums\ebuildinglocktypes.c:7` to `:16`). Combination and code locks are attachments, not enum values: never invent `COMBINATION_LOCK = 2` or `CODE_LOCK = 4`.

## Memory names the lock code reads

The door's own Memory LOD (axes, `soundPos`, interaction point) is the same as before 1.30. These are the extra names script looks up:

| Role | Config or script name | Memory names | Source |
|---|---|---|---|
| Lock proxy | The `selection` of the `CfgSlots` class | `att_combinationlock`, `att_codelock` and the numbered wood and metal variants | `P:\scripts\config.cpp:2316` to `:2321`; `:2768` to `:2773` |
| One sided open and close | `interactPositionPoint` and `interactDirPoint` on the Doors child | Whatever you write there; empty or missing passes, because `MemPointDirectionalCheck` returns true when a point is missing | `P:\scripts\3_game\entities\additionaldoorsinfo.c:34` to `:38`; `P:\scripts\4_world\static\miscgameplayfunctions.c:942` to `:967` |
| Bunker inside against outside | `Bunker.CanDoorBeOpened` builds `"%1_action"` and `"%1_inside"` from `m_DoorType` | For a Doors child `Door1`: `Door1_action`, `Door1_inside` | `P:\scripts\4_world\entities\building\bunker.c:47` to `:54` |
| Code lock facing | `MEMPOINT_CENTER` and `MEMPOINT_INSIDE` on the lock item's own model | `ce_center`, `inside` | `P:\scripts\4_world\entities\itembase\codelock.c:3` to `:4`, used at `:221` |
| Combination lock faces | Selections on the lock item | `lock_attached_outside`, `lock_attached_inside` | `P:\scripts\4_world\entities\itembase\combinationlock.c:27` to `:28` |
| Bunker crate spawn | `BroadcastedBunker` | `storagecratepos`, `storagecratedir` | `P:\scripts\4_world\entities\building\bunker.c:175`, `:316` |

## Combination lock

In 1.30 matching the dials is not enough: `ActionCombinationLockUnlock` has to run (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actioncombinationlockunlock.c:1`, text `#detach_combination_lock`, command `CMD_ACTIONMOD_OPENDOORFW`). The inside and outside faces (`FACING_OUTSIDE` 0, `FACING_INSIDE` 1, `combinationlock.c:29` to `:30`) have separate combinations. Before 1.30 matching the last dial unlocked and dropped the lock (not checked on `P:\`).

`OnStoreSave` writes `m_Combination`, `m_CombinationLocked` and `m_CombinationInside` in that order (`P:\scripts\4_world\entities\itembase\combinationlock.c:129` to `:137`). `OnStoreLoad` reads `m_CombinationInside` only when `version >= 143` (`:169`).

## Code lock

| Fact | Value | Source |
|---|---|---|
| Class | `DigitalCodeLock` in script and config (`Inventory_Base`, model `\dz\gear_takistan\camping\codelock.p3d`); the bunker's `DigitalCodeLock_Bunker` inherits it | `P:\scripts\4_world\entities\itembase\codelock.c:1`; `P:\DZ\gear_takistan\camping\config.cpp:19`, `:315` |
| Parts | A `CodeLockComponent` and a `CodeLockVisualManager` | `codelock.c` |
| Battery | Slot `BatteryD` (`ATTACHMENT_SLOT_BATTERY`), takes a `Battery9V` | `codelock.c:6` |
| PIN length | 4 to 6 digits | `P:\scripts\4_world\classes\codelockcomponent.c:23` to `:24` |
| Stages | `CodeLockStage`: `NONE`, `NORMAL`, `SETTING`, `PROTECTION_STAGE_ONE`, `PROTECTION_STAGE_TWO` | `codelockcomponent.c:4` |
| Menu layout | `"gui/layouts/day_z_digital_lock.layout"` | `P:\scripts\5_mission\gui\digitalcodelockui.c:127` to `:129` |
| Save order | `m_LockPIN` (string), `m_IsLocked` (bool), `m_DoorIndex` (int) | `codelockcomponent.c:257` to `:262` |

Brute force limits come from `cfggameplay.json` through `CfgGameplayHandler`: `GetExternalLockProtectionTime`, `GetExternalLockProtectionResetTime`, `GetExternalLockProtectionCountStageOne` and `GetExternalLockProtectionCountStageTwo` (`P:\scripts\3_game\cfggameplayhandler.c:513` to `:528`; used at `codelockcomponent.c:66` to `:67` and `:474` to `:479`). There is no `GetExternalLockProtectionTimeStageOne`. The save and load rules are in `_shared/persistence/save-load-contract.md`.

## Bunker door

`Bunker` overrides `CanDoorBeOpened(DoorManipulationParams)` for its main door (`P:\scripts\4_world\entities\building\bunker.c:47` to `:62`). From inside it runs `MemPointDirectionalCheck` from `<m_DoorType>_action` to `<m_DoorType>_inside`; from outside it needs `m_IsActive` and an unlocked `DigitalCodeLock_Bunker`. Either way the base check must pass too.

The main door closes itself after `DOOR_AUTOCLOSE_TIME`, 12 s (`bunker.c:3`, timer started in `OnDoorOpenStart` at `:73` to `:84`), and `OnDoorCloseStart` locks the code lock again (`:86` to `:90`). `BroadcastedBunker` finds or creates its `DigitalCodeLock_Bunker` on the slot named by `CODE_LOCK_ATTACHMENT_NAME`, `"att_codelock"` (`:174`; `ResolveCodeLock` at `:192` to `:206`).

## Doors of houses that can be rebuilt

`Rebuilding.OnConstructionDoorOpenStart` and `OnConstructionDoorCloseStart` set the phase of `doorConstructionPhysicsSource` to 1.0 and 0.0 (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:439` to `:461`). Set `doorConstructionPart` and `doorConstructionPhysicsSource` on the Doors child when the door is a construction part that can be rebuilt.

## Moving a 1.29 door mod to 1.30

Vanilla Open no longer calls `CanDoorBeOpened(int, bool)`; that form only wraps the params form (`P:\scripts\3_game\entities\building.c:160` to `:167`). Every vanilla override uses the `DoorManipulationParams` form and calls `super` first, `Land_WarheadStorage_Main` and `Land_WarheadStorage_Bunker_Facility` included (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_main.c:352` to `:355`; `P:\scripts\4_world\entities\building\underground\land_warheadstorage_bunker_facility.c:20` to `:23`).

| What breaks | Severity | Fix |
|---|---|---|
| An override of `CanDoorBeOpened(int, bool)` is skipped by vanilla Open | High | Override the `DoorManipulationParams` form and call `super` (`door-open-and-lock-code.md`). |
| The door opens from the wrong side, or Open never appears | Medium | Add the Memory points named in `interactPositionPoint` and `interactDirPoint`, or leave both keys out. |
| The lockpick is still offered on a padlocked door | Medium | Set `relatedInventorySlots[]` on that Doors entry. |
| A custom combination lock unlocks on the last dial | Medium | Run `ActionCombinationLockUnlock` after the dials match, and read `m_CombinationInside` when `version >= 143`. |
| A lock never attaches to a custom building | High | Declare the slots on the entity, a `class Construction`, the selections `att_codelock` and `att_combinationlock`, and `relatedInventorySlots[]` on the door. |

- [ ] Search the mod for `CanDoorBeOpened(` and move building overrides to the `DoorManipulationParams` form.
- [ ] A door that takes a lock has `attachments[]`, `class Construction` on the entity, `relatedInventorySlots[]` and the Memory slot selections.
- [ ] Nothing treats `EBuildingLockType` as the combination or code lock API.
- [ ] Combination lock mods run `ActionCombinationLockUnlock` and read `m_CombinationInside` from version 143.
- [ ] Doors that can be rebuilt set `doorConstructionPart` and `doorConstructionPhysicsSource`.
