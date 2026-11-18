# Memory management

How reference counting decides an object's lifetime, where `ref` and `autoptr` belong, why `delete` is the wrong tool in mod code, and the lifetime traps that crash a mod after hours. The short reference for the same topic is `../references/language_memory.md`; where the two differ, its `P:\` citations decide.

## Reference counting

Enforce Script frees an object as soon as its last strong reference goes. There is no mark and sweep collector, so the moment is deterministic.

| | `Managed` classes | Plain classes |
|---|---|---|
| Examples | Every entity: `class IEntity: Managed` (`P:\scripts\1_core\proto\enentity.c:164`), `class Object extends IEntity` (`P:\scripts\3_game\entities\object.c:64`) | Classes with no `Managed` ancestor |
| Field without `ref` | Weak | Weak |
| Local variable | Strong | Strong |

An entity's lifetime still belongs to the engine: never hold an entity with `ref`.

Measured once on a DayZ 1.30 dedicated server, with probe classes in the mission `init.c` whose destructors print:

- `ref` works on a plain class. A `ref` field kept its object alive until the holder was released; then the destructor ran.
- A field without `ref` is weak in both families. Once the only strong local was set to `null`, the object was destroyed and the field read `NULL`; it was cleared, not left dangling.
- `new` assigned straight into a field without `ref` does not compile: `Variable 'm_X' is not strong ref (missing 'ref'?) !`, then `Can't compile mission init script`.
- Two plain objects holding `ref` to each other were never destroyed after both locals were released.

## Where `ref` goes

Put `ref` on member fields that own their target:

```c
class MyMod_Manager
{
    ref map<string, ref array<string>> m_Data;

    void MyMod_Manager()
    {
        m_Data = new map<string, ref array<string>>;
    }
}
```

These are errors:

```c
void Process(ref array<int> data) { }        // ref on a parameter
ref array<int> GetData() { }                 // ref on a return type
ref TIntArray arr = new ref TIntArray;       // ref inside new
```

`ref` on a local is legal and changes nothing. Vanilla writes both forms: `ref InventoryLocation il = new InventoryLocation;` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattachwithswich.c:33`), `ref set<Object> victims = new set<Object>;` (`P:\scripts\4_world\classes\areadamage\areadamage.c:175`), and the plain `InventoryLocation il = new InventoryLocation();` (`P:\scripts\3_game\entities\entityai.c:2140`). Prefer the plain form; do not rework old code just to remove it.

| Where | `ref` | `autoptr` | Plain |
|---|---|---|---|
| Member field | Keeps the target alive | Cleans up with the scope | Weak; the target may be freed |
| Parameter | Never | Never | Always |
| Local | Redundant | Fine for a scoped lifetime | Strong, preferred |
| Return type | Never | Never | Always |
| `new` expression | Never | Never | `new X` |

## `autoptr`

Reported, not checked on `P:\`: `autoptr` destroys its target when the enclosing scope ends, which suits a local that should clean up after itself, such as `autoptr FileSerializer file = new FileSerializer;`. `language_memory.md` describes it from vanilla as the older owning qualifier (`autoptr map<string, int> prg_count = new map<string, int>;`, `P:\scripts\1_core\proto\enscript.c:834`) and recommends `ref` in mod code. Never put `ref` and `autoptr` on the same field.

## `delete`

Mod code never needs `delete`: every object is freed when its count reaches zero, and deleting an object something else still holds ends in a segfault. Set the reference to `null` instead. `delete` is legal, and vanilla uses it on script objects it owns (`delete GetBleedingManagerServer();`, `P:\scripts\4_world\entities\manbase\playerbase.c:1224`), so this is advice, not a language limit. Never `delete` an entity; `language_memory.md` lists the calls that remove one.

## Reference cycles

Reference counting cannot free a cycle. If a parent holds `ref Child m_Child`, the child's `m_Parent` must stay plain. When a cycle is unavoidable, break it in a destructor:

```c
void ~MyMod_SorterTagView()
{
    MyMod_SorterTagController ctrl = MyMod_SorterTagController.Cast(GetController());
    if (ctrl)
        ctrl.m_OwnerController = null;
}
```

With a Dabs `ObservableCollection` whose item views point back at the owning controller, clearing the collection is not enough; the item destructors must drop the back reference first (`dabs-mvc-advanced.md`).

## Lifetime traps

A handler held only by a local dies when the method returns, and a `CallLater` on it then fires into a freed object and crashes. Keep it in a `ref` member:

```c
class MyMod_Scheduler
{
    ref MyMod_Handler m_Handler;

    void Setup()
    {
        m_Handler = new MyMod_Handler;
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(m_Handler.OnTimer, 5000, false);
    }
}
```

Reported, cause not checked on `P:\`: a `foreach` written straight over a getter's return value misbehaves. Copy the result to a local (`array<string> arr = GetMyArray();`) and loop over that.

Seen in one third-party mod, cause not isolated: a `ref map<Widget, int>` compiled and then crashed at run time, and parallel `array<Widget>` and `array<int>` fields were used instead. Vanilla does key maps by `Widget` (`runtime-pitfalls.md`), so first check whether the map outlives the widgets it holds.

## Allocation in a tick

Never allocate inside a repeated callback. An array created every few seconds fragments the heap and crashes the server after hours. Allocate once as a member and `Clear()` it each tick:

```c
class MyMod_DeviceManager
{
    ref array<EntityAI> m_TempDevices = new array<EntityAI>;

    void OnTick()
    {
        m_TempDevices.Clear();
    }
}
```
