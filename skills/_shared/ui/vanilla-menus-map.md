# Vanilla menus and HUD: source map and copyable patterns

Which vanilla class and layout build each menu and the HUD, how to register a modded menu, the `UIScriptedMenu` contract, the HUD and inventory architecture, and the focus model. Use it to find which vanilla menu to copy from, and the contracts that make copied code behave.

Added from a sweep of `P:\scripts\5_mission` (220 files), `P:\scripts\3_game\tools\uiscriptedmenu.c`,
`uimanager.c` beside it and `P:\scripts\3_game\gui\widgetlayoutname.c`. Every `path:line` below was re-read on a `P:\`
holding 1.30 (its `day_z_hud.layout` is the 1.30.164014 form); a short `:N` after a path means another line of the same file.
Layout names in the table are relative to `P:\gui\layouts\`.

## 1. Menu → class file → layout table

| Menu | Class file | Layout loaded |
|---|---|---|
| MainMenu | `P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:59` | `new_ui/main_menu.layout` (consoles: `P:\scripts\5_mission\gui\newui\mainmenu\mainmenuconsoles.c:47/49`) |
| InGameMenu (ESC) | `P:\scripts\5_mission\gui\ingamemenu.c:38` | `day_z_ingamemenu.layout` (Xbox: `P:\scripts\5_mission\gui\ingamemenuxbox.c:131/133`) |
| InventoryMenu | `P:\scripts\5_mission\gui\inventorymenu.c:34` — **no CreateWidgets**: `layoutRoot = m_Inventory.GetMainWidget()` | via `WidgetLayoutName` registry: `inventory_new/{narrow\|medium\|wide\|xbox}/day_z_inventory_new.layout` |
| OptionsMenu | `P:\scripts\5_mission\gui\newui\options\optionsmenu.c:42-51` | `new_ui/options/{msstore\|xbox\|ps\|pc}/options_menu.layout` |
| CharacterCreation | `P:\scripts\5_mission\gui\newui\charactercreation\charactercreationmenu.c:82/85` | `new_ui/character_creation/{xbox\|pc}/...` |
| MapMenu | `P:\scripts\5_mission\gui\mapmenu.c:51` | `day_z_map.layout` |
| ServerBrowser | `P:\scripts\5_mission\gui\newui\serverbrowsermenu\serverbrowsermenunew.c:32/37` | `new_ui/server_browser/{xbox\|pc}/server_browser.layout` |
| Keybindings | `P:\scripts\5_mission\gui\newui\keybindings\keybindingsmenu.c:33/35` | `new_ui/options/{msstore\|pc}/keybinding_menu.layout` |
| GesturesMenu (radial) | `P:\scripts\5_mission\gui\gesturesmenu.c:197` | `radial_menu/radial_gestures/day_z_gestures.layout` |
| RadialQuickbar | `P:\scripts\5_mission\gui\radialquickbarmenu.c:171` | `radial_menu/radial_quickbar/radial_quickbar_menu.layout` |
| ChatInput | `P:\scripts\5_mission\gui\chat\chatinputmenu.c:16` | `day_z_chat_input.layout` |
| LogoutMenu | `P:\scripts\5_mission\gui\logoutmenu.c:48` | `day_z_logout_dialog.layout` |
| RespawnDialogue | `P:\scripts\5_mission\gui\respawndialogue.c:21` | `day_z_respawn_dialogue.layout` |
| NoteMenu | `P:\scripts\5_mission\gui\notemenu.c:90` | `day_z_inventory_note.layout` |
| BookMenu | `P:\scripts\5_mission\gui\bookmenu.c:13` | `day_z_book.layout` |
| InspectMenuNew | `P:\scripts\5_mission\gui\inspectmenunew.c:33` | `inventory_new/day_z_inventory_new_inspect.layout` |
| Loading / Startup | `P:\scripts\5_mission\gui\loadingmenu.c:13` / `P:\scripts\5_mission\gui\startupmenu.c:13` | `loading.layout` / `startup.layout` |
| Tutorials / Credits | `P:\scripts\5_mission\gui\newui\mainmenu\tutorialsmenu.c:51-58` / `P:\scripts\5_mission\gui\newui\credits\creditsmenu.c:33` | `new_ui/tutorials/...` / `new_ui/credits/credits_menu.layout` |
| ScriptConsole (diag) | `P:\scripts\5_mission\gui\scriptconsole.c:203` | `script_console/script_console.layout` |
| **HUD root (not a menu)** | `P:\scripts\5_mission\mission\missiongameplay.c:132` | `day_z_hud.layout` |

Platform pattern: `#ifdef PLATFORM_CONSOLE` guards (charactercreation/serverbrowser/tutorials) or the
full `PLATFORM_MSSTORE → PLATFORM_XBOX → PLATFORM_PS4 → PLATFORM_WINDOWS` cascade at CreateWidgets
time (`P:\scripts\5_mission\gui\newui\options\optionsmenu.c:41-55`).

