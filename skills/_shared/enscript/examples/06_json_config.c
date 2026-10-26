// =============================================================================
// MyMod_Config.c
// JSON-driven server configuration singleton.
//   - Loaded from $profile:MyMod/config.json on first access
//   - Written to disk with defaults when no file exists
//   - Nested config classes show how to serialise sub-objects
//   - Global accessor function for ergonomic use anywhere
//
// Placement: Scripts/3_Game/MyMod_Config.c
//   JsonFileLoader itself lives in 3_Game, so 3_Game is the lowest module
//   that can use it.  // P:\scripts\3_game\tools\jsonfileloader.c:1
//   Every script module (3_Game, 4_World, 5_Mission) is compiled on both
//   server and client; no folder is server-only. For server-only config, call
//   GetInstance() only behind GetGame().IsServer() / IsDedicatedServer().
//   // P:\scripts\3_game\global\game.c:1120 (IsServer), :1125 (IsDedicatedServer)
//
// SERIALISATION: JsonSerializer does deep serialisation of class members; the
//   documented way to skip a member is the [NonSerialized()] attribute.
//   // P:\scripts\1_core\proto\serializer.c:8, :16
//   // P:\scripts\1_core\proto\enscript.c:122 (class NonSerialized)
//   UNVERIFIED on P: (engine-side, not in script): that private/protected and
//   static members are skipped. Keep JSON fields public and mark anything else
//   [NonSerialized()] rather than relying on access modifiers.
// =============================================================================

// ---- Nested struct: spawn settings -----------------------------------------
class MyMod_SpawnConfig
{
    // Field names are the JSON keys, so they are plain public members
    // (vanilla JSON data classes do the same: P:\scripts\3_game\cfggameplaydatajson.c:4)
    bool  EnableStarterKit  = true;
    int   StarterWaterMl    = 500;
    float HealthOnSpawn     = 100.0;  // player global health is 0..100
                                      // P:\DZ\characters\data\config.cpp:382 (SurvivorBase hitpoints=100)
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
    // Nested classes serialise as JSON objects; vanilla initialises them inline
    // the same way. // P:\scripts\3_game\cfggameplaydatajson.c:15
    ref MyMod_SpawnConfig  Spawn  = new MyMod_SpawnConfig();
    ref MyMod_TimingConfig Timing = new MyMod_TimingConfig();

    // --- admin UIDs (array of strings) ---
    // Inline array literal on a ref array member: P:\scripts\3_game\cfggameplaydatajson.c:198
    ref array<string> AdminUIDs = {};

    // -------------------------------------------------------------------------
    // Singleton plumbing
    // -------------------------------------------------------------------------
    // Static: not an instance field, so not written to the JSON (UNVERIFIED on P:, see header)
    private static ref MyMod_Config s_Instance;

    // "$profile:" + name, forward slashes, as vanilla does
    // P:\scripts\3_game\constants.c:257 (CFG_FILE_DEBUG_DIR = "$profile:ScriptConsole/")
    static const string FOLDER = "$profile:MyMod/";
    static const string FILE   = "config.json";

    static MyMod_Config GetInstance()
    {
        if (!s_Instance)
        {
            s_Instance = new MyMod_Config();
            Load();
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
    // Static so the target is a variable: LoadFile takes 'out T data', and every
    // vanilla caller passes a variable, never 'this' (passing 'this' to an out
    // parameter is UNVERIFIED on P:).
    // P:\scripts\3_game\tools\jsonfileloader.c:7
    //   static bool LoadFile(string filename, out T data, out string errorMessage)
    // JsonLoadFile / JsonSaveFile are marked DEPRECATED in vanilla; use
    // LoadFile / SaveFile. // P:\scripts\3_game\tools\jsonfileloader.c:99-134
    protected static void Load()
    {
        string path = FOLDER + FILE;

        // FileExist works on folders too; vanilla checks a folder before
        // MakeDirectory. // P:\scripts\5_mission\gui\cameratools\cameratoolsmenu.c:210-211
        // P:\scripts\1_core\proto\ensystem.c:397 (FileExist), :525 (MakeDirectory)
        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);

        if (FileExist(path))
        {
            // Loading into an already-built instance keeps it as the target;
            // vanilla does the same with its pre-filled defaults.
            // P:\scripts\3_game\cfggameplayhandler.c:71
            // UNVERIFIED on P: (engine-side): extra JSON keys are ignored and
            // missing keys keep their default values.
            string errorMessage;
            if (!JsonFileLoader<MyMod_Config>.LoadFile(path, s_Instance, errorMessage))
            {
                // Vanilla reports load failures with ErrorEx.
                // P:\scripts\3_game\objectspawner.c:28, P:\scripts\1_core\proto\endebug.c:83
                ErrorEx(errorMessage);
                return;
            }
            Print("[MyMod] Config loaded from " + path); // P:\scripts\1_core\proto\endebug.c:96
        }
        else
        {
            // First run - write defaults so admins can see the schema
            s_Instance.Save();
            Print("[MyMod] Config defaults written to " + path);
        }
    }

    // -------------------------------------------------------------------------
    // Save
    // -------------------------------------------------------------------------
    // P:\scripts\3_game\tools\jsonfileloader.c:42
    //   static bool SaveFile(string filename, T data, out string errorMessage)
    void Save()
    {
        string path = FOLDER + FILE;
        if (!FileExist(FOLDER))
            MakeDirectory(FOLDER);

        string errorMessage;
        if (!JsonFileLoader<MyMod_Config>.SaveFile(path, this, errorMessage))
            ErrorEx(errorMessage); // same pattern: P:\scripts\3_game\objectspawner.c:125-126
    }

    // -------------------------------------------------------------------------
    // Convenience helpers
    // -------------------------------------------------------------------------
    bool IsAdmin(string uid)
    {
        // array.Find returns the index, or -1 when absent
        // P:\scripts\1_core\proto\enscript.c:392-394
        return AdminUIDs.Find(uid) != -1;
    }
}

// ---- Global accessor --------------------------------------------------------
// Allows clean call-site syntax:  GetMyModConfig().EnablePvP
// Vanilla uses free accessor functions the same way, e.g. GetDayZGame().
// P:\scripts\3_game\dayzgame.c:4076

MyMod_Config GetMyModConfig()
{
    return MyMod_Config.GetInstance();
}
