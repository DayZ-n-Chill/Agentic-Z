# Building a new motorbike: script and model

The script class a new motorbike needs and what to measure in its model, with the vanilla source of each piece. The config is in `motorbike-forward-contract.md`. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`, `motorbikescript.c` means `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, and `motorbike_01.c` is in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\`.

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
