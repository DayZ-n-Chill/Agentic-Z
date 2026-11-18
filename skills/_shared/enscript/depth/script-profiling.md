# Script profiling and hot paths

How to find the expensive script with `EnProfiler`, and the cheap fixes for what it usually finds: strings built every tick, repeated `IsKindOf` and config reads, square roots in distance checks, and one RPC per device. The short `EnProfiler` reference is `../references/api_reflection_profiler.md`; timers are in `timers.md`.

## Profiling a block of script

Every line cited below is in `P:\scripts\1_core\proto\enprofiler.c`.

```c
EnProfiler.Enable(true, true);                  // enable, immediate (:103)
EnProfiler.SetFlags(EnProfilerFlags.RESET);     // (:223)

// ... run the code to measure ...

// The sorted data is filled at the end of each frame; EnProfiler.SortData() fills it now (:158 to :172).
array<ref EnProfilerTimeFuncPair> timePerFunc = new array<ref EnProfilerTimeFuncPair>;
EnProfiler.GetTimePerFunc(timePerFunc, 20);     // top 20

for (int i = 0; i < timePerFunc.Count(); i++)
{
    EnProfilerTimeFuncPair pair = timePerFunc[i];   // Param2<float, string> (:58)
    Print(pair.param2 + ": " + pair.param1.ToString() + " ms");
}

EnProfiler.Enable(false);
```

The queries and the pair type each returns (typedefs at `enprofiler.c:55` to `:59`):

| Method | Returns |
|---|---|
| `GetTimePerFunc(out, count)` | Top functions by time, `Param2<float, string>` |
| `GetCountPerFunc(out, count)` | Top functions by call count, `Param2<int, string>` |
| `GetTimePerClass(out, count)` | Top classes by time, `Param2<float, typename>` |
| `GetInstancesPerClass(out, count)` | Top classes by live instances, `Param2<int, typename>` |
| `GetAllocationsPerClass(out, count)` | Top classes by allocations, `Param2<int, typename>` |
| `GetTimeOfFunc(name, clss, immediate)` | Time of one method of class `clss` (`:689`) |
| `GetTimeOfFuncG(name, immediate)` | Time of one global function (`:701`) |
| `GetCountOfFunc(name, clss, immediate)` | Calls of one method of class `clss` (`:714`) |
| `GetCountOfFuncG(name, immediate)` | Calls of one global function (`:726`) |

The last argument of the single function queries is `immediate`, not a "global" switch; global functions use the `G` forms.

`EnProfilerFlags` has four values (`enprofiler.c:8` to `:18`):

| Flag | Meaning |
|---|---|
| `NONE` | Data adds up across frames; only the current module is sorted |
| `RESET` | Data is reset after each sort |
| `RECURSIVE` | Child modules are profiled too |
| `ALL` | `RESET` and `RECURSIVE`, the default |

What gets profiled is chosen with `EnProfiler.SetModule(EnProfilerModule.X)` (`:333`), not with flags. Native `proto` methods are not tracked on their own (`:70`).

To use it: wrap the suspect code, run a realistic case (many devices, a full server), read `GetTimePerFunc` for the slowest functions and `GetAllocationsPerClass` for allocation pressure, fix, then profile again to confirm.

## Build strings when the data changes

A string joined in every tick costs its time on every device every tick. Build it when the data changes and keep it:

```c
class MyMod_Device
{
    protected string m_CachedLabel;

    void UpdateCachedLabel()
    {
        m_CachedLabel = "Device " + GetType() + " at " + GetPosition().ToString();
    }
}
```

## Cache `IsKindOf` per type

`IsKindOf` walks the class tree (`P:\scripts\3_game\entities\object.c:511`). In a hot path, cache the answer per type name:

```c
class MyMod_Categories
{
    static ref map<string, string> s_Cache;

    static string Get(EntityAI item)
    {
        if (!s_Cache)
            s_Cache = new map<string, string>;

        string typeName = item.GetType();
        string result;
        if (s_Cache.Find(typeName, result))   // map.Find, P:\scripts\1_core\proto\enscript.c:877
            return result;

        result = Compute(item);   // the IsKindOf checks live here
        s_Cache.Set(typeName, result);
        return result;
    }

    static string Compute(EntityAI item)
    {
        if (item.IsKindOf("Weapon_Base"))
            return "weapon";
        return "";
    }
}
```

## Compare squared distances

`vector.DistanceSq` (`P:\scripts\1_core\proto\enconvert.c:210`) skips the square root. Compare it with the squared threshold:

```c
if (vector.DistanceSq(posA, posB) < 2500.0)   // 50 m squared
```

## One RPC for many devices

Sending one `ScriptRPC` per device multiplies the messages. Write the count, then each state, into one RPC:

```c
ScriptRPC rpc = new ScriptRPC();
rpc.Write(deviceCount);
for (int i = 0; i < deviceCount; i++)
    rpc.Write(devices[i].GetState());
rpc.Send(anchor, MYMOD_RPC_BATCH_STATE, true, identity);
```

Keep the size limits in mind and split very large batches (`../references/network_payload_limits.md`).

## Cache config reads

`ConfigGetInt`, `ConfigGetIntArray` (`P:\scripts\3_game\global\game.c:585`) and the other config reads look the value up on every call. Read once per type and keep the result:

```c
class MyMod_ItemArea
{
    static ref map<string, int> s_Cache;

    static int Get(EntityAI item)
    {
        if (!s_Cache)
            s_Cache = new map<string, int>;

        string typeName = item.GetType();
        int area;
        if (s_Cache.Find(typeName, area))
            return area;

        TIntArray sizes = new TIntArray;
        GetGame().ConfigGetIntArray("CfgVehicles " + typeName + " itemSize[]", sizes);
        area = 1;
        if (sizes.Count() >= 2)
            area = sizes[0] * sizes[1];

        s_Cache.Set(typeName, area);
        return area;
    }
}
```
