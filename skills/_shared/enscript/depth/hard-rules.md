# Enforce Script hard rules

Which rules apply to every piece of Enforce Script, each tied to a crash, a failed compile or a silent failure seen in a real mod. Rules for actions, inputs and cameras are in `action-and-input-rules.md`.

## Check the symbol is live before you call it

Before treating a vanilla API as callable, check that it is not inside an `#ifdef` whose macro is never defined. Search `P:\scripts\` for `#ifdef <MACRO>` and `#define <MACRO>`; if only `#ifdef` lines appear, the code is dead and the symbol does not exist.

`ActionManagerClient.PerformAction(int user_action_id, ActionTarget, ItemBase, Param)` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:798`) sits inside `#ifdef BOT` (`:796` to `:802`), and `BOT` is never defined anywhere in vanilla, so it exists in neither retail nor diag. The public way to start an action from script is `PerformActionStart(ActionBase, ActionTarget, ItemBase, Param)` (`:804`). Its 1.30 behaviour is in `dayz-1-30-actions.md`.

A `proto native` line proves the declaration, not that the engine links a native behind it. `proto native int GetFPS();` is declared at `P:\scripts\1_core\proto\proto.c:147`, yet on DayZ 1.29 diag every call throws `Virtual Machine Exception` with `Function 'GetFPS' not linked` (measured in game). Call a `proto native` API once from a throwaway script before building on it, and for capture, rendering, hardware or file APIs run a probe that produces the real result.

`CCINone` means "no item condition", not "hands empty": its `Can()` returns true for anything (`P:\scripts\4_world\classes\useractionscomponent\itemconditioncomponents\ccinone.c:3`).

## Time and player identity

- `CGame.GetTime()` is mission time in milliseconds (`P:\scripts\3_game\global\game.c:1534`) and restarts at every boot. Use it for durations within one session, never for a stored timestamp or ordering across restarts.
- Build wall clock time from `GetYearMonthDayUTC` (`P:\scripts\1_core\proto\ensystem.c:100`) and `GetHourMinuteSecondUTC` (`:76`), and store every part the ordering needs.
- `PlayerIdentity.GetId()` is the hashed ID meant for databases and logs (`P:\scripts\3_game\gameplay.c:367` and `:368`). `GetPlainId()` is marked not for databases or logs (`:369` and `:370`), and `GetPlayerId()` is a session ID reused after the player leaves (`:371` and `:372`). Neither is a durable owner key.

## Syntax

- No ternary operator: `condition ? a : b` does not compile. Use an `if`.
- `++` and `--` work, prefix and postfix; so do `+=` and `-=`.
- `foreach (Type var : array)` and `foreach (key, value : map)` work. Never run `foreach` over a call that returns a temporary collection (reported to hit a null pointer; see `memory-management.md`).
- String literals work as arguments (`MyFunc("hello", "world")`); vanilla passes them everywhere, for example `layoutRoot.FindAnyWidget("continuebtn")` (`P:\scripts\5_mission\gui\ingamemenu.c:40`), so there is no need to copy a literal into a local first. Inline concatenation works (`"Count: " + val + " items"`).
- Keep each statement on one line, and split a long string build into single-line statements (`ln = ln + ...;`). A condition split at `&&` or `||`, a string `+` chain continued on the next line, or a call whose argument list spans lines can stop the whole module (`Can't compile "Mission" script module!`, measured in game). The error lands on the next argument's line and is followed by `Syntax error` and `Unexpected scope`, which look like a corrupt file. Vanilla does hold some multi-line argument lists (`Math.Lerp(` at `P:\scripts\3_game\worlddata.c:153` to `:156`, `new NotificationData(` at `P:\scripts\3_game\client\notifications\notificationsystem.c:307` to `:311`), so exactly what is safe is not known. Treat any line that ends in `(` or `,` after comments are stripped as a risk. Tests that only read the source text pass while the engine rejects the file.
- Declare a variable once before the `if`, not in both the `if` and the `else` (see `compiler-traps.md`, section "Locals have method scope").
- Declare variables before loops and conditions, type everything explicitly, and prefix member fields with `m_`.
- Never create an `array`, `map` or `Param` inside a periodic tick; keep `m_` fields and `Clear()` them.
- A class constant read from a `static` method must be `static const`. A plain `const` there was fatal on a retail server (measured in game). Check with a retail boot with `SERVER` defined; when errors cascade, fix the first and compile again.
- `%` works only on integers. `float ox = (n % 4) * 0.7 - 1.05;` with `int n` fails with `Unknown operator '%'` and stops the module (measured in game on DayZ 1.30; see `pitfalls-advanced.md`). Every vanilla modulo has integer operands, such as `new_index % count` (`P:\scripts\1_core\proto\enscript.c:652` to `:661`) and `startTime.ToInt() % 100` (`P:\scripts\3_game\cfgbunkerbroadcastjsondata.c:196`). Compute `int col = n % 4;` first, then multiply.

