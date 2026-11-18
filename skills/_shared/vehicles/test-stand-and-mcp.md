# Automated vehicle test stand

The limits of driving, seating and unseating a vehicle from an automated test bridge, and which actions the server still checks.

The bridge is dayz-mcp, a third-party MCP server that this repo does not ship. Its behaviour below was measured in game on DayZ 1.29 and 1.30 with `CivilianSedan` and a test helicopter; the vanilla action code it runs into is cited from `P:\`.

## What vanilla checks

| Action | Condition | Source |
|---|---|---|
| `ActionGetOutTransport` | A vehicle command that is not `IsTransitioning`, a crew index of 0 or more, then `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` for that index. Its target condition is `CCTNone`, so the target plays no part. DayZ 1.29 had no transition check and called `IsAreaAtDoorFree` directly (lines 68 to 77 of the same file in that build, not on `P:\`). | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:57`, `:70` to `:79` |
| `ActionSwitchLights` | The player sits at `VEHICLESEAT_DRIVER`, checked on the server. | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:34` |
| Door state | A door reads closed at or below phase 0.5 in `TranslateAnimationPhaseToCarDoorState`; the door action moves it with `SetAnimationPhase`. | `P:\scripts\4_world\entities\vehicles\carscript.c:2248` to `:2258`; `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoors.c:91` |
| Sedan driver door | `CrewCanGetThrough` for seat 0 returns `false` while `CivSedanDriverDoors` is closed. | `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:226` to `:234` |
| Debug spawn | `SpawnEntityOnGroundPos` without a player creates a vehicle with `ECE_PLACE_ON_SURFACE`; in a `DEVELOPER` build a `Boat` gets `ECE_KEEPHEIGHT` instead. | `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:498` to `:502` |

## A client-side get-in is not enough

`vehicle_get_in_client` gives the client the ownership that `engine_set`, `vehicle_control` and `vehicle_trace` need. An action the server checks still fails: `ActionSwitchLights` tests `CrewMemberIndex(player) == VEHICLESEAT_DRIVER` on the server, so `action_use` kept answering `started: 1` while nothing lit. Calling `vehicle_enter`, the server-side seat, as well made the next identical `action_use` work.

For an action the server checks, use both calls, and never read `started: 1` as proof; check the effect.

Smaller limits of the same tools:

- `engine_set` takes `start` and `stop`, not `on` and `off`.
- `vehicle_control.hold_ttl_s` is capped low: 900 and 120 are refused, 30 is accepted. A vehicle parked on a slope rolls again the moment the hold ends.
- The stand's control has no reverse gear (throttle 0 to 1).

## Getting out on the stand

On the stand the get-out action fails the same way at every site tested:

- The driver door spawns closed, and `CrewCanGetThrough` needs it open (see the table).
- Opening the door through an injected action does not work. The action starts on the client (`started=1`), but its server half does nothing and the phase stays 0.0. `ActionCloseCarDoors` then fails its condition, which needs a phase above 0.5, and that tells you the door never opened.
- A car stopped against a static object also blocks the door space. With no reverse gear the site cannot be recovered, so pick sites with at least 150 m clear in the driving direction.

The clean teardown is deleting the vehicle with the player inside, then confirming the player reads `not_seated`. It ejected cleanly every time it was measured. Do not judge a site by whether get-out works.

## Deleting, binding and spawning

- The teardown above held on the stand's own fixtures. In a live play session, deleting a vehicle the player was put into with `vehicle_enter`, without taking them out first, split client and server: the client draws the player seated, the server has them on foot with no vehicle within 40 m, and the get-out key does nothing because the prompt is client side and the action is checked on the server.
- Once a player is bound to a vehicle, `vehicle_get_in_client` on another vehicle answers `not_seated`. `vehicle_release`, `player_teleport` and `ActionGetOutTransport` do not free them; only deleting the vehicle does. Comparing your vehicle with a vanilla one in the same session therefore needs a relaunch.
- The server copy of a car the client owns stays at its spawn point even after the owner drives it 70 to 100 m. The bridge's object tools find objects by position on the server within 25 m, so aim them at the spawn point or do not use them.
- The fourth parameter of `CreateObjectEx` is a set of `RF_*` flags, not a heading. A spawned vehicle takes the ground's orientation at its point, about 11.6 degrees apart for two points 40 m apart, and no tool sets it. When headings must match, choose sites by trial; the trace gives the real heading.
- Where a vehicle stands can stop it moving. The same build drove 91 m at one point and 0.12 m at another 40 m away, at full throttle. Before blaming config, ownership or code, swap sites and repeat in the order A, B, B, A.

## The camera

`camera_set` refuses with `camera_unavailable_vehicle` while `GetCommand_Vehicle()` is not null, and a moving vehicle cannot be left, so a scene that rolls away traps the camera. Set the static camera before getting in; it survives the get-in and gives an outside view of the seated player.

`camera_set` can also freeze the client's picture while simulation, sound and input carry on: the player walks, hears footsteps and moves on the server, but the image never changes. `capture_screenshot` shows it as `distinct_frames: 1` with `max_adjacent_delta: 0` over several frames while `query_player_state` shows the position moving. Only `dayz_test_stop` and a full `dayz_test_run` recover it:

- `restore_gameplay` always answers `restore_unverified`, because `camera_get` returns `camera_unavailable_no_scripted_camera`, which is the normal released state, so its retry advice can never succeed.
- `dayz_test_run(mode="client")` refuses with `client_already_polling`.
- Moving the game window from outside does not bring the picture back, and at 150% display scale it leaves the window oversized and black.

Use a scripted camera only when nothing else will do, and before handing the game back to a person, confirm with `distinct_frames` that the picture is live.

## Flying a mod that reads its own inputs

The bridge cannot fly a vehicle whose mod zeroes the car controller every tick (`SetSteering(0)`) and reads its own `UA` axes, because `UAInput` has no way to inject a value. The route that should work is a diag script on the owner that replaces the `UA` reading before `WriteToMove`; with the Pawn pattern the server reads the axes from the move (`ReadFromMove`), so no sync or RPC is needed. Not yet confirmed in game.
