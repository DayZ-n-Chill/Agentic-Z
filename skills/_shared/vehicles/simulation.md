# Vehicle simulation config

The `class SimulationModule` keys that drive a car or a boat: steering, throttle, brakes, engine, clutch, gearbox, differentials, axles, suspension and wheels.

Inherit `SimulationModule` from the parent and write only the subclasses and keys you change (`class SimulationModule: SimulationModule`, as every vanilla car does, `P:\DZ\vehicles\wheeled\config.cpp:1371`). Each nested class must also inherit its parent's class of the same name (`class Axles: Axles`, `class Front: Front`, `class Wheels: Wheels`, `class Left: Left`), or the keys the parent set inside it are lost.

## Cars

Reference blocks: `RearDrive` (`P:\DZ\vehicles\wheeled\config.cpp:437` to `:532`) and `OffroadHatchback` (`:1371` to `:1500`).

| Class or key | Vanilla example | What it sets |
|---|---|---|
| `Steering` | `maxSteeringAngle=30`; `increaseSpeed[]`, `decreaseSpeed[]`, `centeringSpeed[]` as speed and value pairs (`:1373`) | Wheel lock and how fast steering moves at each speed. |
| `Throttle` | `reactionTime`, `defaultThrust`, `gentleThrust`, `turboCoef`, `gentleCoef` (`:1380`) | Pedal response. |
| `Brake` | `pressureBySpeed[]`, `gentleCoef`, `minPressure`, `reactionTime`, `driverless` (`:1388`) | Brake pressure curve. |
| `Aerodynamics` | `frontalArea`, `dragCoefficient`; `RearDrive` adds `downforceCoefficient`, `downforceOffset[]` (`:462`) | Drag and downforce. |
| `drive` | `"DRIVE_AWD"` (`:1401`); vanilla also uses `DRIVE_RWD`, `DRIVE_FWD` and, for six wheels, `DRIVE_642` (`:764`) | Which axles are driven. |
| `Engine` | `torqueCurve[]` as rpm and torque pairs, `inertia`, `frictionTorque`, `rollingFriction`, `viscousFriction`, `rpmIdle`, `rpmMin`, `rpmClutch`, `rpmRedline` (`:1402`) | Power and rev range. `rpmRedline` matters to damage; see `damage.md`. |
| `Clutch` | `maxTorqueTransfer`, `uncoupleTime`, `coupleTime` (`:1414`) | |
| `Gearbox` | `type="GEARBOX_MANUAL"`, `reverse`, `ratios[]` (`:1420`); `Offroad_02` uses `GEARBOX_AUTOMATIC` (`:21056`) | Gear count is the length of `ratios[]`. |
| `CentralDifferential` | `ratio`, `type="DIFFERENTIAL_LOCKED"` (`:1426`) | Only on all wheel drive. |
| `Axles` then `Front`, `Rear` | `maxBrakeTorque`, `maxHandbrakeTorque`, `wheelHubMass`, `wheelHubRadius` (`:1433`) | One class per axle; trucks add `class Middle: Rear` (`:810`). |
| `Differential` inside an axle | `ratio`, `type="DIFFERENTIAL_OPEN"` (`:1439`) | |
| `Suspension` inside an axle | `stiffness`, `compression`, `damping`, `travelMaxUp`, `travelMaxDown` (`:1444`) | |
| `Wheels` then `Left`, `Right` | `inventorySlot`, `animTurn`, `animRotation`, `animDamper`, `wheelHub` (`:289` in `CarScript`; overrides at `:1452`) | Ties each wheel to its inventory slot, its model animations and its hub memory point. |

The `CarScript` base sets the wheel animation names (`turnfrontleft`, `wheelfrontleft`, `damperfrontleft`) and hub memory points (`wheel_1_1_damper_land` and so on) at `:283` to `:327`. A new model must have those animations in its `model.cfg` and those memory points in its memory LOD, or override them in `Wheels`. `OffroadHatchback` overrides only `animDamper` and `inventorySlot` (`:1452` to `:1463`).

Dampers also need an `AnimationSources` entry each with `source="user"` (`OffroadHatchback`, `:1521` to `:1536`).

Wheel physics live on the wheel item, not the car: `radius`, `width`, `tyreType`, `tyreRoughness`, `tyreGrip`, `tyreRollResistance`, `tyreOffroadResistance`, `tyreLongitudinalFriction`, `tyreLateralFriction` and `radiusByDamage[]` (`HatchbackWheel`, `:853` to `:881`). Wheel items inherit `CarWheel`, which sets `simulation="carwheel"` (`:14` to `:23`).

## Boats

Reference block: `Boat_01_ColorBase` (`P:\DZ\vehicles\water\config.cpp:124` to `:180`). A boat module has no axles or wheels.

| Class | Keys |
|---|---|
| `Engine` (`:126`) | Same keys as a car engine. |
| `Clutch` (`:138`) | `maxTorqueTransfer`, `uncoupleTime`, `coupleTime`. |
| `Gearbox` (`:144`) | `reverse`, `ratios[]` (one forward gear, `0.88`). |
| `Throttle` (`:149`) | `defaultThrust`, `turboIncrease`, `regularIncrease`, `slowIncrease`, `turboDecrease`, `regularDecrease`, `slowDecrease`, `autoDecrease`. |
| `Steering` (`:160`) | As for cars. |
| `Propeller` (`:167`) | `position[]`, `radius`, `outerRadius`, `innerRadius`, `efficiency`, `cavitationThreshold`, `pitch`, `width`, `numberOfBlades`, `mass`. |

