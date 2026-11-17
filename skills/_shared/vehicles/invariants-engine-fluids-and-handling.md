# Engine start, fluids, test kits and handling: invariants

Why an engine will not start or will not stay on, what a test kit must fill and attach, and measured rules for rolling, steering, mass, grip and drivetrain ratios.

> Status: the measurements below were taken in game or offline on mod vehicles, named in each entry; they describe those mods, not vanilla, unless a vanilla citation backs them. Every citation of a vanilla file was opened on `P:\` (a 1.30 build), whether it is written with its full `P:\` path or with the file name alone. A citation marked `1.29` gives the line in a 1.29 build, which is not on `P:\` and is not checked. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- `CarScript.EOnPostSimulate` stops a running engine when `m_EngineHealth <= 0` (`P:\scripts\4_world\entities\vehicles\carscript.c:850`), and `m_EngineHealth` is read from the `Engine` damage zone (`P:\scripts\4_world\entities\vehicles\carscript.c:2135`). A ruined `FuelTank` zone ruins the `Engine` zone when `IsVitalFuelTank` is true (`P:\scripts\4_world\entities\vehicles\carscript.c:861`).
- `CheckOperationalRequirements` sets `NO_IGNITER` for a missing vital spark plug (`P:\scripts\4_world\entities\vehicles\carscript.c:1780`) and for a missing vital glow plug (`P:\scripts\4_world\entities\vehicles\carscript.c:1787`). `CivilianSedan` turns `IsVitalGlowPlug` off (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`) and `Offroad_02` turns `IsVitalSparkPlug` off (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`).
- `FillUpCarFluids` fills `CarFluid.FUEL`, `CarFluid.COOLANT` and `CarFluid.OIL` and nothing else (`P:\scripts\4_world\entities\vehicles\carscript.c:2561-2566`). `brakeFluidCapacity` is `1` on `CarScript` (`P:\DZ\vehicles\wheeled\config.cpp:244`).
- `SpawnUniversalParts` puts bulbs, battery and radiators in with `CreateInInventory` (`P:\scripts\4_world\entities\vehicles\carscript.c:2500`).
- `CarScript.EEOnCECreate` fills `Math.RandomFloat(0.0, maxVolume * 0.35)` of fuel (`P:\scripts\4_world\entities\vehicles\carscript.c:2412-2418`); the base `EEOnCECreate` is documented as called for an entity created as new by CE or debug (`P:\scripts\3_game\entities\entityai.c:1414`) and `AfterStoreLoad` for one loaded from storage (`P:\scripts\3_game\entities\entityai.c:1419`).
- Healthy vanilla wheels carry `tyreRollResistance` from 0.008 to 0.018 (`P:\DZ\vehicles\wheeled\config.cpp:876`, `P:\DZ\vehicles\wheeled\config.cpp:4782`, `P:\DZ\vehicles\wheeled\config.cpp:18144`) and `tyreGrip` from 0.80 to 1.0 (`P:\DZ\vehicles\wheeled\config.cpp:877`, `P:\DZ\vehicles\wheeled\config.cpp:18145`).
- Every vanilla `Brake` class sets `driverless=0.1` (`P:\DZ\vehicles\wheeled\config.cpp:460`); `SetBrakesActivateWithoutDriver` is native on `Car` (`P:\scripts\3_game\vehicles\car.c:212`) and the push action switches it off (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:95`).
- `OffroadHatchback` steers with `maxSteeringAngle=30` and `increaseSpeed[]={0,40,30,20,100,5}` (`P:\DZ\vehicles\wheeled\config.cpp:1375-1376`).
- Vanilla `maxTorqueTransfer` runs from 165 (`P:\DZ\vehicles\wheeled\config.cpp:14125`) to 720 (`P:\DZ\vehicles\wheeled\config.cpp:779`).
- Crash damage uses the cached `m_Impulse` of the first contact (`P:\scripts\4_world\entities\vehicles\carscript.c:1291`), and the damage system reads a zone's `componentNames` from config (`P:\scripts\3_game\damagesystem.c:63`).

