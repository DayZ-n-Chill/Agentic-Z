# Dabs Framework deep dive: MVC lifecycle, commands, observables, WidgetAnimator, LinearColor, ScriptViewMenu

How Dabs Framework's UI layer behaves when you read its source line by line: what the `ScriptView` constructor does, how a `Relay_Command` is dispatched, the full `ObservableCollection` contract, the `WidgetAnimator` and `LinearColor` calls with their traps, and what `ScriptViewMenu` does and does not do for you.

Dabs Framework is a third party mod, not part of the game. Everything here is a **framework** fact, not a vanilla fact. The short, checked introduction (attributes, a first view, a first binding) is `skills/_shared/enscript/integrations/dabs_framework.md`; read that first and come here for depth.

**How facts are marked here.** The claims below were checked in November 2026 against the Steam Workshop copy of Dabs Framework (`addons\Scripts.pbo` and `addons\GUI.pbo`); none of it is on `P:\`. File paths are paths inside `Scripts.pbo`, for example `3_Game\DabsFramework\MVC\ScriptView.c`, and line numbers are the Workshop copy's. A line that says "not checked against the Workshop copy" describes the framework's repository at `production` commit `fd859fd8` (last code commit 2025-12-18). The framework changes between releases, so open the named file again when something here does not match.

---

## Contents

- [Class hierarchy](#class-hierarchy)
- [ScriptView lifecycle](#scriptview-lifecycle)
- [LoadWidgetsAsVariables](#loadwidgetsasvariables)
- [ViewController: data binding](#viewcontroller-data-binding)
- [ViewBinding](#viewbinding)
- [Relay_Command](#relay_command)
- [ObservableCollection and the other observables](#observablecollection-and-the-other-observables)
- [Two way binding support](#two-way-binding-support)
- [WidgetAnimator](#widgetanimator)
- [LinearColor](#linearcolor)
- [ScriptViewMenu](#scriptviewmenu)
- [Prefab layouts shipped with Dabs](#prefab-layouts-shipped-with-dabs)
- [Proven production patterns](#proven-production-patterns)
- [Event flow](#event-flow)
- [Click dispatch and external automation](#click-dispatch-and-external-automation)
- [Versions, branches and dependencies](#versions-branches-and-dependencies)

## Class hierarchy

```
Managed
  └─ ScriptedViewBase          // base: m_LayoutRoot, m_WidgetController, events, Debug_Logging
       ├─ ViewController       // data binding, NotifyPropertyChanged, event dispatch
       ├─ ViewBinding          // Binding_Name, Two_Way_Binding, Relay_Command
       └─ ScriptView           // layout creation, Update loop, widget variable loading
            ├─ ScriptViewMenu  // cursor, input excludes, UIManager integration
            └─ QuickView<T>    // creates one widget of type T from script (no layout file)
```

`ScriptViewTemplate<Class T>` and `ScriptViewMenuTemplate<Class T>` (`MVC\ScriptViewTemplate.c`, `MVC\ScriptViewMenuTemplate.c`) are the typed controller versions: `GetControllerType()` returns `T` and `GetTemplateController()` returns the controller already cast.

---

## ScriptView lifecycle

### Constructor (`MVC\ScriptView.c:46-97`)

1. `CreateWidget(null)` calls `workspace.CreateWidgets(GetLayoutFile(), parent)` (`:160-182`). It logs an error and returns null when `GetLayoutFile()` is empty, when the workspace is null, or when the layout does not load (`Invalid layout file <path>`).
2. `LoadWidgetsAsVariables(this, m_LayoutRoot)` fills the view's `Widget` typed fields by name. It runs once.
3. `m_LayoutRoot.GetScript(m_Controller)` checks whether the layout root has a controller as its `scriptclass`.
4. When no controller is found: `GetControllerType().Spawn()` creates one, then `LoadWidgetsAsVariables(m_Controller, m_LayoutRoot)` fills the controller's widget fields and `m_Controller.OnWidgetScriptInit(m_LayoutRoot)` loads the bindings and installs the event handler.
5. `m_Controller.SetParent(this)` and `m_LayoutRoot.SetUserData(this)` (`:86-87`).
6. When `UseUpdateLoop()` is true, `Update` is added to the `CALL_CATEGORY_SYSTEM` update queue.

Steps 4's two calls run only in the branch that creates the controller. When the controller is declared as `scriptclass` on the layout root (the Workbench style), nothing fills its `Widget` fields: bind them yourself or use `ViewBinding`s.

The whole block sits inside `#ifndef COMPONENT_SYSTEM` and `#ifndef NO_GUI`; with either define set (a dedicated server) the constructor logs `Attempted to create layout on SERVER!` instead.

