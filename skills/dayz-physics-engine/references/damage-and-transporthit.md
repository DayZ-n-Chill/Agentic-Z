# Damage system, hit zones, armor and `TransportHit`

Covers how damage flows from a source to the script callbacks, the calls that deal or read damage, the whole `RegisterTransportHit` flow line by line, hit zones and armor as vanilla configures them, bleeding, shock and hit animations, and a worked case (contact damage from a rolling stone).

Citations are `P:\...:line`, opened on `P:\` (a 1.30 build). `1.29:<path>:<line>` is a line in the 1.29 scripts, which are not on `P:\` and were not re-checked. `[UNVERIFIED]` marks what neither script nor config shows.

## Summary

The damage system (the Modular Damage Framework) runs mostly in native code with an Enforce Script layer on top. The flow is:

**damage source, then `ProcessDirectDamage` (native), then the native calculation with `CfgAmmo`, then `EEHitBy` (a script callback on the server), then the secondary effects (shock, blood, animation, bleeding).**

For an object that should hurt on contact, the path to copy is `TransportHit`. Either the object is a `Transport`, so the victim's own `EOnContact` registers the hit, or it calls `ProcessDirectDamage` with the `TransportHit` ammo from its own `EOnContact`. That gives damage in proportion to speed with no custom ammo in the mod's config.

## Verified API

### 1. `TotalDamageResult`

```c
// P:\scripts\3_game\damagesystem.c:1-5
class TotalDamageResult: Managed
{
    proto native float GetDamage(string zoneName, string healthType);
    proto native float GetHighestDamage(string healthType);
};
```

- `GetDamage("", "Health")`: total damage to the global zone, health type "Health".
- `GetDamage("Head", "Shock")`: shock damage to the "Head" zone.
- `GetHighestDamage("Health")`: the highest "Health" damage among all the zones hit.

### 2. The `DamageType` enum

```c
// P:\scripts\3_game\damagesystem.c:10-17
enum DamageType
{
    CLOSE_COMBAT,   // 0
    FIRE_ARM,       // 1
    EXPLOSION,
    STUN,
    CUSTOM
}
```

In mod scripts pass `DamageType.CLOSE_COMBAT`, `DamageType.FIRE_ARM`, `DamageType.EXPLOSION`, `DamageType.STUN` or `DamageType.CUSTOM`. `DT_CLOSE_COMBAT`, `DT_FIRE_ARM` and `DT_EXPLOSION` appear only in the doc comment of `ProcessDirectDamage` (`P:\scripts\3_game\entities\object.c:1130`); vanilla's `EntityAI.RegisterTransportHit` uses the engine's `DT_CUSTOM` (`P:\scripts\3_game\entities\entityai.c:4153`).

### 3. `ProcessDirectDamage`

```c
// P:\scripts\3_game\entities\object.c:1138
proto native void ProcessDirectDamage(
    int damageType,          // a DamageType value
    EntityAI source,         // the entity causing the damage
    string componentName,    // damage zone name (empty string is the global zone)
    string ammoName,         // the CfgAmmo class to apply
    vector modelPos,         // impact position in model space
    float damageCoef = 1.0,  // multiplier on the ammo's damage
    int flags = 0            // ProcessDirectDamageFlags
);
```

`ProcessDirectDamageFlags` (`P:\scripts\3_game\entities\object.c:1-7`):

- `ALL_TRANSFER`: damage transfers to attachments and to global (the default).
- `NO_ATTACHMENT_TRANSFER`: no transfer to attachments.
- `NO_GLOBAL_TRANSFER`: no transfer to global.
- `NO_TRANSFER`: both of the above.

`ProcessIndirectDamage` does not exist in script. Indirect damage (explosion radius) goes through `DamageSystem.ExplosionDamage`, which is native.

### 4. `DamageSystem` (static class)

```c
// P:\scripts\3_game\damagesystem.c:20-25
class DamageSystem
{
    static proto native void CloseCombatDamage(EntityAI source, Object targetObject,
        int targetComponentIndex, string ammoTypeName, vector worldPos,
        int directDamageFlags = ProcessDirectDamageFlags.ALL_TRANSFER);
    static proto native void CloseCombatDamageName(EntityAI source, Object targetObject,
        string targetComponentName, string ammoTypeName, vector worldPos,
        int directDamageFlags = ProcessDirectDamageFlags.ALL_TRANSFER);
    static proto native void ExplosionDamage(EntityAI source, Object directHitObject,
        string ammoTypeName, vector worldPos, int damageType);
    // plus script helpers: GetDamageZoneMap, GetDamageZoneFromComponentName, ResetAllZones
}
```

`ResetAllZones` sets Health, Shock and Blood to their maximum on every zone of an entity (`P:\scripts\3_game\damagesystem.c:138-153`).

### 5. Reading and setting health

All on `Object` (`P:\scripts\3_game\entities\object.c`):

| Function | Kind | Line | Notes |
|---|---|---|---|
| `IsDamageDestroyed()` | `proto native bool` | `:981` | True when health is 0 or less |
| `GetHealth(zone, type)` | `proto native float` | `:994` | Empty zone is global; empty type is the main health |
| `GetHealth01(zone, type)` | `proto native float` | `:1001` | Normalized 0 to 1 |
| `GetMaxHealth(zone, type)` | `proto native float` | `:1008` | The configured maximum |
| `SetHealth(zone, type, value)` | `proto native void` | `:1015` | Sets it directly |
| `AddHealth(zone, type, value)` | `proto native void` | `:1027` | Adds (a negative value subtracts) |
| `DecreaseHealth(zone, type, value)` | `proto native void` | `:1034` | Subtracts only |
| `SetHealthLevel(int level, zone)` | script helper | `:1087` | |
| `SetHealth01(zone, type, coef)` | script helper | `:1100` | `SetHealth(..., max * coef)` |
| `SetHealthMax(zone, type)` | script helper | `:1105` | `SetHealth` to the maximum |
| `GetHealthLevel(zone)` | `proto native int` | `:1171` | 0 pristine to 4 ruined |

The health types used in script are `"Health"`, `"Blood"` and `"Shock"`. The zone name `"GlobalHealth"` is the one vanilla script reads for the player's global health and blood, for example in `PlayerBase.GetImmunity` (`P:\scripts\4_world\entities\manbase\playerbase.c:5594-5599`).

### 6. `EEHitBy`: signature and chain

```c
// P:\scripts\3_game\entities\entityai.c:1143
void EEHitBy(
    TotalDamageResult damageResult,  // result of the native damage calculation
    int damageType,                  // a DamageType value
    EntityAI source,                 // who caused the damage
    int component,                   // index of the geometry component hit
    string dmgZone,                  // damage zone name (for example "Head", "Torso")
    string ammo,                     // the CfgAmmo class applied
    vector modelPos,                 // impact position in model space
    float speedCoef                  // speed coefficient (for projectiles)
)
```

Called on the server, after the native code has applied the damage. For a player the inheritance chain is `PlayerBase extends ManBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:49`), `ManBase extends DayZPlayerImplement` (`P:\scripts\4_world\entities\manbase.c:1`), down to `EntityAI`. Each override calls `super.EEHitBy` first, so the bodies run in this order:

1. `EntityAI.EEHitBy` invokes `m_OnHitByInvoker` (`P:\scripts\3_game\entities\entityai.c:1143-1146`).
2. `DayZPlayerImplement.EEHitBy` resets `m_TransportHitRegistered` and picks the damage or death animation (`P:\scripts\4_world\entities\dayzplayerimplement.c:1563-1607`).
3. `PlayerBase.EEHitBy` handles the admin log, the unconscious refill modifier, shock to damage transfer, broken legs and the shock check (`P:\scripts\4_world\entities\manbase\playerbase.c:1255-1376`).

Items take a separate branch: `ItemBase.EEHitBy` runs after `EntityAI.EEHitBy` and damages cargo or attachments at random, for clothing, containers and tents (`P:\scripts\4_world\entities\itembase.c:1450-1488`). `ItemBase` is not in the player's chain.

### 7. `EEHitByRemote`

```c
// P:\scripts\3_game\entities\entityai.c:1153
void EEHitByRemote(int damageType, EntityAI source, int component,
    string dmgZone, string ammo, vector modelPos)
