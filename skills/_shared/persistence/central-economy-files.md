# Central economy files

The structure and stock values of the central economy files a 1.30 server reads, so that a mod's `types.xml` or `cfgspawnabletypes.xml` snippet, or a server owner's edit, matches the format. Open this when writing or checking an economy file, or when deciding which categories the economy saves. How a `types.xml` entry for a mod item looks, and the runtime spawn flags, are in `_shared/enscript/integrations/central_economy.md`; how lifetime behaves at run time is in `lifetime-and-storage.md`.

`MISSION` below is `P:\DZ\worlds\chernarusplus\ce\` (another map: `P:\DZ\worlds\<map>\ce\`). It holds the same files as `mpmissions\dayzOffline.chernarusplus\` in the DayZ Server install. Counts are for Chernarus. What a key does is stated only where the file's own comment or a vanilla script says so; everything else is structure and stock values.

## `db/economy.xml`: which categories load, save and respawn

One empty element per category, each with `init`, `load`, `respawn` and `save` flags (`MISSION\db\economy.xml:3-10`):

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

`economy.xml` lists no files; the root classes are in `cfgeconomycore.xml`.

## `cfgeconomycore.xml`: root classes and defaults

`<classes>` lists `<rootclass name="..."/>` entries. The file's comment asks for `act="character"` on a root class that is a player, infected or animal, and `act="car"` on vehicles. The stock roots are `DefaultWeapon`, `DefaultMagazine`, `Inventory_Base`, `HouseNoDestruct`, `SurvivorBase` and `DZ_LightAI` (both `character`), `CarScript`, `BoatScript` and `MotorbikeScript` (all `car`), and `HouseDestructible` (`MISSION\cfgeconomycore.xml:9-18`). A custom map whose copy of this file lacks `MotorbikeScript` and `HouseDestructible` cannot spawn those classes through the economy (error E21 in `skills/dayz-launch-test/references/error-catalog.md`).

`<defaults>` sets `dyn_radius` (30 stock, `:21`), the `dyn_smin`, `dyn_smax`, `dyn_dmin` and `dyn_dmax` values, the `log_ce_*` switches (loop, dynamic events, vehicles, loot spawn, cleanup, respawn, statistics, infected; all `false`), `log_storageinfo`, `log_hivewarning`, `log_missionfilewarning`, `save_events_startup` and `save_types_startup` (`:20-39`).

## `db/types.xml`: stock lifetimes

The stock file has 2382 types. Their `lifetime` values:

| `lifetime` (seconds) | Types | Examples |
|---|---|---|
| 14400 (4 h) | 1293 | most loot |
| 28800 (8 h) | 441 | |
| 1800 (30 min) | 383 | |
| 0 | 71 | `nominal` 0 entries such as the `Land_Container_*` classes |
| 7200 (2 h) | 61 | `AKM` (`MISSION\db\types.xml:124-136`) |
| 900 and 3 | 34 each | |
| 3888000 (45 days) | 22 | tents, barrels, `SeaChest`, `WoodenCrate`, `Fence` (`:7772-7775`), `Watchtower` |
| 604800 (7 days) | 14 | `TerritoryFlag`, `GardenPlot`, `PowerGenerator`, traps, shelters |

Rarer values: 9000 (13 types), 5400 (7), 432000 (3), 1209600 (2), and 30, 300, 2600 and 9800 (one each). What `lifetime` 0 does was not measured. `cost` is 100 on every type except `Mag_SVD_10Rnd` (1000, `MISSION\db	ypes.xml:14956`); its effect was not measured.

## `cfglimitsdefinition.xml` and `cfglimitsdefinitionuser.xml`

`cfglimitsdefinition.xml` defines the names `types.xml` may use, in four blocks under `<lists>` (`MISSION\cfglimitsdefinition.xml:2-44`):

- `<categories>`: `tools`, `containers`, `clothes`, `lootdispatch`, `food`, `weapons`, `books`, `explosives`.
- `<tags>`: `floor`, `shelves`, `ground`.
- `<usageflags>`: `Military`, `Police`, `Medic`, `Firefighter`, `Industrial`, `Farm`, `Coast`, `Town`, `Village`, `Hunting`, `Office`, `School`, `Prison`, `Lunapark`, `SeasonalEvent`, `ContaminatedArea`, `Historical`. The medical one is `Medic` (`:21`), not `Medical`.
- `<valueflags>`: `Tier1` to `Tier4` and `Unique`.

`cfglimitsdefinitionuser.xml` groups those names under new ones, for example `<user name="TownVillage">` with the usages `Town` and `Village` (`MISSION\cfglimitsdefinitionuser.xml:2-7`).

## `cfgspawnabletypes.xml` and `cfgrandompresets.xml`

`cfgspawnabletypes.xml` has a `<type name="...">` entry for each class that needs more than `types.xml` gives: 721 in the stock file, plus 17 inside comments (`MISSION\cfgspawnabletypes.xml:3125-3203` and `:4202-4347`). `HuntingVest` has two entries (`:587` and `:593`). Child elements in the 1.30 file:

- `<hoarder/>`: marks a storage container (`Barrel_Blue`, `WoodenCrate` and others; 17 entries, `MISSION\cfgspawnabletypes.xml:4-53`).
- `<damage min="0.0" max="0.32"/>`: the spawn damage range (89 entries, for example `:56`).
- `<attachments chance="...">` with `<item name="..." chance="..."/>` children (`AKM`, `:2674`); the file does not say how the block's chance and its items' chances combine.
- `<cargo chance="...">` with items, the same shape, for container contents.
- `<attachments preset="name"/>` and `<cargo preset="name"/>`: a named list from `cfgrandompresets.xml` (`DuffelBagSmall_Green` with `foodArmy` and `mixArmy`, `:395-397`).
- `<tag name="shelves"/>` (`:400`).

`cfgrandompresets.xml` defines the presets as `<cargo chance="0.15" name="foodHermit">` or `<attachments ...>` blocks with `<item name chance>` children (`MISSION\cfgrandompresets.xml:3-4`). The stock 1.30 files have no quantity attributes and no `equip` attribute.

## `db/events.xml` and `cfgeventspawns.xml`

An `<event name="...">` carries `nominal`, `min`, `max`, `lifetime`, `restock`, `saferadius`, `distanceradius`, `cleanupradius`, an optional `secondary` (an infected event spawned with it), `<flags deletable init_random remove_damaged/>`, `<position>`, `<limit>`, `<active>` and `<children>` with `<child lootmax lootmin max min type/>` entries. `<position>` is `fixed` on the events that `cfgeventspawns.xml` places, except the inactive `StaticChristmasTree`, which is `uniform`. Example: `StaticHeliCrash`, `nominal` 3, `lifetime` 2100, all three radii 1000, `secondary` `InfectedArmy`, one child `Wreck_UH1Y` with 10 to 15 loot items (`MISSION\db\events.xml:822-839`).

Sakhal's static events with `<active>1</active>` (`P:\DZ\worlds\sakhal\ce\db\events.xml:739-996`): `StaticAmbulance`, `StaticBoatFishing`, `StaticBoatMilitary` (child `StaticObj_PatrolBoat_Military_DE`, `:807`), `StaticContainerLocked`, `StaticHeliCrash`, `StaticPoliceCar`, `StaticScientist`. Defined but inactive: `StaticAirplaneCrate`, `StaticBonfire`, `StaticChristmasTree`, `StaticFridgeTest`, `StaticMilitaryConvoy`, `StaticPoliceSituation`, `StaticSantaCrash`, `StaticTrain`.

`cfgeventspawns.xml` lists the positions per event as `<pos>` elements: 1532 in the stock file, 1121 of them `<pos x z a/>` (`MISSION\cfgeventspawns.xml:2-4`); the others carry `x z` only, or `y` and `group` as well.

## `cfgignorelist.xml`

`<ignore>` with `<type name="..."></type>` entries: `Bandage`, the bandana and heist masks, `CattleProd`, `Defibrillator`, `EngineOil`, `HescoBox`, `EasterEgg`, `StunBaton`, `TransitBus`, `Spear`, `Mag_STANAGCoupled_30Rnd`, `Wreck_Mi8`, `Flaregun` and the flare rounds (`MISSION\cfgignorelist.xml:2-27`). The file has no comment; what the economy does with these classes was not measured.

## `db/globals.xml`

`<var name type value/>`, where `type="0"` is an integer and `type="1"` a float (`MISSION\db\globals.xml:3-32`). Stock values: `AnimalMaxCount` 200, `CleanupAvoidance` 100, `CleanupLifetimeDeadAnimal` 1200, `CleanupLifetimeDeadInfected` 330, `CleanupLifetimeDeadPlayer` 3600, `CleanupLifetimeDefault` 45, `CleanupLifetimeLimit` 50, `CleanupLifetimeRuined` 330, `FlagRefreshFrequency` 432000, `FlagRefreshMaxDuration` 3456000, `FoodDecay` 1, `IdleModeCountdown` 60, `IdleModeStartup` 1, `InitialSpawn` 100, `LootDamageMax` 0.82, `LootDamageMin` 0.0, `LootProxyPlacement` 1, `LootSpawnAvoidance` 100, `RespawnAttempt` 2, `RespawnLimit` 20, `RespawnTypes` 12, `RestartSpawn` 0, `SpawnInitial` 1200, `TimeHopping` 60, `TimeLogin` 15, `TimeLogout` 15, `TimePenalty` 20, `WorldWetTempUpdate` 1, `ZombieMaxCount` 1000, `ZoneSpawnDist` 300.

Script reads any of them with `GetCEApi().GetCEGlobalInt(name)` or `GetCEGlobalFloat(name)` (`P:\scripts\3_game\ce\centraleconomy.c:585` and `:592`). Vanilla reads:

- `FlagRefreshFrequency` and `FlagRefreshMaxDuration`, in seconds (5 and 40 days stock): the territory flag's refresh interval and cap, used only when above 0 (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:34-46`).
- `CleanupLifetimeDeadPlayer`: read inside `DeathDropHandEntity`, where it sets the lifetime of the item dropped from the hands, not of the body (`P:\scripts\4_world\entities\dayzplayerimplement.c:608-646`).
- `FoodDecay`: read as a float, and as an integer when the float read returns `float.MIN`, so both `type` values work (`P:\scripts\3_game\dayzgame.c:1164-1170`).
- `WorldWetTempUpdate`: world wetness and temperature updates run only when it is 1 (`dayzgame.c:1162`).
