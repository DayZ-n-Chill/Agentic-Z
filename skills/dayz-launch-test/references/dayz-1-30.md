# DayZ 1.30 — launch / session-test deltas

Companion to the rules in `README.md` ("Rules that hold on every route"). Diag-only managed lifecycle, absolute
`-mod` paths, and the filepatching-vs-PBO caveats still hold. This file is the
1.30 launch-flag, action-injection and MCP tooling delta.

Script line numbers cite the vanilla scripts unpacked on `P:\scripts\` and were re-opened there for
this file. Quoted changelog lines come from the DayZ 1.30 Experimental modding changelog. Runtime behaviour
of the new exe flags is [CHANGELOG] / [UNVERIFIED]: it was read from the changelog, not measured with a
1.30 DayZ Tools binary. Measurements made with the third-party dayz-mcp tooling, and readings of the 1.29
scripts (1.29 is not unpacked on `P:\`), are not yet checked on `P:\`.

## Unpacked `-mod` folder (configs without packing)

(until 1.29: this skill's loop was "re-pack the PBO, deploy it where the
engine reads mods, and launch DayZDiag".) (since 1.30 [CHANGELOG], the 1.30 Experimental modding changelog):

> Changed: Mods now have their own named filesystem
> Changed: Improved unpacked mod workflow; -mod can now point to a physical folder
> Changed: RV configs can now be read when loaded as an unpacked mod

[DESIGN] For **config.cpp / script** iteration, `-mod` may name the addon
**source folder** (still prefer absolute paths; the silent-no-mount gotcha of
bare `@Name` is unchanged). `.p3d` / `.paa` still follow the existing
filepatching-does-not-reload-binaries rule. A shipping test still packs.

[EXACT] Measured bound of that [DESIGN] (dedicated server, 1.30.164014 Exp, 2026-09-27): an unpacked `-mod` folder mounts as a `relative directory` (RPT: `Adding relative directory ...` vs a PBO's `Adding package ... (pbo count: N)`); with a `CfgMods` block it injects the mod's define into the script modules and loads its scripts, but it does NOT merge its `config.cpp` into the runtime config tree — `ConfigIsExisting("CfgPatches <mod>")` stays false. World configs (`CfgWorlds` terrain `Holes`) therefore require a PACKED PBO: unpacked, `SurfaceIsHole` stays false and the RPT logs `No entry 'config.bin/CfgWorlds/<world>.Holes'`; the same PBO mounted and measured true when packed (the PBO may carry `config.cpp` as text, no binarize needed). Measured in game, DayZ 1.30.164014 Exp.

## New launch flags

(since 1.30 [CHANGELOG], the 1.30 Experimental modding changelog):

> Added: '-resolveFilePatchingUsingEnfusion=0/1' for file patching to
> prioritize looking through named enfusion filesystems before checking
> launched directory (requires -filepatching, always enabled in Workbench)
> Added: '-cacheP3D=0/1' command line launch option, creates .p3dcache files
> next to .p3d files to allow for quicker subsequent launches of the
> Game/Buldozer when working with unbinarized assets

[DESIGN] Append to Diag argv when iterating unpacked / MLOD assets, for
example:

`-filePatching -resolveFilePatchingUsingEnfusion=1 -cacheP3D=1`

Requires `-filePatching`. Workbench always enables the resolve flag.
`.p3dcache` siblings are local caches — do not commit them as product.

## Headless roboclients vs `Mode=all`

(since 1.30) `CGame.IsHeadless()` and `IsHeadlessOrDedicatedServer()`
(`P:\scripts\3_game\global\game.c:1130`, `:1136`) —
see `skills/dayz-mod-workflow/references/dayz-1-30-mod-workflow.md`. This skill's
MCP composition still requires `-Mode all` for a **rendered** client
(the MCP verification references (`references/mcp/README.md`): headless has no window to grab).

[DESIGN] A load-test roboclient is `IsHeadless()==true` and must not be used
as the capture peer. Script that skips VFX should use
`IsHeadlessOrDedicatedServer()` so roboclients match dedicated.

`IsHeadless` is absent from the 1.29 `3_Game\Global\Game.c` (a 1.29 reading, not yet checked on `P:\`).

Measured 2026-09-26 on build 1.30.164014: the headless client (`-headlessMode=1`)
crashes before loading `World`, so there is no headless load-test roboclient in
this build yet. Server-side dummy bots do the job instead; details and numbers in
"Roboclients vs server-side dummy bots" below.

Roboclients are headless: they poll neither a client_peer suitable for `capture_screenshot`
nor a rendered HUD. [DESIGN] Keep `-Mode all` + `@DayZ_MCP` for visual smokes. Do not treat a
headless roboclient as the MCP client_peer.

## Launching the 1.30 DayZDiag directly (outside the managed lifecycle)

On 2026-09-26 the managed launcher still ran the 1.29 install (managed runs on
1.30.164200 are recorded from 2026-10-26 in
"Vehicle tests on 1.30.164200" below). Probing the Exp install by hand
on that date (measured with the dayz-mcp tooling)
hit six traps, each costing a run:

1. **The script log is the define oracle.** Each module logs
   `Module: <name>; …; defines: "…"`. Reading that line after a launch to the main
   menu (~20 s) answers "is X defined in this exe?" without writing a probe mod.
   It also shows the version define, `DAYZ_1_30`.
2. **From the Claude desktop app the game can read a dead Steam PID.** The app sees a
   private, frozen copy of `HKCU\Software\Valve\Steam\ActiveProcess` (MSIX registry
   virtualization). After Steam restarts, a game launched from the app reads a
   dead PID, logs `Unable to locate a running instance of Steam` and shows an error
   dialog while `steam.exe` runs. Compare the app's view with the real value (WMI
   `StdRegProv`) and the live `steam.exe`; then launch through WMI
   (`Win32_Process.Create`) or sync the copy right before launching. Writing the
   value from a shell inside the app only fixes the private copy, and only until the
   next Steam restart.
   Two measured corollaries (2026-09-23/24). Never START or restart Steam from a shell inside the sandboxed app: the new Steam registers in the private copy, and the REAL key can be left at `pid = 0, ActiveUser = 0` — a state the outside WMI check reports as broken while the app's own view looks healthy, and which `auto_remediate_steam` cannot fix because the worker sits inside the app too. Never write or delete another app's HKCU keys from an app shell: a write creates the private copy (shadow), a delete leaves a tombstone that hides the real key even after it is rewritten outside; the shadow only disappears with the app closed and the hive loaded offline. Preflight BOTH views: WMI `StdRegProv` reads the real hive, `Get-ItemProperty` inside the app reads the copy the launched client will see — require both to point at the live `steam.exe`. [EXACT] (measured)
3. **A very long `-profiles=` path is a crash suspect.** A ~245-character profiles
   path ended in `0xC0000005` after 1 s with no log written; a short path did not
   repeat it. Steam was broken at the same time, so the cause is probable, not
   isolated. Keep profiles paths short.
4. **Launch DayZ with a whitelisted environment.** A DayZ `ErrorMessage_*.mdmp` or
   crash minidump embeds the parent's whole environment block, and an agent shell
   usually carries API keys and passwords. On every crash the DayZ CrashReporter
   also sends "analytical data" before offering the dump. Start DayZ with
   `ProcessStartInfo.UseShellExecute = $false` and remove every variable not on a
   short whitelist (`SystemRoot`, `Path`, `TEMP`, `USERPROFILE`, `APPDATA`,
   `LOCALAPPDATA`, `ProgramFiles*`, processor/OS variables, `ComSpec`), and delete
   dumps you do not need.
5. **Own the PID.** Out-of-lifecycle probes start and stop only the process they
   launched, and hold the MCP lease while they run so no managed run lands on top.
6. **Use a fresh `-profiles=` directory per run.** A readiness check that greps the
   newest `script_*.log` found a log left by an earlier run in the same directory.
   It reported the server ready and the client connected at +0 s (2026-09-26): the
   run looked healthy and measured nothing. A client that never loads its textures fools a visual check the same way (`session-findings.md`, the section on untextured runs and a moving 1PP eye).

## Measuring server load

What worked on 2026-09-26 (dummy-bot load, same measurement session):

- **Cap the server.** Uncapped, the Diag server ran at ~1958 FPS and FPS was no load
  signal (10 moving dummies: 1900; 25 idle: 1908). `-limitFPS=60` (the 1.30 exe
  carries a `limitfps` switch) turns frame drops into the saturation point and makes
  process CPU per window comparable across load steps.
- **Meter frames inside the server.** Count `timeslice` in an `override void OnUpdate(float timeslice)`
  of the server mission (`P:\scripts\5_mission\mission\missionserver.c:108`) and log per
  window: frames, seconds, FPS, max frame time. Sample the process
  `TotalProcessorTime` every second from outside and join by timestamp.
- **Bracket the run with baselines, and do not trust a fixed warm-up.** The first three
  windows of run 2 (a fresh storage) ran at 36-84 % machine CPU. In run 3 a 120 s
  warm-up was not enough either: its first baseline used 0.276 server cores, against
  0.001 at the baseline taken after deleting all load. Record a baseline at both ends,
  and treat a large mismatch as an inconclusive comparison.
- **Check post-spawn idle windows.** After 15 s settles in run 2, the idle window right
  after spawning 25 dummies used 0.201 server cores against 0.010 in the moving window
  after it, with the machine nearly idle (3.8 % CPU). At 50 dummies the gap was 0.179
  against 0.032 cores, but machine CPU was 49.2 % during that idle window. The cause
  was not isolated. Run 3 used 45 s settles and its idle windows after spawning 50 and
  100 averaged 60.0 FPS; that does not make 45 s a validated settle time for CPU.
- **Keep the CPU sampler cheap, and check it for gaps.** In run 3 the 1 s sampler went
  58.7 s without a sample across a spawn. Its loop also ran a WMI machine-CPU query and
  a script-log scan every 5 s; the cause was not isolated. The gap crossed two windows,
  which kept only 32 and 43 of their 45 s sampled. An analyzer that takes the nearest
  samples around a window then mixes stages into its CPU delta. Use the samples inside
  the window, report how much of it they cover, and drop the window when coverage is
  short. The in-server FPS meter was unaffected.
- **Write CSV numbers with the invariant culture.** On an es-ES host,
  `'{0:F3}' -f` writes decimal commas and silently splits every CSV row into
  extra columns. Use `[string]::Format([Globalization.CultureInfo]::InvariantCulture, …)`.

## `PerformActionStart` in SP — pending guard + `UA_AM_INIT`

(until 1.29: this skill cited `actionmanagerclient.c:762`.) (since 1.30:
the method is at `:804`. Singleplayer no longer overwrites an in-flight
pending/current action.)

```
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804-828
	void PerformActionStart(ActionBase action, ActionTarget target, ItemBase item, Param extra_data = NULL)
	{
		if (!g_Game.IsMultiplayer())
		{
			if (!m_PendingActionData && !m_CurrentActionData)
			{
				m_PendingActionData = new ActionData;
	
				if (!action.SetupAction(m_Player, target, item, m_PendingActionData, extra_data))
					m_PendingActionData = null;
			}
		}
		else
		{
			ActionStart(action, target, item, extra_data);
		}
	}
	
	override int GetActionState()
	{
		if (m_PendingActionData)
			return UA_AM_INIT;
		
		return super.GetActionState();
	}
