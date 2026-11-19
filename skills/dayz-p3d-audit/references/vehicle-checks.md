# Vehicle checks

What `/dayz-p3d-audit` checks on a wheeled vehicle body, and the vehicle faults it cannot see that you measure by hand: wheel slot selections, the wheel's memory points, ride height, how the Geometry LOD is built, mass, crew and the get in chain. Killers 11 to 13 of `p3d-killers.md` are explained here.

The full vehicle build rules belong to the vehicles pack, `_shared/vehicles/`: the field notes on these faults are `_shared/vehicles/p3d-vehicle-killers.md` and the comparison with vanilla is `_shared/vehicles/vehicle-structural-parity.md`. This file covers only what an audit of the `.p3d` can see. Except where a vanilla file is cited, the faults below were measured in game on custom vehicles (a quad bike compared against a working third-party quad, a test car, a helicopter) and their fixes confirmed there; they are not checked on `P:\`.

## What the script checks

A model counts as a vehicle body when any LOD has a selection with `damper` in its name (`wheel_1_1_damper`, `wheel_1_1_damper_land`). A wheel model that is only a proxy on the body has `wheel` selections and no damper, so it is not treated as a body.

| Check | Severity | Needs |
|---|---|---|
| Wheel slot selection missing from the Fire Geometry LOD (`check_wheel_slot_firegeo`) | CRITICAL; WARNING when the selection is there with 0 faces | `--config`, or a `config.cpp` near the model under `--scan-dir` |
| No Fire Geometry LOD on a vehicle body | CRITICAL | the same `config.cpp` |
| Geometry LOD without the named property `class=vehicle` (`check_geometry_class_vehicle`) | CRITICAL | nothing |
| Heavy most detailed Visual LOD on a body: over 16,384 normals or 32,768 points (`check_lod0_vertex_budget`) | WARNING | nothing |
| `#Mass#` on a LOD that is not the Geometry LOD (`ERR_MASS_ONLY_GEOMETRY`) | CRITICAL | the DayZ fork of py3d |

Without a `config.cpp` the wheel slot check does not run, and the output says so. A vehicle body can then print `ALL CHECKS PASSED` while its wheels will never simulate, so always pass `--config` for a vehicle body.

What vanilla shows behind these checks:

- Every wheeled body under `P:\DZ\vehicles\wheeled\` holds the property strings `class` and `vehicle` (13 of 13 body models, for example `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`). Leaving the property out on a custom quad did not stop the wheels simulating, so the finding is parity with vanilla, not the cause of dead wheels.
- A wheel is tied to the model in two steps. The vehicle class names a slot per wheel, `inventorySlot="NivaWheel_1_1"` (`P:\DZ\vehicles\wheeled\config.cpp:1457`), and `CfgSlots` gives that slot a selection: `Slot_NivaWheel_1_1` has `selection="wheel_1_1"` (`P:\scripts\config.cpp:1030` to `:1034`). Vanilla keeps `CfgSlots` in `P:\scripts\config.cpp`, away from the vehicle classes, so a mod that reuses vanilla wheel slots has no `CfgSlots` of its own; the script then prints a NOTE that it could not read the mapping, and you check the selections by hand.
- Script reads the result with `WheelCount()` and `WheelCountPresent()`, the second counting only attached wheels (`P:\scripts\3_game\vehicles\car.c:345` and `:348`).

## Wheel slot selection on the Fire Geometry LOD

The engine binds a wheel slot to the model through the selection named by `CfgSlots` > `<Slot>` > `selection`. That selection must exist in the body's Fire Geometry LOD and hold the wheel proxy faces. If it exists only in Visual LODs, the slot binds as inventory but the wheel never simulates: `WheelCountPresent()` is 0 while `WheelCount()` is N, with no RPT error. The chassis bounces or sinks, the wheels mount as items but do not turn, and the RPM climbs while the speedometer stays near 0.

Fix: add the wheel proxy face to a second selection with the exact name `CfgSlots` expects, keeping the original selection. On the custom quad this took `WheelCountPresent()` from 0 to 4. `check_wheel_slot_firegeo` in `audit_p3d.py` checks it, when it runs with `--config` or a `--scan-dir` that finds a `config.cpp`.

## Wheel model with only `ce_center` in its Memory LOD

Killer 11, a WARNING: a parity check against the common vanilla pattern, run on wheel models only. A wheel proxy `.p3d` (the separate file named by `ProxyVehiclePart` in `CfgNonAIVehicles`, attached to the body through `inventorySlot`) whose Memory LOD holds only `ce_center` differs from most vanilla wheels, which hold five points: `ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max` and `invview`.

Of the 23 wheel models under `P:\DZ\vehicles\wheeled\*\proxy\`, 19 hold all five names as strings (for example `P:\DZ\vehicles\wheeled\offroadhatchback\proxy\nivawheel.p3d`). `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanwheel.p3d` holds `boundingbox_min`, `boundingbox_max` and `invview` but neither `ce_center` nor `ce_radius`, and the Sedan drives; the three `P:\DZ\vehicles\wheeled\truck_02\proxy\truck_02_wheel*.p3d` files show none of the five. So the five points are the common pattern, not a proven engine requirement.

On the custom quad the wheel collider behaved as if built from those points. Without the four missing ones it had the size of the proxy's Geometry LOD, a small 8-vertex cube on the procedural wheels the model pipeline generates (about 0.10 m against a wheel of about 0.34 m). The symptom, with no RPT error:

- `WheelCount()` and `WheelCountPresent()` are both full, no wheel is locked, and attachment, config and the Fire Geometry slot are all right.
- Wheel contact is 0 on every wheel in every frame. The suspension engages once when the vehicle spawns (penetration contact through the Geometry hub), then the body lifts more than about 10 cm and the wheel raycast no longer reaches the ground.
- The body falls free, the chassis Geometry hits the terrain, and the bounce grows with each impact, because with no wheel contact no friction takes energy out. The speedometer swings ever wider until the engine logs `Will delete object with !finite or outside world coords`.

On that quad the collider followed the Memory points, not the Visual LOD: a wheel can have a correctly sized Visual LOD (0.68 m across) and a tiny Geometry hub (about 0.20 m) and still no contact, because the Memory points are incomplete. The script does not check this, so raise it yourself when the symptom is a vehicle that bounces on spawn, no wheel contact, a speedometer that runs away, or the delete message above.

Detection with py3d, run only on a wheel proxy model (the file named by the wheel's `ProxyVehiclePart` class), never on the body:

```python
WHEEL_PARITY = {"ce_center", "ce_radius", "boundingbox_min",
                "boundingbox_max", "invview"}
