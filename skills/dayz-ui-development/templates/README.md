# UI layout templates

Four `.layout` files to copy as a starting point, the stringtable their text keys need, and the four construction mistakes they exist to prevent.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). "Measured" means measured on a running client (DayZ 1.29) and not yet repeated on 1.30. Counts of vanilla use are over the 227 layouts under `P:\gui\layouts` (9,575 widgets).

## How to use them

Copy a template, rename the widgets, and put the `#STR_` keys in your stringtable. `stringtable.csv` in this folder defines the seven keys the templates use; copy its rows into your addon's own `stringtable.csv` (in the addon root, next to `config.cpp`).

- Without those rows the layouts show the key itself (`STR_UI_YES` instead of `Yes`), which looks like a broken template. The engine logs nothing about it (measured 2026-08-20: zero RPT lines for `STR_UI_`).
- The CSV holds the key without the leading `#`. The `#` belongs only to the reference in the layout.
- A stringtable belongs to an addon: it is read from the PBO at load, so unlike a layout in `$profile:` it does not hot reload.

`Message` in `modal_panel.layout` draws very large glyphs because its box is 0.58 of a panel that is 0.70 of the screen tall (292 px at 720p), and glyph height was measured to follow the widget height. `text_proportion` is honored on `TextWidgetClass` and `ButtonWidgetClass` (glyph height = 0.74 x value x box height, measured to within 2% on 2026-08-21) and ignored on `MultilineTextWidgetClass`, which is why a sweep of six values on 2026-08-20 changed nothing. On a multiline widget, size the box; the attribute does nothing. The numbers and controls are in `../references/hot-iteration.md`, section 6.

Iterate from `$profile:` with `ui_reload_layout`; the loop is described in [`../references/hot-iteration.md`](../references/hot-iteration.md).

The `*.rects.1920.json` and `*.rects.1280.json` files next to each template are the offline prediction of every widget's rectangle at those resolutions. Compare a live `ui_tree` or `ui_reload_layout` result against them. Matching rectangles do not prove anything is drawn.

| File | Use when | Do not use when |
|---|---|---|
| `modal_panel.layout` | A centered confirm, yes or no, or blocking prompt | A persistent HUD, a form (see `form_row`), a list (see `scroll_list`) |
| `hud_overlay.layout` | A corner readout that must not take the mouse | Anything clickable, a menu, a modal |
| `form_row.layout` | One label plus an `EditBoxWidget`; stack rows by parenting copies | A finished dialog (compose the rows into `modal_panel`) |
| `scroll_list.layout` | A viewport whose content is taller than the box | A short fixed list (a `GridSpacerWidget` with no `ScrollWidget` is enough) |

## Offline check (tool in this repo)

Run from the repo root:

```
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/dayz-ui-development/templates/<this.layout> --check
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/dayz-ui-development/templates/<this.layout> --canvas-width 1920 --canvas-height 1080
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/dayz-ui-development/templates/<this.layout> --canvas-width 1280 --canvas-height 720
```

`--check` tests that the file parses and has a sound structure (it prints OK and a widget count). It is not a geometry lint. The JSON dump is that parser's geometry, including `right_ref` and `bottom_ref`, which subtract the offset inward (`parse.py:790-803`).

## Reading the `.rects` files

Each node carries its predicted screen rectangle, `ignore_pointer`, and `clickable`. `clickable` is true only for the widget types that take a click: Button, EditBox, CheckBox, Slider and Combo.

`hud_overlay` (a Panel, an Image and two Text widgets) and `scroll_list` (a Panel, a Scroll and a Spacer) have no clickable widget. **A check that looks only at clickable widgets says nothing about those two templates.** Someone who copies `hud_overlay`, moves the badge off screen, runs such a check and deploys has checked nothing. Compare these widgets by name:

| File | Widgets that must be on screen |
|---|---|
| `modal_panel.layout` | `BtnYes`, `BtnNo` |
| `hud_overlay.layout` | `HudBadge`, `HudIcon`, `HudLabel`, `HudValue` |
| `form_row.layout` | `RowEdit` |
| `scroll_list.layout` | `ScrollListPanel`, `ScrollList`, `ScrollContent` |

Two things in the files look like defects and are the contract:

- In `hud_overlay` every widget has `ignore_pointer` 1, because a HUD must not take the aim. A zero size or an off screen rectangle is what shows a real mistake there.
- In `scroll_list`, `ScrollContent` has `ignore_pointer` 1 and a height of 0. The spacer is authored with height 0 and the engine grows it at runtime (`"Size To Content V" 1`). **Do not "fix" it by giving the spacer a height**; that brings back mistake 4 below. A zero size on `ScrollListPanel` itself is a real mistake.