## Invariant 8: one vital igniter per car

**One vital igniter per car — vanilla defaults BOTH SparkPlug AND GlowPlug to vital, so a bare
`CarScript` car silently demands BOTH.** `CheckOperationalRequirements` sets `NO_IGNITER` if either
vital plug is missing (`carscript.c:1776` SparkPlug / `:1783` GlowPlug); every `IsVital*` defaults true
(`transport.c:404-416` plugs and fuel tank, `carscript.c:2201-2209` belt and radiator; 1.29 `carscript.c:2734-2762`). A PETROL car (CivilianSedan) keeps SparkPlug vital and
overrides `IsVitalGlowPlug()→false` (`civiliansedan.c:370`; on 1.29 also `IsVitalTruckBattery()→false`, 1.29 `:358`, which 1.30 replaced with `GetElectricitySourceDevice()`, `civiliansedan.c:64-69`);
a DIESEL car (Offroad_02) mirrors it — `IsVitalSparkPlug()→false` (`offroad_02.c:415`). `attachments[]`
must declare ONLY the vital plug and `OnDebugSpawn` must attach THAT part. "Engine won't start" with a
SparkPlug already attached = the un-overridden GlowPlug, **NOT** a removed requirement — `IsVitalGlowPlug→false`
IS the vanilla petrol pattern (the car still requires its SparkPlug). Seen on SUB_BRZ (a petrol car defaulted
to needing a GlowPlug it had no slot for; framing the fix as "remove the check" gets it backwards). → `vehicle-config-and-modelcfg.md` §15 (engine will not start).

## Invariant 9: the engine starts then stalls when the Engine and FuelTank damage zones are missing

**Engine STARTS then immediately STALLS (eng=1 for one tick → eng=0 rpm=0) with fuel + ALL vital parts
attached → the car is missing its `Engine` (and `FuelTank`) DamageZone.** `CarScript` stops a running
engine EVERY tick when `m_EngineHealth <= 0` (`carscript.c:850`), and `m_EngineHealth =
GetHealthLevelValue(GetHealthLevel("Engine"), "Engine")` (`carscript.c:2134-2135`) — a `DamageSystem.
DamageZones` with no `class Engine` resolves "Engine" health to RUINED → perpetual `EngineStop()`. A
missing `class FuelTank` compounds it (`carscript.c:861` ruins the Engine zone when FuelTank reads
RUINED). EVERY vanilla car ships BOTH zones; an imported/regen car declaring only body zones
(chassis/front/back/roof) LOOKS configured but the engine never sustains. Fix: add `class Engine` +
`class FuelTank` to `DamageZones` — the proven shape (vanilla/SUB_BRZ) points `componentNames[]` at a
FireGeo `dmgzone_engine`/`dmgzone_fueltank` selection; a config-only health zone (empty `componentNames[]`/
`memoryPoints[]`) is the minimal variant (verify it registers). DISTINCT from #8: #8 gates whether the
engine STARTS (vital igniter parts); #9 gates whether a STARTED engine STAYS ON (engine-health zone).
Seen on MercedesAMGLF (stalled with SparkPlug+CarBattery+CarRadiator+fuel+coolant ALL present; SUB_BRZ ran
only because it carried both zones). Verified vs `carscript.c` source + SUB_BRZ in-game parity.

## Invariant 15c: a vehicle that drifts on its own has a tyreRollResistance defect