Floating is set outside the module by `class Buoyancy` on `BoatScript`: `linearDampeningCoefficient`, `angularDampeningCoefficient`, `linearDragCoefficient`, `quadraticDragCoefficient`, `falloffPower`, `sinkRate` (`:32`). The native `Boat` class sets `canFloat=1`; `Car` sets `canFloat=0` (`P:\bin\config.cpp:1455`, `:1429`).

What a boat does at run time (engine stop out of water, decay, water particles, its actions, get-in that is always free) and the truck's three axles and double wheels are in `vehicle-types-boat-truck.md`. A complete car module with every class filled in is in `vehicle-config-and-modelcfg.md`, section 3.

## Reading the simulation from script

`Car` exposes the live state natively (`P:\scripts\3_game\vehicles\car.c`): `GetSpeedometer()` (`:102`), `EngineGetRPM()` (`:227`), `EngineGetRPMRedline()` (`:224`), `EngineGetRPMMax()` (`:221`), `EngineIsOn()` (`:230`), `GetGear()` (`:248`), `GearboxGetType()` (`:266`), `WheelCount()` (`:345`), `WheelHasContact(int)` (`:286`), `WheelGetWaterState(int)` (`:328`). `Car.OnGearChanged(int newGear, int oldGear)` is called on every shift (`:401`). `Boat` has the same engine and gear calls plus `PropellerGetPosition()` and `PropellerGetAngularVelocity()` (`P:\scripts\3_game\vehicles\boat.c:125`, `:128`).

Tune numbers by changing one class at a time and driving it in game; the values interact and P:\ has no documentation of their units.

## Rules that come out of the config, checked on `P:\`

- **List every axle in an `Axles` override.** Vanilla repeats both `class Front: Front` and `class Rear: Rear` in every override of `Axles` (`RearDrive`, `P:\DZ\vehicles\wheeled\config.cpp:494` to `:510`; `OffroadHatchback`, `P:\DZ\vehicles\wheeled\config.cpp:1431` to `:1466`). A third-party quad that listed only `Rear` reported two wheels instead of four in game and would not move, while `Engine`, `Clutch` and `Gearbox`, which were not redeclared at all, were inherited. Field notes: `invariants-wheels-and-hubs.md`.
- **The steering ramp belongs to the lock angle it was written for.** `increaseSpeed[]` is pairs of speed and steering rate (km/h and degrees per second, as read from the in-game test in invariant 15f; the units are not yet checked on `P:\`), so time to full lock is `maxSteeringAngle` divided by the rate. `OffroadHatchback` pairs `maxSteeringAngle=30` with `increaseSpeed[]={0,40,30,20,100,5}` (`P:\DZ\vehicles\wheeled\config.cpp:1375-1376`). Raising the angle on a copied block without raising the rates makes the car turn less in practice. Field notes: invariant 15f in `invariants-engine-fluids-and-handling.md`.
- **Vanilla `tyreGrip` on healthy wheels** runs from `0.80` (`HatchbackWheel`, `P:\DZ\vehicles\wheeled\config.cpp:877`) to `1.0` (`P:\DZ\vehicles\wheeled\config.cpp:18145`); ruined wheels sit between `0.2` and `0.5`. **Vanilla `tyreRollResistance`** on healthy wheels runs from `0.008` (`CivSedanWheel`, `P:\DZ\vehicles\wheeled\config.cpp:4782`) to `0.018` (`P:\DZ\vehicles\wheeled\config.cpp:18144`). A value ten times lower than that band lets the vehicle creep on any slope. Field notes: invariants 15c, 17 and 18.
- **A parked vanilla car holds still because it is braked, not through friction.** Every vanilla `Brake` class sets `driverless=0.1` (`P:\DZ\vehicles\wheeled\config.cpp:460`), and the push action turns that brake off with `SetBrakesActivateWithoutDriver(false)` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:95`).
- **`Clutch.maxTorqueTransfer` caps what reaches the wheels.** Vanilla values run from `165` (`P:\DZ\vehicles\wheeled\config.cpp:14125`) to `720` (`P:\DZ\vehicles\wheeled\config.cpp:779`); compare it with the peak of `torqueCurve[]` before adding torque.
- **Mass is not a config key.** It is the sum of the per-point mass in the model's Geometry LOD. To change it, scale every point by one factor and scale `stiffness`, `damping` and `compression` by the same factor, never `travelMaxUp` or `travelMaxDown`. Field notes: invariants 15f and 15g.
- **Hub height.** `wheelHub` names a selection in the Geometry and Memory LODs (`wheel_1_1_damper_land`, `P:\DZ\vehicles\wheeled\config.cpp:297`), not the visual wheel. Field notes on hub level against tyre radius, hub size and `LandContact`: `invariants-wheels-and-hubs.md`.

Measured launch, braking and gear change figures for `CivilianSedan`, and a way to rank drive layouts by wheel force against grip, are at the end of `invariants-engine-fluids-and-handling.md`.
