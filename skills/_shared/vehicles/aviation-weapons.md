# Aircraft weapons

How a plane fires: a tracer projectile with no engine physics, instant raycast damage with a visible tracer, the pilot only check, the client to server request, and impact effects timed to the tracer.

The pattern is the Spitfire's in LM_Planes (Workshop `3730564764`), whose scripts are the source; it is mod practice, not vanilla, except where a `P:\` line is cited. The server side code is in `aviation-weapon-fire-code.md`. Of the LM_Planes fleet only the Spitfire fires; the Catalina's Browning M2 is a model with no firing code.

## The approach

The server casts a 1500 m ray for the damage and, at the same time, spawns a tracer that flies along the same line for the look. Hits are instant, and players still see a round travel. Every asset is vanilla except the mod's own impact particle:

| Piece | Where vanilla declares it |
|---|---|
| Tracer model | `P:\DZ\weapons\projectiles\tracer_red.p3d` |
| `Ammo_308Win` and `Ammo_308WinTracer` ammunition | `P:\DZ\weapons\ammunition\config.cpp:100` and `:164` |
| `RGD5Grenade_Ammo` damage profile | `P:\DZ\weapons\explosives\config.cpp:24` |
| `Grenade_explosion_SoundSet` | `P:\DZ\sounds\hpp\config.cpp:338734` |
| `ParticleList.GUN_IZH18`, the IZH-18 muzzle flash (`weapon_shot_izh18_01`) | `P:\scripts\3_game\particles\particlelist.c:176` |
| `DayZPhysics.RaycastRV` | `P:\scripts\3_game\global\dayzphysics.c:199` |
| `ProcessDirectDamage` and `ProcessDirectDamageFlags.ALL_TRANSFER` | `P:\scripts\3_game\entities\object.c:1138` and `:3` |
| `GetDamageZoneNameByComponentIndex` and `GetDamageZones` | `object.c:1164` and `:1153` |
| `ImpactEffectsData` and `ImpactTypes` | `P:\scripts\3_game\impacteffects.c:10` and `:1` |
| `ThrowPhysically` | `P:\scripts\3_game\entities\inventoryitem.c:26` |
| `SetLifetime` | `P:\scripts\3_game\entities\entityai.c:3377` |

`ParticleList.PLANES_IMPACT` is the mod's own particle, not vanilla.

The Spitfire takes rifle rounds from its cargo but deals damage with the `RGD5Grenade_Ammo` profile, so rifle ammunition does explosive damage without a new damage type.

## A tracer with no physics

```cpp
class CfgVehicles
{
    class Inventory_Base;
    class MyMod_Tracer: Inventory_Base
    {
        scope = 2;
        displayName = "Tracer";
        model = "\DZ\weapons\projectiles\tracer_red.p3d";
        gravityCoef = 0;
        linearDamping = 0;
        angularDamping = 0;
        gravity = 0;
        airFriction = 0;
        weight = 0.001;
    };
};
```

Script then calls `dBodySetDamping(proj, 0, 0)`, `dBodyEnableGravity(proj, false)` and `SetLifetime(4)`, so the round flies straight with no drop or drag for four seconds. The same works for any energy round: lasers, plasma, tracers.

## Settings

```c
static const int SHOT_TIMEOUT = 240;          // ms between shots, about 4.2 a second
static const float PROJECTILE_SPEED = 350.0;
static const string PROJECTILE_CLASS = "MyMod_Tracer";
static const string AMMO_TYPE = "RGD5Grenade_Ammo";       // grenade damage, not bullet damage
static const string SHOT_SOUNDSET = "MyMod_Plane_Shot_SoundSet";
static const string IMPACT_SOUNDSET = "Grenade_explosion_SoundSet";
static const int MUZZLE_PARTICLE = ParticleList.GUN_IZH18;
static ref array<string> ALLOWED_AMMO = {"Ammo_308Win", "Ammo_308WinTracer"};
```

Give the mod's RPCs IDs in a range of its own so they do not collide with vanilla or other mods. The Spitfire uses `RPC_SHOT_FIRED = 937081` (client to server) and `RPC_SYNC_SHOT_FX = 937091` (server to clients).

## Only the pilot fires

```c
private bool IsLocalPilot()
{
    DayZPlayer p;
    Transport t;
    if (!Class.CastTo(p, GetGame().GetPlayer())) return false;
    if (!Class.CastTo(t, p.GetParent())) return false;
    return t == this && CrewMemberIndex(p) == 0; // seat 0 is the pilot
}
```

Co-pilots and cargo seats cannot fire, which matters on an aircraft with several seats such as the five seat Catalina.

## Fire request and effects

The pilot's client asks, the server fires, and the server tells every client what to show:

```c
override void EOnPostSimulate(IEntity other, float timeSlice)
{
    super.EOnPostSimulate(other, timeSlice);
    if (!CrewDriver() && !EngineIsOn()) return;
    if (!IsLocalPilot()) return;
    if (m_PlaneMode != PlaneMode.PLANE_MODE_AIR) return;
    Input inp = GetGame().GetInput();
    if (!inp) return;
    if (inp.LocalHold("UAMyModPlaneShoot") && m_canShoot)
    {
        GetGame().RPCSingleParam(this, MyMod_RPC.SHOT_FIRED, new Param1<bool>(true), true);
        m_canShoot = false;
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ShotReady, SHOT_TIMEOUT, false);
    }
}

override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);
    if (GetGame().IsServer() && rpc_type == MyMod_RPC.SHOT_FIRED)
    {
        Param1<bool> p;
        if (ctx.Read(p) && p.param1) DoFire();
    }
    if (rpc_type == MyMod_RPC.SYNC_SHOT_FX && !GetGame().IsServer())
    {
        Param3<Object, ImpactEffectsData, vector> fx;
        if (ctx.Read(fx))
        {
            PlayMuzzleFX(fx.param3); // muzzle flash at once
            float dist = vector.Distance(fx.param2.m_Position, fx.param3);
            float inSpeedLen = fx.param2.m_InSpeed.Length();
            int delayMs = 0;
            if (inSpeedLen > 0.1)
                delayMs = Math.Round((dist / inSpeedLen) * 1000);
            delayMs = Math.Clamp(delayMs, 0, 10000);
            GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(PlayImpactFX, delayMs, false, fx.param1, fx.param2, fx.param3);
        }
    }
}
```

The impact effect waits for the tracer's flight time, so the hit shows when the tracer arrives. Without the delay, a hit 1500 m away would flash at the same moment as the muzzle.

In `PlayImpactFX`, shake the camera when the local player is the one hit:

```c
DayZPlayer localPlayer = DayZPlayer.Cast(GetGame().GetPlayer());
if (directHit && localPlayer && directHit == localPlayer)
    localPlayer.GetCurrentCamera().SpawnCameraShake(0.4);
```
