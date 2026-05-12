# Vanilla Plugin System Integration

Plugins are global singletons automatically instantiated by the engine at mission start. They are the vanilla equivalent of a service locator — a single shared instance accessible from anywhere via `GetPlugin(PluginClassName)`.

---

## Defining a Plugin

```c
// Scripts/4_World/Plugins/PluginMyMod.c
// Must be in 4_World or later layer.

class PluginMyMod : PluginBase
{
    protected ref map<string, int>   m_PointsMap;  // uid -> points
    protected ref MyMod_Config       m_Config;

    // -------------------------------------------------------------------------
    // OnInit: called once after all scripts load, before mission objects exist
    // -------------------------------------------------------------------------
    override void OnInit()
    {
        m_PointsMap = new map<string, int>;
        m_Config    = MyMod_Config.GetInstance();
        Print("[PluginMyMod] Initialised");
    }

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    int GetPoints(string uid)
    {
        int val;
        m_PointsMap.Find(uid, val);
        return val;
    }

    void AddPoints(string uid, int delta)
    {
        int current = GetPoints(uid);
        m_PointsMap.Set(uid, current + delta);
    }

    void RemovePlayer(string uid)
    {
        m_PointsMap.Remove(uid);
    }
}
```

### Accessing from Anywhere

```c
// Retrieve the singleton with a safe cast
PluginMyMod pm;
if (!Class.CastTo(pm, GetPlugin(PluginMyMod)))
    return;

pm.AddPoints(player.GetIdentity().GetId(), 10);
```

---

## Plugin Lifecycle Hooks

`PluginBase` exposes several overridable hooks:

| Method | When it fires |
|---|---|
| `OnInit()` | After all scripts compile, before mission objects |
| `OnDestroy()` | When the plugin is torn down (server shutdown) |
| `OnUpdate(float deltaTime)` | Each frame if `EnableUpdate()` was called in `OnInit()` |
| `OnReconnect(PlayerBase, PlayerIdentity)` | *(via modded MissionServer)* – plugin does NOT forward this automatically |

To use the per-frame update, opt in:

```c
override void OnInit()
{
    EnableUpdate();
    // ...
}

override void OnUpdate(float deltaTime)
{
    // runs every frame; keep it cheap
}
```

---

## PluginAdminLog

Vanilla includes `PluginAdminLog` – useful to log mod events in the server admin log:

```c
PluginAdminLog log;
if (Class.CastTo(log, GetPlugin(PluginAdminLog)))
{
    log.Log(playerBase, string.Format("Player picked up %1", itemName));
}
```

---

## PluginPlayerStatus / PluginLifespan

These vanilla plugins are used internally for player stat tracking. You can read their state in your own code:

```c
PluginPlayerStatus pps;
if (Class.CastTo(pps, GetPlugin(PluginPlayerStatus)))
{
    // pps exposes stat thresholds and current player status levels
}
```

---

## Mod-to-Mod Plugin Communication

If two mods want to share a plugin without a direct dependency, use a typed access interface:

```c
// Mod A defines an interface
class IMyMod_PointsService
{
    int GetPoints(string uid) { return 0; }
    void AddPoints(string uid, int delta) {}
}

// Mod A implements it
class PluginMyMod : PluginBase, IMyMod_PointsService
{
    override int GetPoints(string uid) { /* ... */ return 0; }
    override void AddPoints(string uid, int delta) { /* ... */ }
}

// Mod B accesses Mod A without depending on PluginMyMod directly
IMyMod_PointsService svc;
if (Class.CastTo(svc, GetPlugin(PluginMyMod)))
    svc.AddPoints(uid, 5);
else
    Print("[ModB] PluginMyMod not loaded – skipping points");
```

---

## Important: Plugin vs. Module (CF)

| | Vanilla Plugin | CF Module |
|---|---|---|
| Dependency | None | Requires CF loaded |
| Multiplicity | One per class | One per class |
| Event hooks | Manual (OnUpdate) | Rich event bus |
| Persistence | Manual | CF ModStorage |
| Recommended for | Simple shared services | Feature-rich mods with CF |
