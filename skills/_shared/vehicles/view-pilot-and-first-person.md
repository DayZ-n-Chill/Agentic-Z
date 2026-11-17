# View Pilot LOD and the first-person view

What a seated player actually sees: the res 1100 View Pilot LOD, the proxies it references, trimming it safely, and two traps of an offline first-person viewer.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- For a flat colour in a config texture slot vanilla uses a procedural texture instead of a file, for example `#(argb,8,8,3)color(0.521569,0.427451,0.054902,1.0,co)` on a truck door (`P:\DZ\vehicles\wheeled\config.cpp:18183`).
- The View Pilot LOD of a vanilla car sits inside its binarized model (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`), which py3d cannot read, so no LOD content was measured here.

## Seated-view geometry lives in the View Pilot LOD (added 2026-08-19, SUB_BRZ v1.2)

**Seated-view geometry lives in the View Pilot LOD (invariant, added 2026-08-19, SUB_BRZ v1.2):**
A car with a View Pilot LOD (resolution 1100) renders THAT copy of the geometry for seated
occupants, not LOD0. Any geometry/UV/selection patch that must be visible from the driver seat
(screen UV remaps, marker quads, interior fixes) has to be applied to BOTH res 0 and res 1100 —
patching only LOD0 looks fine from outside and unchanged from the seat, which reads as "the fix did
nothing". Seat-only geometry (1PP gap closures) goes in res 1100 alone (SP-469). Also from the same
session: a tiny 8×8 DXT PAA is invalid (mip chain below 4 px → engine renders the grey fallback);
for flat-color config slots use a procedural `#(argb,8,8,3)color(r,g,b,1,CO)` instead of a file.

## An offline viewer for the user to judge: two traps that make it lie (SP-248, added 2026-08-15; SUB_BRZ first person)

Both were caught by the user, not by any gate.
- **What 1PP draws is the 1100 of each part PLUS every proxy that 1100 REFERENCES.** "Does this
  chunk file have a 1100?" is the wrong question: a proxy that ships only `res=0` is still instanced
  by the parent's ViewPilot and falls back to its own LOD0. The SUB_BRZ shell's `res=1100` lists
  **11 proxies including all four body chunks**; excluding them hid the roll cage from the very
  viewer built to have the user point at it. Read the parent's 1100 proxy list, then per part pick
  `1100` if present else the finest visual — the same rule the engine uses — and never hardcode the
  resolution, because a part grows a 1100 the moment you cut something from it.
- **DayZ model space is left-handed; Three.js and a naive numpy raycaster are right-handed.** Feed
  raw coordinates and the car renders MIRRORED — driver on the wrong side — which invalidates every
  left/right judgement the user is about to make. Negate display X **and** swap one pair of triangle
  vertices so the winding survives; keep ids, bboxes and any ray metric in true model space, since
  the `.p3d` edit reads those. Gate it with an asymmetric fact that must hold on screen (here: the
  centreline must project to the RIGHT of the driver's eye, `side > 0`, or the build aborts) — per
  the reference-frame rule, an orientation you did not assert is an orientation you got wrong.

## The View Pilot LOD (res 1100) is a curated view (SP-249, added 2026-08-15; SUB_BRZ s52, root-caused)

One car shipped both halves of
this hole at once, and the user found both by eye: a roll-cage bar and a headliner crossing the road
view in first person, and 73 faces of body sheet silently absent from 1PP while present in the very
same model's LOD0. Three lessons, each with the measurement that proves it:

- **What the engine draws in 1PP = the main's res-1100 PLUS every proxy that 1100 references**, each
  contributing its own res-1100 when it has one and its finest visual LOD otherwise. "Does this chunk
  file have a 1100?" is the wrong question — SUB_BRZ's shell 1100 lists 11 proxies including all four
  body chunks, which ship only `res=0` and are therefore drawn whole. Corollary for hiding something
  from first person only: give that part its own res-1100 minus the geometry. A part with only a
  visual LOD is drawn entire the moment the parent's ViewPilot references it.
- **A driver-visibility TRIM must run against the complete assembled car — attachments included.**
  The 73 missing faces were deleted by an occlusion classifier whose rule was "drop every face no
  seated eye sees front-facing", run over a scene built from shell + interior only
  (`c2_export_pilot_json.py:11-12`, verified). With the doors absent, the door-aperture sheet was
  reachable from the seat and read as back-facing, so it was trimmed — the exact strip the user later
  reported as "missing where the body should meet the door, same on both sides". That file's own
  comment records the same bug caught once before ("without it the classifier flags rear lights as
  removable") and fixed by adding ONE more occluder. One occluder short is the whole failure mode.
  Same trap bites offline viewers: a 1PP viewer built without the chunks hid the roll cage from the
  very screen built to have the user point at it.
- **Cabin materials inside BODY chunks are an import misclassification, and that is what puts junk in
  front of the driver.** 269 `brz_cab_metal` faces in `brz_chunk_01` and 18 `brz_cab_head` in
  `brz_chunk_02`; the ViewPilot only made them visible. Confine material families to their artifacts
  and check on PRESENCE, not on visibility — a leak outside the driver's cone today is a leak in his
  cone after the next pose change.

**The gate this produced** (`rip_viewpilot_content_gate.py`, schema rip_artifact_gate.v1) runs
three checks — STRUCTURAL (faces of a declared structural selection in the visual LOD but not in the
1100, keyed by rounded coordinates so it survives AddonBuilder reordering), OCCLUSION (driver-eye ray
fan over the truly-drawn 1PP scene against a per-car deny list) and CONTAINMENT (material family →
allowed artifacts, longest prefix wins so one deliberate exception does not weaken its family).
Calibrated red-then-green on the real artifact: FAIL with 73/269/18 on the pre-fix build, PASS on the
shipped one. Two habits it enforced on its own author, both worth copying: the first deny list was
too broad (it banned a material the driver legitimately sees overhead, and the gate said so at
10.9% of sight lines), and the deliberate shell-side console screen had to be DECLARED rather than
have the rule loosened.

**Why nothing caught it for weeks:** every gate in that suite treated the 1100 as a budget or as
presence — perf_budget counts its faces (and already encoded the proxy-LOD rule at
`rip_perf_budget_gate.py:230-243`, used only for counting), coverage is presence-only ("Nothing
here has an opinion about geometry"), lod_semantics classifies the SOURCE, and the one driver-eye ray
gate was scoped to a single defect. No gate compared a model's 1100 against its own LOD0. When a LOD
is hand-edited outside the builder — this one is proxy-only in `rip_p3_structural.py` and was
cloned by hand — it has no owner and no gate, which is exactly where silent cuts live.

**A decimated LOD can keep every texture and material path and still render wrong: collapsed UVs.** [EXACT] On LFQuad3 the far LODs lost the body texture and the quad looked different up close, while the texture/material path census was clean; only a per-texture UV-AREA census found it - LODs 2-4 carried body faces with UV area 0 across the board (LOD2: body1 1.827/1.827, body3 1.706/1.706, body2 2.618/2.650, metal 880/880) and LODs 5-6 cited only `metal_co` (measured in game, DayZ 1.30.164014 Exp). A ViewPilot (res-1100) derived from a decimated LOD inherits the defect. Action: when a vehicle looks different from afar or seated, census UV area per texture on every visual LOD and on the 1100/1200 before touching textures or materials; fix by UV transfer from the intact LOD, then re-census.
