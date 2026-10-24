# Community Framework (CF) Integration

[DayZ-CommunityFramework](https://github.com/Arkensor/DayZ-CommunityFramework) is a widely used mod compatibility layer. It provides a module event bus, per-entity mod storage, and an RPC manager.

CF is not vanilla, so its classes are not under `P:\scripts\`. Every name below was checked in the shipped CF scripts PBO, `P:\Mods\@CF\Addons\scripts.pbo`; a source line gives the file inside that PBO (for example `4_World\CommunityFramework\Module\CF_ModuleWorld.c:3`). Recheck after a CF update.

## Contents

- [Module System](#module-system)
- [CF ModStorage: Per-Entity Persistent Data](#cf-modstorage-per-entity-persistent-data)
- [CF RPCManager](#cf-rpcmanager)
- [Events between mods](#events-between-mods)

---

## Module System

Modules are the core CF pattern. Each mod registers one or more `CF_ModuleWorld` subclasses with the `[CF_RegisterModule(ClassName)]` attribute (`1_Core\CommunityFramework\Module\CF_RegisterModule.c:1`). The chain is `CF_ModuleWorld : CF_ModuleGame : CF_ModuleCore` (`4_World\...\Module\CF_ModuleWorld.c:1`, `3_Game\...\Module\CF_ModuleGame.c:1`, `1_Core\...\Module\CF_ModuleCore.c:1`).

Events are opt-in: call the `Enable...()` method for each event in `OnInit()`, then override its handler.

| Enable call | Handler | Declared in |
|---|---|---|
| `EnableInvokeConnect()` | `OnInvokeConnect(Class sender, CF_EventArgs args)` | `CF_ModuleWorld.c:3` and `:56` |
| `EnableInvokeDisconnect()` | `OnInvokeDisconnect(Class sender, CF_EventArgs args)` | `CF_ModuleWorld.c:8` |
| `EnableClientReady()` | `OnClientReady(Class sender, CF_EventArgs args)` | `CF_ModuleWorld.c:23` and `:76` |
| `EnableUpdate()` | `OnUpdate(Class sender, CF_EventArgs args)` | `CF_ModuleCore.c:76` and `:174` |
| `EnableMissionStart()` | `OnMissionStart(Class sender, CF_EventArgs args)` | `CF_ModuleCore.c:81` and `:168` |
| `EnableMissionFinish()` | `OnMissionFinish(Class sender, CF_EventArgs args)` | `CF_ModuleCore.c:86` and `:170` |

Connect and disconnect pass a `CF_EventPlayerArgs` with `Player` and `Identity` (`4_World\CommunityFramework\EventArgs\CF_EventPlayerArgs.c:1`); update passes a `CF_EventUpdateArgs` with `DeltaTime` (`1_Core\CommunityFramework\EventArgs\CF_EventUpdateArgs.c:1`).

```c
// Scripts/4_World/MyMod_Module.c

[CF_RegisterModule(MyMod_Module)]
class MyMod_Module : CF_ModuleWorld
{
    override void OnInit()
    {
        super.OnInit();

        EnableInvokeConnect();          // player connected (server)
        EnableInvokeDisconnect();       // player disconnected (server)
        EnableClientReady();            // local player set up (client)
        EnableUpdate();                 // frame update
        EnableMissionStart();           // mission is fully started
        EnableMissionFinish();          // mission ending
    }

    override void OnInvokeConnect(Class sender, CF_EventArgs args)
    {
        super.OnInvokeConnect(sender, args);

        auto casted = CF_EventPlayerArgs.Cast(args);
        if (!casted || !casted.Player)
            return;

        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(this.MyMod_DelayedWelcome, 3000, false, casted.Player);
    }

    void MyMod_DelayedWelcome(PlayerBase player)
    {
        if (!player || !player.IsAlive())
            return;
        // send your own RPC here (see "CF RPCManager" below, or ../patterns/rpc.md)
    }

    override void OnUpdate(Class sender, CF_EventArgs args)
    {
        super.OnUpdate(sender, args);

        CF_EventUpdateArgs update = CF_EventUpdateArgs.Cast(args);
        float dt = update.DeltaTime;
        // Avoid heavy work every frame; use your own accumulator
    }

    override void OnClientReady(Class sender, CF_EventArgs args)
    {
        super.OnClientReady(sender, args);
        // Safe to access GetGame().GetPlayer() here on the client
    }

    override void OnInvokeDisconnect(Class sender, CF_EventArgs args)
    {
        super.OnInvokeDisconnect(sender, args);
        auto casted = CF_EventPlayerArgs.Cast(args);
        if (!casted || !casted.Player)
            return;
        // clean up per-player data
    }
}
```

There is no per-player module class in this CF build (`class CF_ModulePlayer` does not appear in the PBO). Keep per-player data in a map on the world module, keyed by the player's ID.

---

## CF ModStorage: Per-Entity Persistent Data

ModStorage lets you attach your own save data to any entity without touching vanilla `OnStoreSave`/`OnStoreLoad`. Each mod gets a named slot, so your data cannot shift another mod's.

`CF_OnStoreSave(CF_ModStorageMap storage)` and `CF_OnStoreLoad(CF_ModStorageMap storage)` are declared on CF's modded `ItemBase` (`4_World\CommunityFramework\Entities\ItemBase.c:42`) and on the other entity bases in the same folder (`BuildingBase.c`, `CarScript.c`, `DayZPlayerImplement.c`, `ZombieBase.c`, ...). `CF_ModStorageMap` has `Get(string name)` and `Contains(string name)` (`3_Game\CommunityFramework\ModStorage\CF_ModStorageMap.c:5` and `:15`).

```c
modded class ItemBase
{
    override void CF_OnStoreSave(CF_ModStorageMap storage)
    {
        super.CF_OnStoreSave(storage);

        CF_ModStorage ctx = storage.Get("MyMod");
        ctx.Write(m_MyModCustomValue);
        ctx.Write(m_MyModTag);
    }

    override bool CF_OnStoreLoad(CF_ModStorageMap storage)
    {
        if (!super.CF_OnStoreLoad(storage))
            return false;

        // Mod data does not exist in saves made before the mod was added
        if (!storage.Contains("MyMod"))
            return true;

        CF_ModStorage ctx = storage.Get("MyMod");
        if (!ctx.Read(m_MyModCustomValue)) return false;
        if (!ctx.Read(m_MyModTag))         return false;

        return true;
    }
}
```

### Version-guarding inside ModStorage

`CF_ModStorage.GetVersion()` returns the version the slot was saved with (`3_Game\CommunityFramework\ModStorage\CF_ModStorage.c:41`); CF's own example branches on it (`4_World\CommunityFramework\Entities\ItemBase.c:70`):

```c
int version = ctx.GetVersion();
if (!ctx.Read(m_MyField)) return false;
if (version >= 2)
{
    if (!ctx.Read(m_MyNewField)) return false;
}
```

---

## CF RPCManager

CF routes RPCs by mod name and function name through one shared ID (`FRAMEWORK_RPC_ID = 10042`, `3_Game\CommunityFramework\RPC\RPCManager.c:47`), so mods using it never pick ID ranges. There is no `CF_RPC` class or `RegisterRPC` call in CF; the API is `GetRPCManager()` (`RPCManager.c:208`):

| Call | Signature | Line |
|---|---|---|
| Register a handler | `bool AddRPC(string modName, string funcName, Class instance, int singlePlayerExecType = SingleplayerExecutionType.Server)` | `RPCManager.c:171` |
| Send | `void SendRPC(string modName, string funcName, Param params = NULL, bool guaranteed = false, PlayerIdentity sendToIdentity = NULL, Object sendToTarget = NULL)` | `RPCManager.c:111` |
| Single-player side | `enum SingleplayerExecutionType { Server, Client, Both }` | `RPCManager.c:8` |

CF calls the handler with a `Param4<CallType, ParamsReadContext, PlayerIdentity, Object>` (`RPCManager.c:87`), so the handler takes those four values. `CallType` is `Server` or `Client` (`RPCManager.c:15`).

```c
// Registration (once, e.g. in the module's OnInit)
GetRPCManager().AddRPC("MyMod", "OnRPC_ShowMessage", this, SingleplayerExecutionType.Both);

// Sender (server to one client)
void SendMsg(PlayerBase target, string msg)
{
    GetRPCManager().SendRPC("MyMod", "OnRPC_ShowMessage", new Param1<string>(msg), true, target.GetIdentity());
}

// Receiver
void OnRPC_ShowMessage(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
{
    Param1<string> data;
    if (!ctx.Read(data))
        return;
    // display data.param1
}
```

A module can also call `AddLegacyRPC(string funcName, ...)`, which registers the function under the module's class name (`3_Game\CommunityFramework\Module\CF_ModuleGame.c:101-103`). For mods without CF, use vanilla RPC (`../patterns/rpc.md`).

---

## Events between mods

CF has no global named event bus in this build (no `CF_EventModule` class in the PBO). To let other mods react to yours, expose a `CF_EventHandler` on your module (`2_GameLib\CommunityFramework\EventHandler\CF_EventHandler.c:70`). Other mods subscribe with `AddSubscriber(ScriptCaller caller)` (:8) and you fire it with `Invoke(Class sender = NULL, TEventArgs args = NULL)` (:52):

```c
class MyMod_OnPointsChanged : CF_EventArgs
{
    PlayerBase Player;
    int        Delta;
}

[CF_RegisterModule(MyMod_Points)]
class MyMod_Points : CF_ModuleWorld
{
    ref CF_EventHandler OnPointsChanged = new CF_EventHandler();

    void AddPoints(PlayerBase player, int delta)
    {
        // ... update the points ...
        MyMod_OnPointsChanged ev = new MyMod_OnPointsChanged();
        ev.Player = player;
        ev.Delta  = delta;
        OnPointsChanged.Invoke(this, ev);
    }
}

// Another mod, which loads after MyMod:
// points.OnPointsChanged.AddSubscriber(ScriptCaller.Create(this.HandlePointsChanged));
```

The subscriber must see `MyMod_Points` at compile time, so it lists your mod in `requiredAddons[]`.
