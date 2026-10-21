# Audio and effects pack

Reference for sound configs, the script that plays sounds, and how sound and particle effects are wired into a mod. Used by `dayz-audio-fx-specialist` and by any lead that needs a sound or an effect. Particle files themselves (`.ptc`, `.emat`, registering and playing particles) are in the `/dayz-particles` pack at `dayz-particles/SKILL.md`; this pack points there instead of repeating it.

Every fact here was checked in the vanilla files on `P:\`. Each file cites the path and line. Line numbers are from the game version on `P:\` when the pack was written; if a line has moved, search for the class name.

## Which file to open

| Question | File |
|---|---|
| Write a `CfgSoundShaders` or `CfgSoundSets` entry: samples, volume, range, curves, looping, the `CfgPatches` it needs | `sound-config.md` |
| Play, loop, stop or fade a sound set from script, and clean it up | `sound-script.md` |
| Put a sound and a particle on one device, start them from the server, or hook sounds and particles through config (weapons, item events) | `effects-wiring.md` |
| Write a `.ptc` or `.emat`, register a particle, pick a vanilla particle | `/dayz-particles` (`dayz-particles/SKILL.md`) |

## The three layers in one line each

- A sound shader (`CfgSoundShaders`) names the `.ogg` samples and sets their volume and how far they carry.
- A sound set (`CfgSoundSets`) groups shaders and sets how they play: 3D or not, volume curve over distance, looping, delay.
- Script plays a sound set by name. Config also names sound sets directly for weapons and animation events.

Main vanilla sources: `P:\DZ\sounds\hpp\config.cpp` (every vanilla shader, set, curve, filter and 3D processor), `P:\DZ\sounds_bliss\config.cpp` (a second addon that adds its own shaders and sets, the shape a mod follows), `P:\scripts\3_game\entities\object.c`, `P:\scripts\3_game\effectmanager.c`, `P:\scripts\3_game\effects\effectsound.c`, and the vanilla generator in `P:\scripts\4_world\entities\itembase\powergenerator.c`.
