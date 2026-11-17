# DayZ 1.30: vanilla AI noise, the infected cower state, animal groups

What 1.30 changed in vanilla infected, animal and noise code: the engine now lowers noise for weather by itself, the old script helpers are obsolete, `AIParams` gained four multipliers, infected have a cower mind state, and the Nasdara map brings two animal group templates. None of this is Expansion AI; the Expansion patterns are in `eai-fsm-combat.md` and `eai-pathfinding-groups.md`.

Every block marked `[EXACT]` was read in the cited file on `P:\` and compared with the knowledge pack's copy. `[DESIGN]` is a recommendation, `[UNVERIFIED]` is not confirmed. What the knowledge pack reports for 1.29 or for the Nasdara data could not be read on `P:\` and is marked that way. The same facts, shorter, are in the AI pack: `skills/_shared/ai/perception.md` ("Weather and noise") and `skills/_shared/ai/creatures.md` ("Infected mind states").

## The engine lowers noise for weather by itself

Until 1.29, `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())` was multiplied into `AddNoise` from player steps and several other emitters (reported for 1.29; not on `P:\`).

Since 1.30 the engine applies the weather, sandstorm and sea reduction natively. Script can ask for the value:

```c
// [EXACT] P:\scripts\3_game\noise.c:12
	//! Absolute noise-strength reduction the environment (weather/sandstorm/sea) applies at 'pos'. Single source of truth used by AI.
	proto native float GetEnvironmentNoiseReduction(vector pos);
```

The debug display (not the AI itself) already reads it: `noiseSys.GetEnvironmentNoiseReduction(m_pPlayer.GetPosition())` at `P:\scripts\4_world\plugins\pluginbase\pluginpresencenotifier.c:155-158`.

Player steps no longer fold weather into the multiplier:

```c
// [EXACT] P:\scripts\4_world\entities\dayzplayerimplement.c:3472
			noiseMultiplier = NoiseAIEvaluate.GetNoiseMultiplier(this);
									
			AddNoise(noiseParams, noiseMultiplier);
```

Infected voice events pass no multiplier at all:

```c
// [EXACT] P:\scripts\4_world\entities\creatures\infected\zombiebase.c:597
		if (g_Game.IsServer())
		{
			if (sound_event.m_NoiseParams != NULL)
				GetGame().GetNoiseSystem().AddNoise(this, sound_event.m_NoiseParams);
		}
```

Two more vanilla emitters carry the comment `// weather dampening is now done engine-side` where a weather factor used to be: the animal trap (`P:\scripts\4_world\entities\itembase\trapspawnbase.c:648`) and the vehicle horn (`P:\scripts\4_world\entities\vehicles\components\vehiclehorncomponent.c:105`).

## Obsolete script weather helpers (kept for the HUD and old mods)

The official 1.30 changelog says `Weather.GetNoiseReductionByWeather` was removed. The method is still in script, marked obsolete:

```c
// [EXACT] P:\scripts\3_game\weather.c:454
	[Obsolete("Use Weather.GetNoiseReductionByWeatherEx instead!")]
	float GetNoiseReductionByWeather()
	{
		float rainReduction = GetRain().GetActual() * GameConstants.RAIN_NOISE_REDUCTION_WEIGHT;
		float snowfallReduction = GetSnowfall().GetActual() * GameConstants.SNOWFALL_NOISE_REDUCTION_WEIGHT;
		
		if (rainReduction == 0 && snowfallReduction == 0)
			return 1;
		
		if (rainReduction > snowfallReduction)	// combined phenomenons dont need to have multiplicative effects
			return 1 - rainReduction;
		else
			return 1 - snowfallReduction;
	}
```

Its replacement also sees the sandstorm. It is obsolete too, and it is not what the AI uses:

```c
// [EXACT] P:\scripts\3_game\weather.c:407
	[Obsolete("1.30: AI noise dampening is now done natively via AIParams config parameters. Kept for HUD and old mods.")]
	float GetNoiseReductionByWeatherEx(notnull Object object)
	{
		float rainReduction = GetRainNoiseReduction();
		float snowfallReduction = GetSnowfallNoiseReduction();
		float sandstormReduction = GetSandstormNoiseReduction(object);
```

```c
// [EXACT] P:\scripts\4_world\static\sensesaievaluate.c:92
	[Obsolete("Use GetNoiseReductionEx instead!")]
	static float GetNoiseReduction(Weather weather)
	{
		if (weather)
			return weather.GetNoiseReductionByWeather();
		 
		return 0;
	}
```

