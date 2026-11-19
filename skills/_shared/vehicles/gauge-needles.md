# Dashboard gauge needles

How to wire a speedometer, tachometer and fuel needle on a vehicle: the selection, axis and bone each needle needs, the `model.cfg` classes, which way vanilla needles turn, what `rpm` is measured against, and the order to build a new cluster in.

The rest of the gauge work is split by topic in this pack:

| Question | File |
|---|---|
| Building the needle mesh, its rest angle, its depth, and the two signs of every new face | `gauge-needle-part.md` |
| The dial's screen frame, telling a mirror from a rotation, deriving `angle0` and `angle1` | `gauge-dial-frame.md` |
| Measuring the printed arc, one texture per dial, padding, legibility on screen | `gauge-dial-art.md` |
| A fuel panel on a model that has no face for it | `gauge-fuel-panel.md` |

The source units of `speed` and `rpm`, the `"rad N"` syntax and where needle bones must live are in `vehicle-modelcfg-animations.md`, section "What the engine feeds the needles"; whether any animation turns the right way in general is in `animation-sign-and-axis.md`. The numbers below were measured on mod test vehicles (two quads and a coupe), which is mod behaviour, not vanilla, except where a `P:\` file is cited.

## The wiring

1. Put the needle geometry in its own named selection, such as `kmh`.
2. In the Memory LOD, add two points named `<selection>_axis`: the pivot (the centre of the needle's black hub) and the pivot plus the dial normal pointing toward the driver. Align that normal against a fixed vector toward the driver rather than negating it, so the result does not depend on the OBJ's triangle order.
3. Add a bone in `skeletonBones[]`, child of the dashboard or handlebar bone (on a quad, `kmh`, `rpm` and `fuel` hang from `drivewheel`). Add it to `sections[]` only if the selection changes texture or material.
4. Paint the dial face 1.2 mm behind the needle (`lift = 0.0012` along the dial normal that points away from the driver) and in front of the panel. Keep the whole needle in front of the panel. A `lift` of -0.0003 hid the needles from every view.
5. Give each new face the same winding and stored normal sign as the visible dial faces next to it (`gauge-needle-part.md`).
6. One texture per dial, a power of two, padded and never stretched (`gauge-dial-art.md`), on its own `.rvmat` with a flat normal and flat specular. Vanilla gauge materials use exactly these, `#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)` and `#(argb,8,8,3)color(1,0,1,1,SMDI)` (`P:\DZ\vehicles\wheeled\offroad_02\data\beige\offroad_02_gauges_e_nolight.rvmat:104` and `:124`). Keep dials and needles out of the paint `hiddenSelections` (`camo1`), or a colour variant overwrites their texture.
7. Add the three `CfgModels` animation classes.

Values from a test quad whose cluster was accepted in game:

```cpp
class IndicatorSpeed
{
    type = "rotation";
    source = "speed";      // km/h
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
    source = "rpm";        // 0 to 1
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

These angles belong to that model's mesh and art; derive your own (`gauge-dial-frame.md`). `fuel` is a native engine source like `speed` and `rpm`: `model.cfg` sources need not appear in script, so its absence from Enforce Script, where fuel shows up only as `GetFluidFraction()`, proves nothing. `speed` is in km/h; `GetSpeedometer` is native on `Car` (`P:\scripts\3_game\vehicles\car.c:102`), and `CAR_JUMPOUT_THRESHOLD` is commented as km/h and compared with it (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:34`).

`dashboardMatOn` and `dashboardMatOff` are the cluster backlight, not the needles. In 1.30 `dashboardMatOn` is registered on the `DashboardOn` selection (`P:\scripts\4_world\entities\vehicles\carscript.c:230`), which uses hidden selection 8, `SELECTION_ID_DASHBOARD_LIGHT` (`:182`). `DashboardShineOn` still exists but is marked `[Obsolete("1.30: use VehicleLightsComponent instead")]` and only calls `SetSelectionMaterial("DashboardOn")` (`carscript.c:2924` to `:2928`); call the lights component instead.

The unit comes from the source, not from the selection name. Still, never name a km/h speedometer `mph`: the inherited name makes everyone believe the gauge is in the wrong unit. Check whether the art prints a unit at all before arguing about it.

## Which way needles turn

Two unknowns are coupled: where the axis points, and which way the engine turns for a positive sweep. Solving one with the other proves nothing. Take the rule from shipped cars. Eleven cluster animations of four vanilla cars, read from the DayZ 1.29 binarized models with an ODOL reader (`Animations.classes` for the angles, `Animations.axis_data[0][i]` for the resolved axis):

| Car | Animation | Resolved axis | `angle0` | `angle1` | Sweep | Axis | Turns |
|---|---|---|---|---|---|---|---|
| `offroadhatchback` | `IndicatorSpeed` | (0, +0.422, +0.907) | 0 | 190 | +190 | toward driver | clockwise |
| `offroadhatchback` | `IndicatorFuel` | (0, +0.422, +0.907) | 0 | 90 | +90 | toward | clockwise |
| `offroadhatchback` | `IndicatorRPM` | (0, +0.422, +0.907) | 20 | 260 | +240 | toward | clockwise |
| `civiliansedan` | `IndicatorFuel` | (0, -0.458, -0.889) | 40 | -40 | -80 | away | clockwise |
| `civiliansedan` | `IndicatorRPM` | (0, -0.458, -0.889) | 50 | -40 | -90 | away | clockwise |
| `hatchback_02` | `IndicatorFuel` | (0, -0.450, -0.893) | 0 | 44 | +44 | away | counterclockwise |
| `hatchback_02` | `IndicatorRPM` | (0, -0.316, -0.949) | 0 | -270 | -270 | away | clockwise |
| `hatchback_02` | `IndicatorSpeed` | (0, -0.316, -0.949) | 0 | -270 | -270 | away | clockwise |
| `sedan_02` | `IndicatorSpeed` | (0, +0.371, +0.928) | -127 | 115 | +242 | toward | clockwise |
| `sedan_02` | `IndicatorRPM` | (0, -0.371, -0.928) | 125 | -100 | -225 | away | clockwise |
| `sedan_02` | `IndicatorFuel` | (0, -0.371, -0.928) | 44 | -44 | -88 | away | clockwise |

