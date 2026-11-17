# Winding diagnostics: measured cases and the fix procedure

The deep companion of `winding-methodology.md`: how each winding check reads on measured models, how to turn a Check B result into a safe fix, and where offline checks stop. Read `winding-methodology.md` first for the short method and the import checklist. Reading rules for py3d's absolute winding finding are in `winding-absolute-check.md`.

Where this file and `winding-methodology.md` once disagreed (what the two uniform Check A states mean, the severity of a mixed reading, the `0x20000` face flag), the measurements here are the newer evidence and `winding-methodology.md` was corrected to match.

**Not yet checked on `P:\`.** These are measurements on mod models (a wooden crate mod, a wall lamp, the SUB_BRZ car door, three gun rack models, the giant infected build of the dayz-characters skill) in game and offline with py3d. Vanilla models on `P:\` are binarized, so none of this can be read from them.

*Rule 12* and *Rule 18* are rules of the model pipeline skill (`dayz-model-pipeline`): Rule 12 is the Blender to DayZ conversion, after which both the cross product `cross(v1-v0, v2-v0)` and the stored normals point away from the side meant to be seen; Rule 18 is the per-component inward check of a collision LOD. `[OFFLINE MEASURED]` marks a result measured offline on the date given.

**Contents**

- How not to verify: misleading heuristics
- How to verify (Check A with its state table, Check B, Check C, in game, the spawn gate)
- Known traps
- From Check B to fix: isolate the minority group and flip it whole
- Render-sign A/B and source-profile limits

## How NOT to verify — misleading heuristics

**Centroid-based check (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**
- It is **right-handed** (Three.js / OpenGL convention). DayZ is **left-handed**. A CORRECT model will appear as "winding inward" in that check, with its declared normals inward too (Rule 12 of `dayz-model-pipeline`) — not incoherence, it is the opposite sign of cross product between systems. *(Corrected 2026-10-02: this line said a correct post-flip model has OUTWARD declared normals, the older convention that Check A below labels UNIFORM_FLIPPED.)*
- Assumes **convex geometry** (compares against LOD centroid). For hollow boxes with thick walls, correct interior faces are marked as "inverted".
- **Conclusion: DOES NOT WORK for validating absolute DayZ winding.** The `dayz-p3d-audit` skill had it for months and produced up to 100% false positives on correct models. Only valid for relative consistency before/after SAME operation, or compared against a reference vanilla.

**Comparing `face.vertices[i].normal` with cross product directly does NOT work.** Normals in `lod.facenormals` pool are smoothed per-vertex-corner (smoothing groups): on flat faces they match flat normal; on smoothed faces they do not. To use them as "intent" reference one must **average normals of the 3-4 corners of ONE face** and compare against `cross(e1, e2)`: Check A below. `audit_p3d.py` does not run Check A; its winding findings come from `P3D.validate()` of the DayZ fork of py3d (printed only when that fork is in use), whose absolute check (`ERR_WINDING_VS_NORMALS`, `winding-absolute-check.md`) takes the first corner's normal. *(Corrected 2026-10-02: this line pointed at Check A in `audit_p3d.py`.)*

**Assuming `lod.facenormals[i]` is normal of `lod.faces[i]`.** False (`_shared/py3d-mlod-notes.md`). `lod.facenormals` is a global POOL (size = MLOD header `num_facenormals`, **independent** of `len(lod.faces)`); each Vertex points to it via `normal_index`. Confusing them leads to checks that never run (length mismatch) or checks comparing wrong things.

## How TO verify

1. **Check A — winding-vs-averaged-normal per face (DIAGNOSTIC).** For each face, calculate `n_winding = normalize(cross(v1-v0, v2-v0))` and compare with normalized average of `face.vertices[i].normal` over corners. On a quad that is not planar and convex, take `n_winding` from the face's vector area instead, the sum of `cross(v[j] − v[0], v[j+1] − v[0])` over its fan (step 3 of "From Check B to fix"): its first three corners can point the other way. On a triangle the two are the same; the SUB_BRZ door and the Rule 12 MLODs measured below are all triangles. % of faces with `dot < -0.5` counts the faces that strongly disagree with their stored normals; it does not say which way either one points (Rule 18 of `dayz-model-pipeline`). Leave `proxy:*` triangles out of this census and out of every fix below: their vertex order encodes the proxy frame (see "Render-sign A/B" below).
   - **~0% UNIFORM_NON_FLIPPED** → no face strongly disagrees. Count agreement as well, on the same averaged normal (`dot > 0`): only ≈ 100 % agreement means winding and normals agree, because normals turned 90-120° away from their faces also read 0 % here. The absolute check in `winding-absolute-check.md` counts agreement on the first corner's normal only, so on smoothed normals the two counts can differ; a face whose corner normals point opposite ways is a defect to inspect, not a sign to flip. A correct Rule 12 export reads this with ≈ 100 % agreement (`dayz-model-pipeline`: cross product AND stored normals both INWARD), like the production MLODs in `winding-absolute-check.md`, "What 0 % means". So do a det=+1 mirror with reversed faces and negated normals, and an inside-out model with both OUTWARD. → severity NOTE: consistent with Rule 12, not proof of it.
   - **~100% UNIFORM_FLIPPED** → they disagree. The older outward-normal convention reads this: cross product inward, normals outward, as in the det=+1 recipe the giant infected build shipped with (the dayz-characters skill, `references/character-rigging.md`, section 6; `check_dayz_winding.py` passed this state until its 2026-10-02 rewrite for Rule 12, and now fails it on the normals). It renders solid but is not what Rule 12 writes. Crate_Wooden read this state: **Empirically verified with Crate_Wooden 2026-04-25 in-game: render/bullets/cursor/collision all OK.** A correct export whose faces were reversed afterwards also reads it, and is inside-out. → severity WARNING on a new export.
   - **5-95% MIXED** → parts in different states, not a verdict by itself. [OFFLINE MEASURED 2026-10-02] The SUB_BRZ co-driver door MLOD of `winding-absolute-check.md` (verified in game; its 26 % agreement reproduced) reads MIXED: 72.67 % of 11,921 faces at `dot < -0.5`, 25.9 % agreeing. Check B finds 1 of its 17,542 two-face edges traversed the same way by both faces (a paint triangle against a black-trim one); with that edge cut, each of its 23 welded components orients as one group with no conflict, so no face group is wound against its neighbours, and that seam is left to inspect. The parts vote apart: the exterior paint, black trim and mirror read 94-100 % of their faces flipped (the paint winds its cross product into the door and stores its normals toward the outside: the older outward-normal convention, which renders solid and, measured on a character, lights inverted — the dayz-characters skill, 2026-10-02; not checked on this door), while the cabin plastic, leather and metal and the glass read 97.9-100 % agreeing. Coincident twins (opposite winding, centroids within 2 mm) are 144 faces, and the census without them is unchanged (72.7 % flipped, 25.9 % agreeing). Never reverse the LOD on this reading. Locate any group wound against the rest of its component with Check B ("From Check B to fix", steps 1-2), split the census by part (welded component, then material), and take each part's or group's repair from the table below, each face read as step 3 of "From Check B to fix" reads it (vector area, ±0.5, corner margin, the part's row decided first): on a part whose normals agree with its winding, a group whose stored normals disagree with its own winding (still pointing like its neighbours') needs `reverse()` only (fourth row), and the coupled negation of "From Check B to fix" step 3 fits only a group whose normals agree with its inverted winding (second row); on a part kept in the older convention on purpose, as this door's paint could be (it renders solid in game), the two readings swap. → severity WARNING; a visible part that the table reads inside-out is the defect, its urgency set by visibility ("From Check B to fix", item 2). *(Corrected 2026-10-02: this bullet read "real bug, inconsistent render/collision between faces. → severity CRITICAL", which that door, verified in game, contradicts; `winding-absolute-check.md`, rule 2.)* *(Corrected 2026-10-02: its repair sentence read "a group whose stored normals disagree with its own winding (still pointing like its neighbours') needs `reverse()` only (fourth row), and the coupled negation of "From Check B to fix" step 3 fits only a group whose normals agree with its inverted winding (second row)" for every part; on this door's paint it picks the wrong branch: "From Check B to fix", step 3.)*

   Coordinate-system-agnostic. Neither uniform label is a fix instruction. First decide, part by part, whether the cross product points AWAY from the side meant to be seen (into the material: the MLOD convention of Rule 12, which on a solid seen from outside is inward) or TOWARD it:

   - visual LOD: the signed volume by winding of each closed shell. Weld points by position, then link two faces only through an edge that exactly those two faces share: parts that merely touch (a common vertex, or an edge used by more than two faces) stay separate shells, and a shell with an open edge has no meaningful sign. Negative = away from a viewer outside, the production sign of a solid (`winding-absolute-check.md`, rule 4); positive = away from a viewer inside, what a room meant to be seen from inside reads. Never decide on the sum over the LOD, nor on a union you cannot split into closed shells: it can hide an inverted part, and reversing it can move the inversion onto a healthy one;
   - collision LODs: Rule 18's per-component outward check; their whole-LOD sign is mixed even on shipped models (rule 7 there);
   - open sheets and double-sided parts: no sign decides; use the visibility battery of "From Check B to fix".

   Then fix the side that is wrong, part by part (a normal shared with a face you leave alone gets a new pool entry: item 3 of "From Check B to fix"):

   | Winding vs stored normals | Cross product | State | To reach Rule 12 |
   |---|---|---|---|
   | agree: UNIFORM_NON_FLIPPED and ≈ 100 % agreement | away from the visible side | Rule 12 | nothing |
   | agree | toward the visible side | inside-out, normals toward the viewer too | `face.vertices.reverse()` on every face of the part AND negate its normals |
   | disagree: UNIFORM_FLIPPED, or ≈ 0 % agreement | away from the visible side | normals toward the viewer: the older outward-normal convention | keep the winding, negate the normals (`winding-absolute-check.md`, rule 5) |
   | disagree | toward the visible side | a correct export with every face reversed | `face.vertices.reverse()` on every face of the part, keep the normals |

   A det=+1 mirror lands in the same row as its unmirrored twin: whatever the row, check chirality on an asymmetric feature (Rule 12).

   [OFFLINE MEASURED 2026-10-02] On the three MLODs of the Rule 12 in-game test (2026-10-01, DayZDiag 1.29.163709), rebuilt byte for byte by the py3d test `test_s7_blender_to_dayz.py` under `scripts/tools/py3d/tests/`, Check A reads UNIFORM_NON_FLIPPED (0 %; 48 of 48 faces agree) on all three: the correct export, the mirrored one and the inside-out one. Their signed volumes are −0.1086, −0.1086 and +0.1086. The same model built with the det=+1 recipe of the giant infected build (dayz-characters, `references/character-rigging.md`, section 6), and the correct export with every face reversed, read UNIFORM_FLIPPED (0 of 48 agree) at −0.1086 and +0.1086. Two variants of the correct export show what a label or a LOD-wide sum misses: with one of its four boxes reversed and that box's normals negated it still reads UNIFORM_NON_FLIPPED with a negative sum (−0.0822), while that box alone reads +0.0132 (linking faces only through edges two faces share isolates it; joining through every welded edge merges it with a touching box into one shell of +0.0066, and reversing that shell moves the inversion onto the healthy box); with every normal turned to `dot = −0.25` from its face it reads 0 % with 0 of 48 faces agreeing.

   *(Corrected 2026-10-02 against Rule 12, measured in game 2026-10-01. This item called ~100 % UNIFORM_FLIPPED the "EXPECTED state in DayZ (left-handed) after export from Blender (right-handed Z-up)" ("Handedness shift inverts cross product", "No action needed", severity NOTE) and read ~0 % UNIFORM_NON_FLIPPED as "either no handedness transform or normals realigned post-transform". The Crate_Wooden measurement stands; calling its state the expected one does not.)*

2. **Check B — edge-pair topology (MOST RELIABLE).** Two manifold faces sharing an edge must traverse it in opposite directions. If `face1` traverses `(A→B)` and `face2` also traverses `(A→B)` ⇒ one of the two is flipped. Coordinate-system-agnostic. Independent of modeler's intent. **Best tool for detecting mixed winding post-flip.**

3. **Check C — comparison vs a reference model.** Match faces between target and a reference of close geometry by centroid proximity, compare winding-derived normals. The reference must be an MLOD py3d can read: vanilla models on `P:\` are binarized ODOL (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`), which py3d cannot read and the audit rejects. A debinarized vanilla model keeps the ODOL winding sign, so invert the comparison's sign for it ("MLOD to ODOL is a winding-sign boundary" in `winding-absolute-check.md`). Only applicable when such a reference exists.

