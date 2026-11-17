# Vehicles and network synchronization (`Transport`, `CarScript`)

Covers why a vehicle's position replicates and a free physics body on an item does not, the script side of `Transport`, `Car` and `CarScript` (crew, controls, fluids, contact damage), the vanilla push action, and what that means for a mod object that has to move for every client.

Citations are `P:\...:line`, opened on `P:\` (a 1.30 build). `1.29:<path>:<line>` is a line in the 1.29 scripts, which are not on `P:\` and were not re-checked. Vehicle authoring (config, model, wheels) is not this file's job: use the vehicles pack, `skills/_shared/vehicles/`.

## Summary

The vehicle system has three layers:

1. **`Transport` (native plus script).** The base class of every vehicle. It inherits from `Pawn` when `FEATURE_NETWORK_RECONCILIATION` is defined, and from `EntityAI` in builds without it. This is where replication happens: `Transport` registers `TransportOwnerState` and `TransportMove` and uses `NetworkMoveStrategy.NONE`, its own native network tick, not the player's reconciliation system.
2. **`Car`, `Boat`, `Helicopter` (native).** They inherit from `Transport` and expose the physics API (throttle, steering, brake, fluids, gears). The simulation is native; script only calls setters.
3. **`CarScript`, `BoatScript`, `HelicopterScript` (script).** Wrappers that add contact damage, fluids, lights, particles, sound and temperature. The contact cache that feeds damage (`m_ContactCache`) runs on the server only.

Position and rotation sync of a `Transport` is not something `ItemBase` has, and it does not use `SetSynchDirty()`. It is a property of the native `Pawn` and `Transport` type: the engine sends position plus linear and angular velocity to all clients continuously.

## Verified API

### Inheritance

```
EntityAI
└── Pawn  [FEATURE_NETWORK_RECONCILIATION]          pawn.c:191
    └── Transport                                    transport.c:66
        ├── Car                                      car.c:87
        │   └── CarScript                            carscript.c:94
        │       ├── OffroadHatchback                 offroadhatchback.c:1
        │       ├── Truck_02                         truck_02.c:1
        │       ├── Sedan_02, Van_01, Hatchback_02 ...
        │       └── Truck_01_Base, then Chassis, Cargo, Covered
        ├── Boat                                     boat.c:28
        │   └── BoatScript                           boatscript.c:41
        │       └── Boat_01_ColorBase                boat_01.c:1
        └── Helicopter, then HelicopterAuto          helicopter.c:9 and :14
            └── HelicopterScript                     helicopterscript.c:4
```

- Full paths: `P:\scripts\3_game\entities\pawn.c:191`, `P:\scripts\3_game\vehicles\transport.c:66`, `P:\scripts\3_game\vehicles\car.c:87`, `P:\scripts\4_world\entities\vehicles\carscript.c:94`, `P:\scripts\3_game\vehicles\boat.c:28`, `P:\scripts\4_world\entities\vehicles\boatscript.c:41`, `P:\scripts\3_game\vehicles\helicopter.c:9`, `P:\scripts\4_world\entities\vehicles\helicopterscript.c:4`.
- Without `FEATURE_NETWORK_RECONCILIATION` the tree is `EntityAI`, then `Transport` (the `#else` at `P:\scripts\3_game\vehicles\transport.c:67-68`). The define is at `P:\scripts\1_core\defines.c:64`.

### `Transport` (`P:\scripts\3_game\vehicles\transport.c`)

