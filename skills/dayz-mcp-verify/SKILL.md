---
name: dayz-mcp-verify
description: "Tests a DayZ mod in the running game through the dayz-mcp MCP server, with no keyboard and no OCR: spawns a class, orbits a camera and captures it, raycasts its collision, reads placement, attachments and telemetry, and writes a PASS or FAIL report with PNG and JSON evidence. Use to auto-test a mod in game, verify in game with MCP, run a visual smoke test or re-test, check that a .p3d loads, shows and collides, or run the vehicle acceptance ladder (spawn, render, get in, drive, wheel direction). Covers static objects, items and weapons, buildings, vehicle placement and drivability, and mod UI clicks; firing, reloading and other free player input stay manual. Spanish triggers: \"auto-probar el mod\", \"verificar in-game con MCP\", \"comprobar que el .p3d carga/se ve/colisiona\"."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-mcp-verify

Drives a DayZDiag client that is already running, through the tools of the dayz-mcp MCP server, to verify a mod without a human at the keyboard: it spawns the object, looks at it from several angles (camera plus a grab of the game window), checks collision by raycast, reads placement and telemetry, and writes a report with pass and fail criteria and evidence. It is the automated observation loop between "the PBO builds and deploys" and "it looks and behaves right in game", for the properties that need no keyboard input.

Follow `skills/_shared/dayz-conventions.md`. dayz-mcp is a third-party tool (an MCP server and its `@DayZ_MCP` mod); this repo does not ship it. The statements about its verbs here and in `references/` come from game sessions with that tool or from reading dayz-mcp's own source; the references mark which ones are a source reading, not tested in game, or a design proposal for a verb that does not exist yet. None of it is checked on `P:\`; vanilla facts cite the vanilla file.

## Where it sits next to the other skills

| Job | Skill |
|---|---|
| Lint, build and deploy the PBO | `/dayz-lint`, `/dayz-build-pbo`, `/dayz-gate build` |
| Start a local server and client for a person to play | `/dayz-launch-test`, stopped with `/dayz-stop-test` |
| Does it boot with clean logs; scripted log checks; screenshot comparison against a baseline | `/dayz-gate ingame`, `/dayz-gate behavior`, `/dayz-gate visual` |
| Read and triage the logs of a run | `/dayz-logwatch` |
| Launch recipes, server and mission config, the AutoTest mod, Linux server and headless client | the `dayz-test-ingame` skill |
| Spawn, look, raycast, seat, drive and click through MCP verbs, with evidence | this skill |

An MCP run is started and stopped by dayz-mcp's own `dayz_test_run` and `dayz_test_stop`, never by `/dayz-launch-test`, `/dayz-stop-test` or `/dayz-gate`: those do not know the run and the last two kill or replace it (`references/run-lifecycle.md`).

## Gate 0: ask who is driving

Before the first dayz-mcp tool of a verification run, ask the user whether they are driving or the MCP is. Assume neither. Ask once per run, not once per capture.

| Situation | Who drives |
|---|---|
| The user is present and available | The user, with an admin tool and their own judgment; MCP only if they ask |
| The user is away, or the run is unattended | MCP, and the report is left for them with the evidence |
| In doubt | Ask |

Why this is a gate and not a preference: with the user present, their manual cycle is faster and gives better results. They spawn with an admin tool in seconds and judge the whole scene at a glance, while the MCP loop has to place a camera, capture and chain tools. MCP wins when the user is not there. Changing mode halfway is not free either: a clean manual test needs a relaunch without `@DayZ_MCP` (`references/captures.md`), so the choice is made at the start of the cycle or paid for twice.

What does not change: MCP is still required for what a person cannot measure by eye (telemetry, numeric raycasts, exact placement, repeatable series). Do not ask for those, use it.

The measurement behind the gate (2026-08-07, across 276 recorded sessions): 63 % of the wall-clock time of a full cycle fell on the user's side, and 71 % of their real checks could be automated with today's tools. That a check can be automated does not mean it should be: with the user present, their cycle rules.

## Before driving

1. The PBO is built and deployed (`/dayz-build-pbo <ModName>` or `/dayz-gate build <ModName>`), and `/dayz-preflight` passes.
2. The `mcp__dayz-mcp__*` tools are available in the session, the bridge config and key are seeded, and every mod in the request can be loaded by the tool (`references/bridge-setup.md`, "Prerequisites, in order").
3. Read dayz-mcp's own agent session protocol before the first run.

## The loop

1. **Launch.** `dayz_test_run` with mode `all` (server and client: the capture reads the rendered client, a server-only run has no window), a build when the PBO changed, and `extra_mods=["@DayZ_MCP"]`, which it does not add on its own. Keep the `run_id`.
2. **Adopt.** `session_acquire_wait(purpose=...)` and check `adopted_run.ok`. Never probe before adopting: until then every verb that crosses the bridge is rejected, reads included. Send `session_heartbeat` at least every 90 s for the whole run; the lease lasts 120 s and nothing renews it for you.
3. **Gate.** `bridge_status` is always the first verb. The server peer needs a fresh `last_poll_age_s`, and for captures the client peer too. "Never polled" means stop and diagnose.
4. **Check the run.** Read `-mod=` and `-mission=` in the run's RPT: a verdict is worth what that line is worth (`references/verification-discipline.md`).
5. **Scene.** `world_time_set` to noon (all five arguments) and `world_weather_set(overcast=1.0)`, so captures can be compared.
6. **Playbook** for the mod type: static object, item or weapon, vehicle (`references/playbooks.md`).
7. **Report** with evidence, and a manual test section for what was not covered.
8. **Stop.** `session_release`, then `dayz_test_stop(run_id)`.

