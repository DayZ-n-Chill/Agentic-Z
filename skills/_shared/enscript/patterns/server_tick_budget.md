# Pattern: keeping periodic server work inside the tick

How to stop many entities from doing the same expensive work on the same server tick: a work budget, staggering, backoff, events in place of polling, and compile-time side gates. The techniques are measured in third-party mods (Expansion's AI and a power grid mod), so they are marked as reported; the vanilla calls they are built from were opened on `P:\`. The full write-up with the quoted Expansion code is `skills/enforce-script-reference/references/server-performance.md`.

See also: `scheduler.md` (timers and per tick allocation) and `../references/api_scheduling.md` (call categories and queues).

---

## The problem

A dedicated server advances the world on one simulation thread, so every entity that wants periodic work shares the same tick. Two shapes of work cause most of the trouble (reported from an audit of the power grid mod):

- **Work that grows with the square of the population and fires often.** That mod's self-heal walked its whole device list five times per run, each walk scanning the list again. The fix was structural: fetch the list once and pass it to the helpers, and replace `outArr.Find(ent)` de-duplication with a `map` of seen items.
- **Log strings built whether or not they are printed.** A string that is concatenated on every tick costs its time even when the log level drops it. Put the level test around the concatenation, not only around the `Print`.

---

## One manager, one tick, a budget

Run all periodic work from one manager that owns one `Timer` (`P:\scripts\3_game\tools\tools.c:576`) or one mission update, with a register and unregister call for the entities. Then cap how many entities it advances per tick and resume from a saved cursor on the next tick. The worst tick then costs the budget, whatever the population; an entity may wait a few ticks for its turn.

```c
class MyMod_TickScheduler
{
    protected ref array<EntityAI> m_Registered = new array<EntityAI>;
    protected int m_Cursor;                          // where the next tick resumes
    protected const int WORK_BUDGET_PER_TICK = 32;   // tune to the measured frame time

    void OnTick(float dt)
    {
        int n = m_Registered.Count();
        if (n == 0)
            return;

        int processed = 0;
        while (processed < WORK_BUDGET_PER_TICK && processed < n)
        {
            if (m_Cursor >= n)
                m_Cursor = 0;

            EntityAI e = m_Registered[m_Cursor];
            if (e)
                DoWork(e, dt);

            m_Cursor++;
            processed++;
        }
    }

    void DoWork(EntityAI e, float dt) {}
}
```

A budget limits cost but does not promise that every item is reached. If a priority pass (nearest first, most urgent first) restarts from the same end every tick, it can use the whole budget each time and starve the tail. Keep the rotating cursor as member state, reserve at least one slot per tick for it, advance it even when the chosen item had nothing to do, and read the count again each tick because the list changes.

---

## Staggering

Do not let every entity do its expensive step on the same tick.

- **Modulo gate.** Run entity `i` only when `(tickCounter + i) % N == 0`. One entity in `N` runs per tick, at a fixed cadence.
- **Random jitter.** Add a small random part to each entity's interval, for example `Math.RandomFloat(0.1, 0.2)` seconds (`RandomFloat`, `P:\scripts\1_core\proto\enmath.c:91`). Entities that all registered at server start then drift apart. Expansion's AI uses this for its target scan and its caches (reported).
- **One item per tick.** Walk a long list one index per tick and start again only when the index reaches the end.

---

## Backoff

When nothing relevant is near an entity, stretch its interval; do not switch it off. It still runs, just less often, and returns to the base rate as soon as something relevant appears. Expansion's AI multiplies the interval by five while no player is within the unit's visibility range (reported). A growing backoff needs a cap, so an idle entity still notices when it becomes relevant:

```c
protected float m_Backoff = 1.0;
protected const float BACKOFF_MAX = 8.0;

float NextInterval(float baseInterval, bool sawSomethingRelevant)
{
    if (sawSomethingRelevant)
        m_Backoff = 1.0;
    else
        m_Backoff = Math.Min(m_Backoff * 2.0, BACKOFF_MAX);

    return baseInterval * m_Backoff;
}
```

The same idea scales an interval with load: keep a running average of the frame time and multiply the base interval by `average / reference` when that ratio is above 1.

---

## Events before polling

The cheapest scan is the one that never runs. Where changes are rare compared with ticks (a device moved, a wire cut, a player joined), let the producer tell the consumers: `ScriptInvoker` (`P:\scripts\2_gamelib\tools.c:115`) has `Insert` (`P:\scripts\2_gamelib\tools.c:120`), `Remove` (`P:\scripts\2_gamelib\tools.c:122`) and `Invoke` (`P:\scripts\2_gamelib\tools.c:118`). Add a debounce (the power grid mod waits 500 ms after the last change) when one change tends to be followed by more.

Every `Insert` needs a matching `Remove` in the consumer's destructor, with a null check on the invoker (`singleton.md`, "`ScriptInvoker` shutdown null-guard"). When the value changes on every tick anyway, read it directly; an invoker fired every tick only adds the fan-out.

---

## Compile-time gate or runtime check

- `#ifdef SERVER` removes the code from the client build, so it costs the client nothing. Use it for whole subsystems that only a dedicated server runs. `SERVER` is not defined in single player (`../references/language_compile.md`).
- `IsServer()` and `IsDedicatedServer()` (`P:\scripts\3_game\global\game.c:1120`, `:1125`) are runtime branches for code that runs on both sides. Do not wrap a per tick hot path in a runtime check when a compile-time gate around the subsystem would remove the branch.
- `#ifndef SERVER` around a class removes the type from the dedicated server. Reported from the power grid mod: another mod that named the hidden class then failed on the server with `Unknown type`, and the server did not start. If another mod or a server handler can name the type, leave an empty stub in the server build (`modded_class.md`, "Server-only overrides need a stub in the base class"), and compile both the dedicated server view and the client view before a release.

---

## What lowers server script memory

Measured in the power grid mod on a dedicated server (static script memory of the World module, in kB; not re-run here):

| Lever | Result |
|---|---|
| Merging or repackaging files under `4_World` | 0 kB |
| Removing comments and whitespace | about 0 kB |
| Removing a few dead classes | 0 kB at that scale |
| `#ifndef SERVER` around client only code | Lowers it |
| Using one generic specialization (`array<EntityAI>` plus a cast) where many were used | Lowers it |

Before a "remove dead code" pass, measure how much of the code is already inside `#ifndef SERVER`: in that mod a UI fork that looked like 182 KB of savings had about 5.5 KB compiled on the server. Measure each change against a baseline in the same boot, twice; the noise was 1 kB.
