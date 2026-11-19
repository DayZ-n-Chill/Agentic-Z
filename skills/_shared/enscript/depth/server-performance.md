# Server tick budget

How to keep many entities inside one server tick: a work budget per tick that stays fair, intervals that stretch with load, scans spread across ticks, and backoff for idle entities. Compile-time gates, event buses and script memory are in `server-side-gates.md`.

The examples come from two sources, neither vanilla. Snippets labelled Expansion are from the third-party DayZ Expansion AI module, read in its scripts from before DayZ 1.30 and not on `P:\`; check the current Expansion scripts before relying on a detail. The same ideas written for your own AI are in `_shared/ai/design-ideas.md`. Measurements are from a large mod's dedicated server with a device registry, wire propagation and per-device diagnostics. Other snippets are skeletons to adapt.

## What eats the tick

A dedicated server advances the world on one simulation thread, so every entity with periodic work (self-heal, target scans, line of sight, visual sync, wire propagation) competes for the same tick. Two shapes do most of the damage, measured on that server:

- Quadratic work on a frequent event. A "validate all wires and propagate" routine walked the whole registry five times per self-heal, each pass quadratic in registry size, and the self-heal ran 500 ms after any device move or cut. Fetch the device list once and pass it into the rebuild helpers, which removed three of the five passes, and replace an `outArr.Find(ent)` duplicate check with a map of seen entities.
- Diagnostics that are always on. Per-node power diagnostic strings and a log line per validation tick were built and printed for every dirty node at the production log level. A string concatenated unconditionally costs even when the log level throws it away, so gate the concatenation, not just the `Print`.

## A work budget per tick

A central scheduler gives each tick a budget, advances only as many entities as fit, and resumes there next tick. The worst tick then costs at most the budget, whatever the population, at the price of an entity sometimes waiting a few ticks. This is the single tick manager from `hard-rules.md`, section "Timers", with a cap. Expansion switches its whole AI population into this mode once it passes a threshold, through the global flag `s_eAI_FTO`.

```c
class MyMod_TickScheduler
{
    protected ref array<EntityAI> m_Registered = new array<EntityAI>;
    protected int m_Cursor;
    protected const int MYMOD_BUDGET_PER_TICK = 32;   // tune to measured frame time