The rule: a positive sweep on an axis pointing at the driver turns clockwise as the driver sees it. In vehicle models +Z points backward (the dashboard sits at minus Z, the driver behind it), so "toward the driver" is Y and Z both positive. Ten of eleven rows agree; the odd one is a 44 degree fuel arc that may be reversed on purpose. The table checks its own premise: with +Z forward the count would be 1 of 11, which shipped clusters rule out.

The current models on `P:\` are ODOL version 56 (for example `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`), which this repo cannot parse, so the table is not checked against today's data. If a cluster built to this rule rests off zero, suspect the dial frame first (`gauge-dial-frame.md`), not the rule.

## What `rpm` is measured against

`rpm` arrives as 0 to 1, and 1.0 is the engine's ceiling, not the last printed number. Whether that ceiling is the last point of `torqueCurve` or `rpmRedline` is not settled (`vehicle-modelcfg-animations.md`, "What the engine feeds the needles"); measure it once in game. On a dial printed 0 to 6 with a ceiling of 6400, "6" sits at 6000 / 6400 = 93.75 percent of the travel, so the sweep is the printed arc divided by that fraction (times 1.0667). Wiring as if the ceiling were 6000 makes the needle wrong across the whole dial, not only at the top.

Compare the painted red zone with the measured engine top before the art is final. On the test quad red starts at 5,000 and the sustained top is 5,805 rpm (404 samples with the engine running), so at full throttle the needle always sits in the red. That is allowed, but decide it.

If the vehicle's top speed passes the last printed number, do not stretch `maxValue` and keep the angles: the needle then reads wrong everywhere. Extend the sweep in proportion into the unpainted gap. With art printed 0 to 120 over 270 degrees (2.25 degrees per km/h), a top of 150 needs 337.5 degrees, and the extra 67.5 fits in the 90 degree gap. Printed numbers stay true at every speed.

## The handlebar that carries the cluster

On a bike or quad the cluster hangs from the handlebar bone, so the handlebar axis matters too. A `drivewheel_axis` 3.4 degrees off vertical (direction (0, +0.9982, -0.0599)) makes grips 0.378 m from the axis rise and fall by 11.5 mm, opposite on each side, at 30 degrees of steer; with an exactly vertical axis that term is zero. The hands do not follow, because the model has no IK and the animation places them relative to the seat. Making the axis vertical through the same point fixed the complaint. Write the handlebar axis vertical unless a measurement says otherwise, and check it as a vector: 3.4 degrees cannot be seen by eye.

When you change the steer sweep, note that `minValue -1 / maxValue 1 / angle0 "rad -30" / angle1 "rad 30"` matches three blocks in a quad's `model.cfg`: `drivingwheel` and both front wheels (`turnfrontleft`, `turnfrontright`, the real steering angle). A blind replace halves the steering, which reads in game as "drives weird". Assert that the edited block is unique.

## Building a new cluster, in order

1. Anchor the dial frame to the model's own right (`gauge-dial-frame.md`). Check: the sign of `<u, light_right - light_left>` is positive.
2. One texture per dial, padded to a power of two, on its own flat `.rvmat`, outside the paint selections. Check: the PAA matches the current art; no dial face in `camo1`.
3. Paint the dial disc and map polar UVs with right to +U and up to -V. Check: the determinant is negative on each disc separately. For the fuel panel see `gauge-fuel-panel.md`. Put new faces and their points in the animated selection in every LOD that has dials.
4. Build the needle in its canonical pose, hub and blade only, in front of the panel (`gauge-needle-part.md`). Check: no needle vertex behind the panel, a drawing of the part, and winding and stored normals matching the discs.
5. Add `<sel>_axis`, the bones and the `Indicator*` classes with `"rad"` angles. Check: both points exist in Memory and the bone hangs from the dashboard.
6. Derive the angles with written value to tick pairs, fit the regular span, `angle0 = rest - theta(min)`, `rpm` over the ceiling. Check: draw the needle over every printed value.
7. Convert textures by content, not by file presence, and check the PBO size (`gauge-dial-art.md`).
8. Before trusting a new render, make it reproduce two known states (`gauge-dial-frame.md`).
9. In game: all three gauges unmirrored with the new faces; the fuel needle visible, between E and F and moving with the tank; with the engine running, speed and rpm needles moving while the painted dial does not turn; needles resting on zero. Look at night or with the dash lights on too, because an inverted stored normal shows only in low light, and a culled part shows only when you look at that part.

## A static verdict does not prove motion

A cluster that looks right parked proves neither that the needles move nor which way. On a test coupe the cluster was accepted parked, and when the car later drove the needles had never moved, frozen at full left, although the sources and wiring matched a quad whose needles did move (measured in game on DayZ 1.30). The needles lived on an interior proxy; where they must live is the vehicle model (`vehicle-modelcfg-animations.md`, "What the engine feeds the needles"). Before closing a gauge task, drive the car and watch each needle. Record what was checked per gauge, because "the dashboard is good" does not say which needle was looked at.
