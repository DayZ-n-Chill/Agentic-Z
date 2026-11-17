# Linux and Proton findings: making the tooling and dayz-mcp work on Linux

Covers what was measured between 2026-11-03 and 2026-11-06 when running DayZ Tools, the DayZ server and client, and the third-party DayZ-MCP bridge on Linux under Proton and podman.

Status: measured results on one Linux machine. Not yet checked on `P:\`: these are tool, launcher and operating-system observations, and each names the DayZ-MCP version (by commit) it was measured on. The one vanilla class the bridge leans on, `RestApi`, is declared at `P:\scripts\3_game\http\restapi.c:147`. The measured guide built from these notes is `skills/_shared/linux-proton.md`.

Scope (2026-11-15): these are measurements of 2026-11-03 to 2026-11-06 on DayZ-MCP's Linux development branch, not new runtime results on its main line. That Linux work reached DayZ-MCP's main line on 2026-11-14; the runs recorded below were made before that and were not repeated on the main line. The helper scripts these notes mention ship in `skills/_shared/scripts/` (server tree, ports, headless client, `dayz-mod-pack.sh`, source extraction). Full managed binarization with assets remains unverified. The packer used for every measurement here was the DayZ build of armake2, which has since been renamed dayzmake at `v1.0.0`; the `armake2` commands below are recorded as run, and today's equivalent is `dayzmake` with the same subcommands (use `v2.0.0` or later before running `dayzmake unpack` on third-party PBOs).

These are raw findings. Sections 1 to 4 are the first pass; sections 5 to 9 record what was built from them, and section 9 corrects three earlier statements. Re-check an item before relying on it.

Machine: Debian testing, Python 3.14, Steam native, GE-Proton11-1, native Linux `DayZServer`
(app 223350), DayZ client (app 221100) under Proton. dayz-mcp at commit `0107c0c` (2026-11-03).

## 1. Structural facts about the Linux setup

- **DayZ Tools (830640) and DayZ (221100) are different Steam apps, so each gets its own Proton prefix.**
  The DayZ Tools themselves run fine under Proton, AddonBuilder included. What breaks is every tool step
  that needs **game data**: the tools prefix does not know where the game is, so that data has to be
  linked into it. Observed on this machine: the game prefix has
  `HKLM\Software\Wow6432Node\Bohemia Interactive\DayZ` `"main"="S:\steamapps\common\DayZ"`, while in the
  tools prefix (`compatdata/830640`) the same key exists but is **empty**. The tools prefix has an `s:`
  drive pointing at the Steam root, and no `P:`. So the link is the `main` value in the tools prefix,
  plus a `P:` with the game data the tool resolves (`dz\...`). This repair is not tested here; the
  measured route is in `skills/_shared/linux-proton.md`. dayz-mcp's `dayz_tools_paths.py` and `pack-addon.ps1` need that
  linked prefix. For these tests the addon was packed with the DayZ build of armake2 (`armake2 build`, `keygen`,
  `sign`), and the game was started by hand.
- The **native Linux `DayZServer`** runs mods and the dayz-mcp bridge unchanged (see 3). Its defines
  include `SERVER_FOR_WINDOWS` and `PLATFORM_LINUX`.
- The **client runs under Proton** (Steam Linux Runtime → Proton → `DayZ_x64.exe`). It accepts
  `-profiles=Z:\<linux path>`, and `$profile:` resolves there. It loads an `@Mod` that is a
  symlink in the client's DayZ folder pointing at a Linux path. Started headless in sway;
  `skills/_shared/scripts/dayz-client-headless.sh` does this.
- **Client and server builds must match.** The Steam client auto-updated to 1.30.164289 while the
  DayZ Server app was still 1.30.164200 (`StateFlags=6`, update pending): the client is refused with
  `CONNECTING FAILED (0x00020013) Client is a newer build than the server`. Check both
  `appmanifest_221100.acf` and `appmanifest_223350.acf` (`buildid`, `StateFlags` 4) before a
  client/server run.

## 2. dayz-mcp Python side on Linux

`tools/` does not import on Linux. Each blocker below was worked around with a throwaway shim (a
`sitecustomize.py` plus a launcher script) to see how far it gets; the list is what a real port needs.

| # | Where | Problem on Linux | Shim used / proper fix |
|---|---|---|---|
| 1 | `win32_fileinfo.bind_common_kernel32` (called at import by `pinned_keyfile`, and more) | `ctypes.WinDLL` does not exist → `AttributeError` at import | fake `WinDLL` whose functions raise when called. Fix: bind lazily, POSIX branches |
| 2 | `dayz_test_worker.py:1250` (module level) | `stat.IO_REPARSE_TAG_MOUNT_POINT` / `_SYMLINK` exist only on Windows | define the constants. Fix: guard with `getattr` or `os.name` |
| 3 | `inbox.py:23` (module level) | `os.environ["LOCALAPPDATA"]` → `KeyError` | set `LOCALAPPDATA`. Fix: XDG state dir (`$XDG_STATE_HOME/dayz_mcp`) on POSIX |
| 4 | `daemon_policy.py:8` | `import msvcrt` at module level | stub module. **Pitfall:** a `msvcrt` module on `sys.path` makes CPython's `subprocess` think it is on Windows (`import _winapi` fails); the stub must be put in `sys.modules` only after `subprocess`/`asyncio` are imported. Fix: `fcntl.flock` on POSIX |
| 5 | `pinned_keyfile.read_pinned_keyfile` (`loopback.read_key`) | Win32 handle-based reader → always `invalid_daemon_keyfile` | plain read. Fix: POSIX reader (`O_NOFOLLOW`, `fstat`: regular file, `st_nlink == 1`, size cap) |
| 6 | `--daemon` mode, `instance_context.try_acquire` → `_open_shared_lock` | `OSError: root_writer_lock_open_failed` (Windows byte-range lock) | used `--embedded` instead. Fix: `fcntl.lockf` on POSIX |
| 7 | `loopback.ExclusiveThreadingHTTPServer.allow_reuse_address = False` | correct on Windows (there SO_REUSEADDR allows a second LISTEN), wrong on Linux: a restarted daemon cannot bind while the game's polls left the port in TIME_WAIT (`Errno 98`) | set `True` on POSIX. On Linux SO_REUSEADDR does not allow a second listener |
| 8 | `session_*` tools | `session_tools_require_client_mode`: leases only exist in `--client` mode, which needs the daemon (#6) | blocks every lease-gated tool until #6 is ported |
| 9 | run binding | a game started by hand polls as `LEGACY_UNBOUND`: reads only, every mutation and most reads refused with `game_not_ready:reason=legacy_unbound`. Binding comes only from the managed launcher (Windows process identity, native launcher bundle) | bound by hand with `ServerState.install_bound_peer(instance=<uuid4>, role="server", pid=<enfMain pid>)` (the test helper), and wrote `"instance": "<uuid4>"` into `dayz_mcp.json` **before** the game starts (the bridge reads `instance` only at init; `ReloadKeyAfterFailure` re-reads the key only). After that the polls show `bind=BOUND`. Fix: a supported "bring your own game" binding (CLI or MCP verb that takes a PID + token and writes the config) |

Not reached (needs a matching client): `bridge_status` readiness also requires the **client** peer to poll
(`client_not_polling`), so even the server-side reads (`surface_query`, `scene_raycast`) were refused with only
the server bound. A server-only mode (useful for terrain checks on a dedicated server) would need that gate relaxed
for server-peer tools.

Platform-specific code to review for a port: `grep -l -E 'winreg|windll|WinDLL|msvcrt|win32|_winapi|
LOCALAPPDATA|IO_REPARSE' tools/dayz_mcp/*.py` hits about 25 modules (`wmi_host`, `window_*`,
`foreground_lock`, `steam_preflight`, `registry_lock`, `launcher_registry*`, `identity_migration`,
`native_*`, `orphan_guard` with `netstat.exe`, `authenticode`, ...). Most are launcher/desktop features that a
Linux port can leave out. The minimal Linux set is: loopback daemon + client mode + leases + a manual binding
(#1–#9).

## 3. dayz-mcp addon (Enforce side) on Linux — works

- `addon/` packed with `armake2 build addon <out>/addons/DayZ_MCP.pbo` (prefix `DayZ_MCP` from
  `$PBOPREFIX$`) and signed with `armake2 keygen`/`sign`. It loads on the native Linux server with
  `-mod=@DayZ_MCP`: the Mission module compiled; warnings only (`IsVitalCarBattery`, `IsVitalTruckBattery`,
  `ForceUpdateLightsStart` obsolete in 1.30).
- `RestApi` polling from the Linux server to the Linux daemon on `127.0.0.1` works at about 1.1 Hz
  (`pollHz 5` configured, measured interval 0.9 s while idle).
- After the daemon restarts, the bridge logs `poll error=7` with backoff up to 30 s and recovers by itself
  once the port is back.
- Under Proton the client loaded the same PBO from a symlinked `@DayZ_MCP` and `$profile:` from
  `-profiles=Z:\...`. Whether its `RestApi` reaches the Linux loopback was **not reached**: the bridge starts
  in-mission and the join failed on the build mismatch (section 1).

## 4. Next steps to finish the test

1. Let Steam finish updating the DayZ Server (223350) to the client's build.
2. Run again: Linux server + Proton client, both with `instance` tokens in their `dayz_mcp.json`, bind both
   peers (`role` `server`/`client`, client PID = the Linux PID of the `DayZ_x64.exe` wine process), and
   check `bridge_status` → `ready`, then `surface_query` / `scene_raycast` / `player_teleport`.
3. Port #6/#8 so leases work. Until then only the embedded, lease-free subset can be tested.

## 5. Follow-up, same day: what changed after these notes

- **DayZ Tools under Proton** were measured tool by tool and turned into
  `skills/_shared/linux-proton.md` (guide) and `skills/_shared/scripts/dayz-proton.sh` (runner). Short
  version: the cross-app problem is the missing `P:` and the empty game key in the tools prefix, plus
  what Steam does on a first launch (install-script registry, VC++ runtime) that a private prefix
  lacks. ImageToPAA, CfgConvert, the DS tools, AddonBuilder, binarize, TexView, Object Builder,
  Workbench and DayZDiag (client and `-server`) all ran.
- **armake2 `--proton-binarize` alpha bug**: fixed in the DayZ build of armake2 by commit `0a0ce3b`; a build from commit
  `7dcb3cf` gives output byte-identical to BI's binarize run from a `P:` root. An older installed build
  still showed the 20-byte difference (texture not found); `--version` prints `v0.3.0` for both.
- **Build match**: by the evening both client and server reported 1.30.164289 (`doctor` in the runner
  compares the game versions; Steam `buildid`s differ per app by design). The Experimental server
  (1042420) was still on 1.30.164200 with an update pending.
- **dayz-mcp Python side**: the Linux branch (commit `ac5578d`) fixes #1–#5 and #7 properly
  (no shims): every module imports except `native_launcher_backend`, the POSIX keyfile reader, OFD
  byte locks, `SO_REUSEADDR` on Linux, XDG state dir. `--embedded` answers MCP `initialize` and
  `tools/list` (107 tools) and serves the loopback. #6/#8 got further: the daemon passes the instance
  lock, startup election, interpreter check and process scan, then stops at the runs.json identity
  migration (`runs_backup_transaction_publish_failed`), which is built on Windows handle semantics
  (no-clobber rename, delete through a pinned handle, file-ID identity) and needs a POSIX design.
  The modules sealed into the native launcher (`tools/packaged-modules.lock.json`) are left
  byte-identical: the Linux code lives in the unsealed `linux_compat.py` (its `install()` runs first
  in `python -m dayz_mcp` and swaps Linux implementations in) and `byte_lock.py`, so no launcher
  rebuild is needed. #9 (binding a hand-started game) is unchanged; attaching to a game under Proton
  is a poor fit (its Linux PID is a Wine process), so the intended route is a Linux launch path in
  which the daemon starts the native server and the Proton client itself and binds them by per-run
  token. The Windows test suite was not run.

## 6. Follow-up, 2026-11-04: podman server, daemon on Linux, binding measured

- **Native server in rootless podman** (dayz-mcp `bbcd0c5`, `tools/dayz_mcp/podman_server.py`): a minimal `debian:trixie-slim` image, a private tree per run,
  `--network host`, the install and mods mounted read-only as overlays. The container (name, ID,
  image ID, labels) identifies the run, and `$profile:dayz_mcp.json` is written before start.
  1.30.164289 with `@DayZ_MCP` loaded the mission in about 10 s and stopped cleanly in about 13 s.
- **runs.json migration on POSIX** (dayz-mcp `850e48f`, `tools/dayz_mcp/posix_fileops.py`): the
  three Windows handle behaviours are rebuilt. The no-clobber rename is
  `renameat2(RENAME_NOREPLACE)`, with `link`+`unlink` as fallback. "Verify, then delete on close"
  becomes: open `O_NOFOLLOW` under a held directory fd, check the bytes, rename to a random
  quarantine name and unlink only if that inode is the pinned one. A concurrent swap cannot be
  blocked as on Windows, but it is detected: the call reports a conflict and deletes nothing foreign.
  With that, `--client` spawns `--daemon`, the migration completes, the client's connected-daemon
  identity check passes and `session_status` answers. Three more sealed-module path checks needed
  replacing through `linux_compat.install()`: `ntpath.isabs` is false for `/home/...` since Python
  3.13, and `daemon_policy_contract.valid_absolute_path` demands a drive letter. The sealed module
  hashes are unchanged (21/21 match `packaged-modules.lock.json`).
- **Install detail**: create `tools/.venv-mcp` with `python3 -m venv --copies`. Sealed `host_config`
  refuses a registered `command` that resolves to another path, and a default venv's `bin/python`
  is a symlink. The client also needs the dayz-mcp registration in both `~/.claude.json` and
  `~/.codex/config.toml`, and the two must agree, as on Windows.
- **Binding measured, podman server + daemon**: the bridge's established poll connection to the
  daemon is owned in the host TCP table (`psutil.net_connections`) by the containerised `DayZServer`'s
  **host PID**. That PID is `podman inspect .State.Pid`, its `/proc/<pid>/exe` is the Steam
  `DayZServer`, and `/proc/<pid>/cgroup` names the container ID
  (`libpod-<id>.scope/container`). So the loopback's existing binding (poll → one PID → creation
  time) works for a container run unchanged. Polls still arrive `LEGACY_UNBOUND`, because nothing
  registers the run.
