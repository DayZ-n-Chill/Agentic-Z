# Reference: mission lifecycle and the `super` chain

The order in which `MissionServer` and `MissionGameplay` run their constructor, `OnInit`, `OnMissionStart` and `OnUpdate`, where each calls `super`, and how an RPC with no target is routed. Every line below was opened on `P:\scripts`. This is source reading: the native code that creates the mission and calls these entry points is not in the scripts, so nothing here says when the engine calls them relative to world or player creation.

The class chain, root first: `Mission` (`P:\scripts\3_game\gameplay.c:685`), `MissionBaseWorld` (`P:\scripts\4_world\classes\missionbaseworld.c:1`), `MissionBase` (`P:\scripts\5_mission\mission\missionbase.c:1`), then `MissionServer` (`P:\scripts\5_mission\mission\missionserver.c:5`) and `MissionGameplay` (`P:\scripts\5_mission\mission\missiongameplay.c:1`). Mod these in `5_Mission` (`patterns/modded_class.md`).

## The order

| Step | Server | Client |
|---|---|---|
| Construct | `MissionServer()` after `MissionBase()` | `MissionGameplay()` after `MissionBase()` |
| Initialise | `MissionServer.OnInit()` | `MissionGameplay.OnInit()` |
| Start | `MissionServer.OnMissionStart()` | `MissionGameplay.OnMissionStart()` |
| Tick | `MissionServer.OnUpdate(timeslice)` | `MissionGameplay.OnUpdate(timeslice)` |

Two asymmetries cause most mission bugs: the server `OnUpdate` calls `super` last while the base `OnUpdate` calls it first, and `MissionGameplay.OnMissionStart` does not call `super` while `MissionServer.OnMissionStart` does.

## Constructor and world data

The `MissionBase` constructor (`P:\scripts\5_mission\mission\missionbase.c:17`) calls `InitialiseWorldData()` at `:30`, which assigns `m_WorldData` (`ChernarusPlusData` for `chernarusplus` at `:116`, and as the default branch at `:148`). World data therefore exists before any `OnInit` line runs.

The `MissionServer` constructor (`P:\scripts\5_mission\mission\missionserver.c:66`) creates the rain handler at `:76`. `MissionServer.GetRainProcurementHandler` returns it (`:835-837`); `MissionBaseWorld.GetRainProcurementHandler` returns `null` (`P:\scripts\4_world\classes\missionbaseworld.c:3-6`), so a custom mission that is not a `MissionServer` has no rain handler.

## Server

- `MissionServer.OnInit` (`P:\scripts\5_mission\mission\missionserver.c:85`) calls `super.OnInit()` at `:87`, then loads the server data: `CfgGameplayHandler.LoadData()` (`:88`), `PlayerSpawnHandler.LoadData()` (`:89`), `CfgPlayerRestrictedAreaHandler.LoadData()` (`:90`), `UndergroundAreaLoader.SpawnAllTriggerCarriers()` (`:91`) and `CfgBunkerBroadcastHandler.LoadData()` (`:95`). `Mission.OnInit` is empty (`P:\scripts\3_game\gameplay.c:700`). Code a mod puts after its own `super.OnInit()` runs after these loads.
- `MissionServer.OnMissionStart` (`:99`) calls `super.OnMissionStart()` at `:101`, then `EffectAreaLoader.CreateZones()` at `:104` with no guard. `Mission.OnMissionStart` is empty (`P:\scripts\3_game\gameplay.c:701`).
- `MissionServer.OnUpdate` (`:108`) runs its own systems first (schedulers, logout, base temperature, the rain handler at `:124`) and calls `super.OnUpdate(timeslice)` last, at `:129`. Below it, `MissionBase.OnUpdate` (`P:\scripts\5_mission\mission\missionbase.c:85`) calls `super` first, at `:87`.

## Client

`MissionGameplay.OnInit` (`P:\scripts\5_mission\mission\missiongameplay.c:102`) calls `super.OnInit()` at `:104`, then returns at once when `m_Initialized` is set (`:106-109`). The constructor clears the flag (`:67`). After the guard it sets `m_Initialized = true` (`:127`) and creates the HUD from `gui/layouts/day_z_hud.layout` (`:132`).

- A second `OnInit` on the same mission object returns after `super` and creates nothing again.
- A modded override that sets `m_Initialized = true` before calling `super.OnInit()` skips the whole vanilla body: no HUD, no chat or action menu wiring. Do that only to replace the base UI, and then create everything `:130-167` creates. Never set the flag by accident in a constructor or a helper it calls; the skip is silent.

`MissionGameplay.OnMissionStart` (`:193`) does not call `super`. It calls `g_Game.SetConnecting(false)` (`:195`), hides the cursor (`:199`), sets the mission state (`:202`), and creates effect areas only inside a `DIAG_DEVELOPER` and not multiplayer guard (`:204-214`). So a modded `MissionGameplay.OnMissionStart` must call `super.OnMissionStart()`: that runs this vanilla body, and leaving it out skips the client start and cuts the chain for other mods. On a real client the zones come from the server, whose `CreateZones()` is not guarded.

## RPC routing

`DayZGame.OnRPC` (`P:\scripts\3_game\dayzgame.c:3141`) calls `super.OnRPC` (`:3143`), fires its RPC invoker (`:3144`) and, when there is a target, calls `target.OnRPC` (`:3151`). With no target it switches on the type; the gameplay config case calls the static `CfgGameplayHandler.OnRPC(null, ctx)` (`:3161`, declared at `P:\scripts\3_game\cfggameplayhandler.c:102`). An `OnRPC` override handles the IDs its mod owns and passes every other ID to `super`. The handler template is in `patterns/rpc.md`.

## Rules for a modded mission

1. Do not try to run before world data creation in `OnInit`; the constructor already did it.
2. Server `OnInit` and `OnMissionStart`: call `super` first, then add work.
3. Client `OnInit`: call `super` first for the base UI, or set `m_Initialized` before it only to replace that UI.
4. Client `OnMissionStart`: call `super`, even though the vanilla body does not.
5. `OnUpdate`: choose the side of `super` on purpose; vanilla differs per level.
6. `OnRPC`: own your IDs, pass the rest to `super`.

A worked `MissionServer` override is `examples/05_mission_server.c`.
