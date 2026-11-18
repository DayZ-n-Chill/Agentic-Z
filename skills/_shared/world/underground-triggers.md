# Underground triggers (DayZ 1.30)

The boxes that make a place dark and quiet underground: the full schema of `cfgundergroundtriggers.json`, how the file is loaded and sent to clients, the trigger types, how a trigger is tied to an object, the in-game trigger editor, and an untested recipe for a mod bunker. Checked on `P:\` (DayZ 1.30) except the parts marked as design or untested. What the trigger does to the player's state is in `underground-presence.md`; the generic trigger volume API under it is in `_shared/physics/scripted-triggers.md`.

The mission file belongs to dayz-server-admin; a script class that spawns triggers belongs to dayz-script-specialist.

## Schema of `cfgundergroundtriggers.json`

The root is `{ "Triggers": [ ... ] }` (`JsonUndergroundTriggers`, `P:\scripts\3_game\undergroundarealoader.c:1` to `:3`). Each trigger is a `JsonUndergroundAreaTriggerData` (`P:\scripts\3_game\undergroundarealoader.c:69` to `:85`):

| Field | Type | Purpose |
|---|---|---|
| `Comment` | string | Free note. |
| `CustomSpawn` | bool | Not spawned at boot; created by a parent object (see "Triggers tied to an object"). |
| `Tag` | string | Link to an Object Spawner entry or a manual spawn. |
| `ParentNetworkId` | int[2] | Link to a map object by its network id. |
| `Position`, `Orientation`, `Size` | float[3] | The trigger box. |
| `EyeAccommodation` | float | Eye adaptation. `1.0` with no breadcrumbs gives the `OUTER` type. |
| `InterpolationSpeed` | float | Transition speed. |
| `UseLinePointFade` | bool | Simple fade between the breadcrumb points. |
| `AmbientSoundType` | string | Ambient type for the sound controller. |
| `AmbientSoundSet` | string | Ambient sound played directly. Livonia uses `Underground_SoundSet`. |
| `Breadcrumbs` | array | Transition points. Any breadcrumb makes the type `TRANSITIONING`; the limit is 32. |

Each breadcrumb is a `JsonUndergroundAreaBreadcrumb` (`P:\scripts\3_game\undergroundarealoader.c:36` to `:51`): `Position` (float[3]), `EyeAccommodation` (float), `UseRaycast` (bool), `Radius` (float; Livonia uses `-1`), `LightLerp` (bool, only with `UseLinePointFade`), `Comment`, and `ExternalValueController` with a `Type` and `Params` (`undergroundarealoader.c:53` to `:57`). One controller type is `BreadcrumbDoorStateController`, which takes the selection name of a door (`undergroundarealoader.c:59` to `:67`).

## Trigger type

Decided in `P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:100` to `:118`:

- with breadcrumbs, `TRANSITIONING` (more than 32 raises an error, `undergroundtrigger.c:102` to `:104`);
- without them, `EyeAccommodation == 1.0` gives `OUTER`;
- any other value gives `INNER`.

The player's presence follows from the type in `TranslateTriggerTypeToPresence` (`undergroundtrigger.c:190`).

## Loading and synchronization

1. **File.** `UndergroundAreaLoader.GetData` first looks for `$mission:cfgundergroundtriggers.json`. If it is missing it writes a warning to the RPT and tries `dz/worlds/<world>/ce/cfgundergroundtriggers.json` (`P:\scripts\3_game\undergroundarealoader.c:105` to `:125`).
2. **Startup.** The server creates one `UndergroundTriggerCarrier` per trigger that has no `CustomSpawn` (`SpawnAllTriggerCarriers`, `undergroundarealoader.c:135` to `:154`, called at `P:\scripts\5_mission\mission\missionserver.c:91`).
3. **Synchronization.** When a player connects, the server sends the whole JSON with `RPC_UNDERGROUND_SYNC` (`SyncDataSend`, `undergroundarealoader.c:174` to `:177`, called at `P:\scripts\5_mission\mission\missionserver.c:342` and `:363`) and the client stores it (`OnRPC`, `undergroundarealoader.c:181` to `:193`). A custom mission JSON works without the client having the file.
4. **Local play.** In a local game on a `DIAG_DEVELOPER` build, the client loads the file and creates the triggers itself (`P:\scripts\5_mission\mission\missiongameplay.c:112` to `:117`).

Limit: `m_TriggerIndex` is synchronized in the range -1 to 4095 (`P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:10`), so one JSON holds up to 4096 triggers. The 1.29 range was -1 to 255 (not on `P:\`).

## Triggers tied to an object

Two ways, both with `CustomSpawn` set to true:

- **A map object.** `ParentNetworkId` holds the object's network id, and the object itself calls `JsonUndergroundTriggers.SpawnParentedTriggers(this)` (`P:\scripts\3_game\undergroundarealoader.c:5` to `:22`). `Land_WarheadStorage_Main` does it (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_main.c:72`) and so does `Land_WarheadStorage_Bunker_Facility` (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_bunker_facility.c:16`).
- **An object placed by Object Spawner.**
  - The spawner entry is an `ITEM_SpawnerObject` with `name`, `pos`, `ypr`, `scale`, `enableCEPersistency` and `customString` (`P:\scripts\3_game\objectspawner.c:100` to `:108`). It carries `"customString": "undergroundTriggerTag=TAG"`.
  - The spawner calls `object.OnSpawnByObjectSpawner(item)` (`P:\scripts\3_game\objectspawner.c:63`).
  - The class walks the `CustomSpawn` triggers and creates those whose `Tag` matches (`OnSpawnByObjectSpawner`, `P:\scripts\4_world\entities\building\underground\land_warheadstorage_bunker_facility.c:62` to `:94`). `customString` takes several pairs separated by `;`.
  - That logic is written in the two Sakhal classes, not in a shared base class, so a mod class has to write it again.

Not verified: whether `Position` of a parented trigger is a world position or relative to the parent. The code creates the carrier at `data.GetPosition()` and then calls `SetParent(parent)` (`SpawnTriggerCarrier`, `undergroundarealoader.c:24` to `:33`); how that changes the position was not measured.

## The in-game trigger editor (new in 1.30)

- Opened with `LCTRL+/` (`KC_SLASH`, `P:\scripts\4_world\plugins\pluginbase\pluginkeybinding.c:55`); `F` focuses the selected object (`pluginkeybinding.c:56`).
- It exists only in the diag build (`P:\scripts\4_world\plugins\pluginbase\pluginundergroundtriggermanager.c:1` is `#ifdef DIAG_DEVELOPER`), and `EditorToggle` returns at once in multiplayer (`pluginundergroundtriggermanager.c:358` to `:360`). Use it in a local diag game rather than editing trigger boxes blind.
- A double click creates a trigger (`Event_OnDoubleClick`, `pluginundergroundtriggermanager.c:305`); boxes and breadcrumbs can be edited.
- It overwrites `$mission:cfgundergroundtriggers.json` (`pluginundergroundtriggermanager.c:821`), then calls `OnExport` (`:830`), which copies the new file to `cfgundergroundtriggers.json.backup-<date>` (`pluginundergroundtriggermanager.c:922` to `:923`). The backup holds the file just written, so the earlier version is lost unless you copy it by hand before exporting.

## Recipe (design, untested): a mod bunker placed with Object Spawner

It follows the vanilla Sakhal pattern.

1. **Trigger in the mission JSON**, with `"CustomSpawn": true`, a unique `Tag` and the interior box. For a dark zone with no transition: no breadcrumbs and an `EyeAccommodation` other than `1`, which gives `INNER`.
2. **Object Spawner entry** with `"customString": "undergroundTriggerTag=<Tag>"`.
3. **The bunker's script class.** Override `OnSpawnByObjectSpawner(ITEM_SpawnerObject item)` with the same loop as `land_warheadstorage_bunker_facility.c:62` to `:94`, calling `JsonUndergroundTriggers.SpawnTriggerCarrier(this, index, triggerData)`.
4. **Hole.** If the bunker opens to the terrain it also needs a hole (`terrain-holes.md`).

A mod cannot ship its own trigger file without touching the loader: `GetData` reads one file. A `modded class UndergroundAreaLoader` that adds the mod's triggers to `m_JsonData` before `SyncDataSend` is the obvious route; it was not tested.