- **Still missing**: `dayz_test_run` goes through the sealed Windows native launcher
  (`native_launcher_backend`: a debugger-attached child in a job object), so it cannot start a
  Linux run. Wiring podman in means a Linux launch backend at that seam. It mints the instance,
  writes it into `dayz_mcp.json` before `podman run`, then records the run with host PID and
  creation time, with the container ID and image ID as cross-checks (cgroup). The Proton client
  (the Linux PID of the Wine `DayZ_x64.exe`) would bind the same way.

## 7. Follow-up, 2026-11-04 (evening): `dayz_test_run` on Linux, server role

The "still missing" item of section 6 is done for `mode=server` (dayz-mcp `7effeef`), behind the same lease, sealed worker and daemon lifecycle as on Windows. The sealed modules are still
byte-identical (21/21).

- **Launcher without the PE.** A Linux bundle in `$LOCALAPPDATA/DayZ_MCP/linux-launchers/dayz-test-v1/`
  holds the same `app.pyz` and the same `request-policy.json` / `worker-runtime.json` the Windows
  builder emits from the launcher policy (POSIX paths), pinned by a manifest and checked against
  `packaged-modules.lock.json` on every open (`python -m dayz_mcp.linux_launcher install|status`). A
  Python relay replaces the PE's loop: the sealed worker runs under the approved interpreter from the
  verified archive bytes, and only a per-frame `--lifecycle-child` sees the lease token and identity.
  `secure_launcher.py` and the builder stay unedited (both feed the Windows build contract): a
  stand-in `native_launcher_backend` module hands the launch to the relay.
  The PE's debugger gate and job object are not rebuilt.
