# Layout attributes

What each attribute of a `.layout` widget does: units and anchors, visibility and input, color, text, and the attributes the counts show are common. The grammar is in `layout-format.md`; how attributes turn into a screen rect is in `layout-geometry.md`.

## Position and size

```text
position X Y      // exact units if hexactpos/vexactpos is 1, fraction of the parent if 0
size W H          // exact units if hexactsize/vexactsize is 1, fraction of the parent if 0
hexactpos 0|1
vexactpos 0|1
hexactsize 0|1
vexactsize 0|1
```

- An exact unit is 1/1080 of the screen height on both axes: the engine draws `declared x height / 1080` pixels whatever the width (measured in game from 461 to 1108 pixels high and at 2560x1080; `checklist-and-troubleshooting.md`, "Declare all four unit flags"). It is a pixel only on a 1080 pixel tall screen. The engine comment on `EXACTPOS` says "Uses physical resolution" (`P:\scripts\1_core\proto\enwidgets.c:68`); the drawn frame says otherwise.
- A flag left out means proportional. 42 vanilla widgets omit all four, among them menu roots such as `P:\gui\layouts\day_z_ingamemenu.layout:1`, and draw correctly. Declare all four anyway so the reader does not have to know that.
- Mixing exact and proportional axes on one widget is the vanilla norm: half of 8,671 vanilla widgets do it. The two most common mixes are exact position with proportional size, and exact position with proportional width and exact height. All proportional is about a quarter, all exact about a fifth.
- The usual way vanilla places a widget is an anchor with a zero offset: `halign` or `valign` set to a `*_ref` value and `position 0 0` (70% of widgets with an exact position have `0 0`).

## Anchors

```text
halign left_ref|center_ref|right_ref
valign top_ref|center_ref|bottom_ref
```

Anchors are central to vanilla layouts that hold at every resolution: the `day_z_hud.layout` roots use `halign center_ref` and `valign center_ref` with a proportional size, and `loading.layout` centres its 16:9 background the same way (`P:\gui\layouts\loading.layout:36`). With `right_ref` or `bottom_ref` the offset is measured inward from that edge, and with `center_ref` it is added to the centred spot. Both are measured in game; the numbers are in `layout-geometry.md`.

## Visibility and input

```text
visible 0|1        // starting visibility, default 1
ignorepointer 0|1  // 1 lets mouse events pass through
clipchildren 0|1   // 1 clips children to this widget's box
priority N         // draw order among siblings, higher on top
```

- Give every background `ImageWidget` `ignorepointer 1`; without it the background takes the mouse events meant for the buttons on it. Never give an `EditBox` or a `Button` `ignorepointer 1`.
- `visible 0` in a layout works: the widget starts hidden with no script, and the engine tree reports `visible:0` and `visible_hierarchy:0`. For sections you switch between, stack identical roots in the same place, declare the active one `visible 1` and the rest `visible 0`, and let script toggle only the roots; this removes the gap that sections stacked one under another leave.
- A tool that reads integer flags must not write `int(value or 1)`: in Python 0 is false, so every `visible 0` turns into 1. `attr_int` in `scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py` uses an explicit missing value.
- `priority` is the layout side of `SetSort`, which sets the order outright (`P:\scripts\1_core\proto\enwidgets.c:130`).

## Color and images

```text
color R G B A       // floats 0.0 to 1.0
image0 "path"       // or "set:dayz_gui image:icon_name"; slots image0 to image7
stretch 0|1         // 1 stretches the image over the widget
mode blend          // blend mode keyword: blend, additive or opaque
"src alpha" 1       // with mode blend, needed for transparent images
inheritalpha 1      // multiply the alpha with the parent's
fixaspect fixwidth  // keyword: fixwidth, inside, outside or none
```

- A layout writes colors as floats from 0 to 1 (`color 0.12 0.12 0.12 0.92`); script writes `ARGB(235, 30, 30, 30)` with integers from 0 to 255. Mixing the two gives invisible or wrong colors.
- `mode` and `fixaspect` take keywords, never numbers: `mode blend` (`P:\gui\layouts\day_z_ingamemenu.layout:74`), `mode additive` (`:551`), `fixaspect outside` (`:72`), `fixaspect fixwidth` (`:563`).
- An imageset image works in `image0` (`image0 "set:dayz_inventory image:missing"`, `P:\gui\layouts\new_ui\hud\simpleicontemplate.layout:56`), in `LoadImageFile` and inline in rich text, never in `color`.
- The alpha in `color` is ignored on an `ImageWidget` with no texture, and a transparent image needs `mode blend` and `"src alpha" 1` (`text-sizing-and-rendering.md`).

