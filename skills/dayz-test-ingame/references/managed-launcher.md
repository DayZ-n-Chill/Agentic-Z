# Managed runs: the dayz-mcp launcher, leases and its traps

How a test run is started, owned and stopped through the third-party dayz-mcp server (`dayz_test_run`, `dayz_test_stop`, the sealed native launcher and its allow-list), the unmanaged fallback, and every trap measured on that route. Read it only when the machine uses dayz-mcp; a plain `/dayz-launch-test` session needs none of it, and the cautions about an "unmanaged" launch describe a machine where dayz-mcp's sealed launcher is installed. The bridge side of the same tool is in `skills/dayz-mcp-verify/`.

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it. Tags such as `SP-078`, `LL-196` and `CLAIM-...` are the finding numbers of the knowledge pack this material came from; they are kept so that cross-references between files stay searchable. `DAYZ_INFRA.md` is that pack's infrastructure note (in this repo `skills/_shared/knowledge/environment-and-infra.md`); a tag like `[EXACT - DAYZ_INFRA.md §Section]` names the section of it that records the fact.

Everything here is behaviour of dayz-mcp, its launcher and its `@DayZ_MCP` mod, measured in game sessions with that tool. It is not yet checked on `P:\` and cannot be, because none of it is vanilla. File and line numbers such as `dayz_test_request.py:336-344` are lines of dayz-mcp's own source at the time of the measurement; `<dayz-mcp>` is the folder of your dayz-mcp checkout.

## SHARED SESSION PROTOCOL

Read before launching:
dayz-mcp's agent session protocol (the runbook that ships with the tool).
Official launcher is Diag-only and enforces this matrix:

| Route | Executable / role | Contract |
|---|---|---|
| Managed diag | `DayZDiag_x64.exe`, including `-server` role | `managed_lifecycle=true`; `dayz_test_run` possesses lease/heartbeat/release and returns `run_id`. |
| Dedicated server | `DayZServer_x64.exe` | `managed_lifecycle=false`; probe-gated and not started by official launcher. |
| External manual retail | Session opened by user outside launcher | No agent lifecycle; triggers quarantine. |

1. Run `bridge_status`; under retail quarantine only reads are allowed.
2. [EXACT][CLAIM-R21-TEST-PUBLIC-LIFECYCLE] Use `dayz_test_run` for
   managed server/client and `dayz_test_stop` for exact `run_id`. Those
   tools possess FIFO queue, lease, heartbeat, and release; DO NOT
   pre-acquire another lease around them.
3. `session_acquire`/`session_wait`/`session_heartbeat`/`session_release` remain
   for low-level mutations not encapsulated by public
   tools. (rev. 2026-09-06) And to ADOPT the run: upon completion, `dayz_test_run`
   releases its lease and run remains `RUNNING_IDLE` without owner; any bridge verb
   on it, reads included, is rejected with `run_not_owned` until
   `session_acquire_wait` adopts it (check `adopted_run`). Sequence and citations:
   `skills/dayz-mcp-verify/references/run-lifecycle.md`, "Bridge startup sequence".
4. [EXACT][CLAIM-R21-TEST-CREDENTIAL-SCOPE] The approved launcher receives
   `DAYZ_MCP_CLIENT_ID_JSON` and `DAYZ_MCP_LEASE_TOKEN` only in the process
   environment. The template captures them, removes them from parent environment, and
   restores them solely around child process; never copy their values to
   shell, argv, logs, or handoff nor invoke approved launcher directly.
5. Retain returned `run_id`. Same mod does not grant ownership: stop/adopt
   require the exact run. `-Kill` without `-RunId` remains fail-closed.
6. Verify terminal state after stop. NEVER substitute lifecycle
   guard with a kill or with attribution based on name, mod, cmdline, or profile.
7. [EXACT] After adopting, keep the run owned yourself: the lease lasts 120 s and is not renewed internally, fresh client or not, so send `session_heartbeat` at least every ~90 s during the whole run, including while a human plays. Without heartbeats the run goes ownerless and the daemon stops it after the grace period (measured 2026-09-27, three runs; detail in `skills/dayz-mcp-verify/references/run-lifecycle.md`, "Leases expire on their own").

Manual-only retail triggers retail quarantine: user who opened it closes it via UI and
then runs doctor/rescan. Without access to that UI, declare `manual_cleanup_required`; another
agent neither kills nor adopts the process.

### Unmanaged fallback when managed is blocked (SP-084-unmanaged-fallback)

`dayz-test.ps1` and `dayz_test_run` are the managed path. If `approved-launchers.json` registry does not let the project pass and MCP daemon on documented port goes down (`session_status`=`daemon_unavailable`), that path does not launch.

With the box free of run DayZ processes and explicit user authorization, the path is UNMANAGED launch. It is not default.

- Do not launch exe from agent shell. [EXACT - this skill, cross-ref SP-085] DayZDiag launched outside registered launcher stays alive with 0 CPU and 0 RPT. Signature: alive + 0 CPU + 0 RPT => not args/mod, it is launch-from-agent.
- Do not use `Start-Process -ArgumentList` for DayZDiag. [EXACT - this skill, SP-167] In Windows PowerShell 5.1 array does not guarantee quoting of each element. [EXACT - SP-228, measured in LFPowerGrid P0.0, 6 A/B attempts 2026-08-12] `cmd /c start` with literal quotes on each value with spaces is the path that starts; `Start-Process -ArgumentList` starts and hangs at ~0.06 s CPU without writing EVEN the RPT header.
- [EXACT] When the command that `cmd /c start` launches is a `.bat`, the new window runs `cmd /K`: an `exit /b` at the end of the bat exits the script, not the interpreter, and the window stays at an idle prompt after the server closes - one leftover console window per launch (measured 2026-09-25, LFDucati T99, Windows 11 23H2: 9 idle `cmd.exe /K` wrappers after two days of server starts; 0 after the switch). Wrap the bat in a second `cmd /c`: `cmd /c start "<title>" cmd /c "<abs bat>"`. A preflight failure with `pause` inside the bat is still visible.
- Recipe: agent writes `.bat` (server/client argv, literal quotes on each value with spaces) and user double-clicks to execute them in interactive session. [EXACT - this skill, SP-077] Read script.log/RPT with `FileShare.ReadWrite`. UI closure, not by PID, except agent's own zombie (then exact `Stop-Process -Id`).
- [DESIGN] Server argv: `-server "-config=<serverDZ.cfg>" "-profiles=<server-profiles>" "-mission=<mission-abs>" "-mod=<mod-abs-semicolon-list>" -filePatching -port=2302`
- [DESIGN] Client argv: `"-mod=<mod-abs-semicolon-list>" -connect=127.0.0.1 -port=2302 "-profiles=<client-profiles>" -name=Dev -window -filePatching`
(since 1.30 [CHANGELOG]) Optional on both: `-cacheP3D=1` (unbinarized `.p3d` sibling cache) and `-resolveFilePatchingUsingEnfusion=1` (requires `-filePatching`; always on in Workbench). `-mod=` may name an unpacked source folder, not only a packed `@Mod`. See `dayz-1-30-test-ingame.md`.

Three gotchas that bite along this same path and are not from argv (SP-228, measured):

- **Stuck Workshop.** `workshop_log.txt` with "No workshop depot defined, skipping non-legacy
  item" on each item (`NeedsDownload=1`) is unblocked with `steam://validate/221100`, which refreshes
  appinfo. Neither launcher nor download page unblocks it.
