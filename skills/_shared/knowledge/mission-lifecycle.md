# Mission lifecycle: bootstrap order and the exact `super` chain

Status: source reading of build `119356`. Checked on `P:\` on 2026-11-17: every cited line below was opened on `P:\scripts` and holds what the note says, and the persistence counts (135, 148, 0 and the two `RegisterPersistentObject` hits) were recounted there. The `[EXACT][CLAIM-...]` tags are claim IDs in `scripts/dev/knowledge-pack/sources/claims.json`.

Most mission bugs that look like engine caprice are order bugs: code that runs before the object it touches exists, a `super` call placed where vanilla does not place it, or a second `OnInit` pass a modder did not know could happen. This note is the script-side map for build `119356`: which mission entry points exist, what each one calls first and last, and which guards decide whether the body runs at all. It covers only what the scripts show; the native calls that create the mission and invoke these entry points are not in the script tree (see Limits).

The class spine, root first, is `Mission` → `MissionBaseWorld` → `MissionBase` → `MissionServer` / `MissionGameplay` (`P:\scripts\3_game\gameplay.c:685`; `P:\scripts\4_world\classes\missionbaseworld.c:1`; `P:\scripts\5_mission\mission\missionbase.c:1`; `P:\scripts\5_mission\mission\missionserver.c:5`; `P:\scripts\5_mission\mission\missiongameplay.c:1`).

## The order

Script-visible order, per side. The constructor is the first script code of the mission object; `OnInit`, `OnMissionStart` and `OnUpdate` follow as separate engine-invoked entry points.

| Step | Server | Client |
|---|---|---|
| Construct | `MissionServer()` after `MissionBase()` | `MissionGameplay()` after `MissionBase()` |
| Initialise | `MissionServer.OnInit()` | `MissionGameplay.OnInit()` |
| Start | `MissionServer.OnMissionStart()` | `MissionGameplay.OnMissionStart()` |
| Tick | `MissionServer.OnUpdate(timeslice)` | `MissionGameplay.OnUpdate(timeslice)` |

Two asymmetries in that table do real damage when assumed away: the server `OnUpdate` calls `super` **last**, the base `OnUpdate` calls it **first**; and `MissionGameplay.OnMissionStart` does not call `super` at all, while `MissionServer.OnMissionStart` does. Both are spelled out below.

## MissionBase and MissionServer

The `MissionBase` constructor (`P:\scripts\5_mission\mission\missionbase.c:17`) calls `InitialiseWorldData()` at `:30`, and `InitialiseWorldData` (`:107`) assigns `m_WorldData = new ChernarusPlusData()` for `chernarusplus` at `:116` and again as the default branch at `:148`; the constructor therefore runs before any `OnInit`, and a custom mission must not assume world data is absent at `OnInit`. [EXACT][CLAIM-MISSION-BASE-CONSTRUCTOR]

`MissionServer.OnInit` (`P:\scripts\5_mission\mission\missionserver.c:85`) calls `super.OnInit()` at `:87` and then the server data loads: `CfgGameplayHandler.LoadData()` (`:88`), `PlayerSpawnHandler.LoadData()` (`:89`), `CfgPlayerRestrictedAreaHandler.LoadData()` (`:90`), `UndergroundAreaLoader.SpawnAllTriggerCarriers()` (`:91`) and `CfgBunkerBroadcastHandler.LoadData()` (`:95`); the chain bottoms out in `Mission.OnInit`, which is empty (`P:\scripts\3_game\gameplay.c:700`), and the rain handler is not created here but in the `MissionServer` constructor (`P:\scripts\5_mission\mission\missionserver.c:66`), which assigns `m_RainProcHandler = new RainProcurementHandler(this)` at `:76`. [EXACT][CLAIM-MISSION-SERVER-ONINIT]

`MissionServer.OnUpdate` (`P:\scripts\5_mission\mission\missionserver.c:108`) runs its own systems first — dummy scheduler, tick scheduler, logout players, base-environment temperature — calls `m_RainProcHandler.Update(timeslice)` at `:124`, and only then calls `super.OnUpdate(timeslice)` at `:129`; below it, `MissionBase.OnUpdate` (`P:\scripts\5_mission\mission\missionbase.c:85`) calls `super.OnUpdate(timeslice)` first, at `:87`, and `Mission.OnUpdate` (`P:\scripts\3_game\gameplay.c:703-708`) only advances the cursor timestamp under `FEATURE_CURSOR`; the rain handler is a `MissionServer` member (`P:\scripts\5_mission\mission\missionserver.c:11`), returned by its `GetRainProcurementHandler` override at `:835-837`, while `MissionBaseWorld.GetRainProcurementHandler` (`P:\scripts\4_world\classes\missionbaseworld.c:3-6`) returns `null`, so a custom `MissionBase` that is not a `MissionServer` has no rain handler. [EXACT][CLAIM-MISSION-SERVER-UPDATE]

## MissionGameplay

`MissionGameplay.OnInit` (`P:\scripts\5_mission\mission\missiongameplay.c:102`) calls `super.OnInit()` at `:104`, then returns at once if `m_Initialized` is set (`:106-109`) — the flag its constructor clears at `:67` — then, under `DIAG_DEVELOPER` on a non-multiplayer session only, loads gameplay, underground and bunker-broadcast data (`:115-117`), calls `PPEffects.Init()` at `:122` (marked deprecated in the source), `MapMarkerTypes.Init()` at `:123`, takes the UI manager at `:125`, sets `m_Initialized = true` at `:127`, and creates the HUD from `gui/layouts/day_z_hud.layout` at `:132`. [EXACT][CLAIM-MISSION-GAMEPLAY-ONINIT]

That guard is the whole override recipe for the client:

- A second `OnInit` on the same mission object returns after the `super` call and re-creates nothing. That is the designed re-entry path.
- A modded override that sets `m_Initialized = true` **before** calling `super.OnInit()` makes the vanilla body skip itself: no HUD layout, no chat or action-menu wiring from this method. That is a deliberate replacement of the base UI, not a shortcut — do it only if the mod creates everything `:130-167` creates.
- Leaving the flag alone and calling `super.OnInit()` first is the normal case: the base UI exists before any mod line runs.

`MissionGameplay.OnMissionStart` (`P:\scripts\5_mission\mission\missiongameplay.c:193`) does **not** call `super.OnMissionStart()`: its body starts with `g_Game.SetConnecting(false)` at `:195`, hides the UI cursor at `:199`, sets the mission state to game at `:202`, and its `EffectAreaLoader` zone/bunker block at `:209-211` sits inside the `DIAG_DEVELOPER` / `!IsMultiplayer` guard at `:204-214`; by contrast, `MissionServer.OnMissionStart` (`P:\scripts\5_mission\mission\missionserver.c:99`) calls `super.OnMissionStart()` at `:101` and then `EffectAreaLoader.CreateZones()` at `:104` unconditionally, and `Mission.OnMissionStart` (`P:\scripts\3_game\gameplay.c:701`) is empty. [EXACT][CLAIM-MISSION-GAMEPLAY-ONMISSIONSTART]

Two traps follow. Adding `super.OnMissionStart()` to a modded `MissionGameplay` override does not call an empty base: it runs the vanilla `MissionGameplay.OnMissionStart` body above (`SetConnecting`, cursor, mission state, and the developer-only zone block), so omitting it skips the client bootstrap and cuts the chain of other mods. The vanilla `MissionGameplay.OnMissionStart` itself does not call `super`, so the empty `Mission.OnMissionStart` is not reached on the client; the server override, by contrast, calls `super` and then `CreateZones()`. And the client zone creation a modder sees in a developer single-player session is not the multiplayer path: on a real client those zones arrive from the server, whose `CreateZones()` is not guarded.

## RPC routing

`DayZGame.OnRPC` (`P:\scripts\3_game\dayzgame.c:3141`) calls `super.OnRPC(sender, target, rpc_type, ctx)` at `:3143`, fires its RPC event invoker at `:3144`, and, when a target object exists, calls `target.OnRPC(sender, rpc_type, ctx)` at `:3151`; with no target it switches on the RPC type, and the gameplay-config case calls `CfgGameplayHandler.OnRPC(null, ctx)` at `:3161`, a separate static handler declared at `P:\scripts\3_game\cfggameplayhandler.c:102`. [EXACT][CLAIM-MISSION-RPC-ROUTING]

So there are three distinct places an RPC can land, and they are not interchangeable: the game object itself, the target object's own `OnRPC`, and — only for the named config-sync types and only with no target — a static config handler. A custom `OnRPC` override that does not call `super.OnRPC` for IDs it does not recognise cuts the chain below it; handle the IDs the mod owns, then pass the rest through.

## Persistence hooks

The persistence pack (`skills/_shared/persistence/`) and the `dayz-persistence` skill already own the stream contract (field order, version, failed-read behaviour); this section only fixes what exists in this build. Counting every occurrence in the `.c` files under `scripts/` gives 135 `OnStoreSave` and 148 `OnStoreLoad`; `RegisterPersistent` does not occur, and the only `RegisterPersistent*` symbol is `RegisterPersistentObject` in `P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:18,26`; the per-entity pair is `EntityAI.OnStoreSave` at `P:\scripts\3_game\entities\entityai.c:2910` and `EntityAI.OnStoreLoad` at `:2978`. [EXACT][CLAIM-MISSION-PERSISTENCE-HOOKS]

A mod that goes looking for a registration call is looking for something the build does not have: persistence is the override pair above, called by the engine per entity, and nothing registers an entity for it in script.

## What this changes

For a modded mission in this build, in order:

1. Construction already happened — world data included — before any `OnInit` line runs. Put nothing in `OnInit` whose job is to "beat" the world-data creation.
2. Server `OnInit`: call `super.OnInit()` first, then add work; the vanilla loads follow the call in the same body, so mod code in an override runs after them only if it also runs after its own `super` call returns.
3. Client `OnInit`: call `super.OnInit()` first for the base UI, or set `m_Initialized` before it to replace that UI wholesale — never set the flag by accident in a constructor or a helper the constructor calls, because the skip is silent.
4. `OnMissionStart`: the server override keeps `super` first; the gameplay override must also call `super` to run the vanilla client body above, even though that vanilla body does not itself call `super` and the empty `Mission.OnMissionStart` is not reached.
5. `OnUpdate`: pick the side of `super` deliberately per level — the server body finishes with it, the base body starts with it.
6. `OnRPC`: own specific IDs, pass everything else to `super`.

## How to reproduce

From the root of the extracted build-119356 script tree:

```text
grep -n "InitialiseWorldData\|void MissionBase()" scripts/5_mission/mission/missionbase.c
grep -n "super.OnInit\|super.OnMissionStart\|super.OnUpdate\|m_RainProcHandler" scripts/5_mission/mission/missionserver.c
grep -n "m_Initialized\|PPEffects.Init\|MapMarkerTypes.Init\|day_z_hud" scripts/5_mission/mission/missiongameplay.c
grep -n "target.OnRPC\|CfgGameplayHandler.OnRPC" scripts/3_game/dayzgame.c
grep -R -E '\bOnStoreSave\b' --include='*.c' scripts | wc -l    # 135
grep -R -E '\bOnStoreLoad\b' --include='*.c' scripts | wc -l    # 148
grep -R -E '\bRegisterPersistent\b' --include='*.c' scripts | wc -l    # 0
grep -R -n -E '\bRegisterPersistentObject\b' --include='*.c' scripts   # 2 hits
```

The last four commands reproduce the figures in the persistence section: 135 and 148 occurrences, zero exact `RegisterPersistent`, and the two `RegisterPersistentObject` hits.

## Limits

- Build `119356` only. Line numbers, the guard placement and the empty base bodies are this build's; re-verify before citing them on another.
- The script-visible order above is exact; the native dispatch that creates the mission object and invokes `OnInit`, `OnMissionStart` and `OnUpdate` is not in the scripts, so nothing here says when the engine calls them relative to world or player creation.
- No runtime verification: this is source reading, not an in-game test, and no statement here claims measured in-game behaviour.
- No vanilla code is copied into this note; it paraphrases and cites `scripts/...` locations only.
