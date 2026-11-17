# Widget script API: every prototype, by class

The native methods of each widget class a mod calls, the `WidgetFlags` and `ControlID` enums, the global widget functions, the preview widgets, and what was measured about `SetRotation` and `SetTransform`. The shorter overview of the same classes, with events, menus and imagesets, is `skills/_shared/enscript/references/widget_api.md`; this file is the full prototype list.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). Every prototype in a code block below was compared, name and signature, with `class Widget` and the classes after it in `P:\scripts\1_core\proto\enwidgets.c:107` onward, or with `P:\scripts\3_game\gameplay.c` for the preview widgets; all of them exist there. "Measured" means the source author measured it on a running client (DayZ 1.29.163709 unless a line says otherwise); those results are not yet checked on `P:\` or in game here. Facts that come from LBmaster_Core, Dabs Framework or LFPowerGrid name the mod. "Rule 3" is rule 3 in `rules-and-checklist.md`.

## Contents

- [Widget (base class)](#widget-base-class)
- [SetRotation and SetTransform: what was measured](#setrotation-and-settransform-what-was-measured)
- [WidgetFlags](#widgetflags)
- [Text widgets](#text-widgets)
- [ImageWidget](#imagewidget)
- [Controls: button, edit box, check box, slider](#controls-button-edit-box-check-box-slider)
- [ScrollWidget](#scrollwidget)
- [Spacer widgets](#spacer-widgets)
- [Preview widgets](#preview-widgets)
- [CanvasWidget and VideoWidget](#canvaswidget-and-videowidget)
- [Global functions](#global-functions)
- [ControlID](#controlid)
- [Usage notes from LBmaster_Core](#usage-notes-from-lbmaster_core)
- [Text readback and widget type IDs](#text-readback-and-widget-type-ids)

---

## Widget (base class)

Every widget inherits these. `class Widget` is declared at `P:\scripts\1_core\proto\enwidgets.c:107`.

```
// Identity
proto native string GetName();
proto native void SetName(string name);
proto native string GetTypeName();
proto native WidgetType GetTypeID();

// Visibility
proto native void Show(bool show, bool immedUpdate = true);
proto native void Enable(bool enable);
proto native bool IsVisible();
proto native bool IsVisibleHierarchy();  // checks the whole parent chain

// Flags
proto native int GetFlags();
proto native int SetFlags(int flags, bool immedUpdate = true);   // ADDS flags
proto native int ClearFlags(int flags, bool immedUpdate = true); // REMOVES flags

// Position and size (logical coordinates)
proto native void SetPos(float x, float y, bool immedUpdate = true);
proto void GetPos(out float x, out float y);
proto native void SetSize(float w, float h, bool immedUpdate = true);
proto void GetSize(out float width, out float height);

// Position and size (screen coordinates)
proto native void SetScreenPos(float x, float y, bool immedUpdate = true);
proto void GetScreenPos(out float x, out float y);
proto native void SetScreenSize(float w, float h, bool immedUpdate = true);
proto void GetScreenSize(out float width, out float height);

// Color and alpha
proto native void SetColor(int color);     // ARGB int
proto native int GetColor();               // ARGB int
proto native void SetAlpha(float alpha);   // 0.0 to 1.0
proto native float GetAlpha();

// Transform
proto native void SetRotation(float roll, float pitch, float yaw, bool immedUpdate = true);
proto native vector GetRotation();         // returns (roll, pitch, yaw)
proto native void SetTransform(vector mat[4], bool immedUpdate = true);

// Z order
proto native int GetSort();
proto native void SetSort(int sort, bool immedUpdate = true);

// Hierarchy
proto native Widget GetParent();
proto native Widget GetChildren();         // first child
proto native Widget GetSibling();          // next sibling
proto native void AddChild(Widget child, bool immedUpdate = true);
proto native void RemoveChild(Widget child);
proto native void Unlink();                // DESTROYS the widget and ALL its children

// Search
proto native Widget FindWidget(string pathname);        // by path "a.b.c"
proto native Widget FindAnyWidget(string pathname);     // by name anywhere in the tree
proto native Widget FindAnyWidgetById(int user_id);     // by user ID

// Script and data
proto void GetScript(out Class data);
proto native void SetUserData(Class data);
proto void GetUserData(out Class data);
proto native int GetUserID();
proto native void SetUserID(int id);

