# Car config: crew, lights, sounds and wiring

The second half of a drivable car's `config.cpp` class: `Crew`, lights, sounds, `AnimationSources`, how config, `model.cfg` and the model wire together, and keys that do nothing. The class tree and `SimulationModule` are in `vehicle-config-and-modelcfg.md`.

Most examples come from two working third-party configs, not vanilla: a four-wheel-drive car built from scratch ("the example 4x4") and a front-wheel-drive quadbike mod ("the reference quad"). Copy their shape, not their numbers. Facts with a `P:\` citation are vanilla.

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
