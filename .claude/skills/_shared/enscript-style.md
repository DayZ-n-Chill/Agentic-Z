# EnScript (Enforce Script) Style Guide

> **Source:** [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide). Mirrored here so DayZ agents/skills follow it offline.
>
> **Authority:** This is best-practice for EnScript across DayZ modding. When code in `workspace/` conflicts with this guide, this guide wins unless the user says otherwise.

## Introduction

EnScript (Enforce Script) is the object-oriented scripting language used by the Enfusion engine in DayZ Standalone. This style guide is based on conventions observed in the official Bohemia Interactive DayZ Script Diff and the DayZ Expansion mod codebase.

---

## File Organization

### File Extensions

- Use `.c` extension for all EnScript files
- File names should match the primary class name when possible

### Directory Structure

Scripts are typically organized by layer inside a root folder called `Scripts/`:

- `1_Core/` - Core systems
- `2_GameLib/` - Game library
- `3_Game/` - Game-specific code
- `4_World/` - World entities
- `5_Mission/` - Mission logic

---

## Naming Conventions

### Classes

**PascalCase** for all class names:

```
class ExpansionGarageSettings
class PlayerBase
class ItemBase
class ExpansionAIPatrolBase
```

**Prefixes:**

- Module/mod-specific prefixes are common (e.g., `Expansion`, `SCR_`)
- Base classes often end with `Base`
- Abstract classes may start with `Abstract`

**Modded Classes:**

- **ALWAYS prefix member variables** in modded classes or classes inheriting from vanilla/other mods:

```
// CORRECT - Prefixed members in modded class
modded class ItemBase
{
    bool m_Expansion_CustomFlag;
    int m_Expansion_CustomValue;
}

// CORRECT - Prefixed members in inherited class
class ExpansionSomeItem : ItemBase
{
    bool m_Expansion_SpecialProperty;
}
```

This prevents name conflicts with vanilla code or other mods.

### Variables

**Member Variables:**

- Use `m_` prefix for private/protected member variables
- Use PascalCase after the prefix

```
bool m_IsLoaded;
ExpansionMarkerModule m_MarkerModule;
ref MapMenu m_Expansion_MapMenu;
```

**Static Variables:**

- Use `s_` prefix for static member variables
- Use PascalCase after the prefix

```
static ref array<EffectArea> s_Expansion_DangerousAreas;
```

**Local Variables:**

- Use camelCase for local variables
- No prefix required

```
int bitmask;
string lootingBehavior;
vector hitPosition;
```

### Methods/Functions

**PascalCase** for method names:

```
void SetDefaultLootingBehaviour()
int GetLootingBehaviour()
void OnSend(ParamsWriteContext ctx)
bool OnRecieve(ParamsReadContext ctx)
```

**Override Methods:**

- Always use the `override` keyword when overriding parent methods

```
override void OnSend(ParamsWriteContext ctx)
override bool OnRecieve(ParamsReadContext ctx)
```

**Proto Methods vs Custom Methods:**

When available, prefer using proto (native engine) methods over custom script implementations **when the native method performs expensive logic**. Proto methods are faster for complex operations as they run in native code.

```
// PREFERRED - Proto method for expensive operations
proto native vector GetPosition();

// AVOID - Custom reimplementation of expensive native logic
vector GetPosition()
{
    // Custom expensive calculation
}
```

If someone is writing a mod that will likely be modded/overridden, suggest using the Obsolete attribute on a method/field/variable instead of removing them altogether. The workbench will show a warning when used.

```
[Obsolete()]
vector GetCustomPosition()
{
    // Custom expensive calculation
}
```

**Specific use note 1:** If at all possible, avoid using `GetObjectsAtPosition` and `GetObjectsAtPosition3D` as much as possible. Static arrays on the class you're looking for, triggers, or the `GetScene` methods are all much better options available.

**Specific use note 2:** If at all possible, avoid `g_Game.SurfaceIsPond()`, `SurfaceIsSea()` or `SurfaceRoadY` as much as possible. They're remarkably slow for their intended purpose.

Recommend using `if (g_Game.GetWaterDepth(vectorpos) <= 0)` for checking if vector is in water, and something similar to the following for surface y calculating.

```
vector GetSurfacePosition(float x, float z)
{
    return Vector(x, g_Game.SurfaceY(x, z), z);
}
```

**Important Note:** There is overhead from calling native methods from script. For simple operations, custom script methods may actually be faster. This is why `proto native CGame GetGame()` was replaced with `DayZGame GetGame() { return g_Game; }` - the script version is faster for simple global access.

**Rule:** Use proto methods when they perform complex/expensive operations. For simple operations (like returning a global), script implementations are often faster.

### Parameters

Use camelCase for parameters:

```
void Log(string msg)
void SetValue(int value, bool isEnabled)
static vector GetPlacementPosition(vector pos)
```

### Constants and Defines

**Constants:**

Use `const` for class-specific constants, or enums for grouped constants:

```
class VehicleManager
{
    const int MAX_VEHICLES = 10;
    const float SEARCH_RADIUS = 100.0;
}
```

**Enums:**

Use enums to group related constants - **avoid creating many similarly named global constants**:

```
// PREFERRED - Grouped with enum
enum EVehicleType
{
    Car,
    Truck,
    Helicopter
}

// ALSO ACCEPTABLE - PASCAL_CASE enums
enum EVehicleType
{
    CAR,
    TRUCK,
    HELICOPTER
}

// AVOID - Multiple global constants
const int VEHICLE_TYPE_CAR = 0;
const int VEHICLE_TYPE_TRUCK = 1;
const int VEHICLE_TYPE_HELICOPTER = 2;
```

**Enum Naming:**

- **CamelCase** is generally nicer to read: `enum EStatus { Idle, Running, Stopped }`
- **PASCAL_CASE** can be used for clarity in some cases: `enum EStatus { IDLE, RUNNING, STOPPED }`
- Choose one style and be consistent within your codebase

**Preprocessor Defines:**

Use UPPERCASE for preprocessor defines:

```
#define EXPANSION_MARKER_VIS_WORLD
#define EXPANSIONMODVEHICLE
```

**Config Class Name Defines (DayZ 1.26+):**

As of DayZ 1.26, config `CfgMods` class names are automatically defined in script. To add custom defines, use the `defines[]` array in your `config.cpp`:

```
class CfgMods
{
    class YourMod
    {
        defines[] =
        {
            "YOURMOD",
            "YOURMOD_FEATURE_X"
        };
    };
}
```

These defines can then be used in script:

```
#ifdef YOURMOD
    // Mod-specific code
#endif
```

**Rule:** Declare new global constants (and globals in general) sparingly to avoid polluting the global namespace. Use class-specific constants, enums, and config-based defines instead.

---

## Code Structure

### Class Declaration

```
class ClassName : ParentClass
{
    // Member variables (private/protected first)
    private bool m_PrivateVar;
    protected int m_ProtectedVar;

    // Public member variables
    bool PublicEnabled;
    int MaxStorableVehicles;
    float VehicleSearchRadius;

    // Non-serialized members
    [NonSerialized()]
    bool m_IsLoaded;

    // Constructor
    void ClassName()
    {
        // Initialization
    }

    // Deconstructor
    void~ClassName()
    {
        // Object deletion
    }

    // Methods
    void MethodName()
    {
        // Implementation
    }

    override void ParentMethod()
    {
        super.ParentMethod();
        // Additional implementation
    }
}
```

### Indentation and Spacing

**Tabs vs Spaces:**

- Use **tabs** for indentation (observed standard in both repositories)

**Braces:**

- Opening brace on the same line as declaration
- Closing brace on new line, aligned with declaration

```
void Method()
{
    if (condition)
    {
        // code
    }
    else
    {
        // code
    }
}
```

**Spacing:**

- Space after keywords: `if (`, `for (`, `while (`
- Space around operators: `x = y + z`
- No space before semicolons
- Space after commas: `Method(param1, param2)`

```
if (isEnabled && hasPermission)
{
    for (int i = 0; i < count; i++)
    {
        array.Insert(value);
    }
}
```

---

## Type System

### Primitive Types

```
bool isEnabled;
int count;
float radius;
string name;
vector position;
```

### Understanding Types and Instances

**IMPORTANT:** EnScript has specific terminology that differs from typical OOP:

```
// `c` is NOT a class - it's an instance
SomeClass c = new SomeClass();

// `typename` represents the actual class
typename t = c.Type();  // Returns the class type

// Type checking methods
c.Type()              // Returns typename (the class)
c.Type().ToString()   // Returns class name as string
c.ClassName()         // Same as Type().ToString() - prefer this
c.GetType()           // Returns config.cpp class name for entities if defined (PREFERRED)
                      // NOTE: Will differ from script class name if no script declaration exists
```

**Best Practice:** Use `GetType()` over `ClassName()` for entities, as it returns the actual config class name which may differ from the script class name.

### Collections

**Shorthand Array Initialization (PREFERRED):**

```
// PREFERRED - Shorthand initialization
array<string> stringArray = {};
array<int> numbers = {1, 2, 3};

// ACCEPTABLE - Explicit initialization
array<string> stringArray = new array<string>;
```

**Type Definitions:**

```
TStringArray entityWhitelist;  // typedef array<string>
autoptr TVectorArray waypoints; // autoptr for managed arrays
```

### References

Use `ref` or `autoptr` for managed references on member variables:

```
ref MapMenu m_Expansion_MapMenu;
autoptr TVectorArray Waypoints;
```

**Understanding `ref` vs `autoptr`:**

- **`ref`**: Instance is deleted when the **last reference** to it is removed (reference counting)
- **`autoptr`**: Instance is deleted when the **parent instance** is deleted (ownership semantics)

```
class Example
{
    ref MyClass m_RefInstance;      // Deleted when all references gone
    autoptr MyClass m_AutoInstance; // Deleted when Example is deleted
}
```

### Type Casting

Use `ClassName.Cast()` for safe casting:

```
PlayerBase player = PlayerBase.Cast(g_Game.GetPlayer());
ItemBase itemBs = ItemBase.Cast(primary);
```

**Alternative: `Class.CastTo()`**

```
// Using Class.CastTo (inline check)
PlayerBase player;
if (Class.CastTo(player, g_Game.GetPlayer()))
{
    // player is valid, use it
}

// Using ClassName.Cast (separate check)
PlayerBase player = PlayerBase.Cast(g_Game.GetPlayer());
if (player)
{
    // player is valid, use it
}
```

Both methods are valid - `CastTo` combines the cast and check in one line, while `Cast` is more explicit.

---

## Memory Management

### Object Creation

Use `new` keyword (with or without trailing parentheses for constructors without arguments):

```
EntityWhitelist = new TStringArray;             // Valid
m_MarkerModule = new ExpansionMarkerModule();   // Valid
```

Both forms are acceptable - choose one style and be consistent.

### Managed Classes

Inherit from `Managed` for automatic reference counting:

```
class MyClass : Managed
{
    // No manual deletion needed
}
```

**Note:** Anything in `3_Game` and up is **automatically managed** - no need to explicitly inherit from `Managed`.

### Garbage Collection

**Understanding EnScript Garbage Collection:**

- Everything (except `Managed`) is a **weak reference by default**
- The garbage collector is **very aggressive** - instances in function scope are destroyed immediately when scope ends
- All instances (Managed or not) are garbage collected when reference count reaches zero

### Deletion

**STRONGLY DISCOURAGED:** Avoid using the `delete` keyword in almost all cases.

```
// AVOID - Using delete keyword
delete myObject;

// PREFERRED - Null the reference instead
myObject = null;
```

**Why avoid `delete`?**

- Can cause segfaults if object is still referenced elsewhere
- **NEVER use for entities** - will cause crashes
- Should only be used in very specific, rare cases
- Nulling references is safer and lets garbage collection handle cleanup

**Rule:** Let the garbage collector handle object cleanup by nulling references.

