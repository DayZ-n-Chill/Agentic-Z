# Managed runs through dayz-mcp

How a test run is started, owned and stopped through the third-party dayz-mcp server (`dayz_test_run`, `dayz_test_stop`, its sealed native launcher and allow-list), the unmanaged fallback, and the traps on that route. Read it only on a machine that uses dayz-mcp; a plain `/dayz-launch-test` session needs none of it. The bridge side of the same tool is in `mcp/`.

Everything here is behaviour of dayz-mcp, its launcher and its `@DayZ_MCP` mod, measured in game sessions on a Windows test machine. None of it is vanilla, so none of it can be checked on `P:\`. Names such as `dayz_test_request.py` are files of dayz-mcp's own source; `<dayz-mcp>` is the folder of your dayz-mcp checkout.

## Who owns a run

Read dayz-mcp's agent session protocol, which ships with the tool, before the first launch. Its launcher is diag only and enforces this:

| Route | Executable and role | Lifecycle |
|---|---|---|
| Managed diag | `DayZDiag_x64.exe`, including the `-server` role | `managed_lifecycle=true`; `dayz_test_run` owns lease, heartbeat and release and returns a `run_id`. |
| Dedicated server | `DayZServer_x64.exe` | `managed_lifecycle=false`; probe gated and never started by the launcher. |
| Manual retail | A session the user opened outside the launcher | No agent lifecycle; it puts the machine in retail quarantine. |

1. Run `bridge_status` first. Under retail quarantine only reads are allowed.
2. Start a managed server or client with `dayz_test_run` and stop it with `dayz_test_stop` for its exact `run_id`. They own the queue, the lease, the heartbeat and the release; never take another lease around them.
3. `session_acquire`, `session_wait`, `session_heartbeat` and `session_release` remain for low level mutations the public tools do not cover, and for adopting the run. When `dayz_test_run` completes it releases its lease and the run stays `RUNNING_IDLE` with no owner; every bridge verb on it, reads included, is refused with `run_not_owned` until `session_acquire_wait` adopts it (check `adopted_run`). Sequence: `mcp/run-lifecycle.md`, "Adopt the run before the first verb".
4. The approved launcher gets `DAYZ_MCP_CLIENT_ID_JSON` and `DAYZ_MCP_LEASE_TOKEN` only through the process environment. `../scripts/dayz-test.ps1` captures them, removes them from the parent environment and restores them only around the child. Never copy their values to a shell, an argument, a log or a handoff, and never call the approved launcher directly.
5. Keep the returned `run_id`. Loading the same mod grants no ownership: stopping and adopting need the exact run. `-Kill` without `-RunId` fails closed.
6. Check the final state after a stop. Never replace the lifecycle guard with a kill, or with a guess based on process name, mod, command line or profile.
7. After adopting, keep the run owned: the lease lasts 120 seconds and nothing renews it, so send `session_heartbeat` at least every 90 seconds for the whole run, also while a person plays. Without heartbeats the run loses its owner and the daemon stops it after the grace period (`mcp/run-lifecycle.md`, "Leases run out on their own").

A retail session opened by hand puts the machine in retail quarantine: the user who opened it closes it through its UI and then runs doctor and rescan. Without access to that UI, declare `manual_cleanup_required`; another agent neither kills nor adopts the process.

## Launching without the managed route

`dayz-test.ps1` and `dayz_test_run` are the managed path. If the `approved-launchers.json` registry does not let the project through, or the daemon on its port is down (`session_status` reports `daemon_unavailable`), that path does not launch. With no DayZ process running and the user's explicit permission, the fallback is an unmanaged launch; it is never the default.

- Do not start the executable from the agent's shell. On a machine with the registered launcher, a DayZDiag started outside it stays alive with 0 CPU and writes no RPT. Alive, 0 CPU and no RPT means the launch came from the agent, not a bad argument or mod.
- Do not use `Start-Process -ArgumentList` for DayZDiag: in Windows PowerShell 5.1 an array does not guarantee quoting of each element. In six paired attempts, `cmd /c start` with literal quotes around each value containing spaces started the game, while `Start-Process -ArgumentList` hung at about 0.06 seconds of CPU without writing even the RPT header.
- When `cmd /c start` launches a `.bat`, the new window runs `cmd /K`: an `exit /b` at the end of the bat exits the script, not the interpreter, and one idle console window stays behind per launch (nine after two days of server starts on Windows 11). Wrap it in a second `cmd /c`: `cmd /c start "<title>" cmd /c "<abs bat>"`. A preflight failure with `pause` inside the bat stays visible.
- The recipe: the agent writes one `.bat` for the server and one for the client, with literal quotes around each value with spaces, and the user double-clicks them in the desktop session. Read `script.log` and the RPT with `FileShare.ReadWrite`. Close through the UI, not by process id, unless the process is the agent's own stuck one (then `Stop-Process -Id` with the exact id).

Command lines for those `.bat` files, not tested as written:

```bat
DayZDiag_x64.exe -server "-config=<serverDZ.cfg>" "-profiles=<server-profiles>" "-mission=<mission-abs>" "-mod=<mod-abs-semicolon-list>" -filePatching -port=2302
DayZDiag_x64.exe "-mod=<mod-abs-semicolon-list>" -connect=127.0.0.1 -port=2302 "-profiles=<client-profiles>" -name=Dev -window -filePatching
```

Since 1.30 both may add `-cacheP3D=1` and `-resolveFilePatchingUsingEnfusion=1` (the second needs `-filePatching`), and `-mod=` may name an unpacked source folder (`dayz-1-30.md`).

Three traps on this path that do not come from the command line:

- **Stuck Workshop.** A `workshop_log.txt` with "No workshop depot defined, skipping non-legacy item" on each item (`NeedsDownload=1`) clears with `steam://validate/221100`, which refreshes the app info. Neither the launcher nor the download page clears it.
- **Default RPT folder.** If `-profiles` does not reach the executable, DayZDiag writes the RPT and script log to `%LOCALAPPDATA%\DayZ`. Look there before deciding nothing was written.
- **VPPAdminTools superadmin.** Current versions read `<profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` (ids only, one per line); `SuperAdmins.json` is the old format and is ignored. With `vppDisablePassword=1` and the id in the `.txt`, the menu opens directly.

