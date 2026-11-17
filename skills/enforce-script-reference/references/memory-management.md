# Memory management

`ref`, `autoptr`, `delete`, reference cycles and the lifetime traps that crash a mod after hours. A line cited as `P:\...:N` was opened on `P:\`; the runtime measurements are the knowledge pack author's and were not re-run here. The checked reference for the same topic is `skills/_shared/enscript/references/language_memory.md`; where the two differ, that file's `P:\` citations decide (the differences are noted in place below).

## Reference counting

Enforce Script manages memory by reference counting. Unlike a mark and sweep collector it is deterministic: an object is destroyed as soon as its reference count reaches zero.

### Two class families

**Managed classes** (inherit from `Managed`):
- Entities are `Managed`: `class Object extends IEntity` (`P:\scripts\3_game\entities\object.c:64`) and `class IEntity: Managed` (`P:\scripts\1_core\proto\enentity.c:164`) [EXACT][CLAIM-ENF-ENTITY-MANAGED-164289]. Their lifetime is still the engine's: never hold an entity with `ref` (see `language_memory.md`)
- Instances survive as long as at least one strong reference exists
- A class **field** without `ref` is weak here too (measured below)

**Plain classes** (no `Managed` ancestor):
- **Class fields** are weak by default: use `ref` to keep the target alive. This is where `ref` bugs live.
- **Local variables** are strong references by default (as Bohemia's Enforce Script wiki says). The object lives to the end of the scope, so `new X()` assigned to a plain local needs no `ref`.
- In short: "weak by default" is about class fields, not about locals.

### The `ref` keyword: strong references

`ref` creates a strong reference that keeps the target alive.

**Correct: `ref` on class member fields.**
```
class MyManager
{
    // Strong ref keeps the map alive as long as MyManager lives
    ref map<string, ref array<string>> m_Data;

    void MyManager()
    {
        m_Data = new map<string, ref array<string>>;
    }
}
```

**Wrong: these are real errors.**
```
// WRONG: ref on function parameter (lifetime is caller's responsibility)
void Process(ref array<int> data) { }

// WRONG: ref on return type
ref array<int> GetData() { }

