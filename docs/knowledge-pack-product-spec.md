# Acceptance criteria for packctl, the offline tools and the knowledge pack skills

What `packctl` (`scripts/dev/knowledge-pack/`), the offline tools under `scripts/tools/` and the knowledge pack skills are held to: each criterion, how it is verified, and whether it is met (`✓`) or still open (`❓`). The criteria carry measured DayZ facts (the persistence file primitives, the `.layout` line-ending measurement, the UI corpus counts, the vanilla evidence lines), and the page says which parts are finished and which are not. It is not a plan for the mod team, and an open criterion is not a task: new work goes through `docs/wishlist.md`.

- A `✓` records the last measurement. The evidence blocks give its date and the command, and nothing here is re-measured automatically: run the check named in the row before you rely on it.
- Group A, and the rows of group B marked "gate run", are measured by `packctl validate` and `packctl gate` on every run, so no status is recorded for them here. `docs/knowledge-pack-maintenance.md` says how to run them.
- `packctl` and its tests are under `scripts/dev/knowledge-pack/`, the tools under `scripts/tools/`, and the mechanical eval cases under `evals/cases/` with their schema in `evals/schema.json`.
- Vanilla citations are under `P:\scripts\`. The lines in [Vanilla evidence](#vanilla-evidence) were opened on `P:\` on DayZ 1.30.

## What is "done"

A release is a reproducible ZIP that `packctl build` makes from a committed tree, and that a person or agent can use to create, verify, test and publish DayZ mods without depending on private paths or turning unverified claims into doctrine.

The finished product includes evidence infrastructure, iterative UI, safe persistence, priority domain skills, py3d tooling, a publishable in-game test methodology, and release and contribution documentation.

## Challenge clause

Each criterion serves the `Intent` of its group. If a simpler implementation protects that Intent better, or a literal requirement contradicts it, raise that before implementing. A criterion does not change without the owner's approval.

## A — Source, compatibility and reproducible release

> **Intent:** that a single distributable truth exists and that installed
> skills receive verifiable promotions without becoming parallel sources or
> leaking private data.

| # | Criterion | How it is verified |
|---|---|---|
| A1 | The repository is the one editable source of what is distributed; installed skill trees are deployments, never sources | no release is built from an installed copy: `packctl build` and `packctl promote` read a clean commit and refuse a dirty tree |
| A3 | All skills comply with the Agent Skills specification and frontmatter ≤1024 characters | `skills-ref validate` with UTF-8: N/N valid, exit 0 |
| A4 | Two clean builds of the same commit produce a byte-identical ZIP and identical manifests | two identical SHA-256; order, timestamps, and encoding normalized |
| A5 | A machine-readable manifest inside the ZIP declares what the release holds | the manifest validates against `scripts/dev/knowledge-pack/packctl/manifest.schema.json`; declared count = actual files |
| A7 | A matrix per knowledge pack skill gives the tested DayZ build, date, dependencies, and breaking changes | every knowledge pack skill has a row in `docs/compatibility-matrix.md`; none claims compatibility without evidence |
| A8 | Zero secrets, identities, private paths, or broken local links that are not allowlisted | the privacy and link checks of `packctl validate` report no finding |
| A9 | Every promoted skill has a route and a promotion receipt per commit and hash | `PROMOTION-UNROUTED=0`, `PROMOTION-DRIFT=0`; readback of all configured targets |

## B — Evidence, APIs, evaluations, and preflight

> **Intent:** that the assistant learns verifiable contracts and that an improvement
> of a skill can be demonstrated against a baseline, not merely look better.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| B1 | Each new executable claim or snippet records its evidence: DayZ build, `path:line`, date, and verification level | the claims check of `packctl validate` reports no claim marker without a record | gate run |
| B2 | Regenerable API index (`packctl api-index`), vanilla-first, read-only, with allowed-roots and rejection of incompatible build/schema | fixtures active/commented/nonexistent/collision class; path escape and build mismatch fail closed | ✓ |
| B3a | Catalog mechanical regression harness: each case in `evals/cases/` is well-formed and its fixed verdict matches its assertions | `packctl gate` walks the variants and fails with `EVAL-UNEXPECTED-VERDICT` if any deviates; each run emits `grading.json` and evidence. **Does not compare against a baseline**: the graded response is written in the case itself | ✓ |
| B3b | At least one live `DISCRIMINATING` case exists: same prompt and fixture, N runs per arm, skill mounted versus absent, and arm without skill below its ceiling | `pass_rate(with_skill) >= min_pass_with_skill`, `pass_rate(without_skill) <= max_pass_without_skill` and difference `>= min_discrimination`, on a real runner and with skill tree hash recorded per arm | ❓ |
| B4 | Known wrong Enforce Script claims exist as negative cases | evals reject false `autoptr`, false overload, false `Managed`, `JsonLoadFile`, incomplete `OnDrop`, and invalid Dabs | ✓ |
| B5 | One pipeline executes skill validation, links, privacy, Python compilation, the test folders, the eval cases, and a reproducible build | one local command (`packctl gate`) returns 0; targeted mutations produce stable codes and non-zero exit | gate run |
| B6 | Minimal template `@MyMod` implements recommended structure, config contracts, build, and test mission, consuming the same release-grade gates as the release skill of E4 | scaffold is instantiated without private paths; preflight and dry-run verify new/structural artifact and a failed publication preserves previous PBO | ❓ |
| B7 | Offline simulators reduce iterations without posing as engine substitutes | config parser and loot/CE/physics validators have positive, negative fixtures and explicit limits | ❓ |
| B8 | API index v2 distinguishes liveness `active/commented/missing`, parent chain, guards, and namespace without replacing reading of source | structural fixtures cover liveness, cycles, `#ifdef`, overrides/config, and comments; preserves allowed-roots/build/schema/tree digest | ❓ |

