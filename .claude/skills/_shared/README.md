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
| `_shared/enscript/patterns/language_workarounds.md` | Missing language features (ternary, lambdas, exceptions, overloading) and their workarounds; `auto` type inference. |
| `_shared/enscript/integrations/community_framework.md` | Community Framework modules, storage, event bus. |
| `_shared/enscript/integrations/dabs_framework.md` | Dabs Framework (third party): attributes, `ScriptView` and `ViewController` MVC, layout bindings, `ScriptViewMenu`. Checked against the mod's own scripts. |
| `_shared/enscript/integrations/vanilla_plugins.md` | Vanilla `PluginBase` lifecycle and `GetPlugin()`. |
| `_shared/enscript/integrations/central_economy.md` | Central Economy XML and runtime spawning. |
| `_shared/enscript/integrations/input_bindings.md` | `inputs.xml`, `UAInput`, context guards. |
| `_shared/enscript/references/language_types.md` | Checked on `P:`: built in types, `auto`, classes, enums, casting, parameters, containers, templates, strings. |
| `_shared/enscript/references/language_memory.md` | Checked on `P:`: `Managed`, `ref` and weak references, `autoptr`, `delete`, deleting entities. |
| `_shared/enscript/references/language_compile.md` | Checked on `P:`: script layers, `modded class`, attributes, preprocessor defines. |
| `_shared/enscript/references/api_game.md` | Checked on `P:`: `GetGame()`, side checks, time, mission, world, config reads, logging. |
| `_shared/enscript/references/api_scheduling.md` | Checked on `P:`: call categories, `CallLater`, `Timer`, update queues, `ScriptInvoker`. |
| `_shared/enscript/references/api_network.md` | Checked on `P:`: RPC calls, `ScriptRPC`, `OnRPC` dispatch, net sync. |
| `_shared/enscript/references/api_entities_inventory.md` | Checked on `P:`: spawning and `ECE_*` flags, inventory create, read and move. |
| `_shared/enscript/references/api_player.md` | Checked on `P:`: finding players, identities, connect hooks, health, stats. |
| `_shared/enscript/references/types_collections.md` | Primitive types, strings, arrays, maps, sets, vectors, `Math`. |
| `_shared/enscript/references/player_api.md` | `PlayerBase` stats, vitals, agents, modifiers, inventory. |
| `_shared/enscript/references/item_api.md` | `ItemBase` quantity, health, actions, spawning, config properties. |
| `_shared/enscript/references/game_api.md` | `GetGame()`, world, mission, object creation, logging. |
| `_shared/enscript/references/erpc_defines.md` | Vanilla RPC, agent and modifier ID tables; custom ID ranges. |
| `_shared/enscript/references/file_paths.md` | `$profile` and `$saves` paths, file and JSON helpers. |
| `_shared/enscript/references/gui_layout.md` | `.layout` format and every widget type. |
| `_shared/enscript/references/widget_api.md` | Widget script classes and methods, events and `ScriptedWidgetEventHandler`, loading layouts, `UIScriptedMenu`, imagesets. |

### Physics pack (`_shared/physics`)

Front index: `_shared/physics/README.md`, which also has a symptom to cause table. Written for `dayz-physics-specialist`, the specialist every lead can call.

| File | Purpose |
|---|---|
| `_shared/physics/mass-and-weight.md` | Config `weight` against body mass, reading each, and the config keys that change handling. |
| `_shared/physics/collision-lods.md` | Which LOD stops players, items and bullets, its rules, and probing each LOD from script. |
| `_shared/physics/drop-and-throw.md` | Static and dynamic bodies, spawn flags, how vanilla drops and throws, falling through floors. |
| `_shared/physics/contact.md` | `EOnContact` and `Contact`, impact sounds, players and vehicles, character collisions, pushing. |

### Animation pack (`_shared/animation`)

Front index: `_shared/animation/README.md`. Used by `dayz-animation-specialist`.

| Folder or file | Purpose |
|---|---|
| `_shared/animation` | Moving parts: `model.cfg` animations, their config sources, script hooks, RTM and the Blender handoff. |
| `_shared/animation/model-cfg-animations.md` | Skeleton bones and the `Animations` block: keys, radians, value ranges, names in vanilla models. |
| `_shared/animation/animation-sources.md` | `AnimationSources` for items and `class Doors` for buildings. |
| `_shared/animation/script-hooks.md` | `SetAnimationPhase`, the door API and the vanilla barrel and fence patterns. |
| `_shared/animation/rtm-and-character-animation.md` | Where vanilla uses `.rtm`, and why player and infected animation is out of scope. |
| `_shared/animation/blender-handoff.md` | Naming and export notes for parts modelled in Blender. |

### Model and LOD pack (`_shared/models`)

Front index: `_shared/models/README.md`. Written for `dayz-object-builder`.

| Folder or file | Purpose |
|---|---|
| `_shared/models` | What a `.p3d` needs inside, LOD by LOD, and the model side of animated doors. |
| `_shared/models/lods.md` | LOD types vanilla uses, their order, visual LOD numbering, and the Geometry, Fire Geometry and View Geometry rules. |
| `_shared/models/memory-points.md` | Memory LOD rules, axes, and the point names vanilla script looks up. |
| `_shared/models/named-properties.md` | Named properties vanilla sets, mass, and the `autocenter` rule. |
| `_shared/models/proxies.md` | Proxy names, indexes and paths, and the config class an attachment proxy needs. |
| `_shared/models/doors.md` | Door bones, axes, components and action points; the door actions; who writes each part. |

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

