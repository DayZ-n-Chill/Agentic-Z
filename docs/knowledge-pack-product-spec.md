# Knowledge Pack product definition

The product definition the DayZ Modding Knowledge Pack was built against, brought in with the import. It is kept because its criteria carry measured DayZ facts (the persistence file primitives, the `.layout` line-ending measurement, the UI corpus counts, the vanilla evidence lines) and because it says which parts of the imported material are finished (`✓`) and which are still open (`❓`). It is not a plan for Agentic-Z.

- "The pack", "Git", "Obsidian" and "the user" are the Knowledge Pack's own repository, its author's notes vault and its author.
- `packctl`, `sources/`, `promotions/` and the `packctl` tests now live under `scripts/dev/knowledge-pack/`; tools live under `scripts/tools/`. `evals/cases/` and `evals/schema.json` name the Knowledge Pack's original eval files; the import's eval questions live in `evals/questions/`.
- `VANILLA`, `VAULT`, `CF_ROOT` and the other upper-case names are the Knowledge Pack's aliases for roots that are not in this repo. `VANILLA/` is `P:\scripts\`: the lines in "Evidence aliases" were opened on `P:\` during the import, and `P:\scripts\3_game\gameplay.c:117` (`ScriptRPC.Send`), `P:\scripts\3_game\entities\entityai.c:2910` (`OnStoreSave`) and `:2978` (`OnStoreLoad`), and `P:\scripts\3_game\tools\jsonfileloader.c:7` (`LoadFile`) and `:105` (`JsonLoadFile`, marked DEPRECATED at `:99`) are where the alias list says they are.

> **Final Product Definition (FPD).** This document sets the acceptable
> result. Live progress is not published: it is measured by running the gates
> (`python -m packctl gate --root . --report-dir ../pack-gate-reports`; the
> report directory goes outside the tree, see `docs/knowledge-pack-maintenance.md`).

## What is “done”

The next pack release will be a reproducible Git source and a
depersonalized ZIP that a person or agent can use to create, verify,
test, and publish DayZ mods without depending on private paths or turning
unverified claims into doctrine.

The finished product includes evidence infrastructure, iterative UI,
safe persistence, priority domain skills, py3d tooling, publishable MCP
methodology, and release/contribution documentation. All accepted
knowledge also remains in Obsidian and, when it is a domain invariant, in the
corresponding active skill.

**Scope and order confirmed with user on 2026-07-24.**

## Challenge clause

Each criterion serves the `Intent` of its group. If a simpler implementation
better protects that Intent, or a literal requirement contradicts it, it is raised in
the plan's Grill before implementing. The criterion does not change without approval
and an entry in the changelog.

## A — Source, compatibility and reproducible release

> **Intent:** that a single distributable truth exists and that Obsidian/skills
> receive verifiable promotions without becoming parallel sources or
> leaking private data.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| A1 | Git is canonical source of the distributable pack; Obsidian preserves full memory/evidence and installed skills are operational deployments | roles registered in ADR 001/002; no release is built from an installed copy | ✓ |
| A2 | Provenance inventory covers 100% of distributable files and adjudicates every pack↔source drift | validator returns 0 `SOURCE-UNMAPPED`, 0 conflicts without decision | ✓ |
| A3 | All skills comply with the Agent Skills specification and frontmatter ≤1024 characters | `skills-ref validate` with UTF-8: N/N valid, exit 0 | ✓ |
| A4 | Two clean builds of the same commit produce byte-identical ZIP and identical manifests | two identical SHA-256; order, timestamps, and encoding normalized | ✓ |
| A5 | Machine-readable manifest declares release, commit, DayZ build, schema, licenses, hashes, and counting convention | schema validation exit 0; declared count = actual files per explicit convention | ✓ |
| A6 | Root MIT license, third-party notices, and “do not redistribute private paths/inputs” policy | license audit: 0 distributable files without coverage; py3d preserves upstream MIT | ✓ |
| A7 | Matrix per skill with tested DayZ build, date, dependencies, and breaking changes | 100% of skills listed; none claims compatibility without evidence | ✓ |
| A8 | Zero secrets, identities, private paths, or broken local links not allowlisted | scanner and link audit exit 0 on built ZIP | ✓ |
| A9 | All accepted knowledge has repo↔Obsidian↔applicable skill routing and promotion receipt per commit/hash | `PROMOTION-UNROUTED=0`, `PROMOTION-DRIFT=0`; readback of all configured targets; `not_applicable` requires reason and is prohibited for domain invariants | ✓ |

