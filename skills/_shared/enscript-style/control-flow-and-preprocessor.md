# Enforce Script style: Control flow and preprocessor

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Preprocessor defines (`SERVER`, `NO_GUI`, `DIAG_DEVELOPER`) are checked in `../enscript/references/language_compile.md`; `foreach` with an index is in `../enscript/references/language_types.md`.

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

Unverified: the style guide reports that Enforce Script follows C/C++ operator precedence, where `==` binds tighter than `&`, so `a & b == b` would parse as `a & (b == b)`. This guide has not checked that against the compiler or a vanilla file. Parentheses make the intent explicit whatever the precedence is, so always use them:

```
int a = 1;
int b = 2;

// AMBIGUOUS: reported (unverified) to parse as a & (b == b)
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

Unverified: the style guide reports that `foreach` over a getter call calls the getter again on every iteration. This guide has not checked that against the compiler or a vanilla file. Assigning the result to a local first is correct either way, so prefer it:

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
        // AVOID: reported (unverified) to call the getter every iteration
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

Unverified: the style guide reports that the compiler can still ask for a return after a `switch` whose `default` case returns. This guide has not checked that against the compiler or a vanilla file, so treat it as reported compiler behaviour, not a confirmed rule. Writing the last return after the `switch` is safe either way:

```
// REPORTED (unverified): compiler may complain about a missing return
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
    // Reported (unverified) error: function must return a value
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

// NOT A BOUNDS CHECK: tests the value, not the index
if (!list[index])
```

`!list[index]` reads the element and tests its value, so it says nothing about whether `index` is in range. Unverified: the style guide reports that it is true for an out-of-range index. This guide has not checked what an out-of-range read does, so never use it as a bounds check.

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

Vanilla compiles `#ifdef` blocks that hold only a comment. `P:\scripts\4_world\classes\environment\environment.c:1-3` ships one, and the diag build defines `DIAG_DEVELOPER`, so it compiles this block:

```
#ifdef DIAG_DEVELOPER
//#define CHECK_SHADOW_VIZ
#endif
```

A comment-only block is therefore not a crash risk. Still delete blocks you no longer need, so the code stays readable.

### Defines

**Common Directives:**

Vanilla script uses `#ifdef`, `#ifndef`, `#else` and `#endif` (`_shared/enscript/references/language_compile.md:47`).

- `#define NAME`: Declares a flag name that `#ifdef` and `#ifndef` test. Every `#define` in `P:\scripts` is a bare name with no value (for example `P:\scripts\1_core\defines.c:14`), and file local debug switches are left as commented `//#define NAME` lines (`P:\scripts\4_world\classes\codelockcomponent.c:1`).
- `#ifdef` / `#ifndef`: Compile the block only when the name is, or is not, defined
- `#else`: Start the alternative block
- `#endif`: End the conditional block

Unverified: whether `#define NAME value` substitutes a value the way a C macro does. No vanilla file does it, so do not rely on it.

**Naming:**

- Use UPPERCASE for defines
- Module-specific prefixes recommended

```
#define MYMOD_DEBUG
#define MYMOD_FEATURE_X
```

**Note:** `#define` only declares a flag name for `#ifdef` and `#ifndef`; it is not a constant. For actual constants, use `const` or enums.
