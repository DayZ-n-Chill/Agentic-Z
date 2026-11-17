# Reference: creating entities and working with inventory

Spawning objects in the world or in an inventory, finding items, moving them and deleting them. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`). Spawning, deleting and moving items is server work (`_shared/conventions/scripts.md`). Making spawned items fall and settle is in `patterns/physics_items.md`.

## Creating in the world

| Call | Use | Source |
|---|---|---|
| `GetGame().CreateObjectEx(type, pos, flags, rotation = RF_DEFAULT)` | The main spawn call. `flags` are `ECE_*` values. | `P:\scripts\3_game\global\game.c:703` |
| `GetGame().CreateObject(type, pos, create_local = false, init_ai = false, create_physics = true)` | The older form with bool switches. | `:691` |
| `SpawnEntity(type, inventoryLocation, ECE_*, RF_*)` | Creates an entity at an `InventoryLocation`, ground or inventory. | `P:\scripts\3_game\gameplay.c:1526` |
| `entity.SpawnEntityOnGroundPos(type, pos)` | Ground spawn with `ECE_PLACE_ON_SURFACE`. | `P:\scripts\3_game\entities\entityai.c:2138` |

Both `CreateObject` calls return `Object`; cast to what you need:

```c
ItemBase newItem = ItemBase.Cast(g_Game.CreateObjectEx(itemType, dropPos, ECE_PLACE_ON_SURFACE));
```

Source: `P:\scripts\4_world\classes\constructionbase.c:1319`.

### Common `ECE_*` flags (`P:\scripts\3_game\ce\centraleconomy.c`)

| Flag | Meaning | Line |
|---|---|---|
| `ECE_PLACE_ON_SURFACE` | Physics, navmesh update and a trace down to the ground. The usual choice for ground items. | 38 |
| `ECE_SETUP` | Full entity setup for a new entity. | 9 |
| `ECE_CREATEPHYSICS` | Build collision and physics data. | 17 |
| `ECE_KEEPHEIGHT` | Keep the given height; no trace or surface placement. | 28 |
| `ECE_NOSURFACEALIGN` | Do not tilt to the terrain. | 27 |
| `ECE_EQUIP`, `ECE_EQUIP_ATTACHMENTS`, `ECE_EQUIP_CARGO` | Spawn with the configured attachments and cargo. | 21 to 23 |
| `ECE_IN_INVENTORY` | The set used for items created in an inventory. | 37 |
| `ECE_LOCAL` | Create on this machine only, never networked. For client previews and effects. | 25 |
| `ECE_NOLIFETIME`, `ECE_NOPERSISTENCY_WORLD` | No Central Economy lifetime; not saved in the world. | 30, 31 |
| `ECE_FULL` | Setup, trace, rotation flags, navmesh and equip together. | 41 |

Rotation flags are `RF_*` (`centraleconomy.c:46` to `:66`); `RF_DEFAULT` (512) uses the placement set in the object's config.

Two flag sets (the flags were checked on `P:\`; the behaviour was measured in game and not re-run here):

- **Infected and animals need `ECE_INITAI`** (`P:\scripts\3_game\ce\centraleconomy.c:18`). `ECE_PLACE_ON_SURFACE | ECE_INITAI | ECE_CREATEPHYSICS` gives a creature that walks and attacks; without `ECE_INITAI` it stands like a statue. Add `ECE_NOPERSISTENCY_WORLD` (`P:\scripts\3_game\ce\centraleconomy.c:31`) so a restart removes it. The surface placement of an AI is deferred: `GetPosition()` right after the call still returns the height you asked for.
- **A client can create a preview only with `ECE_LOCAL`** (`P:\scripts\3_game\ce\centraleconomy.c:25`); without it the client's `CreateObjectEx` returns `null`. The preview has no network ID and the server never sees it. To make it inert, cast to `EntityAI` before `DisableSimulation(true)`: the method is declared on `Entity` (`P:\scripts\3_game\entities\entity.c:3`), not on `Object`. Do not do this to a local infected or animal: making it inert crashed the client, and so did leaving it simulating for a second or two.

More creation and placement traps (raycasts, surface normals, scaled local segments): `skills/enforce-script-reference/references/api-patterns.md`.

## Creating inside an inventory

| Call | Behaviour | Source |
|---|---|---|
| `entity.GetInventory().CreateInInventory(type)` | First free cargo or attachment place. Returns `null` when there is none. | `P:\scripts\3_game\systems\inventory\inventory.c:876` |
| `player.GetHumanInventory().CreateInInventory(type)` | As above, then falls back to the hands. | `P:\scripts\3_game\systems\inventory\humaninventory.c:65` |
| `player.CreateInInventory(type)` | `PlayerBase` helper that searches every location type. | `P:\scripts\4_world\entities\manbase\playerbase.c:6846` |
| `GetInventory().CreateAttachment(type)` / `CreateAttachmentEx(type, slotId)` | As an attachment, in any slot or in one slot. | `inventory.c:209`, `:215` |
| `GetInventory().CreateEntityInCargo(type)` / `CreateEntityInCargoEx(type, idx, row, col, flip)` | In cargo. | `inventory.c:143`, `:150` |
| `player.GetHumanInventory().CreateInHands(type)` | In the hands. | `humaninventory.c:44` |
| `entity.SpawnInInventoryOrGroundPos(type, inv, pos)` | Inventory first, ground if full. | `P:\scripts\3_game\entities\entityai.c:2122` |

Always null check the result: a full inventory returns `null`.

Reported (measured on DayZDiag 1.29, not checked on `P:\`): an attachment made with `CreateAttachmentEx` inside the parent's `EEInit`, or in the same tick as the parent's `CreateObjectEx`, exists on the server but never reaches clients. Created one second later through `GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(fn, 1000, false)` it shows at once. Stock a new entity from the code that created it, with a delayed call and a saved "stocked" flag.

## Reading an inventory

| Call | Returns | Source (`3_game\systems\inventory\inventory.c`) |
|---|---|---|
| `GetInventory().EnumerateInventory(InventoryTraversalType.PREORDER, out items)` | Every item, recursively, in `items`. | `:127`; traversal types at `P:\scripts\3_game\gameplay.c:4` |
| `GetInventory().CountInventory()` | The same count without the array. | `:134` |
| `GetInventory().HasEntityInInventory(item)` | Whether `item` is anywhere inside. | `:118` |
| `GetInventory().AttachmentCount()` / `GetAttachmentFromIndex(i)` | Attachments by index. The index is not a slot ID. | `:205`, `:220` |
| `GetInventory().FindAttachment(slotId)` / `FindAttachmentByName("Slot")` | The attachment in a slot. | `:224`, `:228` |
| `InventorySlots.GetSlotIdFromString("Shoulder")` | A slot ID from its name. | `P:\scripts\3_game\systems\inventory\inventoryslots.c:42` |
| `GetInventory().GetCargo()` | The cargo container. | `:138` |
| `GetInventory().CanAddAttachment(e)` / `CanAddEntityInCargo(e, flip)` | Whether it would fit. | `:241`, `:154` |
| `GetInventory().GetInventoryOwner()` | The entity that owns this inventory. | `:92` |
| `player.GetHumanInventory().GetEntityInHands()` | The item in the hands. `Man.GetEntityInHands()` is the same. | `P:\scripts\3_game\systems\inventory\humaninventory.c:16`, `P:\scripts\3_game\entities\man.c:83` |
| `item.GetHierarchyRoot()`, `GetHierarchyParent()`, `GetHierarchyRootPlayer()` | Who holds an item. | `P:\scripts\3_game\entities\entityai.c:879`, `:885`, `:882` |

Check each entry of the array `EnumerateInventory` fills before you use it. Vanilla does: after `EnumerateInventory(InventoryTraversalType.LEVELORDER, children)` (`P:\scripts\4_world\static\miscgameplayfunctions.c:131`) it tests `if (child)` (`P:\scripts\4_world\static\miscgameplayfunctions.c:136`). A 1.30 diag server threw a `NULL pointer to instance` exception when an unchecked entry was passed to `HasInventoryJunctureItem`, whose parameter is `notnull` (`P:\scripts\3_game\global\game.c:757`).

Two pairs of slot calls on `GameInventory` look alike and answer opposite questions:

| Pair | What it answers | Source |
|---|---|---|
| `GetAttachmentSlotsCount()` / `GetAttachmentSlotId(i)` | Which attachment slots this entity declares, for its own attachments. | `P:\scripts\3_game\systems\inventory\inventory.c:176-184` |
| `GetSlotIdCount()` / `GetSlotId(i)` | Which slots this item can itself go into on some other parent. | `P:\scripts\3_game\systems\inventory\inventory.c:167-175` |

To list the slots of a container or a vehicle, use the first pair. The second pair on such an entity does not fail: measured in game, a `CivilianSedan` returned a count of 1 with an invalid ID, for which `InventorySlots.GetSlotName(id)` (`P:\scripts\3_game\systems\inventory\inventoryslots.c:48`) gives `""`. A list holding one empty slot name on an entity that clearly has attachments means the wrong pair was used.

`GetObjectsAtPosition3D` (`P:\scripts\3_game\global\game.c:930`) returns terrain objects such as bushes, whose `GetType()` is empty, mixed in with players, items, vehicles and infected (measured in game: 38 objects in a 30 m radius on open ground). Filter by type when you want entities only.

## Moving items

The inventory mode decides who runs the move (`P:\scripts\3_game\systems\inventory\inventory.c:20` to `:27`):

| Mode | Use |
|---|---|
| `SERVER` | The move runs only on the server, which may create or destroy objects. The mode for mod server code. |
| `JUNCTURE` | Moves that could race, such as two players taking the same item from the ground. |
| `LOCAL` | Changes only the copy on the machine that runs it. |
| `PREDICTIVE` | Client side prediction; vanilla notes it is not to be used at all in multiplayer. |

The `EntityAI` wrappers pick the mode for you. Since 1.30 vanilla comments mark the untargeted forms as replaced by the `...TargetInventory` forms (`P:\scripts\3_game\entities\entityai.c:1954`, `:1962`, `:1967`).

| Call | Source (`3_game\entities\entityai.c`) |
|---|---|
| `ServerTakeEntityToTargetInventory(target, FindInventoryLocationType.ANY, item)` | `:1983` |
| `ServerTakeEntityToCargo(item)` / `ServerTakeEntityAsAttachment(item)` | `:4849`, `:4907` |
| `ServerTakeToDst(srcLocation, dstLocation)` | `:2063` |
| `ServerDropEntity(item)` | `:2078` |
| `PredictiveTakeEntityToTargetInventory(...)` uses `JUNCTURE` in multiplayer and `PREDICTIVE` offline | `:1972` to `:1978` |

`FindInventoryLocationType` is `ATTACHMENT`, `CARGO`, `HANDS`, `PROXYCARGO`, `ANY_CARGO` or `ANY` (`P:\scripts\3_game\systems\inventory\inventorylocation.c:17`). An `InventoryLocation` names one exact place (ground, attachment slot, cargo cell or hands); `GetInventory().FindFreeLocationFor(item, flags, out loc)` finds one (`inventory.c:276`).

The return value of a take call is not proof that the item moved. When the target slot is already occupied, `TakeEntityAsTargetAttachmentEx` combines the items and returns `true` without attaching the new one: it reads the slot with `FindAttachment(slot)` first (`P:\scripts\3_game\systems\inventory\inventory.c:1106` to `:1118`). After a scripted attach, confirm with `FindAttachment(slot) == item`, comparing the entity and not its type. A trace of the local take path on a live player, which returns `true` in every case, is in `skills/enforce-script-reference/references/api-patterns.md`.

### Merging stacks in a loop: skip a stack that is already emptied

`ItemBase.CombineItems` (`P:\scripts\4_world\entities\itembase.c:2243`) empties the donor through `SetQuantity`, and for an item with `varQuantityDestroyOnMin` that call ends in `this.Delete()` (`P:\scripts\4_world\entities\itembase.c:3333-3338`). `EntityAI.Delete()` only sets `m_PendingDelete` and the object is removed on the next frame (`P:\scripts\3_game\entities\entityai.c:779-782`). Until then the empty stack is still in the cargo, and `CanBeCombined` (`P:\scripts\4_world\entities\itembase.c:2137`) has no check for a pending delete, so a loop that merges several stacks in one call can pick the empty stack as its next target and pour live quantity into an object that is about to disappear. Three rag stacks of 2, 2 and 5 can end as 6 rags instead of 9. In such a loop skip, as target and as donor, any item for which `IsSetForDeletion()` is true (`P:\scripts\3_game\entities\entityai.c:812-814`), and any `Magazine` pile whose `GetAmmoCount()` is 0. This is a static trace through the vanilla scripts, not reproduced in game.

## Position and orientation

`GetPosition()`, `SetPosition(pos)`, `GetOrientation()` and `SetOrientation(ypr)` take degrees for yaw, pitch and roll; `PlaceOnSurface()` drops an object onto the surface below (`P:\scripts\3_game\entities\object.c:287`, `:294`, `:305`, `:311`, `:299`). `GetType()` is the config class name (`object.c:467`).

## Deleting

`Delete()` queues the delete for the next frame; `DeleteSafe()` handles items held by a live player. Details are in `language_memory.md`, section "Deleting entities".
