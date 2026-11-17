# Fixed-wing aircraft on CarScript: the LM_Planes layout

How the LM_Planes mod builds eight planes and one amphibious car on one base class: the config skeleton, `requiredAddons`, the `class defs` wrapper for sub-mods, the data driven base script class, custom Pawn replication, ground and air modes, `driverless` braking, the memory points and bones the model needs, the dashboard material toggle, sub-mod layout, cosmetic proxies, shared wheels and the mistakes seen in the mod.

Third-party mod behaviour (LM_Planes, Workshop `3730564764`), not vanilla. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code.

LM_Planes is the fixed-wing reference: 8 aircraft plus 1 amphibious car (Patty_Wagon) sharing one base class, `LlamaPlaneScript`. It inherits `CarScript`, overrides the physics in script and uses `class Buoyancy` for seaplanes. `CarScript` gives wheels, seats, sound integration and the damage system for free, which `EntityAI` or `Inventory_Base` would not. The vanilla contracts this leans on, and the traps, are in `skills/_shared/vehicles/aviation-carscript-base.md`.

## Architecture

### The fundamental hack

Aviation inherits from `CarScript` (the ground vehicle base). Vanilla ships no flyable aircraft and no fixed-wing class, so:

```cpp
// config.cpp per-aircraft
class LM_Tigermoth: CarScript
{
    scope = 2;
    model = "LM_Planes\LM_Tigermoth\LM_Tigermoth.p3d";
    weight = 1000000;             // Very high for plane stability
    fuelCapacity = 60;
    fuelConsumption = 15;
    animPhysDetachSpeed = 250;
    attachments[] = {"CarBattery","Reflector_1_1","Reflector_2_1","CarRadiator","SparkPlug",...wheels...};
    class SimulationModule: SimulationModule { /* full ground vehicle physics — overridden by scripts */ };
    // ... AnimationSources, DamageSystem, GUIInventoryAttachmentsProps, Sounds
};
```

The plane has 4 wheels (front/back left/right) for ground taxiing and a `SimulationModule` with full ground-vehicle physics — but actual flight physics is applied in scripts on top of the engine, not via config. See `ApplyFlightPhysics(dt)` in `aerodynamics-and-flight-physics.md`.

### Vestigial config values

When reusing `CarScript`, `Engine` block values that don't affect flight (because scripts take over) can be left as stubs:
- `rpmRedline = 80000` (real engines: 6000-8000) — irrelevant for flight, kept to satisfy config validator
- `torqueCurve[] = {600,0,990,65,...}` — only matters for ground mode

This is acceptable: a script-driven plane doesn't read these at runtime. Don't waste time tuning them.

### requiredAddons combo

```cpp
class CfgPatches {
    class LM_Tigermoth {
        requiredAddons[] = {"DZ_Vehicles_Parts","DZ_Data","DZ_Vehicles_Wheeled","DZ_Vehicles_Water","LM_Planes"};
    };
};
```

LM_Planes lists **both `DZ_Vehicles_Wheeled` and `DZ_Vehicles_Water`** in every aircraft: Wheeled for the `CarScript` parent and landing gear, Water for the flying boat and seaplane buoyancy. Sub-aircraft mods also require their parent (`LM_Planes`). Vanilla declares the two addons at `P:\DZ\vehicles\wheeled\config.cpp:3` (`DZ_Vehicles_Wheeled`, where `class CarScript: Car` sits at line 236) and `P:\DZ\vehicles\water\config.cpp:3` (`DZ_Vehicles_Water`, where `class Buoyancy` sits at line 32).

### `class defs` wrapper for sub-mods

Root mod loads `gameScriptModule`/`worldScriptModule` directly under `CfgMods.<Mod>`:

```cpp
class CfgMods {
    class LM_Planes {
        ...
        class gameScriptModule { files[] = {"LM_Planes/scripts/3_Game"}; };
        class worldScriptModule { files[] = {"LM_Planes/scripts/4_World"}; };
    };
};
```

Per-aircraft sub-mods wrap them under `class defs`:

```cpp
class CfgMods {
    class LM_Tigermoth {
        ...
        class defs {
            class gameScriptModule { ...; files[] = {"LM_Planes/scripts/3_Game"}; };
            class worldScriptModule { ...; files[] = {"LM_Planes/scripts/4_World"}; };
        };
    };
};
```

Some sub-mods only load `worldScriptModule` (Cessna180, Spitfire). The wrapper is required when the mod is a child of another mod's namespace.

### Base script class (data-driven config-in-script)

```cpp
class LlamaPlaneScript extends CarScript
{
    // ~60 protected Get* methods for ALL tunable parameters
    protected float GetWingArea()              { return 22.0; }
    protected float GetWingSpan()              { return 8.9; }
    protected float GetWingAR()                { return 5.2; }
    protected float GetEngineMaxPower()        { return 3000.0; }
    protected float GetClCoef3()               { return -0.00038; }
    // ... etc, 60+ methods covering aerodynamics, control, stall, dampening, sound, lights
};

class LM_Tigermoth extends LlamaPlaneScript
{
    // ONLY override Get* methods — zero new logic per aircraft
    override protected float GetWingArea()     { return 22.0; }
    override protected float GetEngineMaxPower() { return 3100.0; }
    override protected float GetStallBaseSpeedKmph() { return 62.0; }
    // ... 50+ overrides
}
```

