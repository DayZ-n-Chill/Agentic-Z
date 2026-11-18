# Vanilla menus and HUD

Which vanilla class and layout build each menu and the HUD, how to register a menu of your own, the `UIScriptedMenu` rules that bite, how the HUD and the inventory are put together, and how focus works. Use it to find the vanilla menu to copy from and the contract copied code has to keep.

Layout names in the table are relative to `P:\gui\layouts\`.

## Which class builds which menu

| Menu | Class file | Layout |
|---|---|---|
| Main menu | `P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:59` | `new_ui/main_menu.layout`; consoles in `mainmenuconsoles.c:47` and `:49` |
| Esc menu | `P:\scripts\5_mission\gui\ingamemenu.c:38` | `day_z_ingamemenu.layout`; Xbox in `ingamemenuxbox.c:131` and `:133` |
| Inventory | `P:\scripts\5_mission\gui\inventorymenu.c:34`, which creates no widgets: `layoutRoot = m_Inventory.GetMainWidget()` | `inventory_new/<narrow, medium, wide or xbox>/day_z_inventory_new.layout`, through `WidgetLayoutName` |
| Options | `P:\scripts\5_mission\gui\newui\options\optionsmenu.c:42` to `:51` | `new_ui/options/<msstore, xbox, ps or pc>/options_menu.layout` |
| Character creation | `P:\scripts\5_mission\gui\newui\charactercreation\charactercreationmenu.c:82` and `:85` | `new_ui/character_creation/<xbox or pc>/...` |
| Map | `P:\scripts\5_mission\gui\mapmenu.c:51` | `day_z_map.layout` |
| Server browser | `P:\scripts\5_mission\gui\newui\serverbrowsermenu\serverbrowsermenunew.c:32` and `:37` | `new_ui/server_browser/<xbox or pc>/server_browser.layout` |
| Key bindings | `P:\scripts\5_mission\gui\newui\keybindings\keybindingsmenu.c:33` and `:35` | `new_ui/options/<msstore or pc>/keybinding_menu.layout` |
| Gestures (radial) | `P:\scripts\5_mission\gui\gesturesmenu.c:197` | `radial_menu/radial_gestures/day_z_gestures.layout` |
| Radial quickbar | `P:\scripts\5_mission\gui\radialquickbarmenu.c:171` | `radial_menu/radial_quickbar/radial_quickbar_menu.layout` |
| Chat input | `P:\scripts\5_mission\gui\chat\chatinputmenu.c:16` | `day_z_chat_input.layout` |
| Logout | `P:\scripts\5_mission\gui\logoutmenu.c:48` | `day_z_logout_dialog.layout` |
| Respawn dialog | `P:\scripts\5_mission\gui\respawndialogue.c:21` | `day_z_respawn_dialogue.layout` |
| Note | `P:\scripts\5_mission\gui\notemenu.c:90` | `day_z_inventory_note.layout` |
| Book | `P:\scripts\5_mission\gui\bookmenu.c:13` | `day_z_book.layout` |
| Inspect | `P:\scripts\5_mission\gui\inspectmenunew.c:33` | `inventory_new/day_z_inventory_new_inspect.layout` |
| Loading, startup | `P:\scripts\5_mission\gui\loadingmenu.c:13`, `P:\scripts\5_mission\gui\startupmenu.c:13` | `loading.layout`, `startup.layout` |
| Tutorials, credits | `P:\scripts\5_mission\gui\newui\mainmenu\tutorialsmenu.c:51` to `:58`, `P:\scripts\5_mission\gui\newui\credits\creditsmenu.c:33` | `new_ui/tutorials/...`, `new_ui/credits/credits_menu.layout` |
| Script console (diag) | `P:\scripts\5_mission\gui\scriptconsole.c:203` | `script_console/script_console.layout` |
| HUD root, not a menu | `P:\scripts\5_mission\mission\missiongameplay.c:132` | `day_z_hud.layout` |

Platform layouts are picked with `#ifdef PLATFORM_CONSOLE`, or with the full `PLATFORM_MSSTORE`, `PLATFORM_XBOX`, `PLATFORM_PS4`, `PLATFORM_WINDOWS` chain when the widgets are created (`P:\scripts\5_mission\gui\newui\options\optionsmenu.c:41` to `:55`).

## Registering a menu of your own

`MissionBase.CreateScriptedMenu` (`P:\scripts\5_mission\mission\missionbase.c:198`) is one switch from 44 `MENU_*` IDs to classes, and it calls `SetID` once after the switch (`menu.SetID(id)`, `:350`). Mirror it:

