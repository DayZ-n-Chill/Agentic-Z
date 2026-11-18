# Fixed-wing aircraft on one base class

How LM_Planes builds seven planes and one amphibious car on one `CarScript` base: the config skeleton, `requiredAddons`, the `class defs` wrapper for sub-mods, the data driven base class, its Pawn replication, ground and air modes, parking brakes, sub-mod layout and shared parts.

LM_Planes (Workshop `3730564764`) is the fixed-wing reference, and its configs and scripts are the source here; it is mod practice, not vanilla, except where a `P:\` line is cited. Learn the pattern from it and write the mod's own code. The vanilla behaviour this leans on is in `aviation-carscript-base.md`; what the model has to contain is in `aviation-plane-model.md`.

## The fleet and its base

Seven planes (Tigermoth, Cessna180, Catalina, Spitfire, DC-3, StuntPlane, Z37_Bumblebee) and one amphibious car (Patty_Wagon) share one script class, `LlamaPlaneScript`, which inherits `CarScript`. `CarScript` brings wheels, seats, sound and the damage system, which `EntityAI` or `Inventory_Base` would not. Each aircraft is a car in config:

```cpp
class MyMod_Plane: CarScript
{
    scope = 2;
    model = "MyMod\Plane\MyMod_Plane.p3d";
    weight = 1000000;          // very high, for stability
    fuelCapacity = 60;
    fuelConsumption = 15;
    animPhysDetachSpeed = 250;
    attachments[] = {"CarBattery","Reflector_1_1","Reflector_2_1","CarRadiator","SparkPlug" /* and the wheels */};
    class SimulationModule: SimulationModule { /* full ground physics, used for taxiing */ };
    // AnimationSources, DamageSystem, GUIInventoryAttachmentsProps, Sounds
};
```

Four wheels carry it on the ground through the `SimulationModule`; the flight physics is added in script on top (`ApplyFlightPhysics(dt)`, `aviation-aerodynamics.md`).

Engine values that only matter on the ground can stay as placeholders, since script takes over in the air: LM_Planes ships `rpmRedline = 80000` (a real engine runs 6000 to 8000) and a ground only `torqueCurve[] = {600,0,990,65,...}`. Do not spend time tuning them.

## Addons to require

```cpp
class CfgPatches
{
    class MyMod_Plane
    {
        requiredAddons[] = {"DZ_Vehicles_Parts","DZ_Data","DZ_Vehicles_Wheeled","DZ_Vehicles_Water","MyMod_Planes"};
    };
};
```

Every LM_Planes aircraft requires both `DZ_Vehicles_Wheeled`, for the `CarScript` parent and the landing gear, and `DZ_Vehicles_Water`, for the buoyancy of the flying boat and the seaplane. Vanilla declares them at `P:\DZ\vehicles\wheeled\config.cpp:3` (where `class CarScript: Car` sits at `:236`) and `P:\DZ\vehicles\water\config.cpp:3` (where `class Buoyancy` sits at `:32`). Each aircraft sub-mod also requires the root mod.

## Script modules for sub-mods

The root mod puts its script modules straight under `CfgMods`:

```cpp
class CfgMods
{
    class MyMod_Planes
    {
        class gameScriptModule { files[] = {"MyMod_Planes/scripts/3_Game"}; };
        class worldScriptModule { files[] = {"MyMod_Planes/scripts/4_World"}; };
    };
};
```

Each aircraft sub-mod wraps the same modules in `class defs`, pointing at the root mod's script folders:

```cpp
class CfgMods
{
    class MyMod_Plane
    {
        class defs
        {
            class gameScriptModule { files[] = {"MyMod_Planes/scripts/3_Game"}; };
            class worldScriptModule { files[] = {"MyMod_Planes/scripts/4_World"}; };
        };
    };
};
```

Some sub-mods load only `worldScriptModule` (Cessna180, Spitfire).

## A data driven base class

`LlamaPlaneScript` exposes about 60 protected `Get*` methods for every tunable value: aerodynamics, control, stall, damping, sound and lights. Each aircraft overrides values only and adds no logic:

```c
class MyMod_PlaneBase extends CarScript
{
    protected float GetWingArea()       { return 22.0; }
    protected float GetWingSpan()       { return 8.9; }
    protected float GetWingAR()         { return 5.2; }
    protected float GetEngineMaxPower() { return 3000.0; }
    protected float GetClCoef3()        { return -0.00038; }
};

