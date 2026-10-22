---
name: dayz-workdrive
---

## Overview

Mounts or unmounts P:\ as the DayZ work drive without opening the DayZ Tools GUI. Windows-only and idempotent. Use when P:\ is not mounted (usually after a reboot) before any other DayZ skill, or when the user asks to mount or unmount the work drive.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-workdrive

Mount `P:\` for DayZ modding without DayZ Tools' GUI.

Follow `.claude/skills/_shared/dayz-conventions.md`. This skill does not gate on `/dayz-preflight`, because preflight fails until `P:\` is mounted and this skill is what mounts it.

## How to run

```
python "<skill-dir>\mount.py"                                  # resolve and mount
python "<skill-dir>\mount.py" --path "C:\Path\To\WorkDrive"    # explicit folder
python "<skill-dir>\mount.py" --unmount
```

`scripts\setup\workdrive.bat` takes the same arguments for users running it outside Claude Code.

## What it does

1. If `P:\` is already mounted, prints `[OK]` with the folder it points to and exits 0. If `--path` names a different folder, it also prints a `[WARN]`: the mount is left alone, so run `--unmount` first to switch folders. When `P:\` is a volume or network drive rather than a folder mapping, any `--path` gets the same `[WARN]`, because the skill cannot tell where `P:\` points.
2. Resolves the work-drive folder, taking the first candidate that exists:
   1. `--path` (fails if it is not a directory)
   2. `$DAYZ_WORK_DRIVE`
   3. The path cached by a previous successful run in `<project>\.claude\local-memory\dayz-work-drive.json`, where `<project>` is `$CLAUDE_PROJECT_DIR`, else the nearest folder at or above the current directory whose `.claude\local-memory\` holds the `/dayz-init` project cache, else the current directory (the same rule `/dayz-init` uses, so a plugin install caches per project and a run from `scripts\setup\` or `workspace\<mod>\` still finds the project)
   4. `[ProjectDrive] path=` in `<DayZ Tools>\settings.ini`
   5. Registry values `WorkDrive`, `WorkDrivePath`, `P_Drive` or `PDrive` under the DayZ Tools keys (HKCU, then HKLM 64-bit and 32-bit)

   If none of these exists the skill exits 1 and asks for `--path`. It never falls back to `<DayZ Tools>\Bin\WorkDrive`: that folder holds `WorkDrive.exe` itself, not a project drive.
3. Prints and runs `WorkDrive.exe /Mount "<folder>"`. If `P:\` still is not visible (or WorkDrive.exe is missing), falls back to `subst P: "<folder>"`.
4. On success, caches the folder for the next run.

DayZ Tools is located with the shared `find_dayz_tools()` resolver from `dayz-preflight/preflight.py`.

`--unmount` runs `WorkDrive.exe /Dismount`, falling back to `subst P: /D` if `P:\` is still visible; it is a no-op when `P:\` is not mounted.

## Output

```
DayZ P:\ mount

[INFO] Mounting P: -> C:\P Drives\Vanilla
[CMD]  "C:\...\DayZ Tools\Bin\WorkDrive\WorkDrive.exe" /Mount "C:\P Drives\Vanilla"
[OK]   P:\ mounted -> C:\P Drives\Vanilla
[INFO] Cached for future runs at <project>\.claude\local-memory\dayz-work-drive.json
```

When nothing resolves it prints, on stderr:

```
[FAIL] Could not resolve a work drive folder.
       Tried: $DAYZ_WORK_DRIVE, cached path, settings.ini, registry.
       Pass --path "C:\path\to\workdrive" with the folder P:\ should show (it is cached for later runs).
```

When already mounted it prints `[OK]   P:\ already mounted -> <folder>` and runs nothing.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | `P:\` is mounted (or, with `--unmount`, unmounted or already absent) |
| 1 | No work-drive folder could be resolved, `--path` is not a directory, both WorkDrive.exe and `subst` failed (the `subst` exit code is printed), or `--unmount` left `P:\` mounted |
| 2 | Bad argument, such as an unknown option or `--path` with no folder (argparse prints the usage) |