`new ScriptView()` therefore calls `CreateWidgets` itself. Never construct a view where the workspace can be null, such as an RPC handler that runs before the mission UI exists; create the view once at mission init and show or hide it later (rule 9 in `rules-and-checklist.md`).

### Destructor (`MVC\ScriptView.c:99-124`)

1. Removes `Update` from the update queue (with a `GetGame()` null check).
2. `delete m_Controller`.
3. `m_LayoutRoot.Unlink()`, which destroys the whole widget tree.
4. Removes the view from the static `All` array.

### Key overrides

```
string GetLayoutFile()           // required: path to the .layout
typename GetControllerType()     // default: ViewController
bool UseUpdateLoop()             // default: true
void Update(float dt)            // called every frame when UseUpdateLoop is true
```

`Delete()` (`:210-213`) deletes the view on the next GUI frame and is the safe way to delete from inside the view. `SetController(ViewController)` (`:185-191`) attaches an existing controller.

### GetLayoutRoot() timing

Valid immediately after the constructor. Dabs's own `TooltipView` creates a `ScriptView` and calls `GetLayoutRoot().GetScreenSize()` on the next line, and that works in production.

### Hot reload under DIAG

Under `#ifdef DIAG_DEVELOPER`, the static `ScriptView.ReloadAll()` (`MVC\ScriptView.c:126-135`, comment "Hot reload all widgets layouts") unlinks and rebuilds the layout of every live `ScriptView`, then runs `LoadWidgetsAsVariables` again. It is a ready made layout iteration tool for Dabs UIs under DayZDiag; wire it to a keybind or a DbgUI button.

---

## LoadWidgetsAsVariables

`static void LoadWidgetsAsVariables(Class context, notnull Widget root_widget)` (`MVC\ScriptView.c:238-266`).

- It is a **flat loop**: for every property whose type inherits `Widget` it does exactly one `root_widget.FindAnyWidget(property_name)`. There is no recursion, no special case for children of a `ButtonWidget` and no workaround. The guard commented `// fixes bug that breaks everything` only skips the assignment when the lookup is null or the name is the root's own name.
- Dots are stripped from the property name before the lookup, and a field named like the layout root gets the root widget itself.
- The framework's own answer for nested lookups is **dot naming**: name children `Button.Icon`, `Button.Text` in the layout and resolve them with `ScriptView.FindWidgetClass(parent, classname)` (`:281-291`, splits on `.`), or with the generic `FindWidget<T>.SearchDown(parent, name)` in `1_Core`.
- Seen in a shipped mod, not reproduced: `FindAnyWidget` returned wrong references for widgets nested inside a `ButtonWidget`, and since this loader is only `FindAnyWidget`, fields bound to such widgets were wrong too. The workaround is to store the children of a button in arrays filled by walking the button's children, not in named fields (rule 8 in `rules-and-checklist.md`).

---

## ViewController: data binding

### LoadDataBindings (called in OnWidgetScriptInit)

`ViewController.OnWidgetScriptInit` (`MVC\ViewController.c:58-70`) installs the event handler on the layout root, then walks the widget tree. For each widget whose `scriptclass` is `ViewBinding` it:

1. Sets the binding's parent to this controller.
2. Inserts it into `m_ViewBindingHashMap` (`map<Widget, ViewBinding>`).
3. Inserts it into `m_DataBindingHashMap` (property name to a set of bindings).
4. Loads the `RelayCommand` when one is named.
5. Calls `NotifyPropertyChanged(binding_name, false)` once to show the starting value.

The walk stops descending at a widget whose script instance is another `ViewController` (that subtree belongs to the child controller, which gets `SetParent`), and it never runs into the root's siblings. Remember both when you debug "binding not found".

`map<Widget, T>` works: `ViewBindingHashMap` is `typedef map<Widget, ViewBinding>` (`MVC\Types\Types.c`) and is used throughout `ViewController.c`. An older claim that widget keyed maps crash was wrong.