## The client needs Steam

The client needs Steam running; the server does not. A client launched with Steam down exits at once, writes an RPT of 793 bytes holding only the header, leaves an `ErrorMessage_*.mdmp`, and logs nothing useful. The real message is only in the minidump: extract its strings and look for `Unable to locate a running instance of Steam`. There is no Windows "Application Error" event, because the engine handles it. Check `Get-Process steam` before launching a client, and start Steam with `steam.exe -silent` if it is missing, from a shell outside any sandboxed desktop app (`diag-direct-launch.md`).

When that message appears while Steam is running, launch the dead half yourself. In one series the client died on 5 launches in a row with that string and `[API loaded no]` in the dump, while `Get-Process steam` showed a live process, `HKCU\Software\Valve\Steam\ActiveProcess` held a non-zero `ActiveUser` whose `pid` matched it, and Steam, DayZDiag and the daemon all ran as the same unelevated user. Restarting Steam twice changed nothing. Only the client needs the Steam API, so start the client from your own user shell with the same command line (take it from the RPT header or the dump):

- If your client dies too, the host or Steam is really broken, and the fix belongs to the user.
- If it lives, the daemon's spawn context breaks it, not the host, and restarting Steam will not help.

In that case it lived: it booted, connected and reached the in-game HUD. `capture_screenshot` works on it, because capture runs on the host and is not a bridge verb. A client you launch yourself is unknown to the run record, so the instance fence refuses its polls (`unaccredited_polls_by_class.instance_unknown` climbs) and no client verb reaches it; with no `camera_set` there is no framing. It puts a person in front of the screen, not an automated reading.

When it is the daemon, measure again before treating it as permanent. The same launch later succeeded first time (`client_alive=true` at 17 seconds, player in game at 51) with nothing changed but `session_status.daemon_generation`: the fault was daemon state, and a daemon restart cleared it. Record `daemon_generation` with the failure, compare it on retry, and give a freshly restarted daemon one clean launch before spending a session on a workaround.