## B — Evidence, APIs, evaluations, and preflight

> **Intent:** that the assistant learns verifiable contracts and that an improvement
> of a skill can be demonstrated against a baseline, not merely look better.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| B1 | Each new executable claim/snippet records source, build/commit, `path:line`, license, date, verification level, and promotion routing | provenance audit: 0 executable claims without record or destination | ✓ |
| B2 | Regenerable index `dayz-api-index`, vanilla-first, read-only, with allowed-roots and rejection of incompatible build/schema | fixtures active/commented/nonexistent/collision class; path escape and build mismatch fail closed | ✓ |
| B3a | Catalog mechanical regression harness: each case in `evals/cases/` is well-formed and its fixed verdict matches its assertions | `packctl gate` walks variants and fails with `EVAL-UNEXPECTED-VERDICT` if any deviates; each run emits `grading.json` and evidence. **Does not compare against baseline**: the graded response is written in the case itself | ✓ |
| B3b | At least one live `DISCRIMINATING` case exists: same prompt and fixture, N runs per arm, skill mounted versus absent, and arm without skill below its ceiling | `pass_rate(with_skill) >= min_pass_with_skill`, `pass_rate(without_skill) <= max_pass_without_skill` and difference `>= min_discrimination`, on a real runner and with skill tree hash recorded per arm | ❓ |
| B4 | Audited StarDZ errors exist as negative cases | evals reject false `autoptr`, false overload, false `Managed`, `JsonLoadFile`, incomplete `OnDrop`, and invalid Dabs | ✓ |
| B5 | CI-like pipeline executes skill validation, provenance, links, privacy, Python, py3d, and reproducible build | one local command returns 0; targeted mutations produce stable codes and non-zero exit | ✓ |
| B6 | Minimal template `@MyMod` implements recommended structure, config contracts, build, and test mission, consuming same release-grade gates as `dayz-workshop-release` | scaffold is instantiated without private paths; preflight and dry-run verify new/structural artifact and a failed publication preserves previous PBO | ❓ |
| B7 | Offline simulators reduce iterations without posing as engine substitutes | config parser and loot/CE/physics validators have positive, negative fixtures and explicit limits | ❓ |
| B8 | `dayz-api-index` v2 distinguishes liveness `active/commented/missing`, parent chain, guards, and namespace without replacing reading of source | structural fixtures cover liveness, cycles, `#ifdef`, overrides/config, and comments; preserves allowed-roots/build/schema/tree digest | ❓ |

## C — `dayz-ui-lab` and `dayz-ui` skill

> **Intent:** that an agent can implement a requested interface, observe
> a deterministic result, compare, correct, and iterate before the real gate in
> DayZDiag, without confusing offline preview with engine truth.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| C1 | Honest parser closes B19/B20 | 319/319 public corpus + 46/46 TraderX + LFPG, exit 0; 0 false `missing-child-block`; CRLF/LF verified in DayZDiag | ✓ |
| C2 | Versionable scenarios compose shell, subviews, and collections, detecting cycles and broken paths | fixture shell→subview→3 cards preserves order/identity/geometry at 1920×1080 and 3440×1440 | ✓ |
| C3 | Semantic render is deterministic across clean runs; RGBA/PNG are only canonical within a fixed raster profile, and resolve first-party assets | two byte-identical `render.json` without timestamps/private paths; within fixed profile, two byte-identical RGBA buffers and PNGs; outside profile, `non_canonical` artifact; fixture `.styles` + `.imageset` 9-slice + font without silent fallback | ❓ |
| C4 | Actionable diff identifies broken reference, clipping, overlap, and missing state per widget/scenario | negative fixture produces exactly the expected findings; green control produces 0 | ✓ |
| C5 | Positive corpus = VPP/Expansion/TraderPlus/TraderX; negative = LFPG Sorter V4 TEST; third parties are not redistributed | manifests by commit/hash and allowlist audit | ✓ |
| C6 | DayZDiag rules as golden; a first-party ingame probe exports runtime geometry/state and calibrates defined resolutions/aspect ratios | coherent `engine-capture-v1` bundle per scenario/run with screenshot PNG, full structured snapshot, sanitized RPT, build, and resolution; manual import suffices to close gate; offline deltas quantified per widget, without invented threshold | ❓ |
| C7 | Pooling is only promoted with full lifecycle and measured benefit | create/unlink vs reuse: same output; 0 ghost state/duplicate callback; reproducible benchmark | ❓ |
| C8 | UI skill incorporates architecture, visual Forward Contract, and verified diagnostic trees | evals “empty/style/collection/tooltip/font/offline≠engine” pass | ❓ |

