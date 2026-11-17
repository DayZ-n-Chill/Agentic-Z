# `binarize` as the load oracle: vertex budget, measured

The three verdicts of `binarize.exe` on a model, the real vertex ceiling in resolved triples, how thin the headroom of a deployed model can be, and which log lines do not discriminate.

> Status: field notes measured on third-party mods: the HH-60G of LFHeli (cross-checked against 25 in-game verdicts), the OH-1, the H2R import and two building cases. Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Tags such as SP-205 or LL-464 are the notes' own lesson numbers, and `[EXACT]`, `[DESIGN]` and `[CLAIM-...]` are the notes' own evidence labels. Paths such as `<vehicle-import>\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. The short rule this file develops is invariant 24 in `invariants-lods-and-vertex-budget.md`.

## Vanilla anchors checked on `P:\`

- `binarize.exe` ships with DayZ Tools and reads its source from the work drive; `/dayz-preflight` checks that DayZ Tools is installed and `P:\` is mounted before any step here that runs it.
- Vanilla models are that tool's output: `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` opens with the `ODOL` signature, version 56 (header read 2026-11-17). A verdict in this file can therefore only be reproduced on a mod's own MLOD source, not on a vanilla model.

## The evidence behind invariant 24

Development of **invariant 24** in `invariants-lods-and-vertex-budget.md` (`binarize` is the three-state offline load
oracle; `RESOLVED_LIMIT = 65535` is a false friend). The invariant is stated there; this is
the evidence behind it. Read it when a model passes every offline gate and still refuses to
spawn, or when you need to know your headroom before adding geometry.

Everything below is measured on the HH-60G, cross-checked against 25 in-game verdicts, except the
two building cases under item 3, which are binarize runs with no in-game verdict, and the H2R
import's runs under item 2, another vehicle with `PASS` verdicts only.

**1. `Too many vertices` and `Won't simulate, it has no geometry` are the SAME defect.**
The rejection happens while **loading the MLOD**, before conversion, so the engine aborts the
whole model and emits the generic physics message even though the Geometry LOD is perfect.
Chasing it as a collision problem costs days. If a model that passes every offline gate does
not spawn, run binarize on it **before** touching the Geometry LOD.

**2. binarize adjudicates N models per pass, offline, in ~90 s.**
`binarize.exe -always <src under P:\> <out>`, with a `model.cfg` that declares **every**
basename in the source dir (undeclared basenames fall back to Default and change the code
path). Validated on 28 variants against the in-game verdicts of the previous cycle:
**13 PASS/PASS, 12 FAIL/FAIL, zero false greens, zero false reds.** This turns a model
bisection from ~6 min per variant into ~90 s per batch.
[DESIGN] Give the call `-addon=<bench>` as well, `<bench>` being a dedicated folder that holds the
source dir (binarize parses every `config.cpp` under `-addon`: SP-155 rule 1 of the `/dayz-build-pbo` references).
The validation above ran without it, and so does the HH-60G project's copy of the bench named
under Tool (read 2026-10-24), which also stops on a source outside `P:\`. In the H2R import
(2026-10), a call of that form with its source outside `P:\` and no `-addon` waited about 5 min
before loading its first model, and three days later, other processes busy, gave no ODOL in
30 min; with `-addon` the first model loaded within a second, all 8 read `PASS` as they had
without it, and the kits built from them spawned in game. No `CAPACITY_FAIL` has been run with
`-addon`, and the stall was seen only with the source outside `P:\` (a source under `P:\` was not
timed). The `Material not loaded` lines listed under "Noise that does NOT discriminate" are
noise for the verdict, not for the ODOL: every material entry of the H2R bench's 8 ODOLs came
out empty, with `-addon` and without (SP-155 rule 5 of the `/dayz-build-pbo` references), so run rule 5's control
before shipping a bench ODOL (claim: CLAIM-BINARIZE-DIRECT-ADDON-STALL-REF).

**3. The verdict has THREE states. Using two is a bug in your bench.**
- `PASS` - a **new**, non-empty ODOL for the basename under test, in an output dir that did
  not already contain it. Skip the "new" requirement and a residual ODOL gives you a false green.
- `CAPACITY_FAIL` - no new ODOL **and** a `Too many vertices` line attributed to that MLOD.
  The line names the MLOD, not the LOD: on a building it came from collision LODs that had grown,
  with the visual LOD as it passed (dayz-model-pipeline skill, `references/lods-and-geometry.md`,
  "Binarize: `Too many vertices` from the collision LODs"). Before blaming the change just made,
  compare every LOD with the last build that passed.
- `OTHER_FAIL` - any other absence: bad `model.cfg`, undeclared basename, malformed MLOD, I/O,
  aborted tool. **It blocks and does NOT authorize touching geometry.** Without this state you
  decimate a mesh because your bench was misconfigured.
  One cause measured since prints nothing of its own (SP-458, 2026-10-03, on a building, not a
  vehicle): with too many pieces in its collision LODs, `binarize.exe` wrote no ODOL and no
  capacity line, and the bench read `OTHER_FAIL` while the bench was fine. Rule it in only once
  the MLOD walks to `#EndOfFile#` in every LOD (a truncated MLOD gave the same verdict) and the
  same model passes without its collision LODs: those two checks place the failure in the
  collision LODs, they do not measure the limit. The fix then moves pieces to another model with
  the same transform and leaves every piece as it is (none is merged or decimated), and each
  resulting model still has to PASS. Boundary and figures: dayz-model-pipeline skill,
  `references/lods-and-geometry.md`, "Collision of a large building with an interior".

