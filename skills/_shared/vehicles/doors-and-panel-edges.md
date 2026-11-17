# Doors: open edge, caps, and detachables that are not doors

Why an imported door shows a missing edge when it opens, how to measure that edge against a vanilla door, how a script closes it, and what a hood or a trunk needs that a door rig gets wrong.

> Status: field notes measured on third-party mods (SUB_BRZ, sub_wrxsti_04), each named in its entry. Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Tags such as SP-205 or LL-464 are the notes' own lesson numbers, and `[EXACT]`, `[DESIGN]` and `[CLAIM-...]` are the notes' own evidence labels. Paths such as `<vehicle-import>\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. `odol_to_mlod.py` is the external ODOL to MLOD converter the notes used; it is not part of this repo. The see-through rim of a ripped panel (SP-247) and the face-for-face completeness check (SP-193) are in `rip-panel-open-rim.md`.

## Vanilla anchors checked on `P:\`

- The vanilla door control the notes extract is `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d`. It is a binarized ODOL (version 56, header read 2026-11-17), so the free-edge lengths quoted below were measured by the notes' author on a debinarized copy and were not measured again here.
- Vanilla ships the hood and the trunk of the same car as their own models next to it: `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanhood.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedantrunk.p3d`.

## How these lessons are ordered

These lessons were split out of the source skill body on 2026-08-15. The reference
tables of `skills/dayz-vehicles/SKILL.md` say when to read this file.
Nothing in this file is repealed: these are active lessons, ordered by topic
instead of date.

---

## An imported door has NO end caps, and a shut door cannot show you (SP-198, added 2026-08-07, SUB_BRZ E-1)

A ripped car door arrives as two open shells - outer skin and inner card - with
NOTHING closing the leading and trailing edges. The source game never shows that
edge, so it was never modelled. Every DayZ door OPENS, so every imported door
shows it. There are no 2D doors: assume the caps are missing until measured.

SUB_BRZ, both doors, measured at the two z extremes of the door-local frame:

| end | faces facing +/-z | cap area | expected (height x thickness) |
|---|---|---|---|
| leading | 125 | 25 cm2 | ~710 cm2 |
| trailing | 62 | 17 cm2 | ~710 cm2 |

3.5% and 2.4% of the area a real cap needs, and what remains is `brz_paint`
fold-over at the skin edge, not a band. Door thickness available at both ends:
77 mm.

**Day-0 check for any vehicle with opening doors** - slice the door at its two
extremes along its long axis, sum the area of faces whose geometric normal runs
along that axis, and compare against `height x thickness`. Under ~30% means the
caps are missing. `<vehicle-import>\work\s43_fixes\s49_probe_ends.py` is the probe.

**Why this hides for entire sessions, and the general lesson:** with the door
SHUT the body covers that edge, so every closed-door measurement passes. SUB_BRZ
spent five winding passes, a paint-normals fix and a black-normals fix, plus an
offline visibility oracle over 20 cameras, a jamb gap measured point-to-triangle
and a culling-correct seam raster - all on the shut door, all green, while the
defect sat in the open-door configuration nobody measured. Generalise it:
**measure a part in the state where it is EXPOSED, not in its default state.**
A green metric on the hidden configuration is not evidence about the visible one.

Corollary for the in-game checklist: a door verdict is only worth collecting with
the door OPEN, and the screenshot must show it open. Two rounds of SUB_BRZ
captures were taken shut and settled nothing.

Corollary for the fix: the caps are new geometry, not a flip. Normals and winding
passes cannot create a surface that was never there - and if a door edge reads as
"nothing at all" rather than "wrong colour" or "wrong shading", suspect absence
before orientation.

## A missing door edge is measured by FREE EDGE LENGTH against vanilla control, and three "obvious" fixes do not close it (SP-202, added 2026-08-07, SUB_BRZ E-1; refines SP-198)

> ⚠ PARTIALLY SUPERSEDED by SP-245 (next section): rear edge DOES fail, and
> script closure DOES work with measured depth. The metric and the 3 ruled-out fixes remain
> active.

SP-198 states that an imported door has no edge caps. What is actionable is missing: **what it is measured with
and what does not fix it**. An entire probing session on SUB_BRZ, reproducible on any car in
the pipeline with detachable doors.

**The control is extracted in one command** (the whole car is not needed):

```
python odol_to_mlod.py "DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d" ctrl.p3d
```

**The correct metric is free edge length per long axis end**, in a 6% band,
across ALL render LODs + 1100. Measured:

| end | vanilla | SUB_BRZ | reading |
|---|---|---|---|
| front (A pillar) | **0 mm** | 673 mm | defect |
| rear (B pillar) | 612 mm | 627 mm | **normal, do not touch** |

Two things that this corrects at once:

1. **Having free edge on door perimeter is NORMAL.** The entire perimeter is a closed
   loop of ~4.4 m (outer skin + glass) and vanilla also has it. Only the FRONT edge
   is anomalous, because it is the only one remaining in view upon opening. A gate measuring "total
   free edge" gives red on a healthy door.
2. **The area gate (`cap >= 70% of height x thickness`) is poorly calibrated** and must not be used: assumes
   constant thickness across full height and that full height is sheet metal. On a frameless door (BRZ,
   GT86, and any rip coupe) upper half is glass, and the "thickness" reported by a band
   probe is the CURVATURE of the bend, not a gap. That gate demanded ~710 cm2 of cap where
   real geometry admits ~640 and only along part of the height.

**Three fixes ruled out WITH MEASUREMENT — do not repeat them:**

- **Double-siding front band**: render with pipeline's calibrated culling rule, before and
  after, **0 px difference**. Edge see-through is not a single-sided face
  problem.
- **Bent lip (hem) copying vanilla**: a free edge is not closed by displacing it; the lip
  moves the edge, does not eliminate it. Additionally clearance against the jamb is insufficient: at 2 mm depth there
  are already bodywork vertices inside the volume (door-jamb gap measured at 0.7 mm).
- **Bridge outer skin <-> inner panel**: the two edges do NOT correspond. Only 6 of 13
  height strips have both edges present, with gaps from 121 to 218 mm. An automatic
  bridge produces a twisted wall.

**The structural cause, which is what needs checking on next car:** outer skin and
inner panel are **separate meshes that do not touch**. In SUB_BRZ the inner panel
(`brz_cab_plastic`, `brz_black`) ends 108 mm before the front edge, where outer skin
(`brz_paint`) does reach. Between both there is nothing. That is why "two rings to bridge" do not exist:
two edges from different parts exist, separated by 11 cm.

**Planning consequence:** closing the edge is **manual modeling** (authoring the edge
wall in Blender), not script surgery. Budget it as such from the start and request the
defect capture WITH THE DOOR OPEN before starting — with the door closed every measurement gives
green (SP-198) and without capture one cannot distinguish "I see through" from "edge looks ugly", leading
to different fixes.

Reusable probes in `<vehicle-import>\work\s50_doorcaps\`: `s50_probe_freeedge.py` (gate
metric, per LOD), `s50_compare_control.py` (control vs candidate, normalized axes),
`s50_probe_bridge.py` (correspondence of the two edges), `s50_render_front.py` (A/B/C render:
current with culling, without culling, and simulated fix).

## Door edge IS CLOSED VIA SCRIPT with a MEASURED depth band — and both edges fail (SP-245, added 2026-08-15, SUB_BRZ s52; partially supersedes SP-202)

Two corrections to SP-202, both with measurement and the first confirmed in-game by user:

1. **The REAR edge also fails.** The attribution "vanilla has 612 mm free there → normal,
   do not touch" was a bad inference: that vanilla has free edge does not imply it remains EXPOSED.
   With user present both fail. And measured at full perimeter (8% z-band, not
   6%): vanilla front **0 mm** / rear ~502 mm; rip 743/598 mm — anomalous delta is at
   BOTH ends.
2. **"Closing the edge is manual modeling" is superseded**: a perimetric band via script
   achieves vanilla parity. The 5 mm fix from s51 failed due to DEPTH (5 mm in a gap of
   ~77 mm), not orientation — its quads did render (cull ON == cull OFF probe).

**The recipe that works** (`<vehicle-import>\work\s52_cantos\s52_close_perimeter.py`, both doors,
visual LODs + 1100):

- **TRUE free edge**: count each edge's use across ALL faces of the LOD and keep
  those of the skin with use==1. Counting only within skin material (like s51) marks as
  "free" edges actually covered by glass or trim, and band crosses them.
- **Measured depth per edge vertex**: raycast inward along thickness axis; depth = 90%
  of gap to first wall, clamp [8, 60] mm; 60 mm where there is no wall within 150 mm. Real
  gap varies 10→135 mm — any constant is wrong across half the perimeter.
- **Watertight band**: ONE extruded point per welded edge vertex, shared between neighboring
  quads (extruding per-edge with different depths leaves slits).
- **Winding**: stored normal pointing OUTSIDE the edge, opposite geometric winding (the
  convention 100% measured across render LODs of both doors). "Outside the edge" = component
  of (midpoint − skin centroid) perpendicular to edge, with thickness axis at 0.
- **Parity gates, always against control** on SAME metric: edge render (BRZ went
  from 15.0% → 25.4% drawn surface vs 26.8% vanilla) and long-axis ray sweep
  (65.7% clean rays vs 68.8% vanilla — door ended up MORE closed than control). An
  absolute threshold without control fails healthy doors: vanilla gives 68.8% "open" in naive
  sweep because most rays pass outside the silhouette legitimately.
- **Prior diagnosis that unblocked it**: render edge in TWO scenes — car ASSEMBLED and
  CLOSED (visible regression from outside?) and ISOLATED door (= open door, where complaint
  lives). Defect only exists in second; measuring only one answers a different question.

Requesting defect capture WITH THE DOOR OPEN (SP-202) remains in effect before sizing.

---

## Detachables that are NOT doors: hood and trunk (measured sub_wrxsti_04, 2026-08-07)

**Evidence level: MEASURED offline. Rig extension is NOT implemented nor verified
in-game as of today.** Numbers below are model geometry, not engine
behavior; what is promoted here is WHERE to look, not a tested recipe.

A detachables rig written for doors bakes two assumptions that are **false** for hood and
trunk, and neither of them screams: one aborts with a message blaming the axis, and the other anchors
the hinge one meter from where it belongs, in green.

1. **The hinge edge is not always the front one.** A door hinges on its front edge
   (-Z), hence rigs band over `z.min()`. But a **hood hinges on its REAR edge**
   (the windshield one, +Z) and a **trunk on its FRONT edge** (-Z). Measured on WRX: hood
   hinge **12 mm** from maximum Z of its panel, trunk **4 mm** from minimum. The front
   edge of the hood, which is where a door rig would band, is **1.16 m** from the real
   hinge. The edge must be a declared datum per role, not a constant.

2. **Tilt is measured against its CLASS axis, not always against vertical.** Hood and
   trunk give **89.81 degrees** and **88.84 degrees** with respect to +Y: they blow any verticality
   budget. Their axis is lateral (+X). A "tilt vs Y" gate is not a quality gate for
   them, it is a prohibition.

3. **Sign pitfall, and it is silent.** With lateral axis `axis[1]` is ~0, so
   usual normalization `if axis[1] < 0: axis = -axis` stops being deterministic: sign is
   decided by PCA noise. Opening direction must come from declared angle, and offline
   gate catching an inverted sign is **physical**: the **free edge** (band OPPOSITE to
   hinge) must RISE upon opening. A displacement-by-magnitude gate (`|delta| > threshold`)
   passes green with inverted sign — measures that it moves, not where to.
   **[EXACT] The free-edge gate validates its OWN arithmetic, and the opening SENSE is calibrated in game** (SP-377, added 2026-10-01, WRX STI first flight): an offline gate that re-derives the rotation and checks a directional property never consults the engine convention. Measured in game (DayZ 1.30.164014 Exp, 2026-08-21): the two GREEN rows were exactly the two pieces opening DOWNWARD (`open_free_edge_lift_m` +1.4021 hood, +0.8393 trunk, gate green), and on a VERTICAL hinge the criterion is inapplicable - a car door does not rise (its side roles read 0.0000/0.0000/-0.0506/-0.0506). Offline still decides axis, role face set and the per-side sign split; calibrate the opening SENSE with ONE in-game observation per car, recorded in the profile: with signs split per side, one observation fixes all six (all six reversed = convention; mixed = bad role split). Declare N/A where the rule does not apply instead of competing with a number in the same table.

4. **Axis gate does NOT validate role's part set, and it is easy to believe it does.** The axis
   fits on ONE part (the one declaring hinge). Putting a part in the role that does not touch — a
   jamb, a bodywork panel, a headlight that actually belongs to bumper — does not move axis by a
   single degree: **hinge contrast remains green and opening contrast too**. A separate
   gate is needed on the property: maximum distance of any role face to axis against a declared
   radius, plus face count against census. Without it, bad grouping reaches game.

5. **Before writing a `+x`/`-x` property rule, measure whether faces exist ON the x=0 plane.** A
   centroid rule discards them from both sides and those faces disappear from the car without anyone
   noticing. On WRX 0 of 18 candidate parts came out, but that is a measured datum, not a format
   guarantee. And for an entire part no special rule is needed if selector defaults to
   "all".

6. **A hood usually brings glass and a trunk does not.** If structural code requires body AND
   glass to bound its boxes, trunk aborts and hood passes — but classifying headlight
   glass as "window", with its damage zone and glass penetration material on top.
   Glass box must be optional, and body/glass classification a datum, not a name
   prefix.

7. **Item mass is not inherited from door.** A global `geometry_mass_kg` assigns a hood
   the kilograms of a door.

Origin: `<vehicle-import>\plans\2026-08-07-T6-detachables-rig-extension.md` (T6 of the CHANGE-3 pilot),
probes in session scratchpad. Points 3 and 4 were raised by a blind R22 review on the
plan, not implementation: they are exactly the kind of defect an offline gate does not find
because the gate was measuring something else.
