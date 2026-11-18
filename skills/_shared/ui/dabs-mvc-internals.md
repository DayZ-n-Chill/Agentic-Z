# Dabs MVC: views, bindings and commands

How Dabs Framework's view layer behaves when you read its source: what the `ScriptView` constructor does, how widgets and bindings are found, how a `Relay_Command` is dispatched, and how clicks travel from widget to handler. Collections, two way binding, `WidgetAnimator` and `LinearColor` are in `dabs-observables-and-animation.md`; `ScriptViewMenu`, the prefab layouts and versions are in `dabs-menus-and-prefabs.md`.

Dabs Framework is a third party mod. Everything here is checked against the framework's own scripts in the Steam Workshop copy (`addons\Scripts.pbo`), not vanilla. Paths are inside `Scripts.pbo`, for example `3_Game\DabsFramework\MVC\ScriptView.c`, and lines are that copy's; the framework changes between releases, so open the named file again when something does not match. Read the short introduction in `skills/_shared/enscript/integrations/dabs_framework.md` first.

## Class tree

| Class | Base | Adds |
|---|---|---|
| `ScriptedViewBase` | `Managed` | `m_LayoutRoot`, `m_WidgetController`, events, `Debug_Logging` |
| `ViewController` | `ScriptedViewBase` | Data binding, `NotifyPropertyChanged`, event dispatch |
| `ViewBinding` | `ScriptedViewBase` | `Binding_Name`, `Two_Way_Binding`, `Relay_Command` |
| `ScriptView` | `ScriptedViewBase` | Layout creation, the update loop, widget fields filled by name |
| `ScriptViewMenu` | `ScriptView` | Cursor, input excludes, the vanilla `UIManager` stack |
| `QuickView<T>` | `ScriptView` | One widget of type `T` made from script, no layout file |

In the framework's repository (`production` branch, `DabsFramework/Scripts/3_Game/DabsFramework/MVC/`), `class ScriptView : ScriptedViewBase` is at `ScriptView.c:39` and `class ViewBinding : ScriptedViewBase` at `ViewBinding.c:1`; the lines below are the Workshop copy's and can differ slightly (the constructor is `:45` to `:98` in the repository).

`ScriptViewTemplate<Class T>` and `ScriptViewMenuTemplate<Class T>` are the typed versions: `GetControllerType()` returns `T` and `GetTemplateController()` returns the controller already cast.

## What constructing a ScriptView does

The constructor (`MVC\ScriptView.c:46` to `:97`) runs in this order:

1. `CreateWidget(null)` calls `workspace.CreateWidgets(GetLayoutFile(), parent)` (`:160` to `:182`). It logs an error and returns null when `GetLayoutFile()` is empty, the workspace is null or the layout does not load (`Invalid layout file <path>`).
2. `LoadWidgetsAsVariables(this, m_LayoutRoot)` fills the view's `Widget` fields by name, once.
3. `m_LayoutRoot.GetScript(m_Controller)` looks for a controller set as the root's `scriptclass`.
4. When there is none, `GetControllerType().Spawn()` creates one, `LoadWidgetsAsVariables(m_Controller, m_LayoutRoot)` fills its widget fields, and `m_Controller.OnWidgetScriptInit(m_LayoutRoot)` loads the bindings and installs the event handler.
5. `m_Controller.SetParent(this)` and `m_LayoutRoot.SetUserData(this)` (`:86` and `:87`).
6. When `UseUpdateLoop()` is true, `Update` joins the `CALL_CATEGORY_SYSTEM` queue.

Step 4 runs only when the view creates the controller. A controller declared as `scriptclass` on the layout root (the Workbench way) gets no `Widget` fields filled: bind them yourself or use `ViewBinding`s.

The whole block sits inside `#ifndef COMPONENT_SYSTEM` and, within that, `#ifndef NO_GUI`. On a dedicated server (`NO_GUI`) the constructor logs `Attempted to create layout on SERVER!`; with `COMPONENT_SYSTEM` it skips the layout silently (`:92` to `:95`).

So `new ScriptView()` calls `CreateWidgets` itself. Never construct a view where the workspace can be null, such as an RPC handler that runs before the mission UI exists. Create it once at mission init and show or hide it.

The destructor (`:99` to `:124`) removes `Update` from the queue (with a `GetGame()` null check), deletes `m_Controller`, unlinks `m_LayoutRoot` and its whole tree, and removes the view from the static `All` array. `Delete()` (`:210` to `:213`) deletes the view on the next GUI frame and is the safe way to delete from inside it. `SetController(ViewController)` (`:185` to `:191`) attaches an existing controller.

| Override | Default | Meaning |
|---|---|---|
| `string GetLayoutFile()` | none | Path to the `.layout`; required |
| `typename GetControllerType()` | `ViewController` | The controller to spawn |
| `bool UseUpdateLoop()` | `true` | Whether `Update` runs |
| `void Update(float dt)` | empty | Called every frame when the loop is on |

