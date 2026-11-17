# DayZ 1.30 particles: dust, vehicle effects, sandstorm

What DayZ 1.30 changed for particles: the client check, effects spawned by the server, surface particle IDs, runtime overrides for vehicle effects, how effect areas tick and place particles, the sandstorm, oil pits and the new `ParticleList` constants. Line numbers are from the 1.30 scripts on `P:\`. Statements about 1.29 come from the notes this file was built from; `P:\` holds 1.30, so they are not yet checked on `P:\`.

## Contents

- [Client check: IsHeadlessOrDedicatedServer](#client-check-isheadlessordedicatedserver)
- [Server spawned effects: CreateParticleServer](#server-spawned-effects-createparticleserver)
- [Surface particle IDs: SurfaceInfo](#surface-particle-ids-surfaceinfo)
- [Runtime overrides: ParticleParamsOverrideData and vehicle effects](#runtime-overrides-particleparamsoverridedata-and-vehicle-effects)
- [Effect areas: tick and ground snap](#effect-areas-tick-and-ground-snap)
- [Sandstorm: a postprocess material, not a particle material](#sandstorm-a-postprocess-material-not-a-particle-material)
- [Oil pits](#oil-pits)
- [Dust kickup from steps and bullets](#dust-kickup-from-steps-and-bullets)
- [New ParticleList constants](#new-particlelist-constants)
- [What breaks in a 1.29 mod](#what-breaks-in-a-129-mod)
- [Migration checklist](#migration-checklist)

---

## Client check: IsHeadlessOrDedicatedServer

Until 1.29, vanilla wrecks and `FireplaceBase` tested `!g_Game.IsDedicatedServer()` (1.29, not yet checked on `P:\`). Since 1.30, vanilla particle code skips headless clients as well as dedicated servers.

- `IsHeadlessOrDedicatedServer` is a native method on the game (`P:\scripts\3_game\global\game.c:1136`).
- Its comment says it combines `IsDedicatedServer` and `IsHeadless`, and that it is also true for a server with a head (`-headlessMode=0`) (`P:\scripts\3_game\global\game.c:1133`).
- `ParticleManager.GetInstance()` builds the global pool only when that check is false (`P:\scripts\3_game\particles\particlemanager\particlemanager.c:65`).
- The `PlayParticle` helper of `FireplaceBase` uses the same check (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1112`).

The vanilla crashed helicopter, whole class:

```
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

Design note: a mod that still checks only for a dedicated server plays particles on headless clients, which draw nothing and still take objects from the particle pool. Use `IsHeadlessOrDedicatedServer()` for every particle effect.

## Server spawned effects: CreateParticleServer

`SEffectManager.CreateParticleServer` creates an effecter entity on the server, and the entity shows the particle on every client near it. It is not new in 1.30: tree and bush cutting, fishing and fish traps already call it. What 1.30 adds is ceiling dust as a frequent caller.

| Caller | Citation |
|---|---|
| Tree cutting, with `TreeEffecterParameters` | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionminetree.c:108` |
| Fishing splash, with `ParticleEffecterParameters` | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfishingnew.c:326` |
| Fish trap catch, stored in `m_CatchParticleEffecterId` | `P:\scripts\4_world\entities\itembase\trapspawnbase.c:660` |
| Ceiling dust (1.30), with the `CeilingDustEffecter` entity | `P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:98` |

The synced ceiling dust handler:

```
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

```
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

Design note: `PlayOnObject` stays client only. Use `CreateParticleServer` when every nearby client must see the same short effect and no client side state change would trigger it.

## Surface particle IDs: SurfaceInfo

Until 1.29, `Surface.GetStepsParticleID(string)` and `Surface.GetWheelParticleID(string)` were the lookups to call (1.29, not yet checked on `P:\`). Since 1.30 both are marked obsolete and only forward to `SurfaceInfo`:

```
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

