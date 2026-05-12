---
name: DayZ Modding Conventions (L2)
description: Layered conventions and full workflow for every DayZ-related agent and skill in this repo. Read this before authoring or running any DayZ skill.
---

# DayZ Modding Conventions (L2)

These rules apply to every DayZ-related agent and skill in this repo. They sit *below* the L1 default rules in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` and *above* any individual agent or skill. When a DayZ agent or skill is invoked, it should read this file in addition to L1.

## EnScript code style

For all Enforce Script (`.c`) work, follow these conventions: naming (`m_`/`s_` member prefixes, PascalCase methods, camelCase locals, tabs not spaces), `ref`/`autoptr` rules (members only, never on params, returns, locals, or typedefs), `modded class` patterns (no inheritance clause, that's a silent no-op), null-check semantics, `IsDedicatedServer()` over `IsClient()/IsServer()` during load, segfault traps. When code in `workspace/` conflicts with these rules, the rules win unless the user says otherwise.

## Environment

- **`P:\` drive must be mounted** by DayZ Tools before any DayZ work. **Every DayZ skill that *does* work MUST gate on `/dayz-preflight`** at the start of execution and halt if preflight returns non-zero — including offline-only skills like scaffolding. The discipline of "preflight first" keeps the workflow uniform and catches a dismounted drive at the first action of a session, not the third.
- **Abort-skill exception.** Skills that *only abort* in-flight work (currently `/dayz-stop-test` killing diag processes) do NOT gate on preflight — they're emergency escape hatches that must work even when the environment is half-broken. This is the only documented exception to the gating rule.
- DayZ Tools must be installed via Steam (Tools section).
- Vanilla DayZ data must be unpacked under `P:\` so configs can inherit from base classes.
- Workshop deploy folder for in-development mods: `P:\Mods\@<ModName>\Addons\`.
- **`P:\Mods\` MUST be a directory junction to `<DayZ install>\!Workshop\`**, not a regular folder. The DayZ engine and Launcher load mods from the `!Workshop` folder; the `P:\Mods\` junction lets builds deploy via the canonical `P:\Mods\@<ModName>\Addons\<ModName>.pbo` path while landing in the actual workshop dir. Skills MUST verify this via the shared `validate_p_mods()` resolver in `dayz-preflight/preflight.py`. The resolver **auto-creates the junction at preflight time** when `P:\Mods\` is absent and the DayZ game install (with `!Workshop\`) is locatable — `mklink /J` is non-destructive, doesn't need admin, and the target is canonical. It still hard-fails when the existing path is the wrong shape (real folder, dangling junction, or junction pointing elsewhere) so accidental damage is impossible. Never `output/`.

### Optional environment variables

Skills resolve paths in this order: env var → Windows registry (Tools only) → common-default fallback. Set these only if your install lives outside the defaults.

| Variable | Points to | Used by |
|---|---|---|
| `DAYZ_TOOLS_PATH` | DayZ Tools install root (the directory containing `Bin\AddonBuilder\AddonBuilder.exe`). | Preflight, build, any skill that invokes AddonBuilder. |
| `DAYZ_GAME_PATH` | DayZ game install root (containing `DayZ_x64.exe` and `DayZDiag_x64.exe`). | Preflight; resolver for the diag client. |
| `DAYZ_DIAG_PATH` | Direct path to `DayZDiag_x64.exe` (override for non-standard installs). | Launch-test. |
| `DAYZ_SERVER_PATH` | DayZ Server install root (containing retail `DayZServer_x64.exe`). **Not used by `/dayz-launch-test`** (which uses diag for both ends). Reserved for hypothetical future retail-server skills. | reserved |
| `DAYZ_VANILLA_DATA_PATH` | Folder on `P:\` containing the unpacked vanilla DayZ PBOs (default candidates: `P:\dz`, `P:\DZ`, `P:\dta`). | Preflight; future skills that read vanilla configs for inheritance. |
| `DAYZ_WORK_DRIVE` | Folder to mount as `P:\`. Auto-resolved from DayZ Tools' `settings.ini` `[ProjectDrive] path` if not set. | `/dayz-workdrive`. |

Skills MUST use the shared resolver helpers (`find_dayz_tools`, `find_vanilla_data` in `dayz-preflight/preflight.py`) rather than re-implementing path discovery. This keeps the resolution order consistent across the whole DayZ skill set.

## RAG embedding (local)

The RAG layer (`/dayz-search-index` + the `dayz-rag` MCP server) runs **fully locally** with `nomic-ai/CodeRankEmbed` (137M-param code-specialised model, 768-dim, top of CoIR). No API keys, no network calls, no per-query cost.

- First indexer run downloads ~280MB of model weights to the HuggingFace cache (`~/.cache/huggingface/`). After that, indexing and queries are entirely offline.
- Full index: ~7,000 chunks, builds in ~90s on a typical CPU.
- Per-query latency: ~50-150ms (local embed + numpy cosine).

DayZ Tools is the only per-machine install needed. There's no per-clone API key.

## Project layout

- Mod source goes under `workspace/<ProjectName>/` per L1 conventions.
- Standard skeleton:
  - `config.cpp` — engine declarations (`CfgPatches`, `CfgMods`, content classes)
  - `$PBOPREFIX$` — declares the in-game path (e.g. `MyMod\Data`)
  - `scripts/` — Enforce Script (`3_Game/`, `4_World/`, `5_Mission/`)
  - `data/` — models (`.p3d`), textures (`.paa`), materials (`.rvmat`)
  - `gui/` — UI layouts (`.layout`) + controllers
  - `worlds/` — map / world data
- A directory junction `P:\<ProjectName>\` → `workspace/<ProjectName>/` is created at scaffold time by `/dayz-new-mod`. AddonBuilder and the engine read from `P:\<ProjectName>\`; you edit at `workspace/<ProjectName>/`. One source of truth, no copies. Build skills MUST verify this junction exists; they MUST NOT create or modify it (that's `/dayz-new-mod`'s job).
- Built `.pbo` deploys to `P:\Mods\@<ModName>\Addons\`.

## Asset conventions

- Textures are `.paa` only, with required suffixes:
  - `_co` — color (diffuse)
  - `_nohq` — normal
  - `_smdi` — spec / mask
- Materials are `.rvmat` referencing the textures and assigning shaders.
- Models are `.p3d` exported from Object Builder.

## Config conventions

- `config.cpp` is the canonical declaration entry point.
- Use `hiddenSelections` + `hiddenSelectionsTextures` for retextures — avoid duplicating models.
- Inherit from vanilla classes — requires `P:\` vanilla data populated.

## Script conventions

- Enforce Script (DayZ's C#-like language).
- Folder modules:
  - `scripts/3_Game/` — base game logic
  - `scripts/4_World/` — world-level logic
  - `scripts/5_Mission/` — mission / server scripts
- Use `modded class Foo extends Foo { ... }` for non-destructive overrides.

## Server / economy

- `types.xml` — Central Economy spawn rates, lifetimes, locations.
- `cfgeconomycore.xml`, `cfgspawnabletypes.xml`, `events.xml` — economy structure.
- `cfggameplay.json` — runtime tuning.
- `mission/init.c` — server-side world init logic.

## Testing

- **DayZ cannot be tested standalone for mod work.** A local server MUST be loaded with the same mod set as the client. Every test/launch skill MUST start a local server alongside the client — never client-only.
- **Both client and server MUST be `DayZDiag_x64.exe`, not the retail binaries.** Retail `DayZ_x64.exe` (client) and `DayZServer_x64.exe` (server) both block past the loading screen when `-filePatching` is enabled, but `-filePatching` is required for live source iteration (so the engine reads raw `.cpp`/`.c` from the `P:\<ModName>\` junction). The same `DayZDiag_x64.exe` runs in either mode — pass `-server` for server mode.
- DayZ Diag lives in the DayZ game install dir alongside the retail exe. The DayZ Server Steam install (appid 223350) is NOT required for diag-mode testing; it's only relevant for retail-server testing (which is a separate skill if/when added).
- The shared resolver is `find_dayz_diag()` in `dayz-preflight/preflight.py` (env `DAYZ_DIAG_PATH` → DayZ game install → Steam fallbacks). Use it; do not re-implement.
- **Server `serverDZ.cfg` MUST contain `allowFilePatching = 1;`** for clients launched with `-filePatching` to connect. Without it the connection fails with `0x00020005` ("The server does not support the client's current filePatching setting"). `/dayz-launch-test` auto-bakes this into the default cfg and auto-appends it to existing cfgs that lack it.
- **Server runtime lives at `.server/<instance>/`** at the project root (not under `workspace/`). Each instance is fully self-contained:
  - `.server/<instance>/mission/`: **editable copy** of the mission folder. Created by `/dayz-add-server` on demand from DayZ Server's `mpmissions/<template>/`; user-editable thereafter (server runs with `-filePatching` so edits are live). Never edit the original DayZ Server install. Folder is named `mission/` regardless of template (the launcher pins the path explicitly via `-mission=<abspath>`).
  - `.server/<instance>/serverDZ.cfg`: per-instance server config. The `template = "..."` line links the instance to its DayZ mission base. Each instance can have totally different tuning (player count, persistence, time of day) without bleeding across instances.
  - `.server/<instance>/Profiles/`: server-side `-profiles=` dir (RPT, script.log, BattlEye state). Per-instance.
  - `.server/!ClientDiagLogs/`: client-side `-profiles=` dir. Top-level, shared across all instances (vanilla naming convention; client diag artifacts don't need per-instance isolation).
- **Instance is the unit of identity, not map.** A user can run multiple variants of the same map (chernarus vanilla vs chernarus-hardcore) by adding two instances. `serverDZ.cfg`'s `template` field is the only place the map link is encoded.
- **Setup vs run is split into two skills.** `/dayz-add-server <instance>` does setup (mission copy + per-instance cfg + profile dirs). `/dayz-launch-test <mod> --server <instance>` does run (verify + spawn). The launch skill never copies missions, never writes cfgs from scratch; it refuses with a hint to run `/dayz-add-server` if state is missing. Only mutation launch does is auto-append `allowFilePatching = 1;` to an existing cfg that lacks it.
- **Legacy `workspace/_server/` layout is no longer supported.** All three runtime skills (`/dayz-add-server`, `/dayz-launch-test`, `/dayz-clean-workspace --include-server`) refuse to run while `workspace/_server/` still exists. The user must delete the legacy folder manually before continuing; the dedicated `/dayz-migrate-server` skill that previously copied content into `.server/<instance>/` was removed in 1.4.0.
- **`.server/` is gitignored by default.** Logs, profiles, BE state, storage, and the rest of the runtime junk are not tracked. User-edited `serverDZ.cfg` and `mission/` contents are tracked via negation patterns in `.gitignore`.

## UI scripting realities (read this before any "change the X color" task)

DayZ's UI does NOT have a centralized theme system. There is no `PrimaryAccentColor` constant that flows through every widget. Reds (or any color) come from three independent places, each requiring a different override approach:

1. **`.layout` files in `P:\gui\layouts\` (100+ files).** Color attributes are baked per-widget as RGBA values. **Modded class doesn't apply** — you'd ship a same-named layout in your mod's `gui/layouts/` to override, which clobbers the entire layout (heavyweight; brittle across DayZ updates).
2. **Inline ARGB literals in `P:\scripts\5_mission\gui\` (10+ files).** Code like `widget.SetColor(0xFFD70D11)` directly applies a hex color. Override the *containing class's method* (the function that calls `SetColor`) via `modded class`, NOT the constant.
3. **`Colors` / `FadeColors` constants in `P:\scripts\3_game\colors.c`.** These look like the obvious target, but **`modded class Colors { const int X = ...; }` is a no-op for compile-time constants** — callers already baked the original value at compile time. Re-declaring in a subclass changes nothing. Worse, `COLOR_DAYZ_RED` (the most-named "DayZ red") is referenced in exactly ONE place across vanilla scripts (`mainmenupromo.c:158`), so even a working override would only recolor the main-menu promo banner.

**Implication:** "change all the red UI to blue" is not a one-file task. It requires sweeping `.layout` files (per-widget replacement) AND finding every `SetColor(<red ARGB>)` call in `5_mission/gui/` to override the containing class's method. This is hours of work, not minutes.

**This is why DayZ's CUI (Community UI Framework) exists** — it provides the centralized theme layer the engine doesn't. For new mods that need theming, build on top of CUI rather than fighting vanilla scatter. For one-off recolors, scope the task to a specific element (e.g. "the main menu hover color") rather than "all red".

When the user requests a color/theme change: ask for scope FIRST (single element vs. sweep) and warn them about the layout/script split BEFORE invoking any agent.

## Mission and DayZ Server install notes

- The launch skill passes `-mission=<absolute path to .server/<instance>/mission>` to pin the mission folder explicitly (the engine otherwise looks in the diag binary's local `mpmissions/`, which doesn't exist in the DayZ game install).
- DayZ Server install (Steam appid 223350) is **only required for the initial mission bootstrap**. After missions are copied into `.server/<instance>/mission/`, DayZ Server can be uninstalled; the workspace copy is the source of truth.

## Vanilla source recall — `search_dayz_source` MCP tool

The `dayz-rag` MCP server exposes semantic search over indexed vanilla DayZ source: `.c` (Enforce Script under `P:\scripts\`), `.layout` (GUI under `P:\gui\`), and `.cpp`/`.cfg`/`.hpp`/`.h` config blocks (under `P:\dz\` and friends). Backed by a per-user numpy + sqlite index at `~/.claude/dayz-search-index/`, built and rebuilt by `/dayz-search-index --full`. Embedding runs locally via `nomic-ai/CodeRankEmbed` — no API keys, no network calls.

**Default to Grep for code-shaped questions** (class names, symbol lookups, exact strings, inheritance trees via `class X extends Y` patterns). `Grep` over `P:\scripts\` is sub-second and exhaustive.

**When to reach for `search_dayz_source` instead:**

- "How does vanilla handle X?" questions where you don't already know the symbol name. The semantic index returns chunks ranked by *meaning*, not keyword match.
- Two or three Grep guesses already came up empty — that's the signal you don't know the right term and semantic similarity earns its slot.
- Browsing for vanilla examples to mirror (e.g. "find a vanilla layout that uses scrollbars").

**When NOT to use it:**

- You already know the exact class/symbol name and want a literal match — that's `Grep` territory.
- You need binary content (`.p3d`, `.paa`) — only text formats are indexed.
- You need files outside the indexed set (`.rvmat` materials, `types.xml`, `events.xml`, `layers.cfg`, `.json`, `.csv`) — those are excluded by design and stay `Grep` territory.

**Tool surface (from the agent's perspective):**

- `search_dayz_source(query, top_k=5, file_type=None)` — semantic search, returns chunks with `path`, `parent_context`, `line_start`/`line_end`, score, and a 1500-char snippet. `file_type` filter: `"c"` | `"cpp"` | `"hpp"` | `"h"` | `"layout"` | `"cfg"` | `None`.
- `get_dayz_file(path, line_start=None, line_end=None)` — fetch full or partial file content for follow-up after a search hit. Sandboxed to paths under `P:\`.
- `list_indexed_sources()` — manifest summary; useful to confirm what was indexed and when.

**Cite-then-verify (REQUIRED).** A `search_dayz_source` or `search_dayz_wiki` hit is a hint, not a fact. Before grounding any claim on a returned chunk:

1. Call `get_dayz_file(path, line_start, line_end)` (or use the `Read` tool directly for paths under `P:\`) to fetch the cited file at the cited range. The 1500-char snippet returned by search is truncated and the index can lag the current state on disk.
2. Verify the chunk says what you think it says, in the form you think it does. Retrieval can return results that are semantically near but functionally wrong (e.g. a similar-looking class from a different inheritance branch, or a constant that's never actually referenced anywhere).
3. If verification disagrees with the snippet, trust the file on disk. Flag the index as possibly stale and suggest the user re-run `/dayz-search-index --full` (or `/dayz-search-wiki-index --full` for wiki drift).
4. When you cite vanilla in your output, include `path:line_start-line_end` so the user can independently verify.

Skip this only when a single search call is being used for navigation/exploration, not for an authoritative answer. A single chunk treated as ground truth without follow-up is the most common RAG failure mode; two cheap calls (search + verify) prevent it.

**Setup gate:** Each DayZ specialist agent assumes the index has been built. If `search_dayz_source` returns `"no index"`, instruct the user to run `/dayz-search-index --full` first. After a DayZ update, the index goes stale — rerun with `--full` to refresh.

## Formatting answers grounded in vanilla source

When answering a DayZ question (especially RAG-grounded ones), use the full markdown surface Claude Code renders so the answer is scannable at a glance, not a wall of prose. Defaults that apply to every DayZ agent and skill:

- **Inline code for every identifier.** Class names (`PlayerBase`), method names (`OnBleedingBegin()`), file paths (`P:\scripts\3_game\dayzgame.c`), constants (`TICK_INTERVAL_SEC`), and field names (`m_BleedingBits`) all go in backticks. Bare prose names disappear in monospace; backticks make them pop.
- **Fenced code blocks for snippets, with language tags.** Use ` ```c ` for Enforce Script, ` ```cpp ` for `config.cpp`, ` ```xml ` for `types.xml`/economy files, ` ```json ` for `cfggameplay.json`. Even short 2-3 line excerpts go in a fence — syntax highlight + visual separation is the win.
- **Tables for multi-class / multi-field summaries.** When explaining a system that spans 2+ classes (e.g. `BleedingSourcesManagerBase` / `Server` / `Remote`), put their roles, key methods, and side in a table rather than three paragraphs. Same for damage-zone enumerations, inventory slot lists, gameplay-effect-widget types.
- **Numbered lists for flow.** "Damage hits → server adds bit → bit syncs → client spawns particle" is a flow, not a paragraph. Number each step. Readers can map cause/effect immediately.
- **Headers for major sections.** `##` for the top-level subject, `###` for subsystems within. Don't over-section; 3-5 headers in a normal-sized answer is the ceiling.
- **Cite `path:line_start-line_end`** inline (already required by the cite-then-verify rule above) — this also doubles as visual anchoring.
- **Do NOT paraphrase the snippet block.** The MCP tool result already shows the user the raw snippets. The follow-up answer should synthesize, contrast, or explain — not restate. Brief synthesis only.

