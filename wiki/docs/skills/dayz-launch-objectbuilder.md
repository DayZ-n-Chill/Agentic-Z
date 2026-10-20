---
name: dayz-launch-objectbuilder
---

## Overview

Opens DayZ Tools' Object Builder (the .p3d model editor) from the command line, optionally on a specific .p3d or inside a mod's P:\&lt;ModName&gt;\ folder, detached so the shell returns at once. Requires /dayz-setup-objectbuilder to have run once on the machine. Use when you need to inspect or edit a .p3d model, such as adding LODs, named selections or memory points.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-launch-objectbuilder

Open Object Builder without leaving the terminal. Optionally pre-loads a `.p3d`, or passes a mod's `P:\<ModName>\` folder so you start inside it.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Gates on `/dayz-preflight`.
2. Locates `ObjectBuilder.exe` via DayZ Tools.
3. Verifies the registry has been populated by `/dayz-setup-objectbuilder` — fails with a clear hint if not.
4. Resolves the open target:
   - `--file <path>` → opens that `.p3d` directly.
   - `--mod <ModName>` → passes `P:\<ModName>\` to Object Builder.
   - Neither → no argument; Object Builder opens its last-used file.
5. Spawns `ObjectBuilder.exe` with `DETACHED_PROCESS`, working directory `<DayZ Tools>\Bin\ObjectBuilder\`, so the shell returns immediately. The window may take a few seconds to appear.

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

[OK]    P:\ mounted
[OK]    DayZ Tools: ...
[OK]    Vanilla data: P:\dz
[OK]    P:\Mods junction valid

[OK]    ObjectBuilder.exe: ...\Bin\ObjectBuilder\ObjectBuilder.exe
[OK]    Registry configured
[INFO]  Opening: P:\MyMod\data\model.p3d

[OK]    Object Builder launched (PID 12345). The window may take a few seconds to appear.
```

## Flag rules

- `--file` and `--mod` are mutually exclusive (argparse rejects both together); pass one or neither.
- `--file` takes an absolute path, or a path relative to the project. Warns if the extension isn't `.p3d` (Object Builder may refuse it).
- `--mod` is just the mod name; the skill expands to `P:\<ModName>\`. Fails fast if the folder isn't there.

## Why detached

Running Object Builder under the parent shell would block the terminal until you close the editor. We spawn with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` so:

- Closing this terminal doesn't kill Object Builder.
- The skill exits immediately after the spawn.
- The PID is printed so you can find/kill it later if needed.

## Do not

- Don't run before `/dayz-setup-objectbuilder` on a fresh machine — the skill will tell you to run setup first.
- Don't pass a relative `--file` path unless you know the project root it resolves against (`CLAUDE_PROJECT_DIR`, else the working directory); absolute paths are safer.
- Don't spam-launch — Object Builder isn't designed to run multiple instances against the same file.
