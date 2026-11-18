# Widget calls worth knowing

Which less obvious widget calls the engine already provides, what the global HUD brightness does to your colors, and how rich text markup is said to behave. Full signatures per class are in `widget-prototypes.md` and `widget-classes.md`.

## Calls the engine already has

All in `P:\scripts\1_core\proto\enwidgets.c`. Check here before you write a helper; most "missing" features are one call away.

| Call | What it gives you | Line |
|---|---|---|
| `Widget.Show(bool show, bool immedUpdate = true)` | Show or hide, with an optional deferred update | `:125` |
| `SetFlags`, `ClearFlags` | Add flags to, or remove them from, the existing set | `:128`, `:131` |
| `Widget.Unlink()` | Destroys the widget and all its children | `:173` |
| `Widget.IsVisibleHierarchy()` | Visible only if every parent is visible too | `:139` |
| `WidgetFlags.CLIPCHILDREN`, `WidgetFlags.DRAGGABLE` | Clipping and native dragging | `:81`, `:84` |
| `ScrollWidget`: `GetVScrollPos`, `VScrollToPos`, `VScrollToPos01`, `VScrollToWidget(child)`, `GetContentHeight`, `IsScrollbarVisible` | Scroll to a child, for example the newest line of a message list | `:481` to `:502` |
| `RichTextWidget`: `GetContentHeight`, `SetContentOffset`, `ElideText`, `GetNumLines`, `SetLinesVisibility`, `GetLineWidth` | Measure and trim long text | `:224` to `:234` |
| `MultilineEditBoxWidget`: `GetLinesCount`, `GetCarriageLine`, `GetCarriagePos`, `SetLine`, `GetLine` | The cursor position, for a terminal style input | `:313` to `:321` |
| `ImageWidget`: `LoadMaskTexture`, `SetMaskProgress`, `SetMaskTransitionWidth` | A reveal transition with a soft edge, no extra code | `:282` to `:310` |
| `SpacerWidget.SetContentAlignmentH` and `V` | Align a spacer's children with `WidgetAlignment` (`WA_LEFT`, `WA_RIGHT`, `WA_CENTER`, `WA_TOP`, `WA_BOTTOM`, `:88` to `:94`) | `:465` to `:471` |
| `TextWidget`: `SetBold`, `SetItalic`, `SetShadow`, `SetOutline`, `GetTextSize`, `SetTextExactSize` | Text styling and measuring | `:189` to `:217` |
| `CanvasWidget`: `DrawLine(x1, y1, x2, y2, width, color)`, `Clear()` | Lines drawn from script | `:341` to `:345` |
| `VideoWidget`: `Load`, `Play`, `Pause`, `Stop`, `SetTime`, `GetTime`, `GetTotalTime`, `SetCallback` | Video playback | `:543` to `:632` |
| `EditBoxWidget.GetText()` | Returns the string; no out parameter | `:349` |
| `PasswordEditBoxWidget.SetHideText(bool hide)` | Masks the input | `:355` |
| `SliderWidget`: `SetMinMax`, `GetStep`, `SetStep` | Range and step | `:358` to `:367` |
| `ButtonWidget`: `SetTextHorizontalAlignment`, `SetTextVerticalAlignment` | Label alignment | `:395` to `:399` |
| `ScriptedWidgetEventHandler.OnEvent(EventType, Widget, int, int)` | A catch all event hook | `:685` |
| Global `GetWidgetUnderCursor()` | Hit test at the mouse | `:184` |
| Global `SetActiveWindow(Widget w, bool resetFocus)`, `SetModal(Widget w)` | Window and modal focus | `:695`, `:700` |
| Global `SetFocus(Widget w)`, `GetFocus()` | Set and read keyboard focus; `GetFocus() == myEditBox` tells you which field has it | `:698`, `:702` |

A vanilla `ScriptedWidgetEventHandler` still needs `SetHandler(this)` (`:172`); a Dabs view does not (`dabs-mvc-internals.md`). Override methods in a handler class don't need to sit next to each other; a production window that spreads them out works. Keeping `ref` to member fields is the conservative choice and is safe; Dabs itself also uses `ref` and `autoptr` elsewhere.

## The global HUD brightness

`Widget.SetLV(float lv)` and `Widget.SetTextLV(float lv)` are `proto static` and set one value for every widget and every text, from -15 to 0, where 0 is the default and lower is darker (`enwidgets.c:114` to `:117`). Vanilla uses exactly those two calls to apply the player's choice: `SetHudBrightness()` is nothing else (`P:\scripts\3_game\dayzgame.c:3910` to `:3914`), fed from `EDayZProfilesOptions.HUD_BRIGHTNESS` through `GetHUDBrightnessSetting()` (`:3916` to `:3919`) in `OnInitialize()` (`:2109` to `:2114`).

So colors that look darker than their hex values are the player's brightness setting doing its job, not an engine default. Measured in game with a lowered setting, pure saturated colors (red, green, blue) barely change, while grays and pastels (white, 50 percent gray, emerald, light red, light blue) come out clearly darker. Calling `SetLV(0)` from a mod overrides the player's preference across the whole HUD, vanilla included. Never call it; design against the setting instead. A HUD that removed both calls passed the same UI checks. To measure it on your own machine, use `color-test-harness.md`.

## Rich text markup

These come from the documented markup of the newer Enfusion engine (Arma Reforger), not from `P:\`. Confirm each one in game before you rely on it in DayZ; `RichTextWidget` itself is vanilla (`enwidgets.c:224`).

- Tags: `<b>`, `<i>`, `<color>` (by rgba, hex or name: `<color rgba="R,G,B,A">`, `<color hex="0xAARRGGBB">`), `<image set name scale>`, `<outline>`, `<shadow>`, `<font>`.
- Tags can't overlap; the parser needs a clean nesting.
- Wrapping and relaying out long text is expensive.
- Bold and italic need SDF fonts.
- `<image set="..." name="..." scale="1" />` draws an image inline; scale 1 is the line height. Vanilla's own text writes it that way: `<image set="dayz_gui" name="icon_pin" />` (`P:\scripts\data\news_feed.txt:2`).
- `<font name='gui/fonts/MetronBook'>...</font>` switches the face for a span; the attribute form is not checked on `P:\`.

## Still to test in game

- The same panel at 720p, 1080p and 1440p, screenshotted. Exact layout values already scale with the screen height, so a script scaler that multiplies them again scales twice (`checklist-and-troubleshooting.md`, "Declare all four unit flags"). DPI and other resolution questions wait on this test; open any existing panel at each resolution.
