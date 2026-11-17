# Aerodynamics, flight physics and aircraft presets

Fixed-wing flight in script: lift, drag and stall, the ISA atmosphere helper, PID self levelling, forces guarded against NaN, seaplane `Buoyancy` and the active water physics on top of it, runtime optimisation, and the per-aircraft parameter presets (Cessna180, Spitfire, Catalina, Tigermoth family).

Third-party material: patterns read from the LM_Planes mod (Workshop `3730564764`, by Llama and Itspete-Here), whose files are not in this repo. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code.

## Aerodynamics & Physics (in script)

### Lift / drag coefficients (polynomial)

```cpp
protected float CalculateLiftCoefficient(float aoaDeg)
{
    float aoaRad = aoaDeg * Math.DEG2RAD;
    float cl = GetClCoef3() * aoaRad * aoaRad * aoaRad
             + GetClCoef2() * aoaRad * aoaRad
             + GetClCoef1() * aoaRad
             + GetClCoef0();
    // ... stall transition smoothing
    return Math.Clamp(cl, GetClMin(), GetClMax());
}

protected float CalculateInducedDrag(float cl)
{
    float denom = Math.PI * GetWingAR() * GetOswaldE();
    return cl * cl / denom;
}
```

Coefficients per aircraft (Tigermoth example): `ClCoef3=-0.00038, ClCoef2=0.00055, ClCoef1=0.095, ClCoef0=0.18, ClMax=1.35, ClMin=-0.95`. Wing AR ≈ 5.2, Oswald e ≈ 0.78.

### Force application

```cpp
protected void ApplyFlightPhysics(float dt)
{
    // Cached state per tick
    vector velocity = m_CachedVelocity;
    vector fwd      = m_CachedFwd;
    // ...
    
    float densityRatio      = StandardPlaneAtmosphere.GetDensityRatio(m_CachedPosition[1]);
    float performanceFactor = StandardPlaneAtmosphere.GetPerformanceFactor(m_CachedPosition[1]);
    
    float dynamicPressure = Math.Min(0.5 * densityRatio * 1.225 * speed * speed, 7500.0);
    float liftMagnitude   = dynamicPressure * GetWingArea() * cl * GetLiftForceScale();
    
    // Lift is perpendicular to velocity (in the plane of velocity & up)
    vector side    = velocityNorm * up;
    vector liftDir = side * velocityNorm;
    
    // Thrust along forward axis, scaled by throttle squared
    float thrustPower = GetEngineMaxPower() * (m_ThrottleSmooth * m_ThrottleSmooth)
                      * performanceFactor * propEff * lowSpeedBoost;
    
    SafeApplyForce(totalForce);
    SafeApplyTorque(totalTorque);
}
```

Key tricks:
- `dynamicPressure` clamped to 7500 max — prevents runaway forces at extreme speeds
- Thrust uses `throttle^2` curve for non-linear response (small throttle = little power, full throttle = max)
- `lowSpeedBoost` (lerp 1.25→1.0 over 0-25 m/s) prevents stall at takeoff

### Stall modeling with bank load factor

```cpp
protected float CalculateStallSpeed(float bankDeg)
{
    float bankRad = Math.AbsFloat(bankDeg) * Math.DEG2RAD;
    float cosBank = Math.Cos(bankRad);
    if (cosBank < 0.1) cosBank = 0.1;  // floor to prevent /0
    float loadFactor = 1.0 / cosBank;  // bank => more lift needed => higher stall speed
    return GetStallBaseSpeedKmph() * Math.Sqrt(loadFactor);
}

protected float CalculateStallFactor(float speedKmph, float aoaDeg, float bankDeg, float heightAGL)
{
    if (heightAGL < GetStallAltitudeMin()) return 0;  // No stall warning below 15m AGL (taxiing/landing)
    float criticalSpeed = CalculateStallSpeed(bankDeg);
    float speedMargin = speedKmph - criticalSpeed;
    // Combine speedMargin + AoA + bank to compute stall depth
}
```

