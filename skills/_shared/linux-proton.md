# DayZ modding on Linux: native tools and Proton

Which Windows step of the DayZ skills has a native Linux equivalent, which one runs under Proton and how, and what is not yet checked. Read it when a skill names a DayZ Tools program, `P:\`, PowerShell, `%LOCALAPPDATA%` or `DayZDiag_x64.exe` and the machine runs Linux. Tier 2 rules in `dayz-conventions.md` still apply.

This repo is a Windows workspace: every skill, the `.bat` wrappers and `/dayz-preflight` assume Windows and apply there unchanged. Nothing here is a fact about vanilla game data, so nothing is checked on `P:\`. It is tool, Proton and server behaviour on DayZ, DayZ Server and DayZ Tools 1.30, measured once on one Linux machine with native Steam, Proton Hotfix and GE-Proton. A line that says "not checked" was not run at all. The helper scripts it names are in `scripts/tools/dayz-linux/` ("The helper scripts" below).

## Which route for each step

| Windows step in a skill | On Linux | Status |
|---|---|---|
| Pack and sign a PBO (AddonBuilder, DSSignFile) | `dayzmake build`, `keygen` and `sign` (dayzmake 1.0.0 or later; install below) | Native; no wrapper needed. |
| Binarize models (`.p3d` MLOD to ODOL) | `dayzmake build --proton-binarize`, which runs BI's `binarize.exe` under Proton | A textured cube matched BI's binarize byte for byte ("DayZ Tools under Proton"). |
| Publish to the Workshop (Publisher) | The `workshop` uploader (the steam-workshop-uploader tool) | Native; `scripts/tools/dayz-linux/dayz-mod-pack.sh publish-hint` prints the commands (`skills/dayz-build-pbo/references/dayzmake-linux.md`). |
| Cross-check dayzmake against BI's own tools | `dayz-proton.sh tool AddonBuilder P:\<Mod> <out> -prefix=<Mod>`; `tool DSCreateKey`, `DSSignFile`, `DSCheckSignatures`; `dayz-proton.sh binarize <P-root> <addon> <out> [files]` | Works; use it for comparisons, not for the build. |
| `config.cpp` to `config.bin` (CfgConvert) | `dayzmake rapify`, or `dayz-proton.sh tool CfgConvert -bin -dst <bin> <cpp>` | Both work. |
| PNG or TGA to PAA (ImageToPAA) | `dayzmake img2paa`, or `dayz-proton.sh tool ImageToPAA <in> <out.paa>` | Both work. |
| View a PAA (TexView) | `dayzmake paa2img`, the viewer in `scripts/tools/dayz-3d-viewer/`, or `dayz-proton.sh gui TexView <paa>` | All work. |
| Object Builder | `dayz-proton.sh gui ObjectBuilder [model.p3d]` | Starts and loads a model; editing not checked. |
| Workbench | `dayz-proton.sh gui Workbench` | Starts and compiles its bundled scripts; game config needs `P:\dz` ("The work drive on Linux"). |
| Terrain Builder, the DSUtils GUI, the ImageToPAA GUI | `dayz-proton.sh gui <Tool>` | Not checked. |
| Dedicated server (`DayZServer_x64.exe`) | The native `DayZServer` (Steam app 223350) from a private tree: `find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh` | Native and preferred; `skills/dayz-launch-test/references/linux-native-server.md`. |
| Client (`DayZ_x64.exe`) | The retail client under Proton, paired with the native server: `dayz-client-headless.sh`, `dayz-client-test.sh` | Works; `skills/dayz-launch-test/references/linux-headless-client.md`. |
| `DayZDiag_x64.exe` (client or `-server`) | `dayz-proton.sh headless start <state> DayZDiag <args>` | Both roles run; a diag client joins a diag server and reaches the world ("Pitfalls"). |
| The `P:` drive (WorkDrive, `subst`) | A plain directory, mapped by `dayz-proton.sh init <dir>` | Works ("The work drive on Linux"). |
| Blender model work (Blender, py3d, the model checks) | `apt-get install -y blender`, `pip install opensimplex --break-system-packages`, then `pip install -e scripts/tools/py3d`; py3d, `scripts/tools/dayz-model-preflight` and `scripts/tools/dayz-3d-viewer` are Python and run natively | Install written for Debian based systems; not run. |
| PowerShell scripts (`*.ps1`) | Rewrite the steps in `sh`; `pwsh` exists on Linux, but the scripts call Windows programs, the registry and `subst` | Translate, do not run. |
| `%LOCALAPPDATA%\DayZ` logs | `<prefix>/pfx/drive_c/users/steamuser/AppData/Local/DayZ` ("Pitfalls") | |

Build, sign, binarize and publish with dayzmake and `workshop`; the Linux route is built on them, and AddonBuilder and Publisher are not needed. Use the Proton route to see what BI's own tools produce, for the GUI editors with no native equivalent (Object Builder, TexView, Workbench, Terrain Builder), and for DayZDiag.

## dayzmake, the DayZ fork of armake2

dayzmake is the DayZ fork of armake2, renamed at `v1.0.0`. Use the fork; the original armake2 is built for Arma. Its V3 file hash leaves out `.c` files, while dayzmake includes them. Whether the original armake2 fails on DayZ configs is not checked.

- **Which version.** `v1.0.0` or later is enough to build and sign your own mod. Unpacking any PBO you did not build needs `v2.0.0` or later: `v2.0.0` checks each entry's relative path (`safe_relative_path` and `crosses_symlink` in `src/pbo.rs`) and skips unsafe entries, and `v1.0.0` has no such check (its entry handling at `src/pbo.rs:724` and `:731` to `:733`).
- **How to install.** Take the pinned `v2.0.0` release binary from the dayzmake releases page, or build the `v2.0.0` tag with `cargo install` (needs `libssl-dev`).
- **What the fork adds.** Preprocessor fixes (`#include` directives, nested macro arguments), `$PREFIX$` accepted when building PBOs, `img2paa` and `paa2img`, a `binarize` command, texture and material checks in `build` (`missing-texture`, `missing-material`) and the opt-in `build --proton-binarize`.
- **Inspecting a model.** `dayzmake inspect` shows format and version for MLOD and ODOL, and the LODs, textures, materials, properties and selections only for an editable MLOD (`README.md:130` of dayzmake `v1.0.0`).
- **Telling builds apart.** A binary is the fork when `dayzmake -h` lists `--proton-binarize`. `dayzmake --version` prints `v1.0.0`; builds from before the rename are called `armake2` and print `v0.3.0` whatever their commit.