// Event handler
proto native void SetHandler(ScriptedWidgetEventHandler eventHandler);

// Misc
proto native bool IsControlClass();
proto native string GetStyleName();        // vanilla declares it "proto native owned string"
proto native void Update();                // force an update; vanilla declares it "proto native volatile void"

// Global brightness, STATIC. These are the PLAYER's setting, not the mod's.
proto static void SetLV(float lv);         // widget brightness [-15, 0], default 0
proto static void SetTextLV(float lv);     // text brightness [-15, 0], default 0
proto static void SetObjectLighting(float lighting); // brightness of objects in widgets [0, 1], default 1
proto static string TranslateString(string stringId);
```

A mod must not call `SetLV` or `SetTextLV`. Vanilla `SetHudBrightness` is exactly those two calls (`P:\scripts\3_game\dayzgame.c:3910-3914`), fed from the player's HUD brightness option, so a mod that calls them overwrites the player's setting for every widget in the game.

## SetRotation and SetTransform: what was measured

Measured by the source author on 2026-08-22, DayZ 1.29.163709, with a probe mod (LFVUI_Spike). None of it is repeated here.

- **`SetTransform` is declared but not linked by the engine.** It is declared at `P:\scripts\1_core\proto\enwidgets.c:156`. Calling it threw a non-fatal VM exception, "Function SetTransform not linked", every frame. Do not use it; there is no matrix alternative.
- **`SetRotation` draws, but only an affine result (scale and shear).** It is declared at `P:\scripts\1_core\proto\enwidgets.c:146`. The width varied by 2 px or less between scanlines across 8 measurements: the sides never converge, so there is no keystone and no perspective.
- **Parameters 1 and 2 cancel each other.** Combining them (40 degrees and 25 degrees) returned the identity, measured twice with a single axis control.
- **Parameter 3 is rotation in the plane of the screen.** Vanilla uses it that way: `m_LayoutRoot.SetRotation(0,0,Math.RAD2DEG * m_AngleRad,true)` at `P:\scripts\4_world\classes\hitindication\hitdirectionarrow.c:24`. An earlier "no effect" reading was a capture that was taken too soon (6 s dwell). At 10 s dwell a 79x45 `ImageWidget` at 30 degrees became 88x76 (inside a MapWidget) and 88x77 (inside a root frame), with 94 to 95% of the area kept. That is the test that tells the two apart: rotation in the plane keeps the area, foreshortening multiplies it by the cosine.
- **Parameters 1 and 3 compose.** `(40, 0, 25)` gave a 25 degree rotation in the plane plus foreshortening, with 72% of the area against cos 40 = 76.6%. Only 1 and 2 cancel.
- **Rotate the container, not the leaf.** Rotating the `ImageWidget` itself clipped its corners (73% of the area; the box does not grow). Rotating an ancestor gave the full rotation.
- **A panel can be aimed at a tilted surface** with foreshortening plus rotation in the plane. What it cannot do is keystone. "Cannot project" means "cannot project with perspective".

## WidgetFlags

`enum WidgetFlags` is at `P:\scripts\1_core\proto\enwidgets.c:57-85`. It has 26 entries; the comments below are the engine's, shortened.

```
SOURCEALPHA    // alpha from texture * color alpha
BLEND          // texture blended with the surface
ADDITIVE       // texture added to the surface
VISIBLE        // widget is visible
NOWRAP         // no texture wrapping
CENTER         // centers text horizontally
VCENTER        // centers text vertically
HEXACTPOS      // exact horizontal position
VEXACTPOS      // exact vertical position
EXACTPOS       // both exact positions (engine comment: "physical resolution"; measured as 1/1080 of the screen height, Rule 3)
HEXACTSIZE     // exact horizontal size
VEXACTSIZE     // exact vertical size
EXACTSIZE      // both exact sizes
NOFILTER       // no texture filtering
RALIGN         // right alignment for text
STRETCH        // stretch the texture to fill
FLIPU          // flip the texture U axis
FLIPV          // flip the texture V axis
CUSTOMUV       // custom UV coordinates
IGNOREPOINTER  // ignore mouse and pointer events
DISABLED       // widget disabled
NOFOCUS        // cannot receive focus
CLIPCHILDREN   // clip children to the widget's bounds
RENDER_ALWAYS  // render even when not visible
NOCLEAR        // no clear
DRAGGABLE      // can be dragged
```

`NOWRAP` is a texture flag, not a text layout flag. Its engine comment is "Do not do texture wrapping" (`P:\scripts\1_core\proto\enwidgets.c:63`). The enum declares nothing for text wrapping. The only other `wrap` symbols in the file are `WrapSpacerWidgetTypeID` (`P:\scripts\1_core\proto\enwidgets.c:48`) and `class WrapSpacerWidget` (`P:\scripts\1_core\proto\enwidgets.c:477`), a widget type that flows its children and has nothing to do with `TextWidget`. So text wrapping cannot be switched on from script through any `WidgetFlags` value.

It cannot be switched on from the `.layout` either, on a `TextWidget`. Measured in game on 2026-08-22 (DayZDiag 1.29.163709): in one 260x150 box, a `TextWidgetClass` with `wrap 1` and one with `wrap 0` drew the same clipped single line, while a `MultilineTextWidgetClass` with `wrap 1` in the same box wrapped the same string to five lines. The attribute does nothing on a `TextWidget` by either route; wrapped text means `MultilineTextWidgetClass`. The full setup is in `text-sizing-and-rendering.md`, section "wrap does nothing on a TextWidget".

---

## Text widgets

### TextWidget (extends Widget)

`class TextWidget` is at `P:\scripts\1_core\proto\enwidgets.c:189`.

```
proto native void SetText(string text, bool immedUpdate = true);
proto void SetTextFormat(string text, void p1..p9);   // nine optional parameters, param1 to param9, each defaulting to NULL
proto native void SetTextExactSize(int size);    // needs the "exact text" flag in the layout
proto native void SetTextSpacing(int horiz, int vert);
proto native void SetTextOffset(int left, int top);
proto void GetTextSize(out int sx, out int sy);  // size in pixels
proto native float GetTextProportion();
proto native void SetTextProportion(float val);  // ratio of text height to widget height [0,1]

