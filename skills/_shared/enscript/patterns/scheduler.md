# Pattern: scheduler & periodic ticks

`CallLater`, `Timer`, and `OnUpdate`-style callbacks are the engine's three ways to run code on a schedule. Two traps are reported for long running mods: `CallLater` drifting after hours, which is not verified, and per tick allocation, which is.

See also: `examples/09_scheduler_timer.c` for full `CallLater`/`Timer`/`OnScheduledTick` patterns with frame-skip guards.

---

## Unverified: `CallLater` drifting after about 4.5 hours

A repeating `CallLater` is reported to drift or stall after about 4.5 hours of uptime, with a 32 bit float due time given as the cause. This cannot be checked on `P:\`: `ScriptCallQueue.CallLater` is `proto` (engine code) and takes its delay as an `int` of milliseconds (`P:\scripts\2_gamelib\tools.c:61`). Treat it as a rumour, not a rule.

For long lived recurring work, a `Timer` is the scripted alternative. `TimerBase` (`P:\scripts\3_game\tools\tools.c:219`) keeps its own elapsed time, and `Timer` (`:576`) adds `Run(duration, obj, fn_name, params, loop)` (`:595`).

```c
// AVOID for long-lived recurring work
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(this.Tick, 1000, true);

// A Timer is scripted, so its timing can be read in tools.c
ref Timer m_Tick = new Timer(CALL_CATEGORY_GAMEPLAY);
m_Tick.Run(1.0, this, "Tick", null, true);
```

The reported symptom is callbacks that fired correctly for hours and then skip, or fire many times back to back. If you see it, compare a `Timer` before you change anything else.

The report rests on logs from long-running production servers that are not in this repo, so it stays unverified here. There is a second way out for work that must keep time across many hours: have one manager object decide when work is due from the system clock, not from an accumulated delay. The clock calls are vanilla: `GetHourMinuteSecond(out int hour, out int minute, out int second)` (`P:\scripts\1_core\proto\ensystem.c:28`) and `GetYearMonthDay(out int year, out int month, out int day)` (`ensystem.c:52`).

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

## Reported traps with scheduled calls

Third-party mod behaviour, measured in game and not checked on `P:\`, because the call queue is native (`CallLater` is `proto`, `P:\scripts\2_gamelib\tools.c:61`):

- **In a one-shot `CallLater`, the callback is the deadline.** A callback that checks the clock again (`GetTickTime() >= armTime`) can miss by a few milliseconds on the frame it fires, and a one-shot never runs again. Inside the callback check only state (armed, not started), not time.
- **A sleeping entity gets no `EOnSimulate`.** An idle vehicle falls asleep within a few ticks, and a countdown that lives in `EOnSimulate` stops with it. Put timed logic for such an entity on the call queue.
- **A manager's repeating call can outlive the manager.** When a singleton is reset on reconnect and its `Remove()` is in the destructor of the dropped instance, the queue keeps calling the dead object. For client maintenance ticks, count `timeslice` up in the mission's `OnUpdate` and fetch the singleton each frame, so nothing is registered. Set the counter to zero when it fires instead of subtracting the period, so a long hitch fires once.
- **Give each fix its own log line.** Without one, "the fix was not compiled in" and "the fix was not enough" look the same after a rebuild.
- **A `CallLater` that queues itself again from inside its own callback stopped after the first step on a 1.29 diag client**, with no error in the log; the same call made from outside the queue worked. A `Timer` with `loop` set, stopped with `Stop()` when the chain is done, ran every step. The same chain was not reproduced on a retail 1.30.164289 server, where both `CALL_CATEGORY_SYSTEM` and `CALL_CATEGORY_GAMEPLAY` chains ran all six steps. If a self re-queuing chain dies silently on a client, switch it to a `Timer`.
- **One repeating `CallLater` per device does not scale.** A power grid mod saw heap fragmentation and an "Illegal write" crash after hours with about a hundred devices each holding its own repeating call. Run one `Timer` in a manager and loop over a registered array of devices instead; `server_tick_budget.md` shows how to cap and spread that loop.

Detail: `skills/enforce-script-reference/references/runtime-traps.md` and, for server load, `skills/enforce-script-reference/references/server-performance.md`.

---

## Call categories

When using `CallLater` and `Timer`, the call-category controls which queue the callback drains from. Pick the right one — mismatched category means callbacks pause when the corresponding queue is paused.

| Category | Use for |
|---|---|
| `CALL_CATEGORY_SYSTEM` | Engine-side maintenance; rarely correct for mod code |
| `CALL_CATEGORY_GUI` | HUD / menu / widget updates |
| `CALL_CATEGORY_GAMEPLAY` | Game logic (default for most mod work) |
