# Troubleshooting a launch: symptoms, Steam, the work drive and dead clients

The symptom table for a local test session, where each log lives, the historical notes on running third-party modsets on the retail executables, and the measured failures that come from the environment and not from the mod: Steam's registry state, a missing `P:\` after a reboot, argument quoting, and a client that dies before it writes a log.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it. Tags such as `SP-078`, `LL-196` and `CLAIM-...` are the finding numbers of the knowledge pack this material came from; they are kept so that cross-references between files stay searchable. `DAYZ_INFRA.md` is that pack's infrastructure note (in this repo under `skills/_shared/knowledge/`); a tag like `[EXACT - DAYZ_INFRA.md §Section]` names the section of it that records the fact.

Measured results and third-party behaviour (BattlEye, Steam, VPPAdminTools, LBmaster, Community Framework, dayz-mcp) are not yet checked on `P:\`; the vanilla script facts in the table cite their file.

## TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| Client kicked `0x00020005` | filePatching mismatch | `allowFilePatching = 1;` in serverDZ.cfg [DAYZ_INFRA.md §serverDZ.cfg - allowFilePatching = 1; mandatory + §BattlEye - most common kick codes] |
| VPP asks for a password despite a `SuperAdmins.txt` superadmin | `serverDZ.cfg` predates the `vppDisablePassword = 1;` default (generated before 2026-06-09); the existing-cfg path only re-checked `allowFilePatching` | launch now self-heals (appends `vppDisablePassword = 1;` if absent) + restart; or add it manually [session 2026-06-15] |
| Kicked `0x00010002` | mismatched signatures | rebuild PBO; or `verifySignatures=0` (dev cfg already does) [DAYZ_INFRA.md §BattlEye - most common kick codes] |
| "PlayerConnect will stay disabled" | mission empty / `-mission` not absolute | pass an absolute mission path [DAYZ_INFRA.md §Canonical invocation commands - Server diag]. On the native Linux `DayZServer` it is the reverse: use a relative `mpmissions/<name>` (`linux.md`) |
| Stuck past loading screen | retail exe + filePatching | use `DayZDiag_x64.exe` [DAYZ_INFRA.md §Mandatory diag binary for iteration] |
| Server/client does not exit | managed run still active | stop only the exact `run_id` with `-Kill -RunId <run_id>`; if ID is missing, declare `manual_cleanup_required` and do not look for another process to kill |
| Mod not visible in-game | PBO landed outside `!Workshop` | ensure `P:\Mods` is a junction [DAYZ_INFRA.md §Drive and mod layout] |
| Server boots then dies before UDP bind; RPT/log shows `!!! Serious stream damage detected during load` | half-written CE storage after an unclean server kill - masquerades as a mod bug | wipe (or rename) `<mission>\storage_1` before the next test; the server regenerates a fresh one. SOP: after ANY unclean server kill, wipe it preemptively |
| Mod class missing / `CreateObjectEx` returns null, no RPT error | relative `-mod=@Name` didn't mount | use absolute `!Workshop` paths - `Get-ModString` now does this (see "MOD PATHS MUST BE ABSOLUTE" in `windows-launch-cycle.md`) |
| Mod mounts (CfgPatches in `defines:`) but no script/hook runs | AddonBuilder binarize dropped the `.c` → config-only PBO | build scripts mods with `-packonly` (Invoke-Build auto-detects when no `.p3d`/`.paa`); grep the deployed PBO for a known classname to confirm. [verified 2026-06-03] |
| Script edit doesn't take effect - the same compile error persists across rebuilds even though the source is fixed on disk | AddonBuilder's incremental sync to `P:\temp\<Mod>` served stale source (a changed `.c` not re-copied); filePatching also did not override the PBO's scripts with the loose work-drive copies | Invoke-Build now wipes `P:\temp\<Mod>` before every build; building AddonBuilder by hand, pass `-clear` or delete the temp first. Canonical tell: a compile error citing a line you already fixed and verified. [verified 2026-06-18] |
| `-Build` ran but the deployed car is UNCHANGED in-game (old config/.p3d) | the deployed PBO was **LOCKED** by the running server, so AddonBuilder failed to COPY it - a SILENT `[ERROR] Build failed` at the *copy* step while the script CONTINUES and the gates run on the OLD pbo | stop exact managed run before rebuilding, verify state `EXITED`, then build and relaunch; without `run_id`, declare manual cleanup instead of inferring ownership. SUB_BRZ s28 |
| Kicked `240 ("Game restart required")` 20-60 s after connect | server BE active + client launched bare (`DayZ_x64.exe` never inits BE); `BattlEye = 0;` stops masking it after a BE service hot-update (check mtimes in `Common Files\BattlEye`) | historical diagnosis: `DayZ_BE.exe` correctly initialized BE in session 2026-06-11; user decides whether to open retail externally and agent remains in quarantine, without launching it |
| Retail server binds, then dies ~1 min later; `BattlEye initialization failed`, RPT ends "Termination successfully completed" | `BEServer_x64.dll` missing/renamed | Historical observation: the 1.29 dedicated server shut down when BE initialization lacked that DLL. The external owner/user decides and performs any restoration outside the agent workflow; the agent remains in quarantine/read-only [session 2026-06-11] |
| Modal "Compile error … Missing function scope" citing a third-party file at boot | diag exe strict-compiles third-party packs | report incompatibility; if user opens retail externally, apply quarantine and do not pursue third-party "bug" |
| Every DayZDiag mission start logs a `SCRIPT (E)` stack, once per peer: the `-- Stack trace --` header, the frames `GetPlugin()` of `pluginmanager.c`, `OnInit()` of `pluginitemdiagnostic.c`, `PluginsInit()`, `PluginManagerInit()`, `MissionBase()` and the mission's own (`CreateMission()` of `somemission.c` on a client, a frame of the mission's `init.c` on a server), and a `-----------------` closing line. In the 375 DayZDiag 1.30 RPTs measured without `@DayZ_MCP` that carry it, the line `Module PluginConfigDebugProfile is not Registred in PluginManager.c!` comes before it. That line can be missing: none of the RPTs measured with `@DayZ_MCP` carries it, and neither does a 1.29 client RPT without `@DayZ_MCP`. With `@DayZ_MCP` loaded the stack has one more frame, `PluginsInit() DayZ_MCP/scripts/4_World/mcp_diagplugins.c : 30` | vanilla, not the mod. `PluginManager.Init` registers `PluginItemDiagnostic` as Diag, inserted under `DIAG_DEVELOPER` (DayZDiag defines it), and `PluginConfigDebugProfile` as Debug, inserted only when `IsDebug()` (an internal build). `PluginItemDiagnostic.OnInit` asks for that plugin, and under `DIAG_DEVELOPER` `GetPlugin` prints the line and dumps the stack; the caller checks for null, so the run goes on. Same code in 1.29 and 1.30. DayZ_MCP's frame is its modded `PluginsInit`, which calls `super` and then prints one `[DayZ_MCP] diag PluginInventoryDebug registered=` line | nothing to fix. A test that counts `SCRIPT (E)` lines as addon errors leaves out the whole block, header to closing line, and recognizes it by its frames, not by the `Module PluginConfigDebugProfile` line: in the runs measured, 8 `SCRIPT (E)` lines per peer per mission start (header, six frames, closing line), 9 with `@DayZ_MCP` [EXACT][CLAIM-TEST-DIAG-PLUGIN-PROFILE-NOISE] |

Vanilla sources for the last row: `P:\scripts\4_world\plugins\pluginmanager.c:76` registers `PluginItemDiagnostic` with `RegisterPluginDiag`, `pluginmanager.c:88` registers `PluginConfigDebugProfile` with `RegisterPluginDebug` (kept only when `g_Game.IsDebug()`, `pluginmanager.c:216`), `pluginmanager.c:339` prints the `is not Registred` line and dumps the stack under `#ifdef DIAG_DEVELOPER`, and `P:\scripts\4_world\plugins\pluginbase\pluginitemdiagnostic.c:94` is the `GetPlugin(PluginConfigDebugProfile)` call in `OnInit`.

