# 3D generation harness

How to run a 3D model build as a gated pipeline: intake, research dossier, plan with tests, per-component build, adversarial roast, fix loop and ship gate, each with written evidence. Use it for a production model or a vanilla-parity rebuild, not for a single mesh or a static visual check (those are `blender-assembly.md` and `blender-visual-review.md`).

The default failure of 3D generation driven by a language model is confident garbage: a model built from memory of what the item probably looks like, reviewed by the same process that built it, and declared done because nothing crashed. This harness turns each of those defaults around:

- Nothing is modeled from memory. A research dossier with references from several viewpoints comes first.
- Nothing is declared correct without a number or a render behind the claim.
- The review phase is adversarial by design. Its output is a defect list, not a verdict.
- Every phase ends in a gate. A gate that does not pass stops the pipeline; it is never noted and continued past.

The harness owns the order of work and the gates. The techniques live in the files below; read each one at the phase that needs it.

## What to read

| Question | Read |
|---|---|
| What goes in the Phase 1 research dossier, and its Gate R checklist | `generation-dossier-template.md` |
| How the Phase 4 roast is scored, the defect list format and the re-roast scope | `generation-roast-rubric.md` |

## Where the techniques live

| Work | Read or run |
|---|---|
| Building geometry in Blender, the helper library and the numeric gates (`verify_bounds`, `verify_overlap`, `verify_mesh_integrity`, `audit_all`) | `blender-assembly.md` |
| Capturing renders (`vr_capture`), the defect checklist and the bounded fix loop | `blender-visual-review.md` |
| DayZ pitfalls of an AI-generated mesh: retopology, the `_nohq` bake, the handoff | `ai-generation.md` |
| LODs, vertex budgets, export to `.p3d` | `lods.md`, `axes-and-winding.md` |
| Auditing the exported `.p3d`, face winding included | `/dayz-p3d-audit` |
| Packing the mod | `/dayz-build-pbo` |

AI mesh generation itself (image or text to 3D) is not shipped in this repo. Without a generator at hand, skip the AI route and stay on the parametric `blender-assembly.md` path. Do not invent a generator or its API.

## Pipeline

```
Phase 0  INTAKE      what / for what / route          -> Gate I
Phase 1  RESEARCH    dossier: views, dims, parts      -> Gate R
Phase 2  PLAN        breakdown + viability tests      -> Gate P
Phase 3  BUILD       per component, checkpointed      -> (component gates)
Phase 4  ROAST       adversarial review, rubric       -> Gate V
Phase 5  FIX LOOP    one diagnosis at a time          -> re-roast
Phase 6  SHIP        full-evidence final gate         -> Gate S
```

Every gate produces a written PASS or FAIL with the evidence that justifies it, appended to the evidence ledger (see "Evidence"). FAIL means fix, or return to the previous phase. Never proceed past a failed gate.

## Phase 0: intake and routing (Gate I)

Answer these before anything else. Ask the user only for what cannot be inferred.

1. **What item, exactly?** "A rifle" is not an answer. "An AKM-pattern rifle, wooden furniture, DayZ-era condition" is.
2. **Target use.** DayZ mod (which slot and behavior), generic game asset, or render only? This sets the poly budget, the LOD plan and which export and audit skills apply.
3. **Route.** Parametric hard surface goes through this harness with `blender-assembly.md`. Organic or sculpted shapes go to AI generation for the base mesh, when a generator is at hand. On that route Phases 1 and 2 still run in full, because the roast is scored against the dossier and the detail list; only the Phase 3 build is replaced by AI generation, and the mesh then goes to the Phase 4 roast. The roast and ship gates apply to AI-generated meshes too, and to them most of all. For a DayZ-bound AI mesh, the DayZ pitfalls (retopology of a non-manifold mesh, the `_nohq` bake, the handoff) are in `ai-generation.md`; this harness owns the generic gates and discipline.
4. **Budget.** The LOD0 triangle range. For DayZ, anchor it to the triangle counts of the vanilla equivalent, not to taste.

Gate I passes when all four have explicit answers written down. An unanswered item is a question for the user, not an assumption.

## Phase 1: research dossier (Gate R)

Never model from memory. What a language model recalls of an object's shape is a hypothesis, not a reference. Build the dossier from `generation-dossier-template.md`:

1. **References from several viewpoints.** Search for images of the item until you hold at least 4 distinct viewpoints (front, side, top and a three-quarter view), plus close-ups of every detail zone (grip, latches, fasteners, seams). For a DayZ item, also bring the vanilla equivalent's model into the scene as a 1:1 reference. Vanilla models on `P:\` are binarized, so Blender can open one only after an external ODOL to MLOD converter, which Agentic-Z does not ship.
2. **Dimension table.** Overall length, width and height from two independent sources, plus at least 5 landmark measurements (barrel length, grip height, wheel diameter and so on). Where no source exists, write `ESTIMATE ±X%`. An unlabeled estimate is an invention.
3. **Part inventory.** Every visually distinct component, named. This becomes the build breakdown.
4. **Unknowns list.** Everything you could not verify, stated as unknown, with the decision: resolve, accept with a tolerance, or ask the user. This list is what stops assumptions. An empty unknowns list on a non-trivial item is itself a red flag.

