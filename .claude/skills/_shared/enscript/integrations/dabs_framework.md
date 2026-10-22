# Dabs Framework Integration

What Dabs Framework adds for UI and registration: attribute classes, the MVC layer (`ScriptView`, `ViewController`, `ViewBinding`, `RelayCommand`, observable collections) and `ScriptViewMenu`.

Dabs Framework is a third party mod by InclementDab, not part of the game. Everything below is a **framework** fact, not a vanilla fact. Use it only when the mod already depends on Dabs Framework or the user asks for it; plain vanilla UI is in `../references/widget_api.md`.

**Where these facts come from.** The Steam Workshop copy of the mod, linked on this machine at `P:\Mods\@Dabs Framework\`. Its `addons\Scripts.pbo` holds plain script, and file paths below are paths inside that PBO (for example `3_Game\DabsFramework\MVC\ScriptView.c`). Usage examples were checked against the DayZ Editor mod (`P:\Mods\@DayZ-Editor\`), which is built on Dabs. The framework changes between releases, so open the named file again when something here does not match.

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

`ButtonCommandArgs` has `GetMouseButton()` and `GetButtonState()`. `CheckBoxCommandArgs` has `GetCheckBoxState()`. Both have `Source`, the widget.

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
