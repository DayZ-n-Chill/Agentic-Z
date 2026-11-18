# Managed runs: the dayz-mcp launcher, leases and its traps

How a test run is started, owned and stopped through the third-party dayz-mcp server (`dayz_test_run`, `dayz_test_stop`, the sealed native launcher and its allow-list), the unmanaged fallback, and every trap measured on that route. Read it only when the machine uses dayz-mcp; a plain `/dayz-launch-test` session needs none of it, and the cautions about an "unmanaged" launch describe a machine where dayz-mcp's sealed launcher is installed. The bridge side of the same tool is in `skills/dayz-launch-test/references/mcp/`.

Terms used below: dated findings were measured on one Windows test machine, and "this install" means that machine, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it.

Everything here is behaviour of dayz-mcp, its launcher and its `@DayZ_MCP` mod, measured in game sessions with that tool. It is not yet checked on `P:\` and cannot be, because none of it is vanilla. File and line numbers such as `dayz_test_request.py:336-344` are lines of dayz-mcp's own source at the time of the measurement; `<dayz-mcp>` is the folder of your dayz-mcp checkout.

## Shared session protocol

Read dayz-mcp's agent session protocol (the runbook that ships with the tool) before launching. The official launcher is Diag-only and enforces this matrix:

| Route | Executable / role | Contract |
|---|---|---|
| Managed diag | `DayZDiag_x64.exe`, including the `-server` role | `managed_lifecycle=true`; `dayz_test_run` owns lease, heartbeat and release and returns a `run_id`. |
| Dedicated server | `DayZServer_x64.exe` | `managed_lifecycle=false`; probe-gated and not started by the official launcher. |
| External manual retail | A session the user opened outside the launcher | No agent lifecycle; triggers quarantine. |

1. Run `bridge_status`. Under retail quarantine only reads are allowed.
2. [EXACT] Use `dayz_test_run` for a managed server or client and `dayz_test_stop` for the exact `run_id`. Those tools own the FIFO queue, the lease, the heartbeat and the release; do not acquire another lease around them.
3. `session_acquire`, `session_wait`, `session_heartbeat` and `session_release` remain for low-level mutations the public tools do not cover, and for adopting the run: when it completes, `dayz_test_run` releases its lease and the run stays `RUNNING_IDLE` without an owner. Any bridge verb on it, reads included, is rejected with `run_not_owned` until `session_acquire_wait` adopts it (check `adopted_run`). Sequence: `skills/dayz-launch-test/references/mcp/run-lifecycle.md`, "Bridge startup sequence".
4. [EXACT] The approved launcher receives `DAYZ_MCP_CLIENT_ID_JSON` and `DAYZ_MCP_LEASE_TOKEN` only in the process environment. `scripts/dayz-test.ps1` captures them, removes them from the parent environment and restores them only around the child process. Never copy their values to a shell, argv, a log or a handoff, and never invoke the approved launcher directly.
5. Keep the returned `run_id`. Loading the same mod does not grant ownership: stop and adopt require the exact run. `-Kill` without `-RunId` fails closed.
6. Verify the terminal state after a stop. NEVER replace the lifecycle guard with a kill, or with attribution based on a process name, mod, command line or profile.
7. [EXACT] After adopting, keep the run owned yourself: the lease lasts 120 s and is not renewed internally, so send `session_heartbeat` at least every 90 s or so during the whole run, including while a human plays. Without heartbeats the run goes ownerless and the daemon stops it after the grace period (measured 2026-09-27, three runs; detail in `skills/dayz-launch-test/references/mcp/run-lifecycle.md`, "Leases expire on their own").

A retail session opened by hand triggers retail quarantine: the user who opened it closes it through its UI and then runs doctor/rescan. Without access to that UI, declare `manual_cleanup_required`; another agent neither kills nor adopts the process.

### Unmanaged fallback when the managed route is blocked

`dayz-test.ps1` and `dayz_test_run` are the managed path. If the `approved-launchers.json` registry does not let the project pass, or the MCP daemon on its documented port is down (`session_status` = `daemon_unavailable`), that path does not launch.

With no DayZ process running on the machine and explicit user authorization, the fallback is an unmanaged launch. It is not the default.

- Do not launch the exe from the agent's shell. [EXACT] On a machine with the registered launcher, a DayZDiag started outside it stays alive with 0 CPU and writes no RPT. Alive, 0 CPU and no RPT means the launch came from the agent; it is not the arguments or the mod.
- Do not use `Start-Process -ArgumentList` for DayZDiag. [EXACT] In Windows PowerShell 5.1 an array does not guarantee quoting of each element. [EXACT] In six A/B attempts on 2026-08-12, `cmd /c start` with literal quotes around each value that contains spaces started the game; `Start-Process -ArgumentList` started it and it hung at about 0.06 s of CPU without writing even the RPT header.
- [EXACT] When the command that `cmd /c start` launches is a `.bat`, the new window runs `cmd /K`: an `exit /b` at the end of the bat exits the script, not the interpreter, and the window stays at an idle prompt after the server closes, one leftover console window per launch (measured 2026-09-25 on Windows 11 23H2: 9 idle `cmd.exe /K` wrappers after two days of server starts, 0 after the change). Wrap the bat in a second `cmd /c`: `cmd /c start "<title>" cmd /c "<abs bat>"`. A preflight failure with `pause` inside the bat is still visible.
- Recipe: the agent writes a `.bat` for the server and one for the client (literal quotes around each value with spaces) and the user double-clicks them in the interactive session. [EXACT] Read `script.log` and the RPT with `FileShare.ReadWrite`. Close through the UI, not by PID, unless the process is the agent's own zombie (then `Stop-Process -Id` with the exact id).
- [DESIGN] Server argv: `-server "-config=<serverDZ.cfg>" "-profiles=<server-profiles>" "-mission=<mission-abs>" "-mod=<mod-abs-semicolon-list>" -filePatching -port=2302`
- [DESIGN] Client argv: `"-mod=<mod-abs-semicolon-list>" -connect=127.0.0.1 -port=2302 "-profiles=<client-profiles>" -name=Dev -window -filePatching`

Since 1.30, optional on both: `-cacheP3D=1` (cache next to unbinarized `.p3d` files) and `-resolveFilePatchingUsingEnfusion=1` (requires `-filePatching`; always on in Workbench). `-mod=` may name an unpacked source folder, not only a packed `@Mod`. See `dayz-1-30.md`.

Three traps on this same path that do not come from argv (measured):

- **Stuck Workshop.** A `workshop_log.txt` with "No workshop depot defined, skipping non-legacy item" on each item (`NeedsDownload=1`) is unblocked with `steam://validate/221100`, which refreshes the appinfo. Neither the launcher nor the download page unblocks it.
- **Default RPT.** If `-profiles` does not reach the exe, DayZDiag writes the RPT and the script log to `%LOCALAPPDATA%\DayZ`. Look there before declaring that nothing was written.
- **VPPAdminTools superadmin.** Current versions read `<profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` (IDs only, one per line); `SuperAdmins.json` is the old format and is ignored. With `vppDisablePassword=1` and the ID in the `.txt`, the menu opens directly.

