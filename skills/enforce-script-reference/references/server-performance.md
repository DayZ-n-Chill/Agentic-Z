# Server-Side Performance Patterns

The techniques for keeping many entities inside one server tick: a budget per frame, intervals that follow load, staggered scans, backoff, compile-time against run-time side checks, and an event bus against polling. Two kinds of evidence are used and neither is vanilla:

1. **DayZ Expansion's AI module (eAI)**: third-party mod behaviour, not vanilla. Its snippets below were read in the Expansion scripts as they were before 1.30 and are not on `P:\`; read the current Expansion scripts before relying on a detail. The same patterns are written up per pattern in the `dayz-ai-patterns` skill, `references/eai-pathfinding-groups.md`.
2. **Measurements on a production mod's dedicated server** (a large mod with a device registry, wire propagation and per-device diagnostics): not re-run here and not checkable on `P:\`.

The generic `#ifdef SERVER` / `IsServer()` / `IsDedicatedServer()` side-check rules and
the ScriptInvoker lifecycle rule are **rules 17-20 and 28** in `hard-rules.md`;
sections (f) and (g) below point at them rather than restating them. The vanilla side
checks are declared at `P:\scripts\3_game\global\game.c:1120` (`IsServer`) and `:1125`
(`IsDedicatedServer`).

A snippet headed "Expansion eAI" shows that mod's code. A snippet headed "Pattern" is a general skeleton to adapt.

---

## (a) The problem — the server tick has a fixed budget

A DayZ dedicated server advances the world on a single simulation thread. Every entity
that wants periodic work (self-heal, target scans, LOS, visual sync, wire propagation)
competes for the **same tick**. Two failure shapes dominate, and both are server-side and
event/tick-shaped, **not** per-frame UI:

- **O(n²)-per-event work that fires often.** Measured case: a "validate all wires and
  propagate" routine ran **five full registry `GetAll()` passes per self-heal**, each O(n²)
  in registry size, and the self-heal ran on a 500 ms debounce after any device move or cut.
  The fix is structural: fetch the device list **once** and pass it by reference into the
  rebuild helpers (this removes three of the five passes), and replace the
  `outArr.Find(ent)` O(n²) dedup with a seen-map.

- **Ungated always-on diagnostics.** Measured case: per-node `SetPowered` diagnostic
  strings and a log line per validation tick were built and `Print`ed for every dirty node
  at the production log level: constant RPT spam with a real cost per tick. Rule of thumb:
  a log string that is **concatenated unconditionally** costs even when the log level would
  discard it. Gate the *concat*, not just the print.

The techniques below are the vocabulary for keeping many entities inside one tick budget.

---

## (b) Budget-per-frame scheduler — cap work per tick, resume next tick

Instead of "every entity does its full work every tick", a central scheduler gives each
tick a **budget** and advances only as many entities as fit, resuming where it left off on
the next tick. Expansion eAI runs exactly this: a global `s_eAI_FTO` scheduler-mode flag
flips the whole AI population from "update every entity every frame" into scheduler mode
once the population crosses a threshold.

In Expansion's `ExpansionWorld.c` the scheduler reads `s_eAI_FTO >= 2` to decide each AI's
interval per tick (see backoff in (e)). Timer **rule 23** in `hard-rules.md` (run all
periodic ticks from one manager with a register and unregister pattern) has the same
shape: a budget scheduler is that manager plus a work cap per tick.

```c
// Pattern: budget scheduler skeleton. One manager owns the tick and caps the work per tick.
class MyTickScheduler
{
    protected ref array<EntityAI> m_Registered;   // rule 8: reuse, never `new` in tick
    protected int m_Cursor;                        // resume point across ticks
    protected const int WORK_BUDGET_PER_TICK = 32; // tune to measured frame time

    void OnTick(float dt)
    {
        int n = m_Registered.Count();
        if (n == 0) return;
        int processed = 0;
        while (processed < WORK_BUDGET_PER_TICK && processed < n)
        {
            if (m_Cursor >= n) m_Cursor = 0;       // wrap
            EntityAI e = m_Registered[m_Cursor];
            if (e) DoWork(e, dt);                  // the actual per-entity work
            m_Cursor++;
            processed++;
        }
        // remaining entities are picked up next tick — work spread, not dropped
    }
}
```

