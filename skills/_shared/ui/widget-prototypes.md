# Widget base class and global calls

What every widget can do from script: the native methods of `class Widget`, what `SetRotation` and `SetTransform` really draw, the `WidgetFlags` enum, the global widget functions, `ControlID` and the widget type IDs. The methods of each widget class are in `widget-classes.md`, the 3D preview widgets in `preview-widgets.md`, and the short overview with events and imagesets in `skills/_shared/enscript/references/widget_api.md`.

Every prototype here was compared, name and signature, with `class Widget` at `P:\scripts\1_core\proto\enwidgets.c:107` and the declarations after it.

## class Widget

```c
// Identity
proto native string GetName();
proto native void SetName(string name);
proto native string GetTypeName();
proto native WidgetType GetTypeID();

// Visibility
proto native void Show(bool show, bool immedUpdate = true);
proto native void Enable(bool enable);
proto native bool IsVisible();            // this widget only
proto native bool IsVisibleHierarchy();   // :139, true only when every parent is visible too

// Flags
proto native int GetFlags();
proto native int SetFlags(int flags, bool immedUpdate = true);    // adds flags
proto native int ClearFlags(int flags, bool immedUpdate = true);  // removes flags

// Position and size relative to the parent, in layout units
proto native void SetPos(float x, float y, bool immedUpdate = true);
proto void GetPos(out float x, out float y);
proto native void SetSize(float w, float h, bool immedUpdate = true);
proto void GetSize(out float width, out float height);

// Position and size on the screen, in pixels (setters :142 and :143, getters :153 and :154)
proto native void SetScreenPos(float x, float y, bool immedUpdate = true);
proto void GetScreenPos(out float x, out float y);
proto native void SetScreenSize(float w, float h, bool immedUpdate = true);
proto void GetScreenSize(out float width, out float height);

// Color and alpha
proto native void SetColor(int color);    // ARGB
proto native int GetColor();
proto native void SetAlpha(float alpha);  // 0 to 1
proto native float GetAlpha();

// Transform
proto native void SetRotation(float roll, float pitch, float yaw, bool immedUpdate = true);
proto native vector GetRotation();
proto native void SetTransform(vector mat[4], bool immedUpdate = true);

// Draw order
proto native int GetSort();
proto native void SetSort(int sort, bool immedUpdate = true);

// Hierarchy
proto native Widget GetParent();
proto native Widget GetChildren();        // first child
proto native Widget GetSibling();         // next sibling
proto native void AddChild(Widget child, bool immedUpdate = true);
proto native void RemoveChild(Widget child);
proto native void Unlink();               // destroys the widget and all its children

// Search
proto native Widget FindWidget(string pathname);       // by path "a.b.c"
proto native Widget FindAnyWidget(string pathname);    // by name anywhere below
proto native Widget FindAnyWidgetById(int user_id);    // by userID

// Script and data
proto void GetScript(out Class data);
proto native void SetUserData(Class data);
proto void GetUserData(out Class data);
proto native int GetUserID();
proto native void SetUserID(int id);
proto native void SetHandler(ScriptedWidgetEventHandler eventHandler);

// Other
proto native bool IsControlClass();
proto native owned string GetStyleName();
proto native volatile void Update();      // call after changing flags

// Static: these are the player's settings, not the mod's
proto static void SetLV(float lv);
proto static void SetTextLV(float lv);
proto static void SetObjectLighting(float lighting);
proto static string TranslateString(string stringId);
```

Calls that are easy to get wrong:

- Never call `SetLV` or `SetTextLV` from a mod. Vanilla `SetHudBrightness` is exactly those two calls (`P:\scripts\3_game\dayzgame.c:3910` to `:3914`), fed from the player's HUD brightness option, so a mod that calls them overwrites that setting for every widget in the game. The engine gives both a range of -15 to 0, default 0 (`P:\scripts\1_core\proto\enwidgets.c:114` to `:117`). `SetObjectLighting` (0 to 1, default 1, `:118` and `:119`) lights 3D previews and is separate.
- `SetSort` sets the order outright, and a higher value draws on top. Only `SetFlags` adds and only `ClearFlags` takes away (`P:\scripts\1_core\proto\enwidgets.c:128` to `:131`). In a `.layout` the order is the `priority` attribute.
- `CreateWidget(type, left, top, width, height, flags, color, sort, parent)` is a `WorkspaceWidget` method, so call it on `GetGame().GetWorkspace()` (`P:\scripts\1_core\proto\enwidgets.c:176` to `:179`). Building from a `.layout` with `CreateWidgets` (`:181`) is the usual way.
- `SetRefresh(period, offset)` and `SetResolutionScale` exist only on `RenderTargetWidget` (`P:\scripts\1_core\proto\enwidgets.c:236` to `:240`).
- `Widget.TranslateString("#STR_MY_KEY")` needs no widget instance and translates several keys in one string.

## SetRotation and SetTransform in game

Measured in game on 1.29 with a test mod; not repeated on 1.30.

