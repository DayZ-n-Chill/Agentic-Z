# DayZ Modding

The full mod lifecycle, from a fresh checkout to a running local server, is covered by a handful of slash commands. They group into three phases: set up your environment and project once, iterate on your code repeatedly, then clean up when you're done.

### Setup

The setup commands prepare your environment and your project. Most are one-time per machine or per mod, but technically you can run them again at any time. Re-running preflight verifies your environment, re-running scaffold throws an error if the project already exists (use clean first), and re-running add-map is idempotent.

<div class="cmd-table">

| Command | What it does |
|---|---|
| **`/dayz-preflight`** | Verifies the DayZ modding environment (`P:\` mounted, Tools installed, vanilla data extracted). Every other DayZ skill calls this first. |
| **`/dayz-new-mod`** | Scaffolds a new mod project under `workspace/<ModName>/` with the standard skeleton and the required `P:\<ModName>\` junction. |
| **`/dayz-add-map`** | Sets up a test map under `workspace/_server/`: copies the mission template, creates the per-map `serverDZ.cfg` + `profiles/`. Run once per map. |

</div>

### Iteration

The iteration commands are the loop you run repeatedly while building. Edit your code, build the PBO, launch the test server + client, see what happens, repeat. The stop command is your escape hatch when things hang.

<div class="cmd-table">

| Command | What it does |
|---|---|
| **`/dayz-build-pbo`** | Packs the mod into a deployable `.pbo` via DayZ Tools' AddonBuilder. |
| **`/dayz-launch-test`** | Spins up a local DayZ server with your mod loaded on the chosen map, then connects the client. Refuses if the map hasn't been added. |
| **`/dayz-stop-test`** | Force-kills any running `DayZDiag_x64.exe` processes. The emergency escape hatch. Doesn't gate on preflight, works even when the environment is broken. |

</div>

### Cleanup

The cleanup commands wipe template-managed artifacts so your repo is ready to push or you can start a project fresh. Both are scoped: they only touch what Agentic-Z scaffolded, never your subscribed mods or hand-rolled projects.

<div class="cmd-table">

| Command | What it does |
|---|---|
| **`/dayz-clean-workspace`** | Removes scaffolds and their deployed artifacts (workspace folders, junctions, `P:\Mods\@<ModName>\` deploy dirs). Match-on-scaffold rule keeps your subscribed mods safe. Pass `--include-server` to also wipe `workspace/_server/`. |
| **`/clean-repo`** | Orchestrates every cleanup skill at once for a pre-push reset. |

</div>

Every step except `/dayz-stop-test` gates on `/dayz-preflight` first, per the L2 convention at `.claude/skills/_shared/dayz-conventions.md`.

---

## Prerequisites

This guide assumes you've already done the one-time setup: DayZ, DayZ Tools, DayZ Diag, the `P:\` drive, the `P:\Mods\` junction, vanilla data extracted, Python, and (optionally) a Voyage API key for RAG. If you haven't, head to **[Prerequisites](./prerequisites)** first.

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

Scaffolds a new mod project under `workspace/&lt;ModName&gt;/` and creates the `P:\&lt;ModName&gt;\` junction so AddonBuilder and the engine can find it.

```cmd
python .claude\skills\dayz-new-mod\new_mod.py &lt;ModName&gt; [--author "YourHandle"]
```

**Argument rules:**

- `&lt;ModName&gt;` — folder name and `CfgPatches` class name. **Must start with a letter; letters, digits, underscores only; max 64 chars.** Hyphens are not allowed because the name doubles as a C-style identifier in `config.cpp` and the engine would reject the parse.
- `--author` — written into `config.cpp` as the mod author. Cached on first run. **Resolution order:**
  1. `--author` flag (also writes to cache)
  2. Cached value at `.claude/local-memory/dayz-author.txt`
  3. Interactive prompt if stdin is a TTY (writes to cache)
  4. Hard fail with instructions

**Files created:**

```
workspace/&lt;ModName&gt;/
├── config.cpp                 # CfgPatches + CfgMods stub registering the script modules
├── $PBOPREFIX$                # contains: &lt;ModName&gt;
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
P:\&lt;ModName&gt;\  ->  workspace/&lt;ModName&gt;/   (symlink, falls back to junction on Windows)
```

**Refuse rules:**

- Preflight returns non-zero (typically `P:\` not mounted).
- Name fails the pattern.
- `workspace/&lt;ModName&gt;/` already exists.
- `P:\&lt;ModName&gt;\` exists as a real folder, or as a link pointing somewhere other than `workspace/&lt;ModName&gt;/`.
- No author handle available and stdin not a TTY.

**Stale-junction auto-clean:** if `P:\&lt;ModName&gt;\` exists as a junction whose target is the about-to-be-scaffolded `workspace/&lt;ModName&gt;/` (typically because the workspace was deleted but the junction wasn't), the skill removes the stale link and proceeds. Common cleanup case after `rm -rf workspace/&lt;ModName&gt;/`.

### `/dayz-build-pbo`

Packs the mod into a deployable `.pbo` via AddonBuilder.

```cmd
python .claude\skills\dayz-build-pbo\build.py &lt;ModName&gt; [--clean]
```

**Steps performed:**

1. Preflight gate.
2. Verify `workspace/&lt;ModName&gt;/config.cpp` and `workspace/&lt;ModName&gt;/$PBOPREFIX$` exist.
3. Verify `P:\&lt;ModName&gt;\` is a link pointing at `workspace/&lt;ModName&gt;/`.
4. Resolve `AddonBuilder.exe` via `find_dayz_tools()`.
5. Ensure `P:\Mods\@&lt;ModName&gt;\Addons\` and `P:\temp\&lt;ModName&gt;\` exist.
6. Invoke `AddonBuilder.exe P:\&lt;ModName&gt; P:\Mods\@&lt;ModName&gt;\Addons -prefix=&lt;ModName&gt; -temp=P:\temp\&lt;ModName&gt; [-clear]`. AddonBuilder's stdout/stderr stream live so you see binarization progress and config errors as they happen.
7. Verify `P:\Mods\@&lt;ModName&gt;\Addons\&lt;ModName&gt;.pbo` exists and was refreshed by this build.
8. Remove the temp dir on success (kept on failure for debugging).

**`--clean` flag** passes `-clear` to AddonBuilder, wiping `P:\Mods\@&lt;ModName&gt;\Addons\` before building. Useful after large refactors or when chasing stale-asset bugs.

Default output is binarized. A `--no-binarize` flag is not exposed yet — easy to add later when iteration speed becomes a concern.

### `/dayz-launch-test`

Spins up a local development environment to test one or more built mods. **Always launches the server first**, then the client connecting to it — DayZ has no offline / single-player mode for mod testing.

```cmd
python .claude\skills\dayz-launch-test\launch.py &lt;ModName&gt; [&lt;ModName2&gt; ...] [--port N] [--dry-run]
```

**Steps performed:**

1. Preflight gate.
2. For each mod, verify `P:\Mods\@&lt;ModName&gt;\Addons\&lt;ModName&gt;.pbo` exists. Fails with a hint to run `/dayz-build-pbo` if missing.
3. Resolve `DayZDiag_x64.exe` (env `DAYZ_DIAG_PATH` → DayZ game install → Steam fallbacks). **Hard-fail if missing.** Both server and client run from the same diag binary.
4. **First-run only:** if `workspace/_server/missions/` is empty, copy missions from DayZ Server install's `mpmissions/` (resolved via `find_dayz_server`). After this initial copy, DayZ Server can be uninstalled — the workspace copy is the editable source.
5. Ensure `workspace/_server/maps/&lt;map&gt;/serverDZ.cfg` and `profiles/` exist for the selected map (default `chernarus`). Default cfg is written on first run; existing cfgs are preserved but `allowFilePatching = 1;` is auto-appended if missing.
6. Spawn the server: `DayZDiag_x64.exe -server -config=&lt;map&gt;/serverDZ.cfg -profiles=&lt;map&gt;/profiles -mission=&lt;missions&gt;/&lt;template&gt; -mod=@Mod1;@Mod2 -filePatching -port=&lt;port&gt;`. The `-mission=&lt;absolute path&gt;` flag pins the mission folder explicitly — the engine otherwise looks in the binary's local `mpmissions/`, which doesn't exist in the DayZ game install.
7. Wait 5 seconds for the server to start listening.
8. Spawn the client: `DayZDiag_x64.exe -profiles=workspace/_server/!ClientDiagLogs -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=&lt;port&gt; -filePatching`. **The client must be DayZ Diag, not retail** — retail `DayZ_x64.exe` blocks past the loading screen with `-filePatching`. The client `-profiles=` points at `workspace/_server/!ClientDiagLogs/` so all client-side diag artifacts (`Users/`, `DataCache/`, `BattlEye/`, RPT, script logs) get contained in that one folder.
9. Print both PIDs and exit. **You close both windows manually** to stop them. (A future `/dayz-stop-test` skill can manage shutdown.)

**`--map &lt;name&gt;`** selects which map to test on. Defaults to `chernarus`. Known aliases: `chernarus` → `dayzOffline.chernarusplus`, `livonia` → `dayzOffline.enoch`, `sakhal` → `dayzOffline.sakhal`. Custom missions: pass the mission folder name directly (e.g. `--map dayzOffline.namalsk`).

**`--dry-run`** prints the resolved server and client commands without launching. Useful for verifying paths and arg construction.

**`--port`** overrides the default `2302`.

**`-filePatching`** is set on both server and client so the engine reads raw `.cpp` / `.c` files from the `P:\&lt;ModName&gt;\` junction instead of only the binarized PBO. This lets you iterate on Enforce Script and configs without rebuilding the PBO every change. The PBO must still exist (the engine looks up the addon by name there) but the actual content can come from source.

---

## Mod project layout

When you scaffold `MyMod` via `/dayz-new-mod`, here's what exists and where:

```
&lt;repo&gt;/
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

DayZ Tools' AddonBuilder reads source folders from `P:\` and resolves `$PBOPREFIX$` relative to it. Our convention keeps source under `workspace/&lt;ModName&gt;/` (under git, in your editor of choice), but the engine and Tools expect to see it at `P:\&lt;ModName&gt;\`. The junction creates one source of truth that both your editor and the engine see.

- You edit files in `workspace/&lt;ModName&gt;/` like any normal repo file.
- AddonBuilder, the engine, and DayZ Tools see them at `P:\&lt;ModName&gt;\` automatically.
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
| `workspace/_server/missions/&lt;template&gt;/` | **Editable copies** of DayZ mission folders (`dayzOffline.chernarusplus`, etc.) | `/dayz-launch-test` first run (bootstrapped from DayZ Server install) |
| `workspace/_server/maps/&lt;map&gt;/` | Per-map `serverDZ.cfg` + `profiles/` (logs, BattlEye state). One folder per map you test on. | `/dayz-launch-test` first run for each map |

Override the author handle: `python .claude\skills\dayz-new-mod\new_mod.py MyMod --author "NewHandle"` (overwrites the cache) or delete `.claude/local-memory/dayz-author.txt`.

The `_server-profile/` folder is preserved across runs so logs accumulate and your `serverDZ.cfg` edits stick. If you want it gitignored in your project, add `workspace/_server/` to `.gitignore` — the skill leaves that decision to you.

---

## L2 conventions (workflow rules)

The full L2 rules live at `.claude/skills/_shared/dayz-conventions.md`. The high-level rules:

- **Every DayZ skill MUST gate on `/dayz-preflight`** at the start of execution and halt on non-zero exit. No exceptions, even for offline scaffolding skills. The discipline of "preflight first" keeps the workflow uniform and catches a dismounted drive at the first action of a session.
- **`P:\` must be mounted** by DayZ Tools before any DayZ work. Preflight enforces.
- **DayZ cannot be tested standalone.** A local server MUST be loaded with the same mod set as the client. `/dayz-launch-test` enforces; never launch the client alone for mod testing.
- **Mod source under `workspace/&lt;ModName&gt;/`**. Built `.pbo` deploys to `P:\Mods\@&lt;ModName&gt;\Addons\`. Scaffold owns the `P:\&lt;ModName&gt;\` junction; build/test skills only verify it.
- **Skills MUST use the shared resolvers** (`find_dayz_tools`, `find_dayz_game`, `find_dayz_diag`, `find_dayz_server`, `find_vanilla_data` in `dayz-preflight/preflight.py`) rather than re-implementing path discovery. Single source of truth.

---

---

## Where everything lives (ASCII map)

```
&lt;repo&gt;/
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
│   ├── &lt;ModName&gt;/                   # your mod source (created by /dayz-new-mod)
│   └── _server-profile/             # local test server (created by /dayz-launch-test)
└── docs/
    └── dayz-modding.md              # this file
```

On `P:\`:

```
P:\
├── &lt;ModName&gt;\           # junction → &lt;repo&gt;\workspace\&lt;ModName&gt;\  (created by /dayz-new-mod)
├── Mods\@&lt;ModName&gt;\Addons\&lt;ModName&gt;.pbo    # built artifact (created by /dayz-build-pbo)
├── temp\&lt;ModName&gt;\      # AddonBuilder temp (created and cleaned by /dayz-build-pbo)
└── dz\                  # vanilla DayZ data (you extract this once via DayZ Tools)
```
