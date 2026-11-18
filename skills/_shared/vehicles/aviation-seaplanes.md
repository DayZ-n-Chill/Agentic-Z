# Seaplanes and amphibious aircraft

How a scripted plane floats with a `Buoyancy` class, which script layer adds water takeoff and steering on top, which numbers suit a large and a small airframe, and how the spray effects are attached and cleaned up.

The pattern comes from LM_Planes (Workshop `3730564764`), whose scripts are the source; it is mod behaviour, not vanilla, except where a `P:\` line is cited. The base flight model is in `aviation-aerodynamics.md`.

## Floating: the Buoyancy class

Vanilla declares `class Buoyancy` on `BoatScript` with six keys: `linearDampeningCoefficient`, `angularDampeningCoefficient`, `linearDragCoefficient`, `quadraticDragCoefficient`, `falloffPower` and `sinkRate` (`P:\DZ\vehicles\water\config.cpp:32`).

LM_Planes puts the block on its `CarScript` aircraft with almost no drag, so the aircraft floats and moves freely without the water holding it back:

```cpp
class MyMod_Seaplane: CarScript
{
    class Buoyancy
    {
        linearDampeningCoefficient = 1e-08;
        angularDampeningCoefficient = 1e-08;
        linearDragCoefficient = 1e-08;
        quadraticDragCoefficient = 1e-08;
        waterResistanceCoef = 1e-08;
        waterAngularDampingCoef = 1e-08;
        falloffPower = 1e-06;
        sinkRate = 0.01;
    };
};
```

The mod uses it on the Catalina (flying boat), the Tigermoth MK3 (seaplane) and the Patty Wagon (amphibious car). `waterResistanceCoef` and `waterAngularDampingCoef` appear in no vanilla config under `P:\DZ\vehicles\` or in `P:\bin\config.cpp`, so whether the engine reads them is unverified. That the car simulation honours `class Buoyancy` on a `CarScript` child is the mod's claim, not yet checked in game.

## Water handling in script

The config makes the aircraft float. `ApplyWaterPhysics(dt)` adds the active part: damping bounce, steering on water, and climbing onto the step for takeoff. It runs after the base aerodynamics, only on water and in `PLANE_MODE_AIR`:

```c
override protected void ApplyFlightPhysics(float dt)
{
    UpdateWaterDetection(dt);      // refresh m_IsOnWater
    super.ApplyFlightPhysics(dt);  // base aerodynamics first
    if (m_IsOnWater && m_PlaneMode == PlaneMode.PLANE_MODE_AIR)
        ApplyWaterPhysics(dt);     // then the water layer
}
```

This is also how to add any extra layer (ground effect, gusts) without rewriting the base. The same class overrides `CalculateStallFactor` to return 0 while on water, so taxiing never sounds the stall warning.

On water is checked every 0.25 s (`WATER_CHECK_INTERVAL`) by the mod's `CheckIsOnWater()`, which uses vanilla calls: `SurfaceIsSea(x, z)` for the sea, `SurfaceIsPond(x, z)` for fresh water, and `SurfaceGetSeaLevel()` for the absolute height of the water (`P:\scripts\3_game\global\game.c:1196`, `:1197` and `:1191`). The same calls serve any amphibious vehicle.

`ApplyWaterPhysics` works in five steps, all scaled by a height fade: `1 - heightAboveSea / maxHeight`, clamped to 0 to 1, then squared.

1. Bounce: when vertical speed is over 0.5 m/s, push down by vertical speed times a negative coefficient, clamped.
2. Rudder: when rudder input is over 0.05, add a yaw torque about `up`, since the rudder steers on water too.
3. Water thrust (small template only): above 30 percent throttle, push forward, because an amphibious car needs direct drive in water.
4. Step takeoff: above the step start speed and 40 percent throttle, a PD controller pitches the nose towards a target angle that grows with speed up to 55 km/h, adds lift to break free of the surface, and adds a forward push. The torque is clamped.
5. Side drag: push against sideways speed so the hull tracks straight.

Forces go through `SafeApplyForce` and `SafeApplyTorque` (see `aviation-aerodynamics.md`) and only when their squared length is over 0.01.

## Large and small templates

LM_Planes ships two sets of numbers. Use the large one for big planes the size of the Catalina or DC-3, and the small one for amphibious cars and small seaplanes.

| Parameter | Large (Catalina) | Small (Patty Wagon, Tigermoth MK3) |
|---|---|---|
| `maxHeight`, fade height above the sea | 2.0 m | 1.5 m |
| Bounce coefficient and clamp | -4300, clamp -14000 | -2400, clamp -8000 |
| Rudder torque multiplier | 2800 | 1200 |
| Water thrust | none | 1800 times throttle times height fade |
| Step start speed | 25 km/h | 15 km/h |
| Target pitch | 8 degrees | 10 degrees |
| PD gains `kP`, `kD` | 1900, 950 | 800, 400 |
| Step torque clamp | plus or minus 12000 | plus or minus 5000 |
| Escape lift | 6000 | 2500 |
| Forward push during the step | 3500 | 1500 |
| Side drag coefficient | 480 | 200 |

## Spray effects on memory points

The model needs four memory points for the spray emitters: `ptcfxfront`, `ptcfxback`, `ptcfxside1` and `ptcfxside2`. Create the effects on clients only, and check each point first with `MemoryPointExists` (`P:\scripts\3_game\entities\object.c:454`):

```c
protected void InitWaterEffects()
{
    if (m_WaterEffectsInitialized) return;
    if (!GetGame().IsClient() && GetGame().IsMultiplayer()) return; // a server draws nothing
    if (MemoryPointExists("ptcfxfront"))
    {
        m_WaterEffectFront = new EffectSeaplaneWaterFront();
        m_WaterEffectFront.AttachTo(this, GetMemoryPointPos("ptcfxfront"));
    }
    // the same for ptcfxback, ptcfxside1 and ptcfxside2
    m_WaterEffectsInitialized = true;
}
```

The `EffectSeaplaneWater*` classes are the mod's own and are described in `aviation-effects-and-lights.md`; the particle file formats are in `/dayz-particles`.

## Clean up effects on every path

An entity that holds `ScriptedEffect` references leaks them unless every way it can go away destroys them. Call the cleanup from all three places:

```c
override void EEDelete(EntityAI parent)
{
    CleanupWaterEffects();
    super.EEDelete(parent);
}

override void CleanupEffects()
{
    super.CleanupEffects();
    CleanupWaterEffects();
}

void ~MyMod_Seaplane()
{
    CleanupWaterEffects(); // the destructor catches the rest
}
```