- `SetTransform` (`P:\scripts\1_core\proto\enwidgets.c:156`) is declared but not linked: calling it throws "Function SetTransform not linked" every frame. Do not use it; there is no matrix route.
- `SetRotation` (`:146`) draws an affine result only, scale and shear. The sides never converge, so there is no keystone and no perspective.
- The third parameter rotates in the plane of the screen. Vanilla uses it that way: `m_LayoutRoot.SetRotation(0,0,Math.RAD2DEG * m_AngleRad,true)` (`P:\scripts\4_world\classes\hitindication\hitdirectionarrow.c:24`). A 79 by 45 image turned 30 degrees became an 88 by 76 box with 94% of its area kept; a rotation in the plane keeps the area, foreshortening multiplies it by the cosine. Read the result at least 10 seconds after the call; a reading taken sooner showed no effect.
- The first and second parameters cancel each other: 40 and 25 degrees together gave no change. The first and third combine: `(40, 0, 25)` gave a 25 degree turn plus foreshortening, with 72% of the area against cos 40 of 76.6%.
- Rotate a container, not the leaf: a rotated `ImageWidget` clips its own corners because its box does not grow, while a rotated parent turns the whole picture.
- A panel can be aimed at a tilted surface with foreshortening plus rotation, but never with perspective.

## WidgetFlags

`enum WidgetFlags` is at `P:\scripts\1_core\proto\enwidgets.c:57` to `:85`, 26 names with no explicit values. The comments below are the engine's, shortened.

| Flag | Meaning |
|---|---|
| `SOURCEALPHA`, `BLEND`, `ADDITIVE` | Alpha from the texture times the color alpha; blended; added |
| `VISIBLE` | Visible |
| `NOWRAP` | "Do not do texture wrapping" (`:63`); a texture flag, not text |
| `CENTER`, `VCENTER`, `RALIGN` | Text centred horizontally, vertically; text aligned right |
| `HEXACTPOS`, `VEXACTPOS`, `EXACTPOS` | Exact position per axis, or both |
| `HEXACTSIZE`, `VEXACTSIZE`, `EXACTSIZE` | Exact size per axis, or both |
| `NOFILTER`, `STRETCH`, `FLIPU`, `FLIPV`, `CUSTOMUV` | Texture filtering, stretch, flips, custom UVs |
| `IGNOREPOINTER`, `DISABLED`, `NOFOCUS` | No mouse events, disabled, cannot take focus |
| `CLIPCHILDREN`, `RENDER_ALWAYS`, `NOCLEAR`, `DRAGGABLE` | Clip children, draw even when hidden, no clear, can be dragged |

No flag turns text wrapping on. The other `wrap` names in the file are `WrapSpacerWidgetTypeID` (`:48`) and `class WrapSpacerWidget` (`:477`), a container. Wrapped text needs a `MultilineTextWidgetClass` (`text-sizing-and-rendering.md`).

Use the names only. Never write flag values in hex, and never mix the alignment values a third party mod uses with `WidgetFlags` names (`script-recipes.md`).

## Global functions

Declared at file level in `enwidgets.c`, from `GetWidgetUnderCursor` (`P:\scripts\1_core\proto\enwidgets.c:184`) on.

```c
proto native Widget GetWidgetUnderCursor();
proto native Widget CancelWidgetDragging();
proto native Widget GetDragWidget();
proto native void SetFocus(Widget w);                         // :698
proto native Widget GetFocus();                               // :702
proto native void SetModal(Widget w);                         // :700, no vanilla callers
proto native bool SetActiveWindow(Widget w, bool resetFocus); // :695, no vanilla callers
proto native void SetCursorWidget(Widget cursor);
proto native void ShowCursorWidget(bool show);
proto native void ReportMouse(int mousex, int mousey, Widget rootWidget);
proto native bool LoadWidgetImageSet(string filename);
proto native void LoadWidgetStyles(string filename);          // :693
proto native bool ReloadTexture(string path);
```

`GetMousePos(out int x, out int y)` and `GetScreenSize(out int x, out int y)` are in another file, `P:\scripts\1_core\proto\ensystem.c:329` to `:331`.

## ControlID

The `control` value of `OnController` events (`enum ControlID`, `P:\scripts\1_core\proto\enwidgets.c:639` to `:653`): `CID_NONE` 0, `CID_SELECT` 1, `CID_BACK` 2, `CID_LEFT` 3, `CID_RIGHT` 4, `CID_UP` 5, `CID_DOWN` 6, `CID_MENU` 7, `CID_DRAG` 8 (dragging on console), `CID_TABLEFT` 9, `CID_TABRIGHT` 10, `CID_RADIALMENU` 11, then `CID_COUNT`.

## Widget type IDs

The `*WidgetTypeID` constants (`TextWidgetTypeID` to `ScrollWidgetTypeID`, `P:\scripts\1_core\proto\enwidgets.c:6` to `:53`) are declared under `#ifdef DOXYGEN` and still usable: compiled vanilla code passes `FrameWidgetTypeID` (`P:\scripts\5_mission\mission\gameplayeffectwidgets\gameplayeffectwidgets.c:34`) and `RenderTargetWidgetTypeID` (`P:\scripts\2_gamelib\entities\rendertarget.c:63`) to `CreateWidget`. There is no enum of widget types to loop over; a factory that builds widgets by name maps names to these constants and never invents integer IDs.
