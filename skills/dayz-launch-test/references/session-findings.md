# DayZ test-in-game: session findings (dated appendices)

In-game findings from real test sessions. Each was verified in a test session and is reusable across mods. Load this file when a launch shows the matching symptom.

These are measured results from third-party mods (VPPAdminTools, Community Framework, Dabs Framework, a third-party weapons pack), the DayZ executables, the third-party dayz-mcp tooling and the `dayz-test.ps1` orchestrator in `../scripts/`. They are not yet checked on `P:\`. Vanilla script facts are cited inline with their `P:\scripts\` path. On Windows in this repo the launch, stop and log jobs are `/dayz-launch-test`, `/dayz-stop-test` and `/dayz-logwatch`; flags such as `-Mode`, `-BaseMods` and `-NoFilePatching` below belong to `dayz-test.ps1`.

Several findings name helper scripts of a per-mod test harness (a physics autotest launcher, a mount-probe launcher, a mission `init.c` that spawns the subject, a verdict parser). Those helpers are not included in this repo; the findings describe traps to avoid when you write or copy such a harness.

---

## Five traps of the diag flow

- **`Print()` goes to `script_*.log`, not to the RPT.** On DayZDiag, script prints go only to the script log (on the retail server they go to the RPT). A gate or monitor that says "RPT" has to be read against the real runtime. Minimal probe: a `Print` in `OnInit` of a modded `MissionServer` confirms both the sink and the mod's hook without a client.
- **`-filePatching` does not guarantee that the mod's scripts load from the work drive.** Verified 2026-06-10: with `-filePatching` and an empty PBO, the modules compiled without the mod's files and without an error (World: 2240 files against 2245 expected). Detection: compare the `Module: X; loaded Nx files` counts of the script log with a reference run (the mod adds N files). Mitigation: `-NoFilePatching`, so the scripts always load from a PBO whose content was verified.
- **VPPAdminTools needs `@CF` before it in `-mod`.** Without it a modal popup "Unknown type 'RPCManager'" (Can't compile Game module) blocks the server until someone clicks, and leaves no useful trace if nobody looks at the desktop. To read a dialog you cannot see: `EnumWindows` and `GetWindowText` from PowerShell.
- **One Steam account is one client.** A second simultaneous DayZDiag with the same SteamID (different `-name` and `-profiles`) is kicked with code 179 (the message says a request has already been sent for this SteamID). Multiplayer observer tests need a second account or a second PC.
- **The deployed PBO stays locked while the server runs.** AddonBuilder's `-clear` and its final copy fail ("Build failed" as the last line of an otherwise normal log). Close server and client before redeploying.

## Retail visual capture and `Start-Process`

Patterns for testing in game with visual capture through a camera (a retail server and client, a camera bridge, and a window grab per orbit position). They do not depend on the mod.

**Visual capture (retail):**

- **Brightness band.** The retail world renders brighter (about 109-126) than the diag band `[48,86]`, so an "in-world ready" gate by brightness gives a false negative on retail and only captures after its timeout. Use a retail band (for example `[110,175]`), or judge by content.
- **Specular glint.** With direct sun (clear weather) some weapons and materials burn out to white and cover the hand or the detail. Setting `overcast=1.0` (diffuse light, no direct sun) removes it.
- **Exposure drift.** In long runs the exposure drifts between the first capture and the last, even with a "frozen" scene. Capture all variants quickly, in a short cycle, for even exposure.
- **Desync in multi-config cycles.** If the "in-world ready" timeout per config is longer than the period at which the mission changes config, the capture falls into the next config and the labels are wrong. Keep the timeout per config shorter than the period, and start the cycle only after boot.
- **RPT check for errors.** Do not include `"Can't load"` in the failure pattern: it matches the benign warning `Can't load @Mod/Anims/cfg/skeletons.anim.xml`, which appears for every mod (a generic probe per mod). Look for real errors (`Unknown type`, `Cannot create`, `compile mission`) and exclude `skeletons.anim.xml`.
- **The DayZDiag client window hides itself.** The process is still alive and responding, but the window changes to `visible=False`; `Get-Process().MainWindowHandle` then returns 0 and any script that depends on it fails with "bad window rect 0 x 0". The window exists: find it with `EnumWindows` filtered by PID and discard the server window by its title (`*Console*`).
- **`PrintWindow` (`PW_RENDERFULLCONTENT`) is doubtful for the UI layer.** It refreshes the 3D scene, but in a 49-frame run the HUD region gave a delta of exactly 0.00 while the user saw the element change on the real screen. An exact zero in compressed JPEG is the same pixel, not "almost equal": suspect the instrument. To measure animated UI, use the user's eye; `PrintWindow` is left for static composition. Do not replace it with dayz-mcp's `capture_screenshot`: that is a host window grab, not a bridge command (`skills/dayz-launch-test/scripts/drive_ladder.py`).

