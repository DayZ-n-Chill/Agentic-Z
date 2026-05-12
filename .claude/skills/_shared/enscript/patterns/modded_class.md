# Pattern: modded class

`modded class` is the only mechanism for extending vanilla (or another mod's) classes without a separate inheritance chain. There is a single class in the final binary — the vanilla class effectively becomes the base layer.

---

## ⚠️ NEVER use `extends` on `modded class`

```c
// WRONG — silent no-op, your override never runs
modded class PlayerBase extends PlayerBase { }

// RIGHT
modded class PlayerBase { }
```

`modded class Foo extends Foo` (or `extends` anything) compiles cleanly and produces no warnings, but the class never participates in the merged stack. This is the **#1 cause** of *"my override isn't running"*. The base class is implicit; do not write it.

---

## Basic Extension

```c
// your mod — file: Scripts/4_World/MyMod_PlayerBase.c
modded class PlayerBase
{
    // New fields live directly on PlayerBase
    protected int m_MyMod_Points = 0;

    // Override a method — super.* IS the vanilla/previously-modded implementation
    override void OnScheduledTick(float deltaTime)
    {
        super.OnScheduledTick(deltaTime); // ALWAYS call super unless deliberately suppressing
        MyMod_PeriodicUpdate(deltaTime);
    }

    void MyMod_PeriodicUpdate(float deltaTime)
    {
        if (!GetGame().IsServer())
            return;
        // your logic
    }
}
```

---

## Mod Stack Ordering

Multiple mods can each `modded class PlayerBase`. The engine stacks them in alphabetical order by PBO name (and within a PBO, alphabetical by file path within the script module). Each `super.*` call chains to the next layer down.

```
[YourMod] OnScheduledTick
    └─ super → [AnotherMod] OnScheduledTick
                   └─ super → [Vanilla] OnScheduledTick
```

> **Warning: Never skip `super.*`** unless you deliberately intend to suppress all lower-layer behaviour. This is the most common source of mod incompatibility.

---

## Adding Fields Safely

```c
modded class ItemBase
{
    // Prefix with your mod name to avoid naming collisions with other mods
    protected int   m_MyMod_UseCount = 0;
    protected bool  m_MyMod_IsSpecial = false;
    protected float m_MyMod_Cooldown = 0.0;
}
```

---

## Adding Actions to an Item

```c
modded class MyMod_CustomCanteen
{
    override void GetActions(typename action_input_type, out array<ActionBase_Basic> actions)
    {
        super.GetActions(action_input_type, actions);

        if (action_input_type == DefaultDamageInput)
            ActionManagerBase.AddAction(ActionMyMod_DrinkContaminate);
    }
}
```

---

## Constructor and Destructor

```c
modded class SomeEntity
{
    void SomeEntity()
    {
        // Constructor runs after ALL modded layers construct
        // (i.e., you can access fields set by other mods)
    }

    void ~SomeEntity()
    {
        // Destructor: release ref-counted resources (timers, arrays, etc.)
        // Called in reverse stack order
    }
}
```

---

## Rules

| Rule | Detail |
|---|---|
| Always call `super.*` on overrides | Skip only when deliberately blocking |
| Prefix all field names with your mod tag | Avoids name collisions across mods |
| modded class lives in the matching script module layer | A modded `PlayerBase` (4_World) must be in `Scripts/4_World/` |
| Do not declare `class X` and `modded class X` in the same mod | One or the other; never both for the same name |
| modded class cannot change the class's parent | You can only extend, not re-parent |
| Never write `modded class Foo extends ...` | Silent no-op; base class is implicit (see top of file) |

---

## Engine classes (Managed-rooted) cannot be modded

Some classes are implemented in engine C++ and exposed to script via `proto native`. They cannot be participated in by `modded class`. Attempting to mod them either fails silently or crashes at compile.

Disqualifying classes — anything **rooted at `Managed`** in the vanilla hierarchy:

- `UIScriptedMenu` and all `Widget` subclasses (`ButtonWidget`, `TextWidget`, `ImageWidget`, etc.)
- `UIManager`
- `GameUI`
- Any class whose vanilla definition starts with `proto native class ... extends Managed`

What works instead:

- For **menus** — `modded class` a concrete menu (e.g. `modded class InventoryMenu`), not the `UIScriptedMenu` base. There is no global menu hook via the base class.
- For **widgets** — manipulate via script API (`SetText`, `SetColor`, `SetPos`) inside the owning menu/HUD class.
- For **HUD** — `modded class IngameHud` (script-side, in `5_Mission/gui/`).

---

## GUI-extending modded classes need `#ifndef NO_GUI` guards

The dedicated server compiles scripts with `NO_GUI` defined and the GUI symbol space stripped. Any `modded class IngameHud` / `modded class Chat` / `modded class UiHintPanel` (and similar GUI base types) referenced from a server-side compile path will crash at compile with `Unknown type 'IngameHud'`. Wrap GUI-extending modded classes in a preprocessor guard:

```c
#ifndef NO_GUI
modded class IngameHud
{
    override void Update(float timeslice)
    {
        super.Update(timeslice);
        // client-only HUD work
    }
}
#endif
```

This applies to any class that exists only in client-side script layers. If you're not sure whether a class is server-aware, search for it under `P:\scripts\` — if it only appears under `5_mission/gui/` it's client-only and needs the guard.

---

## Extend the vanilla **script** class, not the config parent

For mods that add custom barrels, crates, or storage containers, extending `ItemBase` directly drops vanilla behavior (e.g. open/close animation on barrels, paintable-color selection, tent weather tint). Find the vanilla **script class** that matches your config parent and extend that.

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

The script class name often differs from the config class name. Search by config parent: if your `config.cpp` has `class MyBarrel : Barrel_ColorBase`, the script file is `barrel_colorbase.c` somewhere under `P:\scripts\4_world\`.

Also remember to add the vanilla addon to your `requiredAddons[]` if the script class isn't in core:

```cpp
class CfgPatches
{
    class MyMod
    {
        requiredAddons[] = { "DZ_Data", "DZ_Gear_Containers" };
    };
};
```

---

## ⚠️ Member field caveat on engine entity classes

Adding `m_X` member fields to `modded class DayZGame` is safe — `DayZGame` is a script-side singleton with stable lifecycle.

For `modded class PlayerBase` / `modded class ItemBase`, member fields are **mostly** safe, BUT some entity classes have engine-side serialization that can mis-align if many mods add fields and the order shifts. If you see strange crashes at player connect or item spawn that go away when removing a member field, consider an external static map keyed by the entity instead:

```c
// Safer for high-coverage modded fields:
class MyMod_StateMap
{
    static ref map<int, ref MyState> s_StateByEntId = new map<int, ref MyState>;
}
```

This is rare. Default to member fields; only reach for the static-map workaround if you can reproduce a serialization-related crash.
