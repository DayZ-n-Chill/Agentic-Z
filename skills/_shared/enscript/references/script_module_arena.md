# Script module memory: what the `4_World` arena really charges

How much memory the Enforce Script compiler charges a script module (the module's "arena"), what does and does not shrink it, and how to measure it without fooling yourself. For a large mod whose World module is close to the limit the server allows.

The script declarations cited here were checked on `P:\` (DayZ 1.30). The measurements were made on DayZ 1.29.163451, in a production mod with about 1.2 MB of World module scripts, and cannot be checked on `P:\`. The concrete numbers belong to that mod; the rules and the method belong to the engine. Keep engine fact, inference and product constraint apart: do not turn one observed slope into a universal constant.

## The only capacity verdict

```
candidate.World - empty.World <= limit
```

A small saving that you can explain is not a capacity pass. A pass also names the mod stack it belongs to: a pair of runs where only the product's PBO changes measures the candidate's absolute cost in that snapshot, not that another stack will fit. Use separate result names (for example `PROSPECTIVE_SNAPSHOT_CAPACITY_PASS`, `PROSPECTIVE_SNAPSHOT_CAPACITY_FAIL`, `AFFECTED_STACK_NOT_RUN`) and not one ambiguous "pass".

## Ranking of evidence

From most to least authority:

1. **The module difference between two adjacent engine runs:** same build, mod stack, load order, mission, config and artifacts; all of Game, World and Mission reported.
2. **The engine's class counter, calibrated per family of classes.**
3. **Bytecode removed from the server's preprocessed view,** good for a forecast only when the behavior really leaves the module.
4. **Declarations, methods, lines, source bytes and PBO size.** These are inventories. Alone they do not predict the arena.

## What is not a proxy (measured)

| Change | Structural change | World, kB (two runs) |
|---|---|---:|
| 16 fewer files, same classes | none | 0 and -1 |
| 1,071,376 fewer source bytes, same classes | none | -2 and 0 |
| 3 fewer kit shell classes | 3 classes | 1 and 0 |
| 1 fewer large class, 19,670 fewer characters that are not whitespace | 1 class | 44 and 45 |
| 12 fewer generic classes | 12 units | 79 and 77 |
| 18 fewer engine units | 18 units | 101 and 101 |
| 3 fewer generic expressions in source, same classes | none | -3 |
| same classes, real server bytecode removed | none | 28 and 29 |

The compiler charges structure, bytecode and materialized generics, not the text that spells them. One million source bytes was worth 0 kB; twelve generic classes were worth about 78 kB.

## The rules

| # | Rule | Why it bites |
|---|---|---|
| 1 | Classes are calibrated per family | The observed band was about 5.6 to 6.6 kB per engine unit for generic specializations, but a small ordinary class can cost 0 kB. One global "kB per class" figure picks the wrong work. |
| 2 | A generic expression removed is not a materialization removed | Removing three `JsonFileLoader<T>` uses from the model did not lower the engine's counter. A source scan is a precondition, not a verdict. |
| 3 | Count mass net | Removed body, minus the exact replacement source, minus shared helpers added. One refactor showed 277,983 characters gross and only 2,700 net. |
| 4 | The server's preprocessor counts | A whole class under `#ifndef SERVER` stopped being counted (6141 to 6140). Analyze with the exact defines of the run; a raw text search makes a false inventory. |
| 5 | The class counter includes generated types | It is not a count of the word `class`: 203 was 187 declarations plus 14 new generics plus 2 left over. Subtraction sizes the gap; it does not name it. |
| 6 | No moving the cost around | Report Game, World, Mission and the total. A World reduction that grows another module, another PBO or run time by as much does not relieve the pressure; it moves it. |
| 7 | A PBO is not an arena | The `files[]` of the script module classes in `CfgMods` decide where a script compiles. Several PBOs that declare `worldScriptModule` all feed World: splitting the packaging within one module saves 0 kB. |
| 8 | Only five script module keys exist | Engine, GameLib, Game, World and Mission. A scan of 1,238 `config.cpp` files and 1,098 `class *ScriptModule` declarations found no custom key. |

For rule 7, a vanilla example of the config: `class worldScriptModule` with `files[]` in the Sakhal data addon (`P:\DZ\data_sakhal\config.cpp:21` to `:27`). The script layers themselves are in `language_compile.md`.

## The lever that works: a World base with its bodies in Mission

Measured, two reproducible pairs, on a synthetic probe of 200 methods: a base class declared in `4_World` whose method bodies live in a subclass declared in `5_Mission` keeps that mass out of the World arena.

It is not a trick. It is a pattern vanilla uses, and its four parts sit in the two modules exactly as the pattern needs:

- `P:\scripts\4_world\classes\missionbaseworld.c:3`: the base, in World, declares `GetRainProcurementHandler()` returning `null`.
- `P:\scripts\5_mission\mission\missionserver.c:835`: the `override` of `GetRainProcurementHandler` with the real body, in Mission.
- `P:\scripts\4_world\classes\rainprocurementcomponent.c:14`: the caller goes through the base type, `MissionBaseWorld.Cast(g_Game.GetMission()).GetRainProcurementHandler()`.
- `P:\scripts\5_mission\mission\missionbase.c:1`: `class MissionBase extends MissionBaseWorld` inherits across the modules.

| | Control (bodies in World) | Candidate (bodies in Mission) | Moved |
|---|---|---|---|
| World above the baseline | +116 and +118 kB | +53 and +54 kB | 63 and 64 kB (54 %) |

Two points decide whether it helps you:

- **The shell is not free.** The signatures stay declared in World: 53 of the 116 kB stayed. The share that moves depends on the ratio of body to signature, so it does not scale in a straight line between classes. The probe was 33 % signatures (200 tiny methods); a class of 49 fat methods is about 4 % and moves much more.
- **It is transport, not reduction.** Mission goes up 103 kB, and the duplicated signatures add 39 kB. In two pairs with real classes: World -139 and -140 kB, Mission +142 and +142 kB, Game 0, total +3 and +2 kB.

When World is at 97 % and Mission at 39 %, the server fails on module capacity even though total memory is plenty. Rebalancing is a fair answer, but call it an arena rebalance: it does not meet a "no moving the cost around" requirement.

Mission is a better target than Game for a World core: it compiles later and can name World types; Game compiles earlier and cannot.

## The dynamic bridge, when the facade is not possible

These calls are declared in `P:\scripts\1_core\proto\enscript.c`, with the notes from the header itself:

- `Call` (`P:\scripts\1_core\proto\enscript.c:139`): "The call creates new thread, so it's legal to use sleep/wait".
- `CallFunction` (`P:\scripts\1_core\proto\enscript.c:146`) and `CallFunctionParams` (`:147`): "The call do not create new thread!!!!".
- `LoadScript` (`P:\scripts\1_core\proto\enscript.c:160`): creates a child module, but that does not show a separate arena, nor loading from the virtual file system or a PBO.

Required pattern: one call per coarse event (never per getter), a fixed function name that does not come from the client, a checked result, fail closed before any side effect, a rate limited warning, and no dispatch at all in ticks, loops, scans, timers or periodic callbacks.

The difference from the facade: the bridge only allows islands with no callers from World; the facade is ordinary virtual dispatch and leaves the call sites alone.

A child module can have its own arena, but that is not a saving. The mission's `init.c` shows up as a separate module with 1 file and 1 class. If a change lowers World and the cost comes back in a child you do not count, the three module total is no longer complete: the cost was moved without being counted.

## Method: two rules that hold outside DayZ

**An experiment that removes a cost needs a positive control.** A probe with two variants, without the thing and with it, gives an ambiguous zero: when the candidate does not move the metric you cannot tell "the mechanism works" from "the probe measured nothing" (the class was dropped as unreferenced, the file was outside the module, the build did not pick up the change). Always run three variants: baseline, positive control, candidate. The control injects mass the ordinary way and has to move the metric; if it does not, the experiment is void and the candidate is not read. Write the predicted number for all three rows before measuring: an experiment whose prediction is written afterward cannot fail.

**A minimal pilot must be able to fail.** A typical gate: all modules reported, the expected class counter, a World saving of at least 4 kB, Game and Mission not growing, a total saving at least as large as the World saving, a functional test, an exact stop, and cleanup. Keep the pilot's two verdicts apart: the mechanism (World drops, the rest adds up, behavior passes) and the scale (the measured density, applied to the mass that can really be moved, reaches the target with margin). A mechanism that yields 4 kB does not authorize scaling up.

## Stop signals

- The estimate depends on deleting behavior that must later come back in another class.
- The proposal adds loops, scans, timers, callbacks or dispatch to replace a static cost, with no stated intent.
- The family mixes shell classes, templates and large classes.
- The counter drops but World does not move by more than the measurement step.
- The total saving is smaller than the World saving.
- A file hash drifts, or the measured candidate is not the normal build.

## Freezing the stack means freezing PBOs

A `-mod` line proves the order and the roots, not which PBOs were inside each root. For a gate that fails closed, the minimum identity of each input is: the mod path and its order; the exact set of PBOs under that root; the size and SHA-256 of each; a digest of its file listing; an explicit "zero files" manifest for an empty root; and the same manifest before and after each run. When any of these is missing, record `INVENTORY_INCOMPLETE`; never turn it into "zero consumers".

With `-filePatching`, an "empty mod" means an empty folder tree, checked recursively. Checking only `Addons\*.pbo` does not freeze a mod: a stray script, an unexpected subfolder or a link changes the real input even when the PBO count is zero.

A positive control tells "zero hits" from "broken search". When checking whether anything outside references your class names, run the detector against an artifact that does contain them. If the control finds nothing, a zero from the rest means nothing.
