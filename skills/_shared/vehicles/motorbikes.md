# Motorbikes

Which classes a motorbike starts from, which addon it requires, how it differs from a car, and what its config class and script class must contain. Motorbikes (single-track vehicles) are a vanilla vehicle family from DayZ 1.30 on.

Open only the file the current step needs.

| Question | File |
|---|---|
| The rules that break a motorbike when ignored, measured tuning lessons, what is unfinished in 1.30 | `motorbike-invariants.md` |
| The `MotorbikeScript` config class and the `Motorbike_01` against `Motorbike_02` key table | `motorbike-config-contract.md` |
| The vanilla `SimulationModule` and `AnimationSources` of `Motorbike_01` | `motorbike-simulation-config.md` |
| The vanilla damage zones, damage materials and wheel classes of `Motorbike_01` | `motorbike-damage-and-wheel-config.md` |
| Native `Motorbike` API, callbacks, `MotorbikeScript` lifecycle | `motorbike-script-api.md` |
| Start, stop, pick-up and repair actions, HUD, lights, horn, particles, sound classes | `motorbike-actions-hud-lights-sounds.md` |
| Rider pose, animation graph, third-person camera, custom poses | `motorbike-rider-animation.md` |
| Full checklist for a new motorbike, what to measure in the model | `motorbike-forward-contract.md` |
| What the vanilla models contain, at a glance and how to read the tables | `motorbike-vanilla-p3d-anatomy.md` |
| Full model tables of each vanilla bike (LODs, bones, animations, memory points, proxies) | `motorbike-01-model-anatomy.md`, `motorbike-02-model-anatomy.md` |
| Every vanilla file the motorbike files cite, with line counts | `motorbike-vanilla-sources.md` |
| Porting a 1.29 car mod to the 1.30 vehicle scripts | `dayz-1-30-vehicles.md` |

## The class tree

A motorbike exists as a config class in `CfgVehicles` and as a script class of the same name, like every vehicle. `Motorbike` is a sibling of `Car` and `Boat` under `Transport`. It is not a child of `Car`, and `MotorbikeScript` does not inherit `CarScript`.

| Layer | Classes | Where |
|---|---|---|
| Native config | `class Motorbike: Transport` with `simulation="motorbike"` | `P:\bin\config.cpp:1481` and `:1486` |
| Native script (3_Game) | `MotorbikeFluid`, `MotorbikeType`, `MotorbikeOwnerState`, `MotorbikeMove`, `class Motorbike extends Transport` | `P:\scripts\3_game\vehicles\motorbike.c:14`, `:16`, `:20`, `:25`, `:30` |
| Script (4_World) | `MotorbikeScriptOwnerState`, `MotorbikeScriptMove`, `class MotorbikeScript : Motorbike` | `P:\scripts\4_world\entities\vehicles\motorbikescript.c:23`, `:27`, `:53` |
| Config base | `class MotorbikeWheel: CarWheel`, `class MotorbikeScript: Motorbike` | `P:\DZ\vehicles\singletrack\config.cpp:20`, `:23` |

## Vanilla motorbikes to inherit from

