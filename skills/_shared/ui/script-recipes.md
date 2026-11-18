# UI script recipes: auto binding, events, input and cursor, flags, widget types, text styling

Short, copyable building blocks for UI script: binding widget fields by name, the event signatures, locking input and showing the cursor, background blur, runtime alignment flags, a quick table of widget types, passing layout parameters to a script class, the two text styling branches, the Dabs essentials, a layout registry, and registering styles, imagesets and defines.

**How facts are marked here.** A `P:\` path with a line was checked on `P:\` (DayZ 1.30). "group mod pattern" means third-party mod behaviour (a closed source group and map mod and its core library), not vanilla and not checked on `P:\`. Dabs facts are framework facts; the checked details are in `dabs-mvc-internals.md`. The checked vanilla references for the same ground are `skills/_shared/enscript/references/widget_api.md` and `skills/_shared/enscript/references/gui_layout.md`; this file adds the recipes around them.

---

## Contents

- [Auto widget binding](#auto-widget-binding-connectclasswidgetvariables-group-mod-pattern)
- [Event signatures](#event-signatures)
- [Input and cursor management](#input-and-cursor-management)
- [Widget alignment flags](#widget-alignment-flags-group-mod-hex-values)
- [Widget types quick reference](#widget-types-quick-reference)
- [scriptclass and the reference keyword](#scriptclass-and-the-reference-keyword)
- [Text styling: two sibling branches](#text-styling-two-sibling-branches)
- [Dabs Framework essentials](#dabs-framework-essentials)
- [Layout registry pattern](#layout-registry-pattern-the-group-mod)
- [Styles, imagesets and defines in config.cpp](#styles-imagesets-and-defines-in-configcpp)

## Auto widget binding: ConnectClassWidgetVariables (group mod pattern)

Fills a class's `Widget` typed member variables from the layout widgets with the same names. It removes dozens of `FindAnyWidget` calls.

```c
// Global function (write your own, or use the one from a framework):
bool ConnectClassWidgetVariables(Class instance, Widget layoutRoot,
    TStringArray ignored = null, TStringArray renames = null) {
    typename me = instance.Type();
    for (int i = 0; i < me.GetVariableCount(); i++) {
        string varName = me.GetVariableName(i);
        typename type = me.GetVariableType(i);
        if (type.IsInherited(Widget)) {
            string widgetName = varName;
            if (renames) {
                int idx = renames.Find(varName);
                if (idx != -1) widgetName = renames.Get(idx + 1);
            }
            if (ignored && ignored.Find(varName) != -1) continue;
            Widget w = layoutRoot.FindAnyWidget(widgetName);
            if (w) EnScript.SetClassVar(instance, varName, 0, w);
        }
    }
    return true;
}

// Usage:
class MyMenu : UIScriptedMenu {
    TextWidget titleText;      // bound to the widget named "titleText"
    ButtonWidget btnClose;     // bound to "btnClose"
    EditBoxWidget searchInput; // bound to "searchInput"