```c
modded class MissionGameplay
{
    override UIScriptedMenu CreateScriptedMenu(int id)
    {
        UIScriptedMenu menu = super.CreateScriptedMenu(id);
        if (!menu)
        {
            switch (id)
            {
                case MYMOD_MENU_ID:
                    menu = new MyMod_Menu();
                    break;
            }
            if (menu)
                menu.SetID(id);
        }
        return menu;
    }
}
```

Without `SetID` the menu keeps `MENU_UNKNOWN` (`P:\scripts\3_game\tools\uiscriptedmenu.c:138`), and `FindMenu`, `IsMenuOpen` and `CloseMenu`, which compare `GetID()` along the menu chain (`P:\scripts\3_game\tools\uimanager.c:117` to `:175`), never find it. Vanilla IDs run from `MENU_ANY` = 1 to `MENU_UNDERGROUND_TRIGGER_EDITOR` = 48 (`P:\scripts\3_game\constants.c:176` to `:223`); pick a high number of your own.

## UIScriptedMenu rules that bite

From `P:\scripts\3_game\tools\uiscriptedmenu.c`:

- `Init()` (`:161` to `:166`) creates the widgets and returns the root. The engine destroys them ("widgets will be destroyed automatically by c++ side"), so never `Unlink` `layoutRoot` in a menu; no vanilla menu does.
- `OnShow` and `OnHide` (`:173` to `:192`) lock and unlock controls per input device, set the cursor back to the parent menu's `UseMouse()` choice on unlock, and add and remove the player death handler. Call `super` when you override them.
- Every event override calls `super`. The base passes its events on to active `UIScriptedWindow` instances (`OnClick` at `:238` to `:252` loops over `UIScriptedWindow.GetActiveWindows()`), so skipping `super` breaks scripted windows without a word, such as the mission loader window that `OpenWindow` creates for `GUI_WINDOW_MISSION_LOADER` (`P:\scripts\3_game\tools\uimanager.c:193`).
- `IsHandlingPlayerDeathEvent()` returns true by default, so the menu closes when the player dies (`:603` to `:611`). Override it to return false to stay open.
- `EnterScriptedMenu(id)` from a menu makes that menu the parent (`:11` and `:12`; `OnClick_Options`, `P:\scripts\5_mission\gui\ingamemenu.c:251` to `:254`), and `UIManager.Back()` returns to it (`P:\scripts\3_game\tools\uimanager.c:62` to `:75`).
- On console, `SetWidgetAnimAlpha(w)` with the base `Update()` pulses the selected element (`:155` to `:159` and `:195` to `:228`).

## Opening a menu: per open or once

- Created on every open, for light dialogs: the Esc menu calls `EnterScriptedMenu(MENU_INGAME, ...)` (`P:\scripts\5_mission\mission\missiongameplay.c:1322`), adds the `"menu"` input exclude and the inventory restriction (`:1328` and `:1329`), and `Continue()` removes them and calls `CloseMenu(MENU_INGAME)` (`:1334` to `:1349`).
- Created once and shown again, for heavy menus: `InitInventory()` creates the inventory once with `CreateScriptedMenu(MENU_INVENTORY, null)` (`:217` to `:223`), `ShowInventory()` shows the same instance with `ShowScriptedMenu` (`:1190` to `:1209`), and `HideInventory()` hides it (`:1211` to `:1221`). The widget tree survives between opens.
- A key opens a menu by polling input in the mission's `OnUpdate`: `GetUApi().GetInputByID(UAGear).LocalPress()` shows the inventory (`:510` to `:521`), `UAUIMenu` the pause menu (`:700` to `:706`). The key itself is declared in `inputs.xml` (`skills/_shared/enscript/integrations/input_bindings.md`).
- Input exclude groups vanilla uses there: `"menu"`, `"inventory"`, `"radialmenu"`, `"loopedactions"`, `"map"`.

## The HUD

