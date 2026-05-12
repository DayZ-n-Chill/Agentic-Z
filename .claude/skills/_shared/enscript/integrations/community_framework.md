# Community Framework (CF) Integration

[DayZ-CommunityFramework](https://github.com/Arkensor/DayZ-CommunityFramework) — the dominant mod compatibility layer. Provides a module event bus, per-entity mod storage, and an RPC manager.

---

## Module System

Modules are the core CF pattern. Each mod registers one or more `CF_ModuleWorld` (or `CF_ModulePlayer`) subclasses decorated with `[CF_RegisterModule(ClassName)]`.

```c
// Scripts/4_World/MyMod_Module.c

[CF_RegisterModule(MyMod_Module)]
class MyMod_Module : CF_ModuleWorld
{
    // -------------------------------------------------------------------------
    // Lifecycle
    // -------------------------------------------------------------------------
    override void OnInit()
    {
        super.OnInit();

        // Subscribe to lifecycle events (opt-in model)
        EnableInvokeConnect();          // player connected
        EnableInvokeDisconnect();       // player disconnected
        EnableClientReady();            // client HUD loaded (client only)
        EnableUpdate();                 // frame update
        EnableMissionStart();           // mission is fully started
        EnableMissionFinish();          // mission ending

        // Server-side only subscriptions
        if (GetGame().IsServer())
        {
            // no additional opt-ins needed for server-only logic
        }
    }

    // -------------------------------------------------------------------------
    // Player connected (both server and client fire this, guard as needed)
    // -------------------------------------------------------------------------
    override void OnInvokeConnect(Class sender, CF_EventArgs args)
    {
        super.OnInvokeConnect(sender, args);

        auto casted = CF_EventPlayerArgs.Cast(args);
        PlayerBase player = casted.Player;
        if (!player)
            return;

        if (GetGame().IsServer())
        {
            GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(
                this.MyMod_DelayedWelcome, 3000, false, player
            );
        }
    }

    void MyMod_DelayedWelcome(PlayerBase player)
    {
        if (!player || !player.IsAlive())
            return;
        Param1<string> p = new Param1<string>("Welcome to the server!");
        GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, p, true, player.GetIdentity());
    }

    // -------------------------------------------------------------------------
    // Per-frame update
    // -------------------------------------------------------------------------
    override void OnUpdate(Class sender, CF_EventArgs args)
    {
        super.OnUpdate(sender, args);

        // Cast args to access delta time
        CF_EventUpdateArgs update = CF_EventUpdateArgs.Cast(args);
        float dt = update.DeltaTime;

        // Avoid heavy work every frame – use your own accumulator
    }

    // -------------------------------------------------------------------------
    // Client ready: called on the client when the local player entity is set up
    // -------------------------------------------------------------------------
    override void OnClientReady(Class sender, CF_EventArgs args)
    {
        super.OnClientReady(sender, args);
        // Safe to access GetGame().GetPlayer() here on client
    }

    // -------------------------------------------------------------------------
    // Player disconnected
    // -------------------------------------------------------------------------
    override void OnInvokeDisconnect(Class sender, CF_EventArgs args)
    {
        super.OnInvokeDisconnect(sender, args);
        auto casted = CF_EventPlayerArgs.Cast(args);
        PlayerBase player = casted.Player;
        if (!player)
            return;
        // clean up per-player data
    }
}
```

---

## CF_ModulePlayer

For per-player logic that should be coupled to a `PlayerBase`, extend `CF_ModulePlayer` instead. The module instance per player is available via `CF_ModulePlayer.GetInstance(player)`.

---

## CF ModStorage — Per-Entity Persistent Data

ModStorage lets you attach your own save data to any entity without touching vanilla `OnStoreSave`/`OnStoreLoad`. Data is stored in a separate side-channel so you never corrupt vanilla data.

```c
// Add to any entity class (ItemBase, PlayerBase, Building, etc.)

modded class ItemBase
{
    // ---- Save ---------------------------------------------------------------
    override void CF_OnStoreSave(CF_ModStorageMap storage)
    {
        super.CF_OnStoreSave(storage);

        // Each mod gets its own named slot
        CF_ModStorage ctx = storage.Get("MyMod");
        // CF_ModStorage is a ParamsWriteContext-compatible writer
        ctx.Write(m_MyModCustomValue);
        ctx.Write(m_MyModTag);
    }

    // ---- Load ---------------------------------------------------------------
    override bool CF_OnStoreLoad(CF_ModStorageMap storage)
    {
        if (!super.CF_OnStoreLoad(storage))
            return false;

        // Guard: mod data may not exist in old saves
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

CF_ModStorage provides a `Version()` method:

```c
int version = ctx.Version();
if (!ctx.Read(m_MyField)) return false;
if (version >= 2)
{
    if (!ctx.Read(m_MyNewField)) return false;
}
```

---

## CF RPCManager (Legacy Helper)

For older CF-based mods you may encounter `CF_RPC`. It wraps ScriptRPC with an ID registration system. **Prefer vanilla RPC for new code.**

```c
// Registration (once, e.g. in module OnInit)
CF_RPC.RegisterRPC(MyMod_RPCIDs.SHOW_MESSAGE, this, "OnRPC_ShowMessage");

// Sender
void SendMsg(PlayerBase target, string msg)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(msg);
    rpc.Send(target, MyMod_RPCIDs.SHOW_MESSAGE, true, target.GetIdentity());
}

// Receiver (auto-dispatched by CF_RPC)
void OnRPC_ShowMessage(CallType type, ref ParamsReadContext ctx, ref PlayerIdentity sender, ref Object target)
{
    string msg;
    if (!ctx.Read(msg)) return;
    // display msg
}
```

---

## Inter-mod Communication via CF Events

CF provides a typed event bus so mods can decouple from each other:

```c
// Define a custom event args class
class MyMod_OnPointsChanged : CF_EventArgs
{
    PlayerBase Player;
    int        Delta;
    int        NewTotal;
}

// Fire the event (any mod can listen)
CF_EventArgs ev = new MyMod_OnPointsChanged();
MyMod_OnPointsChanged.Cast(ev).Player   = player;
MyMod_OnPointsChanged.Cast(ev).Delta    = delta;
MyMod_OnPointsChanged.Cast(ev).NewTotal = newTotal;
CF_EventModule.GetInstance().Invoke("MyMod_OnPointsChanged", ev);

// Subscribe in another module
override void OnInit()
{
    super.OnInit();
    CF_EventModule.GetInstance().Register("MyMod_OnPointsChanged", this.OnPointsChanged);
}

void OnPointsChanged(Class sender, CF_EventArgs args)
{
    MyMod_OnPointsChanged typed = MyMod_OnPointsChanged.Cast(args);
    Print(string.Format("[AnotherMod] %1 gained %2 points", typed.Player.GetIdentity().GetName(), typed.Delta));
}
```
