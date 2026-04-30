---
name: dayz-stop-test
description: Kill any running DayZDiag_x64.exe processes (server and/or client). Use after /dayz-launch-test when you want to stop a session without manually finding the windows. Does NOT gate on /dayz-preflight — this is an emergency-stop skill that should work even if the environment is half-broken.
---

# /dayz-stop-test

Stop a running local DayZ test session by killing every `DayZDiag_x64.exe` process. Counterpart to `/dayz-launch-test`.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-stop-test\stop_test.py
```

No arguments, no flags. Always kills every `DayZDiag_x64.exe` process via `taskkill /IM DayZDiag_x64.exe /F`.

## Why no preflight gate

Every other DayZ skill gates on `/dayz-preflight` per the L2 convention. **This skill is the documented exception**: stop-test is an emergency escape hatch that must work even when the environment is half-broken (P:\ dismounted, etc.). If you can't run preflight, you can still stop runaway processes.

The rule going forward: skills that **do** work (scaffold, build, launch) gate on preflight; skills that **only abort** work (this one) do not.

## What it does

1. Runs `taskkill /IM DayZDiag_x64.exe /F` (Windows). Force-kills any process with that image name — both server and client sessions.
2. Reports how many processes were terminated.
3. Exit 0 whether processes existed or not (no diag running is the desired end state either way).

## What it WILL NOT do

- Doesn't kill any other DayZ processes (`DayZ_x64.exe` retail, `DayZServer_x64.exe` retail, `DayZLauncher.exe`). Mod-test sessions only run diag — those other processes belong to your normal play / launcher use and stay alone.
- Doesn't clean up logs or state. That's `/dayz-clean-workspace`'s job.
- Doesn't unmount `P:\`, doesn't touch DayZ Tools, doesn't remove junctions.

## Output

```
[OK]    Stopped 2 DayZDiag_x64.exe process(es).
```

Or, if nothing was running:

```
[OK]    No DayZDiag_x64.exe processes running.
```

## Do not

- Don't add a preflight gate. The point of this skill is that it works regardless of environment state.
- Don't extend it to kill other DayZ-related processes by default. If you need that, write a separate skill — keep this one focused on the diag-mod-test session.
- Don't add confirmation prompts. Stop is a fast escape; one command, one kill.
