# Underground triggers

Covers the boxes that make a place dark and quiet underground: every field of `cfgundergroundtriggers.json`, how the file is loaded and sent to clients, the trigger types, tying a trigger to an object, the in-game trigger editor, and a mod bunker built the vanilla way. What a trigger does to the player's state is in `underground-presence.md`; the general trigger volume API is in `_shared/physics/scripted-triggers.md`.

The mission file belongs to dayz-server-admin; a script class that spawns triggers belongs to dayz-script-specialist.

## Fields of `cfgundergroundtriggers.json`

The root is `{ "Triggers": [ ... ] }` (`JsonUndergroundTriggers`, `P:\scripts\3_game\undergroundarealoader.c:1` to `:3`). Each trigger is a `JsonUndergroundAreaTriggerData` (`undergroundarealoader.c:69` to `:85`):

| Field | Type | Purpose |
|---|---|---|
| `Comment` | string | Free note. |
| `CustomSpawn` | bool | Not spawned at boot; a parent object creates it (see "Triggers tied to an object"). |
| `Tag` | string | Link to an Object Spawner entry or a manual spawn. |
| `ParentNetworkId` | int[2] | Link to a map object by its network id. |
| `Position`, `Orientation`, `Size` | float[3] | The trigger box. |
| `EyeAccommodation` | float | Eye adaptation. `1.0` with no breadcrumbs gives the `OUTER` type. |
| `InterpolationSpeed` | float | Transition speed. |
| `UseLinePointFade` | bool | Simple fade between the breadcrumb points. |
| `AmbientSoundType` | string | Ambient type for the sound controller. The vanilla files use `caveSmall` and `caveBig` (Sakhal and Nasdara). |
| `AmbientSoundSet` | string | Ambient sound played directly. Livonia uses `Underground_SoundSet`; Nasdara uses `ambient_Irrigation_Tunnel_loop_SoundSet` and `ambient_Bunker_loop_SoundSet`. |
| `Breadcrumbs` | array | Transition points. Any breadcrumb makes the type `TRANSITIONING`; the limit is 32. |

Each breadcrumb is a `JsonUndergroundAreaBreadcrumb` (`undergroundarealoader.c:36` to `:51`): `Position` (float[3]), `EyeAccommodation` (float), `UseRaycast` (bool), `Radius` (float; Livonia uses `-1`), `LightLerp` (bool, only with `UseLinePointFade`), `Comment`, and `ExternalValueController` with a `Type` and `Params` (`:53` to `:57`). One controller type is `BreadcrumbDoorStateController`, which takes the selection name of a door (`:59` to `:67`).

## Trigger types

The type is decided in `P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:100` to `:118`:

- with breadcrumbs, `TRANSITIONING`; more than 32 raises an error (`undergroundtrigger.c:102` to `:104`);
- without them, `EyeAccommodation == 1.0` gives `OUTER`;
- any other value gives `INNER`.

`TranslateTriggerTypeToPresence` turns the type into the player's presence (`undergroundtrigger.c:190`).

## Loading and sync

1. File: `UndergroundAreaLoader.GetData` looks for `$mission:cfgundergroundtriggers.json` first. When it is missing it writes a warning to the RPT and tries `dz/worlds/<world>/ce/cfgundergroundtriggers.json` (`P:\scripts\3_game\undergroundarealoader.c:105` to `:125`).
2. Startup: the server creates one `UndergroundTriggerCarrier` per trigger without `CustomSpawn` (`SpawnAllTriggerCarriers`, `undergroundarealoader.c:135` to `:154`, called at `P:\scripts\5_mission\mission\missionserver.c:91`).
3. Sync: when a player connects, the server sends the whole JSON with `RPC_UNDERGROUND_SYNC` (`SyncDataSend`, `undergroundarealoader.c:174` to `:177`, called at `missionserver.c:342` and `:363`), and the client stores it (`OnRPC`, `undergroundarealoader.c:181` to `:193`). A custom mission JSON works without the client having the file.
4. Local play: in a local game on a `DIAG_DEVELOPER` build, the client loads the file and creates the triggers itself (`P:\scripts\5_mission\mission\missiongameplay.c:112` to `:117`).

