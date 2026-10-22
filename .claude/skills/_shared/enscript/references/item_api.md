# Reference: ItemBase API

`ItemBase` is the base for held and inventory items (`class ItemBase extends InventoryItem`, `P:\scripts\4_world\entities\itembase.c:23`), so code that names it lives in `4_world` or later. Many of its methods are declared on `EntityAI` or `Object` and inherited. Each fact below cites the vanilla file on `P:\scripts\` it was checked against.

---

## Contents

- [Quantity (liquid, stackable)](#quantity-liquid-stackable)
- [Health (damage zones)](#health-damage-zones)
- [Wetness and temperature](#wetness-and-temperature)
- [Inventory position and attachments](#inventory-position-and-attachments)
- [Spawning items](#spawning-items)
- [Registering actions](#registering-actions)
- [config.cpp properties](#configcpp-properties)
- [Casts](#casts)
- [Magazines: `ServerSetAmmoCount`, not `SetQuantity`](#magazines-serversetammocount-not-setquantity)
- [`SetObjectTexture`](#setobjecttexture)

## Quantity (liquid, stackable)

| Call | What it does | Source |
|---|---|---|
| `GetQuantity()` | Current quantity, `float`. | `P:\scripts\4_world\entities\itembase.c:3486` |
| `GetQuantityMin()`, `GetQuantityMax()` | Limits from config, `int`. | `:3470`, `:3435` |
| `GetQuantityNormalized()` | Quantity scaled to 0..1. | `:3416` |
| `HasQuantity()` | Whether the item uses quantity at all. | `:3481` |
| `SetQuantity(value, destroy_config = true, destroy_forced = false, allow_client = false, clamp_to_stack_max = true)` | Sets it; returns `bool`. Reaching 0 can delete the item, see the two `destroy` flags. | `:3315` |
| `AddQuantity(value, destroy_config = true, destroy_forced = false)` | Adds (or with a negative value takes) quantity; returns `bool`. | `:3389` |
| `GetLiquidType()`, `SetLiquidType(int value, bool allow_client = false)` | The liquid of a bottle or container, for example `LIQUID_WATER`. | `:3883`, `:3867` |
| `IsEmpty()` | No cargo and no attachments (declared on `EntityAI`), not "quantity is 0". | `P:\scripts\3_game\entities\entityai.c:646` |

```c
ItemBase item = ItemBase.Cast(entity);
if (item && item.HasQuantity())
    item.SetQuantity(item.GetQuantityMax());
