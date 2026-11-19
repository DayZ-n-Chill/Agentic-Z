# HUD overlays

How a HUD element added by a mod decides when to show, how the player moves it, how its colors and positions are saved per server, and how it reacts to a resolution change. The vanilla HUD chain is in `vanilla-menus-map.md`.

The patterns come from a large production group and map mod; `My*` names are its helper classes and are not vanilla. The vanilla calls are cited.

## When to show

Every element (compass, GPS, player list, chat) runs the same test each update: a HUD exists, the HUD isn't hidden, the server allows the feature, the player is alive, and no menu is open.

```c
void UpdateHud(float timeslice)
{
    IngameHud hud = IngameHud.Cast(GetGame().GetMission().GetHud());
    if (!hud)
    {
        Show(false);
        return;
    }
    bool visible = hud.MyIsHudVisible() && featureEnabled && MyPlayerUtils.IsClientPlayerAlive() && !GetGame().GetUIManager().GetMenu();
    Show(visible);
    if (visible)
        Update();
}
```

The HUD visibility check, across game versions:

```c
modded class IngameHud
{
    bool MyIsHudVisible()
    {
    #ifdef DAYZ_1_26
        return IsHudVisible();
    #else
        return !GetHudVisibility().IsContextFlagActive(IngameHudVisibility.HUD_HIDE_FLAGS);
    #endif
    }
}
```

On current builds `HUD_HIDE_FLAGS` is `HUD_DISABLE`, `HUD_HIDE`, `MENU_OPEN` and `UNCONSCIOUS` together (`P:\scripts\5_mission\gui\ingamehudvisibility.c:43`), and `IsContextFlagActive` is at `:120`; `IngameHud.GetHudVisibility()` returns that object (`P:\scripts\5_mission\gui\ingamehud.c:876`). Never call `IsHudVisible()` on 1.30: it sits under the `//DEPRECATED` block and always returns false (`ingamehud.c:1303` and `:1313`), so an element gated on it never shows. The same block stubs `IsQuickbarVisible()` and `GetHudState()`.

## Positions the player can change

Each element has a saved position and one of nine alignment anchors:

```c
typedef Param3<string, ref vector, int> MyWidgetPosition; // name, position, alignment

vector pos = positionManager.GetPosition("Minimap", Vector(0.97, 0.83, 0), 8);
int alignIndex = positionManager.GetIndex("Minimap");
MyWidgetUtils.SetWidgetAlignmentIndex(widget, alignIndex);
MyWidgetUtils.SetWidgetPositionIndex(widget, pos, alignIndex);
```

Index 0 is top left, 2 top right, 6 bottom left and 8 bottom right. The position is a fraction from 0 to 1, measured from that anchor.

## Settings saved per server

Colors, positions and visibility are saved as JSON in the profile folder, one file per server. Each manager reads with a default and adds the default when the key is missing:

```c
class MyColorManager_ : MyConfigBase
{
    ref array<ref Param2<string, int>> colors = new array<ref Param2<string, int>>();

    int GetColor(string colorStr, int defaultColor)
    {
        foreach (Param2<string, int> color : colors)
        {
            if (color && color.param1 == colorStr)
                return color.param2;
        }
        colors.Insert(new Param2<string, int>(colorStr, defaultColor));
        return defaultColor;
    }

    void SetColor(string colorStr, int colorARGB)
    {
        foreach (Param2<string, int> color : colors)
        {
            if (color && color.param1 == colorStr)
            {
                color.param2 = colorARGB;
                return;
            }
        }
        colors.Insert(new Param2<string, int>(colorStr, colorARGB));
    }
}
```

The position manager works the same way with `Param3<string, vector, int>` (name, position, alignment), loads from JSON and saves when the settings close.

For a simple mod, a flat settings class is enough: call `MakeDirectory("$profile:MyMod")` (`P:\scripts\1_core\proto\ensystem.c:525`) so the first save works on a clean profile, then `JsonFileLoader<T>.SaveFile("$profile:MyMod/client_settings.json", ...)` (`P:\scripts\3_game\tools\jsonfileloader.c:42`). Treat a missing, unreadable or out of range value as "use the default", not as an error.

## When the resolution changes

Fire an event when the screen size changes and let each element resize itself:

```c
static ref ScriptInvoker Event_OnScreenSizeChanged = new ScriptInvoker();

MyWidgetUtils.Event_OnScreenSizeChanged.Insert(OnSizeChange);

void OnSizeChange()
{
    float width = 300 * MyWidgetUtils.widthScale;
    float height = 300 * MyWidgetUtils.widthScale;
    layoutRoot.SetSize(width, height);
    UpdatePosition();
}
```

Vanilla `MissionGameplay` already handles `WindowsResizeEventTypeID`: it calls `DestroyAllMenus()`, which closes every open menu, dialog and the inventory, then `m_Hud.OnResizeScreen()` (`P:\scripts\5_mission\mission\missiongameplay.c:788` to `:792`; `DestroyAllMenus` at `:1158`). A menu open during a resize is gone afterwards, so keep its state outside the menu object. `IngameHud.OnResizeScreen()` (`P:\scripts\5_mission\gui\ingamehud.c:340`) only updates the HUD panel, badges and notifiers; a `modded class IngameHud` that overrides it and calls `super` is the place to fire the event. Scaling from the height rather than the width keeps squares square; see `screen-scaling.md`.
