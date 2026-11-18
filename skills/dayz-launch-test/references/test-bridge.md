# The in-game test bridge

How agents drive a running DayZ Diag session with nobody at the keyboard: spawn objects and items, teleport the player, get into a car and drive it while reading speed and state, cast rays and read surfaces, set the camera and take screenshots, set the time and weather, and read the logs since a mark. What each command rests on, what was measured, and what the bridge cannot do.

Vanilla facts cite the file on `P:\`; every engine call the mod makes is pinned to its `P:\scripts` line in `.claude/mcp/dayz-testbridge/test_vanilla_calls.py`. The "Measured" section was measured on DayZ 1.30.164289 Diag on Windows, vanilla Chernarus, on 2026-11-18.

## The two halves

| Half | Where | Job |
|---|---|---|
| `AZ_TestBridge` mod | `../assets/testbridge-mod/src/AZ_TestBridge/` | Reads commands in each peer's profile folder, runs them from a fixed `switch`, writes results. Classes are prefixed `AZB_`. |
| `dayz-testbridge` MCP server | `.claude/mcp/dayz-testbridge/` | Starts and stops the session, checks every command against `allowlist.py`, writes it, waits for the result, captures the client window, reads the logs. Its `README.md` lists the tools. |

`launch.py --test-bridge <token>` puts `P:\Mods\@AZ_TestBridge` last on `-mod=` for both peers and adds `-azBridge=<token>`. `/dayz-gate ingame --test-bridge` uses the same option to check that both peers answer.

## How the two talk

Files, one folder per peer and session: `<profile>/AZTestBridge/<token>/`, where the server's profile is `.server/<instance>-bridge/Profiles/` and the client's is `.server/!ClientDiagLogs/`. No network port is opened, and the host addresses each peer directly.

- **Token.** 32 lowercase hex characters, new for every session, read by the mod with `CommandlineGetParam` (`P:\scripts\3_game\global\game.c:661`). No token: the mod does nothing. Files of another token are never read.
- **Hello.** Each peer writes `hello.json` once ready: the server on its first update, the client when its player is loaded. `session_start` waits for both, then closes the pause menu the client opens when its window is not active.
- **Commands.** The host writes `cmd/<seq>.json` as `<seq>.tmp` and renames it. The peer reads only the next number it expects with `FileExist` and never lists the folder, so the `FindFile` bug on 1.30 (`dayz-1-30-server-measured.md`) cannot touch it. The host always writes every `AZB_Args` field, defaults filled.
- **Results.** The peer writes `res/<seq>.json` with `JsonFileLoader.SaveFile` (`P:\scripts\3_game\tools\jsonfileloader.c:42`), then deletes the command. The host counts "command gone and result readable" as done.
- **One use per number.** The host refuses a number that already has a file or is out of order. The peer never runs a command whose result exists, so a restarted peer cannot re-run old commands (the stale `cmd_1.json` trap in `actions-doors-and-inventory.md`).
- **Polling.** Server from `MissionServer.OnUpdate` (`P:\scripts\5_mission\mission\missionserver.c:108`), client from `MissionGameplay.OnUpdate` (`missiongameplay.c:287`), every 0.1 s. A long command (spawn, teleport, get in, drive) keeps its state between ticks.
- **Closing.** `session_stop` renames each token folder to `<token>.done`.

## Which peer runs what

- **Server:** world state and what the server owns: spawn, delete, teleport, time, weather, car setup, rays, surfaces, player state. Car setup runs here because `OnDebugSpawn` does nothing on a client (`vehicle-in-game-facts.md`).
- **Client:** what the local player owns and the camera. Getting in and out uses the real actions, so the server mirrors the crew (`test-cell-vehicles.md`). Driving runs on the driver's client, which owns the car (`OnVehicleSeatDriverEnter` calls `Possess`, `P:\scripts\4_world\entities\manbase\playerbase.c:4561` to `:4576`): an override of `CarScript.OnInput` (`P:\scripts\4_world\entities\vehicles\carscript.c:1041`) sets throttle, steering and brake after `super`.
- **Host:** screenshots (`PrintWindow`, because `MakeScreenshot`, `P:\scripts\1_core\proto\proto.c:142`, writes no file on diag), logs and the session.

`list_commands` returns every command with its peer, arguments, bounds and outputs. Positions are `[x, y_up, z]`; a `y` above 2000 is refused as a swapped triplet. Objects are named by network id written `low,high` from `GetNetworkID` (`P:\scripts\3_game\entities\object.c:819`) and found with `GetObjectByNetworkId` (`game.c:356`).

## Answers that are not errors

`ok: false` with one of these codes is the game's answer; anything the tool raises is the tool's own fault.

| Code | Meaning |
|---|---|
| `unknown_command`, `bad_json`, `seq_mismatch`, `wrong_token` | The peer refused the file and ran nothing. |
| `no_player`, `more_than_one_player` | Player commands need exactly one player on the server. |
| `not_found`, `not_a_car`, `still_there` | The network id names nothing, not a car, or the object survived its delete. |
| `spawn_failed` (with `reason`), `spawn_gone` | No such class or no free place; the spawn vanished before it was read back. |
| `vehicle_has_crew` | Delete refused: deleting a car with crew crashed 1.30 (`vehicle-in-game-facts.md`). |
| `already_in_vehicle`, `no_seat_component`, `not_seated` (with `reason`) | Get-in refused or never seated after three tries. `reason` gives the action manager's gate, the action's condition, the door and the reach. |
| `not_in_vehicle`, `still_seated` | Get-out refused or never finished. |
| `not_driver`, `car_gone` | Drive needs the local player in the driver seat. |

## Measured

- A Hatchback_02 spawned at the north-west airfield bench with 8389668 came back with 4 of 4 wheels present and a full tank after `vehicle_prepare`, was entered on the first try, and drove 13.2 m in 5 s at full throttle with a top speed of 28 km/h; the gear read 1 (neutral) in the first sample and 2 (first) after it (`CarGear`, `P:\scripts\3_game\vehicles\car.c:32` to `:45`). View and bullet rays straight down hit the car; a ray 8 m beside it hit terrain.
- `JsonFileLoader.SaveFile` writes `bool` fields as `0` and `1`, not `true` and `false`.
- Vanilla `GetNetworkIDString` joins high and low with no separator (`object.c:821` to `:826`), so `0,23198` and `023198` read alike; the bridge writes `low,high` itself.
- The client's get-in condition measures from the target's `GetCursorHitPos`, not from the car (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursornoruincheck.c:38` to `:43`): a target with a zero cursor position is refused. The bridge aims at the seat's `CrewEntryWS` point.
- A Hatchback_02 driver only gets through an open door (`CrewCanGetThrough`, `P:\scripts\4_world\entities\vehicles\inheritedcars\hatchback_02.c:218` to `:226`). `vehicle_prepare` opens the driver door with `SetAnimationPhase`, as the vanilla door action does on the server (`actioncardoorsoutside.c:104`); pass `open_driver_door: false` to keep it shut.
- `EngineStart` in the same tick as `OnDebugSpawn` left the engine off: `OnBeforeEngineStart` (`carscript.c:1713`) wants the battery and spark plug that `OnDebugSpawn` is still attaching. A tick later it starts.
- A `staticcamera` set right after getting out of a car lost the view to the player's own camera; the client now re-activates the scripted camera every frame, and hides the HUD every frame while asked to, since vanilla shows it again.
- `wind: 0` read back as 0.005 of the maximum: the weather does not land exactly on zero.
- A car's doors, trunk and radiator are objects of their own, so a ray can hit them and not the car. Each `raycast` hit carries `parent_net_id`, the object the part hangs on. Level view rays from 3.5 m out at 0.4, 0.8 and 1.2 m above the ground hit a prepared Hatchback_02 or a part of it 9 times in 12; before `vehicle_prepare` fitted its doors, 6 times.

