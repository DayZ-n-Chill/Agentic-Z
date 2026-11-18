# Expansion view classes

How DayZ Expansion builds its menus: its own view and controller classes, the show and hide lifecycle, the update tick, the menu manager, subviews, dialogs, the settings panel and HUD panels. Read it before you change a menu that extends Expansion or copy one of its patterns; a full worked example is `expansion-market-menu.md`.

DayZ Expansion is a third party mod. Every path below is inside the DayZ Expansion scripts (the `release` branch of its source), not vanilla, and none of it is on `P:\`. Line numbers move between releases, so search for the symbol.

## Classes

| Class | Base | Adds |
|---|---|---|
| `ExpansionScriptView` | `Managed` | Layout, controller and the update timer |
| `ExpansionScriptViewMenu` | `ExpansionScriptView` | Input lock, blur and the menu lifecycle; menus such as `ExpansionMarketMenu` and `ExpansionQuestMenu` extend it |
| `ExpansionViewController` | | The binding hub: collections and `PropertyChanged` |
| `ObservableCollection<ref T>` | | Tells the controller about `Insert`, `InsertAt`, `Remove` and `Clear` |

Expansion's MVC lives in `DayZExpansion/Core/`. It looks like Dabs Framework's but is a separate implementation; never mix a Dabs `ScriptView` and an `ExpansionScriptView` in one menu.

## Show and hide

`DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Bases/ExpansionScriptViewMenu.c:43`:

```c
override void OnShow()
{
    super.OnShow();
    LockControls();
    PPEffects.SetBlurMenu(0.5);
    SetFocus(GetLayoutRoot());
    CreateUpdateTimer();
}

override void OnHide()
{
    if (!g_Game)
        return;
    super.OnHide();
    PPEffects.SetBlurMenu(0.0);
    DestroyUpdateTimer();
    UnlockControls();
}
```

`LockControls()` walks the active inputs, keeps `UAUIBack`, and calls `ForceDisable` on the rest. `CloseMenu()` hands off to `ExpansionUIManager`.

- Call `super.OnShow()` and `super.OnHide()` in every subclass; the base owns the blur and the timer.
- Guard `OnHide()` with `if (!g_Game) return;`, because it also runs during shutdown.

`PPEffects` still works, but vanilla marks the class "Deprecated; 'PPEManager' used instead" (`P:\scripts\3_game\ppeffects.c:1`). Vanilla's own menus blur through a PPE requester; see `vanilla-menus-map.md`.

## The update tick

`ExpansionScriptView` runs `Expansion_Update` on a `CALL_CATEGORY_GUI` timer only when asked (`DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Bases/ExpansionScriptView.c:48`):

```c
float GetUpdateTickRate()
{
    return -1; // no timer
}

