# Pattern: Singleton Config

A static, lazily-initialized configuration class loaded from a JSON file on the server profile directory. The singleton lives in `3_Game` (loads on both server and client) or `5_Mission` for server-only data.

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
        {
            s_Instance = new MyMod_Config();
            s_Instance.Load();
        }
        return s_Instance;
    }

    // Force reload from disk (e.g. after an admin /reload command)
    static void Reload()
    {
        s_Instance = null;
    }

    void Load()
    {
        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);

        string path = FOLDER + FILE;
        if (FileExist(path))
            JsonFileLoader<MyMod_Config>.JsonLoadFile(path, this);
        else
            Save(); // write defaults on first run
    }

    void Save()
    {
        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);
        JsonFileLoader<MyMod_Config>.JsonSaveFile(FOLDER + FILE, this);
    }

    bool IsAdmin(string uid)
    {
        return AdminUIDs.Find(uid) != -1;
    }
}

// Global accessor — clean call-site: GetMyModConfig().EnableWelcomeMsg
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

| Rule | Detail |
|---|---|
| All serialized fields must be **public** | `private` / `protected` fields are silently skipped |
| Nested objects must be `ref` | Value-type nesting does not serialize correctly |
| Extra JSON keys are ignored | Safe to add new fields in config without breaking old saves |
| Missing keys keep defaults | Rename fields = default on next load; document field renames |
| Arrays serialize as JSON arrays | `ref array<string>` works; use `{}` not `new array<string>()` for literal init |

---

## ⚠️ Static `ScriptInvoker` shutdown crash

A common cleanup pattern null-derefs on shutdown because static invokers don't have a stable destructor order:

```c
// CRASHES if the static invoker was already torn down
MyClass.Event_PowerChanged.Remove(m_Callback);

// CORRECT — null-check first
if (MyClass.Event_PowerChanged)
    MyClass.Event_PowerChanged.Remove(m_Callback);
```

Assume static invokers may already be null during your destructor or mission cleanup. The fix is always the null-guard — don't try to reorder destruction.
