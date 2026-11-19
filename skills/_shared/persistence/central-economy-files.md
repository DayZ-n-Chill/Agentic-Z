# Central economy files

What the central economy files a 1.30 server reads look like, and their stock values, so a mod's `types.xml` or `cfgspawnabletypes.xml` snippet, or a server owner's edit, matches the format. Open it when writing or checking an economy file, or when deciding which categories the economy saves. How a mod item's `types.xml` entry looks and the spawn flags used at run time are in `_shared/enscript/integrations/central_economy.md`; how lifetime behaves at run time is in `lifetime-and-storage.md`.

The files are under `P:\DZ\worlds\chernarusplus\ce\` (another map: `P:\DZ\worlds\<map>\ce\`), the same set as `mpmissions\dayzOffline.chernarusplus\` in the DayZ Server install. Counts are for Chernarus. What a key does is stated only where the file's own comment or a vanilla script says so; everything else is structure and stock values.

## Which categories load, save and respawn

`db\economy.xml` has one empty element per category, each with `init`, `load`, `respawn` and `save` flags (`P:\DZ\worlds\chernarusplus\ce\db\economy.xml:3` to `:10`):

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

## Root classes and defaults

`cfgeconomycore.xml` lists `<rootclass name="..."/>` entries under `<classes>`. Its comment asks for `act="character"` on a root class that is a player, infected or animal, and `act="car"` on vehicles. The stock roots are `DefaultWeapon`, `DefaultMagazine`, `Inventory_Base`, `HouseNoDestruct`, `SurvivorBase` and `DZ_LightAI` (both `character`), `CarScript`, `BoatScript` and `MotorbikeScript` (all `car`), and `HouseDestructible` (`P:\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:9` to `:18`). A custom map whose copy of this file lacks `MotorbikeScript` and `HouseDestructible` cannot spawn those classes through the economy (E21 in `skills/dayz-launch-test/references/error-catalog.md`).

`<defaults>` (`cfgeconomycore.xml:20` to `:39`) sets `dyn_radius` (30 stock, `:21`), `dyn_smin`, `dyn_smax`, `dyn_dmin` and `dyn_dmax`, the `log_ce_*` switches (loop, dynamic events, vehicles, loot spawn, cleanup, respawn, statistics, infected; all `false`), `log_storageinfo`, `log_hivewarning`, `log_missionfilewarning`, `save_events_startup` and `save_types_startup`.

## Stock lifetimes

`db\types.xml` has 2382 types. Their `lifetime` values:

| `lifetime` (seconds) | Types | Examples |
|---|---|---|
| 14400 (4 h) | 1293 | most loot |
| 28800 (8 h) | 441 | |
| 1800 (30 min) | 383 | |
| 0 | 71 | `nominal` 0 entries such as the `Land_Container_*` classes |
| 7200 (2 h) | 61 | `AKM` (`P:\DZ\worlds\chernarusplus\ce\db\types.xml:124` to `:136`) |
| 900 | 34 | |
| 3 | 34 | |
| 3888000 (45 days) | 22 | tents, barrels, `SeaChest`, `WoodenCrate`, `Fence` (`types.xml:7772` to `:7775`), `Watchtower` |
| 604800 (7 days) | 14 | `TerritoryFlag`, `GardenPlot`, `PowerGenerator`, traps, shelters |

Rarer values: 9000 (13 types), 5400 (7), 432000 (3), 1209600 (2), and 30, 300, 2600 and 9800 (one each). What `lifetime` 0 does is not measured. `cost` is 100 on every type except `Mag_SVD_10Rnd`, which has 1000 (`types.xml:14956`); what it does is not measured.

## Names types.xml may use

`cfglimitsdefinition.xml` defines them in four blocks under `<lists>` (`P:\DZ\worlds\chernarusplus\ce\cfglimitsdefinition.xml:2` to `:44`):

| Block | Names |
|---|---|
| `<categories>` | `tools`, `containers`, `clothes`, `lootdispatch`, `food`, `weapons`, `books`, `explosives` |
| `<tags>` | `floor`, `shelves`, `ground` |
| `<usageflags>` | `Military`, `Police`, `Medic`, `Firefighter`, `Industrial`, `Farm`, `Coast`, `Town`, `Village`, `Hunting`, `Office`, `School`, `Prison`, `Lunapark`, `SeasonalEvent`, `ContaminatedArea`, `Historical` |
| `<valueflags>` | `Tier1` to `Tier4`, `Unique` |

The medical usage is `Medic` (`cfglimitsdefinition.xml:21`), not `Medical`.

`cfglimitsdefinitionuser.xml` groups those names under new ones, for example `<user name="TownVillage">` with the usages `Town` and `Village` (`P:\DZ\worlds\chernarusplus\ce\cfglimitsdefinitionuser.xml:2` to `:7`).

## Spawnable types and random presets

`cfgspawnabletypes.xml` has a `<type name="...">` entry for each class that needs more than `types.xml` gives: 721 in the stock file, plus 17 inside comments (`P:\DZ\worlds\chernarusplus\ce\cfgspawnabletypes.xml:3125` to `:3203` and `:4202` to `:4347`). `HuntingVest` has two entries (`:587` and `:593`). The child elements in the 1.30 file:

| Element | Meaning | Example |
|---|---|---|
| `<hoarder/>` | marks a storage container; 17 entries | `Barrel_Blue`, `WoodenCrate` (`cfgspawnabletypes.xml:4` to `:53`) |
| `<damage min="0.0" max="0.32"/>` | the spawn damage range; 89 entries | `:56` |
| `<attachments chance="...">` with `<item name="..." chance="..."/>` children | the file does not say how the block's chance and its items' chances combine | `AKM`, `:2674` |
| `<cargo chance="...">` with items | the same shape, for container contents | |
| `<attachments preset="name"/>`, `<cargo preset="name"/>` | a named list from `cfgrandompresets.xml` | `DuffelBagSmall_Green` with `foodArmy` and `mixArmy`, `:395` to `:397` |
| `<tag name="shelves"/>` | a placement tag | `:400` |

`cfgrandompresets.xml` defines the presets as `<cargo chance="0.15" name="foodHermit">` or `<attachments ...>` blocks with `<item name chance>` children (`P:\DZ\worlds\chernarusplus\ce\cfgrandompresets.xml:3` and `:4`). The stock 1.30 files have no quantity attributes and no `equip` attribute.

## Events and their positions

An `<event name="...">` in `db\events.xml` carries `nominal`, `min`, `max`, `lifetime`, `restock`, `saferadius`, `distanceradius`, `cleanupradius`, an optional `secondary` (an infected event spawned with it), `<flags deletable init_random remove_damaged/>`, `<position>`, `<limit>`, `<active>` and `<children>` with `<child lootmax lootmin max min type/>` entries. `<position>` is `fixed` on the events that `cfgeventspawns.xml` places, except the inactive `StaticChristmasTree`, which is `uniform`. Example: `StaticHeliCrash`, `nominal` 3, `lifetime` 2100, all three radii 1000, `secondary` `InfectedArmy`, one child `Wreck_UH1Y` with 10 to 15 loot items (`P:\DZ\worlds\chernarusplus\ce\db\events.xml:822` to `:839`).

Sakhal's active static events (`P:\DZ\worlds\sakhal\ce\db\events.xml:739` to `:996`): `StaticAmbulance`, `StaticBoatFishing`, `StaticBoatMilitary` (child `StaticObj_PatrolBoat_Military_DE`, `:807`), `StaticContainerLocked`, `StaticHeliCrash`, `StaticPoliceCar` and `StaticScientist`. Defined but inactive: `StaticAirplaneCrate`, `StaticBonfire`, `StaticChristmasTree`, `StaticFridgeTest`, `StaticMilitaryConvoy`, `StaticPoliceSituation`, `StaticSantaCrash` and `StaticTrain`.

`cfgeventspawns.xml` lists the positions per event as `<pos>` elements: 1532 in the stock file, 1121 of them `<pos x z a/>` (`P:\DZ\worlds\chernarusplus\ce\cfgeventspawns.xml:2` to `:4`); the others carry only `x z`, or `y` and `group` as well.

## Ignore list

`cfgignorelist.xml` holds `<type name="..."></type>` entries under `<ignore>`: `Bandage`, the bandana and heist masks, `CattleProd`, `Defibrillator`, `EngineOil`, `HescoBox`, `EasterEgg`, `StunBaton`, `TransitBus`, `Spear`, `Mag_STANAGCoupled_30Rnd`, `Wreck_Mi8`, `Flaregun` and the flare rounds (`P:\DZ\worlds\chernarusplus\ce\cfgignorelist.xml:2` to `:27`). The file has no comment, and what the economy does with these classes is not measured.

## Globals

`db\globals.xml` holds `<var name type value/>` entries, where `type="0"` is an integer and `type="1"` a float (`P:\DZ\worlds\chernarusplus\ce\db\globals.xml:3` to `:32`). Stock values: `AnimalMaxCount` 200, `CleanupAvoidance` 100, `CleanupLifetimeDeadAnimal` 1200, `CleanupLifetimeDeadInfected` 330, `CleanupLifetimeDeadPlayer` 3600, `CleanupLifetimeDefault` 45, `CleanupLifetimeLimit` 50, `CleanupLifetimeRuined` 330, `FlagRefreshFrequency` 432000, `FlagRefreshMaxDuration` 3456000, `FoodDecay` 1, `IdleModeCountdown` 60, `IdleModeStartup` 1, `InitialSpawn` 100, `LootDamageMax` 0.82, `LootDamageMin` 0.0, `LootProxyPlacement` 1, `LootSpawnAvoidance` 100, `RespawnAttempt` 2, `RespawnLimit` 20, `RespawnTypes` 12, `RestartSpawn` 0, `SpawnInitial` 1200, `TimeHopping` 60, `TimeLogin` 15, `TimeLogout` 15, `TimePenalty` 20, `WorldWetTempUpdate` 1, `ZombieMaxCount` 1000, `ZoneSpawnDist` 300.

Script reads any of them with `GetCEApi().GetCEGlobalInt(name)` or `GetCEGlobalFloat(name)` (`P:\scripts\3_game\ce\centraleconomy.c:585` and `:592`). Vanilla reads these:

| Global | What reads it | Source |
|---|---|---|
| `FlagRefreshFrequency`, `FlagRefreshMaxDuration` | the territory flag's refresh interval and cap, in seconds (5 and 40 days stock), used only when above 0 | `P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:34` to `:46` |
| `CleanupLifetimeDeadPlayer` | read inside `DeathDropHandEntity`, where it sets the lifetime of the item dropped from the hands, not of the body | `P:\scripts\4_world\entities\dayzplayerimplement.c:608` to `:646` |
| `FoodDecay` | read as a float, and as an integer when the float read returns `float.MIN`, so both `type` values work | `P:\scripts\3_game\dayzgame.c:1164` to `:1170` |
| `WorldWetTempUpdate` | world wetness and temperature updates run only when it is 1 | `dayzgame.c:1162` |
