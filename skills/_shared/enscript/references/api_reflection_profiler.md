# Reflection, the profiler and debugging globals

How to read and write fields by name, call methods by name, create a class from a string, measure script time with `EnProfiler`, and which global functions help while debugging. Facts marked "measured in game" come from production mods and are not checked on `P:\`. Worked examples are in `../depth/reflection-api.md` and `../depth/script-profiling.md`.

## Reflection

| Call | Use | Source |
|---|---|---|
| `EnScript.GetClassVar(inst, "name", index, out result)` | Read a field by name. Returns 1 on success | `P:\scripts\1_core\proto\enscript.c:188` |
| `EnScript.SetClassVar(inst, "name", index, value)` | Write a field by name. Returns 1 on success | `enscript.c:211` |
| `g_Game.GameScript.CallFunction(inst, "Method", out ret, param)` | Call a method by name with one parameter | `enscript.c:146` |
| `g_Game.GameScript.CallFunctionParams(inst, "Method", out ret, new Param1<string>(s))` | The same, with a `Param` holding the arguments | `enscript.c:147` |
| `inst.Type()`, then `GetVariableCount()`, `GetVariableName(i)`, `GetVariableType(i)` | Walk the fields of a class | `P:\scripts\1_core\proto\enconvert.c:565` to `:567` |
| `"MyClass".ToType()`, then `Spawn()` | Create an instance from a class name. Test the `typename` before `Spawn()` | `P:\scripts\1_core\proto\enstring.c:95`; `Spawn` at `P:\scripts\1_core\proto\enconvert.c:544` |
| `ScriptCaller.Create(fn)`, then `Invoke()` | Keep a function reference to call later | `P:\scripts\2_gamelib\tools.c:160` and `:165` |
| `DoOnce.Run(key, target, "Method", params)` | New in 1.30: run a method by name once per key for the whole process, with `HasRun(key)` and `Clear(key)`. Meant for one time setup, not for debouncing each frame | `P:\scripts\3_game\doonce.c:12`, `:30`, `:37` |

Limits, measured in game:

- `SetClassVar` can write a `private bool`, but eight attempts to replace a `protected ref` collection field all returned 0. Don't build a test hook on writing `ref` collections through reflection.
- A failed write is not harmless. Those eight failed writes were followed by 48 null pointer exceptions when the object was deleted, while the same object without reflection had none. When `SetClassVar` returns 0, stop using that object.
- A test fixture that sets state through reflection must check that `SetClassVar` returned 1 and read the state back before it runs the code under test. Otherwise it reports a setup failure, never a pass.

`Class.Cast` returns `null` on a type mismatch and doesn't throw. Cast to a local and test it.

## EnProfiler

`EnProfiler` (`P:\scripts\1_core\proto\enprofiler.c`) measures script time, call counts and allocations.

```c
EnProfiler.Enable(true, true);              // enable, immediate
EnProfiler.SetFlags(EnProfilerFlags.RESET);

// ... run the code to measure ...

array<ref EnProfilerTimeFuncPair> timePerFunc = new array<ref EnProfilerTimeFuncPair>;
EnProfiler.GetTimePerFunc(timePerFunc, 20); // the 20 most expensive functions

for (int i = 0; i < timePerFunc.Count(); i++)
{
    EnProfilerTimeFuncPair pair = timePerFunc[i];
    Print(pair.param2 + ": " + pair.param1.ToString());   // function name, time
}

EnProfiler.Enable(false);
```

| Member | Use | Source |
|---|---|---|
| `Enable(bool enable, bool immediate = false, bool sessionReset = true)` | Turn profiling on or off | `P:\scripts\1_core\proto\enprofiler.c:103` |
| `SetFlags(int flags, bool sessionReset = true)` | `EnProfilerFlags` has only `NONE`, `RESET`, `RECURSIVE` and `ALL` (`:8` to `:18`); there are no flags per metric | `enprofiler.c:223` |
| `SetModule(EnProfilerModule module, bool sessionReset = true)` | Choose what is profiled | `enprofiler.c:333` |
| `SortData()` | The sorted data is filled at the end of each frame; call this to fill it now | `enprofiler.c:172` |
| `GetTimePerFunc(out, count)`, `GetCountPerFunc(out, count)` | Top functions by time and by call count | `enprofiler.c:610` and `:622` |
| `GetTimePerClass`, `GetAllocationsPerClass`, `GetInstancesPerClass` | Top classes by time, allocations and live instances | `enprofiler.c:574`, `:586`, `:598` |
| `GetTimeOfFunc(name, clss, immediate)`, `GetCountOfFunc(name, clss, immediate)` | One method of class `clss` | `enprofiler.c:689` and `:714` |
| `GetTimeOfFuncG(name, immediate)`, `GetCountOfFuncG(name, immediate)` | One global function. The last argument is `immediate`, not a "global" switch | `enprofiler.c:701` and `:726` |

The result pairs are `Param2` typedefs, so read `param1` and `param2`. `EnProfilerTimeFuncPair` is `Param2<float, string>` (`enprofiler.c:58`; the others are at `:55` to `:59`). Native `proto` methods are not tracked on their own (`:70`).

A high count from `GetAllocationsPerClass` in a tick path means the tick allocates every time; move the buffer to a member field (`../patterns/scheduler.md`).

## Debugging globals

| Call | Use | Source |
|---|---|---|
| `DumpStackString(out string stack)` | The current call stack as a string | `P:\scripts\1_core\proto\endebug.c:50` |
| `ErrorEx(string err, ErrorExSeverity severity = ErrorExSeverity.ERROR)` | An error line prefixed with class and method. The enum is `INFO`, `WARNING`, `ERROR` (`:61`) | `endebug.c:83` |
| `PrintFormat(fmt, ...)` | `Print` with `%1`, `%2` placeholders | `endebug.c:108` |
| `TickCount(int prev)` | A cheap stopwatch: `int start = TickCount(0);`, later `TickCount(start)`. The vanilla comment says it returns "number of CPU ticks", so treat the value as relative | `P:\scripts\1_core\proto\ensystem.c:106` |
| `GetCLIParam("name", out value)`, `IsCLIParam("name")` | Read a launch parameter; vanilla's comments there carry examples | `ensystem.c:128` and `:141`, with examples at `:125` and `:135` |
| `GetScreenSize(out x, out y)`, `GetMousePos(out x, out y)` | Screen size and mouse position in pixels | `ensystem.c:331` and `:329` |
| `GetWidgetUnderCursor()`, `GetFocus()` | The widget under the mouse and the focused widget | `P:\scripts\1_core\proto\enwidgets.c:184` and `:702` |

Reading crashes and logs, measured in game: a `crash_<date>_<time>.log` holds script exceptions, not native crashes, which write a separate dump. When a compile error names a file that looks correct, the cause is often a class from an addon that isn't loaded, because the compiler reports the last file it parsed.