| Method | Signature | Line | Note |
|---|---|---|---|
| `Synchronize()` | `proto native void Synchronize()` | `:172` | Forces a state sync when the simulation is not running |
| `CrewSize()` | `proto native int CrewSize()` | `:175` | |
| `CrewPositionIndex(int componentIdx)` | `proto native int` | `:179` | Maps a raycast component index to a seat index |
| `CrewMemberIndex(Human player)` | `proto native int` | `:183` | -1 when the player is not inside |
| `CrewMember(int posIdx)` | `proto native Human` | `:187` | null when the seat is empty |
| `CrewDriver()` | `proto native Human` | `:191` | |
| `CrewGetIn(Human player, int posIdx)` | `proto native void` | `:206` | |
| `CrewGetOut(int posIdx)` | `proto native Human` | `:209` | |
| `CrewDeath(int posIdx)` | `proto native void` | `:212` | |
| `ApplyForce`, `ApplyTorque`, `ApplyForceAt`, `ApplyCentralImpulse`, `ApplyTorqueImpulse`, `ApplyImpulseAt` | `proto void` | `:260-275` | Deterministic physics |
| `Random`, `RandomRange`, `Random01` | `proto native` | `:283-296` | Only inside `EOnSimulate` or `EOnPostSimulate` |
| `OnContact(zoneName, localPos, other, data)` | `void` | `:315` | Collision callback |
| `OnInput(float dt)` | `void` | `:353` | Called after each input step |
| `OnUpdate(float dt)` | `void` | `:359` | Every frame on a client, fixed rate on the server |
| `IsTransport()` | `override bool`, returns true | `:364` | |

### `Car` script physics API (`P:\scripts\3_game\vehicles\car.c`)

```cpp
proto native float GetSpeedometer();          // :102  km/h, signed
proto native float GetSteering();             // :182  <-1,1>
proto native void  SetSteering(float value, bool unused0 = false);   // :185
proto native float GetThrottle();             // :188  <0,1>
proto native void  SetThrottle(float value);  // :191
proto native float GetBrake();                // :200
proto native void  SetBrake(float value, float unused0 = 0, bool unused1 = false);   // :203
proto native float GetHandbrake();            // :206
proto native void  SetHandbrake(float value); // :209
proto native void  SetBrakesActivateWithoutDriver(bool activate = true);             // :212
proto native float EngineGetRPM();            // :227
proto native bool  EngineIsOn();              // :230
proto native void  EngineStart();             // :233
proto native void  EngineStop();              // :236
proto native int   GetCurrentGear();          // :245  see enum CarGear (REVERSE, NEUTRAL, FIRST ... SIXTEENTH)
proto native int   GetGear();                 // :248  the gear about to be applied
proto native int   GetNeutralGear();          // :251
proto native int   GetGearCount();            // :254
proto native void  ShiftUp();  ShiftTo(int gear);  ShiftDown();          // :257, :260, :263
proto native CarGearboxType GearboxGetType(); // :266  MANUAL | AUTOMATIC
proto native bool  WheelHasContact(int wheelIdx);                       // :286
proto native vector WheelGetContactPosition(int wheelIdx);              // :293
proto native int   WheelCount();              // :345  all hubs
proto native int   WheelCountPresent();       // :348  wheels actually fitted
proto native float GetFluidCapacity(CarFluid fluid);                    // :355
proto native float GetFluidFraction(CarFluid fluid);                    // :363  <0,1>
proto native void  Leak(CarFluid fluid, float amount);                  // :366
proto native void  LeakAll(CarFluid fluid);                             // :369
proto native void  Fill(CarFluid fluid, float amount);                  // :372
```

- **Fluids.** `CarFluid` has FUEL, OIL, BRAKE, COOLANT and USER1 to USER4. In 1.30 these are the values of `ETransportFluid` (`P:\scripts\3_game\vehicles\transport.c:52-63`), which `CarFluid` extends (`P:\scripts\3_game\vehicles\car.c:18`); in 1.29 they were listed in `1.29:3_game\vehicles\car.c:17-29`.
- **Gears.** `CarGear` is REVERSE, NEUTRAL, FIRST to SIXTEENTH (`P:\scripts\3_game\vehicles\car.c:32-52`).

### `CarController` is obsolete

`GetController()` is marked `[Obsolete("Use methods directly on Car")]` (`P:\scripts\3_game\vehicles\car.c:435-436`). `CarController` remains as a legacy class for old code (`P:\scripts\3_game\vehicles\car.c:461`). Do not use it in a new mod.

### `EOnPostSimulate`: signature and where it runs