    override Widget Init() {
        layoutRoot = GetGame().GetWorkspace().CreateWidgets(LAYOUT_PATH);
        ConnectClassWidgetVariables(this, layoutRoot);
        return layoutRoot;
    }
}
```

It uses reflection: `GetVariableCount`, `GetVariableName` and `GetVariableType` on `typename` (`P:\scripts\1_core\proto\enconvert.c:586-588`) and `EnScript.SetClassVar` (`P:\scripts\1_core\proto\enscript.c:211`). `renames` is a flat list of pairs (variable name, then widget name), and `ignored` lists variables to skip. Dabs Framework does the same job with `LoadWidgetsAsVariables` (`dabs-mvc-internals.md`). The sketch above names its members without the `m_` prefix because the names must equal the widget names; in your own code follow the style guide and pass a rename list, or name the widgets to match.

## Event signatures

All from `ScriptedWidgetEventHandler` at `P:\scripts\1_core\proto\enwidgets.c:656-686`. Each returns `bool`.

```
OnClick(Widget w, int x, int y, int button)
OnDoubleClick(Widget w, int x, int y, int button)
OnMouseEnter(Widget w, int x, int y)                // 3 params
OnMouseLeave(Widget w, Widget enterW, int x, int y) // 4 params: not the same shape as OnMouseEnter
OnMouseWheel(Widget w, int x, int y, int wheel)
OnMouseButtonDown(Widget w, int x, int y, int button)
OnMouseButtonUp(Widget w, int x, int y, int button)
OnFocus(Widget w, int x, int y)
OnFocusLost(Widget w, int x, int y)
OnChange(Widget w, int x, int y, bool finished)
OnKeyDown(Widget w, int x, int y, int key)
OnKeyUp(Widget w, int x, int y, int key)
OnKeyPress(Widget w, int x, int y, int key)
OnDrag(Widget w, int x, int y)
OnDragging(Widget w, int x, int y, Widget reciever)
OnDraggingOver(Widget w, int x, int y, Widget reciever)   // line 678; missing from older lists
OnDrop(Widget w, int x, int y, Widget reciever)
OnDropReceived(Widget w, int x, int y, Widget reciever)
OnResize(Widget w, int x, int y)
OnChildAdd(Widget w, Widget child)
OnChildRemove(Widget w, Widget child)
OnUpdate(Widget w)
OnSelect(Widget w, int x, int y)
OnItemSelected(Widget w, int x, int y, int row, int column, int oldRow, int oldColumn)
OnModalResult(Widget w, int x, int y, int code, int result)
OnController(Widget w, int control, int value)
OnEvent(EventType eventType, Widget target, int parameter0, int parameter1)
```

Return true to consume the event and stop it from travelling further. `OnMouseLeave` has four parameters and `OnMouseEnter` three; an `OnMouseLeave` written with three is a different method and is never called. There is no `OnMouseMove`.

## Input and cursor management

```c
// Lock input. It stacks: each +1 needs exactly one -1.
GetGame().GetInput().ChangeGameFocus(1);

// Show the cursor
GetGame().GetUIManager().ShowUICursor(true);

// Block player actions but keep the UI working
HumanInputController hic = man.GetInputController();
hic.SetDisabled(true);
```

- `ChangeGameFocus(int add, int input_device = -1)` is at `P:\scripts\3_game\tools\input.c:20`, `ShowUICursor(bool visible)` at `P:\scripts\3_game\tools\uimanager.c:244`, and `HumanInputController.SetDisabled(bool pState)` at `P:\scripts\3_game\human.c:22`.
- ESC (not yet checked in game): `LocalPress` on `UAUIBack` does not fire while `ChangeGameFocus` is active. Intercept the key in `MissionGameplay.OnKeyPress(int key)` (`P:\scripts\5_mission\mission\missiongameplay.c:742`) and compare with `KeyCode.KC_ESCAPE` (`P:\scripts\1_core\proto\ensystem.c:158`). Compare against the name, not the number 1.

### Mission level input blocking (group mod pattern)

```c
Mission mission = g_Game.GetMission();
mission.AddActiveInputExcludes({"movement", "aiming", "menu"});
// Restore:
mission.RemoveActiveInputExcludes({"menu", "movement", "aiming"}, true);
mission.RemoveActiveInputRestriction(EInputRestrictors.INVENTORY);
mission.RefreshExcludes();
mission.PlayerControlEnable(true);
```

These are declared on `Mission` at `P:\scripts\3_game\gameplay.c:795-802`; note that `PlayerControlEnable` carries the comment `//!deprecated` there. `EInputRestrictors` (`INVENTORY`, `MAP`, `SURRENDER_TRANSITION`) is at `P:\scripts\3_game\constants.c:116-121`. The exclude names come from `<exclude>` groups in `bin/specific.xml`.

### Background blur

```c
// The current vanilla way (preferred): the PPE requester system.
PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Start();  // in OnShow
PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Stop();   // in OnHide

// Legacy route. It works, and DayZ Expansion still uses it:
PPEffects.SetBlurMenu(0.5);   // blur behind the menu
PPEffects.SetBlurMenu(0);     // remove it on close
```