**Evidence executed on 2026-07-28** for `C1` and `C5`, measured on the tree and
re-executable from the repo with
`python scripts/tools/dayz-ui-lab/dayz_ui_lab/corpus.py --root .`:

```
vpp-admin-tools   69/69    dayz-expansion 234/234    traderplus-v1 16/16
traderx           46/46    lfpowergrid     11/11
totals: 376/376 layouts parse across 5/5 corpora, 0 diagnostics emitted
provenance: 1 tracked .layout, 0 redistributed, 364 third-party layouts compared
verdict=PASS  (exit 0)
```

- **C1** — `319/319` public (VPP 69 + Expansion 234 + TraderPlus 16), `46/46`
  TraderX, and `11/11` LFPG, exit `0`. The *0 false `missing-child-block`* is **measured**,
  not inferred from B19 removing the branch: the runner counts the diagnostics that
  the parser actually emits and the total is `0`; if someone re-introduced one,
  `CORPUS-DIAGNOSTICS-EMITTED` turns red. The CRLF/LF span was verified in
  DayZDiag `1.29.163451` with the probe `LF_UIProbe` (`len=10`, LF and CRLF identical,
  value `"Alpha\nBeta"`).
- **C5** — `scripts/tools/dayz-ui-lab/corpora/manifest.json` pins the four references
  by commit (VPP `dc22e420`, Expansion `8d3a453b`, TraderPlus `d0cd39f1`) or by
  Workshop manifest (TraderX `3069958660046119589`), each with license and
  redistribution restriction. **The three PBO hashes of TraderX were
  recomputed locally** and reproduce those of the research, instead of being transcribed.
  The provenance audit compares **by content, not by path**, the 364
  third-party layouts against what is tracked in the repo: `0` redistributed, and the
  only tracked `.layout` is the first-party probe fixture. A third-party
  layout planted under another name is detected by a dedicated test.

> None of the three reference repos is redistributed. The pack carries only
> URL, commit/manifest, hash, and license; the bytes are provided by the operator via
> `scripts/dev/knowledge-pack/sources/local-roots.json`, which is not tracked. A corpus without configured root
> **fails the gate**, it is not silently skipped: "not measured" and "passes" cannot
> look alike.

**Evidence executed on 2026-07-28** for `C2`, measured on the tree:

```
python scripts/tools/dayz-ui-lab/dayz_ui_lab/scenario.py \
    --scenario scripts/tools/dayz-ui-lab/fixtures/scenarios/three-cards/scenario.json \
    --viewport 1920x1080   → verdict=PASS, exit 0, 17 widgets
    --viewport 3440x1440   → verdict=PASS, exit 0
```

- **Identity and order** — the three cards preserve `sibling_index` `0,1,2`, three
  distinct ids, and **the same three ids in both resolutions**. Geometry
  does change (card width `497.664` at 1920×1080, `891.648` at 3440×1440), which is
  what separates "preserves identity" from "ignores viewport": without that assertion,
  an implementation that did not read resolution would pass the criterion.
- **Determinism** — two clean runs of the same scenario/viewport
  produce identical bytes (SHA-256 `1c307898…` both); the other resolution gives
  `2b83d571…`. Without timestamps or absolute paths.
- **Fail-closed** — the six negative scenarios return exit `1` and their exact
  code, one per fixture: `SCENARIO-SCHEMA-INVALID`, `SCENARIO-CYCLE`,
  `SCENARIO-LAYOUT-MISSING`, `SCENARIO-STATE-MISSING`,
  `SCENARIO-BINDING-MISSING`, and `SCENARIO-MOUNT-MISSING`. The seventh,
  `SCENARIO-DUPLICATE-WIDGET-ID`, is a defensive guard: with well-formed
  ancestry and contiguous sibling indices it cannot trigger from a JSON, so
  it is tested by injecting the collision, not weakening the algorithm.
