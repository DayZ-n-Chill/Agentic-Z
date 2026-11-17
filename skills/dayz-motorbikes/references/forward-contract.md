# Forward contract for a new motorbike

The full specification for a new motorbike in DayZ 1.30. Each element is marked `[EXACT]` (read in the cited vanilla file), `[DESIGN]` (the recommended shape for a mod) or `[UNVERIFIED]` (cannot be read from the text sources), and names what consumes it. Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol.

---

## 1. Configuration Contract (config.cpp)

### Patch Declaration
- [DESIGN] `class CfgPatches { class MyBike { requiredAddons[] = {"DZ_Data", "DZ_Vehicles_Wheeled", "DZ_Vehicles_Singletrack"}; }; };`
  - *Consumer*: Engine (class load order).

### Main Entity in CfgVehicles
- [EXACT] `class MyBike: MotorbikeScript` (`P:\DZ\vehicles\singletrack\config.cpp:220`).
  - `scope = 2;`
  - `simulation = "motorbike";` (inherited from `Motorbike`, `P:\bin\config.cpp:1486`).
  - `attachments[] = {"SparkPlug", "Reflector_1_1", "MyBike_Wheel_1", "MyBike_Wheel_2"};` (`config.cpp:225`).
  - `hiddenSelections[] = {"camo1", "camo_fender", "lights_brake", "lights_front", "lights_rear"};` (`config.cpp:232`).
  - `speedGeomActivation = 0.29;` and `speedGeoms[] = {"geotohide"};` (`config.cpp:258-262`).
  - *Consumer*: Enfusion engine and `vehiclelightscomponent.c`.

### `class Crew` Block
- [EXACT] Seat definitions (`config.cpp:52-70`):
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
  - *Consumer*: `actiongetintransport.c:81-100` and `Transport.CrewMember()`.

### `class SimulationModule` Block
- [EXACT] 2-wheel structure without `Axles` (`config.cpp:263-378`):
  - `class Steering`: `tipoverAngle = 50.0;`, curves `maxSteeringAngle[]`, `maxLeanAngle[]`, `steerIncreaseSpeed[]`, `directControl[]`.
  - `class Throttle`: `reactionTime = 0.15;`, `defaultThrust = 0.82;`, `slopeCoef = 0.75;`.
  - `class Brakes`:
    - `class Front { input = 1; pressureBySpeed[] = {0,0.85, ...}; };` (front brake lever).
    - `class Rear { input = 0; pressureBySpeed[] = {0,0.95, ...}; };` (rear brake pedal).
  - `class Aerodynamics`: `frontalArea = 0.8;`, `dragCoefficient = 0.85;`.
  - `class Engine`: `torqueCurve[]`, `rpmIdle = 1200;`, `rpmMin = 1400;`, `rpmRedline = 6000;`.
  - `class Clutch`: `maxTorqueTransfer = 30;`, `uncoupleTime = 0.2;`, `coupleTime = 0.6;`.
  - `class Gearbox`: `type = "GEARBOX_MANUAL";`, `ratios[] = {3.93, 2.43, 0.83};`, `reverse = 2.94;`.
  - `class Wheels: Wheels`:
    - `class Front: Front`: `maxBrakeTorque = 800;`, `wheelHubMass = 10;`, `casterAngle = 25.0;`, `animDamper = "damperfront";`, `inventorySlot = "MyBike_Wheel_1";`, `class Suspension { stiffness = 5500; compression = 600; damping = 1150; travelMaxUp = 0.066; travelMaxDown = 0.066; };`.
    - `class Rear: Rear`: `maxBrakeTorque = 1200;`, `wheelHubMass = 10;`, `driveRatio = 10.2789;`, `animDamper = "damperback";`, `inventorySlot = "MyBike_Wheel_2";`, `class Suspension { stiffness = 7000; compression = 750; damping = 1350; travelMaxUp = 0.058; travelMaxDown = 0.043; };`.

