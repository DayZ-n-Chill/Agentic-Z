# Acceptance ladder: from a ripped model to a drivable car

The full ladder for accepting a drivable car through the dayz-mcp bridge: the owner-side driving verbs, rungs R1 to R6, the table that maps each failure to its known fix (the "SUB_BRZ taxonomy", named after the car it was built on), and what the `drive_ladder.py` orchestrator in this folder does.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game sessions with that tool; it is not yet checked on `P:\` except where a vanilla file is cited. `MCPClientBridge.c`, `MCPBridge.c` and `MCP_CarScript.c` are files of the `@DayZ_MCP` mod and their line numbers are from the time of the measurement; `<dayz-mcp>` is the folder of your dayz-mcp checkout. File names such as `rip-import.md`, `vehicle-structural-parity.md`, `vehicle-config-and-modelcfg.md` and `dayz-1-30-vehicles.md` are files of the vehicles pack in `skills/_shared/vehicles/`, which the `dayz-vehicles` skill reads; search those files for the quoted term.


## DRIVABILITY: available owner-side driving verbs (added 2026-06-28)

Phase 5 of the DayZ-MCP project added and in-game gated a surface of composable verbs that do drive the car
owner-side (client takes ownership and handles throttle/steer). MCP tools (all **client** peer except the last,
which is server):

| MCP Tool | What it does |
|---|---|
| `vehicle_get_in_client(pos)` | seats client in car near `pos` (takes ownership + conditions fuel/battery); returns `seated`/`is_owner`/`vehicle_fixture_ready` |
| `engine_set(mode)` | `"start"`/`"stop"` engine of owner-car |
| `vehicle_control(throttle, steer, brake, handbrake, hold_ttl_s)` | sets sustained control (car keeps driving without re-calling, until `vehicle_release` or deadman `hold_ttl_s`); fail-closed (range+NaN) |
| `vehicle_telemetry()` | speed/gear/engine/pos/`is_owner`/net_strategy of owner-car |
| `vehicle_release()` | releases sustained control |
| `query_get_in_condition(pos, component=-1)` (**server** peer) | diagnoses whether normal get-in would be available and which of the 7 gates of `ActionGetInTransport` blocks; `component` = index from a prior `scene_raycast` (mandatory for an `available` verdict; without it → `partial`, never PASS) |

**Mechanism (do not re-investigate, verified in-game):** client takes ownership with `StartCommand_Vehicle`
client-side (`OnVehicleSeatDriverEnter`→`Possess(car)`, under `FEATURE_NETWORK_RECONCILIATION`); owner-side driving
requires applying `SetThrottle/SetSteering` inside `CarScript.OnInput` after `super` (a `modded class CarScript` in the
MCP PBO - `Car.SetThrottle` from mission is overwritten by `super.OnInput` with driver's input=0). The static holder
`MCPCarDrive` + deadman carries state. See the `dayz-vehicles` skill.

**Acceptance ladder (already wired - see "ACCEPTANCE LADDER" below):** with these verbs rungs that were previously
"manual" are now automatable - R3 get-in available (`query_get_in_condition` with `component` from a raycast →
`available`/`first_block`), R4 seated (`vehicle_get_in_client` → `seated`/`is_owner`), R5 drives
(`engine_set`+`vehicle_control`+`vehicle_telemetry`+`vehicle_release` → `pos_delta` grows), R6 wheel direction
(`vehicle_control{steer}` + visual). Verified gate caveats: (a) to measure driving `pos_delta`, spawn
car in clear area (offset; an obstacle in front gives misleading pos_delta≈0); (b) `query_get_in_condition` requires
car next to player (gate 7 reachability measures player↔door). Reference gate drivers (raw enqueue):
`<dayz-mcp>/tools/tramoA_verbs_gate.py` and `<dayz-mcp>/tools/tramoB_getin_gate.py`.

## ACCEPTANCE LADDER: rip → drivable car (added 2026-06-28)

The orchestrator walks an ordered ladder of **rungs**; each rung reads **in-game ground-truth** with the verbs from
above (DRIVABILITY section); each failure maps to a **known fix in the SUB_BRZ taxonomy** (in the
`dayz-vehicles` skill and the vehicles pack in `skills/_shared/vehicles/`). Goal: iterate a car (source-game rip → drivable) without human
in game, **stopping and escalating** as soon as a failure falls outside known taxonomy.

**When**: after visual smoke (the vehicle playbook in `playbooks.md` already left game launched, bridge
green, and car loading). The ladder is the **driving** extension of the smoke: starts where
smoke ends (entity spawns + is seen) and reaches "drives and turns to the correct side".

### Preconditions (inherited - do NOT re-do here)
- **Launch + readiness + green `bridge_status`**: the vehicle playbook and `bridge-setup.md` (stock mission, bridge
  seed, `-PackOnly`, wait for CE, flaky capture). The ladder assumes both peers `version_state=ok` and the
  player spawned (`query_player_state` returns `pos`).
- **Exclusive DayZ box** between agent sessions (hard precondition, see `run-lifecycle.md`, "The test machine is one shared resource"). A single session.
- **Verb surface built and in-game gated** (DRIVABILITY section). The ladder does not build
  bridge: it drives it.

### How it is traversed (the iteration loop)
1. Position the car (see "Spawn placement") and walk **R1→R6 in order**.
2. On each FAIL rung, **classify**: is the symptom in the SUB_BRZ taxonomy ("Failure→fix mapping" table)?
   - **Yes** → record the rung + mapped fix in the journal and **continue** collecting signal from rungs
     that are still reachable (see "hard-block vs soft" below). Do not rebuild midway through pass.
   - **No** (failure outside taxonomy) → **STOP and escalate** (guardrail 1). Do not blindly rebuild.
3. At end of pass: **batch** of all recorded fixes → agent applies them to `.p3d`/config
   (human/agent loop, not scripted: read screenshots + edit geometry/config with refs from
   `dayz-vehicles`) → **a single** rebuild+deploy (`/dayz-build-pbo`, then relaunch) → re-run the
   ladder. Grouping all fixes into one rebuild makes each in-game test count for all changes.
4. **Iteration budget** per car (default 6 passes; if it does not converge → escalate, no infinite loop).

**Hard-block vs soft (what cuts the pass):**
- **R1 fail = hard** (without entity there is nothing to test) → stop pass, fix, re-spawn.
- **R4 fail = hard for R5/R6** (without seating no driving) → record, skip R5/R6.
- **R2, R3, R6 = soft**: record fix and continue. In particular **R3 (diagnostic get-in) does not block
  R4/R5**: `vehicle_get_in_client` (R4) **forces** `StartCommand_Vehicle` and skips radial
  gates → a car with R3 FAIL (a human could not enter) can still be driven via MCP. That is a
  valuable signal: "drives via MCP but player get-in is broken" → the get-in fix remains
  necessary for the product. Collect both signals in the same pass.

### Spawn placement (R3/R4 ↔ R5 tension - resolving it wrong gives false green/red)
- **R3 `query_get_in_condition` and R4 `vehicle_get_in_client` require the car next to player** (gate 7
  reachability measures player↔door; client-side seat looks for nearby transport).
- **R5 (driving) requires clear track ahead** (an obstacle gives misleading `pos_delta≈0`).
- **Unified resolution**: spawn car **at player position, on open ground**, oriented
  (`world_spawn` arg `rotation`) toward free space. Thus R3/R4 have reachability and R5 has track.
- **Mandatory disambiguation of `pos_delta≈0`** (candidate false-red, do not conclude drivetrain on
  first try): after R4 OK (seated+is_owner) + R5 with throttle, if `pos_delta≈0`:
  - `vehicle_telemetry` with `speedo_max>0` / gear auto-upshifted / engine revs (`[MCP-DRIVE]` log RPM
    rises) → powertrain works, car is **blocked** (obstacle) → **re-run R5 only** with
    car relocated to clear ground (offset like `tramoA_verbs_gate.py --dz 40`). If it then moves,
    it was obstacle (false-red), not a model fix.
  - `speedo_max≈0` + no revs + unsimulated wheels → **real drivetrain/wheel-sim** → R5 fix.
  The gate of the first SUB_BRZ spawn (6063,1931) had obstacle: `pos_delta` 0.15-0.25 with engine at max;
  cleared offset +40m gave 29 m. Ground-truth = re-test on clear ground, not first reading.

### The ladder

| Rung | MCP Verb(s) | PASS (ground-truth) | FAIL → fix (taxonomy) |
|---|---|---|---|
| **R1 spawns** | `world_spawn(type, pos, rotation)` | `ok=1`, `found=1`, entity with `pos` | `unknown_type`/`spawn_failed` → mod not mounted / `CfgPatches`. Spawns but invisible / "action selection not found in geometry" → **componentNN** (loose islands) |
| **R2 solid+oriented render** | `scene_raycast(from,to)` (N points) + `camera_set(cam_mode:"lookat")`+`capture_screenshot` (N angles) | solid rays where they should hit + visual without holes/inverted faces, oriented, plausible scale | hole from one angle / solid from opposite → **per-part winding**. Rotated/mirrored car → **orient transform**. Bad size → **scale**. Floating/rotated ~90° part → **proxy frame** |
| **R2.5 restore-gameplay** | (lookat does not disable sim; see below) | live sim+controls before driving; **freecam forbidden in this ladder** | if R4/R5 do not respond with seated+owner+engine → suspect freecam/sim, not drivetrain |
| **R3 get-in available** | `scene_raycast` (ring) → `component` → `query_get_in_condition(pos, component)` | **driver** seat (`component_crew_index==0`) is `available=1` (`first_block=""`). A car with only passenger available is not drivable by a human → R3 FAIL | the `first_block` of driver ("Failure→fix mapping" table). Soft: does not block R4/R5 |
| **R3b real action (HUD)** | `scene_raycast` (down onto the seat) → `player_teleport` + `player_look_at` → `action_cursor` → `action_use("ActionGetInTransport", component_index, cursor_pos)` → `vehicle_telemetry` | cursor slot `ActionGetInTransport` on the seat's component, then `seated=1`: **from both sides, for each seat** (see R3b below) | slot empty while R3 is `available=1` → cursor on another component or on the wrong side; R3 `unreachable` on one side only → one-sided door condition point |
| **R4 seated (MCP)** | `vehicle_get_in_client(pos)` | `seated=1`, `is_owner=1`, `vehicle_fixture_ready=1` | `not_seated`/`seat_failed` → reachability / seat anim / crew bone. Hard for R5/R6 |
| **R5 drives** | `engine_set("start")` → `vehicle_control(throttle:1, hold_ttl_s:12)` → [do not re-call] → `vehicle_telemetry` → `vehicle_release` | `pos_delta>1.0` m + `speedo_max>0` + `engine_on_server` + `is_owner` (movement by gravity/inertia does not count) | `pos_delta≈0` with engine+owner → ambiguous: **mandatory re-test on clear ground** before mapping fix (`needs_clear_ground_retest`); if still ~0 with revving engine → **wheel sim (FireGeo)** / drivetrain |
| **R6 wheels/direction** | `vehicle_control(steer:-1)` + `vehicle_telemetry` sampling (+ optional `camera_set` lookat) | car curves to commanded side - but left/right sign is uncalibrated: orchestrator reports `signed_cross`, confirm vs vanilla ref car before concluding | curves to opposite side / mirrored wheels → **model.cfg wheel `angle` sign** / **naming `wheel_X_Y`** |

`world_spawn` result: `pos_real`/`pos`. `vehicle_get_in_client`: `seated`/`is_owner`/`vehicle_fixture_ready`.
`vehicle_telemetry`: `speedo_max`/`gear`/`engine_on_server`/`pos`/`is_owner`/`net_strategy`.
`query_get_in_condition` → `get_in`: `available`/`partial`/`crew_size`/`component_crew_index`/`first_block`/
`per_seat[]{crew_index, crew_can_get_through, area_free, occupied, reachable}`. `scene_raycast` →
`raycast`: `hit`/`component`. (Signatures and fields verified against MCP schemas + `tramoA_verbs_gate.py`/
`tramoB_getin_gate.py` that gated PASS in-game.)

### R2.5 - restore-gameplay (mechanism verified, not hand-waved)
Camera and get-in touch player simulation; doing so in the wrong order leaves car inert with
all other verbs green (classic false-red). What was verified in `MCPClientBridge.c`:
- **`camera_set` always suppresses controls** (`SuppressGameplay()`, `:1333` → `PlayerControlDisable` +
  hides HUD) but does **not** disable sim - except `cam_mode="free"`, which calls `DisableSimulation(true)`
  (`:1335-1400`, `CAMERA_MODE_FREE`). `lookat`/`orient`/`matrix` create a `staticcamera`: **live sim**.
- **The `vehicle_get_in_client` verb (R4, `ProcessVehicleGetInClientPrep` `:919-1029`) does not restore sim**:
  does seat (`StartCommand_Vehicle` `:955`) + conditioning (`OnDebugSpawn` `:1006`) + captures ownership, but
  **does not call `RestoreGameplay()`**. The only client PREP that restores is that of the `drive_probe_client` gate
  (`ProcessDriveProbeClientPrep`, `RestoreGameplay()` `:1042`); def `:1808-1832` → `DisableSimulation(false)`
  `:1813` + `PlayerControlEnable(true)` `:1825`. Consequence: a sim disabled by a freecam **does not heal
  itself on entering R4** - get-in would hang in `not_seated` (stopped player sim does not complete
  `HumanCommandVehicle`). The only protection is the rule below.
- **Ladder rule**: for R2 and R6 use **always `cam_mode="lookat"`** (staticcamera, live sim,
  driving keeps working because throttle is applied by the `MCPCarDrive.OnInput` holder, not player
  input). **NEVER `cam_mode="free"` between R2 and R5.** If R5 does not move with `seated=1`+`is_owner=1`+
  `engine_on`, first suspect is a freecam-disabled sim (R2.5 violation), not drivetrain.

### R3b - the player's own get-in action (measured 2026-10-28)

R3 and R4 do not show what a player sees.
`query_get_in_condition` evaluates the gates of `ActionGetInTransport.ActionCondition` for the
component it is given, not for the one under the player's cursor; it also skips `CanGetIn()` and
calls `IsAreaAtDoorFree` where the action calls `IsAreaAtDoorFreeDiag`, so its `available=1` is
partial. The vanilla action checks `CanGetIn()` at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`,
`CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` at `actiongetintransport.c:54` and `CanReachSeatFromDoors` at
`actiongetintransport.c:64`. `vehicle_enter` /
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

