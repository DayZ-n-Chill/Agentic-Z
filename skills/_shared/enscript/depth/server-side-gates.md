# Server-side gates and script memory

When to keep work off the client with `#ifdef SERVER` and when to branch at runtime, why `#ifndef SERVER` can break other mods, why an event bus beats polling, and which changes actually lower a dedicated server's script memory. The tick budget techniques are in `server-performance.md`.

## Compile-time gate or runtime check

Both mean "only on the server", but they resolve at different times. The runtime checks are `IsServer()` and `IsDedicatedServer()` (`P:\scripts\3_game\global\game.c:1120` and `:1125`).

| | `#ifdef SERVER` | `IsServer()`, `IsDedicatedServer()` |
|---|---|---|
| Resolves | At compile time; the code is absent from the client build | At runtime, in a build holding both paths |
| Use for | Whole subsystems that never run on a client: synced variable writes, heavy propagation, disk access, diagnostics | One branch of a method that runs on both sides, such as an `OnRPC` that validates on the server and applies on the client |
| Client cost | None | A branch per call |

During load use `IsDedicatedServer()` or `!IsDedicatedServer()`, not `IsServer()` or `IsClient()`; after load either is safe (`hard-rules.md`, section "Networking and sides"). The client-only resource guard in `rpc-and-input-patterns.md` is a lazy runtime check. Never put a runtime `IsServer()` in a hot per-tick path when a compile-time gate on the subsystem would remove the branch. The defines vanilla uses are in `../references/language_compile.md`.

### `#ifndef SERVER` removes the type from the server

`SERVER` is defined only in the dedicated server executable, not offline or on a listen server. A class wrapped in `#ifndef SERVER` does not exist on the dedicated server, so any other mod or server handler that names it fails with `Unknown type 'X'`, then `Can't compile "World" script module!`, and the server does not start. Measured in game: a viewport class inside `#ifndef SERVER` broke another mod that referenced it.

Checking your own mod does not catch this; the break is in the contract with other mods. Before guarding a symbol, ask whether anything else on the server names it. If so, keep the type in both builds, with a stub under `#ifdef SERVER` that has the signatures the other code touches and empty bodies; plain data classes cost nothing left unguarded. Test by compiling with `SERVER` defined on a dedicated server: offline does not define it, so it passes locally and breaks on the server.

## Events instead of polling

Polling asks every tick whether anything changed; an event bus is told when something did and does nothing otherwise. `ScriptInvoker` is vanilla's event primitive (`P:\scripts\2_gamelib\tools.c:115`; `Invoke` at `:118`, `Insert` at `:120`, `Remove` at `:122`).

```c
// Producer
static ref ScriptInvoker Event_TopologyChanged = new ScriptInvoker();
void OnDeviceMovedOrCut() { Event_TopologyChanged.Invoke(this); }

// Consumer
void Init() { Event_TopologyChanged.Insert(OnTopologyChanged); }
void OnTopologyChanged(EntityAI src) { }   // validate only the affected part
```

The self-heal in `server-performance.md` runs 500 ms after a move or cut event instead of being polled, so the expensive validation runs only when the topology really changes.

Match every `Insert(cb)` with `Remove(cb)` in the consumer's destructor, after a null check: `if (Producer.Event_X) Producer.Event_X.Remove(OnTopologyChanged);`. A leftover subscription keeps a dead consumer reachable, and `Remove` on a freed invoker can crash at shutdown (`../patterns/singleton.md`).

Use a bus when changes are rare compared with ticks: topology edits, power changes, players joining and leaving. When a value changes every tick anyway, such as a position sampled each frame, read it directly; a bus adds fan-out without saving a scan.

## What lowers server script memory

Measured on a dedicated server with a large mod, about 2,380 script files and 6,140 classes, comparing the static `World` script memory in kB:

| Change | Effect on `World` |
|---|---|
| Merging or repackaging files under `4_World` (2,383 files to 2,367, classes unchanged) | None, in two repetitions |
| Removing comments and whitespace | About none |
| Removing a few classes (6,140 to 6,137; 6,110 to 6,109) | None at that scale |
| Cleaning at the bytecode level, class count unchanged | 18 to 29 kB lower |
| `#ifndef SERVER` around client-only code | Lower; the code is not compiled on the server |
| Collapsing generic specialisations, such as `array<T>` to `array<EntityAI>` with a cast | Lower |
| Managed class aliases for types used inside generics | Lower |

There is no simple law from class count to kB. Before budgeting a "remove dead code" pass, measure how much of it is already inside `#ifndef SERVER`. A duplicated UI copy of 182.4 KB of source looked like an easy win, but a count that respected nesting found about 97 percent already excluded, so only about 5.5 KB compiled on the server and removing it would save 3 to 4 kB, not the roughly 118 kB a byte ratio suggested.

As a rough guide, the server holds about 0.65 kB of static memory per KB of compiled `4_World` source; a cross-check on the same mod gave about 1.06 (1,522 kB over about 1,429 KB of server-side source). Use it to rule changes out, never to promise a number.

To measure a change, run three boots side by side (without the mod, the baseline, the candidate), twice. The noise is about 1 kB, since the value is a whole number, so a target smaller than that cannot tell a real change from none.
