# Scripted test cells

How to set up a scripted test, a "cell", that boots the game, drives it without a person and reads its verdict from the logs: where the test code lives, what a test mission may do, which diag defines exist, and who closes the processes. Seating a player in a vehicle by script is in `test-cell-vehicles.md`; gates, teardown and what makes a run count as evidence are in `test-cell-evidence.md`. The ready-made self-reporting test mod is `../assets/autotest-mod/` (`linux-headless-client.md`).

Vanilla script facts cite the file on `P:\`. The rest was measured in game on a Windows test machine with the third-party dayz-mcp tool, Community Framework and test vehicle mods, and is not checked on `P:\`.

## Setting up a headless cell

Reuse the launcher's build and deploy step, then add these:

1. Launch through dayz-mcp's `dayz_test_run` when the machine uses it. It owns the lease, so do not take a separate one first (`managed-launcher.md`). Keep its `run_id` and poll the RPT read only. Never start DayZDiag yourself with `Start-Process` beside it, and never call the approved launcher directly.
2. Skip `CreateHive()` in a test mission `init.c` for a physics test. The Central Economy loads about 20,000 loot items and delays the mission loop by minutes.
3. Connect a client before you spawn a vehicle. A `CarScript` vehicle only ticks `OnUpdate` and simulates with a player present, so give the cell a mode that connects a second diag instance to `127.0.0.1`.
4. Put cell code inside the mod, not in the mission. Spawn on connect, an engine watcher and test hooks belong in the mod under `#ifdef DIAG` plus a launch parameter of the mod's own, for example a `modded class MissionServer` in `5_Mission` switched on by `-<mod>AutoGetIn=1` and read in its `PlayerBase`. The mission lives in the Steam folder (`DayZServer\mpmissions\<mission>\init.c`), which no backup or repo carries; cell code written there was gone on a second machine days later. Inside the mod it travels with the PBO, is versioned, and stays inert in retail because the flag is absent.
5. Start the engine before the crew sits when the mod puts a parked vehicle to sleep; a sleeping body rejects the injected get-in action (`test-cell-vehicles.md`).

## PowerShell traps that hang a cell with no error

- Never name a function parameter `$Args`. It is the automatic variable, so `@Args` splats nothing, and `& python` with no arguments opens the interactive prompt, which never returns.
- `& native 2>&1` under `$ErrorActionPreference = 'Stop'` turns any stderr line into a terminating error in Windows PowerShell 5.1. Call native tools through a helper that switches to `Continue` and returns the text and `$LASTEXITCODE`.
- The DayZ client needs a live Steam session: `HKCU\Software\Valve\Steam\ActiveProcess` must hold a `pid` and an `ActiveUser` other than 0. A Steam restarted minutes earlier can show the `pid` with `ActiveUser = 0`; the client then dies at start with an RPT of about 1 KB and an `ErrorMessage_*.mdmp`, while the server, which needs no Steam, boots. `steam.exe -shutdown` and a relaunch filled the key again in about 20 seconds. Check the key in every cell's preflight.

## What a test mission `init.c` may do

A test mission that adds a `modded class` for a `4_World` type fails with `Unknown type`, for a concrete class (`SmallStone`), a base class (`BuildingBase`) and a mod's own `4_World` class alike. Offline text checks do not catch it. Measured on a DayZ 1.29 diag server.

- Call a class that is already compiled and already has the method under test. A new method goes into the mod, in the same script module and PBO as the class, as a separate change; never add it with a `modded class` in `init.c`.
- Write each test call and each boolean expression on one line. A line starting with `&&` gave `Incompatible parameter` and `Syntax error`.
- Before spending runs, do one control run that only checks that the Game, World and Mission modules loaded, that `OnInit` ran and that the result marker printed.

## `DEVELOPER` is not defined in DayZDiag

