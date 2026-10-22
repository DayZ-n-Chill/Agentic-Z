# Enforce Script style: Modding patterns

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Each topic has a checked file: `../enscript/patterns/modded_class.md`, `patterns/singleton.md`, `../persistence/save-load-contract.md`, `../enscript/integrations/input_bindings.md`.

## Modding Patterns

### Modded Classes

Use `modded` keyword to extend vanilla classes:

```
modded class MissionGameplay
{
    // Additional members and methods

    override void OnUpdate(float timeslice)   // P:\scripts\5_mission\mission\missiongameplay.c:287
    {
        super.OnUpdate(timeslice);
        // Additional implementation
    }
}
```

**CRITICAL: Never Add Inheritance to Modded Classes**

When using the `modded` keyword, **NEVER** add inheritance (`: ParentClass`). The modded class automatically inherits from the original class definition.

```
// WRONG: Adding inheritance to modded class
modded class PlayerBase : ManBase
{
    // Inheritance declaration is ignored!
}

// CORRECT: No inheritance declaration
modded class PlayerBase
{
    // This properly extends the original PlayerBase
}
```

**Why This Matters:**

- Adding inheritance to a `modded` class is **ignored by the compiler**
- You cannot change the class hierarchy by modding an existing class
- It's misleading to readers and should be omitted
- The modded class already IS the class you're modding: you're just adding to it

**Rule:** `modded class ClassName` never has `: ParentClass`: you cannot change its inheritance.

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
// BAD: Global function and separate class
class MyClass { }
MyClass GetMyClassInstance() { return new MyClass(); }

// GOOD: Singleton pattern on the class itself
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

// ALSO GOOD: Public static instance
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
// PREFERRED: Direct global access
g_Game.GetPlayer();

// LESS PREFERRED: Getter function
GetGame().GetPlayer();
```

**Note:** While using getters is common in vanilla code, direct access is often clearer and more efficient. This is why `proto native CGame GetGame()` was replaced with `DayZGame GetGame() { return g_Game; }` (`P:\scripts\3_game\gameplay.c:636`): the script version is faster for simple global access due to the overhead of calling native methods.

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

// PREFERRED: Direct access
int value = instance.PublicValue;

// LESS PREFERRED: Unnecessary getter
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
// Write and read the same fields in the same order on both sides
void WriteTo(ParamsWriteContext ctx)
{
    ctx.Write(MaxItems);
    ctx.Write(EnableWelcomeMsg);

    #ifdef MYMOD_FEATURE_X
        ctx.Write(FeatureXLevel);
    #endif
}

bool ReadFrom(ParamsReadContext ctx)
{
    if (!ctx.Read(MaxItems))
        return false;
    if (!ctx.Read(EnableWelcomeMsg))
        return false;

    #ifdef MYMOD_FEATURE_X
        if (!ctx.Read(FeatureXLevel))
            return false;
    #endif

    return true;
}
```

---

## Input Handling

### Standard Pattern

```
if (input.LocalPress("UAMyModOpenMenu", false) && !menuOpen)
{
    OpenSettingsMenu();
}
```

---

## Module System

Vanilla has no module system of its own; its shared services are plugins. For those, register a `PluginBase` subclass in a modded `PluginManager.Init()` (`../enscript/integrations/vanilla_plugins.md`). With Community Framework, use a `CF_ModuleWorld` with `[CF_RegisterModule(...)]` (`../enscript/integrations/community_framework.md`). Both files cite their sources.
