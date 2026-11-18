# Vehicle geometry and mass

How to build a car's Geometry LOD, where its mass comes from, what makes a car launch or sink on spawn, how to size wheel wells and suspension, and what the separate wheel `.p3d` needs for its collider.

Facts documented by Bohemia Interactive or in the PhysX documentation are marked "per the docs". Measurements were taken on a working third-party quadbike (the reference quad) and on test vehicles built from scratch; they are not read from `P:\`. The rest of the structure is in `vehicle-structural-parity.md`.

## Building the Geometry LOD

A working car's Geometry is several closed convex components, never one hull. The reference quad has 23 chassis components and 4 hubs; a test quad shipped with one `component01` carrying about 90% of the mass. Per the docs:

| Rule | Check |
|---|---|
| Geometry is several closed convex `componentNN` | Object Builder `Find Non-Convexities`, `Find Non-Closed`, `Component Convex Hull`; more than one chassis component |
| Mass sits on every component, the 4 hubs included | Sum the weight per component: none at 0, none above about 60% of the total |
| Named property `autocenter = 0` on the Geometry LOD, and `class = vehicle` | Read the named properties |
| Centre of mass centred left to right, with no large front or rear bias | `CoM.x` near 0. The test quad had `(0, 0.513, +0.399)` against the reference's `(0, 0.474, -0.011)`. |
| Components at least 0.5 m thick; parts under 15 cm do not collide at speed | Apply this to the body away from the wheels; next to the wheels the collision must be narrow (see wheel wells) |
| Hubs `wheel_X_Y_damper_land` are real convex components with mass | Each hub is a closed weighted component |
| No proxies in Geometry | Wheel proxies go in the visual LODs, View Geometry and Fire Geometry |
| Fire Geometry exists | It is required on vehicles |

All six vanilla wheeled vehicles checked carry `class = vehicle` on their Geometry LOD (civiliansedan, sedan_02, hatchback_02, offroadhatchback, offroad_02, truck_01; **model knowledge**). Scripts that assemble a model often set `autocenter` and forget `class`. Set `geo_lod.properties['class'] = 'vehicle'`; it is parity, not the wheel simulation fix (`wheel-simulation-wiring.md`).

Model the collision as boxes sized to each region of the body: the reference quad uses 23 skewed eight-point boxes (a spine about ±0.13 m wide, slabs about ±0.66 m) plus 4 cylinders. Not a convex hull of the whole body, which swallows the wheels, and not arbitrary hulls, which bridge the fenders. The skew of the reference boxes is invisible in game, so do not copy it; spend the effort on clearance and contact.

DayZ cars have no separate PhysX LOD. Arma 3 cars add a 4e13 LOD; the DayZ references (the sedan, the reference quad, a documented 4x4) use Geometry 1e13 only, so do not add a 4e13 LOD.

## Mass lives only in Geometry

Mass, centre of mass and inertia come only from the vertex weights in the Geometry LOD (Object Builder Alt+M). A working car config has no `mass`, `sprungMass`, `centerOfMass` or `geometryClass`; do not try to set mass from config.

A real quad weighs about 1000 kg (the reference quad reads mass 1061.5 and centre of mass `(0, 0.474, -0.011)`), not the 250 or so a procedural hull defaults to. Too little mass makes the physics unstable.

`#Mass#` must sit on the Geometry LOD (1e13) only. Binarize bakes mass from whichever LOD carries `#Mass#`; an all-zero `#Mass#` on Fire Geometry bakes the centre of mass to `(0,0,0)` with zero inertia. `ECE_PLACE_ON_SURFACE` then seats the car by that centre, about 0.48 m too low, the wheels are buried and PhysX throws the car out. py3d writes `#Mass#` on any LOD where a point has `mass != None`, so after every assembly assert that only Geometry has mass, and set `point.mass = None` elsewhere (`p3d-vehicle-killers.md`). Spawn height follows the baked centre of mass (`h` roughly `CoM.y` minus the lowest Geometry point), not the lowest point, LandContact or bounding box, so no geometry change fixes a car baked with a zero centre. `/dayz-p3d-audit` reports it as `ERR_MASS_ONLY_GEOMETRY` (`skills/dayz-p3d-audit/references/vehicle-checks.md`).

