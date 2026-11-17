# Test loop and debug tools

The fast script-only test loop with DayZDiag and file patching, when to stop iterating, a stuck-client fix, and the debugging tools the vanilla scripts offer (shapes, `DbgUI`, the diag menu, the profiler, log switches). `dayz-mod-workflow` points here once code exists and has to be tried in game.

In this repo the loop is run by scripts: `/dayz-add-server` once, `/dayz-build-pbo`, `/dayz-launch-test` (a DayZDiag server and a DayZDiag client with the same mods, both with `-filePatching`), `/dayz-logwatch` while you play, `/dayz-stop-test`, and `/dayz-gate` for the scripted gates. The rules behind them are in Tier 2, "Testing". The knowledge pack's notes below add the reasoning, the limits and the tools; they came from a source-verified pass over vanilla 1.24, were checked again on 1.30.164200, and every `P:\` citation here was opened on the current `P:\` data.

## The fast loop (script-only iteration in seconds)

1. **`DayZDiag_x64.exe`** is the development runtime. It sits in the DayZ game install next to the retail exe (`find_dayz_diag()` in `skills/dayz-preflight/preflight.py`; the knowledge pack says it ships with DayZ Tools, which is not where this repo finds it). Reported by the knowledge pack, not checked on `P:\`: it defines `DIAG_DEVELOPER`, runs without BattlEye and does not require mod signatures (`.bisign`).
2. Launch flags the knowledge pack uses by hand: `-filePatching -dologs -noPause -mission=P:\<mission>`, plus `-connect` and `-port` for multiplayer and `-profile` to boot with the script profiler on (the vanilla comment: "To enable profiling on game launch, use parameter `-profile`", `P:\scripts\1_core\proto\enprofiler.c:63`). `/dayz-launch-test` builds the launch lines for you; `--dry-run` prints them.
3. Edit a `.c` file under `P:\<ModName>\scripts\...` (the junction to `workspace/<ModName>/`), then **restart the mission** to load it. There is no hot reload at run time.
4. Config, model and layout changes: the knowledge pack found they were **not** picked up by file patching and needed a full PBO rebuild. Tier 2 says `-filePatching` lets the engine read raw `.cpp` and `.c` from the junction. Neither statement can be checked on `P:\`. So when a `config.cpp`, model or layout change does not show after a restart, rebuild with `/dayz-build-pbo` before debugging anything else.
5. Logs: with `-profiles=` they are where the launch put them, in this repo `.server/<instance>/Profiles/` (server) and `.server/!ClientDiagLogs/` (client). Without `-profiles=` the client writes to `%LOCALAPPDATA%\DayZ\` (`*.RPT`, script logs, and `.mdmp` crash dumps you can open with WinDbg or Visual Studio).

**Which cycle for what.** The file patching loop for script logic (fixes, prints, tuning). The full build and server cycle for `config.cpp`, models, layouts and the final validation gate; batch those changes so one in-game session checks several.

**Hard stop: two cycles without convergence.** Two in-game cycles of the same kind (patch, rebuild, test) with no measurable progress: stop, do not launch a third. Before a third rebuild, do one of: (a) an offline bisection of pipeline against data (`debug-protocol.md`, Layer 7), or (b) a change of strategy (instrument with `Print`, shapes or the diag menu, or ask the user). "One variable per cycle" is the bisection anti-pattern moved into the in-game loop: it feels like progress and costs one rebuild per guess. Measured case on the knowledge pack author's SUB_BRZ project: "four patches without a clean test; should have stopped after two".

**Client stuck loading at about 148 MB: rotate `storage_1`.** The diag client boots, stays on the mod warning screen and does not go on. Its script log stops after `Module: World`, the process still responds, and its memory stays at **about 148 MB** (a client that really loads goes above 2,000 MB). It is not a lost window focus and not a hung process. Fix: rename the mission's `storage_1` folder (never delete it) and launch again; the server writes a clean one. In this repo that folder is `.server/<instance>/mission/storage_1`. Measured on 2026-08-22: after the rename the same server and client pair started fully and the player joined. The cost, said plainly: rotating storage erases the persistent world state, so spawned vehicles are gone and have to be created again.

## Debug tooling

| Tool | Build | Use |
|---|---|---|
| `Shape.Create*` and `Debug.Draw*` | all builds, retail too (reported) | 3D overlay: spheres, lines, boxes, matrices. `ShapeFlags.ONCE` is "rendered just once and then it's automatically destroyed. Do not keep pointer to these!!" (`P:\scripts\1_core\proto\endebug.c:132`). `Debug.DrawBox` and its siblings start at `P:\scripts\3_game\tools\debug.c:362`. |
| `DbgUI` (`Begin`, `Text`, `Check`, `SliderFloat`, `Button`, `PlotLive`, `End`) | all builds (reported); call it every frame from an update | Live tuning panels (`class DbgUI`, `P:\scripts\1_core\proto\dbgui.c:59-91`). |
| The diag menu (WIN+ALT in game) | `DIAG_DEVELOPER` only | Register entries with a `modded class PluginDiagMenu` that overrides `RegisterModdedDiagsIDs()` (ids from `GetModdedDiagID()`) and `RegisterModdedDiags()`; vanilla's worked example is `P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenumodding.c:55-74`. Script has a limit of 512 diag ids (`GetModdedDiagID` warning, `P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenumodding.c:52`). Wrap the mod code in `#ifdef DIAG_DEVELOPER`, or it silently does nothing on retail. |
| `EnProfiler` | diag and developer builds | `SetModule(EnProfilerModule.WORLD)` (`SetModule`, `P:\scripts\1_core\proto\enprofiler.c:333`), then `Enable(true)` (`P:\scripts\1_core\proto\enprofiler.c:103`), then `Dump()` to the RPT (`P:\scripts\1_core\proto\enprofiler.c:484`). `proto` methods are not tracked one by one (`P:\scripts\1_core\proto\enprofiler.c:70`). |
| `LogManager` command-line switches | all | `-doLogs`, `-doActionLog`, `-doSymptomLog`, `-doInvMoveLog`, `-doSyncLog`, `-doWeaponLog`, `-doWeatherLog` and more are read at boot, with no recompile (`LogManager.Init`, `P:\scripts\3_game\tools\debug.c:718-736`). |

