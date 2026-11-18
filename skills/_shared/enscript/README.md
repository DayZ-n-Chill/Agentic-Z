# Enforce Script Reference Library

Hand-curated reference content for writing DayZ mods in Enforce Script. Consumed by the `dayz-script-specialist` agent (and any other DayZ agent doing script work) as the canonical "how to implement the common pattern" source.

Companion to:

- `_shared/enscript-style.md` and `_shared/enscript-style/`: formatting and naming rules (HOW the code is written)
- `_shared/dayz-conventions.md` — L2 repo rules for DayZ work (preflight, workspace layout, etc.)
- The `dayz-rag` MCP server: semantic search over indexed vanilla source (WHERE vanilla does it)

This folder fills the gap between those: the recurring patterns themselves (netsync, RPCs, persistence, etc.), framework integrations, and complete worked examples.

## What is checked on `P:\`

Files in this folder are in one of two states:

- **Checked on `P:\`**, every fact cites the vanilla file and line it was read from: all of `references/` except `network_payload_limits.md` (measured in game, not checkable on `P:\`) and the newer API layout in `workbench_api.md` (which `P:\` does not hold; its `P:\` section is checked); in `patterns/`, `modded_class.md` (which marks each of its reported claims as such), `netsync.md`, `persistence.md`, `rpc.md`, `singleton.md` (which marks the `JsonSerializer` behavior it could not read in script), `actions.md`, `json_config_migration.md`, `language_workarounds.md`, `physics_items.md`, `scheduler.md` (which marks each of its reported claims as such) and `server_tick_budget.md` (which cites the vanilla calls and marks the third-party techniques as reported); in `integrations/`, `vanilla_plugins.md`, `central_economy.md` and `input_bindings.md`; in `examples/`, `01` to `10`, the three layouts and `layouts.md`.
- **Checked against the framework's own scripts**, not vanilla: `integrations/community_framework.md` (`P:\Mods\@CF\Addons\scripts.pbo`), `integrations/dabs_framework.md` (the Dabs scripts PBO), `integrations/lbmaster.md` (LBmaster's `LBmaster_Core.pbo`) and `integrations/expansion_style.md` (the shipped Expansion PBOs under `P:\Mods\`, and CF's `scripts.pbo` for its CF names).

- **`depth/`** mixes lines checked on `P:\` with results measured in game on a named build and third-party mod behaviour; each file marks which is which (see `depth/README.md`).

When you add or change a fact in a checked file, check it on `P:\` (or in the framework's PBO) and cite the line. Never overwrite a checked file with content that was not checked.

## Layout

```
enscript/
├── patterns/         # Recurring implementation patterns
├── integrations/     # External frameworks (CF, DABS) + vanilla systems (CE, inputs)
├── references/       # API surface by topic (player, item, game, types, paths, etc.)
├── examples/         # Complete .c / .layout files (copy-paste starting points)
└── depth/            # Measured traps, crashes and migrations from real mods (index: depth/README.md)
```

### patterns/

| File | Topic |
|---|---|
| `modded_class.md` | `super.*` rules, field injection, mod load order, **no-extends rule, NO_GUI guard, engine-backed classes not to mod, extend script class not config parent** |
| `netsync.md` | `RegisterNetSyncVariable*` in the constructor, `SetSynchDirty`, `OnVariablesSynchronized`, bitfield packing |
| `persistence.md` | `OnStoreSave`/`OnStoreLoad`, your own version header (the `version` argument is the game's storage version), write-order rules. For saved fields on a modded vanilla class, migrations and data loss, read the deeper `_shared/persistence/` pack (`versioning-and-migration.md`) |
| `rpc.md` | `ScriptRPC`, `RPCSingleParam`, `OnRPC` switch template, client-to-server validation, **ID-collision symptom** |
| `singleton.md` | Static `s_Instance`, lazy init, `GetInstance()`, `LoadFile`/`SaveFile`, **`ScriptInvoker` shutdown null-guard** |
| `actions.md` | `ActionBase`, registering in `ActionConstructor`, `CCINonRuined` vs `CCINone`, the condition component table, stopping pickup (`IsTakeable`, `CanPutInCargo`, `CanPutIntoHands`), conditions that read unsynced state |
| `scheduler.md` | The unverified `CallLater` drift report and the `Timer` alternative, per tick allocation, reported traps with scheduled calls |
| `physics_items.md` | `ThrowPhysically` vs manual `CreateDynamicPhysics`, `SetDynamicPhysicsLifeTime` mandatory call |
| `json_config_migration.md` | `SCHEMA_VERSION` + forward-migration, `LoadFile` parse-failure handling for admin-edited JSON |
| `language_workarounds.md` | No ternary, `auto` inference, no lambdas, no exceptions; overloading and `foreach` with an index do work |
| `server_tick_budget.md` | Keeping periodic server work inside the tick: one manager with a work budget, staggering, backoff, events in place of polling, compile-time side gates. The techniques are third-party mod behaviour (Expansion AI and a power grid mod), marked as reported; the vanilla calls they use are cited |

### integrations/

| File | Topic |
|---|---|
| `community_framework.md` | CF module system, `GetRPCManager()` RPCs, event handlers between mods (CF `ModStorage` is in `_shared/persistence/cf-modstorage.md`) |
| `lbmaster.md` | LBmaster loot presets (third party): optional `#ifdef` dependency, `SpawnPreset` against `SpawnPresets` chance rules, the order to try loot sources in |
| `dabs_framework.md` | Dabs Framework (third party): attributes, `ScriptView` MVC, layout bindings, `ScriptViewMenu` |
| `expansion_style.md` | Expansion targeted work only: prefixes, settings and module patterns, and where they differ from the vanilla style guide |
| `vanilla_plugins.md` | Registering a plugin in `PluginManager.Init()`, its lifecycle, `GetPlugin()`, `PluginAdminLog.LogPrint` |
| `central_economy.md` | The three mission XML files (`types.xml`, `cfgspawnabletypes.xml`, `cfgeconomycore.xml`), spawn flags, lifetime, `GetCEApi()`, ObjectSpawner JSON |
| `input_bindings.md` | `<modded_inputs>` format, the `CfgMods` `inputs` line, `UAInput` API, `GetUApi()`, context guards |