- **C5 boundary intact** — the first-party allowlist changes to two named
  directories to host fixtures, but the C5 guarantee is upheld by the
  **content audit**, which was untouched and already has a test demonstrating
  that it catches a third-party layout replanted inside the allowed directory. A
  `.layout` in a third location continues to give
  `CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY`, with its own test. The gate now measures
  `5 tracked .layout, 0 redistributed`.

**Evidence executed on 2026-07-29** for `C4`, measured on the tree:

```
python scripts/tools/dayz-ui-lab/dayz_ui_lab/diff.py \
    --observed  scripts/tools/dayz-ui-lab/fixtures/scenarios/defect-overlays/observed.json \
    --scenario  scripts/tools/dayz-ui-lab/fixtures/scenarios/defect-overlays/scenario.json
  → verdict=FAIL, exit 1, findings=4
    DIFF-REFERENCE-MISSING · DIFF-CLIPPING · DIFF-OVERLAP · DIFF-STATE-MISSING
positive control three-cards → verdict=PASS, exit 0, findings=0
```

- **Exactly four, with equality and not with "at least"** — the test asserts
  `len(findings) == 4` and the exact set of codes. The four are those named by
  `SC-009`.
- **The negative fixture is not synthetic.** `observed.json` **is** the output of
  the emitter for that scenario at `1000×1000`, perturbed in exactly two places:
  a dangling child and a missing state. The other two defects —clipping and
  overlap— are intrinsic to the layout and reproduced by the real pipeline. Verified
  by comparing the document leaf by leaf against `render.py`: they differ in **two
  leaves**, both injected.
- **Actionable, not just detected** — each finding carries scenario, widget id,
  property, expected, observed, and `path:line:column` of the layout that must be
  edited; no path is absolute.
- **Matching by identity** — reversing the order of the widget list
  produces zero findings, verified by test. The ids are those preserved by the
  render from the compositor.
- **Each detector tested in red and in green**, with clipping and overflow
  mutually excluding each other in both directions.
- **Known residual, recorded as `BUG-023` and out of scope for `C4`**: the
  diff validates that `scenario_id` matches but **not viewports**, so an
  observed captured at another resolution produces geometry findings without warning
  of the mismatch. Matters for Task 6, which is what will plug engine captures
  into this side.

## D — `dayz-persistence`

> **Intent:** that updating, migrating, truncating, or rolling back never turns
> an incompatibility into silent corruption or avoidable loss.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| D1 | Skill separates vanilla stream, CF ModStorage, and files/sidecars | three contracts and three independent fixture suites | ✓ |
| D2 | Versioning/migration covers fresh, legacy, known, future, truncated, same-build upgrade, and rollback | complete matrix produces expected verdict/action, without accepted partial read | ✓ |
| D3 | Sidecars use temp→verify→replace, backup, and fail-closed recovery | fault injection at each I/O boundary preserves original or recoverable evidence | ✓ |
| D4 | Deprecated APIs and incomplete examples are not recommended | evals reject `JsonLoadFile` as new pattern and headers bound only to DayZ build | ✓ |
| D5 | Every persistent change documents legacy, post-change data in rollback, and alternative without format change | checklist and rigorous-data-audit without blocking findings | ✓ |

**Evidence executed on 2026-07-28** (each `✓` with the line that closes it, measured on
`dcf0671`, not inferred). Persistence spec checklist: 16/16.

- **D1** — three contract references in `skills/dayz-persistence/references/` and three
  simulators that share no code: `test_persistence_router.py` parses the three modules
  with `ast` and requires their imports to be disjoint, so factoring out a common serializer
  turns the gate red. Router with `needs_clarification` for ambiguous input.
- **D2** — `test_persistence_migration.py`: the 7 cells with their four columns (verdict,
  bytes consumed, preserved state, action) and **mutation check per cell** —mutating one byte
  changes the verdict in 7/7—. `truncated` never gives `ok` and discards the entire partial state;
  `future-version` leaves the file hash identical and emits a single log line per
  window.