### Reference Management (CRITICAL)

**WARNING: Improper use of `ref` keyword causes crashes and unexpected behavior!**

The `ref` keyword creates strong references and must be used carefully to avoid memory management issues, reference counting problems, and crashes that affect your mod and others.

#### CORRECT Usage of `ref`

**Member Variables:**

```
class MyClass
{
    ref MyOtherClass m_Member;        // Safe - member variable
    autoptr array<string> m_Items;    // Safe - member variable with autoptr

    void MyClass()
    {
        m_Member = new MyOtherClass();
    }
}
```

**Note:** Do NOT use `ref` in typedefs:

```
// WRONG
typedef ref MyClass MyClassRef;

// CORRECT
typedef MyClass MyClassRef;
```

#### INCORRECT Usage of `ref`

**DO NOT use `ref` in:**

1. **Method Parameters:**

```
// WRONG - Causes memory issues
ref MyClass MyMethod(ref MyClass1 a, ref MyClass2 b)
{
    // ...
}

// CORRECT - No ref on parameters
MyClass MyMethod(MyClass1 a, MyClass2 b)
{
    // ...
}
```

2. **Return Types:**

```
// WRONG - Causes reference counting issues
ref MyClass GetObject()
{
    ref MyClass obj = new MyClass();
    return obj;
}

// CORRECT - Return without ref
MyClass GetObject()
{
    MyClass obj = new MyClass();
    return obj;
}
```

3. **Local Variables:**

```
void MyMethod()
{
    // WRONG - Unnecessary ref on local variable
    ref MyClass3 myClass3 = new ref MyClass3();

    // CORRECT - No ref on local variables
    MyClass3 myClass3 = new MyClass3();
}
```

4. **`new` Keyword:**

```
// WRONG - Never use ref with new
ref MyClass obj = new ref MyClass();

// CORRECT
MyClass obj = new MyClass();

// ALSO CORRECT - For member variables
m_Member = new MyClass();
```

#### Reference Counting Best Practices

**1. Minimize Strong References:**

Hold only ONE explicit strong reference (using `ref` keyword) when possible:

```
class VehicleManager
{
    // GOOD - Single strong reference on member
    ref array<EntityAI> m_Vehicles;

    void AddVehicle(EntityAI vehicle)
    {
        // CORRECT - No ref on parameter or local var
        if (!m_Vehicles)
            m_Vehicles = new array<EntityAI>;

        m_Vehicles.Insert(vehicle);
    }
}
```

**2. Avoid Creating Multiple Strong References:**

```
// BAD - Multiple strong refs to same object
class BadExample
{
    ref MyClass m_Object1;
    ref MyClass m_Object2;

    void BadExample()
    {
        MyClass obj = new MyClass();
        m_Object1 = obj;
        m_Object2 = obj;  // Two strong refs to same object!
    }
}

// GOOD - Single strong reference
class GoodExample
{
    ref MyClass m_Object;
    MyClass m_WeakRef;  // Weak reference (no ref keyword)

    void GoodExample()
    {
        m_Object = new MyClass();
        m_WeakRef = m_Object;  // One strong, one weak
    }
}
```

**3. Let EnScript Handle References:**

EnScript's reference counting works best when you don't over-specify references:

```
// PREFERRED - Let the engine manage it
array<EntityAI> GetVehicles()
{
    array<EntityAI> result = {};
    // populate result
    return result;
}

// AVOID - Over-specified refs
ref array<EntityAI> GetVehicles()
{
    ref array<EntityAI> result = new ref array<EntityAI>;
    return result;
}
```

#### Common Issues Caused by Incorrect `ref` Usage

- **Crashes** - Reference counting errors lead to premature deletion or memory leaks
- **Null pointer exceptions** - Objects deleted unexpectedly
- **Cross-mod interference** - Your ref issues affect other mods
- **Unpredictable behavior** - Objects existing longer than intended
- **Memory leaks** - Objects never getting cleaned up

#### Quick Reference Rules

1. **USE `ref` (or `autoptr`) for:** Member variables ONLY
2. **NEVER use `ref` for:** Method parameters, return types, local variables, typedefs
3. **NEVER use:** `new ref ClassName()`
4. **ALWAYS use:** `new ClassName()`
5. **Goal:** One strong reference per object when possible
6. **NEVER use `delete`** - let garbage collection handle cleanup
7. **Don't mix:** Use either `ref` OR `autoptr`, not both in the same codebase

**When in doubt, omit the `ref` keyword and let EnScript's automatic reference counting handle it.**

---

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

// WRONG - Parsed as: a & (b == b)
if (a & b == b)