## Safety

Diag only (every script inside `#ifdef DIAG_DEVELOPER`); off without the token; only a session the tool started (it refuses next to any other `DayZDiag_x64.exe`, and stops only the process ids it recorded); a storage-free `<instance>-bridge` copy, so your world and characters are never touched; at most 50 spawns, 200 m search radius, 60 s of driving; spawn flags must include `ECE_NOPERSISTENCY_WORLD`; no command evaluates script, touches files or calls a method by name; `/dayz-release-pack` refuses any release that names `AZ_TestBridge` or an `AZB_` class.

## Not in v1

- Continuous actions and anything that needs held input or key presses (`actions-doors-and-inventory.md`).
- Doors of buildings, and inventory moves by hand.
- Automatic gearboxes are left to the engine: the drive shifts only manual boxes, and an automatic car that stays in neutral under scripted throttle (`vehicle-in-game-facts.md`) is not handled.
- Linux: `PrintWindow` and the launch path are Windows only.

## The smoke test

`python scripts/dev/testbridge_smoke.py` runs the plan's twelve steps on vanilla Chernarus (session, time and weather, teleport, spawn and prepare a car, get in, drive, get out with rays and a surface read, an overhead camera and screenshot, camera back, delete, logs since a mark, stop) and four negative controls that must come back refused (an unknown command, an invented class, the wrong token, a drive on foot). Its report and the run's `-mod=` line go to `output/in-game-test-tool/smoke-<time>.json`.
