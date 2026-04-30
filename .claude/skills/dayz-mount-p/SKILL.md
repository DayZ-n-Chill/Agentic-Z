---
name: dayz-mount-p
description: Mount the P:\ drive without opening DayZ Tools. P:\ is just a folder mounted as a drive letter (subst); this skill resolves the work drive folder via env var, cache, registry, or DayZ Tools install — then mounts it via Windows' built-in subst command. After a Windows boot or restart, run this once at the start of the session instead of opening DayZ Tools' GUI.
---

# /dayz-mount-p

Mount `P:\` as the DayZ work drive without launching DayZ Tools' GUI. P:\ is just a folder substituted as a drive letter — Windows can do that natively.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Checks if `P:\` is already mounted — if so, exits OK.
2. Resolves the work drive folder. First hit wins:
   - `$DAYZ_WORK_DRIVE` env var
   - Cached path at `.claude/local-memory/dayz-work-drive.json` (set on first successful mount)
   - Windows registry — checks `Software\Bohemia Interactive\DayZ Tools` under HKCU and HKLM (WOW6432Node + native) for several common value names
   - `<DayZ Tools install>\Bin\WorkDrive\` (last-resort default; resolved via `find_dayz_tools()` from preflight.py)
3. Mounts via `subst P: <path>`.
4. Verifies `P:\` is now visible.
5. Caches the resolved path so future runs are instant.

## How to run

**Auto-resolve and mount:**
```cmd
python .claude\skills\dayz-mount-p\mount.py
```

**Explicit path (override resolution, e.g. first time before any cache exists):**
```cmd
python .claude\skills\dayz-mount-p\mount.py --path "C:\path\to\workdrive"
```

**Unmount:**
```cmd
python .claude\skills\dayz-mount-p\mount.py --unmount
```

## When to run

- After a Windows boot / restart, before any other DayZ skill (preflight will fail otherwise).
- When you'd otherwise open DayZ Tools just to click "Mount P Drive."

## Output

```
DayZ P:\ mount

[INFO]  Mounting P: -> C:\Users\you\DayZ-WorkDrive
[OK]    P:\ mounted -> C:\Users\you\DayZ-WorkDrive
[INFO]  Cached for future runs at G:\AI-Templates\.claude\local-memory\dayz-work-drive.json
```

If P:\ is already mounted:
```
[OK]    P:\ already mounted
```

If resolution fails:
```
[FAIL]  Could not resolve a work drive folder.
        Tried: $DAYZ_WORK_DRIVE, cached path, registry, DayZ Tools\Bin\WorkDrive\.
        Pass --path "C:\path\to\workdrive" to specify explicitly.
```

## Does NOT gate on `/dayz-preflight`

Per `.claude/skills/_shared/dayz-conventions.md`'s "abort-skill exception" precedent: this skill predates the preflight gate (preflight checks for P:\, this skill mounts it — chicken-and-egg). After running this, all other DayZ skills' preflight gate will pass naturally.

## Do not

- Don't try to mount on Linux/macOS/WSL — `subst` is Windows-only. The skill exits with a clear error.
- Don't assume the cached path is current after a DayZ Tools reinstall — clear the cache or use `--path` if it gets stale.
- Don't run as admin unless something else needs it. `subst` works fine in user mode.
