# Dashboard gauge needles and dials

How to build a working speedometer, tachometer and fuel gauge on a vehicle model: the needle part, the dial frame and its mirror traps, deriving `angle0` and `angle1`, the wiring in `model.cfg`, a fuel panel from scratch, and a complete recipe with an offline gate per step.

> Status: the measurements below were taken on three mod test vehicles (the LFQuad3 quad from 2026-09-03 to 2026-09-07, then the LFQuad2 quad and the SUB_BRZ car), named in each entry; they are mod behaviour, not vanilla, and were not repeated for this file. A citation written with its full `P:\` path was opened on the vanilla data of this repo (a 1.30 build). The table of vanilla cluster animations in trap 5 was read from DayZ 1.29 models with an ODOL reader; the models on `P:\` are ODOL version 56, which this repo cannot parse, so the table is not yet checked on `P:\`. `[ASSUMPTION]` marks a statement that was not measured. Script names such as `assemble_lfquad3.py`, `dial_derive_final.py` or `normal_sign.py`, the folder `_shared_parts\gauge_needles\` and files such as `generated/model.cfg` belong to those vehicles' build folders, which are not part of this repo; the rules they implement are written out below. The OBJ object names `aguja_derecha` and `aguja_izquierda` are the source model's own (Spanish for "right needle" and "left needle"). "Trap N" numbers the eighteen traps of this file; they are not the numbered invariants of the vehicle pack.

Related file in this pack: `animation-sign-and-axis.md` (the general rule for whether a wheel, steering, door or dial animation turns the right way).

## Vanilla anchors checked on `P:\`

- `GetSpeedometer` is native on `Car`: `P:\scripts\3_game\vehicles\car.c:102`.
- `CAR_JUMPOUT_THRESHOLD` is commented as a speed in km/h, and is compared against the speedometer: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:34`.
- `SELECTION_ID_DASHBOARD_LIGHT` is hidden selection 8: `P:\scripts\4_world\entities\vehicles\carscript.c:182`.
- `dashboardMatOn` is the cluster backlight material, registered on the `DashboardOn` selection: `P:\scripts\4_world\entities\vehicles\carscript.c:230`.
- The four vanilla cars of trap 5 are on `P:\` as binarized models, for example `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` (ODOL version 56, header read 2026-11-17).

## What was accepted in game, and what was not broken down

The LFQuad3 dashboard was accepted as good in game on 2026-09-06 with the verdict "dashboard is good now" (build `5ac339d3`). That verdict is global; it was not broken down per gauge. Three things were still not checked one by one: that the fuel needle moves with the tank; that the painted dial does not rotate with the needles (the object's original disc travels in the animated selection; [ASSUMPTION] it stays occluded); and that the rest position lands exactly on the printed zero (measured offline with the gate, not checked in game). LFQuad2 was confirmed in game on 2026-09-07 00:15 (build `77303210b92d63bd`); see the table "Confirmation status".

## The part: `_shared_parts/gauge_needles/`

The shared parts folder `_shared_parts\gauge_needles\` of those builds (not part of this repo) holds `needle_large` and `needle_small`,
each in `.p3d` (to drop in) and `.obj` (to edit), plus their README.

| | length | width | thickness | tris |
|---|---|---|---|---|
| `needle_large` | 0.02596 m | 0.00714 m | 0.00261 m | 182 |
| `needle_small` | 0.01298 m | 0.00357 m | 0.00130 m | 182 |

The small one is the large one at 50 %. Dimensions WITHOUT scaling: if target vehicle
applies uniform scaling, multiply.

**Official dial faces** in `dial_faces/`: `dial_kmh_official.png`
(0-150 km/h), `dial_rpm_official.png` (0-6 x1000, with red from 5 to 6), and
`dial_fuel_official.png` (E / mid / F panel). They replace dials of original ATV, which were printed 0-120
and 0-8, with the latter **counterclockwise** — hence a needle rotating
counterclockwise over it may be correct. **Check the direction in which face
is PRINTED before touching any angle.**

Both are in **canonical pose** — pivot at origin, tip at **+X**, rotation
axis at **+Z** — with `needle_pivot`, `needle_axis`, and `needle_tip` in Memory
LOD. Mounting them is a translation to dial center plus a rotation mapping
+Z to its normal. **The pose IS the reusable part**: a needle saved
with the angle and position its OBJ gave it is useless to another model.

The pivot is the centroid of the **Black** submesh, not the set's: that is the
hub around which it rotates.

**Library status (regenerated 2026-09-07).** `build_needle_library.py`
extracts needle with `canonical_needle` rule (cut by RADIUS, trap
14): 182 tris LOD0 = hub ring 32 quads (64) + 32-gon cap (30) +
hub skirt 32 quads (64) + blade of 2 octagons (12) and 6 sides
(12); selections by radius `hub` (158) and `blade` (24); rear of blade
at z = 0 and whole part with z >= 0 (hub cap sits a hair
in front of blade root). Set of vertices IDENTICAL to what
`canonical_needle` returns on OBJ (measured, 0 missing, 0 extra).
2026-09-03 version came from ANGULAR WIDTH (`THIN_DEG = 5.0`) and
had 86 tris: the two ENTIRE blade octagons (real tip, at
0.880 r_obj) plus 5 of its 6 sides, without cap or hub skirt, and
with blade BEHIND hub plane (z -0.00261..0): incomplete and badly
placed, not a splinter at the tip. Bad is not same as invisible:
mounted as-is on LFQuad2, blade sits +1.89 mm IN FRONT of painted
disk and is visible (depth probe of that session, 2026-09-06);
visibility is decided by `lift` of each dash disk, not part.
LFQuad2 adopts new version in its own batch with its gate; until
then it mounts the old one.

## Trap 1 — the object named "needle" is not a needle

`aguja_derecha` of LFQuad3 OBJ is **105 faces**. Topology measured in
assembler framework (`needle_parts_probe.py`; drawing `needle_parts.png`):

| part | faces | canonical r | z relative to hub |
|---|---|---|---|
| hub: `Black` ring + 32-gon cap | 32 + 1 | <= 0.0029 | 0 |
| hub skirt: 32 `Gauges` quads (closed 360 degree collar) | 32 | 0.0029 .. 0.0036 | -0.0026 .. 0 |
| blade: 2 octagons + 6 lateral `Gauges` quads | 8 | 0.0029 .. 0.02239 | -0.0026 .. -0.0009 |
| disk: 32 `Gauges` quads | 32 | 0.0036 .. 0.02544 | -0.00235 (flat) |

The hub is 33 faces plus 32 skirt, blade 8, disk 32 (skirt was
counted as blade until its angular extent was measured, 2026-09-07).
Saving it whole puts a gauge in the library under a needle's name.

And numbers do not betray it: object box comes out `0.0509 x 0.0509 x 0.0026`,
which seems reasonable until one notices that 0.0509 is exactly the
DIAMETER of the disk. **Drawing the silhouette uncovered it**, not measuring it. The tip of
the blade is at 0.88 of object's r_max; farthest vertex belongs to DISK.

Separation: **cut by radius**, not angular width. `r_obj` = maximum radius
in the plane of entire object; non-Black faces with any vertex at
r > 0.95 * r_obj are DISCARDED, and exactly 32 OBJ faces /
64 tris are REQUIRED (`SystemExit` if not: `canonical_needle` in `assemble_lfquad3.py`).
Canonical z is shifted so rear of blade sits at 0. Angular width
filter (5 degree threshold, "ring 32 + blade 7") is form 1: a blade
triangle glued to pivot covers a wide angle BECAUSE IT IS CLOSE, not
because it is a wedge, leaving 10 tris of splinter at the tip. Invisible in game in
LFQuad3. 2026-09-03 library came from that same rule with ANOTHER
remainder (the two whole octagons and 5 sides, without cap, blade behind
hub; census, above): rule gives different parts depending on where applied, and
none is the needle.

## Trap 2 — dial frame comes out ARBITRARY, and rotation does not fix a mirror

To map a polar texture onto gauge face a pair of
in-plane axes is needed. If extracted with a generic `basis_from_axis(normal)`, the
pair is **any** perpendicular to axis: gauge comes out with arbitrary
roll. What usually happens then is someone corrects by eye with a
`+ math.pi`, and there problem begins.

Real symptom: text read upside down, half turn was added, and it became
**mirrored**. Half a turn is a rotation and cannot undo a
reflection. Mapping was `u <- -b`, `v <- -a`: axis swap PLUS a
negation, which is a reflection. **No angular offset removes it.**

Cross product alone is not enough either. LFQuad3 generator constructed
`u = cross(w, axis)` and claimed that is screen right "when axis
points to observer". On this model that `u` comes out +X and driver's right
is -X: model itself says so, writing `light_left` at x +0.373
and `light_right` at x -0.374 (`memory_lod`, `assemble_lfquad3.py`). That is the
root of mirror that survived three cycles: verification render
mounted its frame with SAME expression, reproduced failure and called it
correct.

**The fix is to anchor, not compensate:**

```python
MODEL_RIGHT = (-1.0, 0.0, 0.0)   # from light_right - light_left
w = normalize(up - axis * dot(up, axis))   # vehicle-up, in plane
u = normalize(cross(w, axis))
if dot(u, MODEL_RIGHT) < 0:
    u = -u