- **Default RPT.** If `-profiles` does not reach exe, DayZDiag writes RPT and script log to
  `%LOCALAPPDATA%\DayZ`. Search there before declaring nothing was written.
- **VPP superadmin.** Current versions read
  `<profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` (IDs only, one per line);
  `SuperAdmins.json` is old format and ignored. With `vppDisablePassword=1` plus ID in `.txt`
  menu opens directly. Corrects hint that cited only the JSON.

## Secure-launcher allow-list: the base_mods format is decided by junctions, not style (SP-089, added 2026-07-25)

On this box DayZDiag only launches through the registered native launcher (SP-085), so a mod that is not in the sealed allow-list of `dayz-test-v1` cannot be launched under a project entry of its own. It can still be TESTED without touching the launcher, by riding an approved project - see "Testing a mod that is not in the allow-list" below; reach for the rebuild only when the mod needs its own sealed entry. Adding the Nth mod is mechanical - copy a live project block in `<dayz-mcp>\tools\build_native_launcher.py` (`_build_request_policy()` AND `_build_worker_runtime()`, same order) - but the `default_base_mods` FORMAT is a correctness trap, not a style choice.

`request_path_authority._open_descendant` rejects any path component that is a reparse point (`item.reparse_tag != 0 -> _invalid()`). Therefore:

- A dep whose folder under `P:\Mods` is a JUNCTION (`@CF`, `@Dabs Framework`, `@VPPAdminTools` -> Steam workshop) MUST be listed as its ABSOLUTE workshop path, and that path must also be sealed in `mod_roots`.
- A dep that is a REAL directory under `P:\Mods` (a locally built mod, e.g. `@LFHeliCore`) can be a bare relative name: `dayz_test_worker._mod_path` joins it to `mods_root` and it accredits under the sealed `P:\Mods` root (exactly 1 match required).

Why it costs a session: the wrong format passes EVERY unit test (they only pin strings) and fails at accreditation time, when the server is launched. Check `Get-Item <path> | Select-Object LinkType` for each dep BEFORE choosing the format.

Two more gates in the same flow, both of which have already burned a session:

- `tests\test_secure_launcher.py` HARDCODES the launcher PE sha256. Every rebuild changes it (adding a mod changes the PE), so update it after `build_native_launcher.py --offline --verify-reproducible` or the suite stays red for a reason unrelated to the change.
- `launcher_registry_update install-dayz-test-v1 --expected-sha256 <X>` is a compare-and-swap on the BYTES of `approved-launchers.json` (NOT the PE hash), and it REFUSES to install while a `dayz-test-v1` entry exists. Renew an installed entry with `replace-dayz-test-v1 --expected-sha256 <sha256 of the current approved-launchers.json>`, which swaps it in one write. Do not run `rollback-last` and then install: after an earlier replace, the rollback restores an older `dayz-test-v1` entry and install refuses it with `launcher_registry_version_already_installed` (dayz-mcp `tools/dayz_mcp/launcher_registry_update.py:229` and `:329` at 90da56e; pipeline inbox fb-20261016-155416-c9aa).

Origin: LFHeli OH-1 (2026-07-25), authorizing the 6th mod, after the 2026-07-22 session was lost to this same flow.

### Testing a mod that is not in the allow-list, without rebuilding the launcher

Authorizing a project is the expensive path: edit `build_native_launcher.py`, rebuild
the PE, update the hardcoded sha256 in the test, roll back and re-install the registry
entry. Sessions have gone into it. It is only needed when the mod must have its OWN
sealed project entry.

To just run the mod in-game, mount it as an `extra_mods` entry on a project that is
already approved. `_mods` appends every `extra_mods` value to the launch list
(`dayz_test_worker.py:204-210`), and `_mod_path` joins a NON-absolute value to the
sealed `mods_root` (`:199-201`), so a bare `@Name` accredits under `P:\Mods`.

The name must be a plain relative one. `_valid_mod_entry`
(`dayz_test_request.py:137-148`) rejects anything containing `:`, `\` or `/`, rejects
`.` and `..`, and requires `ntpath.normpath(value) == value`. An absolute path is
accepted instead, but then it must fall inside a sealed root.

Two constraints that decide whether the run works:

- **The deployed directory must be REAL, not a reparse point.** Same rule as the
  `default_base_mods` format above: `_open_descendant` rejects any component whose
  `reparse_tag != 0`. A junction has to be listed by its absolute workshop path and
  sealed in `mod_roots`.
- **Pick a carrier project that compiles, and check it on the day.** Script compilation aborts on
  the first mod that fails, so a broken carrier's error only surfaces once yours already compiles -
  which reads as "my mod broke it". Whether a carrier compiles depends on its source that day, not
  on the project. [EXACT][CLAIM-TEST-DAYZMCP-CARRIER] On 2026-10-02 (DayZDiag 1.29.163709) project
  `DayZ_MCP` carried extra mods in two runs: `13cc2542` (`@LFInfectedBig`, `@KP_CharAB`) and
  `1c289781` (those two plus `@KP_ChiralWear` and `@KP_ChiralAnim`). In both, the server and client
  script logs read `Module: Mission; loaded 217x files; 540x classes`, with no `CParser` line, and in
  `1c289781` the probe's `4_World` print ran on both peers. Ten minutes before `13cc2542`,
  `LFPowerGrid` carrying `@DayZ_MCP`, `@LFInfectedBig` and `@KP_CharAB` (run `f1afd2c3`) stopped at
  `Can't compile "Mission" script module!` on an error in its own `5_Mission`; on 2026-07-28 it had
  compiled as a carrier (`Module: Mission; loaded 231x files`). Before reading your mod's errors,
  find the carrier's `Module: Mission; loaded ...` line in the server script log; when it is
  missing, `Can't compile "Mission" script module!` and the `crash_*.log` name the failing file.
  *(Corrected 2026-10-03: this bullet said "`@DayZ_MCP` is not usable as one: its `5_Mission` fails
  with `CParser: quoted string not closed` attributed to `mcpclientbridge.c`", measured for SP-128
  on 2026-07-28.)*