// CORRECT - Explicit parentheses
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
foreach (string lootingBehavior : lootingBehaviors)
{
    lootingBehavior.TrimInPlace();
    int value = typename.StringToEnum(eAILootingBehavior, lootingBehavior);
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
        // CORRECT - Assign to variable first
        TStringArray test = GetTest();
        foreach (string t : test)
        {
            Print(t);
        }
    }

    void TestAlsoGood()
    {
        // CORRECT - Direct member access works fine
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
// PROBLEMATIC - Compiler complains about missing return
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

// WORKAROUND - Move last return outside switch
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

// CORRECT - Index-based bounds check
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
#ifdef EXPANSIONMODGROUPS
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
// WRONG - Causes segfault
#ifdef FOO
    // This will crash
#endif

// CORRECT - Either remove or add actual code
#ifdef FOO
    int dummy;  // At least one statement
#endif

// BETTER - Remove if not needed
// #ifdef FOO
// #endif
```

### Defines

**Common Directives:**

- `#define` - Define preprocessor macros (not constants)
- `#ifdef` / `#ifndef` - Conditional compilation
- `#endif` - End conditional block

**Naming:**

- Use UPPERCASE for defines
- Module-specific prefixes recommended

```
#define EXPANSION_VEHICLE_TOWING
#define EXPANSIONMODMARKET
```

**Note:** `#define` creates preprocessor macros, not constants. For actual constants, use `const` or enums.

---

## Comments

### Single-line Comments

Use `//` for single-line comments:

```
// This is a single-line comment
int value = 5; // Inline comment
```

### Multi-line Comments

Use `/* */` for multi-line comments:

```
/*
 * This is a multi-line comment
 * explaining complex logic
 */
```

### Documentation Comments

Use `//!` for documentation comments:

```
//! Enable/Disable garage market mod features
bool EnableMarketFeatures;

//! @note can't check inheritance against dangerous area types on client
void CheckTypes()
```

### Doxygen-style Comments

For class and method documentation:

```
/**
 * @class ExpansionGarageSettings
 * @brief Settings for the garage system
 */
class ExpansionGarageSettings
```

### Comment Style

- Be descriptive but concise
- Explain **why**, not just **what**
- Update comments when code changes
- Use comments to mark sections of code

```
//! Map Menu
if (input.LocalPress("UAExpansionMapToggle", false) && !viewMenu)
{
    ToggleMapMenu(player);
}

//! GPS
if (input.LocalPress("UAExpansionGPSToggle", false))
{
    // Implementation
}
```

---

## Modding Patterns

### Modded Classes

Use `modded` keyword to extend vanilla classes:

```
modded class MissionGameplay
{
    // Additional members and methods

    override void Expansion_OnUpdate(float timeslice, PlayerBase player)
    {
        super.Expansion_OnUpdate(timeslice, player);
        // Additional implementation
    }
}
```

**CRITICAL: Never Add Inheritance to Modded Classes**

When using the `modded` keyword, **NEVER** add inheritance (`: ParentClass`). The modded class automatically inherits from the original class definition.

```
// WRONG - Adding inheritance to modded class
modded class PlayerBase : ManBase
{
    // Inheritance declaration is ignored!
}

// CORRECT - No inheritance declaration
modded class PlayerBase
{
    // This properly extends the original PlayerBase
}
```

**Why This Matters:**

- Adding inheritance to a `modded` class is **ignored by the compiler**
- You cannot change the class hierarchy by modding an existing class
- It's misleading to readers and should be omitted
- The modded class already IS the class you're modding - you're just adding to it

**Rule:** `modded class ClassName` never has `: ParentClass` - you cannot change its inheritance.

### Accessing Private Members

Modded classes in the same file can access private members:

```
// Original class
class VanillaClass
{
    private bool imPrivate = 0;
    private void DoSomething()
    {
        Print("Vanilla method");
    }
}

// Access in modded class
modded class VanillaClass
{
    void AccessPvt()
    {
        Print(imPrivate);
        DoSomething();
    }
}
```

### Calling Parent Methods

Use `super` to call parent implementations:

```
override void OnSend(ParamsWriteContext ctx)
{
    super.OnSend(ctx);
    // Additional serialization
}
```

**Note:** It should be remembered in most situations, you should be calling super on methods and doing your custom logic in the order you wish for the logic to apply. (pre or post super call)

```
// original method
void foo() {
  for (int i = 0; i < 9999999; i++) { someExpensiveCall(); }
  m_someSideEffect = true;
}

// modded method, adding logic after all the original method's individual logics with super calls are ran.
override void foo() {
  super.foo();
  for (int i = 0; i < 9999999; i++) { myModLogic(); }
}
```

---

## Global Variables and Singletons

### Avoid Creating New Globals

Do not pollute the global namespace with new global variables or functions when not needed.

```
// BAD - Global function and separate class
class MyClass { }
MyClass GetMyClassInstance() { return new MyClass(); }

// GOOD - Singleton pattern on the class itself
class MyClass
{
    private static ref MyClass s_Instance;

    static MyClass GetInstance()
    {
        if (!s_Instance)
            s_Instance = new MyClass();
        return s_Instance;
    }

    private void MyClass() { }  // Private constructor
}

// ALSO GOOD - Public static instance
class MyClass
{
    static ref MyClass Instance;

    private void MyClass()
    {
        Instance = this;
    }
}
```

### Accessing Globals

Prefer accessing global variables directly instead of using global getter functions:

```
// PREFERRED - Direct global access
g_Game.GetPlayer();

// LESS PREFERRED - Getter function
GetGame().GetPlayer();
```

**Note:** While using getters is common in vanilla code, direct access is often clearer and more efficient. This is why `proto native CGame GetGame()` was replaced with `DayZGame GetGame() { return g_Game; }` - the script version is faster for simple global access due to the overhead of calling native methods.

---

## Property Access

### Direct Property Access vs Getters

Prefer direct access to public properties over getter methods that just return the value:

```
class Example
{
    int PublicValue;

    int GetPublicValue()  // Unnecessary getter
    {
        return PublicValue;
    }
}

// PREFERRED - Direct access
int value = instance.PublicValue;

// LESS PREFERRED - Unnecessary getter
int value = instance.GetPublicValue();
```

**Use getters only when:**

- The property needs to be private/protected
- Additional logic is required (validation, lazy initialization, etc.)
- The value is computed rather than stored

---

## Serialization

### Common Pattern

```
override void OnSend(ParamsWriteContext ctx)
{
    ctx.Write(Enabled);
    ctx.Write(GarageMode);
    ctx.Write(MaxStorableVehicles);

    #ifdef EXPANSIONMODGROUPS
        ctx.Write(EnableGroupFeatures);
    #endif
}

override bool OnRecieve(ParamsReadContext ctx)
{
    ctx.Read(Enabled);
    ctx.Read(GarageMode);
    ctx.Read(MaxStorableVehicles);

    #ifdef EXPANSIONMODGROUPS
        ctx.Read(EnableGroupFeatures);
    #endif

    return true;
}
```

---

## Input Handling

### Standard Pattern

```
if (input.LocalPress("UAExpansionMapToggle", false) && !viewMenu)
{
    ToggleMapMenu(player);
}
```

---

## Module System

### Module Registration

```
CF_Modules<ExpansionMarkerModule>.Get(m_MarkerModule);
```

### Module Callbacks

```
ExpansionSettings.SI_Garage.Invoke();
```

---

## Debugging and Tracing

### Debug Traces (Expansion-Specific)

```
// Using EXTrace (preferred - minimal overhead when disabled)
auto trace = EXTrace.Start(EXTrace.GENERAL, this, "MethodName");

// Alternative (older pattern with overhead)
#ifdef EXPANSIONTRACE
    auto trace = CF_Trace_0(ExpansionTracing.SETTINGS, this, "MethodName");
#endif
```

**Note:** `EXTrace.Start` is the better implementation with much less overhead when tracing is disabled (essentially a no-op). It doesn't need to be `#ifdef`'d unless in performance-critical code sections.

### Logging

```
EXError.Error(this, "Invalid looting behaviour " + lootingBehavior, {});
EXTrace.Print(EXTrace.AI, this, "Debug message");
```

### Error Logs

**Exception logs** are named `crash_<date>_<time>.log`, but they contain exceptions, not actual crashes (segfaults). Actual segfaults create different crash dumps.

### Debug Defines

```
//#define EXPANSION_CARKEY_LOGGING
//#define EXPANSION_VEHICLE_SKIN_LOGGING
```

Comment out defines that should not be in production code.

---

## Error Handling

### Existence/Null Checks

1. Existence/Null checks should be done where you know how to handle such cases; propagate the non-nullness guarantee to other methods with `notnull`

```
void Foo()
{
    EntityAI entity = FindSomeEntitySomehow();
    Print(IsWearingSunglasses(entity));
}

bool IsWearingSunglasses(EntityAI entity)
{
    if (entity == null)
    {
        // WRONG: we don't know how to handle null variables
        return false;
    }
    return true;
}

void Foo()
{
    EntityAI entity = FindSomeEntitySomehow();
    if (entity)
    {
        // CORRECT: we do know what to do with a null value
        Print("entity not found");
        return;
    }
    Print(IsWearingSunglasses(entity));
}
```

2. Use null checks when a null value is semantically valid

```
bool IsWearingSunglasses(notnull EntityAI entity)
{
    GameInventory inventory = entity.GetInventory();
    if (!inventory)
    {
        // CORRECT: `GetInventory` returning null means that the entity
        // has no inventory at all, hence it isn't wearing sunglasses
        return false;
    }
    return true;
}
```

3. Avoid unnecessary checks

```
bool IsPlayerWearingSunglasses(notnull PlayerBase player)
{
    GameInventory inventory = player.GetInventory();
    if (!inventory)
    {
        // AVOID: an instance of a player will always have an inventory
        // If for some reasons the player inventory is null, there probably are some other serious issues
        return false;
    }
    return true;
}
```

**Important:** `if (something)` does not just check for null - it checks whether the value evaluates to true. For objects, this means checking existence.

### Value Validation

```
int value = typename.StringToEnum(eAILootingBehavior, lootingBehavior);
if (value == -1)
{
    EXError.Error(this, "Invalid looting behaviour " + lootingBehavior, {});
}
else
{
    bitmask |= value;
}
```

### Client/Server Checks

**CRITICAL: g_Game Behavior During Load**

The `IsClient()` and `IsServer()` methods behave unexpectedly during game load:

```
// WRONG - Returns false on client during load
if (GetGame().IsClient())

// CORRECT - Reliable client check
if (!g_Game.IsDedicatedServer())

// WRONG - Returns true on client during load
if (GetGame().IsServer())

// CORRECT - Reliable server check (dedicated only)
if (g_Game.IsDedicatedServer())

// CORRECT - Server check including offline/singleplayer
if (g_Game.IsServer() && !g_Game.IsMultiplayer())
```

**Rule:** Use `IsDedicatedServer()` for reliable client/server detection, especially in initialization code.

---

## Best Practices

### 1. Use Meaningful Names

```
// Good
float VehicleSearchRadius;
bool CanStoreWithCargo;

// Avoid
float vsr;
bool cswc;
```

### 2. Keep Methods Focused

Each method should do one thing well:

```
void SetDefaultLootingBehaviour()
{
    if (Behaviour == "ROAMING")
        LootingBehaviour = "ALL";
    else
        LootingBehaviour = "DEFAULT";
}
```

### 3. Use Constants for Magic Numbers

```
// Good
const int DEFAULT_MAX_VEHICLES = 10;
MaxStorableVehicles = DEFAULT_MAX_VEHICLES;

// Avoid
MaxStorableVehicles = 10;
```

### 4. Initialize Member Variables

Initialize in constructor or at declaration:

```
void ExpansionGarageSettings()
{
    EntityWhitelist = new TStringArray;
    m_IsLoaded = false;
}
```

### 5. Document Complex Logic

```
//! Toggle between hidden and previously set visibility state for each marker category
int visibility;
int previousVisibility;

visibility |= m_MarkerModule.GetVisibility(ExpansionMapMarkerType.SERVER);
previousVisibility |= m_MarkerModule.GetPreviousVisibility(ExpansionMapMarkerType.SERVER);
```

### 6. Use Bitwise Operations Appropriately

```
layerMask |= PhxInteractionLayers.BUILDING;
layerMask |= PhxInteractionLayers.VEHICLE;
layerMask |= PhxInteractionLayers.TERRAIN;

visibility &= EXPANSION_MARKER_VIS_WORLD;
```

### 7. Leverage Type Safety

```
// Use enums
eAILootingBehavior behavior;

// Use proper casting
PlayerBase player = PlayerBase.Cast(entity);
if (player)
{
    // Safe to use player
}
```

### 8. Avoid Complex Expressions in Array Assignments

**Segfault Risk:**

Some language constructs that work in other languages cause segfaults in EnScript:

```
class MyClass
{
    bool m_IsInside[3];

    // WRONG - Causes segfault
    void TestBad(int index, vector a, vector b, float distSq)
    {
        m_IsInside[index] = vector.DistanceSq(a, b) <= distSq;
    }

    // CORRECT - Use intermediate variable
    void TestGood(int index, vector a, vector b, float distSq)
    {
        bool isInside = vector.DistanceSq(a, b) <= distSq;
        m_IsInside[index] = isInside;
    }
}
```

**Rule:** For array assignments with complex expressions, use an intermediate variable.

### 9. Be Aware of Integer Limits

**Integer Comparison Quirk:**

```
// int.MIN = -2147483648

1 < int.MIN;      // Returns TRUE in EnScript!
1 < -2147483647;  // Also returns TRUE!

// Always be careful with MIN/MAX integer comparisons
```

---

## Common Pitfalls and Issues

### Compiler Error Messages

**Misleading Error Locations:**

Compile errors involving:

- Undefined classes (missing addon not loaded)
- Variable name conflicts

Will **NOT** show the correct filename and line number. Instead, they show the last successfully parsed `.c` file at EOF, which is misleading and unhelpful.

**What to do:**

- If error location seems wrong, search for the class/variable name in your entire codebase
- Check that all required addons are loaded
- Look for name conflicts across files

### Understanding Log Files

- **Exception logs:** `crash_<date>_<time>.log` - Contains exceptions (NOT crashes)
- **Actual crashes:** Segfaults create different crash dumps
- Check both log types when debugging issues

### Common Segfault Causes

1. **Complex array assignments** - Use intermediate variables
2. **Empty preprocessor blocks** - Must contain at least one statement
3. **Misused `delete` keyword** - Let garbage collection handle it
4. **Over-specified `ref` usage** - Only use on members/typedefs

### Performance Considerations

- Aggressive garbage collection destroys function-scope instances immediately
- Use `ref`/`autoptr` on class members to prevent premature collection
- Avoid creating temporary objects in tight loops

---

## Production-verified pitfalls

These are runtime / engine / vanilla-bug issues that bite in real DayZ
production work. Each row includes a verification source so reviewers can
re-check independently.

### Timer & callback bugs

**`CallLater` loses precision after ~4.5 hours of game time.** The engine's
`CallLater` uses a 32-bit float for the absolute due time. Beyond ~4.5h of
elapsed game time, that float saturates and callback timing drifts or stalls
entirely.

```c
// AVOID for long-lived recurring work
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(this.Tick, 1000, true);

// PREFER — Timer class plus periodic resync, or a Manager singleton driving
// timestamps off SystemTime / DateTime to escape the float-window.
ref Timer m_Tick = new Timer(CALL_CATEGORY_GAMEPLAY);
m_Tick.Run(1.0, this, "Tick", null, true);
```

Symptom in logs: callbacks that fired correctly for hours suddenly skip or
fire many times back-to-back as the float resaturates. Verified via long-run
production server logs.

### Vanilla bug — `inventorySlot` string vs array (`T148506`)

When a vanilla item's config declares `inventorySlot` as a **string** (single
slot), trying to extend it from a mod with the `+=` array-append syntax fails
silently — the mod's slot is dropped at parse time.

