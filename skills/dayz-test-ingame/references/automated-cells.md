# Automated in-game test cells: harness patterns and measured walls

How to build a scripted test (a "cell") that boots the game, drives it without a human and reads a verdict from the logs: the headless pattern, what a mission `init.c` may and may not do, getting a player into a vehicle by script, gates that can actually fail, teardown order, and what makes a run valid evidence. The ready-made self-reporting test mod is in `assets/autotest-mod/` (see `linux-headless-client.md`).

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it. Tags such as `SP-078`, `LL-196` and `CLAIM-...` are the finding numbers of the knowledge pack this material came from; they are kept so that cross-references between files stay searchable. `DAYZ_INFRA.md` is that pack's infrastructure note (in this repo `skills/_shared/knowledge/environment-and-infra.md`); a tag like `[EXACT - DAYZ_INFRA.md §Section]` names the section of it that records the fact.

Vanilla script facts cite the file on `P:\`. Measured results and third-party behaviour (dayz-mcp, Community Framework, project mods such as LFHeli and LFQuad) are not yet checked on `P:\`.

## Headless autotest pattern (no client, scripted spawn)

For automated physics/spawn testing without a human client, a dedicated harness lives at
`LFQuad_dev\tools\dayz-autotest.ps1` (reuses this launcher's build+deploy). Five gotchas that
cost many iterations, recorded so the next headless harness works first try:
1. **Historical detached pattern - superseded 2026-07-15.** A direct `Start-Process` avoided
   waiting on the DayZDiag grandchild but left it outside the registered lifecycle. Launch now
   exclusively through the managed Diag launcher after acquiring the lease; retain its `run_id`
   and poll the RPT read-only. Do not recreate the old direct invocation.
2. **A test mission `init.c` should skip `CreateHive()`** (CE economy) for a physics test - it
   loads ~20k loot items and delays the mission loop by minutes.
3. **A `CarScript` vehicle only ticks `OnUpdate` / simulates with a player present.** A headless
   server with zero clients won't drive the vehicle's own script; spawn after a client connects
   (the harness has a `-WithClient` mode that connects a second diag instance to 127.0.0.1).
4. **Cell infrastructure (spawn-on-connect, engine watcher, auto-test hooks) belongs INSIDE the
   mod under `#ifdef DIAG` + a CLI param - never only in the mission `init.c`** (added 2026-08-17,
   LFHeli). The mission lives under Steam (`DayZServer\mpmissions\<mission>\init.c`), which no
   portable pack, backup or repo carries: the LFHeli cell infra written into `init.c` on
   2026-08-12 (`CreateObjectEx` on `InvokeOnConnect` + `EngineStart()` pre-crew watcher) was
   gone on the other machine five days later and had to be recovered from a transcript. In-tree
   it travels with the PBO, is versioned, and stays inert in retail by absence of the flag
   (pattern: `LFHeliCore\scripts\5_Mission\LFHeliFLIRMission.c` `modded class MissionServer`,
   `-lfheliAutoGetIn=1` in `LFHeliPlayerBase.c`). Corollary measured the same day: start the
   engine BEFORE the crew sits - a sleeping PARKED body rejects the injected get-in action.
5. **PowerShell orchestrator traps that hang a cell silently** (measured 2026-08-17, LFHeli
   `run_celda_scripted.ps1`): (a) never name a function parameter `$Args` - it is the automatic
   variable, `@Args` splats EMPTY and `& python` with no argv opens the interactive REPL that
   never returns (the cell sat at "flip DebugLog" for minutes with a `python.exe` child and no
   arguments); (b) `& native 2>&1` under `$ErrorActionPreference='Stop'` turns any stderr line into
   a terminating error (PS 5.1) - wrap native calls in a helper that switches to `Continue` and
   returns text + `$LASTEXITCODE`; (c) the DayZ CLIENT needs a usable Steam
   (`HKCU\Software\Valve\Steam\ActiveProcess` pid AND ActiveUser ≠ 0): a Steam restarted minutes
   earlier sits at pid populated / ActiveUser=0 and the client dies at bootstrap with a ~1 KB RPT
   and an `ErrorMessage_*.mdmp` while the SERVER (no Steam) boots fine - `steam.exe -shutdown` +
   relaunch repopulated the key in ~20 s. Check the key in the pre-flight of every cell.

## Mission `init.c`: do not extend previous module types from fixture (SP-140)

