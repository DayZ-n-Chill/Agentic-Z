---
name: dayz-stop-test
description: Kills every running DayZDiag_x64.exe process (local test server and client). Use when a /dayz-launch-test session needs to stop without hunting for its windows, including when the environment is half-broken. Does not gate on /dayz-preflight.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-stop-test

Stop a running local DayZ test session by killing every `DayZDiag_x64.exe` process. Counterpart to `/dayz-launch-test`.

Follow `.claude/skills/_shared/dayz-conventions.md`. This skill is the abort-only exception to the preflight gate described there, so it works even with `P:\` dismounted.

## How to run

```cmd
"<skill-dir>\stop_test.bat"
```

No arguments. Runs `taskkill /IM DayZDiag_x64.exe /F`. A thin `.bat` is enough because the whole job is one `taskkill` call.

## Exit codes

| taskkill result | Output | Exit |
|---|---|---|
| Processes killed | One `SUCCESS:` line per process | 0 |
| No process running (errorlevel 128) | taskkill's "not found" line, then `[OK]   No DayZDiag_x64.exe processes running.` | 0 |
| Any other failure (e.g. access denied) | taskkill's error, then `[FAIL] taskkill failed with errorlevel N.` | N |

taskkill's error stream is not suppressed, so real failures stay visible.

## Scope

- Only `DayZDiag_x64.exe`. Retail `DayZ_x64.exe`, `DayZServer_x64.exe` and `DayZLauncher.exe` belong to normal play and are left alone.
- Doesn't clean logs or state (that's `/dayz-clean-workspace`), unmount `P:\`, or remove junctions.
- No confirmation prompt: stop is a fast escape.
