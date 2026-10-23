Agentic-Z Guide

# Agentic-Z Guide

This guide explains how to install, set up and use Agentic-Z, the AI agent stack for DayZ modding. Agentic-Z includes 30 agents, 44 skills and three hooks.

## Contents

- [What Agentic-Z is](#what-agentic-z-is)
    - [What it includes](#what-it-includes)
    - [Which AI tools it works with](#which-ai-tools-it-works-with)
    - [How it fits together](#how-it-fits-together)
- [Before you start](#before-you-start)
    - [What you need](#what-you-need)
    - [Optional extras](#optional-extras)
- [Install and first setup](#install-and-first-setup)
    - [Option A: clone as a template](#option-a-clone-as-a-template)
    - [Option B: install as a Claude Code plugin](#option-b-install-as-a-claude-code-plugin)
    - [Run the setup wizard](#run-the-setup-wizard)
- [Your daily loop](#your-daily-loop)
- [Agents](#agents)
    - [All agents](#all-agents)
- [The mod team](#the-mod-team)
    - [Team structure](#team-structure)
    - [Starting the team](#starting-the-team)
    - [How the team checks work](#how-the-team-checks-work)
- [RAG search](#rag-search)
- [The three tiers of rules](#the-three-tiers-of-rules)
    - [Token savers](#token-savers)
    - [Each specialist in detail](#each-specialist-in-detail)
    - [How each specialist works](#how-each-specialist-works)
    - [How every specialist's knowledge is checked](#how-every-specialists-knowledge-is-checked)
    - [Paste it in](#paste-it-in)
- [Add-ons (planned)](#add-ons-planned)
- [How the grading works](#how-the-grading-works)
    - [The final count](#the-final-count)
    - [Who grades](#who-grades)
    - [What they grade against](#what-they-grade-against)
    - [The rubric for agents and skills](#the-rubric-for-agents-and-skills)
    - [The rubric for everything else](#the-rubric-for-everything-else)
    - [The scale](#the-scale)
    - [Run it yourself](#run-it-yourself)
    - [Quality by version](#quality-by-version)
    - [Every skill](#every-skill)
- [Where everything lives](#where-everything-lives)
    - [Folders](#folders)
    - [Settings you might need](#settings-you-might-need)
- [Safety](#safety)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Getting help and contributing](#getting-help-and-contributing)

## What Agentic-Z is

Agentic-Z turns Claude Code, Codex CLI and Gemini CLI into a DayZ modding partner. It provides specialist agents for DayZ, slash commands that run DayZ Tools for you, house rules that keep mods clean, and a search over the vanilla game files. With that search, the AI looks up facts instead of guessing.

> [!NOTE]
> Codex CLI and Gemini CLI get the skills and the rules files (see [Which AI tools it works with](#which-ai-tools-it-works-with)).

### What it includes

:::includes

### Which AI tools it works with

| AI tool | What it gets |
| --- | --- |
| Claude Code | Everything |
| Codex CLI | Skills and rules files |
| Gemini CLI | Skills and rules files |

The agents, the hooks and RAG search work only in Claude Code. Codex CLI and Gemini CLI get the skills, which `/sync-skills` links into all three tools, and the rules files, which are `AGENTS.md` and `GEMINI.md`.

### How it fits together

You work with your AI tool. Agentic-Z gives that tool rules, agents, skills and a search server. Together, these act on your mod folder, the P: drive, DayZ Tools and the game.

![How Agentic-Z fits together](images/guide-01-1.svg)

## Before you start

### What you need

:::requirements

### Optional extras

The core runs on DayZ Tools, the vanilla game files, Python and Claude Code. Some features need more:

- RAG search needs a Voyage AI key. Install its Python packages with `pip install -r .claude\mcp\dayz-rag\requirements.txt`. To build the index, also install `.claude\skills\dayz-search-index\requirements.txt`. Then add `VOYAGE_API_KEY=pa-...` to `.env` at the repository root.
- The Figma pipeline needs a Figma MCP server.
- `/dayz-p3d-audit` needs py3d.
- `/dayz-build-imageset`, `/dayz-layout-preview` and `/dayz-gate visual` need Pillow.
- `/dayz-cot-bootstrap` needs the CF and COT mods.

## Install and first setup

![Setup steps](images/guide-01-2.svg)

Choose one installation option only. If you install both the clone and the plugin, every skill loads twice.

### Option A: clone as a template

Use this option to start a new mod project.

```
git clone https://github.com/DayZ-n-Chill/Agentic-Z.git my-dayz-mod
cd my-dayz-mod
python .claude\skills\sync-skills\sync.py
```

### Option B: install as a Claude Code plugin

Use this option to add Agentic-Z to an existing project.

```
/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill
```

Plugin skills appear with an `agentic-z:` prefix, for example `/agentic-z:dayz-build-pbo`.

### Run the setup wizard

```
/dayz-init
```

The wizard asks whether you are starting a new mod or importing one, the mod name, which map to test on, and whether to build and launch. It fixes what it can, such as mounting P: and creating the `P:\Mods` link, and explains how to fix the rest. On every later run, it shows a status hub for your active mod.

## Your daily loop

![Daily loop](images/guide-01-3.svg)

1. Ask an agent for the change, for example "add a hidden selection for the camo".
2. Run `/dayz-build-pbo <ModName>` to pack the mod into `P:\Mods\@<ModName>\Addons\`.
3. Run `/dayz-launch-test <ModName> --server <instance>` to start a diag server and client with your mod loaded.
4. Check the logs, or hand them to `dayz-mod-debugger`.
5. Run `/dayz-stop-test` to close DayZ. Fix any problems and repeat.

## Agents

Describe what you want, and Claude picks the right specialist. You can also name an agent directly, for example "use the dayz-config-specialist to...".

Agentic-Z has 30 agents. "New" marks an agent added since version 1.6.0.

### All agents

| Agent | What it does | Example request | Since 1.6.0 |
| --- | --- | --- | --- |
| **Plan** | | | |
| **Mod orchestrator** `dayz-orchestrator` | Plans the mod with the user, splits it into small tasks, assigns them to leads, runs the gates and tracks completed work. | See [The mod team](#the-mod-team). | New |
| **Mod architect** `dayz-mod-architect` | Plans the classes, files, assets and behavior checks before work starts. | Started by the orchestrator. | New |
| **Lead (one agent, six teams)** `dayz-lead` | Runs one team: script, config, art, UI, server or release. Splits its share of the work into worker tasks and checks that the results fit together. | Started by the orchestrator. | New |
| **Workers** | | | |
| **Script engineer** `dayz-script-specialist` | Writes Enforce Script: modded classes, RPCs and game logic. | "Make my medkit heal over 30 seconds." | Kept |
| **Workbench plugins** `dayz-workbench-specialist` | Builds tools inside Enfusion Workbench. | "A plugin that checks texture suffixes." | Kept |
| **Config engineer** `dayz-config-specialist` | Writes config.cpp, class inheritance and hidden selections. | "Write the CfgVehicles entry for my vest." | Kept |
| **Object Builder** `dayz-object-builder` | Sets up .p3d models, LODs, selections and doors. | "Set up hidden selections on my vest model." | Kept |
| **Textures and materials** `dayz-asset-specialist` | Handles .paa textures and .rvmat materials. | "Pack vest\_camo\_co.png and make an rvmat." | Kept |
| **UI engineer** `dayz-ui-specialist` | Builds .layout files and the scripts that drive them. | "Add a compass to the HUD." | Kept |
| **Figma cleaner** `figma-node-normalizer` | Prepares a Figma frame for conversion. | "Turn this Figma frame into a DayZ menu." | Kept |
| **Figma to layout** `figma-to-dayz-layout` | Converts the prepared frame into a DayZ .layout, and repairs a layout that failed validation. | "Turn this Figma frame into a DayZ menu." | Kept |
| **Server admin** `dayz-server-admin` | Manages types.xml, init.c and server settings. | "Make my vest spawn rarely in military zones." | Kept |
| **Map builder** `dayz-map-specialist` | Handles Terrain Builder and DayZ Editor work. | "Export my base from DayZ Editor to Terrain Builder." | Kept |
| **Build engineer** `dayz-build-engineer` | Runs the build, test server and launch skills (Haiku). | "Build MyVest and start a test on chernarus." | New |
| **Docs writer** `dayz-docs-writer` | Keeps the mod's README, changelog and classname list up to date (Sonnet). | "Update the MyVest docs." | New |
| **Specialists** | | | |
| **Saving data** `dayz-persistence-specialist` | Saving data across restarts, save versions, base building, and a data audit before release. Works under the script lead; for the data audit, works under the server lead. | "Make my safe keep its code and contents after a restart." | New |
| **AI** `dayz-ai-specialist` | Infected, animals and human AI such as patrols and guards, written from scratch. Works under the script lead. | "Add guards that patrol my base and react to gunfire." | New |
| **Vehicles** `dayz-vehicle-specialist` | Cars, boats and helicopters: engine, gearbox, wheels, doors, fluids, seats and damage. Works under the config lead. | "Add a four door pickup with a bigger fuel tank." | New |
| **Weapons** `dayz-weapon-specialist` | Weapons, magazines, ammunition, attachments, recoil and fire modes. Works under the config lead. | "Add a hunting rifle that takes a five round magazine." | New |
| **Wearables** `dayz-wearables-specialist` | Clothing, characters, inventory slots, protection, color variants and proxies. Works under the art lead. | "Make a plate carrier in three colors." | New |
| **Animation** `dayz-animation-specialist` | model.cfg animations, RTM files and the handoff to Blender. Works under the art lead. | "Make my bunker doors open and close." | New |
| **Audio and FX** `dayz-audio-fx-specialist` | Sound shaders, sound sets and particle effects. Works under any lead that needs it. | "Give my generator a running sound and exhaust smoke." | New |
| **Physics** `dayz-physics-specialist` | Weight, collision LODs, dropping, throwing and contact. Diagnoses problems and hands the fix to the owner, and never edits files. Works under any lead. | "My crate falls through the floor. Fix it." | New |
| **Support** | | | |
| **Router** `dayz-router` | Low-cost Haiku agent behind `/dayz-route`. | Used by `/dayz-route`. | New |
| **Agent creator** `agent-creator` | Writes new agent files and checks them against the agent standard. | "Create an agent that reviews RPC security." | Kept |
| **Gatekeepers (read only)** | | | |
| **Mod reviewer** `dayz-mod-reviewer` | Checks the mod against the DayZ conventions and returns PASS or FAIL. | "Review workspace/MyVest before I build." | Kept |
| **Layout validator** `dayz-layout-validator` | Checks a `.layout` against the Figma-to-DayZ rules without editing it. It serves as the UI gate. | "Turn this Figma frame into a DayZ menu." | Kept |
| **Build checker and in-game tester** `dayz-build-checker` `dayz-ingame-tester` | Act as fallbacks when `/dayz-gate build` or `/dayz-gate ingame` itself fails. | Started by the orchestrator. | New |
| **Debugger** `dayz-mod-debugger` | Reads the logs for errors that triage does not recognize, and names the cause and the owner. | "My server crashes on start, here is the RPT." | Moved |

## The mod team

### Team structure

- You
- Planning
- Team leads
- Workers (one per task)
- Gatekeepers
- Playbook and reference files

![Diagram](images/guide-01-4.svg)

### Starting the team

To start the team after a plugin install, run `claude --agent agentic-z:dayz-orchestrator`. In a clone, run `claude --agent dayz-orchestrator`.

The orchestrator plans the mod with you and waits for your approval. It then runs the work in waves.

### How the team checks work

Checks happen at two levels. The leads run the mod review and the layout check on each task. The orchestrator runs the gates once per wave, one at a time, because there is only one mod folder and one test session. Workers run at the same time only when their tasks touch different files.

Each wave goes through these gates:

| Gate | What it does |
| --- | --- |
| Build check (`/dayz-gate build`) | Runs `/dayz-lint` first, then builds the mod and reports PASS or FAIL. |
| In-game test (`/dayz-gate ingame`) | Loads the mod in game, checks that the logs are clean and reports PASS or FAIL. |
| Behavior test (`/dayz-gate behavior`) | Runs only when `output\<ModName>-plan\behavior-checks.json` exists. A scripted test mission spawns and uses each new item and reports PASS or FAIL for each feature. |
| Visual check (`/dayz-gate visual`) | Takes screenshots during the in-game test and compares them with stored baselines. |

Nothing reaches you until the mod builds, loads in game with clean logs and, when the plan lists behavior checks, passes the behavior test.

The behavior and visual gates have been tested only with fixtures. They have not yet run in a live DayZ session.

![One wave of work](images/guide-01-5.svg)

## RAG search

![RAG search pipeline](images/guide-01-6.svg)

| Tool | What it does |
| --- | --- |
| `search_dayz_source` | Searches vanilla scripts, configs, layouts and materials by meaning. |
| `get_dayz_file` | Opens an exact file and line range on P:. |
| `list_indexed_sources` | Shows what is indexed and when. |

Agents use Grep first when they know an exact class or symbol name. They use RAG search for questions by meaning. A search hit is only a lead until the agent opens the real file, so every answer includes `path:line` references you can check.

## The three tiers of rules

When two tiers disagree, the more specific tier wins. No tier repeats another.

| Tier | What it holds | When it loads |
| --- | --- | --- |
| 1 · Repo rules | How every agent works: communication, tooling, memory and routing. Defined in `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`. | For every agent and every task |
| 2 · DayZ rules | Enforce Script style, config and asset rules, the environment, and vanilla search. Defined in `dayz-conventions.md` plus topic files for config, assets, scripts, UI and server. | For all DayZ work |
| 3 · Agents and reference files | The 30 agents, the 44 skills, and the reference files under `.claude/skills/_shared/`. | Only when the task needs them |

### Token savers

These features move mechanical work out of the AI. The AI then spends tokens only on work that needs judgment: planning, writing code and configs, review and real diagnosis.

![Router](images/guide-01-8.svg)

| Feature | What it does | How to use it |
| --- | --- | --- |
| Script-only checks | Run the build and in-game checks with no AI involved, which saves tokens. | `/dayz-gate build <ModName>`, `/dayz-gate ingame <ModName>` |
| Log triage | Matches failures against 52 known errors, each with its fix and owner. Only new errors go to the debugger. | Runs inside `/dayz-gate`. Use `triage.py --learn` to add your own. |
| Router | Decides who handles a request: keyword rules first, then Jev, then a low-cost Haiku router. | `/dayz-route "<request>"` (the AI runs it first) |
| Edit hooks | Check `config.cpp` and `.layout` syntax after every edit, and block edits to other mods while a scope is set. | Automatic with the plugin or a clone. |
| Paste-in router | Reads what you paste and starts the matching workflow. | Automatic. See [Paste it in](#paste-it-in). |
| Status line | Shows the state of P:, the active mod, whether DayZ Diag is running and the age of the search index. | Run `/dayz-statusline` once per project. |
| Lower-cost models | The build engineer and the router run on Haiku. The docs writer runs on Sonnet. | Automatic. |
| Smaller rules | The DayZ rules file is split into a 143-line core and five topic files of 24 to 56 lines. Most skills read only the core, which is 40% less than the old 239-line file. `/dayz-deploy-pbo` and `/dayz-gate` also read the bundle mods section of the config topic file. Each agent reads the core plus the topic files its job needs. With one topic file, an agent reads 17% to 30% less than before. With two, the result depends on which two. The mod debugger (226 lines) and the mod architect (231 lines) still read slightly less. The vehicle, weapon, and audio and effects specialists (251 lines) read more, as does the mod reviewer, which reads three topic files (283 lines). | Automatic. |
| No-token wrappers | Provide a `.bat` file for every runnable skill, so you can run it yourself with no AI involved. | See `scripts\README.md`. |
| Shorter descriptions | Every skill and agent description loads into every session. The descriptions were shortened to save about 2,100 tokens. | Automatic. |
### Each specialist in detail

In addition to the specialists for scripts, configs, art, UI, maps and servers, Agentic-Z includes specialists for saved data, vehicles, weapons, wearables, animation, audio, physics and AI. Each one works under a team lead and has its own reference pack. Every pack is checked against the vanilla game files, and a specialist loads its pack only when a task needs it. For the checks that run before a mod is packed, see [How the team checks work](#how-the-team-checks-work).

![Where the new specialists join the team](images/guide-02-1.svg)

| `dayz-persistence-specialist` | Details |
| --- | --- |
| What it does | Makes modded items and systems keep their data across server restarts. It writes the save and load code (OnStoreSave and OnStoreLoad) and stamps every save with a version number. It also writes the upgrade path, so old saves still load after the mod changes. It covers base building parts that must survive restarts. Before release, it runs a data audit that confirms every saved field is written and read back in the same order. |
| Example request | "Make my safe keep its code and contents after a restart, and do not break saves from the last version." |
| Works under | Script lead (the release audit goes to the server lead) |
| Hands back | Save and load code with a version number, a migration note for old saves, and an audit report for the server lead. |

| `dayz-vehicle-specialist` | Details |
| --- | --- |
| What it does | Builds cars, boats and helicopters. It sets up the vehicle class and its simulation (engine, gearbox, axles and wheels). It also sets up the parts that attach to the vehicle (doors, hood, trunk, wheels, battery and spark plug), its fluids (fuel, oil, coolant and brake fluid), its seats and crew positions, and how it takes damage. Vanilla DayZ ships native helicopter base classes (Helicopter, HelicopterAuto and HelicopterScript) but no flyable helicopter. The specialist builds flyable helicopters on those classes with your own code and never copies code from another mod. |
| Example request | "Add a four door pickup with its own doors and a bigger fuel tank." |
| Works under | Config lead |
| Hands back | CfgVehicles entries, the CarScript, BoatScript or HelicopterScript class, attachment slots, and a types.xml entry for the server lead. |

| `dayz-weapon-specialist` | Details |
| --- | --- |
| What it does | Builds firearms and everything that goes with them: the weapon class, magazines, ammunition, attachment slots for optics, suppressors, stocks and handguards, recoil, fire modes and muzzle effects. It inherits from the closest vanilla weapon, so reloading, jamming and damage behave as they do in the base game. |
| Example request | "Add a scoped hunting rifle that takes a five round magazine and the vanilla long range optics." |
| Works under | Config lead |
| Hands back | CfgWeapons, CfgMagazines and CfgAmmo entries, a recoil class, and a list of the model selections that the art lead must provide. |

| `dayz-wearables-specialist` | Details |
| --- | --- |
| What it does | Builds clothing, gear and characters. It sets which inventory slot an item uses, how many slots it holds, and its protection and insulation. It sets the hidden selections that let one model carry several textures, and it defines how the item appears on the character through proxies. It also covers new survivor characters. |
| Example request | "Make a plate carrier with three colors that fits the vest slot and holds six items." |
| Works under | Art lead |
| Hands back | Config entries, hidden selection names, texture slots for each color, and proxy notes for the Object Builder specialist. |

| `dayz-animation-specialist` | Details |
| --- | --- |
| What it does | Makes objects move: doors, lids, hatches, triggers and other moving parts. It writes the skeletonBones for the moving parts and the class Animations block in model.cfg (rotations, movements and hidden parts). The Object Builder specialist maintains the rest of model.cfg. It handles .rtm animation files. For models built in Blender, it writes the handoff so that bones and selections line up when the model reaches Object Builder. |
| Example request | "Make the doors on my bunker open and close when a player uses them." |
| Works under | Art lead |
| Hands back | The skeletonBones and class Animations entries for model.cfg, the selection and bone names that the model needs, and the script hook that plays the animation, which the script specialist writes. |

| `dayz-audio-fx-specialist` | Details |
| --- | --- |
| What it does | Handles sound and visual effects: sound shaders and sound sets, how loud a sound is and how far it carries, and particle effects such as smoke, sparks and muzzle flashes. It uses the /dayz-particles skill for particle files. |
| Example request | "Give my generator a running sound that fades with distance and a puff of exhaust smoke." |
| Works under | Any lead that needs it |
| Hands back | CfgSoundShaders and CfgSoundSets entries, particle files, and the script lines that play them. |

| `dayz-physics-specialist` | Details |
| --- | --- |
| What it does | Makes objects behave physically. It sets their weight and their collision shapes in the Geometry and Fire Geometry LODs. It also controls how objects land when dropped or thrown and how they push against players and vehicles. It catches common faults, such as items that fall through floors or bullets that pass through walls. |
| Example request | "My crate falls through the floor when I drop it. Fix it." |
| Works under | Any lead that needs it |
| Hands back | Geometry and mass fixes for the Object Builder specialist, and config lines for the worker who owns the class's config. |

| `dayz-ai-specialist` | Details |
| --- | --- |
| What it does | Builds behavior for computer controlled characters: infected, animals and human AI such as patrols and guards. It studies how other modders build these behaviors to learn the patterns, and then writes your own version. It copies nothing from another mod. |
| Example request | "Add a patrol of guards that walk a route around my military base and react to gunfire." |
| Works under | Script lead |
| Hands back | Script classes for the behavior, the config that the server lead needs to spawn the characters, and notes on server performance. |

### How each specialist works

Each specialist follows its own steps inside the team workflow described in [The mod team](#the-mod-team). The specialists that write DayZ content look up the vanilla files first, using the method in [RAG search](#rag-search). The build engineer, docs writer, build checker, in-game tester and Figma cleaner have no RAG tool. They work from the mod, its logs or the Figma file.

| Specialist | Steps |
| --- | --- |
| **Script lead** | |
| `dayz-script-specialist` | 1. Searches the vanilla scripts for the class it will change and reads the real file. 2. Writes a `modded class` in the correct layer (3\_Game, 4\_World or 5\_Mission) and calls `super`. 3. Adds RPCs only where the client and server must communicate, and confirms which side runs each line. 4. `/dayz-lint` and the build gate check and pack the mod (nothing compiles Enforce Script at this stage). The in-game gate catches compile errors and reads script.log. |
| `dayz-workbench-specialist` | 1. Reads how vanilla Workbench plugins are registered. 2. Writes the plugin script using only the classes, methods and attributes it found there, and cites each one as `path:line`. 3. Never opens Workbench itself. Instead, it tells you to open Workbench with `/dayz-launch-workbench --mod <ModName>`. 4. Returns the plugin and the steps to load and run it. |
| `dayz-persistence-specialist` | 1. Lists every value that must survive a restart. 2. Writes OnStoreSave and OnStoreLoad. 3. Adds the upgrade path for old saves. 4. Runs the data audit. 5. Places the audit at the end of its report to the script lead. The orchestrator passes the audit to the server lead before the test build. |
| `dayz-ai-specialist` | 1. Studies how vanilla infected and animals decide what to do. 2. Writes the behavior as its own script classes. 3. Gives the server lead the spawn setup. 4. The in-game test checks the behavior and server performance. |
| **Config lead** | |
| `dayz-config-specialist` | 1. Finds the closest vanilla parent class and reads its definition on disk, cited as `path:line`. 2. Writes CfgPatches with the correct requiredAddons, and then the class itself. 3. Matches hiddenSelections to the names in the model. 4. `/dayz-lint` and the build gate confirm that the mod loads. |
| `dayz-vehicle-specialist` | 1. Selects the closest vanilla vehicle as the parent. 2. Writes the vehicle class and its simulation. 3. Adds the attachment slots and the fluids. 4. Writes the CarScript, BoatScript or HelicopterScript class for seats, doors and damage. 5. Gives the server lead a types.xml entry. The behavior gate spawns the vehicle, and a person-run checklist covers driving. |
| `dayz-weapon-specialist` | 1. Selects the closest vanilla weapon as the parent. 2. Writes the weapon, magazine and ammo classes and the attachment slots. 3. Sets recoil and fire modes. 4. Lists the model selections and memory points that the art lead must provide. 5. The behavior gate spawns the weapon and fits each attachment. A person-run checklist covers firing and reloading. |
| **Art lead** | |
| `dayz-object-builder` | 1. Specifies the LODs (visual, geometry, fire geometry, view geometry and memory) as numbered Object Builder steps. You build them, because the specialist cannot edit a .p3d. 2. Names the selections and memory points that the config and animations need, and writes model.cfg. 3. Runs `/dayz-p3d-audit` after you save the model. 4. Sends the selection names and config lines, through the art lead, to the worker who owns the class's config. |
| `dayz-asset-specialist` | 1. Confirms that each texture has the correct suffix (\_co, \_nohq, \_smdi and the others). 2. Packs the textures with `/dayz-pack-texture`. 3. Writes the .rvmat for each material. 4. Writes a visual checklist for you to review in Object Builder or in game. It never launches either one. |
| `dayz-wearables-specialist` | 1. Selects the inventory slot and the closest vanilla item as the parent. 2. Sets the slots held, protection and insulation. 3. Sets hidden selections so that one model carries every color. 4. Records the proxy positions for the Object Builder specialist. 5. The behavior gate wears each color class, and a person checks in game how each color looks. |
| `dayz-animation-specialist` | 1. Lists the moving parts and their bones. 2. Writes its model.cfg entries (see [Each specialist in detail](#each-specialist-in-detail)). 3. Gives you the bone and selection names for your own Blender export. 4. Names the script hook that plays the animation. The script specialist writes that code, and the in-game test uses it. |
| **UI lead** | |
| `dayz-ui-specialist` | 1. Reads the vanilla layout closest to the new screen. 2. Writes the .layout and the script class that drives it. 3. Builds icons into an imageset with `/dayz-build-imageset`. 4. The layout checker checks the layout against the Figma-to-DayZ rules, and `/dayz-layout-preview` renders it. The in-game test opens it. |
| `figma-node-normalizer` | 1. Reads the Figma frame. 2. Cleans up layer names and structure so that they map to DayZ widgets. 3. Returns the clean tree as JSON to its caller and names the layout converter as the next stage. |
| `figma-to-dayz-layout` | 1. Converts the clean tree into a DayZ .layout. 2. Uses only widget types that the game supports. 3. Writes the file and names the layout checker as the next stage. |
| **Server lead** | |
| `dayz-server-admin` | 1. Writes types.xml entries with `/dayz-edit-types`. 2. Adds events, spawn points and gameplay settings where needed. 3. Splits large economy files with `/dayz-split-types`. 4. Sets up a missing test server instance with `/dayz-add-server`, which starts nothing. It gives you the `/dayz-launch-test` command instead of starting the server itself. |
| `dayz-map-specialist` | 1. Writes layers.cfg and the surface and clutter configs. If it needs your own layers.cfg and the file is missing, it stops and asks you for it. 2. Provides numbered steps for the DayZ Editor export and the Terrain Builder import and generation, which you carry out. 3. Returns the files and the steps to rebuild the map. |
| **Release lead** | |
| `dayz-build-engineer` | 1. Packs the mod with `/dayz-build-pbo`. 2. Starts the test session with `/dayz-launch-test`. 3. Reports the build result to the release lead, who passes it to the orchestrator. |
| `dayz-docs-writer` | 1. Reads what changed in the wave. 2. Updates the README, changelog and class name list. 3. Writes the Workshop text and server owner notes with `/dayz-release-pack`. |
| **Any lead** | |
| `dayz-audio-fx-specialist` | 1. Reads the vanilla sound or particle closest to the request. 2. Writes the sound shader and sound set, or writes the particle with `/dayz-particles`. 3. Adds the script line that plays it. 4. The in-game test checks how it sounds and looks. |
| `dayz-physics-specialist` | 1. Reads the model's geometry LODs and mass. 2. Identifies the fault: missing geometry, incorrect mass or faulty collision. 3. Hands the fix, through the lead that called it, to the Object Builder specialist or to the worker who owns the class's config. It never edits files. 4. A person-run in-game test drops, throws and shoots the object, which the behavior gate cannot do. |
| **Checks and fixes** | |
| `dayz-mod-reviewer` | 1. Reviews the finished task against the DayZ rules file. 2. Lists each problem with the specialist who owns it. 3. Never edits files. |
| `dayz-layout-validator` | 1. Checks the .layout against the Figma-to-DayZ rules: file format and widget classes. 2. Reports PASS or FAIL with each problem and its line number. It never edits files. |
| `dayz-build-checker` | 1. Runs only when `/dayz-gate build` itself fails. 2. Reads the AddonBuilder output and names the failing file. |
| `dayz-ingame-tester` | 1. Runs only when `/dayz-gate ingame` itself fails. 2. Reads the logs from the test session and reports what failed. |
| `dayz-mod-debugger` | 1. Receives new errors that triage does not recognize. 2. Traces script.log, RPT and crash files back to the line that failed. 3. Reports the cause, evidence, location and fix to its caller (the orchestrator or a lead), and names the worker agent that owns the fix. |

### How every specialist's knowledge is checked

![Cycle for every new specialist](images/guide-02-2.svg)

The existing specialists also have deeper coverage: a full Enforce Script reference, Dabs and widget UI coverage, a texture and material cookbook, model and LOD rules, animated doors, a short specification step in `/dayz-init` before building, and a layout preview at several screen sizes.
### Paste it in

Workflow skills are ready-made jobs for routine modding tasks. Each one runs as a script where possible and asks the AI only for decisions that need judgment. Each workflow skill is described in the [Every skill](#every-skill) table.

Agentic-Z also recognizes the following content when it is pasted into a session.

| Pasted content | Result |
| --- | --- |
| A crash log or RPT file | Triage matches it against known errors, names the cause and the fix, and passes any new error to the debugger. |
| A screenshot of a bug | The paste hook suggests a specialist: the UI specialist for a UI problem, the asset specialist for a texture or material problem, and the script specialist for an error message or incorrect behavior. For an error message shown on screen, the router agent sends the screenshot to the mod debugger (or to gate triage) instead, so the two can disagree in that case. |
| A Figma link | Runs the Figma pipeline and returns a checked `.layout` file. |
| A GitHub link | Suggests `/dayz-import-mod --source <link>`, which imports the mod into `workspace\` and can add any missing standard parts. |
| A Steam Workshop link | Refused, with the reason stated: Workshop content is packed, binarized and often protected. |
| A types.xml chunk | Checks the entries, lists any problems, and suggests `/dayz-edit-types --merge` to merge them. |

## Add-ons (planned)

An optional `agentic-z-addons` plugin for other tools, such as Blender, an AI 3D generator or another MCP server, is planned. No add-on ships yet, and the plugin marketplace lists only `agentic-z`. Each add-on will be a workflow that connects the outside tool at one point in the loop. Usually it will hand a finished model to the Object Builder specialist, so the standard gates can check it like any other work. For the optional dependencies of the core, see [Optional extras](#optional-extras).

Add-ons will follow these rules:

- **Optional:** the core never loads an add-on unless the user installs it.
- **Same gates:** everything an add-on produces goes through the mod review, the build check and the in-game test.
- **No reverse engineering:** no add-on unpacks protected mods or converts binarized models back into editable ones.

## How the grading works

The author does not set the grades. Separate AI reviewers grade every agent, skill and shared file against Anthropic's published best practices for Claude Code. The reviewers are Claude instances started fresh for the job. They see the files, the rubric and the standards, but never the earlier grades or the author's opinion. This is not an official Anthropic rating. It is a repeatable review that anyone can run again with the prompts below.

Answer tests (evals) check 23 of the 30 agents, and a change may only keep or raise a score. Claude Code handles prompt caching on its own, so Agentic-Z has no rule or test of its own for it.

### The final count

The final grades cover 163 items. All 163 are at A+: 30 of the 30 agents, 44 of the 44 skills and 89 of the 89 shared items. The shared items are the hooks, the search server, scripts and wrappers, answer tests, rules files, the shared reference packs and this method note.

The final review graded every item. Fresh graders then regraded items after each fix round. Each item shows its latest grade. The grades come from `final_grades.json` and `final_grades_shared.json`. The `clean-repo` item was graded twice and counts once.

### Who grades

- **Independent reviewers:** each round starts new Claude reviewers with no memory of earlier rounds. The final review used six: two for the agents, three for the skills, and one for everything shared. The shared items are the hooks, the search server, the scripts and wrappers, the answer tests, the rules files, the shared reference packs and this note. A few shared files were not graded; they are listed under "Files not graded" in "Open items and decisions".
- **Read-only access:** reviewers cannot edit files. They read every file, run the tests where the session allows it, and check claims against the code and the vanilla DayZ files on the P: drive. The skill reviewer for `dayz-launch-objectbuilder`, `dayz-launch-workbench` and `dayz-search-download` could not run pytest for them, because its session denied it. The reviewer stated this in its reasons.
- **Separate fixers:** different agents fix the problems the reviewers find, and each fixer owns its own files. A fixer never grades its own work.
- **Regrading:** new reviewers grade again after every fix round. An item counts as A+ only when an independent reviewer gives it A+.

### What they grade against

- **Anthropic's standards:** the Claude Code subagent documentation (code.claude.com/docs/en/sub-agents), the Agent Skills best practices (docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices), the Claude Code hooks reference (code.claude.com/docs/en/hooks) and the plugins reference (code.claude.com/docs/en/plugins-reference). For the search server, the reviewers also use the Model Context Protocol tool guidance.
- **Agentic-Z's own rules:** `CLAUDE.md` (Tier 1), the DayZ rules file and its topic files (Tier 2), the agent standard in `agent-creator.md`, and `docs/prompt-conventions.md`.
- **The real game:** DayZ facts are checked against the vanilla files on P:. Examples include which file holds CfgSurfaces, which texture suffixes exist, and which widget classes can be the root of a layout. Six Enforce Script worked examples (01, 04, 05, 06, 08 and 09) are still marked as vendored and have not been checked on P:.

### The rubric for agents and skills

| Agents | Skills |
| --- | --- |
| **Description:** a precise contract, written in the third person, that states what the agent does and when to use it, with a realistic example and valid YAML. | **Frontmatter:** the name matches the folder, and the description states what the skill does and when to use it, in the third person and kept short. |
| **Tools:** only the tools the role needs, and every tool the instructions require. Read-only roles cannot edit. | **Instructions:** concise and accurate to the code, with every claim and sample output checked against the script, and a clear section on how to run it. |
| **Body:** Lean and specific. It points to shared rules instead of repeating them and uses rules written in capital letters sparingly. | **Script:** Readable, with clear error messages, a nonzero exit code on failure, no dead code and reuse of shared helpers. The environment check runs first where the rules require it. |
| **Correct and consistent:** Every path, skill, agent and tool it names exists and is used correctly. Nothing contradicts the rules or the team flow, and DayZ facts are verified. | **Tests:** Tests exist, cover the risky logic and pass. |
| **Handoffs:** It states what it returns and to whom. | **Safety:** Every destructive step is guarded by a backup, a dry run or a confirmation. |

### The rubric for everything else

The 90 shared items are neither agents nor skills, so the reviewer judges each kind of item against criteria suited to it.

| Kind of item | What the reviewer checks |
| --- | --- |
| Hooks | The output JSON is correct for the hook event, a bug in a hook never blocks the session, the plugin and clone wiring match, and tests pass the hook input through stdin. |
| Search server | Every tool carries read-only annotations, the tool descriptions are clear, errors are returned as `isError` results, and tests cover the tools. |
| Rules files | Every rule is true of the code, no rule repeats another tier, and every named path and skill exists. |
| Specialist reference files | Each game fact cites a P: file and line or is marked as unverified, the cited lines hold when opened on P:, and nothing contradicts the checked references. |
| Scripts, wrappers and repository tests | The tests run and pass, the documentation and help text match the code, and failures exit with a nonzero code and a clear message. |
| Answer tests (evals) | The cases test what the agent is for, the runner and baselines match, and a change can only keep or raise a score. Answer tests cover 23 of the 30 agents. |
| This method note | The note states the rubric for every kind of item and gives the grading prompts. Every count, source and claim in it matches the repository and the grade files. |

### The scale

| Grade | Meaning |
| --- | --- |
| A+ | Can ship unchanged as an example of best practice. The reviewer found nothing concrete to fix. |
| A, A- | Very good, with one or two concrete defects that a user could encounter. |
| B+ to B- | Works, but has real gaps, such as claims that do not match the code, missing tests or unclear handoffs. |
| C+ to D | Wrong or risky in ways that users will encounter, or built on an approach that cannot reach A. |

Every grade below A+ must name the concrete defect and the exact fix. Style preferences alone cannot lower a grade.

### Run it yourself

Anyone can repeat the review. Start a new Claude Code session in the repository and give it one of the following four prompts.

Use this prompt for agents:

```
Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every file in .claude/agents/*.md against
Anthropic's current Claude Code subagent standards and the repo's agent standard
in .claude/agents/agent-creator.md: precise third-person description with an
example; minimal tools that cover the body; lean body with references over
inlining; every path, skill, agent and DayZ fact correct and consistent with
CLAUDE.md, .claude/skills/_shared/dayz-conventions.md and the team flow; a Report
naming its recipient. Scale A+ to D. A+ means nothing concrete left to fix. For
anything lower, name a concrete defect a user would actually hit.
Output a table: Agent | Grade | Why | To reach A+.
```

Use this prompt for skills:

```
Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every skill in .claude/skills/*/ (SKILL.md, its
scripts and its tests) against Anthropic's Agent Skills best practices and the
repo's rules: name matches the folder; third-person description of what it does
and when to use it; instructions accurate to the script; readable script with
clear errors and non-zero exit on failure; preflight first where the rules
require; tests that cover the risky logic and pass; destructive steps guarded
by a backup, dry run or confirmation. Run py -m pytest -q on the skill's tests.
Scale A+ to D. A+ means nothing concrete left to fix. For anything lower, name a
concrete defect a user would actually hit.
Output a table: Skill | Grade | Why | To reach A+.
```

Use this prompt for everything else:

```
Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every hook in hooks/, the MCP server in
.claude/mcp/dayz-rag/, every wrapper
in scripts/, the answer tests in evals/, the rules files and every specialist
reference file under .claude/skills/_shared/. Hooks: correct output JSON for the event,
never block on their own bug, tests through stdin. MCP server: read-only
annotations, clear tool descriptions, errors returned as isError, tests.
Rules files: every rule true of
the code. Reference files: game facts cite a P: file and line or are marked
unverified, and the cited lines hold (open them on P:). Scripts and answer
tests: tests run, documentation matches the code. Run
py -m pytest -q .claude scripts/dev hooks. Scale A+ to D. A+ means nothing
concrete left to fix. For anything lower, name a concrete defect a user would
actually hit. Output a table: Item | Grade | Why | To reach A+.
```

Use this prompt for this method note:

```
Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade the "How the grading works" section of the
Agentic-Z agent team guide. Check that it states the rubric for every kind of
item graded (agents, skills, hooks, search server, rules files,
specialist reference files, scripts, answer tests and this note); that it gives the
grading prompt for every kind; and that every count matches final_grades.json
and final_grades_shared.json. Scale A+
to D. A+ means nothing concrete left to fix. For anything lower, name a
concrete defect a reader would actually hit.
Output a table: Item | Grade | Why | To reach A+.
```

Because each run uses a new reviewer, two runs can word their findings differently, and a stricter reviewer can find a new edge case. This is intended. The grading found real bugs, and each one was fixed and covered by a test.
### Quality by version

This table lists the grade of each agent, skill and shared item at three releases. Independent AI reviewers assigned every grade: at v1.6.0, after the v1.7.0 grading rounds, and for the final release. The final grades also cover the hooks, the search server, the scripts, the answer tests and every specialist reference folder. For the final totals, see "The final count".

![Agentic-Z versions and grades](images/guide-05-1.svg)

Two values in the table are not grades. "Not built" means that the item did not exist yet at that version. "n/a" means that the shared file was not graded at that version. The last column is the final grade, not a target.

| Item | v1.6.0 released | v1.7.0 agent team | v2.0.0 final |
| --- | --- | --- | --- |
| **Agents** | | | |
| `agent-creator` | A- | A+ | A+ |
| `dayz-ai-specialist` | not built | not built | A+ |
| `dayz-animation-specialist` | not built | not built | A+ |
| `dayz-asset-specialist` | C+ | A | A+ |
| `dayz-audio-fx-specialist` | not built | not built | A+ |
| `dayz-build-checker` | A | A | A+ |
| `dayz-build-engineer` | A- | A- | A+ |
| `dayz-config-specialist` | C+ | A+ | A+ |
| `dayz-docs-writer` | A- | A | A+ |
| `dayz-ingame-tester` | A | A | A+ |
| `dayz-layout-validator` | B- | A- | A+ |
| `dayz-lead` | A- | A+ | A+ |
| `dayz-map-specialist` | C+ | A+ | A+ |
| `dayz-mod-architect` | A- | A+ | A+ |
| `dayz-mod-debugger` | B- | A+ | A+ |
| `dayz-mod-reviewer` | B | A- | A+ |
| `dayz-object-builder` | B- | A- | A+ |
| `dayz-orchestrator` | A- | A | A+ |
| `dayz-persistence-specialist` | not built | not built | A+ |
| `dayz-physics-specialist` | not built | not built | A+ |
| `dayz-router` | not built | not built | A+ |
| `dayz-script-specialist` | B- | A+ | A+ |
| `dayz-server-admin` | C+ | A+ | A+ |
| `dayz-ui-specialist` | C | A+ | A+ |
| `dayz-vehicle-specialist` | not built | not built | A+ |
| `dayz-weapon-specialist` | not built | not built | A+ |
| `dayz-wearables-specialist` | not built | not built | A+ |
| `dayz-workbench-specialist` | C+ | A+ | A+ |
| `figma-node-normalizer` | B- | A | A+ |
| `figma-to-dayz-layout` | C+ | A+ | A+ |
| **Skills** | | | |
| `agentic-z-update` | B+ | B+ | A+ |
| `clean-repo` | B | A+ | A+ |
| `dayz-add-scaffold` | B+ | A- | A+ |
| `dayz-add-server` | B+ | B+ | A+ |
| `dayz-ask` | not built | not built | A+ |
| `dayz-balance` | not built | not built | A+ |
| `dayz-build-imageset` | B | A- | A+ |
| `dayz-build-pbo` | B | B | A+ |
| `dayz-clean-workspace` | B- | A | A+ |
| `dayz-conflict-check` | not built | not built | A+ |
| `dayz-cot-bootstrap` | B | A- | A+ |
| `dayz-deploy-pbo` | A- | A | A+ |
| `dayz-edit-types` | C+ | A- | A+ |
| `dayz-gate` | not built | not built | A+ |
| `dayz-health` | not built | not built | A+ |
| `dayz-import-mod` | B+ | A- | A+ |
| `dayz-init` | C | A- | A+ |
| `dayz-launch-objectbuilder` | A- | A | A+ |
| `dayz-launch-test` | B+ | B+ | A+ |
| `dayz-launch-workbench` | B+ | A+ | A+ |
| `dayz-layout-preview` | not built | not built | A+ |
| `dayz-lint` | not built | not built | A+ |
| `dayz-logwatch` | not built | not built | A+ |
| `dayz-new-mod` | B | A | A+ |
| `dayz-p3d-audit` | B | A- | A+ |
| `dayz-pack-texture` | B+ | B+ | A+ |
| `dayz-particles` | B+ | A+ | A+ |
| `dayz-preflight` | B | A+ | A+ |
| `dayz-recipe` | not built | not built | A+ |
| `dayz-record-correction` | A- | A- | A+ |
| `dayz-release-pack` | not built | not built | A+ |
| `dayz-route` | not built | not built | A+ |
| `dayz-scope-mod` | B | A+ | A+ |
| `dayz-search-download` | B- | A | A+ |
| `dayz-search-index` | C+ | A- | A+ |
| `dayz-server-kit` | not built | not built | A+ |
| `dayz-setup-objectbuilder` | B- | A | A+ |
| `dayz-split-types` | B | A+ | A+ |
| `dayz-statusline` | not built | not built | A+ |
| `dayz-stop-test` | A- | A+ | A+ |
| `dayz-upgrade-guard` | not built | not built | A+ |
| `dayz-workdrive` | B+ | A+ | A+ |
| `docs-sync` | B | A- | A+ |
| `sync-skills` | B+ | A+ | A+ |
| **Rules and shared files** | | | |
| `.claude/skills/_shared/dayz-conventions.md (Tier 2 core)` | not built | not built | A+ |
| `_shared/conventions/config.md` | not built | not built | A+ |
| `_shared/conventions/assets.md` | not built | not built | A+ |
| `_shared/conventions/scripts.md` | not built | not built | A+ |
| `_shared/conventions/server.md` | not built | not built | A+ |
| `_shared/conventions/ui.md` | not built | not built | A+ |
| `_shared/container-base.md` | not built | not built | A+ |
| `_shared/py3d-mlod-notes.md` | not built | not built | A+ |
| `_shared/skill_helpers.py + test_skill_helpers.py` | not built | not built | A+ |
| `_shared/enscript-style.md` | not built | not built | A+ |
| `_shared/answer-formatting.md` | not built | not built | A+ |
| Grading method note (the "How the grading works" section of this guide) | not built | not built | A+ |
| `.claude/skills/_shared/README.md (index of shared reference folders)` | not built | not built | A+ |
| `_shared/figma-to-dayz-rules.md` | not built | not built | A+ |
| **Specialist files** | | | |
| `_shared/ai (README + 5 files)` | not built | not built | A+ |
| `_shared/animation (README + 5 files)` | not built | not built | A+ |
| `_shared/models (README + 5 files)` | not built | not built | A+ |
| `_shared/physics (README + 4 files)` | not built | not built | A+ |
| `_shared/vehicles (README + 6 files)` | not built | not built | A+ |
| `_shared/weapons (README + 7 files)` | not built | not built | A+ |
| `_shared/wearables (README + 6 reference files)` | not built | not built | A+ |
| `_shared/audio-fx (README + 3 files)` | not built | not built | A+ |
| `_shared/textures (README + 4 files)` | not built | not built | A+ |
| `_shared/persistence (README + 4 files)` | not built | not built | A+ |
| **Enforce Script files** | | | |
| `enscript/patterns/scheduler.md` | not built | not built | A+ |
| `enscript/patterns/physics_items.md` | not built | not built | A+ |
| `enscript/references/api_entities_inventory.md, api_game.md, api_network.md, api_player.md, api_scheduling.md, language_compile.md, language_memory.md` | not built | not built | A+ |
| `enscript/examples/01_custom_item.c, 04_rpc_patterns.c, 05_mission_server.c, 06_json_config.c, 08_gui_menu.c, 09_scheduler_timer.c` | not built | not built | A+ |
| `enscript/patterns/netsync.md` | not built | not built | A+ |
| `enscript/patterns/json_config_migration.md` | not built | not built | A+ |
| `enscript/patterns/rpc.md` | not built | not built | A+ |
| `enscript/patterns/language_workarounds.md` | not built | not built | A+ |
| `enscript/integrations/central_economy.md` | not built | not built | A+ |
| `enscript/integrations/vanilla_plugins.md` | not built | not built | A+ |
| `enscript/integrations/input_bindings.md` | not built | not built | A+ |
| `enscript/integrations/community_framework.md` | not built | not built | A+ |
| `enscript/references/erpc_defines.md` | not built | not built | A+ |
| `enscript/references/file_paths.md` | not built | not built | A+ |
| `enscript/references/language_types.md` | not built | not built | A+ |
| `enscript/references/types_collections.md` | not built | not built | A+ |
| `enscript/references/widget_api.md` | not built | not built | A+ |
| `enscript/examples/07_agent_modifier.c` | not built | not built | A+ |
| `enscript/examples/12_menu_interactions.layout` | not built | not built | A+ |
| `enscript/patterns/persistence.md` | not built | not built | A+ |
| `enscript/integrations/dabs_framework.md` | not built | not built | A+ |
| `enscript/references/item_api.md` | not built | not built | A+ |
| `enscript/examples/11_hud_plain_text.layout` | not built | not built | A+ |
| `enscript/examples/13_item_preview.layout` | not built | not built | A+ |
| `enscript/README.md` | not built | not built | A+ |
| `enscript/patterns/modded_class.md` | not built | not built | A+ |
| `enscript/patterns/actions.md` | not built | not built | A+ |
| `enscript/patterns/singleton.md` | not built | not built | A+ |
| `enscript/references/gui_layout.md` | not built | not built | A+ |
| `enscript/examples/02_custom_action_singleuse.c` | not built | not built | A+ |
| `enscript/examples/03_continuous_action.c` | not built | not built | A+ |
| `enscript/examples/10_modded_playerbase.c` | not built | not built | A+ |
| **Hooks** | | | |
| `hooks/hooks.json` | not built | not built | A+ |
| `hooks/test_plugin_copy.py` | not built | not built | A+ |
| `hooks/edit_check.py (+ test_edit_check.py)` | not built | not built | A+ |
| `hooks/scope_guard.py (+ test_scope_guard.py)` | not built | not built | A+ |
| `hooks/paste_router.py (+ test_paste_router.py)` | not built | not built | A+ |
| `dayz-rag MCP server (server.py, voyage_common.py, README, tests)` | not built | not built | A+ |
| **Answer tests (evals)** | | | |
| `evals/baseline.json` | not built | not built | A+ |
| `evals/fixtures/dayz-layout-validator/*.layout` | not built | not built | A+ |
| `evals/questions/dayz-ai-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-animation-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-asset-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-audio-fx-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-config-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-layout-validator.json` | not built | not built | A+ |
| `evals/questions/dayz-mod-reviewer.json` | not built | not built | A+ |
| `evals/questions/dayz-object-builder.json` | not built | not built | A+ |
| `evals/questions/dayz-persistence-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-physics-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-script-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-vehicle-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-weapon-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-wearables-specialist.json` | not built | not built | A+ |
| `scripts/dev/test_run_evals.py` | not built | not built | A+ |
| `evals/README.md` | not built | not built | A+ |
| `scripts/dev/run_evals.py` | not built | not built | A+ |
| **Scripts and repo tests** | | | |
| `scripts/dev/evals.bat, clean-repo.bat, docs-sync.bat` | not built | not built | A+ |
| `scripts/setup/preflight.bat, workdrive.bat, setup-objectbuilder.bat, statusline.bat, sync-skills.bat` | not built | not built | A+ |
| `scripts/dayz/*.bat (the other 35 wrappers: add-scaffold, add-server, ask, balance, build-imageset, build-pbo, clean-workspace, conflict-check, cot-bootstrap, deploy-pbo, gate, health, import-mod, launch-test, layout-preview, lint, logwatch, new-mod, objectbuilder, p3d-audit, pack-texture, recipe, release-pack, route, scope-mod, search-download, search-index, server-kit, status, stop-test, triage, types-edit, types-split, upgrade-guard, workbench)` | not built | not built | A+ |
| `scripts/README.md` | not built | not built | A+ |
| `scripts/dayz/dayz-search.bat` | not built | not built | A+ |
| `scripts/setup/agentic-z-update.bat` | not built | not built | A+ |
| `scripts/dev/test_repo_integrity.py` | not built | not built | A+ |
| `scripts/dayz/dayz-search.py` | not built | not built | A+ |

## Where everything lives

These trees show every folder Agentic-Z uses, in three places: the repository, the P: drive and your user folder. Folders marked **local** are created on your PC as you work and are never committed to git.

### The repository

:::tree <repo>\
.claude-plugin\ | Plugin manifest for the Claude Code plugin install
  marketplace.json
  plugin.json
.claude\ | Agents, skills and the search server
  agents\ | The 30 agents, one .md file each
  mcp\ | MCP servers
    dayz-rag\ | The RAG search server (server.py)
  skills\ | The 44 skills, one folder each with its SKILL.md
    _shared\ | Reference packs shared by the agents, indexed in README.md
      conventions\ | The five DayZ rules topic files: assets, config, scripts, server, ui
      ai\ | Reference pack
      animation\ | Reference pack
      audio-fx\ | Reference pack
      enscript\ | Reference pack
      enscript-style\ | Enforce Script style, one file per section
      models\ | Reference pack
      persistence\ | Reference pack
      physics\ | Reference pack
      textures\ | Reference pack
      vehicles\ | Reference pack
      weapons\ | Reference pack
      wearables\ | Reference pack
      dayz-conventions.md | The DayZ rules core (Tier 2)
      README.md | Index of every reference pack
    <skill>\ | One folder per skill, for example dayz-gate\
      SKILL.md
  local-memory\ | Author handle, active project and wizard state | local
  .upstream-baseline | Written by /agentic-z-update | local
  .upstream-update.lock | Written by /agentic-z-update | local
  settings.json | Shared settings
  settings.local.json | Your local settings | local
.github\
  workflows\
    tests.yml | Runs the test suite on GitHub
.server\ | Local test servers | local
  <instance>\ | One test server: mission, serverDZ.cfg, and Profiles with the server logs
  <instance>-behavior\ | Copy of the instance that the behavior gate runs in
  !ClientDiagLogs\ | Client logs
  !Health\ | Stored gate results
    <ModName>\ | Gate results and the health page for /dayz-health
docs\ | Project docs and release notes
evals\ | Answer tests
  fixtures\ | Sample files the answer tests check against
  questions\ | One question file per agent
  baseline.json | The recorded score for each agent
hooks\ | The three edit hooks: edit check, paste router and scope guard
output\ | Everything the skills produce | local
  <ModName>-plan\ | The plan, the behavior checks and the visual shots list
  <ModName>-release\ | Release texts, release pack and server kit zip
  <ModName>-visual\ | Screenshots for each run, and the baselines to keep
  evals\ | Answer test results
  layout-preview\ | Layout preview images
scripts\ | A .bat file for every runnable skill, so you can run it with no AI
  dayz\ | Modding scripts
  dev\ | Repository tools and tests
  setup\ | Setup scripts
wiki\ | Source for the Agentic-Z docs website
workspace\ | Your mods | local
  <ModName>\ | Mod source
.env | Your API keys, such as VOYAGE_API_KEY | local
.env.example | Template for .env
.mcp.json | Registers the RAG search server
AGENTS.md | Repo rules for Codex CLI (Tier 1)
CLAUDE.md | Repo rules for Claude Code (Tier 1)
GEMINI.md | Repo rules for Gemini CLI (Tier 1)
README.md
:::

### The P: drive

:::tree P:\
dz\ | Vanilla game data, extracted once
Mods\ | Linked to DayZ\!Workshop
  @<ModName>\
    Addons\ | The built PBO
scripts\ | Vanilla scripts, also read by the skills
<ModName>\ | Link to <repo>\workspace\<ModName>
:::

### Your user folder

:::tree C:\Users\<you>\.claude\
dayz-search-index\ | The RAG search index
dayz-upgrade-guard\ | Vanilla snapshots for /dayz-upgrade-guard, about 10 MB each
:::

The skills also write to three places outside these folders:

- Object Builder settings in the Windows registry.
- The skill links that `/sync-skills` creates.
- Rule files, which `/dayz-record-correction` updates only after you approve the change.

### Settings you might need

| Variable | Purpose |
| --- | --- |
| `DAYZ_TOOLS_PATH` | Location of the DayZ Tools installation, which contains Bin\AddonBuilder. |
| `DAYZ_GAME_PATH` | Location of the DayZ game installation, which contains DayZ\_x64.exe and its !Workshop folder. |
| `DAYZ_DIAG_PATH` | Location of DayZDiag\_x64.exe, when it is not in the game folder. |
| `DAYZ_VANILLA_DATA_PATH` | Location of the extracted vanilla data, when it is not at P:\dz. |
| `DAYZ_WORK_DRIVE` | The work drive folder that /dayz-workdrive mounts as P:. |
| `DAYZ_SERVER_PATH` | Location of the DayZ Server installation, used by /dayz-add-server. |
| `VOYAGE_API_KEY` | The Voyage AI key for RAG search, stored in .env. |
| `VOYAGE_MODEL` | The Voyage embedding model for the index and for searches. The default is voyage-code-3. |
| `VOYAGE_FREE_TIER_TOKENS` | Your Voyage token budget, when your plan differs from the default budget that the indexer warns against. |
| `DAYZ_RAG_MAX_DISTANCE` | The default distance cutoff for search hits. It is not set by default. |
| `TYPESAFE_API_KEY` | Turns on Jev in /dayz-route. |

## Safety

- In a clone, the shipped `.claude/settings.json` allows the repository's own skills and scripts. It also allows plain `npm install` and `npm ci`, which install from the lockfile. It denies `python -c`, `python -m`, `node -e`, `node -p`, `npx`, and `npm install` or `npm i` with a package name. Other inline forms, such as `py -c`, are not on the allow list, so Claude Code asks you before it runs them. A plugin installation does not include this file, because plugins cannot ship permissions.
- Every agent has an explicit tool list. The five gate agents (mod reviewer, layout validator, build checker, in-game tester and debugger) have no Edit or Write tools. Four of them have Bash to run their checks; only the debugger has no Bash. Two agents have general web or remote design access: `agent-creator` has WebFetch, and `figma-node-normalizer` uses the remote Figma MCP tools. The 21 agents that use RAG search also send text off the machine, because `search_dayz_source` embeds each query through the hosted Voyage AI API.
- `/dayz-scope-mod <ModName>` blocks edits to every other mod in `workspace\`. Start Claude Code from the project root for the block to apply. `--clear` removes it.
- Cleanup removes only what the toolkit created. Destructive steps ask for confirmation first or require `--yes`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `[FAIL] P:\ is NOT mounted` | P: is not mounted. The mount does not survive a reboot. | Mount P: in DayZ Tools, or run `/dayz-workdrive`. |
| `[WARN] DayZ Tools not detected` | DayZ Tools is not installed, or it is installed in an unusual location. | Install DayZ Tools from Steam (under Tools), or set `DAYZ_TOOLS_PATH`. |
| `[WARN] Vanilla DayZ data not detected on P:\` | The game data has not been extracted. | In DayZ Tools, run Extract Game Data. Repeat this once after each Tools update. |
| `P:\Mods\` is missing, is a real folder, or is a broken link | Built PBOs must go to the Workshop folder. | Run `cmd /c mklink /J P:\Mods "<DayZ install>\!Workshop"`. |
| `Connection failed 0x00020005` | serverDZ.cfg does not contain `allowFilePatching = 1;`. | Run `/dayz-add-server <instance>` again. |
| "Mission script has no main function" | The server found no valid mission folder. | Run `/dayz-add-server <instance> --refresh-mission`. |
| `[FAIL] DayZDiag_x64.exe not found` | The DayZ installation is incomplete. | Verify the DayZ files in Steam. The Diag executable ships in the same folder as DayZ\_x64.exe. |
| `[FAIL] P:\<ModName> exists as a real folder, not a link`, or `is a link pointing at ...` | A folder, or a link to another location, already exists at that path. | Move the folder. If it is a stray link, remove it with `cmd /c rmdir P:\<ModName>`. |
| `[FAIL] Mod '<ModName>' has no Addons folder at ...`, or `has no .pbo files in ...` | The mod was launched before it was built. | Run `/dayz-build-pbo <ModName>` first. |
| `[FAIL] P:\<ModName> junction is missing` | The P: link to the mod folder no longer exists. | Run `/dayz-add-scaffold <ModName> --piece junction`. |
| `ERROR` from `/dayz-gate` that asks for `--deps` | The mod's config.cpp requires non-vanilla addons, such as CF. | Pass the addons to the gate, for example `/dayz-gate ingame <ModName> --deps CF`. |
| `FAIL` from `/dayz-lint` before a build | The linter found an error that would stop the mod from loading. | Fix the problem at the `file:line` location it reports. Each finding names the agent that owns the fix. |
| The mod does not load in the game | One of the setup steps is incorrect. | Run `/dayz-preflight`. Then check the junction, the CfgPatches entry, the PBO date and the server `script*.log`, and confirm that the client used `-mod=P:\Mods\@<ModName>`. |

## FAQ

| Question | Answer |
| --- | --- |
| Does it cost money? | Agentic-Z is free to use for DayZ mods (see LICENSE). You need your own AI tool. RAG search requires a Voyage AI key. The last full index build embedded about 66M tokens, and the current indexer creates more chunks, so check Voyage pricing. `/dayz-search-download` avoids the build by downloading a prebuilt index. That index is older than the current indexer, and searching still requires the key to embed your questions. |
| Which AI tools does it work with? | See "Which AI tools it works with" under "What Agentic-Z is". |
| Should I install the plugin or clone the repository? | See "Install and first setup". |
| Will it change my other mods? | No. Skills write only to your mod and to their own state, as listed in "Where everything lives". `/agentic-z-update` also checks out updated template files into your clone and commits them. |
| Does it publish to the Workshop? | No. Builds go to `P:\Mods\@<ModName>`, which the launcher loads. Publish with DayZ Tools Publisher. |
| Can I work on several mods? | Yes. Each mod has its own folder at `workspace\<ModName>`. To change mods, choose "Set up or switch to another mod" in the `/dayz-init` hub. |
| Where are the logs? | See the `.server` folders in "Where everything lives". |
| Does P: stay mounted? | No. See the first row of "Troubleshooting". |
| Do I need the DayZ Server? | Yes. It must be installed whenever you add a test server instance or refresh its mission. `/dayz-add-server` copies the mission template from the DayZ Server installation each time it creates an instance, and again for `--refresh-mission`. |
| How do I update? | For a plugin installation, update through the Claude Code plugin marketplace. For a clone, run `/agentic-z-update`. |
| Is it safe to run? | Yes. See "Safety". |
| Can I teach it my style? | Yes. Correct it once, then run `/dayz-record-correction`. The rule is saved after you approve it. |

## Getting help and contributing

For help, join the DayZ n' Chill Discord at `discord.gg/dayznchill`. The repository is at `github.com/DayZ-n-Chill/Agentic-Z`. To contribute, create a branch with a name that starts with `feature/`, `fix/`, `docs/` or `chore/`, and open a pull request.
