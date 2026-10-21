---
name: dayz-launch-workbench
description: Opens Enfusion Workbench (DayZ Tools' script and UI editor) from the command line, detached, either on vanilla DayZ or on a mod's workbench/dayz.gproj so vanilla and mod scripts compile together. Use when you want to write or debug a mod's Enforce Script or .layout files with Workbench's compiler and code completion.
argument-hint: "[--mod <ModName> | --gproj <path>]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-launch-workbench

Open Workbench without leaving the terminal. Default loads vanilla DayZ; `--mod <ModName>` loads the customized `dayz.gproj` that `/dayz-new-mod` (or `/dayz-add-scaffold --piece workbench`) writes into `workspace/<ModName>/workbench/`, so Workbench compiles and lints vanilla + your mod together.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Gates on `/dayz-preflight`.
2. Locates `workbenchApp.exe` via DayZ Tools (`Bin\Workbench\workbenchApp.exe`).
3. Resolves the project file:
   - `--mod <ModName>` → uses `P:\<ModName>\workbench\dayz.gproj`. Fails fast if the mod folder or gproj isn't there; a missing gproj is added with `/dayz-add-scaffold <ModName> --piece workbench`.
   - `--gproj <path>` → uses an explicit `.gproj` path (escape hatch for non-scaffolded layouts).
   - Neither → no project arg; Workbench loads the default `dayz.gproj` shipped next to `workbenchApp.exe`.
4. Spawns `workbenchApp.exe` with `cwd=<DayZ Tools>\Bin\Workbench` (so Workbench's support files resolve; see "Why cwd" below), detached so the shell returns immediately.

## How to run

**Just open Workbench on vanilla:**
```cmd
python "<skill-dir>\launch.py"
```

**Open with a mod's project file (compiles vanilla + mod together):**
```cmd
python "<skill-dir>\launch.py" --mod MyMod
```
(Requires `P:\MyMod\workbench\dayz.gproj`, created by `/dayz-new-mod MyMod`. For an imported or older mod without it, run `/dayz-add-scaffold MyMod --piece workbench` first.)

**Open with an arbitrary gproj:**
```cmd
python "<skill-dir>\launch.py" --gproj P:\Custom\path\to\my.gproj
```

## When to run

- After `/dayz-new-mod` to start writing scripts/UI for a fresh mod with full code completion against vanilla.
- Anytime you want to edit `.layout` files or browse vanilla scripts in their native IDE.
- When debugging script errors — Workbench's compiler surfaces the same errors the engine would hit at runtime.

## Output

```
DayZ Workbench launcher

DayZ preflight

[OK]    P:\ is mounted
[OK]    DayZ Tools found: C:\...\steamapps\common\DayZ Tools
[OK]    Vanilla data found: P:\dz
[OK]    P:\Mods -> C:\...\steamapps\common\DayZ\!Workshop

Preflight complete.

[OK]    workbenchApp.exe: ...\Bin\Workbench\workbenchApp.exe
[INFO]  Project: P:\MyMod\workbench\dayz.gproj
[OK]    Working directory: ...\Bin\Workbench

[OK]    Workbench launched (PID 12345). The window may take a few seconds to appear.
```

## Flag rules

- `--mod` and `--gproj` are mutually exclusive (argparse rejects both together).
- `--mod` is just the mod name; the skill expands to `P:\<ModName>\workbench\dayz.gproj`. Fails fast if either the mod folder or the gproj is missing.
- `--gproj` accepts an absolute path; a relative path resolves against the project (`CLAUDE_PROJECT_DIR`, else the working directory). Warns if the extension isn't `.gproj`.

## Why cwd=`<DayZ Tools>\Bin\Workbench`

Workbench resolves its own support files (`dta\`, `platforms\`, `ToolAddons\`) from the working directory, and the scaffolded `dayz.gproj` mounts `P:/` and `P:/<ModName>/` explicitly, so vanilla and mod sources resolve no matter where the gproj lives.

## Why detached

The editor is spawned detached (shared `DETACH_FLAGS` in `_shared/skill_helpers.py`) so the terminal returns at once and closing it doesn't kill Workbench; the printed PID identifies the process.

## Editing the gproj

`workbench/dayz.gproj` is yours to edit (for example to add modules beyond the injected `game`/`world`/`mission` paths). No skill rewrites it: `/dayz-new-mod` refuses to run on an existing mod folder and `/dayz-add-scaffold` never overwrites a file. To regenerate it, delete it and run `/dayz-add-scaffold <ModName> --piece workbench`.

## Do not

- Don't pass `--mod` for a mod without `workbench/dayz.gproj`; add it first with `/dayz-add-scaffold <ModName> --piece workbench`.
- Don't spam-launch; Workbench isn't designed to run multiple instances against the same project.