// Style
proto native void SetBold(bool bold);
proto native bool GetBold();
proto native void SetItalic(bool italic);
proto native bool GetItalic();

// Outline
proto native void SetOutline(int outlineSize, int argb = 0xFF000000);
proto native int GetOutlineSize();
proto native int GetOutlineColor();

// Shadow (vanilla gives every parameter after the size a default: 0xFF000000, 1, 0, 0)
proto native void SetShadow(int size, int argb, float opacity, float offX, float offY);
proto native int GetShadowSize();
proto native int GetShadowColor();
proto native float GetShadowOpacity();
proto void GetShadowOffset(out float sx, out float sy);
```

### RichTextWidget (extends TextWidget)

`class RichTextWidget` is at `P:\scripts\1_core\proto\enwidgets.c:224`.

Reported by the source (not yet checked here): it supports the markup tags `<b>`, `<i>`, `<color rgba="R,G,B,A">`, `<color hex="0xAARRGGBB">`, `<image set="..." name="..." scale="1" />`, `<outline>`, `<shadow>` and `<font>`. Tags must not overlap. Bold and italic need SDF fonts. Wrapping plus a new layout pass on every runtime resize is expensive; avoid it with long text.

```
proto native float GetContentHeight();
proto native float GetContentOffset();
proto native void SetContentOffset(float offset, bool snapToLine = false);
proto native void ElideText(int line, float maxWidth, string str);
proto native int GetNumLines();
proto native void SetLinesVisibility(int lineFrom, int lineTo, bool visible);
proto native float GetLineWidth(int line);
proto native float SetLineBreakingOverride(int mode);
```

### MultilineEditBoxWidget (extends TextWidget)

`class MultilineEditBoxWidget` is at `P:\scripts\1_core\proto\enwidgets.c:313`.

```
proto void GetText(out string text);
proto native void SetLine(int line, string text);
proto void GetLine(int line, out string text);
proto native int GetLinesCount();
proto native int GetCarriageLine();     // cursor line
proto native int GetCarriagePos();      // cursor character position
```

---

## ImageWidget

`class ImageWidget` (extends Widget) is at `P:\scripts\1_core\proto\enwidgets.c:247`.

```
proto native bool LoadImageFile(int num, string name, bool noCache = false);
proto native bool SetImage(int num);           // switch the active image (0 to 7)
proto native int GetImage();
proto void GetImageSize(int image, out int sx, out int sy);
proto native void SetImageTexture(int image, RTTextureWidget texture);
proto native void SetUV(float uv[4][2]);       // custom UV (needs the CUSTOMUV flag)