**The verdict is reproducible; the ODOL bytes are NOT.** The same `.p3d` produced 1,725,025 and
1,726,689 bytes with different hashes in two clean consecutive runs. Never gate on the ODOL SHA.

**Noise that does NOT discriminate** (it appears for the known-good control too):
`Material not loaded`, `No entry '.CfgVehicles'`, `Trying to access error value`,
`Error occured: Loading LODShape`, `UV mapping too varied`, `vertices of bone X are shared with
bone Y`, `Too detailed shadow lod`. The word `Error` in the log classifies nothing - attribute
the outcome to a model and a cause, or record `OTHER_FAIL`.

**4. The ceiling in triple units is not 65535, and it is not portable.**
Measured by walking four structurally different bases of the same asset to the cliff:
**46,133 loads, 46,134 does not** - the same integer for all four. The engine's hard cap does
appear to be 65,535 but on **post-split** vertices, and a `(point, normal, uv)` counter
under-counts those by a model-dependent factor: **1.4205** here, **1.46** on the OH-1 (see #24).
An assembler with `RESOLVED_LIMIT = 65535` hardcoded closed its own gate in green, for weeks, on
a model the engine refuses. **Re-measure per model; the hard gate is binarize's verdict.**

**5. Know your headroom, because it can be one edit wide.**
The deployed HH-60G sat at 46,019 of 46,133 - **114 triples of margin**, 99.8 %. Any change that
adds more than 114 resolved vertices kills it: a normal tweak, a UV seam, a texture that forces
another split. Measure resolved before and after **every** visual edit.

**6. When you mint a normal, you are spending budget; when you reverse a corner order, you are not.**
The defect that cost this project a week: a winding-flip block negated the stored normal **per
corner** for the 151 faces (0.43 %) whose source normal disagreed with the source winding. Those
453 corners minted 630 pool entries and +886 resolved. Re-reversing the corner order of those
151 faces reaches **identical** coherence at zero cost. A face's corner order is free; a new
normal is not.

And the identity to have in your head before "fixing" a winding by inverting things:
`dot(-cross, -n) == dot(cross, n)`. Reversing the corners **and** negating the normal is a
no-op for their relationship - it re-parametrizes, it does not flip. A policy that does both
changes nothing.

**7. A perturbation below the consumer's quantum is a null mutation.**
When walking a limit to find where it breaks, the step must survive the consumer's quantization.
Nudging a normal by 1e-4 on one component (~0.006 deg) does not survive DayZ's normal
compression: the estimator counted +120 new triples, the engine saw none, 42 samples "passed",
and the ceiling would have been reported 7 units too high. Use a step that is unambiguously
above the quantum (>= 3 deg for normals) and include a sample past the known-failing value as
a self-check.

Tool: `<vehicle-import>\scripts\p3d_vertex_gate.py` - `count` reports resolved per LOD
as `INFORMATIVE_ONLY`; only `binarize` runs the authoritative three-state adjudication.

## Qualify a capacity warning on the deployed artifact first (SP-182, added 2026-08-31)

Before changing geometry for a numerical warning, run the same counter on the
known-good model extracted from the deployed PBO. If that artifact already exceeds
the proposed threshold, the threshold does not govern that load route. Confirm the
blob rather than the editable tree, and read its magic: `MLOD` proves the engine's
packonly route, while `ODOL` proves a binarized route. Neither result automatically
proves the other.

A discrete tolerance sweep proves only the sampled grid. Powers-of-ten can jump over
the usable interval; refine around the transition and, for unit normals, test an
angular merge rather than only component-wise rounding. The refined instrument must
first reproduce every previously published sample before any new intermediate point
is accepted.

## Read the verdict artifact, not the wrapper exit code (SP-220, added 2026-08-31)

`p3d_vertex_gate.py binarize` and a Python import failure can both exit `1`. Read the
per-model state from a newly written `_verdicts.json`; a missing report or missing
row is `OTHER_FAIL`, never PASS or `CAPACITY_FAIL`. The child process needs the
required module on `PYTHONPATH`, because an in-process `sys.path` edit is not
inherited. Allow for the measured startup cost (about 68 s even for a four-point
control); for a batch, set an explicit larger timeout and include a tiny known-good
model in that same invocation. If the control does not PASS, no product red is
attributable to capacity.

Keep three units separate: a DCC estimator may split one source point by rounded
corner normal/UV; py3d `resolved` counts `(point_index, normal value, uv)` on the
assembled MLOD; the engine enforces post-split vertices. Budget in assembled py3d
units and adjudicate with the three-state binarize result. Count after host proxies
are present; each proxy contributes three points, one face normal, one face and
three resolved entries.

## Source geometry census is a planning bound, not engine authorization (SP-157, added 2026-08-31)

Before sacrificing artist normals, decimating, or repartitioning, compose the source
node world transforms and count `POSITION` accessor vertices per final frozen owner
container. Count every emitted instance; a mesh definition referenced by three nodes
has three costs after emission. The glTF accessor sum is a conservative planning bound
for that routing and is useful before the MLOD exists.

The count chooses where to measure next; it does not authorize a build. Do not compare
it with a fixed 60,000, 65,535, or approximate 32,768 ceiling. Those literals mix
source accessor vertices, assembled resolved triples and engine post-split vertices.
The assembled py3d count remains informative and the three-state `binarize` verdict
remains authoritative. This rule supersedes approximate fixed-ceiling planning advice
elsewhere in this pack (for example the fixed targets in `decimation-libraries.md` and
`external-obj-import.md`) without weakening any measured product gate.