## Which tool verifies what

| Tool | Verifies | Failure signal |
|---|---|---|
| `world_spawn` | the class loads | `unknown_type` or `spawn_failed`: the mod is not mounted |
| `camera_set` + `capture_screenshot` | the render: visible, textures, winding, proportions | invisible, magenta, holes |
| `scene_raycast` (default `rvproxy`) | LOD collision (Geometry, View Geometry, Fire Geometry, by `intersect`) | no hit where there should be one |
| `scene_raycast(method="bullet")` | a physics shape on the masked layers | no hit on the target where there should be one; a miss alone is not proof |
| `player_move` walk + `query_player_state` | the player is stopped by the object | `arrived:true` through it; a walk-through alone is not proof |
| `telemetry_read(mode="object_at")` | placement, orientation, attachments, health | `found=false`, or a buried position |
| `vehicle_enter`, `vehicle_get_in_client`, `vehicle_control`, `vehicle_telemetry` | the seat, then a real drive | `not_seated`, no movement, wrong wheel direction |
| `action_use`, `ui_tree`, `ui_click`, `ui_set_text` | a mod offers an action; a mod UI opens and answers | `condition_failed`, `no_menu` |
| `bridge_status` | both peers are alive (the gate) | `last_poll_age_s=null`: the bridge is down |
| `world_time_set`, `world_weather_set` | a repeatable scene for captures | none |

A reply's `ok` is not the result. For each verb, read the effect (`references/verb-gotchas.md`, "The oracle is the effect, never the reply").

## What it does not cover

Say this in every report.

- Free player input: shooting, reloading, interactive inventory, vanilla menus. There is no generic player input tool.
- Continuous actions (anything with a progress bar: dismantling, deploying, crafting). `action_use` starts them and they never finish, so no persistent object can be made through MCP and no save and load test across restarts is conclusive.
- Doors open and close only with `door_index`, and cannot be held at a static pose.
- `exec_enforce` does not run on the headless diag server.
- A HUD gated on the first-person vehicle camera cannot be photographed with `camera_set`.
- After `camera_set` the user may not get the player back: `restore_gameplay` can answer `restore_unverified`, so a clean manual test needs a relaunch without `@DayZ_MCP`.

The detail and the workarounds (a key-driven test addon, a mission driver) are in `references/actions-ui-and-inventory.md`.

## Report

A criteria table (criterion, PASS, FAIL or INFO, evidence), the PNG captures and the telemetry and raycast JSON, one overall verdict, and a "manual test" section. Each capture costs about 25,000 tokens of context: batch the orbit captures and do not read a PNG twice. If a verdict says FAIL, open the client log before recording it (`/dayz-logwatch --dir <client profile folder>`); in one battery the automatic verdict accused the mod six times with no real mod failure.

## What to read

| Question | Read |
|---|---|
| What must be true before the first verb? Why is the bridge silent, stale or `legacy_blocked`? Which mods can the launch load? | `references/bridge-setup.md` |
| How do I launch, adopt, keep and stop a run? How do several sessions share one test machine? | `references/run-lifecycle.md` |
| What counts as PASS or FAIL for a static object, an item or a vehicle? What goes in the report? | `references/playbooks.md` |
| A verb said `ok`: what did it really do? (`world_spawn`, `wait_for`, `logs_since`, `inventory_give`, `telemetry_read`, `object_delete`, `player_respawn`, `key_press`, `entities_query`) | `references/verb-gotchas.md` |
| How do I read collision with rays, a walk-into test and a stand-on test? What does `normal` mean? How do I pose a test fixture? | `references/collision-probes.md` |
| Why is the capture black, flat or identical between poses? How do I capture a raised weapon or measure UI pixels? | `references/captures.md` |
| Can I drive an action, a door, a mod UI or an inventory move? What when no verb exists? | `references/actions-ui-and-inventory.md` |
| How do I smoke-test a car, give it real wheels and fuel, or run a driving bench? | `references/vehicle-smoke.md` |
| What are the ladder rungs R1 to R6, the owner-side drive verbs and the failure to fix mapping? | `references/acceptance-ladder.md` |
| How do I run the ladder from a script? | `references/drive_ladder.py` (fixtures in `tests/test_drive_ladder.py`) |
| How do I set a numeric threshold on telemetry that real physics can pass? | `references/telemetry-gates.md` |
| Is this verdict worth believing? Which mod did the run load, what is in the PBO, where is the hang, is one sample enough? How do I review the bridge's own code? | `references/verification-discipline.md` |
| What changed in 1.30 (Script Console tabs, `IsHeadless`, pending single-player actions)? | `references/dayz-1-30-mcp-verify.md` |
| Does the bridge work on Linux? | `references/linux.md` |

When the work has to end in a mod that builds, loads and ships (config, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow the `dayz-mod-dev` skill.
