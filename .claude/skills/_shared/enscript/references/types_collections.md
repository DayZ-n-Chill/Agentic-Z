# Reference: Core Types and Collections

Quick examples. The checked reference with vanilla line citations is `language_types.md`.

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

---

## set\<T\>

```c
ref set<string> seen = new set<string>();

seen.Insert("item_a");
bool has = seen.Find("item_a") != -1;   // set has no Contains
seen.RemoveItem("item_a");              // Remove(i) takes an index
int cnt = seen.Count();
```

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

The `+ ""` forces an allocation; assignment alone (`string lower = original;`) shares the underlying string in some engine versions and ToLower will mutate both names.

---

## Existence — these vanilla helpers DO exist

Counters outdated wiki/forum claims:

| API | Verified location |
|---|---|
| `Math.Clamp(val, min, max)` | `P:\scripts\1_core\proto\enmath.c` |
| `Math.Min`, `Math.Max`, `Math.Sqrt`, `Math.Pow` | same |
| `string.IndexOfFrom(startPos, search)` | `P:\scripts\1_core\proto\enstring.c` |
| `string.LastIndexOf`, `string.Hash`, `string.Replace` | same |

If older modding guides say *"you need to write a custom Clamp"* — they're stale.

---

## ⚠️ `int.MIN` comparison quirk

```c
// int.MIN = -2147483648
1 < int.MIN;      // Returns TRUE in EnScript!
1 < -2147483647;  // Also returns TRUE!
```

The boundary value comparison is unreliable. Always validate inputs before relying on integer-limit checks.