## Text

```text
font "gui/fonts/Metron"           // MetronBook for body text, sdf_* faces for scaled text
text "#STR_MYMOD_TITLE"           // always a stringtable key in a shipped mod
"text halign" left|center|right
"text valign" top|center|bottom
text_proportion 0.5               // text height as a fraction of the widget height
"exact text" 1                    // with "exact text size" N
wrap 1                            // only on MultilineText, RichText and Html widgets
```

The vanilla fonts are `gui/fonts/Metron` (bold), `gui/fonts/MetronBook` (regular) and `gui/fonts/amorserifpro` (serif), each also in numbered and SDF sizes. How each face takes its size is in `text-sizing-and-rendering.md`.

Which classes carry the text attributes, over 819 layouts (vanilla, third party and in house):

| Attribute | Where it appears |
|---|---|
| `wrap` (604) | `MultilineTextWidget` 355, `RichTextWidget` 236, `HtmlWidget` 9, `TextWidget` 4 |
| `text_proportion` (1,048) | `TextWidget` 679, `ButtonWidget` 361, `RichTextWidget` 5, `MultilineTextWidget` 3 |
| `"exact text"` (2,888) | `TextWidget` 2,135, `MultilineTextWidget` 352, `RichTextWidget` 292, `EditBox` 87, `HtmlWidget` 13, `MultilineEditBox` 5 |

No spacer carries `wrap`. Totals move by about 1% between counting tools, the hosts do not.

- `text_proportion` sizes text by the widget's height. It never makes a long single line fit the width; only wrapping (a multiline or rich text widget) or a shorter string does.
- Vanilla's dialog text is the recipe for text that fits: a `RichTextWidgetClass` with `"exact text" 1`, `"exact text size" 20`, `"size to text h" 1`, `"size to text v" 1`, `wrap 1` and `clipchildren 1` (`P:\gui\layouts\dialog.layout:95` to `:113`). Copy it whole.

## Other common attributes

| Attribute | Meaning | Status |
|---|---|---|
| `style NAME` | A style from a registered `.styles` file, unquoted, scoped to the widget type (`styles-format.md`) | Checked on `P:\` |
| `userID N` | Integer read by `FindAnyWidgetById` and `GetUserID` | Script side on `P:\` |
| `scriptclass "Name"` | Attaches a handler class (`layout-scriptclass.md`) | Checked on `P:\` |
| `Columns N`, `Rows N`, `Padding`, `Margin` | Spacer grid settings; keys are case sensitive | Measured in game |
| `"Size To Content H"`, `"Size To Content V"` | A spacer grows to fit its children | Measured in game |
| `"Scrollbar V" 1` | Vertical scrollbar on a `ScrollWidget` | Used by the templates |
| `scaled 1` | Unverified: a resolution scaling switch; `SetResolutionScale` exists only on `RenderTargetWidget` (`P:\scripts\1_core\proto\enwidgets.c:240`) | Inferred from the name |
| `keepsafezone 1` | Unverified: keeps TV safe margins on console | Inferred from the name |
| `nocache 1` | Unverified: skips the texture cache | Inferred from the name |
| `draggable 1` | Sets the `DRAGGABLE` flag | Inferred from the name |

An unknown or misspelt key is ignored without a word: a `GridSpacerWidgetClass` with `columns 1` and `rows 0` laid its rows side by side, while one with `Columns 1` and `Rows 100` stacked them (measured in game). Compare each key with its vanilla spelling.

## Script calls for scroll and spacer widgets

```c
float pos01 = scroll.GetVScrollPos01();   // 0 to 1
scroll.VScrollToPos01(0.5);
scroll.VScrollToWidget(childWidget);
spacer.SetContentAlignmentH(WidgetAlignment.WA_CENTER);
```

The full lists are in `widget-classes.md`.
