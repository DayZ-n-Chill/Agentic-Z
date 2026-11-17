# Config driven animation (layer 1)

The text animation system: `model.cfg`, `config.cpp` and a script call moving a named selection of one `.p3d`. No clip, no graph, no Workbench. An agent writes all of it.

The short, vanilla checked version of these rules is in the animation pack: `skills/_shared/animation/model-cfg-animations.md`, `skills/_shared/animation/animation-sources.md` and `skills/_shared/animation/script-hooks.md`. This file adds the full key list, the engine sources and the diagnostics.

Vanilla ships `model.cfg` only inside the binarized `.p3d` files, so there is no vanilla `model.cfg` text on `P:\`. Key names below are the Binarize input format (the Bohemia `model.cfg` documentation, not checked on `P:\`); values quoted from vanilla were read out of the shipped models.

## How it fits together

A controller, the `source`, outputs a value. An `Animations` entry maps that value onto a transform (rotate, translate or hide) of a named `selection`, usually around an `axis`. For script driven motion the source is a `user` source and script sets its value with `SetAnimationPhase`.

Three files, and the names must match across all three:

| File | Holds |
|---|---|
| `model.cfg` | The skeleton (bones) and the `class Animations` transforms. |
| `config.cpp` | `class AnimationSources`, only for `user` sources. |
| script `.c` | `SetAnimationPhase("<source name>", phase)`. |

## Animation types

| `type` | Effect |
|---|---|
| `rotation` | Rotate around an axis given by an axis selection or by `begin` and `end` points. |
| `rotationX`, `rotationY`, `rotationZ` | Rotate around a model axis. |
| `translation` | Slide along an axis. |
| `translationX`, `translationY`, `translationZ` | Slide along a model axis. |
| `hide` | Hide the selection once the value reaches `hideValue`. Vanilla: the barrel lids hide at 0.6, and script sets phase 1 to hide a lid and 0 to show it (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:148` sets `Lid` to 1 when the barrel opens). |
| `translationModelX/Y/Z`, `direct` | Named in some community guides. Not confirmed in any primary source or vanilla model; do not write them. |

## Keys of an `Animations` entry

| Key | Meaning |
|---|---|
| `source` | The controller: an engine source name, or the name of a class in `AnimationSources`. |
| `selection` | The named selection (bone) that moves. It must be in the skeleton's `skeletonBones[]`. |
| `axis` | A named selection of two memory points that defines the axis. |
| `begin`, `end` | Two named points instead of `axis`, giving an oriented axis. |
| `memory` | Whether the axis is in the Memory LOD. Default true. |
| `minValue`, `maxValue` | The source values mapped to the start and the end of the move. |
| `minPhase`, `maxPhase` | The reverse mapping (phase at source minimum and maximum). |
| `sourceAddress` | `"clamp"` (default), `"loop"` or `"mirror"`: what happens outside the range. |
| `angle0`, `angle1` | Start and end angle in radians. `"rad 90"` converts 90 degrees; a bare `90` is 90 radians. |
| `offset0`, `offset1` | Start and end offset for translations, in axis lengths. |
| `hideValue` | The value at which a `hide` animation hides the selection. |

The `.p3d` side, adding the selection or the two axis points, is script work on the MLOD model with the dayz-p3d-inspector or dayz-model-pipeline skills, checked with `/dayz-p3d-audit`. Offer to do it instead of sending the user to Object Builder.

### Rotation sign and chained segments

