# Native declarations

Where the engine's `proto native` declarations live, what `owned` and `static` mean on one, and how to call a native that fills an array or returns a handle. A declaration proves the shape exists, not that the native is linked or behaves as hoped at run time (`language_compile.md`, section "Symbols that are in the source but not in the build").

## Where natives are declared

Counting lines that begin with `proto native` (after white space), the five module folders of `P:\scripts` hold 2,758 declarations:

| Folder | `proto native` lines |
|---|---:|
| `1_core` | 533 |
| `2_gamelib` | 103 |
| `3_game` | 1,956 |
| `4_world` | 166 |
| `5_mission` | 0 |

Search `3_game` first and `1_core` second when you check whether a native exists. `5_mission` declares none, so an empty search there is expected.

The count is of declaration lines, not of distinct calls: overloads, the same name in several classes and lines inside `#ifdef` blocks all count. Lines written `static proto native` don't start with `proto native` and are left out. Count again after a game update.

## `owned` and `static`

- `owned` qualifies the return value. `P:\scripts\1_core\proto\proto.c:14` to `:16` defines it: the returned string or array must not be released by the script VM. It doesn't change how the method is called. 52 of the counted lines carry it.
- `static` makes it a call on the type, through the class name, with no instance. 25 counted lines are written `proto native static`.

Whether a call needs an instance is decided by `static` and the enclosing class, never by `owned`. `GetObjectTexture` is an instance call because it is declared in `class EntityAI` without `static` (`P:\scripts\3_game\entities\entityai.c:2882`): call `entity.GetObjectTexture(0)`, and never pass the entity as an extra first argument. `GetSlotName` is `static proto native owned string GetSlotName(int id)` (`P:\scripts\3_game\systems\inventory\inventoryslots.c:48`): a call on the type with an owned return.

## A native that fills an array: `GetBoneMatrix`

`proto native bool GetBoneMatrix(notnull IEntity ent, int bone, vector mat[4]);` is a free function (`P:\scripts\1_core\proto\envisual.c:41`). Declare `vector mat[4]`, pass it, and read the matrix out of it; the `bool` return only says whether the call worked. There is no form that takes a single `vector`, and `GetBoneLocalMatrix` beside it takes the same array (`:42`).

```c
vector mat[4];
bool ok = GetBoneMatrix(ent, bone, mat);
```

## A static native that returns a handle: `AudioSystem.BankLoad`

`class AudioSystem` (`P:\scripts\1_core\proto\enaudio.c:3` to `:9`) declares only static natives, and `AudioHandle` is `typedef int[] AudioHandle;` (`:1`). Call it through the type, then hand the handle to its sibling calls (`SoundPlay`, `SoundDestroy` at `:7` and `:8`):

```c
AudioHandle bank = AudioSystem.BankLoad(path);   // P:\scripts\1_core\proto\enaudio.c:5
```
