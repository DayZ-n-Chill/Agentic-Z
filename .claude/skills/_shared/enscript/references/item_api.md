# Reference: ItemBase API

`ItemBase` is the base for all held/inventory items. Access it from `Scripts/4_World/`.

---

## Quantity (Liquid, Ammo, Stackable)

```c
ItemBase item = ItemBase.Cast(entity);

// Quantity value and limits
float qty    = item.GetQuantity();           // current
float max    = item.GetQuantityMax();        // config maximum
float pct    = item.GetQuantityNormalized(); // 0..1

item.SetQuantity(500.0);
item.AddQuantity(100.0);

// Liquid type (for bottles, containers)
int liquidType = item.GetLiquidType();                    // LIQUID_WATER, etc.
item.SetLiquidType(LIQUID_WATER);

// Is empty
bool empty = item.IsEmpty();
```

---

## Health (damage zones)

```c
// "" = global zone; named zones: "Health", "Blood" etc.
float hp   = item.GetHealth("", "Health");        // 0..100
float maxHp = item.GetMaxHealth("", "Health");
float pct  = item.GetHealthLevel();               // HealthLevel enum

item.SetHealth("", "Health", 100.0);
item.AddHealth("", "Health", -10.0);   // inflict damage

// Damage
item.DecreaseHealth(10.0, false);     // (amount, destroyWhenRuined)
item.SetHealthMax();                  // restore to max
```

---

## Item Flags and State

```c
bool ruined  = item.IsRuined();
bool damaged = item.IsDamaged();
bool worn    = item.IsWorn();

bool hasTemp = item.HasTemperature();
float temp   = item.GetTemperature();
item.SetTemperature(37.0);

bool wet = item.GetWet() > 0.0;
item.SetWet(1.0); // 0..1

bool isMeleeWeapon = item.IsMeleeWeapon();
bool isWeapon      = Weapon.Cast(item) != null;
```

---

## Inventory Position and Containment

```c
EntityAI owner  = item.GetHierarchyRootPlayer(); // the owning PlayerBase or null
EntityAI parent = item.GetHierarchyParent();     // direct parent container

// Attachment slots
int slotCount   = item.GetInventory().GetSlotCount();
EntityAI attach = item.GetInventory().GetSlotItem(0);

// Check if it's in a cargo bay
bool inCargo    = item.IsInCargo();
```

---

## Spawning Items

```c
// Spawn at world position
EntityAI spawned = GetGame().CreateObject("Apple", vector pos, false, true);

// Spawn in entity's inventory
EntityAI inInv = player.CreateInInventory("Apple");

// Spawn below entity (drops to ground)
player.SpawnEntityOnGroundBelow("Apple", player.GetPosition());
```

---

## Action Registration

```c
modded class MyMod_CustomItem
{
    override void GetActions(typename action_input_type, out array<ActionBase_Basic> actions)
    {
        super.GetActions(action_input_type, actions);

        if (action_input_type == DefaultDamageInput)
            ActionManagerBase.AddAction(ActionMyMod_Smash);
        if (action_input_type == DefaultInteractInput)
            ActionManagerBase.AddAction(ActionMyMod_Inspect);
    }

    // Optional: prevent default actions
    override bool IsIgnoredByConstruction()
    {
        return false;
    }
}
```

---

## config.cpp Properties (class body)

```cpp
class MyMod_Item : ItemBase
{
    displayName = "My Item";
    model       = "MyMod\objects\my_item.p3d";
    descriptionShort = "A useful item.";

    weight = 100;           // grams
    absorbency = 0;

    // Quantity
    varQuantityInit = 100;
    varQuantityMin  = 0;
    varQuantityMax  = 100;

    nutritionalProfile[] = {};   // empty = not food

    // Attachments
    itemSize[]        = {1, 1};  // [width, height] in inventory grid
    forceCargo        = 0;

    // Sounds
    soundImpactSoft   = "Hit_soft";
}
```

---

## Useful Casts

```c
// Always safe-cast before accessing sub-class API
Weapon_Base wpn   = Weapon_Base.Cast(entity);
Magazine_Base mag = Magazine_Base.Cast(entity);
Edible_Base food  = Edible_Base.Cast(entity);
Container_Base ctr = Container_Base.Cast(entity);
```
