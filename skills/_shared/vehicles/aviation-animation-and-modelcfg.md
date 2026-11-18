# Aircraft animations and damage zones

How a scripted aircraft drives its control surfaces, dials, dampers and propeller through `AnimationSources` and `model.cfg`, which damage zones it adds over a car, and which vanilla seat animation set each airframe reuses.

The examples come from LM_Planes (Workshop `3730564764`), whose configs are the source; they are mod practice, not vanilla, except where a `P:\` line is cited. The general rules are in `_shared/animation/model-cfg-animations.md` and `_shared/animation/animation-sources.md`.

## Animation sources in config

Every flight control is a `"user"` source that script drives. `initPhase = 0.5` puts a surface at neutral; dials use a short `animPeriod` so the needle keeps up:

```cpp
class AnimationSources
{
    class elevator_1_1 { source = "user"; initPhase = 0.5; animPeriod = 0.5; };
    class elevator_2_1: elevator_1_1 {};
    class aileron_1_1: elevator_1_1 {};
    class aileron_2_1: elevator_1_1 {};
    class rudder_1_1: elevator_1_1 {};
    class gear_1_1 { source = "user"; initPhase = 0; animPeriod = 2.5; }; // 2.5 s to retract
    class dial_compass { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_horizon_pitch { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_horizon_bank { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_volt { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_altitude { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class damper_1_1 { source = "user"; initPhase = 0.5; animPeriod = 1; };
};
```

Script sets them with `SetAnimationPhase("elevator_1_1", value)` from `UpdateControlSurfaceAnimations(dt)`; `aviation-script-performance.md` shows how to skip calls that change nothing.

## Animation classes in model.cfg

The classes sit in `CfgModels.<Aircraft>.class Animations`. A dial driven by script, a wheel driven by the engine, and a damper:

```cpp
class dial_horizon_bank
{
    type = "rotation";
    source = "dial_horizon_bank"; // a custom source
    selection = "dial_horizon_bank";
    axis = "dial_horizon_bank_axis";
    sourceAddress = clamp;        // a dial stops at the ends
    minValue = -1;
    maxValue = 1;
    angle0 = 3.14;
    angle1 = -3.14;
    memory = true;
};
class wheel_1_1
{
    type = "rotation";
    source = "wheelfrontleft";    // an engine source
    selection = "wheel_1_1";
    axis = "wheel_1_1_axis";
    sourceAddress = loop;         // a wheel turns without end
    minValue = 0.0;
    maxValue = 6.2831855;         // 2 pi
    angle0 = 0.0;
    angle1 = -6.2831855;
    memory = 1;
};
class damper_1_1
{
    type = "translation";
    source = "damper_1_1";
    axis = "damper_1_1_axis";
    offset0 = 0.0;
    offset1 = 0.35;               // upward suspension travel
    memory = 1;
};
```

The tail wheel damper `damper_2_2` uses a different range, `offset0 = -0.2` and `offset1 = -0.40`. Pair each translation damper with a `damper_susp_X_Y` rotation for the swing of the spring mount.

## Dial sources

| Kind | Sources | Naming |
|---|---|---|
| Engine sources, read from the simulation | `rpm` (`dial_rpm`), `fuel` (`dial_fuel`), `coolant` (`dial_temp`), `speed` (`dial_speed`) | The source differs from the bone |
| Script sources, set with `SetAnimationPhase` | `dial_altitude`, `dial_volt`, `dial_compass`, `dial_horizon_bank`, `dial_horizon_pitch` | The source has the bone's name |

## sourceAddress

| Value | Use |
|---|---|
| `clamp` | Dials: the needle stops at the end of its range |
| `loop` | Wheels and the compass: turning without end |
| `mirror` | Back and forth motion; the Catalina and Patty Wagon use it for wipers and dial wobble |

`isDiscrete` is not an animation key. It belongs to the `CfgSkeletons` skeleton class, `1` for mechanical parts such as vehicles and `0` for organic movement such as a creature, and has nothing to do with `sourceAddress` (`_shared/animation/model-cfg-animations.md`).

## The propeller

LM_Planes spins the propeller from a wheel source:

```cpp
class rotor_1_1
{
    type = "rotation";
    source = "wheelfrontright"; // turns with the front right wheel, not the engine
};
```

On a `CarScript` aircraft the wheel sources come for free, so the propeller turns with the front right wheel. To drive it from the engine instead, point the bone at a `"user"` source and set it from script. Do not use `dBodySetAngularVelocity` for this: it spins the whole physics body, not a model part (`P:\scripts\1_core\proto\enphysics.c:165`). The `rotor_1_1_blur` bone carries the blurred propeller and is shown or hidden by script, with no animation class.

Twin engine models name their bones differently: the DC-3 uses `rotor_1_2` and `rotor_center2`, the Catalina `rotor_2_1` and `rotor_center_2`. Pick one scheme for a new mod and keep to it.

## Control surface angles

| Surface | Range |
|---|---|
| Elevator | plus or minus 0.40 rad, about 23 degrees |
| Aileron | plus or minus 0.40 rad, with `angle0` and `angle1` signs swapped against the elevator |
| Rudder | plus or minus 0.27 rad, about 15 degrees |

`minValue` and `maxValue` are -1 and 1; script writes a value in that range.

## Damage zones

The aircraft lists these in `sections[]`:

```cpp
sections[] =
{
    "camo1",
    "dmgzone_body", "dmgzone_back", "dmgzone_chassis", "dmgzone_front",
    "dmgzone_flaps_backleft", "dmgzone_flaps_backright",
    "dmgzone_flaps_frontleft", "dmgzone_flaps_frontright",
    "dmgzone_wings_backleft", "dmgzone_wings_backright",
    "dmgzone_wings_frontleft", "dmgzone_wings_frontright",
    "dmgzone_wings_rudder", "dmgzone_window_back",
    "dmgzone_window_front", "dmgzone_window_left", "dmgzone_window_right",
    "dmgzone_lights"
};
```

Over a car it adds four wing parts and four flaps (front and back, left and right), the rudder counted as a wing part, and four cockpit windows. The zone names script reads on every car, `Engine` and `FuelTank`, still apply (`damage.md`).

## Seat animations

`GetAnimInstance()` returns one of the vanilla sets in `VehicleAnimInstances` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`): `CIVVAN`, `V3S`, `SEDAN`, `HATCHBACK`, `BUS`, `S120`, `MULTICAR`, `GOLF`, `HMMWV`, `ZODIAC`, `MOTO1` and `MOTO2`. None is made for an aircraft, so pick by cockpit size: tight and small is `GOLF`, a normal cockpit is `SEDAN`, a large cabin is `V3S`.

| Aircraft | Set |
|---|---|
| Cessna180 | `GOLF` |
| Spitfire | `GOLF` |
| Catalina | `SEDAN` |
| StuntPlane | `SEDAN` |
| Tigermoth, every variant | `SEDAN` |
| Z37_Bumblebee | `SEDAN` |
| DC-3 | `V3S` |
| Patty_Wagon | `V3S` |
