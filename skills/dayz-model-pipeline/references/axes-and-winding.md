# Axes and winding: Blender to DayZ, collision LODs, glTF and open geometry

The measurements behind the axis conversion and the face winding rules: why the Blender to DayZ map is a reflection, how a collision LOD must be wound, what changes for glTF and OBJ sources, and how to judge orientation on closed and open geometry. Rule numbers (Rule 12, Rule 18) refer to `critical-rules.md`, which states the rules; this file holds the evidence, the history and the special cases.

Everything here was measured on third-party mod models, in game on DayZDiag or offline with py3d. It cannot be checked on `P:\`: vanilla models there are binarized, and winding is a property of the MLOD source. The `/dayz-p3d-audit` references hold the matching checks: `dayz-p3d-audit/references/winding-methodology.md`, `winding-diagnostics.md` and `winding-absolute-check.md`.

Evidence labels: `[EXACT]` is measured in game or read from a file, `[OFFLINE MEASURED]` is measured without the game, `[DESIGN]` is a rule derived from them.

## The rule today, in short

Blender is right handed with Z up; DayZ is left handed with X east, Y up and Z north. Map every point and every normal through `(x,y,z) -> (x,z,y)` (a reflection, det=-1), keep each face's vertex order, and negate every normal. From py3d 1.8.0, `py3d.blender_to_dayz(model)` does exactly that. Winding gates cannot see a mirrored model, so check an asymmetric feature (text, a logo, a one sided part) in game.

## History: the det=+1 recipe was a mirror (formerly Rule 13)
The Blender/FBX recipe changed three times. 2026-07-06: `(x,z,-y)` (det=+1), "a proper rotation, never reverse" — inside-out in game. 2026-09-26: the same map plus reversed faces and negated normals — validated on five working LF_PowerGrid models with offline gates only (collision cross INWARD 100%, visual cross opposite to the mapped source normal 100%), and it is a MIRROR: those models are symmetric, so nobody saw it. 2026-09-22 and 2026-10-01 (in-game test of one chiral model): the map is the det=-1 reflection `(x,z,y)`, faces keep their order, normals are negated — Rule 12. Each step fixed the symptom the previous one left; only an asymmetric model shows the last one.

## A det=+1 map ships a mirrored model, so the Blender to DayZ map needs det=-1 (added 2026-09-22, measured on a motorcycle)

[EXACT] Measured in game (DayZ 1.30.164014 Exp): an exporter that mapped Blender→DayZ with the det=+1 rotation `X = -y` produced a MIRRORED model. Inverting faces and negating normals fixed the inside-out look, but in-game text and logos then read backwards ("92", "ITAJUD"): the shape itself was mirrored, and the mirror was also the real cause of the reversed faces. DayZ is left-handed (X east, Y up, Z north; vehicles face -Z) and Blender right-handed, so conserving shape requires a REFLECTION in the numbers: `X = +y` (det=-1). MLOD convention measured against binarized vanilla: the vertex-order cross points INWARD and the shading normals also point inward; with det=-1 the face order comes out correct on its own, normals get negated, and geometry authored directly in DayZ space (collision boxes) is inverted by the same reflection. Gate: compare your binarized ODOL against the vanilla one with the same reader (tyre tread band, collision boxes) and require readable in-game text. This corrects the earlier glTF import rule in the opposite sense. Confirmed on 2026-10-01 on DayZDiag 1.29.163709 with one chiral model exported three ways (Rule 12), which now uses this map. Exports made with the old det=+1 recipe are mirrored: harmless on symmetric parts, wrong on anything with text, logos or one-sided geometry.

## Collision LOD winding: every face inward per component, never matched to the Visual LOD
When you GENERATE/EDIT a collision LOD (Geometry/Fire/View), run `audit_p3d.py` and Rule 18's
per-component check BEFORE deploying. Rule 18 decides: with its prerequisites met (every
non-proxy face in a `ComponentNN` selection; every component closed and convex; no degenerate
face), every non-proxy face of every component must read INWARD (Rule 12); otherwise the check
is unresolved and confirms nothing. `audit_p3d.py` does not run Rule 18: through py3d
`P3D.validate()` it compares each collision LOD with the Visual LOD and raises
`ERR_WINDING_INVERTED` when both are uniform and opposite: a trigger for Rule 18, not a
verdict, since it also fires on healthy collision LODs under an inside-out Visual LOD or one
meant to be seen from inside (a room). Reverse only the faces that read outward, and set their
stored normals as killer 1's **Fix** says; never reverse a collision LOD to match the Visual
LOD (`dayz-p3d-audit` killer 1 in `references/p3d-killers.md`, and item 7 of the absolute winding
check in `references/winding-absolute-check.md`).
Surface this proactively when the symptom is "no action /
bullets pass". A walk-through does not point at the winding: in game, 2 m boxes whose
collision LODs were wound outward still stopped the player, the same box with no `ComponentNN`
selection let them through, and a 0.49 m `item_small` kit let them through with either winding
(`dayz-p3d-audit` killers 1 and 2, and item 6 of the absolute winding check). *(Corrected 2026-10-02,
measured in game: the symptom list read "walks through / no action / bullets pass".)*
*(Aligned 2026-10-02 with `dayz-p3d-audit` killer 1 and Rule 18: this section was titled
"Collision LOD winding must match the Visual LOD" and opened: "When you GENERATE/EDIT
a collision LOD (Geometry/Fire/View), compare its winding against the Visual LOD of the same
model (centroid method) BEFORE deploying — they must agree in sign (~100% INWARD in DayZ
left-handed). `audit_p3d.py` does NOT validate this (centroid check disabled for false
positives)." That comparison is the relative check `audit_p3d.py` runs, and matching its
sign is the fix killer 1 forbids.)*

## GLB and glTF imports (added 2026-06-11, separated from the FBX/Blender recipe 2026-09-26, aligned with Rule 12 2026-10-03)

A GLB/glTF exported to spec and brought through Blender takes **Rule 12's recipe**: points and
normals through `(x,y,z)->(x,z,y)` (det=-1), every face in its vertex order (proxy triangles
included), and every normal negated — `py3d.blender_to_dayz(model)`. Do **not** reverse the faces.
A glTF read without Blender needs one more step first (last paragraph). Not checked on this path:
a mirrored node (negative determinant, below) arrives in Blender as an object with negative scale;
read that part's winding in the exported MLOD (signed volume per closed shell, with the
`check_dayz_winding.py` script of `/dayz-model-tools`) before trusting it.

**glTF front faces are CCW by spec**, as Blender's are (a node whose global transform has a
negative determinant, a mirrored instance, winds them clockwise: glTF 2.0 §3.7.4
"Instantiation"), and Blender's glTF importer turns Y-up into Z-up with a rotation,
`(x,y,z)->(x,-z,y)` (det=+1; Blender 5.1
`io_scene_gltf2/blender/imp/blender_gltf.py:70-72`), which keeps that order: a GLB brought through
Blender is Blender geometry. The det=-1 map turns its vertex-order cross product INWARD, the MLOD
convention; reversing the faces after it turns the cross product OUTWARD, the case that renders
inside-out (`py3d-direct-generation.md`, "Face Winding Verification"). [EXACT]
Measured in game on two GLB/glTF-origin models:

- an imported rifle (2026-06-11, binarized): pure swap, normals `−S·n` and `REVERSE_WINDING=False`
  rendered with correct textures (the weapon import transform, `skills/_shared/weapons/model-import.md`);
- an imported car (2026-06-24): with its faces reversed after its det=-1 map it rendered
  see-through, and with the glTF order kept it rendered solid (`skills/_shared/vehicles/vehicle-structural-parity.md`,
  under "glTF→DayZ winding: the offline check can be a
  tautology").

A GLB-sourced mesh exported with the det=+1 rotation `(x,z,-y)` can ship with BOTH defects at
once (reproduced on the first build of that rifle, 2026-06-11):

- textures render on the INNER faces (CCW winding kept), and
- the weapon is MIRRORED laterally (the -y flip puts the weapon's right side at -Z; vanilla
  weapons carry it at **+Z** — verified on the BI sample candygun MLOD: `nabojnicestart` +Z).

Both come from the det=+1 map (the section above on det=-1), and Rule 12's det=-1 map removes both. Mirror-detection:
compare one canonical LATERAL point (e.g. `nabojnicestart`) against a vanilla reference — bbox
and audits cannot see a mirror. Weapon attachment proxies (the proxy triangle, its leg directions and
the `proxy:\DZ\...001` naming) are covered in `_shared/models/proxy-frames.md`.

The swap expects Z-up input; a glTF read without Blender is Y-up. Derive its det=-1 map from the
asset's own frame (re-derived per asset, as `import-rule-v4.md` says for weapons). Bake each
node's global transform into its mesh first, and reverse the faces of every instance whose global
transform has a negative determinant: glTF winds those clockwise, so after baking they must be
reversed to run counter-clockwise from the visible side again. Then keep that order through the
det=-1 map: any det=-1 map turns a CCW front face's cross product inward (not measured in game
for a direct read). A ripped game asset in a `.glb` can carry its game's frame rather than the
spec's (the measured rip profile keeps the raw winding with a det=+1 map): the vehicle import
material (`rip-vehicle-import`) decides it from the measured transform and source lineage.

*(Aligned 2026-10-03 with Rule 12. The section opened "This section is **GLB/glTF-only**. It
does **not** override Rule 12's measured FBX/Blender recipe."; its pipeline read "**GLB-only
pipeline (when the lateral-mirror / CCW issues apply):** pure swap `(x,y,z)->(x,z,y)`
(det=-1) + reverse the vertex order of EVERY face in every LOD — except proxy triangles, whose
vertex order encodes the attachment frame (P0/P1/P2) and must NOT be reversed."; and it closed
"Do **not** treat «any GLB/Blender import» as one shared rule with the FBX/Blender recipe in
Rule 12 — Blender-authored FBX follows the det=-1 map with negated normals; GLB keeps its own
path above (not re-tested against the 2026-10-01 in-game test)." The reversal dates from
an early stage of the imported rifle above, when that project's
builds shipped a stray raw MLOD at the PBO root, the file the engine loaded (`skills/_shared/weapons/model-import.md`,
"Test the build the game will run"); its first build that loaded the binarized model,
v12c, kept the vertex order.)*

## Decimate COLLAPSE corner normals

Decimate COLLAPSE can zero or invert `corner_normals`, surfacing as `WARN_WINDING_NORMAL_MISMATCH`.
When a corner normal is about 0 or contrary to the face, fall back to the geometric triangle normal.
This is a documentation note: no generator script applies the fallback.

## Generic DCC visual-winding profile (added 2026-08-31)

Blender/FBX-authored geometry follows Rule 12 instead (det=-1 map, face order kept, normals negated): a
winding-preserving det=+1 transform mirrors the model. A GLB/glTF brought through Blender follows Rule 12
too, and one read directly follows section "GLB/glTF imports". An OBJ is in the frame its exporter wrote.
Exported from Blender with Forward Y / Up Z it keeps Blender's own coordinates
(`blender-headless.md`) and follows Rule 12 as it stands; in any other frame of a right-handed
source with counter-clockwise front faces, derive a det=-1 map from that frame as for a glTF read directly,
keep the face order, negate the normals, and check chirality on an asymmetric feature. [OFFLINE MEASURED
2026-10-03] Blender's default axes write `(x, z, -y)`; from them the map is `(x,y,z)->(x,y,-z)`, which on
the model of Rule 12's in-game test writes the same bytes as Rule 12's export. Another exporter's frame
was not measured in game. Reverse the vertices of every **visual** MLOD face only for a source whose own
lineage was measured to need it: an in-game A/B against the all-visual-faces-flipped variant plus a
chirality check, as the `ai-3d-to-dayz` skill says. Every lineage measured with that reversal under a
det=+1 map started from Blender coordinates, where any det=+1 map mirrors the model: this profile's one
calibration, a helicopter (2026-07-19: an artist's Blender model exported as OBJ, mapped with
`x'=x, y'=z, z'=-y` and judged by which side rendered), an infected character (read mirrored in game:
`skills/_shared/wearables/references/body-rigging.md`, section 6) and the 2026-09-26 recipe (the history
section above). *(Aligned 2026-10-03 with Rule 12, measured in game 2026-10-01: from "An OBJ is in the
frame" to here, this paragraph read "For other raw OBJ imports whose measured axis transform preserves
the source winding, reverse the vertices of every **visual** MLOD face before binarization, and check
chirality on an asymmetric feature.")* *(Aligned 2026-10-03: this sentence read "For other raw OBJ or
glTF imports whose measured axis transform preserves the source winding".)*
Never include proxy triangles: their winding encodes the proxy frame. This is the generic
DCC profile only. Imported vehicles use the vehicle import profile (the `rip-vehicle-import` skill), where
preserve-versus-flip is decided from the measured transform and source lineage.

A pre-binarize census of `dot(cross(v1-v0, v2-v0), mean_stored_normal)` per visual LOD, excluding
`abs(dot) < 1e-9`, reads whether the stored normals agree with the winding, not which side renders. Its
thresholds, at least 95% negative `SOLID` and positive-dominant `INVERTED`, come from this profile's one
calibration, the helicopter pipeline, which stored the normals outward against an inward winding; a Rule 12
export stores both inward. [OFFLINE MEASURED 2026-10-03] On the MLODs of the Rule 12 in-game test, rebuilt
byte for byte by `scripts/tools/py3d/tests/test_s7_blender_to_dayz.py`, the export that rendered solid and read
correctly reads 0% negative, `INVERTED` by those thresholds; the same export with every face reversed
(winding outward: inside-out) and this profile's first recipe, the det=+1 map with reversed faces and outward
normals (a mirror), both read 100% negative, `SOLID`. Read a Rule 12 export with `dayz-p3d-audit`
instead: a healthy single-sided MLOD reads about 100% agreement (item 1 of the absolute winding check in its `references/winding-absolute-check.md`), and
the direction comes from the signed volume by winding of each closed shell, even at 100% agreement, never
from the sum over the LOD: one shell reversed with its normals negated keeps 100% agreement and a negative
sum (Check A in its `references/winding-diagnostics.md`). Open sheets and double-sided parts take the
visibility battery of "From Check B to fix"; isolate a mixed result per part before any bulk fix
(item 2 of the absolute winding check). Do not apply that threshold
to ODOL, to MLOD produced by conversion from ODOL, or as a ratio comparison against a
vanilla model: stored-normal conventions differ by origin. The final gate remains an
in-game A/B of the candidate and an all-visual-faces-flipped variant. That A/B cannot see a mirror, since
both variants share the map: check chirality too. *(Aligned 2026-10-03 with Rule 12 and the census
measured offline: this paragraph opened "Use a pre-binarize census of
`dot(cross(v1-v0, v2-v0), mean_stored_normal)` per visual LOD, excluding `abs(dot) < 1e-9`, as a cheap
predictor. In the calibrated generic-DCC profile, at least 95% negative is `SOLID`, positive-dominant is
`INVERTED`, and an intermediate result requires a per-piece mixed-winding check.")*

## Imported vehicles use their own profile

For an imported vehicle, follow the vehicle import profile (the `rip-vehicle-import` skill and the vehicles pack, `_shared/vehicles/README.md`), not the generic Smart UV and decimation defaults of Path A. That profile is: a measured det=+1 transform; face partition, not decimation; winding preserved, with the minority repaired; UVs by sections. Whether to preserve or flip the winding depends on the profile and the transform (Rule 12); it is not a universal constant. Generic DCC geometry keeps its face order under a det=-1 map (Rule 12, and the generic DCC section above). An A/B test on a synthetic cube measures the collision raycast mechanism, not a universal flip doctrine: measure a real rip before generalizing, and note that a collision A/B is not on the same axis as visual culling. *(Aligned 2026-10-03 with Rule 12: this note used to read "NOT the generic Smart UV / decimation / flip defaults".)*

## Orientation metrics for open geometry (added 2026-08-31)

Before trusting an aggregate orientation metric, translate the model by several metres and
measure again. A changed verdict proves that the metric is not valid for that geometry.
Classify closure before choosing the oracle: signed volume is valid for closed components;
open sheets require a visibility test.

For open geometry, render from a direction battery with and without culling and compare the
nearest surface with the surface that is actually drawn. Count a defect only when the depth
gap exceeds a calibrated distance. A useful report separates `<2 mm`, `2 mm-2 cm`,
`2-10 cm`, and `>10 cm`; a zero-gap pixel count confuses thin sheet thickness with visible
backfaces. Calibrate both green and inverted controls before acting on the result.

A coincident-twin tolerance must be smaller than the thinnest sheet in the model, and the
actual separation must be measured before labelling a pair as intentional double-sided
geometry. Finally, flip a suspect component and remeasure it: if the defect disappears it
was winding; if it moves to the other side, the sheet needs two-sided geometry rather than
another flip.

**Instrument and seal for see-through triage (added 2026-09-24, measured on a motorcycle).** [DESIGN] To see what the game draws, render with Blender Workbench `show_backface_culling` (rasterizes and discards backfaces before depth, like the engine) — use it to locate see-through pixels, not to adjudicate winding signs (`skills/_shared/vehicles/visual-gates-and-winding.md`). Cycles with a transparent backface also skips the coincident twin, and per-face red overlays come out mottled on double layers: neither adjudicates what the player sees. [EXACT] Flipping a two-sided sheet only moves the hole (measured: 313 tank-lip faces flipped, the front lip then vanished from above); the seal that never removes what was visible is an inverted twin carrying its own UVs and normals in the same animation selections. Twins cost vertices — respect the per-model resolved budget (`dayz-p3d-audit` `references/manual-checks.md`), not a fixed 65,535. For a real hole (side views show nothing behind), close the gap and back it with a dark inset sheet. On a model with a ViewPilot, a seal for what only the seat sees, twin or closure, goes in res 1100 alone: in LOD0, closures and twins together drew black slivers seen from outside (the proxies and get-in notes in the vehicles pack). After any mesh fix, compare before/after from the owner's viewpoint, not only the face counts.

## Closed collision-LOD winding (added 2026-08-31)

For a closed collision component, use right-handed signed volume
`sum(dot(v0, cross(v1, v2))) / 6` and calibrate against a known-good vanilla control. The
measured DayZ convention is negative volume. Emit each face so
`cross(v1-v0, v2-v0)` points inward, and store the negated exterior normal. A generator
must measure its new box and fail closed unless the volume is negative.

Do not infer this result from agreement between stored normals and geometric cross products,
and do not treat a generic `py3d.validate()` result as the signed-volume gate. Proxy
triangles and relative winding checks can make that aggregate non-discriminating. Closed
collision volume and open-sheet visibility are separate profiles.
