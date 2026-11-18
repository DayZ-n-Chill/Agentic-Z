# Nasdara and the Badlands DLC

What the Badlands DLC adds as a world: the Nasdara world data, the bunkers announced by radio, the irrigation tunnels, and the data files on `P:\`. The scripts, the Central Economy files, the navmesh and the data addon are on `P:\`; the world file itself is not. The map has not been loaded in game for this pack.

Nasdara's weather and storms are in `sandstorm.md`, its sun table in `heat-stroke.md`, its ambient dust settings in `surface-dust.md`, and its oil pits in `oil-pits.md`.

## The world data

`NasdaraData` lives in `P:\scripts\4_world\classes\worlds\nasdara.c`. Its monthly maximum temperatures (`m_MaxTemps`) peak at 38.4 in July (`nasdara.c:49`), and `environmentMaxTemps` in `cfggameplay.json` replaces them when it has 12 values (`nasdara.c:50` to `:54`). It is the only vanilla world data that starts sandstorms from the weather and the only one that fills the sun table, so a custom desert world copies those parts of it.

## Bunkers announced by radio

- The classes are `Land_Bunker_Basement_Civilian`, `Land_Bunker_Basement_Storage`, `Land_Bunker_Basement_Medical` and the three `Land_Bunker_Shelter_*` classes, all `BroadcastedBunker` (`P:\scripts\4_world\entities\building\bunker.c:331` to `:336`). Each takes a `DigitalCodeLock_Bunker` in its `att_codelock` slot and spawns a `StorageBox_Wooden` at the `storagecratepos` memory point (`bunker.c:8`, `:174` to `:176`).
- The radio plays the coordinates and the code in Morse. The Nasdara file sets the timing: `dotDuration` 0.5, `dashDuration` 1.5, `symbolGapDuration` 0.4, `wordGapDuration` 2.2, with 3 bunkers active, 4 digit codes, and a schedule from 17:45 to 06:00 (`P:\DZ\worlds\nasdara\ce\cfgbunkerbroadcast.json:2` to `:25`). The broadcast has not been heard in game.
- The broadcast is set up in `cfgbunkerbroadcast.json`, read from `$mission:` or from `dz/worlds/<world>/ce/` (`m_ConfigFilePath`, `P:\scripts\3_game\cfgbunkerbroadcasthandler.c:5`, `:22` to `:27`), and switched on by `bunkerBroadcastEnabled` in `cfggameplay.json` (`P:\scripts\3_game\cfggameplaydatajson.c:193`; `true` in `P:\DZ\worlds\nasdara\ce\cfggameplay.json:55`). With it off, `LoadData` returns before reading the file (`cfgbunkerbroadcasthandler.c:15` and `:16`).
- The broadcast's state file is in `_shared/persistence/versioning-and-migration.md`; code locks and rebuilding are in `_shared/persistence/base-building.md`.

## The irrigation tunnels

`Land_IrrigationTunnel_Entrance_01` sits in the `rebuildable` script folder (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1`): the entrance can be rebuilt, and its debug spawn fills it with sticks and rope (`OnDebugSpawn`, `irrigationtunnel_entrance.c:3` to `:11`).

Nasdara's `cfgundergroundtriggers.json` holds 1,076 triggers. 653 play `ambient_Irrigation_Tunnel_loop_SoundSet` and 87 play `ambient_Bunker_loop_SoundSet` (`P:\DZ\worlds\nasdara\ce\cfgundergroundtriggers.json`). Trigger fields and limits are in `underground-triggers.md`.

## Underground facilities

Whether Nasdara opens holes in its terrain cannot be read: its world config is not on `P:\`. The developers have said the terrain holes system is open to other maps and to mods (not checked on `P:\`). How holes work is in `terrain-holes.md`.

## Data files

| Path on `P:\` | What it holds |
|---|---|
| `P:\DZ\data_takistan\config.cpp` | `CfgPatches` `DZ_Data_Nasdara`, `CfgMods` `nasdara` with `appId` 3816030, and `ImpactTestObjectTakistan` (42 lines) |
| `P:\DZ\data_takistan\basicdefines.hpp` | skinning yields |
| `P:\DZ\data_takistan\aiconfigs\config.cpp` | the mouflon and dog group behaviours |
| `P:\DZ\data_takistan\data\penetration\` | `mud_brick` and `mud_brick_impenetrable` `.bisurf` and `.rvmat`, and the impact test model |
| `P:\DZ\worlds\nasdara\ce\` | the Central Economy and mission files: `db\`, `env\` territories, `cfgeffectarea.json`, `cfgundergroundtriggers.json`, `cfgbunkerbroadcast.json`, `cfggameplay.json`, `areaflags.map` |
| `P:\DZ\worlds\nasdara\navmesh\navmesh.nm` | the navmesh |
| `P:\DZ\worlds\nasdara\data\` | sky and cloud textures |

The data addon's prefix is `DZ\data_takistan\` (`P:\DZ\data_nasdara.txt`), so the `takistan` folders on `P:\` (`AI_takistan`, `structures_takistan` and others) are Nasdara's. No `.wrp` for Nasdara is on `P:\`.

- Skinning yields (`P:\DZ\data_takistan\basicdefines.hpp:5` to `:32`): mouflon 10 steaks, 2 guts, 1 lard, 1 bones; dog the same kinds plus a head; lizard 1 meat, 1 guts, 1 lard, 1 bones.
- AI groups (`P:\DZ\data_takistan\aiconfigs\config.cpp`): `DZMouflonGroupBeh` of type `DomesticHerbivores` (`:9` and `:11`), and `DZDogGroupBeh` of type `Predators` (`:61` and `:63`) with `siegeAttackCountdownMin` 10 and `siegeAttackCountdownMax` 15 (`:87` and `:88`).
- The 1.30 changelog says the 1.30 navmesh is not backwards compatible, so a custom terrain's navmesh has to be generated again (not checked on `P:\`).