[IN-GAME CONFIRMED, DayZ 1.29 server diag, 2026-07-30] On this compiler a
generated mission adding `modded class` on `4_World` types failed with
`Unknown type` for both a concrete class (`SmallStone`) and a base
(`BuildingBase`). An earlier incident reproduced the same with
`LFPG_NetworkManager`. Offline text tests did not detect the boundary.

Rule for mission oracles: use an already compiled receiver exposing contract
under test. If you need to add a method, bridge must live in the
same module/PBO as the type and requires its own candidate/amendment; do not
inject it as `modded class` from `init.c`. Keep fixture calls and boolean
expressions in single-line vanilla forms: `&&` operator at the
start of next line produced `Incompatible parameter` + `Syntax
error`. Before expending pairs, run a single control requiring Module
Game/World/Mission, OnInit, and oracle marker.

Evidence: the `script-final.log` of attempts 3 (`f02-unknown-type`), 4 (`f03-cross-module-modded`) and 5
(`f04-boolean-linebreak`) of the LFPowerGrid server-footprint validation of 2026-07-30; the existing receiver
closed the control run (`a7-control`).

## WHEEL SIMULATION DIAGNOSIS (vehicle won't drive / bounces / sinks)

When a modded `CarScript` vehicle spawns but won't drive - wheels mount yet don't
spin, chassis bounces or sinks, engine revs with no speed - the failure is almost
always one of two MEASURABLE things, not mass/inertia. Instrument and read them
side-by-side against a known-good reference vehicle (e.g. the vanilla sedan or the
Croco quadbike) IN THE SAME RUN before touching geometry.

### 1. Is the wheel seated in PhysX, and does it touch ground?

- `WheelCountPresent()` - how many wheels the simulation actually seated (the gate).
  `0` while `WheelCount()` returns N means the slot/FireGeometry wiring is wrong; see
  the `enforce-script-reference` wheel-attachment rule and audit check SP-017.
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
clearance vs tire radius - audit check SP-023), not the model.

### 3. Gotcha: parser/instrumentation drift before declaring the test failed

When the harness reports "ERROR / no data", first confirm the parser regex still
matches the CURRENT log-line format of the instrumentation. A log-format change
(renamed tag, reordered fields) reads as a test failure when the test actually ran
fine. Check the regex against a raw sample line before concluding the build is broken.

(origin: SP-023; LFQuad wheel-well and placement session, 2026-06-01)

## DEVELOPER vs DIAG_DEVELOPER - the standard diag only defines DIAG_DEVELOPER (SP-033, added 2026-07-14)

The standard `DayZDiag_x64` defines `DIAG_DEVELOPER` but NOT `DEVELOPER` (bare). Verified in `script_*.log` of both peers: server/client defines include `DIAG,DIAG_DEVELOPER,...,FEATURE_NETWORK_RECONCILIATION` - no `DEVELOPER`. So every vanilla `#ifdef DEVELOPER` block (e.g. the debug get-in: `DayZPlayerSyncJunctures.SendGetInVehicle`, `SJ_DEBUG_GET_IN_VEHICLE`, `PlayerBase.TryGetInVehicleDebug`, much of `plugindeveloper.c`) does NOT exist in this build. `OnDebugSpawn` working (it is `#ifdef DIAG_DEVELOPER`) does NOT prove `DEVELOPER` is active - different macros. Vanilla: `P:\scripts\4_world\entities\manbase\playerbase.c:3531` opens the `#ifdef DEVELOPER` block that holds `SetGetInVehicleDebug` and `TryGetInVehicleDebug`.

Expensive trap: if a mod PBO EMITS a `#ifdef DEVELOPER` symbol (a call to `SendGetInVehicle`, etc.), the symbol does not exist -> HARD compile failure of the WHOLE PBO -> every tool/script of the mod drops. Not a silent no-op (unlike `ExecuteEnforceScript`, Developer-only, which returns false at runtime).

Rule before basing a design on a vanilla `#ifdef DEVELOPER` API: (1) grep the `#ifdef` guarding it (`DEVELOPER` or `DIAG_DEVELOPER`?); (2) if `DEVELOPER`, read the `defines:` line of a recent `script_*.log` for that build to confirm it is active; (3) if not, do NOT emit the symbol - wrapping it in `#ifdef DEVELOPER` is not "robustness" if the design DEPENDS on it; find a non-DEVELOPER path. Cross-ref `dayz-mod-workflow` (anti-confabulation). Origin: DayZ_MCP Phase 5, section A (2026-06-28), compile logs of both profiles.

