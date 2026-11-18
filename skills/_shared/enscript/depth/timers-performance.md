# Timers, performance and EnProfiler

The timing mechanisms, the `EnProfiler` API and the common optimizations. A line cited as `P:\...:N` was opened on `P:\`; the long-uptime behaviour and the measured results cannot be checked on `P:\`, are marked as such, and were not re-run here. The shared Enforce Script files on this are `skills/_shared/enscript/references/api_scheduling.md` and `skills/_shared/enscript/patterns/scheduler.md`.

## Timer Mechanisms in DayZ

DayZ offers several timing mechanisms, each with tradeoffs.

### CallLater (ScriptCallQueue)

The most common timer. Runs a callback after a delay, optionally repeating (`CallLater`, `P:\scripts\2_gamelib\tools.c:61`; `Remove` at `:65`).

```
// One-shot: execute after 5 seconds
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 5000, false);

// Repeating: execute every 3 seconds
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 3000, true);

// With parameters (up to 9)
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 5000, false, param1, param2);

// Cancel a scheduled call
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(MyCallback);
```

**CallQueue categories** (the constants and their own comments are at `P:\scripts\3_game\tools\tools.c:8-10`):
- `CALL_CATEGORY_SYSTEM`: system-level, "runs always", so also during loading
- `CALL_CATEGORY_GAMEPLAY`: standard gameplay. The vanilla comment is "runs unless ingame menu is opened"; in practice it ticks only while a mission runs and is not paused, so it is also paused during loading (traced in `skills/_shared/enscript/references/api_scheduling.md`)
- `CALL_CATEGORY_GUI`: UI updates, "runs always (on client)"; it never ticks on a dedicated server

**A `CallLater` re-queued from within its own callback never fired again on client diag 1.29** (chain pattern: `fn` re-enqueues itself) — zero RPT errors, chain dies silently after the first step; the same `CallLater` fired from outside the queue works normally. Remedy: `Timer(CALL_CATEGORY_GAMEPLAY).Run(s, this, "fn", null, true)` + `Stop()` on completion. Measured on client diag 1.29 (2026-08-19): the `CallLater` chain died after its first step, and the same chain on a `Timer` completed all five steps. Not reproduced on the retail DayZServer 1.30.164289 (2026-11-10): two chains that re-queue themselves from their own callback with `CallLater(fn, 500, false, …)`, one on `CALL_CATEGORY_SYSTEM` and one on `CALL_CATEGORY_GAMEPLAY`, both ran all six steps; the first queued step fired 14.3 s after `OnMissionStart` in both categories, the rest about 0.5 s apart.

#### THE CALLLATER BUG — 4.5 Hour Precision Loss

**Reported engine bug** (reported as still present in DayZ 1.28 and later). It cannot be checked on `P:\`, because `CallLater` is a `proto` with no script body (rule 21 in `hard-rules.md`; `skills/_shared/enscript/patterns/scheduler.md` treats it as unverified):

The report: after ~4.5 hours of server runtime, `CallLater` intervals become increasingly
inaccurate. The cause it gives: internal time is stored as a 32-bit float, and after 16,200
seconds (4.5h) integer values above 16,777,216 lose precision due to IEEE 754
mantissa limits.

**Reported symptoms:**
- Callbacks scheduled every 5s start firing every 7s, 10s, 15s...
- After 8+ hours, some callbacks never fire at all
- Affects all mods using `CallLater` with `repeat=true`

**Workarounds:**
1. **Server restart schedule** — restart every 3-4 hours
2. **Timer class** — keeps its own clock (next section), reported not affected
3. **Manual tick counter** — count frames in OnUpdate, fire when threshold reached

### Timer Class (Alternative)

The `Timer` class is reported not to be affected by the CallLater bug but is heavier on resources. It is script, so its clock can be read: each timer adds the frame's `timeslice` to its own `m_time` (`P:\scripts\3_game\tools\tools.c:277`) and never compares against the absolute uptime. `Timer` is declared at `:576` and `Run(duration, obj, fn_name, params, loop)` at `:595`.

```
class MyManager
{
    ref Timer m_Timer;

    void Start()
    {
        m_Timer = new Timer(CALL_CATEGORY_GAMEPLAY);
        m_Timer.Run(5.0, this, "OnTick", null, true);  // 5s repeat
    }

    void Stop()
    {
        if (m_Timer)
        {
            m_Timer.Stop();
        }
    }

