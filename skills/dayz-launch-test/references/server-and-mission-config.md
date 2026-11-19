# Server and mission configuration

What the stock DayZ 1.30 dedicated server ships, which keys and files it reads, and which script reads each one.

The mission files were read from the DayZ Server install and the script lines from the vanilla scripts on `P:\scripts\`. `MISSION` below is `mpmissions/dayzOffline.chernarusplus/` of that install. The stock Chernarus, Livonia and Sakhal `cfggameplay.json`, `cfgeffectarea.json` and `cfgweather.xml` are also unpacked as the fallback copies under `P:\DZ\worlds\<world>\ce\`, and the `MISSION` line numbers match those copies where checked:

- `"disableColdAreaBuildingCheck": true` is on `P:\DZ\worlds\chernarusplus\ce\cfggameplay.json:76`.
- `"SafePositions":[` is on `P:\DZ\worlds\chernarusplus\ce\cfgeffectarea.json:167`.
- `<weather reset="0" enable="0">` is on `P:\DZ\worlds\chernarusplus\ce\cfgweather.xml:5`.

The Nasdara files, `serverDZ.cfg` and `db/messages.xml` are not on `P:\` and are not checked there. The Central Economy files (`db/*.xml`, `cfgeconomycore.xml`, `cfgspawnabletypes.xml` and the rest) are in `skills/_shared/persistence/central-economy-files.md`; ports and the test tree layout are in `linux-native-server.md`.

## Missions shipped

`mpmissions/` holds `dayzOffline.chernarusplus`, `dayzOffline.enoch` (Livonia), `dayzOffline.sakhal` and `dayzOffline.nasdara`. The mission to load is `template` inside `class Missions { class DayZ { ... }; };` at the end of `serverDZ.cfg`, written `<mission>.<terrain>`.

The Chernarus mission folder holds:

| File | Role |
|---|---|
| `init.c` | The mission script: `main()` creates the Hive and sets the date, and `CustomMission` sets up new characters. |
| `db/types.xml`, `db/events.xml`, `db/globals.xml`, `db/economy.xml`, `db/messages.xml` | Economy data and server messages. |
| `cfgeconomycore.xml`, `cfglimitsdefinition.xml`, `cfglimitsdefinitionuser.xml`, `cfgspawnabletypes.xml`, `cfgrandompresets.xml`, `cfgignorelist.xml`, `cfgeventspawns.xml`, `cfgeventgroups.xml` | Central Economy setup. |
| `cfggameplay.json` | Gameplay overrides (below). |
| `cfgeffectarea.json` | Static contaminated areas (below). |
| `cfgundergroundtriggers.json` | Underground darkness triggers (`skills/_shared/world/underground-triggers.md`). |
| `cfgenvironment.xml` and `env/*_territories.xml` | Animal and infected territories. |
| `cfgweather.xml` | Weather override, shipped with `enable="0"`, so it is off by default (line 5). |
| `cfgplayerspawnpoints.xml` | Fresh spawn positions. |
| `areaflags.map`, `mapgroup*.xml`, `mapcluster*.xml` | Loot positions on the map. |

Nasdara adds `cfgbunkerbroadcast.json` and `cfgexternallocks.json`; Sakhal adds `build.xml`, `config.cpp` and `pra/`.

## `serverDZ.cfg`

The shipped `serverDZ.cfg` documents each key in a comment. Steam installs it once and never updates it (the depot marks it `UserConfig`), so an old install keeps its first copy after every game update. Newer copies add two keys, `description` (before `enableWhitelist`) and `shardId` (after `vonCodecQuality`), so line numbers depend on when the server was installed: find a key by name. Older and newer copies carry the same other keys and comments; owners change some values.

Keys beyond the ones the test skills already set:

| Key (stock value) | Meaning, from the stock comment |
|---|---|
| `verifySignatures = 2` | Checks PBOs against `.bisign`; "only 2 is supported". |
| `forceSameBuild = 1` | Only clients with the server's exe revision may join. |
| `disableVoN = 0`, `vonCodecQuality = 20` | Voice on or off; codec quality 0 to 30. |
| `disable3rdPerson = 0`, `disableCrosshair = 0` | View and crosshair switches. |
| `disablePersonalLight = 1`, `lightingConfig = 0` | Personal light off; 0 brighter or 1 darker nights. |
| `serverTime = "SystemTime"` | Start time: the machine's clock, or `"YYYY/MM/DD/HH/MM"`. |
| `serverTimeAcceleration = 12` | In-game time multiplier, 0 to 24. |
| `serverNightTimeAcceleration = 1` | Extra multiplier for the night, 0.1 to 64, on top of `serverTimeAcceleration`. |
| `serverTimePersistent = 0` | Save the time to storage and resume from it. |
| `guaranteedUpdates = 1` | Network protocol; "use only number 1". |
| `loginQueueConcurrentPlayers = 5`, `loginQueueMaxPlayers = 500` | Players processed at once during login; queue length. |
| `instanceId = 1` | Server instance number; names the storage folder. |
| `storageAutoFix = 1` | Replace corrupted persistence files with empty ones. |

Keys the scripts read with `ServerConfigGetInt`, which work even though the stock file does not list them all:

| Key | Effect | Source |
|---|---|---|
| `enableCfgGameplayFile` | Unless non-zero (read into a `bool`), a dedicated server ignores `cfggameplay.json`. | `P:\scripts\3_game\cfggameplayhandler.c:53` |
| `disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`, `disablePersonalLight`, `lightingConfig` | The defaults that apply when `cfggameplay.json` is not used. | `P:\scripts\3_game\cfggameplaydatajson.c:47` to `:50`, `:79`, `:176` |
| `adminLogPlayerHitsOnly`, `adminLogPlacement`, `adminLogBuildActions`, `adminLogPlayerList` | Filters for the admin log. | `P:\scripts\4_world\plugins\pluginbase\pluginadminlog.c:44` to `:47` |
| `enableDebugMonitor` | Turns on the debug monitor. | `P:\scripts\5_mission\mission\missionserver.c:164` |

## `cfggameplay.json`

`CfgGameplayHandler.LoadData` reads `$mission:cfggameplay.json`, or `dz/worlds/<world>/ce/cfggameplay.json` when the mission has none, and only when `enableCfgGameplayFile` is set; a diag build that is not a dedicated server forces it on (`P:\scripts\3_game\cfggameplayhandler.c:3`, `:44` to `:60`). Otherwise, or when neither file exists, every `ITEM_*` class runs its `InitServer`, which sets its defaults, some from the `serverDZ.cfg` keys above (`:29` to `:35`, `:62` to `:68`). The whole object is sent to each client on connect (`CfgGameplayJson`, `P:\scripts\3_game\cfggameplaydatajson.c:2`; `cfggameplayhandler.c:94` to `:98`, called for `ClientPrepareEventTypeID` at `P:\scripts\5_mission\mission\missionserver.c:320`).

The members of the four stock files use the field names of `CfgGameplayJson` and its `ITEM_*` classes (`cfggameplaydatajson.c:15` to `:23`, the classes at `:43` to `:459`), with one exception. Chernarus and Livonia carry `disableColdAreaBuildingCheck` (`P:\DZ\worlds\chernarusplus\ce\cfggameplay.json:76`; `P:\DZ\worlds\enoch\ce\cfggameplay.json:76`), which names no field. The field is `disableColdAreaPlacementCheck` (`cfggameplaydatajson.c:252`, read at `cfggameplayhandler.c:367` to `:369`), the name the Sakhal and Nasdara files use. What the loader does with a member that names no field is untested.

When the file fails to parse, `LoadData` reports the loader's message with `ErrorEx` and carries on (`cfggameplayhandler.c:70` to `:72`). Every `ITEM_*` section whose `ValidateServer()` then fails goes back to its defaults through `InitServer`, with `Validation failed during loading of 'cfggameplay.json' for <Section>` in the RPT (`:14` to `:26`), so a bad value can silently undo a whole section: search the RPT for that line after you edit the file. Once loaded, `OnLoaded` calls `OnGameplayDataHandlerLoad()` on the mission and on `DayZGame` (`:81` to `:85`); the hook is empty on `Mission` (`P:\scripts\3_game\gameplay.c:718`) and `MissionServer` overrides it (`missionserver.c:161`), so a `modded class MissionServer` that overrides it and calls `super` is the place to act on the loaded values. A client gets its copy through `RPC_CFG_GAMEPLAY_SYNC`, which replaces its `m_Data` in `OnRPC` (`cfggameplayhandler.c:102` to `:114`, dispatched at `P:\scripts\3_game\dayzgame.c:3159` to `:3163`). By reading of the code, not tested in game: client code that reads a `CfgGameplayHandler` getter before that RPC arrives reads a `CfgGameplayJson` that was never filled.

Stock sections of `MISSION/cfggameplay.json` (`version` is 123):

| Section (lines) | Contents |
|---|---|
| `GeneralData` (3 to 9) | `disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`, `disableRespawnInUnconsciousness`. |
| `PlayerData` (10 to 53) | `disablePersonalLight`; `StaminaData` (`staminaMax` 100, `staminaMinCap` 5, `staminaWeightLimitThreshold` 6000, `staminaKgToStaminaPercentPenalty` 1.75, `sprintStaminaModifierErc` and `sprintStaminaModifierCro`, and the swimming, ladder, melee, obstacle and hold-breath modifiers at 1.0); `ShockHandlingData` (`shockRefillSpeedConscious` 5, `shockRefillSpeedUnconscious` 1, `allowRefillSpeedModifier`); `MovementData`; `DrowningData`; `WeaponObstructionData` (`staticMode`, `dynamicMode`). |
| `WorldsData` (54 to 61, note the plural) | `lightingConfig`, `objectSpawnersArr`, `environmentMinTemps` and `environmentMaxTemps` (twelve monthly values), `wetnessWeightModifiers`. |
| `BaseBuildingData` (62 to 88) | `HologramData` with the switches `disableIsCollidingBBoxCheck`, `disableIsCollidingPlayerCheck`, `disableIsClippingRoofCheck`, `disableIsBaseViableCheck`, `disableIsCollidingGPlotCheck`, `disableIsCollidingAngleCheck`, `disableIsPlacementPermittedCheck`, `disableHeightPlacementCheck`, `disableIsUnderwaterCheck`, `disableIsInTerrainCheck`, `disableColdAreaBuildingCheck` (see above), and `disallowedTypesInUnderground`; `ConstructionData` with `disablePerformRoofCheck`, `disableIsCollidingCheck`, `disableDistanceCheck`, `disableItemFalling`, `disableDropAttachmentsOnFall`, `disableRefundMaterialsOnFall`. |
| `UIData` (89 to 103) | `use3DMap`; `HitIndicationData` (`hitDirectionOverrideEnabled`, behaviour, style, colour, duration, break point, scatter, `hitIndicationPostProcessEnabled`). |
| `MapData` (104 to 110) | `ignoreMapOwnership`, `ignoreNavItemsOwnership`, `displayPlayerPosition`, `displayNavInfo`. |
| `VehicleData` (111 to 118) | `boatDecayMultiplier` and the wheel detach and damage switches. |

Script also knows `ExternalLockData` and `SandstormData` (`cfggameplaydatajson.c:22` and `:23`), which the Chernarus file does not carry and the Nasdara file does (`skills/_shared/world/README.md`).

## `cfgeffectarea.json`

`EffectAreaLoader` reads it (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarealoader.c:2`; the file keeps the old `ContaminatedAreaLoader` name) from `$mission:cfgeffectarea.json`, with the same `dz/worlds/<world>/ce/` fallback (`:4`, `:18`). The top level has two arrays (`P:\scripts\4_world\classes\contaminatedarea\jsondatacontaminatedarea.c:2` to `:6`):

- `Areas`: one object per zone with `AreaName`, `Type` (the entity class, for example `ContaminatedArea_Static`), `TriggerType` (for example `ContaminatedTrigger`), `Data` and `PlayerData`.
- `SafePositions`: `[x, z]` pairs (`MISSION/cfgeffectarea.json:167`).

`Data` holds `Pos`, `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`, `OuterPartDist`, `OuterOffset`, `VerticalLayers`, `VerticalOffset`, `ParticleName`, `EffectInterval`, `EffectDuration` and `EffectModifier`; `PlayerData` holds `AroundPartName`, `TinyPartName` and `PPERequesterType` (`jsondatacontaminatedarea.c:17` to `:41`). A `Radius` of 0 or less is rejected with an error naming the area (`contaminatedarealoader.c:46` to `:50`). Chernarus ships nine `ContaminatedArea_Static` zones.

## `db/messages.xml`

Each `<message>` has child elements, not attributes:

| Element | Meaning |
|---|---|
| `<text>` | The message; may use `#name` for the server name and `#tmin` for the minutes left. |
| `<delay>` | Minutes after connect. |
| `<repeat>` | Minutes between repeats. |
| `<onconnect>1</onconnect>` | Start counting at the player's connect. |
| `<deadline>` | Minutes until the end. |
| `<shutdown>1</shutdown>` | Shut the server down at the deadline, with a countdown message. |

The stock file holds only commented examples (`MISSION/db/messages.xml:3` to `:45`).

## Logs in the profile folder

With `-profiles=<dir>` the server writes `DayZServer_<date>_<time>.RPT` (engine), `script_<date>_<time>.log` and `error_<date>_<time>.log`. With `-adminlog` it also writes `DayZServer_<date>_<time>.ADM`, which opens with an `AdminLog started on <date> at <time>` header; without the switch no `.ADM` appears. Both were measured on the native Linux server; the rest of this page was read from the files, not measured.

## Windows launch parameters and BattlEye

Reported launch behaviour, not checked on `P:\`: the parameters live in the engine, not in the scripts.

- Core switches: `-config=`, `-port=` (2302, UDP), `-profiles=`, `-mission=` (absolute), `-mod=` (client and server, `;`-separated, absolute paths) and `-serverMod=` (server only). Set `steamQueryPort` in `serverDZ.cfg` (2305 in the stock comment) when the server does not show in the browser; do not rely on "game port plus one".
- `-par=<file>` reads the parameters from a file, one per line, a way round the Windows 8192-character command line limit when many absolute mod paths stack up. It is not in the official parameter list and is untested here: try a `.par` file before you rely on it.
- Logging and diagnosis: `-doLogs`, `-adminLog`, `-netLog`, `-freezeCheck`, `-filePatching`, `-cpuCount=` (at most the logical cores) and `-limitFPS=` (at most 200). `priority.txt` in the server folder lists Steam IDs, separated by `;`, that skip the login queue.
- BattlEye reads `BEServer_x64.cfg` next to `BEServer_x64.dll`; `-bePath` moves that folder, and `RConPassword` and `RestrictRCon 1` go in the cfg. Measured on the retail Windows DayZServer 1.30 with `-profiles=` and no `-bePath`: the server used `<profiles>\BattlEye\`, wrote no `beserver_x64_active_*.cfg` copy, and took `RConPort` from that cfg on every start (it listened on 27332 after the value changed from 27331 between two runs).

## The diag menu

Opened with Win+Alt in `DayZDiag_x64`; Ctrl+Win also works but clashes with Windows 11 shortcuts. Its categories include Statistics (the script profiler, which `-profile` forces on), the Enfusion renderer and world, DayZ render, Game (weather, free camera, vehicles, combat, and Central Economy debug: loot spawn editing, force save, dynamic events), AI (navmesh and path graph) and Sounds. Do not rely on a `-debugweather` launch parameter; it is unconfirmed. Reported from use, not checked on `P:\`; the profiler calls are in `test-loop.md`.