# fatal if the markers disagree with MODEL_RIGHT (memory_lod writes both)
u_uv = uc + k * dot(radial, u)
v_uv = vc - k * dot(radial, w)     # sign is MEASURED; see trap 10
```

`dial_basis` orients `u` against `MODEL_RIGHT`. `memory_lod` throws `SystemExit`
if sign of `light_right - light_left` on x stops matching. Final
mapping is `(uc + k*<radial,u>, vc - k*<radial,w>)`: +U to driver's right,
-V upward because V=0 is TOP edge of image
(`polar_uv`).

> **The sign of V in this snippet is NOT universal.** Here it takes minus
> because in this pipeline V=0 is the top edge of image. With `+` LFQuad3
> art came out **vertically mirrored** two cycles in a row. Trap 10
> gives procedure to certify sign in YOUR pipeline and to distinguish
> a mirror from a rotation.

Without `atan2`: angle only served to recompose what are already the two
point coordinates, and upon recomposing it swapped axes.

**The direction of V is MEASURED in your own pipeline; not inherited from here.** What
was measured on LFQuad3: writing complemented V, atlas
render reproduced EXACTLY the mirroring user reported; with naive
V render came out good and game bad.

> **2026-09-04 qualification.** This paragraph previously stated "because engine
> inverts it when sampling", as if it were an engine fact. It is not: **the
> complement lives in the assembler**. `assemble_lfquad3.py:1971` does
> `uv.append((u, 1.0 - v))` on EVERY UV it takes from OBJ, so V
> ending up in `.p3d` is `1 - v_obj`, and dials only need to be
> consistent with it.
>
> Counter-case on LFQuad2, whose UVs come from an
> Arma 2 MLOD and never pass through that `1-v`: with V as-is
> art comes out upright and readable, and with `1-v` model samples **another region
> of the atlas**, not a mirror. They do not contradict each other: they are different pipelines, and the
> engine only has one convention.
>
> **The operational rule is not a sign, it is a procedure:** the V of the
> dials is written in the SAME direction already used by other model UVs,
> and that direction is found with a **positive control** -- a piece of art
> whose orientation admits no debate (text, a readable sticker),
> rendered with actual `.p3d` UVs. Making a mistake produces either a mirror or
> a translation, both "plausible": without that anchor they are indistinguishable.
>
> The LFQuad3 dash was accepted as good in game on 2026-09-06 ("dashboard
> is good now", build `5ac339d3`): anchored frame, newly converted faces, and
> new fuel needle. It was not broken down per gauge. Still not broken down:
> movement of `fuel`, original disk inside animated selection, and
> exact zero (offline gate). LFQuad2: its frame by cross product WAS
> checked against headlights on 2026-09-06 (`light_left` x +0.3011,
> `light_right` x -0.3131, right = -X; `<u, light_right - light_left>` =
> -0.6142; det +164.81 on both disks): MIRRORED, same root as here, and
> the mirrored-frame finding goes from one observation to two, in different models and pipelines. Negating
> `angle0`/`angle1` on Sep 4 was a self-consistent compensation:
> needles nailed to correct number on a face written backwards. That
> session corrected and deployed it (UVs of 64 wedges rewritten in all three LODs
> with right read from model and fatal guard; det -164.81; `LFQuad2.pbo`
> sha `77303210b92d63bd`). Confirmed in game on 2026-09-07 00:15 (cycle
> with `@CF` + `@VPPAdminTools` + `@SurvivorAnims`): speedometer 0-150
> CLOCKWISE, readable "km/h", red to the RIGHT, needle at 0; tachometer
> 0-6 CLOCKWISE, readable "RPM x1000", red to the right, needle at 0. User
> verdict on that build names three other defects (missing fuel,
> disks outside animated selection, pixelated texture; traps 9
> and 15), none from frame. What discriminates the mirror is measurement against
> headlights.

**Instrument that closes this**: rasterize gauge faces from `.p3d` ALREADY
BUILT with their real UVs, sampling texture with engine's V. That
is what will be seen in game. A synthetic render on an invented disk is
invalid — does not carry UVs written by model. In LFQuad3 that closure is
`dial_gate_final.py`, which takes right from `LIGHT_RIGHT_MINUS_LEFT`.
`dial_render_v5.py` (and its Sep 4 `view_all_fix.png`) mounted frame with
`cross(-axis, up)`, same expression as generator: reproduced failure and
called it correct. Does not count as closure.

**Chirality rule for a NEW part** (measured 2026-09-07, LFQuad2).
LFQuad2 reintroduced the same mirror in its own code when mounting
panel frame: it did `Up = cross(Np, Rp)` and, if Up came out inverted,
flipped Up AND recalculated Rp, which dragged Rp to driver's
left (`<Rp, right> = -1.0000`); caught by a guard, not an eye. The frame
of a new part is PROJECTED from anchored frame (Gram-Schmidt over
part normal), never rebuilt with a cross product nor
flipped by components. CHIRALITY is checked against gauge
frame (`<u_part, anchored right>` > 0), because upon it depends
sign of angle0 = rest - theta. Anchored frame above does come
from a `cross`, because its only degree of freedom is fixed against
measured `MODEL_RIGHT`; new part has no own anchor and inherits it.

## Trap 3 — changing the frame INVALIDATES `angle0`, and also inverts rotation

`angle0` rotates needle **from the angle at which it is modeled**, not to
an absolute one: `angle0 = painted_zero - mesh_angle`, both in same
frame.

Un-mirroring the dial **moves painted zero to another physical location**, so
old `angle0` are no longer valid even if no one touched needle. And since
relation between old and new frame is a **reflection**
(`theta_new = C - theta_old`), direction of rotation also inverts: what
engine moved counterclockwise is now read clockwise.

How it is re-derived without guessing (instrument, below):

1. Measure **painted arc** on atlas (ends of tick ring).
2. Measure **mesh angle** of needle in new frame, from built
   `.p3d`: from pivot to farthest vertex of blade (not object).
3. `angle0 = rest - theta(minValue)` and `angle1 = rest - theta(maxValue)`
   in anchored frame. Gate draws needle over EACH printed value.

Numbers from 2026-09-03 (`C = 443` for speedometer, old 225 -> measured
218, prediction 290.3 against 298) were deduced in mirrored frame: they are
**superseded**. Values in mod accepted as good are in
instrument section and in `generated/model.cfg`.

**Beware of measuring arc by tick ring ends**: there may be entry
and exit ticks beyond last label. On LFQuad3 tachometer
ticks cover 299 degrees and printed scale 240.

**If vehicle top exceeds last printed number**, do not stretch
`maxValue` leaving angles: that makes needle lie throughout entire
travel. Sweep is extended proportionally using unpainted
gap. Example with old ATV art (printed 0-120): 270 degrees is 2.25
per km/h; with top 150 sweep would be 337.5 and the 67.5 extra would fit in the
90 degree gap. With official face (printed 0-150, line fitted to 0-100 and
extrapolated) sweep is 302.8: instrument section. **Printed numbers
remain true at any speed.**

## Trap 4 — axis fallback position silently points to wrong gauge

If code writes a hardcoded position for `<sel>_axis` and then
`apply_needle_axis` recalculates it, that fallback is never tested. When swapping
which needle drives which gauge, fallback was left pointing to the other — and gives no error:
if someday calculation does not find needle, needle rotates on wrong
dial. **A constant only used when something fails must be changed
with the rest.**

Measured case (kmh/rpm swap of 2026-09-04): touched two places and left a
third (needle selection tags in `build_visual`). Result:
`kmh_axis` at x +0.046 and `kmh` selection at x -0.045 — needle rotating
on a pivot on the other side of dashboard. Axis, needle mesh, and
texture change TOGETHER, and hardcoded axis fallback too.

## The wiring contract

1. Geometry in a dedicated named selection (e.g. `kmh`).
2. In Memory LOD, two points: pivot (centroid of needle Black
   cube) and pivot plus normal TOWARDS driver, aligned against a
   fixed reference (`n_pilot` in LFQuad3), named `<selection>_axis`.
3. Bone in skeleton (`skeletonBones[]`), child of dashboard
   (`kmh`/`rpm`/`fuel` of `drivewheel` in LFQuad3). `sections[]` only if
   selection changes texture or material; LFQuad3 needles are not in it.
4. Dial face painted 1.2 mm behind needle (`lift = 0.0012` along
   `ring_n`, which points away from driver) and in front of panel. Entire needle
   in front of panel (z >= 0 in canonical pose; fuel pivot 0.0004 m
   forward). A `lift` of -0.0003 left needles invisible from all
   views.
   - **Two signs per new face, copied from neighbors** (trap 17): winding with
     same `sign(<cross, axis>)` as visible discs, and stored normal with
     `<normal, cross> >= 0` at each vertex. Gate: `normal_sign.py`, 0 marked faces
     and same sign column across all cluster selections.
5. One texture per dial, power of two (padded, not stretched). DEDICATED rvmat
   with flat normal and specular (`#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)` and
   `color(1,0,1,1,SMDI)`, attested in vanilla; LFQuad2 finding). Discs and
   needles OUTSIDE color `hiddenSelections` (`camo1`): otherwise, the
   variant overwrites their texture.
6. In `CfgModels`, the three classes. LFQuad3 values (measured 2026-09-06):

```
class IndicatorSpeed
{
    type = "rotation";
    source = "speed";        // km/h
    selection = "kmh";
    axis = "kmh_axis";
    memory = 1;
    minValue = 0;
    maxValue = 150;
    angle0 = "rad 232.5";
    angle1 = "rad 535.3";
};
class IndicatorRPM
{
    type = "rotation";
    source = "rpm";
    selection = "rpm";
    axis = "rpm_axis";
    memory = 1;
    minValue = 0;
    maxValue = 1;
    angle0 = "rad 213.1";
    angle1 = "rad 456.4";
};
class IndicatorFuel
{
    type = "rotation";
    source = "fuel";
    selection = "fuel";
    axis = "fuel_axis";
    memory = 1;
    minValue = 0;
    maxValue = 1;
    angle0 = "rad -129.1";
    angle1 = "rad -47.6";
};
```

