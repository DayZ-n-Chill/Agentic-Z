# Reference: Widget Script API

The script side of DayZ UI: every widget class a mod uses, its methods, widget events and `ScriptedWidgetEventHandler`, loading layouts, `UIScriptedMenu` and imagesets. The `.layout` file format itself is in `gui_layout.md`.

Every fact here is vanilla and was read from these files on `P:\`:

- `P:\scripts\1_core\proto\enwidgets.c`: widget classes, `WidgetFlags`, `ScriptedWidgetEventHandler` (line 656), `LoadWidgetImageSet` (line 692).
- `P:\scripts\1_core\proto\proto.c`: `ARGB` and `ARGBF`.
- `P:\scripts\3_game\tools\uiscriptedmenu.c`: `UIMenuPanel` and `UIScriptedMenu`.
- `P:\scripts\3_game\tools\uimanager.c`: `UIManager`.
- `P:\scripts\3_game\gui\effects\hovereffect.c`: a handler attached from a layout's `scriptclass`.
- `P:\scripts\5_mission\mission\missionbase.c`: `CreateScriptedMenu(int id)` (line 198).

Check a method against `enwidgets.c` before you rely on it. DayZ updates add and remove methods.

---

## Widget classes

Script classes and their parents, from `enwidgets.c`. The layout class is the script class name plus `Class` (`TextWidget` is `TextWidgetClass` in a `.layout`). Cast with `Type.Cast(root.FindAnyWidget("name"))`.

| Script class | Parent | Methods a mod uses |
|---|---|---|
| `Widget` | `Managed` | See "Methods on every widget". Frame and panel widgets are plain `Widget` in script. |
| `TextWidget` | `Widget` | `SetText`, `SetTextFormat`, `SetTextExactSize`, `SetOutline`, `SetShadow`, `SetBold`, `SetItalic`, `GetTextSize`, `SetTextProportion` |
| `MultilineTextWidget` | `TextWidget` | `SetLineBreakingOverride` |
| `RichTextWidget` | `TextWidget` | `GetContentHeight`, `SetContentOffset`, `GetNumLines`, `ElideText` |
| `ImageWidget` | `Widget` | `LoadImageFile(int num, string name)`, `SetImage(int num)`, `GetImage`, `GetImageSize`, `LoadMaskTexture`, `SetMaskProgress` |
| `MultilineEditBoxWidget` | `TextWidget` | `GetText(out string)`, `GetLinesCount`, `SetLine`, `GetLine` |
| `UIWidget` | `Widget` | Text styling for controls: `SetTextColor`, `SetTextOutline`, `SetTextShadow`, `SetTextBold`, `SetTextItalic` |
| `EditBoxWidget` | `UIWidget` | `GetText()` returns the string, `SetText` |
| `PasswordEditBoxWidget` | `EditBoxWidget` | `SetHideText` |
| `ButtonWidget` | `UIWidget` | `SetText`, `GetText(out string)`, `GetState`, `SetState` (toggle buttons), `SetTextHorizontalAlignment` |
| `CheckBoxWidget` | `UIWidget` | `IsChecked`, `SetChecked`, `SetText` |
| `SliderWidget` | `UIWidget` | `SetMinMax`, `GetCurrent`, `SetCurrent`, `SetStep` |
| `SimpleProgressBarWidget` | `UIWidget` | `GetMin`, `GetMax`, `GetCurrent`, `SetCurrent` |
| `ProgressBarWidget` | `SimpleProgressBarWidget` | Same as its parent. |
| `XComboBoxWidget` | `UIWidget` | `AddItem`, `ClearAll`, `SetItem`, `RemoveItem`, `GetNumItems`, `SetCurrentItem`, `GetCurrentItem` |
| `BaseListboxWidget` | `UIWidget` | `ClearItems`, `GetNumItems`, `SelectRow`, `GetSelectedRow`, `RemoveRow`, `EnsureVisible` |
| `TextListboxWidget` | `SimpleListboxWidget` | `AddItem(text, userData, column, row = -1)`, `SetItem`, `GetItemText`, `GetItemData`, `SetItemColor` |
| `SpacerBaseWidget` | `UIWidget` | `AddChildAfter` |
| `GridSpacerWidget`, `WrapSpacerWidget` | `SpacerWidget` | `SetContentAlignmentH`, `SetContentAlignmentV`. Children are placed for you. |
| `ScrollWidget` | `SpacerBaseWidget` | `VScrollToPos`, `VScrollToPos01`, `VScrollToWidget`, `VScrollStep`, `GetContentHeight`, the `H` versions |
| `CanvasWidget` | `Widget` | `DrawLine`, `Clear` |
| `VideoWidget` | `Widget` | `Load`, `Play`, `Pause`, `Stop`, `Unload` |
| `RenderTargetWidget`, `RTTextureWidget` | `Widget` | Render targets. Rare in mods. |

`ItemPreviewWidget`, `PlayerPreviewWidget` and `MapWidget` are declared outside `enwidgets.c`. Their methods are in `gui_layout.md`; search for them in `P:\scripts\` before using a method that is not listed there.

## Methods on every widget

From `class Widget` in `enwidgets.c`:

- Finding: `FindAnyWidget(name)` searches the whole tree under the widget by name. `FindWidget("a.b.c")` takes a dotted path. `FindAnyWidgetById(userID)` uses the layout's `userID`.
- Tree: `GetParent`, `GetChildren` (first child), `GetSibling` (next sibling), `AddChild`, `RemoveChild`, `GetName`, `SetName`.
- Showing: `Show(bool)`, `IsVisible`, `IsVisibleHierarchy`, `Enable(bool)`.
- Look: `SetColor(int argb)`, `GetColor`, `SetAlpha(float)`, `SetRotation`.
- Place: `SetPos`, `GetPos(out x, out y)`, `SetSize`, `GetSize`, `GetScreenPos`, `GetScreenSize`, `SetScreenPos`, `SetScreenSize`. Units follow the widget's exact toggles: pixels when exact, fractions of the parent when not.
- Flags: `SetFlags(WidgetFlags)` adds flags, `ClearFlags` removes them, `GetFlags` reads them.
- Data: `SetUserData(Class)`, `GetUserData(out Class)`, `SetUserID`, `GetUserID`, `GetScript(out Class)` (the `scriptclass` instance).
- Events: `SetHandler(ScriptedWidgetEventHandler)`.
- Freeing: `Unlink()` destroys the widget and all its children.

`WidgetFlags` (from `enwidgets.c`) a mod sets in script: `VISIBLE`, `IGNOREPOINTER`, `DISABLED`, `NOFOCUS`, `CLIPCHILDREN`, `DRAGGABLE`, `EXACTPOS`, `EXACTSIZE`, `HEXACTPOS`, `VEXACTPOS`, `HEXACTSIZE`, `VEXACTSIZE`, `STRETCH`, `FLIPU`, `FLIPV`, `SOURCEALPHA`, `BLEND`, `ADDITIVE`.

Colors in script are one ARGB `int`. Use `ARGB(a, r, g, b)` with 0 to 255 values or `ARGBF(a, r, g, b)` with 0 to 1 values (both in `P:\scripts\1_core\proto\proto.c`). Layout files store `R G B A` floats instead.

---

## Widget events and ScriptedWidgetEventHandler

`ScriptedWidgetEventHandler` (`enwidgets.c` line 656) is a `Managed` class with one method per event. Override the ones you need. Each returns `bool`: return `true` when your code handled the event, `false` to leave it for others. Vanilla handlers such as `HoverEffect.OnMouseEnter` return `false` so the widget's other logic still runs.

| Event | Fires when |
|---|---|
| `OnClick(w, x, y, button)` | A button or other control is clicked. |
| `OnDoubleClick(w, x, y, button)` | A double click. |
| `OnChange(w, x, y, finished)` | An edit box, slider, check box or combo box value changes. `finished` is true when the edit is done. |
| `OnItemSelected(w, x, y, row, column, oldRow, oldColumn)` | A list box selection changes. |
| `OnSelect(w, x, y)` | A widget is selected. |
| `OnMouseEnter(w, x, y)`, `OnMouseLeave(w, enterW, x, y)` | The cursor enters or leaves the widget. |
| `OnMouseButtonDown`, `OnMouseButtonUp`, `OnMouseWheel` | Raw mouse input over the widget. |
| `OnFocus`, `OnFocusLost` | Keyboard or gamepad focus moves. |
| `OnKeyDown`, `OnKeyUp`, `OnKeyPress` | Key input while the widget has focus. |
| `OnController(w, control, value)` | Gamepad input. |
| `OnDrag`, `OnDragging`, `OnDraggingOver`, `OnDrop`, `OnDropReceived` | Drag and drop on widgets with `draggable 1`. |
| `OnResize`, `OnChildAdd`, `OnChildRemove`, `OnUpdate` | Layout changes and updates. |
| `OnModalResult(w, x, y, code, result)` | A dialog shown with `UIManager.ShowDialog` closes. |

A widget with `ignorepointer 1` gets no mouse events. That is the usual reason `OnClick` never fires.

### Attaching a handler from script

Set the handler on the root. Events from every child reach it, and `w` says which widget sent the event. Vanilla does this in `actiontargetscursor.c`, `continuousactionprogress.c` and `crosshairselector.c` (`m_Root.SetHandler(this)`).

```c
class MyMod_PanelHandler : ScriptedWidgetEventHandler
{
	protected Widget m_Root;
	protected ButtonWidget m_BtnClose;

