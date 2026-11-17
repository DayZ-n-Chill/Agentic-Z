# DayZ sound system: the full reference

Every part of mod audio in one file: the pipeline, the config classes, the full script signatures, item and player sounds, sync patterns, music, the noise system, environment controllers, calls that do not exist, and recipes. Line numbers are from the 1.30 scripts on `P:\`. Statements about 1.29 come from the notes this file was built from and are not yet checked on `P:\`.

Two third-party mods serve as worked examples: IMPWMODPart2 (weapon sounds) and DoorLockSystem (door sounds). Facts about them are from their own files and are not checked on `P:\`. The running example is a rolling stone item, `MyMod_RollingStone`, with a roll loop and an impact sound.

The pack `skills/_shared/audio-fx/` holds the same systems as shorter how-to files. Open this file when you need a complete signature list.

## Contents

- [Summary](#summary)
- [The audio pipeline](#the-audio-pipeline)
- [Config](#config)
- [Script API](#script-api)
- [Sounds on items](#sounds-on-items)
- [Sync patterns in multiplayer](#sync-patterns-in-multiplayer)
- [Player sounds](#player-sounds)
- [Music: DynamicMusicPlayer](#music-dynamicmusicplayer)
- [NoiseSystem](#noisesystem)
- [Environment sound controllers](#environment-sound-controllers)
- [Calls that do not exist, and common wrong beliefs](#calls-that-do-not-exist-and-common-wrong-beliefs)
- [Recipes](#recipes)
- [DayZ 1.30: radios, vegetation, destructor](#dayz-130-radios-vegetation-destructor)
- [Sources](#sources)

## Summary

The sound system has two layers:

1. Config, with no script: `CfgSoundShaders` and `CfgSoundSets` in `config.cpp` say which file plays, how loud, and how it fades with distance. The engine places the sound in 3D.
2. Script: `EffectSound` and `SEffectManager`, on clients only. The server cannot play a sound. In multiplayer a sound is synced through a network variable and `OnVariablesSynchronized`, or through the item sound handler.

For the rolling stone, the simplest route is a sound set in config, played on the client with `PlaySoundSet` or `SEffectManager.PlaySoundOnObject` from an event that is already synced (for example `OnVariablesSynchronized`, or a local contact).

## The audio pipeline

### Formats

- Vanilla samples are `.ogg` files; `P:\DZ\sounds\` holds them. The source notes add that `.wav` is accepted too and that mods in practice ship `.ogg` (not checked on `P:\`).
- `.wss` is Bohemia's own compressed sound format. DayZ mods use `.ogg` directly (source notes, not checked on `P:\`).
- A sample is named in `CfgSoundShaders` without its extension. Third-party example: `"IMPWMODPart2\Weapons\Automatic\F2000\Sounds\F2000_close"` in the F2000 sound config of IMPWMODPart2.

### Where the files live in a mod

```
MyMod/
  Sounds/           the .ogg files
  config.cpp        CfgSoundShaders, CfgSoundSets
  scripts/          Enforce Script