**Every `angle*` takes its unit.** A bare number is read by the engine in
**radians** while the rest of the file is in degrees: `30` ends up being 1718
degrees.

**Source units**: `speed` is **km/h** — `P:\scripts\3_game\vehicles\car.c:102`
declares `proto native float GetSpeedometer()` and the comment on `CAR_JUMPOUT_THRESHOLD` at
`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:34`
gives the unit; the action compares it against `GetSpeedometerAbsolute()`. `rpm` comes
normalized 0..1 over `rpmMax` (in LFQuad3 the last point of `torqueCurve`
is 6400; dial prints up to 6000, so `maxValue 1.0` is 6.4 printed
units and `angle1` comes from theta(6.4)).

`speed`, `rpm`, `fuel`, and `coolant` **are native engine sources**, measured in the
ODOL of two 1.29 vanilla cars -- `offroadhatchback` (35 animation classes) and
`civiliansedan` (51) -- read with the ODOL reader of the external ODOL->MLOD converter. Both
have `IndicatorFuel { source = "fuel"; }` on the `dial_fuel` bone, and none
of their cluster animations passes through script `AnimationSources`.

> **Correction 2026-09-04.** This paragraph previously stated that `fuel` was "unconfirmed"
> as engine source, because in scripts only `GetFluidFraction()` appears. It was
> false, and contradicted a table that was already measured in the same project.
> **Absence on the script side is not absence in the engine**: `model.cfg`
> sources are native and do not have to show up in Enforce.

LFQuad3 carries `source = "fuel"` and the user accepted the cluster as good, but the
movement of that needle **is not broken down** in game.

`dashboardMatOn`/`dashboardMatOff` is the material for cluster backlighting; has
nothing to do with needles.

When mounting a needle from an object bringing a disc, the disc does **NOT enter** the
animated selection. In LFQuad3 the original disc of each needle travels inside
`kmh`/`rpm` ([ASSUMPTION] remains occluded by the new dial; user did not
break it down).

## Names

Unit is decided by source, not texture or selection name. Even
so, **do not name `mph` a speedometer in km/h**: in LFQuad3 that inherited
name led to belief that gauge was in wrong unit, costing a
round. And check whether art has unit printed before discussing it — that of
this quad has none.

## Trap 5 — rotation DIRECTION is not deduced, it is taken from vanilla

When mounting a needle there are two coupled unknowns: where axis points and in
which direction engine rotates with positive sweep. It is easy to solve one using
the other and believe something has been proven; reasoning is circular and fails to
detect error.

Rule comes from shipped content. Eleven cluster animations from four vanilla
1.29 cars, read from ODOL with the ODOL reader of the
external ODOL->MLOD converter (`Animations.classes` for
`angle0/angle1`, `Animations.axis_data[0][i]` for already resolved axis):

| car | animation | resolved axis | angle0 | angle1 | sweep | axis | rotation |
|---|---|---|---|---|---|---|---|
| offroadhatchback | IndicatorSpeed | (0, +0.422, +0.907) | 0 | 190 | +190 | towards | clockwise |
| offroadhatchback | IndicatorFuel | (0, +0.422, +0.907) | 0 | 90 | +90 | towards | clockwise |
| offroadhatchback | IndicatorRPM | (0, +0.422, +0.907) | 20 | 260 | +240 | towards | clockwise |
| civiliansedan | IndicatorFuel | (0, -0.458, -0.889) | 40 | -40 | -80 | away | clockwise |
| civiliansedan | IndicatorRPM | (0, -0.458, -0.889) | 50 | -40 | -90 | away | clockwise |
| hatchback_02 | IndicatorFuel | (0, -0.450, -0.893) | 0 | 44 | +44 | away | **counterclockwise** |
| hatchback_02 | IndicatorRPM | (0, -0.316, -0.949) | 0 | -270 | -270 | away | clockwise |
| hatchback_02 | IndicatorSpeed | (0, -0.316, -0.949) | 0 | -270 | -270 | away | clockwise |
| sedan_02 | IndicatorSpeed | (0, +0.371, +0.928) | -127 | 115 | +242 | towards | clockwise |
| sedan_02 | IndicatorRPM | (0, -0.371, -0.928) | 125 | -100 | -225 | away | clockwise |
| sedan_02 | IndicatorFuel | (0, -0.371, -0.928) | 44 | -44 | -88 | away | clockwise |

**10 out of 11 clockwise**, which is how the cluster of any car turns. The rule:

> **Positive sweep on an axis pointing AT DRIVER = clockwise seen by them.**

In DayZ vehicle models **+Z is BACKWARDS** (dashboard falls in -Z and
driver behind), so "points at driver" is `Y>0 and Z>0`. The only discrepant
row is a 44-degree fuel arc, which may be designed in
reverse on purpose.

That 10-out-of-11 **validates its own premise**: if +Z were forward, classification
would invert entirely yielding 1 out of 11 — absurd for shipped
cars whose clusters are seen turning clockwise. No need to believe convention
beforehand.

Reproducible in two minutes on
`DZ\vehicles\wheeled\{offroadhatchback,civiliansedan,hatchback_02,sedan_02}\*.p3d`.

In LFQuad3 this convention (axis towards driver, `angle0 = rest - theta(min)`)
is that of cluster approved in game on 2026-09-06. If a cluster with this
rule rests off zero, first suspect is frame (trap 2), not vanilla
rule. Cheap check: `light_left` and `light_right` of Memory
LOD and sign of `<u_of_frame, light_right - light_left>`; negative = mirrored
frame. LFQuad2 confirms it for a second time, now in game
(2026-09-07 00:15, build `77303210b92d63bd`, cycle with
`@SurvivorAnims`): speedometer 0-150 CLOCKWISE, legible "km/h", red to the
RIGHT, needle at 0; tachometer 0-6 CLOCKWISE. On 2026-09-06
speedometer was below 0 and tachometer above, negated sign
on Sep 4; measured against headlights, MIRRORED frame (det +164.81) and
corrected. Both user readings ("-10", "1000") are predicted
EQUALLY by mirror (-13.5 km/h, +880 rpm) and negated sign: two
observations that do not discriminate between two models choose neither.
What discriminates is measurement against headlights. User verdict
on build 00:15 names three other defects, none concerning
the frame.

## Trap 6 — raw normal of an MLOD face points INWARD

Corollary of 5, and it is the one that bites when applying it. To classify an axis as
"towards the driver" it is tempting to compare it with normal of its own dial,
computed as `cross(v1-v0, v2-v0)`. **In MLOD that cross points towards the
interior of the solid**, so "axis is aligned with normal" means
axis goes inward, not that it looks at driver. Reading it in reverse inverts
entire diagnosis.

Measured in LFQuad3: 94-97% of flank faces have cross
pointing inward.

**The positive control resolving it, valid in any model:** choose
faces whose outer direction admits no dispute —outermost flanks in X, or
roof— and check sign of `dot` between their cross and that direction.

```python
# known exterior = +X for right flank
n = cross(sub(v1, v0), sub(v2, v0))
d = dot(normalize(n), (1, 0, 0))
# d < 0 on most faces  ->  cross points INWARD in this model
```

Two warnings regarding the control, both paid for:

1. **Choose test face carefully.** Top strip of LFQuad3 yielded 38% and does not
   conclude: luggage rack tube is there, with faces pointing in all
   directions. Flanks yielded 3% and 6% across 2,400 faces each. **A control
   that does not discriminate is not a tie: it is a poorly chosen control**, and counting
   it as a vote degrades foundation without changing result.
2. **Do not use pilot point as arbiter.** `dot(axis, pilot - pivot)`
   seems intrinsic and is not: depends on WHICH pilot point is taken. In
   LFQuad3 handlebar cluster is above pelvis (`crewdriver`
   y=0.964) and below eyes, with pivot at y=1.200 — sign flips
   according to anchor, +0.142 with pelvis and -0.994 with eye. In a car
   with low dashboard this does not happen; on a motorcycle or quad, it does.

In LFQuad3 `<sel>_axis` normal is ALIGNED (not simply negated) against
`n_pilot = (0, 0.82162, 0.57004)`, which points to driver: an unconditional
negation would depend on OBJ triangle winding (`apply_needle_axis`).

## Trap 7 — `rpm` is normalized over `rpmMax`, not over painted number

`rpm` arrives 0..1, and `1.0` is the end of `torqueCurve`, **not the last
number on the dial**. If face is painted 0-6 and engine reaches 6400,
"6" falls at `6000/6400 = 93.75 %` of travel, and sweep has to be
painted arc divided by that fraction (`x 1.0667`). Painting 0-6 full arc and
wiring as if ceiling were 6000 makes **the needle lie across the entire
sweep**, not just at top.

Design corollary worth stating before artist finalizes art:
compare **painted redline zone** with MEASURED engine top. In LFQuad3
red starts at 5,000 and sustained top is 5,805 rpm (measured, 404 samples
with engine running), so at full throttle needle is **always** inside the
red. It is a legitimate decision, but it is a decision.

## Trap 8 — arc is NOT measured from art: it is proposed and verified by drawing

Measuring painted arc by automatic detection seems obvious and **failed four
times in a row** on clean art, in black and without noise:

1. **Ring centroid.** Centroid of a partial arc is not the center of the
   circle, so iterating center-ring-center DIVERGES. Center landed in a
   corner, with radius greater than image.
