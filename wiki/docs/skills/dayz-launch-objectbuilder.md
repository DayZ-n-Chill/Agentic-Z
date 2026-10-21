---
name: dayz-launch-objectbuilder
---

## Overview

Opens DayZ Tools' Object Builder (the .p3d model editor), optionally on a specific .p3d or a mod's P:\ folder. Needs /dayz-setup-objectbuilder run once. Use when you need to inspect or edit a .p3d model, such as adding LODs, named selections or memory points.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-launch-objectbuilder

Open Object Builder without leaving the terminal. Optionally pre-loads a `.p3d`, or passes a mod's `P:\<ModName>\` folder so you start inside it.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Gates on `/dayz-preflight` (as `/dayz-launch-workbench` does), so an unmounted `P:\` fails with preflight's fix before `--mod` looks under it.
2. Resolves the open target:
   - `--file <path>`: that `.p3d`. Fails if the path is missing; warns if the extension isn't `.p3d`.
   - `--mod <ModName>`: `P:\<ModName>\`. Fails if the folder is missing.
   - Neither: no argument; Object Builder opens its last-used file.
3. Locates `ObjectBuilder.exe` via DayZ Tools.
4. Verifies the registry has been populated by `/dayz-setup-objectbuilder` (with that skill's own check, loaded from its `setup.py`), and fails with a hint if not.
5. Spawns `ObjectBuilder.exe` detached, with working directory `<DayZ Tools>\Bin\ObjectBuilder\`, so the shell returns immediately. The window may take a few seconds to appear.

## How to run

**Just open the editor:**
```cmd
python "<skill-dir>\launch.py"
```

**Open a specific .p3d:**
```cmd
python "<skill-dir>\launch.py" --file P:\MyMod\data\model.p3d
```

**Start inside a mod folder:**
```cmd
python "<skill-dir>\launch.py" --mod MyMod
```
(Requires `P:\MyMod\` to exist — typically created by `/dayz-new-mod`.)

## When to run

- Anytime you need to inspect or edit a `.p3d` model.
- After `/dayz-new-mod` produced a scaffold and you want to drop a model into `data/`.
- Before adding LODs, named selections, or memory points to a custom asset.

## Output

```
DayZ Object Builder launcher

DayZ preflight

[OK]    P:\ is mounted
[OK]    DayZ Tools found: C:\...\steamapps\common\DayZ Tools
[OK]    Vanilla data found: P:\dz
[OK]    P:\Mods -> C:\...\steamapps\common\DayZ\!Workshop

Preflight complete.

[OK]    ObjectBuilder.exe: ...\Bin\ObjectBuilder\ObjectBuilder.exe
[OK]    Registry configured
[INFO]  Opening: P:\MyMod\data\model.p3d

[OK]    Object Builder launched (PID 12345). The window may take a few seconds to appear.
```

## Flag rules

- `--file` and `--mod` are mutually exclusive (argparse rejects both together); pass one or neither.
- `--file` takes an absolute path, or a path relative to the project. Warns if the extension isn't `.p3d` (Object Builder may refuse it).
- `--mod` is just the mod name; the skill expands to `P:\<ModName>\`. Fails, right after preflight, if the folder isn't there.

## Why detached

The editor is spawned detached (shared `DETACH_FLAGS` in `_shared/skill_helpers.py`) so the terminal returns at once and closing it doesn't kill Object Builder; the printed PID identifies the process.

## Do not

- Don't run before `/dayz-setup-objectbuilder` on a fresh machine — the skill will tell you to run setup first.
- Don't pass a relative `--file` path unless you know the project root it resolves against (`CLAUDE_PROJECT_DIR`, else the working directory); absolute paths are safer.
- Don't spam-launch — Object Builder isn't designed to run multiple instances against the same file.