// Alpha mask (reveal and transition effects)
proto native bool LoadMaskTexture(string resource);
proto native float GetMaskProgress();
proto native void SetMaskProgress(float value);         // [0,1]
proto native float GetMaskTransitionWidth();
proto native void SetMaskTransitionWidth(float value);  // [0,1] softness
```

**Pattern for a colored background (as the source gives it):**

```
string tex = "#(argb,8,8,3)color(1,1,1,1,CO)";
img.LoadImageFile(0, tex);
img.SetColor(ARGB(alpha, r, g, b));
```

The source contradicts itself on this pattern. Rule 2 in `rules-and-checklist.md` records that on DayZ 1.29 the same `LoadImageFile` call with a procedural texture string failed with "Bad texture name" and left the widget without a texture (measured in LFPowerGrid, confirmed again on 2026-09-04). Vanilla script builds such strings only for item materials (`P:\scripts\4_world\static\miscgameplayfunctions.c:243` formats `"#(argb,8,8,3)color(%1,CO)"`), not for `LoadImageFile`. Until someone tests it in game here, use one of the fallbacks from rule 2: a 1x1 white `.edds`, or a style whose center is `WhitePixel` (`styles-format.md`).

---

## Controls: button, edit box, check box, slider

### ButtonWidget (extends UIWidget)

`class ButtonWidget` is at `P:\scripts\1_core\proto\enwidgets.c:381`.

```
proto native bool GetState();
proto native bool SetState(bool state);
proto native void SetText(string text);
proto void GetText(out string text);
proto native void SetTextOffset(float xoff, float yoff);
proto native void SetTextHorizontalAlignment(int align);
proto native void SetTextVerticalAlignment(int align);
proto native void SetColor(int color);   // inherited from Widget; works WITHOUT LoadImageFile
```

### EditBoxWidget (extends UIWidget)

`class EditBoxWidget` is at `P:\scripts\1_core\proto\enwidgets.c:347`.

```
proto string GetText();
proto native void SetText(string str);
// OnChange fires on every keystroke
// SetFocus(null) clears focus (the first ESC removes focus, the second closes the panel)
```

### CheckBoxWidget (extends UIWidget)

`class CheckBoxWidget` is at `P:\scripts\1_core\proto\enwidgets.c:418`.

```
proto native bool IsChecked();
proto native void SetChecked(bool checked);
proto native void SetText(string str);
```

### SliderWidget (extends UIWidget)

`class SliderWidget` is at `P:\scripts\1_core\proto\enwidgets.c:358`.

```
proto native void SetMinMax(float minimum, float maximum);
proto native float GetMin();
proto native float GetMax();
proto native float GetCurrent();
proto native void SetCurrent(float curr);
proto native float GetStep();
proto native void SetStep(float step);
```

---

## ScrollWidget

`class ScrollWidget` (extends SpacerBaseWidget) is at `P:\scripts\1_core\proto\enwidgets.c:481`. It scrolls both ways.

```
proto native float GetScrollbarWidth();
proto native bool IsScrollbarVisible();

proto native float GetContentWidth();
proto native float GetContentHeight();

// Vertical
proto native float GetVScrollPos();         // absolute position
proto native float GetVScrollPos01();       // normalized [0,1]
proto native bool VScrollStep(int steps);
proto native void VScrollToPos(float pos);
proto native void VScrollToPos01(float pos01);
proto native void VScrollToWidget(Widget child);   // scroll until the child shows

