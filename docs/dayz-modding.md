# DayZ Modding

Agentic-Z ships with a complete DayZ modding workflow covering the full mod lifecycle — from "fresh checkout" to "playing my mod on a local server."

## Front door: `/dayz-init`

The fastest path is the wizard:

```
/dayz-init
```

First run: env check, intent prompts (new mod or import, mod name, test map, build/launch toggles, RAG setup), executes the resulting plan. Every run after: drops into a mission-control hub for the cached project — build & launch, stop diag, tail server log, open Workbench / Object Builder, switch project, etc.

The wizard wraps the lower-level skills below, never replaces them. Use it for normal flow; reach for the individual skills when you need surgical control.

## Underlying skills (the wizard orchestrates these)

1. **`/dayz-preflight`** — verifies your DayZ modding environment is ready.
2. **`/dayz-new-mod`** / **`/dayz-import-mod`** — scaffold a new mod project (or symlink an existing one) with the required `P:\<ModName>\` junction.
3. **`/dayz-add-scaffold`** — fill in missing scaffold pieces (config.cpp stub, gproj, etc.) on a mod folder that lacks them.
4. **`/dayz-add-server`** — sets up a test server instance under `.server/<instance>/`: copies the mission template, creates per-instance `serverDZ.cfg` + `Profiles/` (server `-profiles=` dir), and ensures the shared `.server/!ClientDiagLogs/` (client `-profiles=` dir) exists. One-time per instance. Multiple variants of the same map allowed.
5. **`/dayz-build-pbo`** — packs the mod into a deployable `.pbo` via DayZ Tools' AddonBuilder.
6. **`/dayz-launch-test`** — spins up a local DayZ server with your mod loaded on the chosen instance, then connects the client. Run-only; refuses if the instance hasn't been added.

   Counterpart: **`/dayz-stop-test`** — force-kills any running DayZDiag_x64.exe processes so you can stop a session without hunting down windows. Doesn't gate on preflight (emergency escape hatch).
7. **`/dayz-cot-bootstrap`** — two-pass workflow that grants COT (Community-Online-Tools) admin perms on a fresh test instance. Auto-prepends @CF + @Community-Online-Tools, launches, waits for COT to write the per-player JSON, kills the session, edits the perm files, relaunches.
8. **`/dayz-clean-workspace`** — DayZ-only cleanup. Removes scaffolds and their deployed artifacts (workspace folders, `P:\<ModName>\` junctions that target our workspace, `P:\Mods\@<ModName>\` deploy dirs). Match-on-scaffold rule keeps your subscribed mods safe. `--include-server` also removes `.server/`.

For a repo-wide wipe across every domain (pre-push reset), use the general **`/clean-repo`** skill — it orchestrates each `<domain>-clean-workspace` cleanup in turn.

Most skills gate on `/dayz-preflight` first per the L2 convention `.claude/skills/_shared/dayz-conventions.md`. Documented exceptions: `/dayz-stop-test` (escape hatch) and `/dayz-init` (orchestrator — runs preflight on its own steps).

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
| **Python 3.8+** on `PATH` | python.org | The skills are Python scripts. |
| **Voyage AI API key** *(optional, only for RAG)* | Sign up at [dash.voyageai.com](https://dash.voyageai.com) (free, 200M-token allowance), add `VOYAGE_API_KEY=pa-…` to `.env` at the repo root | Powers `/dayz-search-index` and the `dayz-rag` MCP server. Enables semantic search ("how does vanilla handle X?") over the indexed source. Embeddings via `voyage-code-3` (code-tuned, 1024-dim). Without it, agents fall back to `Grep` on the documented vanilla paths — fully functional, just less smart. **Shortcut:** `/dayz-search-download` pulls a prebuilt index from GitHub releases (~1 min) — no key needed for download, but query-time still requires the key. |

---

## Quick start

From a fresh clone:

```cmd
git clone <this-repo> my-dayz-mod
cd my-dayz-mod
python .claude\skills\sync-skills\sync.py

