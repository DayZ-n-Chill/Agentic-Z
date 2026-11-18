# Engine start, fluids and handling checks

Why an engine will not start or will not stay running, what a test kit must fill and attach, and measured rules for rolling away, steering, mass, grip and drivetrain ratios.

Vanilla facts cite `P:\` (DayZ 1.30). The measured cases come from mod vehicles (a ported quad, imported cars) and from vanilla cars driven in a diag session; they say so where they apply. Engine damage zones themselves are in `damage.md`, fluids in `fluids-and-engine.md`.

## One vital igniter per car

`CheckOperationalRequirements` sets `NO_IGNITER` when a vital spark plug is missing or ruined (`P:\scripts\4_world\entities\vehicles\carscript.c:1776` to `:1780`) and again for a vital glow plug (`:1783` to `:1787`). Every `IsVital*` defaults to `true`: plugs and fuel tank on `Transport` (`P:\scripts\3_game\vehicles\transport.c:404` to `:416`), belt and radiator on `CarScript` (`carscript.c:2201` to `:2209`; on 1.29 all of them were at `carscript.c:2734` to `:2762`). So a bare `CarScript` car needs both plugs.

A petrol car keeps the spark plug and turns the glow plug off: `CivilianSedan` overrides `IsVitalGlowPlug()` to `false` (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`). The sedan also picks its battery by overriding `GetElectricitySourceDevice()` to return the `CarBattery` attachment (`civiliansedan.c:64` to `:69`), so it never needs an `IsVitalTruckBattery()` override; that check stays on `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:2818`). A diesel does the opposite: `Offroad_02` overrides `IsVitalSparkPlug()` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`). Declare only the vital plug in `attachments[]` and attach that one in `OnDebugSpawn`.

An engine that will not start with a spark plug fitted usually means the glow plug was never turned off. The fix is the vanilla petrol override, not removing the check: the car still needs its spark plug. Full start conditions: `vehicle-parts-and-start.md`, section "Engine won't start".

## An engine that starts and stalls at once

With fuel and every vital part fitted, an engine that runs for one tick and drops to 0 rpm is missing its `Engine` damage zone, and usually `FuelTank` too. `EOnPostSimulate` stops a running engine every tick while `m_EngineHealth <= 0` (`carscript.c:850`), and `m_EngineHealth` is read from the `Engine` zone's health level with `GetHealthLevelValue(GetHealthLevel("Engine"), "Engine")` (`:2134`, `:2135`); with no `class Engine` that reads as ruined. A ruined `FuelTank` zone also ruins `Engine` when `IsVitalFuelTank` is true (`:861`).

Every vanilla car has both zones. An imported car that declares only body zones (chassis, front, back, roof) looks configured, but its engine never stays on. Add `class Engine` and `class FuelTank` to `DamageZones`, with `componentNames[]` pointing at Fire Geometry selections `dmgzone_engine` and `dmgzone_fueltank`, as vanilla does. A zone with empty `componentNames[]` and `memoryPoints[]` is the minimal variant; check that it registers. The igniter rule decides whether an engine starts; this one decides whether a started engine stays on.

## Missing zone memory points do not cause jerks

Missing `memoryPoints[]` in damage zones, or missing `dmgzone_*` points in the Memory LOD, do not explain collision jerks or stutter while driving. Script never reads `memoryPoints[]`:

- `Transport.OnContact` caches the first contact of the tick with the momentum change as its impulse (`P:\scripts\3_game\vehicles\transport.c:315`), and `CheckContactCache` applies `ProcessDirectDamage(..., zoneName, "EnviroDmg", "0 0 0", dmg)` from the cached `m_Impulse` (`carscript.c:1291`, `:1364`).
- `DamageSystem.GetDamageZoneMap` reads only `componentNames`, with `ConfigGetTextArray(... componentNames)` (`P:\scripts\3_game\damagesystem.c:63` to `:66`). Grep `memoryPoints` in the scripts and you find nothing; it appears only in vehicle configs.
- The vanilla `OffroadHatchback` `Chassis` zone has `componentNames[]` and no `memoryPoints[]` (`P:\DZ\vehicles\wheeled\config.cpp:1579` to `:1593`).
- `m_VFXComponent.ConvertMemPointToPosition("dmgZone_*")` in the constructor (`carscript.c:369` to `:375`) feeds `GetEnginePointPosWS`, `GetFrontPointPosWS` and the rest (`:314` to `:340`), which nothing calls.

The Geometry LOD is the contact mesh; a working car can carry `dmgzone_*` only in Fire Geometry, plus Memory for config parity. Do not spend a game session adding Memory points as a jerk fix. What the native `OnContact` `zoneName` and `GetDamageZonePos` (`P:\scripts\3_game\entities\object.c:1159`) do with zone positions is not visible in script; even if it used memory points, that would change which zone loses health, not the impulse.

## A test kit fills every fluid and fits the radiator

A kit that only calls `Fill(CarFluid.FUEL,...)` leaves oil, coolant and brake fluid empty: the oil light goes red and the engine breaks while driving, which looks like a drivetrain bug. A drive-ready kit fills `FUEL`, `OIL`, `COOLANT` and `BRAKE` and calls `CreateAttachment("CarRadiator")`, because coolant needs the radiator.

Vanilla helpers do not do all of it:

- `FillUpCarFluids()` fills `FUEL`, `COOLANT` and `OIL` with 200.0 each and nothing else (`carscript.c:2561` to `:2566`). It has one definition and no override, so no vanilla car fills brake fluid this way.
- `SpawnUniversalParts()` creates the radiators, when `IsVitalRadiator()`, with `CreateInInventory` (`:2500` to `:2515`), which may put them in cargo instead of the slot.

So a mod car whose `OnDebugSpawn` calls `FillUpCarFluids()` and stops, the obvious vanilla-faithful code, spawns with an empty brake reservoir. Add `Fill(CarFluid.BRAKE, GetFluidCapacity(CarFluid.BRAKE))`, taking the capacity from config rather than a copied 200.0: `brakeFluidCapacity` is `1` on `CarScript` (`P:\DZ\vehicles\wheeled\config.cpp:244`) unless the car redeclares it. A hand-written kit in the mission `init.c` must also fill brake fluid and attach the radiator. `CarFluid` (`FUEL`, `OIL`, `BRAKE`, `COOLANT`) is an alias of `ETransportFluid` (`P:\scripts\3_game\vehicles\car.c:18`); `Fill` adds rather than sets (`car.c:371`, `:372`); `GetFluidCapacity` is at `car.c:355`.

## Spawn fuel belongs in `EEOnCECreate`

To change the fuel a vehicle spawns with, override `EEOnCECreate`, not `EEInit`. Vanilla fills a random 0 to 35 percent (`Math.RandomFloat(0.0, maxVolume * 0.35)`, `carscript.c:2412` to `:2418`). `EEOnCECreate` runs for an entity created new by the Central Economy or debug (`P:\scripts\3_game\entities\entityai.c:1414`), while a load from storage goes through `AfterStoreLoad` (`:1419`), so a fill there does not hand out free fuel on every restart as `EEInit` would. Top up rather than pour: `Fill(CarFluid.FUEL, GetFluidCapacity(CarFluid.FUEL) * (1.0 - GetFluidFraction(CarFluid.FUEL)))`. `OnDebugSpawn` is a separate path and fills on its own.

A script spawn does not reach `EEOnCECreate`. With a vanilla `Hatchback_02` as the control (it must land between 0 and 35 percent if the path runs), neither `ECE_PLACE_ON_SURFACE` (also what the debug spawner's vehicle path passes without a player) nor `ECE_PLACE_ON_SURFACE | ECE_INITAI | ECE_EQUIP_ATTACHMENTS` (the AI spawn path) fired it: both controls and the mod vehicle read fuel 0 (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:454`, `:478` to `:505`). Only a real Central Economy spawn, a `types.xml` entry plus an event, exercises the override. Without a vanilla control in the same run, that zero reads as a broken override.