// Horizontal
proto native float GetHScrollPos();
proto native float GetHScrollPos01();
proto native bool HScrollStep(int steps);
proto native void HScrollToPos(float pos);
proto native void HScrollToPos01(float pos01);
proto native void HScrollToWidget(Widget child);
```

**Key layout properties:** `"Scrollbar V" 1` on the scroll widget and `"Size To Content V" 1` on its spacer child. A scroll widget with no spacer child does not scroll; `<skill-dir>\templates\scroll_list.layout` is a working pair.

---

## Spacer widgets

`class SpacerBaseWidget` is at `P:\scripts\1_core\proto\enwidgets.c:460`, `class SpacerWidget` at `P:\scripts\1_core\proto\enwidgets.c:465`, `class GridSpacerWidget` at `P:\scripts\1_core\proto\enwidgets.c:473` and `class WrapSpacerWidget` at `P:\scripts\1_core\proto\enwidgets.c:477`.

```
// SpacerBaseWidget
proto native void AddChildAfter(Widget child, Widget after, bool immedUpdate = true);

// SpacerWidget (extends SpacerBaseWidget)
proto native WidgetAlignment GetContentAlignmentH();
proto native void SetContentAlignmentH(WidgetAlignment alignment);
proto native WidgetAlignment GetContentAlignmentV();
proto native void SetContentAlignmentV(WidgetAlignment alignment);
```

`enum WidgetAlignment` (`P:\scripts\1_core\proto\enwidgets.c:88-95`): `WA_LEFT` (0), `WA_RIGHT` (1), `WA_CENTER` (2), `WA_TOP` (0), `WA_BOTTOM` (1).

- GridSpacer layout attributes: `Columns N`, `Rows N`, `Padding X`, `Margin X`, `"Size To Content H" 1` and `"Size To Content V" 1`.
- WrapSpacer layout attributes: the same, and it wraps children onto the next row by itself.
- Both work inside a `ScrollWidget` for dynamic lists.

---

## Preview widgets

`PreviewWidget`, `ItemPreviewWidget` and `PlayerPreviewWidget` draw a 3D model inside the UI (inventory slots, inspect windows, character selection). They are declared in `P:\scripts\3_game\gameplay.c:276-314`, not in `enwidgets.c`. The three blocks below are copied from that file (DayZ 1.30).

### PreviewWidget (extends Widget)

```c
// P:\scripts\3_game\gameplay.c:276-284
class PreviewWidget: Widget
{
	proto native void		ApplyToCamera(int cam);

	proto native void		SetModelOrientation(vector vOrientation);
	proto native vector		GetModelOrientation();
	proto native void		SetModelPosition(vector vPos);
	proto native vector		GetModelPosition();
};
```

### ItemPreviewWidget (extends PreviewWidget)

```c
// P:\scripts\3_game\gameplay.c:286-302
class ItemPreviewWidget: PreviewWidget
{
	proto native void SetItem(EntityAI object);
	proto native EntityAI GetItem();
	
	proto native int GetView();
	/**
	* 0 - default boundingbox_min + boundingbox_max + invView
	* 1 - boundingbox_min2 + boundingbox_max2 + invView2
	* 2 - boundingbox_min3 + boundingbox_max3 + invView3
	* ...	
	*/
	proto native void SetView(int viewIndex);
	
	proto native void SetForceFlipEnable(bool enable);
	proto native void SetForceFlip(bool value);
};
```

### PlayerPreviewWidget (extends PreviewWidget)

```c
// P:\scripts\3_game\gameplay.c:305-313
class PlayerPreviewWidget: PreviewWidget
{
	proto native void		UpdateItemInHands(EntityAI object);
	proto native void		SetPlayer(DayZPlayer player);
	//proto native void		SetPlayerType(string type);
	proto native DayZPlayer	GetDummyPlayer();
	
