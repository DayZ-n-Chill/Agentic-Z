# Vehicle smoke test, conditioning and the driving bench

A repeatable visual smoke test of a `CarScript` vehicle through dayz-mcp, how to give a spawned car real wheels and fluids, what a bare spawn does and does not show, the session rules for the drivability ladder, and the rules for a driving bench.

The verbs are dayz-mcp's; their behaviour and every measurement here are third-party, taken in game sessions with that tool, and not yet checked on `P:\`. Vanilla facts cite the vanilla file. `MCPBridge.c:NNN` and similar are lines of dayz-mcp's own source at the time of the measurement; `<dayz-mcp>` is the folder of your dayz-mcp checkout. The ladder itself (rungs, failure to fix mapping) is in `acceptance-ladder.md`.

## Smoke recipe

Verified end to end on a `CarScript` car mod on 2026-06-24. Repeat it without deriving it again.

1. **Mission: the stock `dayzOffline.chernarusplus`** from the DayZ Server install, not a mount-probe mission whose `main()` is empty. A mount-probe mission spawns no player, so the client does not render the world and the capture is black. The stock mission creates the player, which gives a free camera over a rendered world.
2. **Seed the bridge config before the launch.** `dayz_mcp.json` with `{"url":"http://127.0.0.1:8765/","key":"<key>","pollHz":5}` (ASCII) goes in the server profile folder and the client profile folder of the run. The bridge reads it from `$profile:` (server `MCPBridge.c:125`, client `MCPClientBridge.c:211`), once, in its init; the key is `<dayz-mcp>\tools\.dayz_mcp.key`. Do not use `install-mcp.ps1 -Register` for this: it registers the broker mode (`--client`) again. More in `bridge-setup.md`.
3. **Launch** through `dayz_test_run` with mode `all`, a build when the PBO changed, `extra_mods=["@DayZ_MCP"]` and the stock mission (`run-lifecycle.md`). The recipe was first written for the launcher script (`dayz-test.ps1 -Mod <Mod> -Mode all -Build -PackOnly -ExtraMods "@DayZ_MCP" -Mission "<...>\dayzOffline.chernarusplus" -ServerWait 240`, called by its absolute path because `P:\` is a substituted drive); that unmanaged start was superseded on 2026-07-15. Pack-only is required for a mod with `.c` files when the build would binarize them away (the symptom was `NO_IGNITER`).
4. **Readiness.** The stock mission runs the Central Economy start for 1 to 3 minutes and the bridge reads stale meanwhile; do not spawn then (`bridge-setup.md`, "During the Central Economy load the bridge looks stale").
5. **Smoke, grouped.** `world_time_set(year, month, day, hour=12, minute=0)` (all five required) and `world_weather_set(overcast=1.0)`; `world_spawn` of the class about 10 m from the player; wait 30 s (surviving that without a native crash rules out the crash-on-spawn class of defect); then `camera_set` (camera mode `"lookat"`, with `cam_pos` and `look_at`), `capture_screenshot`, `scene_raycast` and `telemetry_read(mode="object_at")`. Healthy telemetry is `found=1`, `health01=1`, velocity 0.
6. **A flaky capture** (loading screen, menu overlay, a frame that is flat everywhere) is handled in `captures.md`, which also has the top-down pose that shows proxy alignment.
7. **The user's eye outranks the capture** when the render is ambiguous (`playbooks.md`, "The report").
8. **The session is shared.** Port 2302 and the Steam client are single resources (`run-lifecycle.md`, "The test machine is one shared resource").
9. **"The wheels are a flat disc" is not a proxy bug.** See "A bare spawn exposes the undercarriage" below.
10. **`legacy_blocked` right after launch** is usually an incomplete init (`bridge-setup.md`).

## Seating and driving: which verb does what

- `vehicle_enter(pos)` seats the player on the server and returns `seated=true`. It confirms placement and the seat, nothing more.
- Driving uses the owner-side verbs that dayz-mcp added and gated in game in its phase 5; the client takes ownership and handles throttle and steering:
  - `vehicle_get_in_client(pos)`: seats the player and takes ownership.
  - `engine_set("start" | "stop")`.
  - `vehicle_control(throttle, steer, brake, handbrake, hold_ttl_s)`: sustained control, fail-closed.
  - `vehicle_telemetry()` and `vehicle_release()`.
  - `query_get_in_condition(pos, component)`: runs on the server peer and says which of its checks blocks the get-in. It covers the checks of `ActionGetInTransport` only in part: it skips `CanGetIn()` and calls `IsAreaAtDoorFree` where the action calls `IsAreaAtDoorFreeDiag`, so its `available=1` is partial (see R3b in `acceptance-ladder.md`; the vanilla `ActionCondition` of that action is at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26`).
