# Script layers, Central Economy, loot and events: quick facts

Covers sixteen facts in four groups: the five script modules and their load order, Enforce Script language gotchas and the entity root, the Central Economy files and `types.xml` semantics, and events and loot balancing.

Status: not yet checked on `P:\`, except the lines listed under "Checked on `P:\`" at the end. The Central Economy facts describe mission XML files, which the script tree on `P:\` cannot confirm; check them against the mission files of the server you work on. Treat every unchecked fact as a lead and confirm it on `P:\scripts` or the mission folder before relying on it.

Related notes: `wiki-systems-reference.md` (gameplay and server configuration) and `public-wiki-harvest.md` (where to look a topic up).

## 1. Enforce Script: five modules and load order

1. DayZ compiles scripts in five numbered modules under `Scripts/`: `1_Core` → `engineScriptModule`, `2_GameLib` → `gameLibScriptModule`, `3_Game` → `gameScriptModule`, `4_World` → `worldScriptModule`, `5_Mission` → `missionScriptModule`. Typical homes: Core utilities and enums; GameLib rarely used by mods; Game for `DayZGame`, RPC and constants; World for `PlayerBase`, `ItemBase` and entities; Mission for `MissionServer`, `MissionGameplay`, HUD and boot hooks.

2. **Critical rule:** a lower module **cannot** name types defined only in a higher module (compile time). Example symptom: `Undefined type 'PlayerBase'` when `PlayerBase` (4_World) is referenced from 3_Game. Workaround: accept a lower base (`Man` or `Object`) in the lower module and `Class.CastTo` in 4_World or above.

3. Mod **script and config load order** is driven by `requiredAddons[]` in each PBO's `config.cpp` `CfgPatches` dependency graph, not by `-mod=` path order alone. The engine compiles **all mods'** scripts for module N (ordered by that graph) before module N+1. Unrelated mods may fall back to ASCII order of `CfgMods` class names.

## 2. Enforce Script: gotchas

4. Enforce Script lacks many C++, C# and Java conveniences: **no** ternary `?:`, **no** `do…while`, **no** `try/catch/throw`, **no** multiple inheritance, **no** lambdas or native delegates, **no** `#include` (modules come from `config.cpp`), **no** namespaces; use `null` or `NULL` (not `nullptr`); `switch`/`case` **does** fall through without `break`; default parameter values must be compile-time values: literals, `NULL`, or named constants and enum values (`int dialogButtonType = DBT_OK`, `float maxYawSpeed = FLT_MAX`).

5. `GetGame().GetPlayer()` returns the **local** player and is **`null` on a dedicated server**. Server-side iteration uses `GetGame().GetPlayers(...)`, not a local player.

6. During client **load**, `GetGame().IsClient()` can report **false** while `IsServer()` reports **true**. Prefer `IsDedicatedServer()` when branching load-time logic. Also (1.28 and later): `sealed` types and methods cannot be extended or overridden, and a method takes at most **16** parameters.

7. World objects descend from `IEntity` → `Object` → … → `EntityAI`, then branch to inventory items (`ItemBase`), players (`PlayerBase`), infected, animals, buildings and transport. Treat any remembered position, transform or health helper signature as a hint until it is matched on `P:\scripts`.

## 3. Central Economy: files and `types.xml` semantics

8. Loot is governed by four cooperating files: **`types.xml`** (per-classname nominal, min, lifetime, restock, flags, usages), **`events.xml`** (dynamic events such as heli crashes), **`cfglimitsdefinition.xml`** (maps category, usage and value tags to map locations), **`cfgspawnabletypes.xml`** (attachments and cargo when an item spawns). Server start loads the registered file set; the economy counts world items and restocks when counts fall through `min` toward `nominal`.

9. In `types.xml`: **`nominal`** = target world count; **`min`** = restock trigger (must be **<** nominal); **`lifetime`** = seconds until an untouched item despawns (interaction resets it); **`restock`** = delay before the economy may replenish after the count dips to or below `min` (`0` = next cycle, still not instant); **`quantmin`/`quantmax`** = spawn quantity percent (`-1` = default/full); **`cost`** = spawn priority weight (commonly 100). Setting `nominal` to `0` disables new spawns for that type.

10. `types.xml` **flags** control what counts toward nominal: `count_in_map` (ground and buildings; usually 1), `count_in_cargo`, `count_in_hoarder` (player storage and bases; useful for rare items), `count_in_player` (inventories; hoarding can starve world spawns), plus `crafted` and `deloot` (loot for dynamic events). Category, usage and value tags must match `cfglimitsdefinition.xml`. Prefer disabling a type with nominal 0 over deleting its row: deleting stops **new** spawns, and existing instances linger until their lifetime ends.

11. `cfgeconomycore.xml` registers the data files under a `ce folder` (often `db`) with typed `<file …/>` entries (`types`, `events`, `globals`, …). Custom or mod loot is added as **extra** `type="types"` (or `events`) files; for **duplicate classnames the last loaded file wins**. Malformed XML here can break the economy load, so validate the file and watch the RPT on the first restart.

## 4. Events and loot balancing

12. `events.xml` entries use their own nominal, min, lifetime and restock cycle plus **`saferadius`** (minimum distance from players to spawn), **`distanceradius`** (spacing between instances of the same event), **`cleanupradius`**, **`active`** (0/1 toggle), and child wreck and loot definitions. Positions for `position=fixed` events live in **`cfgeventspawns.xml`** and must match the event `name`. Contaminated areas pair with `cfgEffectArea.json`.

13. `cfgspawnabletypes.xml` binds to `types.xml` classnames and can declare per-slot **`<attachments chance=…>`** item pools and **`<cargo>`** (inline or `preset=` from `cfgrandompresets.xml`). Cargo that does not fit the parent inventory is skipped.

14. Balancing heuristic (depends on map and population; a rule of thumb, not an engine contract): set rarity tiers by nominal and restock bands (common → very rare); keep **`min` at about 50–70% of `nominal`** for steady restocks; larger gaps feel scarcer. Tune weapons and ammo together; scale nominals to the map's spawn-point density; change one category at a time, starting from vanilla.

## 5. Operator checklist

15. Loot "missing" triage: nominal > 0; `min` < nominal; valid category and usage tags; the type is not on an ignore list; hoarder and player flags are not starving the pool; lifetime is not absurdly short; the XML is well formed; the file is actually registered in `cfgeconomycore.xml`.

16. The facts above are the only ones recorded here. Add a further script or economy fact only after it has been checked on `P:\scripts` or on the mission files.

## Checked on `P:\`

Opened on 2026-11-17. A line here confirms only what it says.

- Fact 5: the server-side player list call is `GetPlayers`, declared at `P:\scripts\3_game\global\game.c:945`.
- Fact 6: `IsDedicatedServer` is declared at `P:\scripts\3_game\global\game.c:1125`.
- Fact 4, default parameters: `int dialogButtonType = DBT_OK, int defaultButton = DBB_OK` at `P:\scripts\3_game\global\errormodulehandler\errorhandlermodule.c:233`, and `float maxYawSpeed = FLT_MAX` at `P:\scripts\3_game\human.c:1261`.
- Fact 7: `class Object extends IEntity` is at `P:\scripts\3_game\entities\object.c:64`, and `class EntityAI extends Entity` at `P:\scripts\3_game\entities\entityai.c:115`.