    void OnTick(float dt)
    {
        int n = m_Registered.Count();
        int processed = 0;
        while (processed < MYMOD_BUDGET_PER_TICK && processed < n)
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
}
```

A budget limits cost but does not promise coverage. A pass that serves the nearest or most urgent items first, restarting from the same end every tick, can spend the whole budget each time and starve the rest. For each independently scheduled group:

1. Keep a rotating cursor as member state, set up outside the tick.
2. Reserve at least one slot of the budget for cursor-driven work; the priority pass must not use that slot or reset the cursor.
3. Advance the cursor even when the chosen item produces nothing, so one ineligible item cannot pin the group.
4. Read the group's count every tick and wrap the cursor with `% count`, since membership and order change.
5. Measure how many samples each item gets, or its maximum age. An item at the tail with no samples is starving even while the scheduler stays inside budget.

## Intervals that stretch with load

When the server has headroom, work at the base rate; when frame time grows, stretch the interval so the work per real second stays the same. Expansion does this for line of sight:

```c
// Expansion AI, eAIBase.c
if (s_eAI_FTO < 2)
    interval = LOS_CHECK_INTERVAL;
else
    interval = LOS_CHECK_INTERVAL * (pDt / ExpansionWorld.AI_UPDATE_INTERVAL);
if (m_eAI_LOSCheckDT >= interval)
    m_eAI_LOSCheckDT = 0;
m_eAI_LOSCheckDT += pDt;
if (m_eAI_LOSCheckDT < interval && !m_eAI_TargetChanged)
    return state.m_LOS;   // cached result, no raycast this tick
```

When the scheduler stretches `pDt` to five times the base, the line of sight interval stretches five times too, so an AI updated at a fifth of the rate does not check five times as often per update. Setting `m_eAI_TargetChanged` forces a fresh check, for transitions where correctness matters.

Judge load from an average, not a single spike:

```c
protected float m_DtAvg;
protected const float MYMOD_DT_SMOOTH = 0.1;   // smaller is smoother and slower

void AccumulateDt(float dt)
{
    m_DtAvg = m_DtAvg * (1.0 - MYMOD_DT_SMOOTH) + dt * MYMOD_DT_SMOOTH;
}

float AdaptiveInterval(float baseInterval, float refDt)
{
    float scale = m_DtAvg / refDt;
    if (scale < 1.0)
        scale = 1.0;   // never faster than the base rate
    return baseInterval * scale;
}
```

A fixed throttle is the same idea with a constant: physics runs every tick while dials and HUD values update 10 times a second (`vehicle-script-helpers.md`).

## Spreading scans across ticks

Never let the whole population do the same expensive thing on the same tick.

Advance one item per tick and refresh fully only when the list is used up. Expansion's target scan does this, with a random wait:

```c
// Expansion AI, eAIBase.c
m_eAI_UpdateTargetsTick += pDt;
if (m_eAI_CurrentPotentialTargetIndex >= m_eAI_PotentialTargetEntities.Count() && m_eAI_UpdateTargetsTick > Math.RandomFloat(0.1, 0.2))
{
    m_eAI_UpdateTargetsTick = 0;
    m_eAI_CurrentPotentialTargetIndex = 0;
```

The random wait, `Math.RandomFloat` (`P:\scripts\1_core\proto\enmath.c:91`), keeps AI spawned on the same frame from finishing their scans on the same later frame. Expansion uses the same jitter for its threat cache (`Math.RandomIntInclusive(250, 300)`, `enmath.c:54`) and formation cache (`Math.RandomFloat(2.0, 4.0)`).

Or run each entity once every N ticks, offset by its index:

```c
protected int m_TickCounter;

void OnTick()
{
    m_TickCounter++;
    for (int i = 0; i < m_Registered.Count(); i++)
    {
        if ((m_TickCounter + i) % MYMOD_SCAN_STRIDE == 0)
            DoScan(m_Registered[i]);
    }
}
```

The index offset gives a fixed cadence; random jitter gives a spread when a fixed phase would still cluster, as with entities that all register at server start. Strongest of all is doing the work only when something changes, such as the self-heal that runs 500 ms after a move or cut event (`server-side-gates.md`, section "Events instead of polling").

## Backoff for idle entities

When nothing relevant is near, stretch an entity's interval instead of switching it off; it still runs and snaps back when something arrives. Expansion uses a flat factor of five, decided by each AI for itself:

```c
// Expansion AI, ExpansionWorld.c
if (eAIBase.s_eAI_FTO >= 2 && ai.m_eAI_PlayersWithinVisibilityDistanceLimit.Count() == 0)
    updateIntervalCurrent = AI_UPDATE_INTERVAL * 5;   // about 50 ms becomes 250 ms
else
    updateIntervalCurrent = updateInterval;
```

A server with 200 idle bots and 3 engaged ones pays full rate for 3 and a fifth for 200. A growing backoff with a cap:

```c
protected float m_Backoff = 1.0;
protected const float MYMOD_BACKOFF_MAX = 8.0;

float NextInterval(float baseInterval, bool sawSomethingRelevant)
{
    if (sawSomethingRelevant)
        m_Backoff = 1.0;
    else
        m_Backoff = Math.Min(m_Backoff * 2.0, MYMOD_BACKOFF_MAX);
    return baseInterval * m_Backoff;
}
```

`Math.Min` is at `enmath.c:553`. Cap the growth so an idle entity still notices when it matters again. A fixed factor is enough when idle and busy are two cheap states; a growing one pays off only when the idle test itself is expensive and idle spells are long.