Both are in `P:\DZ\vehicles\singletrack\config.cpp` (`config.cpp` below), with script classes in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\`.

| Config class | Line | Script class | Notes |
|---|---|---|---|
| `Motorbike_01_ColorBase` | `config.cpp:220` (`scope=1`, `config.cpp:222`) | `motorbike_01.c:1` | Three gears (`ratios[]`, `config.cpp:338`), flip-up seat (`SeatDriver`), rider instance `MOTO1`. Colours `Motorbike_01_Blue`, `_Yellow`, `_Red` (`config.cpp:991`, `:995`, `:1007`). |
| `Motorbike_02_ColorBase` | `config.cpp:1401` (`scope=1`, `config.cpp:1403`) | `motorbike_02.c:1` | Four gears (`ratios[]`, `config.cpp:1528`), three fairing slots (`Motorbike_02_ShieldFront`, `_ShieldLeft`, `_ShieldRight`, `config.cpp:1406` to `:1415`), rider instance `MOTO2`. Colours `Motorbike_02_Red`, `_Yellow`, `_Blue`, `_Green` (`config.cpp:2269`, `:2273`, `:2287`, `:2301`). |

Each bike has its own wheel classes on `MotorbikeWheel`, with a `_Ruined` child each: `Motorbike_01_Wheel_1` and `Motorbike_01_Wheel_2` (`config.cpp:154`, `:187`), `Motorbike_02_Wheel_1` and `Motorbike_02_Wheel_2` (`config.cpp:1019`, `:1051`). The wheel proxies are declared in `CfgNonAIVehicles` (`config.cpp:2316` to `:2350`).

Two ways to make a motorbike, as for a car:

1. A variant of a vanilla bike (new colour, retuned engine, same model). Inherit `Motorbike_01_ColorBase` or `Motorbike_02_ColorBase` in config and write only the changed keys. The vanilla script class already implements every override.
2. A new model. Inherit `MotorbikeScript` in config and in script, and copy the structure of `Motorbike_01_ColorBase`. The rules in `motorbike-invariants.md` apply.

## Addon to require

| Parent comes from | `requiredAddons[]` entry | Defined at |
|---|---|---|
| `MotorbikeScript`, `MotorbikeWheel`, either vanilla bike | `DZ_Vehicles_Singletrack` | `P:\DZ\vehicles\singletrack\config.cpp:3` |

`DZ_Vehicles_Singletrack` itself requires `DZ_Data` and `DZ_Vehicles_Wheeled` (`P:\DZ\vehicles\singletrack\config.cpp:8` to `:12`). A shared part such as `SparkPlug` comes from `DZ_Vehicles_Parts` (`class-hierarchy.md`, "Addons to require").

## How a motorbike differs from a car

| Car subsystem | On a motorbike | Where |
|---|---|---|
| `class Axles` in `SimulationModule` | None. `class Wheels` holds `class Front` and `class Rear` directly. | `P:\DZ\vehicles\singletrack\config.cpp:73` to `:91` |
| Doors | None. `IsAreaAtDoorFree` returns `true`; `CrewCanGetThrough`, `CanReachSeatFromSeat` and `CanReachDoorsFromSeat` return `true`; `CanReachSeatFromDoors` returns `true` only when the player stands within `pDistance` of the seat memory point (height ignored). | `P:\scripts\3_game\vehicles\motorbike.c:60` to `:68`; the reach checks at `motorbikescript.c:469` to `:504` |
| Radiator and coolant | Not vital: `IsVitalRadiator()` returns `false`. | `P:\scripts\4_world\entities\vehicles\motorbikescript.c:321` to `:324` |
| Fluids | Capacities for fuel, oil, coolant and brake fluid are declared (`fuelCapacity`, `oilCapacity`, `coolantCapacity`, `brakeFluidCapacity`), but the script only uses `MotorbikeFluid.FUEL`. | `P:\DZ\vehicles\singletrack\config.cpp:30` to `:33` |
| Battery | Depends on the override. `NeedElectricitySourceDevice()` returns `true` by default and `MotorbikeScript` does not change it; both vanilla bikes return `false`. | `P:\scripts\3_game\vehicles\transport.c:821` to `:824`; `motorbike_01.c:33` to `:36`, `motorbike_02.c:34` to `:37` |
| Brakes | Two channels. `SetBrake` is the rear brake and `SetHandbrake` the front brake; config binds `Front` to `input=1` and `Rear` to `input=0`. There is no parking brake. | `P:\scripts\3_game\vehicles\motorbike.c:129` to `:139`; `config.cpp:292`, `:301` |
| Steering | Lean and tip-over curves in `class Steering` (`tipoverAngle`, `maxLeanAngle[]`, `maxSteeringAngle[]`), read by the native simulation. | `P:\DZ\vehicles\singletrack\config.cpp:266` to `:278` |
| Standing still | A kickstand, deployed in the constructor with `SetKickstand(1)`. | `P:\scripts\4_world\entities\vehicles\motorbikescript.c:141` |
| Falling | The bike can fall (`FallOver`, `IsFallen`), ejects its crew when fallen (`CrewShouldEject`) and is picked up with `ActionPickUpMotorbike`. | `P:\scripts\3_game\vehicles\motorbike.c:112` to `:115`; `motorbikescript.c:464` to `:467`, `:367` |
| Leaving in gear | The engine stops when the driver leaves with a gear engaged (`OnDriverExit`). | `P:\scripts\4_world\entities\vehicles\motorbikescript.c:217` to `:223` |
| Vehicle HUD | `GetVehicleType()` returns `"VehicleTypeMotorbike"`, which selects `MotorbikeHud`. | `P:\scripts\4_world\entities\vehicles\motorbikescript.c:316` to `:319` |
| Third-person camera | Its own camera, `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE`, returned by `Get3rdPersonCameraType`. | `P:\scripts\4_world\entities\vehicles\motorbikescript.c:454` to `:457` |

## What the script class must override

`MotorbikeScript` already implements the seat and reach checks a car has to write: `GetSeatAnimationType` (`motorbikescript.c:449`), `Get3rdPersonCameraType` (`:454`), `CrewCanGetThrough` (`:469`), `CanReachSeatFromSeat` (`:474`), `CanReachSeatFromDoors` (`:479`) and `CanReachDoorsFromSeat` (`:501`). A new bike that inherits it directly still needs these, as both vanilla bikes show (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c`):

