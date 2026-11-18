# model.cfg skeletons and animations

How the bones and the `class Animations` block in a mod's `model.cfg` are laid out, which units the values use, and how names must line up with the `.p3d` and `config.cpp`.

## Who writes what

The file is shared with `dayz-object-builder`. The animation specialist writes the bone entries for the moving parts (`skeletonBones[]`) and the `class Animations` block inside the model's `CfgModels` class. `dayz-object-builder` keeps the rest: the skeleton class itself and its inheritance, `sections[]`, the named selections and the LOD setup in the `.p3d`.

## How it fits together

A controller, the `source`, outputs a value. An `Animations` entry maps that value onto a transform (rotate, translate or hide) of a named `selection`, usually around an `axis`. For script driven motion the source is a `user` source and script sets its value with `SetAnimationPhase`. No clip, no graph, no Workbench: an agent writes all of it.

| File | Holds |
|---|---|
| `model.cfg` | The skeleton (bones) and the `class Animations` transforms. |
| `config.cpp` | `class AnimationSources`, only for `user` sources (`animation-sources.md`). |
| script `.c` | `SetAnimationPhase("<source name>", phase)` (`script-hooks.md`). |

## Layout

Key names below are the Binarize input format. Vanilla does not ship `model.cfg` text on `P:\`, so the layout is format knowledge; the names and values in the next section are what vanilla models store.

```cpp
class CfgSkeletons
{
    class MyMod_Bunker_Skeleton
    {
        skeletonInherit = "";
        isDiscrete = 0;
        skeletonBones[] =
        {
            "door_1", "",        // bone, then its parent ("" for none)
            "door_1_handle", "door_1"
        };
    };
};

class CfgModels
{
    class Default;
    class MyMod_Bunker: Default          // class name = the .p3d file name without extension
    {
        skeletonName = "MyMod_Bunker_Skeleton";
        sections[] = {};
        class Animations
        {
            class Door_1_Rotate
            {
                type = "rotation";
                source = "door_1";       // config source name; see animation-sources.md
                selection = "door_1";    // bone name = named selection in the .p3d
                axis = "door_1_axis";    // two point selection in the Memory LOD
                memory = 1;
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = "rad 90";       // radians; "rad 90" converts degrees
            };
        };
    };
};
```

`skeletonBones[]` is a flat list of pairs: each bone, then its parent bone or `""`. A child bone moves with its parent, so a handle that turns on a door goes under the door bone.

The key is `isDiscrete`, not `discrete`: 1 for mechanical parts, 0 for organic movement such as a creature. `skeletonInherit` names a parent skeleton whose bones this one adds to, or `""`.

### Animation types

| `type` | What it does | Extra keys |
|---|---|---|
| `rotation` | Turns the bone around the axis. | `angle0`, `angle1` (radians) |
| `rotationX`, `rotationY`, `rotationZ` | Turns around a model axis instead of a memory axis. | `angle0`, `angle1` |
| `translation` | Slides the bone along the axis. | `offset0`, `offset1` (in axis lengths) |
| `translationX`, `translationY`, `translationZ` | Slides along a model axis. | `offset0`, `offset1` |
| `hide` | Hides the bone once the phase reaches `hideValue`. | `hideValue` |

Keys of an entry, from the same format documentation:

| Key | Meaning |
|---|---|
| `source` | The controller: an engine source name, or the name of a class in `AnimationSources`. |
| `selection` | The named selection (bone) that moves. It must be in the skeleton's `skeletonBones[]`. |
| `axis` | A named selection of two memory points that defines the axis. |
| `begin`, `end` | Two named points instead of `axis`, giving an oriented axis. |
| `memory` | Whether the axis is in the Memory LOD. Default 1. |
| `minValue`, `maxValue` | The source values mapped to the start and the end of the move. |
| `minPhase`, `maxPhase` | The reverse mapping: the phase at the source's minimum and maximum. |
| `sourceAddress` | `"clamp"` (default), `"loop"` or `"mirror"`: what happens outside the range. A spinning wheel uses `"loop"`. |
| `angle0`, `angle1` | Start and end angle in radians. `"rad 90"` converts 90 degrees; a bare `90` is 90 radians. |
| `offset0`, `offset1` | Start and end offset for translations, in axis lengths. |
| `hideValue` | The value at which a `hide` animation hides the selection. |

A `hide` in vanilla: the barrel lids hide at 0.6, and script sets phase 1 to hide a lid and 0 to show it (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:148` sets `Lid` to 1 when the barrel opens).