if is_wheel_proxy:  # set from config.cpp, never from the file name alone
    for lod in p.lods:
        if abs(lod.resolution - 1e15) > 1e12: continue  # Memory only
        missing = WHEEL_PARITY - set(lod.selections.keys())
        if missing:
            flag_warning(f"wheel proxy Memory lacks {missing} (19 of 23 vanilla wheels have all five)")
```

Fix: add the four missing points in the reference wheel's convention (Y vertical, X along the axle, Z with its min and max deliberately swapped). Reference values and scaling are in `_shared/vehicles/vehicle-geometry-and-mass.md`, section "The wheel `.p3d` collider". Write them with py3d; its quirks are in `_shared/py3d-mlod-notes.md`, section "Writing a `.p3d` from a script". The five points carry no weight; each is its own one-vertex selection. See also "Wheel proxy memory points" in `_shared/models/generated-model-rules.md`.

## Wheels placed too low against the body

Killer 12, CRITICAL for wheeled vehicles. A vehicle whose wheels sit too low against the body rides with its belly too close to the ground. `WheelCount()` and `WheelCountPresent()` are full, but wheel contact is 0 on every wheel even at rest, the chassis bounces on the terrain, and the vehicle falls unbalanced or turns over. No RPT error.

Three working references (a third-party quad, vanilla `OffroadHatchback` and `CivilianSedan`) put the tire bottom at or just above the model origin, never below it, and the chassis floor at or above the wheel centre line. The custom quad that failed had its tire bottom at Y = −0.114 and its chassis floor at Y = 0.120, which is 0.107 below its wheel centre of 0.227.

Measure it; do not judge by eye. Compare with a debinarized working reference:

```python
geo = next(l for l in p3d.lods if abs(l.resolution - 1e13) < 1e11)
wheel_center_Y = ...   # Memory wheel_X_X centroid Y (or hub damper_land)
radius = ...           # config Axles -> Wheels.radius
tire_bottom   = wheel_center_Y - radius
chassis_floor = component01_bbox_min_Y(geo)
if tire_bottom < -0.02:
    flag_critical(f"tire bottom {tire_bottom:.3f} below model origin (working refs about +0.01 to +0.05)")
if chassis_floor < wheel_center_Y - 0.05:
    flag_critical(f"chassis floor {chassis_floor:.3f} below wheel-center line {wheel_center_Y:.3f}")
```

The fix raises both the wheel and hub system and the chassis floor to the reference heights (wheel centre, tire bottom and chassis floor measured on the reference with the check above). Raising only the wheels makes the resting clearance worse. The difference from the three references is measured; that it causes the lost wheel contact is not confirmed in game.

## Vehicle Geometry LOD built as one component

Killer 13, a WARNING about construction practice, not the cause of a launch at spawn. A working DayZ car's Geometry LOD is a compound of several closed, convex components, each with mass, on a LOD that carries the named property `autocenter=0`, never one hull holding all the mass. The reference quad has 23 chassis components and 4 hubs; the custom quad had 1 chassis component (`component01`) holding about 90 % of the mass, and a yaw inertia (Izz) of 128.5 against the reference's 350.7.

A car that shoots up the moment it spawns, tumbles, gains energy and is deleted with `Will delete object with !finite or outside world coords` has a different cause: a `#Mass#` tag on a LOD other than the Geometry LOD. Check that first ("`#Mass#` only in the Geometry LOD" below). The quad's launch stopped when that tag was removed; a one-component Geometry LOD and its low inertia were not the cause.

