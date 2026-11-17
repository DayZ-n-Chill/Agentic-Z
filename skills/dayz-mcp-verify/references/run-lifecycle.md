# Run lifecycle: launch, adopt, lease and the shared test machine

How a dayz-mcp run is started, adopted, kept alive and stopped, and how several sessions share one test machine.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game sessions with that tool. It is not yet checked on `P:\` and cannot be, because none of it is vanilla. File and line numbers such as `loopback.py:1293` are lines of dayz-mcp's own source at the time of the measurement; `<dayz-mcp>` is the folder of your dayz-mcp checkout.

## Who owns what

- Building the PBO is `/dayz-build-pbo` (or `/dayz-gate build`). This skill starts after a PBO is deployed.
- Starting and stopping the game for an MCP run belongs to dayz-mcp's public test tools, `dayz_test_run` and `dayz_test_stop`. The bridge verbs (`world_spawn`, `scene_raycast`, `camera_set` and the rest) never start or stop a process.
- Read dayz-mcp's own agent session protocol (the runbook that ships with the tool) before the first run.
- [EXACT][CLAIM-R21-MCP-ORCHESTRATED-TEST] Run the lifecycle with `dayz_test_run` and stop it with `dayz_test_stop` on the exact `run_id`. Both tools have their own FIFO queue, lease, heartbeat and release, so do not wrap them in a second `session_acquire`. Keep the `session_*` primitives for low-level mutations that those tools do not already cover. Every lifecycle is identified by its `run_id`: loading the same mod as another run gives no ownership of it. Under retail quarantine only reads are allowed; if whoever opened the retail game cannot close it through its UI, declare `manual_cleanup_required`.

## What the run request must ask for

The `dayz_test_run` request selects mode `all`, builds when the PBO changed, and names `@DayZ_MCP` as an extra dependency.

- Mode `all` (server plus client) is required. The visual capture reads the rendered client; a server-only run has no window to grab.
- `@DayZ_MCP` is loaded next to the mod under test. Both peers, the server bridge and the client bridge, poll the MCP server on loopback.
- `dayz_test_run` does not load `@DayZ_MCP` on its own and still answers `succeeded`: pass `extra_mods=["@DayZ_MCP"]` (see `verb-gotchas.md`, "Six traps").

## Bridge startup sequence (revised 2026-09-06)

The order is `dayz_test_run`, then `session_acquire_wait`, then verbs. Never probe before adopting.

"Do not wrap the launch in another lease" does not mean the run stays yours. When it finishes, `dayz_test_run` releases its owner lease (the daemon audit shows `session_release_finished reason=owner_release` right after the launch) and the run moves to `RUNNING_IDLE` with no owner (`release_owner`, `process_lifecycle.py:958-976`). From then on the idle-run fence rejects every `/enqueue` on that run, reads included: `_enqueue_run_rejection` ignores the `mutation` flag (`loopback.py:1293-1296`) and for `RUNNING_IDLE` returns `run_not_owned` (`:1317-1318`) with the hint "This run has no owner (RUNNING_IDLE). Adopt the existing run before dispatching." (`:99-102`, `:1323-1329`). The misleading part: the `bridge_status` counter is named `fence.mutation_rejects_by_code` (`:2821-2822`) and it counts reads too. Every verb that crosses the bridge is rejected this way (`query_*`, telemetry, raycast, captures, `world_spawn` and so on), and so is `wait_for(players_at_least|players_at_most)`, which polls with `query_all_players` (`server.py:2645-2650`). `wait_for(log_matches)` is not rejected: it reads log files without touching the bridge (`server.py:2603-2637`, `:2686-2697`).

1. `dayz_test_run(...)`. Keep the `run_id`.
2. Optional, without adopting: `wait_for(log_matches, "...")` to wait for the boot through the RPT.
3. `session_acquire_wait(purpose=...)`. The grant adopts the only ownerless `RUNNING_IDLE` run and reports it in `adopted_run` (`_adopt_on_grant`, `loopback.py:3119-3120`, `:3193-3230`). Check `adopted_run.ok` before the first verb. With several idle runs it answers `adopted_run.error = "multiple_idle_runs"` and adopts none (`:3202-3208`): stop the surplus run with `dayz_test_stop` and repeat.
4. `wait_for(players_at_least, 1)` and the other verbs.
5. `session_release`, then `dayz_test_stop(run_id)`.

With an MCP client older than dayz-mcp commit `8f5727f` (2026-09-06) the rejection arrived as a bare `remote_error` with no code or hint, and was first blamed on a client without polling. With a current client it arrives as `run_not_owned: This run has no owner (RUNNING_IDLE)...`. In both cases the remedy is to adopt, not to retry and not to relaunch. This rule corrects step 1 of the UI recipe in `actions-ui-and-inventory.md` ("Opening a mod's UI without a keyboard") and explains the lease bullet below.

## Leases expire on their own

- [EXACT] The adopted lease lasts 120 s and is not renewed internally, whether the MCP client is fresh or not (added 2026-09-27, LFPowerGrid, three runs; measured in game, DayZ 1.30.164014 Experimental). Send `session_heartbeat` at least every 90 s or so for the whole run, also while a human plays. Past the deadline the run is ownerless again (`grace.remaining_s` counts down) and the daemon stops it (`lifecycle_stop_outcome: stopped`), even with the user in front of the game.
- [EXACT] Two lease failures around long waits (measured in game sessions, 2026-09-28): (1) `wait_for` over the log does not renew the lease, and a wait longer than about 2 minutes expired with `lease_expired`, so put `session_heartbeat` between waits; (2) when a user message interrupts a call in flight (a long `wait_for`), the next `session_heartbeat` answers `lease_invalid: token was never valid for this client`. If the run is still alive, `session_acquire_wait` adopts it again.
- `dayz_test_close` shuts the run down in order, with a termination line on both sides.
- `query_*`, telemetry, raycast and captures cross the bridge and need `session_acquire`. Only `dayz_test_run` and `dayz_test_stop` manage their own lease; do not assume that for other verbs (SP-152, added 2026-08-31). Since the 2026-09-06 revision, "need `session_acquire`" includes adopting the run that the launch left `RUNNING_IDLE`: the grant of `session_acquire_wait` does that and reports it in `adopted_run`.
- Long sessions: the diag client dies after about 6 minutes without commands (`client_not_polling`). Run a keepalive, for example `vehicle_telemetry` every 45 s or so, for the length of the session (added 2026-08-24).

## One process lifetime for the whole run (added 2026-08-24)

In the agent harness of that session, the spawned daemon and its sequence died with the command tree that spawned them: a "broke away" child did not survive, and adopting an external daemon was broken too (LL-358). So the whole sequence of run, verbs and teardown goes inside one process: preventive stop, run, wait for bridge ready, wait for the player, teleport with a lease, work, `dayz_test_stop`.

## The test machine is one shared resource

- Port 2302 and the Steam client are single resources. Exclusion is coordinated through the runbook's FIFO lease, not by guessing whose processes are running and not by evicting other sessions. `dayz_test_run` acquires and holds the exclusion; keep its `run_id` and end that same run with `dayz_test_stop`. Never kill a process to free the machine: if the state does not reconcile, keep the process and declare a degraded shutdown.
- Historical pattern, superseded 2026-07-15: starting the game with `cmd start` or a `.bat` kept a background job from losing its child, but it created a process outside the registered lifecycle. For any current smoke test use only `dayz_test_run`, keep its `run_id` and end only that run with `dayz_test_stop`. There is no unmanaged fallback that goes around the lifecycle guard.
- In this repo that means: do not start an MCP run with `/dayz-launch-test`, and do not end one with `/dayz-stop-test`, which kills every `DayZDiag_x64.exe` on the machine. `/dayz-gate build`, `ingame`, `behavior` and `visual` also stop a running session before they start (they ask first, or need `--yes`), so do not run a gate while an MCP run is alive. A game started by hand was measured to poll as `LEGACY_UNBOUND`, reads only (see `linux.md`; measured on Linux, not re-measured on Windows).

### `blocked_on` in `session_status` is an instruction (SP-351, added 2026-08-29)

With the machine occupied, `session_status` returns:

```
"blocked_on": "DayZ test box; next: call dayz_test_run(..., wait_for_box_s=<n>) to join the box FIFO"
```

Measured on 2026-08-29: an autonomous night session read that line on every query for seven and three quarter hours and kept waiting for another session to say it was done. The queue existed, was named in the reply, and was not used. When it was finally used, `wait_for_box_s=600` answered `active_run_exists` with `hint: "stop it with dayz_test_stop(run_id=...)"`, again the next step in the reply. Given a 15 minute deadline, the neighbouring session released in two: it had spent hours holding a fixture that had never been used (its own capture gave `frame_client_all_black`, with no activity on its server).

1. If a tool tells you how to unblock yourself, do it before waiting for anyone.
2. An autonomous session has no "wait for notice". Either join the resource queue or give whoever holds it a deadline. Waiting without a horizon is giving up the task. "When the user finishes" is not a horizon, it is an open dependency: whoever offers it should release the resource and ask for it again (a relaunch takes minutes, a fixture is rebuilt in two verbs).

### A free lease does not mean a free machine (SP-124)

`session_status` can return `owner: null`, an empty queue and `claimable: true` while a DayZ server and client are alive, launched outside the managed lifecycle by another line of work and holding port 2302. The lease describes the lease, not the machine. Before treating the machine as free, read the `-mod=` of the living processes:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" |
  Select-Object ProcessId, CommandLine
```