**A ported vehicle that "drifts on its own, even on flat ground" is a `tyreRollResistance`
defect, and the roll-away threshold is `tan(slope) > tyreRollResistance` (measured
2026-09-09, Arma2Quad; closed by telemetry).** The quad's healthy wheels carried
**0.0015** against **0.008-0.018 on every vanilla wheel**
(`P:\DZ\vehicles\wheeled\config.cpp:876`, `:4782`, `:9000`, `:13426`, `:18108`, `:18144`, `:20557`), and its ruined ones
0.03 against 0.2-0.85. That moves the threshold from 0.86 deg to **0.086 deg**: no DayZ
terrain is that flat, so the vehicle creeps everywhere and the report reads as a physics
or sync bug. Three things this invariant exists to stop, all of which cost cycles here:
**(a) mass is irrelevant** - gravity and rolling resistance both scale with weight and
cancel, so "it is too heavy / too light" explains nothing; **(b) vanilla vehicles do not
hold still through friction, they hold still because they are BRAKED** - every vanilla
config carries `Brake.driverless = 0.1` and `Car.c:212` declares
`SetBrakesActivateWithoutDriver`, which `actionpushcar.c:95` disables to push a car, so a
vanilla car with a driver seated and the engine off ALSO rolls downhill; **(c) the
ground is never flat** - `surface_query` returns the normal, and spots that look level
measured 0.72-4.8 deg. Day-1 check on any port: diff the whole wheel class against the
nearest vanilla wheel, not just `radius`. Discriminating rolling from sliding is one
line of telemetry: rolling satisfies `omega == v / r` (here 0.051 measured against 0.048
predicted, 6 %); a mismatch means slip or a decoupled animation.

## Invariant 15f: raising maxSteeringAngle without scaling increaseSpeed turns less, not more

**Raising `maxSteeringAngle` without scaling `increaseSpeed[]` makes the vehicle turn LESS
in practice, not more (measured 2026-09-10, Arma2Quad).**
`increaseSpeed[]` and `decreaseSpeed[]` inside `class Steering` are {km/h, deg/s} pairs: the
RATE at which the steering ramps toward the requested lock. Time to full lock is
`angle / rate`, so the ramp only makes sense relative to the angle it was written for.
Arma2Quad carried `{0,40,30,20,100,5}` - byte-identical to vanilla `OffroadHatchback`
(`P:\DZ\vehicles\wheeled\config.cpp:1376`), whose `maxSteeringAngle` is **30**. Taking ours from
50 to 60 while leaving 20 deg/s at 30 km/h moved time-to-lock from 2.5 s to **3.0 s**, against
the donor car's 1.5 s. In a real corner nobody holds the key that long, so the ceiling went up
and the usable steering went DOWN. The user's report was exactly right and worth quoting as
the symptom: *"it still does not turn as much as I would expect, and I no longer think it is the turning
radius of the wheels"*: the steering still felt short, and it was no longer the wheels'
angle. Rule: whenever you copy a vanilla `Steering` block, the ramp belongs to the DONOR's
lock angle; rescale it with the angle, and state the resulting time-to-lock in the commit so
the next reader can check it in one division.
**Before blaming the steering at all, check the MASS - and it is not in config.cpp.** In DayZ
the vehicle mass lives in the **Geometry LOD of the p3d** (`resolution 1e13`) as a PER-POINT
table: py3d exposes it as `Point.mass` on every point of that LOD, and `lod.mass` is only
their SUM. Read the table before saying anything about how the mass is distributed. A first
reading of Arma2Quad as "1500 kg on one point" was wrong; the
per-point read refuted it in one line - all 214 points carried mass (1.2-46.2 kg), with the
centre of mass centred laterally (X -0.0001) and low (23 % of the hull height). The
distribution was sound; only the TOTAL was wrong: 1500 kg against 250-320 kg for a real ATV,
four to five times the yaw inertia the tyres must overcome. Changing it is coordinated work,
not a tweak - see 15g. What does not change either way is the roll-away threshold: mass
cancels there (15c).

## Invariant 15g: changing a vehicle's mass

