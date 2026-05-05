---
name: DayZ Modding Conventions (L2)
description: Layered conventions and full workflow for every DayZ-related agent and skill in this repo. Read this before authoring or running any DayZ skill.
---

# DayZ Modding Conventions (L2)

These rules apply to every DayZ-related agent and skill in this repo. They sit *below* the L1 default rules in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` and *above* any individual agent or skill. When a DayZ agent or skill is invoked, it should read this file in addition to L1.

## EnScript code style

For all Enforce Script (`.c`) work, follow the **[EnScript Style Guide](enscript-style.md)** sitting alongside this file. It's the authoritative source for naming (`m_`/`s_`, PascalCase methods, camelCase locals, tabs), `ref`/`autoptr` rules (members only — never on params, returns, locals, or typedefs), `modded class` patterns (no inheritance clause), null-check semantics, `IsDedicatedServer()` over `IsClient()/IsServer()` during load, segfault traps, and more. When code in `workspace/` conflicts with that guide, the guide wins unless the user says otherwise.

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

The RAG layer (`/dayz-rag-index` + the `dayz-rag` MCP server) runs **fully locally** with `nomic-ai/CodeRankEmbed` (137M-param code-specialised model, 768-dim, top of CoIR). No API keys, no network calls, no per-query cost.

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
- **Server staging area lives at `workspace/_server/`**, with two subtrees and the client profile at the root:
  - `workspace/_server/missions/<mission-template>/` — **editable copies** of mission folders (e.g. `dayzOffline.chernarusplus/`). Created by `/dayz-add-map` on demand from DayZ Server's `mpmissions/`; user-editable thereafter (server runs with `-filePatching` so edits are live). Never edit the original DayZ Server install.
  - `workspace/_server/maps/<map-name>/` — per-map `serverDZ.cfg` + `profiles/`. Created by `/dayz-add-map`. Each map (chernarus, livonia, sakhal, custom) has its own config + server-side log/BattlEye state so tuning doesn't bleed across maps.
  - `workspace/_server/!ClientDiagLogs/` is the **client `-profiles=` directory**. All client-side diag artifacts (`Users/`, `DataCache/`, `BattlEye/`, RPT logs, script logs) get contained in that one folder rather than spreading across the `_server` root or polluting the DayZ game install dir.
- **Setup vs run is split into two skills.** `/dayz-add-map <map>` does setup (mission copy + per-map cfg + profiles). `/dayz-launch-test <mod> --map <map>` does run (verify + spawn). The launch skill never copies missions, never writes cfgs from scratch — it refuses with a hint to run `/dayz-add-map` if state is missing. Only mutation launch does is auto-append `allowFilePatching = 1;` to an existing cfg that lacks it.
- **Never gitignore `workspace/_server/` template-wide.** It's a per-clone decision: some users want their tuned cfgs and edited missions tracked in their project's git, others don't. The template doesn't enforce.

## UI scripting realities (read this before any "change the X color" task)

DayZ's UI does NOT have a centralized theme system. There is no `PrimaryAccentColor` constant that flows through every widget. Reds (or any color) come from three independent places, each requiring a different override approach:

1. **`.layout` files in `P:\gui\layouts\` (100+ files).** Color attributes are baked per-widget as RGBA values. **Modded class doesn't apply** — you'd ship a same-named layout in your mod's `gui/layouts/` to override, which clobbers the entire layout (heavyweight; brittle across DayZ updates).
2. **Inline ARGB literals in `P:\scripts\5_mission\gui\` (10+ files).** Code like `widget.SetColor(0xFFD70D11)` directly applies a hex color. Override the *containing class's method* (the function that calls `SetColor`) via `modded class`, NOT the constant.
3. **`Colors` / `FadeColors` constants in `P:\scripts\3_game\colors.c`.** These look like the obvious target, but **`modded class Colors { const int X = ...; }` is a no-op for compile-time constants** — callers already baked the original value at compile time. Re-declaring in a subclass changes nothing. Worse, `COLOR_DAYZ_RED` (the most-named "DayZ red") is referenced in exactly ONE place across vanilla scripts (`mainmenupromo.c:158`), so even a working override would only recolor the main-menu promo banner.

**Implication:** "change all the red UI to blue" is not a one-file task. It requires sweeping `.layout` files (per-widget replacement) AND finding every `SetColor(<red ARGB>)` call in `5_mission/gui/` to override the containing class's method. This is hours of work, not minutes.

**This is why DayZ's CUI (Community UI Framework) exists** — it provides the centralized theme layer the engine doesn't. For new mods that need theming, build on top of CUI rather than fighting vanilla scatter. For one-off recolors, scope the task to a specific element (e.g. "the main menu hover color") rather than "all red".

When the user requests a color/theme change: ask for scope FIRST (single element vs. sweep) and warn them about the layout/script split BEFORE invoking any agent.

## Mission and DayZ Server install notes

- The launch skill passes `-mission=<absolute path to workspace/_server/missions/<template>>` to pin the mission folder explicitly (the engine otherwise looks in the diag binary's local `mpmissions/`, which doesn't exist in the DayZ game install).
- DayZ Server install (Steam appid 223350) is **only required for the initial mission bootstrap**. After missions are copied to `workspace/_server/missions/`, DayZ Server can be uninstalled — the workspace copy is the source of truth.

## Vanilla source recall — `search_dayz_source` MCP tool

The `dayz-rag` MCP server exposes semantic search over indexed vanilla DayZ source: `.c` (Enforce Script under `P:\scripts\`), `.layout` (GUI under `P:\gui\`), and `.cpp`/`.cfg`/`.hpp`/`.h` config blocks (under `P:\dz\` and friends). Backed by a per-user numpy + sqlite index at `~/.claude/dayz-rag-index/`, built and rebuilt by `/dayz-rag-index --full`. Embedding runs locally via `nomic-ai/CodeRankEmbed` — no API keys, no network calls.

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
3. If verification disagrees with the snippet, trust the file on disk. Flag the index as possibly stale and suggest the user re-run `/dayz-rag-index --full` (or `/dayz-rag-wiki-index --full` for wiki drift).
4. When you cite vanilla in your output, include `path:line_start-line_end` so the user can independently verify.

Skip this only when a single search call is being used for navigation/exploration, not for an authoritative answer. A single chunk treated as ground truth without follow-up is the most common RAG failure mode; two cheap calls (search + verify) prevent it.

**Setup gate:** Each DayZ specialist agent assumes the index has been built. If `search_dayz_source` returns `"no index"`, instruct the user to run `/dayz-rag-index --full` first. After a DayZ update, the index goes stale — rerun with `--full` to refresh.

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

## Dynamic items — `ThrowPhysically` vs manual `CreateDynamicPhysics`

For items with `simulation = "inventoryItem"` and `physLayer = "item"`, the
`ECE_CREATEPHYSICS` flag of `CreateObjectEx` creates the **collision shape**
but leaves the rigid body **static / kinematic**. Calling
`dBodyApplyImpulse` on a static body silently no-ops — common symptom is
"item appears frozen in air after spawn".

### Preferred pattern — `ThrowPhysically`

The vanilla helper at `P:\scripts\3_game\entities\inventoryitem.c:26`:

```c
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true);
```

Internally calls `CreateDynamicPhysics(ITEM_LARGE)`,
`SetDynamicPhysicsLifeTime(...)`, and applies `force` as an impulse. This is
the pattern vanilla itself uses — see
`P:\scripts\4_world\static\miscgameplayfunctions.c` lines 1188 / 1204 / 1212
for examples.

```c
EntityAI spawned = GetGame().CreateObjectEx("MyMod_Item", pos, ECE_CREATEPHYSICS|ECE_UPDATEPATHGRAPH);
ItemBase ib = ItemBase.Cast(spawned);
if (ib)
    ib.ThrowPhysically(null, impulse, false);
