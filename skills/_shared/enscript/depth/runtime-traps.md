# Runtime traps

Which code compiles and then crashes or does nothing: native camera getters during client preload, the missing `Math.Exp`, where `$profile:` really points, scheduled callbacks that re-check a clock, entities that fall asleep, and path literals that lose their backslashes. Crashes in ordinary code are in `runtime-pitfalls.md`.

## Camera and world getters during client preload

Native getters that reach the world camera are not safe while the client preloads: `GetCurrentCameraPosition` and `GetCurrentCameraDirection` on the game (`P:\scripts\3_game\global\game.c:731` and `:732`), and `Camera.GetCurrentCamera`, `GetCurrentFOV` and `IsInterpolationComplete` (`P:\scripts\3_game\entities\camera.c:7`, `:13`, `:29`). The world camera does not exist yet, the native call reads through a null pointer, and the client takes a native crash with a minidump, not a script exception. A script check on the result, such as `if (!Camera.GetCurrentCamera())`, does not help, because the bad read happens inside the next native call.

A client handler for asynchronous input, such as an RPC, a pulled command or a tick-driven poll, can receive a command before the local player exists. In any client handler that touches camera, world or player APIs, check `GetGame() && GetGame().GetPlayer()` before the first native call and fail closed; a null local player means preload or not in game. Put one check in the dispatcher, plus a guard at the getter for call sites that bypass it. Measured in game: a camera command that arrived during preload wrote a minidump; with the check, the same command returned "client not in game" and no dump.

The side checks during load (`hard-rules.md`, section "Networking and sides") and the `CallLater` report (`hard-rules.md`, section "Timers") are the same family of timing problems.

## No `Math.Exp`

Nothing under `P:\scripts\` declares `Math.Exp`. Write exponentials, for frame-rate-independent smoothing, decay, half lives and easing, with `Math.Pow` (`P:\scripts\1_core\proto\enmath.c:183`) and `Math.EULER` (`:11`). Vanilla does the same, `Pow(EULER,-mean)`, in its Poisson helper (`:710`).

For smoothing that does not depend on frame time, compute once per channel when the tuning loads, `K_PER_SEC = Math.Pow(Math.EULER, -1.0 / TAU)`, then each tick `decay = Math.Pow(K_PER_SEC, dt)` and `alpha = 1 - decay`. That equals `exp(-dt/TAU)` for one `Pow` per channel per tick. Never multiply by a constant per tick, such as 0.95; the result then depends on the frame rate.

## Where `$profile:` points

`$profile:` resolves to the folder given by the executable's `-profiles=` parameter (`DayZDiag_x64`, `DayZServer_x64`), not always to `Documents\DayZ` in the user folder. It differs between server and client, diag and retail, and with the exact `-profiles=` value; a relative value resolves against the folder the executable started from. Print the resolved path once at mission init:

```c
string p = "$profile:mymod.json";
Print("[MyMod] profile resolves to: " + p);
```

Compare it in the RPT with where the launch script wrote the config. A mismatch explains "config URL empty" or "JsonFileLoader returned empty" without touching the read code: fix the launcher's `-profiles=` or use an absolute path. Path tokens are in `../references/file_paths.md`.

## Scheduled callbacks are the deadline

A one-shot `GetGame().GetCallQueue(...).CallLater(fn, delayMs, false)` whose `fn` checks again with `GetTickTime() >= armTime` can miss by milliseconds at the very moment it is due: the call queue keeps its own clock, and `GetTickTime()` can lag in the frame that fires. With a one-shot the action is lost for good. Inside the callback check only state (`armed && !started && state == X`), never the clock; a path that runs on an awake entity's tick may keep the clock comparison. Measured in game in a helicopter mod: the log showed the callback fire and then skip; the clock-free version worked.

An idle `CarScript` that is not moving falls asleep within a few ticks, and anything inside `EOnSimulate`, countdowns and polls, stops with it. `dBodyActive(this, ActiveState.ALWAYS_ACTIVE)` alone did not keep the tick running in that mod. To time logic on an entity that may sleep, use the call queue, which body sleep does not affect.

Give each fix its own log line, such as "keep-awake applied". Without it, "the fix was not compiled" and "the fix is not enough" look the same. The debug order is in `skills/dayz-launch-test/references/debug-protocol.md`.

## Path literals that lose their backslashes

Enforce drops escape sequences it does not recognise. `SetObjectMaterial(idx, "dz\\data\\data\\mirror.rvmat")` written from a bash heredoc reached the file with single backslashes, so the engine received `dzdatadatamirror.rvmat`: the call ran, the log said yes, and nothing rendered. When generating such literals from a script, build the backslash explicitly (`chr(92)` in Python) and check the result with `repr()`, and confirm in the log that the engine received the path intact.

Vanilla writes texture paths escaped and without a leading backslash: `"dz\\gear\\navigation\\data\\GPS_%1_ca.paa"` (`P:\scripts\4_world\entities\itembase\gear\navigation\gpsreceiver.c:4`). One mod shipped 64 `"\ModName\data\....rvmat"` literals with single backslashes across 24 `.c` files. Search a mod's `.c` files for string literals with a lone backslash inside a path, and log the path the engine actually receives.
