# dayz-testbridge MCP server

Lets an agent test a mod inside a running DayZ Diag session with nobody at the keyboard: spawn objects and items, teleport the player, get into a car and drive it while reading speed and state, cast rays and read surfaces, set the camera and take screenshots, set the time and weather, and read the script logs and RPT since a mark.

It has two halves, both written for this repo:

- **`AZ_TestBridge`**, a small Diag-only mod in `skills/dayz-launch-test/assets/testbridge-mod/`. It is packed to `P:\Mods\@AZ_TestBridge\` for one session and removed afterwards. Every script is inside `#ifdef DIAG_DEVELOPER`, and without `-azBridge=<token>` on the command line it does nothing.
- **This server**, which starts and stops the session, writes commands for the mod, waits for the results, captures the client window and reads the logs.

How the two talk, which peer runs each command, and the engine facts each command rests on: `skills/dayz-launch-test/references/test-bridge.md`.

Installed as a plugin, the tools appear as `mcp__plugin_agentic-z_dayz-testbridge__<tool>`.

## Tools

| Tool | What it does |
|---|---|
| `list_commands` | The allowlist: every command, its peer, arguments with defaults and bounds, and its outputs. Read-only. |
| `session_start(mods, deps, server, port)` | Copies `.server/<server>/` to `<server>-bridge` without `storage_*`, packs the bridge, runs `/dayz-launch-test <deps> <mods> --test-bridge <token>`, waits until both peers answer with the player loaded, and closes the pause menu. Empty `mods` tests vanilla. `allow_exec=true` turns on `exec` for this session only. Up to about 5 minutes. |
| `session_status` | Both processes alive, both hellos, the last sequence number per peer, new crash logs, the `-mod=` line. Read-only. |
| `session_restart(keep_storage)` | Orderly server shutdown (the world is saved), then both peers again with the same token; `keep_storage` keeps what this session saved, so a mod's saved data can be checked after a restart. |
| `session_restart_client` | Ends only the client and starts it again into the running server. |
| `session_stop` | Gets the player out of a car, ends only this session's two processes, removes `@AZ_TestBridge`, renames the token folders to `<token>.done`. Safe after a failure. |
| `command(cmd, args, peer)` | Sends one allowlisted command and returns `{seq, ok, error, peer, game_time_ms, data}`. `peer` only for `ping`, `mark`, `vehicle_state` and `exec`. `get_in` and `get_out` also wait for the server to agree (`server.agrees`). |
| `mark(label)` | Saves the end of every log under `label` and prints `[AZ-BRIDGE] MARK <label>` on both peers. |
| `logs_since(mark, peers, kinds, regex, triage, limit)` | Script log and RPT lines since a mark, with `[AZ-BRIDGE] ERROR` lines listed apart; `triage` tags each line with its `/dayz-gate` category. Read-only. |
| `screenshot(name, crop)` | Captures the client window with `PrintWindow` to `output/testbridge/<token>/<name>.png`. Never moves the mouse or brings the window to the front. A black frame is `ok: false`, not a mod failure. |

`ok: false` with an error code (`not_driver`, `vehicle_has_crew`, `spawn_failed`, `wrong_token`, `unknown_command` and the others in `test-bridge.md`) is the game's answer. A raised error is the tool's own problem: a bad argument, no session, a timeout or a peer that died.

## Safety

- Diag only, and off unless the session passes its token.
- Only a session it started: `session_start` refuses while any `DayZDiag_x64.exe` it did not start runs, and `session_stop` ends only the process ids it recorded.
- Two allowlists that must agree: `allowlist.py` here and the mod's fixed `switch` (`test_mod_matches_allowlist.py` checks it). `exec` is the only command that runs code: off unless `session_start` had `allow_exec` (the launch then passes `-azBridgeExec=1`), and every code string goes to `.server/!TestBridge/exec-<token>.log`. On DayZ Diag 1.30 the engine refuses `ExecuteEnforceScript` as a release build ("not allowed in release version"); the command is kept because other Diag builds, or a later release, may allow it (`skills/dayz-launch-test/references/test-bridge.md`). No command reads or writes arbitrary files or calls a method by name; `action_use` takes only classes that inherit `ActionBase`.
- Bounds: positions inside the world and `y` at most 2000, a search radius of at most 200 m, at most 60 s of driving, at most 50 spawns per server start (`session_restart` resets the count), and spawn flags that always include `ECE_NOPERSISTENCY_WORLD`.
- Test runs never touch your world: sessions run on the storage-free `<server>-bridge` copy.
- `/dayz-release-pack` refuses any release that names `AZ_TestBridge` or an `AZB_` class.

## Setup

1. `pip install -r .claude\mcp\dayz-testbridge\requirements.txt` (`mcp`, and `pillow` for screenshots).
2. A test server instance from `/dayz-add-server`, and `/dayz-preflight` passing (P:\ mounted, DayZ Tools, DayZ Diag).
3. The plugin registers the server in `.claude-plugin/plugin.json`. Restart Claude Code and check `/mcp` shows `dayz-testbridge` connected.

If it fails to start, run it directly to see the error:

```cmd
python .claude\mcp\dayz-testbridge\server.py
```

The session record is `.server/!TestBridge/session.json`; a restarted server reads it, so `session_stop` still works after a restart.

## Files

| File | Job |
|---|---|
| `server.py` | The MCP tools. |
| `allowlist.py` | Commands, peers, argument bounds, outputs, and the full wire argument object. |
| `bridge.py` | The file protocol: token folders, sequence numbers, atomic writes, results, timeouts. |
| `session.py` | Start, status, stop, marks and logs of one session. |
| `logs.py` | Log offsets, marks, rotated files, triage. |
| `fakepeer.py` | A stand-in for one peer of the mod, used by the tests. |

The in-game smoke test is `scripts/dev/testbridge_smoke.py`.