**`Start-Process` in the PowerShell tool (`EPERM uv_spawn`).** An inline command with `Start-Process` inside a `foreach` and an `ArgumentList` with backtick-quotes (`` `"$x`" ``) consistently triggers `EPERM: operation not permitted, uv_spawn powershell.exe` (the shell spawn fails, not the command). Fix: write the loop to a `.ps1` on disk and run it (`& script.ps1`), or use `Start-Process -ArgumentList @('a','b','c')` (an array, without backticks). A single inline `Start-Process` usually works; the `foreach` with backticks is what breaks.

## Mount probe and retargeting a physics autotest

Two patterns for bringing a test harness to a new mod.

### Mount probe: a first gate that is cheaper than a physics autotest

For the first build, deploy and mount validation of a new mod, before a model or physics exists, do not use a physics autotest (spawn and measurement). Use a minimal mount probe:

1. A `CfgPatches`-only stub (`config.cpp` with `class CfgPatches { class <Mod> { requiredAddons[]={"DZ_Data"}; }; }` plus `$PBOPREFIX$`), built with `-packonly`.
2. `dayz-test.ps1 -Mod <Mod> -Source <stub> -Mode server -Build -NoBaseMods` (isolated; the stub only requires vanilla).
3. A mission whose `init.c` is a minimal `MissionServer` that on its first `OnUpdate` (once, behind a flag) runs `GetGame().ConfigIsExisting("CfgPatches <Mod>")` and prints `[<MOD>-MOUNT] CfgPatches.<Mod>=0|1`. Vanilla uses the same form of the call, a config path with a space: `g_Game.ConfigIsExisting(CFG_VEHICLESPATH+" "+type_name)` in `P:\scripts\4_world\systems\inventory\attachmentsoutofreach.c:82`.
4. Poll `script*.log` for `[<MOD>-MOUNT]`, and run `BankRev -lf` on the deployed PBO to list its content.

What makes it fast: an empty `void main()` in `init.c` (replacing the vanilla one) skips `CreateHive()` and the CE, so the mission loop starts in seconds, not minutes (about 20k loot items are not loaded). The probe needs no client, unlike spawning a `CarScript`. Measured 2026-06-22: probe result at about 50 s, server only, headless.

### Retargeting a vehicle physics autotest to a new mod: coupling traps

A physics autotest written for one vehicle (a launcher script, an `init.c` that spawns the vehicle and a control, a verdict parser) carries coupling that breaks silently when it is copied to another vehicle. Review all four before trusting the retargeted harness:

- **It does not spawn in a server-only run.** The spawn `init.c` waits for `players >= 1` (a `CarScript` only simulates with a player present). In a server-only run it never spawns and the run times out without samples. Make the client mandatory for a physics run, or fail early when there is none.
- **The dev build gate requires a debug token that does not exist.** A gate that requires a `<MOD>-DBG` token in the PBO depends on in-vehicle debug instrumentation of the first mod. A clean mod does not have it, and debug code does not go into production, so the gate aborts a valid build. Replace it with evidence from the product (the expected `.c` and config files listed by `BankRev -lf`).
- **An inline PowerShell verdict that does not validate the control vehicle.** If the verdict block of the launcher computes PASS from the subject alone while the Python verdict parser requires the control to settle (INVALID-RUN otherwise), and the launcher does not call the parser, a run can pass with an absent or broken control and the negative control is worthless. Have the launcher call the parser and respect its exit code, or port the control gate to PowerShell.
- **PowerShell `-replace` is case-insensitive by default.** Retargeting `'OldMod'` to `'<Mod>'` also rewrites `OLDMOD-DBG` to `<Mod>-DBG` and `[OLDMOD-DBG]` to `[<Mod>-DBG]`. Verify the tokens after the retarget, or use `-creplace` for the case-sensitive ones.

## Retargeting the harness to a new mod

`dayz-test.ps1` takes `-Mod` and has no hardcoded mod token: copy it verbatim into a new mod's `tools` folder. Only per-mod helpers carry the old mod name and need a case-sensitive token swap: the autotest launcher, the mount probe and its `init.c` (including its bracketed `MOD-MOUNT` print token), the spawn `init.c` (the class name and the wheel attachments), the verdict parser, and the `server`/`client`/`offline` `.bat` wrappers (`set MOD=`). Generic p3d utilities copy verbatim.

Do the retarget directly on the host (PowerShell `-creplace` plus `[System.IO.File]::WriteAllText` with UTF-8 without BOM), not through a sandboxed bash whose view of the files is cached, and not with an editing tool on a `.py` in a OneDrive folder (null-byte risk). After the swap, search the destination for leftover old-mod tokens (there must be none) and confirm the new tokens landed (wheel attachment, class name, probe token, `set MOD=`). The control vehicle (`CivilianSedan`) is shared across mods and never changes.

## The test machine is a single exclusive resource across sessions

One Windows machine runs one DayZ instance at a time: a server binds UDP **2302**, and one Steam account is one client (a second client gets kick **179**, see "Five traps of the diag flow"). This bites hardest with several concurrent agent sessions, each testing a different mod. At the time of this finding every `dayz-test.ps1` launch killed all `DayZDiag_x64` processes before starting, so whichever session launched last evicted the others in the middle of their CE boot. The readiness window (build plus CE boot, 2-4 min) did not fit inside the eviction cadence of about a minute, so a smoke test could never complete while a second session kept relaunching. The current template no longer does that: `-Kill` requires the exact `-RunId` and stops only that managed run. The rule below still applies to any launch or kill done by hand. dayz-mcp's `--client`/broker registration lets several sessions hold MCP tools at once, but it does not share the game.

Before launching when other sessions may be open, make sure exactly one session owns the machine. After your own launch connects, confirm that the live `DayZDiag` command lines reference your mod before trusting anything you observe. In the measured case two other sessions evicted the machine repeatedly; PIDs and start times flipped about every minute.

**Pre-launch ownership check.** In the measured case one session blind-killed another mod's dedicated server, evicting an active session, and then a foreign relaunch killed its own server mid-test. NEVER kill blindly before checking who holds the machine. Before any kill or launch:

1. List the holders directly on the host: `Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe' OR Name='DayZServer_x64.exe'"` and read each `.CommandLine` for its `@<Mod>` token and `-profiles=...<OtherMod>_dev` path. Also check `Get-NetUDPEndpoint -LocalPort 2302` for the process that holds the port.
2. If any holder references a different mod than the one you are testing, it is another live session. Do not kill it. Tell the user ("port 2302 is held by @<OtherMod>; should I kill it, or is that session still active?") and wait for confirmation before evicting. Only kill without asking a process that is clearly yours (same `@<Mod>`) or that the user confirmed stale.
3. `DayZServer_x64.exe` (the retail dedicated binary) is a separate process from `DayZDiag_x64`: a DayZDiag-only kill misses it, and killing it evicts a retail-mode session. Cover both names when you clean up legitimately.
4. Killing a foreign DayZServer mid-write corrupts the shared CE persistence at `DayZServer\mpmissions\<mission>\storage_1`; the next boot dies on `!!! Serious stream damage detected during load` and exits before the UDP bind. Remedy: rename `storage_1` (the server creates a fresh one). Better: do not kill foreign servers.
5. After your own launch binds, confirm that the live command line references your `@<Mod>` before trusting any in-game observation.

## Mods with dependencies in a separate `@<Mod>_deps`: include them in the modset

If a mod has its dependencies in a separate addon (`@<Mod>_deps`, not bundled in `@<Mod>`), the launch modset must include them or the client fails to compile scripts: `Can't compile "World": Unknown type '<BaseClass>'`. Dependencies (base config and script classes) must load before the mod, so put them in `-BaseMods` (which goes first in `-mod=`), not in `-ExtraMods` (which goes after the mod).

Before relaunching a mod that was tested before, do not assume the default `-BaseMods`: read `-mod=` from the last successful RPT or launcher output (`<Mod>_dev\_client\profiles\*.RPT`, the "Launch CLIENT" line) and use that modset.

Measured 2026-06-26: launching a weapon mod without its `_deps` addon gave `Unknown type '<BaseClass>'` at a line of the mod's own script and "Can't compile World". Correct: `-BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<Mod>_deps"`. `P:\` may not be mounted in a new session: mount it before build or launch (in this repo: `/dayz-workdrive`).

## Third-party dependencies with scripts that only retail tolerates: `-Retail -NoFilePatching`

If a third-party dependency emits `SCRIPT (W)` warnings on retail but fatal `SCRIPT (E)` errors on DayZDiag (unclosed braces, "missing function scope", "Opened scope at the end of file"), the test path with filePatching does not work, for two reasons:

- **DayZDiag** is stricter: those retail warnings are fatal errors, `Can't compile "World" script module!`, and the diag server dies ("Server process exited before binding").
- **A retail client with `-filePatching`** crashes on connecting: `Unhandled exception ... Access violation. Illegal read ... at 0x0` with the callstack `CDPInitServer`/`CDPCreateClient` (a minidump and a `crash_*.log` in `_client\profiles`). The server stays healthy (`is connected` followed by `[Disconnect] -1`).

**Fix:** if your change is already packed in the PBO, launch with `-Retail -NoFilePatching`. filePatching is unnecessary with an up-to-date PBO, and removing it avoids both failures. A PBO without filePatching is also the configuration the mod runs with on a real dedicated server.

```
dayz-test.ps1 -Mod <Mod> -Mode all -Retail -NoFilePatching -BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<Mod>_deps"
```

The current `../scripts/dayz-test.ps1` refuses `-Retail` (it exits with "Retail lifecycle is manual-only and quarantined"), so the user runs this launch by hand with the same arguments; the command above is the form the finding was measured with.

Verify the connection without OCR: `Select-String 'is connected'` in the server RPT is the authoritative signal, and a new `crash_*.log` in the client profile marks the failure. Read both with PowerShell directly on the host, not through a sandboxed bash whose view of the files is cached.

## Launching DayZDiag from the agent: use `cmd start`, not a background task; the bind-wait gave a false negative

Three traps when an in-game smoke test is run from the agent's tool calls, not by hand:

- **A `DayZDiag_x64.exe` started with `Start-Process` from an agent background task dies when that task ends.** The same happened with the bind-wait of `dayz-test.ps1` when the script ran in the background. The harness kills the job's child processes on closing: the server drops midway through the CE without leaving its own RPT (it binds 2302 and disappears), and a client launched in another call survives (symptom: one DayZDiag process, dead server). Confirmed three times. `Start-Process -PassThru` without `-Wait` is not enough when the call runs in the background. **Fix: launch server and client through a `.bat` with `start ""`** (an independent process group, outside the agent's tree). They survive across tool calls and write their RPT. Pattern: a server bat and a client bat with `start "" "DayZDiag.exe" -server ...` and `... -connect=127.0.0.1`, same modset (`-mod="...;@<Mod>;@DayZ_MCP"` with absolute `!Workshop` paths). Poll the bind yourself (`Get-NetUDPEndpoint -LocalPort 2302`); to wait for the connect use a read-only poller (no `Start-Process` inside it, or closing it kills the game).
- **The bind-wait of `dayz-test.ps1` gave a false negative** (seen at 240 s): the server did bind 2302 (`Get-NetUDPEndpoint` confirmed it) but the orchestrator reported "Timed out waiting for bind", refused to launch the client and killed the server it had launched. Workaround: let `-Build` build the PBO (that part works), ignore the launch failure, and launch server and client by hand through `.bat` files.
- **The MCP bridge's `version_state=legacy_blocked` ("poll did not include ver=") is only an incomplete init**, not a version mismatch: it turns to `ok` when the server mission finishes loading (1-2 min). Do not re-register the server or redeploy because of it; wait and check `bridge_status` again (the MCP verification references (`references/mcp/README.md`) has the same row).