What NOT to use: colors (not rendered), images (not rendered), HTML (escaped), collapsible sections (not supported), ANSI escapes (not supported). Stick to CommonMark + GFM.

This rule applies regardless of which DayZ agent is answering — script-specialist, ui-specialist, server-admin, debugger, reviewer, all of them.

## LOD canonical resolutions (DayZ-specific)

DayZ inherits Bohemia's `.p3d` LOD-resolution-as-tag-number scheme but uses
DIFFERENT numeric values than Arma 3 for the engine-system LODs. **Many
modding guides online quote Arma 3 values; those are WRONG for DayZ** and
will cause audit / migration scripts to misclassify LODs.

| LOD | DayZ resolution | Arma 3 (do NOT use) | Purpose |
|---|---|---|---|
| Visual | `0.0`, `1.0`, `2.0`, ... | same | LOD0 = base, then progressively simplified |
| ShadowVolume | `10000`, `11000` | same | Shadow casters |
| Geometry | `1.0e+13` | same | Physics collision |
| Memory | `1.0e+15` | same | Named memory points |
| LandContact | `2.0e+15` | same | Foot/wheel contact |
| **ViewGeometry** | **`6.0e+15`** | `7.0e+13` ❌ | Cursor / action raycast |
| **FireGeometry** | **`7.0e+15`** | `3.0e+13` ❌ | Bullet / projectile collision |

