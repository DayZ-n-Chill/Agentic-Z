# Bridge setup, health checks and troubleshooting

What must be true before the first verb (tools registered, config and key seeded, both peers polling, mods loadable) and what each bridge failure means.

Everything here is behaviour of the third-party dayz-mcp server and its `@DayZ_MCP` mod, measured in game sessions with that tool, not yet checked on `P:\`. The one vanilla fact, the REST error code, cites its file. `<dayz-mcp>` is the folder of your dayz-mcp checkout; file and line numbers such as `MCPBridge.c:145` are lines of dayz-mcp's own source at the time of the measurement. dayz-mcp's own `tools\README-mcp.md` (startup order, bridge troubleshooting) and its live-state handoff file (server invariants, the tool list, known limits, backlog) are the tool's first-hand documents.

## Prerequisites, in order

1. **The dayz-mcp server is registered and reachable.** The primary check: are the `mcp__dayz-mcp__*` tools available in the session? If a tool search finds them, the gate passes. `claude mcp list` is a secondary check and not reliable: it prints a false `Failed to connect` while the server works, so do not block on it when the tools are there. The tools are only available in a session started after the server was registered (broker registration with `--client`, see the table below).
2. **The bridge config is seeded.** The in-game bridge reads `dayz_mcp.json` (url, key, pollHz) from its profile folders; the MCP server uses `<dayz-mcp>\tools\.dayz_mcp.key`. Seed the same key into the launch profiles with dayz-mcp's `install-mcp.ps1`, pointed at the folders the launcher generated:

   ```powershell
   <dayz-mcp>\tools\install-mcp.ps1 `
     -ServerProfiles "<TargetMod>_dev\_server\profiles" `
     -ClientProfiles "<TargetMod>_dev\_client\profiles" `
     -MissionPath "<...>\mpmissions\dayzOffline.chernarusplus"
   ```

   Verify on the first run: generic seeding (any mod plus `@DayZ_MCP` through the launcher script) had only been exercised through one project's own runner. The first run of this skill shows whether the bridge finds its config in these folders; if `bridge_status` reports `last_poll_age_s = null`, the config is not where the bridge looks, so fix the path and say so in the report.
3. **`bridge_status` is green.** It is always the first call. `server_peer` must have a fresh `last_poll_age_s` (not null), and for captures `client_peer` too. "Never polled" means the bridge did not start (config, key or boot): stop and diagnose, do not keep driving blind.
4. **Every mod passed in `extra_mods` or `base_mods` must be loadable by the tool.** See the next section.

## Which mods the launch accepts

Two layers decide, and confusing them costs a session.

