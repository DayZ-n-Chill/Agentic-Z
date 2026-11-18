# DayZ 1.30 particles

What DayZ 1.30 changed in the particle script API: the client check, effects spawned by the server, surface particle IDs and runtime overrides for vehicle effects, then what breaks in a 1.29 mod and the migration checklist. How effect areas tick, the sandstorm, oil pits, dust kickup and the new `ParticleList` constants are in `dayz-1-30-world-particles.md`. Line numbers are from the 1.30 scripts on `P:\`. What 1.29 did is not checked on `P:\`, which holds 1.30 only.

## Contents

- [Client check: IsHeadlessOrDedicatedServer](#client-check-isheadlessordedicatedserver)
- [Server spawned effects: CreateParticleServer](#server-spawned-effects-createparticleserver)
- [Surface particle IDs: SurfaceInfo](#surface-particle-ids-surfaceinfo)
- [Runtime overrides: ParticleParamsOverrideData and vehicle effects](#runtime-overrides-particleparamsoverridedata-and-vehicle-effects)
- [What breaks in a 1.29 mod](#what-breaks-in-a-129-mod)
- [Migration checklist](#migration-checklist)

## Client check: IsHeadlessOrDedicatedServer

In 1.29 vanilla wrecks and `FireplaceBase` tested `!g_Game.IsDedicatedServer()`. Since 1.30, most vanilla particle code skips headless clients as well as dedicated servers. The Chinook and Mi-24 wrecks still use the dedicated server check alone (`P:\scripts\4_world\entities\building\wrecks\wreck_chinook.c:6` and `P:\scripts\4_world\entities\building\wrecks\wreck_mi24_tk.c:5`).

- `IsHeadlessOrDedicatedServer` is a native method on the game (`P:\scripts\3_game\global\game.c:1136`).
- Its comment says it combines `IsDedicatedServer` and `IsHeadless`, and that it is also true for a server with a head (`-headlessMode=0`) (`P:\scripts\3_game\global\game.c:1133`).
- `ParticleManager.GetInstance()` builds the global pool only when that check is false (`P:\scripts\3_game\particles\particlemanager\particlemanager.c:65`).
- The `PlayParticle` helper of `FireplaceBase` uses the same check (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1112`).

The vanilla crashed helicopter, whole class:

```c
// P:\scripts\4_world\entities\building\wrecks\wreck_mi8.c:2
class Wreck_Mi8_Crashed extends CrashBase
{
	void Wreck_Mi8_Crashed()
	{
		if ( !g_Game.IsHeadlessOrDedicatedServer() )
		{
			m_ParticleEfx = ParticleManager.GetInstance().PlayOnObject(ParticleList.SMOKING_HELI_WRECK, this, Vector(2, 0, -5));
		}
	}
}
```

A mod that still checks only for a dedicated server runs its particle code on headless clients. There `ParticleManager.GetInstance()` returns null, because it creates the global pool only when `IsHeadlessOrDedicatedServer()` is false (`P:\scripts\3_game\particles\particlemanager\particlemanager.c:65`), so a call such as `ParticleManager.GetInstance().PlayOnObject(...)` fails on a null reference. Use `IsHeadlessOrDedicatedServer()` for every particle effect. This narrows the general client-only rule in `skills/_shared/conventions/scripts.md`, which names `!GetGame().IsDedicatedServer()`: `IsHeadlessOrDedicatedServer()` includes that check and adds headless clients.

## Server spawned effects: CreateParticleServer

`SEffectManager.CreateParticleServer` creates an effecter entity on the server, and the entity shows the particle on every client near it. It is not new in 1.30: tree and bush cutting, fishing and fish traps already call it. What 1.30 adds is ceiling dust as a frequent caller.

| Caller | Citation |
|---|---|
| Tree cutting, with `TreeEffecterParameters` | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionminetree.c:108` |
| Fishing splash, with `ParticleEffecterParameters` | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfishingnew.c:326` |
| Fish trap catch, stored in `m_CatchParticleEffecterId` | `P:\scripts\4_world\entities\itembase\trapspawnbase.c:660` |
| Ceiling dust (1.30), with the `CeilingDustEffecter` entity | `P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:98` |