```cpp
// P:\scripts\4_world\entities\vehicles\carscript.c:207, in the constructor:
SetEventMask(EntityEvent.POSTSIMULATE);
SetEventMask(EntityEvent.POSTFRAME);

// P:\scripts\4_world\entities\vehicles\carscript.c:807 (condensed)
override void EOnPostSimulate(IEntity other, float timeSlice)
{
    m_Time += timeSlice;
    if (g_Game.IsServer())
    {
        CheckContactCache();         // applies the collision damage gathered this tick
        m_VelocityPrevTick = GetVelocity(this);
        m_MomentumPrevTick = GetMomentum();
    }
    // every GameConstants.CARS_FLUIDS_TICK: parts health check, engine stop, fluid leaks, engine wear
}
```

`EOnPostSimulate` runs on the server and the client. The damage part (`CheckContactCache`, `:826`) and the engine wear are behind `g_Game.IsServer()`; the engine stop and the fluid leaks are behind `IsServerOrOwner()` (`:846-910`). `IsServerOrOwner()` (`P:\scripts\4_world\entities\vehicles\carscript.c:2592`) returns `IsServer()` for the classic networking, or `IsOwner()` when the strategy is `NetworkMoveStrategy.PHYSICS`.

`EOnSimulate` is not in `carscript.c` or `transport.c`: a car's physics loop is native and script does not override it. `BoatScript` is the exception, with its own `EOnSimulate` (`P:\scripts\4_world\entities\vehicles\boatscript.c:393`).

### `OnInput` and `OnUpdate`

```cpp
// P:\scripts\4_world\entities\vehicles\carscript.c:1041 (the DIAG test branch, condensed)
override void OnInput(float dt)  // called by the engine so script can apply controls
{
    SetThrottle(throttleWanted);
    SetSteering(steeringWanted);
    SetBrake(0.1);
    SetHandbrake(0.0);
}

// P:\scripts\4_world\entities\vehicles\carscript.c:1210
override void OnUpdate(float dt)
{
    Human driver = CrewDriver();
    if (driver && !driver.IsControllingVehicle())
        if (driver.IsAlive())
            SetBrake(0.5);     // brakes when the driver is unconscious
}
```

Outside the diagnostic test code, `CarScript.OnInput` does nothing of its own: a human driver controls the vehicle through their input, which the native physics reads directly.

## `CfgVehicles` config

The vehicle config uses `SimulationModule` and is declarative. It is not in script; it lives in the `config.cpp` of the vehicle addons. In `P:\DZ\vehicles\wheeled\config.cpp` the vanilla car config writes it as nested classes, not arrays:

- `class SimulationModule` (`:283`): the vehicle's physics parameters
  - `class Axles`, each axle with `class Wheels` (`:285-289`)
  - `class Steering` with `maxSteeringAngle` (`:441-443`)
  - `class Brake` with `pressureBySpeed[]` (`:456-458`)
  - `class Aerodynamics` with `frontalArea` and `dragCoefficient` (`:462-465`)
  - `drive`: `"DRIVE_RWD"` (`:469`), `"DRIVE_FWD"` (`:565`), `"DRIVE_AWD"` (`:659`)
  - `class Engine` with `torqueCurve[]`, `rpmIdle`, `rpmMin`, `rpmClutch` and `rpmRedline` (`:470-480`)
  - `class Gearbox` with `type` (`"GEARBOX_MANUAL"`), `reverse` and `ratios[]` (`:488-492`)
- `attachments[]`: the attachment slot names, such as `CarBattery` and the reflectors (`:333-338`)
- `class DamageZones`: the damage zones (`:124`)

The key names `steerAngle`, `frictionCoef`, `dampingRate`, `torqueMax`, `maxRPMDrop`, `engagingSpeed` and `RPMMax` have 0 matches in that file; do not write them. Use `skills/_shared/vehicles/simulation.md` for the full set of keys.

The enums `CarFluid` (FUEL, OIL, BRAKE, COOLANT) and `CarGear` do exist in script and drive the fluid and gearbox behaviour there.

## Why `Transport` replicates and `ItemBase` does not

### The basic difference