## Secure-launcher allow-list: junctions decide the `base_mods` format

On a machine where DayZDiag only launches through the registered native launcher, a mod that is not in the sealed allow-list of `dayz-test-v1` cannot be launched under a project entry of its own. It can still be tested without touching the launcher, by riding an approved project: see "Testing a mod that is not in the allow-list" below, and rebuild only when the mod needs its own sealed entry. Adding another mod is mechanical: copy a live project block in `<dayz-mcp>\tools\build_native_launcher.py` (in `_build_request_policy()` and in `_build_worker_runtime()`, same order). The format of `default_base_mods` is a correctness trap, not a style choice.

`request_path_authority._open_descendant` rejects any path component that is a reparse point (`item.reparse_tag != 0 -> _invalid()`). Therefore:

- A dependency whose folder under `P:\Mods` is a junction (`@CF`, `@Dabs Framework`, `@VPPAdminTools`, all pointing into the Steam workshop) must be listed by its absolute workshop path, and that path must also be sealed in `mod_roots`.
- A dependency that is a real directory under `P:\Mods` (a locally built mod) can be a bare relative name: `dayz_test_worker._mod_path` joins it to `mods_root` and it is accepted under the sealed `P:\Mods` root (exactly one match required).

The wrong format passes every unit test (they only pin strings) and fails at accreditation time, when the server is launched. Check `Get-Item <path> | Select-Object LinkType` for each dependency before choosing the format.

