# Knowledge packs

A knowledge pack is Tier 3 reference material: notes, API tables and worked examples for one kind of work. Any DayZ worker may load any pack for one task. Packs are loaded only when the task needs them, never by default. Tier 1 (`.claude/CLAUDE.md`) and Tier 2 (`dayz-conventions.md` plus `conventions/*.md`) still apply on top of every pack.

Every pack is listed below, and no other index of packs exists. Paths are relative to `skills/`. The repo integrity test (`scripts/dev/test_repo_integrity.py`) fails when a pack folder or pack file is missing from this index, or when the index names a `_shared/` or `dayz-*` path that does not exist. It does not check that paths under other skills' `references/` folders exist.

## Pack layout

- **Where a pack lives.** A pack shared by several agents lives under `_shared/`, either as one file (`_shared/<topic>.md`) or as a folder (`_shared/<topic>/`). A pack that belongs to one skill or one specialist lives in that skill's own `references/` folder (`<skill>/references/`). Use the plural `references/`.
- **File naming.** Lowercase, words joined with `-` or `_` to match the neighbouring files, ending in `.md`. Name the file after its subject (`ptc-format-reference.md`, `singleton.md`), not after a ticket or a date.
- **Front index.** Every pack folder has one front index that says which file to open for which question. For a `_shared/` folder it is the folder's `README.md`; for a skill's `references/` folder it is the table in that skill's `SKILL.md`. Each pack file opens with a title and one line saying what it covers.
- **Loaded only when needed.** Agents and skills name the pack file they need at the step that needs it. They never tell a worker to read a whole pack up front.
- **Checked against vanilla.** Facts about the game cite the vanilla file on `P:\` they came from, so a reviewer can check them. The integrity test fails when a pack file under `_shared/` has no vanilla citation (a `P:\` path, or a file:line such as `itembase.c:261`), except the files it lists as exempt: the style guide's section files, the py3d notes, the Tier 2 core, `textures/checking-the-look.md`, the Blender, tool and working-method files of the animation, model, texture and vehicle packs that hold no game fact, and the folder indexes. It checks that each file cites vanilla at least once; skill `references/` packs are not part of this check, and the line by line check is done by the reviewer. A file still marked "not yet checked on `P:\`" below has not been checked line by line; treat its facts as leads, not answers. A row marked "part checked" has its cited `P:\` lines checked, while its measured results, tool behaviour and facts about other mods are not checked; the file's own opening lines say which is which.
- **Which build a citation is from.** A vanilla line number is right for one game build. Some files cite the lines of the build they were checked on, up to the second 1.30 patch, which can be newer than the extraction on `P:\`; a measurement keeps the build it was made on. When a cited line does not match on `P:\`, find the symbol by name before deciding the fact is wrong. The build timeline and the rules for reading a citation are in `_shared/enscript/references/game_builds.md` ("Which line a citation gives"); what each build changed is in the topic packs.
- **Registered here.** A new pack gets a row in this index in the same change.

## Index

### Shared single file packs

| Pack | Purpose |
|---|---|
| `_shared/enscript-style.md` | Enforce Script code style, front index. Every script task opens it, then reads only the one file below that the task needs. |
| `_shared/answer-formatting.md` | How to format answers grounded in vanilla source. |
| `_shared/container-base.md` | Custom `Container_Base` config requirements (damage, bullets, interaction). |
| `_shared/figma-to-dayz-rules.md` | Translation rules for the Figma to DayZ `.layout` pipeline. |
| `_shared/figma-to-dayz-worked-example.md` | One HUD card carried through the Figma pipeline: Figma node, normalized JSON and `.layout`. |
| `_shared/py3d-mlod-notes.md` | Reading MLOD `.p3d` files with py3d, used by `/dayz-p3d-audit`. |
| `_shared/linux-proton.md` | Not yet checked on `P:\`: the Linux supplement to the Windows skills: which step has a native Linux equivalent, which runs under Proton and how, and what was not checked. |

### Shared helper code

The Linux and Proton shell helpers, the script API index builder and its lookup now live in `scripts/tools/dayz-linux/` (its `README.md` says which script answers which question).

| Folder or file | Purpose |
|---|---|
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
| `_shared/enscript/depth` | Enforce Script depth pack: measured failures and rules from mod projects. Front index: `_shared/enscript/depth/README.md`. Part checked throughout: a line cited as `P:\...:N` was opened; measurements and third-party mod facts were not re-run. |

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
| `_shared/enscript/integrations/community_framework.md` | Community Framework modules, `GetRPCManager()`, event handlers. Checked against the shipped CF scripts PBO. |
| `_shared/enscript/integrations/lbmaster.md` | LBmaster loot presets (third party): optional dependency, which spawn call honours the preset chance, the loot source fallback order. Checked against `LBmaster_Core.pbo`. |
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
| `_shared/enscript/references/mission_lifecycle.md` | Checked on `P:`: the order in which `MissionServer` and `MissionGameplay` run their constructor, `OnInit`, `OnMissionStart` and `OnUpdate`, the exact `super` chain, and how an RPC with no target is routed. |
| `_shared/enscript/references/input_user_data.md` | Checked on `P:`: `ScriptInputUserData`, the channel that carries a player's own input to the server, and when to use it instead of `ScriptRPC`. |
| `_shared/enscript/references/network_payload_limits.md` | Measured, not yet checked on `P:\` beyond the class declarations: payload sizes over `ScriptRPC` and `ScriptInputUserData`, arrays of each type, input queue depth, RPC order, what an acknowledgement proves. |
| `_shared/enscript/references/native_declarations.md` | Checked on `P:`: where the `proto native` declarations are, what `owned` and `static` mean on one, and calling a native that fills an array or returns a handle. |
| `_shared/enscript/references/entity_components.md` | Checked on `P:`: `GenericEntity`, `GenericComponent` and `ScriptComponent`: the `COMPONENT_SYSTEM` guard, insert and remove, event order, event masks. |
| `_shared/enscript/references/workbench_api.md` | The Enforce Script surface that extends Workbench: entry points, the resource manager and script editor modules, plugin events, the `WORKBENCH` guard. For plugin authors, not game scripts. |
| `_shared/enscript/references/game_builds.md` | Which DayZ build a vanilla line number or a measurement belongs to, which build `P:\` holds, and the rules the 1.30 patch line taught. |
| `_shared/enscript/examples/layouts.md` | Checked on `P:`: what the three example layouts are, with their companion scripts. |
| `_shared/enscript/depth/hard-rules.md` | Which rules apply to every piece of Enforce Script, each tied to a crash, a failed compile or a silent failure seen in a real mod. |
| `_shared/enscript/depth/compiler-traps.md` | Ways to break the compiler that give a misleading error, or none until the module compiles at boot. |
| `_shared/enscript/depth/runtime-traps.md` | Failures that compile cleanly and then crash or do nothing at run time. |
| `_shared/enscript/depth/pitfalls-advanced.md` | Which code the Enforce compiler mishandles or rejects with a confusing message, how to read the script log when a module fails, and the scoping traps. |
| `_shared/enscript/depth/memory-management.md` | `ref`, `autoptr`, `delete`, reference cycles and the lifetime traps that crash a mod after hours. |
| `_shared/enscript/depth/script-layers.md` | Which script module a class belongs in, what each module can see, the bridge pattern for HUD code, and layer mistakes that compile and then do nothing. |
| `_shared/enscript/depth/api-patterns.md` | Recurring API patterns and the traps measured around them: type identity, entity lifecycle, creating entities, raycasts, temperature, cooking, cameras, inventory moves. |
| `_shared/enscript/depth/networking.md` | How state reaches clients: synced variables, which server calls replicate on their own, why client-only visual writes get overwritten, and how to tell the sides apart during load. |
| `_shared/enscript/depth/timers.md` | How `CallLater` and `Timer` behave over long uptimes, the reports against `CallLater`, and how to run many periodic devices from one tick. |
| `_shared/enscript/depth/server-performance.md` | Third-party mod behaviour, not re-run: how to keep many entities inside one server tick: a work budget per tick that stays fair, intervals that stretch with load, scans spread across ticks, and backoff for idle entities. |
| `_shared/enscript/depth/actions-and-player-sync.md` | How vanilla registers actions and measures their reach, and how player stamina, synced modifiers, stats and agents travel to the client. |
| `_shared/enscript/depth/reflection-api.md` | How production mods use Enforce Script reflection for data binding, registration at load time and calling by name, with worked examples and the limits that make a reflection based test unsafe. |
| `_shared/enscript/depth/vehicle-scripting.md` | Script side traps on vehicles: the seated pose, get in, vital parts and engine start, networking with physics, wheels that never join the simulation. |
| `_shared/enscript/depth/config-cpp.md` | `config.cpp` patterns for mods: the structure every mod's config needs. |
| `_shared/enscript/depth/production-patterns.md` | Not yet checked on `P:\`: how shipped mods keep a panel's hover, disabled and animated states consistent, batch widget updates, lock and release input, and what an action on the cursor promises. |
| `_shared/enscript/depth/dabs-mvc-advanced.md` | Not yet checked on `P:\` or against the Dabs source: which Dabs Framework MVC habits break a view in shipped mods: property notification, creating views, auto binding inside buttons, `Relay_Command` firing twice, collection leaks and a second controller. |
| `_shared/enscript/depth/mod-structure-patterns.md` | Third-party mod behaviour, not vanilla: how a mod declares its script modules in `CfgMods`, hides a library from the mod list, splits into a parent and feature mods, and registers custom inputs with keys that do not fight vanilla. |
| `_shared/enscript/depth/review-and-troubleshooting.md` | What to scan for before handing over script code, then a symptom table of error, cause and fix. |
| `_shared/enscript/depth/dayz-1-30-enforce-script.md` | What changed for Enforce Script in DayZ 1.30, what breaks in a mod written for 1.29, and what to write instead. |
| `_shared/enscript/depth/action-and-input-rules.md` | Which rules keep actions, recipes, liquid containers, input files and vehicle sights working, each tied to a failure seen in a real mod. |
| `_shared/enscript/depth/actions-mission-api.md` | Which base classes, condition components, overrides and registration calls an action uses, and which `MissionServer` events run when a player connects, respawns or leaves. |
| `_shared/enscript/depth/buildings-and-sound-config.md` | How a static building declares animated doors, how it stays indestructible while its doors take damage, which keys a `CfgSoundSets` entry uses, and which model details need no script. |
| `_shared/enscript/depth/dabs-floating-windows.md` | How a mod's draggable window takes the cursor without a full screen modal, gives input back, and handles colour, button hover and screen size. |
| `_shared/enscript/depth/dayz-1-30-actions.md` | What changed in the 1.30 action system: info only actions, action manager states, the liquid action, animation overrides, target conditions, new inputs, recipes and the targets cursor. |
| `_shared/enscript/depth/dayz-1-30-inventory.md` | How DayZ 1.30 runs inventory commands, where a mod can still watch item moves, how stacking and splitting differ from a move, and which take calls and hand guards changed. |
| `_shared/enscript/depth/entity-inventory-api.md` | Where the common entity, player, item and inventory calls are declared: attach and detach hooks, showing and hiding selections, slot lists, texture getters, type checks, player stats, inventory moves and quantity, and what 1.30 renamed. |
| `_shared/enscript/depth/global-functions.md` | Which global calls production mods rely on for the screen, debugging, launch parameters, files, web requests, sound, notifications, players, nearby objects, JSON, frame callbacks, key bindings, weather and bones, with a short example of each. |
| `_shared/enscript/depth/language-builtins.md` | What the language allows (parameter count, generic classes, typedefs, float constants), how the string and math calls behave, how to look up config, and the language additions in 1.30. |
| `_shared/enscript/depth/modded-class-and-defines.md` | How a `modded class` adds to a vanilla class safely, which vanilla methods it must call `super` on, where its declaration must live, and how to gate code on another mod or on diag builds. |
| `_shared/enscript/depth/persistence-and-files.md` | How an entity saves its fields across restarts with its own version number, which config key makes it persistent, and which file calls to use for JSON and safe writes. |
| `_shared/enscript/depth/rpc-and-input-patterns.md` | How shipped mods number their RPCs, keep a client action responsive while the server decides, send to every client, cache input lookups, and skip client-only work on a dedicated server. |
| `_shared/enscript/depth/rpc-manager-and-cf.md` | How the common third-party pattern sends every RPC on one ID with a function name for dispatch, what it costs, and how Community Framework modules receive events and dispatch RPCs in single player. |
| `_shared/enscript/depth/rpc-routing.md` | How a `ScriptRPC` is sent and where it lands, why a server reply must target the player entity, what the server checks before acting, and how to read `Event_OnRPC` without eating another handler's data. |
| `_shared/enscript/depth/runtime-pitfalls.md` | Which code compiles and then crashes, loses items or slows the server: array element assignment, shaders on a dedicated server, hologram ghosts, merge loops, float time, slow world queries, and the retail replacements for diag-only plugins. |
| `_shared/enscript/depth/script-profiling.md` | How to find the expensive script with `EnProfiler`, and the cheap fixes for what it usually finds: strings built every tick, repeated `IsKindOf` and config reads, square roots in distance checks, and one RPC per device. |
| `_shared/enscript/depth/server-side-gates.md` | When to keep work off the client with `#ifdef SERVER` and when to branch at runtime, why `#ifndef SERVER` can break other mods, why an event bus beats polling, and which changes actually lower a dedicated server's script memory. |
| `_shared/enscript/depth/ui-view-lifecycle.md` | How shipped mods decide what to bind, release bound collections and singleton views, avoid allocating in update loops, and route many buttons. |
| `_shared/enscript/depth/vehicle-script-helpers.md` | How shipped vehicle mods keep animation and sync cheap, stop an empty vehicle spinning, clean up effects on every removal path, detect water, resolve damage zones, find the local driver and pick a seat animation. |

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
| `_shared/physics/player-controller.md` | Part checked: the player's character controller, the script calls on it, moving platforms, lifting and walking a player from script. The measured results come from in-game test mods and cannot be checked on `P:\`. |
| `_shared/physics/rigid-body-api.md` | Creating, waking, moving and removing a physics body from script, where friction and bounce come from, the calls that do not exist. |
| `_shared/physics/scripted-triggers.md` | The script API under every scripted trigger: `ScriptedEntity` and its collision shapes, enter and leave events, the server and client hooks of `TriggerEvents`. |
| `_shared/physics/water-queries.md` | Part checked: what the engine's water queries return over river and stream pieces, the streambed kit and a roadway water face. Declarations checked on `P:`; every number was measured in game. |
| `_shared/physics/damage-pipeline.md` | What happens after a contact decides to deal damage: the calls that deal and read damage, the order of the `EEHitBy` callbacks, damage zones, bleeding, shock, the hit animation. |
| `_shared/physics/joints.md` | The joint calls that tie two physics bodies together. No vanilla script creates a joint, so each limit's behaviour must be confirmed in game. |
| `_shared/physics/surfaces.md` | What script can read about a surface (ground, model face, liquid), where surfaces and `CfgSurfaces` keys are defined, and what it cannot read. |
| `_shared/physics/ragdoll-and-fall-damage.md` | The player ragdoll calls, the 1.30 changes, ragdolling a living player, waking from unconsciousness safely, and the fall damage curve. |