The synced ceiling dust handler:

```c
// P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:92
class DustEffectCeilingHandlerSynced : DustEffectCeilingHandlerBase
{
	//! Request from server, effecter handles the rest
	override protected void CreateEffects(int ceilingParticleID, vector position)
	{
		//'spam' variant of effecters solution
		SEffectManager.CreateParticleServer(position, new ParticleEffecterParameters("CeilingDustEffecter", 2.0, ceilingParticleID));
	}
}
```

The local handler, `DustEffectCeilingHandlerLocal`, still plays on the client with `SEffectManager.PlayInWorld` (`P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:86`). Both get the particle ID from `GetCeilingDustParticleId()` on the surface (`P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:27`).

The manager method:

```c
// P:\scripts\3_game\effectmanager.c:585
	//! returns unique effecter ID
	static int CreateParticleServer(vector pos, EffecterParameters parameters)
	{
		EffecterBase eff;
		eff = EffecterBase.Cast(g_Game.CreateObjectEx(parameters.m_EffecterType, pos, ECE_PLACE_ON_SURFACE));
		
		if (eff)
		{
			int id = GetFreeEffecterID();
			m_EffectersMap.Insert(id, eff);
		}
		
		eff.Init(id, parameters);
		return id;
	}
```

The same block of the manager holds `ReinitParticleServer` (`P:\scripts\3_game\effectmanager.c:602`), `ReactivateParticleServer` (`P:\scripts\3_game\effectmanager.c:611`), `StartParticleServer` (`P:\scripts\3_game\effectmanager.c:620`), `StopParticleServer` (`P:\scripts\3_game\effectmanager.c:630`) and `DestroyEffecterParticleServer` (`P:\scripts\3_game\effectmanager.c:639`). The parameter classes are `EffecterParameters` (`P:\scripts\3_game\effectmanager.c:675`) and `ParticleEffecterParameters` (`P:\scripts\3_game\effectmanager.c:686`).

`PlayOnObject` stays client only. Use `CreateParticleServer` when every nearby client must see the same short effect and no client side state change would trigger it.

How long an effecter lives:

- The lifespan is the second argument of the parameters, in seconds. `SEffectManager.OnUpdate` counts it down every frame (`P:\scripts\3_game\dayzgame.c:3023`; `P:\scripts\3_game\effectmanager.c:654` to `:663`) and destroys the effecter when it runs out (`effectmanager.c:715` to `:724`).
- `EffecterBase.NOT_DEFINED_LIFESPAN` (`-1`) never runs out (`effectmanager.c:698` and `:717`). A caller that passes it keeps the ID that `CreateParticleServer` returns and calls `DestroyEffecterParticleServer` itself, as tree cutting and fishing do (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionminetree.c:125`; `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfishingnew.c:146`). Otherwise the effecter entity stays on the server.
- `CreateParticleServer` calls `eff.Init` even when the object was not created (`effectmanager.c:589` to `:597`), so a misspelt effecter class name ends in a null pointer error on the server instead of a clear message.

## Surface particle IDs: SurfaceInfo

In 1.29 `Surface.GetStepsParticleID(string)` and `Surface.GetWheelParticleID(string)` were the lookups to call. Since 1.30 both are marked obsolete and only forward to `SurfaceInfo`:

```c
// P:\scripts\4_world\static\surface.c:64
	[Obsolete("1.30: use SurfaceInfo.GetStepParticleId directly")]
	static int GetStepsParticleID(string surface_name) 
	{
		return SurfaceInfo.GetByName(surface_name).GetStepParticleId();
	}
	
	[Obsolete("1.30: use SurfaceInfo.GetWheelParticleId directly")]
	static int GetWheelParticleID(string surface_name) 
	{
		return SurfaceInfo.GetByName(surface_name).GetWheelParticleId();
	}
```

The getters on `SurfaceInfo`, each a `proto` method, run from `GetStepParticleId` (`P:\scripts\3_game\surfaceinfo.c:49`) to `GetCeilingDustParticleId` (`P:\scripts\3_game\surfaceinfo.c:70`):

- Steps: `GetStepParticleId`, `GetStepSoundSetName`.
- Wheels: `GetWheelParticleId`, `GetWheelSoundSetName`, `GetWheelContactParticleId`, `GetWheelContactSoundSetName`.
- Vehicle dust: `GetVehicleDustParticleId`, `GetVehicleDustSoundSetName`.
- Dust kickup: `GetDustKickupEffectId`, `GetDustKickupEffectSmallId`, `GetDustKickupEffectBigId`.
- Cloud and ground effects: `GetCloudEffectParticleId`, `GetCloudEffectSoundSetName`, `GetGroundEffectParticleId`, `GetGroundEffectSoundSetName`.
- Ceiling dust: `GetCeilingDustParticleId`.

The comment above them says a config entry that is not set gives `ParticleList.NONE`, and one that is set but names no registered particle gives `ParticleList.INVALID` (`P:\scripts\3_game\surfaceinfo.c:47`).

## Runtime overrides: ParticleParamsOverrideData and vehicle effects

New in 1.30. `EffectParticle` declares three hooks:

```c
// P:\scripts\3_game\effects\effectparticle.c:611
	void SelectFromSurface(string surface);
	void SelectFromSurface(SurfaceInfo surfaceInfo);
	
	void SetParticleState(int state);

	/**
	\brief Callback for overriding effect's particle attributes
	*/
	void ParticleParamsOverride(notnull ParticleParamsOverrideData data);
```

and the data class that is passed in:

```c
// P:\scripts\3_game\effects\effectparticle.c:651
class ParticleParamsOverrideData
{
	ref TFloatArray m_FloatModifiers = new TFloatArray();
	
	void ClearAll()
	{
		m_FloatModifiers.Clear();
	}
}
```

What the vanilla vehicle effects do with it:

| Effect | What its `ParticleParamsOverride` does | Surface ID | Citation |
|---|---|---|---|
| `EffVehicleDust` | Reads `m_FloatModifiers[0]` as speed and `[1]` as weight. Sets `LIFETIME` to `2.5 * weight`, `REPEAT` and `WIND` to true, `VELOCITY` and `SIZE` to `speed * weight`, `AIR_RESISTANCE` to `1.0 * weight`. Its threshold constant is `WHEEL_DUST_THRESHOLD = 3.0`. | `GetVehicleDustParticleId()` | `P:\scripts\4_world\entities\effects\vehicledust.c:5` to `:27` |
| `EffWheelContact` | Reads speed and weight the same way. Sets `LIFETIME` to `1.0 * weight`, `SPRING` to 15, `REPEAT` and `WIND` to false, `SIZE` to 1, `AIR_RESISTANCE` to 1. | `GetWheelContactParticleId()` | `P:\scripts\4_world\entities\effects\effwheelcontact.c:5` to `:27` |
| `EffExhaustSmoke` | Reads speed only. Scales `LIFETIME` by `1 + speed * 0.1` below a speed of 100 and by `0.1` above it, scales `BIRTH_RATE` by `1 + speed * 0.1`, sets `SIZE` and `VELOCITY` to `speed * 2` and `AIR_RESISTANCE` to 2. | none | `P:\scripts\3_game\effects\effectparticle\vehiclesmoke\exhaustsmoke.c:3` to `:29` |
| `EffWheelSmoke` | No override. `SelectFromSurface` picks `GetWheelParticleId()`. Its old `SetSurface(string)` is marked `Obsolete`. | `GetWheelParticleId()` | `P:\scripts\4_world\entities\effects\wheelsmoke.c:5` to `:33` |

`VehicleVFXComponent` (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:96`) owns these effects for a vehicle:

- `RegisterEffect` adds one effect (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:126`); the IDs are in `EVehicleVFXEffect`: `DUST_BEHIND`, `ENGINE_SMOKE`, `COOLANT_STEAM`, `EXHAUST_SMOKE` (`P:\scripts\3_game\enums\evehiclevfxtypes.c:2`).
- `RegisterEffectGroup` adds several copies of one effect, such as one per wheel (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:139`); the IDs are in `EVehicleVFXEffectGroup`: `WHEEL_SMOKE`, `WHEEL_CONTACT` (`P:\scripts\3_game\enums\evehiclevfxtypes.c:12`).
- `GetParticleParamsOverrideData` returns the data object of one effect so the vehicle can fill it (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:373`), and `GetEffectGroupParticleParamsOverrideData` does the same for a group (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:530`).
- `CarScript` registers its six effects with `RegisterEffect` and `RegisterEffectGroup` (`P:\scripts\4_world\entities\vehicles\carscript.c:377` to `:382`), and `MotorbikeScript` registers five, with no coolant steam (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:199` to `:204`).

### Memory points a car model needs for its effects

`CarScript.InitializeParticles()` returns at once on a headless client or dedicated server, then places each effect at a memory point of the model (`P:\scripts\4_world\entities\vehicles\carscript.c:343` to `:382`):

| Memory point | Effect |
|---|---|
| `ptcDustPos` | `DUST_BEHIND`, `EffVehicleDust` |
| `ptcEnginePos` | `ENGINE_SMOKE`, `EffEngineSmoke` |
| `ptcCoolantPos` | `COOLANT_STEAM`, `EffCoolantSteam` |
| `ptcExhaust_end`, `ptcExhaust_start` | `EXHAUST_SMOKE`, `EffExhaustSmoke`: the position, and the direction from start to end |

`ConvertMemPointToPosition` returns `vector.Zero` when the point does not exist (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:115` to `:120`), so a model without one of these points shows that effect at the model origin, with no error. A missing `ptcExhaust_end` also sets the exhaust direction to `"1 1 1"` (`carscript.c:364`). The speed and weight in `m_FloatModifiers` are filled each frame in `EOnPostFrame`, on clients only (`carscript.c:675`, `:681`, `:719` and `:720`); dust starts above `EffVehicleDust.WHEEL_DUST_THRESHOLD` (`carscript.c:716`).

## What breaks in a 1.29 mod

| Symptom | Severity | Change |
|---|---|---|
| Particles play on a headless client | Medium | Replace `!IsDedicatedServer()` with `!IsHeadlessOrDedicatedServer()` around particle code. |
| A call to `Surface.GetStepsParticleID` or `Surface.GetWheelParticleID` warns as obsolete | Low | Stop calling `Surface.GetStepsParticleID` and `Surface.GetWheelParticleID`; read `SurfaceInfo`. |
| A call to `EffWheelSmoke.SetSurface(string)` warns as obsolete | Low | Call `SelectFromSurface(SurfaceInfo)`. |
| A custom `EffectArea` that overrides `OnCEUpdate` may not tick, or its particles float above bridges | Medium | Override `OnCEIterate` and snap with `SurfaceRoadY` (`dayz-1-30-world-particles.md`). |

## Migration checklist

- [ ] Search the mod for `IsDedicatedServer()` around particle code and change those checks to `IsHeadlessOrDedicatedServer()`.
- [ ] Replace `Surface.GetStepsParticleID` and `Surface.GetWheelParticleID` with `SurfaceInfo.GetByName(...).GetStepParticleId()` and `GetWheelParticleId()`.
- [ ] Replace `EffWheelSmoke.SetSurface` with `SelectFromSurface`.
- [ ] Custom `EffectArea`: override `OnCEIterate(float currentTime, float elapsedTime)` and snap with `SurfaceRoadY`.
- [ ] Vehicle dust and exhaust: register the effect through `VehicleVFXComponent` and override `ParticleParamsOverride`.
- [ ] Do not copy `sandstorm.emat` as a particle material; its shader is `SnowEffect`.
