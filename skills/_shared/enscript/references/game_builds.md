# Reference: game builds and which line a citation gives

Which DayZ build a vanilla line number or a measurement belongs to, which build the `P:\` extraction is, and the rules that the 1.30 patch line taught. The changes each build made live in the topic packs (for example `_shared/vehicles/dayz-1-30-vehicles.md`, `_shared/animation/dayz-1-30-changes.md`, `_shared/weapons/dayz-1-30-migration.md`, `_shared/ui/ui-changes-1-30.md`, `_shared/world/heat-stroke.md`); this file does not repeat them.

## Which build `P:\` is

The extraction on `P:\` is a 1.30 build older than 1.30.164200: it still declares `vector Cross(vector v)` (`P:\scripts\1_core\proto\enconvert.c:239`), which 1.30.164200 removed, and it has the Workbench API as one file, `P:\scripts\1_core\workbenchapi.c`, where 1.30.164200 has a `1_core\workbenchapi\` folder (`workbench_api.md`). A fact a pack marks as changed in 1.30.164200 or 1.30.164289 therefore shows its old form on `P:\`. Re-check those facts after `P:\` is extracted from a newer build.

## Timeline

| Build | What it is |
|---|---|
| 1.29.0.163451 | The 1.29 stable script tree. A citation labelled `1.29` gives its lines. |
| 1.29.163709 | The DayZDiag build of the 1.29 in-game measurements (collision boxes, winding). |
| 1.30.164014 | 1.30 Experimental. Measurements labelled "1.30 Exp" were made here. |
| 1.30.164078 | 1.30 stable, 2026-10-15. |
| 1.30.164200 | Stable patch: changes 68 script files and adds 14 (13 under `1_core\workbenchapi\`); removes none. |
| 1.30.164289 | Stable patch of 2026-11-04: changes 27 of the 3,076 script files, all `.c`; `scripts\config.cpp` unchanged. None of the 42,357 extracted data entries (configs, layouts, XML, `.agf`, `.rvmat`) changed from 1.30.164200; models, navmeshes and the Chernarus `.wrp` changed size and were not compared. |

Script files a full-tree tool should find (the `.c` files under the five module folders): 2,806 on 1.29.0.163451, 3,043 on 1.30.164078, 3,057 on 1.30.164200 and 1.30.164289. Count the files on `P:\` before comparing.

DayZ Tools: since the update of 2026-10-15 (`binarize.exe` 1.30.164.078) a binarized model is ODOL v56, like the 1.30 vanilla models, and a map is OPRW v32 (the readers: `_shared/vehicles/dayz-1-30-vehicles.md` and `_shared/world/wrp-format-and-road-graph.md`). Before that update the tools wrote ODOL v55; a v56 file has 4 more zero bytes in the model info, so a v55 reader fails on it.

## Which line a citation gives

A vanilla line number is right for one build. Pack files cite the lines of the build they were checked on, up to 1.30.164289; a citation labelled `1.29` gives the 1.29 line; a measurement keeps the build it was made on. When a cited line does not match on `P:\`, find the symbol by name before deciding the fact is wrong. The files 1.30.164289 changed include base building, the code lock, the diag menu, heat stroke, `game.c`, `playerconstants.c` and `miscgameplayfunctions.c`.

## Rules the 1.30 patch line taught

- **Resolve every `override` against the target build's class chain before porting.** A deleted method (`CarScript.ToggleHeadlights`) or a changed signature (`ActionTargetsCursor.Update(bool fullUpdate = true)`, `P:\scripts\5_mission\gui\actiontargetscursor.c:310`) stops the whole script module, and a lint against the old tree passes.
- **Never save or send an enum as a raw number across builds.** Two vanilla enums were renumbered inside the 1.30 patch line: `NVTypes` gained two values in the middle in 1.30.164200 (older list: `NV_OPTICS_UNDERGROUND` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:69`), and `CollisionFlags` gained `NONE = 0` in 1.30.164289 (older enum: `P:\scripts\1_core\proto\endebug.c:140`). Use the names.
- **A minor stable patch can remove script API.** `vector.Cross` existed in two 1.30 builds and then went away; a call stops the server with `Undefined function 'vector.Cross'`. Check the build the server runs, not the one the code was written on.
- **Compare the vanilla tree with the game's own `dta\scripts.pbo` when a lookup disagrees with the server.** An extraction left over from an earlier build answers for that build.
- **State the build with every measurement.** A result from DayZDiag 1.29 or 1.30 Experimental is a lead on 1.30 stable until it is measured there.
