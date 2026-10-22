# Pattern: Language Workarounds

Enforce Script is a C-like language with several intentional and incidental gaps compared to C++ or modern scripting languages. These are the most commonly encountered missing features and their workarounds. For what the language does have (types, `auto`, parameters, containers, `foreach`, strings), see [`../references/language_types.md`](../references/language_types.md); this file only covers the gaps.

A "not supported" claim below means no vanilla script under `P:\scripts\` uses the feature, and the replacement is what vanilla uses instead, with its file.

## Contents

- [No Ternary Operator](#no-ternary-operator)
- [`auto` infers a local's type](#auto-infers-a-locals-type)
- [No String Interpolation](#no-string-interpolation)
- [No Lambdas / Closures](#no-lambdas--closures)
- [No `null` for Primitives](#no-null-for-primitives)
- [Overloading works, but keep it simple](#overloading-works-but-keep-it-simple)
- [No Exception Handling](#no-exception-handling)
- [`foreach` with an index](#foreach-with-an-index)

---

## No Ternary Operator

No vanilla script uses `cond ? a : b`; vanilla writes an `if`/`else`.

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

## `auto` infers a local's type

`auto` declares a local whose type comes from the value. Vanilla uses it, for example `auto vehicle = CarScript.Cast(vehCommand.GetTransport());` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:32`). The owning qualifier is `autoptr`, a different keyword (`references/language_memory.md`).

```c
// Legal, as in vanilla
auto tmp = t.m_srcState.GetParentState();   // 3_game/systems/hfsmbase.c:177

// Preferred in mod code: explicit types are easier to read
int x = 5;
float f = 3.14;
string s = "hello";
```

---

## No String Interpolation

There are no template strings. Vanilla builds text with `string.Format`, whose placeholders start at `%1` and take up to nine values (`static proto string Format(string fmt, void param1 = NULL, ...)`, `P:\scripts\1_core\proto\enstring.c:526`).

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

There are no anonymous functions. Pass a named method instead: `ScriptCaller` holds one (`static proto ScriptCaller Create(func fn)`, `P:\scripts\2_gamelib\tools.c:165`, used at :195) and `ScriptInvoker` holds many (`Insert`, `Remove` and `Invoke`, `tools.c:115-123`).

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

`int`, `float`, `bool`, `string` and `vector` are value types (`references/language_types.md`, "Built in types"), so they are never `null`.

```c
// int, float, bool, string are value types: they are NEVER null
// Default values: int=0, float=0.0, bool=false, string=""

// ✗ This check is meaningless at best, compile error at worst
if (myInt == null) { }

// ✓ Check objects only
if (!myObject) { }          // preferred
if (myObject == null) { }   // also valid for class instances
```

---

## Overloading works, but keep it simple

Methods can share a name when their parameters differ. Vanilla does it: `Hud.ShowWalkieTalkie(bool show)` and `ShowWalkieTalkie(int fadeOutSeconds)` (`P:\scripts\3_game\gameplay.c:652-653`), and `Effect.SetParent(Object parent_obj, int pivot)` and `SetParent(Object parent_obj)` (`P:\scripts\3_game\effect.c:399` and `:411`). Default parameter values work too (`references/language_types.md`, "Parameters").

Overloads whose arguments convert into each other (such as `int` and `bool`, or `int` and `float`) make the call site hard to read. Prefer distinct names in mod code:

```c
// ✓ Clear at the call site
void DoThingInt(int x) { }
void DoThingStr(string s) { }

// ✓ Or one method with a default parameter
void DoThing(int x, bool verbose = false) { }
```

---

## No Exception Handling

There is no `try`/`catch`; no vanilla script uses either. Vanilla signals failure with a `bool` return and an `out` value, as `JsonFileLoader<T>.LoadFile(string filename, out T data, out string errorMessage)` does (`P:\scripts\3_game\tools\jsonfileloader.c:7`).

```c
// ✓ Return bool / null for error signaling
bool TryParse(string input, out int result)
{
    result = input.ToInt();   // enstring.c:20
    return input.Length() > 0 && result != 0;
}

int val;
if (!TryParse(rawInput, val))
    Print("[MyMod] Parse failed for: " + rawInput);
```

---

## `foreach` with an index

`foreach` gives the index (or a map's key) as an optional first variable: `foreach (int i, string s : tokens)` (`P:\scripts\1_core\proto\enstring.c:427`) and `foreach (int id, Effect eff : m_EffectsMap)` (`P:\scripts\3_game\effectmanager.c:556`). No manual counter is needed.

```c
// ✓ Index and value
foreach (int i, int val : arr)
{
    Print(string.Format("[%1] = %2", i, val));
}

// ✓ Or an indexed for-loop
for (int j = 0; j < arr.Count(); j++)
{
    int v = arr[j];
}
```