2. **Largest angular gap.** With discrete ticks there is always gap between marks;
   "largest gap" ends up being any random one. Worse: central label
   (`km/h`, `RPM x1000`) fills bottom sectors and SPLITS real gap, and
   red marks of redline disappear when converted to gray (pure red =
   luminance 76, below any reasonable threshold) and FABRICATE a gap
   where there is none.
3. **Label blobs.** Centroid of `150` does not fall at same radius or with
   same bias as that of `0`: linear fit yielded +-8 degrees residue.
4. **Major ticks by radial depth.** Count did not match (15 of 16, 9
   of 7) and step sizes came out 16 to 23 degrees on an otherwise regular scale.

**What does work, and is cheap:** propose a scale and **draw a needle
over each painted value**. The image tells on its own if correct. On speedometer
all 16 needles landed on their numbers on first try; on tachometer first
candidate failed, was corrected with the two isolated ticks next to gap and on
second try 0 and 6 landed in place.

Final instrument (`dial_derive_final.py`) leaves value<->tick assignment
WRITTEN in `DIALS` and re-measures it with guard (`TOL = 0.5` degrees): if a tick
moved, fails instead of deriving angles from another drawing. It is the auditable way to
propose and verify by drawing.

**And the closing gate, which is the only one not depending on any convention:** rasterize
**REAL UVs of constructed `.p3d`** onto texture —sampling V like
engine, `1-v`— and draw needle on top at `angle0` and `angle1`. If UV
points land on tick ring and needles on extreme marks,
mapping, texture, and angles are all three right at once. No synthetic
discs: a render not carrying UVs that model wrote proves nothing.
That is `dial_gate_final.py`: needle over EACH printed value, not just
extremes — a line fit to two endpoints always passes through both.

## Trap 9 — one atlas island per dial costs legibility

Putting dials as islands inside body atlas has two costs not
seen until in game:

- **Resolution.** Digit height is 2.8-4.5% of dial diameter. In
  order for a digit to reach 12 px an island of 270-430 px is needed. With 80 px
  islands a digit is 2-4 pixels: illegible. Measured from seat, dial occupies
  ~90 px of 1920 on screen.
- **The window.** With island one must measure center and radius WITHIN atlas, which is
  precisely the measurement that fails (trap 8).

**One texture per dial** eliminates both at once: art goes at full resolution and
UV window becomes `[0,1]^2`, with no crop to measure. It is also a
trivial convention to share across vehicles. In LFQuad3: `Dial_kmh`,
`Dial_rpm`, `Dial_fuel` -> `LFQuad3_dial_*_co.paa`, shared gauges rvmat
(contract calls for dedicated flat one; see LFQuad2 finding).

Limit is SCREEN, not atlas. Measured in LFQuad2 (2026-09-07): the
complaint "pixelated texture" was NOT the texture. Dial occupied 110 px on a
1920 screen and texture provided 501 (4.6 texels per pixel); a
printed digit is 3% of diameter, i.e. 3.3 px, and inevitably looks
coarse. Control: reducing atlas to 110 px offline reproduces EXACTLY
game appearance, so neither DXT1 nor mips degrade anything. Increasing
texture fixes nothing; what fixes it is enlarging the dial (`R_DIAL`
0.027 -> 0.038, +41%, 110 -> ~150 px: numbers are legible) or drawing
fewer and larger numbers. The ~90 px on screen and 12 px per digit
(above) already indicated so; symptom invites increasing texture, which
changes nothing.

## Trap 10 — driver SCREEN frame, and why it resolves both things at once

Measured in LFQuad3 on 2026-09-04 and closed on 2026-09-06, after three cycles with
art upside down. User complaints —"gauges are upside down" and
"needles do not start at 0"— were **a single defect**, both arising from not
having a declared frame. Frame is READ, not deduced.

**The frame, anchored to model.** Needle axis in Memory LOD points AT
driver (trap 6). "Up" is vehicle +Y projected onto plane.
Right is NOT `cross(view, up)` nor "must come out +X": in LFQuad3
driver's right is -X, and file itself knew this from headlights.
Right is projected onto dial plane from model markers
(`light_right` minus `light_left`, or `wheel_1_1`/`wheel_2_1`, or a `*_dir`).
Guard `SystemExit` if they disagree (in LFQuad3 `memory_lod` writes them; if
read from outside, also if missing). Instrument
(`dial_derive_final.py`) uses `LIGHT_RIGHT_MINUS_LEFT` and stops if that right
matches old base `cross(-axis, up)`.

**Mapping target, in that frame:** `right -> +U` and `up -> -V`. The
minus is not an arbitrary convention: V=0 is TOP edge of image.

**How to accredit that direction without blind belief: positive control is model
itself.** No need for test art. LFQuad3 bodywork writes
`(u, 1.0 - v)` from an OBJ (having v=0 bottom), meaning V=0 is top
edge — and that bodywork has cycles seen in game without anyone saying
texture is flipped. That is anchor. In another toolchain (LFQuad2, Arma 2 MLOD
without that `1-v`) anchor is different: **look at what rest of model does,
not what this page says**. Confirmed in game 2026-09-07 00:15
(build `77303210b92d63bd`): upright and legible art, clockwise, red
to the right. User verdict on that build names three other
defects, none regarding frame. What discriminated previous mirror was
measurement against headlights.

**How what is there is MEASURED, instead of argued.** Least squares
fits the 2x2 matrix taking (right, up) to (U, V) using **real UVs
of constructed `.p3d`**. With residue ~1e-6 fit describes entire
mapping, and then:

| result | meaning |
|---|---|
| `right->+U`, `up->-V` | correct |
| `right->+U`, `up->+V` | **vertical mirror** (text reads as in a mirror) |
| `right->-U`, `up->-V` | horizontal mirror |
| `right->-U`, `up->+V` | 180 rotation |

`det > 0` = MIRROR. Negative = unmirrored **ONLY if frame +U is the
REAL right of model**. A +U derived by cross product without checking
against markers can be real left (LFQuad3: +X), and then
determinant is read in a mirrored frame and conclusion inverts. Measured
with anchored instrument on the two LFQuad3 builds: mirrored one
(`LFQuad3_body.p3d.pre-mirrorfix-20260906`) yields +513 / +491 / +1290 and
corrected one -513 / -491 / -1290; that SAME mirrored build, measured on Sep 4 with
generator frame, gave all three negative and cluster remained mirrored in
game. Sign is only evidence in anchored frame. Bound
fit to ONE disc: mixing two dials and a swatch gives anisotropy 6.9 and
780 px residue (LFQuad2); a single disc, anisotropy 1.000000 and 0.0000 px
residue.

★ That table is what distinguishes a MIRROR from a ROTATION, and it is needed: user
reported "upside down, rotate 180" and measurement said vertical mirror. **Do not apply
symptom-describing correction: map to absolute target.** That way
result is correct regardless of label used to describe failure.

Calibration of the instrument against two known states (LFQuad3):

| mapping | basis | render | in-game observation |
|---|---|---|---|
| (+U,+V) | mirrored (cross) | upside down | Sep 4 14:32 build: "upside down, rotate 180" |
| (+U,-V) | mirrored (cross) | mirrored, red to LEFT | 16:28 build, seen Sep 6: "still mirrored" |
| (+U,-V) | anchored to headlights | 0 bottom-left, clockwise, red to right | fix; in game only global verdict of Sep 6 |

Mappings are named in frame of their `u`: (+U,-V) with mirrored basis and
(+U,-V) with anchored basis are DISTINCT mappings (in the unflipped frame they are
(+U,-V) and (-U,-V)). That is why basis is a column.

Reproducing BOTH known states turns instrument into authority; one
only distinguishes reachable from unreachable, not good from bad. Hypotheses
discarded WITH their measurement: texture does NOT arrive flipped (mean difference 0.20
in identity vs 9.00 in horizontal mirror; rpm 1.80 vs 8.08);
driver does NOT see rear face of disc (88 faces at +Y vs 16); axis does NOT
point inward (`<driver - p0, axis>` = +0.0210 kmh and +0.0203 rpm);
inverted winding upon binarizing is format convention, not a bug.

Three rules from the mirrored frame:

1. Frame is ANCHORED to something artifact says about itself, not deduced from
   a handedness convention requiring argument.
2. Instrument does not share with code the expression defining frame.
3. Calibrated against known states before believing a new verdict.

**And angles come from SAME frame, by subtraction.** With positive sweep
clockwise for driver (trap 5) and clockwise = DECREASING screen angle:

```
angle0 = rest - theta(minValue)
angle1 = rest - theta(maxValue)
```

where `rest` is screen angle of BLADE (silent trap 1 /
`needle_rest`: discards near-constant radius rim, band > 0.97*rmax with
>= 10 points spread over more than 90 degrees), and `theta(v)` the screen
angle of painted value. Closure: `dial_gate_final.py` draws needle over
each printed value in render of real UVs.

**Why a mirror moves zero.** Under mirror, `theta -> -theta`: painted 0
of speedometer was at 213 and seen at 147, so stopped needle
pointed to ~120 km/h. With mapping fixed, same `angle0` lands at 0. One
cause, two symptoms — which is why one must not "fix angles too"
separately. Old angles (-115.1/188.0 and -157.2/86.1) were deduced in
mirrored frame: pointed to numbers in their mirrored position. Sweep was
preserved: fix moves origin, not scale.

## Trap 11 — do not STRETCH non-power-of-two art: PAD IT

LFQuad3 fuel panel is 1536x1024 and texture must be power
of two. Was resized to 2048x1024, i.e. 1.333 stretch in x only.

That stretch turns tick arc —a **circle** in art— into an **ellipse**.
Fitted circle stops passing through marks, needle pivot sits at a
center that is no longer center, and needle passes above E and F without touching them.