Origin: SP-128 (2026-07-28), measured against the launcher source; supersedes the
"cannot be tested at all" reading of SP-089.
 Cross-ref SP-085 (diag hangs, 0 CPU / 0 RPT, when launched outside the registered launcher).

## `-ExecutionPolicy Bypass` - intermittent Codex quirk, NOT a host block (corrected 2026-07-22)

`[corrected by user 2026-07-22]` The previous version of this section (2026-07-21, written by
Codex) claimed that host PowerShell policy was `Restricted` and that Microsoft Defender
interrupted wrappers with `-ExecutionPolicy Bypass`, and from there derived a "BLOCKED-
SECURITY / only managed Python lifecycle" regime. **It was a MISUNDERSTANDING by Codex of what the
user said.** The reality:

- **Codex (ChatGPT CLI) SOMETIMES triggers ITS OWN security policy when the command contains
  `-ExecutionPolicy Bypass`.** It is an intermittent rejection by the Codex AGENT, not a host failure: the
  host PowerShell policy is NOT set to `Restricted` because of this, and Defender does NOT interrupt
  launches.
- Therefore `.ps1`/`.bat` launchers of this skill **are NOT host-blocked**: Claude and the
  user run them normally. **There is no "BLOCKED-SECURITY"** for this reason, nor requirement to
  go through a "managed Python lifecycle" to be able to launch.
- **Only implication, and ONLY when delegating a launch to Codex**: `-ExecutionPolicy Bypass` may be
  intermittently rejected by Codex → avoid that flag in the command you pass to Codex, or
  let Claude or the user handle the launch.
- **Independent and active**: the shared session protocol (FIFO lease + `run_id`,
  "SHARED SESSION PROTOCOL" above) still applies to coordinate launch/stop; it has no relation to
  this.

(A diagnosis report written on the source machine on 2026-07-21 carries over the
same Codex misunderstanding - reconcile or mark if cited. Do not disable Defender or add
exclusions as a "workaround": not applicable, because it was not Defender.)

## Secure-launcher runtime traps: daemon argv, staging dir, opaque errors (SP-092, added 2026-07-26)

Three infra traps cost most of a session on 2026-07-26. All three are cheap preflights.

**1. The daemon argv is derived from the client registrations - and the handoff documented it wrong.**
`host_config.resolve_daemon_provenance()` reads BOTH `~/.claude.json` (`mcpServers.dayz-mcp`) and
`~/.codex/config.toml` (`[mcp_servers.dayz-mcp]`), requires them to agree, and builds ONE canonical
daemon argv. Hand-starting the daemon with anything else is rejected with `daemon_identity_unverified`
- by design, so nothing can squat the port and impersonate the daemon. The session handoff said
`--idle-timeout 1800.0`; the registrations say `600`, so the canonical argv ends in `--idle-timeout 600.0`.
That single wrong number made every retry impossible.
Never guess the argv - ask the system:
`python -c "import sys; sys.path.insert(0,r'<tools>'); from dayz_mcp import host_config; print(host_config.resolve_daemon_provenance().argv)"`

**2. The CLI hides its own error code.** `secure_launcher` prints only
`secure launcher failed: ControlClientError` and swallows the code. Getting `daemon_identity_unverified`
required a wrapper script that caught the exception and read `.code`. If a launch fails, capture the
code first - do not retry blind.

**3. `oh1-build-deploy.ps1` fills the staging dir but never creates it.** `$Stage` under
`%LOCALAPPDATA%\Temp\LFHeli_OH1_stage` holds `$PBOPREFIX$`, so when Windows cleans `%TEMP%` the build
dies with `staging dir missing`. Rebuild it by copying the pack source (models/, proxies/,
`$PBOPREFIX$`, config.cpp) into it; the script overwrites the p3ds with the fresh ODOLs afterwards.

Also: the daemon self-terminates on its idle timeout (600 s), so a launch flow that worked hours
earlier will fail later with no change to the mod. Check port 8765 before blaming the build.

