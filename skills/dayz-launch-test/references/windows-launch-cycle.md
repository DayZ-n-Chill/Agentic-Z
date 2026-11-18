# The Windows launch cycle

How the build, deploy and launch loop runs on one Windows machine: what a launch needs before it starts, why each requirement matters, and the default mods and admin tools a test server loads. How a build actually reaches the engine (include lists, file patching, absolute mod paths) is in `windows-build-and-mount.md`.

In this repo the build step is `/dayz-build-pbo`, launching server and client is `/dayz-launch-test`, stopping is `/dayz-stop-test`, reading logs is `/dayz-logwatch`, and the pass or fail verdict is `/dayz-gate`. The test server instance (`.server/<instance>/`, its `serverDZ.cfg`, mission and profiles) is made by `/dayz-add-server`.

Tool and third-party mod behaviour (Community Framework, Dabs Framework, VPPAdminTools) was measured on one Windows test machine and is not checked on `P:\`; most of it cannot be, because it is not vanilla script.

## What the cycle does

It closes the dev loop on one Windows machine: pack the PBO, deploy it where the engine reads mods, and launch `DayZDiag_x64.exe` with `-filePatching` so script and config edits might be picked up without binarizing again (what that really covers is in `windows-build-and-mount.md`). The server starts first, then the client connects to it on `127.0.0.1`.

From 1.30, `-mod` may point at an unpacked source folder, RV configs load unpacked, and there are new flags `-cacheP3D=0/1` and `-resolveFilePatchingUsingEnfusion=0/1`. These are documented for 1.30 Experimental and cannot be checked on `P:\` (`dayz-1-30.md`).

Use it when the user wants to see a mod running in game, iterate scripts and configs, or stand up a local server and client. Do not use it to write the mod (the model pack `skills/_shared/models/` and the Enforce Script pack `skills/_shared/enscript/`), to validate or pack only (`/dayz-build-pbo`), or to configure a production server. The retail `DayZ_x64.exe` is for the final check before release only, run by hand; default to the diag exe.

Before 1.30 the retail executables on the test machine did not finish loading a mission, so a retail run there only proved that `3_Game` and `4_World` compile, and `5_Mission` compiled only on diag. On 1.30 the retail DayZServer loads the mission and runs once `serverDZ.cfg` sets `instanceId` (below). Report script coverage per module, never as one green retail result.

## Run the offline linter first

A boot costs minutes; the linter costs about 60 s and catches what you would otherwise find in an RPT:

```text
py scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

- Judge it on `len(errors)`, never on `status`: `WARN` with zero errors is valid.
- The path is relative to the Agentic-Z repo root, not your mod folder. From a mod folder give the absolute path to the repo checkout, or the command dies with `No such file or directory` and reads as "not installed".
- `/dayz-lint` checks the mod setup; this validator checks the code. Compare against the base branch to know whether an error is yours.
- It does not replace a boot: Enforce Script only compiles when the world loads. But `errors > 0` means the boot will fail, so there is no need to launch to find out. Run it whenever a change deletes classes, files or `config.cpp` entries.

The linter does not see an undeclared member. An `obj.m_Field` where the type of `obj` does not declare `m_Field` passes with 0 errors, and on world load the module dies with `Cant compile "World" script module!` plus `ACCESS_VIOLATION`. A review misses it too, because an incrementing counter looks reasonable in a diff, for example a field read on one class when only the neighbouring class in the same file declares it. If that code runs only on the client render path, the server still starts, so a check that reads only the server log passes it.

A quick sweep catches this before a boot when a change touches many files: for each typed local `Type obj = ...` in the diff, check that each `obj.m_Field` is declared in `Type` or a parent, resolving inheritance with a regex census of `class X : BASE {...};` across all `scripts/`. It runs in seconds. It covers only locals with an explicit type (not member access, function returns or `this`), but it covers this pattern.

## What a launch needs

`/dayz-preflight`, `/dayz-add-server` and `/dayz-launch-test` check these between them.

| Requirement | Why |
|---|---|
| `DayZDiag_x64.exe` for client and server | Retail stops past the loading screen with `-filePatching`. |
| `P:\Mods` is a junction to `<DayZ>\!Workshop` | Deployed PBOs must land where the engine looks. `mklink /J` creates it with no admin rights; `/dayz-preflight` does this when it is missing. |
| `allowFilePatching = 1` in the server's `serverDZ.cfg` | Otherwise the client is kicked with `0x00020005`. |
| An absolute mission path | Otherwise the server loads an empty mission. That holds for Windows and DayZDiag; the native Linux `DayZServer` is the opposite (`linux.md`). |
| `class Missions { class DayZ { template="<mission>"; }; };` in `serverDZ.cfg` | Without it a dedicated server with a `dayzOffline.*` mission ends itself before the mission loads (RPT countdown `[Server] :: termination in: N`). With it the server stays up with no client, which a server-side probe in the mission `init.c` needs. Measured on DayZ 1.30. |
| `instanceId` in `serverDZ.cfg` | Without it a minimal config counts down even with `class Missions`. On the retail Windows DayZServer 1.30, a hand-written `serverDZ.cfg` with `class Missions` and no `instanceId` counted down from `[Server] :: termination in: 10` right after `NETWORK : server: Player dpid=2 added`, with no `SteamGameServer_Init` line; adding `instanceId = 1;` alone let it pass Steam init, load the mission and run. Only this key was tested. |
| A live Steam session, for any launch that starts a client | `HKCU\Software\Valve\Steam\ActiveProcess` needs `pid != 0`, `ActiveUser != 0`, and a `pid` that belongs to a running `steam.exe` (after a crash the key can keep a dead pid). `/dayz-launch-test` checks only that `steam.exe` runs. |
| Mission storage written by the same mod set | Storage written by one mod set crashes or corrupts under another (`build-and-storage-traps.md`). Copy `storage_1` aside before you switch sets, and watch both `Failed to read modstorage` and `Scripted variables corrupted`, because the one that shows may not be the one you expect. |

