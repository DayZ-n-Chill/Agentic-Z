# Automated in-game test cells: harness patterns and measured walls

How to build a scripted test (a "cell") that boots the game, drives it without a human and reads a verdict from the logs: the headless pattern, what a mission `init.c` may and may not do, getting a player into a vehicle by script, gates that can actually fail, teardown order, and what makes a run valid evidence. The ready-made self-reporting test mod is in `assets/autotest-mod/` (see `linux-headless-client.md`).

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it.

Vanilla script facts cite the file on `P:\`. Measured results and third-party behaviour (dayz-mcp, Community Framework, the helicopter and quad-bike mods the cells were built for) are not yet checked on `P:\`.

## Headless autotest pattern (no client, scripted spawn)

For automated physics/spawn testing without a human client, write a dedicated harness script
that reuses the launcher's build and deploy step. Five gotchas that
cost many iterations, recorded so the next headless harness works first try:
1. **Historical detached pattern - superseded 2026-07-15.** A direct `Start-Process` avoided
   waiting on the DayZDiag grandchild but left it outside the registered lifecycle. Launch now
   with `dayz_test_run`, which owns the lease (do not acquire a separate lease first; see
   `managed-launcher.md`); keep its `run_id` and poll the RPT read-only. Do not recreate the old
   direct invocation, and never invoke the approved launcher directly.
2. **A test mission `init.c` should skip `CreateHive()`** (CE economy) for a physics test - it
   loads ~20k loot items and delays the mission loop by minutes.
3. **A `CarScript` vehicle only ticks `OnUpdate` / simulates with a player present.** A headless
   server with zero clients won't drive the vehicle's own script; spawn after a client connects
   (give the harness a mode that connects a second diag instance to 127.0.0.1).
4. **Cell infrastructure (spawn-on-connect, engine watcher, auto-test hooks) belongs inside the
   mod under `#ifdef DIAG` + a CLI param - never only in the mission `init.c`**.
   The mission lives under Steam (`DayZServer\mpmissions\<mission>\init.c`), which no
   backup or repo carries: a helicopter cell's infrastructure written into `init.c` on
   2026-08-12 (`CreateObjectEx` on `InvokeOnConnect` + `EngineStart()` pre-crew watcher) was
   gone on a second machine five days later and had to be written again. In-tree
   it travels with the PBO, is versioned, and stays inert in retail by absence of the flag
   (pattern: a `modded class MissionServer` in the mod's `5_Mission`, switched on by a
   launch parameter of the mod's own, such as `-<mod>AutoGetIn=1`, read in its `PlayerBase`). Corollary measured the same day: start the
   engine before the crew sits, because a sleeping body in the mod's `PARKED` state rejects the injected get-in action.
5. **PowerShell orchestrator traps that hang a cell silently** (measured 2026-08-17): (a) never name a function parameter `$Args` - it is the automatic
   variable, `@Args` splats nothing and `& python` with no argv opens the interactive REPL that
   never returns (the cell sat at "flip DebugLog" for minutes with a `python.exe` child and no
   arguments); (b) `& native 2>&1` under `$ErrorActionPreference='Stop'` turns any stderr line into
   a terminating error (PS 5.1) - wrap native calls in a helper that switches to `Continue` and
   returns text + `$LASTEXITCODE`; (c) the DayZ client needs a usable Steam
   (`HKCU\Software\Valve\Steam\ActiveProcess` pid and ActiveUser ≠ 0): a Steam restarted minutes
   earlier sits at pid populated / ActiveUser=0 and the client dies at bootstrap with a ~1 KB RPT
   and an `ErrorMessage_*.mdmp` while the server (no Steam) boots fine - `steam.exe -shutdown` +
   relaunch repopulated the key in ~20 s. Check the key in the pre-flight of every cell.

## Mission `init.c`: do not mod classes from earlier script modules

[IN-GAME CONFIRMED, DayZ 1.29 server diag, 2026-07-30] A generated mission
that added a `modded class` for a `4_World` type failed with `Unknown type`,
both for a concrete class (`SmallStone`) and for a base class
(`BuildingBase`). An earlier incident showed the same with a mod's own
`4_World` class. Offline text checks did not catch it.

Rules for a mission that checks a result:

- Call a class that is already compiled and already has the method you are
  testing. If you need a new method, add it to the mod, in the same script
  module and PBO as the class, as a separate change. Do not add it with a
  `modded class` in `init.c`.
- Write each test call and each boolean expression on one line. Starting a
  line with `&&` produced `Incompatible parameter` and `Syntax error`.
- Before spending runs, do one control run that only checks that the Game,
  World and Mission modules loaded, that `OnInit` ran, and that your result
  marker was printed.

Measured on 2026-07-30 in three failed runs of a server-side check (unknown type, `modded class`
across modules, boolean line break); the control run that called the existing class passed.

## Wheel simulation diagnosis (vehicle won't drive, bounces or sinks)

When a modded `CarScript` vehicle spawns but won't drive - wheels mount yet don't
spin, chassis bounces or sinks, engine revs with no speed - the failure is almost
always one of two measurable things, not mass/inertia. Instrument and read them
side-by-side against a known-good reference vehicle (e.g. the vanilla sedan or a
modded quad bike known to drive) in the same run before touching geometry.

### 1. Is the wheel seated in PhysX, and does it touch ground?

- `WheelCountPresent()` - how many wheels the simulation actually seated (the gate).
  `0` while `WheelCount()` returns N means the slot/FireGeometry wiring is wrong; see
  the `skills/_shared/enscript/depth/` wheel-attachment rule.
- `WheelHasContact(i)` per wheel - `1` = touching ground, `0` = airborne. Print the
  four as a bitstring (`wc=1111` good; `wc=0000` = the whole vehicle is suspended off
  the ground, a placement/clearance problem, not a sim problem). Vanilla refs:
  `P:\scripts\3_game\vehicles\car.c:286` (`WheelHasContact`), `car.c:345` (`WheelCount`), `car.c:348` (`WheelCountPresent`).

So: `WheelCountPresent()=0` is the silent wheel-binding blocker (FireGeometry slot
selection); `WheelCountPresent()=4` with `wc=0000` is geometry sitting too high or
buried, which step 2 isolates.

### 2. Did placement bury or launch the vehicle? (controlled-height probe)

Spawn with an explicit height flag instead of letting CE drop it:
- `ECE_KEEPHEIGHT` (`=524288`, "no surface trace") - places at the exact Y you pass,
  no terrain snap. Spawn a known clear height and watch whether it settles.
- `ECE_PLACE_ON_SURFACE` (`=1060`) - normal surface-trace placement.
Vanilla refs: `P:\scripts\3_game\ce\centraleconomy.c:38` (`ECE_PLACE_ON_SURFACE`) and `centraleconomy.c:28` (`ECE_KEEPHEIGHT`). If the vehicle is stable under KEEPHEIGHT but
bounces/sinks under PLACE_ON_SURFACE, the bug is placement burying the hull (wheel-well
clearance vs tire radius), not the model.

### 3. Gotcha: parser/instrumentation drift before declaring the test failed

When the harness reports "ERROR / no data", first confirm the parser regex still
matches the current log-line format of the instrumentation. A log-format change
(renamed tag, reordered fields) reads as a test failure when the test actually ran
fine. Check the regex against a raw sample line before concluding the build is broken.

(measured in a quad-bike wheel-well and placement session, 2026-06-01)

## DEVELOPER vs DIAG_DEVELOPER - the standard diag only defines DIAG_DEVELOPER

The standard `DayZDiag_x64` defines `DIAG_DEVELOPER` but not `DEVELOPER` (bare). Verified in the `script_*.log` of both peers: the server and client defines include `DIAG,DIAG_DEVELOPER,...,FEATURE_NETWORK_RECONCILIATION` and no `DEVELOPER`. So every vanilla `#ifdef DEVELOPER` block (for example the debug get-in: `DayZPlayerSyncJunctures.SendGetInVehicle`, `SJ_DEBUG_GET_IN_VEHICLE`, `PlayerBase.TryGetInVehicleDebug`, much of `plugindeveloper.c`) does not exist in this build. `OnDebugSpawn` working proves nothing about `DEVELOPER`: it has no define guard at all (`P:\scripts\3_game\entities\entityai.c:3955`), so it runs in every build. Vanilla: `P:\scripts\4_world\entities\manbase\playerbase.c:3531` opens the `#ifdef DEVELOPER` block that holds `SetGetInVehicleDebug` and `TryGetInVehicleDebug`.

Expensive trap: if a mod's PBO calls a symbol that vanilla defines only under `#ifdef DEVELOPER` (a call to `SendGetInVehicle`, for example), that symbol does not exist in this build, so the whole PBO fails to compile and every tool and script of the mod drops. It is not a silent no-op, unlike `ExecuteEnforceScript`, which is Developer-only and returns false at runtime.

Rule before basing a design on a vanilla `#ifdef DEVELOPER` API: (1) grep the `#ifdef` guarding it (`DEVELOPER` or `DIAG_DEVELOPER`?); (2) if it is `DEVELOPER`, read the `defines:` line of a recent `script_*.log` for that build to confirm it is active; (3) if it is not active, do not call the symbol. Wrapping the call in `#ifdef DEVELOPER` does not help when the design depends on it; find a path that does not need `DEVELOPER`. Cross-ref `dayz-mod-workflow` (anti-confabulation). Measured 2026-06-28 in the compile logs of both profiles.

## Automated in-game cell without a human pilot: the four measured walls and workarounds

Eleven iteration cells in one day to get an automated cell green (stack + get-in +
engine + probes + parser, ~5 min). The four walls, measured with discriminants, so as not to pay
them again:

1. **DayZDiag does not define `DEVELOPER` for scripts (it does define `DIAG` and `DIAG_DEVELOPER`)** - measured with
   defines telemetry on a connected client. Any vanilla mechanism under `#ifdef DEVELOPER`
   (for example `SetGetInVehicleDebug`/`TryGetInVehicleDebug`, `P:\scripts\4_world\entities\manbase\playerbase.c:3524-3549`) does not exist in
   the diag build. Gate test code with a command line parameter
   (`CommandlineGetParam`, `P:\scripts\3_game\global\game.c:661`) or with `#ifdef DIAG`, never with `DEVELOPER`.
2. **Automated get-in in multiplayer: calling `StartCommand_Vehicle` directly from the client seats a
   local ghost** (own=true, HUD active), but the server never registers the crew (crew0=false,
   consumed=0, ObtainState silent). The route that works is to inject the real action:
   `ActionManagerClient.PerformActionStart(GetAction(ActionGetInTransport), target, null)`
   (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804`; in multiplayer it enters through ActionStart, a synchronized flow that the
   server mirrors). Get the target componentIndex by iterating `CrewPositionIndex(c)` until it returns the desired seat
   (`CrewPositionIndex`, `P:\scripts\3_game\vehicles\transport.c:179`).
   Observe success with `GetCommand_Vehicle()`
   on the next tick (with retry); do not mark the step done when the action is injected. Note: `ActionCondition` is
   protected, so it cannot be pre-validated from outside; the action manager validates on both sides.

   **How this fits with seating a player by script from the server** (measured against the vanilla tree, 2026-08-18):
   crew membership and the vehicle command are two distinct things, and only the real action
   produces both. Crew is native engine state, not a script netsync:
   `Transport` registers a single variable (`m_EngineZoneReceivedHit`, `transport.c:110`) and
   `CrewMember`/`CrewDriver` are `proto native` (`transport.c:179-191`), readable from any
   client - that is why a client wanting to get in can reject an already occupied seat
   (the `CrewMember` check at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:50-52`).
   `HumanCommandVehicle`, on the other hand, is created by
   `StartCommand_Vehicle` on the machine that calls it, and across the vanilla scripts on `P:\scripts` (3,044 `.c` files in 1.30) there are
   exactly three call-sites: action itself (`actiongetintransport.c:104`), resumption
   after unconsciousness via `m_TransportCache` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2395`) and a debug under
   `#ifdef DEVELOPER` (`playerbase.c:3541`). **None of them starts the command on learning over the network
   that the player is already seated.** Both sides of the same fact follow from that: calling
   `StartCommand_Vehicle` directly from the client gives the command without server crew (the ghost
   above); seating someone by script from the server gives crew without the local command, and then
   any `ActionCondition` that requires being seated is never satisfied, because those conditions check
   `GetCommand_Vehicle()` and not `CrewMember`, as get-out does
   (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:70-76`) and start/stop engine (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:26-37`). Beware of
   `IsInVehicle()`: it accepts both routes (the command or a parent Transport,
   `dayzplayerimplement.c:468-471`), so it cannot tell them apart.
3. **A sleeping body rejects the injected get-in action** (the mod's `PARKED` sleep gate). If the mod
   puts the vehicle to sleep at rest, the cell must wake it before get-in. The simplest way is to
   start the engine server-side from the test mission (`EngineStart`, `P:\scripts\3_game\vehicles\car.c:233`) as soon as
   the vehicle spawns, not when crew is detected. Also, without the engine or simulation running, the OwnerState channel does not flow
   (ObtainState/RewindState stay silent) even if the player is seated.
4. **The real Enforce compile gate is the startup of the stack** (no offline check sees
   method visibility, such as protected). The cell must search the server script log for `Compile error` / `Can't
   compile` before waiting for later phases, and treat a client
   message box as a hang (phase timeout).

Orchestrator pattern that worked: a wrapper with named phases (BOOT-spawn / BOOT-log /
COMPILE / CONNECT / GETIN / probes / SETTLE / teardown / PARSE), each with a PASS/FAIL
verdict and its own timeout; the logs are copied to the evidence folder even if a phase fails; teardown
kills only the PIDs the cell launched. Measured over the 11 cells of a helicopter session on 2026-08-12,
each with the cause of its failure recorded.

## Preflight: prove your cell's gates can go red before you trust a single green run

A test-cell wrapper is only worth what its gates are worth, and two failure modes make a gate
**structurally incapable of failing** while it keeps printing green. Neither is visible by reading
the script in good faith. Both were live in a wrapper that had already gated ~12 in-game cells.

**1. A flag that turns your regex into a literal.** This line looks like a compile gate:

```powershell
Select-String -Path $slog.FullName -Pattern "Compile error|Can't compile" -SimpleMatch
```

`-SimpleMatch` makes PowerShell search for the whole string **verbatim, pipe included** - a
sequence that never occurs in a log. Measured against a synthetic log containing both real errors:
**0 hits with `-SimpleMatch`, 2 without it.** Every cell that "passed the compile gate" passed it
by construction. Same trap: `-Raw`, `-Literal*`, `[Regex]::Escape` on a pattern you meant as regex,
and `-match` vs `-like` mixups.

**1-bis. The symmetric one: a pattern that cannot come out green - `not closed` is a false red.**
(measured 2026-09-07). If you add `not closed` to the gate thinking of Enforce's
`CParser: quoted string not closed`, you will find it in **healthy** boots:
CommunityFramework writes
`File "$mission:storage_1/communityframework/modstorageplayers.bin" was not closed. Always shut
down the server gracefully to prevent data loss.` every time the previous server did not shut down
gracefully, which is every time it was stopped by the tool. Measured on the same box: 1 occurrence in a
green boot and 0 in the next, with `CParser` at 0 in both, so the difference was the shutdown
mode, not the code. **Anchor pattern to `CParser`, not the loose phrase**, and if you really
want the phrase, also require `CParser` on the same line. A gate shouting red on
good boots deactivates itself: by the third time, someone ignores it.

**2. An analyzer whose input does not depend on the experiment.** Hardcoded log paths
(`$clientPath = ...client_script_2026-08-12_11-25-05.log`) mean every future A/B re-analyses the
same old flight and reports "no change" tautologically. Its sibling: a script that only prints
statistics and never sets an exit code - without one, nothing can fail, so it is a report, not a gate.

**Preflight before trusting any inherited gate** (cheap, and it is the only thing that separates a
gate from decoration):

1. Feed it a fixture that must fail, and confirm it fails. If you have never seen the gate red, you
   do not know it is a gate.
2. Grep the wrapper for `-SimpleMatch`/`-Raw`/`-Literal*` next to any pattern containing `|`, `.`,
   `*`, `\` or `(`.
3. Require parametrised inputs, and assert the analysed artifact is **newer than** the run that
   produced it (a stale-input check is one line and catches the whole class).
4. Require a non-zero exit code on failure, and check the caller actually propagates it.

Corollary for measurement campaigns: fix the gates before the campaign, not after. A campaign run
through a decorative gate produces greens that mean nothing, and you cannot tell afterwards which
of them were real.

## Teardown copies the logs before killing the client, and verifies the copy

Killing the DayZ client immediately loses its last unflushed log buffer. A pilot
run's flight output was lost this way: the **client** log cut at `t=2118` while
the **server** recorded the dismount roughly 56 s later, so the interesting
window existed only in the buffer that the kill discarded.

The order is not "stop, then collect". It is:

1. **Copy** the script logs while the process is still alive;
2. **Verify the copy contains the stretch that matters** -- count the lines of the
   probe you expected to see, do not just check the file is non-empty;
3. **Only then** `Stop-Process`.

A teardown that kills first cannot be repaired afterwards: there is no second
copy of an unflushed buffer. This costs one line-count assertion and buys the
whole run.

## Validity of an automated run: preflight, cycle, and evidence

A cell only emits `PASS` if it demonstrates that it booted in the planned mode, covered the complete transition, and produced the evidence consumed by the verdict. Apply this contract before spending a batch:

1. **Preflight by mechanism and mode.** Document each guard as `protected mechanism → affected modes` and code the branch: a client-exclusive guard aborts with client and only warns in `-NoClient`, without manual bypass. On a box with multiple stacks, an unattended cell with client is not isolated from keyboard either: list the other `DayZDiag` processes and their active mods, record their PIDs, mods and the focus risk, and use a test-only DIAG guard that rejects human actions that would change state while the script is active. The automation keeps a separate programmatic path. If you cannot show isolation, the result is `SETUP_FAIL`.

2. **Boot identity and separation.** In a batch that relaunches the client, leave a conservative cooldown of 60 s between one shutdown and the next startup; a native crash during that startup is `SETUP_FAIL`, not a mod regression. The cooldown does not apply to a truly isolated one-shot run, because it does not chain another client. When packing evidence, do not pick a file by its apparent mtime: the product's artifacts are named in UTC, while RPT names and mtimes use local time. Cross-check the boot id or an internal marker against the timestamp recorded in the incident ledger; that timestamp wins over the mtime. If the expected boot markers are missing, reject the bundle.

3. **Whole path, and a compile check on both sides.** Write each important transition as four steps: the input, the state you can observe, the exit, and the state after the exit. Drive all four from the script. A test that only enters has not covered the transition; find what ends it among the existing watchers, cancellations and timeouts. Extend the server compile check (wall 4 of the automated-cell section above) to the client: search the script logs of both server and client for `Compile error` / `Can't compile` before waiting for any functional marker. A dead client, a live server and `Can't compile` mean code that only the client compiles has an error; it is not a timeout and not a runtime regression. Offline lint cannot prove `private`/`protected` visibility is right; only a real compile on both sides can.

4. **Shutdown matching the measurement.** Copying and verifying the logs before killing (the teardown section above) keeps the evidence already written, but cannot prove anything about results that are only written on exit. For leak reports, flushes, destructors, or final hooks, request graceful shutdown, wait for an explicit marker that the report or hook ran, and only then collect the result. A forced kill gives `SETUP_FAIL` for every exit metric and also prevents verifying a fix that lives in that hook. "The problem did not appear" never equals `PASS` if the check never ran.

## Diagnostic spawn without depending on VPP UI (single-use scope)

If administrative UI blocks a diagnosis, a private mission can use
`CustomMission.InvokeOnConnect` (`P:\scripts\5_mission\mission\missionserver.c:435`) to create a fixture once per boot, at a fixed distance from the
player, with `CreateObjectEx(..., ECE_PLACE_ON_SURFACE)`. Use a one-shot boolean and clean storage.

It is a disposable fallback, not cell infrastructure. Point 4 of "Headless autotest pattern" still
applies: any spawner, watcher or control that must outlive the project lives inside the mod,
gated by DIAG and by an explicit parameter.

## Parsers: first extract the actual `Print` payload

A string variable arrives in the script log in a form equivalent to:

```text
SCRIPT       : string <var> = '<payload>'
```

The closing single quote is stuck to the last field. First extract what lies between
`= '` and the last quote; only then split out the numbers and fields. A log gate always includes
literal fixtures copied from a real log, in addition to synthetic cases, and counter-fixtures with a truncated
wrapper. A self-test that never consumed a real line only validates the parser you imagined.

## Teleport and readiness before injecting an action

To teleport the player in a harness, use the X and Z of the probed point and
`Y = GetGame().SurfaceY(x, z)` (`P:\scripts\3_game\global\game.c:1176`). The Y of a memory point can leave the player in
`ACID_Human_Fall`; during the fall, an injected action can abort without an error while the server has already
reserved the seat.

Before spending an attempt, require an accepted command ID, no action in progress,
`CanStoreInputUserData()`, and `ActionBase.Can(...)`. Then observe the real transition; do not mark
success when the action is sent. A desync of `server=Move, client=Fall` points first to placement.

## Headless retail server as a parity check

The requirement for `DayZDiag_x64.exe` in the prerequisites (`windows-launch-cycle.md`) applies to iteration with `-filePatching` and to
this skill's official launcher. A headless retail `DayZServer_x64.exe` can load PBOs with
`-mod`, compile Enforce and make outbound `RestApi` calls without taking the client's Steam session.
The measured run logged the defines `RELEASE, SERVER, NO_GUI, SERVER_FOR_WINDOWS` and real HTTP polling.

Use it as the second side of a diag-versus-retail gate when server-side behavior may
depend on `RELEASE` or on developer-only APIs. It does not replace the client for visual capture or for
verbs that need a connected player. This server stays outside the official lifecycle: only
a probe-gated runner that holds its exact PID may start and stop it.

## Multi-peer cells: clock, replay, and bilateral probes

For an exit failure or desync, instrument the callback equivalent to `OnDriverExit` on both
peers and emit in a single window `playerPos`, `vehiclePos`, `crewEntryWS`, and their distances. Align
client/server clocks with pairs of the same event; do not compare raw peer timestamps.

In an owner series with rewind and replay, several samples can share the same `t`. Keep the
first sample per tick, or collapse a documented interval shorter than 20 ms, before evaluating
edges. Convert server events to the owner's clock, use the authoritative series as the
primary oracle and the owner's series as secondary, and re-run the history after changing
the parser.

The bridge does not inject arbitrary values into `UAInput`. If the mod neutralizes `CarController` and
consumes its own axes, a cell needs a DIAG script on the owner before `WriteToMove`; this branch
is promoted for the mod only after an in-game run shows that it steers.

## Contract of a repeatable scripted cell

- Spawn the fixture at a known fixed location and place the player at a fixed offset on
  `SurfaceY`; a random spawn turns obstacles and doors into environmental noise. A default spawn also draws a random character class: pin it (`session-findings.md`, the section on untextured runs and a moving 1PP eye).
- After an exit, rearm the placement server-side after a cooldown, with the player on foot.
  Re-entry is part of the test: a ghost pose on the client invalidates reach and `Can()`.
- `forces-off`, `clamp-abort`, `no-probes`, `no-pilot`, and `not-owner` are `INCONCLUSIVE` and accept
  bounded retries. A timeout after the preconditions were met is `FAIL`.
- The script runs the cell; it does not judge the result. Its gates are the ones written down before the run. It detects "settled" by
  a sustained height above ground (AGL) or, better, by the authoritative state, not by a single owner velocity sample.

## Isolation, settle, and effect probes in cells

While the scripted pilot is active, a DIAG guard in `ActionCondition` must reject
human actions that would break the cell, while keeping a separate programmatic route. Settle is
decided by the mirrored authoritative state (`GROUND_READY`/`PARKED`), with AGL only as a backup;
the owner can keep bouncing after the authority has settled.

Instrument the symptom callback on both peers with a gated probe and a stack trace. On the client, print the
stack line by line to prevent truncation, and do not call APIs that are valid only on the server. At
startup, the runner probes the other running DayZDiag processes for PID, mod line and port; if port 2302 belongs to another
session, it picks a different free port. This extends the preflight of "Validity of an automated run" without touching
other sessions' peers.

## Whoever opens a manual process also closes it

Managed runs are closed by their `run_id`. For an authorized manual process outside MCP,
the agent that opened it keeps its PID and `CommandLine`, requests an orderly shutdown with
`CloseMainWindow()`, waits 8-10 s and uses `Stop-Process -Id <pid>` only as the exact fallback. Never
select a process by executable name or touch a peer from another session.

If the user opened the window and is playing, closing it stays the user's job, through the game's UI. If the agent
opened it, the user is not turned into a cleanup operator; asking to continue the cycle authorizes the agent to
close only its own processes.

## An in-game observation is worth whatever the `-mod=` line of its run is worth

Distinct from the rule in `managed-launcher.md` that a free lease does not imply a free box, which reads `-mod=` to know **whose box it is**. This one
reads it to know **whether the observation counts as evidence**, and is done before using the observation, not at
launch.

Measured on 2026-09-04 on two quad-bike mods at once. Of six runs of the first, **one** carried
`@SurvivorAnims`; of the four runs of the second, **none**. Each mod's `GetAnimInstance` override
returns its own instance (22) only if `CfgPatches SurvivorAnims` exists, and otherwise
falls back to `VehicleAnimInstances.V3S`, which is the truck pose on a quad. With the wrong pose
**driver camera is not where it would really be**, and that moves both what is seen from
seat and which LOD engine chooses. A LOD symptom was diagnosed and "fixed"
on those runs and the fix had to be withdrawn: cause was not verified.

The failure is silent by construction: missing mod gives no error, game starts,
observation seems normal and user reports it in good faith.

**Upon receiving an in-game observation that will decide code or geometry:**

1. Locate the RPTs of that run (server and client) and read its first `-mod=` line.
2. Check that mods on which observed behavior depends are present. The three most silent:
   - an **animations** mod queried by `ConfigIsExisting` from `GetAnimInstance` or
     other hook -> without it, pose and camera are different;
   - a **framework** (CF and company) that writes modstorage per entity;
   - the content mod itself whose objects must be seen.
3. If any is missing, observation is not discarded: **it is reclassified**. Whatever does not depend on
   pose or LOD remains valid (a mirrored texture is so from any angle); whatever
   depends on where the eye is, does not.
4. With every mod present, read two more things from that run: whether it rendered textured and, for
   anything that depends on where the eye is, where the eye was. Both changed between runs with the same
   command line (`session-findings.md`, the section on untextured runs and a moving 1PP eye).

Name trap: a mod folder such as `@Survivor Animations` **with space** splits the command
line (in RPT it is seen cut off at `-mod=...;P:\Mods\@Survivor`). Use a junction
without a space, such as `@SurvivorAnims`.

Cheap audit of a whole workday, to know which runs are valid:

```bash
for f in _server/profiles/*.RPT _client/profiles/*.RPT; do
  m=$(grep -m1 -oE '\-mod=[^ ]*' "$f")
  printf "%-52s %s\n" "$(basename $f)" "$m"
done
```

## An unfocused DayZDiag client runs at ~20 fps: what the client measures depends on who holds the foreground

Measured on a helicopter mod's bench (DayZDiag, windowed client and server on same machine),
**with manipulation**, not by correlation:

- With its window in foreground, client runs at **25.0 ms** per frame (40 fps); without focus, at
  **51-52 ms** (~20 fps). Within the same cell, toggling focus moved median
  26 <-> 53 ms.
- It is not shared GPU or CPU distribution: 0 of 10 slow cells coincided with
  local LLM inference, and pinning client to 2 cores with high priority left 4 of 4 cells at
  51-52 ms. Slow ones form a narrow ceiling (91% of frames within +-3 ms), not a contention
  tail.
- What it entails: heli idle bouncing **followed focus**. With focus held, 6 of 6
  still idles; with focus removed, it bounces. Any client-side measurement
  (presentation, owner physics, `vehicle_trace`) inherits focus state.
- On a machine with multiple sessions, foreground is stolen every few seconds by other
  applications: measured Discord, OpenCode, Cursor, another session's AddonBuilder, and explorer.

Rules:

1. A bench measuring client **holds foreground during the entire run** (reaffirming it
   every 0.25 s suffices) and **records compliance** every second along with data.
2. If design requires removing focus, park it on a **visible and activatable window of an
   own process** (a Tk window works). Two measured destinations that fail: DayZ server
   console (Windows returns focus to client instantly: compliance 1.00 with ~430
   attempts per cell) and `Start-Process notepad.exe` on Windows 11 (returned PID is a
   launcher that exits immediately; window lives in another process).
3. A cell archive run with random focus mixes two frame regimes: before
   comparing variants, stratify by frame time or repeat with focus held.
