# Pattern: Singleton Config

A static, lazily-initialized configuration class loaded from a JSON file on the server profile directory. The singleton lives in `3_Game` (loads on both server and client) or `5_Mission` for server-only data.

It loads with `JsonFileLoader<T>.LoadFile(path, data, errorMessage)` and saves with `SaveFile(path, data, errorMessage)`, which return `bool` and say what went wrong (`P:\scripts\3_game\tools\jsonfileloader.c:7` and `:42`). Do not use `JsonLoadFile` or `JsonSaveFile`: they return nothing, so a broken file is only an `ErrorEx` in the log, and vanilla marks them "use JsonFileLoader::LoadFile instead" (`jsonfileloader.c:104-105`).

## Contents

- [Implementation](#implementation)
- [Nested Sub-Config](#nested-sub-config)
- [Rules](#rules)
- [Static `ScriptInvoker` shutdown crash](#-static-scriptinvoker-shutdown-crash)

---

## Implementation

```c
// Scripts/3_Game/MyMod_Config.c

class MyMod_Config
{
    // --- Public config fields (all must be public for JSON serialization) ---
    bool   EnableWelcomeMsg  = true;
    string WelcomeText       = "Welcome to the server!";
    float  GlobalDamageScale = 1.0;
    ref array<string> AdminUIDs = {};

    // --- Nested sub-config ---
    ref MyMod_SpawnConfig Spawn = new MyMod_SpawnConfig();

    // --- Singleton plumbing ---
    private static ref MyMod_Config s_Instance;
    static const string FOLDER = "$profile:\\MyMod\\";
    static const string FILE   = "config.json";

    static MyMod_Config GetInstance()
    {
        if (!s_Instance)
            s_Instance = LoadFromDisk();
        return s_Instance;
    }

    // Force reload from disk (e.g. after an admin /reload command)
    static void Reload()
    {
        s_Instance = null;
    }

    static MyMod_Config LoadFromDisk()
    {
        MyMod_Config cfg = new MyMod_Config();
        string path = FOLDER + FILE;
        if (!FileExist(path))
        {
            cfg.Save(); // write defaults on first run
            return cfg;
        }

        string err;
        if (!JsonFileLoader<MyMod_Config>.LoadFile(path, cfg, err))
        {
            // Keep the admin's file; run on defaults and say why.
            Print("[MyMod] config.json not loaded, using defaults: " + err);
            cfg = new MyMod_Config();
        }
        return cfg;
    }

    void Save()
    {
        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);
        string err;
        if (!JsonFileLoader<MyMod_Config>.SaveFile(FOLDER + FILE, this, err))
            Print("[MyMod] config.json not saved: " + err);
    }

    bool IsAdmin(string uid)
    {
        return AdminUIDs.Find(uid) != -1;
    }
}

// Global accessor: clean call-site: GetMyModConfig().EnableWelcomeMsg
MyMod_Config GetMyModConfig()
{
    return MyMod_Config.GetInstance();
}
```

---

## Nested Sub-Config

```c
class MyMod_SpawnConfig
{
    bool  EnableStarterKit = true;
    int   StarterWaterMl   = 500;
    float HealthOnSpawn    = 100.0;
}
```

`JsonFileLoader` serializes nested `ref` fields recursively. The resulting JSON looks like:

```json
{
    "EnableWelcomeMsg": true,
    "WelcomeText": "Welcome to the server!",
    "GlobalDamageScale": 1.0,
    "AdminUIDs": [],
    "Spawn": {
        "EnableStarterKit": true,
        "StarterWaterMl": 500,
        "HealthOnSpawn": 100.0
    }
}
```

---

## Rules

`LoadFile` and `SaveFile` hand the object to `JsonSerializer`, whose reading and writing is native (`ReadFromString` in `jsonfileloader.c`), so the field rules below cannot be read from script. Rows marked **Reported, not checked on `P:\`** come from modders' reports; test them in your own mod before you rely on them.

| Rule | Detail |
|---|---|
| All serialized fields must be **public** | Reported, not checked on `P:\` (`JsonSerializer` is native): `private` / `protected` fields are silently skipped |
| Nested objects must be `ref` | Reported, not checked on `P:\` (`JsonSerializer` is native): value-type nesting does not serialize correctly |
| Extra JSON keys are ignored | Reported, not checked on `P:\` (`JsonSerializer` is native): safe to add new fields in config without breaking old saves |
| Missing keys keep defaults | Rename fields = default on next load; document field renames |
| Arrays serialize as JSON arrays | `ref array<string>` works. `{}` and `new array<string>()` are both valid ways to create it |

---

## ⚠️ Static `ScriptInvoker` shutdown crash

Reported, not checked on `P:\`: the teardown order of statics is engine behavior that script does not show. The report is that a common cleanup pattern null-derefs on shutdown because static invokers don't have a stable destructor order:

```c
// CRASHES if the static invoker was already torn down
MyClass.Event_PowerChanged.Remove(m_Callback);

// CORRECT: null-check first
if (MyClass.Event_PowerChanged)
    MyClass.Event_PowerChanged.Remove(m_Callback);
```

Assume static invokers may already be null during your destructor or mission cleanup. The fix is always the null-guard: don't try to reorder destruction.
