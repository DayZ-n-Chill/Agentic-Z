# Testing on a Linux host

What changes for this skill when the host runs Linux: which engine runs where, how mods and paths are named, what dayz-mcp does there, and the rules that fail quietly when missed. The other files in this folder describe Windows and stay valid there. The Proton setup, the tool matrix and its pitfalls are in `_shared/linux-proton.md`; the native server has `linux-native-server.md` and the headless client has `linux-headless-client.md`.

All of it is measured behaviour of the Linux server, Proton and the third-party dayz-mcp tool on DayZ 1.30. None of it is vanilla, so it is not checked on `P:\`.

## Two routes

| Route | Engine | How to start it |
|---|---|---|
| Diag pair under Proton | `DayZDiag_x64.exe` for both roles, the server with `-server` | Through dayz-mcp's `dayz_test_run`, or `sh scripts/tools/dayz-linux/dayz-proton.sh headless start <state> DayZDiag <args>` without it |
| Native server and retail client | The native `DayZServer`, with the retail client under Proton | `linux-native-server.md` (server tree, ports, reading the result) and `linux-headless-client.md` (headless client, the AutoTest mod in `../assets/autotest-mod/`, `dayz-client-test.sh`) |

- A diag client only joins a diag server. On the native `DayZServer` it stops at the modal `0x00020017, Client is using Diag exe while the server is not`, which only a screenshot shows. The diag pair joined and reached the world.
- Under Proton, DayZDiag reaches the main menu as a client, and with `-server` and `-config=`, `-mission=` and `-profiles=` pointing into a Linux server tree it loads the mission and runs the Central Economy.
- It loads a mod from an absolute `-mod=Z:\<linux path>\@Mod` and writes its logs to `-profiles=Z:\<linux path>`. `-filePatching` from an unpacked `-mod=` folder under Proton is not verified.
- Client and server must report the same game version (`sh scripts/tools/dayz-linux/dayz-proton.sh doctor`), or the join fails with `0x00020013`.
- `%LOCALAPPDATA%\DayZ` is `<prefix>/pfx/drive_c/users/steamuser/AppData/Local/DayZ`. Pass `-profiles=<linux dir>` to keep logs where you read them.
- A diag server and client ran from one prefix with each role in its own headless Wayland sway session (`PROTON_ENABLE_WAYLAND=1`, through dayz-mcp). With `dayz-proton.sh headless`, one Wine prefix serves one display at a time, so use two `DAYZ_PROTON_HOME` folders or one shared display (`_shared/linux-proton.md`, "Pitfalls").

## The native server

- Start it without `-filePatching`: with it the 1.30 server never finishes loading the landscape.
- Give a relative `-mission=mpmissions/<name>`. An absolute path leaves it without `init.c`'s `main`, so no player can connect (`_shared/linux-proton.md`, "Pitfalls").
- Name `-mod=` and `-servermod=` relative to the server tree as well, the reverse of the absolute path rule on Windows (`linux-native-server.md`, "Run it headless"). Script iteration on the native server therefore means repacking the PBO, not loose files.
- Removing Community Framework from a tree whose storage was written with it floods the log with `Scripted variables corrupted`. Adding it to storage written without it crashed the server on read on Windows (`CF_ModStorageObject` `OnStoreLoad_CF`, `build-and-storage-traps.md`). The one Linux boot that died after adding it died of a compile error instead (`Unknown type 'CF_Trace'`, `Can't compile "Engine" script module`), not isolated because the trees were rebuilt at the same time; isolate that first by rebuilding with the same storage kept, or copy the storage aside.
- Rotate storage by renaming it with the processes stopped, to a name that does not exist yet. Delete only in a throwaway test tree you built.
- Run one server at a time on a host with limited memory: about 7.5 GB resident each with the Expansion bundle. That is a host limit, not an engine rule.
- List servers with `ps aux | grep "[D]ayZServer"` and kill by process id. The process renames itself to `enfMain`, so `pkill` and `pgrep -x DayZServer` silently match nothing.
- Compare each script module the mod adds files to against a vanilla boot. An unchanged count in such a module is the signal (a PBO outside `addons/`, for example); the counter is only an indicator, and a rise can come from other mods. When an override silently does nothing, put a deliberate syntax error in one of the mod's scripts: a clean boot proves the file is not compiled. Compile errors are tagged `SCRIPT    (E)`, space padded, so grep `SCRIPT.*(E)`.