## What the language lacks

| Trap | What to do | Checked |
|---|---|---|
| No `do ... while` | Use `while` or `for` | No vanilla script under `P:\scripts\` uses `do` |
| No `try`, `catch` or `throw` | Return a failure value (`../patterns/language_workarounds.md`) | Reported |
| `switch` cases fall through without `break` | Always `break` unless you mean it | Reported |
| No `nullptr` | Use `null` or `NULL` | Reported |
| No `#include`, no namespaces | Modules come from `CfgMods` `defs` | Reported |
| Defaults must be literals or `NULL` | No call expressions as defaults | Reported |
| `GetGame().GetPlayer()` is null on a dedicated server | It is the local player only; on the server use `GetPlayers` (`P:\scripts\3_game\global\game.c:945`). Not the same null as during client preload (`runtime-traps.md`) | Reported |
| `sealed` classes and methods (1.28 and later) | Cannot be extended or overridden | `sealed class Contact` (`P:\scripts\1_core\physics\contact.c:9`) |
| At most 16 parameters per method (1.28 and later) | Pass a data class | Reported |
| `array.Remove` does not keep order | It moves the last element into the gap (`P:\scripts\1_core\proto\enscript.c:457` to `:463`); use `RemoveOrdered` (`:470`) | Read on `P:\` |

Some string methods change the string in place and return a count, not a new string: `Replace` (`P:\scripts\1_core\proto\enstring.c:156`), `ToLower` (`:171`), `ToUpper` (`:186`) and `TrimInPlace` (`:319`); `Trim()` (`:304`) returns a new string. Reported and not checked on `P:\`: an empty `#ifdef` block can break the compile (a block holding only a comment compiled; `pitfalls-advanced.md`); a `crash_*.log` name does not prove an engine crash; compile errors sometimes name the wrong file; bracket a bitwise test before comparing it; clean up `Obsolete` warnings. `JsonFileLoader.JsonLoadFile` returns `void` (`P:\scripts\3_game\tools\jsonfileloader.c:105`); `persistence-and-files.md` names the calls that return a status.

## Memory

- `ref` on a member field keeps its target alive. On a local it is valid but redundant, since locals are strong. Never put `ref` on a parameter or return type: the diag compiler rejects it as fatal while retail lets it pass (`review-and-troubleshooting.md`, row "Method argument can't be strong reference").
- Never put `ref` and `autoptr` on the same field; pick one.
- Never `delete` an object something else still uses; it ends in a segfault, and setting the reference to `null` is enough. `delete` is legal on objects you own, as vanilla does (`delete GetBleedingManagerServer();`, `P:\scripts\4_world\entities\manbase\playerbase.c:1224`), and never the way to remove an entity. Full rules: `../references/language_memory.md`.
- A field without `ref` is weak, for `Managed` and plain classes alike, and reads `NULL` once the last strong reference goes (measured; see `memory-management.md`).
- Reference counting cannot free a cycle, so break cycles in destructors.