Banked turns require more lift (load factor `1/cos(bank)`), so stall speed rises proportionally. This is the classic flight-physics relationship.

Stall warning sound triggers when `m_StallFactor >= GetStallKillThreshold()` (0.7), `EngineIsOn()`, and in `PLANE_MODE_AIR`. Sound is `<Aircraft>_Engine_StallWarn_SoundSet`.

### ISA-lite atmosphere (standalone utility)

```cpp
class StandardPlaneAtmosphere
{
    static const float SEA_LEVEL_PRESSURE     = 101325.0;
    static const float SEA_LEVEL_TEMPERATURE  = 288.15;
    static const float SEA_LEVEL_DENSITY      = 1.225;
    static const float TEMPERATURE_LAPSE_RATE = -0.0065;
    static const float GAS_CONSTANT           = 287.05;
    static const float GRAVITY                = 9.80665;
    static const float MAX_ALTITUDE           = 2000.0;
    static const float PRACTICAL_CEILING      = 1800.0;
    
    static float GetDensity(float altitude_m) { /* isothermal layer simplification */ }
    static float GetDensityRatio(float altitude_m) { return GetDensity(altitude_m) / SEA_LEVEL_DENSITY; }
    static float GetPerformanceFactor(float altitude_m) {
        // 1.0 below 1200m, lerp 1.0→0.6 between 1200m and 2000m
    }
};
```

Reusable for any aviation/vehicular mod that cares about altitude. ISA values are real physics constants.

### NaN-safe physics (mandatory)

When applying custom forces, NaN propagation will crash the engine. Defensive helpers:

```cpp
static float SanitizeFloat(float value, float fallback, float minVal, float maxVal)
{
    if (!IsFloatFinite(value)) return fallback;
    return Math.Clamp(value, minVal, maxVal);
}

static vector SanitizeVector(vector v, vector fallback) { /* check each component */ }

protected bool IsVectorFinite(vector v) { /* per-component NaN check */ }

protected vector ClampVectorMagnitude(vector v, float maxMag)
{
    float lenSq = v[0]*v[0] + v[1]*v[1] + v[2]*v[2];
    if (lenSq > maxMag * maxMag) {
        float len = v.Length();
        return v * (maxMag / len);
    }
    return v;
}

protected void SafeApplyForce(vector force)
{
    if (!IsVectorFinite(force)) return;  // Silent skip if NaN
    force = ClampVectorMagnitude(force, MAX_FORCE_MAGNITUDE);
    dBodyApplyForce(this, force);
}

protected void CheckPhysicsSanity()
{
    bool dirty = false;
    // If NaN detected over multiple frames, escalate
    if (m_NaNDetectionCount >= NAN_HARD_THRESHOLD) {
        ForcePhysicsReset();  // Zero velocity, zero angular vel
    }
}
```

Constants used: `MAX_SANE_SPEED=250` m/s, `MAX_SANE_ANGULAR_VEL=25`, `MAX_FORCE_MAGNITUDE=80000`, `MAX_TORQUE_MAGNITUDE=60000`, `NAN_RESET_THRESHOLD=1`, `NAN_HARD_THRESHOLD=10`.

**Without these guards, aviation will crash DayZ when edge cases hit.** Treat the pattern as mandatory. The body calls it wraps are vanilla: `dBodyApplyForce` at `P:\scripts\1_core\proto\enphysics.c:146` and `dBodyApplyTorque` at `:153`.

### PID auto-stabilization

