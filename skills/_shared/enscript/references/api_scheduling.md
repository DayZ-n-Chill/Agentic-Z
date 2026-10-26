# Reference: call queues, timers and invokers

Running code later, on a repeat, every frame, or when an event fires. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`). Precision and per tick allocation traps are in `patterns/scheduler.md`.

## Call categories

| Constant | Value | Ticks | Source |
|---|---|---|---|
| `CALL_CATEGORY_SYSTEM` | 0 | Every frame, always. | `P:\scripts\3_game\tools\tools.c:8`, `P:\scripts\3_game\dayzgame.c:3026` to `:3028` |
| `CALL_CATEGORY_GUI` | 1 | Only in builds with a GUI: the tick sits inside `#ifndef NO_GUI`, so it never runs on a dedicated server. Also skipped while loading. | `tools.c:9`, `dayzgame.c:3030` to `:3076` |
| `CALL_CATEGORY_GAMEPLAY` | 2 | Only while a mission runs and is not paused. | `tools.c:10`, `dayzgame.c:3005` to `:3010`, `:3078` to `:3082` |

Pick `GAMEPLAY` for game logic, `GUI` for client UI, and `SYSTEM` only for work that must run even when paused or before a mission exists. Never schedule server logic on `GUI`.

## `ScriptCallQueue`

Get one with `GetGame().GetCallQueue(category)` (`P:\scripts\3_game\dayzgame.c:1233`). The class is at `P:\scripts\2_gamelib\tools.c:52`.

| Method | Behaviour | Line |
|---|---|---|
| `Call(fn, args...)` | Runs `fn` on the next tick. | 57 |
| `CallLater(fn, delayMs, repeat, args...)` | Runs after `delayMs` milliseconds; with `repeat = true` it runs every `delayMs` until removed. Up to nine arguments. | 61 |
| `CallByName(obj, "Fn", params)` / `CallLaterByName(...)` | The same with a method name and a `Param`. | 59, 63 |
| `Remove(fn)` / `RemoveByName(obj, "Fn")` | Removes a queued call. | 65, 69 |
| `GetRemainingTime(fn)` | Milliseconds until it runs. | 67 |

The queue holds the arguments until the call runs or is removed (`tools.c:56`). Vanilla examples:

```c
g_Game.GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(PlaySound, SOUND_REPEAT_INTERVAL * 1000, true, player);
g_Game.GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(PlaySound);
```

Sources: `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionforceconsume.c:34`, `:46`. Pass the method itself (`PlaySound` or `this.PlaySound`), not a string, with `CallLater` and `Remove`. Remove repeating calls when the owner goes away, as vanilla does in `EEDelete` (`P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c:23` to `:25`).

`Object.Delete()` itself is a queued call: it runs `ObjectDelete` through `CALL_CATEGORY_SYSTEM` on the next tick (`P:\scripts\3_game\entities\object.c:82` to `:85`).

## `Timer`

`Timer` (`P:\scripts\3_game\tools\tools.c:576`) calls a method by name. Its duration is in **seconds**, unlike `CallLater`.

```c
ref Timer m_Timer = new Timer(CALL_CATEGORY_GAMEPLAY);
m_Timer.Run(10, this, "Refresh", null, true);   // every 10 seconds
```

| Member | Behaviour | Line |
|---|---|---|
| `Timer(category = CALL_CATEGORY_SYSTEM)` | The default category is `SYSTEM`; pass `GAMEPLAY` for game logic. | 582 |
| `Run(seconds, obj, "fn", params = null, loop = false)` | Starts the timer. `params` is a `Param` such as `new Param1<bool>(false)`. | 595 |
| `Stop()` | Stops and resets; start again with `Run`. | 617 |
| `Pause()` / `Continue()` | Pause keeps the elapsed time. | 239, 247 |
| `IsRunning()`, `GetRemaining()`, `GetDuration()` | State queries. | 264, 318, 313 |

The timer holds its target weakly (`protected Managed m_target;`, line 578), so the target must be a `Managed` object that something else keeps alive. Keep the `Timer` in a `ref` member or it is freed (see `language_memory.md`).

## Per frame updates

`GetGame().GetUpdateQueue(category)` is a `ScriptInvoker` invoked every tick of that category with the frame time (`P:\scripts\3_game\dayzgame.c:1238`, `:3027`). Subscribe a method that takes a `float`:

```c
g_Game.GetUpdateQueue(CALL_CATEGORY_GUI).Insert(this.Update);   // 3_game/gui/effects/radialprogressbar.c:19
g_Game.GetUpdateQueue(CALL_CATEGORY_GUI).Remove(this.Update);   // same file, :25
protected void Update(float tDelta)                             // same file, :38
```

Per frame code is costly. Prefer `CallLater` with a delay for anything that does not need every frame.

## `ScriptInvoker`

A list of methods called together (`P:\scripts\2_gamelib\tools.c:115`).

| Method | Behaviour | Line |
|---|---|---|
| `Insert(fn, flags = IMMEDIATE)` | Adds a listener; returns `bool`. `EScriptInvokerInsertFlags.UNIQUE` raises a script error on a second insert of the same method. | 120, 129 to 145 |
| `Remove(fn, flags = ALL)` | Removes every copy of the listener by default. | 122 |
| `Invoke(args...)` | Calls every listener with up to nine arguments. | 118 |
| `Count(fn)`, `Clear()` | Count copies of a listener, or remove all. | 124, 126 |

A listener inserted while the invoker runs is called in the same run by default (`tools.c:133` to `:138`). Vanilla events are static invokers, for example `static ref ScriptInvoker Event_OnRPC` on `DayZGame` (`P:\scripts\3_game\dayzgame.c:991`). Remove your listener before its object is freed; the shutdown null guard is in `patterns/singleton.md`.

`ScriptCaller` holds exactly one call: `ScriptCaller.Create(fn)`, then `Invoke(...)` and `IsValid()` (`P:\scripts\2_gamelib\tools.c:160`, `:165`, `:169`, `:172`).