## (added 2026-08-12, LFHeli COM/pivot cell) AUTOMATED in-game cell without pilot: the 4 measured walls and workarounds

Eleven iteration cells in one day to get an automated cell green (stack + get-in +
engine + probes + parser, ~5 min). The four walls, measured with discriminants, so as not to pay
them again:

1. **DayZDiag does NOT define DEVELOPER for scripts (DOES define DIAG and DIAG_DEVELOPER)** - measured with
   defines telemetry on connected client. Any vanilla mechanism under `#ifdef DEVELOPER`
   (e.g. `SetGetInVehicleDebug`/`TryGetInVehicleDebug`, `P:\scripts\4_world\entities\manbase\playerbase.c:3524-3549`) DOES NOT EXIST in
   diag. Gate test code via command line parameter
   (`CommandlineGetParam`, `P:\scripts\3_game\global\game.c:661`) or via `#ifdef DIAG`, never DEVELOPER.
2. **Automated get-in in MP: `StartCommand_Vehicle` directly from client seats a
   local GHOST** (own=true, HUD active) but server NEVER registers crew (crew0=false,
   consumed=0, ObtainState silent). The route that works: inject real ACTION -
   `ActionManagerClient.PerformActionStart(GetAction(ActionGetInTransport), target, null)`
   (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804`; in MP enters through ActionStart, synchronized flow mirrored by
   server). Target componentIndex is obtained iterating `CrewPositionIndex(c)` until it returns desired seat
   (`CrewPositionIndex`, `P:\scripts\3_game\vehicles\transport.c:179`).
   Success is observed with `GetCommand_Vehicle()`
   on next tick (with retry), not marking done upon injecting. NOTE: `ActionCondition` is
   protected - cannot be pre-validated from outside; manager validates on both sides.

   **The framework reconciling this with SP-295** (measured against vanilla tree, 2026-08-18):
   crew membership and vehicle command are TWO distinct things, and only real action
   produces both. Crew is NATIVE engine state, not a script netsync:
   `Transport` registers a single variable (`m_EngineZoneReceivedHit`, `transport.c:110`) and
   `CrewMember`/`CrewDriver` are `proto native` (`transport.c:179-191`), readable from any
   client - that is why a client wanting to get in can reject an already occupied seat
   (the `CrewMember` check at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:50-52`).
   `HumanCommandVehicle`, on the other hand, is created by
   `StartCommand_Vehicle` on THE MACHINE that calls it, and across the vanilla scripts on `P:\scripts` (3,044 `.c` files in 1.30) there are
   exactly three call-sites: action itself (`actiongetintransport.c:104`), resumption
   after unconsciousness via `m_TransportCache` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2395`) and a debug under
   `#ifdef DEVELOPER` (`playerbase.c:3541`). **None starts the command upon finding out via network
   that one is already seated.** From there arise both sides of the same fact: calling
   `StartCommand_Vehicle` directly from client gives command WITHOUT server crew (the ghost
   above); seating someone via script from server gives crew WITHOUT local command, and then
   any `ActionCondition` requiring being seated is NEVER satisfied, because they check
   `GetCommand_Vehicle()` and not `CrewMember` - as done by get-out
   (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:70-76`) and start/stop engine (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:26-37`). Beware of
   `IsInVehicle()`: accepts both routes (command OR parent Transport,
   `dayzplayerimplement.c:468-471`), so it is useless to distinguish them.
3. **A ASLEEP body rejects the injected get-in action** (PARKED sleep gate). If the mod
   sleeps the vehicle at rest, the cell must WAKE IT UP before get-in - simplest:
   start the engine server-side from test mission (`EngineStart`, `P:\scripts\3_game\vehicles\car.c:233`) AS SOON AS
   spawned, not upon detecting crew. Furthermore, without engine/simulation OwnerState channel does not flow
   (silent ObtainState/RewindState) even if player is seated.
4. **The real Enforce compile gate is stack STARTUP** (no offline check sees
   method visibility, e.g. protected). The cell must search `Compile error` / `Can't
   compile` in server script log BEFORE waiting for later phases, and treat client
   message-box as hang (phase timeout).

