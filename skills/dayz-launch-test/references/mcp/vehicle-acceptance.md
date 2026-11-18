# Vehicle acceptance steps

How to accept a car through the dayz-mcp bridge, from an imported model to a car that drives and turns the right way: the owner side driving verbs, the acceptance steps R1 to R6 that `run_vehicle_checks.py` walks, where each step's car must stand, and the table that maps each failure to its known fix in the vehicles pack.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game sessions with that tool on test cars, and not checked on `P:\` except where a vanilla file is cited. `MCPClientBridge.c`, `MCPBridge.c` and `MCP_CarScript.c` are files of the `@DayZ_MCP` mod; `<dayz-mcp>` is the folder of your dayz-mcp checkout. Fix files named below without a path are in the vehicles pack, `_shared/vehicles/`, which `dayz-vehicle-specialist` reads.

## Owner side driving verbs

dayz-mcp has a set of verbs, each checked in game, that drive a car from the owner's side: the client takes ownership and applies throttle and steering. All run on the client peer except `query_get_in_condition`, which runs on the server peer.

| Verb | What it does |
|---|---|
| `vehicle_get_in_client(pos)` | Seats the client in the car near `pos` and takes ownership; returns `seated`, `is_owner` and `vehicle_fixture_ready`. It runs the car's `OnDebugSpawn` on the client, which does nothing under server authority, so `vehicle_fixture_ready=1` does not mean the car has wheels or fuel. Condition the car on the server first (`vehicle-smoke.md`, "Giving a spawned car wheels and fluids"). |
| `engine_set(mode)` | Starts (`"start"`) or stops (`"stop"`) the engine of the car the client owns. |
| `vehicle_control(throttle, steer, brake, handbrake, hold_ttl_s)` | Sets held control: the car keeps driving with no further call until `vehicle_release` or until the `hold_ttl_s` deadman runs out. Refuses values out of range and NaN. |
| `vehicle_telemetry()` | Speed, gear, engine, position, `is_owner` and `net_strategy` of the owned car. |
| `vehicle_release()` | Releases the held control. |
| `query_get_in_condition(pos, component=-1)` (server) | Says whether a normal get-in would be available and which of the seven checks of `ActionGetInTransport` blocks it. `component` is the index from an earlier `scene_raycast`; it is needed for an `available` verdict, and without it the answer is `partial`, which never counts as a pass. |

Server side conditioning uses two more: `vehicle_enter(pos)` seats the player on the server, and `vehicle_drive {throttle, duration}`, sent as a raw enqueue, runs the car's `OnDebugSpawn` on the server in its preparation phase (in `MCPBridge.c`). `telemetry_read(mode="object_at", type, pos, radius)` then reads `wheel_count` and `fuel_fraction`.

How the owner drive works, confirmed in game: the client takes ownership by running `StartCommand_Vehicle` on its side (`OnVehicleSeatDriverEnter` calls `Possess(car)` under `FEATURE_NETWORK_RECONCILIATION`). Driving from the owner means applying `SetThrottle` and `SetSteering` inside `CarScript.OnInput` after `super`, which the bridge PBO does in a `modded class CarScript`; a `Car.SetThrottle` call from the mission is overwritten by `super.OnInput` with the driver's input of 0. A static holder, `MCPCarDrive`, and its deadman carry the state.

Two cautions, both confirmed: measure the drive's `pos_delta` on clear ground, because an obstacle in front gives a misleading value near 0; and keep the car next to the player for `query_get_in_condition`, because its seventh check measures the distance from the player to the door. dayz-mcp's reference gate drivers, which use raw enqueues, are `<dayz-mcp>/tools/tramoA_verbs_gate.py` and `<dayz-mcp>/tools/tramoB_getin_gate.py`.

## How the steps are walked

Run the steps after the visual smoke test: the vehicle playbook in `playbooks.md` has launched the game, the bridge is green and the car loads. The steps start where the smoke test ends (the entity spawns and is seen) and end when the car drives and turns to the correct side. The goal is to iterate on a car without a person in the game, and to stop and escalate as soon as a failure falls outside the known table.

They assume, and do not repeat:

- A launch with a green `bridge_status`, both peers at `version_state=ok`, and a spawned player (`query_player_state` returns `pos`): the vehicle playbook and `bridge-setup.md` (stock mission, bridge seed, `-PackOnly`, waiting for the Central Economy, flaky captures).
- An adopted run with a live lease: `session_acquire_wait` adopted it and you send `session_heartbeat` at least every 90 seconds (`run-lifecycle.md`). With no owner the idle run fence refuses every verb, reads included.
- The test machine is yours alone for the session (`run-lifecycle.md`, "The test machine is one shared resource"). Run one session.
- The verbs above are built and checked in game. The steps drive the bridge; they do not build it.

1. Place the car (below) and walk R1 to R6 in order.
2. On each failing step, look the symptom up in "Failure to fix table". If it is there, record the step and its fix in the journal and keep collecting what the reachable steps can tell you (see "Which failures end the pass"); do not rebuild mid pass. If it is not there, stop and escalate; do not rebuild blindly.
3. At the end of the pass, apply all recorded fixes together to the `.p3d` and the config. This is the agent's or a person's loop, not the script's: read the screenshots and edit geometry or config with the vehicles pack. Then rebuild and deploy once (`/dayz-build-pbo`, then relaunch) and walk the steps again, so each test in the game counts for every change.
4. Each car gets an iteration budget, 6 passes by default. If it does not converge within it, escalate rather than loop.

### Which failures end the pass

- R1 ends the pass: with no entity there is nothing to test. Fix it and spawn again.
- R4, including its conditioning, ends the pass for R5 and R6: a car that is not seated and conditioned cannot be driven. Record it and skip them.
- R2, R3 and R6 do not end the pass; record the fix and go on. R3 in particular does not block R4 or R5: `vehicle_get_in_client` forces `StartCommand_Vehicle` and skips the get-in action's checks, so a car a person could not get into can still be driven through dayz-mcp. That is a useful pair of signals: the car drives, and the get-in fix is still needed. Collect both in the same pass.

### Where the car stands

R3 and R4 pull one way and R5 the other, and a car in the wrong place gives a false green or a false red.

- R3 (`query_get_in_condition`) and R4 (`vehicle_enter`, `vehicle_get_in_client`) need the car next to the player: the seventh check measures player to door distance, and the client side seat looks for a nearby vehicle.
- R5 needs a clear track ahead; an obstacle gives a `pos_delta` near 0.
- Spawn the car at the player's position on open ground with at least 150 m clear in every direction it might face. The `world_spawn` argument `rotation` does not set a heading: it is the placement flag passed to `CreateObjectEx` as `iRotation` (`P:\scripts\3_game\global\game.c:703`; 0 leaves `RF_DEFAULT`, 512, `P:\scripts\3_game\ce\centraleconomy.c:66`), as `collision-probes.md` ("Posing a test object square to the world") and `verb-gotchas.md` describe. A spawned car takes the slope of the ground at its point and no tool sets its heading, so choose the site, not the direction. The airfield site in `vehicle-smoke.md` is a good start.
- A `pos_delta` near 0 can be a false red; do not decide the drivetrain is broken on the first reading. With R4 passed (seated, owner, conditioned) and R5 run with throttle: if `vehicle_telemetry` shows `speedo_max` above 0, the gear shifts up by itself, or the engine revs (RPM rises in the `[MCP-DRIVE]` log), the powertrain works and an obstacle blocks the car, so run R5 again on clear ground (an offset like `tramoA_verbs_gate.py --dz 40`). If `speedo_max` stays near 0, the engine does not rev and the wheels are not simulated, the wheel simulation or drivetrain is really broken, and that is an R5 fix. On one test car an obstacle in front gave a `pos_delta` of 0.15 to 0.25 at full throttle, and the same car on clear ground 40 m away drove 29 m.

## The steps

