# DayZ core skills in detail

How the four core skills work step by step: `/dayz-preflight`, `/dayz-new-mod`, `/dayz-build-pbo` and `/dayz-launch-test`, and where their files live. The workflow, prerequisites, path overrides and troubleshooting are in [`dayz-modding.md`](dayz-modding.md).

## `/dayz-preflight`

Verifies the modding environment before any other DayZ skill runs. **Every other DayZ skill that does work calls this first** and propagates non-zero exit, except the documented exceptions listed in [`dayz-modding.md`](dayz-modding.md) (with reasons in `skills/_shared/dayz-conventions.md`).

| Check | Severity |
|---|---|
| `P:\` mounted | **hard fail** — exit 1 |
| `AddonBuilder.exe` locatable (env / registry / Steam paths) | warn |
| DayZ Diag (`DayZDiag_x64.exe`, which `/dayz-launch-test` needs) locatable | warn |
| DayZ Server (`DayZServer_x64.exe`, which `/dayz-add-server` needs) locatable | warn |
| Vanilla data on `P:\` (looks for `P:\dz`, which also matches `P:\DZ` because Windows paths ignore case) | warn |
| Vanilla scripts at `P:\scripts` (linting and vanilla search need them) | warn |
| `P:\Mods\` exists or can be created | warn (creates if missing) |

Hard-fail message tells you to mount `P:\` via DayZ Tools.

Path resolution order for DayZ Tools:

1. `$DAYZ_TOOLS_PATH` env var
2. Windows registry (HKLM/HKCU under `Bohemia Interactive\DayZ Tools`)
3. Steam libraries: the Steam root from the registry (`HKCU\Software\Valve\Steam` SteamPath, `HKLM\SOFTWARE\WOW6432Node\Valve\Steam` InstallPath), then both defaults (`C:\Program Files (x86)\Steam`, `C:\Program Files\Steam`), which are always checked, plus every library listed in `steamapps\libraryfolders.vdf`, each checked for `steamapps\common\DayZ Tools`

Path resolution order for vanilla data:

1. `$DAYZ_VANILLA_DATA_PATH` env var
2. `P:\dz` (which also matches `P:\DZ`, because Windows paths ignore case)

Helper functions `find_dayz_tools()` and `find_vanilla_data()` are exported from `preflight.py` — every other DayZ skill imports them rather than re-implementing path discovery.

## `/dayz-new-mod`

Scaffolds a new mod project under `workspace/<ModName>/` and creates the `P:\<ModName>\` junction so AddonBuilder and the engine can find it.

```cmd
python skills\dayz-new-mod\new_mod.py <ModName> [--author "YourHandle"]
```

**Argument rules:**

- `<ModName>` — folder name and `CfgPatches` class name. **Must start with a letter; letters, digits, underscores only; max 64 chars.** Hyphens are not allowed because the name doubles as a C-style identifier in `config.cpp` and the engine would reject the parse.
- `--author` — written into `config.cpp` as the mod author. Cached on first run. **Resolution order:**
  1. `--author` flag (also writes to cache)
  2. Cached value at `.claude/local-memory/dayz-author.txt`
  3. Interactive prompt if stdin is a TTY (writes to cache)
  4. Hard fail with instructions

**Files created:**

```
workspace/<ModName>/
├── config.cpp                 # CfgPatches + CfgMods stub registering the script modules
├── $PBOPREFIX$                # contains: <ModName>
├── README.md                  # light onboarding notes
├── scripts/
│   ├── 3_Game/.gitkeep        # Enforce Script — base game logic
│   ├── 4_World/.gitkeep       # Enforce Script — world-level logic
│   └── 5_Mission/.gitkeep     # Enforce Script — mission/server scripts
├── data/.gitkeep              # models (.p3d), textures (.paa), materials (.rvmat)
├── gui/.gitkeep               # UI layouts (.layout) and controllers
└── workbench/                 # dayz.gproj (mod paths + FileSystem mounts) + DayZSetting.xml for /dayz-launch-workbench --mod; README placeholder if DayZ Tools is missing
```

Plus a directory junction:

```
P:\<ModName>\  ->  workspace/<ModName>/   (symlink, falls back to junction on Windows)
```

**Refuse rules:**

- Preflight returns non-zero (typically `P:\` not mounted).
- Name fails the pattern.
- `workspace/<ModName>/` already exists.
- `P:\<ModName>\` exists as a real folder, or as a link pointing somewhere other than `workspace/<ModName>/`.
- No author handle available and stdin not a TTY.

**Stale-junction auto-clean:** if `P:\<ModName>\` exists as a junction whose target is the about-to-be-scaffolded `workspace/<ModName>/` (typically because the workspace was deleted but the junction wasn't), the skill removes the stale link and proceeds. Common cleanup case after `rm -rf workspace/<ModName>/`.

## `/dayz-build-pbo`

Packs the mod into a deployable `.pbo` via AddonBuilder.

```cmd
python skills\dayz-build-pbo\build.py <ModName> [--clean]
```

**Steps performed:**

1. Validate `<ModName>`.
2. Preflight gate.
3. Verify `workspace/<ModName>/config.cpp` and `workspace/<ModName>/$PBOPREFIX$` exist, and that `$PBOPREFIX$` contains exactly `<ModName>`.
4. `/dayz-lint` gate, in two stages run by the one command. The setup stage checks what stops a mod loading: `config.cpp` syntax, `CfgPatches`, `requiredAddons`, `$PBOPREFIX$`, script modules and missing files. The code stage then runs the script validator in `scripts/tools/dayz-script-validator/` over the mod's Enforce Script, `.layout`, `config.cpp`, `inputs.xml` and `.rvmat` files, reading the vanilla scripts on `P:\scripts\` when they are there. Any error from either stage refuses the build; warnings are printed. Each finding names the specialist that owns it; a `.layout` rule finding goes to `dayz-ui-specialist`. A code rule that could not judge the mod is listed as `not checked`; for a mod that depends on another mod, run `/dayz-lint <ModName> --external-scripts <folder>` yourself to get the class-reference verdict. The code stage is a set of rules, not a compiler, so other compile errors still surface in `/dayz-gate ingame`.
5. Verify the `P:\Mods\` junction is valid (hard fail).
6. Verify `P:\<ModName>\` is a link pointing at `workspace/<ModName>/`.
7. Resolve `AddonBuilder.exe` via `find_dayz_tools()`.
8. Ownership-marker gate: refuse to build into a `P:\Mods\@<ModName>\` that Agentic-Z did not create. With `--clean`, also refuse while `Addons\` holds PBOs other than `<ModName>.pbo`, or any `.bisign` file.
9. Ensure `P:\Mods\@<ModName>\Addons\` exists, writing the marker when this run created `@<ModName>`, and remove a `P:\temp\<ModName>\` left by an earlier build (hard fail if it cannot be emptied, because AddonBuilder would pack the stale files).
10. Copy the mod to `P:\temp\_stage\<ModName>\` without the files `exclude.lst` names, then invoke `AddonBuilder.exe P:\temp\_stage\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill>\include.lst [-clear]`. It passes no `-exclude=`, because AddonBuilder 1.0.240639 crashes on that flag. AddonBuilder's stdout/stderr stream live so you see binarization progress and config errors as they happen.
11. Read the last `[ResultCode]` in DayZ Tools' `Bin\Logs\AddonBuilder.rpt`: AddonBuilder exits 0 when CfgConvert or binarize fails, so a result other than 0 fails the build.
12. Verify `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and was refreshed by this build.
13. Content check: compare the PBO's entry table with the staged source. A staged `.c` or `.p3d` missing from the PBO, a PBO with no config, or a wrong prefix fails the build.
14. Remove the temp dir on success (kept on failure for debugging).