Orchestrator pattern that worked: wrapper with named PHASES (BOOT-spawn / BOOT-log /
COMPILE / CONNECT / GETIN / probes / SETTLE / teardown / PARSE), each with PASS/FAIL
verdict and its own timeout; logs are copied to evidence EVEN IF a phase fails; teardown
kills ONLY PIDs the cell launched. Full reference:
the LFHeli project's `run_celda_compivot.ps1` wrapper and its `evidence-2026-08-12-offset` folder (11 cells with the
cause of each failure), from the LFHeli OH-1 session of 2026-08-12.

## Preflight: prove your cell's gates can go RED before you trust a single green run (added 2026-08-13, LFHeli council; LL-249)

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

**1-bis. The symmetric one: a pattern that CANNOT come out green - `not closed` is a false red.**
(measured 2026-09-07, LFPowerGrid). If you add `not closed` to the gate thinking of Enforce's
`CParser: quoted string not closed`, you will find it in **healthy** boots:
CommunityFramework writes
`File "$mission:storage_1/communityframework/modstorageplayers.bin" was not closed. Always shut
down the server gracefully to prevent data loss.` every time previous server did not shut down
gracefully - which is ALWAYS if stopped via tool. Measured on same box: 1 occurrence in a
green boot and 0 in next, with `CParser` at 0 in both, meaning difference was shutdown
mode, not code. **Anchor pattern to `CParser`, not the loose phrase**, and if you really
want the phrase, also require `CParser` on the same line. A gate shouting red on
good boots deactivates itself: by the third time, someone ignores it.

**2. An analyzer whose input does not depend on the experiment.** Hardcoded log paths
(`$clientPath = ...client_script_2026-08-12_11-25-05.log`) mean every future A/B re-analyses the
same old flight and reports "no change" tautologically. Its sibling: a script that only prints
statistics and never sets an exit code - without one, nothing can fail, so it is a report, not a gate.

**Preflight before trusting any inherited gate** (cheap, and it is the only thing that separates a
gate from decoration):

1. Feed it a fixture that MUST fail, and confirm it fails. If you have never seen the gate red, you
   do not know it is a gate.
