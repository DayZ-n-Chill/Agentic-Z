# Reference: Core Types and Collections

## Primitive Types

| Type | Default | Notes |
|---|---|---|
| `int` | `0` | 32-bit signed integer |
| `float` | `0.0` | 32-bit float; use `f` suffix on literals: `1.5f` |
| `bool` | `false` | `true` / `false` |
| `string` | `""` | Immutable value type; use `+` to concat |
| `vector` | `"0 0 0"` | 3-component float; literal syntax: `"1.5 0 -3"` |

Primitives are **never null**. Checking `if (myInt == null)` is either a no-op or a compile error.

---

## string API

```c
string s = "Hello, World!";

int    len     = s.Length();              // 13
string upper   = s.ToUppercase();
string lower   = s.ToLowercase();
bool   starts  = s.StartsWith("Hello");
bool   ends    = s.EndsWith("!");
int    idx     = s.IndexOf(",");          // 5; -1 if not found
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
arr.Remove(0);              // remove by index
arr.RemoveItem("z");        // remove by value (linear scan)
arr.Clear();
arr.Copy(otherArr);         // shallow copy into otherArr
arr.Sort(true);             // true = ascending

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
bool has = seen.Contains("item_a");
seen.Remove("item_a");
int cnt = seen.Count();
```

---

## vector API

```c
vector pos = "1 2 3";
float x = pos[0];    // or pos.GetX()
float y = pos[1];    // or pos.GetY()
float z = pos[2];    // or pos.GetZ()

float dist   = vector.Distance(pos1, pos2);
float distSq = vector.DistanceSq(pos1, pos2);   // cheaper, no sqrt
vector dir   = vector.Direction(from, to);       // not normalized
vector norm  = dir.Normalized();
float dot    = vector.Dot(a, b);
vector cross = vector.Cross(a, b);
float len    = pos.Length();

// Angle between two vectors (degrees)
float ang = vector.AngleBetween(dir1, dir2);
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
