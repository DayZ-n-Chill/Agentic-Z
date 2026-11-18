# Language limits and built-ins

What the language allows (parameter count, generic classes, typedefs, float constants), how the string and math calls behave, how to look up config, and the language additions in 1.30. The full type and collection reference is `../references/language_types.md` and `../references/types_collections.md`.

## Language limits

- A method takes at most 16 parameters. Measured in game on a 1.30 dedicated server: a 16 parameter static method compiled and returned the right value; with a 17th parameter the mission failed with `Maximum arguments count 16 exceeded in method 'Sum'` and `Can't compile mission init script`. Past 16, pass one object that carries the values.
- Script classes can be generic, with the same syntax as vanilla's containers: `class array<Class T>` (`P:\scripts\1_core\proto\enscript.c:374`) and `class map<Class TKey,Class TValue>` (`:846`). Measured in game: `class Box<Class T> { T m_Value; }` worked as `Box<int>` and `Box<string>` in one script.
- Container typedefs: `TFloatArray`, `TIntArray` and `TVectorArray` (`enscript.c:732`, `:733`, `:738`); `TStringStringMap = map<string, string>` (`enscript.c:1004`) and its twin `TStringMap` (`P:\scripts\3_game\tools\tools.c:988`).
- `FLT_MAX` and `FLT_MIN` are engine globals (listed at `P:\scripts\1_core\proto\enscript.c:4` and `:5`, used by `float.MAX` and `float.MIN` at `P:\scripts\1_core\proto\enconvert.c:111` to `:113`). The vanilla comment calls `FLT_MIN` "The minimum value for float", but it is the smallest positive normal float, not the most negative one: measured in game, `FLT_MAX` is `3.40282e+38` and `FLT_MIN` is `1.17549e-38`. Start a maximum search from `float.LOWEST`, which is `-FLT_MAX` (`enconvert.c:113`).
- `ftime` is a global float documented as the time since the last frame (`enscript.c:3`). Read in the mission's `main()`, before any frame has run, it is `0` (measured in game).

## Strings

On `string` (`P:\scripts\1_core\proto\enstring.c`): `ToType` `:95`, `Substring` `:113`, `Replace` `:156`, `ToLower` `:171`, `Hash` `:223`, `LastIndexOf` `:253`, `IndexOfFrom` `:271`.

```c
string full = "Hello World";
string sub = full.Substring(0, 5);      // Substring(start, length): "Hello"
int pos = full.IndexOf("World");        // 6, or -1 when not found
int next = full.IndexOfFrom(pos, "o");  // search from a position
int last = path.LastIndexOf("\\");
int h = myString.Hash();                // an int
int count = myString.Replace(":", "");  // changes the string, returns the number replaced

string lower = original + "";           // "+" forces a copy
lower.ToLower();                        // changes the string in place, returns its length

string firstChar = str[0];              // a string of length 1
int n = str.ToInt();
float f = str.ToFloat();
string msg = "Count: " + val.ToString();
```

`ToLower` and `Replace` change the string they are called on, so copy first when you still need the original.

## Math and vectors

`Math.Clamp` (`P:\scripts\1_core\proto\enmath.c:540`), `VectorToAngles` (`P:\scripts\1_core\proto\enconvert.c:374`), `GetScreenPos` (`P:\scripts\3_game\global\game.c:963`). The rest of `Math` and `vector` is in `../references/types_collections.md`.

```c
float clamped = Math.Clamp(value, 0, 1.0);
int floored = Math.Floor(3.7);        // 3
int rounded = Math.Round(3.5);        // 4
int ceiled = Math.Ceil(3.1);          // 4
int rnd = Math.RandomInt(200, int.MAX - 1);

float dist = vector.Distance(posA, posB);
float distSq = vector.DistanceSq(posA, posB);   // no square root
vector norm = dir.Normalized();
vector angles = dir.VectorToAngles();           // [0] yaw, [1] pitch

float groundY = GetGame().SurfaceY(x, z);              // terrain height
vector screenPos = GetGame().GetScreenPos(worldPos);   // world to screen
```

## Config lookups

`ConfigIsExisting` (`P:\scripts\3_game\global\game.c:612`) and `ConfigGetIntArray` (`game.c:585`). A config path is space separated:

```c
if (GetGame().ConfigIsExisting("CfgVehicles " + className))
{
    TIntArray itemSize = new TIntArray;
    GetGame().ConfigGetIntArray("CfgVehicles " + className + " itemSize[]", itemSize);
}
```

Vanilla builds the path with no trailing space: `ConfigIsExisting(CFG_VEHICLESPATH+" "+type_name)` (`P:\scripts\4_world\systems\inventory\attachmentsoutofreach.c:82`). Write new code the same way. A trailing space after the class name still finds an existing class (measured in game on 1.29). With a class that doesn't exist it is untested, so a false positive through that path is not ruled out.

## Additions and removals in 1.30

| Change | Source |
|---|---|
| `array<T>.Slice(int from, int to)`; `to` is inclusive | `P:\scripts\1_core\proto\enscript.c:720` to `:727` |
| `typename.EnumFlagsToString` and `EnumTools.EnumFlagsToString` | `P:\scripts\1_core\proto\enconvert.c:614` and `:704` |
| `class DoOnce`, to run a method by name once per key | `P:\scripts\3_game\doonce.c:1` |
| `GAME_STORAGE_VERSION = 144`; 1.29 had `142` on the same line | `P:\scripts\3_game\global\game.c:5` |
| `vector.Cross(vector v)` existed in 1.30 Experimental and the 1.30 release, and the first 1.30 patch removed it. `P:\` still shows it because its extraction is older (`../references/game_builds.md`). Write the cross product out instead of calling `Cross` | `enconvert.c:239` to `:246` |

The full 1.30 changes are in `dayz-1-30-enforce-script.md`.