Two more gates in the same flow:

- `tests\test_secure_launcher.py` hardcodes the launcher PE sha256. Every rebuild changes it (adding a mod changes the PE), so update it after `build_native_launcher.py --offline --verify-reproducible` or the suite stays red for a reason unrelated to the change.
- `launcher_registry_update install-dayz-test-v1 --expected-sha256 <X>` is a compare-and-swap on the bytes of `approved-launchers.json` (not the PE hash), and it refuses to install while a `dayz-test-v1` entry exists. Renew an installed entry with `replace-dayz-test-v1 --expected-sha256 <sha256 of the current approved-launchers.json>`, which swaps it in one write. Do not run `rollback-last` and then install: after an earlier replace, the rollback restores an older `dayz-test-v1` entry and install refuses it with `launcher_registry_version_already_installed` (dayz-mcp `tools/dayz_mcp/launcher_registry_update.py:229` and `:329` at commit 90da56e).

### Testing a mod that is not in the allow-list, without rebuilding the launcher

Authorizing a project is the expensive path: edit `build_native_launcher.py`, rebuild the PE, update the hardcoded sha256 in the test and replace the registry entry. It is only needed when the mod must have its own sealed project entry.

To just run the mod in game, mount it as an `extra_mods` entry on a project that is already approved. `_mods` appends every `extra_mods` value to the launch list (`dayz_test_worker.py:204-210`), and `_mod_path` joins a non-absolute value to the sealed `mods_root` (`:199-201`), so a bare `@Name` is accepted under `P:\Mods`.

