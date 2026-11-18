# Audio and effects pack

Reference for sound configs, the script that plays sounds, and how sound and particle effects are wired into a mod. Used by `dayz-audio-fx-specialist` and by any lead that needs a sound or an effect. Particle files themselves (`.ptc`, `.emat`, registering and playing particles) are in the `/dayz-particles` pack at `dayz-particles/SKILL.md`; this pack points there instead of repeating it.

Facts here were checked in the vanilla files on `P:\`, except where a line says it is not checked on `P:\` (statements about 1.29, third-party mod behaviour and results measured in game). Each file cites the path and line. Line numbers are from the game version on `P:\` when the pack was written; if a line has moved, search for the class name.

## Which file to open

| Question | File |
|---|---|
| Write a `CfgSoundShaders` or `CfgSoundSets` entry: samples, volume, range, curves, looping, the `CfgPatches` it needs | `sound-config.md` |
| Play, loop, stop or fade a sound set from script, and clean it up | `sound-script.md` |
| Put a sound and a particle on one device, start them from the server, or hook sounds and particles through config (weapons, item events) | `effects-wiring.md` |
| Use the handlers vanilla already runs: item sounds the server starts on every client, attach, detach and impact sounds set in config, player sound handlers, step sounds, player sound events | `item-and-player-sounds.md` |
| Build or tune a sound by hand: `SoundParams`, `SoundObjectBuilder`, `AbstractWave`, pitch of a playing sound, mixer category (`WaveKind`), environment sound controllers, legacy calls | `sound-engine-api.md` |
| Make a noise that infected and animals hear to go with a sound, and the 1.30 weather damping | `noise-for-ai.md` |
| Add a music zone or the music of a custom world, and the 1.30 radio static on the bunker frequency | `music-and-radio.md` |
| Weather sounds (the sandstorm sound sets), and the sound set getters of `SurfaceInfo` | `effects-wiring.md` |
| Move a mod's audio to DayZ 1.30 | "DayZ 1.30 checklist" below |
| Write a `.ptc` or `.emat`, register a particle, pick a vanilla particle | `/dayz-particles` (`dayz-particles/SKILL.md`) |

## Which call for which job

| Situation | Call | File |
|---|---|---|
| One sound at a world position, from client code | `SEffectManager.PlaySound` | `sound-script.md` |
| A sound that follows an object, from client code | `PlaySoundSet`, `PlaySoundSetLoop`, `StopSoundSet` on the object, or `SEffectManager.PlaySoundOnObject` | `sound-script.md` |
| A sound at a memory point of the model | `PlaySoundSetAtMemoryPoint`, behind your own client check | `sound-script.md` |
| A sound the server decides on, for a state that lasts | A synced variable, played in `OnVariablesSynchronized` | `sound-script.md` |
| An item sound the server starts and every client hears | `StartItemSoundServer` and `StopItemSoundServer` | `item-and-player-sounds.md` |
| Steps, gestures, item pickup and drop sounds | Animation events in config | `effects-wiring.md`, `item-and-player-sounds.md` |
| A weapon shot sound or muzzle particle | `soundSetShot[]` and `class Particles` in the weapon config | `effects-wiring.md` |
| The pitch of a playing sound, or its mixer category | A sound built by hand with `SoundObjectBuilder` and `Play3D` | `sound-engine-api.md` |
| Something infected and animals should hear | `AddNoise`, `AddNoisePos` or `AddNoiseTarget`, on the server | `noise-for-ai.md` |
| A zone with its own music, or the music of a custom world | `RegisterDynamicLocation`, or a `DynamicMusicPlayerRegistry` subclass | `music-and-radio.md` |
| A radio that plays static on the bunker frequency | `SOUND_BUNKER_STATIC_NOISE` on the transmitter | `music-and-radio.md` |
| Step sounds of a custom bush | `VegetationSounds` on its `CfgNonAIVehicles` class | `item-and-player-sounds.md` |
| A sound and a particle on one device | `PlaySoundSetLoop` plus `SEffectManager.PlayOnObject` | `effects-wiring.md` |

## Common traps

| Trap | File |
|---|---|
| Any play call on a dedicated server is silent and logs no error | `sound-script.md` |
| A sound played through `SEffectManager` and never destroyed stays in memory | `sound-script.md` |
| `CreateSoundOnObject` returns a `SoundOnVehicle`, not an `EffectSound` | `sound-engine-api.md` |
| `SetFrequency` takes a pitch factor, not Hz | `sound-engine-api.md` |
| There is no volume call for one sound beyond the wave and the `EffectSound` | `sound-engine-api.md` |
| `DynamicMusicPlayer.PlayTrack` is private | `music-and-radio.md` |
| `ItemBase` has no `OnSoundEvent` | `item-and-player-sounds.md` |
| The item sound handler's comment about one sound at a time describes the pre-1.30 path | `item-and-player-sounds.md` |
| `samples[]` paths are written without a file extension | `sound-config.md` |
| A curve, filter or 3D processor name that does not exist | `sound-config.md` |
| A name passed to `NoiseParams.Load` that is not a class of `CfgNoises` | `noise-for-ai.md` |

## DayZ 1.30 checklist

Each line names the file that holds the vanilla lines and the details.

- [ ] Noise for AI: do not multiply `AddNoise` by a weather factor; read `GetEnvironmentNoiseReduction(pos)` and tune `AIParams` in config. The old weather helpers are obsolete (`noise-for-ai.md`).
- [ ] New client play and stop code: test `IsHeadlessOrDedicatedServer()`. `Object.PlaySoundSet` still tests only `IsDedicatedServer()` (`item-and-player-sounds.md`, `sound-script.md`).
- [ ] Item sounds started with `StartItemSoundServer` now travel by RPC, several in one frame, with no change to mod code. The old synced variables play only in a class that calls `LegacyItemSoundSync()` (`item-and-player-sounds.md`).
- [ ] A sound with a fade in now starts at volume zero; listen to tuned loops again (`sound-script.md`).
- [ ] The player sound event `HEAVY_BREATHING` (animation event 907) is new (`item-and-player-sounds.md`).
- [ ] A sound event destructor must test `if (g_Game)` before it stops its sound (`item-and-player-sounds.md`).
- [ ] Custom world music: one `DynamicMusicPlayerRegistry` subclass per world (`music-and-radio.md`).
- [ ] Custom transmitter: set `SOUND_BUNKER_STATIC_NOISE`, and call `SetSynchDirty()` after a frequency change made by your own code (`music-and-radio.md`).
- [ ] Custom bushes: `VegetationSounds`, or the macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` (`item-and-player-sounds.md`).
- [ ] Do not call `SoundHitType` or `GetSoundHitType()`; the changelog names them but script does not have them (`item-and-player-sounds.md`).

## The three layers in one line each

- A sound shader (`CfgSoundShaders`) names the `.ogg` samples and sets their volume and how far they carry.
- A sound set (`CfgSoundSets`) groups shaders and sets how they play: 3D or not, volume curve over distance, looping, delay.
- Script plays a sound set by name. Config also names sound sets directly for weapons and animation events.

Main vanilla sources: `P:\DZ\sounds\hpp\config.cpp` (most vanilla shaders, sets and curves, and every filter and 3D processor), `P:\DZ\sounds_bliss\config.cpp` (a second addon that adds its own shaders, sets and curves, the shape a mod follows; search both files), `P:\scripts\3_game\entities\object.c`, `P:\scripts\3_game\effectmanager.c`, `P:\scripts\3_game\effects\effectsound.c`, and the vanilla generator in `P:\scripts\4_world\entities\itembase\powergenerator.c`.
