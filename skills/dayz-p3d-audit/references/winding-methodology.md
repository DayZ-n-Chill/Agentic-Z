# Winding Diagnostics: Deep Methodology

Field-verified winding-validation methodology from production DayZ mod debugging
(a crate mod and a vanilla-overriding lamp mod). Complements killer #1 (collision LOD
wound outward) in `p3d-killers.md` with validation methodology, known traps, and a
complete Blender-import checklist. The measured cases, the state table for Check A and
the step by step fix are in `winding-diagnostics.md`; how to read the py3d winding
findings is in `winding-absolute-check.md`.

The convention to check against: in a correct MLOD both the cross product
`cross(v1-v0, v2-v0)` and the stored normals point away from the side meant to be seen.
On a solid seen from outside, which every collision component is, both point inward.

**Contents**

- How NOT to verify: heuristics that mislead
- How to verify correctly
- Known traps (lessons learned)
- Checklist when importing a new model from Blender

## How NOT to verify: heuristics that mislead

**Centroid-based check (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**

- It is **right-handed** (Three.js / OpenGL convention). DayZ is **left-handed**. A
  CORRECT model shows up as "winding inward" under this check, with its declared
  normals inward too: that is not an inconsistency, it is the opposite sign of the
  cross product between coordinate systems. (This line once said the normals of a
  correct model point outward. That is the older outward-normal convention, which
  Check A below reads as UNIFORM_FLIPPED.)
- It assumes **convex geometry** (compares against the LOD centroid). For hollow
  boxes with thick walls, correct interior faces get flagged as "inverted".
- **Conclusion: it is NOT valid for validating absolute DayZ winding.** This skill
  shipped with this check for months and it produced up to 100% false positives on
  correct models; it has since been removed from `audit_p3d.py`. It is only useful
  for relative consistency before/after the SAME operation, or when compared against
  a vanilla reference.

**Comparing `face.vertices[i].normal` against the cross product directly does NOT
work.** The normals in the `lod.facenormals` pool are per-vertex-corner smoothed
(smoothing groups): on flat faces they match the flat normal; on smoothed faces they
don't. To use them as an "intent" reference you must **average the normals of the 3-4
corners of ONE face** and compare that with `cross(e1, e2)`. See Check A below.

**Assuming `lod.facenormals[i]` is the normal of `lod.faces[i]`.** False.
`lod.facenormals` is a global POOL (its size is the MLOD header's `num_facenormals`,
**independent** of `len(lod.faces)`); each Vertex points into it via `normal_index`.
Confusing the two leads to checks that never run (length mismatch) or checks that
compare the wrong things.

## How to verify correctly

1. **Check A: winding vs averaged corner normal, per face (DIAGNOSTIC).** For each
   face compute `n_winding = normalize(cross(v1-v0, v2-v0))` and compare it with the
   normalized average of `face.vertices[i].normal` over the corners. The percentage
   of faces with `dot < -0.5` counts the faces that strongly disagree with their
   stored normals. It does not say which way either one points:
   - **~0% UNIFORM_NON_FLIPPED** → winding and normals agree (count agreement as well,
     `dot > 0`: only about 100 % agreement means they agree). A correct export reads
     this. So do a mirrored export and an inside-out model whose faces and normals
     were turned together. → severity NOTE: consistent with a correct model, not proof.
   - **~100% UNIFORM_FLIPPED** → winding and normals disagree: the older
     outward-normal convention (cross product inward, normals outward), or a correct
     export whose faces were reversed afterwards, which is inside-out. One crate mod in
     this state was field-verified in game (rendering, ballistics, cursor and collision
     all OK), but it is not what a correct conversion writes. → severity WARNING on a
     new export.
   - **5-95% MIXED** → parts in different states, not a verdict by itself. A car door
     verified in game reads mixed with no face group inverted. Split the census by
     part and locate any group wound against its neighbours with Check B. → severity
     WARNING; a visible part that reads inside-out is the defect.

   This list once called UNIFORM_FLIPPED the expected state after a Blender export
   (NOTE, no action) and MIXED a real bug (CRITICAL). Later in-game measurements
   corrected both; the evidence and the table that turns each state into a fix are in
   `winding-diagnostics.md`.

   Coordinate-system-agnostic. Leave proxy triangles out of the count and out of any
   fix: their vertex order encodes the proxy frame.

2. **Check B: edge-pair topology (THE MOST RELIABLE).** Two manifold faces that
   share an edge must traverse it in opposite directions. If `face1` traverses
   `(A→B)` and `face2` also traverses `(A→B)`, one of the two is flipped.
   Coordinate-system-agnostic and independent of the modeler's intent. **Best tool
   for detecting mixed winding after a flip.**

3. **Check C: comparison against vanilla.** Match faces between the target and a
   geometrically similar vanilla model (e.g. `DZ/gear/camping/wooden_case.p3d`) by
   centroid proximity, then compare winding-derived normals. Only applicable when a
   close vanilla equivalent exists.

4. **Direct in-game test.** Rebuild the PBO → test server → inspect visual +
   collision + actions + ballistics. This is the final filter and the only 100%
   definitive one. Even when everything above says "OK", still test in-game.

## Known traps (lessons learned)

- **A winding flip applied twice** returns the model to its original state.
  Always write a backup (e.g. `.p3d.bak_pre_winding_flip`)
  before flipping; if the backup exists, the flip was applied at least once.
  Note: no flip helper script is bundled
  with this skill: the operation is `face.vertices.reverse()` on every face via py3d.
  (This note once said to swap `vertices[1]`/`vertices[2]`. That is the same for a
  triangle but turns a quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face.)
- **Negating the `lod.facenormals` pool** ("renegate normals" style scripts) is
  based on a misunderstanding of the format: do not do it. If it was applied, the
  pool normals are wrongly negated; revert by negating them again.
- **One field-verified crate model has mixed winding in its Visual LOD** (~38.6% bad
  edges under Check B) yet **DayZ tolerates it in rendering** (verified in-game:
  visual, ballistics, cursor, and collision all OK). Its collision LODs
  (Geometry/LandContact/ViewGeo/FireGeo) are internally consistent. Treat such a
  Check B reading as a preventive signal even though the engine tolerated it in that
  particular case (where py3d's `validate()` reports it, the audit prints
  `WARN_WINDING_EDGE_INCOHERENT` as a WARNING). Do not re-flip such a model unless a concrete in-game
  symptom appears.
- **`face.flags |= 0x20000` (`NoBackfaceCulling`) does not work.** It was once listed
  here as a way round the problem in the Visual LOD. Measured since: the faces stayed
  see-through in game, because binarize discards the MLOD per-face `flags` field (three
  MLODs that differ only in `face.flags` binarize to byte-identical models). The route
  that works for a part seen from both sides is double-sided geometry, and fixing the
  winding in Geometry/GeoPhys/FireGeo/ViewGeo is mandatory either way
  (`winding-diagnostics.md`, "Known traps").
- **Making a mesh double-sided** (duplicating faces with reversed winding)
  complicates Check B: it introduces non-manifold edges (3+ faces sharing an edge),
  which is correct geometry but the check must treat it as NOTE, not CRITICAL.

## Checklist when importing a new model from Blender

1. Open the .p3d with Object Builder or py3d. List LODs and resolutions; confirm the
   required ones exist (Visual=0, Geometry=1e13, Memory=1e15) plus the recommended
   ones (LandContact=2e15, ViewGeo=6e15, FireGeo=7e15) if the object interacts with
   bullets/cursor.
2. Decide whether the export needs a winding change at all: read Check A and the
   direction test of `winding-diagnostics.md` first. A model converted with the model
   pipeline skill's Blender to DayZ conversion needs none. If a whole-model flip is
   needed, use `face.vertices.reverse()` on every face (never a `vertices[1]`/`[2]`
   swap), write a `.bak` backup first and confirm it was created. (This step once
   said to flip every import; a flip on a correct export turns it inside-out.)
3. Run Check A + Check B on ALL LODs (not just Visual), and `/dayz-p3d-audit`.
4. If Check B reports bad edges: identify which faces, then either re-flip
   selectively or re-export from Blender with correct settings. Do NOT declare the
   model "ready" with mixed winding.
5. If everything is clean: rebuild the PBO + test in-game (visual from outside,
   bullets, actions, walking through).
6. Only after passing in-game should the model be considered "good".
