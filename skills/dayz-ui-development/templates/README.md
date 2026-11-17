# UI layout templates

Four `.layout` files to copy as a starting point, the stringtable their text keys need, and the four construction mistakes they exist to prevent.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). "Measured" means the source author measured it on a running client (DayZ 1.29); those results are not yet repeated here. Counts "in the 214 vanilla files" are the source author's counts on an earlier dump; where a count was repeated on `P:\` (227 layouts under `P:\gui\layouts`) the `P:\` number is given next to it. `mcp_dialog.layout`, `cable_hud.layout` and `LFPG_TankHUD.layout` are layouts from the source author's LFPowerGrid project; they are cited as the origin of some numbers and are not in this repo.

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

## `ui_rect_lint.py` is not in this repo

`ui_rect_lint.py` is a tool of the source author's that was not published with the knowledge pack. The `.rects` files in this folder were produced by its `predict` command. If you have it:

```
python ui_rect_lint.py lint --layout <this.layout> --res 1920x1080 --expect-visible <names>
python ui_rect_lint.py predict --layout <this.layout> --res 1920x1080 --out <this>.rects.1920.json
python ui_rect_lint.py predict --layout <this.layout> --res 1280x720  --out <this>.rects.1280.json
```

The `--expect-visible` names for the four templates:

| File | `--expect-visible` |
|---|---|
| `modal_panel.layout` | `BtnYes,BtnNo` |
| `hud_overlay.layout` | `HudBadge,HudIcon,HudLabel,HudValue` |
| `form_row.layout` | `RowEdit` |
| `scroll_list.layout` | `ScrollListPanel,ScrollList,ScrollContent` |

Without `--expect-visible`, `ui_rect_lint.py:302-306` limits its `targets` to clickable types (`CLICKABLE_TYPES`, `:32-39`): Button, EditBox, CheckBox, Slider and Combo. The rules `R5-zero-size`, `R6-off-screen` and `R7-overlap` then look only at those. `hud_overlay` (a Panel, an Image and two Text widgets) and `scroll_list` (a Panel, a Scroll and a Spacer) have none.

**`CLEAN` on `hud_overlay` and `scroll_list` means "not measured", not "passes".** Someone who copies `hud_overlay`, moves the badge off screen, sees `CLEAN` and deploys has checked nothing. `--expect-visible` is what forces those widgets into `targets`. A lint run on predicted rectangles alone also skips R1, R2 and R3; those need a `ui_tree` capture.

In `hud_overlay` the whole tree is `ignorepointer 1` (a HUD must not take the aim). `--expect-visible HudBadge` therefore always reports `[R4-ignore-pointer]` on a correct copy. That is the pass-through contract, not a geometry failure. R5 and R6 are the rules that catch a real mutation here.

`scroll_list` also reports two findings on a correct copy: `[R4-ignore-pointer]` and `[R5-zero-size]`, both on `ScrollContent`. The spacer is authored with height 0 and the engine grows it at runtime (`"Size To Content V" 1`), so a zero box there is the contract, not a defect. **Do not "fix" it by giving the spacer a height**; that brings back mistake 4 below. R5 is still useful on this template: it catches the mutation that sets the panel itself to `size 0 0`.

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

Vanilla sets `rover_sim_colorable` on panels 577 times in the source author's count, and `style rover_sim_colorable` appears 641 times under `P:\gui\layouts` (counted on `P:\`). `ColorablePanel` exists (6 uses on `P:\`) and is the wrong guess. That a style exists is not enough: open `P:\gui\looknfeel\dayzwidgets.styles`, find `<Widget Name="PanelWidget">` (line 3233) and read the `Center` image of the `Normal` state. Detail: [`../references/styles-format.md`](../references/styles-format.md).

### 2. Title clipped on both sides

**Symptom.** A centered title longer than its box loses characters on the left and on the right.

**Cause.** `TextWidgetClass` with `"text halign" center` and no wrapping. `text_proportion` sizes text by height; it does not fit a long string to the width.

**Fix in these templates.** `MultilineTextWidgetClass` with `wrap 1` (329 of 331 vanilla MultilineText widgets in the source author's count; 337 of 339 on `P:\`). `wrap` on a `TextWidgetClass` appears 0 times in vanilla (also 0 of 1,403 on `P:\`) and does nothing at runtime: `wrap 1` and `wrap 0` draw the same clipped single line (measured in game 2026-08-22, see `../references/text-sizing-and-rendering.md`). Never rely on it.

### 3. White button, white label

**Symptom.** An `EmptyHighlight` button looks fine until it has focus; then its body fills white and the label disappears.

**Cause.** The `Focus` state of the `ButtonWidget` style `EmptyHighlight` has `Center="WhitePixel"` (the style starts at `P:\gui\looknfeel\dayzwidgets.styles:2224`; its `Focus` state starts at line 2236 and the `Center` item is at line 2238). The default label is white. With no body `color`, the pixel stays white.

**Fix in these templates.** `color 1 0 0 1` (the body color, not `"text color"`) plus `inheritalpha 0`, copied from `P:\gui\layouts\dialog.layout:31-42` and from `mcp_dialog.layout`. 14 of 28 vanilla `EmptyHighlight` buttons set `inheritalpha 0` in the source author's count (`style EmptyHighlight` also appears 28 times on `P:\`).

### 4. List does not scroll

**Symptom.** The content is taller than the box, the wheel does nothing, and there is no scrollbar.

**Cause.** A `ScrollWidgetClass` with no spacer child. The first child of the 51 vanilla scroll hosts in the source author's count: `GridSpacer` 23, `WrapSpacer` 10, `Panel` 9, `Frame` 4. (A rough recount on `P:\` gives 54 hosts: `GridSpacer` 25, `WrapSpacer` 12, `Panel` 8, `Frame` 4.)

**Fix in these templates.** A direct child `GridSpacerWidgetClass` with `size 1 0`, `vexactsize 1` and `"Size To Content V" 1`, copied from `P:\gui\layouts\new_ui\options\keybindings_selectors\keybinding_container.layout:35-54`. That vanilla spacer has no children in the file; script fills it at runtime. The template does the same. Do not author sample rows under it.

## Hot iteration mistakes (runtime, not authoring)

The four measured failures of the `$profile:` loop are in [`../references/hot-iteration.md`](../references/hot-iteration.md), section 4: a missing path kills `CreateWidgets`; a second load stacks on the first; a missing texture paints flat white and logs nothing; perfect rectangles say nothing about what is painted. End every loop by looking at a frame.

## What these files are not

They are not verified in game. The `dayz-ui-lab` parser checks format and geometry offline. Load them with `ui_reload_layout` and look at the frame before you trust a color or a wrap.

## Notes on the files

- `stringtable.csv` has the seven column header (`Language`, `original`, `english`, `spanish`, `german`, `russian`, `chinesesimp`); `../references/localization.md` explains why all seven are needed. The `spanish` column holds real Spanish text as sample localization data; the other languages repeat the English text.
- Line numbers of vanilla files in the template comments were checked on `P:\` (DayZ 1.30). Three in `hud_overlay.layout` had moved since the source author's dump and were updated: `BadgesPanel` is at `P:\gui\layouts\day_z_hud.layout:514`, the `Wetness` badge icon at `P:\gui\layouts\day_z_hud.layout:534`, and the `ignorepointer 1` example at `P:\gui\layouts\day_z_hud.layout:446`.