Measured in game (DayZDiag 1.29.163709), not checked on `P:\`:

- A positive angle turns right handed around the axis from the first memory point to the second, the points taken in index order in model coordinates. With the axis toward +Z, +X moves toward +Y.
- Several entries with different `minValue` to `maxValue` segments over one clamped source play as one sequence, and play back in reverse when the source returns.
- A child rotation under a parent rotation in `skeletonBones[]` composes correctly, for example a leaf that folds on a part that also folds. Checked with rays: blade tips cut at x = ±3.15 m against ±3.21 m predicted.

## `class AnimationSources` in `config.cpp`

Needed only for sources script drives. Engine sources work without it.

```cpp
class AnimationSources
{
    class Door1
    {
        source = "user";   // script sets the phase
        animPeriod = 1;    // time per unit of phase
        initPhase = 0;     // phase at spawn
    };
};
```

- The class name is the source name. Use it as `source` in the `model.cfg` animation and pass it to `SetAnimationPhase`. Keep the animation's own class name identical to it, so the two can never be confused.
- What phase 0 and phase 1 mean is yours to decide per object through `angle0` and `angle1` or `hideValue`. A hide that should start hidden uses `initPhase = 1`, as the barrel's second lid does (`P:\DZ\gear\containers\config.cpp:110`).
- `animPeriod` is time per unit of phase: one value for both directions.

## Engine sources

Sources the engine drives need no `AnimationSources` entry. What vanilla DayZ vehicles use, read from the shipped models:

| Animation in the model | `source` | Value range | Model |
|---|---|---|---|
| `DrivingWheel` | `steeringwheel` | −1 to 1 | `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` |
| `wheel_1_1` and the other wheels | `wheelfrontleft`, `wheelfrontright`, `wheelbackleft`, `wheelbackright` | 0 to 6.283 | same |
| `steering_hub_1_1`, `steering_hub_2_1` | `turnfrontleft`, `turnfrontright` | −1.571 to 1.571 | same |
| `suspension_*` | `damper_1_1`, `damper_2_1`, `damper_1_2`, `damper_2_2` | 0 to 1 | same |
| `IndicatorSpeed`, `IndicatorRPM`, `IndicatorFuel`, `IndicatorCoolant` | `speed` (0 to 120), `rpm`, `fuel`, `coolant` | 0 to 1 unless noted | same |
| `DoorsDriver`, `DoorsCoDriver`, `DoorsHood`, `DoorsTrunk` | `doorsdriver`, `doorscodriver`, `doorshood`, `doorstrunk` | 0 to 1 | same |
| `SeatDriver`, `SeatCoDriver` | `seatdriver`, `seatcodriver` | 0 to 1 | same |
| `TurnFront`, `wheel_1`, `damper_1`, `Kickstand` | `turnfront`, `wheelfront`, `damperfront`, `kickstand` | −1.571 to 1.571 for `turnfront` | `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d` |

The door, seat and damper sources are `user` sources declared in the car's `AnimationSources` (`DoorsDriver` at `P:\DZ\vehicles\wheeled\config.cpp:353`, `SeatDriver` at `:1509`, `damper_1_1` at `:1521`, which the wheel names with `animDamper` at `:1456`). The steering, wheel spin, wheel turn and gauge sources are not declared anywhere in that config: the engine supplies them.

The Bohemia `model.cfg` documentation for the older Real Virtuality games lists these engine sources (not checked for DayZ; several are aircraft and tank sources DayZ has no use for): `wheel`, `drivingWheel`, `speed`, `fuel`, `rpm`, `direction`, `time`, `clockHour`, `clockMinute`, `clockSecond`, `gear`, `altBaro`, `altRadar`, `horizonBank`, `horizonDive`, `vertSpeed`, `aileron`, `aileronB`, `aileronT`, `aoa`, `elevator`, `flap`, `rotor`, `rudder`, `speedBrake`, `damper`, `mainGun`, `mainTurret`, `rotorH`, `rotorV`, `rotorHDive`, `rotorVDive`, `hatchCommander`, `hatchDriver`, `hatchGunner`, `obsGun`, `obsTurret`, `turretDir`, `wheelL`, `wheelR`, `reload`, `revolving`, `compassArrow`, `compassCover`, `compassPointer`, `pedals`, `support`, `gmeter`. Before using one, find it in a shipped vanilla model as the table above does. Note that the vanilla car's steering source is `steeringwheel`; `DrivingWheel` is only the name of its animation.

## Skeleton and model classes in `model.cfg`

```cpp
class CfgSkeletons
{
    class MySkeleton
    {
        skeletonInherit = "";      // or the name of a parent skeleton
        isDiscrete = 0;
        skeletonBones[] =
        {
            "bone1", "",           // bone, then its parent ("" for none)
            "bone2", "bone1"
        };
    };
};

class CfgModels
{
    class Default;
    class MyModel: Default         // the .p3d file name without extension
    {
        skeletonName = "MySkeleton";
        sectionsInherit = "";
        sections[] = {};
        class Animations
        {
            class Door1
            {
                type = "rotation";
                source = "Door1";
                selection = "door";
                axis = "door_axis";
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = "rad 90";
            };
        };
    };
};
```

The key is `isDiscrete`, not `discrete`. Use 1 for mechanical parts that should not be smoothed between LOD bones and 0 for organic movement.

## Script interface

On `Entity` (`P:\scripts\3_game\entities\entity.c`): `SetAnimationPhase(string animation, float phase)` at :15 and `GetAnimationPhase(string animation)` at :12. The full call table and the two vanilla patterns to copy are in `skills/_shared/animation/script-hooks.md`.

- A `user` source moves toward the phase you set over `animPeriod`.
- Where a selection is now, with animations applied: `GetSelectionPositionLS`, `GetSelectionPositionMS` and `GetSelectionPositionWS` (`P:\scripts\3_game\entities\object.c:863` to `:865`). Where it was modelled, with no animation applied: `GetSelectionBasePositionLS(string name)` (`:871`). The difference is how far the part has moved.
- Change state on the side that owns it, normally the server, and let it reach clients. A purely cosmetic local toggle can run on the client.

## Diagnosing a `user` source: a read phase does not prove movement

`GetAnimationPhase(src) == 1.0` before the first `SetAnimationPhase(src, 1)` does not prove the part is at phase 1. A source that is not registered on that object can read the same way. Before blaming the phase:

1. List the sources with `GetNumUserAnimationSourceNames()` and `GetUserAnimationSourceName(int index)` (`P:\scripts\3_game\entities\entity.c:17`, `:19`) and confirm `src` is among them.
2. Compare on the same model with a source that does move something, for example a rotor proxy. A selection made of the model's own faces on a bone can fail to move where a proxy on that bone does; for doors, consider making the door a proxied sub-model.

Keep the probe read only. Do not call `SetAnimationPhase(door, 0)` to see whether a source exists: it changes live state. If the door was open, a cached open state in the mod's own script may not restore it, leaving it shown closed while the logic says open until the next toggle. Test writing through the real open and close action with logging added.

The second point and the cache trap were seen in game on one vehicle mod; they are not checked on `P:\`.
