# Widget classes from script

The native methods of each widget class a mod calls: text widgets, images, buttons and inputs, scroll and spacer widgets, canvas and video, and which widgets can give their text back. Methods every widget shares are in `widget-prototypes.md`; the 3D preview widgets are in `preview-widgets.md`.

Every prototype was compared with its class in `P:\scripts\1_core\proto\enwidgets.c`; the line of each class is given with it.

## TextWidget

`class TextWidget extends Widget` (`P:\scripts\1_core\proto\enwidgets.c:189`).

```c
proto native void SetText(string text, bool immedUpdate = true);
proto void SetTextFormat(string text, void param1 = NULL, ...);   // up to param9
proto native void SetTextExactSize(int size);     // needs "exact text" 1 in the layout
proto native void SetTextSpacing(int horiz, int vert);
proto native void SetTextOffset(int left, int top);
proto void GetTextSize(out int sx, out int sy);   // the drawn text, in pixels
proto native float GetTextProportion();
proto native void SetTextProportion(float val);   // text height / widget height, 0 to 1
proto native void SetBold(bool bold);
proto native bool GetBold();
proto native void SetItalic(bool italic);
proto native bool GetItalic();
proto native void SetOutline(int outlineSize, int argb = 0xFF000000);
proto native int GetOutlineSize();
proto native int GetOutlineColor();
proto native void SetShadow(int size, int argb = 0xFF000000, float opacity = 1, float offX = 0, float offY = 0);
proto native int GetShadowSize();
proto native int GetShadowColor();
proto native float GetShadowOpacity();
proto void GetShadowOffset(out float sx, out float sy);
```

Text color on a `TextWidget` is plain `SetColor`.

`RichTextWidget extends TextWidget` (`:224`) adds `GetContentHeight`, `GetContentOffset`, `SetContentOffset(float offset, bool snapToLine = false)`, `ElideText(int line, float maxWidth, string str)`, `GetNumLines`, `SetLinesVisibility(int lineFrom, int lineTo, bool visible)`, `GetLineWidth(int line)` and `SetLineBreakingOverride(int mode)`. Its markup (`<b>`, `<i>`, `<color>`, `<image set="..." name="..."/>`, `<font>`, `<outline>`, `<shadow>`) is in `engine-widget-facts.md`. `HtmlWidget extends RichTextWidget` adds `LoadFile` (`P:\scripts\3_game\gameplay.c:316`).

`MultilineEditBoxWidget extends TextWidget` (`:313`): `GetText(out string text)` (`:318`), `SetLine(int line, string text)`, `GetLine(int line, out string text)`, `GetLinesCount`, `GetCarriageLine` and `GetCarriagePos` (the cursor line and character).

## Text calls on controls

`TextWidget` and `UIWidget` are siblings under `Widget`, and each has its own text calls. `UIWidget` (`P:\scripts\1_core\proto\enwidgets.c:323` to `:339`) is the base of buttons, edit boxes, check boxes, sliders, combo boxes and list boxes.

| Need | On a TextWidget | On a control (UIWidget) |
|---|---|---|
| Text color | `SetColor` | `SetTextColor` (`SetColor` colors the body) |
| Outline | `SetOutline`, `GetOutlineSize`, `GetOutlineColor` | `SetTextOutline`, `GetTextOutlineSize`, `GetTextOutlineColor` |
| Shadow | `SetShadow`, `GetShadowSize`, `GetShadowColor`, `GetShadowOpacity`, `GetShadowOffset` | `SetTextShadow`, `GetTextShadowSize`, `GetTextShadowColor`, `GetTextShadowOpacity`, `GetTextShadowOffsetX`, `GetTextShadowOffsetY` |
| Bold, italic | `SetBold`, `SetItalic`, `GetBold`, `GetItalic` | `SetTextBold`, `SetTextItalic`, `GetTextBold`, `GetTextItalic` |

A `GetText...` getter called on a `TextWidget` does not compile.

## ImageWidget

`class ImageWidget extends Widget` (`P:\scripts\1_core\proto\enwidgets.c:247`).

```c
proto native bool LoadImageFile(int num, string name, bool noCache = false);  // :257, returns whether it loaded
proto native bool SetImage(int num);              // switch the shown slot
proto native int GetImage();
proto void GetImageSize(int image, out int sx, out int sy);   // :260
proto native void SetImageTexture(int image, RTTextureWidget texture);
proto native void SetUV(float uv[4][2]);          // needs CUSTOMUV
proto native bool LoadMaskTexture(string resource);
proto native float GetMaskProgress();
proto native void SetMaskProgress(float value);           // 0 to 1, for reveal effects
proto native float GetMaskTransitionWidth();
proto native void SetMaskTransitionWidth(float value);    // 0 to 1, edge softness
```

`SetColor` multiplies the texture, so author art that you will tint in white or grey.

A procedural texture string from script, `img.LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")`, fails on 1.29 with "Bad texture name" and "LoadImageFile can't load" in the RPT and leaves the widget with no texture (measured in game, not repeated on 1.30). Vanilla builds such strings only for item materials: `string.Format("#(argb,8,8,3)color(%1,CO)", ...)` (`P:\scripts\4_world\static\miscgameplayfunctions.c:245`). Use a 1x1 white `.edds`, or a style whose `Center` is `WhitePixel` (`styles-format.md`). The same string as `image0` in a layout logs no error; whether it draws is not confirmed.

## Buttons and inputs

