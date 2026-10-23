# Agentic-Z Agent Team

This document describes the Agentic-Z mod team: the 30 agents and 44 skills that work together to build a DayZ mod. You describe the mod once and approve a plan. The orchestrator splits the work into tasks, team leads hand each task to the right specialist, and gates check every result before you get a tested build. The sections below cover how the team works, what each agent and skill does, and how every part is graded.

## Contents

- [How the team works](#how-the-team-works)
    - [The team flow](#the-team-flow)
- [What Agentic-Z gives an AI agent](#what-agentic-z-gives-an-ai-agent)
- [Status and next steps](#status-and-next-steps)
    - [Does it work? Checked October 22, 2026](#does-it-work-checked-october-22-2026)
- [Quality by version](#quality-by-version)
- [How the grading works](#how-the-grading-works)
    - [Who grades](#who-grades)
    - [What they grade against](#what-they-grade-against)
    - [The rubric for agents and skills](#the-rubric-for-agents-and-skills)
    - [The rubric for everything else](#the-rubric-for-everything-else)
    - [The scale](#the-scale)
    - [Run it yourself](#run-it-yourself)
- [Token savers and workflows](#token-savers-and-workflows)
    - [Save tokens](#save-tokens)
    - [Workflows](#workflows)
- [Growing the team: new specialists](#growing-the-team-new-specialists)
    - [The order it was built in](#the-order-it-was-built-in)
    - [The same cycle for every specialist](#the-same-cycle-for-every-specialist)
- [Open items and decisions](#open-items-and-decisions)
    - [Roadmap](#roadmap)
    - [What we take and what we leave](#what-we-take-and-what-we-leave)
- [What changed from Agentic-Z 1.0.0](#what-changed-from-agentic-z-160)
- [The agents](#the-agents)
- [The skills](#the-skills)
    - [Specialist workflows](#specialist-workflows)
    - [How one task moves through the team](#how-one-task-moves-through-the-team)

## How the team works

### The team flow

The flow has six stages:

- The user
- Planning
- Team leads
- Workers (one per task)
- Gatekeepers
- Playbook and specialist files

![Diagram](images/team-01-1.svg)

The leads run the mod review on each task, and the layout check on each task that changes a `.layout` file. The orchestrator runs the build check, the in-game test and, when the plan lists behavior checks, the behavior test. It runs these once per wave, one at a time, because there is only one mod folder and one test session. Workers run in parallel only when their tasks touch different files.

### How one task moves through the team

1. The user approves the mod plan from the architect, for example "a tactical vest with three retextures".
2. The orchestrator splits the plan into tasks, such as "write the vest's config.cpp entry".
3. The appropriate lead takes the task and starts a worker.
4. The worker searches vanilla and checks the real file, reads the reference files that the task needs, and completes that one task.
5. The work then passes through the gates described in [The team flow](#the-team-flow). If anything fails, a known error returns with its fix already named, and the debugger reads the logs for any new error. The task then goes back to the worker with notes.
6. Work that passes is packed into a PBO and loaded on a test server.
7. The user gives the final approval and publishes the mod to the Steam Workshop with DayZ Tools Publisher.

## What Agentic-Z gives an AI agent

This table lists everything Agentic-Z gives an AI agent beyond the agents themselves, with a description and the benefit of each feature.

| Feature | Description | Benefit |
| --- | --- | --- |
| **Search and reference** | | |
| RAG search: game files | A searchable index of the vanilla DayZ files on the P: drive (scripts, configs, layouts, materials and economy XML). It is built with Voyage AI code embeddings and stored in LanceDB. | Agents find vanilla code by meaning, such as "how does food spoil", instead of guessing class names. Tool: `search_dayz_source`. |
| File lookup | Opens an exact file and line range on the P: drive, and refuses any path outside it. | Agents read the real source behind a search result. Tool: `get_dayz_file`. |
| Cite then verify | A rule that every agent follows: a search result is only a hint until the real file confirms it. | Answers include `path:line` references that can be checked, and agents invent fewer classes. |
| Cited answers | `/dayz-ask` answers a question about vanilla DayZ and checks every result against P:. It falls back to a keyword search when there is no index or API key. | A question in plain English receives an answer with verified `path:line` citations. |
| Prebuilt index | `/dayz-search-download` downloads a ready-made index from GitHub. | A new installation gets search without spending Voyage credits on embedding. |
| Specialist files | DayZ reference material under `.claude/skills/_shared/`. It contains ten specialist packs, an Enforce Script pack (with references, patterns, framework guides and 13 worked examples) and the Figma rules. | Agents load only the pack their task needs, so they work from facts verified against P:. |
| **The agent team** | | |
| Orchestrator and leads | A planner that runs as the main session, an architect, and one lead per team. | The user describes a mod once and approves a plan. The team then splits and tracks the work. |
| Specialists | DayZ experts for each area (see [Agents](#agents)). | Each task goes to an agent that knows that area of DayZ. |
| Gatekeepers | Mod review, layout check, build check, in-game test and behavior test. | No work reaches the user until it builds and loads in game with clean logs. When the plan lists behavior checks, it must also pass the behavior test. |
| Router | `/dayz-route` keyword rules, then Jev when a TypeSafe key is set, then the Haiku `dayz-router` agent. | Most requests reach the right handler with no model tokens. |
| Figma pipeline (optional) | Three agents that turn a Figma frame into a validated DayZ `.layout` file. | An optional extra for teams that design menus in Figma. It is unused otherwise. |
| Agent creator | An agent that writes and validates new agent files. | New agents follow the same template and rules. |
| **Rules and learning** | | |
| Three tiers | See [The three tiers of rules](#the-three-tiers-of-rules). | Every agent works from the same rules, and no file repeats them. |
| Corrections become rules | `/dayz-record-correction` drafts a rule from a user correction and saves it after the user approves. | A mistake is corrected once, and the whole team stops making it. |
| Agent memory | 19 of the 30 agents, most of them workers, keep notes in the project's own `.claude/agent-memory/` folder. The gates, the debugger, the lead, the router, the build engineer, the docs writer, the physics specialist and the Figma node normalizer keep no memory. | Agents remember the project's decisions between sessions, wherever the repository is cloned. |
| **Hooks** | | |
| Edit check | A syntax check after every edit to `config.cpp` or a `.layout` file. | A missing `;` or `}` is fixed in the same turn, before it causes a build failure. |
| Scope guard | Denies edits to other mods while `/dayz-scope-mod` is set. | An agent that works on one mod cannot damage another. |
| Paste-in router | Reads pasted content and routes it. Crash logs go to triage, `types.xml` excerpts go to a validated merge, and Figma and GitHub links go to their workflows. | Pasted content starts the right workflow with no further explanation. |
| **Safety** | | |
| Permission lists | A shipped allow list and deny list for shell commands, and an explicit tool list on every agent. | Agents can run the repository's own skills, but not inline code or new installations. |
| Read-only checkers | The mod reviewer, layout validator, build checker, in-game tester and debugger cannot edit files. The lead and the physics specialist have no write tools. | The agents that judge the work cannot change it. |
| **Platform support** | | |
| Three AI tools | `/sync-skills` links the same skills into Claude Code, Codex and Gemini. | Teams can use any of the three AI tools with the same skills. |
| Plugin or clone | Agentic-Z installs as a Claude Code plugin, or the repository can be cloned as a mod template. | Plugin users update through the marketplace. Clones update with `/agentic-z-update`. |
| Self-checking repository | A test suite, answer tests, a CI workflow on GitHub, and `/docs-sync` to check that the wiki matches the source. | Broken agents, missing files and wrong tool names are caught before release. |

## Status and next steps

### Does it work? Checked October 22, 2026

Each feature was checked against the current source. Where a check was not yet possible, the table gives the reason.

The status column uses three values:

- **Works:** checked and confirmed.
- **Needs a step:** works once one setup step is complete.
- **Not run yet:** built, but waiting for a live DayZ session.

| Feature | Status | What was checked |
| --- | --- | --- |
| Test suite | Works | `py -m pytest -q .claude scripts/dev hooks`, run in a clean worktree, collects 2,884 tests. The tests confirm that every agent and skill is registered, every file and skill they name exists, gates cannot edit, tier files match, and every wrapper points to a real script. |
| CI on GitHub | Works | The tests workflow passed on GitHub. |
| Answer tests (evals) | Works | 23 of the 30 agents have a question file and a score in `evals/baseline.json`. |
| DayZ facts in the packs | Works | For every pack, the graders opened the cited lines on P:. Six Enforce Script examples are still marked as vendored and have not been checked. |
| RAG search: game files | Needs a step | The index on disk is the August 10, 2026 build (52,048 chunks). For the required steps, see Open items and decisions. |
| Orchestrator, leads, gates in a real session | Not run yet | See Open items and decisions. |
| Behavior and visual gates | Not run yet | Tested with fixtures only. See Open items and decisions. |
## Quality by version

The final grades cover 163 items, and all 163 are at A+: 30 of the 30 agents, 44 of the 44 skills and 89 of the 89 shared items. The shared items are the hooks, the search server, the scripts and wrappers, the answer tests, the rules files, the specialist reference files and the grading method note. The final review graded every item, and each item shows its latest grade. The grades come from `final_grades.json` and `final_grades_shared.json`. The `clean-repo` skill was graded twice and counts once.

Independent reviewers graded every agent and skill at v1.0.0, at v1.5.0 and in the current Agentic-Z (see "How the grading works"). All three columns are their grades, and the final column is the final grade, not a target. The final grades also cover the hooks, the search server, the scripts, the answer tests and every shared reference folder under `_shared/`. An item that did not exist yet at a version shows "not built". A shared file that was not graded at a version shows "n/a".

![Agentic-Z versions and grades](images/team-02-1.svg)

The test suite grew from 84 tests at v1.0.0 to 2,884 tests now.

| Item | v1.0.0 released | v1.5.0 agent team | v2.0.0 final |
| --- | --- | --- | --- |
| Agents | | | |
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
| Skills | | | |
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
| Rules and shared files | | | |
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
| Grading method note (the "How the grading works" section of this document) | not built | not built | A+ |
| `.claude/skills/_shared/README.md (shared file index)` | not built | not built | A+ |
| `_shared/figma-to-dayz-rules.md` | not built | not built | A+ |
| Specialist files | | | |
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
| Enforce Script files | | | |
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
| Hooks | | | |
| `hooks/hooks.json` | not built | not built | A+ |
| `hooks/test_plugin_copy.py` | not built | not built | A+ |
| `hooks/edit_check.py (+ test_edit_check.py)` | not built | not built | A+ |
| `hooks/scope_guard.py (+ test_scope_guard.py)` | not built | not built | A+ |
| `hooks/paste_router.py (+ test_paste_router.py)` | not built | not built | A+ |
| `dayz-rag MCP server (server.py, voyage_common.py, README, tests)` | not built | not built | A+ |
| Answer tests (evals) | | | |
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
| Scripts and repo tests | | | |
| `scripts/dev/evals.bat, clean-repo.bat, docs-sync.bat` | not built | not built | A+ |
| `scripts/setup/preflight.bat, workdrive.bat, setup-objectbuilder.bat, statusline.bat, sync-skills.bat` | not built | not built | A+ |
| `scripts/dayz/*.bat (the other 35 wrappers: add-scaffold, add-server, ask, balance, build-imageset, build-pbo, clean-workspace, conflict-check, cot-bootstrap, deploy-pbo, gate, health, import-mod, launch-test, layout-preview, lint, logwatch, new-mod, objectbuilder, p3d-audit, pack-texture, recipe, release-pack, route, scope-mod, search-download, search-index, server-kit, status, stop-test, triage, types-edit, types-split, upgrade-guard, workbench)` | not built | not built | A+ |
| `scripts/README.md` | not built | not built | A+ |
| `scripts/dayz/dayz-search.bat` | not built | not built | A+ |
| `scripts/setup/agentic-z-update.bat` | not built | not built | A+ |
| `scripts/dev/test_repo_integrity.py` | not built | not built | A+ |
| `scripts/dayz/dayz-search.py` | not built | not built | A+ |

## How the grading works

Separate AI reviewers set every grade; the author does not. The reviewers grade each agent, skill and shared file against Anthropic's published best practices for Claude Code. Each reviewer is a new Claude instance started for the task. A reviewer sees the files, the rubric and the standards, but never the earlier grades or the author's opinion. This is not an official Anthropic rating. It is a repeatable review that anyone can run again with the prompts below.

The final grade count opens the "Quality by version" section.

### Who grades

- Each round starts new, independent Claude reviewers with no memory of earlier rounds. The final review used six reviewers: two for the agents, three for the skills and one for all shared items. The shared items are the hooks, the search server, the scripts and wrappers, the answer tests, the rules files, the specialist reference files and this method note.
- Reviewers are read-only and cannot edit files. They read every file, run the tests where the session allows it, and check claims against the code and the vanilla DayZ files on the P: drive. Three skill reviewers could not run pytest because their sessions denied it, and they stated this in their reasons. These reviewers graded `dayz-launch-objectbuilder`, `dayz-launch-workbench` and `dayz-search-download`.
- Separate fixers correct what the reviewers find. The fixers are different agents, and each one owns its own files. A fixer never grades its own work.
- New reviewers grade again after every fix round. An item counts as A+ only when an independent reviewer gives it A+.
### What they grade against

- **Anthropic standards.** The reviewers use the Claude Code subagent documentation (code.claude.com/docs/en/sub-agents), the Agent Skills best practices (docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices), the Claude Code hooks reference (code.claude.com/docs/en/hooks) and the plugins reference (code.claude.com/docs/en/plugins-reference). For the search server, they also use the Model Context Protocol tool guidance.
- **Agentic-Z rules.** The reviewers use `CLAUDE.md` (Tier 1), the DayZ rules file and its topic files (Tier 2), the agent standard in `agent-creator.md`, and `docs/prompt-conventions.md`.
- **The game files.** Reviewers check DayZ facts against the vanilla files on P:. For example, they confirm which file holds CfgSurfaces, which texture suffixes exist, and which widget classes can serve as the root of a layout. For the worked examples that are not yet checked on P:, see the row "DayZ facts in the packs" in "Does it work? Checked October 22, 2026".

### The rubric for agents and skills

| Agents | Skills |
| --- | --- |
| **Description:** A precise third-person contract that states what the agent does and when to use it, with a realistic example and valid YAML. | **Frontmatter:** The name matches the folder. The description states what the skill does and when to use it, in the third person, and stays short. |
| **Tools:** The agent has only the tools its role needs, and every tool its instructions call for. Read-only roles cannot edit. | **Instructions:** Concise and accurate to the code, with every claim and sample output checked against the script, and a clear section on how to run it. |
| **Body:** Lean and specific. It points to shared rules instead of repeating them and uses capital-letter rules sparingly. | **Script:** Readable, with clear error messages, a nonzero exit code on failure, no dead code and reuse of shared helpers. It runs the environment check first where the rules require one. |
| **Correctness and consistency:** Every path, skill, agent and tool it names exists and is used correctly. Nothing contradicts the rules or the team flow, and DayZ facts are verified. | **Tests:** Tests exist, cover the risky logic and pass. |
| **Handoffs:** The agent states what it returns and to whom. | **Safety:** Every destructive step is guarded by a backup, a dry run or a confirmation. |

### The rubric for everything else

The 89 shared items are neither agents nor skills, so reviewers judge each type of item by its own purpose.

| Item type | What the reviewer checks |
| --- | --- |
| Hooks | The output JSON is correct for the hook event, a bug in a hook never blocks the session, the plugin wiring matches the clone wiring, and the tests pass hook input through stdin. |
| Search server | Every tool carries read-only annotations, tool descriptions are clear, errors return as `isError` results, and tests cover the tools. |
| Rules files | Every rule is true of the code, no rule repeats another tier, and every path and skill named in the files exists. |
| Specialist and Enforce Script files | Each game fact cites a file and line on P: or is marked as unverified, each cited line holds when opened on P:, and nothing contradicts the checked references. |
| Scripts, wrappers and repository tests | The tests run and pass, the documentation and help text match the code, and failures exit with a nonzero code and a clear message. |
| Answer tests (evals) | The cases test what the agent is for, the runner matches the baselines, and a change can only keep or raise a score. |
| This method note | It states the rubric for every item type and gives the grading prompts, and every count, source and claim in it matches the repository and the grade files. |

### The scale

| Grade | Meaning |
| --- | --- |
| A+ | Ready to ship unchanged as an example of best practice. The reviewer found nothing concrete to fix. |
| A, A- | Very good, with one or two concrete defects that a user could encounter. |
| B+ to B- | Works, but has real gaps, such as claims that do not match the code, missing tests or unclear handoffs. |
| C+ to D | Wrong or risky in ways that a user will encounter, or built on an approach that cannot reach A. |

Every grade below A+ must name the concrete defect and the exact fix. Style preferences alone cannot lower a grade.

### Run it yourself

Anyone can repeat the review. Start a fresh Claude Code session in the repository and give it one of the four prompts below. The first prompt grades the agents.

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

The second prompt grades the skills.

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

The third prompt grades all other items.

```
Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every hook in hooks/, the MCP server in
.claude/mcp/dayz-rag/, every wrapper
in scripts/, the answer tests in evals/, the rules files and every specialist
and Enforce Script file under .claude/skills/_shared/. Hooks: correct output JSON for the event,
never block on their own bug, tests through stdin. MCP server: read-only
annotations, clear tool descriptions, errors returned as isError, tests.
Rules files: every rule true of
the code. Specialist files: game facts cite a P: file and line or are marked
unverified, and the cited lines hold (open them on P:). Scripts and answer
tests: tests run, documentation matches the code. Run
py -m pytest -q .claude scripts/dev hooks. Scale A+ to D. A+ means nothing
concrete left to fix. For anything lower, name a concrete defect a user would
actually hit. Output a table: Item | Grade | Why | To reach A+.
```

The fourth prompt grades this method note.

```
Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade the "How the grading works" section of the
Agentic-Z agent team guide. Check that it states the rubric for every kind of
item graded (agents, skills, hooks, search server, rules files,
specialist files, scripts, answer tests and this note); that it gives the
grading prompt for every kind; and that every count matches final_grades.json
and final_grades_shared.json. Scale A+
to D. A+ means nothing concrete left to fix. For anything lower, name a
concrete defect a reader would actually hit.
Output a table: Item | Grade | Why | To reach A+.
```

Each run uses a new reviewer, so two runs can word their findings differently, and a stricter reviewer can find a new edge case. This is by design. Every round found real bugs, and each one was fixed and covered by a test.
## Token savers and workflows

These features move mechanical work out of the AI, so it spends tokens only on work that needs judgment: planning, writing code and configs, review and real diagnosis. Each one is built and tested.

### Save tokens

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

### Workflows

Workflow skills are ready-made jobs for routine modding tasks. Each one runs as a script where possible and asks the AI only for decisions that need judgment. Each workflow skill is described in [The skills](#the-skills).

| Group | Workflows |
| --- | --- |
| Paste in | Crash log or RPT; screenshot of a bug; Figma link; GitHub link; types.xml excerpt |
| Build faster | Mod recipes; live log watch; behavior and visual gates; release pack |
| Stay healthy | Upgrade guard; conflict check with CF, COT and Expansion if your mod uses them; balance sheet against vanilla; health page for each mod |
| Serve owners | Server kit; cited answers about vanilla; answer tests; layout preview |

### Paste it in

Agentic-Z also recognizes the following content when it is pasted into a session.

| Pasted content | Result |
| --- | --- |
| A crash log or RPT file | Triage matches it against known errors, names the cause and the fix, and passes any new error to the debugger. |
| A screenshot of a bug | The paste hook suggests a specialist: the UI specialist for a UI problem, the asset specialist for a texture or material problem, and the script specialist for an error message or incorrect behavior. For an error message shown on screen, the router agent sends the screenshot to the mod debugger (or to gate triage) instead, so the two can disagree in that case. |
| A Figma link | Runs the Figma pipeline and returns a checked `.layout` file. |
| A GitHub link | Suggests `/dayz-import-mod --source <link>`, which imports the mod into `workspace\` and can add any missing standard parts. |
| A Steam Workshop link | Refused, with the reason stated: Workshop content is packed, binarized and often protected. |
| A types.xml chunk | Checks the entries, lists any problems, and suggests `/dayz-edit-types --merge` to merge them. |

## Growing the team: new specialists

New specialists build on Agentic-Z, which remains the base. The team loop is unchanged. The new material adds only workers, their reference files and one check inside the existing build gate. Every fact was verified against the vanilla files on P: and written fresh in our own words. Nothing is copied from outside sources.

![Where the new specialists join the team](images/team-06-1.svg)

### The order it was built in

1. **Research map.** Every topic from outside research and the existing reference notes, sorted into the subjects below. This map is private and is not in the repository.
2. **Foundation.** Client and server ownership rules in the DayZ rules, a `references/` folder layout for specialists, and an empty folder for answer tests (evals).
3. **`/dayz-lint`.** Our own load-error checker. Its findings feed the known-errors triage.
4. **Saving data specialist (persistence).** Storage, save versions and migrations, base building, and a pre-release check that no data is lost.
5. **Vehicle specialist.** Cars, boats, helicopters and flight.
6. **Weapon specialist.** CfgWeapons, attachments, magazines and selections.
7. **Wearables specialist.** Clothing, characters, slots and proxy alignment.
8. **Animation specialist.** model.cfg animation sources, RTM, and the handoff to Blender.
9. **Audio and FX specialist.** Sound shaders and sound sets, working with the existing particles skill.
10. **Physics specialist.** Collision layers, contact and thrown objects.
11. **AI specialist.** Infected, animals, and the patrols or guards built on them. All of it is written from vanilla code and never copied from another mod.
12. **Upgrades to existing material.** A deeper script reference, UI coverage (Dabs and widgets), a texture and rvmat cookbook, model and LOD rules, animated doors in the object builder, a short spec step in `/dayz-init`, and a layout preview at several screen sizes.

### The same cycle for every specialist

![Cycle for every new specialist](images/team-06-2.svg)

### Each specialist in detail

In addition to the specialists for scripts, configs, art, UI, maps and servers, Agentic-Z includes specialists for saved data, vehicles, weapons, wearables, animation, audio, physics and AI. Each one works under a team lead and has its own reference pack. Every pack is checked against the vanilla game files, and a specialist loads its pack only when a task needs it. For the checks that run before a mod is packed, see [How the team checks work](#how-the-team-checks-work).

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

## Open items and decisions

| Item | Status | Next step |
| --- | --- | --- |
| Live DayZ checks | Still outstanding. Nothing in this build has run against a live DayZ session. This includes the team loop, the in-game, behavior and visual gates. | Build one small mod end to end with DayZ running on the user's PC. The user will be asked before this runs. |
| Answer tests for seven agents | The build checker, in-game tester, architect, lead, orchestrator, router and Figma to layout agent have no question file yet. | Write their question files and record a baseline. |
| Files not graded | Nine answer test files, `expansion_style.md`, `examples/layouts.md` and the nine `enscript-style/` section files have no grade yet. | Grade them in the next independent round. |
| Preflight exception list | `docs/dayz-modding.md` still lists five, which no longer matches the DayZ rules file (see The skills). | Bring `docs/dayz-modding.md` in line with the rules file. |
| RAG search | The installed plugin (1.0.0) has the search timeout bug. The fix is in the current Agentic-Z. | The updated plugin, a Voyage API key in `.env`, and a full re-index. |

### Roadmap

1. **Live DayZ checks.** See Open items and decisions.
2. **Answer tests for the last seven agents.** See Open items and decisions.
3. **Grade the files not yet graded.** See Open items and decisions.
4. **Add-ons plugin.** An optional `agentic-z-addons` plugin for outside tools. It will be built only after the core is complete, and only for the add-ons the user names.

## What changed from Agentic-Z 1.0.0

Each change comes from the quality review or the build.

| Type | Change | Reason |
| --- | --- | --- |
| New | Orchestrator, architect and team leads | Previously, the user picked a specialist directly, and nothing split a mod into tasks or checked that the pieces fit together. |
| New | Eight specialists with reference files | Each specialist has its own agent and reference files checked against P:. See The agents. |
| New | Script-only gates | A reviewer existed, but nothing required a check before a build. See Save tokens for how the gates work now. |
| New | Workflows and hooks | See Workflows for the workflow list and What Agentic-Z gives an AI agent for the hooks. |
| Moved | Debugger on the fail path | The debugger now receives only new errors. See Save tokens. |
| Fix | Search works after install | Every agent that searches now asks for the search tools under both names. |
| Fix | Every agent ships in the plugin | The Figma and layout agents and the `/dayz-deploy-pbo` skill were not registered, so plugin users never received them. A test now checks every agent and skill. |
| New | Corrections become rules | User corrections become rules in the right tier. See What Agentic-Z gives an AI agent. |
| Removed | Wiki search | The wiki crawler, `/dayz-search-wiki-index` and the `search_dayz_wiki` tool were removed. The search server now covers vanilla DayZ source only. |

## The skills

Agentic-Z provides 44 slash commands that any agent or person can run. Of these, 40 ship in the plugin and four are available in clones only. Of the 40 plugin DayZ skills, 18 check the environment first with `/dayz-preflight`, which is itself the check. The DayZ rules file has 14 exception entries naming 21 skills, each with its reason. `/dayz-particles` is a reference skill with no script.

Some exempt skills still read P:. `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe`, `/dayz-layout-preview` and `/dayz-upgrade-guard` only read files and write a report, and `/dayz-ask` only checks that P: is mounted. `/dayz-gate` runs its checks through the scripts it calls. `/dayz-stop-test` skips the check so that it still works as an emergency stop.

:::skills
