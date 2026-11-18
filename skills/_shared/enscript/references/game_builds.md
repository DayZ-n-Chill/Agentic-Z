# Game builds and line numbers

Which DayZ build the `P:\` extraction is, which build a cited line belongs to, and the porting rules the 1.30 patches set. What each build changed lives in the topic packs, for example `_shared/vehicles/dayz-1-30-vehicles.md`, `_shared/animation/dayz-1-30-changes.md`, `_shared/weapons/dayz-1-30-migration.md`, `_shared/ui/ui-changes-1-30.md` and `_shared/world/heat-stroke.md`; this file doesn't repeat them.

## Which build `P:\` is

The extraction on `P:\` is a 1.30 build older than the first 1.30 patch. It still declares `vector Cross(vector v)` (`P:\scripts\1_core\proto\enconvert.c:239`), which the first patch removed, and it holds the Workbench API as one file, `P:\scripts\1_core\workbenchapi.c`, where the first patch has a `1_core\workbenchapi\` folder (`workbench_api.md`).

So a fact that a pack marks as changed in the first or second 1.30 patch shows its old form on `P:\`. Check those facts again once `P:\` is extracted from a newer build.

## The builds

The packs name a build by these words. The build string is what `GetVersion` returns and what the script log prints, so it tells you which one a server runs.

| Name in the packs | Build string | What it is |
|---|---|---|
| 1.29 | 1.29.0.163451 | The 1.29 stable script tree. A citation labelled `1.29` gives its lines |
| 1.30 Experimental | 1.30.164014 | The 1.30 pre-release on the Experimental branch |
| the 1.30 release | 1.30.164078 | The first 1.30 stable build |
| the first 1.30 patch | 1.30.164200 | Stable patch: changes 68 script files and adds 14 (13 of them under `1_core\workbenchapi\`); removes none |
| the second 1.30 patch | 1.30.164289 | Stable patch: changes 27 of the 3,076 script files, all `.c`; `scripts\config.cpp` is unchanged. None of the 42,357 extracted data entries (configs, layouts, XML, `.agf`, `.rvmat`) differ from the first patch. Models, navmeshes and the Chernarus `.wrp` changed size and were not compared |

A tool that reads the whole script tree should find these `.c` files under the five module folders: 2,806 on 1.29, 3,043 on the 1.30 release, and 3,057 on both 1.30 patches. Count the files on `P:\` before you compare.

DayZ Tools from 1.30 on writes binarized models as ODOL v56, like the 1.30 vanilla models, and maps as OPRW v32. Older tools wrote ODOL v55. A v56 file has 4 more zero bytes in the model info, so a v55 reader fails on it. The readers are covered in `_shared/vehicles/dayz-1-30-vehicles.md` and `_shared/world/wrp-format-and-road-graph.md`.

## Which line a citation gives

A vanilla line number is right for one build. Pack files cite the lines of the build they were checked on, up to the second 1.30 patch. A citation labelled `1.29` gives the 1.29 line. A result measured in game names the build only when the result changed between builds.

When a cited line doesn't match on `P:\`, Grep for the symbol by name before deciding the fact is wrong. The files the second patch changed include base building, the code lock, the diag menu, heat stroke, `game.c`, `playerconstants.c` and `miscgameplayfunctions.c`.

## Porting rules from the 1.30 patches

- Resolve every `override` against the target build's class chain before porting. A deleted method (`CarScript.ToggleHeadlights`) or a changed signature (`ActionTargetsCursor.Update(bool fullUpdate = true)`, `P:\scripts\5_mission\gui\actiontargetscursor.c:310`) stops the whole script module, and a lint against the old tree still passes.
- Never save or send an enum as a raw number across builds, because two vanilla enums were renumbered inside the 1.30 patches. `NVTypes` gained two values in the middle in the first patch (the older list, with `NV_OPTICS_UNDERGROUND`, is at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:69`), and `CollisionFlags` gained `NONE = 0` in the second patch (the older enum is at `P:\scripts\1_core\proto\endebug.c:140`). Use the names.
- A minor stable patch can remove script API. `vector.Cross` existed in two 1.30 builds and then went away; a call stops the server with `Undefined function 'vector.Cross'`. Check the build the server runs, not the one the code was written on.
- When a lookup disagrees with the server, compare the vanilla tree with the game's own `dta\scripts.pbo`. An extraction left over from an earlier build answers for that build.
- A result from DayZDiag 1.29 or 1.30 Experimental is a lead on 1.30 stable until it is measured there. Say which of the two it came from.
