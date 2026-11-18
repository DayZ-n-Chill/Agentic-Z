# Inventory script in DayZ 1.30

How DayZ 1.30 runs inventory commands, where a mod can still watch item moves, how stacking and splitting differ from a move, and which take calls and hand guards changed. The full list of 1.30 changes is in `dayz-1-30-enforce-script.md`.

## Retail no longer calls `ProcessInputData`

In 1.29 one `ProcessInputData(ParamsReadContext ctx, bool is_juncture, bool is_remote)` ran every inventory command. In 1.30 it still exists (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:3319`), but its callers sit inside `#ifdef DIAG_DEVELOPER` and also need `PluginInventoryDebug.IsOldProcessInputDataEnable()` (`:669`). Retail runs these instead:

| Method | Role | Source |
|---|---|---|
| `bool ValidateInventoryCommandServer(ParamsReadContext ctx)` | Server checks a juncture | `dayzplayerinventory.c:3410` |
| `bool ExecuteInventoryCommandServer(ParamsReadContext ctx)` | Server runs the command | `:3501` |
| `bool ExecuteInventoryCommandClient(ParamsReadContext ctx)` | Owning client, after the juncture | `:3569` |
| `bool ExecuteInventoryCommandRemote(ParamsReadContext ctx)` | Other clients | `:3633` |

Input user data goes through the same diag gate (`:734` to `:744`), then `ValidateInventoryCommandServer` on the server.

### Desync check

`const int INPUT_UDT_INVENTORY_CHECK = 16;` (`P:\scripts\3_game\tools\component\_constants.c:19`) is handled by `OnInventoryCheck(int userDataType, ParamsReadContext ctx)` (`dayzplayerinventory.c:5003`). On a mismatch it calls `InventoryInputUserData.SendServerInventoryCheck` (`:5052`), gated by `IsDesyncRepairEnable` (`:5048` to `:5055`). The repair is capped by `INVENTORY_REPAIR_MAX_DISTANCE = 500.0` and `INVENTORY_REPAIR_MAX_ITEMS = 5` (`:163` and `:164`).

## Engine classes that cannot be modded

`modded class DayZPlayerInventory` does not compile in 1.30: the server log reads `Engine class 'DayZPlayerInventory' cannot be modded.` and `Can't compile "World" script module!` (measured in game). `modded class Magazine` fails the same way. `modded class Ammunition_Base` (`P:\scripts\4_world\entities\itembase\magazine\ammunitionpiles.c:2`) compiles. The validator rule `ES-MODDED-ENGINE-CLASS` lists the classes known to refuse.

## Watching item moves

Override `EEItemLocationChanged(notnull InventoryLocation oldLoc, notnull InventoryLocation newLoc)` (`P:\scripts\3_game\entities\entityai.c:976`; `ItemBase` override at `P:\scripts\4_world\entities\itembase.c:987`) from a `modded class ItemBase`. Measured in game, it fires for moves the client starts with `PredictiveTakeEntityToHands`, `PredictiveTakeEntityToTargetCargo` and `PredictiveTakeEntityToTargetAttachment`, and for moves made by actions:

| Move | Old location to new |
|---|---|
| Crate cargo to hands, hands to crate cargo, one crate to another | `CARGO` and `HANDS` both ways, `CARGO` to `CARGO` |
| `SparkPlug` out of and into a `PowerGenerator` on the ground | `ATTACHMENT` and `HANDS` both ways |
| `WoodenPlank` out of and into the `RB_LvL1_Plank` slot of a `Land_House_1M1` | `ATTACHMENT` and `HANDS` both ways |
| `WoodenCrate` picked up, then dropped | `GROUND` to `HANDS`, `HANDS` to `GROUND` |

- A swap into hands that already hold an item of the same type gives two callbacks in the same tick, one per item.
- Items the server creates in a container (`CreateInInventory`, `CreateAttachmentEx`) arrive with an `oldLoc` that has no parent, the shape of a creation. A container picked up from the ground also has a parentless `oldLoc`, so tell them apart by more than that.
- Neither location names the player for a move between two world objects. `g_Game.HasInventoryJuncture(Man player, EntityAI item)` (`P:\scripts\3_game\global\game.c:758`) called inside the callback returned true for the player who moved an item between crates (one move measured). Moves made by server script without a juncture, and several players near the crate, are unverified.

No moddable replacement for rejecting an inventory command is known.

## Stacking and splitting are not moves

A combine moves quantity, not an item, and a split creates a new item, so neither fires as a move from one parent to another.

- `ItemBase.CombineItems` moves the quantity (`P:\scripts\4_world\entities\itembase.c:2247` to `:2270`). `Magazine.CombineItems` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:317`) overrides it without calling `super`, so ammo piles take their own path. Measured in game: wrapping `CombineItems` in a `modded class ItemBase` and in a `modded class Ammunition_Base`, and reading the receiver's quantity before and after `super`, gives one result per combine with the moved quantity, for `Ammo_762x39` stacked onto a pile in a crate and for `WoodenPlank` stacked onto the plank in a house slot.
- The `ItemBase` split functions (`itembase.c:1584` to `:1953`) mark the new item with `SetResultOfSplit(true)` (ten calls, `:1604` to `:1937`; defined at `:2209`), except `SplitItem` (`:1953`). It creates the copy through `PlayerBase.CreateCopyOfItemInInventoryOrGroundEx` (`P:\scripts\4_world\entities\manbase\playerbase.c:6888` to `:6899`), which marks it only when the copy lands on the ground, not when it goes to the player's cargo (`CreateCopyOfItemInInventory`, `:6856`). To audit `SplitItem`, compare the source quantity before and after `super`; unverified in game.
- `Magazine`'s own `SplitItemToInventoryLocation` and `SplitItem` (`magazine.c:231`, `:256`) never call `SetResultOfSplit`. The server's item handler calls the split functions from `PlayerBase` (`playerbase.c:6640` to `:6725`).
- `SplitIntoStackMaxHands` (`itembase.c:1889`) does nothing when the whole stack fits in the hands (`ShouldSplitQuantity`), so it only splits a stack larger than the hand stack. `SplitItemToInventoryLocation` (`:1917`) splits half toward a given destination.

## Take calls

The 1.29 takes are `[Obsolete]` wrappers in 1.30 (`P:\scripts\3_game\systems\inventory\inventory.c:1345` to `:1386`):

| Obsolete | Line | Use instead | Line |
|---|---|---|---|
| `TakeEntityToCargo(mode, item)` | `:1345` | `TakeEntityToTargetCargo(mode, target, item)` | `:1077` |
| `TakeEntityToCargoEx` | `:1357` | `TakeEntityToTargetCargoEx(mode, cargo, item, row, col)` | `:1084` |
| `TakeEntityAsAttachmentEx` | `:1374` | `TakeEntityAsTargetAttachmentEx(mode, target, item, slot)` | `:1100` |
| `TakeEntityAsAttachment` | `:1382` | `TakeEntityAsTargetAttachment(mode, target, item)` | `:1142` |

The return value still does not prove success; test `FindAttachment(slot) == item` (see `api-patterns.md`, section "A take call's return value is not success").

## Hand guards

In 1.29 `HandGuardCanMove`, `HandGuardCanSwap` and `HandGuardCanForceSwap` passed on `e.m_IsJuncture || e.m_IsRemote`. In 1.30 only `e.m_IsRemote` passes; otherwise they ask `GameInventory.LocationCanMoveEntity`, `CanSwapEntitiesEx` or `CanForceSwapEntitiesEx` (`P:\scripts\3_game\systems\inventory\hand_guards.c:299`, `:325`, `:351`).

The new `HandGuardIsNotSurrendered` (`:405`) returns `!m_Player.IsSurrendered()` (`:412`), so hand events on a surrendered player fail.

## Attachment groups and item type data

`TypeAttachmentGroupsDataHolder` reads `GUIInventoryAttachmentsProps` under the class's config path and stops if it is missing (`P:\scripts\3_game\entities\typeattachmentgroupdataholders.c:39`). The category row reaches 1.5 m, with a vertical allowance of `-range/5`, so minus 0.3 m (`P:\scripts\5_mission\gui\inventorynew\inherited\attachmentcategoriesrow.c:764`).

`ItemBaseType` (`typedef ItemBaseType Inventory_BaseType`, `P:\scripts\4_world\entities\itembasetype.c:1` to `:4`) caches type config: `varWetMax` (`:71`), `itemModelLength` and `itemAttachOffset` (`:86` to `:92`), `compatibleLocks` and `lockType` (`:96` to `:99`), `headSelectionsToHide` (`:105` to `:108`), `hideSelectionsByinventorySlot` (`:111` to `:113`), `quickBarBonus` (`:115`), `temperaturePerQuantityWeight` (`:117` to `:119`) and the soaking and drying `EnvironmentWetnessIncrements` (`:121` to `:137`). The full key table is in `config-cpp.md`.
