# Vehicle types: boats and trucks, with notes on quads and motorbikes

What changes when the vehicle is not a four-wheeled `CarScript` car: boats (a sibling of `Car` under `Transport`), trucks (a `CarScript` config with three axles and double wheels), mod-made quads, and the motorbike family that arrived in DayZ 1.30.

> Status: written from the vanilla scripts and configs. Every citation of a 1.30 file below was opened on `P:\` (a 1.30 build); a citation without the `P:\` prefix names the same file under `P:\scripts`, `P:\DZ` or `P:\bin`. A number marked "1.29" belongs to the 1.29 build, which is not on `P:\`, and is not yet checked on `P:\`. A citation written with its full `P:\` path is also checked by the repo tests. `[UNVERIFIED]` marks anything the vanilla data does not pin down. "Preflight #N" and "invariant N" mean the numbered invariants; `README.md` lists which file holds each number.

The invariant files of this pack are written around the `CarScript` (wheeled) case. This file is the difference for the other `Transport` subclasses: boats, trucks (a car config, not a new class), mod-made quads, and the motorbike gap that 1.30 closed. `class-hierarchy.md` holds the short form of the class tree and `simulation.md` the `SimulationModule` keys; this file adds the per-type detail.

## Vanilla anchors checked on `P:\`

- `Transport` is declared at `P:\scripts\3_game\vehicles\transport.c:66`.
- `Car` extends it at `P:\scripts\3_game\vehicles\car.c:87`.
- `Boat` extends it at `P:\scripts\3_game\vehicles\boat.c:28`.
- `BoatScript` is declared at `P:\scripts\4_world\entities\vehicles\boatscript.c:41`.
- `BoatFluid` is declared at `P:\scripts\3_game\vehicles\boat.c:13`.
- The boat's `CrewCanGetThrough` override is at `P:\scripts\4_world\entities\vehicles\boatscript.c:205`.
- The boat config's `Buoyancy` class is at `P:\DZ\vehicles\water\config.cpp:32`.
- The boat config's `Propeller` class is at `P:\DZ\vehicles\water\config.cpp:167`.
- `Truck_01_Base` is declared at `P:\DZ\vehicles\wheeled\config.cpp:18429`.
- The truck's `DRIVE_642` line is `P:\DZ\vehicles\wheeled\config.cpp:18539`.
- `Truck_01_WheelDouble` is declared at `P:\DZ\vehicles\wheeled\config.cpp:18128`.
- The truck's seat types (`VEHICLESEAT_DRIVER` and `VEHICLESEAT_CODRIVER` only) are at `P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c:135`.
- The engine config class `Motorbike` is at `P:\bin\config.cpp:1481`.
---

## 1. The hierarchy — Car and Boat are SIBLINGS (the central invariant)

```
Pawn (FEATURE_NETWORK_RECONCILIATION) / EntityAI
 └─ Transport            transport.c:66-69
     ├─ Car              car.c:87            → CarScript   carscript.c:94
     └─ Boat             boat.c:28           → BoatScript  boatscript.c:41