## dayz-mcp on Linux

Linux host support is in dayz-mcp's main branch. The managed cycle below was measured on its Linux branch before that merge and not measured again on main. `dayz-test.ps1`, dayz-mcp's `install-mcp.ps1`, its native launcher and the approved launcher registry are Windows only.

- `dayz_test_run` runs with `mode=all`, `server` and `client`, with `build=true`, and with `dayz_test_close` and `dayz_test_stop`. The policy's `diag_executable` picks the engine: `<game>/DayZDiag_x64.exe` runs both roles under Proton in headless sway sessions, as on Windows; `DayZServer` is a server only project in rootless podman, and a client launch on it is refused with `client_needs_diag_executable`.
- `build=true` runs dayzmake from `PATH` (`pack` with `pack_only`, otherwise `build --proton-binarize`) and writes `@Mod/Addons/<Mod>.pbo`. Main accepts only the pinned dayzmake 1.0.0 release binary. Only the pack only path was verified, not managed binarizing with assets.
- The Steam session check reads `~/.steam/steam.pid`, read only; dayz-mcp never repairs or restarts Steam on Linux, and a logged out Steam passes the check and fails at the client's Steam start. `steam_session_stale` with a live `steam.pid` means an older Linux build that read `SteamPID` from `registry.vdf`: update to a current main build and restart the daemon. Restarting Steam does not reliably help.
- `dayz_test_close` runs in the right order: the player logs out (`logout_finished: true`) and the server ends with `--- Termination successfully completed ---`. With a player in the world the client then exits with code 3 during teardown, after `Destroying game` and before its termination line, so the result is `graceful: false`, `exit_metrics_valid: false` (2 of 2 runs, cause unknown). Do not read client exit metrics from a Linux run; the server's RPT metrics are complete. A client still on its loading screen closed cleanly. `dayz_test_stop` is a forced kill, as on Windows.
- `dayz_test_foreground` is not ported; a headless game has nothing to bring forward.
- Managed games have no input devices, so `use_state` reads `idle`, never `human`. As on Windows, another session gets `run_protected` with `retry_after_s` until the 600 second abandon timer ends.

### The bridge

- The `@DayZ_MCP` addon works on the native `DayZServer` and on DayZDiag under Proton, client and server. Packed and signed with dayzmake 1.0.0 or later (`dayzmake build addon <out>/addons/DayZ_MCP.pbo`, the prefix taken from `$PBOPREFIX$`), it polled the daemon on `127.0.0.1` at about 1 Hz.
- The daemon and client run on Linux with leases and the `session_*` tools.
- With `mode=all`, `bridge_status` reached `ready`, with both peers' last poll ages set, about 34 seconds after `dayz_test_run` returned. `ready` can come before the join: one client was still on its loading screen then, so wait for `is connected` in the server RPT before spawning at the player.
- A game started by hand polls as `LEGACY_UNBOUND`: reads only, mutations refused as `game_not_ready:reason=legacy_unbound`, and `bridge_status` waits for a client peer. Start the game through `dayz_test_run`.
- A managed client runs in a headless sway session. When the logs show nothing, take a screenshot of it; that is how a modal dialog with code `0x00020017` was found:

  ```sh
  WAYLAND_DISPLAY=$(cat <state>/DayZ_MCP/proton-clients/<session>/wayland-display) grim out.png
  ```

Which bridge tools work in the world on Linux, beyond `bridge_status`, was not checked tool by tool.