### NotifyPropertyChanged(string property_name = "", bool notify_controller = true)

`MVC\ViewController.c:84-117`.

- With a name it looks up `m_DataBindingHashMap[name]` and calls `UpdateView` on each binding. It touches only bindings whose `Binding_Name` is that name. It does not scan or overwrite other controller fields.
- With an empty name it updates every binding. The source logs that this "is NOT recommended as it is performance intensive".
- `notify_controller = false` skips the `PropertyChanged` callback, which prevents recursion.
- `NotifyPropertiesChanged(array<string>)` (`:126-131`) updates several names.

A binding is not reactive. Changing a field does nothing on screen until you call `NotifyPropertyChanged` for it.

### PropertyChanged(string property_name)

A virtual callback run after the view is updated. Override it for logic that spans properties. When you set properties inside `PropertyChanged`, pass `notify_controller = false` to avoid an endless loop.

### Sub property binding

Dot notation works: `"m_MyObj.value"` is resolved by `PropertyInfo.GetSubScope` (`MVC\Types\PropertyInfo.c:35`, used at `MVC\ViewController.c:243`). Dabs's `SampleMVC.c` shows it.

---

## ViewBinding

### Layout properties (`MVC\ViewBinding.c:4-13`)

```
reference string Binding_Name;     // controller property name
reference string Selected_Item;    // selection property name
reference bool Two_Way_Binding;    // view to controller sync
reference string Relay_Command;    // command name or function name
```

`Debug_Logging` is a fifth one. It is declared on the base class as `[NonSerialized()] reference bool Debug_Logging` (`MVC\ScriptedViewBase.c:8`), so it can be set from a layout's `ScriptParamsClass` on any binding or controller, and it spreads to children through `SetParent` (`:71`). An older claim that the field was removed is wrong: the Workshop copy has it.

### UpdateView (controller to widget)

Reads the property from the controller through a `TypeConverter` and writes it to the widget through `WidgetController.Set()`. `NotifyPropertyChanged` calls it.

### UpdateController (widget to controller)

Runs only when `Two_Way_Binding` is set and the widget's controller returns true from `CanTwoWayBind()` (`MVC\ViewBinding.c:112`). It reads the widget, writes the controller field and calls `NotifyPropertyChanged`. `OnClick`, `OnChange` and `OnKeyPress` on the controller trigger it. A binding that sets `Two_Way_Binding` on a widget that cannot do it logs `Two Way Binding for <type> is not supported!` at init (`:47-48`).

### InvokeCommand (`MVC\ViewBinding.c:206-231`)

1. When the binding holds a `RelayCommand` object and its `CanExecute()` is true, it runs `Execute(context, args)` and takes the returned bool as "handled".
2. Otherwise, when `Relay_Command` is not empty, it calls `g_Script.CallFunction(context, Relay_Command, handled, args)`: a method of that name on the controller, with its return value as "handled".
3. When not handled and the context has a parent, it calls itself on the parent (`:222-224`).

---

## Relay_Command

### Three ways to supply the command

**1. A function on the controller (simplest, recommended)**

```
// Layout: Relay_Command "OnSaveExecute"
// Controller:
bool OnSaveExecute(ButtonCommandArgs args)
{
    // your logic
    return true; // handled
}
```

**2. A RelayCommand field on the controller**

```
// Controller field, named like the Relay_Command value:
ref RelayCommand m_SaveCommand;
// Dabs creates it when it is null
```

**3. A RelayCommand class found by type name**

```
// Layout: Relay_Command "MySaveCommand"
class MySaveCommand : RelayCommand
{
    override bool Execute(Class sender, CommandArgs args) { return true; }
}
```

`LoadRelayCommand` resolves in that order of precedence: a controller property with that name, then a type with that name that inherits `RelayCommand` (`MVC\ViewController.c:300-310`), then a plain function call at click time.

The `RelayCommand` class (`MVC\Inputs\RelayCommand.c`) is an abstract `Managed` subclass with `SetController` and `SetViewBinding`, an overridable `bool CanExecute()` that is checked before `Execute`, and `bool Execute(Class sender, CommandArgs args)`.

### CommandArgs types (`MVC\Types\CommandArgs.c`)