### Weapons pack (`_shared/weapons`)

Front index: `_shared/weapons/README.md`. Written for `dayz-weapon-specialist`.

| File | Purpose |
|---|---|
| `_shared/weapons/weapon-classes.md` | Config and script parents by mechanism, how the script class is found, hand animation profiles. |
| `_shared/weapons/weapon-config.md` | `CfgWeapons` keys, `CfgPatches`, jamming, damage, changing a vanilla gun. |
| `_shared/weapons/magazines-ammo.md` | Magazine, ammo pile and bullet classes and how they name each other. |
| `_shared/weapons/attachments.md` | Slot names, optics, suppressors, and how attachments change recoil and sway. |
| `_shared/weapons/recoil-fire-modes.md` | `RecoilBase` classes, recoil modifiers, fire mode classes and keys. |
| `_shared/weapons/muzzle-effects.md` | Muzzle flash, smoke and overheating particles, shot sounds, AI hearing. |
| `_shared/weapons/model-selections.md` | Memory points, selections and bones the weapon model must have. |

### Persistence pack (`_shared/persistence`)

Front index: `_shared/persistence/README.md`. Written for `dayz-persistence-specialist`.

| Folder or file | Purpose |
|---|---|
| `_shared/persistence` | Saving data across server restarts. |
| `_shared/persistence/save-load-contract.md` | The `OnStoreSave` and `OnStoreLoad` chain, what vanilla already saves, load hook order, persistent IDs. |
| `_shared/persistence/versioning-and-migration.md` | Your own save version, adding and removing fields, modded vanilla class risks, data kept in files. |
| `_shared/persistence/base-building.md` | Part ID bit masks, the `Construction` config, territory flag and lock saves. |
| `_shared/persistence/data-audit.md` | The pre release data loss audit and its report format for the server lead. |

### Vehicle pack (`_shared/vehicles`)

Front index: `_shared/vehicles/README.md`. Loaded by dayz-vehicle-specialist and by any worker that checks a vehicle.

| File | Purpose |
|---|---|
| `_shared/vehicles/class-hierarchy.md` | Config and script parents for cars, boats and helicopters, addons to require, mandatory overrides. |
| `_shared/vehicles/simulation.md` | `SimulationModule` keys for engine, gearbox, axles, suspension, wheels and boat propeller. |
| `_shared/vehicles/attachments-and-crew.md` | `attachments[]`, `CfgSlots`, door and wheel parts, inventory groups, crew seats, door states. |
| `_shared/vehicles/fluids-and-engine.md` | Fluid config keys and script calls, engine start rules, vital parts. |
| `_shared/vehicles/damage.md` | `DamageSystem` zones, zone names script reads, crash and crew damage. |
| `_shared/vehicles/helicopters.md` | What vanilla ships for helicopters and what a mod must write. |

### Audio and effects pack (`_shared/audio-fx`)

Front index: `_shared/audio-fx/README.md`. Used by `dayz-audio-fx-specialist` and any lead that needs a sound or an effect.

| File | Purpose |
|---|---|
| `_shared/audio-fx/sound-config.md` | `CfgSoundShaders` and `CfgSoundSets`: samples, volume, range, curves, looping, `CfgPatches`. |
| `_shared/audio-fx/sound-script.md` | Playing, looping, fading and stopping sound sets from script; cleanup; server triggers. |
| `_shared/audio-fx/effects-wiring.md` | Sound plus particle on one device, and config hooks for weapon and item sounds and particles. |

### AI pack (`_shared/ai`)

Front index: `_shared/ai/README.md`. Main user: `dayz-ai-specialist`.

| File | Purpose |
|---|---|
| `_shared/ai/creatures.md` | Infected and animal classes, commands, the command handler order, mod hooks, input controllers, mind states, attacks. |
| `_shared/ai/behaviour-config.md` | `CfgAIBehaviours` templates, `aiAgentTemplate`, alert, vision and noise tuning, making a variant. |
| `_shared/ai/perception.md` | Noise system, player visibility, reacting to gunfire. |
| `_shared/ai/patrols-and-guards.md` | AI world, groups, navmesh paths, waypoint patrols, steering, and the limits of human AI. |
| `_shared/ai/spawning-and-performance.md` | Spawn flags, Central Economy handoff to the server lead, server performance rules. |

### Texture and material pack (`_shared/textures`)

Front index: `_shared/textures/README.md`, which also has a symptom to cause table. Written for `dayz-asset-specialist`.

| File | Purpose |
|---|---|
| `_shared/textures/suffixes-and-sizes.md` | Texture suffixes and what ImageToPAA does with each, vanilla sizes, procedural placeholders. |
| `_shared/textures/rvmat-stages.md` | `.rvmat` keys, Super and Skin stages, damage and destruct materials, the thermal stage. |
| `_shared/textures/surface-recipes.md` | The vanilla material to copy and the values to change for cloth, metal, glass and skin. |
| `_shared/textures/checking-the-look.md` | What the user checks in Object Builder and in game after the files are written. |

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