Verified against vanilla `DZ\gear\camping\wooden_case.p3d` (debinarized) — 9
LODs total, with Visual(1..4), Geometry(`1e13`), Memory(`1e15`),
LandContact(`2e15`), ViewGeo(`6e15`), FireGeo(`7e15`).

### Heads-up for any audit script

If a project's `audit_p3d.py` (or similar) `classify_lod()` function uses
thresholds like `1e13 < res < 1e14` for FireGeo, it's using **Arma 3 ranges**
and will silently misclassify DayZ ViewGeo and FireGeo as "unknown". A grep
for `7e13` or `3e13` in classification code is a quick check.

### Symptom of getting this wrong

- Bullets pass through the model (FireGeometry not recognized → no projectile
  collision shape).
- Cursor doesn't detect the model / actions don't appear (ViewGeometry not
  recognized → no raycast hit).
- Audit script reports "missing FireGeo / ViewGeo" on a model that actually
  has them, just with the resolution values the script doesn't recognize.

---

## py3d MLOD reader — `lod.facenormals` is a POOL, not per-face

When using KoffeinFlummi's `py3d` library (or any MLOD reader), a critical
detail to know:

`lod.facenormals` is a **global pool of normal vectors** for the LOD, indexed
by `vertex.normal_index`. It is NOT a per-face array.

