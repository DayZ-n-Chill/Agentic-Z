# Visual metrics: what can be asserted from a screenshot

When a pose complaint is a perspective artifact, where a HUD marker ray must be anchored, and how to validate a visual metric on a control before trusting it.

> Status: field notes measured on third-party mods and tutorials, each named in its entry (LFHeli OH-1, LFHeli B-4, SUB_BRZ, LFQuad). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo (a 1.30 build). A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\` unless the text says so: Grep for the symbol before relying on the number. Tags such as SP-130 or LL-090 are the notes' own lesson numbers, and R22, R31 or R35 are the author's process rules. Paths such as `<vehicle-import>\...`, `SUB_BRZ_dev\...`, `AI/10_Projects/...` or `30_Sessions/...` point into those mods' work folders and the author's notes, which are not part of this repo; a file name in Spanish there is the name of such a file. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

Nothing in this file is repealed: these are active lessons, ordered by topic and not by date.

## Vanilla anchors checked on `P:\`

- The third-person vehicle camera `DayZPlayerCamera3rdPersonVehicle` is declared at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:18`.
- It reads `GetTransportCameraOffset` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:49`.
- The default `GetTransportCameraOffset` returns `"0 1.3 0"` at `P:\scripts\3_game\vehicles\transport.c:657`.

---
## An in-game GEOMETRIC POSE complaint can be a PERSPECTIVE artifact - measure the DEPLOYED ODOL before applying any offset (SP-076, added 2026-07-20)

When the user reports "piece X sits N cm off / tilted" on an imported model (rotor vs its housing ring, wheel vs arch, part vs socket), do NOT author a corrective offset/rotation from the capture:

1. **Measure the DEPLOYED artifact, not the source**: debinarize the deployed ODOL (an external ODOL→MLOD converter, not distributed with this pack) and measure the piece against its geometric reference in engine frame - circle-fit (least-squares) of the ring/arch rim, plane-fit (PCA) of a blade/wheel disc, bbox of the socket. Compare piece center / disc normal against the fitted reference.
2. **If the measurement says centered (offset ~mm, tilt ~0 deg), the complaint is PERSPECTIVE**: a ring/aperture with depth along its axis projects obliquely, so a geometrically centered piece LOOKS off-center from an angle - and the apparent offset direction changes with camera angle. Confirm by reproducing the illusion: flat-color render (piece magenta / hull grey) from the user's capture angle vs an orthographic front-on render.
3. **Apply an offset ONLY if the deployed-artifact measurement demands it.** An eyeballed offset on an already-centered model is a REGRESSION (it moves what was right) and burns an in-game cycle to discover it.

Measured case (LFHeli OH-1 round 3, AMENDED same day): user reported tail rotor "10 cm low" + interior "10 cm high, pokes through the canopy". First pass measured global bboxes and called it all perspective - WRONG on two counts: (a) "interior inside the glass" by global bbox missed a REAL 7.25 cm LOCAL protrusion through the canopy roof (per-cell interior-maxY vs glass-surface-Y grid found it; the user's eye was right); (b) the ring fit gave 9.7 mm misreported as 0.9 mm (units slip). CAVEAT the rule accordingly: bbox-vs-bbox NEVER proves containment - protrusion is LOCAL, measure per-cell surface-vs-surface before declaring a pose complaint perceptual. Complements the feel rule (subjective feel -> player data; measurable pose -> deployed-artifact measurement). Origin: LFHeli_dev/reviews/2026-07-20-LA-medicion-pose-fina.md.

## HUD reticle/marker: anchor the ray at the CAMERA, never at the vehicle (SP-365, added 2026-08-07, LFHeli B-4)

A direction reticle drawn by projecting vehicle_origin + GetDirection()*D reads laterally skewed
against the airframe from any 3PP camera sitting off the symmetry plane: at D=300 the world point
projects ~0.2 deg off the vanishing point while the nearby nose projects ~7 deg off (parallax) -
the reticle appears left/right of the hull even though the world point is exactly on axis.
Camera-anchored is the flight-director pattern and kills the parallax for every camera (3PP
orbited, 1PP): nose = GetGame().GetCurrentCameraPosition() + veh.GetDirection() * D, then
GetGame().GetScreenPos(nose), keep the projZ>0 gate. Verified in-game fix path (LFHeli
LFHeliHUD.c 2026-08-07); the previous bone-anchored origin was a no-op built on a misattributed
probe (see next paragraph).

Two measurement traps that produced that dead fix, worth one line each:
- A stable camMS reading across two boots is NOT proof of a systematic engine offset when the
  probe is a one-shot: it can be the fingerprint of WHEN the one-shot fires (same approach walk,
  same inherited camera yaw). Adjudicate camera geometry from the vanilla camera code
  (DayZPlayerCamera3rdPersonVehicle pivots at vehicle origin + GetTransportCameraOffset, default
  0 1.3 0; both opened on `P:\`, see the anchors above) before hypothesizing an offset.
- Selection membership can be PHANTOM: points in a named selection with zero faces referencing
  them (LFHeli glass carried 357 such points on one side). Any per-side point count over a
  selection must count only face-referenced points or the asymmetry measurement lies.

## Diagnose before re-authoring, and validate every visual metric on an in-game-verified control (SP-193, added 2026-08-07, SUB_BRZ E-1/E-2)

SUB_BRZ was one session away from re-assembling both doors from the raw rip, on
the premise that the s42-cut mesh was rotten (five winding passes, 74.7% orphan
verts). Measured first: all six visual factory groups were ALREADY present face
for face in the shipped proxy - skin 2043, card 3344, handle 1176, speaker 18,
wing mirror 4721, mirror base 1174, every one at 100% centroid match <=1 mm. The
re-assembly would have reproduced identical geometry and fixed nothing.

Day-0 check before any re-import/re-assembly of a ripped part:

1. **Face-level completeness, matched by CENTROID** (invariant to vertex order
   and to winding, so it measures presence and never orientation). Point-level
   presence is not enough: a cut can keep every vertex and still drop faces.
2. **Gaps: exact point-to-triangle, never centroid-to-centroid.** The "missing"
   door jamb read 17.2 mm median by centroids and 0.7 mm by exact distance
   (p95 7.1 mm, max 16.2 mm, ZERO faces beyond 30 mm). It was not a hole; adding
   it would have z-fought skin that is already there. A large triangle's centroid
   sits far from a small one while the surfaces touch.

**Offline in-game visibility oracle** (this is what pays for itself - the same
question had cost five in-game cycles):

- A face is DRAWN when its MLOD normal points AWAY from the camera. This is
  SP-191's rule stated per-camera; calibrate it, do not assume it.
- Occlusion counts only DRAWN opaque triangles. A culled face cannot occlude, so
  a plain ray test overstates occlusion badly (mirror glass: 0/315 "visible" with
  raw rays, 238/315 once culling is applied to the occluders).
- **Every run re-validates on a piece confirmed visible in game** and declares
  itself VOID otherwise. Two metrics did exactly that in this session and were
  discarded rather than reported. A visual metric with no self-check is not
  evidence.
- **Judge a part only from cameras that can physically see it.** The mirror glass
  scores 0% from abeam and from the front three-quarter - correct, a rear-facing
  mirror is not visible from in front - and 75.6% from the rear three-quarter.
  A badly chosen camera condemns healthy geometry.
- To inspect a seam, raster the view with the culling rule and colour the PART
  apart from the BODY; both are the same material and one colour per material
  hides the very seam under inspection. Blender's viewport culling is a shading
  flag and has misled this project before - use the calibrated rule.

**A symmetric piece cannot vote on a sign or mirror fit.** Fitting the
blend->DayZ transform, the X-sign discrimination test scored 5.5% for BOTH signs
on a body panel and read as green while measuring nothing: the panel is
mirror-symmetric about x=0, so flipping X maps it onto itself. Report each
control's SELF-MIRROR score and make symmetric pieces ABSTAIN explicitly. Here
only the steering wheel could witness (23.6% vs 0.0%), and it settled that the
pipeline transform is a REFLECTION (det=-1), confirming SP-191/LL-236. Corollary:
never take a part's side from its NAME - adjudicate it against an asymmetric
piece whose in-game position is already measured.

**A flat placeholder _co reads in game as a MISSING part.** brz_mirror_co.paa is
a 16x16 DXT1, 307 bytes, whose AVGC and MAXC taggs are the SAME value
(RGB 38,40,44) - proof of a single near-black colour. The glass geometry,
material and winding were all healthy and it still read as "the mirror has no
glass". Check the PAA taggs (AVGC == MAXC means flat) before hypothesising
geometry; an unswatched piece is a texture bug wearing a geometry costume.

**A defect can survive N winding passes by never entering the adjudicated set.**
The mirror was 315/315 ENCLOSED in the BVH verdict - a category the fixer is told
to skip - and separately excluded from the component census by material. When a
defect outlives several passes, first check whether its faces are even in the set
those passes adjudicate; rim/enclosed are blind spots, not clean bills of health.

Toolkit, parametrised and reusable: `<vehicle-import>\work\s47_doors\` - p12 face
completeness, p18 exact surface gap, p17/p20 self-validating visibility oracle,
p21 culling-correct seam raster, p7/p8 transform fit with abstention.