| Step | Verbs | Pass | Failure and its fix |
|---|---|---|---|
| R1, spawns | `world_spawn(type, pos, rotation)` | `ok=1`, `found=1` and an entity with a `pos`. | `unknown_type` or `spawn_failed`: the mod is not mounted or `CfgPatches` does not register. Spawns but is invisible, or "action selection not found in geometry": `componentNN` (loose islands). |
| R2, solid and oriented | `scene_raycast(from, to)` at several points; `camera_set(cam_mode:"lookat")` with `capture_screenshot` from several angles | Rays hit where they should; no holes or inverted faces; the right orientation and a plausible scale. | A hole from one angle that is solid from the other: per part winding. A rotated or mirrored car: the orient transform. A wrong size: scale. A floating part or one turned about 90 degrees: the proxy frame. |
| R2.5, gameplay restored | (the `lookat` camera does not stop the simulation; see below) | Simulation and controls are live before driving; the free camera is not used here. | If R4 or R5 does not respond with seated, owner and engine on, suspect the free camera or the simulation before the drivetrain. |
| R3, get-in available | `scene_raycast` in a ring for the `component`, then `query_get_in_condition(pos, component)` | The driver seat (`component_crew_index==0`) is `available=1` with `first_block=""`. If only a passenger seat is available a person cannot drive it, so R3 fails. | The driver seat's `first_block` (see the table below). Does not block R4 or R5. |
| R3b, the real action | `scene_raycast` down onto the seat, `player_teleport` and `player_look_at`, `action_cursor`, `action_use("ActionGetInTransport", component_index, cursor_pos)`, then `vehicle_telemetry` | The cursor slot shows `ActionGetInTransport` on the seat's component, then `seated=1`, from both sides and for each seat (see below). | The slot is empty while R3 is `available=1`: the cursor is on another component or on the wrong side. R3 `unreachable` on one side only: the door condition point is on one side. |
| R4, conditioned on the server | `vehicle_enter(pos, timeout_s=30)`, a raw `vehicle_drive {throttle: 0.01, duration: 0.5}`, then `telemetry_read(mode="object_at")` | `wheel_count` equals the car's wheel count and `fuel_fraction` is above 0. | `wheel_count` short: `OnDebugSpawn` attaches no wheels, or an `Axles` override lists only one axle (`invariants-wheels-and-hubs.md`). Fuel 0: read `telemetry_read` again before deciding (`vehicle-verbs.md`), then check that `OnDebugSpawn` fills the tank. Blocks R5 and R6. |
| R4, seated | `vehicle_get_in_client(pos)` | `seated=1`, `is_owner=1`, `vehicle_fixture_ready=1`. | `not_seated` or `seat_failed`: reach, the seat animation or the crew bone. Blocks R5 and R6. |
| R5, drives | `engine_set("start")`, `vehicle_control(throttle:1, hold_ttl_s:12)` called once, `vehicle_telemetry`, `vehicle_release` | `pos_delta` above 1.0 m, `speedo_max` above 0, `engine_on_server` and `is_owner`. Rolling from gravity or inertia does not count. | `pos_delta` near 0 with engine on and ownership: ambiguous, so test again on clear ground before mapping a fix (`needs_clear_ground_retest`). Still near 0 with the engine revving: the wheel simulation (Fire Geometry) or the drivetrain. |
| R6, wheels and direction | `vehicle_control(steer:-1)` with `vehicle_telemetry` samples, optionally `camera_set` in `lookat` | The car curves to the commanded side. The left and right sign is not calibrated: the script reports `signed_cross`; confirm against a vanilla car before deciding. | Curves the opposite way, or the wheels are mirrored: the sign of the wheel `angle` in `model.cfg`, or the `wheel_X_Y` naming. |

Fields the verbs return: `world_spawn` gives `pos_real` and `pos`; `vehicle_get_in_client` gives `seated`, `is_owner` and `vehicle_fixture_ready`; `vehicle_telemetry` gives `speedo_max`, `gear`, `engine_on_server`, `pos`, `is_owner` and `net_strategy`; `telemetry_read(mode="object_at")` gives `found`, `wheel_count` and `fuel_fraction` among others; `query_get_in_condition` returns `get_in` with `available`, `partial`, `crew_size`, `component_crew_index`, `first_block` and `per_seat[]` (`crew_index`, `crew_can_get_through`, `area_free`, `occupied`, `reachable`); `scene_raycast` returns `raycast` with `hit` and `component`. These were checked against the verb schemas and against the two reference gate drivers, which passed their gates in game.