Vanilla `InventoryMenu` uses the requester: `Start()` in `OnShow` at `P:\scripts\5_mission\gui\inventorymenu.c:109` and `Stop()` in `OnHide` at `P:\scripts\5_mission\gui\inventorymenu.c:146`. `PPEffects.SetBlurMenu(float value)` is at `P:\scripts\3_game\ppeffects.c:220`, but vanilla starts that class with the comment "DEPRECATED, left in for legacy purposes only" on its `PPEffects.Init()` call (`P:\scripts\5_mission\mission\missiongameplay.c:122`). Use the requester in new code.

### UIManager operations

```c
g_Game.GetUIManager().CloseAll();
g_Game.GetUIManager().ShowUICursor(true);
g_Game.GetUIManager().IsCursorVisible();
UIScriptedMenu current = g_Game.GetUIManager().GetMenu();
```

`IsCursorVisible()` is at `P:\scripts\3_game\tools\uimanager.c:48`, `GetMenu()` at `P:\scripts\3_game\tools\uimanager.c:59` and `CloseAll()` at `P:\scripts\3_game\tools\uimanager.c:78`.

**Dabs alternative.** A `ScriptViewMenu` handles game focus, the cursor and the menu hierarchy when it opens. It does **not** handle ESC (`CanCloseWithEscape()` has no callers; wire ESC yourself), and it does not release game focus when it closes (the `ChangeGameFocus(-1, ...)` calls in its destructor are commented out), so check the input state after closing. The full contract is in `dabs-mvc-internals.md`, "ScriptViewMenu". Corrected; older text said it handles ESC.

## Widget alignment flags (group mod hex values)

Third-party mod values (the group mod production code); they cannot be checked against the engine. The `WidgetFlags` enum (`P:\scripts\1_core\proto\enwidgets.c:57-85`) declares 26 names with no explicit values and no positional alignment flags at all.

- The odd `V_` and `H_` prefixes are that mod's own naming (in its `MyWidgetUtils.c`): `V_*` are the horizontal values and `H_*` the vertical ones. The Horizontal and Vertical labels below are the correct meaning.
- **Never compute `WidgetFlags` hex values by hand, and never mix these alignment values with `WidgetFlags.*` names.** Under a naive `1 << index` reading, 0x100000 would collide with `DISABLED` and 0x400000 with `CLIPCHILDREN`. Vanilla only ever uses the symbolic names.
- Treat the values as an opaque recipe that works in that mod.

```c
// Horizontal: V_LEFT=0x00, V_CENTER=0x140, V_RIGHT=0x100 (mask: 0x1C0)
// Vertical:   H_TOP=0x00,  H_CENTER=0xA00, H_BOTTOM=0x800 (mask: 0xE00)
// Clear mask for position: 0xFC0
// Text: TEXT_LEFT=0x0, TEXT_CENTER=0x100000, TEXT_RIGHT=0x400000 (mask: 0x500000)

// Change alignment at runtime:
widget.ClearFlags(0xFC0);
widget.SetFlags(0x140);  // V_CENTER
widget.Update();         // call Update() after changing flags

// Change text alignment at runtime:
widget.ClearFlags(0x500000);
widget.SetFlags(0x100000);  // TEXT_CENTER
widget.Update();
```

## Widget types quick reference

"Two way" is the Dabs Framework `Two_Way_Binding` support for that widget (`dabs-mvc-internals.md`); it means nothing in vanilla UI. Script classes are in `P:\scripts\1_core\proto\enwidgets.c` unless a row says otherwise; the preview, HTML and map widgets are in `P:\scripts\3_game\gameplay.c` (`PreviewWidget` at line 276, `HtmlWidget` at line 316, `MapWidget` at line 322).