### Animation Sources (`AnimationSources`)
- [EXACT] Declare minimum sources (`config.cpp:111-147, 379-399`):
  - `damper_1` and `damper_2` (`source = "user";`).
  - `AnimHitWheel_1` and `AnimHitWheel_2` (`source = "Hit"; hitpoint = "HitWheel_1/2"; raw = 1;`).
  - `HideDestroyed_1_1` through `_2_2` (`source = "user";`).
  - If flip-up seat is present: `SeatDriver` (`source = "user"; initPhase = 0.0; animPeriod = 1.0;`).

### Damage System (`DamageSystem`)
- [EXACT] Define `GlobalHealth` (1000 HP) and DamageZones of `Motorbike_01` (`config.cpp:400-989`, with `GUIInventoryAttachmentsProps` at `:955-988`):
  - `Chassis`: 1000 HP, `componentNames[] = {"dmgZone_chassis"}`.
  - `Fender`: 200 HP, `componentNames[] = {"dmgZone_fender"}` (transfer target for `Front`).
  - `Engine`: 1000 HP, `transferToGlobalCoef = 1;`, `inventorySlots[] = {"SparkPlug"}`.
  - `Front`: 700 HP, transfers to Engine, Fender, and Chassis.
  - `Back`: 1000 HP, transfers to Engine and FuelTank.
  - `Reflector_1_1`: 10 HP, transfers to Front.
  - `FuelTank`: 400 HP, `componentNames[] = {"dmgZone_fuelTank"}`.

### Horn Noise
- [EXACT] `class NoiseCarHorn { strength = 30.0; type = "sound"; };` (`config.cpp:148-152`).
  - *Consumer*: `vehiclehorncomponent.c:86` (`LoadFromPath`).

### Wheel Classes in CfgVehicles and Proxies in CfgNonAIVehicles
- [EXACT] Front and rear wheels derived from `MotorbikeWheel` (`config.cpp:154-219`):
  - Define `radius`, `width`, `tyreRollResistance`, `tyreRoughness`, `tyreLongitudinalFriction`, `tyreLateralFriction`.
  - Create ruined wheel classes `_Ruined`.
- [EXACT] Proxies in `CfgNonAIVehicles` (`config.cpp:2316-2350`):
  - `class ProxyMyBike_wheel_1: ProxyVehiclePart { model = "MyMod\data\proxy\mybike_wheel_1.p3d"; inventorySlot[] = {"MyBike_Wheel_1"}; };`, following the vanilla pattern of `config.cpp:2319-2326`.

---

## 2. Script Contract (4_World)

The Enforce Script class in `scripts/4_World/Entities/Vehicles/MyBike.c`:

```c
class MyBike extends MotorbikeScript
{
    void MyBike()
    {
        // [EXACT] Collision coefficients calibrated not to instantly kill the player
        m_VehicleContactDamageCoef = 0.03;   // P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:5
        m_CrewContactDamageCoef    = 0.018;  // motorbike_01.c:6

        // [EXACT] Engine SoundSet string binding (from P:\DZ\sounds\hpp\config.cpp:384304-384341)
        m_EngineStartOK   = "Motorbike_01_engine_start_SoundSet";
        m_EngineStartFuel = "Motorbike_01_engine_failed_start_fuel_SoundSet";
        m_EngineStop      = "Motorbike_01_engine_stop_SoundSet";
        m_EngineStopFuel  = "Motorbike_01_engine_stop_fuel_SoundSet";

        // [EXACT] Lights and horn registration in modular components
        m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Motorbike_01LightProfileFront()));
        m_LightsComponent.RegisterLight("Rear",  new VehicleLightData(new Motorbike_01LightProfileRear()));
        m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "Motorbike_01_Horn_Short_SoundSet");
        m_HornComponent.RegisterSound(VehicleHornMode.LONG,  "Motorbike_01_Horn_SoundSet");

        // [EXACT] Engine block position in model space
        SetEnginePos("0 0.3 -0.06"); // motorbike_01.c:25
    }

    // [EXACT] Rider animation profile in vehicles.agf (10 = MOTO1, 11 = MOTO2)
    override int GetAnimInstance()
    {
        return VehicleAnimInstances.MOTO1; // motorbike_01.c:50
    }

    // [EXACT] Directional get-in and get-out (left / right)
    override bool HasDirectionalInOutAction()
    {
        return true; // motorbike_01.c:55
    }

    // [EXACT] motorbike_01.c:58-69: driver (posIdx 0) -> 0 = GetIn_L, 1 = GetIn_R; every other seat -> 0
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

    // [EXACT] 3rd person camera parameters (ID 32)
    override float GetTransportCameraDistance()
    {
        return 2.5; // motorbike_01.c:40
    }

    override vector GetTransportCameraOffset()
    {
        return "0 1.3 -0.25"; // motorbike_01.c:45
    }

    // [EXACT] Magneto / kick-start bike: needs no battery to start
    override bool NeedElectricitySourceDevice()
    {
        return false; // motorbike_01.c:35
    }
}
```

