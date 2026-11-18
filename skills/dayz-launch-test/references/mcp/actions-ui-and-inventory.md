# Actions, UI and inventory: what the verbs can drive

Which player actions, doors, mod UIs and inventory moves can be driven through dayz-mcp, which only start, and the two workarounds for the rest: a key-driven test addon and a mission driver.

The verbs are dayz-mcp's; their behaviour and the measurements here are third-party, taken in game sessions with that tool, and not yet checked on `P:\`. Vanilla facts cite the vanilla file. `MCPBridge.c:NNN` lines are dayz-mcp's own source at the time of the measurement.

## What has no verb

There is no generic player input tool. Opening and closing doors by hand, interactive inventory, shooting, reloading and menus stay manual unless a section below says otherwise. Driving is covered (`vehicle-smoke.md`). For a building, geometry and collision can be verified; doors only as described below. Always list what was not covered in the report's manual test section.

## Continuous actions: `action_use` starts them and does not finish them

Measured 2026-09-07 (a power-grid mod). For an action with a progress bar, `action_use` returns `ok=1, started=1` and the server effect never arrives: `OnFinishProgressServer` (vanilla `P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:289`) does not fire and the target stays in the world (`entities_query` found it at 0.003 m after two attempts with 60 s and 45 s waits). `key_press` is not the way out: by its own description it is not OS input, key-up or hold, and a continuous action needs sustained input. This rules out dismantling, deploying and crafting, which is how a mod usually moves money and persistent objects.

- **What can still be claimed.** The condition is really evaluated, so `started=1` means "valid candidate" and measures that the mod offers the action on that target in that state. Always pair it with a negative control that must come out red (an excluded target returns `condition_failed`), or `started=1` proves nothing.
- **Corollary: no persistent object through MCP.** Deploying from a kit is a continuous action, so there is no way through MCP to create a truly persistent object: `world_spawn` uses default flags and does not survive a restart. Add that `dayz_test_stop` does not shut the server down gracefully (the next boot prints `... was not closed. Always shut down the server gracefully`), and no test of `OnStoreSave` and `OnStoreLoad` across restarts is conclusive through MCP today. If the result is "did not persist", that is the harness, not the mod: do not report it as a bug.

## Doors

- **Without `door_index`, a door does not open** (measured 2026-09-07 on a building mod). `action_use(ActionOpenDoors, classname=<door>)` returns `condition_failed` even with the player 1.4 m away, because the bridge builds the `ActionTarget` with `componentIndex=-1`, and the vanilla `GetDoorIndex(int componentIndex)` resolves the door from the View Geometry component index (`P:\scripts\3_game\entities\building.c:28`; `ActionOpenDoors` calls it with the target's component at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:40`), so -1 resolves no door.
- **`object_anim` cannot hold a door open.** `object_anim(source=<door source>, phase=1.0)` answers `phase=1`, but the engine's door controller returns the door to its wanted phase (a re-read gives `phase=0`) and `IsDoorOpen(index)` (`P:\scripts\3_game\entities\building.c:34`) stays false, so every action that needs an open door also returns `condition_failed`. Without `door_index`, opening, closing, sound and sync were a manual test and MCP could only verify "starts closed" (`object_anim` reads `phase=0`).
- **With `door_index` the action works** (measured 2026-10-01, DayZDiag 1.29.163709, on a test building whose door component is a button on a moving piece): `action_use` with `ActionOpenDoors` or `ActionCloseDoors` and `door_index` does open and close the door even there. `object_anim` (`SetAnimationPhaseNow`) on the door's source still cannot hold a static pose: the door settles at `ajar` with phase 0.07 instead of the requested phase. For the verdict use `object_doors` and rays.

## `setup_failed` is a false negative for instant actions

Measured 2026-09-07 with `ActionTogglePlaceObject` and `ActionDropItemSimple`: the bridge checks `GetRunningAction()==null` right after `PerformActionStart`, and an instant action has already finished by then. The hologram appeared and the object fell to the ground in both cases. Rule: on `setup_failed` for an instant action, verify the effect (a capture, an `entities_query` for the dropped object) before marking the action as failed.

Vanilla side: `PerformActionStart` is at `P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804` and `GetRunningAction` at `P:\scripts\4_world\classes\useractionscomponent\actionmanagerbase.c:91`. `ActionTogglePlaceObject` overrides both `IsLocal()` and `IsInstant()` to true (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiontoggleplaceobject.c:19`). `ActionDropItemSimple` overrides only `IsInstant()` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiondropitemsimple.c:5`) and inherits `UseAcknowledgment()` returning false from `ActionDropItem` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiondropitem.c:74`). The vanilla test that covers both is `(IsLocal() || !UseAcknowledgment()) && IsInstant()` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1064`).

