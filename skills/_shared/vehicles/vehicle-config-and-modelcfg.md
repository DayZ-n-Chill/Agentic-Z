# Car config, block by block

The `config.cpp` class of a drivable car, block by block: what each of the three files owns, the class tree and `SimulationModule`.

Most examples come from two working third-party configs, not vanilla: a four-wheel-drive car built from scratch ("the example 4x4") and a front-wheel-drive quadbike mod ("the reference quad"). Copy their shape, not their numbers. Facts with a `P:\` citation are vanilla. The rest of the car's config is split by subject:

| Question | File |
|---|---|
| `Crew`, lights, sounds, `AnimationSources`, how config, `model.cfg` and the model wire together, keys that do nothing | `vehicle-config-crew-lights-sounds.md` |
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

Calibrate suspension to mass (`vehicle-geometry-and-mass.md`). For comparison the reference quad (front differential locked at 4.1) uses 41000, 2100 and 7200 with travel 0.293 up and 0.051 down at the front, and 40000, 2000 and 7000 with 0.414 and 0.012 at the rear. A vehicle that inherits springs tuned for another mass sits wrong; the measured method for reseating it is in `motorbike-invariants.md`, section "Tuning lessons from an imported bike".
