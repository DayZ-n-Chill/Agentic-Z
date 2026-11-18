# Knowledge packs

A knowledge pack is Tier 3 reference material: notes, API tables and worked examples for one kind of work. Any DayZ worker may load any pack for one task. Packs are loaded only when the task needs them, never by default. Tier 1 (`.claude/CLAUDE.md`) and Tier 2 (`dayz-conventions.md` plus `conventions/*.md`) still apply on top of every pack.

This file is the one index of every pack. Paths are relative to `skills/`. The repo integrity test (`scripts/dev/test_repo_integrity.py`) fails when a pack folder or pack file is missing from this index, or when the index names a `_shared/` or `dayz-*` path that does not exist. It does not check that paths under other skills' `references/` folders exist.

## Pack layout

- **Where a pack lives.** A pack shared by several agents lives under `_shared/`, either as one file (`_shared/<topic>.md`) or as a folder (`_shared/<topic>/`). A pack that belongs to one skill or one specialist lives in that skill's own `references/` folder (`<skill>/references/`). Use the plural `references/`.
- **File naming.** Lowercase, words joined with `-` or `_` to match the neighbouring files, ending in `.md`. Name the file after its subject (`ptc-format-reference.md`, `singleton.md`), not after a ticket or a date.
- **Front index.** Every pack folder has one front index that says which file to open for which question. For a `_shared/` folder it is the folder's `README.md`; for a skill's `references/` folder it is the table in that skill's `SKILL.md`. Each pack file opens with a title and one line saying what it covers.
- **Loaded only when needed.** Agents and skills name the pack file they need at the step that needs it. They never tell a worker to read a whole pack up front.
- **Checked against vanilla.** Facts about the game cite the vanilla file on `P:\` they came from, so a reviewer can check them. The integrity test fails when a pack file under `_shared/` has no vanilla citation (a `P:\` path, or a file:line such as `itembase.c:261`), except the files it lists as exempt: the style guide and its section files, the answer format note, the py3d notes, the Expansion style note, the Linux and Proton note, the skill resolution note, the server layout notes, the Tier 2 core, `textures/checking-the-look.md` and the folder indexes. It checks that each file cites vanilla at least once; skill `references/` packs are not part of this check, and the line by line check is done by the reviewer. A file still marked "not yet checked on `P:\`" below has not been checked line by line; treat its facts as leads, not answers. A row marked "part checked" has its cited `P:\` lines checked, while its measured results, tool behaviour and facts about other mods are not checked; the file's own opening lines say which is which.
- **Which build a citation is from.** A vanilla line number is right for one game build. Some files cite the lines of the build they were checked on, up to 1.30.164289, which can be newer than the extraction on `P:\`; a measurement keeps the build it was made on. When a cited line does not match on `P:\`, find the symbol by name before deciding the fact is wrong. The build timeline and the files each 1.30 build changed are in `_shared/knowledge/dayz-1-30-build-history.md` ("Which line a citation gives").
- **Registered here.** A new pack gets a row in this index in the same change.

## Index

### Shared single file packs

| Pack | Purpose |
|---|---|
| `_shared/enscript-style.md` | Enforce Script code style, front index. Every script task opens it, then reads only the one file below that the task needs. |
| `_shared/answer-formatting.md` | How to format answers grounded in vanilla source. |
| `_shared/container-base.md` | Custom `Container_Base` config requirements (damage, bullets, interaction). |
| `_shared/figma-to-dayz-rules.md` | Translation rules for the Figma to DayZ `.layout` pipeline. |
| `_shared/py3d-mlod-notes.md` | Reading MLOD `.p3d` files with py3d, used by `/dayz-p3d-audit`. |
| `_shared/linux-proton.md` | Not yet checked on `P:\`: the Linux supplement to the Windows skills: which step has a native Linux equivalent, which runs under Proton and how, and what was not checked. |
| `_shared/skill-resolution.md` | What to do when one skill name is installed twice, as a personal skill and through a plugin. Agent tooling, not game facts. |

### Shared helper scripts (`_shared/scripts`)

Front index: `_shared/scripts/README.md`, which says which script answers which question.

| Folder or file | Purpose |
|---|---|
| `_shared/scripts` | Helper scripts more than one skill uses: the Linux and Proton shell helpers, the script API index builder and its lookup, and their tests. The Linux route was not run in this repo. |
| `_shared/viewer_core.py` | Emits the shared Three.js viewer scaffold that the skills' viewer generators splice into their pages. A string emitter; it does not render and does not vendor three.js. |

### Enforce Script style guide (`_shared/enscript-style`)

Front index: `_shared/enscript-style.md`. Style only; the facts behind it are in the checked `_shared/enscript/references/` files.

| Folder or file | Purpose |
|---|---|
| `_shared/enscript-style` | The style guide, one file per section group. |
| `_shared/enscript-style/naming.md` | File organization and naming: classes, members, methods, constants, defines. |
| `_shared/enscript-style/layout-and-comments.md` | Class layout, braces and spacing, comment styles. |
| `_shared/enscript-style/types.md` | Types, instances and `typename`, collections, casting. |
| `_shared/enscript-style/memory.md` | Object creation, `ref` and `autoptr` rules, `delete`. |
| `_shared/enscript-style/control-flow-and-preprocessor.md` | Conditionals, loops, `switch`, bounds checks, `#ifdef` and `#define`. |
| `_shared/enscript-style/modding-patterns.md` | `modded class`, `super`, singletons and globals, getters, serialization, input, modules. |
| `_shared/enscript-style/debugging-and-errors.md` | Logging, debug defines, null checks, value checks, client and server checks; the Expansion only trace helpers. |
| `_shared/enscript-style/best-practices.md` | Review checklist, compiler and segfault pitfalls, key takeaways. |

### Enforce Script pack (`_shared/enscript`)

Front index: `_shared/enscript/README.md`, which also has a symptom to file table for debugging.

| Folder | Purpose |
|---|---|
| `_shared/enscript/patterns` | Recurring implementation patterns. |
| `_shared/enscript/integrations` | Outside frameworks and vanilla systems. |
| `_shared/enscript/references` | API surface by topic. |
| `_shared/enscript/examples` | Complete `.c` and `.layout` files to start from. Checked on `P:`: `01` to `10` and the three layouts. |

| File | Purpose |
|---|---|
| `_shared/enscript/patterns/modded_class.md` | Checked on `P:`: `modded class` rules: `super`, no `extends`, `NO_GUI` guard, engine-backed classes not to mod. |
| `_shared/enscript/patterns/netsync.md` | Checked on `P:`: net sync variables registered in the constructor, `SetSynchDirty`, `OnVariablesSynchronized`, bit packing. |
| `_shared/enscript/patterns/persistence.md` | Checked on `P:`: `OnStoreSave` and `OnStoreLoad`, your own version header, write order. |
| `_shared/enscript/patterns/rpc.md` | Checked on `P:`: RPC IDs, `ScriptRPC`, the `OnRPC` template, client to server validation. |
| `_shared/enscript/patterns/singleton.md` | Checked on `P:`, with its reported `JsonSerializer` behavior marked: static instance with lazy init, `LoadFile` and `SaveFile`, the `ScriptInvoker` shutdown null guard. |
| `_shared/enscript/patterns/actions.md` | Checked on `P:`: action classes and their `ActionConstructor` registration, condition components, stopping pickup, client and server check mismatch. |
| `_shared/enscript/patterns/scheduler.md` | Checked on `P:`, with each reported claim marked as not checked: the `CallLater` drift report and the `Timer` alternative, per tick allocation cost, traps with scheduled calls, call categories. |
| `_shared/enscript/patterns/physics_items.md` | Checked on `P:`: making spawned items physics active: `ThrowPhysically` or manual dynamic physics. |
| `_shared/enscript/patterns/json_config_migration.md` | Checked on `P:`: JSON config schema versions and forward migration with `LoadFile` and `SaveFile`. |
| `_shared/enscript/patterns/language_workarounds.md` | Checked on `P:`: missing language features (ternary, lambdas, exceptions) and their workarounds; overloading, `auto` and `foreach` with an index, which do work. |
| `_shared/enscript/patterns/server_tick_budget.md` | Part checked: keeping periodic server work inside the tick: a work budget, staggering, backoff, events in place of polling, compile-time side gates. The techniques are third-party mod practice, not vanilla; the vanilla calls they use are cited. |
| `_shared/enscript/integrations/community_framework.md` | Community Framework modules, ModStorage, `GetRPCManager()`, event handlers. Checked against the shipped CF scripts PBO. |
| `_shared/enscript/integrations/dabs_framework.md` | Dabs Framework (third party): attributes, `ScriptView` and `ViewController` MVC, layout bindings, `ScriptViewMenu`. Checked against the mod's own scripts. |
| `_shared/enscript/integrations/expansion_style.md` | Naming and structure for mods that extend or sit beside DayZ Expansion. Expansion targeted work only; the vanilla style guide is the default. |
| `_shared/enscript/integrations/vanilla_plugins.md` | Checked on `P:`: registering a plugin in `PluginManager.Init`, its lifecycle, `GetPlugin()`, `PluginAdminLog`. |
| `_shared/enscript/integrations/central_economy.md` | Checked on `P:` and the vanilla mission: `types.xml`, `cfgspawnabletypes.xml` and `<ce folder>` registration, spawn flags, `GetCEApi()`, ObjectSpawner. |
| `_shared/enscript/integrations/input_bindings.md` | Checked on `P:`: `inputs.xml` format, the `CfgMods` line, `UAInput` API, context guards. |
| `_shared/enscript/references/language_types.md` | Checked on `P:`: built in types, `auto`, classes, enums, casting, parameters, containers, templates, strings. |
| `_shared/enscript/references/language_memory.md` | Checked on `P:`: `Managed`, `ref` and weak references, `autoptr`, `delete`, deleting entities. |
| `_shared/enscript/references/language_compile.md` | Checked on `P:`: script layers, `modded class`, attributes, preprocessor defines. |
| `_shared/enscript/references/api_game.md` | Checked on `P:`: `GetGame()`, side checks, time, mission, world, config reads, logging. |
| `_shared/enscript/references/api_scheduling.md` | Checked on `P:`: call categories, `CallLater`, `Timer`, update queues, `ScriptInvoker`. |
| `_shared/enscript/references/api_network.md` | Checked on `P:`: RPC calls, `ScriptRPC`, `OnRPC` dispatch, net sync. |
| `_shared/enscript/references/api_entities_inventory.md` | Checked on `P:`: spawning and `ECE_*` flags, inventory create, read and move. |
| `_shared/enscript/references/api_player.md` | Checked on `P:`: finding players, identities, connect hooks, health, stats. |
| `_shared/enscript/references/api_recipes_energy_damage.md` | Checked on `P:`, with what could not be opened marked: crafting recipes (`RecipeBase`, `PluginRecipesManager`), `ComponentEnergyManager`, and how damage reaches an entity. |
| `_shared/enscript/references/api_reflection_profiler.md` | Checked on `P:`, with reported behavior marked: fields and methods by name, creating a class from a string, timing script with `EnProfiler`, the debugging globals. |
| `_shared/enscript/references/script_module_arena.md` | Part checked: how much memory the compiler charges a script module (the `4_World` arena), what does and does not shrink it, how to measure it. Declarations checked on `P:`; the measurements are from one mod on 1.29. |
| `_shared/enscript/references/types_collections.md` | Checked on `P:`: primitive types, strings, arrays, maps, sets, vectors, `Math`. |
| `_shared/enscript/references/item_api.md` | Checked on `P:`: `ItemBase` quantity, health, actions, spawning, config properties. |
| `_shared/enscript/references/erpc_defines.md` | Checked on `P:`: `ERPCs`, `eAgents` and `eModifiers`, the modifier and agent calls; custom ID ranges (a modding convention, not vanilla). |
| `_shared/enscript/references/file_paths.md` | Checked on `P:`: `$profile`, `$saves` and `$mission` paths, file and JSON helpers. |
| `_shared/enscript/references/gui_layout.md` | Checked on `P:`: `.layout` format and every widget class vanilla layouts use. |
| `_shared/enscript/references/widget_api.md` | Checked on `P:`: widget script classes and methods, events and `ScriptedWidgetEventHandler`, loading layouts, `UIScriptedMenu`, imagesets. |
| `_shared/enscript/examples/layouts.md` | Checked on `P:`: what the three example layouts are, with their companion scripts. |

