# Sandstorm (DayZ 1.30)

How script reaches the 1.30 sandstorm, how much of it a player feels under shelter, what a world needs for storms to happen, and what infected hear in one. Checked on `P:\` (DayZ 1.30). The native controller itself lives in the game executable and was not inspected. What the storm does to a player's lungs and eyes is in `dust-agents-and-protection.md`.

## Getting and starting the storm

Script never creates the controller. `SandstormController` has a private constructor and destructor (`P:\scripts\3_game\sandstorm.c:12`), and `Sandstorm` is a `typedef` of it (`P:\scripts\3_game\sandstorm.c:135`). The weather object hands it out through `GetSandstorm` (`P:\scripts\3_game\weather.c:210`):

```c
// P:\scripts\3_game\weather.c:210
	proto native Sandstorm GetSandstorm();
```

The engine creates the scripted subclass named by `GetScriptedType`:

```c
// P:\scripts\3_game\sandstorm.c:124
	private static event typename GetScriptedType()
	{
		//
		// The following class is present in module 4_World and
		// hence its typename cannot be used directly in 3_Game.
		//
		string className = "ScriptedSandstormController";
		return className.ToType();
	}
```

| Call | Where | Notes |
|---|---|---|
| `Start(float duration, bool calledByWeather)` | `P:\scripts\3_game\sandstorm.c:20` | Server only. |
| `Stop(float duration, bool calledByWeather)` | `P:\scripts\3_game\sandstorm.c:27` | Server only. |
| `IsActive()`, `GetMagnitude()` | `sandstorm.c:32`, `:83` | Usable with no storm running. |
| `GetDirection()` | `sandstorm.c:33` to `:37` | Direction from the start to the end position. Its comment carries no active-storm note. |
| `IsPositionAtEnd()`, `GetPosition()`, `GetSpeed()`, `GetRemainingMovementDuration()` | `sandstorm.c:38` to `:57` | Need an active storm, per their comments. |
| `GetPointOnEdge(vector worldPosition, out vector outPosition)` | `sandstorm.c:65` | A negative distance means the position is inside the storm. |
| `GetIntensity(vector worldPosition)` | `sandstorm.c:71` | Raw intensity at a point, before shelter. |
| `GetIntensityForPlayer(Man player)` | `sandstorm.c:78` | A script method, not a `proto`; the scripted controller overrides it (below). |

On the server a storm is started with `GetGame().GetWeather().GetSandstorm().Start(duration, false)` and ended with `.Stop(duration, false)`.

The server side `OnStart` and `OnStop` events forward to `WorldData.WeatherSandstormStart` and `WeatherSandstormStop` (`P:\scripts\3_game\sandstorm.c:90` to `:116`). When the weather itself starts a storm, `WorldData.StartSandstorm` sets `m_IsSandstormStartedByWeather` and calls `GetSandstorm().Start(timeToGather, true)` (`P:\scripts\3_game\worlddata.c:477` to `:489`).

A new environmental hazard should copy a vanilla pattern: an `EffectArea` with a synced trigger (`oil-pits.md`), or a `Weather.GetSandstorm().Start` call from the map's `WorldData`.

## How much a player feels (shelter)

`GetIntensityForPlayer` in the scripted controller (`P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:142` to `:178`) runs these steps in order:

1. Take the head position and read `GetIntensity`. Zero or less ends it with 0.
2. `ApplyUndergroundModifier` (`scriptedsandstormcontroller.c:180` to `:197`): an `EUndergroundPresence` of `TRANSITIONING` or `FULL` (`underground-presence.md`) counts as shelter and fades in over 1.5 s. `ApplySurfaceDistanceModifier` then also fades the storm by depth when the player stands below `SurfaceY` (`:199` to `:211`, `MAX_SURFACE_DISTANCE` is 2.0 m). The whole step returns early when the player has a vehicle command (`:182` to `:184`).
3. If intensity is still above 0, `ApplyBuildingCheckModifier` (`:213` to `:248`): shelter needs both a roof found by `MiscGameplayFunctions.IsUnder(..., ObjIntersectIFire)` and `IsSoundInsideBuilding()` (`:222` to `:228`).
4. If intensity is still above 0, `ApplyVehicleModifier` (`:250` to `:282`): only a transport that passes `IsAnyInherited({Car})` shelters (`:265`).

The fade is the same for all three kinds of shelter:

```c
// P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:15
	private static const float INTERIOR_TRANSITION_DURATION = 1.5; // 1.5 seconds transition
```

```c
// P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:129
	protected void ApplyShelterFade(inout float intensity, bool isCurrentlySheltered, float transitionProgress)
	{
		if (isCurrentlySheltered)
		{
			intensity = Math.Lerp(intensity, 0.0, transitionProgress);
		}
		else
		{
			intensity = Math.Lerp(0.0, intensity, transitionProgress);
		}
	}