`GetLayoutRoot()` and its `GetScreenSize()` are valid right after the constructor: Dabs's own `TooltipView` reads `GetLayoutRoot().GetScreenSize()` on the next line (`3_Game\DabsFramework\!Core\Views\Tooltip.c:56` and `:59`), and its tooltip places itself with `GetScreenPos`, `GetScreenSize`, `SetScreenPos`, `GetTextSize` and `GetMousePos` (`Tooltip.c:34` to `:136`). `UseUpdateLoop()` returns true unless you override it (`ScriptView.c:293` to `:296`). `GetFocus() == myEditBox` tells a view which field has focus (`OptionSelectorSliderView.c:41`).

Under `#ifdef DIAG_DEVELOPER`, the static `ScriptView.ReloadAll()` (`:126` to `:135`, commented "Hot reload all widgets layouts") unlinks and rebuilds the layout of every live `ScriptView` and fills the widget fields again. Wire it to a key or a DbgUI button to iterate a Dabs layout under DayZDiag.

## How widget fields are filled

`static void LoadWidgetsAsVariables(Class context, notnull Widget root_widget)` (`MVC\ScriptView.c:238` to `:266`) is a flat loop: for each property whose type inherits `Widget` it does one `root_widget.FindAnyWidget(property_name)`. There is no recursion and no special case for children of a `ButtonWidget`. The guard commented `// fixes bug that breaks everything` only skips the assignment when the lookup is null or the name is the root's own. Dots are stripped from the property name, and a field named like the root gets the root itself.

For nested lookups the framework uses dot names: call children `Button.Icon` and `Button.Text` in the layout and resolve them with `ScriptView.FindWidgetClass(parent, classname)` (`:281` to `:291`, which splits on `.`), or with `FindWidget<T>.SearchDown(parent, name)` from `1_Core`.

A shipped mod saw `FindAnyWidget` return the wrong widget for children inside a `ButtonWidget`; not reproduced. Since this loader is only `FindAnyWidget`, fields bound to such children go wrong too. Keep a button's children in arrays filled by walking the button, not in named fields.

## Bindings

`ViewController.OnWidgetScriptInit` (`MVC\ViewController.c:58` to `:70`) installs the event handler on the root, then loads the data bindings (`LoadDataBindings`) by walking the tree. For each widget whose `scriptclass` is `ViewBinding` it sets the binding's parent, adds it to `m_ViewBindingHashMap` (`map<Widget, ViewBinding>`) and to `m_DataBindingHashMap` (property name to bindings), loads its `RelayCommand` when one is named, and calls `NotifyPropertyChanged(binding_name, false)` once to show the starting value. The walk stops at a widget whose script is another `ViewController` (that subtree belongs to the child, which gets `SetParent`) and never reaches the root's siblings; remember both when a binding is "not found".

`map<Widget, T>` works: `ViewBindingHashMap` is `typedef map<Widget, ViewBinding>` (`MVC\Types\Types.c:24`), used throughout the controller (`MVC\ViewController.c:319`).

`NotifyPropertyChanged(string property_name = "", bool notify_controller = true)` (`MVC\ViewController.c:84` to `:117`):

- With a name it calls `UpdateView` only on the bindings whose `Binding_Name` is that name (`:106` to `:112`).
- With an empty name it updates every binding (`:91` to `:103`); the source logs that this "is NOT recommended as it is performance intensive".
- `notify_controller = false` skips the `PropertyChanged` callback (`:84`, `:114`). Pass it when you set properties inside `PropertyChanged`, or the two call each other forever.
- `NotifyPropertiesChanged(array<string>)` (`:126` to `:131`) updates several names.