## 2. Registering a modded menu ID (the vanilla-mirroring recipe)

`MissionBase.CreateScriptedMenu` (`P:\scripts\5_mission\mission\missionbase.c:198-354`) is the single factory
switch mapping 44 `MENU_*` ids → classes, with **SetID applied once, after the switch**
(`:348-353: if (menu) { menu.SetID(id); } return menu;`). Copyable modded registration:

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
                case MY_MENU_ID: menu = new MyMenu(); break;
            }
            if (menu) menu.SetID(id);   // vanilla-mirroring: MISSING THIS leaves GetID()==MENU_UNKNOWN
        }
        return menu;
    }
}
```

Skipping `SetID` breaks `FindMenu/IsMenuOpen/CloseMenu`, which walk the menu chain comparing
`GetID()` (`P:\scripts\3_game\tools\uimanager.c:117-175`;
ctor sets `m_id = MENU_UNKNOWN`, `P:\scripts\3_game\tools\uiscriptedmenu.c:138`). Vanilla ids are 1..48, `MENU_ANY` to `MENU_UNDERGROUND_TRIGGER_EDITOR` (`P:\scripts\3_game\constants.c:176-223`); pick an arbitrary high int.

## 3. UIScriptedMenu contract (rules that bite)

From `3_game/tools/uiscriptedmenu.c`:
- **Init()** (:161-166): create widgets, return layout root. "widgets will be destroyed automatically
  by c++ side" — **do not Unlink layoutRoot in a menu** (grep: no vanilla menu ever does).
- **OnShow/OnHide** (:173-192) auto Lock/UnlockControls (per-device ChangeGameFocus + cursor;
  UnlockControls restores the cursor to the parent menu's `UseMouse()` preference) and register/remove
  the player-death invoker. Call `super` when overriding.
- **Critical non-obvious rule: every event override must call `super`** — the base fans its events
  out to active `UIScriptedWindow` instances (`:238-252` OnClick loops
  `UIScriptedWindow.GetActiveWindows()`); skipping super silently breaks scripted windows (e.g. the
  MissionLoader window, `P:\scripts\3_game\tools\uimanager.c:193`).
- **IsHandlingPlayerDeathEvent()** returns true by default → menu force-`Close()`s on death
  (`P:\scripts\3_game\tools\uiscriptedmenu.c:603-611`); override to false to survive.
- Submenus: `EnterScriptedMenu(id)` from the current menu sets it as parent (`P:\scripts\3_game\tools\uiscriptedmenu.c:11-12`;
  `OnClick_Options` at `P:\scripts\5_mission\gui\ingamemenu.c:251-254`); `UIManager.Back()` pops (`P:\scripts\3_game\tools\uimanager.c:62-75`).
- Console-only: `SetWidgetAnimAlpha(w)` + base `Update()` gives the pulsing selected-element
  animation on PLATFORM_CONSOLE (`P:\scripts\3_game\tools\uiscriptedmenu.c:155-159, 195-228`).

## 4. Two instantiation strategies (pick per menu weight)

- **(A) create-per-open** — `EnterScriptedMenu(MENU_X, parentMenu)`; vanilla pause menu:
  `P:\scripts\5_mission\mission\missiongameplay.c:1322` + `AddActiveInputExcludes({"menu"})` + INVENTORY restriction (:1328-1329);
  closed via `Continue()` → RemoveActiveInputExcludes + `CloseMenu(MENU_INGAME)` (:1334-1349).
  For cheap dialogs.
- **(B) create-once + show/hide** — vanilla inventory: `InitInventory()` creates once via
  `CreateScriptedMenu(MENU_INVENTORY, null)` (`P:\scripts\5_mission\mission\missiongameplay.c:217-223`); `ShowInventory()` re-shows the same cached
  instance via `ShowScriptedMenu(m_InventoryMenu, null)` (:1190-1209); `HideInventory()` →
  HideScriptedMenu (:1211-1221). Keeps the Init()-built widget tree alive across opens — copy for
  heavyweight menus (inventory rebuilds a whole container tree in Init).
- Key-open pattern = input polling in Mission OnUpdate: `GetUApi().GetInputByID(UAGear).LocalPress()`
  → ShowInventory (`P:\scripts\5_mission\mission\missiongameplay.c:510-521`); `UAUIMenu` → Pause (:700-706).
- Vanilla input-exclude group names used in missiongameplay.c: `"menu"`, `"inventory"`,
  `"radialmenu"`, `"loopedactions"`, `"map"`.

## 5. HUD ownership chain + extension points

- `MissionGameplay` ctor creates `m_Hud = new IngameHud` (`P:\scripts\5_mission\mission\missiongameplay.c:73`); `OnInit()` loads
  one layout `day_z_hud.layout` (`P:\scripts\5_mission\mission\missiongameplay.c:132`), hides it (:134; shown at :497 only when player exists, is
  alive and conscious), then Inits each subsystem with a named subtree: Chat→`ChatFrameWidget`
  (:136), ActionMenu→`ActionsPanel` (:138), IngameHud→`HudPanel` (:140), mic/voice/chat-channel
  panels (:143-165). `OnMissionFinish` deletes the root (:275) — **modded HUD widgets parented
  elsewhere must self-clean**.
- `IngameHud.Init` resolves ~31 sub-widgets by name (+~35 generated in InitBadgesAndNotifiers)
  (`P:\scripts\5_mission\gui\ingamehud.c:143-243`) — **the widget names and types in day_z_hud.layout are load-bearing API**.
  *(Up to 1.29 the interaction widgets `item`, `interact`, `continuous_interact`, `single`, `continuous` were `ImageWidgetClass` loading textures such as `card_drop.edds` or `linear_gradient.edds`; 1.29 is not on `P:\`, so that half is not checked. On 1.30 they are `PanelWidgetClass`: `P:\gui\layouts\day_z_hud.layout:2294`, `:2477`, `:2755`, `:3033`, `:3249`. The new `ActionWidget` style, `P:\gui\looknfeel\dayzwidgets.styles:3700`, sits on their `GridSpacerWidgetClass` container (`P:\gui\layouts\day_z_hud.layout:2287`), not on the five panels; see `styles-format.md`, section 6.)*
  **Breaking change in 1.30:** a script doing `ImageWidget.Cast(m_Root.FindAnyWidget("interact"))` or `"item"` gets `null` on 1.30, because the widget is no longer an `ImageWidget`, and the next `LoadImageFile` or `SetColor` on it is a null pointer error. Migrate to a plain `Widget` (vanilla scripts declare no `PanelWidget` class).
- Safest modded extension points: (1) `modded class IngameHud` override `Init(Widget hud_panel)` →
  super, then add widgets inside the HudPanel subtree; (2) `modded class MissionGameplay` override
  `OnInit` → super, then `CreateWidgets(your.layout)` as a sibling root — the same pattern vanilla
  uses for HudDebug (`P:\scripts\5_mission\mission\missiongameplay.c:175`).
- **Show/hide HUD groups = flag system, not ad-hoc Show()**: `IngameHudVisibility`
  (`P:\scripts\5_mission\gui\ingamehudvisibility.c`) maps an `EHudContextFlags` bitmask (HUD_DISABLE=1, HUD_HIDE=2,
  VEHICLE_DISABLE=4, DRIVER=8, VEHICLE=16, MENU_OPEN=32, NO_BADGE=64, QUICKBAR_DISABLE=128,
  QUICKBAR_HIDE=256, QUICKBAR_GLOBAL=512, INVENTORY_OPEN=1024, UNCONSCIOUS=2048; :15-29) to element
  lists (`LinkElementsToFlags` :69-87); `SetContextFlag(flag,state)` refreshes only affected elements
  (:90-102). Public API = thin wrappers: `ShowHudUI→MENU_OPEN` (`P:\scripts\5_mission\gui\ingamehud.c:909-912`),
  `ShowQuickbarUI→QUICKBAR_DISABLE` (:891-894), `ShowHudPlayer→HUD_HIDE` (:903-906), etc.
  Menus hide the HUD via `mission.GetHud().ShowHudUI(false)+ShowQuickbarUI(false)`
  (`P:\scripts\5_mission\gui\ingamemenu.c:135-147`). **For "hide my custom HUD when X", extend
  `modded IngameHudVisibility.LinkElementsToFlags`** — do not roll a parallel system.
- Vehicle HUD plug-in: `IngameHud.Init` builds `map<string, VehicleHudBase>`
  (`'VehicleTypeCar'→CarHud`) each loading its own layout into the widget named `VehicleHUDPanels`
  (`P:\scripts\5_mission\gui\ingamehud.c:173-189`).
- Sibling overlays not inside IngameHud (map for extending them): watermark `P:\scripts\5_mission\gui\watermark.c:10`;
  debug monitor `P:\scripts\5_mission\gui\debugmonitor.c:28`; player tag `P:\scripts\5_mission\gui\ingamehud.c:1105`
  (`new_ui/hud/hud_player_tag.layout`, lazy); chat lines `P:\scripts\5_mission\gui\chat\chatline.c:25`.
- **Modular Action Info Panels on Cursor (DayZ 1.30)**: `P:\scripts\5_mission\gui\actiontargetscursor.c:152-176, 1268-1292`
  incorporates modular supplemental info panels (`TargetActionInfoPanelBase`, `ConstructionActionInfoPanel`
  in `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:82`) attached to layout `P:\gui\layouts\new_ui\hud\action_info_spacer.layout:1`, dynamically
  rendering grids of tools and materials required for the action (`P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfogrids.c:103`).
  See full reference in `hud-action-info-panels.md`.

## 6. Inventory architecture (the biggest vanilla UI — patterns to steal)

- `InventoryMenu` is a thin shell; composition lives in `Inventory : LayoutHolder`
  (`P:\scripts\5_mission\gui\inventorynew\inventory.c:26`, ctor :74-90 creates ItemManager/ColorManager singletons +
  LeftArea/RightArea/HandsArea/PlayerPreview + Quickbar).
- **`LayoutHolder extends ScriptedWidgetEventHandler`** (`P:\scripts\5_mission\gui\inventorynew\layoutholder.c:1`) is the reusable building
  block: ctor takes parent holder → overridable `SetLayoutName()` → `CreateWidgets(m_LayoutName,
  null, false)` → `parent.GetMainWidget().AddChild(...)` (:89-121); dtor deletes root (:123-127).
  `Container extends LayoutHolder` adds `array<ref LayoutHolder> m_Body` + focused-container/column
  state for gamepad nav (`P:\scripts\5_mission\gui\inventorynew\containers\container.c:1-80`) + `Insert(holder, pos)` (:1197).
- **Decoupling of `SlotsIconBase` (DayZ 1.30)**:
  *(up to 1.29: `SlotsIcon.c` was the monolithic base class for inventory slots; since 1.30: `P:\scripts\5_mission\gui\inventorynew\containeditems\slotsiconbase.c:1` absorbed 744 lines of generic logic, reducing `P:\scripts\5_mission\gui\inventorynew\containeditems\slotsicon.c:1` to 217 lines dedicated to mouse event registration).*
  `SlotsIconBase` manages state widgets (`m_CursorWidget`, `m_ColWidget`, `m_MountedWidget`,
  `m_OutOfReachWidget`, `m_ReservedWidget`, `m_SelectedPanel`, `m_EmptySelectedPanel`, `m_MicromanagedPanel`),
  dimensions, item flags, and preview rendering (`m_ItemPreview`).
  To render icons outside the inventory menu (on the HUD and construction cursor), 1.30 introduces
  `GenericIconBase: SlotsIconBase` (`P:\scripts\5_mission\gui\inventorynew\containeditems\genericicon.c:1`)
  on top of `new_ui/hud/SimpleIconTemplate.layout`, orchestrated by `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfogrids.c:1`.
- Width classes: `InventoryMenu` ctor computes static ScreenWidthType from aspect ratio (>1.75 WIDE,
  >1.5 MEDIUM, else NARROW; `P:\scripts\5_mission\gui\inventorymenu.c:38-52`); layout paths centralized as consts in
  `class WidgetLayoutName` (`P:\scripts\3_game\gui\widgetlayoutname.c:1-51`) with narrow/medium/wide/xbox
  variants for the components that need them — vanilla's own layout registry
  (const-based and width-class-aware). Not universal: a few paths are
  hardcoded inline (the tooltips, `m_TooltipWidget` at `P:\scripts\5_mission\gui\inventorynew\itemmanager.c:54-58`, and `ammo_icon` at `P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c:1521`).

## 7. Focus & gamepad (corrects earlier hint)

- The only focus API vanilla calls is the global pair `SetFocus(Widget)/GetFocus()`
  (`P:\scripts\1_core\proto\enwidgets.c:698/702`; about a hundred call sites). **`SetActiveWindow` has zero vanilla call sites** (proto
  only, :695; `SetModal` :700 likewise unused) — do not design around it.
- Conventions: mouse-first menus clear or root the focus in Init (`P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:113 SetFocus(null)`;
  optionsmenu sets `SetFocus(layoutRoot)` on PC, `P:\scripts\5_mission\gui\newui\options\optionsmenu.c:98`); console menus focus the default button
  (`SetFocus(m_CustomRespawn)` at `P:\scripts\5_mission\gui\respawndialogue.c:27`; `UpdateMenuFocus()` at `P:\scripts\5_mission\gui\ingamemenuxbox.c:966`); EditBox menus focus the box
  on show (`P:\scripts\5_mission\gui\chat\chatinputmenu.c:58`).
- Hover and focus share one highlight path: OnMouseEnter/OnMouseLeave and OnFocus/OnFocusLost all
  route to ColorHighlight/ColorNormal gated by an `IsFocusable(w)` whitelist (`P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:303-378`).
- Device hot-swap: subscribe `g_Game.GetMission().GetOnInputDeviceChanged().Insert(fn)`
  (+ GetOnInputPresetChanged) — 24 vanilla files do this and **Remove in destructor**
  (`P:\scripts\5_mission\gui\mapmenu.c:41-47,162-163`).
- **Universal gamepad icons vs obsolete Xbox methods (DayZ 1.30)**:
  *(up to 1.29: `ActionTargetsCursor.c` used Xbox-specific methods such as `SetInteractXboxIcon`, `SetContinuousInteractXboxIcon`, `SetSingleXboxIcon`, `SetContinuousXboxIcon`, and `SetXboxIcon`; since 1.30: `P:\scripts\5_mission\gui\actiontargetscursor.c:1368-1377` marks them as `[Obsolete("no replacement")]`).*
  Gamepad support is now cross-platform and unified via `SetControllerIcon(string pWidgetName, string pInputName)`
  (`P:\scripts\5_mission\gui\actiontargetscursor.c:146-150`), which injects dynamic RichText glyphs
  for Xbox, PlayStation, or PC controllers via `InputUtils.GetRichtextButtonIconFromInputAction(pInputName, "", EUAINPUT_DEVICE_CONTROLLER)`.

## 8. Facts that correct or extend the rest of this pack

- **Menu blur (corrective)**: vanilla's current mechanism is the PPE requester system —
  `PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Start()/.Stop()` in
  InventoryMenu.OnShow/OnHide (`REQ_INVENTORYBLUR` at `P:\scripts\5_mission\gui\inventorymenu.c:109/146`).
  `PPEffects` (the `SetBlurMenu` route used elsewhere in this pack) carries an explicit deprecation
  comment, "Deprecated; 'PPEManager' used instead" (`P:\scripts\3_game\ppeffects.c:1`) — it still works (Expansion
  uses it) but new code should prefer the requester.
- **UI sounds (verified negative)**: vanilla menus play no per-click/hover sounds — no UI-sound API
  exists to copy; the only menu audio is main-menu music via `SoundParams` +
  `g_Game.GetSoundScene().Play2D` (`P:\scripts\5_mission\mission\missionmainmenu.c:202-206`). Mod click sounds (SEffectManager pattern) are a mod convention,
  not vanilla parity.
- **Compound-button convention**: a vanilla button named `X` has children `X_panel` (bg) and
  `X_label` (text), accessed generically via `w.FindWidget(w.GetName() + "_label")` —
  ButtonSetText/ButtonSetColor helpers (`P:\scripts\5_mission\gui\ingamemenu.c:392-415`). Follow it and generic helpers work
  on your buttons too.
- **Deferred transitions**: mission-continue/logout/respawn-dialogue transitions from a click are
  deferred via `g_Game.GetCallQueue(CALL_CATEGORY_GUI).Call(...)` (`P:\scripts\5_mission\gui\ingamemenu.c:215/242/259`) —
  common for transitions that destroy the current menu; not an absolute rule (OnClick_Options enters
  the options menu synchronously, :253).
- **Widget-tree dumper for "half my UI is missing"**: `MissionBase.DumpCurrentUILayout()`
  (`P:\scripts\5_mission\mission\missionbase.c:378-398`) recursively Prints every widget of the current menu as
  `name (TypeName) [invisible]` with TOTAL/INVISIBLE/VISIBLE counts — call it from any diag hook
  instead of writing your own walker.
- **WidgetEventHandler singleton** (`gui/widgeteventhandler.c`): lets any class receive widget events
  without subclassing ScriptedWidgetEventHandler — `RegisterOnClick(w, handler, "FnName")` keeps
  per-event `map<Widget, Param2<Managed,string>>` registries and dispatches by function-name string.
  Drag&drop keying (verified): OnDrag/OnDrop dispatch keyed to the source widget; OnDraggingOver/
  OnDropReceived keyed to the receiver under the cursor (`P:\scripts\5_mission\gui\widgeteventhandler.c:288-367`); enable
  dragging via `SetFlags(WidgetFlags.DRAGGABLE)` (vanilla wrapper `ItemManager.SetWidgetDraggable`,
  `P:\scripts\5_mission\gui\inventorynew\itemmanager.c:693-702`); mid-drag globals `GetDragWidget()/GetWidgetUnderCursor()/
  CancelWidgetDragging()` (`P:\scripts\1_core\proto\enwidgets.c:184-186`).
