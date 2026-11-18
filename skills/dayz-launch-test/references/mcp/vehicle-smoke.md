# Vehicle smoke test and driving bench

How to run a repeatable visual smoke test of a `CarScript` vehicle through dayz-mcp, give a spawned car real wheels and fluids, read what a bare spawn shows, and keep a driving bench honest.

The verbs belong to the third-party dayz-mcp tool. Their behaviour and every number here were measured in game with it and are not checked on `P:\`; `MCPBridge.c` lines are dayz-mcp's own source and `<dayz-mcp>` is your checkout. Vanilla facts cite the vanilla file. The drive checks themselves, in order, with the fix for each failure, are in `vehicle-acceptance.md`.

## Smoke test, step by step

1. Mission: the stock `dayzOffline.chernarusplus` from the DayZ Server install. A test mission with an empty `main()` creates no player, so the client draws no world and the capture is black. The stock mission creates the player, which gives a free camera over a drawn world.
2. Seed the bridge config before the launch. `dayz_mcp.json` with `{"url":"http://127.0.0.1:8765/","key":"<key>","pollHz":5}` (ASCII) goes in the server and client profile folders of the run. The bridge reads it once, at init, from `$profile:` (server `MCPBridge.c:125`, client `MCPClientBridge.c:211`); the key is `<dayz-mcp>\tools\.dayz_mcp.key`. Do not use `install-mcp.ps1 -Register` for this: it registers the broker mode (`--client`) again. More in `bridge-setup.md`.
3. Launch with `dayz_test_run`: mode `all`, a build when the PBO changed, `extra_mods=["@DayZ_MCP"]` and the stock mission (`run-lifecycle.md`). A mod with `.c` files needs a pack-only build when binarizing would drop them; the symptom was `NO_IGNITER`.
4. Wait for the Central Economy. The stock mission loads it for 1 to 3 minutes and the bridge reads stale meanwhile; do not spawn yet (`bridge-setup.md`, "During the Central Economy load the bridge looks stale").
5. Run the smoke in one batch. `world_time_set(year, month, day, hour=12, minute=0)` (all five required) and `world_weather_set(overcast=1.0)`; `world_spawn` the class about 10 m from the player; wait 30 s, which rules out a crash on spawn; then `camera_set` (mode `"lookat"` with `cam_pos` and `look_at`), `capture_screenshot`, `scene_raycast` and `telemetry_read(mode="object_at")`. Healthy telemetry is `found=1`, `health01=1`, velocity 0.
6. A flaky capture (loading screen, menu, a frame flat everywhere) is handled in `captures.md`, which also has the top-down pose for proxy alignment. When the render is ambiguous, the user's eye outranks the capture (`playbooks.md`, "The report").
7. Port 2302 and the Steam client are shared (`run-lifecycle.md`, "The test machine is one shared resource").
8. `legacy_blocked` right after launch is usually an unfinished init (`bridge-setup.md`).

"The wheels are a flat disc" is not a proxy bug; see "A bare spawn shows the undercarriage" below.

## Seating and driving: which verb does what

| Verb | What it does |
|---|---|
| `vehicle_enter(pos)` | Seats the player on the server and returns `seated=true`. It confirms placement and the seat, nothing more. |
| `vehicle_get_in_client(pos)` | Seats the player and gives the client ownership, so the client handles throttle and steering. |
| `engine_set("start" \| "stop")` | Starts or stops the engine. |
| `vehicle_control(throttle, steer, brake, handbrake, hold_ttl_s)` | Holds the controls for a while and fails closed. |
| `vehicle_telemetry()`, `vehicle_release()` | Reads the drive state; hands the car back. |
| `query_get_in_condition(pos, component)` | Runs on the server and names the check that blocks a get-in. It covers `ActionGetInTransport` only in part: it skips `CanGetIn()` and calls `IsAreaAtDoorFree` where the action calls `IsAreaAtDoorFreeDiag`, so its `available=1` is partial. The vanilla `ActionCondition` is at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26`. |

The drive checks run on top of these, in order: spawns, renders, get-in available, seated, drives, wheels turn the right way. Each reads the truth in game and points its failure at a known fix in the vehicle pack. `skills/dayz-launch-test/scripts/run_vehicle_checks.py` runs them and writes `verdict.json`; it applies no fix and rebuilds nothing, and its test data is in `test_run_vehicle_checks.py` beside it.

The gear index in `vehicle_telemetry` is 0 reverse, 1 neutral, 2 first and so on, so sixth is 7: the order of the vanilla `CarGear` enum, which goes on to `TENTH` (`P:\scripts\3_game\vehicles\car.c:32`).

## Giving a spawned car wheels and fluids

`vehicle_get_in_client` runs `OnDebugSpawn` on the client, which does nothing under server authority. The misleading sign is `vehicle_fixture_ready=1` with `wheel_count=0` and `fuel=0` in the server telemetry.

To fit wheels and fill fluids for real without touching code:

1. `vehicle_enter(pos)`, the server-side seat.
2. A raw enqueue of `vehicle_drive {throttle: 0.01, duration: 0.5}`. Its preparation runs `car.OnDebugSpawn()` on the server (`MCPBridge.c:2104` to `:2112`), and the half-second drive is negligible. A vanilla car's `OnDebugSpawn` is what fills the fluids and attaches the wheels, for example `P:\scripts\4_world\entities\vehicles\inheritedcars\hatchback_02.c:393`.

- `vehicle_drive` needs the server-side seat; with the client-owner seat it answers `not_seated`.
- A raw `/enqueue` needs `{identity, lease_token}` in the body as well as `?key=`; both come from `session_acquire`.
- Measured on a car mod: `wheel_count` went from 0 to 4, fuel to 1.0, the full kit fitted, and the car drove up to sixth gear.

