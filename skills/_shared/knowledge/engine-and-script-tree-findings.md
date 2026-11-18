# Engine and script-tree findings for tools that read the vanilla scripts

Tier 3 pack: a short list of DayZ engine and script-tree facts that no other pack file carries. Load it when writing a tool that reads the vanilla script tree, or when a compile error or a preprocessor question matches one of the headings. Tier 1 and Tier 2 still apply on top.

The build-by-build changes are in `dayz-1-30-build-history.md` and the corrected beliefs in `retracted-claims-ledger.md` (same folder).

Each vanilla line below was opened on `P:\` for this file. A line marked "measured" is an in-game or offline result on the build named and is not yet checked on `P:\`.

## The vanilla script tree is not strict UTF-8

One vanilla script file holds a byte that is not valid UTF-8: a cp1252 trademark sign (0x99) inside a block comment, after the word `MangoBrand` at `P:\scripts\3_game\global\world.c:127`. It is present in 1.30.164200 and 1.30.164289 as well (measured).

- A tool that reads `P:\scripts` with strict UTF-8 decoding stops on that file. Decode with replacement (`errors="replace"` in Python) and keep going.
- The game compiles the file, so an "encoding error" finding on it from a linter is a false positive to allow by name.

## Which macros DayZDiag defines

DayZDiag defines both `DIAG_DEVELOPER` and `ENABLE_LOGGING`, on the server and on the client: the script logs of both list them among the defines of every script module (measured on DayZDiag 1.30.164078). `DEVELOPER` is not defined in DayZDiag.

- Code under `#ifdef DIAG_DEVELOPER` or `#ifdef ENABLE_LOGGING` therefore compiles in a DayZDiag test and is skipped on a retail client or server. A test that passes only on DayZDiag has not tested the retail branch.
- Vanilla sites to read as examples: a `DIAG_DEVELOPER` block at `P:\scripts\4_world\classes\environment\environment.c:1-3` and an `ENABLE_LOGGING` block inside a method at `P:\scripts\4_world\classes\bunkerbroadcasthandler.c:338-340`. Both hold only a comment, and both compile.

## A run of `>` closes nested template arguments

Vanilla closes a nested template with a doubled `>`: the declaration of `surfaceNameToEffectIDMap` at `P:\scripts\3_game\global\ammotypes.c:80` reads `map<string, ref ExplosiveEffectData>> surfaceNameToEffectIDMap;`. A parser or linter for Enforce Script has to accept a run of `>` where one would close the template, and must not read it as a shift operator.

## Casting between unrelated classes stops the module

`X.Cast(y)` where neither `X` nor the declared type of `y` derives from the other is a compile error, not a null result. `IngameHud.Cast(mission)` with `Mission mission` made DayZDiag 1.29 refuse the Mission module with `Types 'IngameHud' and 'Mission' are not related` (measured). Cast from a type that is an ancestor or a descendant of the target: `IngameHud` extends `Hud` (`P:\scripts\5_mission\gui\ingamehud.c:1`), and the mission hands out a `Hud` through `GetHud` (`P:\scripts\3_game\gameplay.c:720`), so `IngameHud.Cast(mission.GetHud())` is the cast that compiles.

The same family on 1.30 (measured on DayZDiag 1.30.164289): passing an `Object` where a `proto` method takes an `EntityAI` fails with `Unsafe down-casting, use 'EntityAI.Cast' for safe down-casting` and `Types 'Object' and 'EntityAI' are unrelated`. Cast first, then pass the result.

## How big the script tree is, by build

Useful for a tool that checks it read the whole tree (all counts measured with the linter `scripts/tools/dayz-script-validator`, which reads the `.c` files under the five module folders):

| Build | Script files read |
|---|---|
| 1.29.0.163451 | 2,806 |
| 1.30.164078 | 3,043 |
| 1.30.164200 | 3,057 (68 changed, 14 added, none removed) |
| 1.30.164289 | 3,057 (27 changed, none added or removed) |

The whole `scripts` tree of 1.30.164289 holds 3,076 files. The extraction on `P:\` that this file was checked on is older than 1.30.164200 (see `dayz-1-30-build-history.md`), so count the files there before comparing with this table.

## A full-tree lint of vanilla takes minutes

The script validator (`scripts/tools/dayz-script-validator`) took 132 to 244 seconds for one full run over the vanilla tree on one PC (measured, 1.30 builds). Plan a vanilla control run as a background step, not as part of every edit.
