# DayZ environment and infrastructure notes

Covers the work drive and mod layout, the diag binaries, `serverDZ.cfg` settings, build and launch commands with their measured gotchas, mission files, engine connect-error codes and log files.

Status: field notes from mod projects, not yet checked on `P:\` line by line; the lines that cite a `P:\` file were opened and confirmed. Tool behaviour (AddonBuilder, CfgConvert, FileBank, BattlEye) was measured on one Windows machine; the VPP AdminTools section is third-party mod behaviour, not vanilla. Where this note and Tier 2 (`skills/_shared/dayz-conventions.md`, `skills/_shared/conventions/server.md`) cover the same rule, Tier 2 wins: this repo keeps test servers under `.server/<instance>/`, not the `workspace\_server\` layout the commands below show.

## Drive and mod layout

- **`P:\` is the DayZ Tools work drive.** DayZ Tools / AddonBuilder / Buldozer
  require the work drive as `P:\`.
- **`P:\Mods\` must be a directory junction to the `!Workshop\` of the installed DayZ**
  (not a normal folder). The engine and the Launcher read mods from
  `<DayZ install>\!Workshop\`. The junction allows deploying PBOs like
  `P:\Mods\@<ModName>\Addons\<ModName>.pbo` and having them land where the engine
  looks for them:

  ```cmd
  cmd /c mklink /J P:\Mods "<DayZ install>\!Workshop"
  ```

  Does not require admin. Verify before every PBO build. If `P:\Mods\` exists
  as a normal folder, it must be deleted first (`rmdir /S /Q`).
- **Vanilla data candidates on `P:\`**: `P:\dz`, `P:\DZ`, `P:\dta` — the first
  that exists is the right one. Windows paths are case-insensitive, so `P:\dz` and `P:\DZ` are the same folder.
- **Mod source convention**: `P:\<ModName>\` as a junction to the actual
  editable folder (typically outside OneDrive if you want to avoid the OneDrive
  race rule). AddonBuilder reads from `P:\<ModName>\`, you edit in the actual
  folder, and `$PBOPREFIX$` resolves relative to `P:\`.
- **Mod naming**: `[A-Za-z][A-Za-z0-9_]{0,63}`. **No hyphens** (the name
  doubles as a C-style identifier in `CfgPatches`). `My-Mod` does not parse, use
  `My_Mod` or `MyMod`.

## Mandatory diag binary for iteration

- **Client and server must be `DayZDiag_x64.exe`**, NOT retail binaries.
  Reason: with `-filePatching` (needed for the engine to read raw `.cpp`/`.c` from
  source) retail (`DayZ_x64.exe` client and `DayZServer_x64.exe`) hang
  past-loading-screen. The same `DayZDiag_x64.exe` runs in client or
  server mode depending on whether you pass `-server` or not.
- **DayZ Server install (Steam appid 223350) is NOT needed for iterating** — only
  for initial bootstrap of the mission template (e.g. `dayzOffline.chernarusplus`).
  After copying it to the workspace, it can be uninstalled.
- **Client display flags**: `-window`, `-x=<width>`, `-y=<height>` — useful
  for iterating without fighting fullscreen ultrawide. Convenient default: 1920x1080
  windowed.

## `serverDZ.cfg` — `allowFilePatching = 1;` is required

If the client connects with `-filePatching` and the server does NOT have
`allowFilePatching = 1;`, the server refuses the connection with engine connect-error code `0x00020005`:
*"The server does not support the client's current filePatching setting"*. This is not a BattlEye
kick: the code is `EConnectErrorServer.FILE_PATCHING` ("Bad file patching",
`P:\scripts\3_game\global\errormodulehandler\connecterrorservermodule.c:10`). See "Connect error codes" below.

```
// serverDZ.cfg
allowFilePatching = 1;
```

It is only lowered to `0` when deploying the server to real production (no live
script iteration).

## VPP AdminTools — admin access in dev (`vppDisablePassword`)

Recurring problem: VPP asks for password when activating admin mode (End key) and
rejects it even if the SteamID is in `Permissions\SuperAdmins\SuperAdmins.txt`.
Third-party mod behaviour, not vanilla: read in the VPP AdminTools scripts
(`PermissionManager.c`, `missionServer.c`) on 2026-06-09:

- Superadmins are read from `<profile>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt`
  (one per line). The root `SuperAdmins.json` is from the old version — it is not used.
- The **Steam API key is NOT required** for superadmin (empty `SteamAPI.json` is
  non-fatal; the "Adding Super Admin" log precedes the SteamAPI error).
- Login = `SHA256(password)` vs `Permissions\credentials.txt` (≤32 chars → VPP
  hashes and rewrites it on boot; ==64 chars → uses it as direct hash). After match,
  `EnableToggles` uses `HasUserGroup`, which returns true for superadmins.

**Solution for dev (the good one — do not fight with credentials.txt):** in `serverDZ.cfg`:

```
vppDisablePassword = 1;
```

VPP's own `missionServer.c:14` → `if (ServerConfigGetInt("vppDisablePassword")>0) DisablePasswordProtection(true)`
→ VPP asks for no password; superadmin (SteamID in SuperAdmins.txt) enters directly.
Default VPP keybinds: `kHome`=Open Menu, `kEnd`=Toggle Admin (rebindable under
Options→Controls if client profile was regenerated without them).

## Canonical invocation commands

**AddonBuilder** (build PBO):

```cmd
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons ^
    -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