	void MyMod_PanelHandler(Widget parent)
	{
		m_Root = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/panel.layout", parent);
		m_BtnClose = ButtonWidget.Cast(m_Root.FindAnyWidget("BtnClose"));
		m_Root.SetHandler(this);
	}

	void ~MyMod_PanelHandler()
	{
		if (m_Root)
			m_Root.Unlink();
	}

	override bool OnClick(Widget w, int x, int y, int button)
	{
		if (w == m_BtnClose)
		{
			m_Root.Show(false);
			return true;
		}

		return false;
	}
}
```

### Attaching a handler from the layout

Put the class name in the widget's `scriptclass` property. When the layout loads, the engine creates that class and calls its `void OnWidgetScriptInit(Widget w)`. Vanilla `HoverEffect` (`P:\scripts\3_game\gui\effects\hovereffect.c`) stores `w` and calls `w.SetHandler(this)` there. Other vanilla `scriptclass` values in `P:\gui\layouts\` are `SizeToChild`, `SizeToParent`, `TabberUI` and `RadialMenu`. Read the instance back with `widget.GetScript(out instance)`.

Values in a `ScriptParamsClass` block under the widget fill the script class's fields that are marked `reference`. Dabs Framework uses this for its bindings; see `../integrations/dabs_framework.md`.

---

## Loading layouts

```c
WorkspaceWidget ws = GetGame().GetWorkspace();
Widget root = ws.CreateWidgets("MyMod/gui/layouts/my_panel.layout");          // top level
Widget part = ws.CreateWidgets("MyMod/gui/layouts/row.layout", listParent);  // inside another widget
```

- `CreateWidgets(string layout, Widget parentWidget = NULL, bool immedUpdate = true)` returns the layout's root widget, or null when the file is not found or does not parse. Check it for null.
- The path starts with the mod's `$PBOPREFIX$` and uses forward slashes. Vanilla paths start with `gui/layouts/`, for example the constants in `P:\scripts\3_game\gui\widgetlayoutname.c`.
- `CreateWidget(WidgetType type, left, top, width, height, WidgetFlags flags, int color, int sort, Widget parentWidget)` makes one widget with no layout file. The type IDs end in `TypeID`, for example `FrameWidgetTypeID` and `TextWidgetTypeID`.
- Each `CreateWidgets` call makes a new copy. Make a list row once per row, and `Unlink()` the root when it is no longer needed. Hiding a widget does not free it.
- The server has no GUI. Code that creates widgets must not run there; guard it with `#ifndef SERVER` or check `GetGame().IsDedicatedServer()`, and guard classes that use GUI only types with `#ifndef NO_GUI` (see `../patterns/modded_class.md`).