```

1.29 contrast: line `:762` of the same file was the old `PerformActionStart` line (a 1.29 reading, not yet
checked on `P:\`).

`UA_AM_INIT = 14` was inserted; later `UA_AM_*` values shifted:

```
// [EXACT] P:\scripts\3_game\constants.c:506-511
	const int 		UA_INITIALIZE = 12;
	const int		UA_CHECK_CON = 13;
	const int		UA_AM_INIT = 14;
	const int		UA_AM_PENDING = 15;
	const int		UA_AM_ACCEPTED = 16;
	const int		UA_AM_REJECTED = 17;
```

[DESIGN] Autotest that injects a second `PerformActionStart` in SP without
waiting for idle will silently no-op. Wait until `GetActionState()` is not
`UA_AM_INIT` / not pending. Never hardcode the integer `14` — use the
constant.

MP path is unchanged: `PerformActionStart` still calls `ActionStart` directly
(`:816-819`).

Through the MCP: `action_use` in singleplayer no-ops the same way while a pending or current
action is set. Continuous actions already do not complete via MCP (`mcp/actions-ui-and-inventory.md`).
For instant actions, if a second inject returns `setup_failed` or a no-op, wait for
`GetActionState()` to leave `UA_AM_INIT`.

## Navmesh / Tools (session awareness)

Custom terrains: regenerate `.nm` (no backwards compatibility, per the 1.30
changelog). Workbench 1.30 was not available when this was written; treat Tools
UI claims as [CHANGELOG].

## `ScriptConsoleTabRegistry` (inject a Diag console tab)

(until 1.29: adding a Script Console tab meant editing / replacing
`ScriptConsole.c`.) (since 1.30: tabs register through
`ScriptConsoleTabRegistry.Register`.)

```
// [EXACT] P:\scripts\5_mission\gui\scriptconsole.c:33-43
class ScriptConsoleTabRegistry
{
	protected static ref array<ref ScriptConsoleTabRegistryEntry> s_Entries;
	