| Layout class | Script class | Visible? | Two way | Notes |
|---|---|---|---|---|
| FrameWidgetClass | Widget | no | — | A node in the hierarchy only |
| ImageWidgetClass | ImageWidget | yes | no | Needs a loaded image before a script color shows |
| TextWidgetClass | TextWidget | text | no | SetText, SetBold, SetItalic, SetShadow. Does not wrap |
| ButtonWidgetClass | ButtonWidget | by style | yes | SetState(bool); SetColor works without an image |
| EditBoxWidgetClass | EditBoxWidget | yes | yes | GetText; OnChange on every keystroke |
| MultilineEditBoxWidgetClass | MultilineEditBoxWidget | yes | yes | GetLinesCount, GetCarriageLine, GetCarriagePos |
| RichTextWidgetClass | RichTextWidget | text | no | Markup: b, i, color, image, outline, shadow |
| CheckBoxWidgetClass | CheckBoxWidget | yes | yes | IsChecked, SetChecked |
| SliderWidgetClass | SliderWidget | yes | yes | SetMinMax, GetCurrent, SetStep |
| ScrollWidgetClass | ScrollWidget | no | yes (holds a collection) | Full scroll API, VScrollToWidget(child) |
| GridSpacerWidgetClass | GridSpacerWidget | no | yes (holds a collection) | Grid that places its children |
| WrapSpacerWidgetClass | WrapSpacerWidget | no | yes (holds a collection) | Wrapping flow layout |
| CanvasWidgetClass | CanvasWidget | drawn | — | DrawLine, Clear |
| VideoWidgetClass | VideoWidget | yes | — | Load, Play, Pause, GetTime |
| MapWidgetClass | MapWidget | yes | — | ScreenToMap, MapToScreen, SetMapPos, GetMapPos, SetScale, GetScale, AddUserMark, ClearUserMarks |
| XComboBoxWidgetClass | XComboBoxWidget | yes | yes | AddItem, ClearAll, GetCurrentItem, SetCurrentItem, GetNumItems |
| TextListboxWidgetClass | TextListboxWidget | yes | yes | AddItem(text, userData, column, row = -1) returns int, SetItem, GetItemText(row, col, out), SetItemColor(row, col, color), RemoveRow, GetSelectedRow, SelectRow, GetNumItems, GetItemData, EnsureVisible, ClearItems |
| ProgressBarWidgetClass | ProgressBarWidget | yes | yes | SetCurrent(float); extends SimpleProgressBarWidget; no SetMinMax (GetMin and GetMax only read; the range comes from the layout or style). Vanilla is said to drive it with 0 to 100 (not checked on `P:\`) |
| MultilineTextWidgetClass | MultilineTextWidget | text | no | Plain text over several lines (TextWidget plus SetLineBreakingOverride). Use it for labels that wrap, with `wrap 1` |
| PasswordEditBoxWidgetClass | PasswordEditBoxWidget | yes | yes | EditBoxWidget plus SetHideText(bool) |
| HtmlWidgetClass | HtmlWidget | yes | no | RichTextWidget plus LoadFile(path); vanilla note and book UIs, for long scrolling documents |
| WindowWidgetClass | Widget | by style | — | Titled window chrome (the `WindowWidget` style block starts at line 1024 of `P:\gui\looknfeel\dayzwidgets.styles`). No `WindowWidget` script class is declared in `P:\scripts`; keep it as a `Widget` |
| SimpleProgressBarWidgetClass | SimpleProgressBarWidget | yes | — | Bar only style set; base of ProgressBarWidget |
| PreviewWidgetClass | PreviewWidget | 3D render | — | Base class for 3D renders in UI (ApplyToCamera, SetModelOrientation, SetModelPosition) |
| ItemPreviewWidgetClass | ItemPreviewWidget | 3D item | no | SetItem, GetItem, SetView, GetView, SetForceFlipEnable, SetForceFlip |
| PlayerPreviewWidgetClass | PlayerPreviewWidget | 3D player | no | UpdateItemInHands, SetPlayer, GetDummyPlayer, Refresh |

Dabs's own registry gives `ProgressBarWidget` and `PasswordEditBoxWidget` a two way controller, so the column above marks both yes.

## scriptclass and the reference keyword

When a layout widget has `scriptclass "MyHandler"`, the engine creates a `MyHandler` and calls its `OnWidgetScriptInit`. Fields marked `reference` are filled from the layout's `ScriptParamsClass` before that call.

```c
class MyValidator : ScriptedWidgetEventHandler {
    reference int maxLength;     // 'reference' = filled from the layout's ScriptParams
    reference string pattern;

    void OnWidgetScriptInit(Widget w) {
        // w is the widget this is attached to; maxLength and pattern are already set
        w.SetHandler(this);
    }
}
```

Layout side:

```
EditBoxWidgetClass myInput {
    scriptclass "MyValidator"
    { ScriptParamsClass { maxLength 50   pattern "[a-z]+" } }
}
```

Vanilla does the same in `SizeToChild`: `reference` fields at `P:\scripts\3_game\gui\containers\sizetochild.c:3-7` and `OnWidgetScriptInit(Widget w)` at `P:\scripts\3_game\gui\containers\sizetochild.c:14`.

## Text styling: two sibling branches

`TextWidget` and `UIWidget` are siblings under `Widget`, and each has its own set of text methods. Corrected: older notes listed the `UIWidget` getters under `TextWidget`.

```c
// TextWidget branch (TextWidget, RichTextWidget, MultilineTextWidget):
widget.SetTextExactSize(16);           // needs the "exact text" flag; 0 = original size
widget.SetOutline(size, argbColor);    // no "Text" prefix on this branch
widget.SetShadow(size, color, opacity, offsetX, offsetY);
widget.SetBold(true);  widget.SetItalic(true);
int w, h;
widget.GetTextSize(w, h);              // the drawn text size in pixels
// Getters: GetOutlineSize, GetOutlineColor, GetShadowSize, GetShadowColor, GetShadowOpacity, GetShadowOffset(out, out)
// Text color on this branch is plain Widget.SetColor().

// UIWidget branch (Button, EditBox, CheckBox, Slider, XComboBox, list boxes, spacers):
btn.SetTextColor(color);               // the way to color a button or edit box label
                                       // (Widget.SetColor colors the widget body)
btn.SetTextOutline(size, argb);  btn.SetTextShadow(size, argb, opacity, offX, offY);
btn.SetTextItalic(true);  btn.SetTextBold(true);
// Getters: GetTextOutlineSize, GetTextOutlineColor, GetTextShadowSize, GetTextShadowColor,
// GetTextShadowOpacity, GetTextShadowOffsetX, GetTextShadowOffsetY, GetTextItalic, GetTextBold.
// These do not exist on TextWidget and will not compile there.

// EditBoxWidget.GetText() returns the string directly (no out parameter)
string text = editBox.GetText();
// MultilineEditBoxWidget uses an out parameter:
string text2; multiEditBox.GetText(text2);

// ImageWidget:
bool ok = img.LoadImageFile(0, path);  // returns bool
int iw, ih; img.GetImageSize(0, iw, ih);

// Position and size in screen pixels (any widget):
widget.SetScreenPos(px, py);  widget.SetScreenSize(pw, ph);
widget.GetScreenPos(outX, outY);  widget.GetScreenSize(outW, outH);

// Visibility:
widget.IsVisibleHierarchy();   // checks the whole parent chain
```

Where each is declared: the `TextWidget` class at `P:\scripts\1_core\proto\enwidgets.c:189-217`, the `UIWidget` class at `P:\scripts\1_core\proto\enwidgets.c:323-339`, `EditBoxWidget.GetText()` at `P:\scripts\1_core\proto\enwidgets.c:349`, `MultilineEditBoxWidget.GetText(out string text)` at `P:\scripts\1_core\proto\enwidgets.c:318`, `LoadImageFile` at `P:\scripts\1_core\proto\enwidgets.c:257`, `GetImageSize` at `P:\scripts\1_core\proto\enwidgets.c:260`, `SetScreenPos` and `SetScreenSize` at `P:\scripts\1_core\proto\enwidgets.c:142-143`, `GetScreenPos` and `GetScreenSize` at `P:\scripts\1_core\proto\enwidgets.c:153-154`, and `IsVisibleHierarchy()` at `P:\scripts\1_core\proto\enwidgets.c:139`.

## Dabs Framework essentials

Framework facts; the checked detail is in `dabs-mvc-internals.md`.

### ScriptView lifecycle

1. The constructor calls `CreateWidget(null)`, then `LoadWidgetsAsVariables`, then creates or finds the controller.
2. `GetLayoutRoot()` is valid right after the constructor.
3. `UseUpdateLoop()` returns true by default; override it to return false to switch the per frame `Update` off.
4. The destructor removes the update, deletes the controller, unlinks the layout and removes the view from `All`.

### Relay_Command (a function as the command)

```
// In the .layout:
Relay_Command "OnSaveExecute"

// In the controller (bool return, a CommandArgs parameter):
bool OnSaveExecute(ButtonCommandArgs args)
{
    // logic
    return true;
}
```

Dabs tries, in order: a `RelayCommand` variable of that name, a `RelayCommand` type of that name, then a function call through `g_Script.CallFunction`.

### WidgetAnimator (built into Dabs; do not write your own tween)

```
WidgetAnimator.Animate(widget, WidgetAnimatorProperty.COLOR_A, 1.0, 300);
WidgetAnimator.AnimateEx(widget, WidgetAnimatorProperty.POSITION_Y, 0, 300, WidgetAnimatorEasing.EASE_OUT_SINE);
WidgetAnimator.AnimateColor(widget, endColor, 300, BlendMode.NORMAL);
WidgetAnimator.CancelAnimate(widget);
```

30 easing curves. Properties: `POSITION_X/Y`, `SIZE_W/H`, `ROTATION_X/Y/Z`, `COLOR_A/R/G/B/H/S/V`, `EXACT_TEXT`. Times are milliseconds.

### NotifyPropertyChanged

- `NotifyPropertyChanged("X")` updates only the bindings whose `Binding_Name` is `"X"`.
- `NotifyPropertyChanged("")` updates all of them (expensive; avoid).
- `NotifyPropertyChanged("X", false)` skips the `PropertyChanged` callback, which prevents recursion.
- Sub properties: `NotifyPropertyChanged("m_Obj.value")`; dot notation is supported.

Dabs `LinearColor` has about 150 named colors, HSV, `Lerp` and blend modes.

## Layout registry pattern (the group mod)

Central layout management with paths another mod can override:

```c
class MyLayoutManager {
    static ref MyLayoutManager s_Instance;
    ref map<string, string> m_Layouts = new map<string, string>();

    static MyLayoutManager Get() {
        if (!s_Instance) s_Instance = new MyLayoutManager();
        return s_Instance;
    }
    void RegisterLayout(string name, string path) { m_Layouts.Insert(name, path); }
    void OverwriteLayout(string name, string path) { m_Layouts.Set(name, path); }
    Widget CreateLayout(string name, Widget parent = null) {
        string path;
        if (!m_Layouts.Find(name, path)) return null;
        return g_Game.GetWorkspace().CreateWidgets(path, parent);
    }
}
// Another mod overrides a layout with:
// modded class MyLayoutManager { void MyLayoutManager() { OverwriteLayout("X", "newpath"); } }
```

## Styles, imagesets and defines in config.cpp

A `.styles` file is XML (unlike a `.layout`):

```xml
<WidgetStyles>
    <Widget Name="PanelWidget">
        <Style Name="MyStyle" Font="gui/fonts/MyFont" ImageSet="my_set" Color="4294967295">
            <State Name="Normal">
                <Item Name="Top" Image="pixel" />
                <Item Name="Center" Image="" />
                <!-- 9-slice: Top, Right, Bottom, Left, the four corners and Center -->
            </State>
        </Style>
    </Widget>
</WidgetStyles>
```

The vanilla file is `P:\gui\looknfeel\dayzwidgets.styles`; its `PanelWidget` block starts at line 3233. The full dissection is `styles-format.md`.

Register style and imageset files in `config.cpp`, inside `CfgMods`, in your mod's `class defs`:

```cpp
class widgetStyles { files[] = { "MyMod/gui/styles/mystyles.styles" }; };
class imageSets { files[] = { "MyMod/gui/imagesets/my_set.imageset" }; };
```

`/dayz-build-imageset` builds the imageset file and its atlas; the `class imageSets` entry is described in `skills/_shared/enscript/references/widget_api.md` ("Imagesets in layouts and script").

Custom preprocessor defines, also in `CfgMods`:

```cpp
class CfgMods {
    class MyMod {
        defines[] = { "MY_FEATURE_FLAG" };
    };
};
// Then in scripts: #ifdef MY_FEATURE_FLAG ... #endif
```

Useful for feature flags that other mods can test for. A real example and the naming rules are in `skills/_shared/enscript-style/naming.md`.