```
Transport extends Pawn extends EntityAI    (transport.c:66, pawn.c:191)
ItemBase extends EntityAI                  (not a Pawn)
```

`Pawn` is the native type the engine treats as a possessed or controlled entity with continuous network movement (`P:\scripts\3_game\entities\pawn.c`):

- `GetOwnerStateType()` returns `PawnOwnerState`, the full state used to correct a desync (`:238`).
- `GetMoveType()` returns `PawnMove`, the movement packet (`:247`).
- `GetNetworkMoveStrategy()` returns the active strategy: `NONE`, `LATEST` or `PHYSICS` (`:218`; the enum at `:138-148`).

`Transport` overrides both types (`P:\scripts\3_game\vehicles\transport.c:160-169`):

```cpp
protected override event typename GetOwnerStateType() { return TransportOwnerState; }
protected override event typename GetMoveType()        { return TransportMove;       }
```

`TransportOwnerState` has `SetWorldTransform` and `GetWorldTransform`, `SetLinearVelocity` and `GetLinearVelocity`, `SetAngularVelocity` and `GetAngularVelocity` (`P:\scripts\3_game\vehicles\transport.c:11-30`). These fields are what the engine serializes and sends to the proxy clients on each vehicle network tick.

The comment above the class says so in one line (`P:\scripts\3_game\vehicles\transport.c:65-66`):

```
//! Uses NetworkMoveStrategy.NONE
class Transport extends Pawn
```

`NetworkMoveStrategy.NONE` means it does not use the client reconciliation system (the one the player uses). The engine uses its own vehicle sync instead (owned by the server, proxies on clients), sending position plus velocities to every proxy continuously.

### Why an `ItemBase` with a dynamic body does not replicate by itself

- `ItemBase` inherits from `EntityAI`, not `Pawn`. The engine has no reason to treat its transform as continuous network state.
- `SetSynchDirty()` with `RegisterNetSyncVariable...` is a mechanism for discrete state (sent when a value changes), not a continuous stream of position and velocity.
- A dynamic body on an `ItemBase` is simulated on the server, but the client does not receive the transform in real time. It updates only when the item enters the client's area of interest and on periodic resyncs. This part is native behaviour that script does not show, so it is not checked on `P:\`.
- So a client that sees such a body move in a local test is not proof of replication. It can be an artifact of low latency and a high resync rate on a local network or in single player, or of an `EntityAI` replication mechanism that script does not document.

### Network methods on `Transport`

```cpp
// P:\scripts\3_game\vehicles\transport.c:171-172
//! Synchronizes car's state in case the simulation is not running.
proto native void Synchronize();
```

`Synchronize()` pushes the state when the vehicle is not in active simulation (just activated, or the driver left and the car stood still). It confirms that the normal sync is continuous and done by the engine, with this as the manual override.

```cpp
// P:\scripts\3_game\vehicles\transport.c:810-814
void SetEngineZoneReceivedHit(bool pState)
{
    m_EngineZoneReceivedHit = pState;
    SetSynchDirty();  // the net sync variable system, for discrete state
}
```

`Transport` uses both systems: the native position stream (through `Pawn`) and `SetSynchDirty()` for state variables (lights, engine damage and so on).

## Damage in `CarScript`

### `OnContact` and `CheckContactCache`

In 1.30 the contact callback is `Transport.OnContact` (`P:\scripts\3_game\vehicles\transport.c:315-343`), which cars inherit:

```cpp
void OnContact(string zoneName, vector localPos, IEntity other, Contact data)
{
    if (GetGame().IsServer())
    {
        if (m_ContactCache.Count() == 0)  // only the first zone each frame
        {
            array<ref VehicleContactData> ccd = new array<ref VehicleContactData>();
            m_ContactCache.Insert(zoneName, ccd);
            float momentumDelta = GetMomentum() - m_MomentumPrevTick;
            float dot = vector.Dot(m_VelocityPrevTick.Normalized(), GetVelocity(this).Normalized());
            if (dot < 0)
                momentumDelta = m_MomentumPrevTick;

            VehicleContactData contactData = new VehicleContactData();
            contactData.SetData(localPos, other, momentumDelta);
            ccd.Insert(contactData);
        }
    }
}
```