B3a measures that the catalog is coherent, not that a skill works: `evals/schema.json` requires `response` as a field of each variant of a case, and the gate compares that pinned response's verdict with the assertions in the same file. B3b stays at `❓` until a real run proves it.

## C — `dayz-ui-lab` and the UI skill

> **Intent:** that an agent can implement a requested interface, observe
> a deterministic result, compare, correct, and iterate before the real gate in
> DayZDiag, without confusing offline preview with engine truth.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| C1 | The format parser reports no false diagnostic on real layouts | 319/319 public corpus + 46/46 TraderX + 11/11 negative set, exit 0; 0 false `missing-child-block`; CRLF/LF verified in DayZDiag | ✓ |
| C2 | Versionable scenarios compose shell, subviews, and collections, detecting cycles and broken paths | fixture shell→subview→3 cards preserves order/identity/geometry at 1920×1080 and 3440×1440 | ✓ |
| C3 | Semantic render is deterministic across clean runs; RGBA/PNG are only canonical within a fixed raster profile, and resolve the mod's own assets | two byte-identical `render.json` without timestamps/private paths; within fixed profile, two byte-identical RGBA buffers and PNGs; outside profile, `non_canonical` artifact; fixture `.styles` + `.imageset` 9-slice + font without silent fallback | ❓ |
| C4 | Actionable diff identifies broken reference, clipping, overlap, and missing state per widget/scenario | negative fixture produces exactly the expected findings; green control produces 0 | ✓ |
| C5 | Positive corpus = VPP Admin Tools, DayZ Expansion, TraderPlus, TraderX; negative = the `lfpowergrid` set; none of their layouts is kept in this repo | manifest pins by commit or hash, and a content audit of every tracked `.layout` | ✓ |
| C6 | DayZDiag rules as golden; an in-game probe exports runtime geometry/state and calibrates defined resolutions/aspect ratios | coherent `engine-capture-v1` bundle per scenario/run with screenshot PNG, full structured snapshot, sanitized RPT, build, and resolution; manual import suffices to close gate; offline deltas quantified per widget, without invented threshold | ❓ |
| C7 | Pooling is only promoted with full lifecycle and measured benefit | create/unlink vs reuse: same output; 0 ghost state/duplicate callback; reproducible benchmark | ❓ |
| C8 | UI skill incorporates architecture, visual Forward Contract, and verified diagnostic trees | evals “empty/style/collection/tooltip/font/offline≠engine” pass | ❓ |

