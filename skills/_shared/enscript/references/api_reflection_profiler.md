# Reference: reflection, the script profiler and debugging globals

Reading and writing fields by name, calling methods by name, creating a class from a string, measuring script time with `EnProfiler`, and the global functions used while debugging. Every line cited as `P:\...:N` was opened on `P:\`; behaviour marked "reported" was measured in production mods and not re-run here. More examples are in `skills/enforce-script-reference/references/verified-api-catalog.md` and `timers-performance.md` in the same folder.

## Reflection

| Call | Use | Source |
|---|---|---|
| `EnScript.GetClassVar(inst, "name", index, out result)` | Read a field by name. Returns 1 on success. | `P:\scripts\1_core\proto\enscript.c:188` |
| `EnScript.SetClassVar(inst, "name", index, value)` | Write a field by name. Returns 1 on success. | `P:\scripts\1_core\proto\enscript.c:211` |
| `g_Game.GameScript.CallFunction(inst, "Method", out ret, param)` | Call a method by name with one parameter. | `P:\scripts\1_core\proto\enscript.c:146` |
| `g_Game.GameScript.CallFunctionParams(inst, "Method", out ret, new Param1<string>(s))` | The same with a `Param` holding the arguments. | `P:\scripts\1_core\proto\enscript.c:147` |
| `inst.Type()`, then `GetVariableCount()`, `GetVariableName(i)`, `GetVariableType(i)` | Walk the fields of a class. | `P:\scripts\1_core\proto\enconvert.c:586-588` |
| `"MyClass".ToType()` then `Spawn()` | Create an instance from a class name. Check the `typename` before `Spawn()`. | `P:\scripts\1_core\proto\enstring.c:95`, `P:\scripts\1_core\proto\enconvert.c:565` |
| `ScriptCaller.Create(fn)` then `Invoke()` | Keep a function reference to call later. | `P:\scripts\2_gamelib\tools.c:160`, `:165` |
| `DoOnce.Run(key, target, "Method", params)` | New in 1.30: run a method by name once per key for the whole process; `HasRun(key)` and `Clear(key)` go with it. For one time setup, not for per frame debouncing. | `P:\scripts\3_game\doonce.c:12`, `:30`, `:37` |

Limits (reported):

- `SetClassVar` reached a `private bool` in a production mod, but eight attempts to replace a `protected ref` collection field returned 0. Do not build a test hook on writing `ref` collections through reflection.
- A failed write is not harmless. In that probe the eight failed writes were followed by 48 null pointer exceptions when the object was deleted, while a control without reflection had none. When `SetClassVar` returns 0, stop using that object.
- A test fixture that injects state through reflection must check `SetClassVar == 1` and read the state back before it runs the code under test, and report a setup failure otherwise, never a pass.
- `Class.Cast` returns `null` on a type mismatch and does not throw; cast to a local and test it.

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

| Member | Use | Source (`1_core\proto\enprofiler.c`) |
|---|---|---|
| `Enable(bool enable, bool immediate = false, bool sessionReset = true)` | Turn profiling on or off. | `P:\scripts\1_core\proto\enprofiler.c:103` |
| `SetFlags(int flags, bool sessionReset = true)` | `EnProfilerFlags` has only `NONE`, `RESET`, `RECURSIVE` and `ALL` (`:8-18`); there are no flags per metric. | `P:\scripts\1_core\proto\enprofiler.c:223` |
| `SetModule(EnProfilerModule module, bool sessionReset = true)` | Choose what is profiled. | `P:\scripts\1_core\proto\enprofiler.c:333` |
| `SortData()` | The sorted data is filled at the end of each frame; call this to fill it now. | `P:\scripts\1_core\proto\enprofiler.c:172` |
| `GetTimePerFunc(out, count)`, `GetCountPerFunc(out, count)` | Top functions by time and by call count. | `P:\scripts\1_core\proto\enprofiler.c:610`, `:622` |
| `GetTimePerClass`, `GetAllocationsPerClass`, `GetInstancesPerClass` | Top classes by time, allocations and live instances. | `P:\scripts\1_core\proto\enprofiler.c:574`, `:586`, `:598` |
| `GetTimeOfFunc(name, clss, immediate)`, `GetCountOfFunc(name, clss, immediate)` | One method of class `clss`. | `P:\scripts\1_core\proto\enprofiler.c:689`, `:714` |
| `GetTimeOfFuncG(name, immediate)`, `GetCountOfFuncG(name, immediate)` | One global function. The last argument is `immediate`, not a "global" switch. | `P:\scripts\1_core\proto\enprofiler.c:701`, `:726` |

The result pairs are `Param2` typedefs, so read `param1` and `param2`: `EnProfilerTimeFuncPair` is `Param2<float, string>` (`P:\scripts\1_core\proto\enprofiler.c:58`; the others are at `:55-59`). Native `proto` methods are not tracked on their own (`:70`).

A high count from `GetAllocationsPerClass` in a tick path means allocation every tick; move the buffer to a member field (`../patterns/scheduler.md`).

## Debugging globals

| Call | Use | Source |
|---|---|---|
| `DumpStackString(out string stack)` | The current call stack as a string. | `P:\scripts\1_core\proto\endebug.c:50` |
| `ErrorEx(string err, ErrorExSeverity severity = ErrorExSeverity.ERROR)` | An error line prefixed with class and method. The enum is `INFO`, `WARNING`, `ERROR` (`:61`). | `P:\scripts\1_core\proto\endebug.c:83` |
| `PrintFormat(fmt, ...)` | `Print` with `%1`, `%2` placeholders. | `P:\scripts\1_core\proto\endebug.c:108` |
| `TickCount(int prev)` | A cheap stopwatch: `int start = TickCount(0);` then `TickCount(start)`. | `P:\scripts\1_core\proto\ensystem.c:106` |
| `GetCLIParam("name", out value)`, `IsCLIParam("name")` | Read a launch parameter (see the vanilla examples in the comments there). | `P:\scripts\1_core\proto\ensystem.c:125`, `:135` |
| `GetScreenSize(out x, out y)`, `GetMousePos(out x, out y)` | Screen size and mouse position in pixels. | `P:\scripts\1_core\proto\ensystem.c:331`, `:329` |
| `GetWidgetUnderCursor()`, `GetFocus()` | The widget under the mouse and the focused widget. | `P:\scripts\1_core\proto\enwidgets.c:184`, `:702` |

Crash and log reading (reported): a `crash_<date>_<time>.log` holds script exceptions, not native crashes, which write a separate dump; and when a compile error names a file that looks correct, the cause is often a class from an addon that is not loaded, because the compiler reports the last file it parsed.
