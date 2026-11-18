# Script module memory

How much memory the Enforce Script compiler charges a script module (the module's arena), what does and doesn't shrink it, and how to measure it. For a large mod whose World module is close to the limit the server allows.

The script declarations are cited from `P:\`. The measurements are from one production mod with about 1.2 MB of World module scripts on DayZ 1.29, and can't be checked on `P:\`. The numbers belong to that mod; the rules and the method hold for any mod. Don't turn one observed slope into a constant.

## The capacity check

```text
candidate.World - empty.World <= limit
```

A small saving you can explain is not a pass. A pass also names the mod stack it was measured with: a pair of runs where only your PBO changes measures its cost in that stack, not that another stack will fit.

Trust the evidence in this order:

1. The module difference between two runs back to back with the same build, mod stack, load order, mission, config and files, with all of Game, World and Mission reported.
2. The engine's class counter, calibrated for each kind of class.
3. Bytecode removed from the server's preprocessed view, as a forecast only, and only when the code really leaves the module.
4. Counts of declarations, methods, lines, source bytes and PBO size. These are inventories and don't predict the arena alone.

## What doesn't move it

Measured World change, two runs each:

| Change | Structural change | World, kB |
|---|---|---:|
| 16 fewer files, same classes | none | 0 and -1 |
| 1,071,376 fewer source bytes, same classes | none | -2 and 0 |
| 3 fewer small shell classes | 3 classes | 1 and 0 |
| 1 fewer large class, 19,670 fewer characters that aren't white space | 1 class | 44 and 45 |
| 12 fewer generic classes | 12 types | 79 and 77 |
| 18 fewer engine types | 18 types | 101 and 101 |
| 3 fewer generic expressions in source, same classes | none | -3 |
| Same classes, real server bytecode removed | none | 28 and 29 |

The compiler charges structure, bytecode and generics it has to build, not the text that spells them. A million source bytes was worth 0 kB; twelve generic classes were worth about 78 kB.

## Rules

| Rule | Why it matters |
|---|---|
| Calibrate classes by kind | Generic specializations cost about 5.6 to 6.6 kB per engine type in the measured mod, while a small ordinary class can cost 0 kB. One "kB per class" figure picks the wrong work |
| A generic expression removed is not a generic type removed | Removing three `JsonFileLoader<T>` uses didn't lower the engine's counter. A source scan is a first check, not a result |
| Count removed code net | Removed body, minus the replacement source, minus shared helpers added. One refactor was 277,983 characters gross and only 2,700 net |
| The server's preprocessor counts | A whole class under `#ifndef SERVER` stops being counted (6141 to 6140 classes). Analyse with the exact defines of the run; a plain text search gives a false inventory |
| The class counter includes generated types | It is not a count of the word `class`: 203 was 187 declarations, 14 new generics and 2 left over |
| Report every module | Report Game, World, Mission and the total. A World drop that grows another module, another PBO or run time by as much moves the cost; it doesn't remove it |
| A PBO is not an arena | The `files[]` of the script module classes in `CfgMods` decide where a script compiles. Several PBOs that declare `worldScriptModule` all feed World, so splitting the packing inside one module saves 0 kB |
| Only five script module keys exist | Engine, GameLib, Game, World and Mission. A scan of 1,238 `config.cpp` files and 1,098 `class *ScriptModule` declarations finds no other key |

A vanilla `worldScriptModule` with its `files[]` is in the Sakhal data addon (`P:\DZ\data_sakhal\config.cpp:21` to `:27`). The script layers themselves are in `language_compile.md`.

## What works: a World base with its bodies in Mission

A base class declared in `4_World` whose method bodies live in a subclass declared in `5_Mission` keeps that code out of the World arena. Vanilla uses the same shape:

- `P:\scripts\4_world\classes\missionbaseworld.c:3`: the base, in World, declares `GetRainProcurementHandler()` returning `null`.
- `P:\scripts\5_mission\mission\missionserver.c:835`: the `override` with the real body, in Mission.
- `P:\scripts\4_world\classes\rainprocurementcomponent.c:14`: the caller goes through the base type, `MissionBaseWorld.Cast(g_Game.GetMission()).GetRainProcurementHandler()`.
- `P:\scripts\5_mission\mission\missionbase.c:1`: `class MissionBase extends MissionBaseWorld` inherits across the modules.

Measured on a test class of 200 small methods, two pairs of runs:

| | Bodies in World | Bodies in Mission | Moved |
|---|---|---|---|
| World above the baseline | +116 and +118 kB | +53 and +54 kB | 63 and 64 kB (54 %) |

- The shell isn't free. The signatures stay declared in World: 53 of the 116 kB stayed. The share that moves depends on how big the bodies are next to the signatures. The test class was 33 % signatures; a class of 49 large methods is about 4 % and moves much more.
- It moves the cost, it doesn't cut it. Mission goes up 103 kB, and the duplicated signatures add 39 kB. With real classes, two pairs: World -139 and -140 kB, Mission +142 and +142 kB, Game 0, total +3 and +2 kB.

When World is at 97 % and Mission at 39 %, the server fails on module capacity although total memory is plenty. Moving bodies to Mission is a fair answer, but call it a rebalance. Mission is a better target than Game for a World core: it compiles later and can name World types, while Game compiles earlier and can't.

## Calling across modules by name

When the base and subclass shape isn't possible, these calls are declared in `P:\scripts\1_core\proto\enscript.c`, with the header's own notes:

- `Call` (`enscript.c:139`): "The call creates new thread, so it's legal to use sleep/wait".
- `CallFunction` (`:146`) and `CallFunctionParams` (`:147`): "The call do not create new thread!!!!".
- `LoadScript` (`:160`) creates a child module. It shows no separate arena and no loading from the virtual file system or a PBO.

Use one call per coarse event, never per getter; a fixed function name that never comes from the client; a checked result; failing closed before any side effect; a rate limited warning; and no such call at all in ticks, loops, scans, timers or periodic callbacks. Unlike the base and subclass shape, this only suits code that nothing in World calls.

A child module can have its own arena, but that is not a saving. The mission's `init.c` shows up as a separate module with 1 file and 1 class. If World drops and the cost comes back in a child module you don't count, the total is no longer complete.

## Measuring it

- Run three variants, not two: the baseline, a positive control and the candidate. The control adds code the ordinary way and has to move World; if it doesn't, the probe measured nothing (the class was dropped as unused, the file was outside the module, the build didn't pick up the change) and the candidate result is void. Write the predicted number for all three before you measure.
- Keep two results apart: that the mechanism works (World drops, the rest adds up, behaviour still passes), and that it scales to your target with the code you can really move. A mechanism that saves 4 kB doesn't prove the larger move.
- Stop when the estimate depends on deleting behaviour that must come back elsewhere, when the change adds loops, scans, timers or calls to replace a static cost, when the counter drops but World doesn't move by more than the measurement step, or when the total saving is smaller than the World saving.

A `-mod` line fixes the load order and the mod roots, not which PBOs are inside each root. To compare runs, record each root's exact PBO list with sizes and the same list before and after each run. With `-filePatching`, an empty mod means an empty folder tree, checked all the way down; checking only `Addons\*.pbo` misses a stray script, an extra subfolder or a link.

When you check whether anything outside references your class names, run the same search on a file that does contain them first. If that finds nothing, a zero from the rest means nothing.
