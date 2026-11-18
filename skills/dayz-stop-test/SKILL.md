---
name: dayz-stop-test
description: "Kills every running DayZDiag_x64.exe process (local test server and client). Use when a /dayz-launch-test session needs to stop, including when the environment is half-broken; does not gate on /dayz-preflight."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-stop-test

Stop a running local DayZ test session by killing every `DayZDiag_x64.exe` process. Counterpart to `/dayz-launch-test`.

Follow `skills/_shared/dayz-conventions.md`. This skill is the abort-only exception to the preflight gate described there, so it works even with `P:\` dismounted.

## How to run

```cmd
"<skill-dir>\stop_test.bat"
```

No arguments (`--help` or `-h` prints usage). Runs `taskkill /IM DayZDiag_x64.exe /F`. A thin `.bat` is enough because the whole job is one `taskkill` call.

## Exit codes

| taskkill result | Output | Exit |
|---|---|---|
| Processes killed | One `SUCCESS:` line per process | 0 |
| No process running (errorlevel 128) | `[OK]   No DayZDiag_x64.exe processes running.` only | 0 |
| Any other failure (e.g. access denied) | taskkill's error, then `[FAIL] taskkill failed with errorlevel N.` | N |
| `--help` or `-h` (taskkill not run) | The usage text | 0 |
| Any other argument (taskkill not run) | `[FAIL] Unknown argument: <arg> (stop-test takes no arguments; see --help).` | 2 |

taskkill's error output is captured and dropped only for errorlevel 128 (its "process not found" line); for every other result it is re-printed on stderr, so real failures stay visible.

## Scope

- Only `DayZDiag_x64.exe`. Retail `DayZ_x64.exe`, `DayZServer_x64.exe` and `DayZLauncher.exe` belong to normal play and are left alone.
- Doesn't clean logs or state (that's `/dayz-clean-workspace`), unmount `P:\`, or remove junctions.
- No confirmation prompt: stop is a fast escape.

## Before you stop a session you did not start

`taskkill /IM` ends every `DayZDiag_x64.exe` on the machine, whoever started it. The test machine has one game port and one Steam client, so another session (the user's own play session, a second agent) may hold it. The measured cases are in `skills/dayz-launch-test/references/test-machine-sharing.md`, "Check who holds the machine before any kill or launch".

- **See who is running first** when the session is not clearly yours. List the processes with their command lines and read each `-mod=` and `-profiles=` value:

  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe' OR Name='DayZServer_x64.exe'" | Select-Object ProcessId, CommandLine
  ```

  If a process loads a mod other than the one under test, ask the user before stopping it. `/dayz-gate` applies the same rule: it stops a session it did not start only after `--yes` or a yes at the prompt.
- **`DayZServer_x64.exe` is a separate process and stays up.** This skill never kills it. A retail server started by hand keeps holding its port until whoever started it closes it.
- **A server killed while it saves can leave half-written persistence.** The next start then dies before binding its port with `!!! Serious stream damage detected during load`, which looks like a mod bug. `/dayz-gate` and `/dayz-logwatch` name it (`storage-stream-damage`) with the fix: rename the mission's `storage_1` with the server stopped, after telling the user that the world and characters reset.