Per-aircraft files are essentially configs-as-code: parameter sets, not new logic. This makes adding aircraft trivial: copy the override block, tune values.

### Custom Pawn replication

DayZ networking for player-controlled entities uses Pawn classes. Aviation needs custom state:

```cpp
class PlaneOwnerState extends CarScriptOwnerState
{
    int m_iFlightMode;             // 0=ground, 1=air
    float m_fThrottleSmooth;
    float m_fPitchSmooth;
    float m_fRollSmooth;
    float m_fRudderSmooth;
    float m_fStallFactor;
    
    protected override event void Write(PawnStateWriter ctx) { /* serialize */ }
    protected override event void Read(PawnStateReader ctx) { /* deserialize */ }
};

class PlaneMove extends CarScriptMove
{
    float m_fPitch;
    float m_fRoll;
    float m_fRudder;
    float m_fThrottle;
    int m_iToggleFlightMode;
    
    protected override event void Write(PawnMoveWriter ctx, PawnMove prev) {}
    protected override event void Read(PawnMoveReader ctx, PawnMove prev) {}
};

// In LlamaPlaneScript:
protected override event typename GetOwnerStateType() { return PlaneOwnerState; }
protected override event typename GetMoveType()       { return PlaneMove; }
protected override event void ObtainMove(PawnMove pMove)  { /* client captures inputs */ }
protected override event void ConsumeMove(PawnMove pMove) { /* server applies inputs */ }
protected override event bool ReplayMove(PawnMove pMove)  { /* client-side prediction replay */ }
protected override event void SimulateMove(PawnMove pMove) { /* apply forces */ }
protected override event void ObtainState(PawnOwnerState pState)    { /* snapshot */ }
protected override event void RewindState(PawnOwnerState pState, PawnMove pMove, inout NetworkRewindType pRewindType) { /* rollback */ }
```

This gives you client-side prediction with server reconciliation — essential for fly-able aviation that doesn't feel laggy. The vanilla classes and events behind it, with their lines, are in `skills/_shared/vehicles/aviation-networking.md`.

### Two flight modes

```cpp
protected int m_PlaneMode = 0;  // 0=GROUND, 1=AIR
protected float m_PlaneModeSwapCooldown;

protected void Server_ToggleMode()
{
    // Cooldown prevents spam
    if (m_PlaneModeSwapCooldown > 0) return;
    m_PlaneMode = 1 - m_PlaneMode;
    m_PlaneModeSwapCooldown = 1.0;
}
```

`PLANE_MODE_AIR` enables `ApplyFlightPhysics()`. `PLANE_MODE_GROUND` lets `CarScript` handle taxiing normally. Pilot toggles with a bound action (default G). Critical for proper landing/takeoff transitions.

### `driverless` design pattern

```cpp
class SimulationModule {
    class Brake {
        driverless = 0.1;  // Sport aircraft: rolls when pilot exits
        // OR
        driverless = 1.0;  // Heavy aircraft: locks fully (no rolling)
    };
};
```

LM_Planes splits them: `0.1` for Cessna180, Spitfire, StuntPlane (sport feel). `1.0` for Catalina, DC-3, Patty_Wagon, Tigermoth, Z37_Bumblebee (utility/heavy feel). Pick based on aircraft character. Vanilla cars use `driverless=0.1` (`P:\DZ\vehicles\wheeled\config.cpp:460`).

## Memory points (for the model artist)

Aircraft p3d must contain these memory points; scripts will read them via `GetMemoryPointSafe(name, fallback)`:

| Memory point | Purpose |
|---|---|
| `axis_back`, `axis_front`, `axis_left`, `axis_right`, `axis_floor`, `axis_roof` | Aircraft orientation reference vectors |
| `axis_elevator_left`, `axis_elevator_right` | Elevator hinge axes for moment-arm calc |
| `axis_flap_left`, `axis_flap_right` | Aileron hinge axes |
| `axis_rudder` | Rudder hinge axis |
| `axis_thruster` | **thrust application point** — engine force is applied here |
| `wing_left`, `wing_right` | Wing tip positions (for wing span calc + nav lights fallback) |
| `light_wing_left`, `light_wing_right`, `light_wing_tail` | Navigation light spawn positions (red/green/white) |
| `pos_driver`, `pos_codriver`, `pos_cargo1-3` + `_dir` variants | Crew entry positions + facing direction |
| `dmgZone_*` | Damage zone hit centers (matches DamageSystem in config) |

Catalina expands with `light_left`, `light_right`, `light_1_1`, `light_2_1`, `light_dashboard`, `light_reverse` for flying-boat exterior lights.

`GetMemoryPointSafe(name, fallbackVec)` returns the position or `fallbackVec` if not found — keeps script robust against missing memory points.