In 1.29 the same logic was an override on `CarScript` with `CarContactData` (`1.29:4_world\entities\vehicles\carscript.c:1453-1479`).

`OnContact` only does work on the server. It uses the change of momentum (the change of velocity times mass) as a stand in for the collision impulse. The `Contact` it receives does have `data.Impulse`, which vanilla only logs in diagnostic builds (`P:\scripts\3_game\vehicles\transport.c:323`).

The processing happens in `CheckContactCache()`, called from `EOnPostSimulate`:

```cpp
// P:\scripts\4_world\entities\vehicles\carscript.c:1279-1364 (condensed)
void CheckContactCache()
{
    float dmg = Math.AbsInt(data[0].m_Impulse * m_dmgContactCoef);  // m_dmgContactCoef = 0.058 (:224)
    float crewDmgBase = Math.AbsInt((data[0].m_Impulse / dBodyGetMass(this)) * 1000 * m_dmgContactCoef);

    if (dmg < GameConstants.CARS_CONTACT_DMG_MIN) continue;    // minimum threshold (:1329)

    if (dmg < GameConstants.CARS_CONTACT_DMG_THRESHOLD)         // (:1338)
        SynchCrashLightSound(true);    // light crash
    else
    {
        DamageCrew(crewDmgBase);       // damage to the crew
        SynchCrashHeavySound(true);    // heavy crash
    }

    ProcessDirectDamage(DamageType.CUSTOM, null, zoneName, "EnviroDmg", "0 0 0", dmg, pddfFlags);   // :1364
}
```

The damage zones (Engine, FuelTank, fenders, front, back) are mapped from memory points of the model (`dmgZone_engine`, `dmgZone_front` and so on, `P:\scripts\4_world\entities\vehicles\carscript.c:369-375`).

### Damage to the crew

`DamageCrew(float dmg)` (`P:\scripts\4_world\entities\vehicles\carscript.c:1374`): when `dmg` is above `GameConstants.CARS_CONTACT_DMG_KILLCREW` the crew member is killed (`:1383`); otherwise shock and health are worked out with `Math.InverseLerp` (`:1401`).

### `EEHitBy` on `Transport`

`Transport.EEHitBy` calls `SetEngineZoneReceivedHit(dmgZone == "Engine")` (`P:\scripts\3_game\vehicles\transport.c:144-152`). That flag is synced with `SetSynchDirty()`.

## Vanilla patterns

### `OnInput`: native physics, script only reads and writes

The standard pattern for a mod that changes driving behaviour:

```cpp
override void OnInput(float dt)
{
    super.OnInput(dt);         // let the base logic run
    // read state: GetThrottle(), GetSteering()
    // change it: SetThrottle(newVal), SetSteering(newVal)
}
```

### Fluids from script

```cpp
// Fill on a debug spawn (the OffroadHatchback and Boat_01 pattern):
float amount = GetFluidCapacity(CarFluid.FUEL);
Fill(CarFluid.FUEL, amount);

// Level check:
if (GetFluidFraction(CarFluid.FUEL) <= 0)
    EngineStop();

// Leak over time:
if (m_FuelTankHealth < GameConstants.DAMAGE_DAMAGED_VALUE)
    LeakFluid(CarFluid.FUEL);  // wrapper that calls Leak() with a rate (carscript.c:2098)
```

### Engine temperature (the `UniversalTemperatureSource` pattern)

Vanilla cars (OffroadHatchback, Truck_02, Van_01 and others) hold a `UniversalTemperatureSource` (`m_UTSource`, `P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:3`), create it in `EEInit` on the server or in single player only, update it in `EOnPostSimulate`, and switch it on and off in `OnEngineStart` and `OnEngineStop`. The client does not touch it.

### Getting in, start to finish