- The `MissionGameplay` constructor creates `m_Hud = new IngameHud` (`P:\scripts\5_mission\mission\missiongameplay.c:73`). `OnInit()` loads `day_z_hud.layout` (`:132`), hides it (`:134`; it is shown at `:497` only for a living, conscious player), and gives each part its subtree: chat `ChatFrameWidget` (`:136`), action menu `ActionsPanel` (`:138`), HUD `HudPanel` (`:140`), then the voice and chat channel panels (`:143` to `:165`). `OnMissionFinish` deletes the root (`:275`), so HUD widgets a mod parents elsewhere must clean up after themselves.
- `IngameHud.Init` finds about 31 widgets by name and generates about 35 more for badges and notifiers (`P:\scripts\5_mission\gui\ingamehud.c:143` to `:243`). The names and types in `day_z_hud.layout` are an API; on 1.30 the action prompt rows changed from `ImageWidgetClass` to `PanelWidgetClass`, which breaks an `ImageWidget.Cast` of them (`ui-changes-1-30.md`).
- The safe places to add to the HUD: a `modded class IngameHud` overriding `Init(Widget hud_panel_widget)`, calling `super`, then adding widgets inside `HudPanel`; or a `modded class MissionGameplay` overriding `OnInit`, calling `super`, then creating your own layout as a second root, as vanilla does for the HUD debug view (`:175`).
- Showing and hiding HUD groups goes through flags, not loose `Show()` calls. `IngameHudVisibility` (`P:\scripts\5_mission\gui\ingamehudvisibility.c`) maps an `EHudContextFlags` mask (`HUD_DISABLE` 1, `HUD_HIDE` 2, `VEHICLE_DISABLE` 4, `DRIVER` 8, `VEHICLE` 16, `MENU_OPEN` 32, `NO_BADGE` 64, `QUICKBAR_DISABLE` 128, `QUICKBAR_HIDE` 256, `QUICKBAR_GLOBAL` 512, `INVENTORY_OPEN` 1024, `UNCONSCIOUS` 2048; `:15` to `:29`) to lists of elements (`LinkElementsToFlags`, `:69` to `:87`), and `SetContextFlag` refreshes only the affected ones (`:90` to `:102`). The public calls wrap it: `ShowHudUI` sets `MENU_OPEN` (`P:\scripts\5_mission\gui\ingamehud.c:909` to `:912`), `ShowQuickbarUI` `QUICKBAR_DISABLE` (`:891` to `:894`), `ShowHudPlayer` `HUD_HIDE` (`:903` to `:906`). Menus hide the HUD with `ShowHudUI(false)` and `ShowQuickbarUI(false)` (`P:\scripts\5_mission\gui\ingamemenu.c:135` to `:147`). To hide your own HUD in a state, extend `LinkElementsToFlags` in a `modded class IngameHudVisibility`.
- Vehicle HUDs plug in through a `map<string, VehicleHudBase>` (`VehicleTypeCar` to `CarHud`), each loading its layout into `VehicleHUDPanels` (`P:\scripts\5_mission\gui\ingamehud.c:173` to `:189`).
- Overlays outside `IngameHud`, each loaded with `CreateWidgets`: the watermark on `day_z_hud_watermark.layout` (`P:\scripts\5_mission\gui\watermark.c:10`), the debug monitor on `day_z_debug_monitor.layout` (`P:\scripts\5_mission\gui\debugmonitor.c:28`), the player tag on `hud_player_tag.layout`, created on first use (`P:\scripts\5_mission\gui\ingamehud.c:1105`), and chat lines on `day_z_chat_item.layout` (`P:\scripts\5_mission\gui\chat\chatline.c:25`).
- The 1.30 action info panels on the cursor (`P:\scripts\5_mission\gui\actiontargetscursor.c:152` to `:176`) are in `hud-action-info-panels.md`.

## The inventory

- `InventoryMenu` is a thin shell; the work is in `Inventory : LayoutHolder` (`P:\scripts\5_mission\gui\inventorynew\inventory.c:26`), whose constructor creates the item and color managers, the left, right and hands areas, the player preview and the quickbar (`:74` to `:90`).
- `LayoutHolder extends ScriptedWidgetEventHandler` (`P:\scripts\5_mission\gui\inventorynew\layoutholder.c:1`) is the building block: the constructor takes the parent holder, calls the overridable `SetLayoutName()`, then `CreateWidgets(m_LayoutName, null, false)` and `parent.GetMainWidget().AddChild(...)` (`:89` to `:121`); the destructor deletes the root (`:123` to `:127`). `Container extends LayoutHolder` adds `array<ref LayoutHolder> m_Body`, gamepad focus state (`P:\scripts\5_mission\gui\inventorynew\containers\container.c:1` to `:80`) and `Insert(holder, pos)` (`:1197`).
- On 1.30 `SlotsIconBase: LayoutHolder` (`P:\scripts\5_mission\gui\inventorynew\containeditems\slotsiconbase.c:1`) holds the generic slot logic: the state widgets (`m_CursorWidget`, `m_ColWidget`, `m_MountedWidget`, `m_OutOfReachWidget`, `m_ReservedWidget`, `m_SelectedPanel`, `m_EmptySelectedPanel`, `m_MicromanagedPanel`), sizes, item flags and the preview `m_ItemPreview`. `SlotsIcon` (`slotsicon.c:1`) keeps the mouse events. `GenericIconBase: SlotsIconBase` (`genericicon.c:1`) draws the same icons outside the inventory on `new_ui/hud/SimpleIconTemplate.layout`.
- `InventoryMenu.CheckWidth()` picks a width class from the aspect ratio: above 1.75 wide, above 1.5 medium, otherwise narrow (`P:\scripts\5_mission\gui\inventorymenu.c:38` to `:51`). Layout paths are constants in `class WidgetLayoutName` (`P:\scripts\3_game\gui\widgetlayoutname.c:1` to `:51`), with narrow, medium, wide and xbox versions where needed: vanilla's own layout registry. A few paths are still written inline, such as the tooltip layouts loaded into `m_TooltipWidget` (`P:\scripts\5_mission\gui\inventorynew\itemmanager.c:54` to `:58`) and `ammo_icon` (`P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c:1521`).

