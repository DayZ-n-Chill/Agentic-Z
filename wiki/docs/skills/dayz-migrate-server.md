---
name: dayz-migrate-server
---

## Overview

One-shot migration from the legacy `workspace/_server/` layout to `.server/<instance>/`. For each old map directory at `workspace/_server/maps/<map>/`, creates a matching `.server/<map>/` instance with `mission/`, `serverDZ.cfg`, `server-profiles/`, `client-profiles/`. Mission folders are copied (not moved), and renamed to `mission/`. The orphaned shared `!ClientDiagLogs/` is assigned to the alphabetically-first migrated instance. Idempotent. Leaves the legacy folder intact for the user to delete after verification.

# /dayz-migrate-server

Migrate from the legacy DayZ test-server layout (`workspace/_server/`) to the new instance-based layout (`.server/<instance>/`). One-shot; subsequent skills (`/dayz-add-server`, `/dayz-launch-test`, `/dayz-clean-workspace`) all refuse to run while the legacy folder still exists, so this is a hard gate.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-migrate-server\migrate.py [--instance-name <name>] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `--instance-name` | no | Override the new instance name. Only valid when exactly one old map directory exists (`workspace/_server/maps/` has exactly one child). With multiple maps, instance names always default to old map directory names. |
| `--dry-run` | no | Print the planned migration; touch nothing. |

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Detect legacy layout**: exits 0 if `workspace/_server/` doesn't exist.
3. **Plan**: for each `workspace/_server/maps/<map>/` directory, plan a new instance at `.server/<map>/` (or `.server/<--instance-name>/` if exactly one map and the flag was given).
4. **Migrate per instance:**
   - `mission/`: **copied** (not moved) from `workspace/_server/missions/<template>/` (the template name comes from the old `serverDZ.cfg`'s `template = "..."` line). Mission folder is renamed to `mission/` regardless of original name. Mission stays a copy because multiple old maps may have shared one template; moving would break the others.
   - `serverDZ.cfg`: moved.
   - `server-profiles/`: moved from old `profiles/`.
   - `client-profiles/`: created empty.
5. **Orphaned shared client logs**: `workspace/_server/!ClientDiagLogs/` contents are moved into the alphabetically-first migrated instance's `client-profiles/`, with a printed warning that the old layout did not isolate client logs and the user can manually redistribute.
6. **Leaves legacy intact**: `workspace/_server/` remains for the user to inspect and delete manually after verifying the new instances launch.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `--instance-name` is given but more than one old map directory exists.

## Output (success)

```
DayZ preflight
... (preflight output)
Preflight complete.

Migration plan: 1 instance(s)
  workspace\_server\maps\chernarus  ->  .server\chernarus  (mission template: dayzOffline.chernarusplus)
  workspace\_server\!ClientDiagLogs  ->  .server\chernarus\client-profiles  (orphaned shared client logs assigned to first instance)

[OK]    Copied mission for 'chernarus': .server\chernarus\mission
[OK]    Moved serverDZ.cfg for 'chernarus'
[OK]    Moved server profiles for 'chernarus'
[OK]    Moved orphaned client logs into 'chernarus' client-profiles
[WARN]  Old layout did not isolate client logs by map. Logs were assigned to the
        first instance ('chernarus') alphabetically. Manually redistribute to
        other instances if you want them attributed differently.

[OK]    Migration complete. New instances under .server/

[WARN]  Legacy workspace/_server/ has been left intact.
        Verify the new instances launch correctly:
          /dayz-launch-test &lt;ModName&gt; --server chernarus
        Then delete the legacy folder manually:
          cmd /c rmdir /s /q workspace\_server
```

## Do not

- Don't run this skill twice without inspecting the result. It's idempotent (safe to re-run on partial state) but the second run is a no-op once `.server/<instance>/` directories already have content.
- Don't auto-delete `workspace/_server/` from the migration. The legacy folder is left intact deliberately so the user can verify the new instances work before committing to the move.