- `ButtonCommandArgs`: the `ButtonWidget` and the mouse button.
- `CheckBoxCommandArgs`: the `CheckBoxWidget`.
- `CommandArgs`: the base class, with `Context` (the `ViewBinding`).
- `XComboBoxCommandArgs` and `WrapSpacerCommandArgs` exist but extend `Param2` and nothing in the framework creates them.

### How dispatch really works

- **Only two widget types fire a command.** `ViewController.OnClick` creates `ButtonCommandArgs` for a `ButtonWidget` (`MVC\ViewController.c:316-335`), and `ViewController.OnChange` creates `CheckBoxCommandArgs` for a `CheckBoxWidget` (`:337-357`). No other widget type dispatches a `Relay_Command`.
- **Command handlers must return true when they handled the click.** `OnClick` returns true as soon as `InvokeCommand` reports handled, and `super.OnClick` is not called in that case. The double execution risk is elsewhere: a handler that returns false, or is declared `void`, leaves "handled" false, so `InvokeCommand` walks up the parent chain and calls the same function name on each ancestor (the view, then its parents). An older wording, "Relay_Command plus a manual OnClick fires twice", described the symptom and not the cause.
- **Dimming is not gating.** A helper that only tints a button (`DimButton` style) leaves it clickable. Put the permission or state check in the handler and return before any RPC or state change.

---

## ObservableCollection and the other observables

### Constructor

```
ref ObservableCollection<MyView> m_Items = new ObservableCollection<MyView>(this);
```

Pass the `ViewController`. The template type must be a class (a reference type). Storage is `ref array<ref TValue>` (`MVC\Observables\ObservableCollection.c:41`).

### Operations (each notifies the UI)

```
int Insert(TValue value)
int InsertAt(TValue value, int index)
void InsertAll(array<TValue> from)
void Remove(int index)
void Remove(TValue value)
void RemoveOrdered(int index)
void RemoveRange(int start, int end)
void Set(int index, TValue value)
int MoveIndex(int index, int moveIndex)
void SwapItems(int itemA, int itemB)
void Clear()
TValue Get(int index)
int Count()
int Find(TValue value)
array<ref TValue> GetArray()
```

### Contracts

- **Binding.** The layout binding's `Binding_Name` must equal the name of the controller variable that holds the collection. `NotifyCollectionChanged` finds the variable by looking the instance up in reverse and logs "could not find variable" otherwise.
- **Item views.** For a collection of `ScriptView`, the element type is a `ScriptView` subclass that overrides `GetLayoutFile()`. Each instance builds its own tree (parent null); on `Insert` its layout root is moved into the bound spacer with `AddChild`. `TypeConversionScriptView.GetWidget()` returns the view's layout root.
- **Spacers.** Bind the collection to a spacer widget (`WrapSpacerWidget`, `GridSpacerWidget`) or a `ScrollWidget`.
- **Circular references.** When items hold a `ref` back to the parent controller, nothing breaks the cycle and both leak. Null the back reference in the item's destructor.
- **`ObservableSet` is broken; do not use it.** It raises `NotifyCollectionChangedAction.Add` and `.Set` (`MVC\Observables\ObservableSet.c:14`, `:23`, `:43`), and the enum only has `Insert`, `InsertAt`, `Remove`, `Replace`, `Move`, `Swap` and `Clear` (`MVC\Types\NotifyCollectionChangedAction.c`).
- **The widget to controller registry matches the exact type.** `RegisterWidgetControllers` (`3_Game\DabsFramework\!Core\DayZGame.c:54-80`) maps widget types to controllers and the lookup uses `data.Type()` with no walk up the inheritance chain. A binding on a widget type that is not registered logs "Could not find WidgetController for type X".

---

## Two way binding support