```

"called only on the client who caused the hit", says the vanilla comment above `EEHitByRemote` (`P:\scripts\3_game\entities\entityai.c:1152`). It has no `TotalDamageResult`. `PlayerBase` uses it for local feedback, the melee block sound (`P:\scripts\4_world\entities\manbase\playerbase.c:1382-1391`).

### 8. `EEKilled`

```c
// P:\scripts\3_game\entities\entityai.c:1104
void EEKilled(Object killer)
```

Called on the server when the entity dies. It invokes `m_OnKilledInvoker` (`:1106-1107`). When `ReplaceOnDeath()` is true (`:1111`) it schedules `DeathUpdate()` with a delayed call.

### 9. `EEDelete`

```c
// P:\scripts\3_game\entities\entityai.c:946
void EEDelete(EntityAI parent)
```

Called when the entity is removed from the world (it also passes through the inventory).

### 10. `EEHealthLevelChanged` and `OnDamageDestroyed`

```c
// P:\scripts\3_game\entities\entityai.c:1043
void EEHealthLevelChanged(int oldLevel, int newLevel, string zone)
```

Called when the health level changes (0 pristine to 4 ruined). When `newLevel == GameConstants.STATE_RUINED` and `zone == ""` (the global zone) it calls `OnDamageDestroyed(oldLevel)`, and `AttemptDestructionBehaviour(...)` follows (`:1058`).

```c
// P:\scripts\3_game\entities\entityai.c:1066
void OnDamageDestroyed(int oldLevel);   // empty here; override it in your class
```

## The whole `TransportHit` flow

### Trigger: `EOnContact` in `DayZPlayerImplement`

```c
// P:\scripts\4_world\entities\dayzplayerimplement.c:3958-3974
override protected void EOnContact(IEntity other, Contact extra)
{
    if (!IsAlive()) return;
    if (GetParent() == other) return;

    Transport transport = Transport.Cast(other);
    if (transport)
    {
        if (g_Game.IsServer())
        {
            RegisterTransportHit(transport);
        }
    }
}
```

The key point: `EOnContact` reacts only to `Transport.Cast(other)`. If the entity that hits is not a `Transport` (and does not inherit from it), the player starts no `TransportHit` flow at all. For a stone that is an `ItemBase`, the player does not detect the collision; the stone must call `target.ProcessDirectDamage(...)` from its own `EOnContact`.

### `RegisterTransportHit`, line by line

```c
// P:\scripts\3_game\entities\entityai.c:4134-4224
void RegisterTransportHit(Transport transport)
{
    if (!m_TransportHitRegistered)
    {
        m_TransportHitRegistered = true;
        m_TransportHitVelocity = GetVelocity(transport);  // the Transport's velocity
```

- **Step 1.** `m_TransportHitRegistered` is a one shot guard: one hit per contact episode.
- **Step 2.** It captures the velocity of the `Transport`, not the player's.

#### Car branch (`:4147-4165`)

```c
        if (Car.CastTo(car, transport))
        {
            float carSpeed = car.GetSpeedometerAbsolute();
            if (carSpeed > 2.0)                             // minimum: 2 km/h
            {
                damage = m_TransportHitVelocity.Length();   // damage is the speed (m/s)
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;            // no damage when moving too slowly

            // compute impulse and apply only if the body dies
            if (IsDamageDestroyed() && carSpeed > 3.0)
            {
                impulse = 40 * m_TransportHitVelocity;
                impulse[1] = 40 * 1.5;                      // a large upward part
                dBodyApplyImpulse(this, impulse);
            }
        }
```

- **Car damage** is the length of the transport's velocity, in metres per second, passed to `ProcessDirectDamage` as `damageCoef`. At 30 km/h (about 8.3 m/s) the coefficient is about 8.3.
- **Ragdoll impulse:** only when the victim is already dead (`IsDamageDestroyed()`). Scaled by 40 in the horizontal plane, and 60 straight up.

#### Motorbike branch (`:4166-4184`, new in 1.30)

```c
// [EXACT] P:\scripts\3_game\entities\entityai.c:4166
			else if (Motorbike.CastTo(motorbike, transport))
			{
				float motorbikeSpeed = motorbike.GetSpeedometerAbsolute();
				if (motorbikeSpeed > 2.0)
				{
					damage = m_TransportHitVelocity.Length();
					ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
				}
				else
					m_TransportHitRegistered = false;

				// compute impulse and apply only if the body dies
				if (IsDamageDestroyed() && motorbikeSpeed > 3.0)
				{
					impulse = 5.0 * m_TransportHitVelocity;
					impulse[1] = 5.0;
					dBodyApplyImpulse(this, impulse);
				}
			}
```

Damage as for a car above 2.0 on the speedometer. The corpse impulse is `5.0 * velocity` with 5.0 straight up, not 40 and 60. Authoring that Motorbike type belongs to the vehicle skills.

#### Boat branch (`:4185-4201`)

```c
        else if (Boat.CastTo(boat, transport))
        {
            Human player = Human.Cast(this);
            if (player && player.PhysicsGetLinkedEntity() == boat)   // standing on the boat: not a real collision
            {
                m_TransportHitRegistered = false;
                return;
            }
            if (m_TransportHitVelocity.Normalize() > 5)     // more than 5 m/s (Normalize returns the original length and leaves the vector at length 1)
            {
                damage = m_TransportHitVelocity.Length() * 0.5;  // always 1 * 0.5 = 0.5, whatever the speed
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;
        }
```

#### Generic branch, any other `Transport` (`:4202-4222`)

```c
        else //old solution just in case if somebody use it
        {
            if (m_TransportHitVelocity.Length() > 0.1)       // minimum: 0.1 m/s
            {
                damage = m_TransportHitVelocity.Length();
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;

            if (IsDamageDestroyed() && m_TransportHitVelocity.Length() > 0.3)
            {
                impulse = 40 * m_TransportHitVelocity;
                impulse[1] = 40 * 1.5;
                dBodyApplyImpulse(this, impulse);
            }
        }
    }
}
```

The generic branch has the lowest threshold (0.1 m/s). Any class that inherits from `Transport` without being a `Car`, a `Motorbike` or a `Boat` lands here. In 1.29 the function ran from line 4089 to 4156 and had no Motorbike branch (`1.29:3_game\entities\entityai.c:4089-4156`).

### Resetting `m_TransportHitRegistered`

The flag is reset in `DayZPlayerImplement.EEHitBy` (`P:\scripts\4_world\entities\dayzplayerimplement.c:1567`):

```c
m_TransportHitRegistered = false;
```

That lets the victim take further transport hits in later physics frames.

### What `ProcessDirectDamage` does with `"TransportHit"`

`ProcessDirectDamage(DT_CUSTOM, source, "", "TransportHit", "0 0 0", damage)` calls native code that:

1. Looks up `CfgAmmo` `TransportHit`.
2. Multiplies the ammo's damage values by `damageCoef` (the speed in m/s).
3. Applies them to the zones of the entity's `DamageSystem`.
4. Fires `EEHitBy` on the target.

The ammo class is in the game's config, not in script: `class TransportHit: MeleeDamage` (`P:\DZ\weapons\melee\config.cpp:52-72`) sets `hitAnimation=1`, `doPhxImpulse=1` and a `DamageApplied` of type `"TransportHit"` with `Health` damage 1, `Blood` 0 and `Shock` 0. So the health damage before armor is the speed in m/s: 10 m/s gives 10.

### In `DayZPlayerImplement.EEHitBy` after a `TransportHit`

```c
// P:\scripts\4_world\entities\dayzplayerimplement.c:1563-1607 (condensed)
override void EEHitBy(..., string ammo, ...)
{
    super.EEHitBy(...);              // EntityAI.EEHitBy (m_OnHitByInvoker); PlayerBase.EEHitBy runs after this override returns
    m_TransportHitRegistered = false; // allows a new hit

    if (!IsAlive())
    {
        // death animation and ragdoll
        EvaluateDeathAnimation(...);
        SendDeathJuncture(...);
    }
    else
    {
        // hit animation: DamageType.CUSTOM with hitAnimation == 1 gives a full body animation
        EvaluateDamageHitAnimation(...);
        DayZPlayerSyncJunctures.SendDamageHitEx(...);
    }
}
```

For `DamageType.CUSTOM` with the ammo `"TransportHit"`, `hitAnimation` is 1 in the config above, so `pAnimHitFullbody` becomes true and the living player plays a full body hit animation.

## Config `DamageZones`

The structure in `CfgVehicles`:

```
class MyCar : Transport
{
    class DamageSystem
    {
        class DamageZones
        {
            class Engine
            {
                componentNames[] = {"engine_comp"};
                transferToZonesNames[] = {"Body"};
                transferToZonesCoefs[] = {0.5};
                class Health
                {
                    hitpoints = 500;
                    transferToGlobalCoef = 0.08;
                };
            };
        };
    };
};
```

The parts of a zone:

- `componentNames[]`: the names of the model selections that map to this zone.
- `transferToZonesNames[]` and `transferToZonesCoefs[]`: what share of the damage passes to other zones.
- `transferToGlobalCoef`: the share that goes to global health. `RepairDamageTransfer` reads it (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairtent.c:167`).
- `fatalInjuryCoef`: vanilla sets it per zone, for example 0.1 on the player's `Head` and 1 on `Brain` (`P:\DZ\characters\data\config.cpp:492` and `:570`). No vanilla script reads it (0 matches in `P:\scripts`), so what the engine does with it is `[UNVERIFIED]`; the likely reading is that a zone at 0 health with a coefficient above 0 kills or destroys the object.

`GlobalHealth` is the zone name vanilla script reads for the player's global health and blood, as in `GetHealth("GlobalHealth", "Blood")` in `PlayerBase.GetImmunity` (`P:\scripts\4_world\entities\manbase\playerbase.c:5599`), `PlayerBase.GetHealthRegenSpeed` (`:6594`) and the server bleeding manager (`P:\scripts\4_world\classes\bleedingsources\bleedingsourcesmanagerserver.c:143`).

Health states (`GameConstants.STATE_RUINED` down to `STATE_PRISTINE`, `P:\scripts\3_game\constants.c:909-913`):

| Constant | Value | Meaning |
|---|---|---|
| `STATE_PRISTINE` | 0 | Pristine |
| `STATE_WORN` | 1 | Worn |
| `STATE_DAMAGED` | 2 | Damaged |
| `STATE_BADLY_DAMAGED` | 3 | Badly damaged |
| `STATE_RUINED` | 4 | Ruined, 0 health |

## Armor and clothing

### `GetProtectionLevel` is not armor

```c
// P:\scripts\4_world\entities\itembase.c:4073
float GetProtectionLevel(int type, bool consider_filter = false, int system = 0)
```

This `ItemBase` function returns the environmental hazard protection of masks and filters, not the absorption of weapon damage. Its types are `DEF_BIOLOGICAL`, `DEF_CHEMICAL`, `DEF_DUST_PARTICLE_BREATH` and `DEF_DUST_PARTICLE_EYES` (`:4082`, `:4085`, `:4088` and `:4091`), read from the entries `biological`, `chemical`, `dust_particle_breath` and `dust_particle_eyes` of the item's `Protection` config class (`:4099-4101`). Any other type falls back to `biological`.

### How absorption of weapon damage works

The reduction of damage by clothing is done in native code from config. In script, what you see afterwards is:

1. `ItemBase.EEHitBy`, where the equipped item gets the callback:

   ```c
   // P:\scripts\4_world\entities\itembase.c:1450-1488 (condensed)
   override void EEHitBy(TotalDamageResult damageResult, ...)
   {
       super.EEHitBy(...);
       if (IsClothing() || IsContainer() || IsItemTent())
       {
           float dmg = damageResult.GetDamage("","Health") * -0.5;
           // damages cargo or an attachment at random
           DamageItemInCargo(dmg);    // or
           DamageItemAttachments(dmg);
       }
   }
   ```

   Equipped clothing wears when the player takes damage: half of the health damage goes to cargo or an attachment. The reduction of the damage to the player does not happen in script; it happens in native code before `EEHitBy` arrives.

2. The armor values themselves are config. A wearable sets `GlobalArmor` inside its `DamageSystem`, one class per damage source; the wearables pack has the keys and vanilla values (`skills/_shared/wearables/references/protection-and-insulation.md`). The player's own zones carry an `ArmorType` class each (`P:\DZ\characters\data\config.cpp:440`). There is no `armorLevels` key in the vanilla vest or headgear config (0 matches in `P:\DZ\characters\vests\config.cpp` and `P:\DZ\characters\headgear\config.cpp`).

### `BallisticHelmet` is only a class

```c
// P:\scripts\4_world\entities\itembase\clothing\helmetbase\ballistichelmet_colorbase.c:1
class BallisticHelmet_ColorBase extends HelmetBase
```

It has no script override that matters. All its protection is config.

## Player hit zones

The player's zones are configured in `class DamageZones` at `P:\DZ\characters\data\config.cpp:421`: `Head` (`:423`), `Brain` (`:501`), `Torso` (`:572`), `LeftArm` (`:625`), `RightArm` (`:671`), `LeftHand` (`:717`), `LeftLeg` (`:782`), `LeftFoot` (`:838`) and their right side twins. Each lists its `componentNames[]` (for the head, `"dmgZone_head"`, `:488-491`).

Where script uses the names:

| Zone | Use in script |
|---|---|
| `"Head"` | With `"Torso"`, picks the full body hit animation (`P:\scripts\4_world\entities\dayzplayerimplement.c:1512`) |
| `"Brain"` | The head sub zone that marks a headshot kill (`P:\scripts\4_world\entities\dayzplayerimplement.c:1592`) |
| `"Torso"` | Full body animation component (`P:\scripts\4_world\entities\dayzplayerimplement.c:1512`) |
| `"LeftArm"` | An upper bleeding source (`P:\scripts\4_world\entities\manbase\playerbase.c:549`) |
| `"RightArm"` | An upper bleeding source (`P:\scripts\4_world\entities\manbase\playerbase.c:545`) |
| `"LeftLeg"`, `"RightLeg"`, `"LeftFoot"`, `"RightFoot"` | The broken legs check (`P:\scripts\4_world\entities\manbase\playerbase.c:1324`) |
| `""` (empty) | The global zone |
| `"GlobalHealth"` | The player's global health and blood (`P:\scripts\4_world\entities\manbase\playerbase.c:5594-5599`) |

## Bleeding sources

```c
// P:\scripts\4_world\entities\manbase\playerbase.c:85-86
ref BleedingSourcesManagerServer m_BleedingManagerServer;
ref BleedingSourcesManagerRemote m_BleedingManagerRemote;
```

The bleeding flow (`ProcessHit`, `P:\scripts\4_world\classes\bleedingsources\bleedingsourcesmanagerserver.c:167-177`):

1. `PlayerBase.EEHitBy` calls `GetBleedingManagerServer().ProcessHit(dmg, source, component, dmgZone, ammo, modelPos)` (`P:\scripts\4_world\entities\manbase\playerbase.c:1292`).
2. `ProcessHit` reads `CfgAmmo <ammo> DamageApplied bleedThreshold` (a float from 0 to 1, `P:\scripts\4_world\classes\bleedingsources\bleedingsourcesmanagerserver.c:170`).
3. It reads the ammo's `DamageApplied type` string (`P:\scripts\4_world\classes\bleedingsources\bleedingsourcesmanagerserver.c:171`) and asks `BleedChanceData.CalculateBleedChance` (`:177`).
4. When the chance passes, it creates a `BleedingSource` in the matching zone.

A bleeding source has a type, `eBleedingSourceType` (`P:\scripts\4_world\classes\bleedingsources\bleedingsource.c:1`), and is mapped to bones and positions of the player's skeleton.

## Shock and unconsciousness

```c
// P:\scripts\4_world\classes\shockhandler.c
class ShockHandler                      // :1
{
    void Update(float deltaT);          // :44
    float GetCurrentShock();            // :82   the current shock (player.m_CurrentShock)
    void SetShock(float dealtShock);    // :92   adds shock
    void CheckValue(bool forceUpdate);  // :106  applies and syncs when over the threshold
}
```

The flow:

1. "Shock" damage arrives through `ProcessDirectDamage`; the native code applies it to the player's Shock health.
2. `PlayerBase.EEHitBy` calls `m_ShockHandler.CheckValue(true)`, which forces a sync (`P:\scripts\4_world\entities\manbase\playerbase.c:1376`).
3. When `CfgAmmo <ammo> DamageApplied transferShockToDamage` is 1, shock is turned into extra Health damage, as for less lethal weapons (`P:\scripts\4_world\entities\manbase\playerbase.c:1313-1314`).
4. `ShockHandler.Update()` runs each tick and calls `CheckValue` on its interval.
5. Unconsciousness is run by the player's command handler (`m_ShouldBeUnconscious`, `P:\scripts\4_world\entities\dayzplayerimplement.c:125`; used at `P:\scripts\4_world\entities\manbase\playerbase.c:3355`).

`GiveShock(float shock)` is `AddHealth("","Shock",shock)` (`P:\scripts\4_world\entities\manbase\playerbase.c:3947-3949`); a negative value drains shock.

## Hit animation flow (`DayZPlayerImplement`)

```c
// P:\scripts\4_world\entities\dayzplayerimplement.c:1485 (condensed)
bool EvaluateDamageHitAnimation(TotalDamageResult, int pDamageType, ...)
{
    switch (pDamageType)
    {
        case DamageType.CLOSE_COMBAT:  // reads cfgAmmo hitAnimation (:1500)
        case DamageType.FIRE_ARM:      // full body for Torso or Head with enough damage (:1512)
        case DamageType.EXPLOSION:     // no special animation
        case DamageType.CUSTOM:
            // hitAnimation == 1: full body (:1528)
            // otherwise, when the ammo is not "HeatDamage", or the player swims or is in a vehicle: return false, no animation (:1531)
    }
}
```

For `DamageType.CUSTOM` with the ammo `"TransportHit"`, `hitAnimation` is 1 (`P:\DZ\weapons\melee\config.cpp:54`), so the full body animation plays. A custom ammo with 0, or with no `hitAnimation`, plays no impact animation.

## Patterns

### Script damage to an entity, with no custom ammo

```c
// Most direct: DecreaseHealth, which skips the ammo system
target.DecreaseHealth("", "", 50.0); // 50 damage to the global zone

// For one zone:
target.DecreaseHealth("LeftLeg", "Health", 25.0);

// To go through the whole pipeline (EEHitBy, animations, bleeding):
target.ProcessDirectDamage(DamageType.CUSTOM, sourceEntity, "", "TransportHit", "0 0 0", damageCoef);
```

### Area damage (trigger zones)

```c
// P:\scripts\4_world\classes\areadamage\ : the default ammo is "MeleeDamage" (areadamage.c:30,
// areadamagenew\damagecomponents\areadamagecomponent.c:21)
object.ProcessDirectDamage(m_DamageType, m_Parent.GetParentObject(),
    data.Hitzone, m_AmmoName, data.Modelpos, damageCoef);
```

### `ExplosionDamage`

```c
// P:\scripts\3_game\damagesystem.c:25
DamageSystem.ExplosionDamage(EntityAI source, Object directHitObject,
    string ammoTypeName, vector worldPos, int damageType);
```

A vanilla use (`P:\scripts\3_game\dayzgame.c:3781`):

```c
DamageSystem.ExplosionDamage(EntityAI.Cast(source), null,
    "Explosion_40mm_Ammo", pos, DamageType.EXPLOSION);
```

With `directHitObject == null` the system applies damage in the radius the ammo defines. Destructibles use `DestructionEffectBase.DealExplosionDamage()`, which calls it (`P:\scripts\3_game\effects\destructioneffects\destructioneffectbase.c:50-52`).

### `DealAbsoluteDmg` (script helper)

```c
// P:\scripts\4_world\static\miscgameplayfunctions.c:1730
static void DealAbsoluteDmg(ItemBase item, float dmg)
{
    item.DecreaseHealth(dmg, false);  // false: no automatic delete
}
```

A helper for tools that wear with use. It skips the ammo system.

## Gotchas

1. **`TransportHit` from the victim's side needs a `Transport`.** The player's `EOnContact` registers a hit only when `Transport.Cast(other)` succeeds. An `ItemBase` is an `EntityAI`, not a `Transport`. A stone must call `target.ProcessDirectDamage(...)` from its own `EOnContact`.
2. **`m_TransportHitRegistered` is a guard per contact episode.** It allows one hit, and is reset in `EEHitBy`, not every frame. An object that calls `ProcessDirectDamage` itself has no such guard and can fire several times in one tick when the contact flickers.
3. **`damageCoef` in `ProcessDirectDamage` is the speed.** In `RegisterTransportHit`, `damage = velocity.Length()` is passed as `damageCoef`. The damage is the `TransportHit` base damage times that: with the vanilla base of 1 Health (`P:\DZ\weapons\melee\config.cpp:61`), 10 m/s gives 10.
4. **The ragdoll impulse comes only after death.** `dBodyApplyImpulse` in `RegisterTransportHit` runs only when `IsDamageDestroyed()`. A living player is pushed by the physics solver itself when two bodies touch; vanilla has no script call for that.
5. **`GetProtectionLevel` is for hazard protection only.** It does not measure armor. Armor values are config, applied in native code.
6. **`DamageType.STUN`** exists in the enum, and the only vanilla script that names it marks it "unused atm" (`P:\scripts\4_world\plugins\pluginbase\pluginadminlog.c:293`).
7. **`EEHitBy` is server only.** Logic placed in `EEHitBy` runs on the server whether or not you guard it. `EEHitByRemote` is the counterpart on the client that caused the hit.
8. **`componentName` in `ProcessDirectDamage` is not a model component name.** It is the damage zone name (for example "Head" or "Engine"). The vanilla doc comment says so: "which 'DamageZone' was hit (NOT a component name, actually!)" (`P:\scripts\3_game\entities\object.c:1132`).
9. **A boat deals a fixed 0.5, not half the speed.** The Boat branch tests `m_TransportHitVelocity.Normalize() > 5` (`P:\scripts\3_game\entities\entityai.c:4194`). `Normalize` scales the member vector to length 1 in place and returns the original length (`P:\scripts\1_core\proto\enconvert.c:140-153`), so the next line, `m_TransportHitVelocity.Length() * 0.5` (`:4196`; `1.29:3_game\entities\entityai.c:4129`), is always 0.5. Any boat hit above 5 m/s passes a coefficient of 0.5, which is 0.5 Health with `TransportHit`. The car and generic branches scale with the speed.
10. **`"Brain"` is a real zone.** It is configured on the player (`P:\DZ\characters\data\config.cpp:501`) with `fatalInjuryCoef=1` (`:570`), and script checks `dmgZone == "Brain"` to mark a headshot kill (`P:\scripts\4_world\entities\dayzplayerimplement.c:1592`).

## What does not exist

- **`ProcessIndirectDamage` on `EntityAI` or `Object`.** Not a script function. Indirect explosion damage is native, through `DamageSystem.ExplosionDamage`.
- **`DealDamage` as a global script function.** The names are `ProcessDirectDamage` (on `Object`) and `DealAbsoluteDmg` (a helper in `MiscGameplayFunctions`).
- **`"TransportHit"` in script.** It is a `CfgAmmo` class in the game config (`P:\DZ\weapons\melee\config.cpp:52`). To copy the flow, a mod uses that ammo name, which the base game already has, or defines its own in `config.cpp`.
- **`GetProtectionLevel` for armor.** The function exists but covers only the hazard types `DEF_BIOLOGICAL`, `DEF_CHEMICAL`, `DEF_DUST_PARTICLE_BREATH` and `DEF_DUST_PARTICLE_EYES`.
- **Hit zones defined in script.** The `componentNames[]` of the player's zones are config, in `class DamageZones` (`P:\DZ\characters\data\config.cpp:421` onward).
- **A getter for `ShockHandler`.** `PlayerBase` holds `m_ShockHandler` and `m_BleedingManagerServer` as plain `ref` members (`P:\scripts\4_world\entities\manbase\playerbase.c:99` and `:85`). The bleeding manager has the getter `GetBleedingManagerServer()` (`:2973`); the shock handler has none.
- **A script read of `fatalInjuryCoef`.** `RepairDamageTransfer` carries the comment "hack; mirrors" (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairtent.c:155`) and reads only `transferToGlobalCoef`. The key is read by native code.

## Worked case: contact damage from a rolling stone

### Pushing, and damage like a vehicle hit

The stone's code calls `ProcessDirectDamage(DamageType.CUSTOM, source, "", "TransportHit", ...)` from its `EOnContact`. The idea is right:

- `DamageType.CUSTOM` with the ammo `"TransportHit"`: the engine finds that ammo, which the base game has.
- `damageCoef` is the speed, so damage follows speed.
- The player's `EEHitBy` fires as usual, with the hit animation.

The activation problem: the player does not see the stone as a `Transport`, so it is the stone's `EOnContact` that fires (the stone inherits `ItemBase`), not the player's. From the stone's `EOnContact` the target can be a player:

```c
// In the stone's EOnContact:
override void EOnContact(IEntity other, Contact extra)
{
    if (!g_Game.IsServer()) return;
    EntityAI target = EntityAI.Cast(other);
    if (target && target.IsAlive())
    {
        float speed = GetVelocity(this).Length(); // the speed of the stone
        if (speed > 0.5) // minimum threshold
        {
            target.ProcessDirectDamage(DamageType.CUSTOM, this, "",
                "TransportHit", "0 0 0", speed);
        }
    }
}
```

### Pushing living players

The ragdoll impulse of `RegisterTransportHit` goes only to corpses. A living player is moved by the physics solver when the stone's body and the player's controller both exist on that machine and their layers interact.

One more idea is to push a living player from script on the server:

```c
if (target.IsAlive() && speed > 1.0)
{
    vector impulse = GetVelocity(this) * 20; // scale by mass
    impulse[1] = Math.Max(impulse[1], 5.0);  // a minimum upward part
    dBodyApplyImpulse(target, impulse);
}
```

Treat that as untested for a player who is standing and controlled. Vanilla never does it, and the in-game measurement (`SKILL.md`, "`PhysicsSetRagdoll` on a live player") shows an impulse taking on a live player only after `PhysicsSetRagdoll(true)` on the server, with the owner client not following. Prefer letting the contact solver do the push.

### A guard against several hits

Without a guard like `m_TransportHitRegistered`, `EOnContact` can fire several times in one physics frame when there are several contact points. Use a bool that is reset in `EEHitBy`, or a time cooldown.

### Hit animation

The player shows a hit animation from `TransportHit` because that ammo has `hitAnimation=1`. A custom ammo (for example "MyMod_StoneHit") has to be defined in the mod's `config.cpp`:

```cpp
class CfgAmmo {
    class MyMod_StoneHit {
        hitAnimation = 1;  // full body
        // DamageApplied { Health { damage = 1; }; Shock { damage = 0.5; }; Blood { damage = 0.3; }; }
    };
};
```

## Fall damage in 1.30

Fall damage is a separate path from `TransportHit` (the `Transport` only `EOnContact` has nothing to do with falls).

- Up to 1.29: `HEALTH_HEIGHT_LOW = 5`, `HEALTH_HEIGHT_HIGH = 14`, `SHOCK_HEIGHT_LOW = 3`, `SHOCK_HEIGHT_HIGH = 12`, `BROKENLEGS_HEIGHT_LOW = 5`, `BROKENLEGS_HEIGHT_HIGH = 9`, and `HandleFallDamage` used `Math.InverseLerp` (`1.29:4_world\entities\dayzplayerimplementfalldamage.c:26-32`, and line 97 of the same file).
- From 1.30: health from 2 to 12 m, shock from 0 to 8 m, broken legs from 3 to 8 m (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:26-32`). `CurveExp` is `Pow(Clamp(InverseLerp(low, high, value), 0, 1), power)` (`:92-97`), with power 2.0 for health and shock and 2.5 for broken legs (`:104-112`). `Randomize` returns a value of 1 unchanged (`:160-163`).

The full ragdoll and fall damage detail is in `ragdoll-and-fall-damage.md`.

## Vanilla files

The vanilla files cited above:

| File | What it holds |
|---|---|
| `P:\scripts\3_game\damagesystem.c` | `TotalDamageResult`, `DamageType`, `DamageSystem` |
| `P:\scripts\3_game\entities\object.c` | `ProcessDirectDamage`, the health calls, `IsDamageDestroyed`, `GetHealthLevel`, `ProcessDirectDamageFlags` |
| `P:\scripts\3_game\entities\entityai.c` | `EEHitBy`, `EEHitByRemote`, `EEKilled`, `EEDelete`, `EEHealthLevelChanged`, `OnDamageDestroyed`, `RegisterTransportHit` |
| `P:\scripts\4_world\entities\dayzplayerimplement.c` | `EOnContact`, `EEHitBy`, `EvaluateDamageHitAnimation` |
| `P:\scripts\4_world\entities\manbase\playerbase.c` | `EEHitBy`, the bleeding manager, `ShockHandler`, `GiveShock`, the leg zones |
| `P:\scripts\4_world\entities\itembase.c` | `EEHitBy` for clothing, `GetProtectionLevel` |
| `P:\scripts\4_world\classes\shockhandler.c` | `ShockHandler` |
| `P:\scripts\4_world\classes\bleedingsources\bleedingsourcesmanagerserver.c` | `ProcessHit` |
| `P:\scripts\4_world\entities\vehicles\carscript.c` | `CheckContactCache`, `m_dmgContactCoef` |
| `P:\scripts\3_game\effects\destructioneffects\destructioneffectbase.c` | `DealExplosionDamage`, `HasExplosionDamage` |
| `P:\scripts\4_world\classes\areadamage\areadamagenew\damagecomponents\areadamagecomponent.c` | `AreaDamageComponent` |
| `P:\scripts\3_game\constants.c` | `STATE_PRISTINE` to `STATE_RUINED` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c` | The `UADamageApplied` constants (`:149-159`) |
| `P:\scripts\4_world\static\miscgameplayfunctions.c` | `DealAbsoluteDmg` |
| `P:\DZ\weapons\melee\config.cpp` | The `TransportHit`, `EnviroDmg` and fall damage ammo classes |
| `P:\DZ\characters\data\config.cpp` | The player's `DamageZones` |