| Class | Declared | Calls |
|---|---|---|
| `ButtonWidget extends UIWidget` | `:381` | `GetState`, `SetState(bool)`, `SetText(string)`, `GetText(out string)` (`:389`), `SetTextOffset(float, float)`, `SetTextHorizontalAlignment(int)`, `SetTextVerticalAlignment(int)`; `SetColor` works with no image when the style's centre is `WhitePixel` |
| `EditBoxWidget extends UIWidget` | `:347` | `string GetText()` (`:349`), `SetText(string)`; `OnChange` fires on every keystroke; there is no text alignment call |
| `CheckBoxWidget extends UIWidget` | `:418` | `IsChecked`, `SetChecked(bool)`, `SetText(string)` |
| `SliderWidget extends UIWidget` | `:358` | `SetMinMax`, `GetMin`, `GetMax`, `GetCurrent`, `SetCurrent`, `GetStep`, `SetStep` |

Other controls, in short:

| Class | Calls |
|---|---|
| `XComboBoxWidget` | `AddItem`, `ClearAll`, `GetCurrentItem`, `SetCurrentItem`, `GetNumItems` |
| `TextListboxWidget` | `AddItem(text, userData, column, row = -1)` returns the row, `SetItem`, `GetItemText(row, col, out text)`, `SetItemColor(row, col, color)`, `RemoveRow`, `GetSelectedRow`, `SelectRow`, `GetNumItems`, `GetItemData`, `EnsureVisible`, `ClearItems` |
| `ProgressBarWidget` | Extends `SimpleProgressBarWidget` (`P:\scripts\1_core\proto\enwidgets.c:369` to `:379`); `SetCurrent(float)`; `GetMin` and `GetMax` only read, so the range comes from the layout or style. Vanilla drives the stamina bar from 0 to 100: `m_Stamina.SetCurrent((value / range) * 100)` (`P:\scripts\5_mission\gui\ingamehud.c:690`) |
| `PasswordEditBoxWidget` | An edit box plus `SetHideText(bool)` |
| `MapWidget` | `ScreenToMap`, `MapToScreen`, `SetMapPos`, `GetMapPos`, `SetScale`, `GetScale`, `AddUserMark`, `ClearUserMarks` (`P:\scripts\3_game\gameplay.c:321`; `map-and-markers.md`) |

Dabs Framework binds both ways (`Two_Way_Binding`) to edit boxes, multiline edit boxes, password edit boxes, check boxes, sliders, combo boxes, text list boxes, progress bars, buttons, and to scroll and spacer widgets that hold a collection; text, rich text, image and preview widgets bind one way only (`dabs-mvc-internals.md`).

`SetFocus(null)` clears focus from an edit box; with a focused edit box the first ESC clears the focus and only the second closes a menu that handles it that way (`verification.md`).

## ScrollWidget and spacers

`class ScrollWidget extends SpacerBaseWidget` (`:481`) scrolls both ways.

```c
proto native float GetScrollbarWidth();
proto native bool IsScrollbarVisible();
proto native float GetContentWidth();
proto native float GetContentHeight();
proto native float GetVScrollPos();
proto native float GetVScrollPos01();          // 0 to 1
proto native bool VScrollStep(int steps);
proto native void VScrollToPos(float pos);
proto native void VScrollToPos01(float pos01);
proto native void VScrollToWidget(Widget child);
// and the same six for H: GetHScrollPos, GetHScrollPos01, HScrollStep, HScrollToPos, HScrollToPos01, HScrollToWidget
```

A scroll widget needs `"Scrollbar V" 1` and a spacer child with `"Size To Content V" 1`; with no spacer child it does not scroll (`templates/scroll_list.layout`).

`SpacerBaseWidget` (`:460`) has `AddChildAfter(Widget child, Widget after, bool immedUpdate = true)`. `SpacerWidget` (`:465`) adds `GetContentAlignmentH`, `SetContentAlignmentH(WidgetAlignment)`, `GetContentAlignmentV` and `SetContentAlignmentV(WidgetAlignment)`. `enum WidgetAlignment` (`:88` to `:95`) is `WA_LEFT` 0, `WA_RIGHT` 1, `WA_CENTER` 2, `WA_TOP` 0, `WA_BOTTOM` 1. `GridSpacerWidget` (`:473`) and `WrapSpacerWidget` (`:477`) take `Columns`, `Rows`, `Padding`, `Margin`, `"Size To Content H" 1` and `"Size To Content V" 1` in the layout; the wrap spacer moves children to the next row by itself.

## CanvasWidget and VideoWidget

`class CanvasWidget` (`:341`): `DrawLine(float x1, float y1, float x2, float y2, float width, int color)` and `Clear()`. Lines alone are enough to draw a QR code.

`class VideoWidget` (`:543`): `Load(string name, bool looping = false, int startTime = 0)`, `Unload`, `Play`, `Pause`, `Stop`, `SetTime(int time, bool preload)`, `GetTime`, `GetTotalTime`, `SetLooping(bool)`, `IsPlaying`, `GetState` (returns a `VideoState`, `:577`), `DisableSubtitles(bool)` and `SetCallback(VideoCallback cb, func fn)`.

## Reading text back

`TextWidget` has no `GetText`: its block (`P:\scripts\1_core\proto\enwidgets.c:189` to `:217`) has `SetText` and no getter. A test that reads a `TextWidget` and compares its text cannot compile, and reading a field the mod owns proves only what the script wrote, not what was drawn. When reading back is the contract, pick a widget that can:

- `MultilineEditBoxWidget.GetText(out string)` (`:318`);
- `EditBoxWidget.GetText()`, which returns the string (`:349`);
- `ButtonWidget.GetText(out string)` (`:389`).