### Physics pack (`_shared/physics`)

Front index: `_shared/physics/README.md`, which also has a symptom to cause table. Written for `dayz-physics-specialist`, the specialist every lead can call.

| File | Purpose |
|---|---|
| `_shared/physics/mass-and-weight.md` | Config `weight` against body mass, reading each, and the config keys that change handling. |
| `_shared/physics/collision-lods.md` | Which LOD stops players, items and bullets, its rules, and probing each LOD from script. |
| `_shared/physics/drop-and-throw.md` | Static and dynamic bodies, spawn flags, how vanilla drops and throws, falling through floors. |
| `_shared/physics/contact.md` | `EOnContact` and `Contact`, impact sounds, players and vehicles, character collisions, pushing. |
| `_shared/physics/layers-and-raycasts.md` | Interaction layers, the three ways to switch a collision off, the two families of ray and overlap tests, and why the action cursor ignores a physics body. |
| `_shared/physics/network-and-authority.md` | What the engine sends clients about a moving object, why a vehicle moves smoothly and a free body on an item does not, which machine simulates what. |
| `_shared/physics/player-controller.md` | Part checked: the player's character controller, the script calls on it, moving platforms, the ragdoll, fall damage. The measured results come from in-game test mods and cannot be checked on `P:\`. |
| `_shared/physics/rigid-body-api.md` | Creating, waking, moving and removing a physics body from script, where friction and bounce come from, the calls that do not exist. |
| `_shared/physics/scripted-triggers.md` | The script API under every scripted trigger: `ScriptedEntity` and its collision shapes, enter and leave events, the server and client hooks of `TriggerEvents`. |
| `_shared/physics/water-queries.md` | Part checked: what the engine's water queries return over river and stream pieces, the streambed kit and a roadway water face. Declarations checked on `P:`; every number was measured in game. |

### Animation pack (`_shared/animation`)

Front index: `_shared/animation/README.md`. Used by `dayz-animation-specialist`.