- The public boundary `_valid_public_mod` (`<dayz-mcp>\tools\dayz_mcp\dayz_test_tool.py:75-85`) rejects `:`, `\` and `/` for every project, so an absolute Workshop path never passes through the tool. That is by design, not a gap in your project's policy. Updated 2026-10-03: the boundary now also accepts an absolute path inside the selected project's `mod_roots`; `_valid_public_mod` calls `dayz_test_request._valid_mod_entry` (`dayz_test_tool.py:269-272`, `dayz_test_request.py:222-233`, dayz-mcp commit `506de5d`). A Workshop path lies outside those roots and still fails, with `bad_mod`.
- Subscribed mods that Steam exposes in `!Workshop` (`@CF`, `@Dabs Framework`, `@VPPAdminTools`) are junctions to `steamapps\workshop\content\221100\<id>`, and the path identity guard rejected them with `dayz_test_failed`, the generic catch-all of `server.py:1101`, which hides the real cause.

Consequence: CF, Dabs and VPP are loaded by declaring them with an absolute path in the project's `default_base_mods` inside the launcher's `request-policy.json`. Mods that are real folders (`@DayZ_MCP`, the mod under test) go in `extra_mods` by relative name.

One command tells which kind a mod folder is:

```powershell
Get-Item '<!Workshop>\<@Mod>' -Force | Select-Object LinkType
```

`Junction` means the relative name did not work. Measured 2026-08-02 with `preflight=true` (a pure dry check: `dayz_test_worker.py:533-534` returns before building or launching anything): no mods passed, `@DayZ_MCP` passed, the mod under test passed, `@CF` failed, `base_mods=["@CF"]` failed.

[EXACT][CLAIM-MCPV-JUNCTION-EXTRA-MODS-130] Corrected 2026-10-26 (stable branch, DayZDiag 1.30.164200): a Steam junction did pass in `extra_mods`. `@SurvivorAnims`, a mount-point junction in `!Workshop` (Workshop item 2918418331), passed `preflight=true` with project `DayZ_MCP` and then loaded in two runs, on server and client (`-mod=P:\Mods\@DayZ_MCP;P:\Mods\@SurvivorAnims;...` in the RPT header, the `World` module at 2349 files with its scripts). The rejection above was measured on 2026-08-02 with `@CF`. Run the preflight on the junction you need before going through `request-policy.json`.

### When the mod under test does not compile, test a probe copy of it

[EXACT][CLAIM-MCPV-PROBE-COPY] Added 2026-10-03, measured 2026-10-02 (dayz-mcp run 606a5dbb), for example when the mod's build packed another session's untracked test scripts:

- Copy the deployed PBO entry by entry without those entries (every other entry byte-identical, the same header properties, the SHA-1 trailer recomputed) into a probe folder of its own under `P:\Mods`.
- Host it in another approved project whose `default_base_mods` carry what the mod needs (CF and Dabs in that run). An absolute Workshop path in `base_mods` fails with `bad_mod`, because each entry must be a folder name or an absolute path inside the project's `mod_roots` (`dayz_test_tool.py:399`, `dayz_test_request.py:222-233`).
- Writing under `P:\Mods` changes what every later run can load. Ask the owner in chat first (in that session the agent harness's permission check blocked the write until the owner agreed), and move the probe out of `P:\Mods` when done.

In that run the copy (641 of the 645 entries) compiled the mission module, and its models were the deployed ones byte for byte.

## A stale key looks like a mod that is not loaded

Before blaming the bridge for `version_blocked` or `last_poll_age_s=null`, check that the `key` in the project profiles' `dayz_mcp.json` is the same as `<dayz-mcp>\tools\.dayz_mcp.key`. A stale key gives 401 and the bridge never polls, with the same symptom as "the mod is not loaded". Key rotations leave behind every project that was not run since (2026-08-02: two projects still had the old key, three had the current one).

The symptom is not always `version_blocked` or `last_poll_age_s=null` (measured 2026-08-17 in LFPowerGrid, with the paragraph above already written and overlooked). With a stale key the peer can read `version_state: ok` with a `last_poll_age_s` of 1.485 s (the figure as the source session recorded it): that is the last good poll, which may belong to a run that is already dead. A dead bridge reads like a healthy one this way. The signature is in the game's script log: `[MCP-POC] poll error=5` on the server, `[MCP-CLIENT] client poll error=5` on the client. That 5 is `EREST_ERROR_CLIENTERROR`, which the vanilla enum comments as equal to `EREST_ERROR` (`P:\scripts\3_game\http\restapi.c:16-17`), meaning the daemon returned 401. The number 401 appears nowhere on the game side.

A two-command gate before blaming anything:

- Compare the key of each `dayz_mcp.json` the run will use against the key file. There are two paths and `$profile:` wins over `$mission:` (`MCPBridge.c:145-149`, `MCPClientBridge.c:234-237`); if the profile's key is missing, the bridge falls back to the mission's key, which is usually the stale one. The same length (43) is not proof: compare the bytes.
- `Invoke-WebRequest "http://127.0.0.1:8765/poll?key=<key file content>"` answering 200 with `{"commands":[]}` proves the daemon and the live key are fine and isolates the failure to the run's JSON.

Fixing it does not need a server restart: `ReloadKeyAfterFailure` (`MCPBridge.c:373-398`) rereads the key when the backoff reaches its ceiling. Fix the JSON, wait about 20 s, `[MCP-POC] poll key reloaded` appears and the peer returns to a `last_poll_age_s` of 0.2. That saves the boot.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `claude mcp list` prints `Failed to connect` | `claude mcp list` is not reliable: it prints a false failure while the server works. Contention on port 8765 (an exclusive HTTP server lock, fail-closed) was the failure mode before the broker existed | Check first with a tool search: if the `mcp__dayz-mcp__*` tools are available, ignore the failure line. Broker registration with `--client` (since 2026-06-24) removes the port contention: several sessions share the server, and an orphan guard releases orphans. If the tools really are missing, register in broker mode (`--client`) and open a new session (tools load at session start) |
| The tools do not appear in the session | The server was registered after the session opened | Open a new session |
| `bridge_status.server_peer.last_poll_age_s = null` | The server bridge does not poll | Check `dayz_mcp.json` in the server profiles and its key; confirm `@DayZ_MCP` is mounted (absolute mod paths) |
| `client_peer` null while the server peer is fine | The client did not connect, or `dayz_mcp.json` is missing from the client profiles | Client autoconnect is flaky (BUG-009): use a longer server wait or retry; seed the client config |
| `version_state = legacy_blocked` | `--require-version` is on against a bridge that sends no `ver=` | Deploy the bridge PBO that sends `ver=4~...`, or register the server without `--require-version` for that run. Right after launch it is usually an incomplete init, see below |
| Byte-identical captures between camera poses | The grab caught a stale desktop frame, not the render | See `captures.md`, "How the window grab behaves" |
| A tool times out and "zombie" commands run on reconnect | BUG-024: a timeout leaves the command queued and the bridge runs it when it returns | After a timeout, reconcile with `bridge_status` before continuing |

### `legacy_blocked` right after launch is usually an incomplete init (added 2026-06-28)

With the current bridge PBO deployed, `bridge_status` can read `legacy_blocked` ("poll did not include ver=") with `last_poll_age_s=null` right after the server starts, because the bridge has not finished its handshake. It moves to `ok` with `ver=4~...` when the server mission has loaded completely (1 to 2 minutes). Do not redeploy or re-register for that: wait and check again. It is a real version mismatch only if it stays `legacy_blocked` with the mission loaded (client connected, world rendered). Origin: a vehicle project's phase 5, 2026-06-28.

### During the Central Economy load the bridge looks stale

A stock mission runs the Central Economy start for 1 to 3 minutes. During that time `bridge_status` reads stale (`last_poll_age_s` grows although `version_state=ok`). Do not spawn then. Wait for `connected to server` in the server's `script*.log` and for `bridge_status` to be fresh again (under 1 s). Poll the log directly on the host with PowerShell; a shell that reads it through a file-system bridge can serve a cached copy (LL-142).

## The daemon serves the code it loaded at startup (LL-223, added 2026-07-29)

If you add a verb to the bridge (`SERVER_COMMANDS` or `CLIENT_COMMANDS` in `loopback.py`) and the tool answers `not_whitelisted`, do not look for the bug in your diff: the daemon loaded that module when it started and has not read it again. `loopback.py` and `server.py` are not sealed in `app.pyz`, so editing them takes effect without rebuilding the bundle, but nothing restarts on its own.

What misleads most: the tool does appear registered in your MCP client, because the client started after the edit. The visible half of the system confirms the verb exists while the half that decides still has the old list.

Check the source's modification time against the start of the process that decides:

```powershell
(Get-Item '<...>\dayz_mcp\loopback.py').LastWriteTime
$pid_ = (Get-NetTCPConnection -LocalPort 8765 -State Listen).OwningProcess
(Get-CimInstance Win32_Process -Filter "ProcessId=$pid_").CreationDate
```

Source newer than process means that is the cause; stop reading code. Measured 2026-07-29: `loopback.py` at 15:57:54 against a daemon started at 14:18:42.

To restart: `Stop-Process` on the listener of port 8765. The client starts it again lazily on the next call and `daemon_generation` changes, which confirms it is another process. Restarting the daemon is declared safe (BUG-062b). Warn first: it disarms the MCP tools of other live sessions for a moment, so check `session_status` (owner and queue) before.

After the restart there is a handshake window: the first calls can return `version_blocked` or `peer_reconnect_flush`. They are transients; retry, do not diagnose again. Confirm with `bridge_status` that both peers have `version_state: ok` and a low `last_poll_age_s`.

This is a sibling of the sealed bundle trap but not the same: there `app.pyz` seals copies of the test lifecycle modules (`dayz_test_worker.py` and others) and needs a rebuild; here nothing is sealed, the process is just old. Origin: the in-game gate of `query_all_players` (2026-07-29).

## `unapproved_debug_image` on a host with a non-English culture (added 2026-10-03)

On a host with a Spanish (`es`) culture, `dayz_test_run(build=true)` on a project whose build runs AddonBuilder failed with `native_debug_gate_rejected:unapproved_debug_image` on 2026-10-03: the .NET helper loads localized resource satellites (`%WINDIR%\Microsoft.NET\assembly\GAC_MSIL\*.resources\v4.0_*_es_*`; seen: `mscorlib.resources.dll`). The MCP server's debug gate admits structurally valid `GAC_MSIL` resource satellites since a fix of 2026-10-01, so the rejection depends on the code the running server was started from. The reply on the wire carries no detail (kind, pid, image): read the rejected image in the MCP server's stderr log (search for `unapproved_debug_image`), and restart the server on current code before treating the rejection as a defect of the gate. It is never a defect of the mod under test.

## Widen a closed allowlist in the readers before the writers (LL-494, 2026-09-10)

When a config is validated against a closed set of options and long-lived readers validate it again on every request, the order is: (1) add the new token to the allowlist in code, (2) ship that code to every reader, (3) restart those readers, (4) only then write the value. Writing first makes the whole file invalid for old readers (`daemon_provenance_conflict`, fail-closed). Not every resident process is a reader: measure which ones read the file and when. A cheap check is to run the validator in a fresh process right after the write and revert on failure.
