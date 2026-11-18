# Entity, item and inventory calls

Where the common entity, player, item and inventory calls are declared: attach and detach hooks, showing and hiding selections, slot lists, texture getters, type checks, player stats, inventory moves and quantity, and what 1.30 renamed. Short facts on items are in `../references/item_api.md` and on inventory in `../references/api_entities_inventory.md`.

## Attach and detach hooks on the item

`OnWasAttached(EntityAI parent, int slot_id)` and `OnWasDetached(EntityAI parent, int slot_id)` fire on the item when it goes into or leaves a parent's slot (`P:\scripts\3_game\entities\entityai.c:1864` and `:1867`). The parent side is `EEItemAttached` and `EEItemDetached`. Vanilla overrides them in `P:\scripts\4_world\entities\core\inherited\inventoryitem.c` (`:82`, `:150`, `:502`, `:542`, `:1093`), `P:\scripts\4_world\entities\core\inherited\itemoptics.c` (`:287`, `:300`) and `P:\scripts\4_world\entities\explosivesbase\plastic_explosive.c` (`:148`, `:160`). `OnMovedWithinCargo(EntityAI container)` is at `entityai.c:1375`.

```c
override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
}

override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
}
```

## Showing and hiding selections

`ShowSelection(string selection_name)` and `HideSelection(string selection_name)` on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:3364` and `:3355`). `huntingoptic.c` overrides them (`P:\scripts\4_world\entities\itembase\inventory_base\huntingoptic.c:34` and `:44`).

To show a lighter model while attached and the full model on the ground, toggle two named selections from the attach hooks:

```c
void MyMod_Item()
{
    ShowSelection("not_attached");   // the ground model by default
    HideSelection("attached");
}

override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
    HideSelection("not_attached");
    ShowSelection("attached");
}

