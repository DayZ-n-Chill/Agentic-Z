Agentic-Z Guide

Guide · October 2026

# Agentic-Z

The Guide

This guide gets you from a clean install to a tested mod on your own server. You will set up your DayZ modding environment, meet the agents and skills, and ship your first build.

Agentic-Z · DayZ n' Chill · github.com/DayZ-n-Chill/Agentic-Z

# Agentic-Z Guide

Agentic-Z is the AI agent stack for DayZ modding, and this is its reference. This edition covers version 2.0.0, with 30 agents, 44 skills, three hooks, and a side panel plugin.

## Contents

- [Overview](#overview)
  - [Specialists](#specialists)
  - [Skills](#skills)
  - [RAG search](#rag-search)
- [Architecture](#architecture)
- [Requirements](#requirements)
  - [Optional features](#optional-features)
- [Installation and setup](#installation-and-setup)
  - [Option A: clone as a template](#option-a-clone-as-a-template)
  - [Option B: install as a Claude Code plugin](#option-b-install-as-a-claude-code-plugin)
  - [Setup wizard](#setup-wizard)
- [Build loop](#build-loop)
- [Agents](#agents)
- [Gates](#gates)
  - [Team structure](#team-structure)
- [RAG search](#rag-search-1)
- [Rule tiers](#rule-tiers)
- [Token savers](#token-savers)
- [Domain specialists](#domain-specialists)
  - [Specialist reference](#specialist-reference)
- [Specialist procedures](#specialist-procedures)
- [Paste-in routing](#paste-in-routing)
- [Versions](#versions)
- [Skill reference](#skill-reference)
- [File layout](#file-layout)
- [Configuration](#configuration)
- [Permissions and safety](#permissions-and-safety)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Support and contributing](#support-and-contributing)

## Overview

Agentic-Z gives you a full DayZ modding team inside Claude Code. It ships as a Claude Code plugin or as a repo template you clone for each new mod.

You get DayZ specialist agents and skills (slash commands) that drive DayZ Tools for you.

The `dayz-rag` MCP server searches the vanilla game files on your P: drive.

### Specialists

- Scripts, configs, and UI
- Models and textures
- Maps and servers
- Saved data and AI
- Vehicles and weapons
- Wearables and animation
- Audio, effects, and physics
- Review and debugging

### Skills

- A setup wizard
- Linting and building PBOs
- Test launches and gates
- types.xml editing
- Textures and layouts
- Release packs

### RAG search

- Vanilla scripts
- Configs
- Layouts
- Materials

| Feature | Claude Code | Codex CLI | Gemini CLI |
| --- | --- | --- | --- |
| Skills | Yes | Yes, linked by `/sync-skills` | Yes, linked by `/sync-skills` |
| Rules file | `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` |
| Agents, hooks, RAG search | Yes | No | No |

## Architecture

Your AI tool loads the Agentic-Z rules, agents, and skills, then calls the `dayz-rag` MCP server. Together they work on your mod folder, the P: drive, DayZ Tools, the game, and the search index on disk.

\*[diagram]\*

## Requirements

| Requirement | Needed for |
| --- | --- |
| Windows | DayZ Tools and the P: drive run only on Windows. |
| DayZ (Steam) | Test sessions. `DayZDiag_x64.exe` ships next to `DayZ_x64.exe`. |
| DayZ Tools (Steam, free) | AddonBuilder, mounting the P: drive, and ImageToPAA. |
| DayZ Server (Steam, app 223350) | `/dayz-add-server` copies the mission template from it for each new instance and for `--refresh-mission`. |
| P: mounted, with vanilla data extracted | Configs inherit from the vanilla classes on P:. |
| Python 3.10+ on PATH | The skills are Python scripts. |
| Claude Code, Codex CLI, or Gemini CLI | This is your AI tool. "Overview" shows which features each one supports. |

### Optional features

| Feature | Needs |
| --- | --- |
| RAG search | Run `pip install -r .claude\mcp\dayz-rag\requirements.txt` and put `VOYAGE_API_KEY=pa-...` in `.env` at the repo root. |
| Building the index (`/dayz-search-index`) | Also run `pip install -r .claude\skills\dayz-search-index\requirements.txt`. |
| Figma pipeline | A Figma MCP server. |
| `/dayz-p3d-audit` | py3d. |
| `/dayz-build-imageset`, `/dayz-layout-preview`, `/dayz-gate visual` | Pillow. |
| `/dayz-cot-bootstrap` | The admin tool mods, installed first. The skill then makes you an admin in them on your test server. |

## Installation and setup

\*[diagram]\*

Pick one way to install Agentic-Z. A clone and a plugin together load every skill twice.

|  | Option A: clone | Option B: plugin |
| --- | --- | --- |
| Use for | A new mod project | An existing project |
| Skill names | `/dayz-build-pbo` | `/agentic-z:dayz-build-pbo` |
| Orchestrator | `claude --agent dayz-orchestrator` | `claude --agent agentic-z:dayz-orchestrator` |
| Permissions | Shipped in `.claude/settings.json` | None, because plugins cannot ship permissions |
| Updates | `/agentic-z-update` | The Claude Code plugin marketplace |

### Option A: clone as a template

```
git clone https://github.com/DayZ-n-Chill/Agentic-Z.git my-dayz-mod
cd my-dayz-mod
python .claude\skills\sync-skills\sync.py
```

### Option B: install as a Claude Code plugin

```
/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill
```

### Setup wizard

```
/dayz-init
```

The wizard gets you ready to mod. On the first run, it asks whether you want a new mod or an import. Then it asks for the mod name, the test map, and whether to build and launch.

It fixes what it can on its own, such as mounting P: and creating the `P:\Mods` link. For anything else, it prints the exact fix. After that, each run opens a status hub for your active mod.

## Build loop

This is the loop you will run every day. Describe a change, build it, and see it in game.

\*[diagram]\*

1. Ask an agent for the change, for example "add a hidden selection for the camo".
2. Run `/dayz-build-pbo <ModName>` to pack the mod into `P:\Mods\@<ModName>\Addons\`.
3. Run `/dayz-launch-test <ModName> --server <instance>` to start a DayZ Diag server and client with the mod loaded.
4. Read the logs ("File layout" lists where they are), or hand them to `dayz-mod-debugger`.
5. Run `/dayz-stop-test` to stop every `DayZDiag_x64.exe` process.

## Agents

Describe the task, and Claude Code picks the right specialist. You can also name one yourself: "use the dayz-config-specialist to ...". "Domain specialists" gives the full scope and output of the eight domain specialists.

| Agent | Scope | Example request or entry point |
| --- | --- | --- |
| `dayz-script-specialist` | Enforce Script, including modded classes, RPCs, and game logic. | "Make my medkit heal over 30 seconds." |
| `dayz-config-specialist` | config.cpp, CfgPatches, inheritance, and hidden selections. | "Write the CfgVehicles entry for my vest." |
| `dayz-asset-specialist` | Textures (.paa) and materials (.rvmat). | "Pack vest\_camo\_co.png and make an rvmat." |
| `dayz-object-builder` | .p3d models, including LODs, selections, and Object Builder steps. | "Set up hidden selections on my vest model." |
| `dayz-ui-specialist` | .layout files and HUD and menu scripts. | "Add a compass to the HUD." |
| `dayz-map-specialist` | Terrain Builder, layers.cfg, surfaces, and clutter. | "Export my base from DayZ Editor to Terrain Builder." |
| `dayz-server-admin` | types.xml, events, init.c, and cfggameplay. | "Make my vest spawn rarely in military zones." |
| `dayz-workbench-specialist` | Workbench plugins, which are editor tools. | "A plugin that checks texture suffixes." |
| `dayz-mod-debugger` | Reads logs and crash files to find the cause. | "My server crashes on start, here is the RPT." |
| `dayz-mod-reviewer` | Audits a mod without changing it and returns PASS or FAIL. | "Review workspace/MyVest before I build." |
| `figma-node-normalizer`, `figma-to-dayz-layout`, `dayz-layout-validator` | The optional Figma pipeline turns a Figma frame into a `.layout`. The validator checks it without editing. | "Turn this Figma frame into a DayZ menu." |
| `dayz-orchestrator` and team | Plans a whole mod and runs the leads, workers, and checks. | Plugin: `claude --agent agentic-z:dayz-orchestrator`. Clone: `claude --agent dayz-orchestrator`. |
| `dayz-mod-architect` | Plans a mod's classes, files, assets, and task list. | Started by the orchestrator. |
| `dayz-lead` | Runs one team (script, config, art, UI, server, or release) and its review checks. | Started by the orchestrator. |
| `dayz-build-checker`, `dayz-ingame-tester` | Fallback gates used when a `/dayz-gate` script errors (exit 2). | Started by the orchestrator. |
| `dayz-build-engineer` | Builds the PBO (or deploys a prebuilt bundle) and starts a test session for you. | "Build MyVest and start a test on chernarus." |
| `dayz-docs-writer` | Writes the mod README, changelog, and classname list. | "Update the MyVest docs." |
| `dayz-persistence-specialist` | Saving data across restarts, save versions, base building, and a data audit before release. | "Make my safe keep its code and contents after a restart." |
| `dayz-ai-specialist` | Infected, animals, and human AI such as patrols and guards, written from scratch. | "Add guards that patrol my base and react to gunfire." |
| `dayz-vehicle-specialist` | Cars, boats, and helicopters, including engine, gearbox, wheels, doors, fluids, seats, and damage. | "Add a four door pickup with a bigger fuel tank." |
| `dayz-weapon-specialist` | Weapons, magazines, ammo, attachments, recoil, and fire modes. | "Add a hunting rifle that takes a five round magazine." |
| `dayz-wearables-specialist` | Clothing, characters, inventory slots, protection, color variants, and proxies. | "Make a plate carrier in three colors." |
| `dayz-animation-specialist` | model.cfg animations, RTM files, and the handoff to Blender. | "Make my bunker doors open and close." |
| `dayz-audio-fx-specialist` | Sound shaders, sound sets, and particle effects. | "Give my generator a running sound and exhaust smoke." |
| `dayz-physics-specialist` | Weight, collision LODs, dropping, throwing, and contact. | "My crate falls through the floor. Fix it." |
| `dayz-router` | A fast Haiku agent that picks the handler when the `/dayz-route` stages are not confident. | Called after `/dayz-route`. |
| `agent-creator` | Writes and checks new agent files. | "Create an agent that reviews RPC security." |

## Gates

Agentic-Z never hands you a mod it has not checked. `dayz-orchestrator` runs a full mod build as the main session.

Start it with `claude --agent agentic-z:dayz-orchestrator` (plugin) or `claude --agent dayz-orchestrator` (clone). It plans the mod with `dayz-mod-architect` and waits for your approval. Then it runs the work in waves.

Each wave passes these gates in order. "Team structure" explains who runs each gate.

| Gate | Runs | Checks |
| --- | --- | --- |
| Mod review (`dayz-mod-reviewer`) | On every task | Convention compliance and common defects, without changing files. |
| Layout check (`dayz-layout-validator`) | On every `.layout` change | The Figma-to-DayZ rules, without changing files. |
| Build (`/dayz-gate build`) | Once per wave | `/dayz-lint` first, then the AddonBuilder output. |
| In-game (`/dayz-gate ingame`) | Once per wave | Server and client logs after the client joins the mission. |
| Behavior (`/dayz-gate behavior`) | Once per wave, when `output\<ModName>-plan\behavior-checks.json` exists | A scripted mission spawns and uses each new item. |

`/dayz-gate` prints its verdict on the first line: `PASS` (exit 0), `FAIL` (exit 1), or `ERROR` (exit 2). If the gate script itself returns an `ERROR`, the orchestrator falls back to `dayz-build-checker` or `dayz-ingame-tester`. The behavior gate has no fallback agent.

Nothing reaches you until it builds and loads in game with clean logs. When the plan lists behavior checks, it must also pass the behavior gate.

\*[diagram]\*

### Team structure

The leads (`dayz-lead`) run the mod review and the layout check on each task. The orchestrator runs the build check and the in-game test once per wave.

It runs them one at a time, because there is only one mod folder and one test session. When the plan lists behavior checks, it runs the behavior test the same way. Workers run at the same time only when their tasks touch different files.

## RAG search

The `dayz-rag` MCP server searches an index of the vanilla game files on your P: drive.

`/dayz-search-index` builds the index with Voyage AI embeddings (`voyage-code-3` by default). It stores the index in LanceDB at `~\.claude\dayz-search-index\`.

You can run `/dayz-search-download` to install a prebuilt index instead, but that index is older than the current indexer. Searching still needs `VOYAGE_API_KEY`, because the Voyage AI API embeds each query.

\*[diagram]\*

| MCP tool | Function |
| --- | --- |
| `search_dayz_source` | Searches vanilla scripts, configs, layouts, and materials by meaning. |
| `get_dayz_file` | Opens an exact file and line range on P:. |
| `list_indexed_sources` | Lists what is indexed and when. |

Agents look things up in a set order. When they know an exact class or symbol name, they use Grep first. They use RAG search for questions by meaning, or after two or three greps fail.

A search hit is only a hint until the agent opens the real file.
## Rule tiers

\*[diagram]\*

Tier 2 holds the DayZ rules. It is `.claude/skills/_shared/dayz-conventions.md` plus five topic files in `conventions/`. The topic files are `config.md`, `assets.md`, `scripts.md`, `ui.md` and `server.md`. When you correct an agent, `/dayz-record-correction` writes the rule into the right tier once you approve it. Every fix you make becomes part of Agentic-Z.

## Token savers

Agentic-Z hands mechanical work to scripts and smaller models. Your model tokens go where they count: planning, writing code and configs, review, and diagnosis.

\*[diagram]\*

| Feature | Behavior | Usage |
| --- | --- | --- |
| Script gates | They build your mod or load it in game, then print `PASS` or `FAIL` without a model call. "Gates" lists the exit codes. | `/dayz-gate build <ModName>`, `/dayz-gate ingame <ModName>` |
| Log triage | It matches each failure against 52 known errors in `known-errors.json`. Each known error comes with a fix and an owning agent. Only new errors reach `dayz-mod-debugger`. | It runs inside `/dayz-gate`. Run `triage.py --learn` to add entries. |
| Router | It picks the handler in three stages. Keyword rules in `rules.json` go first. Next comes Jev, TypeSafe's routing model, used only when `TYPESAFE_API_KEY` is set. Last is the `dayz-router` agent on Haiku. A stage's answer is final at a confidence of 0.8 or more. | Run `/dayz-route "<request>"`. The main session runs it first for every new DayZ request. |
| Hooks | The PostToolUse hook `edit_check.py` checks `config.cpp` and `.layout` syntax after every `Edit`, `Write` or `MultiEdit`. It sends any problems straight back to Claude. The PreToolUse hook `scope_guard.py` blocks edits to other mods while `/dayz-scope-mod` is active. "Paste-in routing" covers the UserPromptSubmit hook `paste_router.py`. | The plugin registers them in `hooks/hooks.json`, and a clone registers them in `.claude/settings.json`. |
| Status line | It shows whether P: is mounted, which mod is active, whether DayZ Diag is running, and how old the search index is. | Run `/dayz-statusline` once per project. |
| Launcher panel | It puts a control panel beside the chat. Buttons cover mount P:, build, the build and in-game gates, deploy, launch and stop. More buttons open Workbench, Object Builder, test logs, the health page and the release pack. A question field sends straight to `/dayz-ask`. | Run `/plugin install agentic-z-panel@dayz-n-chill`, then `/dayz-panel`. |
| Smaller models | `dayz-build-engineer` and `dayz-router` run on Haiku, and `dayz-docs-writer` runs on Sonnet. | Each agent sets this in its `model:` field. |
| No-model wrappers | Every runnable skill has a `.bat` file, so you can run it without the AI. | `scripts\README.md` lists them. |

## Domain specialists

Eight specialists cover saving data, vehicles, weapons, wearables, animation, audio and FX, physics and AI. They work beside the script, config, art, UI, map and server workers. Each specialist reports to a team lead and loads only when a task needs it. "Agents" has the one-line index. The tables below give each specialist's scope and output.

\*[diagram]\*

### Specialist reference

| `dayz-persistence-specialist` | |
| --- | --- |
| Scope | It keeps the data of your modded items and systems across server restarts. It writes the save and load code (`OnStoreSave` and `OnStoreLoad`) and stamps every save with a version number. It also writes the upgrade path, so old saves still load after your mod changes. It covers base building parts that must survive restarts. Before release, it audits your data to confirm every saved field is written and read back in the same order. |
| Example request | "Make my safe keep its code and contents after a restart, and do not break saves from the last version." |
| Lead | Script lead (the release audit goes to the server lead) |
| Returns | Save and load code with a version number, a migration note for old saves, and an audit report for the server lead. |

| `dayz-vehicle-specialist` | |
| --- | --- |
| Scope | It covers cars, boats and helicopters. That means the vehicle class and its simulation (engine, gearbox, axles, wheels) and attached parts (doors, hood, trunk, wheels, battery, spark plug). It also handles fluids (fuel, oil, coolant, brake fluid), seats and crew positions, and damage. Vanilla DayZ ships native helicopter base classes (`Helicopter`, `HelicopterAuto` and `HelicopterScript`), but no flyable helicopter. The specialist builds flyable ones on those classes with your own code and never copies them from another mod. |
| Example request | "Add a four door pickup with its own doors and a bigger fuel tank." |
| Lead | Config lead |
| Returns | CfgVehicles entries, the `CarScript`, `BoatScript` or `HelicopterScript` class, attachment slots, and a `types.xml` entry for the server lead. |

| `dayz-weapon-specialist` | |
| --- | --- |
| Scope | It covers firearms. That means the weapon class, magazines, ammunition, attachment slots (optics, suppressors, stocks, handguards), recoil, fire modes and muzzle effects. Each weapon inherits from the closest vanilla weapon, so reloading, jamming and damage behave as they do in the base game. |
| Example request | "Add a scoped hunting rifle that takes a five round magazine and the vanilla long range optics." |
| Lead | Config lead |
| Returns | CfgWeapons, CfgMagazines and CfgAmmo entries, a recoil class, and the model selections the art lead must provide. |

| `dayz-wearables-specialist` | |
| --- | --- |
| Scope | It covers clothing, gear and characters. That means the inventory slot, the slots an item holds, protection and insulation, and hidden selections that let one model carry several textures. It also handles how items display on the character through proxies. It builds new survivor characters too. |
| Example request | "Make a plate carrier with three colors that fits the vest slot and holds six items." |
| Lead | Art lead |
| Returns | Config entries, hidden selection names, texture slots for each color, and proxy notes for `dayz-object-builder`. |

| `dayz-animation-specialist` | |
| --- | --- |
| Scope | It covers moving parts such as doors, lids, hatches and triggers. It writes the `skeletonBones` for the moving parts and the `class Animations` block in `model.cfg` (rotations, movements, hiding parts). The rest of `model.cfg` stays with `dayz-object-builder`. It handles `.rtm` animation files and writes the Blender handoff, so bones and selections line up in Object Builder. |
| Example request | "Make the doors on my bunker open and close when a player uses them." |
| Lead | Art lead |
| Returns | The `skeletonBones` and `class Animations` entries, the selection and bone names the model needs, and the script hook that plays the animation, for `dayz-script-specialist` to write. |

| `dayz-audio-fx-specialist` | |
| --- | --- |
| Scope | It covers sound shaders and sound sets, sound range and volume, and particle effects such as smoke, sparks and muzzle flashes. It uses the `/dayz-particles` skill for particle files. |
| Example request | "Give my generator a running sound that fades with distance and a puff of exhaust smoke." |
| Lead | Any lead |
| Returns | CfgSoundShaders and CfgSoundSets entries, particle files, and the script lines that play them. |

| `dayz-physics-specialist` | |
| --- | --- |
| Scope | It covers weight, collision shapes in the Geometry and Fire Geometry LODs, how objects land when dropped or thrown, and contact with players and vehicles. It diagnoses common faults, such as items falling through floors or bullets passing through walls. |
| Example request | "My crate falls through the floor when I drop it. Fix it." |
| Lead | Any lead |
| Returns | Geometry and mass fixes for `dayz-object-builder`, and config changes for the config lead. |

| `dayz-ai-specialist` | |
| --- | --- |
| Scope | It covers behavior for computer controlled characters, including infected, animals and human AI such as patrols and guards. It writes original behavior code for your mod and copies nothing from another mod. |
| Example request | "Add a patrol of guards that walk a route around my military base and react to gunfire." |
| Lead | Script lead |
| Returns | Script classes for the behavior, the config the server lead needs to spawn them, and notes on server performance. |

Workers get a spec step in `/dayz-init` before building, and `/dayz-layout-preview` for several screen sizes.
## Specialist procedures

Every specialist follows a set procedure inside the team loop described in "Gates". Specialists that write DayZ content check vanilla first, as described in "RAG search". `dayz-build-engineer`, `dayz-docs-writer`, `dayz-build-checker`, `dayz-ingame-tester` and `figma-node-normalizer` have no RAG tools. They work from the mod, its logs or the Figma file.

| Specialist | Procedure |
| --- | --- |
| Script lead | |
| `dayz-script-specialist` | 1. It searches the vanilla scripts for the class it will change and reads the real file. 2. It writes a `modded class` in the right layer (3\_Game, 4\_World or 5\_Mission) and calls `super`. 3. It adds RPCs only where the client and server must talk, and it checks which side runs each line. 4. `/dayz-lint` and the build gate check and pack it, because nothing there compiles Enforce Script. The in-game gate catches compile errors and reads script.log. |
| `dayz-workbench-specialist` | 1. It reads how vanilla Workbench plugins are registered. 2. It writes the plugin script and its tool panel. 3. It never opens Workbench itself. Instead, it tells the user to open it with `/dayz-launch-workbench --mod <ModName>`. 4. It returns the plugin and the steps to load and run it. |
| `dayz-persistence-specialist` | 1. It lists every value that must survive a restart. 2. It writes OnStoreSave and OnStoreLoad, with a version number written first. 3. It adds an upgrade path so that saves from the last version still load. 4. It runs the data audit, which confirms that the code writes and reads back every field in the same order. 5. It hands the audit to the server lead before release. |
| `dayz-ai-specialist` | 1. It reads how vanilla infected and animals decide what to do. 2. It writes the behavior as its own script classes and never copies them from another mod. 3. It gives the server lead the spawn setup. 4. The in-game test watches the behavior and the server's performance. |
| Config lead | |
| `dayz-config-specialist` | 1. It finds the closest vanilla parent class. It uses Grep for known names, or RAG search for questions by meaning. It then reads the definition on disk. 2. It writes CfgPatches with the right requiredAddons, then the class itself. 3. It matches hiddenSelections to the names in the model. 4. `/dayz-lint` and the build gate check that it loads. |
| `dayz-vehicle-specialist` | 1. It picks the closest vanilla vehicle as the parent. 2. It writes the vehicle class and its simulation, which covers the engine, gearbox, axles and wheels. 3. It adds attachment slots for the doors, hood, trunk, wheels, battery and plug, and it adds the fluids. 4. It writes the CarScript or BoatScript class for seats, doors and damage. 5. It gives the server lead a types.xml entry. The behavior gate spawns the vehicle, and a checklist run by a person covers driving. |
| `dayz-weapon-specialist` | 1. It picks the closest vanilla weapon as the parent. 2. It writes the weapon, magazine and ammo classes and the attachment slots. 3. It sets recoil and fire modes. 4. It lists the model selections and memory points that the art lead must provide. 5. The behavior gate spawns the weapon and fits each attachment. A checklist run by a person covers firing and reloading. |
| Art lead | |
| `dayz-object-builder` | 1. It specifies the LODs (visual, geometry, fire geometry, view geometry and memory) as numbered Object Builder steps. The user builds them, because the specialist cannot edit a .p3d. 2. It names the selections and memory points that the config and animations need, and it writes model.cfg. 3. It runs `/dayz-p3d-audit` after the user saves the model. 4. It hands the selection names to the config lead. |
| `dayz-asset-specialist` | 1. It checks that each texture has the right suffix (\_co, \_nohq, \_smdi and the rest). 2. It packs them with `/dayz-pack-texture`. 3. It writes the .rvmat for each material. 4. It writes a checklist so the user can check the look in Object Builder or in game. It never launches either one. |
| `dayz-wearables-specialist` | 1. It picks the inventory slot and the closest vanilla item as the parent. 2. It sets the slots held, the protection and the insulation. 3. It sets hidden selections so that one model carries every color. 4. It notes the proxy positions for the Object Builder specialist. 5. The behavior gate wears each color class, and a person checks in game how each color looks. |
| `dayz-animation-specialist` | 1. It lists the moving parts and their bones. 2. It writes skeletonBones for the moving parts and the class Animations block in model.cfg. The Object Builder specialist keeps the rest of model.cfg. 3. It gives the user the bone and selection names for their own Blender export. 4. It names the script hook that plays the animation. The script specialist writes that code, and the in-game test uses it. |
| UI lead | |
| `dayz-ui-specialist` | 1. It reads the vanilla layout closest to the new screen. 2. It writes the .layout and the script class that drives it. 3. It builds icons into an imageset with `/dayz-build-imageset`. 4. The layout checker checks the layout, and `/dayz-layout-preview` draws it. The in-game test opens it. |
| `figma-node-normalizer` | 1. It reads the Figma frame. 2. It cleans up layer names and structure so that they map to DayZ widgets. 3. It hands the clean tree to the layout converter. |
| `figma-to-dayz-layout` | 1. It turns the clean tree into a DayZ .layout. 2. It uses only widget types that the game supports. 3. It hands the layout to the layout checker. |
| Server lead | |
| `dayz-server-admin` | 1. It writes types.xml entries with `/dayz-edit-types`. 2. It adds events, spawn points and gameplay settings where needed. 3. It splits large economy files with `/dayz-split-types`. 4. It sets up a missing test server instance with `/dayz-add-server`, which starts nothing. It gives you the `/dayz-launch-test` command instead of starting the server itself. |
| `dayz-map-specialist` | 1. It writes layers.cfg and the surface and clutter configs. If it needs the user's own layers.cfg and that file is missing, it stops and asks for it. 2. It gives numbered steps for the DayZ Editor export and for the Terrain Builder import and generation, which the user carries out. 3. It returns the files and the steps to rebuild the map. |
| Release lead | |
| `dayz-build-engineer` | 1. It packs the mod with `/dayz-build-pbo`. 2. It starts the test session with `/dayz-launch-test`. 3. It reports the build result to the release lead, who passes it to the orchestrator. |
| `dayz-docs-writer` | 1. It reads what changed in the wave. 2. It updates the README, the changelog and the classname list. 3. It writes the Workshop text and the server-owner notes with `/dayz-release-pack`. |
| Any lead | |
| `dayz-audio-fx-specialist` | 1. It reads the vanilla sound or particle closest to the request. 2. It writes the sound shader and sound set, or it writes the particle with `/dayz-particles`. 3. It adds the script line that plays it. 4. The in-game test listens and looks. |
| `dayz-physics-specialist` | 1. It reads the model's geometry LODs and mass. 2. It finds the fault, which is missing geometry, the wrong mass or bad collision. 3. It hands the fix to the Object Builder or config specialist and never edits anything itself. 4. A person runs an in-game test that drops, throws and shoots the object, which the behavior gate cannot do. |
| Checks and fixes | |
| `dayz-mod-reviewer` | 1. It reads the finished task against the DayZ rules file. 2. It lists each problem along with the specialist who owns it. 3. It never edits files. |
| `dayz-layout-validator` | 1. It checks the .layout's file format and widget classes. 2. It reports PASS or FAIL with each problem and its line. It never edits. |
| `dayz-build-checker` | 1. It runs only when `/dayz-gate build` itself breaks. 2. It reads the AddonBuilder output and names the failing file. |
| `dayz-ingame-tester` | 1. It runs only when `/dayz-gate ingame` itself breaks. 2. It reads the logs from the test session and reports what failed. |
| `dayz-mod-debugger` | 1. It receives new errors that triage does not recognize. 2. It traces script.log, RPT and crash files back to the line that failed. 3. It reports the cause, evidence, location and fix to whoever called it (the orchestrator or a lead). It also names the worker agent that owns the fix. |

## Paste-in routing

Paste in a log, a link or a screenshot, and Agentic-Z knows what to do with it. The UserPromptSubmit hook, `paste_router.py`, points Claude at the matching workflow. It never blocks a prompt.

| Pasted input | Result |
| --- | --- |
| Crash log, RPT or `script.log` lines | The hook triages them against the `/dayz-gate` known errors. It gives the cause and fix for known lines, and it sends new lines to `dayz-mod-debugger`. |
| Screenshot of a bug | The hook suggests a specialist. UI problems go to `dayz-ui-specialist`, texture or material problems go to `dayz-asset-specialist`, and an error message or wrong behavior goes to `dayz-script-specialist`. The `dayz-router` agent sends an on-screen error message to `dayz-mod-debugger` (or to gate triage) instead, so the two can disagree in that case. |
| Figma link | It runs the Figma pipeline and returns a checked `.layout`. |
| GitHub link | It points at `/dayz-import-mod --source <link>`, which imports the mod into `workspace\` and can add the missing standard pieces. |
| Steam Workshop link | It refuses the link and gives the reason: Workshop content is packed, binarized and often protected. |
| `types.xml` chunk | It checks the entries, lists any problems and points at `/dayz-edit-types --merge`. |

## Versions

Version 2.0.0 follows 1.6.0. There is no 1.7.0 or 1.8.0. The release notes are in `docs/release-notes/`.

| Version | Contents |
| --- | --- |
| 1.6.0 (`main`) | This version has 14 agents and 29 skills (25 of them for DayZ). It includes the workers, the reviewer and the debugger, the Figma-to-DayZ pipeline, and the `dayz-rag` search server with source and wiki search. |
| 2.0.0 (`develop`) | This version has 30 agents and 44 skills (40 of them for DayZ). It includes the orchestrator, the leads, the router and eight domain specialists. It also includes script gates, hooks, the token-saving layer, the side panel, answer tests and CI. Search covers only the vanilla source. |

## Skill reference

Agentic-Z gives agents and users 44 skills (slash commands). Of these, 40 ship in the plugin, while `/sync-skills`, `/agentic-z-update`, `/docs-sync` and `/clean-repo` exist only in a clone. Each skill runs as a script where it can, and it asks the AI only for judgment.

- **Environment check:** 18 of the 40 plugin DayZ skills run `/dayz-preflight` first. Preflight is itself the check.
- **Exceptions:** The Tier 2 rules file has 14 exception entries that name 21 skills, and each entry gives its reason. `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe`, `/dayz-layout-preview` and `/dayz-upgrade-guard` read P:, but they only read files and write a report. `/dayz-ask` only checks that P: is mounted. `/dayz-gate` runs the check through the scripts it calls. `/dayz-stop-test` skips the check.
- **Reference only:** `/dayz-particles` has no script.

| Skill | Function |
| --- | --- |
| Setup | |
| `/dayz-init` | On the first run, it is a setup wizard with an optional spec step. After that, it is a status hub for the active mod. |
| `/dayz-preflight` | It checks that P: is mounted, DayZ Tools is installed, the vanilla data is extracted and the `P:\Mods` Workshop link exists. |
| `/dayz-workdrive` | It mounts P: after a reboot without opening DayZ Tools. |
| `/dayz-setup-objectbuilder` | It configures Object Builder on a new machine. |
| Mods | |
| `/dayz-new-mod` | It creates a mod with the standard folders and files. |
| `/dayz-import-mod` | It imports an existing mod folder or a GitHub repo into `workspace\`. |
| `/dayz-add-scaffold` | It adds missing standard pieces to an existing mod. |
| `/dayz-recipe` | It starts a plan from a template (new weapon, new vest or new craftable) for `dayz-mod-architect` to finish. |
| `/dayz-scope-mod` | It locks editing to one mod. `--clear` lifts the lock. |
| `/dayz-clean-workspace` | It removes the mods it created, along with their builds. |
| Build | |
| `/dayz-lint` | It finds errors that would stop a mod from loading, before packing. It runs first inside `/dayz-gate build` and `/dayz-build-pbo`. |
| `/dayz-build-pbo` | It packs a mod into a PBO with AddonBuilder. |
| `/dayz-deploy-pbo` | It copies prebuilt PBOs and keys into place without AddonBuilder. |
| Test | |
| `/dayz-add-server` | It creates a local test server instance. |
| `/dayz-launch-test` | It starts a DayZ Diag server and client with the given mods. |
| `/dayz-stop-test` | It stops the test session. It skips the environment check so that it works as an emergency stop. |
| `/dayz-cot-bootstrap` | It grants you admin rights in the server admin tools on the test server. |
| `/dayz-logwatch` | It watches the logs during a test session and triages each new error as it appears. |
| Gates and checks | |
| `/dayz-gate` | It runs the build, in-game, behavior and visual gates as scripts that print `PASS` or `FAIL`, with triage of known errors. `behavior` runs a test mission that spawns and uses each new item and reports on each feature. `visual` takes screenshots in game and compares them with stored baselines. |
| `/dayz-conflict-check` | It checks your mod for conflicts with the other mods loaded beside it, without extracting them. For packed mods (the usual Workshop install), it reads only the PBO headers. In that case, it compares prefixes, paths and script file names. It compares config and script classes only for unpacked mods. `--ingame` loads the mods together in a test session, where class clashes with packed mods show up. |
| `/dayz-upgrade-guard` | It takes a snapshot of vanilla before a DayZ update, then lists the mod classes whose vanilla parents changed. It can also rebuild the search index. |
| `/dayz-balance` | It compares item stats with similar vanilla items and flags outliers. |
| `/dayz-health` | It shows a page for each mod with the last build, the last test, open findings and the history of every gate run. |
| Routing and status | |
| `/dayz-route` | It prints which skill, specialist or team should handle a request (see "Token savers"). |
| `/dayz-statusline` | It installs a status line that shows P:, the active mod, DayZ Diag and the index age. |
| Art and UI | |
| `/dayz-pack-texture` | It converts images to `.paa` and checks their suffixes. |
| `/dayz-build-imageset` | It packs UI sprites into an imageset. |
| `/dayz-layout-preview` | It renders a `.layout` to PNGs at several screen sizes and flags widgets that fall off the screen. |
| `/dayz-p3d-audit` | It finds collision, physics and structure problems in models. |
| `/dayz-particles` | It is a reference for making particle effects without Workbench, and it has no script. |
| `/dayz-launch-objectbuilder` | It opens Object Builder on a model. |
| `/dayz-launch-workbench` | It opens Workbench on a mod's project. |
| Server economy | |
| `/dayz-edit-types` | It adds, changes, removes or merges `types.xml` entries. |
| `/dayz-split-types` | It splits one large `types.xml` into 19 category files. |
| Release | |
| `/dayz-release-pack` | It writes the Workshop description, a changelog entry, the classname list and install notes for server owners. |
| `/dayz-server-kit` | It zips the `types.xml` entries, the `cfgeconomycore` lines, the load order and the public `.bikey` for server owners. It never packs a `.biprivatekey`. |
| RAG search | |
| `/dayz-search-index` | It builds the index of game files. |
| `/dayz-search-download` | It installs a prebuilt index instead. |
| `/dayz-ask` | It answers a question in plain English about vanilla DayZ. |
| Team and repo | |
| `/dayz-record-correction` | It writes your correction into the right rule tier after you approve it. |
| `/sync-skills` | It links the skills into Claude Code, Codex CLI and Gemini CLI (clone only). |
| `/agentic-z-update` | It pulls template updates into a clone (clone only). |
| `/docs-sync` | It keeps the docs wiki in line with the source files (clone only). |
| `/clean-repo` | It runs a cleanup across every domain of the repo (clone only). |

The side panel is a separate plugin, not a skill. Install it with `/plugin install agentic-z-panel@dayz-n-chill`, then run `/dayz-panel`.
## File layout

Agentic-Z keeps your work in predictable places. This map shows your files and every location the skills write to, apart from the repo's own tool folders.

```
<repo>\
  workspace\<ModName>\           your mod source
  .server\<instance>\            local test server (mission, serverDZ.cfg, Profiles)
  .server\<instance>\Profiles\   server logs
  .server\<instance>-behavior\   copy of the instance the behavior gate runs in
  .server\!ClientDiagLogs\       client logs
  .server\!Health\<ModName>\     stored gate results and the /dayz-health page
  .claude\local-memory\          your author handle, active project, wizard state
  .claude\settings.local.json    local settings
  .claude\.upstream-baseline     written by /agentic-z-update
  .claude\.upstream-update.lock  written by /agentic-z-update
  output\<ModName>-plan\         the plan, behavior checks and the visual shots list
  output\<ModName>-visual\       visual gate screenshots per run, and the baselines
  output\<ModName>-release\      release pack texts and server kit zip
  output\layout-preview\         /dayz-layout-preview images
  output\evals\                  answer test results
  output\                        other one-off deliverables
~\.claude\dayz-search-index\     RAG search index
~\.claude\dayz-upgrade-guard\    vanilla snapshots for /dayz-upgrade-guard (about 10 MB each)
P:\
  <ModName>\                     link to workspace\<ModName>
  Mods\@<ModName>\Addons\        built PBO (Mods links to DayZ\!Workshop)
  dz\                            vanilla data you extracted once
  scripts\                       vanilla scripts, also read by the skills
```

A few skills also write outside these folders. `/dayz-setup-objectbuilder` saves Object Builder settings in the registry, and `/sync-skills` creates the skill links. `/dayz-record-correction` writes rule files only after you approve them. `/agentic-z-update` checks out updated template files into your clone and commits them.

## Configuration

Agentic-Z finds your installs on its own in most setups. Set the environment variables below only when a default location or behavior does not fit your machine.

| Variable | Purpose |
| --- | --- |
| `DAYZ_TOOLS_PATH` | The DayZ Tools install, which holds Bin\AddonBuilder. |
| `DAYZ_GAME_PATH` | The DayZ game install, which holds DayZ\_x64.exe and its !Workshop folder. |
| `DAYZ_DIAG_PATH` | The location of DayZDiag\_x64.exe, when it is not next to the game. |
| `DAYZ_VANILLA_DATA_PATH` | The extracted vanilla data, when it is not at P:\dz. |
| `DAYZ_WORK_DRIVE` | The work drive folder that /dayz-workdrive mounts as P:. |
| `DAYZ_SERVER_PATH` | The DayZ Server install, which /dayz-add-server uses. |
| `VOYAGE_API_KEY` | The key for RAG search. Set it in .env. |
| `VOYAGE_MODEL` | The Voyage embedding model for the index and searches. The default is voyage-code-3. |
| `VOYAGE_FREE_TIER_TOKENS` | Your Voyage token budget. Set it when your plan differs from the default that the indexer warns against. |
| `DAYZ_RAG_MAX_DISTANCE` | The default distance cutoff for search hits. It is unset by default. |
| `TYPESAFE_API_KEY` | The key that turns on Jev in /dayz-route. |

## Permissions and safety

Agentic-Z is built to work fast without putting your machine or your other mods at risk. Here is exactly what it can and cannot do.

- Shipped permissions apply to a clone only. `.claude/settings.json` allows the repo's own skills and scripts, plus `npm install` and `npm ci` from the lockfile. It denies `python -c`, `python -m`, `node -e`, `node -p`, `npx`, and `npm install` or `npm i` with a package name. Other inline forms, such as `py -c`, are not on the allow list, so they ask for permission first. A plugin install does not get this file, because plugins cannot ship permissions.
- Every agent has an explicit tool list. The five gates (`dayz-mod-reviewer`, `dayz-layout-validator`, `dayz-build-checker`, `dayz-ingame-tester` and `dayz-mod-debugger`) have no Edit or Write tools. Four of them have Bash to run their checks. Only the debugger has no Bash.
- Network access is narrow and named. `agent-creator` has WebFetch, and `figma-node-normalizer` uses the remote Figma MCP tools. The 21 agents that use RAG search send query text to the hosted Voyage AI API through `search_dayz_source`. When `TYPESAFE_API_KEY` is set, `/dayz-route` sends the request text to `api.typesafe.ai` for Jev.
- The scope lock keeps you focused on one mod. `/dayz-scope-mod <ModName>` blocks edits to every other mod in `workspace\`. Start Claude Code from the project root when you use it. The `--clear` flag lifts the lock.
- Cleanup removes only what the toolkit made. Destructive steps ask first or need `--yes`.

## Troubleshooting

Most problems come from the environment, not your mod. Find the message you see, and the fix is one step away.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `[FAIL] P:\ is NOT mounted` | P: is not mounted. It does not survive a reboot. | Mount it in DayZ Tools, or run `/dayz-workdrive`. |
| `[WARN] DayZ Tools not detected` | DayZ Tools is not installed, or it is installed somewhere unusual. | Install it from Steam (Tools), or set `DAYZ_TOOLS_PATH`. |
| `[WARN] Vanilla DayZ data not detected on P:\` | You have not extracted the game data yet. | In DayZ Tools, run Extract Game Data. Do this once per Tools update. |
| `P:\Mods\` is missing, is a real folder, or is dangling. | Built PBOs must land in the Workshop folder. | Run `cmd /c mklink /J P:\Mods "<DayZ install>\!Workshop"`. |
| `Connection failed 0x00020005` | serverDZ.cfg is missing `allowFilePatching = 1;`. | Rerun `/dayz-add-server <instance>`. |
| "Mission script has no main function" | The server found no valid mission folder. | Run `/dayz-add-server <instance> --refresh-mission`. |
| `[FAIL] DayZDiag_x64.exe not found` | The DayZ install is incomplete. | Verify DayZ in Steam. Diag ships next to DayZ\_x64.exe. |
| `[FAIL] P:\<ModName> exists as a real folder, not a link`, or `is a link pointing at ...` | A folder, or a link to somewhere else, is already there. | Move it. If it is a stray link, run `cmd /c rmdir P:\<ModName>`. |
| `[FAIL] Mod '<ModName>' has no Addons folder at ...`, or `has no .pbo files in ...` | You launched the mod before you built it. | Run `/dayz-build-pbo <ModName>` first. |
| `[FAIL] P:\<ModName> junction is missing` | The P: link to your mod folder is gone. | Run `/dayz-add-scaffold <ModName> --piece junction`. |
| `ERROR` from `/dayz-gate` asking for `--deps` | The mod's config.cpp needs addons that are not part of vanilla DayZ. | Pass them, for example `/dayz-gate ingame <ModName> --deps CF`. |
| `FAIL` from `/dayz-lint` before a build | It found an error that would stop the mod from loading. | Fix the `file:line` it names. Each finding names its owner. |
| The mod does not load in game. | One of the setup pieces is wrong. | Run `/dayz-preflight`. Then check the junction, the CfgPatches entry, the PBO date and the server `script*.log`, and confirm that the client used `-mod=P:\Mods\@<ModName>`. |

## FAQ

| Question | Answer |
| --- | --- |
| Does it cost money? | Agentic-Z is free to use for DayZ mods (see `LICENSE`). You bring your own AI tool. See "Overview" for what each one supports. RAG search needs a Voyage AI key, so check Voyage pricing. The prebuilt index from `/dayz-search-download` skips the build cost (see "RAG search"). Searching still needs the key to embed your questions. |
| Which AI tools work? | Claude Code gets the full toolkit. Codex CLI and Gemini CLI get the skills and the rules files (`AGENTS.md` and `GEMINI.md`). `/sync-skills` links the skills into all three tools. The agents, the hooks and RAG search are Claude Code features. |
| Should I use the plugin or a clone? | Use the plugin to add Agentic-Z to an existing project. Its skills show as `/agentic-z:...`. Clone the repo to start a new mod project. Don't use both at once, or every skill loads twice. |
| Will it touch my other mods? | No. No skill writes to your other mods. Besides your mod, its P: link, its test server and its build folder, the skills write only the state listed in "File layout". `/dayz-scope-mod <ModName>` also blocks edits to every other mod in `workspace\`. |
| Does it publish to the Workshop? | No. Builds land in `P:\Mods\@<ModName>`, which the launcher loads. When you are ready to publish, use DayZ Tools Publisher. |
| Can I work on several mods? | Yes. Each mod lives in `workspace\<ModName>`. Select "Set up or switch to another mod" in the `/dayz-init` hub. |
| Where are the logs? | Server logs are in `.server\<instance>\Profiles\`. Client logs are in `.server\!ClientDiagLogs\`. |
| Does P: stay mounted? | No, it does not survive a reboot. Run `/dayz-workdrive` after you boot. |
| Do I need the DayZ Server? | Yes. You need it installed whenever you add a test server instance or refresh its mission. `/dayz-add-server` copies the mission template from the DayZ Server install each time it creates an instance, and again for `--refresh-mission`. |
| How do I update? | If you use the plugin, update through the Claude Code plugin marketplace. If you cloned the repo, run `/agentic-z-update`. |
| Is it safe to run? | Yes. See "Permissions and safety" for exactly what each part can touch. |
| Can I teach it my style? | Yes. Correct it once and run `/dayz-record-correction`. It saves the rule after you approve it. |

## Support and contributing

Agentic-Z grows with the modders who use it. Join the Discord at `discord.gg/dayznchill` to ask questions and share what you build. The repo is at `github.com/DayZ-n-Chill/Agentic-Z`. To contribute, branch from `develop` with a `feature/`, `fix/` or `docs/` prefix, and open the pull request against `develop`.

Agentic-Z is made by DayZ n' Chill.
