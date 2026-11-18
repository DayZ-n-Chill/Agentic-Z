# Fixed-wing flight physics in script

How a scripted plane works out lift, drag, thrust and stall, which atmosphere model it uses, how it levels itself, and how it keeps NaN forces out of the physics body.

The pattern comes from LM_Planes (Workshop `3730564764`) and is that mod's own script, not vanilla; only the `P:\` lines cited here are vanilla. Learn the pattern from it and write the mod's own code. Seaplanes are in `aviation-seaplanes.md`, the per-aircraft numbers in `aviation-aircraft-presets.md`, and the update rate tricks in `aviation-script-performance.md`.

## Lift and drag coefficients

Lift is a cubic polynomial of the angle of attack, clamped; induced drag follows from the lift coefficient, the wing aspect ratio and the Oswald factor:

```c
protected float CalculateLiftCoefficient(float aoaDeg)
{
    float aoaRad = aoaDeg * Math.DEG2RAD;
    float cl = GetClCoef3() * aoaRad * aoaRad * aoaRad
             + GetClCoef2() * aoaRad * aoaRad
             + GetClCoef1() * aoaRad
             + GetClCoef0();
    // stall transition smoothing goes here
    return Math.Clamp(cl, GetClMin(), GetClMax());
}

protected float CalculateInducedDrag(float cl)
{
    return cl * cl / (Math.PI * GetWingAR() * GetOswaldE());
}
```

The Tigermoth uses `ClCoef3=-0.00038`, `ClCoef2=0.00055`, `ClCoef1=0.095`, `ClCoef0=0.18`, `ClMax=1.35`, `ClMin=-0.95`, a wing aspect ratio of about 5.2 and an Oswald factor of about 0.78.

## Forces each tick

`ApplyFlightPhysics(dt)` reads cached velocity, forward vector and position, then:

| Step | How |
|---|---|
| Air density | `StandardPlaneAtmosphere.GetDensityRatio(altitude)` times 1.225 |
| Dynamic pressure | `0.5 * density * speed * speed`, capped at 7500 so forces cannot run away at extreme speed |
| Lift | Dynamic pressure times wing area times lift coefficient times a lift scale, along `(velocityNorm * up) * velocityNorm`, which is square to the velocity in the plane of velocity and up |
| Thrust | `GetEngineMaxPower()` times throttle squared, times the altitude performance factor, propeller efficiency and a low speed boost, along the forward axis |
| Apply | `SafeApplyForce(totalForce)` and `SafeApplyTorque(totalTorque)` (see below) |

Throttle squared gives little power at low throttle and full power at the top. The low speed boost runs from 1.25 down to 1.0 between 0 and 25 m/s so the plane does not stall on takeoff.

## Stall and bank

A banked wing needs more lift, by the load factor `1/cos(bank)`, so the stall speed rises with the square root of it:

```c
protected float CalculateStallSpeed(float bankDeg)
{
    float cosBank = Math.Cos(Math.AbsFloat(bankDeg) * Math.DEG2RAD);
    if (cosBank < 0.1) cosBank = 0.1; // no divide by zero near 90 degrees
    return GetStallBaseSpeedKmph() * Math.Sqrt(1.0 / cosBank);
}
```

`CalculateStallFactor(speedKmph, aoaDeg, bankDeg, heightAGL)` returns 0 below `GetStallAltitudeMin()` (15 m above ground, so taxiing and landing never warn), and otherwise combines the speed margin over the stall speed, the angle of attack and the bank into a stall depth. The warning sound `<Aircraft>_Engine_StallWarn_SoundSet` plays when `m_StallFactor` reaches `GetStallKillThreshold()` (0.7), the engine is on and the plane is in `PLANE_MODE_AIR`.

## A small standard atmosphere

`StandardPlaneAtmosphere` is a standalone helper any vehicle mod that cares about altitude can reuse. Its constants are the real standard atmosphere values:

| Constant | Value |
|---|---|
| `SEA_LEVEL_PRESSURE` | `101325.0` |
| `SEA_LEVEL_TEMPERATURE` | `288.15` |
| `SEA_LEVEL_DENSITY` | `1.225` |
| `TEMPERATURE_LAPSE_RATE` | `-0.0065` |
| `GAS_CONSTANT` | `287.05` |
| `GRAVITY` | `9.80665` |
| `MAX_ALTITUDE` | `2000.0` |
| `PRACTICAL_CEILING` | `1800.0` |

`GetDensity(altitude)` uses a single isothermal layer, `GetDensityRatio` divides by sea level density, and `GetPerformanceFactor` is 1.0 below 1200 m and falls in a straight line to 0.6 at 2000 m.

## Keep NaN out of the body

A NaN that reaches the physics body crashes the game, so guard every custom force. The wrapped calls are vanilla: `dBodyApplyForce` (`P:\scripts\1_core\proto\enphysics.c:146`) and `dBodyApplyTorque` (`:153`).

```c
protected void SafeApplyForce(vector force)
{
    if (!IsVectorFinite(force)) return; // drop the force, never pass NaN on
    force = ClampVectorMagnitude(force, MAX_FORCE_MAGNITUDE);
    dBodyApplyForce(this, force);
}
```

The helpers around it: `SanitizeFloat(value, fallback, min, max)` returns the fallback for a non-finite value and clamps the rest; `SanitizeVector` checks each component; `ClampVectorMagnitude` scales a vector down to a maximum length. `CheckPhysicsSanity` counts frames with NaN and, at `NAN_HARD_THRESHOLD`, calls `ForcePhysicsReset()` to zero linear and angular velocity.

| Constant | Value |
|---|---|
| `MAX_SANE_SPEED` | `250` m/s |
| `MAX_SANE_ANGULAR_VEL` | `25` |
| `MAX_FORCE_MAGNITUDE` | `80000` |
| `MAX_TORQUE_MAGNITUDE` | `60000` |
| `NAN_RESET_THRESHOLD` | `1` |
| `NAN_HARD_THRESHOLD` | `10` |

Treat these guards as part of every scripted flight model, not an extra.

## Self levelling

Each axis levels itself only while the pilot gives no input on it, inside a deadband. The gains grow with `controlEffectiveness`, which grows with speed: weak while taxiing, full in flight.

| Axis | Behaviour |
|---|---|
| Roll | Deadband 3 degrees; `rollCmd = -bankErr * Kp - rollRate * Kd`, with `Kp` and `Kd` lerped from 40 percent to full by control effectiveness |
| Yaw | Same pattern; `Kp=0.22`, `Kd=0.25`, deadband 2 degrees |
| Pitch | Level flight hold above `GetLevelFlightSpeedKmph()` (185); fades with speed margin and pitch input |
| Turn | Automatic rudder of `bankSign * turnNeed * 0.30` plus a sideslip correction while banked |

## Damping with no pilot

With nobody in the seat, multiply angular velocity by `IDLE_DAMPING_FACTOR = 0.92` each tick, skipping it below a small threshold so it does not jitter. A plane the pilot jumps out of then stops spinning instead of turning forever. The calls are vanilla: `dBodyGetAngularVelocity` and `dBodySetAngularVelocity` (`P:\scripts\1_core\proto\enphysics.c:158` and `:165`).
