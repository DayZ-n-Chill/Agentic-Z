# The Windows build, deploy and launch cycle

The loop this skill runs on one Windows machine: prerequisites, the build and launch cycle, launch modes, the `dayz-test.ps1` orchestrator generated from `templates/`, default mods and admin tools, what `-filePatching` does and does not reload, and why mod paths must be absolute.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: dated findings were measured on one Windows test machine, and "this install" means that machine, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it. `[EXACT - environment-and-infra.md]` means `skills/_shared/knowledge/environment-and-infra.md` records the fact too.

Measured results, tool behaviour and third-party mod behaviour (Community Framework, Dabs Framework, VPPAdminTools, dayz-mcp) in this file are not yet checked on `P:\` and most cannot be, because they are not vanilla script facts.

## WHAT THIS DOES

Closes the dev loop for a DayZ mod on a single Windows machine: re-pack the PBO, deploy it where the engine reads mods, and launch `DayZDiag_x64.exe` with `-filePatching` so that script and config edits can be picked up without re-binarizing (see "FILEPATCHING SCOPE" for what that really covers). Four launch modes (`offline`, `server`, `client`, `all`) are driven by one orchestrator script and double-click `.bat` wrappers, generated per mod into `<Mod>_dev\tools\`.

Until 1.29 the loop was: pack the PBO, deploy the packed `@Mod`, launch DayZDiag with `-filePatching`. Since 1.30 `-mod` may point at an **unpacked** source folder, RV configs load unpacked, and there are new flags `-cacheP3D=0/1` and `-resolveFilePatchingUsingEnfusion=0/1` (documented for 1.30 Experimental; not checkable on `P:\`). Details: `dayz-1-30-test-ingame.md`.

## WHEN TO USE / WHEN NOT

Use when the user wants to see a mod running in game, iterate scripts and configs, or stand up a local server and client. Do not use it to author the mod (that is `dayz-model-pipeline` / `enforce-script-reference`), to validate or pack only (`/dayz-build-pbo`), or to configure a production server. The retail `DayZ_x64.exe` is for final pre-release validation only; default to the diag exe. Retail is manual-only and external to this launcher.

On the measured machine the retail executables did not finish loading a mission, so a retail run there only proved that `3_Game` and `4_World` compile; `5_Mission` was only compiled on diag. Report script coverage per module, never as one green retail result.

## PREREQUISITES (the preflight runs automatically)

### Step 0 - offline linter, before spending a startup

A startup cycle costs minutes; the linter costs about 60 s and catches what you would otherwise discover reading an RPT:

```
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Gate on **`len(errors)`**, never on `status` (`WARN` with zero errors is valid). The path is relative to the Agentic-Z repo root, not your mod folder: from a mod directory give the absolute path to the repo checkout, or the command dies with `No such file or directory` and reads as "not installed". `/dayz-lint` checks the mod setup; this validator checks the code itself. Compare against the base branch to know whether an error is yours. It does not replace a startup: Enforce Script only compiles when the world loads, and the linter does not see that. But `errors > 0` means the startup will fail, and there is no need to launch to find out. Run it whenever a change deletes classes, files or `config.cpp` entries.

**Measured blind spot: the linter does not see an undeclared member.** An `obj.m_Field` where the type of `obj` does not declare `m_Field` exits with 0 errors and no delta, and on world load the module dies with `Cant compile "World" script module!` plus `ACCESS_VIOLATION`. Measured 2026-09-08: the same tree passed this gate 12 times on branches and again after the merge, and a review by a second model did not catch it either, because an incrementing counter looks reasonable in a diff. The case was a field read on one metrics class that only the adjacent class in the same file declares. The server started fine because that code was on the render path; a gate that only reads the server log passes it.

A cheap sweep catches it before a startup when a change touches many files: for each typed local `Type obj = ...` in the diff, check that each `obj.m_Field` is declared in `Type` or its parents, resolving inheritance with a regex census of `class X : BASE {...};` across all `scripts/`. Measured: 145 classes and 32 files in about 2 s. It only covers locals with an explicit type (not member accesses, function returns or `this`), but it covers this pattern.