**Changing a vehicle's mass: scale every `Point.mass` by one factor, and scale `stiffness`,
`damping` and `compression` by the SAME factor - never `travelMaxUp/Down` (measured
2026-09-10, Arma2Quad 1500 -> 750 kg).** A uniform factor leaves the centre of mass and the
front/rear split exactly where they were, so the only thing that changes is inertia. Ride
height comes out of `u = -travelMaxDown + F/k`: holding `k/F` holds the stance, so
`stiffness` scales with the mass. `damping` and `compression` scale the same way because the
damping ratio is `c / (2*sqrt(k*m))`, and halving both k and m halves `sqrt(k*m)`. Travel is
geometry and stays. Result: front `u` -0.00005 m before and after, rear -0.00470 vs -0.00469,
and in game a freshly prepared quad settled at `y = 139.97918701171875` at BOTH masses, bit
for bit. Gate the mass INSIDE the PBO, not in the source: pull the packed `.p3d` out and sum
`Point.mass` with py3d. Keep `.p3d` backups out of the addon folder - AddonBuilder packs them.
Traps surfaced by halving the mass. (a) The user reported *"it turns less than before, nothing more"*:
no slide and no bounce, and the lock angle had not changed. Suspected
cause, NOT confirmed: the same corner is now taken faster, where `increaseSpeed[]` is lower.
Flattening the ramp above the speed the driver had already approved (35 -> 60 deg/s at
60 km/h) drew "still improvable", not a clean yes. (b) Do NOT read `centeringSpeed >
increaseSpeed` at speed as the defect: in `DZ/vehicles/wheeled/config.cpp` centering is
higher at 60 km/h in 8 of the 10 `Steering` blocks (up to 6.5x, `:14085-14087`) and equal in
the other 2 (`:741-743`, `:18513-18515`) - it is the vanilla norm. (c) Check
`Clutch.maxTorqueTransfer` against the `torqueCurve` peak before adding torque: Arma2Quad had
140 against a 320 peak, below every vanilla car (165 at `P:\DZ\vehicles\wheeled\config.cpp:14125` to 720 at `:779`). On
`DRIVE_FWD`, a first-order Coulomb estimate (not measured in game) says first gear was already
asking 6307 N of the 4749 N of front grip at 750 kg, so torque past that becomes wheelspin on
the steering axle, which works against turning.

## Invariant 15h: spawn fuel belongs in EEOnCECreate, not EEInit

**To change the fuel a vehicle spawns with, override `EEOnCECreate`, not `EEInit`
(source-verified; a script spawn does NOT reach it - measured, see below).** Vanilla
`CarScript.EEOnCECreate` fills a random 0-35 % of `GetFluidCapacity(CarFluid.FUEL)`
(`scripts/4_world/entities/vehicles/carscript.c:2412-2419`). It runs when the entity is
created as new by CE/debug (`scripts/3_game/entities/entityai.c:1413-1416`), while a load
from storage goes through `AfterStoreLoad` (`:1418-1421`) - so a fill there cannot turn into
free fuel on every restart, which the same code in `EEInit` would. `Fill` ADDS
(`scripts/3_game/vehicles/car.c:371-372`), so top up rather than pour the whole capacity into
a tank that may not be empty:
`Fill(CarFluid.FUEL, GetFluidCapacity(CarFluid.FUEL) * (1.0 - GetFluidFraction(CarFluid.FUEL)))`.
`OnDebugSpawn` is a separate path and fills on its own. **Measured 2026-09-11 with a vanilla
`Hatchback_02` as the control**, which must land in 0-35 % if the path runs: neither a plain
script spawn (`ECE_PLACE_ON_SURFACE`, which is also what the debug spawner's vehicle path
`SpawnEntityOnGroundPos` passes when no player is given, or `ECE_KEEPHEIGHT` for a boat in
DEVELOPER builds, `4_World/plugins/pluginbase/plugindeveloper.c:478-505`) nor the fuller set
`ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS` (the AI spawn path `SpawnAI`,
`plugindeveloper.c:454`) fire `EEOnCECreate`: both controls
read `fuel_fraction` 0, and so did the modded vehicle. Only a real Central Economy spawn
exercises the override, so observing it needs a `types.xml` entry plus an event. Without a
vanilla control in the same run, that zero reads as "my override is broken".

## Invariant 16: a drive-ready test kit fills every fluid and attaches the radiator

