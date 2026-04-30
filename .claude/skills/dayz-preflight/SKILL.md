---
name: dayz-preflight
description: Verify the DayZ modding environment is ready (P:\ mounted, DayZ Tools installed, vanilla data unpacked, workshop deploy folder accessible). Run this before any other DayZ skill. Hard-fails if P:\ is not mounted; warns on the rest.
---

# /dayz-preflight

Verify the DayZ modding environment before doing any DayZ work. Halts with a clear error if `P:\` is not mounted (per `.claude/skills/_shared/dayz-conventions.md`); warns on optional checks so the user can decide whether to proceed.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it checks

| # | Check | Severity |
|---|---|---|
| 1 | `P:\` drive is mounted | **hard fail** — exit 1 |
| 2 | DayZ Tools installed (AddonBuilder.exe locatable) | warn |
| 3 | Vanilla DayZ data unpacked under `P:\` | warn |
| 4 | `P:\Mods\` is a directory junction to `<DayZ install>\!Workshop\` (not a regular folder, not missing, not dangling) | warn — build-pbo hard-fails on the same condition |

Exit code 0 = ready (or warnings only). Non-zero = hard environment issue, named in stderr.

## How paths are resolved

Paths are not blindly hard-coded. Resolution order, first hit wins:

| What | Order |
|---|---|
| **DayZ Tools install root** | 1. `DAYZ_TOOLS_PATH` env var → 2. Windows registry (`HKLM\SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ Tools` → `Path` value, plus the `HKLM` non-WOW6432 and `HKCU` siblings) → 3. Common Steam paths (`C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools`, then `C:\Program Files\…`). A candidate counts only if `Bin\AddonBuilder\AddonBuilder.exe` exists under it. |
| **Vanilla data root** | 1. `DAYZ_VANILLA_DATA_PATH` env var → 2. Canonical names on P:\: `P:\dz`, `P:\DZ`, `P:\dta`. A candidate counts only if it exists and is non-empty. |
| **`P:\` and `P:\Mods\`** | Fixed by DayZ engine convention — not configurable. |

To override either env var, set it in your shell or in the user/system environment before running any DayZ skill. Example (PowerShell): `$env:DAYZ_TOOLS_PATH = 'D:\Games\Steam\steamapps\common\DayZ Tools'`.

The `find_dayz_tools()` and `find_vanilla_data()` helper functions in `preflight.py` are reusable — future DayZ skills (e.g. `dayz-build-pbo`) should import them instead of re-implementing path discovery.

## How to run

```cmd
python .claude\skills\dayz-preflight\preflight.py
```

## When to run

- Before invoking any other DayZ skill.
- After a fresh clone of the repo.
- After a fresh boot of the workstation — `P:\` does not auto-mount; you have to open DayZ Tools and mount it (or use the Tools "Mount P drive" command) at the start of each session.

## Output

Plain text, one line per check:

```
DayZ preflight

[OK]    P:\ is mounted
[OK]    DayZ Tools found: C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools
[OK]    Vanilla data found: P:\dz
[OK]    Workshop deploy folder exists: P:\Mods

Preflight complete.
```

If `P:\` is not mounted:

```
DayZ preflight

[FAIL]  P:\ is NOT mounted
        Open DayZ Tools and mount the P drive (Tools menu > Mount P drive).
```

Exit 1, and downstream DayZ skills should refuse to run.

## Do not

- Don't try to mount `P:\` programmatically — it's a DayZ Tools function and assumes Tools is installed and configured. Surface a clear message and let the user mount it.
- Don't gate on the DayZ Tools / vanilla data / Workshop folder checks — they're warnings, not errors. The user may have a custom layout.
- Don't reintroduce hard-coded paths in other DayZ skills. Import `find_dayz_tools` / `find_vanilla_data` from this skill so resolution stays consistent (env var → registry → fallback).