**`--clean` flag** passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Useful after large refactors or when chasing stale-asset bugs. Refused while `Addons\` holds any `.pbo` other than `<ModName>.pbo` (deployed payload from `/dayz-deploy-pbo`) or any `.bisign` file (copied in by `/dayz-deploy-pbo` or made by hand; AddonBuilder never writes one), since `-clear` would wipe them; build without `--clean`, or move them aside first and re-deploy or re-sign afterwards.

Default output is binarized. A `--no-binarize` flag is not exposed yet — easy to add later when iteration speed becomes a concern.

## `/dayz-launch-test`

Spins up a local development environment to test one or more built mods. **Always launches the server first**, then the client connecting to it — DayZ has no offline / single-player mode for mod testing.

```cmd
python skills\dayz-launch-test\launch.py <ModName> [<ModName2> ...] [--server-only <ModName>]... [--server <instance>] [--port N] [--dry-run]
```

**Steps performed:**

1. Preflight gate.
2. Refuse if `workspace/_server/` still exists. That old layout is no longer supported; delete the folder by hand.
3. For each mod, verify `P:\Mods\@<ModName>\Addons\` holds at least one `.pbo` (any name, so mods with several PBOs work). Fails with a hint to run `/dayz-build-pbo` if the folder is missing or has no `.pbo`.
4. Refuse when a mod's non-vanilla `requiredAddons` are not provided by a mod named before it.
5. Resolve `DayZDiag_x64.exe` (env `DAYZ_DIAG_PATH` → DayZ game install → Steam fallbacks). **Hard-fail if missing.** Both server and client run from the same diag binary.
6. **First-run only:** the instance must have been added via `/dayz-add-server <instance>`, which copies the mission template from DayZ Server's `mpmissions/<template>/` into `.server/<instance>/mission/`. After this initial copy, DayZ Server can be uninstalled.
7. Verify `.server/<instance>/serverDZ.cfg` and `.server/<instance>/mission/` exist for the selected instance (default `chernarus`). The skill never edits the cfg: if it lacks an active `allowFilePatching = 1;` (missing, commented out or another value) or a `template = "...";` line, or the `<template>/` junction to `mission/` is missing, the launch is refused with a hint to run `/dayz-add-server <instance>`, which sets these up.
8. Refuse if the port is already in use, then refuse if Steam is not running (the diag client needs it); neither is checked on `--dry-run`. Then spawn the server: `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/Profiles -mission=<instance>/<template> -mod=P:\Mods\@Mod1;P:\Mods\@Mod2 [-serverMod=P:\Mods\@ServerOnly1;...] -filePatching -port=<port>`. `-mission=` is the absolute `.server/<instance>/<template>` path (for example `dayzOffline.chernarusplus`), the junction to `mission/` that `/dayz-add-server` creates; without a path named after the template the client connects but never spawns.
9. Wait (up to 180 seconds) until the server has bound its UDP port.
10. Spawn the client: `DayZDiag_x64.exe -profiles=.server/!ClientDiagLogs -mod=P:\Mods\@Mod1;P:\Mods\@Mod2 -connect=127.0.0.1 -port=<port> -filePatching -window -x=<W> -y=<H>`. Windowed mode and resolution come from `.claude/local-memory/dayz-client-display.json`, created with `{"windowed": true, "width": 1920, "height": 1080}` on the first non-dry-run launch; edit it to change them (invalid contents fall back to the defaults). **The client must be DayZ Diag, not retail.** Retail `DayZ_x64.exe` blocks past the loading screen with `-filePatching`. The client `-profiles=` points at the shared top-level `.server/!ClientDiagLogs/` (vanilla naming convention; client diag artifacts don't need per-instance isolation).
11. Print both PIDs and exit. **You close both windows manually** to stop them. (Or run `/dayz-stop-test`.)

**`--server <instance>`** selects which instance to test on. Defaults to `chernarus`. The instance must have been added via `/dayz-add-server` first.

**`--server-only <ModName>`** takes one name; repeat the flag for each server-only mod (`--server-only SrvA --server-only SrvB`). Name every shared mod before the options: a mod name after an option exits 2 with `unexpected arguments`. It loads these mods on the server via `-serverMod=` and never on the client, for server-side mods that exit when loaded client-side. Their PBOs must exist. A mod cannot be named both as shared and as server-only.

**`--dry-run`** prints the resolved server and client commands without launching. Useful for verifying paths and arg construction.

**`--port`** overrides the default `2302`.

**`-filePatching`** is set on both server and client so the engine reads raw `.cpp` / `.c` files from the `P:\<ModName>\` junction instead of only the binarized PBO. This lets you iterate on Enforce Script and configs without rebuilding the PBO every change. The PBO must still exist (the engine looks up the addon by name there) but the actual content can come from source.

## Where everything lives

```
<repo>/
├── skills/
│   ├── dayz-preflight/
│   │   ├── SKILL.md
│   │   └── preflight.py            # exports find_dayz_tools, find_dayz_game,
│   │                               # find_dayz_diag, find_dayz_server,
│   │                               # find_vanilla_data
│   ├── dayz-new-mod/
│   │   ├── SKILL.md
│   │   └── new_mod.py
│   ├── dayz-build-pbo/
│   │   ├── SKILL.md
│   │   └── build.py
│   ├── dayz-launch-test/
│   │   ├── SKILL.md
│   │   └── launch.py
│   └── _shared/
│       ├── dayz-conventions.md      # L2 core rules every DayZ skill follows
│       └── conventions/             # L2 topic rules (config, assets, scripts, ui, server)
├── .claude/
│   └── local-memory/                # gitignored, per-clone
│       ├── dayz-author.txt
│       ├── dayz-current-project.txt
│       └── dayz-init-state.json
├── workspace/
│   └── <ModName>/                   # your mod source (created by /dayz-new-mod)
├── .server/
│   └── <instance>/                  # local test server (created by /dayz-add-server)
└── docs/
    ├── dayz-modding.md              # workflow, prerequisites, troubleshooting
    └── dayz-core-skills.md          # this file
```

On `P:\`:

```
P:\
├── <ModName>\           # junction → <repo>\workspace\<ModName>\  (created by /dayz-new-mod)
├── Mods\@<ModName>\Addons\<ModName>.pbo    # built artifact (created by /dayz-build-pbo)
├── temp\<ModName>\      # AddonBuilder temp (created and cleaned by /dayz-build-pbo)
└── dz\                  # vanilla DayZ data (you extract this once via DayZ Tools)
```

