# Surface dust, oil pits and Nasdara

Where 1.30 dust effects come from (`SurfaceInfo`), the oil pit effect area, and what the Nasdara world (Badlands DLC) adds. Checked on `P:\` (DayZ 1.30) except where a line says otherwise: the Nasdara data files are not unpacked on `P:\`. Writing `.ptc` and `.emat` files, and playing particles, is in `/dayz-particles`; this file keeps to the hazard and the world setup.

## `SurfaceInfo` (1.30)

New getters on `SurfaceInfo`, from `GetStepParticleId` to `GetCeilingDustParticleId` (`P:\scripts\3_game\surfaceinfo.c:49` to `:70`):

| Group | Getters |
|---|---|
| Steps | `GetStepParticleId`, `GetStepSoundSetName` |
| Wheels | `GetWheelParticleId`, `GetWheelSoundSetName`, `GetWheelContactParticleId`, `GetWheelContactSoundSetName` |
| Vehicle dust | `GetVehicleDustParticleId`, `GetVehicleDustSoundSetName` |
| Kickup | `GetDustKickupEffectId`, `GetDustKickupEffectSmallId`, `GetDustKickupEffectBigId` |
| Ambient | `GetCloudEffectParticleId`, `GetGroundEffectParticleId` and their sound set getters |
| Ceilings | `GetCeilingDustParticleId` |

Surface thickness is `GetThickness()` (`P:\scripts\3_game\surfaceinfo.c:31`).

The old static getters on `Surface` are marked obsolete and now forward to `SurfaceInfo`:

```c
// P:\scripts\4_world\static\surface.c:64
	[Obsolete("1.30: use SurfaceInfo.GetStepParticleId directly")]
	static int GetStepsParticleID(string surface_name) 
	{
		return SurfaceInfo.GetByName(surface_name).GetStepParticleId();
	}
```

`EffWheelSmoke.SetSurface` is obsolete too; use `SelectFromSurface` (`P:\scripts\4_world\entities\effects\wheelsmoke.c:32` to `:33`, the replacement is at `wheelsmoke.c:5`). In new code call `SurfaceInfo.GetByName(...).GetStepParticleId()` and pass a `SurfaceInfo` to `SelectFromSurface`.

## Dust from ceilings

`DustEffectCeilingHandlerBase.OnStepUpdate` (`P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:25` to `:41`): when the surface's `GetCeilingDustParticleId()` is above 0, it counts steps and, every 4 to 8 steps by default (`RANGE_MIN_DEFAULT`, `RANGE_MAX_DEFAULT`, `dusteffectceilinghandler.c:3` to `:4`), lowers the position by `GetThickness()` and spawns the effect. A thickness of -1 means "not defined" and falls back to 0.4 m (`FLOOR_THICKNESS_DEFAULT`, `dusteffectceilinghandler.c:5`, `:66` to `:72`).

- Local variant: `SEffectManager.PlayInWorld` (`dusteffectceilinghandler.c:79` to `:88`).
- Synced variant: `SEffectManager.CreateParticleServer` with `ParticleEffecterParameters("CeilingDustEffecter", ...)` (`dusteffectceilinghandler.c:95` to `:99`).

## Ambient ground and cloud dust

`DustEffectManager` reads `GetWorldData().GetDustEffectsSettings()` (`P:\scripts\4_world\classes\dust\dusteffectsmanager.c:81`; the getter is at `P:\scripts\3_game\worlddata.c:548`). Nasdara turns both effects on in `SetupDustEffects` (`P:\scripts\4_world\classes\worlds\nasdara.c:152` to `:169`): ground dust from wind strength 8 at distance 30, cloud dust from wind strength 5 at distance 16.

Kickup dust is `DustKickupEffects`, with the sound set `KickupDustEffect_SoundSet` (`P:\scripts\3_game\dustkickupeffects.c:43` to `:45`).

## Vehicles

- `VehicleVFXComponent.PlayEffectData` finds the ground with `g_Game.GetSurface` and hands on its `SurfaceInfo` (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:177` to `:186`).
- `EffVehicleDust.SelectFromSurface` uses `GetVehicleDustParticleId()` (`P:\scripts\4_world\entities\effects\vehicledust.c:25` to `:35`). Its `ParticleParamsOverride` scales `LIFETIME`, `VELOCITY`, `SIZE` and `AIR_RESISTANCE` by speed and a weight coefficient (`vehicledust.c:5` to `:23`).
- `EffWheelContact.SelectFromSurface` uses `GetWheelContactParticleId` and `GetWheelContactSoundSetName` (`P:\scripts\4_world\entities\effects\effwheelcontact.c:25` to `:28`).

The weight coefficient is `GetWeightCoef()`:

| Class | Value | Where |
|---|---|---|
| `Transport` (default) | 1.0 | `GetWeightCoef`, `P:\scripts\3_game\vehicles\transport.c:475` |
| `Offroad_02` | 1.5 | `GetWeightCoef`, `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:133` |
| `Truck_01_Base` | 2.0 | `GetWeightCoef`, `P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c:120` |
| `Motorbike_01` | 0.5 | `GetWeightCoef`, `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:87` |
| `Motorbike_02` | 0.75 | `GetWeightCoef`, `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:77` |

The source notes passed on an unchecked figure of 0.25 for motorbikes; `P:\` shows 0.5 and 0.75.

## Oil pit

The area type is `EEffectAreaType.OIL_PIT = 8` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:10` to `:16`).

