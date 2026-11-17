# Legacy diagnostic gate ladder for family B assets from before CHANGE-0

History only: the superseded order of diagnostic gates for an imported car, kept for vehicles already in flight, plus the LOD frame parity rung.

> Status: field notes measured on third-party mods (SUB_BRZ, MercedesAMGLF), each named in its entry. Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Tags such as SP-205 or LL-464 are the notes' own lesson numbers, and `[EXACT]`, `[DESIGN]` and `[CLAIM-...]` are the notes' own evidence labels. Paths such as `<vehicle-import>\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- Rung 0 diffs the model against a vanilla car; the control used throughout these notes is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` (a binarized ODOL, not read here).

## The ladder

Superseded ordering, kept for vehicles already in flight. For a NEW asset none of these
rungs fires automatically unless its exact contract is in the B1-B6 allowlist of the rip-vehicle-import
skill (`skills/rip-vehicle-import/SKILL.md`, which now lists B1 to B7).
The original wording is archived in `pre-change-0-gate-ladder.md`, next to this file.

> Nothing here is current doctrine. The findings that used to sit under this heading and ARE
> current (rip panel open rim SP-247, offline viewer traps SP-248, ViewPilot curation SP-249,
> gate calibration) were promoted to their own sections on 2026-08-15 —
> they were invisible in the index while filed under "LEGACY". They are now in `rip-panel-open-rim.md`,
> `view-pilot-and-first-person.md` and `method-and-gate-calibration.md`.

For vehicles already in flight, this preserves the diagnostic order from before CHANGE-0. For a new family B
asset, none of these rungs executes automatically unless its exact contract appears in the B1-B6
allowlist of that skill. The original wording and order are archived in
`pre-change-0-gate-ladder.md`; every rung remains invocable by hand during diagnosis.

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
   misses. HINT — the in-game render is the final gate (s13). (First-person INTERIOR is a separate LOD:
   ViewPilot 1100, DOUBLE-SIDE it per #10g, not orient-inward.)
5. **MATERIAL / LOD / PATHS** — each visible piece has a material selection (not `untagged`), lives in
   LOD0, and its textures/rvmats resolve (the `/dayz-build-pbo` references; `/dayz-lint` checks missing files in this repo). A piece with NO material renders invisible
   too — same symptom as inverted winding, different cause; rule it out here.

6. **LOD FRAME PARITY — every `_lodN` variant carries the SAME frame as its LOD0** (added 2026-08-01,
   MercedesAMGLF R22F-003). Any post-hoc transform of a proxy-split body (yaw fix, flip, translate)
   must enumerate EVERY file the host references — including the `_lod1`/`_lod2`/`_lodN` variant of
   each proxy — not just the base pieces. A fix that touches only the bases leaves the distant LODs in
   the OLD frame: the car looks perfect up close and draws its cabin/mechanicals rotated at mid
   distance, the moment the engine switches LOD. Why nothing catches it: topology, face counts, vertex
   ceilings and every structural verifier stay green — each variant is internally valid, just wrongly
   oriented — and the in-game test passes too, unless the tester WALKS AWAY far enough to trip the
   switch. Gate — TWO DISTINCT checks; conflating them makes the gate impossible (this correction
   came from the R22 that reviewed the original wording, 2026-08-01): **(a) transform applied** —
   each rewritten file against ITS OWN input: exact rotation, immutable topology, error
   `0.000000000`. That proves the fix ran on that file; it says nothing about LOD-to-LOD agreement.
   **(b) frame parity LODn vs LOD0** — a metric that TOLERATES decimation (principal axes, oriented
   bounding box, centroid + direction of matched anatomical features). Never point-to-point: a
   legitimately simplified LOD has no vertex correspondence with LOD0, so demanding identical
   topology between them would forbid the decimation the ladder exists for. Plus one in-game orbit
   backing off through LOD1 and LOD2.
   Real cost: the MercedesAMGLF yaw-180 fix rotated the 6 base proxies and left 12 `_lod1`/`_lod2`
   files byte-identical to the pre-fix backup — undetected for 25 days across several visual reviews,
   because the generating script's file list enumerated only the bases (`cabin_align.py:18`).
   Corollary for the CONTRACT, not just the gate: if no acceptance criterion demands LOD-to-LOD frame
   parity, this defect is not merely missed — it is *out of scope*, so no reviewer is wrong to pass it.
   Add the criterion (MercedesAMGLF `AC1.4c`) alongside the check. Cross-project: any car with a LOD
   ladder plus body proxies has the identical exposure (SUB_BRZ shares the shape exactly).
