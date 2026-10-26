# Effects wiring: sound plus particles

How a sound and a particle are put on one device, and how config hooks sounds and particles to weapons and item events. The particle file and its registration are covered by `/dayz-particles`; open `dayz-particles/SKILL.md` and its `references/` files for `.ptc`, `.emat` and the particle API.

## The vanilla generator: sound and smoke together

`P:\scripts\4_world\entities\itembase\powergenerator.c` is the closest vanilla match for "a running sound and exhaust smoke":

| Line | What it does |
|---|---|
| 9 to 12 | Sound set names as constants. |
| 15 to 19 | One `EffectSound` field per sound, and `ref protected Effect m_Smoke` for the smoke. |
| 75 to 83 | `GetSmokeParticlePosition()` returns `"0.3 0.21 0.4"` and `GetSmokeParticleOrientation()` returns `"270 0 0"`, the local offset and rotation of the exhaust. |
| 93 to 99 | Starts the loop sound, then `m_Smoke = new EffGeneratorSmoke();` and `SEffectManager.PlayOnObject(m_Smoke, this, GetSmokeParticlePosition(), GetSmokeParticleOrientation());`. |
| 199 to 203 | On stop: plays the stop sound, stops the loop, `SEffectManager.DestroyEffect(m_Smoke);`. |
| 36 to 39 | The destructor destroys the smoke effect as well. |

The smoke effect is a three line class, `P:\scripts\3_game\effects\effectparticle\generatorsmoke.c:1` to `7`:

```c
class EffGeneratorSmoke : EffectParticle
{
    void EffGeneratorSmoke()
    {
        SetParticleID(ParticleList.POWER_GENERATOR_SMOKE);
    }
}
```

`POWER_GENERATOR_SMOKE` is registered as `"smoke_small_generator_01"` (`P:\scripts\3_game\particles\particlelist.c:149`), the file `P:\graphics\particles\smoke_small_generator_01.ptc`. `SetParticleID` is at `P:\scripts\3_game\effects\effectparticle.c:327`, and `SEffectManager.PlayOnObject(notnull Effect eff, Object obj, vector local_pos = "0 0 0", vector local_ori = "0 0 0", bool force_rotation_relative_to_world = false)` at `P:\scripts\3_game\effectmanager.c:70`.

## Doing the same in a mod

1. Reuse a vanilla particle when one fits; the `/dayz-particles` catalog (`dayz-particles/references/vanilla-particle-catalog.md`) lists them. For a new look, write the `.ptc` with `/dayz-particles` (`dayz-particles/references/ptc-format-reference.md`).
2. Register a new particle in `3_Game` with a modded `ParticleList`, as the vanilla comment at `particlelist.c:3` to `9` shows: `static const int MYMOD_EXHAUST = RegisterParticle("MyMod/data/particles/", "mymod_exhaust");`. `RegisterParticle(string root_path, string file_name)` (line 452) lowercases both parts and takes the name without `.ptc`.
3. Write a small `EffectParticle` subclass that calls `SetParticleID` with your ID, like `EffGeneratorSmoke`. Put it in `3_Game` or `4_World`.
4. In the device, keep `ref Effect m_Smoke;`, start it with `SEffectManager.PlayOnObject` next to the loop sound, and free it with `SEffectManager.DestroyEffect` where the loop sound stops, and in the destructor or `EEDelete`.
5. Wrap all of it in the client check (`!GetGame().IsDedicatedServer()`). Particles are client only like sounds (Tier 2, `conventions/scripts.md`).

The full device pattern for particles, with toggles and cleanup, is Pattern D in `dayz-particles/references/integration-patterns.md`. The sound side is in `sound-script.md`.

## Config hooks: sounds and particles without script

### Weapon shots

`P:\DZ\weapons\firearms\akm\config.cpp`:

- Each fire mode lists the sound sets of one shot in `soundSetShot[]` (line 89, inside `class SemiAuto: Mode_SemiAuto` at line 87): the first person shot, an interior version, tails and a slapback.
- `class Particles` (line 218) holds `class OnFire` (line 220) and `class OnOverheating` (line 240). Each entry under them names a particle with `overrideParticle`, such as `class MuzzleFlash` with `overrideParticle="weapon_shot_akm_01"` (lines 226 to 228), plus options `ignoreIfSuppressed`, `illuminateWorld`, `positionOffset[]`, `overridePoint` and `overrideDirectionPoint`.

`P:\scripts\4_world\entities\weaponparticles.c` reads those keys. Two facts from it matter for a mod:

- `overrideParticle` is looked up with `ParticleList.GetParticleIDByName` (line 121), so a mod particle used here must be registered in a modded `ParticleList` first.
- With no `overridePoint`, the effect plays at the memory point `"Usti hlavne"` (lines 112 and 113), the muzzle point of vanilla weapon models.

### Item animation events

Items name sound sets for animation events under `class AnimEvents` and `class SoundWeapon`. `TShirt_ColorBase` (`P:\DZ\characters\tops\config.cpp:2244`) has `class AnimEvents` at line 2339 with `class pickUpItem { soundSet="Shirt_pickup_SoundSet"; id=797; };` (line 2345). The set is a normal sound set, `Shirt_pickup_SoundSet: baseCharacter_SoundSet` (`P:\DZ\sounds\hpp\config.cpp:321595`). To give a mod item its own pickup or drop sound, redeclare this block in its `CfgVehicles` class with the mod's own sound set, and keep the event class name and `id` as vanilla has them.

## Hand to the in-game test

The gates that read files cannot hear or see an effect. When handing back, write what the in-game test should check, for example: "Start MyMod_Generator. The start sound plays, then a loop that is clear at 10 m and gone by 60 m. Grey smoke rises from the exhaust while it runs and stops when it is switched off." Also ask it to look in the logs for errors such as `Invalid sound set.` (`P:\scripts\3_game\effects\effectsound.c:313`) and the missing memory point error from `PlaySoundSetAtMemoryPoint` (`P:\scripts\3_game\entities\object.c:1305`).