- The acceptance ladder runs on top of them, in order: R1 spawns, R2 renders, R3 get-in available, R4 seated, R5 drives, R6 wheel direction. Each rung reads ground truth in the game and maps its failure to a known fix in the vehicle pack. The reference orchestrator `skills/dayz-launch-test/scripts/drive_ladder.py` drives R1 to R6 and writes `verdict.json`; it applies no fix and rebuilds nothing. Its fixtures are in `skills/dayz-launch-test/scripts/test_drive_ladder.py`. Verbs, the verified owner-side mechanism, preconditions, spawn placement, the restore-gameplay step (R2.5), the guards against a false green, the ladder table and the failure to fix mapping are all in `acceptance-ladder.md`.
- The gear index in `vehicle_telemetry` is 0 = reverse, 1 = neutral, 2 = first, up to 7 = sixth, the order of the vanilla `CarGear` enum (`P:\scripts\3_game\vehicles\car.c:32`).

## Conditioning a custom car on the server

`vehicle_get_in_client` runs `OnDebugSpawn` on the client, which does nothing under server authority. The misleading symptom is `vehicle_fixture_ready=1` with `wheel_count=0` and `fuel=0` in the server telemetry.

To condition the car for real (authoritative wheels and fluids) without touching code:

1. `vehicle_enter(pos)`, the server-side seat.
2. A raw enqueue of `vehicle_drive {throttle: 0.01, duration: 0.5}`. Its preparation phase runs `car.OnDebugSpawn()` on the server (`MCPBridge.c:2104-2112`), and the 0.5 s micro-drive is negligible. A vanilla car's `OnDebugSpawn` is what fills fluids and attaches wheels, for example `P:\scripts\4_world\entities\vehicles\inheritedcars\hatchback_02.c:393`.

Notes:

- `vehicle_drive` needs the server-side seat; with the owner-client seat it answers `not_seated`.
- A raw `/enqueue` needs `{identity, lease_token}` in the body as well as `?key=`; identity and token come from `session_acquire`.
- Verified in game on a car mod (session of 2026-07-18): `wheel_count` 0 to 4, fuel 1.0, the full kit, and a run up to sixth gear.

### `vehicle_prepare_fixture` takes any `CarScript` class

`vehicle_prepare_fixture` takes any `CarScript` class name; an object of another class fails with `fixture_not_vehicle` (`<dayz-mcp>/addon/scripts/5_Mission/MCPBridge.c:1214-1280`). Between 2026-08-18 and 2026-10-01 it returned `vehicle_fixture_ready=1` with `wheel_count` 4 on 15 other `CarScript` types, among them `SUB_BRZ`, `LFQuad2`, `Arma2Quad`, the vanilla `Hatchback_02` and the vanilla `CivilianSedan`; three test variants of one quad returned `fixture_not_ready`.

Corrected 2026-10-03: this entry used to say that `vehicle_prepare_fixture` did not work outside one car mod, whose class name was hard-coded in `MCPBridge.c:835` and `loopback.py:113`, with an open issue to generalize it. The loopback copy of 2026-07-25 still had that check; the tools' 2026-08-16 release does not.

## A bare spawn exposes the undercarriage

A `world_spawn` of a `CarScript` vehicle creates it without attachments (`wheel_count=0`, `attachment_count=0`). Only the hub or disc shows, without tyres, and the brakes (rotor and caliper, the caliper often red), suspension and hubs sit exposed in the wheel arch and look as if they float in a gap. That is not misalignment: it is correct base geometry, symmetric and in place, inside the volume the missing wheel would fill.

- A smoke test with a bare spawn is materials only. It validates body paint, textures and winding, not undercarriage alignment and not the finished look.
- To judge alignment or the look with wheels, condition the car (`wheel_count` 0 to 4, section above) and capture again.
- When a part "looks displaced", measure before concluding (bounding box, centroid, left and right symmetry, a bisection against a backup, containment in the wheel volume). Do not sign "broken" or "fine" by opinion.

Verified on a car mod, 2026-07-22: a "misaligned parts" scare turned out to be exposed brakes and suspension from a bare spawn. The forensics measured symmetry within 0.003 m, no movement in a bisection across 6 shells, and containment in the wheel volume. It cost 30 minutes that the rule above avoids.

## Ladder sessions: site, process and instruments