- **Daemon launch in podman.** `ProcessLifecycle._launch` off Windows runs the worker's server argv in
  rootless podman. Config, profiles and mission are absolute and mounted at their own paths (absolute
  `-config`/`-profiles`/`-mission` work on the 1.30 Linux server); each `-mod` becomes an `@name` link
  in a private tree. The launcher waits until the container's PID 1 has exec'd DayZServer, and checks
  that PID's cgroup and the image. The run is recorded by host PID and creation time, as on Windows.
  The daemon allows only the server binary paired with its `game_path`
  (`steamapps/common/DayZ` → `DayZServer/DayZServer`).
- **Host probes ported**: the process scan walks `/proc` (a Proton process is named by its Windows
  `argv[0]`). In the UDP holder scan, other users' sockets (chrony, avahi, rpcbind), which an
  unprivileged process cannot map to a PID, are labelled `uid:<n>`; before that every Linux host read
  as `port_attribution_unknown` and no launch was admitted.
- **Measured end to end** (DayZServer 1.30, `@DayZ_MCP`): `dayz_test_run mode=server` succeeded
  (`lifecycle_ack: launch_identity_match`). The bridge's server polls arrived **bound** to the run
  (`server_bound_last_poll_age_s` ≈ 0.3 s, equal to the unbound age). `dayz_test_stop` matched the
  identity and killed the container's DayZServer (`terminated: 1`, run `EXITED`, container removed by
  `--rm`). A container killed by hand was retired by the run reaper within one pass.
