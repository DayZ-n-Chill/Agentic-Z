# Server and mission configuration on DayZ 1.30

What the stock dedicated server ships and which script reads it. Everything here was read from the
DayZ Server install of 1.30.164289 (Steam app 223350, build 26220720; the binary reports `1.30.164289.70`
in its RPT) and from the vanilla scripts extracted from the 1.30.164289 client, except `serverDZ.cfg`, which
Steam does not update (section 2). `MISSION` below is `mpmissions/dayzOffline.chernarusplus/` of that install.
Script citations use the vanilla scripts unpacked on `P:\scripts\` and were re-opened there for this file. The
stock Chernarus, Livonia and Sakhal `cfggameplay.json`, `cfgeffectarea.json` and `cfgweather.xml` are also unpacked
as the fallback copies under `P:\DZ\worlds\<world>\ce\`, and the line numbers given for `MISSION/` files match those
copies where checked (`P:\DZ\worlds\chernarusplus\ce\cfggameplay.json:76`,
`P:\DZ\worlds\chernarusplus\ce\cfgeffectarea.json:167`, `P:\DZ\worlds\chernarusplus\ce\cfgweather.xml:5`). The
Nasdara files, `serverDZ.cfg` and `db/messages.xml` are not unpacked on `P:\` and are not yet checked on `P:\`. The Central Economy files (`db/*.xml`,
`cfgeconomycore.xml`, `cfgspawnabletypes.xml`, ...) are in the dayz-persistence skill (`references/central-economy-files.md`).
Ports and the test-tree layout are in `linux-native-server.md`.

## 1. Missions shipped

`mpmissions/` holds `dayzOffline.chernarusplus`, `dayzOffline.enoch` (Livonia), `dayzOffline.sakhal` and
`dayzOffline.nasdara`. The mission to load is `template` inside `class Missions { class DayZ { ... }; };` at the
end of `serverDZ.cfg`, in the form `<mission>.<terrain>`.

A mission folder (Chernarus) contains:

| File | Role |
|---|---|
| `init.c` | the mission script: `main()` creates the Hive and sets the date, and `CustomMission` sets up new characters |
| `db/types.xml`, `db/events.xml`, `db/globals.xml`, `db/economy.xml`, `db/messages.xml` | economy data and server messages |
| `cfgeconomycore.xml`, `cfglimitsdefinition.xml`, `cfglimitsdefinitionuser.xml`, `cfgspawnabletypes.xml`, `cfgrandompresets.xml`, `cfgignorelist.xml`, `cfgeventspawns.xml`, `cfgeventgroups.xml` | Central Economy setup |
| `cfggameplay.json` | gameplay overrides (section 3) |
| `cfgeffectarea.json` | static contaminated areas (section 4) |
| `cfgundergroundtriggers.json` | underground darkness triggers (the dayz-underground skill) |
| `cfgenvironment.xml` + `env/*_territories.xml` | animal and infected territories |
| `cfgweather.xml` | weather override; shipped with `enable="0"`, so the file is off by default (line 5) |
| `cfgplayerspawnpoints.xml` | fresh-spawn positions |
| `areaflags.map`, `mapgroup*.xml`, `mapcluster*.xml` | loot positions of the map |

Nasdara adds `cfgbunkerbroadcast.json` and `cfgexternallocks.json`; Sakhal adds `build.xml`, `config.cpp`
and `pra/`.

## 2. `serverDZ.cfg` keys in the stock file

The shipped `serverDZ.cfg` documents each key in a comment. Steam
installs it once and does not update it (the depot marks the file `UserConfig`): a Windows install updated to build
26220720 on 2026-11-10 still holds its copy of 2024-07-31 (2987 bytes), while the depot of build 26220720 holds a
3200-byte file whose content was not checked. Newer copies add two keys, `description` (before `enableWhitelist`)
and `shardId` (after `vonCodecQuality`), so line numbers depend on when the server was installed: find a key by
name. The keys, stock values and comments below are those of the 2024 copy; three newer copies checked, all with
`description` and `shardId`, carry the same keys and comments, with some values changed by their owners. Beyond the
keys the test skills already set:

| Key (stock value) | Meaning, from the stock comment |
|---|---|
| `verifySignatures = 2` | checks PBOs against `.bisign`; "only 2 is supported" |
| `forceSameBuild = 1` | only clients with the server's exe revision may join |
| `disableVoN = 0`, `vonCodecQuality = 20` | voice on/off; codec quality 0-30 |
| `disable3rdPerson = 0`, `disableCrosshair = 0` | view and crosshair toggles |
| `disablePersonalLight = 1`, `lightingConfig = 0` | personal light off; 0 brighter / 1 darker nights |
| `serverTime = "SystemTime"` | start time: the machine's clock, or `"YYYY/MM/DD/HH/MM"` |
| `serverTimeAcceleration = 12` | in-game time multiplier, 0-24 |
| `serverNightTimeAcceleration = 1` | extra multiplier for the night, 0.1-64, applied on top of `serverTimeAcceleration` |
| `serverTimePersistent = 0` | save the time to storage and resume from it |
| `guaranteedUpdates = 1` | network protocol; "use only number 1" |
| `loginQueueConcurrentPlayers = 5`, `loginQueueMaxPlayers = 500` | players processed at once during login; queue length |
| `instanceId = 1` | server instance number; names the storage folder |
| `storageAutoFix = 1` | replace corrupted persistence files with empty ones |

Keys the scripts read with `ServerConfigGetInt` (so they work even
though the stock file does not list all of them):

- `enableCfgGameplayFile`: unless it is set to a non-zero value (it is read into a `bool`,
  `P:\scripts\3_game\cfggameplayhandler.c:53`), a dedicated server ignores `cfggameplay.json` (section 3).
- `disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`, `disablePersonalLight`, `lightingConfig`:
  the defaults that apply when `cfggameplay.json` is not used (`P:\scripts\3_game\cfggameplaydatajson.c:47-50`,
  `:79`, `:176`).
- `adminLogPlayerHitsOnly`, `adminLogPlacement`, `adminLogBuildActions`, `adminLogPlayerList`: filters for the
  admin log (`P:\scripts\4_world\plugins\pluginbase\pluginadminlog.c:44-47`).
- `enableDebugMonitor` (`P:\scripts\5_mission\mission\missionserver.c:164`).

## 3. `cfggameplay.json`

`CfgGameplayHandler.LoadData` reads `$mission:cfggameplay.json`, or
`dz/worlds/<world>/ce/cfggameplay.json` when the mission has none, and only when `enableCfgGameplayFile` is set in
`serverDZ.cfg`; a diag build that is not a dedicated server forces it on (`P:\scripts\3_game\cfggameplayhandler.c:3`,
`:44-60`). Otherwise, or when neither file exists, every `ITEM_*` class runs its `InitServer`, which sets its
defaults, some of them from the section-2 keys (`:29-35`, `:62-68`). The whole object is sent to each client on
connect (`CfgGameplayJson`, `P:\scripts\3_game\cfggameplaydatajson.c:2`; `CfgGameplayHandler.c:94-98`, called for
`ClientPrepareEventTypeID` at `P:\scripts\5_mission\mission\missionserver.c:320`). The members of the four stock files
carry the names of the fields of `CfgGameplayJson` and its `ITEM_*` classes (`CfgGameplayDataJson.c:15-23`, the
classes at `:43-459`), with one exception: Chernarus and Livonia carry `disableColdAreaBuildingCheck` (line 76 in
both), which names no field. The field is `disableColdAreaPlacementCheck` (`CfgGameplayDataJson.c:252`, read at
`CfgGameplayHandler.c:367-369`), the name the Sakhal and Nasdara files use. What the loader does with a member that
names no field was not tested.

Stock sections (`MISSION/cfggameplay.json`; `version` is 123):

- `GeneralData` (lines 3-9): `disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`,
  `disableRespawnInUnconsciousness`.
- `PlayerData` (10-53): `disablePersonalLight`; `StaminaData` (`staminaMax` 100, `staminaMinCap` 5,
  `staminaWeightLimitThreshold` 6000, `staminaKgToStaminaPercentPenalty` 1.75, `sprintStaminaModifierErc/Cro`
  and the swimming, ladder, melee, obstacle and hold-breath modifiers at 1.0); `ShockHandlingData`
  (`shockRefillSpeedConscious` 5, `shockRefillSpeedUnconscious` 1, `allowRefillSpeedModifier`);
  `MovementData`; `DrowningData`; `WeaponObstructionData` (`staticMode`, `dynamicMode`).
- `WorldsData` (54-61, note the plural): `lightingConfig`, `objectSpawnersArr`, `environmentMinTemps` /
  `environmentMaxTemps` (twelve monthly values), `wetnessWeightModifiers`.
- `BaseBuildingData` (62-88): `HologramData` with the `disable...Check` switches (`disableIsCollidingBBoxCheck`,
  `disableIsCollidingPlayerCheck`, `disableIsClippingRoofCheck`, `disableIsBaseViableCheck`,
  `disableIsCollidingGPlotCheck`, `disableIsCollidingAngleCheck`, `disableIsPlacementPermittedCheck`,
  `disableHeightPlacementCheck`, `disableIsUnderwaterCheck`, `disableIsInTerrainCheck`,
  `disableColdAreaBuildingCheck`, see above) and `disallowedTypesInUnderground`; `ConstructionData` with
  `disablePerformRoofCheck`, `disableIsCollidingCheck`, `disableDistanceCheck`, `disableItemFalling`,
  `disableDropAttachmentsOnFall`, `disableRefundMaterialsOnFall`.
- `UIData` (89-103): `use3DMap`, `HitIndicationData` (`hitDirectionOverrideEnabled`, behaviour, style, colour,
  duration, break point, scatter, `hitIndicationPostProcessEnabled`).
- `MapData` (104-110): `ignoreMapOwnership`, `ignoreNavItemsOwnership`, `displayPlayerPosition`,
  `displayNavInfo`.
- `VehicleData` (111-118): `boatDecayMultiplier` and the wheel detach/damage switches.

The script also knows `ExternalLockData` and `SandstormData` (`CfgGameplayDataJson.c:22-23`), which the Chernarus
file does not carry and the Nasdara file does (`skills/dayz-mod-workflow/references/dayz-1-30-mod-workflow.md`).

## 4. `cfgeffectarea.json`

Read by `EffectAreaLoader` (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarealoader.c:2`; the file name keeps the old `ContaminatedAreaLoader` name) from `$mission:cfgeffectarea.json`, with the same `dz/worlds/<world>/ce/`
fallback (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarealoader.c:4`, `:18`). The top level has two
arrays (`P:\scripts\4_world\classes\contaminatedarea\jsondatacontaminatedarea.c:2-6`):

- `Areas`: one object per zone with `AreaName`, `Type` (the entity class, e.g. `ContaminatedArea_Static`),
  `TriggerType` (e.g. `ContaminatedTrigger`), `Data` and `PlayerData`.
- `SafePositions`: `[x, z]` pairs (`MISSION/cfgeffectarea.json:167`).

`Data` holds `Pos`, `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`,
`OuterPartDist`, `OuterOffset`, `VerticalLayers`, `VerticalOffset`, `ParticleName`, `EffectInterval`,
`EffectDuration`, `EffectModifier`; `PlayerData` holds `AroundPartName`, `TinyPartName`, `PPERequesterType`
(`jsondatacontaminatedarea.c:17-41`). A `Radius` of 0 or less is rejected with an error naming the area
(`contaminatedarealoader.c:46-50`). Chernarus ships nine `ContaminatedArea_Static` zones.

## 5. `db/messages.xml`

Each `<message>` has child elements, not attributes: `<text>` (may use `#name` for the server name and `#tmin`
for the minutes left), `<delay>` (minutes after connect), `<repeat>` (minutes between repeats),
`<onconnect>1</onconnect>` (start counting at the player's connect), `<deadline>` (minutes until the end) and
`<shutdown>1</shutdown>` (shut the server down at the deadline, with a countdown message). The stock file holds
only commented examples (`MISSION/db/messages.xml:3-45`).

## 6. Logs in the profile folder

With `-profiles=<dir>` the server writes `DayZServer_<date>_<time>.RPT` (engine), `script_<date>_<time>.log`
and `error_<date>_<time>.log`. With `-adminlog` it also writes `DayZServer_<date>_<time>.ADM`, which starts with
an `AdminLog started on <date> at <time>` header; without the switch no `.ADM` file appears (both measured at runtime on the
native Linux server, 1.30.164289, 2026-11-13). The rest of this page was read from the 164289 source (paths cited inline), not measured at runtime.