The construction rule for a car's Geometry LOD: convex components; every component's vertices carry weight, and the vehicle's total mass and centre of mass come from those weights; wheel hubs have their own components. In Object Builder: convex components, `autocenter` set to 0, mass on all components, hubs present, centre of mass checked. See `_shared/vehicles/vehicle-geometry-and-mass.md`, section "Building the Geometry LOD".

Measure it against a debinarized working reference:

```python
geo = next(l for l in p3d.lods if abs(l.resolution - 1e13) < 1e11)   # Geometry LOD
comps = components_in(geo)                          # named selections componentNN (chassis) + hubs
chassis = [c for c in comps if c.name.startswith("component")]
if len(chassis) <= 1:
    flag_warning(f"Geometry chassis is {len(chassis)} component; working cars use many "
                 f"convex components (the reference quad has 23). One hull gives low inertia.")
for c in comps:                                     # mass on all components, none near 0, none dominant
    if c.mass <= 0:
        flag_warning(f"component {c.name} has no mass; centre of mass and inertia will be wrong")
    if c.mass > 0.6 * total_mass:
        flag_warning(f"component {c.name} holds {c.mass/total_mass:.0%} of mass (low inertia)")
if geo.properties.get("autocenter") != "0":         # a named property belongs to the LOD
    flag_warning("Geometry LOD missing autocenter=0 (engine may recompute the centre of mass)")
com = center_of_mass(geo)
if abs(com.x) > 0.05:
    flag_warning(f"center of mass X={com.x:.3f} not laterally centered (vehicle may lean)")
```

`autocenter=0` is also killer 3, which the script applies to any `config.cpp` class whose model is this `.p3d` and that sets `autocenter = 0`. On a vehicle the Geometry LOD must carry it as a named property whatever the config says. An MLOD named property belongs to a LOD, not to a selection or component, so one property covers every component; without it the engine recomputes the origin and moves the centre of mass away from the mass you assigned. Rebuild the chassis as several convex components with spread mass together with the ride height fix above; changing one without the other creates a new fault.

## Checks the script does not run

- **`#Mass#` only in the Geometry LOD.** A stray `#Mass#` tag on another LOD (on the quad, an all-zero one on the Fire Geometry LOD) makes binarize take that LOD's mass: the ODOL gets a centre of mass at `(0,0,0)` and zero inertia, `ECE_PLACE_ON_SURFACE` spawns the vehicle about 0.48 m below ground, and the physics ejects it. The DayZ fork of py3d reports it as `ERR_MASS_ONLY_GEOMETRY`, which `audit_p3d.py` prints as CRITICAL; with any other py3d check it by hand. Fix: set `point.mass = None`, not `0.0`, on every LOD that is not the Geometry LOD. See also `_shared/vehicles/vehicle-geometry-and-mass.md`, section "What makes a car launch or sink on spawn".
- **Wheel well clearance against the wheel radius, not the hub.** Measure the chassis to wheel centre distance against the effective wheel radius (a cylinder), not the small hub box. Less than the radius means the physics ejects the body from its own wheels.
- **Crew seats.** `seat_driver` and `seat_codriver` must each sit in their own View Geometry component, and crew proxies must be a proper frame, not an isosceles 90, 45, 45 triangle, or the player sits sideways.
- **Crew proxy shape.** Build a crew proxy as a scalene triangle with an unambiguous frame and calibrate its +Y and +Z against the proxy model it names. Put the anchor vertex at the real seat height; do not copy vertices from another proxy type.
- **The vertex budget counts resolved vertices.** The 16-bit limit is on unique resolved vertices (point, normal and UV), not on `faces × 3`; `check_lod0_vertex_budget` counts them that way.
- **Convex decomposition and mass distribution are separate audits.** Regrouping the same points into other components does not change the centre of mass or the inertia. Do not make centre of mass or inertia hard gates when they come from rebuilt uniform masses or cannot be reached with the geometry.

## The get in chain

For every vehicle that declares `class Crew`, check the whole chain of names at once rather than each file on its own:

- Find the Memory LOD by its resolution near `1e15` and require the `actionSel`, `proxyPos`, `getInPos` and `getInDir` points to exist in the `.p3d`.
- Follow those names through `model.cfg` `sections[]` and `SkeletonBones[]`, then through the matching `config.cpp` `class Crew` fields.
- Require each get in position and direction pair to lie within 1 m of its proxy.
- Match `config.cpp` `AnimationSources` to `model.cfg` `Animations`.

Report every broken link with the files and names at both ends. Keep `actionSel` in `sections[]` as a warning, not a failure, until it has been checked on a vanilla vehicle: one check passed one known good model and rejected one known bad one, which does not settle that rule.
