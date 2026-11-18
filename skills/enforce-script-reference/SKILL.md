---
name: enforce-script-reference
description: "Deep reference for writing and reviewing DayZ Enforce Script: the hard rules that stop a compile or crash a server, compiler and runtime traps, script layers (3_Game, 4_World, 5_Mission), memory (ref, autoptr, delete), ScriptRPC, synced variables, OnStoreSave and OnStoreLoad, CallLater and timers, server performance, modded class, config.cpp, inputs.xml keybinds, vehicle scripting and the DayZ 1.30 script changes. Use when writing or reviewing a .c file, when a script module will not compile, on a crash or segfault, when a hook, RPC or synced variable does nothing, to check whether a class, method or enum exists, or when porting a 1.29 mod to 1.30. Full UI, layout and Dabs work is in dayz-ui-development."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Enforce Script reference

Enforce Script is the object oriented script language of the Enfusion engine that DayZ uses. It looks like C# and differs from it in ways that stop a compile or crash a server.

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only: it runs no scripts, so there is no preflight gate.

## How this skill fits with the packs

- The short, checked facts are in the Enforce Script pack, `skills/_shared/enscript/README.md`, and the style guide, `skills/_shared/enscript-style.md`. Read those first for a signature or a pattern.
- This skill holds the depth: failures met in real mods, with the build they were measured on, the error text and the fix. Read the file the table below names for your question; do not read them all.

How to read the evidence in the reference files: a line cited as `P:\...:N` was opened on `P:\` and holds what the text says. "Measured in game" gives the game build; those results were not run again here. A fact about a third-party mod (Community Framework, Expansion, Dabs Framework) names that mod.

## The rules broken most often

The full list, with evidence, is in `references/hard-rules.md`. These are the ones to check on every file:

1. No ternary operator. `++`, `--`, `+=`, `foreach` and string literals as arguments all work.
2. Keep each statement on one line. A condition, a string `+` chain or an argument list continued on the next line can stop the whole module compiling.
3. A local variable has method scope. Do not declare the same name in two `if`, `else` or `case` blocks of one method.
4. Put `ref` on member fields that own an object, never on a parameter or a return type. Break reference cycles in destructors.
5. Write synced variables only on the server and call `SetSynchDirty()`. Register them in the constructor, not in `EEInit`.
6. Check the return value of every `ctx.Read()` and stop on failure. On the server, validate the sender of every RPC.
7. During load, tell the sides apart with `IsDedicatedServer()`; `IsServer()` and `IsClient()` are safe only in callbacks after load.
8. Do not allocate arrays, maps or `Param` objects in a periodic tick. Run periodic work from one place, not one repeating `CallLater` per object.
9. Check every `Cast()` and every creation call for `null` before use.
10. Before you call or mod a vanilla symbol, check that it is not inside an inactive `#ifdef` or a block comment.

Offline checks prove form, not compilation. A script module is known to compile only when the game boots with it: use `/dayz-gate`.

## Which file answers which question