```

Paths in `samples[]` start at the mod's prefix, the same as model paths.

## Config

The keys of both classes, with vanilla evidence for each, are in `skills/_shared/audio-fx/sound-config.md`. This section keeps the third-party examples.

### CfgSoundShaders

A shader names the audio files, the volume, the range and the fade curve. Keys seen in the IMPWMODPart2 weapon sound config:

| Key | Type | Meaning |
|---|---|---|
| `samples[]` | list of `{path, weight}` pairs | The samples, each with a weight for random choice |
| `volume` | number | Base volume |
| `range` | number | The farthest distance, in meters, at which the sound is heard |
| `rangeCurve[]` | list of `{distance, factor}` pairs | Fade over distance, written inline |
| `rangeCurve` | string | The name of a predefined curve, such as `"closeShotCurve"` |

A shader with no parent and an inline curve (IMPWMODPart2, `Weapons\Automatic\Sounds\config.cpp`):

```cpp
class IMP_SoundShaderMid
{
    samples[] = {{"IMPWMODPart2\Weapons\Automatic\Sounds\Rifle1Mid", 1}};
    volume = 0.56234133;
    range = 1500;
    rangeCurve[] =
    {
        {0,   0.2},
        {50,  1},
        {300, 0},
        {1500,0}
    };
};
```

A shader that inherits a vanilla base, the cleanest form for a mod (IMPWMODPart2, `Weapons\Automatic\F2000\Sounds\config.cpp`):

```cpp
class base_closeShot_SoundShader;   // declare the vanilla parent first
class IMP_F2000_closeShot_SoundShader: base_closeShot_SoundShader
{
    samples[] = {{"IMPWMODPart2\Weapons\Automatic\F2000\Sounds\F2000_close", 1}};
    volume = 0.8;
};
```

The vanilla parent `base_closeShot_SoundShader` is at `P:\DZ\sounds\hpp\config.cpp:17117`, and the curve `closeShotCurve` at `P:\DZ\sounds\hpp\config.cpp:930`.

### CfgSoundSets

A set groups shaders under one name that script and config refer to. Its one required key is `soundShaders[]`, the list of shader names. The other keys (`sound3DProcessingType`, `volumeCurve`, `spatial` and more) were marked as unverified in the source notes; they are verified with vanilla lines in `skills/_shared/audio-fx/sound-config.md`.

A set that inherits a vanilla base (same IMPWMODPart2 file):

```cpp
class CfgSoundSets
{
    class Rifle_Shot_Base_SoundSet;   // declare the vanilla parent first
    class IMP_F2000_Shot_SoundSet: Rifle_Shot_Base_SoundSet
    {
        soundShaders[] = {
            "IMP_F2000_closeShot_SoundShader",
            "IMP_F2000_midShot_SoundShader",
            "IMP_F2000_distShot_SoundShader"
        };
    };
};
```

The vanilla parent `Rifle_Shot_Base_SoundSet` is at `P:\DZ\sounds\hpp\config.cpp:323687`.

A plain set with no parent, enough for an item or an alarm. One shader is enough for a simple effect:

```cpp
class CfgSoundSets
{
    class MyMod_Roll_SoundSet
    {
        soundShaders[] = {"MyMod_Roll_SoundShader"};
    };
};
```

### Curves and 3D processing

- `CfgSoundCurves` holds the named volume curves (`P:\DZ\sounds\hpp\config.cpp:59`). Mods refer to them by name.
- The 3D processing classes are in `CfgSound3DProcessors` (`P:\DZ\sounds\hpp\config.cpp:2587`). The source notes called this class `CfgSound3DProcessingTypes` and could not find it; the key on a sound set is `sound3DProcessingType`, and the root class it points into is `CfgSound3DProcessors`.

## Script API

### Core types

All in `P:\scripts\3_game\sound.c`.

```
// P:\scripts\3_game\sound.c:1
enum WaveKind
{
    WAVEEFFECT, WAVEEFFECTEX, WAVESPEECH, WAVEMUSIC,
    WAVESPEECHEX, WAVEENVIRONMENT, WAVEENVIRONMENTEX,
    WAVEWEAPONS, WAVEWEAPONSEX, WAVEATTALWAYS, WAVEUI
}
```

`SoundParams` loads a sound set by name and says whether it is valid:

```
// P:\scripts\3_game\sound.c:137
class SoundParams
{
    void SoundParams(string name);
    proto native bool Load(string name);
    proto native bool IsValid();
    proto string GetName();
}
```

`SoundObjectBuilder` builds a `SoundObject` and carries the sound variables:

```
// P:\scripts\3_game\sound.c:82
class SoundObjectBuilder
{
    void SoundObjectBuilder(SoundParams soundParams);
    SoundObject BuildSoundObject();                        // calls g_Game.GetSoundScene().BuildSoundObject
    proto native void Initialize(SoundParams soundParams);
    proto native void AddEnvSoundVariables(vector position);
    proto native void AddVariable(string name, float value);
    proto void AddVariables(notnull array<string> names, array<float> values = null);
}
```

`SoundObject` is the source in the world:

```
// P:\scripts\3_game\sound.c:111
class SoundObject
{
    proto native void SetParent(IEntity parent, int pivot = -1);
    proto native IEntity GetParent();
    proto native void SetPosition(vector position);        // local to the parent when there is one
    proto native vector GetPosition();
    proto native void SetSpeed(vector speed);
    proto native void SetOcclusionObstruction(float occlusion, float obstruction);
    proto native void SetKind(WaveKind kind);
}
```

`AbstractWave` is the handle of a playing sound:

```
// P:\scripts\3_game\sound.c:155
class AbstractWave
{
    proto void Play();
    proto void Stop();
    proto void Restart();
    proto void SetStartOffset(float offset);
    proto float GetLength();                      // blocks until the header has loaded
    proto float GetCurrPosition();                // fraction of the total length
    proto void Loop(bool setLoop);
    proto float GetVolume();
    proto void SetVolume(float value);
    proto void SetVolumeRelative(float value);    // relative to the config volume
    proto void SetFrequency(float value);         // a pitch factor, see the recipes
    proto float GetFrequency();
    proto void SetPosition(vector position, vector velocity = "0 0 0");
    proto void SetFadeInFactor(float volume);
    proto void SetFadeOutFactor(float volume);
    proto void SetDoppler(bool setDoppler);
    proto void Skip(float timeSec);
    proto bool IsHeaderLoaded();
    AbstractWaveEvents GetEvents();               // the ScriptInvoker events below
}
```

`AbstractWaveEvents` holds the events of one wave:

```
// P:\scripts\3_game\sound.c:146
class AbstractWaveEvents
{
    ref ScriptInvoker Event_OnSoundWaveStarted;
    ref ScriptInvoker Event_OnSoundWaveStopped;
    ref ScriptInvoker Event_OnSoundWaveLoaded;
    ref ScriptInvoker Event_OnSoundWaveHeaderLoaded;
    ref ScriptInvoker Event_OnSoundWaveEnded;
}
```

`AbstractSoundScene` is the engine's sound scene, reached with `g_Game.GetSoundScene()` (`P:\scripts\3_game\global\game.c:735`):

```
// P:\scripts\3_game\sound.c:53
proto native AbstractWave Play2D(SoundObject soundObject, SoundObjectBuilder soundBuilder);
proto native AbstractWave Play3D(SoundObject soundObject, SoundObjectBuilder soundBuilder);
proto native SoundObject BuildSoundObject(SoundObjectBuilder soundObjectbuilder);
proto native float GetRadioVolume();
proto native void SetRadioVolume(float vol, float time);
proto native float GetSpeechExVolume();
proto native void SetSpeechExVolume(float vol, float time);
proto native float GetMusicVolume();
proto native void SetMusicVolume(float vol, float time);
proto native float GetSoundVolume();
proto native void SetSoundVolume(float vol, float time);    // the volume of the whole category
proto native float GetVOIPVolume();
proto native void SetVOIPVolume(float vol, float time);
```

### SEffectManager

The static manager of effects, sounds and particles alike, in `P:\scripts\3_game\effectmanager.c`. Its sound maps exist on clients only: `Init()` is called when the game is not a dedicated server (`P:\scripts\3_game\global\game.c:58`).

```
// P:\scripts\3_game\effectmanager.c:153
// Create and register, without playing
static EffectSound CreateSound(string sound_set, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false, bool enviroment = false);