**Drive-ready TEST KIT: fill ALL fluids + attach the radiator, not just FUEL (recurring: LFQuad and SUB_BRZ).** An admin/harness kit that only `Fill(CarFluid.FUEL,...)` leaves OIL/COOLANT/BRAKE empty → the oil
gauge goes RED and the engine BREAKS while driving (looks like a physics/drivetrain bug, it is NOT). A
drive-ready kit must `Fill` FUEL + OIL + COOLANT + BRAKE **and** `CreateAttachment("CarRadiator")` (coolant
needs the radiator). Vanilla `FillUpCarFluids()` does NOT do all of it, and mirroring `OnDebugSpawn` is not
enough either. It fills exactly FUEL, COOLANT and OIL — **BRAKE is not among them**
(`scripts/4_world/entities/vehicles/carscript.c:2561-2566`; a single
definition in the tree, every other hit is a call, so no subclass overrides it). The
radiator does not come from it either: that is `SpawnUniversalParts()`
(`carscript.c:2511-2515`), gated on `IsVitalRadiator()`, via `CreateInInventory` — which
searches `CARGO | ATTACHMENT` and may land in either (`inventory.c:876-893`), so a debug
spawn does not guarantee an ATTACHED radiator. Fill BRAKE and attach the radiator
explicitly; a hand-rolled `KitManual` in the mission `init.c` has to do both. `CarFluid` enum = FUEL/OIL/BRAKE/COOLANT
(on 1.30 an alias of `ETransportFluid`, `scripts/3_game/vehicles/car.c:18`, values at `transport.c:52-57`); `Fill`/`GetFluidCapacity` at `car.c:372/355`.

**How the gap shows (SUB_WRXSTI, 2026-08-19).** `FillUpCarFluids()` alone does not satisfy this invariant. A mod car whose `OnDebugSpawn` calls it and stops — which is the obvious, vanilla-faithful thing to write, and what both SUB_BRZ and
SUB_WRXSTI shipped — spawns its test car with the brake reservoir EMPTY. That is the exact state
this invariant says breaks the engine while driving, reached by following vanilla. Add the fourth
fill explicitly: `Fill(CarFluid.BRAKE, GetFluidCapacity(CarFluid.BRAKE))` — capacity from the
declared value, not a copied `200.0`, since `brakeFluidCapacity` is `1` unless the car redeclares
it (`P:\DZ\vehicles\wheeled\config.cpp:244`, the only declaration in that file). Corollary worth more than the fix: an invariant that names the right requirement AND
names a vanilla call as satisfying it will be read as "call that and you are done". Verify the
call, not the claim.

## Invariant 17: raise tyre grip with a CarWheel subclass, without touching the wheel binding

**Raise tyre grip WITHOUT touching the wheel binding: a `CarWheel` subclass of the vanilla wheel.** To add
grip to a car that slides, do NOT rewire slots/proxies (risks re-opening the freeze/wheel-bind). Declare
`class <Mod>_Wheel : CivSedanWheel { scope=2; tyreGrip=0.98; };` — it INHERITS the vanilla `inventorySlot[]`
(`P:\DZ\vehicles\wheeled\config.cpp:4768` lists CivSedanWheel_1_1.._2_2 + Spare) so it drops into the same
`CivSedanWheel_*` slots and reuses the sedanwheel proxy; only tyreGrip changes. Then `OnDebugSpawn`/kit
create `<Mod>_Wheel`. Grip is DECOUPLED from the visual wheel model (custom source-game rim = separate visual job). Measured on SUB_BRZ.

## Invariant 18: diagnose a sliding car by axis

**Diagnose "the car slides" BY AXIS — longitudinal (accelerating) vs lateral (cornering) need different
fixes.** Sliding when you FLOOR it (power-oversteer, RWD) → tyreGrip + throttle/torque down. Sliding when
you TURN (body roll unloads the inside tyre) → tyreGrip + LOW CoM + downforce + roll stiffness. A low CoM
helps the CORNERING slide (less lateral weight transfer) but NOT the accelerating slide — in RWD a very low
CoM even transfers LESS weight rearward under throttle (slightly less traction). Never sell "lower the CoM"
as the fix for wheelspin. On SUB_BRZ the accel-slide dropped with grip 0.95→0.98 + throttle 0.8→0.72; corner-slide needed CoM/downforce.