Gate R passes when at least 4 viewpoints are on file, the dimension table is sourced or explicitly estimated, the part inventory is complete and the unknowns are explicit. The dossier is saved with the evidence ledger. The roast in Phase 4 is scored against it, so a thin dossier makes the roast blind.

## Phase 2: plan with viability tests (Gate P)

Using the dossier, write the plan and its tests before any code. A plan without verifiable criteria gets returned, not improvised around.

1. **Build breakdown.** An ordered part list, each part mapped to the `blender-assembly.md` rule that builds it.
2. **Connection map and detail list.** As in `blender-assembly.md` Phases 1 and 1.5: every joint, and every detail feature with its size.
3. **Viability tests (the contract).** A `TESTS` block stating, per part: expected dimensions within ±5% of the dossier table, expected joint overlaps, and the expected `verify_mesh_integrity` result (closed or open, ngon tolerance). For the whole model: the total triangle range, the named landmarks the final render must match, and which later audits apply (for DayZ, the winding and structure checks of `/dayz-p3d-audit`).

Gate P passes when every part in the breakdown has at least one numeric or visual pass/fail criterion. A part with no criterion cannot fail, which means it cannot be verified either.

## Phase 3: build (component gates)

Execute the plan under `blender-assembly.md` discipline (load its helper library first). Per component:

1. Build it, then run `verify_bounds` and `verify_overlap` against the connection map.
2. Run `verify_mesh_integrity` after every boolean, modifier or loft.
3. **Component checkpoint.** Take a quick visual capture of each complex part before building on top of it (`blender-visual-review.md`, "Multi-angle capture"). For high-risk parts, build two parameter variants and choose from the renders.
4. Log each component's results in the evidence ledger. A failed component gate stops the build at that component.

Do not improve the plan mid-build. A discovered necessity goes to the ledger as a plan deviation with one line of justification. A discovered nicety is scope creep and gets dropped.

## Phase 4: roast (Gate V)

The roast is a separate pass with the opposite goal: find what is wrong, with evidence. It is not a summary of the build.

1. Take fresh full captures with `vr_capture` (`blender-visual-review.md`, all four angles, scale cube in frame), plus close-ups of every detail zone listed in the dossier.
2. Walk `generation-roast-rubric.md`: 8 categories, each scored 0 to 2, each verdict citing its evidence (a render filename and what it shows, or a measured number against the dossier number). "Looks fine" is not evidence; the banned phrases under "Honesty rules" apply hardest here.
3. **Dimension audit.** A table of measured dimensions (from the numeric output of `vr_capture`) against the dossier dimensions, with the percentage deviation per landmark. A deviation over 5% is a defect unless the plan declared a tolerance.
4. **Detail audit.** Every feature in the detail list, present or missing. A missing planned feature is automatically a defect.
5. Output: a ranked defect list (severity high, medium or low) and the rubric score.

If the first roast returns zero defects, treat that result as suspect, not as success: roast again with new camera angles and tighter close-ups. If the second pass also returns zero, accept it. A first build that survives first contact intact is rare enough that the cheap second look is always worth it.

Gate V passes when no rubric category scores 0, the total is at least 13 of 16, and no high-severity defect remains open. Otherwise go to Phase 5.

## Phase 5: fix loop

Follow `blender-visual-review.md`: fix one diagnosis at a time, re-render the same angles, keep the before and after pair. After the fixes, re-run only the affected rubric categories plus mesh integrity on the touched parts. A full re-roast is needed only when the fixes touched 3 or more components. Loop until Gate V passes. Stop when `correction_loop.py` (in `skills/dayz-model-tools/scripts/`) says so: once the same defect survives 2 consecutive fixes, it stops with `refine-spec`, and you re-plan that component, because the plan was wrong, not the execution.

## Phase 6: ship gate (Gate S)

The final gate checks everything once more, on the final state:

1. All numeric gates green: `audit_all`, `verify_mesh_integrity` on every part, triangle count inside the budget.
2. Gate V passed with the current geometry, not with the renders of an earlier iteration.
3. Target audits. For DayZ, run `/dayz-p3d-audit` after export, and check ride height and scale against the vanilla reference. Absolute face winding is decided by that audit and in game, never from a Blender render (the hard guardrail in `blender-visual-review.md`).
4. Evidence ledger complete: dossier, plan with tests, per-component logs, roast reports with renders, fix before and after pairs, final rubric.

Only after Gate S does the item go to packing (`/dayz-build-pbo`) or delivery.

## Evidence

One folder per item, `output/harness-<item>/`, holding:

- `dossier.md`
- `plan.md`, with the `TESTS` block
- `ledger.md`, append only: every gate verdict with a timestamp and a reference to its evidence
- `renders/`, files named `<part>__<angle>__<iter>.png`
- `roast_N.md`, one per roast

The ledger is append only on purpose. A gate verdict is never edited, only superseded by a later entry.

## Honesty rules (every phase)

- Every claim about the real item traces to a dossier entry. Every claim that the model is correct traces to a render or a number in the ledger.
- Banned as evidence: "looks fine", "looks correct", "should be right", "probably", and "as expected" without a comparison. If one of these is the only support for a verdict, the verdict is UNVERIFIED, and UNVERIFIED is not PASS.
- Unknown stays unknown until measured. "I don't know, I'll measure it" is always a valid intermediate answer. A confident guess is not.
- The roast reports defects to the user as found, including defects in the plan or in this harness. A harness that hides its misses teaches nothing.
