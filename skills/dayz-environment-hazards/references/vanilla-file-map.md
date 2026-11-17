# Vanilla file map for environment hazards

Which vanilla file holds which part of the 1.30 hazard systems, what could not be checked, and claims from earlier notes that turned out wrong. Every path in the first table exists on `P:\` (DayZ 1.30); line numbers are in the topic files, not here.

## Files on `P:\`

| File | What is in it |
|---|---|
| `P:\scripts\3_game\sandstorm.c` | `SandstormController` API and `GetScriptedType` |
| `P:\scripts\3_game\weather.c` | `GetSandstorm`, the obsolete noise reduction helpers |
| `P:\scripts\3_game\worlddata.c` | `StartSandstorm`, sun effect, dust settings, `m_sandstormFrequency` |
| `P:\scripts\3_game\cfggameplaydatajson.c` | `ITEM_SandstormData` |
| `P:\scripts\3_game\cfggameplayhandler.c` | `GetSandstormFrequency` |
| `P:\scripts\3_game\enums\eagents.c` | `SILICOSIS` 512, `EYES_IRRITATION` 1024 |
| `P:\scripts\3_game\constants.c` | `AGT_AIRBOURNE_SOLID`, `DEF_DUST_PARTICLE_*`, `ENVIRO_TICK_SHADOW_RC_CHECK`, motorbike and boat heat comfort speeds |
| `P:\scripts\3_game\playerconstants.c` | `THERMAL_BIAS_*` |
| `P:\scripts\3_game\surfaceinfo.c` | dust getters |
| `P:\scripts\3_game\dustkickupeffects.c` | kickup dust |
| `P:\scripts\3_game\ppemanager\requesters\ppersandstorm.c` | sandstorm post process |
| `P:\scripts\3_game\vehicles\transport.c` | `GetWeightCoef` |
| `P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c` | shelter |
| `P:\scripts\4_world\systems\sandstorm\playersandstormdata.c` | per player state |
| `P:\scripts\4_world\classes\playermodifiers\emodifiers.c` | the new modifier IDs |
| `P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c` | eyes and heat stroke sync bits |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c` | feeding the thermal bias |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c` | the four phases |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\silicosis.c` | silicosis thresholds |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\irritatedeyes.c` | eye effect from 15 agents |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\sandstormexposure.c` | agent transmission, coughing |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\immunesystem.c` | the sick notifier |
| `P:\scripts\4_world\classes\transmissionagents\agents\silicosisagent.c` | silicosis agent |
| `P:\scripts\4_world\classes\transmissionagents\agents\eyesirritation.c` | eye irritation agent |
| `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c` | the `AGT_AIRBOURNE_SOLID` case, cached equipment protection |
| `P:\scripts\4_world\classes\thermalbiashandler.c` | `Add`, resistance, save and load |
| `P:\scripts\4_world\classes\environment\environment.c` | shade, sun, motorbike and boat wind |
| `P:\scripts\4_world\classes\worlds\nasdara.c` | sand weather, sun table, dust settings |
| `P:\scripts\4_world\classes\worlds\chernarusplus.c` | no sun table, no `StartSandstorm` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c` | washing the head |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheaditemcontinuous.c` | washing from a bottle |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwetclothinginhandsbase.c` | wetting clothing in hands |
| `P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c` | the 3 to 10 s ignition delay |
| `P:\scripts\4_world\classes\contaminatedarea\effectarea.c` | `OnCEIterate`, `OIL_PIT = 8`, `SurfaceRoadY` |
| `P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c` | 20 heat damage per second |
| `P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c` | ceiling dust |
| `P:\scripts\4_world\classes\dust\dusteffectsmanager.c` | dust manager |
| `P:\scripts\4_world\entities\effects\vehicledust.c` | vehicle dust particle overrides |
| `P:\scripts\4_world\entities\effects\effwheelcontact.c` | wheel contact effect |
| `P:\scripts\4_world\entities\effects\wheelsmoke.c` | obsolete `SetSurface` |
| `P:\scripts\4_world\static\surface.c` | obsolete surface getters |
| `P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c` | `GetSurface` |
| `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c` | weight coefficient 1.5 |
| `P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c` | weight coefficient 2.0 |
| `P:\scripts\4_world\entities\vehicles\boatscript.c` | `GetHeatComfortOverride` |
| `P:\scripts\4_world\entities\manbase\playerbase.c` | handler creation, `HasDisease`, the handler's save and load calls |
| `P:\scripts\4_world\classes\playersymptoms\states\secondary\squintstate.c` | eye protection for squinting |
| `P:\scripts\5_mission\mission\gameplayeffectwidgets\gewidgetsmetadataeyeveins.c` | eye veins screen effect (file exists; not read for these notes) |
| `P:\scripts\5_mission\mission\gameplayeffectwidgets\gewidgetsmetadatasquinting.c` | squinting screen effect (file exists; not read for these notes) |
| `P:\DZ\data\config.cpp` | `class Sandstorm` in the default world |
| `P:\DZ\data\aiconfigs\config.cpp` | `AIParams` noise multipliers |
| `P:\DZ\characters\masks\config.cpp` | `dust_particle_breath` and `dust_particle_eyes` on masks |
| `P:\DZ\characters\glasses\config.cpp` | `dust_particle_eyes` on eyewear |
| `P:\graphics\materials\postprocess\sandstorm.emat` | the `SnowEffect` material of the storm |

