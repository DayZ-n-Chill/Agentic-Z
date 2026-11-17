---
name: dayz-sound-system
description: "Reference for DayZ mod audio: CfgSoundShaders and CfgSoundSets, playing sound sets from script (PlaySoundSet, SEffectManager, EffectSound), sounds the server starts (StartItemSoundServer), the NoiseSystem that AI hears, music zones, radio static and the DayZ 1.30 audio changes. Use when a sound does not play, there is no sound on a dedicated server, a sound needs syncing, or its pitch, volume or range must change; also for bunker radio static, HEAVY_BREATHING, GetEnvironmentNoiseReduction, IsHeadlessOrDedicatedServer, sandstorm noise and VegetationSounds. The dayz-audio-fx-specialist agent reads it when it writes or debugs mod audio. Spanish trigger: sonido DayZ. Not particles (dayz-particles) and not UI work."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ sound system

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. The reference files are in `<skill-dir>\references\`, and the shared audio pack is in `skills/_shared/audio-fx/`.

Line numbers are from the 1.30 scripts on `P:\`.

## What to read

| Task | Read |
|---|---|
| Write `CfgSoundShaders` and `CfgSoundSets`, pick curves and 3D processing, inherit a vanilla shot sound | `skills/_shared/audio-fx/sound-config.md` |
| Play, loop, fade, stop and free a sound set from script | `skills/_shared/audio-fx/sound-script.md` |
| Start an item sound on the server and hear it on every client; player sound handlers, step sounds, bush step sounds | `skills/_shared/audio-fx/item-and-player-sounds.md` |
| Build a sound by hand to set its pitch or mixer category; override environment sound controllers | `skills/_shared/audio-fx/sound-engine-api.md` |
| Make infected and animals hear something; the 1.30 weather damping | `skills/_shared/audio-fx/noise-for-ai.md` |
| Add a music zone or the music of a custom world; radio static on the bunker frequency | `skills/_shared/audio-fx/music-and-radio.md` |
| Put a sound and a particle on one device; weapon and item sounds named in config | `skills/_shared/audio-fx/effects-wiring.md` |
| See every signature in one place, the third-party config examples and the full recipes | `references/sound-deep-dive.md` |
| Move a mod to DayZ 1.30: quoted vanilla lines, what breaks, the checklist | `references/dayz-1-30-sound.md` |

## The one rule behind most sound bugs

Audio is client only.

- `SEffectManager` creates its sound maps only when the game is not a dedicated server (`P:\scripts\3_game\global\game.c:58`).
- `PlaySoundSet` on any object does nothing on a dedicated server: it tests `g_Game && !g_Game.IsDedicatedServer()` (`P:\scripts\3_game\entities\object.c:1249`).

A `Play` call on a dedicated server is silent and reports no error. To make a sound happen "from the server", sync a change of state and let each client play it. Vanilla gives you `StartItemSoundServer` for item sounds; for anything else, sync your own variable and play in `OnVariablesSynchronized`.

Since 1.30 the item and player sound handlers test `IsHeadlessOrDedicatedServer()`, so headless clients are skipped too (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:121`). `Object.PlaySoundSet` did not change.

## Which call for which job