**Pad with black on sides** (art background is usually black anyway) and arc remains
a circle. Constants translate automatically: `u_2048 = (pad + x_arte) / 2048`.

In LFQuad3 panel is a `Screen` QUAD of part 32 chosen by centroid
(`FUEL_FACE_POS`). `fuel_face_uv` maps a window with aspect ratio of face
itself centered on texture, V = row/H directly (without `1 -`). Pivot and reach
come from art arc (`FUEL_C_U/V`, `FUEL_R_U`) by inverting same mapping. Needle
scales `reach / tip` (`FUEL_INFO["scale"]`; x0.665 in final p3d:
constructed tip 0.01220 / scale 0.82 / canonical tip 0.02239).

★ General corollary: **an angle does not survive anisotropic mapping.** Before using an
angle measured on texture as screen angle, verify mapping is isotropic
—in 2x2 fit, `|dU/dright|` and `|dV/dup|` equal—. If not, either angle
is transformed, or radius is expressed in same units on both axes so
two anisotropies cancel out.

★ Corollary 2: **anisotropy can be absorbed in ART**, and is usually cheaper. If
face already brings good UV (exact [0,1] window, no mirror, negative det) and only issue
is non-isotropic mapping, there is NO need to reassign host model UVs:
simply compose art already deformed by INVERSE factor and both anisotropies cancel
on face. SUB_BRZ: real panel measures 264.78 x 105.61 mm (2.5072:1) against a
2:1 texture, so art was composed PRE-COMPRESSED horizontally by 0.797711; face
isotropy gate 1.0000 / 1.0053 / 0.9947. This avoids reassigning UVs of a 20 MB `.p3d`
not yours: same result with an order of magnitude less scope.

Condition to use it: anisotropy must be CONSTANT across face (2x2 fit with
residue ~0; in SUB_BRZ, 5e-07). If varying across face, deforming art only
cancels it at one point and one must return to remapping.

## Fuel panel from scratch

For a model bringing NO rectangular face to map art to. LFQuad3
REUSES a `Screen` quad of part 32 (trap 11); that recipe does not cover
constructing the panel. Numbers from official art `dial_fuel_official.png`
(measured in `assemble_lfquad3.py:140-158` and `convert_textures.py:223-233`).

**Art and padding.** PNG is 1536x1024 and is NOT a power of two. Padded to
2048x1024 with black and CENTERED (256 px on each side), never stretched:
`pad.paste(src_im, ((2048 - src_im.width) // 2, ...)` in
`convert_textures.py:223-233`. Stretching turns arc into ellipse (trap 11).

Constants (`assemble_lfquad3.py:140-158`): FUEL_TEX_W/H 2048/1024,
FUEL_ART_W/H 1536/1024, FUEL_PAD_X 256, FUEL_C_U = (256 + 940)/2048 = 0.58398,
FUEL_C_V = 968.7/1024 = 0.94600 (row counted from TOP),
FUEL_R_U = 634.7/2048 = 0.30991 (fraction of texture width),
FUEL_E_DEG = 130.0 (RED mark of empty end), FUEL_F_DEG = 48.5
(last tick of full). Center and radius come from a circle fitted to
ticks E..F and VERIFIED by drawing on top (`assemble_lfquad3.py:945-949`),
not from face bounding box. Sweep E->F: 81.5 degrees, CLOCKWISE.

**Same numbers as fraction of art** (face mapping ONLY art,
without padding bands):

- cx = 940/1536 = 0.6120 of width
- cy = 968.7/1024 = 0.9460 from top (pivot sits at 5.4% from
  BOTTOM edge: very open arc)
- r = 634.7/1536 = 0.4132 of face width

**Face and three clean windows.** In LFQuad3 face is a `Screen` quad of
1.84:1 aspect ratio, chosen by centroid (`FUEL_FACE_POS`,
`assemble_lfquad3.py:164-167`). `fuel_face_uv` (`assemble_lfquad3.py:866-893`)
opens a window with aspect ratio of FACE ITSELF centered on 2:1
texture: window occupies full WIDTH of texture and height comes from
ratio, so with 1.84:1 it overflows 44 px top and bottom (V
outside 0..1; relies on art being black there and wrap falling
onto black; comment in `assemble_lfquad3.py:874-878`). V = row/H
directly, without `1 -` (`assemble_lfquad3.py:886-893`).

Consequence for a NEW face: with ratio A, V goes from
0.5 - 1/A to 0.5 + 1/A; at 1.5:1 it would overflow 170 px and wrap would bring
art hub rows to top of face. Therefore LFQuad3 1.84:1 mapping
is NOT copied. Three clean windows:

- 2:1 face (padded texture ratio): U 0..1, V 0..1; black padding
  bands (12.5% per side) remain on face; center and radius,
  those of TEXTURE (0.58398 / 0.94600 / 0.30991);
- 1.5:1 face (art ratio): window of art ONLY, U 0.125..0.875,
  V 0..1; no bands; center and radius, those of ART (0.6120 / 0.9460 /
  0.4132). Rectangular shape for a pod bringing no face.
- face of DRAWING within art (measured 2026-09-07, LFQuad2): art
  brings its own black border; box x 305..1742, y 149..875 = 1437x726 px
  = 1.9793:1. Window U 0.1489..0.8506 (305/2048 .. 1742/2048), V
  0.1455..0.8545 (149/1024 .. 875/1024); no padding or art
  bands; corner-to-corner mapping, no overflow. Center and radius referred
  to drawing box: cx = 0.6200 of width (0.6200 x 1437 + 305 = 1196
  px texture = 940 px art), r = 0.4417 of width (0.4417 x 1437 =
  634.7 px). Same arc comes out by two different rules (fraction of
  art and fraction of drawing): this is cross-control.

In all three, V = row/H (without `1 -`), u = driver's right and w = up
of ANCHORED frame (traps 2 and 10). Art is neither stretched nor mirrored.

**Where the pivot falls.** With the drawing window (V up to 875/1024 =
0.8545), the arc center (row 968.7, V 0.9460) falls BELOW the
bottom edge of the face (3.3 mm at LFQuad2 size). So the
needle cannot be a needle from the hub: LFQuad2 built it as a
SHORT POINTER between 0.55 and 0.96 of the arc radius; drawn from the
pivot, it would stick out below the panel. With the entire art window
(LFQuad3, V up to 1.0), the pivot stays inside (V 0.9460) and the hub is seen
flush with the bottom edge.

A single quad suffices. In LFQuad3 the face belongs to the pod itself and has no lift; the
painted discs use lift 0.0012 (`assemble_lfquad3.py:771`). For a
new face over a pod: use whatever lift the discs of that model already use. LFQuad2
measures +1.89 mm of blade ahead of its disc and it works
(measured 2026-09-06, LFQuad2).