## Not on `P:\`

The source notes read these in the game's own PBOs; they are not unpacked on `P:\` and were not checked here:

- The Nasdara data addon (`DZ\data_takistan\config.cpp`, `basicDefines.hpp`, `aiconfigs\config.cpp`) and the PBO listings of builds 1.30.164014 and 1.30.164200.
- The 1.30 changelog entries (`OnCEIterate`, native AI noise, the known issues list).
- Everything reported for build 1.30.164289: the topic files mark each such line.

## Not checked anywhere

1. The native `SandstormController`: how the storm grows, its magnitude and `GetPointOnEdge` live in the game executable.
2. The Nasdara terrain: no listed PBO has a `.wrp`; it is presumably inside the encrypted `worlds_nasdara.ebo`.
3. Binary assets (`.p3d`, `.ptc`, `.edds`): only their names in listings; emitter curves were not read.
4. Run time: no tick was measured in game. Every line in this skill is read from source.
5. Log texts to search for in the RPT (`ThermalBiasHandler`, `Sandstorm`, `Could not get players sandstorm data`) were not confirmed against a real log.

## Corrections to earlier notes

Claims that circulated in earlier digests of the 1.30 scripts and are wrong on `P:\`:

| Earlier claim | What `P:\` shows |
|---|---|
| The shadow check runs every 5 s | Every 30 s: `ENVIRO_TICK_SHADOW_RC_CHECK` (`P:\scripts\3_game\constants.c:760`) |
| The area enum is `EOffsetDataAreaType` | It is `EEffectAreaType` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:10`) |
| The new modifiers are integers 59 to 66 | The enum has no explicit numbers after `MDF_TEMPERATURE = 1`; use the names (`P:\scripts\4_world\classes\playermodifiers\emodifiers.c:3`) |
| The `AGT_AIRBOURNE_SOLID` case is at line 377 of the transmission plugin | It is at `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414` |
| `PlayerBase` saves the thermal bias handler around line 941 | That area is `OnUpdateEffectAreaServer` (`P:\scripts\4_world\entities\manbase\playerbase.c:911`); the save call is `m_ThermalBiasHandler.OnStoreSave(ctx)` at `P:\scripts\4_world\entities\manbase\playerbase.c:7395` |
| Motorbike and boat wind is at lines 371 to 402 and 884 to 942 of the environment class | It is `DetermineHeatcomfortBehavior` at `P:\scripts\4_world\classes\environment\environment.c:575`; line 889 is `GetWetDelta` |
| Motorbikes have a dust weight coefficient of 0.25 | `Motorbike_01` returns 0.5 and `Motorbike_02` 0.75 from `GetWeightCoef` (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:87`) |
| A mask cancels the sandstorm cough | Only when its `DEF_DUST_PARTICLE_BREATH` protection covers the storm's intensity: `coughIntensity` is intensity minus protection (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\sandstormexposure.c:143`) |
| The Nasdara data config has skinning entries at lines 214 to 239 | Per the source notes that config ends near line 60; the yields are in `basicDefines.hpp`. Not on `P:\` |