```cpp
// Vanilla (DZ\gear\camping\config.cpp ~ line 10074):
class WoodenCrate : Inventory_Base
{
    inventorySlot = "WoodenCrate";       // STRING, not array
};

// FAILS silently — append to a string isn't valid:
class MyMod_FancyCrate : WoodenCrate
{
    inventorySlot[] += {"MyMod_CustomSlot"};
};

// FIX — redeclare as an explicit array, including the original value:
class MyMod_FancyCrate : WoodenCrate
{
    inventorySlot[] = {"WoodenCrate", "MyMod_CustomSlot"};
};
```

Bohemia ticket: `T148506`. The bug is "won't fix"; the workaround is
mandatory. Symptom: attachment slot just doesn't accept the modded item, no
RPT error, no script error.

### Action system

**`CCINonRuined` vs `CCINone` for "must be holding tool" actions.** Use
`CCINonRuined` (item-in-hand, must not be ruined) NOT `CCINone` (no item
needed) when the action requires holding a specific tool. With `CCINone` the
engine may skip the action entirely when an item IS in hand, even if your
condition would have passed.

```c
// CORRECT for tool-in-hand actions
override void CreateConditionComponents()
{
    m_ConditionItem = new CCINonRuined;     // tool must be present, non-ruined
    m_ConditionTarget = new CCTNone;
}

// AVOID — engine may skip when item-in-hand
m_ConditionItem = new CCINone;
```