---

## 3. WHAT NEEDS TO BE MEASURED IN THE P3D

Since binary `.p3d` files cannot be read in plain text, the modder **must measure** the following mandatory elements on their 3D model before compiling the addon, with `/dayz-p3d-audit` (MLOD source models only) or py3d (`scripts/tools/py3d/`):

### A. Skeleton Bones in `model.cfg`
1. **`drivewheel` [MANDATORY]**: The front fork and handlebars must have this exact name. `motorbikescript.c:1107` executes `GetBoneIndex("drivewheel")` to attach the headlight cone. If the bone is named differently, the headlight will not rotate with steering.
2. **`damperfront` and `damperback`**: names passed by config in `animDamper` (`config.cpp:80, 88`); they must exist as `model.cfg` animations with their bone [UNVERIFIED: vanilla ships no `model.cfg` text for these models on `P:\`; the animations read from the binary models are in `vanilla-p3d-anatomy.md`].
3. **`wheelfront`/`wheelback` and `turnfront`/`turnback`**: rotation (`animRotation`) and turning (`animTurn`) animations for each wheel, along with `wheelHub` names `wheel_1_damper_land` and `wheel_2_damper_land` (`config.cpp:75-90`).

### B. Required Memory Points in LOD Memory
Names verified in script: lights `motorbikescript.c:69-71`, `engine` `:181`, `ptcExhaust_end`/`ptcExhaust_start` `:183, 187`, `ptcDustPos`/`ptcEnginePos` `:199-200`, `refill` `transport.c:112-113` and `actionfillfuel.c:13`; crew points come from `class Crew` (`config.cpp:52-70`).
1. **Lights**:
   - `light_1_1` (headlight origin) and `light_1_1_dir` (normal vector where headlight focuses).
   - `light_1_2_reverse` (origin for rear tail and brake light).
2. **Crew and Mounting**:
   - `seat_driver` (driver seat selection for cursor interaction).
   - `crewDriver` and `crewCoDriver` (points where player proxies are seated).
   - `pos_driver` and `pos_driver_dir` (position and orientation where player walks to get on).
   - `pos_codriver` and `pos_codriver_dir`.
3. **Particle Effects (VFX)**:
   - `engine` (position for water drowning detection).
   - `ptcExhaust_start` and `ptcExhaust_end` (exhaust smoke emission vector).
   - `ptcEnginePos` (smoke from overheated or ruined engine).
   - `ptcDustPos` (dust cloud kicked up behind vehicle).
4. **Refueling**:
   - `refill` (fuel cap position consumed by `ActionFillFuel`).

### C. Geometric LODs
1. **LOD Geometry**:
   - Main chassis collision box.
   - Component named `"geotohide"` containing the stand or kickstand, toggled at speed by `speedGeomActivation`.
2. **LOD View Geometry**:
   - Convex for occlusion calculation and proxy positioning on server.
3. **LOD Fire Geometry**:
   - Components named `dmgZone_chassis`, `dmgZone_fender`, `dmgZone_engine`, `dmgZone_front`, `dmgZone_back`, `dmgZone_fuelTank`, `dmgZone_lights_1_1` paired with `DamageSystem` damage zones.
4. **LOD ViewPilot (res 1100, a visual LOD)**, optional:
   - None on the vanilla motorbikes (`vanilla-p3d-anatomy.md`, parsed from their ODOLs, not checked in game).
   - Add one only for geometry meant for the seat alone, such as closures over the gaps the rider sees through the fairing (`skills/_shared/vehicles/view-pilot-and-first-person.md`, SP-469).
