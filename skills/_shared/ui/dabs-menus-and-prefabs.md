# Dabs menus, prefab layouts and versions

How Dabs Framework's `ScriptViewMenu` puts a view on the vanilla menu stack and what it leaves for you to do, which prefab layouts ship with the framework, and how a mod detects and requires it. Views, bindings and commands are in `dabs-mvc-internals.md`.

Dabs Framework is a third party mod. These facts are checked against its own scripts in the Steam Workshop copy (`addons\Scripts.pbo` and `addons\GUI.pbo`), not vanilla; paths and lines are that copy's. The vanilla calls it wraps are cited where they appear.

## What ScriptViewMenu does

`3_Game\DabsFramework\MVC\ScriptViewMenu.c` is a `ScriptView` that is also a menu on the vanilla `UIManager` stack.

- Constructing it opens it. The field `ref UIScriptViewMenu m_UIScriptViewMenu = new UIScriptViewMenu(this)` wraps the view in a vanilla `UIScriptedMenu` (`P:\scripts\3_game\tools\uiscriptedmenu.c:66`), and when `UseUIManager()` is true the constructor calls `ShowScriptedMenu(m_UIScriptViewMenu, GetMenu())` (`:19` to `:22`; vanilla `ShowScriptedMenu`, `P:\scripts\3_game\tools\uimanager.c:9`).
- It adds the names from `GetInputExcludes()` with `Mission.AddActiveInputExcludes` (`:25`; vanilla `P:\scripts\3_game\gameplay.c:800`) and removes them in the destructor (`:79` to `:81`).
- It calls `ChangeGameFocus(1, INPUT_DEVICE_MOUSE)` when `UseMouse()` is true and `ChangeGameFocus(1, INPUT_DEVICE_KEYBOARD)` when `UseKeyboard()` is true (`:38` to `:44`; vanilla `ChangeGameFocus(int add, int input_device = -1)`, `P:\scripts\3_game\tools\input.c:20`).
- It sets the cursor two GUI frames later with `SetMouseCursorDesiredVisibility` (`:47`; vanilla `P:\scripts\3_game\dayzgame.c:4003`). The source comment says one frame worked and two is the safe value.
- `Close()` queues `_Close` on `CALL_CATEGORY_GUI`, which runs `if (CanClose()) delete this` (`:170` to `:191`). You own the object's memory: keep a reference while it is open.

## What it leaves to you

- Esc does not close a Dabs menu. `CanCloseWithEscape()` exists (`:181` to `:184`) but nothing calls it; the comment above it reads "tbd how i want to handle this". Wire Esc yourself, for example `OnKeyPress` with `KeyCode.KC_ESCAPE` (`P:\scripts\1_core\proto\ensystem.c:158`) calling `Close()`.
- Game focus is not released on close. Both `ChangeGameFocus(-1, ...)` calls in the destructor are commented out (`:68` and `:73`), and `UIScriptViewMenu` overrides `LockControls` and `UnlockControls` with empty bodies (`MVC\UIScriptViewMenu.c:30` to `:36`), where vanilla's do the work (`P:\scripts\3_game\tools\uiscriptedmenu.c:80` and `:104`). Only the cursor comes back. A mod that adds its own `ChangeGameFocus` around a Dabs menu can leave the focus counts unbalanced; check input after the menu closes.
- There is no `OnShow` or `OnHide` on `ScriptView` or `ScriptViewMenu`. The only ones are the vanilla `UIScriptedMenu` overrides inside the internal wrapper (`MVC\UIScriptViewMenu.c:54` to `:66`), which forward to `ScriptViewMenu.OnMenuEnter(parent)` and `OnMenuExit(parent)`. Override those two. Show or hide a plain `ScriptView` with `ScriptedViewBase.Show(bool)` and `IsVisible()`.
- `GetInputRestrictions()` does nothing. The constructor and destructor loop over a fresh empty local array instead of calling it (`:26` to `:35` and `:84` to `:92`).

