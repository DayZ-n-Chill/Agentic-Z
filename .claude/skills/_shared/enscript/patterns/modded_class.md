# Pattern: modded class

`modded class` is the only mechanism for extending vanilla (or another mod's) classes without a separate inheritance chain. There is a single class in the final binary: the vanilla class effectively becomes the base layer. Vanilla itself uses it: `modded class ParticleList` (`P:\scripts\3_game\particles\particlelist.c:5`) and `modded class PluginDiagMenu` (`P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenumodding.c:21`).

## Contents

- [NEVER use `extends` on `modded class`](#-never-use-extends-on-modded-class)
- [Basic Extension](#basic-extension)
- [Mod Stack Ordering](#mod-stack-ordering)
- [Adding Fields Safely](#adding-fields-safely)
- [Adding Actions to an Item](#adding-actions-to-an-item)
- [Constructor and Destructor](#constructor-and-destructor)
- [Rules](#rules)
- [Engine-backed classes you should not mod](#engine-backed-classes-you-should-not-mod)
- [GUI-extending modded classes need `#ifndef NO_GUI` guards](#gui-extending-modded-classes-need-ifndef-no_gui-guards)
- [Extend the vanilla **script** class, not the config parent](#extend-the-vanilla-script-class-not-the-config-parent)

---

## ⚠️ NEVER use `extends` on `modded class`

```c
// WRONG: silent no-op, your override never runs
modded class PlayerBase extends PlayerBase { }

// RIGHT
modded class PlayerBase { }
```

`modded class Foo extends Foo` (or `extends` anything) compiles cleanly and produces no warnings, but the class never participates in the merged stack. This is the **#1 cause** of *"my override isn't running"*. The base class is implicit; do not write it. None of the vanilla `modded class` lines above has an `extends`.

---

## Basic Extension

`PlayerBase.OnScheduledTick(float deltaTime)` is at `P:\scripts\4_world\entities\manbase\playerbase.c:3007`.

```c
// your mod: file: Scripts/4_World/MyMod_PlayerBase.c
modded class PlayerBase
{
    // New fields live directly on PlayerBase
    protected int m_MyMod_Points = 0;

    // Override a method: super.* IS the vanilla/previously-modded implementation
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

Multiple mods can each `modded class PlayerBase`. Each mod's layer sits on top of the mods loaded before it, and each `super.*` call chains to the next layer down. When your mod builds on another mod's modded class, list that mod's `CfgPatches` class in your `requiredAddons[]` so it loads first.

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

Override `SetActions()` and call `AddAction(typename)` after `super.SetActions()`. That is how `ItemBase` adds its own actions (`P:\scripts\4_world\entities\itembase.c:246-253`); `GetActions` only reads the map those calls build (`itembase.c:235`).

```c
modded class MyMod_CustomCanteen
{
    override void SetActions()
    {
        super.SetActions();
        AddAction(ActionMyMod_DrinkContaminate);
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
        // Runs after the constructors of the layers below this one
        // (vanilla and the mods loaded before yours), so their fields are set.
    }

    void ~SomeEntity()
    {
        // Destructor: release ref-counted resources (timers, arrays, etc.)
    }
}
```

---

## Rules

| Rule | Detail |
|---|---|
| Always call `super.*` on overrides | Skip only when deliberately blocking |
| Prefix all field names with your mod tag | Avoids name collisions across mods |
| modded class lives in the matching script module layer | A modded `PlayerBase` (`P:\scripts\4_world\...`) must be in `Scripts/4_World/` |
| Do not declare `class X` and `modded class X` in the same mod | One or the other; never both for the same name |
| modded class cannot change the class's parent | You can only extend, not re-parent |
| Never write `modded class Foo extends ...` | Silent no-op; base class is implicit (see top of file) |

---

## Engine-backed classes you should not mod

Some classes are made and driven by the engine, not by script. Their constructor is `proto private` or their methods are `proto native`, so there is no script body for a modded layer to wrap. Do not `modded class` them; use the script class that owns them.

| Class | What vanilla shows | Use instead |
|---|---|---|
| `Widget` and every widget class (`TextWidget`, `ButtonWidget`, `ImageWidget`, ...) | `class Widget: Managed` with `proto private void Widget()` (`P:\scripts\1_core\proto\enwidgets.c:107-110`); `TextWidget` at :189, `ButtonWidget` at :381 | Call the widget's script API (`SetText`, `SetColor`, `SetPos`) from the menu or HUD that owns it, or attach a `ScriptedWidgetEventHandler` (`enwidgets.c:656`) |
| `UIManager` | The engine's menu manager; its methods are `proto native` (`P:\scripts\3_game\tools\uimanager.c:1-12`) | Mod the concrete menu, or the mission that opens it |
| `UIScriptedMenu` | A script class (`P:\scripts\3_game\tools\uiscriptedmenu.c:66`), but the base of every menu, so a change there reaches all of them and is not a hook for one menu | `modded class InventoryMenu` (`P:\scripts\5_mission\gui\inventorymenu.c:8`) or the one menu you need |

Being rooted at `Managed` is not the test. `Managed` (`P:\scripts\1_core\proto\enscript.c:117`) is the root of most script classes, including `Hud` (`P:\scripts\3_game\gameplay.c:637`), and `IngameHud extends Hud` (`P:\scripts\5_mission\gui\ingamehud.c:1`) is the usual HUD hook.

---

## GUI-extending modded classes need `#ifndef NO_GUI` guards

Server builds define `NO_GUI` and `NO_GUI_INGAME` (`P:\scripts\1_core\defines.c:29` and `:34`, "Present for server builds"), and vanilla wraps its own GUI code in `#ifndef NO_GUI` (for example `P:\scripts\3_game\dayzgame.c:1061`). Any `modded class IngameHud` (`P:\scripts\5_mission\gui\ingamehud.c:1`) or `modded class Chat` (`P:\scripts\5_mission\gui\chat\chat.c:14`) (and similar GUI types) referenced from a server-side compile path can fail with `Unknown type 'IngameHud'`. Wrap GUI-extending modded classes in a preprocessor guard:

```c
#ifndef NO_GUI
modded class IngameHud
{
    override void Update(float timeslice) // P:\scripts\5_mission\gui\ingamehud.c:1141
    {
        super.Update(timeslice);
        // client-only HUD work
    }
}
#endif
```

This applies to any class that exists only in client-side script layers. If you're not sure whether a class is server-aware, search for it under `P:\scripts\`: if it only appears under `5_mission/gui/` it's client-only and needs the guard.

---

## Extend the vanilla **script** class, not the config parent

For mods that add custom barrels, crates, or storage containers, extending `ItemBase` directly drops vanilla behavior (e.g. open/close animation on barrels, paintable-color selection, tent weather tint). Find the vanilla **script class** that matches your config parent and extend that.

```c
// Vanilla "Barrel_ColorBase" lives at
//   P:\scripts\4_world\entities\itembase\barrel_colorbase.c
//: handles open/close action, paintable color, weather effects.

// CORRECT: extend the vanilla script class
class MyMod_FancyBarrel : Barrel_ColorBase
{
    override void EEKilled(Object killer)
    {
        super.EEKilled(killer);
        // your custom death logic
    }
}

// AVOID: drops vanilla barrel behavior
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
