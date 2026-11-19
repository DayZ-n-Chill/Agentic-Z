# Building a model in checked stages

How to take a production model, or a rebuild that has to match a vanilla object, from the first question to the packed file in seven stages, each ending in a written pass or fail. A single mesh or a quick look at a render needs only `blender-assembly.md` and `blender-visual-review.md`.

This is a working method, not a set of facts about the game. The vanilla numbers it asks for are read from the vanilla object while the work is done.

## Why stages

A model built from what the item probably looks like, checked by the same pass that built it and called done because nothing crashed, is usually wrong. The stages turn each of those habits around:

- Nothing is modelled from memory. References from several sides come first.
- Nothing is called correct without a number or a render behind it.
- The review looks for faults. Its result is a list of faults, not a verdict.
- A stage that fails stops the work. Never note a failure and carry on past it.

## Where the techniques live

| Work | Read or run |
|---|---|
| Building geometry in Blender and the helper library | `blender-assembly.md` |
| The checks after each part (`verify_bounds`, `verify_overlap`, `verify_mesh_integrity`, `audit_all`) | `blender-assembly-checks.md` |
| Capturing renders with `vr_capture` and the fix loop | `blender-visual-review.md` |
| What to look for in a render | `blender-review-checklist.md` |
| Why a render cannot judge DayZ face winding | `blender-winding-flips.md` |
| A mesh from AI generation: retopology, the `_nohq` bake, the handoff | `ai-generation.md` |
| LODs, vertex budgets and the export to `.p3d` | `lods.md`, `axes-and-winding.md` |
| Checking the exported `.p3d`, face winding included | `/dayz-p3d-audit` |
| Packing the mod | `/dayz-build-pbo` |

This repo ships no AI mesh generator (image or text to 3D). Without one at hand, stay on the `blender-assembly.md` route, and never invent a generator or its API.

## The seven stages

| Stage | What it produces | Passes when |
|---|---|---|
| Brief | The item, its use, its route and its triangle budget | All four have written answers |
| Research | The research sheet (below) | Four views on file, the sizes sourced or marked as estimates, the part list complete, the unknowns written down |
| Plan | A part list with a pass or fail test for each part | Every part has at least one number or render it must match |
| Build | Each part, checked as it is made | Each part passes its own checks |
| Review | A ranked list of faults | No area fails, no serious fault is open |
| Fix | One fix at a time, with before and after renders | The review passes again |
| Final check | The model with all its evidence | Every check passes on the final geometry |

Write each pass or fail, with the evidence behind it, into the build log (see "Where the record goes"). A fail means fix it, or go back one stage.

## The brief

Answer these first. Ask the user only for what cannot be worked out.

1. Which item, exactly. "A rifle" is not an answer; "an AKM pattern rifle, wooden furniture, worn" is.
2. What it is for: a DayZ mod (which slot and behaviour), a game asset for another engine, or a render only. This sets the triangle budget, the LOD plan and which export and audit steps apply.
3. The route. A hard surface item is built in Blender with `blender-assembly.md`. An organic or sculpted shape takes its base mesh from AI generation when a generator is at hand. On that route research and planning still run in full, because the review is scored against them; only the build stage is replaced, and the mesh then goes to review like any other. For a DayZ item from AI generation, the DayZ steps (retopology of a mesh that is not manifold, the `_nohq` bake, the handoff) are in `ai-generation.md`.
4. The budget: the triangle range of LOD 0. For DayZ, take it from the triangle counts of the vanilla object that matches, not from taste.

An unanswered item is a question for the user, not a guess.

## Research before modelling

What a language model remembers of an object's shape is a guess, not a reference. Collect:

- At least four views (front, side, top and three quarter), plus a close up of every detail zone (grip, latches, fasteners, seams). For a DayZ item, also bring the matching vanilla model into the scene at 1:1. Vanilla models on `P:\` are binarized, so Blender opens one only after an outside ODOL to MLOD converter, which this repo does not ship.
- The overall length, width and height from two separate sources, and at least five landmark sizes (barrel length, grip height, wheel diameter). Where no source exists, write `ESTIMATE ±X%`; an estimate without that label is an invention.
- Every part that looks distinct, by name. This list becomes the build order.
- Everything you could not confirm, each with a decision: find out, accept within a tolerance, or ask the user. A non trivial item with no unknowns has not been looked at closely enough.

Copy this sheet to `output/model-build-<item>/research.md` and fill it in:

```markdown
# Research: <item>

Use: <DayZ mod / other engine / render only>. Route: <Blender build / AI generation>.

## The item
- Exact item: <make, pattern, variant, condition>
- Role in game: <slot, behaviour, the vanilla object to match>

## Views
| View | Source (URL or file) | Notes |
|---|---|---|
| front | | |
| side | | |
| top | | |
| three quarter | | |
| close up: <detail zone> | | |

## Sizes
| Measurement | Value | Source A | Source B or ESTIMATE ±X% |
|---|---|---|---|
| Overall length | | | |
| Overall width | | | |
| Overall height | | | |
| Landmark 1 to 5 | | | |

## Parts
| Part | What shows (feeds the detail list) | How it is built (`blender-assembly.md` rule) |
|---|---|---|

## Materials
| Part | Material | Finish and wear | Notes for `_co`, `_nohq`, `_smdi` |
|---|---|---|---|

