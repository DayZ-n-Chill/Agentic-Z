# Rip-imported panels have an open rim

Why a door, hood or tailgate taken from a game rip shows a see-through edge when it opens, what does not close it, and the gate that proves a real cap.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The vanilla control for a closed door volume is the sedan door model, `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d`. It is a binarized ODOL, which py3d cannot read, so the free edge length of 0 quoted for vanilla was not measured again here.

## A rip-imported panel is two parallel skins with an open rim; a vanilla panel is a closed volume (SP-247, added 2026-08-15; SUB_BRZ doors, corrected the same day)

Any door, hood, tailgate or flap coming out of a game rip is a pair of surfaces — outer skin and
inner card — that are never joined at the edge. The source game never shows that edge, so it was
never modelled; every DayZ door OPENS, so every imported door shows it. This is the same finding as
**SP-198**, measured a week earlier on the same car (leading-edge cap 25 cm² against the ~710 cm² a
real cap needs, 77 mm of thickness available) — and the fact that SP-247 was written without
reading it is itself the lesson: **before authoring a fix, grep this pack for the defect, not just
for the car.**

- **Count a free edge over ALL faces of the LOD, not within the material.** An edge the skin shares
  with glass or trim is covered, not open; skirting it pokes through the neighbour. Counting
  within-material inflates the census and aims the fix at edges that were never exposed.

- **⚠ REFUTED — do NOT close the rim with an extruded skirt, and do NOT calibrate on the edge-on
  silhouette.** The first version of this entry canonized both, on the strength of an edge-on render
  going 15.0% → 25.4% of frame against a vanilla control at 26.8%. The user's eye falsified it the
  same day: the edge was still see-through in game, plus two new defects. Two mechanisms, both
  measured afterwards, and either one alone is fatal:
  1. **An extrusion is a flange, not a cap.** Welding a band to the rim closes that edge and opens
     a new one at the band's inner boundary. Measured on the shipped door: true free edge went
     **4455 → 5036 mm**. The operation moved the hole inward; it never closed it.
  2. **The extruded vertices inherited the rim vertex's UV, so every quad has 3D area and ZERO UV
     area** — 235 of 235 quads measured at 0.00000 UV/3D against 0.18 for the skin beside them. The
     faces draw (same pixel count cull ON and OFF), which is exactly why a solid-colour offline
     render scored them as closed, while the engine samples a degenerate mapping and the player
     reads smeared garbage. A skirt that lands anywhere near glass reads as an artifact ON the
     glass: 39 quads within 5 cm of a pane, closest 6.1 mm.
  The silhouette percentage was measuring the patch, not the defect — the exact failure the
  corollary below warns about, committed in the bullet above it.

- **The rim has to be AUTHORED as a cap, on the vertical leading and trailing edges only.** Weld
  skin edge to card edge with its own UV strip (or a dedicated opaque edge material); do not sweep
  the whole free perimeter, because most of it is not exposed — measured on SUB_BRZ, only 31.5% of
  an automatic perimeter skirt landed on the two edges that were actually the complaint, while 17.4%
  (663 cm²) landed on the window top and became a new texture defect.

- **RE-IMPORTING DOES NOT FIX THIS — measured twice.** SP-193 found all six visual factory groups
  already present face-for-face in the shipped proxy (100% centroid match ≤1 mm), and the pipeline's
  own `build_detachable_doors` output measures **684 mm** of free leading edge against the live
  door's 743 and vanilla's **0**. The open sandwich is in the source. Re-assembly reproduces it.

- **Gate: a TEXTURED render plus an in-game capture with the panel OPEN, at the angle of the
  complaint.** Never the silhouette percentage, and never a solid-colour render — both are blind to
  the UV failure that decides whether the fix is visible at all.

- **Corollary on gates (same family as SP-202).** "56 of 63 quads face the edge", "cap 25→40 cm²"
  and "silhouette 15.0→25.4%" all improved while the defect was untouched. A metric that improves
  without the symptom moving is measuring the fix, not the defect — go back to the artifact of the
  complaint.

- **Stale reference, not threshold (LL-275).** If three visible improvements make the metric monotonically worse (here `5.2` -> `3.4` -> `0.5 mm` toward negative), the reference is stale — do not negotiate the threshold. Review what it measures against: the exterior rail must sit on the sheet edge, the interior rail correctly rises to the glass; qualifying the interior against the sheet demands it not do its job.
