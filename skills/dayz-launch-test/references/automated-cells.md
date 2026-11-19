# Scripted test cells

How to set up a scripted test, a "cell", that boots the game, drives it without a person and reads its verdict from the logs: where the test code lives, what a test mission may do, which diag defines exist, and who closes the processes. Seating a player in a vehicle by script is in `test-cell-vehicles.md`; gates, teardown and what makes a run count as evidence are in `test-cell-evidence.md`. The ready-made self-reporting test mod is `../assets/autotest-mod/` (`linux-headless-client.md`).

Vanilla script facts cite the file on `P:\`. The rest was measured in game on a Windows test machine with Community Framework and test vehicle mods, and is not checked on `P:\`.

## Setting up a headless cell

Build with `/dayz-build-pbo`, then add these:

1. Launch with `/dayz-launch-test` or a `.bat` the user starts (`test-machine-sharing.md`), keep the process ids, and poll the RPT read only. Never start DayZDiag with `Start-Process` from a background task, which kills it when the task ends.
2. Skip `CreateHive()` in a test mission `init.c` for a physics test. The Central Economy loads about 20,000 loot items and delays the mission loop by minutes.
3. Connect a client before you spawn a vehicle. A `CarScript` vehicle only ticks `OnUpdate` and simulates with a player present, so give the cell a mode that connects a second diag instance to `127.0.0.1`.
4. Put cell code inside the mod, not in the mission. Spawn on connect, an engine watcher and test hooks belong in the mod under `#ifdef DIAG` plus a launch parameter of the mod's own, for example a `modded class MissionServer` in `5_Mission` switched on by `-<mod>AutoGetIn=1` and read in its `PlayerBase`. The mission lives in the Steam folder (`DayZServer\mpmissions\<mission>\init.c`), which no backup or repo carries. Inside the mod it travels with the PBO, is versioned, and stays inert in retail because the flag is absent.
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

The standard `DayZDiag_x64.exe` defines `DIAG` and `DIAG_DEVELOPER` but not `DEVELOPER`: the `defines:` line of both peers' `script_*.log` lists `DIAG,DIAG_DEVELOPER,...,FEATURE_NETWORK_RECONCILIATION` and no `DEVELOPER`. Every vanilla `#ifdef DEVELOPER` block is therefore absent from the build, for example `SetGetInVehicleDebug` and `TryGetInVehicleDebug` (`P:\scripts\4_world\entities\manbase\playerbase.c:3531` to `:3549`), `DayZPlayerSyncJunctures.SendGetInVehicle` and `SJ_DEBUG_GET_IN_VEHICLE` (`P:\scripts\4_world\entities\dayzplayersyncjunctures.c:33` to `:35` and `:40` to `:49`), the juncture case that reads it (`playerbase.c:8553` to `:8559`) and much of `plugindeveloper.c`.