A binding is not reactive: changing a field shows nothing until you call `NotifyPropertyChanged` for it. Dot names such as `"m_MyObj.value"` work through `PropertyInfo.GetSubScope` (`MVC\Types\PropertyInfo.c:35`, used at `MVC\ViewController.c:243`; Dabs's own sample binds one at `SampleMVC.c:185`).

A `ViewBinding` reads these from the layout's `ScriptParamsClass` (`MVC\ViewBinding.c:4` to `:13`):

| Field | Type | Meaning |
|---|---|---|
| `Binding_Name` | `string` | Controller property to show |
| `Selected_Item` | `string` | Property that holds the selection |
| `Two_Way_Binding` | `bool` | Write widget changes back to the controller |
| `Relay_Command` | `string` | Command class, field or function name |
| `Debug_Logging` | `bool` | Declared on the base as `[NonSerialized()] reference bool Debug_Logging` (`MVC\ScriptedViewBase.c:8`), so any binding or controller takes it; children inherit it through `SetParent` (`:71`) |

`UpdateView` reads the property through a `TypeConverter` and writes it with `WidgetController.Set()`. `UpdateController` runs only when `Two_Way_Binding` is set and the widget's controller returns true from `CanTwoWayBind()` (`MVC\ViewBinding.c:112`); it reads the widget, writes the field and calls `NotifyPropertyChanged`. `OnClick`, `OnChange` and `OnKeyPress` trigger it. A binding that asks for two way on a widget that can't do it logs `Two Way Binding for <type> is not supported!` at init (`:47` and `:48`).

## Commands

A `Relay_Command` can name three things. `LoadRelayCommand` tries them in this order (`MVC\ViewController.c:273` to `:313`): a controller property with that name, then a type with that name that inherits `RelayCommand`, then a plain function call at click time.

```c
// Layout: Relay_Command "OnSaveExecute". The simplest form: a function on the controller.
bool OnSaveExecute(ButtonCommandArgs args)
{
    return true; // handled
}

// Layout: Relay_Command "m_SaveCommand". A field on the controller; when it is null, Dabs
// spawns the field's declared type (MVC\ViewController.c:282 to :294). Declare the concrete
// subclass: a bare RelayCommand has an empty Execute, and a held command gets no function fallback.
ref MyMod_SaveCommand m_SaveCommand;

// Layout: Relay_Command "MyMod_SaveCommand". A class found by type name.
class MyMod_SaveCommand : RelayCommand
{
    override bool Execute(Class sender, CommandArgs args) { return true; }
}
```

`RelayCommand` (`MVC\Inputs\RelayCommand.c`) is an abstract `Managed` class with `SetController`, `SetViewBinding`, an overridable `bool CanExecute()` checked before `Execute`, and `bool Execute(Class sender, CommandArgs args)`. The argument types (`MVC\Types\CommandArgs.c`) are `ButtonCommandArgs` (the button and mouse button), `CheckBoxCommandArgs` (the check box) and the base `CommandArgs` with `Context`, the `ViewBinding`. `XComboBoxCommandArgs` and `WrapSpacerCommandArgs` exist, but they extend `Param2` and nothing creates them.

`InvokeCommand` (`MVC\ViewBinding.c:206` to `:231`):

1. A held `RelayCommand` whose `CanExecute()` is true runs `Execute(context, args)`, and its return value is "handled".
2. Only when no `RelayCommand` is held and `Relay_Command` is not empty (`:217`), it calls `g_Script.CallFunction(context, Relay_Command, handled, args)`. A held command whose `CanExecute()` is false gets no function fallback.
3. When not handled and the context has a parent, it calls itself on the parent (`:222` to `:224`).

What follows for your handlers:

- Only two widget types fire a command: `ViewController.OnClick` makes `ButtonCommandArgs` for a `ButtonWidget` (`MVC\ViewController.c:316` to `:335`), and `OnChange` makes `CheckBoxCommandArgs` for a `CheckBoxWidget` (`:337` to `:357`).
- Return true when the handler handled the click. `OnClick` then returns true at once and skips `super.OnClick`. A handler that returns false or is `void` leaves "handled" false, so the same function name is called on the view and each ancestor in turn: the click runs twice or more.
- Tinting a button does not disable it. Put the permission or state check in the handler and return before any RPC or state change.

## How a click reaches the handler

1. `ScriptedViewBase` derives from `Managed`, not from `ScriptedWidgetEventHandler` (`MVC\ScriptedViewBase.c:4`). The bridge is `ScriptedViewBaseHandler`, a `ScriptedWidgetEventHandler` that forwards `OnClick(Widget w, int x, int y, int button)` to its `ScriptedViewBase` (`MVC\ScriptedViewBaseHandler.c:2` to `:14`).
2. The `ViewController` owns that bridge and installs it with `m_LayoutRoot.SetHandler(m_ScriptedViewBaseHandler)` (`MVC\ViewController.c:56` to `:63`), the same vanilla `SetHandler` a plain handler uses (`P:\scripts\1_core\proto\enwidgets.c:172`). That is why a Dabs view never calls `SetHandler(this)` itself.
3. `ScriptView` separately writes the view into the root's user data (`MVC\ScriptView.c:86` and `:87`, `:149` and `:150`). `SetHandler` does not make `GetScript()` return the handler.
4. Every `On*` event except `OnResize` then bubbles from the `ViewController` up to the `ScriptView` through `m_ParentScriptedViewBase` (the source comment: "Events are invoked up heirarchy, starting at ViewController, and up to ScriptView").

A generic search that walks up the parents and casts `GetScript()` or `GetUserData()` to `ScriptedWidgetEventHandler` misses a valid Dabs view, because the root's user data is the `ScriptView` and the bridge sits on the controller. Always pass the widget that was clicked: a view that dispatches on `w.GetUserID()` silently misses when automation passes the root instead. An outside test harness still needs a way to find the root and the real widget; see `automated-ui-checks.md`, "Dabs views are not menus".

`OnResize` stops at the `ViewController`: the bridge passes it to the controller (`MVC\ScriptedViewBaseHandler.c:121` to `:124`), but `ScriptedViewBase.OnResize` returns true before its forwarding line (`MVC\ScriptedViewBase.c:261` and `:262`), so an `OnResize` override on a `ScriptView` never runs. Override it on the `ViewController` instead. The framework's wiki says nothing about the view layer, so its problems are found by reading the source.
