# Car config, block by block

The `config.cpp` class of a drivable car, block by block: what each of the three files owns, the class tree, `SimulationModule`, crew, lights, attachments, wheel and door items, sounds, animation sources, and how config, `model.cfg` and the model wire together.

Most examples come from two working third-party configs, not vanilla: a four-wheel-drive car built from scratch ("the example 4x4") and a front-wheel-drive quadbike mod ("the reference quad"). Copy their shape, not their numbers. Facts with a `P:\` citation are vanilla. The rest of the car's config is split by subject:

| Question | File |
|---|---|
| `model.cfg` skeleton and animations, dashboard needles, reusing a vanilla rig, the crew proxy frame | `vehicle-modelcfg-animations.md` |
| `DamageSystem` zones, window glass, `RefTexsMats[]` and `"hidden"` | `vehicle-damage-and-glass.md` |
| Attachments, cargo, fuel, wheel and door items with their slots and proxies, an engine that will not start, `OnDebugSpawn` | `vehicle-parts-and-start.md` |
| Ruined wheels: script, proxy, repair, in-hands pose, flat tyre radius | `ruined-wheels.md` |

## What each file owns

| File | Owns | Does not own |
|---|---|---|
| `.p3d` | Geometry, LODs, named selections, memory points, proxies, mass and centre of mass (Geometry vertex weights) | Physics values, animation values |
| `config.cpp` | The car class, drivetrain, engine and suspension numbers, crew, damage, lights, cargo, attachments, sounds, `AnimationSources` | Mass, centre of mass, animation axes |
| `model.cfg` | `CfgSkeletons` bones and `CfgModels` animations | Physics, which sources are user driven |

Mass is not a config key (`vehicle-geometry-and-mass.md`). The model structure is in `vehicle-structural-parity.md`.

## The class tree

A drivable car extends `CarScript`: a `scope=0` base that holds the physics (with `model=""` or the real model), then `scope=2` variants.

```cpp
class CarScript;
class MyMod_Car_Base: CarScript
{
    scope = 0;
    displayName = "MyMod Car";
    model = "\MyMod\Car\MyMod_Car.p3d";
    // hiddenSelections, attachments, Crew, SimulationModule, DamageSystem, AnimationSources, Sounds
};
class MyMod_Car: MyMod_Car_Base { scope = 2; };
```

Config class names resolve without case, so the example 4x4's `Carscript` inherits correctly; vanilla spells it `CarScript`. The class name does not have to match the model file; the link is `model=`.

## `SimulationModule`

A complete working block from the example 4x4 (all wheel drive, the mass of a long 4x4):

```cpp
class SimulationModule
{
    drive = "DRIVE_AWD";                    // DRIVE_RWD, DRIVE_FWD, DRIVE_AWD, DRIVE_642; case sensitive
    class Steering
    {
        maxSteeringAngle = 35;
        increaseSpeed[]  = {0,45, 60,25, 100,15};   // {km/h, deg/s}: slower at speed
        decreaseSpeed[]  = {0,90, 60,45, 100,15};
        centeringSpeed[] = {0,0, 15,28, 60,45, 100,60};
    };
    class Throttle { reactionTime = 0.25; defaultThrust = 0.8; gentleThrust = 0.6; turboCoef = 5; gentleCoef = 0.7; };
    class Brake
    {
        pressureBySpeed[] = {0,0.85, 10,0.7, 20,0.5, 40,0.4, 60,0.43, 80,0.46, 100,0.52, 120,0.7};
        reactionTime = 0.25; driverless = 0.1;   // brake with no driver, 0 to 1
    };
    class Aerodynamics { frontalArea = 2.18; dragCoefficient = 0.65; };
    class Engine
    {
        torqueCurve[] = {650,0, 850,110, 1200,150, 2500,200, 4350,160, 7300,0};  // {rpm, Nm}
        inertia = 0.5; frictionTorque = 160; rollingFriction = 0.5; viscousFriction = 0.5;
        rpmIdle = 800; rpmMin = 850; rpmClutch = 1450; rpmRedline = 6150;
    };
    class Clutch { maxTorqueTransfer = 440; uncoupleTime = 0.1; coupleTime = 0.1; };
    class Gearbox { type = "GEARBOX_MANUAL"; reverse = 3.91; ratios[] = {3.6,3.0,2.3,1.45,1.0}; };
    class CentralDifferential { ratio = 1.5; type = "DIFFERENTIAL_LOCKED"; };   // AWD and 642 only
    class Axles
    {
        class Front
        {
            maxBrakeTorque = 3500; maxHandbrakeTorque = 4000;
            wheelHubMass = 15; wheelHubRadius = 0.284;
            class Differential { ratio = 4.0; type = "DIFFERENTIAL_OPEN"; };
            class Suspension { stiffness = 40000; compression = 2100; damping = 5400; travelMaxUp = 0.10; travelMaxDown = 0.06; };
            class Wheels
            {
                class Left  { animTurn="turnfrontleft";  animRotation="wheelfrontleft";  wheelHub="wheel_1_1_damper_land"; animDamper="damper_1_1"; inventorySlot="MyMod_Wheel_1_1"; };
                class Right { animTurn="turnfrontright"; animRotation="wheelfrontright"; wheelHub="wheel_2_1_damper_land"; animDamper="damper_2_1"; inventorySlot="MyMod_Wheel_2_1"; };
            };
        };
        class Rear
        {
            maxBrakeTorque = 1750; maxHandbrakeTorque = 4000;
            wheelHubMass = 15; wheelHubRadius = 0.284;
            class Differential { ratio = 4.0; type = "DIFFERENTIAL_OPEN"; };
            class Suspension { stiffness = 40000; compression = 2100; damping = 5400; travelMaxUp = 0.10; travelMaxDown = 0.06; };
            class Wheels
            {
                class Left  { animTurn="turnbackleft";  animRotation="wheelbackleft";  wheelHub="wheel_1_2_damper_land"; animDamper="damper_1_2"; inventorySlot="MyMod_Wheel_1_2"; };
                class Right { animTurn="turnbackright"; animRotation="wheelbackright"; wheelHub="wheel_2_2_damper_land"; animDamper="damper_2_2"; inventorySlot="MyMod_Wheel_2_2"; };
            };
        };
    };
};
```

Both third-party configs spell the rear right `animTurn` as `turnbacktright`, which does no harm because rear wheels do not steer. `DRIVE_642` is the vanilla truck drivetrain (`drive="DRIVE_642"` on `Truck_01_Base`, `P:\DZ\vehicles\wheeled\config.cpp:18539`, with a locked `CentralDifferential` of `ratio=0.75` at `:18564` to `:18567`).

| Class | Keys | Meaning |
|---|---|---|
| `Steering` | `maxSteeringAngle`, `increaseSpeed[]`, `decreaseSpeed[]`, `centeringSpeed[]` | Each `{km/h, deg/s}` point sets how fast the wheel turns at that speed |
| `Throttle` | `defaultThrust`, `gentleThrust`, `turboCoef`, `gentleCoef`, `reactionTime` | Gentle, default and turbo pedal modes |
| `Brake` | `pressureBySpeed[]`, `reactionTime`, `driverless` | Time to floor the pedal; brake with no driver, 0 to 1 |
| `Aerodynamics` | `frontalArea`, `dragCoefficient`, optional downforce | Drag practically sets top speed; negative drag is not allowed |
| `Engine` | `torqueCurve[]`, `inertia`, `rpmIdle`, `rpmMin`, `rpmClutch`, `rpmRedline` | `inertia` is the real key; `engineMomentum` does not occur in `P:\DZ\vehicles\wheeled\config.cpp` |
| `Clutch` | `maxTorqueTransfer`, `uncoupleTime`, `coupleTime` | Torque in Nm before the clutch slips |
| `Gearbox` | `type`, `reverse`, `ratios[]` | `GEARBOX_MANUAL` or `GEARBOX_AUTOMATIC` |
| `CentralDifferential` | `ratio`, `type` | All wheel drive and 642 only |

`GEARBOX_AUTOMATIC` is native: `enum CarGearboxType` (`P:\scripts\3_game\vehicles\car.c:23` to `:27`) and `GearboxGetMode()` (`:269`). Only `Offroad_02` uses it (`P:\DZ\vehicles\wheeled\config.cpp:21056`); copy its `Gearbox` block and check it live with the diag tool.

Wheel keys: `wheelHub` names the hub memory point and Geometry component (`wheel_X_Y_damper_land`); `animTurn`, `animRotation` and `animDamper` name `model.cfg` animation sources; `inventorySlot` names the wheel slot.

Calibrate suspension to mass (`vehicle-geometry-and-mass.md`). For comparison the reference quad (front differential locked at 4.1) uses 41000, 2100 and 7200 with travel 0.293 up and 0.051 down at the front, and 40000, 2000 and 7000 with 0.414 and 0.012 at the rear. A vehicle that inherits springs tuned for another mass sits wrong; the measured method for reseating it is in `motorbike-invariants.md`, section "Measured lessons from a real import".

## Crew

| Key | Meaning |
|---|---|
| `actionSel` | Named selection in View or Fire Geometry where the get-in action starts |
| `proxyPos` | Proxy selection in View Geometry where the player sits; it needs a bone in the skeleton |
| `getInPos` | Point the player gets in and out at |
| `getInDir` | Second point giving the direction from the first |
| `isDriver` | Marks a driver seat. Vanilla cars set it on one seat (`P:\DZ\vehicles\wheeled\config.cpp:273`), but both motorbike seats set it (`P:\DZ\vehicles\singletrack\config.cpp:60` and `:68`) |

```cpp
class Crew
{
    class Driver   { actionSel="seat_driver";   proxyPos="CrewDriver";   getInPos="pos_driver";   getInDir="pos_driver_dir";   isDriver=1; };
    class CoDriver { actionSel="seat_codriver"; proxyPos="CrewCoDriver"; getInPos="pos_codriver"; getInDir="pos_codriver_dir"; };
    class Cargo1   { actionSel="seat_cargo1";   proxyPos="CrewCargo1";   getInPos="pos_cargo";    getInDir="pos_cargo_dir"; };
};
```

`proxyPos` needs both a proxy in View and Fire Geometry and a bone in `CfgSkeletons` (`vehicle-proxies.md`, `crew-get-in-geometry.md`).

Crew memory points are baked into the model, so a wrong seat costs a full build per guess. A throwaway offline editor worked on a quad: sliders for the crew proxy and `pos_driver` position and yaw, a seated figure about 1.8 m tall, the grips as fixed markers and a live readout, seeded from a working vehicle's points. It places the seat; the seat probe in `crew-get-in-geometry.md` checks it can be hit.

## Lights

The glowing faces are `hiddenSelections` swapped to a lights `.rvmat`, and the `*ReflectorMatOn` and `Off` keys tell `CarScript` which material to swap. The beams sit at memory points (`vehicle-structural-parity.md`). From the example 4x4:

```cpp
hiddenSelections[]={ "light_left","light_right","light_brake_1_2","light_brake_2_2",
    "light_reverse_1_2","light_reverse_2_2","light_1_2","light_2_2","light_dashboard","base","special" };
