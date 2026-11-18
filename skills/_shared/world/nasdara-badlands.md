# Nasdara and the Badlands DLC

What the Badlands DLC adds as a world: the Nasdara world data on `P:\`, the bunkers announced by radio, the irrigation tunnel entrance, and the data files that are not on `P:\`. The scripts are checked on `P:\` (DayZ 1.30); every line marked "not on `P:\`" comes from the game's own PBOs on builds 1.30.164014 and 1.30.164200 and was not checked here. The map was not loaded in game.

Nasdara's weather and storms are in `sandstorm.md`, its sun table in `heat-stroke.md`, and its ambient dust settings in `surface-dust.md`.

## The world data on `P:\`

`NasdaraData` lives in `P:\scripts\4_world\classes\worlds\nasdara.c`. Its monthly maximum temperatures (`m_MaxTemps`) peak at 38.4 in July (`P:\scripts\4_world\classes\worlds\nasdara.c:49`). It is the only vanilla world data that starts sandstorms from the weather and the only one that fills the sun table; a custom desert world copies those parts of it.

## Bunkers announced by radio

- The classes are `Land_Bunker_Basement_Civilian`, `Land_Bunker_Basement_Storage`, `Land_Bunker_Basement_Medical` and the three `Land_Bunker_Shelter_*` ones, all `BroadcastedBunker` (`P:\scripts\4_world\entities\building\bunker.c:331` to `:336`), each with a code lock.
- The radio broadcasts coordinates and the code in Morse (not on `P:\`; the broadcast was not heard in game).
- It is configured in `cfgbunkerbroadcast.json`, in `$mission:` or in `dz/worlds/<world>/ce/` (`m_ConfigFilePath`, `P:\scripts\3_game\cfgbunkerbroadcasthandler.c:5`, `:26` to `:27`), plus `bunkerBroadcastEnabled` in `cfggameplay.json` (`P:\scripts\3_game\cfggameplaydatajson.c:193`).
- The broadcast's state file is in `_shared/persistence/versioning-and-migration.md`; code locks and rebuilding are in `_shared/persistence/base-building.md`.

## Irrigation tunnel

`Land_IrrigationTunnel_Entrance_01` sits in the `rebuildable` script folder (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1`): the entrance can be rebuilt, and its debug spawn fills it with sticks and rope (`OnDebugSpawn`, `irrigationtunnel_entrance.c:3` to `:11`).

## Underground facilities

Announced for Badlands on 2026-09-22, not checked on `P:\`: the Badlands underground facilities use the terrain holes system, which will also be available for other maps and for mods (`terrain-holes.md`). What the Nasdara PBOs hold underground was not read.

## Data files (not on `P:\`)

- The mod class is `CfgMods.nasdara` with `appId = 3816030`; the data addon's internal prefix is `DZ\data_takistan`.
- On 1.30.164014, `data_nasdara.pbo` held 6 files: its config, `basicdefines.hpp`, the AI config and an impact test model with its `.bisurf` and `.rvmat`. There was no `.wrp` and no navmesh.
- 1.30.164200 installs `nasdara\addons\` with 24 PBOs and `worlds_nasdara.ebo`. `worlds_nasdara_nav.pbo` holds `navmesh.nm`, `worlds_nasdara_ce.pbo` holds the Central Economy files (34 `.xml`, 4 `.json`, `areaflags.map`), and `data_nasdara.pbo` has 8 files (the same 6 plus `mud_brick_impenetrable.bisurf` and its `.rvmat`). No PBO lists a `.wrp`; as with Sakhal, the world is presumably inside the encrypted `.ebo`, which was not opened. The dedicated server ships the mission `mpmissions\dayzOffline.nasdara`.
- Skinning yields in its `basicDefines.hpp`: mouflon 10 steaks, 2 guts, 1 lard, 1 bones; dog the same kinds plus a head; lizard 1 of each. The yields are in that file, not in the data config, which ends near line 60.
- AI groups in its AI config: `DZMouflonGroupBeh` of type `DomesticHerbivores`, and `DZDogGroupBeh` of type `Predators` with `siegeAttackCountdownMin` and `siegeAttackCountdownMax` of 10 and 15.
- The 1.30 changelog says the 1.30 navmesh is not backwards compatible: a custom terrain's navmesh has to be generated again.
