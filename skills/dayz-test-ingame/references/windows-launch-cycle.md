# The Windows build, deploy and launch cycle

The loop this skill runs on one Windows machine: prerequisites, the build and launch cycle, launch modes, the `dayz-test.ps1` orchestrator generated from `templates/`, default mods and admin tools, what `-filePatching` does and does not reload, and why mod paths must be absolute.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it. Tags such as `SP-078`, `LL-196` and `CLAIM-...` are the finding numbers of the knowledge pack this material came from; they are kept so that cross-references between files stay searchable. `DAYZ_INFRA.md` is that pack's infrastructure note (in this repo `skills/_shared/knowledge/environment-and-infra.md`); a tag like `[EXACT - DAYZ_INFRA.md §Section]` names the section of it that records the fact.

Measured results, tool behaviour and third-party mod behaviour (Community Framework, Dabs Framework, VPPAdminTools, dayz-mcp) in this file are not yet checked on `P:\` and most cannot be, because they are not vanilla script facts.

## WHAT THIS DOES

Closes the dev loop for a DayZ mod on a single Windows box: re-pack the PBO, deploy it
where the engine reads mods, and launch `DayZDiag_x64.exe` with `-filePatching` so script
and config edits are picked up without re-binarizing. Three launch modes (offline / server /
client / all) driven by one orchestrator script and double-click `.bat` wrappers, generated
per mod into `<Mod>_dev\tools\`.
(until 1.29: the loop was pack PBO → deploy packed `@Mod` → DayZDiag `-filePatching`.) (since 1.30 [CHANGELOG]: `-mod` may point at an **unpacked** source folder; RV configs load unpacked; new flags `-cacheP3D=0/1` and `-resolveFilePatchingUsingEnfusion=0/1`. Details: `dayz-1-30-test-ingame.md`.)

## WHEN TO USE / WHEN NOT

Use when the user wants to see a mod running in-game, iterate scripts/configs live, or stand
up a local server+client. Do NOT use to author the mod (that is `dayz-model-pipeline` /
`enforce-script-reference`), to validate/pack only (`/dayz-build-pbo`), or to configure a
production server. The retail `DayZ_x64.exe` is for final pre-release validation only -
default to the diag exe. Retail is manual-only and external to this launcher.
On this box retail does not load mission (LL-479): B-4 accredits 3_Game+4_World and 5_Mission
only compiles in diag; coverage is written per module in the matrix, never "B-4 green".

## PREREQUISITES (preflight - runs automatically)

### Step 0 - offline linter, BEFORE wasting a startup

A startup cycle costs minutes; linter costs ~60 s and catches cold what you would otherwise
discover reading an RPT:

```
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Gate on **`len(errors)`**, never on `status` (`WARN` with zero errors is valid).
 The path is **relative to the Agentic-Z repo root**, not your mod folder: from a mod directory
give the absolute path to the repo checkout, or the command dies with
`No such file or directory` and reads as "not installed". `/dayz-lint` checks the mod setup;
this validator checks the code itself.
 Compare against
base to know if error is yours. **Does not substitute startup** - Enforce only compiles on loading
the world, and this linter does not see that - but `errors > 0` means startup will fail and
there is no need to launch it to find out. Mandatory if change deletes classes, files, or
`config.cpp` entries.

⚠ **MEASURED blind spot, costing an entire startup: linter DOES NOT see an undeclared
variable.** An `obj.m_Field` where type of `obj` does not declare `m_Field` exits with **0 errors**
and zero delta, and upon world load module dies with `Cant compile "World" script module!` +
`ACCESS_VIOLATION`. Measured 2026-09-08 in LFPowerGrid: SAME tree passed this gate in **12
lanes** and again on merged `main`; an adversarial review from another family did not
catch it either, because read in a diff an incrementing counter looks reasonable. The case:
`tRnd.m_Projections` on a `LFPG_RenderMetrics`, field existing on `LFPG_PreviewMetrics`
- the adjacent class in same file. **Useful asymmetry**: SERVER started fine because
that code was on render path; a gate looking only at its log gives green to this.

Cheap sweep that catches it, before wasting startup when touching many files: for
each typed local `Type obj = ...` in diff, check that each `obj.m_Field` is declared in
`Type` or its parents, resolving inheritance with regex census of `class X : BASE {...};`
across all `scripts/`. Measured: 145 classes and 32 files in ~2 s. Only covers locals with explicit
type - does not see member accesses, function returns, or `this` - but covers this pattern.