`-clear` clears the `-temp` folder before copying (useful in large refactors /
chasing stale assets).
**Measured build gotchas:**

- **With `-clear`, AddonBuilder cleans its `-temp` BEFORE copying** ("Clearing temp folder" in its log) and
  the default is `P:\temp\<mod>`. `P:\temp` and `P:\TEMP` are the SAME path (Windows
  case-insensitive): source staging under `P:\TEMP\<X>` with `-temp=P:\temp\<X>`
  causes AddonBuilder to DELETE the entire staging and fail with "Copy failed" (and exit 0 on
  some error paths — log is the truth, not exit code). NEVER place staging
  or sources under `P:\temp\*` / `P:\TEMP\*`.
- **Without `-clear` the sync of `-temp` is INCREMENTAL and can serve STALE source.** Only with `-clear` does AddonBuilder log
  "Clearing temp folder"; without it, it does incremental "Syncing folders" and a changed `.c`
  may NOT be re-copied. Measured case: one `.c` file kept a ~2-month-old copy
  in `P:\temp\<Mod>\` → each build (packonly and binarize) packed old code,
  diag compiled the old version, and an applied fix verified on disk "did not take"
  during several rebuilds. Filepatching did NOT save the case (did not overwrite `.c` files in
  the PBO with loose ones from work drive). Canonical symptom: compilation error that
  persists identically after editing + verifying source. Mitigation: delete
  `P:\temp\<Mod>` before each build, or pass `-clear`.
- **CfgConvert `-dst` fails SILENTLY (exit 0, no output) with quoted args** via
  `Start-Process -ArgumentList` (nested quotes). Reliable pattern: `-WorkingDirectory`
  in config folder + RELATIVE paths without quotes
  (`-bin -dst config.bin config.cpp`). ALWAYS validate output by
  timestamp+exact location, not by "a file with that name exists" (a years-old
  config.bin in the working directory almost ended up inside the day's PBO).
- **Pack-only pipeline validated in game** for pure script
  mods: (1) clean copy of sources WITHOUT `*.pbo`/`*.bisign` (robocopy `/XF`); (2)
  `CfgConvert -bin -dst config.bin config.cpp` and remove `config.cpp` + `mod.cpp` from
  staging (deployable PBO does NOT include them; `mod.cpp` goes loose in `@Mod\`); (3)
  `FileBank.exe -property prefix=<Mod> -property "product=dayz ugc" <folder>` → generates
  `<folder>.pbo` alongside. Verification: parse header (properties + file list
  vs previous validated PBO) + binary grep for new symbols + signature
  `\0raP` of config.bin. FileBank does NOT compile `.c` — first real compile-check
  is startup RPT.

**Server diag**:

```cmd
DayZDiag_x64.exe -server ^
    -config=workspace\_server\maps\<map>\serverDZ.cfg ^
    -profiles=workspace\_server\maps\<map>\profiles ^
    -mission=<absolute-path-to-mission-template> ^
    -mod=@Mod1;@Mod2 ^
    -filePatching -port=2302
