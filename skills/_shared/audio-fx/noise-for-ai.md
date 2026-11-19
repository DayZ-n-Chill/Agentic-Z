# Noise for AI: making a sound that infected and animals hear

How to make the noise that infected and animals hear alongside a sound players hear, and how 1.30 moved weather damping into the engine. A sound set is what players hear; what the engine AI hears is a separate noise, made on the server through the noise system. How the AI reacts to noise is in the AI pack, `skills/_shared/ai/perception.md`. Line numbers are from the 1.30 files on `P:\`; statements about 1.29 are not yet checked on `P:\`.

## Contents

- [Sound and noise are two things](#sound-and-noise-are-two-things)
- [The calls](#the-calls)
- [Where the noise values come from](#where-the-noise-values-come-from)
- [Weather damping moved into the engine (1.30)](#weather-damping-moved-into-the-engine-130)

## Sound and noise are two things

- A sound set plays on clients only and no AI hears it.
- A noise is added on the server and no player hears it.

A device that should be both heard by players and noticed by infected needs both: the sound from `sound-script.md`, and a noise from the calls below.

## The calls

`NoiseSystem` (`P:\scripts\3_game\noise.c:1`), reached with `GetGame().GetNoiseSystem()` (`P:\scripts\3_game\global\game.c:738`):

| Line | Method | Use |
|---|---|---|
| 6 | `AddNoise(EntityAI source_entity, NoiseParams noise_params, float external_strenght_multiplier = 1.0)` | A noise at the entity. |
| 7 | `AddNoisePos(EntityAI source_entity, vector pos, NoiseParams noise_params, float external_strenght_multiplier = 1.0)` | A noise at a position, owned by an entity. |
| 10 | `AddNoiseTarget(vector pos, float lifetime, NoiseParams noise_params, float external_strength_multiplier = 1.0)` | A noise the AI keeps noticing at a position for `lifetime` seconds, with no entity. The tool for a distraction or decoy. |
| 13 | `GetEnvironmentNoiseReduction(vector pos)` | New in 1.30. How much the environment reduces noise at a point. |

`NoiseParams` (`P:\scripts\3_game\noise.c:16`) holds the strength and type of a noise and is loaded from config with `Load(string noise_name)` for a class of `CfgNoises`, or `LoadFromPath(string noise_path)` for any config path (`P:\scripts\3_game\noise.c:23` and `:25`).

## Where the noise values come from

Vanilla `CfgNoises` is small: `DeerStepNoise`, `DeerRoarNoise`, `WolfStepNoise`, `WolfRoarNoise`, `ZombieStepNoise` and `ZombieRoarNoise` (`P:\DZ\AI\config.cpp:6903`). Most vanilla noises are not there. They are classes inside the item, weapon or character config, loaded by path:

- The alarm clock: `LoadFromPath("cfgVehicles " + GetType() + " NoiseAlarmClock")` (`P:\scripts\4_world\entities\itembase\gear\tools\alarmclock.c:22`), then `AddNoiseTarget` on every tick while it rings (`P:\scripts\4_world\entities\itembase\gear\tools\alarmclock.c:142`).
- The flare: `LoadFromPath("cfgWeapons Flaregun_Base NoiseFlare")` (`P:\scripts\4_world\entities\firearms\flaresimulation.c:55`).
- Opening a door: `LoadFromPath("CfgVehicles SurvivorBase NoiseActionDefault")` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:83`), then `AddNoisePos` at the player (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:90`).
- A shot: `class NoiseShoot` in the weapon config. Its keys and the suppressor modifier are in `skills/_shared/weapons/muzzle-effects.md`.

The player's own noises come from the player type, not from `CfgNoises`:

- A step loads the noise of the stance: `GetNoiseParamsStand()`, `GetNoiseParamsCrouch()` or `GetNoiseParamsProne()`, with stand as the fallback for an unknown stance (`P:\scripts\4_world\entities\dayzplayerimplement.c:3460` to `:3470`).
- A landing adds `GetNoiseParamsLandLight()` for a fall under 3 m and `GetNoiseParamsLandHeavy()` for 3 m and more (`P:\scripts\4_world\entities\dayzplayerimplement.c:2530` to `:2555`).

For your own item, add a noise class to its config (copy the keys of a vanilla one, `strength` and `type`) and load it by path. Do not pass `"FlareLight"` or `"Footstep_Heavy"` to `Load()`; neither name is a class of `CfgNoises` on `P:\`. Use one of the six names above or a path.

A distraction noise, server side:

```c
// m_DecoyNoise is a member, so it is loaded once and not on every call
protected ref NoiseParams m_DecoyNoise;

void MyMod_MakeDecoyNoise(vector pos)
{
    if (!GetGame().IsServer())
        return;

    if (!m_DecoyNoise)
    {
        m_DecoyNoise = new NoiseParams();
        m_DecoyNoise.LoadFromPath("CfgVehicles MyMod_Decoy NoiseDecoy");
    }

    float lifetimeSeconds = 30;
    float strengthMultiplier = 2.0;
    GetGame().GetNoiseSystem().AddNoiseTarget(pos, lifetimeSeconds, m_DecoyNoise, strengthMultiplier);
}
```

An example of the shot noise on a mod rifle (third-party mod config, not vanilla): `class NoiseShoot { strength = 82; type = "shot"; }`. Vanilla values to compare with are in the weapons pack.

## Weather damping moved into the engine (1.30)

Up to 1.29, script lowered a noise for rain and wind: the step noise of a player was multiplied by `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())` (1.29, not yet checked on `P:\`).

Since 1.30 the engine does it, and the script helpers are marked obsolete:

- `GetEnvironmentNoiseReduction(vector pos)` is described in its comment as the single source of truth used by AI, covering weather, sandstorm and sea (`P:\scripts\3_game\noise.c:13`).
- `NoiseAIEvaluate.GetNoiseReduction(Weather weather)` is `Obsolete` (`P:\scripts\4_world\static\sensesaievaluate.c:92`), and so is `GetNoiseReductionEx`, whose message says the damping is now done natively through `AIParams` (`P:\scripts\4_world\static\sensesaievaluate.c:18`).
- `Weather.GetNoiseReductionByWeather()` is `Obsolete` (`P:\scripts\3_game\weather.c:454`), and `GetNoiseReductionByWeatherEx` too, kept for the HUD and old mods (`P:\scripts\3_game\weather.c:407`).
- The step noise of a player now passes only `NoiseAIEvaluate.GetNoiseMultiplier(this)`, which is speed, shoes and surface (`P:\scripts\4_world\entities\dayzplayerimplement.c:3472`).
- Infected add their noise with no multiplier at all: `AddNoise(this, sound_event.m_NoiseParams)` (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:600`).