4. **Direct in-game test.** Rebuild PBO → test server → inspect visual + collision + actions + ballistic. It is the final filter and the only 100% definitive one. When all previous checks say "OK", test in-game anyway.

5. **In-game spawn is non-negotiable.** Offline `.p3d` gates (py3d reload, per-LOD digest, normal budget, resolved vs 65,535, winding parity, indices, degenerate faces, Geometry byte-identical to a p3d that does spawn) **do not authorize spawn**. Never declare a p3d "ready for spawn" by those checks; in-game spawn is mandatory gate. Complements point 4: offline "OK" is not "spawns".
   - **Case (LFHeli HH-60G V8, verified 2026-07-20):** passed those gates — normals 24,404<32,768, resolved 46,905<65,535, winding 100%, Geometry LOD byte-identical to a p3d that DOES spawn — and yet `Won't simulate, it has no geometry`. The "normal budget" theory (that the visual LOD's 24,404 normals, under the 32,768 normal budget, still caused the failure) was REFUTED: with normals reduced to 5,506 it still failed. V8 is a negative capacity control, not a refutation of `binarize`.
   - **Measured cause (2026-07-29, same model):** that message is same defect as `Too many vertices` — engine aborts when loading MLOD, before constructing physics; a valid Geometry LOD does not exonerate. HH-60G cliff: **46,133 resolved triples** (46,133 loads, 46,134 does not; 25 in-game verdicts, zero false ones) recorded in the binarize vertex budget reference of the dayz-vehicles skill (its invariants 24 and 27). The 46,905 of V8 are above that cliff; `RESOLVED_LIMIT = 65535` is a false friend. **Run `binarize` before touching geometry** (three-state verdict: PASS / CAPACITY_FAIL / OTHER_FAIL). CAPACITY_FAIL → do not go in-game to "fix" Geometry; OTHER_FAIL → do not touch geometry. Visual LOD serialization hypothesis (corner order / TAGG / normal pool, "open RCA" on 2026-07-20) was closed as capacity nine days later; do not reopen as primary suspicion or treat count as irrelevant. If `binarize` yields PASS and game still reports no-geometry, other axes remain and in-game spawn is judge.
   - **Reusable bisection:** N test-classnames in 1 PBO, each with a p3d-variant (LODs swapped via py3d). filePatching does NOT reload `.p3d` binaries; one restart tests N variants. Each classname needs its CfgModels entry inheriting skeleton+crew-bones from actual model. 2026-07-20 origin: without that entry, a config with Crew `proxyPos` bones caused `CreateObjectEx` to crash server (minidump in the spawn call) instead of returning spawn_failed. Orthogonal to the render sign question ("Render-sign A/B" below). Cross-ref: the dayz-vehicles skill (get-in/spawn), `dayz-model-pipeline` (`.p3d` export).

## Known traps (lessons learned)

- **A whole-model winding flip applied twice** returns the model to its original state. Write a backup before a flip (for example `.p3d.bak_pre_winding_flip`); if that backup exists, the flip was applied at least once. No flip script ships with this skill: the operation is `face.vertices.reverse()` on every face through py3d.
- **Negating the whole `lod.facenormals` pool to "renegate" normals** was based on a misunderstanding of the pool and is deprecated. If it was applied, the pool normals are wrongly negated; revert by negating them again.
- **Crate_Wooden has mixed winding in Visual LOD** (38.6% bad edges in Check B, 2026-04-25) but **DayZ tolerates it in render** (verified in-game: visual / bullets / cursor / collision OK). Collision LODs (Geometry/LandContact/ViewGeo/FireGeo) are internally consistent. Treat a Check B reading like this as a preventive signal, even though the engine tolerated it in this case; where py3d's `validate()` reports edges traversed the same way, the audit prints `WARN_WINDING_EDGE_INCOHERENT` as a WARNING. Do not re-flip this model unless a concrete in-game symptom appears.
- **Measured:** setting `face.flags |= 0x20000` did not produce two-sided rendering; the faces
  remained see-through in-game. The route confirmed to work is double-sided geometry. The reason is
  now pinned: `binarize.exe` discards the MLOD per-face `flags` field entirely. Three MLODs differing
  ONLY in `face.flags` (`0`, `0x00000020`, `0x00020000`) binarize to a byte-identical model, while a
  moved point and a cleared texture on the same faces each change it (round-trip 2026-08-24). The
  `0x20000` vs `0x00000020` dispute is moot: no face-flag value reaches the game.

## From Check B to fix: isolate minority group and flip it ENTIRELY (winding; stored normals as Check A reads them)

Verified method (GunRacks T1/T2/T3 2026-08-28: 156 inverted faces across 11 parts of three
delivered models, seen in game as planks with inverted normals):

1. **Isolate**: weld points by position (5 decimals), split visual LOD into connected
   components (excluding faces from `proxy:*` selections), and within each component run
   orientation flood-fill with Check B rule (two manifold faces traversing
   shared edge in SAME direction are opposite). Then count the component's parity
   conflicts: two-face edges whose faces ended in the same group although they traverse the
   edge the same way, or in opposite groups although they traverse it opposite ways. A
   component with no conflict yields ONE group when healthy and two when broken, and **the
   minority one is the inverted one** — reference is part's own majority, never an absolute
   sign convention. A component with a conflict, or one that splits evenly, has no minority
   group: where a conflicted fill splits follows the order of the fill. Inspect it with the
   visibility battery of item 2; its edges traversed the same way mark where to look.
   [OFFLINE MEASURED 2026-10-02] The SUB_BRZ co-driver door's LOD 1.0 (healthy, verified in
   game: Check A, `MIXED`) has one edge traversed the same way; with it, the fill splits a
   2,235-face component 2,121 + 114 with 7 conflicts, and over 41 other orders of the faces the
   minority ran from 6 to 246 faces, never none; with it cut, no conflict and no minority. With
   a 30-face patch of that component's paint reversed in memory, the fill returned 144 faces
   (the patch and the 114). Cutting every edge traversed the same way, keeping cut those with
   the same piece on both sides and filling again returned exactly that patch, behind 22 cut
   edges, and exactly the 29 damaged faces of an annulus around a healthy face, but four intact
   faces and none of the 29 when the damaged annulus took in a face of the door's one edge
   traversed the same way: no fill decides such a component. The three GunRacks MLODs of the record above have no conflict:
   their minority groups are the 156 faces their fix reversed, and two of them also hold two
   1 + 1 splits each.
   *(Corrected 2026-10-02: this item read "A healthy component yields ONE group; a broken one
   yields two, and the minority one is the inverted one", with no conflict count.)*
2. **Severity by visibility, not by count**: render with id-buffer and screen culling,
   with sign CALIBRATED against population (majority of a model looking good in-game
   must come out front-facing; same lesson as centroid-check above). Minority group
   visible from outside = defect reported by players; interior groups (shelf
   edges) = same fix, lower urgency. Signed volume does NOT decide orientation on open
   sheets. **When discarding "residual", measure in PIXELS of visible backface, not in faces** —
   "few faces" can be a strip of hundreds of pixels (measured: 1 face, 636 px); and
   "identical to shipped" does NOT exonerate: shipped asset can carry defect from origin.
   Real legitimate residual: front-dominant faces with minor slit backfaces
   (healthy pattern measured: 4335 px front / 59 back).
3. **Read the group's stored normals, then fix it**: before touching the group, read each of
   its faces with Check A, `dot(n_face, average of its corner normals)` with both vectors
   normalized, where `n_face` is the face's vector area: the sum of
   `cross(v[j] − v[0], v[j+1] − v[0])` over its fan triangles. On a triangle or a planar
   convex quad it points like Check A's `n_winding`; on a non-planar or non-convex quad the
   first three corners can point the other way, and which three they are changes with the
   reversal, while the vector area turns exactly. [OFFLINE MEASURED 2026-10-02] A planar dart
   quad whose reflex corner sat at index 1 after `reverse()`, and a twisted quad reversed by
   `v[:1] + reversed(v[1:])`, sent the first-three reading to the wrong branch in both states
   below; the vector area sent all four right. The branches below are written for a part
   whose normals agree with its winding (rows 1-2 of the Check A table). Decide the row of the
   group's part (welded component, then material, as in Check A's `MIXED`) first, from its
   faces outside the group, with the table and its direction test, never from the normals
   alone: a Rule 12 part whose normals were all turned reads like the older convention. A part
   with no face outside the group, or whose other faces read MIXED, has no row: inspect. Bring
   the part to Rule 12 with its row's fix (the third row: keep the winding, negate the normals),
   run step 1 again (a fix that reverses faces can repair the group with them), and read the
   group it finds as written. A part kept in the older convention on purpose, checked in game,
   is read against it: there the two branches swap, ≤ −0.5 meaning winding and normals turned
   together and ≥ +0.5 the winding alone. [OFFLINE MEASURED 2026-10-02] On a 30-face patch of
   the SUB_BRZ door's paint (a 1,926-face part, 98.5 % below −0.5), damaged in memory, every
   face read −1.000 with winding and normals reversed and +1.000 with the winding alone; the
   branches as written left 90 of 90 corners against the undamaged normals both times, while
   bringing the part to Rule 12 first, or reading it against its kept convention, restored 30
   of 30 (to the part converted, or as it was). On a flat Rule 12 box with
   one face reversed and every normal turned, the other five faces read UNIFORM_FLIPPED with
   their cross product toward the box's centre (the third row): that face read against them
   was reversed only and left 24 of 24 corners against the undamaged normals, with Check B
   clean, while the box brought to Rule 12 first came back corner for corner. With that face a
   part of its own, reversed with its normals or alone (rows 2 and 4), its row's fix restored
   the box, and reversing the old group as well took Check B to 4.
   Once every face of the group has a reading, invert the vertex order of every face of the
   group (`v[:1] + reversed(v[1:])`), and per face:
   - **Normals agree with the inverted winding** (reading ≥ +0.5: they turned along with it;
     second row of the Check A table): **negate stored normals of those corners in the same
     pass** — UNLESS pipeline recalculates normals in a subsequent step. This is the GunRacks
     case: there each minority group had its winding AND its stored normals reversed against
     its neighbours', and the fixers of T1/T2 and of the second pass refused to save unless 0
     flipped faces had summed stored normals against the new winding (2026-08-28).
     A fixer that only inverts vertices (as the first GunRacks fixer did) is correct ONLY
     because its pipeline recalculated normals afterwards; copying that mechanic to a pipeline
     without recalculation leaves face visible but shaded inside out (second lost cycle).
   - **Normals disagree with the inverted winding** (reading ≤ −0.5: only the winding was
     reversed, and the normals still point like the neighbours'; fourth row): **keep them**;
     the new vertex order alone makes them agree. [OFFLINE MEASURED 2026-10-02] On a Visual
     LOD made of one Rule 12 unit box, with one face reversed and its normals untouched,
     negating them as well left 5 of 6 faces agreeing (83.3 %, in py3d's absolute check and in
     Check A), while keeping them restored 6 of 6, corner for corner the undamaged model; both
     left 0 edges traversed the same way by both faces. The same held with smoothed normals
     (one pool entry per point, shared by three faces) and for a two-face group with one face
     in each state: 83.3 % after negating both, 100 % after deciding face by face.
   - A face that reads between −0.5 and +0.5 (normals near its plane, where the sign is noise
     and a change of 1e-15 picks the other branch), or that has a corner on the other side of
     it or within 0.1 of its plane (`|dot| < 0.1` against `n_face`: an average can hide one
     such corner, as three agreeing corners and one at 1e-15 average to 0.9487), has no
     reading: inspect it, never infer its normals from the rest of the group. One face with no
     reading stops the whole group, before any face is inverted. [OFFLINE MEASURED 2026-10-02]
     16 of the 114 faces of the door's split (the fill of step 1 without its conflict count)
     have no reading (glass: a corner on the other side of 13 of them, within 0.1 of 3);
     stopping the group leaves the healthy door as it was, while fixing the other 98 alone
     takes Check B from 1 to 20 edges traversed the same way, and every face reversed with the
     98 negated, to 7. It stops real groups too: a
     30-face patch of the door's cabin plastic (99.5 % agreeing), damaged both ways, has one
     face at ±0.392, and the other 29 read the right branch (29 of 30 restored with that face
     set aside).

   Safe mechanics with global POOL: if `normal_index` of the corners to negate are exclusive
   to them, negate in place; if any is shared with a corner whose normal you keep (a face
   outside the group, or a face of the group that keeps its normals), add negated normal as
   new pool entry (32768 budget) and reindex only those corners.

   Close on the whole LOD, not on the group: Check B finds no edge traversed the same way by
   both faces, and every corner normal points along its face's vector area by the same corner
   margin (`dot ≥ 0.1`), or against it (`dot ≤ −0.1`) on a part kept in the older convention
   on purpose (step 3), where most corners fail `dot ≥ 0.1` by construction. A corner that
   fails is inspected, never negated on this reading
   alone: a corner normal smoothed across a sharp fold can point against one of its faces
   with every face wound right. py3d's absolute check reads one corner per face and the
   group's reading sees only the group, so neither sees corners spoiled outside it.
   [OFFLINE MEASURED 2026-10-02] On the smoothed box, with the reversed face's normals negated
   in place on entries its four neighbours share, this step repaired that face with four pool
   copies and left 8 corners of the neighbours pointing outward; py3d read 100 % with no
   winding finding (each neighbour's first corner was intact), while the corner check found
   the 8 and Check A read 33.3 %. A flat tetrahedron wound coherently inward, with
   area-weighted corner normals, fails the corner check at 6 of its 12 corners. On the healthy
   SUB_BRZ door's LOD 1.0, `dot ≥ 0.1` alone fails 26,576 of 35,766 corners, 25,934 of them on
   faces reading ≤ −0.5 and 100 on faces reading ≥ +0.5; read against the face on its 11
   parts that read UNIFORM_FLIPPED (95 % of their faces or more below −0.5), as if all were
   kept, 441. After the paint patch of step 3 was fixed down the wrong branch, the first count
   fell by 90 (to 26,486) and the second rose by 90 (to 531). The GunRacks MLODs read 0, 112
   and 239 both ways (no part reads UNIFORM_FLIPPED), and the smoothed box 8. That label does
   not fix every corner: a strip of 20 quads with the normals of 19 turned reads 95 % with 4
   of its 80 corners at `dot ≥ 0.1`.

   *(Corrected 2026-10-02: this item read "**Coupled fix**: invert vertex order
   (`v[:1] + reversed(v[1:])`) **and negate stored normals of those corners in the same
   pass** — UNLESS pipeline recalculates normals in a subsequent step." for every minority
   group, and its pool rule read "if `normal_index` of faces to flip are exclusive to them,
   negate in place; if any is shared with a face not touched, add negated normal as new pool
   entry". That fits a group whose normals turned with its winding, as in GunRacks; on a
   group whose winding alone was reversed it turns right normals wrong (the 83.3 % above).
   The section title read "isolate minority group and flip it ENTIRELY (winding + stored
   normals)".)*
4. **Artist defect RECURS**: measured identical across three consecutive deliveries of
   same model (16/08, 18/08, 19/08) — lives in working file, re-exporting does not cure it.
   Check is run on EVERY delivery reintegration, not only initial import; and
   fixer is anchored fail-closed (expected component centers + exact face count)
   so a differently re-exported breakdown aborts rather than flipping wrong things.
5. **Inverted faces WITHOUT topological minority** (edges/chamfers not sharing manifold
   edges with their part — point 1 flood-fill cannot see them): operational criterion is
   **back-dominance across a battery of views covering entire sphere** — per face, pixels
   won in z-buffer as backface ≥8 and ≥4× those won as front. Second GunRacks round
   (same day): 17 more faces like this, with strips up to 636 px, which first pass discarded
   as residual. Two measured pitfalls when trying to arbitrate by geometry instead of
   visibility: positional gate ("near ymax ⇒ exterior is +Y") errs on hanging
   faces (soffits, shelf bottoms), and bidirectional raycast cannot resolve ~1 mm sheet
   sandwiches (epsilon hit against twin skin in both directions). And verify the
   battery itself: in typical yaw/pitch projection of these rasterizers positive pitch
   LOWERS camera — a "top view" looking from below leaves roof un-audited
   (measured: sought roof defect did not exist, but original battery could not
   know). Closing loop: complete post-fix re-render with 0 back-dominant faces and
   none new.


## Render-sign A/B and source-profile limits

Edge-pair coherence and cross-product-versus-stored-normal ratios test internal consistency;
they do not by themselves predict which side the engine will render. Normals and winding can
be mutually coherent while both use the wrong sign for the target pipeline.

When the absolute sign remains uncertain, generate an all-flipped variant by reversing every
**visual** face, excluding proxy triangles because their winding encodes the proxy frame.
Binarize the candidate and variant, then run an in-game A/B. Before spending that cycle,
measure both derived outputs with the same census and require the results to differ; equal
results make the A/B a null experiment. Binarize does not normalize per-face winding: it turns
the sign at the MLOD to ODOL boundary ("MLOD to ODOL is a winding-sign boundary" in
`winding-absolute-check.md`), so a flipped variant stays distinct after binarizing.

A pre-binarize dot census can be a cheap predictor only inside a calibrated source profile.
Exclude near-zero dots, do not compare ratios across vanilla ODOL, converted MLOD, and raw
DCC MLOD, and do not generalize a generic-DCC flip rule to a vehicle profile with a different
measured source transform. After adopting a flip, recalibrate every expected fraction in the
assembler's gates. The in-game A/B remains the absolute render verdict.
