---
name: dayz-workdrive
description: Mounts P:\ as the DayZ work drive without opening the DayZ Tools GUI, using WorkDrive.exe with a subst fallback, and can unmount it. Resolves the work-drive folder from an env var, cached path, settings.ini, registry or the DayZ Tools default. Idempotent, Windows-only. Use when P:\ is not mounted (usually after a reboot) and before any other DayZ skill, or when the user asks to mount or unmount the work drive.
---

<!-- skill-dir-note -->
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

1. If `P:\` is already mounted, prints `[OK]` and exits 0.
2. Resolves the work-drive folder, taking the first candidate that exists:
   1. `--path` (fails if it is not a directory)
   2. `$DAYZ_WORK_DRIVE`
   3. The path cached by a previous successful run in `.claude/local-memory/dayz-work-drive.json`
   4. `[ProjectDrive] path=` in `<DayZ Tools>\settings.ini`
   5. Registry values `WorkDrive`, `WorkDrivePath`, `P_Drive` or `PDrive` under the DayZ Tools keys (HKCU, then HKLM 64-bit and 32-bit)
   6. `<DayZ Tools>\Bin\WorkDrive`
3. Prints and runs `WorkDrive.exe /Mount "<folder>"`. If `P:\` still is not visible (or WorkDrive.exe is missing), falls back to `subst P: "<folder>"`.
4. On success, caches the folder for the next run.

DayZ Tools is located with the shared `find_dayz_tools()` resolver from `dayz-preflight/preflight.py`.

`--unmount` runs `WorkDrive.exe /Dismount`, falling back to `subst P: /D` if `P:\` is still visible; it is a no-op when `P:\` is not mounted.

## Output

```
DayZ P:\ mount

[INFO] Mounting P: -> C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\WorkDrive
[CMD]  "C:\...\DayZ Tools\Bin\WorkDrive\WorkDrive.exe" /Mount "C:\...\DayZ Tools\Bin\WorkDrive"
[OK]   P:\ mounted -> C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\WorkDrive
[INFO] Cached for future runs at <project>\.claude\local-memory\dayz-work-drive.json
```

When already mounted it prints `[OK]   P:\ already mounted` and runs nothing.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | `P:\` is mounted (or, with `--unmount`, unmounted or already absent) |
| 1 | No work-drive folder could be resolved, `--path` is not a directory, both WorkDrive.exe and `subst` failed (the `subst` exit code is printed), or `--unmount` left `P:\` mounted |
