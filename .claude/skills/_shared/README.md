# Knowledge packs

A knowledge pack is Tier 3 reference material: notes, API tables and worked examples for one kind of work. Any DayZ worker may load any pack for one task. Packs are loaded only when the task needs them, never by default. Tier 1 (`CLAUDE.md`) and Tier 2 (`dayz-conventions.md` plus `conventions/*.md`) still apply on top of every pack.

This file is the one index of every pack. Paths are relative to `.claude/skills/`. The repo integrity test (`scripts/dev/test_repo_integrity.py`) fails when a pack folder or pack file is missing from this index, or when the index names a file that does not exist.

## Pack layout

- **Where a pack lives.** A pack shared by several agents lives under `_shared/`, either as one file (`_shared/<topic>.md`) or as a folder (`_shared/<topic>/`). A pack that belongs to one skill or one specialist lives in that skill's own `references/` folder (`<skill>/references/`). Use the plural `references/`. One older folder, `dayz-search-index/reference`, predates this rule.
- **File naming.** Lowercase, words joined with `-` or `_` to match the neighbouring files, ending in `.md`. Name the file after its subject (`ptc-format-reference.md`, `singleton.md`), not after a ticket or a date.
- **Front index.** Every pack folder has one front index that says which file to open for which question. For a `_shared/` folder it is the folder's `README.md`; for a skill's `references/` folder it is the table in that skill's `SKILL.md`. Each pack file opens with a title and one line saying what it covers.
- **Loaded only when needed.** Agents and skills name the pack file they need at the step that needs it. They never tell a worker to read a whole pack up front.
- **Checked against vanilla.** Facts about the game cite the vanilla file on `P:\` they came from, so a reviewer can check them.
- **Registered here.** A new pack gets a row in this index in the same change.

## Index

### Shared single file packs

| Pack | Purpose |
|---|---|
| `_shared/enscript-style.md` | Enforce Script code style: naming, `ref` and `autoptr`, null checks, `modded class` patterns, segfault traps. Every script task. |
| `_shared/answer-formatting.md` | How to format answers grounded in vanilla source. |
| `_shared/container-base.md` | Custom `Container_Base` config requirements (damage, bullets, interaction). |
| `_shared/figma-to-dayz-rules.md` | Translation rules for the Figma to DayZ `.layout` pipeline. |
| `_shared/py3d-mlod-notes.md` | Reading MLOD `.p3d` files with py3d, used by `/dayz-p3d-audit`. |

### Enforce Script pack (`_shared/enscript`)

Front index: `_shared/enscript/README.md`, which also has a symptom to file table for debugging.

| Folder | Purpose |
|---|---|
| `_shared/enscript/patterns` | Recurring implementation patterns. |
| `_shared/enscript/integrations` | Outside frameworks and vanilla systems. |
| `_shared/enscript/references` | API surface by topic. |
| `_shared/enscript/examples` | Complete `.c` and `.layout` files to start from. |

| File | Purpose |
|---|---|
| `_shared/enscript/patterns/modded_class.md` | `modded class` rules: `super`, no `extends`, `NO_GUI` guard, engine classes that cannot be modded. |
| `_shared/enscript/patterns/netsync.md` | Net sync variables, `SetSynchDirty`, `OnVariablesSynchronized`, bit packing. |
| `_shared/enscript/patterns/persistence.md` | `OnStoreSave` and `OnStoreLoad`, version header, write order. |
| `_shared/enscript/patterns/rpc.md` | RPC IDs, `ScriptRPC`, the `OnRPC` template, client to server validation. |
| `_shared/enscript/patterns/singleton.md` | Static instance with lazy init, `GetInstance()`, the `ScriptInvoker` shutdown null guard. |
| `_shared/enscript/patterns/actions.md` | Action classes, condition components, stopping pickup, client and server check mismatch. |
| `_shared/enscript/patterns/scheduler.md` | `CallLater` overflow after about 4.5 hours, per tick allocation, call categories. |
| `_shared/enscript/patterns/physics_items.md` | Making spawned items physics active: `ThrowPhysically` or manual dynamic physics. |
| `_shared/enscript/patterns/json_config_migration.md` | JSON config schema versions and forward migration. |
| `_shared/enscript/patterns/language_workarounds.md` | Missing language features (ternary, type inference, lambdas, exceptions, overloading) and their workarounds. |
| `_shared/enscript/integrations/community_framework.md` | Community Framework modules, storage, event bus. |
| `_shared/enscript/integrations/dabs_framework.md` | DABS attribute actions and MVC layouts. |
| `_shared/enscript/integrations/vanilla_plugins.md` | Vanilla `PluginBase` lifecycle and `GetPlugin()`. |
| `_shared/enscript/integrations/central_economy.md` | Central Economy XML and runtime spawning. |
| `_shared/enscript/integrations/input_bindings.md` | `inputs.xml`, `UAInput`, context guards. |
| `_shared/enscript/references/types_collections.md` | Primitive types, strings, arrays, maps, sets, vectors, `Math`. |
| `_shared/enscript/references/player_api.md` | `PlayerBase` stats, vitals, agents, modifiers, inventory. |
| `_shared/enscript/references/item_api.md` | `ItemBase` quantity, health, actions, spawning, config properties. |
| `_shared/enscript/references/game_api.md` | `GetGame()`, world, mission, object creation, logging. |
| `_shared/enscript/references/erpc_defines.md` | Vanilla RPC, agent and modifier ID tables; custom ID ranges. |
| `_shared/enscript/references/file_paths.md` | `$profile` and `$saves` paths, file and JSON helpers. |
| `_shared/enscript/references/gui_layout.md` | `.layout` format and every widget type. |

### Wearables pack (`_shared/wearables`)

Front index: `_shared/wearables/README.md`. Written for `dayz-wearables-specialist`.

| Folder or file | Purpose |
|---|---|
| `_shared/wearables/references` | Clothing, gear and character reference, checked against vanilla. |
| `_shared/wearables/references/classes-and-parents.md` | Config and script class trees, picking the vanilla parent, `requiredAddons[]` per folder. |
| `_shared/wearables/references/slots-and-cargo.md` | Player slots, `inventorySlot[]`, cargo against attachments, exclusion flags, visibility. |
| `_shared/wearables/references/protection-and-insulation.md` | `heatIsolation` factors, `varWetMax`, armor, filter protection, repair kit types. |
| `_shared/wearables/references/color-variants.md` | Hidden selections per model, one texture per selection, `personality`, script texture calls. |
| `_shared/wearables/references/models-and-proxies.md` | Ground and worn models, body and gear proxies, head hiding, notes for Object Builder. |
| `_shared/wearables/references/characters.md` | Survivor classes, body parts and heads, how a character reaches the list. |

### Skill packs (`references/`)

| Folder or file | Purpose |
|---|---|
| `dayz-particles/references` | Particle pack. Front index: `dayz-particles/SKILL.md`. |
| `dayz-particles/references/ptc-format-reference.md` | Every `.ptc` emitter property and curve. |
| `dayz-particles/references/emat-format-reference.md` | `.emat` particle material format and vanilla materials. |
| `dayz-particles/references/script-api-reference.md` | Playing, stopping and tuning particles from script. |
| `dayz-particles/references/integration-patterns.md` | Wiring particles into a device. |
| `dayz-particles/references/vanilla-particle-catalog.md` | Every vanilla particle in `ParticleList`. |
| `dayz-p3d-audit/references` | Model audit pack. Front index: `dayz-p3d-audit/SKILL.md`. |
| `dayz-p3d-audit/references/p3d-killers.md` | Model faults that break a `.p3d` with no engine error. |
| `dayz-p3d-audit/references/winding-methodology.md` | How to verify face winding. |
| `dayz-p3d-audit/references/config-rvmat-checks.md` | `config.cpp` and `.rvmat` checks for models. |
| `dayz-search-index/reference` | Search index notes. Front index: `dayz-search-index/SKILL.md`. |
| `dayz-search-index/reference/cost-and-free-tier.md` | Voyage embedding cost and the free tier check. |

### Not file packs

- Vanilla source search is the `dayz-rag` MCP server, not a file. Its rules are in `dayz-conventions.md` ("Vanilla source search").
- Tier 2 topic rules live in `conventions/` and are listed in `dayz-conventions.md`, not here.
