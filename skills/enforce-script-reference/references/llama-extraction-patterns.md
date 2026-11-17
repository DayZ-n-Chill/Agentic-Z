# Mod structure, input, RPC and performance patterns

Enforce Script and config patterns for structuring a mod and scripting vehicles. The first part covers `CfgMods`, custom inputs, the `CfgSoundSets` parameters, buildings and performance. The second part covers custom RPC enums, server-authoritative input, broadcast, cleanup hooks, vanilla helpers, the vehicle anim instance and the parent and child mod architecture. These are third-party mod patterns, not vanilla code, and are not yet checked on `P:\` unless a line cites a vanilla file. The aviation uses are in the `dayz-aviation` skill.

---

## Config, input, building and performance patterns

General Enforce Script and DayZ patterns that apply beyond aviation.

### CfgMods config patterns

**Hide a mod from the in-game menu** (useful for libraries / non-user-facing mods):

```cpp
class CfgMods {
    class MyLib {
        dir = "MyLib";
        picture = "";
        action = "";
        hideName = 1;       // Hide from mod list
        hidePicture = 1;    // Hide picture slot
        name = "";          // Empty display name
        credits = "...";
        author = "...";
        version = "1.0";
        extra = 0;
        type = "mod";
        dependencies[] = {"Game","World","Mission"};
        // gameScriptModule + worldScriptModule as usual
    };
};
```

**Sub-mod `class defs` wrapper** — when one mod has child mods (e.g. parent + per-feature sub-mods), the child CfgMods entries wrap their script-module loaders in `class defs`:

```cpp
// Root mod (parent): script modules directly under CfgMods.<Mod>
class CfgMods {
    class MyParentMod {
        ...
        class gameScriptModule { files[] = {"MyParentMod/scripts/3_Game"}; };
        class worldScriptModule { files[] = {"MyParentMod/scripts/4_World"}; };
    };
};

// Sub-mod (child): wrapped in class defs
class CfgMods {
    class MyParentMod_FeatureX {
        ...
        class defs {
            class gameScriptModule { files[] = {"MyParentMod/scripts/3_Game"}; };
            class worldScriptModule { files[] = {"MyParentMod/scripts/4_World"}; };
        };
    };
};
```

The child mod's `CfgPatches` must require the parent (`requiredAddons[] = {"...", "ParentMod"}`). Without the `class defs` wrapper, sub-mod script modules don't register.

### Custom inputs registration (modded_inputs XML)

`scripts/data/Inputs.xml`:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<modded_inputs>
    <inputs>
        <actions>
            <input name="UAMyModAction1" loc="mymod_action1_loc"/>
            <input name="UAMyModAction2" loc="mymod_action2_loc"/>
        </actions>
        <sorting name="mymod" loc="mymod_controls_category">
            <input name="UAMyModAction1"/>
            <input name="UAMyModAction2"/>
        </sorting>
        <exclude name="MyMod_Controls">
            <input name="UAMyModAction1"/>
        </exclude>
    </inputs>
    <preset>
        <input name="UAMyModAction1">
            <btn name="kSpace"/>           <!-- keyboard: k prefix -->
            <btn name="x1A"/>              <!-- xbox: x1 prefix -->
        </input>
    </preset>
</modded_inputs>
```

Reference from `config.cpp`:

```cpp
class CfgMods {
    class MyMod {
        inputs = "MyMod/scripts/data/Inputs.xml";
        ...
    };
};
```

**Sections**:
- `<actions>` declares inputs + stringtable loc keys
- `<sorting>` groups inputs under a category for the in-game keybind menu
- `<exclude>` marks inputs as excluded from default vanilla binding conflicts
- `<preset>` assigns default bindings (one or more `<btn>` per input)

**Naming conventions**:
- Input names always `UA` prefix (User Action): `UAMyModFire`, `UAMyModInteract`
- Keyboard button prefix: `k` → `kSpace`, `kLShift`, `kLControl`, `kLMenu`, `kW`, `kA`, etc.
- Xbox controller prefix: `x1` → `x1A`, `x1B`, `x1ShoulderLeft/Right`, `x1TriggerLeft/Right`, `x1LeftThumbUp/Down/Left/Right`, `x1ThumbLeft/Right` (thumbstick click), `x1RightThumbUp/...`