The command line says whose run it is and whether it loads your mod. For a build, the "no DayZ process" guard can be narrowed to the two conditions it stands for (no running process loads your mod, and the target PBO opens exclusively) instead of skipping the guard or waiting for the other line to finish. The same rule applies on the launch side (the `dayz-test-ingame` skill).

### A machine that looks free can be taken seconds later (measured 2026-08-18)

`bridge_status` said the machine was free (peers null, no lease, no runs) and 40 s later a navigation probe run started outside the lifecycle and without a lease; one of this session's probes then ran `player_teleport` and moved that run's player. Before any mutation on "the first human" check `bridge_status.coordination.active`, `server_peer.last_poll_age_s`, and:

```powershell
Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe'"
```

If a server is polling that is not yours, do not mutate.

## External companion: dayz-labs

[EXACT][CLAIM-R21-MCP-COMPANION-AUTHORITY] `external_companion_no_lifecycle_authority`. Release v0.1.35 of the dayz-labs tool, reviewed at pinned commit `dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a`, can serve as a reference or an optional companion. Its `start`, `stop` and `restart` verbs are excluded while dayz-mcp holds a run: only `dayz_test_run` and `dayz_test_stop` on the exact `run_id` govern that lifecycle. Do not install or update the companion as part of a gate, and always record the `pinned_version` you examined.

Its interface is WPF and it captures its own application: `wpf_not_layout_evidence`. A correct capture from dayz-labs does not validate the parser, proportions, clipping or meaning of a DayZ `.layout`; a UI viewer needs its own render and a comparison against in-game evidence.