### Guardrails against a false green (not negotiable)
1. **Failure outside known taxonomy → STOP and escalate.** Do not blindly rebuild. The ladder maps
   known symptoms; a new symptom is a sign that something needs to be understood, not of iterating at random.
2. **Gate is in-game ground-truth, never offline proxy.** An offline audit (`rip_p5_gate.py --cull`,
   `audit_getin_wheels.py`) pre-filters before rebuild, but rung verdict is the in-game
   reading. Offline gives false-green (proven 2× on MercedesAMGLF/SUB_BRZ).
3. **Iteration budget + journal per cycle.** Each pass writes `verdict.json` (reached rung,
   `first_block`, `pos_delta`, mapped fix) + R2/R6 PNGs + telemetry, to
   `<TargetMod>_dev\_ladder\run_<n>\`, so that each green is **inspectable** and each red traceable.

### Failure → fix mapping (SUB_BRZ taxonomy → the vehicles pack, `skills/_shared/vehicles/`)

| Symptom / signal | Rung | Fix (anchor) |
|---|---|---|
| `world_spawn` `unknown_type`/`spawn_failed` | R1 | mod not mounted / `CfgPatches` does not register - `skills/dayz-test-ingame/references/windows-launch-cycle.md` ("MOD PATHS MUST BE ABSOLUTE"), not a model bug |
| Spawns but invisible / "action selection X not found in view/fire geometry" | R1 | **componentNN dual-tag**: `vehicle-structural-parity.md` "componentNN DUAL-TAG" + `rip-import.md` (hubs/seats = islands with 0% overlap → invisible to collision enumerator; each hub/seat also carries a `componentNN` on same faces) |
| Hole from one angle, solid from opposite | R2 | **per-part winding** (not global flip - was false-green): `rip-import.md`; permanent fix = orient to source authorized normal; offline gate = `rip_p5_gate.py --cull` |
| Rotated/mirrored car, or part floating/rotated ~90° | R2 | body **orient transform** / `R=((-1,0,0),(0,0,1),(0,1,0))` **proxy frame** - `dayz-vehicles` (proxies) (Mercedes convention; py3d `rotation=None` renders ~90° rotated) |
| `first_block="componentNN"` (`component_crew_index<0`) | R3 | **componentNN** on seats (same fix as invisible R1): seat is not enumerated as crew component |
| `first_block="crew_can_get_through"` | R3 | **bare `class X: CarScript`** inherits `Transport.CrewCanGetThrough()=false`: `rip-import.md`; fix = `extends CarScript` with `CrewCanGetThrough`+`GetSeatAnimationType`+`GetAnimInstance` override + `worldScriptModule` in `CfgMods` (doors not required) |
| `first_block="area_blocked"` (gate 6b) | R3 | `IsAreaAtDoorFree` false → door area obstruction / door selection |
| `first_block="unreachable"` (gate 7) | R3 | `CanReachSeatFromDoors` false → seat↔door geometry, or **car too far from player** (move adjacent before concluding model fix) |
| `action_cursor` slot empty while R3 is `available=1` | R3b | partial diagnosis: R3 skips `CanGetIn()` and uses `IsAreaAtDoorFree`, the action checks `CanGetIn()` + `IsAreaAtDoorFreeDiag` (e.g. a fallen motorbike, `P:\scripts\4_world\entities\vehicles\motorbikescript.c:225`). Candidate, not proven cause: the cursor is on another component (fender, body): aim at the top of the seat and compare `cursor.target.component_index` with the seat's component |
| R3 `unreachable` from one side only | R3b | candidate: the door condition points sit on one side (seen on Arma2Quad at the tested positions only): `skills/_shared/vehicles/dayz-1-30-vehicles.md` (the one-sided get-in finding) |
| `telemetry_read` `class_name="CarScript"` and R3 `crew_can_get_through` | R3 | the mod's scripts did not load: compare `Module: World; loaded Nx files` with a run without the mod (`skills/_shared/vehicles/dayz-1-30-vehicles.md`, the script module path finding: backslashes in `files[]` load nothing on 1.30) |
| `first_block="occupied"` / `"item_heavy"` / `"already_in_vehicle"` | R3 | harness state, not model bug: clean re-spawn / drop heavy item from hands / exit vehicle first |
| `first_block="no_component"` (`partial=1`) | R3 | passed `component=-1`: obtain real `component` from a `scene_raycast`; without it diagnosis is partial, never PASS |
| `vehicle_get_in_client` `not_seated`/`seat_failed` | R4 | get-in latency (increase `prep_deadline`) / crew bone-selection / seat anim type - `vehicle-config-and-modelcfg.md` (crew proxy = selection in geometry **and** bone in `CfgSkeletons`, both or get-in breaks) |
| `pos_delta≈0` (after ruling out obstacle) | R5 | **wheel sim (FireGeo)**: `rip-import.md` (face of each wheel proxy also in visual `wheel_X_Y` + `wheel_X_Y_damper` + front `wheel_X_1_steering`) + `vehicle-structural-parity.md` (hubs as faces + componentNN in Geometry); or drivetrain in config.cpp |
| Curves opposite to commanded `steer` / mirrored wheels | R6 | **model.cfg wheel `angle` sign** (`vehicle-config-and-modelcfg.md`) + **naming `wheel_X_Y`** (`rip-import.md`: 1st index = side 1=+x/2=−x, 2nd = axle 1=front; watch Mercedes vs sedan mirroring) |

### Reference orchestrator
`references/drive_ladder.py` - drives R1→R6 against daemon `:8765` (raw `/enqueue`+`/await`, same verified
pattern of `tramoA_verbs_gate.py`/`tramoB_getin_gate.py`), stops on first hard-fail or after collecting
soft-fails, and emits `verdict.json` naming the rung, `first_block`, and mapped fix. It does **not** apply fixes
or rebuild (that is the agent/human loop, guardrail 1). Reports `objective_PASS` (scriptable rungs);
real **acceptance** also requires agent visual rungs (R2_visual winding/orient/scale, R6
turning calibration), which script does not close. Hardening: R3 gates
the driver seat (not just any), R4 fail-closed (seated+owner+fixture), a preflight aborts if
player is already in a car (re-run would measure the old one), R5 requires engine_on+owner and emits
`needs_clear_ground_retest` instead of guessing obstacle/drivetrain, each verb checks timeout/ok (a harness
failure is not a model fix). Offline fixtures `tests/test_drive_ladder.py` (9 PASS scenarios).
Honest verification status: each rung reuses a verb sequence already gated separately in-game; the
R1→R6 chain in a single run is the very in-game test the ladder exists to run (not gated
as a unit). `py_compile` + fixtures OK.