## Logging discipline

- `Print` and `PrintFormat` go to the log and are cheap. `PrintToRPT` flushes the file on every call ("performance warning - each write means fflush!", `P:\scripts\1_core\proto\endebug.c:98-99`); keep it for messages that must survive a crash.
- `ErrorEx(string err, ErrorExSeverity severity = ErrorExSeverity.ERROR)` (`P:\scripts\1_core\proto\endebug.c:83`) prefixes the message with `[Class::Method] :: [SEVERITY]`.
- Server admin log: the `serverDZ.cfg` keys `adminLogPlayerHitsOnly`, `adminLogPlacement` and `adminLogBuildActions` (reported; server config is not in the scripts on `P:\`), and from script `g_Game.AdminLog(text)` (`AdminLog`, `P:\scripts\3_game\global\game.c:669`).

## Known limits

- No script hot reload; a mission restart per change.
- The Workbench script editor has **no verified breakpoint or step-debug API**: debugging is prints, shapes, `DbgUI` and the diag menu.
- The physics-view indexes of `GetDiagDrawMode` (`P:\scripts\3_game\global\game.c:789-794`) are engine-side values that script does not expose as an enum; drive them from the native diag menu.

## On Linux

Everything above is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`; this section says only what changes for this skill.

- Build and sign with dayzmake 1.0.0 or newer (bzed's DayZ fork of armake2, `https://github.com/bzed/dayzmake`, pinned to tag `v1.0.0`) instead of AddonBuilder, and publish with the `workshop` uploader. Upstream armake2 targets Arma: its V3 file hash leaves `*.c` files out (dayzmake v1.0.0 includes them) and it lacks dayzmake's DayZ-only functions.
- Linux host support in the dayz-mcp server was merged into its `main` branch on 2026-11-14 (`https://github.com/willy92wins/dayz-mcp/pull/411`, the successor of the closed pull request 353). The managed-cycle observations here were measured on its `linux-port` branch before that merge and were not measured again on `main`; they do not verify managed binarization with assets. Test loop: `dayz_test_run` on dayz-mcp `main` (`skills/dayz-test-ingame/references/linux.md`), or by hand either pair that can join: a DayZDiag client and `DayZDiag -server` under Proton, or a manually configured retail Proton client and the native `DayZServer` (a diag client on the native server is refused with `0x00020017`). The native server hangs before the landscape with `-filePatching` (measured 2026-11-04), so start it without the flag and repack; the file patching loop above with loose files under Proton was **not verified**.
- `%LOCALAPPDATA%` and `.ps1` steps: see the Linux guide's pitfalls; translate scripts to `sh`.
- Testing without dayz-mcp: the native `DayZServer` and the retail client under Proton (`dayz-test-ingame`, `references/linux-native-server.md` and `references/linux-headless-client.md`). The 1.30 facts measured on that server are in `dayz-1-30-server-measured.md`.
