# Pattern: schema migration for admin-tunable JSON configs

Mods that ship JSON config files (`cfggameplay.json`-style: admin opens it, edits values, restarts server) need a forward-compatible migration story. Otherwise: admin runs old JSON against new mod, missing fields → either crashes or silently uses default-of-default → admin reports *"feature gone"* that's actually just unset.

See also: `examples/06_json_config.c` for the singleton-load companion pattern.

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

static MyMod_Settings LoadOrCreate(string path)
{
    MyMod_Settings cfg = new MyMod_Settings;

    if (!FileExist(path))
    {
        cfg.Defaults();
        SaveToDisk(cfg, path);
        return cfg;
    }

    if (!JsonFileLoader<MyMod_Settings>.JsonLoadFile(path, cfg))
    {
        // Parse failed — admin probably has a typo. DO NOT overwrite;
        // log + return defaults in memory only.
        cfg.Defaults();
        Print("[MyMod] settings JSON failed to parse — using in-memory defaults; not overwriting");
        return cfg;
    }

    if (cfg.version < MyMod_Settings.SCHEMA_VERSION)
    {
        // Forward migration. Build a fresh defaults instance and copy in
        // only the NEW fields that didn't exist in the old version.
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
        Print("[MyMod] migrated settings v" + cfg.version + " -> v" + MyMod_Settings.SCHEMA_VERSION);
    }

    return cfg;
}
```

---

## Rules of thumb

- Bump `SCHEMA_VERSION` whenever you add a field. Don't bump for behavior changes that don't change the JSON shape.
- Constructor stays minimal — just enough so the serializer doesn't choke on null members. All "didactic example" defaults live in `Defaults()`.
- On parse failure, **DO NOT overwrite the file**. The admin may be mid-edit with a typo. Use defaults in memory only and log loudly.
- Migration is incremental: each `if (cfg.version < N)` block patches in only the fields added at version N.

Reference pattern: `salutesh/DayZ-Expansion-Scripts/ExpansionGarageSettings.c::OnLoad` uses an equivalent approach.