The fork keeps adding functions only DayZ needs, or needs differently from Arma. Read the release notes before you upgrade a pinned build.

## Why DayZ Tools under Proton needs setup

DayZ (221100), DayZ Server (223350) and DayZ Tools (830640) are separate Steam apps. Proton gives each app its own Wine prefix (`steamapps/compatdata/<appid>`), and nothing crosses between them:

- On Windows the game installer writes `HKLM\SOFTWARE\(WOW6432Node\)Bohemia Interactive\DayZ`, value `main`, set to the game folder, and the tools read it (the Launcher, WorkDrive and Workbench binaries carry that key name). In the tools prefix the key exists but is empty, because the game went into another prefix.
- `P:` is a `subst` drive on Windows, shared by every program. Wine has no `subst`, and a drive letter is a symlink in one prefix's `dosdevices/`, so `P:` exists nowhere until you create it, in each prefix that needs it (tools and game).
- A prefix Steam never launched lacks what Steam does on a first launch: the registry entries of DayZ Tools' `installscript.vdf` (without them TexView stops at "Missing registry entry HKEY_LOCAL_MACHINE/Software\BIStudio\TextureConvert") and the VC++ runtime from `Steamworks Shared/_CommonRedist` (Object Builder does not load without `mfc140.dll`).

`scripts/tools/dayz-linux/dayz-proton.sh init <P-root>` handles all of it in private prefixes under `~/.local/share/dayz-proton`, leaving Steam's own prefixes alone. It replays the install script registry, adds the game `main` key, installs the VC++ runtime, uses up the first .NET start ("Pitfalls"), and links `P:` in the tools and the game prefix. It takes about two minutes, once. `doctor` prints what is installed, the game version of each app, update state, and whether dayzmake (or a fork build from before the rename) is installed and is the right fork.

## How `dayz-proton.sh` guards input and processes

