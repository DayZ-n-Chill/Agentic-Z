# Testing a mod in the running game

Reference for closing the test loop of a DayZ mod: build the PBO, deploy it where the engine reads mods, start a server and a client, and read what happened. `launch.py` runs none of this; open the one file that answers the question.

Most files here are results measured in test sessions with third-party mods and tools (Community Framework, Dabs Framework, VPPAdminTools, the dayz-mcp server); each file says what is not checked on `P:\`. Vanilla facts cite the vanilla file. Line numbers match the vanilla data at the time of writing; if a line has moved, Grep the class or key name in the same file.

## Which skill does the job

| Job | Use |
|---|---|
| Check the environment (`P:\`, DayZ Tools, DayZ Diag, DayZ Server) | `/dayz-preflight` |
| Find errors that stop loading, before a boot | `/dayz-lint <ModName>` |
| Pack and deploy the PBO | `/dayz-build-pbo <ModName>` |
| Create a local test server instance | `/dayz-add-server` |
| Start the diag server and client with the mod | `/dayz-launch-test` |
| Stop them | `/dayz-stop-test` |
| Read and triage the logs | `/dayz-logwatch` |
| PASS or FAIL: builds, boots clean, behaves, looks right | `/dayz-gate build`, `ingame`, `behavior`, `visual` |
| Drive the running game through dayz-mcp verbs (spawn, capture, raycast, drive) | `mcp/README.md` |
| A server only boot on Linux, a headless client, a self-reporting test mod, a scripted test | the files below and `../assets/autotest-mod/` |

## Rules that hold on every route

- **Mod paths are absolute on Windows.** A relative `-mod=` entry is not mounted and nothing says so (`windows-build-and-mount.md`). The native Linux server is the reverse (`linux-native-server.md`, "Run it headless").
- **An observation is worth the `-mod=` line of its run.** Before reading any verdict, read `-mod=` and `-mission=` in that run's RPT (`test-cell-evidence.md`).
- **Do not promise hot reload.** `-filePatching` is meant to reload scripts and configs from source, never models, textures or materials, and on the measured install even scripts came from the PBO. Rebuild the PBO for a script change unless a source only log string probe shows your install serves the source (`windows-build-and-mount.md`).
- **A gate that cannot go red proves nothing.** Watch it fail once before trusting a green run (`test-cell-evidence.md`).
- **Mission storage belongs to the mod set that wrote it.** Booting storage written without Community Framework on a mod set that has it crashed the server; the reverse floods the log with `Scripted variables corrupted` and can rewrite the storage so the next server with Community Framework crashes; and saved entities come back as the last run left them (`build-and-storage-traps.md`). Renaming `storage_1` resets the world and characters, so ask the user first.
- **The test machine is one shared resource:** one game port, one Steam client. Whoever opens a process closes it (`managed-launcher.md`, `test-machine-sharing.md`).

## Which file to open

| Question | File |
|---|---|
| What is the Windows launch cycle, its modes and prerequisites? Which mods and admin tools load by default? | `windows-launch-cycle.md` |
| Why did the build drop my scripts, what does `-filePatching` really serve, and why must mod paths be absolute? | `windows-build-and-mount.md` |
| The server or client does not connect or load the mod: what does this symptom mean? Where is each log? Retail executables with third-party mod sets | `troubleshooting.md` |
| The client or build dies before it logs: a missing `P:\` after a reboot, a stale Steam key, the wrong Steam account, quoting | `client-startup-failures.md` |
| Diag traps: `Print` in the script log, file patching that loads nothing, dependency addons, scripts only retail accepts, the 1.30 launch flags | `diag-flow-traps.md` |
| Several sessions share one machine: who holds it, launching DayZDiag from an agent's shell | `test-machine-sharing.md` |
| How do I check a new mod mounts, and what changes when I copy test helpers to another mod? | `mount-probe-and-test-helpers.md` |
| Why does a window grab mislead (retail brightness, hidden window, runs that never load textures)? | `window-capture-pitfalls.md` |
| Where is the vehicle first person eye, and why must I log it every run? | `vehicle-first-person-eye.md` |
| The run went green without testing my change: stale or locked PBO, backups packed in, a signature on the old PBO, storage from another mod set | `build-and-storage-traps.md` |
| How do I set up a scripted test that boots the game and reads a verdict from the logs? What may a mission `init.c` do? Which diag defines exist? How does vanilla's own `-autotest` harness run test suites? | `automated-cells.md` |
| How does a scripted test seat a player in a vehicle, and why will the test vehicle not drive? | `test-cell-vehicles.md` |
| Can this gate fail at all? What order does teardown take? When does a run count as evidence, and does the `-mod=` line or window focus spoil it? | `test-cell-evidence.md` |
| How do dayz-mcp's `dayz_test_run` and `dayz_test_stop`, its launcher allow-list, leases and request rules behave, and what are their traps? | `managed-launcher.md` |
| What ships with the dedicated server, and which script reads `serverDZ.cfg`, `cfggameplay.json`, `cfgeffectarea.json` and `messages.xml`? Which logs land in the profile folder? | `server-and-mission-config.md` |
| What changed in 1.30 for launching: unpacked `-mod` folders, new launch flags, headless clients, pending actions in single player, Script Console tabs? | `dayz-1-30.md` |
| What goes wrong when I start the 1.30 DayZDiag by hand (defines, a stale Steam inside a desktop app, profiles path, crash dump environment)? | `diag-direct-launch.md` |
| How do I load a server with moving dummy players and measure the load honestly? | `server-load-and-dummy-bots.md` |
| What was measured on a running 1.30 server (version define, `FindFile`, `files[]` slashes, compile crashes, load order, Community Framework and Expansion)? | `dayz-1-30-server-measured.md` |
| What changes on a Linux host? | `linux.md` |
| How do I prove the server half of a mod on the native Linux `DayZServer`, with no client and no dayz-mcp? | `linux-native-server.md` |
| How do I test the client side on Linux with a headless client under Proton, and have a test mod report its own results? | `linux-headless-client.md` |
| How do I verify a mod in game through dayz-mcp (spawn, capture, collision, vehicle acceptance steps, report)? | `mcp/README.md`, which indexes the files in `mcp/` |
| Which skill runs each step from scope to Workshop, which pack do I read for a request, and how do I port a mod to 1.30? | `mod-loop.md` |
| How do I run the fast DayZDiag script loop, when do I stop iterating, and which debug tools does vanilla offer? | `test-loop.md` |
| The feature does not work and the log is clean: in what order do I look, how do I place probes, how do I bisect? Is it a crash, a VM exception or corruption, and which missing engine minimum crashes? | `debug-protocol.md` |
| Which mistakes keep coming back (E01 to E35), and what is the correct form of each? | `error-catalog.md` |
| How do I read numbers from a test session without fooling myself (clock offsets, ranges, defect rates)? | `measurement-discipline.md` |

## Scripts and assets

| Path | What it is |
|---|---|
| `../scripts/dayz-test.ps1` | A PowerShell orchestrator for one mod (build, deploy, launch modes `offline`, `server`, `client` and `all`, stop). It is the launcher dayz-mcp's `dayz_test_run` starts: it runs only inside a session that dayz-mcp's managed launcher started, and stops with "Managed lifecycle environment is incomplete" otherwise. Copy it, with the three `.bat` templates below, into the mod's `<Mod>_dev\tools\` folder and register that copy with dayz-mcp (`managed-launcher.md`). It does not go through `/dayz-preflight` (it has its own `Invoke-Preflight` check), so run `/dayz-preflight` first. Without dayz-mcp, use `/dayz-launch-test`. |
| `../assets/launcher/server.bat`, `client.bat`, `offline.bat` | Templates for the wrappers around that orchestrator, one per launch mode. Copy them beside the mod's copy of `dayz-test.ps1` and replace `__MODNAME__` with the mod's `CfgPatches` name. |
| `skills/dayz-launch-test/scripts/run_vehicle_checks.py` | Walks the vehicle acceptance steps against a running dayz-mcp daemon (`mcp/vehicle-acceptance.md`). Its offline fixtures are `test_run_vehicle_checks.py` beside it. |
| `../assets/autotest-mod/` | AutoTest, a small mod whose test cases run on server and client and print their results to the logs, so a run reports on itself. Source under `src/AutoTest/`. How to build, load and read it: `linux-headless-client.md`, "Tests that run on both sides and report back". Keep it out of a release. |
