# Reference: Core Types and Collections

Quick examples. Every method below was checked against its declaration on `P:\scripts\1_core\proto\` (the file and first line are given under each block). The longer reference is `language_types.md`.

## Contents

- [Primitive Types](#primitive-types)
- [string API](#string-api)
- [array\<T\>](#arrayt)
- [map\<K, V\>](#mapk-v)
- [set\<T\>](#sett)
- [vector API](#vector-api)
- [Math API (Math class)](#math-api-math-class)
- [⚠️ `string.ToLower()` / `ToUpper()` mutate in place](#-stringtolower--toupper-mutate-in-place)
- [Existence — these vanilla helpers DO exist](#existence--these-vanilla-helpers-do-exist)
- [Reported: `int.MIN` comparison quirk](#reported-intmin-comparison-quirk)

## Primitive Types

| Type | Default | Notes |
|---|---|---|
| `int` | `0` | 32-bit signed integer |
| `float` | `0.0` | 32-bit float; an `f` suffix on literals (`1.5f`) is allowed but optional |
| `bool` | `false` | `true` / `false` |
| `string` | `""` | Value type; use `+` to concat. `ToLower`, `ToUpper` and `Replace` change it in place |
| `vector` | `"0 0 0"` | 3-component float; literal syntax: `"1.5 0 -3"` |

Primitives are **never null**. Checking `if (myInt == null)` is either a no-op or a compile error.

---

## string API

```c
string s = "Hello, World!";

int    len     = s.Length();              // 13
bool   has     = s.Contains("World");
int    idx     = s.IndexOf(",");          // 5; -1 if not found
// No StartsWith/EndsWith: use s.IndexOf("Hello") == 0
// ToUpper()/ToLower() change s in place (see below)
string sub     = s.Substring(7, 5);      // "World"
string trimmed = s.Trim();
int    asInt   = "42".ToInt();
float  asFloat = "3.14".ToFloat();

// Format: %1, %2, ... placeholders (1-indexed)
string fmted = string.Format("X=%1 Y=%2", x, y);

// Split
array<string> parts = new array<string>();
s.Split(",", parts);                      // parts = ["Hello", " World!"]

// Contains check
if (s.IndexOf("World") != -1) { }
```

Declared in `P:\scripts\1_core\proto\enstring.c`: `ToInt` `:20`, `ToFloat` `:46`, `Substring` `:113`, `Replace` `:156`, `ToLower` `:171`, `ToUpper` `:186`, `Length` `:199`, `IndexOf` `:240`, `LastIndexOf` `:253`, `IndexOfFrom` `:271`, `Contains` `:286`, `Trim` `:304`, `Split` `:396`, `Format` `:526`.

---

## array\<T\>

```c
ref array<string> arr = new array<string>();

arr.Insert("a");            // append
arr.InsertAt("b", 0);       // insert at index
int cnt = arr.Count();
string val = arr[0];
arr.Set(0, "z");
arr.Remove(0);              // remove by index; moves the last element into the gap
arr.RemoveOrdered(0);       // remove by index, keeping order
arr.RemoveItem("z");        // remove by value, keeping order (linear scan)
arr.Clear();
arr.Copy(otherArr);         // replace arr's contents with otherArr's
arr.Sort();                 // ascending; Sort(true) = descending

// Iteration
foreach (string item : arr)
    Print(item);

// Find index (returns -1 if not found)
int i = arr.Find("a");
```

`class array<Class T>` is `P:\scripts\1_core\proto\enscript.c:374`: `Count` `:380`, `Clear` `:385`, `Set` `:389`, `Find` `:394`, `Get` `:399`, `Insert` `:407`, `InsertAt` `:418`, `Remove` `:463` (vanilla: "the empty position is replaced by last element", `:458` to `:459`), `RemoveOrdered` `:470`, `Sort(bool reverse = false)` `:493`, `Copy(from)` `:499` (copies `from` into this array), `RemoveItem` `:502`.

---

## map\<K, V\>

```c
ref map<string, int> scores = new map<string, int>();

scores.Set("Alice", 100);
scores.Set("Bob",   80);

int aliceScore = scores.Get("Alice");    // 100
bool hasKey    = scores.Contains("Bob");
scores.Remove("Bob");

int cnt = scores.Count();

// Iterate keys
for (int i = 0; i < scores.Count(); i++)
{
    string key = scores.GetKey(i);
    int    val = scores.GetElement(i);
}
```

`class map<Class TKey,Class TValue>` is `P:\scripts\1_core\proto\enscript.c:846`: `Get` `:866`, `GetElement` `:887`, `GetKey` `:897`, `Set` `:902`, `Remove(key)` `:906`, `Contains` `:917`.

---

## set\<T\>

```c
ref set<string> seen = new set<string>();