From `CanTwoWayBind()` in each file under `MVC\WidgetController\`:

| Widget | CanTwoWayBind | Set (controller to view) | Get (view to controller) |
|---|---|---|---|
| EditBoxWidget, PasswordEditBoxWidget | yes | SetText | GetText |
| ButtonWidget | yes | SetState(bool) | GetState |
| CheckBoxWidget | yes | SetChecked | IsChecked |
| SliderWidget | yes | SetCurrent | GetCurrent |
| ProgressBarWidget | yes | (see `ProgressBarController.c`) | |
| XComboBoxWidget | yes | (see `XComboBoxWidgetController.c`) | |
| TextListboxWidget | yes | (see `TextListboxController.c`) | |
| SpacerBaseWidget, WrapSpacerWidget, GridSpacerWidget, ScrollWidget | yes | AddChild | GetFocus (selection) |
| MultilineEditBoxWidget | yes | SetText | GetText |
| TextWidget, MultilineTextWidget, RichTextWidget | no | SetText | |
| ImageWidget | no | LoadImageFile | |

The Workshop copy returns true for `ProgressBarWidget`, `XComboBoxWidget` and `TextListboxWidget`, which matches the table in `skills/_shared/enscript/integrations/dabs_framework.md`.

`ButtonWidgetController`: `Set` and `Get` map to `SetState` and `GetState` (the pressed bool). `Selected_Item` on a button binds its label text (`SetText` and `GetText`).

---

## WidgetAnimator

`3_Game\DabsFramework\!Core\WidgetAnimator.c` (not under `MVC\`). A complete animation system. Do not build your own tween code on top of Dabs.

### Calls

```
// Animate from the current value to end
static void Animate(Widget source, WidgetAnimatorProperty property, float end_value, TimeSpan time)

// Animate with an explicit start
static void Animate(Widget source, WidgetAnimatorProperty property, float start_value, float end_value, int time)

// Animate with easing
static void AnimateEx(Widget source, WidgetAnimatorProperty property, float end_value, TimeSpan time, WidgetAnimatorEasing easing = 0)

// Loop
static void AnimateLoop(Widget source, WidgetAnimatorProperty property, float end_value, int time)
static void AnimateLoop(Widget source, WidgetAnimatorProperty property, float start_value, float end_value, int time)

// Color, with blend modes
static void AnimateColor(Widget source, LinearColor end_color, TimeSpan time, BlendMode blend_mode = BlendMode.NORMAL, bool loop = false)
static void AnimateColor(Widget source, LinearColor start_color, LinearColor end_color, TimeSpan time, BlendMode blend_mode = BlendMode.NORMAL, bool loop = false)

// HSV color
static void AnimateColorHSV(Widget source, vector start_color, vector end_color, TimeSpan time, bool loop = false, WidgetAnimatorEasing easing = 0)

