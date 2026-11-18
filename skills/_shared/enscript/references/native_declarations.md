# Reference: `proto native` declarations

Where the engine's script surface is declared, what `owned` and `static` mean on a native, and how to call a native that fills an array or returns a handle. Every count and line below was taken on `P:\scripts`. A declaration proves the shape exists, not that the native is linked or behaves as hoped at run time (`language_compile.md`, "Symbols that are in the source but not in the build").

## Where natives are declared

Counting lines that begin with `proto native` (after white space), `P:\scripts` holds 2,789 declarations:

| Folder | `proto native` lines |
|---|---:|
| `1_core` | 565 |
| `2_gamelib` | 103 |
| `3_game` | 1,955 |
| `4_world` | 166 |
| `5_mission` | 0 |

Search `3_game` first and `1_core` second when checking whether a native exists. `5_mission` declares none, so an empty search there is expected. The count is of declaration lines, not of distinct APIs: overloads, the same name in several classes and lines inside `#ifdef` blocks all count. Lines written `static proto native` do not start with `proto native` and are not in it. Recount after a game update.

## `owned` and `static`

- `owned` qualifies the return value. `P:\scripts\1_core\proto\proto.c:14-16` defines it: the returned string or array must not be released by the script VM. It does not change how the method is called. 52 of the counted lines carry it.
- `static` makes it a type level call through the class name, with no instance. 25 counted lines are written `proto native static`.
- Instance or type level is decided by `static` and the enclosing class, never by `owned`. `GetObjectTexture` is an instance call because it is declared in `class EntityAI` without `static` (`P:\scripts\3_game\entities\entityai.c:2882`): call `entity.GetObjectTexture(0)`, and never pass the entity as an extra first argument. `GetSlotName` is `static proto native owned string GetSlotName(int id)` (`P:\scripts\3_game\systems\inventory\inventoryslots.c:48`): a type level call with an owned return.

## A native that fills an array: `GetBoneMatrix`

`proto native bool GetBoneMatrix(notnull IEntity ent, int bone, vector mat[4]);` is a free function (`P:\scripts\1_core\proto\envisual.c:41`). Declare `vector mat[4]`, pass it, and read the matrix out of it; the `bool` return only says whether it worked. There is no form that takes a single `vector`, and `GetBoneLocalMatrix` beside it takes the same array (`:42`).

```c
vector mat[4];
bool ok = GetBoneMatrix(ent, bone, mat);
```

## A static native that returns a handle: `AudioSystem.BankLoad`

`class AudioSystem` (`P:\scripts\1_core\proto\enaudio.c:3-9`) declares only static natives, and `AudioHandle` is `typedef int[] AudioHandle;` (`:1`). Call it through the type and hand the handle back to its sibling calls (`SoundPlay`, `SoundDestroy` at `:7-8`):

```c
AudioHandle bank = AudioSystem.BankLoad(path);   // P:\scripts\1_core\proto\enaudio.c:5
```
