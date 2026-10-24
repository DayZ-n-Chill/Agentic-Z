# DayZ Modding

Agentic-Z ships with a complete DayZ modding workflow covering the full mod lifecycle — from "fresh checkout" to "playing my mod on a local server."

## Front door: `/dayz-init`

The fastest path is the wizard:

```
/dayz-init
```

First run: environment check (mounting `P:\` itself if needed), setup questions (new mod or import, mod name, test map, build and launch toggles, an optional spec), then it shows and runs the resulting plan. Every run after: a status hub for the active mod (PBO age, test servers, whether DayZ Diag is running, search status) with actions to build and launch, lint the mod, gate the build, gate in game, show mod health, stop DayZ Diag, show the server log, open Workbench or Object Builder, review the mod, add a test server, set up search (on request), or set up or switch to another mod.

Its state is per clone, in `.claude/local-memory/` (gitignored): `dayz-current-project.txt` holds the project root the other DayZ skills read, and `dayz-init-state.json` holds the active mod.

The wizard wraps the lower-level skills below, never replaces them. Use it for normal flow; reach for the individual skills when you need surgical control.

## Underlying skills (the wizard orchestrates these)

1. **`/dayz-preflight`** — verifies your DayZ modding environment is ready.
2. **`/dayz-new-mod`** / **`/dayz-import-mod`** — scaffold a new mod project (or symlink an existing one) with the required `P:\<ModName>\` junction.
3. **`/dayz-add-scaffold`** — fill in missing scaffold pieces (config.cpp stub, gproj, etc.) on a mod folder that lacks them; `--piece junction` repairs a missing `P:\<ModName>\` link.
4. **`/dayz-add-server`** — sets up a test server instance under `.server/<instance>/`: copies the mission template, creates per-instance `serverDZ.cfg` + `Profiles/` (server `-profiles=` dir), and ensures the shared `.server/!ClientDiagLogs/` (client `-profiles=` dir) exists. One-time per instance. Multiple variants of the same map allowed.
5. **`/dayz-build-pbo`** — packs the mod into a deployable `.pbo` via DayZ Tools' AddonBuilder.
6. **`/dayz-launch-test`** — spins up a local DayZ server with your mod loaded on the chosen instance, then connects the client. Run-only; refuses if the instance hasn't been added.

   Counterpart: **`/dayz-stop-test`** — force-kills any running DayZDiag_x64.exe processes so you can stop a session without hunting down windows. Doesn't gate on preflight (emergency escape hatch).
7. **`/dayz-cot-bootstrap`** — two-pass workflow that grants COT (Community-Online-Tools) admin perms on a fresh test instance. Auto-prepends @CF + @Community-Online-Tools, launches, waits for COT to write the per-player JSON, kills the session, edits the perm files, relaunches.
8. **`/dayz-clean-workspace`** — DayZ-only cleanup. Removes scaffolds and their deployed artifacts (workspace folders, `P:\<ModName>\` junctions that target our workspace, `P:\Mods\@<ModName>\` deploy dirs). Match-on-scaffold rule keeps your subscribed mods safe. `--include-server` also removes `.server/`.

For a repo-wide wipe across every domain (pre-push reset), use the general **`/clean-repo`** skill — it orchestrates each `<domain>-clean-workspace` cleanup in turn.

Most skills gate on `/dayz-preflight` first per the L2 convention `.claude/skills/_shared/dayz-conventions.md`. Documented exceptions, each with its reason in that file (Environment section):

- `/dayz-stop-test` (emergency stop that has to work when the environment is half-broken).
- `/dayz-scope-mod` and `/dayz-record-correction` (they edit settings or rule files, not DayZ content).
- `/dayz-init` (the wizard runs preflight inside its own steps).
- `/dayz-workdrive` (it mounts the `P:\` that preflight checks).
- `/dayz-search-download` (it only downloads a prebuilt index into `~/.claude/`).
- `/dayz-ask` (it only reads vanilla files and checks that `P:\` is mounted itself).
- `/dayz-preflight` (the gate itself).
- `/dayz-gate` (it gates through `/dayz-build-pbo` and `/dayz-launch-test`, which both gate on preflight).
- `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe` and `/dayz-layout-preview` (they only read files and write a report).
- `/dayz-upgrade-guard` (reads files and writes a report; snapshots go under `~/.claude/dayz-upgrade-guard/`).
- `/dayz-release-pack` and `/dayz-server-kit` (they only read the mod's own files and write texts or a zip under `output/`).
- `/dayz-health` and `/dayz-logwatch` (they only read gate results and logs).
- `/dayz-route` (it only classifies the text of a request).
- `/dayz-statusline` (it only edits a settings file).

Reference-only skills such as `/dayz-particles` run no scripts, so they have no gate.

---

## Prerequisites

You need a Windows machine with:

| Requirement | How to get it | Why |
|---|---|---|
| **DayZ** (the game) | Steam — buy it | The client (`DayZ_x64.exe`) you'll use to test mods. |
| **DayZ Tools** | Steam → Library → Tools (free) | AddonBuilder, Binarize, P-drive mounting. |
| **DayZ Diag** | Comes with DayZ — `DayZDiag_x64.exe` lives next to `DayZ_x64.exe` in your DayZ install dir | The diagnostic build that allows `-filePatching` to function. Used for **both** client and server in `/dayz-launch-test`. Retail binaries block past the loading screen with filePatching on. |
| **`P:\` drive mounted** | Open DayZ Tools → mount the P drive, **OR** run `python .claude\skills\dayz-workdrive\mount.py` (auto-resolves the work drive from DayZ Tools' `settings.ini`) | DayZ Tools and the engine both read from `P:\`. Preflight hard-fails without it. P:\ does not auto-mount; mount it at the start of each session. |
| **`P:\Mods\` junction** | One-time: `cmd /c mklink /J P:\Mods "<DayZ install>\!Workshop"` | The DayZ engine and Launcher load mods from `<DayZ install>\!Workshop\`. The `P:\Mods\` junction lets builds deploy via `P:\Mods\@<ModName>\Addons\<ModName>.pbo` and actually land where the engine reads. Build-pbo hard-fails if this junction is missing or points at a regular folder. |
| **Vanilla DayZ data on `P:\`** | DayZ Tools → "Extract Game Data" | Configs in your mod inherit from base classes (`ItemBase`, `Inventory_Base`, etc.) which only exist if vanilla PBOs are unpacked. |
| **Python 3.10+** on `PATH` | python.org | The skills are Python scripts. |
| **Voyage AI API key** *(optional, only for RAG)* | Sign up at [dash.voyageai.com](https://dash.voyageai.com), add `VOYAGE_API_KEY=pa-…` to `.env` at the repo root | Powers `/dayz-search-index` and the `dayz-rag` MCP server. Enables semantic search ("how does vanilla handle X?") over the indexed source. Embeddings via `voyage-code-3` (code-tuned, 1024-dim), stored in LanceDB under `~/.claude/dayz-search-index/`. The last full source build (August 2026, before windowing) embedded about 66M tokens; the current indexer makes about 62,000 chunks, and its local estimate of about 96M tokens runs high. Without it, agents fall back to `Grep` on the documented vanilla paths — fully functional, just less smart. **Shortcut:** `/dayz-search-download` pulls a prebuilt index from GitHub releases with no embedding cost; queries still need the key. |

---

## Quick start

From a fresh clone:

```cmd
git clone <this-repo> my-dayz-mod
cd my-dayz-mod
python .claude\skills\sync-skills\sync.py

:: Optional but recommended — pull the prebuilt vector index from GitHub
:: releases instead of building it locally with /dayz-search-index:
python .claude\skills\dayz-search-download\download.py
```

Then, every time you start a modding session:

```cmd
:: 1. Verify environment (P:\ mounted, Tools installed, vanilla data extracted)
python .claude\skills\dayz-preflight\preflight.py

:: 2. Scaffold a new mod (only the first time per mod)
python .claude\skills\dayz-new-mod\new_mod.py MyMod --author "MyHandle"

:: 3. Set up a test server instance (one-time per instance, copies mission template,
::    creates per-instance serverDZ.cfg + profile dirs)
python .claude\skills\dayz-add-server\add_server.py chernarus

:: 4. Edit your mod under workspace\MyMod\ — see Mod project layout below

:: 5. Build the PBO
python .claude\skills\dayz-build-pbo\build.py MyMod

:: 6. Launch local server + client with your mod loaded on the chosen map
python .claude\skills\dayz-launch-test\launch.py MyMod --server chernarus
```

Inside Claude Code, Codex, or Gemini CLI, the same commands are available as slash commands: `/dayz-preflight`, `/dayz-new-mod`, etc.

### Without the agent: `scripts\*\*.bat`

Most slash-command skills have a matching `.bat` wrapper: DayZ workflow skills in `scripts\dayz\`, one-time setup skills in `scripts\setup\`, repo maintenance in `scripts\dev\`. Each is a thin pass-through to the underlying skill's Python script with all arguments forwarded. Use these from Explorer or a plain terminal when you don't want to spin up an agent for a one-line action.

Bat names usually drop the `dayz-` prefix. A few are shortened or reordered further: `workbench.bat` (/dayz-launch-workbench), `objectbuilder.bat` (/dayz-launch-objectbuilder), `types-edit.bat` (/dayz-edit-types), `types-split.bat` (/dayz-split-types) and `status.bat` (the /dayz-init status hub). Examples:

```text
scripts\setup\preflight.bat             -> /dayz-preflight
scripts\setup\workdrive.bat             -> /dayz-workdrive
scripts\dayz\new-mod.bat MyMod          -> /dayz-new-mod MyMod
scripts\dayz\build-pbo.bat MyMod        -> /dayz-build-pbo MyMod
scripts\dayz\launch-test.bat MyMod      -> /dayz-launch-test MyMod
scripts\dayz\workbench.bat --mod MyMod  -> /dayz-launch-workbench --mod MyMod
scripts\dayz\stop-test.bat              -> /dayz-stop-test
scripts\dayz\scope-mod.bat MyMod        -> /dayz-scope-mod MyMod
scripts\dev\clean-repo.bat --yes        -> /clean-repo --yes
```

For full per-skill argument detail, see the skill's `SKILL.md` or pass `--help` to the bat (most underlying scripts use argparse and surface helpful output).

---

## The four skills in detail

### `/dayz-preflight`

Verifies the modding environment before any other DayZ skill runs. **Every other DayZ skill that does work calls this first** and propagates non-zero exit, except the documented exceptions listed at the top of this page (with reasons in `.claude/skills/_shared/dayz-conventions.md`).

| Check | Severity |
|---|---|
| `P:\` mounted | **hard fail** — exit 1 |
| `AddonBuilder.exe` locatable (env / registry / Steam paths) | warn |
| Vanilla data on `P:\` (looks for `P:\dz`, `P:\DZ`, `P:\dta`) | warn |
| `P:\Mods\` exists or can be created | warn (creates if missing) |

Hard-fail message tells you to mount `P:\` via DayZ Tools.

Path resolution order for DayZ Tools:

1. `$DAYZ_TOOLS_PATH` env var
2. Windows registry (HKLM/HKCU under `Bohemia Interactive\DayZ Tools`)
3. Steam libraries: the Steam root from the registry (`HKCU\Software\Valve\Steam` SteamPath, `HKLM\SOFTWARE\WOW6432Node\Valve\Steam` InstallPath), then both defaults (`C:\Program Files (x86)\Steam`, `C:\Program Files\Steam`), which are always checked, plus every library listed in `steamapps\libraryfolders.vdf`, each checked for `steamapps\common\DayZ Tools`

Path resolution order for vanilla data:

1. `$DAYZ_VANILLA_DATA_PATH` env var
2. Canonical names on `P:\`: `P:\dz`, `P:\DZ`, `P:\dta`

Helper functions `find_dayz_tools()` and `find_vanilla_data()` are exported from `preflight.py` — every other DayZ skill imports them rather than re-implementing path discovery.

### `/dayz-new-mod`

Scaffolds a new mod project under `workspace/<ModName>/` and creates the `P:\<ModName>\` junction so AddonBuilder and the engine can find it.

```cmd
python .claude\skills\dayz-new-mod\new_mod.py <ModName> [--author "YourHandle"]
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

### `/dayz-build-pbo`

Packs the mod into a deployable `.pbo` via AddonBuilder.

```cmd
python .claude\skills\dayz-build-pbo\build.py <ModName> [--clean]
```

**Steps performed:**

1. Validate `<ModName>`.
2. `/dayz-lint` gate: any lint error refuses the build; warnings are printed.
3. Preflight gate.
4. Verify the `P:\Mods\` junction is valid (hard fail).
5. Verify `workspace/<ModName>/config.cpp` and `workspace/<ModName>/$PBOPREFIX$` exist, and that `$PBOPREFIX$` contains exactly `<ModName>`.
6. Verify `P:\<ModName>\` is a link pointing at `workspace/<ModName>/`.
7. Resolve `AddonBuilder.exe` via `find_dayz_tools()`.
8. Ownership-marker gate: refuse to build into a `P:\Mods\@<ModName>\` that Agentic-Z did not create. With `--clean`, also refuse while `Addons\` holds PBOs other than `<ModName>.pbo`.
9. Ensure `P:\Mods\@<ModName>\Addons\` and `P:\temp\<ModName>\` exist, writing the marker when this run created `@<ModName>`.
10. Copy the mod to `P:\temp\_stage\<ModName>\` without the files `exclude.lst` names, then invoke `AddonBuilder.exe P:\temp\_stage\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill>\include.lst [-clear]`. It passes no `-exclude=`, because AddonBuilder 1.0.240639 crashes on that flag. AddonBuilder's stdout/stderr stream live so you see binarization progress and config errors as they happen.
11. Verify `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and was refreshed by this build.
12. Remove the temp dir on success (kept on failure for debugging).

**`--clean` flag** passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Useful after large refactors or when chasing stale-asset bugs. Refused while `Addons\` holds any `.pbo` other than `<ModName>.pbo` (deployed payload from `/dayz-deploy-pbo`), since `-clear` would wipe it; build without `--clean`, or remove those PBOs first and re-deploy afterwards.

Default output is binarized. A `--no-binarize` flag is not exposed yet — easy to add later when iteration speed becomes a concern.

### `/dayz-launch-test`

Spins up a local development environment to test one or more built mods. **Always launches the server first**, then the client connecting to it — DayZ has no offline / single-player mode for mod testing.

```cmd
python .claude\skills\dayz-launch-test\launch.py <ModName> [<ModName2> ...] [--server-only <Mod> ...] [--server <instance>] [--port N] [--dry-run]
```

**Steps performed:**

1. Preflight gate.
2. For each mod, verify `P:\Mods\@<ModName>\Addons\` holds at least one `.pbo` (any name, so mods with several PBOs work). Fails with a hint to run `/dayz-build-pbo` if the folder is missing or has no `.pbo`.
3. Resolve `DayZDiag_x64.exe` (env `DAYZ_DIAG_PATH` → DayZ game install → Steam fallbacks). **Hard-fail if missing.** Both server and client run from the same diag binary.
4. **First-run only:** the instance must have been added via `/dayz-add-server <instance>`, which copies the mission template from DayZ Server's `mpmissions/<template>/` into `.server/<instance>/mission/`. After this initial copy, DayZ Server can be uninstalled.
5. Verify `.server/<instance>/serverDZ.cfg` and `.server/<instance>/mission/` exist for the selected instance (default `chernarus`). The skill never edits the cfg: if it lacks an active `allowFilePatching = 1;` (missing, commented out or another value) or a `template = "...";` line, or the `<template>/` junction to `mission/` is missing, the launch is refused with a hint to run `/dayz-add-server <instance>`, which sets these up.
6. Refuse if the port is already in use (not checked on `--dry-run`), then spawn the server: `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/Profiles -mission=<instance>/<template> -mod=P:\Mods\@Mod1;P:\Mods\@Mod2 [-serverMod=P:\Mods\@ServerOnly1;...] -filePatching -port=<port>`. `-mission=` is the absolute `.server/<instance>/<template>` path (for example `dayzOffline.chernarusplus`), the junction to `mission/` that `/dayz-add-server` creates; without a path named after the template the client connects but never spawns.
7. Wait (up to 180 seconds) until the server has bound its UDP port.
8. Spawn the client: `DayZDiag_x64.exe -profiles=.server/!ClientDiagLogs -mod=P:\Mods\@Mod1;P:\Mods\@Mod2 -connect=127.0.0.1 -port=<port> -filePatching -window -x=<W> -y=<H>`. Windowed mode and resolution come from `.claude/local-memory/dayz-client-display.json`, created with `{"windowed": true, "width": 1920, "height": 1080}` on the first non-dry-run launch; edit it to change them (invalid contents fall back to the defaults). **The client must be DayZ Diag, not retail.** Retail `DayZ_x64.exe` blocks past the loading screen with `-filePatching`. The client `-profiles=` points at the shared top-level `.server/!ClientDiagLogs/` (vanilla naming convention; client diag artifacts don't need per-instance isolation).
9. Print both PIDs and exit. **You close both windows manually** to stop them. (Or run `/dayz-stop-test`.)

**`--server <instance>`** selects which instance to test on. Defaults to `chernarus`. The instance must have been added via `/dayz-add-server` first.

**`--server-only <Mod> ...`** loads these mods on the server via `-serverMod=` and never on the client, for server-side mods that exit when loaded client-side. Their PBOs must exist. A mod cannot be named both as shared and as server-only.

**`--dry-run`** prints the resolved server and client commands without launching. Useful for verifying paths and arg construction.

**`--port`** overrides the default `2302`.

**`-filePatching`** is set on both server and client so the engine reads raw `.cpp` / `.c` files from the `P:\<ModName>\` junction instead of only the binarized PBO. This lets you iterate on Enforce Script and configs without rebuilding the PBO every change. The PBO must still exist (the engine looks up the addon by name there) but the actual content can come from source.

---

## Mod project layout

When you scaffold `MyMod` via `/dayz-new-mod`, here's what exists and where:

```
<repo>/
├── workspace/
│   └── MyMod/                          # your editable source (under git, your editor)
│       ├── config.cpp                  # engine declarations
│       ├── $PBOPREFIX$                 # in-game data path: "MyMod"
│       ├── scripts/
│       │   ├── 3_Game/                 # base game scripts
│       │   ├── 4_World/                # world-level scripts
│       │   └── 5_Mission/              # mission / server scripts
│       ├── data/                       # .p3d / .paa / .rvmat
│       ├── gui/                        # .layout files
│       ├── workbench/                  # dayz.gproj + DayZSetting.xml for /dayz-launch-workbench --mod
│       └── README.md
└── P:\
    ├── MyMod\  ->  workspace\MyMod\    # junction: created by /dayz-new-mod
    └── Mods\@MyMod\Addons\MyMod.pbo    # built artifact: created by /dayz-build-pbo
```

### Why the `P:\` junction

DayZ Tools' AddonBuilder reads source folders from `P:\` and resolves `$PBOPREFIX$` relative to it. Our convention keeps source under `workspace/<ModName>/` (under git, in your editor of choice), but the engine and Tools expect to see it at `P:\<ModName>\`. The junction creates one source of truth that both your editor and the engine see.

- You edit files in `workspace/<ModName>/` like any normal repo file.
- AddonBuilder, the engine, and DayZ Tools see them at `P:\<ModName>\` automatically.
- `/dayz-build-pbo` doesn't need to manage the junction — it just verifies it exists.
- No copies, no de-sync.

The skill creates the junction at scaffold time. Junctions don't require admin; symlinks do. The skill tries `os.symlink` first and falls back to `mklink /J` (junction) on Windows when symlinks need elevation.

If the link is missing later (for example a mod cloned straight into `workspace/`, or the link was removed), repair it with `/dayz-add-scaffold <ModName> --piece junction`. It creates only the link, never touches files in the mod, and refuses if `P:\<ModName>\` is a real folder or points somewhere else.

---

## Environment variables (path overrides)

All DayZ skills resolve paths in this order: env var → Windows registry (Tools only) → common-default fallback. **Set these only if your install lives outside the defaults.**

| Variable | Resolves | Used by |
|---|---|---|
| `DAYZ_TOOLS_PATH` | DayZ Tools install root (parent of `Bin\AddonBuilder\AddonBuilder.exe`) | preflight, build, anywhere AddonBuilder is invoked |
| `DAYZ_GAME_PATH` | DayZ game install (contains both `DayZ_x64.exe` retail and `DayZDiag_x64.exe`) | preflight, launch-test (used to find diag) |
| `DAYZ_DIAG_PATH` | Direct path to `DayZDiag_x64.exe` if it lives outside the DayZ game install | launch-test |
| `DAYZ_SERVER_PATH` | DayZ Server install (containing `DayZServer_x64.exe`). Read by `find_dayz_server()`; `/dayz-add-server` copies the mission template from it. `/dayz-launch-test` runs the diag build and does not use it. | `/dayz-add-server` |
| `DAYZ_VANILLA_DATA_PATH` | Folder on `P:\` containing unpacked vanilla DayZ PBOs (default candidates: `P:\dz`, `P:\DZ`, `P:\dta`) | preflight, future skills that read vanilla configs |
| `DAYZ_WORK_DRIVE` | Folder that WorkDrive mounts as `P:\`. If it is unset, the cached path from the last mount is used, then DayZ Tools' `settings.ini` `[ProjectDrive] path`. There is no default and no registry lookup: if none of these is found, `/dayz-workdrive` fails and asks for `--path`. | `/dayz-workdrive` |

PowerShell example:

```powershell
$env:DAYZ_TOOLS_PATH = 'D:\Games\Steam\steamapps\common\DayZ Tools'
$env:DAYZ_DIAG_PATH = 'D:\Games\Steam\steamapps\common\DayZ\DayZDiag_x64.exe'
```

CMD example:

```cmd
set DAYZ_TOOLS_PATH=D:\Games\Steam\steamapps\common\DayZ Tools
set DAYZ_DIAG_PATH=D:\Games\Steam\steamapps\common\DayZ\DayZDiag_x64.exe
```

To make the override persistent, set it via System Properties → Environment Variables.

---

## Per-clone caches and runtime files

Two locations hold per-clone, gitignored, user/machine-specific state:

| Path | Contents | Created by |
|---|---|---|
| `.claude/local-memory/dayz-author.txt` | One-line cached author handle (e.g. `MyHandle`) | `/dayz-new-mod` first run |
| `.claude/local-memory/dayz-current-project.txt` | The project root every DayZ skill reads; they refuse to run until it exists | `/dayz-init`, `/dayz-new-mod`, `/dayz-import-mod` |
| `.claude/local-memory/dayz-init-state.json` | The active mod and other setup choices | `/dayz-init` |
| `.claude/local-memory/dayz-client-display.json` | Client windowed mode and resolution | `/dayz-launch-test` first run |
| `.server/<instance>/mission/` | **Editable copy** of a DayZ mission folder (one per instance). | `/dayz-add-server` (bootstrapped from DayZ Server install) |
| `.server/<instance>/serverDZ.cfg` | Per-instance server config. Tunable. | `/dayz-add-server` (default written on first add; preserved thereafter) |
| `.server/<instance>/Profiles/` | Per-instance server `-profiles=` dir (RPT, script.log, BattlEye state). | `/dayz-add-server` (created empty); populated by `/dayz-launch-test` |
| `.server/!ClientDiagLogs/` | Shared client `-profiles=` dir (RPT, BattlEye state, Users/, DataCache/). | `/dayz-add-server` (created empty); populated by `/dayz-launch-test` |

Override the author handle: `python .claude\skills\dayz-new-mod\new_mod.py MyMod --author "NewHandle"` (overwrites the cache) or delete `.claude/local-memory/dayz-author.txt`.

`.server/` is gitignored by default except for `serverDZ.cfg` and `mission/` contents (so your tuned configs and mission edits stay in version control while logs and profiles do not). Override the gitignore in your clone if you want different behavior.

---

## L2 conventions (workflow rules)

The core L2 rules live at `.claude/skills/_shared/dayz-conventions.md`; topic rules (config, assets, scripts, UI, server) live in `.claude/skills/_shared/conventions/`. The high-level rules:

- **Every DayZ skill MUST gate on `/dayz-preflight`** at the start of execution and halt on non-zero exit, even offline scaffolding skills. The exceptions are the emergency stop (`/dayz-stop-test`), meta-skills that edit settings or rule files rather than DayZ content (`/dayz-scope-mod`, `/dayz-record-correction`), `/dayz-init` (runs preflight inside its own steps), `/dayz-workdrive` (mounts `P:\`), the gate itself (`/dayz-preflight`), `/dayz-search-download`, `/dayz-ask`, `/dayz-gate` (gates through the skills it runs), the read-only and report skills (`/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe`, `/dayz-layout-preview`, `/dayz-upgrade-guard`, `/dayz-release-pack`, `/dayz-server-kit`, `/dayz-health`, `/dayz-logwatch`), `/dayz-route` and `/dayz-statusline`. The reason for each is in `.claude/skills/_shared/dayz-conventions.md`. The discipline of "preflight first" keeps the workflow uniform and catches a dismounted drive at the first action of a session.
- **`P:\` must be mounted** by DayZ Tools before any DayZ work. Preflight enforces.
- **DayZ cannot be tested standalone.** A local server MUST be loaded with the same mod set as the client. `/dayz-launch-test` enforces; never launch the client alone for mod testing.
- **Mod source under `workspace/<ModName>/`**. Built `.pbo` deploys to `P:\Mods\@<ModName>\Addons\`. Scaffold owns the `P:\<ModName>\` junction; build/test skills only verify it.
- **Skills MUST use the shared resolvers** (`find_dayz_tools`, `find_dayz_game`, `find_dayz_diag`, `find_dayz_server`, `find_vanilla_data` in `dayz-preflight/preflight.py`) rather than re-implementing path discovery. Single source of truth.

---

## Superpowers ↔ DayZ specialist routing

When a Superpowers workflow (`/brainstorming`, `/writing-plans`, `/executing-plans`, `/requesting-code-review`, `/dispatching-parallel-agents`, `/subagent-driven-development`, etc.) needs to dispatch a subagent and the work touches DayZ, route to the matching `dayz-*` specialist via the Agent tool. Do NOT use generic Superpowers agents (e.g. `superpowers:code-reviewer`) on DayZ code - they don't know Enforce Script, the `modded class` no-extends rule, hidden-selection conventions, or the engine-classes-can't-be-modded constraint.

| Superpowers role / verb | DayZ specialist to dispatch |
|---|---|
| whole mod, many parts | `dayz-orchestrator` as the main session (`claude --agent agentic-z:dayz-orchestrator`) |
| planning / design a mod | `dayz-mod-architect` |
| build check / verification | `dayz-build-checker`, then `dayz-ingame-tester` |
| release build and test session (build the PBO, start a session for the user) | `dayz-build-engineer` |
| code review | `dayz-mod-reviewer` |
| scripting (Enforce Script) | `dayz-script-specialist` |
| config / data (config.cpp, CfgVehicles, etc.) | `dayz-config-specialist` |
| UI (`.layout`, widgets, HUD, menus, color theme) | `dayz-ui-specialist` |
| 3D model (`.p3d`, LODs, named selections) | `dayz-object-builder` |
| textures / materials (`.paa`, `.rvmat`) | `dayz-asset-specialist` |
| terrain / map / clutter | `dayz-map-specialist` |
| server / Central Economy / `types.xml` / `init.c` | `dayz-server-admin` |
| Workbench plugin (editor-time tooling) | `dayz-workbench-specialist` |
| saving data across restarts, save versions, base building saves | `dayz-persistence-specialist` |
| infected, animals, patrols and guards | `dayz-ai-specialist` |
| cars, boats and helicopters | `dayz-vehicle-specialist` |
| weapons, magazines, ammo, attachments | `dayz-weapon-specialist` |
| clothing, gear and characters | `dayz-wearables-specialist` |
| moving parts, `model.cfg` animations, RTM | `dayz-animation-specialist` |
| sound sets, sound shaders, particles | `dayz-audio-fx-specialist` |
| weight, collision, dropping and throwing | `dayz-physics-specialist` |
| log / crash forensics (RPT, script.log, BattlEye) | `dayz-mod-debugger` |
| README, changelog, Workshop text, server owner kit | `dayz-docs-writer` |
| Figma → `.layout` conversion | `figma-node-normalizer` → `figma-to-dayz-layout` → `dayz-layout-validator` (gate mode), then `dayz-ui-specialist` for the widget script (in order) |

How to apply: when a Superpowers skill says "dispatch a code reviewer" while you're working on DayZ files, call `Agent(subagent_type="dayz-mod-reviewer", ...)` instead of the default. Same idea for the other roles. For non-DayZ work (Python skills, scripts, infra, the wiki), Superpowers' generic agents are fine.

When in doubt, check the touched paths: anything under `workspace/<ModName>/`, `.claude/skills/dayz-*/`, `P:\`, or DayZ-specific files (`.c`, `.layout`, `.p3d`, `.paa`, `.rvmat`, `config.cpp`, `types.xml`) → DayZ specialist.

---

## Troubleshooting

### `[FAIL] P:\ is NOT mounted`

DayZ Tools didn't mount the P drive (or it was unmounted). Open DayZ Tools and use the "Mount P drive" command (Tools menu). `P:\` does not auto-mount across reboots.

### `[WARN] DayZ Tools not detected` / `[FAIL] DayZ Tools not found.`

Either DayZ Tools isn't installed, or it's installed somewhere unusual. `/dayz-preflight` only warns here; skills that run a DayZ Tools exe (`/dayz-build-pbo`, `/dayz-build-imageset`, `/dayz-pack-texture`, `/dayz-launch-workbench`, `/dayz-launch-objectbuilder`, `/dayz-setup-objectbuilder`) fail with `[FAIL] DayZ Tools not found.`

- Install via Steam → Library → Tools → DayZ Tools (free).
- If installed in a non-default location: set `$env:DAYZ_TOOLS_PATH` to the install root (parent of `Bin\AddonBuilder\AddonBuilder.exe`).

### `[WARN] Vanilla DayZ data not detected on P:\`

You haven't extracted the vanilla DayZ PBOs to `P:\`. Open DayZ Tools → Extract Game Data → run the extraction. This is a one-time setup step (per Tools update).

### `[FAIL] P:\Mods\ does not exist` / `is a regular folder, not a junction` / `junction is dangling`

`P:\Mods\` must be a directory junction to `<DayZ install>\!Workshop\` so built PBOs land where the engine actually loads mods. Run:

```cmd
cmd /c rmdir P:\Mods                                                     (only if it exists as a regular folder)
cmd /c mklink /J P:\Mods "C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop"
```

Adjust the target path if your DayZ install is elsewhere. Preflight warns; build-pbo refuses to run.

### `Connection failed 0x00020005` / "The server does not support the client's current filePatching setting"

The server's `serverDZ.cfg` is missing `allowFilePatching = 1;`. The client connects with `-filePatching` enabled, and the server refuses unless the cfg explicitly allows it. `/dayz-launch-test` refuses to launch an instance whose cfg lacks an active `allowFilePatching = 1;`, so you normally see this only with a hand-edited cfg or a server started outside the skill. Fix: re-run `/dayz-add-server <instance>`, which sets the line to `allowFilePatching = 1;` whether it was missing, commented out or set to another value.

### "Mission script has no main function. PlayerConnect will stay disabled"

The server can't find a valid mission folder, so it loaded an empty/broken mission. Check that:

- `.server/<instance>/mission/` exists (default chernarus instance is created by `/dayz-add-server chernarus`).
- That folder has an `init.c` with a proper `main()` function.

`/dayz-launch-test` passes `-mission=<absolute path to .server/<instance>/<template>>` (the template junction to `mission/`) so the engine doesn't look in the wrong `mpmissions/` location. If the mission copy got corrupted or partially deleted, run `/dayz-add-server <instance> --refresh-mission` to re-copy from DayZ Server install.

### `[FAIL] DayZDiag_x64.exe not found`

DayZ Diag is the diagnostic client required for mod development. It ships **alongside** the retail `DayZ_x64.exe` in your DayZ game install dir — if you have DayZ installed it should already be there. If it's not, your DayZ install may be incomplete or out of date. Verify the file integrity in Steam (Library → DayZ → Properties → Local Files → Verify). If your install is in a non-standard location, set `DAYZ_DIAG_PATH` directly to the exe path.

### `[FAIL] P:\<ModName> exists as a real folder, not a link` / `[FAIL] P:\<ModName> is a link pointing at <target>`

You have a folder or junction at `P:\<ModName>\` that the skill won't clobber. Either:

- It's a real folder (move or remove it manually).
- It's a junction pointing somewhere other than `workspace/<ModName>/` (remove via `cmd /c rmdir P:\<ModName>` and re-run).

### `[FAIL] workspace\<ModName> already exists`

The scaffold already exists. Pick a different name, or `rm -rf workspace/<ModName>/` to start over (the skill will auto-clean the resulting dangling junction on the next scaffold).

### `[FAIL] Mod '<Name>' has no Addons folder` / `[FAIL] Mod '<Name>' has no .pbo files`

You called `/dayz-launch-test` before `/dayz-build-pbo`. Run the build first.

### Mod doesn't load in-game

Checklist:

- `/dayz-preflight` passes?
- `P:\<ModName>\` junction points at the right `workspace\<ModName>\`?
- `workspace\<ModName>\config.cpp` has a `CfgPatches\<ModName>` entry?
- `P:\Mods\@<ModName>\Addons\<ModName>.pbo` is newer than your last edit?
- Server log (newest `script*.log` in `.server\<instance>\Profiles\`) shows the mod loading?
- Client launch line includes `-mod=@<ModName>`?

### `[FAIL] P:\<ModName> junction is missing` / junction got corrupted

The mod folder is fine but the `P:\<ModName>\` link to it is gone. Run `/dayz-add-scaffold <ModName> --piece junction` to recreate it; your files in `workspace/<ModName>/` are not touched. If `P:\<ModName>\` still exists as a link pointing somewhere else, remove it first with `cmd /c rmdir P:\<ModName>` (this removes only the link, not the target), then run the same command.

---

## Where everything lives (ASCII map)

```
<repo>/
├── .claude/
│   ├── skills/
│   │   ├── dayz-preflight/
│   │   │   ├── SKILL.md
│   │   │   └── preflight.py        # exports find_dayz_tools, find_dayz_game,
│   │   │                           # find_dayz_diag, find_dayz_server,
│   │   │                           # find_vanilla_data
│   │   ├── dayz-new-mod/
│   │   │   ├── SKILL.md
│   │   │   └── new_mod.py
│   │   ├── dayz-build-pbo/
│   │   │   ├── SKILL.md
│   │   │   └── build.py
│   │   ├── dayz-launch-test/
│   │   │   ├── SKILL.md
│   │   │   └── launch.py
│   │   └── _shared/
│   │       ├── dayz-conventions.md  # L2 core rules every DayZ skill follows
│   │       └── conventions/         # L2 topic rules (config, assets, scripts, ui, server)
│   └── local-memory/                # gitignored, per-clone
│       ├── dayz-author.txt
│       ├── dayz-current-project.txt
│       └── dayz-init-state.json
├── workspace/
│   └── <ModName>/                   # your mod source (created by /dayz-new-mod)
├── .server/
│   └── <instance>/                  # local test server (created by /dayz-add-server)
└── docs/
    └── dayz-modding.md              # this file
```

On `P:\`:

```
P:\
├── <ModName>\           # junction → <repo>\workspace\<ModName>\  (created by /dayz-new-mod)
├── Mods\@<ModName>\Addons\<ModName>.pbo    # built artifact (created by /dayz-build-pbo)
├── temp\<ModName>\      # AddonBuilder temp (created and cleaned by /dayz-build-pbo)
└── dz\                  # vanilla DayZ data (you extract this once via DayZ Tools)
```