### references/

Every file below cites the vanilla file and line on `P:\` for its facts, apart from the two exceptions named above. Start with the `language_*` and `api_*` files.

| File | Topic |
|---|---|
| `language_types.md` | Built in types, `auto`, classes and access, enums, casting, `out`/`inout`/`notnull`, static arrays, `array`/`map`/`set` API, templates, strings |
| `language_memory.md` | `Class` against `Managed`, `ref` and weak references, `autoptr`, `delete`, deleting entities, calls and timers that outlive their target |
| `language_compile.md` | Script layers, `modded class`, attributes (`Obsolete`, `NonSerialized`, Workbench), preprocessor defines (`SERVER`, `NO_GUI`, `DIAG_DEVELOPER`) |
| `api_game.md` | `GetGame()` and `g_Game`, side checks, time, mission and world, config reads, logging |
| `api_scheduling.md` | Call categories and when they tick, `ScriptCallQueue`, `Timer`, update queues, `ScriptInvoker`, `ScriptCaller` |
| `api_network.md` | `RPCSingleParam`, `RPC`, `ScriptRPC`, `OnRPC` dispatch, reading payloads, net sync registration and flow |
| `api_entities_inventory.md` | `CreateObjectEx` and `ECE_*` flags, creating in inventory, reading and moving inventory, inventory modes |
| `api_player.md` | Finding players, `PlayerIdentity`, `MissionServer` connect hooks, health zones and types, stats, state checks |
| `api_recipes_energy_damage.md` | Crafting recipes (`RecipeBase`, `PluginRecipesManager`), `ComponentEnergyManager`, and how damage reaches an entity |
| `api_reflection_profiler.md` | Reading and writing fields by name, calling methods by name, creating a class from a string, timing script with `EnProfiler`, the debugging globals |
| `script_module_arena.md` | How much memory the compiler charges a script module (the `4_World` arena), what does and does not shrink it, and how to measure it. Declarations checked on `P:\`; the measurements are reported from one mod on 1.29 |
| `types_collections.md` | Primitive types, string methods, array/map/set API, vector math, `Math` |
| `item_api.md` | `ItemBase` quantity/health/flags, action registration, spawning, `config.cpp` properties |
| `erpc_defines.md` | Vanilla `ERPCs`/`eAgents`/`eModifiers` tables, `ActivateModifier` and `InsertAgent`, custom ID range convention |
| `file_paths.md` | `$profile`/`$saves`/`$mission` path tokens, `FileExist`, `MakeDirectory`, `CopyFile`, `JsonFileLoader.LoadFile`, `FileMode` |
| `gui_layout.md` | `.layout` file format, RGBA colors, coords, every widget class vanilla layouts use, `ItemPreviewWidget`/`PlayerPreviewWidget` |
| `widget_api.md` | Widget script classes and methods, events and `ScriptedWidgetEventHandler`, loading layouts, `UIScriptedMenu`, imagesets |
| `mission_lifecycle.md` | The order `MissionServer` and `MissionGameplay` run constructor, `OnInit`, `OnMissionStart` and `OnUpdate`, where each calls `super`, the client `m_Initialized` guard, RPCs with no target |
| `input_user_data.md` | `ScriptInputUserData`: the player input channel, its `CanStoreInputUserData()` guard, the engine driven receive path, and when to use it instead of `ScriptRPC` |
| `network_payload_limits.md` | Measured, not checkable on `P:\`: string and array sizes each channel delivered, the input queue depth, RPC order across reliability modes, what an acknowledgement proves |
| `native_declarations.md` | Where the `proto native` declarations are, what `owned` and `static` mean on one, calling a native that fills `vector mat[4]` or returns a handle |
| `entity_components.md` | `GenericComponent`, `ScriptComponent` and `GenericEntity` under the `COMPONENT_SYSTEM` guard (Workbench builds): insert and remove, event order, event masks |
| `workbench_api.md` | The Workbench scripting API for plugin authors: what `P:\` holds, the newer `workbenchapi\` folder layout, the `#ifdef WORKBENCH` guard, modules, plugin events |
| `game_builds.md` | Which build `P:\` is, the 1.29 and 1.30 release timeline, which line a citation gives, and the porting rules the 1.30 patches taught |

### depth/

The traps behind the short facts above: compiler and runtime failures, memory, networking, timers, server load, `config.cpp`, vehicle scripting, the DayZ 1.30 script changes, an API lookup catalog and third-party framework patterns, each with the build it was measured on. `depth/README.md` lists every file and the question it answers; open it when a short fact here is not enough or the question is a crash, a silent failure or a 1.29 to 1.30 port.

### examples/

Numbered, complete working files. Reference by number when pointing the agent at a starting point. The layouts start with their root widget like vanilla; their notes and companion scripts are in `examples/layouts.md`.

| # | File | Demonstrates |
|---|---|---|
| 01 | `01_custom_item.c` | Custom item with NetSync bool flag and versioned `OnStoreSave`/`OnStoreLoad` |
| 02 | `02_custom_action_singleuse.c` | Single-use action with `ActionCondition`, registered in `SetActions()` |
| 03 | `03_continuous_action.c` | Hold-to-complete action with a `CAContinuousTime` callback and `OnFinishProgressServer` |
| 04 | `04_rpc_patterns.c` | All three RPC APIs side by side |
| 05 | `05_mission_server.c` | `MissionServer` overrides: connect/disconnect/tick |
| 06 | `06_json_config.c` | `JsonFileLoader` singleton config with nested sub-config |
| 07 | `07_agent_modifier.c` | Custom `ModifierBase` driven by a vanilla agent, registered in a modded `ModifiersManager.Init()` |
| 08 | `08_gui_menu.c` | `UIScriptedMenu` with listbox, filter, buttons |
| 09 | `09_scheduler_timer.c` | `CallLater`, `Timer`, `OnScheduledTick` with frame-skip guard |
| 10 | `10_modded_playerbase.c` | Comprehensive `PlayerBase` mod combining everything |
| 11 | `11_hud_plain_text.layout` | HUD overlay with `TextWidget`s (companion modded `IngameHud` in `layouts.md`) |
| 12 | `12_menu_interactions.layout` | Dialog with `EditBoxWidgetClass` filter, 2-column `TextListboxWidgetClass`, `ButtonWidgetClass` |
| 13 | `13_item_preview.layout` | Item inspect panel with `ItemPreviewWidgetClass` for live 3D model |

## Quick reference — symptom → file

When debugging, jump to the file that owns the symptom.

| Symptom | File |
|---|---|
| `modded class Foo` override never runs | `patterns/modded_class.md` (no-extends rule) |
| HUD code runs or errors on the dedicated server | `patterns/modded_class.md` (`#ifndef NO_GUI` guard, as vanilla does in `dayzgame.c:1061` and `missionserver.c:59`) |
| Can't `modded class Widget` / `UIManager`, or a `UIScriptedMenu` mod hits every menu | `patterns/modded_class.md` (engine-backed classes) |
| Custom barrel missing open/close anim | `patterns/modded_class.md` (extend script class, not config parent) |
| A new action never appears (with `-doLogs -logToScript`, `script.log` shows `Action X dosn't exist!`) | `patterns/actions.md` (register it in `modded class ActionConstructor`) |
| Action shows on client, server rejects on execute | `patterns/actions.md` (condition reads client-only or unsynced state) |
| Tool-in-hand action shows with a ruined tool or none | `patterns/actions.md` (`CCINonRuined` vs `CCINone`) |
| Item placed but still draggable into inventory | `patterns/actions.md` (`CanPutInCargo` and `CanPutIntoHands`) |
| `OnStoreLoad` `version` looks like a game version | `patterns/persistence.md` (it is the storage version) |
| Saved fields on a `modded class ItemBase` or `PlayerBase` load wrong, or old saves break after an update | `_shared/persistence/versioning-and-migration.md` ("Adding saved fields to a vanilla class") |
| `override void Init()` on an item does not compile | `patterns/netsync.md` (register in the constructor) |
| `GetPlugin(MyPlugin)` returns `null` | `integrations/vanilla_plugins.md` (register it in `PluginManager.Init`) |
| Items declared in `config.cpp` never spawn | `integrations/central_economy.md` (the CE reads mission XML only) |
| Long running callback drifts after hours | `patterns/scheduler.md` (unverified `CallLater` report, `Timer` alternative) |
| Frame-time spikes every N seconds | `patterns/scheduler.md` (reported per-tick allocation cost) |
| Item appears frozen in air after spawn | `patterns/physics_items.md` (`ThrowPhysically`) |
| Admin's edited JSON resets / loses fields after mod update | `patterns/json_config_migration.md` (schema migration) |
| RPC fires "wrong handler" with another mod loaded | `patterns/rpc.md` (ID-collision symptom) |
| Crash on shutdown / mission end after `ScriptInvoker.Remove()` | `patterns/singleton.md` (null-guard) |
| Keybind does nothing, no log error | `integrations/input_bindings.md` (`<modded_inputs>`, the `CfgMods` line, the input name) |
| Dabs menu stuck open, no other menus work | `integrations/dabs_framework.md` (wrong layout path trap) |
| Button `OnClick` never fires | `references/widget_api.md` (`ignorepointer`, handler not set) |
| Icon from an imageset is blank | `references/widget_api.md` (imageset not registered in `CfgMods`) |
| Magazine spawns with 0 rounds despite quantity set | `references/item_api.md` (`Magazine.ServerSetAmmoCount`) |
| `SetObjectTexture` no-op, no log warn | `references/item_api.md` (case-sensitivity, index vs name) |
| Whole script file fails to compile, no obvious cause | `references/item_api.md` (`SetObjectTextureGlobal` and `GetObjectTextures` do not exist in vanilla) |
| `ConfigGet*` returns nothing | `references/api_game.md` (space separated path, not dotted) |
| HUD marker jitters at screen edges | `references/api_game.md` (`GetScreenPos` z check) |
| `string.ToLower()` mutates both copies | `references/types_collections.md` (force-allocate via `+ ""`) |
| Older guide says *"write a custom Clamp"* | `references/types_collections.md` (`Math.Clamp` exists) |
| Member set with `new` reads `null` straight after | `references/language_memory.md` (missing `ref`) |
| Call or timer never fires on the dedicated server | `references/api_scheduling.md` (`CALL_CATEGORY_GUI` does not tick without a GUI) |
| Server code inside `#ifdef SERVER` does nothing in offline mode | `references/language_compile.md` (`SERVER` is dedicated only) |
| `Debug.Log` prints nothing | `references/api_game.md` (silent unless logs are enabled) |
| `set.Contains` or `string.StartsWith` does not compile | `references/language_types.md` (methods that do not exist) |
| Modded `MissionGameplay` HUD missing, or client start skipped | `references/mission_lifecycle.md` (`m_Initialized`, `OnMissionStart` must call `super`) |
| `ScriptInputUserData` packet never arrives | `references/input_user_data.md` (guard and routing key) and `references/network_payload_limits.md` (`Write` returns false when full) |
| A cited vanilla line does not match `P:\` | `references/game_builds.md` (which build `P:\` is) |
| `Engine class '...' cannot be modded` | `patterns/modded_class.md` (engine-backed classes) |
| Attachment slot silently rejects modded item | `../conventions/config.md` (T148506: `+=` on a parent whose `inventorySlot` is a string drops the slot) |
