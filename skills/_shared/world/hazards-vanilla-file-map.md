# Where the hazard code lives

Which vanilla file holds which part of the sandstorm, heat stroke, dust and oil pit systems, what `P:\` cannot show about them, and the facts that are easiest to get wrong. Line numbers are in the topic files; this file is the map.

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
| `P:\scripts\4_world\systems\sandstorm\playersandstormdata.c` | per player storm state |
| `P:\scripts\4_world\classes\playermodifiers\emodifiers.c` | the hazard modifier IDs |
| `P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c` | eye and heat stroke sync bits |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c` | feeding the thermal bias |
| `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c` | the four heat stroke phases |
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
| `P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c` | the 3 to 9 s ignition delay |
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
| `P:\scripts\5_mission\mission\gameplayeffectwidgets\gewidgetsmetadataeyeveins.c` | eye veins screen effect (not yet read) |
| `P:\scripts\5_mission\mission\gameplayeffectwidgets\gewidgetsmetadatasquinting.c` | squinting screen effect (not yet read) |
| `P:\DZ\data\config.cpp` | `class Sandstorm` in `CAWorld` > `Weather` |
| `P:\DZ\data\aiconfigs\config.cpp` | `AIParams` noise multipliers |
| `P:\DZ\characters\masks\config.cpp` | `dust_particle_breath` and `dust_particle_eyes` on masks |
| `P:\DZ\characters\glasses\config.cpp` | `dust_particle_eyes` on glasses |
| `P:\graphics\materials\postprocess\sandstorm.emat` | the `SnowEffect` material of the storm |
| `P:\scripts\4_world\entities\itembase\clothing_base.c` | `Mask_Base` and `Glasses_Base` cached equipment categories |
| `P:\scripts\4_world\entities\itembase\clothing\gp5gasmask.c` | GP5 mask protection read from its filter |
| `P:\scripts\3_game\entities\cachedequipmentstoragebase.c` | category matching for protection queries |
| `P:\DZ\weapons\melee\config.cpp` | `HeatDamage` ammo of the oil pit |
| `P:\DZ\worlds\nasdara\ce\cfgeffectarea.json` | the 15 vanilla oil pits |
| `P:\DZ\worlds\nasdara\ce\cfggameplay.json` | `SandstormData`, `bunkerBroadcastEnabled` |

## What `P:\` does not show

The Nasdara data addon and its Central Economy files are on `P:\` (`nasdara-badlands.md`). These are not, so treat them as unverified:

- The 1.30 changelog entries for `OnCEIterate`, native AI noise and the known issues.
- The native `SandstormController`: how the storm grows, its magnitude and `GetPointOnEdge` are in the game executable.
- The Nasdara and Sakhal world configs and `.wrp` files: `P:\DZ\worlds\nasdara\` and `P:\DZ\worlds\sakhal\` hold only `ce`, `data` and `navmesh`.
- Binary assets (`.p3d`, `.ptc`, `.edds`): only their names are known, not their emitter curves.
- Run time behaviour: every line in this pack is read from source, and no tick was timed in game.
- The RPT texts the topic files name are quoted from the script that prints them; none has been seen in a real log.

## Facts that are easy to get wrong

| Fact | Source |
|---|---|
| The shade check runs every 30 s, not every 5 s | `ENVIRO_TICK_SHADOW_RC_CHECK`, `P:\scripts\3_game\constants.c:760` |
| The area enum is `EEffectAreaType` | `P:\scripts\4_world\classes\contaminatedarea\effectarea.c:10` |
| The hazard modifiers have no fixed numbers; the enum numbers nothing after `MDF_TEMPERATURE = 1`, so use the names | `P:\scripts\4_world\classes\playermodifiers\emodifiers.c:3` |
| The `AGT_AIRBOURNE_SOLID` case of the transmission plugin | `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414` |
| `PlayerBase` saves the thermal bias handler last in `OnStoreSave`, with `m_ThermalBiasHandler.OnStoreSave(ctx)`; the server update while the player stands in an effect area is `OnUpdateEffectAreaServer` | `P:\scripts\4_world\entities\manbase\playerbase.c:7395`; `:911` |
| Motorbike and boat wind is decided in `DetermineHeatcomfortBehavior`, not in `GetWetDelta` | `P:\scripts\4_world\classes\environment\environment.c:575`; `:889` |
| Motorbike dust weight is 0.5 (`Motorbike_01_ColorBase`) and 0.75 (`Motorbike_02_ColorBase`), never 0.25 | `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:1` and `:84` (`return 0.5` at `:86`); `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:1` and `:74` (`return 0.75` at `:76`) |
| A mask stops the storm cough only when its breath protection covers the storm's intensity, because `coughIntensity` is intensity minus protection | `P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\sandstormexposure.c:143` |
| A mask or glasses protect only when the script class files them as `MASK` or `EYEWEAR`; the config value alone does nothing | `P:\scripts\4_world\entities\itembase\clothing_base.c:178` and `:198` |
| Underground shelter from the storm has no 1.5 s fade; its timer is never set | `P:\scripts\4_world\systems\sandstorm\playersandstormdata.c:12` |
| Nasdara's skinning yields are in its `basicdefines.hpp`, not in the data config, which is 42 lines | `P:\DZ\data_takistan\basicdefines.hpp:5` |
