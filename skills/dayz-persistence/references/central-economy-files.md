# Central Economy files on DayZ 1.30

The structure of the Central Economy (CE) files as the 1.30 dedicated server ships them, so that a mod's `types.xml` / `cfgspawnabletypes.xml` snippet or a server owner's edit matches the format the server reads. `MISSION` is `mpmissions/dayzOffline.chernarusplus/` in the DayZ Server install; counts are for Chernarus. These mission files are not on `P:\`, so their `MISSION/...:line` citations cannot be checked there. The source pack read them from the 1.30.164289 server (claim `CLAIM-CE-STOCK-FILES-164289`); the `economy.xml` flags, the `types.xml` type and lifetime counts, the `globals.xml` values, the `cfgeconomycore.xml` root classes and the `cfgspawnabletypes.xml` entry count were compared with a local DayZ Server install and match. Script citations are from `P:\` (game storage version 144). What a key *does* is only stated where the file's own comment or a vanilla script says so; the rest is structure and stock values. How a missing `types.xml` entry behaves at run time is measured in `lifetime-and-storage.md`. Server-side settings outside the CE (`serverDZ.cfg`, `cfggameplay.json`, `cfgeffectarea.json`, `messages.xml`) are covered by the in-game test material (the dayz-test-ingame skill of the source pack) and by `dayz-server-admin`.

## `db/economy.xml`: which CE categories load, save and respawn

One empty element per category, each with `init`, `load`, `respawn` and `save` flags (0/1). Stock values (`MISSION/db/economy.xml:3-10`):

| Element | init | load | respawn | save |
|---|---|---|---|---|
| `dynamic` | 1 | 1 | 1 | 1 |
| `animals` | 1 | 0 | 1 | 0 |
| `zombies` | 1 | 0 | 1 | 0 |
| `vehicles` | 1 | 1 | 1 | 1 |
| `randoms` | 0 | 0 | 1 | 0 |
| `custom` | 0 | 0 | 0 | 0 |
| `building` | 1 | 1 | 0 | 1 |
| `player` | 1 | 1 | 1 | 1 |

There is no file list in `economy.xml`; the list of root classes is in `cfgeconomycore.xml`.

## `cfgeconomycore.xml`: root classes and CE defaults

`<classes>` lists `<rootclass name="..."/>` entries; the file's comment asks for `act="character"` on a root class that is a player, infected or animal, and `act="car"` on movable vehicles (`MISSION/cfgeconomycore.xml:4-8`). Stock roots: `DefaultWeapon`, `DefaultMagazine`, `Inventory_Base`, `HouseNoDestruct`, `SurvivorBase` (character), `DZ_LightAI` (character), `CarScript`, `BoatScript`, `MotorbikeScript` (all `car`) and `HouseDestructible` (`:9-18`). `<defaults>` sets `dyn_radius`, `dyn_smin`/`dyn_smax`/`dyn_dmin`/`dyn_dmax`, the `log_ce_*` switches (loop, dynamic events, vehicles, loot spawn, cleanup, respawn, statistics, zombies; all `false`), `log_storageinfo`, `log_hivewarning`, `log_missionfilewarning`, `save_events_startup` and `save_types_startup` (`:20-39`). A custom map whose copy of this file lacks `MotorbikeScript` and `HouseDestructible` fails to load those classes (error E21 in the source pack's mod workflow error catalog).

## `db/types.xml`

One `<type name="Class">` per spawnable class with `nominal`, `lifetime` (seconds), `restock`, `min`, `quantmin`/`quantmax`, `cost`, a `<flags>` element (`count_in_cargo`, `count_in_hoarder`, `count_in_map`, `count_in_player`, `crafted`, `deloot`) and any number of `<category>`, `<usage>`, `<value>` and `<tag>` references to names defined in `cfglimitsdefinition.xml`. Example: `AKM` (`MISSION/db/types.xml:124-136`).

Lifetimes in the stock file (2382 types):

| `lifetime` | Types | Examples |
|---|---|---|
| 14400 (4 h) | 1293 | most loot |
| 28800 (8 h) | 441 | |
| 1800 (30 min) | 383 | |
| 7200 (2 h) | 61 | `AKM` |
| 0 | 71 | `Land_Container_*` and other `nominal` 0 entries (`:12309-12311`) |
| 604800 (7 d) | 14 | `TerritoryFlag`, `GardenPlot`, `PowerGenerator`, traps, shelters |
| 3888000 (45 d) | 22 | tents, barrels, `SeaChest`, `WoodenCrate`, `Fence`, `Watchtower` |

Other values: 3 and 900 (34 types each), 9000 (13), 5400 (7), 432000 (3), 1209600 (2), and 30, 300, 2600 and 9800 (one each). What `lifetime` 0 does was not measured. `cost` is 100 on every type except `Mag_SVD_10Rnd` (1000, `:14956`); its effect was not measured.

## `cfglimitsdefinition.xml` and `cfglimitsdefinitionuser.xml`

`cfglimitsdefinition.xml` defines the names `types.xml` may use, in four blocks under `<lists>` and nothing else (`MISSION/cfglimitsdefinition.xml:2-44`):

- `<categories>`: `tools`, `containers`, `clothes`, `lootdispatch`, `food`, `weapons`, `books`, `explosives`.
- `<tags>`: `floor`, `shelves`, `ground`.
- `<usageflags>`: `Military`, `Police`, `Medic`, `Firefighter`, `Industrial`, `Farm`, `Coast`, `Town`, `Village`, `Hunting`, `Office`, `School`, `Prison`, `Lunapark`, `SeasonalEvent`, `ContaminatedArea`, `Historical`. The medical one is `Medic`, not `Medical`.
- `<valueflags>`: `Tier1` to `Tier4` and `Unique`.

`cfglimitsdefinitionuser.xml` groups those names under new ones, e.g. `<user name="TownVillage">` with the usages `Town` and `Village` (`MISSION/cfglimitsdefinitionuser.xml:2-7`).

## `cfgspawnabletypes.xml` and `cfgrandompresets.xml`

`cfgspawnabletypes.xml` has `<type name="...">` entries for the classes that need more than `types.xml` gives (721 in the stock file, plus 17 inside comments at `:3125-3203` and `:4202-4347`; `HuntingVest` has two, `:587` and `:593`). Child elements in the 1.30 file:

- `<hoarder/>`: marks a storage container (`Barrel_Blue`, `WoodenCrate`, ...; 17 entries, `:4-53`).
- `<damage min="0.0" max="0.32"/>`: spawn damage range (89 entries, e.g. `:56`).
- `<attachments chance="0.25">` with `<item name="..." chance="1.00"/>` children (`AKM`, `:2674-2692`); the file does not say how the block's chance and its items' chances combine.
- `<cargo chance="...">` with items, same shape, for container contents.
- `<attachments preset="name"/>` and `<cargo preset="name"/>`: a named list from `cfgrandompresets.xml` (e.g. `DuffelBagSmall_Green` with `foodArmy` and `mixArmy`, `:395-397`).
- `<tag name="shelves"/>` (`FirstAidKit`, `:400`).

`cfgrandompresets.xml` defines those presets as `<cargo chance="0.15" name="foodHermit">` or `<attachments ...>` blocks with `<item name chance>` children (`MISSION/cfgrandompresets.xml:3-7`). The stock 1.30 files contain no quantity attributes and no `equip` attribute.

## `db/events.xml` and `cfgeventspawns.xml`

An `<event name="...">` carries `nominal`, `min`, `max`, `lifetime`, `restock`, `saferadius`, `distanceradius`, `cleanupradius`, an optional `secondary` (an infected event spawned with it), `<flags deletable init_random remove_damaged/>`, `<position>` (`fixed` on the events that `cfgeventspawns.xml` places, except the inactive `StaticChristmasTree`, which is `uniform`), `<limit>` (`child` etc.), `<active>` and `<children>` with `<child lootmax lootmin max min type/>`. Example: `StaticHeliCrash`, nominal 3, lifetime 2100, all three radii 1000, secondary `InfectedArmy`, child `Wreck_UH1Y` with 10 to 15 loot items (`MISSION/db/events.xml:822-839`). `cfgeventspawns.xml` lists the positions per event as `<pos>` elements, `<pos x z a/>` in 1121 of the 1532 (`MISSION/cfgeventspawns.xml:2-4`); the others carry `x z` only, or `y` (and `group`) as well.

Sakhal's static events with `<active>1</active>` (`mpmissions/dayzOffline.sakhal/db/events.xml:739-996`): `StaticAmbulance`, `StaticBoatFishing`, `StaticBoatMilitary` (child `StaticObj_PatrolBoat_Military_DE`, `:807`), `StaticContainerLocked`, `StaticHeliCrash`, `StaticPoliceCar`, `StaticScientist`. Defined but inactive: `StaticAirplaneCrate`, `StaticBonfire`, `StaticChristmasTree`, `StaticFridgeTest`, `StaticMilitaryConvoy`, `StaticPoliceSituation`, `StaticSantaCrash`, `StaticTrain`.

## `cfgignorelist.xml`

`<ignore>` with `<type name="..."></type>` entries: `Bandage`, the bandana and heist masks, `CattleProd`, `Defibrillator`, `EngineOil`, `HescoBox`, `EasterEgg`, `StunBaton`, `TransitBus`, `Spear`, `Mag_STANAGCoupled_30Rnd`, `Wreck_Mi8`, `Flaregun` and the flare rounds (`MISSION/cfgignorelist.xml:2-27`). The file carries no comment; what the CE does with these classes was not measured here.

## `db/globals.xml`

`<var name type value/>`, where `type="0"` is an integer and `type="1"` a float (`LootDamageMin` / `LootDamageMax` are the stock floats). Stock values (`MISSION/db/globals.xml:3-32`): `AnimalMaxCount` 200, `CleanupAvoidance` 100, `CleanupLifetimeDeadAnimal` 1200, `CleanupLifetimeDeadInfected` 330, `CleanupLifetimeDeadPlayer` 3600, `CleanupLifetimeDefault` 45, `CleanupLifetimeLimit` 50, `CleanupLifetimeRuined` 330, `FlagRefreshFrequency` 432000, `FlagRefreshMaxDuration` 3456000, `FoodDecay` 1, `IdleModeCountdown` 60, `IdleModeStartup` 1, `InitialSpawn` 100, `LootDamageMax` 0.82, `LootDamageMin` 0.0, `LootProxyPlacement` 1, `LootSpawnAvoidance` 100, `RespawnAttempt` 2, `RespawnLimit` 20, `RespawnTypes` 12, `RestartSpawn` 0, `SpawnInitial` 1200, `TimeHopping` 60, `TimeLogin` 15, `TimeLogout` 15, `TimePenalty` 20, `WorldWetTempUpdate` 1, `ZombieMaxCount` 1000, `ZoneSpawnDist` 300.

Script can read any of them with `GetCEApi().GetCEGlobalInt(name)` / `GetCEGlobalFloat(name)` (`P:\scripts\3_game\ce\centraleconomy.c:585`, `:592`). Vanilla does so for:

- `FlagRefreshFrequency` and `FlagRefreshMaxDuration` (seconds; 5 and 40 days stock): the territory flag's refresh interval and cap, used only when greater than 0 (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:34-46`).
- `CleanupLifetimeDeadPlayer`: its consumer in `P:\scripts\4_world\entities\dayzplayerimplement.c:608-646` is inside `DeathDropHandEntity` and adjusts the lifetime of the item dropped from the hands, not the corpse. No corpse-lifetime consumer is claimed here.
- `FoodDecay`: read as a float, and as an integer if the float read returns `float.MIN`, so both `type` values work (`P:\scripts\3_game\dayzgame.c:1164-1170`).
- `WorldWetTempUpdate`: world wetness/temperature updates are on only when it equals 1 (`dayzgame.c:1162`).
