// =============================================================================
// MyMod_Scheduler.c
// Demonstrates the main timing / scheduling mechanisms available in Enforce Script:
//
//   1. CallLater        – one-shot and repeating, on GetCallQueue
//   2. Timer class      – start/stop object, one-shot or repeat
//   3. OnCEIterate      – server-side periodic hook on items (Central Economy pass)
//                         (OnScheduledTick exists only on PlayerBase:
//                          // P:\scripts\4_world\entities\manbase\playerbase.c:3007)
//   4. Frame-skip pattern in EOnFrame for expensive per-entity work
//   5. GetGame().GetTime() – mission time in MILLISECONDS (int)
//      GetGame().GetTickTime() – time since game start in SECONDS (float), not a frame delta
//      // P:\scripts\3_game\global\game.c:1534 (GetTime), :914 (GetTickTime)
//
// GetGame() returns g_Game (DayZGame)
// // P:\scripts\3_game\gameplay.c:636
//
// Placement: anywhere – this is a patterns reference, not a deployable entity
// =============================================================================

// =============================================================================
// 1. CallLater patterns
// =============================================================================

class MyMod_CallLaterExamples
{
    void Demonstrate()
    {
        // ---- One-shot: fires once after 2 seconds ---------------------------
        // CallLater(func fn, int delay = 0, bool repeat = false, void param1..param9)
        // // P:\scripts\2_gamelib\tools.c:61
        // GetCallQueue(int call_category) // P:\scripts\3_game\dayzgame.c:1233
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(
            this.DoSomethingOnce,
            2000,    // milliseconds
            false    // repeat = false → one-shot
        );

        // ---- Repeating: fires every 5 seconds until explicitly removed ------
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(
            this.DoSomethingRepeatedly,
            5000,
            true     // repeat = true
        );

        // ---- With arguments ---------------------------------------------------
        // CallLater takes up to 9 arguments directly after 'repeat'
        // (vanilla usage: P:\scripts\3_game\dayzgame.c:3319)
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(
            this.DoSomethingWithArgs, 1000, false, "hello", 42
        );

        // CallLaterByName takes ONE Param object, not loose arguments:
        // CallLaterByName(Class obj, string fnName, int delay = 0, bool repeat = false, Param params = NULL)
        // // P:\scripts\2_gamelib\tools.c:63
        // Param2<Class T1, Class T2> // P:\scripts\1_core\param.c:59
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLaterByName(
            this, "DoSomethingWithArgs", 1000, false, new Param2<string, int>("hello", 42)
        );
    }

    void DoSomethingOnce()
    {
        Print("[MyMod] One-shot fired"); // Print(void var) // P:\scripts\1_core\proto\endebug.c:96
    }

    void DoSomethingRepeatedly()
    {
        Print("[MyMod] Repeating tick");
    }

    void DoSomethingWithArgs(string msg, int val)
    {
        // string.Format(string fmt, void param1..param9) // P:\scripts\1_core\proto\enstring.c:526
        Print(string.Format("[MyMod] msg=%1 val=%2", msg, val));
    }

    // ---- Cancel a repeating CallLater before the object is destroyed --------
    void Cleanup()
    {
        // Remove(func fn) // P:\scripts\2_gamelib\tools.c:65
        // (vanilla: P:\scripts\3_game\dayzgame.c:1455)
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).Remove(this.DoSomethingRepeatedly);
    }
}

// CALL_CATEGORY_* constants (choose based on context):
// // P:\scripts\3_game\tools\tools.c:8-10
//   CALL_CATEGORY_SYSTEM   – ticks every update, always
//                            // P:\scripts\3_game\dayzgame.c:3026
//   CALL_CATEGORY_GUI      – client only (inside #ifndef NO_GUI); skipped while the
//                            loading / login-time screen is up; avoid for game logic
//                            // P:\scripts\3_game\dayzgame.c:3030, :3044
//   CALL_CATEGORY_GAMEPLAY – skipped while the mission is paused (mission.IsPaused())
//                            // P:\scripts\3_game\dayzgame.c:3007-3010, :3078-3080

// =============================================================================
// 2. Timer class
// =============================================================================
// Timer.Run's target is typed Managed, so the callback owner must extend Managed.
// // P:\scripts\3_game\tools\tools.c:595

class MyMod_TimerExample : Managed
{
    private ref Timer m_CooldownTimer;
    private bool      m_OnCooldown;

    void StartCooldown(float seconds)
    {
        m_OnCooldown = true;

        // Timer(int category = CALL_CATEGORY_SYSTEM) // P:\scripts\3_game\tools\tools.c:582
        // Run(float duration /*seconds*/, Managed obj, string fn_name, Param params = NULL, bool loop = false)
        // loop = false → one-shot, loop = true → repeat // P:\scripts\3_game\tools\tools.c:595
        if (!m_CooldownTimer)
            m_CooldownTimer = new Timer(CALL_CATEGORY_SYSTEM);

        m_CooldownTimer.Run(seconds, this, "OnCooldownExpired", null, false);
    }

    void OnCooldownExpired()
    {
        m_OnCooldown = false;
        // A one-shot Timer stops itself before calling back; the object is NOT
        // released, so keep the ref and reuse it on the next Run.
        // // P:\scripts\3_game\tools\tools.c:285-291
        Print("[MyMod] Cooldown expired");
    }

    bool IsOnCooldown()
    {
        return m_OnCooldown;
    }
}

