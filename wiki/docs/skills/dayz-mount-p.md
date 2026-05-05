---
name: dayz-mount-p
---

# /dayz-mount-p

Mount `P:\` for DayZ modding without DayZ Tools' GUI.

## Run

Direct (preferred, no agent):
```
scripts\mount-p.bat
scripts\mount-p.bat -Path "C:\Path\To\WorkDrive"
scripts\mount-p.bat -Unmount
```

Or call PowerShell directly:
```
powershell -NoProfile -File .claude\skills\dayz-mount-p\mount.ps1
```

## When

- After a Windows boot, before any other DayZ skill (preflight gates on P:\ being mounted).
- Idempotent: re-running while mounted is a no-op.

## Does NOT gate on /dayz-preflight

Chicken-and-egg: preflight checks for P:\, this skill mounts it. Run this first.

## Notes

- Pure PowerShell. No Python required.
- Prints the actual `WorkDrive.exe /Mount` or `subst P:` command before executing it, so users learn the underlying primitive.
- Caches the resolved path at `.claude/local-memory/dayz-work-drive.json` for instant re-runs.
