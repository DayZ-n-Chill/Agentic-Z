# Enforce Script style: Control flow and preprocessor

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Preprocessor defines (`SERVER`, `NO_GUI`, `DIAG_DEVELOPER`) are checked in `../enscript/references/language_compile.md`; `foreach` with an index is in `language_types.md`.

## Control Flow

### Conditionals

```
if (condition)
{
    // Single condition
}

if (condition1 && condition2)
{
    // Multiple conditions
}
else if (condition3)
{
    // Else-if branch
}
else
{
    // Else branch
}
```

**Bitwise Operators in Conditions:**

EnScript follows C/C++ operator precedence where comparison comes before bitwise operations. Always use parentheses:

```
int a = 1;
int b = 2;

// WRONG: Parsed as: a & (b == b)
if (a & b == b)

// CORRECT: Explicit parentheses
if ((a & b) == b)
```

### Loops

**For Loop:**

```
for (int i = 0; i < count; i++)
{
    // Loop body
}

foreach (string item : collection)
{
    // For-each loop
}
```

### Foreach Loops

```
foreach (string stateName : stateNames)
{
    stateName.TrimInPlace();
    int value = typename.StringToEnum(EMyMod_State, stateName);
    // Process value
}
```

**Foreach with Getters:**

`foreach` should not be used directly on iterables returned by getter methods. You should assign to a variable first:

```
class MyClass
{
    autoptr TStringArray m_Test = {"A", "B"};

    TStringArray GetTest()
    {
        return m_Test;
    }

    void TestBad()
    {
        // getter is called every foreach
        foreach (string t : GetTest())
        {
            Print(t);
        }
    }

    void TestGood()
    {
        // CORRECT: Assign to variable first
        TStringArray test = GetTest();
        foreach (string t : test)
        {
            Print(t);
        }
    }

    void TestAlsoGood()
    {
        // CORRECT: Direct member access works fine
        foreach (string t : m_Test)
        {
            Print(t);
        }
    }
}
```

**While Loop:**

```
while (condition)
{
    // Loop body
}
```

### Switch Statements

**Switch Default Case Issue:**

EnScript requires explicit return after switch even with default case:

```
// PROBLEMATIC: Compiler complains about missing return
string Test(string what)
{
    switch (what)
    {
        case "A":
        case "B":
            return "X";
        default:
            return "Y";
    }
    // Compiler error: function must return a value
}

// WORKAROUND: Move last return outside switch
string Test(string what)
{
    switch (what)
    {
        case "A":
        case "B":
            return "X";
    }
    return "Y";  // Default case moved outside
}
```

### Array Bounds Checking

Always check array bounds before accessing elements:

```
array<int> list = {0, 1, 2};

// CORRECT: Index-based bounds check
if (index >= 0 && index < list.Count())
{
    int value = list[index];
}

// NOTE: This is valid but has different semantics
// Returns true if entry is null OR out of bounds
if (!list[1])  // Evaluates to true for both null and out-of-bounds
```

**Best Practice:** Use explicit index bounds checking: `if (index >= 0 && index < array.Count())`

---

## Preprocessor Directives

### Conditional Compilation

```
#ifdef MYMOD_GROUPS
    // Group-specific code
#endif

#ifdef SERVER
    // Server-only code
#endif

#ifndef DIAG_DEVELOPER
    // Non-developer build code
#endif
```

**Empty Preprocessor Blocks:**

Empty `#ifdef`/`#ifndef` blocks cause segfaults, even if they only contain comments:

```
// WRONG: Causes segfault
#ifdef FOO
    // This will crash
#endif

// CORRECT: Either remove or add actual code
#ifdef FOO
    int dummy;  // At least one statement
#endif

// BETTER: Remove if not needed
// #ifdef FOO
// #endif
```

### Defines

**Common Directives:**

- `#define`: Define preprocessor macros (not constants)
- `#ifdef` / `#ifndef`: Conditional compilation
- `#endif`: End conditional block

**Naming:**

- Use UPPERCASE for defines
- Module-specific prefixes recommended

```
#define MYMOD_DEBUG
#define MYMOD_FEATURE_X
```

**Note:** `#define` creates preprocessor macros, not constants. For actual constants, use `const` or enums.
