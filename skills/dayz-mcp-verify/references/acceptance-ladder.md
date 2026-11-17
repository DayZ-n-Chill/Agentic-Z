# Acceptance ladder: from a ripped model to a drivable car

The full ladder for accepting a drivable car through the dayz-mcp bridge: the owner-side driving verbs, rungs R1 to R6, the table that maps each failure to its known fix (the "SUB_BRZ taxonomy", named after the car it was built on), and what the `drive_ladder.py` orchestrator in this folder does.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game sessions with that tool; it is not yet checked on `P:\` except where a vanilla file is cited. `MCPClientBridge.c`, `MCPBridge.c` and `MCP_CarScript.c` are files of the `@DayZ_MCP` mod and their line numbers are from the time of the measurement; `<dayz-mcp>` is the folder of your dayz-mcp checkout. File names such as `rip-import.md`, `vehicle-structural-parity.md`, `vehicle-config-and-modelcfg.md` and `dayz-1-30-vehicles.md` are files of the vehicles pack in `skills/_shared/vehicles/`, which the `dayz-vehicles` skill reads; search those files for the quoted term.


## Owner-side driving verbs (added 2026-06-28)

In its phase 5 dayz-mcp added, and gated in game, a set of verbs that drive the car owner-side: the client takes ownership of the car and applies throttle and steering. All of them run on the client peer except `query_get_in_condition`, which runs on the server peer.

| MCP tool | What it does |
|---|---|
| `vehicle_get_in_client(pos)` | Seats the client in the car near `pos` and takes ownership. It returns `seated`, `is_owner` and `vehicle_fixture_ready`. It runs the car's `OnDebugSpawn` on the client, which does nothing under server authority, so `vehicle_fixture_ready=1` does not mean the car has wheels or fuel; condition the car on the server first (`vehicle-smoke.md`, "Conditioning a custom car on the server"). |
| `engine_set(mode)` | Starts (`"start"`) or stops (`"stop"`) the engine of the car the client owns. |
| `vehicle_control(throttle, steer, brake, handbrake, hold_ttl_s)` | Sets sustained control: the car keeps driving without another call until `vehicle_release` or until the `hold_ttl_s` deadman expires. It rejects values out of range and NaN. |
| `vehicle_telemetry()` | Speed, gear, engine, position, `is_owner` and `net_strategy` of the car the client owns. |
| `vehicle_release()` | Releases the sustained control. |
| `query_get_in_condition(pos, component=-1)` (server peer) | Says whether a normal get-in would be available and which of the 7 checks of `ActionGetInTransport` blocks it. `component` is the index from an earlier `scene_raycast`; it is required for an `available` verdict, and without it the answer is `partial`, which never counts as a pass. |

The server-side conditioning uses two more verbs: `vehicle_enter(pos)` seats the player on the server, and `vehicle_drive {throttle, duration}`, sent as a raw enqueue, runs the car's `OnDebugSpawn` on the server in its preparation phase (`MCPBridge.c:2104-2112`). `telemetry_read(mode="object_at", type, pos, radius)` then reads `wheel_count` and `fuel_fraction`.

How the owner-side drive works, verified in game (there is no need to investigate it again): the client takes ownership by running `StartCommand_Vehicle` on the client side (`OnVehicleSeatDriverEnter` calls `Possess(car)` under `FEATURE_NETWORK_RECONCILIATION`). Driving from the owner requires applying `SetThrottle` and `SetSteering` inside `CarScript.OnInput` after `super`, which the MCP PBO does in a `modded class CarScript`; a `Car.SetThrottle` call from the mission is overwritten by `super.OnInput` with the driver's input of 0. The static holder `MCPCarDrive` and its deadman carry the state. See the `dayz-vehicles` skill.

With these verbs, rungs that used to be manual can be scripted:

- R3, get-in available: `query_get_in_condition` with a `component` from a raycast gives `available` and `first_block`.
- R4, seated: `vehicle_enter` and a short `vehicle_drive` condition the car on the server, then `vehicle_get_in_client` gives `seated` and `is_owner`.
- R5, drives: `engine_set`, `vehicle_control`, `vehicle_telemetry` and `vehicle_release`; `pos_delta` grows.
- R6, wheel direction: `vehicle_control` with `steer`, plus a visual check.

Two caveats were verified with these gates. To measure the driving `pos_delta`, put the car on clear ground, because an obstacle in front gives a misleading `pos_delta` near 0. `query_get_in_condition` needs the car next to the player, because check 7 (reachability) measures the distance from the player to the door. The reference gate drivers, which use raw enqueues, are `<dayz-mcp>/tools/tramoA_verbs_gate.py` and `<dayz-mcp>/tools/tramoB_getin_gate.py`.

## The acceptance ladder: from a rip to a drivable car (added 2026-06-28)

The orchestrator walks an ordered ladder of rungs. Each rung reads ground truth in the game with the verbs above, and each failure maps to a known fix in the SUB_BRZ taxonomy (in the `dayz-vehicles` skill and the vehicles pack in `skills/_shared/vehicles/`). The goal is to iterate on a car, from a source-game rip to a drivable car, without a human in the game, and to stop and escalate as soon as a failure falls outside the known taxonomy.

Run the ladder after the visual smoke test: the vehicle playbook in `playbooks.md` has already launched the game, the bridge is green and the car loads. The ladder is the driving extension of the smoke test. It starts where the smoke test ends (the entity spawns and is seen) and ends when the car drives and turns to the correct side.

### Preconditions

The ladder inherits these from earlier steps and does not repeat them:

- Launch, readiness and a green `bridge_status`: the vehicle playbook and `bridge-setup.md` (stock mission, bridge seed, `-PackOnly`, waiting for the Central Economy, flaky captures). The ladder assumes both peers report `version_state=ok` and the player has spawned (`query_player_state` returns `pos`).
- An adopted run with a live lease: `session_acquire_wait` has adopted the run and you send `session_heartbeat` at least every 90 s (`run-lifecycle.md`). Without an owner the idle-run fence rejects every verb, reads included.
- The DayZ machine is yours alone for the session (a hard precondition, see `run-lifecycle.md`, "The test machine is one shared resource"). Run a single session.
- The verb surface above is built and gated in game. The ladder does not build the bridge; it drives it.

### How the ladder is walked

1. Place the car (see "Spawn placement") and walk R1 to R6 in order.
2. On each failing rung, check whether the symptom is in the SUB_BRZ taxonomy (the "Failure to fix mapping" table).
   - If it is, record the rung and the mapped fix in the journal and keep collecting signal from the rungs that can still be reached (see "Which failures end the pass" below). Do not rebuild in the middle of a pass.
   - If it is not, stop and escalate (guardrail 1). Do not rebuild blindly.
3. At the end of the pass, the agent applies all recorded fixes together to the `.p3d` and the config. This is a loop of the agent or a human, not a script: read the screenshots and edit the geometry or config with the references of `dayz-vehicles`. Then do a single rebuild and deploy (`/dayz-build-pbo`, then relaunch) and run the ladder again. One rebuild for all fixes makes each test in the game count for all the changes.
4. Each car has an iteration budget, 6 passes by default. If the ladder does not converge within it, escalate rather than loop.

### Which failures end the pass

- An R1 failure ends the pass: without an entity there is nothing to test. Fix it and spawn again.
- An R4 failure, including its conditioning step, ends the pass for R5 and R6: a car that is not seated and conditioned cannot be driven. Record it and skip R5 and R6.
- R2, R3 and R6 failures do not end the pass: record the fix and continue. In particular R3 (the get-in diagnosis) does not block R4 or R5. `vehicle_get_in_client` forces `StartCommand_Vehicle` and skips the checks of the get-in action, so a car that fails R3 (a human could not get in) can still be driven through MCP. That is a useful signal: the car drives through MCP but the player's get-in is broken, and the get-in fix is still needed for the product. Collect both signals in the same pass.

### Spawn placement

R3 and R4 pull one way and R5 the other, and placing the car wrong gives a false green or a false red.

- R3 (`query_get_in_condition`) and R4 (`vehicle_enter`, `vehicle_get_in_client`) need the car next to the player: check 7 measures the distance from the player to the door, and the client-side seat looks for a nearby vehicle.
- R5 needs a clear track ahead: an obstacle gives a misleading `pos_delta` near 0.
- Spawn the car at the player's position on open ground with at least 150 m clear in every direction it might face. The `world_spawn` argument `rotation` does not set a heading: it is the Central Economy rotation flag passed to `CreateObjectEx` (`iRotation`, `P:\scripts\3_game\global\game.c:703`; 0 leaves `RF_DEFAULT`, 512, `P:\scripts\3_game\ce\centraleconomy.c:66`), as `collision-probes.md` ("Axis-aligned fixtures") and `verb-gotchas.md` describe. A spawned car takes the orientation of the ground at its point, and no tool sets its heading, so choose the site rather than the direction. The airfield site certified in `vehicle-smoke.md` ("Ladder sessions") is a good start.
- A `pos_delta` near 0 may be a false red; do not conclude that the drivetrain is broken on the first reading. After R4 passes (seated, owner and conditioned) and R5 runs with throttle, if `pos_delta` is near 0:
  - If `vehicle_telemetry` shows `speedo_max` above 0, the gear shifts up on its own, or the engine revs (the RPM rises in the `[MCP-DRIVE]` log), the powertrain works and the car is blocked by an obstacle. Run R5 again with the car moved to clear ground (an offset like `tramoA_verbs_gate.py --dz 40`). If it then moves, the failure was an obstacle, not a model defect.
  - If `speedo_max` stays near 0, the engine does not rev and the wheels are not simulated, the wheel simulation or drivetrain is really broken, and that is an R5 fix.
  At the first SUB_BRZ gate, spawned at (6063, 1931), an obstacle stood in front: `pos_delta` read 0.15 to 0.25 with the engine at full throttle, and the same car on clear ground 40 m away drove 29 m. Ground truth is the test on clear ground, not the first reading.

### The ladder

| Rung | MCP verbs | Pass (ground truth) | Failure and its fix (taxonomy) |
|---|---|---|---|
| R1, spawns | `world_spawn(type, pos, rotation)` | `ok=1`, `found=1` and an entity with a `pos`. | `unknown_type` or `spawn_failed`: the mod is not mounted or `CfgPatches` does not register. Spawns but is invisible, or "action selection not found in geometry": componentNN (loose islands). |
| R2, solid and oriented render | `scene_raycast(from, to)` at several points, and `camera_set(cam_mode:"lookat")` with `capture_screenshot` from several angles | Rays hit where they should, and the render has no holes or inverted faces, the right orientation and a plausible scale. | A hole from one angle that is solid from the opposite one: per-part winding. A rotated or mirrored car: the orient transform. A wrong size: scale. A floating part or one rotated about 90 degrees: the proxy frame. |
| R2.5, restore gameplay | (the `lookat` camera does not disable the simulation; see below) | The simulation and controls are live before driving; the free camera is not used in this ladder. | If R4 or R5 does not respond with seated, owner and engine on, suspect the free camera or the simulation before the drivetrain. |
| R3, get-in available | `scene_raycast` in a ring for the `component`, then `query_get_in_condition(pos, component)` | The driver seat (`component_crew_index==0`) is `available=1` with `first_block=""`. A car where only a passenger seat is available cannot be driven by a human, so R3 fails. | The driver seat's `first_block` (see the "Failure to fix mapping" table). It does not block R4 or R5. |
| R3b, the real action on the HUD | `scene_raycast` down onto the seat, `player_teleport` and `player_look_at`, `action_cursor`, `action_use("ActionGetInTransport", component_index, cursor_pos)`, then `vehicle_telemetry` | The cursor slot shows `ActionGetInTransport` on the seat's component, then `seated=1`, from both sides and for each seat (see "R3b" below). | The slot is empty while R3 is `available=1`: the cursor is on another component or on the wrong side. R3 is `unreachable` on one side only: the door condition point is on one side. |
| R4, conditioned on the server | `vehicle_enter(pos, timeout_s=30)`, a raw `vehicle_drive {throttle: 0.01, duration: 0.5}`, then `telemetry_read(mode="object_at")` | `wheel_count` equals the car's wheel count and `fuel_fraction` is above 0. | `wheel_count` short: the car's `OnDebugSpawn` attaches no wheels, or an `Axles` override lists only one axle (`invariants-wheels-and-hubs.md`). Fuel 0: read `telemetry_read` again before concluding (`dayz-1-30-mcp-verify.md`), then check that `OnDebugSpawn` fills the tank. Blocks R5 and R6. |
| R4, seated (MCP) | `vehicle_get_in_client(pos)` | `seated=1`, `is_owner=1`, `vehicle_fixture_ready=1`. | `not_seated` or `seat_failed`: reachability, the seat animation or the crew bone. Blocks R5 and R6. |
| R5, drives | `engine_set("start")`, `vehicle_control(throttle:1, hold_ttl_s:12)` without calling it again, `vehicle_telemetry`, `vehicle_release` | `pos_delta` above 1.0 m, `speedo_max` above 0, `engine_on_server` and `is_owner`. Movement from gravity or inertia does not count. | `pos_delta` near 0 with the engine on and ownership: ambiguous, so test again on clear ground before mapping a fix (`needs_clear_ground_retest`). If it is still near 0 with the engine revving: the wheel simulation (FireGeo) or the drivetrain. |
| R6, wheels and direction | `vehicle_control(steer:-1)` with `vehicle_telemetry` samples, and optionally a `camera_set` in `lookat` mode | The car curves to the commanded side. The sign for left and right is not calibrated: the orchestrator reports `signed_cross`; confirm it against a vanilla reference car before concluding. | The car curves to the opposite side, or the wheels are mirrored: the sign of the wheel `angle` in `model.cfg`, or the `wheel_X_Y` naming. |

Fields the verbs return:

- `world_spawn`: `pos_real` and `pos`.
- `vehicle_get_in_client`: `seated`, `is_owner` and `vehicle_fixture_ready`.
- `vehicle_telemetry`: `speedo_max`, `gear`, `engine_on_server`, `pos`, `is_owner` and `net_strategy`.
- `telemetry_read(mode="object_at")`: `found`, `wheel_count` and `fuel_fraction`, among others.
- `query_get_in_condition` returns `get_in` with `available`, `partial`, `crew_size`, `component_crew_index`, `first_block` and `per_seat[]` (`crew_index`, `crew_can_get_through`, `area_free`, `occupied`, `reachable`).
- `scene_raycast` returns `raycast` with `hit` and `component`.

The signatures and fields were checked against the MCP schemas and against `tramoA_verbs_gate.py` and `tramoB_getin_gate.py`, which passed their gates in game.

### R2.5: restore gameplay

The camera and the get-in both touch the player's simulation, and doing them in the wrong order leaves the car inert while every other verb reads green, a classic false red. What was verified in `MCPClientBridge.c`:

- `camera_set` always suppresses the controls (`SuppressGameplay()`, `:1333`, which calls `PlayerControlDisable` and hides the HUD) but does not disable the simulation, except with `cam_mode="free"`, which calls `DisableSimulation(true)` (`:1335-1400`, `CAMERA_MODE_FREE`). The `lookat`, `orient` and `matrix` modes create a `staticcamera`, and the simulation stays live.
- `vehicle_get_in_client` (`ProcessVehicleGetInClientPrep`, `:919-1029`) does not restore the simulation. It seats the player (`StartCommand_Vehicle`, `:955`), runs the client-side conditioning (`OnDebugSpawn`, `:1006`) and takes ownership, but it does not call `RestoreGameplay()`. Besides the `restore_gameplay` lifecycle verb, which can answer `restore_unverified` (`skills/_shared/vehicles/test-stand-and-mcp.md`), the only client preparation that restores it is the one of the `drive_probe_client` gate (`ProcessDriveProbeClientPrep`, `RestoreGameplay()` at `:1042`); its definition at `:1808-1832` calls `DisableSimulation(false)` (`:1813`) and `PlayerControlEnable(true)` (`:1825`). So a simulation disabled by a free camera does not recover when R4 starts: the get-in hangs in `not_seated`, because a stopped player simulation never completes `HumanCommandVehicle`. The rule below is the dependable protection.
- The rule: for R2 and R6 always use `cam_mode="lookat"`. It is a static camera with a live simulation, and driving keeps working because the `MCPCarDrive.OnInput` holder applies the throttle, not the player's input. Do NOT use `cam_mode="free"` anywhere between R2 and R5. If R5 does not move with `seated=1`, `is_owner=1` and the engine on, first suspect a simulation disabled by a free camera (an R2.5 violation), not the drivetrain.

### R3b: the player's own get-in action (measured 2026-10-28)

R3 and R4 do not show what a player sees.
`query_get_in_condition` evaluates the checks of `ActionGetInTransport.ActionCondition` for the
component it is given, not for the one under the player's cursor; it also skips `CanGetIn()` and
calls `IsAreaAtDoorFree` where the action calls `IsAreaAtDoorFreeDiag`, so its `available=1` is
partial. The vanilla action checks `CanGetIn()` at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`,
`CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` at `actiongetintransport.c:54` and `CanReachSeatFromDoors` at
`actiongetintransport.c:64`. `vehicle_enter` and
`vehicle_get_in_client` seat the player without the action. Arma2Quad v1.0.1 was seated that way
in its 2026-10-26 tests; on 2026-10-28 its right side turned out to have no get-in action for
either seat (the one-sided get-in finding in `skills/_shared/vehicles/dayz-1-30-vehicles.md`). The rung that matches the player,
run from both sides and for each seat:

1. Seat component: `scene_raycast(intersect="view")` straight down onto the top of the seat
   (Arma2Quad: 16 driver, 18 co-driver). A horizontal ray at seat height hit the rear fender
   (component 31) first.
2. R2 leaves the `camera_set("lookat")` script camera on, and while it is active `player_look_at`
   returns `script_camera` (`MCPClientBridge.c:6758`): send `restore_gameplay` and wait for its
   response first. Then stand within 1 m of the seat's door condition point and `player_look_at` the top of the seat.
   The aim converged up to about 42 degrees off the body heading; targets at 60 and 76 degrees
   ended in `deadline` and the view went back to the body heading, which `player_teleport` does not
   change. Place the player so the seat lies within about 40 degrees of
   the current heading, for example behind-left or behind-right of a vehicle that faces the same way.
3. `action_cursor`: PASS when `cursor.slots.continuous_primary.action_class` is
   `ActionGetInTransport` and `cursor.target.component_index` is the seat's component. On screen the
   prompt sits under the vehicle's name (`Entrar [MANTENER]` in a Spanish client).
4. `action_use("ActionGetInTransport", classname=<type>, component_index=<from action_cursor>,
   cursor_pos=<from action_cursor>)`, then `vehicle_telemetry`: PASS when `seated=1` on the expected
   seat. Without `pos`, `action_use` picks the nearest matching object, not the one under the cursor
   (`MCPClientBridge.c:4094`): pass `pos`/`radius` tied to the object `action_cursor` observed and
   check that the seated vehicle is that instance, or keep a single instance of the type in range.
   `action_use("ActionGetOutTransport", target="self")` got the player off again.

