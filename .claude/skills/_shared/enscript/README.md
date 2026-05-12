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
| `modded_class.md` | `super.*` rules, field injection, mod load order, **no-extends rule, NO_GUI guard, Managed-rooted engine classes** |
| `netsync.md` | `RegisterNetSyncVariable*`, `SetSynchDirty`, `OnVariablesSynchronized`, bitfield packing |
| `persistence.md` | `OnStoreSave`/`OnStoreLoad`, version header, write-order rules |
| `rpc.md` | `ScriptRPC`, `RPCSingleParam`, `OnRPC` switch template, client-to-server validation |
| `singleton.md` | Static `s_Instance`, lazy init, `GetInstance()` |
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

## Our additions

The vendored content was lightly modified to include Agentic-Z-specific gotchas:

- **`patterns/modded_class.md`** — added prominent `NEVER use extends` callout at top (silent no-op, #1 cause of "my override isn't running"), plus sections on Managed-rooted engine classes that cannot be modded and the `#ifndef NO_GUI` guard rule for modded GUI classes.

When SWARM updates upstream, re-run the import and re-apply our gotchas — they are localized to `patterns/modded_class.md` for easy re-application.

## Attribution

Source: [`SWARMDayZ/dayz-enfusion-skills`](https://github.com/SWARMDayZ/dayz-enfusion-skills). Vendored with verbal permission from the author (granted via YouTube video accompanying the repo). No license file is published upstream; treat this content as "use for whatever" per the author's public grant.

Original layout and prose by SWARM; modifications and integration into Agentic-Z by DayZ-n-Chill.
