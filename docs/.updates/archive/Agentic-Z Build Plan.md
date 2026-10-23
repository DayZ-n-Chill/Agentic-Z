# Agentic-Z v2.0.0 build plan

Draft for approval, 20 Oct 2026. Spec: `Agentic-Z Guide.pdf` (source `agentic-z-guide.html` in the vault). Source of the gaps: an eight agent check of every guide claim against `develop` (full results in the session scratchpad, `gapmap.json`).

## Where things stand

* Of about 520 guide claims checked, roughly 380 hold, 75 hold partly and 115 are false.
* Most of the false ones are the unbuilt work the handoff lists: `/dayz-lint`, eight specialists, seven upgrades, eleven workflow commands, paste-in, evals and the regrade.
* About 60 are small wording problems, where the guide or repo text went stale after PRs #53 to #56 (wiki rows, "NEW" badges, counts, version labels, the clone command).
* The handoff is out of date on four points: PRs #53 and #55 are merged, PR #56 dropped the wiki crawler and wiki search, and `feature/specialists` now equals `develop`.

## How the loop runs here

* All work is DayZ tooling, so workers are the `dayz-*` specialists (for packs and agents) and general workers (for Python skills). Each works in its own worktree on its own branch, with one PR to `develop` per row.
* Gates per task: `dayz-mod-reviewer` for DayZ content, plus code review, test check and security review. The accessibility and design QA gates apply only to the layout preview and the health page, the two rows that make something a person looks at.
* Shared files (`dayz-lead.md`, router `rules.json`, `dayz-router.md`, reviewer and debugger owner lists, `plugin.json`, `scripts/README.md`) are edited only in the wiring rows, so parallel workers never collide.
* The guide and team PDF are regenerated from the vault sources after each wave.

## Task table