For a stale Steam key, copy the running `steam.exe` pid into the key's `pid` value from a shell outside any sandboxed app: a write from inside one reaches only that app's private registry copy (`diag-direct-launch.md`). Guard the write: the key unchanged between two reads, `ActiveUser` non-zero, exactly one running `steam.exe`, checked again just before writing and verified after. Restarting Steam keeps the login but may leave the key pointing at the old pid with the client still dead, so restart only when no Steam is running or `ActiveUser` is 0. The full procedure is in `client-startup-failures.md`, "The Steam pid in the registry can be dead".

Paths come from environment variables first and Steam defaults second (`DAYZ_GAME_PATH`, `DAYZ_DIAG_PATH`, `DAYZ_TOOLS_PATH`). The work drive is always `P:\`.

## Default mods and admin tools

A common test set puts three base mods first, CF leftmost, using the folder names Steam Workshop installs: `@CF;@Dabs Framework;@VPPAdminTools`, then the mod under test. With `/dayz-launch-test`, name them first, in that order, before the mod.

`@VPPAdminTools` gives in-game admin tools (teleport, spawn, godmode, object editing). Access is by SteamID64, not a server password, but the file layout differs between VPPAdminTools versions, and the version measured reads the `Permissions\` folder, not the root `SuperAdmins.json`. Because each test server has its own `-profiles`, seed these files there, and never overwrite a password that is already hashed:

| File under `<server profiles>\VPPAdminTools\` | Content |
|---|---|
| `Permissions\SuperAdmins\SuperAdmins.txt` | One SteamID64 per line; the file the measured version reads. |
| `Permissions\credentials.txt` | The in-game login password on line 1. VPPAdminTools hashes it on first boot and the raw value is then lost. There is no default; seed it only when the operator gives a password, and never print it. |
| `SuperAdmins.json` | `{ "SUPER_ADMINS": ["<SteamID64>"] }`, the older layout, still seeded for older builds. |

The SteamID can be copied from the retail config at `%LOCALAPPDATA%\DayZ\VPPAdminTools\SuperAdmins.json`. To change the admin or the password later, edit these files and restart the server.

Set `vppDisablePassword = 1;` in `serverDZ.cfg`, so a superadmin listed in `SuperAdmins.txt` gets in with no password. Checked against the VPPAdminTools source, not vanilla and not on `P:\`: line 14 of its own `missionServer.c` calls `DisablePasswordProtection(true)`, and access follows from `HasUserGroup` reaching `IsSuperAdmin` (line 693 of its `PermissionManager.c`). The password route breaks over hashing and differences between versions, and turning it off removes that whole class of failure; a seeded `credentials.txt` only matters if you remove `vppDisablePassword` to test with a password. In game, End toggles admin and Home opens the menu; rebind them under Options, Controls if a fresh client profile lost them.

`/dayz-add-server` sets `verifySignatures = 0`, so VPPAdminTools' signed PBO loads without its `.bikey`.

## Out of scope

Writing the mod, production server config (the stock 1.30 formats are in `server-and-mission-config.md`), Central Economy and persistence tuning beyond the minimal dev `serverDZ.cfg`, and signing for a Workshop release. PBO validation and packing belong to `/dayz-build-pbo` and `/dayz-release-pack`; `windows-build-and-mount.md` records what those skills must guarantee.

## Related files

| Question | File |
|---|---|
| Why did the build drop scripts, does file patching serve my edit, why did the mod not mount | `windows-build-and-mount.md` |
| A launch shows a known symptom | `troubleshooting.md`, then `client-startup-failures.md` |
| Diag-only traps, dependency addons, retail-only third-party scripts | `diag-flow-traps.md` |
| Several sessions share the machine; launching from an agent's shell | `test-machine-sharing.md` |
| Probing a new mod's mount, copying test helpers to another mod | `mount-probe-and-test-helpers.md` |
| Grabbing the client window; runs that never load textures | `window-capture-pitfalls.md` |
| The vehicle first-person eye moves between runs | `vehicle-first-person-eye.md` |
| Server config and launch rules | `skills/_shared/conventions/server.md`; `/dayz-preflight` for the work drive, the `P:\Mods` junction and the installs |
| Script or engine errors in a launch | `debug-protocol.md` and `error-catalog.md` |
| The rest of the loop (look up, write, build, boot, check, publish) | `mod-loop.md` |