| Override | Vanilla value | In `Motorbike_01` | Default it replaces |
|---|---|---|---|
| `int GetAnimInstance()` | `VehicleAnimInstances.MOTO1` (10) or `MOTO2` (11) | `motorbike_01.c:48` to `:51` | `Error("GetAnimInstance() not implemented")` (`P:\scripts\3_game\vehicles\transport.c:662` to `:665`) |
| `bool HasDirectionalInOutAction()` | `true` | `motorbike_01.c:53` to `:56` | `Transport` version at `transport.c:677` |
| `int GetSeatAnimationTypeDirectional(int posIdx, int directionIndex)` | `0` from the left, `1` from the right, for the driver | `motorbike_01.c:58` to `:69` | `Error("GetSeatAnimationTypeDirectional() not implemented")` (`P:\scripts\3_game\vehicles\transport.c:690` to `:693`) |
| `bool NeedElectricitySourceDevice()` | `false` (no battery) | `motorbike_01.c:33` to `:36` | `true` (`transport.c:821` to `:824`) |
| `float GetTransportCameraDistance()` | `2.5` | `motorbike_01.c:38` to `:41` | `Transport` version at `transport.c:649` |
| `vector GetTransportCameraOffset()` | `"0 1.3 -0.25"` | `motorbike_01.c:43` to `:46` | `Transport` version at `transport.c:657` |

`MOTO1` and `MOTO2` are the last two entries of `VehicleAnimInstances` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13` to `:14`). The directional seat animation is read only when `HasDirectionalInOutAction()` returns `true` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:81` to `:100`), so a bike that overrides only `GetSeatAnimationTypeDirectional` ignores its left and right get-in animations.

The constructor sets what the base leaves empty (`motorbike_01.c:3` to `:26`): the contact damage coefficients `m_VehicleContactDamageCoef` and `m_CrewContactDamageCoef`, the engine sound sets (`m_EngineStartOK`, `m_EngineStartFuel`, `m_EngineStop`, `m_EngineStopFuel`), the light profiles and horn sounds, and `SetEnginePos`. `Motorbike_01` also overrides `CanGetIn` to require the seat down (`motorbike_01.c:92` to `:98`) and `IsVitalGlowPlug` to `false` (`motorbike_01.c:82` to `:85`).

## What the config class must contain

| Block | Vanilla example | Notes |
|---|---|---|
| `class Crew` | `P:\DZ\vehicles\singletrack\config.cpp:52` to `:70` | `Driver` and `CoDriver: Driver`; both have `isDriver=1` and `actionSel="seat_driver"`. |
| `class SimulationModule` | base `config.cpp:71` to `:92`, `Motorbike_01` `config.cpp:263` to `:378` | `Steering`, `Throttle`, `Brakes`, `Aerodynamics`, `Engine`, `Clutch`, `Gearbox`, `Wheels` with `Front` and `Rear`. |
| `class AnimationSources` | base `config.cpp:111` to `:147`, `Motorbike_01` `config.cpp:379` to `:399` | `HideDestroyed_*`, `AnimHitWheel_1` and `_2`, `damper_1`, `damper_2`, and `SeatDriver` for a flip-up seat. |
| `class DamageSystem` | `Motorbike_01` `config.cpp:400` to `:989` | Zones `Chassis`, `Fender`, `Engine`, `Front`, `Reflector_1_1`, `Back`, `FuelTank`, then `GUIInventoryAttachmentsProps`. |
| `class NoiseCarHorn` | `config.cpp:148` to `:152` | Read by the horn component for infected hearing. |
| `speedGeomActivation`, `speedGeoms[]` | `config.cpp:258` to `:262` | Hides the kickstand collision component `geotohide` at speed. |
| Wheel classes and proxies | `config.cpp:154` to `:219`, `config.cpp:2316` to `:2350` | One class per wheel on `MotorbikeWheel`, a `_Ruined` child each, and a `ProxyVehiclePart` class per wheel model. |