The name must be a plain relative one. `_valid_mod_entry` (`dayz_test_request.py:137-148`) rejects anything containing `:`, `\` or `/`, rejects `.` and `..`, and requires `ntpath.normpath(value) == value`. An absolute path is accepted instead, but then it must fall inside a sealed root.

Two constraints decide whether the run works:

- **The deployed directory must be real, not a reparse point.** Same rule as the `default_base_mods` format above: `_open_descendant` rejects any component whose `reparse_tag != 0`. A junction has to be listed by its absolute workshop path and sealed in `mod_roots`.
- **Pick a carrier project that compiles, and check it on the day.** Script compilation aborts on the first mod that fails, so a broken carrier's error only surfaces once yours already compiles, which reads as "my mod broke it". Whether a carrier compiles depends on its source that day, not on the project. [EXACT] On 2026-10-02 (DayZDiag 1.29.163709) the project `DayZ_MCP` carried extra mods in two runs, two in the first and four in the second. In both, the server and client script logs read `Module: Mission; loaded 217x files; 540x classes` with no `CParser` line, and in the second the probe's `4_World` print ran on both peers. Ten minutes before the first, another project used as carrier for `@DayZ_MCP` and the same two mods stopped at `Can't compile "Mission" script module!` on an error in its own `5_Mission`; two months earlier the same project had compiled as a carrier. Before reading your mod's errors, find the carrier's `Module: Mission; loaded ...` line in the server script log; when it is missing, `Can't compile "Mission" script module!` and the `crash_*.log` name the failing file.

## `-ExecutionPolicy Bypass`: an intermittent Codex rejection, not a host block

The Codex CLI sometimes applies its own security policy to a command that contains `-ExecutionPolicy Bypass` and rejects it. That is the agent refusing, not the host:

- The host PowerShell policy is not `Restricted` because of it, and Microsoft Defender does not interrupt the launch.
- The `.ps1` and `.bat` launchers of this skill are not host-blocked. Claude and the user run them normally, and nothing here requires a "managed Python lifecycle" in order to launch.
- When you delegate a launch to Codex, leave that flag out of the command you pass, or let Claude or the user do the launch.
- The shared session protocol above (FIFO lease and `run_id`) still coordinates launch and stop; it is unrelated to this.

Do not disable Defender or add exclusions as a workaround: Defender is not the cause.

## Secure-launcher runtime traps: daemon argv, staging dir, opaque errors

Three cheap preflights.

**1. The daemon argv is derived from the client registrations.** `host_config.resolve_daemon_provenance()` reads both `~/.claude.json` (`mcpServers.dayz-mcp`) and `~/.codex/config.toml` (`[mcp_servers.dayz-mcp]`), requires them to agree, and builds one canonical daemon argv. Hand-starting the daemon with anything else is rejected with `daemon_identity_unverified`, by design, so that nothing can take the port and impersonate the daemon. In the measured case a hand-typed `--idle-timeout 1800.0` against registrations that said `600` made every retry fail. Never guess the argv; ask the system:
`python -c "import sys; sys.path.insert(0,r'<tools>'); from dayz_mcp import host_config; print(host_config.resolve_daemon_provenance().argv)"`

**2. The CLI hides its own error code.** `secure_launcher` prints only `secure launcher failed: ControlClientError` and swallows the code. Getting `daemon_identity_unverified` took a wrapper script that caught the exception and read `.code`. If a launch fails, capture the code first; do not retry blind.

**3. A build script that fills its staging dir but never creates it.** A staging folder under `%LOCALAPPDATA%\Temp` that holds `$PBOPREFIX$` disappears when Windows cleans `%TEMP%`, and the build then dies with `staging dir missing`. Have the script create the folder, or rebuild it by copying the pack source (models, proxies, `$PBOPREFIX$`, `config.cpp`) into it.

Also: the daemon stops itself on its idle timeout (600 s in the measured registrations), so a launch flow that worked hours earlier fails later with no change to the mod. Check port 8765 before blaming the build.

## Secure-launcher request grammar, the Steam prerequisite, and orphaned runs

**1. The client needs Steam running. The server does not.** A client launched with Steam down exits immediately, writes a 793-byte RPT with only the header and an `ErrorMessage_*.mdmp` next to it, and logs nothing useful. The real message is only inside the minidump: extract strings and look for `Unable to locate a running instance of Steam`. There is no Windows "Application Error" event because the engine handles it itself. Check `Get-Process steam` before launching a client, and start it with `steam.exe -silent` if it is missing, from a shell outside any sandboxed (MSIX) app, never from a shell inside the Claude or Codex app (point 1-ter).

**1-bis. If that message appears while Steam is running, run the discriminator.** Measured 2026-09-08: the client died on 5 consecutive launches with exactly the string above, plus `[API loaded no]` in the same dump, while `Get-Process steam` returned a live process, `HKCU\Software\Valve\Steam\ActiveProcess` held a non-zero `ActiveUser` whose `pid` matched it, and `steam.exe`, `DayZDiag_x64` and the daemon all ran as the same unelevated user. Restarting Steam (`steam.exe -shutdown`, then relaunch) changed nothing, twice.

The asymmetry is the clue: the server lives and the client dies. Only the client needs the Steam API, so launch the dead half yourself, from your own user shell, with the same command line (take it from the RPT header or the dump):

- **The hand-launched client dies too**: the host or Steam really is broken, and that fix belongs to the user.
- **The hand-launched client lives**: the daemon's spawn context breaks it, not the host. No amount of restarting Steam will change that.

On that date it lived: it booted, connected and reached the in-game HUD. `capture_screenshot` works on it, because capture is host-side and not a bridge verb.

A client you launched yourself is foreign to the run record, so the instance fence rejects its polls (`unaccredited_polls_by_class.instance_unknown` climbs) and no client verb reaches it. Without `camera_set` there is no framing. It is good for putting a human in front of the screen, not for automating a reading.

The general rule: when one half of a client/server pair dies and the other lives, their differing requirements already shortlist the cause. Run the by-hand launch of the dead half before believing whatever subsystem the error message names.

When it is the daemon, re-measure before treating the wall as permanent. On 2026-09-10 the same launch succeeded on the first try (`client_alive=true` at 17 s, player in game at 51 s, no Steam intervention, `auto_remediate_steam` not requested). The only thing that had changed was `session_status.daemon_generation`: the wall was daemon state, and a daemon restart cleared it. Record `daemon_generation` when you note the failure, compare it when you retry, and give a freshly restarted daemon one clean launch before spending a session on the workaround.

**1-ter. A client you start from a shell inside the Claude or Codex app can read a Steam that is gone.** Those apps keep a private copy of `HKCU` for every process they start (MSIX registry virtualization), and once anything inside the app has written Steam's keys the copy stays on that Steam's pid after it exits. [EXACT] Measured 2026-10-16: an agent's `Start-Process` of the retail client from a Claude app shell read `pid = 67468`, a Steam gone since 2026-10-06, and died with point 1's message while `steam.exe` ran; the 11 `dayz_test_run` launches of that day passed Steam, because the daemon runs outside the app and reads the real key. It also fools point 1-bis: a by-hand launch from such a shell dies for this reason, not because the host is broken.

- Before a by-hand launch from an app shell, compare `(Get-ItemProperty HKCU:\Software\Valve\Steam\ActiveProcess).pid` read there with `(Get-Process steam).Id`. dayz-mcp's `session_status` names a mismatch as the warning `steam_app_view_stale`.
- Launch from outside the app instead: from Steam, from Explorer, or through WMI (`Win32_Process.Create`, as the daemon does).
- Never start Steam, or write or delete its registry keys, from the app's shells: that is what creates or freezes the copy, and only an offline edit of the app's hive with the app closed removes it (dayz-mcp's `tools/clear-app-steam-shadow.ps1`). Background in `dayz-1-30.md`, "Launching the 1.30 DayZDiag directly", point 2.

**2. The request JSON must not carry a UTF-8 BOM.** `Out-File -Encoding utf8` in Windows PowerShell 5.1 writes a BOM and the parser rejects the whole request with `invalid_dayz_test_request`. Write it with `[IO.File]::WriteAllText($path, $json, (New-Object Text.UTF8Encoding($false)))`, or copy a known-good request file and replace the fields.

**3. The request grammar has two coupled rules** (`dayz_test_request.py:336-344`), and violating either returns the same opaque `invalid_dayz_test_request`:

- `kill: true` requires a `run_id`.
- With a `run_id`, `mode` may not be `server` or `all`; and `mode: "client"` requires a `run_id`.

So the valid shapes are: `server` or `all` without a run_id (starts a run), `client` with a run_id (joins one), and kill as `mode: "client"` + `kill: true` + run_id (stops the run, not just the client). `mode: "all"` launches server and client in one request and needs no run_id; the section on `extra_mods` below records that `server`, wait, then `client` was the more reliable sequence.

**4. `run_not_adoptable` means the run is gone but its processes may not be.** The kill path tries `adopt` then `stop` (`dayz_test_worker.py:496-507`); when both fail the lifecycle has lost the run while a DayZ process may still hold port 2302, so every new run fails with `worker_failed` and the audit trail shows `session_rejected reason=process_identity_mismatch`. Read the tail of `%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl`: it names the real reason, which the CLI hides. Recovery is a documented degraded closure: close that specific process after verifying by its `CommandLine` that it is yours, then start a fresh run. This is the one sanctioned exception to "never kill DayZ processes directly": it applies only to a process you launched, under a run the guard has already disowned, that is blocking the port.

`lifecycle_cli.py` cannot be invoked standalone: it answers `missing_lifecycle_environment` because the launcher chain sets its environment. Drive lifecycle operations through `secure_launcher.run_secure_launcher` with a request on stdin.

`host_config.resolve_daemon_provenance()` raises `daemon_provenance_conflict` if you call it with the system Python and not the `.venv-mcp` interpreter that both registrations declare: it compares `command` against the local launch executable (`host_config.py:218-222`). That is a false alarm produced by the caller, not a divergence between the Claude and Codex registrations. Always invoke it with `<dayz-mcp>\tools\.venv-mcp\Scripts\python.exe`.

## `dayz_test_run` with `build:true` did not build, and its error does not say so

Measured on Windows on 2026-07-29. On Linux `build=true` goes through dayzmake (then still named armake2) and did build on 2026-11-06; see `linux.md`.

On a machine where DayZDiag only starts through the registered native launcher, `dayz_test_run` is the only way to launch. Its `build:true` returned the generic `dayz_test_failed` and did not write the PBO (hash and mtime of the deployed file unchanged). Reproduced twice, always at about 16 s.

`dayz_test_failed` is the `except Exception` of `server.py:1101`, which swallows the real cause: it is not a tool error code. Reading the audit trail (`%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl`) does not help here either: the lease is granted and released cleanly, with `runs_released: []` and no run event.

A bisection in three calls isolates it; run it before touching anything:

| Call | Measured result | What it rules out |
|---|---|---|
| `preflight: true` | `succeeded` in 1.5 s | launcher, PE, bundle, request and lifecycle are healthy |
| `mode: server` without `build` | `succeeded` in 5.1 s | launching works |
| AddonBuilder by hand | `Build Successful`, exit 0, about 3.4 s | AddonBuilder is not the cause either |

With those three, the failure is isolated to the build path of the lifecycle, which belongs to dayz-mcp.

Workaround, verified and repeatable (build outside the published path, which "RELEASE-GRADE BUILD BOUNDARY" in `windows-launch-cycle.md` also requires):

```powershell
# 1. build to staging, never directly to the published path
AddonBuilder.exe P:\<Mod> <staging> -prefix=<Mod> -temp=P:\temp\<Mod> -clear -packonly
# 2. validate by content before publishing (count anchors, do not use Contains:
#    build-and-storage-traps.md, "Backups (.bak_*) in scripts/ inflate the PBO")
# 3. publish and verify by SHA-256, not by mtime
Copy-Item <staging>\<Mod>.pbo P:\Mods\@<Mod>\Addons\<Mod>.pbo -Force
(Get-FileHash 'P:\Mods\@<Mod>\Addons\<Mod>.pbo' -Algorithm SHA256).Hash
# 4. start with dayz_test_run without build
```

Two preconditions matter here: the deployed PBO stays locked while the run is executing (stop the run before publishing), and scripts did not hot-load on the measured install (`windows-launch-cycle.md`, "Script changes did not hot-load"), so each Enforce Script iteration needs this whole cycle.

The method is reusable: an opaque wrapper error is narrowed down by bisecting capabilities (preflight, the call without the feature, the tool by hand), not by reading the code that threw it.

## `dayz_test_run` `extra_mods` replaces the extras list, it does not extend it

Passing `extra_mods=["@MyMod"]` to `dayz_test_run` replaces the project's extra mods with that list. If the `@DayZ_MCP` bridge was among them, it drops out and all MCP verbs stop working although the pair boots: both processes alive and responding, mission loaded, and `bridge_status.ready.reason = server_poll_stale` with `last_poll_age_s` frozen at the value from the previous run.

A five-second check: search the server script log for `DayZ_MCP` in the `defines:` list of any module, or for the line `[DayZ-MCP] config loaded ... poll_hz=`. If neither is there, the mod was not loaded. Always name `@DayZ_MCP` explicitly in `extra_mods`.

From the same launch: `mode="pair"` does not exist and returns `bad_dayz_test_request` without saying which modes are valid. They are `server`, `client` and `all`. The reliable path was `server`, wait, then `client` with the same `run_id`, not `all`.

## The diag RPT is buffered in about 52 KB, and the lifecycle needs its window after `run_not_adoptable`

Two facts from a six-boot run, each reproduced several times:

1. **A frozen RPT does not tell a dead process from an unflushed buffer.** Diag writes the RPT through a buffer of about 52 KB (five boots, always about 464 lines / 52 KB at the moment of failure, with different contents). The discriminant is the CPU delta of the process over 30 s (`Get-Process` twice): flat means stopped, growing means alive with the log buffered. `Get-Item` on a work drive that sits in a OneDrive folder can also report the wrong size (927 bytes reported, 52 KB real): read with `Get-Content` (share-read) and count.
2. **After a `run_not_adoptable` from `dayz_test_stop`, the lifecycle has a reconciliation window**: the next `dayz_test_run` returns `active_run_exists` even if the processes are dead. The pattern that worked three times: close the orphan DayZDiag by process, retry the stop until it returns `run_not_active`, and only then launch the new run.

## A free lease does not mean a free machine

`session_status` can return `owner: null`, an empty queue and `claimable: true` while a DayZ server and client are alive, launched outside the managed lifecycle by another session and holding port 2302. The lease describes the lease, not the machine.

Before treating the machine as free, read `-mod=` of the live processes:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" |
  Select-Object ProcessId, CommandLine
```

