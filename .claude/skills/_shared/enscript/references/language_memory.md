# Reference: object lifetime, `ref` and `autoptr`

Who owns an object, when it is freed, and how entities are deleted. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`). Rules marked "engine behaviour" describe what the script VM does; the source shows the pattern but not the VM itself.

## The two roots

- `Class` is the root of every class (`P:\scripts\1_core\proto\enscript.c:10`). Entities (`Object`, `EntityAI`, `ItemBase`, `PlayerBase`) are owned by the engine, not by script references.
- `Managed` is the root for script objects that script owns (`P:\scripts\1_core\proto\enscript.c:117`). `Param`, `TimerBase`, `Serializer` and `PlayerIdentityBase` all derive from it (`P:\scripts\1_core\param.c:11`, `P:\scripts\3_game\tools\tools.c:219`, `P:\scripts\1_core\proto\serializer.c:55`, `P:\scripts\3_game\gameplay.c:338`).
- Give your own helper, manager and data classes `Managed` (or a vanilla class that has it) as the root.

## `ref` keeps an object alive

Engine behaviour: a `Managed` object is freed when the last strong reference to it goes away, and a plain reference does not keep it alive.

| Declaration | Meaning | Vanilla example |
|---|---|---|
| `ref Foo m_Foo;` | Strong. This object owns `m_Foo`. | `ref ModifiersManager m_ModifiersManager;` set with `new` in the constructor (`P:\scripts\4_world\entities\manbase\playerbase.c:88`, `:430`) |
| `Foo m_Foo;` | Weak. Points at an object someone else owns. | `Timer` keeps its target as `protected Managed m_target;` so a timer never keeps its target alive (`P:\scripts\3_game\tools\tools.c:578`) |
| `ref array<ref Foo>` | The array is owned and so is every element. | `protected static ref map<int, ref Effect> m_EffectsMap;` (`P:\scripts\3_game\effectmanager.c:8`); vanilla notes that registering "will make SEffectManager hold a strong ref for the Effect" (`:327`) |
| `array<Foo>` inside a `ref array` | The array is owned, the elements are not. | `typedef array<Managed> TManagedArray;` against `typedef array<ref Managed> TManagedRefArray;` (`P:\scripts\1_core\proto\enscript.c:736`, `:737`) |

Rules that follow:

1. A member that you create with `new` and that nothing else holds must be `ref`, or it is freed at once (engine behaviour). The symptom is a member that reads `null` right after it was set.
2. Containers of objects you create need `ref` on the element type too: `ref array<ref MyData>`.
3. Parent owns child with `ref`; child points back at the parent without `ref`. Two `ref`s pointing at each other keep both alive forever.
4. Never `ref` an entity or a `PlayerIdentity`. The engine owns them. `PlayerIdentityBase` says "This is a C++ managed class, so script has no business managing the lifetime" (`P:\scripts\3_game\gameplay.c:382`). Hold a plain reference and null check it before every use.
5. Do not keep engine handles the source tells you not to keep, such as `SurfaceInfo` ("don't store handles of this type yourself", `P:\scripts\3_game\surfaceinfo.c:5`).

## `autoptr`

`autoptr` is the older owning qualifier. Vanilla uses it in ten files, mostly in `1_core` docs and examples: `autoptr map<string, int> prg_count = new map<string, int>;` (`P:\scripts\1_core\proto\enscript.c:834`) and `autoptr map<string, float> m_values;` as a member (`P:\scripts\1_core\proto\serializer.c:14`). Newer vanilla code uses `ref` for members. Use `ref` in mod code.

## Locals

A local created with `new` lives for the scope that uses it (engine behaviour), so short lived helpers need no `ref`: `InventoryLocation il = new InventoryLocation();` (`P:\scripts\3_game\entities\entityai.c:2140`). A local can also be built with constructor syntax, `array<Man> players();` (`P:\scripts\3_game\global\game.c:948`).

## Freeing script objects

- `delete obj;` frees a script object now: `delete GetBleedingManagerServer();` (`P:\scripts\4_world\entities\manbase\playerbase.c:1224`). An object may free itself with `delete this;` (`P:\scripts\4_world\classes\bullethitreaction\bullethitreaction.c:45`).
- Setting the last `ref` to `null` also frees it (engine behaviour).

## Deleting entities

Never use `delete` on an entity. Use the engine calls:

| Call | What it does | Source |
|---|---|---|
| `obj.Delete()` | Queues `ObjectDelete` for the next frame on `CALL_CATEGORY_SYSTEM`. `EntityAI` also marks it pending. | `P:\scripts\3_game\entities\object.c:82`, `P:\scripts\3_game\entities\entityai.c:779` |
| `item.DeleteSafe()` | Calls `Delete()` when no live player holds it. When a live player does, a multiplayer server deletes it through a juncture and anything else queues it on the player. Use it for items that may sit in a player's inventory. | `P:\scripts\3_game\entities\entityai.c:791` |
| `obj.DeleteOnClient()` | Deletes only the local copy on this client. | `P:\scripts\3_game\entities\entityai.c:785` |
| `GetGame().ObjectDelete(obj)` | The engine delete that the calls above queue. | `P:\scripts\3_game\global\game.c:705` |

Because `Delete()` runs next frame, the object is still valid for the rest of the current call.

## Calls and timers that outlive their target

- A call queue holds the arguments of a queued call until it runs or is removed (`P:\scripts\2_gamelib\tools.c:56`). Remove your own queued calls when the object goes away; vanilla does it in `EEDelete` (`P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c:23` to `:25`).
- A `Timer` holds its target weakly (rule above) and its `Param` strongly (`protected ref Param m_params;`, `P:\scripts\3_game\tools\tools.c:580`). Keep the `Timer` itself in a `ref` member, then call `Stop()` when you are done (`P:\scripts\3_game\tools\tools.c:617`).

See `api_scheduling.md` for the call queue and timer API.
