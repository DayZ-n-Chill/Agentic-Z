# StarDZ and DZconfig distill: Enforce Script, Central Economy, loot and events

Covers sixteen facts paraphrased from two public community sources: the StarDZ DayZ Modding Wiki (script layers, load order, language gotchas, entity root) and the DZconfig wiki (Central Economy files, `types.xml` semantics, events, loot balancing).

Status: third-party facts; each one names its source page. Not yet checked on `P:\`, except the lines listed under "Checked on `P:\`" at the end. The `[EXACT][CLAIM-...]` tags are claim IDs in `scripts/dev/knowledge-pack/sources/claims.json`.

> Paraphrase with links: no StarDZ or DZconfig page text is copied here.
> Harvest: the author's local staging folder `dayz-public-corpus-2026-09-07/harvested/other/{stardz,dzconfig}/` (batch 3, **2026-09-07**; outside this repo).
> Facts below are **`historical` until live-verified** against vanilla `P:\scripts` / current mission CE samples / live upstream pages.
>
> Reconcile with `wiki-systems-reference.md` and `public-wiki-harvest.md` (batch-3 pointers). Do **not** duplicate sealed skill contracts.

## Provenance

| `source_id` | Kind | Canonical URLs |
|---|---|---|
| `stardz-dayz-modding-wiki-2026-09` | web | https://github.com/StarDZ-Team/DayZ-Modding-Wiki · https://stardz-team.github.io/DayZ-Modding-Wiki/ |
| `dzconfig-wiki-2026-09` | web | https://dzconfig.com/wiki · https://dzconfig.com/wiki/understanding-ce |

Note: the source pack's registry (`scripts/dev/knowledge-pack/sources/`) already has git source `stardz` → `StarDZ-Team/Dayz-Modding-Skills` (skills prior-art / negatives). That is **not** this wiki harvest.

## 1. Enforce Script — five layers + load order (StarDZ)

1. [EXACT][CLAIM-STARDZ-FIVE-LAYER-MODULES] DayZ compiles scripts in five numbered modules under `Scripts/`: `1_Core` → `engineScriptModule`, `2_GameLib` → `gameLibScriptModule`, `3_Game` → `gameScriptModule`, `4_World` → `worldScriptModule`, `5_Mission` → `missionScriptModule`. Typical homes: Core utilities/enums; GameLib rarely used by mods; Game for `DayZGame`/RPC/constants; World for `PlayerBase`/`ItemBase`/entities; Mission for `MissionServer`/`MissionGameplay`, HUD, boot hooks. *(historical; StarDZ five-layers)* — https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/02-mod-structure/01-five-layers.md

2. [EXACT][CLAIM-STARDZ-LOWER-LAYER-REF-BAN] **Critical rule:** a lower layer **cannot** name types defined only in a higher layer (compile-time). Example symptom: `Undefined type 'PlayerBase'` when `PlayerBase` (4_World) is referenced from 3_Game. Workaround: accept a lower base (`Man`/`Object`) in the lower layer and `Class.CastTo` in 4_World+. *(historical)* — same five-layers URL.

3. [EXACT][CLAIM-STARDZ-REQUIREDADDONS-ORDER] Mod **script/config load order** is driven by `requiredAddons[]` in each PBO's `config.cpp` `CfgPatches` dependency graph — not by `-mod=` path order alone. The engine compiles **all mods'** scripts for layer N (ordered by that graph) before layer N+1. Unrelated mods may fall back to ASCII order of `CfgMods` class names. *(historical; community note attributed in StarDZ to DabsFramework author)* — five-layers URL.

## 2. Enforce Script — high-signal gotchas (StarDZ)

4. [EXACT][CLAIM-STARDZ-ENFORCE-SYNTAX-ABSENCES] Enforce lacks many C++/C#/Java conveniences: **no** ternary `?:`, **no** `do…while`, **no** `try/catch/throw`, **no** multiple inheritance, **no** lambdas/native delegates, **no** `#include` (modules come from `config.cpp`), **no** namespaces; use `null`/`NULL` (not `nullptr`); `switch`/`case` **does** fall through without `break`; default parameter values must be literals or `NULL`. *(historical)* — https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/01-enforce-script/12-gotchas.md

5. [EXACT][CLAIM-STARDZ-GETPLAYER-SERVER-NULL] `GetGame().GetPlayer()` returns the **local** player and is **`null` on a dedicated server**. Server-side iteration should use `GetGame().GetPlayers(...)` (or equivalent player list APIs), not assume a local player. *(historical)* — gotchas URL.

6. [EXACT][CLAIM-STARDZ-ISCLIENT-DURING-LOAD] During client **load**, `GetGame().IsClient()` can report **false** while `IsServer()` reports **true**. Prefer `IsDedicatedServer()` (or equivalent dedicated checks) when branching load-time logic. Also note (1.28+): `sealed` types/methods cannot be extended/overridden; method arity hard-capped at **16** parameters. *(historical)* — gotchas URL.

7. [EXACT][CLAIM-STARDZ-ENTITY-ROOT] World objects descend from `IEntity` → `Object` → … → `EntityAI`, then branch to inventory items (`ItemBase`), players (`PlayerBase`), infected, animals, buildings, transport. Prefer API quick-reference tables for position/transform/health helpers; treat signatures as hints until matched on `P:\scripts`. *(historical)* — https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/06-engine-api/01-entity-system.md · https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/06-engine-api/quick-reference.md