2. Grep the wrapper for `-SimpleMatch`/`-Raw`/`-Literal*` next to any pattern containing `|`, `.`,
   `*`, `\` or `(`.
3. Require parametrised inputs, and assert the analysed artifact is **newer than** the run that
   produced it (a stale-input check is one line and catches the whole class).
4. Require a non-zero exit code on failure, and check the caller actually propagates it.

Corollary for measurement campaigns: fix the gates BEFORE the campaign, not after. A campaign run
through a decorative gate produces greens that mean nothing, and you cannot tell afterwards which
of them were real.

## Teardown copies the logs BEFORE killing the client, and verifies the copy (SP-237, added 2026-08-13)

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

1. **Preflight by mechanism and mode (LL-284, LL-307).** Document each guard as `protected mechanism → affected modes` and code the branch: a client-exclusive guard aborts with client and only warns in `-NoClient`, without manual bypass. On a box with multiple stacks, an unattended cell with client is not isolated from keyboard either: census other `DayZDiag` and active mods, record PID/mods and focus risk, and use a test-exclusive DIAG guard to reject human actions that would change state while script is active. Automation preserves a separate programmatic path. If you cannot demonstrate isolation, result is `SETUP_FAIL`.

2. **Boot identity and separation (LL-258, LL-260).** In a batch relaunching client, leave a conservative cooldown of 60 s from previous shutdown to next startup; a native crash during that startup is `SETUP_FAIL`, not a mod regression. Cooldown does not apply to a truly isolated one-shot because it does not chain another client. When packing evidence, do not select file by apparent mtime: product artifacts are named in UTC and RPT/mtimes use local time. Cross-check boot-id or internal marker against ledger incident; its timestamp rules over mtime. If expected boot markers are missing, reject bundle.

3. **Complete path and bilateral compile gate (LL-310, LL-312).** Draw each critical transition as `input → observable state → exit → poststate` and execute it via software. An autotest that only enters has incomplete coverage; first find the closing trigger among existing watchers, cancellations, and timeouts. Extend the server compile gate (wall 4 of the automated-cell section above) to the client log: scan script logs of both peers for `Compile error` / `Can't compile` before waiting for functional markers. `Dead client / live server + Can't compile` is a client-only code compile failure, not a timeout nor runtime regression. Offline lint does not accredit `private`/`protected` visibility; real compilation of both peers is authoritative.

4. **Shutdown matching the measurement (LL-277).** SP-237 ("copy/verify before killing") preserves already emitted evidence, but does not accredit metrics born upon exiting. For leak reports, flushes, destructors, or final hooks, request graceful shutdown, wait for an explicit marker that the report or hook executed, and only then collect result. A forced kill produces `SETUP_FAIL` for all exit metrics and also prevents verifying a fix living in that hook. "Problem did not appear" never equals `PASS` if check never ran.

## Diagnostic spawn without depending on VPP UI (SP-210, single-use scope)

If administrative UI blocks a diagnosis, a private mission can use
`CustomMission.InvokeOnConnect` (`P:\scripts\5_mission\mission\missionserver.c:435`) to create a fixture once per boot, at fixed distance from
player, with `CreateObjectEx(..., ECE_PLACE_ON_SURFACE)`. Use a one-shot boolean and clean storage.

It is a disposable fallback, not cell infrastructure. The portable rule of "Headless autotest pattern", point 4, continues
to govern: any spawner, watcher, or control that must survive the project lives inside the mod,
gated by DIAG and by an explicit parameter.

## Parsers: first extract actual `Print` payload (SP-234)

A string variable arrives in script log with a form equivalent to:

```text
SCRIPT       : string <var> = '<payload>'
```

Closing single quote is stuck to the last field. First extract what is between
`= '` and the last quote; only then tokenize numbers and fields. A log gate always includes
literal fixtures copied from a real log, in addition to synthetic cases, and counter-fixtures with truncated
wrapper. A self-test that never consumed a real line only validates the imagined parser.

## Teleport and readiness before injecting an action (SP-235)

To teleport player in a harness use X/Z of probed point and
`Y = GetGame().SurfaceY(x, z)` (`P:\scripts\3_game\global\game.c:1176`). The Y of a memory point can leave them in
`ACID_Human_Fall`; during Fall, an injected action can abort without error while server already
reserved seat.

Before spending an attempt, require an accepted command ID, no action in progress,
`CanStoreInputUserData()`, and `ActionBase.Can(...)`. Then observe real transition; do not mark
success upon sending action. A desync `server=Move, client=Fall` points first to placement.

## Headless retail server as parity term (SP-242)

The requirement of `DayZDiag_x64.exe` in the prerequisites (`windows-launch-cycle.md`) is scoped to iteration with `-filePatching` and to
official launcher of this skill. A headless retail `DayZServer_x64.exe` can load PBOs with
`-mod`, compile Enforce, and execute outbound `RestApi` without occupying client Steam session.
Measurement observed defines `RELEASE, SERVER, NO_GUI, SERVER_FOR_WINDOWS` and real HTTP polling.

Use it as second term of a diag↔retail gate when server-side behavior may
depend on `RELEASE` or developer-only APIs. It does not replace client for visual capture or for
verbs requiring a connected player. This server remains outside official lifecycle: only
a probe-gated runner possessing its exact PID can start and stop it.

## Multi-peer cells: clock, replay, and bilateral probes (SP-276 / SP-278)

For an exit failure or desync, instrument the callback equivalent to `OnDriverExit` on both
peers and emit in a single window `playerPos`, `vehiclePos`, `crewEntryWS`, and their distances. Align
client/server clocks with pairs of the same event; do not compare raw peer timestamps.

In an owner series with rewind/replay, multiple samples can share the same `t`. Retain the
first sample per tick -or collapse a documented interval smaller than 20 ms- before evaluating
edges. Convert server events to owner clock, use authoritative series as
primary oracle and owner as secondary, and re-run history after changing
the parser.

The bridge does not inject arbitrary values into `UAInput`. If the mod neutralizes `CarController` and
consumes its own axes, a cell needs a DIAG script on the owner before `WriteToMove`; this branch
is only promoted for the mod when an in-game run demonstrates that it steers.

## Contract of a repeatable scripted cell (SP-279)

- Spawn fixture at a known fixed location and place player at a fixed offset on
  `SurfaceY`; random spawn turns obstacles and doors into environmental noise. A default spawn also draws a random character class: pin it (`session-findings.md`, "H2R import (2026-10)").
- After an exit, rearm placement server-side after cooldown with player on foot.
  Re-entry is part of the test: a ghost pose on client invalidates reach and `Can()`.
- `forces-off`, `clamp-abort`, `no-probes`, `no-pilot`, and `not-owner` are **INCONCLUSIVE** and accept
  bounded retries. A timeout after satisfying preconditions is **FAIL**.
- Script executes; it does not adjudicate. Its gates are the same as preregistration. Detects "settled" by
  sustained AGL or, better, by authoritative state, not by an isolated owner velocity.

## Isolation, settle, and effect probes in cells (SP-285)

While scripted pilot is active, a DIAG guard must reject in `ActionCondition`
human actions that break the cell, but preserve a separate programmatic route. Settle is
decided by mirrored authoritative state (`GROUND_READY`/`PARKED`) and uses AGL only as backup;
owner can keep bouncing after authority is settled.

Instrument symptom callback on both peers with a gated probe and stack. On client print
stack line by line to prevent truncation and do not call APIs whose validity is server-side only. Upon
startup, runner probes other running DayZDiag with PID, modline, and port; if 2302 belongs to another
session, choose a different accredited port. This extends the preflight of "Validity of an automated run" without touching foreign
peers.

## Whoever opens a manual process also closes it (SP-344)

Managed runs are closed by their `run_id`. For an authorized manual process outside MCP,
the agent that opened it retains PID and `CommandLine`, requests orderly shutdown with
`CloseMainWindow()`, waits 8-10 s and uses `Stop-Process -Id <pid>` only as exact fallback. Never
select by executable name or touch a peer from another session.

If the window was opened by the user and they are playing, closing remains theirs via UI. If opened
by the agent, the user is not turned into a cleanup operator; asking to continue the cycle authorizes
closing only those own processes.

## An in-game observation is worth whatever the `-mod=` line of ITS run is worth (added 2026-09-05)

Distinct from SP-124 in `managed-launcher.md`, which reads `-mod=` to know **whose box it is**. This one
reads it to know **if the observation serves as evidence**, and is done BEFORE using it, not at
launch.

Measured on 2026-09-04 on two mods at once. Of six runs with `@LFQuad3`, **one** carried
`@SurvivorAnims`; of the four of LFQuad2, **none**. `LFQuad3.c:86-88` (and its twin in
LFQuad2) does `GetAnimInstance` -> returns 22 only if `CfgPatches SurvivorAnims` exists, and otherwise
falls back to `VehicleAnimInstances.V3S`, which is TRUCK pose on a quad. With the wrong pose
**driver camera is not where it would really be**, and that moves both what is seen from
seat and which LOD engine chooses. LFQuad2 had diagnosed and "fixed" a LOD
symptom on those runs and had to withdraw the fix: cause was not verified.

The failure is silent by construction: missing mod gives no error, game starts,
observation seems normal and user reports it in good faith.

**Upon receiving an in-game observation that will decide code or geometry:**

1. Locate RPT of THAT run (server and client) and read its first `-mod=` line.
2. Check that mods on which observed behavior depends are present. The three most silent:
   - an **animations** mod queried by `ConfigIsExisting` from `GetAnimInstance` or
     other hook -> without it, pose and camera are different;
   - a **framework** (CF and company) that writes modstorage per entity;
   - the content mod itself whose objects must be seen.
3. If any is missing, observation is not discarded: **it is reclassified**. Whatever does not depend on
   pose or LOD remains valid (a mirrored texture is so from any angle); whatever
   depends on where the eye is, does not.
4. With every mod present, read two more things from THAT run: whether it rendered textured and, for
   anything that depends on where the eye is, where the eye was. Both changed between runs with the same
   command line in the H2R import (2026-10) (`session-findings.md`).

Name trap in this tree: `@Survivor Animations` **with space** splits the command
line (in RPT it is seen cut off at `-mod=...;P:\Mods\@Survivor`). The good junction is
`@SurvivorAnims`.

Cheap audit of a whole workday, to know which runs are valid:

```bash
for f in _server/profiles/*.RPT _client/profiles/*.RPT; do
  m=$(grep -m1 -oE '\-mod=[^ ]*' "$f")
  printf "%-52s %s\n" "$(basename $f)" "$m"
done
```

## An unfocused DayZDiag client runs at ~20 fps: what the client measures depends on who holds the foreground (SP-391, added 2026-09-13)

Measured on F1 bench of LFHeli (DayZDiag, windowed client and server on same machine),
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

Evidence and recipes: the LFHeli session note of 2026-09-13 ("the bounce follows the client's focus") in the source author's notes.
