# Vehicle script helpers

How shipped vehicle mods keep animation and sync cheap, stop an empty vehicle spinning, clean up effects on every removal path, detect water, resolve damage zones, find the local driver and pick a seat animation. Seat poses, crew and vehicle networking are in `vehicle-scripting.md`; the vehicles pack is `_shared/vehicles/`.

## Skip animation calls that change nothing

`SetAnimationPhase` is an engine call. For values that move smoothly, such as dials and slow rotations, call it only when the phase has moved past a threshold:

```c
protected float m_LastPitchPhase = -999.0;
protected const float MYMOD_ANIM_STEP = 0.015;

protected void UpdatePitchAnim()
{
    float phase = ComputePitchPhase();
    if (Math.AbsFloat(phase - m_LastPitchPhase) < MYMOD_ANIM_STEP)
        return;
    SetAnimationPhase("mymod_pitch", phase);
    m_LastPitchPhase = phase;
}
```

A step of 0.015 gives about 67 distinct positions across 0 to 1, which looks continuous.

## Different rates for different work

```c
protected float m_DialTimer;
protected const float MYMOD_DIAL_INTERVAL = 0.1;   // 10 per second

override void EOnPostSimulate(IEntity other, float dt)
{
    super.EOnPostSimulate(other, dt);
    m_DialTimer += dt;
    if (m_DialTimer >= MYMOD_DIAL_INTERVAL)
    {
        UpdateAllDials();
        m_DialTimer = 0;
    }
}
```

Physics still runs every tick; only cosmetic work is throttled. Dials, HUD values and cosmetic animations at 10 per second are visibly less smooth but stay readable and cost far less. Shipped mods sync at about 30 per second while there is input and 10 per second when idle.

## Damping an empty vehicle

With no driver, multiply angular velocity by 0.92 each tick so a vehicle the pilot left does not spin or roll forever, and ignore tiny rotations so the damping does not fight small oscillations:

```c
protected const float MYMOD_IDLE_DAMPING = 0.92;

protected void ApplyIdleDamping()
{
    vector angVel = dBodyGetAngularVelocity(this);
    if (angVel.LengthSq() < 0.01)
        return;
    dBodySetAngularVelocity(this, angVel * MYMOD_IDLE_DAMPING);
}
```

## Cleaning up effects on every path

An entity that owns particles, sounds or lights must release them through `SEffectManager.DestroyEffect`, or they leak. Call one cleanup method from three places, so normal removal, server unload and the final release are all covered:

```c
class MyMod_Vehicle: CarScript
{
    protected ref EffectParticle m_Eff;

    override void EEDelete(EntityAI parent)
    {
        MyMod_Cleanup();
        super.EEDelete(parent);
    }

    override void CleanupEffects()
    {
        super.CleanupEffects();
        MyMod_Cleanup();
    }

    void ~MyMod_Vehicle()
    {
        MyMod_Cleanup();
    }

    protected void MyMod_Cleanup()
    {
        if (!m_Eff)
            return;
        m_Eff.Stop();
        SEffectManager.DestroyEffect(m_Eff);
        m_Eff = null;
    }
}
```

`CleanupEffects` is declared on `Transport` (`P:\scripts\3_game\vehicles\transport.c:1007`) and overridden in `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:390`).

## Water

`CGame` declares `SurfaceGetSeaLevel()`, `SurfaceIsSea(float x, float z)`, `SurfaceIsPond(float x, float z)` and `GetWaterDepth(vector posWS)` (`P:\scripts\3_game\global\game.c:1191` to `:1198`). Height above the sea is `pos[1] - GetGame().SurfaceGetSeaLevel()`. `SurfaceIsSea` and `SurfaceIsPond` are slow; prefer `GetWaterDepth(pos)` on a hot path (see `runtime-pitfalls.md`).

## Resolving a damage zone

`GetDamageZoneNameByComponentIndex(int componentIndex)` and `GetDamageZones(out TStringArray dmgZones)` are on `Object` (`P:\scripts\3_game\entities\object.c:1164` and `:1153`). Shipped mods fall back in steps before calling `ProcessDirectDamage`, so an unknown target type never gets an empty zone:

```c
protected string MyMod_ResolveZone(Object hitObj, int componentIdx)
{
    string zone = hitObj.GetDamageZoneNameByComponentIndex(componentIdx);
    if (zone != "")
        return zone;
    if (hitObj.IsMan() || hitObj.IsInherited(DayZInfected) || hitObj.IsInherited(DayZCreatureAI))
        return "Torso";
    TStringArray zones = new TStringArray();
    hitObj.GetDamageZones(zones);
    if (zones.Count() > 0)
        return zones[0];
    return "";
}
```

Call `ProcessDirectDamage(DamageType.FIRE_ARM, this, zone, ammoType, hitObj.WorldToModel(hitPos), damageCoef, ProcessDirectDamageFlags.ALL_TRANSFER)` only when the zone is not empty. The declaration is `ProcessDirectDamage(int damageType, EntityAI source, string componentName, string ammoName, vector modelPos, float damageCoef = 1.0, int flags = 0)` (`P:\scripts\3_game\entities\object.c:1138`): the position is in the target's model space (`WorldToModel` at `:874`), and the sixth argument scales the ammo's damage, it is not a damage amount.

## Camera shake for the local player

`DayZPlayerCamera.SpawnCameraShake(float strength = 1, float radius = 2, float smoothness = 5, float radius_decay_speed = 6)` (`P:\scripts\3_game\dayzplayer.c:127`). From a client side impact handler, shake only when the hit is the local player; `0.4` is mild, use more for explosions:

```c
DayZPlayer localPlayer = DayZPlayer.Cast(GetGame().GetPlayer());
if (directHit && localPlayer && directHit == localPlayer)
    localPlayer.GetCurrentCamera().SpawnCameraShake(0.4);
```

## Is the local player driving

```c
private bool MyMod_IsLocalDriver()
{
    DayZPlayer p;
    Transport t;
    if (!Class.CastTo(p, GetGame().GetPlayer()))
        return false;
    if (!Class.CastTo(t, p.GetParent()))
        return false;
    return t == this && CrewMemberIndex(p) == 0;
}
```

Seat 0 is the driver or pilot (`CrewMemberIndex`, `P:\scripts\3_game\vehicles\transport.c:186`). Use it to gate driver-only weapons and actions.

## Seat animation set

Override `GetAnimInstance()`, which `Transport` declares (`P:\scripts\3_game\vehicles\transport.c:665`), to return a vanilla `VehicleAnimInstances` value that matches the cockpit, and no custom animations are needed:

| Value | Fits |
|---|---|
| `GOLF` | A small, compact cockpit (sports cars, small planes) |
| `SEDAN` | A standard car |
| `V3S` | A truck cab (large vehicles, transport planes) |

The full enum, with `CIVVAN`, `HATCHBACK`, `BUS`, `S120`, `MULTICAR`, `HMMWV`, `ZODIAC`, `MOTO1` and `MOTO2`, is at `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`.