- **D3** — `test_persistence_sidecar.py`: the **9** I/O boundaries with injected failure, each
  with the invariant "original intact **or** recoverable evidence". Includes the real
  window of the replace (failure between `delete_file` and `copy_file`, missing destination and recoverable
  `.tmp`+`.bak`) and a test requiring that the FS expose exactly the nine primitives of
  DayZ, without `rename` or `move`.
- **D4** — `evals/cases/persistence-deprecated-api.json`, `persistence-mod-version.json`, and
  `persistence-migration-rollback.json`, executed by the harness (`evals/cases/*.json`, with
  closed inventory in `scripts/dev/knowledge-pack/tests/packctl/test_packctl_evals.py`), each with `current=PASS` /
  `absent=FAIL`. Also verified that no assertion `value` appears in the `prompt` of
  its own case.
- **D5** — `test_persistence_checklist.py`: the checklist fails exactly once per
  missing element (legacy, rollback, alternative without format change), accumulates without
  short-circuit, and rejects an alternative presented *after* the change. Plus
  `rigorous-data-audit` **without blocking findings**: 1 P2 and 2 P3, all three fixed in
  `dcf0671`.
  **Declared scope of that audit:** executed **single-agent**, because subagents
  require explicit authorization in this project (`project-brief.md`) and the session did not
  have it; precedent is recorded in `compatibility-matrix.md`. Completed full Step 1
  —mechanical checks, which is where the skill itself states that reasoning
  fails— and 1-to-1 verification of each finding against the file. Step 2 did **not** run
  (eight angles in parallel) nor Step 4 (implementer-grade with fresh context).
  Report: `VAULT/10_Projects/DayZ_Modding_Knowledge_Pack/reviews/2026-07-28-phase03-rigorous-data-audit.md`.

## E — Skills and domain knowledge

> **Intent:** cover the areas that currently force the assistant to improvise,
> keeping modules small and research vanilla-first.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| E1 | `dayz-multiplayer-sync` covers RPC, reliability, ownership, prediction, and desync diagnosis | client/server fixtures, fail-closed auth, and two local clients | ❓ |
| E2 | `dayz-sound-particles` covers `.ptc`, soundsets, Effect systems, and occlusion | source-pinned examples + build/smoke per subsystem | ❓ |
| E3 | `dayz-terrain` covers basic map, roadgraph, and CE | minimal reproducible project and roadgraph/CE checks | ❓ |
| E4 | `dayz-workshop-release` covers mod.cpp, dependencies, signing/bisign, images, changelog, preflight, invalidatable cache, and transactional publication | dry-run requires new PBO, header/prefix/entries, signature when applicable, and fatal-free log; input/toolchain changes invalidate cache and a failure preserves previous bytes/manifest | ❓ |
| E5 | Vault incorporates RPT decision tree, mod architectures, and measured performance guide | deduplicated branches with evidence; budgets declare build/hardware/corpus | ❓ |
| E6 | Disease/modifiers and plugin lifecycle are audited vanilla-first before becoming skill/reference | research with `path:line`, sides, lifecycle, and fixtures; unknowns remain marked | ❓ |
| E7 | Compatibility is reviewed against pinned stable and records breaking changes | matrix updated from local/official sources and verifiable date | ❓ |

## F — py3d and export validation

> **Intent:** that 3D tooling reduces iterations and blocks corruption or
> non-canonical models before binarize.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| F1 | Proxies support add/remove/align with rotation and round-trip | fixtures with known matrices; save→reload preserves transform and selection | ✓ |
| F2 | RTM/SEAnim/animation helpers have explicit contract and limits | round-trip or export fixture compared with accepted reference | ✓ |
| F3 | Pre-export validates winding, bones, and scale | positive/negative fixtures and stable codes; 0 silent repair | ✓ |
| F4 | Read-only ODOL reader exists for anatomy/parity, with declared coverage and limitations, without adding ODOL writer | legally distributable v53/v54/v55 fixtures, self-diff, and fail-closed boundary/oob failures | ✓ |
| F5 | py3d keeps its entire suite green and a single canonical distribution | baseline 130 pass/10 skip does not regress; wheels/rollout hashes pinned | ✓ |

## G — Publishable MCP and automation

