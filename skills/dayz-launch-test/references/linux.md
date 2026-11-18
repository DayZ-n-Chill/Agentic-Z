# Testing on a Linux host

What changes for this skill when the host runs Linux: which engine runs where, how mods and paths are named, and the rules that fail quietly when missed. The other files in this folder describe Windows and stay valid there. The Proton setup, the tool matrix and its pitfalls are in `_shared/linux-proton.md`; the native server has `linux-native-server.md` and the headless client has `linux-headless-client.md`.

All of it is measured behaviour of the Linux server and Proton on DayZ 1.30. None of it is vanilla, so it is not checked on `P:\`.

## Two routes

| Route | Engine | How to start it |
|---|---|---|
| Diag pair under Proton | `DayZDiag_x64.exe` for both roles, the server with `-server` | `sh scripts/tools/dayz-linux/dayz-proton.sh headless start <state> DayZDiag <args>` |
| Native server and retail client | The native `DayZServer`, with the retail client under Proton | `linux-native-server.md` (server tree, ports, reading the result) and `linux-headless-client.md` (headless client, the AutoTest mod in `../assets/autotest-mod/`, `dayz-client-test.sh`) |

- A diag client only joins a diag server. On the native `DayZServer` it stops at the modal `0x00020017, Client is using Diag exe while the server is not`, which only a screenshot shows. The diag pair joined and reached the world.
- Under Proton, DayZDiag reaches the main menu as a client, and with `-server` and `-config=`, `-mission=` and `-profiles=` pointing into a Linux server tree it loads the mission and runs the Central Economy.
- It loads a mod from an absolute `-mod=Z:\<linux path>\@Mod` and writes its logs to `-profiles=Z:\<linux path>`. `-filePatching` from an unpacked `-mod=` folder under Proton is not verified.
- Client and server must report the same game version (`sh scripts/tools/dayz-linux/dayz-proton.sh doctor`), or the join fails with `0x00020013`.
- `%LOCALAPPDATA%\DayZ` is `<prefix>/pfx/drive_c/users/steamuser/AppData/Local/DayZ`. Pass `-profiles=<linux dir>` to keep logs where you read them.
- A diag server and client ran from one prefix with each role in its own headless Wayland sway session (`PROTON_ENABLE_WAYLAND=1`). With `dayz-proton.sh headless`, one Wine prefix serves one display at a time, so use two `DAYZ_PROTON_HOME` folders or one shared display (`_shared/linux-proton.md`, "Pitfalls").

## The native server

- Start it without `-filePatching`: with it the 1.30 server never finishes loading the landscape.
- Give a relative `-mission=mpmissions/<name>`. An absolute path leaves it without `init.c`'s `main`, so no player can connect (`_shared/linux-proton.md`, "Pitfalls").
- Name `-mod=` and `-servermod=` relative to the server tree as well, the reverse of the absolute path rule on Windows (`linux-native-server.md`, "Run it headless"). Script iteration on the native server therefore means repacking the PBO, not loose files.
- Removing Community Framework from a tree whose storage was written with it floods the log with `Scripted variables corrupted`. Adding it to storage written without it crashed the server on read on Windows (`CF_ModStorageObject` `OnStoreLoad_CF`, `build-and-storage-traps.md`). The one Linux boot that died after adding it died of a compile error instead (`Unknown type 'CF_Trace'`, `Can't compile "Engine" script module`), not isolated because the trees were rebuilt at the same time; isolate that first by rebuilding with the same storage kept, or copy the storage aside.
- Rotate storage by renaming it with the processes stopped, to a name that does not exist yet. Delete only in a throwaway test tree you built.
- Run one server at a time on a host with limited memory: about 7.5 GB resident each with the Expansion bundle. That is a host limit, not an engine rule.
- List servers with `ps aux | grep "[D]ayZServer"` and kill by process id. The process renames itself to `enfMain`, so `pkill` and `pgrep -x DayZServer` silently match nothing.
- Compare each script module the mod adds files to against a vanilla boot. An unchanged count in such a module is the signal (a PBO outside `addons/`, for example); the counter is only an indicator, and a rise can come from other mods. When an override silently does nothing, put a deliberate syntax error in one of the mod's scripts: a clean boot proves the file is not compiled. Compile errors are tagged `SCRIPT    (E)`, space padded, so grep `SCRIPT.*(E)`.

## Diag pair facts

- A diag pair under Proton closes in order when the player logs out first and the server ends with `--- Termination successfully completed ---`. With a player in the world the client then exits with code 3 during teardown, after `Destroying game` and before its termination line (2 of 2 runs, cause unknown). Do not read client exit metrics from a Linux run; the server's RPT metrics are complete. A client still on its loading screen closed cleanly.
- The Steam session on Linux is `~/.steam/steam.pid`. A logged out Steam still writes it, and the client then fails at its Steam start; restarting Steam does not reliably help.
- Packing a test PBO with dayzmake 1.0.0 or later (`dayzmake build addon <out>/addons/<Mod>.pbo`, the prefix taken from `$PBOPREFIX$`) loads on the native `DayZServer` and on DayZDiag under Proton, client and server. Only the pack only path was checked, not binarizing with assets.
- Wait for `is connected` in the server RPT before spawning at the player: the server can be ready while the client still shows its loading screen.
- A client in a headless sway session shows nothing in its logs when a modal dialog stops it. Take a screenshot of its display; that is how a modal dialog with code `0x00020017` was found:

  ```sh
  WAYLAND_DISPLAY=<the session's wayland display> grim out.png
  ```
