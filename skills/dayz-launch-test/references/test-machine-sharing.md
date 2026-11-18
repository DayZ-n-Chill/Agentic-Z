# Sharing the test machine

How several sessions share one Windows test machine without evicting each other, how to check who holds it before a launch or a kill, and how to start DayZDiag from an agent's shell so it survives the call.

Measured on one Windows test machine with the DayZ executables and per-mod launch scripts; none of it is vanilla script, so none is checked on `P:\`.

## One machine runs one DayZ at a time

A server binds UDP 2302, and one Steam account is one client: a second client is kicked with 179 (`diag-flow-traps.md`). This bites hardest when several agent sessions each test a different mod. A launcher that kills every `DayZDiag_x64` process before starting lets whichever session launched last evict the others in the middle of their Central Economy boot. The time to get ready (build plus Central Economy boot, 2 to 4 minutes) is longer than the minute or so between relaunches, so no smoke test completes while a second session keeps relaunching; process ids and start times changed about every minute.

Never write a launcher that kills by executable name. `/dayz-stop-test` kills every `DayZDiag_x64.exe` on the machine, so run it only when the machine is yours. The rule below applies to any launch or kill.

When other sessions may be open, make sure exactly one session owns the machine before you launch, and after your launch connects, confirm the running `DayZDiag` command lines name your mod before you trust anything you see.

## Check who holds the machine before any kill or launch

Never kill blindly. A blind kill of another mod's server evicts a live session, and a relaunch from that session can then kill your server mid-test.

1. List the holders on the host: `Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe' OR Name='DayZServer_x64.exe'"`, and read each `.CommandLine` for its `@<Mod>` token and its `-profiles=...<OtherMod>_dev` path. Check `Get-NetUDPEndpoint -LocalPort 2302` for the process holding the port.
2. If a holder names a different mod than yours, it is another live session. Do not kill it. Tell the user ("port 2302 is held by @<OtherMod>; should I stop it, or is that session still active?") and wait for an answer. Stop without asking only a process that is clearly yours (same `@<Mod>`) or one the user confirmed is stale.
3. `DayZServer_x64.exe`, the retail dedicated server, is a separate process from `DayZDiag_x64`: a diag-only kill misses it, and killing it evicts a retail session. Cover both names when you clean up your own.
4. Killing someone else's DayZServer while it writes corrupts the shared persistence at `DayZServer\mpmissions\<mission>\storage_1`. The next boot dies on `!!! Serious stream damage detected during load` and exits before the UDP bind. Rename `storage_1` and the server creates a fresh one; better, do not kill other sessions' servers.
5. After your own launch binds, confirm the running command line names your `@<Mod>` before you trust any observation in game.

## Starting DayZDiag from an agent's shell

When a smoke test is started from the agent's tool calls rather than by hand:

- A `DayZDiag_x64.exe` started with `Start-Process` from an agent's background task dies when that task ends, and so does a launch script's bind wait run in the background. The tool kills the task's child processes as it closes: the server drops partway through the Central Economy boot without writing its own RPT (it binds 2302 and disappears), while a client started in another call survives, leaving one DayZDiag and a dead server. `Start-Process -PassThru` without `-Wait` is not enough when the call runs in the background.
- Start server and client through a `.bat` with `start ""`, which puts them in their own process group outside the agent's tree. They survive across calls and write their RPT. Use one server `.bat` with `start "" "DayZDiag.exe" -server ...` and one client `.bat` with `... -connect=127.0.0.1`, both with the same mod set (`-mod="...;@<Mod>"` with absolute `!Workshop` paths). Poll the bind yourself (`Get-NetUDPEndpoint -LocalPort 2302`), and wait for the connect with a poller that only reads: a `Start-Process` inside it kills the game when the poller closes.
- A bind wait can report a false failure. At 240 s the server had bound 2302 (`Get-NetUDPEndpoint` showed it), yet a launch script reported "Timed out waiting for bind", refused to start the client and killed the server it had started. Check the port yourself before you trust a timeout.
- A stock mission runs the Central Economy start for 1 to 3 minutes after the bind. Do not spawn test objects until `connected to server` shows in the server's `script*.log`. Poll the log directly on the host; a shell that reads it through a file system bridge can serve a cached copy.
- Do not use `Start-Process -ArgumentList` for DayZDiag: in Windows PowerShell 5.1 an array does not guarantee quoting of each element. In six paired attempts, `cmd /c start` with literal quotes around each value containing spaces started the game, while `Start-Process -ArgumentList` hung at about 0.06 s of CPU without writing even the RPT header.
- When `cmd /c start` launches a `.bat`, the new window runs `cmd /K`: an `exit /b` at the end of the bat exits the script, not the interpreter, and one idle console window stays behind per launch. Wrap it in a second `cmd /c`: `cmd /c start "<title>" cmd /c "<abs bat>"`. A preflight failure with `pause` inside the bat stays visible.
- A launch from the agent's own shell that stays alive with 0 CPU and writes no RPT is a launch context problem, not a bad argument or mod. Hand the user one server `.bat` and one client `.bat` to double-click in the desktop session, and read `script.log` and the RPT with `FileShare.ReadWrite` (`client-startup-failures.md`, "Reading live logs").

Command lines for those `.bat` files, with literal quotes around each value that has spaces (not tested as written):

```bat
DayZDiag_x64.exe -server "-config=<serverDZ.cfg>" "-profiles=<server-profiles>" "-mission=<mission-abs>" "-mod=<mod-abs-semicolon-list>" -filePatching -port=2302
DayZDiag_x64.exe "-mod=<mod-abs-semicolon-list>" -connect=127.0.0.1 -port=2302 "-profiles=<client-profiles>" -name=Dev -window -filePatching
```

Since 1.30 both may add `-cacheP3D=1` and `-resolveFilePatchingUsingEnfusion=1` (the second needs `-filePatching`), and `-mod=` may name an unpacked source folder (`dayz-1-30.md`).

## Traps on a hand launch that do not come from the command line

- **Stuck Workshop.** A `workshop_log.txt` with "No workshop depot defined, skipping non-legacy item" on each item (`NeedsDownload=1`) clears with `steam://validate/221100`, which refreshes the app info.
- **Default RPT folder.** If `-profiles` does not reach the executable, DayZDiag writes the RPT and script log to `%LOCALAPPDATA%\DayZ`. Look there before deciding nothing was written.
- **A frozen RPT.** Diag writes the RPT through a buffer of about 52 KB, so compare process CPU over 30 s before calling the process dead (`in-game-check-validity.md`). On a work drive inside a OneDrive folder `Get-Item` can also report the wrong size (927 bytes against 52 KB real); read with `Get-Content` and count.
- **Codex and `-ExecutionPolicy Bypass`.** The Codex CLI sometimes refuses a command containing `-ExecutionPolicy Bypass` by its own policy. That is the agent refusing, not the host: the PowerShell policy is not `Restricted` because of it and Microsoft Defender does not stop the launch. Leave the flag out or let Claude or the user launch. Never disable Defender or add exclusions for it.

## `Start-Process` inside a loop in the PowerShell tool

An inline command with `Start-Process` inside a `foreach`, and an `ArgumentList` quoted with backticks (`` `"$x`" ``), triggers `EPERM: operation not permitted, uv_spawn powershell.exe` every time: the shell fails to spawn, not the command. Write the loop to a `.ps1` on disk and run it (`& script.ps1`), or pass `Start-Process -ArgumentList @('a','b','c')`, an array without backticks. A single inline `Start-Process` usually works; the `foreach` with backticks is what breaks.