```python
# WRONG mental model — face.facenormals[i] is NOT the normal of face[i]
for i, face in enumerate(lod.faces):
    n = lod.facenormals[i]   # ← WRONG, indexes pool not face

# CORRECT — each Vertex has point_index AND normal_index pointing into pools
for face in lod.faces:
    for v in face.vertices:
        point  = lod.points[v.point_index].coords      # (x, y, z)
        normal = lod.facenormals[v.normal_index]       # (x, y, z)
        uv     = v.uv                                   # (u, v)
```

`face.vertices[i].normal` is a property that resolves to
`lod.facenormals[v.normal_index]` for you. It returns a tuple `(x, y, z)`
directly — NOT a Vec3 object — so don't write `.coords` on it (compare with
`lod.points[i].coords` which DOES require `.coords` because points ARE Vec3
objects).

### Pool size is independent of face count

`len(lod.facenormals)` equals `num_facenormals` from the MLOD header. It is
**independent** of `len(lod.faces)`. Smoothing-group merges multiple faces
sharing a vertex normal; flat shading allocates one entry per face corner.
Audit code that asserts `len(lod.facenormals) == len(lod.faces)` will fire
spurious errors on most non-trivial models.

### Why this matters for winding / handedness checks

A common audit anti-pattern: compare `lod.facenormals[i]` to
`cross(face.vertices[1].point - face.vertices[0].point, face.vertices[2].point - face.vertices[0].point)`
to detect "winding mismatch". This breaks because:
- `facenormals[i]` is not per-face,
- and even if it were, smoothed-shaded faces have averaged corner normals
  that won't match the flat winding cross product.