**Evidence executed on 2026-07-28** for `C1` and `C5`, with all five corpora
configured, by
`python scripts/tools/dayz-ui-lab/dayz_ui_lab/corpus.py --root .`:

```
vpp-admin-tools   69/69    dayz-expansion 234/234    traderplus-v1 16/16
traderx           46/46    lfpowergrid     11/11
totals: 376/376 layouts parse across 5/5 corpora, 0 diagnostics emitted
verdict=PASS  (exit 0)
```

- **C1** — `319/319` public (VPP 69 + Expansion 234 + TraderPlus 16), `46/46`
  TraderX, and `11/11` for the negative set, exit `0`. The *0 false `missing-child-block`* is **measured**,
  not inferred from the branch having been removed: the runner counts the diagnostics that
  the parser actually emits and the total is `0`; if someone re-introduced one,
  `CORPUS-DIAGNOSTICS-EMITTED` turns red. The CRLF/LF span was verified in
  DayZDiag `1.29.163451` with the probe `LF_UIProbe`
  (`scripts/tools/dayz-ui-lab/probe/LF_UIProbe/`): `len=10`, LF and CRLF identical,
  value `"Alpha\nBeta"`.
- **C5** — `scripts/tools/dayz-ui-lab/corpora/manifest.json` pins the four references
  by commit (VPP `dc22e420`, Expansion `8d3a453b`, TraderPlus `d0cd39f1`) or by
  Workshop manifest (TraderX `3069958660046119589`). **The three PBO hashes of TraderX were
  recomputed locally**, not transcribed.
  The audit compares **by content, not by path**, the layouts of the four
  references (364 compared in that run) against what is tracked in the repo: `0` kept. A corpus
  layout planted under another name is detected by a dedicated test. The audit
  also reports any tracked `.layout` outside the tool's own fixture folders as
  `CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY`.

> None of the corpora is in this repo. The manifest carries only the identity
> of each (commit or Workshop manifest, and hashes); the operator supplies the
> bytes through `scripts/dev/knowledge-pack/sources/local-roots.json`, which is not tracked. A corpus without a configured root
> **fails the gate**, it is not silently skipped: "not measured" and "passes" cannot
> look alike. Without that file the run reports `CORPUS-LOCAL-ROOTS-MISSING` and
> one `CORPUS-ROOT-MISSING` per corpus.

**Evidence executed on 2026-07-28** for `C2`, and run again on 2026-11-17 with the same result:

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
  produce identical bytes, without timestamps or absolute paths.
- **Fail-closed** — the six negative scenarios return exit `1` and their exact
  code, one per fixture: `SCENARIO-SCHEMA-INVALID`, `SCENARIO-CYCLE`,
  `SCENARIO-LAYOUT-MISSING`, `SCENARIO-STATE-MISSING`,
  `SCENARIO-BINDING-MISSING`, and `SCENARIO-MOUNT-MISSING`. The seventh,
  `SCENARIO-DUPLICATE-WIDGET-ID`, is a defensive guard: with well-formed
  ancestry and contiguous sibling indices it cannot trigger from a JSON, so
  it is tested by injecting the collision, not weakening the algorithm.
- **C5 boundary intact** — the scenario fixtures live in a second allowed
  folder, and the C5 guarantee is upheld by the **content audit**, which has a
  test demonstrating that it catches a corpus layout replanted inside an allowed
  folder. A `.layout` in any other location gives
  `CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY`, with its own test.

**Evidence executed on 2026-07-29** for `C4`, and run again on 2026-11-17 with the same result:

```
python scripts/tools/dayz-ui-lab/dayz_ui_lab/diff.py \
    --observed  scripts/tools/dayz-ui-lab/fixtures/scenarios/defect-overlays/observed.json \
    --scenario  scripts/tools/dayz-ui-lab/fixtures/scenarios/defect-overlays/scenario.json \
    --report    <diff.json>
  → verdict=FAIL, exit 1, findings=4
    DIFF-REFERENCE-MISSING · DIFF-CLIPPING · DIFF-OVERLAP · DIFF-STATE-MISSING
positive control three-cards → verdict=PASS, exit 0, findings=0
```