- **User text.** `binarize` and console `tool` never put user text in the `cmd.exe /c` string. Each writes a `.bat` holding every user value in double quotes (`%` doubled, a run of trailing backslashes doubled, `setlocal DisableDelayedExpansion` so `!` stays literal). An argument that is empty or holds a double quote, CR or LF is refused before anything is created, copied, linked, removed or run.
- **State paths.** A headless state path may only contain `A-Z a-z 0-9 / . _ -`. `headless start`, `stop` and `shot` check the path as given and again after `pwd -P` resolves it, before any side effect, and refuse one with a space, backslash, newline, tab, quote, `$` or backtick. A state name with `.` and `-` still starts and stops. The `sway.conf` path is compared literally through awk's `ENVIRON`, not `awk -v`, whose escape handling would mis-compare some paths.
- **Starting.** `headless start` needs `setsid` (one launcher form, no `nohup`). It refuses, and touches nothing, while a launcher or sway of the same state may still run; it looks for one by the pid in `sway.pid` and by scanning `/proc/*/cmdline` for this state's `sway.conf` or launcher form, and an incomplete scan counts as running. Stale `sway.pid` or `sway.cancel` files with no live process behind them are removed, along with `sway.identity`, with one line on stderr.
- **Success.** `start` succeeds only once the recorded pid's `/proc` comm is `sway` with the exact three entry argv `sway -c <state>/sway.conf`; a script named `sway` does not pass. It waits `DAYZ_PROTON_START_WAIT_TENTHS` tenths of a second (default 50) and checks again after the last sleep.
- **Failure.** On failure `start` first writes `sway.cancel`, which the launcher child checks before and just after it writes `sway.pid` (removing its pid and exiting instead of starting sway). Then it signals only its own launcher or that exact sway, waits five tenths of a second for a pid published in that window, and only then deletes its tracking. The marker stays so a slower child still cancels; the next `start` removes it only after proving no launcher of that state is alive, and a successful `start` removes it. So `DAYZ_PROTON_START_WAIT_TENTHS=0` fails cleanly without leaving a sway. After `start` returns, either the recorded sway is tracked with a verified identity or no sway of that state runs.
- **Stopping.** `headless stop` signals only a sway whose recorded `/proc` start time and full argv still match, and then only the wineserver of that session's recorded display, as a pid and start time pair checked again (comm and start time) just before the signal. If the sway is gone or foreign, or the recorded display is empty or unreadable, it signals nothing and says so. `init` stops, by the same pid and start time pairs, the wineservers that were not running when it began, in the prefixes it used; a program someone else starts in those prefixes meanwhile cannot be told apart.
- **Limits.** The identity check and the signal are not atomic, so a pid reused in between can still be signalled; the checks narrow that race but do not close it. The offline tests (`scripts/tools/dayz-linux/test_dayz_proton.py`) cover the `.bat` writing only, not how `cmd.exe`, `binarize.exe` or the console tools parse it, and they do not run real Proton, sway or `cmd.exe`.

## The work drive on Linux

`P:` is just a directory. Pick one (for example `~/dayz/P`), put each addon at `P/<prefix path>` (`P/MyMod/config.cpp` for prefix `MyMod`) and run `dayz-proton.sh init ~/dayz/P`. `winpath` shows the mapping (`P:\MyMod\config.cpp`), and `tool` and `gui` rewrite absolute Linux paths in arguments to `P:\…` inside the root and `Z:\…` elsewhere.

Keep the `P:` root small. Binarize scans the folder above the addon it converts (`-addon=` is the parent of the source folder; `skills/dayz-build-pbo/references/binarize-file-lookup.md`), and from `P:\MyMod` that is the `P:` root. From a `Z:` path it is a Linux directory, possibly your home, and binarize then burns CPU for minutes; scans of `~/.cargo` and of a network mount were seen.

