# Building a new motorbike

What a new motorbike needs in `config.cpp`, in its script class and in its model, with the vanilla source of each piece and what reads it. The values follow `Motorbike_01_ColorBase`. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`, `motorbikescript.c` means `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, and `motorbike_01.c` is in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\`. The literal vanilla blocks are in `motorbike-config-contract.md`. The script class and what to measure in the model are in `motorbike-forward-contract-script.md`.

## Config

| Piece | Value | Source | Read by |
|---|---|---|---|
| `CfgPatches` | `requiredAddons[] = {"DZ_Data", "DZ_Vehicles_Wheeled", "DZ_Vehicles_Singletrack"};` (a suggested shape) | | Engine, for load order |
| Class | `class MyMod_Bike: MotorbikeScript`, `scope = 2` | `config.cpp:220` | |
| Simulation | `simulation = "motorbike"`, inherited from `Motorbike` | `P:\bin\config.cpp:1486` | Engine |
| Attachments | `{"SparkPlug", "Reflector_1_1", "MyMod_Bike_Wheel_1", "MyMod_Bike_Wheel_2"}` | `config.cpp:225` | Inventory |
| Hidden selections | `{"camo1", "camo_fender", "lights_brake", "lights_front", "lights_rear"}` | `config.cpp:232` | `vehiclelightscomponent.c` |
| Light materials | `frontReflectorMatOn`, `frontReflectorMatOff`, `brakeReflectorMatOn`, `brakeReflectorMatOff`, each an `.rvmat` path | `config.cpp:256` to `:259` | `ConfigGetString` in `P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:77` |
| Speed geometry | `speedGeomActivation = 0.29;`, `speedGeoms[] = {"geotohide"};` | `config.cpp:262` to `:266` | Engine |
| Horn noise | `class NoiseCarHorn { strength = 30.0; type = "sound"; };` | `config.cpp:148` to `:152` | `P:\scripts\4_world\entities\vehicles\components\vehiclehorncomponent.c:86` |

The crew (`config.cpp:52` to `:70`), read by `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:75` to `:104`, which turns the cursor's component into a crew index with `CrewPositionIndex` and starts `StartCommand_Vehicle` on it:

```cpp
class Crew
{
    class Driver
    {
        actionSel = "seat_driver";
        proxyPos = "crewDriver";
        getInPos = "pos_driver";
        getInDir = "pos_driver_dir";
        isDriver = 1;
    };
    class CoDriver: Driver
    {
        actionSel = "seat_driver";
        proxyPos = "crewCoDriver";
        getInPos = "pos_codriver";
        getInDir = "pos_codriver_dir";
        isDriver = 1;
    };
};
```

### Simulation

Two wheels and no `Axles` (`config.cpp:267` to `:382`):

| Class | Keys |
|---|---|
| `Steering` | `tipoverAngle = 50.0`; curves `maxSteeringAngle[]`, `maxLeanAngle[]`, `steerIncreaseSpeed[]`, `directControl[]` |
| `Throttle` | `reactionTime = 0.15`, `defaultThrust = 0.82`, `slopeCoef = 0.75` (`:285` to `:290`) |
| `Brakes` | `Front` on `input = 1` (the lever), `Rear` on `input = 0` (the pedal) |
| `Aerodynamics` | `frontalArea = 0.8`, `dragCoefficient = 0.85` (`:315`, `:316`) |
| `Engine` | `torqueCurve[]`, `rpmIdle = 1200`, `rpmMin = 1400`, `rpmRedline = 6000` (`:327` to `:330`) |
| `Clutch` | `maxTorqueTransfer = 30`, `uncoupleTime = 0.2`, `coupleTime = 0.6` (`:334` to `:336`) |
| `Gearbox` | `type = "GEARBOX_MANUAL"`, `ratios[] = {3.93, 2.43, 0.83}`, `reverse = 2.94` (`:340` to `:342`) |
| `Wheels: Wheels`, `Front: Front` | `maxBrakeTorque = 800`, `wheelHubMass = 10`, `casterAngle = 25.0` (`:352`), `animDamper = "damperfront"`, `inventorySlot = "MyMod_Bike_Wheel_1"`; suspension `stiffness = 5500`, `compression = 600`, `damping = 1150`, `travelMaxUp = 0.066`, `travelMaxDown = 0.066` |
| `Wheels: Wheels`, `Rear: Rear` | `maxBrakeTorque = 1200`, `wheelHubMass = 10`, `driveRatio = 10.2789` (`:369`), `animDamper = "damperback"`, `inventorySlot = "MyMod_Bike_Wheel_2"`; suspension `stiffness = 7000`, `compression = 750`, `damping = 1350`, `travelMaxUp = 0.058`, `travelMaxDown = 0.043` |

### Animation sources

The minimum set (`config.cpp:111` to `:147` and `:383` to `:403`):

- `damper_1` and `damper_2`, `source = "user"`.
- `AnimHitWheel_1` and `AnimHitWheel_2`, `source = "Hit"`, `hitpoint = "HitWheel_1"` or `"HitWheel_2"`, `raw = 1`.
- `HideDestroyed_1_1`, `_1_2`, `_2_1` and `_2_2`, `source = "user"`.
- With a flip-up seat, `SeatDriver`: `source = "user"; initPhase = 0.0; animPeriod = 1.0;`.

### Damage

`GlobalHealth` of 1000 and the zones of `Motorbike_01` (`config.cpp:404` to `:993`, with `GUIInventoryAttachmentsProps` at `:959` to `:992`):

| Zone | Health | Notes |
|---|---|---|
| `Chassis` | 1000 | `componentNames[] = {"dmgZone_chassis"}` |
| `Fender` | 200 | `componentNames[] = {"dmgZone_fender"}`; receives damage from `Front` |
| `Engine` | 1000 | `transferToGlobalCoef = 1`, `inventorySlots[] = {"SparkPlug"}` |
| `Front` | 700 | Passes damage to `Engine`, `Fender` and `Chassis` |
| `Back` | 1000 | Passes damage to `Engine` and `FuelTank` |
| `Reflector_1_1` | 10 | Passes damage to `Front` |
| `FuelTank` | 400 | `componentNames[] = {"dmgZone_fuelTank"}` |

### Wheels and their proxies

Front and rear wheel classes on `MotorbikeWheel` (`config.cpp:154` to `:219`) set `radius`, `width`, `tyreRollResistance`, `tyreRoughness`, `tyreLongitudinalFriction` and `tyreLateralFriction`, each with a `_Ruined` child. Each wheel model gets a proxy class in `CfgNonAIVehicles` (`config.cpp:2323` to `:2357`), following `ProxyMotorbike_01_wheel_1` (`:2326` to `:2333`):

```cpp
class ProxyMyMod_Bike_wheel_1: ProxyVehiclePart
{
    model = "MyMod\data\proxy\mymod_bike_wheel_1.p3d";
    inventorySlot[] = {"MyMod_Bike_Wheel_1"};
};
```
