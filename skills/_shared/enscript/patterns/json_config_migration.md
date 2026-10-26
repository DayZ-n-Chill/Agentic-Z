# Pattern: schema migration for admin-tunable JSON configs

Mods that ship JSON config files (`cfggameplay.json`-style: admin opens it, edits values, restarts server) need a forward-compatible migration story. Otherwise: admin runs old JSON against new mod, missing fields → either crashes or silently uses default-of-default → admin reports *"feature gone"* that's actually just unset.

See also: `examples/06_json_config.c` for the singleton-load companion pattern.

Load and save with `JsonFileLoader<T>.LoadFile(path, data, errorMessage)` and `SaveFile(path, data, errorMessage)`. Both return `bool` and fill `errorMessage` (`P:\scripts\3_game\tools\jsonfileloader.c:7` and `:42`). The older `JsonLoadFile` and `JsonSaveFile` return `void`, so `if (!...JsonLoadFile(...))` does not compile, and vanilla marks them "use JsonFileLoader::LoadFile instead" (`jsonfileloader.c:104-105`).

---

## Pattern

```c
class MyMod_Settings
{
    static const int SCHEMA_VERSION = 3;

    int    version;            // sentinel; 0 = "not loaded yet"
    string serverName;
    int    maxPlayers;
    ref array<string> allowedKits;

    // Constructor: minimal scalar defaults + empty arrays so the JSON
    // serializer never sees null members.
    void MyMod_Settings()
    {
        version = 0;
        serverName = "";
        maxPlayers = 0;
        allowedKits = new array<string>;
    }

    // Defaults() is separate so it can be called at fresh-install time AND
    // re-used at migration time to source new-field default values.
    void Defaults()
    {
        serverName = "Untitled Server";
        maxPlayers = 60;
        allowedKits.Clear();
        allowedKits.Insert("StarterKit_Basic");
        version = SCHEMA_VERSION;
    }
}

static void SaveToDisk(MyMod_Settings cfg, string path)
{
    string err;
    if (!JsonFileLoader<MyMod_Settings>.SaveFile(path, cfg, err))
        Print("[MyMod] cannot save settings: " + err);
}

static MyMod_Settings LoadOrCreate(string path)
{
    MyMod_Settings cfg = new MyMod_Settings;

    if (!FileExist(path))
    {
        cfg.Defaults();
        SaveToDisk(cfg, path);
        return cfg;
    }

    string err;
    if (!JsonFileLoader<MyMod_Settings>.LoadFile(path, cfg, err))
    {
        // Parse failed: admin probably has a typo. DO NOT overwrite;
        // log + return defaults in memory only.
        cfg = new MyMod_Settings; // a failed parse can leave cfg half filled
        cfg.Defaults();
        Print("[MyMod] settings JSON failed to parse (" + err + "); using in-memory defaults, not overwriting");
        return cfg;
    }

    if (cfg.version < MyMod_Settings.SCHEMA_VERSION)
    {
        // Forward migration. Build a fresh defaults instance and copy in
        // only the NEW fields that didn't exist in the old version.
        int oldVersion = cfg.version;
        MyMod_Settings fresh = new MyMod_Settings;
        fresh.Defaults();

        if (cfg.version < 2)
        {
            // Field added in v2:
            cfg.maxPlayers = fresh.maxPlayers;
        }
        if (cfg.version < 3)
        {
            // Field added in v3:
            cfg.allowedKits = fresh.allowedKits;
        }

        cfg.version = MyMod_Settings.SCHEMA_VERSION;
        SaveToDisk(cfg, path);
        Print("[MyMod] migrated settings v" + oldVersion + " -> v" + MyMod_Settings.SCHEMA_VERSION);
    }

    return cfg;
}
```

---

## Rules of thumb

- Bump `SCHEMA_VERSION` whenever you add a field. Don't bump for behavior changes that don't change the JSON shape.
- Constructor stays minimal: just enough so the serializer doesn't choke on null members. All "didactic example" defaults live in `Defaults()`.
- On parse failure, **DO NOT overwrite the file**. The admin may be mid-edit with a typo. Use defaults in memory only and log loudly.
- Migration is incremental: each `if (cfg.version < N)` block patches in only the fields added at version N.

Vanilla reference: `CfgGameplayHandler` loads `cfggameplay.json` with `LoadFile` and reports the error message instead of overwriting the file (`P:\scripts\3_game\cfggameplayhandler.c:70-72`), and its data class keeps a `version` field (`P:\scripts\3_game\cfggameplaydatajson.c:4`).