| Situation | Use |
|---|---|
| One sound at a world position, from client code | `SEffectManager.PlaySound("Set", pos)` |
| A sound that follows an object, from client code | `obj.PlaySoundSet(sound, "Set", fadeIn, fadeOut, loop)` or `SEffectManager.PlaySoundOnObject("Set", obj)` |
| An item sound the server starts and every client hears | `StartItemSoundServer(id)` and `StopItemSoundServer(id)` |
| A sound at a memory point of the model | `PlaySoundSetAtMemoryPoint(...)`; it has no server test of its own, so guard it |
| Steps, gestures and other animation sounds | Animation events in config; the engine plays them on each client |
| A door or alarm sound on a building, the old way | `PlaySound` and `PlaySoundLoop` on the object, which return a `SoundOnVehicle` (third-party example: DoorLockSystem). Prefer a sound set |
| Something infected and animals should hear | `GetGame().GetNoiseSystem().AddNoise`, `AddNoisePos` or `AddNoiseTarget`, on the server |
| A zone with its own music | `RegisterDynamicLocation` on the dynamic music player |
| Fixed music zones of a custom world (1.30) | A subclass of `DynamicMusicPlayerRegistry` that calls `RegisterTrackLocationStaticMultiRectangle` |
| A radio that plays static on the bunker frequency (1.30) | Set `SOUND_BUNKER_STATIC_NOISE` on the transmitter |
| Step sounds of a custom bush (1.30) | A `VegetationSounds` class on its `CfgNonAIVehicles` class, or the macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` |

Cleanup matters. Every `SEffectManager.Play` call registers the effect and the manager keeps a reference to it (`P:\scripts\3_game\effectmanager.c:3`). Call `SEffectManager.DestroyEffect(effect)` or set autodestroy, or the effect stays in memory.

## Config in one screen

A sample is an `.ogg` file named without its extension, with a path that starts at the mod prefix.

```cpp
class CfgSoundShaders
{
    class MyMod_Roll_SoundShader
    {
        samples[]    = {{"MyMod\Sounds\roll_loop", 1}};   // {path without extension, weight}
        volume       = 1.0;
        range        = 40;                                 // meters
        rangeCurve[] = {{0, 1}, {20, 0.8}, {40, 0}};       // inline fade curve, in meters
        // or: rangeCurve = "closeShotCurve";              // the name of a vanilla CfgSoundCurves class
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

For a variant of a vanilla sound, inherit the vanilla shader or set and change only what differs; `skills/_shared/audio-fx/sound-config.md` shows it for weapon shots, with every sound set key (`spatial`, `volumeCurve`, `sound3DProcessingType`, `loop` and the rest) and its vanilla line.

## Sounds the server starts

1. Link an ID of `SoundConstants` to a sound set in `InitItemSounds()` with `GetItemSoundHandler().AddSound(id, "MyMod_Deploy_SoundSet")`.
2. Call `StartItemSoundServer(id)` on the server; for a loop, stop it with `StopItemSoundServer(id)`.
3. Clients play it with no more code.

IDs go up to `ITEM_SOUNDS_MAX = 63` (`P:\scripts\4_world\entities\itembase.c:116`).

On 1.30 the server sends every sound started in one frame in a single `RPC_ITEM_SOUND_PLAY` (`P:\scripts\4_world\entities\itembase.c:4476`). Up to 1.29 one synced variable carried one play and one stop at a time (1.29, not yet checked on `P:\`). Details: `skills/_shared/audio-fx/item-and-player-sounds.md`.

## What AI hears

A sound set is for players. For AI, add a noise on the server:

```c
GetGame().GetNoiseSystem().AddNoise(entity, noiseParams, multiplier);        // at the entity
GetGame().GetNoiseSystem().AddNoisePos(entity, pos, noiseParams, multiplier); // at a position
GetGame().GetNoiseSystem().AddNoiseTarget(pos, lifetimeSeconds, noiseParams); // a decoy with no entity
```

Since 1.30 the engine damps noise for rain, snow, fog, wind, sea and sandstorm, and `GetEnvironmentNoiseReduction(pos)` reads the result (`P:\scripts\3_game\noise.c:13`). Do not also multiply the strength by a weather factor in script. Details: `skills/_shared/audio-fx/noise-for-ai.md`.

## Calls that do not exist, and common wrong beliefs

| Wrong belief | What is true |
|---|---|
| `SEffectManager` plays sound on a server | Client only. `InitServer()` exists for particle effecters, not for sound (`P:\scripts\3_game\effectmanager.c:517`) |
| `PlaySoundSet` is heard from a dedicated server | It does nothing there. Sync a state instead |
| `GetGame().CreateSoundOnObject(...)` returns an `EffectSound` | It returns a `SoundOnVehicle` entity (`P:\scripts\3_game\global\game.c:692`). Prefer `SEffectManager` |
| `DynamicMusicPlayer.PlayTrack("...")` can be called | `PlayTrack` is `private` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:511`). Use `SetCategory` and `RegisterDynamicLocation` |
| `ItemBase` has an `OnSoundEvent` override | It does not. Use the item sound handler or `PlaySoundSet` |
| `StartItemSoundServer` can sync only one sound at a time | True up to 1.29. On 1.30 sounds started in one frame travel together; the comment in the handler still states the old limit |
| One sound has a master volume call | Only `SetVolumeRelative` on its wave, or `SetSoundVolume` on its `EffectSound`. The shader `volume` is fixed config |
| `samples[]` paths need a file extension | They are written without one |
| `SetFrequency` takes Hz | It takes a pitch factor; 1.0 is the recorded pitch (measured, see `skills/_shared/audio-fx/sound-engine-api.md`) |

## Recipes

A loop tied to movement, on the client only. The position of the object is already synced, so the server has no part in the sound:

```c
protected EffectSound m_RollSound;

void MyMod_UpdateRollAudio()                    // call from a client side update
{
    bool moving = GetVelocity(this).Length() > 0.5;
    if (moving && !m_RollSound)
    {
        PlaySoundSet(m_RollSound, "MyMod_Roll_SoundSet", 0.1, 0.5, true);   // loop
    }
    else if (!moving && m_RollSound)
    {
        StopSoundSet(m_RollSound);              // fades out over 0.5 s
    }
}
```

More:

- The same loop built by hand so its pitch can change, and the position rule that keeps it audible: `skills/_shared/audio-fx/sound-engine-api.md`.
- An impact sound the server triggers: link a set in `InitItemSounds()`, call `StartItemSoundServer(id)` from the server event (for example `EOnContact`).
- A distraction noise for infected: `AddNoiseTarget` with a lifetime, in `skills/_shared/audio-fx/noise-for-ai.md`.
- A music zone: `RegisterDynamicLocation(this, locationType, radius)` when the entity is set up on the client and `UnregisterDynamicLocation(this)` when it is deleted, in `skills/_shared/audio-fx/music-and-radio.md`. On a custom world since 1.30, also give the world its own registry class.

## DayZ 1.30

The quoted vanilla lines, what breaks and the full checklist are in `references/dayz-1-30-sound.md`. In short:

- The engine damps noise for weather; `GetEnvironmentNoiseReduction(pos)` replaces the weather helpers, which are obsolete.
- `IsHeadlessOrDedicatedServer()` guards the item and player sound paths; `Object.PlaySoundSet` still tests `IsDedicatedServer()`.
- An `EffectSound` with a fade in starts at volume zero.
- New player sound event `HEAVY_BREATHING` (animation event 907), requested by silicosis.
- One music registry class per world.
- Transmitters play `SOUND_BUNKER_STATIC_NOISE` while `IsTunedToBunkerFrequency()` is true.
- Static objects can carry `VegetationSounds` for steps.
- The changelog's `SoundHitType` and `GetSoundHitType()` are not in script. Do not call them.

## Related skills

- Particles share `SEffectManager` and its cleanup rules: `/dayz-particles`.
- How infected and animals react to noise: `skills/_shared/ai/perception.md`, and the dayz-ai-patterns skill for Expansion AI.
- Contact events that usually trigger impact sounds: `skills/_shared/physics/contact.md`, and the dayz-physics-engine skill.
- Net sync variables and `OnVariablesSynchronized`: `skills/_shared/enscript/patterns/netsync.md`, and the enforce-script-reference skill.

## On Linux

Everything above is written for Windows and stays valid there. Sound configs, `.ogg` files and scripts are the same on Linux. What changes is packing and the tools around it. The notes below are from the source this skill was built from and are not checked here:

- Pack, sign and binarize with dayzmake 1.0.0 or later, a DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to release `v1.0.0`: either the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from its releases page, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`. The commands are `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where a model needs it.
- Upstream armake2 is not a substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake `v1.0.0` includes them), and it lacks the DayZ only functions dayzmake keeps adding.
- A wrapper script, `dayz-mod-pack.sh`, runs those commands as `init`, `keygen`, `build [--binarize-models]`, `check` and `publish-hint`. It arrives with the Linux notes of the scripting workstream, as does a dayzmake reference in the dayz-pbo-build skill.
- One comparison is on record: on 2026-11-03 a textured cube binarized through dayzmake (fork commit `7dcb3cf`, when the fork was still named armake2; `v1.0.0` contains it) matched Bohemia's binarize from a `P:` root byte for byte. That is a file comparison, not a check of the model in game.
- `P:\` is a plain folder mapped by the Proton setup script (`dayz-proton.sh init <dir>`), so a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView start under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `dayz-proton.sh gui TexView <paa>`. Object Builder opened and showed a model; editing in it was not tried.
- The offline Python tools (`scripts/tools/py3d/`, `scripts/tools/dayz-model-preflight/`, `scripts/tools/dayz-3d-viewer/`) run natively on Linux.
- The Proton setup, the measured tool matrix and the limits are in the Linux notes of the shared pack (`_shared/linux-proton.md`), and the in-game checks on Linux in the dayz-test-ingame skill.

## Building, testing and publishing the mod

This skill ends at the config and the script. To pack the mod and hear the result, use `/dayz-build-pbo` and `/dayz-launch-test`; for the whole loop of a mod (`config.cpp` and `CfgMods`, `requiredAddons`, signing, the Workshop) use the dayz-mod-dev skill. No gate that reads files can hear a sound, so write down what the in-game test should listen for (`skills/_shared/audio-fx/effects-wiring.md`, "Hand to the in-game test").