`NoiseAIEvaluate.GetNoiseReductionEx` (`P:\scripts\4_world\static\sensesaievaluate.c:18-26`) forwards to `GetNoiseReductionByWeatherEx` and carries the same 1.30 obsolete note. No other file under `P:\scripts` calls any of these four helpers.

## `AIParams` weather multipliers

Until 1.29 `AIParams` had `rainToNoiseMultiplier` and `seaToNoiseMultiplier` only (reported for 1.29 `DZ\data\aiconfigs\config.cpp:21-23`; not on `P:\`). Since 1.30:

```cpp
// [EXACT] P:\DZ\data\aiconfigs\config.cpp:12
class AIParams
{
	maxNoiseRange=300;
	rainToNoiseMultiplier=10;
	snowfallToNoiseMultiplier=5;
	seaToNoiseMultiplier=15;
	fogToNoiseMultiplier=10;
	windToNoiseMultiplier=10;
	sandstormToNoiseMultiplier=10;
	noiseDampeningMultiplier=0.69999999;
```

`[DESIGN]` To make infected hear less in a sandstorm, raise `sandstormToNoiseMultiplier` (or one of the other `*ToNoiseMultiplier` keys). Do not override `GetNoiseReductionByWeather` and expect the engine AI to follow.

## Infected `MINDSTATE_COWER`

```c
// [EXACT] P:\scripts\3_game\entities\dayzinfected.c:12
	//! mind states
	MINDSTATE_CALM,
	MINDSTATE_DISTURBED,
	MINDSTATE_ALERTED,
	MINDSTATE_CHASE,
	MINDSTATE_FIGHT,
	MINDSTATE_COWER,
```

```c
// [EXACT] P:\scripts\4_world\entities\creatures\infected\zombiebase.c:54
		RegisterNetSyncVariableInt("m_MindState", -1, 5);
```

```c
// [EXACT] P:\scripts\4_world\entities\creatures\infected\zombiebase.c:474
			//! sandstorm cowering, movement is already stopped by the AI, hold the calm idle pose
			case DayZInfectedConstants.MINDSTATE_COWER:
				if ( moveCommand && !moveCommand.IsTurning() )
					moveCommand.SetIdleState(0);
				break;
```

`[UNVERIFIED]` The native code that puts an infected into `MINDSTATE_COWER` from sandstorm strength is not in Enforce Script; only the script reaction above is visible.

## Animal group templates (Nasdara)

Reported by the knowledge pack from the Nasdara data of 1.30 (`DZ\data_takistan\aiconfigs\config.cpp` in his extraction, `GroupBehaviourTemplates` at `:14-132`); not yet checked on `P:\`, which has no Nasdara data. The vanilla templates that are on `P:\` (`DZWolfGroupBeh`, `DZDeerGroupBeh` and the rest) are in `P:\DZ\data\aiconfigs\config.cpp:77`; see `skills/_shared/ai/animal-territories.md`.

`DZMouflonGroupBeh` (his `:16`):

```cpp
	class DZMouflonGroupBeh
	{
		type = "DomesticHerbivores";
		alertDistributionSpeed = 20.0;
		groupMaxAlertedSpreadRadius = 40.0;
		catchUpTestDelay = 4.0;
		catchUpStartRadius = 30.0;
		catchUpTargetRadius = 12.0;
		groupRadius = 10.0;
```

`DZDogGroupBeh` (his `:68`):

```cpp
	class DZDogGroupBeh
	{
		type = "Predators";
		alertDistributionSpeed = 10.0;
		catchUpTestDelay = 4.0;
		catchUpStartRadius = 60.0;
		catchUpTargetRadius = 7.0;
		groupRadius = 10.0;
```

The dog life cycle uses `zoneType = "HuntingGround"` (his `:114`) with `siegeAttackCountdownMin = 10` and `siegeAttackCountdownMax = 15` (`:94-95`) and `safeKeeperIntervalMin = 20` and `safeKeeperIntervalMax = 40` (`:92-93`). For comparison, the wolf template on `P:\` is also `type="Predators"` and uses the `Rest` and `HuntingGround` zone types (`P:\DZ\data\aiconfigs\config.cpp:87-148`).

## Navmesh

The official 1.30 experimental modding changelog says the navmesh file is a newer version with no backward compatibility, so custom terrains must regenerate it, and that a navmesh can use a hide animation source if the EntityType navmesh config sets one up. Neither statement was checked against binary navmesh files by the knowledge pack's author or for Agentic-Z. It matters to any path code on a custom map, including Expansion's (PC-15 and PC-16 in `eai-pathfinding-groups.md`).