## Opening a mod's UI without a keyboard

The whole chain was verified in game on 2026-08-17 (run `28f2e26f`). The measured recipe, on an ATM device of the a power-grid mod mod with `@DayZ_MCP`; adapt the names to your mod:

1. `dayz_test_run(project="a power-grid mod", mode="all", extra_mods=["@DayZ_MCP"])`, then `wait_for(log_matches, "OnStoreLoad SUCCESS")` (77 s, 26 probes), then `session_acquire_wait(purpose=...)` (it adopts the run: check `adopted_run`), then `wait_for(players_at_least, 1)`. Revised 2026-09-06: the earlier order probed `players_at_least` before adopting; that probe crosses the bridge and the idle-run fence rejects it with `run_not_owned` (`run-lifecycle.md`).
2. `world_spawn(type="LFPG_BTCAtmAdmin", pos=[x,0,z])` about 3 m from the player, then `action_use(action="LFPG_ActionOpenBTCAtm", classname="LFPG_BTCAtmAdmin", radius=5)` returns `started:1` (the lookup by `Type().ToString()` works at runtime).
3. `wait_for(log_matches, "[BTCOpenResponse]", lookback_lines=200)`, with the lookback: the response lands about 200 ms after the trigger, and with a "from now" cursor it is always lost (2 of 2 timeouts with the line already in the log).
4. `ui_tree(path="BTCAtmRoot")`. With an empty path it returns `no_menu` although the UI is open: a Dabs or `ScriptView` panel is a pre-created host, not a `UIScriptedMenu`. Pass the root name of the `.layout`, which is the first `FrameWidgetClass <name>` in the layout file.
5. `ui_set_text("EditBtcAmount", "1")` with an integer (the mod's getter is an int: "0.001" becomes 0 and the panel shows a status with no RPC), then `ui_click("BtnBuyBtc")` returns `clicked:1 handler=LFPG_BTCAtmView user_id=100` (the `#ifdef DabsFramework` branch of the bridge's `InvokeUiClick` fires when another mod loads Dabs), then `wait_for(log_matches, "[BTCTxResult]", lookback_lines=200)` and read `err=`.
6. `session_release`, then `dayz_test_stop`.

Check that the machine is really yours before the first mutation (`run-lifecycle.md`, "A machine that looks free can be taken seconds later").

## Driving a client: three traps

Measured on DayZDiag 1.29.163709 with one client on localhost:

- With the CF, Dabs Framework and VPPAdminTools stack loaded, a mod's `MissionGameplay.OnKeyPress` does not receive the keys sent by `input_trigger`; without that stack it does.
- The client can come up in the pause menu: Escape does not close it, `ui_click` on `continuebtn` does.
- `Print(variable)` prefixes the line with `string name = '...'`, and the client log cuts lines at 255 characters (the server log does not): print short expressions.

## Real inventory moves: what the verbs reach, and a key-driven test addon

Added 2026-10-24, measured on DayZDiag 1.30.164200 (managed runs of project `DayZ_MCP` with a server-side logger as an extra mod, all but the first also with a test-only driver):

- `hands_take` answered `not_reachable` for an item in the cargo of a world container (`WoodenCrate`, `Barrel_Blue`, open, player 1.5 m away) and for an item in the `RB_LvL1_Plank` slot of a `Land_House_1M1` (player 6.5 m and 12.7 m from its origin); other buildings were not tried. It worked for an attachment of an item lying on the ground (`SparkPlug` in a `PowerGenerator`) and for a container on the ground (`WoodenCrate` into the hands).
- `action_use(action="ActionAttach", classname="Land_House_1M1")` with a plank in the hands returned `condition_failed`; on a `PowerGenerator` it attached the spark plug.
- Of the inventory verbs of that build, `inventory_give` and `inventory_attach` create a new item, `hands_take` takes to the hands, and `hands_attach` puts the held item into an attachment slot of a world entity (not tried in these runs). None puts an item from the player into a container's cargo or moves it between two containers.
- What did, in every case tried: a test-only addon whose `modded class MissionGameplay` (inside `#ifndef SERVER`) maps keys in `OnKeyPress` to the client's own inventory calls on objects found with `g_Game.GetObjectsAtPosition` (`P:\scripts\3_game\global\game.c:923`), fired with `key_press` (key codes 63 to 67 for the moves, 68 for the combine, 88 for the half split, 87 for a split to the hands). The calls: `PredictiveTakeEntityToHands` (cargo to hands, building slot to hands; `P:\scripts\3_game\entities\man.c:178`), `PredictiveTakeEntityToTargetCargo` (hands to cargo, crate to crate; `P:\scripts\4_world\entities\manbase\playerbase.c:9072`), `PredictiveTakeEntityToTargetAttachment` (hands to an empty building slot; `P:\scripts\4_world\entities\manbase\playerbase.c:9044`), and the stack calls `CombineItemsClient` (hands onto a stack in a crate or a building slot; `P:\scripts\4_world\entities\itembase.c:786`) and `OnRightClick` (split a stack in half; `P:\scripts\4_world\entities\itembase.c:2059`). Each one reached the server as a real inventory command.
- Read the hands on the server (`weapon_state`): a client-side `no_item_in_hands` from `action_use` is the client's prediction.
- The runs loaded no CF, Dabs or VPP stack (with that stack `OnKeyPress` does not get the keys, see the three traps above). Ship the driver as its own PBO and leave it out of the release.
- `dayz_test_run` starts the server without `-adminlog`: no run left a `.ADM` file in its server profile, so lines written with `AdminLog` (`P:\scripts\3_game\global\game.c:669`) cannot be read from the harness. Have the test build copy them to `Print` and read `script_*.log` (`logs_since`).
- The player keeps what it carried between runs (`verb-gotchas.md`, trap 4). A plank left in the hands by the previous run turned the next take from a slot into a swap.