1. The player looks at the vehicle; the raycast hits a component of the model.
2. `ActionGetInTransport.ActionCondition` checks that `transport.CrewPositionIndex(componentIndex)` is 0 or more and that the seat is empty (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:45-69`).
3. In `Start()`: `action_data.m_Player.StartCommand_Vehicle(transport, crewIndex, seat)` creates a `HumanCommandVehicle` (`actiongetintransport.c:104`).
4. `AddActionJuncture` reserves the seat for the player with an inventory juncture (`actiongetintransport.c:138-158`).
5. To leave: `ActionGetOutTransport`. After a jump out, its `ApplyJumpOutDmg` calls `OnVehicleJumpOutServer` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:252-258`), which works out the damage from speed (`P:\scripts\4_world\entities\vehicles\carscript.c:951`).

## Gotchas

1. **`OnContact` does its work on the server only** (`P:\scripts\3_game\vehicles\transport.c:317`; `1.29:4_world\entities\vehicles\carscript.c:1456`). There is no collision callback for cars on the client.
2. **`EOnPostSimulate` runs on both**, but most of its logic is behind `g_Game.IsServer()`.
3. **`Random`, `RandomRange` and `Random01` only inside `EOnSimulate` or `EOnPostSimulate`** (`P:\scripts\3_game\vehicles\transport.c:280-296`). Using them elsewhere breaks determinism.
4. **`GetController()` is obsolete.** Use the methods on `Car` (`SetThrottle`, `SetSteering` and so on).
5. **`IsServerOrOwner()`** (`P:\scripts\4_world\entities\vehicles\carscript.c:2592`). With the new networking (`NetworkMoveStrategy.PHYSICS`) the owner, the client that drives, also runs the simulation. With the classic networking only the server does.
6. **`dBodyApplyImpulseAt` in `ActionPushCar`** (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:52`). It uses the global `dBody` API, not `Transport`'s; the result spreads because the physics body exists on the server and `Transport` replicates it.
7. **`Synchronize()`.** Call it by hand when the vehicle goes from standing to active, to force a snapshot.
8. **The contact data uses `momentumDelta` as its "impulse".** The main calculation does not use `data.Impulse` from the `Contact`; it uses `GetMomentum() - m_MomentumPrevTick`.
9. **`FEATURE_NETWORK_RECONCILIATION` is defined** (`P:\scripts\1_core\defines.c:64`). `P:\scripts\3_game\vehicles\transport.c:65-69` shows that without it `Transport` would inherit straight from `EntityAI`.
10. **Cars with no driver.** `SetBrakesActivateWithoutDriver(true)` (`P:\scripts\3_game\vehicles\car.c:212`). When the driver loses control, `OnUpdate` applies a brake of 0.5.

## What does not exist

- **Setting up a `SimulationModule` from script.** It is config only (`CfgVehicles`). Enforce Script has no way to create wheel or axle physics parameters.
- **A custom `Transport` with no model that has a simulation module.** It needs a P3D with the right geometry (collision, LODs, memory points) registered in config.
- **`GetCrewIndex()`.** Not under that name. The calls are `CrewPositionIndex(int componentIdx)` (`P:\scripts\3_game\vehicles\transport.c:179`) and `CrewMemberIndex(Human player)` (`:183`).
- **An `EFluidType` enum for vehicles.** Not under that name. It is `CarFluid` (`P:\scripts\3_game\vehicles\car.c:18`) and `BoatFluid` (`P:\scripts\3_game\vehicles\boat.c:13`).
- **`EOnSimulate` on `CarScript`.** No car script class overrides it; the simulation is native. (`BoatScript` does, as noted above.)
- **A `HelicopterScript` with full physics.** `HelicopterScript.EOnPostSimulate` is empty (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:11-13`). The flight is native in `HelicopterAuto`.
- **Doubt that `BoatScript` exists.** It does: `class BoatScript : Boat` (`P:\scripts\4_world\entities\vehicles\boatscript.c:41`), and `Boat extends Transport` (`P:\scripts\3_game\vehicles\boat.c:28`).

## Worked case: a rolling stone item

### Why `Transport` replicates and the stone, an `ItemBase`, does not

`Transport extends Pawn`, and the engine gives every `Pawn` of this kind a continuous stream of `TransportOwnerState` (world transform, linear velocity, angular velocity) to all proxies. `ItemBase` does not inherit from `Pawn`, so the engine creates no such stream.

