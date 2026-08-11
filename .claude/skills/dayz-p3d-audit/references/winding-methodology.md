# Winding Diagnostics — Deep Methodology

Field-verified winding-validation methodology from production DayZ mod debugging
(a crate mod and a vanilla-overriding lamp mod). Complements killer #1 ("Inverted
Face Winding") in `p3d-killers.md` with validation methodology, known traps, and a
complete Blender-import checklist.

## How NOT to verify — heuristics that mislead

**Centroid-based check (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**

- It is **right-handed** (Three.js / OpenGL convention). DayZ is **left-handed**. A
  CORRECT post-flip model shows up as "winding inward" under this check while its
  declared normals point outward — that is not an inconsistency, it is the opposite
  sign of the cross product between coordinate systems.
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

1. **Check A — winding vs averaged corner normal, per face (DIAGNOSTIC).** For each
   face compute `n_winding = normalize(cross(v1-v0, v2-v0))` and compare it with the
   normalized average of `face.vertices[i].normal` over the corners. The percentage
   of faces with `dot < -0.5` indicates the handedness state:
   - **~100% UNIFORM_FLIPPED** → the EXPECTED state in DayZ (left-handed) after
     export from Blender (right-handed Z-up). The handedness change inverts the
     cross product. Field-verified in-game on production mods: rendering,
     ballistics, cursor, and collision all OK. No action needed. → severity NOTE.
   - **~0% UNIFORM_NON_FLIPPED** → either there was no handedness transform, or the
     normals were re-aligned post-transform. Verify in-game. → severity NOTE.
   - **5-95% MIXED** → real bug; rendering/collision is inconsistent between faces.
     → severity CRITICAL.

   Coordinate-system-agnostic.

2. **Check B — edge-pair topology (THE MOST RELIABLE).** Two manifold faces that
   share an edge must traverse it in opposite directions. If `face1` traverses
   `(A→B)` and `face2` also traverses `(A→B)`, one of the two is flipped.
   Coordinate-system-agnostic and independent of the modeler's intent. **Best tool
   for detecting mixed winding after a flip.**

3. **Check C — comparison against vanilla.** Match faces between the target and a
   geometrically similar vanilla model (e.g. `DZ/gear/camping/wooden_case.p3d`) by
   centroid proximity, then compare winding-derived normals. Only applicable when a
   close vanilla equivalent exists.

4. **Direct in-game test.** Rebuild the PBO → test server → inspect visual +
   collision + actions + ballistics. This is the final filter and the only 100%
   definitive one. Even when everything above says "OK", still test in-game.

## Known traps (lessons learned)

- **A winding flip applied twice** returns the model to its original state
  (idempotent modulo 2). Always write a backup (e.g. `.p3d.bak_pre_winding_flip`)
  before flipping; if the backup exists, the flip was applied at least once.
  Note: the flip helper scripts referenced by the original project are NOT bundled
  with this skill — the operation is simply swapping `vertices[1]`/`vertices[2]` on
  every face via py3d.
- **Negating the `lod.facenormals` pool** ("renegate normals" style scripts) is
  based on a misunderstanding of the format — do not do it. If it was applied, the
  pool normals are wrongly negated; revert by negating them again.
- **One field-verified crate model has mixed winding in its Visual LOD** (~38.6% bad
  edges under Check B) yet **DayZ tolerates it in rendering** (verified in-game:
  visual, ballistics, cursor, and collision all OK). Its collision LODs
  (Geometry/LandContact/ViewGeo/FireGeo) are internally consistent. Check B marking
  this CRITICAL is fine as a preventive signal even though the engine tolerated it
  in that particular case. Do not re-flip such a model unless a concrete in-game
  symptom appears.
- **`face.flags |= 0x20000` (`NoBackfaceCulling`)** sidesteps the problem in the
  Visual LOD but NOT in collision LODs. If you use it on Visual, fixing the winding
  in Geometry/GeoPhys/FireGeo/ViewGeo is **still mandatory**.
- **Making a mesh double-sided** (duplicating faces with reversed winding)
  complicates Check B: it introduces non-manifold edges (3+ faces sharing an edge),
  which is correct geometry but the check must treat it as NOTE, not CRITICAL.

## Checklist when importing a new model from Blender

1. Open the .p3d with Object Builder or py3d. List LODs and resolutions; confirm the
   required ones exist (Visual=0, Geometry=1e13, Memory=1e15) plus the recommended
   ones (LandContact=2e15, ViewGeo=6e15, FireGeo=7e15) if the object interacts with
   bullets/cursor.
2. Apply a winding flip (swap `vertices[1]`/`vertices[2]` on every face via py3d).
   Write a `.bak` backup first and confirm it was created.
3. Run Check A + Check B on ALL LODs (not just Visual).
4. If Check B reports bad edges: identify which faces, then either re-flip
   selectively or re-export from Blender with correct settings. Do NOT declare the
   model "ready" with mixed winding.
5. If everything is clean: rebuild the PBO + test in-game (visual from outside,
   bullets, actions, walking through).
6. Only after passing in-game should the model be considered "good".
