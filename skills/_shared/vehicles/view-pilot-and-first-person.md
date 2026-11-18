# View Pilot LOD and the first-person view

What a seated player actually sees: the res 1100 View Pilot LOD, the proxies it references, trimming it safely, and two traps of an offline first-person viewer.

> Status: third-party mod behaviour, not vanilla. The measurements were taken on the mod vehicles named in each entry (TestCoupe, TestQuad3) and are not yet checked on `P:\`, because the View Pilot LOD of a vanilla car sits inside a binarized model. A citation written with its full `P:\` path was opened on the vanilla data.

## Vanilla anchors checked on `P:\`

- For a flat colour in a config texture slot vanilla uses a procedural texture instead of a file, for example `#(argb,8,8,3)color(0.521569,0.427451,0.054902,1.0,co)` on a truck door (`P:\DZ\vehicles\wheeled\config.cpp:18183`).
- The View Pilot LOD of a vanilla car sits inside its binarized model (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`), which py3d cannot read, so no LOD content was measured on it.

## Seated-view geometry lives in the View Pilot LOD (added 2026-08-19, TestCoupe v1.2)

A car with a View Pilot LOD (resolution 1100) renders THAT copy of the geometry for seated
occupants, not LOD0. Any geometry/UV/selection patch that must be visible from the driver seat
(screen UV remaps, marker quads, interior fixes) has to be applied to BOTH res 0 and res 1100 —
patching only LOD0 looks fine from outside and unchanged from the seat, which reads as "the fix did
nothing". Seat-only geometry (first-person gap closures) goes in res 1100 alone.

Two texture facts measured on the same car: a tiny 8×8 DXT PAA is invalid (mip chain below 4 px →
the engine renders the grey fallback); for flat-colour config slots use a procedural
`#(argb,8,8,3)color(r,g,b,1,CO)` instead of a file.

## An offline first-person viewer: two traps that make it lie (added 2026-08-15, TestCoupe)

No automated gate caught either trap; both were found by eye on the rendered view.

- **The viewer must draw what the engine draws: the 1100 of each part PLUS every proxy that 1100
  REFERENCES** (the rule is in the next section). Excluding the proxies that ship only `res=0` hid the
  roll cage from the very viewer built to judge it. Read the parent's 1100 proxy list, then per part pick
  `1100` if present else the finest visual, and never hardcode the resolution, because a part grows a
  1100 the moment you cut something from it.
- **DayZ model space is left-handed; Three.js and a naive numpy raycaster are right-handed.** Feed
  raw coordinates and the car renders MIRRORED — driver on the wrong side — which invalidates every
  left/right judgement made on the picture. Negate display X **and** swap one pair of triangle
  vertices so the winding survives; keep ids, bboxes and any ray metric in true model space, since
  the `.p3d` edit reads those. Gate it with an asymmetric fact that must hold on screen (here: the
  centreline must project to the RIGHT of the driver's eye, `side > 0`, or the build aborts). An
  orientation you did not assert is an orientation you got wrong.

## The View Pilot LOD (res 1100) is a curated view (added 2026-08-15, TestCoupe, root-caused)

One car shipped both halves of this hole at once, and both were found by eye: a roll-cage bar and a
headliner crossing the road view in first person, and 73 faces of body sheet silently absent from
first person while present in the very same model's LOD0. Three lessons, each with the measurement
that proves it:

- **What the engine draws in first person = the main model's res-1100 PLUS every proxy that 1100
  references**, each contributing its own res-1100 when it has one and its finest visual LOD
  otherwise. "Does this chunk file have a 1100?" is the wrong question — TestCoupe's shell 1100 lists
  11 proxies including all four body chunks, which ship only `res=0` and are therefore drawn whole.
  Corollary for hiding something from first person only: give that part its own res-1100 minus the
  geometry. A part with only a visual LOD is drawn entire the moment the parent's View Pilot
  references it.
- **A driver-visibility TRIM must run against the complete assembled car — attachments included.**
  The 73 missing faces were deleted by an occlusion classifier whose rule was "drop every face no
  seated eye sees front-facing", run over a scene built from shell + interior only. With the doors
  absent, the door-aperture sheet was reachable from the seat and read as back-facing, so it was
  trimmed — a missing strip where the body meets the door, the same on both sides. The same
  classifier had earlier flagged the rear lights as removable until one more occluder was added.
  One occluder short is the whole failure mode.
- **Cabin materials inside BODY chunks are an import misclassification, and that is what puts junk in
  front of the driver.** 269 `brz_cab_metal` faces in `brz_chunk_01` and 18 `brz_cab_head` in
  `brz_chunk_02`; the View Pilot only made them visible. Confine material families to their artifacts
  and check on PRESENCE, not on visibility — a leak outside the driver's cone today is a leak in the
  cone after the next pose change.

**The gate this produced** runs three checks — STRUCTURAL (faces of a declared structural selection
in the visual LOD but not in the 1100, keyed by rounded coordinates so it survives AddonBuilder
reordering), OCCLUSION (driver-eye ray fan over the truly-drawn first-person scene against a per-car
deny list) and CONTAINMENT (material family → allowed artifacts, longest prefix wins so one
deliberate exception does not weaken its family). Calibrated red-then-green on the real artifact:
FAIL with 73/269/18 on the pre-fix build, PASS on the shipped one. Two habits worth copying: the
first deny list was too broad (it banned a material the driver legitimately sees overhead, and the
gate said so at 10.9% of sight lines), and the deliberate shell-side console screen had to be
DECLARED rather than have the rule loosened.

**Why nothing caught it for weeks:** every gate treated the 1100 as a budget or as presence — a
performance budget counts its faces, coverage checks only that it exists, LOD semantics classifies
the source, and the one driver-eye ray gate was scoped to a single defect. No gate compared a
model's 1100 against its own LOD0. When a LOD is hand-edited outside the builder (this one was
proxy-only in the structural builder and was cloned by hand) it has no owner and no gate, which is
exactly where silent cuts live.

**A decimated LOD can keep every texture and material path and still render wrong: collapsed UVs.** On TestQuad3 the far LODs lost the body texture and the quad looked different up close, while the texture/material path census was clean; only a per-texture UV-AREA census found it - LODs 2-4 carried body faces with UV area 0 across the board (LOD2: body1 1.827/1.827, body3 1.706/1.706, body2 2.618/2.650, metal 880/880) and LODs 5-6 cited only `metal_co` (measured in game, DayZ 1.30.164014 Exp). A View Pilot (res-1100) derived from a decimated LOD inherits the defect. Action: when a vehicle looks different from afar or seated, census UV area per texture on every visual LOD and on the 1100/1200 before touching textures or materials; fix by UV transfer from the intact LOD, then re-census.
