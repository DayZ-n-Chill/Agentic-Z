# Pattern: RPC (Remote Procedure Calls)

DayZ has two RPC APIs: the legacy `GetGame().RPC` / `GetGame().RPCSingleParam` and the cleaner `ScriptRPC` builder. Both deliver messages that are received in `OnRPC()` overrides on the target entity.

---

## Custom RPC ID Enum

Always claim a private ID range. Vanilla uses 0–~200; community mods use high ranges.

```c
// Scripts/3_Game/MyMod_ERPCs.c
enum MyMod_ERPCs
{
    // Range 20000–20099 owned by MyMod — document in README
    RPC_NOTIFICATION     = 20000,
    RPC_SYNC_DATA        = 20001,
    RPC_CLIENT_TO_SERVER = 20002,
}
```

---

## 1. RPCSingleParam — Simplest Path

One `Param` wrapper, sent to a specific player or null-broadcast.

```c
// Server → specific client
void SendNotification(PlayerBase player, string msg)
{
    if (!GetGame().IsServer())
        return;

    GetGame().RPCSingleParam(
        player,                          // target entity (OnRPC fires here)
        MyMod_ERPCs.RPC_NOTIFICATION,    // RPC type
        new Param1<string>(msg),         // payload
        true,                            // guaranteed (TCP-like)
        player.GetIdentity()             // recipient; null = all clients
    );
}
```

---

## 2. GetGame().RPC — Broadcast all Clients

```c
// Server → all clients (null recipient)
void BroadcastAlert(string msg)
{
    array<ref Param> params = new array<ref Param>;
    params.Insert(new Param1<string>(msg));
    GetGame().RPC(null, MyMod_ERPCs.RPC_NOTIFICATION, params, true);
}
```

---

## 3. ScriptRPC — Multi-Field Payload

Avoids `Param8` nesting for complex payloads.

```c
// Send
void SendSyncData(PlayerBase player, string key, int val, float factor)
{
    if (!GetGame().IsServer())
        return;
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(key);
    rpc.Write(val);
    rpc.Write(factor);
    rpc.Send(player, MyMod_ERPCs.RPC_SYNC_DATA, true, player.GetIdentity());
}

// Receive — field order MUST match write order
override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);
    if (rpc_type == MyMod_ERPCs.RPC_SYNC_DATA)
    {
        string key;
        int    val;
        float  factor;
        if (!ctx.Read(key))    return;
        if (!ctx.Read(val))    return;
        if (!ctx.Read(factor)) return;
        // apply data...
    }
}
```

---

## 4. Client → Server RPC

Clients can send RPCs up by calling on their own entity with a `null` recipient.

```c
// Called on local client
void ClientRequestRespawn(PlayerBase localPlayer)
{
    if (GetGame().IsServer())
        return;

    GetGame().RPCSingleParam(
        localPlayer,
        MyMod_ERPCs.RPC_CLIENT_TO_SERVER,
        new Param1<int>(1),
        true,
        null   // server-only delivery
    );
}

// Server receives it in PlayerBase.OnRPC
case MyMod_ERPCs.RPC_CLIENT_TO_SERVER:
{
    if (!GetGame().IsServer())
        break;
    // ALWAYS validate server-side — never trust client input
    break;
}
```

---

## 5. OnRPC Override Template

```c
modded class PlayerBase
{
    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        super.OnRPC(sender, rpc_type, ctx); // MUST call super first

        switch (rpc_type)
        {
            #ifndef SERVER
            // Client-only cases
            case MyMod_ERPCs.RPC_NOTIFICATION:
            {
                Param1<string> p = new Param1<string>("");
                if (ctx.Read(p))
                    MessageAction(p.param1);
                break;
            }
            #endif

            // Server-only cases (no preprocessor guard needed)
            case MyMod_ERPCs.RPC_CLIENT_TO_SERVER:
            {
                if (!GetGame().IsServer()) break;
                // handle...
                break;
            }
        }
    }
}
```

---

## Rules

| Rule | Detail |
|---|---|
| Always call `super.OnRPC` first | Vanilla and other mods process their own cases there |
| Use `#ifndef SERVER` for client cases | Avoids server executing client-only code |
| Read order = write order | Mismatched reads produce garbled data or crashes |
| `guaranteed = true` for game logic | `false` (unreliable) only for cosmetic/high-frequency updates |
| Validate ALL client-sent RPCs server-side | Never trust input from clients |
| Cap RPC frequency | Don't fire `ScriptRPC` every frame. Cache and send on change |
