# Enforce Script style: Memory and `ref`

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: The checked lifetime facts (`Class` against `Managed`, `ref`, `autoptr`, `delete`, deleting entities) are in `../enscript/references/language_memory.md`; it cites `P:\scripts\` and wins where the two differ.

## Memory Management

### Object Creation

Use `new` keyword (with or without trailing parentheses for constructors without arguments):

```
EntityWhitelist = new TStringArray;             // Valid
m_MarkerModule = new MyMod_MarkerModule();   // Valid
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

### Garbage Collection

**Understanding EnScript Garbage Collection:**

- Everything (except `Managed`) is a **weak reference by default**
- The garbage collector is **very aggressive**: instances in function scope are destroyed immediately when scope ends
- All instances (Managed or not) are garbage collected when reference count reaches zero

### Deletion

**STRONGLY DISCOURAGED:** Avoid using the `delete` keyword in almost all cases.

```
// AVOID: Using delete keyword
delete myObject;

// PREFERRED: Null the reference instead
myObject = null;
```

**Why avoid `delete`?**

- Can cause segfaults if object is still referenced elsewhere
- **NEVER use for entities**: will cause crashes
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
    ref MyOtherClass m_Member;        // Safe: member variable
    autoptr array<string> m_Items;    // Safe: member variable with autoptr

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
// WRONG: Causes memory issues
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
// WRONG: Causes reference counting issues
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
void MyMethod()
{
    // WRONG: Unnecessary ref on local variable
    ref MyClass3 myClass3 = new ref MyClass3();

    // CORRECT: No ref on local variables
    MyClass3 myClass3 = new MyClass3();
}
```

4. **`new` Keyword:**

```
// WRONG: Never use ref with new
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
class VehicleManager
{
    // GOOD: Single strong reference on member
    ref array<EntityAI> m_Vehicles;

    void AddVehicle(EntityAI vehicle)
    {
        // CORRECT: No ref on parameter or local var
        if (!m_Vehicles)
            m_Vehicles = new array<EntityAI>;

        m_Vehicles.Insert(vehicle);
    }
}
```

**2. Avoid Creating Multiple Strong References:**

```
// BAD: Multiple strong refs to same object
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

// GOOD: Single strong reference
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
array<EntityAI> GetVehicles()
{
    array<EntityAI> result = {};
    // populate result
    return result;
}

// AVOID: Over-specified refs
ref array<EntityAI> GetVehicles()
{
    ref array<EntityAI> result = new ref array<EntityAI>;
    return result;
}
```

#### Common Issues Caused by Incorrect `ref` Usage

- **Crashes**: Reference counting errors lead to premature deletion or memory leaks
- **Null pointer exceptions**: Objects deleted unexpectedly
- **Cross-mod interference**: Your ref issues affect other mods
- **Unpredictable behavior**: Objects existing longer than intended
- **Memory leaks**: Objects never getting cleaned up

#### Quick Reference Rules

1. **USE `ref` (or `autoptr`) for:** Member variables ONLY
2. **NEVER use `ref` for:** Method parameters, return types, local variables, typedefs
3. **NEVER use:** `new ref ClassName()`
4. **ALWAYS use:** `new ClassName()`
5. **Goal:** One strong reference per object when possible
6. **NEVER use `delete`**: let garbage collection handle cleanup
7. **Don't mix:** Use either `ref` OR `autoptr`, not both in the same codebase

**When in doubt, omit the `ref` keyword and let EnScript's automatic reference counting handle it.**