	proto native void		Refresh();
};
```

### What the 1.30 changelog says against what the scripts hold

1. **Ticket T181406 (`WorldToScreen` and `ScreenToWorld`).** The official DayZ 1.30 experimental changelog says: "Added: WorldToScreen and ScreenToWorld methods for ItemPreviewWidget and PlayerPreviewWidget classes (T181406)". The scripts do not declare them: `class PreviewWidget` and its two children at `P:\scripts\3_game\gameplay.c:276-314` hold only the methods above, and a search of every `.c` file under `P:\scripts` for `WorldToScreen` and `ScreenToWorld` finds nothing (checked here on DayZ 1.30; the source author found the same on build 1.30.164014). The feature presumably sits in the engine binary without a script binding. Do not call these methods from a mod.
2. **Disabling particles in preview widgets.** The changelog says: "Added: Possibility to disable specific attached particles inside of the player / item preview widgets". The source author found no `Particle` method in `gameplay.c` and no such property in the preview layouts; it is taken to be an internal ability of the renderer.

---

## CanvasWidget and VideoWidget

`class CanvasWidget` is at `P:\scripts\1_core\proto\enwidgets.c:341`.

```
proto native void DrawLine(float x1, float y1, float x2, float y2, float width, int color);
proto native void Clear();
```

`class VideoWidget` is at `P:\scripts\1_core\proto\enwidgets.c:543`.

```
proto native bool Load(string name, bool looping = false, int startTime = 0);
proto native void Unload();
proto native bool Play();
proto native bool Pause();
proto native bool Stop();
proto native bool SetTime(int time, bool preload);
proto native int GetTime();
proto native int GetTotalTime();
proto native void SetLooping(bool looping);
proto native bool IsPlaying();
proto native VideoState GetState();
proto native void DisableSubtitles(bool disable);
proto void SetCallback(VideoCallback cb, func fn);
```

---

## Global functions

Declared at file level in `enwidgets.c`: `GetWidgetUnderCursor` at `P:\scripts\1_core\proto\enwidgets.c:184`, the rest between lines 185 and 715.

```
proto native Widget GetWidgetUnderCursor();
proto native Widget CancelWidgetDragging();
proto native Widget GetDragWidget();
proto native void SetFocus(Widget w);
proto native Widget GetFocus();
proto native void SetModal(Widget w);
proto native void SetCursorWidget(Widget cursor);
proto native void ShowCursorWidget(bool show);
proto native bool SetActiveWindow(Widget w, bool resetFocus);
proto native void ReportMouse(int mousex, int mousey, Widget rootWidget);
proto native bool LoadWidgetImageSet(string filename);
proto native void LoadWidgetStyles(string filename);
proto native bool ReloadTexture(string path);

// Screen size (int version)
void GetScreenSize(out int w, out int h);

// Mouse position (int version)
void GetMousePos(out int x, out int y);
```

The two `int` versions are declared in another file: `GetMousePos` and `GetScreenSize` are `proto void` functions at `P:\scripts\1_core\proto\ensystem.c:329-331`.

---

## ControlID

For `OnController` events. `enum ControlID` is at `P:\scripts\1_core\proto\enwidgets.c:639-653`; it ends with `CID_COUNT`.

```
CID_NONE = 0
CID_SELECT = 1     // select or use the focused widget
CID_BACK = 2
CID_LEFT = 3       // navigation
CID_RIGHT = 4
CID_UP = 5
CID_DOWN = 6
CID_MENU = 7       // main menu
CID_DRAG = 8       // dragging on consoles
CID_TABLEFT = 9
CID_TABRIGHT = 10
CID_RADIALMENU = 11
```

---

## Usage notes from LBmaster_Core

How LBmaster_Core (a third-party mod) calls the vanilla API. The methods are vanilla and listed above; the flag bit values and the usage patterns are LBmaster's and are not yet checked on `P:\`.

### Text styling

```
widget.SetTextExactSize(16);                    // pixel size (not the font size)
widget.SetOutline(size, argbColor);             // text outline
widget.SetShadow(size, color, opacity, offsetX, offsetY);
widget.SetBold(true);
widget.SetItalic(true);
widget.SetColor(intARGB);                       // text color
int color = widget.GetColor();
int txtW, txtH;
widget.GetTextSize(txtW, txtH);                 // measure the rendered text

// Text property getters on controls (UIWidget and its children, such as EditBoxWidget):
int outlineSize = widget.GetTextOutlineSize();
int outlineColor = widget.GetTextOutlineColor();
int shadowSize = widget.GetTextShadowSize();
int shadowColor = widget.GetTextShadowColor();
float shadowOpacity = widget.GetTextShadowOpacity();
float shadowOffsetX = widget.GetTextShadowOffsetX();
float shadowOffsetY = widget.GetTextShadowOffsetY();
bool isItalic = widget.GetTextItalic();
bool isBold = widget.GetTextBold();
```

Corrected against `P:\`: the source lists the nine `GetText...` getters under "TextWidget" and adds "also on EditBoxWidget". In vanilla they belong to `class UIWidget` only (`GetTextOutlineSize` to `GetTextBold`, `P:\scripts\1_core\proto\enwidgets.c:323-338`), so they work on an `EditBoxWidget`, a `ButtonWidget` and other controls. A `TextWidget` does not have them; it has `GetOutlineSize`, `GetOutlineColor`, `GetShadowSize`, `GetShadowColor`, `GetShadowOpacity`, `GetShadowOffset`, `GetBold` and `GetItalic` instead (listed under TextWidget above).

### GetText on the two edit boxes

```
// EditBoxWidget returns the string directly:
string text = editBox.GetText();