// WRONG: double ref in instantiation — the `new ref` is the error
ref TIntArray arr = new ref TIntArray;
```

**Redundant but not wrong: `ref` on a local variable.**
```
// Valid but redundant — locals are strong by default per Bohemia wiki
void DoStuff()
{
    ref array<int> local = new array<int>;    // works
    array<int> also_valid = new array<int>;   // also works (preferred, idiomatic)
}
```
Vanilla code uses both forms for locals: `ref InventoryLocation il = new InventoryLocation;` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattachwithswich.c:33`) and `ref set<Object> victims = new set<Object>;` (`P:\scripts\4_world\classes\areadamage\areadamage.c:175`) beside the plain `InventoryLocation il = new InventoryLocation();` (`P:\scripts\3_game\entities\entityai.c:2140`). The plain form is the usual one and shorter; `ref` on a local is legal and changes nothing. (The knowledge pack named `construction.c` as the example file; the 1.30 file on `P:\` has no `InventoryLocation` local.)

**Measured at run time by the knowledge pack's author on a dedicated server, DayZ 1.30.164289** (CLAIM-ENF-REF-FIELD-PROBE-164289, recorded as unverified: neither the probe nor its log was published, and it was not run again. The probe: a class declared in the mission `init.c`, i.e. in the mission module, with a destructor that prints). The class-family statements around it were read from the 164289 source (paths cited inline):

- `ref` works on a plain class with no `Managed` ancestor: a `ref` field kept its object alive until the holder was released, then the destructor ran. You do not need to inherit `Managed` for `ref` to work.
- A field without `ref` is weak for **both** families: once the only strong local was set to `null`, the object was destroyed and the weak field read `NULL` (for a plain class and for a `Managed` one alike). It was cleared, not left dangling.
- Assigning `new` straight into a non-`ref` field does not compile: `Variable 'm_X' is not strong ref (missing 'ref'?) !`, followed by `Can't compile mission init script`.
- Two plain objects holding `ref` to each other were never destroyed after both locals were released: no destructor line was printed for the rest of that run, so the cycle rule below holds.

**In short**: `ref` is required on class member fields that should own their target (otherwise the target dies with its last strong reference and the field reads `NULL`). Never on parameters or return types. On locals it is a matter of style: do not rework existing code only to remove them.

### `autoptr`: scoped strong references

`autoptr` is an alternative to `ref` that, by the knowledge pack's account, destroys the target when the containing scope ends, which suits a local that should clean up after itself. `language_memory.md` describes it from the vanilla sources as the older owning qualifier (`autoptr map<string, int> prg_count = new map<string, int>;`, `P:\scripts\1_core\proto\enscript.c:834`) and recommends `ref` in mod code.

```
void ProcessFile()
{
    autoptr FileSerializer file = new FileSerializer;
    // file survives until end of this function
    // then auto-destroyed
}
```

Never combine `ref` and `autoptr` on the same field; what happens then is undefined.

### The `delete` keyword: avoid it in mod code

The knowledge pack's rule: `delete` is never necessary, because every instance is freed when its reference count reaches zero, and using `delete` on an object that something else still references ends in a segfault.

What `P:\` shows: `delete` is legal and vanilla uses it on script objects it owns, for example `delete GetBleedingManagerServer();` (`P:\scripts\4_world\entities\manbase\playerbase.c:1224`). So the rule is advice for mod code, not a language limit: set the reference to `null` unless you are sure nothing else holds the object, and never `delete` an entity (`language_memory.md` lists the entity delete calls).

```
// WRONG — causes segfault if anything else references obj
delete obj;

// CORRECT — just let it go out of scope or set to null
obj = null;  // drops this reference; the object is freed when the last one goes
```

### Preventing reference cycles

Reference counting cannot free a cycle. If A holds B and B holds A, neither is ever freed.

**The problem:**
```
class Parent
{
    ref Child m_Child;  // strong ref to child
}

class Child
{
    Parent m_Parent;  // If this were ref, circular leak!
}
```

**The solution: break cycles in destructors.**
```
class LFPG_SorterTagView extends ScriptView
{
    void ~LFPG_SorterTagView()
    {
        // Break the cycle: Tag → Controller → OwnerController → ... → Tag
        LFPG_SorterTagController ctrl = LFPG_SorterTagController.Cast(GetController());
        if (ctrl)
        {
            ctrl.m_OwnerController = null;
        }
    }
}
```

**With a Dabs `ObservableCollection`:** when the collection holds `ScriptView` items that point back at the parent controller, clearing the collection is not enough: the views' destructors must break the back reference first.

### Common lifetime traps

**Trap 1: a local instance disappears too early**
```
// WRONG — timer callback: by the time it fires, myHandler is GC'd
void Setup()
{
    MyHandler handler = new MyHandler;
    string cbName = "OnTimer";
    GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(handler.OnTimer, 5000, false);
    // handler goes out of scope → GC'd → CallLater fires on dead object → segfault
}

// CORRECT — store as member field
class MyClass
{
    ref MyHandler m_Handler;

    void Setup()
    {
        m_Handler = new MyHandler;
        string cbName = "OnTimer";
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(m_Handler.OnTimer, 5000, false);
    }
}
```

**Trap 2: `foreach` over the return of a getter**
```
// WRONG — getter returns weak ref, GC collects between iterations
void Test()
{
    foreach (string t: GetMyArray())  // NPE on 2nd element!
    {
    }
}

// CORRECT — assign to local first
void Test()
{
    array<string> arr = GetMyArray();
    int i;
    for (i = 0; i < arr.Count(); i = i + 1)
    {
        string t = arr[i];
    }
}
```

**Trap 3: `map<Widget, T>` crashes at run time** (reported from the LFPG mods; not checkable on `P:\`)
```
// COMPILES but crashes — Widget is not a valid map key in Enforce
ref map<Widget, int> m_WidgetMap;  // crashes

// Use parallel arrays or a wrapper instead
ref array<Widget> m_Widgets;
ref array<int> m_Values;
```

### Allocation in tick callbacks

Never allocate inside a repeated callback:
```
// WRONG — allocates every 5s, fragments heap, crash after hours
void OnTick()
{
    array<EntityAI> devices = new array<EntityAI>;  // BAD
    // ...
}

// CORRECT — allocate once as member, clear each tick
class MyManager
{
    ref array<EntityAI> m_TempDevices;

    void MyManager()
    {
        m_TempDevices = new array<EntityAI>;
    }

    void OnTick()
    {
        m_TempDevices.Clear();
        // reuse m_TempDevices
    }
}
```

### Summary table

| Usage | `ref` | `autoptr` | plain |
|---|---|---|---|
| Class member field | Yes: keeps the target alive | Yes: cleans up with the scope | Weak; the target may be freed |
| Function parameter | Never | Never | Always plain |
| Local variable | Redundant (valid; leave it out by style) | Fine for a scoped lifetime | Strong (preferred) |
| Return type | Never | Never | Always plain |
| `new` expression | Never (`new ref X` is wrong) | Never | `new X` |