> **Intent:** make test methodology reproducible even without private
> bridge and expand capabilities without weakening lifecycle/ownership.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| G1 | Bridge protocol documents commands, schemas, errors, version, and extension | request/response examples validated against schema and current bridge | ❓ |
| G2 | Lite mode works with DayZDiag + filePatching + ingame scripts, without private bridge | minimal reproducible spawn→action→RPT/verdict ladder | ❓ |
| G3 | An orchestrator integrates test-ingame + MCP and incremental watch mode | fixture change triggers exact rebuild/retest; lease and run_id remain fail-closed | ❓ |
| G4 | Sequences, crash/RPT detection, screenshot diff, telemetry, and two clients have separate gates | each capability has fixture and verdict; screenshot adapter imports `engine-capture-v1`, selects a single client by `run_id`, and preserves lossless PNG or fails closed; no performance numbers without measurement | ❓ |
| G5 | VPP/init.c alternatives and companions are documented with limits; dayz-labs remains pinned, optional, and without lifecycle authority, and Cheat Engine is not a recommended dependency | capability/reliability/risk/license/version matrix verified; gates exclude installer and `start/stop/restart`; WPF does not count as `.layout` evidence | ❓ |

## H — Ecosystem, contribution, and polish

> **Intent:** that the pack is maintainable, teachable, and expandable without duplication
> or dependency on the original machine.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| H1 | Workbench/Mikero/viewers integration documented with versions and license | commands smoked or marked as unverified companion | ❓ |
| H2 | Clean reproducible server environment uses VM or viable alternative, chosen after spike | second machine/VM executes smoke without private junctions | ❓ |
| H3 | Contribution guide defines source map, evidence, tests, license, promotion to Obsidian/skills, and release | fixture contribution goes through end-to-end validation and promotion | ❓ |
| H4 | Duplicate notes are consolidated without losing claims/evidence | old→canonical map; link audit and semantic diff reviewed | ❓ |
| H5 | Minimal diagrams cover skeleton, proxy frame, and Construction quartet lifecycle | first-party assets, valid links, and human review | ❓ |
| H6 | Risk register/known engine bugs lives versioned and distinguishes crash/exception/corruption/degradation/cosmetic | each entry has concrete evidence, build, and severity | ❓ |

## Out of scope

- Importing StarDZ as a monolithic skill or copying unverified snippets.
- Bundling GPL, DPL-ND, CC-NC code/assets, vanilla DayZ, or third-party mods.
- Integrating dayz-labs/Lake lifecycle as a parallel authority to DayZ_MCP.
- Running Enforce in the browser or promising engine-faithful 3D previews.
- Writing ODOL.
- Setting CPU/network/widgets budgets without reproducible benchmark.
- Publishing repo, release, or Workshop during planning phase.
- Treating Obsidian or installed skills as parallel release sources;
  promotion occurs from Git after gates and preserves private evidence only in
  Obsidian.

## Parity references

