# Compatibility matrix

This matrix came in with the DayZ Modding Knowledge Pack import. It records, per skill, which DayZ build the pack's material was checked on and how. Read it before trusting a skill or pack file on a newer build.

- "The author" and "the pack" mean the Knowledge Pack and the person who wrote it; "this phase" and "r21" are that project's review rounds. None of the checks below were re-run during the import.
- Skill names are the Knowledge Pack's. Where the import merged a skill into an existing Agentic-Z skill or pack (for example `dayz-preflight`, `dayz-particles`, `dayz-p3d-audit`, and `dayz-pbo-build`, whose material is now under `skills/dayz-build-pbo/`), the row describes the merged-in material, and an evidence path may name a file that now lives in the merged skill or in a pack under `skills/_shared/`.
- The sections "Data files" and "Vanilla line numbers: which build" that this file points to in `skills/_shared/dayz-conventions.md` come from the Knowledge Pack's version of that file.
- Tool paths are the Agentic-Z ones (`scripts/tools/<name>/`).

Reviewed: **2026-07-24**. Rows for `dayz-clothing` and `dayz-persistence` were
added on **2026-08-15** with their own evidence; ten author-owned skills were
adopted on **2026-08-17** from the live store, nine author-owned 3D playbooks
later the same day, and four more (`dayz-ai-patterns`,
`dayz-realistic-animation-director`, `uv-clean-atlas`, `3d-generation-harness`)
in the closing batch. None of those adoptions were re-run in this phase. The
other rows were not re-reviewed on those dates.

Build every row below was checked against: **DayZ PC 1.29.0.163451** (released
2026-07-15; 1.29 was the stable branch until 2026-10-15).