On a machine with dayz-mcp's registered launcher these hand launches are the unmanaged fallback of `managed-launcher.md`, not the default.

## DayZ 1.30: launch flags

New launch flags on DayZDiag and Workbench since 1.30 (documented in the 1.30 Experimental modding changelog; not confirmed here as strings in the executable, and not checkable on `P:\`):

- `-mod` accepts an **unpacked** source folder (not only a packed `@Mod` with PBOs).
- `-cacheP3D=0` / `-cacheP3D=1` disable or enable the P3D cache.
- `-resolveFilePatchingUsingEnfusion=0` / `-resolveFilePatchingUsingEnfusion=1` select the Enfusion path for filePatching.

Until 1.29, `-mod` was documented as packed `@Mod` folders. Pair an unpacked `-mod` with the filePatching caveats already in this file (the empty-PBO compile, `-NoFilePatching` for a production replica). Full notes: `dayz-1-30.md`.

## Motorbike import: untextured runs and a moving 1PP eye

Two ways a capture run misleads while its error counts look normal. Measured while importing a motorbike model in 2026-10: dedicated server and windowed client on one PC, the client window grabbed with Windows Graphics Capture at 3841x2160, one JPEG a second (ffmpeg `-q:v 3`). MB is 10^6 bytes. Script lines are those of the scripts unpacked on `P:\scripts\`; where a 1.29 line is given it was read from a 1.29 extract and is not checked on `P:\`.

### Some runs never load their textures: judge the run before its frames

[EXACT] On DayZDiag 1.30.164.200, 2 of 7 runs on 2026-10-19 and 5 of 12 on 2026-10-24 drew the scene flat for most or all of the run (terrain, sky, vegetation as blocks, the mod's own model; in some, part of it arrived late) while lighting and shadows still drew and the run ended normally. The next run with the same server and client command line came back textured after 5 of the 7 flat runs (once three flat runs came in a row), and two textured runs opened with 4 and 11 s of flat frames. No error flags it: the client RPT and script log hold as many error lines as a textured run's. In all 24 captured runs of this probe (Chernarus, 2026-10-15 to 24), though, every textured run's client RPT had three warnings and no flat run's had all three: `MatMulti` on `atcbig_multi_5metal_plates_old_co.paa`, and `No components in` on `cl_rock1.p3d` and on `muzzle_flash_pistol_fnp.p3d`; two mostly flat runs had one or two of them (other maps not checked). Flat clients were also seen on 1.30.164014 (in part) and 1.29.163709 (dayz-characters `references/character-rigging.md`). The cause is unknown; window focus was not recorded (`automated-cells.md`, "An unfocused DayZDiag client runs at ~20 fps"), so it is not ruled out. One observation points at it (not reproduced here): on 2026-10-23 a client launched by the managed launcher stayed flat for about 3 min and loaded its textures as soon as the user clicked into its window, and the managed tools do not give that window focus. Until focus is ruled out, log the foreground window, or have a human click the client window, before judging frames.

- Signal: the run's median JPEG size, not a frame's: 0.36-0.45 MB for the 7 flat runs against 1.46-1.61 MB for the 13 textured runs whose view filled the window. The last four runs of 2026-10-24 drew the view in about 72% of the window's width and height, and the textured one among them read 0.63 MB: compare runs with the same framing. Single frames overlap (night, late textures).
- For anything judged on its frames such a run is `SETUP_FAIL` (`automated-cells.md`, "Validity of an automated run"): relaunch; do not tune a material, LOD or closure on it, nor fail a model for missing textures (the MCP verification references (`references/mcp/README.md`)) while the vanilla terrain and sky in the frame are flat too. Its script-side readings still count: two of the Lewis eye readings below come from flat runs.

### The 1PP eye is not a constant of the character class: log it in every run

[EXACT] The vehicle 1PP camera, `DayZPlayerCamera1stPersonVehicle` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`), keeps its parent's placement: bound by position to the character's `Head` bone (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera1stperson.c:15`), offset `"0.04 0.04 0"` (`:21`, bound at `:53-54`); the binding fields `m_iDirectBone` and `m_iDirectBoneMode` are at `P:\scripts\3_game\dayzplayer.c:23-24`. Item 5 of `skills/_shared/vehicles/rip-import.md` rests on it.

[EXACT] On DayZDiag 1.30.164.200, logged in the bike's model space at seven fixed looks per run with the bike stopped (11 runs, 2026-10-16 to 24), the eye sat 5.4-6.1 cm from the `Head` bone at every look (the offset is 5.7 cm long), and that bone moved while the rest held: the pelvis stayed within 0.6 mm, with the bars at rest and the same rider clips swapped in, and the head ranged over 7.6 cm.

- Between runs with one class and command line: four runs pinned to SurvivorM_Lewis on 2026-10-19 put the eye at 1.479-1.493 m, one of them 8.5-9.4 cm to one side at yaw 0.
- Between looks: SurvivorF_Keiko held 1.401 m for six of seven looks on 2026-10-19, with black clipped shards where the handlebar and top clamp should be, and 1.474 m on the seventh, handlebar back; two runs pinned to Keiko on 2026-10-24 read 1.42-1.51 m, changing from look to look. In 5 of the 11 runs, though, the eye held within 1 mm over all seven looks, yaw ±45 included.
- Across classes: SurvivorF_Judy read Lewis's eye to 0.2 mm on 2026-10-19 and 3.7 cm lower on 2026-10-16.

Why the head moves, and what held Keiko at 1.401 m (not reproduced), is not established. It is not the missing-mod case either (`automated-cells.md`, the `-mod=` line check, point 2): the mod set and the pose swap were the same in every run. Window focus, which changed client-side readings in the unfocused-client finding of `automated-cells.md`, was not logged in these runs either.

- Log the eye at every look of every run: `GetCurrentCameraTransform` (`P:\scripts\3_game\dayzplayer.c:1237`) through the vehicle's `WorldToModel` (`P:\scripts\3_game\entities\object.c:874`). Compare first-person frames only between runs whose eyes match, and check offline 1PP geometry (the vehicles pack, `skills/_shared/vehicles/`) against the eyes the runs logged, not one eye per class.
- Pin the class anyway, to remove one variable; whether the class moves the eye is not established. [EXACT] In a `modded class MissionServer`, override `PlayerBase CreateCharacter(PlayerIdentity identity, vector pos, ParamsReadContext ctx, string characterName)` (`P:\scripts\5_mission\mission\missionserver.c:499`, 1.29 `:486`; both spawn paths of `OnClientNewEvent` call it, `:573` and `:589`), set `characterName` from `CommandlineGetParam` (`P:\scripts\3_game\global\game.c:661`, 1.29 `:660`) behind the test flag (`automated-cells.md`, "Automated in-game cell without a human pilot: the four measured walls and workarounds", point 1) and call `super`: all 7 runs that passed a class spawned it, and 17 runs without it drew 14 classes.
