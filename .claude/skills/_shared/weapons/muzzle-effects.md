# Muzzle effects and shot sounds

Muzzle flash, smoke and overheating are config entries under `class Particles` on the weapon (and on a suppressor). Shot sounds are sound set names on each fire mode. New particle or sound files belong to the audio and FX specialist and the `/dayz-particles` skill; this file covers wiring vanilla ones into a weapon.

## How the effects are played

- `ItemBase.LoadParticleConfigOnFire` reads every child class of `Particles OnFire` and `Particles OnBulletCasingEject` (`P:\scripts\4_world\entities\itembase.c:313` to `:349`). Overheating settings are read at `itembase.c:400` to `:411`.
- On each shot `Weapon_Base.EEFired` plays the weapon's fire particles, then a fitted suppressor's own (`P:\scripts\4_world\entities\firearms\weapon_base.c:341` to `:356`). It plays no effects on a dedicated server (`weapon_base.c:345`).
- Each entry becomes a `WeaponParticlesBase` (`P:\scripts\4_world\entities\weaponparticles.c:7`).

## The three event classes

From the CZ527 (`P:\DZ\weapons\firearms\cz527\config.cpp:132` to `:177`):

- `class OnFire`: plays on every shot. The CZ527 has `MuzzleFlash` and `ChamberSmoke`; the AKM adds `SmokeCloud` (`P:\DZ\weapons\firearms\akm\config.cpp:222`).
- `class OnOverheating`: smoke that builds up with sustained fire. It needs `maxOverheatingValue`, `shotsToStartOverheating` (1 or more, or script logs an error, `itembase.c:400` to `:405`) and `overheatingDecayInterval` (`cz527\config.cpp:152` to `:154`; the AKM uses 12, 4 and 0.7 at `akm\config.cpp:242` to `:244`).
- `class OnBulletCasingEject`: plays when a case is ejected (`cz527\config.cpp:169`).

## Keys on each effect entry

All read in `weaponparticles.c`:

| Key | Meaning | Line |
|---|---|---|
| `overrideParticle` | Particle name as registered in `ParticleList`, such as `weapon_shot_cz527_01` (`P:\scripts\3_game\particles\particlelist.c:188`). Looked up with `ParticleList.GetParticleIDByName`. Required; a missing value logs an error. | `:116` to `:127` |
| `overridePoint` | Memory point to spawn at. Defaults to `Usti hlavne`, the muzzle. | `:109` to `:113` |
| `overrideDirectionPoint` | Memory point the effect points toward. | `:132` |
| `positionOffset[]` | Offset from the point. | `:147` |
| `ignoreIfSuppressed` | Skip when a suppressor is fitted. | `:38` |
| `illuminateWorld` | The flash lights the surroundings. | `:44` |
| `onlyIfBoltIsOpen` | Only when the bolt is open. | `:41` |
| `onlyWithinOverheatLimits[]`, `onlyWithinRainLimits[]`, `onlyWithinHealthLabel[]` | Two value ranges that gate the effect. | `:78`, `:94`, `:62` |
| `onlyIfWeaponIs`, `onlyIfBulletIs` | Gate the effect by weapon or bullet type. | `:54`, `:58` |
| `muzzleIndex` | For guns with more than one muzzle. | `:47` |

A new particle name must be registered in `ParticleList` before `overrideParticle` can use it (`RegisterParticle` at `particlelist.c:414`). That is `/dayz-particles` work.

## Shot sounds

- Each fire mode lists `soundSetShot[]` for a plain shot (`cz527\config.cpp:87` to `:94`) and `soundSetShotExt[]` for suppressed shots, one inner array per suppressor kind (`:95` to `:103`).
- The AKM gives two inner arrays, a factory suppressor set and a homemade set (`akm\config.cpp:98` to `:112`). The CZ527 gives only the homemade set, since its only muzzle slot is `suppressorImpro` (`cz527\config.cpp:190`).
- Automatic modes add `soundSetShot1st[]` and `soundSetShotExt1st[]` for the first round (`akm\config.cpp:121`, `:135`).
- Reusing a vanilla gun's sound set names is fine. New sound sets are `CfgSoundSets` and `CfgSoundShaders` work for the audio and FX specialist.

## AI hearing

`class NoiseShoot` on the weapon sets how loud the shot is to AI (`cz527\config.cpp:76` to `:80`, `strength=100`; AKM `strength=80` at `akm\config.cpp:82`). Suppressors lower it with `noiseShootModifier` (`P:\DZ\weapons\attachments\muzzle\config.cpp:1083`).