    void OnTick()
    {
        // Called every 5s, reliable even after 4.5h+
    }
}
```

**Timer class uses more memory** than CallLater (creates internal objects).
For a few timers this is fine. For 100+ devices each with their own Timer,
use the centralized tick pattern instead.

### Centralized tick pattern

**One manager runs every periodic device tick** (rule 23 in `hard-rules.md`):

```
class MyNetworkManager
{
    // Single timer for ALL devices
    ref Timer m_GlobalTimer;

    // Device registry
    ref array<MyDevice> m_RegisteredDevices;

    void MyNetworkManager()
    {
        m_RegisteredDevices = new array<MyDevice>;
    }

    void StartGlobalTick()
    {
        m_GlobalTimer = new Timer(CALL_CATEGORY_GAMEPLAY);
        m_GlobalTimer.Run(5.0, this, "OnGlobalTick", null, true);
    }

    void RegisterDevice(MyDevice dev)
    {
        if (m_RegisteredDevices.Find(dev) < 0)
        {
            m_RegisteredDevices.Insert(dev);
        }
    }

    void UnregisterDevice(MyDevice dev)
    {
        int idx = m_RegisteredDevices.Find(dev);
        if (idx >= 0)
        {
            m_RegisteredDevices.Remove(idx);
        }
    }

    void OnGlobalTick()
    {
        int i;
        int count = m_RegisteredDevices.Count();
        for (i = 0; i < count; i = i + 1)
        {
            MyDevice dev = m_RegisteredDevices[i];
            if (dev)
            {
                dev.OnDeviceTick();
            }
        }
    }
}
```

**Why not per-device CallLater:**
- Each `CallLater(repeat=true)` allocates internal queue entries
- 100 devices × repeating callbacks = heap fragmentation
- After hours: an "Illegal write" crash (seen on a production server, not reproduced here; rule 22 in `hard-rules.md`)
- Single Timer + array iteration = zero fragmentation, reliable indefinitely

**Exception**: `ScriptRPC` calls that create `new ScriptRPC()` are fine because
they're consumed on Send (no accumulation).

---

## EnProfiler API

Enforce Script has a built-in profiler for measuring script performance. Every `enprofiler.c` line below is in `P:\scripts\1_core\proto\enprofiler.c` (`EnProfiler.Enable` is at `P:\scripts\1_core\proto\enprofiler.c:103`).

### Basic Usage

```
// Enable profiling (enprofiler.c:103)
EnProfiler.Enable(true, true);  // (enable, immediate = false, sessionReset = true)

// Set the flags (enprofiler.c:8-18, :223). The only values are
// NONE, RESET, RECURSIVE and ALL; there are no per-metric flags.
EnProfiler.SetFlags(EnProfilerFlags.RESET);

// ... run code to profile ...

// Get results. The sorted data is filled at the end of each frame;
// call EnProfiler.SortData() to fill it now (enprofiler.c:158-172).
// EnProfilerTimeFuncPair is a typedef of Param2<float, string> (enprofiler.c:58),
// so the fields are param1 (time) and param2 (function name).
array<ref EnProfilerTimeFuncPair> timePerFunc = new array<ref EnProfilerTimeFuncPair>;
EnProfiler.GetTimePerFunc(timePerFunc, 20);  // top 20

int i;
for (i = 0; i < timePerFunc.Count(); i = i + 1)
{
    EnProfilerTimeFuncPair pair = timePerFunc[i];
    string funcName = pair.param2;
    float timeMs = pair.param1;
    string msg = funcName;
    msg = msg + ": ";
    msg = msg + timeMs.ToString();
    msg = msg + " ms";
    Print(msg);
}

