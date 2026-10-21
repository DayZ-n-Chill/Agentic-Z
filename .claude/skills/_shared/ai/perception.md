# Perception: noise, visibility and reacting to gunfire

How the engine AI notices players and sounds, and how a mod can make noises or react to shots.

## Noise system

`NoiseSystem` (`P:\scripts\3_game\noise.c:1`), from `GetGame().GetNoiseSystem()` (`P:\scripts\3_game\global\game.c:738`):

- `AddNoise(EntityAI source_entity, NoiseParams noise_params, float external_strenght_multiplier = 1.0)` (`noise.c:6`): a noise at the entity.
- `AddNoisePos(EntityAI source_entity, vector pos, NoiseParams noise_params, float external_strenght_multiplier = 1.0)` (`:7`): a noise at a position, owned by an entity.
- `AddNoiseTarget(vector pos, float lifetime, NoiseParams noise_params, float external_strength_multiplier = 1.0)` (`:10`): a noise the AI keeps "seeing" at that position for `lifetime` seconds.
- `GetEnvironmentNoiseReduction(vector pos)` (`:13`): how much weather and sea reduce noise at a point.

`NoiseParams` (`noise.c:16`) loads a noise from config: `Load(string noise_name)` reads `CfgNoises`, `LoadFromPath(string noise_path)` reads any config path.

Vanilla makes noise only on the server. Examples in `P:\scripts\3_game\dayzgame.c`:

- Explosions: `LoadFromPath("cfgAmmo <ammo> NoiseExplosion")`, then `AddNoiseTarget(pos, 21, ...)` (`:3612` to `:3618`).
- Bullet impacts: `NoiseHit` from the ammo, `AddNoiseTarget(pos, 10, ...)` (`:3786` to `:3793`).
- Melee impacts: `AddNoisePos` with the surface multiplier (`:3833`).

A fake gunshot or alarm that pulls infected to a point:

```c
// server only; m_AlarmNoise is a member so it is not rebuilt every call
if (GetGame().IsServer())
{
    if (!m_AlarmNoise)
    {
        m_AlarmNoise = new NoiseParams();
        m_AlarmNoise.LoadFromPath("CfgWeapons AKM NoiseShoot");
    }
    GetGame().GetNoiseSystem().AddNoiseTarget(alarmPos, 10, m_AlarmNoise);
}
```

`AKM` with its `NoiseShoot` class is in `cfgWeapons` in `P:\DZ\weapons\firearms\akm\config.cpp` (`:82` inside `AKM_Base` at `:26`; `AKM` at `:191` inherits it). Infected hear a shot out to `rangeShotMax` 110 m (`P:\DZ\AI\config.cpp:6383`).

## What makes a player visible

- Clothing: `PlayerBase.CalculateVisibilityForAI` (`P:\scripts\4_world\entities\manbase\playerbase.c:5405`) averages each worn item's visibility over ten slots and stores it with `SetVisibilityCoef` (`:5438`). Read it with `GetVisibilityCoef()` (`:5443`).
- Stance and speed: `AITargetCallbacksPlayer.GetMaxVisionRangeModifier` (`P:\scripts\4_world\entities\manbase\playerbase\aitargetcallbacksplayer.c:45`) averages a speed factor and a stance factor. The factors are in `PlayerConstants` (`P:\scripts\3_game\playerconstants.c:263` to `:268`): run 1, walk 0.66, idle 0.3, standing 1.5, crouch 0.6, prone 0.15.
- The base callback class is `AITargetCallbacks` (`P:\scripts\3_game\systems\ai\aitarget_callbacks.c:8`): head position, vision point and the range modifier.
- Range, field of view and weather factors come from the template's `TargetSystemDZBase` (see `behaviour-config.md`).

## Reacting to gunfire in script

The engine AI already reacts to shot noise for infected and animals. For your own behaviour (a guard that turns toward shots, an alarm), you need to see the shot yourself:

- `EntityAI.EEFired(int muzzleType, int mode, string ammoType)` (`P:\scripts\3_game\entities\entityai.c:4927`) is called when a weapon fires; `Weapon_Base` overrides it (`P:\scripts\4_world\entities\firearms\weapon_base.c:341`). Vanilla wraps its muzzle effects in `!g_Game.IsHeadlessOrDedicatedServer()`, which shows the event reaches the server too. Confirm which side your code runs on in the in game test before relying on it.
- In a `modded class Weapon_Base`, call `super.EEFired(...)` first, then on the server hand the shooter and position to your own manager. Do not search for nearby guards inside `EEFired`; that runs for every shot on the server. Let the manager hold a list of guards and check distance squared against it.
- For a cheaper signal, reuse the fake noise above: let the engine AI do the hearing and read the result from the input controller (`GetMindState()`, `GetTargetEntity()`).
</content>
</invoke>