override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
    ShowSelection("not_attached");
    HideSelection("attached");
}
```

The two selections live in the `.p3d`, and `model.cfg` pairs them through an animation source. The model side is in `_shared/animation/attach-state-parts.md`, section "Two models in one item: swap by attach state". The script calls are checked on `P:\`; the `model.cfg` wiring is not, so compare it with a vanilla item that has two models, such as the flag.

## Which slot list to read

Two `GameInventory` pairs look alike but answer opposite questions:

| Pair | Answers | Source |
|---|---|---|
| `GetSlotIdCount()`, `GetSlotId(i)` | "number of slots this item can belong to": where this item attaches on another parent | `P:\scripts\3_game\systems\inventory\inventory.c:167` to `:175` |
| `GetAttachmentSlotsCount()`, `GetAttachmentSlotId(i)` | "number of slots for attachments": the slots this entity declares | `inventory.c:176` to `:184` |

To list the attachment slots an entity has, always use `GetAttachmentSlotsCount()` and `GetAttachmentSlotId(i)`.

The wrong pair doesn't throw. On `CivilianSedan`, which attaches to nothing, `GetSlotIdCount()` returns 1 with an invalid id, and `InventorySlots.GetSlotName(id)` (`P:\scripts\3_game\systems\inventory\inventoryslots.c:48`) returns `""`. The result is `[""]`, one empty name, which looks like a data bug. An empty slot name on an entity that clearly has attachments means the wrong pair.

## Texture and material getters

There is no `GetObjectTextures()`. The run time getters are singular and take an index: `GetObjectTexture(int)` and `GetObjectMaterial(int)` (`P:\scripts\3_game\entities\entityai.c:2882` to `:2885`). For every hidden selection, loop from 0 to `GetHiddenSelections().Count() - 1`.

The config getters are `GetHiddenSelectionsTextures()` and `GetHiddenSelectionsMaterials()` (`P:\scripts\3_game\entities\object.c:125` to `:140`). For the material list embedded in a model, use `GetObjectMaterials(vobject object, string materials[])` (`P:\scripts\1_core\proto\envisual.c:6` to `:27`). A call to a getter that doesn't exist stops the whole script module compiling.

## Type checks and transforms

| Call | On | Source |
|---|---|---|
| `IsMan()`, `IsItemBase()` | `Object` | `P:\scripts\3_game\entities\object.c:523` and `:553` |
| `IsBuilding()`, `IsTransport()` | `Object` | `object.c:642` and `:686` |
| `GetSpeed()`, the velocity in world space | `Object` | `object.c:335` |
| `IsAnimal()`, `IsZombie()` | `EntityAI` | `P:\scripts\3_game\entities\entityai.c:734` and `:739` |
| `GetTransform(out vector mat[])`, `SetTransform(vector mat[4])` | `IEntity` | `P:\scripts\1_core\proto\enentity.c:288` and `:356` |

`ProcessDirectDamage` and its damage zone argument are in `../references/api_recipes_energy_damage.md`.

## Player state

`GetStatWater()`, `GetStatEnergy()` and `GetStatHeatComfort()` return a `PlayerStat<float>` (`P:\scripts\4_world\entities\manbase\playerbase.c:8197`, `:8215`, `:8224`). Read it with `.Get()`, write it with `.Set(value)` or `.Add(value)` (`Set(T value, string system = "")` at `P:\scripts\4_world\classes\playerstats\playerstatbase.c:85`, `Add` at `:129`).

`GetBrokenLegs()` returns `eBrokenLegs` (`playerbase.c:3966`), one of `NO_BROKEN_LEGS`, `BROKEN_LEGS` and `BROKEN_LEGS_SPLINT` (`P:\scripts\3_game\enums\ebrokenlegs.c:1` to `:6`). `IsControlledPlayer()` is true only on the client that controls this character (`P:\scripts\4_world\entities\manbase.c:8` to `:13`).

## Inventory

`GameInventory` (`P:\scripts\3_game\systems\inventory\inventory.c:80`):

| Call | Line |
|---|---|
| `GetCargo()`, a `CargoBase` with `GetItemCount()` and `GetItem(int)` (`P:\scripts\3_game\systems\inventory\cargo.c:28` and `:32`) | `:138` |
| `CreateEntityInCargo(string)` | `:143` |
| `CanAddEntityInCargo(EntityAI e, bool flip)` | `:154` |
| `AttachmentCount()` | `:205` |
| `CreateAttachment(string)` | `:209` |
| `GetAttachmentFromIndex(int)` | `:220` |
| `CanAddAttachment(EntityAI e)` | `:241` |
| `FindFreeLocationFor(EntityAI item, FindInventoryLocationType flags, out InventoryLocation loc)` | `:276` |
| `CreateInInventory(string)` | `:876` |
| `TakeEntityToInventory(InventoryMode mode, FindInventoryLocationType flags, EntityAI item)` | `:1013` |

- `InventoryMode` is `PREDICTIVE`, `LOCAL`, `JUNCTURE` or `SERVER` (`inventory.c:21` to `:27`); use `SERVER` only in code that runs on the server alone. `FindInventoryLocationType` is `ATTACHMENT`, `CARGO`, `HANDS`, `PROXYCARGO`, `ANY_CARGO`, `ANY` and `NO_SLOT_AUTO_ASSIGN` (`P:\scripts\3_game\systems\inventory\inventorylocation.c:17` to `:26`).
- `HumanInventory.CreateInHands(string)` (`P:\scripts\3_game\systems\inventory\humaninventory.c:44`); `InventoryLocation.SetCargo(EntityAI parent, EntityAI e, int idx, int row, int col, bool flip)` (`inventorylocation.c:152`).
- Player moves on `Man` (`P:\scripts\3_game\entities\man.c`): `PredictiveTakeEntityToHands(EntityAI)` `:178`, `PredictiveTakeEntityToInventory(FindInventoryLocationType, EntityAI)` `:381`, `ServerTakeEntityToInventory(FindInventoryLocationType, EntityAI)` `:402`, `PredictiveTakeToDst(InventoryLocation src, InventoryLocation dst)` `:738`.
- Item hooks: `ItemBase.OnInventoryEnter(Man)` and `OnInventoryExit(Man)` (`P:\scripts\4_world\entities\itembase.c:3902` and `:3914`).
- Quantity on `ItemBase`: `SetQuantity(...)` `:3315`, `AddQuantity(...)` `:3389`, `GetQuantityMax()` `:3435`, `GetQuantity()` `:3486` (`itembase.c`). Rounds in a magazine: `Magazine.GetAmmoCount()` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:68`).

## What 1.30 renamed

| Old call, now `[Obsolete]` | Use instead | Source |
|---|---|---|
| `TakeEntityToCargo`, `TakeEntityToCargoEx`, `TakeEntityAsAttachment`, `TakeEntityAsAttachmentEx` | `TakeEntityToTargetCargo` `:1077`, `TakeEntityToTargetCargoEx` `:1084`, `TakeEntityAsTargetAttachmentEx` `:1100`, `TakeEntityAsTargetAttachment` `:1142` | `P:\scripts\3_game\systems\inventory\inventory.c:1345` to `:1386` |
| `OnCEUpdate()` | `OnCEIterate(float currentTime, float elapsedTime)` | `P:\scripts\3_game\entities\entityai.c:3904`, `:4924` and `:4925` |

New in 1.30: `DayZPlayer.IsFirstRenderFrame()`, true on the first tick of a render frame (`P:\scripts\3_game\dayzplayer.c:1186` to `:1189`), and `Entity.DisableSimulation(bool)` with `GetIsSimulationDisabled()` (`P:\scripts\3_game\entities\entity.c:3` to `:6`).