**Standard category bindings** (avoid conflicts with vanilla):
- WASD: movement (avoid for non-movement features)
- Q/E: lean (avoid)
- Mouse: aim/look (avoid)
- F: pickup/interact (avoid hijacking)
- LShift/LCtrl: sprint/crouch (avoid)
- Space: jump (avoid)
- Available: G, H, J, K, V, B, N, M, function keys F1-F12, numpad
- LeftAlt: free look toggle (used by some mods)

### CfgSoundSets parameters reference

```cpp
class baseEngine_EXT_SoundSet
{
    sound3DProcessingType = "Vehicle_Ext_3DProcessingType";  // or character3DProcessingType, WeaponMediumShot3DProcessingType
    distanceFilter        = "softVehiclesDistanceFreqAttenuationFilter";  // or weaponShotDistanceFreqAttenuationFilter
    volumeCurve           = "vehicleEngineAttenuationCurve";  // or characterAttenuationCurve, RifleShotCurve
    volumeFactor          = 1;        // multiplier
    occlusionFactor       = 0;        // 0-1 geometry blocking attenuation
    obstructionFactor     = 0;        // 0-1 obstacle attenuation
    spatial               = 1;        // 1 = 3D positioned
    loop                  = 1;        // 0/1
    doppler               = 0;        // 0/1 enable doppler effect
    positionOffset[]      = {0,0,0.3}; // Vec3 offset relative to owner
    soundShaders[]        = {"<shader1>","<shader2>"};  // array of SoundShader refs
    soundShadersLimit     = 2;        // concurrency cap (weapons)
    soundObjectsLimit     = 2;        // global concurrency cap (weapons)
};
```

### Buildings: class Doors pattern

For static structures (HouseNoDestruct base) with animated doors:

```cpp
class land_MyBuilding: HouseNoDestruct
{
    scope = 1;          // 1 = script/terrain only (not in public lists/tools that filter by scope 2), 2 = public
    model = "MyMod\MyBuilding\MyBuilding.p3d";
    class Doors
    {
        class Door1_Open
        {
            displayName = "Door 1";
            component   = "door1_open";    // selection name in model
            soundPos    = "door1_action";  // memory point for sound origin
            animPeriod  = 8.0;             // seconds to open/close (large doors = longer)
            initPhase   = 0;
            initOpened  = 0.0;             // 0 = starts closed, 1 = starts open
            soundOpen      = "doorMetalSmallOpen";
            soundClose     = "doorMetalSmallClose";
            soundLocked    = "doorMetalSmallRattle";
            soundOpenABit  = "doorMetalSmallOpenABit";
        };
    };
};
```

Standard vanilla door sound classes: `doorMetalSmall*`, `doorWoodenSmall*`, `doorMetalLarge*`. Pick by door size/material.

### Buildings: damage isolation pattern (immortal building, damageable doors)

Lets specific components take damage without the whole building dying:

```cpp
class DamageSystem
{
    class GlobalHealth {
        class Health { hitpoints = 10000; };
    };
    class GlobalArmor {
        // Building is bulletproof / immune globally
        class Projectile { class Health { damage = 0; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
        class Melee      { class Health { damage = 0; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
    };
    class DamageZones {
        class Door1 {
            class Health {
                hitpoints = 10000;
                transferToGlobalCoef = 0;  // !!! KEY: door damage does NOT propagate to building global
            };
            componentNames[] = {"door1"};
            fatalInjuryCoef = -1;
            class ArmorType {
                // Door-specific armor: ALLOWS damage
                class Projectile { class Health { damage = 2; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
                class Melee      { class Health { damage = 2.5; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
            };
        };
    };
};
```

The trick is the combo: `GlobalArmor` blocks all damage to the building itself, while `DamageZones.<Zone>.ArmorType` allows damage to specific components. `transferToGlobalCoef=0` prevents the component damage from bubbling up.

### Performance optimization patterns

**Animation phase delta cache** — skip engine calls if value barely changed:

```cpp
protected float m_LastPitchAnim = -999.0;
protected const float ANIM_THRESHOLD = 0.015;

protected void UpdateAnim()
{
    float newPhase = ComputePhase();
    if (Math.AbsFloat(newPhase - m_LastPitchAnim) >= ANIM_THRESHOLD) {
        SetAnimationPhase("my_anim_source", newPhase);
        m_LastPitchAnim = newPhase;
    }
}
```