// P:\scripts\3_game\effectmanager.c:178
// Create and play at a position
static EffectSound PlaySound(string sound_set, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// P:\scripts\3_game\effectmanager.c:197
// Create and play from SoundParams you already built
static EffectSound PlaySoundParams(notnull SoundParams params, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// P:\scripts\3_game\effectmanager.c:216
// The same, with the manager caching the SoundParams of each set name
static EffectSound PlaySoundCachedParams(string sound_set, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// P:\scripts\3_game\effectmanager.c:237
// With the environment variables at that position
static EffectSound PlaySoundEnviroment(string sound_set, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// P:\scripts\3_game\effectmanager.c:256
// Create and play on an object, following it
static EffectSound PlaySoundOnObject(string sound_set, Object parent_object,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// P:\scripts\3_game\effectmanager.c:280
// Safe cleanup; lets a running fade out finish
static void DestroyEffect(Effect effect);

// P:\scripts\3_game\effectmanager.c:441
// Older form for sounds
static bool DestroySound(EffectSound sound_effect);
```

Every `Play` method registers the effect, and the manager keeps a strong reference to it. The vanilla warning is at the top of the class: it "Keeps a ref to any Effect registered" (`P:\scripts\3_game\effectmanager.c:3`). Without `DestroyEffect` or `SetAutodestroy(true)` the effect stays in memory.

### EffectSound

The high level wrapper around a wave, in `P:\scripts\3_game\effects\effectsound.c`:

```
// P:\scripts\3_game\effects\effectsound.c:4
class EffectSound : Effect
{
    void SetSoundSet(string snd);
    void SetSoundLoop(bool loop);
    void SetSoundFadeIn(float fade_in);
    void SetSoundFadeOut(float fade_out);
    void SetSoundVolume(float volume);         // relative, 0 to 1
    void SetSoundMaxVolume(float volume);      // the level a fade in rises to
    void SetSoundWaveKind(WaveKind wave_kind);
    void SetDoppler(bool setDoppler);
    void SetEnviromentVariables(bool setEnvVariables);
    bool SoundPlay();
    void SoundStop();                          // fades out first when a fade out is set
    bool IsSoundPlaying();
    float GetSoundWaveLength();

    // its own events:
    ref ScriptInvoker Event_OnSoundWaveStarted;
    ref ScriptInvoker Event_OnSoundWaveEnded;
    ref ScriptInvoker Event_OnSoundFadeInStopped;
    ref ScriptInvoker Event_OnSoundFadeOutStarted;
}
```

Since 1.30, when the fade in time is above zero, `Event_OnSoundWaveStarted` calls `SetSoundVolume(0)`, so the first frame is silent (`P:\scripts\3_game\effects\effectsound.c:549`). The quoted lines are in `dayz-1-30-sound.md`.

### Object.PlaySoundSet

The helpers on every object, in `P:\scripts\3_game\entities\object.c`:

```
// P:\scripts\3_game\entities\object.c:1247
bool PlaySoundSet(out EffectSound sound, string sound_set, float fade_in, float fade_out, bool loop = false);
// P:\scripts\3_game\entities\object.c:1273
bool PlaySoundSetLoop(out EffectSound sound, string sound_set, float fade_in, float fade_out);
// P:\scripts\3_game\entities\object.c:1294
bool PlaySoundSetAtMemoryPoint(out EffectSound sound, string soundSet, string memoryPoint,
    bool looped = false, float play_fade_in = 0, float stop_fade_out = 0);
// P:\scripts\3_game\entities\object.c:1314
bool StopSoundSet(out EffectSound sound);
```

`PlaySoundSet`, `PlaySoundSetLoop` and `StopSoundSet` do nothing on a dedicated server: the test is `g_Game && !g_Game.IsDedicatedServer()` (`P:\scripts\3_game\entities\object.c:1249`). The source notes said all four helpers have that test. `PlaySoundSetAtMemoryPoint` does not: its body goes straight to the memory point lookup and `SEffectManager.PlaySoundEnviroment` (`P:\scripts\3_game\entities\object.c:1294`), so guard it yourself, as `skills/_shared/audio-fx/sound-script.md` says.

`PlaySoundSet` on `Object` kept the dedicated server test in 1.30. The item and player sound handlers moved to `IsHeadlessOrDedicatedServer()`.

### CreateSoundOnObject

```
// P:\scripts\3_game\global\game.c:692
proto native SoundOnVehicle CreateSoundOnObject(Object source, string sound_name, float distance, bool looped, bool create_local = false);
proto native SoundWaveOnVehicle CreateSoundWaveOnObject(Object source, SoundObject soundObject, AbstractWave soundWave);
```

`SoundOnVehicle` is an entity class, not an `EffectSound`:

```
// P:\scripts\3_game\entities\soundonvehicle.c:1
class SoundOnVehicle extends Entity
{
    proto native float GetSoundLength();
};
```

It is a different route from `SEffectManager`. `Object.PlaySound` and `Object.PlaySoundLoop` wrap it (`P:\scripts\3_game\entities\object.c:1235`). For item mods prefer `SEffectManager.PlaySoundOnObject`.

### Volume by category

`AbstractSoundScene` sets the volume of whole categories (sound, music, radio, speech, VOIP). There is no call for one sound beyond `SetVolumeRelative` on its wave and `SetSoundVolume` on its `EffectSound`.

## Sounds on items

### The item sound handler: server to client

The official way to start a sound on the server and hear it on all clients.

1. The IDs are in `SoundConstants`:

   ```
   // P:\scripts\3_game\constants.c:423
   class SoundConstants
   {
       const int ITEM_PLACE        = 1;
       const int ITEM_DEPLOY_LOOP  = 2;
       const int ITEM_DEPLOY       = 3;
       const int ITEM_FOLD_LOOP    = 4;
       const int ITEM_FOLD         = 5;
       const int ITEM_ATTACH       = 6;
       const int ITEM_DETACH       = 7;
       // ... more, up to ITEM_SOUNDS_MAX = 63
   }
   ```

   `ITEM_SOUNDS_MAX` is at `P:\scripts\4_world\entities\itembase.c:116`.

2. Link sound sets in `InitItemSounds()` (the base method is at `P:\scripts\4_world\entities\itembase.c:4416`):

   ```
   override void InitItemSounds()
   {
       super.InitItemSounds();
       ItemSoundHandler handler = GetItemSoundHandler();
       handler.AddSound(SoundConstants.ITEM_DEPLOY, "MyMod_Deploy_SoundSet");
       // for a loop:
       SoundParameters params = new SoundParameters();
       params.m_Loop = true;
       handler.AddSound(SoundConstants.ITEM_DEPLOY_LOOP, "MyMod_DeployLoop_SoundSet", params);
   }
   ```

3. Start it from the server, or in single player:

   ```
   StartItemSoundServer(SoundConstants.ITEM_DEPLOY);           // one shot
   StopItemSoundServer(SoundConstants.ITEM_DEPLOY_LOOP);       // stop a loop
   ```

   `StartItemSoundServer(int id)` is at `P:\scripts\4_world\entities\itembase.c:4451` and `StopItemSoundServer(int id)` at `P:\scripts\4_world\entities\itembase.c:4495`.

4. The client plays it without more code. On 1.30 this goes by RPC: the server queues every sound started in a frame and sends them in one `RPC_ITEM_SOUND_PLAY` (`P:\scripts\4_world\entities\itembase.c:4476`), a stop is one `RPC_ITEM_SOUND_STOP` (`P:\scripts\4_world\entities\itembase.c:4502`), and `ItemBase.OnRPC` calls `PlayItemSoundClient` and `StopItemSoundClient` on the client (`P:\scripts\4_world\entities\itembase.c:2796`).

   On 1.29 it went through `OnVariablesSynchronized` (1.29, not yet checked on `P:\`):

   ```
   // 1.29 ItemBase.OnVariablesSynchronized, automatic when the handler is used
   if (m_SoundSyncPlay != 0)
       m_ItemSoundHandler.PlayItemSoundClient(m_SoundSyncPlay, m_SoundSyncSlotID);
   if (m_SoundSyncStop != 0)
       m_ItemSoundHandler.StopItemSoundClient(m_SoundSyncStop);
   ```

   1.30 keeps that path only as `LegacyItemSoundSync()`, for a class that calls it from its own `OnVariablesSynchronized` (`P:\scripts\4_world\entities\itembase.c:3293`).

The network variables of the old path are `m_SoundSyncPlay`, `m_SoundSyncStop` and `m_SoundSyncSlotID`, cleared 100 ms later through `CallLater`. On 1.30 they are marked deprecated (`P:\scripts\4_world\entities\itembase.c:117`) and only `LegacyStopItemSoundServer` still writes one (`P:\scripts\4_world\entities\itembase.c:4483`).

The limit that the handler's comment states, that only one play and one stop can be synced at a time (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:20`), describes the 1.29 path. On 1.30 the comment is unchanged, but the RPC queue sends every sound started in the same frame.

### PlaySoundSet on the client

For an object that is already on the client, for example feedback on a local action:

```
EffectSound m_RollSound;
PlaySoundSet(m_RollSound, "MyMod_Roll_SoundSet", 0, 0.5, true);  // loop, with a 0.5 s fade out
// ...
StopSoundSet(m_RollSound);
```

## Sync patterns in multiplayer

Audio is client only. The server has no `SEffectManager` sound maps and no `Play` call that does anything. The ways to sync:

| Pattern | Mechanism | Typical use |
|---|---|---|
| `StartItemSoundServer` | RPC on 1.30 (a network variable on 1.29) | Items: place, deploy, a deploy loop |
| `PlaySoundSet` in `OnVariablesSynchronized` | A network variable you already have | A sound when an item changes state |
| An animation event bound in config | The engine plays it on each client | Steps, player actions |
| `SEffectManager.PlaySound` called directly | Only behind a client check | Local effects, impacts |

For the rolling stone: the roll sound can start on the client when the client sees the object move faster than a threshold, because the position is already synced. The server is not needed for the audio.

## Player sounds

### PlayerSoundManagerBase

```
// P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:2
const float SOUNDS_HEARING_DISTANCE = 50;

enum eSoundHandlers { STAMINA, HUNGER, INJURY, THIRST, COUNT }

class PlayerSoundManagerBase
{
    ref SoundHandlerBase m_Handlers[MAX_HANDLERS_COUNT];
    void RegisterHandler(SoundHandlerBase handler);
    SoundHandlerBase GetHandler(eSoundHandlers id);
}
```

There is one handler class per state: stamina, hunger, injury and thirst, each with a server and a client form, all extending `SoundHandlerBase` (`P:\scripts\4_world\classes\staminasoundhandler.c:32`). A freezing handler class exists (`P:\scripts\4_world\classes\soundhandlers\freezingsoundhandler.c:2`) but its registration is commented out.

### Steps

`DayZPlayerImplement.OnStepEvent` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3269`):

- reads `GetStepSoundLookupTable()` of the player type, which maps a surface to a sound set (`P:\scripts\4_world\entities\dayzplayerimplement.c:3328`);
- builds a `SoundObjectBuilder` with the environment variables;
- plays through `Play3D` directly (`P:\scripts\4_world\entities\dayzplayerimplement.c:3254`);
- compiles the sound part for clients only, inside `#ifndef SERVER` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3326`).

### Related files

- The sound tables of the player are registered in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgsounds.c`. The source notes could not confirm that this file exists; it does, and since 1.30 its step and attachment sound tables are registered only when `IsHeadlessOrDedicatedServer()` is false (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgsounds.c:335`).
- Voice uses `SetSpeechExVolume` on the sound scene and `WaveKind.WAVESPEECHEX`.

### HEAVY_BREATHING (1.30)

A new `EPlayerSoundEventID.HEAVY_BREATHING` (`P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:38`), registered with `RegisterState(new HeavyBreathEvent1())` (`P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:99`). The class `HeavyBreathEvent1` sets `m_SoundVoiceAnimEventClassID = 907` (`P:\scripts\4_world\classes\soundevents\playersoundevents\events\heavybreathevents.c:21`). Vanilla requests it from silicosis (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\silicosis.c:105`).

## Music: DynamicMusicPlayer

The client side system for ambient and location music:

```
// P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:81
class DynamicMusicPlayer
{
    void SetCategory(DynamicMusicPlayerCategoryPlaybackData playbackData);
    void RegisterDynamicLocation(notnull Entity caller, int locationType, float locationSize);
    void UnregisterDynamicLocation(notnull Entity caller);
}

// P:\scripts\3_game\enums\edynamicmusicplayercategory.c:1
enum EDynamicMusicPlayerCategory
{
    NONE, MENU, CREDITS, TIME,
    LOCATION_STATIC, LOCATION_STATIC_PRIORITY, LOCATION_DYNAMIC
}
```

- Playback: a `SoundObjectBuilder`, then `Play2D` with `WaveKind.WAVEMUSIC` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:520`).
- Fade out: `SetFadeOutFactor` on a 0.2 second tick (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:579`).
- For a mod: register a dynamic location (an event zone, say) with `RegisterDynamicLocation`, and `LOCATION_DYNAMIC` tracks play while the player is inside. A track is an ordinary sound set.
- Since 1.30 each world creates its own registry class, and fixed rectangular zones are registered with `RegisterTrackLocationStaticMultiRectangle`. The details are in `skills/_shared/audio-fx/music-and-radio.md` and the quoted lines in `dayz-1-30-sound.md`.

## NoiseSystem

```
// P:\scripts\3_game\noise.c:1
class NoiseSystem
{
    proto void AddNoise(EntityAI source_entity, NoiseParams noise_params,
        float external_strenght_multiplier = 1.0);
    proto void AddNoisePos(EntityAI source_entity, vector pos, NoiseParams noise_params,
        float external_strenght_multiplier = 1.0);
    proto void AddNoiseTarget(vector pos, float lifetime, NoiseParams noise_params,
        float external_strength_multiplier = 1.0);
    proto native float GetEnvironmentNoiseReduction(vector pos); // since 1.30
}

class NoiseParams
{
    proto native void Load(string noise_name);        // a class of CfgNoises, by name
    proto native void LoadFromPath(string noise_path); // any config path
}
```

Reached with `g_Game.GetNoiseSystem()` (`P:\scripts\3_game\global\game.c:738`).

### How it feeds the AI

```
// P:\scripts\4_world\entities\dayzplayerimplement.c:3258
void AddNoise(NoiseParams noisePar, float noiseMultiplier = 1.0)
{
    if (noisePar != null)
        g_Game.GetNoiseSystem().AddNoise(this, noisePar, noiseMultiplier);
}
```

- Up to 1.29 the multiplier was lowered for rain and wind with `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())` (1.29, not yet checked on `P:\`).
- Since 1.30 that is obsolete. `GetEnvironmentNoiseReduction(pos)` is the single source of truth for the AI, steps pass only `GetNoiseMultiplier(this)`, infected pass no multiplier, and `class AIParams` in config holds the weather multipliers. The lines are in `skills/_shared/audio-fx/noise-for-ai.md`. Do not pass a multiplier that already includes weather; the engine would damp the noise a second time.
- Steps use the noise parameters of the player type, `GetNoiseParamsLandLight()` and `GetNoiseParamsLandHeavy()` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2530`).
- A shot uses `class NoiseShoot { strength = 82; type = "shot"; }` in the weapon config (third-party example from IMPWMODPart2, its MCX Spear rifle).

`AddNoiseTarget` makes a decoy: a noise at a fixed position, with a lifetime and no entity. It suits stun grenades and distraction devices.

For the rolling stone: if infected should react when it rolls, call `g_Game.GetNoiseSystem().AddNoise(this, noiseParams)` from the item script on the server, with a `NoiseParams` loaded from config.

## Environment sound controllers

```
// P:\scripts\3_game\sound.c:38
proto native void SetSoundControllerOverride(string controllerName, float value, SoundControllerAction action);
proto native void MuteAllSoundControllers();
proto native void ResetAllSoundControllers();
```

The controller names, from the comment above the first function: `rain`, `night`, `meadow`, `trees`, `hills`, `houses`, `windy`, `deadBody`, `sea`, `forest`, `altitudeGround`, `altitudeSea`, `altitudeSurface`, `daytime`, `shooting`, `coast`, `waterDepth`, `overcast`, `fog`, `snowfall`, `caveSmall`, `caveBig`.

## Calls that do not exist, and common wrong beliefs

| Wrong belief | What is true |
|---|---|
| `GetGame().CreateSoundOnObject(obj, "MySoundSet", ...)` fits every case | It exists, but returns a `SoundOnVehicle`, not an `EffectSound`. Prefer `SEffectManager.PlaySoundOnObject`. |
| `SEffectManager` plays sound on a server | Its sound maps are created on clients only. A server gets `InitServer()`, which is for particle effecters. |
| Script can set a master volume for one sound | Only `SetVolumeRelative` on the wave. The `volume` of a shader is fixed in config. |
| `ItemBase` has an `OnSoundEvent` callback | No such override. Start item sounds with `StartItemSoundServer` or `PlaySoundSet`. |
| `PlaySoundSet` is heard from a dedicated server | It tests `!g_Game.IsDedicatedServer()` and does nothing there. |
| `DynamicMusicPlayer.PlayTrack(string)` is public | `PlayTrack` is `private`. The public call is `SetCategory`. |
| `StartItemSoundServer` cannot send several sounds at once | True up to 1.29. Since 1.30 every sound started in a frame goes in one `RPC_ITEM_SOUND_PLAY`, and each stop is its own `RPC_ITEM_SOUND_STOP`. The handler comment that states the limit was not updated. |

Since 1.30 the `PlaySoundSet` row is still true for `Object.PlaySoundSet`; the handlers also skip headless clients. Do not write `GetNoiseReductionByWeather()` in new code.

## Recipes

### A. A sound on an item, with no server sync

```cpp
// config.cpp
class CfgSoundShaders
{
    class MyMod_Roll_SoundShader
    {
        samples[] = {{"MyMod\Sounds\roll_loop", 1}};
        volume = 1.0;
        range = 40;
        rangeCurve[] = {{0,1},{20,0.8},{40,0}};
    };
};
class CfgSoundSets
{
    class MyMod_Roll_SoundSet
    {
        soundShaders[] = {"MyMod_Roll_SoundShader"};
    };
};
```

```c
// On the item, client only
EffectSound m_RollSound;

void StartRolling()
{
    if (!g_Game.IsDedicatedServer())
        PlaySoundSet(m_RollSound, "MyMod_Roll_SoundSet", 0.1, 0.5, true);
}

void StopRolling()
{
    if (!g_Game.IsDedicatedServer())
        StopSoundSet(m_RollSound);
}
```

### B. A sound synced from the server with the item sound handler

```c
override void InitItemSounds()
{
    super.InitItemSounds();
    GetItemSoundHandler().AddSound(SoundConstants.ITEM_PLACE, "MyMod_Impact_SoundSet");
}

// On the server, when the impact is detected:
StartItemSoundServer(SoundConstants.ITEM_PLACE);
// Clients play it with no more code.
```

### C. A music zone

```c
// On the client, when the entity is set up:
DynamicMusicPlayer dmp = GetGame().GetMission().GetDynamicMusicPlayer();
dmp.RegisterDynamicLocation(this, DynamicMusicLocationTypes.CONTAMINATED_ZONE, 100.0);
// When it is deleted:
dmp.UnregisterDynamicLocation(this);
```

The source notes marked `GetGame().GetMission().GetDynamicMusicPlayer()` as unverified. It is the vanilla call: the mission declares it (`P:\scripts\3_game\gameplay.c:752`) and the contaminated area uses it exactly this way (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarea.c:21`).

### D. A noise for infected

```c
// On the server, when the stone rolls or hits something:
NoiseParams np = new NoiseParams();
np.Load("ZombieRoarNoise");    // a class of CfgNoises, vanilla or your own
g_Game.GetNoiseSystem().AddNoise(this, np, 2.0);  // twice the config strength
```

The source notes loaded `"Footstep_Heavy"` here. That name is not a class of `CfgNoises` on `P:\`; the vanilla classes are `DeerStepNoise`, `DeerRoarNoise`, `WolfStepNoise`, `WolfRoarNoise`, `ZombieStepNoise` and `ZombieRoarNoise` (`P:\DZ\AI\config.cpp:6903`). Since 1.30, do not multiply the `2.0` by a weather factor worked out in script; the engine damps the noise at that position itself.

## DayZ 1.30: radios, vegetation, destructor

The quoted lines are in `dayz-1-30-sound.md`.

- Radio and bunker: `TransmitterBase.SOUND_BUNKER_STATIC_NOISE`, and `UseBunkerStaticNoise()`, which is `IsTunedToBunkerFrequency() && SOUND_BUNKER_STATIC_NOISE != ""` (`P:\scripts\4_world\entities\itembase\transmitterbase.c:135`). The native method is on `ItemTransmitter`. The personal radio and the base radio set the name to `"bunkerbroadcast_staticnoise_SoundSet"`.
- Static vegetation: `StaticObjectType` reads `CfgNonAIVehicles <Name> VegetationSounds` (`P:\scripts\3_game\entities\staticobjecttype.c:13`). The macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` is at `P:\DZ\data\basicdefines.hpp:310`.
- The event destructor: `~SoundEventBase` runs `if (g_Game) Stop();` (`P:\scripts\4_world\classes\soundevents\soundevents.c:12`). Do not write a 1.29 style destructor in a subclass of `InfectedSoundEventBase`.

## Sources

| File | What it holds |
|---|---|
| `P:\scripts\3_game\sound.c` | `SoundParams`, `SoundObjectBuilder`, `SoundObject`, `AbstractWave`, `AbstractSoundScene`, `WaveKind` |
| `P:\scripts\3_game\effectmanager.c` | `SEffectManager` |
| `P:\scripts\3_game\effects\effectsound.c` | `EffectSound` |
| `P:\scripts\3_game\entities\object.c` | `PlaySoundSet`, `PlaySoundSetAtMemoryPoint` |
| `P:\scripts\3_game\entities\soundonvehicle.c` | `SoundOnVehicle`, `SoundWaveOnVehicle` |
| `P:\scripts\3_game\global\game.c` | `CreateSoundOnObject`, `GetSoundScene`, `GetNoiseSystem` |
| `P:\scripts\3_game\noise.c` | `NoiseSystem`, `NoiseParams` |
| `P:\scripts\3_game\constants.c` | `SoundConstants` |
| `P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c` | `DynamicMusicPlayer` |
| `P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c` | The Nasdara music registry |
| `P:\scripts\4_world\entities\itembase.c` | `InitItemSounds`, `StartItemSoundServer`, `StopItemSoundServer`, the item sound RPCs, `LegacyItemSoundSync` |
| `P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c` | `ItemSoundHandler` |
| `P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c` | `PlayerSoundManagerBase` |
| `P:\scripts\4_world\entities\dayzplayerimplement.c` | `AddNoise`, `OnStepEvent` |
| `P:\scripts\3_game\entities\staticobjecttype.c` | `StaticObjectType` and `VegetationSounds` (1.30) |
| `P:\scripts\4_world\entities\itembase\transmitterbase.c` | `SOUND_BUNKER_STATIC_NOISE` |
| IMPWMODPart2, `Weapons\Automatic\Sounds\config.cpp` | Third-party: shaders with an inline `rangeCurve[]` |
| IMPWMODPart2, `Weapons\Automatic\F2000\Sounds\config.cpp` | Third-party: inheriting the vanilla shot bases |
| IMPWMODPart2, `Weapons\Automatic\MCXSpear\config.cpp` | Third-party: `soundSetShot` in a fire mode, and `NoiseShoot` |
| DoorLockSystem, `ActionUnlockDLSDoor.c` | Third-party: `building.PlaySound` and `building.PlaySoundLoop` |
