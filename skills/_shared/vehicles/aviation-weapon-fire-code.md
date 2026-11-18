# Aircraft weapon fire on the server

How the server side of an aircraft gun works: take a round from cargo, pick the muzzle, launch the tracer with the aircraft's speed, cast the damage ray, find a damage zone, and send the effects to every client.

The code follows the Spitfire in LM_Planes (Workshop `3730564764`), whose scripts are the source; it is mod practice, not vanilla, except where a `P:\` line is cited. The client side, the tracer config and the list of vanilla assets it reuses are in `aviation-weapons.md`.

## DoFire

```c
protected void DoFire()
{
    if (!GetGame().IsServer()) return;

    // 1. take one round from cargo
    Magazine mag = FindAmmoInCargo();
    if (!mag) return;
    mag.ServerSetAmmoCount(mag.GetAmmoCount() - 1);
    if (mag.GetAmmoCount() <= 0) mag.Delete();

    // 2. alternate the two guns
    string muzzleName = (m_NextMuzzle == 0) ? "cannon_muz_1" : "cannon_muz_2";
    string vectorName = (m_NextMuzzle == 0) ? "cannon_dir_1" : "cannon_dir_2";
    m_NextMuzzle = 1 - m_NextMuzzle;

    // 3. position and direction from the model's selections
    vector mw = ModelToWorld(GetSelectionPositionMS(muzzleName));
    vector vw = ModelToWorld(GetSelectionPositionMS(vectorName));
    vector dirRaw = vw - mw;
    float dirLen = dirRaw.Length();
    if (dirLen < 0.001) return;
    vector dir = dirRaw * (1.0 / dirLen);

    // 4. the round keeps the aircraft's own velocity
    vector bulletVel = dir * PROJECTILE_SPEED + GetVelocity(this);
    float bulletSpeed = bulletVel.Length();
    if (bulletSpeed < 0.1) return;
    vector axis = bulletVel * (1.0 / bulletSpeed);

    // 5. the tracer: no gravity, no damping, gone after 4 s
    EntityAI proj = EntityAI.Cast(GetGame().CreateObjectEx(PROJECTILE_CLASS, mw + axis, ECE_CREATEPHYSICS));
    if (proj)
    {
        dBodySetDamping(proj, 0, 0);
        dBodyEnableGravity(proj, false);
        proj.SetDirection(dir);
        InventoryItem ii = InventoryItem.Cast(proj);
        if (ii) ii.ThrowPhysically(null, bulletVel);
        SetVelocity(proj, bulletVel);
        proj.SetLifetime(4);
    }

    // 6. instant damage along a 1500 m ray
    vector hitPos;
    int hitComp;
    m_HitObjects.Clear();
    DayZPhysics.RaycastRV(mw, mw + axis * 1500, hitPos, null, hitComp, m_HitObjects, null, this, false, false, ObjIntersectFire);
    Object directHit = null;
    if (m_HitObjects.Count() > 0) directHit = m_HitObjects.Get(0);
    if (directHit && directHit.IsInherited(EntityAI))
    {
        string zone = ResolveDamageZone(directHit, hitComp);
        if (zone != "")
            directHit.ProcessDirectDamage(DamageType.FIRE_ARM, this, zone, AMMO_TYPE, directHit.WorldToModel(hitPos), 1.0, ProcessDirectDamageFlags.ALL_TRANSFER);
    }

    // 7. send the effects to every client
    ImpactEffectsData ie = new ImpactEffectsData();
    ie.m_DirectHit = directHit;
    ie.m_ComponentIndex = hitComp;
    ie.m_Surface = "Hit_Gravel";
    ie.m_Position = hitPos;
    ie.m_ImpactType = ImpactTypes.STOP;
    ie.m_AmmoType = AMMO_TYPE;
    ie.m_InSpeed = bulletVel;
    m_PlayerCache.Clear();
    GetGame().GetPlayers(m_PlayerCache);
    foreach (Man man : m_PlayerCache)
        GetGame().RPCSingleParam(this, MyMod_RPC.SYNC_SHOT_FX, new Param3<Object, ImpactEffectsData, vector>(directHit, ie, mw), true, man.GetIdentity());
}
```

The ray itself is vanilla: `DayZPhysics.RaycastRV` (`P:\scripts\3_game\global\dayzphysics.c:199`), and so is the damage call, `ProcessDirectDamage` (`P:\scripts\3_game\entities\object.c:1138`).

## Two guns, one after the other

`m_NextMuzzle` toggles between 0 and 1, and each shot takes the next pair of selections: `cannon_muz_1` and `cannon_dir_1`, then `cannon_muz_2` and `cannon_dir_2`. The model needs all four. The real Spitfire carried eight wing guns; the mod uses two that alternate. The same toggle works for any weapon with several mounts: chain guns, torpedo bays, rocket pods.

## Finding ammunition in cargo

```c
protected Magazine FindAmmoInCargo()
{
    m_AmmoSearchItems.Clear();
    GetInventory().EnumerateInventory(InventoryTraversalType.INORDER, m_AmmoSearchItems);
    foreach (EntityAI item : m_AmmoSearchItems)
    {
        if (!item) continue;
        string itemType = item.GetType();
        for (int i = 0; i < ALLOWED_AMMO.Count(); i++)
        {
            if (itemType == ALLOWED_AMMO[i])
            {
                Magazine mag = Magazine.Cast(item);
                if (mag && mag.GetAmmoCount() > 0) return mag;
            }
        }
    }
    return null;
}
```

It walks the vehicle's inventory and returns the first allowed stack that is not empty. The search array is a member, cleared each time, so a shot allocates nothing.

## Choosing a damage zone

```c
protected string ResolveDamageZone(Object hitObj, int componentIdx)
{
    string zone = hitObj.GetDamageZoneNameByComponentIndex(componentIdx);
    if (zone != "") return zone;
    if (hitObj.IsMan() || hitObj.IsInherited(DayZInfected)) return "Torso";
    if (hitObj.IsInherited(DayZCreatureAI)) return "Torso";
    m_DmgZoneCache.Clear();
    hitObj.GetDamageZones(m_DmgZoneCache);
    if (m_DmgZoneCache.Count() > 0) return m_DmgZoneCache[0];
    return ""; // nothing to damage
}
```

Try the component's own zone first, then `Torso` for players, infected and animals, then the target's first zone. Use the same chain wherever you call `ProcessDirectDamage` on whatever a ray hit. `GetDamageZoneNameByComponentIndex` and `GetDamageZones` are vanilla (`P:\scripts\3_game\entities\object.c:1164` and `:1153`).
