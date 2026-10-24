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
- [What changed from Agentic-Z 1.6.0](#what-changed-from-agentic-z-160)
- [Agents](#agents)
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
| Self-checking repository | A test suite, answer tests, a CI workflow on GitHub, and `/docs-sync` to keep the wiki in line with the source. For the counts, see Does it work? | Broken agents, missing files and wrong tool names are caught before release. |

## Status and next steps

### Does it work? Checked October 22, 2026

Each feature was checked against the current source. Where a check was not yet possible, the table gives the reason.

The status column uses three values:

- **Works:** checked and confirmed.
- **Needs a step:** works once one setup step is complete.
- **Not run yet:** built, but waiting for a live DayZ session.

| Feature | Status | What was checked |
| --- | --- | --- |
| Test suite | Works | `py -m pytest -q .claude scripts/dev hooks`, run in a clean worktree, collects 5,005 tests. The tests confirm that every agent and skill is registered, every file and skill they name exists, gates cannot edit, tier files match, and every wrapper points to a real script. |
| CI on GitHub | Works | The tests workflow passed on GitHub. |
| Answer tests (evals) | Works | All 30 agents have a question file and a score in `evals/baseline.json`. |
| DayZ facts in the packs | Works | For every pack, the graders opened the cited lines on P:. The Enforce Script examples are checked on P: too, and a test keeps them in step with the vanilla files. |
| RAG search: game files | Needs a step | The index on disk is the August 10, 2026 build (52,048 chunks). For the required steps, see Open items and decisions. |
| Orchestrator, leads, gates in a real session | Works | On October 24, 2026 the orchestrator built a three-retexture plate carrier mod from plan to tested PBO. The run found six bugs, and each was fixed with a test. |
| Behavior and visual gates | Works | Both ran in the same live session. All 10 behavior checks passed, and the visual gate compared a capture with its baseline. |
## Quality by version

The final grades cover 193 items, and 192 are at A+: 30 of the 30 agents, 44 of the 44 skills and 118 of the 119 shared items. The shared items are the hooks, the search server, the scripts and wrappers, the answer tests, the rules files, the specialist reference files and the grading method note. The final review graded every item, and each item shows its latest grade. The grades come from `final_grades.json` and `final_grades_shared.json`. The `clean-repo` skill was graded twice and counts once. The one item below A+ is the Agentic-Z panel mod (`mods/agentic-z-panel`), at B+. It is a third-party piece, so it is kept exactly as it is and was not sent to the fixers.

Independent reviewers graded every agent and skill at v1.6.0, at v1.7.0 and in the current Agentic-Z (see "How the grading works"). All three columns are their grades, and the final column is the final grade, not a target. The final grades also cover the hooks, the search server, the scripts, the answer tests and every shared reference folder under `_shared/`. An item that did not exist yet at a version shows "not built". A shared file that was not graded at a version shows "n/a".

![Agentic-Z versions and grades](images/team-02-1.svg)

The test suite grew from 85 tests at v1.6.0 to 5,005 tests now.

| Item | v1.6.0 released | v1.7.0 agent team | v2.0.0 final |
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
| `_shared/enscript-style.md` | n/a | n/a | A+ |
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
| Hooks | | | |
| `hooks/hooks.json` | not built | not built | A+ |
| `hooks/test_plugin_copy.py` | not built | not built | A+ |
| `hooks/edit_check.py (+ test_edit_check.py)` | not built | not built | A+ |
| `hooks/scope_guard.py (+ test_scope_guard.py)` | not built | not built | A+ |
| `hooks/paste_router.py (+ test_paste_router.py)` | not built | not built | A+ |
| `dayz-rag MCP server (server.py, voyage_common.py, README, tests)` | not built | not built | A+ |
| `mods/agentic-z-panel (plugin.json, hooks.json, register.tsx, register.test.tsx, types)` | not built | not built | B+ |
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
| Scripts and repo tests | | | |
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

## How the grading works

Separate AI reviewers set every grade; the author does not. The reviewers grade each agent, skill and shared file against Anthropic's published best practices for Claude Code. Each reviewer is a new Claude instance started for the task. A reviewer sees the files, the rubric and the standards, but never the earlier grades or the author's opinion. This is not an official Anthropic rating. It is a repeatable review that anyone can run again with the prompts below.

The final grade count opens the "Quality by version" section.

### Who grades

- Each round starts new, independent Claude reviewers with no memory of earlier rounds. The final rounds used seven reviewers: two for the agents, three for the skills, one for the shared files and one for the answer tests. The shared items are the hooks, the search server, the scripts and wrappers, the answer tests, the rules files, the specialist reference files and this method note. Every item has been graded. In the final rounds each reviewer also got a defect rule, so only concrete defects counted against an item: a wrong DayZ fact, a failing test, a doc that does not match the code, or a real bug.
- Reviewers are read-only and cannot edit files. They read every file, run the tests where the session allows it, and check claims against the code and the vanilla DayZ files on the P: drive. One skill reviewer could not run pytest because its session denied it. It said so in its reasons for the three skills it graded that way: `dayz-launch-objectbuilder`, `dayz-launch-workbench` and `dayz-search-download`.
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

The 119 shared items are neither agents nor skills, so reviewers judge each type of item by its own purpose.

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

Every token saver and workflow in this section is new. Each one is built and tested.

### Save tokens

| Saver | Description |
| --- | --- |
| Script-only gates | `/dayz-gate build`, `ingame`, `behavior` and `visual` are plain scripts that print PASS, FAIL or ERROR. Claude is called only when a gate fails. This is the largest saving. |
| Log triage | A list of 52 known errors, each with its fix and its owner. Only new errors go to the debugger, and `triage.py --learn` adds your own errors to the list. |
| Router | Most requests are routed with no model tokens (see What Agentic-Z gives an AI agent). |
| Hooks | The three hooks are described in What Agentic-Z gives an AI agent. |
| Status line | Status line with no token cost (`/dayz-statusline`). |
| Cheaper models | The build engineer and the router run on Haiku, and the docs writer runs on Sonnet. |
| Smaller rules loading | The DayZ rules core is 143 lines, and each of the five topic files is 28 to 56 lines (see [The three tiers of rules](#the-three-tiers-of-rules)). Most skills read only the core, which is 40% less than the old 239-line file. `/dayz-deploy-pbo` and `/dayz-gate` also read the bundle mods section of the config topic file. An agent that reads one topic file loads 17% to 30% less than before. With two topic files, the result depends on the pair. The mod debugger (226 lines) and the mod architect (231 lines) still read slightly less. The vehicle, weapon, and audio and FX specialists (251 lines) read more, as does the mod reviewer with three topic files (283 lines). |
| Wrappers | A `.bat` wrapper for every runnable skill runs its script directly. |
| Shorter descriptions | Every session loads about 2,100 fewer tokens. |

### Workflows

| Group | Workflows |
| --- | --- |
| Paste in | Crash log or RPT; screenshot of a bug; Figma link; GitHub link; types.xml excerpt |
| Build faster | Mod recipes; live log watch; behavior and visual gates; release pack |
| Stay healthy | Upgrade guard; conflict check with CF, COT and Expansion; balance sheet against vanilla; health page for each mod |
| Serve owners | Server kit; cited answers about vanilla; answer tests; layout preview |

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

## Open items and decisions

| Item | Status | Next step |
| --- | --- | --- |
| RAG search | The installed plugin (1.6.0) has the search timeout bug. The fix is in the current Agentic-Z. | The updated plugin, a Voyage API key in `.env`, and a full re-index. |

### Roadmap

1. **Add-ons plugin.** An optional `agentic-z-addons` plugin for outside tools. It will be built only after the core is complete, and only for the add-ons the user names.

## What changed from Agentic-Z 1.6.0

Each change comes from the quality review or the build.

| Type | Change | Reason |
| --- | --- | --- |
| New | Orchestrator, architect and team leads | Previously, the user picked a specialist directly, and nothing split a mod into tasks or checked that the pieces fit together. |
| New | Eight specialists with reference files | Each specialist has its own agent and reference files checked against P:. See [Agents](#agents). |
| New | Script-only gates | A reviewer existed, but nothing required a check before a build. See Save tokens for how the gates work now. |
| New | Workflows and hooks | See Workflows for the workflow list and What Agentic-Z gives an AI agent for the hooks. |
| Moved | Debugger on the fail path | The debugger now receives only new errors. See Save tokens. |
| Fix | Search works after install | Every agent that searches now asks for the search tools under both names. |
| Fix | Every agent ships in the plugin | The Figma and layout agents and the `/dayz-deploy-pbo` skill were not registered, so plugin users never received them. A test now checks every agent and skill. |
| New | Corrections become rules | User corrections become rules in the right tier. See What Agentic-Z gives an AI agent. |
| Removed | Wiki search | The wiki crawler, `/dayz-search-wiki-index` and the `search_dayz_wiki` tool were removed. The search server now covers vanilla DayZ source only. |

## The skills

Agentic-Z provides 44 slash commands that any agent or person can run. Of these, 40 ship in the plugin and four are available in clones only. Of the 40 plugin DayZ skills, 18 check the environment first with `/dayz-preflight`, which is itself the check. The DayZ rules file has 14 exception entries naming 21 skills, each with its reason. `/dayz-particles` is a reference skill with no script.

Some exempt skills still read P:. `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe` and `/dayz-layout-preview` only read files and write a report. `/dayz-upgrade-guard` also saves snapshots under `~/.claude/dayz-upgrade-guard/` and rebuilds the search index only with `--reindex`. `/dayz-ask` only checks that P: is mounted. `/dayz-gate` runs its checks through the scripts it calls. `/dayz-stop-test` skips the check so that it still works as an emergency stop.

:::skills

### Specialist workflows

Every task follows the team loop described in How one task moves through the team. Within that loop, each specialist works through its own steps, listed in the table below. Specialists that write DayZ content look up vanilla first. They use Grep for a class or symbol name they already know, and RAG search for questions by meaning or after two or three failed Grep searches. They then read the real file before relying on any hit. The build engineer, the docs writer, the build checker, the in-game tester and `figma-node-normalizer` have no RAG tool. They work from the mod, its logs or the Figma file.

| Agent | Steps |
| --- | --- |
| **Script lead** | |
| `dayz-script-specialist` | 1. Searches the vanilla scripts for the class it will change and reads the real file. 2. Writes a `modded class` in the correct layer (3\_Game, 4\_World or 5\_Mission) and calls `super`. 3. Adds RPCs only where the client and server must communicate, and checks which side runs each line. 4. `/dayz-lint` and the build gate check and pack the code. Neither compiles Enforce Script, so the in-game gate catches compile errors and reads script.log. |
| `dayz-workbench-specialist` | 1. Reads how vanilla Workbench plugins are registered. 2. Writes the plugin script, using only APIs it found in vanilla and cited as `path:line`. 3. Never opens Workbench itself. Instead, it tells the user to open it with `/dayz-launch-workbench --mod <ModName>`. 4. Returns the plugin and the steps to load and run it. |
| `dayz-persistence-specialist` | 1. Lists every value that must survive a restart. 2. Writes OnStoreSave and OnStoreLoad, with a version number written first. 3. Adds an upgrade path so that saves from the previous version still load. 4. Runs the data audit, which confirms that every field is written and read back in the same order. 5. Places the audit at the end of its report to the script lead. The orchestrator gives the audit to the server lead before the test build. |
| `dayz-ai-specialist` | 1. Studies how vanilla infected and animals decide what to do. 2. Writes the behavior as its own script classes, never copied from another mod. 3. Includes the spawn setup in its report, for the script lead to forward to the server lead. 4. The in-game test watches the behavior and server performance. |
| **Config lead** | |
| `dayz-config-specialist` | 1. Finds the closest vanilla parent class and reads its definition on disk, cited as `path:line`. 2. Writes CfgPatches with the correct requiredAddons, then the class itself. 3. Matches hiddenSelections to the names in the model. 4. Checks that braces balance and that every entry ends with `;`. `/dayz-lint` and the build gate then check and pack the config. |
| `dayz-vehicle-specialist` | 1. Selects the closest vanilla vehicle as the parent. 2. Writes the vehicle class and its simulation: engine, gearbox, axles and wheels. 3. Adds attachment slots for the doors, hood, trunk, wheels, battery and plug, and adds the fluids. 4. Writes the CarScript or BoatScript class for seats, doors and damage. 5. Gives the server lead a types.xml entry. The behavior gate spawns the vehicle, and a manual checklist covers driving. |
| `dayz-weapon-specialist` | 1. Selects the closest vanilla weapon as the parent. 2. Writes the weapon, magazine and ammunition classes and the attachment slots. 3. Sets recoil and fire modes. 4. Lists the model selections and memory points that the art lead must provide. 5. The behavior gate spawns the weapon and fits each attachment. A manual checklist covers firing and reloading. |
| **Art lead** | |
| `dayz-object-builder` | 1. Specifies the LODs (visual, geometry, fire geometry, view geometry and memory) as numbered Object Builder steps. The user builds them, because the agent cannot edit a .p3d file. 2. Names the selections and memory points that the config and animations need, and writes model.cfg. 3. Runs `/dayz-p3d-audit` after the user saves the model. 4. Sends the selection names and config lines, through the art lead, to the worker that owns the class's config.cpp. |
| `dayz-asset-specialist` | 1. Checks that each texture has the correct suffix (\_co, \_nohq, \_smdi and the others). 2. Packs the textures with `/dayz-pack-texture`. 3. Writes the .rvmat file for each material. 4. Writes a visual checklist for the user to review in Object Builder or in game. It never launches either one. |
| `dayz-wearables-specialist` | 1. Selects the inventory slot and the closest vanilla item as the parent. 2. Sets the slots held, protection and insulation. 3. Sets hidden selections so that one model carries every color. 4. Records the proxy positions for the Object Builder specialist. 5. The behavior gate wears each color class, and a person checks in game how each color looks. |
| `dayz-animation-specialist` | 1. Lists the moving parts and their bones. 2. Writes skeletonBones for the moving parts and the class Animations block in model.cfg. The Object Builder specialist maintains the rest of model.cfg. 3. Gives the user the bone and selection names for their own Blender export. 4. Names the script hook that plays the animation. The script specialist writes that code, and the in-game test uses it. |
| **UI lead** | |
| `dayz-ui-specialist` | 1. Reads the vanilla layout closest to the new screen. 2. Writes the .layout file and the script class that drives it. 3. Builds icons into an imageset with `/dayz-build-imageset`. 4. The layout validator checks the layout against the Figma-to-DayZ rules, `/dayz-layout-preview` renders it, and the in-game test opens it. |
| `figma-node-normalizer` | 1. Reads the Figma frame. 2. Cleans up layer names and structure so that they map to DayZ widgets. 3. Returns the clean tree as JSON to its caller and names `figma-to-dayz-layout` as the next stage. |
| `figma-to-dayz-layout` | 1. Converts the clean tree into a DayZ .layout file. 2. Uses only widget types that the game supports. 3. Writes the file, returns to its caller and names `dayz-layout-validator` as the next stage. |
| **Server lead** | |
| `dayz-server-admin` | 1. Writes types.xml entries with `/dayz-edit-types`. 2. Adds events, spawn points and gameplay settings where needed. 3. Splits large economy files with `/dayz-split-types`. 4. Sets up a missing test server instance with `/dayz-add-server`, which starts nothing. It gives the user the `/dayz-launch-test` command instead of starting the server itself. |
| `dayz-map-specialist` | 1. Writes layers.cfg and the surface and clutter configs. If it needs the user's own layers.cfg and that file is missing, it stops and asks for it. 2. Provides numbered steps for the DayZ Editor export and for the Terrain Builder import and generation, which the user carries out. 3. Returns the files and the steps to rebuild the map. |
| **Release lead** | |
| `dayz-build-engineer` | 1. Packs the mod with `/dayz-build-pbo`. 2. Starts the test session with `/dayz-launch-test`. 3. Reports the build result to the release lead, who passes it to the orchestrator. |
| `dayz-docs-writer` | 1. Reads what changed in the wave. 2. Updates the README, the changelog and the class name list. 3. Writes the Workshop text and the server owner notes with `/dayz-release-pack`. |
| **Any lead** | |
| `dayz-audio-fx-specialist` | 1. Reads the vanilla sound or particle effect closest to the request. 2. Writes the sound shader and sound set, or writes the particle effect with `/dayz-particles`. 3. Adds the script line that plays it. 4. The in-game test listens to the sound and watches the effect. |
| `dayz-physics-specialist` | 1. Reads the model's geometry LODs and mass. 2. Finds the fault: missing geometry, incorrect mass or faulty collision. 3. Hands the fix to the Object Builder specialist or to the worker that owns the class's config.cpp. It never edits files. 4. A person runs an in-game test that drops, throws and shoots the object, which the behavior gate cannot do. |
| **Checks and fixes** | |
| `dayz-mod-reviewer` | 1. Reviews the finished task against the DayZ rules file. 2. Lists each problem with the specialist that owns it. |
| `dayz-layout-validator` | 1. Checks the .layout file against the Figma-to-DayZ rules for file format and widget classes. 2. Reports PASS or FAIL, with each problem and its line number. |
| `dayz-build-checker` | 1. Runs only when the `/dayz-gate build` script errors (exit 2) instead of giving a verdict. 2. Runs `/dayz-lint`, stops any running test session, rebuilds with `/dayz-build-pbo` (or checks a prebuilt bundle with `/dayz-deploy-pbo`), and reports PASS or FAIL with the AddonBuilder lines and the file they point to. |
| `dayz-ingame-tester` | 1. Runs only when the `/dayz-gate ingame` script errors (exit 2) instead of giving a verdict. 2. Stops any leftover session, launches its own test session with `/dayz-launch-test`, reads the log lines written after it started, reports PASS or FAIL, and stops the session. |
| `dayz-mod-debugger` | 1. Receives only new errors that triage does not recognize. 2. Traces script.log, RPT and crash files back to the line that failed. 3. Reports the cause, evidence, location and fix to its caller (the orchestrator or a lead), and names the worker agent that owns the fix. |

### How one task moves through the team

1. The user approves the mod plan from the architect, for example "a tactical vest with three retextures".
2. The orchestrator splits the plan into tasks, such as "write the vest's config.cpp entry".
3. The appropriate lead takes the task and starts a worker.
4. The worker searches vanilla and checks the real file, reads the reference files that the task needs, and completes that one task.
5. The work then passes through the gates described in The team flow. If anything fails, a known error returns with its fix already named, and the debugger reads the logs for any new error. The task then goes back to the worker with notes.
6. Work that passes is packed into a PBO and loaded on a test server.
7. The user gives the final approval and publishes the mod to the Steam Workshop with DayZ Tools Publisher.