seen.Insert("item_a");
bool has = seen.Find("item_a") != -1;   // set has no Contains
seen.RemoveItem("item_a");              // Remove(i) takes an index
int cnt = seen.Count();
```

`class set<Class T>` is `P:\scripts\1_core\proto\enscript.c:741`: `Find` `:749`, `Insert` `:758`, `Remove(index)` `:775`, `RemoveItem` `:790`. It declares no `Contains`.

---

## vector API

```c
vector pos = "1 2 3";
float x = pos[0];
float y = pos[1];
float z = pos[2];

float dist   = vector.Distance(pos1, pos2);
float distSq = vector.DistanceSq(pos1, pos2);   // cheaper, no sqrt
vector dir   = vector.Direction(from, to);       // not normalized
vector norm  = dir.Normalized();
float dot    = vector.Dot(a, b);
vector cross = a.Cross(b);                       // instance method
float len    = pos.Length();
float yaw    = dir.VectorToYaw();
```

`class vector` is `P:\scripts\1_core\proto\enconvert.c:118`: `Normalized` `:156`, `Length` `:169`, `Distance` `:196`, `DistanceSq` `:210`, `Cross` `:239` (an instance method), `Direction` `:254`, `Dot` `:305`, `VectorToYaw` `:345`.

---

## Math API (Math class)

```c
float a = Math.AbsFloat(-3.5);     // 3.5
int   b = Math.AbsInt(-3);         // 3
float c = Math.Clamp(val, 0, 1);   // min/max clamp
float d = Math.Lerp(0, 100, 0.5);  // 50
float e = Math.InverseLerp(0, 100, 50); // 0.5
float f = Math.Round(3.7);         // 4
float g = Math.Ceil(3.2);          // 4
float h = Math.Floor(3.9);         // 3
float r = Math.RandomFloat(0, 1);  // uniform [0, 1)
int   i = Math.RandomInt(1, 6);    // [1, 6) — upper bound EXCLUSIVE
float s = Math.Sin(Math.DEG2RAD * 45);
float t = Math.Sqrt(9);            // 3
float pi = Math.PI;
```

Declared in `P:\scripts\1_core\proto\enmath.c`: `PI` `:12`, `DEG2RAD` `:17`, `RandomInt` `:38` (vanilla: "Range ends [exclusive]", `:28`), `RandomFloat` `:91`, `Pow` `:183`, `AbsFloat` `:225`, `AbsInt` `:237`, `Sqrt` `:305`, `Sin` `:331`, `Round` `:413`, `Floor` `:427`, `Ceil` `:441`, `Clamp` `:540`, `Min` `:553`, `Max` `:566`, `Lerp` `:608`, `InverseLerp` `:622`.

---

## ⚠️ `string.ToLower()` / `ToUpper()` mutate in place

They change the string in place and return its new length (`P:\scripts\1_core\proto\enstring.c:171`, `:186`). Always copy first if you need to preserve the original:

```c
string original = "Hello World";

// WRONG — mutates original
original.ToLower();

// CORRECT — copy by concatenation, then mutate the copy
string lower = original + "";
lower.ToLower();
```

Reported, not checked on `P:\`: plain assignment (`string lower = original;`) can share the underlying string, so `ToLower` on the copy changes both names. Copying with `+ ""` avoids the question.

---

## Existence — these vanilla helpers DO exist

Counters outdated wiki/forum claims:

| API | Verified location |
|---|---|
| `Math.Clamp(val, min, max)` | `P:\scripts\1_core\proto\enmath.c:540` |
| `Math.Min`, `Math.Max`, `Math.Sqrt`, `Math.Pow` | `:553`, `:566`, `:305`, `:183` |
| `string.IndexOfFrom(startPos, search)` | `P:\scripts\1_core\proto\enstring.c:271` |
| `string.LastIndexOf`, `string.Hash`, `string.Replace` | `:253`, `:223`, `:156` |

If older modding guides say *"you need to write a custom Clamp"* — they're stale.

---

## Reported: `int.MIN` comparison quirk

`int.MIN` is `-2147483648` (`P:\scripts\1_core\proto\enconvert.c:28`). The comparison result below is reported by modders and not checked on `P:\`:

```c
// int.MIN = -2147483648
1 < int.MIN;      // Returns TRUE in EnScript!
1 < -2147483647;  // Also returns TRUE!
```

The boundary value comparison is unreliable. Always validate inputs before relying on integer-limit checks.