	static void Register(int id, string displayName, string widgetName, typename tabClass)
	{
		if (!s_Entries)
			s_Entries = new array<ref ScriptConsoleTabRegistryEntry>();
			
		s_Entries.Insert(new ScriptConsoleTabRegistryEntry(id, displayName, widgetName, tabClass));
	}
```

Vanilla `InitializeRegistry` (`scriptconsole.c:50-66`) registers GENERAL through WEATHER.
`ScriptConsole.BuildContextMenu()` (`scriptconsole.c:279`) calls `InitializeRegistry()` then
iterates `GetAll()` (`scriptconsole.c:293-296`); `Init()` calls `BuildContextMenu()` at
`scriptconsole.c:227`, and on console builds `OnInputDeviceChanged` calls it again at `:249`.

[DESIGN] A verification / debug tab for a mod: `modded` the registry
initializer or register from a mission module **after** vanilla init, with a
new `ScriptConsoleTabID` value **below** `COUNT`. Do not replace the whole
`ScriptConsole.c`. Tabs are Diag/developer UI, not MCP verbs - they do not
replace `bridge_status` / spawn / raycast.

[UNVERIFIED] Whether a mod can `Register` from `4_World` before
`InitializeRegistry` clears the array (`scriptconsole.c:52-53` Clear). Prefer registering
inside a `modded` `InitializeRegistry` after `super` (if super exists) or by
appending after vanilla Register calls via modded class. Confirm in-game
before treating the order as contract.

Everything about the third-party dayz-mcp server, its `@DayZ_MCP` mod (`MCP_CarScript.c`,
`MCPClientBridge.c`), its commit hashes and the measured runs in the sections below is not yet
checked on `P:\`; `[EXACT]` marks a measured result, `[DESIGN]` an unverified proposal. The managed
`dayz_test_run` / `dayz_test_stop` lifecycle and the rule that captures need mode `all` still hold.

## Roboclients vs server-side dummy bots (measured 2026-09-26)

Build 1.30.164014 Exp, public DayZDiag, local server outside the managed
lifecycle. Source paths below are the 1.30
scripts on `P:\scripts\`.

[EXACT] The public 1.30 Exp DayZDiag
compiles every script module with `ROBOCLIENT` and `INPUT_OVERRIDE` defined, as
client and as `-server` (script log: `Module: ...; defines: "...,ROBOCLIENT,INPUT_OVERRIDE,..."`).
`-headlessMode=1` adds `NO_GUI,NO_GUI_INGAME`. The 1.29 executables carry no
`ROBOCLIENT` or `RoboclientUtils` strings.

What that switches on (source-read):
- Every `PlayerBase` builds a `Bot` in `Init()` (`P:\scripts\4_world\entities\manbase\playerbase.c:607-613`),
  and so does a Script Console spawn through `OnSpawnedFromConsole` (`playerbase.c:5281-5296`,
  called from `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:350-362`).
- Without `-roboclient` the bot idles in a debug FSM whose states start on
  `EActions.PLAYER_BOT_*` (`P:\scripts\4_world\systems\bot\bot.c:344-383`, `bot.c:331-342`; enum
  `P:\scripts\3_game\enums\eactions.c:92-107`): stance and movement randomizers, user-action
  spam, attach/drop cycle, item move back and forth, spawn/open/eat/destroy a can,
  hand swaps. The Diag debug-action menu lists them (`playerbase.c:8427-8456`) and
  `OnAction` forwards them to `m_Bot.StartAction` (`playerbase.c:8356-8363`).
- With `-roboclient` the FSM comes from config through
  `RoboclientUtils.ReadStateMachines` (`bot.c:80-84`). Vanilla ships none that we
  found, so a rendered `-roboclient` connects and stands still.

[EXACT] A server-side dummy moves with no client
connected. Recipe used (APIs: `P:\scripts\3_game\global\game.c:703`, `playerbase.c:5281`,
`bot.c:205-215`):

```c
// [DESIGN] server mission script; m_Bot exists only under #ifdef ROBOCLIENT
PlayerBase d = PlayerBase.Cast(GetGame().CreateObjectEx("SurvivorM_Mirek", pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS));
d.OnSpawnedFromConsole();                                    // scheduler + Bot, as the console does
d.m_Bot.StartAction(EActions.PLAYER_BOT_RANDOMIZE_MOVEMENT); // start
d.m_Bot.StartAction(EActions.PLAYER_BOT_STOP_CURRENT);       // back to idle
```

Measured: ~33.7 m per 5 s (sprint, ~6.75 m/s) in a straight line north, ~1.7 m/s
once in water. Mean displacement: 169.2, 169.1, 168.1 and 158.9 m in 25 s for 10, 25,
50 and 100 dummies (run 2); 297.1 and 291.0 m in 45 s for 50 and 100 (run 3). The
"randomizer" is not random: it forces `OverrideMovementSpeed(ONE_FRAME, 3.0)`
and `OverrideMovementAngle(ONE_FRAME, 0.0)` every frame
(`P:\scripts\4_world\systems\bot\bot_movementrandomizer.c:26-40`). Spawn inland; from the
coast the dummies run into the sea.

[EXACT] The headless roboclient is unusable in
this build: `-headlessMode=1 -roboclient` crashes with
`Access violation. Illegal read ... at 0x0` at the same instruction, standalone and
with `-connect` (3 of 3 on 2026-09-26), after compiling `Game` and before `World`.

Load: one server at `-limitFPS=60`, no client, Ryzen 7 7800X3D. Two runs on
2026-09-26, one sample per cell:

- Run 2 added dummies in steps of 10, 25, 50 and 100 with 15 s settles, and did not
  move them back between steps.
- Run 3 spawned 50 and then 100 on a 10-wide grid (6 m by 8 m), settled 45 s, and put
  every dummy back on the grid before each moving window.

| Moving dummies | Run 2 FPS | Run 2 server CPU (cores) | Run 2 machine CPU | Run 3 FPS | Run 3 server CPU (cores) | Run 3 machine CPU |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (final baseline) | 60.0 | 0.007 | 0.6 % | 60.0 | 0.001 | 0.4 % |
| 25 | 60.0 | 0.010 | 0.4 % | not run | not run | not run |
| 50 | 60.0 | 0.032 | 2.0 % | 60.0 | 0.024 (32 of 45 s sampled) | 3.2 % |
| 100 | 54.7 | 0.384 | 34.2 % | 60.0 | 0.008 | 2.0 % |

FPS is the mean over each window (run 2: 25 s for moving windows and 30 s for the final
baseline; run 3: 45 s); machine CPU is the whole host. In run 3's setup the 100-dummy moving window averaged 60.0 FPS (33 ms
max frame) at 0.008 server cores. Run 2's averaged 54.7 FPS while the host ran at
34.2 % CPU, of which the server's 0.384 cores are about 2.4 %. The runs differ in
settles, placement, window length and host load, and none of them was isolated, so
neither run is a capacity figure. Other contamination seen that day:

- Post-spawn idle windows. In run 2 the idle window right after spawning 25 dummies
  used 0.201 server cores against 0.010 in the moving window after it, with the host
  nearly idle; the idle window after spawning 50 ran with the host at 49.2 %.
- Startup. Machine CPU was 36-84 % in the first three windows of run 2, and the run-3
  baseline after a 120 s warm-up still used 0.276 server cores against 0.001 at its
  final baseline.

Method and traps: "Measuring server load" above.

[DESIGN] For the MCP: server verbs `bot_dummy_spawn(n, pos)` plus `bot_start(action)`
and `bot_stop()` on this path would give N moving players on one machine for load
and soak tests. They need a 1.30 lane; on 2026-09-26 the managed launcher still ran
1.29 (managed runs on 1.30.164200 are recorded from 2026-10-26, below). This
is not a way to offload simulation: dummies and roboclients alike run under server
authority.

## Vehicle tests on 1.30.164200: what the LFQuad port ran into (2026-10-26)

[EXACT] Five behaviours of the bridge that shaped a car test,
on 1.30.164200 DayZDiag (Exp and stable installs), each with its way round:

- `vehicle_control` does not shift an automatic gearbox: the bridge changes gear only when
  `GearboxGetType()` is manual (`MCP_CarScript.c:790-810` of the deployed `@DayZ_MCP`), so an
  automatic car stays in neutral with the throttle open. To drive one, test a copy of the build whose `Gearbox.type` is
  `GEARBOX_MANUAL` and every other entry byte-identical, and say so in the verdict.
- `vehicle_prepare_fixture` answered `fixture_not_ready` with `fuel_fraction=0.0` right after
  `OnDebugSpawn()`, in four runs on two boxes, although `OnDebugSpawn()` fills the tank:
  `telemetry_read object_at` read `fuel_fraction=1` afterwards, and the car started and drove.
  The bridge reads the tank in the tick of the `Fill()`.
  Confirm with `telemetry_read` before calling it a failure.
- `entities_query` returns the config class as `type` and the script class as `classname`:
  a mod wheel with no script class of its own reads `CarWheel`, its `_Ruined` twin with one
  reads its own name. That is a cheap check that a mod's script class binds.
- No tool sets an item's health, so health-level
  transitions such as the 1.30 ruined-wheel swap cannot be driven. An RGD5 dropped unpinned
  1.5 m from a loose wheel took it only to 0.971. A grenade unpinned in the hands
  (`action_use ActionUnpin`, target `hands`) arms only when it leaves them
  (`P:\scripts\4_world\entities\itembase\grenade_base.c:273-281`); `ActionDropItem`, target `hands`, drops it.
- With the player seated, `camera_set` failed with `camera_unmoved_cabin`, yet the next
  capture showed the requested outside view and carried the warning `camera_unverified`. The camera had moved: that is how the driver's pose
  was checked from outside. It stays mounted until `restore_gameplay`.

## Vehicle tests on 1.30.164200: what the Arma2Quad port added (2026-10-26)

[EXACT] Six more behaviours of the bridge, from the stable
box (DayZDiag 1.30.164200 of the stable install) with a second 1.29 quad, Arma2Quad:

- In-vehicle actions need `vehicle_get_in_client` as well as `vehicle_enter`. After
  `vehicle_enter` alone, `action_use ActionSwitchLights` (target `self`) answered
  `condition_failed`; after `vehicle_get_in_client` it started and the lights came on. The client stays bound to that first car: after
  `ActionGetOutTransport`, `vehicle_enter` into a second car seated the server player, and the
  switch failed there twice. Plan one car per run.
- `vehicle_enter` with its default 15 s timeout answered `timeout` with the player already in
  the seat (`query_player_state`); with `timeout_s=30` it answered in 1.3 s.
- Parts that `OnDebugSpawn` mounts are not world objects: `object_resolve` on a mounted
  `HeadlightH7` gave `object_not_found` at 0.3 and 3 m. To remove a part during a test, mount it
  with `inventory_attach`, keep its `item_object_id` and `object_delete` that id; the detach
  path runs (the headlights went from the two-bulb to the one-bulb state in game).
- No bridge reader exposes the light state: `vehicle_telemetry` and `telemetry_read` have no
  light field. Log it from the mod under `#ifdef DIAG_DEVELOPER` (Arma2Quad prints it in
  `OnDriverExit`) or compare captures.
