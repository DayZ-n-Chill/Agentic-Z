# DayZ 1.30: MCP and script-console tooling

What DayZ 1.30 changed for MCP verification. The managed `dayz_test_run` /
`dayz_test_stop` lifecycle and the rule that captures need mode `all` still hold.

Vanilla script facts cite the 1.30 file on `P:\`. Everything about the third-party dayz-mcp server, its
`@DayZ_MCP` mod (`MCP_CarScript.c`, `MCPClientBridge.c`), its commit hashes and the measured
runs is not yet checked on `P:\`; `[EXACT]` marks a measured result, `[DESIGN]` an unverified proposal.

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

## Headless vs rendered MCP

(since 1.30) `IsHeadless()` / `IsHeadlessOrDedicatedServer()` exist on `CGame`
(`IsHeadless` and `IsHeadlessOrDedicatedServer`, `P:\scripts\3_game\global\game.c:1130-1136`). This skill
already forbids `-Mode server` for capture (no window). Roboclients are
headless: they poll neither a client_peer suitable for `capture_screenshot`
nor a rendered HUD.

[DESIGN] Keep `-Mode all` + `@DayZ_MCP` for visual smokes. Do not treat a
headless roboclient as the MCP client_peer.

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

Method and traps:
`skills/dayz-test-ingame/references/dayz-1-30-test-ingame.md`, "Measuring server load".

[DESIGN] For the MCP: server verbs `bot_dummy_spawn(n, pos)` plus `bot_start(action)`
and `bot_stop()` on this path would give N moving players on one machine for load
and soak tests. They need a 1.30 lane; on 2026-09-26 the managed launcher still ran
1.29 (managed runs on 1.30.164200 are recorded from 2026-10-26, below). This
is not a way to offload simulation: dummies and roboclients alike run under server
authority.

## Action injection vs 1.30 SP pending

MCP `action_use` / `PerformActionStart` in singleplayer now no-ops if
pending/current is set (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804-814`). Continuous actions
already do not complete via MCP (see `actions-ui-and-inventory.md`). Instant
actions: if a second inject returns `setup_failed` / no-op, wait for
`GetActionState()` to leave `UA_AM_INIT`. Detail:
`skills/dayz-test-ingame/references/dayz-1-30-test-ingame.md`.

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