- **Engine findings** (guide section 5): `-filePatching` makes the native `DayZServer` 1.30 busy-poll
  `/proc/self/statm` and `/proc/meminfo` after the last building type, and the landscape never
  finishes. This was measured natively and in podman, while without the flag the landscape loads in
  about 10 s, so the podman launcher drops the flag and labels the container. Separately, a mod folder
  mounted `:ro` is skipped without a log line, and `:O` loads it.
- **Still missing**: the client and offline roles (DayZ under Proton, bound by the same PID rule: the
  Linux PID of the Wine `DayZ_x64.exe`), build mode (AddonBuilder), and the Windows suite run for
  these changes.

## 8. Follow-up, 2026-11-05: the client role, implemented but not yet run

dayz-mcp `3a82bdc` adds the client and offline roles for `dayz_test_run` on Linux. They use the headless
chain of `skills/_shared/scripts/dayz-client-headless.sh` (headless sway, Steam Linux Runtime 4, `proton run`) with `DayZDiag_x64.exe`, not the retail
`DayZ_x64.exe`, which the daemon treats as the user's own game. The Steam check reads `SteamPID` from
`~/.steam/registry.vdf`. No managed client was started (the client was in use), so the join and the bound
client polls are still open. Measured on the way:

- **`DayZDiag_x64.exe` 1.30.164289.70 under GE-Proton11-1**, started through that chain, loads a mod from an
  absolute `-mod=Z:\tmp\...\@DayZ_MCP` and writes its RPT, script and error logs into
  `-profiles=Z:\tmp\...`. Mods need not be linked into the Steam install for the diag client.