- With another box's DayZ server holding port 2302, `dayz_test_run` on the stable box answered
  `port_in_use_foreign` with a hint to pass another `port=`; with `port=2402` it answered
  `active_run_exists` and only queued until that server exited.
- `wait_for(log_matches, role=server, lookback_from=launch)` returned the client's
  `Module: World` line and listed only `_client` files in `scanned`. Check `scanned.files`, or the defines of the returned line
  (`SERVER`), before taking it for the server's.

## Deleting vehicles and checking what a run loaded (2026-11-01)

[EXACT] On 1.30.164200, deleting a car with a player in a crew
seat brings the game down: `ObjectDelete` on an occupied car crashed the server (runs `0ac3f9dd`
and `7eddedd4` on dayz-mcp main `f4bec4a4`), and on the client the vanilla `CarHud.RefreshVehicleHud`
hit a NULL in `CarScript.EngineGetRPM` (`P:\scripts\5_mission\gui\vehicles\carhud.c:104`) until the client stopped polling. LBAdmin
works around the same bug. dayz-mcp since commit `c7f09b7d` ejects every occupant, on every crew
position, before `ObjectDelete` in `object_delete`, `scene_clear` and the loadout cleanup, and
answers `vehicle_eject_failed` without deleting when a seat cannot be emptied. With it the server
survived (runs `0761a892` and `9cb9a5ee`). Eject first, then delete, in any tool or test you write.

