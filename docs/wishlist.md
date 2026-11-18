# Wishlist

Ideas that would be nice to add but were not asked for. Nothing here is built during a job: the rule in `.claude/CLAUDE.md` ("Scope") sends every such idea here instead. The user picks what, if anything, becomes real work.

| Idea | Where it came up | Date |
| --- | --- | --- |
| Derive the seat roster in `skills/dayz-p3d-audit/scripts/audit_getin_wheels.py` from the car's `Crew` config, so it is right for four-seat cars and cars with no seat-back selections. | Vehicles review | 2026-11-17 |
| A census script for the hidden-selection face ownership check and the light selection preflight the vehicle pack describes by hand. | Vehicles review | 2026-11-17 |
| A PBO reader for the checks in section 5 of `skills/_shared/vehicles/build-packaging-and-debug.md` (completeness, build mode, baked wheel angle, stray drive letters); `scripts/tools/dayz-pbo-diff/` may cover part of it. | Vehicles review | 2026-11-17 |
| An override resolver for the 1.30 migration checklist: flag an `override` of a method DayZ 1.30 deleted, which the script validator passes today. | Vehicles review | 2026-11-17 |
| Turn the DXT1 PAA encoder printed in `skills/_shared/vehicles/png-to-paa-encoding.md` into a tested script with a DXT5 path. | Vehicles review | 2026-11-17 |
| A `/dayz-p3d-audit` check for a vehicle sub-model whose visual LOD lacks `autocenter=0`. | Vehicles review | 2026-11-17 |
| A `/dayz-p3d-audit` check built from a negative fixture that swaps the proxy frame sides and must fail. | Vehicles review | 2026-11-17 |
| A script that finds each un-prefixed `file.c:N` citation in the vehicle field-note files on `P:\` and rewrites it with the `P:\` prefix, so the citation tests cover them. | Vehicles review | 2026-11-17 |
| A short "Boats at run time" section in `skills/_shared/vehicles/class-hierarchy.md` (engine stop out of water, decay timer, water particle points). | Vehicles review | 2026-11-17 |
| A `/dayz-lint` warning for a class that extends `CarScript`, defines `EOnSimulate` and never calls `SetEventMask(EntityEvent.SIMULATE)`. | Vehicles review | 2026-11-17 |
| A `/dayz-lint` check that every `UA*` string read in script is declared in the mod's `inputs.xml`. | Vehicles review | 2026-11-17 |
| A line in the pack index on the tag vocabulary for third-party references (`[VERIFIED-<mod>]`, `[INFERRED]`, `[UNVERIFIED]`, `[DESIGN]`). | Vehicles review | 2026-11-17 |
| A fixed phrase for facts reported for a newer game build than the one on `P:\`, as a convention. | Vehicles review | 2026-11-17 |
| Eval questions for `dayz-vehicle-specialist` on aviation (event mask, `OnDriverExit` gear stop, `SyncedValue` priming) and motorbikes (brake `input` channels, `Wheels` without `Axles`, the battery override, the directional get-in pair). | Vehicles review | 2026-11-17 |
| `/dayz-p3d-audit`: print a per-LOD resolved-vertex count, with a warning at 90 % of a ceiling the user gives. | Models review | 2026-11-17 |
| `/dayz-p3d-audit`: script the checks its references describe by hand (wheel model memory points, ride height, component count and mass share on a vehicle, `#Mass#` outside Geometry, the per-component inward winding check, the get-in contract gate). | Models review | 2026-11-17 |
| A UV audit script for MLOD models (`uv_audit.py`), and a `/dayz-p3d-audit` report of the share of zero and degenerate UVs per visual LOD. | Models review | 2026-11-17 |
| Scripts for the parts of the clean UV atlas method (`skills/_shared/models/tools-uv-atlas.md`) that have none: Track B (`smart_project` plus the exact fold loop) and the shared-sheet recipe for LODs. | Models review | 2026-11-17 |
| Clean UV atlas engine (`skills/dayz-model-tools/scripts/project_atlas.py`): take the expected `.blend` hash, face count and shell lists from command-line options or the assignment JSON, pick the stage with a `--stage` option, and replace `render_atlas_pngs` with a small PNG writer. | Models review | 2026-11-17 |
| `sat_gate.py`: print evaluated, skipped and total triangle counts, and stop cleanly when every triangle is collapsed. Share one module for the SAT check and the island finder, which exist two and three times. | Models review | 2026-11-17 |
| A Blender-gated end-to-end test for the clean UV atlas scripts of `dayz-model-tools` (unwrap a small generated mesh, assert zero overlapping pairs). | Models review | 2026-11-17 |
| Write `probe_truth.py` and `facet_report.py`, which `skills/_shared/models/tools-vlm-judge.md` documents but `/dayz-model-tools` does not ship. | Models review | 2026-11-17 |
| A checker for shorthand citations (`file.c:123`, a bare `:123` after a path), which the integrity test skips. | Animation review | 2026-11-17 |
| Name the graph layer in the opening sentence of `skills/_shared/animation/README.md`. | Animation review | 2026-11-17 |
| A pytest for `gen_model_cfg.py` (it has only `--self-test`), one that builds the animation viewer page against `viewer_core.py`, and tests for `ik_pose_to_seanim.py` and `weapon_grip_viewer.py --data`. | Animation review | 2026-11-17 |
| Finish `ik_pose_to_seanim.py`: write the step that turns joint positions into bone rotations, and drop its free text notes. | Animation review | 2026-11-17 |
| A guard in `weapon_grip_viewer.py` that refuses a py3d without `IS_DAYZ_FORK`. | Animation review | 2026-11-17 |
| `skills/dayz-animation-pipeline/scripts/retargeting.py`: reject an empty bone map, strip the `mixamorig:` prefix, register the three scene properties, fix the `KeyError` in `auto_map_bones`, and replace the emoji in its `print` calls with plain text. | Animation review | 2026-11-17 |
| A filled-in `production` contract template for the motion checker (`skills/_shared/animation/motion-contract.md`), with provenance blocks, to copy per task. | Animation review | 2026-11-17 |
| Run `skills/dayz-animation-pipeline/scripts/run_regression_tests.py` once on a machine with Blender and record the result. | Animation review | 2026-11-17 |
| An in-game test of a `.txa` exported with the ring and pinky chains and their carpal bones, to settle an open disagreement. | Animation review | 2026-11-17 |
| Run the two `get_fcurves` variants on a real Blender 4.3 and 4.4, to settle an open disagreement. | Animation review | 2026-11-17 |
| Run the character winding gate as a step of `/dayz-gate build` or `/dayz-p3d-audit` for any mod with a skinned model. | Animation review | 2026-11-17 |
| Rebuild the offline deform judge and the bone-list diff for characters as scripts, and add a script that reads the skeleton name out of a binarized model. | Animation review | 2026-11-17 |
| An offline check script for a worn clothing model (skeleton name byte scan, anatomical facing test), and have the alignment viewer export its own cross-check samples. | Animation review | 2026-11-17 |
| An offline check that every part `id` in a `Construction` block is unique and between 1 and 93, as part of `/dayz-lint`. | World review | 2026-11-17 |
| A `types.xml` entry check against the public classes of `config.cpp`, as part of `/dayz-lint`. | World review | 2026-11-17 |
| An offline script that builds the sidecar cleanup table (every file suffix written against every `DeleteFile` site) and the path helper table from a mod's scripts, for `/dayz-lint` or the deep data audit in `skills/_shared/persistence/deep-audit.md`. | World review | 2026-11-17 |
| An eval question set for `dayz-physics-specialist` drawn from the physics pack, `skills/_shared/physics/`. | World review | 2026-11-17 |
| `rvmat_lint.py`: warn when a Stage4 `_as` reads `uvSource="tex1"` in a material borrowed from vanilla, and when a `_nohq` source name lacks the suffix. | World review | 2026-11-17 |
| A script that prints per channel statistics of an `_as` or `_smdi` `.paa`, and one under `scripts/dev/` that regenerates the procedural SMDI and `dir[]` counts after a game update. | World review | 2026-11-17 |
| A `/dayz-p3d-audit` mode that compares the centre of each remapped weapon selection with the reference weapon. | World review | 2026-11-17 |
| `scripts/dayz/` wrappers that build the API index from `P:\scripts` and query it, so Windows users get every inherited member of a class in one command. | Scripting review | 2026-11-17 |
| Check each Expansion call shape in `expansion_style.md` against the Expansion PBOs and add file and line. | Scripting review | 2026-11-17 |
| A script validator rule for `ChangeGameFocus(0)`. | Scripting review | 2026-11-17 |
| A test that every file named in a `SKILL.md` reference table exists. | Scripting review | 2026-11-17 |
| A script that prints, for one widget type, the vanilla styles whose `Normal` state has a non-empty `Center`. | Scripting review | 2026-11-17 |
| A test that runs `scripts/tools/dayz-ui-lab` `parse.py --check` on the four UI layout templates. | Scripting review | 2026-11-17 |
| A CSV stringtable check (keys used against column 1, header columns). | Scripting review | 2026-11-17 |
| A build check that every `.rvmat` named in `config.cpp` is an entry of the PBO. | Scripting review | 2026-11-17 |
| Compare the entries of two PBOs from `/dayz-build-pbo` with `scripts/tools/dayz-pbo-diff`. | Scripting review | 2026-11-17 |
| `/dayz-setup-objectbuilder`: offer to set the external viewer to the game's `-buldozer` command line. | Scripting review | 2026-11-17 |
| A `/dayz-gate` guard that refuses to stop a session whose command line loads `@DayZ_MCP` without `--yes`. | Scripting review | 2026-11-17 |
| `/dayz-stop-test`: list each DayZ process command line before killing, and cover `DayZServer_x64.exe`. | Scripting review | 2026-11-17 |
| A `--game-root` option on `/dayz-lint` for the `VANILLA-ROOT-BUILD-MISMATCH` rule. | Tools review | 2026-11-17 |
| Let `/dayz-gate build` and `/dayz-build-pbo` find dependency folders from `requiredAddons[]` and pass them to the lint code stage. | Tools review | 2026-11-17 |
| A thin skill for `scripts/tools/dayz-layout-viewer`, next to `/dayz-layout-preview`. | Tools review | 2026-11-17 |
| After `P:\` is re-extracted from the current game build, replace each "not checked on `P:\`" build line of `skills/_shared/enscript/references/game_builds.md` and the topic packs with the cited line. | Knowledge review | 2026-11-17 |
| A `.mcp.example.json` at the repo root for DayZ-MCP. | Knowledge review | 2026-11-17 |
| Short `.cursorrules` and `.github/copilot-instructions.md` entry files that point at `AGENTS.md`. | Knowledge review | 2026-11-17 |
| Adopt the labels `[EXACT]` and `[DESIGN]` for examples in pack files, and six named verification levels, as written conventions. | Knowledge review | 2026-11-17 |
| An eval question for `dayz-ui-specialist` on Dabs MVC. | Knowledge review | 2026-11-17 |