**`RemoveAction` pickup-prevention pattern.** Overriding `IsTakeable()` alone
is not enough to prevent a placed item from being picked up by drag — the
player can still grab it. Full prevention is a 4-step pattern:

```c
override bool IsTakeable() { return false; }

override void SetActions()
{
    super.SetActions();
    RemoveAction(ActionTakeItem);
    RemoveAction(ActionTakeItemToHands);
}

override bool CanPutInCargo(EntityAI parent) { return false; }
```

**Action client/server check style mismatch.** If the client uses `IsKindOf()`
to decide an action shows up but the server uses `GetType() == "..."` to
validate, the action may render but be rejected on execute (or vice versa).
Use the **same** check style on both sides — `IsKindOf()` is preferred
because it respects inheritance.

### RPC ID collisions

When defining custom RPC IDs, **start at a high unique base** to avoid
colliding with vanilla and other mods.

```c
enum eMyMod_RPC
{
    START          = 25416533,   // any high random base
    SyncPowerState,
    RequestActivate,
    BroadcastEvent,
    // ...
}
```

Low IDs (1-100) are heavily used by vanilla. Symptom of collision: RPC fires
"the wrong handler" intermittently when another mod is loaded.

### `ScriptInvoker` shutdown crash

A common cleanup pattern null-derefs on shutdown:

```c
// CRASHES if the static invoker was already torn down
MyClass.Event_PowerChanged.Remove(m_Callback);

// CORRECT — null-check first
if (MyClass.Event_PowerChanged)
    MyClass.Event_PowerChanged.Remove(m_Callback);
```

Static invokers don't have a stable destructor order; assume they may already
be null during your destructor / mission cleanup.

### `inputs.xml` keybind format

Custom keybinds require a specific 3-piece setup. Missing any one piece
results in "keybind does nothing" with no log error.