The scheduler's payoff is that the **worst-case tick cost is bounded by `WORK_BUDGET_PER_TICK`**,
independent of population. It trades latency (an entity may wait a few ticks for its turn)
for a flat frame time.

### Fairness inside a priority budget

A budget limits cost but does not guarantee coverage. A deadline/near-first pass that restarts from the same end every tick can consume the whole budget repeatedly and starve later items forever.

For every independently scheduled group:

1. Keep a persistent rotating cursor as member state, initialized outside the tick.
2. Reserve at least one budget slot for cursor-driven work; the priority pass must not consume that slot or reset the cursor.
3. Advance the cursor even when the selected item produces no sample, so one ineligible item cannot pin the group.
4. Re-read the current group count each tick and normalize the cursor with `% count`; membership and order can change.
5. Measure per-item sample count or maximum age. A zero-sample tail item is a starvation failure even when the scheduler stays within budget.

---

## (c) FPS-adaptive interval + rolling average — scale work rate to headroom

When the server has headroom, do work at the base rate; when it's under load (frame time /
`pDt` grows), stretch the interval so the *per-real-second* work stays constant. Expansion
eAI does this for its line of sight checks.

Expansion eAI, `eAIBase.c` (third-party mod behaviour, not vanilla):

```c
if (s_eAI_FTO < 2)
    interval = LOS_CHECK_INTERVAL;
else
    interval = LOS_CHECK_INTERVAL * (pDt / ExpansionWorld.AI_UPDATE_INTERVAL);
if (m_eAI_LOSCheckDT >= interval)
    m_eAI_LOSCheckDT = 0;
m_eAI_LOSCheckDT += pDt;
if (m_eAI_LOSCheckDT < interval && !m_eAI_TargetChanged)
    return state.m_LOS;   // return cached LOS; skip the raycast this tick
```

The key line is `interval = LOS_CHECK_INTERVAL * (pDt / AI_UPDATE_INTERVAL)`: when the
scheduler stretches `pDt` to 5× the base interval, the LOS interval also stretches 5×, so an
AI updated at one-fifth the rate does **not** get five times the LOS-check frequency. The
effective LOS rate stays constant regardless of how loaded the scheduler is. Setting
`m_eAI_TargetChanged` forces a fresh check, bypassing the cache — the escape hatch for
correctness-critical transitions.

**Rolling average** feeds this: to decide "is the server loaded", average `pDt` over a
window instead of reacting to a single spike. Expansion's `pDt` is already the scheduler's
smoothed step; the pattern generalizes to any adaptive interval:

```c
// Pattern: rolling average of frame time to drive an adaptive interval.
protected float m_DtAvg;
protected const float DT_SMOOTH = 0.1;   // EMA weight; smaller = smoother/slower
void AccumulateDt(float dt) { m_DtAvg = m_DtAvg * (1.0 - DT_SMOOTH) + dt * DT_SMOOTH; }
float AdaptiveInterval(float baseInterval, float refDt)
{
    float scale = m_DtAvg / refDt;   // above 1 when frames take longer than the reference
    if (scale < 1.0)
        scale = 1.0;                 // never run faster than the base rate
    return baseInterval * scale;
}
```

(The clamp is an `if` because Enforce Script has no ternary operator, rule 1 in `hard-rules.md`.)

The same shape appears as a fixed (non-adaptive) throttle for cosmetic work: physics runs
every tick while dials and HUD throttle to 10 Hz (`DIAL_UPDATE_INTERVAL = 0.1`), because
ten updates a second is enough for a numeric readout to stay readable and current, even
though a faster refresh would still be visible. FPS-adaptive is that same
throttle with the interval *driven by measured load* instead of a constant.

---

## (d) Staggered / modulo-gated scan — spread work across ticks, de-sync the herd