```

### Manual pattern — when you need finer control

If you need to drive lifetime, gravity, or interaction layer explicitly:

```c
obj.CreateDynamicPhysics(PhxInteractionLayers.DYNAMICITEM);
obj.EnableDynamicCCD(true);
obj.SetDynamicPhysicsLifeTime(20.0);     // without this, engine sleeps the body
dBodyEnableGravity(obj, true);
dBodyApplyImpulse(obj, impulse);
```

Verified APIs:

- `P:\scripts\3_game\entities\object.c:462-464` — `CreateDynamicPhysics`,
  `EnableDynamicCCD`, `SetDynamicPhysicsLifeTime`.
- `P:\scripts\3_game\global\dayzphysics.c:1-29` — `PhxInteractionLayers` enum
  (`DYNAMICITEM`, `DYNAMICITEM_NOCHAR`, ...).
- `P:\scripts\1_core\proto\enphysics.c:64-69, 141` — `dBodyDynamic`,
  `dBodyEnableGravity`, `dBodyApplyImpulse`.
- `P:\scripts\4_world\entities\itembase.c:4530` — `StopItemDynamicPhysics`
  reduces `SetDynamicPhysicsLifeTime` to `0.01` to "park" the body.

The `SetDynamicPhysicsLifeTime` call is mandatory — without it the engine
sleeps the body within a few ticks and the impulse is lost mid-flight.

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

## Schema migration for admin-tunable JSON configs

Mods that ship JSON config files (`cfggameplay.json`-style: admin opens it,
edits values, restarts server) need a forward-compatible migration story.
Otherwise: admin runs old JSON against new mod, missing fields → either
crashes or silently uses default-of-default → admin reports "feature gone"
that's actually just unset.

### Pattern

```c
class MyMod_Settings
{
    static const int SCHEMA_VERSION = 3;