```

**Critical**: `-mission=<absolute path>` must be absolute. If omitted, engine
looks in binary `mpmissions/` (does not exist in DayZ install) and server
boots with empty mission → log says *"Mission script has no main function.
PlayerConnect will stay disabled"*.

**Client diag**:

```cmd
DayZDiag_x64.exe -profiles=workspace\_server\!ClientDiagLogs ^
    -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=2302 -filePatching
```

`-profiles=` pointing to a dedicated folder contains all diag artifacts
(Users/, DataCache/, BattlEye/, RPT, script.log) in one place.

## Mission templates — canonical aliases

| Short alias | Mission folder |
|---|---|
| `chernarus` | `dayzOffline.chernarusplus` |
| `livonia` | `dayzOffline.enoch` |
| `sakhal` | `dayzOffline.sakhal` |
| custom | actual folder name (e.g. `dayzOffline.namalsk`) |

## Optional environment variables (resolvers)

In case your install lives outside Steam defaults. Resolution order: env var
→ registry (Tools only) → common fallback.

| Variable | Points to | Used by |
|---|---|---|
| `DAYZ_TOOLS_PATH` | DayZ Tools install root (parent of `Bin\AddonBuilder\AddonBuilder.exe`) | Build, preflight |
| `DAYZ_GAME_PATH` | DayZ game install (with `DayZ_x64.exe` and `DayZDiag_x64.exe`) | Launch-test |
| `DAYZ_DIAG_PATH` | Direct path to `DayZDiag_x64.exe` | Launch-test (override) |
| `DAYZ_VANILLA_DATA_PATH` | Folder with extracted vanilla (`P:\dz`, `P:\DZ`, `P:\dta`) | Preflight, lookup configs |
| `DAYZ_WORK_DRIVE` | Folder to mount as `P:\` | Mount script |

## Textures: required suffixes

Textures referenced in `.rvmat` and `config.cpp` must use canonical
suffixes. ImageToPAA validates this when converting from PNG/TGA. Textures in
**power-of-two dimensions** (1024x1024, 512x512, etc.).

| Suffix | Purpose |
|---|---|
| `_co` | Color (diffuse) |
| `_nohq` | Normal map |
| `_smdi` | Spec/mask |

## `.p3d` named properties — the ones that matter

Set in Object Builder via *Edit → Named Properties*:

| Property | Typical value | Purpose |
|---|---|---|
| `autocenter` | `0` | Items in hand: grip point is NOT recentered when loading model |
| `mass` | (kg) | Geometry LOD: physics weight |
| `mapType` | `building`, `vehicle`, etc. | Icon shown on in-game map |
| `class` | `house`, `car`, etc. | Engine behavior category |
| `damage` | `no`, `building`, `tree`, `tent` | Destruction type: how the object breaks when destroyed (e.g. `building` in `P:\DZ\structures\military\houses\mil_barracks_round.p3d`) |

## Server and Central Economy: relevant files

Standard layout under `<mission>/`:

| File | Function |
|---|---|
| `init.c` | Server-side mission entrypoint. Mandatory `main()` (if missing → "PlayerConnect will stay disabled" in RPT) |
| `cfgeconomycore.xml` | CE structure (points to type files) |
| `db/types.xml` | Spawn rates, lifetimes, locations |
| `db/events.xml` | Custom dynamic events (heli crashes, infected hordes, etc.) |
| `cfgeventspawns.xml` | Event spawn positions |
| `cfgspawnabletypes.xml` | Items appearing as event content |
| `cfggameplay.json` | Runtime tuning (movement, stamina, environment). Read from `$mission:cfggameplay.json` (`P:\scripts\3_game\cfggameplayhandler.c:3`), and only when `enableCfgGameplayFile` is set in `serverDZ.cfg` (`P:\scripts\3_game\cfggameplayhandler.c:53`) |
| `cfgweather.xml` | Weather config (XML: `<weather reset= enable=>` + overcast/fog/rain/wind/storm). NOT `.json` |
| `db/globals.xml` | CE global variables |
| `mapgroupproto.xml` + `mapgrouppos.xml` | Loot tier locations (military, residential, etc.) |
| `storage_1/` | Active persistence. **Backup BEFORE touching economy.** |

## Connect error codes

A `CONNECTING FAILED (0xCCCCNNNN)` message is an engine connect error, not a BattlEye kick. The full code is two shorts: the high short is the `ErrorCategory` and the low short is the code inside it (`P:\scripts\3_game\global\errormodulehandler\errormodulehandler.c:4-26`). Category `0x0001` is `ConnectErrorClient` and `0x0002` is `ConnectErrorServer`: the measured `0x00020017` "Client is using Diag exe while the server is not" (`linux-proton-findings.md`) is `EConnectErrorServer.CLIENT_DIAG` = 23 (`connecterrorservermodule.c:29`). The usage examples in the comments of `errormodulehandler.c` number the categories one higher; the measured messages are what the engine does.

| Code | Enum value | Meaning | Fix |
|---|---|---|---|
| `0x00020005` | `EConnectErrorServer.FILE_PATCHING` (`connecterrorservermodule.c:10`) | Client runs `-filePatching`, server does not allow it | `allowFilePatching = 1;` in serverDZ.cfg |
| `0x00010002` | `EConnectErrorClient.ALREADY_CONNECTING` (`connecterrorclientmodule.c:7`) | Client is already trying to join a server | Wait for the first attempt to finish or fail, then retry |

The enums are in `P:\scripts\3_game\global\errormodulehandler\`.

## When the RPT cites that a script fails

- `script_<date>_<time>.log` → script side errors (compile + runtime). On the retail server the RPT
  repeats its `SCRIPT` lines as well (server RPTs of 1.29.163047 and 1.30.164200, read 2026-11-09),
  so a script error shows up in both
- `<server>.RPT` / client RPT → engine-side errors (missing assets, malformed
  configs, access violations)
- `crash_<date>_<time>.log` → **handled exceptions, NOT real segfaults** (hard
  crashes write a separate dump)

## Tooling realities

- **DayZ does NOT have a unit test runner for Enforce Script.** The quality lever
  is strict adherence to `enforce-script-reference` (style guide +
  pitfalls). Hence the rule to batch in-game tests: each iteration is expensive
  (rebuild PBO ~30s + connect ~30s + scenario setup 1-3 min).
- **`shutil.rmtree` on Windows recurses INSIDE junction targets.** If you have
  `P:\<Mod>\` pointing to external source and you run `rmtree(P:\<Mod>)`, it wipes out
  external source. To delete junctions: `cmd /c rmdir <junction>`
  (does not recurse, only deletes link).

## Terrain / map (quick reference)

Basic pipeline:

| File / step | Function |
|---|---|
| Heightmap (`.png` / `.xyz`) | Terrain elevation |
| Satellite map | Large terrain texture color |
| Mask map | Surface assignment per pixel |
| `layers.cfg` | Layer config — which surface maps to which mask color |

## Caveats measured on one Windows machine (2026-06)

- **DayZServer standalone (Steam, app 223350) does NOT complete mission loading on this machine EVEN IN PURE VANILLA**: hangs after loading configs, no error in logs, and dies ~6 min later with -freezecheck ("Termination successfully completed"). 4 verified runs 2026-06-10. For local tests ALWAYS use DayZDiag route (skill dayz-test-ingame; per-mod tools in `<Mod>_dev\tools\`). Its mpmissions folder remains useful as mission source for diag absolute -mission. **Not reproduced on 1.30 (2026-11-10):** on the same machine the retail DayZServer 1.30.164289 passed Steam init, loaded a copy of the vanilla mission and ran until a test mod asked it to exit, with a `serverDZ.cfg` that sets `instanceId` (without it the server counts down `termination in: 10` and exits: `skills/dayz-test-ingame/references/windows-launch-cycle.md`, the `instanceId` bullet).
- **Parsing of -mod in standalone DayZServer**: embedded quotes in paths with spaces SPLIT the value (treats `"C:\Program` as mod name; symptom: `ANIMATION (E): Can't load "C:\Program...`). DayZDiag with ENTIRE -mod token wrapped in outer quotes does accept absolute paths with spaces separated by semicolons. General fix: junctions without spaces (mklink /J) and paths relative to working dir.
- The standalone DayZServer route needs each mod reachable from its own install folder: junctions there (`@CF`, `@VPPAdminTools`) pointing at the client `!Workshop` folders served a Steam-server `.bat`. The DayZDiag flow does not need them.
