# A complete car `config.cpp` and `model.cfg`, block by block

The full `CarScript` config class and the matching `model.cfg` (skeleton and animations) of a drivable car, shown on a working from-scratch 4x4 and compared with a quad bike, a DayZ Expansion vehicle and vanilla.

> Status: three kinds of content, told apart as follows.
> - **Vanilla.** A citation written with its full `P:\` path was opened on the vanilla data (a 1.30 build).
> - **Third-party mod config, not vanilla, not checked on `P:\`.** The "example 4x4" (the `Landrover_*` classes: an AWD car built from scratch), the "reference quad" (a FWD quad bike mod) and the DayZ Expansion UAZ. Their values are working mod configs, quoted as examples to copy the shape from, not as vanilla numbers.
> - **Measured in game or offline on mod builds.** Each entry says what was measured and on which DayZ build. Those measurements were not repeated here.
>
> `[unverified]` marks a point that is not established: do not build on it without testing. "Invariant N" means the numbered vehicle invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- `CrewPositionIndex` is declared at `P:\scripts\3_game\vehicles\transport.c:179`.
- `RaycastRV` is declared at `P:\scripts\3_game\global\dayzphysics.c:199`.
- The enum `VehicleAnimInstances` starts at `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`; it has 12 values and ends with `MOTO2`.
- `GetSpeedometer` is declared at `P:\scripts\3_game\vehicles\car.c:102`.
- `CarGearboxType` is declared at `P:\scripts\3_game\vehicles\car.c:23`.
- The petrol pattern, an `IsVitalGlowPlug` override, is at `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`.
- The diesel pattern, an `IsVitalSparkPlug` override, is at `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`.
- `GetRuinedReplacement` is at `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:215`.
- `SetReplacementTypes` is at `P:\scripts\4_world\entities\core\inherited\inventoryitemtype.c:17`.
- The repair gate on `STATE_RUINED` is at `P:\scripts\4_world\plugins\pluginbase\pluginrepairing.c:96`.
- The destroyed-wheel proxy `ProxySedanWheel_destroyed` is at `P:\DZ\vehicles\wheeled\config.cpp:23981`.
- The `RefTexsMats` list of the Motorbike_02 `Front` zone is at `P:\DZ\vehicles\singletrack\config.cpp:1719`.
- `Motorbike_02_ShieldFront_ColorBase` is at `P:\DZ\vehicles\singletrack\config.cpp:1083`.

## How to read this file

`vehicle-structural-parity.md` covers the model structure of a car (Geometry, mass, centre of mass, wheel hubs, wheel-proxy Memory anatomy, ride height). It does not cover the full `config.cpp` car class or the matching `model.cfg` (skeleton and animations). This file gives both, end to end.

Read order for a car: (1) `vehicle-structural-parity.md` for the model-structure rules; (2) this file for `config.cpp` and `model.cfg`; (3) the per-LOD content, memory-point catalog and proxy placement parts of `vehicle-structural-parity.md`. Mass is not set in config: see §1.

## 1. The three files and what each owns (and where mass lives)

| File | Owns | Does NOT own |
|---|---|---|
| `.p3d` (Object Builder / py3d) | geometry, LODs, named selections, memory points, proxies, **mass + CoM (Geometry LOD vertex weights)** | physics params, animation values |
| `config.cpp` | the car class, drivetrain/engine/suspension numbers, crew, damage, lights, cargo, attachments, sound bindings, `AnimationSources` | mass, CoM, the animation geometry (axes) |
| `model.cfg` | `CfgSkeletons` (bone hierarchy) + `CfgModels` `Animations` (how each bone moves) | physics, which sources are user-driven |

**Mass is NOT in config.cpp.** Every vertex of every Geometry LOD component carries a weight, and the engine computes the vehicle's total mass and centre of mass from those weights. Neither the example 4x4 nor the reference quad has a `mass`, `centerOfMass`, `sprungMass` or `geometryClass` field, and none of the four names occurs in `P:\DZ\vehicles\wheeled\config.cpp` or `P:\DZ\vehicles\singletrack\config.cpp`. See the mass section of `vehicle-structural-parity.md` for assigning the weights. `sprungMass` is an Arma 3 car-config field (there the per-wheel values must add up to the vehicle's weight); whether DayZ's `CarScript` reads it at all is `[unverified]`.

## 2. The car class skeleton

A drivable DayZ car extends **`CarScript`**. Pattern: a `scope=0` base (`model=""` or the real model) that holds all physics, then `scope=2` concrete variants. The example 4x4 has a base and one variant:

```cpp
class Carscript;                       // forward-declare the parent (NOTE casing below)
class Landrover_Base: Carscript
{
    scope = 0;
    displayname = "Landrover Base";
    Model = "\Landrover\Landrover.p3d";
    // ... hiddenSelections, attachments, Crew, SimulationModule, DamageSystem, AnimationSources, Sounds ...
};
class Landrover: Landrover_Base { scope = 2; };
```

**Casing gotcha:** the example 4x4 writes `Carscript` (lowercase s); the reference quad writes `CarScript`. Config class-name resolution is **case-insensitive**, so both inherit correctly. The vanilla spelling is `CarScript`. The class name does NOT have to match the .p3d filename for a vehicle; the link is the `Model=` path.

## 3. SimulationModule — the physics core (reproduce, then tune)

`SimulationModule` holds the car's control properties and its engine and drivetrain configuration. A complete, working block from the example 4x4 (AWD, roughly the mass class of a long-wheelbase 4x4):

```cpp
class SimulationModule
{
    drive = "DRIVE_AWD";                    // DRIVE_RWD | DRIVE_FWD | DRIVE_AWD | DRIVE_642 (case-sensitive, defines feel)
    class Steering
    {
        maxSteeringAngle = 35;              // max wheel turn in degrees
        increaseSpeed[]  = {0,45, 60,25, 100,15};   // {km/h, deg/s} pairs — slower steer at speed
        decreaseSpeed[]  = {0,90, 60,45, 100,15};   // counter-steer speed
        centeringSpeed[] = {0,0, 15,28, 60,45, 100,60};
    };
    class Throttle
    {
        reactionTime = 0.25;               // s to reach wanted thrust
        defaultThrust = 0.8; gentleThrust = 0.6;
        turboCoef = 5; gentleCoef = 0.7;
    };
    class Brake
    {
        pressureBySpeed[] = {0,0.85, 10,0.7, 20,0.5, 40,0.4, 60,0.43, 80,0.46, 100,0.52, 120,0.7};
        reactionTime = 0.25; driverless = 0.1;   // driverless = brake applied with no driver, [0,1]
    };
    class Aerodynamics { frontalArea = 2.18; dragCoefficient = 0.65; };   // drag sets top speed
    class Engine
    {
        torqueCurve[] = {650,0, 850,110, 1200,150, 2500,200, 4350,160, 7300,0};  // {rpm, Nm} pairs
        inertia = 0.5; frictionTorque = 160; rollingFriction = 0.5; viscousFriction = 0.5;
        rpmIdle = 800; rpmMin = 850; rpmClutch = 1450; rpmRedline = 6150;
    };
    class Clutch { maxTorqueTransfer = 440; uncoupleTime = 0.1; coupleTime = 0.1; };
    class Gearbox { type = "GEARBOX_MANUAL"; reverse = 3.91; ratios[] = {3.6,3.0,2.3,1.45,1.0}; };
    class CentralDifferential { ratio = 1.5; type = "DIFFERENTIAL_LOCKED"; };   // only for AWD/642
    class Axles
    {
        class Front
        {
            maxBrakeTorque = 3500; maxHandbrakeTorque = 4000;
            wheelHubMass = 15;          // KG, only used while NO wheel is attached
            wheelHubRadius = 0.284;     // radius of the HUB component (Shift+E on hub, axis Y) — never negative
            class Differential { ratio = 4.0; type = "DIFFERENTIAL_OPEN"; };
            class Suspension { stiffness = 40000; compression = 2100; damping = 5400; travelMaxUp = 0.10; travelMaxDown = 0.06; };
            class Wheels
            {
                class Left  { animTurn="turnfrontleft";  animRotation="wheelfrontleft";  wheelHub="wheel_1_1_damper_land"; animDamper="damper_1_1"; inventorySlot="Landrover_Wheel_1_1"; };
                class Right { animTurn="turnfrontright"; animRotation="wheelfrontright"; wheelHub="wheel_2_1_damper_land"; animDamper="damper_2_1"; inventorySlot="Landrover_Wheel_2_1"; };
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
                class Left  { animTurn="turnbackleft";   animRotation="wheelbackleft";   wheelHub="wheel_1_2_damper_land"; animDamper="damper_1_2"; inventorySlot="Landrover_Wheel_1_2"; };
                class Right { animTurn="turnbacktright";  animRotation="wheelbackright";  wheelHub="wheel_2_2_damper_land"; animDamper="damper_2_2"; inventorySlot="Landrover_Wheel_2_2"; };
            };
        };
    };
};
```
(`animTurn="turnbacktright"` on rear-right is a typo in that config: `turnbacktright` has an extra `t`. The reference quad has the identical typo. Harmless: rear wheels don't steer. Use `turnbackright` in new work.)

`DRIVE_642` is the vanilla truck drivetrain: `drive="DRIVE_642"` at `P:\DZ\vehicles\wheeled\config.cpp:18539` (class `Truck_01_Base`), with a `CentralDifferential` of `ratio=0.75` and `type="DIFFERENTIAL_LOCKED"` at `:18564-18567`.

### What the wheel fields wire to
- `wheelHub` = the name of the wheel-hub **memory point / land-contact** in the .p3d (`wheel_X_Y_damper_land`).
- `animTurn` / `animRotation` / `animDamper` = **model.cfg animation SOURCE names** (see §11–13). Front
  wheels set `animTurn` (they steer); rear wheels still list it but it does nothing.
- `inventorySlot` = the wheel item slot (see §8).

### Parameter semantics
| class | key fields | meaning |
|---|---|---|
| `Steering` | `maxSteeringAngle`, `increaseSpeed[]`/`decreaseSpeed[]`/`centeringSpeed[]` | Each point of a curve sets how fast the steering wheel rotates at that vehicle speed. `{km/h, deg/s}` pairs. |
| `Throttle` | `defaultThrust`,`gentleThrust`,`turboCoef`,`gentleCoef`,`reactionTime` | gentle/default/turbo pedal-pressure modes |
| `Brake` | `pressureBySpeed[]`,`reactionTime`,`driverless` | `reactionTime` = how long it takes to floor the brake pedal; `driverless` ∈ [0,1] |
| `Aerodynamics` | `frontalArea`,`dragCoefficient`,(`downforceCoefficient`,`downforceOffset`) | Frontal drag practically sets the maximum forward speed. Negative drag is not allowed. |
| `Engine` | `torqueCurve[]` `{rpm,Nm}`, `inertia`, `rpmIdle/Min/Clutch/Redline` | The torque curve is entered by hand. `inertia` is the real field; `engineMomentum` does not exist (no occurrence in `P:\DZ\vehicles\wheeled\config.cpp`). |
| `Clutch` | `maxTorqueTransfer`,`uncoupleTime`,`coupleTime` | Maximum torque in Nm the clutch can transfer before it starts to slip. |
| `Gearbox` | `type` (`GEARBOX_MANUAL`/`GEARBOX_AUTOMATIC`), `reverse`, `ratios[]` | one reverse ratio + N forward ratios |
| `CentralDifferential` | `ratio`, `type` (`DIFFERENTIAL_LOCKED`/`_OPEN`) | Valid only for AWD and 642 drivetrains. |

### Suspension tuning — calibrate to mass (don't copy blindly)
Starting formula, then adjust: `compression = stiffness/10`, `damping = compression*3`; size the stiffness so the spring can carry the mass that gravity pushes down on that wheel. Two working reference points for a 4-wheeler (third-party mod configs):

| | Example 4x4 (AWD) | Reference quad (FWD) |
|---|---|---|
| Front stiffness / compression / damping | 40000 / 2100 / 5400 | 41000 / 2100 / 7200 |
| Front travelMaxUp / travelMaxDown | 0.10 / 0.06 | 0.293 / 0.051 |
| Rear stiffness / comp / damp | 40000 / 2100 / 5400 | 40000 / 2000 / 7000 |
| Rear travelMaxUp / travelMaxDown | 0.10 / 0.06 | 0.414 / 0.012 |
| drive / front diff | DRIVE_AWD / OPEN 4.0 | DRIVE_FWD / LOCKED 4.1 |

Trap: mass too LOW with stiffness copied from a heavier vehicle catapults the car. Suspension is **not** the spawn-bounce trigger, and neither is a monolithic Geometry LOD (see the spawn-launch corrections in `vehicle-structural-parity.md`). Confirmed spawn-bounce causes: chassis Geometry overlapping the wheel volume, spawn placement, and a stray `#Mass#` tag on a non-Geometry LOD (FireGeo) baking CoM=(0,0,0).