### Keep the simulation running

The camera and the get-in both touch the player's simulation, and the wrong order leaves the car inert while every other verb reads green. From `MCPClientBridge.c`:

- `camera_set` always suppresses the controls (`SuppressGameplay()`, which calls `PlayerControlDisable` and hides the HUD) but stops the simulation only with `cam_mode="free"`, which calls `DisableSimulation(true)`. The `lookat`, `orient` and `matrix` modes create a `staticcamera` and the simulation stays live.
- `vehicle_get_in_client` (`ProcessVehicleGetInClientPrep`) seats the player with `StartCommand_Vehicle`, runs the client side `OnDebugSpawn` and takes ownership, but never calls `RestoreGameplay()`. Apart from the `restore_gameplay` verb, which can answer `restore_unverified` (`test-stand-and-mcp.md`), only the `drive_probe_client` preparation restores it (`ProcessDriveProbeClientPrep` calls `RestoreGameplay()`, which calls `DisableSimulation(false)` and `PlayerControlEnable(true)`). So a simulation stopped by a free camera does not come back at R4: the get-in hangs at `not_seated`, because a stopped player simulation never completes `HumanCommandVehicle`.
- So use `cam_mode="lookat"` for R2 and R6, a fixed camera with live simulation; driving keeps working because the `MCPCarDrive.OnInput` holder applies the throttle, not the player's input. Never use `cam_mode="free"` between R2 and R5. If R5 does not move with `seated=1`, `is_owner=1` and the engine on, suspect a free camera first, not the drivetrain.

### R3b: the player's own get-in

