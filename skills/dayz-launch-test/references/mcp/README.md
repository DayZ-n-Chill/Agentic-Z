# Verifying a mod in game through dayz-mcp

How to drive a running DayZDiag client through the tools of the dayz-mcp MCP server, to check a mod with no one at the keyboard: spawn the object, look at it from several angles (camera plus a grab of the game window), test collision by raycast, read placement and telemetry, and write a report with pass and fail criteria and evidence. It covers the stretch between "the PBO builds and deploys" and "it looks and behaves right in game", for what needs no keyboard input.

dayz-mcp is a third-party tool, an MCP server with its `@DayZ_MCP` mod, and this repo does not ship it. What these files say about its verbs comes from game sessions with it or from reading its source, and each file marks what is a source reading, untested, or a proposal for a verb that does not exist yet. None of it is checked on `P:\`; vanilla facts cite the vanilla file.

## Where it sits next to the skills

| Job | Skill |
|---|---|
| Lint, build and deploy the PBO | `/dayz-lint`, `/dayz-build-pbo`, `/dayz-gate build` |
| Start a local server and client for a person to play | `/dayz-launch-test`, stopped with `/dayz-stop-test` |
| Boots with clean logs; scripted log checks; screenshots against a baseline | `/dayz-gate ingame`, `/dayz-gate behavior`, `/dayz-gate visual` |
| Read and triage a run's logs | `/dayz-logwatch` |
| Launch recipes, server and mission config, the AutoTest mod, the Linux server and headless client | `../README.md` |
| Spawn, look, raycast, seat, drive and click through dayz-mcp verbs, with evidence | this folder |

A dayz-mcp run is started and stopped by its own `dayz_test_run` and `dayz_test_stop`, never by `/dayz-launch-test`, `/dayz-stop-test` or `/dayz-gate`: those do not know the run, and the last two kill or replace it (`run-lifecycle.md`).

## Ask who is driving

Before the first dayz-mcp tool of a verification run, ask the user whether they are driving or dayz-mcp is. Assume neither, and ask once per run, not once per capture.

| Situation | Who drives |
|---|---|
| The user is present and free | The user, with an admin tool and their own judgment; dayz-mcp only if they ask |
| The user is away, or the run is unattended | dayz-mcp, with the report left for them with the evidence |
| In doubt | Ask |

With the user present, their manual cycle is faster and better: they spawn with an admin tool in seconds and judge the whole scene at a glance, while dayz-mcp has to place a camera, capture and chain tools. dayz-mcp wins when the user is not there. Switching halfway costs too: a clean manual test needs a relaunch without `@DayZ_MCP` (`captures.md`), so choose at the start of the cycle. Across 276 recorded sessions, 63 percent of a full cycle's wall clock time fell on the user's side, and 71 percent of their real checks could be automated with today's tools; that a check can be automated does not mean it should be while the user is there.

What a person cannot measure by eye (telemetry, numeric raycasts, exact placement, repeatable series) still goes through dayz-mcp. Do not ask about those; use it.

## Before driving

1. The PBO is built and deployed (`/dayz-build-pbo <ModName>` or `/dayz-gate build <ModName>`), and `/dayz-preflight` passes.
2. The `mcp__dayz-mcp__*` tools are available in the session, the bridge config and key are seeded, and the tool can load every mod in the request (`bridge-setup.md`, "Prerequisites, in order").
3. You have read dayz-mcp's own agent session protocol.

## The loop

1. **Launch.** `dayz_test_run` with mode `all` (server and client: captures read the rendered client, and a server only run has no window), a build when the PBO changed, and `extra_mods=["@DayZ_MCP"]`, which it does not add by itself. Keep the `run_id`.
2. **Adopt.** `session_acquire_wait(purpose=...)` and check `adopted_run.ok`. Never probe before adopting: until then every verb that crosses the bridge is refused, reads included. Send `session_heartbeat` at least every 90 seconds for the whole run; the lease lasts 120 seconds and nothing renews it for you.
3. **Gate.** `bridge_status` is always the first verb. The server peer needs a fresh `last_poll_age_s`, and for captures the client peer too. "Never polled" means stop and diagnose.
4. **Check the run.** Read `-mod=` and `-mission=` in the run's RPT: a verdict is worth what that line is worth (`verification-discipline.md`).
5. **Scene.** `world_time_set` to noon (all five arguments) and `world_weather_set(overcast=1.0)`, so captures compare.
6. **Playbook** for the kind of mod: static object, item or weapon, vehicle (`playbooks.md`).
7. **Report** with evidence, and a manual test section for what was not covered.
8. **Stop.** `session_release`, then `dayz_test_stop(run_id)`.

## Which tool checks what

| Tool | Checks | Failure signal |
|---|---|---|
| `world_spawn` | the class loads | `unknown_type` or `spawn_failed`: the mod is not mounted |
| `camera_set` and `capture_screenshot` | the render: visible, textured, faces the right way, proportions | invisible, magenta, holes |
| `scene_raycast` (default `rvproxy`) | LOD collision (Geometry, View Geometry, Fire Geometry, by `intersect`) | no hit where there should be one |
| `scene_raycast(method="bullet")` | a physics shape on the masked layers | no hit on the target where there should be one; a miss alone is not proof |
| `player_move` walk and `query_player_state` | the object stops the player | `arrived:true` through it; walking through alone is not proof |
| `telemetry_read(mode="object_at")` | placement, orientation, attachments, health | `found=false`, or a buried position |
| `vehicle_enter`, `vehicle_get_in_client`, `vehicle_control`, `vehicle_telemetry` | the seat, then a real drive | `not_seated`, no movement, wrong wheel direction |
| `action_use`, `ui_tree`, `ui_click`, `ui_set_text` | the mod offers an action; a mod UI opens and answers | `condition_failed`, `no_menu` |
| `bridge_status` | both peers are alive (the gate) | `last_poll_age_s=null`: the bridge is down |
| `world_time_set`, `world_weather_set` | a repeatable scene for captures | none |

A reply's `ok` is not the result. For each verb, read the effect (`verb-gotchas.md`, "Read the effect, never the reply").

## What it does not cover

Say this in every report.

- Free player input: shooting, reloading, interactive inventory, vanilla menus. There is no generic player input tool.
- Continuous actions (anything with a progress bar: dismantling, deploying, crafting). `action_use` starts them and they never finish, so no persistent object can be made through dayz-mcp and no save and load test across restarts is conclusive.
- Doors open and close only with `door_index` and cannot be held at a fixed pose.
- `exec_enforce` does not run on the headless diag server.
- A HUD tied to the first person vehicle camera cannot be photographed with `camera_set`.
- After `camera_set` the user may not get the player back: `restore_gameplay` can answer `restore_unverified`, so a clean manual test needs a relaunch without `@DayZ_MCP`.

The detail and the workarounds (a key driven test addon, a mission driver) are in `actions-ui-and-inventory.md`.

## Report

A criteria table (criterion, PASS, FAIL or INFO, evidence), the PNG captures and the telemetry and raycast JSON, one overall verdict, and a manual test section. Each capture costs about 25,000 tokens of context: batch the orbit captures and never read a PNG twice. Before you record a FAIL, open the client log (`/dayz-logwatch --dir <client profile folder> --since <minutes>`, reaching back past the failure; without `--since` it reads only lines written after the watch starts). In one series the automatic verdict blamed the mod six times with no real mod failure.

## What to read

| Question | Read |
|---|---|
| What must be true before the first verb? Why is the bridge silent, stale or `legacy_blocked`? Which mods can the launch load? | `bridge-setup.md` |
| How do I launch, adopt, keep and stop a run? How do several sessions share one test machine? | `run-lifecycle.md` |
| How do `dayz_test_run`, its launcher allow-list, leases and request rules behave, and how does `dayz-test.ps1` fit in? | `../managed-launcher.md` |
| What counts as PASS or FAIL for a static object, an item or a vehicle? What goes in the report? | `playbooks.md` |
| A verb said `ok`: what did it really do? (`world_spawn`, `wait_for`, `logs_since`, `inventory_give`, `telemetry_read`, `object_delete`, `player_respawn`, `key_press`, `entities_query`, `player_teleport`, `object_anim`) | `verb-gotchas.md` |
| How do I read collision with rays, a walk into test and a stand on test? What does `normal` mean? How do I pose a test object? | `collision-probes.md` |
| Why is the capture black, flat or the same between poses? How do I capture a raised weapon or measure UI pixels? | `captures.md` |
| Can I drive an action, a door, a mod UI or an inventory move? What when no verb exists? | `actions-ui-and-inventory.md` |
| How do I smoke test a car, give it real wheels and fuel, or run a driving bench? | `vehicle-smoke.md` |
| How do the vehicle verbs behave on 1.30 (gearboxes, fuel readings, seating, deleting a car)? | `vehicle-verbs.md` |
| What are the acceptance steps R1 to R6, the owner side drive verbs and the failure to fix table? | `vehicle-acceptance.md` |
| How do I run those steps from a script? | `skills/dayz-launch-test/scripts/run_vehicle_checks.py` (its fixtures are `test_run_vehicle_checks.py` beside it) |
| How do I set a numeric threshold on telemetry that real physics can pass? | `telemetry-gates.md` |
| Is this verdict worth believing? Which mod did the run load, what is in the PBO, where is the hang, is one sample enough? How do I review the bridge's own code? | `verification-discipline.md` |
| What changed in 1.30 (Script Console tabs, `IsHeadless`, pending single player actions)? | `../dayz-1-30.md` |
| Does the bridge work on Linux? | `../linux.md`, "The bridge" |
