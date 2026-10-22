# Central Economy (CE) & Hive Integration

The Central Economy (CE) controls all dynamic object spawning in DayZ: loot, infected, animals, vehicles, and static territory. It is driven by **mission XML files on the server**, not by `config.cpp`. There are no `CfgSpawnablesTypes` or `CfgRandomPresence` config classes anywhere on `P:\`; a mod that declares them ships config that does nothing. At runtime, script talks to the CE through spawn flags, an item's economy profile and `GetCEApi()`, all in `P:\scripts\3_game\ce\centraleconomy.c`.

The mission files cited below are in the vanilla Chernarus mission that DayZ Server installs, `<DayZServer>\mpmissions\dayzOffline.chernarusplus\` (shortened to `<mission>`). See also `../../conventions/server.md`.

## Contents

- [Registering a mod item: three mission files](#registering-a-mod-item-three-mission-files)
- [Runtime: spawn flags](#runtime-spawn-flags)
- [Runtime: lifetime and the item's economy profile](#runtime-lifetime-and-the-items-economy-profile)
- [Runtime: `GetCEApi()`](#runtime-getceapi)
- [ObjectSpawner (fixed map objects from JSON)](#objectspawner-fixed-map-objects-from-json)

---

## Registering a mod item: three mission files

### 1. `types.xml` entry

How many exist, how long they stay and where they spawn. The format matches vanilla's `AKM` entry (`<mission>\db\types.xml:124-136`):

```xml
<type name="MyMod_CustomCanteen">
    <nominal>20</nominal>
    <lifetime>14400</lifetime>
    <restock>0</restock>
    <min>10</min>
    <quantmin>-1</quantmin>
    <quantmax>-1</quantmax>
    <cost>100</cost>
    <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
    <category name="tools"/>
    <usage name="Military"/>
    <value name="Tier3"/>
</type>
```

The meaning of each number is in the comments of `CEItemProfile` (`P:\scripts\3_game\ce\centraleconomy.c:754-768`): nominal is about how many should be on the map, min the lowest count, lifetime the idle seconds before an abandoned item is deleted, restock the idle time before it may respawn, cost its priority in respawn and cleanup.

Edit `types.xml` with `/dayz-edit-types`, which checks every entry and merges a chunk in one write.

### 2. `cfgspawnabletypes.xml` entry (optional)

Damage range, attachments and cargo an item spawns with. Add the entry to the mission's own `<mission>\cfgspawnabletypes.xml`. The format matches vanilla's `AKM` entry (`:2674-2682`) and its chance-based cargo (`:324-326`):

```xml
<type name="MyMod_CustomCanteen">
    <damage min="0.0" max="0.3" />
    <cargo chance="0.5">
        <item name="Rag" />
    </cargo>
</type>
```

### 3. `cfgeconomycore.xml` registration

Keep the mod's `types.xml` in its own folder under the mission and list it in a `<ce folder="...">` block. The folder is relative to the mission root, and the server still loads `db\types.xml` as well. Vanilla's own `cfgeconomycore.xml` has only `<classes>` and `<defaults>` (`<mission>\cfgeconomycore.xml`), so add the block after them:

```xml
<!-- <mission>/cfgeconomycore.xml (excerpt) -->
<economycore>
    <classes> ... </classes>
    <defaults> ... </defaults>
    <ce folder="mymod_ce">
        <file name="types.xml" type="types"/>
    </ce>
</economycore>
```

`/dayz-server-kit` writes these lines and the `types.xml` entries for every spawnable class of a mod; `/dayz-split-types` writes a `<ce folder="db/types">` block for a split mission.

---

## Runtime: spawn flags

`CreateObjectEx(string type, vector pos, int iFlags, int iRotation = RF_DEFAULT)` (`P:\scripts\3_game\global\game.c:703`) takes `ECE_*` flags. The ones a mod uses most, from `centraleconomy.c`:

| Flag | Value | Meaning (vanilla comment) | Line |
|---|---|---|---|
| `ECE_PLACE_ON_SURFACE` | 1060 | `ECE_CREATEPHYSICS\|ECE_UPDATEPATHGRAPH\|ECE_TRACE` | :38 |
| `ECE_EQUIP` | 24576 | equip with configured attachments and cargo | :23 |
| `ECE_NOLIFETIME` | 4194304 | do not set lifetime when creating the object | :30 |
| `ECE_NOPERSISTENCY_WORLD` | 8388608 | do not save this object in world | :31 |
| `ECE_DYNAMIC_PERSISTENCY` | 33554432 | spawns without persistency; once a player takes it, persistency is enabled | :33 |
| `ECE_LOCAL` | 1073741824 | create object locally | :25 |

```c
// Server only: the CE runs on the server.
if (!GetGame().IsServer())
    return;