## Unknowns
| Unknown | Decision: find out, accept ±tolerance, ask the user | Result |
|---|---|---|
```

Give every detail zone at least one close up. When a side cannot be found, write it down as an unknown; never fill in a hidden side by symmetry without saying so. The size table is what the review measures against, so a thin sheet makes the review blind.

## Plan with pass and fail tests

Write the plan and its tests before any geometry. A plan without tests goes back, it is not worked around.

1. The parts in build order, each with the `blender-assembly.md` rule that builds it.
2. Every joint and every detail with its size, as in `blender-assembly.md`.
3. A `TESTS` block: for each part, its sizes within 5 % of the research sheet, the overlaps at its joints, and the `verify_mesh_integrity` result it must give (closed or open, how many ngons). For the whole model: the triangle range, the landmarks the final render must match, and which audits apply (for DayZ, the winding and structure checks of `/dayz-p3d-audit`).

A part with no test cannot fail, so it cannot be checked either.

## Build one part at a time

Load the helper library of `blender-assembly.md` first; the checks are described in `blender-assembly-checks.md`. For each part:

1. Build it, then run `verify_bounds` and `verify_overlap` against the joints in the plan.
2. Run `verify_mesh_integrity` after every boolean, modifier or loft.
3. Capture a quick render of each complex part before building on it (`blender-visual-review.md`, "Capturing four angles"). For a risky part, build two versions with different settings and pick from the renders.
4. Log the results. A part that fails stops the build there.

Do not improve the plan while building. Something found to be necessary goes into the log as a change to the plan with one line of reason; something found to be nice is dropped.

## Review: look for faults

The review is a separate pass with the opposite goal to the build. Take fresh renders with `vr_capture` (all four angles, the 1 m scale cube in frame) and close ups of every detail zone, then go through the eight areas. Each verdict names its evidence: a render file and what it shows, or a measured number against the research sheet. "Looks fine", "looks correct", "should be right", "probably" and "as expected" without a comparison are not evidence; a verdict that rests on one of them is unchecked, and unchecked is not a pass.

| Area | Compare | Evidence |
|---|---|---|
| Outline | Named landmarks (roofline, wheel arch, muzzle, grip curve) against the reference views, not the overall impression | The render file and the reference view, per landmark |
| Sizes | Measured sizes from `vr_capture` or `verify_bounds` against the research sheet, with the difference in percent. Over 5 % is a fault unless the plan allowed it | The table itself |
| Orientation and scale | Forward axis right, nothing mirrored or upside down, size right against the scale cube (and for DayZ against the vanilla model at 1:1) | A render with the scale cube in frame |
| Detail | Every feature of the detail list, marked present, missing or degraded. A missing planned feature is a fault. A main object shows at least three kinds of feature | A close up per detail zone |
| Mesh integrity | `verify_mesh_integrity` on every part of the current geometry. Any failure fails the area | The check output in the log |
| Shading and normals | The Face Orientation overlay (red toward the camera is a fault), black facets, pinching, smoothing across hard edges, ngons on curves. For DayZ only the winding relative to a vanilla model can be judged here; the absolute winding is decided by `/dayz-p3d-audit` and in game (`blender-winding-flips.md`) | A viewport capture and a render |
| Assembly | Gaps, floating parts, shimmer between angles from faces on top of each other, parts sunk deeper than planned | `verify_overlap` and the three quarter render |
| Fit for the target | Triangles per LOD within budget; for DayZ, ride height and footprint measured against the vanilla model (a ground item sits with its lowest point at about 0), proxies and slots present. For another engine, what its export format requires | Counts and sizes against the vanilla numbers |

Rate each area clean (checked, evidence cited), minor (small faults, or only part of the evidence) or failing (a fault with no way round it, or nothing on file to check it with). A verdict with no cited evidence is at best minor. The review passes when no area fails, no more than three are minor, and no high severity fault is open.

List the faults ranked, in this form:

| Fault | Severity | Area | Evidence | Proposed fix |
|---|---|---|---|---|

High is visibly wrong or breaks the use (wrong proportions, a broken mesh, a major part missing). Medium shows in normal viewing (a gap, a missing planned detail, a shading fault). Low is polish (a bevel width, a small texture seam).

A first review with no faults is suspect, not a success: review again from new angles with tighter close ups. Two clean reviews in a row are accepted.

## Fix one fault at a time

Follow `blender-visual-review.md`: one diagnosis, one fix, the same angles rendered again, the before and after pair kept. After fixes to one or two parts, review only the areas they touch, plus mesh integrity on those parts, from the same angles as before. After fixes to three or more parts, review everything again. Stop when `correction_loop.py` (in `skills/dayz-model-tools/scripts/`) returns `refine-spec`, which it does once the same fault survives two fixes in a row: the plan for that part is wrong, so plan it again.

## Final check

1. Every number check passes: `audit_all`, `verify_mesh_integrity` on every part, the triangle count within budget.
2. The review passed on the current geometry, not on renders of an earlier version.
3. For DayZ, run `/dayz-p3d-audit` on the export and check ride height and scale against the vanilla model. Absolute face winding is decided by the audit and in game, never from a Blender render.
4. The record is complete.

Only then does the model go to `/dayz-build-pbo` or to the user.

## Where the record goes

One folder per item, `output/model-build-<item>/`:

- `research.md`, the sheet above
- `plan.md`, with its `TESTS` block
- `log.md`, added to and never edited: each pass or fail with its time and a pointer to its evidence. A wrong verdict is answered by a later entry, not rewritten.
- `renders/`, files named `<part>__<angle>__<version>.png`
- `review-<n>.md`, one per review

Report faults to the user as they are found, including faults in the plan or in this method.