---

## UIScriptedMenu: full screen menus

`UIScriptedMenu` (`P:\scripts\3_game\tools\uiscriptedmenu.c`) is the vanilla base for menus that take the mouse and keyboard. It extends `UIMenuPanel`, a `Managed` class, and declares the same handler events as `ScriptedWidgetEventHandler` itself (from line 238), so override `OnClick` and the others directly on the menu.

| Member | Use |
|---|---|
| `Widget layoutRoot` | Set it in `Init()`. |
| `Widget Init()` | Create the layout, find widgets, return `layoutRoot`. |
| `void OnShow()`, `void OnHide()` | The menu became visible or hidden. Lock and unlock controls here. |
| `void Update(float timeslice)` | Called each frame while the menu is shown. Keep it light. |
| `bool UseMouse()`, `bool UseKeyboard()` | Whether the menu takes the cursor and the keyboard. |
| `void LockControls()`, `void UnlockControls()` | Vanilla helpers that stop the player moving while the menu is open. |
| `void Close()` | Closes the menu. |
| `GetID()`, `SetID(int)` | The menu ID. |

Open a menu by ID through the `UIManager` (`P:\scripts\3_game\tools\uimanager.c`):

- `GetGame().GetUIManager().EnterScriptedMenu(id, parent)` asks the mission for the menu, then shows it. Vanilla calls it in `missiongameplay.c` (for example `EnterScriptedMenu(MENU_MAP, null)`).
- The mission builds the menu in `CreateScriptedMenu(int id)` (`missionbase.c` line 198, a `switch` on the ID). A mod adds its case with `modded class MissionBase` or `modded class MissionGameplay`, calls `super.CreateScriptedMenu(id)` first, and sets the menu's ID with `menu.SetID(id)` when it builds one.
- `ShowScriptedMenu(menu, parent)` shows a menu object you made yourself. `GetMenu()` returns the open menu. `CloseMenu(id)`, `Back()` and `CloseAll()` close menus.
- Pick a menu ID far above vanilla's `MENU_*` constants so it does not clash with another mod. `../examples/08_gui_menu.c` is a complete menu.