1. **`MyMod\inputs.xml`** must use `<modded_inputs>` as the root tag (NOT
   `<inputs>`):

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <modded_inputs>
       <action name="UAMyModToggleHud" preset="default">
           <key name="KC_F4"/>
       </action>
   </modded_inputs>
   ```

2. **`config.cpp`** must register the file under `CfgMods`:

   ```cpp
   class CfgMods
   {
       class MyMod
       {
           inputs = "MyMod\\inputs.xml";   // backslash-escaped
       };
   };
   ```

3. **Script** reads via `GetGame().GetInput().LocalPress("UAMyModToggleHud", false)`.

Wrong root tag, missing `inputs = ` line, or using `LocalRelease` when you
meant `LocalPress` — all silent failures with no log warning.

### Layout path & Dabs ghost-menu trap

A `.layout` file's path passed to `GetLayoutFile()` MUST match the mod's
`$PBOPREFIX$` exactly. Mismatched path → engine fails to load the layout AND
Dabs Framework's `ScriptViewMenu` singleton state remains set, causing the
menu to appear "open" forever (no other UI menus can open).

```c
// In a Dabs ScriptViewMenu subclass:
override string GetLayoutFile()
{
    // If $PBOPREFIX$ is "MyMod", the path MUST start with "MyMod\..."
    return "MyMod/gui/layouts/main_menu.layout";
}

// Defensive guard so a layout-load failure doesn't poison the singleton:
override void OnShow()
{
    super.OnShow();
    if (!GetLayoutRoot())
    {
        s_Instance = null;          // free the ghost menu state
        // log + early return
        return;
    }
}
```

### Magazines vs items — `ServerSetAmmoCount` vs `SetQuantity`

For magazines (`Magazine_Base` and subclasses including ammo piles), calling
`ItemBase.SetQuantity(N)` does NOT populate the ammo count. The mag spawns
with 0 rounds despite reporting "quantity = N".

```c
// DWIM helper for "set quantity on whatever this is"
void SetQuantityOrAmmo(EntityAI ent, float value)
{
    Magazine mag = Magazine.Cast(ent);
    if (mag)
    {
        mag.ServerSetAmmoCount(value.ToInt());
        return;
    }
    ItemBase ib = ItemBase.Cast(ent);
    if (ib)
        ib.SetQuantity(value);
}
```

Verified `Magazine.ServerSetAmmoCount` at
`P:\scripts\4_world\entities\itembase\magazine\magazine.c:70`. Vanilla uses
this pattern in `weapon_base.c:805`, `cfgplayerspawnhandler.c:330,340`, and
~20 other call sites.

### String operations — quirks worth knowing

**`String.ToLower()` / `String.ToUpper()` mutate in place.** They return
nothing useful (some return self, some void depending on engine version).
Always copy first if you need to preserve the original:

```c
string original = "Hello World";

// WRONG — mutates original
original.ToLower();

// CORRECT — copy by concatenation, then mutate the copy
string lower = original + "";
lower.ToLower();
```

The `+ ""` forces an allocation; assignment alone (`string lower = original;`)
shares the underlying string in some engine versions.

**Existence — these vanilla helpers DO exist (counters outdated wiki/forum
claims):**

| API | Verified location |
|---|---|
| `Math.Clamp(val, min, max)` | `P:\scripts\1_core\proto\enmath.c` |
| `Math.Min`, `Math.Max`, `Math.Sqrt`, `Math.Pow` | same |
| `string.IndexOfFrom(startPos, search)` | `P:\scripts\1_core\proto\enstring.c` |
| `string.LastIndexOf`, `string.Hash`, `string.Replace` | same |

If older modding guides say "you need to write a custom Clamp" — they're stale.

### `CONFIG_NOT_FOUND` — config-path format

Config-lookup errors are silent unless you check the return; the path format
is **space-separated**, not dot-notation:

```c
// CORRECT
GetGame().ConfigGetText("CfgVehicles ClassName displayName", out_str);
GetGame().ConfigGetFloat("CfgWeapons ClassName fireMode " + i + " dispersion");

// WRONG — silently returns nothing
GetGame().ConfigGetText("CfgVehicles.ClassName.displayName", out_str);
```

### `SetObjectTexture` quirks

- **Hidden selection name is case-sensitive** vs. the named selection in the
  `.p3d`. Mismatch → texture silently ignored, no log warn.
- **Index is the position in `hiddenSelections[]`** (0-based), NOT the
  selection name. A model with one selection at `hiddenSelections[] = {"camo1"}`
  uses index `0`.
- **`GetObjectTextures()` path differs from config path.** Engine normalizes
  by stripping leading backslashes:

  ```c
  // config.cpp says:    "\dz\gear\camping\data\crate_co.paa"
  // GetObjectTextures: "dz\gear\camping\data\crate_co.paa"
  ```

  When saving and restoring textures across serialization, use the result of
  `GetObjectTextures()` as the canonical form, NOT the hardcoded config path.

- **`SetObjectTextureGlobal()` may NOT exist on your DayZ build.** Calling a
  method that doesn't exist makes the **entire script file fail to compile**,
  not just that line. Verify with `Grep` over `P:\scripts\` before using.

### Custom containers — extend the **vanilla script class**, NOT `ItemBase`

For mods that add custom barrels, crates, or storage containers, extending
`ItemBase` directly drops vanilla behavior (e.g. open/close animation, color
selection on barrels, weather-tint on tents). Find the vanilla **script**
class that matches your config parent and extend that.

```c
// Vanilla "Barrel_ColorBase" lives at
//   P:\scripts\4_world\entities\itembase\barrel_colorbase.c
// — handles open/close action, paintable color, weather effects.

// CORRECT — extend the vanilla script class
class MyMod_FancyBarrel : Barrel_ColorBase
{
    override void EEKilled(Object killer)
    {
        super.EEKilled(killer);
        // your custom death logic
    }
}