class MyMod_Biplane extends MyMod_PlaneBase
{
    override protected float GetEngineMaxPower()     { return 3100.0; }
    override protected float GetStallBaseSpeedKmph() { return 62.0; }
};
```

A new aircraft is a copied override block with new numbers. The values LM_Planes uses are in `aviation-aircraft-presets.md`.

## Pawn replication

The base class carries its own owner state and move, so the pilot's client predicts and the server reconciles:

```c
class MyMod_PlaneOwnerState extends CarScriptOwnerState
{
    int m_iFlightMode; // 0 ground, 1 air
    float m_fThrottleSmooth;
    float m_fPitchSmooth;
    float m_fRollSmooth;
    float m_fRudderSmooth;
    float m_fStallFactor;
    protected override event void Write(PawnStateWriter ctx) { super.Write(ctx); }
    protected override event void Read(PawnStateReader ctx) { super.Read(ctx); }
};

class MyMod_PlaneMove extends CarScriptMove
{
    float m_fPitch;
    float m_fRoll;
    float m_fRudder;
    float m_fThrottle;
    int m_iToggleFlightMode;
    protected override event void Write(PawnMoveWriter ctx, PawnMove prev) { super.Write(ctx, prev); }
    protected override event void Read(PawnMoveReader ctx, PawnMove prev) { super.Read(ctx, prev); }
};
```

The aircraft returns them from `GetOwnerStateType()` and `GetMoveType()`, and fills the events: `ObtainMove` captures input on the client, `ConsumeMove` applies it on the server, `ReplayMove` replays it for prediction, `SimulateMove` applies forces, `ObtainState` takes a snapshot, and `RewindState` rolls back. The vanilla classes and events behind them, with their lines, are in `aviation-networking.md`.

## Ground and air modes

```c
protected int m_PlaneMode = 0; // 0 ground, 1 air
protected float m_PlaneModeSwapCooldown;

protected void Server_ToggleMode()
{
    if (m_PlaneModeSwapCooldown > 0) return; // stops spamming
    m_PlaneMode = 1 - m_PlaneMode;
    m_PlaneModeSwapCooldown = 1.0;
}
```

`PLANE_MODE_AIR` turns on `ApplyFlightPhysics()`; `PLANE_MODE_GROUND` leaves taxiing to `CarScript`. The pilot switches with a bound key, G by default. Takeoff and landing depend on this switch.

## Parking brake when the pilot leaves

`driverless` in `class Brake` of the `SimulationModule` sets how hard the brake holds with no driver. Vanilla's `RearDrive` template uses `driverless=0.1` (`P:\DZ\vehicles\wheeled\config.cpp:460`). LM_Planes uses `0.1`, so the plane rolls, on the Cessna180, Spitfire and StuntPlane, and `1.0`, fully locked, on the Catalina, DC-3, Patty_Wagon, Tigermoth and Z37_Bumblebee. Choose by the aircraft: light and sporty, or heavy and utility.

## Sub-mods and shared parts

- The root mod has `CfgPatches.units[] = {}`: it adds no entity, only `Inputs.xml` and the script modules. Each aircraft sub-mod declares its own `units[]` and requires the root. The dependency runs one way, so any aircraft can be switched off without breaking the root.
- Use vanilla systems where config and proxies are enough. The DC-3's rear seats are a decorative proxy, `proxy/LM_DC_3_Rear_seats.p3d`, with no `pos_cargo*` memory points and no `seat_cargo*` selections; its `class Crew` lists only the driver and co-driver. The Z37's doors, `proxy/LM_Z37_Bumblebee_door_1_1.p3d` and `door_2_1.p3d`, use the vanilla door system (a `CarDoor` child, `attachments[]` and a `Doors` damage zone) with no script.
- A family of variants shares one set of wheel items. The Tigermoth MK2 and MK3 spawn the base wheels in `OnDebugSpawn`, `CreateInInventory("LM_Tigermoth_wheel_front")` and `"LM_Tigermoth_wheel_back"`, not variant wheels. Only the body changes.

## Mistakes in the mod to avoid

- The slot is defined as `LM_Tigermoth_Wheel_1_1` but named `LM_Tigermoth_wheel_1_1` in `class Wheels`. The engine resolves it, but keep the case the same.
- The propeller turns with `wheelfrontright`, not the engine (`aviation-animation-and-modelcfg.md`). Drive it from script if it should follow the engine.
- `Stringtable.csv` has 13 language columns that all hold the same English text. Not wrong, but know it when you read the mod's stringtable.
