# Doors: open edge, caps, and detachables that are not doors

Why an imported door shows a missing edge when it opens, how to measure that edge against a vanilla door, how a script closes it, and what a hood or a trunk needs that a door rig gets wrong.

> Status: the measurements below were taken on two imported cars (a sports coupe and a sedan, third-party mod content, not vanilla) and are not yet checked on `P:\`. A citation written with its full `P:\` path was opened on the vanilla data. The see-through rim of an imported panel and the face-for-face completeness check are in `rip-panel-open-rim.md`.

## Vanilla anchors checked on `P:\`

- The vanilla door used as the control is `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d`. It is a binarized ODOL (version 56), so the free-edge lengths quoted below were measured on a debinarized copy; they cannot be read from the file on `P:\` directly.
- Vanilla ships the hood and the trunk of the same car as their own models next to it: `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanhood.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedantrunk.p3d`.

## How this file is ordered

The door-edge rules come first, in the order they build on each other: the missing caps, the metric that measures them, then the script that closes them. The hood and trunk rules follow. The reference tables of `README.md` say when to read this file.

---

## An imported door has NO end caps, and a shut door cannot show you

A ripped car door arrives as two open shells - outer skin and inner card - with
NOTHING closing the leading and trailing edges. The source game never shows that
edge, so it was never modelled. Every DayZ door OPENS, so every imported door
shows it. There are no 2D doors: assume the caps are missing until measured.

Measured on a sports coupe import, both doors, at the two z extremes of the door-local frame:

| end | faces facing +/-z | cap area | expected (height x thickness) |
|---|---|---|---|
| leading | 125 | 25 cm2 | ~710 cm2 |
| trailing | 62 | 17 cm2 | ~710 cm2 |

3.5% and 2.4% of the area a real cap needs, and what remains is paint
fold-over at the skin edge, not a band. Door thickness available at both ends:
77 mm.

**Day-0 check for any vehicle with opening doors** - slice the door at its two
extremes along its long axis, sum the area of faces whose geometric normal runs
along that axis, and compare against `height x thickness`. Under ~30% means the
caps are missing. This check only detects absence; do not use the area figure as
a pass gate (see the next section for the metric that is).

**Why this hides for entire sessions, and the general lesson:** with the door
SHUT the body covers that edge, so every closed-door measurement passes. On the
coupe, five winding passes, a paint-normals fix and a black-normals fix, plus an
offline visibility oracle over 20 cameras, a jamb gap measured point-to-triangle
and a culling-correct seam raster were all run on the shut door, all green, while the
defect sat in the open-door configuration nobody measured. Generalise it:
**measure a part in the state where it is EXPOSED, not in its default state.**
A green metric on the hidden configuration is not evidence about the visible one.

Corollary for the in-game checklist: a door verdict is only worth collecting with
the door OPEN, and the screenshot must show it open. Captures taken with the door
shut settle nothing.

Corollary for the fix: the caps are new geometry, not a flip. Normals and winding
passes cannot create a surface that was never there - and if a door edge reads as
"nothing at all" rather than "wrong colour" or "wrong shading", suspect absence
before orientation.

## A missing door edge is measured by FREE EDGE LENGTH against a vanilla control, and three "obvious" fixes do not close it

Knowing that the caps are missing is not actionable until you know **what to measure it
with and what does not fix it**. The method below is reproducible on any car with
detachable doors.

**The control is one model** (the whole car is not needed): debinarize
`P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d` to MLOD with an ODOL to
MLOD converter. Agentic-Z ships none; it is the same external backend that
`scripts/tools/dayz-odol-strict` expects.

**The correct metric is free edge length per long axis end**, in a band at each end of the
long axis, across ALL render LODs + 1100. Measured with a 6% band:

| end | vanilla | sports coupe import | reading |
|---|---|---|---|
| front (A pillar) | **0 mm** | 673 mm | defect |
| rear (B pillar) | 612 mm | 627 mm | see the next section: this edge fails too |

Two things that this corrects at once:

1. **Having free edge on door perimeter is NORMAL.** The entire perimeter is a closed
   loop of ~4.4 m (outer skin + glass) and vanilla also has it. A gate measuring "total
   free edge" gives red on a healthy door.
2. **The area gate (`cap >= 70% of height x thickness`) is poorly calibrated** and must not be used: it assumes
   constant thickness across full height and that full height is sheet metal. On a frameless door (any
   coupe) the upper half is glass, and the "thickness" reported by a band
   probe is the CURVATURE of the bend, not a gap. That gate demanded ~710 cm2 of cap where
   real geometry admits ~640 and only along part of the height.

**Three fixes ruled out WITH MEASUREMENT — do not repeat them:**

- **Double-siding front band**: render with a calibrated culling rule, before and
  after, **0 px difference**. Edge see-through is not a single-sided face
  problem.
- **Bent lip (hem) copying vanilla**: a free edge is not closed by displacing it; the lip
  moves the edge, does not eliminate it. Additionally clearance against the jamb is insufficient: at 2 mm depth there
  are already bodywork vertices inside the volume (door-jamb gap measured at 0.7 mm).
- **Bridge outer skin <-> inner panel**: the two edges do NOT correspond. Only 6 of 13
  height strips have both edges present, with gaps from 121 to 218 mm. An automatic
  bridge produces a twisted wall.

**The structural cause, which is what needs checking on the next car:** outer skin and
inner panel are **separate meshes that do not touch**. On the coupe the inner panel
(plastic and black trim materials) ends 108 mm before the front edge, where the outer skin
(paint material) does reach. Between both there is nothing. That is why "two rings to bridge" do not exist:
two edges from different parts exist, separated by 11 cm.

**Planning consequence:** request the defect capture WITH THE DOOR OPEN before starting —
with the door closed every measurement gives green, and without a capture one cannot
distinguish "I see through" from "edge looks ugly", which lead to different fixes.

Four probes cover the method: free edge per LOD (the gate metric), control against
candidate on normalized axes, correspondence of the two edges, and an A/B/C render
(current with culling, without culling, and simulated fix).

## The door edge IS CLOSED BY SCRIPT with a MEASURED depth band — and both edges fail

Two refinements of the metric above, the first confirmed in game:

1. **The REAR edge also fails.** "Vanilla has 612 mm free there, so it is normal"
   is a bad inference: that vanilla has free edge does not imply it remains EXPOSED.
   In game both edges show the defect. Measured at full perimeter (8% z-band, not
   6%): vanilla front **0 mm** / rear ~502 mm; import 743/598 mm — the anomalous delta is at
   BOTH ends.
2. **Closing the edge does not need manual modelling**: a perimetric band added by script
   achieves vanilla parity. A band of constant 5 mm depth fails because of DEPTH (5 mm in a gap of
   ~77 mm), not orientation — its quads do render (cull ON == cull OFF probe).

**The recipe that works** (both doors, visual LODs + 1100):

- **TRUE free edge**: count each edge's use across ALL faces of the LOD and keep
  those of the skin with use==1. Counting only within the skin material marks as
  "free" edges actually covered by glass or trim, and the band crosses them.
- **Measured depth per edge vertex**: raycast inward along thickness axis; depth = 90%
  of gap to first wall, clamp [8, 60] mm; 60 mm where there is no wall within 150 mm. Real
  gap varies 10→135 mm — any constant is wrong across half the perimeter.
- **Watertight band**: ONE extruded point per welded edge vertex, shared between neighboring
  quads (extruding per-edge with different depths leaves slits).
- **Winding**: stored normal pointing OUTSIDE the edge, opposite geometric winding (the
  convention measured on 100% of the render LOD faces of both doors). "Outside the edge" = component
  of (midpoint − skin centroid) perpendicular to edge, with thickness axis at 0.
- **Parity gates, always against control** on SAME metric: edge render (the import went
  from 15.0% → 25.4% drawn surface vs 26.8% vanilla) and long-axis ray sweep
  (65.7% clean rays vs 68.8% vanilla — door ended up MORE closed than control). An
  absolute threshold without control fails healthy doors: vanilla gives 68.8% "open" in naive
  sweep because most rays pass outside the silhouette legitimately.
- **Diagnosis before sizing**: render the edge in TWO scenes — car ASSEMBLED and
  CLOSED (visible regression from outside?) and ISOLATED door (= open door, where the complaint
  lives). The defect only exists in the second; measuring only one answers a different question.

Request the defect capture WITH THE DOOR OPEN before sizing.

---

## Detachables that are NOT doors: hood and trunk

**Evidence level: MEASURED offline on a sedan import. The rig extension is not verified
in game.** Numbers below are model geometry, not engine
behavior; what is stated here is WHERE to look, not a tested recipe.

A detachables rig written for doors bakes two assumptions that are **false** for hood and
trunk, and neither of them screams: one aborts with a message blaming the axis, and the other anchors
the hinge one meter from where it belongs, in green.

1. **The hinge edge is not always the front one.** A door hinges on its front edge
   (-Z), hence rigs band over `z.min()`. But a **hood hinges on its REAR edge**
   (the windshield one, +Z) and a **trunk on its FRONT edge** (-Z). Measured: hood
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
   **The free-edge gate validates its OWN arithmetic, and the opening SENSE is calibrated in game**: an offline gate that re-derives the rotation and checks a directional property never consults the engine convention. Measured in game on 1.30: the two GREEN rows were exactly the two pieces opening DOWNWARD (`open_free_edge_lift_m` +1.4021 hood, +0.8393 trunk, gate green), and on a VERTICAL hinge the criterion is inapplicable - a car door does not rise (its side roles read 0.0000/0.0000/-0.0506/-0.0506). Offline still decides axis, role face set and the per-side sign split; calibrate the opening SENSE with ONE in-game observation per car, recorded in the profile: with signs split per side, one observation fixes all six (all six reversed = convention; mixed = bad role split). Declare N/A where the rule does not apply instead of competing with a number in the same table.

4. **Axis gate does NOT validate role's part set, and it is easy to believe it does.** The axis
   fits on ONE part (the one declaring hinge). Putting a part in the role that does not touch — a
   jamb, a bodywork panel, a headlight that actually belongs to bumper — does not move axis by a
   single degree: **hinge contrast remains green and opening contrast too**. A separate
   gate is needed on the property: maximum distance of any role face to axis against a declared
   radius, plus face count against census. Without it, bad grouping reaches game.

5. **Before writing a `+x`/`-x` property rule, measure whether faces exist ON the x=0 plane.** A
   centroid rule discards them from both sides and those faces disappear from the car without anyone
   noticing. On the sedan 0 of 18 candidate parts came out, but that is a measured datum, not a format
   guarantee. And for an entire part no special rule is needed if selector defaults to
   "all".

6. **A hood usually brings glass and a trunk does not.** If structural code requires body AND
   glass to bound its boxes, trunk aborts and hood passes — but classifying headlight
   glass as "window", with its damage zone and glass penetration material on top.
   Glass box must be optional, and body/glass classification a datum, not a name
   prefix.

7. **Item mass is not inherited from door.** A global `geometry_mass_kg` assigns a hood
   the kilograms of a door.

Points 3 and 4 are exactly the kind of defect an offline gate does not find,
because the gate is measuring something else.