- **A verified site.** A ladder with a drive needs a point with at least 150 m clear in the driving direction. An earlier site froze the vehicle (drivability that depends on position) and the end of its line blocked the get-out against statics. Do not reuse a site without evidence from the session itself: `surface_query` plus `entities_query`. A `scene_raycast` in `view` mode does not see the statics that stop a car.
- **The certified site: north-west airfield, `[4200.0, 0.0, 10650.0]`** on Chernarus (certified 2026-08-24 against one PBO, recorded in dayz-mcp's `docs/VEHICLE_TESTING.md`): a corridor of 160 m by 25 m either side, to the north, fully enumerated; a drive moved 3.2 m in 2 s in the horizontal plane; teardown verified. Certify it again for your PBO with dayz-mcp's `python tools/g0_site_gate.py --pbo-sha256 <sha> --out <verdict.json>` (the game already running, the bridge ready; the hash is required). Alternates and the causes of degradation are in that document.
- **One process lifetime** for run, verbs and teardown (`run-lifecycle.md`).
- **`entities_query` only with the player inside the area, and a canopy check before any teleport to unverified coordinates** (`verb-gotchas.md`, "`entities_query`, `surface_query` and unverified coordinates").
- **Keepalive.** The diag client dies after about 6 minutes without commands; run `vehicle_telemetry` every 45 s or so (`run-lifecycle.md`).
- **Three agent families drove it** (2026-08-24): three different AI coding agents, one of them with MCP access only, each drove spawn, fixture, seat, a drive of 100 to 163 m, a door by `object_id`, delete and release from a minimal brief. Not yet checked on P:\ or in this repo.

## Driving bench: orphans, the wrong car and old dumps

Measured 2026-09-13 on a car-tuning bench (17 episodes, DayZDiag, airfield concrete, one `vehicle_trace` per episode) with the dayz-mcp build before commit `d065b0e`.

1. **A `world_spawn` car outlives its run.** Created with `flags=0`, a car whose run dies before `object_delete` is persisted by the server and comes back in every new run. `object_delete(object_id)` cannot reach it: the id belonged to the dead run. Create bench fixtures with `flags=8389668`, which is `ECE_PLACE_ON_SURFACE` (1060, `P:\scripts\3_game\ce\centraleconomy.c:38`) plus `ECE_NOPERSISTENCY_WORLD` (8388608, `P:\scripts\3_game\ce\centraleconomy.c:31`).
2. **`vehicle_get_in_client(pos)` answered `ok` while seating the player in that orphan**, 2 m away, instead of the car just created at 0 m, in two episodes. Only the trace's `car_type` showed it. Two cars of the same class in range make `vehicle_prepare_fixture` return `ambiguous_fixture`. Commit `d065b0e` makes the get-in take the nearest vehicle; keep the check anyway.
3. After that, the get-in returned `not_seated` for any car, also on a clean site and after `player_respawn`. Only a fresh client fixed it.
4. **The drive controller skipped gears.** The automatic `ShiftUp()` (vanilla `P:\scripts\3_game\vehicles\car.c:257`) fired on every tick with the rpm above 0.8 of the redline: first to fourth within 100 ms at about 33 km/h, and no downshift. `d065b0e` waits 0.3 s between automatic upshifts (`AUTO_SHIFT_SETTLE_S`, dayz-mcp `addon/scripts/4_World/MCP_CarScript.c`). Launch figures recorded before that build are valid only below about 33 km/h.
5. **`vehicle_trace` dumps of that build carry 0/1 booleans and lack fields added later.** The reader coerces them and requires those fields since dayz-mcp commit `1f71983`, so a current checkout rejects them as `dump_invalid`. Pinning the reader at `d2f9dad` reproduced all 16 episodes without a difference.
6. With that build, 7 cars in a row within one run, each deleted with the client seated, worked. What broke the get-in was the orphan, not the number of cars.

Rules for a driving bench:

- Create the fixture with `flags=8389668`.
- Before the first episode, `entities_query(pos, radius=30)` shows no foreign vehicle.
- After `vehicle_get_in_client`, the returned `type` is the class you created; otherwise record `car_mismatch` and skip the episode.
- Before analysing an episode, cross-check the trace's `car_type` against the class you asked for.
- A `not_seated` that survives `player_respawn` needs a fresh client.
- An analysis of stored dumps pins the `vehicle_trace.py` revision they were recorded with.

Still open, and what would close it: a get-in with a foreign vehicle 2 m away on a build with `d065b0e`, and a 5-car run with `flags=8389668` killed halfway, checking that nothing persists.

Numeric thresholds on any of this telemetry follow `telemetry-gates.md`.
