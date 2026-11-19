# Modded classes and defines

How a `modded class` adds to a vanilla class safely, which vanilla methods it must call `super` on, where its declaration must live, and how to gate code on another mod or on diag builds. The 1.30 changes are in `dayz-1-30-enforce-script.md`.

## What a modded class may do

```c
modded class PlayerBase
{
    int m_MyMod_PowerDraw;

    override void OnConnect()
    {
        super.OnConnect();
    }

    void MyMod_Helper() { }
}
```

- A `modded class` adds fields as well as methods and overrides. Vanilla's own modding example adds a `static const int` to `modded class ParticleList` (`P:\scripts\3_game\particles\particlelist.c:5`).
- Prefix every member you add, `m_MyMod_PowerDraw` and not `m_PowerDraw`, so it cannot collide with another mod that mods the same class.
- Two `modded class` declarations of one class can live in different files.
- Call `super` in overrides to keep vanilla behaviour.

## `super` is required on these

- `MissionServer.OnGameplayDataHandlerLoad` sets `m_RespawnMode` and the debug monitor and calls `InitialiseWorldData()` (`P:\scripts\5_mission\mission\missionserver.c:161` to `:167`); without `super`, world data silently breaks.
- `MissionServer.OnClientPrepareEvent` decides `useDB` from `GetHive()` (`:449` to `:463`); without `super`, character loading breaks.

## Where to spawn at startup

Spawn where vanilla spawns the same kind of object. Vanilla's spawn that waits for the central economy lives in `GlobalsInit()` (`P:\scripts\3_game\dayzgame.c:1158`): it reads the economy globals under `if (GetCEApi())` (`:1160`), then calls `ObjectSpawnerHandler.OnGameplayDataHandlerLoad()` (`:1174`) under the comment "CE being initialized before spawning them" (`:1173`). `GlobalsInit` is queued on its own with `GetCallQueue(CALL_CATEGORY_GAMEPLAY).Call(GlobalsInit)` (`:1096`). The mission hook runs much earlier: `MissionServer.OnInit` (from `:85`) calls `CfgGameplayHandler.LoadData()` at `P:\scripts\5_mission\mission\missionserver.c:88`, so those `GlobalsInit` lines do not justify spawning from `OnGameplayDataHandlerLoad`.

Spawning early is still right for objects that do not touch the economy: vanilla spawns the underground trigger carriers in `OnInit` (`UndergroundAreaLoader.SpawnAllTriggerCarriers`, `missionserver.c:91`). Items with an economy lifetime go through the object spawner route.

## The declaration lives in the class's own module

A `modded class X` must compile in the same script module that defines `X`; using `X` from a higher module is not enough. `PPERequesterBank` is defined in `3_Game` (`P:\scripts\3_game\ppemanager\pperequesterbank.c:4`). Referring to it from `4_World` compiles, but declaring `modded class PPERequesterBank` under `Scripts/4_World/` is reported to fail with `Unknown type 'PPERequesterBank'` and kill the World module. Put it under `Scripts/3_Game/<Mod>/`.

Never hide such a declaration with `#ifndef SERVER`: the server compile then passes only because it skips the code, while the client still compiles it and fails. Compile both the dedicated server and the client views before release, since a server-only check misses code under `#ifndef SERVER` and a client-only check misses `#ifdef SERVER`.

## Detecting another mod

```c
#ifdef EXPANSION
// compiled only when the define exists
#endif

bool hasHardline = GetGame().ConfigIsExisting("CfgPatches ExpansionHardline");   // checked at runtime
```

Reported, not checked on `P:\`: since DayZ 1.26 `CfgMods` defines `#define <ModClassName>` for every mod, plus anything in its `defines[]`:

```cpp
class CfgMods
{
    class MyMod
    {
        defines[] = { "MYMOD", "MYMOD_FEATURE_X" };
    };
};
```

These defines reach other mods' code. A `#define X` written inside the target mod's own script, such as `scripts/Common/Define.c`, is visible only in that mod's files, even with the same name, so an `#ifdef X` in your mod quietly compiles to nothing and your `modded class` never runs. Gate on a name from the target PBO's `CfgPatches` or `CfgMods.defines[]`. Reported for mods; it cannot be checked on `P:\`.

## `DEVELOPER` is not `DIAG_DEVELOPER`

Some vanilla APIs sit under `#ifdef DEVELOPER`, for example `DayZPlayerSyncJunctures.SendGetInVehicle` with `SJ_DEBUG_GET_IN_VEHICLE` and much of `plugindeveloper.c`. The standard diag executable defines `DIAG_DEVELOPER` but not `DEVELOPER`. Calling a `DEVELOPER`-only symbol from your mod breaks the whole PBO's compile; the log shows only that the PBO or its addons did not load (measured in a mod). A working `OnDebugSpawn` (under `DIAG_DEVELOPER`) proves nothing about `DEVELOPER`. Read the `defines:` line of the server's and the client's `script_*.log` before relying on any `#ifdef` API.

## Type names

`GetType()` returns the config class name, through `g_Game.ObjectGetType(this, ret)` (`P:\scripts\3_game\entities\object.c:467`); `ClassName()` returns the script class name. They differ when the script class has no matching config class. Use `GetType()` for entities, as vanilla does for hidden selections (`GetHiddenSelections`, `object.c:128`, `:134`, `:140`) and animation config paths (`HasAnimation`, `:424`, `:430`, `:436`).

## `[Obsolete]` and `notnull`

`[Obsolete("Use GizmoApi.GetCount")]` above `proto native int GizmoGetCount();` makes Workbench warn at every call (`P:\scripts\3_game\global\game.c:802`, `:808`, `:814`; also `P:\scripts\3_game\enums\ecrewmemberstate.c:1`). Mark an API obsolete before removing it, so dependent mods get a warning first.

`notnull` on a parameter says the caller has already checked it, as in `AddLocation(notnull BenchmarkLocation loc)` (`P:\scripts\5_mission\mission\missionbenchmark.c:54`). Check for null where you know how to handle it, then pass the value on as `notnull`.

## `EXTrace` comes with Expansion and Community Framework

`auto trace = EXTrace.Start(EXTrace.GENERAL, this, "MethodName");` is a low-cost trace that needs no `#ifdef` and does nothing when tracing is off. It replaces the older `CF_Trace_0` form that needed `#ifdef EXPANSIONTRACE`. It is not vanilla: nothing under `P:\scripts` names `EXTrace`, so on servers without Expansion or Community Framework use `Print()` or your own logger. The Expansion and Community Framework side is not checked here.