    int    version;            // sentinel; 0 = "not loaded yet"
    string serverName;
    int    maxPlayers;
    ref array<string> allowedKits;

    // Constructor: minimal scalar defaults + empty arrays so the JSON
    // serializer never sees null members.
    void MyMod_Settings()
    {
        version = 0;
        serverName = "";
        maxPlayers = 0;
        allowedKits = new array<string>;
    }

    // Defaults() is separate so it can be called at fresh-install time AND
    // re-used at migration time to source new-field default values.
    void Defaults()
    {
        serverName = "Untitled Server";
        maxPlayers = 60;
        allowedKits.Clear();
        allowedKits.Insert("StarterKit_Basic");
        version = SCHEMA_VERSION;
    }
}

static MyMod_Settings LoadOrCreate(string path)
{
    MyMod_Settings cfg = new MyMod_Settings;

    if (!FileExist(path))
    {
        cfg.Defaults();
        SaveToDisk(cfg, path);
        return cfg;
    }

    if (!JsonFileLoader<MyMod_Settings>.JsonLoadFile(path, cfg))
    {
        // Parse failed — admin probably has a typo. DO NOT overwrite;
        // log + return defaults in memory only.
        cfg.Defaults();
        Print("[MyMod] settings JSON failed to parse — using in-memory defaults; not overwriting");
        return cfg;
    }

    if (cfg.version < MyMod_Settings.SCHEMA_VERSION)
    {
        // Forward migration. Build a fresh defaults instance and copy in
        // only the NEW fields that didn't exist in the old version.
        MyMod_Settings fresh = new MyMod_Settings;
        fresh.Defaults();

        if (cfg.version < 2)
        {
            // Field added in v2:
            cfg.maxPlayers = fresh.maxPlayers;
        }
        if (cfg.version < 3)
        {
            // Field added in v3:
            cfg.allowedKits = fresh.allowedKits;
        }

        cfg.version = MyMod_Settings.SCHEMA_VERSION;
        SaveToDisk(cfg, path);
        Print("[MyMod] migrated settings v" + cfg.version + " → v" + MyMod_Settings.SCHEMA_VERSION);
    }

    return cfg;
}
```

### Rules of thumb

- Bump `SCHEMA_VERSION` whenever you add a field. Don't bump for behavior
  changes that don't change the JSON shape.
- Constructor stays minimal — just enough so the serializer doesn't choke on
  null members. All "didactic example" defaults live in `Defaults()`.
- On parse failure, DO NOT overwrite the file. The admin may be mid-edit
  with a typo. Use defaults in memory only and log loudly.
- Migration is incremental: each `if (cfg.version < N)` block patches in only
  the fields added at version N.

Reference pattern: `salutesh/DayZ-Expansion-Scripts/ExpansionGarageSettings.c::OnLoad`
uses an equivalent approach.

---

## How agents and skills reference this file

Each DayZ agent or skill should include a one-line reference near the top of its definition:

> Follow `.claude/skills/_shared/dayz-conventions.md`.

That single line is enough — the agent/skill is expected to read this file when invoked.
