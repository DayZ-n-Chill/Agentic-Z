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

## Position and orientation

`GetPosition()`, `SetPosition(pos)`, `GetOrientation()` and `SetOrientation(ypr)` take degrees for yaw, pitch and roll; `PlaceOnSurface()` drops an object onto the surface below (`P:\scripts\3_game\entities\object.c:287`, `:294`, `:305`, `:311`, `:299`). `GetType()` is the config class name (`object.c:467`).

## Deleting

`Delete()` queues the delete for the next frame; `DeleteSafe()` handles items held by a live player. Details are in `language_memory.md`, section "Deleting entities".
