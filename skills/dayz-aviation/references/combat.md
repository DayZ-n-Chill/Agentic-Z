# Combat aviation: weapons, projectiles and hitscan

Optional weapons on an aircraft: a tracer projectile with no engine physics, hitscan damage with a visual tracer, the full Spitfire fire pipeline (RPC, ammo, damage zone resolution), and camera shake.

Third-party material: patterns read from the LM_Planes mod (Workshop `3730564764`, by Llama and Itspete-Here), whose files are not in this repo. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code.

## Combat Aviation (optional)

### Custom projectile (zero-physics tracer)

```cpp
class CfgVehicles {
    class Inventory_Base;
    class LM_Planes_Tracer: Inventory_Base
    {
        scope = 2;
        displayName = "Bombardment!";
        model = "\DZ\weapons\projectiles\tracer_red.p3d";
        gravityCoef    = 0;
        linearDamping  = 0;
        angularDamping = 0;
        gravity        = 0;
        airFriction    = 0;
        weight         = 0.001;
    };
};
```

For script-driven projectiles where you want zero engine physics interference (visual only).

### Hitscan + visual tracer (Spitfire pattern)

```cpp
class LM_Spitfire extends LlamaPlaneScript
{
    protected bool m_canShoot;
    static const string SPIT_PROJECTILE_CLASS = "LM_Planes_Tracer";
    
    override void OnInput(float dt)
    {
        // ... base flight inputs
        if (inp.LocalHold("UALlamaPlaneShoot") && m_canShoot)
        {
            m_canShoot = false;
            DoFire();
            // cooldown re-enables m_canShoot via timer
        }
    }
    
    protected void DoFire()
    {
        vector mw = /* muzzle world position */;
        vector axis = /* forward axis */;
        vector hitPos;
        Object hitObj;
        DayZPhysics.RaycastRV(mw, mw + axis * 1500, hitPos, null, hitComp, m_HitObjects,
                              null, this, false, false, ObjIntersectFire);
        // Spawn LM_Planes_Tracer at mw, accelerating along axis
        // Apply damage at hitPos if raycast hit
        // Use vanilla DayZ Ammo_308WinTracer for damage profile
    }
}
```

Hitscan (1500m raycast) does damage, visual tracer is the projectile spawn — combo gives instant hits with visible bullet trail.

### Combat aviation: Spitfire shooting pattern (full)

Heavy combat pattern. Only Spitfire among Llama's aircraft has full firing implementation. Catalina has visible Browning M2 .50 cal rvmats but no firing logic — gun mounts are cosmetic.

**Custom RPC enum convention** (avoid vanilla DayZ RPC collisions):

```cpp
enum SPIT_RPCserver { RPC_SHOT_FIRED  = 937081 };
enum SPIT_RPCclient { RPC_SYNC_SHOT_FX = 937091 };
```

Magic constants in 937xxx range to avoid colliding with vanilla DayZ + other mods. Pick your own unique range (~10 digits) for your mod's RPCs.

**Constants and config**:

```cpp
class LM_Spitfire extends LlamaPlaneScript
{
    protected bool m_canShoot;
    protected int m_NextMuzzle;
    protected ref array<EntityAI> m_AmmoSearchItems = new array<EntityAI>();
    protected ref set<Object> m_HitObjects = new set<Object>();
    protected ref array<Man> m_PlayerCache = new array<Man>();
    protected ref array<string> m_DmgZoneCache = new array<string>();
    
    static const int SPIT_SHOT_TIMEOUT       = 240;     // ms between shots (~4.16 shots/sec)
    static const float SPIT_PROJECTILE_SPEED = 350.0;
    static const string SPIT_PROJECTILE_CLASS = "LM_Planes_Tracer";
    static const string SPIT_AMMO_TYPE        = "RGD5Grenade_Ammo";       // !!! grenade damage, not bullet
    static const string SPIT_SHOT_SOUNDSET    = "LM_Spitfire_Shot_SoundSet";
    static const string SPIT_IMPACT_SOUNDSET  = "Grenade_explosion_SoundSet";
    static const int SPIT_IMPACT_PARTICLE     = ParticleList.PLANES_IMPACT;
    static const int SPIT_MUZZLE_PARTICLE     = ParticleList.GUN_IZH18;   // reuse vanilla shotgun muzzle flash
    
    static ref array<string> SPIT_ALLOWED_AMMO = {
        "Ammo_308Win",
        "Ammo_308WinTracer"
    };
    
    void LM_Spitfire() { m_canShoot = true; m_NextMuzzle = 0; }
```