`m_TriggerIndex` syncs in the range -1 to 4095 (`P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:10`), so one JSON holds up to 4096 triggers. In 1.29 the range was -1 to 255 (not checked on `P:\`). The vanilla files hold 8 triggers on Livonia, 30 on Sakhal and 1,076 on Nasdara, none on Chernarus (`P:\DZ\worlds\<world>\ce\cfgundergroundtriggers.json`); Nasdara alone is past the old limit.

The carrier exists on the server and on clients; the box that tests the player, `UndergroundTrigger`, is spawned locally on the client when the carrier enters the player's network bubble (`P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:1` and `:2`). A server check cannot ask the trigger whether a player is inside; it reads the presence the client reports (`underground-presence.md`).

## Triggers tied to an object

Both ways set `CustomSpawn` to true.

- A map object: `ParentNetworkId` holds the object's network id, and the object calls `JsonUndergroundTriggers.SpawnParentedTriggers(this)` itself (`P:\scripts\3_game\undergroundarealoader.c:5` to `:22`). `Land_WarheadStorage_Main` does this (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_main.c:72`), and so does `Land_WarheadStorage_Bunker_Facility` (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_bunker_facility.c:16`).
- An object placed by Object Spawner:
  - The spawner entry is an `ITEM_SpawnerObject` with `name`, `pos`, `ypr`, `scale`, `enableCEPersistency` and `customString` (`P:\scripts\3_game\objectspawner.c:100` to `:108`). It carries `"customString": "undergroundTriggerTag=TAG"`.
  - The spawner calls `object.OnSpawnByObjectSpawner(item)` (`objectspawner.c:63`).
  - The class walks the `CustomSpawn` triggers and creates those whose `Tag` matches (`OnSpawnByObjectSpawner`, `land_warheadstorage_bunker_facility.c:62` to `:94`). `customString` takes several pairs separated by `;`.
  - That logic is copied into both warhead storage classes (`land_warheadstorage_main.c:183` to `:215` has the same loop), not in a shared base class, so a mod class writes it again.
  - `GetData` reads the JSON file from disk on every call (`P:\scripts\3_game\undergroundarealoader.c:109` to `:133`), and both ways call it once per spawned object, so keep the number of parented objects small.

Of the vanilla files on `P:\`, only Sakhal uses `CustomSpawn`: 4 of its 30 triggers, all tied by `ParentNetworkId` (`P:\DZ\worlds\sakhal\ce\cfgundergroundtriggers.json`). No vanilla file uses `Tag`, so the Object Spawner route has no vanilla data example.

Unverified: whether `Position` of a parented trigger is a world position or relative to the parent. The code creates the carrier at `data.GetPosition()` and then calls `SetParent(parent)` (`SpawnTriggerCarrier`, `undergroundarealoader.c:24` to `:33`), but how that moves the box has not been measured.

## The in-game trigger editor

- Open it with `LCTRL+/` (`KC_SLASH`, `P:\scripts\4_world\plugins\pluginbase\pluginkeybinding.c:55`); `F` focuses the selected object (`pluginkeybinding.c:56`).
- It exists only in the diag build (`P:\scripts\4_world\plugins\pluginbase\pluginundergroundtriggermanager.c:1` is `#ifdef DIAG_DEVELOPER`), and `EditorToggle` returns at once in multiplayer (`pluginundergroundtriggermanager.c:358` to `:360`). Use it in a local diag game rather than editing trigger boxes blind.
- A double click creates a trigger (`Event_OnDoubleClick`, `:305`); boxes and breadcrumbs can be edited.
- Export overwrites `$mission:cfgundergroundtriggers.json` (`:821`), then `OnExport` (`:830`) copies the new file to `cfgundergroundtriggers.json.backup-<date>` (`:922` and `:923`). The backup holds the file just written, so copy the earlier version by hand before you export or it is lost.

## A mod bunker placed with Object Spawner

This follows the vanilla Sakhal pattern, but no mod class has been tested with it, so it is unverified until a diag session shows the bunker going dark.

1. Trigger in the mission JSON with `"CustomSpawn": true`, a unique `Tag` and the interior box. For a dark zone with no transition, leave out breadcrumbs and set an `EyeAccommodation` other than `1`, which gives `INNER`.
2. Object Spawner entry with `"customString": "undergroundTriggerTag=<Tag>"`.
3. The bunker's script class overrides `OnSpawnByObjectSpawner(ITEM_SpawnerObject item)` with the same loop as `land_warheadstorage_bunker_facility.c:62` to `:94`, calling `JsonUndergroundTriggers.SpawnTriggerCarrier(this, index, triggerData)`.
4. If the bunker opens to the terrain it also needs a hole (`terrain-holes.md`).

A mod cannot ship its own trigger file without touching the loader, because `GetData` reads one file. A `modded class UndergroundAreaLoader` that adds the mod's triggers to `m_JsonData` before `SyncDataSend` is the likely route; it is unverified.
