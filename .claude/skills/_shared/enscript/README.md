# Enforce Script Reference Library

Hand-curated reference content for writing DayZ mods in Enforce Script. Consumed by the `dayz-script-specialist` agent (and any other DayZ agent doing script work) as the canonical "how to implement the common pattern" source.

Companion to:

- `_shared/enscript-style.md` — formatting and naming rules (HOW the code is written)
- `_shared/dayz-conventions.md` — L2 repo rules for DayZ work (preflight, workspace layout, etc.)
- The `dayz-rag` MCP server — semantic search over indexed vanilla source + wiki (WHERE vanilla does it)

This folder fills the gap between those: the recurring patterns themselves (netsync, RPCs, persistence, etc.), framework integrations, and complete worked examples.

## Layout

```
enscript/
├── patterns/         # Recurring implementation patterns
├── integrations/     # External frameworks (CF, DABS) + vanilla systems (CE, inputs)
├── references/       # API surface by topic (player, item, game, types, paths, etc.)
└── examples/         # Complete .c / .layout files (copy-paste starting points)
```

### patterns/

| File | Topic |
|---|---|
| `modded_class.md` | `super.*` rules, field injection, mod load order, **no-extends rule, NO_GUI guard, Managed-rooted engine classes, extend script class not config parent, member-field caveat** |
| `netsync.md` | `RegisterNetSyncVariable*`, `SetSynchDirty`, `OnVariablesSynchronized`, bitfield packing |
| `persistence.md` | `OnStoreSave`/`OnStoreLoad`, version header, write-order rules |
| `rpc.md` | `ScriptRPC`, `RPCSingleParam`, `OnRPC` switch template, client-to-server validation, **ID-collision symptom** |
| `singleton.md` | Static `s_Instance`, lazy init, `GetInstance()`, **`ScriptInvoker` shutdown null-guard** |
| `actions.md` | `ActionBase`, `CCINonRuined` vs `CCINone`, full `RemoveAction` pickup-prevention pattern, client/server check-style mismatch |
| `scheduler.md` | `CallLater` 4.5h overflow, per-tick allocation GC pressure, call-category guidance |
| `physics_items.md` | `ThrowPhysically` vs manual `CreateDynamicPhysics`, `SetDynamicPhysicsLifeTime` mandatory call |
| `json_config_migration.md` | `SCHEMA_VERSION` + forward-migration, parse-failure handling for admin-edited JSON |
| `language_workarounds.md` | No ternary, no auto type inference, no lambdas, no exceptions, no overloading |

### integrations/

| File | Topic |
|---|---|
| `community_framework.md` | CF module system, `ModStorage` persistence, event bus, inter-mod events |
| `dabs_framework.md` | Attribute-based action system, `CF_ModAttribute`, MVC layout |
| `vanilla_plugins.md` | `PluginBase` lifecycle, `GetPlugin()`, service-locator isolation |
| `central_economy.md` | CE XML format, runtime CE with `SpawnObject`/`DeleteObject`, `cfgeconomycore.xml` |
| `input_bindings.md` | `inputs.xml`, `UAInput` API, `GetUApi()`, context guards |

### references/

| File | Topic |
|---|---|
| `types_collections.md` | Primitive types, string methods, array/map/set API, vector math, `Math` |
| `player_api.md` | `PlayerBase` stats, vitals, agents, modifiers, inventory, NetSync, RPC helpers |
| `item_api.md` | `ItemBase` quantity/health/flags, action registration, spawning, `config.cpp` properties |
| `game_api.md` | `GetGame()`, `GetWorld()`, `GetMission()`, `CreateObject`, `CallLater`, logging |
| `erpc_defines.md` | Vanilla `eRPCs`/`eAgents`/`eModifiers` tables, custom ID range convention |
| `file_paths.md` | `$profile`/`$saves` path tokens, `FileExist`, `MakeDirectory`, `JsonFileLoader`, `FileMode` |
| `gui_layout.md` | `.layout` file format, RGBA colors, coords, all widget types, `ItemPreviewWidget`/`PlayerPreviewWidget` |

### examples/

Numbered, complete working files. Reference by number when pointing the agent at a starting point.

| # | File | Demonstrates |
|---|---|---|
| 01 | `01_custom_item.c` | Custom item with NetSync bool flag and versioned `OnStoreSave`/`OnStoreLoad` |
| 02 | `02_custom_action_singleuse.c` | Single-use `ActionBase` with `CanPerformAction` guard |
| 03 | `03_continuous_action.c` | Hold-to-complete action with progress bar, interrupt, cooldown |
| 04 | `04_rpc_patterns.c` | All three RPC APIs side by side |
| 05 | `05_mission_server.c` | `MissionServer` overrides: connect/disconnect/tick |
| 06 | `06_json_config.c` | `JsonFileLoader` singleton config with nested sub-config |
| 07 | `07_agent_modifier.c` | Full `SymptomBase` + `ModifierBase` disease stack |
| 08 | `08_gui_menu.c` | `UIScriptedMenu` with listbox, filter, buttons |
| 09 | `09_scheduler_timer.c` | `CallLater`, `Timer`, `OnScheduledTick` with frame-skip guard |
| 10 | `10_modded_playerbase.c` | Comprehensive `PlayerBase` mod combining everything |
| 11 | `11_hud_plain_text.layout` | HUD overlay with `TextWidget`s (+ companion modded `Hud.Update()` script) |
| 12 | `12_menu_interactions.layout` | Dialog with `EditBoxWidgetClass` filter, 2-column `TextListboxWidgetClass`, `ButtonWidgetClass` |
| 13 | `13_item_preview.layout` | Item inspect panel with `ItemPreviewWidgetClass` for live 3D model |