**Pivot, offset push, reach, and scale.** The pivot is the arc center
inverted by the same face mapping (`assemble_lfquad3.py:955-960`),
plus an offset push of 0.0004 m in front of the face along its normal
(`assemble_lfquad3.py:963`, "a hair ahead of the face, so it does not
z-fight with it"). The reach is the radius in meters:
`reach = FUEL_R_U * FUEL_TEX_W * m_per_px` (`assemble_lfquad3.py:961`),
that is, r_fraction x window width. The canonical needle
(`canonical_needle`, `assemble_lfquad3.py:972-1035`; trap 14) is scaled
`reach/tip` (`assemble_lfquad3.py:1985-1988`; in LFQuad3 x0.665).

Needle criterion: r_obj = maximum in-plane radius of the ENTIRE object;
non-Black faces with any vertex at r > 0.95 * r_obj are DISCARDED, and it is
REQUIRED that there are exactly 32 OBJ faces / 64 tris (`SystemExit` otherwise). The
parts in `_shared_parts\gauge_needles\` are regenerated with that cutoff
since 2026-09-07 (census, above: 182 tris, radial selections `hub`
158 / `blade` 24, z >= 0); `canonical_needle` lives in `assemble_lfquad3.py`.

**Angles: what transfers and what does not.** Convention:
`angle0 = rest - theta(min)`, `angle1 = rest - theta(max)`
(`dial_derive_final.py:282`; "The derivation instrument"). Both
thetas (130.0 and 48.5) and the sweep (81.5) belong to the ART with an
unstretched, unmirrored window: they transfer. Rest DOES NOT transfer: it is the direction of
the tip of selection `fuel` measured in the BUILT p3d, in the anchored
frame (`needle_rest`, `dial_derive_final.py:148`; printed in
`dial_derive_final.py:232-236`).

In LFQuad3, fuel rest is 0.90, which is why -129.1 / -47.6 are obtained
(instrument table). With the canonical needle mounted with the tip towards
+u, rest is ~0: it would yield rest - 130.0 and rest - 48.5, i.e.,
-130.0 / -48.5; with another mesh, it is measured. LFQuad2 built the needle
pointing UP (rest = 90 in its anchored frame) and obtains angle0
"rad -40.0", angle1 "rad 41.5", sweep +81.5: art thetas
(130.0 / 48.5) transfer, rest does not. Wiring identical to LFQuad3 and
bone "fuel" parented to "drivewheel". The pairs -129.1/-47.6 must NOT be
copied to another model.

**Wiring.** `generated/model.cfg:238-247` (`IndicatorFuel`, source
"fuel", selection `fuel`, axis `fuel_axis`, memory = 1, minValue 0,
maxValue 1). The bone hangs from the corresponding dashboard or handlebar
bone (`skeletonBones[]`: in LFQuad3 `fuel` from `drivewheel`;
wiring contract, above). The new panel geometry AND its
points belong in that animated selection (trap 15); otherwise, when turning the
part, the panel stays behind.

Checklist:

- arc drawn over the art (passes through tick marks E..F)
- V = row/H, without `1 -`
- anchored frame (u = driver's right, traps 2 and 10)
- chirality: new part frame projected from anchored frame (Gram-Schmidt),
  not reconstructed via cross product or flipped component-wise;
  `<u_part, anchored_right>` > 0 (trap 2; measured 2026-09-07, LFQuad2)
- where pivot falls: inside the face (art window, V up to 1.0)
  or below (drawing window, V up to 0.8545); if it falls outside, short
  pointer 0.55..0.96 of radius, not needle from hub
- rest measured in the built p3d (`needle_rest`); not inherited
- animated bone: panel and needle in rotating selection (trap 15)
- negative det in anchored frame (`det < 0` = direct)

## Trap 12 — a regularity check rejects a bad measurement before it costs you a cycle

Detecting the ring tick marks to measure the arc fails in many ways (trap 8).
What makes detection **usable** is not tuning the threshold: it is a check provided for free by
the scale itself. A gauge scale is **regular**, so:

- if detected tick marks are not equally spaced within a narrow margin, the
  detection is wrong and **the number is not used**;
- the LARGEST angular gap is reliable even if the rest fails: it bounds the arc.

Measured: on the speedometer ring, detection yielded 46 clusters with steps from 1.5 to
15.8 degrees — RED check, number discarded. The three LARGE tick marks, however,
define the circle exactly, and using that center the ten fuel panel tick marks
came out to a 9.0-9.4 degree step: GREEN check.

★ And a LUMINANCE threshold skips RED tick marks (pure red = 76, below
any reasonable threshold). The "empty" end of a fuel gauge is precisely a
red mark: probe by **color**, not by brightness, or you will measure an arc that falls short
precisely at the end that defines `angle0`. Ink by MAXIMUM channel (`INK = 110`,
`max(r,g,b)`).


## Three silent traps when deriving needle angles (added 2026-09-04, LFQuad3)

All three were found by measuring the built `.p3d`, and each one produced a
plausible number rather than an error.

**1. The needle selection is not only the needle.** Taking "the farthest point of
the needle selection" as the modelled rest direction returned a vertex of the
**hub disc** — a 32-gon at the *same* radius as the printed dial face (measured:
32 points at r=0.0209 with the face at r=0.0208; the blade only reaches 0.0184,
88 % of it). The angle it returned was meaningless and depended on set iteration
order. Discard any ring of points at near-constant radius spread over more than
~90 degrees, then take the farthest of what is left.

**2. Whether the texture is mirrored is a determinant, not a judgement call.**
Fit the affine map (driver-screen x,y) -> (U,V) over the dial faces of the built
model. Image V grows **down** and screen y grows **up**, so an unmirrored texture
gives a **negative** determinant. Positive means mirrored, whatever the numbers
"look like" in a small render. That sign is valid only in a frame whose +right
is the model's real right (trap 2). In LFQuad3 the instrument first shared the
generator's frame (`u = cross(w, axis)`, pointing +X while the driver's right is
-X): on 4 September it read +512/+491 for the round dials with the (-U,-V) mapping and
-1290 for the fuel panel, and once the mapping went to (+U,-V) it read all three
negative -- on a build that was still mirrored in game. Measured again with the
frame anchored to `light_left`/`light_right`, that same mirrored build reads
+513 / +491 / +1290 and the fixed build -513 / -491 / -1290. The sign became
evidence only once the frame was anchored; the bug was the frame.

  ★ Corollary about evidence: two user reports of the same defect are not two
  observations of two states. Check the **build timestamp** before inferring a
  sign from a sequence of reports. Here "upside down" and "mirrored" both
  described the same deployed PBO (14:32); at that moment the intermediate fix
  had not been built yet, and reasoning as if it had produced a sign that the
  render then disproved. The 16:28 build shipped later and was seen on 6 September
  ("still mirrored"): that is the second calibration point of trap 10, not a
  second observation of the 14:32 build.
  Trap 2 amends the ending: that lesson stands, but the sign taken from the
  determinant was measured in a mirrored frame, so the correction that followed
  from it was wrong.

**3. Reading ticks off the art needs two limits and the right ink test.**

- Ink by **max channel**, not luminance. A red tick (255,0,0) is 76 in
  grayscale; an ink threshold of 110 drops the whole redline band and, with it,
  the last major of the scale.
- Measure how far ink reaches inward from the rim, and **stop early**: a hole
  tolerance of ~2 samples and a scan depth of ~0.16 of the radius. With a looser
  tolerance the scan jumps from the tick to the printed number beside it and
  returns 6-10 degree plateaus centred on the numbers, dips and all. Measured on
  this dial a minor tick reaches 0.07-0.11 of the radius and a major 0.15+, which
  separates the two families cleanly. Instrument: `INK = 110`, `KMAX = 160`
  samples at 0.001 r, `holes > 2` cuts, majors with depth >= `MAJOR_MIN = 0.13`.
- Do **not** pick a ring "because it returns as many groups as there are
  majors". A count that matches validates nothing: one ring returned exactly 16
  groups spread over 62 degrees on a dial that sweeps 290.

**And a fit rule when the printed scale is not regular.** The needle rotates
linearly, so a printed scale that is compressed at one end cannot be matched
everywhere. Fit the line to the regular part that is actually used (LFQuad3:
0-100 km/h, residual 1.53 degrees over 11 majors) and let the error fall in the
range the vehicle never reaches, rather than spreading it across the whole face.
Gate it by drawing the needle on **every** printed value, not on the endpoints —
a line fitted to two endpoints passes through both endpoints by construction.
Fuel E and F are NOT re-measured: the depth centroid of those long marks lies 8
degrees off (130.0 and 48.5 come from the arc fit, checked by drawing).

## The derivation instrument

`dial_derive_final.py` reads the ALREADY BUILT `.p3d`: both points of
`<sel>_axis` in Memory LOD, actual UVs of faces textured with the
gauge texture, and official art. Helpers: `dial_gate_final.py` (render of
actual UVs with anchored frame, needle over each printed value), `fit_gauge.py`
(circle, window, and scale fitting; validated against positive control),
`needle_draw.py`. `dial_render_v5.py` predates frame anchoring and is not
used for sign-off.

Final numbers (measured 2026-09-06, LFQuad3; `dial_angles_final.json`;
`generated/model.cfg`):

| dial | minValue | maxValue | angle0 | angle1 | sweep | gate |
|---|---|---|---|---|---|---|
| kmh | 0 | 150 | "rad 232.5" | "rad 535.3" | 302.8 | 11 green (0..100) |
| rpm | 0 | 1 | "rad 213.1" | "rad 456.4" | 243.3 | 7 green (0..6) |
| fuel | 0 | 1 | "rad -129.1" | "rad -47.6" | 81.5 | 3 (E, middle, F) |

Determinants with anchored frame: kmh -512.5, rpm -491.2, fuel -1290
(`det < 0` = direct). Fitting span: speedometer ONLY 0..100; tachometer
its 7 major marks; fuel tank E and F.

Dial center and radius in texture (`DIAL_UV`): center obtained via two concurring
methods (non-black centroid and least-squares circle on
major marks, within 12.7 px kmh and 6.4 px rpm); radius = ACTUAL disc edge (r_max).
Moving the center MOVES angles: they are re-derived when it changes. Painted disc:
32 segments, `DISC_R = 0.0254`, centered at p0 offset by `lift`, `add_dial_faces`. Each needle
with ITS disc: `remap_gauge_discs` assigns by x (`aguja_izquierda` at x +0.056 =
speedometer; `aguja_derecha` at x -0.055 = tachometer; OBJ names
are inverted relative to their position).

Stack measured along axis, in mm from eye: -0.3 painted disc with
bad `lift` of -0.0003 (covered everything), +0.0 blade, +0.8..+2.5 hub, +1.5
original panel. With `lift` 0.0012, painted disc sits BETWEEN blade and
panel.

## Trap 13 — the PAA cache that does not check content

`convert_textures.py` `emit` skipped ANY `.paa` existing on disk,
without checking timestamp or content. Measured: packed gauge faces dated from
Sep 4 03:44 and art from Sep 4 15:39; tachometer correction and
speedometer revert NEVER reached the game and every cycle checked the
old texture. Now: sha256 stamp of the PNG passed to ImageToPAA,
saved as `<paa>.src.sha256`; if source changes, it is reconverted.

The cache DID NOT cause mirroring, though for a while it appeared so: two real defects in
the same path, and the first one encountered does not have to be the one explaining
the symptom.

Stamps and backups residing inside mod tree end up
in PBO if packaging copies entire tree (95.7 MB instead of 21.8, with
"Build Successful"); `pack_lfquad3.py` filters using `ignore_patterns`.

## Trap 14 — a count is not a shape: three fake fuel needles

LFQuad3's fuel needle went through probes three times with three different
shapes, none of which was a needle. Topology: see trap 1.

**Shape 1** (Sep 4 build): filter by angular width seen from hub,
cutoff at 5 degrees. A blade triangle close to pivot spans a wide angle
BECAUSE IT IS CLOSE: filter ate up blade interior and left 10 tris of
sliver at tip (r 0.01122..0.01217). Invisible in-game on LFQuad3.
THAT is the rule this reference recommended. It is bogus. The shared
library was extracted with that rule on 2026-09-03 (7 blade faces: both
full octagons and 5 sides, no cap, blade behind hub) and was
regenerated on 2026-09-07 with `canonical_needle` (census, above). When checking
who else uses them, do not look only for missing needles: on LFQuad2 the old
part protrudes +1.89 mm ahead of painted disc (another lift) and is visible.

**Shape 2** (round 1 from 2026-09-06, "keep all"): furthest vertex
became one on the disc (0.02544), scale dropped from x0.665 to x0.585, blade
reached 88% of arc and full disc landed on arc. It PASSED count
probes (182 faces, "order of magnitude of kmh") and cross-review. Caught by
ANOTHER observable: derivation instrument (rest 0.90 -> 5.63 and 32 discarded
ring points where 0 existed previously) and part drawing.
`fuel_needle_probe.R1.out`: 182 faces and r_min 0.00111 — green, and wrong.

**Shape 3, common to both:** blade sits BEHIND hub plane (negative
z) and pivot is only pushed 0.0004 ahead of panel face
(`add_fuel_gauge`): 360 of 546 vertices ended up behind panel. No
probe measured depth until one was added (`fuel_needle_probe.py`:
"blade vertices behind the panel face (z < -0.0003)" -> OK/HIDDEN).

**Correct** (`canonical_needle`): r_obj = maximum in-plane radius of entire
object; non-Black faces with any vertex at r > 0.95 * r_obj are DISCARDED, and
it is REQUIRED that there are exactly 32 OBJ faces / 64 tris (`SystemExit` otherwise);
tip = furthest vertex of remainder; canonical pose (pivot at origin,
tip +X, axis +Z); canonical z shifted so blade back ends up
at 0. Result on final p3d (`fuel_needle_probe.R2.out`): 118 `Gauges`
tris (cap 30 + octagons 12 + 76 from quads), tip at r 0.0122 on
arc, 0 vertices behind panel, rest 0.90 with 0 ring points, angles
-129.1/-47.6 unchanged.

Four lessons from the three fake needles: a count is not a shape (ask what else produces
that number; if it is "the entire object", criterion does not discriminate); reviewer
inherits brief's criterion; measure ALL dimensions user sees (depth
relative to what it occludes); look at the part (a 60 KB drawing was worth
more than three rounds of probes).

## Trap 15 — new geometry inherits NO selection

Measured on LFQuad2, build `77303210b92d63bd`, 2026-09-07 00:15. The 64 painted
disc faces added as new geometry were in NO
selection; needles were (`dial_speed` / `dial_rpm`, which in `skeletonBones`
hang from "drivewheel"). In-game result, literal quote from user: "when turning
the part, dash does not turn with it, both circles stay behind (needles
do rotate)".

Fix: place faces AND their points into animated selection (`drivewheel`)
across ALL LODs containing dials. Build `4034b2e35a9fbb96` (00:33):
dials turn WITH handlebars.

Generalizable: new geometry inherits no selection, and symptom
only appears when TURNING; no static screenshot reveals it. It is symmetric
to already documented case (original disc traveling INSIDE animated
selection when it should not; confirmation table, LFQuad3 row): here it is the one
staying OUTSIDE that should be inside.

Cheap self-check (measured 2026-09-07, LFQuad2): scaling gauge IN
PLANE (non-uniform, so as not to eat up needle margin over disc)
changes neither UVs (`uv_disco` divides radius by `R_DIAL`: maximum
change 0.000000 px) nor angles (102.55/405.45 and 71.95/315.16 before and
after). If they change upon scaling, scaling and mapping are inconsistent.

## Trap 16 — handlebars with rake separate hands from grips when turning

Measured on two models (2026-09-07). LFQuad2 `drivewheel_axis` was 3.4 degrees off
vertical (direction (0, +0.9982, -0.0599)); at +-30 degrees rotation the grips, at 0.378 m from
axis, rise and fall +-11.5 mm with OPPOSITE sign on each side (dz +-190 mm dominant, dx
+-41..60). With EXACTLY vertical axis that term is 0.00 by construction. Hands do not
follow: this model has no IK (Memory LOD only holds `crewdriver` and `drivewheel_axis`),
hand is placed by animation relative to seat. User verdict, verbatim, after making axis
vertical through same point: "axis better now". LFQuad3 confirms from the other side: its axis
is exact (0, 1, 0) (Memory LOD, measured in deployed p3d `9499be34`), animation
`drivingwheel` with `angle0 "rad -30"` / `angle1 "rad 30"`, grips at 0.464 m.

What it was NOT: the sweep. LFQuad3 sweeps the same (+-30) with grips FURTHER away (0.464 versus
0.378 m; 232 mm travel versus 189) and lacks reported symptom; if sweep were
cause, it would separate more on LFQuad3. Open question whether hands track grips at STOPS on
LFQuad3 (not itemized). Relative seat-grip posture differs between both models under
same animation: LFQuad2 has handlebar 22 cm further forward and 12 cm lower relative to
seat, and driver 16 cm higher and 12 cm further back relative to axis base.

Status at 02:30 on 2026-09-07 (LFQuad2, after its closure): sweep at +-22.5 (was +-15) and
driver 125 mm forward of original, with seat-grip reach at 588.7 mm, identical
to LFQuad3. Open contradiction: LFQuad3 uses +-30 with 232 mm travel and is signed
off, so if its hands hold that, +-30 on LFQuad2 was not "excessive" and user's
range measures something else; LFQuad2 hypothesis: grip HEIGHT above
seat (+210 mm in LFQuad3, +118 in LFQuad2). Deciding factor is checking LFQuad3 hands at
both stops (not done).

Rule: handlebar axis in Memory LOD is written VERTICAL unless measurement indicates
otherwise, and is verified with vector direction, not by eye (3.4 degrees cannot be seen).

Methodological trap when modifying sweep (LFQuad2, same night): pattern `minValue -1 / maxValue
1 / angle0 "rad -30" / angle1 "rad 30"` matches THREE blocks in `model.cfg`: `drivingwheel` and
both front wheels (`turnfrontleft`, `turnfrontright`, ACTUAL steering angle). A
pattern replace leaves quad steering half as much as it should, and in-game reads as "drives
weird", not as "handlebar is wrong". Caught by uniqueness assert on edited block, not by
eye.

## Trap 17 — two signs per new face, both copied from neighbors

A new face carries TWO independent signs: winding (vertex order: determines
culling) and STORED per-vertex normal (determines lighting). Neither is deduced from
"must face driver": both are READ from neighboring faces already rendering properly and
are checked SEPARATELY. Same night (2026-09-07), one failed in each model, and in
both the other sign was correct:

- **LFQuad2, stored normal.** Correct winding on all four parts (`<cross, axis>`
  = -1.000, like discs), but fuel panel and needle with stored normal at
  +1.000, written "towards driver". By day they looked identical to dials; at NIGHT they did
  not shine under same rvmat. Measured on the LFQuad2 `.p3d` and reproduced with
  a second instrument on `.p3d` of its deployed PBO (`3670fe455648c1ac`: 1 + 1 faces
  with `<normal, cross> < 0` in each visual LOD) and on its fixed tree
  (`5f49257c4380280d`: 0). Its PBO carries it since 02:10 (`bea1b889b3ecedae`, body
  `5f47e2cbf8ea323f`, 0 with this instrument); NIGHT inspection remains pending.
- **LFQuad3, winding.** Stored normal = cross on all cluster faces (generator
  saves cross `n` in `add_tri`): 0 inverted. But `add_fuel_needle`
  forced `<cross, axis> > 0` with `axis` towards driver, and EVERYTHING else in cluster
  has `<cross, axis> < 0`: discs, rings, numbers, fuel panel, and OBJ
  kmh/rpm needles (raw cross points inward, trap 6). 182 tris reversed relative to
  rest: fuel needle gets culled from seat in build `5ac339d3` that was
  signed off (global verdict; that needle was not broken down). No offline render
  caught it: they draw double-sided. Fixed in generator (flip condition changed to
  `> 0`); in-game confirmation pending.

**Rule.** For each new cluster selection: `sign(<cross, axis>)` equal to that of
already visible discs, and `<stored_normal, cross> >= 0` at each vertex (60-degree
smoothing never drops below 0.5). Both columns come from `normal_sign.py` (LFQuad3
measurement tools): groups cluster faces by selection + texture against nearest Memory
axis. Positive control: `--control <sel>` negates in memory the
normals of a selection and all its faces must be flagged. Independent control:
LFQuad2 PBO above, which is a real defect made independently. The instrument also provides
winding verdict: each gauge group (needle selections, dial textures,
numbers and needles) against average sign of painted discs. Functional LODs
(Geometry 1e13, ViewGeometry 6e15, FireGeometry 7e15) are excluded unless `--all-lods`:
they carry 1-2 untextured faces with normal at +0.6 that are not rendered and which a blind
counter reads as "5 discrepancies" on a clean model (noise measured on LFQuad2). And normal
counter sums only gauge groups: rest of cluster is reported separately,
informational, because decimated LODs of a base model ship with some face having
smoothed normal against its cross (LFQuad2, LOD 1-3: 5-7 faces each).

**And in-game, inspect cluster also at NIGHT** or with dash lights turned on
(`dashboardMatOn`, the material that 1.30 registers on the `DashboardOn` selection,
`P:\scripts\4_world\entities\vehicles\carscript.c:230`; on 1.29 `DashboardShineOn` applied it, at `carscript.c:2481-2497` of the 1.29 build, which is not on `P:\`): normal defect only surfaces in low light. Winding defect is
visible at any hour, but only when inspecting THAT specific part: global verdict does not break it down.

**And winding instrument has its own failure mode: radial metric does not decide on
a shell.** Counting what fraction of faces has cross pointing OUTWARD from
mesh centroid works on a convex solid and means nothing in a cockpit. Inside
SUB_BRZ that metric gave **0.0% of faces "towards driver"** and looked like
entire model reversed. It was not. A cockpit is a shell viewed from INSIDE and
a cluster is almost a torus: centroid falls outside material, so radius is no
reference for anything. Signed volume also failed to arbitrate: negative in BOTH
variants, and neither mesh was WATERTIGHT, a condition without which that number
means nothing either.

**What decides is a FLAT surface already known to be visible, in the SAME file.**
`light_dashboard` (dashboard, which is obviously visible) gave `<cross, axis> = -1.0000` and
`screen_nav` -0.9858; the 100 nearly parallel faces of new needle bore that exact same
sign. False alarm dropped without flipping anything: flipping via radial metric would have INTRODUCED
defect believed to be fixed. Rule: winding witness is a VISIBLE neighboring
face of known normal; centroid statistics only apply to convex shapes, and signed
volume only to watertight meshes, which must be verified BEFORE citing it.

## Trap 18 — a verdict on a STATIC cluster does not accredit needle motion (added 2026-10-01, SUB_BRZ)

The interior proxy carried the three needles with their `Indicator*` classes. The user's
verdict on that build was "driver dash correct", and the turn sign was taken as proven from it;
in a later session, watching the moving car, the needles had NEVER moved - frozen at full left. The sources were
the same ones that move on the quad control car and the wiring chain was identical: they had never
animated at all (measured in game, DayZ 1.30.164014 Exp). A global verdict on a static cluster
accredits neither movement nor turn sign: ask to move the car and look at the needle before closing
a gauge task. Needles and their `Indicator*` classes live in the VEHICLE model, never in a static
proxy.

## Complete recipe for a new cluster, in order

Numbered steps. Each with its offline gate and LFQuad3 function that
implements it. Another pipeline (LFQuad2 or other) follows the order, not the example's
numbers.

1. **Anchor the frame.** Right = model markers projected to gauge
   plane (`light_left`/`light_right`, or equivalent). Fatal guard if
   discrepant (and if missing, when read externally). Gate: sign of `<u, light_right - light_left>`
   (negative = mirrored frame); instrument halts if old and model bases
   coincide. LFQuad3: `MODEL_RIGHT`, `dial_basis`, guard in
   `memory_lod`; `LIGHT_RIGHT_MINUS_LEFT` in `dial_derive_final.py`.
2. **One texture per gauge**, power of two padded (trap 11), separate flat
   rvmat, excluded from color selections. Gate: PAA matches current
   art; 0 dial faces in `camo1`. LFQuad3: `MAT_TEX` `Dial_*`,
   `convert_textures.py`; own flat rvmat discovered in LFQuad2.
3. **Painted disc + polar UV (+U, -V)** with anchored basis. Gate: `det < 0`
   on EACH disc separately (trap 10). LFQuad3: `add_dial_faces`,
   `polar_uv`, `remap_gauge_discs`.
   - **Fuel panel.** If model DOES NOT supply face: section
     `## Fuel panel from scratch`. If reusing face: trap 11
     (`fuel_face_uv`). Do not copy LFQuad3 1.84:1 mapping to new face.
   - **Animated selection** (trap 15). Put faces AND their points (discs,
     panel) into rotating bone selection, across ALL LODs with
     dials. Gate: when turning, dials move with pod.
4. **Needle:** canonical pose, pivot = Black hub, hub + blade only (never
   disc), in front of panel, disc 1.2 mm behind (`lift = 0.0012`). Gate:
   depth probe in green (`z < -0.0003` behind panel = HIDDEN) and
   part DRAWING. LFQuad3: `canonical_needle`, `add_fuel_gauge` (pivot
   0.0004), `needle_parts_probe.py`, `fuel_needle_probe.py`, `needle_draw.py`.
   Gate 2: `normal_sign.py`, needle winding and stored normal matching sign of
   discs (trap 17): render without culling misses it.
5. **`<sel>_axis`** = pivot and pivot + normal towards driver; bones;
   Indicator classes with `"rad"`. Gate: both points exist in Memory;
   bone hangs from dashboard. LFQuad3: `apply_needle_axis`, `memory_lod`,
   `generated/model.cfg`.
6. **Angles via instrument:** value<->tick pairs written and re-measured
   (`TOL = 0.5`), fit to regular span, `angle0 = rest - theta(min)`, rpm
   over `rpmMax`. Gate = needle over EACH printed value (`dial_gate_final.py`).
   LFQuad3: `dial_derive_final.py` -> `dial_angles_final.json`.
7. **Texture cache by content** (`<paa>.src.sha256`) and PBO of expected
   size (stamps do not travel; trap 13). LFQuad3: `emit` in
   `convert_textures.py`, `ignore_patterns` in `pack_lfquad3.py`.
8. **Before trusting a new render**, reproduce two known states
   (trap 10). A single green does not tell good from bad.
9. **In-game**, inspect: all three gauges unmirrored and with new faces; fuel
   needle visible and between E and F, moving with tank; with engine
   running, kmh/rpm moving and painted dial NOT rotating
   with them; rest resting on zero. Record **verbatim** verdict,
   with build and date, and items remaining not itemized. LFQuad3 closed with
   "dashboard is good now" (2026-09-06, `5ac339d3`); fuel motion,
   original disc, and exact zero remain not itemized. Inspect also at NIGHT or
   with dash light on: inverted stored normal surfaces only in low
   light, and a culled part only when looking at that part (trap 17).

## Confirmation status

| | signed off in-game | not itemized / open |
|---|---|---|
| LFQuad3 | "dashboard is good now" (2026-09-06, build `5ac339d3`) | fuel motion; original disc in animated selection; exact zero (offline gate); fuel needle: in `5ac339d3` its 182 tris have winding reversed relative to rest of cluster (culled from seat, measured 2026-09-07, trap 17), fixed in generator and UNCONFIRMED in-game |
| LFQuad2 `77303210b92d63bd` | 2026-09-07 00:15, cycle `@CF` + `@VPPAdminTools` + `@SurvivorAnims`, 1st person: speedometer 0-150 CLOCKWISE, "km/h" legible, red on RIGHT, needle at printed 0; tachometer 0-6 CLOCKWISE, "RPM x1000" legible, red on right, needle at 0; both dials visible from seat. Verbatim user verdict: "nothing seen on fuel gauge, plus when turning the part, dash does not turn with it, both circles stay behind (needles do rotate). On the other hand, as you can see, texture is pixelated, must be fixed". Second in-game confirmation of the mirrored-frame finding, on another model. What discriminated prior mirroring was measurement against headlights (det +164.81). Deployed as `LFQuad2.pbo` `77303210b92d63bd` + `model.cfg` `1a2df84507870fc8`. | fuel: none; discs outside drivewheel (trap 15); pixelated texture = screen resolution limit (trap 9). None of the three stems from frame. |
| LFQuad2 `4034b2e35a9fbb96` | 2026-09-07 00:33 (R 0.038 and discs in drivewheel): dials turn WITH handlebars; legible numbers; unmirrored faces; needles at 0. User verdict: PENDING. | user verdict pending; fuel: none. |
| LFQuad2 batch 2 (fuel panel + driver 1 cm forward; PBO 12,632,912 B; 2026-09-07) | offline gate green: actual UVs from .p3d rasterized against texture with frame anchored to headlights, needle drawn at E, 1/2, and F, det -231.92 direct, anisotropy 1.0049, residual 5.0e-07; deployed and verified by content inside PBO. CONFIRMED IN-GAME (2026-09-07 01:16, clean cycle, cycled storage, new character, frame_stale=false): panel visible above gauges, centered, FUEL / E / 1-2 / F legible and unmirrored; needle built pointing UP (rest 90) points in-game to F with fuel = 1.0: engine rotated it +41.5 = its angle1. First WIRING test of recipe, not just drawing. | user verdict on LFQuad2 in that window: hands and handlebar separate when turning ("handlebar moves slightly upward and hand animation slightly downward"), defect unrelated to cluster (handlebar axis with 3.4 degrees rake, under study); no recorded objection to panel or mirroring. |
| SUB_BRZ `AF365A3C` (2026-09-07) | **CONFIRMED IN-GAME by user** on 2026-09-07, manually launched cycle (`@DayZ_MCP;@CF;@VPPAdminTools;@SurvivorAnims;@SUB_BRZ`, Chernarus). Verbatim verdict: "Driver dash correct, leaving it like this now". Confirms along the way that rotation SIGN, which was DERIVED and not measured, was correct: reversed it would have swept backward. Third model confirmed under recipe, and first with all three custom dials. | ENTIRE cluster. Built offline: three custom dials (km/h 0-220, rpm 0-8, fuel E-F) in `brz_cluster_co.paa` DXT1 2048x1024 across the 42 faces of `light_dashboard`, which already had an exact [0,1] UV window and native emissive swap `dashboardMatOn/Off`; three canonical 182-tri needles in BOTH visual LODs of interior proxy (1.0 and 1100 = first person); `mph` -> `kmh`; `IndicatorSpeed maxValue` 60 -> 220, which was a REAL defect (needle stuck at 60 km/h and rest of scale was dead). Verified INSIDE PBO: binarized ODOL of interior contains `kmh`/`kmh_axis`/`rpm`/`rpm_axis`/`fuel_1`/`fuel_1_axis` and zero `mph`. **Rotation SIGN is DERIVED** (right hand + `DrivingWheel` from same file), not measured: if it sweeps backwards, it is a sign. Inherited trap: BODY (`sub_brz.p3d`, byte-for-byte identical to the build before it) retains obsolete `mph`/`rpm`/`fuel_1` memory points with PURE +-Z axes vs inclined interior axes; `model.cfg` does not reference them, but car #2 could be wired to wrong pair. |