R3 and R4 do not show what a player sees. `query_get_in_condition` evaluates the checks of `ActionGetInTransport.ActionCondition` for the component it is given, not the one under the cursor; it also skips `CanGetIn()` and calls `IsAreaAtDoorFree` where the action calls `IsAreaAtDoorFreeDiag`, so its `available=1` is partial. The vanilla action checks `CanGetIn()` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`), `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` (`:54`) and `CanReachSeatFromDoors` (`:64`). `vehicle_enter` and `vehicle_get_in_client` seat the player without the action, which is how a test quad passed every seated test while its right side turned out to have no get-in action for either seat (the one sided get-in finding in `dayz-1-30-vehicles.md`). Run this from both sides and for each seat:

1. Find the seat component with `scene_raycast(intersect="view")` straight down onto the top of the seat. On a test quad that gave component 16 for the driver and 18 for the co-driver. A level ray at seat height hit the rear fender (component 31) first.
2. R2 leaves the `lookat` script camera on, and while it is active `player_look_at` returns `script_camera` (`MCPClientBridge.c:6758`): send `restore_gameplay` and wait for its answer first. Then stand within 1 m of the seat's door condition point and `player_look_at` the top of the seat. Aiming converged up to about 42 degrees off the body heading; targets at 60 and 76 degrees ended in `deadline` and the view went back to the body heading, which `player_teleport` does not change. Place the player so the seat lies within about 40 degrees of the current heading, for example behind left or behind right of a car facing the same way.
3. `action_cursor` passes when `cursor.slots.continuous_primary.action_class` is `ActionGetInTransport` and `cursor.target.component_index` is the seat's component. On screen the hold prompt sits under the vehicle's name, in the client's language (`Entrar [MANTENER]` in a Spanish client).
4. `action_use("ActionGetInTransport", classname=<type>, component_index=<from action_cursor>, cursor_pos=<from action_cursor>)`, then `vehicle_telemetry`: pass when `seated=1` on the expected seat. Without `pos`, `action_use` picks the nearest matching object, not the one under the cursor (`MCPClientBridge.c:4094`), so pass `pos` and `radius` for the object `action_cursor` saw and check the seated car is that one, or keep a single car of the type in range. `action_use("ActionGetOutTransport", target="self")` gets the player out again.

A build whose scripts did not load shows here too: `telemetry_read object_at` reports `class_name="CarScript"` instead of the mod's class, the cursor shows only the vehicle's name, and R3 stops at `crew_can_get_through` (seen with a Workshop copy that held an older PBO: the `World` module loaded five files fewer than with the fixed one).

### Guardrails against a false green

1. A failure outside the table means stop and escalate. The table maps known symptoms; a new one needs understanding, not random iteration.
2. The verdict comes from the game, never an offline stand-in. An offline audit can filter before a rebuild (`skills/dayz-p3d-audit/scripts/audit_getin_wheels.py`, and a per part winding check in your own import workspace, `rip-import.md`), but the step's verdict is still the reading in game. Offline checks have given a false green on two test cars.
3. Keep an iteration budget and a journal per pass. Give each pass its own folder, `<TargetMod>_dev\_acceptance\run_<n>\`: run `run_vehicle_checks.py --journal <TargetMod>_dev\_acceptance\run_<n>` so its `verdict.json` (the step reached, `first_block`, `pos_delta`, the telemetry it read and the mapped fix) lands there, and save that pass's R2 and R6 PNGs beside it. Without `--journal` the script writes `.\_acceptance\<vehicle>\verdict.json` in the current folder, and the next pass overwrites it.

## Failure to fix table

| Symptom or signal | Step | Fix (where to read it) |
|---|---|---|
| `world_spawn` returns `unknown_type` or `spawn_failed` | R1 | The mod is not mounted or `CfgPatches` does not register it: `../windows-build-and-mount.md` on absolute mod paths. Not a model fault. |
| Spawns but is invisible, or "action selection X not found in view/fire geometry" | R1 | The `componentNN` double tag: `vehicle-structural-parity.md` and `rip-import.md`. Hubs and seats are islands with no overlap, so the collision enumerator does not see them; each also carries a `componentNN` selection on the same faces. |
| A hole from one angle, solid from the other | R2 | Per part winding, not a global flip (a global flip gave a false green): `rip-import.md`. The lasting fix orients each part to the source model's normal. |
| The car is rotated or mirrored, or a part floats or is turned about 90 degrees | R2 | The body's orient transform, or the proxy frame `R=((-1,0,0),(0,0,1),(0,1,0))`: `_shared/vehicles/proxies-and-detachable-parts.md`. py3d with `rotation=None` renders the part about 90 degrees off. |
| `first_block="componentNN"` (`component_crew_index<0`) | R3 | `componentNN` on the seats (the same fix as the invisible R1 case): the seat is not counted as a crew component. |
| `first_block="crew_can_get_through"` | R3 | A bare `class X: CarScript` inherits `Transport.CrewCanGetThrough()=false`: `rip-import.md`. Extend `CarScript` with overrides of `CrewCanGetThrough`, `GetSeatAnimationType` and `GetAnimInstance`, and add `worldScriptModule` in `CfgMods`. Doors are not needed. |
| `first_block="area_blocked"` (check 6b) | R3 | `IsAreaAtDoorFree` is false: something blocks the door area, or the door selection is wrong. |
| `first_block="unreachable"` (check 7) | R3 | `CanReachSeatFromDoors` is false: seat and door geometry, or the car is too far from the player. Move the player next to the car before deciding the model needs a fix. |
| The `action_cursor` slot is empty while R3 is `available=1` | R3b | R3's diagnosis is partial: it skips `CanGetIn()` and uses `IsAreaAtDoorFree`, while the action checks `CanGetIn()` and `IsAreaAtDoorFreeDiag` (for example a fallen motorbike, `P:\scripts\4_world\entities\vehicles\motorbikescript.c:225`). Likely, not proven: the cursor is on another component (fender, body). Aim at the top of the seat and compare `cursor.target.component_index` with the seat's component. |
| R3 `unreachable` from one side only | R3b | Likely: the door condition points sit on one side (seen on one test quad at the positions tried): `dayz-1-30-vehicles.md`, the one sided get-in finding. |
| `telemetry_read` reports `class_name="CarScript"` and R3 stops at `crew_can_get_through` | R3 | The mod's scripts did not load. Compare `Module: World; loaded Nx files` with a run without the mod (`dayz-1-30-vehicles.md`, the script module path finding: backslashes in `files[]` load nothing on 1.30). |
| `first_block="occupied"`, `"item_heavy"` or `"already_in_vehicle"` | R3 | The test's own state, not a model fault: spawn a clean car, drop the heavy item from the hands, or get out first. |
| `first_block="no_component"` (`partial=1`) | R3 | `component=-1` was passed. Take a real `component` from a `scene_raycast`; without it the diagnosis is partial and never a pass. |
| `wheel_count` short or `fuel_fraction` 0 after server conditioning | R4 | `OnDebugSpawn` attaches no wheels, or an `Axles` override lists only one axle (`invariants-wheels-and-hubs.md`, "List every axle in an `Axles` override"). For fuel, read `telemetry_read` again first: the bridge can read the tank in the same tick as the `Fill()` (`vehicle-verbs.md`). |
| `vehicle_get_in_client` returns `not_seated` or `seat_failed` | R4 | Get-in latency (raise `prep_deadline`), the crew bone or selection, or the seat animation type: `vehicle-config-and-modelcfg.md`. The crew proxy needs both a selection in the geometry and a bone in `CfgSkeletons`, or the get-in breaks. |
| `pos_delta` near 0 with an obstacle ruled out | R5 | Wheel simulation (Fire Geometry): `rip-import.md` (each wheel proxy's face also in the visual `wheel_X_Y`, `wheel_X_Y_damper` and, at the front, `wheel_X_1_steering`) and `vehicle-structural-parity.md` (hubs as faces and `componentNN` in the Geometry LOD); or the drivetrain in `config.cpp`. |
| The car curves opposite to the commanded `steer`, or the wheels are mirrored | R6 | The sign of the wheel `angle` in `model.cfg` (`vehicle-config-and-modelcfg.md`) and the `wheel_X_Y` naming (`rip-import.md`: the first index is the side, 1 = +x and 2 = -x; the second is the axle, 1 = front; watch for mirroring between imported car conventions and the vanilla sedan's). |

## The reference script

`skills/dayz-launch-test/scripts/run_vehicle_checks.py` walks R1 to R6 against the daemon on port 8765 with raw `/enqueue` and `/await` calls, the same pattern as dayz-mcp's two reference gate drivers.

- It needs a live lease. Adopt the run with `session_acquire_wait` from your MCP session and pass the identity and lease token it returned (`--identity` and `--lease-token`, or `DAYZ_MCP_IDENTITY` and `DAYZ_MCP_LEASE_TOKEN`); the script sends them in every `/enqueue` body beside `?key=` (`vehicle-smoke.md`). It does not renew the lease, so keep sending `session_heartbeat` from your session at least every 90 seconds while it runs. A fence refusal (`run_not_owned`, `lease_expired`, `lease_invalid`) stops it at once with that error.
- It stops at the first failure that ends the pass, or collects those that do not, and writes `verdict.json` naming the step, the `first_block` and the mapped fix into the `--journal` folder.
- It does not apply fixes or rebuild; that is the agent's or a person's loop.
- It reports `objective_PASS` for the steps a script can close. Real acceptance also needs the agent's visual checks (R2 for winding, orientation and scale, and the R6 turn calibration), which the script cannot close.
- Its safeguards: R3 checks the driver seat, not any seat. `R4_conditioned` seats the player on the server, runs `OnDebugSpawn` there and requires `wheel_count` (`--wheels`, 4 by default) and fuel. R4 fails closed on seated, owner and fixture ready. A preflight aborts if the player already sits in a car, since a second run would measure the old one. R5 requires the engine on and ownership, and reports `needs_clear_ground_retest` instead of guessing between an obstacle and the drivetrain. Each verb is checked for timeout and `ok`, because a test failure is not a model fix.
- Offline fixtures: `skills/dayz-launch-test/scripts/test_run_vehicle_checks.py` (12 tests).

Each step reuses a verb sequence that passed its own gate in game. The full R1 to R6 chain in one run, the very test the script exists for, has not been run as a unit. The script compiles and its offline fixtures pass; the server conditioning step and the lease arguments follow `vehicle-smoke.md` and `run-lifecycle.md` and have not yet been run through it in game.