## Invariant 19: transplanting a donor mod's drivetrain

**Transplanting a donor mod's drivetrain: match (gear x central x final) / wheel-radius, never
the ratios verbatim.** (added 2026-07-10, SUB_BRZ) Wheel force per engine-Nm = total_reduction /
wheel_radius and per-gear road speed = rpm x radius / reduction, so a donor running a different
wheel radius shifts EVERY gear by r_donor/r_yours. Compare radii FIRST; the CentralDifferential
ratio is the compensation lever. Case: SUB_BRZ (CivSedanWheel 0.34) adopting the Gelenvagen
drivetrain (0.48 wheels, central 1.4) keeps central 1.0 — 0.34/0.48 ~= 1/1.4 cancels the donor's
central, reproducing its per-gear speeds AND per-Nm force <1% off; copying central 1.4 verbatim
would run 29% shorter than the donor feel. The failure class cost a full session first (an
offroad central 1.5 compounded ratios authored for central 1.0 → gears ~50% short, 6th
unreachable). Corollaries: (a) donor force on half the mass = ~2x the acceleration — scale
expectations by mass before judging "too much/too little power"; (b) engine `frictionTorque` is
calibrated to the donor's mass/curve — engine-braking decel scales as fT x reduction / (radius x
mass), and when the radius/reduction terms cancel (as above) the mass-equivalent value is simply
fT x m_yours/m_donor; adopt the donor value for its cruise character but pre-compute that fallback
before the in-game cycle.

Which vehicle each of these was settled on is in `skills/_shared/knowledge/vehicles-crossproject.md`.

## Invariant 35: missing damage zone memory points do not explain collision jerks or driving stutters

**Missing DamageZone `memoryPoints[]` / Memory `dmgzone_*` points do NOT explain collision jerks or driving stutters (added 2026-08-30, LFQuad2).** The script contact path never reads `memoryPoints[]`. `Transport.OnContact` caches the first contact of the tick, with the momentum change as its impulse (`P:\scripts\3_game\vehicles\transport.c:315`; on 1.29 `CarScript.OnContact`, 1.29 `carscript.c:1454-1478`); `CheckContactCache` applies `ProcessDirectDamage(..., zoneName, "EnviroDmg", "0 0 0", dmg)` (`carscript.c:1291`, `:1364`). `DamageSystem.GetDamageZoneMap` only `ConfigGetTextArray(... componentNames)` (`P:\scripts\3_game\damagesystem.c:63`). Zero `memoryPoints` hits in `scripts/**/*.c`; the same grep finds them in vehicle configs. Vanilla OffroadHatchback `class Chassis` has `componentNames[]` and no `memoryPoints[]` (`P:\DZ\vehicles\wheeled\config.cpp:1579-1593`). `m_VFXComponent.ConvertMemPointToPosition("dmgZone_*")`, called from the ctor (`carscript.c:369-375`; 1.29 `GetMemoryPointPos`, 1.29 `carscript.c:393-406`), feeds `GetEnginePointPosWS` / `GetFrontPointPosWS` / … (`:314-340`) which have **zero callers**. Geometry is the contact mesh; a working referent can carry `dmgzone_*` only in FireGeometry (+ Memory for config parity). Do not spend an in-game cycle adding Memory `dmgzone_*` as a jerk fix. DISTINCT from #9 (missing `class Engine`/`FuelTank` stalls a started engine). Native `OnContact.zoneName` / `GetDamageZonePos` remain C++-opaque — even if they used memory points, that would change which zone loses HP, not the impulse.

## A sliding car is almost never fixed by lowering grip: weigh wheel force against grip (added 2026-09-11, Arma2Quad)

