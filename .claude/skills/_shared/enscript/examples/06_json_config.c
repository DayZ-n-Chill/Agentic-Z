// =============================================================================
// MyMod_Config.c
// JSON-driven server configuration singleton.
//   - Loaded from $profile:\MyMod\config.json on first access
//   - Written to disk with defaults when no file exists
//   - Nested config classes show how to serialise sub-objects
//   - Global accessor function for ergonomic use anywhere
//
// Placement: Scripts/3_Game/MyMod_Config.c
//   (3_Game loads on BOTH server and client; use for shared config)
//   Move to 5_Mission/Mission/ if server-only data and file paths matter.
//
// IMPORTANT: JsonFileLoader only serialises PUBLIC members.
//            Private / protected members are silently ignored.
// =============================================================================

// ---- Nested struct: spawn settings -----------------------------------------
class MyMod_SpawnConfig
{
    // All fields must be PUBLIC for JSON serialisation
    bool  EnableStarterKit  = true;
    int   StarterWaterMl    = 500;
    float HealthOnSpawn     = 100.0;  // 0..100 matching game health scale
}

// ---- Nested struct: timing settings ----------------------------------------
class MyMod_TimingConfig
{
    int  WelcomeDelayMs     = 3000;
    int  ServerTickIntervalS = 60;
    bool EnableArtyBarrage  = false;
    float ArtyDelayS        = 120.0;
}

// ---- Root config class ------------------------------------------------------
class MyMod_Config
{
    // --- meta ---
    string ModVersion       = "1.0.0";

    // --- feature toggles ---
    bool   EnableWelcomeMsg  = true;
    string WelcomeText       = "Welcome to the server!";
    bool   EnablePvP         = true;
    float  GlobalDamageScale = 1.0;

    // --- nested objects ---
    // JsonFileLoader supports nested classes directly
    ref MyMod_SpawnConfig  Spawn  = new MyMod_SpawnConfig();
    ref MyMod_TimingConfig Timing = new MyMod_TimingConfig();

    // --- admin UIDs (array of strings) ---
    ref array<string> AdminUIDs = {};

    // -------------------------------------------------------------------------
    // Singleton plumbing
    // -------------------------------------------------------------------------
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

    // Force a reload from disk (e.g. after a /reloadconfig admin command)
    static void Reload()
    {
        s_Instance = null; // discard; next GetInstance() will re-read disk
    }

    // -------------------------------------------------------------------------
    // Load
    // -------------------------------------------------------------------------
    void Load()
    {
        string path = FOLDER + FILE;

        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);

        if (FileExist(path))
        {
            // JsonLoadFile fills 'this' in-place; matching field names by key.
            // Extra JSON keys are ignored; missing keys keep default values.
            JsonFileLoader<MyMod_Config>.JsonLoadFile(path, this);
            Print("[MyMod] Config loaded from " + path);
        }
        else
        {
            // First run – write defaults so admins can see the schema
            Save();
            Print("[MyMod] Config defaults written to " + path);
        }
    }

    // -------------------------------------------------------------------------
    // Save
    // -------------------------------------------------------------------------
    void Save()
    {
        string path = FOLDER + FILE;
        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);
        JsonFileLoader<MyMod_Config>.JsonSaveFile(path, this);
    }

    // -------------------------------------------------------------------------
    // Convenience helpers
    // -------------------------------------------------------------------------
    bool IsAdmin(string uid)
    {
        return AdminUIDs.Find(uid) != -1;
    }
}

// ---- Global accessor --------------------------------------------------------
// Allows clean call-site syntax:  GetMyModConfig().EnablePvP
// This is NOT a singleton pattern violation in Enforce Script because there is
// no module system – a free function acts as the access point.

MyMod_Config GetMyModConfig()
{
    return MyMod_Config.GetInstance();
}
