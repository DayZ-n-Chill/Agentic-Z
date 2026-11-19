# Timers and the central tick

How `CallLater` and `Timer` behave over long uptimes, the reports against `CallLater`, and how to run many periodic devices from one tick. The call categories and queues themselves are in `../references/api_scheduling.md` and the short pattern in `../patterns/scheduler.md`; profiling and hot path fixes are in `script-profiling.md`.

## `CallLater`

`CallLater` runs a callback after a delay in milliseconds, once or repeating, with up to nine arguments (`P:\scripts\2_gamelib\tools.c:61`); `Remove` cancels it (`:65`).

```c
// once, after 5 seconds
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 5000, false);

// every 3 seconds
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 3000, true);

// with arguments
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 5000, false, param1, param2);

// cancel
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(MyCallback);
```

The three categories, with the vanilla comments (`P:\scripts\3_game\tools\tools.c:8` to `:10`):

| Category | Vanilla comment | In practice |
|---|---|---|
| `CALL_CATEGORY_SYSTEM` | "Runs always" | Also ticks while loading |
| `CALL_CATEGORY_GUI` | "Runs always (on client)" | Never ticks on a dedicated server |
| `CALL_CATEGORY_GAMEPLAY` | "Runs unless ingame menu is opened" | Ticks only while a mission runs and is not paused, so not while loading (`../references/api_scheduling.md`) |

## A `CallLater` that queues itself again

On the 1.29 diag client, a `CallLater` queued again from inside its own callback never fired a second time: the chain died after its first step with no RPT error, while the same call made from outside the queue worked. The same chain on a `Timer` ran all its steps.

On the 1.30 dedicated server this does not happen. Two chains that queue themselves again with `CallLater(fn, 500, false, ...)`, one on `CALL_CATEGORY_SYSTEM` and one on `CALL_CATEGORY_GAMEPLAY`, both ran all six steps. The first step fired 14.3 s after `OnMissionStart` in both categories, the rest about 0.5 s apart. Both results are measured in game.

On a client, or wherever a chain must not die, use `Timer(CALL_CATEGORY_GAMEPLAY).Run(seconds, this, "fn", null, true)` and call `Stop()` when the work is done.

## The reported loss of precision after hours

A report says that after about 4.5 hours of server uptime, `CallLater` intervals drift: callbacks set for every 5 s fire every 7, 10, then 15 s, some stop firing after 8 hours, and every mod with `repeat=true` is affected. The cause it gives is time held as a 32 bit float, which can't hold every whole number above 16,777,216 (2 to the 24th). It is reported as still present from DayZ 1.28 on.

This can't be checked on `P:\`: `CallLater` is a `proto` with no script body and takes its delay as an `int` of milliseconds (`P:\scripts\2_gamelib\tools.c:61`). Treat it as unverified (`hard-rules.md`, section "Timers"). The workarounds the report gives:

1. Restart the server every 3 to 4 hours.
2. Use `Timer`, which keeps its own clock.
3. Count frames or `timeslice` in `OnUpdate` and fire when a threshold is reached.

## `Timer`

`Timer` is script, so its clock can be read. Each timer adds the frame's `timeslice` to its own `m_time` (`P:\scripts\3_game\tools\tools.c:277`) and never compares against the absolute uptime, which is why it is reported free of the drift above. `Timer` is declared at `:576` and `Run(float duration, Managed obj, string fn_name, Param params = NULL, bool loop = false)` at `:595`.

```c
class MyMod_Manager
{
    ref Timer m_Timer;

    void Start()
    {
        m_Timer = new Timer(CALL_CATEGORY_GAMEPLAY);
        m_Timer.Run(5.0, this, "OnTick", null, true);  // every 5 s
    }

    void Stop()
    {
        if (m_Timer)
            m_Timer.Stop();
    }

    void OnTick()
    {
    }
}
```

A `Timer` is a full object, so it costs more memory than a queued call. A few are fine; for a hundred devices, use one central tick instead.

## One central tick for many devices

Run every periodic device tick from one manager that devices register with (`hard-rules.md`, section "Timers").

```c
class MyMod_DeviceManager
{
    ref Timer m_GlobalTimer;
    ref array<MyMod_Device> m_Devices = new array<MyMod_Device>;

    void StartGlobalTick()
    {
        m_GlobalTimer = new Timer(CALL_CATEGORY_GAMEPLAY);
        m_GlobalTimer.Run(5.0, this, "OnGlobalTick", null, true);
    }

    void Register(MyMod_Device dev)
    {
        if (m_Devices.Find(dev) < 0)
            m_Devices.Insert(dev);
    }

    void Unregister(MyMod_Device dev)
    {
        int idx = m_Devices.Find(dev);
        if (idx >= 0)
            m_Devices.Remove(idx);
    }

    void OnGlobalTick()
    {
        int count = m_Devices.Count();
        for (int i = 0; i < count; i++)
        {
            MyMod_Device dev = m_Devices[i];
            if (dev)
                dev.OnDeviceTick();
        }
    }
}
```

Why not one repeating `CallLater` per device: each repeating call holds its own queue entry, and a hundred of them fragment the heap. Reported from a long running production server, not checked on `P:\`: after hours it ends in an "Illegal write" crash. One timer walking an array has no such cost.

Creating a `new ScriptRPC()` per message is fine, because each one is used up by `Send` and nothing piles up.

A larger version with a work budget per tick, staggering and backoff is in `../patterns/server_tick_budget.md` and `server-performance.md`.
