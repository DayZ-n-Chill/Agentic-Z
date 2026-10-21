# Reference: Enforce Script types, classes and containers

Built in types, classes, enums, casting, parameters, arrays, maps, sets and templates. Every fact cites the vanilla file on `P:\scripts\` it was checked against. Line numbers are from game storage version 144 (`P:\scripts\3_game\global\game.c:5`); after a game update, search for the name if a line has moved.

## Built in types

| Type | What it is | Source |
|---|---|---|
| `int` | 32 bit signed integer. `int.MAX` is 2147483647 and `int.MIN` is -2147483648. | `P:\scripts\1_core\proto\enconvert.c:22`, `:27`, `:28` |
| `float` | Floating point number. A literal may carry an `f` suffix (`0.75242724772f`) but does not need one. | `P:\scripts\1_core\proto\enconvert.c:109`, `P:\scripts\3_game\gameplay.c:1316` |
| `bool` | `true` or `false`. `ToString()` gives `"true"` or `"false"`. | `P:\scripts\1_core\proto\enconvert.c:1` |
| `string` | Text. It has methods (`Length`, `Substring`, `IndexOf`, `Replace`, `ToLower`) and an empty constant `string.Empty`. | `P:\scripts\1_core\proto\enstring.c:5`, `:7` |
| `vector` | Three floats. Written as a string literal (`"0 1 0"`); `vector.Up`, `vector.Zero` and friends are constants. | `P:\scripts\1_core\proto\enconvert.c:118`, `:120` to `:123` |
| `typename` | A class type as a value. `Spawn()` makes an instance, `ToString()` gives the name, `IsInherited()` tests the parent. | `P:\scripts\1_core\proto\enconvert.c:556`, `:565`, `:574`, `:584` |
| `func` | A function reference, used by call queues and `ScriptInvoker`. | `P:\scripts\1_core\proto\enconvert.c:10`, `P:\scripts\2_gamelib\tools.c:57` |
| `Class` | Root of every class. | `P:\scripts\1_core\proto\enscript.c:10` |
| `Managed` | Root for script classes whose lifetime script manages (see `language_memory.md`). | `P:\scripts\1_core\proto\enscript.c:117` |

A string turns into a type with `"PlayerBase".ToType()` (`P:\scripts\1_core\proto\enstring.c:95`). Use `typename.EnumToString(MyEnum, value)` and `typename.StringToEnum(MyEnum, "NAME")` for enum names (`P:\scripts\1_core\proto\enconvert.c:598`, `:670`); `EnumTools` has the same helpers plus `GetEnumSize` and `GetLastEnumValue` (`P:\scripts\1_core\proto\enconvert.c:699` to `:750`).

## Type inference with `auto`

`auto` declares a local whose type comes from the right hand side. Vanilla uses it often:

```c
auto vehicle = CarScript.Cast(vehCommand.GetTransport());   // 4_world/.../actionstartengine.c:32
auto tmp = t.m_srcState.GetParentState();                  // 3_game/systems/hfsmbase.c:177
```

Sources: `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:32`, `P:\scripts\3_game\systems\hfsmbase.c:177`. Prefer explicit types in mod code so a reader sees the type; `auto` is legal, not a trap.

## Classes and members

- Inherit with `:` or `extends`; vanilla uses both (`class Param: Managed`, `class Param1<Class T1> extends Param`, `P:\scripts\1_core\param.c:11`, `:31`).
- The constructor and destructor are methods named after the class: `void Param1(T1 p1)` and `void ~ScriptRPC()` (`P:\scripts\1_core\param.c:35`, `P:\scripts\3_game\gameplay.c:107`).
- Access: `private` and `protected` on fields and methods (`P:\scripts\3_game\global\game.c:15`, `:72`). A private constructor stops script from creating the class (`P:\scripts\3_game\gameplay.c:383`).
- `static` and `const` combine: `static const int GEAR_COUNT = 3;` (`P:\scripts\3_game\analytics\analyticsmanagerclient.c:3`). A top level `const int` is a global constant (`P:\scripts\3_game\tools\tools.c:8`).
- `override` marks a method that replaces a parent method; call the parent with `super.Name(...)` (`P:\scripts\3_game\entities\entityai.c:3507`, `:3509`).
- `sealed class` cannot be inherited from (`P:\scripts\1_core\physics\contact.c:9`).
- `proto native` marks a method the engine implements. You can call it but never give it a body.
- `event` marks a method the engine calls (`P:\scripts\3_game\entities\inventoryitem.c:47`).

## Enums

```c
enum ErrorExSeverity { INFO, WARNING, ERROR, }       // 1_core/proto/endebug.c:61
enum CarFluid : ETransportFluid {};                  // 3_game/vehicles/car.c:18
```

Values count up from 0 unless set. An enum can extend another enum with `:` (`P:\scripts\3_game\vehicles\car.c:18`, `P:\scripts\3_game\enums\ediagmenugame.c:3`). Enum values are `int`.

## Casting

| Call | Result | Source |
|---|---|---|
| `PlayerBase.Cast(obj)` | The object as `PlayerBase`, or `null` when it is not one. | `P:\scripts\1_core\proto\enscript.c:94` |
| `Class.CastTo(player, obj)` | `true` and fills `player` when the cast works; `false` when it fails or `obj` is null. | `P:\scripts\1_core\proto\enscript.c:110` |
| `obj.IsInherited(PlayerBase)` | `true` when the instance is that type or a child. | `P:\scripts\1_core\proto\enscript.c:23` |
| `obj.Type()` / `obj.ClassName()` | The runtime type as `typename` or `string`. | `P:\scripts\1_core\proto\enscript.c:52`, `:37` |
| `obj.IsKindOf("Inventory_Base")` | Config class test, separate from script types. `GetGame().IsKindOf(className, parentName)` does the same for a class name. | `P:\scripts\3_game\entities\object.c:511`, `P:\scripts\3_game\global\game.c:1436` |

A template class casts the same way: `PlayerStat<float>.Cast(...)` (`P:\scripts\4_world\entities\manbase\playerbase.c:8201`).

## Parameters

- `out` fills a variable for the caller: `GetPlayers(out array<Man> players)` (`P:\scripts\3_game\global\game.c:945`).
- `inout` reads and writes it: `SanitizeMinsMaxs(inout vector min, inout vector max)` (`P:\scripts\1_core\proto\enconvert.c:542`).
- `notnull` makes passing `null` an error: `HasEntityInInventory(notnull EntityAI item)` (`P:\scripts\3_game\systems\inventory\inventory.c:118`).
- Default values work: `CreateObject(string type, vector pos, bool create_local = false, ...)` (`P:\scripts\3_game\global\game.c:691`).

## Static arrays

Fixed size, declared with brackets, and filled with braces:

```c
int statArray[4] = {6,9,2,3};          // 1_core/proto/serializer.c:22
vector mat[4];                         // 3_game/entities/entityai.c:2141
```

A transform is `vector mat[4]`: three axes then the position in `mat[3]` (`P:\scripts\3_game\entities\entityai.c:2141` to `:2143`).

## Dynamic containers

All three are templates in `P:\scripts\1_core\proto\enscript.c`. Brace initialisers work: `array<int> dynArray = {8,5,6,4};` (`P:\scripts\1_core\proto\serializer.c:23`). A local can also be created with constructor syntax, `array<Man> players();` (`P:\scripts\3_game\global\game.c:948`).

### `array<T>` (`enscript.c:374`)

| Method | Behaviour | Line |
|---|---|---|
| `Count()` | Number of elements. | 380 |
| `Insert(v)` | Appends; returns the new index. | 407 |
| `InsertAt(v, i)` | Inserts and shifts the rest up. | 418 |
| `Get(i)` / `arr[i]` / `Set(i, v)` | Read or write by index. | 399, 389 |
| `Find(v)` | First index of `v`, or -1. | 394 |
| `Remove(i)` | Fast removal that moves the last element into the gap, so order is lost. | 463 |
| `RemoveOrdered(i)` | Slower removal that keeps order. | 470 |
| `RemoveItem(v)` | Finds `v` and removes it keeping order. `RemoveItemUnOrdered(v)` uses the fast removal. | 502, 512 |
| `Clear()` | Destroys all elements; keeps the memory. | 385 |
| `Resize(n)` / `Reserve(n)` | Change the size, or only the capacity. | 476, 482 |
| `Sort(reverse = false)` | Ascending by default; pass `true` for descending. | 493 |
| `Copy(from)` | Replaces this array's contents with `from`'s. | 499 |
| `IsValidIndex(i)` | `true` when `0 <= i < Count()`. | 522 |
| `GetRandomElement()` | One random element. | 586 |

There is no `GetChecked`; vanilla has it commented out (`enscript.c:527` to `:535`). Check with `IsValidIndex` first. Typedefs such as `TStringArray` and `TIntArray` are at `enscript.c:731` to `:739`.

### `map<TKey, TValue>` (`enscript.c:846`)

| Method | Behaviour | Line |
|---|---|---|
| `Insert(k, v)` | Adds a new pair; the fast way to add. | 926 |
| `Set(k, v)` | Adds or replaces. | 902 |
| `Get(k)` | The value, or the type's default (`null`, 0) when missing. | 866 |
| `Find(k, out v)` | `true` and fills `v` when the key exists. Use it when 0 or `null` is a real value. | 877 |
| `Contains(k)` | Key test. | 917 |
| `Remove(k)` | Removes by key. | 906 |
| `GetKey(i)` / `GetElement(i)` | By position; each call is O(n), so avoid them in loops. | 897, 887 |
| `GetKeyArray()` / `GetValueArray()` | New arrays of keys or values. | 929 to 940 |

Iterate with `foreach`, which gives key then value:

```c
foreach (EDayZProfilesOptions e_opt, DayZProfilesOptionBool r_opt : m_DayZProfilesOptionsBool)   // 3_game/dayzgame.c:489
```

### `set<T>` (`enscript.c:741`)

An ordered list of unique values. Its API is `Count`, `Clear`, `Find(v)` (index or -1), `Get(i)`, `Insert(v)`, `InsertAt`, `Remove(index)`, `Copy`, `Swap`, plus the script helpers `InsertSet`, `RemoveItem(v)` and `RemoveItems` (`enscript.c:743` to `:805`). There is no `Contains`: test with `Find(v) != -1`. `Remove` takes an index, not a value; use `RemoveItem(v)` to remove by value.

### `foreach`

`foreach (T item : arr)` walks values; `foreach (int i, T item : arr)` adds the index (`P:\scripts\1_core\proto\enstring.c:427`, `P:\scripts\1_core\proto\enscript.c:600`).

## Templates

Declare type parameters with `Class`:

```c
class Param1<Class T1> extends Param      // 1_core/param.c:31
class JsonFileLoader<Class T>             // 3_game/tools/jsonfileloader.c:1
class map<Class TKey,Class TValue>        // 1_core/proto/enscript.c:846
```

Use them with concrete types: `new Param1<int>(55)` (`P:\scripts\1_core\param.c:26`). `Param1` to `Param4` and up carry values through RPCs, call queues and timers, and expose `param1`, `param2` and so on (`P:\scripts\1_core\param.c:33`).

## Strings

| Method | Behaviour | Source |
|---|---|---|
| `Length()` | Character count. | `enstring.c:199` |
| `Substring(start, len)` | Part of the string. | `enstring.c:113` |
| `IndexOf(s)`, `LastIndexOf(s)`, `IndexOfFrom(start, s)` | Position or -1. | `enstring.c:240`, `:253`, `:271` |
| `Contains(s)` | Substring test. | `enstring.c:286` |
| `Replace(a, b)` | Replaces in place; returns the count. | `enstring.c:156` |
| `ToLower()`, `ToUpper()` | Change the string in place; return its length. | `enstring.c:171`, `:186` |
| `Trim()` / `TrimInPlace()` | Returns a trimmed copy, or trims in place. | `enstring.c:304`, `:319` |
| `Split(sep, out arr)` / `string.Join(sep, arr)` | Split into an array and join back. | `enstring.c:396`, `:424` |
| `ToInt()`, `ToFloat()`, `ToVector()` | Parse. | `enstring.c:20`, `:46`, `:59` |
| `string.Format("%1 %2", a, b)` | Placeholders start at `%1`; up to nine values. | `enstring.c:526` |

There is no `StartsWith`, `EndsWith`, `ToUppercase` or `ToLowercase` in vanilla `enstring.c`. All paths are under `P:\scripts\1_core\proto\`.