Two distinct sub-techniques, both aimed at never letting the whole population do the same
expensive thing on the same tick.

**Persistent-index staggered scan** — advance one item per tick, full refresh only when the
index is exhausted. Expansion eAI's target scan does this.

Expansion eAI, `eAIBase.c` (third-party mod behaviour, not vanilla):

```c
m_eAI_UpdateTargetsTick += pDt;
if (m_eAI_CurrentPotentialTargetIndex >= m_eAI_PotentialTargetEntities.Count()
    && m_eAI_UpdateTargetsTick > Math.RandomFloat(0.1, 0.2))
{
    m_eAI_UpdateTargetsTick = 0;
    m_eAI_CurrentPotentialTargetIndex = 0;
```

`UpdateTargets` advances **one index per tick** rather than scanning the whole list; a full
refresh happens only when the index is exhausted **and** the random interval elapsed. The
`Math.RandomFloat(0.1, 0.2)` jitter is the de-sync: without it, every AI that spawned on the
same frame would finish its scan on the same later frame, re-clustering the cost. The same
jitter idea recurs in Expansion's `eAITargetInformationState.c` (threat cache,
`Math.RandomIntInclusive(250, 300)`) and `eAIGroup.c` (formation cache,
`Math.RandomFloat(2.0, 4.0)`).

**Modulo-gated scan** — process `entity[i]` only when `(tick + i) % N == 0`, so 1/N of the
population runs each tick, and offsets by index so they don't all land together:

```c
// Pattern: modulo-gating. Each entity runs once every N ticks, staggered by index.
protected int m_TickCounter;
void OnTick()
{
    m_TickCounter++;
    for (int i = 0; i < m_Registered.Count(); i++)
        if ((m_TickCounter + i) % SCAN_STRIDE == 0)   // +i staggers the herd
            DoScan(m_Registered[i]);
}
```

Modulo-gating gives a deterministic 1/N spread (good when you want a guaranteed cadence);
random jitter gives a statistical spread (good when deterministic phase would still cluster,
e.g. entities that all register on server boot). The *event-driven* variant of "don't do it
every tick" is a self-heal that is **debounced 500 ms** on the triggering event rather than
polled, which is the strongest form of staggering: do the work zero times until something
actually changes (see (g)).

---

## (e) Exponential / multiplicative backoff — degrade frequency by relevance

When an entity has nothing nearby worth reacting to, **stretch its interval** instead of
disabling it — logic still runs, just less often, and re-arms instantly when relevance
returns. Expansion eAI uses a flat 5× backoff gated on player proximity.

Expansion eAI, `ExpansionWorld.c` (third-party mod behaviour, not vanilla):

```c
if (eAIBase.s_eAI_FTO >= 2 && ai.m_eAI_PlayersWithinVisibilityDistanceLimit.Count() == 0)
    updateIntervalCurrent = AI_UPDATE_INTERVAL * 5;   // 50 ms -> 250 ms
else
    updateIntervalCurrent = updateInterval;
```

When no player is within the AI's visibility range, its interval degrades from ~50 ms to
~250 ms. The condition is **AI-local** — each unit decides its own backoff independently, so
a server with 200 idle bots and 3 engaged bots pays full rate for 3 and one-fifth rate for
200. This is the multiplicative-backoff principle (degrade frequency by relevance); the eAI
case uses a fixed 5× factor rather than a growing exponential, but the shape generalizes:

```c
// Pattern: exponential backoff with a cap. Grows while idle, snaps back on activity.
protected float m_Backoff = 1.0;
protected const float BACKOFF_MAX = 8.0;
float NextInterval(float baseInterval, bool sawSomethingRelevant)
{
    if (sawSomethingRelevant) m_Backoff = 1.0;                        // snap back
    else                      m_Backoff = Math.Min(m_Backoff * 2.0, BACKOFF_MAX); // double, capped
    return baseInterval * m_Backoff;
}
```

