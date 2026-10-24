# Enforce Script style: Memory and `ref`

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: The checked lifetime facts (`Class` against `Managed`, `ref`, `autoptr`, `delete`, deleting entities) are in `../enscript/references/language_memory.md`; it cites `P:\scripts\` and wins where the two differ.

## Memory Management

### Object Creation

Use `new` keyword (with or without trailing parentheses for constructors without arguments):

```
AllowedItems = new TStringArray;      // Valid
m_Settings = new MyMod_Settings();    // Valid
```

Both forms are acceptable: choose one style and be consistent.

### Managed Classes

Inherit from `Managed` for automatic reference counting:

```
class MyClass : Managed
{
    // No manual deletion needed
}
```

**Note:** Entities (`Object`, `EntityAI`, `ItemBase`, `PlayerBase`) are owned by the engine. Give your own helper and data classes `Managed` (or a vanilla class that has it) as the root; see `../enscript/references/language_memory.md`, "The two roots".

### Freeing objects

A `Managed` object is freed when its last strong (`ref`) reference goes away; a plain reference does not keep it alive. This is engine behaviour, stated in `../enscript/references/language_memory.md`, "`ref` keeps an object alive".

### Deletion

**Never `delete` an entity** (`Object`, `EntityAI`, `ItemBase`, `PlayerBase`). Use the engine calls instead: `Delete()` (`P:\scripts\3_game\entities\entityai.c:779`) or, for items that may sit in a player's inventory, `DeleteSafe()` (`P:\scripts\3_game\entities\entityai.c:791`). See `../enscript/references/language_memory.md`, "Deleting entities".

```
// WRONG: delete on an entity
delete item;

// CORRECT
item.DeleteSafe();
```

**`delete` on your own script object is allowed** and frees it now. Vanilla does it: `delete GetBleedingManagerServer();` (`P:\scripts\4_world\entities\manbase\playerbase.c:1224`), and an object may free itself with `delete this;` (`P:\scripts\4_world\classes\bullethitreaction\bullethitreaction.c:45`). Only do it when no other code still holds a reference to that object. When you just want to let go, set your last `ref` to `null` instead.

### Reference Management (CRITICAL)

`ref` makes a strong reference. Two mistakes have checked effects (`../enscript/references/language_memory.md`, rules 1 and 3, engine behaviour):

- A member you create with `new` and that nothing else holds, without `ref`, is freed at once. It reads `null` right after it was set.
- Two objects that hold `ref`s to each other keep each other alive forever (a leak). The parent owns the child with `ref`; the child points back without `ref`.

Unverified: that `ref` mistakes crash the game or affect other mods. No vanilla source on `P:\scripts\` shows either.

#### CORRECT Usage of `ref`

**Member Variables:**

```
class MyClass
{
    ref MyOtherClass m_Member;        // Safe: member variable
    ref array<string> m_Items;        // Safe: member variable

    void MyClass()
    {
        m_Member = new MyOtherClass();
    }
}
```

**Element types of containers you fill with your own objects:**

`ref` on the member owns the container, not what is in it. If the container holds objects you create with `new`, the element type needs `ref` too, or nothing owns the elements and they are freed (`../enscript/references/language_memory.md`, rule 2). Vanilla spells out both forms: `typedef array<Managed> TManagedArray;` and `typedef array<ref Managed> TManagedRefArray;` (`P:\scripts\1_core\proto\enscript.c:736`, `:737`).

```
class MyMod_Registry
{
    ref array<ref MyData> m_Entries;  // Owns the array AND each MyData in it
    ref array<EntityAI> m_Items;      // Entities: the engine owns them, no ref on the element

    void MyMod_Registry()
    {
        m_Entries = new array<ref MyData>;
        m_Entries.Insert(new MyData());  // Kept alive by the ref element type
    }
}
```

**Note:** `autoptr` is the older owning qualifier. Vanilla still has it in old code (`autoptr map<string, float> m_values;`, `P:\scripts\1_core\proto\serializer.c:14`), but use `ref` in mod code (`../enscript/references/language_memory.md`, "`autoptr`").

**Note:** Do NOT put `ref` on the aliased type itself (`typedef ref T`). `ref` inside a template argument of a typedef is allowed and is how vanilla names owning containers: `typedef array<ref Managed> TManagedRefArray;` (`P:\scripts\1_core\proto\enscript.c:737`). No `typedef ref` form appears anywhere under `P:\scripts\`.

```
// WRONG: ref on the aliased type
typedef ref MyClass MyClassRef;

// CORRECT
typedef MyClass MyClassRef;

// ALSO CORRECT: ref on the element type, as vanilla does
typedef array<ref MyData> MyDataRefArray;
```

#### INCORRECT Usage of `ref`

**DO NOT use `ref` in:**

1. **Method Parameters:**

```
// AVOID: ref on parameters and return type is not needed in mod code (style)
ref MyClass MyMethod(ref MyClass1 a, ref MyClass2 b)
{
    // ...
}

