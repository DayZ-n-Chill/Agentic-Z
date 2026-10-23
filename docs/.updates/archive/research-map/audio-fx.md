# Research map: audio and effects specialist

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Sound config layers | `CfgSoundShaders` (samples, volume, range) feed `CfgSoundSets` (spatial, curves, filters). | `P:\DZ\sounds\hpp\config.cpp:3072` (`CfgSoundShaders`), `:318379` (`CfgSoundSets`) |
| 2 | Curves, effects, filters, 3D processors | `CfgSoundCurves`, `CfgSoundEffects`, `CfgDistanceFilters`, `CfgSound3DProcessors`. | `P:\DZ\sounds\hpp\config.cpp:59`, `:2161`, `:2422`, `:2587` |
| 3 | Sound tables | `CfgSoundTables` map surfaces/events to sounds (steps, impacts). | `P:\DZ\sounds\hpp\config.cpp:385078` |
| 4 | Environment sounds | `CfgEnvSounds`. | `P:\DZ\sounds\hpp\config.cpp:507137` |
| 5 | Weapon shot sound sets | `AKM_Shot_SoundSet` inherits a base; weapon config references it through `soundSetShot[]`. | `P:\DZ\sounds\hpp\config.cpp:330959`, `:331082`; `P:\DZ\weapons\firearms\akm\config.cpp:89` |
| 6 | Playing sounds from script | `SEffectManager.PlaySound`, `EffectSound`, `PlaySoundSet`, `PlaySoundSetLoop`. | `P:\scripts\3_game\effectmanager.c:5`; `P:\scripts\3_game\effects\effectsound.c:4`; `P:\scripts\3_game\dayzgame.c:3226`; `P:\scripts\3_game\effects\destructioneffects\destructioneffectbase.c:94`, `:95` |
| 7 | Low-level sound API | `SoundObjectBuilder`, `SoundObject`, `SoundParams`, `AbstractWave`, `AbstractSoundScene`. | `P:\scripts\3_game\sound.c:53`, `:82`, `:111`, `:137`, `:155` |
| 8 | Animation-driven sounds | Lookup tables for steps, attachments, impacts. | `P:\scripts\3_game\dayzanimeventmaps.c:2`, `:79`, `:87`, `:116` |
| 9 | Player sound events | Event handler and base for breathing, pain, stamina sounds. | `P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:45`; `...\playersoundeventbase.c:31`; `...\events\staminaevents.c:24` |
| 10 | Infected and replaced sounds | Infected sound handler; replace sound handler. | `P:\scripts\4_world\classes\soundevents\infectedsoundevents\infectedsoundeventhandler.c:14`; `P:\scripts\4_world\classes\soundevents\replacesoundevents\replacesoundeventhandler.c:20` |
| 11 | Zombie behaviour sounds in AI config | `SoundsDuring`/`SoundsEntering` per mind state. | `P:\DZ\AI\config.cpp:6272`, `:6308` |
| 12 | Player sound manager | Server-side voice and sound type handling. | `P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:57` |
| 13 | Vehicle sounds | `OnSound` controllers and engine states. See vehicles map. | `P:\scripts\4_world\entities\vehicles\carscript.c:1433`, `:1560` |
| 14 | Clothing and item handling sounds | `soundAttType`, `AnimEvents`/`SoundWeapon`. | `P:\DZ\characters\tops\config.cpp:2268`, `:2341` |
| 15 | Particle files | `.ptc` files (367 in vanilla) edited in Workbench Particle Editor. | `P:\graphics\particles` |
| 16 | Registering particles | `ParticleList.RegisterParticle`, modded `ParticleList` example in vanilla comments. | `P:\scripts\3_game\particles\particlelist.c:5`, `:7`, `:11`, `:22` |
| 17 | Playing particles | `ParticleManager.GetInstance().PlayInWorld/PlayOnObject`; `Particle` class. | `P:\scripts\3_game\particles\particlemanager\particlemanager.c:16`-`50`; `P:\scripts\3_game\particles\particle.c:6`; `P:\scripts\3_game\ammoeffects.c:56` |
| 18 | Effect wrappers | `EffectParticle`, `EffectParticleGeneral`. | `P:\scripts\3_game\effects\effectparticle.c:4`; `P:\scripts\3_game\effectmanager.c:868` |
| 19 | Bullet impact effects | `EffBulletImpactBase` per surface; `ImpactMaterials`. | `P:\scripts\3_game\effects\effectparticle\bulletimpactbase.c:1`; `...\bulletimpactbase\hit_concrete.c:1`; `P:\scripts\3_game\impacteffects.c:28` |
| 20 | Weapon muzzle effects | `Particles`/`OnFire`/`OnOverheating` in weapon config. | `P:\DZ\weapons\firearms\akm\config.cpp:218`-`240`; `P:\scripts\4_world\entities\weaponparticles.c:7` |
| 21 | Fire effects | Fireplace particle constants. | `P:\scripts\4_world\entities\itembase\fireplacebase.c:107`-`109` |
| 22 | Vehicle smoke | `EffVehicleSmoke`, `EffExhaustSmoke`, `EffWheelSmoke`. | `P:\scripts\3_game\effects\effectparticle\vehiclesmoke.c:1`; `P:\scripts\4_world\entities\effects\wheelsmoke.c:1` |
| 23 | Explosions | `Explode`, explosive bases, grenades; explosion particle via `ParticleManager`. | `P:\scripts\3_game\entities\object.c:144`; `P:\scripts\4_world\entities\explosivesbase.c:19`; `P:\scripts\4_world\entities\itembase\grenade_base.c:30`; `P:\scripts\3_game\dayzgame.c:3637` |
| 24 | Particle config classes | Particle effect config block. | `P:\DZ\data\data\particleeffects\config.cpp` |
| 25 | Lights | `ScriptedLightBase`, `PointLightBase`, `EntityLightSource`, `SetBrightnessTo`. | `P:\scripts\4_world\entities\scriptedlightbase.c:10`; `...\scriptedlightbase\pointlightbase.c:1`; `P:\scripts\3_game\entities\entitylightsource.c:8` |
| 26 | Post-process effects | `PPEManager`, `PPERequesterBank`, legacy `PPEffects`. | `P:\scripts\3_game\ppemanager\ppemanager.c:53`; `P:\scripts\3_game\ppemanager\pperequesterbank.c:4`; `P:\scripts\3_game\ppeffects.c:2` |
| 27 | Camera shake | `CameraShake`. | `P:\scripts\4_world\classes\camerashake.c:1` |
| 28 | Contaminated area visuals | `EffectArea`, dynamic gas area. | `P:\scripts\4_world\classes\contaminatedarea\effectarea.c:49`; `...\contaminatedarea_dynamic.c:22` |
| 29 | Swarming flies and ambient effects | `EffSwarmingFlies`. | `P:\scripts\3_game\effects\effectparticle\swarmingflies.c:1` |
| 30 | Client versus server | Sounds and particles are client-only; server triggers via net-synced variables or RPC (see `RegisterNetSyncVariableBoolSignal`). | `P:\scripts\4_world\entities\vehicles\carscript.c:280` |
| 31 | Audio file format | `.ogg` (or `.wss`) samples, mono for 3D sounds. **knowledge** | Sample paths inside `P:\DZ\sounds` |