### Animation pack (`_shared/animation`)

Front index: `_shared/animation/README.md`. Used by `dayz-animation-specialist`.

| Folder or file | Purpose |
|---|---|
| `_shared/animation` | Moving parts and doors, clips, graphs and skeletons, items, weapons and riders in the hands, Blender authoring, realistic motion and its checker, and two experimental routes. The front index groups the files the same way. |
| `_shared/animation/model-cfg-animations.md` | Skeleton bones and the `Animations` block: keys, radians, value ranges, names in vanilla models. |
| `_shared/animation/animation-sources.md` | `AnimationSources` for items and `class Doors` for buildings. |
| `_shared/animation/script-hooks.md` | `SetAnimationPhase`, the door API and the vanilla barrel and fence patterns. |
| `_shared/animation/rtm-and-character-animation.md` | Where vanilla uses `.rtm`, how character animation differs, and what the graph layer allows without replacing it (a per-item clip through a child `.asi`); editing the player or infected graph stays out of scope. |
| `_shared/animation/blender-handoff.md` | Naming and export notes for parts modelled in Blender. |
| `_shared/animation/anim-graphs.md` | What the animation graph that drives characters and creatures holds: where its files are, the `CMD_` commands the engine, AI and script send, the variables that steer blending, terrain alignment, tags, and which mod changes collide. |
| `_shared/animation/items-in-hands.md` | How the game picks the pose of a held item, how a mod registers its own items, and how script switches the player's animation instance. |
| `_shared/animation/attach-state-parts.md` | The vanilla ways to show, hide or swap model parts with attach state: a host part that follows a slot, and an item with two models. |
| `_shared/animation/rider-poses.md` | How the vanilla graph poses a player on a vehicle, what that means for a mod vehicle of another shape, and the one way to change the pose for a single vehicle class. |
| `_shared/animation/building-doors.md` | Doors, hatches and lids on buildings and static props, the buttons or levers that drive them, the LOD contract and the 1.30 lock rules; the entry point for door work. |
| `_shared/animation/door-config-and-locks.md` | Part checked: which classes and keys a building door needs in `model.cfg` and `config.cpp`, what each one does, and which values the three worked patterns use. |
| `_shared/animation/door-lods.md` | Part checked: what each LOD of a door model holds, the Object Builder checks, and the extra memory points 1.30 reads. |
| `_shared/animation/door-patterns.md` | Part checked: how three complete door samples are wired, side by side: a door with a handle, a door opened by a button, and a door with a handle and a lever. |
| `_shared/animation/handlebar-and-steering.md` | Making a steering wheel, handlebar or rudder turn with the steering through `model.cfg` and two memory points. |
| `_shared/animation/get-in-sides.md` | Keeping a player from spinning when they board from the other side of a seat: the 1.30 directional get in and the scripted snap used before it. |
| `_shared/animation/selections-for-actions.md` | Measured on one model, no vanilla facts: painting named selections exact enough for action raycasts (seat, grip, door handle). |
| `_shared/animation/tooling-and-walls.md` | Tool facts not checked on `P:\`: which tool does what, which the agent runs and which the user runs, the limits no tool gets around, what a handoff must say. |
| `_shared/animation/anm-clips.md` | The route from keyframes to an `.anm` clip the game loads, for characters, infected, animals and weapons. |
| `_shared/animation/scripted-commands.md` | What a scripted human command can make the vanilla player graph do, and what breaks on the way. API and graph lines checked on `P:\`; the behaviour was measured in game. |
| `_shared/animation/player-skeleton.md` | The bones of the player skeleton by zone, for mapping a Blender armature onto it. The measured parent table is the text file `player-skeleton-parents.txt` beside it. |
| `_shared/animation/creature-rig-to-game.md` | From a rigged creature in Blender to one that moves in game: skeleton, export, `model.cfg`, a first graph, AI wiring. The workflow advice is not yet checked on `P:\`. |
| `_shared/animation/dayz-1-30-changes.md` | What 1.30 changed for building and directing animation, what breaks in 1.29 work, and the migration checklist. Changelog lines are marked. |
| `_shared/animation/weapon-in-hands.md` | What decides how a custom weapon sits in the hands and the sights, and the memory points a weapon needs. |
| `_shared/animation/weapon-anim-blender.md` | What a custom player weapon animation is, which route and tools it uses, how to set up Blender and the plugin, the rig and its IK helpers, and how to start from a vanilla pose. |
| `_shared/animation/weapon-anim-viewer.md` | A web page for authoring weapon animations on the player skeleton with IK handles and a keyframe timeline, exported as SEAnim. |
| `_shared/animation/rider-pose-solver.md` | How to get a driver's or passenger's seated pose by solving it from a few fixed points on the vehicle model instead of keying the body bone by bone, and how the solved pose becomes clips. |
| `_shared/animation/blender-mcp-workflow.md` | Driving the user's live Blender through the Blender MCP server for animation: preflight, API breaks, runtime rules, authoring stages, checks before delivery. Blender tool behaviour, no game facts. |
| `_shared/animation/blender-txa-export.md` | Part checked: what a Blender session hands to the DayZ animation pipeline when the motion is for a DayZ character or weapon: which export route to take, what to deliver, and how the DayZ animation plugin must be set up. |
| `_shared/animation/blender-headless-authoring.md` | Tool behaviour and in-game results, not yet checked on `P:\`: authoring keyframes with Blender run from the command line. |
| `_shared/animation/blender-bpy-armatures.md` | How a script reads and sets bone poses in Blender: which matrix lives in which space, the three ways to set a pose, the space names, and how to choose rotation modes. |
| `_shared/animation/blender-bpy-objects-camera.md` | How a script animates a camera in Blender (lens, focus, aim, paths, orbits), sets up constraints and parenting without the jump, and reads motion paths back for checking arcs. |
| `_shared/animation/blender-bpy-physics.md` | How a script adds rigid bodies and their constraints in Blender, sets mass, shape and bounce, throws an object with a starting speed, and avoids the scale, origin and gravity traps. |
| `_shared/animation/blender-realism-and-review.md` | How the twelve animation principles show up in F-curves and how a script applies each one in Blender, what makes scripted motion read robotic and how to fix it, frame counts for common actions, and how a camera should move. |
| `_shared/animation/realistic-motion.md` | Directing motion that must look physically believable: measurable motion contracts, gates per stage and evidence states. The checker scripts are in `dayz-animation-pipeline/scripts`. |
| `_shared/animation/motion-authority-and-routing.md` | Which file or skill owns which decision when an animation is authored, and what each side hands the other. |
| `_shared/animation/motion-contract.md` | The report and contract formats the motion scripts share, every check type the validator knows, and how tolerances are chosen. |
| `_shared/animation/motion-biomechanics.md` | Anatomy, positive contact, relative lock, sliding and collision rules for hands, arms and what they hold. |
| `_shared/animation/motion-domain-gates.md` | Extra checks per kind of animation: player actions, hands with a weapon or object, locomotion, creatures, vehicle occupants, props, physics simulation. |
| `_shared/animation/motion-evidence.md` | The evidence ladder from contract to in-game proof, the visual review set, and what to hand the DayZ pipeline. |
| `_shared/animation/mixamo-retarget.md` | Experimental, untested in Blender: retargeting Mixamo or other FBX motion capture onto a Blender rig with the pipeline's two modules. |
| `_shared/animation/mixamo-bone-mapping.md` | Experimental, no game facts: how automatic bone matching works, reviewing a map, fixing bad matches. |
| `_shared/animation/motion-generation-ardy.md` | Experimental, nothing has reached the game: generated survivor locomotion with ARDY and the untested route into DayZ. |

### Model and LOD pack (`_shared/models`)

Front index: `_shared/models/README.md`. Written for `dayz-object-builder`.

| Folder or file | Purpose |
|---|---|
| `_shared/models` | What a `.p3d` needs inside, LOD by LOD, and the model side of animated doors. |
| `_shared/models/lods.md` | LOD types vanilla uses, their order, visual LOD numbering, and the Geometry, Fire Geometry and View Geometry rules. |
| `_shared/models/memory-points.md` | Memory LOD rules, axes, and the point names vanilla script looks up. |
| `_shared/models/named-properties.md` | Named properties vanilla sets, mass, and the `autocenter` rule. |
| `_shared/models/proxies.md` | Proxy names, indexes and paths, and the config class an attachment proxy needs. |
| `_shared/animation/doors.md` | Door bones, axes, components and action points; the door actions; who writes each part. |
| `_shared/models/selections.md` | What a named selection in a `.p3d` is, which LOD each kind belongs in, who reads it, and how tools lose it without a word. |
| `_shared/models/building-selections.md` | The names a building or ladder model carries: door leaves and their points, the two ladder schemes, Paths LOD points, loot and rain sound points, `liquid_source`. |
| `_shared/models/proxy-frames.md` | Part checked: how a proxy triangle becomes a position and a facing, and the crew seat, body part, clothing and weapon attachment cases. Names, paths and config classes checked on `P:`; the frame rules are not checked. |
| `_shared/models/uv-mapping.md` | Part checked: how UVs are stored in a `.p3d`, which UV set each material stage reads, what binarizing does to them, tracing a texture fault to the UVs. Material and config facts checked on `P:`; format details and measurements are not. |
| `_shared/models/multi-rvmat-texturing.md` | How vanilla textures one mesh with up to four tiling surfaces through one `Multi` shader material: the mask, the two UV sets and faces with no texture of their own. |
| `_shared/models/axes-and-winding.md` | How geometry from Blender, FBX, OBJ, glTF or an AI generator maps into DayZ space, which way faces wind in each LOD, and telling a correct export from an inside out or mirrored one. |
| `_shared/models/tools-p3d-inspector.md` | Running the p3d inspector scripts of `dayz-model-tools`: a source `.p3d` read into one Recipe JSON, edited in a browser, built back into a `.p3d`. Tool behaviour. |
| `_shared/models/tools-p3d-inspector-recipe.md` | Tool behaviour: the Recipe JSON fields, the LOD types it knows, and how each part is written back into a `.p3d`. |
| `_shared/models/tools-p3d-inspector-viewer.md` | Tool behaviour: what the inspector's HTML page shows, how the user works in it, and the design choices that must not be undone. |
| `_shared/models/tools-p3d-inspector-round-trip.md` | Not yet checked on `P:\`: what an extract, edit and rebuild cycle can lose or misread, and how to test for it. |
| `_shared/models/tools-proxy-align.md` | Tool behaviour: aligning proxy triangles on a host model with the proxy editor scripts of `dayz-model-tools`. |
| `_shared/models/tools-winding-gate.md` | Tool behaviour: what the offline winding and normal gate `check_dayz_winding.py` reads in a source `.p3d`, how to read its verdict, and what it cannot see. |
| `_shared/models/tools-3d-viewer.md` | Tool behaviour: running the `.p3d` to `.glb` converter in `scripts/tools/dayz-3d-viewer` and reading its HTML page. |
| `_shared/models/tools-3d-viewer-formats.md` | What the viewer in `scripts/tools/dayz-3d-viewer` supports in `.paa`, `.p3d` and `.rvmat` files and how it turns a material into a Three.js one. Vanilla checks made on `P:\`; the rest is tool behaviour. |
| `_shared/models/tools-threejs-viewers.md` | No game facts: loading Three.js in a generated viewer page, the fit editor pattern for placing memory points, testing a viewer page. |
| `_shared/models/tools-uv-mesh-health.md` | Measured on test meshes, not checked on `P:\`: the checks a mesh must pass before UV work, Blender API traps in headless runs, and the seam methods measured. |
| `_shared/models/tools-uv-mlod-audit.md` | Measured, not checked on `P:\`: what to measure on the UVs of an assembled `.p3d`, the traps in measuring it, and one measured case. |
| `_shared/models/tools-uv-multi-lod-atlas.md` | Measured, not checked on `P:\`: re-unwrapping a model that already ships with a LOD chain when only UV may move. |
| `_shared/models/tools-uv-organic-photograph.md` | Measured, not checked on `P:\`: a paintable atlas for an organic one-shell mesh made by projecting it instead of unwrapping it. |
| `_shared/models/tools-uv-partuv.md` | Tool behaviour: installing and running PartUV, what went wrong, and how it scored on the same meshes. |
| `_shared/models/tools-uv-tool-survey.md` | Tool research: which automatic or AI unwrap tools were considered and why each was chosen, shortlisted or discarded. |
| `_shared/models/tools-uv-atlas.md` | Measured, not checked on `P:\`: turning a hard-surface mesh into a readable UV atlas with the clean atlas scripts of `dayz-model-tools`. |
| `_shared/models/tools-uv-atlas-traps.md` | Measured, not checked on `P:\`: the Blender, SLIM, fold guard, smoothing and Windows traps that silently break the clean UV atlas pipeline. |
| `_shared/models/blender-assembly.md` | How to build a hard surface model in Blender through a Blender MCP server without exploded parts, wrong sizes, broken booleans or bare boxes: planning the joints and the detail, the geometry rules, and the normal bake. |
| `_shared/models/blender-detail-scan.md` | A planning method: scanning a reference zone by zone for the detail list, and where each texture-side detail lands in the DayZ texture set. |
| `_shared/models/blender-visual-review.md` | How to check a model in Blender by looking at it: render it from fixed angles, read the images against a checklist, fix one thing, render the same angles again, and stop when the stop rule says so. |
| `_shared/models/tools-vlm-judge.md` | Tool behaviour: a local vision model as a pre-filter on renders, which checklist questions may be delegated and how each was calibrated. |
| `_shared/models/tools-vlm-checklist-format.md` | Tool behaviour: the JSON format of a render checklist and how `--view` routes each question to one image. |
| `_shared/models/ai-generation.md` | Part checked: taking an AI-generated mesh to a DayZ prop (generators, retopology, bake, handoff, writing the MLOD), and reskinning a vanilla infected. |
| `_shared/models/model-build-stages.md` | How to take a production model, or a rebuild that has to match a vanilla object, from the first question to the packed file in seven stages, each ending in a written pass or fail. |

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
| `_shared/wearables/references/body-rigging.md` | Giving a custom humanoid mesh (a survivor body, a human NPC or an infected) weights on the vanilla bone names in the canonical bind pose, in Blender, and why a body explodes or does not move. |
| `_shared/wearables/references/body-lods.md` | Part checked: the LODs a new humanoid body needs, a see-through hole in a body, and why size cannot come from a scale call. |
| `_shared/wearables/references/canonical-bind.md` | What the engine binds a character mesh against, the three ways a mesh misses that bind, the infected bind, and the offline checks that hold. |
| `_shared/wearables/references/body-uv-bake.md` | Measured on one project: unwrapping a rigged low-poly body and baking normal and ambient occlusion maps into the new UV. |
| `_shared/wearables/references/ragdoll.md` | The data-driven ragdoll 1.30 binds on survivors: where it is bound, the `human.ragdoll` format, the vanilla bone masses, what a custom body must keep. |
| `_shared/wearables/references/fitting-worn-models.md` | Fixing plates or panels that bind but sit off the body: by hand in the alignment viewer, or through an artist with FBX. |
| `_shared/wearables/references/autofit-on-official-rig.md` | Tool behaviour, not yet checked on `P:\`: fitting a garment onto the official rig in headless Blender with weights from the rig's body mesh; what worked and what was refuted. |
| `_shared/wearables/references/body-export.md` | Writing a body rigged in Blender (`body-rigging.md`) to an MLOD `.p3d` with py3d, so its vertex groups become weighted named selections: the axis map, winding and normals, the py3d rules, the offline checks and the chiral check in game. |

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
| `_shared/weapons/model-import.md` | Importing a weapon mesh from Blender the right way round, and which build to test it with. Measured on one project where marked. |
| `_shared/weapons/troubleshooting.md` | Checks before the first in-game test of a custom firearm, and a symptom table; each line points to the file that holds the fact. |
| `_shared/weapons/dayz-1-30-migration.md` | What breaks in a 1.29 weapon mod, the checklist for moving it to 1.30, and where the four weapons added in 1.30 live. |

### Persistence pack (`_shared/persistence`)

Front index: `_shared/persistence/README.md`. Written for `dayz-persistence-specialist`.

| Folder or file | Purpose |
|---|---|
| `_shared/persistence` | Saving data across server restarts. |
| `_shared/persistence/save-load-contract.md` | The `OnStoreSave` and `OnStoreLoad` chain, what vanilla already saves, load hook order, persistent IDs. |
| `_shared/persistence/versioning-and-migration.md` | Your own save version, adding and removing fields, modded vanilla class risks, data kept in files. |
| `_shared/persistence/base-building.md` | Part ID bit masks, the `Construction` config, territory flag and lock saves. |
| `_shared/persistence/data-audit.md` | The pre release data loss audit and its report format for the server lead. |
| `_shared/persistence/where-to-save.md` | Choosing between the entity save stream, Community Framework ModStorage and a file of the mod's own before writing any code. |
| `_shared/persistence/sidecar-files.md` | Keeping mod data in its own file under the server profile: the file functions, the load rules, a save sequence that can be recovered at every step. |
| `_shared/persistence/migration-matrix.md` | The seven kinds of input a reader must classify when a saved format changes, proving the tests can fail, and how vanilla 1.30 handled its own new fields. |
| `_shared/persistence/cf-modstorage.md` | Community Framework behaviour, not vanilla: how CF stores one framed block per mod inside an entity's save, and what it leaves to the mod. |
| `_shared/persistence/lifetime-and-storage.md` | Part checked: why placed objects vanish after a restart even when their save code is right, and what a copied storage folder needs. The measurements are in-game probes. |
| `_shared/persistence/central-economy-files.md` | The structure and stock values of the Central Economy files a 1.30 server reads, for writing or checking a `types.xml` or `cfgspawnabletypes.xml` entry. |
| `_shared/persistence/load-and-restore.md` | Part checked: what happens when `OnStoreLoad` returns false, the order in which structures and stored entities come back, mod registries and live cargo. |
| `_shared/persistence/dayz-1-30-persistence.md` | What 1.30 changed in the vanilla save streams, with the vanilla code copied in and compared with `P:\`. |
| `_shared/persistence/base-building-structures.md` | The classes that make up a buildable object, the kit to base flow, what breaks silently, and quick triage of build, dismantle and save symptoms. |
| `_shared/persistence/base-building-config.md` | Every config field a buildable object needs, with the vanilla code that reads it. |
| `_shared/persistence/base-building-lifecycle.md` | The call chain from crafting a kit to a base surviving a server restart, hop by hop. |
| `_shared/persistence/base-building-placement.md` | What decides whether a kit can be placed and whether its recipe can be built: slot stack sizes, the hologram tint, the carry pose, custom wall placement. |
| `_shared/persistence/base-building-fence-gate.md` | The vanilla fence as a template for a stateful part: gate state, barbed wire damage, locks and the saved gate fields. |
| `_shared/persistence/base-building-save-checklist.md` | The hand-off checklist for a base building save change: the synced bit masks and the 93 part cap. |
| `_shared/persistence/base-building-1-30.md` | What DayZ 1.30 changed in the construction system for player built objects: the class tree, the per type config cache, the `*ServerEx` methods, the build collision check, masonry and the fence code lock, with what each change breaks in a 1.29 mod. |
| `_shared/persistence/deep-audit.md` | The full audit for a mod where a bug loses player progression: mechanical checks, eight audit angles, and every finding verified against the real file. |
| `_shared/persistence/deep-audit-angles.md` | What each of the eight review angles of the deep audit looks for, how a reviewer reports, how the claims are checked, and what the cross-actor pass traces. |
| `_shared/persistence/deep-audit-path-naming.md` | Mechanical check 1: a path helper and a recovery or cleanup site that disagree on the file name on disk. |
| `_shared/persistence/deep-audit-sidecar-cleanup.md` | Mechanical check 2: a writer creates a file or marker and the matching cleanup site fails to remove it. |
| `_shared/persistence/deep-audit-entry-points.md` | Mechanical check 3: the main path keeps an invariant but another entry point skips it. |
| `_shared/persistence/deep-audit-flag-lifecycle.md` | Mechanical check 4: two state stores that must move together, where one moves without the other. |
| `_shared/persistence/deep-audit-state-machine.md` | Illegal transitions, state counted twice, and "should never happen" branches that can happen. |
| `_shared/persistence/deep-audit-hooks-and-super.md` | Code that overrides an engine event or relies on a `modded class` hook: what the event delivers and whether every class calls `super`. |
| `_shared/persistence/deep-audit-incremental-rebuild.md` | Three defect classes that appear when a rebuild that ran in one call is spread over several ticks. |
| `_shared/persistence/deep-audit-evidence-controls.md` | Telling real evidence from evidence that only looks real: the deployed build against the source, controls that can fail, complete inventories. |
| `_shared/persistence/deep-audit-fix-traps.md` | What goes wrong when fixing and auditing again: a missed sibling call site, two correct fixes that break each other, a fix never audited. |
| `_shared/persistence/base-building-rebuildable.md` | How a map building (`BuildingBase`) gets its own construction component on 1.30, how that component saves its parts, which config keys it reads and what the game ships for it. |
| `_shared/persistence/base-building-decay-and-falling.md` | How built parts decay on 1.30, and what happens to items, players, vehicles and buildable objects resting on a part that is dismantled or destroyed, with the server switches. |

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
| `_shared/vehicles/motorbikes.md` | Which classes a motorbike starts from, which addon it requires, how it differs from a car, and what its config class and script class must contain. |
| `_shared/vehicles/motorbike-invariants.md` | Part checked: the ten rules that break a motorbike when ignored, tuning lessons measured on a real import, and what vanilla left unfinished in 1.30. |
| `_shared/vehicles/vehicle-types-boat-truck.md` | 1.30 citations checked on `P:`: what changes for boats, trucks, mod-made quads and the motorbike family against a four-wheeled `CarScript` car. |
| `_shared/vehicles/dayz-1-30-vehicles.md` | Part checked: what DayZ 1.30 changed for cars, trucks and boats beyond the class tree, which change breaks a 1.29 mod outright, and the steps to move a car from 1.29 to 1.30. |
| `_shared/vehicles/aviation-carscript-base.md` | Part checked: the vanilla contracts an aircraft leans on when it inherits `CarScript`: entity events, scripted velocity, angular velocity, body sleep, what stops the engine. |
| `_shared/vehicles/aviation-inputs-and-actions.md` | Part checked: custom flight inputs and in-seat pilot actions: why an input reads zero in the seat, reading it on the server, deadzones, sight and camera interfaces. |
| `_shared/vehicles/aviation-networking.md` | Part checked: how a scripted aircraft stays smooth for its pilot: the Pawn classes and events, the move strategy, owner prediction, ownership changes, the pilot's camera. |
| `_shared/vehicles/aviation-dayz-1-30.md` | Checked on `P:\`: what 1.30 changed underneath an aircraft that inherits `CarScript`: lights, horn, battery and the event mask contract. |
| `_shared/vehicles/aviation-model-axes.md` | Why an offset measured from a `.p3d` with py3d can land on the wrong end of the aircraft, and the runtime probe that settles it. |
| `_shared/vehicles/aviation-thermal-imaging.md` | Why a thermal view cannot be built with post-processing, and the per entity texture and material swap that works. |
| `_shared/vehicles/motorbike-config-contract.md` | What the vanilla `MotorbikeScript` config class declares, and which key or script value of `Motorbike_01` and `Motorbike_02` does what and who reads it. |
| `_shared/vehicles/motorbike-script-api.md` | The native interface of the motorbike class, the simulation callbacks, the script lifecycle, net sync variables, and what a motorbike lacks against a car. |
| `_shared/vehicles/motorbike-actions-hud-lights-sounds.md` | The motorbike user actions, the HUD structure, the lights, horn and effect components, and the sound classes. |
| `_shared/vehicles/motorbike-rider-animation.md` | How the rider is animated: the human vehicle command, the vehicle graph, the vanilla clips, the camera, and how far a mod can change the pose. |
| `_shared/vehicles/motorbike-forward-contract.md` | The full specification for a new 1.30 motorbike, each element marked exact, design or unverified. |
| `_shared/vehicles/motorbike-vanilla-p3d-anatomy.md` | What the binarized models of the two vanilla motorbikes hold, at a glance, and how to read the full tables in `motorbike-01-model-anatomy.md` and `motorbike-02-model-anatomy.md`. |
| `_shared/vehicles/motorbike-vanilla-sources.md` | Every vanilla file the motorbike files cite, with its path on `P:\`, its line count and the symbols read in it. |

The aircraft files below describe third-party mods, not vanilla, and are not yet checked on `P:\` except where a `P:\` path is cited.

| File | Purpose |
|---|---|
| `_shared/vehicles/aviation-fixed-wing.md` | How LM_Planes builds seven planes and one amphibious car on one `CarScript` base: the config skeleton, `requiredAddons`, the `class defs` wrapper for sub-mods, the data driven base class, its Pawn replication, ground and air modes, parking brakes, sub-mod layout and shared parts. |
| `_shared/vehicles/aviation-aerodynamics.md` | How a scripted plane works out lift, drag, thrust and stall, which atmosphere model it uses, how it levels itself, and how it keeps NaN forces out of the physics body. |
| `_shared/vehicles/aviation-animation-and-modelcfg.md` | Animation sources for control surfaces, dials and dampers, the `model.cfg` classes behind them, and aircraft damage zones. |
| `_shared/vehicles/aviation-input-bindings.md` | How that mod registers its flight inputs, its keyboard and controller scheme, and the stringtable and config tie-in. |
| `_shared/vehicles/aviation-sounds.md` | The sound shader and sound set layout for aircraft engines: the RPM band crossfade, volume modulation, ranges. |
| `_shared/vehicles/aviation-effects-and-lights.md` | Navigation lights, headlights and seaplane water spray on an aircraft. |
| `_shared/vehicles/aviation-weapons.md` | How a plane fires: a tracer projectile with no engine physics, instant raycast damage with a visible tracer, the pilot only check, the client to server request, and impact effects timed to the tracer. |
| `_shared/vehicles/aviation-flight-testing.md` | Working rules for testing a scripted flight model in game and judging the result from logs. |
| `_shared/vehicles/helicopter-model-comparison.md` | Five helicopter flight models side by side: what they share, monolithic loop against modular aerofoils, kinematic against force based, which to build from. |
| `_shared/vehicles/helicopter-expansion.md` | How the DayZ Expansion vehicle framework flies helicopters and planes with physics modules and a config driven aerofoil module. |
| `_shared/vehicles/helicopter-mh6.md` | A force based helicopter mod: Pawn owner state and move replication, the simulate loop, real rigid body forces. |
| `_shared/vehicles/helicopter-rffs.md` | A kinematic helicopter framework: class layout and a flight loop on set velocity and set orientation. |
| `_shared/vehicles/helicopter-sib.md` | A kinematic helicopter model: class layout, its simple flight loop, the JSON coefficient store. |
| `_shared/vehicles/helicopter-mod-sources.md` | Which Workshop helicopter mods can be read as plain script, which PBO holds the flight code, and which are a dead end. |

The symptom files below start from what the tester sees and walk to the cause.

| File | Purpose |
|---|---|
| `_shared/vehicles/get-in-guards.md` | Which checks stand between a player and the "get in" prompt, in the order the action runs them, and how to find the one that blocks before touching the model. |
| `_shared/vehicles/vehicle-door-mechanisms.md` | Which of the three unrelated door mechanisms a door needs, how to choose before modelling or scripting, and the trap on each vehicle route when a door shows no open or close action. |
| `_shared/vehicles/attachment-proxies.md` | Why a wheel, door, part or rack item can be attached and simulate yet not render: the proxy class name rule, the proxy frame the item is drawn in, which proxy base class a slot needs, and why one rack cannot hold rifles and tools in line. |
| `_shared/vehicles/wheel-simulation-wiring.md` | What it looks like when a car's wheels are attached but do not simulate, which model property is only parity, and which wiring actually decides it. |
| `_shared/vehicles/binarize-dropped-textures.md` | Why a vehicle that looks right with file patching renders white or untextured on a dedicated server, which assets the binarize step does not pack, and the two ways to ship them. |

The files below are field notes from vehicle projects. Each opens with a `Status:` line saying what it was measured on. In a "part checked" file, a citation written with its full `P:\` path was opened on `P:\`; the measurements were not repeated.

| Folder or file | Purpose |
|---|---|
| `_shared/vehicles/new-car-day-one.md` | Part checked: what to measure offline before a new or ported vehicle first goes in game, what each of the three files owns, and the gaps no config review reveals. |
| `_shared/vehicles/vehicle-config-and-modelcfg.md` | Part checked: the `config.cpp` class of a drivable car, block by block: what each of the three files owns, the class tree, `SimulationModule`, crew, lights, attachments, wheel and door items, sounds, animation sources, and how config, `model.cfg` and the model wire together. |
| `_shared/vehicles/vehicle-structural-parity.md` | Part checked: how to compare a new or imported car with a working vanilla car before the first in-game test, and what each LOD, selection, memory point and proxy of a drivable car holds. |
| `_shared/vehicles/invariants-engine-fluids-and-handling.md` | Part checked: why an engine will not start or stay on, what a test kit must fill and attach, and measured rules for rolling, steering, mass, grip and drivetrain ratios. |
| `_shared/vehicles/invariants-get-in-and-seats.md` | Part checked: why a get-in, seat or door action does not appear on a new or imported car, and the model, config and script contract that makes it appear. |
| `_shared/vehicles/invariants-import-mesh-and-winding.md` | Part checked: checks for a body that comes from an OBJ, a glTF or a game rip: mesh and UV health, mirror against rotation, winding, nose direction, cabin alignment. |
| `_shared/vehicles/invariants-lods-and-vertex-budget.md` | Not yet checked on `P:\`: how many visual LODs an imported vehicle needs, how far each decimation method goes, and telling offline that a model is over the vertex ceiling. |
| `_shared/vehicles/invariants-wheels-and-hubs.md` | Part checked: where wheel hubs live in the model, how wheel proxies line up with them, hub height against tyre radius, wheel facing, and the axle classes the engine counts. |
| `_shared/vehicles/proxies-and-detachable-parts.md` | Part checked: how proxies sit on a car that works, which four config and model layers a detachable door, hood or trunk needs, what changes when a baked part becomes an attachment, and how to check binarized output without trusting its bytes. |
| `_shared/vehicles/get-in-actions-and-proxy-pose.md` | Part checked: the four-link condition chain behind the get-in prompt, the two registrations a cursor-targeted vehicle action needs, and where an occupant's pose comes from. |
| `_shared/vehicles/gunner-shoot-from-vehicle.md` | Part checked: how a rider can fire a handheld weapon from a moving car or boat, as one third-party mod does it: linked at an anchor and frozen by a scripted human command. |
| `_shared/vehicles/doors-and-panel-edges.md` | Not yet checked on `P:\`: why an imported door shows a missing edge when it opens, measuring that edge against a vanilla door, and what a hood or trunk needs that a door rig gets wrong. |
| `_shared/vehicles/rip-panel-open-rim.md` | Not yet checked on `P:\`: why a door, hood or tailgate from a game rip shows a see-through edge when it opens, what does not close it, and the gate that proves a real cap. |
| `_shared/vehicles/lights.md` | Part checked: why a car's lights do not switch: material paths, hidden selection ownership and order, bulbs, driver exit, testing the setter against a vanilla car. |
| `_shared/vehicles/emissive-leds-and-dynamic-lights.md` | Part checked: how to make an LED change colour and glow from script (a hidden selection, one `.rvmat` per state, a swap with `SetObjectMaterial`) and how to make it also light the scene with a `PointLightBase` on a memory point. |
| `_shared/vehicles/gauge-needles.md` | Part checked: how to wire a speedometer, tachometer and fuel needle on a vehicle: the selection, axis and bone each needle needs, the `model.cfg` classes, which way vanilla needles turn, what `rpm` is measured against, and the order to build a new cluster in. |
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
| `_shared/vehicles/scripted-vehicle-tests.md` | Part checked: what the engine does when a test seats, drives, unseats or films a vehicle from script, and which actions the server still checks. |
| `_shared/vehicles/method-and-gate-calibration.md` | Part checked: process rules: the iteration budget, calibrating a gate before trusting it, what a PASS covers. |
| `_shared/vehicles/process-gates.md` | Part checked: writing a model-import gate that can be trusted: a negative fixture per rule, three exit states, controls independent of the candidate. |
| `_shared/vehicles/visual-gates-and-winding.md` | Part checked: which offline checks catch winding and shading faults on an imported car and which ones only seem to, the one orientation rule for a ripped car, why a clean `validate()` or a Blender culling render proves nothing about what the game draws, and how to pick the winding of a face a script adds or moves. |
| `_shared/vehicles/visual-metrics-and-viewer.md` | Part checked: what can be asserted from a screenshot: perspective artifacts, where a HUD marker ray is anchored, validating a visual metric on a control. |
| `_shared/vehicles/external-obj-import.md` | Part checked: how to turn an artist's OBJ export (Maya, ZBrush, Blender) into DayZ coordinates: which existing item to copy, how to split faces by material, the UV flip, the transform, and how to tell a winding problem from a normals problem. |
| `_shared/vehicles/decimation-libraries.md` | Not yet checked on `P:\`: which Python library to reduce a high-poly import with, a `pymeshlab` recipe that keeps UV seams, and face targets for a LOD ladder. |
| `_shared/vehicles/gta-rip-intake.md` | Part checked: reading a GTA V vehicle mod archive offline, what its skeleton names map to in DayZ, and checking bone names against the real mesh pieces. |
| `_shared/vehicles/rip-import.md` | Part checked: how to turn a car ripped from a racing game into a drivable `CarScript` vehicle: what a per-car rip folder holds, which parts to include, how to read dimensions and the transform from the locators, and where the car's physics data comes from. |
| `_shared/vehicles/rip-geometry-and-winding.md` | Part checked: geometry work on a ripped mesh: automatic retopology, the winding rules for proxy triangles and visual faces, the scope of `autocenter=0`, fixing winding per component. |
| `_shared/vehicles/ripped-car-proxy-split.md` | Part checked: a new ripped car split into proxies with moving parts: the transform, what to settle before any geometry, what the rips ship for doors, the user's visual check before a build, and the order of work. |
| `_shared/vehicles/rip-classify-viewer.md` | Reviewing and changing the classification of a ripped car's parts without opening Blender: the viewer's Three.js files, the steps per car, the GLB data contract. Tool behaviour, no game fact. |
| `_shared/vehicles/rip-profile-schema.md` | Field by field, what a car profile of the import project holds and which script reads each field (legacy and in flight). No game fact. |
| `_shared/vehicles/attachment-proxy-hiding.md` | How to hide a proxy baked into a model while its slot is empty, which two config halves `HideSelection` needs, and how to make a seat unusable while something is attached. |
| `_shared/vehicles/aviation-aircraft-presets.md` | Which aircraft LM_Planes builds on one base class, and the parameter values it uses for a large plane, a small plane, an aerobatic plane and a flying car, as starting points for a new aircraft. |
| `_shared/vehicles/aviation-plane-model.md` | Which memory points, skeleton bones and selections a scripted plane's `.p3d` and `model.cfg` need, and how the dashboard switches its lit material. |
| `_shared/vehicles/aviation-script-performance.md` | How a scripted aircraft keeps its per-tick cost down: skip animation calls that change nothing, run each update at the rate it needs, cache input lookups, and move cockpit detail into proxy models. |
| `_shared/vehicles/aviation-seaplanes.md` | How a scripted plane floats with a `Buoyancy` class, which script layer adds water takeoff and steering on top, which numbers suit a large and a small airframe, and how the spray effects are attached and cleaned up. |
| `_shared/vehicles/aviation-weapon-fire-code.md` | How the server side of an aircraft gun works: take a round from cargo, pick the muzzle, launch the tracer with the aircraft's speed, cast the damage ray, find a damage zone, and send the effects to every client. |
| `_shared/vehicles/crew-get-in-geometry.md` | What a car's model and script must provide for the get-in action to appear on every seat and for the seated player to sit right: seat components, the crew proxy triangle, the script class, and how to probe seats without aiming by hand. |
| `_shared/vehicles/dayz-1-30-get-in-and-boats.md` | What the 1.30 get-in condition checks and which side a rider can board from, what boats gained, how `speedGeoms` hides parts at speed, which wrecks became wells, and where the motorbike camera lives. |
| `_shared/vehicles/dayz-1-30-lights-and-battery.md` | How a 1.30 car registers its lights, what the light toggle and the driver seat do to the light state, which profile fields are dead, how a car declares its battery, and where the horn, effect scale and ganged rear bulbs moved. |
| `_shared/vehicles/dayz-1-30-wheels.md` | How 1.30 swaps a ruined wheel for its `_Ruined` twin, what a mod wheel needs so the swap works without errors, and the four tyre fields every 1.30 wheel declares. |
| `_shared/vehicles/emissive-led-materials.md` | How to write the `.rvmat` for each LED state so it glows: which shader and stages to use, how strong `emmisive[]` must be, and what to check when an LED renders black. |
| `_shared/vehicles/gauge-dial-art.md` | How to measure the printed arc of a dial, why each dial gets its own padded texture, what limits legibility on screen, and how stale textures slip into a build. |
| `_shared/vehicles/gauge-dial-frame.md` | How to fix the screen frame of a dial so its art is neither mirrored nor rotated, how to tell a mirror from a rotation by measurement, and how `angle0` and `angle1` follow from that frame. |
| `_shared/vehicles/gauge-fuel-panel.md` | How to add a fuel gauge panel to a model: padding the art, choosing a UV window that matches the face, where the pivot falls, sizing the needle, and which angles carry over from one model to another. |
| `_shared/vehicles/gauge-needle-part.md` | How to build a gauge needle mesh that can be reused across vehicles, how to cut a real needle out of an imported cluster object, how to measure its rest angle and depth, and the two signs every new cluster face must copy from its neighbours. |
| `_shared/vehicles/motorbike-01-model-anatomy.md` | What the binarized model of the vanilla `Motorbike_01` holds: model info, LODs, skeleton, every animation with its source, memory points, proxies and selections. |
| `_shared/vehicles/motorbike-02-model-anatomy.md` | What the binarized model of the vanilla `Motorbike_02` holds: model info, LODs, skeleton, every animation with its source, memory points, proxies and selections. |
| `_shared/vehicles/motorbike-damage-and-wheel-config.md` | How the vanilla `Motorbike_01_ColorBase` lays out its `DamageSystem`, which materials each zone swaps as it takes damage, and what its wheel classes and ruined wheels set. |
| `_shared/vehicles/motorbike-simulation-config.md` | What the vanilla `SimulationModule` and `AnimationSources` of `Motorbike_01_ColorBase` hold, as a starting point for a new bike's handling. |
| `_shared/vehicles/obj-import-assembly.md` | How to finish an OBJ import once it is parsed and in DayZ coordinates: decimate each material group, build smooth normals, assemble the `.p3d`, encode the PAA, wire config and scripts into the mod, and check the result. |
| `_shared/vehicles/rip-glass-and-gap-closure.md` | How to close the see-through gap between a ripped car's glass and its body without greying the windows, how to transfer materials when authored LODs carry foreign geometry, where a rally lift belongs, and how to apply a structural fix without losing a working get-in. |
| `_shared/vehicles/rip-structural-lods.md` | How to build the body and structural LODs of a ripped car, why a rip body crashes the render until it is thinned, which faults block the first spawn and get-in, and the offline checks worth building before testing in game. |
| `_shared/vehicles/rip-textures-and-materials.md` | How to texture a car ripped from a racing game: which UV channel the swatches use, where the factory paint colour is stored, how to give every mesh the right material type, and how glass, interior and two-sided surfaces behave in DayZ. |
| `_shared/vehicles/rip-wheels-and-doors.md` | How to deploy a rebuilt visual shell without losing the structural LODs, make wheels draw and use the car's original rim, change the track width, take doors from the rip's pre-cut parts, and give first person the car's own interior. |
| `_shared/vehicles/ruined-wheels.md` | How a mod wheel swaps to its ruined model, which script and config it needs on DayZ 1.29 and 1.30, why no repair rule is needed, and how to size and seal a flat tyre model. |
| `_shared/vehicles/seated-actions-and-get-in-faults.md` | How to offer an action to a player sitting in a vehicle, how to run continuous actions and input excludes from the seat, and three faults that look like a broken model or get-in and are not: a misread host, a shared script core and a phantom vehicle command. |
| `_shared/vehicles/vehicle-damage-and-glass.md` | How a car's `DamageSystem` block is written in config, how breakable glass uses the same zones, what `RefTexsMats[]` and `"hidden"` do in a damage level, and a windscreen case that is still open. |
| `_shared/vehicles/vehicle-geometry-and-mass.md` | How to build a car's Geometry LOD, where its mass comes from, what makes a car launch or sink on spawn, how to size wheel wells and suspension, and what the separate wheel `.p3d` needs for its collider. |
| `_shared/vehicles/vehicle-modelcfg-animations.md` | How a car's `model.cfg` skeleton and animation classes are written, what the engine feeds the dashboard needles, when a vanilla rig can be reused, and how the crew proxy frame and the driver's hands are decided. |
| `_shared/vehicles/vehicle-parts-and-start.md` | How a car's attachments, cargo and fuel are declared, how wheels and doors are wired as items with their slots and proxies, and why an engine will not start. |
| `_shared/vehicles/vehicle-proxies.md` | How proxy paths, frames and bone selections must be written for a car's body chunks, wheels, crew and doors, how components are tagged, which way a DayZ car faces, and how to bring in a high-detail body as proxies. |
| `_shared/vehicles/view-pilot-assembly.md` | What the View Pilot LOD (resolution 1100) of a car built as a shell plus proxies must carry, how to tell its three possible states apart, how to create it when it is missing, and how to count what the seated view holds before an in-game test. |
| `_shared/vehicles/view-pilot-closures.md` | How to close gaps in a fairing or cockpit through which the seated rider sees the ground: black membranes that only the View Pilot LOD (resolution 1100) carries, placed behind everything the steering sweeps, and tested with the bars turned. |

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
| `_shared/ai/design-ideas.md` | Design ideas, not vanilla: parts of a scripted AI brain (a human guard, or any creature whose decisions you script) that keep many units cheap and stable; every number is a starting value to measure. |

### Texture and material pack (`_shared/textures`)

Front index: `_shared/textures/README.md`, which also has a symptom to cause table. Written for `dayz-asset-specialist`.

| File | Purpose |
|---|---|
| `_shared/textures/suffixes-and-sizes.md` | Texture suffixes and what ImageToPAA does with each, vanilla sizes, procedural placeholders. |
| `_shared/textures/rvmat-stages.md` | `.rvmat` keys, Super and Skin stages, damage and destruct materials, the thermal stage. |
| `_shared/textures/surface-recipes.md` | The vanilla material to copy and the values to change for cloth, metal, glass and skin. |
| `_shared/textures/checking-the-look.md` | What the user checks in Object Builder and in game after the files are written. |
| `_shared/textures/runtime-material-swaps.md` | Part checked: what changes an item's material or texture at run time: health levels, the script calls, and what was measured when a script repaints worn clothing. Blocks marked "measured in game" come from one mod project. |
| `_shared/textures/rvmat-cookbook.md` | Which material route fits a goal, a seven stage Super starting point, and the patterns for damage, emissive, glass, alpha decals, the environment map and penetration materials. |
| `_shared/textures/normal-maps.md` | Which way a DayZ normal map points, measuring a source map's convention before packing, what a `_nohq` holds, building one from albedo brightness. |
| `_shared/textures/smdi-and-levels.md` | What goes in each `_smdi` channel, getting there from metallic and roughness, setting `_smdi`, `_as` and `_co` levels against a vanilla asset, the DXT atlas border fault. |
| `_shared/textures/config-wiring.md` | How textures and materials are connected in `config.cpp`: hidden selections, health level materials, vehicle light material pairs. |
| `_shared/textures/vehicle-materials.md` | Which shader a vehicle or hard surface part needs, tiled detail on overlapping UVs, color variants, generated wear. |
| `_shared/textures/multi-materials.md` | When the Multi shader is worth it, which mask color picks which material, a skeleton to adapt, painting the mask, the checks before accepting it. |
| `_shared/textures/baked-atlas-checks.md` | The checks between a baked or borrowed texture and a working `.paa`, converting a `.paa` back, and what changes on Linux. |
| `_shared/textures/normal-bake.md` | Blender practice measured on one mod: the checks a high to low normal bake must pass before the first pass, and the conversion to `_nohq`. |
| `_shared/textures/matpbr-emat.md` | Not run in this repo: a second material route for metallic and roughness assets through an `.emat` file beside the Super route. |
| `_shared/textures/ui-textures.md` | Measured on one production mod: the tone curve and screen sized images for loading screen, menu and map textures, and why a hand written `.edds` does not render. |
| `_shared/textures/png-to-paa-encoding.md` | Part checked: a DXT1 `.paa` writer of about 150 lines that needs only Pillow and numpy: when to use it, the code, how to check its output, and what it cannot do. |

### UI pack (`_shared/ui`)

Written for `dayz-ui-specialist`. The folder has no front index of its own yet; pick the file from this table. Part checked throughout: a `P:\` path with a line was checked; in-game measurements and third-party mod facts were not re-run. The Figma pipeline rules are in `_shared/figma-to-dayz-rules.md`.

| Folder or file | Purpose |
|---|---|
| `_shared/ui` | `.layout` and `.styles` files, widget script, menus and the HUD, localization, iteration and verification, and the third-party UI frameworks. |
| `_shared/ui/layout-format.md` | How a `.layout` file is written: the brace grammar, the lexer details a tool must handle, the two ways a widget gives its name, and which widget classes exist and draw. |
| `_shared/ui/styles-format.md` | How the `style` attribute resolves, the format and state names of a `.styles` file, the vanilla styles, and the recipe for a mod's own styles. |
| `_shared/ui/widget-prototypes.md` | What every widget can do from script: the native methods of `class Widget`, what `SetRotation` and `SetTransform` really draw, the `WidgetFlags` enum, the global widget functions, `ControlID` and the widget type IDs. |
| `_shared/ui/script-recipes.md` | Copyable script for the parts every menu needs: binding widget fields by name, the event signatures, locking input and showing the cursor, background blur, alignment flags at runtime, a layout registry, and registering styles, imagesets and defines in `config.cpp`. |
| `_shared/ui/checklist-and-troubleshooting.md` | The 18 numbered build rules for `.layout` files and UI script, the checklist before a UI is done, and a symptom to fix table. |
| `_shared/ui/vanilla-menus-map.md` | Which vanilla class and layout build each menu and the HUD, registering a modded menu, the `UIScriptedMenu` contract, the focus model. |
| `_shared/ui/text-sizing-and-rendering.md` | Measured on a running client: `wrap`, font sizes, alpha, blending, render to texture. |
| `_shared/ui/theme-and-color.md` | Where UI colors come from, scoping a recolor request, the method override shape, and the rules of the color system. |
| `_shared/ui/localization.md` | The two stringtable formats, how layouts and script refer to a key, and the measured rule that decides whether a `stringtable.csv` is registered. |
| `_shared/ui/imagesets-draw-order-progress-bars.md` | Imageset file and set names, widget draw order, layout typos that stop the parser, image based and segmented progress bars. |
| `_shared/ui/stacking-and-clickability.md` | Sketches to check before use: how to keep widgets from overlapping when some of them hide, and how to find out why a widget ignores clicks. |
| `_shared/ui/hud-action-info-panels.md` | How the 1.30 interaction cursor shows the tools and materials an action needs, and how a mod adds its own panel. |
| `_shared/ui/ui-changes-1-30.md` | What 1.30 changed in the action prompt HUD, the inventory slot icon classes and the preview widgets, what breaks in a mod, and a migration checklist. |
| `_shared/ui/layout-variants.md` | Measured in game on 1.30: changing a vanilla layout through a layout variant, packing one, scoping it by inheritance. |
| `_shared/ui/cameras-seats-loading-screens.md` | Leaving a scripted camera, opening an interface from a vehicle seat, replacing the loading screen background. |
| `_shared/ui/hot-iteration.md` | How to change a `.layout` on disk and see it in the running client within seconds: which paths the game reads again, the reload loop, its four traps, and what the preview can't show. |
| `_shared/ui/plan-to-implementation.md` | Why a built UI differs from its plan, and an author, preview, build and verify loop with a parity gate. |
| `_shared/ui/verification.md` | What a passing automated check proves about a UI and what only a look at the screen can, which offline tool answers which question, how to test another resolution, and the traps in host helpers, logs and black frames. |
| `_shared/ui/color-test-harness.md` | A diagnostic mod that draws swatches of known colors to measure how UI colors are drawn. A harness, not a pattern to copy. |
| `_shared/ui/layout-corpus-counts.md` | Not yet checked on `P:\`: which widget classes and attributes real `.layout` files use and how often, what the less common attributes mean, and which layout checks hold up against shipped files and which only raise false alarms. |
| `_shared/ui/engine-widget-facts.md` | Not yet checked on `P:\`: which less obvious widget calls the engine already provides, what the global HUD brightness does to your colors, and how rich text markup is said to behave. |
| `_shared/ui/admin-ui-patterns.md` | Not yet checked on `P:\`: how admin style tools build their screens: floating windows you drag and resize, labels that follow objects in the world, a skeleton drawn on a canvas, box selection, a numpad menu, an orbiting camera preview and looking around while a menu stays open. |
| `_shared/ui/map-and-markers.md` | Third-party mod behaviour, not vanilla: how to drive a `MapWidget` from script, draw over it with a canvas, drag markers on it, follow the player with a minimap, and refresh markers only when something changed. |
| `_shared/ui/dabs-mvc-internals.md` | How Dabs Framework's view layer behaves when you read its source: what the `ScriptView` constructor does, how widgets and bindings are found, how a `Relay_Command` is dispatched, and how clicks travel from widget to handler. |
| `_shared/ui/expansion-mvc-patterns.md` | DayZ Expansion behaviour, not vanilla: its MVC classes, menu lifecycle, observable collections, subviews, dialogs, HUD panels. |
| `_shared/ui/expansion-market-menu.md` | How the DayZ Expansion Market menu works end to end, as a model for any UI that trades with the server: the MVC menu, its state machine, confirming before the RPC, the server's price recheck, reserved stock and the RPC handshake. |
| `_shared/ui/templates` | Four `.layout` files to copy as a starting point, the stringtable they need, and preview rectangles. Front index: its own `README.md`. |
| `_shared/ui/cards-and-tabs.md` | How to build an info card and a set of tabs, each as a layout plus a menu class. |
| `_shared/ui/chat-ui.md` | How a production mod replaces the vanilla chat: measuring text before placing it, a ring of reused line widgets, pausing fades while the chat is open, scrolling, and replacing the chat input without breaking it. |
| `_shared/ui/color-picker.md` | How to build a color editor where sliders and edit boxes stay in step, and how to reuse the finished picker of a group mod's core library without its three lifetime traps. |
| `_shared/ui/dabs-menus-and-prefabs.md` | How Dabs Framework's `ScriptViewMenu` puts a view on the vanilla menu stack and what it leaves for you to do, which prefab layouts ship with the framework, and how a mod detects and requires it. |
| `_shared/ui/dabs-observables-and-animation.md` | How Dabs Framework's `ObservableCollection` fills a list, which widgets bind both ways, and how `WidgetAnimator` and `LinearColor` work, with the traps in each. |
| `_shared/ui/dragging-hover-and-status.md` | How to make a window the player can drag by its header, give a button hover feedback, and show a status message that fades out. |
| `_shared/ui/expansion-settings-and-persistence.md` | Where DayZ Expansion keeps its settings and saved state, which fields a market item has, how it splits server data from client preferences, and how another mod detects Expansion at run time. |
| `_shared/ui/form-controls.md` | How to build a two way toggle and a pair of number fields that convert as the player types, each as a layout plus a menu class. |
| `_shared/ui/hud-overlays.md` | How a HUD element added by a mod decides when to show, how the player moves it, how its colors and positions are saved per server, and how it reacts to a resolution change. |
| `_shared/ui/layout-attributes.md` | What each attribute of a `.layout` widget does: units and anchors, visibility and input, color, text, and the attributes the counts show are common. |
| `_shared/ui/layout-geometry.md` | How to work out each widget's screen rectangle from the `.layout` alone, how anchors move a widget, and why the children of a spacer ignore their own position and size. |
| `_shared/ui/layout-html-preview.md` | What a static HTML preview of a `.layout` can and can't show, how to run the repo's viewer, and when a preview needs more than the core widget set. |
| `_shared/ui/layout-scriptclass.md` | How a layout widget gets its own script handler through `scriptclass`, how `ScriptParamsClass` passes values to it, and how a layout names a style. |
| `_shared/ui/layout-snippets.md` | Copyable `.layout` blocks for the common pieces of a menu, the checks to run on a layout before delivery, and the mistakes that cost the most. |
| `_shared/ui/menu-script-patterns.md` | Script patterns that polished mod menus share: imageset icons, tabs, lists built from a row layout, a search filter, a press twice to confirm button, a status message that fades, server set colors, a 3D item preview, a HUD overlay and click sounds. |
| `_shared/ui/preview-text-and-stringtables.md` | What a layout loaded from `$profile:` shows about text: when a `#STR_` key resolves, why reading the text back can't tell you, how glyph height follows the widget box and `text_proportion`, and when a PBO's own stringtable is not read. |
| `_shared/ui/preview-widgets.md` | Which widgets draw a 3D item or player inside the UI, their full script API, and the 1.30 changelog items that script cannot reach. |
| `_shared/ui/screen-scaling.md` | How to keep sizes and positions that script sets in screen pixels the same on every resolution, which values need the multiplier, and which the engine already scales for you. |
| `_shared/ui/ui-architecture.md` | How a large production mod keeps many screens manageable: a registry of layouts by name, widget fields bound by name, pages and tabs, an event bus, compile time feature switches, an RPC dispatcher, and formatting numbers for display. |
| `_shared/ui/automated-ui-checks.md` | What a script-driven UI check can and cannot do: finding a Dabs view, calling a click handler, loading a layout from `$profile:`, ESC with a focused edit box, and probes that answer through a file. |
| `_shared/ui/widget-classes.md` | The native methods of each widget class a mod calls: text widgets, images, buttons and inputs, scroll and spacer widgets, canvas and video, and which widgets can give their text back. |
| `_shared/ui/widget-name-collisions.md` | Why two layouts that share widget names make one of them unreachable by name, how to find the overlap before it costs a session, and why renaming one root is usually the whole fix. |
| `_shared/ui/world-markers-and-compass.md` | How to pin a widget to a point in the world, slide a compass strip with the camera heading, place a marker on the compass, and drop a ping where the crosshair points. |
| `_shared/ui/templates/panel-contract.md` | The contract of layouts loaded from `$profile:` and filled at run time: empty texts, no stringtable keys, widget names. |