// =============================================================================
// 3. OnCEIterate on an item
// =============================================================================
// Items have no OnScheduledTick. The vanilla per-item periodic hook is OnCEIterate,
// which the Central Economy calls on the server when it iterates entities;
// always call super first (vanilla doc comment).
// // P:\scripts\3_game\entities\entityai.c:3893-3904
// Unverified on P: (engine side): how often CE iterates, and whether items held in
// a player's inventory are included. elapsedTime is treated as seconds, matching
// its use in ItemBase.ProcessVariables // P:\scripts\4_world\entities\itembase.c:4659

// Its own class name: MyMod_CustomCanteen is already declared in 01_custom_item.c.
// Unverified on P: (compiler behaviour): that two plain class declarations with
// one name break the script compile; a distinct name avoids the question.
class MyMod_EvaporatingCanteen extends Bottle_Base // P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:7
{
    private float m_TickAccumulator;
    private static const float DECAY_INTERVAL = 30.0; // seconds between decay ticks

    // ---- Server-side tick ---------------------------------------------------
    override void OnCEIterate(float currentTime, float elapsedTime)
    {
        super.OnCEIterate(currentTime, elapsedTime);

        // IsServer() // P:\scripts\3_game\global\game.c:1120
        if (!GetGame().IsServer())
            return;

        m_TickAccumulator += elapsedTime;

        if (m_TickAccumulator >= DECAY_INTERVAL)
        {
            m_TickAccumulator = 0;
            MyMod_PeriodicDecay();
        }
    }

    private void MyMod_PeriodicDecay()
    {
        // Slowly reduce water quantity over time (simulates evaporation)
        // GetQuantity() // P:\scripts\4_world\entities\itembase.c:3486
        // SetQuantity(float value, ...) – server only // P:\scripts\4_world\entities\itembase.c:3315
        // Math.Max(float x, float y) // P:\scripts\1_core\proto\enmath.c:566
        float qty = GetQuantity();
        if (qty > 0)
            SetQuantity(Math.Max(0, qty - 1));
    }
}

// =============================================================================
// 4. Frame-skip pattern for expensive per-entity work
// =============================================================================
// When you MUST be in EOnFrame (visual updates, HUD), skip frames aggressively.
// EOnFrame only fires when EntityEvent.FRAME is in the event mask; PlayerBase sets it.
// // P:\scripts\1_core\proto\enentity.c:183 (EOnFrame), :701 (SetEventMask is proto native)
// // P:\scripts\4_world\entities\manbase\playerbase.c:366 (FRAME mask), :4605 (EOnFrame)
// For periodic player logic prefer PlayerBase.OnScheduledTick(float deltaTime), driven by
// MissionServer.TickScheduler (server) and MissionGameplay.TickScheduler (local player).
// // P:\scripts\4_world\entities\manbase\playerbase.c:3007
// // P:\scripts\5_mission\mission\missionserver.c:766-781, missiongameplay.c:225-230

modded class PlayerBase
{
    private int m_MyMod_FrameSkipCounter;
    private static const int MYMOD_SKIP_EVERY = 20; // process every 20th frame ≈ 1/s at 20 FPS

    override void EOnFrame(IEntity other, float timeSlice)
    {
        super.EOnFrame(other, timeSlice);

        // EOnFrame runs for every PlayerBase: on the server, and on each client for
        // every nearby player. HUD work belongs only to the locally controlled player,
        // the same guard vanilla uses before its effect-widget update.
        // // P:\scripts\4_world\entities\manbase\playerbase.c:4607-4610
        if (GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_CLIENT || !IsControlledPlayer())
            return;

        m_MyMod_FrameSkipCounter++;
        if (m_MyMod_FrameSkipCounter < MYMOD_SKIP_EVERY)
            return;

        m_MyMod_FrameSkipCounter = 0;
        MyMod_ExpensiveVisualUpdate(timeSlice * MYMOD_SKIP_EVERY);
    }

    private void MyMod_ExpensiveVisualUpdate(float effectiveDelta)
    {
        // e.g. update a custom HUD indicator based on player stats
    }
}

// =============================================================================
// 5. GetGame().GetTime() – mission-time reference point
// =============================================================================
// proto int GetTime() – "returns mission time in milliseconds"
// // P:\scripts\3_game\global\game.c:1533-1534
// Convert to seconds with * 0.001 (vanilla does the same: playerbase.c:3122-3123)

float MyMod_GetElapsedSinceStart()
{
    return GetGame().GetTime() * 0.001; // GetTime() returns milliseconds
}

// Example: record when a player last ate and gate eating cooldown
class MyMod_EatCooldownTracker
{
    private static const float COOLDOWN = 10.0; // 10 seconds
    // Start one cooldown in the past so CanEat() is true from mission start
    // (a 0 default would block eating for the first COOLDOWN seconds).
    // Member initialised from a const: vanilla does it at
    // // P:\scripts\4_world\classes\contaminatedarea\spookyareamisc.c:206
    // Unverified on P: a unary minus on a const in a member initialiser.
    private float m_LastEatTime = -COOLDOWN;

    bool CanEat()
    {
        float now = GetGame().GetTime() * 0.001;
        return (now - m_LastEatTime) >= COOLDOWN;
    }

    void RecordEat()
    {
        m_LastEatTime = GetGame().GetTime() * 0.001;
    }
}
