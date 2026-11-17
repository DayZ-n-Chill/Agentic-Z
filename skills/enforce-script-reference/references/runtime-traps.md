# Runtime traps

Failures that compile cleanly and then crash or do nothing at run time: native getters called during client preload, the missing `Math.Exp`, where `$profile:` really points, scheduled callbacks that re-check a clock, and path literals that lose their backslashes. A line cited as `P:\...:N` was opened on `P:\`; the measured results name the mod that measured them and were not re-run here.

## Client preload: native camera and world getters crash, and no guard catches it (SP-064)

Native getters that reach the world camera are not safe during the client's preload: `GetCurrentCameraPosition` and `GetCurrentCameraDirection` on the game (`P:\scripts\3_game\global\game.c:731-732`), and `Camera.GetCurrentCamera`, `GetCurrentFOV` and `IsInterpolationComplete` (`P:\scripts\3_game\entities\camera.c:7`, `:13`, `:29`). The world camera is not built yet, the native getter reads through a null pointer, and the process takes a native crash (a minidump), not a script exception. A script guard on the result (`if (!Camera.GetCurrentCamera())`) does not catch it: the bad read happens inside the next native call. A client handler that processes asynchronous input (an RPC, a pulled command, a poll driven by a tick) can receive a command before the local player exists and hit this.

Rule: in any client handler that touches camera, world or player derived APIs, check readiness before the first native call and fail closed: `GetGame() && GetGame().GetPlayer()` (a null local player means preload, or not in game). The DayZ-MCP vehicle handlers already use the same test (`ResolveOwnedCar` returns `null` when `GetGame().GetPlayer()` is null). Prefer one check in the dispatcher, which covers the whole class of commands, plus a defensive guard at the getter when it has call sites that do not come back through the dispatcher (for example the report of an asynchronous job).

Related: the entity lifecycle notes in `api-patterns.md`, the `IsServer` and `IsClient` side checks (rules 19 and 20 in `hard-rules.md`) and the `CallLater` rule (rule 21) are the same family of lifecycle timing problems. Origin: the DayZ-MCP bridge mod (a minidump inside its client camera command, reproduced 2026-07-11); with the check in place a `camera_get` that reached the client during preload returned `client_not_in_game` and no dump was written (in game, 2026-07-12).

## There is no `Math.Exp`: write `Math.Pow(Math.EULER, x)` (SP-058)

Enforce has no `Math.Exp` (no hit anywhere under `P:\scripts\`). Write any exponential (smoothing that does not depend on the frame time, decay, half life, easing) with `Math.Pow` (`P:\scripts\1_core\proto\enmath.c:183`) and `Math.EULER` (`P:\scripts\1_core\proto\enmath.c:11`). Vanilla uses the same idiom, `Pow(EULER,-mean)`, in its Poisson helper (`P:\scripts\1_core\proto\enmath.c:710`).

A tick pattern that does not depend on the frame time (cheap: one `Pow` per channel per tick): when the tuning loads, compute once per channel `K_PER_SEC = Math.Pow(Math.EULER, -1.0 / TAU_channel)`; each tick compute `decay = Math.Pow(K_PER_SEC, dt)` and `alpha = 1 - decay`. This equals `exp(-dt/TAU)` without an exp call. Never use a constant per tick (multiplying by 0.95 each tick depends on the frame rate; that was the real bug in the flight simulation of the third-party RFFS helicopter mod).

Related: the row "`Math.Clamp` not found" in `review-and-troubleshooting.md`, the same family of math APIs assumed missing or assumed present. Origin: the LFHeli mod, where a reviewer caught the missing function before coding; it ships with four `K_PER_SEC` channels.

## `$profile:` is the folder of the exe's `-profiles=`, not always `%USERPROFILE%`: probe it at run time (SP-029)

`$profile:` resolves to the folder given by the `-profiles=` parameter of the exe (`DayZDiag_x64`, `DayZServer_x64`), not always `%USERPROFILE%\Documents\DayZ\...`. What it resolves to changes between server and client, between diag and retail, and with the exact `-profiles=` value (a relative path resolves against the folder the exe was launched from). The standard probe, run by the mod on first boot (mission init):

    string p = "$profile:dayz_mcp.json"; // or whatever file
    Print("[MOD] profile resolves to: " + p);

Check in the RPT that `p` matches the absolute path where the launch wrapper (PowerShell or batch) wrote the config. A mismatch explains symptoms such as "config_url_empty" or "JsonFileLoader returned empty" without touching the read code or rebuilding: the fix is the wrapper's `-profiles=` or an absolute path in the mod, not the read logic. Origin: the DayZ-MCP bridge mod, 2026-06-07. Related lessons: LL-113, LL-097 (a path is a hint), LL-101 (a proto is not the run time). The path tokens themselves are in `skills/_shared/enscript/references/file_paths.md`.

## Scheduled callbacks: the callback is the deadline; sleeping entities miss `EOnSimulate`; one log marker per fix (SP-060)

A clock race in a scheduled one-shot: a `GetGame().GetCallQueue(...).CallLater(fn, delayMs, false)` whose `fn` checks the deadline again with `GetTickTime() >= armTime` can miss by milliseconds at the very instant it is due (the call queue keeps its own clock, and `GetTickTime()` can lag in the frame that fires). With a one-shot the action is lost for good. Rule: the callback is the deadline. Do not compare clocks inside it; check only state (`armed && !started && state==X`). A path that runs on a tick of an awake entity may keep the clock comparison. Evidence: in the LFHeli mod the log read `TrySpikeStart fired state=0` and then `skipped`; the version without a clock (`IsArmedNotStarted()`) worked first time.

Sleeping entities miss `EOnSimulate`: an idle `CarScript` that is not moving goes to sleep within a few ticks, and anything living inside `EOnSimulate` (countdowns, polls) stops with it. `dBodyActive(this, ActiveState.ALWAYS_ACTIVE)` alone did not guarantee the tick in that mod; the robust way to time logic on an entity that may sleep is the call queue, which body sleep does not affect.

A working habit: one log marker per fix. Each fix that goes through an in game cycle adds its own log line ("keep-awake applied", "TrySpikeStart fired state=X"). Without it, "the fix was not compiled" and "the fix is not enough" look the same and cost a full rebuild and boot. Related: the `CallLater` rule (rule 21 in `hard-rules.md`) and the debug order in the `dayz-mod-workflow` skill. Origin: the LFHeli mod, 2026-07-11.

## A path literal whose backslashes never arrive

`SetObjectMaterial(idx, "dz\\data\\data\\mirror.rvmat")` written from a bash heredoc arrives in the file with a single backslash. Enforce drops escape sequences it does not recognize, so the engine received `dzdatadatamirror.rvmat`: the call ran, the log said yes, and nothing was rendered. It fails silently and looks green; the whole run was useless.

Write such literals by building the backslash in Python (`chr(92)`) and check the result with `repr()`. When the engine consumes the value, check in its log that it arrived intact before trusting the run: here the log itself printed the path it received, and the missing backslashes were visible there.

The same single backslash trap repeats at the size of a whole mod, so script path literals belong in an audit. [EXACT] Vanilla script literals write texture paths escaped and without a leading backslash (`"dz\\gear\\navigation\\data\\GPS_%1_ca.paa"`, `P:\scripts\4_world\entities\itembase\gear\navigation\gpsreceiver.c:4`). One mod shipped 64 `"\ModName\data\....rvmat"` literals with single backslashes in the source across 24 `.c` files, all of them its LEDs (measured in the LFPowerGrid mod). [DESIGN] Search the mod's `.c` files for string literals that carry a lone backslash inside a path, and print in the log the path the engine actually receives.
