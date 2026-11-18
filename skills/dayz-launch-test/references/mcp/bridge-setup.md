# Bridge setup and health

What must be true before the first dayz-mcp verb (tools registered, config and key seeded, both peers polling, mods loadable) and what each bridge failure means.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game sessions with that tool and not checked on `P:\`; the one vanilla fact, the REST error code, is cited. `<dayz-mcp>` is the folder of your dayz-mcp checkout, and names such as `MCPBridge.c` or `dayz_test_tool.py` are files of its source. Its own `tools\README-mcp.md` (startup order, bridge troubleshooting) and its live state handoff file (server invariants, tool list, known limits) are the tool's first hand documents.

## Prerequisites, in order

1. **The dayz-mcp server is registered and reachable.** The real check is whether the `mcp__dayz-mcp__*` tools are available in the session; if a tool search finds them, it passes. `claude mcp list` is not reliable: it prints a false `Failed to connect` while the server works, so never block on it when the tools are there. The tools appear only in a session started after the server was registered (broker registration with `--client`, see "Troubleshooting").
2. **The bridge config is seeded.** The in-game bridge reads `dayz_mcp.json` (url, key, pollHz) from its profile folders; the server uses `<dayz-mcp>\tools\.dayz_mcp.key`. Seed the same key into the launch profiles with dayz-mcp's `install-mcp.ps1`, pointed at the folders the launcher made:

   ```powershell
   <dayz-mcp>\tools\install-mcp.ps1 `
     -ServerProfiles "<TargetMod>_dev\_server\profiles" `
     -ClientProfiles "<TargetMod>_dev\_client\profiles" `
     -MissionPath "<...>\mpmissions\dayzOffline.chernarusplus"
   ```

   Seeding for an arbitrary mod plus `@DayZ_MCP` through the launcher script has only been run through one project's own runner, so check it on the first run: if `bridge_status` reports `last_poll_age_s = null`, the config is not where the bridge looks. Fix the path and say so in the report.
3. **`bridge_status` is green.** It is always the first call. `server_peer` needs a fresh `last_poll_age_s` (not null), and for captures `client_peer` too. "Never polled" means the bridge did not start (config, key or boot): stop and diagnose rather than drive blind.
4. **The tool can load every mod in `extra_mods` or `base_mods`.** See the next section.

## Which mods the launch accepts

Two layers decide, and mixing them up costs a session.

