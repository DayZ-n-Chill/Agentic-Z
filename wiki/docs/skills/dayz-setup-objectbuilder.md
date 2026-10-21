---
name: dayz-setup-objectbuilder
---

## Overview

Configures Object Builder (DayZ Tools' .p3d editor) by importing the default registry settings DayZ Tools ships and setting four preferred view/renderer flags under HKCU. Use when Object Builder is opened for the first time on a machine, after a DayZ Tools reinstall, or when it opens with broken panel layouts.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-setup-objectbuilder

One-time configuration of Object Builder. Bohemia ships a `.reg` file with sensible defaults (window layouts, panel positions, render flags) but doesn't auto-import it — without this step, Object Builder runs from a blank `HKCU\Software\Bohemia Interactive\DayZ Tools\Object Builder` tree and looks broken on first open.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Gates on `/dayz-preflight`.
2. Locates DayZ Tools via the shared `find_dayz_tools()` resolver.
3. Verifies these exist:
   - `Bin\ObjectBuilder\ObjectBuilder.exe`
   - `Bin\ObjectBuilder\ObjectBuilder_defaultSettings.reg`
4. Checks `HKCU\Software\Bohemia Interactive\DayZ Tools\Object Builder\CConfig` for an existing config.
5. If empty (or with `--force`, after confirmation): checks that every key the `.reg` touches is under `HKEY_CURRENT_USER` (refuses otherwise, before touching the registry). On a forced reset it then runs `reg export` on the existing Object Builder key to `.claude/local-memory/objectbuilder-backup-<YYYYMMDD-HHMMSS>.reg` in the project and prints that path (the reset is abandoned if the export fails), and deletes the key with `reg delete ... /f` (stops if that fails). Finally it runs `reg import` on the `.reg` and verifies the key now exists.
6. On every run, sets four preferred flags under `CConfig`, writing only the ones not already on: View background LOD, background LOD in the 3D preview, background LOD in the UV editor (all `"1"`), and Direct3D renderer by default (`"On"`).

## How to run

**First time (or after a fresh DayZ Tools reinstall):**
```cmd
python "<skill-dir>\setup.py"
```

**Force re-import (resets Object Builder to factory defaults — wipes any custom panel layout you've saved):**
```cmd
python "<skill-dir>\setup.py" --force
```

On an already-configured machine `--force` asks `[y/N]`, backs up the current settings, deletes the whole Object Builder key (including saved `MainFrame-*` toolbar layouts, `HistoryPaths` recent files, and any value the shipped `.reg` doesn't set), then imports the defaults into the empty tree. To undo the reset, run `reg import` on the backup file it printed. Without a terminal (an agent's Bash call) it refuses unless `--yes` is also given, so get the user's go-ahead first and then run `--force --yes`.

Exits 1 if DayZ Tools, `ObjectBuilder.exe` or the `.reg` is missing, the `.reg` touches a key outside `HKEY_CURRENT_USER`, the reset is not confirmed, the backup export or the key delete fails, or the keys are still missing after import; a failed `reg import` returns its own exit code.

## When to run

- After installing DayZ Tools for the first time on a machine.
- After reinstalling DayZ Tools (Steam may have wiped the registry tree).
- If Object Builder opens with floating panels everywhere and weird defaults.

## Output

```
DayZ Object Builder setup

[OK]    DayZ Tools: C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools
[OK]    ObjectBuilder.exe: ...\Bin\ObjectBuilder\ObjectBuilder.exe
[OK]    Default settings file: ObjectBuilder_defaultSettings.reg
[INFO]  Registry empty — importing defaults.
[INFO]  Running: reg import ...\ObjectBuilder_defaultSettings.reg
[OK]    Registry imported successfully.

[INFO]  Applying preferred Object Builder defaults:
[INFO]  View > Background LOD: turned on
[OK]    Background LOD shown in 3D preview pane: already on
...
[INFO]  1 of 4 preferences changed.

[OK]    Object Builder is ready. Launch with: /dayz-launch-objectbuilder
```

On an already-configured machine the import is skipped (`[OK] Registry already configured ...`), but the preference step still runs and turns on any of the four flags that were switched off in Object Builder since the last run.

## Why a registry import (and why it's safe)

Object Builder is an old MFC-based Windows tool — its config lives entirely under `HKEY_CURRENT_USER\Software\Bohemia Interactive\DayZ Tools\Object Builder`. The shipped `.reg` file writes window/panel/toolbar defaults into that tree. It's **HKCU-only** (the script verifies this before every import), so:

- No Administrator elevation needed.
- Only affects the current Windows user.
- Reversible: `--force` saves a backup `.reg` before resetting, and you can `reg import` it to get your layout back. Note that the four preferred flags are re-applied on every run, so turning one off in Object Builder only lasts until this skill runs again.

## Do not

- Don't run as Administrator unless the non-elevated import fails. The `.reg` writes to HKCU, not HKLM.
- Don't edit the `.reg` file in DayZ Tools install — Steam will overwrite it on update. If you want custom defaults, save a layout from inside Object Builder; it persists in the same registry tree but in `MainFrame-*` subkeys you don't need to touch directly.