- **It is a host process.** Pressure-vessel does not hide it: `comm` is `enfMain`, `argv[0]` is the
  `Z:\...\DayZDiag_x64.exe` path, and its parent is `pv-adverb`.
- **Wine leaves the rewritten argv NUL-padded.** psutil reads the padding as empty arguments (222 after a
  DayZDiag command line). Any tool that rejects empty arguments, as dayz-mcp's process guard did, cannot
  identify a Proton process until it trims them.
- **The Steam PID on Linux** is `HKLM/Software/Valve/Steam/SteamPID` in `~/.steam/registry.vdf` (and
  `~/.steam/steam.pid`), held by `ubuntu12_32/steam`. The `ActiveProcess` key inside a Proton prefix holds a
  Wine PID, which says nothing about the native Steam.

## 9. Follow-up, 2026-11-06: the full cycle ran, and three earlier statements were wrong

dayz-mcp's Linux branch, a version newer than `3a82bdc`. Machine as above, DayZDiag 1.30.164289.70 under GE-Proton11-1, `@DayZ_MCP`,
every result through `dayz_test_run` with a scratch `HOME`.

**Corrections to the sections above**

- Section 7: "absolute `-mission` works on the 1.30 Linux server" was wrong. Modules load and the bridge polls, so it
  looked healthy, but the RPT says `Mission script has no main function, player connect will stay disabled!`. The
  `dayz_test_run mode=server` runs of section 7 used that path. A relative `-mission=mpmissions/<name>` gives `[CE][Hive]`
  and `[IdleMode]`.