The literal blocks are in `motorbike-config-contract.md`, `motorbike-simulation-config.md` and `motorbike-damage-and-wheel-config.md`.

## Testing a motorbike

1. Offline: run `/dayz-lint` on the mod, then the script validator on the addon folder (`python scripts\tools\dayz-script-validator\scripts\script_validator.py <addon_root>`). It prints JSON with `errors` and `warnings` and exits 0 (pass), 1 (fail) or 2 (warnings only), so gate on no `errors`; compare with the unchanged base tree to isolate what the mod added.
2. In game (`/dayz-launch-test`, server started with `-filePatching`), in this order:
   - Spawn: the bike stands on its kickstand without endless oscillation and does not sink.
   - Render: wheels show their proxies, materials respond, no panel is grey or invisible from a wrong selection name.
   - Get in from the left, then the right: `ActionGetInTransport` plays `GetIn_L` and `GetIn_R`.
   - Start and ride: `ActionStartEngineMotorbike` plays the kickstart sound and the headlight turns with the handlebars (`drivewheel`).
   - Telemetry: rpm, speed and gear respond as the `SimulationModule` says.
   - Fall and recover: a side hit or sharp turn tips the bike, the rider is thrown off (`CrewShouldEject`) and `ActionPickUpMotorbike` stands it up.
3. A spawn with no simulation: look for an `Axles` block where `Wheels` should be (the exact failure is not measured).

Limits of the DayZ-MCP bridge on motorbikes (the bridge's own behaviour, not vanilla): its addon does not know `Motorbike`. Control and telemetry cast to `CarScript`, so `engine_set`, `vehicle_control` and the engine part of `vehicle_telemetry` do not see a bike (it inherits `Transport`, not `CarScript`), `ResolveOwnedCar` answers `not_seated`, and no verb reads player bones. Without the bridge, a diagnostic addon with the scenario in a `modded MissionServer` behind a command-line parameter, log markers in `script_*.log` and a Python driver that waits for them works; seating the player from the server gives a crew member without `HumanCommandVehicle` on the client, which is fine for measuring the pose on the server but not for testing actions or the HUD.

What could not be checked: the vanilla bikes' source `model.cfg` is not shipped, and `/dayz-p3d-audit` reads only MLOD models; the anatomy in `motorbike-vanilla-p3d-anatomy.md` comes from a reader for binarized (ODOL version 56) models that is not in this repo. The gyroscopic solver, stability logic and balance model are native and not reachable from script, so curve units and the effect of `tipoverAngle` are unverified.

## Where vanilla keeps motorbike data

| What | Path on `P:\` |
|---|---|
| Native config parent | `P:\bin\config.cpp:1481` |
| Bikes, wheels, fairings, wheel proxies | `P:\DZ\vehicles\singletrack\config.cpp` (addon `DZ_Vehicles_Singletrack`) |
| Models | `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d`, `P:\DZ\vehicles\singletrack\motorbike_02\motorbike_02.p3d` |
| Native script class | `P:\scripts\3_game\vehicles\motorbike.c` |
| Script classes | `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, `inheritedmotorbikes\motorbike_01.c` and `motorbike_02.c` |
| Lights, horn and particle components | `P:\scripts\4_world\entities\vehicles\components\` |
| Contact damage thresholds (`MOTORBIKES_CONTACT_DMG_*`) | `P:\scripts\3_game\constants.c:898` to `:901` |
| HUD | `P:\scripts\5_mission\gui\vehicles\motorbikehud.c` |
| Rider animation graph and clip table | `P:\DZ\anims\workspaces\player\player_main\vehicles.agf`, `player_main.asi` |
| Sound classes | `P:\DZ\sounds\hpp\config.cpp` (the `Motorbike_0*` classes) |
