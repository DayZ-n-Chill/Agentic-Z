---
name: dayz-launch-workbench
description: Open Enfusion Workbench (DayZ Tools' script + UI editor) from the CLI, optionally pointed at a specific mod's project file. Spawns detached with cwd=P:\ so vanilla data resolves. Default behavior loads the vanilla dayz.gproj shipped with DayZ Tools; --mod &lt;ModName&gt; loads the per-mod gproj scaffolded by /dayz-new-mod.
---

# /dayz-launch-workbench

Open Workbench without leaving the terminal. Default loads vanilla DayZ; `--mod &lt;ModName&gt;` loads the customized `dayz.gproj` that `/dayz-new-mod` writes into `workspace/&lt;ModName&gt;/workbench/`, so Workbench compiles and lints vanilla + your mod together.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Gates on `/dayz-preflight`.
2. Locates `workbenchApp.exe` via DayZ Tools (`Bin\Workbench\workbenchApp.exe`).
3. Resolves the project file:
   - `--mod &lt;ModName&gt;` → uses `P:\&lt;ModName&gt;\workbench\dayz.gproj` (the file scaffolded by `/dayz-new-mod`). Fails fast if the mod folder or gproj isn't there.
   - `--gproj &lt;path&gt;` → uses an explicit `.gproj` path (escape hatch for non-scaffolded layouts).
   - Neither → no project arg; Workbench loads the default `dayz.gproj` shipped next to `workbenchApp.exe`.
4. Spawns `workbenchApp.exe` with `cwd=P:\` (so the gproj's `Directory "./"` resolves to the work drive root) and `DETACHED_PROCESS` so the shell returns immediately.

## How to run

**Just open Workbench on vanilla:**
```cmd
python .claude\skills\dayz-launch-workbench\launch.py
```

**Open with a mod's project file (compiles vanilla + mod together):**
```cmd
python .claude\skills\dayz-launch-workbench\launch.py --mod MyMod
```
(Requires `P:\MyMod\workbench\dayz.gproj` to exist — created automatically by `/dayz-new-mod MyMod`.)

**Open with an arbitrary gproj:**
```cmd
python .claude\skills\dayz-launch-workbench\launch.py --gproj P:\Custom\path\to\my.gproj
```

## When to run

- After `/dayz-new-mod` to start writing scripts/UI for a fresh mod with full code completion against vanilla.
- Anytime you want to edit `.layout` files or browse vanilla scripts in their native IDE.
- When debugging script errors — Workbench's compiler surfaces the same errors the engine would hit at runtime.

## Output

```
DayZ Workbench launcher

[OK]    P:\ mounted
[OK]    DayZ Tools: ...
[OK]    Vanilla data: P:\dz
[OK]    P:\Mods junction valid

[OK]    workbenchApp.exe: ...\Bin\Workbench\workbenchApp.exe
[INFO]  Project: P:\MyMod\workbench\dayz.gproj
[OK]    Working directory: P:\

[OK]    Workbench launched (PID 12345). The window may take a few seconds to appear.
```

## Flag rules

- `--mod` and `--gproj` are mutually exclusive.
- `--mod` is just the mod name; the skill expands to `P:\&lt;ModName&gt;\workbench\dayz.gproj`. Fails fast if either the mod folder or the gproj is missing.
- `--gproj` accepts an absolute path (relative paths resolve against repo root). Warns if the extension isn't `.gproj`.

## Why cwd=`&lt;DayZ Tools&gt;\Bin\Workbench`

Workbench loads its support files (`dta\`, `platforms\`, `ToolAddons\`) and its bundled `dayz.gproj` relative to cwd, not relative to `workbenchApp.exe`. Launching from anywhere else (including `P:\`) triggers a "cannot find file dayz.gproj" error even when a valid project file is passed as an argument. We always launch with `cwd = &lt;DayZ Tools&gt;\Bin\Workbench\`. The project file we pass as an arg is then loaded as the active project, while the support files resolve from the install dir as Workbench expects.

Vanilla data paths inside the gproj (e.g. `DZ/Anims/cfg/...`, `gui/imagesets/...`) are resolved by Workbench relative to the gproj file's location, NOT cwd — so as long as your mod's `dayz.gproj` lives next to its sibling `&lt;ModName&gt;/` source tree on the work drive (the layout `/dayz-new-mod` produces), vanilla imports keep resolving via the `P:\` junction the engine and Workbench share.

## Why detached

Running Workbench under the parent shell would block the terminal until you close the editor. We spawn with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` so:

- Closing this terminal doesn't kill Workbench.
- The skill exits immediately after the spawn.
- The PID is printed so you can find/kill it later if needed.

## Do not

- Don't pass `--mod` for a mod that wasn't scaffolded by `/dayz-new-mod` — the workbench/dayz.gproj won't exist. Run `/dayz-new-mod &lt;ModName&gt;` first.
- Don't edit the workbench/dayz.gproj manually expecting `/dayz-new-mod` re-runs to preserve your changes — the scaffolder writes a fresh copy each time. If you need custom modules beyond the auto-injected `game`/`world`/`mission`, keep your edits in a side file or accept that re-running scaffolding will overwrite.
- Don't spam-launch — Workbench isn't designed to run multiple instances against the same project.