New in 1.30 (the source notes say 1.29 scripts do not have it; not yet checked on `P:\`). `EffectParticle` declares three hooks:

```
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

```
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
- `CarScript` registers its six effects with `RegisterEffect` and `RegisterEffectGroup` (`P:\scripts\4_world\entities\vehicles\carscript.c:377` to `:382`), and `MotorbikeScript` does the same (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:199`).

## Effect areas: tick and ground snap

Until 1.29, `EffectArea` ticked from `OnCEUpdate()` and `SpawnParticles` wrote `partPos[1] = g_Game.SurfaceY(...)` (1.29, not yet checked on `P:\`). Since 1.30 the tick hook is `OnCEIterate`:

```
// P:\scripts\4_world\classes\contaminatedarea\effectarea.c:190
	// Through this we will evaluate the resize of particles
	override void OnCEIterate(float currentTime, float elapsedTime)
	{
		super.OnCEIterate(currentTime, elapsedTime);
		Tick();
	}
```

and a particle is lowered to the road surface only when it starts above it:

```
// P:\scripts\4_world\classes\contaminatedarea\effectarea.c:412
	protected void SpawnParticles(ParticlePropertiesArray props, vector centerPos, vector partPos, inout int count)
	{
		float roadY = g_Game.SurfaceRoadY(partPos[0], partPos[2]);	// Snap particles to ground
		
		if (partPos[1] > roadY)
			partPos[1] = roadY;
```

Design note: a custom area that still overrides `OnCEUpdate` does not tick. The road snap keeps gas on a bridge deck instead of on the terrain under it. The particle budget and the vertical band of an area are in `effect-area-particles.md`.

## Sandstorm: a postprocess material, not a particle material

The weather class `Sandstorm` names three sound sets and one particle path, `particlePath="Graphics/Particles/sandstorm/sandstorm"` (`P:\DZ\data\config.cpp:1540`).

`sandstorm.emat` is not a `Particle` or `ParticleSprite` material:

- It opens with the shader `SnowEffect` (`P:\graphics\materials\postprocess\sandstorm.emat:1`).
- Its tint is `ParticlesColor 0.69 0.49 0.29 1` (`P:\graphics\materials\postprocess\sandstorm.emat:29`).
- Its texture is `SnowFlakesSheets_BCA.edds` (`P:\graphics\materials\postprocess\sandstorm.emat:13`).
- The Nasdara rain uses another postprocess shader, `RainEffect` (`P:\graphics\materials\postprocess\rainnasdara.emat:1`).

Do not name either file on the `Material` line of a `.ptc`.

The particle the weather config names is an ordinary `.ptc` with one emitter, `sand`: a `Box` shape with `MaxNum 200`, `BirthRate 20`, `LifeTime 5` and `Repeat 1`, using the material `sandstorm/dust_fluid_02.emat` (`P:\graphics\particles\sandstorm\sandstorm.ptc:4` to `:51`). The source notes could not read this file and marked its emitter count as unverified; the file is on `P:\` and the values above were read from it. It is not a `ParticleList` constant; the engine loads it from the weather config.

## Oil pits

`OilPitTrigger` picks one of two fire and smoke pairs in `UpdateState` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:90`):

- `ParticleList.OIL_FIRE1` with `BONFIRE_SMOKE` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:109`).
- `ParticleList.OIL_FIRE2` with `SMOKE_GENERIC_WRECK` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:114`).
- The light is a `BonfireLight` at `GetPosition() + "0 2.5 0"` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:98`).
- Both the start and the stop path test `IsHeadlessOrDedicatedServer` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:37` and `P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:190`).

## Dust kickup from steps and bullets

`DustKickupEffects` (`P:\scripts\3_game\dustkickupeffects.c:43`) maps a surface to a particle and to distance bands. `SurfaceInfo` supplies the IDs through `GetDustKickupEffectId`, `GetDustKickupEffectSmallId` and `GetDustKickupEffectBigId` (`P:\scripts\3_game\surfaceinfo.c:59` to `:61`).