```cpp
// Roll self-leveling when no roll input
float rollDeadband = GetRollDeadbandDeg() * Math.DEG2RAD;  // 3 deg
if (Math.AbsFloat(m_RollSmooth) < rollDeadband) {
    float autoKp = Math.Lerp(GetRollLevelKp() * 0.4, GetRollLevelKp(), controlEff);
    float autoKd = Math.Lerp(GetRollLevelKd() * 0.4, GetRollLevelKd(), controlEff);
    rollCmd = -bankErr * autoKp - rollRate * autoKd;
}

// Yaw auto-center (same pattern, Kp=0.22 Kd=0.25 deadband=2deg)

// Pitch level-flight stabilizer (kicks in above GetLevelFlightSpeedKmph 185)
// Fades by speed margin and pitch input

// Coordinated turn helper: when banking, auto-rudder = bankSign * turnNeed * 0.30 + sideslipCorrection
```

Self-leveling kicks in only when pilot has NO input on that axis (within deadband). Gains scale with `controlEffectiveness` (which scales with speed) — at low speed (just taxiing), stabilizer is weak; at flight speed, strong.

### Idle damping

```cpp
protected const float IDLE_DAMPING_FACTOR = 0.92;

protected void ApplyIdleDamping()
{
    vector angVel = dBodyGetAngularVelocity(this);
    float angMagSq = angVel[0]*angVel[0] + angVel[1]*angVel[1] + angVel[2]*angVel[2];
    if (angMagSq < threshold) return;  // anti-jitter
    vector dampedAng = angVel * IDLE_DAMPING_FACTOR;
    dBodySetAngularVelocity(this, dampedAng);
}
```

When no driver, multiply angular velocity by 0.92 per tick. Prevents planes spinning forever in mid-air when pilot bails out.

## Buoyancy for Seaplanes

```cpp
class LM_Catalina: CarScript {
    ...
    class Buoyancy
    {
        linearDampeningCoefficient   = 1e-08;
        angularDampeningCoefficient  = 1e-08;
        linearDragCoefficient        = 1e-08;
        quadraticDragCoefficient     = 1e-08;
        waterResistanceCoef          = 1e-08;
        waterAngularDampingCoef      = 1e-08;
        falloffPower                 = 1e-06;
        sinkRate                     = 0.01;
    };
}
```

All damping/drag coefficients at `1e-08` (basically zero), `falloffPower=1e-06`, `sinkRate=0.01`. This lets the aircraft float and move freely on water without engine drag. Applied to: Catalina (flying boat), Tigermoth_MK3 (seaplane variant), Patty_Wagon (amphibious car).

Vanilla declares `class Buoyancy` on `BoatScript` at `P:\DZ\vehicles\water\config.cpp:32` with six keys: `linearDampeningCoefficient`, `angularDampeningCoefficient`, `linearDragCoefficient`, `quadraticDragCoefficient`, `falloffPower` and `sinkRate`. The other two keys in the block above, `waterResistanceCoef` and `waterAngularDampingCoef`, appear in no vanilla config under `P:\DZ\vehicles\` or in `P:\bin\config.cpp`, so whether the engine reads them is unverified. Whether the car simulation honours `class Buoyancy` on a `CarScript` child at all is an LM_Planes result, not checked in game here.

## Optimization Patterns

### Animation phase delta cache

```cpp
protected float m_LastPitchAnim = -999.0;
protected const float ANIM_THRESHOLD = 0.015;

protected void UpdateControlSurfaceAnimations(float dt)
{
    float pitchPhase = m_PitchSmooth;
    if (Math.AbsFloat(pitchPhase - m_LastPitchAnim) >= ANIM_THRESHOLD) {
        SetAnimationPhase(ANIM_ELEVATOR_1, pitchPhase);
        SetAnimationPhase(ANIM_ELEVATOR_2, pitchPhase);
        m_LastPitchAnim = pitchPhase;
    }
}
```

Skip `SetAnimationPhase` engine call if value barely changed. Same pattern for roll, rudder, gear retract. Cuts engine calls dramatically.

### Adaptive update rates

| Update | Interval | Rationale |
|---|---|---|
| `UpdateAllDials` | 100ms (10Hz) | Human eye doesn't perceive faster dial updates |
| Network sync (active pilot) | 33ms (30Hz) | `GetSyncInterval()` |
| Network sync (idle) | 100ms (10Hz) | `GetSyncIntervalIdle()` |
| Flight physics tick | every `EOnSimulate` | Mandatory for stability |

### Input action caching

```cpp
protected UAInput m_InputPitchBack;
protected UAInput m_InputPitchFwd;
// ... 10 more