- The public check `_valid_public_mod` in `dayz_test_tool.py` calls `dayz_test_request._valid_mod_entry`: it refuses `:`, `\` and `/` for every project, except an absolute path inside the selected project's `mod_roots`. A Workshop path lies outside those roots and fails with `bad_mod`. That is by design, not a gap in your project's policy.
- Subscribed mods that Steam exposes in `!Workshop` (`@CF`, `@Dabs Framework`, `@VPPAdminTools`) are junctions to `steamapps\workshop\content\221100\<id>`, and the path identity guard refused `@CF` with `dayz_test_failed`, the catch-all in `server.py` that hides the real cause.

So Community Framework, Dabs and VPP are loaded by naming them with an absolute path in the project's `default_base_mods` in the launcher's `request-policy.json`, while mods in real folders (`@DayZ_MCP`, the mod under test) go in `extra_mods` by relative name. One command tells which kind a folder is:

```powershell
Get-Item '<!Workshop>\<@Mod>' -Force | Select-Object LinkType
```

`Junction` means the relative name may not work. With `preflight=true`, a pure dry check that returns before building or launching anything (in `dayz_test_worker.py`): no mods passed, `@DayZ_MCP` passed, the mod under test passed, `@CF` failed and `base_mods=["@CF"]` failed. On the stable branch after the first 1.30 patch, though, one Steam junction did pass in `extra_mods`: `@SurvivorAnims` (Workshop item 2918418331) passed `preflight=true` on project `DayZ_MCP` and loaded on server and client in two runs (`-mod=P:\Mods\@DayZ_MCP;P:\Mods\@SurvivorAnims;...` in the RPT header, the `World` module at 2349 files with its scripts). Run the preflight on the junction you need before editing `request-policy.json`.

### When the mod under test does not compile

For example when the mod's build packed another session's untracked test scripts, test a probe copy of it:

- Copy the deployed PBO entry by entry without those entries (every other entry byte identical, the same header properties, the SHA-1 trailer recomputed) into a probe folder of its own under `P:\Mods`.
- Host it in another approved project whose `default_base_mods` carry what the mod needs (Community Framework and Dabs in that run). An absolute Workshop path in `base_mods` fails with `bad_mod`, because each entry must be a folder name or an absolute path inside the project's `mod_roots`.
- Writing under `P:\Mods` changes what every later run can load. Ask the owner first, and move the probe out of `P:\Mods` when done.

In that run the copy (641 of the 645 entries) compiled the mission module, and its models were the deployed ones byte for byte.

## A stale key looks like a mod that did not load

Before blaming the bridge for `version_blocked` or `last_poll_age_s=null`, check that the `key` in the project profiles' `dayz_mcp.json` matches `<dayz-mcp>\tools\.dayz_mcp.key`. A stale key gets a 401 and the bridge never polls, the same symptom as "the mod is not loaded". Key rotations leave behind every project not run since (two of five projects still had the old key in one check).

The symptom is not always `version_blocked` or a null age. With a stale key the peer can read `version_state: ok` with a `last_poll_age_s` of 1.485 seconds, the last good poll, which may belong to a run that is already dead; a dead bridge then reads like a healthy one. The signature is in the game's script log: `[MCP-POC] poll error=5` on the server and `[MCP-CLIENT] client poll error=5` on the client. In the vanilla enum, 5 is `EREST_ERROR`, and the comment beside `EREST_ERROR_CLIENTERROR` says the two are the same value (`P:\scripts\3_game\http\restapi.c:16` and `:17`): the daemon answered 401, a number that appears nowhere on the game side.

Two checks before blaming anything:

- Compare the key of each `dayz_mcp.json` the run will use against the key file. There are two paths and `$profile:` wins over `$mission:` (`MCPBridge.c:145` to `:149`, `MCPClientBridge.c:234` to `:237`); if the profile's key is missing, the bridge falls back to the mission's, which is usually the stale one. Equal length (43) is no proof: compare the bytes.
- `Invoke-WebRequest "http://127.0.0.1:8765/poll?key=<key file content>"` answering 200 with `{"commands":[]}` proves the daemon and the live key are fine and puts the fault in the run's JSON.

The fix needs no server restart: `ReloadKeyAfterFailure` (`MCPBridge.c:373` to `:398`) reads the key again when the backoff reaches its ceiling. Fix the JSON, wait about 20 seconds, `[MCP-POC] poll key reloaded` appears, and the peer returns to a `last_poll_age_s` around 0.2. That saves the boot.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `claude mcp list` prints `Failed to connect` | `claude mcp list` prints a false failure while the server works. Before the broker existed, contention on port 8765 (an exclusive, fail closed HTTP server lock) was the real failure. | Check with a tool search first: if the `mcp__dayz-mcp__*` tools are there, ignore the line. Broker registration with `--client` removes the contention: several sessions share the server and an orphan guard frees orphans. If the tools really are missing, register in broker mode and open a new session. |
| The tools do not appear in the session | The server was registered after the session opened | Open a new session. |
| `bridge_status.server_peer.last_poll_age_s = null` | The server bridge does not poll | Check `dayz_mcp.json` in the server profiles and its key; confirm `@DayZ_MCP` is mounted (absolute mod paths). |
| `client_peer` null while the server peer is fine | The client did not connect, or `dayz_mcp.json` is missing from the client profiles | Client autoconnect is flaky: wait longer for the server or retry; seed the client config. |
| `version_state = legacy_blocked` | `--require-version` is on against a bridge that sends no `ver=` | Deploy the bridge PBO that sends `ver=4~...`, or register the server without `--require-version` for that run. Right after launch it is usually an unfinished start (below). |
| Byte identical captures between camera poses | The grab caught a stale desktop frame, not the render | `captures.md`, "Where the picture comes from". |
| A tool times out and old commands run on reconnect | A timeout leaves the command queued, and the bridge runs it when it comes back | After a timeout, reconcile with `bridge_status` before going on. |

### `legacy_blocked` right after launch

With the current bridge PBO deployed, `bridge_status` can read `legacy_blocked` ("poll did not include ver=") with `last_poll_age_s=null` right after the server starts, because the bridge has not finished its handshake. It moves to `ok` with `ver=4~...` once the server mission has fully loaded, 1 to 2 minutes later. Do not redeploy or re-register for it: wait and check again. It is a real version mismatch only if it stays `legacy_blocked` with the mission loaded (client connected, world drawn).

### During the Central Economy load the bridge looks stale

A stock mission runs the Central Economy start for 1 to 3 minutes, and meanwhile `bridge_status` reads stale (`last_poll_age_s` grows although `version_state=ok`). Do not spawn then. Wait for `connected to server` in the server's `script*.log` and for `bridge_status` to be fresh again (under 1 second). Poll the log directly on the host with PowerShell; a shell that reads it through a file system bridge can serve a cached copy.

## The daemon runs the code it loaded at start

If you add a verb to the bridge (`SERVER_COMMANDS` or `CLIENT_COMMANDS` in `loopback.py`) and the tool answers `not_whitelisted`, do not look for the bug in your change: the daemon loaded that module when it started and has not read it again. `loopback.py` and `server.py` are not sealed in `app.pyz`, so editing them takes effect without rebuilding the bundle, but nothing restarts by itself. What misleads is that the tool does show as registered in your MCP client, because the client started after the edit: the visible half says the verb exists while the half that decides still has the old list.

Compare the source's modified time with the start of the process that decides:

```powershell
(Get-Item '<...>\dayz_mcp\loopback.py').LastWriteTime
$pid_ = (Get-NetTCPConnection -LocalPort 8765 -State Listen).OwningProcess
(Get-CimInstance Win32_Process -Filter "ProcessId=$pid_").CreationDate
```

A source newer than the process is the cause; stop reading code. To restart, `Stop-Process` the listener on port 8765; the client starts it again on the next call and `daemon_generation` changes, which confirms a new process. Restarting is safe, but it disarms other live sessions' tools for a moment, so check `session_status` (owner and queue) and warn first. Right after, the first calls can return `version_blocked` or `peer_reconnect_flush`; retry rather than diagnose again, and confirm with `bridge_status` that both peers show `version_state: ok` and a low `last_poll_age_s`.

This is related to, but not the same as, the sealed bundle: `app.pyz` seals copies of the test lifecycle modules (`dayz_test_worker.py` and others), which need a rebuild; here nothing is sealed and the process is just old.

## `unapproved_debug_image` on a non-English host

On a host with a Spanish culture, `dayz_test_run(build=true)` on a project whose build runs AddonBuilder failed with `native_debug_gate_rejected:unapproved_debug_image`: the .NET helper loads localized resource satellites (`%WINDIR%\Microsoft.NET\assembly\GAC_MSIL\*.resources\v4.0_*_es_*`, for example `mscorlib.resources.dll`). Current dayz-mcp admits structurally valid `GAC_MSIL` resource satellites, so the refusal depends on the code the running server started from. The reply carries no detail (kind, process, image): find the refused image in the MCP server's stderr log (search for `unapproved_debug_image`), and restart the server on current code before treating it as a fault of the gate. It is never a fault of the mod under test.

## Widen a closed allow-list in the readers before the writers

When a config is checked against a closed set of options, and long lived readers check it again on every request, the order is: add the new value to the allow-list in code, ship that code to every reader, restart those readers, and only then write the value. Writing first makes the whole file invalid for old readers (`daemon_provenance_conflict`, fail closed). Not every resident process is a reader, so find out which read the file and when. A cheap guard is to run the validator in a fresh process right after the write and revert on failure.