## Networking and sides

- Write synced variables only on the server, inside `#ifdef SERVER`, then call `SetSynchDirty()`. Code that must also run in single player checks `GetGame().IsServer()`, because `SERVER` is not defined there (`../references/language_compile.md`).
- Check the return of every `ctx.Read()` and return on failure.
- On the server, validate every RPC sender: its identity, and that its ID matches the target `PlayerBase`. Rate limit per player, and reject by default even when the payload looks harmless.
- During load and init (constructors, module init, `OnInit`), tell the sides apart with `IsDedicatedServer()`, which vanilla calls the "robust check ... valid much sooner" (`P:\scripts\3_game\global\game.c:1121` to `:1125`). Reported, not checked on `P:\`: `IsServer()` returns true on the client during load, and `IsClient()` is not reliable then; use `!IsDedicatedServer()`. In callbacks after load (`OnRPC`, `EOnContact`, a tick) `IsServer()` and `IsClient()` are safe and are what vanilla uses.
- The 1.30 inventory network path is in `dayz-1-30-inventory.md`.

## Timers

- Reported, not checkable on `P:\`: `CallLater` loses precision after about 4.5 hours. `CallLater` is `proto` and takes an `int` of milliseconds (`P:\scripts\2_gamelib\tools.c:61`); `../patterns/scheduler.md` gives the `Timer` alternative.
- Reported on a long running server: one repeating `CallLater` per device fragments the heap and crashes after hours.
- Run all periodic ticks from one manager with register and unregister calls. A singleton alone is not enough: its `Reset()` on reconnect orphans the repeat timer, because the `Remove()` lives in the dropped instance's destructor, so the queue keeps firing into a dead object. Drive those ticks from the mission's `OnUpdate` with a `timeslice` accumulator and fetch the singleton through `Get()` each frame; nothing is registered, so nothing is orphaned. Reset the accumulator to zero when it fires, so a long hitch fires once rather than in a burst, and never skip the maintenance call when there is nothing to draw, because retry and reconcile ticks exist to build what is not drawn yet. Measured in game: five repeating `CALL_CATEGORY_GUI` chains became one `MaintenanceTick(timeslice)` call per renderer.

## Overrides and modded classes

- An `override` keeps the base class's parameter names. Reported, not checked on `P:\`: different names fail silently at runtime.
- A `modded class` can add member fields; a shipped mod's modded `DayZGame` adds more than ten. For `ItemBase` and `PlayerBase`, a static map keyed by entity ID is the cautious choice (`../patterns/modded_class.md`, "Adding fields safely").
- Two `modded class` declarations of the same class can live in different files.
- Before varying an engine call, reproduce the exact vanilla call site. If that fails too, stop changing syntax and isolate the context: server or client, headless or not, build and defines.
- Never initialize an opaque engine handle with a literal (`FileHandle handle = 0`). Declare it, assign the API's return, and guard on the value that API documents.

## Serialization and cleanup

- `[NonSerialized()]` keeps a runtime field out of serialization (`P:\scripts\1_core\proto\serializer.c:16`). Check that it stays out of your JSON before relying on it.
- Remove `ScriptInvoker` subscriptions in the destructor, after a null check: `if (MyClass.Event_X) MyClass.Event_X.Remove(callback);`.
- `Widget.Unlink()` destroys the widget and all its children (`P:\scripts\1_core\proto\enwidgets.c:173`); use it for UI cleanup instead of `delete`.

## Layouts and menus

- Layout paths must match `$PBOPREFIX$`: with prefix `MyMod`, use `MyMod/gui/layouts/...`. A mismatch crashes and leaves a ghost menu in `UIManager`.
- After `new` on a Dabs `ScriptViewMenu`, check `GetLayoutRoot()`. If it is null, set the singleton to null (never `delete`); a failed menu leaves a ghost entry in `UIManager` that blocks every later menu.

Full UI and Dabs material: `_shared/ui/` and `../integrations/dabs_framework.md`.
