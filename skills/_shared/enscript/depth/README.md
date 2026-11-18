# Enforce Script depth

Traps, crashes and migrations met in real mods, each with the error text and the fix. The short checked facts sit one level up in `../README.md` (`references/`, `patterns/`, `integrations/`); read those first for a signature or a pattern, and open one file below only when the question is a trap, a crash or a migration.

Every fact cites the vanilla file on `P:\` it came from. Line numbers match the vanilla data at the time of writing; when a line has moved, Grep for the class or method name in the same file. A result marked "measured in game" was seen in a running game and is not visible in the scripts. "Reported" means it comes from mod authors and is not checked on `P:\`. A fact about a third-party mod (Community Framework, Expansion, Dabs Framework, VPPAdminTools) names that mod and its source.

## The rules broken most often

The full rules are in `hard-rules.md` and `action-and-input-rules.md`. Check these in every file:

- No ternary operator. `++`, `--`, `+=`, `foreach` and string literals as arguments all work.
- Keep each statement on one line. A condition, a string `+` chain or an argument list continued on the next line can stop the whole module compiling.
- A local has method scope: never declare the same name in two `if`, `else` or `case` blocks of one method.
- Put `ref` on member fields that own an object, never on a parameter or a return type, and break reference cycles in destructors.
- Write synced variables only on the server, then call `SetSynchDirty()`; register them in the constructor, not in `EEInit`.
- Check every `ctx.Read()` and stop on failure; on the server, validate the sender of every RPC.
- During load, tell the sides apart with `IsDedicatedServer()`; `IsServer()` and `IsClient()` are safe only in callbacks after load.
- Never allocate arrays, maps or `Param` objects in a periodic tick, and run periodic work from one manager, not one repeating `CallLater` per object.
- Check every `Cast()` and every creation call for `null` before use.
- Before calling or modding a vanilla symbol, check that it is not inside an inactive `#ifdef` or a block comment.

## Which file to open

