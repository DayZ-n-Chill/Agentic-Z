# Sound script: playing sound sets

How Enforce Script plays, loops, fades and stops a sound set, and how to clean it up. The sound set itself is written in config (`sound-config.md`).

Sounds are client only (Tier 2, `conventions/scripts.md`, "Client and server ownership"). PlaySoundSet, PlaySoundSetLoop and StopSoundSet do nothing on a dedicated server (object.c:1249, 1316). The memory point helpers (lines 1279 to 1311) have no server check, so put them behind `!GetGame().IsDedicatedServer()` yourself. The code around any helper (timers, fields, particles) needs the check too.

## The helpers on every Object

`P:\scripts\3_game\entities\object.c`:

| Line | Signature | What it does |
|---|---|---|
| 1247 | `bool PlaySoundSet(out EffectSound sound, string sound_set, float fade_in, float fade_out, bool loop = false)` | Plays the set on this object, following it as it moves. Returns false on a dedicated server. Sets autodestroy on the new sound. |
| 1273 | `bool PlaySoundSetLoop(out EffectSound sound, string sound_set, float fade_in, float fade_out)` | `PlaySoundSet` with `loop = true`. |
| 1294 | `bool PlaySoundSetAtMemoryPoint(out EffectSound sound, string soundSet, string memoryPoint, bool looped = false, float play_fade_in = 0, float stop_fade_out = 0)` | Plays at the world position of a memory point in the model. The sound stays at that spot; it does not follow the object. Logs an error and returns false when the point is missing. |
| 1288 | `bool PlaySoundSetAtMemoryPointLooped(...)` | The looped form of the one above. |
| 1279 | `bool PlaySoundSetAtMemoryPointLoopedSafe(...)` | Stops the sound in `sound` first if it is playing, then plays looped. |
| 1314 | `bool StopSoundSet(out EffectSound sound)` | Stops the sound and sets your variable to `null`. |

Two rules hidden in `PlaySoundSet` (lines 1251 to 1260):

- Called with `loop = true` while your variable still holds a sound, it returns true and plays nothing new. To restart a loop, call `StopSoundSet` first. The vanilla generator does this when it swaps to the low fuel loop (`P:\scripts\4_world\entities\itembase\powergenerator.c:257`).
- Called with `loop = false` while your variable holds a sound, it stops the old one before playing the new one.

`PlaySound` and `PlaySoundLoop` on the same class (lines 1235 and 1241) take a `CfgSounds` name and a range, not a sound set. Use the sound set helpers for new work.

## SEffectManager

`P:\scripts\3_game\effectmanager.c`. Use these when the sound is not tied to an object, or you need the `EffectSound` before it plays.

