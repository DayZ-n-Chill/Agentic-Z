# Pattern: scheduler & periodic ticks

`CallLater`, `Timer`, and `OnUpdate`-style callbacks are the engine's three ways to run code on a schedule. Two non-obvious traps bite production mods: the `CallLater` long-run precision loss, and per-tick allocation GC pressure.

See also: `examples/09_scheduler_timer.c` for full `CallLater`/`Timer`/`OnScheduledTick` patterns with frame-skip guards.

---

## ⚠️ `CallLater` loses precision after ~4.5 hours of game time

The engine's `CallLater` uses a 32-bit float for the absolute due time. Beyond ~4.5h of elapsed game time, that float saturates and callback timing drifts or stalls entirely.

```c
// AVOID for long-lived recurring work
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(this.Tick, 1000, true);

// PREFER — Timer class plus periodic resync, or a Manager singleton driving
// timestamps off SystemTime / DateTime to escape the float-window.
ref Timer m_Tick = new Timer(CALL_CATEGORY_GAMEPLAY);
m_Tick.Run(1.0, this, "Tick", null, true);
```

Symptom in logs: callbacks that fired correctly for hours suddenly skip or fire many times back-to-back as the float resaturates. Verified via long-run production server logs.

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