For any vehicle that inherits suspension from a different mass (measured in game on a 157 kg motorbike inheriting `Motorbike_02`'s springs, DayZ 1.30.164014): the wheel hangs from the modelled axle, the spring is zero at full extension, and F = k (u + travelMaxDown) with u linear in the damper phase (phase 0 = -travelMaxDown, 1 = +travelMaxUp). Measure each wheel's rest phase in game: the sum of spring forces / 9.81 must equal the configured mass; a shortfall means another collision box is resting on the ground. To seat the body on the axle set travelMaxDown = F / k per wheel keeping the up+down total (so the model.cfg damper zero stays valid); if that asks for too much extension, raise k = F / down and scale damping with √(k·m). Leave compression travel for load transfer (m·h / wheelbase). Full recipe with the measured numbers: `motorbike-invariants.md`, "Measured lessons from a real import".

## 4. Crew (driver / co-driver / cargo)

| property | type | description |
|---|---|---|
| `actionSel` | string | Name of the named selection(s) in the View or Fire Geometry LOD. This selection is the entry point for the user action. |
| `proxyPos` | string | Name of the named proxy selection in the View Geometry LOD. This proxy is where the player is put inside the car. It must have a bone defined in the car's skeleton config. |
| `getInPos` | string | Name of the point selection from which the player gets in and out. |
| `getInDir` | string | Name of a second point selection that gives the direction from the first. |
| `isDriver` | boolean | Marks the driver position. There can be at most one. |

The example 4x4 has a driver, a co-driver and 6 cargo seats. `proxyPos` names a **proxy object in ViewGeometry** (and FireGeometry) AND a **bone in `CfgSkeletons`**; both are required or get-in breaks (see `vehicle-structural-parity.md` "Crew proxies"):

```cpp
class Crew
{
    class Driver   { actionSel="seat_driver";   proxyPos="CrewDriver";   getInPos="pos_driver";   getInDir="pos_driver_dir";   isDriver=1; };
    class CoDriver { actionSel="seat_codriver"; proxyPos="CrewCoDriver"; getInPos="pos_codriver"; getInDir="pos_codriver_dir"; };
    class Cargo1   { actionSel="seat_cargo1";   proxyPos="CrewCargo1";   getInPos="pos_cargo";    getInDir="pos_cargo_dir"; };
    // Cargo2..Cargo6 identical, incrementing the index; all cargo share pos_cargo/pos_cargo_dir here
};
```
(`isDriver=1` and `isDriver=true` are equivalent.)

**Fix `crewDriver`/`pos_driver` BEFORE baking (offline fit editor).** Crew memory points are baked into the Memory LOD: they cannot be nudged in game without a rebuild, so a wrong seat costs a full build cycle per guess. A cheap fix that worked on a quad build: a throwaway offline HTML editor (sliders for `crewDriver` X/Y/Z/yaw and `pos_driver` X/Y/Z, a seated mannequin about 1.8 m tall, the handlebar or wheel grips as fixed markers, a live coordinate readout) to align pelvis to seat and hands to grips, then copy the final coordinates into the build script. Seed its defaults from a working reference vehicle's real points (debinarize its Memory LOD). The editor *places* the seat offline; the headless crew probe (`vehicle-structural-parity.md`) *verifies* that the ViewGeo seat cube can be hit by a raycast.

## 5. Lights (selections + reflector material on/off)

Two halves: (a) the glowing headlight **mesh faces** are `hiddenSelections` swapped to a lights `.rvmat`; (b) named `*ReflectorMatOn/Off` properties tell `CarScript` which material to swap when lights toggle. The **light beam** itself is placed at Memory points (`light_left`,`light_left_dir`,`light_right`, `light_right_dir`, `reflector_1_1`, `reflector_2_1`). Example 4x4:

```cpp
hiddenSelections[]={ "light_left","light_right","light_brake_1_2","light_brake_2_2",
    "light_reverse_1_2","light_reverse_2_2","light_1_2","light_2_2","light_dashboard","base","special" };
hiddenSelectionsTextures[]={ "","","","","","","","","", "Landrover\data\lr_base_acr_co.paa","Landrover\data\lr_special_acr_co.paa" };
hiddenSelectionsMaterials[]={ "","","","","","","","","", "Landrover\data\lr_base.rvmat","Landrover\data\lr_special.rvmat" };

frontReflectorMatOn  ="Landrover\data\landrover_front_lights_on.rvmat";   frontReflectorMatOff ="Landrover\data\lr_base.rvmat";
brakeReflectorMatOn  ="Landrover\data\landrover_brake_lights_on.rvmat";   brakeReflectorMatOff ="Landrover\data\lr_base.rvmat";
TailReflectorMatOn   ="Landrover\data\landrover110_tail_lights_on.rvmat"; TailReflectorMatOff  ="Landrover\data\lr_base.rvmat";
ReverseReflectorMatOn="Landrover\data\landrover_reverse_lights_on.rvmat"; ReverseReflectorMatOff="Landrover\data\lr_base.rvmat";
dashboardMatOn       ="Landrover\data\landrover_dashboard_lights_on.rvmat"; dashboardMatOff    ="Landrover\data\lr_base.rvmat";
```
The `_on.rvmat` is an **emissive** material (see `emissive-leds-and-dynamic-lights.md`, and the emissive section of `skills/dayz-model-pipeline/references/config-and-packing.md`); the `_off` is the plain body material. Without the selections, the memory points and these properties, headlights mount but never illuminate (`vehicle-structural-parity.md` "Lights").

## 6. DamageSystem / DamageZones

`class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[] } } class DamageZones { ... } }`.
Each zone maps to a `dmgZone_*` selection (in FireGeometry/Hitpoints + Memory) via `componentNames[]`/`memoryPoints[]`, and can cascade damage to other zones (`transferToZonesNames[]`/`Coefs[]`) or to attached items (`inventorySlots[]`/`Coefs[]`). The example 4x4's full zone set: **Chassis, Front, Back, Roof, Fender_1_1/2_1/1_2/2_2, WindowFront, Engine, FuelTank, Reflector_1_1/2_1** (door/window zones live on the `CarDoor` item classes, §8). Two zones in full; the rest follow the same shape:

```cpp
class DamageSystem
{
    class GlobalHealth { class Health { hitpoints=2500; healthLevels[]={ {1.0,{}},{0.7,{}},{0.5,{}},{0.3,{}},{0.0,{}} }; }; };
    class DamageZones
    {
        class Chassis
        {
            class Health { hitpoints=2500; transferToGlobalCoef=0; };
            displayName="$STR_CfgVehicleDmg_Chassis0";
            memoryPoints[]={"dmgZone_chassis"};  componentNames[]={"dmgZone_chassis"};
            fatalInjuryCoef=-1;  inventorySlots[]={};
        };
        class Front
        {
            class Health { hitpoints=2500; transferToGlobalCoef=0;
                healthLevels[]={ {1.0,{"Landrover\data\lr_base.rvmat","Landrover\data\lr_special.rvmat"}},
                                 {0.7,{...}},{0.5,{"...lr_base_damage.rvmat",...}},{0.3,{...}},{0.0,{"...lr_base_destruct.rvmat",...}} }; };
            displayName="$STR_CfgVehicleDmg_Bumper0";
            transferToZonesNames[]={"Reflector_1_1","Reflector_2_1","Fender_1_1","Fender_2_1","Engine"};
            transferToZonesCoefs[]={0.1,0.1,0.1,0.1,0.15};
            memoryPoints[]={"dmgZone_front"};  componentNames[]={"dmgZone_front"};
            inventorySlots[]={"Landrover_Hood","CarRadiator","Landrover_Wheel_1_1","Landrover_Wheel_2_1"};
            inventorySlotsCoefs[]={0.3,0.25,0.1,0.1};
        };
        // Back, Roof(dmgZone_tarp), Fender_*, WindowFront, Engine(fatalInjuryCoef=0.001), FuelTank, Reflector_* ...
    };
};
```
`healthLevels[]` has 5 thresholds (1.0/0.7/0.5/0.3/0.0); each supplies the `.rvmat` array to swap at that damage level (empty `{}` = no visual change). `"hidden"` instead of an rvmat array is the config shape for glass that should vanish at that level; this file has no in-game check of it, and on one import a glass slot never hid (end of §6b). Every `dmgZone_*` in `componentNames[]` MUST exist as a selection in the model (FireGeometry component + Hitpoints/Memory). Without DamageZones + FireGeometry components there is no localized damage.

A zone's `class Health` can also declare `RefTexsMats[]`. Vanilla Motorbike_02 `Front` lists `motorbike_02_body`, `_glass` and `_wheel`, the rvmats of its 1.0 entry in the same order (`P:\DZ\vehicles\singletrack\config.cpp:1719-1724`), and its 0.0 entry is `{body_destruct, "hidden", wheel_destruct}` (`:1773`): read from the config, each slot of an entry replaces the rvmat in the same slot of the list. In that config every motorbike zone that hides glass declares the list, while Motorbike_01 `FuelTank` and Motorbike_02 `Engine` have none; in `P:\DZ\vehicles\wheeled\config.cpp` none of the 18 `Window*` zones whose `healthLevels[]` hold `"hidden"` declares one, and 14 of them hide with the whole entry `{0,"hidden"}`. How the engine matches rvmats to faces in a zone without the list is not established. A child zone that redefines `healthLevels[]` but not `RefTexsMats[]` keeps its parent's list through `class Health: Health`; what that does in game was never isolated.

Script reads `componentNames[]` (`P:\scripts\3_game\damagesystem.c:63-68`), not `memoryPoints[]`. The vanilla Chassis zone may omit `memoryPoints[]` entirely. Missing Memory `dmgzone_*` points are a config/Memory parity matter, not a cause of collision jerks (invariant 35). Keep the FireGeometry `dmgzone_*` selections; do not spend an in-game cycle adding the Memory half as a physics fix.

## 6b. Window / glass damage

In config, breakable glass is **not** a separate system: it is the same `DamageZones` + `healthLevels[]` rvmat-swap mechanism as any body panel (§6), applied to a window-named zone. That the swap and the hiding work on glass is not checked in game here (see the windscreen at the end of §6b). Three independent configs converge on the same shape (intact, intact/no change, damage rvmat, destruct rvmat, `"hidden"`):

| Config | Zone | hitpoints | final state |
|---|---|---|---|
| Example 4x4 (third-party mod) | `WindowFront` (body) | 200 | `"hidden"` |
| DayZ Expansion UAZ (third-party mod) | `Window` (per door) | 500 | `"hidden"` |
| DayZ Expansion UAZ (third-party mod) | `WindowFront` (body) | 800 | `"hidden"` |
| Vanilla `OffroadHatchback` | `WindowFront` | 120 (`hitpoints` at `P:\DZ\vehicles\wheeled\config.cpp:2059`) | `"hidden"` (`:2095`) |

The DayZ Expansion UAZ door window:
```cpp
class Window
{
    class Health
    {
        hitpoints=500;
        healthLevels[]=
        {
            {1,   {"dz\vehicles\wheeled\hatchback_02\data\hatchback_02_windows.rvmat"}},
            {0.7, {"dz\vehicles\wheeled\hatchback_02\data\hatchback_02_windows.rvmat"}},
            {0.5, {"dz\vehicles\wheeled\hatchback_02\data\glass_i_damage.rvmat"}},
            {0.3, {"dz\vehicles\wheeled\hatchback_02\data\glass_i_damage.rvmat"}},
            {0,   "hidden"}
        };
    };
    fatalInjuryCoef=-1; transferToGlobalCoef=0;
    componentNames[]={"dmgZone_doorwindowLeft"};
};
```
It reuses the **vanilla Hatchback_02** glass rvmats (both files exist under `P:\DZ\vehicles\wheeled\hatchback_02\data\`) instead of authoring new damage textures: a legitimate shortcut when the vanilla crack look is acceptable.

**Naming convention**: English, `dmgZone_*` pattern (e.g. `dmgZone_windowFront`, `dmgZone_doorwindowLeft`), NOT the Czech legacy names (`sklo predni L/P`) of Arma 1 era glass. Those belong to a different, older pipeline (convex glass hull duplicated into the Fire Geometry LOD, one Hit-points LOD vertex per opening) that does not apply to DayZ's config-driven DamageZones system. Do not follow it.

**`[unverified]`, open, do not guess:**
- The "correct" `hitpoints` value varies from 120 to 800 across these configs: calibrate per vehicle, and do not treat any single number as canonical.
- The `.p3d`-side authoring: which LOD the `dmgZone_window*` selection must live in, and how to paint it in Object Builder or Blender. Debinarize a vanilla car with glass (`civiliansedan`) with the parity-first method and inspect its selection directly instead of guessing.
- Whether `"hidden"` at 0 HP also removes FireGeometry/collision or only the visual. Test in game: does a shattered window still block bullets and vision like solid glass?

### Per-slot `"hidden"` and a windscreen that never hid

Vanilla motorbikes put `"hidden"` in the glass slot of a zone with `RefTexsMats[]` (§6): Motorbike_02 `Front`, `Reflector_1_1` and `FuelTank`, and Motorbike_01 `Reflector_1_1` (quoted in `skills/dayz-motorbikes/references/config-contract.md`). In the binarized Motorbike_02 model that glass rvmat sits on three LOD 0 sections, one in each of its three zones, with a procedural texture at 10% alpha (`#(argb,8,8,3)color(0.000,0.000,0.000,0.100,ca)`); `motorbike_02_glass.rvmat` itself sets `renderFlags[] = {"NoZWrite"}` and the `Super` shaders (`P:\DZ\vehicles\singletrack\motorbike_02\data\motorbike_02_glass.rvmat:7-12`). The Motorbike_02 windscreen is not one of them: it is the attachment `Motorbike_02_ShieldFront_ColorBase` (`proxy\Motorbike_02_windshield.p3d`), with its own `GlobalHealth` swap to windshield, damage and destruct rvmats and no `"hidden"`, and its slot is listed in `Front`'s `inventorySlots[]` (`P:\DZ\vehicles\singletrack\config.cpp:1083` for the class and `:1788` for the slot).

One motorbike import wired its windscreen like that body glass, not like the vanilla windscreen: its `Front` declares `RefTexsMats[]` with the glass rvmat in the same slot as in every `healthLevels[]` entry, and `"hidden"` in that slot at 0.0. In the binarized model of the build tested, LOD 0 has 390 sections (the vanilla Motorbike_02 has 22); the windscreen is section 173, textured with a procedural at 35% alpha, and the ninth of the 67 sections of the sectional selection `dmgzone_front`; the glass rvmat is on 149 sections, 146 of them in `dmgzone_back`. With the zones taken down by the vanilla contact-damage call (`process-gates.md`) and levels 2 and 4 logged on server and client, the body panels of `Front` took the damage and destruct rvmats and came back on repair, while the windscreen stayed drawn at level 4 (measured in game on DayZDiag 1.30.164014 and in three runs on 1.30.164200, the last of them with the crack rvmat taken out of the 0.5/0.3 entries). The cause is unknown.

- **Excluded:** a missing file. `"hidden"` needs none, the glass rvmat is on faces, and the diagnostic PBO held its marker rvmat, so the config-only rvmat trap of `/dayz-build-pbo` does not apply. binarize's "Material not loaded" names the glass rvmat, but also the body rvmats that do swap.
- **Weak evidence:** at level 2, cracks (two runs) and a red emissive marker (one run) never showed, but no part carried those rvmats from the start, and cracks on alpha-blended glass are faint. A vanilla Motorbike_02 control cannot witness the case: its nearly transparent glass looks the same hidden or not. The strong evidence is the windscreen still drawn at level 4.

**Open, untested:** a limit on section index or count (a cap at a zone's first 64 sections would still include its ninth entry, and 173 is under 256); a per-material section count; how transparent sections are handled (a blanket limit is unlikely, since vanilla glass is also `NoZWrite`/`Super`, but no vanilla glass was seen hiding either); the shape itself: vanilla puts its body glass in zones of two to five sections, cars give glass a zone of its own (§6b table) and the Motorbike_02 windscreen is an attachment. Section indices move between builds (`/dayz-build-pbo`; `proxies-and-get-in.md`), so read the index from the binarized model you test.

Cheapest first, one variable per build against an unmodified control, every build counted against the iteration budget of `method-and-gate-calibration.md`: (1) offline, the face-ownership census of invariant 15d (`lights.md`) for the windscreen section, against the model's hidden selections (on that import `light_1_1`, `camo`, `light_1_2`, `dashboard` and the gauge glyphs); (2) the windscreen in a zone of its own whose 0.0 entry is `{0,"hidden"}`; (3) the windscreen as an attachment, like `Motorbike_02_ShieldFront`; (4) the windscreen at a low section index with the same material and section count (check the binarized model before the run); (5) its own rvmat path (same content) with its own `RefTexsMats[]` slot; (6) `NoZWrite` alone against an opaque texture alone; (7) an opaque, unmistakable final rvmat instead of `"hidden"`, next to a part that carries that rvmat from the start. Until one of them changes the result, a glass zone that passes config and model checks is "config", not "works".

## 7. Attachments, Cargo, fuel, GUI groups

Example 4x4:

```cpp
fuelCapacity=65; fuelConsumption=15;
attachments[]={ "CarBattery","Reflector_1_1","Reflector_2_1","CarRadiator","SparkPlug",
    "Landrover_Driver_Door","Landrover_CoDriver_Door","Landrover_Hood","Landrover_Trunk",
    "Landrover_Wheel_1_1","Landrover_Wheel_1_2","Landrover_Wheel_2_1","Landrover_Wheel_2_2","Landrover_Sparewheel" };
class Cargo { itemsCargoSize[]={10,50}; allowOwnedCargoManipulation=1; openable=0; };
class GUIInventoryAttachmentsProps
{
    class Engine  { name="$STR_attachment_Engine0";  icon="set:dayz_inventory image:cat_vehicle_engine";  attachmentSlots[]={"CarBattery","CarRadiator","SparkPlug"}; };
    class Body    { name="$STR_attachment_Body0";    icon="set:dayz_inventory image:cat_vehicle_body";    attachmentSlots[]={"Reflector_1_1","Reflector_2_1","Landrover_Driver_Door","Landrover_CoDriver_Door","Landrover_Hood","Landrover_Trunk","Landrover_Sparewheel"}; };
    class Chassis { name="$STR_attachment_Chassis0"; icon="set:dayz_inventory image:cat_vehicle_chassis"; attachmentSlots[]={"Landrover_Wheel_1_1","Landrover_Wheel_1_2","Landrover_Wheel_2_1","Landrover_Wheel_2_2"}; };
};
```
`CarBattery` + `SparkPlug` (+ `CarRadiator`) are vanilla engine-part slots **required for the engine to start** (§15). Vanilla leaves BOTH `IsVitalSparkPlug` and `IsVitalGlowPlug` true by default (`P:\scripts\3_game\vehicles\transport.c:404-412`), so a petrol car must override `IsVitalGlowPlug()` to return false (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`) or it also demands a GlowPlug it has no slot for, without saying so. `ObstacleGenerator { class Shapes { class Cylindric {...} } }` (in the example 4x4) carves the road-block volume; optional.

## 8. Wheels & doors as ITEMS + slot/proxy wiring

A car's wheels and doors are **separate item entities** attached into slots. Three pieces wire each one: the item class, the slot, and (for the visual drawn while attached) the proxy.

### a) Wheel item — `class <Wheel>: CarWheel` (example 4x4)
```cpp
class CarWheel;
class Landrover_Wheel: CarWheel
{
    scope=2; displayName="Landrover Wheel"; model="\Landrover\proxy\Landrover_Wheel.p3d"; weight=15000;
    inventorySlot[]={"Landrover_Wheel_1_1","Landrover_Wheel_1_2","Landrover_Wheel_2_1","Landrover_Wheel_2_2","Landrover_Sparewheel"};
    radius=0.451; width=0.142;                          // tire radius/width (drives the visual + ground contact)
    radiusByDamage[]={0,0.451, 0.3,0.3, 0.9998,0.25, 0.9999,0.2};
    tyreOffroadResistance=0.75; tyreGrip=0.8; tyreRollResistance=0.015;
    rotationFlags=8; repairableWithKits[]={6}; repairCosts[]={30};
    class DamageSystem { class GlobalHealth { class Health { hitpoints=400; healthLevels[]={...} }; }; };
};
class Landrover_Wheel_Ruined: CarWheel { /* radius=0.2; width=0.107; tyreGrip=0.2; the destroyed variant */ };
```
`tyreGrip`/`tyreRollResistance` are the "feel" knobs: the reference quad uses `tyreGrip=2.8` with `tyreRollResistance=0.015` (glued to the ground) against the example 4x4's `0.8`/`0.015`. **`radius` here must agree with the wheel proxy .p3d Memory anatomy** (see the wheel-proxy part of `vehicle-structural-parity.md`) or the wheel makes no ground contact.

### b) Slot registration — `class CfgSlots` (reference quad)
Custom wheel slots are registered once (vanilla slots like `CarBattery` need no registration):
```cpp
class CfgSlots
{
    class Slot_quad_wheel_1_1 { name="quad_wheel_1_1"; displayName="Front Left Wheel"; selection="wheel_1_1"; ghostIcon="wheel"; };
    // _1_2 (rear left), _2_1 (front right), _2_2 (rear right)
};
```
Naming convention `<side>_<axle>`: side 1=left, 2=right; axle 1=front, 2=rear (`_1_2` is rear left and `_2_1` front right). Vanilla agrees: the truck's front axle holds `Truck_01_Wheel_1_1` and `Truck_01_Wheel_2_1` (`P:\DZ\vehicles\wheeled\config.cpp:18589` and `:18594`).

`[unverified]` The example 4x4's `config.cpp` has no `CfgSlots` block for its `Landrover_Wheel_*` slots: either the slots are defined elsewhere in that mod or the engine registers them by itself. Confirm the mechanism before shipping custom slots without a `CfgSlots` entry.

### c) Proxy-while-attached — `class CfgNonAIVehicles` (reference quad)
For the wheel or part to be DRAWN on the body while attached (and not only in inventory):
```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;
    class ProxyVehiclePart: ProxyAttachment { scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0; };
    class Proxyquadbike_wheel: ProxyVehiclePart { model="\MyMod\QuadBike\proxys\quadbike_wheel.p3d"; inventorySlot[]={"quad_wheel_1_1","quad_wheel_2_1"}; };
    // + rear + destroyed variants
};
```
The proxy `.p3d` is the same model referenced by the `CarWheel` item and placed as a proxy face in the body's Visual + ViewGeometry + FireGeometry LODs (see wheel proxies in FireGeometry and the wheel-proxy Memory anatomy in `vehicle-structural-parity.md`).

### d) Door item — `class <Door>: CarDoor` (example 4x4)
Doors are items too (`Landrover_Driver_Door`/`CoDriver_Door`/`Hood`/`Trunk`), each a `CarDoor` with its own `model="\Landrover\proxy\<Door>.p3d"`, `inventorySlot`, `hiddenSelections` and a `DamageZones` with `Window`+`Doors` zones. The door **opening animation** lives in model.cfg (§12) + `AnimationSources` (§10), not on the item.

## 9. Sounds — borrow a vanilla engine's SoundSets

The simplest correct pattern: reference an existing vanilla vehicle's SoundSets by name (do NOT redefine them). The example 4x4 borrows the whole `offroad_*` set:
```cpp
class Sounds
{
    thrust=0.6; thrustTurbo=1; thrustGentle=0.3; thrustSmoothCoef=0.02; camposSmoothCoef=0.03;
    soundSetsFilter[]={ "offroad_Engine_Offload_Ext_Rpm1_SoundSet", ... "offroad_Engine_Ext_Rpm0..5_SoundSet",
        "offroad_Engine_Ext_Broken_SoundSet", "offroad_Tires_*_SoundSet", "offroad_Rain_Ext_SoundSet",
        "offroad_damper_left_SoundSet","offroad_damper_right_SoundSet" };
    soundSetsInt[]={ "Offroad_Tires_Asphalt_Fast_General_Int_SoundSet","Offroad_Wind_SoundSet" };
};
```
A from-scratch car only needs custom `CfgSoundShaders`/`CfgSoundSets` if you want a unique engine note; otherwise borrow `offroad_*` (truck/SUV) or `Hatchback_02_*`/`Sedan_02_*` (car). The reference quad borrows `Hatchback_02_*` start and horn sounds and defines only its own RPM SoundShaders. Its `class Sounds` block lives on the **scope=2 variant** (on the base in the example 4x4); both work.

## 10. config.cpp — AnimationSources (the `user`-driven sources)

Dampers and doors are driven by script or simulation as `source="user"`; the engine-driven sources (`wheelfrontleft`, `turnfrontleft`, `speed`, `rpm`, `fuel`…) are NOT listed here: the car simulation provides them. Example 4x4:
```cpp
class AnimationSources
{
    class DoorsDriver  { source="user"; initPhase=0;       animPeriod=0.5; };
    class DoorsCoDriver: DoorsDriver {}; class DoorsHood: DoorsDriver {}; class DoorsTrunk: DoorsDriver {};
    class damper_1_1   { source="user"; initPhase=0.4857;  animPeriod=1; };   // front rest position
    class damper_2_1: damper_1_1 {};
    class damper_1_2   { source="user"; initPhase=0.4002;  animPeriod=1; };   // rear rest position
    class damper_2_2: damper_1_2 {};
};
```
Missing a damper source gives the RPT line `unknown animation source damper`. `initPhase` fixes the visual rest position of the damper (front ≈0.486, rear ≈0.400).

## 11. model.cfg — CfgSkeletons (the bone hierarchy)

The **wheel bone chain encodes steering vs rolling vs suspension**: front = `damper → steering → wheel` (3 levels), rear = `damper → wheel` (no steering bone). `isDiscrete=1` (mechanical). Example 4x4, abridged to the vehicle-critical bones:
```cpp
class cfgSkeletons
{
    class Landrover_skeleton
    {
        skeletonInherit=""; isDiscrete=1;
        SkeletonBones[]=
        {
            "drivewheel","", "mph","", "rpm","", "dial_rpm","", "dial_temp","", "fuel_1","",   // dashboard
            "doors_driver","", "doors_codriver","", "doors_hood","", "doors_trunk","",          // doors
            "crewdriver","", "crewcodriver","", "CrewCargo1","", /* ...CrewCargo6 */              // crew proxy bones
            "engine","", "engine_rotate","engine",
            // FRONT wheels: damper -> steering -> wheel
            "wheel_1_1_damper","",  "wheel_1_1_steering","wheel_1_1_damper",  "wheel_1_1","wheel_1_1_steering",
            "wheel_2_1_damper","",  "wheel_2_1_steering","wheel_2_1_damper",  "wheel_2_1","wheel_2_1_steering",
            // REAR wheels: damper -> wheel  (NO steering bone)
            "wheel_1_2_damper","",  "wheel_1_2","wheel_1_2_damper",
            "wheel_2_2_damper","",  "wheel_2_2","wheel_2_2_damper"
        };
    };
};
```
Each pair is `"bone","parent"` (empty parent = root). `crewdriver`/`crewcodriver`/`CrewCargoN` bones MUST exist here because `Crew.proxyPos` requires them (§4). Bone names MUST match the .p3d selection names.

## 12. model.cfg — CfgModels Animations

`class <Model>: Default { skeletonName="<skeleton>"; sections[]={hiddenSelections + dmgZones}; class Animations {...} }`.
The four animation families a car needs (example 4x4):

```cpp
class Animations
{
    // ---- wheel ROLLING (continuous spin) — source provided by sim; sourceAddress=loop; maxValue=2*PI ----
    class wheel_1_1 { type="rotation"; source="wheelfrontleft";  selection="wheel_1_1"; axis="wheel_1_1_axis";
                      sourceAddress=loop; minValue=0.0; maxValue=6.2831855; angle0=0.0; angle1=6.2831855; };
    class wheel_2_1 { type="rotation"; source="wheelfrontright"; selection="wheel_2_1"; axis="wheel_2_1_axis";
                      sourceAddress=loop; minValue=0.0; maxValue=6.2831855; angle0=0.0; angle1=-6.2831855; };  // right side negated
    // wheel_1_2 (wheelbackleft), wheel_2_2 (wheelbackright) identical pattern

    // ---- STEERING (front only) — selection is the *_steering bone ----
    class steering_hub_1_1 { type="rotation"; source="turnfrontleft";  selection="wheel_1_1_steering"; axis="wheel_1_1_steering_axis";
                             minValue=-1.5707964; maxValue=1.5707964; angle0=-1.5707964; angle1=1.5707964; };
    class steering_hub_2_1 { type="rotation"; source="turnfrontright"; selection="wheel_2_1_steering"; axis="wheel_2_1_steering_axis";
                             minValue=-1.5707964; maxValue=1.5707964; angle0=-1.5707964; angle1=1.5707964; };

    // ---- SUSPENSION damper (translation) — minValue/maxValue FIXED 0/1, travel via offsets ----
    class suspension_damper_1_1 { type="translation"; source="damper_1_1"; selection="wheel_1_1_damper"; axis="wheel_1_1_damper_axis";
                                  minValue=0.0; maxValue=1.0; offset0=0.05; offset1=-0.35; };
    // _2_1 same; rear _1_2/_2_2 use maxValue=0.6 (visual only), same offsets

    // ---- steering WHEEL + dials + doors ----
    class DrivingWheel { type="rotation"; source="steeringwheel"; selection="drivewheel"; axis="drivewheel_axis";
                         minValue=-1.0; maxValue=1.0; angle0=1.9415927; angle1=-1.9415927; };
    class IndicatorSpeed { type="rotation"; source="speed"; selection="mph"; axis="mph_axis"; minValue=0.0; maxValue=160.0; angle0=0.0; angle1=-4.5361256; };
    class IndicatorRPM   { type="rotationZ"; source="rpm"; selection="rpm"; axis="rpm_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=-1.5707964; };
    class IndicatorFuel  { type="rotation"; source="fuel"; selection="fuel_1"; axis="fuel_1_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=-1.5707964; };
    class DoorsDriver { type="rotation"; source="doorsdriver"; selection="doors_driver"; axis="doors_driver_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=1.3962634; };
    // DoorsCoDriver, DoorsHood, DoorsTrunk same shape
};
```
Key points: **wheel rolling** uses `sourceAddress=loop` and a full-turn range (`maxValue=2π`), right-side `angle1` negated; **steering** rotates the `*_steering` selection ±90° (±π/2); **damper** is a `translation` with `minValue=0`/`maxValue=1` and the real travel carried by `offset0`/`offset1` (NOT by min/max, a recurring confusion; see the `suspension_damper` pattern in `vehicle-structural-parity.md`). Every animation needs a matching 2-point `*_axis` selection in the Memory LOD or it does nothing and logs nothing (`/dayz-p3d-audit` checks this).

**Two traps measured on a quad build:**
- **`angle0/angle1="rad N"`: N is the throw in DEGREES, not radians.** `rad 0.45` gives about 0.5° (looks frozen), `rad 30` gives about 30°. Tune handlebar, needle and door throw on a degree scale, not a 0–2π scale (the bare `6.2831855` constants above are radians: see point 4 of the next section).
- **`GetSteering()` is client-only: the server returns 0** (measured in game). A cosmetic steering or handlebar animation driven by a script `source="user"` set from the client gets overwritten by server sync and snaps back in multiplayer. Use the **engine-native `source="steeringwheel"`** channel (already synced; the `DrivingWheel` class above) for any visual tied to steering; keep `source="user"` for what the engine does not already drive (dampers, doors).

### Dashboard needles: what the engine feeds `speed` / `rpm`

Read from the binarized vanilla models `DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` and `civiliansedan\civiliansedan.p3d` with an ODOL reader (ODOL v54, DayZ 1.29; not re-read on this build). These are the classes the vanilla cars ship with, not the example 4x4 above:

| car | class | source | type | minValue | maxValue | angle0 | angle1 | bone |
|---|---|---|---|---|---|---|---|---|
| offroadhatchback | IndicatorSpeed | `speed` | rotation | 0 | **120** | 0 | 190 deg | `dial_speed` (root) |
| offroadhatchback | IndicatorRPM | `rpm` | rotation | 0 | **1.0** | 20 deg | 260 deg | `dial_rpm` (root) |
| offroadhatchback | IndicatorFuel / IndicatorCoolant | `fuel` / `coolant` | rotation | 0 | 1.0 | 0 / 85 deg | 90 / 0 deg | `dial_fuel` / `dial_temp` |
| civiliansedan | IndicatorSpeed | `speed` | **translation** | 0 | **200** | - | - | `dial_speed` |
| civiliansedan | IndicatorRPM | `rpm` | rotation | 0 | 1.0 | 50 deg | -40 deg | `dial_rpm` |

What this settles (the example 4x4 rows above are consistent with it):

1. `speed`, `rpm`, `fuel`, `coolant` are engine-provided sources; vanilla declares NO `AnimationSources` for them.
2. `speed` arrives on the speedometer scale, i.e. km/h like `GetSpeedometer()` (`P:\scripts\3_game\vehicles\car.c:102`): `maxValue` is simply the top number painted on the dial (120 hatchback, 200 sedan).
3. `rpm` arrives NORMALISED 0..1 (`maxValue = 1.0` on both cars). Which engine rpm maps to 1.0 (`EngineGetRPMMax` = end of `torqueCurve[]`, or `rpmRedline`) is NOT settled by the model; on one quad build they differed by 1 rpm (6400 vs 6399). Design the sweep as `angle1 = angle0 + painted_sweep x (D / painted_top)` and measure D once in game (log `EngineGetRPM`/`EngineGetRPMMax`/`EngineGetRPMRedline`, declared at `P:\scripts\3_game\vehicles\car.c:221-227`, plus a photo of the needle at cut-off).
4. Angles are stored in radians in the binarized model, but vanilla authors them as `"rad N"` with N in DEGREES: `rad` is the config parser's degrees-to-radians function (3.3161 rad == "rad 190"). That is why `"rad 0.45"` looks frozen and `"rad 30"` sweeps 30 deg. A bare number (`angle1 = -4.5361256`) is radians. Both syntaxes are valid; never mix them in one model.cfg.
5. `angle0` is applied at `minValue`, so the needle mesh does NOT have to rest on the painted zero: vanilla rests the rpm needle 20 deg before its zero. Keeping the mesh at rest (e.g. 12 o'clock) and carrying the offset in `angle0` also gives a free detector: with the engine off, a needle still at 12 o'clock means the animation did not bake (bone missing from `skeletonBones[]`, selection empty, or the class dropped by binarize).
6. The needle axis is a 2-point Memory selection on the pivot along the dial normal (the example 4x4 puts the points 1 mm apart; 1 m apart avoids a degenerate axis). Sign rule by pseudovector `angle1 x unit(axis_dir)` against the hatchback control: axis pointing from the dial TOWARDS the driver + positive angle1 = clockwise for the driver. The example 4x4 authors it the other way round (axis away from the driver, angle1 negative) and gets the same pseudovector, so compare the pseudovector, never the raw sign (see `animation-sign-and-axis.md`).
7. Bone parent: vanilla `dial_*` bones hang from the ROOT because the cluster sits on the dashboard. On a quad or bike the cluster rides on the handlebar: the needle bones must be children of `drivewheel`, and `drivewheel` must cover ALL the handlebar and cluster faces, or the needles stay behind when the bars turn.
8. A needle animated on a PROXY sub-model is static in game (measured on a car build): host the needle selections in the main model.

In-game confirmation of the sign rule and of D is still pending. The full needle workflow is in `gauge-needles.md`.

## 13. The wiring chain (config ⇄ model.cfg ⇄ .p3d)

```
config Axles.Front.Wheels.Left
  animRotation="wheelfrontleft" ─────► model.cfg class wheel_1_1   source="wheelfrontleft"  (sim-driven, loop)
  animTurn    ="turnfrontleft"  ─────► model.cfg class steering_hub_1_1 source="turnfrontleft" (sim-driven)
  animDamper  ="damper_1_1"     ─────► model.cfg class suspension_damper_1_1 source="damper_1_1"
                                              ▲ also ► config AnimationSources class damper_1_1 source="user"
  wheelHub    ="wheel_1_1_damper_land" ─────► .p3d Memory point (land contact) + Geometry hub component
  inventorySlot="Landrover_Wheel_1_1"  ─────► CfgSlots slot + CarWheel item + CfgNonAIVehicles proxy
model.cfg selections (wheel_1_1, wheel_1_1_steering, wheel_1_1_damper, *_axis) ─────► must exist in .p3d
```
A break anywhere in this chain is a failure with no log line (no roll / no steer / no suspension), or `unknown source`.

## 14. Shortcut: reuse a vanilla anim-instance rig

Instead of authoring the whole model.cfg, a mod can reuse a vanilla rig by overriding `GetAnimInstance()` in its CarScript child (the reference quad returns `VehicleAnimInstances.V3S`). Then the wheel, steering and damper animation CLASSES come from the vanilla rig and you only need matching selections and axes in the .p3d. Caveat: returning a `VehicleAnimInstances` value alone does not prove the vanilla model.cfg is reusable; verify the vanilla rig's selection names match yours before relying on it. For a truly from-scratch car, author the full model.cfg (§11–12): it is self-contained, and the example 4x4 drives with it.

## 15. Troubleshooting — engine / won't-start (+ the in-game Diag tool)

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Engine won't start at all | Missing engine-part slots | `CarBattery` + `SparkPlug` (and often `CarRadiator`) must be in `attachments[]` and physically attached in game; a car with no battery or plug cranks but won't run |
| Won't start even WITH a SparkPlug attached | The default `IsVitalGlowPlug()` returns true and demands a GlowPlug too (`P:\scripts\4_world\entities\vehicles\carscript.c:1783`); a bare `CarScript` needs BOTH plugs (all `IsVital*` default true: `P:\scripts\3_game\vehicles\transport.c:404-417` for the plugs and the fuel tank, `P:\scripts\4_world\entities\vehicles\carscript.c:2201-2209` for the belt and the radiator) | Override the unused igniter. Petrol: `IsVitalGlowPlug()` returns false (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`), keep SparkPlug. Diesel: `IsVitalSparkPlug()` returns false (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`), keep GlowPlug. Declare ONLY the vital plug in `attachments[]` and attach it in `OnDebugSpawn`. Returning false from `IsVitalGlowPlug` is the vanilla petrol pattern, NOT a removed check |
| Engine drowns instantly at spawn | Missing `drown_engine` memory point, so it defaults to (0,0,0) | Add `drown_engine` at the engine in the Memory LOD (see the memory-point catalog in `vehicle-structural-parity.md`) |
| RPT: `unknown animation source damper` | `AnimationSources` damper class missing | Add `class damper_X_Y { source="user"; ... }` for all four (§10) |
| Revs but no torque / stalls weirdly | `torqueCurve[]` starts/ends nonzero or rpm bands wrong | Curve must start at 0 Nm (stall rpm) and return to 0 at redline; keep `rpmIdle<rpmMin<rpmClutch<rpmRedline` |
| Steers but wheels don't spin | `animRotation` source not wired in model.cfg, or no `wheel_X_Y_axis` | §12 wheel class + 2-point axis in Memory |

**Use the Diag binary.** Every simulation property can be debugged live in the Diag build of the game: open the diag menu (hold Win + Alt) and go to Game -> Vehicles -> Simulation. This is the fastest way to see live engine, RPM, wheel-contact and suspension state: measure, don't guess.

**`OnDebugSpawn` traps (measured on a quad build).** It must `CreateAttachment` the drivetrain by **CLASS name, not slot name** (`"<Mod>_Wheel_Front"`, not the slot `"<Mod>_wheel_1_1"`); in vanilla the slot and the class share a name, so the bug stays masked until your custom slots differ. Add `Fill(CarFluid.FUEL, GetFluidCapacity(CarFluid.FUEL))` (and `COOLANT` if `IsVitalRadiator()`); the base only drops loose parts into cargo. Also: **`OnDebugSpawn` does NOT fire when the entity is created by the mission server in a headless harness**. Attach parts manually in that path (the MCP or admin spawn), or a "wheels missing / engine won't start" verdict is a false negative, not a real bug.

## 16. What is not established (do NOT invent these)

- `simulationclass=` string: not in the example 4x4 or reference quad configs (both rely on extending `CarScript`), and no occurrence in `P:\DZ\vehicles\wheeled\config.cpp`. Do not add one. The Arma 3 equivalent is `simulation="carx"`.
- `mass`, `centerOfMass`, `sprungMass`, `geometryClass`: not in a DayZ car config (§1). Mass and CoM come from the Geometry LOD vertex weights.
- `CentralDifferential`: the fields seen are `ratio` + `type` (example 4x4: 1.5 / `DIFFERENTIAL_LOCKED`; vanilla truck: 0.75 / `DIFFERENTIAL_LOCKED`, `P:\DZ\vehicles\wheeled\config.cpp:18564-18567`). Any property beyond those is `[unverified]`.
- `reflectors[]` array: an Arma 3 lights feature; no occurrence in `P:\DZ\vehicles\wheeled\config.cpp`.
- Custom `CfgSlots` registration in the example 4x4: not in its config.cpp (§8b); mechanism `[unverified]`.
- A separate PhysX LOD (4e13): Arma 3 requires one holding just the main body of the car, with the wheels added by the engine. The DayZ references here (the example 4x4, the reference quad, `civiliansedan`) use **Geometry 1e13 only**. Do NOT add a 4e13 LOD for a DayZ car unless verified in game.
- `type="GEARBOX_AUTOMATIC"`: native. `enum CarGearboxType {MANUAL, AUTOMATIC}` is at `P:\scripts\3_game\vehicles\car.c:23-27` and `GearboxGetMode()` returning `CarAutomaticGearboxMode` at `:269`. One vanilla car uses it: `Offroad_02` (`P:\DZ\vehicles\wheeled\config.cpp:21056`); every other vanilla car and the third-party configs above use `GEARBOX_MANUAL`. Copy the `Offroad_02` `Gearbox` block as the starting point and check the behaviour live with the Diag tool (§15).

## 17. Crew get-in resolution and the crew proxy frame

> Extends §4 (Crew) with **how the engine resolves which seat a get-in lands in**, and **how a crew proxy's geometry must be shaped** so the player sits upright at the right height facing forward. Verified in game on a quad build whose co-driver seat never worked until its crew ViewGeometry matched the reference quad's: its seat selections were spread across many collision components instead of two dedicated ones. The seat cubes must ALSO be inward-wound with point flags `0x0000003F` or a raycast does not hit them: see the crew get-in sections of `vehicle-structural-parity.md`.

### 17.1 Get-in is resolved per COLLISION COMPONENT (not per selection, not per memory point)

The engine maps a get-in to a seat through **`Transport.CrewPositionIndex(int componentIndex)`**: `proto native int CrewPositionIndex( int componentIdx )` at `P:\scripts\3_game\vehicles\transport.c:179` (native; no script body). The `componentIndex` is the **collision component** that the cursor's raycast hits when the player presses "enter". The engine pre-associates each crew slot with the component(s) that contain that slot's `actionSel` selection (the `seat_driver` / `seat_codriver` named selection from the `Crew` config, §4) **in the ViewGeometry LOD**.

So the wiring is: cursor raycast → hit component N → `CrewPositionIndex(N)` → driver / co-driver / cargo. A wheel-hub axis or a `pos_driver` memory point does NOT drive this; **only the geometry of the component carrying `seat_driver`/`seat_codriver` does.**

### 17.2 RULE: each seat needs its OWN dedicated component in the ViewGeometry

The reference quad has exactly **two** crew components in its ViewGeometry: `component24` = `seat_driver` (8 pts / 6 faces, one clean cube), `component25` = `seat_codriver` (8 pts / 6 faces). One selection, one component, per seat.

The broken quad build had the `seat_driver`/`seat_codriver` selections **spread across the whole multi-component grid** that had been copied from the Geometry LOD into the ViewGeometry: **23 crew components, 88/112 points** instead of 2. The engine then generated 23 overlapping crew components; the get-in raycast resolved to the first (driver) component every time and **never** landed on the co-driver. Symptom: **co-driver seat unusable, player only ever boards as driver.**

> **Build rule (do this for every car):** in the ViewGeometry LOD, give each seat its **own single dedicated component**: one connected cube (8 pts / 6 faces is enough) tagged ONLY with that seat's `actionSel` selection (`seat_driver` in one, `seat_codriver` in another, `seat_cargoN` each in its own). Do NOT reuse the multi-component Geometry/collision grid as the crew ViewGeo. Verify with py3d: `count of components carrying seat_* == number of seats`. If it is 20+, the get-in is broken.

To diagnose a case like this, diff the model structure against a working reference with py3d instead of theorizing about the native function, and transplant the reference structure whole instead of patching it piece by piece.

### 17.3 The crew PROXY frame = orientation + seated height (and where height actually comes from)

`Crew.proxyPos` (§4) names a **proxy in the ViewGeometry** (a 3-vertex triangle face placed as `proxy:\...`), and that proxy is what positions the player, **not** the `pos_driver` memory point or the skeleton bone. The proxy's frame is derived by **angle-sort of its three vertices** (the convention `/dayz-proxy-align` uses):

| vertex | role |
|---|---|
| widest angle | **anchor** = the proxy's position (and thus the seated player's position/height) |
| middle angle | local **+Y** |
| smallest angle | local **+Z** |

For a **crew** proxy the target frame is: **+Y → front of the vehicle, +Z → up.** Then:

- **Anchor = seated height.** Because the anchor vertex is the position, an anchor placed too high puts the player in the air. On the quad build, anchors at Y=1.46 / Y=1.70 left the player floating above the quad; the fix was to drop the anchor to seat height plus the small seat offset. Tune the **anchor Y**, not the memory point.
- **Use a canonical scalene triangle, never isosceles.** A 90/45/45 isosceles triangle (the shape you get from a hand-rolled 1 mm proxy) makes the middle and smallest angles **tie**, so the +Y/+Z assignment is ambiguous, the frame falls differently per proxy, and the **player sits sideways and spins on entry**. Always emit 3 distinct angles (e.g. 90/63.4/26.6) encoding the exact frame.
- **Do NOT copy a proxy frame from another sub-model.** The correct frame depends on which crew sub-model the proxy references. Vanilla cars reference `crew_driver` / `crew_cargo` (`proxy:\dz\vehicles\wheeled\proxies\crew_driver`), for which **+Y must point to the vehicle front**. The reference quad references `bus_driver` / `bus_cargo`, and its co-driver derives **+Y → −Z (toward the rear)**. Copying that raw triangle into a car that uses the vanilla crew sub-models gives a back-facing or otherwise wrong orientation. Match the frame to the referenced sub-model; do not transplant raw vertices across sub-models.

### 17.4 Driver's HANDS = the animation rig, not the model

The hands on the wheel or bars come from the player's **animation instance** (the anim set selected via `GetAnimInstance()`, §14; a quad can use a `QUADBIKE` set from a third-party animation mod), NOT from IK and NOT from any memory point on the vehicle. Neither the quad build nor the reference quad has hand memory points in its `.p3d`, and hand placement is **not editable from the `.p3d`**: it is a property of the rig. If the hands sit wrong, fix the anim instance, not the model.

### 17.5 Headless validation loop for crew get-in (and its limits)

You can validate the get-in **without a manual in-game test cycle** with a test mission that spawns the vehicle plus an auto-connecting client and probes each seat:

1. For `i` in `0..N`, call `Transport.CrewPositionIndex(i)` and tabulate which component maps to which seat (driver/co-driver/cargo). This alone reveals "23 components all map to driver".
2. Raycast from outside toward each seat's world position with
   **`DayZPhysics.RaycastRV(vector begPos, vector endPos, out vector contactPos, out vector contactDir, out int contactComponent, set<Object> results = NULL, Object with = NULL, Object ignore = NULL, bool sorted = false, bool ground_only = false, int iType = ObjIntersectView, float radius = 0.0, CollisionFlags flags = CollisionFlags.NEARESTCONTACT)`** (signature at `P:\scripts\3_game\global\dayzphysics.c:199`) and check that `contactComponent` is the seat's dedicated component. Compare every result against a **control vehicle that already works**.

**Limits (all measured in game on the quad build):**
- `RaycastRV` finds nothing on a server without a client: with no connected client it returns hit=0. The mission must actually connect a client.
- A **large `radius`** crosses the boundary between adjacent components and gives a false component id: use a **fine radius (~0.05)** so the hit lands inside one component.
- The raycast offset must be expressed in **LOCAL space transformed by `ModelToWorld`**, not a fixed world offset: the vehicle spawns with some pitch and roll, so a world-fixed probe misses.
- The **visual posture is NOT measurable headless**: final orientation (sitting upright vs sideways) and seated height are only confirmable by eye in game. The loop proves *which seat the get-in resolves to*; it cannot prove *how the player looks once seated* (that is §17.3 plus an in-game screenshot).

> Bottom line for a car's crew: (1) one dedicated seat component per seat in ViewGeo, counted with py3d against a working control; (2) crew proxies with canonical scalene triangles, +Y→front, +Z→up, anchor at seat height; (3) match the proxy frame to the referenced crew sub-model, never copy it raw from another; (4) hands come from the anim rig; (5) gate the get-in with the headless `CrewPositionIndex` + `RaycastRV` loop, then confirm posture by eye.

## Engine and script identifiers that fail without a log

- The engine schema is the `torqueCurve[] = {rpm, torque, ...}` table documented above. `torqueMax`, `torqueRpm`, `powerMax`, `powerRpm` and `rpmMax` have no occurrence in `P:\DZ\vehicles\wheeled\config.cpp`, and unknown properties are ignored without a log. If a config edit has no effect, verify that the property exists before tuning it.
- `VehicleAnimInstances` is fixed by `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1-15`: `CIVVAN=0`, `V3S=1`, `SEDAN=2`, `HATCHBACK=3`, `BUS=4`, `S120=5`, `MULTICAR=6`, `GOLF=7`, `HMMWV=8`, `ZODIAC=9`, and since 1.30 `MOTO1=10`, `MOTO2=11` (1.29 ended at `ZODIAC`). Return the instance that matches the model skeleton; a wrong value can fail as a missing get-in pose or clipping, not a crash.
- Offroad Hatchback door slots are exactly `NivaDriverDoors`, `NivaCoDriverDoors`, `NivaHood`, and `NivaTrunk` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:209-219`; `NivaHood` also at `:146` and `:160`, `NivaTrunk` at `:189`). Slot lookup and SoundSet names are case-sensitive; a mismatch returns no attachment or no sound without a clear diagnostic.

## A ruined wheel needs script, not only a config class

On 1.29, declaring `<Mod>_Wheel_Ruined` in `CfgVehicles` and shipping the destroyed `.p3d` changes nothing in game: the wheel reaches 0 health still wearing its healthy model. The swap is done by `CarWheel.EEHealthLevelChanged` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:220-248`), which asks `GetRuinedReplacement()`. On 1.29 that method is a `switch` over **seven hardcoded vanilla classnames** (1.29 behaviour, not checked on `P:\`, which holds 1.30): HatchbackWheel, CivSedanWheel, Hatchback_02_Wheel, Sedan_02_Wheel, Truck_01_Wheel, Truck_01_WheelDouble, Offroad_02_Wheel. Anything else returns `""`, and an empty name makes the handler do nothing at all. The 1.29 fix is four leaf classes. Do NOT `modded class CarWheel`: that reaches the wheels of every vehicle on the server.

    class <Mod>_Wheel_Front extends CarWheel
    { override string GetRuinedReplacement() { return "<Mod>_Wheel_Front_Ruined"; } }
    class <Mod>_Wheel_Front_Ruined extends CarWheel_Ruined
    { override string GetReplacement() { return "<Mod>_Wheel_Front"; } }

Keep the override on the LEAF, never on a shared base. The ruined class inherits `GetRuinedReplacement` from `CarWheel`, whose switch does not match it either, and that is what stops a ruined wheel from swapping itself forever.

**On 1.30 the name is derived, so these overrides are no longer needed.** `GetRuinedReplacement()` returns the name `CarWheelType.SetReplacementTypes()` set when the first wheel of the class was created, `<class>_Ruined`, and that call logs an error when the config class does not exist (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:215-218`, `P:\scripts\4_world\entities\core\inherited\inventoryitemtype.c:17-46`). A 1.30 mod wheel needs the `_Ruined` config class and an empty script class that extends `CarWheel_Ruined`; overrides like the ones above still compile and return the same names. The vanilla pattern and the in-game runs on 1.30.164200 are in `dayz-1-30-vehicles.md`, section 11.

- **The ruined model needs its own `CfgNonAIVehicles` proxy.** A proxy binds one model file to the slots it may fill, so without it the engine has no route to draw the new mesh once the attachment is replaced. Vanilla declares one per destroyed wheel, `inventorySlot[]` copied verbatim from the healthy proxy and only `model=` changed (`P:\DZ\vehicles\wheeled\config.cpp:23981`, `:24035`, `:24076`, `:24094` and `:24187`). The class name must mirror the proxy file basename: `ProxySedanWheel_destroyed` and `sedanWheel_destroyed.p3d`. Breaking that pair gives the native client crash on the swap at speed described in `rip-import.md`.
- **Repair needs no config work.** `PluginRepairing.CanRepair` opens with `state != GameConstants.STATE_RUINED` (`P:\scripts\4_world\plugins\pluginbase\pluginrepairing.c:96`) and every repair route (kit in hands, the crafting recipes, `ItemBase.CanRepair`) goes through that one function, so an inherited `repairableWithKits[]` on the ruined class is harmless. Do not invent a mechanic to block what the engine already refuses.
- **`GetReplacement()` is diagnostic only.** Its single consumer is under `#ifdef DIAG_DEVELOPER` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:350-366`, the debug "fix the whole car"): live in DayZDiag, compiled out of retail. Implement it for parity, never describe it as repair.
- **Register the heavy in-hands IK for the ruined leaf classes too**, or a destroyed wheel taken in hands falls back to the one-handed profile: the profile is looked up by exact leaf class. Vanilla registers all seven (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:876`, `:884`, `:886`, `:893`, `:903`, `:913`, `:923`), 1.30 also the four ruined motorbike wheels (`:933`, `:935`, `:937`, `:939`), and reuses the healthy `.anm` where no destroyed pose exists.

**The physical radius comes from the envelope, not from one distance.** A modelled flat tyre is usually collapsed over a sector, not all round: on one quad build the axis-to-lowest-point figure was 0.276 m, but the outer envelope sampled every 10 degrees had median 0.3275 and peak 0.3588, so that single number would have buried the intact rubber up to 83 mm at other rotations. Measure `max(hypot(y,z))` per angular bin and pick from the upper middle of that distribution; the minima are the rips, where no rubber reaches the ground anyway. Flatten `radiusByDamage[]` to the same value, or the inherited healthy curve resolves the ruined wheel to its bottom entry.

**Geometry inherited from the healthy wheel is single-sided, and the tear exposes its back.** The rim lives sealed inside an intact tyre, so nothing ever sees its reverse; open the tyre and the player looks straight through the wheel. Do not reach for `face.flags`: `binarize.exe` discards the MLOD per-face flags entirely (`skills/dayz-p3d-audit/references/winding-diagnostics.md`). Double-side only the exposed component: on that quad build, `radius < 0.18` isolated exactly 302 faces in BOTH the healthy and the ruined mesh, which is what made the cut a boundary of the mesh instead of a guess. `py3d.LOD.make_double_sided()` duplicates the whole LOD; copy its normal-pool dedup with a face filter. Gate it with a first-hit raycast that culls before the depth test: if two coincident twins tie on `t` and either faces the camera, the pixel is drawn, and an instrument that picks the nearest hit by `argmin` alone reports the FIX as a regression.

Status of the ruined-wheel work: the swap, the model, the slots, the in-hands profile and driving were verified in game; the double-sided rim was verified offline only (14 directions, healthy control 0, delivered-model control 1361, patched 0), not yet looked at in game.
