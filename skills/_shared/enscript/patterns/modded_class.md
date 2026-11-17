# Pattern: modded class

`modded class` is the only mechanism for extending vanilla (or another mod's) classes without a separate inheritance chain. There is a single class in the final binary: the vanilla class effectively becomes the base layer. Vanilla documents it for modders but compiles no `modded class` of its own: `modded class ParticleList` (`P:\scripts\3_game\particles\particlelist.c:5`) sits in a `/* */` block labelled "Example how to register particles from a mod" (`:3-9`), and `modded class PluginDiagMenu` (`P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenumodding.c:21`) is the `#else` branch of an `#ifdef DOXYGEN` (`:18-21`) in a file wrapped in `#ifdef DOXYGEN` (`:8`), so no build compiles it.

## Contents

- [NEVER use `extends` on `modded class`](#-never-use-extends-on-modded-class)
- [Basic Extension](#basic-extension)
- [Mod Stack Ordering](#mod-stack-ordering)
- [Server-only overrides need a stub in the base class](#server-only-overrides-need-a-stub-in-the-base-class)
- [`MissionServer` overrides: call `super`, and spawn where vanilla spawns](#missionserver-overrides-call-super-and-spawn-where-vanilla-spawns)
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

The base class is implicit; do not write it. None of the vanilla `modded class` examples above has an `extends`.

**Reported, not checked on `P:\`** (the compiler is native, and vanilla compiles no `modded class` to read): `modded class Foo extends Foo` (or `extends` anything) compiles cleanly and produces no warnings, but the class never joins the merged stack, so the override never runs. Modders report it as the most common cause of *"my override isn't running"*. Test it in your own mod before you rely on the exact behavior; the rule (no `extends`) holds either way.

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

Reported, not checked on `P:\` (load order is native): the order of the layers follows the `requiredAddons` compile order, not the order of the `-mod=` or `-servermod=` launch string (measured on a 1.30 server). Do not assume your layer is the outermost one. To undo what another mod's layer did, act in an event that runs after it, such as `EEInit()` after the constructor chain.

A `modded class` in the wrong module fails in one of two ways:

- The class is from a lower module than the file. `modded class Transport` written in `4_World` fails with `Unknown type 'Transport'` (reported); `Transport` is a `3_game` class (`P:\scripts\3_game\vehicles\transport.c:68`).
- The class is from a higher module than the file. `modded class MissionServer`, `MissionGameplay` or `Chat` written in `4_World` may compile, depending on parse order, but the override is never bound to the live object, so `OnInit`, `OnMissionStart` and `InvokeOnConnect` never run from your code and nothing is logged (reported). `MissionServer` is declared in `5_mission` (`P:\scripts\5_mission\mission\missionserver.c:5`). Put the file in `Scripts/5_Mission/`.

More on which code goes in which module: `skills/enforce-script-reference/references/script-layers.md`.

---

## Server-only overrides need a stub in the base class

A mod can keep its heavy server logic out of the client by declaring a class with empty methods for both sides and overriding them in a `modded class` wrapped in `#ifdef SERVER`. `SERVER` is defined only on a dedicated server (`P:\scripts\1_core\defines.c:106`), so the client never compiles the second file. The class names below are placeholders; `CF_ModuleWorld` is Community Framework's module base (`../integrations/community_framework.md`).

```c
// Scripts/4_World/MyMod_Module.c: compiled on client and server
class MyMod_Module : CF_ModuleWorld
{
    // Empty stubs the client can call without error
    bool ShouldBlock(ItemBase item) { return false; }
    void Notify(PlayerBase player) {}
}

// Scripts/4_World/MyMod_Module_Server.c: compiled on the server only
#ifdef SERVER
modded class MyMod_Module
{
    override bool ShouldBlock(ItemBase item) { /* validation, file access, RPC */ }
    override void Notify(PlayerBase player) { /* admin messages */ }

    // A new method added only here is the trap
    bool NewServerMethod(ItemBase item) { return true; }
}
#endif
```

**The trap.** A method added only in the server file does not exist on the client. Any code the client compiles that calls it fails with `Undefined function 'MyMod_Module.NewServerMethod'`. The body of an `OnStartServer` override runs on the server, but its file is compiled on both sides, so a call there is enough:

```c
#ifdef SomeOtherMod          // active only where that mod is loaded
modded class ActionX
{
    override void OnStartServer(ActionData action_data)
    {
        MyMod_Module module = MyMod_Module.GetModule();
        if (module.NewServerMethod(null)) { }   // fails to compile on a client that loads this block
    }
}
#endif
```

When the caller sits inside an `#ifdef` for another mod, only clients that have that mod see the error, so the fault can stay hidden for months. This happened in a storage mod where two methods existed only in the server file; it is third-party mod behaviour and no vanilla file shows it.

**Fix.** Add an empty stub to the base class in the same commit as the server method, with the same parameter list and the same parameter names as the server version:

```c
bool NewServerMethod(ItemBase item) { return false; }
```

**Check before a commit.** List the method names declared in the server file, then confirm each one also appears in the base file. Any name found only in the server file is a missing stub. The same check works from the other side: list every `MyMod_Module.` call in the mod and compare it with what the base class declares.

---

## `MissionServer` overrides: call `super`, and spawn where vanilla spawns

Two `MissionServer` methods look like empty hooks and are not. A `modded class MissionServer` override of either one that leaves out `super` breaks the server without an error:

- `OnGameplayDataHandlerLoad` sets `m_RespawnMode`, sets up the debug monitor and calls `InitialiseWorldData()` (`P:\scripts\5_mission\mission\missionserver.c:161-167`). Without `super`, world data is never initialised.
- `OnClientPrepareEvent` decides `useDB` from `GetHive()` (`P:\scripts\5_mission\mission\missionserver.c:449-463`). Without `super`, characters stop loading.

`OnGameplayDataHandlerLoad` is also too early to spawn items that the Central Economy must know. It runs from `CfgGameplayHandler.LoadData()`, which `MissionServer.OnInit` calls (`P:\scripts\5_mission\mission\missionserver.c:88`). Vanilla's own Central Economy dependent spawn is later, in `GlobalsInit()`, which opens with `if (GetCEApi())` and carries the comment about objects that depend on the CE being initialized (`P:\scripts\3_game\dayzgame.c:1160`, `:1173-1174`); `GlobalsInit` is queued as a separate call (`P:\scripts\3_game\dayzgame.c:1096`). The rule is not "always spawn late": vanilla spawns the underground trigger carriers in `OnInit` with `UndergroundAreaLoader.SpawnAllTriggerCarriers()` (`P:\scripts\5_mission\mission\missionserver.c:91`), because they do not touch the CE. Spawn where vanilla spawns the kind of object you create; items with a CE lifetime go through the object spawner route (`../integrations/central_economy.md`).

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

### Reported: many added fields on entity classes

Reported, not checked on `P:\` (it is about engine behaviour, and no vanilla file shows it):

- Member fields added to `modded class DayZGame` are safe: it is one script-side object with a stable lifetime.
- Member fields added to `modded class PlayerBase` or `modded class ItemBase` are safe in almost every mod. The report is that some entity classes can go wrong on the engine side when many mods add fields and their order shifts, and that the sign is a strange crash at player connect or item spawn that goes away when one added field is removed.
- Default to member fields. Only when you can reproduce such a crash, keep the state outside the entity in a static map keyed by an id of the entity:

```c
// Fallback only for a reproduced crash: state kept outside the entity
class MyMod_StateMap
{
    static ref map<int, ref MyMod_State> s_StateByEntId = new map<int, ref MyMod_State>;
}
```

Remove the entry when the entity is deleted, or the map keeps the state object alive (`ref` element type, `../references/language_memory.md` rule 2). What is checked is the save stream: fields you write in `OnStoreSave` on a modded vanilla class must be read back in the same order, and that is covered in `../../persistence/versioning-and-migration.md` ("Adding saved fields to a vanilla class").

---

## Adding Actions to an Item

Override `SetActions()` and call `AddAction(typename)` after `super.SetActions()`. That is how `ItemBase` adds its own actions (`P:\scripts\4_world\entities\itembase.c:246-253`); `GetActions` only reads the map those calls build (`itembase.c:235`). To add an action to a vanilla item, mod its class (`Canteen` at `P:\scripts\4_world\entities\itembase\edible_base\bottle_base\canteen.c:1`, whose parent `Bottle_Base` overrides `SetActions` at `bottle_base.c:356`). For an item class your mod declares, override `SetActions` in its own declaration instead.

```c
modded class Canteen
{
    override void SetActions()
    {
        super.SetActions();
        AddAction(ActionMyMod_DrinkContaminate);
    }
}
```

A new action class must also be registered once:

```c
modded class ActionConstructor
{
    override void RegisterActions(TTypenameArray actions)
    {
        super.RegisterActions(actions);
        actions.Insert(ActionMyMod_DrinkContaminate);
    }
}
```

`RegisterActions` is at `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27`. Without it `AddAction` logs `Action ... dosn't exist!` and returns (`itembase.c:261`). See `actions.md`.

---

## Constructor and Destructor

```c
modded class SomeEntity
{
    void SomeEntity()
    {
        // Your layer's constructor: set up your own fields here.
    }

    void ~SomeEntity()
    {
        // Destructor: release ref-counted resources (timers, arrays, etc.)
    }
}
```

**Reported, not checked on `P:\`** (constructor chaining is native): each layer's constructor runs after the constructors of the layers below it (vanilla and the mods loaded before yours), so their fields are already set when yours runs. Do not depend on another mod's constructor having run; test the order in your own mod if you need it.

---

## Rules

| Rule | Detail |
|---|---|
| Always call `super.*` on overrides | Skip only when deliberately blocking |
| Prefix all field names with your mod tag | Avoids name collisions across mods |
| modded class lives in the matching script module layer | A modded `PlayerBase` (`P:\scripts\4_world\...`) must be in `Scripts/4_World/` |
| For a class your mod declares, put its members in the declaration | `modded class` is for classes you do not own. Vanilla's DiagMenu example (documentation only, see top of file) layers `modded class PluginDiagMenu` (`plugindiagmenumodding.c:21`) on a class declared in another file of the same module (`P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenu.c:29`), so vanilla does not rule the split out. For your own class, though, splitting it over `class X` and `modded class X` leaves one class in two places and makes the result depend on file load order |
| modded class cannot change the class's parent | You can only extend, not re-parent |
| Never write `modded class Foo extends ...` | Base class is implicit; reported to be a silent no-op (see top of file) |

---

## Engine-backed classes you should not mod

Some classes are made and driven by the engine, not by script. Their constructor is `proto private`, or their real work is `proto native`, so a modded layer either cannot be built or reaches every caller at once. Do not `modded class` them; use the script class that owns them.

| Class | What vanilla shows | Use instead |
|---|---|---|
| `Widget` and every widget class (`TextWidget`, `ButtonWidget`, `ImageWidget`, ...) | `class Widget: Managed` with `proto private void Widget()` (`P:\scripts\1_core\proto\enwidgets.c:107-110`); `TextWidget` at :189, `ButtonWidget` at :381 | Call the widget's script API (`SetText`, `SetColor`, `SetPos`) from the menu or HUD that owns it, or attach a `ScriptedWidgetEventHandler` (`enwidgets.c:656`) |
| `UIManager` | The engine's menu manager. Its menu calls are `proto native` (`EnterScriptedMenu`, `CreateScriptedMenu`, `ShowScriptedMenu`, `HideScriptedMenu` at `P:\scripts\3_game\tools\uimanager.c:4-10`, `GetMenu` at :59). Its script helpers (`Back` :62, `CloseMenu` :117, `IsMenuOpen` :154) have bodies, but every menu goes through them, so a modded layer changes all menus at once. | Mod the concrete menu, or the mission that opens it |
| `UIScriptedMenu` | A script class (`P:\scripts\3_game\tools\uiscriptedmenu.c:66`), but the base of every menu, so a change there reaches all of them and is not a hook for one menu | `modded class InventoryMenu` (`P:\scripts\5_mission\gui\inventorymenu.c:8`) or the one menu you need |

Being rooted at `Managed` is not the test. `Managed` (`P:\scripts\1_core\proto\enscript.c:117`) is the root of most script classes, including `Hud` (`P:\scripts\3_game\gameplay.c:637`), and `IngameHud extends Hud` (`P:\scripts\5_mission\gui\ingamehud.c:1`) is the usual HUD hook.

---

## GUI-extending modded classes need `#ifndef NO_GUI` guards

Server builds define `NO_GUI` and `NO_GUI_INGAME` (`P:\scripts\1_core\defines.c:29` and `:34`, "Present for server builds"). The HUD classes still compile there: `IngameHud` (`P:\scripts\5_mission\gui\ingamehud.c:1`) and `Chat` (`P:\scripts\5_mission\gui\chat\chat.c:14`) are declared with no guard. But their GUI calls do nothing useful on a server, so vanilla wraps GUI work in `#ifndef NO_GUI` (`P:\scripts\3_game\dayzgame.c:1061`, `P:\scripts\5_mission\mission\missionserver.c:59`). Do the same for a modded `IngameHud` or `Chat`:

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

To decide whether another class needs the guard, check whether vanilla itself guards the class or its callers with `NO_GUI` (search `P:\scripts\` for `NO_GUI` near its uses).

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

`requiredAddons[]` is about the config parent, not the script class. Every vanilla script class ships in the scripts module, but your `config.cpp` class inherits a config class from a vanilla addon, so list the `CfgPatches` class that defines that parent. `Barrel_ColorBase`'s config class is in `DZ_Gear_Containers` (`P:\DZ\gear\containers\config.cpp:3`, the class at `:19`), so a barrel mod needs:

```cpp
class CfgPatches
{
    class MyMod
    {
        requiredAddons[] = { "DZ_Data", "DZ_Gear_Containers" };
    };
};
```