No vanilla model checked here uses the types `translationModelX`, `translationModelY`, `translationModelZ` or `direct`; do not write them.

## What vanilla models store

Read from the shipped models on `P:\DZ\`. Each row is one animation as the game loads it.

| Model | Animation | Source | Value range | Result | Bone and axis names in the model |
|---|---|---|---|---|---|
| `P:\DZ\gear\camping\fence.p3d` | `Wall_Gate_Rotate` | `user` | 0 to 100 | rotation, 0 to 1.7453 rad (100 degrees) | skeleton `fence_skeleton`, bones `wall_gate`, `wall_interact`, axis `rotate_axis` |
| `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d` | `Doors5` | `doors5` | 0 to 1 | rotation, 0 to minus 1.5708 rad (90 degrees the other way) | bone `doors5`, axis `doors5_axis`, sound point `doors5_action` |
| `P:\DZ\gear\containers\55galDrum.p3d` | `Lid`, `Lid2` | `lid`, `lid2` | 0 to 1 | hide at 0.6 | skeleton `55galDrum_skeleton`, bones `lid`, `lid2` |
| `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` | `DrivingWheel` | `steeringwheel` | minus 1 to 1 | rotation, 3.1416 rad (180 degrees) each way | the steering wheel |
| same | `SeatDriver`, then `SeatDriverRot` | `seatdriver` for both | 0 to 0.5, then 0.5 to 1 | two moves played one after the other | the driver seat |
| same | `wheel_1_1` | `wheelfrontleft` | 0 to 6.283 | one full turn | a wheel |
| `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d` | `TurnFront` | `turnfront` | minus 1.571 to 1.571 | rotation by minus the value (value 1.571 turns it minus 1.571 rad) | the front fork and handlebar |

What this shows:

- **Angles are radians.** `angle1 = 90` turns the part 90 radians, which spins it many times. Write `1.5708` or `"rad 90"`. The number after `rad` is degrees: `"rad 0.39"` is 0.39 degrees, too small to see.
- **Several entries can share one source.** The seat's two animations split the source's range into 0 to 0.5 and 0.5 to 1, so one source plays a slide and then a turn, and plays them back in reverse when it returns.
- **Engine sources need no config class.** `steeringwheel`, `wheelfrontleft` and `turnfront` are not declared in any vehicle `AnimationSources`; the engine supplies them (see `animation-sources.md`). `DrivingWheel` is the animation's name, not a source.
- **The value range is yours to choose.** Fence runs 0 to 100 so script can pass degrees: `fence.c:12` sets `GATE_ROTATION_ANGLE_DEG = 100` and `fence.c:498` calls `SetAnimationPhase("Wall_Gate_Rotate", 100)`. A phase is only meaningful inside `minValue` to `maxValue`.
- **A negative angle opens the other way.** Mirror a door by changing the sign, not the bone.
- **Hide works on a threshold.** The barrel lids hide at 0.6, so phase 1 hides and phase 0 shows; `Lid2` starts at phase 1 (hidden) in `P:\DZ\gear\containers\config.cpp:110`.
- **Names are stored in lower case.** The model holds `lid` while `config.cpp` says `class Lid` (`P:\DZ\gear\containers\config.cpp:101`), so matching ignores case. Keep the case identical anyway so a reviewer can grep it.
- **A model source of `user` means the animation's own name is the source.** Fence stores `Wall_Gate_Rotate` with source `user`, and its config class `Wall_Gate_Rotate` (`P:\DZ\gear\camping\config.cpp:4450`) is the name script passes (`fence.c:498`). The barrel and house doors name the source directly instead (`lid`, `doors5`).
- **Animation name and source can differ.** The house model's `Doors1` animation uses source `doorstwin1`, the config door class `DoorsTwin1` (`P:\DZ\structures\residential\config.cpp:7359`). Script and doors find animations by source; `SetAnimationPhase` takes the source name.

## Engine sources

Sources the engine drives need no `AnimationSources` entry. Besides the rows in the table above, the vanilla vehicles use these, read from the shipped models:

| Animation in the model | `source` | Value range | Model |
|---|---|---|---|
| `steering_hub_1_1`, `steering_hub_2_1` | `turnfrontleft`, `turnfrontright` | −1.571 to 1.571 | `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` |
| the other wheels | `wheelfrontright`, `wheelbackleft`, `wheelbackright` | 0 to 6.283 | same |
| `suspension_*` | `damper_1_1`, `damper_2_1`, `damper_1_2`, `damper_2_2` | 0 to 1 | same |
| `IndicatorSpeed`, `IndicatorRPM`, `IndicatorFuel`, `IndicatorCoolant` | `speed` (0 to 120), `rpm`, `fuel`, `coolant` | 0 to 1 unless noted | same |
| `DoorsDriver`, `DoorsCoDriver`, `DoorsHood`, `DoorsTrunk` | `doorsdriver`, `doorscodriver`, `doorshood`, `doorstrunk` | 0 to 1 | same |
| `wheel_1`, `damper_1`, `Kickstand` | `wheelfront`, `damperfront`, `kickstand` | | `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d` |

The door, seat and damper sources are `user` sources declared in the car's `AnimationSources`; the steering, wheel spin, wheel turn and gauge sources are supplied by the engine (`animation-sources.md`, "Vehicles").

The Bohemia `model.cfg` documentation for the older Real Virtuality games lists these engine sources (not checked for DayZ; several are aircraft and tank sources DayZ has no use for): `wheel`, `drivingWheel`, `speed`, `fuel`, `rpm`, `direction`, `time`, `clockHour`, `clockMinute`, `clockSecond`, `gear`, `altBaro`, `altRadar`, `horizonBank`, `horizonDive`, `vertSpeed`, `aileron`, `aileronB`, `aileronT`, `aoa`, `elevator`, `flap`, `rotor`, `rudder`, `speedBrake`, `damper`, `mainGun`, `mainTurret`, `rotorH`, `rotorV`, `rotorHDive`, `rotorVDive`, `hatchCommander`, `hatchDriver`, `hatchGunner`, `obsGun`, `obsTurret`, `turretDir`, `wheelL`, `wheelR`, `reload`, `revolving`, `compassArrow`, `compassCover`, `compassPointer`, `pedals`, `support`, `gmeter`. Before using one, find it in a shipped vanilla model as the tables here do. The vanilla car's steering source is `steeringwheel`; `DrivingWheel` is only the name of its animation.

## Naming checklist

1. Every bone in `skeletonBones[]` is a named selection in every visual LOD that moves, and in the Geometry, FireGeometry and ViewGeometry LODs where those parts should move with it.
2. Every `axis` is a selection of exactly two points in the Memory LOD.
3. Every `source` matches a class in the item's `AnimationSources` or the building's `Doors`. If the source is `user`, the animation's class name must match that class instead (see `animation-sources.md`).
4. The `CfgModels` class name matches the `.p3d` file name, and `skeletonName` matches the `CfgSkeletons` class.
5. One moving part, one bone. A part that moves with another part is a child bone of it.

Items 1, 2, 4 and 5 are Binarize rules, not something a vanilla file on `P:\` shows; the vanilla models above follow them (bone `doors5` with axis `doors5_axis`).

Adding a missing selection or the two axis points to an MLOD `.p3d` is script work for the p3d inspector of dayz-model-tools or a py3d script (`_shared/models/py3d-generation.md`), checked with `/dayz-p3d-audit`; offer it instead of sending the user to Object Builder. A binarized model has to be converted to MLOD by the user first.

## Limits and measured behaviour

Measured in game or tool behaviour; not checked on `P:\`.

- **Which way a positive angle turns.** Right handed around the axis from its first memory point to its second, the points taken in index order (measured in game on DayZDiag 1.29). With the axis toward +Z, +X moves toward +Y.
- **A child rotation composes with its parent's.** A part that folds on another folding part works when it is a child bone of it. Checked with rays on a leaf that folds on a folding part: blade tips cut at x = ±3.15 m against ±3.21 m predicted.
- **Chained segments.** Several entries with different `minValue` to `maxValue` segments over one clamped source play as one sequence, and play back in reverse when the source returns.
- **A sub-piece of a proxy cannot be animated in place.** Animations move whole selections and whole proxies. Split the moving piece into its own proxy or selection.
- **A mod that derives from another mod's model** needs its own `.p3d`, its own `model.cfg` and its own `model=` entry to add animations; inheriting the config class alone binds no new skeleton.

Steering parts: `handlebar-and-steering.md`. Checking that a source exists: `animation-sources.md`.