## Quick reference — symptom → file

When debugging, jump to the file that owns the symptom.

| Symptom | File |
|---|---|
| `modded class Foo` override never runs | `patterns/modded_class.md` (no-extends rule) |
| Server compile error `Unknown type 'IngameHud'` (or `Chat` / `UiHintPanel`) | `patterns/modded_class.md` (`#ifndef NO_GUI` guard) |
| Can't `modded class UIScriptedMenu` / `Widget` | `patterns/modded_class.md` (Managed-rooted classes) |
| Custom barrel missing open/close anim | `patterns/modded_class.md` (extend script class, not config parent) |
| Strange crashes at player connect after adding `m_X` fields | `patterns/modded_class.md` (member field caveat) |
| Action shows on client, server rejects on execute | `patterns/actions.md` (check-style mismatch) |
| Tool-in-hand action doesn't fire | `patterns/actions.md` (`CCINonRuined` vs `CCINone`) |
| Item placed but still draggable into inventory | `patterns/actions.md` (`RemoveAction` 4-step pattern) |
| Long-running callback drifts after ~4.5h | `patterns/scheduler.md` (`CallLater` float overflow) |
| Frame-time spikes every N seconds | `patterns/scheduler.md` (per-tick allocation) |
| Item appears frozen in air after spawn | `patterns/physics_items.md` (`ThrowPhysically`) |
| Admin's edited JSON resets / loses fields after mod update | `patterns/json_config_migration.md` (schema migration) |
| RPC fires "wrong handler" with another mod loaded | `patterns/rpc.md` (ID-collision symptom) |
| Crash on shutdown / mission end after `ScriptInvoker.Remove()` | `patterns/singleton.md` (null-guard) |
| Keybind does nothing, no log error | `integrations/input_bindings.md` (3-piece setup) |
| Dabs menu stuck open, no other menus work | `integrations/dabs_framework.md` (layout-path ghost trap) |
| Magazine spawns with 0 rounds despite quantity set | `references/item_api.md` (`Magazine.ServerSetAmmoCount`) |
| `SetObjectTexture` no-op, no log warn | `references/item_api.md` (case-sensitivity, index vs name) |
| Whole script file fails to compile, no obvious cause | `references/item_api.md` (`SetObjectTextureGlobal` may not exist) |
| `ConfigGet*` returns nothing | `references/game_api.md` (space-separated path, not dotted) |
| HUD marker jitters at screen edges | `references/game_api.md` (`GetScreenPos` z-check) |
| `string.ToLower()` mutates both copies | `references/types_collections.md` (force-allocate via `+ ""`) |
| Older guide says *"write a custom Clamp"* | `references/types_collections.md` (`Math.Clamp` exists) |
| Attachment slot silently rejects modded item | `dayz-conventions.md` (T148506 — vanilla `inventorySlot` is a string) |

## Our additions

The vendored content was lightly modified to include Agentic-Z-specific gotchas:

- **`patterns/modded_class.md`** — `NEVER use extends` callout, `Managed`-rooted engine classes, `#ifndef NO_GUI` guard rule, extend-script-class-not-config-parent, member field caveat
- **`patterns/rpc.md`** — ID-collision symptom + high-base recommendation
- **`patterns/singleton.md`** — `ScriptInvoker` shutdown null-guard
- **`patterns/actions.md`** *(new)* — full action-system pitfalls
- **`patterns/scheduler.md`** *(new)* — `CallLater` 4.5h overflow + per-tick allocation
- **`patterns/physics_items.md`** *(new)* — `ThrowPhysically` pattern
- **`patterns/json_config_migration.md`** *(new)* — forward-compatible JSON schema migration
- **`integrations/input_bindings.md`** — silent-fail keybind 3-piece trap
- **`integrations/dabs_framework.md`** — layout-path ghost-menu trap
- **`references/item_api.md`** — `Magazine.ServerSetAmmoCount`, `SetObjectTexture` case-sensitivity
- **`references/game_api.md`** — `ConfigGet*` space-separated path, `GetScreenPos` z-check
- **`references/types_collections.md`** — `string.ToLower/ToUpper` mutation, `Math`/`string` API existence table, `int.MIN` quirk

When SWARM updates upstream, re-run the import and re-apply our additions.

## Attribution

Source: [`SWARMDayZ/dayz-enfusion-skills`](https://github.com/SWARMDayZ/dayz-enfusion-skills). Vendored with verbal permission from the author (granted via YouTube video accompanying the repo). No license file is published upstream; treat this content as "use for whatever" per the author's public grant.

Original layout and prose by SWARM; modifications and integration into Agentic-Z by DayZ-n-Chill.