Logs (where to look): `script.log` = script compile/runtime errors; `*.RPT` = engine errors
(missing assets, malformed configs); `crash_*.log` = handled exceptions, not hard segfaults.
[EXACT - DAYZ_INFRA.md §When the RPT cites that a script fails]. All under the `_server\profiles\` and `_client\profiles\`
folders. For a structured script-failure diagnosis, hand off to `dayz-mod-workflow`.

## MANUAL EXTERNAL RETAIL FOR THIRD-PARTY MODSETS (historical verified 2026-06-11)

The diag exe compiled Enforce in STRICT mode; the retail chain compiled permissively.
Third-party packs were observed with syntax that retail tolerated as `FIX-ME` warnings but
diag rejected as fatal errors - verified live with the A6 weapons pack (braceless
one-liners: `override typename GetInputType() return X;` in OpticScripts/WeaponScripts,
"Missing function scope") and LBmaster_Core ("Unsafe down-casting"). This remained a
diagnostic fact, not an alternate launcher path. The agent's role is limited to reporting
the incompatibility; the user owns any decision to open retail manually outside this
orchestrator. While an external retail route is open, the agent remains in retail
quarantine and read-only under the protocol.

Historical manual-route facts retained for diagnosis:

- **Retail server was `DayZServer_x64.exe` from the dedicated install.** In the observed
  session, the retail game exe with `-server` booted the CE and then terminated while
  loading GFX resources (`Water/*.edds`, "Termination successfully completed").
- **The dedicated binary already operated as a server.** Adding `-server` also triggered
  LBmaster's startup check (`Error: Remove Startup Parameter: -server`).
- **The historical LBmaster setup loaded server-only addons through `-serverMod=`.** Its
  `*_Server.pbo` files had been placed under `@SomeFolder\addons\*.pbo`, and their paths
  had resolved absolutely in the same way as `-mod` paths.
- The launcher's bind-wait produced a false negative ("exited before binding") while the
  server was still booting the CE. In that session, the first CE boot of the large pack
  took minutes and the later UDP 2302 observation showed that startup had continued.

**BattlEye on the retail pair - kick 240 "Game restart required"** (session 2026-06-11):

- The retail server loaded its BE module (`profiles\BattlEye\BEServer_x64.dll`,
  auto-downloaded on its first BE boot) and kicked clients that had not initialized BE,
  including the bare `DayZ_x64.exe` client from that session. `BattlEye = 0;` in
  serverDZ.cfg masked the behavior for several sessions, then stopped doing so after a
  system-wide BE service hot-update under `%ProgramFiles(x86)%\Common Files\BattlEye`.
  The recorded file times identified that update, after which kick 240 returned 20-60 s
  after each connection regardless of the cfg flag.
- When `BEServer_x64.dll` was removed or renamed in the 1.29 dedicated installation, the
  server bound UDP, printed `BattlEye initialization failed`, and shut down cleanly about
  a minute later ("Termination successfully completed" in the RPT). The sequence looked
  like a healthy boot followed by a silent death.
- In the historical external-manual setup, with server BE intact, `DayZ_BE.exe`
  initialized the client handshake and avoided the kick. The in-game session on
  2026-06-11 reached spawn, equip and inventory with zero kicks. This launcher did not
  invoke that route; the user owned its UI lifecycle and the agent remained in
  quarantine/read-only.

Historical load-order failures that cost a session:

- Removing `@CF` from BaseMods while `@VPPAdminTools` remained caused VPP's embedded CF
  sources to fail with `Unknown type 'RPCManager'`.
- LBmaster operated only when the observed setup included client PBOs (`LBmaster_Core`
  plus the matching client of every `*_Server.pbo`, such as `LBmaster_Groups` for
  `AdvancedGroups_Server`), the server-side PBOs and a per-IP license whitelist. Its
  error log contained the corresponding whitelist URL. In the historical local weapon
  sessions, VPP served as the admin/spawner and LBmaster appeared only in parity runs.
- The historical `@A6_TestPack` subset had been staged with filesystem hardlinks from
  `@LFTEST`; it represented 13 weapon PBOs without duplicate file copies.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from the source pack's lessons-learned corpus so they arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites its originating `LL-NNN`;
the full entry (symptom, origin, evidence) lives there.

Keep each `LL-NNN` citation: the source pack's lessons index finds a promoted rule by searching for that number.

- **LL-118** - In the face of a regression, first compare launch command, `-mod` arguments, paths, and environment with the last passing run. Verify a measurable invariant between both runs and consult ledgers before formulating a code hypothesis.
- **LL-196** - Search for mod's `Print()` and `DbgLog` in the most recent `script_*.log` of corresponding profiles. Use RPT for engine, CE, network, compilation, and native crashes; do not conclude “code did not run” from absence of prints in RPT.
- **LL-197** - Prepare command, paths, and arguments before acquiring a short lease; acquire and use the token in adjacent calls. If there was prolonged analysis, acquire again right before the blocking operation.
- **LL-198** - In managed cycles, execute `adopt → stop` while server and client remain alive; request keeping both open between iterations. If a peer already died, use documented degraded shutdown and wait for auto-heal before relaunching.

## Three pitfalls measured in LFPG S2-B cycle (added 2026-08-29)

All three cost time the same night, with healthy MCP bridge v10. None was from mod.

1. **`action_use` matches by CLASS NAME, not by action text.** The bridge iterates
   `ActionManagerBase.m_ActionsArray` and compares `candidate.Type().ToString() == wantedAction`
   (`DayZ_MCP/scripts/5_Mission/MCPClientBridge.c:1806`). Passing visible text -the one resolving
   `m_Text` from stringtable- returns `action_not_found` even if action is available on
   screen. Pitfall worsens with client in another language, inviting testing the translation:
   language is irrelevant, the key is the class. Take the name from `class X : ActionInteractBase`
   of the mod itself, never from stringtable.

2. **The Steam session check of the prerequisites (`windows-launch-cycle.md`) only WARNS, and also does not run via MCP.** It is
   implemented in the preflight of `templates/dayz-test.ps1`, which is THIS skill's launcher;
   MCP's `dayz_test_run` does not pass through there, so on the route used by MCP sessions the
   check simply does not exist. New variant observed 2026-08-29: `pid=0` **and** `ActiveUser=0`
   with **zero live Steam processes** (already documented signature was populated pid / ActiveUser=0).
   Same outcome: client RPT cut off right after argv, without a single script line, and
   server intact because it does not use Steam. Checking key before launching client takes 10 s.

3. **Active Steam ACCOUNT decides WHICH CHARACTER loads.** (Corrected the same day: see
   refutation at end of point - MOD state does not depend on account.) Restarting
   Steam can return ANOTHER account without warning. Measured 2026-08-29: 03:55 client entered
   as `76561197995575711`, with persisted character at test site; 04:17 client,
   after restart, as `76561198141021937`, with fresh character on coast. Site appeared
   without its devices and **looked like a mod persistence failure**. Registry key tells it
   without opening game: `ActiveUser = steamID64 - 76561197960265728`. Corroborated from outside:
   AddonBuilder prints `Steam_SetMinidumpSteamID:  Caching Steam ID:  <steamID64>` in its output.
   If cycle depends on persisted character, pin ACCOUNT in pre-flight, not just pid.

   **MEASURED REFUTATION THE SAME DAY, and the distinction is subtle and costly.** Returning to correct account
   returns CHARACTER (spawn at exact site, without teleport) but NOT mod state. With
   `...711` server still said `[VanillaWires] Loaded 0 entries from 0` and
   `RebuildTrackedDevices: tracking 0 wired devices`: zero wires across BOTH accounts. Meaning an
   empty test site is NOT explained by account, and whoever assumes so wastes time switching
   logins instead of mounting fixture. Useful rule is: account explains WHERE your
   character appears; mod state is either set up or absent.

## After a reboot, `P:` does NOT exist -- and FileBank packs emptiness with exit 0 (added 2026-08-29)

`P:` is a `subst`, not a disk link: **does not survive a reboot**, let alone a hard
crash. Everything that BI tools and sealed launcher touch hangs from there
(`P:\Mods`, `P:\<Mod>`, `P:\<Mod>_dev\_server\profiles`, `P:\scripts`, `P:\DZ`).

The expensive part is not that it is missing: it is **how it fails**. Measured today, with `P:` absent:

    FileBank.exe -property prefix=<Mod> -exclude <lst> -dst <staging> P:\<Mod>
    exit=0
    <staging>\<Mod>.pbo   ->   79 bytes

**Exit 0 and a 79-byte PBO.** Not a single message. Same failure mode as
AddonBuilder's `Build failed` with exit 0 already documented in this skill: BI tool
considers packing zero files a success.

**Preflight, two lines, before any build or launch:**

    Test-Path -LiteralPath "P:\"          # if False:
    subst P: "<work-drive-folder>"     # in this repo: /dayz-workdrive

And check anchors, not just root: `P:\<Mod>\config.cpp`, `P:\Mods\@<Mod>\Addons`,
`P:\scripts`, `P:\DZ`. **Validate PBO by SIZE and entry count** before
publishing; a three-digit byte package is the signature of this.

## Steam `pid` in registry can be DEAD, and this skill's check was not seeing it (added 2026-08-29)

This skill already requires `HKCU\Software\Valve\Steam\ActiveProcess` to have `pid != 0` and
`ActiveUser != 0`. **Necessary, but NOT sufficient: a non-zero `pid` can be a dead
pid.** After a hard PC crash the key retains the previous Steam pid; Steam
starts again with ANOTHER pid and **does not always rewrite the key in time**. DayZ reads that pid,
looks for that process, does not find it, and dies.

Measured today: registry `pid=25484`, live `steam.exe` `pid=13856`. The "not zero" check
gave GREEN on a broken system. The right question is not "is it zero?" but **"does that
process exist?"**:

    $k  = Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess'
    $st = Get-Process -Name steam -ErrorAction SilentlyContinue
    $ok = $st -and ($st.Id -contains [int]$k.pid) -and $k.ActiveUser -ne 0

**Failure signature, to recognize it without guessing** (three identical reproductions):

| signal | value |
|---|---|
| modal dialog | `unable to locate running instance of Steam` |
| dump exception | `0x80000003` **BREAKPOINT**, same exact address each time |
| client process CPU | **0 s** -- alive but stopped cold |
| client RPT | frozen at **847 B**, header only |
| loaded modules | ~69, last ones from Steam (`gameoverlayrenderer64.dll`, `tier0_s64.dll`) |

`0x80000003` **is not a crash**: it is a deliberate `int 3` of diag exe when popping its dialog. That
is why process remains alive with 0 CPU instead of disappearing, and why there is no failure event
in Windows Event Viewer: DayZ writes its own `.mdmp` and halts.

**Remedy** (revised 2026-09-12): reliable approach is **copying live `steam.exe` pid to the key**,
with guards: stable key between two reads, valid `ActiveUser`, single live `steam.exe` in your
session and in its path, rechecked just before writing and verified after. Restarting Steam
(`steam.exe -shutdown` and relaunch) preserves login but **may not rewrite the key**: measured
that day, Steam started with pid 34316, key stayed at 50968 untouched since previous night
and new pid only appeared in `HKLM\SOFTWARE\Valve\Steam\SteamPID`. If you restart, **check that
key matches a live process** before launching client; it is not enough that Steam "is open".

**The discriminating probe is `SteamAPI_IsSteamRunning`, not `SteamAPI_Init`.** With stale key,
DayZ's own `steam_api64.dll` returned `Init` OK and `IsSteamRunning` FALSE, and client died
just the same; after copying pid both came back true and client entered. A gate that only calls
`Init` yields green on broken state.

**Two Steam facts the registry cannot answer (measured 2026-09-08, LFPowerGrid; SP-382).** (1) WHICH account is logged in: read `logs/connection_log.txt` under the Steam install for `[Logged On, ...] [U:1:<accountID>] RecvMsgClientLogOnResponse() : 'OK'` (`SteamID64 = accountID + 76561197960265728`). (2) Whether that account OWNS DayZ: `steamapps/appmanifest_221100.acf`, field `"LastOwner"`. If the logged-in account is not the LastOwner, the client dies about one second after launch with the same header-only RPT + `0x80000003` signature while every registry check passes green; the dump's `Caching Steam ID: <id>` vs `LastOwner` closes the case in a minute. [EXACT] (measured, SP-382]

**How to read the dump without a debugger**, which is what broke the hypothesis loop: a minidump
brings `MINIDUMP_EXCEPTION_STREAM` (type 6) and `MODULE_LIST` (type 4); with ~60 Python lines one
extracts exception code and the module containing `ExceptionAddress`. Before theorizing
about drivers or mod, **read the instrument**: here `0x80000003` ruled out in one blow
"render crash" and "corrupt mod", which were the two hypotheses on which two boot cycles had already
been spent.

**And the method corollary, valid for any failure after touching the mod:** before searching
for the cause in your change, **deploy PREVIOUS artifact and reproduce**. Here the
pre-surgery PBO failed identically, exonerating work in a single cycle and sending search into
the environment. An A/B with old binary costs same as a hypothesis, and unlike
it, decides.

## Live logs and shutdown of a released run (SP-077)

DayZDiag keeps RPT and `script_*.log` open. `Get-Content` or `ReadAllText` can fail with
`IOException` throughout a waiter. To monitor a live peer, open with explicit sharing:

```powershell
$fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read,
                     [IO.FileShare]::ReadWrite)
try { $text = [IO.StreamReader]::new($fs).ReadToEnd() } finally { $fs.Dispose() }
```

In managed lifecycle, retain `run_id` and use public tools. If a low-level
operation finds a `released` run, the sequence is `adopt` and then `stop`; `stop` can only
return `run_not_adopted`. If another session already cleaned it up, `run_not_adoptable` + zero run processes
+ RPT ending in `Termination successfully completed` describes orderly shutdown, not crash.

## Quoting and triage of a Diag that does not manage to write logs (SP-167)

For `name=value` arguments with spaces, quote the entire token:

```text
-profiles="<profiles-path>"      # NO: quotes only around the value
"-profiles=<profiles-path>"      # YES: a complete token
```

Apply the same pattern to `-config=`, `-mission=`, and `-mod=`. In Windows PowerShell 5.1, passing an
array to `Start-Process -ArgumentList` does not guarantee quoting of each element; do not use that
result as proof of the received argv. The managed path of this skill transports a structured
array and remains the normal way.

For a hang with 0 CPU and no RPT, first run the authorized minimal control
`DayZDiag_x64.exe -server`, with no other arguments, and add one by one. In the measurement that founded this
rule, ~53 modules was "has not yet reached UI" and 69-78 was real startup; use the delta as signature of the
measured build, not as a universal constant. Obtain the real argv with `Win32_Process`: the truncated
RPT header line does not reliably represent it.

## Bare client: separate argument, native path, and mod (SP-174)

Faced with a client that does not start, decide by form before touching the mod:

- **Alive, 0 CPU, without RPT or dump:** apply the minimal control and the previous argument bisection.
- **Dies with header-only RPT + `ErrorMessage_*.mdmp`, without `crash_*.log`, even without mods:**
  launch server of the same build. Stable server with large RPT and bare client crashing points
  to client native/graphics path. Confirm with another project's profile in the same window.
- **Only fails upon adding `-mod`:** then do open mod investigation and its load order.

"It was rebooted" is also measured: compare `Win32_OperatingSystem.LastBootUpTime` and verify that no
process prior to the declared instant survives. Fast Startup can preserve kernel after
shutdown; a full reboot changes that datum.
