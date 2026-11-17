# DayZ modding on Linux: native tools and Proton

Tier 3 pack for anyone running the DayZ skills on Linux. Tier 2 rules in `dayz-conventions.md` still apply.

This repo is a Windows workspace: every skill, the `.bat` wrappers and `/dayz-preflight` assume Windows,
and on Windows they apply unchanged. This note is the Linux supplement the skills point to: which Windows
step has a native Linux equivalent, which one runs under Proton and how, and what was not checked. Read it
when a skill names a DayZ Tools program, `P:\`, PowerShell, `%LOCALAPPDATA%` or `DayZDiag_x64.exe` and the
machine is Linux. The helper scripts it names are in `skills/_shared/scripts/` (table in section 7).

Not yet checked on `P:\`: nothing here is a fact about vanilla game data. It is measured tool, Proton and
server behaviour on the builds named below, and the measurements have not been repeated.

Measured on 2026-11-03 (server pitfalls in section 5 on 2026-11-04): Debian testing, Steam native, Proton Hotfix and GE-Proton11-1, DayZ and
DayZ Server 1.30.164289, DayZ Tools build 26405911 (binarize 1.30.164289.70). Everything below marked
**not verified** was not run.

Evidence status: the 2026-11-03..06 measurements in this note (the tool matrix, the textured-cube
comparison at `7dcb3cf`, the managed cycle) were made once, on Debian testing; their logs are not in
this repo and they have not been reproduced on a second machine. Statements labelled "not checked"
below were not measured at all.

## 1. Pick the route per step

| Windows step in a skill | On Linux | Status |
|---|---|---|
| Pack / sign a PBO (AddonBuilder, DSSignFile) | `dayzmake build` / `keygen` / `sign` (dayzmake >= 1.0.0; install below) | native; no external wrapper required |
| Binarize models (`.p3d` MLOD → ODOL) | `dayzmake build --proton-binarize` (invokes BI binarize.exe under Proton) | recorded textured-cube comparison at dayzmake commit `7dcb3cf`, which `v1.0.0` contains (section 4) |
| Publish to the Workshop (Publisher) | `workshop` uploader (the steam-workshop-uploader tool) | native route; `skills/_shared/scripts/dayz-mod-pack.sh publish-hint` prints the commands (`skills/dayz-build-pbo/references/dayzmake-linux.md`) |
| Cross-check dayzmake against BI's own tools | `skills/_shared/scripts/dayz-proton.sh tool AddonBuilder P:\<Mod> <out> -prefix=<Mod>`; `tool DSCreateKey` / `DSSignFile` / `DSCheckSignatures`; `dayz-proton.sh binarize <P-root> <addon> <out> [files]` | works (section 4); for comparisons, not the build |
| `config.cpp` → `config.bin` (CfgConvert) | `dayzmake rapify`, or `dayz-proton.sh tool CfgConvert -bin -dst <bin> <cpp>` | both work |
| PNG/TGA → PAA (ImageToPAA) | `dayzmake img2paa`, or `dayz-proton.sh tool ImageToPAA <in> <out.paa>` | both work |
| View a PAA (TexView) | `dayzmake paa2img`, the viewer tool in `scripts/tools/dayz-3d-viewer/`, or `dayz-proton.sh gui TexView <paa>` | all work |
| Object Builder | `dayz-proton.sh gui ObjectBuilder [model.p3d]` | starts, loads a model; editing not exercised |
| Workbench | `dayz-proton.sh gui Workbench` | starts and compiles the bundled scripts; game config needs `P:\dz` (section 3) |
| Terrain Builder, DSUtils GUI, ImageToPAA GUI | `dayz-proton.sh gui <Tool>` | **not verified** |
| Dedicated server (`DayZServer_x64.exe`) | native `DayZServer` (Steam app 223350) from a private tree: `skills/_shared/scripts/find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh` | native, preferred; `skills/dayz-test-ingame/references/linux-native-server.md` |
| Client (`DayZ_x64.exe`) | retail client under Proton, paired with the native server: `skills/_shared/scripts/dayz-client-headless.sh`, `dayz-client-test.sh` | works; `skills/dayz-test-ingame/references/linux-headless-client.md` |
| `DayZDiag_x64.exe` (client or `-server`) | `dayz-proton.sh headless start <state> DayZDiag <args>`, or managed through dayz-mcp `main` (Linux host support since 2026-11-14; last row) | both roles run; a diag client joins a diag server and reaches the world (section 5, pairing) |
| `P:` drive (WorkDrive, `subst`) | a plain directory, mapped by `dayz-proton.sh init <dir>` | works (section 3) |
| PowerShell scripts (`*.ps1`) | rewrite the steps in sh; `pwsh` exists on Linux but the scripts call Windows programs, the registry and `subst` | translate, do not run |
| `%LOCALAPPDATA%\DayZ` logs | `<prefix>/pfx/drive_c/users/steamuser/AppData/Local/DayZ` (section 5) | |
| dayz-mcp in-game bridge | Linux host support is in dayz-mcp `main` since 2026-11-14: `dayz_test_run` (`mode=all/server/client`, `build=true`), `dayz_test_close`, `dayz_test_stop`, bound polls | observations here were measured on its `linux-port` branch on 2026-11-06, before that merge (not re-measured on `main`); managed binarization with assets unverified; section 9 of `skills/_shared/knowledge/linux-proton-findings.md` |

Build, sign, binarize and publish with dayzmake and `workshop`; they are what the Linux route
is built on. AddonBuilder and Publisher are not needed on Linux. Use the Proton route when the question
is "what do BI's own tools produce", or for the GUI editors that have no native equivalent (Object
Builder, TexView, Workbench, Terrain Builder) and for DayZDiag.

**dayzmake** is the DayZ fork of armake2, renamed at `v1.0.0`. Use `v2.0.0` or later (`v1.0.0` or later is fine for building and signing your own mod, whereas unpacking any PBO you did not build yourself requires >= `v2.0.0` — tag `v2.0.0`, commit `f31056ae`, where `src/pbo.rs` `safe_relative_path` and `crosses_symlink` validate relative paths and skip unsafe entries; `v1.0.0` `src/pbo.rs:724,731-733` has no containment check):
install the pinned `v2.0.0` release binary from the dayzmake project's releases page
(note that dayz-mcp's managed `build=true` path pins the `v1.0.0` release binary for building),
or build the `v2.0.0` tag from its source with `cargo install` (needs `libssl-dev`). The fork
is required, not a preference, and it is moving away from the original armake2 on purpose: it implements more and
more functions that only DayZ needs, or that DayZ needs differently from Arma. The original armake2
is built for Arma: the V3 file hash omits `.c` files in the original armake2 and includes them in dayzmake v1.0.0.
Not checked here: the original armake2 fails on DayZ configs. What the fork adds: preprocessor grammar
fixes (`#include` directives, nested macro arguments), `$PREFIX$` accepted when
building PBOs, `img2paa` / `paa2img`, a `binarize` command, texture and material checks in `build` (`missing-texture`,
`missing-material`) and opt-in `build --proton-binarize` (models through BI's binarize under Proton).
For models, `dayzmake inspect` shows format and version for MLOD and ODOL, and LODs, textures, materials, properties and selections only for an editable MLOD (dayzmake v1.0.0 `README.md:130`).
Expect new DayZ-only behaviour in later releases; read the release notes before upgrading a pinned build. An installed binary is the fork when `dayzmake -h`
lists `--proton-binarize`; `dayzmake --version` prints `v1.0.0`, while builds from before the rename
are called `armake2` and print `v0.3.0` whatever their commit.

## 2. The cross-app quirk: why DayZ Tools under Proton needs setup

DayZ (221100), DayZ Server (223350) and DayZ Tools (830640) are separate Steam apps. Proton gives each
app its own Wine prefix (`steamapps/compatdata/<appid>`), and nothing crosses between them:

- On Windows the game installer writes `HKLM\SOFTWARE\(WOW6432Node\)Bohemia Interactive\DayZ`, value
  `main` = game folder, and the tools read it (the Launcher, WorkDrive and Workbench binaries carry
  that key name). In the tools prefix that key exists but is empty: the game was installed into
  another prefix.
- `P:` is a `subst` drive on Windows, shared by every program. Wine has no `subst`, and a drive
  letter is a symlink in one prefix's `dosdevices/`, so `P:` exists nowhere unless you create it, and
  it must be created in each prefix that needs it (tools and game).
- A prefix Steam never launched misses what Steam does on a first launch: the registry entries of
  DayZ Tools' `installscript.vdf` (TexView stops at "Missing registry entry
  HKEY_LOCAL_MACHINE/Software\BIStudio\TextureConvert" without them) and the VC++ runtime from
  `Steamworks Shared/_CommonRedist` (Object Builder does not load without `mfc140.dll`).

`skills/_shared/scripts/dayz-proton.sh init <P-root>` handles all of it in private prefixes under
`~/.local/share/dayz-proton` (Steam's own prefixes are not touched): it replays the install-script
registry, adds the game `main` key, installs the VC++ runtime, spends the first .NET start (below),
and links `P:` in the tools and the game prefix. It takes about two minutes once. `doctor` prints what
is installed, the game version of each app, update state and whether dayzmake (or a pre-rename `armake2` fork build) is installed and the right fork.

`dayz-proton.sh binarize` and console `dayz-proton.sh tool` never put user text in the `cmd.exe /c`
string: each writes a `.bat` holding every user value double-quoted (`%` doubled, a run of trailing
backslashes doubled, `setlocal DisableDelayedExpansion` so `!` stays literal), and refuses an argument
with a double quote, CR, LF or an empty argument before anything is created, copied, linked, removed
or run. The offline tests (`skills/_shared/scripts/test_dayz_proton.py`) prove that .bat serialization only, not how `cmd.exe`, binarize.exe or the console tools parse it (that parsing is not checked).
`headless stop` signals only a sway whose recorded /proc start time and full argv still match, and then only the wineserver serving that session's recorded display, as a pid:starttime pair re-checked (/proc comm and start time) just before the signal; if the sway is gone or foreign it signals nothing and says so.
A headless state path may only contain `A-Z a-z 0-9 / . _ -`: `headless start`, `stop` and
`shot` check the path as given and once `pwd -P` resolved, before any side effect, and refuse
one with (for example) a space, backslash, newline, tab, quote, `$` or backtick. `headless
start` requires `setsid` (one launcher form, no `nohup`), refuses while a launcher or sway of
the same state may still be running (it finds a launcher from the pid in `sway.pid` or by
scanning `/proc/*/cmdline` for this state's `sway.conf` or launcher form, and an incomplete
scan counts as running) and touches nothing in that case; if `sway.pid`/`sway.cancel` exist
but no such process is alive, they are stale and `start` removes `sway.pid`, `sway.identity`
and `sway.cancel` with one stderr line before continuing. It succeeds only once
the recorded pid's /proc comm is `sway` with the exact three-entry `sway -c <state>/sway.conf`
argv (a script named `sway` does not pass; the wait is `DAYZ_PROTON_START_WAIT_TENTHS` tenths of
a second, default 50, checked again after the last sleep), and signals no wineserver at all when
the recorded display is empty or unreadable. After `start` returns, success or failure, either
the recorded sway is tracked with a verified identity or no sway of that state is running: on
failure it first writes `sway.cancel`, which the launcher child checks before writing `sway.pid`
and again just after (removing its pid and exiting instead of `exec`ing sway), then signals only
its own launcher or that exact sway, waits five tenths of a second re-checking for a pid
published in that window, and only then deletes its tracking. The marker stays after a failure
so a slower child still cancels; the next `start` removes it only after proving no launcher of
this state is alive, and a successful `start` removes it, so `DAYZ_PROTON_START_WAIT_TENTHS=0`
fails cleanly without leaving a sway.
The `sway.conf` path is compared literally through awk's `ENVIRON`, not `awk -v` (whose escape
handling would mis-compare some state paths), and an allowed state name with `.` and `-` still
starts and stops. `init` stops the
wineservers that were not running when `init` began, in the prefixes it used, by the same
pid:starttime pairs; a program someone else starts in those prefixes meanwhile cannot be
told apart. These stops reduce but do not eliminate the check-then-signal
race: the identity check and the signal are not atomic, and a pid reused in between can
still be signalled. Real Proton, sway and `cmd.exe` were not run by these offline tests.

## 3. `P:` on Linux

`P:` is just a directory. Pick one (for example `~/dayz/P`), put each addon at `P/<prefix path>`
(`P/MyMod/config.cpp` for prefix `MyMod`) and run `dayz-proton.sh init ~/dayz/P`. `winpath` shows the
mapping (`P:\MyMod\config.cpp`), and `tool`/`gui` rewrite absolute Linux paths in arguments to `P:\…`
inside the root and `Z:\…` elsewhere.

Keep the `P:` root small. Binarize scans the folder above the addon it converts (`-addon=` is the
parent of the source folder; `skills/dayz-build-pbo/references/addonbuilder-rules.md` documents this); from `P:\MyMod` that is the `P:` root.
From a `Z:` path it is a Linux directory, possibly your home, and binarize then burns CPU for minutes
(scans of `~/.cargo` and of a network mount were recorded).

Vanilla data under `P:\dz` (what WorkDrive's "extract game data" does on Windows): unpack the game's
PBOs with `dayzmake unpack` into `P/` at their prefix paths using dayzmake >= `v2.0.0` (tag `v2.0.0`, commit `f31056ae`, `src/pbo.rs` `safe_relative_path`/`crosses_symlink`; `v1.0.0` `src/pbo.rs:724,731-733` has no entry-name containment — on < `v2.0.0` check every entry name with `dayzmake inspect` first; the `dayz-pbo-reverse-engineering` skill has the unpacking rules). For scripts and configs
only, `skills/_shared/scripts/extract-dayz-sources.sh <install> <dir>` (configs derapified; about 90 s). Workbench without the
extracted data compiled its bundled scripts but logged `No entry 'config.bin/CfgVehicles/…'`
for vanilla classes. Whether an extracted `P:\dz` removes those errors is **not verified**,
and neither is a model that references vanilla textures.

## 4. DayZ Tools under Proton: what was measured

All through `dayz-proton.sh` in a fresh private prefix after `init`.

| Tool | Result | Notes |
|---|---|---|
| ImageToPAA | PNG → DXT5 PAA in 3–6 s; read back by `armake2 paa2img` (now `dayzmake paa2img`) and TexView | paths with spaces work |
| CfgConvert | `-bin` output decodes with `armake2 derapify` (now `dayzmake derapify`); a syntax error exits 1 with the message | a **missing input exits 0** and writes a 26-byte empty `config.bin`: check the input exists |
| DSCreateKey / DSSignFile / DSCheckSignatures | key pair, `.bisign`, "Signature … is OK" | they print nothing on Proton's console; `tool` runs them through `cmd` with output redirected |
| AddonBuilder | `-packonly` and full builds (config.bin, binarized `.p3d`, `texHeaders.bin`), 3–5 s | exits 0 on failure; `tool` reads `[ResultCode]` from `DayZ Tools/Bin/Logs/AddonBuilder.rpt` and returns it |
| binarize (`binarize` subcommand) | MLOD → ODOL; output version not independently verified | recorded byte match to AddonBuilder for the tested model; textures resolved |
| TexView | opens a DXT5 PAA, shows format, size, average colour | |
| Object Builder | opens a `.p3d` (points, faces, LOD, selections shown) | first start shows BI's licence: run it once on your desktop and answer it yourself |
| Workbench | starts, compiles the vanilla script modules from its bundled `dta/`, shows its script-authorization prompt | game config missing without `P:\dz` |
| DayZDiag_x64 client | main menu, v1.30.164289.70, ~20 s | a diag build reports `Error()` as VM exceptions (`crash_*.log`), as on Windows |
| DayZDiag_x64 `-server` | mission loaded from a Linux server tree via `Z:` paths, Central Economy ran, listening on the given UDP port | |

The fork's `--proton-binarize` (measured under its old name armake2) against BI's binarize run from the `P:` root (same textured cube, alpha
`_ca.paa`): the output was **byte-identical** from fork commit
`7dcb3cfbd34e62e7b89e8ffd5ea27b603a092daa` (short `7dcb3cf`, including fix `0a0ce3b`).
The older tested fork build `782396e` differed in 20 bytes: the face's average colour
(`00 00 00 FF` instead of `70 83 83 C8`) and flag bits, consistent with texture-not-found defaults.
`armake2 --version` prints `v0.3.0` for both; the version string does not identify the tested build.
dayzmake `v1.0.0` (tag commit `2279ac6`) contains `7dcb3cf` and `0a0ce3b`; the comparison was not
repeated with the `v1.0.0` binary. This is a record of the comparison, not a new measurement or an in-game validation of the ODOL.

## 5. Pitfalls

- **One display per prefix.** A prefix's wineserver is bound to the display its first program used.
  A program started later on another display — or after that display is gone, e.g. a stopped headless
  sway — dies with `X Error … BadWindow … X_UnmapWindow`. (That is the X11 path. With
  `PROTON_ENABLE_WAYLAND=1` two sways on one prefix worked, measured 2026-11-06.) Run one session per prefix, and stop the
  wineserver when it ends (`headless stop` does, identity-checked as in section 2; by hand:
  `WINEPREFIX=<prefix>/pfx <proton dir>/files/bin/wineserver -k`).
- **WoW64 workaround on the tested host.** `PROTON_USE_WOW64=1` (the script's default)
  fixed the reported tool-startup/font issues. Without it, the host showed missing FreeType
  and empty tool dialogs; GDI tools inside the Steam Linux Runtime container
  (`DAYZ_PROTON_RUNTIME=1`) crashed on this host (fontconfig/X errors). Check each installed
  executable's PE architecture before describing it as a 32-bit tool.
- **The first .NET start in a fresh prefix fails**: AddonBuilder crashed (DXVK error) without WoW64
  and hung after its constructor with it; every later start worked. `init` spends that start.
- **Never `pkill -f <tool>`** from a shell whose command line contains that name: it kills the shell.
  Kill by PID, or stop the prefix's wineserver.
- **`pkill`/`pgrep -x DayZServer` never match a running server.** The native server and the game rename their main
  thread to `enfMain`, so a name-based kill or count silently finds nothing while servers of about 7.5 GB each keep
  running (measured on 1.30.164289). List with `ps aux | grep "[D]ayZServer"`, check the arguments (tree, ports) and kill
  by PID; a server that must outlive an agent's tool call needs `setsid nohup`.
- **A diag client only joins a diag server.** `DayZDiag_x64.exe` on the native `DayZServer` stops at the
  modal `CONNECTING FAILED (0x00020017): Client is using Diag exe while the server is not`, after the client
  has loaded; the log shows no error, only the screen does, and the server never sees a player. Pair them: both
  `DayZDiag` (`-server` under Proton, with `allowFilePatching = 1` in `serverDZ.cfg`), or the retail `DayZ_x64.exe`
  with the native server (`skills/dayz-test-ingame/references/linux-headless-client.md`). Measured 2026-11-06, 1.30.164289.70: the diag pair joined,
  `Player "Dev" … is connected` in the server RPT and the player in the world, from one prefix with each role
  in its own headless sway (`PROTON_ENABLE_WAYLAND=1`).
- **An absolute `-mission` on the native server boots without a mission.** `DayZServer` 1.30 with
  `-mission=/abs/path` loads the mission's modules, but `init.c`'s `main` does not run: `Mission script has no
  main function, player connect will stay disabled!` in the RPT, no `[CE][Hive]` lines, and the mod's scripts and
  bridge still work, so it looks healthy. Name it relative to the working directory, `-mission=mpmissions/<name>`
  (measured 2026-11-06). `DayZDiag -server` under Proton takes an absolute `Z:\…` path.
- **Absolute `-mod=` / `-servermod=` paths mount nothing on the native server.** The engine probes the folder,
  loads no PBO from it and prints no error; the server starts and the mod is simply absent. Give mod paths relative
  to the server tree (symlinks or `../` work). This is the reverse of the Windows rule in
  `skills/dayz-test-ingame/references/windows-launch-cycle.md` ("MOD PATHS MUST BE ABSOLUTE"); evidence: `skills/dayz-test-ingame/references/linux-native-server.md`, section 3.
  `-config` and `-profiles` take absolute paths; `DayZDiag` under Proton loads an absolute `-mod=Z:\…` (same file).
- **Which PID is Steam**: `~/.steam/steam.pid`, the file `steam.sh` itself checks. `SteamPID` in
  `~/.steam/registry.vdf` can name a start-up process that is already gone (measured 2026-11-06: `SteamPID`
  20624, no such process, `steam.pid` 20622, the live `ubuntu12_32/steam`).
- **Stopping a game in order**: `DayZServer` handles SIGTERM as an orderly shutdown, also as a container's PID 1
  (11.5 s, RPT ends `--- Termination successfully completed ---`, measured 2026-11-06). So does
  `DayZDiag -server` under Proton on SIGTERM. A headless sway view closes the game too:
  `swaymsg '[con_id=N] kill'`; a `DayZDiag` client in the world then logs out and exits with code 3 before its
  termination line (2 of 2 runs, cause unknown), so its RPT exit metrics are not complete.
- **Client and server versions must match**, or the client is refused with `0x00020013 Client is a
  newer build than the server`. Steam `buildid`s differ per app by design; compare the game version
  (`dayz-proton.sh doctor` prints it) and check `StateFlags` 4 (fully updated) in both
  `appmanifest_*.acf`.
- **Logs**: a Proton program's `%LOCALAPPDATA%` is
  `<prefix>/pfx/drive_c/users/steamuser/AppData/Local` (the Steam client's prefix is
  `steamapps/compatdata/221100`, the script's game prefix `~/.local/share/dayz-proton/game`); pass
  `-profiles=<linux dir>` (rewritten to `Z:\…`) to get them where you want. DayZ Tools write their own
  logs into `DayZ Tools/Bin/Logs`, as on Windows.
- **`-filePatching` hangs the native server.** Measured 2026-11-04 on `DayZServer` 1.30, natively and
  in rootless podman: after the last building type loads, the main thread busy-polls
  `/proc/self/statm` and `/proc/meminfo` and the landscape never finishes (90 s natively, over 4 minutes
  in the container); without the flag it loads in about 10 s. Start the Linux server without
  `-filePatching`. `DayZDiag_x64.exe -server -filePatching` under Proton does not hang: it loaded the mission
  and took a player (measured 2026-11-06, with a packed mod; loose files from an unpacked `-mod=` folder were
  **not verified**).
- **A read-only mod folder is skipped silently.** With a mod mounted read-only into a container
  (`podman -v <mod>:<mod>:ro`) `DayZServer` 1.30 never logs `Adding package … @Mod` and runs without it;
  from an overlay mount (`:O`) the same folder loads. Give the server a writable view of each mod
  folder (an overlay keeps the build itself untouched).
- **Case sensitivity**: Linux file systems are case-sensitive and Wine's `Z:` hides that from the
  tools, but native tools (dayzmake, the Linux server reading loose files) do not. Keep path case in
  `config.cpp`, `.rvmat` and model texture references identical to the files on disk.

## 6. What this note does not cover

Terrain Builder, Publisher, BinMake and the GUI front-ends were not started. Object Builder was
opened, not used to edit. An ODOL produced under Proton was not loaded in game here.

## 7. The helper scripts

All are in `skills/_shared/scripts/`. The shell scripts run on Linux only (POSIX `sh` or `bash`, `/proc`,
Proton). The two Python scripts also run on Windows, where the vanilla scripts folder on the work drive is
already a tree `build-api-index.py` can read: on 2026-11-17 `python skills/_shared/scripts/build-api-index.py`
with that folder and an output folder as its two arguments wrote the index in about 6 seconds (6,776 classes,
431 enums), and `python skills/_shared/scripts/dayz-api.py chain PlayerBase` then printed the base class chain.
On Windows the Tier 2 search rule (Grep, then the `dayz-rag` search) stays the first choice; the index is for
a machine with no work drive, or for one answer that needs every inherited member.

| Script | What it does |
|---|---|
| `dayz-proton.sh` | `init`, `doctor`, `winpath`, `tool`, `gui`, `binarize` and `headless start/shot/stop` for DayZ Tools and `DayZDiag` under Proton, in private prefixes (sections 2 to 5). |
| `dayz-mod-pack.sh` | Workshop project helper on dayzmake: `init`, `keygen`, `build`, `check`, `publish-hint`. It never uploads; publishing stays a manual step. |
| `dayz-client-headless.sh` | Runs the retail client in a headless sway session: `start`, `shot`, `stop`, `status`. One client at a time. |
| `dayz-client-test.sh` | One automated client and server test: starts the native server and the headless client, waits for the mod's final test line, collects logs and a screenshot, stops both. |
| `find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh` | Find the native server install, build a private server tree, pick free ports. |
| `extract-dayz-sources.sh` | Unpacks the scripts and derapified configs of an install or a mod. |
| `build-api-index.py`, `dayz-api.py` | Build a compressed script API index (`dayz-api.txt.xz`, or `mod-<name>.txt.xz` with `--mod`) and query it: `class`, `find`, `sub`, `enum`, `src`, `chain`, `defines`. The index holds Bohemia's and mod authors' declarations, so build it locally (default folder `~/.cache/dayz-api`, or `DAYZ_API_DIR`) and never commit it. |
