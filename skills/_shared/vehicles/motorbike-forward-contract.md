# Building a new motorbike

What a new motorbike needs in `config.cpp`, in its script class and in its model, with the vanilla source of each piece and what reads it. The values follow `Motorbike_01_ColorBase`. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`, `motorbikescript.c` means `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, and `motorbike_01.c` is in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\`. The literal vanilla blocks are in `motorbike-config-contract.md`.

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

## Script class

```c
// scripts/4_World/MyMod/Vehicles/MyMod_Bike.c
class MyMod_Bike extends MotorbikeScript
{
    void MyMod_Bike()
    {
        // Contact damage tuned so a graze does not kill the rider (motorbike_01.c:5, :6)
        m_VehicleContactDamageCoef = 0.03;
        m_CrewContactDamageCoef    = 0.018;

        // Engine sound sets (P:\DZ\sounds\hpp\config.cpp:386137 to :386174)
        m_EngineStartOK   = "Motorbike_01_engine_start_SoundSet";
        m_EngineStartFuel = "Motorbike_01_engine_failed_start_fuel_SoundSet";
        m_EngineStop      = "Motorbike_01_engine_stop_SoundSet";
        m_EngineStopFuel  = "Motorbike_01_engine_stop_fuel_SoundSet";

        // Lights and horn on their components (motorbike_01.c:16, :17, :24, :25)
        m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Motorbike_01LightProfileFront()));
        m_LightsComponent.RegisterLight("Rear",  new VehicleLightData(new Motorbike_01LightProfileRear()));
        // Light materials: the number is the hiddenSelections index (motorbike_01.c:19 to :22)
        m_LightsComponent.RegisterSelection("FrontOn",  {new VehicleLightSelectionData(3, "frontReflectorMatOn")});
        m_LightsComponent.RegisterSelection("FrontOff", {new VehicleLightSelectionData(3, "frontReflectorMatOff")});
        m_LightsComponent.RegisterSelection("BrakeOn",  {new VehicleLightSelectionData(2, "brakeReflectorMatOn")});
        m_LightsComponent.RegisterSelection("BrakeOff", {new VehicleLightSelectionData(2, "brakeReflectorMatOff")});
        m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "Motorbike_01_Horn_Short_SoundSet");
        m_HornComponent.RegisterSound(VehicleHornMode.LONG,  "Motorbike_01_Horn_SoundSet");

        SetEnginePos("0 0.3 -0.06"); // engine position in model space, motorbike_01.c:27
    }

    // Rider set in vehicles.agf: 10 = MOTO1, 11 = MOTO2 (motorbike_01.c:45)
    override int GetAnimInstance()
    {
        return VehicleAnimInstances.MOTO1;
    }

    // Get on and off from the left or right (motorbike_01.c:50)
    override bool HasDirectionalInOutAction()
    {
        return true;
    }

    // Driver: 0 plays GetIn_L, 1 plays GetIn_R; every other seat 0 (motorbike_01.c:55 to :66)
    override int GetSeatAnimationTypeDirectional(int posIdx, int directionIndex)
    {
        if (posIdx == 0)
        {
            if (directionIndex == 0)
                return 0;
            else
                return 1;
        }
        return 0;
    }

    // Third-person camera, camera type 32 (motorbike_01.c:35, :40)
    override float GetTransportCameraDistance()
    {
        return 2.5;
    }

    override vector GetTransportCameraOffset()
    {
        return "0 1.3 -0.25";
    }

    // A kick-start bike needs no battery (motorbike_01.c:30)
    override bool NeedElectricitySourceDevice()
    {
        return false;
    }
}
```

## What to measure in the model

A binary `.p3d` cannot be read as text, so check these on the mod's own model before packing, with `/dayz-p3d-audit` (MLOD models only) or py3d (`scripts/tools/py3d/`).

### Bones and animations

- `drivewheel` on the fork and handlebars, exactly that name. `GetBoneIndex("drivewheel")` attaches the headlight to it (`motorbikescript.c:1122`); with another name the light does not turn with the bars.
- `damperfront` and `damperback`, the names `animDamper` passes (`config.cpp:80`, `:88`). They must exist as `model.cfg` animations with their bones. Vanilla ships no `model.cfg` text for these models on `P:\`, so this is not checked there; the animations read from the binarized models are in `motorbike-vanilla-p3d-anatomy.md`.
- `wheelfront`, `wheelback`, `turnfront` and `turnback`, the spin (`animRotation`) and steer (`animTurn`) animations per wheel, with the hubs `wheel_1_damper_land` and `wheel_2_damper_land` (`config.cpp:75` to `:90`).

### Memory points

The script reads these names: the lights (`motorbikescript.c:69` to `:71`), `engine` (`:181`), `ptcExhaust_end` and `ptcExhaust_start` (`:183`, `:187`), `ptcDustPos` and `ptcEnginePos` (`:199`, `:200`), and `refill` (`P:\scripts\3_game\vehicles\transport.c:112` and `:113`; `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:13`). The crew points come from `class Crew`.

| Point | Purpose |
|---|---|
| `light_1_1`, `light_1_1_dir` | Headlight origin and the direction it points |
| `light_1_2_reverse` | Origin of the tail and brake light |
| `crewDriver`, `crewCoDriver` | Where the player proxies sit |
| `pos_driver`, `pos_driver_dir`, `pos_codriver`, `pos_codriver_dir` | Where the player walks to get on, and which way they face |
| `engine` | Position for the drowning check |
| `ptcExhaust_start`, `ptcExhaust_end` | Exhaust smoke direction |
| `ptcEnginePos` | Smoke from an overheated or ruined engine |
| `ptcDustPos` | Dust behind the bike |
| `refill` | Fuel cap, used by `ActionFillFuel` |

`seat_driver` is the selection the cursor hits to get on.

### LODs

- Geometry: the main frame collision, plus a component named `geotohide` holding the kickstand, switched off at speed by `speedGeomActivation`.
- View Geometry: convex, for occlusion and for placing proxies on the server.
- Fire Geometry: components `dmgZone_chassis`, `dmgZone_fender`, `dmgZone_engine`, `dmgZone_front`, `dmgZone_back`, `dmgZone_fuelTank` and `dmgZone_lights_1_1`, matching the damage zones.
- View Pilot (resolution 1100, a visual LOD), optional. The vanilla bikes have none (`motorbike-vanilla-p3d-anatomy.md`, read from their binarized models, not checked in game). Add one only for geometry meant for the seat alone, such as closing the gaps the rider sees through the fairing (`view-pilot-and-first-person.md`).
