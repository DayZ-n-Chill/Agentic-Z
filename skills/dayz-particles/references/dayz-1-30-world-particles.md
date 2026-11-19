# DayZ 1.30 world particles

How effect areas tick and place their particles since 1.30, what the sandstorm and oil pits play, where dust kickup gets its particles, and which `ParticleList` constants 1.30 added. The script API changes (client check, server spawned effects, `SurfaceInfo`, vehicle overrides) and the migration checklist are in `dayz-1-30-particles.md`. Line numbers are from the 1.30 scripts on `P:\`. What 1.29 did is not checked on `P:\`, which holds 1.30 only.

## Contents

- [Effect areas: tick and ground snap](#effect-areas-tick-and-ground-snap)
- [Sandstorm: a postprocess material, not a particle material](#sandstorm-a-postprocess-material-not-a-particle-material)
- [Oil pits](#oil-pits)
- [Dust kickup from steps and bullets](#dust-kickup-from-steps-and-bullets)
- [New ParticleList constants](#new-particlelist-constants)

## Effect areas: tick and ground snap

In 1.29 `EffectArea` ticked from `OnCEUpdate()` and `SpawnParticles` wrote `partPos[1] = g_Game.SurfaceY(...)`. Since 1.30 the tick hook is `OnCEIterate`:

```c
// P:\scripts\4_world\classes\contaminatedarea\effectarea.c:190
	// Through this we will evaluate the resize of particles
	override void OnCEIterate(float currentTime, float elapsedTime)
	{
		super.OnCEIterate(currentTime, elapsedTime);
		Tick();
	}
```

and a particle is lowered to the road surface only when it starts above it:

```c
// P:\scripts\4_world\classes\contaminatedarea\effectarea.c:412
	protected void SpawnParticles(ParticlePropertiesArray props, vector centerPos, vector partPos, inout int count)
	{
		float roadY = g_Game.SurfaceRoadY(partPos[0], partPos[2]);	// Snap particles to ground
		
		if (partPos[1] > roadY)
			partPos[1] = roadY;
```

`OnCEUpdate` is marked obsolete in favour of `OnCEIterate` (`P:\scripts\3_game\entities\entityai.c:4924`), and `EffectArea` no longer calls `Tick()` from it. Whether the engine still calls `OnCEUpdate` is not checked on `P:\`, so move a custom area's override to `OnCEIterate`. The road snap keeps gas on a bridge deck instead of on the terrain under it. The particle budget and the vertical band of an area are in `effect-area-particles.md`.

## Sandstorm: a postprocess material, not a particle material

The weather class `Sandstorm` names three sound sets and one particle path, `particlePath="Graphics/Particles/sandstorm/sandstorm"` (`P:\DZ\data\config.cpp:1540`). The sound sets are listed in the audio pack, `skills/_shared/audio-fx/effects-wiring.md`, "Weather sounds".

`sandstorm.emat` is not a `Particle` or `ParticleSprite` material:

- It opens with the shader `SnowEffect` (`P:\graphics\materials\postprocess\sandstorm.emat:1`).
- Its tint is `ParticlesColor 0.69 0.49 0.29 1` (`P:\graphics\materials\postprocess\sandstorm.emat:29`).
- Its texture is `SnowFlakesSheets_BCA.edds` (`P:\graphics\materials\postprocess\sandstorm.emat:13`).
- The Nasdara rain uses another postprocess shader, `RainEffect` (`P:\graphics\materials\postprocess\rainnasdara.emat:1`).

Do not name either file on the `Material` line of a `.ptc`.

The particle the weather config names is an ordinary `.ptc` with one emitter, `sand`: a `Box` shape with `MaxNum 200`, `BirthRate 20`, `LifeTime 5` and `Repeat 1`, using the material `sandstorm/dust_fluid_02.emat` (`P:\graphics\particles\sandstorm\sandstorm.ptc:4` to `:51`). It is not a `ParticleList` constant; the engine loads it from the weather config.

## Oil pits

`OilPitTrigger` picks one of two fire and smoke pairs in `UpdateState` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:90`):

- `ParticleList.OIL_FIRE1` with `BONFIRE_SMOKE` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:109`).
- `ParticleList.OIL_FIRE2` with `SMOKE_GENERIC_WRECK` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:114`).
- The light is a `BonfireLight` at `GetPosition() + "0 2.5 0"` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:98`).
- Both the start and the stop path test `IsHeadlessOrDedicatedServer` (`P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:37` and `P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:190`).

## Dust kickup from steps and bullets

`DustKickupEffects` (`P:\scripts\3_game\dustkickupeffects.c:43`) maps a surface to a particle and to distance bands. `SurfaceInfo` supplies the IDs through `GetDustKickupEffectId`, `GetDustKickupEffectSmallId` and `GetDustKickupEffectBigId` (`P:\scripts\3_game\surfaceinfo.c:59` to `:61`).

A custom `CfgSurfaces` class that should raise kickup dust, wheel dust or ceiling dust must fill those config entries, or the getters return `ParticleList.NONE`.

## New ParticleList constants

All of these are in the catalog (`vanilla-particle-catalog.md`). This list says which ones 1.30 added; line numbers are in `P:\scripts\3_game\particles\particlelist.c`. `STEP_DESERT` and `STEP_SOIL` (`:374` and `:375`) were already in 1.29.

| Constant | `.ptc` | Line |
|---|---|---|
| `TANDOOR_HOUSE_SMALL_FIRE` through `TANDOOR_HOUSE_FIRE_STEAM_2END` | `tandoor_fire_*`, `tandoor_smoke_*`, `tandoor_steam_*` | 49 to 54 |
| `EXPLOSION_GRENADE_SAND`, `EXPLOSION_GRENADE_DESERT_SAND` | `explosion_grenade_sand`, `explosion_grenade_desert_sand` | 145, 146 |
| `IMPACT_DESERT_SAND_*`, `IMPACT_MUD_BRICK_*` | `impacts/hit_desert_sand_*`, `impacts/hit_mud_brick_*` | 266 to 271 |
| `CEILING_WOOD` | `dust/dust_ceiling_wood`, registered with `RegisterParticleByFullPath` | 378 |
| `BUILDNG_DESTRUCT_WOOD`, `BUILDNG_DESTRUCT_BRICK`, `BUILDNG_DESTRUCT_METAL` | `building_destruction_*` | 381 to 383 |
| `VEHICLE_WHEEL_SOIL`, `VEHICLE_WHEEL_DESERT` | `vehicle_wheel_soil`, `vehicle_wheel_desert` | 390, 391 |
| `DUST_GROUND`, `DUST_CLOUD`, `DUST_VEHICLE`, `DUST_VEHICLE_SOFT` | `dust/dust_grnd_01`, `dust/dust_effect_01`, `dust_vehicle`, `dust_vehicle_soft` | 405 to 409 |
| `OIL_FIRE1`, `OIL_FIRE2` | `fire_oil1`, `fire_oil2` | 411, 412 |

`CEILING_WOOD` is the one constant registered by full path: `RegisterParticleByFullPath("graphics/particles/dust/dust_ceiling_wood")` (`P:\scripts\3_game\particles\particlelist.c:378`); the helper is declared at `P:\scripts\3_game\particles\particlelist.c:421`.