// MultilineEditBoxWidget uses an out parameter:
string text2;
multiEditBox.GetText(text2);
```

### Images

```
bool loaded = img.LoadImageFile(0, path);       // returns whether it loaded
int imgW, imgH;
img.GetImageSize(0, imgW, imgH);               // image size in pixels
```

### Positioning in screen coordinates (any widget)

```
widget.SetScreenPos(pixelX, pixelY);            // absolute position
widget.SetScreenSize(pixelW, pixelH);           // absolute size
float x, y;
widget.GetScreenPos(x, y);                      // read the position
float w, h;
widget.GetScreenSize(w, h);                     // read the size
```

### Alignment flags

```
// Set and clear flags at runtime:
widget.ClearFlags(flagMask);
widget.SetFlags(newFlags);
widget.Update();                                // MUST be called after a flag change

// Bit values used by LBmaster_Core (not in the vanilla scripts):
// Horizontal: V_LEFT=0x00, V_CENTER=0x140, V_RIGHT=0x100 (mask: 0x1C0)
// Vertical: H_TOP=0x00, H_CENTER=0xA00, H_BOTTOM=0x800 (mask: 0xE00)
// Position clear mask: 0xFC0
// Text: TEXT_LEFT=0x0, TEXT_CENTER=0x100000, TEXT_RIGHT=0x400000 (mask: 0x500000)
```

### Visibility checks

```
widget.IsVisibleHierarchy();                    // true only when ALL parents are visible
widget.IsVisible();                             // this widget only
```

### Widget.TranslateString(): static localization

```
string translated = Widget.TranslateString("#STR_MY_KEY");
// Static: works without a widget instance
// Handles several #keys in one string:
// "Hello #STR_WORLD" becomes "Hello World"
```

### CanvasWidget drawing

```
CanvasWidget canvas;
// Drawing primitives for custom rendering
// LBmaster uses them to generate QR codes
```

### Global widget functions

```
Widget hovered = GetWidgetUnderCursor();         // widget under the mouse
Widget focused = GetFocus();                     // focused widget
int mx, my;
GetMousePos(mx, my);                            // mouse position in pixels
int sw, sh;
GetScreenSize(sw, sh);                          // screen resolution
```

## Text readback and widget type IDs

Added by the source author on 2026-08-31; the line numbers were checked here on `P:\`.

`TextWidget` has **no `GetText` method**. Its native block is `P:\scripts\1_core\proto\enwidgets.c:189-218`; it has `SetText` and no getter for the text. A test criterion that says "read the native TextWidget and compare its text" therefore cannot compile. Reading a wrapper the mod owns only proves what the model wrote, not what the widget drew.

When reading the text back is the contract, choose a widget whose real signature supports it:

- `MultilineEditBoxWidget.GetText(out string)` (`P:\scripts\1_core\proto\enwidgets.c:318`);
- `EditBoxWidget.GetText()`, which returns a `string` (`P:\scripts\1_core\proto\enwidgets.c:349`);
- `ButtonWidget.GetText(out string)` (`P:\scripts\1_core\proto\enwidgets.c:389`).

The `*WidgetTypeID` constants are usable although their declarations sit under `#ifdef DOXYGEN` (`TextWidgetTypeID` to `ScrollWidgetTypeID`, `P:\scripts\1_core\proto\enwidgets.c:6-53`). Compiled vanilla code uses them: `FrameWidgetTypeID` at `P:\scripts\5_mission\mission\gameplayeffectwidgets\gameplayeffectwidgets.c:34` and `RenderTargetWidgetTypeID` at `P:\scripts\2_gamelib\entities\rendertarget.c:63`. There is no enum of widget types to iterate. A data driven factory maps names to these constants; it does not invent integer IDs.