```

---

## Health (damage zones)

Health calls take a zone name and a health type. `""` for both means the global zone's main health. Max health comes from the item's `DamageSystem` config, so it is not always 100.

| Call | Source |
|---|---|
| `GetHealth(zoneName, healthType)`, `GetHealth()` | `P:\scripts\3_game\entities\object.c:994`, `:1062` |
| `GetHealth01(zoneName, healthType)` (0..1) | `:1001` |
| `GetMaxHealth(zoneName, healthType)` | `:1008` |
| `SetHealth(zoneName, healthType, value)` | `:1015` |
| `AddHealth(zoneName, healthType, value)` | `:1027` |
| `DecreaseHealth(zoneName, healthType, value, auto_delete)` | `:1049` (the three argument form is `:1034`) |
| `SetHealthMax(zoneName = "", healthType = "")` | `:1105` |
| `GetHealthLevel(zone = "")` returns an `int` health level, `GameConstants.STATE_PRISTINE` (0) to `STATE_RUINED` (4) (`P:\scripts\3_game\constants.c:909`, `:913`) | `:1171` |
| `IsRuined()`, `IsDamageDestroyed()` | `:1219`, `:981` |

```c
item.SetHealth("", "", item.GetMaxHealth("", "") * 0.5);
item.DecreaseHealth("", "", 10, false);
```

---

## Wetness and temperature

| Call | Source |
|---|---|
| `GetWet()`, `SetWet(float value, bool allow_client = false)` | `P:\scripts\4_world\entities\itembase.c:3717`, `:3688` |
| `CanHaveTemperature()` | `P:\scripts\3_game\entities\entityai.c:3883` |
| `GetTemperature()` | `:2442` |
| `SetTemperatureDirect(value, allow_client = false)` | `:2293` |
| `SetTemperature(value, allow_client = false)`; vanilla notes it is missing the context `TemperatureData` gives, use `SetTemperatureEx(TemperatureData)` for that | `:2307` to `:2308`, `:2327` |

There is no `HasTemperature`, `IsDamaged` or `IsWorn` in vanilla script. Use `CanHaveTemperature()`, a `GetHealthLevel()` check, and the item's inventory location instead.

---

## Inventory position and attachments

| Call | Returns | Source |
|---|---|---|
| `GetHierarchyRootPlayer()` | The `Man` carrying it, or null. | `P:\scripts\3_game\entities\entityai.c:882` |
| `GetHierarchyParent()` | The direct parent entity, or null. | `:885` |
| `GetInventory().AttachmentCount()` | How many attachments it holds. | `P:\scripts\3_game\systems\inventory\inventory.c:205` |
| `GetInventory().GetAttachmentFromIndex(i)` | The attachment at that index. | `:220` |
| `GetInventory().GetAttachmentSlotsCount()` | How many attachment slots it has. | `:184` |
| `GetInventory().IsInCargo()` | True when it sits in the cargo of something. | `:397` |

```c
GameInventory inv = item.GetInventory();
for (int i = 0; i < inv.AttachmentCount(); i++)
{
    EntityAI att = inv.GetAttachmentFromIndex(i);
}
```

---

## Spawning items

Spawning and the `ECE_*` flags are in `api_entities_inventory.md`. Two helpers on `EntityAI`:

| Call | What it does | Source |
|---|---|---|
| `GetInventory().CreateInInventory(type)` | Creates the item anywhere it fits in this entity's inventory. | `P:\scripts\3_game\systems\inventory\inventory.c:876` |
| `SpawnEntityOnGroundPos(type, pos)` | Creates it on the ground at `pos` (placed on the surface). | `P:\scripts\3_game\entities\entityai.c:2138` |

---

## Registering actions

Override `SetActions()`, call `super`, then `AddAction` and `RemoveAction` with the action's typename. `ItemBase` calls `SetActions()` once per item type, the first time its actions are asked for (`GetActions` calls `InitializeActions`).

```c
class MyMod_CustomItem : ItemBase
{
    override void SetActions()
    {
        super.SetActions();
        AddAction(ActionMyMod_Inspect);
        RemoveAction(ActionTakeItemToHands);
    }
}
```

Sources: `SetActions` `P:\scripts\4_world\entities\itembase.c:246`, `AddAction(typename)` `:255`, `RemoveAction(typename)` `:295`, `InitializeActions` `:223`, `GetActions` `:235`. The action pitfalls are in `../patterns/actions.md`.

---

## config.cpp properties

```cpp
class MyMod_Item : Inventory_Base   // the config base; script class P:\scripts\4_world\entities\itembase\inventory_base.c:1
{
    scope = 2;
    displayName = "My Item";
    descriptionShort = "A useful item.";
    model = "\MyMod\objects\my_item.p3d";
    weight = 100;            // grams
    itemSize[] = {1, 2};     // width, height in the inventory grid
    absorbency = 0.9;        // how fast it gets wet
    varQuantityInit = 200;
    varQuantityMax = 200;
    soundImpactType = "organic";
};
```

Each key appears on a vanilla food item: `weight`, `itemSize[]` and `varQuantityInit`/`varQuantityMax` at `P:\DZ\gear\food\config.cpp:252` to `:261` and `:401` to `:412` (with `absorbency`), and `soundImpactType` at `:644`. The full config rules are in `_shared/conventions/config.md`.

---

## Casts

```c
Weapon_Base wpn    = Weapon_Base.Cast(entity);   // P:\scripts\4_world\entities\firearms\weapon_base.c:38
Magazine mag       = Magazine.Cast(entity);      // magazine.c:38; Magazine_Base is a typedef of it, :1
Edible_Base food   = Edible_Base.Cast(entity);   // P:\scripts\4_world\entities\itembase\edible_base.c:1
Container_Base ctr = Container_Base.Cast(entity);// P:\scripts\4_world\entities\itembase\container_base.c:1
```

---

## Magazines: `ServerSetAmmoCount`, not `SetQuantity`

A magazine's rounds are an engine ammo count, set with `Magazine.ServerSetAmmoCount(int)` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:70`). `Magazine` (`:38`) does not override `SetQuantity`, so `SetQuantity` on a magazine does not load rounds. Vanilla loads spawned magazines this way in `P:\scripts\4_world\classes\playergearspawn\cfgplayerspawnhandler.c:330` and `:340`, and `P:\scripts\4_world\entities\firearms\weapon_base.c:797`.

```c
void SetQuantityOrAmmo(EntityAI ent, int value)
{
    Magazine mag = Magazine.Cast(ent);
    if (mag)
    {
        mag.ServerSetAmmoCount(value);
        return;
    }
    ItemBase ib = ItemBase.Cast(ent);
    if (ib)
        ib.SetQuantity(value);
}
```

---

## `SetObjectTexture`

- The signature is `SetObjectTexture(int index, string texture_name)` (`P:\scripts\3_game\entities\entityai.c:2881`); `SetObjectMaterial(int index, string mat_name)` is next to it (`:2884`). The index is the position in the config's `hiddenSelections[]`, starting at 0, not the selection name.
- `GetHiddenSelectionsTextures()` reads the config's `hiddenSelectionsTextures[]` (`P:\scripts\3_game\entities\object.c:132`). Vanilla has no `GetObjectTextures` and no `SetObjectTextureGlobal`; calling a method that does not exist stops the whole script module compiling.
- Reported, not checked on `P:\`: a selection name that differs in case from the named selection in the `.p3d` is ignored without a log line.
