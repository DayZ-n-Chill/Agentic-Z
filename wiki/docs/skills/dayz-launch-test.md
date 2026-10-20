---
name: dayz-launch-test
---

## Overview

Launches a local DayZ Diag server for an instance added with /dayz-add-server, waits for it to bind its port, then starts the diag client connected to it, with the given built mods loaded and file patching on. Run-only; it does no setup. Use when you want to test built mods in game, or to check the exact launch commands with --dry-run.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-launch-test

Run-only: launches a local DayZ test session for one or more built mods. Always starts the **server first**, then the **client** connecting to it (DayZ cannot be tested standalone, per L2 conventions). Both run from `DayZDiag_x64.exe` with `-filePatching` for fast iteration on Enforce Script and config edits.

**Prerequisite:** the instance must have been added with `/dayz-add-server <instance>`, which owns the `.server/<instance>/` layout (mission copy, `serverDZ.cfg`, `Profiles/`, the template junction) and documents how to edit the mission. This skill verifies that state and runs.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\launch.py" <ModName> [<ModName2> ...] [--server <instance>] [--port N] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName> ...` | yes | One or more mod names already built. Each must have at least one `.pbo` at `P:\Mods\@<ModName>\Addons\` (build with `/dayz-build-pbo` first). |
| `--server` | no | Server instance to launch on. Default `chernarus`. Must have been added via `/dayz-add-server`. |
| `--port` | no | Server port. Default `2302`. |
| `--dry-run` | no | Run every check, print the resolved server and client commands, then exit 0. Writes nothing: no cfg edit, no profile dirs, no display-prefs file, no processes. |

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Old-layout gate**: refuses if `workspace/_server/` still exists. Delete the folder manually; that layout is no longer supported.
3. **Built-mod check**: for each mod, verifies at least one `.pbo` exists in `P:\Mods\@<ModName>\Addons\`. Fails fast with a hint to run `/dayz-build-pbo` if missing.
4. **Diag client resolution**: finds `DayZDiag_x64.exe` via `find_dayz_diag()` (env var, DayZ game install, Steam paths). Both client and server run from this binary; the server adds `-server`. Retail `DayZ_x64.exe` and `DayZServer_x64.exe` are not used; both block past the loading screen with `-filePatching` enabled.
5. **Instance check**: reads the mission template from the `template = "...";` line in `.server/<instance>/serverDZ.cfg` and confirms `mission/` and the `<template>/` junction to it exist. The server's `-mission=` points at that junction (the engine resolves the template name during the connect handshake; without it the client connects but never spawns). Anything missing fails with a hint to run `/dayz-add-server <instance>`. Outside `--dry-run` it appends `allowFilePatching = 1;` to a cfg that lacks it and creates the two profile dirs if absent.
6. **Launch server**: spawns `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/Profiles -mission=<instance>/<template> -mod=P:\Mods\@Mod1;P:\Mods\@Mod2 -filePatching -port=<port>`.
7. **Wait for the port**: polls once a second, for up to 180 s, until the server has bound UDP `<port>` (a DayZ server can take 30 s or more to load the mission and mods). If the server exits, or the wait times out (the server is then killed), the skill exits 1 without starting the client.
8. **Launch client**: spawns `DayZDiag_x64.exe -profiles=.server/!ClientDiagLogs -mod=... -connect=127.0.0.1 -port=<port> -filePatching` plus the display flags from the per-clone preferences.
9. **Print PIDs and exit.** Both processes run independently. Close the windows to stop them, or run `/dayz-stop-test`.

## Refuses to run if

- No project is cached (run `/dayz-init`).
- `/dayz-preflight` returns non-zero.
- `workspace/_server/` still exists.
- Any named mod has no `.pbo` at `P:\Mods\@<ModName>\Addons\`.
- `DayZDiag_x64.exe` is not found.
- The `--server` instance is not set up: `serverDZ.cfg` missing or without a `template = "...";` line, `mission/` missing, or the `<template>/` junction missing. Run `/dayz-add-server <instance>`.

## Output (success)

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    Project: C:\Projects\MyDayZProject
[OK]    BuildTest PBO present: P:\Mods\@BuildTest\Addons\BuildTest.pbo
[OK]    Diag client: C:\Program Files (x86)\Steam\steamapps\common\DayZ\DayZDiag_x64.exe
[OK]    Instance: chernarus
[OK]    Instance dir: .server\chernarus

[Launch] Server: DayZDiag_x64.exe -server -config=...\chernarus\serverDZ.cfg -profiles=...\chernarus\Profiles -mission=...\chernarus\dayzOffline.chernarusplus -mod=P:\Mods\@BuildTest -filePatching -port=2302
[OK]    Server PID: 12345
        Waiting up to 180s for server to bind UDP port 2302...
......
[OK]    Server has bound UDP port 2302

[Launch] Client: DayZDiag_x64.exe -profiles=...\!ClientDiagLogs -mod=P:\Mods\@BuildTest -connect=127.0.0.1 -port=2302 -filePatching -window -x=1920 -y=1080
[OK]    Client PID: 67890

Both running. Close the windows manually to stop.
  Server PID: 12345    Client PID: 67890
  Server logs: .server\chernarus\Profiles
  Client logs: .server\!ClientDiagLogs
```

With `--dry-run`, the output is the same through the instance check (plus a `[DRY-RUN] Would append allowFilePatching = 1 ...` line if the cfg lacks it), then the two `[DRY-RUN] Server cmd:` / `[DRY-RUN] Client cmd:` lines, and exit 0.

## Client display preferences

The client reads `.claude/local-memory/dayz-client-display.json` (per clone, gitignored). The first real launch creates it with:

```json
{
  "windowed": true,
  "width": 1920,
  "height": 1080
}
```

These map to `-window`, `-x=<width>`, `-y=<height>`. Edit the file freely; an unparseable file falls back to the defaults with a warning.

## Do not

- Don't launch the client without the server. DayZ has no offline mode for mod testing.
- Don't substitute retail `DayZ_x64.exe` or `DayZServer_x64.exe` for the diag binary.
- Don't kill the session from here once it is running; close the windows or use `/dayz-stop-test`.