| Question | File |
|---|---|
| Which rules apply to all Enforce Script: syntax, memory, sides, timers, overrides, layouts | `hard-rules.md` |
| Which rules keep actions, recipes, liquid containers, input files and vehicle sights working | `action-and-input-rules.md` |
| Why does the compiler give a misleading error, or none until boot: method scope, split statements, commented out classes, inactive defines | `compiler-traps.md` |
| Which code the compiler mishandles (`int.MIN`, `switch` with `default`, `%` beside a float, long formulas), and what a log line means | `pitfalls-advanced.md` |
| It compiles, then crashes or does nothing: client preload, no `Math.Exp`, where `$profile:` points, a callback that never fires, lost backslashes | `runtime-traps.md` |
| It crashes, loses items or runs slow: array element assignment, hologram ghosts, merge loops, float time, slow world queries, retail admin calls | `runtime-pitfalls.md` |
| How a `modded class` adds fields safely, where it must live, and how to gate code on another mod or on diag | `modded-class-and-defines.md` |
| What goes in `3_Game`, `4_World` and `5_Mission`, and why my `modded class MissionServer` never runs | `script-layers.md` |
| Type checks, entity lifecycle, creating entities and AI, client-local previews, rays and normals, cooking, cameras, inventory moves, respawn | `api-patterns.md` |
| What to scan before handing code over, and what an error or symptom means | `review-and-troubleshooting.md` |
| `ref`, `autoptr`, `delete`, reference cycles, leaks | `memory-management.md` |
| Synced variables, what replicates on its own, side checks during load | `networking.md` |
| Where a `ScriptRPC` lands, why a reply must target the player, what the server checks, reading `Event_OnRPC` safely | `rpc-routing.md` |
| One RPC ID with dispatch by function name, Community Framework modules and single player RPCs | `rpc-manager-and-cf.md` |
| Saving fields with a mod version, `storageCategory`, JSON calls that report errors, safe file writes | `persistence-and-files.md` |
| RPC numbers by direction, client lock with server decision, sending to all clients, caching inputs, skipping client work on a server | `rpc-and-input-patterns.md` |
| `CallLater` over long uptimes, a callback that queues itself again, `Timer`, one central tick for many devices | `timers.md` |
| Which script is slow: `EnProfiler`, and fixes for strings, `IsKindOf`, distances, RPCs and config reads in a hot path | `script-profiling.md` |
| Keeping many entities in one tick: a fair budget, intervals that follow load, staggered scans, backoff | `server-performance.md` |
| `#ifdef SERVER` against `IsServer()`, `#ifndef SERVER` breaking other mods, events against polling, server script memory | `server-side-gates.md` |
| `CfgPatches`, `CfgMods` modules, item and kit config, the 1.30 item keys, slots, `hiddenSelections`, `model.cfg`, `$PBOPREFIX$` | `config-cpp.md` |
| `class defs`, hiding a library, a parent mod with feature mods, custom inputs and which keys to avoid | `mod-structure-patterns.md` |
| Doors on a building, an indestructible building with damageable doors, sound set keys | `buildings-and-sound-config.md` |
| What changed for scripts in DayZ 1.30, and what breaks in a 1.29 mod | `dayz-1-30-enforce-script.md` |
| 1.30 inventory: the command path, engine classes that cannot be modded, watching item moves, stacking and splitting, take calls, hand guards | `dayz-1-30-inventory.md` |
| 1.30 actions: info actions, action states, the liquid action, animation overrides, target conditions, new inputs, recipes, the targets cursor | `dayz-1-30-actions.md` |
| Fields and methods by name, creating a class from a string, load time attributes, a safe reflection test | `reflection-api.md` |
| Screen, launch parameters, folders, web requests, sound, notifications, online players, JSON, frame callbacks, key bindings, weather, bones | `global-functions.md` |
| Parameter limits, generic classes, float constants, string and maths calls, config lookups, 1.30 language additions | `language-builtins.md` |
| Attach hooks, showing selections, which slot list to read, texture getters, player stats, inventory calls, what 1.30 renamed | `entity-inventory-api.md` |
| Action base classes, condition components, overrides, registration, `MissionServer` connect and disconnect events | `actions-mission-api.md` |
| How actions are registered and how far they reach, stamina sync, synced modifier bits, player stat indices, agents | `actions-and-player-sync.md` |
| Seat pose, get in, vital parts, wheels that do not simulate, engine state for passengers, vehicle networking | `vehicle-scripting.md` |
| Cheap vehicle animation and sync, damping an empty vehicle, effect cleanup, water, damage zones, the local driver, seat animation sets | `vehicle-script-helpers.md` |
| Dabs MVC traps: property names, creating views, auto binding in buttons, `Relay_Command` firing twice, collection leaks | `dabs-mvc-advanced.md` |
| A floating window: input without a modal, dragging, colour, hover, scaling | `dabs-floating-windows.md` |
| Hover caches, disabled controls, one animation at a time, batched updates, input locks, what the action cursor promises | `production-patterns.md` |
| What to bind, releasing collections and singleton views, no allocation in update loops, many buttons | `ui-view-lifecycle.md` |

Fire modes on a derived weapon are in `../../weapons/recoil-fire-modes.md` and `../../weapons/weapon-config.md`. Full UI, layout, widget and Dabs work is in the UI pack, `_shared/ui/`.

## Offline checks prove form, not compilation

The script validator in `scripts/tools/dayz-script-validator/` reads a mod's scripts, layouts and configs without the game; how to run it and what its exit codes mean is in `docs/tools.md`. `/dayz-lint <ModName>` runs `script_validator.py` as its second stage. `ui_reconcile.py` is not part of lint, so run it by hand: it matches `FindAnyWidget` names against layouts and `#STR` keys against the stringtable, which no compiler checks, and `--strict` turns its warnings into a failure. `script_validator.py` exits 2 for a clean tree with warnings, so a caller that rejects any non-zero exit rejects it; count the errors in the JSON, or accept 2. A script module is known to compile only when the game boots with it: use `/dayz-gate`.

## On Linux

The Proton setup, unpacking the vanilla scripts and the local script API index are in `../../linux-proton.md` and `scripts/tools/dayz-linux/README.md`; the platform defines are in `../references/language_compile.md`. DayZDiag and the client under Proton define `PLATFORM_WINDOWS`, while the native Linux server defines `PLATFORM_LINUX` and `SERVER_FOR_WINDOWS`, so never use either define to mean "the host runs Windows".
