# Actions, UI and inventory through dayz-mcp

Which player actions, doors, mod UIs and inventory moves dayz-mcp's verbs can drive, which they only start, and the two ways round the rest: a key driven test addon and a mission driver.

The verbs and their behaviour are dayz-mcp's, measured in game sessions with that tool on DayZDiag 1.29 and 1.30, and not checked on `P:\`. Vanilla facts cite the vanilla file. `MCPBridge.c` is a file of dayz-mcp's `@DayZ_MCP` mod.

## What has no verb

There is no generic player input tool. Opening and closing doors by hand, interactive inventory, shooting, reloading and menus stay manual unless a section below says otherwise. Driving is covered (`vehicle-smoke.md`). For a building, geometry and collision can be checked; doors only as described below. List what was not covered in the report's manual test section.

## Continuous actions start and never finish

For an action with a progress bar, `action_use` returns `ok=1, started=1` and the server effect never arrives: `OnFinishProgressServer` (`P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:289`) does not fire and the target stays in the world (`entities_query` found it at 0.003 m after waits of 60 and 45 seconds, on a power grid mod). `key_press` is no way out: by its own description it is not OS input, key up or hold, and a continuous action needs held input. That rules out dismantling, deploying and crafting, which is how a mod usually moves money and persistent objects.

- What you can still claim: the condition really is evaluated, so `started=1` means "valid candidate" and shows the mod offers the action on that target in that state. Always pair it with a negative control that must come out red (an excluded target returns `condition_failed`), or `started=1` proves nothing.
- No persistent object through dayz-mcp. Deploying from a kit is a continuous action, and `world_spawn` uses default flags that do not survive a restart. Add that `dayz_test_stop` does not shut the server down gracefully (the next boot prints `... was not closed. Always shut down the server gracefully`), and no test of `OnStoreSave` and `OnStoreLoad` across restarts is conclusive through dayz-mcp. "Did not persist" is the test setup, not the mod; never report it as a bug.

## Doors

