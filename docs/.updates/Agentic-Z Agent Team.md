# Agentic-Z Agent Team

This document describes the Agentic-Z mod team: the 30 agents and 44 skills that work together to build a DayZ mod. You describe the mod once and approve a plan. The orchestrator splits the work into tasks, team leads hand each task to the right specialist, and gates check every result before you get a tested build. The sections below cover how the team works, what each agent and skill does, and how every part is graded.

## Contents

- [How the team works](#how-the-team-works)
    - [The team flow](#the-team-flow)
- [What Agentic-Z gives an AI agent](#what-agentic-z-gives-an-ai-agent)
- [Status and next steps](#status-and-next-steps)
    - [Does it work? Checked October 22, 2026](#does-it-work-checked-october-22-2026)
- [Quality by version](#quality-by-version)
- [Why each item got its grade](#why-each-item-got-its-grade)
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
- [Real bugs the grading found and fixed](#real-bugs-the-grading-found-and-fixed)
    - [What we take and what we leave](#what-we-take-and-what-we-leave)
- [What changed from Agentic-Z 1.6.0](#what-changed-from-agentic-z-160)
- [The three tiers every agent works from](#the-three-tiers-every-agent-works-from)
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
| Specialists | DayZ experts for each area (see The agents). | Each task goes to an agent that knows that area of DayZ. |
| Gatekeepers | Mod review, layout check, build check, in-game test and behavior test. | No work reaches the user until it builds and loads in game with clean logs. When the plan lists behavior checks, it must also pass the behavior test. |
| Router | `/dayz-route` keyword rules, then Jev when a TypeSafe key is set, then the Haiku `dayz-router` agent. | Most requests reach the right handler with no model tokens. |
| Figma pipeline (optional) | Three agents that turn a Figma frame into a validated DayZ `.layout` file. | An optional extra for teams that design menus in Figma. It is unused otherwise. |
| Agent creator | An agent that writes and validates new agent files. | New agents follow the same template and rules. |
| **Rules and learning** | | |
| Three tiers | See The three tiers every agent works from. | Every agent works from the same rules, and no file repeats them. |
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
| Side panel | `agentic-z-panel` 0.3.0, a second plugin that shows DayZ state and provides one-click buttons. Install it with `/plugin install agentic-z-panel@dayz-n-chill`, then open it with `/dayz-panel`. | Build, check, launch, stop, open the editors and read the logs without spending tokens. |
| Self-checking repository | A test suite, panel tests, answer tests, a CI workflow on GitHub, and `/docs-sync` to keep the wiki in line with the source. For the counts, see Does it work? | Broken agents, missing files and wrong tool names are caught before release. |

## Status and next steps

### Does it work? Checked October 22, 2026

Each feature was checked against the current source. Where a check was not yet possible, the table gives the reason.

The status column uses three values:

- **Works:** checked and confirmed.
- **Needs a step:** works once one setup step is complete.
- **Not run yet:** built, but waiting for a live DayZ session.

| Feature | Status | What was checked |
| --- | --- | --- |
| Test suite | Works | `py -m pytest -q .claude scripts/dev hooks`, run in a clean worktree, collects 2,884 tests, plus 18 panel tests. The tests confirm that every agent and skill is registered, every file and skill they name exists, gates cannot edit, tier files match, and every wrapper points to a real script. |
| Panel tests | Works | `claude plugin test mods/agentic-z-panel` runs 18 tests. |
| CI on GitHub | Works | The tests workflow passed on GitHub. |
| Answer tests (evals) | Works | 23 of the 30 agents have a question file and a score in `evals/baseline.json`. |
| DayZ facts in the packs | Works | For every pack, the graders opened the cited lines on P:. Six Enforce Script examples are still marked as vendored and have not been checked. |
| RAG search: game files | Needs a step | The index on disk is the August 10, 2026 build (52,048 chunks). For the required steps, see Open items and decisions. |
| Orchestrator, leads, gates in a real session | Not run yet | See Open items and decisions. |
| Behavior and visual gates | Not run yet | Tested with fixtures only. See Open items and decisions. |
## Quality by version

The final grades cover 164 items, and all 164 are at A+: 30 of the 30 agents, 44 of the 44 skills and 90 of the 90 shared items. The shared items are the hooks, the search server, the panel, the scripts and wrappers, the answer tests, the rules files, the specialist reference files and the grading method note. The final review graded every item, and each item shows its latest grade. The grades come from `final_grades.json` and `final_grades_shared.json`. The `clean-repo` skill was graded twice and counts once.

Independent reviewers graded every agent and skill at v1.6.0, at v1.7.0 and in the current Agentic-Z (see "How the grading works"). All three columns are their grades, and the final column is the final grade, not a target. The final grades also cover the hooks, the search server, the panel, the scripts, the answer tests and every shared reference folder under `_shared/`. An item that did not exist yet at a version shows "not built". A shared file that was not graded at a version shows "n/a".

![Agentic-Z versions and grades](images/team-02-1.svg)

The test suite grew from 84 tests at v1.6.0 to 2,884 tests now.

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
| Search server and panel | | | |
| `dayz-rag MCP server (server.py, voyage_common.py, README, tests)` | not built | not built | A+ |
| `mods/agentic-z-panel (plugin.json, hooks.json, register.tsx, register.test.tsx, types)` | not built | not built | A+ |
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

## Why each item got its grade

Every item in this table is graded A+. An A+ means that the grader found nothing concrete to fix. The Why column gives the latest independent grader's reason for each grade, edited for consistent style.

| Item | v2.0.0 | Why |
| --- | --- | --- |
| **Agents** | | |
| `agent-creator` | A+ | The description is a clear trigger with an example, and the tools fit the agent's job. Every path, list and test it names exists, and every integrity assert now names its rule. It runs the answer tests with py scripts/dev/run\_evals.py, which works from Bash. The integrity test passes. |
| `dayz-ai-specialist` | A+ | The description is a clear contract with an example. The tools are minimal: there is no Bash, and both dayz-rag names are present. Handoffs to the server admin, the debugger and the script specialist are explicit, and the Report names the script lead. Every P: fact the grader checked is correct. DZInfectedPackBeh is at P:\DZ\data\aiconfigs\config.cpp:304. CfgAIBehaviours is at line 14 of both P:\DZ\AI\config.cpp and P:\DZ\AI\_bliss\config.cpp. The three vanilla script folders exist. ModCommandHandlerBefore, Inside and After are declared in dayzanimal.c and overridden in zombiebase.c. OverrideMovementSpeed and OverrideAlertLevel are in dayzcreatureaiinputcontroller.c. The file uses one MUST, which is within the budget for capitalized words. Nothing concrete to fix. |
| `dayz-animation-specialist` | A+ | Ownership is split precisely with dayz-object-builder. This agent owns skeletonBones and class Animations, while the skeleton class, sections[] and the .p3d stay with dayz-object-builder. Each step points to its own file in the animation pack, and every referenced pack file exists. The claim that vanilla ships no model.cfg text holds, because no model.cfg exists under P:\DZ. Out-of-scope work (.anm and graph changes) is stated, and the Report names its recipient and every item it returns. Nothing concrete to fix. |
| `dayz-asset-specialist` | A+ | Both earlier defects are fixed. The agent sends dayz-config-specialist the healthLevels[] material paths, which P:\DZ\characters\vests\config.cpp uses, and it no longer forwards the skill's suggested \_co suffix for normal or specular maps. The suffix set, the refusal of sizes that are not a power of two and the overwrite behavior match pack\_texture.py. Every pack section it cites exists. |
| `dayz-audio-fx-specialist` | A+ | Every DayZ fact checked out on P:. Both sound config files exist, and their CfgPatches classes are DZ\_Sounds\_Effects and DZ\_Sounds\_Bliss. particlelist.c and P:\graphics\particles exist. powergenerator.c plays a start, loop and stop sound with PlaySoundSet, PlaySoundSetLoop and StopSoundSet, and it plays its smoke with SEffectManager.PlayOnObject. Object.c defines all three sound helpers. The tools are the minimum the job needs (no Bash), and the handoffs are clear. The agent states plainly that no file gate can hear or see the result, and it names the recipient of its report. Nothing concrete to fix. |
| `dayz-build-checker` | A+ | It matches gate\_build in gate.py. Lint runs first, then the session stops, then the build runs. A payload-only bundle skips the build, and a bundle with a linker config.cpp gets both a build and a deploy (FAIL lines and missing-.bisign WARN lines). test\_build\_checker\_matches\_gate enforces this order. The agent has read-only tools and no memory (it is in READ\_ONLY\_GATES), and the PBO path matches build.py. The verdict comes first, and the agent names the recipient of its report. Nothing concrete to fix. |
| `dayz-build-engineer` | A+ | Every skill it names exists with the flags and behavior it describes. These include the /dayz-stop-test OK line, /dayz-build-pbo refusing --clean when other PBOs are present, and the --server-only flag. Its use of Bash is narrowly limited. It stops and reports to the release lead whenever the map or the dependency list is missing. |
| `dayz-config-specialist` | A+ | Ownership boundaries with the weapon, vehicle, wearables and audio specialists are sharp, and handbacks go through the config lead. Every section it cites exists: 'Config conventions', the inventorySlot string-versus-array bug (T148506) in conventions/config.md, and container-base.md. The workflow covers vanilla parent citation, the requiredAddons ordering, forward declarations, the rule to redeclare only changed entries, path checks for $PBOPREFIX$ and \DZ, and a syntax check. The tools are minimal. Nothing concrete to fix. |
| `dayz-docs-writer` | A+ | Every flag it passes to /dayz-release-pack and /dayz-server-kit is real, and the output files it merges are the ones those scripts write. Its warning list matches both skills. Its git commands are read-only and limited to the mod folder. It stops and reports when there is no git repository or no version. |
| `dayz-ingame-tester` | A+ | It matches gate.py. The ready pattern is DEFAULT\_READY\_RE, and the line comes from vanilla P:\scripts\5\_mission\somemission.c:3, as cited. The settle time is 30 seconds and the timeout is 300 seconds. MOD\_QUALIFIED covers NULL pointer and Can't find. The vanilla-only baseline uses the two newest sessions whose CLI params line lacks the mod. test\_ingame\_tester\_matches\_gate enforces this. The agent has read-only tools and no memory, always stops the session, puts the verdict first and names the recipient of its report. Nothing concrete to fix. |
| `dayz-layout-validator` | A+ | Semicolons and = signs inside quotes are allowed, and the agent cites vanilla lines that exist on P: (remoteinfo:38, camera\_tools:98, watermark:55). Step 3 matches what edit\_check.py does with a missing file, a file over 2 MB and the cap of five problems. The agent runs only as a gate and has no write tools, which matches READ\_ONLY\_GATES. |
| `dayz-lead` | A+ | Every worker in the table is a real agent (test\_lead\_workers\_are\_agents), and the lead has no write tools and no memory (NO\_WRITE\_ROLES). Starting workers from a lead is valid under the current specification, which allows a subagent with the Agent tool to start its own subagents up to three levels deep. The specification ignores a type list here, so a bare Agent tool is correct. The table columns match the orchestrator's task table. The persistence audit, the For the server lead block and the health-page quote all agree with the orchestrator and persistence-specialist files. The Figma steps follow the order in CLAUDE.md, and the gate boundaries are clear. Nothing concrete to fix. |
| `dayz-map-specialist` | A+ | The trigger and example for the server team are clear, the write tools fit the role, and the Report names the server lead. These facts were checked on P: and hold. P:\DZ\surfaces\config.cpp holds CfgWorlds > CAWorld > Clutter (line 20), CfgSurfaceCharacters (257) and CfgSurfaces (613). surfaces\_bliss and surfaces\_sakhal exist. No layers.cfg exists anywhere under P:\DZ\worlds. The world config is at P:\DZ\worlds\chernarusplus\world\config.cpp. Nothing concrete to fix. |
| `dayz-mod-architect` | A+ | It is a planning role with Write and no Edit. The recipe draft marker matches DRAFT\_MARK in dayz-recipe/recipe.py. The behavior actions match ACTIONS in dayz-gate/behavior.py (spawn, hands, wear, attach, cargo), and the ID rule matches ID\_RE. The Report names the orchestrator and the output paths. Nothing concrete to fix. |
| `dayz-mod-debugger` | A+ | It is read-only, which suits a role that fixes nothing. When triage has not run, it checks both known-errors.json and the learned file that triage.py loads, and it quotes pasted logs as <pasted>:<line>. Every owner agent it names exists, and its DayZ facts check out. |
| `dayz-mod-reviewer` | A+ | Lint findings keep the owner that lint assigns, so setup faults go to dayz-orchestrator and an unmounted P: goes to the user, which matches known-errors.json. The lint rule names, the --json flag and exit code 2 match lint.py. The hidden selection examples are true on P:. |
| `dayz-object-builder` | A+ | Nothing concrete to fix. The description is clear about ownership, including the animation and physics handoffs, and it has a realistic example. That example's config owner, dayz-wearables-specialist, agrees with line 22. The tools fit a worker that writes model.cfg and runs /dayz-p3d-audit. Every referenced pack file and section exists: models/README.md, lods.md, memory-points.md, named-properties.md, proxies.md and doors.md; sections 3 and 5 of p3d-killers.md; and the 'Required Properties for Placed Objects' section of config-rvmat-checks.md. The LOD values (Geometry 1.0e+13, Memory 1.0e+15, ViewGeometry 6.0e+15, FireGeometry 7.0e+15) match conventions/assets.md. The proxy example points to P:\DZ\gear\camping\combination\_lock3.p3d, which exists. dBodyGetMass exists (P:\scripts\1\_core\proto\enphysics.c:122). The mass and autocenter rules match named-properties.md and mass-and-weight.md. The agent states the ODOL-versus-MLOD limit and the step where the user must save in Object Builder, and its report covers both. |
| `dayz-orchestrator` | A+ | The contract for the main session is clear. The Agent() list carries both the plain names and the agentic-z: names. Every skill call matches its argument-hint: /dayz-gate build, ingame and behavior with --deps, --server and --json; /dayz-new-mod --author with the cached dayz-author.txt (new\_mod.py:34); /dayz-recipe <weapon\|vest\|craftable> <ModName>; /dayz-health record <ModName> review reading standard input (health.py:467); and triage.py --learn. Gate routing, fallbacks and the stop after three rounds are consistent with dayz-lead and dayz-gate. Nothing concrete to fix. |
| `dayz-persistence-specialist` | A+ | Nothing concrete to fix. The description is a precise trigger with a realistic example. The agent has the minimum tools for a worker that writes scripts, with Bash and Skill for /dayz-lint. The workflow runs scripts first (lint) and includes a verification step (the data audit from data-audit.md). Every pack file it names exists. The vanilla hooks check out against P:/scripts/3\_game/entities/entityai.c (OnStoreLoad :2978, EEOnAfterLoad :1381, AfterStoreLoad :1419). The audit route agrees with step 6 of dayz-orchestrator and the 'For the server lead' heading in dayz-lead. The report names its recipient, and the answer tests pass 5 of 5. |
| `dayz-physics-specialist` | A+ | Nothing concrete to fix. It is a diagnosis-only role with no Edit, Write or memory, which NO\_WRITE\_ROLES in test\_repo\_integrity.py enforces. Bash is limited to the audit script. The agent is never named as an owner, which matches the debugger and the reviewer. All pack files exist, and the README's symptom table matches the workflow. Its DayZ facts check out on P:. WoodenCrate is at P:\DZ\gear\camping\config.cpp:10157. dBodyGetMass, dBodyIsDynamic, RaycastRV and ObjIntersectFire are all in P:\scripts. The claim that neither /dayz-gate behavior nor dayz-ingame-tester can drop, throw or shoot matches the behavior gate's actions (spawn, hands, wear, attach, cargo). Its config handoffs match the 'Any team' table in dayz-lead. The agent states plainly that the in-game test steps need a live diagnostic session. It has answer-test questions in evals/questions/dayz-physics-specialist.json. |
| `dayz-router` | A+ | The tools are minimal (Read only), the Haiku pin is documented as a cost decision, and the output is a single JSON line. Its 41 routes match the rules.json targets exactly in both names and kinds, as a script confirmed, and the args keys agree with dayz-route/SKILL.md. Nothing concrete to fix. |
| `dayz-script-specialist` | A+ | It has a precise reference map, a correct layer rule, side checks that match lines 20 to 24 of conventions/scripts.md, a /dayz-lint step with the Bash and Skill tools it needs, and complete handoffs. P:\scripts\3\_game\colors.c and 5\_mission\gui\ exist. Nothing concrete to fix. |
| `dayz-server-admin` | A+ | The table of tasks and done checks matches the skills. test\_types\_edit.py covers the claim that /dayz-edit-types makes a backup only when something changes. The /dayz-add-server --map and /dayz-launch-test --server arguments match their argument-hints. The cfgeconomycore folder rule matches split-types, and the audit intake matches data-audit.md. The agent never starts the server itself. Nothing concrete to fix. |
| `dayz-ui-specialist` | A+ | Nothing concrete to fix. The description is in the third person, says when to use the agent, and sends Figma input back to the pipeline, as the routing rule in CLAUDE.md requires. Every path exists: the Figma rules, gui\_layout.md, widget\_api.md with its 'Imagesets in layouts and script' section, 08\_gui\_menu.c, the numbered .layout examples, dabs\_framework.md, and the 'UI scripting realities' section of ui.md. The /dayz-layout-preview sizes and finding names match its SKILL.md. The /dayz-build-imageset .gui-sources flow matches its SKILL.md. The P: facts hold: P:\gui\layouts exists, LoadImageFile(int, string) is in enwidgets.c:257, and 'set:dayz\_gui image:' is used in ingamehud.c and in vanilla layouts. The tools fit the role, and the report names its recipient. |
| `dayz-vehicle-specialist` | A+ | Nothing concrete to fix. Its ownership boundary with dayz-config-specialist is clear, handoffs go through the config lead, the workflow ends with lint and behavior checks, and the Report names the config lead. The answer tests pass 5 of 5. Every pack file exists. The DayZ facts were spot-checked on P:, and all hold: CfgPatches DZ\_Vehicles\_Wheeled, DZ\_Vehicles\_Water and DZ\_Vehicles\_Parts; the native Transport, Car, Boat and Helicopter classes in P:\bin\config.cpp:1404-1563; CfgSlots in P:\scripts\config.cpp:11; Helicopter, HelicopterAuto and HelicopterScript in scripts/3\_game/vehicles/helicopter.c and 4\_world/entities/vehicles/helicopterscript.c; and MotorbikeScript and P:\DZ\vehicles\singletrack\. GetAnimInstance, GetSeatAnimationType and CrewCanGetThrough are in inheritedcars/civiliansedan.c. The IsVital\* methods, script that reads the 'Engine' and 'FuelTank' zones by name, the Engine, Gearbox and Propeller of the boat SimulationModule, and GUIInventoryAttachmentsProps and fuelCapacity in the wheeled config are all present. |
| `dayz-weapon-specialist` | A+ | Nothing concrete to fix. The description is a precise trigger with an example. The agent has the minimum tools for a writer of configs and scripts. Its ownership boundary with dayz-config-specialist is clear, and every pack file it names exists. Its DayZ facts check out on P:. Weapon classes go in units[] with weapons[] empty, which matches P:/DZ/weapons/firearms/mosin9130/config.cpp and weapon-config.md. chamberableFrom, spawnPileType, ammoItems, recoilModifier, simpleHiddenSelections and class Particles are vanilla keys. RecoilBase and SpawnRecoilObject are in 4\_world. The agent checks its work by script (/dayz-lint) and returns behavior checks in the checks-file format with only supported actions (spawn, hands, attach). It gives a checklist for a person to run for what the gate cannot test, and it names its recipient. Its answer tests pass 5 of 5. |
| `dayz-wearables-specialist` | A+ | The contract for the art team is clear, and every reference file exists. These P: paths were verified: CfgSlots in P:\scripts\config.cpp, and the clothing scripts in 4\_world/entities/itembase/clothing and clothing\_base.c. The agent runs /dayz-lint with the tools it needs, and it returns behavior checks without overwriting the plan file. Nothing concrete to fix. |
| `dayz-workbench-specialist` | A+ | It follows a verify-before-write rule with real sources: P:\scripts\editor\plugins, editor\workbench and 1\_core\workbenchapi.c all exist. The launch commands match /dayz-launch-workbench --mod and /dayz-add-scaffold --piece workbench, and scripts/dayz/workbench.bat exists. The agent never opens Workbench itself. Nothing concrete to fix. |
| `figma-node-normalizer` | A+ | Nothing concrete to fix. It follows least privilege: it has read-only tools plus the Figma MCP tools under all three server names, and it writes no files. The trigger matches the pipeline rule in CLAUDE.md. It stops if no Figma tool is loaded, and it never builds JSON from memory. Its 13 prefixes match section 4 of the rules document exactly (bar\_ maps to progress). The JSON shape matches the eight core fields in section 10 of the rules document. The agent is deterministic and lists every removal in its summary. The Report names the caller and the next stage (figma-to-dayz-layout). The answer tests pass 5 of 5. |
| `figma-to-dayz-layout` | A+ | Prefix-first mapping and per-axis sizing match sections 3 to 9 of figma-to-dayz-rules.md. The claim of one-space indentation is verified against P:\gui\layouts\camera\_checkerboard.layout. The file\_type="layout" filter exists in the dayz-rag server. The agent hands off to dayz-layout-validator in gate mode, then to dayz-ui-specialist. Nothing concrete to fix. |
| **Skills** | | |
| `agentic-z-update` | A+ | The resolve command for each file is now built relative to the repository root that the script runs from, and the quiet reminder names only the commands that apply. The SessionStart hook matches the SKILL.md, with a timeout of 20 seconds and an exit code that is always 0. All 98 tests pass. |
| `clean-repo` | A+ | Nothing concrete to fix. disable-model-invocation is set, which suits a destructive wipe of the whole repository. The description says what the skill does and when to use it, and it points cleanups of a single domain to that domain's skill. The orchestrator stays independent of any domain. Every child dry run finishes before anything is removed, and any dry-run failure aborts the run with nothing removed. A run without --yes in a non-TTY shell is refused (exit 2) before anything runs. The prompt names the cached project and warns when that project is not this checkout. The 'From an agent shell' steps give the correct flow for confirming in chat. The child contract (--include-server, --dry-run, --yes) matches dayz-clean-workspace/clean.py, which runs its own preflight gate (h.gate\_on\_preflight), as the SKILL.md says. The 13 tests cover each of these paths and pass, and the .bat wrapper matches. |
| `dayz-add-scaffold` | A+ | Every claim checked against add\_scaffold.py holds. Pieces run in the documented order, and the author is resolved before anything is written. --piece junction is never part of all, and a real folder or a foreign link is refused. The skill is idempotent, and the SKIP and OK lines match the samples. The templates come from new\_mod.py. The skill gates on preflight first and has 34 tests. Nothing concrete to fix in this skill. The DayZSetting.xml it writes ends up packed into the PBO, but that is fixed in dayz-build-pbo. |
| `dayz-add-server` | A+ | Nothing concrete to fix. The map aliases match the real DayZ Server mpmissions folders on the grading machine (chernarusplus, enoch, sakhal, nasdara), and Steam appid 223350 is correct. The output samples and the refusal list in the SKILL.md match add\_server.py. A refresh keeps a timestamped backup. The template-mismatch gate, the reserved-name checks (! and -behavior), the ANSI-safe config rewrite and the exit on junction failure all exist and are tested. |
| `dayz-ask` | A+ | The trigger description is precise, and the work runs scripts first: RAG search, then a check of every hit against P:, then a Grep fallback. The verdict line and exit codes match the code. The JSON keys, the cap of 60 lines per excerpt, the default folders and the --top-k bounds all match ask.py. The rules for ready-made answers forbid answering from memory. Tests cover verified, moved and dropped hits, every fallback reason, ranking and the CLI. Nothing concrete to fix. |
| `dayz-balance` | A+ | A bad argument now prints ERROR on stdout and exits with code 2, as SKILL.md says. The mask facts check out on P:, including GasMask at line 21 and Inventory\_Base biological=0. All 34 tests pass. |
| `dayz-build-imageset` | A+ | The structure of the generated .imageset (ImageSetClass, RefSize, ImageSetTextureClass with mpix 0, and ImageSetDefClass with Name, Pos, Size and Flags 0) matches the vanilla files in P:\gui\imagesets\ line for line. The code matches the documentation: rectangular atlases with power-of-two sizes, a 10px gutter, next-fit splitting, removal of stale outputs only after every atlas has converted, detection of an unchanged .paa, and identifier checks on sprite names. Preflight runs first, there is a requirements.txt, and there are 31 tests. Nothing concrete to fix. |
| `dayz-build-pbo` | A+ | Every numbered step matches the order in main() in build.py: name check, project, lint gate, preflight, P:\Mods junction, workspace and prefix, junction, tools, ownership gate, clean gate, marker before the build, AddonBuilder, and then a check for a fresh PBO and cleanup. The guards on destructive steps (the ownership marker and the refusal of --clean while payload PBOs exist) are tested. include.lst and exclude.lst match their descriptions. Nothing concrete to fix. |
| `dayz-clean-workspace` | A+ | The ownership rules require proof: a link, or a folder without .git that either has a junction pointing at it or carries an ownership marker. Links are removed with cmd /c rmdir and never with rmtree. The plan order, the cleanup of the health folder, the dry-run flow for agents, the stop on the first failure and the warnings all match clean.py. Destructive actions are guarded by a dry run, a prompt and disable-model-invocation, and there are 26 tests. Nothing concrete to fix. |
| `dayz-conflict-check` | A+ | Run read-only against the real P:\Mods (@CF, @Community-Online-Tools, and @DayZ-Expansion-Bundle with 246 PBO headers), it finished in 0.67 s, which matches 'about a second'. Bundle-only selection, script-name matching from PBO headers, owner and fix lines, and the rule never to extract all behave as documented. The folder names in the documentation match P:\Mods. The limits are stated plainly. Nothing concrete to fix. |
| `dayz-cot-bootstrap` | A+ | It is correctly marked disable-model-invocation, because it launches the game. The edit applies strictly to one player and never touches Roles/\*.txt. The timings (600 s, 15 s, 30 s) match the constants, and the skill kills only the processes it started. Pass 2 runs only after a successful edit. The keybinds were checked against the COT scripts.pbo on P:\Mods: UACOTToggleButtons is kY and UACOTModuleToggleCOT is kEnd, which matches the closing message. The tests are thorough. Nothing concrete to fix. |
| `dayz-deploy-pbo` | A+ | It performs a purely additive copy with an ownership gate. It is idempotent by size plus a 2 s mtime tolerance, handles a locked-file failure while still writing the marker, and warns about an unsigned PBO. The <name>.pbo.<key>.bisign pattern was confirmed against real Workshop folders on P:\Mods. The documentation matches deploy.py line for line, and the tests cover each refusal. Nothing concrete to fix. |
| `dayz-edit-types` | A+ | Child elements are written in the vanilla order of category, tag, usage and value, which matches the Chernarus types.xml. Without cfglimitsdefinitionuser.xml, user= groups are skipped instead of producing a warning. A dry run on the vanilla mission flagged only the real misspelling Militar, and all 64 tests pass. |
| `dayz-gate` | A+ | All gate logic lives in scripts, and the 227 tests run against fixture missions, logs and images. Every option in SKILL.md matches gate.py. Bad arguments exit with code 2 and a clear ERROR line, and commented-out requiredAddons lines are ignored. The Limits section states plainly which parts have not yet run against live DayZ. |
| `dayz-health` | A+ | Checked against health.py: KEEP=200 and HISTORY\_ROWS=50 match the documentation, and 'show' is inserted as the default command. Findings close when a newer result from the same gate drops them, and ERROR reports are refused. The stored folder is ignored by git through .server/\*/\*, and both page files are rebuilt on every record. The skill starts no process and has 34 tests. Nothing concrete to fix. |
| `dayz-import-mod` | A+ | The trigger is clear, including the GitHub and Workshop cases. The Workshop refusal happens before preflight, and the non-TTY decision check happens before any link is made. The workspace link is rolled back when the P: junction fails, and the clone is removed if a later step refuses. The $PBOPREFIX$ mismatch warning matches the build-pbo rule, and the code matches the documentation. 63 tests cover the risky paths. Nothing concrete to fix. |
| `dayz-init` | A+ | The hub, plan.py and the launch dispatch share one rule, so the skill no longer asks for dependencies of prebuilt bundles. Every dispatch action exists, bad input gets clear messages, and the four maps match the installed missions. All 109 tests pass. |
| `dayz-launch-objectbuilder` | A+ | Nothing concrete to fix. The trigger description is clear, and every claim in SKILL.md matches launch.py. Preflight runs first, and --file and --mod are mutually exclusive. --mod opens the single .p3d under data/, or lists several and asks for --file. The registry check is reused from setup.py, the launch is detached with the correct working directory, and OSError is handled. The sample output matches the print statements. The 17 tests cover the risky paths. On disk, the grader confirmed that ObjectBuilder.exe exists under DayZ Tools\Bin\ObjectBuilder and that /dayz-new-mod scaffolds data/. The grader did not run the tests, because pytest was not permitted in that session. |
| `dayz-launch-test` | A+ | Nothing concrete to fix. Every claim in SKILL.md was checked against launch.py and the shared skill\_helpers.py, and all of them match. These include the step order, the dry run that writes nothing, exit code 2 for bad ports and for a mod named both ways, the port gate, the 180 s wait for the bind with a kill on timeout, the server being killed when the client fails to start, detached processes and the fallback for display preferences. The sample output matches the real prefixes. The 38 tests cover the risky paths, and all 181 tests across the four scripted skills pass. The wiki mirror is identical. The remaining limits (a live server bind and the in-game connection) need a live DayZ session, which the skill already depends on. |
| `dayz-launch-workbench` | A+ | Nothing concrete to fix. The description is precise, and the documentation matches the code. Preflight runs first, then the check for the executable, then gproj resolution with distinct errors for a missing mod folder and a missing gproj. The launch is then detached with cwd set to Bin\Workbench. The DayZ facts were spot-checked in the real binary: WorkbenchApp.exe contains the '-gproj' switch and the 'CurrentDir:dayz.gproj' default, and dta/, platforms/, ToolAddons/ and dayz.gproj sit next to it. The 10 tests cover flag handling, cwd and the -gproj= argument. The grader did not run the tests, because pytest was not permitted. |
| `dayz-layout-preview` | A+ | The trigger is clear, and the work runs scripts first: the AI only reads the PNG files. The exit codes (0, 1, 2) match main(). The limits are stated plainly: the 1080 reference for 'scaled 1', and plain halign values treated like the \_ref values. A spot check on P:\gui\layouts confirms that plain 'right' and 'center' appear in vanilla (390 and 287 uses), so handling them is necessary. The skill has fixtures and tests, and it is listed as a preflight exception in dayz-conventions.md. Nothing concrete to fix. |
| `dayz-lint` | A+ | RULES in lint.py matches the table in SKILL.md and the lint-\* entries in dayz-gate/known-errors.json one to one (25 rules each, counting required-addon-duplicate). The claim that /dayz-build-pbo lints before preflight matches build.py (gate\_on\_lint runs before h.gate\_on\_preflight). The DayZ facts check out on P:\: DZ\_data\_aiconfigs has an empty body in P:\DZ\data\aiconfigs\config.cpp, and P:\DZ\data\_sakhal\config.cpp maps worldScriptModule to scripts/4\_World. Procedural #(...) textures are correctly skipped. The skill has 359 lines of tests. Nothing concrete to fix. |
| `dayz-logwatch` | A+ | An interval of zero, a negative value, nan or inf now stops the run with a clear error and exit code 2, and the usage line lists every flag. The SKILL.md matches logwatch.py on folders, crash logs, exit codes and JSON fields. All tests pass. |
| `dayz-new-mod` | A+ | The description is precise and routes to sibling skills. The skill covers refusal cases, cleans a stale junction automatically with rollback on partial failure, validates the author handle and has 357 lines of tests. The workbench/dayz.gproj and DayZSetting.xml it copies exist in DayZ Tools\Bin\Workbench on the grading machine. Nothing concrete to fix. |
| `dayz-p3d-audit` | A+ | All 71 tests pass, and the exit codes behave as documented, including a clear Not MLOD failure for a vanilla ODOL file. The P: path check skips URLs, and kits get no autocenter finding. Component names match regardless of case, so the coverage check always runs. The penetration rvmats and bisurfs that its references cite exist on P:. |
| `dayz-pack-texture` | A+ | The suffix table was checked against DayZ Tools\Bin\ImageToPAA\TexConvert.cfg on the grading machine, and every accepted suffix has a rule there, as the skill claims. The skill refuses a stale .paa whose modification time did not change, validates every input before converting any, gates on preflight and is tested. Nothing concrete to fix. |
| `dayz-particles` | A+ | It is a reference skill that explains why it has no preflight gate. These facts were checked on P:\: POOL\_SIZE 10000 is at particlemanager.c:25, GetInstance() returns null on headless or dedicated servers, the StopParticleFlags enum exists in particlesource.c, the two-argument RegisterParticle(root\_path, file\_name) form exists in particlelist.c:452, and vanilla uses ScaleParticleParamFromOriginal. Unverified items are marked as unverified. Nothing concrete to fix. |
| `dayz-preflight` | A+ | Its only repair (mklink /J when P:\Mods is missing) is narrow and justified. The resolver order is documented, the resolvers are shared, and there are 285 lines of tests. A run on the grading machine found P:\ mounted and DayZ Tools at the default Steam path, which matches the documented resolution. Nothing concrete to fix. |
| `dayz-recipe` | A+ | It runs scripts first and verifies against P:\. It writes nothing on failure, protects existing plans with --force and hands off clearly to dayz-mod-architect. Every default was checked on P:\: AKM (akm/config.cpp:191), AK\_WoodBttstck, Mag\_AKM\_30Rnd, SmershVest, SmershBag, RecipeBase, PluginRecipesManager, RegisterRecipies (pluginrecipesmanagerbase.c:14) and CraftRagRope. The skill is listed as a preflight exception and has 406 lines of tests. Nothing concrete to fix. |
| `dayz-record-correction` | A+ | In a plugin install, step 1 now also searches the Agentic-Z rules section of the project's CLAUDE.md, AGENTS.md and GEMINI.md. Every path it names exists, and its step 3b check passed on a copy of the repository. |
| `dayz-release-pack` | A+ | Every fact comes from the mod's files, each warning states an action, the contract for exit codes is clear, and the handoff to /dayz-server-kit is explicit. The mapping of scope keywords (public, protected, private = 2, 1, 0) matches the DayZ config defines. The skill has fixtures and 229 lines of tests, and it is in the preflight exception list. Nothing concrete to fix. |
| `dayz-route` | A+ | route.py does exactly what the documentation describes. Rules run first, with conflict\_factor 0.5, absorbs and the threshold of 0.8 from rules.json. Jev runs next, only when a key is set, and the final result is a null/next dayz-router result. The skill states that request text goes to api.typesafe.ai. test\_route.py keeps rules.json in sync with dayz-router.md, and that agent exists. This matches the routing rule in CLAUDE.md. Nothing concrete to fix. |
| `dayz-scope-mod` | A+ | It applies least privilege correctly. It adds deny rules only and records exactly what it added, so --clear removes only those rules. It refuses names that would be read as pattern syntax, and it states what it does not protect. The scope\_guard hook backs it up for mods created later. The skill is a listed preflight exception and has tests. Nothing concrete to fix. |
| `dayz-search-download` | A+ | Nothing concrete to fix. The script uses only the standard library, is safe and matches the documentation exactly. It is idempotent by tag through release-tag.txt, refuses an asset with no digest before downloading it, checks SHA-256, extracts tar files safely (with the data filter or a manual check), swaps in a staged copy with a restore path, handles network errors clearly, and exits with code 1 when the prompt is declined or the session is non-interactive. The release claims were checked against the live GitHub API. 1.4.0, 1.1.0, 1.0.1, v1.0.0 and v0.1.0 ship dayz-rag-index-v0.1.0.tar.gz; 1.2.0 and 1.2.1 ship dayz-search-index-<ver>.tar.gz; 1.2.2 has no asset; and every asset has a sha256 digest. The 1.4.0 asset has the same digest as v0.1.0, which supports the claim that the release index predates windowing. The 30 tests cover the risky paths. The grader did not run the tests, because pytest was not permitted. |
| `dayz-search-index` | A+ | All 49 tests pass, and --status and the refusal to overwrite an existing index behave and exit as documented, with no cost incurred. Running the chunker over P: without embedding produced exactly the 61,757 chunks that the documentation claims, with no chunk over 6,000 characters. The six vanilla folders it names exist, and the cost rates and free tier logic match its reference. |
| `dayz-server-kit` | A+ | The code refuses to zip a .biprivatekey (ReleaseError), as the documentation states. The placeholder entries (nominal 0) are commented and listed in README.txt. The source order for types is documented, and the code matches it. --mission accepts an instance name. Tests exist. Nothing concrete to fix. |
| `dayz-setup-objectbuilder` | A+ | The destructive --force option is guarded by a prompt (or by --yes when there is no terminal), a reg export backup, a check that only HKCU is changed, and a refusal while Object Builder is running. These facts were checked on the grading machine: ObjectBuilder\_defaultSettings.reg is in Bin\ObjectBuilder, the CConfig key exists, and '#View background LOD' = 1 matches the preferred flags. The skill has 414 lines of tests. Nothing concrete to fix. |
| `dayz-split-types` | A+ | It is a thin wrapper around a vendored tool, with timestamped backups and the <ce folder> fix. A result check decides success, because the upstream script always exits with code 0. The vendored typeSplitter.py was checked and defines exactly the 19 categories listed. Tests exist. Nothing concrete to fix. |
| `dayz-statusline` | A+ | It edits only settings.local.json and keeps a backup. It records the status line it replaced so that --remove restores it, refuses invalid JSON, and fails quietly with 'DayZ status unavailable'. The RAG age segment reads the indexed\_at field, which exists in the real manifest. The skill is a listed preflight exception and has tests. Nothing concrete to fix. |
| `dayz-stop-test` | A+ | A simple .bat file is the right tool for one taskkill call, which matches the repository's tooling rule. The handling of errorlevel 128 and the pass-through of stderr match the table in the documentation exactly. The skill is a documented preflight exception and is tested with a taskkill stub. Nothing concrete to fix. |
| `dayz-upgrade-guard` | A+ | All 39 tests pass and cover all six finding reasons. A real snapshot of P: took 9.6 seconds and came to 10 MB with no files skipped, which matches the documentation. The check, diff, missing project, older format and bad argument paths all print the documented verdict first with the correct exit code. A separate reindex command rebuilds the search index after a failed check. |
| `dayz-workdrive` | A+ | Nothing concrete to fix. The description is a clear trigger. The skill runs scripts first, and it explains well why it does not gate on preflight. The order in which it searches for the work-drive folder matches the code. Both the WorkDrive.exe route and the subst fallback check whether P:\ is actually present instead of trusting the return code. The skill warns when settings.ini names a letter other than P. The exit codes match the table in SKILL.md. The 33 tests pass. The DayZ facts were checked on the grading machine: DayZ Tools\Bin\WorkDrive\WorkDrive.exe exists, and settings.ini has [ProjectDrive] path= and Letter=P, exactly as the skill reads them. |
| `docs-sync` | A+ | Nothing concrete to fix. The description is in the third person and says both what the skill does and when to use it. Everything runs from a script, and the SKILL.md matches the code: the modes, the exit codes 0, 1 and 2, the mirror map, the orphan rules (about.md and files prefixed with \_ are kept), and the behavior when YAML is missing under --quiet. The Stop hook is wired in .claude/settings.json as 'sync.py --check --quiet' with a timeout of 15 seconds. It prints a valid systemMessage JSON line, never fails the session, and took 0.23 seconds. CI runs 'sync.py --check' in .github/workflows/tests.yml. 'sync.py --check' reports the wiki in sync, and the 60 tests across test\_apply.py and test\_docs\_sync.py pass. Dry runs cover --apply. The em dash characters in apply.py are valid UTF-8, not mojibake. |
| `sync-skills` | A+ | Nothing concrete to fix. The description says what the skill does and when to use it. The instructions match sync.py: the OK, REFRESH, FOREIGN, LINK, SKIP and PRUNE states; the --force takeover; the rule that links into a worktree count as foreign; normalization of case and separators in paths; exit code 1 on a failed link or folder creation; exit code 2 on a bad agents.json, an unknown agent name or a missing skills folder; and the sample '[FAILED] cannot create' line. The paths for each agent in SKILL.md and agents.json (Claude through CLAUDE\_CONFIG\_DIR or ~/.claude/skills, Codex at ~/.agents/skills, and Gemini through GEMINI\_CLI\_HOME/.gemini or ~/.gemini/skills) agree with the skill discovery paths in the repository's CLAUDE.md, AGENTS.md and GEMINI.md. The script never deletes a real folder, has a dry run, and leaves the links of another clone alone unless --force is given. It also tells the user how to reload each agent CLI and how to check the skill counts afterward. All 26 of its pytest tests pass. They cover foreign links, worktrees, orphan pruning, real folders, a malformed agents.json, the --skip and --agents options, and the environment variables that move each agent's home folder. The thin wrapper at scripts/setup/sync-skills.bat forwards its arguments correctly. |
| **Rules and shared files** | | |
| `.claude/skills/_shared/dayz-conventions.md (Tier 2 core)` | A+ | The preflight exceptions match the skills, the RAG facts match server.py, the search rule is clear, and there are no stale references to the wiki. |
| `_shared/conventions/config.md` | A+ | GlowPlug (string form, parts config:822-831) and WoodenCrate (array form, camping config:10157) were verified on P:\. |
| `_shared/conventions/assets.md` | A+ | The LOD table and the suffix set agree with the textures pack and the p3d audit. Nothing concrete to fix. |
| `_shared/conventions/scripts.md` | A+ | The file is correct and cites P:\, for example the IsServerCheck message at entityai.c:2763 and net sync registered in the constructor, as in barrel\_colorbase.c:21. It contradicts enscript/patterns/netsync.md, but the fault is in netsync.md. |
| `_shared/conventions/server.md` | A+ | It matches the .server/ layout and the division of work between the add-server and launch-test skills. |
| `_shared/conventions/ui.md` | A+ | actionmenu.c:74 SetColor(0xFFFFEC44) and mainmenupromo.c:157 COLOR\_DAYZ\_RED were verified. |
| `_shared/container-base.md` | A+ | The citations were verified (WoodenCrate class Cargo at camping config 10261-10266). |
| `_shared/py3d-mlod-notes.md` | A+ | These are library notes for py3d, so no P:\ citation is needed. Nothing concrete to fix. |
| `_shared/skill_helpers.py + test_skill_helpers.py` | A+ | The allowFilePatching regular expression ignores commented-out lines. It has 27 tests. |
| `_shared/enscript-style.md` | A+ | It is a lean front index that sends the reader to one section file per task and states that facts live in the checked references. Its one citation (gameplay.c:636) is correct. |
| `_shared/answer-formatting.md` | A+ | The formatting rules are short and actionable, they match what Claude Code renders, and the file states its tier correctly. |
| Grading method note (the "How the grading works" section of this document) | A+ | The rubric covers every kind of item, and four grading prompts are given, including one for the note itself. The counts match the grade files, and every cross-reference to another section exists. Since this grade, that section has been rewritten in this document to add real test counts, all six reviewers, the references to hooks and plugins, a rubric for the items that are not agents or skills, the grading prompts and the caveat about unchecked examples. The rewritten section has not been regraded since. |
| `.claude/skills/_shared/README.md (shared file index)` | A+ | Every pack folder and file is listed, and the index test passes. The exemption list matches CITATION\_EXEMPT exactly. Its statement of what the integrity test checks (citation presence only) is accurate, and the checked and vendored status of the examples matches enscript/README.md. Every named agent exists. Nothing concrete to fix. |
| `_shared/figma-to-dayz-rules.md` | A+ | The vanilla dark panel is now color 0.1569 0.1569 0.1569 0.902, which appears 225 times on P:. Every P: citation holds when the file is opened, the spacer count of 149 of 227 is exact, and every widget class, alignment, style and font it names exists in vanilla. |
| **Specialist files** | | |
| `_shared/ai (README + 5 files)` | A+ | The files are heavily cited, and the samples were verified (CalculateVisibilityForAI at playerbase.c:5405, SetVisibilityCoef at :5438, and CfgAIBehaviours). All files are under 100 lines. |
| `_shared/animation (README + 5 files)` | A+ | The citations were verified (OpenFence at fence.c:488, ActionOpenDoors at playerbase.c:1697, and Wall\_Gate\_Rotate). |
| `_shared/models (README + 5 files)` | A+ | Every sampled citation matched. All files are short. |
| `_shared/physics (README + 4 files)` | A+ | The citations were verified (dBodyGetMass at enphysics.c:122, GetMass at physics.c:69, and ThrowPhysically). |
| `_shared/vehicles (README + 6 files)` | A+ | The citations were verified (Helicopter: Air at bin config:1563, simulation at :1568, and RotorLibHelicopterProperties at :1673). |
| `_shared/weapons (README + 7 files)` | A+ | The citations were verified (HuntingOptic inventorySlot at optics config:1443, and Slot\_weaponBayonet at scripts config:219). |
| `_shared/wearables (README + 6 reference files)` | A+ | The citations were verified (CanPutInCargoClothingConditions at clothing\_base.c:38, and PlateCarrierVest). |
| `_shared/audio-fx (README + 3 files)` | A+ | About 50 line citations were spot-checked in P:\DZ\sounds\hpp\config.cpp, sounds\_bliss, object.c, effectmanager.c, effectsound.c, powergenerator.c and particlelist.c, and every one matched. The pack marks unverified readings as unverified, tells the user how to free sounds created through the manager, and gives a handoff for the in-game test. |
| `_shared/textures (README + 4 files)` | A+ | Checked on P: and against the real TexConvert.cfg: the \_co/\_ca DXT1/DXT5 classes and their sRGB comments, the \_nohq 1-R/1-A swizzle, \_smdi with R=1 and G and B kept, \_as green only, \_dt alpha only, and \_mc DXT5. The bomberjacket \_damage values (specular 0.4745, specularPower 55, fresnel(1.28,0.5), Stage7 color 0.15, tops\_damage\_mc) match, as do the TacticalGoggles healthLevels at glasses\config.cpp:598 and the pcu5jacket StageTI. Lines about tool knowledge are labeled, and the symptom table points to the right files. Nothing concrete to fix. |
| `_shared/persistence (README + 4 files)` | A+ | About 90 cited lines were opened on P:, and all of them hold what the pack says. These include GAME\_STORAGE\_VERSION 144 at game.c:5, the OnStoreSave and OnStoreLoad chain in entityai.c, the version gates (2981, 3053, itembase 3103, and combinationlock 160 and 169), the BaseBuildingBase masks (143, 150, 157 and the part\_id comment at 139), Fence id=1 at gear/camping/config.cpp:4537, the 500 ms EEOnAfterLoad retry at basebuildingbase.c:505, the PIN length at codelockcomponent.c:23-24, the ECE flags and JsonFileLoader. The analysis of data loss from a modded vanilla class is correct. The audit's handoff (script lead, then orchestrator, then server lead) matches dayz-persistence-specialist, dayz-lead and dayz-orchestrator. Nothing concrete to fix. |
| **Enforce Script files** | | |
| `enscript/patterns/scheduler.md` | A+ | It marks the report of CallLater drift as unverified and cites tools.c:61. |
| `enscript/patterns/physics_items.md` | A+ | It is cited and verified (ThrowPhysically at inventoryitem.c:26). |
| `enscript/references/api_entities_inventory.md, api_game.md, api_network.md, api_player.md, api_scheduling.md, language_compile.md, language_memory.md` | A+ | Every identifier resolves in P:\scripts, and the sampled line citations matched. All files are under 100 lines. |
| `enscript/examples/01_custom_item.c, 04_rpc_patterns.c, 05_mission_server.c, 06_json_config.c, 08_gui_menu.c, 09_scheduler_timer.c` | A+ | Every vanilla name used exists on P:\. The unknown names are the mod's own IDs and widgets. |
| `enscript/patterns/netsync.md` | A+ | Every API line checked matched (entityai.c:2832-3069, playerbase.c:359-364 and 558-565, and InitItemVariables). The claim that ItemBase has no Init() checks out. The rules are correct and cited. |
| `enscript/patterns/json_config_migration.md` | A+ | It gives a correct LoadFile/SaveFile pattern (jsonfileloader.c:7, 42 and 104) and does not overwrite the file on a parse error. Migration is incremental, and the vanilla CfgGameplayHandler citations match (cfggameplayhandler.c:70-72, cfggameplaydatajson.c:4). |
| `enscript/patterns/rpc.md` | A+ | All signature citations matched (object.c:860, entityai.c:3507, game.c:211, 1011 and 1013, dayzgame.c:3141 and 3151, gameplay.c:117, and erpcs.c:1, 7 and 225). It labels the convention of high IDs as a community convention and says to validate everything a client sends. |
| `enscript/patterns/language_workarounds.md` | A+ | Each 'not supported' claim is defined as 'not used in vanilla', and each replacement is cited. The auto, Format, ScriptCaller/ScriptInvoker, overloading and foreach-with-index lines were checked, and all matched. |
| `enscript/integrations/central_economy.md` | A+ | The ECE flag values and lines, CreateObjectEx, GetEconomyProfile, CEApi, ObjectSpawner and the cfggameplay field all match P:\. It labels calls for developers only correctly and points to the right skills. |
| `enscript/integrations/vanilla_plugins.md` | A+ | The citations for PluginManager registration, the lifecycle, GetPlugin/GetPluginSafe and PluginAdminLog all matched (pluginmanager.c:57, 104, 193, 222, 297, 326 and 350, and missionbase.c:21 and 61). |
| `enscript/integrations/input_bindings.md` | A+ | The UAInput and Input API lines, the MissionGameplay hooks, the menu and chat guards and the spectator axis example all match P:\. The inputs.xml format is taken from named shipped mods that exist under P:\Mods. |
| `enscript/integrations/community_framework.md` | A+ | It states clearly that CF is not vanilla and that its source is P:\Mods\@CF\Addons\scripts.pbo. The names checked in the PBO (EnableInvokeConnect, EnableClientReady, CF\_RegisterModule, CF\_OnStoreSave, CF\_ModuleWorld, GetRPCManager, CF\_EventPlayerArgs) are all present. |
| `enscript/references/erpc_defines.md` | A+ | The ERPCs, the agent and modifier calls and the positions of the RPC flags matched P:\ (playerbase.c:8115, brokenlegs.c:81, modifiersmanager.c:227, game.c:1013, gameplay.c:117). It labels the ID ranges as a community convention. |
| `enscript/references/file_paths.md` | A+ | The $saves and $mission tokens and the JsonFileLoader citations matched P:\ (pluginconfigscene.c:3, cfgbunkerbroadcasthandler.c:23, jsonfileloader.c:7). |
| `enscript/references/language_types.md` | A+ | All 48 P:\ citations resolve to existing files and lines, and the sampled citations matched. It works well as the companion to language\_workarounds.md that lists what exists. |
| `enscript/references/types_collections.md` | A+ | The corrections are verified: set has no Contains, string has no StartsWith, Sort(bool reverse) is at enscript.c:493, Copy(from) exists, vector.Cross is an instance method, Math.Clamp is at enmath.c:540, and int.MIN is at enconvert.c:28. The 'reported' quirks are labeled as reported. |
| `enscript/references/widget_api.md` | A+ | 29 of the methods, classes and flags it names were checked in enwidgets.c (SetTextProportion, ElideText, SetHideText, AddChildAfter, FindAnyWidgetById, RTTextureWidget, OnModalResult, SOURCEALPHA and others), and all are present. The guidance on handlers and menus is correct. |
| `enscript/examples/07_agent_modifier.c` | A+ | Verified against modifiersmanager.c: modifiers are kept in a map by ID, the ID must be 1 or higher, AddModifier takes an instance, and on load the time value of an unknown saved ID cannot be skipped. That makes m\_TrackActivatedTime=false correct, and the file explains it well. The agent and modifier calls match playerbase.c:8102, 8115 and 8121. |
| `enscript/examples/12_menu_interactions.layout` | A+ | The format is valid, and the anchors and exact toggles are consistent. The colums spelling matches vanilla, the button offsets from right\_ref/bottom\_ref are correct, and the companion script in layouts.md is cited. |
| `enscript/patterns/persistence.md` | A+ | All citations match P: (entityai.c:2910/:2978, itembase.c:3190/:3089, playerbase.c:7353/:7408, game.c:5 GAME\_STORAGE\_VERSION=144, bottle\_base.c:7). The version-header pattern is correct. It agrees with the persistence pack (the warning about a modded PlayerBase, and false meaning a lost record), and it points to the pack for depth. Nothing concrete to fix. |
| `enscript/integrations/dabs_framework.md` | A+ | Every framework fact that was spot-checked is in P:\Mods\@Dabs Framework\addons\Scripts.pbo: 'Attempted to create layout on SERVER', 'Invalid layout file', the DF\_Scripts and DF\_GUI patches, RegisterPluginAttribute, RegisterProfileSettingSlider, Two\_Way\_Binding, Relay\_Command, ReloadAll, UseUpdateLoop, StringEvaluater, ScriptViewMenu, HidesParentMenu, GetInputExcludes and SwapItems. It is clearly scoped as third party, and it states what it could not confirm (line 55). Nothing concrete to fix. |
| `enscript/references/item_api.md` | A+ | Every cited line opened on P: matches: itembase.c:23/223/3315/3389/3416/3435/3470/3481/3486/3688/3717/3867/3883; object.c:132/981/994-1062/1105/1171/1219; entityai.c:646/882/885/2138/2293/2307-2308/2327/2442/2881/2884/3883; inventory.c:184/205/220/397/876; magazine.c:1/:38/:70; constants.c:909/913; and the food config lines. The claim about SetActions for each type matches InitializeActions and m\_ItemTypeActionsMap. The one engine behavior it cannot observe is marked as reported. Nothing concrete to fix. |
| `enscript/examples/11_hud_plain_text.layout` | A+ | It is well formed in the vanilla property format and starts at the root widget, with no BOM or comments. gui\_layout.md shows vanilla using every property and value in it (ignorepointer, halign right\_ref, valign bottom\_ref, 'exact text', 'exact text size', 'bold text', 'text halign' right/center, and the sdf\_Metron fonts). The exact-position toggles match the explanation of offsets in layouts.md. Nothing concrete to fix in the layout itself. The loading path in its companion text is covered under gui\_layout.md. |
| `enscript/examples/13_item_preview.layout` | A+ | The structure is valid. ItemPreviewWidgetClass, PanelWidgetClass with style rover\_sim\_colorable (used in vanilla camera\_tools.layout and day\_z\_book.layout), ButtonWidgetClass with styles Default and Editor, and the combinations of font, text, alignment and toggles all appear in vanilla. The widget names match the companion script in layouts.md. Nothing concrete to fix in the layout itself. |
| `enscript/README.md` | A+ | The index matches the folder: every file in patterns, integrations, references and examples is listed. The 'checked on P:' list agrees with what each file says about itself (the singleton and modded\_class markers). The cross-references in the symptom table exist: conventions/config.md T148506, the persistence section 'Adding saved fields to a vanilla class', ServerSetAmmoCount, the GetScreenPos z check, and the + "" copy. The NO\_GUI citations at dayzgame.c:1061 and missionserver.c:59 are correct. The examples not yet checked are clearly marked as vendored. Nothing concrete to fix. |
| `enscript/patterns/modded_class.md` | A+ | Every citation was opened on P:, and all are correct: particlelist.c:3-9 (a commented-out example); plugindiagmenumodding.c:8 #ifdef DOXYGEN and :21; playerbase.c:3007; itembase.c:235/246-253/261; canteen.c:1; bottle\_base.c:356; actionconstructor.c:27; plugindiagmenu.c:29; enwidgets.c:107-110/189/381/656; uimanager.c:4-10/59/62/117/154; uiscriptedmenu.c:66; inventorymenu.c:8; enscript.c:117; gameplay.c:637; ingamehud.c:1/1141; defines.c:29/34; chat.c:14; dayzgame.c:1061; missionserver.c:59; and DZ\gear\containers\config.cpp:3/19. A grep confirms that vanilla compiles no modded class. Claims about native behavior are marked as reported. Nothing concrete to fix. |
| `enscript/patterns/actions.md` | A+ | Every cited line was checked on P:, and each one holds: actionbase.c:51/245/441/951/954, actionconstructor.c:3, actionmanagerbase.c:214, the re-check at actionmanagerserver.c:168, itembase.c:255-262/295, the logging gates in debug.c and constants.c:256, the IsTakeable checks in actiontakeitem.c:36 and actiontakeitemtohands.c:38, the three PowerGeneratorStatic overrides, and the base-class lines. The table of condition components matches all eight files exactly, including CCINotRuinedAndEmpty meaning quantity > 0 and CCINone also overriding CanContinue. ActionDrink is an ActionConsume. Nothing concrete to fix. |
| `enscript/patterns/singleton.md` | A+ | The citations are correct: defines.c:106 ('Only defined when CGame.IsDedicatedServer') and :112-115 (#define SERVER); jsonfileloader.c:7 LoadFile and :42 SaveFile, both returning bool with errorMessage; and :104-105 'use JsonFileLoader::LoadFile instead'. The deprecated JsonLoadFile does only an ErrorEx. The `ref array<string> X = {};` field initializer has a vanilla precedent (worldsmenu.c:16). The rules for JsonSerializer and static teardown are marked as reported, not checked, because the serializer is native. The code resets cfg after a failed load. Nothing concrete to fix. |
| `enscript/references/gui_layout.md` | A+ | A script checked 92 of its citations against P:, and all matched. These cover every 'first vanilla use' file:line for the widget classes, the script types and methods in enwidgets.c and gameplay.c (TextListbox AddItem/SetItem/GetItemText and BaseListbox members, and ItemPreview/PlayerPreview members), the property examples, the colums lines and the first uses of fonts. The value lists are the complete vanilla sets: mode blend/additive/opaque; clamp mode clamp/border/wrap/invalid; stretch mode stretch\_w\_h/fit\_w\_center/none/invalid; fixaspect fixwidth/inside/outside/none; priority 0..4000; and text valign center only. Nothing concrete to fix. |
| `enscript/examples/02_custom_action_singleuse.c` | A+ | Every cited line is correct: actionsingleusebase.c:1/:29; actionbase.c:51/245/259/441/954; animatedactionbase.c:179/183; itembase.c:3315/3486/246-253/255-262; playerbase.c:5773, where RPC\_USER\_ACTION\_MESSAGE leads to MessageAction; and actionconstructor.c:3-27. actionmanagerserver.c:168 calls Can(), which reaches ActionCondition at actionbase.c:954. All the identifiers exist: CMD\_ACTIONMOD\_EAT, CCINonRuined, CCTNone, m\_StanceMask and m\_Text. The code follows the shape of the vanilla ActionTurnOnWhileInHands, and it puts SetActions in the item's own declaration, as modded\_class.md requires. Nothing concrete to fix. |
| `enscript/examples/03_continuous_action.c` | A+ | It mirrors ActionCraftArmband line for line (CMD\_ACTIONFB\_CRAFTING at :14, m\_FullBody, STANCEMASK\_CROUCH, CCINonRuined and CCTSelf at :23-24, and HasTarget false). Every cited line holds: actioncontinuousbase.c:1/120/208/228/289, cacontinuoustime.c:1 and :9, object.c:1001 GetHealth01, object.c:1105 SetHealthMax and playerbase.c:5773. The registration steps are correct. Nothing concrete to fix. |
| `enscript/examples/10_modded_playerbase.c` | A+ | The citations hold: playerbase.c:359-364 (the constructor calls Init, where vanilla registers its own net-sync variables); :6733 GetItemInHands; :2042 GetStaminaHandler; staminahandler.c:1081 GetStamina; and bloodregen.c:14 GetHealth("GlobalHealth","Blood"). The stated ranges match vanilla: STAMINA\_MAX 100, SL\_ENERGY\_MAX 5000 and blood 5000. The APIs all exist (GetSingleAgentCount, eAgents.FOOD\_POISON, GetStatEnergy, m\_StaminaHandler, EnumerateInventory with INORDER, MessageAction), and the overridden signatures match playerbase.c. SetSynchDirty runs only when the flags change, the synced field is not saved, and the warning about saved fields on a vanilla class is present. Nothing concrete to fix. |
| **Hooks** | | |
| `hooks/hooks.json` | A+ | The plugin hook wiring matches .claude/settings.json and uses ${CLAUDE\_PLUGIN\_ROOT}. Each hook has a timeout. test\_paste\_router and test\_plugin\_copy cover both wirings. |
| `hooks/test_plugin_copy.py` | A+ | It covers the plugin copy standing aside for the project copy for all three hooks, both alone and when shadowed. |
| `hooks/edit_check.py (+ test_edit_check.py)` | A+ | The PostToolUse output format is correct, and the hook exits silently if the checker itself fails. Messages give the file, the line and the fix. The tests are thorough and pass. A run on 208 vanilla config.cpp files and 228 vanilla .layout files from P:\ flagged none of them. |
| `hooks/scope_guard.py (+ test_scope_guard.py)` | A+ | The PreToolUse deny output is correct, and the reason tells Claude what to do. The gap for shell commands is documented. The hook covers mod folders created after the scope was set, all forms of P: paths and corrupt state files, and the tests pass. |
| `hooks/paste_router.py (+ test_paste_router.py)` | A+ | All 141 tests across the hook and the importer pass. A branch link that contains a slash stays whole, and GitHub's own pages, pull requests and gists get no suggestion. The hook's text about where each kind of link ends up matches import\_mod.py, which asks git ls-remote for the branch and links a subfolder from its own clone. The suggested --name follows the importer's naming rule. |
| **Search server and panel** | | |
| `dayz-rag MCP server (server.py, voyage_common.py, README, tests)` | A+ | Nothing concrete to fix. All three tools carry readOnlyHint, and search also carries openWorldHint. The tool descriptions are clear, and errors are raised so that FastMCP returns them as isError results. The P: path check is lexical and documented, the cache is cleared when the index is rebuilt, and transient Voyage errors are retried with a client timeout. The README matches the code (.mcp.json, enabledMcpjsonServers, the plugin.json mcpServers block and cost-and-free-tier.md). All server and voyage\_common tests pass, including the check that the file-type list matches the indexer. |
| `mods/agentic-z-panel (plugin.json, hooks.json, register.tsx, register.test.tsx, types)` | A+ | `claude plugin test mods/agentic-z-panel` passes 18 of 18. The argv of every button matches its script's argparse definition: gate.py build/ingame <mod>; launch.py modnames; deploy.py and build.py modname; health.py takes a bare mod and inserts 'show' itself; release\_pack.py mod; workbench --mod; logwatch --since/--duration/--mod; and ask.py exits with code 1 on NONE, which the panel shows as 'nothing found'. The run timeout of 600 s covers the gate's 300 s plus the 30 s in-game wait. The plugin cache path matches the marketplace name dayz-n-chill/agentic-z, and the versions in plugin.json and marketplace.json both read 0.3.0. The README table and the note that the panel runs only on Windows match the code. The lock is taken before any await, and the test\_repo\_integrity test checks the button scripts. Nothing concrete to fix. |
| **Answer tests (evals)** | | |
| `evals/baseline.json` | A+ | It has one entry per question file, and test\_shipped\_baseline\_\* enforces that. |
| `evals/fixtures/dayz-layout-validator/*.layout` | A+ | The fixtures match the 'unchanged' lists in the questions, and the clean fixture follows the format of the vanilla day\_z\_connection\_lost.layout. |
| `evals/questions/dayz-ai-specialist.json` | A+ | Every verified citation resolves on P:\ to the cited symbol (eagents, CfgAIBehaviours, noise.c and others). |
| `evals/questions/dayz-animation-specialist.json` | A+ | The citations were verified: fence.c:12, camping config 4450, and barrel\_colorbase.c:21/148. |
| `evals/questions/dayz-asset-specialist.json` | A+ | The citations were verified (hoodie.rvmat:15). |
| `evals/questions/dayz-audio-fx-specialist.json` | A+ | The citations were verified (sounds/hpp config, object.c:1273, particlelist.c). |
| `evals/questions/dayz-config-specialist.json` | A+ | The citations were verified (GlowPlug at parts config 822/831, DZ\_Characters\_Vests at :3, PlateCarrierVest at :24). |
| `evals/questions/dayz-layout-validator.json` | A+ | The citations were verified against a vanilla layout, and the fixtures are protected with 'unchanged'. |
| `evals/questions/dayz-mod-reviewer.json` | A+ | The citations were verified. |
| `evals/questions/dayz-object-builder.json` | A+ | The citations were verified (building.c:27, actionopendoors.c:40). |
| `evals/questions/dayz-persistence-specialist.json` | A+ | The citations were verified (GAME\_STORAGE\_VERSION = 144 at game.c:5, combinationlock.c:160). |
| `evals/questions/dayz-physics-specialist.json` | A+ | The citations were verified. |
| `evals/questions/dayz-script-specialist.json` | A+ | The citations were verified. |
| `evals/questions/dayz-vehicle-specialist.json` | A+ | The citations were verified (transport.c, carscript.c:1752, CfgSlots). |
| `evals/questions/dayz-weapon-specialist.json` | A+ | The citations were verified (cz527.c, Mag\_CZ527\_5rnd, Slot\_weaponOpticsLRS). |
| `evals/questions/dayz-wearables-specialist.json` | A+ | The citations were verified (ENVIRO\_ISOLATION\_WETFACTOR\_DRENCHED, noHelmet). |
| `scripts/dev/test_run_evals.py` | A+ | 31 tests cover validation, scoring, detection of unchanged files, the baseline gate and the shipped files, including 'verified'. |
| `evals/README.md` | A+ | It is accurate: 23 question files and 7 named uncovered agents add up to the 30 agents. The runner, the format document and the scoring rule are all linked correctly. |
| `scripts/dev/run_evals.py` | A+ | It applies least privilege: read-only tools are allowed, and the edit, shell, Agent and web tools are explicitly denied. The question is sent on stdin, files listed as 'unchanged' are checked by hash, and question files are validated. The baseline can only stay the same or rise, and results go to output/. It has tests. |
| **Scripts and repository tests** | | |
| `scripts/dev/evals.bat, clean-repo.bat, docs-sync.bat` | A+ | These are thin wrappers. The targets exist, and the usage comments match the CLIs. |
| `scripts/setup/preflight.bat, workdrive.bat, setup-objectbuilder.bat, statusline.bat, sync-skills.bat` | A+ | The targets exist, and the documented flags (--path, --unmount, --remove, --status) exist in the scripts. |
| `scripts/dayz/*.bat (the other 35 wrappers: add-scaffold, add-server, ask, balance, build-imageset, build-pbo, clean-workspace, conflict-check, cot-bootstrap, deploy-pbo, gate, health, import-mod, launch-test, layout-preview, lint, logwatch, new-mod, objectbuilder, p3d-audit, pack-texture, recipe, release-pack, route, scope-mod, search-download, search-index, server-kit, status, stop-test, triage, types-edit, types-split, upgrade-guard, workbench)` | A+ | Every target script exists. The usage lines that were checked match the argparse definitions: gate build/ingame/behavior/visual, health record, objectbuilder --file/--mod, and workbench --mod/--gproj. |
| `scripts/README.md` | A+ | Every .bat file in scripts/dayz, scripts/setup and scripts/dev is listed, and every listed file exists (a script checked both directions). The integrity test confirms that each wrapper's target exists. The examples match the scripts' command lines; for example, health.bat MyVest works because health.py inserts 'show'. Nothing concrete to fix. |
| `scripts/dayz/dayz-search.bat` | A+ | It is a thin wrapper. It uses setlocal plus PYTHONIOENCODING=utf-8 so that redirected output does not crash on non-ASCII text. The target is found relative to the script folder and checked by the integrity test, and all arguments are passed on. Nothing concrete to fix. |
| `scripts/setup/agentic-z-update.bat` | A+ | The relative target is correct (..\..\.claude\skills\agentic-z-update\update.py, checked by the integrity test). It uses setlocal plus UTF-8 output and passes all arguments on. Nothing concrete to fix. |
| `scripts/dev/test_repo_integrity.py` | A+ | All its tests pass, including test\_cited\_vanilla\_lines\_exist\_on\_p, which ran because P: is mounted (no skip). The docstring matches what the file checks. The read-only, no-write and memory rules match the subagent documentation (memory turns on Write and Edit). The citation and exemption lists check themselves for stale entries. The panel SKILL map is parsed, so a renamed script fails CI. The grader checked the references outside .md files that the test does not scan (.c, .json and .layout files under .claude/skills, scripts/, hooks/ and mods/). The only unmatched ones are paths relative to a mod, such as scripts/4\_World/Vest.c, so the gap does not hide a dead link. Nothing concrete to fix. |
| `scripts/dayz/dayz-search.py` | A+ | All 29 tests pass, and a live query returned real hits whose files exist on P:. Every error path prints one clear line and exits with code 2, including -k 0, an empty query, a missing index and an invalid key. The help for -s matches the server's cap of 1500 characters. When no file\_hashes.json exists, the run explains why every hit shows as stale. |
## How the grading works

Separate AI reviewers set every grade; the author does not. The reviewers grade each agent, skill and shared file against Anthropic's published best practices for Claude Code. Each reviewer is a new Claude instance started for the task. A reviewer sees the files, the rubric and the standards, but never the earlier grades or the author's opinion. This is not an official Anthropic rating. It is a repeatable review that anyone can run again with the prompts below.

The final grade count opens the "Quality by version" section.

### Who grades

- Each round starts new, independent Claude reviewers with no memory of earlier rounds. The final review used six reviewers: two for the agents, three for the skills and one for all shared items. The shared items are the hooks, the search server, the panel, the scripts and wrappers, the answer tests, the rules files, the specialist reference files and this method note. For the files that were not graded, see "Files not graded" under "Open items and decisions".
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

The 90 shared items are neither agents nor skills, so reviewers judge each type of item by its own purpose.

| Item type | What the reviewer checks |
| --- | --- |
| Hooks | The output JSON is correct for the hook event, a bug in a hook never blocks the session, the plugin wiring matches the clone wiring, and the tests pass hook input through stdin. |
| Search server | Every tool carries read-only annotations, tool descriptions are clear, errors return as `isError` results, and tests cover the tools. |
| Panel plugin | The plugin manifest and hook wiring follow the plugins reference, and the plugin's own tests pass. |
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
.claude/mcp/dayz-rag/, the panel plugin in mods/agentic-z-panel/, every wrapper
in scripts/, the answer tests in evals/, the rules files and every specialist
and Enforce Script file under .claude/skills/_shared/. Hooks: correct output JSON for the event,
never block on their own bug, tests through stdin. MCP server: read-only
annotations, clear tool descriptions, errors returned as isError, tests. Panel:
follows the plugins reference, its tests pass. Rules files: every rule true of
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
item graded (agents, skills, hooks, search server, panel, rules files,
specialist files, scripts, answer tests and this note); that it gives the
grading prompt for every kind; and that every count matches final_grades.json
and final_grades_shared.json. Scale A+
to D. A+ means nothing concrete left to fix. For anything lower, name a
concrete defect a reader would actually hit.
Output a table: Item | Grade | Why | To reach A+.
```

Each run uses a new reviewer, so two runs can word their findings differently, and a stricter reviewer can find a new edge case. This is by design. Every round found real bugs, and each one is listed in "Real bugs the grading found and fixed".
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
| Smaller rules loading | The DayZ rules core is 143 lines, and each of the five topic files is 24 to 56 lines (see The three tiers every agent works from). Most skills read only the core, which is 40% less than the old 239-line file. `/dayz-deploy-pbo` and `/dayz-gate` also read the bundle mods section of the config topic file. An agent that reads one topic file loads 17% to 30% less than before. With two topic files, the result depends on the pair. The mod debugger (226 lines) and the mod architect (231 lines) still read slightly less. The vehicle, weapon, and audio and FX specialists (251 lines) read more, as does the mod reviewer with three topic files (283 lines). |
| Panel and wrappers | A `.bat` wrapper for every runnable skill runs its script directly. For the panel, see What Agentic-Z gives an AI agent. |
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
| Live DayZ checks | Still outstanding. Nothing in this build has run against a live DayZ session. This includes the team loop, the in-game, behavior and visual gates, and the panel's launch buttons. | Build one small mod end to end with DayZ running on the user's PC. The user will be asked before this runs. |
| Answer tests for seven agents | The build checker, in-game tester, architect, lead, orchestrator, router and Figma to layout agent have no question file yet. | Write their question files and record a baseline. |
| Files not graded | Nine answer test files, `expansion_style.md`, `examples/layouts.md` and the nine `enscript-style/` section files have no grade yet. | Grade them in the next independent round. |
| Preflight exception list | `docs/dayz-modding.md` still lists five, which no longer matches the DayZ rules file (see The skills). | Bring `docs/dayz-modding.md` in line with the rules file. |
| RAG search | The installed plugin (1.6.0) has the search timeout bug. The fix is in the current Agentic-Z. | The updated plugin, a Voyage API key in `.env`, and a full re-index. |

### Roadmap

1. **Live DayZ checks.** See Open items and decisions.
2. **Answer tests for the last seven agents.** See Open items and decisions.
3. **Grade the files not yet graded.** See Open items and decisions.
4. **Add-ons plugin.** An optional `agentic-z-addons` plugin for outside tools. It will be built only after the core is complete, and only for the add-ons the user names.

## Real bugs the grading found and fixed

Each was covered by a test after the fix (method in How the grading works).

| Bug | Effect | Found in |
| --- | --- | --- |
| Search tools missing after install | Agents installed from the plugin had no RAG search tools. | v1.7.0 |
| Cleanup could delete your mod | `/dayz-clean-workspace` could delete a mod cloned in by hand, including its git history. | v1.7.0 |
| Update included unrelated changes | `/agentic-z-update` could add unrelated staged changes to its own commit. | v1.7.0 |
| Index download never worked | `/dayz-search-download` looked for a file name that no release uses. | v1.7.0 |
| RAG skipped large classes | About 39% of the code in large script classes such as PlayerBase was never searchable. | v1.7.0 |
| Server could not find split types | `/dayz-split-types` pointed the economy at the wrong folder and loaded entries twice. | v1.7.0 |
| Failed build blocked rebuilds | A single failed first build caused every later build to refuse to run. | v1.7.0 |
| Line endings broke updates | On Windows, every upstream change appeared as a local edit. | v1.7.0 |
| Port already in use | A second test session connected to the old server instead of failing with a clear error. | v1.7.0 |
| Old textures and atlases counted as new | A stale `.paa` from an earlier run was reported as newly built. | v1.7.0 |
| Wrong project used | With two Agentic-Z projects on one machine, a skill could work on the other project's workspace. | v2.0.0 |
| UI styles left out of the PBO | `/dayz-build-pbo` did not pack `.styles` files, so menus that use them shipped without their styles. | v2.0.0 |
| Server-only mods sent to clients | `/dayz-launch-test` had no way to keep a server-only mod off the client. | v2.0.0 |
| Lint blocked valid mods | `/dayz-lint` failed builds on findings that do not stop a mod from loading. | v2.0.0 |
| Unsafe names in the behavior gate | A crafted instance or template name could point the behavior test outside its folder. | v2.0.0 |
| Spec written into an import | Running `/dayz-init` again could write `spec.md` into an imported, linked mod. | v2.0.0 |
| Balance compared the wrong items | `/dayz-balance` missed mod overrides of a vanilla class with the same name. | v2.0.0 |
| Upgrade guard missed changes | `/dayz-upgrade-guard` missed inherited members and config keys written in a different case. | v2.0.0 |
| Conflict check refused linked mods | `/dayz-conflict-check --ingame` refused `@mods` that were links. | v2.0.0 |
| Requests routed to the wrong owner | `/dayz-route` sent spawn and modded class requests to object specialists instead of their owners. | v2.0.0 |
| Incorrect vanilla facts in the new packs | The vehicle, wearables, audio, AI and animation packs had incorrect line citations and class facts. All were corrected against P:. | v2.0.0 |
| Gates kept memory | The read-only gates had a memory folder, which a gate that only judges should not have. | v2.0.0 |
### What we take and what we leave

| Decision | Items |
| --- | --- |
| Build new | Persistence, base building, data audit, vehicles, aviation, weapons, clothing, characters, proxy alignment, doors, physics, sound, AI patterns, animation pipeline, `/dayz-lint`, layout preview, answer tests. |
| Keep ours | Preflight, p3d audit, particles, PBO build, in-game testing, mod workflow, the DayZ rules and script style (the pack copied these from Agentic-Z), and the CLAUDE, AGENTS and GEMINI files. |
| Expand ours | Script reference, UI development, texture pipeline, model pipeline, and a spec step before building. |
| Later | Blender animation and assembly, UV atlas, 3D viewer, p3d inspector, model preflight, animation format checkers, and vehicle proxy checks. |
| Do not take | Racing-game vehicle rips, PBO reverse engineering, scraped notes and Discord dumps, the pack's MIT label, copied Expansion or VPP code, AI 3D generators, and the pack's bookkeeping system. |

For the status of in-game testing, see Open items and decisions.

## What changed from Agentic-Z 1.6.0

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

## The three tiers every agent works from

When two tiers disagree, the more specific tier wins. No tier repeats another.

| Tier | What it holds | When it loads |
| --- | --- | --- |
| 1 · Repo rules | How every agent works: communication, tooling, memory and routing. Defined in `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`. | For every agent and every task |
| 2 · DayZ rules | Enforce Script style, config and asset rules, the environment, and vanilla search. Defined in `dayz-conventions.md` plus topic files for config, assets, scripts, UI and server. | For all DayZ work |
| 3 · Agents and reference files | The 30 agents, the 44 skills, and the reference files under `.claude/skills/_shared/`. | Only when the task needs them |

## The agents

Agentic-Z has 30 agents. "New" marks an agent added since version 1.6.0.

| Agent | Role | Change since 1.6.0 |
| --- | --- | --- |
| **Plan** | | |
| Mod orchestrator | Plans the mod with the user, splits it into small tasks, assigns them to leads, runs the gates and tracks completed work. | New |
| Mod architect | Plans the classes, files, assets and behavior checks before work starts. | New |
| Lead (one agent, six teams) | Runs one team: script, config, art, UI, server or release. Splits its share of the work into worker tasks and checks that the results fit together. | New |
| **Workers** | | |
| Script engineer | Writes Enforce Script: modded classes, RPCs and game logic. | Kept |
| Workbench plugins | Builds tools inside Enfusion Workbench. | Kept |
| Config engineer | Writes config.cpp, class inheritance and hidden selections. | Kept |
| Object Builder | Sets up .p3d models, LODs, selections and doors. | Kept |
| Textures and materials | Handles .paa textures and .rvmat materials. | Kept |
| UI engineer | Builds .layout files and the scripts that drive them. | Kept |
| Figma cleaner | Prepares a Figma frame for conversion. | Kept |
| Figma to layout | Converts the prepared frame into a DayZ .layout, and repairs a layout that failed validation. | Kept |
| Server admin | Manages types.xml, init.c and server settings. | Kept |
| Map builder | Handles Terrain Builder and DayZ Editor work. | Kept |
| Build engineer | Runs the build, test server and launch skills (Haiku). | New |
| Docs writer | Keeps the mod's README, changelog and classname list up to date (Sonnet). | New |
| **Specialists** | | |
| Saving data | Saving data across restarts, save versions, base building, and a data audit before release. Works under the script lead; for the data audit, works under the server lead. | New |
| AI | Infected, animals and human AI such as patrols and guards, written from scratch. Works under the script lead. | New |
| Vehicles | Cars, boats and helicopters: engine, gearbox, wheels, doors, fluids, seats and damage. Works under the config lead. | New |
| Weapons | Weapons, magazines, ammunition, attachments, recoil and fire modes. Works under the config lead. | New |
| Wearables | Clothing, characters, inventory slots, protection, color variants and proxies. Works under the art lead. | New |
| Animation | model.cfg animations, RTM files and the handoff to Blender. Works under the art lead. | New |
| Audio and FX | Sound shaders, sound sets and particle effects. Works under any lead that needs it. | New |
| Physics | Weight, collision LODs, dropping, throwing and contact. Diagnoses problems and hands the fix to the owner, and never edits files. Works under any lead. | New |
| **Support** | | |
| Router | Low-cost Haiku agent behind `/dayz-route`. | New |
| Agent creator | Writes new agent files and checks them against the agent standard. | Kept |
| **Gatekeepers (read only)** | | |
| Mod reviewer | Checks the mod against the DayZ conventions and returns PASS or FAIL. | Kept |
| Layout validator | Checks a `.layout` against the Figma-to-DayZ rules without editing it. It serves as the UI gate. | Kept |
| Build checker and in-game tester | Act as fallbacks when `/dayz-gate build` or `/dayz-gate ingame` itself fails. | New |
| Debugger | Reads the logs for errors that triage does not recognize, and names the cause and the owner. | Moved |

## The skills

Agentic-Z provides 44 slash commands that any agent or person can run. Of these, 40 ship in the plugin and four are available in clones only. Of the 40 plugin DayZ skills, 18 check the environment first with `/dayz-preflight`, which is itself the check. The DayZ rules file has 14 exception entries naming 21 skills, each with its reason. `/dayz-particles` is a reference skill with no script.

Some exempt skills still read P:. `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe`, `/dayz-layout-preview` and `/dayz-upgrade-guard` only read files and write a report, and `/dayz-ask` only checks that P: is mounted. `/dayz-gate` runs its checks through the scripts it calls. `/dayz-stop-test` skips the check so that it still works as an emergency stop.

| Skill | What it does |
| --- | --- |
| **Setup** | |
| `/dayz-init` | Runs a setup wizard on first use, with an optional spec step, and then serves as a status hub for the active mod. |
| `/dayz-preflight` | Checks the P drive, DayZ Tools, vanilla data and the Workshop link. |
| `/dayz-workdrive` | Mounts the P drive after a reboot without opening DayZ Tools. |
| `/dayz-setup-objectbuilder` | Configures Object Builder on a new machine. |
| **Mods** | |
| `/dayz-new-mod` | Creates a new mod with the standard folders and files. |
| `/dayz-import-mod` | Brings an existing mod folder or a GitHub repository into the workspace. |
| `/dayz-add-scaffold` | Adds missing standard pieces to an existing mod. |
| `/dayz-recipe` | Starts a plan from a recipe (new weapon, new vest or new craftable item) for the architect to complete. |
| `/dayz-scope-mod` | Restricts editing to one mod. |
| `/dayz-clean-workspace` | Removes the mods it created and their builds. |
| **Build** | |
| `/dayz-lint` | Finds errors that would prevent a mod from loading, before packing. Runs first inside the build gate and `/dayz-build-pbo`. |
| `/dayz-build-pbo` | Packs a mod into a PBO with AddonBuilder. |
| `/dayz-deploy-pbo` | Copies prebuilt PBOs and keys into place without AddonBuilder. |
| **Test** | |
| `/dayz-add-server` | Sets up a local test server instance. |
| `/dayz-launch-test` | Starts a diag server and client with the selected mods. |
| `/dayz-stop-test` | Stops the test session. |
| `/dayz-cot-bootstrap` | Grants admin rights in Community Online Tools on the test server. |
| `/dayz-logwatch` | Watches the logs during a test session and triages each new error as it appears. |
| **Checks, routing and status** | |
| `/dayz-gate` | Runs the build, in-game, behavior and visual checks as scripts that print PASS or FAIL, with known-error triage. |
| `/dayz-conflict-check` | Finds prefix, path and class collisions with CF, COT and Expansion. |
| `/dayz-upgrade-guard` | After a DayZ update, lists mod classes whose vanilla parent classes changed. |
| `/dayz-balance` | Compares item stats with similar vanilla items and flags outliers. |
| `/dayz-health` | Produces a page for each mod with the last build, last test, open findings and gate history. |
| `/dayz-route` | Shows which skill, specialist or team should handle a request. |
| `/dayz-statusline` | Installs a status line that shows P:, the active mod, DayZ Diag and index age. |
| **Art and UI** | |
| `/dayz-pack-texture` | Converts images to `.paa` and checks their suffixes. |
| `/dayz-build-imageset` | Packs UI sprites into an imageset. |
| `/dayz-layout-preview` | Renders a `.layout` as PNG images at several screen sizes and flags widgets that fall off screen. |
| `/dayz-p3d-audit` | Finds collision, physics and structure problems in models. |
| `/dayz-particles` | Provides reference material for making particle effects without Workbench. |
| `/dayz-launch-objectbuilder` | Opens Object Builder on a model. |
| `/dayz-launch-workbench` | Opens Workbench on a mod's project. |
| **Server economy** | |
| `/dayz-edit-types` | Adds, changes, removes or merges `types.xml` entries. |
| `/dayz-split-types` | Splits one large `types.xml` into 19 category files. |
| **Release** | |
| `/dayz-release-pack` | Writes the Workshop description, a changelog entry, the classname list and installation notes for server owners. |
| `/dayz-server-kit` | Packages types.xml entries, cfgeconomycore lines, the load order and the public key into a ZIP file for server owners. |
| **RAG search** | |
| `/dayz-search-index` | Builds the game files index. |
| `/dayz-search-download` | Downloads a prebuilt index instead. |
| `/dayz-ask` | Answers a plain-English question about vanilla DayZ with verified path:line citations. |
| **Team and repository** | |
| `/dayz-record-correction` | Turns a user correction into a team rule. |
| `/sync-skills` | Links the skills into Claude Code, Codex and Gemini (clones only). |
| `/agentic-z-update` | Pulls template updates into a clone (clones only). |
| `/docs-sync` | Keeps the documentation wiki in line with the source files (clones only). |
| `/clean-repo` | Runs a cleanup across every domain of the repository (clones only). |

The side panel is a separate plugin, not a skill. See What Agentic-Z gives an AI agent.
### Specialist workflows

Every task follows the team loop described in How one task moves through the team. Within that loop, each specialist works through its own steps, listed in the table below. Specialists that write DayZ content look up vanilla first. They use Grep for a class or symbol name they already know, and RAG search for questions by meaning or after two or three failed Grep searches. They then read the real file before relying on any hit. The build engineer, the docs writer, the build checker, the in-game tester and `figma-node-normalizer` have no RAG tool. They work from the mod, its logs or the Figma file.

| Agent | Steps |
| --- | --- |
| **Script lead** | |
| `dayz-script-specialist` | 1. Searches the vanilla scripts for the class it will change and reads the real file. 2. Writes a `modded class` in the correct layer (3\_Game, 4\_World or 5\_Mission) and calls `super`. 3. Adds RPCs only where the client and server must communicate, and checks which side runs each line. 4. `/dayz-lint` and the build gate check and pack the code. Neither compiles Enforce Script, so the in-game gate catches compile errors and reads script.log. |
| `dayz-workbench-specialist` | 1. Reads how vanilla Workbench plugins are registered. 2. Writes the plugin script and its tool panel. 3. Never opens Workbench itself. Instead, it tells the user to open it with `/dayz-launch-workbench --mod <ModName>`. 4. Returns the plugin and the steps to load and run it. |
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
| `dayz-build-checker` | 1. Runs only when `/dayz-gate build` itself fails. 2. Reads the AddonBuilder output and names the failing file. |
| `dayz-ingame-tester` | 1. Runs only when `/dayz-gate ingame` itself fails. 2. Reads the logs from the test session and reports what failed. |
| `dayz-mod-debugger` | 1. Receives only new errors that triage does not recognize. 2. Traces script.log, RPT and crash files back to the line that failed. 3. Reports the cause, evidence, location and fix to its caller (the orchestrator or a lead), and names the worker agent that owns the fix. |

### How one task moves through the team

1. The user approves the mod plan from the architect, for example "a tactical vest with three retextures".
2. The orchestrator splits the plan into tasks, such as "write the vest's config.cpp entry".
3. The appropriate lead takes the task and starts a worker.
4. The worker searches vanilla and checks the real file, reads the reference files that the task needs, and completes that one task.
5. The work then passes through the gates described in The team flow. If anything fails, a known error returns with its fix already named, and the debugger reads the logs for any new error. The task then goes back to the worker with notes.
6. Work that passes is packed into a PBO and loaded on a test server.
7. The user gives the final approval and publishes the mod to the Steam Workshop with DayZ Tools Publisher.
