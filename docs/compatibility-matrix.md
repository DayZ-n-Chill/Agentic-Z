# Compatibility matrix

This matrix records, per skill, which DayZ build the skill's material was checked on and how. Read it before trusting a skill or pack file on a newer build.

- A row records a check made on the date and build it names. "Not re-run" means the level comes from reading the material against its sources, not from a new run on that build.
- A path in the Evidence column is relative to the repo root. `P:\` paths are vanilla files.
- Which build a vanilla line number belongs to, and what moved between the 1.30 builds: `skills/_shared/knowledge/dayz-1-30-build-history.md`.

Reviewed: **2026-07-24**. The rows for `dayz-clothing` and `dayz-persistence` were
added on **2026-08-15** with their own evidence. The rows marked "not re-run" were
added on **2026-08-17** and later without a new run. The other rows were not
re-reviewed on those dates.

Build every row below was checked against: **DayZ PC 1.29.0.163451** (released
2026-07-15; 1.29 was the stable branch until 2026-10-15).

> **The 1.29 stable branch later moved to `1.29.0.163709`** (seen on a local
> install on 2026-08-15). **No row has been re-checked against it.** Same minor
> version, so the API surface is very unlikely to have shifted, but "very
> unlikely" is not evidence and this matrix only records what was measured. Treat
> every level below as verified on `163451` until someone re-runs it.

> **Since 2026-10-15 the stable branch is DayZ 1.30** (`1.30.164078`, then
> `1.30.164200` from 2026-10-21 and `1.30.164289` since 2026-11-04). The levels in
> §Skill coverage are still the 1.29 ones: no row was re-run on 1.30. What was
> checked on 1.30 stable, and how, is in §DayZ 1.30 below.

This matrix records what was actually checked. It does not claim that every
workflow was run end-to-end on the build named.

## Verification levels

- `runtime_verified`: observed in a real DayZ run; the evidence may predate
  this matrix unless the row says otherwise.
- `source_verified`: exact contracts checked against local vanilla or project
  source for the target build.
- `offline_tested`: exercised with deterministic local tests, without DayZ.
- `cross_checked`: reconciled against more than one source or project corpus.
- `historical`: retained from dated project evidence and needs revalidation
  when reused.
- `unverified`: no sufficient evidence; never interpret as compatible.

## DayZ 1.30

Added **2026-10-01**, while 1.30 was still Experimental (Experimental Update 1
shipped 2026-09-16). 1.30 reached stable on 2026-10-15.

The 29 skills below hold DayZ 1.30 content. It was first written between 2026-09-16
and 2026-10-01 against a local extraction of build `1.30.164014` (scripts,
`config.cpp` files and the plain-text `.agf` animation graphs). **This table only
locates that content; it does not re-verify it.** The evidence level of each 1.30
statement is the one its own section records (`[EXACT]` with a `path:line` for source
checks, "measured in game" for runtime ones).

**Re-check on 1.30 stable (2026-10-28).** Every vanilla script citation (a `.c` file,
or `scripts\config.cpp`) in the skills (the 1.30 sections and the rest) was checked
against `1.30.164200` and moved with the text it cites, where some build has that
text. Citations of the game's data files were re-checked where the cited file could be
read on `1.30.164200`; a data-file citation may still give an older tree's line. The
`[EXACT]` blocks that quote vanilla script were compared with that build; the status
lists of `dayz-motorbikes` and `dayz-environment-hazards` were read again on it.
Measurements were not repeated: something measured in game on `1.30.164014` is
evidence for that build. How to tell which build a citation's lines come from, and
which 1.30 build the files on `P:\` are: "What `P:\` shows" and "Which line a
citation gives" in `skills/_shared/knowledge/dayz-1-30-build-history.md`.

**Move to 1.30.164289 (2026-11-09).** `1.30.164289`, the Steam update of 2026-11-04, changed
27 script files, all `.c`, and none of the data PBO entries the 2026-10-28 re-check extracted;
its models, four navmeshes and `ChernarusPlus.wrp` changed size and were not compared. The
citations of the 27 files give their lines on `P:\`, which holds an older build. Where
`1.30.164289` changed the code they cite, the text says what changed and marks it as not
checked on `P:\`: heat stroke and head washing in
`dayz-environment-hazards`, `CollisionFlags` in `dayz-physics-engine`, the bunker doors in
`dayz-doors`, and the item-fall box and the part keys in `dayz-basebuilding`.

Paths in the table are relative to the skill's folder (`skills/<skill>/`) unless they
start with `skills/`. The table names the files that have a 1.30 file or section of
their own. Other files of the same skill mention 1.30 in passing; search the skill for
`1.30` to find them.

| Skill | Where the 1.30 content lives |
|---|---|
| `dayz-ai-patterns` | `SKILL.md`, `references/dayz-1-30-ai.md` |
| `dayz-animation-pipeline` | `references/dayz-1-30-animation-changes.md`, `references/anim-graph.md`, `references/dual-entry-action-pattern.md`, `references/skeletal-anm-enfusion.md`, `references/tooling-and-walls.md`, `references/player-skeleton.md`, `references/item-ik-and-hide.md` |
| `dayz-aviation` | `references/dayz-1-30-aviation.md` |
| `dayz-basebuilding` | `references/dayz-1-30-construction-rebuilding.md`, `references/entity-lifecycle.md`, `references/config-contract.md`, `references/persistence-audit.md`, `references/fence-gate-case.md` |
| `dayz-build-pbo` | `references/dayz-1-30-pbo-build.md`, `references/common-validation-failures.md` |
| `dayz-characters` | `SKILL.md`, `references/dayz-1-30-characters.md`, `references/character-ragdoll.md`, `references/character-rigging.md` |
| `dayz-clothing` | `SKILL.md` |
| `dayz-doors` | `SKILL.md`, `references/door-model-cfg-and-config.md`, `references/lods-and-object-builder.md`, `references/worked-examples.md` |
| `dayz-environment-hazards` | the whole skill (1.30 only) |
| `dayz-mcp-verify` | `references/dayz-1-30-mcp-verify.md` |
| `dayz-mod-dev` | `SKILL.md` (written later, against `1.30.164289`; targets 1.30 or later only) |
| `dayz-mod-workflow` | `references/dayz-1-30-mod-workflow.md`, `references/dayz-1-30-server-measured.md` |
| `dayz-model-pipeline` | `references/dayz-1-30-model-pipeline.md` |
| `dayz-motorbikes` | the whole skill (1.30 only) |
| `dayz-particles` | `SKILL.md`, `references/dayz-1-30-particles.md`, `references/script-api-reference.md`, `references/standalone-particle-reference.md` |
| `dayz-pbo-reverse-engineering` | `references/pitfalls.md` |
| `dayz-persistence` | `SKILL.md`, `references/dayz-1-30-persistence.md`, `references/migration-matrix.md`, `references/vanilla-stream.md`, `references/central-economy-files.md`, `references/sidecar-files.md` |
| `dayz-physics-engine` | `SKILL.md`, `references/ragdoll-and-fall-damage.md`, `references/engine-deep-dive.md`, `references/damage-and-transporthit.md` |
| `dayz-preflight` | `references/dayz-1-30.md` |
| `dayz-realistic-animation-director` | `references/dayz-1-30-animation-direction.md`, `references/biomechanics-and-contact.md`, `references/domain-gates.md` |
| `dayz-sound-system` | `SKILL.md`, `references/dayz-1-30-sound.md`, `references/sound-deep-dive.md` |
| `dayz-test-ingame` | `references/dayz-1-30-test-ingame.md`, `references/session-findings.md`, `references/server-and-mission-config.md` |
| `dayz-texture-pipeline` | `references/vehicle-materials-and-color-variants.md`, `references/map-conventions.md` (one 1.30 measurement each) |
| `dayz-ui-development` | `references/dayz-130-ui-changes.md`, `references/layout-variants-130.md`, `references/hud-action-info-panels.md`, `references/styles-format.md`, `references/widget-api.md` |
| `dayz-underground` | the whole skill (1.30 only) |
| `dayz-vehicles` | `skills/_shared/vehicles/dayz-1-30-vehicles.md` |
| `dayz-weapons` | `SKILL.md`, `references/dayz-1-30-weapons.md`, `references/cfgweapons-contract.md`, `references/p3d-selection-contract.md`, `references/bone-remap.md` |
| `enforce-script-reference` | `SKILL.md`, `references/dayz-1-30-enforce-script.md`, `references/pitfalls-advanced.md`, `references/verified-api-catalog.md`, `references/production-patterns.md` |
| `rip-vehicle-import` | `references/cookbook-get-in-missing.md` |

## Skill coverage

| Skill | Level on 1.29.0.163451 | Required or recommended dependencies | Breaking changes / limits | Evidence |
|---|---|---|---|---|
| `ai-3d-to-dayz` | `cross_checked` | AI generator; Blender; `dayz-model-pipeline`; `dayz-texture-pipeline`; `dayz-build-pbo` | No end-to-end runtime run. Generator APIs and Blender add-ons move independently of DayZ; recheck before use. | `skills/ai-3d-to-dayz/SKILL.md` |
| `ardy-motion-generation` | `historical` | WSL2; NVIDIA GPU with CUDA; Python; PyTorch; CMake 3.15 or newer; a C++17 compiler; the Blender and DayZ animation pipeline | The ARDY environment was not rebuilt for this row. Pin the ML stack the skill documents; compatibility beyond the dated project evidence is `unknown`. | `skills/ardy-motion-generation/SKILL.md` |
| `blender-animation` | `cross_checked` | Blender with `bpy`; Blender MCP; DayZ animation export tooling | DayZ 1.29 changed Animation Editor workflows: live debug, TXA re-import and save flow. Blender-to-DayZ export remains project-dependent and was not rerun. | `skills/blender-animation/SKILL.md`; Bohemia's 1.29 tools changelog |
| `dayz-aviation` | `source_verified` + historical runtime evidence | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-vehicles`; `dayz-test-ingame` | Source contracts were checked on 1.29; each flight model still requires real-input runtime validation. No universal aircraft API guarantee is asserted. | `skills/dayz-aviation/SKILL.md`; the vanilla scripts of build 1.29.0.163451 |
| `dayz-basebuilding` | `source_verified` | `enforce-script-reference`; `dayz-model-pipeline`; `rigorous-data-audit`; `dayz-build-pbo` | 1.29 known issue: navmesh does not update when fence gates open/close. Persistence and part-ID assumptions must be rechecked for each structure. | `skills/dayz-basebuilding/SKILL.md`; Bohemia's 1.29 changelog |
| `dayz-characters` | `historical` | Blender; `OFP2_ManSkeleton`; `dayz-model-pipeline`; `dayz-animation-pipeline`; `dayz-build-pbo` | No full humanoid import was rerun on 1.29. Skeleton, scale and deformation claims remain dated project evidence until revalidated. | `skills/dayz-characters/SKILL.md` |
| `dayz-clothing` | `runtime_verified` (2026-08-03, DayZ 1.29 diag) | Blender; `DayzTemporarySkeleton`; `dayz-characters`; `dayz-build-pbo`; `dayz-test-ingame` | Three silent failure modes were isolated in game on one garment: a `config.bin` that did not register the class, a mesh in the wrong frame, and a skeleton name that must be `DayzTemporarySkeleton` rather than `OFP2_ManSkeleton`. | `skills/dayz-clothing/SKILL.md` |
| `dayz-3d-viewer` | `offline_tested` | `scripts/tools/py3d` 1.6.0 or later; optional Pillow and `lzokay` | Offline conversion only. The HTML loads Three.js 0.185.1 from the jsDelivr CDN, so a page needs a network. The PAA `SWIZ` tag is read but not applied, proxy triangles show as geometry, and a pilot view LOD (resolution 1100) is never chosen as the mesh. No in-game render was run for this row. | `skills/dayz-3d-viewer/SKILL.md`; `scripts/tools/dayz-3d-viewer/tests` |
| `dayz-feature-spec` | `offline_tested` | project spec, plan, task/handoff and source evidence | Engine-independent process skill. The forward contract for injected objects is source-verified; it does not itself prove runtime behavior. | `skills/dayz-feature-spec/SKILL.md` |
| `dayz-mcp-verify` | `source_verified` + historical runtime evidence | dayz-mcp's `dayz_test_run` / `dayz_test_stop`; a configured dayz-mcp bridge (`docs/dayz-mcp.md`); `dayz-test-ingame` | The bridge needs its own install and wiring. What the tools cannot cover (the skill lists it) goes into the report as a manual test section. The run lifecycle code was read for this row; DayZ was not started. | `skills/dayz-mcp-verify/SKILL.md`; `docs/dayz-mcp.md` |
| `dayz-persistence` | `source_verified` | `enforce-script-reference`; `rigorous-data-audit`; optional Community Framework ModStorage | Entity-stream, schema-version and JSON-loader contracts are read from vanilla source. Nothing here asserts runtime behaviour: atomic-save and recovery claims are design contracts and still need a real save/restart cycle. | `skills/dayz-persistence/SKILL.md`; `P:\scripts\3_game\entities\entityai.c:2910,2958-2978`; `P:\scripts\3_game\tools\jsonfileloader.c:7-40` |
| `dayz-pbo-reverse-engineering` | `offline_tested` | lawful access to the PBO; Mikero ExtractPbo | Tool output and legal permissions vary. Binarized or obfuscated content may limit recovery; no third-party payload may be redistributed. | `skills/dayz-pbo-reverse-engineering/SKILL.md` |
| `dayz-test-ingame` | `source_verified` + `offline_tested` | DayZ Tools; AddonBuilder; DayZDiag; managed lifecycle; optional Community Framework and VPPAdminTools | The launcher template contract tests pass. No runtime launch was made for this row. 1.29 mod and tool changes require dependency checks before reuse. | `skills/dayz-test-ingame/SKILL.md`; `scripts/dev/knowledge-pack/tests/packctl/test_packctl_dayz_test_template_contract.py` |
| `dayz-vehicles` | `source_verified` + historical runtime evidence | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-build-pbo`; `dayz-test-ingame` | Several advanced proxy and winding rules are explicitly offline-only or pending in game; preserve those labels. 1.29 vehicle fixes do not prove custom vehicle compatibility. | `skills/dayz-vehicles/SKILL.md`; `skills/_shared/vehicles/`; vanilla vehicle and action scripts |
| `dayz-weapons` | `historical` + `source_verified` | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-animation-pipeline`; `dayz-build-pbo` | The 1.29 Animation Editor workflow changed, and Bohemia's 1.29 experimental notes listed some weapon animation playback issues. Entity contracts keep their project evidence but must be tested on the target build. | `skills/dayz-weapons/SKILL.md`; Bohemia's 1.29 tools changelog |
| `rip-vehicle-import` | `offline_tested` + historical runtime evidence | `dayz-vehicles`; the `<vehicle-import>` project (not in this repo); Blender; py3d; the build and test skills | In the `<vehicle-import>` project the winding-lineage and material-override tests pass, and its broader profile test has a known unrelated `builder.occ_struct` failure. No new vehicle was run in game for this row. | `skills/rip-vehicle-import/SKILL.md` |
| `rigorous-data-audit` | `cross_checked` | real code/data paths; independent evidence; runtime validation for release | An audit can prove source invariants, not runtime safety by itself. | `skills/rigorous-data-audit/SKILL.md` |
| `enforce-script-reference` | `cross_checked` | vanilla `P:\scripts`; production mods as case studies | Not re-run. Treat signatures as hints until opened at `path:line` on the target build. | `skills/enforce-script-reference/SKILL.md` |
| `dayz-mod-workflow` | `cross_checked` | `enforce-script-reference`; domain skills; vanilla action/network sources | Process skill. The error catalog is dated project evidence; the protocol itself is engine-independent. Not re-run. | `skills/dayz-mod-workflow/SKILL.md` |
| `dayz-texture-pipeline` | `cross_checked` | DayZ Tools TexView and ImageToPAA; vanilla `.rvmat`; optional Blender/Substance | Map-suffix and Super-shader conventions were not re-exported. The MatPBR `.emat` route is not documented by Bohemia, not confirmed by a vanilla file on `P:\` and not run in this repo. | `skills/dayz-texture-pipeline/SKILL.md`; `skills/dayz-texture-pipeline/references/matpbr-emat-pipeline.md` |
| `dayz-particles` | `cross_checked` | vanilla `.ptc`/`.emat` library; `enforce-script-reference` | Particle files are plain text. GUIDs and the size of the particle catalog depend on the game version (304 constants on 1.30). Not re-run. | `skills/dayz-particles/SKILL.md`; `skills/dayz-particles/references/vanilla-particle-catalog.md` |
| `dayz-sound-system` | `cross_checked` | vanilla sound and effect scripts; `enforce-script-reference` | Audio is client only. Not re-run. | `skills/dayz-sound-system/SKILL.md` |
| `dayz-ui-development` | `cross_checked` | vanilla `enwidgets.c` and `gui/`; optional Dabs Framework | An offline preview is not the engine. Registering a layout in both Workbench and `config.cpp` is a common trap. Not re-run. | `skills/dayz-ui-development/SKILL.md` |
| `dayz-doors` | `cross_checked` | Object Builder; `model.cfg`; `HouseNoDestruct` | The three worked patterns (Simple Door, Door with Button, Expert Mode) are described in tables; their model files are not in this repo. The Expert Mode model has a documented anomaly (its lever is in no component): read it before copying. Not re-run. | `skills/dayz-doors/SKILL.md`; `skills/dayz-doors/references/worked-examples.md`; `skills/dayz-doors/references/lods-and-object-builder.md` |
| `dayz-physics-engine` | `cross_checked` | vanilla `enphysics.c` and `dayzphysics.c`; `enforce-script-reference` | Several API names that sound standard do not exist; check "What does not exist" in the skill. Not re-run on 1.29; the skill's citations are `P:\` lines. | `skills/dayz-physics-engine/SKILL.md` |
| `dayz-preflight` | `offline_tested` | DayZ Tools; `P:\` mount; `*_PATH` environment variables first, then the registry and Steam library lookups | Reports and does not repair, with one exception: it creates the `P:\Mods\` junction when that is absent. The unit tests run without DayZ. | `skills/dayz-preflight/SKILL.md`; `skills/dayz-preflight/preflight.py`; `skills/dayz-preflight/test_preflight.py` |
| `dayz-build-pbo` | `cross_checked` | AddonBuilder; optional `scripts/tools/py3d` | The four validators in `references/validation-scripts.md` are code to adapt, not bundled scripts; `/dayz-lint` is the gate the build runs. Not re-run. | `skills/dayz-build-pbo/SKILL.md`; `skills/dayz-build-pbo/references/validation-scripts.md` |
| `dayz-model-pipeline` | `cross_checked` | Blender headless; `scripts/tools/py3d` 1.6.0 or later; OpenSimplex and Pillow for textures | Install py3d with `python -m pip install -e scripts\tools\py3d`, never `pip install py3d` (an unrelated package on PyPI). Winding and mass rules are source-checked; no new object was assembled for this row. | `skills/dayz-model-pipeline/SKILL.md`; `skills/dayz-model-pipeline/references/py3d-direct-generation.md` |
| `dayz-p3d-audit` | `cross_checked` | `scripts/tools/py3d` 1.6.0 or later | The audit script loads py3d from `scripts/tools/py3d/` and needs 1.6.0 or later for the `validate()` findings. The silent-killer catalogue was not re-run on a live `.p3d` for this row. | `skills/dayz-p3d-audit/SKILL.md`; `skills/dayz-p3d-audit/scripts/audit_p3d.py` |
| `dayz-p3d-inspector` | `cross_checked` | `scripts/tools/py3d` 1.6.0 or later; Three.js 0.185.1 from the jsDelivr CDN | py3d's own recipe JSON (`to_dict` / `from_dict`) is lossy: see `scripts/tools/py3d/KNOWN-ISSUES.md`. `p3d_inspector_build.py` binds `Selection(lod.points, lod.faces)` to the live lists. The viewer is one generated HTML file. Not re-run. | `skills/dayz-p3d-inspector/SKILL.md`; `scripts/tools/py3d/KNOWN-ISSUES.md` |
| `dayz-proxy-align` | `cross_checked` | `scripts/tools/py3d` 1.6.0 or later; Three.js 0.185.1 from the jsDelivr CDN | Uses py3d's `add_proxy`, `get_proxies`, `align_proxy` and `remove_proxy`. The editor page needs a network. Not re-run. | `skills/dayz-proxy-align/SKILL.md` |
| `dayz-animation-pipeline` | `cross_checked` | `scripts/tools/py3d`; `scripts/tools/dayz-animation-formats`; Blender; DayZATool and Workbench for `.anm` | There is no `py3d.read_p3d`; open a model with `py3d.P3D(open(path, "rb"))`. The py3d 1.0.0 write quirks are kept as history. Not re-run. | `skills/dayz-animation-pipeline/SKILL.md`; `skills/dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` |
| `mixamo-retarget` | `cross_checked` | Blender with `bpy`; Blender MCP | Experimental: unit-tested outside Blender, and a run inside Blender on a fixture is still pending. No Mixamo or Adobe FBX file or character ships. | `skills/mixamo-retarget/SKILL.md` |
| `blender-assembly` | `cross_checked` | Blender with `bpy`; Blender MCP | Process skill. No third-party meshes ship. Not re-run. | `skills/blender-assembly/SKILL.md` |
| `blender-visual-review` | `cross_checked` | Blender with `bpy`; Blender MCP; optional local vision model | A Blender render cannot judge DayZ winding. Not re-run. | `skills/blender-visual-review/SKILL.md` |
| `dayz-ai-patterns` | `cross_checked` | DayZ Expansion AI (eAI) source, not in this repo; `enforce-script-reference` | Mostly DayZ Expansion AI: third-party mod behaviour, not vanilla. Not re-run. | `skills/dayz-ai-patterns/SKILL.md` |
| `dayz-realistic-animation-director` | `cross_checked` | Blender with `bpy`; `blender-animation`; `dayz-animation-pipeline`; optional DayZDiag for the in-game gate | The offline validators compile. No third-party motion model or ARDY weights ship. Not re-run. | `skills/dayz-realistic-animation-director/SKILL.md`; `skills/dayz-realistic-animation-director/scripts/` |
| `uv-clean-atlas` | `cross_checked` | Blender 4.3 or later, headless; optional PartUV (not shipped) | The scripts compile. Not re-run. | `skills/uv-clean-atlas/SKILL.md`; `skills/uv-clean-atlas/scripts/` |
| `3d-generation-harness` | `cross_checked` | `blender-assembly`; `blender-visual-review`; `dayz-model-pipeline`; `dayz-p3d-audit`; optional external image-to-3D skill `hunyuan3d-local` (not in this repo) | Process harness. AI mesh generation is done by the optional external skill, which this repo does not ship. Not re-run. | `skills/3d-generation-harness/SKILL.md` |
| `dayz-mod-dev` | `unverified` (targets 1.30 or later only) | `dayz-mod-workflow`; `dayz-feature-spec`; the domain skills it routes to; `dayz-test-ingame`; `dayz-build-pbo`; optional Community Framework and DayZ Expansion | Reading guide and rule set. Written against 1.30.164289; builds before 1.30 are not covered and it was not checked on 1.29. Its `P:\` citations are 1.30 lines; its measured rules name the 1.30 server build they were measured on. | `skills/dayz-mod-dev/SKILL.md`; `skills/dayz-mod-workflow/references/dayz-1-30-server-measured.md` |
| `systematic-debugging` | `offline_tested` | `/dayz-lint`; `/dayz-gate`; `/dayz-logwatch`; `/dayz-upgrade-guard` | Engine-independent process skill. Its tests check only that the skill and its reference files are complete and consistent; they do not run DayZ. | `skills/systematic-debugging/SKILL.md`; `skills/systematic-debugging/test_systematic_debugging_docs.py` |
| `task-observer` | `offline_tested` | `/dayz-record-correction` | Engine-independent process skill: it logs observations and stages skill updates, and touches no DayZ file. The tests run its log scan and id snippets on temporary folders. | `skills/task-observer/SKILL.md`; `skills/task-observer/test_task_observer_docs.py` |
| `dayz-environment-hazards` | `unverified` (1.30-only feature set) | `enforce-script-reference`; `dayz-underground` | Written against 1.30.164014 Exp; citations re-checked on 1.30.164200 stable (2026-10-28) and 1.30.164289 (2026-11-09); not checked on 1.29. | `skills/dayz-environment-hazards/SKILL.md`; `skills/dayz-environment-hazards/references/vanilla-file-map.md` |
| `dayz-motorbikes` | `unverified` (targets 1.30 only) | `dayz-vehicles`; `dayz-animation-pipeline`; `dayz-model-pipeline` | 1.30 `MotorbikeScript` contract (`P:\scripts\4_world\entities\vehicles\motorbikescript.c`), written against 1.30.164014 Exp and re-checked on 1.30.164200 stable (2026-10-28); the 1.29 stable scripts contain no `MotorbikeScript` (0 references, checked 2026-10-01). | `skills/dayz-motorbikes/SKILL.md`; `skills/dayz-motorbikes/references/script-api.md` |
| `dayz-underground` | `unverified` (1.30-only terrain holes) | `dayz-basebuilding`; `dayz-test-ingame` | Written against 1.30.164014 Exp; citations re-checked on 1.30.164200 stable (2026-10-28) and 1.30.164289 (2026-11-09); not checked on 1.29. | `skills/dayz-underground/references/terrain-holes-evidence.md` |

## Stable-build evidence and update policy

- The exact game and scripts baseline used for source checks is
  `1.29.0.163451`. For the 1.30 content it is `1.30.164289` since
  2026-11-09, and was `1.30.164200` from the 2026-10-28 re-check (§DayZ 1.30).
- Bohemia's 1.29 stable changelog gives the Steam Stable build as `1.29.163451`,
  released 2026-07-15.
- Before a DayZ stable update is adopted, pin its build, diff relevant vanilla
  contracts, rerun offline gates, then batch representative in-game tests.
- A row only advances to `runtime_verified` with a dated, reproducible test
  artifact. Absence of a listed breaking change means `unknown`, not “none”.
- Dependencies with their own release cycles must be pinned per project. Nothing
  here promises compatibility with an unpinned VPP, Expansion, TraderPlus, TraderX,
  Blender or ML-tool version.