### What the orchestrator checks

`dayz-test.ps1` checks these on every run and fixes what it safely can.

- **Diag exe** - `DayZDiag_x64.exe`. Client and server must both be the diag binary; retail blocks past the loading screen with `-filePatching`. [EXACT - environment-and-infra.md]
- **`P:\Mods` junction** to `<DayZ>\!Workshop`, so deployed PBOs land where the engine looks. The script creates it with `mklink /J` if it is missing (no admin rights needed). [EXACT - environment-and-infra.md]
- **`allowFilePatching = 1`** in the server's `serverDZ.cfg`, or BattlEye kicks the client with `0x00020005`. The script generates a dev `serverDZ.cfg` with it set. [EXACT - environment-and-infra.md]
- **Mission template** - an absolute path; the server loads an empty mission otherwise. That is Windows and DayZDiag; the native Linux `DayZServer` is the opposite, see `linux.md`. Aliases: `chernarus`, `livonia`, `sakhal`. [EXACT - environment-and-infra.md]
- **`class Missions` in `serverDZ.cfg`** - a dedicated server with a `dayzOffline.*` mission terminates itself before the mission loads (RPT countdown `[Server] :: termination in: N`) unless the config declares `class Missions { class DayZ { template="<mission>"; }; };`. With it, the server stays up with no client, which is what a server-side probe in the mission `init.c` needs. [EXACT] (measured in game, DayZ 1.30.164014 Experimental)
- **`instanceId` in `serverDZ.cfg`** - keep it: without it a minimal config got the same countdown even though it declared `class Missions`. On the retail DayZServer 1.30.164289 (Windows, 2026-11-10) a hand-written `serverDZ.cfg` with `class Missions` and no `instanceId` counted down from `[Server] :: termination in: 10` right after `NETWORK : server: Player dpid=2 added`, with no `SteamGameServer_Init` line; the same file plus `instanceId = 1;` and nothing else passed Steam init, loaded the mission and ran until a test mod asked it to exit. Only `instanceId` was tested: whether another key of the shipped `serverDZ.cfg` would also avoid the countdown is unknown. The dev `serverDZ.cfg` the script generates already sets it (the generated config block of `templates/dayz-test.ps1`). [EXACT]
- **AddonBuilder** - only with `-Build`. [EXACT - environment-and-infra.md]
- **Steam client session** - for the modes that launch a client (`offline`, `client`, `all`), `HKCU\Software\Valve\Steam\ActiveProcess` must have both `pid != 0` and `ActiveUser != 0`. The script warns without aborting and suggests `steam.exe -shutdown` followed by a relaunch of Steam (the login is preserved), both from outside any sandboxed (MSIX) app (`managed-launcher.md`, "Secure-launcher request grammar, the Steam prerequisite, and orphaned runs", point 1-ter). A restart is not the reliable remedy: measured 2026-09-08/09, a restart can leave the key pointing at the old pid with the client still dead. The deterministic fix is to copy the live `steam.exe` pid into `ActiveProcess` from a shell outside any sandboxed app (a write from inside one only reaches that app's private registry copy, see `dayz-1-30-test-ingame.md`), with the guards and the verification in "The Steam `pid` in the registry can be dead" in `troubleshooting.md`. Restart only as a fallback when there is no live Steam or `ActiveUser == 0`.

- **On the dayz-mcp managed route the mod set is sealed, and changing it wipes the test world** (since 2026-09-06, measured in game; dayz-mcp behaviour, not vanilla). Each server startup seals its effective mod list in `<mission>\storage_1.modset.json` (`seal` field, sha256). If the seal differs from the previous startup, the startup archives `storage_1` into `storage_1.modset-<ts>-<seal8>` (with its `.marker.json` and a `…rotation.<hash>.completed.json` receipt) and starts fresh: world, bases and test characters are gone. Measured: repeating the same set does not rotate and the seal does not move; changing it rotates exactly once; repeating the new one does not rotate; and `mode=client` on a live run does not rotate either, because rotation happens at server startup.
  - If you alternate mod stacks (your mod, then another, then yours), you lose test persistence on each hop. To keep it, copy `storage_1` by hand beforehand; the archived copies all stay as siblings in the mission directory.
  - Rotation leaves no row in the audit log (a known defect: the emitter swallows its exceptions). If you lose the world and look for the reason, check the `storage_1.modset-*` folders and the `seal` field, not the audit log.
  - It is deliberate and fixes something worse: before the seal, the same stack hop corrupted the savegame. Measured 2026-09-04 with the previous bundle, an A to B hop produced 43,197 lines of `Scripted variables corrupted`; with the seal, both signatures (`Failed to read modstorage` and `Scripted variables corrupted`) are at 0. When diagnosing, watch both signatures: in that repro the one that appeared was not the one first suspected.
  - Format trap: `extra_mods` is a list, not a string with `;`. `["@CF;@VPPAdminTools"]` passes validation and then does not exist as a folder, and nothing reports it.
  - On the MCP route, the stale Steam session of the previous point shows as `dayz_test_run` dying in the `validating` phase at about 1.3 s with `error_code: "steam_session_stale"`; the remedy is the same.

Path resolution is environment variable first, Steam default as fallback (`DAYZ_GAME_PATH`, `DAYZ_DIAG_PATH`, `DAYZ_TOOLS_PATH`, `DAYZ_WORK_DRIVE`). [EXACT - environment-and-infra.md]

## THE CYCLE

1. **Build and deploy** (`-Build`) - `AddonBuilder P:\<Mod> -> P:\Mods\@<Mod>\Addons\<Mod>.pbo`. Required whenever **assets** (`.p3d`, `.paa`, `.rvmat`) change: filePatching does not reliably hot-load binarized models and textures.

   **Scripts-only mods**: AddonBuilder's default binarize mode drops `.c` files (they are not in its include list), which gives a config-only PBO where the mod mounts but no script runs. `Invoke-Build` adds `-packonly` when the source has no `.p3d`, `.paa` or `.rvmat` (force it with `-PackOnly`), and warns if a mod with a `scripts\` folder packs suspiciously small (verified 2026-06-03).

   **`.asi` / `.anm` (added 2026-06-24)**: binarize mode also drops these unless the `-include` list has `*.asi;*.anm`. A weapon with a custom player animation graph (`AddItemInHandsProfileIK`, second argument its own `.asi`) then builds without the graph: the reference points at a missing file and the change is silently absent, while the build still reports success. The include list must contain `*.asi;*.anm`. Verify that the `.asi`/`.anm` shows up as a file entry in the PBO header, not just as a string inside the compiled script.

   **Mixed mods, assets plus scripts (added 2026-07-22)**: `-packonly` is not added when `.p3d`/`.paa` are present, and `Invoke-Build` never passes `-include` (only `-prefix`, `-temp`, and `-clear` or `-packonly` when they apply), so binarize still silently drops `.c`, `.paa`, `.ogg`, `.rvmat`, `.layout` and `.csv`: the PBO mounts with zero scripts running. The "packs suspiciously small" warning (under 4096 bytes) misses it, because binarized `.p3d` files keep the PBO large (measured: 95.1 MB / 170 files without an include list, 451 files / 106.8 MB with one). The build that worked: `AddonBuilder <src> <out> -prefix=<Mod> "-temp=<tmp>" "-include=<lst>" -clear` with the list `*.c;*.asi;*.anm;*.paa;*.rvmat;*.layout;*.ogg;*.ptc;*.csv`. After the build, count the PBO entries or search the PBO for a known `.c` (170 against 451 is the drop). The limits of `-include` are in `build-and-storage-traps.md`, "Mixed build": the list filters what is synced, it does not define the PBO, so validate the actual entries. `/dayz-build-pbo` is the supported build in this repo.

   **Mixed mods, migration (added 2026-08-04)**: the failure usually arrives when a mod migrates from a hand command to the generated scripts. Measured on a mod with three script files: 22 entries / 401,857 bytes without the include list, 25 entries / 411,786 bytes with it; the gap is exactly the three `.c`. The hand command passed `-include=...\tools\include.lst`, a list created by hand. Generating the scripts for a mod copies only `dayz-test.ps1` and the three `.bat` wrappers; it does not write `include.lst`, and `Invoke-Build` does not pass `-include`. Switching from the hand command to `server.bat` or `dayz-test.ps1 -Build` therefore drops every script with no visible change (the PBO is still large; the 4096-byte warning never fires). In game the mod mounts but no action appears, which cannot be told from an unregistered ActionConstructor or a bad ActionCondition, so the wrong file gets debugged. List the freshly built PBO before spending a test cycle. A local patch for `Invoke-Build` passes the include list when it exists and the build is not packonly:

       $incLst = Join-Path $PSScriptRoot 'include.lst'
       if (-not $usePackOnly -and (Test-Path $incLst)) { $abArgs += "-include=$incLst" }

   and replaces the size check (`scripts\` present and PBO under 4096 bytes) with a content check: if the source has `scripts\`, list the PBO (for example with `BankRev -lf`) and require the packed `.c` count to equal the source `.c` count. The template in `templates/` does not carry this patch.
2. **Launch** - the diag exe in the chosen mode. `-filePatching` is meant to pick up **script and config** edits (`.c`, `.cpp`) without re-packing; on the measured install it did not (see "Script changes did not hot-load" below), so prove it with the probe there before relying on it.

So: edit a model, re-run with `-Build`. Edit a script, rebuild the PBO too unless the probe showed that your install serves the source.

## RELEASE-GRADE BUILD BOUNDARY

[EXACT] `exit_0_is_not_build_success`. AddonBuilder can leave an old destination PBO in place after a later copy step fails, so the process exit code and `Test-Path` alone do not prove that the requested bytes were built or deployed. A release verdict requires evidence for a `fresh_pbo`, the expected `header_prefix` and file entries, and a clean `fatal_log` scan; require a valid `.bisign` too when signing is expected.

[DESIGN] A release workflow must stage the candidate outside the published path, validate it, and publish only after every gate passes. On any failure, require `previous_artifact_unchanged` and do not advance the build manifest or cache. Its cache key must cover input bytes, build options, prefix, DayZ build, tool versions and hashes, and signing-key identity. Its preflight must reject case and path conflicts, files that are excluded but referenced, absolute packaged paths, stale or missing `.paa` dependencies, and unsupported ODOL inputs before binarization.

The generated dev launcher does not implement that release contract. Use its PBO for iteration, but do not label the result release-ready until a build and release pipeline (`/dayz-build-pbo`, `/dayz-gate build`, `/dayz-release-pack`) supplies these postconditions.

## MODES

| Mode | What | Status |
|---|---|---|
| `all` (default) | server, wait for the UDP bind, then client | [EXACT - environment-and-infra.md] |
| `server` | `DayZDiag_x64.exe` managed with `-server` | `managed_lifecycle=true`; [EXACT - environment-and-infra.md] |
| `client` | diag `-connect=127.0.0.1` (server already up); needs `-RunId` | [EXACT - environment-and-infra.md] |
| `offline` | single diag with `-mission`, no network | **[DESIGN]** validate in game |

## USAGE

The orchestrator starts and stops the game through the dayz-mcp managed lifecycle: every launch mode and `-Kill` need the lifecycle environment (`DAYZ_MCP_TOOLS` and the client id and lease that `dayz_test_run` passes in, see `managed-launcher.md`). `-Preflight` and `-Build` run before the first lifecycle call. Without dayz-mcp, use `/dayz-build-pbo` and `/dayz-launch-test`.

From `<Mod>_dev\tools\`:

```powershell
# build, deploy, run server+client on Chernarus
.\dayz-test.ps1 -Mod MyMod -Mode all -Build

# relaunch only the client on the run that is already up
.\dayz-test.ps1 -Mod MyMod -Mode client -RunId <run_id>

# offline look at a model [DESIGN]
.\dayz-test.ps1 -Mod MyMod -Mode offline -Build

# another map + an extra dependency on top of the defaults (CF/Dabs/VPP)
.\dayz-test.ps1 -Mod MyMod -Mode all -Build -Mission livonia -ExtraMods "@SomeDependency"

# preflight only / stop one exact managed run
.\dayz-test.ps1 -Mod MyMod -Preflight
.\dayz-test.ps1 -Mod MyMod -Kill -RunId <run_id>
```

Key parameters: `-Mod` (required), `-Mode`, `-Mission`, `-Build`/`-Clean`, `-ExtraMods`, `-BaseMods`/`-NoBaseMods` (see below), `-Source` (default `P:\<Mod>`), `-RunId`, `-NoFilePatching`, `-Port`, `-PlayerName`, `-ServerWait`. Double-click wrappers: `server.bat` (all + build), `client.bat` (pass `-RunId <run_id>`), `offline.bat`.

## DEFAULT MODS & ADMIN TOOLS

Every launch prepends three base mods (load order, CF leftmost; the folder names are the ones Steam Workshop installs): `@CF;@Dabs Framework;@VPPAdminTools`. The mod under test and `-ExtraMods` load after them. Override with `-BaseMods "..."`, or drop them with `-NoBaseMods`.

`@VPPAdminTools` gives in-game admin tools (teleport, spawn, godmode, object editing) for testing. Admin access is by **SteamID64**, not a server password, but the on-disk layout differs across VPPAdminTools versions, and the version measured uses the `Permissions\` folder, not the root `SuperAdmins.json`. Because the script isolates `-profiles`, the preflight seeds both so that admin works on either version (idempotent; a password that is already hashed is never overwritten):

- `<server profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` - one SteamID64 per line; the file the measured VPPAdminTools reads (verified in place 2026-06-09).
- `<server profiles>\VPPAdminTools\Permissions\credentials.txt` - the in-game login password on line 1. VPPAdminTools hashes it on first boot and the raw value is then lost. [EXACT] There is no packaged default. It is seeded only when the operator explicitly supplies a non-empty `-AdminPass`, and its value is never printed.
- `<server profiles>\VPPAdminTools\SuperAdmins.json` - `{ "SUPER_ADMINS": ["<SteamID64>"] }`, the legacy layout; still seeded for older builds that read it.

SteamID source: `-AdminSteamId`, else reused from the retail config at `%LOCALAPPDATA%\DayZ\VPPAdminTools\SuperAdmins.json`. In game: open the VPPAdminTools menu (the key is set under Options → Controls), then log in with the password. To change the admin or the password later, edit the files above and restart the server.

**No-password dev default (verified against the VPPAdminTools source 2026-06-09; third-party mod behaviour, not vanilla):** the generated `serverDZ.cfg` sets `vppDisablePassword = 1;`, so VPPAdminTools skips the login password: a superadmin (SteamID in `SuperAdmins.txt`) gets access with no password (its `missionServer.c:14` calls `DisablePasswordProtection(true)`; access is granted because `HasUserGroup` leads to `IsSuperAdmin`, its `PermissionManager.c:693`). The `credentials.txt` password path failed repeatedly across sessions (SHA256 and version quirks), and disabling it removes that class of failure. An explicitly seeded `credentials.txt` password only matters if you remove `vppDisablePassword` for password-gated testing. In-game keys: End toggles admin, Home opens the menu (rebind under Options → Controls if a fresh client profile lost them).

The dev `serverDZ.cfg` sets `verifySignatures = 0`, so VPPAdminTools' signed PBO loads without registering its `.bikey`.

## GENERATING THE SCRIPTS FOR A MOD

1. Create `<Mod>_dev\tools\` if absent (the orchestrator expects dev tooling in a `<Mod>_dev` folder next to the mod source, and refuses to run from inside a skill folder).
2. Copy `templates\dayz-test.ps1` there verbatim; it is generic (driven by `-Mod`).
3. Copy the three `.bat` wrappers and replace the `__MODNAME__` placeholder with the real mod name (the CfgPatches identifier, no dashes: `My_Mod`, not `My-Mod`). [EXACT - environment-and-infra.md]
4. Confirm the mod **source** is reachable at `P:\<Mod>` (a junction to the editable folder) or pass `-Source`. Confirm that the `requiredAddons` in `config.cpp` map to the `-ExtraMods` you pass (CF, Expansion and so on); the client and server mod lists must match.

The `.ps1` does not depend on this skill at runtime, so it stays valid in the mod repo if the skill changes. The `_server\` and `_client\` workspaces (serverDZ.cfg, RPT, script.log) are created next to `tools\` under `<Mod>_dev\`.

## FILEPATCHING SCOPE - read before promising hot-reload

`-filePatching` is meant to hot-load **scripts and configs** from raw source, not binarized assets. Model, texture and material changes need a `-Build`. Do not tell the user "just edit and it reloads" for a `.p3d` or `.paa` change; that is the most common false expectation here. On the measured install even scripts did not hot-load, the PBO won (2026-07-20): see the next section and use its `srcprobe` discriminator before attributing anything to filePatching.

## Script changes did not hot-load from the work drive on the measured install: the PBO wins (added 2026-07-20)

Measured 2026-07-20: with `-filePatching` on server and client, `allowFilePatching=1`, the work drive mounted and `P:\<prefix>\scripts\...` present, the engine still compiled the scripts from the PBO. Probe prints that existed only in the source tree never appeared over two boots; after `dayz-test.ps1 -Build` (a packonly repack) the same prints appeared immediately. Consequences:

1. "Iterate scripts without repacking" did not work there. Every Enforce Script change needed a PBO rebuild (packonly, seconds) and a relaunch. Treat the PBO as the only source of truth for scripts until the probe below says otherwise on your install.
2. Loose-file shadowing of models and textures is equally unproven on that install. Do not attribute stale visuals to loose work-drive files, and do not expect fresh visuals from them; verify what the engine runs.
3. **The srcprobe discriminator** (one boot, definitive): change a log string in a line that already prints, in the source only (for example `[TAG]` to `[TAG srcprobe]`), relaunch without rebuilding, and search the script log. Token present: the source was served. Absent, with the old string still printing: the PBO was served. Use it before spending cycles on "why does my script change do nothing".

In the measured session three boots went to probes that were "deployed" but never in the runtime. The same fact explained a false lead of that day: a stale model tree on the work drive was suspected of shadowing the deployed model, and it never did.

## MOD PATHS MUST BE ABSOLUTE - silent no-mount otherwise (verified 2026-06-01)

A bare `-mod=@Name` is resolved by the engine **relative to its working directory** (the game directory), that is `<DayZ>\@Name`. Deployed mods live under `<DayZ>\!Workshop\@Name`, so that relative path does not exist and the engine **silently fails to mount the addon**: its `CfgPatches` and `CfgVehicles` classes never register, and `CreateObjectEx` later returns **null with no RPT error**. The server boots, the mission runs, nothing logs an error, and the mod's classes are not there.

Verified with an in-mission `ConfigIsExisting("CfgPatches <Mod>")` probe on a headless `-server`:

- `-mod=@<Mod>` (relative, working directory = game) gave `CfgPatches.<Mod> = 0` (absent).
- `-mod=<DayZ>\!Workshop\@<Mod>` (absolute) gave `CfgPatches.<Mod> = 1`, and the mod's base class existed.

That was measured on Windows, and the failure is not always silent:

- A relative path that climbs out of the server folder with `..\` does not mount either, and it is loud: the retail DayZServer 1.30.164289 (2026-11-10, in `-serverMod`) stopped loading at an error window `Cannot open file '<server>\..\..\…\@Name\addons\<pbo>'`, wrote an `ErrorMessage_DayZServer_x64_<date>.mdmp` into the profile folder and never reached the mods' `PBO Load` lines; its RPT says nothing about it. [EXACT]
- On the native Linux server the rule is reversed: an absolute `-mod=` / `-servermod=` path mounts nothing and gives no error, so the paths go relative to the server tree. Evidence and the launch line: `linux-native-server.md`, section 3.

`Get-ModString` rewrites every bare `@Name` to its absolute `!Workshop` path through `Resolve-ModToken` (it handles names with spaces such as `@Dabs Framework`, and passes through tokens that are already rooted or not found under `!Workshop`). This applies to server, client and offline.

Not yet verified:

- The probe only confirmed the mount of the **mod under test**. Whether base mods mount under relative names in the `all` mode (client present) was not isolated; resolving all of them to absolute paths makes it moot.
- Checking a dependency's mount needs its **real CfgPatches name**, not the folder name: `@CF` is `JM_CF_Scripts` (verified by extracting `@CF\addons\scripts.pbo`). A probe using `"CF"` gives a false negative.

## OUT OF SCOPE

Authoring the mod, production server config (stock 1.30 formats: `server-and-mission-config.md`), Central Economy and persistence tuning beyond the minimal dev `serverDZ.cfg`, and signing for a Workshop release. PBO validation and packaging internals belong to `/dayz-build-pbo` and `/dayz-release-pack`; the orchestrator calls AddonBuilder and this file records the handoff contract those skills must meet. It does not re-implement their checks.

## REFERENCES

- `skills/_shared/knowledge/environment-and-infra.md` - canonical paths, flags and traps of the environment.
- `/dayz-build-pbo` - pre-build validation and packaging.
- `dayz-mod-workflow` - the debug protocol when a launch surfaces script or engine errors.
- `templates\dayz-test.ps1`, `server.bat`, `client.bat`, `offline.bat` - the generated tooling.

## Session findings (dated appendices -> session-findings.md)

In-game findings from single sessions are in `session-findings.md`; load it when a launch hits one of these. One line each:

- **Five traps of the diag flow (2026-06-11)** - `Print()` goes to script.log, not the RPT; `-filePatching` can compile without the mod's scripts and say nothing; VPPAdminTools needs `@CF` first; one Steam account is one client (kick 179); the deployed PBO is locked while the server runs.
- **Retail visual capture and `Start-Process` (2026-06-17)** - brightness band, specular glint, exposure drift, multi-config desync, the RPT error filter, and `Start-Process EPERM uv_spawn` in a `foreach` with backticks.
- **Mount probe and retargeting a physics autotest (2026-06-22)** - a cheap mount-probe gate (CfgPatches existence) before a physics autotest; the coupling traps of a copied physics harness (no spawn in server-only, a debug token that does not exist, the control-vehicle verdict, case-insensitive `-replace`).
- **Retargeting the harness to a new mod (2026-06-23)** - `dayz-test.ps1` copies verbatim; only per-mod helpers need a case-sensitive token swap; do it directly on the host.
- **The test machine is a single exclusive resource (2026-06-24, superseded 2026-07-15)** - one DayZ instance per machine (UDP 2302); the FIFO lease serializes mutations and the exact `run_id` identifies a lifecycle; mod and profile names give no ownership.
- **Separate `@<Mod>_deps` addon (2026-06-26)** - put dependencies in `-BaseMods` (loads first) or the client fails with `Unknown type` at compile; use the `-mod=` of the last successful RPT.
- **Third-party scripts that only retail tolerates (2026-06-28)** - dependencies that only warn on retail but fail to compile on diag need a parity run on retail that the user opens by hand; the agent stays in quarantine.
- **Launching DayZDiag from the agent (2026-06-28, superseded 2026-07-15)** - background tool jobs can lose their child process; with dayz-mcp use the Diag-only managed launcher and its exact run, not an unmanaged process.
- **H2R import (2026-10-24)** - some DayZDiag 1.30 runs never load their textures while their error counts read normal (compare the run's median JPEG size with a textured run of the same framing, the RPT warning set being specific to that probe, and relaunch); the vehicle 1PP eye rides the `Head` bone and moves between runs and looks: log it at every look.

## The rest of the mod loop

Testing is one step of the loop in the `dayz-mod-dev` skill (look up, write, build, boot, verify, publish), which also routes a failing mod to the domain skill that owns the broken part.
