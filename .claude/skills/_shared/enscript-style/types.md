# Enforce Script style: Types and casting

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: The checked type facts are in `../enscript/references/language_types.md`; it cites `P:\scripts\` and wins where the two differ.

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
// `c` is NOT a class: it's an instance
SomeClass c = new SomeClass();

// `typename` represents the actual class
typename t = c.Type();  // Returns the class type

// Type checking methods
c.Type()              // Returns typename (the class)  P:\scripts\1_core\proto\enscript.c:52
c.Type().ToString()   // Returns class name as string
c.ClassName()         // Same as Type().ToString(): prefer this  enscript.c:37
c.GetType()           // Returns config.cpp class name for entities if defined (PREFERRED)  P:\scripts\3_game\entities\object.c:467
                      // NOTE: Will differ from script class name if no script declaration exists
```

**Best Practice:** Use `GetType()` over `ClassName()` for entities, as it returns the actual config class name which may differ from the script class name.

### Collections

**Shorthand Array Initialization (PREFERRED):**

```
// PREFERRED: Shorthand initialization
array<string> stringArray = {};
array<int> numbers = {1, 2, 3};

// ACCEPTABLE: Explicit initialization
array<string> stringArray = new array<string>;
```

**Type Definitions:**

```
TStringArray entityWhitelist;  // typedef array<string>, P:\scripts\1_core\proto\enscript.c:731
autoptr TVectorArray waypoints; // autoptr for managed arrays
```

### References

Use `ref` or `autoptr` for managed references on member variables:

```
ref MapMenu m_MyMod_MapMenu;
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

Both methods are valid: `CastTo` combines the cast and check in one line, while `Cast` is more explicit.