// Disable when done
EnProfiler.Enable(false);
```

### Available Queries

| Method | Returns |
|---|---|
| `GetTimePerFunc(out, count)` | Top N functions by time consumed (`Param2<float, string>`) |
| `GetCountPerFunc(out, count)` | Top N functions by call count (`Param2<int, string>`) |
| `GetTimePerClass(out, count)` | Top N classes by time consumed (`Param2<float, typename>`) |
| `GetInstancesPerClass(out, count)` | Top N classes by instance count (`Param2<int, typename>`) |
| `GetAllocationsPerClass(out, count)` | Top N classes by allocation count (`Param2<int, typename>`) |
| `GetTimeOfFunc(name, clss, immediate)` | Time consumed by a method of class `clss` (:689) |
| `GetTimeOfFuncG(name, immediate)` | Time consumed by a global function (:701) |
| `GetCountOfFunc(name, clss, immediate)` | Call count of a method of class `clss` (:714) |
| `GetCountOfFuncG(name, immediate)` | Call count of a global function (:726) |

The pair typedefs are at enprofiler.c:55-59. For the `...Of...` queries, the third
parameter is `immediate`, not a "global" switch: global functions use the `G` variants.

### Profiling Flags

`EnProfilerFlags` has only four values (enprofiler.c:8-18):

```
EnProfilerFlags.NONE        // Data accumulates across frames; only the current module is sorted
EnProfilerFlags.RESET       // Data is reset after each sort
EnProfilerFlags.RECURSIVE   // Child modules are profiled too, not only the current one
EnProfilerFlags.ALL         // RESET | RECURSIVE (the default)
```

What gets profiled is chosen with `EnProfiler.SetModule(EnProfilerModule.X)` (:333), not
with flags. Native `proto` methods are not tracked on their own (:70).

### Practical Profiling Workflow

1. Add profiling around suspected bottleneck
2. Run for representative scenario (many devices, full grid)
3. Check `GetTimePerFunc` — top functions are your bottleneck
4. Check `GetAllocationsPerClass` — high alloc count = GC pressure
5. Optimize: cache lookups, reduce allocations, batch operations
6. Re-profile to verify improvement

---

## Performance Optimization Patterns

### String Concatenation — Pre-build, Don't Repeat

```
// WRONG — builds string every tick
void OnTick()
{
    string msg = "Device ";
    msg = msg + GetType();
    msg = msg + " at ";
    msg = msg + GetPosition().ToString();
    Print(msg);  // called every 5s for 50 devices = 250 string builds
}

// CORRECT — cache when data changes, print cached
class MyDevice
{
    protected string m_CachedLabel;

    void UpdateCachedLabel()
    {
        m_CachedLabel = "Device ";
        m_CachedLabel = m_CachedLabel + GetType();
        m_CachedLabel = m_CachedLabel + " at ";
        m_CachedLabel = m_CachedLabel + GetPosition().ToString();
    }
}
```

### IsKindOf Caching

`IsKindOf` walks the class hierarchy (`P:\scripts\3_game\entities\object.c:511`), which is expensive for hot paths.

```
// WRONG — checked every tick for every item
string cat = "";
string kWeapon = "Weapon_Base";
if (item.IsKindOf(kWeapon))
    cat = "weapon";

// CORRECT — cache per typeName
static ref map<string, string> s_CategoryCache;

static string GetCategory(EntityAI item)
{
    if (!s_CategoryCache)
    {
        s_CategoryCache = new map<string, string>;
    }

    string typeName = item.GetType();
    if (s_CategoryCache.Contains(typeName))
    {
        return s_CategoryCache.Get(typeName);
    }

    string result = ComputeCategory(item);
    s_CategoryCache.Set(typeName, result);
    return result;
}
```

### Distance Checks — DistanceSq First

```
// WRONG — sqrt every check
float dist = vector.Distance(posA, posB);
if (dist < 50.0)

// CORRECT — compare squared distances (no sqrt)
float distSq = vector.DistanceSq(posA, posB);
float thresholdSq = 2500.0;  // 50^2
if (distSq < thresholdSq)
```

### Batch Network Operations

```
// WRONG — separate RPC per device
int i;
for (i = 0; i < deviceCount; i = i + 1)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(devices[i].GetState());
    rpc.Send(devices[i], RPC_STATE, true, identity);
}

// CORRECT — single RPC with batch data
ScriptRPC rpc = new ScriptRPC();
rpc.Write(deviceCount);
int j;
for (j = 0; j < deviceCount; j = j + 1)
{
    rpc.Write(devices[j].GetState());
}
rpc.Send(anchor, RPC_BATCH_STATE, true, identity);
```

### Config Reads — Cache Results

`GetGame().ConfigGetInt()` etc. read from binarized config every call (`ConfigGetIntArray` is at `P:\scripts\3_game\global\game.c:585`).

```
// Cache config values on first access
static ref map<string, int> s_ItemSizeCache;

static int GetItemSlotSize(EntityAI item)
{
    if (!s_ItemSizeCache)
    {
        s_ItemSizeCache = new map<string, int>;
    }

    string typeName = item.GetType();
    if (s_ItemSizeCache.Contains(typeName))
    {
        return s_ItemSizeCache.Get(typeName);
    }

    // Read from config
    string cfgPath = "CfgVehicles ";
    cfgPath = cfgPath + typeName;
    cfgPath = cfgPath + " itemSize[]";
    TIntArray sizes = new TIntArray;
    GetGame().ConfigGetIntArray(cfgPath, sizes);

    int area = 1;
    if (sizes.Count() >= 2)
    {
        area = sizes[0] * sizes[1];
    }

    s_ItemSizeCache.Set(typeName, area);
    return area;
}
```