- `OnDebugSpawn` working proves nothing about `DEVELOPER`: it has no define guard (`P:\scripts\3_game\entities\entityai.c:3955`), so it runs in every build.
- A mod whose PBO calls a symbol vanilla defines only under `#ifdef DEVELOPER`, such as `SendGetInVehicle`, does not compile, and every script of the mod drops. That is not a silent no-op, unlike `ExecuteEnforceScript` (`proto native`, `P:\scripts\3_game\global\game.c:777`), which compiles in every build and returned false at run time outside a developer build (measured; the native side is not checked on `P:\`).
- Gate test code with `#ifdef DIAG` or a launch parameter read with `CommandlineGetParam` (`game.c:661`), never with `DEVELOPER`.

Before you design around a vanilla API behind an `#ifdef`, grep which define guards it. If it is `DEVELOPER`, read the `defines:` line of a recent `script_*.log` from that build; when it is not there, find a path that does not need it. Wrapping your own call in `#ifdef DEVELOPER` does not help when the design depends on the call. The same rule from the planning side is in `skills/dayz-scope-mod/references/implementation-protocol.md`, "Write or edit it".

## Compile errors are the first gate

No offline check sees method visibility such as `protected`; the real Enforce compile happens when the stack starts. Search the server script log for `Compile error` and `Can't compile` before waiting for later phases, and treat a client message box as a hang that the phase timeout catches. Search the client's script log too (`test-cell-evidence.md`, "What makes a run valid").

A wrapper that worked splits the cell into named phases (boot and spawn, boot log, compile, connect, get in, probes, settle, teardown, parse), each with a PASS or FAIL verdict and its own timeout. It copies the logs to the evidence folder even when a phase fails, and its teardown kills only the processes the cell started.

## Vanilla's own test harness

The game ships a small test framework that a client started with `-autotest=<config.json> -mission=<mission>` runs by itself. Read from the vanilla scripts; it was not run in game, and whether a retail or diag client honours `-autotest` is not checked on `P:\` (the harness itself is `proto native`).

- **Start.** The client picks its start from the command line in this order: `-join`, `-connect`, `-autotest`, `-mission`, `-party`, else the main menu (`P:\scripts\3_game\dayzgame.c:2124` to `:2150`). So `-connect` wins over `-autotest`, and `-autotest` without `-mission` logs `[Autotest] Parameter 'mission' is not set on CLI.` to the RPT and quits (`dayzgame.c:2364` to `:2380`).
- **Config.** The `-autotest` value is a path to a JSON file `{"TestSuites": ["MyMod_Suite"]}` (`P:\scripts\3_game\autotest\autotestconfigjson.c:1` to `:3`), loaded with `JsonFileLoader` (`autotestconfighandler.c:5` to `:14`). A file that does not load is logged and the mission still starts, with no tests.
- **Tests.** A suite is a class extending `TestSuite`; a test is a class extending `TestBase` with the attribute `[Test("MyMod_Suite", timeoutS, timeoutMs, sortOrder)]`, and its methods carry `[Step(EStage.Setup)]`, `[Step(EStage.Main)]` or `[Step(EStage.TearDown)]` (`P:\scripts\2_gamelib\tests\testingframework.c:96` to `:130`, `:160` and `:181`). A step reports with `SetResult(new CustomResult(bool, text))` (`P:\scripts\3_game\autotest\autotestrunner.c:80` to `:104`). Only suites named in the config and enabled run (`autotestrunner.c:45`). Vanilla warns that an empty suite gives no error and is skipped (`:111`).
- **Run and verdict.** `MissionGameplay.OnUpdate` drives the runner every frame (`P:\scripts\5_mission\mission\missiongameplay.c:232` to `:244`, called at `:315`), so it runs in the client's mission, in practice an offline mission. When the harness finishes it writes a JUnit style report to `$mission:Autotest_<UTC time>.xml` (`P:\scripts\3_game\autotest\autotestfixture.c:3` and `:8` to `:28`) and the client exits with code 0 (`missiongameplay.c:243`), whether the tests passed or not: read the XML, never the exit code.

Use it for logic a single process can check (config values, a pure script function, an item spawned at the player with `AutoTestFixture.SpawnEntityAI`, `autotestfixture.c:30`). Anything that needs a dedicated server and a client still needs the cell above.

## A retail server as a parity check

The DayZDiag requirement in `windows-launch-cycle.md` covers iteration with `-filePatching` and `/dayz-launch-test`. A headless retail `DayZServer_x64.exe` also loads PBOs with `-mod`, compiles Enforce Script and makes outbound `RestApi` calls without taking the client's Steam session; a measured run logged the defines `RELEASE, SERVER, NO_GUI, SERVER_FOR_WINDOWS` and real HTTP polling.

Use it as the second side of a diag against retail check when server behaviour may depend on `RELEASE` or on developer only APIs. It does not replace the client for captures or for anything that needs a connected player. Only a runner that holds its exact process id starts and stops it.

## A one-off diagnostic spawn

When admin UI blocks a diagnosis, a private mission can create a fixture once per boot by overriding `InvokeOnConnect` in its `CustomMission` (the `MissionServer` hook it inherits, `P:\scripts\5_mission\mission\missionserver.c:435`), at a fixed distance from the player, with `CreateObjectEx(..., ECE_PLACE_ON_SURFACE)` (`P:\scripts\3_game\global\game.c:703`; the flag at `P:\scripts\3_game\ce\centraleconomy.c:38`). Use a one-shot boolean and clean storage. It is a throwaway, not cell code: anything that must outlive the investigation lives in the mod behind `DIAG` and a parameter, as above.

`MissionServer.OnEvent` calls `InvokeOnConnect` from two paths, so a hook there fires on every connect, whichever path the player takes:

| Event | Called first | Then | Source |
|---|---|---|---|
| `ClientNewEventTypeID` (no stored character) | `OnClientNewEvent`, which creates the player (`:549`) | `InvokeOnConnect` | `missionserver.c:326` to `:336` |
| `ClientReadyEventTypeID` (a character loaded from storage) | `OnClientReadyEvent` | `InvokeOnConnect` | `missionserver.c:345` to `:357` |

A respawn and a reconnect call `OnClientRespawnEvent` and `OnClientReconnectEvent` and not `InvokeOnConnect` (`:366` to `:394`). Which path a join takes depends on whether storage holds the character (the decision is native), so a cell that spawns on connect has to work from both, and the one-shot boolean is what stops a second join from spawning a second fixture.

## Whoever opens a process closes it

The agent that opened a process keeps its process id and `CommandLine`, asks it to close with `CloseMainWindow()`, waits 8 to 10 seconds, and uses `Stop-Process -Id <pid>` only as the fallback. Never pick a process by executable name or touch another session's peer.

If the user opened the window and is playing, closing it stays their job, through the game's UI. If the agent opened it, the agent closes it; asking to continue the cycle lets the agent close only its own processes.