`SetAnimationPhase` is an engine call. For animations that change smoothly (dials, slow rotations), cutting calls below threshold saves significant CPU. Threshold of 0.015 means ~67 distinct values across [0,1] range — visually indistinguishable from continuous.

**Adaptive update rate** — different timing for different work:

```cpp
protected float m_DialUpdateTimer = 0.0;
protected const float DIAL_UPDATE_INTERVAL = 0.1;  // 10Hz

override void EOnPostSimulate(IEntity other, float dt)
{
    m_DialUpdateTimer += dt;
    if (m_DialUpdateTimer >= DIAL_UPDATE_INTERVAL) {
        UpdateAllDials();
        m_DialUpdateTimer = 0;
    }
    // Physics still runs every tick — only visual UI throttled
}

// For network sync with active/idle split:
protected float GetSyncInterval()      { return 0.033; }  // 30Hz when active
protected float GetSyncIntervalIdle()  { return 0.1; }    // 10Hz when no input
```

Human eye doesn't perceive UI refresh >10-15Hz. Physics needs full tick rate, but dials/HUD/cosmetic anims can be 5-10x cheaper without visual difference.

**Idle damping for vehicles without driver**:

```cpp
protected const float IDLE_DAMPING_FACTOR = 0.92;

protected void ApplyIdleDamping()
{
    vector angVel = dBodyGetAngularVelocity(this);
    float angMagSq = angVel[0]*angVel[0] + angVel[1]*angVel[1] + angVel[2]*angVel[2];
    if (angMagSq < 0.01) return;  // anti-jitter, don't damp tiny rotations
    vector dampedAng = angVel * IDLE_DAMPING_FACTOR;
    dBodySetAngularVelocity(this, dampedAng);
}
```

Multiply angular velocity by 0.92 per tick when no driver. Prevents vehicles flipping/spinning forever when pilot bails. Anti-jitter floor prevents fighting against tiny oscillations.

**Input action caching** — resolve UAInput refs once, cache:

```cpp
protected UAInput m_InputFire;
protected UAInput m_InputReload;
protected bool m_InputsCached = false;

protected void CacheInputActions()
{
    m_InputFire   = GetUApi().GetInputByName("UAMyModFire");
    m_InputReload = GetUApi().GetInputByName("UAMyModReload");
    m_InputsCached = true;
}

override void OnInput(float dt)
{
    if (!m_InputsCached) CacheInputActions();
    if (m_InputFire.LocalPress()) DoFire();
}
```

`GetInputByName` does a string-keyed lookup. Doing it every input frame is wasteful. Cache once, reuse refs. Pattern applies to any hot path that does string-keyed lookups.

## RPC, cleanup, vehicle and mod architecture patterns

### Custom RPC enum with magic constants

```cpp
enum MyMod_RPCserver { RPC_DO_FIRE     = 937081 };
enum MyMod_RPCclient { RPC_SYNC_FX     = 937091 };

override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);
    
    if (GetGame().IsServer() && rpc_type == MyMod_RPCserver.RPC_DO_FIRE) {
        Param1<bool> p;
        if (ctx.Read(p) && p.param1) DoServerAction();
    }
    
    if (rpc_type == MyMod_RPCclient.RPC_SYNC_FX && !GetGame().IsServer()) {
        Param3<Object, ImpactEffectsData, vector> fx;
        if (ctx.Read(fx)) PlayClientEffect(fx);
    }
}
```

**Magic constants in 6-7 digit range** (like `937081`) avoid collision with vanilla DayZ's lower-numbered RPCs and other mods. Pick a unique number prefix per mod. Group by direction (`_RPCserver` for client→server, `_RPCclient` for server→client) — explicit which way each RPC flows.

`GetGame().IsServer()` inside `OnRPC` is safe: the load-time caveat of rules 19 and 20 in `hard-rules.md` applies only during init, not to post-load callbacks.

### Server-authoritative input pattern (client predicts, server validates)

For weapons / actions where server must be authoritative but client needs responsive feedback:

```cpp
override void EOnPostSimulate(IEntity other, float timeSlice)
{
    super.EOnPostSimulate(other, timeSlice);
    
    if (!IsLocalPilot()) return;  // only the controlling player triggers
    
    Input inp = GetGame().GetInput();
    if (!inp) return;
    
    if (inp.LocalHold("UAMyAction") && m_canAct) {
        // 1) RPC server to perform action
        GetGame().RPCSingleParam(this, MyMod_RPCserver.RPC_DO_ACTION,
                                 new Param1<bool>(true), true);
        
        // 2) Lock client immediately (anti-spam, no wait for server)
        m_canAct = false;
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY)
                 .CallLater(ActionReady, ACTION_TIMEOUT_MS, false);
    }
}

// On server, OnRPC receives and executes:
//   - Validate inputs
//   - Mutate world state
//   - Broadcast FX to all clients via foreach Players + RPCSingleParam
```

Client locks before server response — keeps input feeling responsive. Cooldown re-arms client even if server response is lost. Server is canonical authority.

### Broadcast-to-all-clients pattern

```cpp
m_PlayerCache.Clear();  // reused array — clear, don't allocate
GetGame().GetPlayers(m_PlayerCache);
foreach (Man man : m_PlayerCache)
    GetGame().RPCSingleParam(this, MyMod_RPCclient.RPC_SYNC,
                              new Param3<...>(...), true, man.GetIdentity());
```