The orchestrator checks these every run and fixes what it safely can. Verified on this box
2026-05-30: missions present in DayZServer, AddonBuilder present, `P:\` mounted, but
`P:\Mods` junction NOT yet created and `DAYZ_*` env vars unset (fallbacks used).

- **Diag exe** - `DayZDiag_x64.exe`. Client AND server MUST be the diag binary; retail blocks
  past the loading screen with `-filePatching`. [EXACT - DAYZ_INFRA.md §Mandatory diag binary for iteration]
- **`P:\Mods` junction** -> `<DayZ>\!Workshop` so deployed PBOs land where the engine looks.
  The script creates it via `mklink /J` if missing (no admin needed). [EXACT - DAYZ_INFRA.md §Drive and mod layout]
- **`allowFilePatching = 1`** in the server's `serverDZ.cfg`, else BattlEye kicks the client
  with `0x00020005`. The script generates a dev `serverDZ.cfg` with it set. [EXACT - DAYZ_INFRA.md §serverDZ.cfg - allowFilePatching = 1; mandatory]
- **Mission template** - absolute path; the server loads an empty mission otherwise. (Windows and DayZDiag. The native Linux `DayZServer` is the opposite, see `linux.md`.)
  [EXACT - DAYZ_INFRA.md §Canonical invocation commands - Server diag]. Aliases:
  `chernarus`/`livonia`/`sakhal`. [EXACT - DAYZ_INFRA.md §Mission templates - canonical aliases]
- **`class Missions` in `serverDZ.cfg`** - a dedicated server with a `dayzOffline.*` mission self-terminates before the mission loads (RPT countdown `[Server] :: termination in: N`) unless the config declares `class Missions { class DayZ { template="<mission>"; }; };`. With it, the server stays up with no client, which is what a server-side probe in the mission `init.c` needs. [EXACT] (measured in game, DayZ 1.30.164014 Exp, SP-434]
- **`instanceId` in `serverDZ.cfg`** - keep it: without it a minimal config got the same countdown even though it declared `class Missions`. On the retail DayZServer 1.30.164289 (Windows, 2026-11-10) a hand-written `serverDZ.cfg` with `class Missions` and no `instanceId` counted down from `[Server] :: termination in: 10` right after `NETWORK : server: Player dpid=2 added`, with no `SteamGameServer_Init` line; the same file plus `instanceId = 1;` and nothing else passed Steam init, loaded the mission and ran until a test mod asked it to exit. Only `instanceId` was tested: whether another key of the shipped `serverDZ.cfg` would also avoid the countdown is unknown. The dev `serverDZ.cfg` the script generates already sets it (the generated config block of `templates/dayz-test.ps1`). [EXACT][CLAIM-TEST-SERVERCFG-INSTANCEID-130]
- **AddonBuilder** - only when `-Build`. [EXACT - DAYZ_INFRA.md §Canonical invocation commands - AddonBuilder]
- **Steam client session** - for CLIENT-launching modes only (`offline`, `client`, `all`),
  `HKCU\Software\Valve\Steam\ActiveProcess` must have both `pid != 0` and
  `ActiveUser != 0`. The script warns without aborting; run `steam.exe -shutdown`, then relaunch
  Steam (the login is preserved), both from outside any sandboxed (MSIX) app (SP-095 point 1-ter
  in `managed-launcher.md`). [DESIGN] Restart is NOT the reliable remedy: measured 2026-09-08/09, a restart can leave the key pointing at the old pid with the client still dead - the deterministic fix is to copy the live `steam.exe` pid into `ActiveProcess` from a shell OUTSIDE any sandboxed (MSIX) app - a write from inside one only reaches that app's private registry copy, see `dayz-1-30-test-ingame.md` - (guards and verification in "Steam `pid` in registry can be DEAD" in `troubleshooting.md`), and restart only as a fallback when there is no live Steam or `ActiveUser == 0`.

- **Mod set is SEALED, and changing it WIPES test world** (since 2026-09-06,
  measured in game). Each server startup seals its effective mod list in
  `<mission>\storage_1.modset.json` (`seal` field, sha256). If seal changes relative to previous
  startup, startup **archives `storage_1`** into `storage_1.modset-<ts>-<seal8>` (with its
  `.marker.json` and a `…rotation.<hash>.completed.json` receipt) and starts fresh: **world, bases, and
  test characters, gone**. Measured: repeating same set DOES NOT rotate and seal does not move;
  changing it rotates **exactly once**; repeating new one does not rotate; and `mode=client` on live run
  does not rotate either - rotation lives in SERVER startup.
  - **Consequence for anyone alternating stacks** (testing your mod, then next one, then yours):
    you lose test persistence on each hop. If you need to preserve it, **copy
    `storage_1` manually beforehand**; archived ones all remain as siblings in mission directory.
  - **Rotation DOES NOT leave a row in audit log** (known defect, emitter swallows its
    exceptions silently). If one day you lose the world and look for why, check via
    `storage_1.modset-*` folders and `seal` field, not audit log.
  - **It is deliberate and fixes something worse**: previously, that same stack hop corrupted savegame.
    Measured 2026-09-04 with previous bundle, an A→B hop produced **43,197** lines of
    `Scripted variables corrupted`; with seal, both signatures (`Failed to read modstorage` and
    `Scripted variables corrupted`) exit at **0**. Caution when diagnosing: in that repro the signature
    appearing was NOT the one incident entry proposed watching; watch **both**.
  - **Format trap**: `extra_mods` is a **list**, not a string with `;`. A
    `["@CF;@VPPAdminTools"]` passes validation and then does not exist as folder: silent red.
  - Via MCP route, expired Steam session from previous point manifests as
    `dayz_test_run` dying in `validating` phase at ~1.3 s with `error_code: "steam_session_stale"`;
    remedy is the same (restart Steam, login is preserved).

Path resolution is env-var-first, Steam-default fallback (`DAYZ_GAME_PATH`, `DAYZ_DIAG_PATH`,
`DAYZ_TOOLS_PATH`, `DAYZ_WORK_DRIVE`). [EXACT - DAYZ_INFRA.md §Optional environment variables (resolvers)]

## THE CYCLE

1. **Build + deploy** (`-Build`) - `AddonBuilder P:\<Mod> -> P:\Mods\@<Mod>\Addons\<Mod>.pbo`.
   Required whenever **assets** (`.p3d`, `.paa`, `.rvmat`) change - filepatching does not
   reliably hot-load binarized models/textures.
   **Scripts-only mods**: AddonBuilder's default binarize mode drops `.c` files (not in its
   include-list) → a config-only PBO where the mod mounts but no script runs. `Invoke-Build`
   now auto-adds `-packonly` when the source has no `.p3d`/`.paa` (force with `-PackOnly`), and
   warns if a mod with a `scripts\` folder packs suspiciously small. [verified 2026-06-03]
   **`.asi`/`.anm` (added 2026-06-24, A6_SR2M)**: binarize mode ALSO drops these unless the
   `-include` list has `*.asi;*.anm`. A weapon with a custom player anim graph
   (`AddItemInHandsProfileIK` 2nd arg = its own `.asi`) then builds WITHOUT the graph → the
   reference points at a missing file and the change (e.g. a fire-anim no-jump fix) is silently
   absent (the build still reports success). The generated include list must contain
   `*.asi;*.anm`. Verify the `.asi`/`.anm` shows up as a FILE ENTRY in the PBO header, not just
   as a string inside the compiled script.

   **Mixed mods (assets + scripts, SP-083, added 2026-07-22, LFPowerGrid)**: auto-`-packonly` does
   NOT apply when `.p3d`/`.paa` are present - `Invoke-Build` and `dayz-test.ps1 -Build` never pass
   `-include` (only -prefix/-temp/[-clear]/[-packonly]), so binarize still silently drops
   `.c`/`.paa`/`.ogg`/`.rvmat`/`.layout`/`.csv` - the PBO mounts with zero scripts running.
   The "packs suspiciously small" warning (<4096 B) misses it: binarized `.p3d` keep the PBO
   large (measured 95.1 MB / 170 files; with include-list 451 files / 106.8 MB). Production:
   AddonBuilder <src> <out> -prefix=<Mod> "-temp=<tmp>" "-include=<lst>" -clear with
   lst = `*.c;*.asi;*.anm;*.paa;*.rvmat;*.layout;*.ogg;*.ptc;*.csv`. Mandatory post-build gate:
   count PBO entries (PboViewer unpackFolder) or grep a known `.c` (170 vs 451 = drop).
   Complements SP-065. Cross-ref `/dayz-build-pbo`.

   **Mixed mods, migration (SP-168, added 2026-08-04, GunRacks)**: the real failure mode
   is MIGRATION. Measured on GunRacks: **22 entries / 401.857 B without the include-list,
   25 entries / 411.786 B with it** - the gap is exactly the three `.c`. The project's
   documented hand command already passed `-include=...\tools\include.lst`
   (in that project's plan and handoff notes); that `include.lst` was created by
   hand. GENERATING THE SCRIPTS FOR A MOD copies only `dayz-test.ps1` plus the three
   `.bat` wrappers - it does not write `include.lst`. `Invoke-Build` still does not pass
   `-include`, so switching from the hand command to `server.bat` / `dayz-test.ps1 -Build`
   drops every script with no visible change (PBO still large; the <4096 B warning never
   fires). In-game the mod mounts but no action appears - indistinguishable from an
   unregistered ActionConstructor or a bad ActionCondition, so the wrong file gets
   debugged. Caught by listing the freshly built PBO before spending a test cycle.
   In `Invoke-Build`, pass the include-list when it exists and the build is not packonly:
       $incLst = Join-Path $PSScriptRoot 'include.lst'
       if (-not $usePackOnly -and (Test-Path $incLst)) { $abArgs += "-include=$incLst" }
   Replace the size check (`scripts\` present and PBO < 4096 B) with a CONTENT check:
   if the source has `scripts\`, list the PBO and require packed `.c` count == source
   `.c` count. `GunRacks_dev\tools\pbo_list.py` is the lister. Cross-ref
   `GunRacks_dev\tools\dayz-test.ps1` Invoke-Build (patched locally; the measurement
   is in the comment). Complements SP-083.
2. **Launch** - diag exe in the chosen mode. **Script/config** edits (`.c`, `.cpp`) are then
   picked up live by `-filePatching` without re-packing.

So: edit a model -> re-run with `-Build`. Edit a script -> just relaunch (or even keep the
client running, depending on what changed).

## RELEASE-GRADE BUILD BOUNDARY

[EXACT][CLAIM-R21-TEST-BUILD-POSTCONDITION] `exit_0_is_not_build_success`.
AddonBuilder can leave an old destination PBO in place after a later copy step
fails, so process exit and `Test-Path` alone do not prove that the requested
bytes were built or deployed. A release verdict requires evidence for a
`fresh_pbo`, the expected `header_prefix` and file entries, and a clean
`fatal_log` scan; require a valid `.bisign` too when signing is expected.

[DESIGN] The Phase 04 release workflow must stage the candidate outside the
published path, validate it, and publish only after every gate passes. On any
failure, require `previous_artifact_unchanged` and do not advance the build
manifest or cache. Its cache key must cover input bytes, build options, prefix,
DayZ build, tool versions/hashes and signing-key identity. Its preflight must
reject case/path conflicts, excluded-but-referenced files, absolute packaged
paths, stale or missing `.paa` dependencies, and unsupported ODOL inputs before
binarization.

The current generated dev launcher does not yet implement that complete
release contract. Use its PBO for iteration, but do not label the result
release-ready until a build and release pipeline
(`/dayz-build-pbo`, `/dayz-gate build`, `/dayz-release-pack`) supplies these postconditions.

## MODES

| Mode | What | Status |
|---|---|---|
| `all` (default) | server, wait for UDP bind, then client | [EXACT - DAYZ_INFRA.md §Canonical invocation commands - Server diag + Client diag] |
| `server` | `DayZDiag_x64.exe` managed with `-server` | `managed_lifecycle=true`; [EXACT - DAYZ_INFRA.md §Canonical invocation commands - Server diag] |
| `client` | diag `-connect=127.0.0.1` (server already up) | [EXACT - DAYZ_INFRA.md §Canonical invocation commands - Client diag] |
| `offline` | single diag with `-mission`, no network | **[DESIGN]** validate in-game |

## USAGE

Orchestrator (from `<Mod>_dev\tools\`):

```powershell
# build, deploy, run server+client on Chernarus
.\dayz-test.ps1 -Mod HiddenBase -Mode all -Build

