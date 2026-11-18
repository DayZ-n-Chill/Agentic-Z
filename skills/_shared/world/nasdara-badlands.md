# Nasdara and the Badlands DLC

What the Badlands DLC adds as a world: the Nasdara world data, the bunkers announced by radio, the irrigation tunnel entrance, and the data files shipped in the game's own PBOs. The scripts are on `P:\`; every line marked "not on `P:\`" comes from the Nasdara PBOs and is not checked there. The map has not been loaded in game for this pack.

Nasdara's weather and storms are in `sandstorm.md`, its sun table in `heat-stroke.md`, and its ambient dust settings in `surface-dust.md`.

## The world data

`NasdaraData` lives in `P:\scripts\4_world\classes\worlds\nasdara.c`. Its monthly maximum temperatures (`m_MaxTemps`) peak at 38.4 in July (`nasdara.c:49`). It is the only vanilla world data that starts sandstorms from the weather and the only one that fills the sun table, so a custom desert world copies those parts of it.

## Bunkers announced by radio

- The classes are `Land_Bunker_Basement_Civilian`, `Land_Bunker_Basement_Storage`, `Land_Bunker_Basement_Medical` and the three `Land_Bunker_Shelter_*` classes, all `BroadcastedBunker` (`P:\scripts\4_world\entities\building\bunker.c:331` to `:336`), each with a code lock.
- The radio broadcasts the coordinates and the code in Morse (not on `P:\`; the broadcast has not been heard in game).
- The broadcast is set up in `cfgbunkerbroadcast.json`, read from `$mission:` or from `dz/worlds/<world>/ce/` (`m_ConfigFilePath`, `P:\scripts\3_game\cfgbunkerbroadcasthandler.c:5`, `:26` and `:27`), and switched on by `bunkerBroadcastEnabled` in `cfggameplay.json` (`P:\scripts\3_game\cfggameplaydatajson.c:193`).
- The broadcast's state file is in `_shared/persistence/versioning-and-migration.md`; code locks and rebuilding are in `_shared/persistence/base-building.md`.

## The irrigation tunnel

`Land_IrrigationTunnel_Entrance_01` sits in the `rebuildable` script folder (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1`): the entrance can be rebuilt, and its debug spawn fills it with sticks and rope (`OnDebugSpawn`, `irrigationtunnel_entrance.c:3` to `:11`).

## Underground facilities

The Badlands underground facilities use the terrain holes system, which the developers have said will also be open to other maps and to mods (not on `P:\`). How holes work is in `terrain-holes.md`. What the Nasdara PBOs hold underground has not been read.

## Data files

All of this is from the Nasdara PBOs and the 1.30 changelog, not on `P:\`.

- The mod class is `CfgMods.nasdara` with `appId = 3816030`; the data addon's internal prefix is `DZ\data_takistan`.
- In the first 1.30 release, `data_nasdara.pbo` held 6 files: its config, `basicdefines.hpp`, the AI config, and an impact test model with its `.bisurf` and `.rvmat`. It had no `.wrp` and no navmesh.
- A later 1.30 update installs `nasdara\addons\` with 24 PBOs and `worlds_nasdara.ebo`. `worlds_nasdara_nav.pbo` holds `navmesh.nm`; `worlds_nasdara_ce.pbo` holds the Central Economy files (34 `.xml`, 4 `.json`, `areaflags.map`); `data_nasdara.pbo` has 8 files, the same 6 plus `mud_brick_impenetrable.bisurf` and its `.rvmat`. No PBO lists a `.wrp`; as with Sakhal, the world is presumably inside the encrypted `.ebo`, which has not been opened. The dedicated server ships the mission `mpmissions\dayzOffline.nasdara`.
- Skinning yields are in `basicDefines.hpp`: mouflon 10 steaks, 2 guts, 1 lard, 1 bones; dog the same kinds plus a head; lizard 1 of each. The data config ends near line 60 and holds no yields.
- AI groups in the AI config: `DZMouflonGroupBeh` of type `DomesticHerbivores`, and `DZDogGroupBeh` of type `Predators` with `siegeAttackCountdownMin` 10 and `siegeAttackCountdownMax` 15.
- The 1.30 changelog says the 1.30 navmesh is not backwards compatible, so a custom terrain's navmesh has to be generated again.