The right approach is to **average the per-corner normals of one face** and
compare to the winding cross product. See the audit / winding-diagnostics
section for details.

---

## ⚠️ Vanilla bug — `inventorySlot` string vs array (`T148506`)

When a vanilla item's config declares `inventorySlot` as a **string** (single slot), trying to extend it from a mod with the `+=` array-append syntax fails silently — the mod's slot is dropped at parse time.

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

---

## Custom `Container_Base` — non-obvious requirements

Inheriting from `Container_Base` and declaring `scope = 2; model = ...` is
NOT enough for the resulting object to (a) take damage, (b) stop bullets,
or (c) appear as an interactive container. Three common omissions cause
silent failures:

### 1. `class Cargo` is mandatory (even if container is non-cargo)

Some engine builds skip container initialization entirely without it. For
containers that don't expose player cargo (loot drops via `EEKilled` etc.),
declare an empty cargo class and mark zero size:

```cpp
class MyMod_FancyContainer : Container_Base
{
    scope = 2;
    model = "\MyMod\data\fancy.p3d";

    itemsCargoSize[] = {0, 0};    // no player cargo

    class Cargo
    {
        itemsCargoSize[] = {0, 0};
        openable = 0;
        allowOwnedCargoManipulation = 0;
    };
};
```

Some builds emit an RPT warning for `itemsCargoSize[] = {0, 0}`. If yours
does, fall back to extending `Inventory_Base` and removing `class Cargo`
entirely.

