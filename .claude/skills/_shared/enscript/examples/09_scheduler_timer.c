// =============================================================================
// MyMod_Scheduler.c
// Demonstrates every timing / scheduling mechanism available in Enforce Script:
//
//   1. CallLater        – one-shot and repeating, on GetCallQueue
//   2. Timer class      – start/stop object, one-shot or repeat
//   3. OnScheduledTick  – server-side per-entity tick on ItemBase / PlayerBase
//   4. GetGame().GetTime() – real elapsed seconds since server start
//   5. GetGame().GetTickTime() – delta since last frame (use in OnScheduledTick)
//   6. Avoiding excessive per-frame work with frame skipping
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

        // ---- With arguments (up to 9 Param slots via Param1..Param9) --------
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLaterByName(
            this, "DoSomethingWithArgs", 1000, false, "hello", 42
        );
    }

    void DoSomethingOnce()
    {
        Print("[MyMod] One-shot fired");
    }

    void DoSomethingRepeatedly()
    {
        Print("[MyMod] Repeating tick");
    }

    void DoSomethingWithArgs(string msg, int val)
    {
        Print(string.Format("[MyMod] msg=%1 val=%2", msg, val));
    }

    // ---- Cancel a repeating CallLater before the object is destroyed --------
    void Cleanup()
    {
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).Remove(this.DoSomethingRepeatedly);
    }
}

// CALL_CATEGORY_* constants (choose based on context):
//   CALL_CATEGORY_SYSTEM   – engine frame; most reliable
//   CALL_CATEGORY_GAMEPLAY – paused when game-time pauses
//   CALL_CATEGORY_GUI      – only runs when UI is up; avoid for game logic

// =============================================================================
// 2. Timer class
// =============================================================================

class MyMod_TimerExample
{
    private ref Timer m_CooldownTimer;
    private bool      m_OnCooldown;

    void StartCooldown(float seconds)
    {
        m_OnCooldown = true;

        // Timer takes (EventType, callback_object, priority)
        // SLT_REPEAT or SLT_NORMAL (one-shot)
        m_CooldownTimer = new Timer(CALL_CATEGORY_SYSTEM);
        m_CooldownTimer.Run(seconds, this, "OnCooldownExpired", null, false);
    }

    void OnCooldownExpired()
    {
        m_OnCooldown = false;
        // m_CooldownTimer is auto-released (SLT_NORMAL = one-shot)
        m_CooldownTimer = null;
        Print("[MyMod] Cooldown expired");
    }

    bool IsOnCooldown()
    {
        return m_OnCooldown;
    }
}

// =============================================================================
// 3. OnScheduledTick on ItemBase
// =============================================================================
// Called every EOnFrame (continuous) or at the item's tick interval.
// For heavy logic prefer OnScheduledTick over EOnFrame to avoid per-frame cost.

modded class MyMod_CustomCanteen
{
    private float m_TickAccumulator;
    private static const float DECAY_INTERVAL = 30.0; // seconds between decay ticks

    // Opt in to receiving EOnInit so we can set the tick interval
    override void SetEventMask(int mask)
    {
        super.SetEventMask(mask | EntityEvent.INIT);
    }

    override void EOnInit(IEntity other, int extra)
    {
        super.EOnInit(other, extra);
        // Set server-side scheduled tick interval (seconds)
        SetSynchDirty();
    }

    // ---- Server-side tick ---------------------------------------------------
    // deltaTime: seconds since last invocation (NOT raw frame delta)
    override void OnScheduledTick(float deltaTime)
    {
        super.OnScheduledTick(deltaTime);

        if (!GetGame().IsServer())
            return;

        m_TickAccumulator += deltaTime;

        if (m_TickAccumulator >= DECAY_INTERVAL)
        {
            m_TickAccumulator = 0;
            MyMod_PeriodicDecay();
        }
    }

    private void MyMod_PeriodicDecay()
    {
        // Slowly reduce water quantity over time (simulates evaporation)
        float qty = GetQuantity();
        if (qty > 0)
            SetQuantity(Math.Max(0, qty - 1));
    }
}

// =============================================================================
// 4. Frame-skip pattern for expensive per-entity work
// =============================================================================
// When you MUST be in EOnFrame (visual updates, HUD), skip frames aggressively.

modded class PlayerBase
{
    private int m_MyMod_FrameSkipCounter;
    private static const int SKIP_EVERY = 20; // process every 20th frame ≈ 1/s at 20 FPS

    override void EOnFrame(IEntity other, float timeSlice)
    {
        super.EOnFrame(other, timeSlice);

        m_MyMod_FrameSkipCounter++;
        if (m_MyMod_FrameSkipCounter < SKIP_EVERY)
            return;

        m_MyMod_FrameSkipCounter = 0;
        MyMod_ExpensiveVisualUpdate(timeSlice * SKIP_EVERY);
    }

    private void MyMod_ExpensiveVisualUpdate(float effectiveDelta)
    {
        // e.g. update a custom HUD indicator based on player stats
    }
}

// =============================================================================
// 5. GetGame().GetTime() – wall-clock reference point
// =============================================================================
// Returns float seconds since server start. Used for absolute timestamps.

float MyMod_GetElapsedSinceStart()
{
    return GetGame().GetTime() * 0.001; // GetTime() returns milliseconds
}

// Example: record when a player last ate and gate eating cooldown
class MyMod_EatCooldownTracker
{
    private float m_LastEatTime;
    private static const float COOLDOWN = 10.0; // 10 seconds

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
