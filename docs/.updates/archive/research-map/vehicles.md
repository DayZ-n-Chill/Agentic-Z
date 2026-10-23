# Research map: vehicles specialist

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Class hierarchy | `Transport` then `Car` (native physics) then `CarScript` (script). Boats, motorbikes and helicopters branch from `Transport`. | `P:\scripts\3_game\vehicles\transport.c:66`; `P:\scripts\3_game\vehicles\car.c:87`; `P:\scripts\4_world\entities\vehicles\carscript.c:94` |
| 2 | Native car API | Steering, throttle, brake, clutch, gears, RPM, engine start/stop, wheel queries. | `P:\scripts\3_game\vehicles\car.c:102`-`355` |
| 3 | Fluids | `CarFluid` enum, `GetFluidFraction`, `Fill`, `Leak`, `LeakAll`, `fuelCapacity` in config. | `P:\scripts\3_game\vehicles\car.c:18`, `:355`; `P:\scripts\4_world\entities\vehicles\carscript.c:425`, `:579`, `:897`; `P:\DZ\vehicles\wheeled\config.cpp:5211` |
| 4 | Engine start conditions | `OnBeforeEngineStart` checks battery, spark/glow plug, fuel and plays failure sounds. | `P:\scripts\4_world\entities\vehicles\carscript.c:1713`, `:1776`, `:1783` |
| 5 | Engine start/stop events | `OnEngineStart`, `OnEngineStop`, delayed `SetEngineStarted`. | `P:\scripts\4_world\entities\vehicles\carscript.c:1805`, `:1822`, `:1592` |
| 6 | Vital parts | `IsVitalCarBattery`, `IsVitalTruckBattery`, `IsVitalSparkPlug`, `IsVitalGlowPlug`, `IsVitalRadiator`; per-class overrides. | `P:\scripts\4_world\entities\vehicles\carscript.c:2812`, `:2818`, `:853`, `:693` |
| 7 | Damage simulation tick | `EOnPostSimulate` handles RPM overrev damage, coolant, fuel/oil/brake leaks. | `P:\scripts\4_world\entities\vehicles\carscript.c:807`-`920` |
| 8 | Collision damage | `OnContact` feeds contact data; `DamageCrew` hurts occupants. | `P:\scripts\4_world\entities\vehicles\carscript.c:1278`, `:1374`; `P:\scripts\4_world\entities\vehicles\carscript.c:53` (`CarContactData`) |
| 9 | Drowning | Engine drowns when underwater beyond threshold. | `P:\scripts\4_world\entities\vehicles\carscript.c:1210`, `:1236` |
| 10 | Crew and seats | `class Crew` in config; `CrewCanGetThrough`, `CanReachSeatFromDoors`, door slot from seat. | `P:\DZ\vehicles\wheeled\config.cpp:5213`; `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:226`; `P:\scripts\4_world\entities\vehicles\carscript.c:2162`, `:2167`, `:2177` |
| 11 | Seat animation type and anim instance | `GetAnimInstance`, `GetSeatAnimationType` map to vehicle anim sets. | `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:109`, `:119`; `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c` |
| 12 | Doors and animation sources | `GetCarDoorsState`, `GetAnimSourceFromSelection`, `AnimationSources` config. | `P:\scripts\4_world\entities\vehicles\carscript.c:2243`; `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:349`; `P:\DZ\vehicles\wheeled\config.cpp:5363` |
| 13 | Door and wheel item classes | `CarDoor`, `CarWheel` script classes; config bases `CarWheel`, `CarDoor`. | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:194`, `:568`; `P:\DZ\vehicles\wheeled\config.cpp:14`, `:75` |
| 14 | Simulation module | Steering, Throttle, Brake, Aerodynamics, Engine (torque curve), Clutch, Gearbox, Axles with Suspension, Differential, Wheels. | `P:\DZ\vehicles\wheeled\config.cpp:5236`-`5356`; templates `RearDrive` `:437`, `FrontDrive` `:533`, `AllDrive` `:629`, `TruckDrive` `:734` |
| 15 | Attachments and slots | `attachments[]` list and `GUIInventoryAttachmentsProps` UI grouping. | `P:\DZ\vehicles\wheeled\config.cpp:5119`, `:6081` |
| 16 | Damage zones | `DamageSystem` with `GlobalHealth` and zones (Chassis, Engine, FuelTank, Front, Back, Reflectors, Windows). | `P:\DZ\vehicles\wheeled\config.cpp:5396`-`6056` |
| 17 | Cargo | `class Cargo` sizes in car config. | `P:\DZ\vehicles\wheeled\config.cpp:5357` |
| 18 | Hidden selections and textures | `hiddenSelections[]` for paint variants such as `CivilianSedan_Wine`. | `P:\DZ\vehicles\wheeled\config.cpp:5138`, `:6128` |
| 19 | Obstacle generator | Navmesh obstacle shape for AI around vehicles. | `P:\DZ\vehicles\wheeled\config.cpp:6057` |
| 20 | User actions on cars | `SetActions` registers actions; get in/out, refuel, push. | `P:\scripts\4_world\entities\vehicles\carscript.c:2313`; `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:1`; `...\actiongetouttransport.c:23`; `...\continuous\vehicles\actionfillfuel.c:11`; `...\continuous\actionpushcar.c:56` |
| 21 | Fluid action component names | `GetActionCompNameFuel`/`Coolant` decide where refuel actions target. | `P:\scripts\4_world\entities\vehicles\carscript.c:2260` |
| 22 | Jump-out handling | Server handling of leaving a moving vehicle. | `P:\scripts\4_world\entities\vehicles\carscript.c:951` |
| 23 | Attachment rules | `EEItemAttached`, `CanReleaseAttachment` (locked doors and running engine). | `P:\scripts\4_world\entities\vehicles\carscript.c:482`, `:638` |
| 24 | Lights | `CarLightBase`, `CreateFrontLight`, `CreateRearLight`, lights component. | `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\carlightbase.c:2`; `P:\scripts\4_world\entities\vehicles\carscript.c:2938`, `:2945`; `P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c` |
| 25 | Horn | Horn component. | `P:\scripts\4_world\entities\vehicles\components\vehiclehorncomponent.c:10` |
| 26 | Engine and crash sounds | `OnSound` with `CarSoundCtrl`, `HandleEngineSound`, crash sound sync bools. | `P:\scripts\4_world\entities\vehicles\carscript.c:1433`, `:1560`, `:280`; `P:\scripts\3_game\vehicles\car.c:3` |
| 27 | Exhaust and damage smoke | `VehicleVFXComponent`, `EffVehicleSmoke`, `EffExhaustSmoke`. | `P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:96`; `P:\scripts\3_game\effects\effectparticle\vehiclesmoke.c:1`; `...\vehiclesmoke\exhaustsmoke.c:1` |
| 28 | Camera | `Get3rdPersonCameraType`, transport camera distance/offset. | `P:\scripts\4_world\entities\vehicles\carscript.c:2232` |
| 29 | Battery item | `VehicleBattery` class, energy manager link. | `P:\scripts\4_world\entities\itembase\vehiclebattery.c:1` |
| 30 | Spark plug | `SparkPlug` item class, `SLOT_ID`. | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:952` |
| 31 | Boats | `Boat` native class, `BoatScript` overrides seat, sound, anim instance. | `P:\scripts\3_game\vehicles\boat.c:28`; `P:\scripts\4_world\entities\vehicles\boatscript.c:195`, `:497`; `P:\scripts\4_world\entities\vehicles\inheritedboats\boat_01.c:11` |
| 32 | Motorbikes | `Motorbike` native class and script overrides. | `P:\scripts\3_game\vehicles\motorbike.c:30`; `P:\scripts\4_world\entities\vehicles\motorbikescript.c:263`, `:449` |
| 33 | Helicopters | `HelicopterAuto` and `HelicopterScript` (not used in vanilla gameplay). | `P:\scripts\3_game\vehicles\helicopter.c:14`; `P:\scripts\4_world\entities\vehicles\helicopterscript.c:4` |
| 34 | Persistence | Car state saved natively; see persistence map. Spawned cars need wheels and parts attached by script or CE `cfgspawnabletypes.xml` (**knowledge**). | `P:\scripts\4_world\entities\vehicles\carscript.c:94` |
| 35 | Model requirements | Wheel memory points, damper axis points, `geometry`/`geometryPhys` LODs, proxy seats. **knowledge**; inspect vanilla p3d with `/dayz-p3d-audit`. | `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` |