Design note: a custom `CfgSurfaces` class that should raise kickup dust, wheel dust or ceiling dust must fill those config entries, or the getters return `ParticleList.NONE`.

## New ParticleList constants

All of these are in the catalog (`vanilla-particle-catalog.md`). This list says which ones 1.30 added, per the source notes; line numbers are in `P:\scripts\3_game\particles\particlelist.c`. `STEP_DESERT` and `STEP_SOIL` (`:374`, `:375`) were already in 1.29 according to the same notes.

| Constant | `.ptc` | Line |
|---|---|---|
| `TANDOOR_HOUSE_SMALL_FIRE` to `TANDOOR_HOUSE_FIRE_STEAM_2END` | `tandoor_fire_*`, `tandoor_smoke_*`, `tandoor_steam_*` | 49 to 54 |
| `EXPLOSION_GRENADE_SAND`, `EXPLOSION_GRENADE_DESERT_SAND` | `explosion_grenade_sand`, `explosion_grenade_desert_sand` | 145, 146 |
| `IMPACT_DESERT_SAND_*`, `IMPACT_MUD_BRICK_*` | `impacts/hit_desert_sand_*`, `impacts/hit_mud_brick_*` | 266 to 271 |
| `CEILING_WOOD` | `dust/dust_ceiling_wood`, registered with `RegisterParticleByFullPath` | 378 |
| `BUILDNG_DESTRUCT_WOOD`, `BUILDNG_DESTRUCT_BRICK`, `BUILDNG_DESTRUCT_METAL` | `building_destruction_*` | 381 to 383 |
| `VEHICLE_WHEEL_SOIL`, `VEHICLE_WHEEL_DESERT` | `vehicle_wheel_soil`, `vehicle_wheel_desert` | 390, 391 |
| `DUST_GROUND`, `DUST_CLOUD`, `DUST_VEHICLE`, `DUST_VEHICLE_SOFT` | `dust/dust_grnd_01`, `dust/dust_effect_01`, `dust_vehicle`, `dust_vehicle_soft` | 405 to 409 |
| `OIL_FIRE1`, `OIL_FIRE2` | `fire_oil1`, `fire_oil2` | 411, 412 |

`CEILING_WOOD` is the one constant registered by full path: `RegisterParticleByFullPath("graphics/particles/dust/dust_ceiling_wood")` (`P:\scripts\3_game\particles\particlelist.c:378`); the helper is declared at `P:\scripts\3_game\particles\particlelist.c:421`.

## What breaks in a 1.29 mod

| Symptom | Severity | Change |
|---|---|---|
| Particles play on a headless client | Medium | Replace `!IsDedicatedServer()` with `!IsHeadlessOrDedicatedServer()` around particle code. |
| Wheel or step particles ignore custom surfaces | Medium | Stop calling `Surface.GetStepsParticleID` and `Surface.GetWheelParticleID`; read `SurfaceInfo`. |
| A call to `EffWheelSmoke.SetSurface(string)` warns as obsolete | Low | Call `SelectFromSurface(SurfaceInfo)`. |
| A custom `EffectArea` never ticks, or its particles float above bridges | Medium | Override `OnCEIterate` and snap with `SurfaceRoadY`. |

## Migration checklist

- [ ] Search the mod for `IsDedicatedServer()` around particle code and change those checks to `IsHeadlessOrDedicatedServer()`.
- [ ] Replace `Surface.GetStepsParticleID` and `Surface.GetWheelParticleID` with `SurfaceInfo.GetByName(...).GetStepParticleId()` and `GetWheelParticleId()`.
- [ ] Replace `EffWheelSmoke.SetSurface` with `SelectFromSurface`.
- [ ] Custom `EffectArea`: override `OnCEIterate(float currentTime, float elapsedTime)` and snap with `SurfaceRoadY`.
- [ ] Vehicle dust and exhaust: register the effect through `VehicleVFXComponent` and override `ParticleParamsOverride`.
- [ ] Do not copy `sandstorm.emat` as a particle material; its shader is `SnowEffect`.
