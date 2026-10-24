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
    - [Step 1: install the plugin](#step-1-install-the-plugin)
    - [Step 2: run the setup wizard](#step-2-run-the-setup-wizard)
    - [Step 3: your first steps](#step-3-your-first-steps)
    - [Optional: clone as a template](#optional-clone-as-a-template)
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
- [One source of truth](#one-source-of-truth)
- [Community mods and add-ons](#community-mods-and-add-ons)
- [How the grading works](#how-the-grading-works)
    - [The final count](#the-final-count)
    - [Who grades](#who-grades)
    - [What they grade against](#what-they-grade-against)
    - [The rubric for agents and skills](#the-rubric-for-agents-and-skills)
    - [The rubric for everything else](#the-rubric-for-everything-else)
    - [The scale](#the-scale)
    - [Run it yourself](#run-it-yourself)
    - [Quality by version](#quality-by-version)
    - [The skills](#the-skills)
- [Where everything lives](#where-everything-lives)
    - [Folders](#folders)
    - [Settings you might need](#settings-you-might-need)
- [Safety](#safety)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Getting help and contributing](#getting-help-and-contributing)

## What Agentic-Z is

Agentic-Z turns Claude Code, Codex CLI and Gemini CLI into a DayZ modding partner. It provides specialist agents for DayZ, slash commands that run DayZ Tools for you, house rules that keep mods clean, and a search over the vanilla game files. With that search, the AI looks up facts instead of guessing.

It's built for production-ready mods. Work goes through the same checks a careful team runs before a release: a code review, a layout check, a build check and an in-game test. Read-only gate agents run them, and the orchestrator runs the gates before it marks work as done.

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

> [!WARNING]
> AI can make mistakes, and the gates are AI too. They catch a lot, but review every change yourself and test your mod in game before you publish it.

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

Most people should install Agentic-Z as a Claude Code plugin. It's the recommended way: you get every agent, skill, hook and the search server in any project folder, without forking the repository.

### Step 1: install the plugin

Open Claude Code in your mod project folder and run:

```
/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill
```

The first command adds the DayZ n' Chill marketplace. The second installs Agentic-Z from it. The `dayz-rag` search server registers on its own.

Plugin skills appear with an `agentic-z:` prefix, for example `/agentic-z:dayz-build-pbo`.

### Step 2: run the setup wizard

From your mod project in Claude Code, run:

```
/dayz-init
```

The wizard asks whether you are starting a new mod or importing one, the mod name, which map to test on, and whether to build and launch. It fixes what it can, such as mounting P: and creating the `P:\Mods` link, and gives you the fix or a steam:// link for the rest. Its state is kept in `.claude/local-memory/` in your project.

### Step 3: your first steps

- Run `/dayz-init` again at any time. After the first run it shows a status hub for your active mod (PBO age, test servers, whether DayZ Diag is running, search status) and runs the next action you pick.
- To work on another mod, pick "Set up or switch to another mod" in the hub.
- To build a whole mod with the team, start the orchestrator as your main session: `claude --agent agentic-z:dayz-orchestrator`. See [The mod team](#the-mod-team).
- To run one step yourself, call a skill directly, such as `/agentic-z:dayz-preflight`, `/agentic-z:dayz-build-pbo` or `/agentic-z:dayz-launch-test`.
- To turn on RAG search, see [Optional extras](#optional-extras).

### Optional: clone as a template

This is not recommended for most people. Clone the repository only if you want your own full copy of Agentic-Z to change, or you want the skills in Codex CLI and Gemini CLI as well.

```
git clone https://github.com/DayZ-n-Chill/Agentic-Z.git my-dayz-mod
cd my-dayz-mod
python .claude\skills\sync-skills\sync.py
```

In a clone, skills appear without the prefix (`/dayz-build-pbo`), and you start the team with `claude --agent dayz-orchestrator`. Then run `/dayz-init` as in Step 2.

> [!WARNING]
> Use the plugin or a clone, not both. With both installed, every skill loads twice.

## Your daily loop

![Daily loop](images/guide-01-3.svg)

1. Ask an agent for the change, for example "add a hidden selection for the camo".
2. Run `/dayz-build-pbo <ModName>` to pack the mod into `P:\Mods\@<ModName>\Addons\`.
3. Run `/dayz-launch-test <ModName> --server <instance>` to start a diag server and client with your mod loaded.
4. Check the logs, or hand them to `dayz-mod-debugger`.
5. Run `/dayz-stop-test` to close DayZ. Fix any problems and repeat.

## Agents

Describe what you want, and Claude picks the right specialist. You can also name an agent directly, for example "use the dayz-config-specialist to...".

Agentic-Z has 30 agents. "New" marks an agent added since version 1.0.0.

### All agents

| Agent | What it does | Example request | Since 1.0.0 |
| --- | --- | --- | --- |
| **Plan** | | | |
| **Mod orchestrator** `dayz-orchestrator` | Plans the mod with the user and the architect, gets the user's approval of the task list, assigns tasks to leads in waves, runs the gates and tracks completed work. | See [The mod team](#the-mod-team). | New |
| **Mod architect** `dayz-mod-architect` | Plans the classes, files, assets and behavior checks, and splits the work into small tasks for each team, before work starts. | Started by the orchestrator. | New |
| **Lead (one agent, six teams)** `dayz-lead` | Runs one team: script, config, art, UI, server or release. Briefs a worker for each of its tasks, gates the results and checks that they fit together. | Started by the orchestrator. | New |
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
| **Saving data** `dayz-persistence-specialist` | Saving data across restarts, save versions, base building, and a data audit before release. Works under the script lead; its data audit report is passed on to the server lead. | "Make my safe keep its code and contents after a restart." | New |
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

Checks happen at two levels. The leads run the mod review on each task, and the layout check on each task that changes a `.layout`. Build tasks have no file check: they pass when the build engineer reports success and the PBO exists. The orchestrator runs the gates once per wave, one at a time, because there is only one mod folder and one test session. Workers run at the same time only when their tasks touch different files.

Each wave goes through these gates:

| Gate | What it does |
| --- | --- |
| Build check (`/dayz-gate build`) | Runs `/dayz-lint` first, then builds the mod and reports PASS or FAIL. |
| In-game test (`/dayz-gate ingame`) | Loads the mod in game, checks that the logs are clean and reports PASS or FAIL. |
| Behavior test (`/dayz-gate behavior`) | Runs only when `output\<ModName>-plan\behavior-checks.json` exists. A scripted test mission spawns and uses each new item and reports PASS or FAIL for each feature. |
| Visual check (`/dayz-gate visual`) | Takes screenshots during the in-game test and compares them with stored baselines. |

Nothing reaches you until the mod builds, loads in game with clean logs and, when the plan lists behavior checks, passes the behavior test.

All four gates have run in a live DayZ session. On October 24, 2026 a three-retexture plate carrier mod was built end to end: the build, in-game, behavior (10 checks) and visual gates each passed.

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

## One source of truth

Ask ten modders how to do something in DayZ and you can get ten answers. One tutorial says to do it this way, a forum post says another, and an old video uses a method that no longer works. Agentic-Z doesn't take anyone's word for it, including ours.

Every answer comes from the game itself. The vanilla scripts, configs, layouts and materials on your P: drive are the reference, and Bohemia's own tools build and test the mod. That's why the core is built on vanilla DayZ and leaves community mods out.

- **It reads the code:** before an agent writes anything, it searches the vanilla files and opens the real file. A search result is only a lead until the agent has read it.
- **It shows its work:** answers cite the file and line they came from, as `path:line`, so you can open it and check.
- **It builds on what's there:** new items inherit from the closest vanilla class, so they behave the way the base game does.
- **It proves it:** the gates check the result with a code review, a layout check, a build check and an in-game test before the work counts as done.

The result is code that matches how DayZ is actually built, not how someone remembers it.

## Community mods and add-ons

Agentic-Z is built on vanilla DayZ and Bohemia's own tools on purpose (see [One source of truth](#one-source-of-truth)). Every rule and reference pack is checked against the vanilla game files, and nothing in the core depends on a community mod. Community mods can still be added. This page covers using them in your mod, teaching Agentic-Z about a new one, and connecting an outside tool as an add-on.

### Using a community mod in your mod

List the mod's addons in `requiredAddons[]` in your mod's `config.cpp`, the same as without Agentic-Z. The agent doing the work then reads the matching reference pack, only for mods that use that community mod:

| Community mod | Reference pack |
| --- | --- |
| Community Framework (CF) | `.claude\skills\_shared\enscript\integrations\community_framework.md` |
| Dabs Framework | `.claude\skills\_shared\enscript\integrations\dabs_framework.md` |
| DayZ Expansion | `.claude\skills\_shared\enscript\integrations\expansion_style.md` |
| Your mod, or any other | Add a reference pack of your own. See [Teaching Agentic-Z a new community mod](#teaching-agentic-z-a-new-community-mod). |

Three tools also help when your mod sits next to community mods:

- `/dayz-conflict-check` looks for prefix, path and class collisions with the community mods your mod uses, such as CF, COT and Expansion.
- `/dayz-gate` loads the addons your mod needs on the test server. Pass them with `--deps`, for example `/dayz-gate ingame <ModName> --deps CF`.
- `/dayz-cot-bootstrap` gives you admin rights in Community Online Tools on your test server.

### Teaching Agentic-Z a new community mod

This works in a clone of the repository. A plugin install replaces its files on every update.

1. Write a reference pack for the mod at `.claude\skills\_shared\enscript\integrations\<mod>.md`. Start with a title and one line on what it covers.
2. Base every fact on the mod's own scripts, and cite the file and line it came from, for example `CF_ModuleWorld.c:3`. The repository test fails when a pack cites nothing.
3. Describe the mod's API in your own words with short original examples. Never paste the mod's code into the pack: community mods ship under their own licenses.
4. Add a row for the pack in `.claude\skills\_shared\README.md`. The repository test fails when a pack is missing from that index.
5. Tell the agent that does the work when to read it. Add one line to its file in `.claude\agents\`, the way the UI specialist names Dabs Framework: use it only when the mod lists the community mod in `requiredAddons[]`, and then read the pack first.
6. Run the tests: `py -m pytest -q .claude scripts/dev hooks`.

### Adding a rule or a specialist

- **A rule:** correct the AI once, then run `/dayz-record-correction`. It saves the rule in the right tier after you approve it.
- **A specialist:** ask the agent creator, for example "Create an agent that builds Expansion market configs." It writes the agent file and checks it against the agent standard. Then add the new agent to "All agents" on the Agents page and update the count on the home page. `/docs-sync` reports anything you missed.

### Making an add-on

An add-on connects an outside tool, such as Blender, an AI 3D generator or another MCP server, at one point in the loop. Usually it hands a finished model to the Object Builder specialist, so the standard gates check it like any other work. Add-ons will ship in an optional `agentic-z-addons` plugin. That plugin is planned: no add-on ships yet, and the plugin marketplace lists only `agentic-z`. For the optional dependencies of the core, see [Optional extras](#optional-extras).

Every add-on follows these rules:

- **Optional:** the core never loads an add-on unless the user installs it.
- **Same gates:** everything an add-on produces goes through the mod review, the build check and the in-game test.
- **No reverse engineering:** no add-on unpacks protected mods or converts binarized models back into editable ones.

### Suggested add-ons

These are the outside tools we plan to connect first. Each one has an MCP server or API an agent can drive.

| Tool | What it could do for a DayZ mod |
| --- | --- |
| **Figma MCP** | Design menus, HUD pieces and other in-game screens in Figma, then turn them into DayZ layout files. |
| **Blender MCP** | Model, clean up and UV unwrap in Blender, then export a model ready for the Object Builder specialist. |
| **Meshy** | Generate a first 3D model from a text prompt or an image, as a starting point to refine in Blender. |
| **Higgsfield** | Make concept art, texture ideas and short video clips for your Workshop page and trailers. |

> [!NOTE]
> Coming soon. The workflows for these add-ons will ship in an upcoming release. Until then, nothing on this list is installed or connected by Agentic-Z.

## How the grading works

The author does not set the grades. Separate AI reviewers grade every agent, skill and shared file against Anthropic's published best practices for Claude Code. The reviewers are Claude instances started fresh for the job. They see the files, the rubric and the standards, but never the earlier grades or the author's opinion. This is not an official Anthropic rating. It is a repeatable review that anyone can run again with the prompts below.

Answer tests (evals) check 30 of the 30 agents, and a change may only keep or raise a score. Claude Code handles prompt caching on its own, so Agentic-Z has no rule or test of its own for it.

### The final count

The final grades cover 193 items, and 193 are at A+: 30 of the 30 agents, 44 of the 44 skills and 119 of the 119 shared items. The shared items are the hooks, the search server, scripts and wrappers, answer tests, rules files, the shared reference packs and this method note.

The final review graded every item. Fresh graders then regraded items after each fix round. In the last rounds every reviewer also got the defect rule under "Run it yourself", so only concrete defects counted against an item, not feature requests. Each item shows its latest grade. The grades come from `final_grades.json` and `final_grades_shared.json`. The `clean-repo` item was graded twice and counts once.

### Who grades

- **Independent reviewers:** each round starts new Claude reviewers with no memory of earlier rounds. The final rounds used seven: two for the agents, three for the skills, one for the shared files and one for the answer tests. The shared items are the hooks, the search server, the scripts and wrappers, the answer tests, the rules files, the shared reference packs and this note.
- **Read-only access:** reviewers cannot edit files. They read every file, run the tests where the session allows it, and check claims against the code and the vanilla DayZ files on the P: drive. The skill reviewer for `dayz-launch-objectbuilder`, `dayz-launch-workbench` and `dayz-search-download` could not run pytest for them, because its session denied it. The reviewer stated this in its reasons.
- **Separate fixers:** different agents fix the problems the reviewers find, and each fixer owns its own files. A fixer never grades its own work.
- **Regrading:** new reviewers grade again after every fix round. An item counts as A+ only when an independent reviewer gives it A+.

### What they grade against

- **Anthropic's standards:** the Claude Code subagent documentation (code.claude.com/docs/en/sub-agents), the Agent Skills best practices (docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices), the Claude Code hooks reference (code.claude.com/docs/en/hooks) and the plugins reference (code.claude.com/docs/en/plugins-reference). For the search server, the reviewers also use the Model Context Protocol tool guidance.
- **Agentic-Z's own rules:** `CLAUDE.md` (Tier 1), the DayZ rules file and its topic files (Tier 2), the agent standard in `agent-creator.md`, and `docs/prompt-conventions.md`.
- **The real game:** DayZ facts are checked against the vanilla files on P:. Examples include which file holds CfgSurfaces, which texture suffixes exist, and which widget classes can be the root of a layout. The Enforce Script worked examples are checked on P: too, and a test keeps them in step with the vanilla files.

### The rubric for agents and skills

| Agents | Skills |
| --- | --- |
| **Description:** a precise contract, written in the third person, that states what the agent does and when to use it, with a realistic example and valid YAML. | **Frontmatter:** the name matches the folder, and the description states what the skill does and when to use it, in the third person and kept short. |
| **Tools:** only the tools the role needs, and every tool the instructions require. Read-only roles cannot edit. | **Instructions:** concise and accurate to the code, with every claim and sample output checked against the script, and a clear section on how to run it. |
| **Body:** Lean and specific. It points to shared rules instead of repeating them and uses rules written in capital letters sparingly. | **Script:** Readable, with clear error messages, a nonzero exit code on failure, no dead code and reuse of shared helpers. The environment check runs first where the rules require it. |
| **Correct and consistent:** Every path, skill, agent and tool it names exists and is used correctly. Nothing contradicts the rules or the team flow, and DayZ facts are verified. | **Tests:** Tests exist, cover the risky logic and pass. |
| **Handoffs:** It states what it returns and to whom. | **Safety:** Every destructive step is guarded by a backup, a dry run or a confirmation. |

### The rubric for everything else

The 119 shared items are neither agents nor skills, so the reviewer judges each kind of item against criteria suited to it.

| Kind of item | What the reviewer checks |
| --- | --- |
| Hooks | The output JSON is correct for the hook event, a bug in a hook never blocks the session, the plugin and clone wiring match, and tests pass the hook input through stdin. |
| Search server | Every tool carries read-only annotations, the tool descriptions are clear, errors are returned as `isError` results, and tests cover the tools. |
| Rules files | Every rule is true of the code, no rule repeats another tier, and every named path and skill exists. |
| Specialist reference files | Each game fact cites a P: file and line or is marked as unverified, the cited lines hold when opened on P:, and nothing contradicts the checked references. |
| Scripts, wrappers and repository tests | The tests run and pass, the documentation and help text match the code, and failures exit with a nonzero code and a clear message. |
| Answer tests (evals) | The cases test what the agent is for, the runner and baselines match, and a change can only keep or raise a score. Answer tests cover 30 of the 30 agents. |
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

The final rounds added this defect rule after the prompt, word for word:

```
Defect rule (from the repository owner, applies to this grading): count only concrete defects: a wrong DayZ fact (checked on P:), a failing test, a doc, comment or help text that does not match the code, or a real bug a user would hit. Feature requests, extra tests for behavior that already works and is covered, optional hardening, refactors and style or wording preferences are NOT defects and must not lower the grade. An item with no concrete defect is A+. For anything lower, "To reach A+" names only the concrete defects, each with its file and line.
```

Because each run uses a new reviewer, two runs can word their findings differently, and a stricter reviewer can find a new edge case. This is intended. The grading found real bugs, and each one was fixed and covered by a test.
### Quality by version

This table lists the grade of each agent, skill and shared item at three points. Independent AI reviewers assigned every grade: on the working tree before the agent team was added (after the v1.0.0 release), after the v1.5.0 grading rounds, and for the final release. The final grades also cover the hooks, the search server, the scripts, the answer tests and every specialist reference folder. For the final totals, see "The final count".

![Agentic-Z versions and grades](images/guide-05-1.svg)

Two values in the table are not grades. "Not built" means that the item did not exist yet at that version. "n/a" means that the shared file was not graded at that version. The last column is the final grade, not a target.

| Item | Before the agent team (after v1.0.0) | v1.5.0 agent team | v2.0.0 final |
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
| `_shared/enscript-style.md` | n/a | n/a | A+ |
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
| `_shared/enscript-style/README.md` | not built | not built | A+ |
| `_shared/enscript-style/best-practices.md` | not built | not built | A+ |
| `_shared/enscript-style/control-flow-and-preprocessor.md` | not built | not built | A+ |
| `_shared/enscript-style/debugging-and-errors.md` | not built | not built | A+ |
| `_shared/enscript-style/layout-and-comments.md` | not built | not built | A+ |
| `_shared/enscript-style/memory.md` | not built | not built | A+ |
| `_shared/enscript-style/modding-patterns.md` | not built | not built | A+ |
| `_shared/enscript-style/naming.md` | not built | not built | A+ |
| `_shared/enscript-style/types.md` | not built | not built | A+ |
| `enscript/examples/layouts.md` | not built | not built | A+ |
| `enscript/integrations/expansion_style.md` | not built | not built | A+ |
| **Hooks** | | | |
| `hooks/hooks.json` | not built | not built | A+ |
| `hooks/test_plugin_copy.py` | not built | not built | A+ |
| `hooks/edit_check.py (+ test_edit_check.py)` | not built | not built | A+ |
| `hooks/scope_guard.py (+ test_scope_guard.py)` | not built | not built | A+ |
| `hooks/paste_router.py (+ test_paste_router.py)` | not built | not built | A+ |
| `dayz-rag MCP server (server.py, voyage_common.py, README, tests)` | not built | not built | A+ |
| `mods/agentic-z-panel (plugin.json, hooks.json, register.tsx, register.test.tsx, types)` | not built | not built | A+ |
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
| `evals/questions/agent-creator.json` | not built | not built | A+ |
| `evals/questions/dayz-build-checker.json` | not built | not built | A+ |
| `evals/questions/dayz-build-engineer.json` | not built | not built | A+ |
| `evals/questions/dayz-docs-writer.json` | not built | not built | A+ |
| `evals/questions/dayz-ingame-tester.json` | not built | not built | A+ |
| `evals/questions/dayz-lead.json` | not built | not built | A+ |
| `evals/questions/dayz-map-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-mod-architect.json` | not built | not built | A+ |
| `evals/questions/dayz-mod-debugger.json` | not built | not built | A+ |
| `evals/questions/dayz-orchestrator.json` | not built | not built | A+ |
| `evals/questions/dayz-router.json` | not built | not built | A+ |
| `evals/questions/dayz-server-admin.json` | not built | not built | A+ |
| `evals/questions/dayz-ui-specialist.json` | not built | not built | A+ |
| `evals/questions/dayz-workbench-specialist.json` | not built | not built | A+ |
| `evals/questions/figma-node-normalizer.json` | not built | not built | A+ |
| `evals/questions/figma-to-dayz-layout.json` | not built | not built | A+ |
| **Scripts and repo tests** | | | |
| `scripts/dev/evals.bat, clean-repo.bat, docs-sync.bat` | not built | not built | A+ |
| `scripts/setup/preflight.bat, workdrive.bat, setup-objectbuilder.bat, statusline.bat, sync-skills.bat` | not built | not built | A+ |
| `scripts/dayz/*.bat (the other 35 wrappers: add-scaffold, add-server, ask, balance, build-imageset, build-pbo, clean-workspace, conflict-check, cot-bootstrap, deploy-pbo, gate, health, import-mod, launch-test, layout-preview, lint, logwatch, new-mod, objectbuilder, p3d-audit, pack-texture, recipe, release-pack, route, scope-mod, search-download, search-index, server-kit, status, stop-test, triage, types-edit, types-split, upgrade-guard, workbench)` | not built | not built | A+ |
| `scripts/README.md` | not built | not built | A+ |
| `scripts/dayz/dayz-search.bat` | not built | not built | A+ |
| `scripts/setup/agentic-z-update.bat` | not built | not built | A+ |
| `scripts/dev/test_repo_integrity.py` | not built | not built | A+ |
| `scripts/dayz/dayz-search.py` | not built | not built | A+ |
| `.claude/skills/_shared/test_enscript_examples.py` | not built | not built | A+ |
| `scripts/dev/test_dayz_search.py` | not built | not built | A+ |

## Where everything lives

These trees show every folder Agentic-Z uses, in three places: the repository, the P: drive and your user folder. Folders marked **local** are created on your PC as you work and are never committed to git.

### The repository

:::tree <repo>\
.claude-plugin\ | Plugin manifest for the Claude Code plugin install
  marketplace.json
  plugin.json
.claude\ | Agents, skills and the search server
  agents\ | The 30 agents, one .md file each
  agent-memory\ | Per-agent memory, one folder per agent | local
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
.imports\ | Repos cloned by /dayz-import-mod for GitHub links to a subfolder | local
.server\ | Local test servers. Only each instance's serverDZ.cfg and mission\ are committed (not mission\storage_*)
  <instance>\ | One test server: mission, serverDZ.cfg, and Profiles with the server logs
  <instance>-behavior\ | Copy of the instance that the behavior gate runs in | local
  !ClientDiagLogs\ | Client logs | local
  !Health\ | Stored gate results | local
    <ModName>\ | Gate results and the health page for /dayz-health
docs\ | Project docs and release notes
evals\ | Answer tests
  fixtures\ | Sample files the answer tests check against
  questions\ | One question file per covered agent
  baseline.json | The recorded score for each covered agent
hooks\ | The three hooks: edit check and scope guard on edits, and the paste router on each prompt
output\ | Everything the skills produce
  <ModName>-plan\ | The plan, the behavior checks and the visual shots list
  <ModName>-release\ | Release texts, release pack and server kit zip
  <ModName>-visual\ | Screenshots for each run (runs\, not committed) and the baselines, which are committed
  evals\ | Answer test results | local
  layout-preview\ | Layout preview images
scripts\ | A .bat file for every runnable skill, so you can run it with no AI
  dayz\ | Modding scripts
  dev\ | Repository tools and tests
  setup\ | Setup scripts
wiki\ | Source for the Agentic-Z docs website
workspace\ | Your mods
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

- **Review before you ship:** AI can make mistakes. The gate agents and reviewers check every change, but they are AI too. Read the changes, test the mod in game, and only then publish it.
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
| Does it cost money? | Agentic-Z is free to use for DayZ mods. It is source-available: see [License](#license). You need your own AI tool. RAG search requires a Voyage AI key. The last full index build embedded about 66M tokens, and the current indexer creates more chunks, so check Voyage pricing. `/dayz-search-download` avoids the build by downloading a prebuilt index. That index is older than the current indexer, and searching still requires the key to embed your questions. |
| Which AI tools does it work with? | See "Which AI tools it works with" under "What Agentic-Z is". |
| Should I install the plugin or clone the repository? | See "Install and first setup". |
| Does it use Expansion, CF or other community mods? | Not in the core: Agentic-Z is built on vanilla DayZ and Bohemia's own tools on purpose (see [One source of truth](#one-source-of-truth)). Your mod can still use them, and you can teach Agentic-Z about new ones. See "Community mods and add-ons". |
| Will it change my other mods? | No. Skills write only to your mod and to their own state, as listed in "Where everything lives". `/agentic-z-update` also checks out updated template files into your clone and commits them. |
| Does it publish to the Workshop? | No. Builds go to `P:\Mods\@<ModName>`, which the launcher loads. Publish with DayZ Tools Publisher. |
| Can I work on several mods? | Yes. Each mod has its own folder at `workspace\<ModName>`. To change mods, choose "Set up or switch to another mod" in the `/dayz-init` hub. |
| Where are the logs? | See the `.server` folders in "Where everything lives". |
| Does P: stay mounted? | No. See the first row of "Troubleshooting". |
| Do I need the DayZ Server? | Usually. `/dayz-add-server` copies the mission template from the DayZ Server installation when the instance's `mission\` folder is missing or empty, and again for `--refresh-mission`. If you put the mission in `.server\<instance>\mission\` yourself, the DayZ Server is not needed. |
| How do I update? | For a plugin installation, update through the Claude Code plugin marketplace. For a clone, run `/agentic-z-update`. |
| Is it safe to run? | Yes. See "Safety". |
| Can I teach it my style? | Yes. Correct it once, then run `/dayz-record-correction`. The rule is saved after you approve it. |

## Getting help and contributing

For help, join the DayZ n' Chill Discord at `discord.gg/dayznchill`. The repository is at `github.com/DayZ-n-Chill/Agentic-Z`. To contribute, create a branch with a name that starts with `feature/`, `fix/`, `docs/` or `chore/`, and open a pull request.

### License

Agentic-Z is source-available, not open source. The code is public so you can read it, use it and change it, but it comes with limits. The full terms are in [LICENSE](https://github.com/DayZ-n-Chill/Agentic-Z/blob/main/LICENSE).

- **You can:** use, modify and run Agentic-Z to build DayZ mods and related content.
- **Your mods are yours:** anything you build with it is yours to share or sell. The license puts no limits on your mods.
- **You can share it for free:** pass on Agentic-Z, changed or unchanged, at no charge, as long as the license and copyright notice stay with it.
- **You can't sell it:** you may not sell, license or otherwise make money from Agentic-Z itself, in whole or in large part. That includes its code, agents, skills, prompts and documentation, changed or not.
- **You can't build a paid product on it:** you may not offer it as a paid product, template or service, or put it inside any paid or monetized app, agent system or service, even as just one part of it.
- **Only for DayZ modding:** the license covers building DayZ mods and related content. It gives no permission to use Agentic-Z for anything else.