// CORRECT: No ref on parameters
MyClass MyMethod(MyClass1 a, MyClass2 b)
{
    // ...
}
```

2. **Return Types:**

```
// AVOID: not needed in mod code (style). Vanilla does compile it, e.g.
// `ref map<int, string> GetAttachSoundSets()` (P:\scripts\3_game\inventoryitemtype.c:20)
ref MyClass GetObject()
{
    ref MyClass obj = new MyClass();
    return obj;
}

// CORRECT: Return without ref
MyClass GetObject()
{
    MyClass obj = new MyClass();
    return obj;
}
```

3. **Local Variables:**

```
// AVOID: ref on a local is not needed in mod code (style). Vanilla does it,
// e.g. `ref set<Object> victims = new set<Object>;` (P:\scripts\4_world\classes\areadamage\areadamage.c:175)
void MyMethodAvoid()
{
    ref MyClass3 myClass3 = new ref MyClass3();
}

// CORRECT: No ref on local variables
void MyMethod()
{
    MyClass3 myClass3 = new MyClass3();
}
```

4. **`new` Keyword:**

```
// AVOID: ref with new (style: no vanilla file uses `new ref`, grep of P:\scripts;
// whether it compiles is unverified)
ref MyClass obj = new ref MyClass();

// CORRECT
MyClass obj = new MyClass();

// ALSO CORRECT: For member variables
m_Member = new MyClass();
```

#### Reference Counting Best Practices

**1. Minimize Strong References:**

Hold only ONE explicit strong reference (using `ref` keyword) when possible:

```
class MyMod_ItemTracker
{
    // GOOD: Single strong reference on member
    ref array<EntityAI> m_Items;

    void AddItem(EntityAI item)
    {
        // CORRECT: No ref on parameter or local var
        if (!m_Items)
            m_Items = new array<EntityAI>;

        m_Items.Insert(item);
    }
}
```

**2. Prefer One Owner (style):**

Two strong refs to the same object is valid shared ownership: it does not
leak or crash (only freed-too-early and ref cycles are real effects, see
`../enscript/references/language_memory.md`, rules 1 and 3). One owner is a style preference so lifetime is obvious.
Keep shared ownership when both holders must keep the object alive: a weak
copy reads null once the single owner lets go.

```
// AVOID (style, no leak or crash): two owners make lifetime harder to follow
class BadExample
{
    ref MyClass m_Object1;
    ref MyClass m_Object2;

    void BadExample()
    {
        MyClass obj = new MyClass();
        m_Object1 = obj;
        m_Object2 = obj;  // Second owner: valid, just less obvious
    }
}

// PREFERRED (style): one owner, one weak observer
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
// PREFERRED: Let the engine manage it
array<EntityAI> GetItems()
{
    array<EntityAI> result = {};
    // populate result
    return result;
}

// AVOID: Over-specified refs
ref array<EntityAI> GetItems()
{
    ref array<EntityAI> result = new ref array<EntityAI>;
    return result;
}
```

#### Common Issues Caused by Incorrect `ref` Usage

- **Freed too early**: a member made with `new` and no `ref` is freed at once, so later uses find `null` (`../enscript/references/language_memory.md`, rule 1, engine behaviour)
- **Leaks**: two objects holding `ref`s to each other are never freed (`../enscript/references/language_memory.md`, rule 3, engine behaviour)
- **Unverified**: crashes or effects on other mods. No vanilla source on `P:\scripts\` shows that a `ref` mistake causes either.

`ref` on parameters, return types and locals is a style point only (Quick Reference Rules, rule 2); it is not on this list.

#### Quick Reference Rules

1. **USE `ref` for:** Member variables you own, and the element type of containers that hold objects you create (`ref array<ref MyData>`, as in `typedef array<ref Managed> TManagedRefArray;`, `P:\scripts\1_core\proto\enscript.c:737`)
2. **Do not use `ref` for (style, not needed in mod code):** Method parameters, return types, local variables, and the aliased type of a typedef (`typedef ref T`)
3. **Do not use (style):** `new ref ClassName()`. No vanilla file uses `new ref` (grep of `P:\scripts`); whether it compiles is unverified
4. **ALWAYS use:** `new ClassName()`
5. **Goal:** One strong reference per object when possible
6. **NEVER `delete` an entity**: use `Delete()` or `DeleteSafe()`. `delete` on your own script object is allowed when nothing else holds it
7. **No `autoptr`:** it is legacy; use `ref` in mod code

**When in doubt on a parameter, return type or local, omit the `ref` keyword and let EnScript's automatic reference counting handle it. Owning members and their element types still need it.**
