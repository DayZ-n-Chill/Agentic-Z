# Troubleshooting a launch: symptoms, Steam, the work drive and dead clients

The symptom table for a local test session, where each log lives, the historical notes on running third-party modsets on the retail executables, and the measured failures that come from the environment and not from the mod: Steam's registry state, a missing `P:\` after a reboot, argument quoting, and a client that dies before it writes a log.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: dated findings were measured on one Windows test machine, and "this install" means that machine, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it.

Measured results and third-party behaviour (BattlEye, Steam, VPPAdminTools, LBmaster, Community Framework, dayz-mcp) are not yet checked on `P:\`; the vanilla script facts in the table cite their file.

## TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| Client kicked `0x00020005` | filePatching mismatch | `allowFilePatching = 1;` in serverDZ.cfg |
| VPPAdminTools asks for a password despite a `SuperAdmins.txt` superadmin | the `serverDZ.cfg` was generated before `vppDisablePassword = 1;` became the default (before 2026-06-09) | the `dayz-test.ps1` preflight appends `vppDisablePassword = 1;` when it is absent; restart the server, or add the line by hand (measured 2026-06-15) |
| Kicked `0x00010002` | mismatched signatures | rebuild the PBO; or `verifySignatures=0` (the dev cfg already sets it) |
| "PlayerConnect will stay disabled" | mission empty, or `-mission` not absolute | pass an absolute mission path. On the native Linux `DayZServer` it is the reverse: use a relative `mpmissions/<name>` (`linux.md`) |
| Stuck past the loading screen | retail exe with filePatching | use `DayZDiag_x64.exe` |
| Server or client does not exit | managed run still active | stop only the exact `run_id` with `-Kill -RunId <run_id>`; if the id is missing, declare `manual_cleanup_required` and do not look for another process to kill |
| Mod not visible in game | PBO landed outside `!Workshop` | make sure `P:\Mods` is a junction |
| Server boots, then dies before the UDP bind; RPT or log shows `!!! Serious stream damage detected during load` | half-written CE storage after an unclean server kill; it looks like a mod bug | wipe or rename `<mission>\storage_1` before the next test; the server creates a fresh one. After any unclean server kill, do it before the next boot |
| Mod class missing, `CreateObjectEx` returns null, no RPT error | a relative `-mod=@Name` did not mount | use absolute `!Workshop` paths; `Get-ModString` in `dayz-test.ps1` does this (see "MOD PATHS MUST BE ABSOLUTE" in `windows-launch-cycle.md`) |
| Mod mounts (CfgPatches in `defines:`) but no script or hook runs | AddonBuilder's binarize mode dropped the `.c` files, leaving a config-only PBO | build script mods with `-packonly` (`Invoke-Build` adds it for a source with no `.p3d`, `.paa` or `.rvmat`); search the deployed PBO for a known class name to confirm (verified 2026-06-03) |
| A script edit does not take effect: the same compile error persists across rebuilds although the source is fixed on disk | AddonBuilder's incremental sync to `P:\temp\<Mod>` served stale source (a changed `.c` was not copied again); filePatching did not override the PBO's scripts with the loose work-drive copies either | `Invoke-Build` wipes `P:\temp\<Mod>` before every build; when you run AddonBuilder by hand, pass `-clear` or delete the temp folder first. The tell is a compile error citing a line you already fixed and verified (verified 2026-06-18) |
| `-Build` ran but the deployed mod is unchanged in game (old config or `.p3d`) | the deployed PBO was locked by the running server, so AddonBuilder failed to copy it: an `[ERROR] Build failed` at the copy step with exit 0 | stop the exact managed run before rebuilding, verify the state `EXITED`, then build and relaunch; without a `run_id`, declare manual cleanup, do not infer ownership. The current `Invoke-Build` stops on that log line and on an unchanged PBO mtime |
| Kicked `240 ("Game restart required")` 20-60 s after connect | server BattlEye active and the client launched bare (`DayZ_x64.exe` never initializes BattlEye); `BattlEye = 0;` stops masking it after a BattlEye service hot-update (check the file times in `Common Files\BattlEye`) | historical diagnosis: `DayZ_BE.exe` initialized BattlEye correctly in a session on 2026-06-11. The user decides whether to open retail externally; the agent stays in quarantine and does not launch it |
| Retail server binds, then dies about 1 min later; `BattlEye initialization failed`, RPT ends "Termination successfully completed" | `BEServer_x64.dll` missing or renamed | historical observation on the 1.29 dedicated server (2026-06-11). The user decides and performs any restoration outside the agent workflow; the agent stays in quarantine, read-only |
| Modal "Compile error … Missing function scope" citing a third-party file at boot | the diag exe compiles third-party packs strictly | report the incompatibility; if the user opens retail externally, apply quarantine and do not chase the third-party error |
| Every DayZDiag mission start logs a `SCRIPT (E)` stack, once per peer: the `-- Stack trace --` header, the frames `GetPlugin()` of `pluginmanager.c`, `OnInit()` of `pluginitemdiagnostic.c`, `PluginsInit()`, `PluginManagerInit()`, `MissionBase()` and the mission's own (`CreateMission()` of `somemission.c` on a client, a frame of the mission's `init.c` on a server), and a `-----------------` closing line. In the 375 DayZDiag 1.30 RPTs measured without `@DayZ_MCP` that carry it, the line `Module PluginConfigDebugProfile is not Registred in PluginManager.c!` comes before it. That line can be missing: none of the RPTs measured with `@DayZ_MCP` carries it, and neither does a 1.29 client RPT without `@DayZ_MCP`. With `@DayZ_MCP` loaded the stack has one more frame, `PluginsInit() DayZ_MCP/scripts/4_World/mcp_diagplugins.c : 30` | vanilla, not the mod. `PluginManager.Init` registers `PluginItemDiagnostic` as Diag, inserted under `DIAG_DEVELOPER` (DayZDiag defines it), and `PluginConfigDebugProfile` as Debug, inserted only when `IsDebug()` (an internal build). `PluginItemDiagnostic.OnInit` asks for that plugin, and under `DIAG_DEVELOPER` `GetPlugin` prints the line and dumps the stack; the caller checks for null, so the run goes on. The stack was also seen on 1.29. DayZ_MCP's frame is its modded `PluginsInit`, which calls `super` and then prints one `[DayZ_MCP] diag PluginInventoryDebug registered=` line | nothing to fix. A test that counts `SCRIPT (E)` lines as addon errors leaves out the whole block, header to closing line, and recognizes it by its frames, not by the `Module PluginConfigDebugProfile` line: in the runs measured, 8 `SCRIPT (E)` lines per peer per mission start (header, six frames, closing line), 9 with `@DayZ_MCP` [EXACT] |

Vanilla sources for the last row: `P:\scripts\4_world\plugins\pluginmanager.c:76` registers `PluginItemDiagnostic` with `RegisterPluginDiag`, `pluginmanager.c:88` registers `PluginConfigDebugProfile` with `RegisterPluginDebug` (kept only when `g_Game.IsDebug()`, `pluginmanager.c:216`), `pluginmanager.c:339` prints the `is not Registred` line and `:340` dumps the stack under `#ifdef DIAG_DEVELOPER`, and `P:\scripts\4_world\plugins\pluginbase\pluginitemdiagnostic.c:94` is the `GetPlugin(PluginConfigDebugProfile)` call in `OnInit`.