The command line tells whose run it is and whether it loads your mod.

For a build, the "no DayZ process" guard can be narrowed to the two conditions it stands for: no running process loads your mod, and the target PBO opens exclusively. That is better than skipping the guard or waiting for the other session to finish.

The same rule from the bridge side is in the MCP verification references (`references/mcp/README.md`).

## Three walls of managed startup that do not name their cause

Each returns a code that does not describe what happens, and each is resolved in a minute once you know which it is.

### 1. `launcher_root_identity_drift`: the seal pins the directory, not just the binary

The sealed registry pins the NTFS identity of the directory that contains the launcher (`launcher_registry.py`, `_open_validated_entry`: it compares `root_file_id`, which is `file_id` plus `volume_serial_number`, against `os.stat(root)`). If that directory is recreated, which a OneDrive-synced folder does, `file_id` changes and the whole managed path dies, `preflight` included. A byte-identical binary makes no difference.

Diagnose before touching a security seal, because the diagnosis tells benign drift from tampering: compare the two fields of `root_file_id` separately, and the sha256 of the PE. Same volume, different `file_id` and a PE with the pinned hash means the directory was recreated and the binary did not change.

The remedy is for the machine's owner to authorize, not for you to decide:

    cd <dayz-mcp>\tools
    .venv-mcp\Scripts\python.exe -m dayz_mcp.launcher_registry_update replace-dayz-test-v1 --expected-sha256 <REGISTRY SHA256, IN UPPERCASE>