A client started from a shell inside the Claude or Codex desktop app can read a Steam that is gone, because those apps keep a private copy of `HKCU` for the processes they start (`diag-direct-launch.md`, "A desktop app can show the game a dead Steam"). An agent's `Start-Process` of the retail client from such a shell read the `pid` of a Steam gone for ten days and died with the message above, while the same day's `dayz_test_run` launches passed, because the daemon runs outside the app. It also fools the test above: a launch by hand from such a shell dies for this reason, not because the host is broken.

- Before a launch by hand from an app shell, compare `(Get-ItemProperty HKCU:\Software\Valve\Steam\ActiveProcess).pid` read there with `(Get-Process steam).Id`. dayz-mcp's `session_status` reports a mismatch as the warning `steam_app_view_stale`.
- Launch from outside the app instead: from Steam, from Explorer, or through WMI (`Win32_Process.Create`, as the daemon does).
- Never start Steam, or write or delete its registry keys, from the app's shells; that creates or freezes the copy, and only an offline edit of the app's hive with the app closed removes it (dayz-mcp's `tools/clear-app-steam-shadow.ps1`).

## Requests the launcher refuses

- **A UTF-8 byte order mark.** `Out-File -Encoding utf8` in Windows PowerShell 5.1 writes one, and the parser refuses the whole request with `invalid_dayz_test_request`. Write it with `[IO.File]::WriteAllText($path, $json, (New-Object Text.UTF8Encoding($false)))`, or copy a known good request file and replace the fields.
- **Two coupled rules** in `dayz_test_request.py`, both reported as the same `invalid_dayz_test_request`: `kill: true` needs a `run_id`; with a `run_id`, `mode` may not be `server` or `all`, and `mode: "client"` needs a `run_id`. The valid shapes are `server` or `all` without a `run_id` (starts a run), `client` with one (joins it), and `mode: "client"` with `kill: true` and the `run_id` (stops the whole run). `mode="pair"` does not exist and returns `bad_dayz_test_request` without naming the valid modes.
- **`extra_mods` replaces the list, it does not extend it.** `extra_mods=["@MyMod"]` drops the project's other extras; if `@DayZ_MCP` was among them, every verb stops working although the pair boots, and `bridge_status.ready.reason` reads `server_poll_stale` with `last_poll_age_s` frozen at the previous run's value. Check the server script log for `DayZ_MCP` in any module's `defines:` or for `[DayZ-MCP] config loaded ... poll_hz=`; if neither is there the mod did not load. Always name `@DayZ_MCP` in `extra_mods`.
- **A client rejoin needs the list again.** On `mode=client`, leaving out `extra_mods` does not inherit the server's list; it fails with `bridge_mod_missing: add extra_mods=['@DayZ_MCP']`. Pass the same list as for `mode=server`; a different list also changes the mod set's seal.
- `mode: "all"` starts both in one request, but `server`, a wait, then `client` with the same `run_id` was the more reliable sequence.

## Mods the sealed launcher accepts

On a machine where DayZDiag only starts through the registered native launcher, a mod outside the sealed allow-list of `dayz-test-v1` cannot launch under a project of its own. It can still be tested by riding on an approved project.

- `extra_mods` on an approved project: `_mods` in `dayz_test_worker.py` appends every value to the launch list, and `_mod_path` joins a relative value to the sealed `mods_root`, so a bare `@Name` is accepted under `P:\Mods`. `_valid_mod_entry` in `dayz_test_request.py` refuses anything with `:`, `\` or `/`, refuses `.` and `..`, and requires `ntpath.normpath(value) == value`; an absolute path is accepted only inside a sealed root. For a throwaway probe: `dayz_test_run(project="DayZ_MCP", mode="all", extra_mods=["@MyProbe"])` starts the full bridge plus your probe without touching the sealed policy.
- The deployed folder must be real, not a reparse point. `request_path_authority._open_descendant` refuses any path part whose `reparse_tag != 0`. A dependency that is a junction under `P:\Mods` (`@CF`, `@Dabs Framework`, `@VPPAdminTools`, all pointing into the Steam Workshop) must be listed in `default_base_mods` by its absolute Workshop path, and that path must be sealed in `mod_roots`. A locally built mod in a real folder can be a bare relative name. Check `Get-Item <path> | Select-Object LinkType` before choosing the form; the wrong form passes every unit test, which only pin strings, and fails when the server launches. One Workshop junction, `@SurvivorAnims`, did pass in `extra_mods` and loaded on both sides, so run the preflight on the junction you need before editing `request-policy.json` (`mcp/bridge-setup.md`).
- Pick a carrier project that compiles that day. Script compilation stops at the first mod that fails, so a broken carrier's error shows only once yours compiles, which reads as "my mod broke it". One project carried two and then four extra mods with `Module: Mission; loaded ...` and no `CParser` line in both peers' logs, while another carrier, fine two months earlier, stopped at `Can't compile "Mission" script module!` on its own `5_Mission`. Before reading your mod's errors, find the carrier's `Module: Mission; loaded ...` line; when it is missing, `Can't compile "Mission" script module!` and the `crash_*.log` name the failing file.

Giving a mod its own sealed entry is the expensive path: copy a live project block in `<dayz-mcp>\tools\build_native_launcher.py` (in `_build_request_policy()` and `_build_worker_runtime()`, same order), rebuild the PE with `build_native_launcher.py --offline --verify-reproducible`, update the PE SHA-256 that `tests\test_secure_launcher.py` hardcodes (every rebuild changes it), and replace the registry entry. `launcher_registry_update install-dayz-test-v1 --expected-sha256 <X>` compares and swaps the bytes of `approved-launchers.json`, not the PE, and refuses while a `dayz-test-v1` entry exists; renew with `replace-dayz-test-v1 --expected-sha256 <SHA-256 of the current approved-launchers.json>` in one write. Never run `rollback-last` and then install: after an earlier replace the rollback restores an older entry and install refuses it with `launcher_registry_version_already_installed`.

## Errors that hide their cause

- **`daemon_identity_unverified`.** `host_config.resolve_daemon_provenance()` reads both `~/.claude.json` (`mcpServers.dayz-mcp`) and `~/.codex/config.toml` (`[mcp_servers.dayz-mcp]`), requires them to agree and builds one daemon command line; a daemon started by hand with anything else is refused, so nothing can take the port and pose as the daemon. A hand typed `--idle-timeout 1800.0` against registrations that said `600` failed every retry. Ask the system instead: `<dayz-mcp>\tools\.venv-mcp\Scripts\python.exe -c "import sys; sys.path.insert(0,r'<tools>'); from dayz_mcp import host_config; print(host_config.resolve_daemon_provenance().argv)"`. Run it with that interpreter: with the system Python it raises `daemon_provenance_conflict`, a false alarm from the caller, not a disagreement between registrations.
- **`secure launcher failed: ControlClientError`.** The CLI swallows the code; catch the exception in a small wrapper and read `.code` before retrying.
- **`staging dir missing`.** A build script that fills a staging folder under `%LOCALAPPDATA%\Temp` but never creates it dies when Windows cleans `%TEMP%`. Have it create the folder, or rebuild it from the pack source (models, proxies, `$PBOPREFIX$`, `config.cpp`).
- **The daemon stopped on its idle timeout** (600 seconds in the registrations), so a launch that worked hours earlier fails with no change to the mod. Check port 8765 before blaming the build.
- **`run_not_adoptable`.** The kill path tries adopt, then stop; when both fail the lifecycle has lost the run while a DayZ process may still hold port 2302, so every new run fails with `worker_failed` and the audit log shows `session_rejected reason=process_identity_mismatch`. Read the end of `%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl`, which names the real reason. Close that one process after checking from its `CommandLine` that it is yours, retry the stop until it returns `run_not_active` (the next `dayz_test_run` answers `active_run_exists` until then), and start a fresh run. This is the one allowed exception to "never kill DayZ processes directly": only a process you launched, under a run the guard already disowned, that blocks the port. `lifecycle_cli.py` cannot run alone (it answers `missing_lifecycle_environment`); drive lifecycle operations through `secure_launcher.run_secure_launcher` with a request on stdin.
- **`launcher_root_identity_drift`.** The sealed registry pins the NTFS identity of the folder holding the launcher (`launcher_registry.py`, `_open_validated_entry`, which compares `root_file_id`, the `file_id` plus `volume_serial_number`, against `os.stat(root)`). A folder that is recreated, as a OneDrive synced folder can be, gets a new `file_id` and the whole managed path dies, preflight included, with a byte identical binary. Compare the two fields and the PE's SHA-256 before touching the seal: same volume, a new `file_id` and the pinned PE hash means the folder was recreated, not tampered with. The fix is for the machine's owner to approve: `.venv-mcp\Scripts\python.exe -m dayz_mcp.launcher_registry_update replace-dayz-test-v1 --expected-sha256 <REGISTRY SHA-256 IN UPPERCASE>` from `<dayz-mcp>\tools`. It must be `replace`, the token is the SHA-256 of `approved-launchers.json`, and it must be uppercase (`_HEX = frozenset("0123456789ABCDEF")`; the lowercase hash `sha256sum` prints fails with `invalid_launcher_registry_update`). It returns the new registry's hash, the token for the next operation.
- **`dayz_test_failed` from `build:true`.** It is the catch-all `except Exception` in `server.py`, not a tool error code, and the audit log shows only a clean lease. On Windows `build:true` failed this way at about 16 seconds without writing the PBO (hash and modified time unchanged). Three calls isolate it: `preflight: true` succeeds (launcher, PE, bundle, request and lifecycle are healthy), `mode: server` without `build` succeeds (launching works), and AddonBuilder by hand prints `Build Successful` (the builder is fine), which leaves the lifecycle's build path. On Linux `build=true` does build (`linux.md`). The working route: build to a staging folder (`AddonBuilder.exe P:\<Mod> <staging> -prefix=<Mod> -temp=P:\temp\<Mod> -clear -packonly`), check it by content (count anchors; `build-and-storage-traps.md`, "Backups packed into the PBO"), copy it to `P:\Mods\@<Mod>\Addons\<Mod>.pbo` and check its SHA-256, then start `dayz_test_run` without `build`. Stop the run before publishing, since the deployed PBO stays locked, and since scripts did not reload from source on the measured install, each Enforce Script change needs this whole cycle. Bisect an opaque error by capability (preflight, the call without the feature, the tool by hand) rather than by reading the code that threw it.
- **`unapproved_debug_image`.** See `mcp/bridge-setup.md`.

## Codex and `-ExecutionPolicy Bypass`

The Codex CLI sometimes applies its own policy to a command containing `-ExecutionPolicy Bypass` and refuses it. That is the agent refusing, not the host: the PowerShell policy is not `Restricted` because of it, Microsoft Defender does not stop the launch, and the `.ps1` and `.bat` launchers here are not blocked for Claude or the user. When you hand a launch to Codex, leave the flag out or let Claude or the user launch. Never disable Defender or add exclusions for it; Defender is not the cause.

## The machine, not the lease

- `session_status` can show `owner: null`, an empty queue and `claimable: true` while a server and client started by another session hold port 2302. The lease describes the lease, not the machine. Read the live command lines first; they tell whose run it is and whether it loads your mod:

  ```powershell
  Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" | Select-Object ProcessId, CommandLine
  ```

- For a build, the "no DayZ process" guard narrows to what it stands for: no running process loads your mod, and the target PBO opens exclusively (`build-and-storage-traps.md`, "Before you spend a boot").

### The machine is busy, not the port

With another session's DayZ running, `dayz_test_run` returns `active_run_exists` or `port_in_use_foreign` even with another `port=`, and keeps naming 2302. Its first hint says to pass another `port=`; the second, once the machine reads as occupied, says to retry with `wait_for_box_s`, which is the one that works: it puts the request in the queue. `port=` only helps two runs share a machine that is already yours. Before waiting, check that the occupant is alive (`Get-Process` on `DayZ*`, CPU and start time): growing CPU is another session's real run and is respected.

### A frozen RPT

Diag writes the RPT through a buffer of about 52 KB (five boots stopped at about 464 lines and 52 KB with different content). A frozen RPT does not tell a dead process from an unflushed buffer: compare the process CPU over 30 seconds with `Get-Process` twice, flat means stopped and growing means alive. On a work drive inside a OneDrive folder `Get-Item` can also report the wrong size (927 bytes against 52 KB real); read with `Get-Content` and count.

## `condition_failed` against `action_not_found`

`action_use` returns `action_not_found` when the action class is not in the player's list, and `condition_failed` when it is there, resolved against the target, and refused by its `ActionCondition`. That shows an action reaches an entity type without building the fixture that satisfies its guard. Run the negative control too: an invented action name on the same object must return `action_not_found`, or you do not know the two codes are really told apart.