### 2. `class GlobalArmor` for projectile registration

Without an armor declaration the engine may not register impacts of
projectiles, causing "bullets pass through" even when FireGeometry is
present. Damage classes inside `GlobalArmor` are keyed by `cfgAmmo` class
names (e.g. `Bullet_762x39`, `FragGrenade`, `MeleeFist`), and each entry
uses `damage = N;` not `hit = N;`:

```cpp
class GlobalArmor
{
    class FragGrenade
    {
        class Health { damage = 0; };
        class Blood  { damage = 0; };
        class Shock  { damage = 0; };
    };
    class Bullet_762x39
    {
        class Health { damage = 5; };
    };
};
```

### 3. `healthLevels[]` (modern format, not `healthLevelValues[]`)

Modern DayZ damage system uses `healthLevels[]`. It must be nested inside
`class DamageSystem > class GlobalHealth > class Health` on the entity;
declared at root level it parses but does nothing:

```cpp
// CORRECT (modern, properly nested)
class DamageSystem
{
    class GlobalHealth
    {
        class Health
        {
            healthLevels[] =
            {
                {1.0, {"\MyMod\data\fancy.rvmat"}},
                {0.7, {"\MyMod\data\fancy_dam.rvmat"}},
                {0.5, {"\MyMod\data\fancy_dest.rvmat"}},
                {0.3, {""}},
                {0.0, {""}}
            };
        };
    };
};

// AVOID (legacy, silently breaks)
healthLevelValues[] = { 1.0, 0.7, 0.5, 0.3, 0.0 };
```

Reference: vanilla `WoodenCrate` in `DZ\gear\camping\config.cpp` lines
~10074-10210 has the canonical full pattern.

---

## How agents and skills reference this file

Each DayZ agent or skill should include a one-line reference near the top of its definition:

> Follow `.claude/skills/_shared/dayz-conventions.md`.

That single line is enough — the agent/skill is expected to read this file when invoked.
