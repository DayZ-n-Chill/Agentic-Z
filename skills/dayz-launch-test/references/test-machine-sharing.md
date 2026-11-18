# Sharing the test machine

How several sessions share one Windows test machine without evicting each other, how to check who holds it before a launch or a kill, and how to start DayZDiag from an agent's shell so it survives the call.

Measured on one Windows test machine with the DayZ executables, the launcher script `dayz-test.ps1` and dayz-mcp; none of it is vanilla script, so none is checked on `P:\`. The managed rules for a dayz-mcp run are in `mcp/run-lifecycle.md`.

## One machine runs one DayZ at a time

A server binds UDP 2302, and one Steam account is one client: a second client is kicked with 179 (`diag-flow-traps.md`). This bites hardest when several agent sessions each test a different mod. A launcher that kills every `DayZDiag_x64` process before starting lets whichever session launched last evict the others in the middle of their Central Economy boot. The time to get ready (build plus Central Economy boot, 2 to 4 minutes) is longer than the minute or so between relaunches, so no smoke test completes while a second session keeps relaunching; process ids and start times changed about every minute.

The current launcher no longer does that: `-Kill` needs the exact `-RunId` and stops only that managed run. dayz-mcp's broker registration (`--client`) lets several sessions hold MCP tools at once, but they still share one game. The rule below applies to any launch or kill done by hand.

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

- A `DayZDiag_x64.exe` started with `Start-Process` from an agent's background task dies when that task ends, and so does the bind wait of `dayz-test.ps1` run in the background. The tool kills the task's child processes as it closes: the server drops partway through the Central Economy boot without writing its own RPT (it binds 2302 and disappears), while a client started in another call survives, leaving one DayZDiag and a dead server. `Start-Process -PassThru` without `-Wait` is not enough when the call runs in the background.
- Start server and client through a `.bat` with `start ""`, which puts them in their own process group outside the agent's tree. They survive across calls and write their RPT. Use one server `.bat` with `start "" "DayZDiag.exe" -server ...` and one client `.bat` with `... -connect=127.0.0.1`, both with the same mod set (`-mod="...;@<Mod>;@DayZ_MCP"` with absolute `!Workshop` paths). Poll the bind yourself (`Get-NetUDPEndpoint -LocalPort 2302`), and wait for the connect with a poller that only reads: a `Start-Process` inside it kills the game when the poller closes.
- The bind wait of `dayz-test.ps1` can report a false failure. At 240 s the server had bound 2302 (`Get-NetUDPEndpoint` showed it), yet the script reported "Timed out waiting for bind", refused to start the client and killed the server it had started. Let `-Build` build the PBO, which works, ignore the launch failure, and start server and client by hand through the `.bat` files.
- The MCP bridge's `version_state=legacy_blocked` ("poll did not include ver=") is an unfinished init, not a version mismatch. It turns to `ok` once the server mission finishes loading, after 1 to 2 minutes. Do not register the server again or redeploy; wait and check `bridge_status` again (`mcp/README.md`).

On a machine with dayz-mcp's registered launcher these hand launches are the unmanaged fallback in `managed-launcher.md`, not the default.

## `Start-Process` inside a loop in the PowerShell tool

An inline command with `Start-Process` inside a `foreach`, and an `ArgumentList` quoted with backticks (`` `"$x`" ``), triggers `EPERM: operation not permitted, uv_spawn powershell.exe` every time: the shell fails to spawn, not the command. Write the loop to a `.ps1` on disk and run it (`& script.ps1`), or pass `Start-Process -ArgumentList @('a','b','c')`, an array without backticks. A single inline `Start-Process` usually works; the `foreach` with backticks is what breaks.
