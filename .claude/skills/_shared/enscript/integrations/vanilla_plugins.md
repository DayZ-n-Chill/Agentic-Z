# Vanilla Plugin System Integration

Plugins are global singletons owned by `PluginManager`. They are the vanilla equivalent of a service locator: one shared instance per class, reachable from anywhere through `GetPlugin(PluginClassName)`. They are **not** created automatically: `PluginManager.Init()` registers each plugin class by name, and only registered plugins are spawned (`P:\scripts\4_world\plugins\pluginmanager.c:39-104`). A plugin that is never registered makes `GetPlugin` return `null`.

All line numbers below are in `P:\scripts\4_world\plugins\` unless another path is given.

## Contents

- [Defining a Plugin](#defining-a-plugin)
- [Registering it](#registering-it)
- [Accessing from Anywhere](#accessing-from-anywhere)
- [Plugin Lifecycle Hooks](#plugin-lifecycle-hooks)
- [PluginAdminLog](#pluginadminlog)
- [Other vanilla plugins](#other-vanilla-plugins)
- [Mod-to-Mod Plugin Communication](#mod-to-mod-plugin-communication)
- [Plugin vs. Module (CF)](#plugin-vs-module-cf)

---

## Defining a Plugin

`PluginBase` declares `OnInit()`, `OnUpdate(float delta_time)` and `OnDestroy()` (`pluginbase.c:6-8`). Put the plugin in `4_World` or later, where `PluginBase` lives.

```c
// Scripts/4_World/Plugins/PluginMyMod.c
class PluginMyMod : PluginBase
{
    protected ref map<string, int>   m_PointsMap;  // uid -> points
    protected ref MyMod_Config       m_Config;

    // Called once, right after every registered plugin is spawned
    override void OnInit()
    {
        m_PointsMap = new map<string, int>;
        m_Config    = MyMod_Config.GetInstance();
        Print("[PluginMyMod] Initialised");
    }

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

---

## Registering it

Add the plugin in a modded `PluginManager.Init()`, after `super.Init()`. `RegisterPlugin(string plugin_class_name, bool reg_on_client, bool reg_on_server, bool reg_on_release = true)` is at `pluginmanager.c:193`; vanilla registers its own plugins the same way, for example `RegisterPlugin("PluginAdminLog", false, true)` (`:57`).

```c
// Scripts/4_World/Plugins/PluginManager.c
modded class PluginManager
{
    override void Init()
    {
        super.Init();
        //             class name      client  server
        RegisterPlugin("PluginMyMod",  true,   true);
    }
}
```

This works because the mission calls `PluginManagerInit()` (`P:\scripts\5_mission\mission\missionbase.c:21`), which runs `Init()` and then `PluginsInit()` (`pluginmanager.c:297-303`). `PluginsInit()` spawns every registered class and then calls `OnInit()` on each (`:110-138`). Pass `false` for client or server to keep a plugin off that side: in multiplayer, `RegisterPlugin` skips it there (`:195-212`).

---

## Accessing from Anywhere

`GetPlugin(typename plugin_type)` (`pluginmanager.c:326`) returns the instance, or `null` when the class was never registered. Only a `DIAG_DEVELOPER` build also prints "not Registred in PluginManager.c" (:336-342); retail builds stay silent. `GetPluginSafe` (:350) never prints.

```c
// Retrieve the singleton with a safe cast
PluginMyMod pm;
if (!Class.CastTo(pm, GetPlugin(PluginMyMod)))
    return;

pm.AddPoints(player.GetIdentity().GetId(), 10);
```

---

## Plugin Lifecycle Hooks

| Method | When it fires | Source |
|---|---|---|
| `OnInit()` | Once, after all registered plugins are spawned | `pluginmanager.c:131-138` |
| `OnUpdate(float delta_time)` | Every gameplay update, for every plugin | `PluginManager.MainOnUpdate`, `pluginmanager.c:143-153`, queued at :104 |
| `OnDestroy()` | When the plugin manager is deleted, as the mission ends | `pluginmanager.c:23-31`; `missionbase.c:61` |

There is no opt-in step for `OnUpdate`: `PluginManager.Init()` puts `MainOnUpdate` in the `CALL_CATEGORY_GAMEPLAY` update queue (`:104`), and it calls `OnUpdate` on every plugin. Keep `OnUpdate` cheap, or leave it empty and use a timer (`../patterns/scheduler.md`). Player events such as connect and reconnect are not forwarded to plugins; call your plugin from a modded `MissionServer`.

---

## PluginAdminLog

Vanilla includes `PluginAdminLog` to write to the server admin log (`pluginbase\pluginadminlog.c:1`). It is registered on the server only (`pluginmanager.c:57`), so `GetPlugin(PluginAdminLog)` is `null` on a client. Write a line with `LogPrint(string message)` (`pluginadminlog.c:62`), and build the usual player prefix with `GetPlayerPrefix(PlayerBase player, PlayerIdentity identity)` (:67):

```c
PluginAdminLog log;
if (Class.CastTo(log, GetPlugin(PluginAdminLog)))
{
    log.LogPrint(log.GetPlayerPrefix(player, player.GetIdentity()) + " picked up " + itemName);
}
```

`PluginBase.Log(string msg, string label)` (`pluginbase.c:10`) is a different call: it writes a debug log line, not the admin log.

---

## Other vanilla plugins

`PluginPlayerStatus`, `PluginLifespan`, `PluginRecipesManager`, `PluginTransmissionAgents` and the rest are registered in the same list (`pluginmanager.c:46-57`). Read their files under `P:\scripts\4_world\plugins\pluginbase\` before relying on one; they are internal services, not a modding API.

---

## Mod-to-Mod Plugin Communication

Enforce Script has single inheritance only: a class has one parent, so `class PluginMyMod : PluginBase, IMyMod_PointsService` does not compile. To let another mod use your service without a hard dependency, give it a base class of its own that the other mod can also see, and look the plugin up by name at runtime:

```c
// Mod A, in a small shared PBO or its own 4_World: the service contract
class MyMod_PointsServiceBase : PluginBase
{
    int GetPoints(string uid) { return 0; }
    void AddPoints(string uid, int delta) {}
}

// Mod A: the real plugin, registered as shown above
class PluginMyMod : MyMod_PointsServiceBase
{
    override int GetPoints(string uid) { /* ... */ return 0; }
    override void AddPoints(string uid, int delta) { /* ... */ }
}

// Mod B: no compile-time reference to PluginMyMod
typename t = "PluginMyMod".ToType();
MyMod_PointsServiceBase svc;
if (t && Class.CastTo(svc, GetPluginSafe(t)))
    svc.AddPoints(uid, 5);
else
    Print("[ModB] PluginMyMod not loaded, skipping points");
```

`string.ToType()` turns a class name into a `typename`, as `RegisterPlugin` does (`pluginmanager.c:222`). If the name is unknown, `t` is `null` and Mod B skips the call.

---

## Plugin vs. Module (CF)

| | Vanilla Plugin | CF Module |
|---|---|---|
| Dependency | None | Requires CF loaded |
| Multiplicity | One per class | One per class |
| Event hooks | `OnInit`, `OnUpdate`, `OnDestroy` | Rich event bus (see `community_framework.md`) |
| Persistence | Manual | CF ModStorage |
| Recommended for | Simple shared services | Feature-rich mods with CF |