To reshape collision without disturbing physics, move existing Geometry points, which keeps each point's `#Mass#`. Regenerating the geometry redistributes mass: moving points kept 1061.5 kg and the centre exactly, while a convex hull rebuild moved the centre's Z from 0.260 to 0.348.

## What makes a car launch or sink on spawn

A car that spawns, steers and makes sound but does not roll, sinks and bounces with no RPT error has wheels whose physics never engage: the wheel is known to config and animation, but contact, suspension and spin are blocked. If it was cloned from a working car, the drivetrain, scripts and `model.cfg` are not the cause; look at the model.

| Cause | Sign | Fix |
|---|---|---|
| `#Mass#` on a LOD other than Geometry | Spawns about half a metre low and is thrown out | Mass on Geometry only (above) |
| Chassis collision inside the wheel | Chassis points 0.16 to 0.19 m from the wheel centre with a 0.34 m tyre; the reference quad keeps 0.43 to 0.46 m | Clear the wheel wells (below); after the fix all four wheels touched the ground at 0.3 s |
| Spawn height | The origin under the ground at spawn (-0.264 m against +0.216 m for the reference quad), wheels buried | Measured, mechanism not settled; compare spawn height with a working car side by side |

Mass distribution is not the launch trigger. A body re-weighted to the reference quad's centre and roll inertia bounced exactly the same, to three digits: a mostly vertical spawn impulse with the same total mass gives the same speed whatever the distribution. Splitting a single hull into components is parity, not the fix. PhysX does throw apart bodies created overlapping, solving the overlap in one step (per the docs), and sharp edges add a large moment on contact (common modding practice). "Flying tanks" is a different effect: a gun barrel that sticks out of the collision hitting the world.

## Wheel wells and wheel size

For each wheel centre (the `*_damper_land` centroid), no chassis collision point may fall inside the tyre radius, the config `radius` (about 0.34 m), not the small `wheelHubRadius`. Aim for the radius plus 0.07 to 0.09 m, as on the references, and keep the gap clear sideways so the well still holds when the wheel moves up under compression. Checking only that the eight-point hub box sits outside the hull misses this.