- Section 8: the Steam PID is `~/.steam/steam.pid`. `SteamPID` in `registry.vdf` was 20624, no such process, with
  Steam live as 20622, so a freshly started Steam read `steam_session_stale`. Section 8 passed, presumably because
  the value happened to match that day.
- Sections 7 and 8: a `DayZDiag` client cannot join the native `DayZServer`, so the planned pairing could not work:
  `CONNECTING FAILED (0x00020017): Client is using Diag exe while the server is not`. Nothing in the RPT says so; a
  screenshot of the headless session did. The earlier manual attempt that "stopped while loading" was this.

**What the daemon does now**: the policy's `diag_executable` picks the engine. `DayZDiag_x64.exe` runs both roles
under Proton, one headless sway each, one prefix; `DayZServer` is server-only in podman, and a client is refused
with `client_needs_diag_executable`.

**Measured**

| What | Result |
|---|---|
| `mode=all` | `ready`, both polls bound to the run, about 34 s after `dayz_test_run` returned (it took 15 s once, 138 s once; the difference was not looked into) |
| The join | server RPT `Player "Dev" ... is connected`; screenshot: player in the world, with HUD. `ready` can precede it: at one `ready` the client was still on its loading screen |
| `dayz_test_close`, client still loading | `graceful: true`, `stop_method: orderly_close`, `exit_metrics_valid: true`, 3.6 s; both RPTs end `--- Termination successfully completed ---` |
| `dayz_test_close`, player in the world (2 of 2) | `logout_finished: true`, server RPT ends with the termination line; the client reaches `Destroying game` and exits with code 3 before its own, so `graceful: false`, `exit_metrics_valid: false`, about 21 s. Cause unknown |
| `mode=all build=true pack_only=true` | armake2 in the sealed worker's path; PBO in `@DayZ_MCP/Addons/`, loaded by both roles, polls bound, player connected |
| `dayz_test_stop` from a second session | `run_protected` with `retry_after_s` (the 600 s abandon rule, as on Windows) |
| Native server | SIGTERM is an orderly shutdown as a container's PID 1, 11.5 s; loads `Addons/` |
| `DayZDiag -server -filePatching` with a packed mod | no hang, takes a player |

**Limit**: a daemon that dies between a game's launch and its record cannot re-match it, because the launch intent
hashes the worker's argv and Wine rewrites it (`lifecycle_launch_intent_unmatchable: argv_mismatch` in the audit log).

**Not measured**: a binarizing `build=true` through a full managed run (the relay function ran `build
--proton-binarize` on an addon without binarizable assets); bridge tools in the world beyond `bridge_status`. The
Windows suite passes on these changes in CI, without a game. Seen once and not reproduced: a `dayz_test_stop` from a second session took 180 s
and failed with `NativeLauncherTransactionError` while an aborted session's lease was still running out. In-game the
picture filled about 1600x900 of the 1920x1080 output, which affects screenshots.
