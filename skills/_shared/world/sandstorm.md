# Sandstorm

How script reaches the sandstorm, how much of it a player feels under shelter, what a world needs before storms happen, and what infected hear in one. The native controller lives in the game executable, so its growth and movement are not visible on `P:\`. What the storm does to lungs and eyes is in `dust-agents-and-protection.md`.

## Getting and starting a storm

Script never creates the controller. `SandstormController` has a private constructor and destructor (`P:\scripts\3_game\sandstorm.c:12`), and `Sandstorm` is a `typedef` of it (`sandstorm.c:135`). The weather object hands it out:

```c
// P:\scripts\3_game\weather.c:210
	proto native Sandstorm GetSandstorm();
```

The engine creates the scripted subclass that `GetScriptedType` names. From `P:\scripts\3_game\sandstorm.c:124`:

```c
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

| Call | Source | Notes |
|---|---|---|
| `Start(float duration, bool calledByWeather)` | `sandstorm.c:20` | Server only; returns `bool`. The storm must be inactive (`:14` to `:19`). |
| `Stop(float duration, bool calledByWeather)` | `sandstorm.c:27` | Server only. The storm must be active (`:21` to `:26`). |
| `IsActive()`, `GetMagnitude()` | `sandstorm.c:32`, `:83` | Their comments do not require an active storm. |
| `GetDirection()` | `:33` to `:37` | Direction from the start to the end position; its comment does not require an active storm. |
| `IsPositionAtEnd()`, `GetPosition()`, `GetSpeed()`, `GetRemainingMovementDuration()` | `:38` to `:57` | Need an active storm, per their comments. |
| `GetPointOnEdge(vector worldPosition, out vector outPosition)` | `:58` to `:65` | Needs an active storm. A negative distance means the position is inside the storm. |
| `GetIntensity(vector worldPosition)` | `:66` to `:71` | Needs an active storm. Raw intensity at a point, before shelter. |
| `GetIntensityForPlayer(Man player)` | `:72` to `:78` | Needs an active storm. A script method, not a `proto`; the scripted controller overrides it (below). |

Check `IsActive()` before any call that needs an active storm.

On the server, start a storm with `GetGame().GetWeather().GetSandstorm().Start(duration, false)` and end it with `.Stop(duration, false)`.

## Storm events and hooks

`OnStart`, `OnUpdate` (every tick while active) and `OnStop` are raised on the server and on every client; a client that joins a running storm still gets `OnStart` (`sandstorm.c:84` to `:117`). On the server `OnStart` and `OnStop` forward to `WorldData.WeatherSandstormStart` and `WeatherSandstormStop` (`:90` to `:97`, `:110` to `:117`). Those two are `sealed` (`P:\scripts\3_game\worlddata.c:495`, `:516`); the hooks a world data class overrides are `OnSandstormStart(bool isStartedByWeather)` and `OnSandstormStop(bool calledFromWeather)` (`worlddata.c:524`, `:528`).

When the weather itself starts a storm, `WorldData.StartSandstorm` sets `m_IsSandstormStartedByWeather` and calls `GetSandstorm().Start(timeToGather, true)` (`worlddata.c:477` to `:490`). `ScriptedSandstormController.OnStart` passes its two arguments to `super.OnStart` in swapped order (`P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:312`), so `WeatherSandstormStart` receives `calledByWeather` as `continuedSession` and reports any start with `calledByWeather` true as started by the weather (`worlddata.c:497` to `:510`). Start a storm from mod script with `calledByWeather` false so `OnSandstormStart` sees it as external.

On a client, `ScriptedSandstormController` has two `ScriptInvoker`s, `GetSandstormStartSI()` and `GetSandstormStopSI()` (`scriptedsandstormcontroller.c:376` to `:384`). They fire only on a machine that is not a dedicated server, because `OnStart` and `OnStop` return before invoking them there (`:315`, `:329` and `:330`; `:362`, `:372` and `:373`). Server logic hooks `OnSandstormStart` in the world data instead.

