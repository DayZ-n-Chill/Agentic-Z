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
TStringArray allowedItems;     // typedef array<string>, P:\scripts\1_core\proto\enscript.c:731
ref TVectorArray m_SpawnPoints; // ref: this object owns the array
```

### References

Use `ref` for owned (strong) references on member variables:

```
ref MyMod_SettingsMenu m_MyMod_SettingsMenu;
ref TVectorArray m_SpawnPoints;
```

- **`ref`**: a strong reference. The instance is deleted when the last strong reference to it goes away (`../enscript/references/language_memory.md`).
- **`autoptr`**: the older owning qualifier, not a separate model. Vanilla keeps it in ten files, mostly `1_core` docs and examples (`autoptr map<string, float> m_values;`, `P:\scripts\1_core\proto\serializer.c:14`). Newer vanilla code uses `ref` for members. Use `ref` in mod code (`../enscript/references/language_memory.md`, section `autoptr`).

```
class Example
{
    ref MyClass m_Instance; // owned by Example
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
