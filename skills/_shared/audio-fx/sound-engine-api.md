# Sound engine API: building and tuning a sound by hand

The classes under `EffectSound`: `SoundParams`, `SoundObjectBuilder`, `SoundObject`, `AbstractWave` and the sound scene. Use them when the sound set helpers in `sound-script.md` are not enough: to change the pitch of a playing sound, to pick its mixer category, to override the environment sound controllers, or to read what a legacy call returns.

All line numbers below are in `P:\scripts\3_game\sound.c` unless another file is named. They are from the 1.30 scripts on `P:\`.

## Contents

- [The classes](#the-classes)
- [Building and playing by hand](#building-and-playing-by-hand)
- [The wave handle](#the-wave-handle)
- [Mixer categories: WaveKind](#mixer-categories-wavekind)
- [Volume: per category, not per sound](#volume-per-category-not-per-sound)
- [Environment sound controllers](#environment-sound-controllers)
- [Legacy: CreateSoundOnObject and SoundOnVehicle](#legacy-createsoundonobject-and-soundonvehicle)

## The classes

| Class | Line | What it is |
|---|---|---|
| `SoundParams` | 137 | Loads one sound set by name. `IsValid()` (line 142) says whether the name exists. |
| `SoundObjectBuilder` | 82 | Takes the `SoundParams`, receives sound variables, and builds the `SoundObject`. |
| `SoundObject` | 111 | The source in the world: its parent, position and mixer category. |
| `AbstractSoundScene` | 53 | The engine's sound scene. `Play2D` (line 58) and `Play3D` (line 59) start a `SoundObject` and return the wave. Reached with `GetGame().GetSoundScene()` (`P:\scripts\3_game\global\game.c:735`). |
| `AbstractWave` | 155 | The handle of a playing sound: play, stop, loop, volume, pitch, fades. |
| `AbstractWaveEvents` | 146 | Five `ScriptInvoker` events of a wave. |

`EffectSound` wraps all of them. It keeps its wave in the protected member `m_SoundWaveObject` (`P:\scripts\3_game\effects\effectsound.c:23`), so script outside the class cannot reach the wave of a sound started with `PlaySoundSet`. That is the usual reason to build a sound by hand.

## Building and playing by hand

Vanilla does this in three places, each a good model:

- The music player builds a `SoundObject`, sets `WaveKind.WAVEMUSIC` and calls `Play2D` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:520`).
- `EffectSound` adds the environment variables, builds the object, sets its kind and parent, sets its position and calls `Play3D` (`P:\scripts\3_game\effects\effectsound.c:173`).
- The player's step sounds set the position and call `Play3D` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3254`).

The same steps for a looping sound that follows an object, kept as a wave so its pitch can be changed. Client only:

```c
protected AbstractWave m_RollWave;

void MyMod_StartRollLoop(Object parent)
{
    if (GetGame().IsDedicatedServer())
        return;

    SoundParams params = new SoundParams("MyMod_Roll_SoundSet");
    if (!params.IsValid())
        return;

    SoundObjectBuilder builder = new SoundObjectBuilder(params);
    builder.AddEnvSoundVariables(parent.GetPosition());

    SoundObject soundObject = builder.BuildSoundObject();
    soundObject.SetKind(WaveKind.WAVEEFFECTEX);
    soundObject.SetParent(parent);

    // With a parent, the position is in the parent's model space. Set it before Play3D.
    vector localPos = "0 0.1 0";
    soundObject.SetPosition(localPos);

    m_RollWave = GetGame().GetSoundScene().Play3D(soundObject, builder);
    if (m_RollWave)
        m_RollWave.Loop(true);
}

void MyMod_StopRollLoop()
{
    if (m_RollWave)
    {
        m_RollWave.Stop();
        m_RollWave = null;
    }
}
```

The calls, with their lines:

- `SoundObjectBuilder.AddEnvSoundVariables(vector position)` (line 93) and `AddVariable(string name, float value)` (line 94) feed variables to the sound set. `BuildSoundObject()` (line 86) asks the sound scene for the object.
- `SoundObject.SetParent(IEntity parent, int pivot = -1)` (line 119), `SetPosition(vector position)` (line 124), `SetKind(WaveKind kind)` (line 132) and `SetOcclusionObstruction(float occlusion, float obstruction)` (line 131).

### The position rule that makes a hand-built loop audible

The comment on `SetPosition` says it "Sets the position locally if parented" (line 123). `EffectSound` always sets the position right before it plays: it calls `SetCurrentLocalPosition` (`P:\scripts\3_game\effects\effectsound.c:172`) one line before `Play3D`, and its override passes the position on to `m_SoundObject.SetPosition` (`P:\scripts\3_game\effects\effectsound.c:746`).

