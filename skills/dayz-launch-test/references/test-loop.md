# Test loop and debug tools

How to iterate on scripts quickly with DayZDiag, when to stop iterating, how to free a client stuck loading, and which debug tools the vanilla scripts offer (shapes, `DbgUI`, the diag menu, the profiler, log switches). Read it once code exists and has to be tried in game.

In this repo scripts run the loop: `/dayz-add-server` once, `/dayz-build-pbo`, `/dayz-launch-test` (a DayZDiag server and a DayZDiag client with the same mods, both with `-filePatching`), `/dayz-logwatch` while you play, `/dayz-stop-test`, and `/dayz-gate` for the scripted checks. The rules behind them are in Tier 2, "Testing"; this file adds the reasons, the limits and the tools.

## The quick loop for scripts

1. `DayZDiag_x64.exe` is the development runtime. It sits in the DayZ game install next to the retail exe (`find_dayz_diag()` in `skills/dayz-preflight/preflight.py`), not in DayZ Tools. Not checked on `P:\`: it defines `DIAG_DEVELOPER`, runs without BattlEye and does not require mod signatures (`.bisign`).
2. Flags when you start it by hand: `-filePatching -dologs -noPause -mission=P:\<mission>`, plus `-connect` and `-port` for multiplayer and `-profile` to boot with the script profiler on. The vanilla comment says: "To enable profiling on game launch, use parameter `-profile`" (`P:\scripts\1_core\proto\enprofiler.c:63`). `/dayz-launch-test` builds the launch lines for you, and `--dry-run` prints them.
3. Edit a `.c` file under `P:\<ModName>\scripts\...` (the junction to `workspace/<ModName>/`), then restart the mission to load it; there is no hot reload while it runs. `-filePatching` is meant to serve the edited script from the junction, but on the measured install the scripts came from the PBO even with the flag (`skills/dayz-launch-test/SKILL.md`), and with an empty PBO the modules compiled without the mod's files and without an error (`diag-flow-traps.md`). So when a script change does not show after a mission restart, rebuild with `/dayz-build-pbo` and compare the `Module: X; loaded Nx files` counts in the script log with a run known to load the mod.
4. Config, model and layout changes were not picked up by file patching in measured sessions and needed a full PBO rebuild, although Tier 2 says `-filePatching` lets the engine read raw `.cpp` and `.c` from the junction. Neither statement can be checked on `P:\`. When a `config.cpp`, model or layout change does not show after a restart, rebuild with `/dayz-build-pbo` before you debug anything else.
5. Logs: with `-profiles=` they go where the launch put them, in this repo `.server/<instance>/Profiles/` (server) and `.server/!ClientDiagLogs/` (client). Without `-profiles=` the client writes to `%LOCALAPPDATA%\DayZ\`: `*.RPT`, script logs, and `.mdmp` crash dumps you can open in WinDbg or Visual Studio.

Use the mission restart loop for script logic (fixes, prints, tuning), with a `/dayz-build-pbo` rebuild whenever the script log shows the mod's files did not load from the work drive. Use the full build and server cycle for `config.cpp`, models, layouts and the final check, and batch those changes so one session in game checks several.

## Stop after two cycles with no progress

Two cycles of the same kind (patch, rebuild, test) with no measurable progress: stop, and do not launch a third. Before a third rebuild, either bisect pipeline against data offline (`debug-protocol.md`, "Component bisection"), or change approach: add `Print` lines, shapes or diag menu entries, or ask the user. Changing one guess per cycle feels like progress and costs a rebuild per guess.

## A client stuck loading at about 148 MB

The diag client boots, stays on the mod warning screen and goes no further. Its script log stops after `Module: World`, the process still responds, and its memory stays at about 148 MB, where a client that really loads climbs past 2,000 MB. It is not lost window focus and not a hung process.

Rename the mission's `storage_1` folder (never delete it) and launch again; the server writes a clean one, and the same server and client then start fully and the player joins. In this repo the folder is `.server/<instance>/mission/storage_1`. Renaming it wipes the saved world, so spawned vehicles are gone and have to be created again.

## Debug tools

| Tool | Build | Use |
|---|---|---|
| `Shape.Create*` and `Debug.Draw*` | All builds, retail too (reported) | 3D overlay: spheres, lines, boxes, matrices. `ShapeFlags.ONCE` is "rendered just once and then it's automatically destroyed. Do not keep pointer to these!!" (`P:\scripts\1_core\proto\endebug.c:132`). `Debug.DrawBox` and its siblings start at `P:\scripts\3_game\tools\debug.c:362`. |
| `DbgUI` (`Begin`, `Text`, `Check`, `SliderFloat`, `Button`, `PlotLive`, `End`) | All builds (reported); call it every frame from an update | Live tuning panels (`class DbgUI`, `P:\scripts\1_core\proto\dbgui.c:59` to `:91`). |
| The diag menu (Win+Alt in game) | `DIAG_DEVELOPER` only | Register entries with a `modded class PluginDiagMenu` that overrides `RegisterModdedDiagsIDs()` (ids from `GetModdedDiagID()`) and `RegisterModdedDiags()`; vanilla's worked example is `P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenumodding.c:55` to `:74`. Script has a limit of 512 diag ids (the `GetModdedDiagID` warning, `plugindiagmenumodding.c:52`). Wrap the mod code in `#ifdef DIAG_DEVELOPER`, or it silently does nothing on retail. |
| `EnProfiler` | Diag and developer builds | `SetModule(EnProfilerModule.WORLD)` (`P:\scripts\1_core\proto\enprofiler.c:333`), then `Enable(true)` (`:103`), then `Dump()` to the RPT (`:484`). `proto` methods are not tracked one by one (`:70`). |
| `LogManager` command line switches | All | `-doLogs`, `-doActionLog`, `-doSymptomLog`, `-doInvMoveLog`, `-doSyncLog`, `-doWeaponLog`, `-doWeatherLog` and more are read at boot, with no recompile (`LogManager.Init`, `P:\scripts\3_game\tools\debug.c:718` to `:736`). |

