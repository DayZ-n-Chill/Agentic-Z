# Vehicle verbs on DayZ 1.30

How dayz-mcp's vehicle verbs behave on DayZ 1.30 when you test a car with them: gearboxes, fuel readings, seating, removing parts, deleting a car, and reading what a run loaded. The driving workflow itself is in `vehicle-smoke.md` and `vehicle-acceptance.md`.

Measured in game with the third-party dayz-mcp server and its `@DayZ_MCP` mod on DayZ 1.30 (Experimental and stable installs), porting two 1.29 quad bikes. None of it is vanilla behaviour, so it is not checked on `P:\`; the vanilla lines it leans on are cited.

## Driving and conditioning a car

- `vehicle_control` does not shift an automatic gearbox. The bridge changes gear only when `GearboxGetType()` is manual (in `@DayZ_MCP`'s `MCP_CarScript.c`), so an automatic car stays in neutral with the throttle open. To drive one, test a copy of the build whose `Gearbox.type` is `GEARBOX_MANUAL` with every other entry byte identical, and say so in the verdict.
- `vehicle_prepare_fixture` can answer `fixture_not_ready` with `fuel_fraction=0.0` right after `OnDebugSpawn()`, although `OnDebugSpawn()` fills the tank: the bridge reads the tank in the same tick as the `Fill()`. Seen in four runs on two machines; `telemetry_read object_at` then read `fuel_fraction=1` and the car started and drove. Read `telemetry_read` before calling it a failure.
- `entities_query` returns the config class as `type` and the script class as `classname`. A mod wheel with no script class of its own reads `CarWheel`; its `_Ruined` twin, which has one, reads its own name. That is a cheap check that a mod's script class binds.
- In-vehicle actions need `vehicle_get_in_client` as well as `vehicle_enter`. After `vehicle_enter` alone, `action_use ActionSwitchLights` (target `self`) answered `condition_failed`; after `vehicle_get_in_client` it started and the lights came on.
- The client stays bound to the first car it got into. After `ActionGetOutTransport`, `vehicle_enter` into a second car seated the server player, and the light switch failed there twice. Plan one car per run.
- `vehicle_enter` with its default 15 second timeout answered `timeout` with the player already seated (`query_player_state` showed it); with `timeout_s=30` it answered in 1.3 seconds.

## Parts, health and lights

- No verb sets an item's health, so health level transitions such as the 1.30 ruined wheel swap cannot be driven. An RGD5 dropped unpinned 1.5 m from a loose wheel took it only to 0.971. A grenade unpinned in the hands (`action_use ActionUnpin`, target `hands`) arms only when it leaves them (`EEItemLocationChanged`, `P:\scripts\4_world\entities\itembase\grenade_base.c:273` to `:281`); `ActionDropItem` with target `hands` drops it.
- Parts that `OnDebugSpawn` mounts are not world objects: `object_resolve` on a mounted `HeadlightH7` gave `object_not_found` at 0.3 and 3 m. To remove a part during a test, mount it with `inventory_attach`, keep its `item_object_id` and `object_delete` that id; the detach path then runs (the headlights went from the two bulb to the one bulb state in game).
- No bridge reader shows the light state: `vehicle_telemetry` and `telemetry_read` have no light field. Log it from the mod under `#ifdef DIAG_DEVELOPER` (for example in `OnDriverExit`) or compare captures.

## Cameras

With the player seated, `camera_set` failed with `camera_unmoved_cabin`, yet the next capture showed the requested outside view and carried the warning `camera_unverified`: the camera had moved. That is how the driver's pose can be checked from outside. The camera stays mounted until `restore_gameplay`.

## Deleting a car

- Deleting a car with a player in a crew seat brings the game down on the first 1.30 patch. `ObjectDelete` on an occupied car crashed the server, and on the client the vanilla `CarHud.RefreshVehicleHud` hit a NULL in `CarScript.EngineGetRPM` (`P:\scripts\5_mission\gui\vehicles\carhud.c:104`) until the client stopped polling. LBmaster's admin tool (LBAdmin) works around the same bug. Current dayz-mcp ejects every occupant, on every crew position, before `ObjectDelete` in `object_delete`, `scene_clear` and the loadout cleanup, and answers `vehicle_eject_failed` without deleting when a seat cannot be emptied; with it the server survived. Eject first, then delete, in any tool or test you write.
- The server only sees its own crew. A player seated with `vehicle_get_in_client` alone sits in the car on the client but not in the server's crew, so the eject finds nobody, the car goes, and the client's `HumanCommandVehicle` points at a deleted car: a native `ACCESS_VIOLATION` on the client. dayz-mcp now reads the client's seat telemetry before deleting a car (not tested in game). When the client reports the player seated, `object_delete` refuses with `vehicle_client_seated`, `deleted=0`. When the seat cannot be verified (an unreadable status in embedded mode, an absent or stale client, unreadable telemetry, and live mode with admin), it refuses with `vehicle_seat_unverified`, `deleted=0`. Treat both as a refusal, not a passing error: get the player out on the client, then retry.

## What a run loaded

- In current dayz-mcp, `clean=true` changes only a build that was asked for (`effective_build = build` in its `dayz_test_request.py`); `clean=true` alone no longer rebuilds the bridge PBO. Older versions of the `dayz-test-v1` launcher rebuilt it from `default_source` whenever `clean=true`, even with `build=false`. Either way, hash the live server and client PBOs with SHA-256 after launch and at the end of the run.
- On a Windows machine where `Get-CimInstance Win32_Process` answers access denied, a provenance check that reads command lines through WMI fails before any test step runs. Measure without WMI: `Get-Process` for the DayZDiag processes, and the command line DayZ writes at the top of each RPT for the `-mod=` and `-serverMod=` lists.
- `wait_for(log_matches, role=server, lookback_from=launch)` once returned the client's `Module: World` line and listed only `_client` files in `scanned`. Check `scanned.files`, or the defines of the returned line (`SERVER`), before taking it for the server's.
- With another machine's DayZ server holding port 2302, `dayz_test_run` answered `port_in_use_foreign` with a hint to pass another `port=`; with `port=2402` it answered `active_run_exists` and only queued until that server exited (`../managed-launcher.md`, "The machine is busy, not the port").