A case measured in game on DayZ 1.30 experimental (not checked on `P:\`) shows what happens when a hand-built sound skips that step: a roll loop built with `SoundParams`, `SoundObjectBuilder`, `SetKind(WaveKind.WAVEEFFECTEX)`, `SetParent` on the player and `Play3D` did play (its header loaded and the script logged it) but was barely audible, while one-shots of the same sound bases played through `PlaySoundSet` were loud. The loop had set no position and sat far from the rider. Calling `SetPosition` after `SetParent` and before `Play3D`, with a small offset in the parent's model space (0.1 m up), fixed it.

## The wave handle

`AbstractWave` methods (all `proto` except `GetEvents()`, which is a script method):

| Line | Method | Note |
|---|---|---|
| 173 | `Play()` | Starts the wave. |
| 181 | `Stop()` | Stops it. |
| 182 | `Restart()` | Starts again from the beginning. |
| 185 | `GetLength()` | Length of the sound. The vanilla comment warns that it blocks until the header has loaded. |
| 187 | `GetCurrPosition()` | Current position as a fraction of the length. |
| 188 | `Loop(bool setLoop)` | Turns looping on or off. |
| 190 | `SetVolume(float value)` | Absolute volume. |
| 191 | `SetVolumeRelative(float value)` | Volume relative to the config volume. |
| 192 | `SetFrequency(float value)` | Pitch. See the note below. |
| 193 | `GetFrequency()` | Current pitch value. |
| 195 | `SetFadeInFactor(float volume)` | Fade in factor. |
| 196 | `SetFadeOutFactor(float volume)` | Fade out factor. The music player calls it on a 0.2 second tick to fade a track (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:579`). |
| 197 | `SetDoppler(bool setDoppler)` | Doppler shift on or off. |
| 199 | `IsHeaderLoaded()` | True once the header is in. Ask before `GetLength()`. |
| 201 | `GetEvents()` | The wave's `AbstractWaveEvents`. |

`SetFrequency` takes a factor, not a frequency in Hz. In the measured case above, `GetFrequency()` on a playing `.ogg` loop returned 1.0, so the value is a pitch multiplier. Set it relative to `GetFrequency()`, and only once `IsHeaderLoaded()` is true. This was measured in game on 1.30 experimental and is not checked on `P:\`.

The events of a wave are five `ScriptInvoker` members of `AbstractWaveEvents`: `Event_OnSoundWaveStarted` (line 148), `Event_OnSoundWaveStopped` (line 149), `Event_OnSoundWaveLoaded` (line 150), `Event_OnSoundWaveHeaderLoaded` (line 151) and `Event_OnSoundWaveEnded` (line 152). `EffectSound` uses the header event to wait before it asks for the length (`P:\scripts\3_game\effects\effectsound.c:181`).

## Mixer categories: WaveKind

`SetKind` puts a sound in one mixer category, which decides which volume slider of the player controls it. The `WaveKind` enum (lines 1 to 14): `WAVEEFFECT`, `WAVEEFFECTEX`, `WAVESPEECH`, `WAVEMUSIC`, `WAVESPEECHEX`, `WAVEENVIRONMENT`, `WAVEENVIRONMENTEX`, `WAVEWEAPONS`, `WAVEWEAPONSEX`, `WAVEATTALWAYS`, `WAVEUI`.

On an `EffectSound`, set it with `SetSoundWaveKind(WaveKind wave_kind)` (`P:\scripts\3_game\effects\effectsound.c:788`) before the sound plays.

## Volume: per category, not per sound

`AbstractSoundScene` has a getter and a setter for each category volume: `SetRadioVolume` (line 63), `SetSpeechExVolume` (line 66), `SetMusicVolume` (line 69), `SetSoundVolume` (line 72) and `SetVOIPVolume` (line 75). Each setter takes the volume and a time.

There is no master volume for one sound beyond `SetVolumeRelative` on its wave, or `SetSoundVolume` on its `EffectSound` (`P:\scripts\3_game\effects\effectsound.c:856`). The `volume` of a shader is fixed in config.

## Environment sound controllers

The engine drives ambient sound from named controllers (how much rain, forest, sea and so on is around the listener). Three global functions override them:

- `SetSoundControllerOverride(string controllerName, float value, SoundControllerAction action)` (line 38). `SoundControllerAction` is `None`, `Limit` or `Overwrite` (line 25).
- `MuteAllSoundControllers()` (line 43) mutes every environment controller.
- `ResetAllSoundControllers()` (line 48) removes all overrides.

The controller names, from the vanilla comment at line 34: `rain`, `night`, `meadow`, `trees`, `hills`, `houses`, `windy`, `deadBody`, `sea`, `forest`, `altitudeGround`, `altitudeSea`, `altitudeSurface`, `daytime`, `shooting`, `coast`, `waterDepth`, `overcast`, `fog`, `snowfall`, `caveSmall`, `caveBig`.

## Legacy: CreateSoundOnObject and SoundOnVehicle

`CreateSoundOnObject(Object source, string sound_name, float distance, bool looped, bool create_local = false)` on the game returns a `SoundOnVehicle` (`P:\scripts\3_game\global\game.c:692`). That is an entity class with one method, `GetSoundLength()` (`P:\scripts\3_game\entities\soundonvehicle.c:1`), not an `EffectSound`. `Object.PlaySound` and `Object.PlaySoundLoop` are thin wrappers around it (`P:\scripts\3_game\entities\object.c:1235`).

It is still in the API, and some third-party mods use it for building sounds (for example `building.PlaySound` and `building.PlaySoundLoop` in a door unlock action; those are the `Object` methods above, not methods of the building class). For new work prefer the sound set helpers in `sound-script.md`, which return an `EffectSound` you can stop, fade and free.