The standard `DayZDiag_x64.exe` defines `DIAG` and `DIAG_DEVELOPER` but not `DEVELOPER`: the `defines:` line of both peers' `script_*.log` lists `DIAG,DIAG_DEVELOPER,...,FEATURE_NETWORK_RECONCILIATION` and no `DEVELOPER`. Every vanilla `#ifdef DEVELOPER` block is therefore absent from the build, for example `SetGetInVehicleDebug` and `TryGetInVehicleDebug` (`P:\scripts\4_world\entities\manbase\playerbase.c:3531` to `:3549`), `DayZPlayerSyncJunctures.SendGetInVehicle`, `SJ_DEBUG_GET_IN_VEHICLE` and much of `plugindeveloper.c`.

- `OnDebugSpawn` working proves nothing about `DEVELOPER`: it has no define guard (`P:\scripts\3_game\entities\entityai.c:3955`), so it runs in every build.
- A mod whose PBO calls a symbol vanilla defines only under `#ifdef DEVELOPER`, such as `SendGetInVehicle`, does not compile, and every script of the mod drops. That is not a silent no-op, unlike `ExecuteEnforceScript`, which is developer only and returns false at run time.
- Gate test code with `#ifdef DIAG` or a launch parameter read with `CommandlineGetParam` (`P:\scripts\3_game\global\game.c:661`), never with `DEVELOPER`.

Before you design around a vanilla API behind an `#ifdef`, grep which define guards it. If it is `DEVELOPER`, read the `defines:` line of a recent `script_*.log` from that build; when it is not there, find a path that does not need it. Wrapping your own call in `#ifdef DEVELOPER` does not help when the design depends on the call. The same rule from the planning side is in `skills/dayz-scope-mod/references/implementation-protocol.md`, "Write or edit it".

## Compile errors are the first gate

No offline check sees method visibility such as `protected`; the real Enforce compile happens when the stack starts. Search the server script log for `Compile error` and `Can't compile` before waiting for later phases, and treat a client message box as a hang that the phase timeout catches. Search the client's script log too (`test-cell-evidence.md`, "What makes a run valid").

A wrapper that worked splits the cell into named phases (boot and spawn, boot log, compile, connect, get in, probes, settle, teardown, parse), each with a PASS or FAIL verdict and its own timeout. It copies the logs to the evidence folder even when a phase fails, and its teardown kills only the processes the cell started.

## A retail server as a parity check

The DayZDiag requirement in `windows-launch-cycle.md` covers iteration with `-filePatching` and `/dayz-launch-test`. A headless retail `DayZServer_x64.exe` also loads PBOs with `-mod`, compiles Enforce Script and makes outbound `RestApi` calls without taking the client's Steam session; a measured run logged the defines `RELEASE, SERVER, NO_GUI, SERVER_FOR_WINDOWS` and real HTTP polling.

Use it as the second side of a diag against retail check when server behaviour may depend on `RELEASE` or on developer only APIs. It does not replace the client for captures or for anything that needs a connected player. It stays outside the managed lifecycle: only a runner that holds its exact process id starts and stops it.

## A one-off diagnostic spawn

When admin UI blocks a diagnosis, a private mission can create a fixture once per boot from `CustomMission.InvokeOnConnect` (`P:\scripts\5_mission\mission\missionserver.c:435`), at a fixed distance from the player, with `CreateObjectEx(..., ECE_PLACE_ON_SURFACE)`. Use a one-shot boolean and clean storage. It is a throwaway, not cell code: anything that must outlive the investigation lives in the mod behind `DIAG` and a parameter, as above.

## Whoever opens a process closes it

Managed runs close by their `run_id`. For a manual process outside dayz-mcp that the user allowed, the agent that opened it keeps its process id and `CommandLine`, asks it to close with `CloseMainWindow()`, waits 8 to 10 seconds, and uses `Stop-Process -Id <pid>` only as the fallback. Never pick a process by executable name or touch another session's peer.

If the user opened the window and is playing, closing it stays their job, through the game's UI. If the agent opened it, the agent closes it; asking to continue the cycle lets the agent close only its own processes.