The strength of the damping is config, in `class AIParams` (`P:\DZ\data\aiconfigs\config.cpp:12` to `:23`). Vanilla values:

| Key | Vanilla value |
|---|---|
| `maxNoiseRange` | 300 |
| `rainToNoiseMultiplier` | 10 |
| `snowfallToNoiseMultiplier` | 5 |
| `seaToNoiseMultiplier` | 15 |
| `fogToNoiseMultiplier` | 10 |
| `windToNoiseMultiplier` | 10 |
| `sandstormToNoiseMultiplier` | 10 |
| `noiseDampeningMultiplier` | 0.7 |
| `noiseCollisionDampeningMultiplier` | 0.2 |
| `noiseShotCollisionDampeningMultiplier` | 0.5 |

No script reads these keys; the engine does, so what each one does beyond its name is not checked on `P:\`. `AIParams` is a root class of the addon `DZ_data_aiconfigs` (`P:\DZ\data\aiconfigs\config.cpp:3`), so a mod changes it with a root `class AIParams` in its own `config.cpp` and `DZ_data_aiconfigs` in `requiredAddons[]`.

Rules for a mod:

- Do not multiply the strength you pass to `AddNoise` by a weather factor worked out in script. The engine already damps the noise at that position, and the noise would be damped twice.
- To show a player how well they are hidden, or to make a decision in script, read `GetEnvironmentNoiseReduction(pos)`.
- To change how much weather hides noise, change `AIParams` in config, not script.
- Do not call `GetNoiseReductionByWeather()` in new code.