- The hub `wheel_X_Y_damper_land` is a small convex component, about 0.20 by 0.18 by 0.18 m on the sedan, not a large box; a 0.40 m box reaches almost to the ground.
- `wheelHubRadius` is the hub component's radius (about 0.11 to 0.15: the reference quad 0.11 with a 0.367 tyre, the sedan 0.15), not the tyre radius.
- Small wheels make the body ride low: the sedan's belly sits 0.428 m above the contact plane.
- All checked vanilla cars carry wheel proxies in Fire Geometry identical to the visual ones (the sedan's `sedanwheel.001` to `.005`, hatchback_02, niva, offroad_02). Copy them there with mass 0. The rule that keeps proxies out of Fire Geometry is for item attachments, not wheels.

## Contact diagnostics

Log `WheelHasContact(i)` per wheel and `WheelCountPresent()` for your car and a working one side by side in the test mission (`WheelHasContact`, `WheelCount` and `WheelCountPresent` at `P:\scripts\3_game\vehicles\car.c:286`, `:345` and `:348`). Contact `0000` against `1111` isolates wheels that never touch. With no wheel item attached the engine still simulates colliders from the model, so contact reflects the model's own wheel collision. Logging spawn height side by side finds a placement fault at once, where "flies 38 m" alone does not. Instrument a silent failure with a temporary debug script (wheel count, wheel speed against `EngineGetRPM()`, server against client, contact) instead of changing one thing per test.

## Suspension

Stiffness must hold the mass gravity pushes down. Per the docs, start from `compression = stiffness / 10` and `damping = compression * 3`, then adjust. A documented 4x4 (an order of magnitude anchor only):

```cpp
class Suspension { stiffness=40000; compression=2100; damping=5400; travelMaxUp=0.10; travelMaxDown=0.06; };
wheelHubMass=15;      // kg, used only when no wheel is attached
wheelHubRadius=0.284; // measured from the hub component, never negative
```

Suspension scales with mass: springs from a heavy crawler on a light quad bounce it, and too little mass with springs from a heavier vehicle catapults it. Clone from a vehicle of similar mass. Changing springs does not cure a car that floats or bounces for one of the causes above.

In `model.cfg`, per the docs, damper bones keep `minValue=0` and `maxValue=1` and the travel comes from the offsets:

```cpp
class suspension_damper_1_1 {
    type="translation"; source="damper_1_1"; selection="wheel_1_1_damper";
    axis="wheel_1_1_damper_axis";
    minValue=0.0; maxValue=1.0;        // front; the rear uses maxValue=0.6, visual only
    offset0=0.05;  offset1=-0.35;      // +0.05 above rest to -0.35 compressed
};
// config.cpp AnimationSources: class damper_1_1 { source="user"; initPhase=0.4857; animPeriod=1; }
// initPhase is the damper's resting position: front about 0.486, rear about 0.400
```

The bone chain is damper, steering, wheel at the front and damper, wheel at the rear. The damper `source` matches `animDamper` in the config `Axles` wheels and the `AnimationSources` class.

## The wheel `.p3d` collider

The wheel attachment's own `.p3d` (referenced from its `ProxyVehiclePart` class in `CfgNonAIVehicles`) is not just a wheel with visual LODs. PhysX builds the wheel collider from five points in its Memory LOD. Without them it falls back to the proxy's Geometry, often a 0.20 m cube from a model generator (`_shared/models/generated-model-pipeline.md`), and the wheel ray reaches only 0.10 m below the hub: wheels attach, contact stays 0, the body falls until the chassis hits, bounces grow, and the engine finally logs `Will delete object with !finite or outside world coords`.

Measured on the reference quad's front wheel, Memory LOD at 1e15, one point per selection:

| Selection | Reference value | Meaning | For your wheel |
|---|---|---|---|
| `ce_center` | about `(0, 0, 0)` | Collider centre | Origin |
| `ce_radius` | `(0, 0.37679, 0.40015)` | Radius marker in Y, width marker in Z | `(0, wheel_radius, Z)`, keeping Z about 1.062 times Y |
| `boundingbox_min` | `(-0.19095, -0.3816, +0.38558)` | Min corner, Z positive | `(-width/2, -wheel_radius, +wheel_radius)` |
| `boundingbox_max` | `(+0.20446, +0.39014, -0.38393)` | Max corner, Z negative | `(+width/2, +wheel_radius, -wheel_radius)` |
| `invview` | `(-0.23026, 0, 0)` | Negative X offset | Keep it relative to the width |

`boundingbox_min.Z` is greater than `boundingbox_max.Z` on purpose; do not normalise it. Scale Y and Z by `wheel_radius / 0.38587` and X by `width / 0.39541`. Writing Memory LODs with py3d is covered once in `_shared/py3d-mlod-notes.md`, section "Writing a `.p3d` from a script". Check the five before calling a wheel ready:

```python
mem = next(l for l in p3d.lods if abs(l.resolution - 1e15) < 1e12)
required = {"ce_center", "ce_radius", "boundingbox_min", "boundingbox_max", "invview"}
missing = required - set(mem.selections.keys())
assert not missing, f"wheel proxy Memory incomplete: missing {missing}"
```

`/dayz-p3d-audit` checks this (`skills/dayz-p3d-audit/references/vehicle-checks.md`, Killer 11).

The wheel's Geometry must be a cylinder of about the radius, not a box: a box with half-size equal to the radius has corners at radius times 1.414, 42% too big (a test box reached 0.482 against a 0.34 radius; the reference quad's 24-point cylinder reads 0.340 to 0.366 all round). Build an N-gon in Y and Z, extrude it along X, take its convex hull for outward faces, select it all as `component01`, and add View Geometry (6e15) and Fire Geometry (7e15, selections `component01` and `wheel`). Give the Fire Geometry faces a penetration material such as rubber; an empty material weakens ballistics but does not block spawning.