A new environmental hazard copies one of the two vanilla patterns: an `EffectArea` with a synced trigger (`oil-pits.md`), or a `Weather.GetSandstorm().Start` call from the map's `WorldData`.

## How much a player feels

`GetIntensityForPlayer` in the scripted controller (`P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:142` to `:178`) runs these steps in order:

1. Take the head position and read `GetIntensity`. Zero or less ends it with 0.
2. `ApplyUndergroundModifier` (`scriptedsandstormcontroller.c:180` to `:197`): an `EUndergroundPresence` of `TRANSITIONING` or `FULL` (`underground-presence.md`) counts as shelter. `ApplySurfaceDistanceModifier` then also fades the storm by depth when the player stands below `SurfaceY` (`:199` to `:211`; `MAX_SURFACE_DISTANCE` is 2.0 m). The whole step returns early when the player has a vehicle command (`:182` to `:184`).
3. If intensity is still above 0, `ApplyBuildingCheckModifier` (`:213` to `:248`): shelter needs both a roof found by `MiscGameplayFunctions.IsUnder(..., ObjIntersectIFire)` and `IsSoundInsideBuilding()` (`:222` to `:228`).
4. If intensity is still above 0, `ApplyVehicleModifier` (`:250` to `:282`): only a transport that passes `IsAnyInherited({Car})` shelters (`:265`).

The building and vehicle shelter fade is labelled 1.5 s, but the constant is applied to `g_Game.GetTime()`, which returns mission time in milliseconds (`P:\scripts\3_game\global\game.c:1534` to `:1535`), so the fade completes after 1.5 ms and building and vehicle shelter take effect at once (`:233` to `:247`, `:271` to `:281`). Underground shelter uses the same fade, but its timer `m_UndergroundTransitionTimer` is never set anywhere in vanilla script (`P:\scripts\4_world\systems\sandstorm\playersandstormdata.c:12`), so underground shelter takes effect at once. The fade time and the fade:

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

What this means for a mod:

- Only a `Car` shelters; a motorbike or boat does not, so a rider keeps squinting and collecting silicosis. A custom closed vehicle inherits from `Car`, or the mod overrides `GetIntensityForPlayer`.
- A roof alone is not shelter. `EXCLUDED_SHELTER_TYPES` is `{CrashBase, Plant}` (`scriptedsandstormcontroller.c:20`), so a wreck or a tree overhead never counts, and neither does an eave without `IsSoundInsideBuilding()`.
- A mod building shelters only when the player's sound environment reports "inside" and the roof check finds its Fire Geometry.

`PlayerSandstormData` keeps the state per player (`P:\scripts\4_world\systems\sandstorm\playersandstormdata.c:1`), keyed by player id in multiplayer and by `"-1"` in single player (`scriptedsandstormcontroller.c:49` to `:58`). `PlayerBase` removes a player's entry on disconnect with `CleanupDisconnectedPlayer` and `CheckConnectedPlayers` (`P:\scripts\4_world\entities\manbase\playerbase.c:7674` and `:7679`).

The underground step reads `GetUndergroundPresence()`, which the client reports to the server (`underground-presence.md`). On the server `SandstormExposureDynamicMdfr` doses agents from this intensity, so a client that reports `FULL` takes no storm agents.

## The client post process

On the client, `OnStart` asks for `PPERequesterBank.REQ_SANDSTORMEFFECT` and sets the target intensity (`scriptedsandstormcontroller.c:310` to `:327`), `OnUpdate` sets it again from `GetIntensityForPlayer` every tick (`:336` to `:352`), and `OnStop` sets it to 0 and stops the requester (`:357` to `:370`). The effect class is `PPERequester_SandstormEffect` (`P:\scripts\3_game\ppemanager\requesters\ppersandstorm.c:1`): amber color, saturation and god rays. Its material is a postprocess material, not a particle material; the shader, the tint and the storm's `.ptc` are in `dayz-particles/references/dayz-1-30-world-particles.md`, section "Sandstorm: a postprocess material, not a particle material".