## Selection names (skeleton bones in model.cfg)

Top-level bones registered in `CfgSkeletons.<Aircraft>_skeleton.SkeletonBones[]` (no parent unless wheel chain):

**Flight controls** (script-driven via `SetAnimationPhase`):
- `elevator_1_1`, `elevator_2_1` (paired elevators)
- `aileron_1_1`, `aileron_2_1`
- `rudder_1_1`
- `gear_1_1` (landing gear retract)

**Rotors** (propeller animation):
- `rotor_1_1`, `rotor_center` (main prop)
- `rotor_1_1_blur` (visual blur when spinning)
- `rotor_1_2`, `rotor_center2` (DC-3 second engine) or `rotor_2_1`, `rotor_center_2` (Catalina) — naming inconsistent
- Single-engine planes: only `rotor_1_1` + `rotor_center`

**Instruments**:
- `dial_compass`, `dial_horizon_bank`, `dial_horizon_pitch`
- `dial_altitude`, `dial_volt`
- `dial_rpm`, `dial_fuel`, `dial_temp`, `dial_speed` (vanilla-driven)

**Other**:
- `engine`, `radiator`, `refill`
- `drivewheel`, `drivewheel_1`, `drivewheel_2` (cockpit yokes)
- `crewdriver`, `crewcodriver`, `seat_driver`, `seat_codriver`, `seat_cargo1-3`
- `propeller` (selection, not the rotor bone)

**Wheel chain** (parented):
- `damper_susp_X_Y` (top, no parent) → `damper_X_Y` (parent: damper_susp) → `wheel_X_Y` (parent: damper) → `wheel_X_Y_steering` (parent: wheel)
- Rear/tail wheel: `damper_2_2` has no `damper_susp` parent (simpler chain)

## Visuals and materials

### Toggle rvmat pattern (dashboard on/off)

```
Controls.rvmat (lights off)        Controls_on.rvmat (lights on)
forcedDiffuse = {0,0,0,1}     →   forcedDiffuse = {0.1,0.1,0.1,1}
Stage5 SMDI = controls_SMDI       Stage5 SMDI = controls_on_SMDI
Everything else identical.
```

Only 2 things differ between off/on. Cross-aircraft material sharing (Catalina referencing `LM_Tigermoth/data/Controls.rvmat`) — DRY across aircraft (verified in p3d binary string references).

## Sub-mod layout, proxies and shared wheels

### Sub-mod parent and child layout

Root mod (`LM_Planes`) has `CfgPatches.units[] = {}` (empty — no entities directly). Only registers `Inputs.xml` + script modules. Per-aircraft sub-mods (`LM_Tigermoth`, `LM_Catalina`, etc.) declare their own `units[]` and require `LM_Planes` parent.

**One-way dependency**: child requires parent, parent doesn't require children. Lets you enable/disable per-aircraft sub-mods independently without breaking root. Critical pattern for large modular mods.

### Cosmetic-only proxies (no script logic needed)

DC-3 has `proxy/LM_DC_3_Rear_seats.p3d` (165 KB) — purely decorative cockpit seats visible in proxy LOD. No memory points `pos_cargo*`, no selections `seat_cargo*`. `CfgVehicles.LM_DC_3.class Crew` declares only Driver + CoDriver (no cargo).

Z37_Bumblebee has `proxy/LM_Z37_Bumblebee_door_1_1.p3d` + `door_2_1.p3d` — handled by **vanilla DayZ door attachment system** (CarDoor base + attachments[] in config + class DamageZones.Doors). No script logic for doors. Engine handles visibility on attach/detach.

**Pattern**: use vanilla DayZ systems when possible. Don't write scripts for doors/seats if config + proxies suffice.

### Family wheel sharing (variant reuse)

Tigermoth family (`LM_Tigermoth` + `LM_Tigermoth_MK2` + `LM_Tigermoth_MK3`) all use the same wheel inventory class:

```cpp
// LM_Tigermoth_MK2.c OnDebugSpawn:
GetInventory().CreateInInventory("LM_Tigermoth_wheel_front");  // NOT MK2_wheel_*
GetInventory().CreateInInventory("LM_Tigermoth_wheel_back");
```

Only the variant aircraft body changes; wheels are shared. Reduces config + asset duplication. Pattern for vehicle families.

## Mistakes seen in the mod

1. **Inventory slot case inconsistency** (`LM_Tigermoth_Wheel_1_1` capital W defined, but referenced as `LM_Tigermoth_wheel_1_1` lowercase w in `class Wheels`). Engine resolves it but bug-magnet. Be consistent.
2. **Rotor source = wheelfrontright** — visual prop tied to wheel, not engine RPM. Works as a hack but doesn't reflect actual engine behavior. Script-overriding it is the proper fix.
3. **rpmRedline=80000** in Engine — vestigial CarScript values left because they don't matter when scripts control physics. Don't bother tuning these for aviation.
4. **i18n placeholders** — Stringtable.csv with 13 locales all identical English. Pragmatic shortcut, not bad practice per se, but worth knowing when reading the mod's stringtable.