HUD elements that must not take the mouse are not menus. Create their layout under the HUD root once and update it, as `../examples/11_hud_plain_text.layout` and its script do.

---

## Imagesets in layouts and script

An imageset is one texture atlas plus a `.imageset` file that names rectangles in it. Vanilla imagesets are in `P:\gui\imagesets\` (for example `dayz_gui`). Build a mod's own with `/dayz-build-imageset`; its `SKILL.md` describes the generated file format.

Using an image:

- In a layout: `image0 "set:<set name> image:<image name>"` on an `ImageWidgetClass`. The set name is the `Name` inside the `.imageset` file, not the file name.
- In script: `ImageWidget.LoadImageFile(0, "set:dayz_gui image:cartridge_int")` loads into slot 0 (vanilla `P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c` line 1541). `SetImage(n)` switches between loaded slots.
- In rich text: `<image set="<set>" name="<image>" />` (vanilla `P:\scripts\3_game\tools\inpututils.c` line 178).

The engine must know a mod's imageset before a layout can use it. Register it in `config.cpp` under `CfgMods`:

```cpp
class CfgMods
{
	class MyMod
	{
		type = "mod";
		class defs
		{
			class imageSets
			{
				files[] = { "MyMod/gui/imagesets/my_icons.imageset" };
			};
		};
	};
};
```

Dabs Framework's own `config.cpp` registers its imagesets this way. Script can also load one at run time with `LoadWidgetImageSet(string filename)` (`enwidgets.c` line 692). When an icon is blank, check three things first: the `CfgMods` entry, the set `Name` and the image name.