| Question | Read |
|---|---|
| Which rules apply to all Enforce Script (syntax, memory, networking, timers, overrides, actions, layout paths, inputs and keybinds)? | `references/hard-rules.md` |
| Why does the compiler give a misleading error, or none until boot (method scope, split statements, keywords as names, commented out classes, methods under an inactive define)? | `references/compiler-traps.md` |
| It compiles and then crashes or does nothing: client preload, no `Math.Exp`, where `$profile:` points, a scheduled callback that never fires, a path that lost its backslashes | `references/runtime-traps.md` |
| What goes in `3_Game`, `4_World` and `5_Mission`? Why does my `modded class MissionServer` never run? | `references/script-layers.md` |
| Type checks (`GetType`, `ClassName`, `IsKindOf`), entity lifecycle, creating entities and AI, client-local previews, raycasts and surface normals, cooking, custom cameras, inventory moves, respawn | `references/api-patterns.md` |
| What do I scan for before handing code over? What does this error or symptom mean? | `references/review-and-troubleshooting.md` |
| Seat pose, get in, vital parts, wheels that do not simulate, engine state on passengers, vehicle networking | `references/vehicle-scripting.md` |
| `ref`, `autoptr`, `delete`, reference cycles, leaks | `references/memory-management.md` |
| `ScriptRPC`, synced variables, `OnStoreSave` and `OnStoreLoad`, RPC IDs, Community Framework RPCs and modules, JSON file helpers | `references/networking.md` |
| `CallLater`, `Timer`, one central tick, `EnProfiler` | `references/timers-performance.md` |
| Server load: a budget per frame, intervals that follow FPS, staggered scans, backoff, `#ifdef SERVER` against `IsServer()`, an event bus against polling | `references/server-performance.md` |
| Compiler bugs (`int.MIN`, `switch` with `default` return, empty `#ifdef`), runtime segfaults, operator precedence, modded class rules, scoping, debugging tools, string and number traps | `references/pitfalls-advanced.md` |
| `CfgPatches`, `CfgVehicles`, `CfgSlots`, `inventorySlot` overrides, `hiddenSelections`, `model.cfg`, `$PBOPREFIX$`, the 1.30 `ItemBaseType` config keys | `references/config-cpp.md` |
| What changed for scripts in DayZ 1.30, and what breaks in a 1.29 mod? | `references/dayz-1-30-enforce-script.md` |
| Does this function exist? Reflection, global functions, string, math and config lookup calls | `references/verified-api-catalog.md` |
| Recipes and crafting, the energy manager, the action system, the damage pipeline, player internals and sync, read from vanilla | `references/vanilla-deep-dive.md` |
| Fire modes on a derived weapon (single, burst, full auto) and the `Mode_*` forward declaration trap | `references/weapon-firemodes.md` |
| Dabs MVC traps: `ObservableCollection`, auto binding, `Relay_Command`, floating windows, hover, scaling | `references/dabs-mvc-advanced.md` |
| UI state, hover caching, view binding, animation and event handler patterns from shipped mods | `references/production-patterns.md` |
| Mod structure patterns: `CfgMods`, custom inputs, `CfgSoundSets` parameters, building doors, RPC enums, server-authoritative input, parent and child mods | `references/mod-structure-patterns.md` |

Full UI, layout, widget and Dabs work is in the `dayz-ui-development` skill; this skill keeps only the layout path and menu guard rules and the `CfgMods` `inputs` entry.

## Offline check before a boot

The script validator reads a mod's scripts, layouts and configs without the game:

```cmd
python scripts\tools\dayz-script-validator\scripts\script_validator.py <addon_root>
python scripts\tools\dayz-script-validator\scripts\ui_reconcile.py <addon_root>
```

Run both from the repo root; the paths do not exist from inside a mod folder. `/dayz-lint <ModName>` runs `script_validator.py` as its second stage, after the mod setup checks, and prints the findings as `file:line` with an owner and a fix, so for a mod under `workspace/` one lint run covers the first command. `ui_reconcile.py` is not part of lint; run it by hand.

- `script_validator.py` prints JSON on stdout and exits 0 for PASS, 1 for FAIL and 2 for WARN. A clean tree with warnings exits 2, so a caller that tests "not 0" rejects it: count the errors in the JSON, or accept 2.
- `ui_reconcile.py` matches `FindAnyWidget` names against layouts and `#STR` keys against the stringtable, which no compiler checks. `--strict` turns its warnings into a failure.

`/dayz-lint` checks the mod's setup (`config.cpp`, `CfgPatches`, prefix, script modules). Neither replaces a boot.

## DayZ 1.30 in short

The bodies and the full migration list are in `references/dayz-1-30-enforce-script.md`.

