---
name: dayz-workdrive
description: "Mounts or unmounts P:\\ as the DayZ work drive without opening the DayZ Tools GUI. Windows-only and idempotent. Use when P:\\ is not mounted (usually after a reboot) before any other DayZ skill, or when the user asks to mount or unmount the work drive."
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
python "<skill-dir>\mount.py" --unmount --force               # unmount even while DayZ Tools or DayZDiag runs
```

`scripts\setup\workdrive.bat` takes the same arguments for users running it outside Claude Code.

## What it does

1. If `P:\` is already mounted, prints `[OK]` with the folder it points to and exits 0. If `--path` names a different folder, it also prints a `[WARN]`: the mount is left alone, so run `--unmount` first to switch folders. When `P:\` is a volume or network drive rather than a folder mapping, any `--path` gets the same `[WARN]`, because the skill cannot tell where `P:\` points.
2. Resolves the work-drive folder, taking the first candidate that exists:
   1. `--path` (fails if it is not a directory). A relative `--path` is made absolute against the current folder first, so the folder that is mounted and cached is the same one from any later run
   2. `$DAYZ_WORK_DRIVE`
   3. The path cached by a previous successful run in `<project>\.claude\local-memory\dayz-work-drive.json`, where `<project>` is `$CLAUDE_PROJECT_DIR`, else the nearest folder at or above the current directory whose `.claude\local-memory\` holds the `/dayz-init` project cache, else the clone that holds the skill scripts when that clone has the cache, else the current directory (the same rule `/dayz-init` uses, so a plugin install caches per project and a run from `scripts\setup\` or `workspace\<mod>\` still finds the project)
   4. `[ProjectDrive] path=` in `<DayZ Tools>\settings.ini`

   If none of these exists the skill exits 1 and asks for `--path`. It never falls back to `<DayZ Tools>\Bin\WorkDrive`: that folder holds `WorkDrive.exe` itself, not a project drive. The DayZ Tools registry keys are not a source: they hold the install path, not the work drive folder.
3. Prints and runs `WorkDrive.exe /Mount "<folder>"`. WorkDrive.exe gets 60 seconds; if it is still running (stuck at its "press any key" prompt) it is stopped. If `P:\` still is not visible (or WorkDrive.exe is missing or was stopped), falls back to `subst P: "<folder>"`. When `[ProjectDrive] Letter=` in `settings.ini` is not `P`, WorkDrive.exe would mount that letter instead, so the skill prints `[WARN] DayZ Tools' settings.ini sets [ProjectDrive] Letter=<X>, so WorkDrive.exe would mount <X>: instead of P:\. Using subst P: instead.` and goes straight to `subst P:`. `--unmount` then skips WorkDrive.exe the same way.
4. On success, caches the folder for the next run.

DayZ Tools is located with the shared `find_dayz_tools()` resolver from `dayz-preflight/preflight.py`.

`--unmount` runs `WorkDrive.exe /Dismount`, falling back to `subst P: /D` if `P:\` is still visible; it is a no-op when `P:\` is not mounted. Before unmounting it lists running processes with `tasklist` and refuses (exit 1, nothing unmounted) while any of `WorkbenchApp.exe`, `ObjectBuilder.exe`, `AddonBuilder.exe`, `binarize.exe` or `DayZDiag_x64.exe` is running, because pulling `P:\` out from under them breaks those open sessions. Close them first (`/dayz-stop-test` stops DayZDiag), or pass `--force` to unmount anyway with a `[WARN]` naming them. If `tasklist` cannot start, exits non-zero or prints nothing, the running processes are unknown, so `--unmount` refuses the same way (exit 1, `[FAIL] Not unmounting: tasklist failed ...`); `--force` unmounts anyway with a `[WARN]` that nothing was checked.

`--force` is accepted only with `--unmount`, and `--path` only without it; either mismatch exits 2 with an argparse error instead of being silently ignored.

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
       Tried: $DAYZ_WORK_DRIVE, cached path, settings.ini.
       Pass --path "C:\path\to\workdrive" with the folder P:\ should show (it is cached for later runs).
```

When already mounted it prints `[OK]   P:\ already mounted -> <folder>` and runs nothing.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | `P:\` is mounted (or, with `--unmount`, unmounted or already absent) |
| 1 | No work-drive folder could be resolved, `--path` is not a directory, both WorkDrive.exe and `subst` failed (the `subst` exit code is printed), `--unmount` left `P:\` mounted, or `--unmount` without `--force` found DayZ Tools or DayZDiag running or could not list processes |
| 2 | Bad argument, such as an unknown option, `--path` with no folder, `--force` without `--unmount`, or `--path` with `--unmount` (argparse prints the usage) |