- Without `door_index`, a door does not open. `action_use(ActionOpenDoors, classname=<door>)` returns `condition_failed` even with the player 1.4 m away, because the bridge builds the `ActionTarget` with `componentIndex=-1`, and the vanilla `GetDoorIndex(int componentIndex)` resolves the door from the View Geometry component index (`P:\scripts\3_game\entities\building.c:28`; `ActionOpenDoors` passes the target's component at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:40`), so -1 resolves no door.
- `object_anim` cannot hold a door open. `object_anim(source=<door source>, phase=1.0)` answers `phase=1`, but the engine's door controller returns the door to its wanted phase (a re-read gives `phase=0`) and `IsDoorOpen(index)` (`building.c:34`) stays false, so every action that needs an open door returns `condition_failed` too. Without `door_index`, opening, closing, sound and sync are a manual test and dayz-mcp can only confirm "starts closed".
- With `door_index` the action works, even on a test building whose door component is a button on a moving piece: `action_use` with `ActionOpenDoors` or `ActionCloseDoors` and `door_index` opens and closes the door. `object_anim` (`SetAnimationPhaseNow`) on the door's source still cannot hold a pose: the door settles `ajar` at phase 0.07 instead of the requested phase. For the verdict use `object_doors` and rays.

## `setup_failed` on an instant action

With `ActionTogglePlaceObject` and `ActionDropItemSimple`, the bridge checks `GetRunningAction()==null` right after `PerformActionStart`, and an instant action has already finished by then. In both cases the hologram appeared and the object fell to the ground. On `setup_failed` for an instant action, check the effect (a capture, an `entities_query` for the dropped object) before marking it failed.

Vanilla side: `PerformActionStart` is at `P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804` and `GetRunningAction` at `P:\scripts\4_world\classes\useractionscomponent\actionmanagerbase.c:91`. `ActionTogglePlaceObject` overrides both `IsLocal()` and `IsInstant()` to true (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiontoggleplaceobject.c:19` and `:24`). `ActionDropItemSimple` overrides only `IsInstant()` (`actiondropitemsimple.c:5`) and inherits `UseAcknowledgment()` returning false from `ActionDropItem` (`actiondropitem.c:74`). The vanilla test that covers both is `(IsLocal() || !UseAcknowledgment()) && IsInstant()` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1064`).

## Opening a mod's UI without a keyboard

The whole chain was confirmed in game on an ATM device of a power grid mod with `@DayZ_MCP`. Change the names for your mod:

1. `dayz_test_run(project="<Project>", mode="all", extra_mods=["@DayZ_MCP"])`, then `wait_for(log_matches, "OnStoreLoad SUCCESS")` (77 seconds, 26 probes), then `session_acquire_wait(purpose=...)` to adopt the run (check `adopted_run`), then `wait_for(players_at_least, 1)`. Adopt before probing `players_at_least`: that probe crosses the bridge, and the idle run fence refuses it with `run_not_owned` (`run-lifecycle.md`).
2. `world_spawn(type="<MyMod_Device>", pos=[x,0,z])` about 3 m from the player, then `action_use(action="<MyMod_ActionOpenDevice>", classname="<MyMod_Device>", radius=5)` returns `started:1` (the lookup by `Type().ToString()` works at run time).
3. `wait_for(log_matches, "<response marker>", lookback_lines=200)`, with the lookback: the response lands about 200 ms after the trigger, and with a "from now" cursor it is always lost (2 of 2 timeouts with the line already in the log).
4. `ui_tree(path="<RootWidget>")`. With an empty path it returns `no_menu` although the UI is open: a Dabs Framework or `ScriptView` panel is a host created up front, not a `UIScriptedMenu`. Pass the root name of the `.layout`, the first `FrameWidgetClass <name>` in the layout file.
5. `ui_set_text("<EditBox>", "1")` with an integer (the mod's getter was an int, so `"0.001"` became 0 and the panel showed a status with no RPC), then `ui_click("<Button>")` returns `clicked:1 handler=<ViewClass> user_id=100` (the bridge's `InvokeUiClick` takes its `#ifdef DabsFramework` branch when another mod loads Dabs), then `wait_for(log_matches, "<result marker>", lookback_lines=200)` and read the result.
6. `session_release`, then `dayz_test_stop`.

Check that the machine is really yours before the first change (`run-lifecycle.md`, "A machine that looks free can be taken seconds later").

## Driving a client: three traps

Measured on DayZDiag 1.29 with one client on localhost:

- With the Community Framework, Dabs Framework and VPPAdminTools stack loaded, a mod's `MissionGameplay.OnKeyPress` does not get the keys sent by `input_trigger`; without that stack it does.
- The client can come up in the pause menu. Escape does not close it; `ui_click` on `continuebtn` does.
- `Print(variable)` prefixes the line with `string name = '...'`, and the client log cuts lines at 255 characters (the server log does not): print short expressions.

## Real inventory moves

Measured in game on DayZ 1.30, in managed runs with a server side logger as an extra mod and, in all but the first, a test only driver:

- `hands_take` answered `not_reachable` for an item in the cargo of a world container (`WoodenCrate`, `Barrel_Blue`, open, player 1.5 m away) and for an item in the `RB_LvL1_Plank` slot of a `Land_House_1M1` (player 6.5 m and 12.7 m from its origin); other buildings were not tried. It worked for an attachment of an item lying on the ground (`SparkPlug` in a `PowerGenerator`) and for a container on the ground (`WoodenCrate` into the hands).
- `action_use(action="ActionAttach", classname="Land_House_1M1")` with a plank in the hands returned `condition_failed`; on a `PowerGenerator` it attached the spark plug.
- Of that build's inventory verbs, `inventory_give` and `inventory_attach` create a new item, `hands_take` takes to the hands, and `hands_attach` puts the held item into an attachment slot of a world entity (not tried here). None moves an item from the player into a container's cargo or between two containers.
- What worked every time: a test only addon whose `modded class MissionGameplay` (inside `#ifndef SERVER`) maps keys in `OnKeyPress` to the client's own inventory calls on objects found with `g_Game.GetObjectsAtPosition` (`P:\scripts\3_game\global\game.c:923`), fired with `key_press` (key codes 63 to 67 for the moves, 68 for the combine, 88 for the half split, 87 for a split to the hands). The calls: `PredictiveTakeEntityToHands` (cargo to hands, building slot to hands; `P:\scripts\3_game\entities\man.c:178`), `PredictiveTakeEntityToTargetCargo` (hands to cargo, crate to crate; `P:\scripts\4_world\entities\manbase\playerbase.c:9072`), `PredictiveTakeEntityToTargetAttachment` (hands to an empty building slot; `playerbase.c:9044`), and the stack calls `CombineItemsClient` (hands onto a stack in a crate or a building slot; `P:\scripts\4_world\entities\itembase.c:786`) and `OnRightClick` (split a stack in half; `itembase.c:2059`). Each reached the server as a real inventory command.
- Read the hands on the server (`weapon_state`): a client side `no_item_in_hands` from `action_use` is only the client's prediction.
- Those runs loaded no Community Framework, Dabs or VPP stack (with it `OnKeyPress` does not get the keys, see above). Ship the driver as its own PBO and keep it out of the release.
- `dayz_test_run` starts the server without `-adminlog`, so no run leaves a `.ADM` file in its server profile and lines written with `AdminLog` (`game.c:669`) cannot be read. Have the test build copy them to `Print` and read `script_*.log` (`logs_since`).
- The player keeps what it carried between runs (`verb-gotchas.md`, trap 4). A plank left in the hands by the previous run turned the next take from a slot into a swap.

## Comparing worn items, and getting an infected to attack

Measured in one run on DayZDiag 1.29, checking character and clothing imports:

- No verb takes a worn item off the player. A second garment cannot go into a taken slot, `player_respawn` on a living player does nothing even after `player_godmode(on=false)` (`verb-gotchas.md`), and `player_teleport` to y=160 left the player hanging in the air with no fall. To compare two garments, put the second on a survivor spawned with `world_spawn(type="SurvivorM_<name>")`: `inventory_attach(object_id=<its id>, dest="attachment", slot=...)` works on it, and it stands facing north. It cannot hold an item (`slot="Hands"` returns `attachment_create_failed`), so read its sides from its facing.
- An infected attacks only once it notices the player. One spawned with AI (`flags=8391716`, the living infected value 3108 plus `ECE_NOPERSISTENCY_WORLD` = 8388608, `P:\scripts\3_game\ce\centraleconomy.c:31`) behind a still player walked away. Spawned 2.4 m in front of the player, it attacked after a short `player_move` (jog, 1.2 seconds), wind-up and swings, again and again. Godmode does not hide the player from AI: in the diag build `m_CanBeTargetedDebug` starts true under `#ifdef DIAG_DEVELOPER` (`P:\scripts\4_world\entities\manbase\playerbase.c:408`).
- Infected spawned without AI did not stay healthy in that run. With `flags=8389668` three idled in place, but about 12 minutes later one custom and one vanilla `ZmbM_SoldierNormal` read `health01 = 0` in `telemetry_read(mode="object_at")` and lay on the ground, and the third read 0.75. No log line explains it; it is one observation with no control. Capture static infected early, and read their health again before a late capture.

## A mission driver for logic that has no verb

When a test needs mod APIs no verb reaches, put an Enforce Script driver in the test mission's `init.c` instead of using `exec_enforce`. Use a mission kept with the mod's own test files (for example `<Mod>_dev\_server\mpmissions\<mission>\`) and boot the test server on it instead of the template mission; starting it belongs to `/dayz-launch-test`. `/dayz-gate behavior` injects a driver of the same kind (`AZ_BehaviorTest`) into a copy of the instance's mission; for its five built in actions use the gate. The pattern that worked with dayz-mcp runs:

1. A server only driver class, started with `CallLater` at 250 ms.
2. A file protocol written once per sequence number: `$profile:<case>\cmd_<seq>.json` in, `res_<seq>.json` out, read and written with `JsonFileLoader`. Never rewrite a `seq`.
3. One boot per run: the sequence lives in memory and resets to 1 on restart. Between runs, archive the whole folder with a rename; do not move its contents with a wildcard.
4. A `MARK` line in the script log marks each window. Every failed operation is written into its `res_<seq>.json`; the driver's poll loop does not die on a failed case.
5. Mission scripts see the classes of every loaded mod and compile on the server with `#ifdef SERVER` visible. The host runner only writes commands, reads results and cuts the log between marks.
6. Archive the case folder when a run finishes, always, not only between runs, and never run a command that already has its `res_<seq>.json`. A driver whose sequence reset to 1 on a stale `cmd_1.json` re-ran a mounting command about every 1.5 seconds on DayZ 1.30 Experimental; half an hour later the world held thousands of duplicate objects and the user aborted the next session for performance. The lines dismissed as test noise were the signal: a repeated `OP seq=1` means the command is running again, and duplicated live device ids mean two entities share one id. Before filing a repeated line or an `ERR` line as noise, write in one sentence what it would mean if true; if that sentence describes damage, it is signal.
