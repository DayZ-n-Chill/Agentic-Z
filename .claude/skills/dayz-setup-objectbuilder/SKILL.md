---
name: dayz-setup-objectbuilder
description: Configure Object Builder (DayZ Tools' .p3d model editor) on a fresh machine. Imports the default registry settings shipped with DayZ Tools so Object Builder opens with sane window layouts and defaults instead of an empty config. One-time per machine; idempotent. Run before /dayz-launch-objectbuilder on a clean install.
---

<!-- skill-dir-note -->
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
5. If empty: runs `reg import` on the default `.reg` file.
6. Verifies the import landed.

## How to run

**First time (or after a fresh DayZ Tools reinstall):**
```cmd
python "<skill-dir>\setup.py"
```

**Force re-import (resets Object Builder to factory defaults — wipes any custom panel layout you've saved):**
```cmd
python "<skill-dir>\setup.py" --force
```

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
[OK]    Buldozer.exe: ...\Bin\Buldozer\Buldozer.exe  (used for 3D preview)
[INFO]  Registry empty — importing defaults.
[INFO]  Running: reg import ...\ObjectBuilder_defaultSettings.reg
[OK]    Registry imported successfully.

[OK]    Object Builder is configured. Launch with: /dayz-launch-objectbuilder
```

On an already-configured machine, output stops at `[OK] Registry already configured` and exits 0.

## Why a registry import (and why it's safe)

Object Builder is an old MFC-based Windows tool — its config lives entirely under `HKEY_CURRENT_USER\Software\Bohemia Interactive\DayZ Tools\Object Builder`. The shipped `.reg` file writes window/panel/toolbar defaults into that tree. It's **HKCU-only**, so:

- No Administrator elevation needed.
- Only affects the current Windows user.
- Reversible via `--force` re-import or by deleting the registry tree.

## Do not

- Don't run this without `/dayz-preflight` clean — the skill enforces it.
- Don't run as Administrator unless the non-elevated import fails. The `.reg` writes to HKCU, not HKLM.
- Don't edit the `.reg` file in DayZ Tools install — Steam will overwrite it on update. If you want custom defaults, save a layout from inside Object Builder; it persists in the same registry tree but in `MainFrame-*` subkeys you don't need to touch directly.