```

What follows from the code:

- A motorbike or a boat is not shelter; only `Car` is. A rider keeps squinting and collecting silicosis. A custom closed vehicle inherits from `Car`, or the mod overrides `GetIntensityForPlayer`.
- A roof alone is not shelter. `EXCLUDED_SHELTER_TYPES` is `{CrashBase, Plant}` (`scriptedsandstormcontroller.c:20`), so a wreck or a tree overhead never counts, and an eave without `IsSoundInsideBuilding()` does not either.
- A mod building shelters only when the player's sound environment reports "inside" and its Fire Geometry is found by the roof check.

State is kept per player in `PlayerSandstormData` (`P:\scripts\4_world\systems\sandstorm\playersandstormdata.c:1`), keyed by player id in multiplayer and by `"-1"` in single player (`scriptedsandstormcontroller.c:49` to `:58`).

## Client: post process

On the client, `OnStart` asks for `PPERequesterBank.REQ_SANDSTORMEFFECT` and sets the target intensity (`scriptedsandstormcontroller.c:310` to `:327`). The effect class is `PPERequester_SandstormEffect` (`P:\scripts\3_game\ppemanager\requesters\ppersandstorm.c:1`): amber color, saturation and god rays. Its material is a postprocess material, not a particle material; the shader, the tint and the storm's `.ptc` are in `dayz-particles/references/dayz-1-30-particles.md` ("Sandstorm: a postprocess material, not a particle material").

## World config: `class Sandstorm`

The world class needs a `Sandstorm` block with sound sets and a particle path. The default world has it:

```cpp
// P:\DZ\data\config.cpp:1532
			class Sandstorm
			{
				soundSets[]=
				{
					"SandStorm_Debris_SoundSet",
					"SandStorm_Close_SoundSet",
					"SandStorm_Dist_SoundSet"
				};
				particlePath="Graphics/Particles/sandstorm/sandstorm";
```

## `cfggameplay.json`: `sandstormFrequency`

```c
// P:\scripts\3_game\cfggameplaydatajson.c:440
class ITEM_SandstormData : ITEM_DataBase
{
	override void InitServer()
	{
	}
	
	override bool ValidateServer()
	{
		return true;
	}
	
	//-------------------------------------------------------------------------------------------------
	//!!! all member variables must correspond with the cfggameplay.json file contents !!!!
	
	/*!
	* \brief Rate at which the sandstorm should occur.
	* \note Example values: 0 => never occur, 1 => occur at normal rate, 2 => occur twice as frequently.
	*/ 
	float sandstormFrequency = 1.0;
};
```

In the JSON this is `"SandstormData": { "sandstormFrequency": 1.0 }`. `CfgGameplayHandler.GetSandstormFrequency()` (`P:\scripts\3_game\cfggameplayhandler.c:533`) is copied into `m_sandstormFrequency` of the weather settings by `SetupWeatherSettings`, which also clamps a negative value to 0 (`P:\scripts\3_game\worlddata.c:427` to `:442`).

## Nasdara: the weather trigger

Only the Nasdara world data starts storms from weather. In bad weather its `CalculateWind` computes `sandstormChance` as 8 times `m_sandstormFrequency`, clamped to 0 to 100 (`P:\scripts\4_world\classes\worlds\nasdara.c:563` to `:575`), and sets `m_IsSandstorm`. On the overcast change it then calls `StartSandstorm(phmnTime * WIND_MAGNITUDE_TIME_MULTIPLIER)` (`P:\scripts\4_world\classes\worlds\nasdara.c:318` to `:322`). `ChernarusPlusData` never calls `StartSandstorm`; its world data file does not name it (`P:\scripts\4_world\classes\worlds\chernarusplus.c:31` is its `Init`).

Design note: on a custom map with no `CalculateWind` like Nasdara's, `sandstormFrequency` does nothing until something calls `Start`, either a mission script or the map's own `WorldData` class. Copying Nasdara's pattern is a design step, not a copied recipe.

## AI hearing in a storm

Infected hearing in a storm is config, not script: `AIParams` has `sandstormToNoiseMultiplier=10` (`P:\DZ\data\aiconfigs\config.cpp:20`). Both script helpers are marked obsolete: `GetNoiseReductionByWeatherEx(notnull Object object)` with the note that AI noise dampening is now native through `AIParams` and the method is kept for the HUD and old mods (`P:\scripts\3_game\weather.c:407` to `:408`), and the older `GetNoiseReductionByWeather()` with a pointer to the `Ex` form (`P:\scripts\3_game\weather.c:454` to `:455`). Changing either from script does not change what infected hear: for the HUD or an old mod keep using `GetNoiseReductionByWeatherEx(object)`; for infected hearing change the `AIParams` config. The noise system is in `_shared/ai/perception.md`.

## Testing a storm in game

On a local test server from `/dayz-launch-test`:

- **Start:** on the server, `GetGame().GetWeather().GetSandstorm().Start(5, false)`. The client must get the `REQ_SANDSTORMEFFECT` post process.
- **Shelter:** walk into a building that reports `IsSoundInsideBuilding`; intensity reaches 0 within 1.5 s. Mount a motorbike: intensity must not drop. Get into a `Car`: it must.
- **Logs:** search the RPT for `Sandstorm`; the log text `Could not get players sandstorm data` was not confirmed against a real log.