| Line | Signature | Use |
|---|---|---|
| 178 | `static EffectSound PlaySound(string sound_set, vector position, float play_fade_in = 0, float stop_fade_out = 0, bool loop = false)` | One sound at a world position. |
| 237 | `static EffectSound PlaySoundEnviroment(string sound_set, vector position, float play_fade_in = 0, float stop_fade_out = 0, bool loop = false)` | Same, and adds the environment sound variables at that spot (the spelling is vanilla's). |
| 256 | `static EffectSound PlaySoundOnObject(string sound_set, Object parent_object, float play_fade_in = 0, float stop_fade_out = 0, bool loop = false)` | Plays on an object and follows it. This is what `Object.PlaySoundSet` calls. |
| 153 | `static EffectSound CreateSound(string sound_set, vector position, ...)` | Creates and registers without playing. Call `SoundPlay()` on it later. |
| 280 | `static void DestroyEffect(Effect effect)` | Stops, unregisters and frees. If a fade out is still running, it lets the sound finish and then frees it. |

The manager keeps a strong reference to every effect it registers (warning at line 3, and at line 40 for `PlayInWorld`). An effect is freed only when it has autodestroy set and stops, or when you call `DestroyEffect`. A sound you play through `SEffectManager` directly and never destroy stays in memory. `PlaySoundSet` and `PlaySoundSetLoop` set autodestroy for you (object.c line 1264). The memory point helpers do not set autodestroy. `StopSoundSet` only stops their sound and sets your variable to null, and the manager still holds it. Free their sound with `SEffectManager.DestroyEffect(sound)`, which stops it and frees it once any fade out ends (effectmanager.c:280), or call `sound.SetAutodestroy(true)` right after the helper returns true so the sound frees itself when it stops (`P:\scripts\3_game\effect.c:336`).

## EffectSound

`P:\scripts\3_game\effects\effectsound.c`, class at line 4.

| Line | Method | Note |
|---|---|---|
| 199 | `bool SoundPlay()` | Starts the sound. |
| 217 | `void SoundStop()` | Stops it. With a fade out set, it fades first instead of stopping at once. |
| 816 | `void SetSoundLoop(bool loop)` | Loops the playing wave. The loop flag is applied again when the wave starts (line 383), so a script loop works even when the set says `loop=0`. The vanilla generator relies on this: `powerGeneratorLoop_SoundSet` has `loop=0` (`P:\DZ\sounds\hpp\config.cpp:319409`) and is played with `PlaySoundSetLoop` (`powergenerator.c:95`). |
| 856 | `void SetSoundVolume(float volume)` | Relative volume on top of the config volume. |
| 899, 908 | `SetSoundFadeIn(float)`, `SetSoundFadeOut(float)` | Fade times in seconds. |
| 607 | `override void SetAutodestroy(bool auto_destroy)` | Free the effect when it stops. |
| 11 | `ref ScriptInvoker Event_OnSoundWaveEnded` | Fires when the wave ends. Also `Event_OnSoundWaveStarted`, `Event_OnSoundFadeInStopped`, `Event_OnSoundFadeOutStarted` (lines 10 to 13). |

## Worked example: start, loop and stop

This is the shape of the vanilla generator (`P:\scripts\4_world\entities\itembase\powergenerator.c`), with mod names:

```c
class MyMod_Generator extends ItemBase
{
    static const string START_SOUND = "MyMod_GeneratorStart_SoundSet";
    static const string LOOP_SOUND  = "MyMod_GeneratorLoop_SoundSet";
    static const string STOP_SOUND  = "MyMod_GeneratorStop_SoundSet";

    protected EffectSound m_EngineStart;
    protected EffectSound m_EngineLoop;
    protected EffectSound m_EngineStop;

    override void OnWorkStart()
    {
        super.OnWorkStart();
        if (!GetGame().IsDedicatedServer())
        {
            PlaySoundSet(m_EngineStart, START_SOUND, 0, 0);
            PlaySoundSetLoop(m_EngineLoop, LOOP_SOUND, 0.3, 0.3);
        }
    }

    override void OnWorkStop()
    {
        super.OnWorkStop();
        if (!GetGame().IsDedicatedServer())
        {
            PlaySoundSet(m_EngineStop, STOP_SOUND, 0, 0);
            StopSoundSet(m_EngineLoop);
        }
    }

    override void EEDelete(EntityAI parent)
    {
        super.EEDelete(parent);
        StopSoundSet(m_EngineLoop);
    }
}
```

Vanilla differences worth knowing:

- Vanilla tests `g_Game.IsClient() || !g_Game.IsMultiplayer()` (lines 88, 147, 196). That is the same as "not a dedicated server" for a player, and also covers single player. Either form works; Tier 2 prefers `!GetGame().IsDedicatedServer()`.
- Vanilla starts the loop 1.5 seconds after the start sound with a `Timer` (line 161) so the start sound plays first. A `startDelay` in the loop set (`startDelay=1.2`, `P:\DZ\sounds\hpp\config.cpp:319412`) does a similar job in config.
- The vanilla destructor frees the smoke effect (line 38) but not the loop sound. Stop loops yourself in `EEDelete` so a deleted device goes quiet.

## Starting a sound from the server

The server cannot play sounds. When the server decides a sound should play, send that to clients and let each client play it:

- For a one-shot, register a signal bool: `RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundLight")` (`P:\scripts\4_world\entities\vehicles\carscript.c:280`). The doc comment says the value is sent to clients while true and then becomes false again (`P:\scripts\3_game\entities\entityai.c:2835` to `2840`). The client plays the sound in `OnVariablesSynchronized()` (`carscript.c:435` to `442`). `ItemBase` uses the same pattern for impact sounds (`P:\scripts\4_world\entities\itembase.c:194`).
- For a state that lasts (running, stopped), sync a bool or int and start or stop the loop in `OnVariablesSynchronized()` when it changes. Pattern: `.claude/skills/_shared/enscript/patterns/netsync.md`.
- Energy devices are simpler: the energy manager's `DeviceUpdate` runs on clients too and calls `OnWorkStart` and `OnWorkStop` there; only the energy use is limited to the server (`P:\scripts\3_game\tools\component\componentenergymanager.c:1781` to `1840`). That is why the vanilla generator plays its sounds in those two events.
