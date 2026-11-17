# Imported-model gate ladder before CHANGE-0 (archived snapshot)

History only: the old ordered ladder of visual gates for an imported car, kept for manual diagnosis and for vehicles already built against it.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

> Snapshot of 2026-08-05. Nothing here is current doctrine; the current rules are in `method-and-gate-calibration.md` and the invariant files.

## Vanilla anchors checked on `P:\`

- The ladder's rung 0 diffs the model against a vanilla car; the control used throughout these notes is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` (binarized, not read here).

## GATE LADDER — imported-model VISUAL correctness (run IN ORDER, cheap -> expensive)

Every imported car (rip→DayZ) passes these gates IN THIS ORDER. Skipping a rung = re-work later:
`gate_car` was built at rung 4 (see-through) while rung 2 (the most BASIC winding check) was missing,
and the user caught the defect in-game (BRZ backlight mixed-winding, 2026-07-01). Rule: before building
a "done" validator, enumerate the failure modes and name which rung covers each — if you can't, don't
code yet. Run cheap topological gates before expensive raycast/in-game ones.

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
   LOD0, and its textures/rvmats resolve (dayz-pbo-build). A piece with NO material renders invisible
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

**Calibration + scope (so a gate is trustworthy, not a false green):**
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
