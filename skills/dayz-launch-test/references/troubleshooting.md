# Troubleshooting a launch

Which symptom of a local test session points at which cause, where each log lives, a vanilla error stack that is not the mod's fault, what to know about third-party modsets on the retail executables, and three traps from actions and Steam. Failures that stop a client from starting at all (a missing work drive, a stale Steam key, quoting, a client that writes no log) are in `client-startup-failures.md`.

In this repo the build step is `/dayz-build-pbo`, launching is `/dayz-launch-test`, stopping is `/dayz-stop-test`, reading logs is `/dayz-logwatch`, and the verdict is `/dayz-gate`. `P:\<Mod>` is the junction to `workspace/<ModName>/`, and `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

The causes below were measured on one Windows test machine; BattlEye, Steam, VPPAdminTools, LBmaster and Community Framework behaviour is not checked on `P:\`. Vanilla script facts cite their file.

## Symptom to cause

| Symptom | Cause | Fix |
|---|---|---|
| Client kicked with `0x00020005` | File patching mismatch | `allowFilePatching = 1;` in `serverDZ.cfg`. |
| Kicked with `0x00010002` | Signatures do not match | Rebuild the PBO, or `verifySignatures=0` (the dev config already sets it). |
| VPPAdminTools asks for a password although `SuperAdmins.txt` lists you | The `serverDZ.cfg` predates `vppDisablePassword = 1;` | Add the line and restart the server (`windows-launch-cycle.md`, "Default mods and admin tools"). |
| "PlayerConnect will stay disabled" | Empty mission, or `-mission` not absolute | Pass an absolute mission path. On the native Linux `DayZServer` it is the reverse: a relative `mpmissions/<name>` (`linux.md`). |
| Stuck past the loading screen | Retail exe with file patching | Use `DayZDiag_x64.exe`. |
| Server or client does not exit | The process is still running | Stop only the process you started, by its process id, or ask the user who started it (`test-machine-sharing.md`). Do not hunt for another process to kill. |
| Mod not visible in game | The PBO landed outside `!Workshop` | Make sure `P:\Mods` is a junction. |
| Server boots, then dies before the UDP bind; RPT shows `!!! Serious stream damage detected during load` | Half-written Central Economy storage after an unclean server kill; it looks like a mod bug | Rename or wipe `<mission>\storage_1` before the next boot; the server creates a fresh one. Do this after every unclean server kill. |
| Mod class missing, `CreateObjectEx` returns null, no RPT error | A relative `-mod=@Name` did not mount | Use absolute `!Workshop` paths; `/dayz-launch-test` does this (`windows-build-and-mount.md`, "Mod paths must be absolute"). |
| Mod mounts (its `CfgPatches` shows in `defines:`) but no script or hook runs | AddonBuilder's binarize mode dropped the `.c` files | Build script mods with `-packonly` (`/dayz-build-pbo` handles it), and search the deployed PBO for a known class name (`windows-build-and-mount.md`). |
| The same compile error survives rebuilds although the source on disk is fixed | AddonBuilder's incremental sync to `P:\temp\<Mod>` served stale source, and file patching did not override the PBO's scripts either | `/dayz-build-pbo` wipes `P:\temp\<Mod>` before every build; by hand, pass `-clear` or delete the temp folder first. The tell is an error on a line you already fixed. |
| `-Build` ran but the game shows the old config or `.p3d` | The running server locked the deployed PBO, so AddonBuilder's copy failed: `[ERROR] Build failed` at the copy step, with exit 0 | Stop the session that holds the PBO, check that its processes are gone, then build and relaunch. Check the PBO's time stamp changed. |
| Kicked with `240 ("Game restart required")` 20 to 60 s after connecting | Server BattlEye is active and the client started bare (`DayZ_x64.exe` never starts BattlEye) | See "BattlEye on the retail pair" below. The user decides whether to open retail by hand; the agent does not launch it. |
| Retail server binds, then dies about a minute later with `BattlEye initialization failed`; the RPT ends "Termination successfully completed" | `BEServer_x64.dll` missing or renamed | Any repair is the user's, outside the agent's work; the agent only reads. |
| Modal "Compile error ... Missing function scope" naming a third-party file at boot | The diag exe compiles third-party packs strictly | Report the incompatibility (below). Do not chase the third-party error. |
| A `SCRIPT (E)` stack at every DayZDiag mission start, once per peer | Vanilla, not the mod | Nothing to fix; see the next section. |

## A vanilla error stack at every diag mission start

Each DayZDiag mission start logs a `SCRIPT (E)` block once per peer: the `-- Stack trace --` header, the frames `GetPlugin()` of `pluginmanager.c`, `OnInit()` of `pluginitemdiagnostic.c`, `PluginsInit()`, `PluginManagerInit()`, `MissionBase()` and the mission's own frame (`CreateMission()` of `somemission.c` on a client, a frame of the mission's `init.c` on a server), then a `-----------------` closing line.

| Vanilla line | What it does |
|---|---|
| `P:\scripts\4_world\plugins\pluginmanager.c:77` | Registers `PluginItemDiagnostic` with `RegisterPluginDiag`, kept under `DIAG_DEVELOPER` (`:249` to `:251`), which DayZDiag defines. |
| `pluginmanager.c:89` and `:217` | Registers `PluginConfigDebugProfile` with `RegisterPluginDebug`, kept only when `g_Game.IsDebug()`, an internal build. |
| `P:\scripts\4_world\plugins\pluginbase\pluginitemdiagnostic.c:94` | `OnInit` asks for `GetPlugin(PluginConfigDebugProfile)`. |
| `pluginmanager.c:340` and `:341` | Under `#ifdef DIAG_DEVELOPER`, prints `Module ... is not Registred in PluginManager.c!` and dumps the stack. The caller checks for null, so the run goes on. |

