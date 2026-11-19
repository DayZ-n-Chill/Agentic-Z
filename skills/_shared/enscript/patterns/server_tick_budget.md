# Keeping periodic server work inside the tick

How to stop many entities from doing the same expensive work on the same server tick: a work budget, staggering, backoff, events in place of polling, and compile time side gates. The techniques come from third-party mods (Expansion's AI and a power grid mod) and are marked as reported; the vanilla calls they use are cited. The longer version is `../depth/server-performance.md`; timers and allocation in a tick are in `scheduler.md`, call categories and queues in `../references/api_scheduling.md`.

## Where the time goes

A dedicated server advances the world on one simulation thread, so every entity that wants periodic work shares the same tick. Two shapes of work cause most of the trouble (reported from the power grid mod):

- Work that grows with the square of the population and runs often. That mod's self repair walked its whole device list five times per run, each walk scanning the list again. The fix is structural: fetch the list once and pass it to the helpers, and replace `outArr.Find(ent)` de-duplication with a `map` of items already seen.
- Log strings built whether or not they are printed. A string joined on every tick costs its time even when the log level drops it. Put the level test around the string building, not only around the `Print`.

## One manager, one tick, a budget

Run all periodic work from one manager that owns one `Timer` (`P:\scripts\3_game\tools\tools.c:576`) or one mission update, with a register and unregister call for the entities. Cap how many entities it advances per tick, and resume from a saved cursor on the next tick. The worst tick then costs the budget, whatever the population; an entity may wait a few ticks for its turn.

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

A budget limits cost but doesn't promise every item is reached. A priority pass (nearest first, most urgent first) that restarts from the same end every tick can use the whole budget each time and starve the tail. Keep the rotating cursor as member state, reserve at least one slot per tick for it, advance it even when the chosen item had nothing to do, and read the count again each tick because the list changes.

## Staggering

Don't let every entity do its expensive step on the same tick.

- Modulo gate: run entity `i` only when `(tickCounter + i) % N == 0`. One entity in `N` runs per tick, at a fixed rate.
- Random jitter: add a small random part to each entity's interval, for example `Math.RandomFloat(0.1, 0.2)` seconds (`RandomFloat`, `P:\scripts\1_core\proto\enmath.c:91`). Entities that all registered at server start then drift apart. Expansion's AI does this for its target scan and its caches (reported).
- One item per tick: walk a long list one index per tick, and start again only when the index reaches the end.

## Backoff

When nothing relevant is near an entity, stretch its interval rather than switching it off. It still runs, less often, and returns to the base rate as soon as something relevant appears. Expansion's AI multiplies the interval by five while no player is within the AI's visibility range (reported). A growing backoff needs a cap, so an idle entity still notices when it becomes relevant:

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

## Events before polling

The cheapest scan is the one that never runs. Where changes are rare compared with ticks (a device moved, a wire cut, a player joined), let the producer tell the consumers. `ScriptInvoker` (`P:\scripts\2_gamelib\tools.c:115`) has `Invoke` (`:118`), `Insert` (`:120`) and `Remove` (`:122`). Add a debounce when one change tends to be followed by more; the power grid mod waits 500 ms after the last change.

Every `Insert` needs a matching `Remove` in the consumer's destructor, with a null check on the invoker (`singleton.md`, section "Static `ScriptInvoker` shutdown crash"). When the value changes on every tick anyway, read it directly; an invoker fired every tick only adds the fan out.

## Compile time gate or run time check

- `#ifdef SERVER` removes the code from the client build, so it costs the client nothing. Use it for whole subsystems that only a dedicated server runs. `SERVER` is not defined in single player (`../references/language_compile.md`).
- `IsServer()` and `IsDedicatedServer()` (`P:\scripts\3_game\global\game.c:1120` and `:1125`) are run time branches for code that runs on both sides. Don't put a run time check inside a hot path that runs every tick when a compile time gate around the subsystem would remove the branch.
- `#ifndef SERVER` around a class removes the type from the dedicated server. Reported from the power grid mod: another mod that named the hidden class then failed on the server with `Unknown type`, and the server didn't start. If another mod or a server handler can name the type, leave an empty stub in the server build (`modded_class.md`, section "Server-only overrides need a stub in the base class"), and compile both the server and the client view before a release.

What does and doesn't shrink a script module's memory is in `../references/script_module_arena.md`.
