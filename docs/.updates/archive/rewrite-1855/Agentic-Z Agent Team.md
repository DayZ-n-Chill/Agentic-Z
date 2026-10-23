Agentic-Z Agent Team

Agent team · October 2026

# Agentic-Z

The Agent Team

Agentic-Z 2.0.0 puts 30 agents and 44 skills to work as one modding team.

Agentic-Z · DayZ n' Chill · github.com/DayZ-n-Chill/Agentic-Z

# Agentic-Z Agent Team

Agentic-Z 2.0.0 is the DayZ modding reference, delivered as a Claude Code plugin and repo template. It ships 30 agents in `.claude/agents/` and 44 skills in `.claude/skills/`. It also ships three hooks and the `dayz-rag` MCP search server. Version 2.0.0 is on `develop`, and `main` carries 1.6.0. The team runs like a real studio. You approve a plan, and `dayz-orchestrator` splits it into tasks. Then `dayz-lead` hands each task to a worker, and the gates return PASS or FAIL. Nothing is published until you give final approval.

## Contents

- [Architecture](#architecture)
- [Components](#components)
- [Grades by version](#grades-by-version)
- [Limits](#limits)
- [Token savers and workflows](#token-savers-and-workflows)
  - [Token savers](#token-savers)
  - [Workflows](#workflows)
  - [Paste-in inputs](#paste-in-inputs)
  - [Build](#build)
  - [Maintenance](#maintenance)
  - [Server owners](#server-owners)
  - [Roadmap](#roadmap)
- [Domain specialists](#domain-specialists)
  - [Build order](#build-order)
  - [Scope decisions](#scope-decisions)
- [Version comparison](#version-comparison)
- [Rule tiers](#rule-tiers)
- [Agents](#agents)
- [Skills](#skills)
- [Specialist workflows](#specialist-workflows)
- [Task lifecycle](#task-lifecycle)

## Architecture

You
Planning
Team leads
Workers (one per task)
Gatekeepers

\*[diagram]\*

The gates run in a fixed order. `dayz-lead` runs `dayz-mod-reviewer` on every task and `dayz-layout-validator` on every `.layout` change. Once per wave, `dayz-orchestrator` runs the build gate, then the in-game gate, and then the behavior gate when the plan lists behavior checks. These gates run one at a time because there is only one mod folder and one test session. Workers run in parallel only when their tasks touch different files.

## Components

Here is everything Agentic-Z 2.0.0 adds to a Claude Code session, with one row per component. Agents, skills and rule tiers each have their own section below.

| Component | Implementation and effect |
| --- | --- |
| Search | |
| --- | --- |
| RAG search: game files | `search_dayz_source` is a tool in the `dayz-rag` MCP server. It searches an index of the vanilla DayZ files on P: (scripts, configs, layouts, materials and economy XML). Voyage AI code embeddings build the index, and LanceDB stores it. Agents find vanilla code by meaning ("how does food spoil") instead of guessing class names. |
| File lookup | `get_dayz_file` returns an exact file and line range on P: and refuses any path outside it. Agents use it to read the full file behind a search hit. |
| Plain English answers | `/dayz-ask` answers a plain English question about vanilla. It falls back to keyword search when there is no index or no key. |
| Prebuilt index | `/dayz-search-download` pulls a prebuilt index from GitHub. A fresh install gets search without spending Voyage credits on embedding. |
| Agent team | |
| Orchestrator and leads | The team leaders are `dayz-orchestrator` (the main session), `dayz-mod-architect`, and a `dayz-lead` for each of six teams. You describe a mod once and approve a plan. The team then splits and tracks the work. |
| Workers and specialists | There is one agent for each area of DayZ: script, config, models, textures, UI, maps, server and Workbench. Eight domain specialists work alongside them. See "Agents". |
| Gates | The gates are `dayz-mod-reviewer`, `dayz-layout-validator`, and the build, in-game and behavior gates in `/dayz-gate`. Each one returns PASS or FAIL. Work reaches you only after it builds and loads in game with clean logs. When the plan lists behavior checks, the work must also pass the behavior gate. |
| Router | `/dayz-route` tries keyword rules first. Next it uses TypeSafe's Jev when `TYPESAFE_API_KEY` is set, and then the Haiku `dayz-router` agent. Most requests reach the right handler without spending any model tokens. |
| Figma pipeline (optional) | `figma-node-normalizer`, `figma-to-dayz-layout` and `dayz-layout-validator` turn a Figma frame into a checked DayZ `.layout`. The pipeline stays unused without a Figma input. |
| Agent creator | `agent-creator` writes agent files and checks them against the standard template and rules. |
| Rules and learning | |
| Rule tiers | There are three tiers: repo rules, DayZ rules, and then the agents. The more specific tier wins, and no file repeats another. See "Rule tiers". |
| Corrections become rules | `/dayz-record-correction` drafts a rule from your correction and saves it once you approve. A mistake you correct once is then corrected for the whole team. |
| Agent memory | Of the 30 agents, 19 set `memory: project`. They keep notes on the project's decisions in the project's own `.claude/agent-memory/` folder, wherever it is cloned. The gates, `dayz-lead` and `dayz-router` keep no memory. |
| Hooks (`hooks/hooks.json`). Each hook exits silently on its own errors, so a hook bug never blocks the session. | |
| Edit check | `hooks/edit_check.py` is a PostToolUse hook on `Edit`, `Write` and `MultiEdit`. It checks the syntax of `config.cpp` and `.layout` files. When it finds a problem, it returns `{"decision": "block"}` with each `file:line`. The agent then fixes a missing `;` or `}` in the same turn, before a build fails on it. |
| Scope guard | `hooks/scope_guard.py` is a PreToolUse hook. It denies edits to other mods while `/dayz-scope-mod` is set. |
| Paste-in router | `hooks/paste_router.py` is a UserPromptSubmit hook. It sends crash logs to triage and `types.xml` chunks to a checked merge. Figma and GitHub links go to their own workflows. |
| Safety | |
| Permission lists | `.claude/settings.json` ships 26 allow rules and 11 deny rules, and every agent has an explicit `tools` list. Agents can run the repo's own skills. They cannot run inline code (`python -c`, `node -e`) or new installs (`npm install`, `npx`). |
| Read-only gates | `dayz-mod-reviewer`, `dayz-layout-validator`, `dayz-build-checker`, `dayz-ingame-tester` and `dayz-mod-debugger` cannot edit files. `dayz-lead` and `dayz-physics-specialist` have no write tools. The agents that judge the work cannot change it. |
| Platforms and distribution | |
| Three AI tools | `/sync-skills` links the same skills into Claude Code, Codex and Gemini. |
| Plugin or clone | You can install the `agentic-z` plugin from the `dayz-n-chill` marketplace, and it updates through the marketplace. Or you can clone the repo as a mod template, and it updates with `/agentic-z-update`. |
| Side panel | `agentic-z-panel` 0.3.0 is a second plugin with DayZ status and buttons. The buttons run the skill scripts directly, so you can build, check, launch, stop, open the editors and read the logs without spending model tokens. |
| Self-checking repo | The test suite, panel tests, answer tests (evals), the `tests.yml` GitHub workflow and `/docs-sync` catch broken agents, missing files and wrong tool names before release. `/docs-sync` also keeps the wiki matching the repo. |

## Grades by version

This section grades every agent and skill at three points: v1.6.0, after the v1.7.0 grading rounds, and the final v2.0.0 review. All grades come from fresh, independent AI reviewers. The v2.0.0 review also covers the hooks, the search server, the panel, the scripts and the answer tests. The label "not built" marks an item that did not exist yet, and "n/a" marks a core file that was not graded at that version.

\*[diagram]\*

At v2.0.0, 30 of 30 agents, 44 of 44 skills and every other graded item are graded A+.

All three columns are grades from independent reviewers. The v2.0.0 column is the final grade, not a target.

| Item | v1.6.0 released | v1.7.0 agent team | v2.0.0 final |
| --- | --- | --- | --- |
| Agents | | | |
| --- | --- | --- | --- |
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
| Rules and core files | | | |
| `.claude/skills/_shared/dayz-conventions.md (Tier 2 core)` | not built | not built | A+ |
| `_shared/conventions/config.md` | not built | not built | A+ |
| `_shared/conventions/assets.md` | not built | not built | A+ |
| `_shared/conventions/scripts.md` | not built | not built | A+ |
| `_shared/conventions/server.md` | not built | not built | A+ |
| `_shared/conventions/ui.md` | not built | not built | A+ |
| `_shared/skill_helpers.py + test_skill_helpers.py` | not built | not built | A+ |
| `_shared/answer-formatting.md` | not built | not built | A+ |
| Grading method note (the "Grading method" section of this document) | not built | not built | A+ |
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

## Limits

- **Live DayZ session.** Nothing in 2.0.0 has run against a real DayZ session. That includes the team loop, the in-game, behavior and visual gates, and the panel's launch buttons. The behavior and visual gates have only been tested with fixtures.
- **Published version.** Version 2.0.0 is on `develop`, while `main` carries 1.6.0. The 2.0.0 release notes are on `develop`, and CI passes there.
- **Search timeout.** The installed plugin (1.6.0) still has the search timeout bug. The fix is in 2.0.0, which is on `develop` and has not been released yet.
- **Answer tests.** 23 of the 30 agents have them. These seven agents have no question file: `dayz-build-checker`, `dayz-ingame-tester`, `dayz-mod-architect`, `dayz-lead`, `dayz-orchestrator`, `dayz-router` and `figma-to-dayz-layout`.
- **Files not graded.** Nine answer test files have not been graded.
- **Preflight exceptions.** The DayZ rules file has 14 exception entries, which name 21 skills that skip the preflight gate. `docs/dayz-modding.md` lists only five of them.

## Token savers and workflows

Agentic-Z keeps your token bill small, so more of each session goes into the mod itself. Every saver and workflow below is built and tested. None has run in a live DayZ session yet.

### Token savers

| Saver | Mechanism |
| --- | --- |
| Script-only gates | `/dayz-gate build`, `ingame`, `behavior` and `visual` are scripts that print `PASS` (exit 0), `FAIL` (exit 1) or `ERROR` (exit 2). The model steps in only when something fails. This is the largest saving. |
| Log triage | `known-errors.json` holds 52 known errors, each with its fix and its owner. Only new errors go to `dayz-mod-debugger`, and `triage.py --learn` adds entries for the project. |
| Router | Keyword rules run before any model call. See "Components". |
| Hooks | The hooks are the edit check, the scope guard and the paste-in router. See "Components". |
| Status line | `/dayz-statusline` shows P:, the active mod, DayZ Diag and the index age under the prompt. It uses no tokens. |
| Cheaper models | `dayz-build-engineer` and `dayz-router` run on Haiku, and `dayz-docs-writer` runs on Sonnet. |
| Small rules loading | Tier 2 is a 143-line core plus five topic files of 24 to 56 lines each. Most skills read only the core. `/dayz-deploy-pbo` and `/dayz-gate` also point to the bundle mods section of the config topic file. Each agent reads the core plus the topic files its job needs. The most is 283 lines, for `dayz-mod-reviewer`, which reads three topic files. The former Tier 2 was a single 239-line file. Compared with that, the core alone is 40% smaller. An agent that reads one topic file reads 17% to 30% less. With two topic files, the result depends on which two. `dayz-mod-debugger` (226 lines) and `dayz-mod-architect` (231 lines) read a little less. `dayz-vehicle-specialist`, `dayz-weapon-specialist` and `dayz-audio-fx-specialist` (251 lines) read more, and so does `dayz-mod-reviewer` with three (283 lines). |
| Panel and wrappers | The `agentic-z-panel` buttons, and a `.bat` wrapper for every runnable skill, run the scripts directly. |
| Short descriptions | Every session loads the agent and skill descriptions, so we keep them short. This loads about 2,100 fewer tokens into every session. |

### Workflows

### Paste-in inputs

- A crash log or RPT
- A screenshot of a bug
- A Figma link
- A GitHub link
- A chunk of types.xml

### Build

- Mod recipes
- A live log watch
- Behavior and visual gates
- A release pack

### Maintenance

- An upgrade guard
- A conflict check against the other mods loaded beside yours
- A balance sheet against vanilla
- A health page for each mod

### Server owners

- A server kit
- Answers to questions about vanilla
- Answer tests
- A layout preview

### Roadmap

- **Live DayZ checks.** Build one small mod from start to finish with DayZ running on the user's PC, and run the in-game, behavior and visual gates for real. We will ask the user before it runs.
- **Release 2.0.0.** Merge `develop` into `main` once the user says yes. Nothing is released until then.
- **RAG search.** After the release, add a Voyage API key to `.env` and run a full re-index.
- **Answer tests for the last seven agents.** Write question files for `dayz-build-checker`, `dayz-ingame-tester`, `dayz-mod-architect`, `dayz-lead`, `dayz-orchestrator`, `dayz-router` and `figma-to-dayz-layout`, and record a baseline.
- **Grade the files not yet graded.** Do this in the next independent round. Grade the nine newer question files.
- **Preflight exception list.** Bring `docs/dayz-modding.md` in line with the rules file.
- **Add-ons plugin.** Build an optional `agentic-z-addons` plugin for outside tools. We will build it only after the core is done, and only for the add-ons the user names.

## Domain specialists

Agentic-Z gives you eight specialist agents. They work under the team leads alongside the workers, and `/dayz-lint` runs inside the build gate.

Agentic-Z stays the base, and the team loop stays the same: plan, leads, workers, gates, ship. The specialists add only workers and one check inside the existing build gate. All of it is on develop.

\*[diagram]\*

### Build order

1. **Foundation.** This adds rules on client and server ownership to the DayZ rules. It also adds an empty folder for answer tests (evals).
2. **`/dayz-lint`.** This is Agentic-Z's own checker for errors that would stop a mod from loading. It runs inside `/dayz-gate build` and `/dayz-build-pbo` before packing, and its findings feed the known-errors triage.
3. **`dayz-persistence-specialist`.** It covers storage, save versions and migrations, base building, and a check before release to confirm that nothing gets lost.
4. **`dayz-vehicle-specialist`.** It covers cars, boats, helicopters and flight.
5. **`dayz-weapon-specialist`.** It covers CfgWeapons, attachments, magazines and selections.
6. **`dayz-wearables-specialist`.** It covers clothing, characters, slots and proxy alignment.
7. **`dayz-animation-specialist`.** It covers model.cfg animation sources, RTM, and the handoff to Blender.
8. **`dayz-audio-fx-specialist`.** It covers sound shaders and sound sets, working with the existing particles skill.
9. **`dayz-physics-specialist`.** It covers collision layers, contact and thrown objects.
10. **`dayz-ai-specialist`.** It covers infected, animals and human AI such as patrols and guards.
11. **Upgrades to existing agents and skills.** These cover scripts, UI and widgets, textures and rvmats, and models and LODs. They also add animated doors in the object builder, a short spec step in `/dayz-init`, and a layout preview at several screen sizes.

### Scope decisions

This table shows what Agentic-Z builds new, keeps, expands, saves for later and refuses to ship.

| Verdict | Items |
| --- | --- |
| Build new | Persistence, base building, data audit, vehicles, aviation, weapons, clothing, characters, proxy alignment, doors, physics, sound, AI patterns, the animation pipeline, `/dayz-lint`, layout preview and answer tests. |
| Keep ours | Preflight, p3d audit, particles, PBO build, in-game testing, the mod workflow, the DayZ rules and script style, and the CLAUDE, AGENTS and GEMINI files. |
| Expand ours | Scripting, UI development, the texture pipeline, the model pipeline, and a spec step before building. |
| Later | Blender animation and assembly, UV atlas, a 3D viewer, a p3d inspector, model preflight, animation format checkers and vehicle proxy checks. |
| Won't ship | Vehicle rips from racing games, PBO reverse engineering and AI 3D generators. |

The specialists have not run in a live DayZ session (see "Limits"). Testing each specialist in game needs DayZ running on the user's PC. We will ask the user before it runs.

## Version comparison

This table shows what each version has and does not have.

| Feature | v1.6.0 released | v1.7.0 agent team | v2.0.0 final |
| --- | --- | --- | --- |
| Counts | | | |
| --- | --- | --- | --- |
| Agents | 14 | 21 | 30 |
| Skills | 29 | 31 | 44 |
| Hooks | 0 | 0 | 3 |
| Tests | 84 | 1,064 | 2,884 plus 18 panel tests |
| Agents | | | |
| Workers for script, config, models, textures, UI, maps, server and Workbench | Has | Has | Has |
| `dayz-mod-reviewer` and `dayz-mod-debugger` | Has | Has | Has |
| The Figma-to-DayZ pipeline, with three agents and its rules file | Has | Has | Has |
| `agent-creator` | Has | Has | Has |
| Orchestrator, architect and team leads | Does not have | Has | Has |
| `dayz-build-engineer` and `dayz-docs-writer` | Does not have | Has | Has |
| `dayz-build-checker` and `dayz-ingame-tester` | Does not have | Has | Has |
| `dayz-router` and `/dayz-route` | Does not have | Does not have | Has |
| Eight domain specialists | Does not have | Does not have | Has |
| Checks | | | |
| The `/dayz-gate` build, in-game, behavior and visual gates as scripts, with known-error triage | Does not have | Does not have | Has |
| `/dayz-lint` inside the build gate | Does not have | Does not have | Has |
| Hooks for the edit check, scope guard and paste-in router | Does not have | Does not have | Has |
| Answer tests (evals) | Does not have | Does not have | Has |
| A `tests` workflow on every pull request | Does not have | Does not have | Has |
| Skills and tools | | | |
| `/dayz-deploy-pbo` | Does not have | Has | Has |
| `/dayz-record-correction` | Does not have | Has | Has |
| Workflow commands for recipes, log watch, release pack, server kit, upgrade guard, conflict check, balance, health, answers about vanilla and layout preview | Does not have | Does not have | Has |
| Token savers: the status line, and Tier 2 split into a core file and topic files | Does not have | Does not have | Has |
| The `agentic-z-panel` side panel | Does not have | Does not have | Has |
| Search | | | |
| `dayz-rag` search over the vanilla game files on your P: drive | Has | Has | Has |
| Wiki search with `/dayz-search-wiki-index` and the `search_dayz_wiki` tool | Has | Has | Does not have |

## Rule tiers

Every agent loads its rules from three tiers. When two tiers disagree, the more specific one wins, and no tier repeats another.

| Tier | Contents and files | Loaded by |
| --- | --- | --- |
| 1 · Repo rules | Communication, tooling, memory and routing, in `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`. | Every agent, for every task |
| 2 · DayZ rules | Enforce Script style, config and asset rules, environment and vanilla search, in `.claude/skills/_shared/dayz-conventions.md` plus five topic files in `conventions/`: config, assets, scripts, UI and server. | All DayZ work |
| 3 · Agents and skills | The 30 agents and the 44 skills. | Only what the task needs |

## Agents

There are 30 agent files in `.claude/agents/`, and the plugin ships all of them. "New" in the Since 1.6.0 column means the agent was added after version 1.6.0. Agents with no model named here use the session's model.

| Agent | Role | Since 1.6.0 |
| --- | --- | --- |
| Planning | | |
| --- | --- | --- |
| `dayz-orchestrator` | Runs as the main session (`claude --agent agentic-z:dayz-orchestrator`). It plans the mod with the user, splits it into small tasks, hands them to the leads, runs the gates and tracks what is done. | New |
| `dayz-mod-architect` | Plans the classes, files, assets and behavior checks before work starts. | New |
| `dayz-lead` | One agent for six teams: script, config, art, UI, server and release. It splits its share into worker tasks and checks that the results fit together. | New |
| Workers | | |
| `dayz-script-specialist` | Writes Enforce Script: modded classes, RPCs and game logic. | Keep |
| `dayz-workbench-specialist` | Handles tools inside Enfusion Workbench. | Keep |
| `dayz-config-specialist` | Handles `config.cpp`, class inheritance and hidden selections. | Keep |
| `dayz-object-builder` | Handles `.p3d` models, LODs, selections and doors. | Keep |
| `dayz-asset-specialist` | Handles `.paa` textures and `.rvmat` materials. | Keep |
| `dayz-ui-specialist` | Handles `.layout` files and the scripts that drive them. | Keep |
| `figma-node-normalizer` | Normalizes a Figma frame so it can be converted. | Keep |
| `figma-to-dayz-layout` | Converts the normalized frame into a DayZ `.layout`, and repairs any layout the validator failed. | Keep |
| `dayz-server-admin` | Handles `types.xml`, `init.c` and server settings. | Keep |
| `dayz-map-specialist` | Handles Terrain Builder and DayZ Editor work. | Keep |
| `dayz-build-engineer` | Runs the build, test server and launch skills. It runs on Haiku. | New |
| `dayz-docs-writer` | Keeps the mod's README, changelog and classname list up to date. It runs on Sonnet. | New |
| Specialists | | |
| `dayz-persistence-specialist` | Handles data that survives restarts: storage, save versions and migrations, base building, and a data audit before release to confirm that nothing gets lost. It belongs to the script team, and the audit goes to the server lead. | New |
| `dayz-ai-specialist` | Handles infected, animals and human AI such as patrols and guards. It belongs to the script team. | New |
| `dayz-vehicle-specialist` | Handles cars, boats and helicopters: engine, gearbox, wheels, doors, fluids, seats, damage, get-in actions and flight. It belongs to the config team. | New |
| `dayz-weapon-specialist` | Handles CfgWeapons, magazines, ammo, attachments, bones and selections, recoil and fire modes. It belongs to the config team. | New |
| `dayz-wearables-specialist` | Handles clothing, characters, inventory slots, protection, color variants, proxies and proxy alignment. It belongs to the art team. | New |
| `dayz-animation-specialist` | Handles model.cfg animation sources, RTM files and the handoff to Blender. It belongs to the art team. | New |
| `dayz-audio-fx-specialist` | Handles sound shaders, sound sets, client-only audio and particle effects (with the `/dayz-particles` skill). It works with any team. | New |
| `dayz-physics-specialist` | Covers weight, collision LODs and layers, dropping, throwing and contact. It diagnoses problems and hands the fix to the owner, and never edits files itself. It works with any team. | New |
| Support | | |
| `dayz-router` | It is the Haiku agent behind `/dayz-route`, and it decides who handles a request. | New |
| `agent-creator` | Writes new agent files and checks them against the agent standard. | Keep |
| Gates (read-only) | | |
| `dayz-mod-reviewer` | Checks the mod against the DayZ conventions and returns PASS or FAIL. | Keep |
| `dayz-layout-validator` | Checks a `.layout` against the Figma-to-DayZ rules without editing it. It is the UI gate. | Keep |
| `dayz-build-checker`, `dayz-ingame-tester` | These are fallbacks that start only when the `/dayz-gate build` or `/dayz-gate ingame` script itself errors (exit code 2). | New |
| `dayz-mod-debugger` | Reads the logs for errors that triage does not recognize, and names the cause and the owner. | Moved |
## Skills

Agentic-Z gives you 44 skills in `.claude/skills/`, and each one is a slash command that you or any agent can run. Forty of them ship in the plugin. The other four (`/sync-skills`, `/agentic-z-update`, `/docs-sync` and `/clean-repo`) are for clones only. The preflight check guards the 40 DayZ skills in the plugin in three ways.

- 18 skills run `/dayz-preflight` before they do anything. For preflight itself, running it is the check.
- The DayZ rules file lists 14 exceptions that cover 21 skills, and each one states its reason. Some of these skills read P:. `/dayz-lint`, `/dayz-balance`, `/dayz-conflict-check`, `/dayz-recipe`, `/dayz-layout-preview` and `/dayz-upgrade-guard` only read files and write a report, and `/dayz-ask` only checks that P: is mounted. `/dayz-gate` relies on the checks in the scripts it calls. `/dayz-stop-test` skips the check so that it still works as an emergency stop.
- `/dayz-particles` is a reference skill and has no script.

| Skill | Function |
| --- | --- |
| Setup | |
| `/dayz-init` | Walks you through setup on first run, with an optional spec step. After that, it becomes the status hub for your active mod. |
| `/dayz-preflight` | Checks the P drive, DayZ Tools, the vanilla data and the Workshop link. |
| `/dayz-workdrive` | Mounts the P drive after a reboot without opening DayZ Tools. |
| `/dayz-setup-objectbuilder` | Sets up Object Builder on a new machine. |
| Mods | |
| `/dayz-new-mod` | Creates a new mod with the standard folders and files. |
| `/dayz-import-mod` | Brings an existing mod folder or a GitHub repo into the workspace. |
| `/dayz-add-scaffold` | Adds any missing standard pieces to an existing mod. |
| `/dayz-recipe` | Starts a plan from a recipe (new weapon, new vest or new craftable item) for the architect to finish. |
| `/dayz-scope-mod` | Locks editing to one mod. |
| `/dayz-clean-workspace` | Removes the mods it created, along with their builds. |
| Build | |
| `/dayz-lint` | Catches errors that would stop a mod from loading, before it is packed. It runs first inside the build gate and inside `/dayz-build-pbo`. |
| `/dayz-build-pbo` | Packs a mod into a PBO with AddonBuilder. |
| `/dayz-deploy-pbo` | Copies prebuilt PBOs and keys into place without AddonBuilder. |
| Test | |
| `/dayz-add-server` | Sets up a local test server instance. |
| `/dayz-launch-test` | Starts a diag server and client with the mods you name. |
| `/dayz-stop-test` | Stops the test session. |
| `/dayz-cot-bootstrap` | Gives you in-game admin rights on the test server. |
| `/dayz-logwatch` | Watches the logs during a test session and triages each new error the moment it appears. |
| Checks, routing and status | |
| `/dayz-gate` | Runs build, in-game, behavior and visual checks as scripts that print PASS or FAIL, and triages known errors. |
| `/dayz-conflict-check` | Finds prefix, path and class collisions with the other mods loaded beside yours. |
| `/dayz-upgrade-guard` | After a DayZ update, lists the mod classes whose vanilla parents changed. |
| `/dayz-balance` | Compares item stats with similar vanilla items and flags the outliers. |
| `/dayz-health` | Shows a page for each mod with the last build, the last test, open findings and gate history. |
| `/dayz-route` | Shows which skill, specialist or team should handle a request. |
| `/dayz-statusline` | Installs a status line that shows P:, the active mod, DayZ Diag and the age of the index. |
| Art and UI | |
| `/dayz-pack-texture` | Converts images to `.paa` and checks their suffixes. |
| `/dayz-build-imageset` | Packs UI sprites into an imageset. |
| `/dayz-layout-preview` | Draws a `.layout` as PNGs at several screen sizes and flags any widgets that fall off screen. |
| `/dayz-p3d-audit` | Finds collision, physics and structure problems in models. |
| `/dayz-particles` | Shows you how to make particle effects without Workbench. |
| `/dayz-launch-objectbuilder` | Opens Object Builder on a model. |
| `/dayz-launch-workbench` | Opens Workbench on a mod's project. |
| Server economy | |
| `/dayz-edit-types` | Adds, changes, removes or merges `types.xml` entries. |
| `/dayz-split-types` | Splits one large `types.xml` into 19 category files. |
| Release | |
| `/dayz-release-pack` | Writes the Workshop description, a changelog entry, the classname list and install notes for server owners. |
| `/dayz-server-kit` | Zips the types.xml entries, cfgeconomycore lines, load order and public key for server owners. |
| RAG search | |
| `/dayz-search-index` | Builds the index of the game files. |
| `/dayz-search-download` | Downloads a prebuilt index instead. |
| `/dayz-ask` | Answers a plain-English question about vanilla DayZ by searching the game files on your P drive. |
| Team and repo | |
| `/dayz-record-correction` | Turns a correction from you into a team rule. |
| `/sync-skills` | Links the skills into Claude Code, Codex and Gemini (clones only). |
| `/agentic-z-update` | Pulls template updates into a clone (clones only). |
| `/docs-sync` | Keeps the docs wiki in step with the source files (clones only). |
| `/clean-repo` | Cleans up the whole repo across every domain (clones only). |

The side panel is a separate plugin, not a skill. Install it with `/plugin install agentic-z-panel@dayz-n-chill`, and then open it with `/dayz-panel`.

## Specialist workflows

These are the steps each agent follows inside the task lifecycle. Every agent that writes DayZ content checks vanilla first. It uses Grep for a known class or symbol name. It uses RAG search for questions by meaning, or after two or three greps come up empty. Then it reads the real file before it relies on a hit. `dayz-build-engineer`, `dayz-docs-writer`, `dayz-build-checker`, `dayz-ingame-tester` and `figma-node-normalizer` have no RAG tool. They work from the mod, its logs or the Figma file.

| Agent | Steps |
| --- | --- |
| Script lead | |
| `dayz-script-specialist` | 1. Searches the vanilla scripts for the class it will change, and reads the real file. 2. Writes a `modded class` in the right layer (3\_Game, 4\_World or 5\_Mission) and calls `super`. 3. Adds RPCs only where the client and server must talk, and checks which side runs each line. 4. `/dayz-lint` and the build gate check and pack it, but neither one compiles Enforce Script. The in-game gate catches compile errors in script.log. |
| `dayz-workbench-specialist` | 1. Reads how vanilla Workbench plugins are registered. 2. Writes the plugin script and its tool panel. 3. Never opens Workbench itself. Instead, it tells you to open it with `/dayz-launch-workbench --mod <ModName>`. 4. Returns the plugin and the steps to load and run it. |
| `dayz-persistence-specialist` | 1. Lists every value that must survive a restart. 2. Writes OnStoreSave and OnStoreLoad, with a version number written first. 3. Adds an upgrade path so that saves from the last version still load. 4. Runs the data audit, which checks that every field is written and read back in the same order. 5. Hands the audit to the server lead before release. |
| `dayz-ai-specialist` | 1. Reads how vanilla infected and animals decide what to do. 2. Writes the behavior as its own script classes, never copied from another mod. 3. Gives the server lead the spawn setup. 4. The in-game test watches the behavior and the server performance. |
| Config lead | |
| `dayz-config-specialist` | 1. Finds the closest vanilla parent class (with Grep for known names and RAG search for questions by meaning). It reads the definition on disk. 2. Writes CfgPatches with the right requiredAddons, and then the class itself. 3. Matches hiddenSelections to the names in the model. 4. `/dayz-lint` and the build gate check that it loads. |
| `dayz-vehicle-specialist` | 1. Picks the closest vanilla vehicle as the parent. 2. Writes the vehicle class and its simulation: engine, gearbox, axles and wheels. 3. Adds attachment slots for the doors, hood, trunk, wheels, battery and plug, and adds the fluids. 4. Writes the CarScript or BoatScript class for seats, doors and damage. 5. Gives the server lead a types.xml entry. The behavior gate spawns the vehicle, and a person runs a checklist for driving. |
| `dayz-weapon-specialist` | 1. Picks the closest vanilla weapon as the parent. 2. Writes the weapon, magazine and ammo classes and the attachment slots. 3. Sets the recoil and fire modes. 4. Lists the model selections and memory points that the art lead must provide. 5. The behavior gate spawns the weapon and fits each attachment, and a person runs a checklist for firing and reloading. |
| Art lead | |
| `dayz-object-builder` | 1. Specifies the LODs (visual, geometry, fire geometry, view geometry and memory) as numbered Object Builder steps for you. It cannot edit a .p3d itself. 2. Names the selections and memory points that the config and animations need, and writes model.cfg. 3. Runs `/dayz-p3d-audit` after you save the model. 4. Hands the selection names to the config lead. |
| `dayz-asset-specialist` | 1. Checks that each texture has the right suffix (\_co, \_nohq, \_smdi and the rest). 2. Packs the textures with `/dayz-pack-texture`. 3. Writes the .rvmat for each material. 4. Writes a checklist of how things should look, for you to check in Object Builder or in game. It never launches either one. |
| `dayz-wearables-specialist` | 1. Picks the inventory slot and the closest vanilla item as the parent. 2. Sets the slots held, the protection and the insulation. 3. Sets hidden selections so that one model carries every color. 4. Notes the proxy positions for the Object Builder specialist. 5. The behavior gate wears each color class, and a person checks in game how each color looks. |
| `dayz-animation-specialist` | 1. Lists the moving parts and their bones. 2. Writes skeletonBones for the moving parts and the class Animations block in model.cfg. The Object Builder specialist keeps the rest of model.cfg. 3. Gives you the bone and selection names for your own Blender export. 4. Names the script hook that plays the animation. The script specialist writes that code, and the in-game test uses it. |
| UI lead | |
| `dayz-ui-specialist` | 1. Reads the vanilla layout closest to the new screen. 2. Writes the .layout and the script class that drives it. 3. Builds icons into an imageset with `/dayz-build-imageset`. 4. The layout checker tests it, `/dayz-layout-preview` draws it, and the in-game test opens it. |
| `figma-node-normalizer` | 1. Reads the Figma frame. 2. Cleans up the layer names and structure so that they map to DayZ widgets. 3. Hands the clean tree to the layout converter. |
| `figma-to-dayz-layout` | 1. Turns the clean tree into a DayZ .layout. 2. Uses only the widget types that the game supports. 3. Hands the result to the layout checker. |
| Server lead | |
| `dayz-server-admin` | 1. Writes types.xml entries with `/dayz-edit-types`. 2. Adds events, spawn points and gameplay settings where they are needed. 3. Splits large economy files with `/dayz-split-types`. 4. Sets up a missing test server instance with `/dayz-add-server`, which starts nothing. It returns the `/dayz-launch-test` command instead of starting the server. |
| `dayz-map-specialist` | 1. Writes layers.cfg and the surface and clutter configs. If your own layers.cfg is needed and missing, it stops and asks. 2. Gives numbered steps for the DayZ Editor export and for the Terrain Builder import and generation, which you carry out. 3. Returns the files and the steps to rebuild the map. |
| Release lead | |
| `dayz-build-engineer` | 1. Packs the mod with `/dayz-build-pbo`. 2. Starts the test session with `/dayz-launch-test`. 3. Reports the build result to the release lead, who passes it to the orchestrator. |
| `dayz-docs-writer` | 1. Reads what changed in the wave. 2. Updates the README, the changelog and the classname list. 3. Writes the Workshop text and the server-owner notes with `/dayz-release-pack`. |
| Any lead | |
| `dayz-audio-fx-specialist` | 1. Reads the vanilla sound or particle closest to the request. 2. Writes the sound shader and sound set, or writes the particle with `/dayz-particles`. 3. Adds the script line that plays it. 4. The in-game test listens and looks. |
| `dayz-physics-specialist` | 1. Reads the model's geometry LODs and mass. 2. Finds the fault: missing geometry, the wrong mass or bad collision. 3. Hands the fix to the Object Builder or config specialist. It never edits anything itself. 4. A person runs an in-game test that drops, throws and shoots the item, which the behavior gate cannot do. |
| Checks and fixes | |
| `dayz-mod-reviewer` | 1. Reads the finished task against the DayZ rules file. 2. Lists each problem along with the specialist who owns it. 3. Never edits files. |
| `dayz-layout-validator` | 1. Checks the file format and widget classes of the .layout. 2. Reports PASS or FAIL, with each problem and its line. It never edits. |
| `dayz-build-checker` | 1. Runs only when `/dayz-gate build` itself breaks. 2. Reads the AddonBuilder output and names the file that failed. |
| `dayz-ingame-tester` | 1. Runs only when `/dayz-gate ingame` itself breaks. 2. Reads the logs from the test session and reports what failed. |
| `dayz-mod-debugger` | 1. Receives new errors that triage does not recognize. 2. Traces script.log, RPT and crash files back to the line that failed. 3. Reports the cause, evidence, location and fix to its caller (the orchestrator or a lead), and names the worker that owns the fix. |

## Task lifecycle

1. You approve the mod plan from `dayz-mod-architect`, for example "a tactical vest with three retextures".
2. `dayz-orchestrator` splits the plan into tasks, for example "write the vest's config.cpp entry".
3. The `dayz-lead` for the matching team takes the task and starts a worker.
4. The worker runs a RAG search, checks the real file and does the one task.
5. The lead gates the work with `dayz-mod-reviewer` (plus `dayz-layout-validator` for UI). After the wave, the orchestrator builds the mod and loads it in game. Triage sends known errors to their owners and new ones to `dayz-mod-debugger`, and the task comes back with notes.
6. Work that passes is packed into a PBO and loaded on a test server.
7. You approve the mod and publish it to the Steam Workshop with DayZ Tools Publisher.
