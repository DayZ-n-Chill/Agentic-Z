# Automated vehicle test stand

Measured limits of driving, seating and unseating a vehicle from an automated test harness (the dayz-mcp bridge), and which actions the server still validates.

> Status: measured in game through dayz-mcp, a third-party MCP server that this repo does not ship, on DayZDiag 1.29 and 1.30 with `CivilianSedan` and the LFHeli build; not yet checked on `P:\`. A citation written with its full `P:\` path was opened on vanilla data (a 1.30 build); a bare `file.c:N` is a 1.30 line number that repeats or extends a full citation in the anchors list below, and a number given for 1.29 cannot be checked on `P:\`. `MCPBridge.c` is dayz-mcp's own script. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- `ActionGetOutTransport.ActionCondition` needs a vehicle command that is not `IsTransitioning` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:70-73`) and then `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` for the crew index (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:79`); its target condition is `CCTNone` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:57`).
- `ActionSwitchLights` requires the player to sit at `VEHICLESEAT_DRIVER` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:34`).
- A door reads as closed at or below phase 0.5 in `TranslateAnimationPhaseToCarDoorState` (`P:\scripts\4_world\entities\vehicles\carscript.c:2248-2250`), and the door action moves it with `SetAnimationPhase` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoors.c:91`).
- The debug spawner creates objects with `ECE_PLACE_ON_SURFACE` among its flags (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:454`).

## Scripted pilot: UAInput has no injection API

**Scripted-pilot limitation — `UAInput` has no injection API (added 2026-08-17, LFHeli):** the dayz-mcp bridge cannot pilot a vehicle whose mod neutralizes the CarController (`SetSteering(0)` every tick) and reads its own UA axes, because `UAInput` does not admit value injection. The working path is a DIAG script in the OWNER that substitutes the UA reading before `WriteToMove`: with the Pawn pattern of active forces the server consumes the axes from the Move (`ConsumeMove → ReadFromMove`), so the script needs no sync and no RPC. Status: pending — conditioned on the scripted pilot actually flying (do not promote a mechanic without in-game adjudication); the get-out re-registration of `runtime-state-and-sync.md` was adjudicated in-game 17-Aug.

## Invariant 15e: a client-side get-in is not enough for an action the server validates

**Through dayz-mcp, a client-side get-in is not enough for any action the SERVER
validates (measured 2026-09-10).** `vehicle_get_in_client` establishes the client
ownership that `engine_set`, `vehicle_control` and `vehicle_trace` need, but
`ActionSwitchLights` checks `car.CrewMemberIndex(player) == VEHICLESEAT_DRIVER` in
`ActionCondition` on the server
(`scripts/4_world/classes/useractionscomponent/actions/interact/vehicles/actionswitchlights.c`),
so it was rejected silently: `action_use` kept answering `started: 1` and nothing lit, three
times. Calling `vehicle_enter` (server-side seat) as well made the very next identical
`action_use` work. Rule: for a server-validated action use BOTH verbs, and never read
`started: 1` as evidence - verify the effect. Two related bounds cost a round trip each:
`engine_set` takes `start`/`stop`, not `on`/`off`, and `vehicle_control.hold_ttl_s` is
capped low (900 and 120 rejected, 30 accepted), so a vehicle parked on a slope starts
rolling again the moment the hold expires.
Also: `camera_set` refuses with `camera_unavailable_vehicle` while
`GetCommand_Vehicle()` is non-null, and a moving vehicle cannot be exited, so a scene that
rolls away traps the camera. Set the static camera BEFORE getting in - it survives the
get-in and gives the external view of a seated rider.
**And it can be worse than a refusal: `camera_set` can leave the client RENDER frozen while
simulation, audio and input keep running** (measured again 2026-09-10, this time in a live
play session). The player walks, hears their own footsteps, and their server position
advances, but the picture never changes. The signal is in `capture_screenshot`:
`distinct_frames: 1` with `max_adjacent_delta: 0` over several frames, while
`query_player_state` shows the position moving. There is NO recovery short of
`dayz_test_stop` + a full `dayz_test_run`: `restore_gameplay` has no path to green in that
state (it always answers `restore_unverified`, because `camera_get` returns
`camera_unavailable_no_scripted_camera` - which IS the released state - and its "Retry"
advice cannot ever succeed), and `dayz_test_run(mode="client")` refuses with
`client_already_polling`, because polling is taken as proof of health and it is not. Do NOT
try to force a repaint by moving the window host-side with SetWindowPos: it does not restore
the render, and under a 150% display scale it leaves the window oversized and black.
Practical rule: use a scripted camera only when nothing else will do, and before handing the
game back to a human, confirm the render is alive with `distinct_frames`.
Two more traps from the same session: deleting a vehicle a player was put into with
`vehicle_enter`, without taking them out first, desynchronises client and server - the client
draws them seated while the server has them on foot with no vehicle within 40 m, and holding
the get-out key does nothing because the prompt is client-side and the action is validated
server-side. And once a player is bound to a vehicle, `vehicle_get_in_client` on ANOTHER one
answers `not_seated`; neither `vehicle_release` nor `player_teleport` nor
`ActionGetOutTransport` frees them. Only deleting the vehicle does. That makes "measure ours,
then measure a vanilla control in the same session" impossible without a relaunch.

## Automated vehicle stand: measured invariants (added 2026-08-24)

Measured on dayz-mcp stand (DayZDiag 1.29.163709, CivilianSedan), ABBA session
(the frictions below aborted 3 attempts):

- **Get-out**: `ActionGetOutTransport.ActionCondition` = `!IsTransitioning() && crewIndex >= 0 && CrewCanGetThrough && IsAreaAtDoorFreeDiag` (actiongetouttransport.c:70-79; 1.29 had no transition check and `IsAreaAtDoorFree`, 1.29 actiongetouttransport.c:68-77; `CCTNone` — target does not participate). A car stopped AGAINST statics leaves door blocked and action in `condition_failed`; stand control surface has no reverse gear (throttle 0..1) — site becomes unrecoverable. Design site with >=150 m clear IN DRIVING DIRECTION and graceful cleanup: deleting fixture with player inside cleanly ejects (4/4 measured).
- **Spawn heading**: 4th parameter of `CreateObjectEx` is `RF_*` flags, NOT yaw; vehicle inherits ground orientation at point (~11.6 degrees between two points 40 m apart). No orientation setter via tools: if experiment demands comparable headings, sites are selected empirically (trace samples give actual driven heading).
- **Positional drivability**: a vehicle can end up FROZEN (2s delta ~0.12 m at throttle 1.0) due to SITE — same binary/config drove 91 m at one point and 0.12 m at another 40 m away. Before blaming config/ownership/code: ABBA of sites.

## Stand get-out: the real chain and the sanctioned teardown (added 2026-08-24)

Triangulated across 13 rounds on NWAF (2026-08-24). ActionGetOutTransport `condition_failed` on stand fixtures
DOES NOT depend on site (identical across 9 sites, 7 pristine):

- Driver door spawns CLOSED and `CrewCanGetThrough` requires it non-closed
  (civiliansedan.c:226-234; phase <=0.5 = CLOSED, carscript.c:2248-2258).
- Opening via action DOES NOT work: server half of injected actions is inert
  (`OnStartServer`/SetAnimationPhase does not materialize, actioncardoors.c:91) - action
  STARTS on client (started=1) but phase remains 0.0. Cheap discriminator:
  ActionCloseCarDoors returns condition_failed after "opening" (its condition requires
  phase >0.5 and shares IsAreaAtDoorFree with get-out, which is exculpated).
- SERVER replica of client-auth car does not leave spawn point even if owner-peer
  drives 70-100 m: object_anim/object_inspect (resolve by position on server,
  radius 25, MCPBridge.c:20) must be targeted AT SPAWN or not used.

**Sanctioned teardown**: object_delete of fixture with ejection verified via telemetry
(`not_seated`); 18/18 clean accumulated. Action-based get-out is NOT a site criterion.
