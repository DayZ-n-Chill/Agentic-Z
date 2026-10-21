# Pattern: scheduler & periodic ticks

`CallLater`, `Timer`, and `OnUpdate`-style callbacks are the engine's three ways to run code on a schedule. Two traps are reported for long running mods: `CallLater` drifting after hours, which is not verified, and per tick allocation, which is.

See also: `examples/09_scheduler_timer.c` for full `CallLater`/`Timer`/`OnScheduledTick` patterns with frame-skip guards.

---

## Unverified: `CallLater` drifting after about 4.5 hours

Some modders report that a repeating `CallLater` drifts or stalls after about 4.5 hours of uptime, and blame a 32 bit float due time. This cannot be checked on `P:\`: `ScriptCallQueue.CallLater` is `proto` (engine code) and takes its delay as an `int` of milliseconds (`P:\scripts\2_gamelib\tools.c:61`). Treat it as a rumour, not a rule.

For long lived recurring work, a `Timer` is the scripted alternative. `TimerBase` (`P:\scripts\3_game\tools\tools.c:219`) keeps its own elapsed time, and `Timer` (`:576`) adds `Run(duration, obj, fn_name, params, loop)` (`:595`).

```c
// AVOID for long-lived recurring work
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(this.Tick, 1000, true);

// A Timer is scripted, so its timing can be read in tools.c
ref Timer m_Tick = new Timer(CALL_CATEGORY_GAMEPLAY);
m_Tick.Run(1.0, this, "Tick", null, true);
```

The reported symptom is callbacks that fired correctly for hours and then skip, or fire many times back to back. If you see it, compare a `Timer` before you change anything else.

---

## ⚠️ Per-tick allocation kills perf

In any function called every tick (`OnUpdate`, `OnPostFrameUpdate`, repeating `CallLater`/`Timer` callback), allocating arrays / maps / `Param` objects creates GC pressure that compounds:

```c
// BAD — allocates every tick, GC churn
override void OnUpdate(float dt)
{
    array<Object> nearby = new array<Object>;
    GetGame().GetObjectsAtPosition(GetPosition(), 10.0, nearby, null);
    // ...
}

// GOOD — allocate once, .Clear() every tick
ref array<Object> m_NearbyBuf = new array<Object>;

override void OnUpdate(float dt)
{
    m_NearbyBuf.Clear();
    GetGame().GetObjectsAtPosition(GetPosition(), 10.0, m_NearbyBuf, null);
    // ...
}
```

The engine's GC is aggressive on function-scope refs; high-frequency `new` inside ticks shows up as periodic frame-time spikes in the diag profiler.

Rule of thumb: anything inside a function that fires more than once per second should own its working buffers as member fields and `.Clear()` them rather than reallocate.

---

## Call categories

When using `CallLater` and `Timer`, the call-category controls which queue the callback drains from. Pick the right one — mismatched category means callbacks pause when the corresponding queue is paused.

| Category | Use for |
|---|---|
| `CALL_CATEGORY_SYSTEM` | Engine-side maintenance; rarely correct for mod code |
| `CALL_CATEGORY_GUI` | HUD / menu / widget updates |
| `CALL_CATEGORY_GAMEPLAY` | Game logic (default for most mod work) |