## Logging

- `Print` and `PrintFormat` go to the log and are cheap. `PrintToRPT` flushes the file on every call ("performance warning - each write means fflush!", `P:\scripts\1_core\proto\endebug.c:98` and `:99`); keep it for messages that must survive a crash.
- `ErrorEx(string err, ErrorExSeverity severity = ErrorExSeverity.ERROR)` (`endebug.c:83`) prefixes the message with `[Class::Method] :: [SEVERITY]`. The vanilla comment adds that a severity above `INFO` "will show a messagebox" (`:69`); use `INFO` for plain trace lines.
- The server admin log takes the `serverDZ.cfg` keys `adminLogPlayerHitsOnly`, `adminLogPlacement`, `adminLogBuildActions` and `adminLogPlayerList`, which script reads with `ServerConfigGetInt` (`P:\scripts\4_world\plugins\pluginbase\pluginadminlog.c:44` to `:47`), and from script `g_Game.AdminLog(text)` (`AdminLog`, `P:\scripts\3_game\global\game.c:669`).

## The vanilla script test framework

Vanilla ships a unit test framework and a client launch mode that runs it, separate from this repo's AutoTest mod (`../assets/autotest-mod/`).

- Tests are written with attributes (`P:\scripts\2_gamelib\tests\testingframework.c`): `[Test("MySuite")]` on a `TestBase` subclass or on a free function returning `TestResultBase`, with optional `timeoutS`, `timeoutMs` and `sortOrder` (`:96` to `:111`); `[Step(EStage.Setup)]`, `[Step(EStage.Main)]` and `[Step(EStage.TearDown)]` on its methods (`:116` to `:133`); a result through `SetResult`. A commented example suite is in `P:\scripts\3_game\autotest\autotestrunner.c:106` to `:216`; its comment warns that an empty suite gives no error and runs nothing.
- `-autotest=<config.json>` on the client command line takes priority over `-mission` in `DayZGame`'s launch switch (`P:\scripts\3_game\dayzgame.c:2135` to `:2137`). The JSON has one key, `TestSuites`, the list of suite names to run (`P:\scripts\3_game\autotest\autotestconfigjson.c:3`). `-mission` is still required: without it the game quits; a config that fails to load only logs and loads the mission without tests (`dayzgame.c:2364` to `:2380`).
- `MissionGameplay.OnUpdate` starts `AutotestRunner`, runs it every frame and calls `RequestExit(0)` when it is done (`P:\scripts\5_mission\mission\missiongameplay.c:232` to `:243`). The runner enables only the named suites, then writes the `TestHarness` report, JUnit style XML, to `$mission:Autotest_<UTC time>.xml` (`autotestrunner.c:19` to `:74`; `P:\scripts\3_game\autotest\autotestfixture.c:3`). Its own messages go to the RPT prefixed `[Autotest]` (`autotestfixture.c:52`).

It runs in `MissionGameplay`, so on a client or an offline mission, never in `MissionServer`. Whether the retail executables accept `-autotest` is not checked in game.

## Limits

- No script hot reload; one mission restart per change.
- The Workbench script editor has no checked breakpoint or step debugging API, so debugging is prints, shapes, `DbgUI` and the diag menu.
- The physics view indexes of `GetDiagDrawMode` (`P:\scripts\3_game\global\game.c:789` to `:794`) are engine values that script does not expose as an enum; drive them from the native diag menu.

## On Linux

Everything above is the Windows workflow and stays valid there. The Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`; this section says only what changes for this skill.

- Build and sign with dayzmake 1.0.0 or newer (a DayZ fork of armake2, tag `v1.0.0`) instead of AddonBuilder, and publish with the `workshop` uploader. armake2 itself targets Arma: its V3 file hash leaves `*.c` files out, which dayzmake includes, and it lacks dayzmake's DayZ-only functions.
- Linux host support is on the dayz-mcp server's `main` branch. The managed cycle notes here were measured on its earlier Linux branch and not measured again on `main`, and they do not cover managed binarization with assets. Test with `dayz_test_run` on dayz-mcp `main` (`linux.md`), or by hand with either pair that can join: a DayZDiag client with `DayZDiag -server` under Proton, or a hand-configured retail Proton client with the native `DayZServer`. A diag client on the native server is refused with `0x00020017`.
- The native server hangs before the landscape with `-filePatching`, so start it without the flag and repack. The loose-file loop above under Proton is not checked.
- For `%LOCALAPPDATA%` and `.ps1` steps, see the Linux guide's pitfalls and translate scripts to `sh`.
- Testing without dayz-mcp: the native `DayZServer` and the retail client under Proton (`linux-native-server.md` and `linux-headless-client.md`). The 1.30 facts measured on that server are in `dayz-1-30-server-measured.md`.
