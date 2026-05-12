# Central Economy (CE) & Hive Integration

The Central Economy (CE) controls all dynamic object spawning in DayZ: loot, infected, animals, vehicles, and static territory. Mods interact with CE through `config.cpp` declarations and, at runtime, through Hive/CE API calls from script.

---

## config.cpp — Registering Items in CE

### CfgSpawnablesTypes (loot tables)

Add your item to existing or custom categories:

```cpp
// config.cpp

class CfgSpawnablesTypes
{
    class MyMod_CustomCanteen
    {
        // Category determines which loot containers will spawn this item
        // e.g. "Military" = military spawn points only
        category[] = {"Military"};

        // CE uses usage tags to filter spawning contexts
        usage[] = {"Military", "Hunting"};

        // Value tag drives CE rarity (higher = rarer but more CE budget)
        value[] = {"Tier3"};

        // Lifetime on ground before CE despawns (seconds, 0 = default)
        lifetime = 14400;

        // Nominal = target quantity across the map
        // Min = never let count drop below this
        // Restock = how many to add per CE cycle
        nominal = 15;
        min     = 5;
        quantmin = -1;   // -1 = use item's varQuantityMin
        quantmax = -1;   // -1 = use item's varQuantityMax
        cost     = 100;  // CE budget unit cost
        spawnabletypes
        {
            class cargo
            {
                // preset controls which attachment/content presets apply
                preset = "drybag_cargo";
            };
        };
    };
};
```

### CfgRandomPresence (territory-based spawn tables)

```cpp
class CfgRandomPresence
{
    class MyMod_CanteenTable
    {
        // This table is used by the CE territory system
        filename = "MyMod_Canteen.xml";  // external CE table file
    };
};
```

---

## Runtime CE Queries from Script

### Check if CE is running (server-only)

```c
// CE is only meaningful on the server; never call CE APIs from clients.
if (!GetGame().IsServer())
    return;
```

### Hive object lifecycle

```c
// EntityAI exposes CE flags through InventoryItem / ItemBase
// Get CE lifetime remaining
float lifetime = item.GetLifetime();
item.SetLifetime(3600); // reset to 1 hour

// Mark as CE-persistent (survives server restart in the CE database)
item.SetInvisible(false);

// Force CE to "flag" an item for deletion next cycle
item.Delete(); // removes it immediately; CE will not re-link it
```

### Spawning with CE linkage

CE manages all objects on the map. Spawning via script creates "non-persistent" objects unless explicitly stored:

```c
// Spawn an object and let CE track it
EntityAI spawned = GetGame().CreateObjectEx("MyMod_CustomCanteen", spawnPos, ECE_PLACE_ON_SURFACE);
if (spawned)
{
    // CE-linked object: registered in the CE database after next CE cycle
    // For immediate persistence, use Hive persistence directly:
    spawned.SetLifetime(86400); // 24 hours
}

// Spawn WITHOUT CE tracking (e.g. quest item, temp object)
EntityAI temp = GetGame().CreateObject("MyMod_CustomCanteen", spawnPos, false, true);
// false = not persistent, true = snap to ground
```

---

## Custom CE XML Tables

CE data is driven by XML files placed in `env/` inside your mod's `.pbo`:

```xml
<!-- MyMod/env/MyMod_Canteen.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<types>
    <type name="MyMod_CustomCanteen">
        <nominal>20</nominal>
        <lifetime>14400</lifetime>
        <restock>0</restock>
        <min>10</min>
        <quantmin>-1</quantmin>
        <quantmax>-1</quantmax>
        <cost>100</cost>
        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
        <category name="Military"/>
        <usage name="Military"/>
        <value name="Tier3"/>
    </type>
</types>
```

### Attaching to vanilla types.xml

Use `cfgeconomycore.xml` to merge your table without overriding vanilla:

```xml
<!-- MyMod/cfgeconomycore.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<economycore>
    <ce folder="env">
        <file name="MyMod_Canteen.xml" type="types"/>
    </ce>
</economycore>
```

---

## ObjectSpawner (Scripted Map Objects)

For static map-fixed objects (lamps, signs, decoration) use `ObjectSpawner` JSON:

```json
[
  {
    "pos": [5432.0, 0.0, 7123.5],
    "ypr": [0.0, 0.0, 0.0],
    "scale": 1.0,
    "name": "MyMod_Sign",
    "enableCEPersistency": true
  }
]
```

```c
// Loaded in MissionServer.OnInit():
GetGame().CreateObjectEx("MyMod_Sign", Vector(5432, 0, 7123.5), ECE_PLACE_ON_SURFACE);
// Or via the vanilla ObjectSpawner system (reads from JSON automatically)
```

---

## InfectedHorde Spawner

To add wave-based infected spawns around an area:

```c
// Server only
vector centre = player.GetPosition();
int radius    = 50;
int count     = 5;

SpawnInfectedPatrol spawner = SpawnInfectedPatrol.Cast(
    GetGame().CreateObjectEx("ZmbM_PoliceMan_Pants", centre, ECE_PLACE_ON_SURFACE)
);
// Or use built-in spawn tables:
GetGame().CreateObjectEx("ZmbM_PoliceMan_Pants", centre + Vector(Math.RandomFloat(-radius, radius), 0, Math.RandomFloat(-radius, radius)), ECE_PLACE_ON_SURFACE);
```
