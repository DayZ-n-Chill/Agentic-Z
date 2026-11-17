# Working method and gate calibration

Process rules that cost more iterations than any config fact: the iteration budget, calibrating a gate before trusting it, what a PASS covers, and the habits that stop re-deriving known causes.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The crew probe of the method below dumps `CrewPositionIndex` for each component index (`P:\scripts\3_game\vehicles\transport.c:179`).

## Iteration budget: check this before opening a front (added 2026-07-27)

Measured over one month of vehicle work (125 session handoffs: MercedesAMGLF 46, SUB_BRZ 38,
LFHeli 37): **26 sessions ended in STOP/BLOCKED/FALSIFIED against 24 green**. The three failure
modes below are process gates, not config facts — and each burned dozens of sessions on a
different project before being named. They cost more iterations than any invariant below.

1. **Count the cycles spent on one objective, and make the count block.** `DZ-R5` already says
   "after 2 rebuilds without progress, STOP and change strategy"; it does not bite because nobody
   tracks N. Carry `cycles_on_this_objective: N` in the HANDOFF `LIVE-STATE`, and at N>=3 the
   re-entry gate must pick one of three exits before touching code: change strategy, escalate to a
   human, or drop the objective. Evidence: MercedesAMGLF Task 9 reached **v64 across 29 sessions**,
   and what finally closed it was shifting 28 proxy triangles by -0.240 m in X.

2. **Keep the test harness OUT of the product task.** Task 9 mixed "align the Mercedes proxies"
   (product) with "build an automated live verifier" (daemon, broker, lease, preflight, camera
   contract, JPEG SHA) — the harness silently took the bulk of the time and became the project.
   If a product task is blocked TWICE by the harness, stop the product and decide explicitly: scope
   the harness as its own project, or run that one test by hand and move on.

3. **When the judge is the eye, offline analysis gets ONE round.** Green offline gates do not
   predict the live result. A Task 9 build reported `263/263 global + verifier 35/35 hard PASS` plus
   every SHA, and then: `Visual: FAIL of evidence, client hung`. The LFHeli "six fronts" night
   spent ~25 Codex sessions to produce refutations only (binding intact, re-bake refuted, clock and
   interpolation refuted) and concluded the discriminator was the user's own screenshot. If the
   discriminator is visual or feel, spend one offline round ruling out cheap causes, then go to the
   game — extra offline rounds postpone the verdict, they do not replace it.

Corollary already paid twice: SUB_BRZ needed 30+ sessions to conclude that a decimated rip mesh
cannot reach game-ready quality (pivot to a human artist), and the LFHeli HH-60G reached the same
verdict independently weeks later. A visual red that survives N rounds is a signal to escalate to a
human, not to run round N+1.

For family B (a new car ripped from a source game and split into proxies), the absent door radial is covered by the family B cookbook `cookbook-door-radial-missing.md` of the rip-vehicle-import skill.

## Before any numbered invariant: calibrate the gate itself (SP-132, added 2026-07-29; LFHeli HH-60G and OH-1)

**BEFORE any numbered gate below — calibrate the gate itself (SP-132, added 2026-07-29; LFHeli HH-60G + OH-1).**
Two rules in this file already cover this — the "Calibration and scope" section
below and habit 2 of the "Method" section ("never close a phase on a tautological gate"). Both were live and **neither
fired across four gates in one week**, because both read as being about *car render/winding* gates. They
are not: they govern every item below, and capacity, parity, telemetry and policy gates alike. The four
shapes, so they are recognizable on sight:
- **A threshold copied instead of measured.** `hh60g_assemble.py:29` carried `RESOLVED_LIMIT = 65535`;
  the engine's real resolved-vertex ceiling on that model is **46.133** (42% lower), so the gate passed
  models `binarize` rejects with `Too many vertices`. The cap is model-dependent (×1.4205 on HH-60G,
  ×1.46 on OH-1) — never copy it between models, re-measure with binarize.
- **A policy that is a mathematical no-op.** `uniform` and `keepdot` were geometrically inert
  (`dot(-cross,-n) == dot(cross,n)`); four variants were built on them before the identity was checked.
- **A gate that shares the producer's frame.** OH-1 seat parity compared under pure translation — the
  same assumption the sub-model was generated with. `delta 0.000` proved producer and gate agreed, not
  that either was right.