:: Optional but recommended — pull the prebuilt vector index from GitHub
:: releases instead of running /dayz-search-index locally (~25 min vs ~1 min):
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
python .claude\skills\dayz-launch-test\launch.py MyMod --map chernarus
```

Inside Claude Code, Codex, or Gemini CLI, the same commands are available as slash commands: `/dayz-preflight`, `/dayz-new-mod`, etc.

### Without the agent: `scripts\*.bat`

Every slash-command skill has a matching `.bat` wrapper in `scripts\`. Each is a thin pass-through to the underlying skill's Python script with all arguments forwarded. Use these from Explorer or a plain terminal when you don't want to spin up an agent for a one-line action.

Bat naming drops the `dayz-` prefix where present. Examples:

```text
scripts\preflight.bat               -> /dayz-preflight
scripts\workdrive.bat                 -> /dayz-workdrive
scripts\new-mod.bat MyMod           -> /dayz-new-mod MyMod
scripts\build-pbo.bat MyMod         -> /dayz-build-pbo MyMod
scripts\launch-test.bat MyMod       -> /dayz-launch-test MyMod
scripts\workbench.bat --mod MyMod   -> /dayz-launch-workbench --mod MyMod
scripts\stop-test.bat               -> /dayz-stop-test
scripts\scope-mod.bat MyMod         -> /dayz-scope-mod MyMod
scripts\clean-repo.bat --yes        -> /clean-repo --yes
```

For full per-skill argument detail, see the skill's `SKILL.md` or pass `--help` to the bat (most underlying scripts use argparse and surface helpful output).

---

## The four skills in detail

### `/dayz-preflight`

Verifies the modding environment before any other DayZ skill runs. **Every other DayZ skill calls this first** and propagates non-zero exit.

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
3. Common Steam paths (`C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools`, `C:\Program Files\…`)

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
└── gui/.gitkeep               # UI layouts (.layout) and controllers
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

1. Preflight gate.
2. Verify `workspace/<ModName>/config.cpp` and `workspace/<ModName>/$PBOPREFIX$` exist.
3. Verify `P:\<ModName>\` is a link pointing at `workspace/<ModName>/`.
4. Resolve `AddonBuilder.exe` via `find_dayz_tools()`.
5. Ensure `P:\Mods\@<ModName>\Addons\` and `P:\temp\<ModName>\` exist.
6. Invoke `AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]`. AddonBuilder's stdout/stderr stream live so you see binarization progress and config errors as they happen.
7. Verify `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and was refreshed by this build.
8. Remove the temp dir on success (kept on failure for debugging).

**`--clean` flag** passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Useful after large refactors or when chasing stale-asset bugs.

Default output is binarized. A `--no-binarize` flag is not exposed yet — easy to add later when iteration speed becomes a concern.

### `/dayz-launch-test`

Spins up a local development environment to test one or more built mods. **Always launches the server first**, then the client connecting to it — DayZ has no offline / single-player mode for mod testing.

```cmd
python .claude\skills\dayz-launch-test\launch.py <ModName> [<ModName2> ...] [--port N] [--dry-run]
```

**Steps performed:**