protected void CacheInputActions()
{
    m_InputPitchBack = GetUApi().GetInputByName("UALlamaPlanePitchBack");
    m_InputPitchFwd  = GetUApi().GetInputByName("UALlamaPlanePitchForward");
    // ...
    m_InputsCached = true;
}

override void OnInput(float dt)
{
    if (!m_InputsCached) CacheInputActions();
    float pitchInput = m_InputPitchFwd.LocalValue() - m_InputPitchBack.LocalValue();
    // ...
}
```

Lookup `UAInput` references once in `OnInit`, cache. Avoids string-keyed lookup every input frame.

## Detail Proxy LOD Pattern

Each aircraft can have `proxy/*_details.p3d` or `proxy/*_detail_<part>.p3d` files separate from the main `<Aircraft>.p3d`. Pattern:
- Main `.p3d`: low-poly fuselage shell, all LODs
- `proxy/*_detail_cockpit.p3d`, `proxy/*_detail_controls.p3d`, `proxy/*_detail_engine.p3d`: high-poly cockpit/engine details
- `proxy/*_door_X_Y.p3d`: detachable doors (Z37_Bumblebee)
- Main p3d references via `proxy:\path` (per-LOD proxy with version `.001`)

LOD-aware loading: high-poly proxies only load at close camera distance. Lets you have detailed cockpits without paying the polygon cost from far away.

## Multi-aircraft Variation Patterns Observed in Llama's Catalogue

| Aircraft | Variants | Buoyancy | Crew | Combat |
|---|---|---|---|---|
| Tigermoth | MK1 / MK2 (sport, no top wing) / MK3 (seaplane) | MK3 only | 2 (driver + codriver) | — |
| Cessna180 | base only | — | 2 | — |
| Catalina | base | yes (flying boat) | 5 (driver + codriver + 3 cargo) | Browning M2 .50 cal (visible) |
| Spitfire | MK1 (only) | — | 1 (fighter, solo) | Yes, `LM_Planes_Tracer` |
| DC-3 | base | — | 2 | — (twin engine) |
| StuntPlane | base | — | 2 | — |
| Z37_Bumblebee | base | — | 2 | — (agricultural) |
| Patty_Wagon | "plane" — actually a car | yes (amphibious) | 2 | car horn |

### Seaplane Water Physics (active, on top of Buoyancy class)

Buoyancy in config makes the aircraft float passively; **`ApplyWaterPhysics(dt)` in script adds active water-takeoff/water-driving dynamics**. Two templates observed (Catalina LARGE, Patty_Wagon+Tigermoth_MK3 SMALL):

```cpp
class LM_Catalina extends LlamaPlaneScript
{
    protected bool m_IsOnWater;
    protected float m_WaterCheckTimer;
    protected const float WATER_CHECK_INTERVAL = 0.25;
    protected ref EffectSeaplaneWaterFront m_WaterEffectFront;
    protected ref EffectSeaplaneWaterBack  m_WaterEffectBack;
    protected ref EffectSeaplaneWaterSide  m_WaterEffectSide1;
    protected ref EffectSeaplaneWaterSide  m_WaterEffectSide2;
    
    protected bool CheckIsOnWater()
    {
        float px = m_CachedPosition[0];
        float pz = m_CachedPosition[2];
        if (GetGame().SurfaceIsSea(px, pz)) return true;
        if (GetGame().SurfaceIsPond(px, pz)) return true;
        return false;
    }
    
    protected void ApplyWaterPhysics(float dt)
    {
        float seaLevel = GetGame().SurfaceGetSeaLevel();
        float heightAboveSea = m_CachedPosition[1] - seaLevel;
        float maxHeight = 2.0;  // LARGE: 2.0, SMALL: 1.5
        float heightFade = 1.0 - (heightAboveSea / maxHeight);
        if (heightFade < 0) heightFade = 0;
        if (heightFade > 1.0) heightFade = 1.0;
        heightFade = heightFade * heightFade;  // squared falloff
        
        // 1) Bounce suppression
        if (velocity[1] > 0.5 && heightFade > 0.01) {
            float bounceSuppress = velocity[1] * -4300.0 * heightFade;  // LARGE -4300, SMALL -2400
            if (bounceSuppress < -14000.0) bounceSuppress = -14000.0;   // clamp
            totalForce[1] += bounceSuppress;
        }
        
        // 2) Rudder torque on water (rudder works in water)
        if (Math.AbsFloat(m_RudderSmooth) > 0.05) {
            float rudderTorque = m_RudderSmooth * 2800.0;  // LARGE 2800, SMALL 1200
            totalTorque += up * rudderTorque;
        }
        
        // 3) [SMALL template only] Water thrust (car needs direct propulsion in water)
        // if (m_ThrottleSmooth > 0.3) {
        //     totalForce += fwd * (1800.0 * m_ThrottleSmooth * heightFade);
        // }
        
        // 4) Step takeoff PID (escape water surface)
        float stepStartSpeed = 25.0;  // LARGE 25, SMALL 15
        float stepFullSpeed  = 55.0;
        float targetPitchDeg = 8.0;   // LARGE 8, SMALL 10
        if (speedKmph > stepStartSpeed && m_ThrottleSmooth > 0.4) {
            float stepProgress = Math.Clamp((speedKmph - stepStartSpeed) / (stepFullSpeed - stepStartSpeed), 0, 1);
            float currentPitchDeg = Math.Asin(fwd[1]) * Math.RAD2DEG;
            float pitchError = (targetPitchDeg * stepProgress) - currentPitchDeg;
            float pitchRate = vector.Dot(m_CachedAngularVel, right) * Math.RAD2DEG;
            
            float kP = 1900.0;  // LARGE 1900, SMALL 800
            float kD = 950.0;   // LARGE 950,  SMALL 400
            float stepTorque = (pitchError * kP) - (pitchRate * kD);
            stepTorque = Math.Clamp(stepTorque * m_ThrottleSmooth * heightFade, -12000, 12000);  // LARGE ±12000, SMALL ±5000
            totalTorque += right * stepTorque;
            
            // Extra lift escape
            float liftProgress = stepProgress * stepProgress;
            float escapeForce = liftProgress * 6000.0 * m_ThrottleSmooth * heightFade;  // LARGE 6000, SMALL 2500
            totalForce[1] += escapeForce;
            
            // Thrust boost
            float thrustBoost = liftProgress * 3500.0 * m_ThrottleSmooth * heightFade;  // LARGE 3500, SMALL 1500
            totalForce += fwd * thrustBoost;
        }
        
        // 5) Side drag (water tracking)
        float sideDot = vector.Dot(velocity, right);
        totalForce += right * -(sideDot * 480.0);  // LARGE 480, SMALL 200
        
        if (totalForce.LengthSq() > 0.01) SafeApplyForce(totalForce);
        if (totalTorque.LengthSq() > 0.01) SafeApplyTorque(totalTorque);
    }
    
    override protected void ApplyFlightPhysics(float dt)
    {
        UpdateWaterDetection(dt);
        super.ApplyFlightPhysics(dt);  // base aerodynamics first
        if (m_IsOnWater && m_PlaneMode == PlaneMode.PLANE_MODE_AIR)
            ApplyWaterPhysics(dt);     // then water layer
    }
    
    // Stall disabled while on water (prevents spurious stall warning during taxi)
    override protected float CalculateStallFactor(float speedKmph, float aoaDeg, float bankDeg, float heightAGL)
    {
        if (m_IsOnWater) return 0.0;
        return super.CalculateStallFactor(speedKmph, aoaDeg, bankDeg, heightAGL);
    }
};
```

**Two-template preset table**:

| Parameter | LARGE (Catalina) | SMALL (Patty_Wagon, Tigermoth_MK3) |
|---|---|---|
| `maxHeight` (water effect fade above sea) | 2.0 m | 1.5 m |
| `bounceSuppress` coefficient | -4300, clamp -14000 | -2400, clamp -8000 |
| `rudderTorque` multiplier | 2800 | 1200 |
| `waterThrust` (direct propulsion, SMALL only) | — | 1800 × throttle × heightFade |
| `stepStartSpeed` km/h | 25 | 15 |
| `targetPitchDeg` | 8° | 10° |
| PID `kP, kD` | 1900, 950 | 800, 400 |
| Step torque clamp | ±12000 | ±5000 |
| `escapeForce` (vertical lift boost) | 6000 | 2500 |
| `thrustBoost` (forward push during step) | 3500 | 1500 |
| `sideDrag` coefficient | 480 | 200 |

Pick LARGE for big planes (Catalina, DC-3-like sizes). Pick SMALL for amphibious cars or small seaplanes (Patty_Wagon, biplane MK3).

### Water effect attachment via memory points

```cpp
protected void InitWaterEffects()
{
    if (m_WaterEffectsInitialized) return;
    if (!GetGame().IsClient() && GetGame().IsMultiplayer()) return;  // server skip (no rendering)
    
    if (MemoryPointExists("ptcfxfront")) {
        m_WaterEffectFront = new EffectSeaplaneWaterFront();
        m_WaterEffectFront.AttachTo(this, GetMemoryPointPos("ptcfxfront"));
    }
    // ... ptcfxback, ptcfxside1, ptcfxside2
    m_WaterEffectsInitialized = true;
}
```

Memory points needed in p3d: `ptcfxfront`, `ptcfxback`, `ptcfxside1`, `ptcfxside2` (4 spawn positions for water spray emitters). Always check `MemoryPointExists` first (defensive; declared at `P:\scripts\3_game\entities\object.c:454`). The `EffectSeaplaneWaterFront/Back/Side` classes are LM_Planes's own and are described in `effects-and-lights.md`; the particle file formats are in the `dayz-particles` skill.

### Triple cleanup hook pattern (effect lifecycle)

```cpp
override void EEDelete(EntityAI parent) {
    CleanupWaterEffects();
    super.EEDelete(parent);
}
override void CleanupEffects() {
    super.CleanupEffects();
    CleanupWaterEffects();
}
void ~LM_Catalina() {
    CleanupWaterEffects();  // destructor catches edge cases
}
```

Guarantees `SEffectManager.DestroyEffect()` runs regardless of destruction path. **Mandatory pattern when entity holds ScriptedEffect refs** — without it, effects leak.

### Composition pattern: ApplyFlightPhysics override

```cpp
override protected void ApplyFlightPhysics(float dt) {
    UpdateWaterDetection(dt);    // pre-step: refresh state flags
    super.ApplyFlightPhysics(dt); // base aerodynamics
    if (m_IsOnWater && m_PlaneMode == PlaneMode.PLANE_MODE_AIR)
        ApplyWaterPhysics(dt);    // additional physics layer
}
```

Per-aircraft can add extra physics layers without rewriting base. Combine: base aero + water + (future: weather effects, ground effect, gusts).

### Parameter presets table (large vs small aircraft)

Use these as starting points for new aircraft:

**LARGE aircraft preset** (Catalina + DC-3 share these exact values):

```cpp
override protected float GetWingArea()        { return 28.0; }
override protected float GetWingSpan()        { return 14.5; }
override protected float GetWingAR()          { return 7.5; }
override protected float GetWingMeanChord()   { return 1.93; }
override protected float GetEngineMaxPower()  { return 5200.0; }
override protected float GetPropEfficiency()  { return 0.88; }
override protected float GetEngineSpoolUp()   { return 7.0; }     // slow spool (inertia)
override protected float GetEngineSpoolDown() { return 3.5; }
override protected float GetElevatorAuthority() { return 0.85; }  // more authority to move mass
override protected float GetAileronAuthority()  { return 0.70; }
override protected float GetRudderAuthority()   { return 0.95; }
override protected float GetMaxSpeedMs()        { return 72.0; }
override protected float GetCameraDistance()    { return 28.0; }  // bigger orbit
override protected vector GetCameraOffset()     { return "0 5.5 0"; }  // higher view
override protected float GetStallBaseSpeedKmph() { return 50.0; }  // stalls later (wing area)
```

**SMALL aircraft preset** (Tigermoth template, identical for Cessna180/StuntPlane/Z37):

```cpp
override protected float GetWingArea()        { return 22.0; }
override protected float GetWingSpan()        { return 8.9; }
override protected float GetWingAR()          { return 5.2; }
override protected float GetWingMeanChord()   { return 1.7; }
override protected float GetEngineMaxPower()  { return 3100.0; }  // ~3000-4000
override protected float GetPropEfficiency()  { return 0.92; }
override protected float GetEngineSpoolUp()   { return 2.8; }     // fast spool
override protected float GetElevatorAuthority() { return 0.60; }
override protected float GetMaxSpeedMs()      { return 52.0; }
override protected float GetCameraDistance()  { return 14.0; }
override protected vector GetCameraOffset()   { return "0 2.8 0"; }
override protected float GetStallBaseSpeedKmph() { return 62.0; }
```

**Acrobatic tuning** (StuntPlane = small airframe + aggressive overrides):

```cpp
// Same airframe as Spitfire/StuntPlane base
override protected float GetAileronEffectiveness() { return 0.87; }  // +74% vs default 0.50
override protected float GetAileronAuthority()     { return 1.20; }  // +60%, max in mod
override protected float GetStallBaseSpeedKmph()   { return 18.0; }  // ultra-low (acrobatic stunts)
override protected float GetMinFlightSpeedKmph()   { return 32.0; }
override protected float GetMaxSpeedMs()           { return 95.0; }  // fastest
override protected float GetLevelFlightSpeedKmph() { return 250.0; }
override protected bool HasRetractableGear()       { return false; }
```

**Flying car tuning** (Patty_Wagon = car that barely flies):

```cpp
// Tigermoth chassis + minimal flight envelope (engineered to drive, not fly)
override protected float GetEngineMaxPower()      { return 3200.0; }
override protected float GetStallBaseSpeedKmph()  { return 18.0; }  // can lift off if accelerated
override protected float GetMinFlightSpeedKmph()  { return 32.0; }
override protected float GetCameraOffset()        { return "0 2.5 0"; }
// + ApplyWaterPhysics SMALL template for amphibious behavior
```

### Helper: SurfaceIsSea / SurfaceIsPond / SurfaceGetSeaLevel

Vanilla DayZ water detection (reusable for amphibious vehicles, submarines, water-aware behavior). `SurfaceGetSeaLevel` is declared at `P:\scripts\3_game\global\game.c:1191`, and `SurfaceIsSea` and `SurfaceIsPond` at `P:\scripts\3_game\global\game.c:1196` to `:1197`:

```cpp
float seaLevel = GetGame().SurfaceGetSeaLevel();  // absolute Y of water level

bool onWater = GetGame().SurfaceIsSea(x, z)       // saltwater/ocean
           || GetGame().SurfaceIsPond(x, z);      // freshwater/lagoon

float heightAboveSea = pos[1] - seaLevel;
```