**Damage Type hack** — uses rifle ammo as inventory source but applies grenade damage profile (gets explosive damage from rifle bullets without creating new damage types). Reuses vanilla `ParticleList.GUN_IZH18` (shotgun muzzle flash) and `Grenade_explosion_SoundSet` for impact. Zero new assets created for combat.

**IsLocalPilot** check (gate weapons to pilot seat only):

```cpp
private bool IsLocalPilot() {
    DayZPlayer p;
    Transport t;
    if (!Class.CastTo(p, GetGame().GetPlayer())) return false;
    if (!Class.CastTo(t, p.GetParent())) return false;
    return (t == this && CrewMemberIndex(p) == 0);  // CrewMemberIndex 0 = pilot
}
```

Copilots / cargo seats can't fire — only seat index 0. Critical when aircraft has multiple seats (Catalina with 5).

**Input → server → broadcast pattern**:

```cpp
override void EOnPostSimulate(IEntity other, float timeSlice)
{
    super.EOnPostSimulate(other, timeSlice);
    if (!CrewDriver() && !EngineIsOn()) return;
    if (!IsLocalPilot()) return;
    if (m_PlaneMode != PlaneMode.PLANE_MODE_AIR) return;
    
    Input inp = GetGame().GetInput();
    if (!inp) return;
    
    if (inp.LocalHold("UALlamaPlaneShoot") && m_canShoot) {
        // RPC to server: please fire
        GetGame().RPCSingleParam(this, SPIT_RPCserver.RPC_SHOT_FIRED, new Param1<bool>(true), true);
        m_canShoot = false;
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ShotReady, SPIT_SHOT_TIMEOUT, false);
    }
}

override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);
    
    // Server: receive shot request, execute
    if (GetGame().IsServer() && rpc_type == SPIT_RPCserver.RPC_SHOT_FIRED) {
        Param1<bool> p;
        if (ctx.Read(p) && p.param1) DoFire();
    }
    
    // Clients: receive FX sync, play effects with tracer-aware delay
    if (rpc_type == SPIT_RPCclient.RPC_SYNC_SHOT_FX && !GetGame().IsServer()) {
        Param3<Object, ImpactEffectsData, vector> fx;
        if (ctx.Read(fx)) {
            PlayMuzzleFX(fx.param3);  // immediate muzzle flash
            
            // Tracer-aware impact delay: calculate real flight time
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

The tracer-aware impact delay is a key polish detail: impact FX appears after the tracer reaches the target (matches visual trajectory). Without this, hits would visually appear simultaneous with muzzle flash even when target is 1500m away.

**Server-side DoFire (consume ammo + spawn projectile + damage + broadcast FX)**:

```cpp
protected void DoFire()
{
    if (!GetGame().IsServer()) return;
    
    // 1) Find ammo in inventory
    Magazine mag = FindAmmoInCargo();
    if (!mag) return;
    mag.ServerSetAmmoCount(mag.GetAmmoCount() - 1);
    if (mag.GetAmmoCount() <= 0) mag.Delete();
    
    // 2) Pick alternating muzzle (cannon_muz_1 / cannon_muz_2)
    string muzzleName = (m_NextMuzzle == 0) ? "cannon_muz_1" : "cannon_muz_2";
    string vectorName = (m_NextMuzzle == 0) ? "cannon_dir_1" : "cannon_dir_2";
    m_NextMuzzle = 1 - m_NextMuzzle;
    
    // 3) Position + direction from named selections
    vector mw = ModelToWorld(GetSelectionPositionMS(muzzleName));
    vector vw = ModelToWorld(GetSelectionPositionMS(vectorName));
    vector dirRaw = vw - mw;
    float dirLen = dirRaw.Length();
    if (dirLen < 0.001) return;
    vector dir = dirRaw * (1.0 / dirLen);
    
    // 4) Bullet velocity inherits vehicle velocity (Galilean relativity)
    vector vehVel = GetVelocity(this);
    vector bulletVel = dir * SPIT_PROJECTILE_SPEED + vehVel;
    float bulletSpeed = bulletVel.Length();
    if (bulletSpeed < 0.1) return;
    vector axis = bulletVel * (1.0 / bulletSpeed);
    
    // 5) Spawn custom-physics tracer (no gravity, no damping, autodestroy 4s)
    EntityAI proj = EntityAI.Cast(
        GetGame().CreateObjectEx(SPIT_PROJECTILE_CLASS, mw + axis, ECE_CREATEPHYSICS));
    if (proj) {
        dBodySetDamping(proj, 0, 0);
        dBodyEnableGravity(proj, false);
        proj.SetDirection(dir);
        InventoryItem ii = InventoryItem.Cast(proj);
        if (ii) ii.ThrowPhysically(null, bulletVel);
        SetVelocity(proj, bulletVel);
        proj.SetLifetime(4);
    }
    
    // 6) Hitscan damage (raycast 1500m)
    vector hitPos;
    int hitComp;
    m_HitObjects.Clear();
    DayZPhysics.RaycastRV(mw, mw + axis * 1500, hitPos, null, hitComp, m_HitObjects, null, this, false, false, ObjIntersectFire);
    
    Object directHit = null;
    if (m_HitObjects.Count() > 0) directHit = m_HitObjects.Get(0);
    
    if (directHit && directHit.IsInherited(EntityAI)) {
        string zone = ResolveDamageZone(directHit, hitComp);
        if (zone != "")
            directHit.ProcessDirectDamage(DamageType.FIRE_ARM, this, zone, SPIT_AMMO_TYPE, hitPos, 1.0, ProcessDirectDamageFlags.ALL_TRANSFER);
    }
    
    // 7) Broadcast FX to all clients
    ImpactEffectsData ie = new ImpactEffectsData();
    ie.m_DirectHit = directHit;
    ie.m_ComponentIndex = hitComp;
    ie.m_Surface = "Hit_Gravel";
    ie.m_Position = hitPos;
    ie.m_ImpactType = ImpactTypes.STOP;
    ie.m_AmmoType = SPIT_AMMO_TYPE;
    ie.m_InSpeed = bulletVel;
    
    m_PlayerCache.Clear();
    GetGame().GetPlayers(m_PlayerCache);
    foreach (Man man : m_PlayerCache)
        GetGame().RPCSingleParam(this, SPIT_RPCclient.RPC_SYNC_SHOT_FX,
            new Param3<Object, ImpactEffectsData, vector>(directHit, ie, mw), true, man.GetIdentity());
}
```

**FindAmmoInCargo helper**:

```cpp
protected Magazine FindAmmoInCargo()
{
    m_AmmoSearchItems.Clear();
    GetInventory().EnumerateInventory(InventoryTraversalType.INORDER, m_AmmoSearchItems);
    foreach (EntityAI item : m_AmmoSearchItems) {
        if (!item) continue;
        string itemType = item.GetType();
        for (int i = 0; i < SPIT_ALLOWED_AMMO.Count(); i++) {
            if (itemType == SPIT_ALLOWED_AMMO[i]) {
                Magazine mag = Magazine.Cast(item);
                if (mag && mag.GetAmmoCount() > 0) return mag;
            }
        }
    }
    return null;
}
```

Iterates vehicle inventory, matches against whitelist, returns first non-empty Magazine. Reused `m_AmmoSearchItems` array (`.Clear()` first) avoids allocations every shot.

**Alternating muzzles for twin-gun aircraft**:

`m_NextMuzzle` 0/1 toggle, selection names `cannon_muz_1` / `cannon_muz_2` + `cannon_dir_1` / `cannon_dir_2`. Each shot picks next muzzle. Real Spitfire had 8 wing-mounted Browning .303 machine guns; mod simplifies to 2 alternating cannons. Pattern works for any multi-mount weapon (chainguns, torpedo bays, missile pods).

**Custom-physics tracer projectile**:

```cpp
// In CfgVehicles (config.cpp):
class LM_Planes_Tracer: Inventory_Base
{
    scope = 2;
    displayName = "Bombardment!";
    model = "\DZ\weapons\projectiles\tracer_red.p3d";  // vanilla DayZ tracer model
    gravityCoef    = 0;
    linearDamping  = 0;
    angularDamping = 0;
    gravity        = 0;
    airFriction    = 0;
    weight         = 0.001;
};
```

Plus script-side `dBodySetDamping(proj, 0, 0)` + `dBodyEnableGravity(proj, false)` + `SetLifetime(4)`. Bullet flies straight without gravity/drag for 4 seconds. Pattern for any "energy projectile" (lasers, plasma, tracers).

### Helper: ResolveDamageZone (defensive damage attribution)

```cpp
protected string ResolveDamageZone(Object hitObj, int componentIdx)
{
    string zone = hitObj.GetDamageZoneNameByComponentIndex(componentIdx);
    if (zone != "") return zone;
    
    if (hitObj.IsMan() || hitObj.IsInherited(DayZInfected))
        return "Torso";
    
    if (hitObj.IsInherited(DayZCreatureAI))
        return "Torso";
    
    m_DmgZoneCache.Clear();
    hitObj.GetDamageZones(m_DmgZoneCache);
    if (m_DmgZoneCache.Count() > 0)
        return m_DmgZoneCache[0];
    
    return "";  // No damage applicable
}
```

Chained fallback prevents crashes when damaging unknown target types. Apply this anywhere you call `ProcessDirectDamage` against arbitrary hit objects.

### Camera shake on damage receipt

```cpp
DayZPlayer localPlayer = DayZPlayer.Cast(GetGame().GetPlayer());
if (directHit && localPlayer && directHit == localPlayer)
    localPlayer.GetCurrentCamera().SpawnCameraShake(0.4);