Logs (where to look): `script.log` holds script compile and runtime errors; `*.RPT` holds engine errors (missing assets, malformed configs); `crash_*.log` holds handled exceptions, not hard segfaults. All are under the `_server\profiles\` and `_client\profiles\` folders. For a structured script-failure diagnosis, hand off to `dayz-mod-workflow`.

## MANUAL EXTERNAL RETAIL FOR THIRD-PARTY MODSETS (historical, verified 2026-06-11)

The diag exe compiled Enforce Script strictly; the retail executables compiled permissively. Third-party packs were observed with syntax that retail tolerated as `FIX-ME` warnings and diag rejected as fatal errors: a third-party weapons pack with braceless one-liners (`override typename GetInputType() return X;` in its optic and weapon scripts, "Missing function scope") and LBmaster_Core ("Unsafe down-casting"). This is a diagnostic fact, not an alternate launcher path. The agent reports the incompatibility; the user owns any decision to open retail manually outside this orchestrator. While an external retail route is open, the agent stays in retail quarantine, read-only, under the protocol in `managed-launcher.md`.

Facts from the manual route, kept for diagnosis:

- **The retail server was `DayZServer_x64.exe` from the dedicated install.** In the observed session, the retail game exe with `-server` booted the CE and then terminated while loading GFX resources (`Water/*.edds`, "Termination successfully completed").
- **The dedicated binary already runs as a server.** Adding `-server` also triggered LBmaster's startup check (`Error: Remove Startup Parameter: -server`).
- **The LBmaster setup loaded server-only addons through `-serverMod=`.** Its `*_Server.pbo` files had been placed under `@SomeFolder\addons\*.pbo`, and their paths resolved absolutely in the same way as `-mod` paths.
- The launcher's bind-wait produced a false negative ("exited before binding") while the server was still booting the CE. In that session the first CE boot of the large pack took minutes, and the later observation of UDP 2302 showed that startup had continued.

**BattlEye on the retail pair: kick 240 "Game restart required"** (2026-06-11):

- The retail server loaded its BattlEye module (`profiles\BattlEye\BEServer_x64.dll`, downloaded on its first BattlEye boot) and kicked clients that had not initialized BattlEye, including the bare `DayZ_x64.exe` client of that session. `BattlEye = 0;` in serverDZ.cfg masked the behaviour for several sessions, then stopped doing so after a system-wide BattlEye service hot-update under `%ProgramFiles(x86)%\Common Files\BattlEye`. The file times identified that update, after which kick 240 returned 20-60 s after each connection whatever the cfg flag said.
- When `BEServer_x64.dll` was removed or renamed in the 1.29 dedicated installation, the server bound UDP, printed `BattlEye initialization failed`, and shut down cleanly about a minute later ("Termination successfully completed" in the RPT). The sequence looked like a healthy boot followed by a silent death.
- With server BattlEye intact, `DayZ_BE.exe` initialized the client handshake and avoided the kick. The in-game session on 2026-06-11 reached spawn, equip and inventory with zero kicks. `dayz-test.ps1` did not invoke that route; the user owned its UI lifecycle and the agent stayed in quarantine, read-only.

Load-order failures from the same period:

- Removing `@CF` from the base mods while `@VPPAdminTools` remained caused VPPAdminTools' embedded CF sources to fail with `Unknown type 'RPCManager'`.
- LBmaster worked only when the setup included its client PBOs (`LBmaster_Core` plus the matching client of every `*_Server.pbo`, such as `LBmaster_Groups` for `AdvancedGroups_Server`), the server-side PBOs and a per-IP license whitelist. Its error log contained the corresponding whitelist URL. In the local weapon sessions VPPAdminTools served as admin tool and spawner, and LBmaster appeared only in parity runs.
- A test subset of a large weapons pack was staged with filesystem hardlinks from the full pack's folder: 13 weapon PBOs without duplicate file copies.

## Four working rules for a test cycle

- Faced with a regression, first compare the launch command, the `-mod` arguments, the paths and the environment with the last passing run. Check a measurable invariant between both runs before you form a hypothesis about the code.
- Look for the mod's `Print()` and `DbgLog` output in the most recent `script_*.log` of the matching profile. Use the RPT for engine, CE, network, compilation and native crashes; do not conclude "the code did not run" from prints missing in the RPT.
- Prepare the command, paths and arguments before acquiring a short lease; acquire and use the token in adjacent calls. After a long analysis, acquire again right before the blocking operation.
- In managed cycles, run `adopt` then `stop` while server and client are both alive, and ask for both to stay open between iterations. If a peer has already died, use the documented degraded shutdown and wait for the lifecycle to reconcile before relaunching (`managed-launcher.md`).

## Three pitfalls measured in one cycle

All three cost time the same night, with a healthy MCP bridge (v10). None came from the mod.

1. **`action_use` matches by class name, not by action text.** The bridge iterates `ActionManagerBase.m_ActionsArray` and compares `candidate.Type().ToString() == wantedAction` (`DayZ_MCP/scripts/5_Mission/MCPClientBridge.c:1806`, dayz-mcp's source). Passing the visible text, the one `m_Text` resolves from the stringtable, returns `action_not_found` even while the action is available on screen. A client in another language invites testing the translation, but language is irrelevant: the key is the class. Take the name from `class X : ActionInteractBase` in the mod itself, never from the stringtable.

2. **The Steam session check of the prerequisites (`windows-launch-cycle.md`) only warns, and its `scripts/dayz-test.ps1` preflight does not run on the MCP route.** `dayz_test_run` does not pass through that preflight. It now has its own check: a stale session makes it fail in the `validating` phase with `error_code: "steam_session_stale"` (`windows-launch-cycle.md`, prerequisites). In the 2026-08-29 cycle the launch went ahead without that error. Variant observed 2026-08-29: `pid=0` and `ActiveUser=0` with zero live Steam processes (the signature known before was a populated pid with `ActiveUser=0`). Same outcome: the client RPT is cut off right after argv, without a single script line, and the server is intact because it does not use Steam. Checking the key before launching a client takes 10 s.

3. **The active Steam account decides which character loads, and nothing else.** Restarting Steam can bring back another account without warning. Measured 2026-08-29: at 03:55 the client entered under one account, with the persisted character at the test site; at 04:17, after a Steam restart, it entered under a second account, with a fresh character on the coast. The site appeared without its devices and looked like a persistence failure of the mod. The registry key tells the account without opening the game: `ActiveUser = steamID64 - 76561197960265728`. AddonBuilder also prints `Steam_SetMinidumpSteamID:  Caching Steam ID:  <steamID64>` in its output. If a cycle depends on a persisted character, pin the account in the preflight, not just the pid.

   Returning to the first account brought back the character (spawn at the exact site, without a teleport) but not the mod's state: the server log still reported zero saved entries under both accounts. An empty test site is therefore not explained by the account, and switching logins will not set up the fixture. The account explains where your character appears; the mod's state is either set up or absent.

## After a reboot `P:` does not exist, and FileBank packs nothing with exit 0

`P:` is a `subst`, not a disk link: it does not survive a reboot, let alone a hard crash. Everything the Bohemia tools and the sealed launcher touch hangs from it (`P:\Mods`, `P:\<Mod>`, `P:\<Mod>_dev\_server\profiles`, `P:\scripts`, `P:\DZ`).

The expensive part is how it fails. Measured with `P:` absent:

    FileBank.exe -property prefix=<Mod> -exclude <lst> -dst <staging> P:\<Mod>
    exit=0
    <staging>\<Mod>.pbo   ->   79 bytes

Exit 0, a 79-byte PBO and not a single message. It is the same failure mode as AddonBuilder's `Build failed` with exit 0: the tool counts packing zero files as a success.

Preflight, two lines, before any build or launch:

    Test-Path -LiteralPath "P:\"          # if False:
    subst P: "<work-drive-folder>"     # in this repo: /dayz-workdrive

Check the anchors too, not just the root: `P:\<Mod>\config.cpp`, `P:\Mods\@<Mod>\Addons`, `P:\scripts`, `P:\DZ`. Validate the PBO by size and entry count before publishing; a package of a few hundred bytes is the signature of this.

## The Steam `pid` in the registry can be dead

The prerequisites require `HKCU\Software\Valve\Steam\ActiveProcess` to have `pid != 0` and `ActiveUser != 0`. That is necessary and not sufficient: a non-zero `pid` can be the pid of a dead process. After a hard PC crash the key keeps the previous Steam pid; Steam starts again with another pid and does not always rewrite the key in time. DayZ reads that pid, looks for the process, does not find it, and dies.

Measured: registry `pid=25484`, live `steam.exe` `pid=13856`. The "not zero" check passed on a broken system. The question to ask is whether that process exists:

    $k  = Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess'
    $st = Get-Process -Name steam -ErrorAction SilentlyContinue
    $ok = $st -and ($st.Id -contains [int]$k.pid) -and $k.ActiveUser -ne 0

Failure signature (three identical reproductions):

| signal | value |
|---|---|
| modal dialog | `unable to locate running instance of Steam` |
| dump exception | `0x80000003` (breakpoint), same address each time |
| client process CPU | 0 s: alive but stopped |
| client RPT | frozen at 847 B, header only |
| loaded modules | about 69, the last ones from Steam (`gameoverlayrenderer64.dll`, `tier0_s64.dll`) |

`0x80000003` is not a crash: it is a deliberate `int 3` of the diag exe when it shows its dialog. That is why the process stays alive with 0 CPU, and why there is no failure event in the Windows Event Viewer: DayZ writes its own `.mdmp` and halts.

Remedy: the reliable approach is to copy the live `steam.exe` pid into the key, with guards: the key stable between two reads, a valid `ActiveUser`, a single live `steam.exe` in your session and in its install path, rechecked just before writing and verified after. Write from a shell outside any sandboxed (MSIX) app (`managed-launcher.md`, point 1-ter). Restarting Steam (`steam.exe -shutdown` and relaunch) preserves the login but may not rewrite the key: on that day Steam started with pid 34316, the key stayed at 50968, untouched since the previous night, and the new pid only appeared in `HKLM\SOFTWARE\Valve\Steam\SteamPID`. If you restart, check that the key matches a live process before launching the client.

The discriminating probe is `SteamAPI_IsSteamRunning`, not `SteamAPI_Init`. With a stale key, DayZ's own `steam_api64.dll` returned `Init` OK and `IsSteamRunning` false, and the client died all the same; after copying the pid both returned true and the client entered. A gate that only calls `Init` passes on the broken state.

**Two Steam facts the registry cannot answer** [EXACT] (measured 2026-09-08). (1) Which account is logged in: read `logs/connection_log.txt` under the Steam install for `[Logged On, ...] [U:1:<accountID>] RecvMsgClientLogOnResponse() : 'OK'` (`SteamID64 = accountID + 76561197960265728`). (2) Whether that account owns DayZ: `steamapps/appmanifest_221100.acf`, field `"LastOwner"`. If the logged-in account is not the LastOwner, the client dies about one second after launch with the same header-only RPT and `0x80000003` signature while every registry check passes; comparing the dump's `Caching Steam ID: <id>` with `LastOwner` settles it in a minute.

**Reading the dump without a debugger.** A minidump carries a `MINIDUMP_EXCEPTION_STREAM` (type 6) and a `MODULE_LIST` (type 4); about 60 lines of Python extract the exception code and the module that contains `ExceptionAddress`. Read it before theorizing about drivers or the mod: here `0x80000003` ruled out both "render crash" and "corrupt mod", the two hypotheses two boot cycles had already been spent on.

**Before searching for the cause in your change, deploy the previous artifact and reproduce.** Here the PBO from before the change failed identically, which cleared the change in a single cycle and sent the search into the environment. An A/B with the old binary costs the same as testing a hypothesis and it decides.

## Live logs and shutdown of a released run

DayZDiag keeps the RPT and `script_*.log` open. `Get-Content` or `ReadAllText` can fail with `IOException` at any point of a wait loop. To monitor a live peer, open with explicit sharing:

```powershell
$fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read,
                     [IO.FileShare]::ReadWrite)
try { $text = [IO.StreamReader]::new($fs).ReadToEnd() } finally { $fs.Dispose() }
```

In the managed lifecycle, keep the `run_id` and use the public tools. If a low-level operation finds a `released` run, the sequence is `adopt` and then `stop`; `stop` alone can only return `run_not_adopted`. If another session already cleaned it up, `run_not_adoptable` with zero run processes and an RPT ending in `Termination successfully completed` describes an orderly shutdown, not a crash.

## Quoting, and triage of a diag that never writes logs

For `name=value` arguments with spaces, quote the entire token:

```text
-profiles="<profiles-path>"      # NO: quotes only around the value
"-profiles=<profiles-path>"      # YES: a complete token
```

Apply the same pattern to `-config=`, `-mission=` and `-mod=`. In Windows PowerShell 5.1, passing an array to `Start-Process -ArgumentList` does not guarantee quoting of each element; do not take that result as proof of the argv the game received. The managed path of this skill transports a structured array and remains the normal way.

For a hang with 0 CPU and no RPT, first run the authorized minimal control, `DayZDiag_x64.exe -server` with no other arguments, and add the arguments one by one. In the measurement behind this rule, about 53 loaded modules meant "has not yet reached the UI" and 69-78 meant a real startup; use the delta as a signature of the measured build, not as a universal constant. Get the real argv from `Win32_Process`: the truncated header line of the RPT does not represent it reliably.

## A client that does not start: separate argument, native path and mod

Decide by the form of the failure before touching the mod:

- **Alive, 0 CPU, no RPT and no dump:** apply the minimal control and the argument bisection above.
- **Dies with a header-only RPT and an `ErrorMessage_*.mdmp`, without a `crash_*.log`, even without mods:** launch a server of the same build. A stable server with a large RPT next to a bare client that crashes points to the client's native or graphics path. Confirm with another project's profile in the same window.
- **Fails only when `-mod` is added:** then investigate the mod and its load order.

"It was rebooted" is measurable too: compare `Win32_OperatingSystem.LastBootUpTime` and check that no process older than the stated reboot survives. Fast Startup can preserve the kernel across a shutdown; a full reboot changes that value.