| Folder or file | Purpose |
|---|---|
| `_shared/animation` | Moving parts: `model.cfg` animations, their config sources, script hooks, RTM and the Blender handoff. |
| `_shared/animation/model-cfg-animations.md` | Skeleton bones and the `Animations` block: keys, radians, value ranges, names in vanilla models. |
| `_shared/animation/animation-sources.md` | `AnimationSources` for items and `class Doors` for buildings. |
| `_shared/animation/script-hooks.md` | `SetAnimationPhase`, the door API and the vanilla barrel and fence patterns. |
| `_shared/animation/rtm-and-character-animation.md` | Where vanilla uses `.rtm`, how character animation differs, and what the graph layer allows without replacing it (a per-item clip through a child `.asi`); editing the player or infected graph stays out of scope. |
| `_shared/animation/blender-handoff.md` | Naming and export notes for parts modelled in Blender. |
| `_shared/animation/anim-graphs.md` | Where the player and creature animation graphs live on `P:\`, the names they declare, and which mod changes collide. |
| `_shared/animation/items-in-hands.md` | How the game picks the pose of a held item, how a mod registers its own items, and the vanilla ways to show, hide or swap model parts with attach state. |
| `_shared/animation/rider-poses.md` | How the vanilla graph poses a player on a vehicle, what that means for a mod vehicle of another shape, and the one way to change the pose for a single vehicle class. |

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
| `_shared/models/selections.md` | What a named selection in a `.p3d` is, which LOD each kind belongs in, who reads it, and how tools lose it without a word. |
| `_shared/models/building-selections.md` | The names a building or ladder model carries: door leaves and their points, the two ladder schemes, Paths LOD points, loot and rain sound points, `liquid_source`. |
| `_shared/models/proxy-frames.md` | Part checked: how a proxy triangle becomes a position and a facing, and the crew seat, body part, clothing and weapon attachment cases. Names, paths and config classes checked on `P:`; the frame rules are not checked. |
| `_shared/models/uv-mapping.md` | Part checked: how UVs are stored in a `.p3d`, which UV set each material stage reads, what binarizing does to them, tracing a texture fault to the UVs. Material and config facts checked on `P:`; format details and measurements are not. |
| `_shared/models/multi-rvmat-texturing.md` | How vanilla textures one mesh with up to four tiling surfaces through one `Multi` shader material: the mask, the two UV sets and faces with no texture of their own. |

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
| `_shared/wearables/references/worn-models.md` | Part checked: what the worn models (`_m` and `_f`) need to bind to the player: skeleton name, coordinate frame, selections and weights, and three failures that give no log error. Results marked "Measured" were measured on one armor build. |
| `_shared/wearables/references/changes-in-1-30.md` | What DayZ 1.30 changed in the config and script contract around wearables, what that breaks in a 1.29 mod, and a checklist for moving one over. The 1.29 statements are marked and cannot be checked on `P:\`. |

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
| `_shared/weapons/weapon-script-api.md` | Script calls around a firearm: spawning it loaded, reading its state, its state machine, the firearm actions, and the calls that changed in DayZ 1.30. |
| `_shared/weapons/hand-animation-and-grip.md` | How a weapon gets its hand pose and its reload and fire clips, what a custom weapon can change without replacing the player graph, and what was measured about closing the support hand. |

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
| `_shared/vehicles/motorbikes.md` | Checked on `P:`: which classes a motorbike starts from, the addon it requires, how it differs from a car, and what its config and script classes must contain. |
| `_shared/vehicles/motorbike-invariants.md` | Part checked: the ten rules that break a motorbike when ignored, tuning lessons measured on a real import, and what vanilla left unfinished in 1.30. |
| `_shared/vehicles/vehicle-types-boat-truck.md` | 1.30 citations checked on `P:`: what changes for boats, trucks, mod-made quads and the motorbike family against a four-wheeled `CarScript` car. |
| `_shared/vehicles/dayz-1-30-vehicles.md` | Part checked: what DayZ 1.30 changed for cars, trucks and boats beyond the class tree: lights, electricity, horn, the get-in condition, boats, `speedGeoms`, ruined wheels, and a migration checklist. |
| `_shared/vehicles/aviation-carscript-base.md` | Part checked: the vanilla contracts an aircraft leans on when it inherits `CarScript`: entity events, scripted velocity, angular velocity, body sleep, what stops the engine. |
| `_shared/vehicles/aviation-inputs-and-actions.md` | Part checked: custom flight inputs and in-seat pilot actions: why an input reads zero in the seat, reading it on the server, deadzones, sight and camera interfaces. |
| `_shared/vehicles/aviation-networking.md` | Part checked: how a scripted aircraft stays smooth for its pilot: the Pawn classes and events, the move strategy, owner prediction, ownership changes, the pilot's camera. |

The files below are field notes from vehicle projects. Each opens with a `Status:` line saying what it was measured on. In a "part checked" file, a citation written with its full `P:\` path was opened on `P:\`; the measurements were not repeated.

| Folder or file | Purpose |
|---|---|
| `_shared/vehicles/new-car-day-one.md` | Part checked: what to measure offline before a new or ported vehicle first goes in game, what each of the three files owns, and the gaps no config review reveals. |
| `_shared/vehicles/vehicle-config-and-modelcfg.md` | Part checked: a complete `CarScript` config class and the matching `model.cfg` of a drivable car, block by block, from a working from-scratch third-party 4x4, compared with a quad bike, a DayZ Expansion UAZ and vanilla. |
| `_shared/vehicles/vehicle-structural-parity.md` | Part checked: the parity-first method: debinarize a vanilla car once, diff your model against it, and build every missing LOD, selection, proxy, hub and override in one pass. |
| `_shared/vehicles/invariants-engine-fluids-and-handling.md` | Part checked: why an engine will not start or stay on, what a test kit must fill and attach, and measured rules for rolling, steering, mass, grip and drivetrain ratios. |
| `_shared/vehicles/invariants-get-in-and-seats.md` | Part checked: why a get-in, seat or door action does not appear on a new or imported car, and the model, config and script contract that makes it appear. |
| `_shared/vehicles/invariants-import-mesh-and-winding.md` | Part checked: checks for a body that comes from an OBJ, a glTF or a game rip: mesh and UV health, mirror against rotation, winding, nose direction, cabin alignment. |
| `_shared/vehicles/invariants-lods-and-vertex-budget.md` | Not yet checked on `P:\`: how many visual LODs an imported vehicle needs, how far each decimation method goes, and telling offline that a model is over the vertex ceiling. |
| `_shared/vehicles/invariants-wheels-and-hubs.md` | Part checked: where wheel hubs live in the model, how wheel proxies line up with them, hub height against tyre radius, wheel facing, and the axle classes the engine counts. |
| `_shared/vehicles/proxies-and-get-in.md` | Part checked: how proxies are placed on a working car, the four layers a detachable door, hood or trunk needs, what a seated player's action must register, hiding an attachment proxy from script. |
| `_shared/vehicles/get-in-actions-and-proxy-pose.md` | Part checked: the four-link condition chain behind the get-in prompt, the two registrations a cursor-targeted vehicle action needs, and where an occupant's pose comes from. |
| `_shared/vehicles/gunner-shoot-from-vehicle.md` | Part checked: how a rider can fire a handheld weapon from a moving car or boat, as one third-party mod does it: linked at an anchor and frozen by a scripted human command. |
| `_shared/vehicles/doors-and-panel-edges.md` | Not yet checked on `P:\`: why an imported door shows a missing edge when it opens, measuring that edge against a vanilla door, and what a hood or trunk needs that a door rig gets wrong. |
| `_shared/vehicles/rip-panel-open-rim.md` | Not yet checked on `P:\`: why a door, hood or tailgate from a game rip shows a see-through edge when it opens, what does not close it, and the gate that proves a real cap. |
| `_shared/vehicles/lights.md` | Part checked: why a car's lights do not switch: material paths, hidden selection ownership and order, bulbs, driver exit, testing the setter against a vanilla car. |
| `_shared/vehicles/emissive-leds-and-dynamic-lights.md` | Part checked: making an LED change colour and glow (a hidden selection, one `.rvmat` per state, a swap from script) and light the scene (a `PointLightBase` on a memory point). |
| `_shared/vehicles/gauge-needles.md` | Part checked: a working speedometer, tachometer and fuel gauge: the needle part, the dial frame and its mirror traps, deriving the angles, the `model.cfg` wiring. |
| `_shared/vehicles/cockpit-screens-and-map-tiles.md` | Part checked: showing a map on a dashboard screen: the render target bridge and its limit, satellite tiles on hidden selections, tile overlap, a sliding tile window. |
| `_shared/vehicles/inventory-preview.md` | Part checked: two ways the inventory preview of a door, hood or other part renders empty: the wrong `rotationFlags` and an `invview` point at the bounding box centre. |
| `_shared/vehicles/materials-and-selections.md` | Part checked: two diagnoses that look solid and are not, and the rule that a selection the car's config drives must live in the parent model. |
| `_shared/vehicles/view-pilot-and-first-person.md` | Part checked: what a seated player sees: the View Pilot LOD, the proxies it references, trimming it safely, and two traps of an offline first-person viewer. |
| `_shared/vehicles/placement-and-autocenter.md` | Part checked: where `autocenter=0` belongs on a placed item and on a vehicle, why adding it to every LOD made one item float, and the LOD resolution bands to use. |
| `_shared/vehicles/animation-sign-and-axis.md` | Not yet checked on `P:\`: proving offline that a wheel, door, steering or dial animation turns the right way, by comparing angle and axis with a vanilla control. |
| `_shared/vehicles/animation-bake-and-odol-sections.md` | Part checked: proving offline that a `model.cfg` animation and new geometry survived binarization: skeleton bones, `sections[]`, ODOL section flags, translation offsets. |
| `_shared/vehicles/binarize-vertex-budget.md` | Not yet checked on `P:\`: the three verdicts of binarize on a model, the real vertex ceiling in resolved triples, and which log lines do not discriminate. |
| `_shared/vehicles/p3d-vehicle-killers.md` | Part checked: vehicle checks beyond the P3D killers: mass tagged in the wrong LOD, wheel-well clearance, crew seat components, crew proxy triangles, the vertex ceiling. |
| `_shared/vehicles/build-packaging-and-debug.md` | Part checked: what changes between a packed-only and a binarized vehicle PBO, where the wheel spin direction lives, and checking a vehicle PBO offline. |
| `_shared/vehicles/deploy-gates-and-crash-fingerprint.md` | Part checked: gates that prove the packed PBO holds what was approved, the one offline syntax gate for `config.cpp`, and comparing native crashes. |
| `_shared/vehicles/runtime-state-and-sync.md` | Part checked: which per-tick event a car runs, what a non-owner client reads, why script visual state is missing on a fresh spawn, probing a vehicle that draws or exits in the wrong place. |
| `_shared/vehicles/network-physics-ownership.md` | Part checked: who simulates a vehicle, why a forced seat is not ownership, why writing the pose fights the owner, and the rules of a custom `PawnMove` and `PawnOwnerState` pair. |
| `_shared/vehicles/test-stand-and-mcp.md` | Part checked: measured limits of driving, seating and unseating a vehicle from an automated test harness, and which actions the server still validates. |
| `_shared/vehicles/method-and-gate-calibration.md` | Part checked: process rules: the iteration budget, calibrating a gate before trusting it, what a PASS covers. |
| `_shared/vehicles/process-gates.md` | Part checked: writing a model-import gate that can be trusted: a negative fixture per rule, three exit states, controls independent of the candidate. |
| `_shared/vehicles/visual-gates-and-winding.md` | Part checked: the session record of imported-car offline visual gates that lie, followed by the later winding lessons. |
| `_shared/vehicles/visual-metrics-and-viewer.md` | Part checked: what can be asserted from a screenshot: perspective artifacts, where a HUD marker ray is anchored, validating a visual metric on a control. |
| `_shared/vehicles/external-obj-import.md` | Part checked: OBJ to game-ready `.p3d`, end to end: parse, transform, decimate, normals, LOD assembly, PNG to PAA, config wiring and validation. |
| `_shared/vehicles/decimation-libraries.md` | Not yet checked on `P:\`: which Python library to reduce a high-poly import with, a `pymeshlab` recipe that keeps UV seams, and face targets for a LOD ladder. |
| `_shared/vehicles/png-to-paa-encoding.md` | Part checked: a DXT1 `.paa` writer in Python, the file layout it writes, how to check its output, and what it cannot do. The header layout was compared with vanilla files on `P:\` and the encoder's output was read back with this repo's PAA decoder; nothing was checked in game. `/dayz-pack-texture` is the normal route. |
| `_shared/vehicles/gta-rip-intake.md` | Part checked: reading a GTA V vehicle mod archive offline, what its skeleton names map to in DayZ, and checking bone names against the real mesh pieces. |
| `_shared/vehicles/rip-import.md` | Part checked: the rip import path in detail, from one worked example: the rip folder, deriving dimensions and the transform, the structural LOD recipe, first spawn results and their causes. |
| `_shared/vehicles/rip-geometry-and-winding.md` | Part checked: geometry work on a ripped mesh: automatic retopology, the winding rules for proxy triangles and visual faces, the scope of `autocenter=0`, fixing winding per component. |
| `_shared/vehicles/history` | History only, no authority: superseded gate ladders and rules, kept for vehicles already built against them. Listed in `_shared/vehicles/README.md`. |
| `_shared/vehicles/history/legacy-gate-ladder.md` | Not yet checked on `P:\`: the superseded order of diagnostic gates for an imported car, plus the LOD frame parity rung. |
| `_shared/vehicles/history/pre-change-0-gate-ladder.md` | Not yet checked on `P:\`: the old ordered ladder of visual gates for an imported car, kept for manual diagnosis. |
| `_shared/vehicles/history/superseded-family-b-rules.md` | Not yet checked on `P:\`: the exact text of vehicle rules that were later corrected, so a reader can see what was replaced and why. |

### Audio and effects pack (`_shared/audio-fx`)

Front index: `_shared/audio-fx/README.md`. Used by `dayz-audio-fx-specialist` and any lead that needs a sound or an effect.

| File | Purpose |
|---|---|
| `_shared/audio-fx/sound-config.md` | `CfgSoundShaders` and `CfgSoundSets`: samples, volume, range, curves, looping, `CfgPatches`. |
| `_shared/audio-fx/sound-script.md` | Playing, looping, fading and stopping sound sets from script; cleanup; server triggers. |
| `_shared/audio-fx/effects-wiring.md` | Sound plus particle on one device, and config hooks for weapon and item sounds and particles. |
| `_shared/audio-fx/sound-engine-api.md` | The classes under `EffectSound` (`SoundParams`, `SoundObjectBuilder`, `SoundObject`, `AbstractWave`, the sound scene), for building and tuning a sound by hand. |
| `_shared/audio-fx/item-and-player-sounds.md` | The sound systems vanilla already runs: the item sound handler, the player sound handlers, step sounds, player sound events, bush step sounds. |
| `_shared/audio-fx/music-and-radio.md` | How the client music player picks a track, adding a music zone or the music of a custom world, and the 1.30 bunker static of radios. |
| `_shared/audio-fx/noise-for-ai.md` | Making a noise that infected and animals hear to go with a sound, and the 1.30 change to weather noise reduction. |

### AI pack (`_shared/ai`)

Front index: `_shared/ai/README.md`. Main user: `dayz-ai-specialist`.

| File | Purpose |
|---|---|
| `_shared/ai/creatures.md` | Infected and animal classes, commands, the command handler order, mod hooks, input controllers, mind states, attacks. |
| `_shared/ai/behaviour-config.md` | `CfgAIBehaviours` templates, `aiAgentTemplate`, alert, vision and noise tuning, making a variant. |
| `_shared/ai/perception.md` | Noise system, player visibility, reacting to gunfire. |
| `_shared/ai/patrols-and-guards.md` | AI world, groups, navmesh paths, waypoint patrols, steering, and the limits of human AI. |
| `_shared/ai/spawning-and-performance.md` | Spawn flags, Central Economy handoff to the server lead, server performance rules. |
| `_shared/ai/animal-territories.md` | The mission files that say where animals and ambient life live: `cfgenvironment.xml`, the territory zone files, the group behaviour names and the group templates they select. |
| `_shared/ai/creature-animation.md` | How an animal or infected class is tied to its animation graph, which commands and variables the graph declares, and the two bones the engine moves and aims. |
| `_shared/ai/custom-infected.md` | What a custom infected inherits for behaviour, what its model must keep for the AI, why a bigger body does not reach further, and the 1.30 infected changes. Facts that are not vanilla are marked. |

### Texture and material pack (`_shared/textures`)

Front index: `_shared/textures/README.md`, which also has a symptom to cause table. Written for `dayz-asset-specialist`.

| File | Purpose |
|---|---|
| `_shared/textures/suffixes-and-sizes.md` | Texture suffixes and what ImageToPAA does with each, vanilla sizes, procedural placeholders. |
| `_shared/textures/rvmat-stages.md` | `.rvmat` keys, Super and Skin stages, damage and destruct materials, the thermal stage. |
| `_shared/textures/surface-recipes.md` | The vanilla material to copy and the values to change for cloth, metal, glass and skin. |
| `_shared/textures/checking-the-look.md` | What the user checks in Object Builder and in game after the files are written. |
| `_shared/textures/runtime-material-swaps.md` | Part checked: what changes an item's material or texture at run time: health levels, the script calls, and what was measured when a script repaints worn clothing. Blocks marked "measured in game" come from one mod project. |

### Knowledge notes pack (`_shared/knowledge`)

Front index: `_shared/knowledge/README.md`, which also says how far to trust each file. Each file states what was checked in a `Status:` line under its title or in its opening paragraph.

| Folder or file | Purpose |
|---|---|
| `_shared/knowledge` | Cross-cutting DayZ notes that fit no single topic pack: source maps of vanilla systems, measured results and field notes. |
| `_shared/knowledge/mission-lifecycle.md` | Checked on `P:`: the order in which the mission classes run their constructor, `OnInit`, `OnMissionStart` and `OnUpdate`, and the exact `super` chain. |
| `_shared/knowledge/script-input-user-data.md` | Checked on `P:`: `ScriptInputUserData`, the channel that carries a player's own input to the server, and when to use it instead of `ScriptRPC`. |
| `_shared/knowledge/vanilla-native-surface.md` | Checked on `P:` (the counts differ, see its status): the `proto native` declarations, where they are, and what `owned` and `static` mean on one. |
| `_shared/knowledge/entity-component-system.md` | Checked on `P:`: `GenericEntity`, `GenericComponent` and `ScriptComponent`: the `COMPONENT_SYSTEM` guard, insert and remove, event order, event masks. |
| `_shared/knowledge/workbench-scripting-api.md` | Not yet checked on `P:\` (which holds an older API): the Enforce Script entry points, modules, plugins and events that extend Workbench. |
| `_shared/knowledge/script-network-limits.md` | Measured, not yet checked on `P:\`: string payload sizes over `ScriptRPC` and `ScriptInputUserData`, input queue depth, RPC burst ordering, what an ACK proves. |
| `_shared/knowledge/script-network-arrays.md` | Measured, not yet checked on `P:\`: the first run of `array<int>` over `ScriptRPC` and `ScriptInputUserData`. |
| `_shared/knowledge/script-network-array-types.md` | Measured, not yet checked on `P:\`: larger `array<int>`, `array<string>` and nested arrays over both channels. |
| `_shared/knowledge/mcp-bridge-protocol.md` | Part checked: design record of the third-party DayZ-MCP bridge. Its engine facts are checked on `P:`; the tool surface and measured behaviour are not. |
| `_shared/knowledge/linux-proton-findings.md` | Measured, not yet checked on `P:\`: DayZ Tools, the server, the client and DayZ-MCP on Linux under Proton and podman. |
| `_shared/knowledge/environment-and-infra.md` | Not yet checked on `P:\` line by line (its cited lines were): work drive and mod layout, diag binaries, build and launch gotchas, mission files, BattlEye kick codes, logs. |
| `_shared/knowledge/technical-notes.md` | Part checked: py3d usage, LOD resolutions, winding when porting from Blender, debris offsets, dynamic item physics, magazine quantity, JSON schema migration. Cited lines checked on `P:`. |
| `_shared/knowledge/verified-capabilities.md` | Not yet checked on `P:\` line by line: feasibility verdicts and gotchas from mod projects; its last section lists what was checked. |
| `_shared/knowledge/vehicles-crossproject.md` | Part checked: the seven invariants every vehicle runs into and which vehicle project showed each. The vanilla citations in rows 1 and 7 are checked on `P:`. |
| `_shared/knowledge/wiki-systems-reference.md` | Not yet checked on `P:\`, except the lines its last section lists: gameplay, environment and server configuration systems. |
| `_shared/knowledge/script-layers-and-central-economy.md` | Not yet checked on `P:\`, except the lines its last section lists: sixteen facts on script layers, load order, Central Economy files, loot and events. |
| `_shared/knowledge/public-reference-index.md` | Not yet checked on `P:\` (an index of pointers, almost no game facts): where to look up a DayZ topic outside the repo and how far each kind of page can be trusted. |
| `_shared/knowledge/dayz-1-30-build-history.md` | Part checked: which DayZ build a fact or line number belongs to, and what moved between the 1.30 builds. The 1.30.164200 and 1.30.164289 rows are not yet checked on `P:\`, which holds an older 1.30 build. |
| `_shared/knowledge/retracted-claims-ledger.md` | Part checked: DayZ modding beliefs that were written down as fact and later corrected. Cited lines checked on `P:`; the measured corrections are not. |
| `_shared/knowledge/engine-and-script-tree-findings.md` | Part checked: DayZ engine and script-tree facts that no other pack file carries, for writing a tool that reads the vanilla script tree. Cited lines checked on `P:`; counts and measurements are not. |
| `_shared/knowledge/working-rules.md` | Process rules for planning how to verify, test and record DayZ work. Process, not game facts; the vanilla lines it cites as examples were opened. |
| `_shared/knowledge/mod-cycle.md` | A map of one pass through making a mod (understand, write, lint, pack, deploy, test, debug) and a route table from "I want X" to the skill or tool. Tool behaviour not yet checked. |

### Skill packs (`references/`)

A skill's own pack. The front index of each folder is the table in that skill's `SKILL.md`. The marks follow each file's own opening lines: "not yet checked on `P:\`" for third-party facts, tool behaviour and results measured in mod projects, "part checked" where the cited `P:\` lines were checked and the rest was not. A row with no mark makes no claim either way: the file's opening lines say what was checked.

| Folder or file | Purpose |
|---|---|
| `dayz-particles/references` | Particle pack. Front index: `dayz-particles/SKILL.md`. |
| `dayz-particles/references/ptc-format-reference.md` | Every `.ptc` emitter property and curve. |
| `dayz-particles/references/emat-format-reference.md` | `.emat` particle material format and vanilla materials. |
| `dayz-particles/references/script-api-reference.md` | Playing, stopping and tuning particles from script. |
| `dayz-particles/references/integration-patterns.md` | Wiring particles into a device. |
| `dayz-particles/references/vanilla-particle-catalog.md` | Every vanilla particle in `ParticleList`. |
| `dayz-particles/references/dayz-1-30-particles.md` | What DayZ 1.30 changed for particles: the client check, effects spawned by the server, surface particle IDs, vehicle effect overrides, effect areas, the sandstorm, oil pits. |
| `dayz-particles/references/effect-area-particles.md` | How many emitters a contaminated area in `cfgeffectarea.json` asks for, the hard cap, and why an area can hurt players where no gas is drawn. |
| `dayz-particles/references/playonobject-client-guard.md` | The usual mod pattern for attaching a looping particle to a placed object, compared with the vanilla wrecks it copies. |
| `dayz-particles/references/standalone-particle-reference.md` | How a large effect is built from several emitters, how the modulation curves shape it, switching emitters from script, and mapping old `CfgCloudlets` particles onto `.ptc`. |
| `dayz-p3d-audit/references` | Model audit pack. Front index: `dayz-p3d-audit/SKILL.md`. |
| `dayz-p3d-audit/references/p3d-killers.md` | Model faults that break a `.p3d` with no engine error. |
| `dayz-p3d-audit/references/winding-methodology.md` | How to verify face winding. |
| `dayz-p3d-audit/references/config-rvmat-checks.md` | `config.cpp` and `.rvmat` checks for models. |
| `dayz-p3d-audit/references/killers-detail.md` | The measured evidence behind killers 1 to 10 of `p3d-killers.md`: what was tested in game, how each fault is detected and fixed, and what was not measured. |
| `dayz-p3d-audit/references/manual-checks.md` | Not yet checked on `P:\`, except the vanilla LOD counts: faults the audit cannot see from one `.p3d`, how to measure each by hand, and rules for trusting a new gate. |
| `dayz-p3d-audit/references/vehicle-checks.md` | Not yet checked on `P:\`, except where a vanilla file is cited: what the audit checks on a wheeled vehicle body, and the vehicle faults (killers 11 to 13) to measure by hand. |
| `dayz-p3d-audit/references/winding-absolute-check.md` | Not yet checked on `P:\`: how to read the winding findings the audit prints from py3d, and why a clean py3d result is not proof of correct geometry. |
| `dayz-p3d-audit/references/winding-diagnostics.md` | The deep companion of `winding-methodology.md`: how each winding check reads on measured models, turning a result into a safe fix, and where offline checks stop. |
| `dayz-search-index/references` | Search index notes. Front index: `dayz-search-index/SKILL.md`. |
| `dayz-search-index/references/cost-and-free-tier.md` | Voyage embedding cost and the free tier check. |
| `dayz-search-index/references/chunking.md` | How each file type is chunked, and what indexes built by older versions are missing. |
| `dayz-import-mod/references` | Import notes. Front index: `dayz-import-mod/SKILL.md`. |
| `dayz-import-mod/references/github-and-cleanup.md` | Git link forms, clone naming and reuse, and removing an imported or cloned mod. |
| `dayz-preflight/references` | Environment check notes. Front index: `dayz-preflight/SKILL.md`. |
| `dayz-preflight/references/object-builder-viewer.md` | Object Builder's external viewer (Buldozer) path, a check to run by hand before a session that leans on Object Builder previews. |
| `dayz-preflight/references/dayz-1-30.md` | Not yet checked on `P:\`: the 1.30 launch options and Workbench editors worth knowing; no environment check changed. |
| `dayz-preflight/references/linux.md` | Not yet checked on `P:\`: what replaces each environment check on Linux. |
| `dayz-build-pbo/references` | Build and packing pack. Front index: `dayz-build-pbo/SKILL.md`. |
| `dayz-build-pbo/references/addonbuilder-rules.md` | How AddonBuilder and binarize behave when they pack a mod: the command line, which source tree a build uses, staging, `-temp`, where the ODOL lands. |
| `dayz-build-pbo/references/pre-build-checks.md` | What to check in a mod folder before it is packed: structure, `config.cpp`, `model.cfg`, texture and material paths, LODs, stringtable, scripts, wheel slots. |
| `dayz-build-pbo/references/common-validation-failures.md` | Symptom, cause and fix for the failures the pre-build checks report most often. |
| `dayz-build-pbo/references/validation-scripts.md` | Four reference validators as code blocks (config, texture paths, stringtable, LODs), with their output and exit codes. Shapes to adapt, not bundled scripts. |
| `dayz-build-pbo/references/script-linter-and-compile-gate.md` | Using the offline script validator before packing, what its result proves, and the boot check that shows a deployed mod's script modules compile. |
| `dayz-build-pbo/references/post-build-gates.md` | Checks on a built or deployed PBO: its scripts and models are inside, its entries match the source, the mod's script modules load. |
| `dayz-build-pbo/references/workshop-publish.md` | Signing a built PBO with DsUtils, the Workshop item folder, and publishing with the Publisher or SteamCMD. |
| `dayz-build-pbo/references/dayz-1-30-pbo-build.md` | Not yet checked on `P:\`: what 1.30 changes for packing: duplicate members stop binarize, unpacked mods, the `fsShadowing` header property. |
| `dayz-build-pbo/references/dayzmake-linux.md` | Not yet checked on `P:\`: building, signing and publishing a mod on Linux with dayzmake, without DayZ Tools. |
| `dayz-pbo-reverse-engineering/references` | Notes for studying another mod's PBO. Front index: `dayz-pbo-reverse-engineering/SKILL.md`. |
| `dayz-pbo-reverse-engineering/references/pitfalls.md` | Not yet checked on `P:\`, except where a vanilla file is named: wrong conclusions from names and partial code, an extraction that did not decode, a companion PBO that seems lost. |
| `dayz-pbo-reverse-engineering/references/state-ledger.md` | Not yet checked on `P:\` (a working method): the four ledger files of an extraction project, classifying a finding, one unit per turn, the closing document. |
| `dayz-pbo-reverse-engineering/references/linux.md` | Not yet checked on `P:\`: unpacking a PBO on Linux: which dayzmake version may unpack it, the fallback, the shell equivalents. |
| `dayz-test-ingame/references` | In-game test pack. Front index: `dayz-test-ingame/SKILL.md`. |
| `dayz-test-ingame/references/windows-launch-cycle.md` | The build, deploy and launch loop on one Windows machine: prerequisites, launch modes, default mods and admin tools, what `-filePatching` reloads. |
| `dayz-test-ingame/references/troubleshooting.md` | The symptom table for a local test session, where each log lives, and measured failures that come from the environment and not from the mod. |
| `dayz-test-ingame/references/build-and-storage-traps.md` | Measured ways a build, deploy and test cycle goes green without testing the change: a locked PBO never replaced, a check that only tests existence, signing the old PBO. |
| `dayz-test-ingame/references/automated-cells.md` | Building a scripted test that boots the game, drives it without a human and reads a verdict from the logs; the measured walls. |
| `dayz-test-ingame/references/managed-launcher.md` | Not yet checked on `P:\`: starting, owning and stopping a test run through the third-party dayz-mcp server, the unmanaged fallback, and every trap measured on that route. |
| `dayz-test-ingame/references/server-and-mission-config.md` | What the stock 1.30 dedicated server ships and which script reads it, read from the DayZ Server install. |
| `dayz-test-ingame/references/session-findings.md` | Not yet checked on `P:\`: dated in-game findings measured on third-party mods and tooling, to load when a launch shows the matching symptom. |
| `dayz-test-ingame/references/dayz-1-30-test-ingame.md` | Part checked: the 1.30 launch flag and action injection changes. Script lines were opened on `P:\`; changelog lines and runtime behaviour were not. |
| `dayz-test-ingame/references/linux.md` | Not yet checked on `P:\`: what changes in the test workflow when the host is Linux. |
| `dayz-test-ingame/references/linux-native-server.md` | Measured on Linux, not yet checked on `P:\`: proving a mod loads on the native Linux dedicated server, with no client. |
| `dayz-test-ingame/references/linux-headless-client.md` | Not yet checked on `P:\`: testing the client side on Linux with the retail client under Proton and a self-reporting test mod. |
| `dayz-mcp-verify/references` | Verification through the third-party dayz-mcp bridge. Front index: `dayz-mcp-verify/SKILL.md`. Tool behaviour throughout: not yet checked on `P:\`; vanilla facts cite their file. |
| `dayz-mcp-verify/references/bridge-setup.md` | What must be true before the first verb (tools registered, config and key seeded, both peers polling) and what each bridge failure means. |
| `dayz-mcp-verify/references/run-lifecycle.md` | How a run is started, adopted, kept alive and stopped, and how several sessions share one test machine. |
| `dayz-mcp-verify/references/verb-gotchas.md` | Per-verb traps of the bridge: what each reply does and does not prove, each with its check. |
| `dayz-mcp-verify/references/captures.md` | How the screenshot and camera verbs behave, which frames say nothing about the mod, capturing a raised weapon, measuring UI in a capture. |
| `dayz-mcp-verify/references/collision-probes.md` | Reading an object's collision with ray, walk-into and stand-on tests: the ray battery and its controls, and which results prove nothing. |
| `dayz-mcp-verify/references/actions-ui-and-inventory.md` | Which player actions, doors, mod UIs and inventory moves can be driven through the bridge, which only start, and two workarounds. |
| `dayz-mcp-verify/references/playbooks.md` | The scene to set before capturing, and what counts as PASS or FAIL for a static object, an item or weapon, and a vehicle. |
| `dayz-mcp-verify/references/vehicle-smoke.md` | A repeatable visual smoke test of a `CarScript` vehicle, giving a spawned car real wheels and fluids, and the rules for a driving bench. |
| `dayz-mcp-verify/references/acceptance-ladder.md` | The full ladder for accepting a drivable car: the driving verbs, rungs R1 to R6, and the table from each failure to its known fix. |
| `dayz-mcp-verify/references/telemetry-gates.md` | Setting a threshold on telemetry read from the game so that real physics can pass it and an incomplete trace cannot. |
| `dayz-mcp-verify/references/verification-discipline.md` | Rules for reading and writing verdicts from an MCP-driven run: which mod loaded, what the PBO holds, how many samples a negative has. |
| `dayz-mcp-verify/references/dayz-1-30-mcp-verify.md` | What DayZ 1.30 changed for MCP verification. Vanilla script facts cite the 1.30 file on `P:\`. |
| `dayz-mcp-verify/references/linux.md` | The state of the bridge on a Linux host, as measured on 2026-11-06. |
| `dayz-mod-workflow/references` | Implementation workflow pack. Front index: `dayz-mod-workflow/SKILL.md`. |
| `dayz-mod-workflow/references/pre-implementation-grill.md` | The questions to settle with the user before writing the `config.cpp`, `model.cfg` or scripts of a placeable or usable object. |
| `dayz-mod-workflow/references/checklists.md` | What to verify in each kind of file before a mod file counts as written. |
| `dayz-mod-workflow/references/error-catalog.md` | Mistakes made more than once while implementing DayZ mods (E01 to E35), each with the correct form. |
| `dayz-mod-workflow/references/debug-protocol.md` | Diagnosing a feature that "doesn't work" after it was implemented: six layers checked top down, rules for probes, component bisection. |
| `dayz-mod-workflow/references/test-loop.md` | The fast script-only test loop with DayZDiag and file patching, when to stop iterating, and the debugging tools the vanilla scripts offer. |
| `dayz-mod-workflow/references/measurement-discipline.md` | Part checked: reading numbers out of a test session without fooling yourself: aligning client and server series and three statistical traps. Method and measured results; only the script calls are checked on `P:`. |
| `dayz-mod-workflow/references/audit-escalation.md` | Labelling the severity of an audit finding and of something missing, and keeping parallel auditors independent. |
| `dayz-mod-workflow/references/concurrent-session-snapshot.md` | What a session does when the skill files may be rewritten by another session while it runs. |
| `dayz-mod-workflow/references/dayz-1-30-mod-workflow.md` | What 1.30 changed in the contracts the workflow checks: the action start gate, Central Economy root classes, `cfggameplay.json`, the underground trigger editor, headless guards. Read on `P:\`; later 1.30 builds are marked. |
| `dayz-mod-workflow/references/dayz-1-30-server-measured.md` | Measured on the native Linux server, not yet checked on `P:\`: what was observed by booting test mods on a 1.30 dedicated server that a source file cannot show. |
| `dayz-feature-spec/references` | Feature spec pack. Front index: `dayz-feature-spec/SKILL.md`. A method; it states no game facts. |
| `dayz-feature-spec/references/spec-template.md` | The template Step 1 fills in: one copy per feature, kept next to the plan. |
| `dayz-feature-spec/references/spec-checklist.md` | The 18 checks Step 2 runs against a feature spec before any code is written. |
| `dayz-feature-spec/references/analyze-gate.md` | The read-only consistency pass Step 3 runs over a feature's artifacts before an in-game test is spent on them. |
| `rigorous-data-audit/references` | Data audit pack. Front index: `rigorous-data-audit/SKILL.md`. Audit method and lessons from third-party mods; the few vanilla facts cite their file. |
| `rigorous-data-audit/references/audit-prompts.md` | The text to paste into each review of a data audit: the shared preamble, one prompt per audit angle, the verifier prompt, the implementer-grade prompt. |
| `rigorous-data-audit/references/dayz-persistence-facts.md` | Two engine properties every mod with saved data inherits: no rename or move for files, and a base class that writes a varying number of values into the save stream. |
| `rigorous-data-audit/references/path-naming-matrix.md` | Mechanical check 1: a path helper and a recovery or cleanup site that disagree on the file name on disk. |
| `rigorous-data-audit/references/sidecar-cleanup-symmetry.md` | Mechanical check 2: a writer creates a sidecar or marker file and the matching cleanup site fails to remove it. |
| `rigorous-data-audit/references/entry-point-audit.md` | Mechanical check 3: the canonical path enforces an invariant but an alternative entry point skips it. |
| `rigorous-data-audit/references/flag-lifecycle-audit.md` | Mechanical check 4: two state stores that must move together, where one moves without the other. |
| `rigorous-data-audit/references/state-machine-matrix.md` | Structural check: illegal transitions, state counted twice, and "should never happen" branches that can happen. |
| `rigorous-data-audit/references/engine-hooks-and-super-chain.md` | Checks for code that overrides an engine event or relies on a `modded class` hook: what the event delivers and whether every class calls `super`. |
| `rigorous-data-audit/references/incremental-rebuild-traps.md` | Three defect classes that appear when a rebuild that ran in one call is spread over several ticks. |
| `rigorous-data-audit/references/evidence-and-controls.md` | Telling real evidence from evidence that only looks real: the deployed build against the source, controls that can fail, complete inventories. |
| `rigorous-data-audit/references/fix-and-reaudit-traps.md` | What goes wrong when fixing and auditing again: a missed sibling call-site, two correct fixes that break each other, a corrective never audited. |
| `rigorous-data-audit/references/authority-and-loopback.md` | Audit rules for lease queues, local daemons and any control plane on localhost. Tooling around a mod; nothing here can be checked on `P:\`. |
| `rigorous-data-audit/references/crash-safe-evidence-and-bundles.md` | Audit rules for a long evidence campaign, a generated final index, or a release that publishes into more than one root. Tooling; nothing here can be checked on `P:\`. |
| `rigorous-data-audit/references/fact-audit-postmortem.md` | Case study: a fact audit run by four parallel agents with no verification step, most of whose critical findings were wrong. Not facts about DayZ; do not act on any row. |
| `rigorous-data-audit/references/why-this-skill-exists.md` | Case study behind the procedure: six reasoning agents signed off a storage mod and an outside auditor then found 12 vulnerabilities. |
| `systematic-debugging/references` | Debugging method notes. Front index: `systematic-debugging/SKILL.md`. General method with TypeScript examples; no game facts. |
| `systematic-debugging/references/root-cause-tracing.md` | Tracing a bug backward through the call chain to the code that first produced the bad value. |
| `systematic-debugging/references/defense-in-depth.md` | What to add after the root cause is found: a check at every layer the bad data passes through. |
| `systematic-debugging/references/condition-based-waiting.md` | Fixing a flaky test that sleeps for a guessed time: wait for the condition, with a timeout. |
| `task-observer/references` | Task observer notes. Front index: `task-observer/SKILL.md`. Agent tooling; no game facts. |
| `task-observer/references/signals.md` | The full catalogue, with examples, of what the observer watches for. |
| `task-observer/references/observation-log.md` | The observation log: storage layout, scripts and rationale. |
| `task-observer/references/weekly-review.md` | The comprehensive review that cross-checks open observations against all skills. |
| `task-observer/references/skill-authoring.md` | Structure, taxonomy, licensing, confidentiality and editing rules to load before creating or changing a skill; the repo's own rules win where they differ. |
| `task-observer/references/environments.md` | Setup, compaction and resume behaviour, and running without filesystem access. |
| `task-observer/references/migration.md` | Upgrading a single-file observation log from before version 3.0. |
| `enforce-script-reference/references` | Enforce Script depth pack: measured failures and rules from mod projects. Front index: `enforce-script-reference/SKILL.md`. Part checked throughout: a line cited as `P:\...:N` was opened; measurements and third-party mod facts were not re-run. |
| `enforce-script-reference/references/hard-rules.md` | The rules to apply to every piece of Enforce Script, each tied to a crash, a failed compile or a silent failure seen in a real mod. |
| `enforce-script-reference/references/compiler-traps.md` | Ways to break the compiler that give a misleading error, or none until the module compiles at boot. |
| `enforce-script-reference/references/runtime-traps.md` | Failures that compile cleanly and then crash or do nothing at run time. |
| `enforce-script-reference/references/pitfalls-advanced.md` | Compiler quirks, runtime crashes, `modded class` rules, scoping traps, debugging tools and the DayZ 1.30 traps. |
| `enforce-script-reference/references/memory-management.md` | `ref`, `autoptr`, `delete`, reference cycles and the lifetime traps that crash a mod after hours. |
| `enforce-script-reference/references/script-layers.md` | Which script module a class belongs in, what each module can see, the bridge pattern for HUD code, and layer mistakes that compile and then do nothing. |
| `enforce-script-reference/references/api-patterns.md` | Recurring API patterns and the traps measured around them: type identity, entity lifecycle, creating entities, raycasts, temperature, cooking, cameras, inventory moves. |
| `enforce-script-reference/references/networking.md` | Synced variables, `ScriptRPC`, the game level RPC bus, what replicates without custom sync, save and load hooks, file I/O. |
| `enforce-script-reference/references/timers-performance.md` | The timing mechanisms, the `EnProfiler` API and the common optimizations. |
| `enforce-script-reference/references/server-performance.md` | Third-party mod behaviour, not re-run: the server tick performance techniques used across DayZ mods. |
| `enforce-script-reference/references/vanilla-deep-dive.md` | Quick facts on five vanilla systems: recipes and crafting, the energy manager, the action system, the damage pipeline, player internals and sync. |
| `enforce-script-reference/references/verified-api-catalog.md` | A lookup catalog: reflection, global functions, string, math and config lookup patterns, attachment hooks, and the 1.30 engine, inventory, action and mission surface. |
| `enforce-script-reference/references/vehicle-scripting.md` | Script side traps on vehicles: the seated pose, get in, vital parts and engine start, networking with physics, wheels that never join the simulation. |
| `enforce-script-reference/references/weapon-firemodes.md` | Config side fire mode inheritance for weapons: when to inherit and when to override, and the root-scope forward declaration trap. |
| `enforce-script-reference/references/config-cpp.md` | `config.cpp` patterns for mods: the structure every mod's config needs. |
| `enforce-script-reference/references/production-patterns.md` | Not yet checked on `P:\`: UI state, view binding, animation, memory and event patterns from production mods; they use the Dabs Framework classes. |
| `enforce-script-reference/references/dabs-mvc-advanced.md` | Not yet checked on `P:\` or against the Dabs source: patterns and traps for the third-party Dabs Framework's MVC classes. |
| `enforce-script-reference/references/mod-structure-patterns.md` | Third-party mod behaviour, not vanilla: Enforce Script and config patterns of one aircraft mod. |
| `enforce-script-reference/references/review-and-troubleshooting.md` | What to scan for before handing over script code, then a symptom table of error, cause and fix. |
| `enforce-script-reference/references/dayz-1-30-enforce-script.md` | The DayZ 1.30 Enforce Script contract: what replaced the 1.29 hooks. Its line numbers are those of a later 1.30 build than the one on `P:\`. |
| `dayz-ui-development/references` | UI development pack. Front index: `dayz-ui-development/SKILL.md`. Part checked throughout: a `P:\` path with a line was checked on `P:\`; in-game measurements and third-party mod facts were not re-run. |
| `dayz-ui-development/references/layout-format.md` | The brace syntax of a `.layout` file, every widget class and attribute seen in shipped layouts, the script API that goes with them, and layout geometry. |
| `dayz-ui-development/references/styles-format.md` | How the `style` attribute resolves, the format and state names of a `.styles` file, the vanilla styles, and the recipe for a mod's own styles. |
| `dayz-ui-development/references/widget-api.md` | The native methods of each widget class a mod calls, the `WidgetFlags` and `ControlID` enums, the global widget functions, the preview widgets. |
| `dayz-ui-development/references/script-recipes.md` | Copyable building blocks for UI script: binding widget fields by name, event signatures, locking input and showing the cursor, blur, alignment flags. |
| `dayz-ui-development/references/rules-and-checklist.md` | The 18 numbered rules for `.layout` files and UI script, the checklist to run before a UI is done, and a symptom to fix table. |
| `dayz-ui-development/references/vanilla-menus-map.md` | Which vanilla class and layout build each menu and the HUD, registering a modded menu, the `UIScriptedMenu` contract, the focus model. |
| `dayz-ui-development/references/text-sizing-and-rendering.md` | What the engine draws, as measured on a running client: `wrap`, font sizes, alpha, blending, render to texture. |
| `dayz-ui-development/references/theme-and-color.md` | Where UI colors come from, how to scope a recolor request, and the rules of the color system. |
| `dayz-ui-development/references/localization.md` | The two stringtable formats, how layouts and script refer to a key, and the measured rule that decides whether a `stringtable.csv` is registered. |
| `dayz-ui-development/references/advanced-patterns.md` | Unchecked sketches (an audit found calls that do not exist): stacking, toggles, tabs, drag, status bars, hover and input fields. Check every call before use. |
| `dayz-ui-development/references/admin-ui-patterns.md` | Not yet checked on `P:\`: floating windows, world to screen labels, canvas drawing and box selection, as closed source third-party admin mods build them. |
| `dayz-ui-development/references/dabs-framework.md` | Dabs Framework behaviour, not vanilla: the Dabs Framework UI layer: the view lifecycle, commands, observable collections, animation and color helpers. |
| `dayz-ui-development/references/expansion-mvc-patterns.md` | DayZ Expansion behaviour, not vanilla: how DayZ Expansion structures a menu: its MVC classes, menu lifecycle, observable collections, subviews, dialogs, HUD panels. |
| `dayz-ui-development/references/expansion-market-menu-pattern.md` | DayZ Expansion behaviour, not vanilla: the DayZ Expansion Market menu as a worked example of a complete UI feature, end to end. |
| `dayz-ui-development/references/lbgroups-patterns.md` | Third-party mod behaviour, not vanilla: UI patterns of a large production groups mod: chat, map markers, compass, minimap, player list, admin menu. |
| `dayz-ui-development/references/lfpg-knowledge-base.md` | Not yet checked on `P:\`: a fact ledger built while writing one mod's UI: what the engine protos say, what the Dabs source says, and which early assumptions were wrong. |
| `dayz-ui-development/references/community-findings.md` | Five findings on loading screens, imageset names, draw order, layout typos and image progress bars. Each says what was checked on `P:\` and what is not yet checked. |
| `dayz-ui-development/references/layout-empirical-corpus.md` | Not yet checked on `P:\`: counts of widget classes and attributes over real `.layout` files, the coverage of a static renderer, calibration numbers for layout checks. |
| `dayz-ui-development/references/hot-iteration.md` | Measured on 1.29: iterating on a UI without repacking: which paths the running game re-reads, the reload loop and its four traps. |
| `dayz-ui-development/references/layout-variants-130.md` | Measured in game on 1.30: changing a vanilla layout through a layout variant, packing one, scoping it by inheritance. |
| `dayz-ui-development/references/hud-action-info-panels.md` | How the 1.30 interaction cursor shows the tools and materials an action needs: the classes, the layouts, and how a mod adds its own panel. |
| `dayz-ui-development/references/dayz-130-ui-changes.md` | What 1.30 changed in the action prompt HUD, the inventory slot icon classes and the preview widgets, what breaks in a mod, and a migration checklist. |
| `dayz-ui-development/references/cameras-seats-loading-screens.md` | Three lifecycle contracts next to UI work: leaving a scripted camera, opening an interface from a vehicle seat, replacing the loading screen background. |
| `dayz-ui-development/references/plan-to-implementation.md` | Why a built UI differs from its plan in DayZ, and an author, preview, build and verify loop with a parity gate. |
| `dayz-ui-development/references/verification-and-automation.md` | What automated UI checks, probes and test harnesses can and cannot prove. |
| `dayz-ui-development/references/color-test-harness.md` | A diagnostic mod that draws swatches of known colors to measure how UI colors are drawn. A harness, not a pattern to copy. |
| `dayz-model-pipeline/references` | Model generation pack. Front index: `dayz-model-pipeline/SKILL.md`. Part checked throughout: lines that cite `P:\` were opened; winding, axis and tool results were measured on mod projects and not repeated. |
| `dayz-model-pipeline/references/critical-rules.md` | The 21 numbered rules every generated model must meet, and the LOD resolution values they rely on. |
| `dayz-model-pipeline/references/lods-and-geometry.md` | What goes in each LOD of a generated model, the limits that make Binarize or the game reject a LOD, and the Blender object names that become LODs. |
| `dayz-model-pipeline/references/memory-and-selections.md` | Which memory points and named selections a generated model needs, how to create them, and how proxy selections make an attachment show. |
| `dayz-model-pipeline/references/axes-and-winding.md` | Cannot be checked on `P:\`: the measurements behind the Blender to DayZ axis conversion and the face winding rules. |
| `dayz-model-pipeline/references/py3d-direct-generation.md` | The py3d API for building a model in Python: LODs, points, faces, selections, named properties, proxies, reading an existing file. |
| `dayz-model-pipeline/references/py3d-assembly-rules.md` | Rules for writing or editing a `.p3d` with py3d beyond the basic API: where mass may sit, cutting geometry without breaking selections, what the validator's findings mean. |
| `dayz-model-pipeline/references/blender-headless.md` | The Blender Python calls the skill uses to build geometry without the Blender window. Tool knowledge, not game data. |
| `dayz-model-pipeline/references/blender-workflow.md` | Manual Blender steps for a mesh that came from somewhere else: import, cleanup, UVs, LODs, export. Tool knowledge, not game data. |
| `dayz-model-pipeline/references/blender-import-preflight.md` | What to check before geometry work on an imported mesh, and what was measured while reducing and reshaping such meshes. |
| `dayz-model-pipeline/references/animations.md` | A worked reference for the `model.cfg` side of a generated object: skeleton, animation types, config sources, script control, memory axes. |
| `dayz-model-pipeline/references/config-and-packing.md` | The config side of a generated model: folder layout, `$PBOPREFIX$`, the `CfgVehicles` class, proxy attachment classes, a material file, packing. |
| `dayz-model-pipeline/references/rvmat-patterns.md` | Material recipes beyond the basic Super material: flat colors, a damage overlay, lit panels, glass, emissive. |
| `dayz-model-pipeline/references/multi-rvmat-section-texturing.md` | Giving one mesh region two to four tiling detail textures with the `Multi` shader: the mask, the stage and texGen layout, the two UV sets, a template. |
| `dayz-model-pipeline/references/procedural-textures.md` | Generating the `_co`, `_nohq` and `_smdi` maps of a generated model in Python with coherent noise. Tool knowledge and recipes, not game data. |
| `dayz-model-pipeline/references/domain-recipes.md` | Not yet checked on `P:\`: three results measured on real mods: cookware, a client side cable segment, and an asset posed in the hands. |
| `dayz-model-pipeline/references/lfpg-recipes.md` | Third-party mod practice, not vanilla: seven object specifications of one power mod, with its vertex budgets and naming habits, as starting points. |
| `dayz-model-pipeline/references/artist-return-and-provenance.md` | What to check when a `.p3d`, `.paa` or `.rvmat` comes from outside the repo. Process rules learned on mod projects. |
| `dayz-model-pipeline/references/community-findings.md` | Not checked on `P:\`: three unconfirmed findings of medium confidence, to use as red flags during a model audit. |
| `dayz-model-pipeline/references/troubleshooting.md` | Symptom, root cause and fix for the failures the pipeline produces most. Causes and fixes come from mod projects and are not checked on `P:\`. |
| `dayz-model-pipeline/references/dayz-1-30-model-pipeline.md` | What 1.30 changes for meshes, proxies, houses, wells and the model cache, with an evidence label on each line. |
| `dayz-model-pipeline/references/linux.md` | Not yet checked on `P:\`: what changes for the model pipeline on Linux. |
| `dayz-p3d-inspector/references` | P3D inspector notes. Front index: `dayz-p3d-inspector/SKILL.md`. Tool behaviour, not game facts. |
| `dayz-p3d-inspector/references/recipe-format.md` | The data contract between the extractor, the viewer and the builder: the Recipe's fields and how each part is turned back into a `.p3d`. |
| `dayz-p3d-inspector/references/viewer.md` | What the inspector's HTML page shows, how the user works in it, and the design choices that must not be undone. |
| `dayz-p3d-inspector/references/round-trip-caveats.md` | Not yet checked on `P:\`: what an extract, edit and rebuild cycle can lose or misread, and how to test for it. |
| `dayz-3d-viewer/references` | 3D viewer notes. Front index: `dayz-3d-viewer/SKILL.md`. |
| `dayz-3d-viewer/references/formats-and-materials.md` | What the viewer tool supports in `.paa`, `.p3d` and `.rvmat` files, how it turns a material into a Three.js one, and the faults fixed while building it. |
| `dayz-3d-viewer/references/threejs-viewers.md` | No game facts: loading Three.js in a generated viewer page, the fit editor pattern for placing memory points, and testing a viewer page. |
| `dayz-3d-viewer/references/states-animations-leds.md` | Planned, not built: a viewer that plays a model's animations and swaps its materials, with examples from one mod. |
| `3d-generation-harness/references` | 3D generation harness templates. Front index: `3d-generation-harness/SKILL.md`. Working method; no game facts. |
| `3d-generation-harness/references/dossier-template.md` | The Phase 1 research dossier to fill in before any geometry is built. |
| `3d-generation-harness/references/roast-rubric.md` | The scored rubric for the Phase 4 adversarial review: 8 categories, the evidence each needs, the defect list format. |
| `ai-3d-to-dayz/references` | AI mesh to DayZ notes. Front index: `ai-3d-to-dayz/SKILL.md`. |
| `ai-3d-to-dayz/references/mlod-winding.md` | Measured, not yet checked on `P:\`: coordinate map, face order and normals when a generated mesh is written to an MLOD, and reading a winding census. |
| `blender-assembly/references` | Blender assembly notes. Front index: `blender-assembly/SKILL.md`. |
| `blender-assembly/references/detail-scan.md` | Scanning a reference image zone by zone for the detail list, and where each texture-side detail lands in the DayZ texture set. |
| `blender-assembly/references/mcp-render-pitfalls.md` | Two traps that make a render over the Blender MCP disagree with the mesh data. Blender tool behaviour. |
| `blender-visual-review/references` | Visual review notes. Front index: `blender-visual-review/SKILL.md`. Tool behaviour and measurements; no game facts. |
| `blender-visual-review/references/checklist-format.md` | The JSON format of a question checklist for the scoring script and how each question is routed to one image. |
| `blender-visual-review/references/local-vlm-judge.md` | Using a local vision model as a pre-filter on renders: which checklist questions may be delegated and how each was calibrated. |
| `blender-visual-review/references/winding-flip-detection.md` | Measured, not yet checked on `P:\`: catching a reversed face winding in Blender before export, and why a lit render hides it. |
| `uv-clean-atlas/references` | UV atlas pack. Front index: `uv-clean-atlas/SKILL.md`. Results measured on test meshes and tool behaviour throughout, not checked on `P:\`. |
| `uv-clean-atlas/references/mesh-health-and-seams.md` | The checks a mesh must pass before any UV work, the Blender API traps in headless runs, and the seam methods that were measured. |
| `uv-clean-atlas/references/mlod-uv-audit.md` | What to measure on the UVs of a `.p3d` that is already assembled, the traps in measuring it, and one fully measured case. |
| `uv-clean-atlas/references/multi-lod-shared-atlas.md` | Re-unwrapping a model that already ships with a LOD chain, when the only thing that may move is UV. |
| `uv-clean-atlas/references/organic-paint-photograph.md` | Building a paintable atlas for an organic one-shell mesh by projecting it orthographically instead of unwrapping it. |
| `uv-clean-atlas/references/partuv-pilot.md` | Installing and running PartUV, what went wrong, and how it scored against this skill's pipeline on the same meshes. |
| `uv-clean-atlas/references/tool-research.md` | Which automatic or AI unwrap tools were considered and why each was chosen, shortlisted or discarded. |
| `dayz-texture-pipeline/references` | Texture pipeline pack. Front index: `dayz-texture-pipeline/SKILL.md`. Part checked throughout: a `P:\` citation was checked on the vanilla files; "measured" blocks name their project and were not rechecked unless they say so. |
| `dayz-texture-pipeline/references/map-conventions.md` | How each texture map is oriented, packed and levelled: the normal map convention, `_nohq` and `_smdi` storage, getting from metallic and roughness to `_smdi`. |
| `dayz-texture-pipeline/references/rvmat-cookbook.md` | Patterns for writing a `.rvmat`: which route fits the goal, the Super template, damage, emissive, glass, alpha decals, penetration materials. |
| `dayz-texture-pipeline/references/config-and-damage.md` | How textures and materials are connected in `config.cpp`: hidden selections, health level materials, vehicle light material pairs. |
| `dayz-texture-pipeline/references/baked-atlas-to-paa.md` | The checks between a baked or borrowed texture and a working `.paa`. |
| `dayz-texture-pipeline/references/normal-bake-checklist.md` | Blender practice measured on one mod, not yet checked on `P:\`: the checks a high to low normal bake must pass before the first pass. |
| `dayz-texture-pipeline/references/multi-rvmat-section-texturing.md` | When to use the Multi shader, its stage layout, the two UV sets it needs, painting the mask, and the checks before accepting a Multi material. |
| `dayz-texture-pipeline/references/matpbr-emat-pipeline.md` | Not run in this repo and not yet checked on `P:\`: a second material route for metallic and roughness assets through an `.emat` file. |
| `dayz-texture-pipeline/references/vehicle-materials-and-color-variants.md` | Which shader a vehicle or hard surface part needs, tiled detail on overlapping UVs, and how color variants are wired. |
| `dayz-texture-pipeline/references/ui-textures-and-edds.md` | Measured on one production mod: two rules for full screen UI textures and the `.edds` layout that was tried. |
| `dayz-texture-pipeline/references/validation-checklist.md` | The checks to run before handing texture and material work over. States no game facts of its own. |
| `dayz-animation-pipeline/references` | Animation pipeline pack. Front index: `dayz-animation-pipeline/SKILL.md`. Part checked throughout: vanilla facts cite `P:\`; measured results name their project and build; third-party tool facts are not checked. |
| `dayz-animation-pipeline/references/config-driven-animation.md` | The text animation system (layer 1): `model.cfg`, `config.cpp` and a script call moving a named selection of one `.p3d`. |
| `dayz-animation-pipeline/references/handlebar-and-steering-config.md` | Making a vehicle part turn with the steering through `model.cfg` and two memory points. |
| `dayz-animation-pipeline/references/item-ik-and-hide.md` | Four text patterns for items in hands, hide on attach and switching the animation instance, plus one measured method for syncing a pose with an action. |
| `dayz-animation-pipeline/references/dual-entry-action-pattern.md` | Keeping a player from spinning when they board a vehicle from the other side: the 1.30 directional get in and the scripted snap used before it. |
| `dayz-animation-pipeline/references/selection-painter-for-actions.md` | A tooling pattern for named selections whose surface must be exact enough for the game's action raycasts. |
| `dayz-animation-pipeline/references/anim-graph.md` | Animation graphs: files, commands, variables, instance files and the 1.30 format; 1.29 lines are marked and cannot be checked on `P:\`. |
| `dayz-animation-pipeline/references/player-skeleton.md` | The bones of the player skeleton by zone, for mapping a Blender armature onto it. |
| `dayz-animation-pipeline/references/skeletal-anm-enfusion.md` | The route from keyframes to an `.anm` clip the game loads, for characters, infected, animals and weapons. |
| `dayz-animation-pipeline/references/skeletal-rtm.md` | Cannot be checked on `P:\`: the legacy `.rtm` clip format and its tools. |
| `dayz-animation-pipeline/references/blender-authoring.md` | Tool behaviour and in-game results, not yet checked on `P:\`: authoring keyframes with Blender run from the command line (layer 2). |
| `dayz-animation-pipeline/references/tooling-and-walls.md` | Tool research, not checked on `P:\`: which tool does what, which an agent can run and which the user runs, and the limits no tool gets around. |
| `dayz-animation-pipeline/references/creature-animation.md` | The path from a rigged creature in Blender to one that moves in game: skeleton, export, `model.cfg`, a first graph, AI wiring. The workflow advice is not yet checked on `P:\`. |
| `dayz-animation-pipeline/references/scripted-command-locomotion.md` | What a scripted human command can make the vanilla player graph do. API and graph lines checked on `P:\`; the behaviour was measured in game. |
| `dayz-animation-pipeline/references/vehicle-rider-ik-pose.md` | Solving a seated driver or passenger pose from fixed points on the vehicle model, and how such a pose reaches the game. |
| `dayz-animation-pipeline/references/weapon-in-hands.md` | What decides how a custom weapon sits in the hands: the player's clips, the sights and the memory points a weapon needs. |
| `dayz-animation-pipeline/references/weapon-anim-authoring-viewer.md` | A web page for authoring weapon animations on the player skeleton with IK handles and a keyframe timeline. |
| `dayz-animation-pipeline/references/weapon-anim-blender-complete.md` | The whole route for a custom weapon animation: author in Blender, export, compile in Workbench, map it in an instance file, bind it in script, test. |
| `dayz-animation-pipeline/references/dayz-1-30-animation-changes.md` | The 1.30 changes that touch animation work, what breaks, and what to migrate. File and script lines checked on `P:\`; changelog lines are marked. |
| `dayz-animation-pipeline/references/lessons-and-tooling-notes.md` | Project experience, not yet checked on `P:\`: short rules from mod projects, plus notes on tools and on Linux. |
| `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` | Not checked on `P:\`, historical: write quirks of an old py3d version and the frame check for a rebake script. |
| `dayz-realistic-animation-director/references` | Animation direction pack. Front index: `dayz-realistic-animation-director/SKILL.md`. Vanilla facts cite `P:\`; lines marked "1.30 changelog" are not yet checked on `P:\`. |
| `dayz-realistic-animation-director/references/authority-and-routing.md` | Which skill owns which decision when an animation is authored for DayZ, and what each side hands the other. |
| `dayz-realistic-animation-director/references/motion-quality-contract.md` | The report and contract formats the two scripts share, every check type the validator knows, and how tolerances are chosen. |
| `dayz-realistic-animation-director/references/biomechanics-and-contact.md` | Anatomy, positive contact, relative lock, sliding and collision rules for hands, arms and the things they hold. |
| `dayz-realistic-animation-director/references/domain-gates.md` | Extra checks per kind of animation: player actions, hands with a weapon or object, locomotion, creatures, vehicle occupants, mechanical props. |
| `dayz-realistic-animation-director/references/evidence-and-integration.md` | The evidence ladder from contract to in-game proof, the visual review set, and what to hand the DayZ pipeline. |
| `dayz-realistic-animation-director/references/dayz-1-30-animation-direction.md` | What 1.30 changed for anyone directing animation, what breaks in work made for 1.29, and a migration checklist. |
| `blender-animation/references` | Blender animation pack. Front index: `blender-animation/SKILL.md`. Blender tool knowledge; only the DayZ handoff file states game facts. |
| `blender-animation/references/characters-armatures.md` | Bones, pose spaces, keyframing, Actions, IK, cycles and baking, for animation written as Blender Python code. |
| `blender-animation/references/objects-camera-materials-drivers.md` | The F-curve data model, keyframes and easing, camera rigs, constraints, material and shape key animation, and drivers. |
| `blender-animation/references/physics-sims.md` | Rigid bodies, cloth, soft bodies and particles authored and baked from code, and the export of the result. |
| `blender-animation/references/realism-and-iteration.md` | The twelve animation principles in F-curve terms, fixes for robotic motion, the self-audit, and the review loop for an agent. |
| `blender-animation/references/dayz-handoff.md` | Part checked: what the skill hands to the DayZ animation pipeline: export route, what to key, coordinate conventions, loop notetracks. |
| `mixamo-retarget/references` | Retargeting notes. Front index: `mixamo-retarget/SKILL.md`. |
| `mixamo-retarget/references/bone-mapping-guide.md` | How automatic bone matching works for retargeting, reviewing a map, and fixing bad matches. A guide to a Blender tool; it cites no vanilla file. |
| `ardy-motion-generation/references` | Motion generation notes. Front index: `ardy-motion-generation/SKILL.md`. |
| `ardy-motion-generation/references/dayz-integration-plan.md` | Unverified design: the steps that would turn a generated motion file into a DayZ `.anm`, which are untested, and the open questions. |
| `dayz-characters/references` | Character pack. Front index: `dayz-characters/SKILL.md`. Part checked throughout: a `P:\` path with a line was opened; results marked with a project name were measured on that mod and cannot be checked on `P:\`. |
| `dayz-characters/references/character-rigging.md` | The Blender workflow that gives a custom mesh weights on the vanilla bone names in the canonical bind pose, and the export that carries them into the `.p3d`. |
| `dayz-characters/references/canonical-bind.md` | What the engine binds a character mesh against, the three ways a mesh can miss that bind, and the offline checks that hold. |
| `dayz-characters/references/custom-infected-recipe.md` | Adding a custom infected that reuses the vanilla skeleton, animations and AI with a new mesh: config inheritance, size, LODs, cost. |
| `dayz-characters/references/character-uv-bake.md` | Blender behaviour measured on one project: unwrapping the low-poly character and baking normal and ambient occlusion maps. |
| `dayz-characters/references/character-ragdoll.md` | The data-driven ragdoll 1.30 binds on survivors: where it is bound, the file format, the vanilla bone masses, what a custom body must keep. |
| `dayz-characters/references/worn-clothing-skeleton.md` | The skeleton name a worn clothing model must compile with, the frame a worn mesh is built in, and tests that isolate a worn model that will not follow the body. |
| `dayz-characters/references/winding-gate.md` | What the offline winding and normal gate reads in a source `.p3d`, how to read its verdict, and what it cannot see. |
| `dayz-characters/references/dayz-1-30-characters.md` | The 1.30 changes that touch custom infected and survivors: new infected classes, the graph format, the cower state, skinning, surrender. |
| `dayz-characters/references/case-log.md` | Cannot be checked on `P:\`: the real character imports the skill's rules were learned on, one entry per import. |
| `dayz-characters/references/linux-notes.md` | Tool behaviour, not yet checked on `P:\`: what changes for character work when the mod is built on Linux. |
| `dayz-clothing/references` | Clothing notes. Front index: `dayz-clothing/SKILL.md`. |
| `dayz-clothing/references/autofit-from-official-rig.md` | Tool behaviour, not yet checked on `P:\`: fitting a garment onto the official rig in headless Blender and taking its weights from the rig's body mesh; what worked and what four test rounds refuted. |
| `dayz-weapons/references` | Weapon build pack. Front index: `dayz-weapons/SKILL.md`. Part checked throughout: each fact is marked as read in the cited vanilla file, tested in game on mod projects, or inferred. |
| `dayz-weapons/references/p3d-selection-contract.md` | Which selections and memory points a firearm model must have, what each must cover, and how to check that before a test. |
| `dayz-weapons/references/bone-remap.md` | Which weapon selection maps to which player bone, when a remap is needed, and the rule that the selection must cover the part first. |
| `dayz-weapons/references/cfgweapons-contract.md` | Config inheritance, the chamber, magazine, muzzle and optics entries, fire modes, recoil, dispersion and the config side of jamming. |
| `dayz-weapons/references/import-rule-v4.md` | Measured on one project: the axis swap, normals and winding rule for importing a weapon mesh, and the `model=` path rule. |
| `dayz-weapons/references/dayz-1-30-weapons.md` | What 1.30 changed on the entity side of firearms: new scripts, pistol state getters, magazine detach, new recoil classes, the explosion effect API. |
| `dayz-ai-patterns/references` | AI pattern pack. Front index: `dayz-ai-patterns/SKILL.md`. |
| `dayz-ai-patterns/references/dayz-1-30-ai.md` | What 1.30 changed in vanilla infected, animal and noise code. Blocks marked as exact were read on `P:\`; the 1.29 and Nasdara data statements are not yet checked on `P:\`. |
| `dayz-ai-patterns/references/eai-fsm-combat.md` | DayZ Expansion behaviour, not vanilla, none of it on `P:\`: how the DayZ Expansion AI module puts a unit to sleep, enters combat, builds its state machine and filters targets. |
| `dayz-ai-patterns/references/eai-pathfinding-groups.md` | DayZ Expansion behaviour, not vanilla, none of it on `P:\`: how the DayZ Expansion AI module limits path recalculation, spreads a squad, keeps a formation and throttles perception. |
| `dayz-sound-system/references` | Sound depth pack. Front index: `dayz-sound-system/SKILL.md`. |
| `dayz-sound-system/references/sound-deep-dive.md` | Every part of mod audio in one file: the pipeline, config classes, script signatures, item and player sounds, sync, music, noise, recipes. Facts about its two third-party example mods are not checked on `P:\`. |
| `dayz-sound-system/references/dayz-1-30-sound.md` | What 1.30 changed for mod audio, with the vanilla lines quoted, what breaks in a 1.29 mod, and a migration checklist. |
| `dayz-physics-engine/references` | Physics depth pack. Front index: `dayz-physics-engine/SKILL.md`. Citations were opened on `P:\` (a 1.30 build); lines marked 1.29 were not re-checked. |
| `dayz-physics-engine/references/engine-deep-dive.md` | The full rigid body API, interaction layers, the two raycast families, contacts, the native drop and throw path, the player controller, surfaces, what the engine syncs. |
| `dayz-physics-engine/references/damage-and-transporthit.md` | How damage flows from a source to the script callbacks, the vehicle hit flow line by line, hit zones and armor, bleeding, shock and hit animations. |
| `dayz-physics-engine/references/transport-netsync.md` | Why a vehicle's position replicates and a free body on an item does not, and the script side of the vehicle classes. |
| `dayz-physics-engine/references/ragdoll-and-fall-damage.md` | The 1.30 changes to player physics: the data driven ragdoll file, the two death physics calls, the fall damage curve. |
| `dayz-persistence/references` | Persistence depth pack. Front index: `dayz-persistence/SKILL.md`. Line numbers are from `P:\` (game storage version 144); citations marked 1.29 were not checked there. |
| `dayz-persistence/references/vanilla-stream.md` | The rules for data saved in an entity's own save stream: write and read order, the version argument, the variable width of the base class data. |
| `dayz-persistence/references/sidecar-files.md` | Keeping mod data in its own file under the server profile: the file primitives, the load rules, a recoverable save sequence. |
| `dayz-persistence/references/migration-matrix.md` | The seven kinds of input a reader must classify when a saved format changes, and how vanilla 1.30 handled its own new fields. |
| `dayz-persistence/references/cf-modstorage.md` | Community Framework behaviour, not vanilla, not yet checked on `P:\`: how Community Framework stores one framed block per mod inside an entity's save. |
| `dayz-persistence/references/lifetime-and-storage.md` | Part checked: why placed objects vanish after a restart even when their save code is right. The measurements are in-game probes and were not repeated. |
| `dayz-persistence/references/load-and-restore.md` | Part checked: load failures, restore order and mod registries. The measurements and code reviews come from third-party mods. |
| `dayz-persistence/references/central-economy-files.md` | The structure of the Central Economy files as the 1.30 dedicated server ships them. |
| `dayz-persistence/references/dayz-1-30-persistence.md` | What 1.30 changed in the vanilla save streams, with the vanilla code copied in and compared with `P:\`. |
| `dayz-basebuilding/references` | Base building pack. Front index: `dayz-basebuilding/SKILL.md`. Line numbers are from `P:\` (game storage version 144); citations marked 1.29 were not checked there. |
| `dayz-basebuilding/references/config-contract.md` | Every config field a buildable object needs, with the vanilla code that reads it. |
| `dayz-basebuilding/references/entity-lifecycle.md` | The call chain from crafting a kit to a base surviving a server restart, hop by hop. |
| `dayz-basebuilding/references/placement-and-materials.md` | What decides whether a kit can be placed and whether its recipe can be built: slot stack sizes, the hologram tint, the carry pose, custom wall placement. |
| `dayz-basebuilding/references/fence-gate-case.md` | The vanilla fence as a template for a stateful part: gate state, barbed wire damage, locks and the saved gate fields. |
| `dayz-basebuilding/references/persistence-audit.md` | The hand-off checklist for a base building save change: the synced bit masks. |
| `dayz-basebuilding/references/dayz-1-30-construction-rebuilding.md` | What 1.30 changed in the construction system: the class hierarchy, the type data cache, the second save stream for rebuildable buildings, masonry, the fence code lock. |
| `dayz-doors/references` | Door pack. Front index: `dayz-doors/SKILL.md`. Part checked throughout: the vanilla and 1.30 facts were checked on `P:\`; the three door patterns are not checked on `P:\`. |
| `dayz-doors/references/door-model-cfg-and-config.md` | Every class and key a building door needs in `model.cfg` and `config.cpp`, and the 1.30 rules for opening and locking a door. |
| `dayz-doors/references/lods-and-object-builder.md` | What each LOD of a door model has to hold, the Object Builder checks to run, and the extra memory points 1.30 reads. |
| `dayz-doors/references/worked-examples.md` | Three complete door patterns compared side by side, and the 1.30 lock attachments for building doors. |
| `dayz-underground/references` | Underground pack. Front index: `dayz-underground/SKILL.md`. |
| `dayz-underground/references/underground-triggers.md` | The schema of `cfgundergroundtriggers.json`, how it is loaded and sent to clients, and an untested recipe for a mod bunker. Checked on `P:\` except the parts marked as design or untested. |
| `dayz-underground/references/terrain-holes-evidence.md` | What is known about 1.30 terrain holes and how it was found: the Livonia config, the cell size and the world file version change. |
| `dayz-underground/references/wrp-format-and-road-graph.md` | Part checked: notes on the binary layout of a world file and a pipeline that extracts its road graph. The header facts were checked on `P:\`; the rest is measured work. |
| `dayz-environment-hazards/references` | Environment hazard pack. Front index: `dayz-environment-hazards/SKILL.md`. Checked on `P:\` (DayZ 1.30) except where a line says otherwise. |
| `dayz-environment-hazards/references/sandstorm-shelter.md` | How script reaches the 1.30 sandstorm, how much of it a player feels under shelter, and what a world needs for storms to happen. |
| `dayz-environment-hazards/references/thermal-heatstroke.md` | How 1.30 turns sustained heat into heat stroke: the thermal bias value, its four phases, washing the head, shade, wind on a motorbike or boat. |
| `dayz-environment-hazards/references/ppe-agents.md` | The two dust agents the sandstorm puts on a player, the gear that stops each one, and the symptoms each causes. |
| `dayz-environment-hazards/references/dust-oilpit-nasdara.md` | Where 1.30 dust effects come from, the oil pit effect area, and what the Nasdara world adds; the Nasdara data files are not on `P:\`. |
| `dayz-environment-hazards/references/vanilla-file-map.md` | Which vanilla file holds which part of the 1.30 hazard systems, what could not be checked, and earlier claims that turned out wrong. |
| `dayz-aviation/references` | Aviation pack. Front index: `dayz-aviation/SKILL.md`. Third-party mod behaviour throughout, not vanilla: patterns of aircraft mods and one helicopter project, not yet checked on `P:\` except where a `P:\` path is cited. |
| `dayz-aviation/references/fixed-wing-lm-planes.md` | How one third-party mod builds eight planes and an amphibious car on one base class: config skeleton, base script class, Pawn replication. |
| `dayz-aviation/references/aerodynamics-and-flight-physics.md` | Fixed-wing flight in script: lift, drag and stall, the atmosphere helper, self levelling, seaplane buoyancy, per-aircraft presets. |
| `dayz-aviation/references/animation-and-modelcfg.md` | Animation sources for control surfaces, dials and dampers, the `model.cfg` classes behind them, and aircraft damage zones. |
| `dayz-aviation/references/inputs-and-bindings.md` | How that mod registers its flight inputs, its keyboard and controller scheme, and the stringtable and config tie-in. |
| `dayz-aviation/references/sounds.md` | The sound shader and sound set layout for aircraft engines: the RPM band crossfade, volume modulation, ranges. |
| `dayz-aviation/references/effects-and-lights.md` | Navigation lights, headlights and seaplane water spray on an aircraft. |
| `dayz-aviation/references/combat.md` | Optional weapons on an aircraft: a tracer projectile, hitscan damage with a visual tracer, the fire pipeline, camera shake. |
| `dayz-aviation/references/helicopter-model-comparison.md` | Five helicopter flight models side by side: what they share, monolithic loop against modular aerofoils, kinematic against force based, which to build from. |
| `dayz-aviation/references/helicopter-expansion.md` | How the DayZ Expansion vehicle framework flies helicopters and planes with physics modules and a config driven aerofoil module. |
| `dayz-aviation/references/helicopter-mh6.md` | A force based helicopter mod: Pawn owner state and move replication, the simulate loop, real rigid body forces. |
| `dayz-aviation/references/helicopter-rffs.md` | A kinematic helicopter framework: class layout and a flight loop on set velocity and set orientation. |
| `dayz-aviation/references/helicopter-sib.md` | A kinematic helicopter model: class layout, its simple flight loop, the JSON coefficient store. |
| `dayz-aviation/references/mod-sources.md` | Which Workshop helicopter mods can be read as plain script, which PBO holds the flight code, and which are a dead end. |
| `dayz-aviation/references/flight-testing-and-measurement.md` | Working rules for testing a scripted flight model in game and judging the result from logs. |
| `dayz-aviation/references/model-axes-and-py3d.md` | Why an offset measured from a `.p3d` with py3d can land on the wrong end of the aircraft, and the runtime probe that settles it. The engine facts cite `P:\`. |
| `dayz-aviation/references/thermal-imaging.md` | Why a thermal view cannot be built with post-processing, and the per entity texture and material swap that works. The script calls cite `P:\`. |
| `dayz-aviation/references/dayz-1-30-aviation.md` | Checked on `P:\`: what 1.30 changed underneath an aircraft that inherits `CarScript`: lights, horn, battery and the event mask contract. |
| `dayz-motorbikes/references` | Motorbike pack. Front index: `dayz-motorbikes/SKILL.md`. Read from the 1.30 vanilla files on `P:\`, with each element marked as exact, design or unverified. |
| `dayz-motorbikes/references/config-contract.md` | The `config.cpp` blocks of the vanilla single-track vehicles, and a table of the parameters with the code that reads each one. |
| `dayz-motorbikes/references/script-api.md` | The native interface of the motorbike class, the simulation callbacks, the script lifecycle, net sync variables, and what a motorbike lacks against a car. |
| `dayz-motorbikes/references/actions-hud-lights-sounds.md` | The user actions specific to motorbikes, the HUD structure, the lights, horn and effect components, and the sound classes. |
| `dayz-motorbikes/references/rider-animation.md` | How the rider is animated: the human vehicle command, the vehicle animation graph, the vanilla clips, the camera, and how far a mod can change the pose. |
| `dayz-motorbikes/references/forward-contract.md` | The full specification for a new motorbike in 1.30, each element marked exact, design or unverified. |
| `dayz-motorbikes/references/vehicle-1.30-refactor.md` | How 1.30 restructured the vehicle scripts, and what an existing car mod has to change. |
| `dayz-motorbikes/references/vanilla-p3d-anatomy.md` | Tool output, not yet checked on `P:\`: what the two vanilla motorbike models hold: mass, LODs, skeleton, animations, memory points. |
| `dayz-motorbikes/references/sources.md` | Every vanilla file the skill cites, with its path on `P:\`, its line count there and the symbols read in it. |
| `rip-vehicle-import/references` | Ripped vehicle import pack. Front index: `rip-vehicle-import/SKILL.md`. Part checked throughout: vanilla facts cite the file on `P:\`; the measurements on imported cars are not yet checked on `P:\`. |
| `rip-vehicle-import/references/classify-viewer.md` | Reviewing and changing the classification of a ripped car's parts without opening Blender. |
| `rip-vehicle-import/references/profile-schema.md` | Field by field, what a car profile of the import project holds and which script reads each field (legacy and in flight). |
| `rip-vehicle-import/references/cookbook-get-in-missing.md` | For a car whose get-in prompt never shows: the ordered guards of the action and naming the guard that blocks. |
| `rip-vehicle-import/references/cookbook-door-radial-missing.md` | For a vehicle door that shows no open or close action: the three unrelated door mechanisms and picking the right one. |
| `rip-vehicle-import/references/cookbook-attachment-invisible.md` | For a wheel, door or rack item that is attached and simulates but does not render: the proxy frame contract and the class name rule. |
| `rip-vehicle-import/references/cookbook-wheelpresent-0.md` | For a car whose wheels are attached but do not simulate: the symptom, the refuted fix and where the real gate is. |
| `rip-vehicle-import/references/cookbook-white-car.md` | For a car that renders white on a dedicated server: the include list that drops textures and the two fixes. |
| `rip-vehicle-import/references/history-canonical-path.md` | History: the day-1 checklist and 12-step pipeline a ripped car followed before change 0. |
| `rip-vehicle-import/references/history-family-b-runbook.md` | History only, no authority: the full runbook that change 1 removed from the critical path. |
| `rip-vehicle-import/references/history-retired-artifacts.md` | History: the seven document types a new car no longer produces since change 0. |

### Not file packs

- Vanilla source search is the `dayz-rag` MCP server, not a file. Its rules are in `dayz-conventions.md` ("Vanilla source search").
- Tier 2 topic rules live in `conventions/` and are listed in `dayz-conventions.md`, not here.