## Comparing worn items, and getting an infected to attack

Measured in one run (DayZDiag 1.29.163709, in-game checks of the character and clothing import routes):

- **No verb takes a worn item off the player.** A second garment cannot go into an occupied slot, `player_respawn` on a living player does nothing even after `player_godmode(on=false)` (`verb-gotchas.md`), and `player_teleport` to y=160 left the player hanging in the air with no fall. To compare two garments, wear the second on a survivor spawned with `world_spawn(type="SurvivorM_<name>")`: `inventory_attach(object_id=<its id>, dest="attachment", slot=...)` works on it, and it stands facing north. It cannot be given an item to hold (`slot="Hands"` returns `attachment_create_failed`), so read its sides from its facing.
- **An infected attacks only once it notices the player.** One spawned with AI (`flags=8391716`, the living-infected value 3108 plus `ECE_NOPERSISTENCY_WORLD`) behind a player standing still walked away. Spawned 2.4 m in front of the player, it attacked after a short `player_move` (jog, 1.2 s): wind-up and swings, again and again. Godmode does not hide the player from AI: in the diag build `m_CanBeTargetedDebug` starts true (`P:\scripts\4_world\entities\manbase\playerbase.c:408`).
- **In this run, infected spawned without AI did not stay healthy.** With `flags=8389668` three of them idled in place, but about 12 minutes later one custom and one vanilla `ZmbM_SoldierNormal` read `health01 = 0` in `telemetry_read(mode="object_at")` and lay on the ground, and the third read 0.75. No log line explains it and the cause was not found; it is one observation with no AI against no-AI control. Capture static infected early, and read their health again before a late capture.

## A mission driver for logic that has no verb

When the test needs mod APIs that no MCP verb reaches, put an Enforce Script driver in the `init.c` of the test mission instead of using `exec_enforce`. Use a mission kept with the mod's own test files (for example `<Mod>_dev\_server\mpmissions\<mission>\`) and boot the test server on it instead of the template mission; the launch side of this pattern belongs to the `dayz-launch-test` skill. `/dayz-gate behavior` injects a driver of the same kind (`AZ_BehaviorTest`) into a copy of the instance's mission; for its five built-in actions use the gate. The pattern validated with dayz-mcp runs:

1. A server-only driver class, started with `CallLater` at 250 ms.
2. A file protocol that is written once per sequence number: `$profile:<case>\cmd_<seq>.json` in, `res_<seq>.json` out, read and written with `JsonFileLoader`. Never rewrite a `seq`.
3. One boot per run: the sequence lives in memory and resets to 1 on restart. Between runs, archive the whole directory with a rename; do not move its contents with a wildcard.
4. Print a `MARK` line in the script log to delimit each window. Every failure of an operation is serialized inside its `res_<seq>.json`; the driver's poll loop does not die from a failed case.
5. Mission scripts see the classes of every loaded mod and compile on the server with `#ifdef SERVER` visible. The host runner only writes commands, reads results and cuts the log between marks.
6. Archive the case directory on completion, always and not only between runs, and never run a command that already has its `res_<seq>.json`. Measured failure (2026-09-27, a power-grid mod; DayZ 1.30.164014 Experimental): a driver whose sequence reset to 1 on a stale `cmd_1.json` re-ran a mounting command every 1.5 s or so; half an hour later the world held thousands of duplicate objects and the user aborted the next session for performance. The log lines dismissed as harness noise were the signal: a repeated `OP seq=1` means the command is running again, and duplicated live device ids mean two entities share one id. Before filing a repeated line or an `ERR` line as noise, write in one sentence what it would mean if it were true; if that sentence describes damage, it is signal.