1. Preflight gate.
2. For each mod, verify `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists. Fails with a hint to run `/dayz-build-pbo` if missing.
3. Resolve `DayZDiag_x64.exe` (env `DAYZ_DIAG_PATH` → DayZ game install → Steam fallbacks). **Hard-fail if missing.** Both server and client run from the same diag binary.
4. **First-run only:** the instance must have been added via `/dayz-add-server <instance>`, which copies the mission template from DayZ Server's `mpmissions/<template>/` into `.server/<instance>/mission/`. After this initial copy, DayZ Server can be uninstalled.
5. Verify `.server/<instance>/serverDZ.cfg` and `.server/<instance>/mission/` exist for the selected instance (default `chernarus`). Existing cfgs are preserved but `allowFilePatching = 1;` is auto-appended if missing.
6. Spawn the server: `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/Profiles -mission=<instance>/mission -mod=@Mod1;@Mod2 -filePatching -port=<port>`. The `-mission=<absolute path>` flag pins the mission folder explicitly.
7. Wait 5 seconds for the server to start listening.
8. Spawn the client: `DayZDiag_x64.exe -profiles=.server/!ClientDiagLogs -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=<port> -filePatching`. **The client must be DayZ Diag, not retail.** Retail `DayZ_x64.exe` blocks past the loading screen with `-filePatching`. The client `-profiles=` points at the shared top-level `.server/!ClientDiagLogs/` (vanilla naming convention; client diag artifacts don't need per-instance isolation).
9. Print both PIDs and exit. **You close both windows manually** to stop them. (Or run `/dayz-stop-test`.)

**`--server <instance>`** selects which instance to test on. Defaults to `chernarus`. The instance must have been added via `/dayz-add-server` first.

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

---

## Environment variables (path overrides)

All DayZ skills resolve paths in this order: env var → Windows registry (Tools only) → common-default fallback. **Set these only if your install lives outside the defaults.**

| Variable | Resolves | Used by |
|---|---|---|
| `DAYZ_TOOLS_PATH` | DayZ Tools install root (parent of `Bin\AddonBuilder\AddonBuilder.exe`) | preflight, build, anywhere AddonBuilder is invoked |
| `DAYZ_GAME_PATH` | DayZ game install (contains both `DayZ_x64.exe` retail and `DayZDiag_x64.exe`) | preflight, launch-test (used to find diag) |
| `DAYZ_DIAG_PATH` | Direct path to `DayZDiag_x64.exe` if it lives outside the DayZ game install | launch-test |
| `DAYZ_SERVER_PATH` | DayZ Server install (containing `DayZServer_x64.exe`) — **not used by `/dayz-launch-test` in diag mode**; reserved for future retail-server skills | reserved |
| `DAYZ_VANILLA_DATA_PATH` | Folder on `P:\` containing unpacked vanilla DayZ PBOs (default candidates: `P:\dz`, `P:\DZ`, `P:\dta`) | preflight, future skills that read vanilla configs |

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
| `.server/<instance>/mission/` | **Editable copy** of a DayZ mission folder (one per instance). | `/dayz-add-server` (bootstrapped from DayZ Server install) |
| `.server/<instance>/serverDZ.cfg` | Per-instance server config. Tunable. | `/dayz-add-server` (default written on first add; preserved thereafter) |
| `.server/<instance>/Profiles/` | Per-instance server `-profiles=` dir (RPT, script.log, BattlEye state). | `/dayz-add-server` (created empty); populated by `/dayz-launch-test` |
| `.server/!ClientDiagLogs/` | Shared client `-profiles=` dir (RPT, BattlEye state, Users/, DataCache/). | `/dayz-add-server` (created empty); populated by `/dayz-launch-test` |

Override the author handle: `python .claude\skills\dayz-new-mod\new_mod.py MyMod --author "NewHandle"` (overwrites the cache) or delete `.claude/local-memory/dayz-author.txt`.

`.server/` is gitignored by default except for `serverDZ.cfg` and `mission/` contents (so your tuned configs and mission edits stay in version control while logs and profiles do not). Override the gitignore in your clone if you want different behavior.

---

## L2 conventions (workflow rules)

The full L2 rules live at `.claude/skills/_shared/dayz-conventions.md`. The high-level rules:

- **Every DayZ skill MUST gate on `/dayz-preflight`** at the start of execution and halt on non-zero exit. No exceptions, even for offline scaffolding skills. The discipline of "preflight first" keeps the workflow uniform and catches a dismounted drive at the first action of a session.
- **`P:\` must be mounted** by DayZ Tools before any DayZ work. Preflight enforces.
- **DayZ cannot be tested standalone.** A local server MUST be loaded with the same mod set as the client. `/dayz-launch-test` enforces; never launch the client alone for mod testing.
- **Mod source under `workspace/<ModName>/`**. Built `.pbo` deploys to `P:\Mods\@<ModName>\Addons\`. Scaffold owns the `P:\<ModName>\` junction; build/test skills only verify it.
- **Skills MUST use the shared resolvers** (`find_dayz_tools`, `find_dayz_game`, `find_dayz_diag`, `find_dayz_server`, `find_vanilla_data` in `dayz-preflight/preflight.py`) rather than re-implementing path discovery. Single source of truth.

---

## Superpowers ↔ DayZ specialist routing

When a Superpowers workflow (`/brainstorming`, `/writing-plans`, `/executing-plans`, `/requesting-code-review`, `/dispatching-parallel-agents`, `/subagent-driven-development`, etc.) needs to dispatch a subagent and the work touches DayZ, route to the matching `dayz-*` specialist via the Agent tool. Do NOT use generic Superpowers agents (e.g. `superpowers:code-reviewer`) on DayZ code - they don't know Enforce Script, the `modded class` no-extends rule, hidden-selection conventions, or the engine-classes-can't-be-modded constraint.

| Superpowers role / verb | DayZ specialist to dispatch |
|---|---|
| code review | `dayz-mod-reviewer` |
| scripting (Enforce Script) | `dayz-script-specialist` |
| config / data (config.cpp, CfgVehicles, etc.) | `dayz-config-specialist` |
| UI (`.layout`, widgets, HUD, menus, color theme) | `dayz-ui-specialist` |
| 3D model (`.p3d`, LODs, named selections) | `dayz-object-builder` |
| textures / materials (`.paa`, `.rvmat`) | `dayz-asset-specialist` |
| terrain / map / clutter | `dayz-map-specialist` |
| server / Central Economy / `types.xml` / `init.c` | `dayz-server-admin` |
| Workbench plugin (editor-time tooling) | `dayz-workbench-specialist` |
| log / crash forensics (RPT, script.log, BattlEye) | `dayz-mod-debugger` |

How to apply: when a Superpowers skill says "dispatch a code reviewer" while you're working on DayZ files, call `Agent(subagent_type="dayz-mod-reviewer", ...)` instead of the default. Same idea for the other roles. For non-DayZ work (Python skills, scripts, infra, the wiki), Superpowers' generic agents are fine.

When in doubt, check the touched paths: anything under `workspace/<ModName>/`, `.claude/skills/dayz-*/`, `P:\`, or DayZ-specific files (`.c`, `.layout`, `.p3d`, `.paa`, `.rvmat`, `config.cpp`, `types.xml`) → DayZ specialist.

---

## Troubleshooting

### `[FAIL] P:\ is NOT mounted`

DayZ Tools didn't mount the P drive (or it was unmounted). Open DayZ Tools and use the "Mount P drive" command (Tools menu). `P:\` does not auto-mount across reboots.

### `[FAIL] DayZ Tools not detected`

Either DayZ Tools isn't installed, or it's installed somewhere unusual.

- Install via Steam → Library → Tools → DayZ Tools (free).
- If installed in a non-default location: set `$env:DAYZ_TOOLS_PATH` to the install root (parent of `Bin\AddonBuilder\AddonBuilder.exe`).

### `[FAIL] Vanilla DayZ data not detected on P:\`

You haven't extracted the vanilla DayZ PBOs to `P:\`. Open DayZ Tools → Extract Game Data → run the extraction. This is a one-time setup step (per Tools update).

### `[FAIL] P:\Mods\ does not exist` / `is a regular folder, not a junction` / `junction is dangling`

`P:\Mods\` must be a directory junction to `<DayZ install>\!Workshop\` so built PBOs land where the engine actually loads mods. Run:

```cmd
cmd /c rmdir P:\Mods                                                     (only if it exists as a regular folder)
cmd /c mklink /J P:\Mods "C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop"
```

Adjust the target path if your DayZ install is elsewhere. Preflight warns; build-pbo refuses to run.

### `Connection failed 0x00020005` / "The server does not support the client's current filePatching setting"

The server's `serverDZ.cfg` is missing `allowFilePatching = 1;`. The client connects with `-filePatching` enabled, and the server refuses unless the cfg explicitly allows it. `/dayz-launch-test` auto-appends `allowFilePatching = 1;` to existing `serverDZ.cfg` files that don't have it — re-running the skill should fix it. If you've manually set `allowFilePatching = 0;`, the skill leaves your value alone (you have to know what you're doing); change it to `1` yourself for diag-mode testing.

### "Mission script has no main function. PlayerConnect will stay disabled"

The server can't find a valid mission folder, so it loaded an empty/broken mission. Check that:

- `.server/<instance>/mission/` exists (default chernarus instance is created by `/dayz-add-server chernarus`).
- That folder has an `init.c` with a proper `main()` function.

`/dayz-launch-test` passes `-mission=<absolute path to .server/<instance>/mission>` so the engine doesn't look in the wrong `mpmissions/` location. If the mission copy got corrupted or partially deleted, run `/dayz-add-server <instance> --refresh-mission` to re-copy from DayZ Server install.

### `[FAIL] DayZDiag_x64.exe not found`

DayZ Diag is the diagnostic client required for mod development. It ships **alongside** the retail `DayZ_x64.exe` in your DayZ game install dir — if you have DayZ installed it should already be there. If it's not, your DayZ install may be incomplete or out of date. Verify the file integrity in Steam (Library → DayZ → Properties → Local Files → Verify). If your install is in a non-standard location, set `DAYZ_DIAG_PATH` directly to the exe path.

### `[FAIL] P:\<ModName> already exists. Refusing to scaffold`

You have a folder or junction at `P:\<ModName>\` that the skill won't clobber. Either:

- It's a real folder (move or rename it manually).
- It's a junction pointing somewhere other than `workspace/<ModName>/` (remove via `cmd /c rmdir P:\<ModName>` and re-run).

### `[FAIL] workspace\<ModName> already exists`

The scaffold already exists. Pick a different name, or `rm -rf workspace/<ModName>/` to start over (the skill will auto-clean the resulting dangling junction on the next scaffold).

### `[FAIL] Mod '<Name>' has no built PBO`

You called `/dayz-launch-test` before `/dayz-build-pbo`. Run the build first.

### Mod doesn't load in-game

Checklist:

- `/dayz-preflight` passes?
- `P:\<ModName>\` junction points at the right `workspace\<ModName>\`?
- `workspace\<ModName>\config.cpp` has a `CfgPatches\<ModName>` entry?
- `P:\Mods\@<ModName>\Addons\<ModName>.pbo` is newer than your last edit?
- Server console log (`workspace\_server-profile\server_console.log`) shows the mod loading?
- Client launch line includes `-mod=@<ModName>`?

### Junction got corrupted / `P:\<ModName>\` lost track

Quickest fix: `rm -rf workspace/<ModName>/` (back up first if there's local work), then re-run `/dayz-new-mod <ModName>`. The stale-junction auto-clean handles the orphaned junction on the re-scaffold.

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
│   │       └── dayz-conventions.md  # L2 rules every DayZ skill follows
│   └── local-memory/
│       └── dayz-author.txt          # gitignored, per-clone
├── workspace/
│   ├── <ModName>/                   # your mod source (created by /dayz-new-mod)
│   └── _server-profile/             # local test server (created by /dayz-launch-test)
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
