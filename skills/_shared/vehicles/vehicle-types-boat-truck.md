# Boats, trucks and quads

What changes when the vehicle is not a four-wheeled car: boats, which sit beside `Car` under `Transport`; trucks, which are a `CarScript` config with three axles and double wheels; and mod-made quads. Motorbikes have their own files (`motorbikes.md`, `motorbike-invariants.md`).

The short class tree is in `class-hierarchy.md` and the `SimulationModule` keys in `simulation.md`; this file adds the detail per type. A line marked DayZ 1.29 describes a build that is not on `P:\` and is not checked there.

## Cars and boats are siblings

| Class | Source |
|---|---|
| `Transport`, extending `Pawn` with `FEATURE_NETWORK_RECONCILIATION` or `EntityAI` without it | `P:\scripts\3_game\vehicles\transport.c:66` to `:69` |
| `Car extends Transport`, scripted as `CarScript` | `P:\scripts\3_game\vehicles\car.c:87`; `P:\scripts\4_world\entities\vehicles\carscript.c:94` |
| `Boat extends Transport`, scripted as `BoatScript : Boat` | `P:\scripts\3_game\vehicles\boat.c:28`; `P:\scripts\4_world\entities\vehicles\boatscript.c:41` |
| `Motorbike extends Transport` (since DayZ 1.30, `simulation = "motorbike"`); `MotorbikeScript` does not inherit `CarScript` | `P:\scripts\3_game\vehicles\motorbike.c:30`; `P:\bin\config.cpp:1481` to `:1486` |

In config the boat base is `class BoatScript: Boat` (`P:\DZ\vehicles\water\config.cpp:17`) with `Boat_01_ColorBase: BoatScript` at `:47`; the truck base is `Truck_01_Base: CarScript` (`P:\DZ\vehicles\wheeled\config.cpp:18429`).

A boat inherits nothing wheeled and a car nothing buoyant, which decides where each feature lives:

| Feature | Lives on |
|---|---|
| Crew, get-in, flip detection, fuel point, lights, physics helpers | `Transport`, shared |
| Wheels, brakes, handbrake, `CarFluid` oil, brake fluid and coolant | `Car` only |
| Propeller, buoyancy, `BoatFluid` | `Boat` only |

Since DayZ 1.30 the shared fluid enum is `ETransportFluid` (`transport.c:52` to `:63`): `CarFluid` aliases it (`car.c:18`), as do `BoatFluid : ETransportFluid {}` (`boat.c:13`) and `MotorbikeFluid` (`P:\scripts\3_game\vehicles\motorbike.c:14`). `BoatScript` still uses only fuel. On DayZ 1.29 `BoatFluid` held fuel alone and `CarFluid` declared its own values.

## What `Transport` provides

| Feature | Source |
|---|---|
| Native crew: `CrewSize`, `CrewMemberIndex`, `CrewMember`, `CrewDriver`, `CrewEntry`, `CrewEntryWS`, `CrewTransform`, `CrewGetIn`, `CrewGetOut`, `CrewDeath` | `transport.c:175` to `:212` |
| `OnDriverEnter`, `OnDriverExit` | `:218` to `:224` |
| `LightIsOn`, `LightOn`, `LightOff`, `LightToggle`, `OnBeforeLightOn`, `UpdateLights` | `:227` to `:255`, `:362` |
| Fuel position from the memory point `refill`, `GetRefillPointPosWS` | `:112` to `:115`, `:459` to `:472` |
| Flip detection: `DetectFlipped`, `IsFlipped`, water-aware `DetectFlippedUsingSurface` | `:522` to `:619` |
| `ApplyForce`, `ApplyTorque`, `ApplyImpulseAt` and the other physics helpers | `:260` to `:275` |
| `IsAreaAtDoorFree` | `:844` to `:899` |
| `GetVehicleType()`, `"VehicleTypeUndefined"` on the base | `:454` to `:457` |
| Buoyancy state on the owner: `SetBuoyancySubmerged`, `GetBuoyancySubmerged` | `:22` and `:23` |

`Car` adds the native wheel calls (`WheelCount`, `WheelCountPresent`, `WheelGetAngularVelocity`, `WheelHasContact`, `WheelGetSurface`, `WheelGetWaterState`, `WheelGetEntity`, `WheelIsLocked`, `car.c:272` to `:348`; `CarWheelWaterState` at `:67` to `:72`), brakes and handbrake (`GetBrake`, `SetBrake`, `GetHandbrake`, `SetHandbrake`, `SetBrakesActivateWithoutDriver`, `:200` to `:212`), `GetSpeedometer` (`:102`) and flip detection by wheel contact (`DetectFlippedUsingWheels`, `:157` to `:178`). A boat has no brake calls. Since DayZ 1.30 `Boat` also has `GetSpeedometer()` and `GetSpeedometerAbsolute()` (`boat.c:42` to `:56`).

`CarScript.SetActions()` adds `ActionOpenCarDoorsOutside`, `ActionCloseCarDoorsOutside`, `ActionGetInTransport`, `ActionSwitchLights`, the horn actions and `ActionPushCar` (`carscript.c:2313` to `:2321`). Since DayZ 1.30 the horn actions are `ActionVehicleHornShort` and `ActionVehicleHornLong`; the old `ActionCarHornShort` and `Long` are marked obsolete, and `CarHornShortActionInput` is an empty alias of `VehicleHornShortActionInput` (`dayz-1-30-vehicles.md`).

## Boats

Author a boat like a car up to the shared layer, then diverge. Do not copy a car's `Axles`, brakes or car fluids into a boat.

| Area | Boat | Source |
|---|---|---|
| Propulsion | Native propeller: `PropellerGetPosition()`, `PropellerGetAngularVelocity()` | `boat.c:125` to `:128` |
| Brakes | None | |
| Steering | `GetSteering`, `SetSteering(float)`; the car's `SetSteering` has an extra `bool` | `boat.c:59` to `:62`; `car.c:185` |
| Sound controllers | `BoatSoundCtrl` holds engine, speed and player only, no rpm or doors | `boat.c:2` to `:10` |
| Get-in | `CrewCanGetThrough`, `CanReachSeatFromSeat` and the others return `true` | `boatscript.c:205` to `:223` |
| Animation set | `VehicleAnimInstances.ZODIAC` | `boatscript.c:195` to `:198` |
| Actions | `ActionGetInTransport` and `ActionPushBoat` only | `boatscript.c:758` to `:762` |
| Type | `"VehicleTypeBoat"` | `boatscript.c:175` to `:178` |

Get-in is always open on a boat. A bare `CarScript` inherits a `CrewCanGetThrough` that returns `false` and loses its get-in prompt (`crew-get-in-geometry.md`); `BoatScript` overrides it to return `true` because the cockpit is open and has no doors.

Water physics is config. The boat base has `class Buoyancy` where a car has axles (`P:\DZ\vehicles\water\config.cpp:32` to `:40`):

```cpp
class Buoyancy
{
    linearDampeningCoefficient;
    angularDampeningCoefficient;
    linearDragCoefficient = 0.2;
    quadraticDragCoefficient = 0.2;
    falloffPower = 0.8;
    sinkRate = 0.05;
};
```

Its `SimulationModule` (`:124` to `:180`) has no `Axles`, wheels or brakes, and carries `class Propeller` (`:167` to `:179`) beside the usual engine, clutch, gearbox, throttle and steering:

```cpp
class Propeller
{
    position; radius; outerRadius; innerRadius;
    efficiency; cavitationThreshold; pitch; width;
    numberOfBlades = 3; mass;
};
```

At run time (`boatscript.c`):

- The engine stops when the propeller leaves the water, `GetWaterDepth(pos) < -0.2` then `EngineStop()` in `EOnSimulate` (`:393` to `:407`), and when fuel runs out (`:361` to `:371`).
- An empty boat decays: a server timer every 10 seconds, four times faster when flipped (`:44` to `:47`, `:110` and `:111`, `:534` to `:548`).
- Four water effects sit on memory points `ptcFxFront`, `ptcFxBack`, `ptcFxSide1`, `ptcFxSide2` (`:129` to `:144`); the classes are `EffectBoatWaterFront`, `Back` and `Side` (`P:\scripts\4_world\entities\effects\boatwatereffects.c:10`, `:116`, `:199`), and the back effect reads `PropellerGetAngularVelocity` (`:183`).
- A spark plug is the one vital part for starting (`CheckOperationalRequirements`, `:278` to `:286`); a car defaults to demanding both plugs (`invariants-engine-fluids-and-handling.md`).
- Flips are detected by the water-aware surface check, not wheels (`:490` to `:495`).
- Since DayZ 1.30, `GetHeatComfortOverride()` (`:256` to `:259`) and an AI noise class `NoiseBoatEngine { type = "sound"; strength = 30; }` (`P:\DZ\vehicles\water\config.cpp:41` to `:45`).

Boat actions, under `P:\scripts\4_world\classes\useractionscomponent\actions\`:

- `ActionStartEngineBoat` (continuous) and `ActionStopEngineBoat` (single use) cast the target to `BoatScript`, require `CrewDriver() == player`, and skip server execution when the move strategy is `PHYSICS` (`actionstartengineboat.c:9` to `:70`, `actionstopengineboat.c:1` to `:52`). Start calls `OnIgnition()` in `OnExecute` and `EngineStart()` in `OnFinishProgress` (`actionstartengineboat.c:58`, `:69`); stop calls `EngineStop()` (`actionstopengineboat.c:51`).
- `ActionPushBoat extends ActionPushObject`, full body, syncing its push sound on start and end (`actionpushboat.c:17` to `:46`).
- `ActionRepairBoatChassis` and `ActionRepairBoatEngine` extend `ActionRepairVehiclePartBase`. The chassis action repairs any zone but `Engine` between worn and ruined (`actionrepairboatchassis.c:33` to `:37`); the engine action repairs only `Engine` in that band, with the engine off and a charged blowtorch (`actionrepairboatengine.c:26` to `:48`).

## Trucks

`Truck_01_Base` is a plain `CarScript` config; every difference is config.

| Feature | Truck | Source |
|---|---|---|
| Axles | Three: `class Front`, `class Middle: Rear`, `class Rear: Rear` | `P:\DZ\vehicles\wheeled\config.cpp:18569` to `:18672` |
| Drivetrain | `drive="DRIVE_642"` with a locked central differential | `:18539`; `:18564` to `:18568` |
| Wheel slots | Six hubs `Truck_01_Wheel_1_1` to `2_3` plus two spares; only the four middle and rear hubs are driven, since `class Front` has no `Differential` | `:18441` to `:18448`; `:18571` to `:18597`, base `:287` to `:308` |
| Double wheel | The four rear slots take `Truck_01_WheelDouble`: `width=0.40` against 0.20, `weight=50000` against 30000, better grip | `:18128` to `:18141` |
| Crew | Two seats. The truck declares no `class Crew` and inherits the two-seat one of the `CarScript` base (`:265` to `:283`); its `GetSeatAnimationType` maps only seats 0 and 1 (`P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c:130` to `:138`). The four-seat block at `:1348` to `:1366` belongs to `OffroadHatchback`. | |
| Cargo | `itemsCargoSize[]={10,40}` | `:18674` to `:18677` |
| Fuel | `fuelCapacity=120`, `fuelConsumption=30` | `:18506` and `:18507` |

One attachment class per rear hub covers both physical tyres through the `Truck_01_WheelDouble.p3d` model; there are not two wheel entities per hub. The rear axles reference it by `inventorySlot` (`:18598` to `:18668`), and each middle and rear wheel declares `wheelHub`, `animDamper`, `animTurn` and `animRotation`. Two `Truck_01_Wheel` ingredients craft into a double wheel and a crowbar or lug wrench takes it apart (`P:\scripts\4_world\classes\recipes\recipes\crafttruck01doublewheel.c:27` to `:46`; `decrafttruck01doublewheel.c:36`, `:48` to `:60`).

So a truck's structure is a car's (`vehicle-structural-parity.md`) with six hubs instead of four, the rear four each resolving to one double wheel class, three axle blocks with a locked centre differential, and the base's two-seat crew. Get-in, damage zones and the vital igniter rules do not change.

Since DayZ 1.30 the abandoned cistern wrecks `Land_Wreck_Truck01_Aban1_Cistern` and `Land_Wreck_Truck01_Aban2_Cistern` extend `Well`: they are water sources, not vehicles (`P:\scripts\4_world\entities\building\wrecks\wreck_truck01_aban1_cistern.c:1`).

## Quads

Vanilla has no quad. Mod quads are plain `CarScript` cars with their slots grouped under `Chassis` instead of `Body` (third-party mod practice, not checked on `P:\`). Everything else follows the car files; the test quad behind many of this pack's measurements is built exactly that way.

## Motorbikes

Since DayZ 1.30 the game ships `class Motorbike: Transport`, `MotorbikeScript` (not a `CarScript`), two bikes (`Motorbike_01` and `Motorbike_02` in `vehicles_singletrack.pbo`) and a two-wheel `SimulationModule` with `Wheels{Front,Rear}` instead of `Axles`, `Steering.maxLeanAngle[]` and `tipoverAngle`, and `Brakes{Front input=1, Rear input=0}` (`P:\DZ\vehicles\singletrack\config.cpp:263` to `:378`, `Motorbike_01_ColorBase`). Never derive a bike's lean and balance from the four-wheel `Axles` blocks. The full contract is in `motorbikes.md` and the other motorbike files.