// AVOID — drops vanilla barrel behavior
class MyMod_FancyBarrel : ItemBase
{
    // ...
}
```

The script class name often differs from the config class name. Search by
config parent: if your `config.cpp` has `class MyBarrel : Barrel_ColorBase`,
the script file is `barrel_colorbase.c` somewhere under `P:\scripts\4_world\`.

Also remember to add the vanilla addon to your `requiredAddons[]` if the
script class isn't in core:

```cpp
class CfgPatches
{
    class MyMod
    {
        requiredAddons[] = { "DZ_Data", "DZ_Gear_Containers" };
    };
};
```

### Periodic ticks — `new` allocation kills perf

In any function called every tick (`OnUpdate`, `OnPostFrameUpdate`, repeating
`CallLater`/`Timer` callback), allocating arrays/maps/Param objects creates
GC pressure that compounds:

```c
// BAD — allocates every tick, GC churn
override void OnUpdate(float dt)
{
    array<Object> nearby = new array<Object>;
    GetGame().GetObjectsAtPosition(GetPosition(), 10.0, nearby, null);
    // ...
}

// GOOD — allocate once, .Clear() every tick
ref array<Object> m_NearbyBuf = new array<Object>;

override void OnUpdate(float dt)
{
    m_NearbyBuf.Clear();
    GetGame().GetObjectsAtPosition(GetPosition(), 10.0, m_NearbyBuf, null);
    // ...
}
```

The engine's GC is aggressive on function-scope refs; high-frequency `new`
inside ticks shows up as periodic frame-time spikes in the diag profiler.

### `GetScreenPos` for HUD markers — check Z for "behind camera"

`GetGame().GetScreenPos(worldPos)` returns valid x,y even when the world
position is behind the camera. The z component tells you which side:

```c
vector screenPos = GetGame().GetScreenPos(targetWorldPos);
if (screenPos[2] <= 0)
{
    // behind camera — hide the marker
    m_Marker.Show(false);
    return;
}
m_Marker.Show(true);
m_Marker.SetPos(screenPos[0], screenPos[1]);
```

Without the z check, your "compass marker" or "objective indicator" jitters
around the screen edges when you turn away from the target.

### Modded class members on engine entity classes — caveat

Adding `m_X` member fields to `modded class DayZGame` is safe — `DayZGame` is
a script-side singleton with stable lifecycle.

For `modded class PlayerBase` / `modded class ItemBase`, member fields are
mostly safe BUT some entity classes have engine-side serialization that can
mis-align if many mods add fields and the order shifts. If you see strange
crashes at player connect or item spawn that go away when removing a member
field, consider an external static map keyed by the entity instead:

```c
// Safer for high-coverage modded fields:
class MyMod_StateMap
{
    static ref map<int, ref MyState> s_StateByEntId = new map<int, ref MyState>;
}
```

This is rare. Default to member fields; only reach for the static-map
workaround if you can reproduce a serialization-related crash.

---

## Quick reference — symptom → cause → fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Action shows on client, server rejects on execute | Mismatched check style (`IsKindOf` vs `GetType ==`) | Use identical check both sides |
| Attachment slot rejects modded item | T148506 — vanilla `inventorySlot` is string | Redeclare as `inventorySlot[] = {"vanilla", "custom"}` |
| Item placed but draggable into inventory | Only `IsTakeable()` overridden | Add `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)` + `CanPutInCargo() = false` |
| Mag spawns with 0 rounds despite quantity set | `SetQuantity` doesn't populate ammo on Magazines | `Magazine.Cast(...).ServerSetAmmoCount(N)` |
| Layout fails + all menus blocked | `ScriptViewMenu` singleton stuck | Guard: `if (!GetLayoutRoot()) { s_Instance = null; return; }` |
| Keybind does nothing | Wrong root tag in `inputs.xml` | Use `<modded_inputs>`, not `<inputs>` |
| RPC fires "wrong handler" with another mod | RPC ID collision in low range | Start enum at high unique base (e.g. `25416533`) |
| Crash on shutdown / mission end | Static `ScriptInvoker.Remove()` after teardown | Null-guard: `if (X.Event_Y) X.Event_Y.Remove(cb);` |
| `SetObjectTexture` no-op | Selection name case mismatch with `.p3d` | Verify exact case from `GetObjectTextures()` |
| Whole script file fails to compile, no obvious cause | Calling method that doesn't exist (e.g. `SetObjectTextureGlobal` on builds without it) | Grep `P:\scripts\` to verify method exists before use |
| HUD marker appears at wrong screen edge | `GetScreenPos` z not checked | `if (screenPos[2] <= 0) hide;` |
| Custom barrel missing open/close anim | Extends `ItemBase` instead of `Barrel_ColorBase` | Extend the vanilla SCRIPT class, not `ItemBase` |
| Long-running callback drifts after ~4.5h | `CallLater` 32-bit float overflow | Use `Timer` class + periodic resync |
| Frame-time spikes every N seconds | `new array/map/Param` in tick path | Member field + `.Clear()` per tick |

---

## Conclusion

This style guide reflects the conventions used in professional DayZ modding. Consistency with these patterns will make your code more maintainable and easier to integrate with existing mods and the vanilla codebase.

### Key Takeaways

- Use PascalCase for classes and methods
- Use `m_` prefix for member variables, `s_` for static
- Use tabs for indentation
- Always use `override` keyword when overriding
- Check for null before using objects
- Document complex logic with comments
- Use preprocessor directives for conditional compilation
- Follow the modded class pattern for extending vanilla code
- Where possible, use proto methods over custom methods for expensive logic
- CfgMod class names are defines in script as of 1.26
- **NEVER use `ref` in method parameters, return types, or local variables** - only on member variables and templates
- **NEVER add inheritance (`: ParentClass`) to `modded` classes** - they already inherit from the original class

### References

- [DayZ Script Diff (Bohemia Interactive)](https://github.com/BohemiaInteractive/DayZ-Script-Diff)
- [DayZ Expansion Scripts](https://github.com/salutesh/DayZ-Expansion-Scripts)
- [Bohemia Interactive Community Wiki - Enforce Script](https://community.bistudio.com/wiki/DayZ:Enforce_Script_Syntax)
