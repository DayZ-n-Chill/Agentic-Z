---
name: dayz-stop-test
---

## Overview

Kill any running DayZDiag_x64.exe processes (server and/or client). Use after /dayz-launch-test when you want to stop a session without manually finding the windows. Does NOT gate on /dayz-preflight — this is an emergency-stop skill that should work even if the environment is half-broken.

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-stop-test

Stop a running local DayZ test session by killing every `DayZDiag_x64.exe` process. Counterpart to `/dayz-launch-test`.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
"<skill-dir>\stop_test.bat"
```

No arguments, no flags. Always kills every `DayZDiag_x64.exe` process via `taskkill /IM DayZDiag_x64.exe /F`.

This skill is a thin `.bat` wrapper — no Python — because the entire job is a single `taskkill` invocation. Per the L1 rule (Python by default, `.bat` for trivial wrappers around an exe), this is the trivial case.

## Why no preflight gate

Every other DayZ skill gates on `/dayz-preflight` per the L2 convention. **This skill is the documented exception**: stop-test is an emergency escape hatch that must work even when the environment is half-broken (P:\ dismounted, etc.). If you can't run preflight, you can still stop runaway processes.

The rule going forward: skills that **do** work (scaffold, build, launch) gate on preflight; skills that **only abort** work (this one) do not.

## What it does

1. Runs `taskkill /IM DayZDiag_x64.exe /F` (Windows). Force-kills any process with that image name — both server and client sessions.
2. Lets `taskkill`'s own output through (one `SUCCESS:` line per killed process).
3. If nothing was running, prints `[OK]   No DayZDiag_x64.exe processes running.` instead of `taskkill`'s noisy `ERROR: ... not found.`
4. Exit 0 whether processes existed or not (no diag running is the desired end state either way).

## What it WILL NOT do

- Doesn't kill any other DayZ processes (`DayZ_x64.exe` retail, `DayZServer_x64.exe` retail, `DayZLauncher.exe`). Mod-test sessions only run diag — those other processes belong to your normal play / launcher use and stay alone.
- Doesn't clean up logs or state. That's `/dayz-clean-workspace`'s job.
- Doesn't unmount `P:\`, doesn't touch DayZ Tools, doesn't remove junctions.

## Output

When something was running:

```
SUCCESS: The process "DayZDiag_x64.exe" with PID 12345 has been terminated.
SUCCESS: The process "DayZDiag_x64.exe" with PID 12346 has been terminated.
```

When nothing was running:

```
[OK]   No DayZDiag_x64.exe processes running.
```

## Do not

- Don't add a preflight gate. The point of this skill is that it works regardless of environment state.
- Don't extend it to kill other DayZ-related processes by default. If you need that, write a separate skill — keep this one focused on the diag-mod-test session.
- Don't add confirmation prompts. Stop is a fast escape; one command, one kill.
