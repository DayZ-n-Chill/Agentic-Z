---
name: dayz-workdrive
---

## Overview

Mount P:\ as the DayZ work drive after a Windows boot, without opening DayZ Tools' GUI. Resolves the work drive path via env var, cache, settings.ini, registry, or DayZ Tools install. Idempotent. Windows-only (uses subst).

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-workdrive

Mount `P:\` for DayZ modding without DayZ Tools' GUI.

## Run

Direct (preferred, no agent):
```
scripts\workdrive.bat
scripts\workdrive.bat --path "C:\Path\To\WorkDrive"
scripts\workdrive.bat --unmount
```

Or call Python directly:
```
python "<skill-dir>\mount.py"
python "<skill-dir>\mount.py" --path "C:\Path\To\WorkDrive"
python "<skill-dir>\mount.py" --unmount
```

## When

- After a Windows boot, before any other DayZ skill (preflight gates on P:\ being mounted).
- Idempotent: re-running while mounted is a no-op.

## Does NOT gate on /dayz-preflight

Chicken-and-egg: preflight checks for P:\, this skill mounts it. Run this first.

## Notes

- Python (per the L1 "Python by default" rule). Reuses `find_dayz_tools` from `dayz-preflight` to avoid duplicating registry/Steam-path probing.
- Prints the actual `WorkDrive.exe /Mount` or `subst P:` command before executing it, so users learn the underlying primitive.
- Caches the resolved path at `.claude/local-memory/dayz-work-drive.json` for instant re-runs.
