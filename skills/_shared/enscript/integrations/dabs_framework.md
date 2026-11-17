# Dabs Framework Integration

What Dabs Framework adds for UI and registration: attribute classes, the MVC layer (`ScriptView`, `ViewController`, `ViewBinding`, `RelayCommand`, observable collections) and `ScriptViewMenu`.

Dabs Framework is a third party mod, not part of the game. Everything below is a **framework** fact, not a vanilla fact. Use it only when the mod already depends on Dabs Framework or the user asks for it; plain vanilla UI is in `../references/widget_api.md`.

**Where to check these facts.** The Steam Workshop copy of the mod (for example linked as `P:\Mods\@Dabs Framework\` by `/dayz-workdrive`); its `addons\Scripts.pbo` holds plain script, and file paths below are paths inside that PBO (for example `3_Game\DabsFramework\MVC\ScriptView.c`). Usage examples were checked against the DayZ Editor mod (`P:\Mods\@DayZ-Editor\`), which is built on Dabs. The framework changes between releases, so open the named file again when something here does not match. In the framework's public source tree the same MVC files sit at `DabsFramework/Scripts/3_Game/DabsFramework/MVC/` on the `production` branch, not at `DabsFramework/scripts/3_Game/MVC/` on `master` (read on 2026-05-13, not checked on `P:\`).

---

## Contents

- [Depending on it](#depending-on-it)
- [Attributes](#attributes)
- [MVC: ScriptView and ViewController](#mvc-scriptview-and-viewcontroller)
- [ScriptViewMenu](#scriptviewmenu)
- [Traps](#traps)

## Depending on it

- `CfgPatches` class: `DF_Scripts`, which itself requires `DZ_Scripts` and `DF_GUI`. Add `"DF_Scripts"` to your `requiredAddons[]`.
- Players and the server must load `@Dabs Framework` before your mod.
- The framework's files live under the prefix `DabsFramework/`, for example `DabsFramework/GUI/layouts/sample_mvc.layout`.

---

## Attributes

An Enforce Script attribute is a class name in square brackets written on the line above a declaration, such as `[RegisterLogger(EditorLog)]`. The attribute class's constructor runs when the script module loads, with the bracket arguments. That is how Dabs registers things without a modded vanilla class in your mod.

| Attribute class (file) | Arguments | What Dabs does with it |
|---|---|---|
| `RegisterAction` (`1_Core\DabsFramework\Managed\Classes\RegisterAction.c`) | `typename action_type` | Dabs's `modded class ActionConstructor` (`4_World\...\ActionConstructor.c`) adds every registered type in `RegisterActions`. |
| `RegisterPluginAttribute` (`1_Core\...\RegisterPlugin.c`) | `typename plugin, bool client, bool server, PluginType type = PluginType.STABLE` | Dabs's `modded class PluginManager` (`4_World\...\PluginManager.c`) calls vanilla `RegisterPlugin`, `RegisterPluginDiag` or `RegisterPluginDebug` before `super.Init()`. This is a game `PluginBase` plugin, not a Workbench menu plugin. |
| `RegisterProfileSetting` (`1_Core\...\RegisterProfileSetting.c`) | `typename type, string display_name = ""` | Adds a `ProfileSettings` subclass to the game's options menu. |
| `RegisterProfileSettingMultistate`, `RegisterProfileSettingSlider`, `RegisterProfileSettingColor`, `RegisterProfileSettingText` (`3_Game\DabsFramework\Settings\Classes\`) | Category, field name, display name, then type specific values (the slider takes `min, max`) | Adds one option for a field of the `ProfileSettings` class above it. |
| `RegisterLogger`, `RegisterMissionSetting`, `RegisterDiagMenu`, `RegisterEditorObject` | See their files in `1_Core\...\Classes\` | Loggers, mission JSON settings, diag menu entries, Editor objects. |

What `RegisterAction` does and does not do: it replaces only the step of modding `ActionConstructor.RegisterActions`. An item still adds the action in its own `SetActions()` with `AddAction(...)`, as in vanilla. It does not bind an action to one item type.

Settings, as the DayZ Editor declares them (`3_Game\DayZEditor\EditorSettings.c`):

```c
[RegisterProfileSetting(MyMod_Settings, "MY MOD")]
class MyMod_Settings: ProfileSettings
{
	[RegisterProfileSettingMultistate("GENERAL", "ShowWelcome", "Show Welcome Message", {"NO", "YES"})]
	int ShowWelcome = 1;   // multistate fields are int: the index into the option list

	[RegisterProfileSettingSlider("GENERAL", "HudScale", "HUD Scale", 0.5, 2)]
	float HudScale = 1;
}
```

Not seen in a shipped mod on this machine: the exact bracket name for `RegisterPluginAttribute` and a `[RegisterAction(...)]` call. Read the class in the PBO and test in game before relying on either.

---

## MVC: ScriptView and ViewController

Dabs MVC loads a `.layout`, assigns widgets to fields by name, and keeps widgets and controller fields in sync. The pieces, all in `3_Game\DabsFramework\MVC\`:

| Class | Role |
|---|---|
| `ScriptView` (`ScriptView.c`) | Loads the layout. Override `GetLayoutFile()` and `GetControllerType()`. |
| `ScriptViewTemplate<T>` | A `ScriptView` whose controller type is `T`; `GetTemplateController()` returns it typed. |
| `ViewController` (`ViewController.c`) | Holds the data. Its fields are what bindings point at. |
| `ViewBinding` (`ViewBinding.c`) | Script class set on a widget in the layout; links one widget to one controller field. |
| `RelayCommand` (`Inputs\RelayCommand.c`) | A command object run by a button or check box. |
| `ObservableCollection<T>` (`Observables\ObservableCollection.c`) | A list field that adds and removes child widgets as it changes. |

### What the ScriptView constructor does

From `ScriptView.c`:

1. Calls `GetGame().GetWorkspace().CreateWidgets(GetLayoutFile(), parent)`. On a dedicated server it logs `Attempted to create layout on SERVER!` and stops, so only create views on the client.
2. Assigns every `Widget` typed field on the view whose name matches a widget name (`LoadWidgetsAsVariables`, which uses `FindAnyWidget`). A field `TextWidget Title;` gets the widget named `Title`.
3. Takes the controller from the layout root's `scriptclass`, or creates `GetControllerType()` when the root has none, and fills that controller's widget fields the same way.
4. Adds `Update(float dt)` to the system update queue unless `UseUpdateLoop()` returns false.

Destroy a view with `delete view;`. The destructor removes the update, deletes the controller and unlinks the layout. Inside the view, call `Delete()`, which deletes on the next GUI frame.

```c
class MyMod_StatusController: ViewController
{
	string StatusText = "Ready";   // bound by Binding_Name "StatusText"
	int Count;                     // bound by Binding_Name "Count"
}

class MyMod_StatusView: ScriptViewTemplate<MyMod_StatusController>
{
	override string GetLayoutFile()
	{
		return "MyMod/gui/layouts/status.layout";   // starts with the mod's $PBOPREFIX$
	}

	override bool UseUpdateLoop()
	{
		return false;   // no per frame work in this view
	}

	void SetCount(int count)
	{
		GetTemplateController().Count = count;
		GetTemplateController().NotifyPropertyChanged("Count");
	}
}
```

### Bindings live in the layout

A binding is not an XML attribute. It is `scriptclass "ViewBinding"` on the widget plus a `ScriptParamsClass` block, as in Dabs's own `layouts\sample_mvc2.layout` and `layouts\prefabs\ButtonPrefab.layout` (in `addons\GUI.pbo`):

```
TextWidgetClass StatusText {
 scriptclass "ViewBinding"
 {
  ScriptParamsClass {
   Binding_Name "StatusText"
  }
 }
}
ButtonWidgetClass BtnRefresh {
 scriptclass "ViewBinding"
 {
  ScriptParamsClass {
   Relay_Command "OnRefreshExecute"
  }
 }
}
```

When the bound widget also has child widgets, the `ScriptParamsClass` goes in a second block of its own, after the block that holds the children; it is never mixed in with them. In a count over the layouts of shipped third party mods, all 157 `ScriptParamsClass` blocks sat alone like this, and the block holds its fields directly, with no inner braces (a count over third party layouts, not checked on `P:\`; the layout side is in `skills/dayz-ui-development/references/layout-format.md`).

`ViewBinding` fields you can set there:

| Field | Meaning |
|---|---|
| `Binding_Name` | The controller field shown in the widget. |
| `Selected_Item` | The controller field that holds the selected item (list boxes, combo boxes, spacers). |
| `Two_Way_Binding` | `1` writes widget changes back to the field. Only works for widgets whose controller allows it (see below). |
| `Relay_Command` | A `RelayCommand` subclass name, or a method name on the controller or view. |
| `Debug_Logging` | `1` prints what the binding does. |

### Updating the view

- After you change a field, call `NotifyPropertyChanged("FieldName")` on the controller, or `NotifyPropertiesChanged({"A", "B"})`. Calling `NotifyPropertyChanged()` with no name refreshes every binding; the source warns that this is slow.
- Override `PropertyChanged(string property_name)` on the controller to react after a field changes, including changes written back by two way bindings.
- Do not call `NotifyPropertyChanged` for an `ObservableCollection`. It notifies on `Insert`, `InsertAt`, `Remove`, `Set`, `SwapItems` and `Clear`. Override `CollectionChanged(string collection_name, CollectionChangedEventArgs args)` to react.
- Create a collection with the controller: `ref ObservableCollection<ref MyMod_RowView> Rows = new ObservableCollection<ref MyMod_RowView>(this);`. Bound to a spacer or scroll widget, each inserted `ScriptView` adds its layout root as a child.

### Commands

When a bound `ButtonWidget` is clicked or a bound `CheckBoxWidget` changes, the binding runs its `Relay_Command`:

- A `RelayCommand` subclass: `Execute(Class sender, CommandArgs args)` runs when `CanExecute()` is true. Return `true` when handled.
- Otherwise a method of that name, called with the arguments object: `void OnRefreshExecute(ButtonCommandArgs args)`, as the DayZ Editor does (`4_World\DayZEditor\gui\Controllers\EditorHudController.c`).
- Not handled goes on to the parent controller.
- Only a `ButtonWidget` (in `OnClick`) and a `CheckBoxWidget` (in `OnChange`) run a command; a `Relay_Command` on any other widget type never fires (`ViewController.c`).

`ButtonCommandArgs` has `GetMouseButton()` and `GetButtonState()`. `CheckBoxCommandArgs` has `GetCheckBoxState()`. Both have `Source`, the widget.

#### A command that runs twice

One click can run a command twice, in two ways. The symptom is the same for both: a toggle cancels itself and seems to do nothing.

1. **The handler does not return `true`** (read from the Dabs source). "Handled" is the method's return value. `ViewBinding.InvokeCommand` (`3_Game\DabsFramework\MVC\ViewBinding.c`) calls the method through `g_Script.CallFunction` and, when the result is not true, calls the same method name on each parent in turn. A handler declared `void`, or one that returns false, can therefore run again on a parent that has a method of that name. Declare handlers `bool` and return `true` when the click was handled: `bool OnRefreshExecute(ButtonCommandArgs args)`.
2. **The view overrides `OnClick` and calls `super.OnClick()` while the widget also has a `Relay_Command`** (third party mod behaviour, not checked against the Dabs source; code in `skills/enforce-script-reference/references/dabs-mvc-advanced.md`). The override and the command both run. Use the command or the override, not both.

### Which widgets bind

From `RegisterWidgetControllers` in `3_Game\DabsFramework\!Core\DayZGame.c`. Widgets marked two way allow `Two_Way_Binding`.

| Widget | Two way |
|---|---|
| `ButtonWidget`, `CheckBoxWidget`, `EditBoxWidget`, `PasswordEditBoxWidget`, `MultilineEditBoxWidget`, `SliderWidget`, `ProgressBarWidget`, `XComboBoxWidget`, `TextListboxWidget` | yes |
| `SpacerBaseWidget`, `WrapSpacerWidget`, `GridSpacerWidget`, `ScrollWidget` (hold collections) | yes |
| `TextWidget`, `MultilineTextWidget`, `RichTextWidget`, `ImageWidget`, `ItemPreviewWidget`, `PlayerPreviewWidget`, `HtmlWidget`, `CanvasWidget`, `MapWidget` | no |

Field types with built in converters (`RegisterConversionTemplates`, same file): `bool`, `int`, `float`, `string`, `vector`, `Widget`, `Object`, `Observable`, `ScriptedViewBase` and `StringEvaluater`. Other types need a converter added by modding `DayZGame.RegisterConversionTemplates`.

---

## ScriptViewMenu

`ScriptViewMenu` (`3_Game\DabsFramework\MVC\ScriptViewMenu.c`) is a `ScriptView` that is also a full screen menu. Its constructor wraps itself in a `UIScriptViewMenu` (a `UIScriptedMenu`), shows it through the vanilla `UIManager`, takes mouse focus and applies input excludes. So `new MyMod_Menu();` opens the menu; you do not call `EnterScriptedMenu`.

- Close it with `Close()`, which deletes it on the next GUI frame when `CanClose()` returns true. The file header says you own its memory: keep a reference while it is open, and do not delete it twice.
- Override `UseMouse()` (default true), `UseKeyboard()` (default false), `GetInputExcludes()` (names from `<exclude>` in `bin/specific.xml`), `CanClose()` and `HidesParentMenu()`.
- `ScriptViewMenuTemplate<T>` is the typed controller version.
- `EnterChildMenu(id or menu)` opens a vanilla menu or another `ScriptViewMenu` on top.
- **ESC does not close it.** `CanCloseWithEscape()` exists in `ScriptViewMenu.c`, but nothing in the framework calls it (the comment above it reads "tbd how i want to handle this"). Handle the key yourself, for example `OnKeyPress` with `KeyCode.KC_ESCAPE` calling `Close()`.
- **The lifecycle hooks are `OnMenuEnter(UIMenuPanel parent_panel)` and `OnMenuExit(UIMenuPanel parent_panel)`.** `ScriptView` and `ScriptViewMenu` have no `OnShow` or `OnHide` to override; show or hide a plain view with `Show(bool)`.
- **Game focus is taken on open and not given back on close.** The constructor calls `ChangeGameFocus(1, ...)` for the mouse (and the keyboard when `UseKeyboard()` is true); both `ChangeGameFocus(-1, ...)` lines in the destructor are commented out. A mod that adds its own `ChangeGameFocus` calls around a Dabs menu can leave the focus count unbalanced, so check that the player can move after the menu closes.
- `GetInputRestrictions()` is not wired: the constructor and destructor loop over an empty local array, so overriding it does nothing. Use `GetInputExcludes()`.

```c
class MyMod_Menu: ScriptViewMenuTemplate<MyMod_StatusController>
{
	override string GetLayoutFile()
	{
		return "MyMod/gui/layouts/menu.layout";
	}

	void OnCloseExecute(ButtonCommandArgs args)
	{
		Close();
	}
}
```

---

## Traps

- **Names are matched as strings.** Widget fields match widget names, and `Binding_Name` matches field names. A typo leaves the field null or the binding empty. Check the log with `Debug_Logging 1` on the binding.
- **Wrong layout path leaves a menu with no layout.** When `CreateWidgets` fails, `ScriptView` logs `Invalid layout file <path>` and has no root widget, but the `ScriptViewMenu` constructor still shows the menu and takes the mouse. The player is left with a cursor, no visible menu and other menus that will not open. The path must start with your `$PBOPREFIX$`. After `new`, check `GetLayoutRoot()` and call `Close()` when it is null.
- **Views are client only.** Creating one on a dedicated server logs an error and makes nothing.
- **The update loop runs every frame.** `Update(float dt)` is queued for every view by default. Return false from `UseUpdateLoop()` when the view has no per frame work.
- **Do not mix with a vanilla `ActionConstructor` mod for the same action.** Registering one action type both ways adds it twice.
- **Hot reload exists only in diag builds.** `ScriptView.ReloadAll()` is compiled only under `DIAG_DEVELOPER`.
- **A controller named as `scriptclass` on the layout root does not get its widget fields filled.** `LoadWidgetsAsVariables` runs on the controller only in the branch where `ScriptView` creates it from `GetControllerType()`. Use bindings, or look the widgets up yourself.
- **A collection item that holds a `ref` back to its controller leaks.** `ObservableCollection` stores `ref array<ref TValue>`, and nothing breaks the cycle. Set the back reference to null in the item's destructor. Third party mod behaviour, not checked against the Dabs source: `Clear()` on the collection does not break the cycle either, so null the back reference in each row view before clearing, and do not walk the parent chain from a row; pass the controller in.
- **Do not use `ObservableSet`.** It raises `NotifyCollectionChangedAction.Add` and `.Set`, which the enum (`MVC\Types\NotifyCollectionChangedAction.c`) does not have.
- **`WidgetAnimator` times are milliseconds, but the `TimeSpan` helpers count seconds.** `TimeSpan` is `typedef int` (`1_Core\DabsFramework\TimeSpan.c`), so `TimeSpan.FromMinutes(1)` is 60 and animates for 60 ms. Pass plain millisecond ints: `WidgetAnimator.Animate(widget, WidgetAnimatorProperty.COLOR_A, 1.0, 300);`.
- **Detect the framework from script with `#ifdef DABSFRAMEWORK_1_51`**, defined at the top of `MVC\ScriptedViewBase.c`. The mod has no release tags.

More depth (the full `WidgetAnimator` and `LinearColor` calls, the complete `ObservableCollection` operations, click dispatch and the shipped prefab layouts) is in `skills/dayz-ui-development/references/dabs-framework.md`.

Third party mod behaviour, not checked against the Dabs source; the code for each is in `skills/enforce-script-reference/references/dabs-mvc-advanced.md`:

- **Do not create a `ScriptView` from an RPC handler or during early init.** The constructor creates widgets and needs a workspace. Queue the creation on `CALL_CATEGORY_GUI` instead.
- **Widgets inside a `ButtonWidget` can bind to the wrong widget.** Auto binding and `FindAnyWidget` returned wrong, non null references for children of a button. Fetch those children yourself from the button after the view is created.
- **A `Relay_Command` that runs twice** has two causes, a handler that does not return `true` and an `OnClick` override that calls `super.OnClick()`; both are under "A command that runs twice" above.
- **`scriptclass "ViewBinding"` on the root widget plus `GetControllerType()` makes two controllers.** Leave the root widget without a script class.