// Control
static void CancelAnimate(Widget source, WidgetAnimatorProperty property = -1, bool reset = false)
static bool HasAnimation(Widget source, WidgetAnimatorProperty property)
static WidgetAnimatorProperty GetAnimations(Widget source)
```

Typical use:

```
WidgetAnimator.Animate(widget, WidgetAnimatorProperty.COLOR_A, 1.0, 300);
WidgetAnimator.AnimateEx(widget, WidgetAnimatorProperty.POSITION_Y, 0, 300, WidgetAnimatorEasing.EASE_OUT_SINE);
WidgetAnimator.AnimateColor(widget, endColor, 300, BlendMode.NORMAL);
WidgetAnimator.CancelAnimate(widget);
```

### WidgetAnimatorProperty (bit flags, `!Core\Enum\WidgetAnimatorProperty.c`)

```
POSITION_X = 1       POSITION_Y = 2
SIZE_W = 4           SIZE_H = 8
ROTATION_X = 16      ROTATION_Y = 32      ROTATION_Z = 64     // roll, pitch, yaw
COLOR_A = 128        COLOR_R = 256        COLOR_G = 512       COLOR_B = 1024
COLOR_H = 2048       COLOR_S = 4096       COLOR_V = 8192
EXACT_TEXT = 16384
SIZE_EXACT_W = 32768 SIZE_EXACT_H = 65536
LINEAR_COLOR = 1920  // A + R + G + B
```

Color values are floats from 0 to 1.

### WidgetAnimatorEasing (30 curves plus NONE)

`NONE`, then `EASE_IN_`, `EASE_OUT_` and `EASE_INOUT_` for each of: Sine, Quad, Cubic, Quart, Quint, Exponential, Circ, Back, Elastic, Bounce.

### Internals

- Runs on the `CALL_CATEGORY_GUI` update queue.
- Cancels the previous animation of the same property on the same widget.
- The timer deletes itself when it completes.
- On a `TextWidget`, `COLOR_A` also updates the outline alpha.

### Five traps

1. **The time unit is milliseconds, but the `TimeSpan` helpers count in seconds.** `TimeSpan` is `typedef int` (`1_Core\DabsFramework\TimeSpan.c:71`); `TimeSpan.FromMinutes(1)` gives 60, and the animator reads that as 60 ms. Pass plain millisecond ints.
2. **`EASE_IN_BOUNCE` and `EASE_OUT_BOUNCE` are swapped** in the implementation (`!Core\WidgetAnimationTimer.c:134-135`).
3. **`AnimateColor` does nothing when the current color already equals the end color**, loop included (`!Core\WidgetAnimator.c:103`).
4. **`AnimateColorHSV` does not cancel earlier animations** (every other entry point does) and starts three timers, one each for H, S and V.
5. Completed timers are never removed from the static `m_RunningTimers` array; only `CancelAnimate` removes entries (`:150-157`), so a long session leaks slots. Deleting or unlinking a widget in the middle of an animation is safe (the timer holds a weak reference and cleans itself up on the next GUI tick).

---

## LinearColor

`3_Game\DabsFramework\!Core\Color.c`. `class LinearColor: int`: an ARGB integer with color helpers.

### Construction

```
LinearColor.Create(r, g, b)           // ints 0-255
LinearColor.Create(a, r, g, b)        // ints 0-255
LinearColor.CreateF(r, g, b)          // floats 0-1
LinearColor.CreateF(a, r, g, b)       // floats 0-1
LinearColor.CreateHSV(hue, sat, val, alpha)  // hue 0-360, the rest 0-1
LinearColor.FromHex(hex)
```

### Access

```
int GetAlpha(), GetRed(), GetGreen(), GetBlue()
void SetAlpha(int), SetRed(int), SetGreen(int), SetBlue(int)
float GetLuminance()
string ToHexColor()
vector ToVector()            // float RGB, 0 to 1
```

### Operations

```
LinearColor.Lerp(a, b, blendMode, t)   // interpolation
LinearColor.Blend(a, b, blendMode)     // blend
bool IsEqual(other, epsilon)           // fuzzy compare
LinearColor Add / Subtract / Multiply
```

### BlendMode

`NORMAL`, `MULTIPLY`, `SCREEN`, `OVERLAY`, `HARD_LIGHT`, `SOFT_LIGHT`.

### Named constants

About 150 `static const LinearColor` values named after the X11 color set: `LinearColor.RED`, `.BLUE`, `.DARK_SLATE_GRAY`, `.CORNFLOWER_BLUE` and so on.

---

## ScriptViewMenu

`3_Game\DabsFramework\MVC\ScriptViewMenu.c`. A `ScriptView` that is also a menu on the vanilla `UIManager` stack.

### What the constructor and destructor do

- **Constructing it opens it.** The field `ref UIScriptViewMenu m_UIScriptViewMenu = new UIScriptViewMenu(this)` wraps the view in a `UIScriptedMenu`, and when `UseUIManager()` is true the constructor calls `ShowScriptedMenu(m_UIScriptViewMenu, GetMenu())` (`:19-22`).
- It adds the names from `GetInputExcludes()` with `Mission.AddActiveInputExcludes` (`:25`) and removes them in the destructor (`:79-81`).
- It calls `ChangeGameFocus(1, INPUT_DEVICE_MOUSE)` when `UseMouse()` is true and `ChangeGameFocus(1, INPUT_DEVICE_KEYBOARD)` when `UseKeyboard()` is true (`:38-44`).
- It sets the cursor visibility two GUI frames later with `SetMouseCursorDesiredVisibility` (`:47`; the source comment says one frame worked and two is the safe value).
- `Close()` queues `_Close` on `CALL_CATEGORY_GUI`, which runs `if (CanClose()) delete this` (`:170-191`). The file header says you own the object's memory: keep a reference while it is open.

### What it does not do

- **ESC does not close a Dabs menu.** `CanCloseWithEscape()` exists (`:181-184`) but nothing in the framework calls it; the source comment above it reads "tbd how i want to handle this". Wire ESC yourself, for example `OnKeyPress` with `KeyCode.KC_ESCAPE` calling `Close()`.
- **Game focus is not released on close.** Both `ChangeGameFocus(-1, ...)` calls in the destructor are commented out (`:68` and `:73`), and `UIScriptViewMenu` overrides `LockControls` and `UnlockControls` as empty methods (`MVC\UIScriptViewMenu.c:30-36`). Only cursor visibility is restored. A mod that adds its own `ChangeGameFocus` around a Dabs menu can leak focus counts; check the input state after the menu closes.
- **There is no `OnShow` or `OnHide` on `ScriptView` or `ScriptViewMenu`.** The only ones in the framework are the `UIScriptedMenu` overrides in the internal wrapper (`MVC\UIScriptViewMenu.c:54-66`), which forward to `ScriptViewMenu.OnMenuEnter(parent)` and `OnMenuExit(parent)`. Those two are the lifecycle hooks to override. Show or hide a plain `ScriptView` with `ScriptedViewBase.Show(bool)` and `IsVisible()`.
- **`GetInputRestrictions()` is dead code.** The constructor and destructor loop over a fresh empty local array instead of calling it (`:26-35` and `:84-92`), so overriding it does nothing.

### Override points

```
bool UseMouse()                       // default true: shows the cursor
bool UseKeyboard()                    // default false
bool UseUIManager()                   // default true: registers with UIManager
array<string> GetInputExcludes()      // names from <exclude> in bin/specific.xml
array<int> GetInputRestrictions()     // not wired, see above
bool HidesParentMenu(UIMenuPanel parent_panel)   // default true
bool CanClose()                       // guard for Close()
bool CanCloseWithEscape()             // not called by the framework
void OnMenuEnter(UIMenuPanel parent_panel)
void OnMenuExit(UIMenuPanel parent_panel)
```

### Methods

```
void Close()                                    // deferred delete
UIScriptedMenu EnterChildMenu(ScriptViewMenu menu)
UIScriptedMenu EnterChildMenu(int id)           // a vanilla menu id
UIScriptedMenu EnterChildMenu(UIScriptedMenu scripted_menu)
void ShowDialog(string caption, string text, int id, int buttons, int default_button, int type)
static ScriptViewMenu Get(UIScriptedMenu menu)
```

### Trade off

It uses the `UIManager` menu stack, which can conflict with other mods that manage menus. For a floating window that coexists with gameplay (a sorter window over the running game, for example), handle `ChangeGameFocus` and `HumanInputController.SetDisabled` by hand instead.

---

## Prefab layouts shipped with Dabs

In `addons\GUI.pbo` under `layouts\prefabs\`:

```
ButtonPrefab.layout
CheckBoxPrefab.layout
ColorPickerPrefab.layout
Dropdown\DropdownPrefab.layout, Dropdown\DropdownElementPrefab.layout
EditBoxPrefab.layout
EditboxSliderPrefab.layout
GroupPrefab.layout
HorizontalSpacerPrefab.layout
ListBoxPrefab.layout, Listbox\ListBoxPrefab.layout, Listbox\ListBoxEntryPrefab.layout
ListItems\CategorizedListItem.layout
MessageBoxPrefab.layout          (uses RichTextWidget)
MultilineEditBoxPrefab.layout
SliderPrefab.layout
TextBoxPrefab.layout
VectorPrefab.layout
```

The same PBO has `layouts\sample_mvc.layout`, `layouts\sample_mvc2.layout`, `layouts\tooltip\tooltip_view.layout` and the options menu layouts under `layouts\options\`. Their path from script starts with `DabsFramework/GUI/`, for example `DabsFramework/GUI/layouts/prefabs/ButtonPrefab.layout`.

---

## Proven production patterns

### ScrollWidget, WrapSpacer and ObservableCollection

From Dabs's `layouts\options\options_tab.layout`:

```
ScrollWidgetClass Scroll {
  "Scrollbar V" 1
  {
    WrapSpacerWidgetClass Content {
      scriptclass "ViewBinding"
      "Size To Content V" 1
      {
        ScriptParamsClass {
          Binding_Name "MyCollection"
        }
      }
    }
  }
}
```

### Function as command (from SampleMVC.c)

```
// Layout: Relay_Command "SwapItemsExecute"
bool SwapItemsExecute(ButtonCommandArgs args)
{
    m_Collection.SwapItems(m_Left, m_Right);
    return true;
}
```

### Color animation (from OptionSelectorColorViewController.c)

```
WidgetAnimator.AnimateColor(ColorPickerPanel, Value, 10);
```

### Widget position relative to its parent (from OptionSelectorColorViewController.c)

```
static void SetWidgetPosRelativeToParent(Widget w, float x, float y)
{
    x = Math.Clamp(x, 0, 1);
    y = Math.Clamp(y, 0, 1);
    Widget parent = w.GetParent();
    float pW, pH;
    parent.GetScreenSize(pW, pH);
    float wW, wH;
    w.GetScreenSize(wW, wH);
    w.SetPos((pW * x) - (wW / 2), (pH * y) - (wH / 2));
}
```

---

## Event flow

- Every `ScriptedViewBase` `On*` event bubbles up through `m_ParentScriptedViewBase`, from the `ViewController` to the `ScriptView` (`MVC\ScriptedViewBase.c`, comment "Events are invoked up heirarchy, starting at ViewController, and up to ScriptView"). The events enter through the handler that `ViewController.OnWidgetScriptInit` installs on the root. That is why a Dabs view needs no `SetHandler(this)` of its own (rule 10 in `rules-and-checklist.md`).
- The Workshop copy forwards `OnResize` like the other events (`MVC\ScriptedViewBaseHandler.c:121-124`). At repository commit `fd859fd8` it was dead code (not checked against the Workshop copy's history), so test it before relying on it.
- The framework's wiki has nothing on the UI layer, and its issue tracker has no `ViewBinding`, `ScriptView` or `WidgetAnimator` reports (not checked against the Workshop copy; read in July 2026). The known problems of the MVC layer are found only by reading the source.

---

## Click dispatch and external automation

Dabs uses two different objects in its click path. Confusing them gives a silent "no handler".

1. `ScriptedViewBase` derives from `Managed`, not from `ScriptedWidgetEventHandler` (`MVC\ScriptedViewBase.c:4`). The actual event bridge is `ScriptedViewBaseHandler: ScriptedWidgetEventHandler` (`MVC\ScriptedViewBaseHandler.c:2-14`), which forwards `OnClick(Widget w, int x, int y, int button)` to its `ScriptedViewBase`.
2. `ViewController` owns that bridge and installs it with `m_LayoutRoot.SetHandler(m_ScriptedViewBaseHandler)` (`MVC\ViewController.c:56-63`). Separately, `ScriptView` writes the **view** into the root's user data with `m_LayoutRoot.SetUserData(this)` (`MVC\ScriptView.c:86-87` and `:149-150`). `SetHandler` does not make `GetScript()` return the handler.
3. Event methods bubble from the `ViewController` to the `ScriptView`. Always pass the widget that was actually clicked. A view that dispatches on `w.GetUserID()` silently misses when automation passes the layout root instead.

A generic handler search that walks up the parents and casts only `GetScript()` or `GetUserData()` to `ScriptedWidgetEventHandler` therefore misses a valid Dabs view: the root's user data is a `ScriptView`, while the bridge is held by the controller. This describes the framework's internal contract. It does not change the measured result in `verification-and-automation.md` ("Clicks on ScriptViews cannot be automated through the MCP bridge"): an external harness still needs a way to find the `ScriptView` root and target the real clicked widget, and the bridge measured on 2026-08-29 had none.

---

## Versions, branches and dependencies

- The active branch of the framework's repository is `production` (its default branch), not `master`. Not checked against the Workshop copy: the Steam Workshop build (item 2545327648) tracks `staging`, and the MVC and animator files are byte identical between the two branches (the 31 file difference between them touches nothing under `MVC\` or `!Core\WidgetAnimator*`).
- In the repository the scripts live under `DabsFramework/Scripts/3_Game/DabsFramework/MVC/` (capital `Scripts`, and a second `DabsFramework` folder).
- There are no releases or tags. To detect the framework version from script, use `#ifdef DABSFRAMEWORK_1_51`, which is defined at the top of `MVC\ScriptedViewBase.c` (line 1). Not checked against the Workshop copy: `Version.hpp` is stuck at 1.5 on both branches.
- The mod's `CfgPatches` classes are `DF_Scripts` (which requires `DZ_Scripts` and `DF_GUI`) and `DF_GUI`. A mod requires those. `DabsFramework` is only the `CfgMods` name and is not a patch class.
