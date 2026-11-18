# Legacy diagnostic gate ladder for family B assets from before change 0

History only: the superseded order of diagnostic gates for an imported car, kept for vehicles already in flight, plus the LOD frame parity rung.

> Status: the measurements below were taken on third-party vehicle mods (TestCoupe, TestMercedes), named in each entry; they are third-party mod behaviour, not vanilla, and were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. Script names such as `winding_consistency.py`, `gate_car.py`, `raycast_winding.py`, `dedup_faces.py`, `position_dedup.py` and `cabin_align.py` belong to those mods' work folders, which are not part of this repo. "Preflight #N" and "#N" mean the numbered invariants; `skills/_shared/vehicles/README.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- Rung 0 diffs the model against a vanilla car; the control used throughout is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` (a binarized ODOL, not read here).

## The ladder

Nothing here is current doctrine. This is the diagnostic order from before change 0, the family B cutover of 2026-08-05 that made the B1 to B6 allowlist the only automatic checks (B7 was added on 2026-08-16), kept for vehicles already in flight. For a new family B asset none of these rungs runs automatically unless its exact contract is in the allowlist of the family B runbook (`rip-family-b-runbook.md`, now B1 to B7); every rung can still be run by hand during diagnosis. The rule that set the order is in `pre-change-0-gate-ladder.md`, next to this file.

The findings that used to sit under this heading and are current (the open rim of a rip panel, the offline viewer traps, ViewPilot curation and gate calibration) are in `rip-panel-open-rim.md`, `view-pilot-and-first-person.md` and `method-and-gate-calibration.md`.

0. **STRUCTURAL PARITY** (config/model.cfg) — preflight #1-#6 (get-in, geometry `class=vehicle`,
   componentNN dual-tag+collidable, crew/wheel proxies, DamageZones). Gates spawn/drive, not looks.
   Do it via the parity-first vanilla diff.
1. **DEDUP coincident duplicate faces** (z-fight speckle) — `dedup_faces.py` + `position_dedup.py` (#10e).
   FIRST geometry gate: duplicates dirty every later check. A clean car has ~0 coincident.
2. **WINDING UNIFORMITY per piece** — topological, no raycast — `scripts\winding_consistency.py --car <p>`
   -> every visible piece `OK uniform`. THE basic winding gate; faces inverted vs their NEIGHBOURS =
   triangular artifacts in-game (#10f). Cheap; run BEFORE anything raycast.
3. **ORIENTATION vs SOURCE** — verify each piece preserved the raw glTF winding (#10j); use
   `tools\raycast_winding.py` only as the #10d see-through HINT (L-vs-R asymmetry = bug tell), NEVER as
   authority to flip a whole piece — an all-single-sided piece can be legitimate cabin-side geometry
   (`glass*int_a`); that oracle class is what inverted the BRZ rear glass.
4. **SEE-THROUGH vs exterior** — `scripts\gate_car.py --car <p>` (#10d): body `color`/`glass`
   scattered=noise, dense cluster / L-vs-R asymmetry = bug. Catches isolated inverted faces topology
   misses. HINT — the in-game render is the final gate. (First-person INTERIOR is a separate LOD:
   ViewPilot 1100, DOUBLE-SIDE it per #10g, not orient-inward.)
5. **MATERIAL / LOD / PATHS** — each visible piece has a material selection (not `untagged`), lives in
   LOD0, and its textures/rvmats resolve (the `/dayz-build-pbo` references; `/dayz-lint` checks missing files in this repo). A piece with NO material renders invisible
   too — same symptom as inverted winding, different cause; rule it out here.

6. **LOD FRAME PARITY — every `_lodN` variant carries the SAME frame as its LOD0** (added 2026-08-01,
   TestMercedes). Any post-hoc transform of a proxy-split body (yaw fix, flip, translate)
   must enumerate EVERY file the host references — including the `_lod1`/`_lod2`/`_lodN` variant of
   each proxy — not just the base pieces. A fix that touches only the bases leaves the distant LODs in
   the OLD frame: the car looks perfect up close and draws its cabin/mechanicals rotated at mid
   distance, the moment the engine switches LOD. Why nothing catches it: topology, face counts, vertex
   ceilings and every structural verifier stay green — each variant is internally valid, just wrongly
   oriented — and the in-game test passes too, unless the tester WALKS AWAY far enough to trip the
   switch. Gate — TWO DISTINCT checks; conflating them makes the gate impossible: **(a) transform applied** —
   each rewritten file against ITS OWN input: exact rotation, immutable topology, error
   `0.000000000`. That proves the fix ran on that file; it says nothing about LOD-to-LOD agreement.
   **(b) frame parity LODn vs LOD0** — a metric that TOLERATES decimation (principal axes, oriented
   bounding box, centroid + direction of matched anatomical features). Never point-to-point: a
   legitimately simplified LOD has no vertex correspondence with LOD0, so demanding identical
   topology between them would forbid the decimation the ladder exists for. Plus one in-game orbit
   backing off through LOD1 and LOD2.
   Real cost: the TestMercedes yaw-180 fix rotated the 6 base proxies and left 12 `_lod1`/`_lod2`
   files byte-identical to the pre-fix backup — undetected for 25 days across several visual reviews,
   because the generating script's file list enumerated only the bases (`cabin_align.py`).
   Corollary for the CONTRACT, not just the gate: if no acceptance criterion demands LOD-to-LOD frame
   parity, this defect is not merely missed — it is *out of scope*, so no reviewer is wrong to pass it.
   Add the criterion alongside the check. Any car with a LOD
   ladder plus body proxies has the identical exposure (TestCoupe shares the shape exactly).
