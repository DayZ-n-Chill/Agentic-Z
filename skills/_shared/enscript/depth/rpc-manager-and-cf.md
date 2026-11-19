# One-ID RPC dispatch and Community Framework

How the common third-party pattern sends every RPC on one ID with a function name for dispatch, what it costs, and how Community Framework modules receive events and dispatch RPCs in single player. Routing and server checks are in `rpc-routing.md`.

## One ID and a function name

Instead of a growing enum of RPC IDs, register one high fixed ID on `DayZGame.Event_OnRPC` and dispatch on a function name sent as the first parameter. A new networked call is then just a method whose name matches the string. This "RPCManager" pattern is third-party mod code, not vanilla; `Event_OnRPC` itself is declared at `P:\scripts\3_game\dayzgame.c:991`.

```c
protected const int MYMOD_RPC_ID = 1004258;   // one high, unlikely to collide

class MyMod_RPCManager
{
    protected Class m_Handlers;

    void MyMod_RPCManager()  { GetDayZGame().Event_OnRPC.Insert(OnRPC); }
    void ~MyMod_RPCManager() { GetDayZGame().Event_OnRPC.Remove(OnRPC); }
    void RegisterHandlers(Class instance) { m_Handlers = instance; }

    void OnRPC(PlayerIdentity sender, Object target, int rpc_type, ParamsReadContext ctx)
    {
        if (rpc_type != MYMOD_RPC_ID)
            return;
        Param1<string> fn = new Param1<string>("");
        if (!ctx.Read(fn))
            return;
        auto callData = new Param3<ParamsReadContext, PlayerIdentity, Object>(ctx, sender, target);
        GetGame().GameScript.CallFunctionParams(m_Handlers, fn.param1, NULL, callData);
    }

    void SendRPC(array<ref Param> params, bool guaranteed = false, PlayerIdentity toIdentity = NULL, Object toTarget = NULL)
    {
        GetGame().RPC(toTarget, MYMOD_RPC_ID, params, guaranteed, toIdentity);
    }
}
```

The sender puts the function name first, then the payload:

```c
array<ref Param> p = new array<ref Param>;
p.Insert(new Param1<string>("MyMod_SeatChanged_Client"));
p.Insert(new Param2<PlayerBase, int>(player, seatIdx));
g_MyMod_RPC.SendRPC(p, true, identity);
```

The handler is a method on the registered instance, for example a `modded MissionGameplay` that called `RegisterHandlers(this)` in its constructor:

```c
void MyMod_SeatChanged_Client(ParamsReadContext ctx, PlayerIdentity sender, Object target)
{
    Param2<PlayerBase, int> data = new Param2<PlayerBase, int>(NULL, 0);
    if (!ctx.Read(data))
        return;
}
```

The pattern filters its ID before the first read, which keeps it safe on the shared bus (`rpc-routing.md`, section "Reading `Event_OnRPC` safely").

What it costs:

- `CallFunctionParams` dispatches on a string, so a typo silently does nothing and no compiler checks the name.
- The one ID can still collide when two mods pick the same number; pick a random high one.
- Nothing checks side or authority. Each handler checks `GetGame().IsServer()` and validates the sender, a `*_Server` method never trusts entities a client supplied, and an unknown or bad payload fails closed.

Shipped copies of this pattern often put `ref` on parameters and write `new ref`; never copy that (`memory-management.md`).

## Community Framework modules

Read in the Community Framework source at version 1.5.8, under its `JM/CF/Scripts/` folder; not measured in game and not checked against the CF copy on `P:\`. `../integrations/community_framework.md` holds what was checked in the CF PBO.

- Register a module with the attribute `[CF_RegisterModule(MyMod_Module)]` above its class; the attribute's constructor adds the type to the module manager (`1_Core/CommunityFramework/Module/CF_RegisterModule.c:1` to `:6`, used at `4_World/CommunityFramework/ModStorage/CF_ModStorageModule.c:6`).
- Every event handler takes `(Class sender, CF_EventArgs args)` and fires only after its `Enable...()` call in `OnInit()`. `CF_ModuleCore` (`1_Core/CommunityFramework/Module/CF_ModuleCore.c:76` to `:238`) offers `OnMissionStart`, `OnMissionFinish`, `OnMissionLoaded`, `OnUpdate`, `OnSettingsChanged`, `OnPermissionsChanged`, `OnWorldCleanup`, the `OnMPSession*` and `OnMPConnect*` events, `OnRespawn`, `OnLoginTime`, `OnLoginStatus`, `OnLogout` and `OnChat`.
- `OnUpdate` receives a `CF_EventUpdateArgs`; cast it and read `DeltaTime` (`1_Core/CommunityFramework/EventArgs/CF_EventUpdateArgs.c:1` to `:7`). The mission reuses one instance (`5_Mission/CommunityFramework/Mission/MissionBase.c:7`), so never store it.
- `CF_ModuleWorld` adds the server side client lifecycle (`4_World/CommunityFramework/Module/CF_ModuleWorld.c:3` to `:101`): `OnInvokeConnect`, `OnInvokeDisconnect`, `OnClientNew`, `OnClientRespawn`, `OnClientReady`, `OnClientPrepare`, `OnClientReconnect`, `OnClientLogout`, `OnClientDisconnect` (the player has left; no reconnect follows) and `OnClientLogoutCancelled`, each with its `Enable...()`.

## Community Framework RPCs in single player

`SingleplayerExecutionType` matters only when one process is both server and client, offline. There `Server` runs the handler once as the server call, `Client` once as the client call, and `Both` runs it twice, server first. In multiplayer the value is ignored: the server and clients each handle their own side (`3_Game/CommunityFramework/RPC/RPCManager.c:8` to `:13`, `:89` to `:98`). `SendRPCs` does not support `Both` and logs a warning (`:142`, `:162` to `:164`).