Cap the growth (`BACKOFF_MAX`) so an idle entity still checks often enough to notice when it
becomes relevant. Fixed-factor (eAI's ×5) is simpler and adequate when the "idle" and "busy"
states are binary and cheap to test; growing-exponential is worth it only when the idle test
itself is expensive and idleness is long-tailed.

---

## (f) `#ifdef SERVER` (compile-time) vs `IsServer()` / `IsDedicatedServer()` (runtime)

See **rules 17-20** in `hard-rules.md`. Both mean "do this only on the server", but they
resolve at different times and have different failure modes — picking wrong is a perf **and**
a correctness bug.

- **`#ifdef SERVER` — compile-time.** The block is *not compiled into* the client build at
  all. Use it to keep server-only work (SyncVar writes per rule 17, heavy propagation, disk
  I/O, diagnostics) out of the client binary entirely — zero runtime cost on the client
  because the code doesn't exist there. This is the right tool for **whole subsystems** that
  never run client-side, such as self-heal, propagation and per-node diagnostics; the fix
  for the ungated diagnostic strings in (a) is to `#ifdef`-guard or delete them so they
  never build at ship level.
  `skills/_shared/enscript/references/language_compile.md` lists the defines vanilla uses.

    - **`#ifndef SERVER` erases the type from the dedicated-server build.** `SERVER` is defined only in the dedicated-server executable (absent in offline and listen). Wrapping a class in `#ifndef SERVER … #endif` removes it from the server type surface; any other mod or server-side RPC handler that references it then fails with `Unknown type 'X'`, then `Can't compile "World" script module!`, and the server does not start. A check of your own mod ("0 client symbols in the server view") does not catch this: the break is in the contract with other mods. Before guarding a symbol, ask "does any other mod or server-side handler reference it?" If it does, keep the type declared in both builds: an empty stub under `#ifdef SERVER` with the signatures the consumer touches (a no-op body if the logic is client-only); pure data classes (fields only) cost nothing to leave unguarded. Smoke test: **compile the module with `SERVER` defined (a dedicated server)**, not just offline or client: offline does not define `SERVER`, so it passes locally and breaks on dedicated. Measured in game (2026-07-20): a viewport class inside `#ifndef SERVER` broke another mod that referenced it, with `Unknown type` on the dedicated server.

- **`IsServer()` / `IsDedicatedServer()` — runtime.** A branch taken at execution time in a
  build that contains *both* paths. Use it inside code that legitimately runs on both sides
  and must fork behavior per-call (e.g. an `OnRPC` handler that validates on server and
  applies on client). **The load-time trap (rules 19-20, not yet checked on `P:\`):** `GetGame().IsServer()`
  is reported to return true on a client *during load*, and `IsClient()` is not reliably true on a client during
  load — so at constructor / module-init / `OnInit` time you must use `IsDedicatedServer()` /
  `!IsDedicatedServer()`, not `IsServer()`/`IsClient()`. After load (post-load callbacks:
  `OnRPC`, `EEContact`, per-tick), `IsServer()`/`IsClient()` are safe and are the standard
  vanilla pattern (rule 20 scope note). A guard for a client-only resource
  (`!IsClient() && IsMultiplayer()`, called *lazily*, never at load) is the concrete
  "skip if MP server" instance of this.

**Perf decision rule:** if the work is server-only for an entire subsystem, prefer
`#ifdef SERVER` — it removes the cost from the client build outright. If the work is one
branch of a both-sides method, use the runtime check, and if it runs at load time use
`IsDedicatedServer()`. Do not wrap a per-tick hot path in a runtime `IsServer()` when a
compile-time gate on the enclosing subsystem would remove the branch entirely.

---

## (g) ScriptInvoker bus vs polling — react to events, don't scan for them

The cheapest scan is the one you never run. Polling asks "did anything change?" every tick;
an event bus (`ScriptInvoker`) is *told* when something changed and does zero work otherwise.
The self-heal in (a) is the canonical win: it is **debounced 500 ms on the device move/cut
event** rather than polled every tick, so the expensive O(n²) validation runs only in
response to an actual topology change.

`ScriptInvoker` is the DayZ event-bus primitive (`P:\scripts\2_gamelib\tools.c:115`; `Invoke` at `:118`, `Insert` at `:120`, `Remove` at `:122`): an entity/manager exposes an invoker,
consumers `Insert(callback)`, and the producer `Invoke(...)` fans out on the event. This
replaces "N consumers each polling the producer's state every tick" with "producer notifies
N consumers once, when the state changes".

```c
// Pattern: event bus instead of per-tick polling.
// Producer:
static ref ScriptInvoker Event_TopologyChanged = new ScriptInvoker();
void OnDeviceMovedOrCut() { Event_TopologyChanged.Invoke(this); }   // fire once, on change

// Consumer:
void Init()   { Event_TopologyChanged.Insert(OnTopologyChanged); }
void OnTopologyChanged(EntityAI src) { /* validate only the affected subgraph */ }
```

**Lifecycle, rule 28 in `hard-rules.md` (mandatory):** every `ScriptInvoker.Insert(cb)` **must** be
matched by a `Remove(cb)` in the consumer's destructor, null-checking the invoker first:
`if (Producer.Event_X) Producer.Event_X.Remove(OnTopologyChanged);`. A dangling subscription
keeps a dead consumer reachable (leak) and can crash on shutdown when `Remove` is called on a
freed invoker (see the `ScriptInvoker` shutdown null guard in
`skills/_shared/enscript/patterns/singleton.md`).

**When polling still wins:** an event bus is worth it when changes are *sparse relative to
ticks* (topology edits, power transitions, player join/leave). If a value changes *every*
tick anyway (a moving position you sample each frame), a direct read is simpler than firing
an invoker every tick — the bus adds fan-out overhead without saving a scan. Choose the bus
when `event_rate << tick_rate`; keep the poll when `event_rate ≈ tick_rate`.

## Server-side script memory (World kB) — measured levers and non-levers

Measured on a dedicated server with a large mod loaded (about 2,380 script files and 6,140 classes; July to August 2026), not re-run here. The operational question: which lever actually lowers static script memory (World kB) on a dedicated server.

**Measured 0 kB (does not move World):**
- Merging or repackaging files under `4_World`: files 2383 to 2367, classes 6141 to 6141, World 13483 to 13483 kB (two repetitions).
- Removing comments and whitespace: about 0 kB.

**Measured non-zero (does move World):**
- Bytecode-level cleaning (2026-07-30): World dropped by 28 to 29 kB in one run and 18 to 19 kB in another with the class count unchanged (6110 to 6110). The relationship is not a simple "class count to kB" law.
- `#ifndef SERVER` around client-only code (excluded from the dedicated-server compile entirely).
- Collapsing engine generic specializations (`array<T>` to `array<EntityAI>` plus a cast).
- Managed-class aliases for types used inside generics.

**Measured 0 kB at small scale (do not budget on this assumption):**
- Removing a few classes: 6140 to 6137 classes gave 0 kB, and 6110 to 6109 gave 0 kB. A "purge dead classes" pass is not a reliable kB lever at this granularity.

**Before budgeting any "purge dead code" pass, measure existing `#ifndef SERVER` coverage.**
Real case: a duplicated UI fork of 182.4 KB source looked like the obvious cheap lever. A nesting-aware preprocessor count showed about 97% of it already inside `#ifndef SERVER`; only about 5.5 KB compiled on the server. Purging yields about 3 to 4 kB, not the roughly 118 kB a byte ratio suggests. Without that measurement it would have been prioritized over a real lever of about 140 kB.

**Order-of-magnitude heuristic:** about 0.65 kB of static memory per KB of compiled `4_World` source on the server. Cross-check on the same mod: 1522 kB of World attributable to the mod over about 1429 KB of server-side source gives about 1.06. Use it to discard levers, never to promise a number.

**Causal measurement protocol:** adjacent triplets of runs (without the mod, baseline, candidate), same boot, two repetitions. The observed noise is ±1 kB (the value is an integer): a success criterion below that does not discriminate and will pass a 0 kB change.