- Baseline ZIP SHA-256
  `E63C26C5C385E3037B4AFE9C918B3A9DE9E12CC0AF876316214518BF852735E5`;
  root commit `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.
- Agent Skills reference validator: **`skills-ref==0.1.1`** from PyPI
  (<https://agentskills.io>), whose console script is **`agentskills`**. Replaces
  the previous pin by commit `38a2ff82958afee88dadf4831509e6f7e9d8ef4e`, which ceased
  to be retrievable: that commit is no longer in `anthropics/skills` and its HEAD does
  not retain the `skills-ref/` directory. A PyPI version is an immutable release
  artifact, so the new pin is also more stable than the old one.
  Reproducible installation: `python -m venv <root> && <root>/Scripts/pip install`
  `skills-ref==0.1.1`, and `PACK_SKILLS_REF_ROOT=<root>`.
- Initial DayZ compatibility: `1.29.0.163451`, verified 2026-07-24. Stable
  branch moved to `1.29.0.163709` on 2026-08-15; **nothing has been re-verified
  against that build** and the matrix states so row by row. Since 2026-10-15 the
  stable branch is DayZ 1.30 (`1.30.164289` since 2026-11-04): the vanilla line
  numbers in the skills are that build's unless a citation names another, the
  matrix levels are still the 1.29 ones, and `compatibility-matrix.md` §DayZ 1.30
  says what was checked on 1.30.
- UI: VPP and Expansion pinned by commit; TraderX by manifest
  `3069958660046119589` and PBO hashes; LFPG Sorter V4 TEST as negative.
- Audited prior art: dayz-labs `dbd6ad3e...`, Lake `ac56f369...`,
  StarDZ `dbdcd23b...`.
- py3d upstream `7acd58b`/tag `v1.0` and fork release `1.5.0`; distribution
  `py3d-dayz` (importable module remains `py3d`; `py3d` on PyPI is another
  library). Reproducible wheel `py3d_dayz-1.5.0-py3-none-any.whl` SHA-256
  `16eac9218cddb02b52b533540c0259c33d5e5b2d6ad2cd28444ef049d608a73b`,
  resealed on 2026-08-15 by explicit user decision when synchronizing the
  pack with published fork `willy92wins/py3d-dayz@c50321c`, which was
  ahead. Reproducibility is **toolchain-bound**: valid for
  `setuptools==83.0.0` and Python `3.14.3`, both declared in
  `rollout/wheel-manifest.json`.
- **Why the jump to `1.5.0` and not another reseal at `1.4.0`.** That name came
  to designate three different contents —the `cc014a4330e8…` seal prior to the
  existence of `scripts/tools/py3d/pyproject.toml`, the `c635bf7ec12c…` of `913192d`, and the
  `8043b796…` hardened by `4271ff0`— and the only thing separating them was the manifest
  seal. Bumping the version restores the property that a name
  identifies a content; `1.4.0` remains retired as ambiguous. The published
  fork remains tagged `1.4.0` with these exact same bytes: upon pushing it must
  also be bumped to `1.5.0`, or there will again be two contents under one
  name.

Evidence aliases used in plans:

- `VANILLA/3_game/entities/entityai.c:2893-2910,2954-2978` — contract
  `OnStoreSave`/`OnStoreLoad`.
- `VANILLA/3_game/tools/jsonfileloader.c:7-40,99-105` — `LoadFile` and
  deprecation of `JsonLoadFile`.
- `CF_ROOT/Entities/ItemBase.c:22-84` and
  `CF_ROOT/ModStorage/CF_ModStorageObject.c:25-76,80-156` — integration and
  framing of CF ModStorage.
- `VANILLA/3_game/gameplay.c:104-117` — signature of `ScriptRPC.Send`.
- `VAULT/AI/10_Projects/DayZ_UI_Research/project-brief.md:25-26` and
  `research/2026-07-24-ui-positive-reference-corpus-codex.md:64-105` —
  baseline B19/B20 and UI corpora.

Phase 01 will pin revision, hash, and local root of each alias outside Git.

## Scope changelog

- 2026-07-24 — initial scope and order approved by user.
- 2026-07-24 — source reconciliation added as P0 gate after measuring drift in
  the 14 skills; does not change order, makes it safe.
- 2026-07-24 — user requires that all gathered knowledge also remain
  in Obsidian and applicable skills; A9 and ADR 002 added.
- 2026-07-24 — three post-Phase 01 deltas approved: B8 for
  `dayz-api-index` v2 without blocking UI, E4/B6 with postconditions/cache/transactional
  publishing, and G5 with dayz-labs solely as pinned companion without lifecycle.
- 2026-07-25 — Phase 02 amendments approved: cross-run semantic
  determinism and raster only within pinned profile; structured in-game snapshot;
  first-party vanilla-first probe without mandatory Dabs; schema
  `engine-capture-v1` now and run-bound/lossless MCP adapter in Phase 05.
  `py3d` left out of this execution and continues in parallel under Phase 04.
- 2026-07-26 — B3 split into B3a/B3b after measuring that mechanical catalog does not
  compare against baseline; approved by user. Applied 2026-07-27:
  `evals/schema.json:104-114,138-140` requires `response` as a field of the case itself
  and `scripts/dev/knowledge-pack/packctl/gate.py:262-274` compares that pinned verdict against assertions
  in same file, so the 18/18 measure catalog coherence, not skill
  effectiveness. B3a preserves original text with that written reservation; B3b remains
  at `❓` until a real run proves it.
- 2026-07-25 — Phase 04 closed: F1–F5 pass gate clean; py3d 1.4.0,
  strict RTM/SEAnim, MLOD preflight, and ODOL v53–v55 reader distributed
  from Git with verified fixtures and provenance. Rollout to active
  installations remains separate and requires final authorization.