### World pack (`_shared/world`)

Front index: `_shared/world/README.md`, which also has a symptom table and a setup order. Written for `dayz-map-specialist`. Checked on `P:\` (DayZ 1.30) except the lines marked "not on `P:\`"; nothing in it was tested in a running game.

| Folder or file | Purpose |
|---|---|
| `_shared/world` | What a world does beyond its terrain source: terrain holes, underground areas, the 1.30 environmental hazards, the Badlands world, the `.wrp` layout. |
| `_shared/world/terrain-holes.md` | How a 1.30 world removes terrain over height map cells, the script call that reads it, how a terrain author marks holes, what is unproven. |
| `_shared/world/terrain-holes-storage.md` | Which file holds a world's holes, why one cell is 6.25 m in Livonia, which engine strings load holes, and how the `.wrp` format changed in 1.30. |
| `_shared/world/underground-triggers.md` | The schema of `cfgundergroundtriggers.json`, how it is loaded and sent to clients, the trigger types, and an untested recipe for a mod bunker. |
| `_shared/world/underground-presence.md` | What "underground" means for a player, who decides it, how it reaches the server in 1.30, and which server check reads it. |
| `_shared/world/nasdara-badlands.md` | What the Badlands DLC adds as a world: the Nasdara data on `P:\`, the radio bunkers, the tunnel entrance, and the data files not on `P:\`. |
| `_shared/world/wrp-format-and-road-graph.md` | Part checked: the binary layout of a `.wrp` world file and what a tool must do to extract its road graph. Header facts checked on `P:\`; the rest was measured on third-party maps. |
| `_shared/world/sandstorm.md` | How script reaches the 1.30 sandstorm, how much a player feels under shelter, what a world needs for storms, what infected hear in one. |
| `_shared/world/heat-stroke.md` | How 1.30 turns sustained heat into heat stroke: the thermal bias value, its four phases, washing the head, shade, wind on a motorbike or boat. |
| `_shared/world/dust-agents-and-protection.md` | The two dust agents the sandstorm puts on a player, the gear that stops each one, and the symptoms each causes. |
| `_shared/world/surface-dust.md` | Where the 1.30 dust effects come from: ceilings, wind driven ground and cloud dust, kickup, dust behind vehicles scaled by weight. |
| `_shared/world/oil-pits.md` | How the 1.30 oil pit works, placing one, and writing an effect area of your own on the 1.30 tick. |
| `_shared/world/hazards-vanilla-file-map.md` | Which vanilla file holds which part of the sandstorm, heat stroke, dust and oil pit systems, what `P:\` cannot show about them, and the facts that are easiest to get wrong. |

### Skill packs (`references/`)

A skill's own pack. The front index of each folder is the table in that skill's `SKILL.md`. The marks follow each file's own opening lines: "not yet checked on `P:\`" for third-party facts, tool behaviour and results measured in mod projects, "part checked" where the cited `P:\` lines were checked and the rest was not. A row with no mark makes no claim either way: the file's opening lines say what was checked.

| Folder or file | Purpose |
|---|---|
| `dayz-particles/references` | Particle pack. Front index: `dayz-particles/SKILL.md`. |
| `dayz-particles/references/ptc-format-reference.md` | Every `.ptc` emitter property and curve. |
| `dayz-particles/references/emat-format-reference.md` | `.emat` particle material format and vanilla materials. |
| `dayz-particles/references/script-api-reference.md` | Playing, stopping and tuning particles from script. |
| `dayz-particles/references/integration-patterns.md` | Wiring particles into a device. |
| `dayz-particles/references/device-particle-choices.md` | Which vanilla particles suit a placed device and whether each needs stopping, tuning a particle at runtime, and bringing older device code up to the 1.30 form. |
| `dayz-particles/references/vanilla-particle-catalog.md` | Every vanilla particle in `ParticleList`. |
| `dayz-particles/references/dayz-1-30-particles.md` | What DayZ 1.30 changed in the particle script API: the client check, effects spawned by the server, surface particle IDs, vehicle effect overrides, and the migration checklist. |
| `dayz-particles/references/dayz-1-30-world-particles.md` | What DayZ 1.30 changed for effect areas, the sandstorm, oil pits and dust kickup, and the `ParticleList` constants it added. |
| `dayz-particles/references/effect-area-particles.md` | How many emitters a contaminated area in `cfgeffectarea.json` asks for, the hard cap, and why an area can hurt players where no gas is drawn. |
| `dayz-particles/references/playonobject-client-guard.md` | The usual mod pattern for attaching a looping particle to a placed object, compared with the vanilla wrecks it copies. |
| `dayz-particles/references/layered-effects.md` | How a large effect (an explosion, an impact, a fireball) is built from several emitters, which properties matter when you layer them, and how the `Mast` curves shape the whole effect over time. |
| `dayz-particles/references/effects-from-script.md` | How a mod registers its own `.ptc` files, plays a layered effect at a position or through the effect manager, and turns single emitters on and off as the game changes. |
| `dayz-particles/references/ptc-layout-and-cloudlets.md` | How a `.ptc` file is laid out, which emitter shapes vanilla uses, and how the old class based `CfgCloudlets` particles map onto `.ptc`. |
| `dayz-p3d-audit/references` | Model audit pack. Front index: `dayz-p3d-audit/SKILL.md`. |
| `dayz-p3d-audit/references/p3d-killers.md` | Model faults that break a `.p3d` with no engine error. |
| `dayz-p3d-audit/references/winding-methodology.md` | How to verify face winding. |
| `dayz-p3d-audit/references/config-rvmat-checks.md` | `config.cpp` and `.rvmat` checks for models. |
| `dayz-p3d-audit/references/killers-detail.md` | What was measured in game for the three collision killers of `p3d-killers.md` (a collision LOD wound outward, no `ComponentNN` selection, and parts left out of every component), how each is detected and fixed, and short notes on the other model killers. |
| `dayz-p3d-audit/references/manual-checks.md` | Not yet checked on `P:\`, except the vanilla LOD counts: faults the audit cannot see from one `.p3d`, how to measure each by hand, and rules for trusting a new gate. |
| `dayz-p3d-audit/references/vehicle-checks.md` | Not yet checked on `P:\`, except where a vanilla file is cited: what the audit checks on a wheeled vehicle body, and the vehicle faults (killers 11 to 13) to measure by hand. |
| `dayz-p3d-audit/references/winding-absolute-check.md` | Not yet checked on `P:\`: how to read the winding findings the audit prints from py3d, and why a clean py3d result is not proof of correct geometry. |
| `dayz-p3d-audit/references/winding-diagnostics.md` | The deep companion of `winding-methodology.md`: how each winding check reads on measured models, turning a result into a safe fix, and where offline checks stop. |
| `dayz-p3d-audit/references/collision-mesh-hygiene.md` | The mesh faults that make a convex collision piece fail without a word: needle triangles, zero-area faces, points left without a face, and hulls that are not quite convex. |
| `dayz-search-index/references` | Search index notes. Front index: `dayz-search-index/SKILL.md`. |
| `dayz-search-index/references/cost-and-free-tier.md` | Voyage embedding cost and the free tier check. |
| `dayz-search-index/references/chunking.md` | How each file type is chunked, and what indexes built by older versions are missing. |
| `dayz-import-mod/references` | Import notes. Front index: `dayz-import-mod/SKILL.md`. |
| `dayz-import-mod/references/github-and-cleanup.md` | Git link forms, clone naming and reuse, and removing an imported or cloned mod. |
| `dayz-import-mod/references/study-a-packed-mod.md` | Studying a mod shipped only as PBOs: classify them, extract them, and sweep the files for patterns with `path:line` evidence until no new pattern turns up. |
| `dayz-import-mod/references/extraction-ledger.md` | A working method: the four ledger files of a packed mod study, classifying a finding, one unit per turn, the closing report. |
| `dayz-import-mod/references/extraction-pitfalls.md` | Not yet checked on `P:\`: wrong conclusions from names and partial code, an extraction that did not decode, a model read with the wrong reader, and the Linux differences. |
| `dayz-launch-test/references` | In-game test pack. Front index: `dayz-launch-test/references/README.md` (what is known about closing the test loop); `launch.py` itself runs none of it. |
| `dayz-launch-test/references/windows-launch-cycle.md` | How the build, deploy and launch loop runs on one Windows machine: what a launch needs before it starts, why each requirement matters, and the default mods and admin tools a test server loads. How a build actually reaches the engine (include lists, file patching, absolute mod paths) is in `windows-build-and-mount.md`. |
| `dayz-launch-test/references/troubleshooting.md` | Which symptom of a local test session points at which cause, where each log lives, a vanilla error stack that is not the mod's fault, what to know about third-party modsets on the retail executables, and three traps from actions and Steam. Failures that stop a client from starting at all (a missing work drive, a stale Steam key, quoting, a client that writes no log) are in `client-startup-failures.md`. |
| `dayz-launch-test/references/build-and-storage-traps.md` | Measured ways a build, deploy and test cycle goes green without testing the change: a locked PBO never replaced, a check that only tests existence, signing the old PBO. |
| `dayz-launch-test/references/automated-cells.md` | How to set up a scripted test, a "cell", that boots the game, drives it without a person and reads its verdict from the logs: where the test code lives, what a test mission may do, which diag defines exist, and who closes the processes. |
| `dayz-launch-test/references/server-and-mission-config.md` | What the stock 1.30 dedicated server ships and which script reads it, launch switches and the diag menu, read from the DayZ Server install. |
| `dayz-launch-test/references/diag-flow-traps.md` | Not yet checked on `P:\`: which traps of the DayZDiag launch flow make a working mod look broken: where `Print` output goes, file patching that loads nothing, dependency mods in the wrong place, third-party scripts that only retail accepts, and the launch flags added in 1.30. |
| `dayz-launch-test/references/dayz-1-30.md` | Part checked: what DayZ 1.30 changes for starting and driving a test session: unpacked `-mod` folders, two new launch flags, headless clients, pending actions in single player and Script Console tabs. |
| `dayz-launch-test/references/linux.md` | Not yet checked on `P:\`: what changes in the test workflow when the host is Linux. |
| `dayz-launch-test/references/linux-native-server.md` | Measured on Linux, not yet checked on `P:\`: proving a mod loads on the native Linux dedicated server, with no client. |
| `dayz-launch-test/references/linux-headless-client.md` | Not yet checked on `P:\`: testing the client side on Linux with the retail client under Proton and a self-reporting test mod. |
| `dayz-launch-test/references/mod-loop.md` | The mod loop on 1.30 or later from scope to Workshop: which skill runs each step, the rules every mod task needs, where to look an API up, which pack to read, porting to 1.30. |
| `dayz-launch-test/references/test-loop.md` | The fast script-only test loop with DayZDiag and file patching, when to stop iterating, and the debugging tools the vanilla scripts offer. |
| `dayz-launch-test/references/debug-protocol.md` | Diagnosing a feature that "doesn't work" after it was implemented: six layers checked top down, rules for probes, component bisection, naming what a fault does, and the engine minimums that crash when missing. |
| `dayz-launch-test/references/error-catalog.md` | Mistakes made more than once while implementing DayZ mods (E01 to E35), each with the correct form. |
| `dayz-launch-test/references/measurement-discipline.md` | Part checked: reading numbers out of a test session without fooling yourself: aligning client and server series and three statistical traps. Method and measured results; only the script calls are checked on `P:`. |
| `dayz-launch-test/references/dayz-1-30-server-measured.md` | Measured on the native Linux server, not yet checked on `P:\`: what was observed by booting test mods on a 1.30 dedicated server that a source file cannot show. |
| `dayz-launch-test/references/client-startup-failures.md` | How to tell an environment failure from a mod failure when a DayZ client or build dies before it writes a useful log: the work drive missing after a reboot, a Steam registry key that points at a dead process, the wrong Steam account, quoting, and a diag that never writes logs. |
| `dayz-launch-test/references/diag-direct-launch.md` | What to check when you start DayZDiag yourself, outside `/dayz-launch-test`: reading defines from the log, a stale Steam session seen from inside a desktop app, the profiles path, the environment a crash dump carries, and owning the process. Each trap cost a run when a 1.30 Experimental install was probed by hand. |
| `dayz-launch-test/references/mount-probe-and-test-helpers.md` | How to check that a new mod mounts before any model or physics exists, and what to change when you copy a test launcher, spawn mission and verdict parser from one mod to another. |
| `dayz-launch-test/references/server-load-and-dummy-bots.md` | How to load a DayZ 1.30 server with moving dummy players and no clients, and how to measure that load without fooling yourself. |
| `dayz-launch-test/references/test-cell-evidence.md` | What makes a scripted test's verdict worth believing: gates that can actually fail, a teardown that keeps the logs, the checks a run must pass before it counts, and the two silent ways an in-game observation is spoiled (a missing mod on the `-mod=` line, and an unfocused client). |
| `dayz-launch-test/references/test-cell-vehicles.md` | How a scripted test seats a player in a vehicle without a person at the keyboard, how to tell why a test vehicle will not drive, and how to probe both peers when getting out goes wrong. |
| `dayz-launch-test/references/test-machine-sharing.md` | How several sessions share one Windows test machine without evicting each other, how to check who holds it before a launch or a kill, and how to start DayZDiag from an agent's shell so it survives the call. |
| `dayz-launch-test/references/vehicle-first-person-eye.md` | Where the first-person camera sits in a vehicle, why its position is not a constant of the character class, and how to log it in every run before you judge first-person frames or check first-person geometry offline. |
| `dayz-launch-test/references/window-capture-pitfalls.md` | How grabbing the client window from outside the game misleads: brightness and exposure that differ from diag, a hidden window, a grab that misses UI changes, and runs that never load their textures while their logs look normal. |
| `dayz-launch-test/references/windows-build-and-mount.md` | How a change reaches the engine on Windows: what AddonBuilder keeps or drops for script, asset and mixed mods, what `-filePatching` really serves, what a release build must prove, and why mod paths must be absolute. |
| `dayz-launch-test/references/actions-doors-and-inventory.md` | Which player actions, doors and inventory moves a scripted test can drive and read back, which need held input it cannot give, and the two ways round the rest: a key driven test addon and a mission driver. |
| `dayz-launch-test/references/in-game-check-validity.md` | What makes a check run in the game valid: which mod the run really loaded, what the PBO holds, why a command's own answer is not its effect, where a hang sits, how many samples a negative needs, and what the report must say. These rules apply to any in-game check, by hand or scripted. |
| `dayz-launch-test/references/raycasts-and-collision.md` | How to read an object's collision in the running game: the two vanilla raycasts and what their results mean, the set of rays and its controls, why picking an item up proves nothing, and the walk-into and stand-on tests for the player. |
| `dayz-launch-test/references/screenshots-and-cameras.md` | How a picture of the running game is taken, which frames say nothing about the mod, what a scripted camera does to the player, how to pose a raised weapon for a capture, and how to measure UI pixels in a capture. |
| `dayz-launch-test/references/spawning-and-placement.md` | How to create a test object so it lands where you meant, does not outlive the run, and is posed so its faces can be read: the spawn flags, the coordinate order, the placement flags, what an inventory create really makes, and how to kill, respawn and provoke the player. |
| `dayz-launch-test/references/telemetry-thresholds.md` | How to set a numeric threshold on telemetry read from the game (a drive check, a flight spike, any scripted check) so that real physics can pass it and an incomplete trace cannot. |
| `dayz-launch-test/references/vehicle-acceptance-checks.md` | Which checks take an imported car from "it spawns" to "it drives and turns the right way", where the car must stand for each, which failures end a pass, and which fix in the vehicles pack each failure points to. |
| `dayz-launch-test/references/vehicle-in-game-facts.md` | How a car behaves when a test spawns, seats, conditions, drives and deletes it: which peer owns the drive, how throttle reaches the car, how to give a spawned car wheels and fluids, how to read gears, and the traps of a driving bench. The checks to run, in order, with the fix for each failure, are in `vehicle-acceptance-checks.md`. |
| `dayz-preflight/references` | Environment check notes. Front index: `dayz-preflight/SKILL.md`. |
| `dayz-preflight/references/object-builder-viewer.md` | Object Builder's external viewer (Buldozer) path, a check to run by hand before a session that leans on Object Builder previews. |
| `dayz-preflight/references/dayz-1-30.md` | Not yet checked on `P:\`: the 1.30 launch options and Workbench editors worth knowing; no environment check changed. |
| `dayz-build-pbo/references` | Build and packing pack. Front index: `dayz-build-pbo/SKILL.md`. |
| `dayz-build-pbo/references/addonbuilder-rules.md` | How AddonBuilder behaves when it packs a mod: the command line, the `-temp` folder, which source tree a build really uses, where the ODOL lands, what it leaves out, and how to judge whether a build worked. |
| `dayz-build-pbo/references/pre-build-checks.md` | What to check in a mod folder before it is packed, which of those checks `/dayz-build-pbo` already runs, how to report the result, and what `$PBOPREFIX$` must hold. |
| `dayz-build-pbo/references/common-validation-failures.md` | Symptom, cause and fix for the failures the pre-build checks report most often. |
| `dayz-build-pbo/references/validation-scripts.md` | Which reference validators exist for a build pipeline outside this repo's own gates, which of them work, how their exit codes gate a build, and how to run them in CI. |
| `dayz-build-pbo/references/script-linter-and-compile-gate.md` | Using the offline script validator before packing, what its result proves, and the boot check that shows a deployed mod's script modules compile. |
| `dayz-build-pbo/references/post-build-gates.md` | How to prove a built PBO is the one you meant to build: its scripts, stringtable and models are inside, its entries match the source, its config points at files it really holds, and the gate you rely on can fail. |
| `dayz-build-pbo/references/workshop-publish.md` | Signing a built PBO with DsUtils, the Workshop item folder, and publishing with the Publisher or SteamCMD. |
| `dayz-build-pbo/references/dayz-1-30-pbo-build.md` | Not yet checked on `P:\`: what 1.30 changes for packing: duplicate members stop binarize, unpacked mods, the `fsShadowing` header property. |
| `dayz-build-pbo/references/dayzmake-linux.md` | Not yet checked on `P:\`: building, signing and publishing a mod on Linux with dayzmake, without DayZ Tools. |
| `dayz-build-pbo/references/file-checklists.md` | What to verify in each kind of file (`config.cpp`, script, networking, layout, action, `.rvmat`, persistence, refactor) before a mod file counts as written. |
| `dayz-build-pbo/references/asset-checks.md` | What to check in a mod's assets before packing: every texture and material path resolves, each `.p3d` has the LODs and memory points it needs, and a vehicle's wheel slots point at selections that make the wheels simulate. |
| `dayz-build-pbo/references/binarize-file-lookup.md` | How binarize finds the materials and textures a `.p3d` cites, what it writes when it cannot find one, how to stage a build so it finds them all, and how to check the ODOL afterwards. |
| `dayz-build-pbo/references/comparing-builds.md` | How to tell what really changed between two builds of a mod: which entries can be compared by bytes, how to compare models, and why a hash pinned to a PBO or a file in git breaks on its own. |
| `dayz-build-pbo/references/config-and-model-checks.md` | What to check in `config.cpp` and `model.cfg` before packing: syntax, `CfgPatches`, inheritance, the `hiddenSelections` arrays, duplicates, and whether `model.cfg` matches the models it describes. |
| `dayz-build-pbo/references/config-validator-script.md` | A reference `config_cpp_validator.py` to adapt for a CI pipeline: it checks brace balance, semicolons, `CfgPatches`, the `hiddenSelections` arrays per class, duplicate class names and parent classes with regex heuristics, and prints JSON. |
| `dayz-build-pbo/references/deployed-pbo-checks.md` | How to make sure the PBO the game loads is the one you built, from the sources you meant, and why a mod that mounts can still run nothing. |
| `dayz-build-pbo/references/manual-build-checklist.md` | What to tick by hand before and after a build when the automated checks are not available. |
| `dayz-build-pbo/references/stringtable-and-script-checks.md` | What to check in a mod's stringtable and scripts before packing: that every `#STR_` key resolves from a `stringtable.csv` DayZ can read, and that the scripts avoid what Enforce Script rejects. |
| `dayz-build-pbo/references/texture-path-checker-script.md` | A reference `texture_path_checker.py` to adapt for a CI pipeline: it finds every quoted `.paa` and `.rvmat` in `config.cpp` and in the addon's `.rvmat` files, resolves each one from the work drive root, and warns on stray `.png` and `.dds` files and on file names whose capitalisation differs from the file on disk. |
| `dayz-scope-mod/references` | Feature spec pack. Front index: `dayz-scope-mod/SKILL.md` ("Scoping a feature"). A method; the few game facts cite their file. |
| `dayz-scope-mod/references/scoping-a-feature.md` | How to say what done means for a non-trivial feature, and how each part will be checked, before any code is written. |
| `dayz-scope-mod/references/spec-outline.md` | What a feature spec holds, section by section: one copy per feature, saved as `spec.md` next to the plan in `output/<ModName>-plan/`. |
| `dayz-scope-mod/references/spec-review.md` | Which 18 checks a feature spec must pass before any code is written. |
| `dayz-scope-mod/references/questions-before-building.md` | Which questions to settle with the user before writing the `config.cpp`, `model.cfg` or scripts of a placeable or usable DayZ object, and how to ask them. |
| `dayz-scope-mod/references/implementation-protocol.md` | Writing the code once the spec exists: API checks, the mini-audit, the client and server data map, checkpoints, the bug ledger and the handoff. |
| `dayz-scope-mod/references/consistency-pass.md` | What the read-only check before the in-game test looks for across a feature's spec, plan, task list and code, how it rates each finding, and what its report holds. |
| `_shared/models/generated-model-pipeline.md` | Front page of the generated model workflow: the steps from Blender and py3d to a packed object, and which file covers each step. |
| `_shared/models/generated-model-rules.md` | The rules every generated model must meet, each under its own heading, and the LOD resolution values they use. |
| `_shared/models/lods-authoring.md` | How to reduce a visual LOD without losing a feature, the vertex and normal limits that make the game drop or crash on a LOD, the Blender object names that Object Builder's FBX import turns into LODs, and the ceiling on the number of LODs. |
| `_shared/models/memory-and-selections-authoring.md` | Which memory points and named selections a generated model needs, how to create them, and how proxy selections make an attachment show. |
| `_shared/models/py3d-generation.md` | How to build a model in Python with the py3d in `scripts/tools/py3d`: LODs, points, faces, selections and named properties, the LOD resolution values, the build order and the checks to run on the result. |
| `_shared/models/py3d-assembly-rules.md` | Rules for writing or editing a `.p3d` with py3d beyond the basic API: where mass may sit, cutting geometry without breaking selections, what the validator's findings mean. |
| `_shared/models/blender-headless.md` | How to drive Blender from a script with no window: starting it, clearing the scene, primitives, modifiers, UVs, materials and the ambient occlusion bake. |
| `_shared/models/blender-external-mesh.md` | How to take a mesh made somewhere else (an asset store, 3ds Max, Maya, ZBrush, a commissioned or legacy model) through Blender to OBJ files that py3d assembles into a `.p3d`: import, cleanup, UVs, LODs, export and textures. |
| `_shared/models/blender-import-preflight.md` | What to check before geometry work on an imported mesh, and what was measured while reducing and reshaping such meshes. |
| `_shared/animation/device-model-cfg.md` | How the `model.cfg` of a small device (switch, button, dial, lid, LED, drawer) is laid out: the skeleton, each animation type with its keys, how memory axes set direction and travel, and which LODs need the moving selection. |
| `_shared/animation/anim-graph-format-1-30.md` | How a 1.30 animation graph is written, using the vehicle sub-graph as a tour of the node types, how it differs from the 1.29 syntax, how to open the player graph in Workbench, and how to port a 1.29 `$AnimGraph 7` graph field by field. |
| `_shared/animation/anim-instances-and-templates.md` | How `.asi` instance files map animation names to clips, which player instances vanilla ships, the weapon state names and what a weapon states clip stores, the `ikpose_` keys, and the named groups of a 1.30 `.ast` template. |
| `_shared/animation/blender-bpy-cloth-and-particles.md` | How a script sets up cloth with pins, collisions and preset values, soft bodies, and particle debris in Blender, and reads deformed geometry per frame. |
| `_shared/animation/blender-bpy-fcurve-modifiers.md` | How a script adds noise, loops, polynomials, smoothing, limits, steps and envelopes to an F-curve in Blender, and which of them changed in 4.4 and 5.1. |
| `_shared/animation/blender-bpy-fcurves.md` | How Blender stores animation as F-curves on an Action, how slots changed that in 4.4, and how a script sets interpolation, easing and handles on keys. |
| `_shared/animation/blender-bpy-ik-and-baking.md` | How a script sets up IK in Blender, bakes constrained motion down to keys, and runs operators that need a context, plus the traps that make a correct looking script produce wrong animation. |
| `_shared/animation/blender-bpy-keyframes-and-actions.md` | How a script inserts keys, organises them in Actions and the NLA, and loops a cycle in Blender, and how Blender's key types map onto blocking, breakdowns and polish. |
| `_shared/animation/blender-bpy-materials-drivers.md` | How a script animates shader values, links one property to another with a driver, and keys shape keys in Blender, and where each one's Action really lives. |
| `_shared/animation/blender-bpy-sim-baking-export.md` | How a script bakes a Blender simulation's point cache, turns it into keys, reads the keys back on any version, and exports the result, and which formats keep cloth deformation. |
| `_shared/animation/blender-review-loop.md` | How an agent that cannot scrub a timeline checks Blender animation: the numeric self-audit on F-curves, cheap still and preview renders, which frames to look at and for what, and the stages from blocking to polish. |
| `_shared/animation/building-door-locks.md` | How a 1.30 building door takes a combination lock or a code lock: the slots, the `class Doors` keys, the memory names script looks up, the two lock items, the bunker door, and what breaks when a 1.29 door mod moves to 1.30. |
| `_shared/animation/device-animation-patterns.md` | Which `config.cpp` source and which script call drive a device's `model.cfg` animation, and five worked patterns: toggle switch, push button, hinged lid, dial with set positions and drawer. |
| `_shared/animation/device-switch-box.md` | A complete device with a toggle switch, a push button, a hinged cover and a coloured LED, as `model.cfg`, `config.cpp` and script, plus the two ways to light a screen and why they must not be combined. |
| `_shared/animation/door-open-and-lock-code.md` | How vanilla 1.30 script decides whether a building door may open, how the one sided door check works, and why combination and code locks are not `EBuildingLockType` values. |
| `_shared/animation/loop-notetracks.md` | How a clip for a hold action that a script timer ends, such as unjamming a weapon, must carry `LoopStart` and `LoopEnd`, how long the loop must last, and how to leave it without a jerk. |
| `_shared/animation/rider-pose-measured.md` | What was measured in game on 1.30 when a mod's own rider pose was swapped in for one motorbike class through a child instance file, with vanilla clips and with clips of its own, and the traps found. |
| `_shared/animation/txa-bones-and-axes.md` | Which skeleton bones a Blender clip keys or leaves out for DayZ, and how the plugin and the SEAnim exporter turn Blender axes into DayZ axes. |
| `_shared/animation/weapon-anim-authoring.md` | How to author each kind of player weapon clip in Blender (IK pose, fire, weapon states, reload, hold actions), what a full body action on a weapon must leave out, and the rules vanilla clips follow for helper bones. |
| `_shared/animation/weapon-anim-compile.md` | How to export a weapon clip from Blender as `.txa`, set its events, what the plugin's two coordinate changes are, how Workbench compiles `.txa` to `.anm`, and what the compile loses. |
| `_shared/animation/weapon-anim-testing.md` | How to build, deploy and test a custom player weapon animation, how to judge the elbow, the failures that look done and are not, the RPT lines to expect, a full checklist, the timing of the vanilla AKM clips, and what is still unconfirmed. |
| `_shared/animation/weapon-anim-wiring.md` | How a compiled weapon clip reaches the player: the instance file, the state names it may fill, the script registration and bone remap, how the graph picks column and state, the weapon's own `model.cfg` and `config.cpp`, and the mod layout. |
| `_shared/models/model-config-and-packing.md` | What a new model needs from `config.cpp`, how its addon folder is laid out, and how it is packed and tested. |
| `_shared/textures/rvmat-mod-patterns.md` | Material recipes beyond the basic Super material: flat colors, a damage overlay, lit panels, glass, emissive. |
| `_shared/textures/procedural-textures.md` | How to generate the `_co`, `_nohq` and `_smdi` maps of a generated model in Python with coherent noise: the maps to target, OpenSimplex noise and FBM, building a surface in layers with blend modes, and the mistakes that make a texture look procedural. |
| `_shared/textures/paa-file-layout.md` | How a DayZ `.paa` file is laid out byte by byte: the format magic, the tagged header, the mip headers, the terminator, and how a DXT1 block stores 16 pixels. |
| `_shared/textures/procedural-normal-and-smdi.md` | How to turn a height map into a DayZ `_nohq` with a Sobel filter, how to get a height map from a color texture, and how to write a flat `_smdi` per material with the right channel packing. |
| `_shared/textures/procedural-recipes.md` | Ready recipes for the surfaces of electrical and industrial props: painted metal, brushed steel, rubber, a rust overlay, baked AO multiplied into the color, and a full script that writes all three maps for an electrical box. |
| `_shared/models/domain-recipes.md` | Not yet checked on `P:\`: three results measured on real mods: cookware, a client side cable segment, and an asset posed in the hands. |
| `_shared/models/device-recipes.md` | Third-party mod practice, not vanilla: which worked specifications exist for electrical devices (a push button, a wall switch, a battery adapter, a sorter, a generator, a cable segment and a junction box), the design language they share, their vertex budgets and naming, and a template for a new device. |
| `_shared/models/artist-returns.md` | What to check when a `.p3d`, `.paa` or `.rvmat` comes from outside the repo. Process rules learned on mod projects. |
| `_shared/models/unconfirmed-findings.md` | Not checked on `P:\`: three unconfirmed findings of medium confidence, to use as red flags during a model audit. |
| `_shared/models/generated-model-troubleshooting.md` | Symptom, root cause and fix for the failures the pipeline produces most. Causes and fixes come from mod projects and are not checked on `P:\`. |
| `_shared/models/dayz-1-30-models.md` | What 1.30 changes for meshes, proxies, houses, wells and the model cache, with an evidence label on each line. |
| `_shared/models/tools-3d-viewer-states.md` | Planned, not built: where a model's moving parts and material states are defined, across the `.p3d`, `model.cfg` and `config.cpp`, and the maths that turns an animation phase into a movement. |
| `_shared/models/blender-assembly-checks.md` | What to check after each part of a model built in Blender over MCP, how to finish the scene, the rules that catch the rarer faults, and the two render traps over MCP. |
| `_shared/models/blender-headless-export.md` | How to export OBJ files from a windowless Blender script for py3d to assemble, how to make the LOD set, the mistakes that lose data on the way, and a script template. |
| `_shared/models/blender-review-checklist.md` | Which faults to look for when you review a Blender model's renders: general 3D faults, a comparison with a vanilla model, a comparison with a reference image, and scoring likeness to a photo. |
| `_shared/models/blender-winding-flips.md` | Why a Blender render cannot judge DayZ face winding, the two Blender checks that still catch a reversed winding before export, and why a vision model cannot answer the question either. |
| `_shared/models/building-collision-limits.md` | How to build the collision of a large building with rooms inside so that it follows the visible walls and still passes Binarize, which can reject a collision LOD with no message at all. |
| `_shared/models/device-recipes-controls.md` | Worked specifications of two control devices of a third-party electrical power mod: a push button and a wall switch, with their geometry, memory points, selections, animations, LED states, textures and config. |
| `_shared/models/device-recipes-distribution.md` | Worked specifications of two distribution devices of a third-party electrical power mod: a six output sorter and a six port junction box. |
| `_shared/models/device-recipes-power.md` | Worked specifications of three power devices of a third-party electrical power mod: a battery adapter, a floor generator and the cable segment drawn between devices. |
| `_shared/models/model-material-file.md` | What a Super shader `.rvmat` for a new model holds, stage by stage, which texture suffix goes where, and how a part is made to glow. |
| `_shared/models/proxy-attachment-config.md` | How the `CfgNonAIVehicles` class that makes an attached item visible is named and written, and why an item needs a proxy class of its own rather than a slot added to a vanilla vehicle part. |
| `_shared/models/py3d-axis-map.md` | How to map geometry made with Z up (Blender, or code written that way) into a DayZ `.p3d`, which has Y up, without mirroring it or turning it inside out, and when a py3d script may reverse faces. |
| `_shared/models/py3d-collision-and-mass.md` | How to check a model's baked mass and centre of mass offline with `binarize.exe` instead of a full build and spawn, how to build a collision LOD from a convex hull with py3d, and the needle triangles a hull can carry that rays pass through. |
| `_shared/models/py3d-part-checks.md` | Py3d checks for a generated model's proxies, its selections across LODs and its collision LODs, and a runner that calls these and the shape checks of `py3d-shape-checks.md` in one go. |
| `_shared/models/py3d-proxies.md` | How to write a proxy triangle into a parent model with py3d, what the triangle is made of, and how to write the minimal proxy model the selection points at. |
| `_shared/models/py3d-reading.md` | How to open an existing MLOD model with the py3d in `scripts/tools/py3d` and read its LODs, points, faces, selections, named properties, bounds and texture paths. |
| `_shared/models/py3d-shape-checks.md` | Quick py3d checks for the commonest faults in a generated model, centring, axes, UVs and face winding, and the repairs that go with them. |
| `_shared/models/tools-3d-viewer-states-build.md` | How the viewer tool in `scripts/tools/dayz-3d-viewer` would play a model's animations and swap its materials: the group tree in Three.js, the movement and swap code, the two config readers it needs, the data the extractor would add, and the order to build it in. |

### Not file packs

- Vanilla source search is the `dayz-rag` MCP server, not a file. Its rules are in `dayz-conventions.md` ("Vanilla source search").
- Tier 2 topic rules live in `conventions/` and are listed in `dayz-conventions.md`, not here.