| # | Task | Team | Done when | Needs |
|---|---|---|---|---|
| **Wave 0: make what exists true** | | | | |
| 0.1 | Repo truth pass: drop wiki mentions (`docs/README.md`, `enscript/README.md`), fix LICENSE parts list, plugin.json counts, add Tier 2 line to `figma-node-normalizer`, route rules for asset, map, workbench, docs, Figma links, remove debinarize wording (`conventions/assets.md:30`, old release notes), RAG `pip install` step in README | Release | Tests pass; grep finds no wiki tool, no debin, no stale counts | none |
| 0.2 | Guide truth pass: delete wiki rows, NEW badges and "new" captions, 19 not 18, clone form of the orchestrator command, settings rows (`DAYZ_DIAG_PATH`, `DAYZ_VANILLA_DATA_PATH`, `VOYAGE_MODEL`, `TYPESAFE_API_KEY`), troubleshooting messages matched to the real text, safety and FAQ wording, clone only marks, item count 54, current test count, version labels | Release (vault) | Every basics, team and skills claim checks true | none |
| 0.3 | CI runs `hooks` tests too | Release | `tests.yml` covers `.claude scripts/dev hooks` | your `gh auth refresh -s workflow` |
| **Wave 1: foundations** | | | | |
| 1.1 | Tier 2 client and server ownership rules; `references/` layout convention; one knowledge pack index | Script | Conventions file and index exist; integrity test checks the index | 0.1 |
| 1.2 | Evals: `evals/` folder, question file format, runner (`claude -p`, scored by script), first five questions for three existing agents | Release | Runner passes on the three agents; tests | 0.1 |
| 1.3 | `/dayz-lint`: config.cpp, CfgPatches, requiredAddons, `$PBOPREFIX$`, script module and folder checks; called first by `/dayz-gate build` and `/dayz-build-pbo`; findings go to triage | Release | Catches each known boot error in fixture mods; `.bat`, tests, registration | 0.1 |
| 1.4 | Research map for the eight subjects (private, vault only; the knowledge pack and StarDZ used as a map, nothing copied) | Architect | One topic list per specialist, each topic with the vanilla file to verify on P: | none |
| 1.5 | `/dayz-gate behavior`, offline part: test mission script injection, PASS and FAIL log line format, parser; architect plan format gets one check per feature | Release | Parser and injector tested on fixture logs | 1.3 |
| **Wave 2: eight specialists** (each: own `references/` pack, agent file matching both guide sections, a separate agent verifies every fact on P:, evals) | | | | |
| 2.1 to 2.8 | persistence, vehicle, weapon, wearables, animation, audio and FX, physics, AI | Script, Config, Art, any | Agent and pack exist; verifier signs off every fact; evals pass | 1.1, 1.2, 1.4 |
| 2.9 | Wire all eight: lead tables (plus an "any team" row), router rules and tests, reviewer and debugger owner lists, triage owners, plugin.json | Release | Router tests route each sample request; integrity tests pass | 2.1 to 2.8 |
| **Wave 3: existing specialists go deeper** | | | | |
| 3.1 | Enforce Script reference, verified on P: | Script | Pack covers the language and core APIs; verifier signs off | 1.1 |
| 3.2 | Dabs and widget UI pack, wired into the UI specialist | UI | Same | 1.1 |
| 3.3 | Texture and rvmat cookbook, wired into the asset specialist | Art | Same | 1.1 |
| 3.4 | Model and LOD rules plus animated doors, wired into object builder | Art | Same | 1.1, 2.5 |
| 3.5 | Spec step in `/dayz-init` that writes a short spec the architect reads | Script | Skill and `plan.py` tests | 0.1 |
| 3.6 | Layout preview at several screen sizes (renders a `.layout` to an approximate PNG) | UI | Preview of three vanilla layouts at three sizes; tests | 0.1 |
| 3.7 | Agent step fixes from the workflows section: workbench and server admin tell the user instead of launching, UI imageset step, object builder audit step, docs writer reads the wave | Release | Each agent matches its guide workflow row | 2.9 |
| **Wave 4: workflow commands** (each: script first, `.bat`, `scripts/README.md` row, tests, registration, guide row) | | | | |
| 4.1 | `/dayz-ask` with `path:line` citations, plus a cache of repeated search answers | Release | Tests with a fake index | 1.3 |
| 4.2 | `/dayz-recipe` (new weapon, new vest, new craftable) pre-filling the architect plan | Release | Three recipes; tests | 2.9 |
| 4.3 | `/dayz-logwatch` | Release | Flags errors from a fixture log being written live | 1.3 |
| 4.4 | `/dayz-release-pack` and `/dayz-server-kit` (public `.bikey` only) | Release | Fixture mod gives the pack and zip | 1.3 |
| 4.5 | `/dayz-balance` | Config | Flags outliers on a fixture mod | 1.3 |
| 4.6 | `/dayz-upgrade-guard` | Release | Detects a changed parent between two fixture snapshots | 1.3 |
| 4.7 | `/dayz-conflict-check`, static scan of CF, COT and Expansion configs (scan only, nothing copied) | Release | Finds planted collisions in fixtures | 1.3 |
| 4.8 | `/dayz-health` page per mod, reading stored gate results | Release | Page from fixture history | 1.3, 1.5 |
| 4.9 | Paste-in hook: crash log or RPT to triage then debugger, `types.xml` chunk merge, Figma link to the pipeline, GitHub link to import, screenshot to the right specialist | Release | Hook tests for each paste type | 1.3 |
| 4.10 | `/dayz-gate visual`, offline part (capture and compare code, baselines) | Release | Compare tested on fixture images | 1.5 |
| 4.11 | Panel buttons for logwatch, release pack, health, ask | Release | `claude plugin test mods/agentic-z-panel` passes | 4.1 to 4.8 |
| **Wave 5: live DayZ (needs DayZ open on your PC; I ask before each run)** | | | | |
| 5.1 | First real end to end mod build with the orchestrator, using a recipe | All | Tested PBO you play | Wave 4 |
| 5.2 | Live checks: behavior gate, visual gate, logwatch, conflict check with CF, COT and Expansion loaded | Release | Each gives a real PASS or FAIL | 5.1 |
| **Wave 6: grade and release** | | | | |
| 6.1 | Independent regrade of every item, fix, regrade until one clean pass | Quality | Every item A+ from a fresh grader | Wave 5 |
| 6.2 | Guide quality tables and team PDF filled with the real grades; PDFs printed | Release | Guide claims all check true | 6.1 |
| 6.3 | Version 2.0.0, release notes, `develop` to `main` when you say so | Release | Marketplace install gives the guide's product | 6.2, your yes |

## Defaults I will use unless you say otherwise

* model.cfg: object builder keeps skeletons, selections and LOD setup; the animation specialist owns `CfgModels` animations and RTM.
* Physics specialist reads mass and geometry through config, `model.cfg` and `/dayz-p3d-audit` on MLOD mod models only. Vanilla ODOL models stay closed; the debinarizer stays out.
* AI specialist: written from vanilla infected and animal code; Expansion behavior described in our words only, no code.
* Vehicle specialist: cars and boats, plus helicopters built on vanilla's native helicopter base classes; the guide line "not in vanilla" gets corrected.
* Prompt caching: the guide says Claude Code caches automatically and Agentic-Z keeps rules files stable so the cache holds. No caching code.
* Credits for the vendored enscript pack (SWARMDayZ, TrueDolphin) stay; the no credit rule is about StarDZ only.
* Old release notes keep a one line "removed in 1.6.0" without naming the skill.
* Gate count: no accessibility or design QA gate on pure Python rows.
</content>
</invoke>