## A vehicle that rolls away on its own

A port that "drifts on its own, even on flat ground" has a `tyreRollResistance` defect. It rolls when `tan(slope) > tyreRollResistance`. A ported quad's healthy wheels carried 0.0015 against 0.008 to 0.018 on every vanilla wheel (`P:\DZ\vehicles\wheeled\config.cpp:876`, `:4782`, `:9000`, `:13426`, `:18108`, `:18144`, `:20557`), and its ruined wheels 0.03 against 0.2 to 0.85. That moved the threshold from 0.86 to 0.086 degrees; no DayZ terrain is that flat, so it crept everywhere and the report read like a physics or sync bug.

- Mass does not matter here: gravity and rolling resistance both scale with weight and cancel.
- Vanilla cars stand still because they are braked, not because of friction. Every vanilla `Brake` class sets `driverless=0.1` (`config.cpp:460`), `SetBrakesActivateWithoutDriver` is native on `Car` (`P:\scripts\3_game\vehicles\car.c:212`), and the push action turns it off (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:95`). A vanilla car with a driver seated and the engine off also rolls downhill.
- Ground is never flat: spots that look level measured 0.72 to 4.8 degrees from the surface normal.

Diff the whole wheel class against the nearest vanilla wheel on any port, not just `radius`. To tell rolling from sliding, check `omega == v / r` (0.051 measured against 0.048 predicted, 6 percent); a mismatch means slip or an animation detached from the wheel.

## Steering angle and its ramp

`increaseSpeed[]` and `decreaseSpeed[]` in `class Steering` are pairs of km/h and degrees per second: how fast steering moves toward the requested lock. Time to full lock is angle divided by rate, so the ramp only fits the angle it was written for. `OffroadHatchback` steers with `maxSteeringAngle=30` and `increaseSpeed[]={0,40,30,20,100,5}` (`config.cpp:1375`, `:1376`).

A ported quad carried that exact ramp with a lock of 50, raised to 60. At 20 degrees per second at 30 km/h, time to lock went from 2.5 s to 3.0 s, against 1.5 s on the hatchback. Nobody holds a key that long in a corner, so the ceiling rose and usable steering fell; the player reported that it still did not turn as much as expected and that it no longer seemed to be the wheels' angle. When you copy a vanilla `Steering` block, rescale the ramp with the angle, and write the resulting time to lock in the commit.

`centeringSpeed` above `increaseSpeed` at speed is not a defect: in 8 of the 10 vanilla `Steering` blocks centring is faster at 60 km/h, up to 6.5 times (`config.cpp:14085` to `:14087`), and equal in the other two (`:741` to `:743`, `:18513` to `:18515`).

## Mass lives in the Geometry LOD

Check mass before blaming steering, and look in the model, not `config.cpp`. Vehicle mass is a per-point table in the Geometry LOD (resolution `1e13`); py3d exposes `Point.mass` on each point and `lod.mass` is only their sum (**model knowledge**). Read the table before describing the distribution. A ported quad first read as "1,500 kg on one point" had mass on all 214 points (1.2 to 46.2 kg), centred sideways (X -0.0001) and low (23 percent of hull height). Only the total was wrong: 1,500 kg against 250 to 320 kg for a real ATV, four to five times the yaw inertia the tyres must turn.

To change mass, scale every `Point.mass` by one factor and scale `stiffness`, `damping` and `compression` by the same factor; never `travelMaxUp` or `travelMaxDown`. One factor keeps the centre of mass and the front to rear split, so only inertia changes. Ride height is `u = -travelMaxDown + F/k`, so holding `k/F` holds the stance. Damping ratio is `c / (2 * sqrt(k * m))`, so halving k and m halves `sqrt(k * m)` and c follows. Travel is geometry and stays. Halving the quad from 1,500 to 750 kg left front `u` at -0.00005 m and rear at -0.00470 against -0.00469, and in game it settled at the same height to the last bit at both masses (`y = 139.97918701171875`).

Check the mass inside the packed PBO: extract the `.p3d` and sum `Point.mass`. Keep `.p3d` backups out of the addon folder, because AddonBuilder packs them.

## Grip against wheel force

A first-order friction estimate is not a simulation, but it ranks layouts, which is the decision. First gear asks `clutch cap * gear * final drive / tyre radius` at the wheels; the driven axle holds `mass * 9.81 * its weight share * tyreGrip`. On a 750 kg quad with a 180 Nm clutch cap, 4.3 times 3.667 over a 0.35 m radius, 65.2 percent of weight on the front:

| Layout | Asked | Held | Ratio | What the driver said |
|---|---|---|---|---|
| RWD | 8,109 N | 2,535 N | 3.2 | "they slide a lot" |
| AWD, open differentials | 8,109 N | 7,284 N, less in a corner as the inner wheel spins first | | "they slide a lot" |
| AWD, locked rear | 8,109 N | 7,284 N | 1.11 | "least bad, but it cannot go straight at full throttle without skidding" |
| FWD | 8,109 N | 4,749 N | 1.7 | stable, but "it turns less" |

The arithmetic predicted the driver's order. Lowering `tyreGrip` moves every row the wrong way: at 0.85 the locked-rear AWD goes to 1.30 and the FWD to 2.0. On `DRIVE_FWD` the wheels that spin are the wheels that steer, so excess torque reaches the driver as "it will not turn", never as wheelspin. Halving mass halves the grip budget and leaves the torque, which alone turns a car that steered into one that pushes. Check `Clutch.maxTorqueTransfer` against the `torqueCurve` peak before adding torque: the quad had 140 against a 320 peak, below every vanilla car (165 at `config.cpp:14125` to 720 at `:779`).

Vanilla `tyreGrip` on healthy wheels: 0.80 (`config.cpp:877`), 0.82 (`:13427`), 0.85 (`:4783`), 0.89 (`:9001`), 0.95 (`:18109`, `:20558`), 1.0 (`:18145`); ruined wheels sit at 0.2 to 0.5. A value of 0.99 is inside the vanilla range.

Diagnose a sliding car by axis. Sliding under full throttle (power oversteer on RWD) wants more grip and less throttle or torque. Sliding in a turn, as body roll unloads the inside tyre, wants grip, a lower centre of mass, downforce and roll stiffness. A low centre of mass helps the cornering slide but not the throttle slide; on RWD it even moves less weight rearward under power. On an imported coupe the throttle slide dropped with grip 0.95 to 0.98 and throttle 0.8 to 0.72, while the cornering slide needed the centre of mass and downforce.

To add grip without touching the wheel binding, subclass the vanilla wheel: `class MyMod_Wheel: CivSedanWheel { scope=2; tyreGrip=0.98; };`. It inherits the vanilla `inventorySlot[]` (`config.cpp:4768`, `CivSedanWheel_1_1` to `_2_2` and the spare), so it fits the same slots and proxy; create it from `OnDebugSpawn` or the kit. Grip is separate from the wheel's look; a custom rim is a separate job.

## Taking another mod's drivetrain

Match `(gear * central * final) / wheel radius`, never the ratios as written. Wheel force per engine Nm is total reduction over wheel radius, and road speed per gear is `rpm * radius / reduction`, so a different wheel radius shifts every gear by the ratio of radii. Compare radii first; the central differential ratio is the lever that compensates. A coupe on `CivSedanWheel` (radius 0.34) taking a drivetrain built for 0.48 m wheels with a central ratio of 1.4 keeps its central at 1.0: 0.34 / 0.48 is about 1 / 1.4, so the per-gear speeds and force per Nm come out under 1 percent off. Copying 1.4 would make every gear 29 percent short, and a central of 1.5 on ratios written for 1.0 made gears about 50 percent short with sixth unreachable.

The same force on half the mass gives about twice the acceleration, so scale expectations by mass before judging power. Engine `frictionTorque` is tuned to the source car's mass: engine braking scales as `frictionTorque * reduction / (radius * mass)`, so when radius and reduction cancel the equivalent is `frictionTorque * yourMass / sourceMass`. Work out that fallback before testing in game.

## Measured launch of the vanilla sedan

On airfield concrete, a standing start at full throttle under automated driving, changing one config field per run on `CivilianSedan` and `CivSedanWheel`, traced at 19 to 20 Hz. The runs are few and the count is given per result; read them as measurements, not laws. The automated driver skipped gears above about 33 km/h, so launch figures stop there.

- Torque drives the launch almost in proportion: acceleration over the first 3 s scales as torque to the power 0.93 to 0.95 (torque times 0.7 gave 0.72, one run; times 1.3 with clutch 520 gave 1.28, three runs; baseline five runs), and the 0 to 30 km/h time as torque to the power -1.17. First gear does not slip (rear slip 90th percentile about 0.001).
- `tyreGrip` from 0.70 to 1.00 changed neither the straight launch (2 percent or less) nor braking (5.7 to 6.0 m/s²). At 0.30 the car braked 22 to 30 percent less and launched 10 percent faster with almost no slip (one run, not explained). Here `tyreGrip` does not act as a simple friction coefficient along the car.
- The first upshift came at 9.20 m/s against 9.33 m/s predicted by `0.8 * redline * 2πr / (60 * i_1 * i_final)` (five runs), so the formula holds for radius and ratios.
- In a steady arc at steering 0.3 (circles of about 20 m), drift angle fell from 8.3 degrees at 14 km/h to 3.4 at 32 km/h, lateral acceleration reached 7.2 m/s² (about 0.73 g), with no slide (one run).

To change the launch, change torque. Above about 0.7, `tyreGrip` does not change the sedan's straight launch or braking; its effect in cornering and drift is not measured.
