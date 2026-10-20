---
name: DayZ Modding Conventions (L2)
description: Layered conventions and full workflow for every DayZ-related agent and skill in this repo. Read this before authoring or running any DayZ skill.
---

# DayZ Modding Conventions (L2)

These are the Tier 2 (L2) rules. They apply to every DayZ-related agent and skill in this repo. They sit below the L1 default rules in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` and above any individual agent or skill. When a DayZ agent or skill is invoked, it reads this file in addition to L1. Tier 3 packs for narrower work live next to this file in `.claude/skills/_shared/`.

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
  - `/dayz-search-wiki-index` is on hold; its gating is decided when it is picked up again.

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
| `DAYZ_WORK_DRIVE` | Folder to mount as `P:\`. Read from DayZ Tools' `settings.ini` `[ProjectDrive] path` if not set. | `/dayz-workdrive`. |

Skills use the shared resolvers in `dayz-preflight/preflight.py` (`find_dayz_tools`, `find_dayz_game`, `find_dayz_diag`, `find_dayz_server`, `find_vanilla_data`) rather than re-implementing path discovery, so the resolution order stays the same across every skill.

## RAG index (Voyage + LanceDB)

The RAG layer (`/dayz-search-index` plus the `dayz-rag` MCP server) embeds vanilla source with Voyage AI's `voyage-code-3` model (1024 dimensions) and stores the vectors in LanceDB under `~/.claude/dayz-search-index/`. Embedding is a hosted API call, not a local model:

- It needs `VOYAGE_API_KEY=...` in `.env` at the repo root. Without it, searches fail with a "VOYAGE_API_KEY not set" error.
- Indexed file types: `.c`, `.cpp`, `.hpp`, `.h`, `.cfg`, `.layout`, `.rvmat`, `.xml`, `.json`, `.csv`. Binary formats (`.p3d`, `.paa`) are not indexed.
- `list_indexed_sources()` reports what the live index holds and when it was built.
- The wiki index is separate and built by `/dayz-search-wiki-index --full`.

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

## Bundle / umbrella mods (pre-compiled PBOs)

Not every `workspace/<ModName>/` is buildable source. A bundle carries pre-compiled artifacts: third-party or purchased mods distributed as PBO-only, or an umbrella `@mod` collecting many pre-built PBOs under one container.

- `workspace/<ModName>/Addons/*.pbo` (+ matching `*.bisign` signatures): the pre-compiled payload.
- `workspace/<ModName>/Keys/*.bikey`: public keys; deploy to `P:\Mods\@<ModName>\Keys\`.
- Optional `meta.cpp` / `mod.cpp` at the bundle root.
- Optional linker `config.cpp` + `$PBOPREFIX$`: a content-free `CfgPatches` declaring `requiredAddons[]`, built from source like any mod.

Build and deploy are separate paths with separate gates. The `config.cpp` + `$PBOPREFIX$` requirement (and the `P:\<ModName>\` junction) applies to the build path only (`/dayz-build-pbo`, which runs AddonBuilder). The deploy path (`/dayz-deploy-pbo`) is an idempotent copy of the pre-compiled payload into `P:\Mods\@<ModName>\` and requires none of them. Both paths write the same `.agentic-z-scaffold` ownership marker; `/dayz-deploy-pbo` and `/dayz-clean-workspace` refuse to touch an existing `@<ModName>` dir that lacks it (it could be a subscribed or hand-placed mod).

Umbrella pattern: each payload PBO keeps its own prefix (baked in when it was compiled); `@<ModName>` is just the container. Never merge several mods into one re-prefixed PBO: that needs a destructive config and asset merge and breaks external `requiredAddons[]` references. A full umbrella is the built linker PBO (via `/dayz-build-pbo`) plus the copied payload (via `/dayz-deploy-pbo`) side by side under one `@<ModName>\Addons\`; deploy never deletes, so order does not matter.

## Asset conventions

- Textures are `.paa` only, with required suffixes:
  - `_co`: color (diffuse)
  - `_nohq`: normal
  - `_smdi`: spec / mask
- Materials are `.rvmat` files referencing the textures and assigning shaders.
- Models are `.p3d` files exported from Object Builder. Code that reads `.p3d` with py3d follows `.claude/skills/_shared/py3d-mlod-notes.md`.

## Config conventions

- `config.cpp` is the canonical declaration entry point.
- Use `hiddenSelections` + `hiddenSelectionsTextures` for retextures rather than duplicating models.
- Inherit from vanilla classes (requires vanilla data on `P:\`).
- Custom containers: see `.claude/skills/_shared/container-base.md` (the `class Cargo`, `GlobalArmor` and `healthLevels[]` requirements).

## Vanilla bug: `inventorySlot` string vs array (`T148506`)

When a vanilla item's config declares `inventorySlot` as a **string** (single slot), trying to extend it from a mod with the `+=` array-append syntax fails silently: the mod's slot is dropped at parse time.

```cpp
// Vanilla (DZ\gear\camping\config.cpp ~ line 10074):
class WoodenCrate : Inventory_Base
{
    inventorySlot = "WoodenCrate";       // STRING, not array
};

// FAILS silently — append to a string isn't valid:
class MyMod_FancyCrate : WoodenCrate
{
    inventorySlot[] += {"MyMod_CustomSlot"};
};

// FIX — redeclare as an explicit array, including the original value:
class MyMod_FancyCrate : WoodenCrate
{
    inventorySlot[] = {"WoodenCrate", "MyMod_CustomSlot"};
};
```

Bohemia ticket: `T148506`. The bug is "won't fix"; the workaround is mandatory. Symptom: attachment slot just doesn't accept the modded item, no RPT error, no script error.

## Script conventions

- Enforce Script (DayZ's C#-like language), styled per `enscript-style.md`.
- Folder modules:
  - `scripts/3_Game/`: base game logic
  - `scripts/4_World/`: world-level logic
  - `scripts/5_Mission/`: mission / server scripts
- Use `modded class Foo { ... }` for non-destructive overrides, with NO `extends` clause. `modded class Foo extends Foo` compiles but is a silent no-op.

## Server / economy

- `types.xml`: Central Economy spawn rates, lifetimes, locations.
- `cfgeconomycore.xml`, `cfgspawnabletypes.xml`, `events.xml`: economy structure.
- `cfggameplay.json`: runtime tuning.
- `mission/init.c`: server-side world init logic.

## Testing

- DayZ mods cannot be tested client-only. Every test or launch skill MUST start a local server with the same mod set alongside the client.
- Both client and server MUST be `DayZDiag_x64.exe`, not the retail binaries. Retail `DayZ_x64.exe` and `DayZServer_x64.exe` both block past the loading screen when `-filePatching` is on, and `-filePatching` is what lets the engine read raw `.cpp`/`.c` from the `P:\<ModName>\` junction. The same `DayZDiag_x64.exe` runs either end; pass `-server` for server mode.
- DayZ Diag lives in the DayZ game install next to the retail exe; resolve it with `find_dayz_diag()` in `dayz-preflight/preflight.py`. The DayZ Server Steam install (appid 223350) is only needed to copy mission templates.
- The server's `serverDZ.cfg` needs `allowFilePatching = 1;` for `-filePatching` clients to connect. Without it the connection fails with `0x00020005` ("The server does not support the client's current filePatching setting"). `/dayz-launch-test` writes it into the default cfg and appends it to existing cfgs that lack it.
- Server runtime lives at `.server/<instance>/` at the project root (not under `workspace/`). Each instance is self-contained:
  - `.server/<instance>/mission/`: editable copy of the mission folder, created by `/dayz-add-server` from DayZ Server's `mpmissions/<template>/` and edited by the user after that (the server runs with `-filePatching`, so edits are live). Never edit the original DayZ Server install. The folder is named `mission/` whatever the template; the launcher passes `-mission=<abspath>`.
  - `.server/<instance>/serverDZ.cfg`: per-instance server config. Its `template = "..."` line links the instance to its mission base, so instances can differ in player count, persistence or time of day.
  - `.server/<instance>/Profiles/`: server `-profiles=` dir (RPT, script.log, BattlEye state).
  - `.server/!ClientDiagLogs/`: client `-profiles=` dir, shared by all instances.
- The instance, not the map, is the unit of identity: two instances can run variants of the same map (chernarus and chernarus-hardcore).
- Setup and run are separate skills. `/dayz-add-server <instance>` copies the mission, writes the cfg and creates the profile dirs. `/dayz-launch-test <mod> --server <instance>` verifies and launches; it never copies missions or writes cfgs from scratch, and refuses with a hint to run `/dayz-add-server` when state is missing. Its only write is appending `allowFilePatching = 1;` to a cfg that lacks it.
- The legacy `workspace/_server/` layout is not supported. `/dayz-add-server`, `/dayz-launch-test` and `/dayz-clean-workspace --include-server` refuse to run while it exists; the user deletes it manually.
- `.server/` is gitignored except the user-edited `serverDZ.cfg` and `mission/` contents, which `.gitignore` negation patterns keep tracked.

## UI scripting realities (read before any "change the X color" task)

DayZ's UI has no central theme system; no `PrimaryAccentColor` constant flows through every widget. A color comes from three independent places, each overridden differently:

1. `.layout` files in `P:\gui\layouts\` (100+ files). Colors are baked per widget as RGBA values. `modded class` does not apply; overriding means shipping a same-named layout in your mod's `gui/layouts/`, which replaces the whole layout and is brittle across DayZ updates.
2. Inline ARGB literals in `P:\scripts\5_mission\gui\` (10+ files), such as `widget.SetColor(0xFFD70D11)`. Override the containing class's method with `modded class`, not the constant.
3. `Colors` / `FadeColors` constants in `P:\scripts\3_game\colors.c`. `modded class Colors { const int X = ...; }` is a no-op for compile-time constants, because callers baked the original value at compile time. `COLOR_DAYZ_RED` is referenced in one place across vanilla scripts (`mainmenupromo.c:158`), so even a working override would only recolor the main-menu promo banner.

So "change all the red UI to blue" is not a one-file task: it means sweeping `.layout` files per widget and overriding every class method that calls `SetColor(<red ARGB>)` in `5_mission/gui/`. That is hours of work. For new mods that need theming, build on CUI (Community UI Framework), which supplies the theme layer the engine lacks; for one-off recolors, scope the task to one element.

When the user asks for a color or theme change, ask for scope first (single element or sweep) and warn about the layout/script split before invoking any agent.

## Mission and DayZ Server install notes

- The launch skill passes `-mission=<absolute path to .server/<instance>/mission>` to pin the mission folder (otherwise the engine looks in the diag binary's local `mpmissions/`, which does not exist in the game install).
- DayZ Server (Steam appid 223350) is only needed for the initial mission copy. After that it can be uninstalled; the `.server/<instance>/mission/` copy is the source of truth.

## Vanilla source search (the search rule)

This is the single search rule for every DayZ agent and skill. Agents state it in one line and point here.

1. **Grep first** when you know the symbol or exact string (class names, method names, `class X extends Y`, a `<type name="...">` entry). `Grep` over the relevant `P:\` folder is fast and exhaustive.
2. **RAG search** (`search_dayz_source`, or `search_dayz_wiki` for the community wiki) when the question is by meaning ("how does vanilla handle X?"), when you are hunting for an example to mirror, or after two or three greps came up empty.
3. **Cite, then verify** every hit before you rely on it (below).

Scope searches to your domain's folders (`P:\scripts\`, `P:\dz\<category>\`, `P:\gui\`, mission templates). Do not fan out across all of `P:\`; if a scoped search is empty, ask before widening.

### Tools

Each tool is exposed under two names depending on how the server is loaded: `mcp__dayz-rag__<tool>` (project server) and `mcp__plugin_agentic-z_dayz-rag__<tool>` (plugin). Agents that search list both in `tools:`.

- `search_dayz_source(query, top_k=5, file_type=None, max_distance=None)` returns chunks with `path`, `parent_context`, `line_start`/`line_end`, `distance` (lower is closer), `is_stale`, and a truncated snippet. `file_type` is one of `c`, `cpp`, `hpp`, `h`, `layout`, `cfg`, `rvmat`, `xml`, `json`, `csv`, or omitted.
- `search_dayz_wiki(query, top_k=5)` searches the Bohemia community wiki (DayZ categories).
- `get_dayz_file(path, line_start=None, line_end=None)` fetches a file or range under `P:\` to verify a hit.
- `list_indexed_sources()` returns `{source, wiki}`: the manifest of the vanilla source index and of the wiki index (what was indexed and when), with `null` for an index that has not been built.

### Cite, then verify

A search hit is a hint, not a fact. Before grounding a claim on one:

1. Fetch the cited range with `get_dayz_file` (or `Read` the `P:\` path). The snippet is truncated and the index can lag the files on disk; `is_stale=True` says so explicitly.
2. Check the code says what you think, in the form you think. Retrieval returns near-misses: a similar class on another inheritance branch, a constant nothing references.
3. If the file disagrees with the snippet, trust the file and suggest re-running `/dayz-search-index --full` (or `/dayz-search-wiki-index --full` for the wiki).
4. Cite vanilla as `path:line_start-line_end` so the user can check it.

A single search used only to navigate does not need verifying. A single chunk treated as ground truth is the most common RAG failure.

### When the index is unavailable

If a search returns "no index", a missing-table error, or a missing `VOYAGE_API_KEY`, say so, fall back to scoped `Grep`, and tell the user which fix applies (`/dayz-search-index --full`, `/dayz-search-wiki-index --full`, or adding the key to `.env`). After a DayZ update the index goes stale; rebuild with `--full`.


Format answers grounded in vanilla source per `.claude/skills/_shared/answer-formatting.md`.

## LOD canonical resolutions (DayZ-specific)

DayZ inherits Bohemia's `.p3d` scheme where a LOD's resolution value is its type tag, but some engine-system LODs use different numbers than Arma 3. Many online guides quote Arma 3 values; those misclassify DayZ LODs.

| LOD | DayZ resolution | Arma 3 | Purpose |
|---|---|---|---|
| Visual | `0.0`, `1.0`, `2.0`, ... | same | LOD0 = base, then progressively simplified |
| ShadowVolume | `10000`, `11000` (range 10000 to 19999) | same | Shadow casters |
| Geometry | `1.0e+13` | same | Physics collision |
| Memory | `1.0e+15` | same | Named memory points |
| LandContact | `2.0e+15` | same | Foot/wheel contact |
| ViewGeometry | `6.0e+15` | `7.0e+13` (wrong for DayZ) | Cursor / action raycast |
| FireGeometry | `7.0e+15` | `3.0e+13` (wrong for DayZ) | Bullet / projectile collision |

Verified against vanilla `DZ\gear\camping\wooden_case.p3d` (debinarized): 9 LODs, with Visual(1..4), Geometry(`1e13`), Memory(`1e15`), LandContact(`2e15`), ViewGeo(`6e15`), FireGeo(`7e15`). `classify_lod()` in `.claude/skills/dayz-p3d-audit/scripts/audit_p3d.py` uses these values.

A `classify_lod()` that uses Arma 3 ranges (a grep for `7e13` or `3e13` finds them) reports ViewGeo and FireGeo as unknown. Symptoms in game: bullets pass through the model (FireGeometry not recognized), the cursor does not detect the model and actions do not appear (ViewGeometry not recognized), and audits report "missing FireGeo / ViewGeo" on models that have them.

## How agents and skills reference this file

Each DayZ agent or skill includes a one-line reference near the top of its definition:

> Follow Tier 2 (`.claude/skills/_shared/dayz-conventions.md`).

Agents that search vanilla add one line for the search rule instead of restating it, for example:

> Search: Grep for known names, RAG for questions by meaning, then verify every hit (Tier 2, "Vanilla source search").
