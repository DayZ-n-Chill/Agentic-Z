---
name: dayz-test-ingame
description: "Reference for testing a DayZ mod in the running game: the build, deploy and launch cycle with -filePatching on DayZDiag, what hot-reloads and what does not, absolute -mod paths, serverDZ.cfg and mission config, local dedicated server with or without mods, managed dayz-mcp runs, scripted test cells and the self-reporting AutoTest mod, the native Linux server and a headless client under Proton, and the traps that make a test run meaningless. Use when the mod doesn't load, the server or client won't start or connect to 127.0.0.1, a script change is not picked up, a test passes without testing the change, or you need a headless or Linux test. To just launch, stop or gate on Windows use /dayz-launch-test, /dayz-stop-test and /dayz-gate. Spanish triggers: \"lanzar el juego con el mod\", \"probar el mod in-game\", \"arrancar server local\"."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-test-ingame

What is known about closing the test loop of a DayZ mod: build the PBO, deploy it where the engine reads mods, start a server and a client, and read what happened. This skill is reference only. It ships no Python script, so there is no preflight gate here; the skills that do the work gate on `/dayz-preflight` themselves.

Follow `skills/_shared/dayz-conventions.md`. Most of `references/` is measured results from real test sessions with third-party mods and tools (Community Framework, Dabs Framework, VPPAdminTools, the dayz-mcp server); those are not yet checked on `P:\` and each file says so. Vanilla facts cite the vanilla file.

## Which skill does the job

On Windows the jobs of the test loop are scripts in this repo. Use them; read this skill for the why and for what they do not cover.

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
| Drive the running game through MCP verbs (spawn, capture, raycast, drive) | the `dayz-mcp-verify` skill |
| A server-only boot on Linux, a headless client, a self-reporting test mod, a scripted test cell | this skill's references and assets |

The whole loop can also run from one PowerShell orchestrator, `dayz-test.ps1`, generated per mod from `templates/`. The templates serve readers who want that route or need to read a finding that names its flags (`-Mode all`, `-Build`, `-PackOnly`, `-ExtraMods`, `-ServerWait`); the references say which repo skill each flag corresponds to.

## Rules that hold on every route

- **Mod paths are absolute.** A relative `-mod=` entry is not mounted and nothing says so (`references/windows-launch-cycle.md`).
- **An observation is worth what the `-mod=` line of its own run is worth.** Before reading any verdict, read `-mod=` and `-mission=` in that run's RPT (`references/automated-cells.md`).
- **Do not promise hot-reload.** `-filePatching` is meant to reload scripts and configs from source, never models, textures or materials; on the measured install even scripts came from the PBO. Rebuild the PBO for a script change unless a source-only log-string probe shows your install serves the source (`references/windows-launch-cycle.md`).
- **A gate that cannot go red proves nothing.** Show the failing case once before trusting a green run (`references/automated-cells.md`).
- **Mission storage belongs to the mod set that wrote it.** Booting storage written without Community Framework on a mod set that has it crashed the server; the reverse floods the log with `Scripted variables corrupted` and can rewrite the storage so that the next server with Community Framework crashes; and persisted entities come back as the last run left them (`references/build-and-storage-traps.md`).
- **The test machine is one shared resource**: one game port, one Steam client. Whoever opens a process closes it (`references/managed-launcher.md`, `references/session-findings.md`).

## What to read

| Question | Read |
|---|---|
| What is the build, deploy and launch cycle, its modes and prerequisites? What does `-filePatching` reload? Why must mod paths be absolute? Which mods and admin tools load by default? | `references/windows-launch-cycle.md` |
| The server or client does not start, connect or load the mod: what does this symptom mean? Where is each log? Steam, a missing `P:\` after a reboot, quoting, a client that dies before it logs, retail executables with third-party mod sets | `references/troubleshooting.md` |
| The run went green without testing my change: stale or locked PBO, backups packed in, a signature on the old PBO, storage from another mod set, the `modstorage` warning | `references/build-and-storage-traps.md` |
| How do I write a scripted test that boots the game and reads a verdict from the logs? What may a mission `init.c` do? Why will the vehicle not drive in the test? What makes a run valid evidence? | `references/automated-cells.md` |
| How do dayz-mcp's `dayz_test_run` and `dayz_test_stop`, its launcher allow-list, leases and request grammar behave, and what are their traps? | `references/managed-launcher.md` |
| What ships with the dedicated server, and which script reads `serverDZ.cfg`, `cfggameplay.json`, `cfgeffectarea.json` and `messages.xml`? Which logs land in the profile folder? | `references/server-and-mission-config.md` |
| What changed in 1.30: unpacked `-mod` folders, new launch flags, headless clients, server load figures, pending actions in single player? | `references/dayz-1-30-test-ingame.md` |
| What changes on a Linux host? | `references/linux.md` |
| How do I prove the server half of a mod on the native Linux `DayZServer`, with no client and no dayz-mcp? | `references/linux-native-server.md` |
| How do I test the client side on Linux with a headless client under Proton, and have a test mod report its own results? | `references/linux-headless-client.md` |
| Has this symptom been seen before in a real session (third-party dependencies, retail capture, launching from an agent, untextured runs)? | `references/session-findings.md` |

## Assets and templates

| Path | What it is |
|---|---|
| `assets/autotest-mod/` | AutoTest, a small mod whose test cases run on server and client and print their results to the logs, so a run reports on itself. Source under `src/AutoTest/` (`config.cpp`, `scripts/3_Game/AutoTestRpc.c`, `scripts/4_World/AutoTestCases.c`, `scripts/4_World/AutoTestRunner.c`, `scripts/5_Mission/AutoTestMission.c`). How to build, load and read it: `references/linux-headless-client.md`, section 3. Keep it out of a release. |
| `templates/dayz-test.ps1` | A PowerShell orchestrator that runs the whole loop for one mod (build, deploy, launch modes, stop). `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-stop-test` are the supported route in this repo. The script needs `P:\`, DayZ Tools and the game and does not go through `/dayz-preflight` (it carries its own `Invoke-Preflight` check), so run `/dayz-preflight` first when you use it. |
| `templates/server.bat`, `templates/client.bat`, `templates/offline.bat` | Double-click wrappers around that orchestrator, one per launch mode. |