- **Exactly four, with equality and not with "at least"** — the test asserts
  `len(findings) == 4` and the exact set of codes.
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
- **Known residual, out of scope for `C4`**: the
  diff validates that `scenario_id` matches but **not viewports**, so an
  observed captured at another resolution produces geometry findings without warning
  of the mismatch. It matters once engine captures (C6) are compared on this side.

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

**Evidence executed on 2026-07-28** (each `✓` with the test that closes it, measured,
not inferred). The tests are in `skills/dayz-persistence/tests/`.

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
  `rigorous-data-audit` **without blocking findings**: 1 P2 and 2 P3, all three fixed.
  **Declared scope of that audit:** it ran **single-agent**. It completed the full Step 1
  —mechanical checks, which is where the skill itself states that reasoning
  fails— and 1-to-1 verification of each finding against the file. Step 2 did **not** run
  (eight angles in parallel) nor Step 4 (implementer-grade with fresh context).

## E — Skills and domain knowledge

> **Intent:** cover the areas that currently force the assistant to improvise,
> keeping modules small and research vanilla-first.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| E1 | A multiplayer sync skill covers RPC, reliability, ownership, prediction, and desync diagnosis | client/server fixtures, fail-closed auth, and two local clients | ❓ |
| E2 | A sound and particles skill covers `.ptc`, soundsets, Effect systems, and occlusion | pinned examples + build/smoke per subsystem | ❓ |
| E3 | A terrain skill covers basic map, roadgraph, and CE | minimal reproducible project and roadgraph/CE checks | ❓ |
| E4 | A Workshop release skill covers mod.cpp, dependencies, signing/bisign, images, changelog, preflight, invalidatable cache, and transactional publication | dry-run requires new PBO, header/prefix/entries, signature when applicable, and fatal-free log; input/toolchain changes invalidate cache and a failure preserves previous bytes/manifest | ❓ |
| E5 | The knowledge packs incorporate an RPT decision tree, mod architectures, and a measured performance guide | deduplicated branches with evidence; budgets declare build/hardware/corpus | ❓ |
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
| F4 | Read-only ODOL reader exists for anatomy/parity, with declared coverage and limitations, without adding ODOL writer | v53/v54/v55 fixtures, self-diff, and fail-closed boundary/oob failures | ✓ |
| F5 | py3d keeps its entire suite green and a single canonical distribution | `scripts/tools/py3d/tests` does not regress; the wheel hash is pinned in `scripts/tools/py3d/rollout/wheel-manifest.json` | ✓ |

## G — In-game test automation

> **Intent:** make test methodology reproducible even without DayZ-MCP
> and expand capabilities without weakening lifecycle/ownership.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| G1 | Bridge protocol documents commands, schemas, errors, version, and extension | request/response examples validated against schema and current bridge | ❓ |
| G2 | Lite mode works with DayZDiag + filePatching + ingame scripts, without DayZ-MCP | minimal reproducible spawn→action→RPT/verdict ladder | ❓ |
| G3 | An orchestrator integrates test-ingame + MCP and incremental watch mode | fixture change triggers exact rebuild/retest; lease and run_id remain fail-closed | ❓ |
| G4 | Sequences, crash/RPT detection, screenshot diff, telemetry, and two clients have separate gates | each capability has fixture and verdict; screenshot adapter imports `engine-capture-v1`, selects a single client by `run_id`, and preserves lossless PNG or fails closed; no performance numbers without measurement | ❓ |
| G5 | VPP/init.c alternatives and companions are documented with limits; dayz-labs remains pinned, optional, and without lifecycle authority, and Cheat Engine is not a recommended dependency | capability/reliability/risk/version matrix verified; gates exclude installer and `start/stop/restart`; WPF does not count as `.layout` evidence | ❓ |

## H — Ecosystem, contribution, and polish

> **Intent:** that the material is maintainable, teachable, and expandable without duplication
> or dependency on one machine.

