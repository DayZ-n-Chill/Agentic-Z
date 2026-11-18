# Expansion MVC patterns: how DayZ Expansion builds its menus

How DayZ Expansion structures a menu: its own MVC classes, the menu lifecycle, observable collections, subviews, dialogs and HUD panels. Read it before writing or changing a menu that extends Expansion, or to copy one of its patterns.

Everything here is a DayZ Expansion fact, not a vanilla fact. Expansion is a third-party mod, so none of it is checked on `P:\`. Every path below is a path inside the DayZ Expansion scripts tree, and every `path:line` is for its `release` branch at commit `8f75d554fda209b257c00deb8f01c181e67c980a`; a newer Expansion build can move the lines. One vanilla fact is cited on `P:\`: the `PPEffects` class Expansion uses for menu blur is marked deprecated in vanilla (section 2).

---

## 1. Class Hierarchy (Expansion Core MVC)

```
Managed
  └─ ExpansionScriptView              // base: layout + controller + update timer
       └─ ExpansionScriptViewMenu     // adds: input lock, blur, UIManager lifecycle
            └─ (concrete menus)       // e.g. ExpansionMarketMenu, ExpansionQuestMenu
ExpansionViewController               // data binding hub (ObservableCollection, PropertyChanged)
ObservableCollection<ref T>           // notifies ViewController on Insert/Remove/Clear
```

Expansion's MVC is its own implementation in `DayZExpansion/Core/` — parallel to Dabs Framework
but not interchangeable. Do not mix Dabs `ScriptView` and `ExpansionScriptView` in the same menu.

---

## 2. ExpansionScriptViewMenu — OnShow/OnHide with blur + ForceDisable loop

**Path:line**: `DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Bases/ExpansionScriptViewMenu.c:43`
**Confidence**: high.

```
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
    if (!g_Game) return;
    super.OnHide();
    PPEffects.SetBlurMenu(0.0);
    DestroyUpdateTimer();
    UnlockControls();
}
```

`LockControls()` iterates active inputs, preserves `UAUIBack`, and calls `ForceDisable` on each.
`CloseMenu()` delegates to `ExpansionUIManager`.

`PPEffects` still works, but vanilla marks the class deprecated in favor of `PPEManager` (`P:\scripts\3_game\ppeffects.c:1`). Vanilla's own menu blur goes through a PPE requester: see `vanilla-menus-map.md`, section 8.

Rules:
- Always call `super.OnShow()` / `super.OnHide()` — base manages blur state and timer.
- Always guard `OnHide()` with `if (!g_Game) return` — called during shutdown.

---

## 3. ExpansionScriptView — Tick update opt-in (CALL_CATEGORY_GUI timer)

**Path:line**: `DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Bases/ExpansionScriptView.c:48`
**Confidence**: high.

```
float GetUpdateTickRate()
{
    return -1;   // -1 = no timer (default)
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

Override `GetUpdateTickRate()` to return a positive float (seconds between ticks) to opt in.
Menu subclasses recreate the timer in `OnShow`/`OnHide`. Example: `ExpansionQuestHud` uses a
1-second tick to poll `GetClientQuestData()`.

---

## 4. ExpansionUIManager — Singleton menu lifecycle

**Path:line**: `DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/ExpansionUIManager.c:101`
**Confidence**: high.

```
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

`CreateSVMenu(viewName)` destroys any existing instance of the same class before creating a new
one — safe to call repeatedly. `CloseAll(includeVanilla)` closes ScriptViewMenus and
UIScriptedMenus separately. The range `MENU_EXPANSION_MENU_START..END` protects vanilla menus.

Open a menu from module code (e.g. after server-side validation):
```
// ExpansionMarketModule.c:4587 — after MoneyCheck() passes:
CreateSVMenu("ExpansionMarketMenu");
// Must be called on the client in MissionGameplay phase; workspace must be valid.
```

Never call `CreateSVMenu` from RPC handler context — workspace may be null mid-RPC.

---

## 5. ObservableCollection + ViewBinding — Declarative two-way binding

**Path:line (controller)**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:3620`
**Path:line (layout root)**: `GUI/layouts/market/expansion_market_menu.layout:12`
**Path:line (widget binding)**: `GUI/layouts/market/expansion_market_menu.layout:77`
**Confidence**: high.

```
class ExpansionMarketMenuController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionMarketMenuCategory> MarketCategories =
        new ObservableCollection<...>(this);
    ref ObservableCollection<ref ExpansionMarketMenuDropdownElement> DropdownElements = ...
    string MarketName;
    string PlayerTotalMoney;
    override void PropertyChanged(string property_name)
```

```
FrameWidgetClass ExpansionMarketMenu {
 scriptclass "ExpansionMarketMenuController"
 ...
      TextWidgetClass market_text {
       scriptclass "ViewBinding"
       Binding_Name "MarketName"
       Two_Way_Binding 1
```

Rules:
- Layout root: `scriptclass` names the controller class.
- Child widgets: `scriptclass "ViewBinding"` + `Binding_Name` must match a controller property exactly.
- Editable/checkbox widgets: `Two_Way_Binding 1` writes back to the controller.
- `ObservableCollection` auto-notifies the controller on `Insert`/`InsertAt`/`Remove`/`Clear`.

---

## 6. Subview composition — each row/element is its own ExpansionScriptView

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuItem.c:13` and `:119-126`
**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuCategory.c:652`
**Confidence**: high.

```
class ExpansionMarketMenuItem: ExpansionScriptView
    return "DayZExpansion/Market/GUI/layouts/market/expansion_market_menu_item_element.layout";

// Category controller (line 652):
ref ObservableCollection<ref ExpansionMarketMenuItem> MarketItems
```

Complex menus are not monoliths. Every item row, category panel, tooltip, dropdown, and dialog
is a separate subview with its own layout, controller, and observable collections.
The parent menu holds `ObservableCollection<ref SubviewType>` and inserts/removes subview
instances as data changes. Of the patterns here, this is the one most worth copying for a complex menu.

---

## 7. Intermediate model filter before touching ObservableCollection

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:436-452` and `:644-663`
**Confidence**: high.

```
if (!m_TraderMarket.ItemExists(currentItem.ClassName) || m_TraderMarket.IsAttachmentBuySell(...))
    continue;
currentItem.m_ShowInMenu = true/false;  // filter in model
TempInsertItem(displayName, currentItem, tempItems);  // accumulate in temp list
...
m_MarketMenuController.MarketCategories.InsertAt(marketCategoryElement, i);  // only at the end
```

Maintain an intermediate model (`m_ShowInMenu` flag, temp lists) before modifying
`ObservableCollection`. The UI receives only pre-filtered, pre-sorted elements.
Avoids partial re-renders mid-collection.

---

## 8. ExpansionDialogBase — Composable dialogs via ObservableCollection

**Path:line**: `DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Dialogs/ExpansionDialogBase.c:118`
**Confidence**: high.

```
class ExpansionDialogBaseController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionDialogContentBase> DialogContents =
        new ObservableCollection<ref ExpansionDialogContentBase>(this);
    ref ObservableCollection<ref ExpansionDialogButtonBase> DialogButtons =
        new ObservableCollection<ref ExpansionDialogButtonBase>(this);
    string DialogTitle;
};
```

Inject content/buttons via `AddContent()` / `AddButton()`. Conditional visibility controlled
by virtuals `HasHeader()`, `HasFooter()`, `HasCloseButton()`. Layout uses
`Binding_Name "DialogContents"` and `"DialogButtons"`.

---

## 9. Client settings UI — reflection via EnScript.GetClassVar with dot-path

**Path:line**: `DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/Serialization/ExpansionSettingSerializationBase.c:53`
**Confidence**: high.

```
protected bool FindClassInstanceAndVariable()
{
    array<string> arr = {};
    m_Variable.Split( ".", arr );
    m_ActualInstance = m_Instance;
    for ( int i = 0; i < arr.Count() - 1; ++i )
    {
        EnScript.GetClassVar( m_ActualInstance, arr[i], 0, m_ActualInstance );
```

Accepts dot-path strings like `"Foo.Bar"` — walks the object graph via `EnScript.GetClassVar`.
`CreateToggle/CreateSlider/CreateEnum` build serialization objects per category. Use for generic
settings panels that bind UI controls to nested config objects without hardcoded field references.

---

## 10. HUD multi-pointer — Expansion vehicle HUD registration

**Path:line**: `DayZExpansion/Vehicles/Scripts/5_Mission/DayZExpansion_Vehicles/GUI/IngameHud.c:13`
**Path:line**: `DayZExpansion/Vehicles/Scripts/5_Mission/DayZExpansion_Vehicles/GUI/expansionboathud.c:39` and `:169`
**Path:line**: `DayZExpansion/Vehicles/GUI/layouts/hud/hud_boats.layout:170`
**Confidence**: high.

`modded class IngameHud` registers additional HUD panels keyed by a vehicle/entity type enum.
Each panel is a self-contained `ExpansionScriptView` subclass. The panel reads synced NetVar state
(`m_IsSync`, `m_HaltPhysics`, `m_IsInvulnerable`) and updates widget visibility in
`Expansion_Update()`. Pattern applies to any HUD overlay driven by server-synced state.

Note: legacy and modern HUD paths coexist under `EXPANSION_VEHICLES_HUD_OLD` compile flag.
Check which path is active in the target build before modifying HUD registration code.

---

## Key rules for Expansion MVC (summary)

1. Never instantiate `ExpansionScriptView` subclasses from RPC context — workspace may be null.
2. Always call `super.OnShow()` / `super.OnHide()` in every Expansion menu subclass.
3. The controller is an active state hub — `PropertyChanged` may cascade updates across multiple
   collections and settings simultaneously.
4. Filter and sort model data into a temp list before any `ObservableCollection` mutation.
5. `CreateSVMenu` is idempotent — safe to re-call; old instance is destroyed automatically.
6. `ObservableCollection` items with back-refs to their controller create circular ref leaks —
   null back-refs in item destructors.
