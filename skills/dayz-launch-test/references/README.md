# Testing a mod in the running game

What is known about closing the test loop of a DayZ mod: build the PBO, deploy it where the engine reads mods, start a server and a client, and read what happened. `launch.py` runs none of this; open the file that answers the question.

Most files here are measured results from real test sessions with third-party mods and tools (Community Framework, Dabs Framework, VPPAdminTools, the dayz-mcp server); those are not yet checked on `P:\` and each file says so. Vanilla facts cite the vanilla file.

## Which skill does the job

| Job | Use |
|---|---|
| Check the environment (`P:\`, DayZ Tools, DayZ Diag, DayZ Server) | `/dayz-preflight` |
| Find load-stopping errors before a boot | `/dayz-lint <ModName>` |
| Pack and deploy the PBO | `/dayz-build-pbo <ModName>` |
| Create a local test server instance | `/dayz-add-server` |
| Start the diag server and client with the mod | `/dayz-launch-test` |
| Stop them | `/dayz-stop-test` |
| Read and triage the logs | `/dayz-logwatch` |
| PASS or FAIL: builds, boots clean, behaves, looks right | `/dayz-gate build`, `ingame`, `behavior`, `visual` |
| Drive the running game through dayz-mcp verbs (spawn, capture, raycast, drive) | `mcp/README.md` |
| A server-only boot on Linux, a headless client, a self-reporting test mod, a scripted test cell | the files below and `../assets/autotest-mod/` |

## Rules that hold on every route

- **Mod paths are absolute** on Windows. A relative `-mod=` entry is not mounted and nothing says so (`windows-launch-cycle.md`). The native Linux server is the reverse (`linux-native-server.md`, section 3).
- **An observation is worth what the `-mod=` line of its own run is worth.** Before reading any verdict, read `-mod=` and `-mission=` in that run's RPT (`automated-cells.md`).
- **Do not promise hot-reload.** `-filePatching` is meant to reload scripts and configs from source, never models, textures or materials; on the measured install even scripts came from the PBO. Rebuild the PBO for a script change unless a source-only log-string probe shows your install serves the source (`windows-launch-cycle.md`).
- **A gate that cannot go red proves nothing.** Show the failing case once before trusting a green run (`automated-cells.md`).
- **Mission storage belongs to the mod set that wrote it.** Booting storage written without Community Framework on a mod set that has it crashed the server; the reverse floods the log with `Scripted variables corrupted` and can rewrite the storage so that the next server with Community Framework crashes; and persisted entities come back as the last run left them (`build-and-storage-traps.md`). Renaming `storage_1` resets the world and characters, so ask the user first.
- **The test machine is one shared resource**: one game port, one Steam client. Whoever opens a process closes it (`managed-launcher.md`, `session-findings.md`).

## Files

| Question | Read |
|---|---|
| What is the build, deploy and launch cycle, its modes and prerequisites? What does `-filePatching` reload? Why must mod paths be absolute? Which mods and admin tools load by default? | `windows-launch-cycle.md` |
| The server or client does not start, connect or load the mod: what does this symptom mean? Where is each log? Steam, a missing `P:\` after a reboot, quoting, a client that dies before it logs, retail executables with third-party mod sets | `troubleshooting.md` |
| The run went green without testing my change: stale or locked PBO, backups packed in, a signature on the old PBO, storage from another mod set, the `modstorage` warning | `build-and-storage-traps.md` |
| How do I write a scripted test that boots the game and reads a verdict from the logs? What may a mission `init.c` do? Why will the vehicle not drive in the test? What makes a run valid evidence? | `automated-cells.md` |
| How do dayz-mcp's `dayz_test_run` and `dayz_test_stop`, its launcher allow-list, leases and request grammar behave, and what are their traps? | `managed-launcher.md` |
| What ships with the dedicated server, and which script reads `serverDZ.cfg`, `cfggameplay.json`, `cfgeffectarea.json` and `messages.xml`? Which logs land in the profile folder? | `server-and-mission-config.md` |
| What changed in 1.30: unpacked `-mod` folders, new launch flags, headless clients, server load figures, pending actions in single player? | `dayz-1-30.md` |
| What changes on a Linux host? | `linux.md` |
| How do I prove the server half of a mod on the native Linux `DayZServer`, with no client and no dayz-mcp? | `linux-native-server.md` |
| How do I test the client side on Linux with a headless client under Proton, and have a test mod report its own results? | `linux-headless-client.md` |
| Has this symptom been seen before in a real session (third-party dependencies, retail capture, launching from an agent, untextured runs)? | `session-findings.md` |
| How do I verify a mod in game through dayz-mcp (spawn, capture, collision, vehicle ladder, report)? | `mcp/README.md`, which indexes the files in `mcp/` |
| Which skill runs each step from scope to Workshop, which pack do I read for a request, and how do I port a mod to 1.30? | `mod-loop.md` |
| How do I run the fast DayZDiag script loop, when do I stop iterating, and which debug tools does vanilla offer? | `test-loop.md` |
| The feature does not work and the log is clean: in what order do I look, how do I place probes, how do I bisect? | `debug-protocol.md` |
| Which mistakes keep coming back (E01 to E35), and what is the correct form of each? | `error-catalog.md` |
| How do I read numbers from a test session without fooling myself (clock offsets, ranges, defect rates)? | `measurement-discipline.md` |
| How do I label the severity of an audit finding or of something missing, and keep parallel auditors independent? | `audit-escalation.md` |
| What was measured on a running 1.30 server (version define, `FindFile`, `files[]` slashes, compile crashes, load order, CF and Expansion)? | `dayz-1-30-server-measured.md` |

## Scripts and assets

| Path | What it is |
|---|---|
| `../scripts/dayz-test.ps1` | A PowerShell orchestrator for one mod (build, deploy, launch modes `offline`, `server`, `client`, `all`, stop). It is the launcher dayz-mcp's `dayz_test_run` starts: it runs only inside a session that dayz-mcp's managed launcher started, and stops with "Managed lifecycle environment is incomplete" otherwise. Copy `../scripts/` into the mod's `<Mod>_dev\tools\` folder and register that copy with dayz-mcp (`managed-launcher.md`). It does not go through `/dayz-preflight` (it carries its own `Invoke-Preflight` check), so run `/dayz-preflight` first. Without dayz-mcp, use `/dayz-launch-test`. |
| `skills/dayz-launch-test/scripts/server.bat`, `client.bat`, `offline.bat` in the same folder | Wrappers around that orchestrator, one per launch mode; replace `__MODNAME__` with the mod's `CfgPatches` name. |
| `skills/dayz-launch-test/scripts/drive_ladder.py` | Runs the vehicle acceptance ladder against a running dayz-mcp daemon (`mcp/acceptance-ladder.md`). Its offline fixtures are `test_drive_ladder.py` beside it. |
| `../assets/autotest-mod/` | AutoTest, a small mod whose test cases run on server and client and print their results to the logs, so a run reports on itself. Source under `src/AutoTest/`. How to build, load and read it: `linux-headless-client.md`, section 3. Keep it out of a release. |