// A normal world item: placed on the ground, saved, with its types.xml lifetime
Object canteen = GetGame().CreateObjectEx("MyMod_CustomCanteen", spawnPos, ECE_PLACE_ON_SURFACE);

// A temporary quest item: not saved in the world, no lifetime
Object temp = GetGame().CreateObjectEx("MyMod_CustomCanteen", spawnPos, ECE_PLACE_ON_SURFACE | ECE_NOPERSISTENCY_WORLD | ECE_NOLIFETIME);
```

---

## Runtime: lifetime and the item's economy profile

| Call | What it does | Source |
|---|---|---|
| `void SetLifetime(float fLifeTime)` | Set the remaining lifetime in seconds | `P:\scripts\3_game\entities\entityai.c:3377` |
| `float GetLifetime()` | Read the remaining lifetime | `entityai.c:3379` |
| `CEItemProfile GetEconomyProfile()` | The item's `types.xml` values (`GetNominal`, `GetMin`, `GetLifetime`, `GetRestock`, `GetCost`) | `entityai.c:888`; `centraleconomy.c:749-768` |

```c
EntityAI item = EntityAI.Cast(canteen);
if (item)
{
    item.SetLifetime(3600); // one hour before the CE may clean it up
    CEItemProfile profile = item.GetEconomyProfile();
    if (profile)
        Print("[MyMod] types.xml lifetime: " + profile.GetLifetime());
}
```

`Delete()` removes an object at once; it is not a CE call.

---

## Runtime: `GetCEApi()`

`proto native CEApi GetCEApi()` (`centraleconomy.c:746`) returns the CE API (`class CEApi`, :227). Most of it is for diagnostics and export, and several calls are marked "DEVELOPER/DIAG ONLY" in their comments, for example `SpawnDE` (:350-364). Read the comment above a call before using it on a live server. Two that mods use:

| Call | Use | Line |
|---|---|---|
| `Entity SpawnGroup(string sGroupName, vector vPos, float fAngle = -1)` | Spawn a map group such as a building | :347 |
| `void SpawnLoot(string sEvName, vector vPos, float fAngle, int iCount = 1, float fRange = 1)` | Spawn loot of an event at a position | :394 |

---

## ObjectSpawner (fixed map objects from JSON)

For fixed map objects (signs, props, decoration) the vanilla `ObjectSpawnerHandler` reads JSON files listed in `cfggameplay.json` under `objectSpawnersArr` (`P:\scripts\3_game\cfggameplaydatajson.c:195`; empty in `<mission>\cfggameplay.json:57`). Each path is read from the mission folder (`"$mission:" + spawnerFilePath`, `P:\scripts\3_game\objectspawner.c:18`).

The file is one object with an `Objects` array (`ObjectSpawnerJson` and `ITEM_SpawnerObject`, `objectspawner.c:95-108`):

```json
{
  "Objects": [
    {
      "name": "MyMod_Sign",
      "pos": [5432.0, 0.0, 7123.5],
      "ypr": [0.0, 0.0, 0.0],
      "scale": 1.0,
      "enableCEPersistency": false,
      "customString": ""
    }
  ]
}
```

Without `enableCEPersistency` the object spawns with `ECE_NOLIFETIME | ECE_DYNAMIC_PERSISTENCY`; with it, both flags are cleared so the CE manages it like loot (`objectspawner.c:48-54`). A `name` that holds a path spawns a static `.p3d`, but only from the plant and rock folders in `VALID_PATHS` (`objectspawner.c:3-8`).