## What a world needs

The world class needs a `Sandstorm` block with sound sets and a particle path. `CAWorld` defines it inside its `Weather` class (`P:\DZ\data\config.cpp:258` and `:260`), so a world that inherits `CAWorld` has it:

```cpp
// P:\DZ\data\config.cpp:1532 (CfgWorlds > CAWorld > Weather)
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

How often storms come is `sandstormFrequency` in `cfggameplay.json`. The class behind it, `ITEM_SandstormData`, starts at `P:\scripts\3_game\cfggameplaydatajson.c:440`, and the field is at `:458`:

```c
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

In the JSON this is `"SandstormData": { "sandstormFrequency": 1.0 }`, as in the Nasdara mission's file (`P:\DZ\worlds\nasdara\ce\cfggameplay.json:129` to `:131`). `CfgGameplayHandler.GetSandstormFrequency()` (`P:\scripts\3_game\cfggameplayhandler.c:533`) is copied into `m_sandstormFrequency` of the weather settings by `SetupWeatherSettings`, which clamps a negative value to 0 (`P:\scripts\3_game\worlddata.c:427` to `:442`).

## How Nasdara starts storms from the weather

Only the Nasdara world data starts storms from the weather. In bad weather its `CalculateWind` sets `sandstormChance` to 8 times `m_sandstormFrequency`, clamped to 0 to 100 (`P:\scripts\4_world\classes\worlds\nasdara.c:563` to `:575`), and sets `m_IsSandstorm`, with a wind magnitude from `m_SandstormMinWindMagnitude` 18 up to the maximum and a direction between `m_SandstormMinWindDirection` -1.77 and `m_SandstormMaxWindDirection` -1.20 (`nasdara.c:572` to `:574`; defaults at `P:\scripts\3_game\worlddata.c:594` to `:596`). On the overcast change it then calls `StartSandstorm(phmnTime * WIND_MAGNITUDE_TIME_MULTIPLIER)` (`nasdara.c:318` to `:322`). `ChernarusPlusData` never calls `StartSandstorm`; its world data file does not name it (`P:\scripts\4_world\classes\worlds\chernarusplus.c:31` is its `Init`).

On a custom map without a `CalculateWind` like Nasdara's, `sandstormFrequency` does nothing until something calls `Start`: a mission script or the map's own `WorldData` class. No vanilla map other than Nasdara does this, so a copy of Nasdara's pattern is unverified until it is seen working in game.

## What infected hear in a storm

Infected hearing in a storm is config, not script: `AIParams` has `sandstormToNoiseMultiplier=10` (`P:\DZ\data\aiconfigs\config.cpp:20`). Both script helpers are marked obsolete. `GetNoiseReductionByWeatherEx(notnull Object object)` carries the note that AI noise dampening is now native through `AIParams` and the method stays for the HUD and old mods (`P:\scripts\3_game\weather.c:407` and `:408`); the older `GetNoiseReductionByWeather()` points to the `Ex` form (`weather.c:454` and `:455`). Changing either from script does not change what infected hear. For the HUD or an old mod keep `GetNoiseReductionByWeatherEx(object)`; for infected hearing change `AIParams`. The noise system is in `_shared/ai/perception.md`.

## Checking a storm in game

On a local test server from `/dayz-launch-test`:

- Start: on the server, `GetGame().GetWeather().GetSandstorm().Start(5, false)`. The client gets the `REQ_SANDSTORMEFFECT` post process.
- Shelter: walk into a building that reports `IsSoundInsideBuilding`, and intensity reaches 0 at once. On a motorbike intensity does not drop; in a `Car` it does.
- Logs: search the RPT for `Could not get players sandstorm data`, the error `GetPlayerSandstormData` raises when it has no entry for a player (`scriptedsandstormcontroller.c:65` and `:69`).