- It is `replace-*`, not `install-*`: `install` refuses while an entry exists.
- The compare-and-swap token is the sha256 of the bytes of `approved-launchers.json`, not of the PE.
- The hash must be in uppercase. `_HEX = frozenset("0123456789ABCDEF")`, so a lowercase sha, which is what `sha256sum` prints, fails with `invalid_launcher_registry_update`, a code that says nothing about the format.
- It returns the sha of the new registry, which is the token for the next operation.

### 2. The machine is occupied, not the port: `port=` does not get around a foreign process

With a foreign DayZ running, `dayz_test_run` returns `active_run_exists` / `port_in_use_foreign` even if you pass another `port=`, and keeps naming 2302 in the error. Its first hint says to pass another `port=`; the second, once the machine has been read as occupied, says to retry with `wait_for_box_s`. The second is the one that works: `wait_for_box_s` puts the request into the FIFO queue. `port=` only helps two runs coexist when the machine is already yours.

Before waiting, check that the occupant is alive and not a zombie: `Get-Process` on `DayZ*`, CPU and start time. Growing CPU is another session's real run and is respected. Its `-mod=` tells you whose it is.

### 3. `mode=client` requires `extra_mods` again, or it rejects the reattach

On a client reattach, omitting `extra_mods` does not inherit the list from the server start; it fails with `bridge_mod_missing: add extra_mods=['@DayZ_MCP']`. Pass the same list as in `mode=server`: a different list also changes the mod set's seal, on top of losing the bridge.

### `condition_failed` and `action_not_found` tell two things apart, given a control

`action_use` returns `action_not_found` when the action class is not in the player's array, and `condition_failed` when it is present, resolved against the target, and rejected by its `ActionCondition`. That shows an action reaches an entity type without setting up the fixture that satisfies its guard. Run the negative control too: send an invented action name on the same object and check that it returns `action_not_found`; without it you do not know that the two codes are really distinguished.

## A disposable probe does not need to register as an MCP project

`P:\Mods` is the `mod_root` of the approved projects in `request-policy.json`, and `dayz_test_tool._valid_public_mod` accepts any relative folder inside those roots. So:

```
dayz_test_run(project="DayZ_MCP", mode="all", extra_mods=["@MyProbe"])
```

starts with the full bridge (`capture_screenshot`, `camera_set`, `query_player_state`, `wait_for` on `log_matches`) plus your probe, without touching the sealed policy or rebuilding it with `build_native_launcher.py`.
