# Enforce Script depth

The depth part of the Enforce Script pack: failures met in real mods, with the build they were measured on, the error text and the fix. The short, checked facts are one level up in `../README.md` (`references/`, `patterns/`, `integrations/`); read those first for a signature or a pattern, and open the file below only when the question is a trap, a crash or a migration. Open only the file the question names.

How to read the evidence in these files: a line cited as `P:\...:N` was opened on `P:\` and holds what the text says. "Measured in game" gives the game build; those results were not run again here. A fact about a third-party mod (Community Framework, Expansion, Dabs Framework) names that mod.

| Question | Read |
|---|---|
| Which rules apply to all Enforce Script (syntax, memory, networking, timers, overrides, actions, layout paths, inputs and keybinds)? | `hard-rules.md` |
| Why does the compiler give a misleading error, or none until boot (method scope, split statements, keywords as names, commented out classes, methods under an inactive define)? | `compiler-traps.md` |
| It compiles and then crashes or does nothing: client preload, no `Math.Exp`, where `$profile:` points, a scheduled callback that never fires, a path that lost its backslashes | `runtime-traps.md` |
| What goes in `3_Game`, `4_World` and `5_Mission`? Why does my `modded class MissionServer` never run? | `script-layers.md` |
| Type checks (`GetType`, `ClassName`, `IsKindOf`), entity lifecycle, creating entities and AI, client-local previews, raycasts and surface normals, cooking, custom cameras, inventory moves, respawn | `api-patterns.md` |
| What do I scan for before handing code over? What does this error or symptom mean? | `review-and-troubleshooting.md` |
| Seat pose, get in, vital parts, wheels that do not simulate, engine state on passengers, vehicle networking | `vehicle-scripting.md` |
| `ref`, `autoptr`, `delete`, reference cycles, leaks | `memory-management.md` |
| `ScriptRPC`, synced variables, `OnStoreSave` and `OnStoreLoad`, RPC IDs, Community Framework RPCs and modules, JSON file helpers | `networking.md` |
| `CallLater`, `Timer`, one central tick, `EnProfiler` | `timers-performance.md` |
| Server load: a budget per frame, intervals that follow FPS, staggered scans, backoff, `#ifdef SERVER` against `IsServer()`, an event bus against polling | `server-performance.md` |
| Compiler bugs (`int.MIN`, `switch` with `default` return, empty `#ifdef`), runtime segfaults, operator precedence, modded class rules, scoping, debugging tools, string and number traps | `pitfalls-advanced.md` |
| `CfgPatches`, `CfgVehicles`, `CfgSlots`, `inventorySlot` overrides, `hiddenSelections`, `model.cfg`, `$PBOPREFIX$`, the 1.30 `ItemBaseType` config keys | `config-cpp.md` |
| What changed for scripts in DayZ 1.30, and what breaks in a 1.29 mod? | `dayz-1-30-enforce-script.md` |
| Does this function exist? Reflection, global functions, string, math and config lookup calls | `verified-api-catalog.md` |
| Recipes and crafting, the energy manager, the action system, the damage pipeline, player internals and sync, read from vanilla | `vanilla-deep-dive.md` |
| Dabs MVC traps: `ObservableCollection`, auto binding, `Relay_Command`, floating windows, hover, scaling | `dabs-mvc-advanced.md` |
| UI state, hover caching, view binding, animation and event handler patterns from shipped mods | `production-patterns.md` |
| Mod structure patterns: `CfgMods`, custom inputs, `CfgSoundSets` parameters, building doors, RPC enums, server-authoritative input, parent and child mods | `mod-structure-patterns.md` |

Fire modes on a derived weapon are in `../../weapons/recoil-fire-modes.md` and `../../weapons/weapon-config.md`. Full UI, layout, widget and Dabs work is in the `dayz-ui-development` skill.

## Offline checks prove form, not compilation

The script validator in `scripts/tools/dayz-script-validator/` reads a mod's scripts, layouts and configs without the game; how to run it and what its exit codes mean is in `docs/tools.md`. `/dayz-lint <ModName>` runs `script_validator.py` as its second stage; `ui_reconcile.py` is not part of lint, so run it by hand. A script module is known to compile only when the game boots with it: use `/dayz-gate`.

## On Linux

The Proton setup, unpacking the vanilla scripts and the local script API index are in `../../linux-proton.md` and `../../scripts/README.md`; the platform defines are in `../references/language_compile.md`. One note found nowhere else: DayZDiag and the client under Proton define `PLATFORM_WINDOWS`, while the native Linux server defines `PLATFORM_LINUX` and `SERVER_FOR_WINDOWS`. Do not use either define to mean "the host runs Windows".