To get vanilla data under `P:\dz` (what WorkDrive's "extract game data" does on Windows), unpack the game's PBOs with `dayzmake unpack` into `P/` at their prefix paths, with dayzmake `v2.0.0` or later. On an older build, check every entry name with `dayzmake inspect` first; the unpacking rules are in `skills/dayz-import-mod/references/extraction-pitfalls.md`. For scripts and configs only, `scripts/tools/dayz-linux/extract-dayz-sources.sh <install> <dir>` writes them with configs derapified in about 90 seconds. Workbench without the extracted data compiles its bundled scripts but logs `No entry 'config.bin/CfgVehicles/…'` for vanilla classes. Whether an extracted `P:\dz` removes those errors is not checked, and neither is a model that references vanilla textures.

### What replaces each `/dayz-preflight` check

`preflight.py` looks for `P:\` and reads the Windows registry, so on Linux it stops at the first check with `[FAIL]  P:\ is NOT mounted`. Measured with Steam and Proton:

| Windows check | Linux equivalent |
|---|---|
| DayZ Tools, DayZ and DayZ Server located | `dayz-proton.sh doctor`. It reads `libraryfolders.vdf` and the app manifests, and prints the game versions and any pending updates. |
| `P:\` mounted | A plain directory recorded by `dayz-proton.sh init <dir>`. `doctor` prints it. |
| `DayZDiag_x64.exe` found | It is in the DayZ folder (Steam app 221100) and runs under Proton. |
| Workshop folder | `<library>/steamapps/workshop/content/221100/<id>` |
| Registry values | They do not exist on the host. `init` writes the values the tools read into its own private prefix. |

`init` is the Linux counterpart of mounting `P:`, and the mounting rule carries over: do not run it unasked. Tell the user what it does (it creates private prefixes under `~/.local/share/dayz-proton` and takes about two minutes) and let them run it. The Object Builder viewer value that `/dayz-preflight` checks (`skills/dayz-preflight/references/object-builder-viewer.md`) lives in the tools prefix's registry on Linux; that check was not run there.

## DayZ Tools under Proton

Each tool was run through `dayz-proton.sh` in a fresh private prefix after `init`:

| Tool | Result | Watch for |
|---|---|---|
| ImageToPAA | PNG to DXT5 PAA in 3 to 6 s; read back by `dayzmake paa2img` and TexView | Paths with spaces work. |
| CfgConvert | `-bin` output decodes with `dayzmake derapify`; a syntax error exits 1 with the message | A missing input exits 0 and writes an empty 26 byte `config.bin`, so check the input exists. |
| DSCreateKey, DSSignFile, DSCheckSignatures | Key pair, `.bisign`, "Signature … is OK" | They print nothing on Proton's console; `tool` runs them through `cmd` with output redirected. |
| AddonBuilder | `-packonly` and full builds (`config.bin`, binarized `.p3d`, `texHeaders.bin`) in 3 to 5 s | Exits 0 on failure; `tool` reads `[ResultCode]` from `DayZ Tools/Bin/Logs/AddonBuilder.rpt` and returns it. |
| binarize (`binarize` subcommand) | MLOD to ODOL, byte for byte the same as AddonBuilder for the tested model, textures resolved | The output version is not checked on its own. |
| TexView | Opens a DXT5 PAA and shows format, size and average colour | |
| Object Builder | Opens a `.p3d` and shows points, faces, LODs and selections | The first start shows BI's licence; run it once on your desktop and answer it yourself. |
| Workbench | Starts, compiles the vanilla script modules from its bundled `dta/`, shows its script authorization prompt | Game config is missing without `P:\dz`. |
| DayZDiag_x64 client | Reaches the main menu in about 20 s | A diag build reports `Error()` as VM exceptions (`crash_*.log`), as on Windows. |
| DayZDiag_x64 `-server` | Loads a mission from a Linux server tree through `Z:` paths, runs the Central Economy, listens on the given UDP port | |

The fork's `--proton-binarize` against BI's binarize run from the `P:` root, on a textured cube with an alpha `_ca.paa`, gave byte for byte the same output once the fork had its texture lookup fix. An older fork build differed in 20 bytes: the face's average colour (`00 00 00 FF` instead of `70 83 83 C8`) and flag bits, which matches the defaults for a texture that was not found. Both builds print `v0.3.0`, so the version string does not identify a pre-rename build. dayzmake `v1.0.0` contains the fix, but the comparison was not repeated with the `v1.0.0` binary, and the ODOL was not loaded in game.

## Pitfalls

- **One display per prefix.** A prefix's wineserver is bound to the display its first program used. A program started later on another display, or after that display is gone (a stopped headless sway, for example), dies with `X Error … BadWindow … X_UnmapWindow`. That is the X11 path; with `PROTON_ENABLE_WAYLAND=1` two sways on one prefix worked. Run one session per prefix and stop the wineserver when it ends: `headless stop` does this, and by hand it is `WINEPREFIX=<prefix>/pfx <proton dir>/files/bin/wineserver -k`.
- **WoW64 mode.** `PROTON_USE_WOW64=1`, the script's default, fixed the tool start and font problems seen. Without it the host showed missing FreeType and empty tool dialogs, and GDI tools inside the Steam Linux Runtime container (`DAYZ_PROTON_RUNTIME=1`) crashed with fontconfig and X errors. Check each installed executable's PE architecture before you call it a 32-bit tool.
- **The first .NET start in a fresh prefix fails.** AddonBuilder crashed (a DXVK error) without WoW64 and hung after its constructor with it; every later start worked. `init` uses up that start.
- **Never `pkill -f <tool>`** from a shell whose command line contains that name, because it kills the shell. Kill by PID, or stop the prefix's wineserver.
- **`pkill` and `pgrep -x DayZServer` never match a running server.** The native server and the game rename their main thread to `enfMain`, so a kill or count by name finds nothing while servers of about 7.5 GB each keep running. List with `ps aux | grep "[D]ayZServer"`, check the arguments (tree, ports) and kill by PID. A server that must outlive an agent's tool call needs `setsid nohup`.
- **A Proton game process is a host process with a padded command line.** Pressure-vessel does not hide `DayZDiag_x64.exe`: its `comm` is `enfMain`, `argv[0]` is the `Z:\…` path and its parent is `pv-adverb`. Wine leaves the rewritten argv padded with NULs, which psutil reads as empty arguments (222 of them after one DayZDiag command line), so a tool that matches a process by its arguments must drop empty ones first.
- **A diag client only joins a diag server.** `DayZDiag_x64.exe` on the native `DayZServer` stops at the modal `CONNECTING FAILED (0x00020017): Client is using Diag exe while the server is not` after the client has loaded. The log shows no error, only the screen does, and the server never sees a player. Pair them: both `DayZDiag` (`-server` under Proton, with `allowFilePatching = 1` in `serverDZ.cfg`), or the retail `DayZ_x64.exe` with the native server (`skills/dayz-launch-test/references/linux-headless-client.md`). A diag pair run from one prefix, each role in its own headless sway with `PROTON_ENABLE_WAYLAND=1`, joined: the server RPT logs `Player "<name>" … is connected` and the player stands in the world.
- **An absolute `-mission` on the native server boots without a mission.** `DayZServer` 1.30 with `-mission=/abs/path` loads the mission's modules, but `init.c`'s `main` does not run. The RPT says `Mission script has no main function, player connect will stay disabled!`, there are no `[CE][Hive]` lines, and the mod's scripts still run, so it looks healthy. Name it relative to the working directory, `-mission=mpmissions/<name>`. `DayZDiag -server` under Proton takes an absolute `Z:\…` path.
- **Absolute `-mod=` and `-servermod=` paths mount nothing on the native server.** The engine probes the folder, loads no PBO from it and prints no error; the server starts and the mod is simply absent. Give mod paths relative to the server tree (symlinks or `../` work). This is the reverse of the Windows rule in `skills/dayz-launch-test/references/windows-build-and-mount.md` ("Mod paths must be absolute"); the run is in `skills/dayz-launch-test/references/linux-native-server.md`, "Run it headless". `-config` and `-profiles` take absolute paths. `DayZDiag` 1.30 under GE-Proton loads an absolute `-mod=Z:\…` and writes its logs into an absolute `-profiles=Z:\…`, so mods need not be linked into the Steam install for the diag client.
- **Which PID is Steam.** Read `~/.steam/steam.pid`, the file `steam.sh` itself checks. `SteamPID` in `~/.steam/registry.vdf` can name a start-up process that is already gone, two numbers below the live `ubuntu12_32/steam`.
- **Stopping a game in order.** `DayZServer` handles SIGTERM as an orderly shutdown, also as a container's PID 1 (about 11.5 s; the RPT ends `--- Termination successfully completed ---`). So does `DayZDiag -server` under Proton. Closing a headless sway view closes the game too (`swaymsg '[con_id=N] kill'`); a `DayZDiag` client in the world then logs out and exits with code 3 before its termination line (two of two runs, cause unknown), so its RPT exit metrics are incomplete.
- **Client and server versions must match**, or the client is refused with `0x00020013 Client is a newer build than the server`. Steam `buildid`s differ per app by design, so compare the game version (`dayz-proton.sh doctor` prints it) and check `StateFlags` 4 (fully updated) in both `appmanifest_*.acf` files.
- **Logs.** A Proton program's `%LOCALAPPDATA%` is `<prefix>/pfx/drive_c/users/steamuser/AppData/Local`. The Steam client's game prefix is `steamapps/compatdata/221100` and the script's is `~/.local/share/dayz-proton/game`. Pass `-profiles=<linux dir>` (rewritten to `Z:\…`) to put the logs where you want them. DayZ Tools write their own logs into `DayZ Tools/Bin/Logs`, as on Windows.
- **`-filePatching` hangs the native server.** On `DayZServer` 1.30, natively and in rootless podman, after the last building type loads the main thread busy-polls `/proc/self/statm` and `/proc/meminfo` and the landscape never finishes (90 s natively, over four minutes in the container); without the flag it loads in about 10 s. Start the Linux server without `-filePatching`. `DayZDiag_x64.exe -server -filePatching` under Proton does not hang: it loaded the mission and took a player with a packed mod. Loose files from an unpacked `-mod=` folder are not checked.
- **A read-only mod folder is skipped silently.** With a mod mounted read-only into a container (`podman -v <mod>:<mod>:ro`), `DayZServer` 1.30 never logs `Adding package … @Mod` and runs without it; from an overlay mount (`:O`) the same folder loads. Give the server a writable view of each mod folder; an overlay keeps the build itself untouched.
- **Case sensitivity.** Linux file systems are case sensitive. Wine's `Z:` hides that from the tools, but native tools (dayzmake, the Linux server reading loose files) do not, so keep path case in `config.cpp`, `.rvmat` and model texture references identical to the files on disk.

## Not covered

Terrain Builder, Publisher, BinMake and the GUI front ends were not started. Object Builder was opened, not used to edit. An ODOL made under Proton was not loaded in game.

## The helper scripts

All are in `scripts/tools/dayz-linux/`. The shell scripts run on Linux only (POSIX `sh` or `bash`, `/proc`, Proton). The two Python scripts also run on Windows, where the vanilla scripts folder on the work drive is already a tree `build-api-index.py` can read: `python scripts/tools/dayz-linux/build-api-index.py`, given that folder and an output folder, writes the index in about 6 seconds (6,786 classes, 431 enums), and `python scripts/tools/dayz-linux/dayz-api.py chain PlayerBase` then prints the base class chain. On Windows the Tier 2 search rule (Grep, then the `dayz-rag` search) stays the first choice; the index is for a machine with no work drive, or for one answer that needs every inherited member.

| Script | What it does |
|---|---|
| `dayz-proton.sh` | `init`, `doctor`, `winpath`, `tool`, `gui`, `binarize` and `headless start`, `shot` and `stop` for DayZ Tools and `DayZDiag` under Proton, in private prefixes. |
| `dayz-mod-pack.sh` | Workshop project helper on dayzmake: `init`, `keygen`, `build`, `check`, `publish-hint`. It never uploads; publishing stays a manual step. |
| `dayz-client-headless.sh` | Runs the retail client in a headless sway session: `start`, `shot`, `stop`, `status`. One client at a time. |
| `dayz-client-test.sh` | One automated client and server test: starts the native server and the headless client, waits for the mod's final test line, collects logs and a screenshot, stops both. |
| `find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh` | Find the native server install, build a private server tree, pick free ports. |
| `extract-dayz-sources.sh` | Unpacks the scripts and derapified configs of an install or a mod. |
| `build-api-index.py`, `dayz-api.py` | Build a compressed script API index (`dayz-api.txt.xz`, or `mod-<name>.txt.xz` with `--mod`) and query it: `class`, `find`, `sub`, `enum`, `src`, `chain`, `defines`. The index holds Bohemia's and mod authors' declarations, so build it locally (default folder `~/.cache/dayz-api`, or `DAYZ_API_DIR`) and never commit it. |