The `Module PluginConfigDebugProfile is not Registred` line comes before the stack in the DayZDiag 1.30 RPTs measured, but it can be missing: a 1.29 client RPT does not carry it, and neither do RPTs of runs with a mod that overrides `PluginsInit`. The stack itself shows on 1.29 too. A mod with a `modded` `PluginsInit` adds one frame of its own to the stack.

A test that counts `SCRIPT (E)` lines as addon errors should leave out the whole block, header to closing line, and recognise it by its frames, not by the `Module PluginConfigDebugProfile` line. It is 8 `SCRIPT (E)` lines per peer per mission start (header, six frames, closing line), one more for each mod that overrides `PluginsInit`.

## Where each log lives

`script.log` holds script compile and runtime errors; `*.RPT` holds engine errors (missing assets, malformed configs); `crash_*.log` holds handled exceptions, not hard crashes. All sit under the `_server\profiles\` and `_client\profiles\` folders. For a structured diagnosis follow `debug-protocol.md` and check `error-catalog.md`.

## Third-party modsets on the retail executables

The diag exe compiles Enforce Script strictly; the retail executables compile leniently. Some third-party packs use syntax that retail accepts as `FIX-ME` warnings and diag rejects as fatal: a weapons pack with braceless one-liners (`override typename GetInputType() return X;` in its optic and weapon scripts, "Missing function scope"), and LBmaster_Core ("Unsafe down-casting"). This is a diagnosis, not another way to launch. The agent reports the incompatibility; opening retail by hand is the user's decision, and while such a game runs the agent only reads (`test-machine-sharing.md`).

What the hand-opened retail route showed, kept for diagnosis:

- The retail server is `DayZServer_x64.exe` from the dedicated install. The retail game exe with `-server` booted the Central Economy and then ended while loading graphics resources (`Water/*.edds`, "Termination successfully completed").
- The dedicated binary already runs as a server. Adding `-server` also trips LBmaster's startup check (`Error: Remove Startup Parameter: -server`).
- LBmaster loads its server-only addons through `-serverMod=`. Its `*_Server.pbo` files sat under `@SomeFolder\addons\*.pbo`, and their paths resolve absolutely like `-mod` paths.
- The launcher's bind wait reported "exited before binding" while the server was still booting the Central Economy; the first boot of the large pack took minutes, and UDP 2302 opened later.

### BattlEye on the retail pair

- The retail server loads its BattlEye module (`profiles\BattlEye\BEServer_x64.dll`, downloaded on its first BattlEye boot) and kicks clients that have not started BattlEye, the bare `DayZ_x64.exe` client included, with 240 "Game restart required".
- `BattlEye = 0;` in `serverDZ.cfg` hid this for a while, then stopped hiding it after a system-wide BattlEye service update under `%ProgramFiles(x86)%\Common Files\BattlEye`. The file times there identify the update; after it, kick 240 came back 20 to 60 s after each connect whatever the cfg said.
- With `BEServer_x64.dll` removed or renamed in the 1.29 dedicated install, the server bound UDP, printed `BattlEye initialization failed` and shut down cleanly about a minute later ("Termination successfully completed"). It looks like a healthy boot followed by a silent death.
- With server BattlEye intact, `DayZ_BE.exe` starts the client handshake and avoids the kick: a session through it reached spawn, equipment and inventory with no kick. `/dayz-launch-test` does not use that route.

### Load order

- Removing `@CF` from the base mods while `@VPPAdminTools` stays makes VPPAdminTools' embedded CF sources fail with `Unknown type 'RPCManager'`.
- LBmaster works only with its client PBOs (`LBmaster_Core` plus the client matching each `*_Server.pbo`, such as `LBmaster_Groups` for `AdvancedGroups_Server`), its server PBOs and a license allowed for the machine's IP. Its error log names the license URL. For weapon tests VPPAdminTools served as admin tool and spawner; LBmaster was loaded only for runs that had to match a live server.
- A test subset of a large weapons pack can be staged with filesystem hardlinks from the full pack's folder: 13 weapon PBOs with no duplicate copies.

## Four rules for a test cycle

- Faced with a regression, first compare the launch command, the `-mod` arguments, the paths and the environment with the last passing run, and check a measurable fact in both runs before you form a theory about the code.
- Look for the mod's `Print()` and `DbgLog` output in the latest `script_*.log` of the matching profile. Use the RPT for engine, Central Economy, network, compile and native crash messages; never conclude "the code did not run" from prints missing in the RPT.
- Prepare the command, paths and arguments before the launch, so the steps after it run back to back.
- Stop server and client while both are alive, and ask for both to stay open between iterations. If a peer has died, collect its minidump and logs before you relaunch.

## Three traps from actions and Steam

None of these came from the mod.

1. Name an action by its class, not by its text. A script that looks an action up in the player's action list compares the class name (`Type().ToString()`); the visible text, which `m_Text` resolves from the stringtable, finds nothing even while the action shows on screen. The client's language is irrelevant; the key is the class. Take the name from `class X : ActionInteractBase` in the mod, never from the stringtable.
2. A Steam check that looks only at the process does not catch every stale session: one launch went ahead with `pid=0` and `ActiveUser=0` and no Steam process running, a second signature next to the known one of a filled `pid` with `ActiveUser=0`. Either way the client RPT stops right after the command line without a single script line, and the server is fine because it does not use Steam. Checking the key before launching a client takes 10 s.
3. The active Steam account decides which character loads, and nothing else. Restarting Steam can bring back a different account without warning: the client entered first under one account with the saved character at the test site, and after a Steam restart under another account with a fresh character on the coast, so the site looked empty and the mod's persistence looked broken. The registry gives the account without opening the game: `ActiveUser = steamID64 - 76561197960265728`. AddonBuilder also prints `Steam_SetMinidumpSteamID:  Caching Steam ID:  <steamID64>`. If a cycle depends on a saved character, pin the account in the preflight, not just the pid. Going back to the first account brought the character back at the exact site but not the mod's state: the server log still reported zero saved entries under both accounts. The account explains where your character appears; the mod's state is either set up or not.
