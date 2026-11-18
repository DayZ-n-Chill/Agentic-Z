# Car model.cfg and animations

How a car's `model.cfg` skeleton and animation classes are written, what the engine feeds the dashboard needles, when a vanilla rig can be reused, and how the crew proxy frame and the driver's hands are decided.

Examples come from a working four-wheel-drive car built from scratch ("the example 4x4") and a quadbike mod ("the reference quad"), both third-party configs, not vanilla. Vanilla needle values were read from binarized models with an outside reader (**model knowledge**). The config side is in `vehicle-config-and-modelcfg.md`.

## The skeleton

Each pair is `"bone","parent"`, with an empty parent for the root. Front wheels chain damper, steering, wheel; rear wheels chain damper, wheel. Bone names must match the `.p3d` selection names, and the crew bones must exist because `Crew.proxyPos` needs them.

```cpp
class CfgSkeletons
{
    class MyMod_Car_skeleton
    {
        skeletonInherit=""; isDiscrete=1;
        skeletonBones[]=
        {
            "drivewheel","", "mph","", "rpm","", "dial_rpm","", "dial_temp","", "fuel_1","",
            "doors_driver","", "doors_codriver","", "doors_hood","", "doors_trunk","",
            "crewdriver","", "crewcodriver","", "crewcargo1","",
            "engine","", "engine_rotate","engine",
            "wheel_1_1_damper","", "wheel_1_1_steering","wheel_1_1_damper", "wheel_1_1","wheel_1_1_steering",
            "wheel_2_1_damper","", "wheel_2_1_steering","wheel_2_1_damper", "wheel_2_1","wheel_2_1_steering",
            "wheel_1_2_damper","", "wheel_1_2","wheel_1_2_damper",
            "wheel_2_2_damper","", "wheel_2_2","wheel_2_2_damper"
        };
    };
};
```

## The animation classes

`class MyMod_Car: Default { skeletonName="MyMod_Car_skeleton"; sections[]={...}; class Animations {...} }`, with `sections[]` holding the hidden selections and damage zones. The families a car needs, from the example 4x4 (the damper class is in `vehicle-geometry-and-mass.md`):

```cpp
class Animations
{
    // wheel spin: source from the simulation, looped over a full turn
    class wheel_1_1 { type="rotation"; source="wheelfrontleft";  selection="wheel_1_1"; axis="wheel_1_1_axis";
                      sourceAddress=loop; minValue=0.0; maxValue=6.2831855; angle0=0.0; angle1=6.2831855; };
    class wheel_2_1 { type="rotation"; source="wheelfrontright"; selection="wheel_2_1"; axis="wheel_2_1_axis";
                      sourceAddress=loop; minValue=0.0; maxValue=6.2831855; angle0=0.0; angle1=-6.2831855; };
    // steering, front only, on the *_steering bone
    class steering_hub_1_1 { type="rotation"; source="turnfrontleft"; selection="wheel_1_1_steering"; axis="wheel_1_1_steering_axis";
                             minValue=-1.5707964; maxValue=1.5707964; angle0=-1.5707964; angle1=1.5707964; };
    // steering wheel, dials, doors
    class DrivingWheel { type="rotation"; source="steeringwheel"; selection="drivewheel"; axis="drivewheel_axis";
                         minValue=-1.0; maxValue=1.0; angle0=1.9415927; angle1=-1.9415927; };
    class IndicatorSpeed { type="rotation"; source="speed"; selection="mph"; axis="mph_axis"; minValue=0.0; maxValue=160.0; angle0=0.0; angle1=-4.5361256; };
    class IndicatorRPM   { type="rotationZ"; source="rpm"; selection="rpm"; axis="rpm_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=-1.5707964; };
    class IndicatorFuel  { type="rotation"; source="fuel"; selection="fuel_1"; axis="fuel_1_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=-1.5707964; };
    class DoorsDriver    { type="rotation"; source="doorsdriver"; selection="doors_driver"; axis="doors_driver_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=1.3962634; };
};
```

Wheel spin uses `sourceAddress=loop` over a full turn; this 4x4 negates `angle1` on the right because its wheel axes are mirrored, while cars with uniform axes keep one `angle1` (`vehicle-proxies.md`, section "Wheel spin direction"). Steering turns the `*_steering` selection up to a quarter turn either way. Every animation needs its two-point `*_axis` selection in Memory, or it does nothing and logs nothing; `/dayz-p3d-audit` checks this.

Two traps, measured in game on a quad:

- In `angle0` and `angle1`, `"rad N"` takes N in degrees: `rad` is the config parser's degrees to radians function. `rad 0.45` turns about half a degree and looks frozen; `rad 30` turns 30 degrees. A bare number such as `-4.5361256` is radians. Both are valid; never mix them in one file.
- `GetSteering()` is client only and the server returns 0. A cosmetic steering animation driven by a `source="user"` set from the client is overwritten by server sync and snaps back in multiplayer. Use the engine's own `source="steeringwheel"`, already synced, for anything tied to steering, and keep `source="user"` for dampers and doors.

## What the engine feeds the needles

From the binarized vanilla `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`:

| Car | Class | Source | Type | Max | `angle0` | `angle1` | Bone |
|---|---|---|---|---|---|---|---|
| offroadhatchback | `IndicatorSpeed` | `speed` | rotation | 120 | 0 | 190 degrees | `dial_speed`, root |
| offroadhatchback | `IndicatorRPM` | `rpm` | rotation | 1.0 | 20 degrees | 260 degrees | `dial_rpm`, root |
| offroadhatchback | `IndicatorFuel`, `IndicatorCoolant` | `fuel`, `coolant` | rotation | 1.0 | 0, 85 degrees | 90, 0 degrees | `dial_fuel`, `dial_temp` |
| civiliansedan | `IndicatorSpeed` | `speed` | translation | 200 | | | `dial_speed` |
| civiliansedan | `IndicatorRPM` | `rpm` | rotation | 1.0 | 50 degrees | -40 degrees | `dial_rpm` |

1. `speed`, `rpm`, `fuel` and `coolant` come from the engine; vanilla declares no `AnimationSources` for them.
2. `speed` is on the speedometer scale, km/h like `GetSpeedometer()` (`P:\scripts\3_game\vehicles\car.c:102`), so `maxValue` is the top number painted on the dial.
3. `rpm` arrives scaled 0 to 1. Which engine rpm maps to 1.0, `EngineGetRPMMax` (the end of `torqueCurve[]`) or `rpmRedline`, the model does not say; on one quad they differed by 1 rpm. Design the sweep as `angle1 = angle0 + painted_sweep × (D / painted_top)` and measure D once in game, logging `EngineGetRPM`, `EngineGetRPMMax` and `EngineGetRPMRedline` (`car.c:221` to `:227`) with a photo of the needle at cut-off.
4. `angle0` applies at `minValue`, so the needle mesh need not rest on the painted zero: vanilla rests the rpm needle 20 degrees before it. Keeping the mesh at a fixed rest, such as 12 o'clock, and carrying the offset in `angle0` gives a free check: with the engine off, a needle still at 12 o'clock means the animation did not bake (bone missing from `skeletonBones[]`, empty selection, or class dropped by binarize).
5. The needle axis is two Memory points on the pivot along the dial normal; 1 m apart avoids a degenerate axis (the example 4x4 uses 1 mm). Compare the pseudovector `angle1 × unit(axis_dir)` with the hatchback: an axis pointing from the dial toward the driver with a positive `angle1` turns clockwise for the driver. The 4x4 points its axis away and uses a negative `angle1`, giving the same result, so compare pseudovectors, never raw signs (`animation-sign-and-axis.md`).
6. Vanilla `dial_*` bones hang from the root because the cluster sits on the dashboard. On a quad or bike the cluster rides the handlebar: make the needle bones children of `drivewheel` and give `drivewheel` all the handlebar and cluster faces, or the needles stay behind when the bars turn.
7. A needle animated inside a proxy sub-model stays still in game (measured on a test car); keep needle selections in the main model.

The sign rule and D are not yet confirmed in game. The full needle workflow is in `gauge-needles.md`.

## Reusing a vanilla rig

A mod can reuse a vanilla rig by overriding `GetAnimInstance()` in its script class (the reference quad returns `VehicleAnimInstances.V3S`). `VehicleAnimInstances` is fixed (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1` to `:15`): `CIVVAN=0`, `V3S=1`, `SEDAN=2`, `HATCHBACK=3`, `BUS=4`, `S120=5`, `MULTICAR=6`, `GOLF=7`, `HMMWV=8`, `ZODIAC=9`, and since 1.30 `MOTO1=10` and `MOTO2=11`. Return the instance that matches the model; a wrong value shows as a missing get-in pose or clipping, not a crash.

Returning a value alone does not prove the vanilla `model.cfg` fits your model; check that its selection names match yours. For a car built from scratch, write the full `model.cfg`; the example 4x4 drives with its own.

## The crew proxy frame

`Crew.proxyPos` names a three-vertex proxy in View Geometry. Its frame comes from sorting the triangle's angles, the rule the proxy editor of `/dayz-model-tools` follows:

| Vertex | Role |
|---|---|
| Widest angle | Anchor, the proxy's position |
| Middle angle | Local +Y |
| Smallest angle | Local +Z |

For a crew proxy the target is +Y toward the front of the vehicle and +Z up. Match the frame to the crew model the proxy references. Vanilla cars reference `crew_driver` and `crew_cargo` (`proxy:\dz\vehicles\wheeled\proxies\crew_driver`), for which +Y points forward; the reference quad references `bus_driver` and `bus_cargo`, and its co-driver's +Y points to the rear. Copying that triangle into a car using the vanilla crew models seats the player facing backwards. The triangle shape and seat height rules are in `crew-get-in-geometry.md`.

The driver's hands on the wheel or bars come from the player's animation set chosen by `GetAnimInstance()` (a quad can use a quad set from a third-party animation mod), not from IK or vehicle memory points. Neither a test quad nor the reference quad has hand points, and hand placement cannot be edited in the `.p3d`. Fix wrong hands in the animation set.

## Limits of the headless seat probe

The seat probe casts `DayZPhysics.RaycastRV` (`P:\scripts\3_game\global\dayzphysics.c:199`), whose `contactComponent` out parameter is compared with the seat's component. Measured in game on a quad:

- With no client connected, `RaycastRV` returns no hit; the mission must connect a client.
- A large `radius` crosses into the next component and returns the wrong id; use about 0.05.
- Express the ray offset in local space through `ModelToWorld`; the vehicle spawns pitched and rolled, so a fixed world offset misses.
- The seated posture cannot be measured headless. The probe proves which seat get-in resolves to, not how the seated player looks; check that by eye in game.
