# DayZ test-in-game — Session findings (dated appendices)

Per-session in-game findings kept out of `../SKILL.md` for length; each was verified in the session it names and is reusable across mods. Load on demand when a launch surfaces the matching symptom.

These are measured results from third-party mods (VPPAdminTools, Community Framework, Dabs Framework, the A6 packs), the DayZ executables, the third-party dayz-mcp tooling and the `dayz-test.ps1` harness in `../templates/`. They are not yet checked on `P:\`. Vanilla script facts are cited inline with their `P:\scripts\` path and were re-opened there for this file. On Windows in this repo the launch, stop and log jobs are `/dayz-launch-test`, `/dayz-stop-test` and `/dayz-logwatch`; flags such as `-Mode`, `-BaseMods` and `-NoFilePatching` below belong to `dayz-test.ps1`.

---

## LFSlidingFloor session findings (added 2026-06-11)

Origin: session 2026-06-10 (R21 + in-game test of 2 spikes). Five verified gotchas of diag flow:
- **Print() goes to script_*.log, NOT to RPT**: in DayZDiag script Prints go ONLY to script log (retail server: RPT). Gates/monitors saying "RPT" must be translated to real runtime. Minimal probe: a Print in OnInit of a modded MissionServer confirms sink AND mod hook without requiring client (see LL-137).
- **-filePatching does NOT guarantee loading mod scripts from work drive**: verified 2026-06-10 — with -filePatching and an empty PBO, modules compiled WITHOUT mod files and WITHOUT error (World 2240 vs 2245 expected). Detection: compare counts "Module: X; loaded Nx files" of script log against reference run (+N mod files). Mitigation: -NoFilePatching (ALWAYS load from content-verified PBO).
- **VPPAdminTools REQUIRES @CF in front in -mod**: without it, modal popup "Unknown type 'RPCManager'" (Can't compile Game module) that BLOCKS server waiting for click — no useful trace if nobody looks at desktop. To read invisible dialogs: EnumWindows + GetWindowText via PowerShell.
- **1 Steam account = 1 client**: second simultaneous DayZDiag (same SteamID, distinct -name and -profiles) receives kick 179 (the message says a request has already been sent for this SteamID; seen on a Spanish-language client). MP observer tests need second account or second PC.
- **Deployed PBO remains LOCKED while server runs**: AddonBuilder -clear and final copy fail ("Build failed" as last line with rest of log normal). Close server and client BEFORE redeploy.

## A6_SR2M grip session findings — retail visual capture + Start-Process (added 2026-06-17)

Reusable patterns when testing in-game with **camera visual capture** (`gate-mcp.ps1` style gate:
retail server+client + camera bridge + window-grab by orbit). Mod-independent.

**Visual capture (retail):**
- **Brightness band.** Retail world renders brighter (~109–126) than diag band `[48,86]`,
  so an "in-world ready" gate by brightness gives false-negative in retail and only captures after
  timeout. Use a retail band (e.g. `[110,175]`) so it confirms quickly, or judge by content.
- **Specular glint.** With direct sun (clear time) some weapons/materials burn out to white and
  cover hand/detail. Setting `overcast=1.0` (overcast sky → diffuse light, no direct sun) eliminates it.
- **Exposure drift.** In long runs exposure drifts between first capture and last ones
  even if scene is "frozen". Capture all variants QUICKLY (short cycle) for even
  exposure among them.
- **Desync in multi-config cycles.** If "in-world ready" timeout per config is GREATER than
  period at which init changes config, capture falls into NEXT config (corrupt labels
  — happened in iter18). Keep timeout per config < period, and start cycle only after boot.
- **RPT check for errors.** Do NOT include `"Can't load"` in failure pattern: matches BENIGN
  warning `Can't load @Mod/Anims/cfg/skeletons.anim.xml`, which appears for ALL mods (generic probe
  per-mod). Look for real errors (`Unknown type`, `Cannot create`, `compile mission`) excluding
  `skeletons.anim.xml`.

- **DayZDiag client window hides itself (added 2026-08-22).** Process is still alive and
  responding, but window changes to `visible=False`; then `Get-Process().MainWindowHandle`
  returns **0** and any script depending on it fails with "bad window rect 0 x 0". The
  window exists: must locate it with `EnumWindows` filtering by PID and discard server
  window by title (`*Console*`). The originating project did this in a capture-loop
  script (not included here).