## The four construction mistakes

These are the defects the templates stop you paying for in deploys. Each has a style or attribute that looks right and is not.

### 1. Invisible panel

**Symptom.** The widget tree is correct, the rectangles match, `ui_tree` shows the right color, and the panel is not on screen. Text floats over the world.

**Cause.** A `PanelWidgetClass` paints only through a style whose `Normal` state has a non-empty `Center` image. Style names are scoped per widget type.

| Style | Widget type it belongs to | What `Normal` draws |
|---|---|---|
| `Colorable` | `WindowWidget` (set at `P:\gui\layouts\dialog.layout:16`) | WhitePixel (a window) |
| `ColorablePanel` | `PanelWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3388`) | `Center=""`, nothing |
| `rover_sim_colorable` | `PanelWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3284`) | `Center="WhitePixel"` |

Vanilla sets `rover_sim_colorable` on 641 panels under `P:\gui\layouts`; it is the most used panel style. `ColorablePanel` exists (6 uses) and is the wrong guess. That a style exists is not enough: open `P:\gui\looknfeel\dayzwidgets.styles`, find `<Widget Name="PanelWidget">` (line 3233) and read the `Center` image of the `Normal` state. Detail: [`../references/styles-format.md`](../references/styles-format.md).

### 2. Title clipped on both sides

**Symptom.** A centered title longer than its box loses characters on the left and on the right.

**Cause.** `TextWidgetClass` with `"text halign" center` and no wrapping. `text_proportion` sizes text by height; it does not fit a long string to the width.

**Fix in these templates.** `MultilineTextWidgetClass` with `wrap 1` (337 of 339 vanilla MultilineText widgets). `wrap` on a `TextWidgetClass` appears on 0 of 1,403 vanilla widgets and does nothing at runtime: `wrap 1` and `wrap 0` draw the same clipped single line (measured in game 2026-08-22, see `../references/text-sizing-and-rendering.md`). Never rely on it.

### 3. White button, white label

**Symptom.** An `EmptyHighlight` button looks fine until it has focus; then its body fills white and the label disappears.

**Cause.** The `Focus` state of the `ButtonWidget` style `EmptyHighlight` has `Center="WhitePixel"` (the style starts at `P:\gui\looknfeel\dayzwidgets.styles:2224`; its `Focus` state starts at line 2236 and the `Center` item is at line 2238). The default label is white. With no body `color`, the pixel stays white.

**Fix in these templates.** `color 1 0 0 1` (the body color, not `"text color"`) plus `inheritalpha 0`, copied from `P:\gui\layouts\dialog.layout:31-42`. 14 of the 28 vanilla `EmptyHighlight` buttons set `inheritalpha 0`.

### 4. List does not scroll

**Symptom.** The content is taller than the box, the wheel does nothing, and there is no scrollbar.

**Cause.** A `ScrollWidgetClass` with no spacer child. The first child of the 54 vanilla scroll hosts: `GridSpacer` 25, `WrapSpacer` 12, `Panel` 8, `Frame` 4, another type or no child 5.

**Fix in these templates.** A direct child `GridSpacerWidgetClass` with `size 1 0`, `vexactsize 1` and `"Size To Content V" 1`, copied from `P:\gui\layouts\new_ui\options\keybindings_selectors\keybinding_container.layout:35-54`. That vanilla spacer has no children in the file; script fills it at runtime. The template does the same. Do not author sample rows under it.

## Hot iteration mistakes (runtime, not authoring)

The four measured failures of the `$profile:` loop are in [`../references/hot-iteration.md`](../references/hot-iteration.md), section 4: a missing path kills `CreateWidgets`; a second load stacks on the first; a missing texture paints flat white and logs nothing; perfect rectangles say nothing about what is painted. End every loop by looking at a frame.

## What these files are not

They are not verified in game. The `dayz-ui-lab` parser checks format and geometry offline. Load them with `ui_reload_layout` and look at the frame before you trust a color or a wrap.

## Notes on the files

- `stringtable.csv` has the seven column header (`Language`, `original`, `english`, `spanish`, `german`, `russian`, `chinesesimp`); `../references/localization.md` explains why all seven are needed. The `spanish` column holds real Spanish text as sample localization data; the other languages repeat the English text.
- Line numbers of vanilla files and counts of vanilla use in the template comments were checked on `P:\` (DayZ 1.30). In `hud_overlay.layout`, `BadgesPanel` is at `P:\gui\layouts\day_z_hud.layout:514`, the `Wetness` badge icon at `P:\gui\layouts\day_z_hud.layout:534`, and the `ignorepointer 1` example at `P:\gui\layouts\day_z_hud.layout:446`.
