# Starting, holding and stopping a run

How a dayz-mcp run is started, adopted, kept alive and stopped, and how several sessions share one test machine.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game with that tool. None of it is vanilla, so none of it can be checked on `P:\`. Lines such as `loopback.py:1293` are dayz-mcp's own source; `<dayz-mcp>` is your dayz-mcp checkout.

## Who owns what

- Building the PBO is `/dayz-build-pbo` or `/dayz-gate build`. This folder starts after a PBO is deployed.
- dayz-mcp's own `dayz_test_run` and `dayz_test_stop` start and stop the game for an MCP run. The bridge verbs (`world_spawn`, `scene_raycast`, `camera_set` and the rest) never start or stop a process.
- Read dayz-mcp's own agent session protocol, which ships with the tool, before the first run.
- `dayz_test_run` and `dayz_test_stop` each have their own queue, lease, heartbeat and release, so do not wrap them in a second `session_acquire`. Keep the `session_*` calls for low-level changes those tools do not cover.
- A run is identified by its `run_id`. Loading the same mod as another run gives you no ownership of that run.
- While a retail game opened by hand is running, only reads are allowed. If whoever opened it cannot close it from its own menu, declare `manual_cleanup_required`.

## What the run request asks for

- Mode `all`, server plus client. Captures read the rendered client; a server-only run has no window to grab.
- A build when the PBO changed.
- `@DayZ_MCP` beside the mod under test, so that both the server bridge and the client bridge poll the MCP server on loopback. `dayz_test_run` does not add it on its own and still answers `succeeded`: pass `extra_mods=["@DayZ_MCP"]` (`verb-gotchas.md`, "Six traps that cost a run each").

## Adopt the run before the first verb

When `dayz_test_run` finishes, it releases its owner lease (the daemon audit shows `session_release_finished reason=owner_release`) and the run moves to `RUNNING_IDLE` with no owner (`release_owner`, `process_lifecycle.py:958` to `:976`). From then on every `/enqueue` on that run is rejected, reads included: `_enqueue_run_rejection` ignores the `mutation` flag (`loopback.py:1293` to `:1296`) and for `RUNNING_IDLE` returns `run_not_owned` (`:1317` and `:1318`) with the hint "This run has no owner (RUNNING_IDLE). Adopt the existing run before dispatching." (`:99` to `:102`).

The `bridge_status` counter for these is named `fence.mutation_rejects_by_code` (`:2821` and `:2822`), but it counts reads too. Every verb that crosses the bridge is rejected (`query_*`, telemetry, raycast, captures, `world_spawn`), and so is `wait_for(players_at_least|players_at_most)`, which polls through `query_all_players` (`server.py:2645` to `:2650`). `wait_for(log_matches)` is not rejected: it reads log files without the bridge (`server.py:2603` to `:2637`).

1. `dayz_test_run(...)`. Keep the `run_id`.
2. Optional, without adopting: `wait_for(log_matches, "...")` to wait for the boot in the RPT.
3. `session_acquire_wait(purpose=...)`. The grant adopts the only ownerless `RUNNING_IDLE` run and reports it in `adopted_run` (`_adopt_on_grant`, `loopback.py:3193` to `:3230`). Check `adopted_run.ok` before the first verb. With several idle runs it answers `adopted_run.error = "multiple_idle_runs"` and adopts none (`:3202` to `:3208`): stop the extra run with `dayz_test_stop` and repeat.
4. `wait_for(players_at_least, 1)`, then the other verbs.
5. `session_release`, then `dayz_test_stop(run_id)`.

A current client shows the rejection as `run_not_owned: This run has no owner (RUNNING_IDLE)...`; older dayz-mcp clients showed a bare `remote_error` with no code. Either way, adopt; do not retry and do not relaunch. This also applies to the first step of "Opening a mod's UI without a keyboard" in `actions-ui-and-inventory.md`.

## Leases run out on their own

- The adopted lease lasts 120 s and nothing renews it for you. Send `session_heartbeat` at least every 90 s or so for the whole run, also while a person plays. Past the deadline the run is ownerless again (`grace.remaining_s` counts down) and the daemon stops it (`lifecycle_stop_outcome: stopped`), even with the user in front of the game.
- `wait_for` on the log does not renew the lease; a wait longer than about 2 minutes ended with `lease_expired`. Put a `session_heartbeat` between waits.
- When a user message interrupts a call in progress (a long `wait_for`), the next `session_heartbeat` answers `lease_invalid: token was never valid for this client`. If the run is still alive, `session_acquire_wait` adopts it again.
- `dayz_test_close` shuts the run down in order, with a termination line on both sides.
- Only `dayz_test_run` and `dayz_test_stop` manage their own lease. Every other verb that crosses the bridge needs `session_acquire`, which includes adopting the idle run as above.
- The diag client dies after about 6 minutes without commands (`client_not_polling`). In a long session run a keepalive, for example `vehicle_telemetry` every 45 s or so.

## Keep the whole run in one process

When the agent's shell runs commands as a process tree that is torn down with the call, the daemon it spawned dies with that tree: a child that "broke away" did not survive, and adopting an outside daemon did not work either. So keep the whole sequence in one process: a preventive stop, the run, a wait for the bridge, a wait for the player, a teleport under a lease, the work, then `dayz_test_stop`.

## The test machine is one shared resource

- Port 2302 and the Steam client are single resources. Share them through the FIFO lease of dayz-mcp's protocol, not by guessing whose processes are running and not by evicting other sessions. `dayz_test_run` takes and holds the machine; keep its `run_id` and end that same run with `dayz_test_stop`.
- Never kill a process to free the machine. If the state does not reconcile, leave the process and declare a degraded shutdown.
- Do not start the game with `cmd start` or a `.bat` for an MCP check: that creates a process outside the managed lifecycle, and there is no fallback that goes around it.
- In this repo that means: never start an MCP run with `/dayz-launch-test` or end one with `/dayz-stop-test`, which kills every `DayZDiag_x64.exe` on the machine. `/dayz-gate build`, `ingame`, `behavior` and `visual` also stop a running session before they start (they ask first, or need `--yes`), so do not run a gate while an MCP run is alive.
- A game started by hand polls as `LEGACY_UNBOUND` and allows reads only (measured on Linux, `../linux.md`; not measured again on Windows).

### `blocked_on` in `session_status` is an instruction

With the machine taken, `session_status` returns:

```json
"blocked_on": "DayZ test box; next: call dayz_test_run(..., wait_for_box_s=<n>) to join the box FIFO"
```

The reply names the queue; join it. `dayz_test_run(..., wait_for_box_s=600)` then answered `active_run_exists` with `hint: "stop it with dayz_test_stop(run_id=...)"`, again the next step. An unattended session that only waited for another session to say it was done sat idle for hours while the other side held a test setup it never used.

1. If a tool tells you how to unblock yourself, do it before you wait for anyone.
2. An unattended session has no "wait until told". Join the queue, or give the holder a deadline. "When the user finishes" is not a deadline: whoever offers it should release the machine and ask for it again later, since a relaunch takes minutes and a test object takes two verbs to rebuild.

### A free lease does not mean a free machine

`session_status` can return `owner: null`, an empty queue and `claimable: true` while a DayZ server and client started outside the managed lifecycle hold port 2302. The lease describes the lease, not the machine. Before you treat the machine as free, read the `-mod=` of the running processes:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" |
  Select-Object ProcessId, CommandLine
```

The command line says whose run it is and whether it loads your mod. For a build, the "no DayZ process" check can be narrowed to the two things it stands for: no running process loads your mod, and the target PBO can be opened exclusively. The same rule applies when launching (`/dayz-launch-test`).

### A machine that looks free can be taken seconds later

`bridge_status` once showed the machine free (no peers, no lease, no runs) and 40 s later another run started outside the lifecycle without a lease; a probe then teleported that run's player. Before any change on "the first player", check `bridge_status.coordination.active`, `server_peer.last_poll_age_s` and:

```powershell
Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe'"
```

If a server that is not yours is polling, change nothing.

## The dayz-labs companion

The dayz-labs tool can serve as a reference or an optional companion, but it has no say over a dayz-mcp run (`external_companion_no_lifecycle_authority`). Its `start`, `stop` and `restart` verbs are off limits while dayz-mcp holds a run: only `dayz_test_run` and `dayz_test_stop` on the exact `run_id` control it. Do not install or update it as part of a check, and always record the `pinned_version` you examined.

Its interface is WPF and it captures its own window (`wpf_not_layout_evidence`). A good capture from dayz-labs says nothing about how a DayZ `.layout` parses, scales, clips or reads; a UI check needs its own render compared against the game.
