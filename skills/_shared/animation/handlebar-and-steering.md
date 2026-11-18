# Handlebar and steering wheel rotation (layer 1, config only)

How to make a vehicle part turn with the steering: a car steering wheel, a quad or motorbike handlebar, a boat rudder. It is `model.cfg` plus two memory points; no script and no clip.

This is the visible half of the steering. When the rider's hands also follow the grips through IK, read `rider-pose-solver.md` too and keep the shared angle described at the end of this file.

## What vanilla does

Read from the shipped models:

| Model | Animation | `source` | Value range | Angle |
|---|---|---|---|---|
| `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` | `DrivingWheel` | `steeringwheel` | −1 to 1 | ±3.1416 rad (180 degrees each way) |
| `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d` | `TurnFront` | `turnfront` | −1.571 to 1.571 | the value itself, in radians |

So the car's steering source is `steeringwheel`. `DrivingWheel` is the name of the animation class, not a source, and writing `source = "drivingWheel"` drives nothing. Neither source is declared in the vehicle's `AnimationSources`: the engine supplies both.

## Files touched

- The vehicle's `model.cfg`: the bone in `CfgSkeletons` and a `class Animations` entry in `CfgModels`.
- The vehicle's `.p3d`: the named selection that turns, and the axis as two memory points.

## Skeleton

```cpp
class CfgSkeletons
{
    class MyVehicle_Skeleton
    {
        isDiscrete = 0;
        skeletonInherit = "";
        skeletonBones[] =
        {
            "handlebar", ""        // or "steering_wheel", ""
            // other bones: wheels, dampers, doors
        };
    };
};
```

The steering part's parent is empty: it turns relative to the body.

## Animation

```cpp
class CfgModels
{
    class Default;
    class MyVehicle: Default
    {
        skeletonName = "MyVehicle_Skeleton";
        sectionsInherit = "";
        sections[] = {};
        class Animations
        {
            class DrivingWheel
            {
                type      = "rotation";
                source    = "steeringwheel";   // engine source, -1 full left to +1 full right
                selection = "handlebar";       // named selection in the .p3d
                axis      = "handlebar_axis";  // two memory points
                memory    = 1;
                minValue  = -1;
                maxValue  =  1;
                angle0    = "rad -30";         // degrees after "rad"
                angle1    = "rad 30";
            };
        };
    };
};
```

| Key | Note |
|---|---|
| `source = "steeringwheel"` | No `AnimationSources` entry. Seen in game on a quad mod (not checked on `P:\`): the engine feeds it only when the model also has the standard steering chain of bones, `wheel_X_X_damper` then `wheel_X_X_steering` then `wheel_X_X`, and a second animation cannot be fed from a wheel source. |
| `selection` | The whole steering assembly: bar, grips, levers, mirrors. |
| `axis` | A selection of exactly two points in the Memory LOD. Their order sets the direction of a positive angle. |
| `angle0`, `angle1` | The angle at `minValue` and `maxValue`. `"rad 30"` means 30 degrees, converted to radians; a bare number is radians. Writing `rad 0.39` to mean radians gives 0.39 degrees: a throw too small to see. Start around 25 to 35 degrees for a handlebar and tune in game. |

## The axis

Place the two memory points on the steering stem or column, so the line between them is the real pivot. One sport quad used `(0, 0.748, -0.298)` and `(0, 1.139, -0.384)`: direction about `(0, 0.977, -0.214)`, tilted slightly back like a quad's stem, and on the centre line (`x = 0`) so the steering stays centred.

Add the two points and the selection with the p3d inspector of dayz-model-tools or a py3d script (`_shared/models/py3d-generation.md`); do not send the user to Object Builder for it.

## Sources for the neighbouring parts

Use the names vanilla models use (table in `model-cfg-animations.md`, "Engine sources"): `wheelfrontleft` and its siblings for wheel spin (0 to 6.283, one turn in radians), `turnfrontleft` and `turnfrontright` for the steered hubs, `damper_1_1` and its siblings for suspension travel, `speed`, `rpm` and `fuel` for gauges. A spinning wheel normally uses a model axis type (`rotationX`, `rotationY` or `rotationZ`, whichever is the wheel's axle) with `sourceAddress = "loop"` so it keeps turning past the end of its range.

## One angle for the part and for the rider's hands

When the rider's hands follow the grips through the pose solver in `rider-pose-solver.md`, the angle the part turns must equal the solver's `steerMax`:

```
model.cfg:  angle0 = "rad -30"; angle1 = "rad 30";
solver:     steerMax = the same 30 degrees, in the solver's unit
```

If they drift apart, at full lock the part turns to its angle while the hands stop at the solver's, and a gap opens between hands and grips. Keep the value in one place in the project and check both ends of the range. This does not hold on the 1.30 motorbike graph, whose steering poses span ±45 degrees of wheel angle whatever the model turns; see `rider-pose-solver.md`.

## Check before the build

- The bone is in `skeletonBones[]` and its name equals the `selection`.
- The axis selection exists in the Memory LOD with exactly two points.
- `/dayz-p3d-audit` with `--model-cfg` passes: it checks that the `selection` exists in the Visual LOD and that the axis has exactly two points. It does not read `skeletonBones[]`; check the bone list by hand, or watch for the warning `gen_model_cfg.py` prints when a `selection` is not in `skeletonBones[]`.

## Multiplayer: use the engine source, not a script source

Seen in multiplayer on a quad mod (not checked on `P:\`): `GetSteering()` (`P:\scripts\3_game\vehicles\car.c:182`) returned 0 on the dedicated server, and a steering animation driven from the client through a `user` source was overwritten by server sync and snapped back to 0 in multiplayer. For anything tied to steering use the engine's own `steeringwheel` source, which already reaches every client. Keep `user` sources for what the engine does not drive, such as doors.