- **PrintWindow (PW_RENDERFULLCONTENT) doubtful for UI layer (added 2026-08-22).** Refreshes
  3D scene, but in a 49-frame run the HUD region gave delta **exactly
  0.00** while user saw element changing on real screen. An EXACT zero in
  compressed JPEG is not "almost equal", it is the same pixel: suspect the instrument (`G3`).
  To measure animated UI use user's eye; PrintWindow is left for static composition.
  Do not replace with MCP `capture_screenshot`: it is host window-grab, not a bridge
  command (`skills/dayz-mcp-verify/references/drive_ladder.py`). Origin: LFVUI_Spike probe
  (49 JPEG frames and a frame-diff script, not included here).

**Start-Process in PowerShell tool (`EPERM uv_spawn`).** An inline command with `Start-Process` inside
a `foreach` and `ArgumentList` with backtick-quotes (`` `"$x`" ``) triggers, consistently,
`EPERM: operation not permitted, uv_spawn powershell.exe` (shell spawn fails, not the command).
Fix: write loop to a `.ps1` on disk and run it (`& script.ps1`), or use
`Start-Process -ArgumentList @('a','b','c')` (array, without backticks). A single inline `Start-Process` usually
works; `foreach` with backticks is what breaks.

## MercedesAMGLF Phase 0 session findings (added 2026-06-22)

Two reusable patterns when launching this harness on a new mod. Origin: MercedesAMGLF import, harness R21.

### Mount-probe pattern — Phase 0 gate, cheaper than physics autotest

For the first build→deploy→mount validation of a new mod, before model or physics exists, do not use physics autotest (spawn + measurement): use a minimal mount probe.

1. `CfgPatches`-only stub (`config.cpp` with `class CfgPatches { class <Mod> { requiredAddons[]={"DZ_Data"}; }; }` + `$PBOPREFIX$`), build with `-packonly`.
2. `dayz-test.ps1 -Mod <Mod> -Source <stub> -Mode server -Build -NoBaseMods` (isolates; stub only requires vanilla).
3. Mission whose `init.c` is a minimal `MissionServer` that on first `OnUpdate` (one-shot with flag) runs `GetGame().ConfigIsExisting("CfgPatches <Mod>")` and prints `[<MOD>-MOUNT] CfgPatches.<Mod>=0|1`. API form verified in vanilla: `g_Game.ConfigIsExisting(CFG_VEHICLESPATH+" "+type_name)` in `P:\scripts\4_world\systems\inventory\attachmentsoutofreach.c:82` (path with space).
4. Poll `script*.log` for `[<MOD>-MOUNT]` + `BankRev -lf` of deployed PBO to list content.

Speed key: an empty `void main()` in `init.c` (replaces vanilla) skips `CreateHive()`/CE, so mission loop starts in seconds instead of minutes (does not load ~20k loot items). Probe needs no client, unlike spawning a `CarScript`. Verified: AC0.1 MercedesAMGLF 2026-06-22, probe at ~50s, server-only headless, runner `dayz-mount-probe.ps1`.

### Retargeting LFQuad physics autotest to a new mod — coupling traps

`dayz-autotest.ps1` / `autospawn_init.c` / `*_verdict.py` inherited from LFQuad bring coupling that breaks silently when copying to another vehicle. Verified by R21 on MercedesAMGLF; before trusting retargeted harness, review all four:

- **Does not spawn in server-only.** `autospawn_init.c` gates spawn to `players >= 1` (a `CarScript` only simulates with player present). In server-only by default it never spawns → timeout without samples. Make `-WithClient` default/mandatory for physics run, or fail early if no client.
- **The dev build-gate requires a nonexistent debug token.** `Invoke-BuildGate` calls `Require-PboToken -Token '<MOD>-DBG'`; that token came from LFQuad in-vehicle instrumentation. A clean mod does not have it, and debug is not put into production → gate aborts a valid build. Replace with productive evidence (presence of expected `.c`/config via `BankRev -lf`).
- **PowerShell inline verdict does not validate control vehicle.** Verdict block of `.ps1` computes PASS with subject only; `*_verdict.py` does require control to settle (INVALID-RUN otherwise). As `.ps1` does not invoke `.py`, it can give PASS with absent/broken control and lose negative control value. Have `.ps1` invoke `.py` and respect its exit code, or port control gate to PowerShell.
- **PowerShell `-replace` is case-insensitive by default.** Retargeting `'LFQuad'`→`'<Mod>'` also rewrites `LFQUAD-DBG`→`<Mod>-DBG` and `[LFQUAD-DBG]`→`[<Mod>-DBG]`. Verify tokens after retarget (or use `-creplace` for case-sensitive ones).


## RETARGETING THE HARNESS TO A NEW MOD (added 2026-06-23)

`dayz-test.ps1` is fully car-parametric (it takes `-Mod` and has zero hardcoded mod tokens) — copy it
verbatim into a new mod's `tools` folder. Only the per-mod helpers carry the old mod name and need a
case-sensitive token swap: `dayz-autotest.ps1`, the mount probe (`dayz-mount-probe.ps1` plus
`mount_probe_init.c`, including its bracketed `MOD-MOUNT` print token), `autospawn_init.c` (the classname
and the `MOD_Wheel` attachments), the verdict parser (`mod_verdict.py`), and the `server`/`client`/`offline`
.bat wrappers (`set MOD=`). Generic p3d utilities (`lfq_*.py`, `fix_firegeo_mass.py`,
`measure_wheel_geometry.py`) copy verbatim.

Retarget host-direct (PowerShell `-creplace` plus `[System.IO.File]::WriteAllText` with UTF8-no-BOM), NOT
the bash sandbox (bindfs cache) and NOT the Write/Edit tool on a OneDrive `.py` (null-byte risk). After the
swap, grep the destination for residual old-mod tokens — it MUST be zero — and confirm the new tokens
landed (wheel attachment, classname, probe token, `set MOD=`). The CONTROL (`CivilianSedan`) is shared
across mods and never changes. Origin: SUB_BRZ harness retargeted from MERCEDES_AMGLF with 0 residuals.

## THE DAYZ BOX IS A SINGLE EXCLUSIVE RESOURCE ACROSS SESSIONS (added 2026-06-24)

One Windows box runs one DayZ instance at a time: a server binds UDP **2302**, and one Steam account = one client
(a second client gets kick **179**, already noted under LFSlidingFloor findings). This bites hardest with multiple
concurrent Cowork sessions each testing a different mod: every `dayz-test.ps1` launch runs `-Kill` (kills ALL
`DayZDiag_x64`) before starting, so whichever session launches last EVICTS the others — their server+client die
mid-CE. The readiness window (build + CE boot, 2-4 min) does not fit inside the ~1-min eviction cadence, so a smoke
can never complete while a second session keeps relaunching. The dayz-mcp `--client`/broker registration lets several
sessions hold MCP tools at once, but it does NOT share the game — it does not solve this.

Rule before launching when other sessions may be open: ensure EXACTLY ONE Cowork session owns the box. Kill residual
`DayZDiag_x64`, then watch ~40 s host-direct (PowerShell) for any relaunch — a foreign `DayZDiag` reappearing means
another session is still alive (its cmdline shows the other `@Mod`/profiles; trace its parent). After your own launch
connects, confirm the live `DayZDiag` cmdlines reference YOUR mod before trusting anything you observe. Origin:
MERCEDES_AMGLF Phase 2 smoke 2026-06-24 (SUB_BRZ + LFInfectedBig sessions evicted the box repeatedly; PIDs/start-times
flipped every ~1 min).

**Pre-launch ownership check (added 2026-06-28, MANDATORY — origin: a SUB_BRZ session blind-killed A6_SR2M's
dedicated server, evicting an active session, then a foreign relaunch killed the SUB_BRZ server mid-test).**
NEVER `-Kill` / blind-kill before checking who holds the box. Before any kill or launch:
1. List holders host-direct: `Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe' OR Name='DayZServer_x64.exe'"`
   and read each `.CommandLine` for its `@<Mod>` token and `-profiles=...<OtherMod>_dev` path. Also check
   `Get-NetUDPEndpoint -LocalPort 2302` for the actual binder.
2. If ANY holder references a DIFFERENT mod than the one you are testing → it is another live Cowork session.
   **Do NOT kill it.** Surface to the user ("port 2302 is held by @<OtherMod>; should I kill it, or is that session still active?") and
   wait for confirmation before evicting. Only auto-kill processes that are clearly YOURS (same `@<Mod>`) or
   confirmed stale by the user.
3. `DayZServer_x64.exe` (retail/dedicated binary) is a SEPARATE process from `DayZDiag_x64`: a DayZDiag-only kill
   misses it, and killing it evicts a retail-mode session. Cover both names when you legitimately clean up.
4. Killing a foreign DayZServer mid-write corrupts the shared `DayZServer\mpmissions\<mission>\storage_1` CE
   persistence → next boot dies on `!!! Serious stream damage detected during load` and exits before UDP bind.
   Remedy: rename `storage_1` (server regenerates a fresh one); better: don't kill foreign servers in the first place.
5. After your own launch binds, confirm the live cmdline references YOUR `@<Mod>` before trusting any in-game observation.


## (added 2026-06-26) Mods with dependencies in separate `@<Mod>_deps`: include them in modset

If mod has its dependencies in a SEPARATE addon (`@<Mod>_deps`, not bundled in `@<Mod>`), launch modset MUST include them or client fails to compile scripts: `Can't compile "World": Unknown type '<BaseClass>'`. Dependencies (base config and script classes) must load BEFORE the mod → put them in `-BaseMods` (which goes first in `-mod=`), not in `-ExtraMods` (which goes after the mod).

Before relaunching an already tested mod, do not assume default `-BaseMods`: read `-mod=` from last successful RPT/output (`<Mod>_dev\_client\profiles\*.RPT`, "Launch CLIENT" line) and replicate THAT modset.

Real example (A6_SR2M, 2026-06-26): launching without `@A6_SR2M_deps` → `Unknown type 'A6_Optic_Mount_Base' (a6_sr2m.c:77)` / "Can't compile World". Correct: `-BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@A6_SR2M_deps"`. Windows note: `P:\` may not be mounted in a new session → `subst P: "<real work drive path>"` before build/launch (in this repo: `/dayz-workdrive`).

## (added 2026-06-28) Third-party deps with "sloppy" scripts: use `-Retail -NoFilePatching`

If a third-party dependency (not yours, e.g. an A6 pack) emits `SCRIPT (W)` (warnings) in
retail but FATAL `SCRIPT (E)` in DayZDiag (unclosed braces, "missing function scope",
"Opened scope at the end of file"), test path with filePatching does NOT work for TWO reasons:

- **DayZDiag** is stricter: those retail warnings are fatal errors -> `Can't compile
  "World" script module!` -> Diag server dies ("Server process exited before binding").
- **Retail client + `-filePatching`** -> crashes upon CONNECTING: `Unhandled exception ... Access
  violation. Illegal read ... at 0x0` with callstack `CDPInitServer`/`CDPCreateClient`
  (minidump + `crash_*.log` in `_client\profiles`). Server remains healthy (`is connected`
  followed by `[Disconnect] -1`).

**Fix:** if your change is already packaged in PBO (you do not need script hot-reload),
launch with **`-Retail -NoFilePatching`**. filePatching is unnecessary with up-to-date PBO, and
removing it avoids both failures. The production replica (PBO + without filePatching) is also the
config with which mod runs on a real dedicated server.

```
dayz-test.ps1 -Mod <Mod> -Mode all -Retail -NoFilePatching -BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<Mod>_deps"
```

The current `../templates/dayz-test.ps1` refuses `-Retail` (it exits with "Retail lifecycle is manual-only and
quarantined"), so run this launch by hand with the same arguments; the command above is the form the finding was
measured with.

Verify connection without OCR: `Select-String 'is connected'` in server RPT (authoritative
signal) and new `crash_*.log` in client profile for failure (PowerShell
host-direct, not Monitor bash -> bindfs cache, LL-142). Origin: A6_SR2M bug#10, 2026-06-28.

## (added 2026-06-28) Launching DayZDiag from agent: use `cmd start`, NOT a background task — and bind-wait gives false-negative

Three verified gotchas when running an in-game smoke FROM the agent (tool calls), not by hand. Origin:
SUB_BRZ Phase 5 smoke 2026-06-28 (cost ~half a session). Cross-ref LL-168.

- **A `DayZDiag_x64.exe` started with `Start-Process` from an agent `run_in_background` task
  (or from the bind-wait of `dayz-test.ps1` itself run in background) DIES when that task/job
  finishes.** Harness kills job child processes upon closing: server drops midway through CE **WITHOUT
  leaving its own RPT** (binds 2302 and disappears), and client —if launched in another call— survives
  (symptom: `DayZDiag count = 1`, dead server). Confirmed x3. Previous note "Start-Process -PassThru
  without -Wait" is NOT enough when call runs in background. **Fix: launch server and client via a `.bat`
  with `start ""`** (independent process group, outside agent tree) — they survive across
  tool calls and write their RPT. Pattern: `srv.bat`+`cli.bat` with `start "" "DayZDiag.exe" -server ...`
  / `... -connect=127.0.0.1`, same modset (`-mod="...;@<Mod>;@DayZ_MCP"` with absolute `!Workshop` paths).
  Poll bind yourself (`Get-NetUDPEndpoint -LocalPort 2302`); to wait for connect use a
  **read-only** poller (without `Start-Process` inside, or on close it would kill the game).
- **The bind-wait of `dayz-test.ps1` gives FALSE-NEGATIVE** (seen at 240s): server DID bind 2302
  (`Get-NetUDPEndpoint` confirms it) but orchestrator "Timed out waiting for bind" → refuses to launch
  client AND kills server it had launched. Workaround: let `-Build` build PBO (that does
  work), ignore launch failure, and launch server+client manually via `.bat`.
- **The MCP bridge `version_state=legacy_blocked` ("poll did not include ver=") is only incomplete init**,
  NOT a version mismatch: turns to `ok` when server mission finishes loading (~1-2 min). Do not
  re-register server or redeploy because of that — wait and re-check `bridge_status` (refines eponymous
  row of `dayz-mcp-verify` skill).

## DayZ 1.30 — launch flags (added 2026-09-17, lane P15)

(since 1.30 [CHANGELOG]) New launch flags on DayZDiag / Workbench (not observed as strings in this extract; documented in the 1.30 Experimental modding changelog):

- `-mod` accepts an **unpacked** source folder (not only a packed `@Mod` with PBOs).
- `-cacheP3D=0` / `-cacheP3D=1` — disable / enable P3D cache.
- `-resolveFilePatchingUsingEnfusion=0` / `-resolveFilePatchingUsingEnfusion=1` — Enfusion path for filePatching.

(until 1.29: `-mod` was documented as packed `@Mod` folders.) Pair unpacked `-mod` with the filePatching caveats already in this file (empty-PBO compile, `-NoFilePatching` for production replica). Full notes: `dayz-1-30-test-ingame.md`.

## H2R import (2026-10): untextured runs and a moving 1PP eye (SP-470, added 2026-10-24)

Two ways a capture run misleads while its error counts look normal. Measured in the H2R import (2026-10):
dedicated server and windowed client on one PC, the client window grabbed with Windows Graphics Capture at
3841x2160, one JPEG a second (ffmpeg `-q:v 3`). MB is 10^6 bytes; script lines are 1.30's as unpacked on `P:\scripts\` (re-opened there), followed by the author's 1.29 line where it differs.

### Some runs never load their textures: judge the run before its frames

[EXACT][CLAIM-TEST-DIAG-UNTEXTURED-RUN-130] On DayZDiag 1.30.164.200, 2 of 7 runs on 2026-10-19 and 5 of 12 on
2026-10-24 drew the scene flat for most or all of the run (terrain, sky, vegetation as blocks, the mod's own
model; in some, part of it arrived late) while lighting and shadows still drew and the run ended normally.
The next run with the same server and client command line came back textured after 5 of the 7 flat runs (once
three flat runs came in a row), and two textured runs opened with 4 and 11 s of flat frames. No error flags
it: the client RPT and script log hold as many error lines as a textured run's. In all 24 captured runs of
this probe (Chernarus, 2026-10-15 to 24), though, every textured run's client RPT had three warnings and no
flat run's had all three: `MatMulti` on `atcbig_multi_5metal_plates_old_co.paa`, and `No components in` on
`cl_rock1.p3d` and on `muzzle_flash_pistol_fnp.p3d`; two mostly flat runs had one or two of them (other maps
not checked). Flat clients were also seen on 1.30.164014 (in part) and 1.29.163709 (dayz-characters
`references/character-rigging.md`). Cause unknown; window focus was not recorded (`SKILL.md`, SP-391), so it
is not ruled out. One observation from another project points at it (historical, not reproduced here): on
2026-10-23 a client launched by the managed launcher stayed flat for about 3 min and loaded its textures as
soon as the owner clicked into its window, and the managed tools do not give that window focus. Until focus is
ruled out, log the foreground window, or have a human click the client window, before judging frames.

- Signal: the run's median JPEG size, not a frame's: 0.36-0.45 MB for the 7 flat runs against 1.46-1.61 MB for
  the 13 textured runs whose view filled the window. The last four runs of 2026-10-24 drew the view in about
  72% of the window's width and height, and the textured one among them read 0.63 MB: compare runs with the
  same framing. Single frames overlap (night, late textures).
- For anything judged on its frames such a run is `SETUP_FAIL` (`SKILL.md`, "Validity of an automated run"):
  relaunch; do not tune a material, LOD or closure on it, nor fail a model for missing textures
  (`dayz-mcp-verify`) while the vanilla terrain and sky in the frame are flat too. Its script-side readings
  still count: two of the Lewis eye readings below come from flat runs.

### The 1PP eye is not a constant of the character class: log it in every run

[EXACT][CLAIM-TEST-1PP-CAMERA-HEAD-BONE] The vehicle 1PP camera,
`DayZPlayerCamera1stPersonVehicle` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`),
keeps its parent's placement: bound by position to the character's
`Head` bone (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera1stperson.c:15`), offset `"0.04 0.04 0"` (`:21`, bound at `:53-54`);
the binding fields `m_iDirectBone` and `m_iDirectBoneMode` are at `P:\scripts\3_game\dayzplayer.c:23-24` (same lines in 1.29 by the author's reading).
Item 5 of `skills/_shared/vehicles/rip-import.md` (the vehicles pack) rests on it.

[EXACT][CLAIM-TEST-1PP-EYE-PER-RUN-130] On DayZDiag 1.30.164.200, logged in the bike's model space at seven
fixed looks per run with the bike stopped (11 runs, 2026-10-16 to 24), the eye sat 5.4-6.1 cm from the `Head`
bone at every look (the offset is 5.7 cm long), and that bone moved while the rest held: the pelvis stayed
within 0.6 mm, with the bars at rest and the same rider clips swapped in, and the head ranged over 7.6 cm.

- Between runs with one class and command line: four runs pinned to SurvivorM_Lewis on 2026-10-19 put the
  eye at 1.479-1.493 m, one of them 8.5-9.4 cm to one side at yaw 0.
- Between looks: SurvivorF_Keiko held 1.401 m for six of seven looks on 2026-10-19, with black clipped shards
  where the handlebar and top clamp should be, and 1.474 m on the seventh, handlebar back; two runs pinned to
  Keiko on 2026-10-24 read 1.42-1.51 m, changing from look to look. In 5 of the 11 runs, though, the eye held
  within 1 mm over all seven looks, yaw ±45 included.
- Across classes: SurvivorF_Judy read Lewis's eye to 0.2 mm on 2026-10-19 and 3.7 cm lower on 2026-10-16.

Why the head moves, and what held Keiko at 1.401 m (not reproduced), is not established. It is not the
missing-mod case either (`SKILL.md`, the `-mod=` line check, point 2): the mod set and the pose swap were the
same in every run. Window focus, which changed client-side readings in SP-391 (`SKILL.md`), was not logged
in these runs either.

- Log the eye at every look of every run: `GetCurrentCameraTransform` (`P:\scripts\3_game\dayzplayer.c:1237`) through
  the vehicle's `WorldToModel` (`P:\scripts\3_game\entities\object.c:874`); the author read both at the same lines in 1.29. Compare first-person frames only between runs whose
  eyes match, and check offline 1PP geometry (dayz-vehicles, SP-248, SP-249) against the eyes the runs
  logged, not one eye per class.
- Pin the class anyway, to remove one variable; whether the class moves the eye is not established.
  [EXACT][CLAIM-TEST-PIN-CHARACTER-CREATECHARACTER] In a `modded class MissionServer`, override
  `PlayerBase CreateCharacter(PlayerIdentity identity, vector pos, ParamsReadContext ctx, string characterName)`
  (`P:\scripts\5_mission\mission\missionserver.c:499`, 1.29 `:486`; both spawn paths of `OnClientNewEvent` call it, `:573` and `:589`), set `characterName` from
  `CommandlineGetParam` (`P:\scripts\3_game\global\game.c:661`, 1.29 `:660`) behind the test flag (`SKILL.md`, "AUTOMATED in-game cell
  without pilot", point 1) and call `super`: all 7 runs that passed a class spawned it, and 17 runs without
  it drew 14 classes.
