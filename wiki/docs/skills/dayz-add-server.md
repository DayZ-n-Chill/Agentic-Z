---
name: dayz-add-server
---

## Overview

Sets up an isolated DayZ test server instance under .server/&lt;instance&gt;/ with its own mission copy, serverDZ.cfg and profiles. Use when you need a new test instance before /dayz-launch-test (for example chernarus or chernarus-hardcore), or to refresh the mission after a DayZ update.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-add-server

Set up a self-contained test server instance for local DayZ mod testing. Each instance lives under `.server/<instance>/` and owns its mission copy, server config, and server logs. Client diag logs are shared across instances at `.server/!ClientDiagLogs/`. Run as many instances as you want, including multiple variants of the same map.

This is the **setup** half of the test loop. `/dayz-launch-test` is the **run** half, and refuses to run for an instance you haven't added yet.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\add_server.py" <instance> [--map <name>] [--refresh-mission]
```

| Argument | Required? | Notes |
|---|---|---|
| `<instance>` | yes | Free-form instance name. Becomes the folder name under `.server/`, so it must be a single folder name (no `/`, `\`, `:`, `..`, or any of the characters Windows forbids in file names, such as `*`, `?` and `"`). Examples: `chernarus`, `chernarus-hardcore`, `loot-test`, `livonia-pvp`. |
| `--map` | no | Map alias (`chernarus`, `livonia`, `sakhal`) or full mission template folder name (e.g. `dayzOffline.namalsk`). When omitted, `<instance>` is used as the map alias if it matches a known one; otherwise the skill fails and asks for `--map`. |
| `--refresh-mission` | no | Re-copy the mission folder from the DayZ Server install. The current `mission/` is first renamed to `mission.bak-<YYYYMMDD-HHMMSS>/` so your edits stay recoverable. Use after a DayZ update brings new mission content. Without this flag, an existing mission folder is left alone. |

## What it does

1. **Project check**: reads the cached project folder; halts if none is cached (run `/dayz-init`).
2. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
3. **Old-layout gate**: refuses if `workspace/_server/` still exists. Delete the folder manually; that layout is no longer supported.
4. **Resolve map and mission template**: turns the instance name and `--map` flag into the canonical mission folder name via the alias table. If the instance already has a `serverDZ.cfg` whose active `template = "..."` line names a different template, the skill refuses before copying anything (see Refuses to run if).
5. **Mission copy**: if `.server/<instance>/mission/` doesn't exist (or `--refresh-mission` was passed), copies it from `<DayZServer>/mpmissions/<template>/`. With `--refresh-mission`, the existing folder is renamed to `mission.bak-<timestamp>/` first; nothing is deleted. The copy is always named `mission/`.
6. **Instance directory**: ensures `.server/<instance>/` exists with:
   - `serverDZ.cfg`: default config pointing at the right mission template, with `allowFilePatching = 1;` and a `shardId` made of the first six letters and digits of the instance name (padded with `shard`). An existing config is preserved, except that `allowFilePatching = 1;` is appended if no active line exists (a commented-out line does not count) or set back to `1` if it holds any other value. `/dayz-launch-test` refuses to start without that line, so rerunning this skill is the fix.
   - `Profiles/`: server-side `-profiles=` dir (RPT, script.log, BattlEye state). Per-instance.
   - `<template>/` (for example `dayzOffline.chernarusplus/`): a junction to `mission/`. The engine looks the mission up by template name during the client connect handshake; without it the client connects but never spawns. If `mklink` fails, the skill exits non-zero. An existing junction is reported as `[OK]    Junction <template>/ -> mission/ already present`.
7. **Shared client log dir**: ensures `.server/!ClientDiagLogs/` exists; this is the client-side `-profiles=` dir, shared across all instances.

## Refuses to run if

- No project is cached (run `/dayz-init`).
- `/dayz-preflight` returns non-zero.
- `workspace/_server/` still exists. Delete it manually; the legacy layout is no longer supported.
- DayZ Server install isn't found AND the mission isn't already in `.server/<instance>/mission/`. (Install DayZ Server free from Steam appid 223350 for the initial copy. Once the mission is local, DayZ Server is no longer required.)
- `<instance>` contains a path separator, a drive colon, one of `* ? " < > |`, or is `.`/`..` (argparse rejects it, exit 2).
- The instance already exists and its `serverDZ.cfg` `template = "..."` line names a different mission template than this run resolved (for example `chernarus` rerun with `--map livonia`). Add a new instance for the other map, or set the `template =` line yourself and rerun with `--refresh-mission` to swap the mission (the old one is kept as a backup).
- `<instance>` isn't a known map alias and `--map` wasn't given. (We have no way to guess the mission template from a free-form name.)
- DayZ Server install lacks the requested mission template (e.g. `--map dayzOffline.namalsk` but DayZ Server doesn't ship namalsk; either provide the mission manually under `.server/<instance>/mission/` or correct the name).
- The `<template>/` junction to `mission/` cannot be created (the `mklink` error is printed).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    Project: C:\Projects\MyDayZProject
[OK]    Instance: chernarus-hardcore  (map: chernarus, mission: dayzOffline.chernarusplus)
[OK]    Copied .server\chernarus-hardcore\mission  (from DayZ Server install)
[OK]    Wrote default .server\chernarus-hardcore\serverDZ.cfg
[OK]    Junction dayzOffline.chernarusplus/ -> mission/ (template handshake)
[OK]    .server\chernarus-hardcore\Profiles ready
[OK]    .server\!ClientDiagLogs ready

Instance 'chernarus-hardcore' is ready. Next:
  /dayz-build-pbo <ModName>
  /dayz-launch-test <ModName> --server chernarus-hardcore
```

On a rerun with everything already set up, the changed lines read:

```
[OK]    Mission already present: .server\chernarus-hardcore\mission
[OK]    .server\chernarus-hardcore\serverDZ.cfg unchanged (already configured)
[OK]    Junction dayzOffline.chernarusplus/ -> mission/ already present
```

## Editing what this skill creates

- **Mission folder** at `.server/<instance>/mission/` is yours to edit. The server runs with `-filePatching` so edits to `init.c`, `cfggameplay.json`, `db/types.xml`, etc. are live on the next launch.
- **`serverDZ.cfg`** at `.server/<instance>/serverDZ.cfg` is yours to tune (max players, persistence, etc.). The skill never overwrites your edits, except `allowFilePatching`: it is re-added if you remove it and set back to `1` if you change it (without it, clients launched with `-filePatching` can't connect).

## Do not

- Don't edit missions inside the DayZ Server Steam install; edit the instance copy at `.server/<instance>/mission/`.
- Don't move `.server/` into `workspace/`. The split is deliberate: `workspace/` is for active mod sources, `.server/` is for runtime artifacts.