| # | Criterion | How it is verified | Status |
|---|---|---|---|
| H1 | Workbench, PBO extraction tools and viewers integration documented with versions | commands smoked or marked as unverified companion | ❓ |
| H2 | Clean reproducible server environment uses VM or viable alternative, chosen after spike | second machine/VM executes smoke without private junctions | ❓ |
| H3 | Contribution guide defines evidence, tests, promotion to installed skills, and release | fixture contribution goes through end-to-end validation and promotion | ❓ |
| H4 | Duplicate notes are consolidated without losing claims/evidence | old→canonical map; link audit and semantic diff reviewed | ❓ |
| H5 | Minimal diagrams cover skeleton, proxy frame, and Construction quartet lifecycle | the repo's own assets, valid links, and human review | ❓ |
| H6 | Risk register/known engine bugs lives versioned and distinguishes crash/exception/corruption/degradation/cosmetic | each entry has concrete evidence, build, and severity | ❓ |

## Out of scope

- Copying unverified snippets into a skill.
- Bundling vanilla DayZ data, third-party mods, or code and assets that may not be redistributed.
- Giving a companion tool lifecycle authority (start, stop, restart) in parallel to DayZ-MCP.
- Running Enforce in the browser or promising engine-faithful 3D previews.
- Writing ODOL.
- Setting CPU/network/widgets budgets without reproducible benchmark.
- Publishing a repo, a release, or a Workshop item during a planning phase.
- Treating installed skills as a parallel release source;
  promotion occurs from the repository after the gates.

## Pinned references

- Agent Skills reference validator: **`skills-ref==0.1.1`** from PyPI, whose
  console script is **`agentskills`**. A PyPI version is an immutable release
  artifact, so the pin is stable.
  Reproducible installation: `python -m venv <root> && <root>/Scripts/pip install`
  `skills-ref==0.1.1`, and `PACK_SKILLS_REF_ROOT=<root>`.
- DayZ compatibility: first verified on `1.29.0.163451`, 2026-07-24. The stable
  branch moved to `1.29.0.163709` on 2026-08-15; **nothing has been re-verified
  against that build** and the matrix states so row by row. Since 2026-10-15 the
  stable branch is DayZ 1.30 (`1.30.164289` since 2026-11-04): the vanilla line
  numbers in the skills are that build's unless a citation names another, the
  matrix levels are still the 1.29 ones, and `docs/compatibility-matrix.md` §DayZ 1.30
  says what was checked on 1.30.
- UI: VPP, Expansion and TraderPlus pinned by commit; TraderX by Workshop manifest
  `3069958660046119589` and PBO hashes; the `lfpowergrid` set as negative. All in
  `scripts/tools/dayz-ui-lab/corpora/manifest.json`.
- py3d: distribution `py3d-dayz` (the importable module remains `py3d`; `py3d`
  on PyPI is another library), version `1.10.1`. Reproducible wheel
  `py3d_dayz-1.10.1-py3-none-any.whl`, SHA-256
  `c9f000a51e6aca83104a8f021ef5e3eefe8d7f0a5b053623544b49dbdd5d1785`.
  Reproducibility is **toolchain-bound**: valid for
  `setuptools==83.0.0` and Python `3.14.3`, both declared in
  `scripts/tools/py3d/rollout/wheel-manifest.json`.
- **A version name identifies one content.** py3d `1.4.0` came
  to designate three different contents, and the only thing separating them was the manifest
  seal. When the bytes of a release change, bump the version; do not reseal
  the old name. `1.4.0` remains retired as ambiguous.

## Vanilla evidence

- `P:\scripts\3_game\entities\entityai.c:2910` (`OnStoreSave`) and `:2978`
  (`OnStoreLoad`) — the persistence stream contract.
- `P:\scripts\3_game\tools\jsonfileloader.c:7` (`LoadFile`) and `:105`
  (`JsonLoadFile`, marked DEPRECATED at `:99`).
- `P:\scripts\3_game\gameplay.c:117` — signature of `ScriptRPC.Send`.
- Community Framework `Entities/ItemBase.c:22-84` and
  `ModStorage/CF_ModStorageObject.c:25-76,80-156` — integration and
  framing of CF ModStorage. These are in the Community Framework source, not on
  `P:\`, and were not re-opened for this page.