A test in which the client sees the stone roll can be explained by:

- **Single player:** no network; one process sees everything.
- **Local multiplayer at low latency:** `EntityAI` gets a periodic position resync when it has moved enough. That resync is infrequent and carries no velocities, so the client interpolates badly or sees jumps. (Native behaviour, not visible in script and not checked on `P:\`.)

### The real options for the stone

1. **Option A, the native throw path (`ThrowPhysically`, `DYNAMICITEM`).** Use the drop and throw physics the engine already runs on the server and the owner client. See `engine-deep-dive.md` section 2.9.
2. **Option B, position by RPC.** On each server tick read `GetPosition()` and `GetVelocity()` from the body and send an RPC so the client moves the stone itself (`SetPosition` plus the global `SetVelocity`). Costly but correct.
3. **Option C, inherit from `Transport`.** A class that inherits from `Transport` (not `ItemBase`), registered with a minimal simulation module in config, would get the sync for free. The cost is that `Transport` needs a `CfgVehicles` config with a `SimulationModule` and a fitting P3D. Risky without a full simulation module.
4. **Option D, measure the native resync.** Confirm in a test whether the engine resyncs an `EntityAI` at an interval the gameplay tolerates. If it is about 100 ms it may be good enough for a first version.

### `ActionPushCar` as the model for a push action

`ActionPushCarCB.ApplyForce` uses exactly the pattern a push action on the stone should use, `dBodyApplyImpulseAt` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:52`):

```cpp
dBodyApplyImpulseAt(car, impulse, car.ModelToWorld(car.GetEnginePos()));
```

Adapted for the stone:

```cpp
dBodyApplyImpulseAt(stone, impulse, stone.GetPosition());
```

The impulse is body mass times force times a coefficient times the direction. The action runs on the server, so the push moves the body there. The client sees the effect only if the object is synced (the known problem above).

### `OnContact` as the model for the stone's `EOnContact`

`Transport.OnContact`, which does its work on the server only, is the same pattern as an `ItemBase`'s `EOnContact`. The difference is that `Transport` gets a callback with a zone name, while for an `ItemBase` the pattern is `EOnContact(IEntity other, Contact data)`. The damage design (gather in a cache, process in the post simulate step) can be reused for the stone if it should damage players on impact.

## Vanilla files

Vanilla files this reference cites, under `P:\scripts\`:

| File | What it holds |
|---|---|
| `3_game\vehicles\transport.c` | `Transport` base class: crew, forces, the net sync state types |
| `3_game\vehicles\car.c` | The `Car` native API: steering, throttle, brake, gears, fluids |
| `3_game\vehicles\boat.c` | The `Boat` native API |
| `3_game\vehicles\helicopter.c` | `Helicopter` and `HelicopterAuto` (native auto hover) |
| `3_game\entities\pawn.c` | `Pawn`, `PawnOwnerState`, `PawnMove`, the `NetworkMoveStrategy` enum |
| `1_core\defines.c` | `FEATURE_NETWORK_RECONCILIATION` |
| `4_world\entities\vehicles\carscript.c` | All of `CarScript`: contact, fluids, lights, `EOnPostSimulate` |
| `4_world\entities\vehicles\boatscript.c` | `BoatScript` |
| `4_world\entities\vehicles\helicopterscript.c` | `HelicopterScript`, with its empty `EOnPostSimulate` |
| `4_world\entities\vehicles\inheritedcars\offroadhatchback.c` | The temperature source pattern, `GetSeatAnimationType` |
| `4_world\entities\vehicles\inheritedcars\truck_02.c` | A truck with temperature |
| `4_world\entities\vehicles\inheritedboats\boat_01.c` | `Boat_01`: fluids, seats |
| `4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c` | Getting in |
| `4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c` | Getting out, the jump out damage call |
| `4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c` | `dBodyApplyImpulseAt` as a pattern |

The `SimulationModule` keys are cited from `P:\DZ\vehicles\wheeled\config.cpp`.
