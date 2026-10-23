---
name: DayZ Modding Conventions (L2)
description: Layered conventions and full workflow for every DayZ-related agent and skill in this repo. Read this before authoring or running any DayZ skill.
---

# DayZ Modding Conventions (L2)

These are the Tier 2 (L2) rules. They apply to every DayZ-related agent and skill in this repo. They sit below the L1 default rules in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` and above any individual agent or skill. When a DayZ agent or skill is invoked, it reads this core file in addition to L1, plus the topic files under `conventions/` that its work touches (index at the end). Tier 3 packs for narrower work live next to this file in `.claude/skills/_shared/` and in skills' `references/` folders; `.claude/skills/_shared/README.md` indexes every pack and sets the pack layout.

## EnScript code style

All Enforce Script (`.c`) work follows `.claude/skills/_shared/enscript-style.md` (naming, `ref`/`autoptr` rules, `modded class` patterns, null checks, `IsDedicatedServer()` during load, segfault traps). Worked examples and API notes are in `.claude/skills/_shared/enscript/`. When code in `workspace/` conflicts with the style guide, the guide wins unless the user says otherwise.

## Environment

- `P:\` must be mounted by DayZ Tools before any DayZ work. Every DayZ skill that does work MUST gate on `/dayz-preflight` at the start and halt if it returns non-zero, including offline-only skills like scaffolding. Scripts do this with `gate_on_preflight()` from `.claude/skills/_shared/skill_helpers.py`. Gating first keeps the workflow uniform and catches a dismounted drive at the first action of a session, not the third.
- Exceptions to the preflight gate, each with its reason:
  - `/dayz-stop-test` only kills diag processes. It is an emergency stop that has to work when the environment is half-broken.
  - `/dayz-scope-mod` and `/dayz-record-correction` are meta-skills that edit settings and rule files, not `P:\` content.
  - `/dayz-init` runs preflight inside its own steps (the environment check and the plan it executes), so it does not gate before the wizard starts.
  - `/dayz-workdrive` mounts `P:\`, which is the thing preflight checks.
  - `/dayz-search-download` only downloads a prebuilt index into `~/.claude/`; it never reads or writes `P:\`.
  - `/dayz-ask` only reads vanilla files. It checks that `P:\` is mounted itself and needs none of the rest of preflight.
  - `/dayz-preflight` is the gate itself.
  - `/dayz-gate` gates through the scripts it runs: the build gate calls `/dayz-build-pbo` and the game gates call `/dayz-launch-test`, and both gate on preflight.
  - `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe` and `/dayz-layout-preview` only read files and write a report. The ones that read `P:\` say so themselves when it is not mounted.
  - `/dayz-upgrade-guard` reads files and writes a report, saves its snapshots under `~/.claude/dayz-upgrade-guard/`, and rebuilds the search index only with `--reindex`. It says so itself when `P:\` is not mounted.
  - `/dayz-release-pack` and `/dayz-server-kit` only read the mod's own files and write texts or a zip under `output/`.
  - `/dayz-health` and `/dayz-logwatch` only read gate results and logs.
  - `/dayz-route` only classifies the text of a request.
  - `/dayz-statusline` only edits a settings file, and the status line exists to show a broken environment.

  Every other skill that does work gates on preflight, including `/dayz-search-index` (it reads vanilla source on `P:\`). A new exception needs a stated reason here.
- DayZ Tools is installed via Steam (Tools section).
- Vanilla DayZ data is unpacked under `P:\` so configs can inherit from base classes.
- Workshop deploy folder for in-development mods: `P:\Mods\@<ModName>\Addons\`, never `output/`.
- `P:\Mods\` MUST be a directory junction to `<DayZ install>\!Workshop\`, not a regular folder. The engine and Launcher load mods from `!Workshop`; the junction lets builds deploy to the canonical `P:\Mods\@<ModName>\Addons\<ModName>.pbo` path while landing in the real workshop folder. Skills verify it with `validate_p_mods()` in `dayz-preflight/preflight.py`. Preflight creates the junction when `P:\Mods\` is absent and the game's `!Workshop\` folder is found (`mklink /J` is non-destructive and needs no admin). It fails, and changes nothing, when the existing path is the wrong shape: a real folder, a dangling junction, or a junction pointing elsewhere.

### Optional environment variables

Skills resolve paths in this order: env var, then Windows registry (DayZ Tools only), then Steam libraries and default paths. Set these only if your install lives outside the defaults.

| Variable | Points to | Used by |
|---|---|---|
| `DAYZ_TOOLS_PATH` | DayZ Tools install root (the directory containing `Bin\AddonBuilder\AddonBuilder.exe`). | Preflight, build, any skill that runs a DayZ Tools exe. |
| `DAYZ_GAME_PATH` | DayZ game install root (containing `DayZ_x64.exe` and `DayZDiag_x64.exe`). | Preflight (`P:\Mods` junction target); the diag client resolver. |
| `DAYZ_DIAG_PATH` | Direct path to `DayZDiag_x64.exe` (override for non-standard installs). | `/dayz-launch-test`. |
| `DAYZ_SERVER_PATH` | DayZ Server install root (containing `DayZServer_x64.exe`). Only its mission templates are read; testing runs diag for both ends. | `/dayz-add-server` (mission copy). |
| `DAYZ_VANILLA_DATA_PATH` | Folder on `P:\` containing the unpacked vanilla DayZ PBOs (default candidates: `P:\dz`, `P:\DZ`, `P:\dta`). | Preflight. |
| `DAYZ_WORK_DRIVE` | Folder to mount as `P:\`; else the cached path from the last mount, then DayZ Tools' `settings.ini` `[ProjectDrive] path`, then the DayZ Tools registry values. No default: with none of these, `/dayz-workdrive` fails and asks for `--path`. | `/dayz-workdrive`. |

Skills use the shared resolvers in `dayz-preflight/preflight.py` (`find_dayz_tools`, `find_dayz_game`, `find_dayz_diag`, `find_dayz_server`, `find_vanilla_data`) rather than re-implementing path discovery, so the resolution order stays the same across every skill.

## RAG index (Voyage + LanceDB)

The RAG layer (`/dayz-search-index` plus the `dayz-rag` MCP server) embeds vanilla source with Voyage AI's `voyage-code-3` model (1024 dimensions) and stores the vectors in LanceDB under `~/.claude/dayz-search-index/`. Embedding is a hosted API call, not a local model:

- It needs `VOYAGE_API_KEY=...` in `.env` at the repo root. Without it, searches fail with a "VOYAGE_API_KEY not set" error.
- Indexed file types: `.c`, `.cpp`, `.hpp`, `.h`, `.cfg`, `.layout`, `.rvmat`, `.xml`, `.json`, `.csv`. Binary formats (`.p3d`, `.paa`) are not indexed.
- `list_indexed_sources()` reports what the live index holds and when it was built.

## Project layout

- Mod source goes under `workspace/<ProjectName>/` per L1 conventions.
- Standard skeleton:
  - `config.cpp`: engine declarations (`CfgPatches`, `CfgMods`, content classes)
  - `$PBOPREFIX$`: declares the in-game path (e.g. `MyMod\Data`)
  - `scripts/`: Enforce Script (`3_Game/`, `4_World/`, `5_Mission/`)
  - `data/`: models (`.p3d`), textures (`.paa`), materials (`.rvmat`)
  - `gui/`: UI layouts (`.layout`) and controllers
  - `worlds/`: map and world data
- `/dayz-new-mod` creates a directory junction `P:\<ProjectName>\` to `workspace/<ProjectName>/` at scaffold time. AddonBuilder and the engine read from `P:\<ProjectName>\`; you edit in `workspace/<ProjectName>/`. One source of truth, no copies. Build skills verify the junction exists and never create or modify it (that is `/dayz-new-mod`'s job).
- Built `.pbo` files deploy to `P:\Mods\@<ModName>\Addons\`.

## Testing

- DayZ mods cannot be tested client-only. Every test or launch skill MUST start a local server with the same mod set alongside the client.
- Both client and server MUST be `DayZDiag_x64.exe`, not the retail binaries. Retail `DayZ_x64.exe` and `DayZServer_x64.exe` both block past the loading screen when `-filePatching` is on, and `-filePatching` is what lets the engine read raw `.cpp`/`.c` from the `P:\<ModName>\` junction. The same `DayZDiag_x64.exe` runs either end; pass `-server` for server mode.
- DayZ Diag lives in the DayZ game install next to the retail exe; resolve it with `find_dayz_diag()` in `dayz-preflight/preflight.py`. The DayZ Server Steam install (appid 223350) is only needed to copy mission templates.
- The server's `serverDZ.cfg` needs `allowFilePatching = 1;` for `-filePatching` clients to connect. Without it the connection fails with `0x00020005` ("The server does not support the client's current filePatching setting"). `/dayz-add-server` writes it into the default cfg, treating a missing, commented-out or non-1 `allowFilePatching` as missing and setting it to `allowFilePatching = 1;`. `/dayz-launch-test` and `/dayz-cot-bootstrap` refuse to launch without it.

The `.server/<instance>/` layout and setup/run split are in `conventions/server.md`.

## Vanilla source search (the search rule)

This is the single search rule for every DayZ agent and skill. Agents state it in one line and point here.

1. **Grep first** when you know the symbol or exact string (class names, method names, `class X extends Y`, a `<type name="...">` entry). `Grep` over the relevant `P:\` folder is fast and exhaustive.
2. **RAG search** (`search_dayz_source`) when the question is by meaning ("how does vanilla handle X?"), when you are hunting for an example to mirror, or after two or three greps came up empty.
3. **Cite, then verify** every hit before you rely on it (below).

Scope searches to your domain's folders (`P:\scripts\`, `P:\dz\<category>\`, `P:\gui\`, mission templates). Do not fan out across all of `P:\`; if a scoped search is empty, ask before widening.

### Tools

Each tool is exposed under two names depending on how the server is loaded: `mcp__dayz-rag__<tool>` (project server) and `mcp__plugin_agentic-z_dayz-rag__<tool>` (plugin). Agents that search list both in `tools:`.

- `search_dayz_source(query, top_k=5, file_type=None, max_distance=None)` returns chunks with `path`, `file_type`, `parent_context`, `line_start`/`line_end`, `distance` (lower is closer; `max_distance` drops hits above it), `is_stale`, and a truncated snippet. `file_type` is one of `c`, `cpp`, `hpp`, `h`, `layout`, `cfg`, `rvmat`, `xml`, `json`, `csv`, or omitted.
- `get_dayz_file(path, line_start=None, line_end=None)` fetches a file or range under `P:\` to verify a hit.
- `list_indexed_sources()` returns `{source}`: the manifest of the vanilla source index (what was indexed and when), or `null` if it has not been built.

### Cite, then verify

A search hit is a hint, not a fact. Before grounding a claim on one:

1. Fetch the cited range with `get_dayz_file` (or `Read` the `P:\` path). The snippet is truncated and the index can lag the files on disk; `is_stale=True` says so explicitly.
2. Check the code says what you think, in the form you think. Retrieval returns near-misses: a similar class on another inheritance branch, a constant nothing references.
3. If the file disagrees with the snippet, trust the file and suggest re-running `/dayz-search-index --full`.
4. Cite vanilla as `path:line_start-line_end` so the user can check it.

A single search used only to navigate does not need verifying. A single chunk treated as ground truth is the most common RAG failure.

Format answers grounded in vanilla source per `.claude/skills/_shared/answer-formatting.md`.

### When the index is unavailable

If a search returns "no index", a missing-table error, or a missing `VOYAGE_API_KEY`, say so, fall back to scoped `Grep`, and tell the user which fix applies (`/dayz-search-index --full`, or adding the key to `.env`). After a DayZ update the index goes stale; rebuild with `--full`.

## Topic files

The core above is what every DayZ agent and skill reads. Topic rules live in `.claude/skills/_shared/conventions/`; load only the ones your task touches.

| Topic file | Sections | Read by |
|---|---|---|
| `conventions/config.md` | Config conventions, `inventorySlot` string vs array (`T148506`), Bundle / umbrella mods | config-specialist, build-checker, build-engineer, mod-reviewer |
| `conventions/assets.md` | Asset conventions (texture suffixes, `.rvmat`, `.p3d`), LOD canonical resolutions | asset-specialist, object-builder, mod-reviewer, mod-architect |
| `conventions/scripts.md` | Script conventions (`scripts/` layers, `modded class` with no `extends`), Client and server ownership (which side runs what, who owns state, RPC direction, server validation) | script-specialist, workbench-specialist, mod-debugger, mod-reviewer, mod-architect |
| `conventions/ui.md` | UI scripting realities (read before any "change the X color" task) | ui-specialist, figma-to-dayz-layout, layout-validator |
| `conventions/server.md` | Server / economy, Test server instances (`.server/`), Mission and DayZ Server install notes | server-admin, map-specialist, ingame-tester, mod-debugger |

## How agents and skills reference this file

Each DayZ agent or skill includes a one-line reference near the top of its definition:

> Follow Tier 2 (`.claude/skills/_shared/dayz-conventions.md`).

Agents that search vanilla add one line for the search rule instead of restating it, for example:

> Search: Grep for known names, RAG for questions by meaning, then verify every hit (Tier 2, "Vanilla source search").

Agents that need a topic file name it on the same line, for example:

> Follow Tier 2 (`.claude/skills/_shared/dayz-conventions.md` and `conventions/config.md`).