frontReflectorMatOn="MyMod\data\front_lights_on.rvmat";     frontReflectorMatOff="MyMod\data\body.rvmat";
brakeReflectorMatOn="MyMod\data\brake_lights_on.rvmat";     brakeReflectorMatOff="MyMod\data\body.rvmat";
TailReflectorMatOn="MyMod\data\tail_lights_on.rvmat";       TailReflectorMatOff="MyMod\data\body.rvmat";
ReverseReflectorMatOn="MyMod\data\reverse_lights_on.rvmat"; ReverseReflectorMatOff="MyMod\data\body.rvmat";
dashboardMatOn="MyMod\data\dashboard_lights_on.rvmat";      dashboardMatOff="MyMod\data\body.rvmat";
```

The `_on` material is emissive (`emissive-led-materials.md`; `_shared/models/model-material-file.md`, "Glowing parts"); the `_off` one is the plain body material. `CarScript` swaps them by index, not by name: `hiddenSelections[]` slots 0 to 8 must be front left, front right, brake left, brake right, reverse left, reverse right, tail left, tail right and dashboard (`SELECTION_ID_FRONT_LIGHT_L` onwards, `P:\scripts\4_world\entities\vehicles\carscript.c:174` to `:182`, registered with the material keys at `:230` to `:263`); the example's order above matches (`vehicle-structural-parity.md`). Light switching faults are in `lights.md`.

## Sounds

Reference a vanilla vehicle's sound sets by name rather than redefining them. The example 4x4 borrows the `offroad_*` sets:

```cpp
class Sounds
{
    thrust=0.6; thrustTurbo=1; thrustGentle=0.3; thrustSmoothCoef=0.02; camposSmoothCoef=0.03;
    soundSetsFilter[]={ "offroad_Engine_Offload_Ext_Rpm1_SoundSet", "offroad_Engine_Ext_Rpm0_SoundSet",
        "offroad_Engine_Ext_Broken_SoundSet", "offroad_Rain_Ext_SoundSet",
        "offroad_damper_left_SoundSet", "offroad_damper_right_SoundSet" };
    soundSetsInt[]={ "Offroad_Tires_Asphalt_Fast_General_Int_SoundSet", "Offroad_Wind_SoundSet" };
};
```

Only a unique engine note needs your own `CfgSoundShaders` and `CfgSoundSets`. Borrow `offroad_*` for a truck or SUV, `Hatchback_02_*` or `Sedan_02_*` for a car. The reference quad borrows `Hatchback_02_*` start and horn sounds and defines only its RPM shaders, with `class Sounds` on the `scope=2` variant; on the base also works.

## `AnimationSources`

Dampers and doors are `source="user"`. The sources the simulation provides (`wheelfrontleft`, `turnfrontleft`, `speed`, `rpm`, `fuel`) are not listed.

```cpp
class AnimationSources
{
    class DoorsDriver  { source="user"; initPhase=0; animPeriod=0.5; };
    class DoorsCoDriver: DoorsDriver {}; class DoorsHood: DoorsDriver {}; class DoorsTrunk: DoorsDriver {};
    class damper_1_1   { source="user"; initPhase=0.4857; animPeriod=1; };   // front rest position
    class damper_2_1: damper_1_1 {};
    class damper_1_2   { source="user"; initPhase=0.4002; animPeriod=1; };   // rear rest position
    class damper_2_2: damper_1_2 {};
};
```

A missing damper source logs `unknown animation source damper`.

## How the three files wire together

| Config key | Goes to |
|---|---|
| `animRotation="wheelfrontleft"` | `model.cfg` class `wheel_1_1` with `source="wheelfrontleft"`, driven by the simulation |
| `animTurn="turnfrontleft"` | `model.cfg` class `steering_hub_1_1` with `source="turnfrontleft"` |
| `animDamper="damper_1_1"` | `model.cfg` class `suspension_damper_1_1` with `source="damper_1_1"`, and config `AnimationSources` class `damper_1_1` with `source="user"` |
| `wheelHub="wheel_1_1_damper_land"` | The memory point and Geometry hub component in the `.p3d` |
| `inventorySlot="MyMod_Wheel_1_1"` | The `CfgSlots` slot, the `CarWheel` item and the `CfgNonAIVehicles` proxy |

Every `model.cfg` selection (`wheel_1_1`, `wheel_1_1_steering`, `wheel_1_1_damper`, the `*_axis` points) must exist in the `.p3d`. A break anywhere fails without a log line (no roll, no steering, no suspension) or logs `unknown source`.

## Keys that do nothing

Unknown config keys are ignored without a log, so check a key exists before tuning it.

- No `simulationclass=` in either third-party config or in `P:\DZ\vehicles\wheeled\config.cpp`; do not add one (Arma 3 uses `simulation="carx"`).
- No `mass`, `centerOfMass`, `sprungMass` or `geometryClass` in either config, in `P:\DZ\vehicles\wheeled\config.cpp` or in `P:\DZ\vehicles\singletrack\config.cpp`. `sprungMass` is an Arma 3 key; whether DayZ reads it is not checked.
- No `torqueMax`, `torqueRpm`, `powerMax`, `powerRpm` or `rpmMax` in the vanilla wheeled config; the engine is the `torqueCurve[]` table.
- No `reflectors[]` (an Arma 3 lights feature) in the vanilla wheeled config.
- `CentralDifferential` keys seen are `ratio` and `type` only.
- Offroad Hatchback door slots are exactly `NivaDriverDoors`, `NivaCoDriverDoors`, `NivaHood` and `NivaTrunk` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:209` to `:219`; `NivaHood` also at `:146` and `:160`, `NivaTrunk` at `:189`). Slot lookups and sound set names are case sensitive; a mismatch returns nothing without a clear message.