- **A field read selectively.** `attachment_count=2` was signed PASS because that one field matched
  expectation; the regression sat in the same output 20 min before the user hit it in-game.

**A fifth shape, and it fakes an ABSENCE rather than a green (added 2026-08-19, SUB_WRXSTI): matching
a LOD by its nominal resolution.** LOD resolutions on disk are not the round numbers the docs use —
FireGeometry reads `6999999976046592`, not `7e15`. A bucket keyed on `round(7e15)`, or any `==`
against the nominal, comes back EMPTY, and a gate built on it reports "the selection is absent" about
something that is present. Measured cost: a cross-check of the config's `componentNames[]` against the
`.p3d` reported all six damage zones missing, and they were all there in FireGeo — the report reached
the user as a red before the control against vanilla caught it. Always match with a RELATIVE tolerance
(`abs(res - nominal) <= nominal * 1e-3`), and note the direction of the failure: this one does not
show up as a suspicious green you might question, but as a confident red about missing data, which is
the shape people act on fastest.

**One minute, before trusting any gate:** (a) run it against a KNOWN-BAD case — green on a known-bad
means the bug is the gate, not the artifact; (b) name in one line the assumption the artifact was BUILT
with, and confirm the gate does not reuse it. A gate that has only ever been seen green is unmeasured,
not verified.

- **Gates that stay red stop being sensors (LL-244).** If a known failure is deliberately accepted, pin its exact signature — entities and measurements — and report `KNOWN_RED` separately from `NEW_RED`. Any drift, including an improvement, is new evidence because the pin describes a state, not a ceiling. A gate that returns the same verdict for N runs without making a new red distinguishable has become a constant.

## Calibration and scope, so a gate is trustworthy and not a false green

- **Draw the window from the defect, not the fix (LL-271).** Derive the measurement window from where the defect is visible, the viewing angles and the user's referent, never from the area the repair touched. A red dismissed as a window artifact needs an independent control proving the instrument lies.
- **Classify new faces before choosing a comparator (LL-272).** Invented points/UVs -> independent calibrated reference (material median); geometry derived from one face (twin, displaced panel) -> that exact source face — stricter, here `0 of 7,205 deviate >5%`; exact twin -> exact equality only. A failure inherited unchanged from the source does not prove the edit introduced it. A twin cannot fail a UV gate — it inherits UVs literally.
- **Half the model failing is structure, not defect (LL-276).** If a detector rejects ~50% of entities, presume a structural property such as double-sided construction until refuted. Here `13,260` vertices in `brz_black` / `12,986` in `brz_paint` flagged as "normal opposite face" = the design. Prefer invariants internal to one entity — e.g. the three normals of the same triangle >90° apart (112 of 618 glass faces) — then remeasure the whole residual after the repair: negating opposite normals fixed ~59%, the remaining ~41% needed flattening against the face normal.

- **Every rung must catch at least one KNOWN in-game bug, not just a synthetic self-test.** The
  self-test proves the MECHANICS; a real known-bad case proves COVERAGE. Keep a short per-car list of
  known in-game defects and confirm the ladder catches each: BRZ backlight mixed-winding -> caught by
  rung 2 (`winding_consistency`: glass 18.2% of area); MercedesAMGLF left tail-lamp inverted -> caught
  by rung 4 (`gate_car` see-through, L-vs-R 310/0). (both 2026-07-01)
- **A PASS states its SCOPE — never a bare "clean".** "clean of see-through in `color`/`glass`" is NOT
  "clean of winding". `gate_car` reporting "BRZ clean" while rung 2 (per-piece uniformity) was
  unchecked was a FALSE GREEN the user caught in-game (2026-07-01). Name what each gate covered and did not.
- **Freshness:** the analysis prints model SHA+mtime and flags changes vs the last run
  (`model_freshness.stamp`) — the deployed `.p3d` can change under you between sessions (SUB_BRZ s16
  de-dup removed 20320 faces mid-analysis; a stale golden then misleads). Owner of a shared artifact
  (a car's `.p3d`, or THIS skill) = the session working it; edit append-only + verify (this skill was
  being edited by two sessions at once, 2026-07-01).

## Method: habits that stop the re-derivation (apply before the per-invariant fixes)

