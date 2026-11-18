# Server load and dummy bots

How to load a DayZ 1.30 server with moving dummy players and no clients, and how to measure that load without fooling yourself. The DayZDiag executable of the public 1.30 Experimental build compiles in the bot code that makes this possible.

Measured on the 1.30 Experimental DayZDiag, a local server outside dayz-mcp's managed lifecycle, and not checked on `P:\` beyond the cited script lines. The figures come from two runs with one sample per cell; neither is a capacity figure.

## What the 1.30 DayZDiag compiles in

The public 1.30 Experimental DayZDiag compiles every script module with `ROBOCLIENT` and `INPUT_OVERRIDE` defined, as client and as `-server` (script log: `Module: ...; defines: "...,ROBOCLIENT,INPUT_OVERRIDE,..."`). `-headlessMode=1` adds `NO_GUI,NO_GUI_INGAME`. The 1.29 executables hold no `ROBOCLIENT` or `RoboclientUtils` strings.

What that switches on, read in the scripts:

- Every `PlayerBase` builds a `Bot` in `Init()` under `#ifdef ROBOCLIENT` (`P:\scripts\4_world\entities\manbase\playerbase.c:607` to `:613`), and so does a Script Console spawn through `OnSpawnedFromConsole` (`playerbase.c:5281` to `:5296`, called from `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:350` to `:362`).
- Without `-roboclient` the bot idles in a debug state machine whose states start on `EActions.PLAYER_BOT_*` (`AddTransition` and `InitFSM`, `P:\scripts\4_world\systems\bot\bot.c:331` to `:381`; the enum range at `P:\scripts\3_game\enums\eactions.c:92` to `:107`): stance and movement randomizers, user action spam, an attach and drop cycle, moving an item back and forth, spawning, opening, eating and destroying a can, and hand swaps. The diag debug action menu lists them (`playerbase.c:8427` to `:8456`) and `OnAction` passes them to `m_Bot.StartAction` (`playerbase.c:8356` to `:8363`).
- With `-roboclient` the state machine comes from config through `RoboclientUtils.ReadStateMachines` (`bot.c:80` to `:84`). Vanilla ships none that we found, so a rendered `-roboclient` connects and stands still.
- The headless roboclient cannot be used on 1.30 Experimental: `-headlessMode=1 -roboclient` crashes with `Access violation. Illegal read ... at 0x0` at the same instruction, alone and with `-connect`, 3 of 3 times, after compiling `Game` and before `World`.

## Moving dummies with no client

A dummy spawned on the server moves with no client connected. The recipe used (`CreateObjectEx`, `P:\scripts\3_game\global\game.c:703`; `OnSpawnedFromConsole`, `playerbase.c:5281`; `StartAction`, `bot.c:205` to `:215`):

```c
// server mission script; m_Bot exists only under #ifdef ROBOCLIENT
PlayerBase d = PlayerBase.Cast(GetGame().CreateObjectEx("SurvivorM_Mirek", pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS));
d.OnSpawnedFromConsole();                                    // scheduler and Bot, as the console does
d.m_Bot.StartAction(EActions.PLAYER_BOT_RANDOMIZE_MOVEMENT); // start
d.m_Bot.StartAction(EActions.PLAYER_BOT_STOP_CURRENT);       // back to idle
```

The "randomizer" is not random: it forces `OverrideMovementSpeed(ONE_FRAME, 3.0)` and `OverrideMovementAngle(ONE_FRAME, 0.0)` every frame (`P:\scripts\4_world\systems\bot\bot_movementrandomizer.c:26` to `:40`), so every dummy sprints in a straight line north: about 33.7 m per 5 seconds (about 6.75 m/s), and about 1.7 m/s once in water. Spawn inland; from the coast they run into the sea. Mean distance covered was 169.2, 169.1, 168.1 and 158.9 m in 25 seconds for 10, 25, 50 and 100 dummies in one run, and 297.1 and 291.0 m in 45 seconds for 50 and 100 in the other.

Dummies and roboclients alike run under server authority, so this loads the server; it does not offload simulation. dayz-mcp has no verb for it yet; a server verb pair to spawn N dummies and start or stop their action would give N moving players on one machine for load and soak tests.

## Measuring the load

- **Cap the server.** Uncapped, the diag server ran at about 1958 fps and fps meant nothing (10 moving dummies: 1900; 25 idle: 1908). `-limitFPS=60` (the 1.30 executable has a `limitfps` switch) turns dropped frames into the saturation point and makes process CPU per window comparable across steps.
- **Count frames inside the server.** Count `timeslice` in an `override void OnUpdate(float timeslice)` of the server mission (`P:\scripts\5_mission\mission\missionserver.c:108`) and log per window: frames, seconds, fps, longest frame. Sample the process `TotalProcessorTime` every second from outside and join on the timestamp.
- **Take a baseline at both ends.** A fixed warm-up is not enough: the first three windows of a fresh storage ran at 36 to 84 percent machine CPU, and after a 120 second warm-up the first baseline still used 0.276 server cores against 0.001 at the final one. Treat a large mismatch between the two baselines as an inconclusive comparison.
- **Watch the idle window right after a spawn.** After 15 second settles, the idle window right after spawning 25 dummies used 0.201 server cores against 0.010 in the moving window after it, with the machine nearly idle (3.8 percent CPU). At 50 dummies the gap was 0.179 against 0.032 cores, but machine CPU was 49.2 percent during that idle window. The cause was not isolated. With 45 second settles the idle windows after 50 and 100 averaged 60.0 fps; that does not make 45 seconds a proven settle time for CPU.
- **Keep the CPU sampler cheap, and check it for gaps.** A 1 second sampler that also ran a WMI machine CPU query and a script log scan every 5 seconds went 58.7 seconds without a sample across a spawn, leaving two 45 second windows with only 32 and 43 seconds sampled. An analyzer that takes the nearest samples around a window then mixes stages. Use the samples inside the window, report how much of it they cover, and drop a window with short coverage. The in-server fps counter was not affected.
- **Write CSV numbers with the invariant culture.** On a host with a Spanish culture, `'{0:F3}' -f` writes decimal commas and quietly splits every CSV row into extra columns. Use `[string]::Format([Globalization.CultureInfo]::InvariantCulture, ...)`.

## The two runs

One server at `-limitFPS=60`, no client. The first run added dummies in steps of 10, 25, 50 and 100 with 15 second settles and never moved them back. The second spawned 50 and then 100 on a 10 wide grid (6 m by 8 m), settled 45 seconds, and put every dummy back on the grid before each moving window.

| Moving dummies | Run 1 fps | Run 1 server CPU (cores) | Run 1 machine CPU | Run 2 fps | Run 2 server CPU (cores) | Run 2 machine CPU |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (final baseline) | 60.0 | 0.007 | 0.6 % | 60.0 | 0.001 | 0.4 % |
| 25 | 60.0 | 0.010 | 0.4 % | not run | not run | not run |
| 50 | 60.0 | 0.032 | 2.0 % | 60.0 | 0.024 (32 of 45 s sampled) | 3.2 % |
| 100 | 54.7 | 0.384 | 34.2 % | 60.0 | 0.008 | 2.0 % |

Fps is the mean over each window (run 1: 25 seconds for moving windows and 30 for the final baseline; run 2: 45 seconds). Machine CPU is the whole host. In run 2 the 100 dummy window averaged 60.0 fps (33 ms longest frame) at 0.008 server cores. Run 1's averaged 54.7 fps while the host ran at 34.2 percent CPU, of which the server's 0.384 cores are about 2.4 percent. The runs differ in settles, placement, window length and host load, and none of these was isolated.