[EXACT] The server only sees its own crew. A player seated with
`vehicle_get_in_client` alone sits in the car on the client and not in the server's crew, so that
eject finds nobody, the car goes, and the client's `HumanCommandVehicle` is left pointing at
a deleted car: native `ACCESS_VIOLATION` on the client. The fix (dayz-mcp commit
`cbea6034`; not tested in game) reads the client's seat telemetry
before deleting a car. When the client reports the player seated, `object_delete` refuses with
`vehicle_client_seated`, `deleted=0`. When the seat cannot be verified
(unreadable status in embedded mode, an absent or stale client, unreadable telemetry, and also in
live mode with admin), it refuses with `vehicle_seat_unverified`, `deleted=0`. Treat either answer
as a refusal, not a transient error: get the player out on the client, then retry.

[EXACT] Historical behaviour:
the `dayz-test-v1` launcher rebuilt the bridge PBO from `default_source` even with `build=false`
when `clean=true`. The rule was `effective_build = build or clean`
(`dayz_test_request.py:538`, same rule at `server.py:6130` at that time).
Whether the quad run `43b9f3cb` (PBO `3DA69CD1` to `52F9A9E5`) was such a rebuild was not verified.

Changed 2026-11-08 in dayz-mcp commit
`de772447f5adac9814257a212c29244be6bc140a`. At dayz-mcp main snapshot
`4129522921241b2d4fb3e97f62343a360fe9f173`, `tools/dayz_mcp/dayz_test_request.py:577-578`
says that clean only modifies an explicitly requested build and sets `effective_build = build`;
`clean=true` alone no longer requests a build through this rule. This is a source check, not a
new in-game test. Retain SHA-256 checks of the live server and client PBOs after launch and at
run end; do not describe the old rebuild rule as current behavior.

[EXACT] On a Windows box where `Get-CimInstance Win32_Process`
answers access denied, a provenance check that reads command lines through WMI fails before any
test step runs (run `43b9f3cb`). Measure without WMI: `Get-Process` for the DayZDiag processes,
and the command line DayZ writes at the top of each RPT for the `-mod=` and `-serverMod=` lists
(the retry, run `0a98badc`, passed that way).