| Override | Default | Meaning |
|---|---|---|
| `bool UseMouse()` | `true` | Shows the cursor and takes mouse focus |
| `bool UseKeyboard()` | `false` | Takes keyboard focus |
| `bool UseUIManager()` | `true` | Registers with the `UIManager` stack |
| `array<string> GetInputExcludes()` | | Names from `<exclude>` in `bin/specific.xml` |
| `bool HidesParentMenu(UIMenuPanel parent_panel)` | `true` | Hides the menu underneath |
| `bool CanClose()` | | Guard for `Close()` |
| `void OnMenuEnter(UIMenuPanel parent_panel)`, `void OnMenuExit(UIMenuPanel parent_panel)` | | The lifecycle hooks |

Other methods: `Close()` (deferred delete), `EnterChildMenu` taking a `ScriptViewMenu`, a vanilla menu ID or a `UIScriptedMenu`, `ShowDialog(caption, text, id, buttons, default_button, type)`, and the static `ScriptViewMenu.Get(UIScriptedMenu menu)`.

The `UIManager` stack can clash with other mods that manage menus. For a floating window that lives beside gameplay, handle `ChangeGameFocus` and `HumanInputController.SetDisabled` by hand instead.

## Prefab layouts

`addons\GUI.pbo` ships these under `layouts\prefabs\`; from script the path starts with `DabsFramework/GUI/`, for example `DabsFramework/GUI/layouts/prefabs/ButtonPrefab.layout`.

| Layouts | Notes |
|---|---|
| `ButtonPrefab`, `CheckBoxPrefab`, `EditBoxPrefab`, `MultilineEditBoxPrefab`, `TextBoxPrefab` | Single controls |
| `SliderPrefab`, `EditboxSliderPrefab`, `VectorPrefab`, `ColorPickerPrefab` | Value pickers |
| `Dropdown\DropdownPrefab`, `Dropdown\DropdownElementPrefab` | Drop down list |
| `ListBoxPrefab`, `Listbox\ListBoxPrefab`, `Listbox\ListBoxEntryPrefab`, `ListItems\CategorizedListItem` | Lists |
| `GroupPrefab`, `HorizontalSpacerPrefab` | Grouping |
| `MessageBoxPrefab` | Uses a `RichTextWidget` |

The same PBO holds `layouts\sample_mvc.layout`, `layouts\sample_mvc2.layout`, `layouts\tooltip\tooltip_view.layout` and the options menu layouts under `layouts\options\`. Dabs's `SampleMVC.c` shows a function command (`Relay_Command "SwapItemsExecute"` calling `m_Collection.SwapItems(m_Left, m_Right)` and returning true).

Its color option places a marker inside its parent by fraction, a helper worth copying:

```c
static void MyMod_SetWidgetPosRelativeToParent(Widget w, float x, float y)
{
    x = Math.Clamp(x, 0, 1);
    y = Math.Clamp(y, 0, 1);
    float pW, pH, wW, wH;
    w.GetParent().GetScreenSize(pW, pH);
    w.GetScreenSize(wW, wH);
    w.SetPos((pW * x) - (wW / 2), (pH * y) - (wH / 2));
}
```

## Detecting and requiring the framework

- Require the `CfgPatches` classes `DF_Scripts` (which itself requires `DZ_Scripts` and `DF_GUI`) and `DF_GUI`. `DabsFramework` is only the `CfgMods` name, not a patch class.
- Detect it from script with `#ifdef DABSFRAMEWORK_1_51`, defined on the first line of `MVC\ScriptedViewBase.c`. The framework publishes no releases or tags.
- The repository's default branch is `production`; the Workshop build (item 2545327648) tracks `staging`, and the MVC and animator files are the same on both. In the repository the scripts sit under `DabsFramework/Scripts/3_Game/DabsFramework/MVC/`. These two points are from the repository, not the Workshop copy.
