# UI script recipes

Copyable script for the parts every menu needs: binding widget fields by name, the event signatures, locking input and showing the cursor, background blur, alignment flags at runtime, a layout registry, and registering styles, imagesets and defines in `config.cpp`. The checked vanilla reference for the same ground is `skills/_shared/enscript/references/widget_api.md`; the methods of each widget are in `widget-classes.md`.

Some recipes come from a closed source group and map mod and its core library; they are marked as that mod's pattern, not vanilla.

## Binding widget fields by name

A group mod pattern: fill every `Widget` typed member of a class from the layout widget with the same name, instead of a `FindAnyWidget` call per field.

```c
bool MyMod_ConnectWidgets(Class instance, Widget layoutRoot, TStringArray ignored = null, TStringArray renames = null)
{
    typename t = instance.Type();
    for (int i = 0; i < t.GetVariableCount(); i++)
    {
        string varName = t.GetVariableName(i);
        if (!t.GetVariableType(i).IsInherited(Widget))
            continue;
        if (ignored && ignored.Find(varName) != -1)
            continue;
        string widgetName = varName;
        if (renames)
        {
            int idx = renames.Find(varName);
            if (idx != -1)
                widgetName = renames.Get(idx + 1);
        }
        Widget w = layoutRoot.FindAnyWidget(widgetName);
        if (w)
            EnScript.SetClassVar(instance, varName, 0, w);
    }
    return true;
}
```

It uses reflection: `GetVariableCount`, `GetVariableName` and `GetVariableType` on `typename` (`P:\scripts\1_core\proto\enconvert.c:565` to `:567`) and `EnScript.SetClassVar` (`P:\scripts\1_core\proto\enscript.c:211`). `renames` is a flat list of pairs, a member name then the widget name. Because member and widget names must match, pass a rename list to keep the `m_` prefix on your members. Dabs Framework does the same job with `LoadWidgetsAsVariables` (`dabs-mvc-internals.md`).

## Event signatures

All on `ScriptedWidgetEventHandler` (`P:\scripts\1_core\proto\enwidgets.c:656` to `:686`). Each returns `bool`; return true to consume the event.

```c
OnClick(Widget w, int x, int y, int button)
OnDoubleClick(Widget w, int x, int y, int button)
OnMouseEnter(Widget w, int x, int y)                  // three parameters
OnMouseLeave(Widget w, Widget enterW, int x, int y)   // four parameters
OnMouseWheel(Widget w, int x, int y, int wheel)
OnMouseButtonDown(Widget w, int x, int y, int button)
OnMouseButtonUp(Widget w, int x, int y, int button)
OnFocus(Widget w, int x, int y)
OnFocusLost(Widget w, int x, int y)
OnChange(Widget w, int x, int y, bool finished)
OnKeyDown(Widget w, int x, int y, int key)
OnKeyUp(Widget w, int x, int y, int key)
OnKeyPress(Widget w, int x, int y, int key)
OnDrag(Widget w, int x, int y)
OnDragging(Widget w, int x, int y, Widget reciever)
OnDraggingOver(Widget w, int x, int y, Widget reciever)   // :678
OnDrop(Widget w, int x, int y, Widget reciever)
OnDropReceived(Widget w, int x, int y, Widget reciever)
OnResize(Widget w, int x, int y)
OnChildAdd(Widget w, Widget child)
OnChildRemove(Widget w, Widget child)
OnUpdate(Widget w)
OnSelect(Widget w, int x, int y)
OnItemSelected(Widget w, int x, int y, int row, int column, int oldRow, int oldColumn)
OnModalResult(Widget w, int x, int y, int code, int result)
OnController(Widget w, int control, int value)
OnEvent(EventType eventType, Widget target, int parameter0, int parameter1)
```

An `OnMouseLeave` written with three parameters is a different method and is never called. There is no `OnMouseMove`. Vanilla spells the parameter `reciever`. A handler receives nothing until the widget's `SetHandler(this)` (`:172`).

## Input and cursor

```c
GetGame().GetInput().ChangeGameFocus(1);           // stacks: each +1 needs one -1
GetGame().GetUIManager().ShowUICursor(true);
HumanInputController hic = player.GetInputController();
hic.SetDisabled(true);                              // blocks player actions, keeps the UI
```

`ChangeGameFocus(int add, int input_device = -1)` is at `P:\scripts\3_game\tools\input.c:20`, `ShowUICursor(bool visible)` at `P:\scripts\3_game\tools\uimanager.c:244` and `HumanInputController.SetDisabled(bool pState)` at `P:\scripts\3_game\human.c:22`.

ESC: inside a `UIScriptedMenu`, vanilla polls `GetUApi().GetInputByID(UAUIBack).LocalPress()` in `Update` and calls `Close()` (`P:\scripts\5_mission\gui\notemenu.c:130` to `:137`), while the menu's `LockControls` holds game focus, so the input arrives there. Outside a menu, `LocalPress` on `UAUIBack` is reported not to fire while `ChangeGameFocus` is active (not checked in game). There, catch the key in `MissionGameplay.OnKeyPress(int key)` (`P:\scripts\5_mission\mission\missiongameplay.c:742`) and compare with `KeyCode.KC_ESCAPE` (`P:\scripts\1_core\proto\ensystem.c:158`), by name, not by number.

The group mod also blocks input at mission level:

```c
Mission mission = GetGame().GetMission();
mission.AddActiveInputExcludes({"movement", "aiming", "menu"});
// on close
mission.RemoveActiveInputExcludes({"menu", "movement", "aiming"}, true);
mission.RemoveActiveInputRestriction(EInputRestrictors.INVENTORY);
mission.RefreshExcludes();
```

These are declared on `Mission` (`P:\scripts\3_game\gameplay.c:798` to `:802`); `PlayerControlEnable` and `PlayerControlDisable` just above carry `//!deprecated` (`:795` and `:796`). `EInputRestrictors` (`INVENTORY`, `MAP`, `SURRENDER_TRANSITION`) is at `P:\scripts\3_game\constants.c:116` to `:121`. The exclude names are the `<exclude>` groups of `bin/specific.xml`.

`UIManager` calls a menu often needs: `IsCursorVisible()` (`P:\scripts\3_game\tools\uimanager.c:48`), `GetMenu()` (`:59`) and `CloseAll()` (`:78`).

A Dabs `ScriptViewMenu` takes game focus and shows the cursor when it opens, but does not close on ESC (`CanCloseWithEscape()` has no callers) and does not give game focus back when it closes (the `ChangeGameFocus(-1, ...)` calls in its destructor are commented out). Wire ESC yourself and check the input state after closing (`dabs-menus-and-prefabs.md`, "What ScriptViewMenu does").

## Background blur

```c
PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Start();   // in OnShow
PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Stop();    // in OnHide
```

Vanilla `InventoryMenu` does exactly this (`P:\scripts\5_mission\gui\inventorymenu.c:109` and `:146`). The older `PPEffects.SetBlurMenu(float)` (`P:\scripts\3_game\ppeffects.c:220`) still works and DayZ Expansion uses it, but its file opens with "Deprecated; 'PPEManager' used instead" (`:1`) and vanilla calls `PPEffects.Init()` with "DEPRECATED, left in for legacy purposes only" (`P:\scripts\5_mission\mission\missiongameplay.c:122`). Use the requester in new code.

## Alignment flags at runtime

The group mod changes alignment at runtime with raw hex values. They are that mod's values, not vanilla: `enum WidgetFlags` (`P:\scripts\1_core\proto\enwidgets.c:57` to `:85`) declares 26 names with no explicit values and no position alignment flags. Under a naive `1 << index` reading, `0x100000` would land on `DISABLED` and `0x400000` on `CLIPCHILDREN`. Treat these as a recipe that works in that mod, and never mix them with `WidgetFlags` names.

| Group | Values | Clear mask |
|---|---|---|
| Horizontal | left `0x00`, centre `0x140`, right `0x100` | `0x1C0` |
| Vertical | top `0x00`, centre `0xA00`, bottom `0x800` | `0xE00` |
| Both positions | | `0xFC0` |
| Text | left `0x0`, centre `0x100000`, right `0x400000` | `0x500000` |

The mod names the horizontal values `V_*` and the vertical ones `H_*`; the table gives their real meaning.

```c
widget.ClearFlags(0xFC0);
widget.SetFlags(0x140);   // centre horizontally
widget.Update();          // always after a flag change
```

## A layout registry

A group mod pattern for layout paths another mod can replace:

```c
class MyMod_LayoutManager
{
    static ref MyMod_LayoutManager s_Instance;
    protected ref map<string, string> m_Layouts = new map<string, string>();

    static MyMod_LayoutManager Get()
    {
        if (!s_Instance)
            s_Instance = new MyMod_LayoutManager();
        return s_Instance;
    }

    void RegisterLayout(string name, string path) { m_Layouts.Insert(name, path); }
    void OverwriteLayout(string name, string path) { m_Layouts.Set(name, path); }

    Widget CreateLayout(string name, Widget parent = null)
    {
        string path;
        if (!m_Layouts.Find(name, path))
            return null;
        return GetGame().GetWorkspace().CreateWidgets(path, parent);
    }
}
```

Another mod replaces a layout with `OverwriteLayout` from a `modded class` constructor. How the registry fits a larger UI is in `ui-architecture.md`. Vanilla's own registry is the constants of `class WidgetLayoutName` (`vanilla-menus-map.md`).

## Styles, imagesets and defines in config.cpp

Register style and imageset files in your mod's `class defs` inside `CfgMods`, with paths relative to the prefix and no leading slash:

```cpp
class CfgMods
{
    class MyMod
    {
        defines[] = { "MYMOD_FEATURE_FLAG" };
        class defs
        {
            class widgetStyles { files[] = { "MyMod/gui/styles/mymod.styles" }; };
            class imageSets { files[] = { "MyMod/gui/imagesets/mymod_set.imageset" }; };
        };
    };
};
```

- A `.styles` file is XML, unlike a `.layout`; its format is in `styles-format.md`. An unregistered `.styles` file does nothing.
- `/dayz-build-imageset` builds the imageset and its atlas; the `class imageSets` entry is described in `skills/_shared/enscript/references/widget_api.md`, "Imagesets in layouts and script".
- `defines[]` adds preprocessor symbols other mods can test with `#ifdef MYMOD_FEATURE_FLAG`; the naming rules are in `skills/_shared/enscript-style/naming.md`.
- For the Workbench Layout Editor to show the same styles and imagesets, list them in `dayz.gproj` too (`plan-to-implementation.md`).