## Secure-launcher request grammar, the Steam prerequisite, and orphaned runs (SP-095, added 2026-07-27)

Four traps in one launch session on LFHeli OH-1. Each is cheap once known and expensive when not.

**1. The CLIENT needs Steam running. The SERVER does not.** A client launched with Steam down exits
immediately, writes a 793-byte RPT with only the header and an `ErrorMessage_*.mdmp` next to it, and
logs NOTHING useful. The real message is only inside the minidump: extract strings and look for
`Unable to locate a running instance of Steam`. There is no Windows "Application Error" event
because the engine handles it itself. Check `Get-Process steam` BEFORE launching a client, and start
it with `steam.exe -silent` if missing, from a shell outside any sandboxed (MSIX) app, never from a
shell inside the Claude or Codex app (point 1-ter).

**1-bis. If that message appears while Steam IS running, stop reading the message and run the
discriminator.** Measured 2026-09-08 on SUB_BRZ: the client died on 5 consecutive launches with
exactly the string above, plus `[API loaded no]` in the same dump, while `Get-Process steam`
returned a live process, `HKCU\Software\Valve\Steam\ActiveProcess` held a non-zero `ActiveUser`
whose `pid` matched it, and steam.exe, DayZDiag_x64 and the daemon all ran as the same unelevated
user. Restarting Steam (`steam.exe -shutdown`, then relaunch) changed nothing, twice. Point 1's
advice ends at "check Steam is running"; when it IS, the reader has nowhere to go.

**The asymmetry is the clue: the server lives and the client dies.** Point 1 already says why - only
the client needs the Steam API - so the split names the suspect on its own, and the experiment that
separates the two causes is to launch the dead half YOURSELF, from your own user shell, with the
same command line (lift it from the RPT header or the dump). Two minutes, and it answers completely:

- **the hand-launched client dies too** -> the host or Steam really is broken, and that fix belongs
  to the user.
- **the hand-launched client lives** -> the DAEMON'S SPAWN CONTEXT is what breaks it, not the host.
  Different owner, different fix, and no amount of restarting Steam will touch it.

On that date it lived: it booted, connected, and reached the in-game HUD. `capture_screenshot` works
on it, because capture is host-side rather than a bridge verb. Filed as `fb-20260908-190943-5073`.

**Caveat that bounds the workaround**: a client you launched yourself is FOREIGN to the run record,
so the instance fence rejects its polls (`unaccredited_polls_by_class.instance_unknown` climbs) and
no client verb reaches it. Without `camera_set` there is no framing. It is good for putting a HUMAN
in front of the screen, not for automating a reading.

**The general rule, worth more than this case**: when one half of a client/server pair dies and the
other lives, their differing requirements already shortlist the cause. Run the by-hand launch of the
dead half BEFORE believing whatever subsystem the error message happens to name. Here the message
named Steam, and Steam was the one thing that could not help.

**And when it IS the daemon, re-measure before treating the wall as permanent.** Confirmed on
SUB_BRZ 2026-09-10, the day after: the same launch succeeded on the first try -- `client_alive=true`
at 17 s, player in game at 51 s, no Steam intervention, and `auto_remediate_steam` not even
requested. The only thing that had changed was `session_status.daemon_generation`. The wall was
daemon STATE, not the host, and a daemon restart cleared it. So record `daemon_generation` when you
file the finding, compare it when you retry, and give a freshly restarted daemon one clean launch
before spending a session on the workaround.

**1-ter. A client YOU start from a shell inside the Claude or Codex app can read a Steam that is
gone.** Those apps keep a private copy of `HKCU` for every process they start (MSIX registry
virtualization), and once anything inside the app has written Steam's keys the copy stays on that
Steam's pid after it exits. Measured 2026-10-16: an agent's `Start-Process` of the retail client from
a Claude app shell read `pid = 67468`, a Steam gone since 2026-10-06, and died with point 1's message
while `steam.exe` ran; the 11 `dayz_test_run` launches of that day passed Steam, because the daemon
runs outside the app and reads the real key. It also fools point 1-bis: a by-hand launch from such a
shell dies for this reason, not because the host is broken.

- Before a by-hand launch from an app shell, compare `(Get-ItemProperty
  HKCU:\Software\Valve\Steam\ActiveProcess).pid` read there with `(Get-Process steam).Id`.
  dayz-mcp's `session_status` names a mismatch as the warning `steam_app_view_stale`.
