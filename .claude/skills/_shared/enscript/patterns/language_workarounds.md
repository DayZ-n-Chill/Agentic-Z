# Pattern: Language Workarounds

Enforce Script is a C-like language with several intentional and incidental gaps compared to C++ or modern scripting languages. These are the most commonly encountered missing features and their workarounds.

---

## No Ternary Operator

```c
// ✗ Does NOT compile
string label = count > 0 ? "items" : "empty";

// ✓ Use if/else
string label;
if (count > 0)
    label = "items";
else
    label = "empty";

// ✓ Or a helper function:
string StringIf(bool cond, string a, string b)
{
    if (cond) return a;
    return b;
}
string label = StringIf(count > 0, "items", "empty");
```

---

## No `auto` Type Inference

`auto` is a **storage qualifier** (autoptr = reference-counted pointer), NOT type inference.

```c
// ✗ WRONG — 'auto x = 5' means autoptr int (confusing, avoid)
auto x = 5;

// ✓ Always declare explicit types
int x = 5;
float f = 3.14;
string s = "hello";

// ✓ 'auto Type' IS valid — it means autoptr (ref-counted ownership)
auto array<int> arr = new array<int>(); // equivalent to: ref array<int> arr = ...
```

---

## No String Interpolation

```c
// ✗ Template strings do not exist
string msg = $"Player {name} has {hp} HP";

// ✓ string.Format with %N placeholders (1-indexed)
string msg = string.Format("Player %1 has %2 HP", name, hp);

// ✓ Concatenation (verbose but works)
string msg2 = "Player " + name + " has " + hp.ToString() + " HP";
```

---

## No Lambdas / Closures

```c
// ✗ Anonymous functions / closures do not exist

// ✓ ScriptCaller for a single function pointer
ScriptCaller caller = ScriptCaller.Create(MyTopLevelFunction);
caller.Invoke(sender, eventArgs);

// ✓ ScriptInvoker for a multicast delegate (many listeners)
ref ScriptInvoker m_OnDeath = new ScriptInvoker();
m_OnDeath.Insert(this.HandleDeath);     // subscribe
m_OnDeath.Invoke(player, cause);        // fire all listeners
m_OnDeath.Remove(this.HandleDeath);     // unsubscribe
```

---

## No `null` for Primitives

```c
// int, float, bool, string are value types — they are NEVER null
// Default values: int=0, float=0.0, bool=false, string=""

// ✗ This check is meaningless at best, compile error at worst
if (myInt == null) { }

// ✓ Check objects only
if (!myObject) { }          // preferred
if (myObject == null) { }   // also valid for class instances
```

---

## No Function Overloading by Signature

```c
// ✗ Cannot have two methods with same name different params
void DoThing(int x) { }
void DoThing(string s) { }  // compile error: duplicate name

// ✓ Use distinct names
void DoThingInt(int x) { }
void DoThingStr(string s) { }

// ✓ Or use optional-flag parameter and early return
void DoThing(int x, bool useStr = false, string s = "")
{
    if (useStr)
    {
        // handle string path
        return;
    }
    // handle int path
}
```

---

## No Exception Handling

```c
// ✗ try/catch does not exist

// ✓ Return bool / null for error signaling
bool TryParse(string input, out int result)
{
    result = input.ToInt();
    return input.Length() > 0 && result != 0;
}

int val;
if (!TryParse(rawInput, val))
    Print("[MyMod] Parse failed for: " + rawInput);
```

---

## No `foreach` with Index

```c
// ✗ Cannot get index inside foreach
foreach (int val : arr) { /* no index available */ }

// ✓ Use a manual counter
int i = 0;
foreach (int val : arr)
{
    Print(string.Format("[%1] = %2", i, val));
    i++;
}

// ✓ Or indexed for-loop
for (int i = 0; i < arr.Count(); i++)
{
    int val = arr[i];
}
```

---

## No Default Parameter Values (pre-1.17 builds)

On older engine builds, default parameter values may not work. Be conservative:

```c
// May fail on older builds — safer to avoid for public API
void MyFunc(int x, bool optional = false) { }

// ✓ Overload-via-wrapper pattern instead
void MyFunc(int x)         { MyFuncInternal(x, false); }
void MyFunc(int x, bool b) { MyFuncInternal(x, b); }
void MyFuncInternal(int x, bool b) { /* impl */ }
```