`vehicle_prepare_fixture` takes any `CarScript` class name; an object of another class fails with `fixture_not_vehicle` (`<dayz-mcp>/addon/scripts/5_Mission/MCPBridge.c:1214` to `:1280`). It returned `vehicle_fixture_ready=1` with `wheel_count` 4 on 15 different `CarScript` types, among them several test cars and quads and the vanilla `Hatchback_02` and `CivilianSedan`; three test variants of one quad returned `fixture_not_ready`.

An old dayz-mcp copy hard-codes one car mod's class name in this verb; update dayz-mcp if it refuses every other class.

## A bare spawn shows the undercarriage

A `world_spawn` of a `CarScript` creates it with no attachments (`wheel_count=0`, `attachment_count=0`). Only the hub or disc shows, with no tyre, and the brakes (rotor and caliper, the caliper often red), suspension and hubs sit bare in the wheel arch as if floating in a gap. That is not misalignment: it is correct base geometry, symmetric and in place, inside the space the missing wheel would fill.

- A smoke test of a bare spawn checks materials only: body paint, textures and winding. It does not check undercarriage alignment or the finished look.
- To judge alignment or the look with wheels, fit them (section above) and capture again.
- When a part "looks displaced", measure before you decide: bounding box, centroid, left and right symmetry, a comparison against a backup, containment in the wheel volume. On one car a "misaligned parts" scare was bare brakes and suspension, symmetric within 0.003 m and inside the wheel volume.

## Where and how to run the drive checks

- Use a verified site with at least 150 m clear in the driving direction. A site can freeze the vehicle or block the get-out against statics at the end of the run. Do not reuse a site without evidence from the session itself: `surface_query` plus `entities_query`. A `scene_raycast` in `view` mode does not see the statics that stop a car.
- The site dayz-mcp's `docs/VEHICLE_TESTING.md` records is the north-west airfield on Chernarus, `[4200.0, 0.0, 10650.0]`: a corridor 160 m long and 25 m either side, to the north, fully listed; a drive there moved 3.2 m in 2 s on the flat. Certify it again for your PBO with dayz-mcp's `python tools/g0_site_gate.py --pbo-sha256 <sha> --out <verdict.json>`, with the game running and the bridge ready (the hash is required). That document also lists other sites and what degrades them.
- Keep run, verbs and teardown in one process (`run-lifecycle.md`).
- Use `entities_query` only with the player inside the area, and check for a roof or canopy before any teleport to unverified coordinates (`verb-gotchas.md`, "`entities_query`, `surface_query` and unverified coordinates").
- The diag client dies after about 6 minutes without commands; send `vehicle_telemetry` every 45 s or so (`run-lifecycle.md`).
- Three different AI coding agents, one with MCP access only, each ran spawn, wheel fitting, seat, a drive of 100 to 163 m, a door by `object_id`, delete and release from a short brief.

## Driving bench: leftover cars, the wrong car and old traces

Measured over 17 driving runs on the airfield concrete, one `vehicle_trace` each, with an older dayz-mcp build.

1. A `world_spawn` car outlives its run. Created with `flags=0`, a car whose run dies before `object_delete` is saved by the server and comes back in every new run, and `object_delete(object_id)` cannot reach it because the id belonged to the dead run. Create bench cars with `flags=8389668`: `ECE_PLACE_ON_SURFACE` (1060, `P:\scripts\3_game\ce\centraleconomy.c:38`) plus `ECE_NOPERSISTENCY_WORLD` (8388608, `centraleconomy.c:31`).
2. `vehicle_get_in_client(pos)` answered `ok` while seating the player in that leftover car 2 m away instead of the new one at 0 m, twice. Only the trace's `car_type` showed it. Two cars of the same class in range make `vehicle_prepare_fixture` return `ambiguous_fixture`. Newer builds take the nearest vehicle; keep the check anyway.
3. After that, the get-in returned `not_seated` for any car, on a clean site and after `player_respawn` too. Only a fresh client fixed it.
4. The drive controller skipped gears. The automatic `ShiftUp()` (vanilla `P:\scripts\3_game\vehicles\car.c:257`) fired on every tick with rpm above 0.8 of the redline: first to fourth within 100 ms at about 33 km/h, and no downshift. Newer builds wait 0.3 s between automatic upshifts (`AUTO_SHIFT_SETTLE_S` in dayz-mcp's `addon/scripts/4_World/MCP_CarScript.c`). Launch figures from the older build hold only below about 33 km/h.
5. Traces from the older build store booleans as 0 and 1 and lack fields added later, so a current reader rejects them as `dump_invalid`. The reader revision they were recorded with reproduced all 16 runs exactly.
6. Seven cars in a row in one run, each deleted with the client seated, worked. What broke the get-in was the leftover car, not the number of cars.

Rules for a driving bench:

- Create the test car with `flags=8389668`.
- Before the first run, `entities_query(pos, radius=30)` shows no other vehicle.
- After `vehicle_get_in_client`, the returned `type` is the class you created; otherwise record `car_mismatch` and skip the run.
- Before you analyse a run, check the trace's `car_type` against the class you asked for.
- A `not_seated` that survives `player_respawn` needs a fresh client.
- Analyse stored traces with the `vehicle_trace.py` revision they were recorded with.

Not yet tested: a get-in with another vehicle 2 m away on a build that takes the nearest one, and a five-car run with `flags=8389668` killed halfway, checking that nothing is saved.

Numeric thresholds on any of this telemetry follow `telemetry-gates.md`.
