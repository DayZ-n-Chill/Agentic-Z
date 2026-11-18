# RPC and input patterns

How shipped mods number their RPCs, keep a client action responsive while the server decides, send to every client, cache input lookups, and skip client-only work on a dedicated server. RPC routing and server checks are in `rpc-routing.md`; synced variables in `networking.md`.

## RPC numbers grouped by direction

```c
enum MyMod_RPCserver { RPC_DO_FIRE = 937081 };   // client to server
enum MyMod_RPCclient { RPC_SYNC_FX = 937091 };   // server to client

override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);
    if (GetGame().IsServer() && rpc_type == MyMod_RPCserver.RPC_DO_FIRE)
    {
        Param1<bool> p;
        if (ctx.Read(p) && p.param1)
            DoServerAction();
    }
    if (rpc_type == MyMod_RPCclient.RPC_SYNC_FX && !GetGame().IsServer())
    {
        Param3<Object, ImpactEffectsData, vector> fx;
        if (ctx.Read(fx))
            PlayClientEffect(fx);
    }
}
```

A high fixed number in a block unique to the mod keeps clear of vanilla's low numbers and other mods (a community convention; see `rpc-routing.md`, section "RPC IDs"). One enum per direction makes the flow of each RPC obvious. `IsServer()` is safe inside `OnRPC`; the load time caveat in `hard-rules.md`, section "Networking and sides", applies only during init.

## Client locks, server decides

For a weapon or action where the server must decide but the player needs instant feedback, send the request and lock the client at once, without waiting for a reply:

```c
override void EOnPostSimulate(IEntity other, float timeSlice)
{
    super.EOnPostSimulate(other, timeSlice);
    if (!IsLocalPilot())
        return;
    Input inp = GetGame().GetInput();
    if (!inp || !m_CanAct || !inp.LocalHold("UAMyModAction"))
        return;
    GetGame().RPCSingleParam(this, MyMod_RPCserver.RPC_DO_FIRE, new Param1<bool>(true), true);
    m_CanAct = false;
    GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ActionReady, ACTION_TIMEOUT_MS, false);
}
```

The cooldown re-arms the client even if the server's answer is lost. On the server, `OnRPC` validates the request, changes the world and broadcasts the effect.

## Sending to every client

`RPCSingleParam(Object target, int rpc_type, Param param, bool guaranteed, PlayerIdentity recipient = null)` (`P:\scripts\3_game\global\game.c:1013`) sent from the server with a null recipient reaches every client (see `rpc-routing.md`, section "Sending"). The fourth argument, `true`, makes it reliable.

Loop over the players only when some of them should receive it, and reuse the array:

```c
m_PlayerCache.Clear();
GetGame().GetPlayers(m_PlayerCache);
foreach (Man man : m_PlayerCache)
{
    if (MyMod_ShouldReceive(man))
        GetGame().RPCSingleParam(this, MyMod_RPCclient.RPC_SYNC_FX, new Param1<int>(m_State), true, man.GetIdentity());
}
```

## Cache input lookups

`GetUApi().GetInputByName` is a lookup by string. Resolve each input once and keep the reference:

```c
protected UAInput m_InputFire;

override void OnInput(float dt)
{
    if (!m_InputFire)
        m_InputFire = GetUApi().GetInputByName("UAMyModFire");
    if (m_InputFire.LocalPress())
        DoFire();
}
```

The same applies to any hot path that looks something up by string.

## Skip client-only work on a dedicated server

A dedicated server renders nothing, so particles, lights and sounds need not exist there:

```c
protected void InitClientEffects()
{
    if (m_Initialized)
        return;
    if (!GetGame().IsClient() && GetGame().IsMultiplayer())
        return;   // multiplayer server
    // create effects, lights and sounds
    m_Initialized = true;
}
```

In single player `IsClient()` is true, so nothing is skipped; on a multiplayer server the check returns early. Call the guard lazily, on the first tick or event, never from a constructor or load time init: during load `IsClient()` is not reliable on the client (`hard-rules.md`, section "Networking and sides"). `IsMultiplayer()` and `IsClient()` are declared on `CGame` (`P:\scripts\3_game\global\game.c:1118` and `:1119`).