`OilPitArea` (`P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c:7`): `PRE_BURNING_DURATION_MIN` 3 and `PRE_BURNING_DURATION_MAX` 10 seconds (`oilpitarea.c:10` to `:11`). `InitZoneServer` creates the trigger and calls `StartBurning` after that random delay (`oilpitarea.c:33` to `:48`). `StartBurning` sets `EOilPitState.BURNING` on the trigger (`oilpitarea.c:57` to `:61`). Until then the pit does no damage, so a freshly loaded pit looks inert for up to 10 s.

Damage:

```c
// P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:7
	protected const float 	DAMAGE_TICK_RATE 	= 1.0;	// seconds between fire damage ticks
	protected const float 	DAMAGE_MULTIPLIER	= 20.0;	// damage per tick
```

```c
// P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:63
	override void OnStayServerEvent(TriggerInsider insider, float deltaTime)
	{
		if (!m_DealDamageFlag)
			return;

		EntityAI entity = EntityAI.Cast(insider.GetObject());
		if (entity)
			entity.ProcessDirectDamage(DamageType.CUSTOM, this, "", "HeatDamage", "0 0 0", DAMAGE_MULTIPLIER);
	}
```

`OnStayStartServerEvent` raises the damage flag only in the `BURNING` state and once per `DAMAGE_TICK_RATE` (`oilpittrigger.c:53` to `:61`).

On the client (`UpdateState`, `oilpittrigger.c:90` to `:126`): a `BonfireLight` 2.5 m above the pit; fire and smoke as either `OIL_FIRE1` with `BONFIRE_SMOKE` or `OIL_FIRE2` with `SMOKE_GENERIC_WRECK`; the sound `oil_pit_burn_SoundSet`, played only within 200 m and re-checked every 2 s (`oilpittrigger.c:3` to `:5`; `UpdateSoundRange` and `UpdateSound`, `oilpittrigger.c:201` to `:224`). The position is snapped to the ground with `SurfaceRoadY` (`oilpittrigger.c:128` to `:134`). `DeferredInit` skips `UpdateState` on a headless or dedicated server (`oilpittrigger.c:37`), but the ignition branch of `UpdateState` itself calls `PlayInWorld` with no such guard (`oilpittrigger.c:105` to `:116`).

### Placing one, and writing your own

Effect areas are listed in the mission's `cfgeffectarea.json` as entries with `AreaName`, `Type`, `TriggerType` and `Data`; the vanilla Sakhal file uses the types `GeyserArea`, `HotSpringArea` and `VolcanicArea` (file `P:\DZ\worlds\sakhal\ce\cfgeffectarea.json`). No vanilla file on `P:\` places an oil pit, so an entry with `Type` `OilPitArea` and `TriggerType` `OilPitTrigger` is a design inference from the class names, not a copied example.

For a custom area, inherit `OilPitArea` or copy its trigger and net sync pattern. Override `OnCEIterate(float currentTime, float elapsedTime)`, as `EffectArea` does (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:191`); `OnCEUpdate` is marked obsolete in 1.30 (`P:\scripts\3_game\entities\entityai.c:4924` to `:4925`). `SpawnParticles` snaps each particle to `SurfaceRoadY` (`effectarea.c:412` to `:414`).

## Nasdara (Badlands DLC)

The scripts for the world are on `P:\` (`P:\scripts\4_world\classes\worlds\nasdara.c:49` holds its monthly maximum temperatures, 38.4 in July). Its data PBOs are not. The rest of this section is from the source notes' reading of the game's own files on builds 1.30.164014 and 1.30.164200, and is not checked on `P:\`:

- The mod class is `CfgMods.nasdara` with `appId = 3816030`; the data addon's internal prefix is `DZ\data_takistan`.
- On 1.30.164014, `data_nasdara.pbo` held 6 files: its config, `basicdefines.hpp`, the AI config and an impact test model with its `.bisurf` and `.rvmat`. There was no `.wrp` and no navmesh.
- 1.30.164200 installs `nasdara\addons\` with 24 PBOs and `worlds_nasdara.ebo`. `worlds_nasdara_nav.pbo` holds `navmesh.nm`, `worlds_nasdara_ce.pbo` holds the Central Economy files (34 `.xml`, 4 `.json`, `areaflags.map`), and `data_nasdara.pbo` has 8 files (the same 6 plus `mud_brick_impenetrable.bisurf` and its `.rvmat`). No PBO lists a `.wrp`; as with Sakhal, the world is presumably inside the encrypted `.ebo`, which was not opened. The dedicated server ships the mission `mpmissions\dayzOffline.nasdara`. The map was not loaded in game.
- Skinning yields in its `basicDefines.hpp`: mouflon 10 steaks, 2 guts, 1 lard, 1 bones; dog the same kinds plus a head; lizard 1 of each.
- AI groups in its AI config: `DZMouflonGroupBeh` of type `DomesticHerbivores`, and `DZDogGroupBeh` of type `Predators` with `siegeAttackCountdownMin` and `siegeAttackCountdownMax` of 10 and 15.
- The 1.30 changelog says the 1.30 navmesh is not backwards compatible: a custom terrain's navmesh has to be generated again.

Weather for the map: `sandstorm-shelter.md`. Sun table: `thermal-heatstroke.md`.

## AI hearing in a storm

Infected hearing in a storm is config, not script: `AIParams` has `sandstormToNoiseMultiplier=10` (`P:\DZ\data\aiconfigs\config.cpp:20`). Both script helpers are marked obsolete: `GetNoiseReductionByWeatherEx(notnull Object object)` with the note that AI noise dampening is now native through `AIParams` and the method is kept for the HUD and old mods (`P:\scripts\3_game\weather.c:407` to `:408`), and the older `GetNoiseReductionByWeather()` with a pointer to the `Ex` form (`P:\scripts\3_game\weather.c:454` to `:455`). Changing either from script does not change what infected hear. The noise system is in `_shared/ai/perception.md`.
