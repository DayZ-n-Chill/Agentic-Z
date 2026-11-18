# Diag launch traps

Which traps of the DayZDiag launch flow make a working mod look broken: where `Print` output goes, file patching that loads nothing, dependency mods in the wrong place, third-party scripts that only retail accepts, and the launch flags added in 1.30.

These were measured in game with the diag and retail executables, Community Framework, Dabs Framework, VPPAdminTools and a third-party weapons pack; they are not checked on `P:\`. In this repo the launch, stop and log jobs are `/dayz-launch-test`, `/dayz-stop-test` and `/dayz-logwatch`.

## Five traps of the diag flow

- `Print()` goes to `script_*.log`, not the RPT. On DayZDiag script prints reach only the script log; on the retail server they go to the RPT. A check or monitor that says "RPT" has to be read against the real runtime. The quickest probe: a `Print` (`P:\scripts\1_core\proto\endebug.c:96`) in `OnInit` of a modded `MissionServer` (`P:\scripts\5_mission\mission\missionserver.c:85`) confirms both where prints go and that the mod's hook runs, without a client. To force a line into the RPT on both executables, vanilla has `PrintToRPT` (`endebug.c:99`); its comment warns that "each write means fflush! use with care", so keep it out of per-frame code.
- `-filePatching` does not guarantee the mod's scripts load from the work drive. With `-filePatching` and an empty PBO, the modules compiled without the mod's files and without an error (World: 2240 files against 2245 expected). To detect it, compare the `Module: X; loaded Nx files` counts in the script log with a reference run (the mod adds N files). To avoid it, use `-NoFilePatching`, so scripts always load from a PBO whose content you checked.
- VPPAdminTools needs `@CF` before it in `-mod`. Without it a modal "Unknown type 'RPCManager'" (Can't compile Game module) blocks the server until someone clicks, and leaves no useful trace if nobody looks at the desktop. To read a dialog you cannot see, call `EnumWindows` and `GetWindowText` from PowerShell.
- One Steam account is one client. A second DayZDiag at the same time with the same SteamID (other `-name` and `-profiles`) is kicked with code 179, saying a request has already been sent for this SteamID. Multiplayer tests with an observer need a second account or a second PC.
- The deployed PBO stays locked while the server runs. AddonBuilder's `-clear` and its final copy fail, with "Build failed" as the last line of an otherwise normal log. Close server and client before you deploy again.

## A dependency addon goes in the base mods

When a mod keeps its dependencies in a separate addon (`@<Mod>_deps`, not inside `@<Mod>`), the launch must include it or the client fails to compile: `Can't compile "World": Unknown type '<BaseClass>'`, at a line of the mod's own script. Dependencies (base config and script classes) must load before the mod, so put them first in `-mod=`, before the mod; with `/dayz-launch-test`, name them first in the mod list (dependencies first). The external launcher these traps were measured with (not in this repo) does this with its `-BaseMods` parameter, which goes first in `-mod=`, not `-ExtraMods`, which goes after the mod. A weapon mod that loads correctly takes `-BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<Mod>_deps"`.

Before you relaunch a mod that was tested before, do not assume a default mod set (that launcher's default `-BaseMods`): read `-mod=` from the last successful RPT or launcher output (`<Mod>_dev\_client\profiles\*.RPT`, the "Launch CLIENT" line) and use that set. `P:\` may not be mounted in a new session; mount it before you build or launch (`/dayz-workdrive`).

## Third-party scripts that only retail accepts

Some third-party dependencies produce `SCRIPT (W)` warnings on retail but fatal `SCRIPT (E)` errors on DayZDiag: unclosed braces, "missing function scope", "Opened scope at the end of file". The file patching test route then fails twice over:

- DayZDiag is stricter: the warnings become `Can't compile "World" script module!`, and the diag server dies ("Server process exited before binding").
- A retail client with `-filePatching` crashes on connect with `Unhandled exception ... Access violation. Illegal read ... at 0x0`, call stack `CDPInitServer` and `CDPCreateClient`, and leaves a minidump and a `crash_*.log` in `_client\profiles`. The server stays healthy (`is connected`, then `[Disconnect] -1`).

When your change is already packed in the PBO, launch the retail executables without `-filePatching`. File patching is unnecessary with an up-to-date PBO, dropping it avoids both failures, and a PBO without file patching is how the mod runs on a real dedicated server:

The same mod list as the diag run goes on `-mod=` of both retail executables, Community Framework first. The user runs this launch by hand; the agent only reads while it runs (`troubleshooting.md`, "Third-party modsets on the retail executables").

Confirm the connection without reading the screen: `Select-String 'is connected'` in the server RPT is the reliable signal, and a new `crash_*.log` in the client profile marks the failure. Read both with PowerShell on the host, not through a sandboxed shell whose view of the files can be cached.

## Launch flags added in 1.30

DayZDiag and Workbench take new flags from 1.30, documented in the 1.30 Experimental modding changelog. They were not found as strings in the executable and cannot be checked on `P:\`.

| Flag | Effect |
|---|---|
| `-mod=<folder>` | Accepts an unpacked source folder, not only a packed `@Mod` with PBOs. |
| `-cacheP3D=0`, `-cacheP3D=1` | Turns the P3D cache off or on. |
| `-resolveFilePatchingUsingEnfusion=0`, `=1` | Selects the Enfusion path for file patching. |

Up to 1.29, `-mod` was documented as packed `@Mod` folders only. With an unpacked `-mod`, keep the file patching traps above in mind (the empty PBO that compiles, `-NoFilePatching` for a copy of production). More in `dayz-1-30.md`.