- Launch from outside the app instead: from Steam, from Explorer, or through WMI
  (`Win32_Process.Create`, as the daemon does).
- Never start Steam, or write or delete its registry keys, from the app's shells: that is what
  creates or freezes the copy, and only an offline edit of the app's hive with the app closed removes
  it (dayz-mcp's `tools/clear-app-steam-shadow.ps1`). Background in
  `dayz-1-30-test-ingame.md`, "Launching the 1.30 DayZDiag directly", point 2.
  [EXACT] (measured, LL-510 / SP-420 / LL-516)

**2. The request JSON must not carry a UTF-8 BOM.** `Out-File -Encoding utf8` in Windows PowerShell
5.1 writes a BOM and the parser rejects the whole request with `invalid_dayz_test_request`. Write it
with `[IO.File]::WriteAllText($path, $json, (New-Object Text.UTF8Encoding($false)))`, or copy a
known-good request file and string-replace the fields.

**3. The request grammar has two coupled rules** (`dayz_test_request.py:336-344`), and violating
either returns the same opaque `invalid_dayz_test_request`:
- `kill: true` REQUIRES a `run_id`.
- With a `run_id`, `mode` may NOT be `server` or `all`; and `mode: "client"` REQUIRES a `run_id`.
So the valid shapes are: `server`/`all` without run_id (starts a run), `client` with run_id (joins
one), and kill as `mode: "client"` + `kill: true` + run_id (stops the run, not just the client).
`mode: "all"` in one request launches server AND client and avoids the run_id dance entirely - prefer
it when starting fresh.

**4. `run_not_adoptable` means the run is gone but its processes may not be.** The kill path tries
`adopt` then `stop` (`dayz_test_worker.py:496-507`); when both fail the lifecycle has lost the run
while a DayZ process may still hold port 2302, so every new run fails with `worker_failed` and the
audit trail shows `session_rejected reason=process_identity_mismatch`. Read
`%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl` (tail) - it names the real reason, which the CLI hides.
Recovery is a documented DEGRADED CLOSURE: close that specific process after verifying by
`CommandLine` that it is yours, then start a fresh run. This is the sanctioned exception to "never
kill DayZ processes directly": it applies only to a process you launched, under a run the guard has
already disowned, that is blocking the port.

**Also**: `lifecycle_cli.py` cannot be invoked standalone - it answers `missing_lifecycle_environment`
because the launcher chain sets its environment. Drive lifecycle operations through
`secure_launcher.run_secure_launcher` with a request on stdin.

**Method note that cost real time here**: `host_config.resolve_daemon_provenance()` raises
`daemon_provenance_conflict` if you call it with the SYSTEM python instead of the `.venv-mcp`
interpreter that both registrations declare - it compares `command` against the local launch
executable (`host_config.py:218-222`). That is a false alarm produced by the caller, not a
divergence between the Claude and Codex registrations. Always invoke with
`<dayz-mcp>\tools\.venv-mcp\Scripts\python.exe`.

Cross-ref SP-089 (allow-list format), SP-092 (daemon argv, staging dir, opaque errors), SP-085
(diag hangs outside the registered launcher).

## `dayz_test_run` with `build:true` does NOT build - and the error it returns does not say so (SP-139, added 2026-07-29)

(Windows, measured 2026-07-29. On Linux `build=true` goes through dayzmake (then still named armake2) and did build, 2026-11-06; see `linux.md`.)

On this box DayZDiag only starts via registered native launcher (SP-085), so
`dayz_test_run` is the only way. **Its `build:true` is BROKEN**: returns generic
`dayz_test_failed` and **does NOT write the PBO** (hash and mtime of deployed remain intact).
Measured 2026-07-29 in DayZ_MCP, reproduced 2 times, always at ~16 s.

Why it is deceptive: `dayz_test_failed` is the `except Exception` of `server.py:1101`, which **swallows the
real cause** - it is not a tool error code, it is "something threw and I don't know what". Reading the audit
(`%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl`) is not enough here either: lease is granted and
released cleanly, with `runs_released: []` and no run event. Looks like a build failure and does
not say where.

**Bisection isolating it in 3 calls** (perform it before touching anything):

| Call | Measured result | What it rules out |
|---|---|---|
| `preflight: true` | `succeeded` in 1.5 s | launcher, PE, bundle, request, and lifecycle are HEALTHY |
| `mode: server` without `build` | `succeeded` in 5.1 s | launch works |
| AddonBuilder by hand | `Build Successful`, exit 0, ~3.4 s | **AddonBuilder is not the culprit either** |

With those three, the failure is isolated to the LIFECYCLE build path, which is platform.

**Verified and repeatable workaround** (build outside published path, which is also what
"RELEASE-GRADE BUILD BOUNDARY" in `windows-launch-cycle.md` requires):

```powershell
# 1. build to staging, NEVER directly to published path
AddonBuilder.exe P:\<Mod> <staging> -prefix=<Mod> -temp=P:\temp\<Mod> -clear -packonly
# 2. validate by CONTENT before publishing (count anchors, not Contains -- SP-065)
# 3. publish and verify by SHA-256, not by mtime
Copy-Item <staging>\<Mod>.pbo P:\Mods\@<Mod>\Addons\<Mod>.pbo -Force
(Get-FileHash 'P:\Mods\@<Mod>\Addons\<Mod>.pbo' -Algorithm SHA256).Hash
# 4. start with dayz_test_run WITHOUT build
```

Two preconditions that were already documented and are load-bearing here: deployed PBO remains
**LOCKED while the run is executing** (stop run before publishing), and per SP-078 **scripts do not
hot-load on this install**, so each Enforce iteration requires this entire cycle.

Origin: DayZ_MCP, grouped gate of `query_all_players` (2026-07-29). Real cost: ~20 min of
bisection on an opaque error naming neither build nor launch.

**Associated method lesson**: `LL-224` - the opaque error was narrowed down by bisecting CAPABILITIES (preflight / without feature / tool by hand), not reading the code that threw it. The table above IS that bisection; reuse the pattern for any wrapper error that describes nothing.

## `dayz_test_run` `extra_mods` REPLACES the extras list, does not extend it (SP-323, added 2026-08-22)

Passing `extra_mods=["@MyMod"]` to `dayz_test_run` **replaces** extra mods with that
list instead of appending to those the project brings. If the `@DayZ_MCP` bridge traveled
there, it drops out and **all MCP verbs stop working even though the pair
boots perfectly**: both processes alive, responding, with mission loaded,
and `bridge_status.ready.reason = server_poll_stale` with `last_poll_age_s` frozen at
the value from PREVIOUS run. Misleading symptom because everything else is healthy.

**Cheap 5 s check**: grep server script log for `DayZ_MCP` in the list of
`defines:` of any module, or for the line `[DayZ-MCP] config loaded ... poll_hz=`; if absent,
the mod was not loaded. ALWAYS name `@DayZ_MCP` explicitly in `extra_mods`.

Second note from same launch: **`mode="pair"` does not exist** and returns
`bad_dayz_test_request` without saying which are valid. Modes are `server`, `client`,
and `all`. Reliable path remains `server` -> wait -> `client` with same
`run_id` (T9-HARNESS-046), not `all`.

Origin: session 2026-08-22; one full boot cycle lost to this.

## (added 2026-08-01, HH-60G v19) Diag RPT BUFFERS ~52 KB, and lifecycle needs its window after run_not_adoptable

Two operational facts from 6-boot overnight run (all reproduced several times):

1. **A frozen RPT does NOT distinguish dead process from un-flushed buffer.** Diag writes the
   RPT to a buffer of ~52 KB (tonight: 5 distinct boots, ALWAYS ~464 lines / ~52 KB at the
   moment of failure, with different contents). Real discriminant is **CPU delta of
   the process in 30 s** (`Get-Process` twice): flat = truly stopped; growing =
   alive with log buffered. Additionally `Get-Item`/stat over P:\ (OneDrive) can lie about
   size (927 b reported with 52 KB real): read with `Get-Content` (share-read) and count.
2. **After a `run_not_adoptable` from `dayz_test_stop`, the lifecycle has a reconciliation
   window**: next `dayz_test_run` returns `active_run_exists` even if
   processes are dead. Pattern that worked (x3): close orphan DayZDiag by
   process, retry stop until it returns `run_not_active`, and ONLY then launch
   the new run.

## SP-124 - Free lease does NOT imply free box

`session_status` can return `owner: null`, empty queue, and `claimable: true` while a DayZ
server and client are alive, launched outside the managed lifecycle by another project
line and occupying port 2302. The lease speaks of the lease, not of the box.

Before considering the box free, read `-mod=` of living processes:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" |
  Select-Object ProcessId, CommandLine
```

The command line tells whose run it is and whether it loads your mod.

Corollary for build: the "no DayZ process" guard can be **narrowed** to the two
conditions it actually represents -no running process loads your mod, and target PBO opens
exclusively- instead of skipping it or waiting for the other line to finish.

Cross-ref: `dayz-mcp-verify` (same rule, bridge side).

## (added 2026-09-08) Three walls of managed startup that do not name their cause

Measured in a verification startup of LFPowerGrid. All three return a code that does not
describe what happens, and all three are resolved in one minute if you know which it is.

### 1. `launcher_root_identity_drift` - the seal fixes the DIRECTORY, not just binary

Sealed registry pins NTFS identity **of the directory** containing launcher
(`launcher_registry.py` `_open_validated_entry`: compares `root_file_id` = `file_id` +
`volume_serial_number` against `os.stat(root)`). If that directory is **recreated** -and it is under
OneDrive, which does so- `file_id` changes and **the entire** managed path dies, `preflight`
included. Binary can be byte-identical and it makes no difference.

**Diagnosis before touching a security seal**, because it distinguishes benign drift from
tampering: compare the two fields of `root_file_id` separately and **the sha256 of the PE**.
Same volume + different `file_id` + **PE with pinned hash** = directory was recreated and
binary did not change.

**Remedy** (it is the owner's to authorize, not yours to decide):

    cd <dayz-mcp>\tools
    .venv-mcp\Scripts\python.exe -m dayz_mcp.launcher_registry_update         replace-dayz-test-v1 --expected-sha256 <REGISTRY SHA256, IN UPPERCASE>

- It is `replace-*`, not `install-*`: `install` refuses while entry exists.
- CAS token is the sha256 **of the bytes of `approved-launchers.json`**, not of the PE.
- ⚠ **MUST BE IN UPPERCASE.** `_HEX = frozenset("0123456789ABCDEF")`, so a lowercase sha
  -what `sha256sum` produces- fails with `invalid_launcher_registry_update`, which says nothing
  about the format and sends you looking for the problem where it is not.
- Returns sha of the NEW registry, which is the CAS token for next operation.

### 2. Occupation is of BOX, not port: `port=` does not dodge a foreign process

With a foreign DayZ running, `dayz_test_run` returns `active_run_exists` / `port_in_use_foreign`
**even if you pass another `port=`**, and keeps naming 2302 in the error. The first hint says
"pass another port="; the second, with the box already read as occupied, says "retry with
wait_for_box_s". **The one that works is the second**: `wait_for_box_s` puts request into FIFO.
`port=` is only valid to coexist when the box is ALREADY yours.

Before waiting, verify that occupant is alive and not a zombie: `Get-Process` on
`DayZ*` and check **CPU and start time**. Growing CPU = real run of another line, it is
respected. And look at its `-mod=`: tells you whose it is.

### 3. `mode=client` requires repeating `extra_mods`, or rejects reattach

Complement of SP-323 measured today: on client reattach, omitting `extra_mods` does not inherit those
from server start - fails with `bridge_mod_missing: add extra_mods=['@DayZ_MCP']`. Pass the
**same list** as in `mode=server`, or whole set's seal changes in addition to losing bridge.

### Bonus: `condition_failed` vs `action_not_found` is a discriminator, with its control

`action_use` distinguishes the two things, and that turns a cheap probe into proof: `action_not_found`
= action class is not in player array; `condition_failed` = **is present and resolved
against target**, and rejected by its `ActionCondition`. Serves to accredit that an action
reaches an entity type without setting up the fixture satisfying its guard. **With negative
control**: also launch an invented action name on the same object and verify that it gives
`action_not_found`; without that control you do not know if both codes are truly distinguished.

## A disposable probe does not need to register as an MCP project

`P:\Mods` is `mod_root` of the ten approved projects in `request-policy.json`, and
`dayz_test_tool._valid_public_mod` accepts any relative folder inside those roots. Thus:

```
dayz_test_run(project="DayZ_MCP", mode="all", extra_mods=["@MyProbe"])
```

starts with the full bridge (`capture_screenshot`, `camera_set`, `query_player_state`, `wait_for`
on `log_matches`) **plus** your probe, without touching sealed policy or rebuilding it with
`build_native_launcher.py`.