A first-order Coulomb estimate is not a simulation, but it RANKS layouts, and the ranking is the
decision. First gear asks `clutch cap x gear x final drive / tyre radius` at the wheels; the
driven axle holds `mass x 9.81 x its share of the weight x tyreGrip`. On a 750 kg quad with a
180 Nm cap, 4.3 x 3.667 / 0.35 m, front/rear split 65.2/34.8:

| layout | asked | held | over | what the driver said |
|---|---|---|---|---|
| RWD | 8109 N | 2535 N | 3.2x | "they slide a lot" |
| AWD, open diffs | 8109 N | 7284 N, less in a corner: the inner wheel spins first | - | "they slide a lot" |
| AWD, locked rear | 8109 N | 7284 N | 1.11x | "least bad, but it cannot go straight at full throttle without skidding" |
| FWD (shipped) | 8109 N | 4749 N | 1.7x | stable, but "it turns less" |

That arithmetic predicted the exact order the driver reported. Lowering `tyreGrip` moves every
row the wrong way: at 0.85 the locked-rear AWD goes from 1.11x to 1.30x and the FWD from 1.7x to
2.0x. It agrees with invariant 18 from the other side - the SUB_BRZ accel-slide was fixed with
grip UP and throttle DOWN.

Vanilla `tyreGrip` census for healthy wheels, so no one calls a value "too high" again without
one: 0.80 (`P:\DZ\vehicles\wheeled\config.cpp:877`), 0.82 (`:13427`), 0.85 (`:4783`), 0.89 (`:9001`), 0.95 (`:18109`, `:20558`),
1.0 (`:18145`); ruined wheels sit at 0.2-0.5. A 0.99 is inside the vanilla band.

Corollary for a wheel-driven steering axle: on `DRIVE_FWD` the wheels that spin are the wheels
that steer, so excess torque reaches the driver as "it will not turn", never as "wheelspin".
Halving a vehicle's mass halves the grip budget while leaving the torque where it was, which on
its own turns a vehicle that steered into one that pushes - the trap behind 15g(a).

## CivilianSedan on a straight: what torque, tyreGrip and the gear ratios did, measured (added 2026-09-24)

Measured 2026-09-13 in DayZDiag: NWAF concrete, standing start at full throttle through the MCP
drive controller, one config field changed per variant on `CivilianSedan` / `CivSedanWheel`,
`vehicle_trace` at 19-20 Hz. The samples are small and the n is given per result: these are
measurements, not general law. The controller of that build skipped gears above ~33 km/h
(see the dayz-mcp-verify skill), so the launch figures stop there.

- **Torque drives the launch almost proportionally.** Acceleration over the first 3 s scales as
  torque^0.93-0.95 (torque ×0.7 → ×0.72, n = 1; ×1.3 with clutch 520 → ×1.28, n = 3; baseline
  n = 5), and the 0-30 km/h time as torque^-1.17. First gear does not slip (rear slip p90
  ≈ 0.001): the torque reaches the ground.
- **tyreGrip between 0.70 and 1.00 changed neither the straight launch (≤ 2 %) nor braking
  (5.7-6.0 m/s²).** At 0.30 the car braked 22-30 % less and launched 10 % faster with almost no
  slip (n = 1, unexplained). In this regime tyreGrip does not act as a simple longitudinal
  friction coefficient.
- **First upshift at 9.20 m/s**, against 9.33 m/s predicted by
  `0.8 × redline × 2πr / (60 · i_1 · i_final)` (n = 5): the formula holds for wheel radius and
  gear ratios.
- **Steady arc at steering 0.3** (~20 m circles): drift angle falls from 8.3° at 14 km/h to 3.4°
  at 32 km/h, lateral acceleration reaches 7.2 m/s² (≈ 0.73 g), no slide (n = 1).

Rule of thumb: to change the launch, change the torque. Above ~0.7, tyreGrip does not change the
vanilla sedan's straight launch or braking; look for its effect in cornering and drift, which is
not measured yet.