protected void CreateUpdateTimer()
{
    if (!m_UpdateTimer && GetUpdateTickRate() != -1)
    {
        m_UpdateTimer = new Timer(CALL_CATEGORY_GUI);
        m_UpdateTimer.Run(GetUpdateTickRate(), this, "Expansion_Update", NULL, true);
    }
}
```

Return a positive number of seconds from `GetUpdateTickRate()` to opt in. Menus create the timer in `OnShow` and destroy it in `OnHide`. `ExpansionQuestHud` ticks once a second to poll `GetClientQuestData()`. `CALL_CATEGORY_GUI` is the vanilla queue that "Runs always (on client)" (`P:\scripts\3_game\tools\tools.c:9`).

## The menu manager

`ExpansionUIManager.CreateSVMenu` (`DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/ExpansionUIManager.c:101`):

```c
ExpansionScriptViewMenuBase CreateSVMenu(string viewName)
{
    ExpansionScriptViewMenuBase viewMenu;
    if (m_ActiveMenus.Find(viewName, viewMenu))
    {
        m_ActiveMenus.Remove(viewName);
        viewMenu.Destroy();
    }
    viewMenu = CreateMenuInstance(viewName);
    if (viewMenu)
    {
        SetMenu(viewMenu);
        m_ActiveMenus.Insert(viewName, viewMenu);
        viewMenu.Show();
```

It destroys any open instance of the same name first, so calling it twice is safe. `CloseAll(includeVanilla)` closes Expansion's `ScriptViewMenus` and vanilla `UIScriptedMenu`s separately, and the ID range `MENU_EXPANSION_MENU_START` to `MENU_EXPANSION_MENU_END` keeps Expansion's IDs clear of vanilla's.

Open a menu from module code on the client during gameplay, once the server has said yes: the Market calls `CreateSVMenu("ExpansionMarketMenu")` after `MoneyCheck()` passes (`ExpansionMarketModule.c:4587`). Never create a view or call `CreateSVMenu` from inside an RPC handler, where the workspace can be null.

## Bindings and subviews

The layout root's `scriptclass` names the controller; each child is `scriptclass "ViewBinding"` with a `Binding_Name` that matches a controller property exactly, and `Two_Way_Binding 1` on edit boxes and check boxes. `expansion-market-menu.md`, "Menu, controller and layout", shows the Market's controller and layout.

A complex menu is many small views. Every item row, category panel, tooltip, drop down and dialog is its own `ExpansionScriptView` with its own layout, controller and collections, and the parent holds an `ObservableCollection<ref SubviewType>`:

```c
class ExpansionMarketMenuItem: ExpansionScriptView
{
    override string GetLayoutFile()
    {
        return "DayZExpansion/Market/GUI/layouts/market/expansion_market_menu_item_element.layout";
    }
}

// in the category controller
ref ObservableCollection<ref ExpansionMarketMenuItem> MarketItems;
```

Sources: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuItem.c:13` and `:119` to `:126`; `ExpansionMarketMenuCategory.c:652`. This is the pattern most worth copying for a large menu.

Filter and sort in the model before you touch a collection (`ExpansionMarketMenu.c:436` to `:452` and `:644` to `:663`). The Market skips an item when `!m_TraderMarket.ItemExists(currentItem.ClassName)` or `m_TraderMarket.IsAttachmentBuySell(...)`, sets an `m_ShowInMenu` flag on the rest, gathers the shown items into a temporary list with `TempInsertItem(displayName, currentItem, tempItems)`, and only at the end calls `MarketCategories.InsertAt(...)`. The UI then receives finished, sorted rows and never redraws half a list.

Items that hold a reference back to their controller leak; null the back reference in the item's destructor.

## Dialogs

`ExpansionDialogBase` builds dialogs from two collections (`DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Dialogs/ExpansionDialogBase.c:118`):

```c
class ExpansionDialogBaseController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionDialogContentBase> DialogContents = new ObservableCollection<ref ExpansionDialogContentBase>(this);
    ref ObservableCollection<ref ExpansionDialogButtonBase> DialogButtons = new ObservableCollection<ref ExpansionDialogButtonBase>(this);
    string DialogTitle;
};
```

Add content and buttons with `AddContent()` and `AddButton()`. The virtuals `HasHeader()`, `HasFooter()` and `HasCloseButton()` decide what shows. The layout binds `Binding_Name "DialogContents"` and `"DialogButtons"`.

## A settings panel by reflection

Expansion's client settings bind controls to nested fields by a dotted path (`DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/Serialization/ExpansionSettingSerializationBase.c:53`):

```c
protected bool FindClassInstanceAndVariable()
{
    array<string> arr = {};
    m_Variable.Split(".", arr);
    m_ActualInstance = m_Instance;
    for (int i = 0; i < arr.Count() - 1; ++i)
    {
        EnScript.GetClassVar(m_ActualInstance, arr[i], 0, m_ActualInstance);
```

A path such as `"Foo.Bar"` walks the object graph with `EnScript.GetClassVar`. `CreateToggle`, `CreateSlider` and `CreateEnum` build one entry per setting, so a generic panel binds controls without naming each field in code.

## HUD panels driven by synced state

Expansion's vehicles module registers extra HUD panels from a `modded class IngameHud`, keyed by a vehicle type enum (`DayZExpansion/Vehicles/Scripts/5_Mission/DayZExpansion_Vehicles/GUI/IngameHud.c:13`). Each panel is its own `ExpansionScriptView` that reads synced net variables (`m_IsSync`, `m_HaltPhysics`, `m_IsInvulnerable`) and sets widget visibility in `Expansion_Update()` (`expansionboathud.c:39` and `:169`; layout `DayZExpansion/Vehicles/GUI/layouts/hud/hud_boats.layout:170`). The same shape suits any overlay driven by server state.

An older and a newer HUD path sit side by side behind the `EXPANSION_VEHICLES_HUD_OLD` compile flag; check which one the build uses before you change the registration.