## 3. Central Economy — files + types semantics (DZconfig)

8. [EXACT][CLAIM-DZCONFIG-CE-FOUR-CORE] CE loot is commonly reasoned as four cooperating surfaces: **`types.xml`** (per-classname nominal/min/lifetime/restock/flags/usages), **`events.xml`** (dynamic events such as heli crashes), **`cfglimitsdefinition.xml`** (maps category/usage/value tags to map locations), **`cfgspawnabletypes.xml`** (attachments/cargo when an item spawns). Server start loads the registered CE file set; the manager counts world items and restocks when counts fall through `min` toward `nominal`. *(historical)* — https://dzconfig.com/wiki/understanding-ce

9. [EXACT][CLAIM-DZCONFIG-TYPES-NOMINAL-MIN] In `types.xml`: **`nominal`** = target world count; **`min`** = restock trigger (must be **<** nominal); **`lifetime`** = untouched despawn seconds (interaction resets); **`restock`** = delay before CE may replenish after dipping to/below `min` (`0` = next CE cycle, still not literally instant); **`quantmin`/`quantmax`** = spawn quantity percent (`-1` = default/full); **`cost`** = spawn priority weight (commonly 100). Setting `nominal` to `0` disables new spawns for that type. *(historical)* — https://dzconfig.com/wiki/types · understanding-ce

10. [EXACT][CLAIM-DZCONFIG-TYPES-COUNT-FLAGS] `types.xml` **flags** control what counts toward nominal: `count_in_map` (ground/buildings; usually 1), `count_in_cargo`, `count_in_hoarder` (player storage/bases — useful for rares), `count_in_player` (inventories — hoarding can starve world spawns), plus `crafted` and `deloot` (dynamic-event-oriented loot). Category / usage / value tags must match `cfglimitsdefinition.xml`. Prefer disabling via ignore-list / nominal 0 over deleting type rows (deleting stops **new** spawns; existing instances can linger until lifetime). *(historical)* — types + understanding-ce URLs.

11. [EXACT][CLAIM-DZCONFIG-CFGECONOMYCORE-SPLIT] `cfgeconomycore.xml` registers CE data files under a `ce folder` (often `db`) with typed `<file …/>` entries (`types`, `events`, `globals`, …). Custom/mod loot is commonly added as **extra** `type="types"` (or `events`) files; **duplicate classnames: last loaded file wins**. Malformed XML here can break economy load — validate and watch RPT on first restart. *(historical; reconcile with BI CE mission-files wiki)* — https://dzconfig.com/wiki/cfgeconomycore

## 4. Events + loot balancing (DZconfig)

12. [EXACT][CLAIM-DZCONFIG-EVENTS-RADIUS-ACTIVE] `events.xml` entries use their own nominal/min/lifetime/restock cycle plus **`saferadius`** (min distance from players to spawn), **`distanceradius`** (spacing between same-event instances), **`cleanupradius`**, **`active`** (0/1 toggle), and child wreck/loot defs. Positions for `position=fixed` events live in **`cfgeventspawns.xml`** and must match the event `name`. Contaminated areas pair with `cfgEffectArea.json`. *(historical)* — https://dzconfig.com/wiki/events

13. [EXACT][CLAIM-DZCONFIG-SPAWNABLETYPES-ATTACH] `cfgspawnabletypes.xml` binds to `types.xml` classnames and can declare per-slot **`<attachments chance=…>`** item pools and **`<cargo>`** (inline or `preset=` from `cfgrandompresets.xml`). Cargo that does not fit the parent inventory is skipped. *(historical)* — https://dzconfig.com/wiki/cfgspawnabletypes

14. [EXACT][CLAIM-DZCONFIG-LOOT-TIER-RATIOS] Balancing heuristic (map/pop dependent): rarity tiers by nominal/restock bands (common → very rare); keep **`min` ≈ 50–70% of `nominal`** for steady restocks; larger gaps feel scarcer. Tune weapons and ammo together; scale nominals to map spawn-point density; change one category at a time starting from vanilla. *(historical guidance, not a BI contract)* — https://dzconfig.com/wiki/loot-balancing

## 5. Operator checklist (cross-source, still historical)

15. Loot “missing” triage: nominal > 0; `min` < nominal; valid category/usage tags; not on ignore-list; hoarder/player flags not starving the pool; lifetime not absurdly short; XML well-formed; CE file actually registered. *(DZconfig understanding-ce troubleshooting.)*

16. StarDZ troubleshooting chapters + first-mod tutorial are staging pointers only — promote further facts only with new claims after re-check. Hub: https://stardz-team.github.io/DayZ-Modding-Wiki/

## Cross-ref

- `public-wiki-harvest.md` — batch-3 index (StarDZ/DZconfig counts)
- `wiki-systems-reference.md` — prior systems distill / errata
- Staging: the source pack's private staging folder `dayz-public-corpus-2026-09-07/harvested/other/{stardz,dzconfig}/` (not part of this repo)

## Checked on `P:\`

Opened on 2026-11-17. A line here confirms only what it says.

- Fact 5: the server-side player list call is `GetPlayers`, declared at `P:\scripts\3_game\global\game.c:945`.
- Fact 6: `IsDedicatedServer` is declared at `P:\scripts\3_game\global\game.c:1125`.
- Fact 7: `class Object extends IEntity` is at `P:\scripts\3_game\entities\object.c:64`, and `class EntityAI extends Entity` at `P:\scripts\3_game\entities\entityai.c:115`.