A build whose scripts did not load shows here as well: `telemetry_read object_at` reports
`class_name="CarScript"` instead of the mod's script class, the cursor shows only the vehicle's
name, and R3 stops at `crew_can_get_through`. Seen with the Arma2Quad Workshop copy of 2026-10-27,
which was the v1.0.0 PBO (`World` 2343 files on 1.30.164200, against 2348 with v1.0.1).

### Guardrails against a false green

These three rules always apply.

1. A failure outside the known taxonomy means stop and escalate. Do not rebuild blindly. The ladder maps known symptoms; a new symptom means something needs to be understood, not that you should iterate at random.
2. The verdict comes from the game, never from an offline proxy. An offline audit can filter before a rebuild: `skills/dayz-vehicles/scripts/audit_getin_wheels.py`, and the `rip_p5_gate.py --cull` gate, which is not shipped in this repo but lives in your own vehicle-import workspace (`<vehicle-import>` in `rip-import.md`, "PHASE 5"). The rung's verdict is still the reading in the game. Offline checks have given a false green twice, on MercedesAMGLF and on SUB_BRZ.
3. Keep an iteration budget and a journal for each pass. Each pass gets its own folder, `<TargetMod>_dev\_ladder\run_<n>\`, with a new `<n>` per pass: run `drive_ladder.py` with `--journal <TargetMod>_dev\_ladder\run_<n>` so its `verdict.json` (the rung reached, `first_block`, `pos_delta`, the telemetry it read and the mapped fix) lands there, and save the R2 and R6 PNGs of that pass in the same folder. Without `--journal` the script writes `.\_ladder\<vehicle>\verdict.json` in the current directory, and the next pass overwrites it. One folder per pass lets each green be inspected and each red traced.

### Failure to fix mapping (SUB_BRZ taxonomy, pointing into the vehicles pack in `skills/_shared/vehicles/`)

| Symptom or signal | Rung | Fix (where to read it) |
|---|---|---|
| `world_spawn` returns `unknown_type` or `spawn_failed` | R1 | The mod is not mounted or `CfgPatches` does not register it: `skills/dayz-test-ingame/references/windows-launch-cycle.md` ("MOD PATHS MUST BE ABSOLUTE"). Not a model bug. |
| Spawns but is invisible, or "action selection X not found in view/fire geometry" | R1 | componentNN dual tag: `vehicle-structural-parity.md` ("componentNN DUAL-TAG") and `rip-import.md`. Hubs and seats are islands with 0% overlap, so the collision enumerator does not see them; each hub and seat also carries a `componentNN` selection on the same faces. |
| A hole from one angle, solid from the opposite one | R2 | Per-part winding, not a global flip (a global flip gave a false green): `rip-import.md`. The lasting fix orients each part to the normal of the source model; the offline gate is `rip_p5_gate.py --cull` in your vehicle-import workspace. |
| The car is rotated or mirrored, or a part floats or is rotated about 90 degrees | R2 | The body's orient transform, or the proxy frame `R=((-1,0,0),(0,0,1),(0,1,0))`: `dayz-vehicles` (proxies). This is the Mercedes convention; py3d with `rotation=None` renders the part about 90 degrees rotated. |
| `first_block="componentNN"` (`component_crew_index<0`) | R3 | componentNN on the seats (the same fix as the invisible R1 case): the seat is not enumerated as a crew component. |
| `first_block="crew_can_get_through"` | R3 | A bare `class X: CarScript` inherits `Transport.CrewCanGetThrough()=false`: `rip-import.md`. The fix extends `CarScript` with overrides of `CrewCanGetThrough`, `GetSeatAnimationType` and `GetAnimInstance`, and adds `worldScriptModule` in `CfgMods`. Doors are not required. |
| `first_block="area_blocked"` (check 6b) | R3 | `IsAreaAtDoorFree` is false: something obstructs the door area, or the door selection is wrong. |
| `first_block="unreachable"` (check 7) | R3 | `CanReachSeatFromDoors` is false: the seat and door geometry, or the car is too far from the player. Move the player next to the car before concluding that the model needs a fix. |
| The `action_cursor` slot is empty while R3 is `available=1` | R3b | R3's diagnosis is partial: it skips `CanGetIn()` and uses `IsAreaAtDoorFree`, while the action checks `CanGetIn()` and `IsAreaAtDoorFreeDiag` (for example a fallen motorbike, `P:\scripts\4_world\entities\vehicles\motorbikescript.c:225`). A candidate, not a proven cause: the cursor is on another component (fender, body). Aim at the top of the seat and compare `cursor.target.component_index` with the seat's component. |
| R3 `unreachable` from one side only | R3b | A candidate: the door condition points sit on one side (seen on Arma2Quad at the tested positions only): `skills/_shared/vehicles/dayz-1-30-vehicles.md` (the one-sided get-in finding). |
| `telemetry_read` reports `class_name="CarScript"` and R3 stops at `crew_can_get_through` | R3 | The mod's scripts did not load. Compare `Module: World; loaded Nx files` with a run without the mod (`skills/_shared/vehicles/dayz-1-30-vehicles.md`, the script module path finding: backslashes in `files[]` load nothing on 1.30). |
| `first_block="occupied"`, `"item_heavy"` or `"already_in_vehicle"` | R3 | The state of the harness, not a model bug: spawn a clean car, drop the heavy item from the hands, or get out of the vehicle first. |
| `first_block="no_component"` (`partial=1`) | R3 | `component=-1` was passed. Take a real `component` from a `scene_raycast`; without it the diagnosis is partial and never a pass. |
| `wheel_count` short or `fuel_fraction` 0 after the server-side conditioning | R4 | The car's `OnDebugSpawn` attaches no wheels, or an `Axles` override lists only one axle (`invariants-wheels-and-hubs.md`, "Every axle must be listed in an Axles override"). For fuel, read `telemetry_read` again first: the bridge can read the tank in the tick of the `Fill()` (`dayz-1-30-mcp-verify.md`). |
| `vehicle_get_in_client` returns `not_seated` or `seat_failed` | R4 | Get-in latency (raise `prep_deadline`), the crew bone or selection, or the seat animation type: `vehicle-config-and-modelcfg.md`. The crew proxy needs both a selection in the geometry and a bone in `CfgSkeletons`, or the get-in breaks. |
| `pos_delta` near 0 after an obstacle is ruled out | R5 | Wheel simulation (FireGeo): `rip-import.md` (the face of each wheel proxy also in the visual `wheel_X_Y`, `wheel_X_Y_damper` and, at the front, `wheel_X_1_steering`) and `vehicle-structural-parity.md` (hubs as faces and componentNN in the Geometry LOD); or the drivetrain in `config.cpp`. |
| The car curves opposite to the commanded `steer`, or the wheels are mirrored | R6 | The sign of the wheel `angle` in `model.cfg` (`vehicle-config-and-modelcfg.md`) and the `wheel_X_Y` naming (`rip-import.md`: the first index is the side, 1 = +x and 2 = -x; the second is the axle, 1 = front; watch the mirroring between the Mercedes and sedan conventions). |

### Reference orchestrator

`references/drive_ladder.py` drives R1 to R6 against the daemon on port 8765 with raw `/enqueue` and `/await` calls, the same verified pattern as `tramoA_verbs_gate.py` and `tramoB_getin_gate.py`.

- It needs a live lease. Adopt the run with `session_acquire_wait` from your MCP session and pass the identity and lease token it returned (`--identity` and `--lease-token`, or the `DAYZ_MCP_IDENTITY` and `DAYZ_MCP_LEASE_TOKEN` environment variables); the script sends them in every `/enqueue` body next to `?key=` (`vehicle-smoke.md`). It does not renew the lease, so keep sending `session_heartbeat` from your session at least every 90 s while it runs. A fence rejection (`run_not_owned`, `lease_expired`, `lease_invalid`) stops the script at once with that error.
- It stops at the first failure that ends the pass, or collects the failures that do not, and writes `verdict.json` naming the rung, the `first_block` and the mapped fix into the `--journal` folder (pass a new `<TargetMod>_dev\_ladder\run_<n>` each pass, guardrail 3).
- It does not apply fixes or rebuild; that is the loop of the agent or a human (guardrail 1).
- It reports `objective_PASS` for the rungs a script can close. Real acceptance also needs the agent's visual rungs (R2_visual for winding, orientation and scale, and the R6 turn calibration), which the script cannot close.
- Its safeguards: R3 checks the driver seat, not any seat. `R4_conditioned` seats the player on the server, runs `OnDebugSpawn` there and requires `wheel_count` (`--wheels`, 4 by default) and fuel. R4 fails closed on seated, owner and fixture ready. A preflight aborts if the player is already in a car, since a second run would measure the old one. R5 requires the engine on and ownership, and reports `needs_clear_ground_retest` instead of guessing between an obstacle and the drivetrain. Each verb is checked for a timeout and for `ok`, because a harness failure is not a model fix.
- Offline fixtures: `tests/test_drive_ladder.py` (12 tests).

Verification status: each rung reuses a verb sequence that passed its own gate in game. The chain of R1 to R6 in a single run is the very test in the game the ladder exists to run, and it has not been gated as a unit. The script compiles and its offline fixtures pass. The server-side conditioning step and the lease arguments follow `vehicle-smoke.md` and `run-lifecycle.md` and have not yet been run through this script in game.