```

In client-side `PlayImpactFX`, shake camera when local player IS the target. Visual feedback patch for weapons in vehicles.

## Vanilla pieces the pattern reuses

Checked on `P:\`, so a mod can name them without shipping new assets:

| Piece | Where vanilla declares it |
|---|---|
| Tracer model | `P:\DZ\weapons\projectiles\tracer_red.p3d` |
| `Ammo_308Win` and `Ammo_308WinTracer` magazines | `P:\DZ\weapons\ammunition\config.cpp:100` and `:164` |
| `RGD5Grenade_Ammo` damage profile | `P:\DZ\weapons\explosives\config.cpp:24` |
| `Grenade_explosion_SoundSet` | `P:\DZ\sounds\hpp\config.cpp:338734` |
| `ParticleList.GUN_IZH18` muzzle flash | `P:\scripts\3_game\particles\particlelist.c:176` |
| `DayZPhysics.RaycastRV` | `P:\scripts\3_game\global\dayzphysics.c:199` |
| `ProcessDirectDamage` and `ProcessDirectDamageFlags.ALL_TRANSFER` | `P:\scripts\3_game\entities\object.c:1138` and `:3` |
| `GetDamageZoneNameByComponentIndex` and `GetDamageZones` | `P:\scripts\3_game\entities\object.c:1164` and `:1153` |
| `ImpactEffectsData` and `ImpactTypes` | `P:\scripts\3_game\impacteffects.c:10` and `:1` |
| `ThrowPhysically` | `P:\scripts\3_game\entities\inventoryitem.c:26` |
| `SetLifetime` | `P:\scripts\3_game\entities\entityai.c:3377` |

`ParticleList.PLANES_IMPACT` is LM_Planes's own registration, not a vanilla particle.