Loop all players + RPCSingleParam with `man.GetIdentity()` for each. `true` 4th arg = reliable. Not as efficient as a true broadcast (those don't exist in DayZ Enforce Script) but reliable per-player delivery.

### Triple cleanup hook (effect/handle lifetime safety)

When an entity owns ScriptedEffect refs (sounds, particles, lights), guarantee cleanup via three hooks:

```cpp
class MyEntity : EntityAI
{
    protected ref EffectParticle m_Eff;
    
    override void EEDelete(EntityAI parent)
    {
        CleanupResources();
        super.EEDelete(parent);
    }
    
    override void CleanupEffects()  // CarScript or similar base method
    {
        super.CleanupEffects();
        CleanupResources();
    }
    
    void ~MyEntity()                // destructor (last line of defense)
    {
        CleanupResources();
    }
    
    protected void CleanupResources()
    {
        if (m_Eff) {
            m_Eff.Stop();
            SEffectManager.DestroyEffect(m_Eff);
            m_Eff = null;
        }
    }
}
```

`SEffectManager.DestroyEffect` must be called or effects leak. The triple hook catches all destruction paths (normal removal, server unload, garbage collection).

### Client-only resource init guard

Particles, lights, sounds don't need to be created on dedicated servers (no rendering):

```cpp
protected void InitClientEffects()
{
    if (m_Initialized) return;
    if (!GetGame().IsClient() && GetGame().IsMultiplayer()) return;
    // SP: IsClient is true, no skip
    // MP server: IsClient false + IsMultiplayer true → skip
    // MP client: IsClient true, no skip
    
    // ... create effects, lights, sounds
    m_Initialized = true;
}
```

The condition `!IsClient() && IsMultiplayer()` is the standard "skip if MP server" check. In SP, `IsClient()` returns true so the check passes.

Call this guard lazily (first tick/event), not from a constructor or load-time init: during load `IsClient()` is not reliable on the client (rules 19 and 20 in `hard-rules.md`) and the guard would mis-skip.

### Vanilla DayZ helpers reference

**Water detection** (any position):

```cpp
GetGame().SurfaceIsSea(x, z)       // ocean / saltwater
GetGame().SurfaceIsPond(x, z)      // freshwater pond/lake
GetGame().SurfaceGetSeaLevel()     // absolute Y of sea level

float heightAboveSea = position[1] - GetGame().SurfaceGetSeaLevel();
```

Useful for amphibious vehicles, submarines, swimming behavior, weather effects over water. (Cost caveat: see the water-detection entry in `pitfalls-advanced.md` — `SurfaceIsSea`/`SurfaceIsPond` are slow proto natives; prefer `GetGame().GetWaterDepth(pos)` in hot paths.)

**Damage zone resolution** (defensive helper for `ProcessDirectDamage`):

```cpp
protected string ResolveDamageZone(Object hitObj, int componentIdx)
{
    // 1) Try component-specific zone (most precise)
    string zone = hitObj.GetDamageZoneNameByComponentIndex(componentIdx);
    if (zone != "") return zone;
    
    // 2) Humans/zombies default to Torso
    if (hitObj.IsMan() || hitObj.IsInherited(DayZInfected)) return "Torso";
    
    // 3) Animals default to Torso
    if (hitObj.IsInherited(DayZCreatureAI)) return "Torso";
    
    // 4) Generic objects: first available zone
    array<string> zones = new array<string>();
    hitObj.GetDamageZones(zones);
    if (zones.Count() > 0) return zones[0];
    
    // 5) No applicable zone
    return "";
}

// Use:
string zone = ResolveDamageZone(hitObj, hitComp);
if (zone != "")
    hitObj.ProcessDirectDamage(DamageType.FIRE_ARM, this, zone, AMMO_TYPE,
                                hitPos, damage, ProcessDirectDamageFlags.ALL_TRANSFER);
```

Chained fallback prevents `ProcessDirectDamage` crashes when hitting unknown target types.

**Camera shake on local player damage**:

```cpp
DayZPlayer localPlayer = DayZPlayer.Cast(GetGame().GetPlayer());
if (directHit && localPlayer && directHit == localPlayer)
    localPlayer.GetCurrentCamera().SpawnCameraShake(0.4);
```

Trigger from client-side impact handler. Shake intensity `0.4` is mild — increase for explosions.

**Local pilot / driver check**:

```cpp
private bool IsLocalDriver()
{
    DayZPlayer p;
    Transport t;
    if (!Class.CastTo(p, GetGame().GetPlayer())) return false;
    if (!Class.CastTo(t, p.GetParent())) return false;
    return (t == this && CrewMemberIndex(p) == 0);  // 0 = driver/pilot
}
```

Checks: (1) local player exists, (2) is in a Transport, (3) the transport IS this vehicle, (4) is in seat 0 (driver/pilot, not copilot/passenger). Use to gate vehicle-mounted weapons / driver-only actions.

### Vehicle anim instance override

```cpp
override int GetAnimInstance() { return VehicleAnimInstances.<TYPE>; }
```

Where `<TYPE>` ∈ `{GOLF, SEDAN, V3S, ...}`. Determines the player sit/getin animation when interacting with the vehicle. Pick a vanilla instance that matches your vehicle's cockpit shape — avoids needing to author custom anims:
- `GOLF` — small/compact cockpit (sport cars, small planes)
- `SEDAN` — standard car cockpit (most use cases)
- `V3S` — truck cabin (large vehicles, transport planes)
- The other vanilla instances (`CIVVAN`, `HATCHBACK`, `BUS`, `S120`, `MULTICAR`, `HMMWV`, `ZODIAC`, `MOTO1`, `MOTO2`) are in the enum at `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`

### Mod parent/child architecture (asymmetric dependency)

For mods organized as parent + per-feature sub-mods:

```cpp
// Parent (root mod) — registers shared infra
class CfgPatches {
    class MyParentMod {
        units[] = {};              // EMPTY — no entities in parent
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgMods {
    class MyParentMod {
        // Script modules registered DIRECTLY (no class defs wrapper):
        class gameScriptModule  { files[] = {"MyParentMod/scripts/3_Game"}; };
        class worldScriptModule { files[] = {"MyParentMod/scripts/4_World"}; };
    };
};

// Per-feature sub-mod
class CfgPatches {
    class MyParentMod_FeatureX {
        units[] = {"MyEntity1", "MyEntity2"};
        requiredAddons[] = {"DZ_Data", "MyParentMod"};  // requires parent
    };
};
class CfgMods {
    class MyParentMod_FeatureX {
        class defs {                                     // wrapped in class defs
            class worldScriptModule { files[] = {"MyParentMod/scripts/4_World"}; };
        };
    };
};
```

**One-way dependency**: child requires parent, parent doesn't require children. Lets users enable/disable per-feature sub-mods without breaking the root. Parent root only registers shared scripts + inputs.

### Cosmetic-only proxies (no script needed)

If your model has visual-only details (seats players don't sit on, doors players don't open via script, decorative engine parts), use proxy .p3d files **without** corresponding `pos_*` memory points or `seat_*` selections. Engine renders the proxy at the LOD distance without requiring script support.

Doors that should detach as inventory attachments use vanilla DayZ's `CarDoor` base + `class DamageZones.Doors` + `attachments[]` — engine handles visibility on attach/detach. No script logic needed for the door itself.