- **What changed.** The Central Economy tick is `OnCEIterate(float currentTime, float elapsedTime)`; `OnCEUpdate` is `[Obsolete]`. The inventory network path is `ValidateInventoryCommandServer` plus `ExecuteInventoryCommandServer`, `Client` and `Remote`, with `INPUT_UDT_INVENTORY_CHECK` and `OnInventoryCheck`; retail no longer calls `ProcessInputData`. `TakeEntityToCargo*` and `TakeEntityAsAttachment*` are `[Obsolete]` in favour of the `Target` forms. Hand guards no longer pass on `m_IsJuncture` alone, and `HandGuardIsNotSurrendered` blocks surrendered players. `ItemBaseType` caches `headSelectionsToHide`, `varWetMax` and the `GUIInventoryAttachmentsProps` groups. Actions gained `CanBeStarted`, `SortActions` and `IsTargetInfoAction`; `ActionFillBottleBase` gave way to `ActionObtainLiquidBase` with `CCTLiquid`; animation overrides moved to `EntityAI.OverrideActionAnimation`. New engine calls: `World.GetThirdPersonViewMode()`, `Weather.GetNoiseReductionByWeatherEx`, `array.Slice`, `EnumFlagsToString`, `DoOnce`, `DayZPlayer.IsFirstRenderFrame`. `vector.Cross` was a script method in 1.30.164014 and 1.30.164078 and is gone in 1.30.164200: write its body inline. `GAME_STORAGE_VERSION` is 144.
- **What breaks in a 1.29 mod.** An `override OnCEUpdate`, a modded `ProcessInputData`, `AddAction(ActionFillBottleBase)`, `ItemBase.m_ItemActionOverrides`, hard-coded `UA_AM_*` numbers, and `Is3rdPersonDisabled()` read as a bool. A recipe that replaces an ingredient no longer overwrites the result's health. A fill or drink target condition copied from `CCTWaterSurfaceEx` misses vanilla liquid.
- **Checklist.** `OnCEIterate` with `super`. Observe completed inventory moves through `ItemBase.EEItemLocationChanged`; `ProcessInputData` has no moddable replacement. `Target` take calls. `ActionObtainLiquidBase`. `OverrideActionAnimation` on the entity. `CanBeStarted` for info only actions. `CCTLiquid` with `GetPlayerHeadPosition`. `ThirdPersonMode.ENABLED`. Storage version 144. No hard-coded `UA_AM_*`. Do not treat `GetNoiseReductionByWeatherEx` as the AI noise damper: that is in the native AI parameters, and the `Ex` call is kept for the HUD.

## On Linux

Everything above is the Windows workflow. On Linux, the Proton setup, the measured tool matrix and the traps are in `skills/_shared/linux-proton.md`. What changes for this skill:

- **Vanilla scripts.** Unpack the installed script PBOs with `dayzmake unpack`, keeping their prefix paths, and cite the extracted file and the game build. Use dayzmake `v2.0.0` (commit `f31056ae`) or later: its unpacker skips unsafe entry names (`safe_relative_path` and `crosses_symlink` in `src/pbo.rs`), which `v1.0.0` does not, so with an older version inspect every entry name first, as the `dayz-pbo-reverse-engineering` skill describes. `skills/_shared/scripts/extract-dayz-sources.sh <install> <dir>` extracts every script and unpacked config (about 90 s for the vanilla install).
- **Does this symbol exist.** `skills/_shared/scripts/build-api-index.py <dir>/scripts ~/.cache/dayz-api` builds an index of declarations, and `skills/_shared/scripts/dayz-api.py` queries it with `class`, `find`, `chain`, `sub`, `enum` or `src` and a name. The index holds Bohemia's declarations, so build it locally and never ship it. Online, `https://diff.yadz.app/api/classes/<Name>.json` gives one class of the latest build as JSON (`base`, `bases` with the define a base depends on, `methods`, `members`, file and line); `api/enums/<Name>.json` and `api/globals.json` cover the rest, and `api.json` is only a name index. Not checked here; the site served build 1.30.164078 when this was written.
- **Script logs.** The native server writes to its `-profiles` folder. The Proton client writes to `<prefix>/pfx/drive_c/users/steamuser/AppData/Local/DayZ`, or to its `-profiles=` folder.
- **Defines.** The native Linux server defines `PLATFORM_LINUX` and also `SERVER_FOR_WINDOWS` (observed). DayZDiag and the client under Proton define `PLATFORM_WINDOWS`. Do not use either define to mean "the host runs Windows".

## Building, testing and publishing

When the work must end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow the `dayz-mod-dev` skill. In this repo the steps are `/dayz-build-pbo`, `/dayz-gate` and `/dayz-launch-test`.