Not invariants but the working method that would have saved most of the LFQuad→SUB_BRZ→MercedesAMGLF
iterations. They are otherwise diffuse across the references; they live here at the front on purpose:

1. **Parity-first.** Debinarize a known-good vanilla vehicle (`civiliansedan`, ODOL v54) ONCE and diff your
   model against it — LODs, named selections, crew proxies, wheel hubs, componentNN, memory points — into a
   single master gap checklist. Fix every gap in one pass instead of discovering them error-by-error in-game.
   → `vehicle-structural-parity.md` "Parity-first method".
2. **In-game is the ONLY gate; offline is a hint.** Offline parity / frame / winding / render checks repeatedly
   passed GREEN while the car still failed in-game (proxy frame, body winding, seat collidability). A metric that
   is `0.000`/`100%` *by construction* (winding-vs-its-own-normals, frame=py3d-identity) proves internal
   consistency, NOT that DayZ renders / spawns / seats correctly. Never close a phase on a tautological gate.
3. **Crew-probe headless FIRST** when a get-in / radial action will not appear for a seat. BEFORE any rebuild
   cycle: spawn the car + a known-good control (LFQuad/Croco) headless, dump `CrewPositionIndex(0..79)`, and run
   `RaycastRV(ObjIntersectView)` per seat anchored at `pos_driver`/`pos_codriver`. This is what caught the
   inward-winding blocker (#4) without eyeballing and broke the blind-rebuild loop. → `vehicle-structural-parity.md` crew-probe.
   - **(added 2026-07-28, LL-219) A probe you INHERIT carries the coordinates of the artifact of THEN —
     re-derive its targets from source before believing a negative.** The probe is not the thing that
     rots; a hardcoded seat centre is. Re-running it verbatim yields a `hit=0` that is **aim, not
     mechanism**, and it is indistinguishable from the real verdict — while being exactly the
     "interesting" answer nobody re-questions. Measured on SUB_BRZ: the s9 mission
     (`brz_crew_probe_init.c:122-123`) aims at engine `(-0.40, 0.72, -0.12)` / `(0.54, 0.72, -0.12)`,
     while today's boxes come from `profiles\<car>.json` → `rip_p3_structural.py` seat params at
     py3d `(±0.357, 0.55, 0.12)` with half-extents `(0.22, 0.25, 0.25)` — the codriver ray passes
     **3.7 cm** from the box face in X. Still inside, zero margin. Procedure: (a) re-derive the aim
     point from the profile + generator that produced TODAY's artifact, never from the handoff that
     described it; (b) compute the ray's margin against the target box — margin below ~one half-extent
     means the negative is not evidence, fix the literal first; (c) log the aim point used next to the
     verdict, so a later reader can tell a real `hit=0` from a miss. Same family as METHOD #2
     (measure, never assume) applied to the instrument instead of the artifact.
4. **Two failed rebuilds on ONE symptom = HARD STOP — build the probe, do not fire cycle #3.** The rule
   predated the failures and still got skipped (retro 2026-07-03: copilot get-in ~7 days of serial wrong
   hypotheses; handlebar ~2 sessions of parameter sweeps settled by ONE GetSteering log; BRZ get-in 3
   bottom-up sessions when the gate was one script override) — while EVERY time the discipline ran
   (both-sides log line, crew-probe, headless harness, LL-100 field-diff vs a working referent) the issue
   closed in a single pass. Before the 3rd in-game cycle on the same symptom: enumerate candidate causes,
   read the actual mechanism (engine source / wiki, not intuition), instrument BOTH client and server
   (verify the hook actually fires — a silent log IS a signal, `OnUpdate` is not an engine callback), then
   ONE directed fix. If two probes also fail, escalate to a multi-agent audit over the REAL files — that
   escalation resolved the LFQuad wheelsim stall (4 sessions serial) in one session.

## Cite, then verify

Vehicle config and model values are easy to half-remember. Before writing a class name, property, or
named selection, grep it in vanilla (`P:\dz\vehicles\`) or in the references' cited sources, and keep
the provenance labels the references already use (`[Landrover ✓]`, `[QuadBike]`, `[LFQuad ✓]`,
`[TBD-verify]`). Anchor any new vehicle lesson to a real mod with `path:line`, never to memory.