## Focus and gamepad

- The only focus calls vanilla makes are the globals `SetFocus(Widget)` and `GetFocus()` (`P:\scripts\1_core\proto\enwidgets.c:698` and `:702`), about a hundred times. `SetActiveWindow` (`:695`) and `SetModal` (`:700`) have no vanilla callers; do not design around them.
- Mouse first menus clear or root the focus in `Init`: `SetFocus(null)` (`P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:113`), `SetFocus(layoutRoot)` on PC (`P:\scripts\5_mission\gui\newui\options\optionsmenu.c:98`). Console menus focus the default button (`P:\scripts\5_mission\gui\respawndialogue.c:27`; `UpdateMenuFocus()`, `P:\scripts\5_mission\gui\ingamemenuxbox.c:966`). Menus with an edit box focus it on show (`P:\scripts\5_mission\gui\chat\chatinputmenu.c:58`).
- Hover and focus share one highlight path: `OnMouseEnter`, `OnMouseLeave`, `OnFocus` and `OnFocusLost` all go to `ColorHighlight` or `ColorNormal`, gated by an `IsFocusable(w)` list (`P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:303` to `:378`).
- To follow a change of input device, insert into `GetGame().GetMission().GetOnInputDeviceChanged()` and `GetOnInputPresetChanged()`, and remove the callback in the destructor, as 24 vanilla files do (`P:\scripts\5_mission\gui\mapmenu.c:41` to `:47` and `:162` and `:163`).
- On 1.30 the Xbox icon setters of `ActionTargetsCursor` are `[Obsolete("no replacement")]` (`SetInteractXboxIcon` at `P:\scripts\5_mission\gui\actiontargetscursor.c:1369` to `SetXboxIcon` at `:1377`); `SetControllerIcon(string pWidgetName, string pInputName)` (`:146` to `:150`) writes a rich text glyph for any controller through `InputUtils.GetRichtextButtonIconFromInputAction`.

## Other vanilla habits worth copying

- Menu blur is the PPE requester: `PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Start()` and `.Stop()` in `InventoryMenu.OnShow` and `OnHide` (`P:\scripts\5_mission\gui\inventorymenu.c:109` and `:146`). `PPEffects` opens with "Deprecated; 'PPEManager' used instead" (`P:\scripts\3_game\ppeffects.c:1`).
- Vanilla menus play no click or hover sounds and have no UI sound call to copy; the only menu audio is the main menu music through `SoundParams` and `GetSoundScene().Play2D` (`P:\scripts\5_mission\mission\missionmainmenu.c:202` to `:206`). Click sounds in mods are a mod habit (`menu-script-patterns.md`).
- A button `X` has children `X_panel` (background) and `X_label` (text), found with `w.FindWidget(w.GetName() + "_label")` by the `ButtonSetText` and `ButtonSetColor` helpers (`P:\scripts\5_mission\gui\ingamemenu.c:392` to `:415`). Name your buttons the same way and the helpers work on them.
- A click that destroys the current menu (continue, logout, respawn) is deferred with `GetGame().GetCallQueue(CALL_CATEGORY_GUI).Call(...)` (`P:\scripts\5_mission\gui\ingamemenu.c:215`, `:242`, `:259`). Not always: `OnClick_Options` enters the options menu at once (`:253`).
- `MissionBase.DumpCurrentUILayout()` (`P:\scripts\5_mission\mission\missionbase.c:378` to `:398`) prints every widget of the current menu as `name (TypeName) [invisible]` with totals. Call it from a diag hook when half the UI is missing.
- The `WidgetEventHandler` singleton (`P:\scripts\5_mission\gui\widgeteventhandler.c`) lets any class take widget events without extending `ScriptedWidgetEventHandler`: `RegisterOnClick(w, handler, "FnName")` stores a per event map and calls by function name. `OnDrag` and `OnDrop` are keyed to the dragged widget, `OnDraggingOver` and `OnDropReceived` to the one under the cursor (`:288` to `:367`). Make a widget draggable with `SetFlags(WidgetFlags.DRAGGABLE)` (vanilla wraps it in `ItemManager.SetWidgetDraggable`, `P:\scripts\5_mission\gui\inventorynew\itemmanager.c:693` to `:702`); during a drag use `GetDragWidget()`, `GetWidgetUnderCursor()` and `CancelWidgetDragging()` (`P:\scripts\1_core\proto\enwidgets.c:184` to `:186`).