> **The stable branch has since moved to `1.29.0.163709`** (observed on the
> author's install 2026-08-15). **No row has been re-checked against it.** Same
> minor version, so the API surface is very unlikely to have shifted, but "very
> unlikely" is not evidence and this matrix only records what was measured. Treat
> every level below as verified on `163451` until someone re-runs it.

> **Since 2026-10-15 the stable branch is DayZ 1.30** (`1.30.164078`; the author's
> install ran `1.30.164200` from 2026-10-21 and has run `1.30.164289` since 2026-11-04). The levels in §Skill coverage are
> still the 1.29 ones: no row was re-run on 1.30. What was checked on 1.30 stable, and
> how, is in §DayZ 1.30 below.

This matrix records what was actually checked. It does not claim that every
workflow was run end-to-end on this build during r21 Phase 01.

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

Between 2026-09-16 and 2026-10-01, sections for 1.30 Experimental were added to
the 28 skills below, plus the 1.30-only `dayz-motorbikes`. They were written
against a local extraction of build `1.30.164014` (scripts, `config.cpp` files and
the plain-text `.agf` animation graphs). **This table only locates that content; it
does not re-verify it.** The evidence level of each 1.30 statement is the one its own
section records (`[EXACT]` with a `path:line` for source checks, "measured in game"
for runtime ones).

**Re-check on 1.30 stable (2026-10-28).** Every vanilla script citation (a `.c` file,
or `scripts\config.cpp`) in the skills (the 1.30 sections and the rest) was checked
against `1.30.164200` and moved with the text it cites, where some build has that
text. Citations of the game's data files were re-checked where the re-check could
read the cited file on `1.30.164200`; "Data files" in
`skills/_shared/dayz-conventions.md` says which may still give an older tree's line.
The `[EXACT]` blocks that quote vanilla script were compared with that build; the
status lists of `dayz-motorbikes` and `dayz-environment-hazards` were read again on
it. Measurements were not repeated: something measured in game on `1.30.164014` is
evidence for that build. How to tell which build a citation's lines come from:
`skills/_shared/dayz-conventions.md` §Vanilla line numbers: which build.

**Move to 1.30.164289 (2026-11-09).** `1.30.164289`, the Steam update of 2026-11-04, changed
27 script files, all `.c`, and none of the data PBO entries the 2026-10-28 re-check extracted;
its models, four navmeshes and `ChernarusPlus.wrp` changed size and were not compared. The
citations of the 27 files were moved to their `1.30.164289` lines. Where it changed the code
they cite, the text says what changed: heat stroke and head washing in
`dayz-environment-hazards`, `CollisionFlags` in `dayz-physics-engine`, the bunker doors in
`dayz-doors`, and the item-fall box and the part keys in `dayz-basebuilding`.

| Skill | Where the 1.30 content lives |
|---|---|
| `dayz-ai-patterns` | `references/dayz-1-30-ai.md` |
| `dayz-animation-pipeline` | `SKILL.md`, `references/anim-graph.md`, `references/dual-entry-action-pattern.md` (+6 more) |
| `dayz-aviation` | `references/dayz-1-30-aviation.md` |
| `dayz-basebuilding` | `references/dayz-1-30-construction-rebuilding.md` |
| `dayz-characters` | `references/dayz-1-30-characters.md` |
| `dayz-clothing` | `references/dayz-1-30-clothing.md` |
| `dayz-doors` | `SKILL.md`, `references/door-model-cfg-and-config.md`, `references/lods-and-object-builder.md` (+1 more) |
| `dayz-environment-hazards` | `SKILL.md`, `references/sandstorm-shelter.md`, `references/sources.md` (+1 more) |
| `dayz-mcp-verify` | `references/dayz-1-30-mcp-verify.md` |
| `dayz-mod-workflow` | `references/dayz-1-30-mod-workflow.md` |
| `dayz-model-pipeline` | `references/dayz-1-30-model-pipeline.md` |
| `dayz-particles` | `references/dayz-1-30-particles.md` |
| `dayz-pbo-build` | `references/dayz-1-30-pbo-build.md` |
| `dayz-pbo-reverse-engineering` | `SKILL.md` |
| `dayz-persistence` | `references/dayz-1-30-persistence.md` |
| `dayz-physics-engine` | `references/dayz-1-30-ragdoll-and-fall.md` |
| `dayz-preflight` | `SKILL.md` |
| `dayz-proxy-align` | `SKILL.md` |
| `dayz-realistic-animation-director` | `SKILL.md`, `references/biomechanics-and-contact.md`, `references/domain-gates.md` (+2 more) |
| `dayz-sound-system` | `references/dayz-1-30-sound.md` |
| `dayz-test-ingame` | `references/dayz-1-30-test-ingame.md` |
| `dayz-texture-pipeline` | `SKILL.md`, `references/vehicle-materials-and-color-variants.md` |
| `dayz-ui-development` | `SKILL.md`, `references/hud-action-info-panels.md`, `references/styles-format.md` (+2 more) |
| `dayz-underground` | `SKILL.md`, `references/terrain-holes-evidence.md`, `references/underground-triggers.md` |
| `dayz-vehicles` | `references/dayz-1-30-vehicles.md` |
| `dayz-weapons` | `references/dayz-1-30-weapons.md` |
| `enforce-script-reference` | `references/dayz-1-30-enforce-script.md` |
| `rip-vehicle-import` | `references/cookbook-get-in-missing.md` |
| `dayz-motorbikes` | the whole skill (1.30 only) |

## Skill coverage

| Skill | Level on 1.29.0.163451 | Required or recommended dependencies | Breaking changes / limits | Evidence |
|---|---|---|---|---|
| `ai-3d-to-dayz` | `cross_checked` | AI generator; Blender; `dayz-model-pipeline`; texture pipeline; `dayz-pbo-build` | No end-to-end runtime run in this phase. Generator APIs and Blender add-ons move independently of DayZ; recheck before use. | `skills/ai-3d-to-dayz/SKILL.md`; r21 source reconciliation |
| `ardy-motion-generation` | `historical` | WSL2; NVIDIA GPU/CUDA; Python; PyTorch 2.6.0; CMake ≥3.15; C++17; Blender/DayZ animation pipeline | ARDY environment was not rebuilt in this phase. Pin the documented ML stack; current compatibility beyond the cited project evidence is `unknown`. | `skills/ardy-motion-generation/SKILL.md:63-84` |
| `blender-animation` | `cross_checked` | Blender with `bpy`; optional Blender MCP; DayZ animation export tooling | DayZ 1.29 changed Animation Editor workflows: live debug, TXA re-import and save flow. Blender-to-DayZ export remains project-dependent and was not rerun here. | `skills/blender-animation/SKILL.md`; official 1.29 tool changelog |
| `dayz-aviation` | `source_verified` + historical runtime evidence | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-vehicles`; `dayz-test-ingame` | Source contracts were checked on 1.29; each flight model still requires real-input runtime validation. No new universal aircraft API guarantee is asserted. | `skills/dayz-aviation/SKILL.md:26-31`; local `P:\scripts` build 1.29.0.163451 |
| `dayz-basebuilding` | `source_verified` | `enforce-script-reference`; `dayz-model-pipeline`; `rigorous-data-audit`; `dayz-pbo-build` | 1.29 known issue: navmesh does not update when fence gates open/close. Persistence and part-ID assumptions must be rechecked for each structure. | `skills/dayz-basebuilding/SKILL.md`; official 1.29 changelog |
| `dayz-characters` | `historical` | Blender; `OFP2_ManSkeleton`; `dayz-model-pipeline`; animation pipeline; `dayz-pbo-build` | No full humanoid import was rerun on 1.29. Skeleton, scale and deformation claims remain dated project evidence until revalidated. | `skills/dayz-characters/SKILL.md`; r21 source reconciliation |
| `dayz-clothing` | `runtime_verified` (2026-08-03, DayZ 1.29 diag) | Blender; `DayzTemporarySkeleton`; `dayz-characters`; `dayz-pbo-build`; `dayz-test-ingame` | Three silent failure modes were isolated in-game on one garment (ArmorHneck): config.bin not registering, wrong mesh frame, and a skeleton name that must be `DayzTemporarySkeleton` rather than `OFP2_ManSkeleton`. The helper scripts carry placeholder paths and must be re-pointed before use. | `skills/dayz-clothing/SKILL.md` |
| `dayz-3d-viewer` | `offline_tested` | pack `scripts/tools/py3d` >=1.5.0; optional Pillow and LZO extras | Offline conversion only. HTML loads three.js 0.160.0 from a CDN. SWIZ, proxy triangles and ViewPilot 1100 remain documented gaps. No in-game render was run for this row. | `skills/dayz-3d-viewer/SKILL.md`; `scripts/tools/dayz-3d-viewer/tests` |
| `dayz-feature-spec` | `offline_tested` | project spec, plan, task/handoff and source evidence | Engine-independent process skill. New injected-object Forward Contract is source-verified; it does not itself prove runtime behavior. | `skills/dayz-feature-spec/SKILL.md:46-59`; `GAMEMASTER_SOURCE/tools/gm/service.py:209-218` |
| `dayz-mcp-verify` | `source_verified` + historical runtime evidence | public `dayz_test_run` / `dayz_test_stop`; configured DayZ MCP bridge; `dayz-test-ingame` | The bridge is not bundled. Player UI, door interaction, inventory use and firing remain manual. This phase inspected lifecycle code but did not start DayZ. | `skills/dayz-mcp-verify/SKILL.md:33-64`; `DAYZ_MCP_SOURCE/server.py:915-995` |
| `dayz-persistence` | `source_verified` | `enforce-script-reference`; `rigorous-data-audit`; optional Community Framework ModStorage | Entity-stream, schema-version and JSON-loader contracts are read from vanilla source for this build. Nothing here asserts runtime behaviour: atomic-save and recovery claims are design contracts and still need a real save/restart cycle. | `skills/dayz-persistence/SKILL.md:30-39,70-71`; `VANILLA/3_game/entities/entityai.c:2910,2958-2978`; `VANILLA/3_game/tools/jsonfileloader.c:7-40` |
| `dayz-pbo-reverse-engineering` | `offline_tested` | lawful PBO access; Mikero ExtractPbo or equivalent; optional p3d tooling | Tool output and legal permissions vary. Binarized/obfuscated content may limit recovery; no third-party payload may be redistributed automatically. | `skills/dayz-pbo-reverse-engineering/SKILL.md` |
| `dayz-test-ingame` | `source_verified` + `offline_tested` | DayZ Tools; AddonBuilder; DayZDiag; managed lifecycle; optional CF/VPP | Generated launcher parser and secret tests pass. Runtime launch was intentionally not run in this phase. 1.29 mod/tool changes require dependency checks before reuse. | `skills/dayz-test-ingame/SKILL.md`; `scripts/dev/knowledge-pack/tests/packctl/test_packctl_dayz_test_template_contract.py` |
| `dayz-vehicles` | `source_verified` + historical runtime evidence | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-pbo-build`; `dayz-test-ingame` | Several advanced proxy/winding rules are explicitly offline-only or pending in-game; preserve those labels. 1.29 vehicle fixes do not prove custom vehicle compatibility. | `skills/dayz-vehicles/SKILL.md:110-118,256-264`; local vanilla vehicle/action sources |
| `dayz-weapons` | `historical` + `source_verified` | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-animation-pipeline`; `dayz-pbo-build` | 1.29 Animation Editor workflow changed; experimental notes reported some weapon animation playback issues. Entity contracts retain project evidence but must be tested on the target build. | `skills/dayz-weapons/SKILL.md:32-64`; official 1.29 tool changelog |
| `rip-vehicle-import` | `offline_tested` + historical runtime evidence | `dayz-vehicles`; <vehicle-import> scripts; Blender; py3d; build/test pipeline | Winding-lineage and material-override focused tests pass. Broader profile test still has a known unrelated `builder.occ_struct` failure; no new vehicle was run in-game in this phase. | `skills/rip-vehicle-import/SKILL.md:251-265`; focused tests under the local `<vehicle-import>` evidence root |
| `rigorous-data-audit` | `cross_checked` | real code/data paths; independent evidence; runtime validation for release | Audit can prove source invariants, not runtime safety by itself. Its multi-angle procedure references subagents, but r21 execution was explicitly single-agent. | `skills/rigorous-data-audit/SKILL.md:76-77,132-182`; new r21 references |
| `enforce-script-reference` | `cross_checked` | vanilla `P:\scripts`; production mods as case studies | Adopted from the author's live store, not re-run in this phase. Treat signatures as hints until opened at `path:line` on the target build. | `skills/enforce-script-reference/SKILL.md` |
| `dayz-mod-workflow` | `cross_checked` | `enforce-script-reference`; domain skills; vanilla action/network sources | Process skill. Error catalog is dated project evidence; the protocol itself is engine-independent. Adopted from the author's live store, not re-run in this phase. | `skills/dayz-mod-workflow/SKILL.md` |
| `dayz-texture-pipeline` | `cross_checked` | DayZ Tools TexView/ImageToPAA; vanilla `.rvmat`; optional Blender/Substance | Map-suffix and Super-shader conventions were not re-exported in this phase. MatPBR `.emat` route is community-verified, not Bohemia-documented. | `skills/dayz-texture-pipeline/SKILL.md` |
| `dayz-particles` | `cross_checked` | vanilla `.ptc`/`.emat` library; `enforce-script-reference` | Particle files are plain text; GUIDs and the 276-entry catalog are version-dependent. Adopted from the author's live store, not re-run in this phase. | `skills/dayz-particles/SKILL.md` |
| `dayz-sound-system` | `cross_checked` | vanilla v1.24 sound/effect sources; `enforce-script-reference` | Audio is client-only. Prior-art configs (IMPWMODPart2, DoorLockSystem) are cited, not shipped. Adopted from the author's live store, not re-run in this phase. | `skills/dayz-sound-system/SKILL.md` |
| `dayz-ui-development` | `cross_checked` | vanilla `enwidgets.c` + `gui/`; optional Dabs Framework | Offline preview is not the engine. Dual Workbench/`config.cpp` registration still bites. Adopted from the author's live store, not re-run in this phase. | `skills/dayz-ui-development/SKILL.md` |
| `dayz-doors` | `cross_checked` | Object Builder; `model.cfg`; HouseNoDestruct; the three example models of novoGOD's tutorial *Doors_Buttons_Lesson* (not shipped) | Worked examples describe the tutorial's files in tables and cite them by path and line; the tutorial's files are not shipped. Expert Mode example has a documented source-to-Doors anomaly — read it before copying. Adopted from the author's live store, not re-run in this phase. | `skills/dayz-doors/SKILL.md`; `skills/dayz-doors/references/worked-examples.md` |
| `dayz-physics-engine` | `cross_checked` | vanilla v1.24 `enphysics.c` / `dayzphysics.c`; `enforce-script-reference` | Half the "obvious" API does not exist. Source-verified against v1.24; not re-run on 1.29 in this phase. | `skills/dayz-physics-engine/SKILL.md` |
| `dayz-preflight` | `historical` | DayZ Tools; `P:\` mount; Windows registry/Steam fallbacks | Read-only checker. Paths are env-var-first. Adopted from the author's live store; the script was not executed in this phase. | `skills/dayz-preflight/SKILL.md`; `skills/dayz-preflight/preflight.py` |
| `dayz-pbo-build` | `cross_checked` | AddonBuilder; optional pack `scripts/tools/py3d` >=1.5.0 | Reference validators live as prose, not a bundled `validate.py`. The old 1.4.0 wheel is out; install `pip install -e scripts/tools/py3d`. Adopted from the author's live store, not re-run in this phase. | `skills/dayz-build-pbo/SKILL.md`; `skills/dayz-build-pbo/references/validation-scripts.md` |
| `dayz-model-pipeline` | `cross_checked` | Blender headless; pack `scripts/tools/py3d` >=1.5.0; OpenSimplex/Pillow for textures | The old 1.4.0 wheel is out; install `pip install -e scripts/tools/py3d`. Winding/mass rules are source-checked; no new object was assembled in this phase. | `skills/dayz-model-pipeline/SKILL.md`; `skills/dayz-model-pipeline/references/py3d-direct-generation.md` |
| `dayz-p3d-audit` | `cross_checked` | pack `scripts/tools/py3d` >=1.5.0 | `scripts/audit_p3d.py` compiles and imports `py3d` normally. Version guard and install text now require 1.5.0; the silent-killer catalogue was not re-run on a live `.p3d` in this phase. | `skills/dayz-p3d-audit/SKILL.md`; `skills/dayz-p3d-audit/scripts/audit_p3d.py` |
| `dayz-p3d-inspector` | `cross_checked` | pack `scripts/tools/py3d` >=1.5.0; Three.js r0.147 CDN | Recipe JSON is lossy in 1.5.0 (`to_dict`/`from_dict` — see pack `scripts/tools/py3d/KNOWN-ISSUES.md`). `p3d_inspector_build.py` binds `Selection(lod.points, lod.faces)` to the live lists. Viewer HTML is not bundled. Adopted, not re-run. | `skills/dayz-p3d-inspector/SKILL.md`; `scripts/tools/py3d/KNOWN-ISSUES.md` |
| `dayz-proxy-align` | `cross_checked` | pack `scripts/tools/py3d` >=1.5.0; Three.js r0.147 CDN | `add_proxy` / `get_proxies` / `align_proxy` exist on 1.5.0. The 1.4.0 lifecycle facts stay as facts. Adopted, not re-run. | `skills/dayz-proxy-align/SKILL.md` |
| `dayz-animation-pipeline` | `cross_checked` | pack `scripts/tools/py3d` >=1.5.0; `scripts/tools/dayz-animation-formats`; Blender; DayZATool/Workbench for `.anm` | `SKILL.md` still names `py3d.read_p3d` as a validation option; that API does not exist (use `py3d.P3D(open(...))`). Historical 1.0.0 quirks stay as history. Helper scripts carry placeholder paths. Adopted, not re-run. | `skills/dayz-animation-pipeline/SKILL.md`; `skills/dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` |
| `mixamo-retarget` | `cross_checked` | Blender with `bpy`; Blender MCP | Experimental. Mixamo/Adobe FBX and characters are **not** redistributed. Fixture validation is still pending. | `skills/mixamo-retarget/SKILL.md` |
| `blender-assembly` | `cross_checked` | Blender with `bpy`; Blender MCP | Process skill. No third-party meshes ship. Adopted, not re-run. | `skills/blender-assembly/SKILL.md` |
| `blender-visual-review` | `cross_checked` | Blender with `bpy`; optional local VLM | A Blender render cannot judge DayZ winding. Adopted, not re-run. | `skills/blender-visual-review/SKILL.md` |
| `dayz-ai-patterns` | `cross_checked` | Expansion eAI source (not redistributed); `enforce-script-reference` | Expansion-specific. Cited commit is `8f75d554…`. Adopted from the live store, not re-run in this phase. | `skills/dayz-ai-patterns/SKILL.md` |
| `dayz-realistic-animation-director` | `cross_checked` | Blender with `bpy`; `blender-animation`; `dayz-animation-pipeline`; optional DayZDiag for the in-game gate | Offline validators compile. No third-party motion models or ARDY weights ship. Adopted, not re-run. | `skills/dayz-realistic-animation-director/SKILL.md`; `skills/dayz-realistic-animation-director/scripts/` |
| `uv-clean-atlas` | `cross_checked` | Blender 4.3+ headless; optional PartUV (not shipped) | Scripts compile; `sys.path` stays at the skill `scripts/` directory. One source-game brand token was neutralized. Adopted, not re-run. | `skills/uv-clean-atlas/SKILL.md`; `skills/uv-clean-atlas/scripts/` |
| `3d-generation-harness` | `cross_checked` | `blender-assembly`; `blender-visual-review`; `dayz-model-pipeline`; `dayz-p3d-audit`; optional external image-to-3D skill (not in this pack) | Process harness. `hunyuan3d-local` and kin are optional/external — the pack does not include them. Adopted, not re-run. | `skills/3d-generation-harness/SKILL.md` |
| `dayz-environment-hazards` | `unverified` (1.30-only feature set) | `enforce-script-reference`; `dayz-underground` | Written against 1.30.164014 Exp; citations re-checked on 1.30.164200 stable (2026-10-28) and 1.30.164289 (2026-11-09); not checked on 1.29. | `skills/dayz-environment-hazards/references/sources.md` |
| `dayz-motorbikes` | `unverified` (targets 1.30 only) | `dayz-vehicles`; `dayz-animation-pipeline`; `dayz-model-pipeline` | 1.30 `MotorbikeScript` contract, written against 1.30.164014 Exp and re-checked on 1.30.164200 stable (2026-10-28); the 1.29 stable scripts contain no `MotorbikeScript` (0 references, checked 2026-10-01). | `skills/dayz-motorbikes/references/sources.md` |
| `dayz-underground` | `unverified` (1.30-only terrain holes) | `dayz-basebuilding`; `dayz-test-ingame` | Written against 1.30.164014 Exp; citations re-checked on 1.30.164200 stable (2026-10-28) and 1.30.164289 (2026-11-09); not checked on 1.29. | `skills/dayz-underground/references/terrain-holes-evidence.md` |

## Stable-build evidence and update policy

- The exact local game/scripts baseline used for source checks is
  `1.29.0.163451`. For the 1.30 content it is `1.30.164289` since
  2026-11-09, and was `1.30.164200` from the 2026-10-28 re-check (§DayZ 1.30).
- The [official stable changelog](https://forums.dayz.com/topic/266379-stable-update-129/)
  identifies Steam Stable `1.29.163451`, released 2026-07-15.
- Before a DayZ stable update is adopted, pin its build, diff relevant vanilla
  contracts, rerun offline gates, then batch representative in-game tests.
- A row only advances to `runtime_verified` with a dated, reproducible test
  artifact. Absence of a listed breaking change means `unknown`, not “none”.
- Dependencies with their own release cycles must be pinned per project. This
  pack does not promise compatibility with an unpinned VPP, Expansion,
  TraderPlus, TraderX, Blender or ML-tool version.