# script-only change: relaunch client, no re-pack
.\dayz-test.ps1 -Mod HiddenBase -Mode client

# offline eyeball of a model [DESIGN]
.\dayz-test.ps1 -Mod HiddenBase -Mode offline -Build

# another map + an extra dependency on top of the defaults (CF/Dabs/VPP)
.\dayz-test.ps1 -Mod LFPowerGrid -Mode all -Build -Mission livonia -ExtraMods "@RaG_Liquid_Framework"

# preflight only / stop one exact managed run
.\dayz-test.ps1 -Mod HiddenBase -Preflight
.\dayz-test.ps1 -Mod HiddenBase -Kill -RunId <run_id>
```

Key params: `-Mod` (required), `-Mode`, `-Mission`, `-Build`/`-Clean`, `-ExtraMods`,
`-BaseMods`/`-NoBaseMods` (see below), `-Source` (default `P:\<Mod>`), `-RunId`,
`-NoFilePatching`, `-Port`, `-PlayerName`, `-ServerWait`. Double-click wrappers:
`server.bat` (all+build), `client.bat`, `offline.bat`.

## DEFAULT MODS & ADMIN TOOLS

Every launch prepends three base mods (load order, CF leftmost - folder names verified in this
user's `!Workshop`): `@CF;@Dabs Framework;@VPPAdminTools`. The mod under test and `-ExtraMods`
load after them. Override with `-BaseMods "..."`, or drop them entirely with `-NoBaseMods`.

`@VPPAdminTools` gives in-game admin tools (teleport, spawn, godmode, object editing) for
testing. Admin access is by **SteamID64**, not a server password - but the on-disk layout
differs across VPP versions, and the installed one uses the `Permissions\` folder, NOT the root
`SuperAdmins.json`. Because this script isolates `-profiles`, the preflight seeds **both** so
admin works regardless of version (idempotent; an already-hashed password is never clobbered):

- `<server profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` - one SteamID64 per
  line; the file the installed VPP actually reads. (verified in-situ 2026-06-09)
- `<server profiles>\VPPAdminTools\Permissions\credentials.txt` - the **in-game login
  password** on line 1. VPP hashes it on first boot and the raw is then lost.
  [EXACT][CLAIM-R21-TEST-VPP-SECRET] There is no packaged default. It is seeded
  only when the operator explicitly supplies non-empty `-AdminPass`, and its
  value is never printed.
- `<server profiles>\VPPAdminTools\SuperAdmins.json` - `{ "SUPER_ADMINS": ["<SteamID64>"] }`,
  the legacy layout; still seeded for older VPP builds that read it.

SteamID source: `-AdminSteamId`, else reused from the retail config at
`%LOCALAPPDATA%\DayZ\VPPAdminTools\SuperAdmins.json`. In-game: open the VPP menu (key set under
Options → Controls; VPP's common default is Insert), then log in with the password. To change
admin or password later, edit the files above and restart the server.

**No-password dev default (verified vs VPP source 2026-06-09):** the generated `serverDZ.cfg`
sets `vppDisablePassword = 1;`, so VPP skips the login password entirely - a superadmin (SteamID
in `SuperAdmins.txt`) gets access with NO password (`missionServer.c:14` →
`DisablePasswordProtection(true)`; granted because `HasUserGroup`→`IsSuperAdmin`,
`PermissionManager.c:693`). This is the robust local-dev default: the `credentials.txt` password
path repeatedly failed across sessions (SHA256/version quirks), and disabling it removes that
whole failure class. An explicitly seeded `credentials.txt` password only matters if you remove
`vppDisablePassword` for password-gated testing. In-game keys: End = toggle admin, Home = open
menu (rebind under Options → Controls if a fresh client profile lost them).

Earlier this doc claimed VPP reads the root `SuperAdmins.json` - that was wrong for the installed
build (it reads `Permissions\`), which is why admin silently failed until 2026-06-09.

The dev `serverDZ.cfg` sets `verifySignatures = 0`, so VPP's signed PBO loads without registering
its `.bikey`.

## GENERATING THE SCRIPTS FOR A MOD

1. Create `<Mod>_dev\tools\` if absent (the source pack keeps dev tooling in a `<Mod>_dev` folder next to the mod source).
2. Copy `templates\dayz-test.ps1` there verbatim - it is fully generic (driven by `-Mod`).
3. Copy the three `.bat` wrappers and replace the `__MODNAME__` placeholder with the real mod
   name (the CfgPatches identifier - no dashes; `My_Mod`, not `My-Mod`). [EXACT - DAYZ_INFRA.md §Drive and mod layout - Mod naming]
4. Confirm the mod **source** is reachable at `P:\<Mod>` (a junction to the editable folder)
   or pass `-Source`. Confirm `requiredAddons` in `config.cpp` map to the `-ExtraMods` you
   pass (CF, Expansion, etc.) - the client and server mod lists MUST match.

The `.ps1` is self-contained (no dependency on this skill at runtime) so it stays valid in the
mod repo even if the skill changes. `_server\` and `_client\` workspaces (serverDZ.cfg, RPT,
script.log) are created next to `tools\` under `<Mod>_dev\`.

## FILEPATCHING SCOPE - read before promising hot-reload

`-filePatching` hot-loads **scripts and configs** from raw source in the general case, not
binarized assets. Model/texture/material changes need a `-Build`. Do not tell the user "just
edit and it reloads" for a `.p3d` or `.paa` change - that is the most common false expectation
here. **On this install even scripts do NOT hot-load - the PBO wins** (measured 2026-07-20);
see the SP-078 section right after this one and use the `srcprobe` discriminator before
attributing anything to filepatching.

## Script changes NEVER hot-load from the work drive on this install - the PBO wins; rebuild the PBO for every script iteration (SP-078, added 2026-07-20)

Measured 2026-07-20 (LFHeli toggle diagnosis): with `-filePatching` on server AND client, `allowFilePatching=1`, work drive mounted and `P:\<prefix>\scripts\...` present, the engine still compiled the scripts FROM THE PBO. Probe prints existing only in the source tree never appeared over two boots; after `dayz-test.ps1 -Build` (packonly repack) the same prints appeared immediately. Consequences:

1. "Iterate scripts without repacking" does NOT work here. Every Enforce change needs a PBO rebuild (packonly, seconds) + relaunch. Treat the PBO as the only script source of truth.
2. Loose-file MODEL/texture shadowing is equally unproven on this install - do not attribute stale visuals to (or expect fresh visuals from) work-drive loose files; verify what the engine runs, do not assume filepatching semantics.
3. **The srcprobe discriminator** (cheap, definitive, one boot): change a LOG STRING in an already-printing line in the SOURCE only (e.g. `[TAG]` -> `[TAG srcprobe]`), relaunch WITHOUT rebuilding, grep the script log: token present = source served; absent (old string still printing) = PBO served. Use it before wasting cycles on "why doesn't my script change do anything".

Origin: 3 boots lost to probes that were "deployed" but never in the runtime; the PBO-wins fact then explained an earlier red herring the same day (a stale `P:\LFHeli\models` tree suspected of shadowing the deployed model - it never did).

## MOD PATHS MUST BE ABSOLUTE - silent no-mount otherwise (verified 2026-06-01)

A bare `-mod=@Name` is resolved by the engine **relative to its working directory** (the game
dir), i.e. `<DayZ>\@Name`. Deployed mods live under `<DayZ>\!Workshop\@Name`, so that relative
path does not exist and the engine **silently fails to mount the addon** - its `CfgPatches` /
`CfgVehicles` classes never register, and `CreateObjectEx` later returns **null with no RPT
error**. This is a brutal failure mode: the server boots, the mission runs, nothing logs wrong,
but your mod's classes simply aren't there.

Verified via an in-mission `ConfigIsExisting("CfgPatches LFQuad")` probe on a headless `-server`:
- `-mod=@LFQuad` (relative, cwd=game) → `CfgPatches.LFQuad = 0` (absent).
- `-mod=C:\...\DayZ\!Workshop\@LFQuad` (absolute) → `CfgPatches.LFQuad = 1`, `LFQuad_base = 1`.

That was measured on Windows, and the failure is not always silent:
- A relative path that climbs out of the server folder with `..\` does not mount either, and it is loud: the retail
  DayZServer 1.30.164289 (2026-11-10, in `-serverMod`) stopped loading at an error window
  `Cannot open file '<server>\..\..\…\@Name\addons\<pbo>'`, wrote an `ErrorMessage_DayZServer_x64_<date>.mdmp` into the
  profile folder and never reached the mods' `PBO Load` lines; its RPT says nothing about it.
  [EXACT][CLAIM-TEST-MODPATH-DOTDOT-130]
- On the native Linux server the rule is reversed: an absolute `-mod=` / `-servermod=` path mounts nothing and
  gives no error, so the paths go relative to the server tree. Evidence and the launch line:
  `linux-native-server.md`, section 3.

`Get-ModString` now rewrites every bare `@Name` to its absolute `!Workshop` path via
`Resolve-ModToken` (handles names with spaces like `@Dabs Framework`; passes through tokens that
are already rooted or not found under `!Workshop`). This applies to server, client and offline.

Caveats (honest scope - not yet verified):
- The probe only confirmed the **mod-under-test** mount. Whether base mods mount under relative
  names in the `all` mode (client present) was NOT isolated - the fix makes it moot by resolving
  all of them to absolute.
- Checking a dependency's mount needs its **real CfgPatches name**, not the folder name:
  `@CF` → `JM_CF_Scripts` (verified by extracting `@CF\addons\scripts.pbo`). A probe using `"CF"`
  yields a false negative.

## OUT OF SCOPE

Authoring the mod, production server config (stock 1.30 formats: `server-and-mission-config.md`), Central Economy / persistence tuning beyond the
minimal dev `serverDZ.cfg`, signing for Workshop release. PBO validation/packaging internals
belong to `/dayz-build-pbo` / `/dayz-release-pack` - this skill calls
AddonBuilder and records their required handoff contract; it does not re-implement the checks.

## REFERENCES

- `skills/_shared/knowledge/environment-and-infra.md` (the pack's `DAYZ_INFRA.md`) - canonical paths/flags/gotchas (the source this skill serves).
- `/dayz-build-pbo` - pre-build validation + packaging.
- `dayz-mod-workflow` - debug protocol when a launch surfaces script/engine errors.
- `templates\dayz-test.ps1`, `server.bat`, `client.bat`, `offline.bat` - the generated tooling.

## Session findings (dated appendices -> session-findings.md)

Per-session in-game gotchas moved to `session-findings.md`; load it when a launch hits one of these. One line each:

- **LFSlidingFloor (2026-06-11)** - `Print()`->script.log not RPT; `-filePatching` can compile WITHOUT the mod's scripts silently; VPP needs `@CF` first; 1 Steam acct = 1 client (kick 179); deployed PBO locked while server runs.
- **A6_SR2M grip (2026-06-17)** - visual capture on retail (brightness band, specular glint, exposure drift, multi-config desync, RPT error filter) + `Start-Process EPERM uv_spawn` in a backtick `foreach`.
- **MercedesAMGLF Phase 0 (2026-06-22)** - cheap mount-probe gate (CfgPatches existence) before physics autotest; retargeting the LFQuad physics harness (server-only no-spawn, phantom debug token, control-vehicle verdict, case-insensitive `-replace`).
- **Retargeting the harness to a new mod (2026-06-23)** - `dayz-test.ps1` is car-parametric (copy verbatim); only per-mod helpers need a case-sensitive token swap; retarget host-direct.
- **The box is a coordinated resource (2026-06-24, superseded 2026-07-15)** - one DayZ instance per box (UDP 2302); FIFO lease serializes mutations and the exact `run_id` identifies a lifecycle; mod and profile names give no ownership.
- **`@<Mod>_deps` separate dep addon (2026-06-26)** - put deps in `-BaseMods` (loads first) or the client fails `Unknown type` at compile; replicate the last successful `-mod=` from the RPT.
- **Third-party "sloppy" scripts (2026-06-28)** - deps that only warn on retail but fatal-compile on diag require a user-owned external manual parity run; agent stays in quarantine.
- **Launching DayZDiag from the agent (2026-06-28, superseded 2026-07-15)** - background tool-jobs can lose their child; use the Diag-only managed launcher and its exact run instead of an unmanaged process.
- **H2R import (2026-10-24)** - some DayZDiag 1.30 runs never load their textures while their error counts read normal (compare the run's median JPEG size with a textured run of the same framing, the RPT warning set being specific to that probe, and relaunch); the vehicle 1PP eye rides the `Head` bone and moves between runs and looks: log it at every look.

## The rest of the mod loop

Testing is one step of the loop in the `dayz-mod-dev` skill (look up, write, build, boot, verify, publish), which also routes a failing mod to the domain skill that owns the broken part.
