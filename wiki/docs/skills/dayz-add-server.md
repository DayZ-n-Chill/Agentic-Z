---
name: dayz-add-server
---

## Overview

Set up a DayZ test server instance under .server/&lt;instance&gt;/. Copies the mission template from DayZ Server install if missing, creates per-instance serverDZ.cfg + Profiles/ (server -profiles=) and a top-level shared .server/!ClientDiagLogs/ (client -profiles=). Each instance is isolated on the server side so you can run multiple variants of the same map (chernarus, chernarus-hardcore, etc.) without cross-contamination. Refuses if the legacy workspace/_server/ layout exists (delete it manually; that layout is no longer supported). Required before /dayz-launch-test for a given instance. Use --refresh-mission to re-copy mission content after a DayZ update.

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
| `<instance>` | yes | Free-form instance name. Becomes the folder name under `.server/`. Examples: `chernarus`, `chernarus-hardcore`, `loot-test`, `livonia-pvp`. |
| `--map` | no | Map alias (`chernarus`, `livonia`, `sakhal`) or full mission template folder name (e.g. `dayzOffline.namalsk`). When omitted, `<instance>` is used as the map alias if it matches a known one; otherwise the skill fails and asks for `--map`. |
| `--refresh-mission` | no | Re-copy the mission folder from DayZ Server install, **overwriting any local edits**. Use after a DayZ update brings new mission content. Without this flag, an existing mission folder is left alone. |

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Old-layout gate**: refuses if `workspace/_server/` still exists. Delete the folder manually; that layout is no longer supported.
3. **Resolve map and mission template**: turns the instance name and `--map` flag into the canonical mission folder name via the alias table.
4. **Mission copy**: if `.server/<instance>/mission/` doesn't exist (or `--refresh-mission` was passed), copies it from `<DayZServer>/mpmissions/<template>/`. Folder is renamed to `mission/` regardless of template (the launcher pins the path explicitly).
5. **Instance directory**: ensures `.server/<instance>/` exists with:
   - `serverDZ.cfg`: default config pointing at the right mission template, with `allowFilePatching = 1;`
   - `Profiles/`: server-side `-profiles=` dir (RPT, script.log, BattlEye state). Per-instance.
   Also ensures the shared `.server/!ClientDiagLogs/` dir at the project root exists; this is the client-side `-profiles=` dir, shared across all instances.
   If `serverDZ.cfg` already exists, the existing config is preserved; only `allowFilePatching = 1;` is auto-appended if missing.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `workspace/_server/` still exists. Delete it manually; the legacy layout is no longer supported.
- DayZ Server install isn't found AND the mission isn't already in `.server/<instance>/mission/`. (Install DayZ Server free from Steam appid 223350 for the initial copy. Once the mission is local, DayZ Server is no longer required.)
- `<instance>` isn't a known map alias and `--map` wasn't given. (We have no way to guess the mission template from a free-form name.)
- DayZ Server install lacks the requested mission template (e.g. `--map dayzOffline.namalsk` but DayZ Server doesn't ship namalsk; either provide the mission manually under `.server/<instance>/mission/` or correct the name).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    Instance: chernarus-hardcore  (map: chernarus, mission: dayzOffline.chernarusplus)
[OK]    Copied .server\chernarus-hardcore\mission  (from DayZ Server install)
[OK]    Wrote default .server\chernarus-hardcore\serverDZ.cfg
[OK]    .server\chernarus-hardcore\Profiles ready
[OK]    .server\!ClientDiagLogs ready

Instance 'chernarus-hardcore' is ready. Next:
  /dayz-build-pbo <ModName>
  /dayz-launch-test <ModName> --server chernarus-hardcore
```

If everything is already set up, the skill no-ops the relevant steps and reports them as `[OK]` (already present).

## Editing what this skill creates

- **Mission folder** at `.server/<instance>/mission/` is yours to edit. The server runs with `-filePatching` so edits to `init.c`, `cfggameplay.json`, `db/types.xml`, etc. are live on the next launch.
- **`serverDZ.cfg`** at `.server/<instance>/serverDZ.cfg` is yours to tune (max players, persistence, etc.). The skill never overwrites your edits, but it WILL re-add `allowFilePatching = 1;` if you remove it (without that, clients with `-filePatching` can't connect).

## Do not

- Don't edit missions inside the DayZ Server Steam install; edit the workspace copy.
- Don't move `.server/` into `workspace/`. The split is deliberate: `workspace/` is for active mod sources, `.server/` is for runtime artifacts.