```

(up to 1.29: the diagram above is complete — `Transport` has two scripted children.)
(since 1.30: a third native sibling `Motorbike` with `simulation = "motorbike"` sits next to `Car` and `Boat`. Engine proto `class Motorbike extends Transport` at `scripts\3_game\vehicles\motorbike.c:30`; config `bin\config.cpp:1481-1486`. Scripted layer `MotorbikeScript` does **not** inherit `CarScript`. Two-wheel contract: `motorbikes.md` and `motorbike-invariants.md` of this pack. Full 1.30 vehicle deltas: `dayz-1-30-vehicles.md`.)

- `class Transport extends Pawn` (with `FEATURE_NETWORK_RECONCILIATION`) /
  `extends EntityAI` (without) — `scripts\3_game\vehicles\transport.c:66-69`.
- `class Car extends Transport` — `scripts\3_game\vehicles\car.c:87`.
- `class Boat extends Transport` — `scripts\3_game\vehicles\boat.c:28`.
- Scripted layer: `class CarScript` — `scripts\4_world\entities\vehicles\carscript.c:94`.
  `class BoatScript : Boat` — `scripts\4_world\entities\vehicles\boatscript.c:41`.
- Config layer: `class BoatScript: Boat` base at `DZ\vehicles\water\config.cpp:17`;
  concrete `Boat_01_ColorBase: BoatScript` at `:47`. Truck base
  `Truck_01_Base: CarScript` at `DZ\vehicles\wheeled\config.cpp:18429`.

**Key structural fact:** Car and Boat are SIBLINGS, both directly under
`Transport`. They are NOT parent/child. A boat does not inherit anything wheeled,
and a car does not inherit anything buoyant. This governs where each feature
lives:

| Concern | Lives on | Why it matters |
|---|---|---|
| Crew / get-in / flip / fuel plumbing / lights / physics helpers | **Transport** | shared by cars AND boats |
| Wheels / brakes / handbrake / `CarFluid` (OIL/BRAKE/COOLANT) | **Car** | boat has NONE of these |
| Propeller / buoyancy / `BoatFluid` (the type holds every fluid since 1.30; `BoatScript` uses only `FUEL`) | **Boat** | car has none of these |

(since 1.30: `enum ETransportFluid` on `Transport` (`scripts\3_game\vehicles\transport.c:52-63`) is the shared fluid enum. `BoatFluid : ETransportFluid {}` (`Boat.c:13`) and `MotorbikeFluid : ETransportFluid {}` (`Motorbike.c:14`) inherit it; fuel plumbing is no longer a Boat-only isolated enum.)

A **truck is just a `CarScript` config** with more axles and double wheels — no
new class (see §4).

### 1.1 What Transport OWNS (shared by Car AND Boat)

- Crew system (native): `CrewSize/CrewMemberIndex/CrewMember/CrewDriver/CrewEntry/
  CrewEntryWS/CrewTransform/CrewGetIn/CrewGetOut/CrewDeath` — `transport.c:175-212`.
  `OnDriverEnter/OnDriverExit` hooks — `transport.c:218-224`.
- Lights: `LightIsOn/LightOn/LightOff/LightToggle`, `OnBeforeLightOn`,
  `UpdateLights` — `transport.c:227-255,362`.
- Fuel refill point: `m_fuelPos` from memory point `"refill"`,
  `GetRefillPointPosWS` — `transport.c:112-115,459-472`.
- Flip detection scaffolding: `DetectFlipped` (override per-impl), `IsFlipped`,
  `DetectFlippedUsingSurface` (water-aware, uses `GetWaterDepth`) —
  `transport.c:522-619`.
- Deterministic physics helpers: `ApplyForce/ApplyTorque/ApplyImpulseAt/...` —
  `transport.c:260-275`.
- Get-in door-clearance: `IsAreaAtDoorFree` — `transport.c:844-899`.
- `GetVehicleType()` returns `"VehicleTypeUndefined"` on base —
  `transport.c:454-457` (each subclass overrides).

### 1.2 CAR-only additions (`car.c`)

- Wheels API (native): `WheelCount/WheelCountPresent/WheelGetAngularVelocity/
  WheelHasContact/WheelGetSurface/WheelGetWaterState/WheelGetEntity/
  WheelIsLocked` — `car.c:272-348`. `CarWheelWaterState` enum
  (ON_LAND/IN_WATER/UNDER_WATER) — `car.c:67-72`.
- Brakes + handbrake: `GetBrake/SetBrake/GetHandbrake/SetHandbrake/
  SetBrakesActivateWithoutDriver` — `car.c:200-212`. **Boat has NO brake API.**
- Fluids: `CarFluid` = FUEL/OIL/BRAKE/COOLANT (+USER1-4): on 1.30 an alias of `ETransportFluid` (`car.c:18`,
  values at `transport.c:52-63`); 1.29 declared the values in `car.c` itself (1.29 `car.c:18-29`).
  Speedometer `GetSpeedometer` — `car.c:102`.
  (since 1.30: `GetSpeedometer` is **not** Car-only. `Boat` implements `GetSpeedometer()` and `GetSpeedometerAbsolute()` at `scripts\3_game\vehicles\boat.c:42-56`.)
- Flip via wheels: `DetectFlippedUsingWheels` (all wheels must have contact) —
  `car.c:157-178`.
- Scripted get-in actions: `SetActions()` adds `ActionOpenCarDoorsOutside,
  ActionCloseCarDoorsOutside, ActionGetInTransport, ActionSwitchLights,
  ActionCarHornShort/Long, ActionPushCar` — 1.29 `carscript.c:2871-2880`.
  (up to 1.29: `ActionCarHornShort/Long` as listed.)
  (since 1.30: `CarScript.SetActions()` at `scripts\4_world\entities\vehicles\carscript.c:2313-2321` adds `ActionVehicleHornShort`/`ActionVehicleHornLong`. `ActionCarHornShort`/`Long` are `[Obsolete]` (`ActionCarHorn.c:69-70,213-214`). Empty aliases `CarHornShortActionInput : VehicleHornShortActionInput {}` at `ActionInput.c:757-758,773-774`.)

---

## 2. BOAT — the deltas vs the CarScript contract

A boat is authored like a car up to the `Transport`-shared layer, then diverges.
Do NOT copy a car's `Axles`/brakes/`CarFluid` blocks into a boat.

| Area | Boat | vs Car |
|---|---|---|
| Fluids | 1.29: `BoatFluid` = **FUEL only** (1.29 `boat.c:13-16`); 1.30: an alias of `ETransportFluid` (`boat.c:13`), the enum `CarFluid` also aliases | Car has FUEL/OIL/BRAKE/COOLANT |
| Propulsion | **Propeller** native: `PropellerGetPosition()`, `PropellerGetAngularVelocity()` — `boat.c:125-128` | Car has wheels; no propeller |
| Brakes | **none** (no brake/handbrake protos) | Car has full brake API |
| Steering | `GetSteering/SetSteering(float)` — `boat.c:59-62` (Car's `SetSteering` has an extra `bool unused0`, `car.c:185`) | signature differs |
| Sound ctrl | `BoatSoundCtrl` = ENGINE/SPEED/PLAYER — `boat.c:2-10` (no RPM, no DOORS) | Car adds RPM, DOORS |
| Get-in | `CrewCanGetThrough/CanReachSeatFromSeat/...` all return **true** — `boatscript.c:205-223` (no doors, open cockpit) | Car GATES by door state |
| Anim | `GetAnimInstance()` = `VehicleAnimInstances.ZODIAC` — `boatscript.c:195-198` | Car uses its own instance |
| Actions | `SetActions()` = only `ActionGetInTransport` + `ActionPushBoat` — `boatscript.c:758-762` | Car adds doors/lights/horn |
| Type | `GetVehicleType()` = `"VehicleTypeBoat"` — `boatscript.c:175-178` | Car returns its own |

(up to 1.29: `BoatFluid` listed as an isolated enum at `boat.c:13-16`.)
(since 1.30: `enum BoatFluid : ETransportFluid {}` at `scripts\3_game\vehicles\boat.c:13` — still fuel-only in practice, but it **inherits** the shared `ETransportFluid` base. Speedometer rows above are no longer Car-exclusive.)

### 2.1 Get-in is ALWAYS free on a boat

This is the single most useful contrast for the core-skill reader. The CarScript
preflight #1 exists because a bare `CarScript` inherits `CrewCanGetThrough()` →
`false`, killing the get-in radial. A boat does NOT have that trap: `BoatScript`
overrides `CrewCanGetThrough` (and `CanReachSeatFromSeat`, etc.) to return
**true** unconditionally — `boatscript.c:205-223` — because it is an open cockpit
with no doors. There is no door-state gating to satisfy.

### 2.2 Water physics (config, not script)

On the config base `BoatScript` there is a `class Buoyancy` in place of a car's
`Axles`/brakes — `DZ\vehicles\water\config.cpp:32-40`:

```cpp
class Buoyancy
{
    linearDampeningCoefficient;
    angularDampeningCoefficient;
    linearDragCoefficient  = 0.2;
    quadraticDragCoefficient = 0.2;
    falloffPower = 0.8;
    sinkRate = 0.05;
};
```

Native buoyancy state lives on the owner: `SetBuoyancySubmerged/
GetBuoyancySubmerged` — `transport.c:22-23` (`TransportOwnerState`).

The boat `SimulationModule` (config block `:124-180`) has **NO
`Axles` block and NO brakes**. Instead it carries a `class Propeller` plus the
usual Engine/Clutch/Gearbox/Throttle/`class Steering`:

```cpp
class Propeller
{
    position; radius; outerRadius; innerRadius;
    efficiency; cavitationThreshold; pitch; width;
    numberOfBlades = 3; mass;
};
```

`DZ\vehicles\water\config.cpp:124-180` (the `Propeller` class is `:167-179`). There is no `Axles`/`Wheels`/brake class
anywhere in a boat's `SimulationModule`.

### 2.3 Boat runtime deltas (`boatscript.c`)

- **Auto-stop out of water:** the engine auto-stops if the propeller lifts out of
  the water — `GetWaterDepth(pos) < -0.2 → EngineStop()` in `EOnSimulate` —
  `boatscript.c:393-407`. Also stops on no-fuel — `:361-371`.
- **Decay while unoccupied:** server-side `Timer DecayHealthTick` every 10s, ×4
  if flipped — `boatscript.c:44-47,110-111,534-548`.
- **4 water particle effects** attached to memory points `ptcFxFront/Back/Side1/
  Side2` — `boatscript.c:129-144`. Effect classes `EffectBoatWaterFront/Back/Side`
  in `scripts\4_world\entities\effects\boatwatereffects.c:10,116,199` (speed-gated
  emitters; the Back effect reads `PropellerGetAngularVelocity` for speed
  `boatwatereffects.c:183`).
- **Vital `SparkPlug`** gates engine start — `boatscript.c:278-286`
  (`CheckOperationalRequirements`). (Contrast the car's SparkPlug+GlowPlug double
  default in invariant 8, `invariants-engine-fluids-and-handling.md` — the boat only ever demands its SparkPlug.)
- **Flip uses the SURFACE detector** (water-aware), not wheels —
  `boatscript.c:490-495`.

### 2.4 Boat actions (`scripts\4_world\...\actions\`)

- `ActionStartEngineBoat` (continuous) / `ActionStopEngineBoat` (single-use):
  both cast target to `BoatScript`, require `CrewDriver()==player`, and guard
  `GetNetworkMoveStrategy()==PHYSICS` to skip server exec —
  `actionstartengineboat.c:9-70`, `actionstopengineboat.c:1-52`. The start
  action calls `vehicle.OnIgnition()` in `OnExecute` and `EngineStart()` in
  `OnFinishProgress` (`actionstartengineboat.c:58,69`). The stop action calls
  `vehicle.EngineStop()` in `OnExecute` (`actionstopengineboat.c:51`).
- `ActionPushBoat extends ActionPushObject` — full-body, syncs `SyncSoundPushBoat`
  on start/end (server) — `actionpushboat.c:17-46`.
- `ActionRepairBoatChassis` and `ActionRepairBoatEngine` both extend
  `ActionRepairVehiclePartBase`. The chassis action repairs any zone except
  `Engine` whose health level is above WORN and below RUINED
  (`actionrepairboatchassis.c:33-37`). The engine action repairs only the
  `Engine` zone in that same band, needs the engine off and a blowtorch with
  enough energy (`actionrepairboatengine.c:26-48`).

(since 1.30: `BoatScript.GetHeatComfortOverride()` at `scripts\4_world\entities\vehicles\boatscript.c:256-259`. Config AI noise `class NoiseBoatEngine { type = "sound"; strength = 30; }` at `DZ\vehicles\water\config.cpp:41-45`.)

---

## 3. (reserved — see §4 for the truck deltas)

---

## 4. TRUCK — a Car config with more axles + double wheels (NOT a new class)

A truck (`Truck_01_Base: CarScript` — `DZ\vehicles\wheeled\config.cpp:18429`) is
NOT a new class. It is a plain `CarScript` config; the deltas are pure config.

| Feature | Truck config | Standard car (contrast) |
|---|---|---|
| Axle count | **3 axles**: `class Front`, `class Middle: Rear`, `class Rear: Rear` — `config.cpp:18569-18672` | 2 axles (Front/Rear) |
| Drivetrain | `drive="DRIVE_642"` (6×4) — `config.cpp:18539`; `class CentralDifferential { type="DIFFERENTIAL_LOCKED"; }` — `:18564-18568` | typically DRIVE_4x2/4x4 |
| Wheel slots | 6 wheel hubs `Truck_01_Wheel_1_1..2_3` + 2 spares — `config.cpp:18441-18448`; only the 4 Middle and Rear hubs are driven, since `class Front` has no `Differential` (`config.cpp:18571-18597`, base `:287-308`) | 4 hubs |
| Double wheel | Middle+Rear hubs take **`Truck_01_WheelDouble`** — `config.cpp:18128-18141`; its `inventorySlot[]` = the 4 rear slots `1_2,1_3,2_2,2_3`. `width=0.40` (vs single `0.20`), `weight=50000` (vs 30000), better grip/resistance | single `Truck_01_Wheel` |
| Dual-wheel craft | `Truck_01_Wheel + Truck_01_Wheel → Truck_01_WheelDouble` recipe — `crafttruck01doublewheel.c:27-46`; reverse decraft needs Crowbar/LugWrench → 2 wheels — `decrafttruck01doublewheel.c:36,48-60` | n/a |
| Crew | **2 seats**: Driver + CoDriver. `Truck_01_Base` declares no `class Crew` of its own and inherits the two-seat one of the config base `CarScript` (`config.cpp:265-283`); its script maps only seats 0 and 1 (`truck_01_base.c:130-138`). The four-seat `Crew` block at `config.cpp:1348-1366` belongs to `OffroadHatchback`, not to the truck. | 2-4 depending |
| Cargo | `class Cargo { itemsCargoSize[]={10,40}; }` — `config.cpp:18674-18677` | small/none |
| Fuel | `fuelCapacity=120; fuelConsumption=30` — `config.cpp:18506-18507` | ~50 / lower |

### 4.1 The "double wheel" invariant

**One attachment classname per rear hub covers BOTH physical tyres via the
`Truck_01_WheelDouble.p3d` model** — it is NOT two wheel entities per hub. The
rear axles reference it via `inventorySlot` in the Axles/Wheels blocks
(`config.cpp:18598-18668`). Each Middle/Rear wheel also declares
`wheelHub="wheel_X_Y_damper_land"` plus `animDamper`/`animTurn`/`animRotation`.

So a truck's structural parity is a car's parity (invariants 1 to 9) with:
(a) 6 wheel hubs instead of 4, (b) the rear four resolving to one WheelDouble
classname each, (c) 3 axle blocks with a locked central differential, (d) the
same two-seat crew as the config base. Nothing about get-in, DamageZones, or the vital-igniter chain changes — it
is still `CarScript`.

(since 1.30: abandoned cistern wrecks `Land_Wreck_Truck01_Aban1_Cistern` and `Land_Wreck_Truck01_Aban2_Cistern` extend `Well` — they are drinkable, not vehicle entities. `scripts\4_world\entities\building\wrecks\wreck_truck01_aban1_cistern.c:1` and `wreck_truck01_aban2_cistern.c:1`.)

---

## 5. ATV (quad) — mod pattern, one line

Mod-made ATVs are plain `CarScript` with slots hung off `Chassis` instead of
`Body`. (No vanilla ATV in the base game; this is third-party mod behaviour, not
vanilla, and not yet checked on `P:\`.) Everything else is the standard
`CarScript` contract of the invariant files (TestQuad is the worked example throughout
them: a quad IS a car).

---

## 6. Motorbikes — honest gap

> (updated 2026-09-16) This gap closed with DayZ 1.30 Experimental (build 1.30.164014): the engine ships `class Motorbike: Transport` with `simulation = "motorbike"` (`bin\config.cpp:1481-1486`), `MotorbikeScript` (`4_World\Entities\Vehicles\MotorbikeScript.c:53`, not a `CarScript`), two vanilla bikes (`Motorbike_01` = Jawa_05, `Motorbike_02` = Jawa_Bitrak in `vehicles_singletrack.pbo`) and a 2-wheel `SimulationModule` (`Wheels{Front,Rear}` instead of `Axles`, `Steering.maxLeanAngle[]`/`tipoverAngle`, `Brakes{Front input=1, Rear input=0}`; `DZ\vehicles\singletrack\config.cpp:263-378` for `Motorbike_01_ColorBase`). The contract, script API, actions, sounds and rider animation live in `motorbikes.md` and `motorbike-invariants.md` and the other motorbike files of this pack. The paragraph below is the pre-1.30 state; its "do not derive from Axles" warning still holds.

(up to 1.29:) No vanilla motorbike exists, so the 2-wheel physics pattern has no vanilla reference.
Do not fabricate a `SimulationModule` for two wheels from the car pattern — a
motorbike's lean/balance model is not derivable from the 4-wheel `Axles` blocks
and there is nothing verified to cite. Flag `[UNVERIFIED]` and check the engine first.
