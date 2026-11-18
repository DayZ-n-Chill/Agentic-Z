# UI layout templates

Four `.layout` files to copy as a starting point, the stringtable their keys need, how to check them offline, and the four construction mistakes they are built to avoid. Vanilla counts are over the 227 layouts under `P:\gui\layouts` (9,525 widgets).

The three preview panels in this folder, `chat_feed.layout`, `info_panel.layout` and `mini_hud.layout`, are not starting points; their widget names and defaults are in `panel-contract.md`.

## Which template

| File | Use for | Not for |
|---|---|---|
| `modal_panel.layout` | A centred confirm, yes or no, or blocking prompt | A lasting HUD, a form (`form_row`), a list (`scroll_list`) |
| `hud_overlay.layout` | A corner readout that must not take the mouse | Anything clickable, a menu, a modal |
| `form_row.layout` | One label and an `EditBoxWidget`; stack rows by parenting copies | A finished dialog (put the rows into `modal_panel`) |
| `scroll_list.layout` | A view whose content is taller than its box | A short fixed list (a `GridSpacerWidget` with no `ScrollWidget` is enough) |

Copy a template, rename its widgets, and copy the rows of `stringtable.csv` in this folder into your addon's `stringtable.csv`, next to `config.cpp`. It defines the seven keys the templates use.

- Without those rows the layouts show the key itself (`STR_UI_YES` instead of `Yes`), and the engine logs nothing about it (measured: no RPT line).
- The CSV holds keys without the `#`; only the reference in the layout has it.
- The CSV has the seven column header `Language`, `original`, `english`, `spanish`, `german`, `russian`, `chinesesimp`, which the engine needs (`../localization.md`). The `spanish` column holds real Spanish; the other languages repeat the English.
- A stringtable is read from the PBO at load, so unlike a layout in `$profile:` it does not reload while you iterate.

`Message` in `modal_panel.layout` draws large glyphs because its box is 0.58 of a panel that is 0.70 of the screen tall (292 px at 720p), and glyph height follows the widget height (measured). `text_proportion` is honored on `TextWidgetClass` and `ButtonWidgetClass`, where glyph height is 0.74 x value x box height to within 2%, and ignored on `MultilineTextWidgetClass`: size a multiline box instead (`../preview-text-and-stringtables.md`, "`text_proportion` works on TextWidget only"). The button readings are in the comment on `BtnYes` in `modal_panel.layout`.

Iterate from `$profile:`; the loop and its four traps are in `../hot-iteration.md`. End every loop by looking at a frame.

## Checking a template offline

From the repo root:

```text
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/_shared/ui/templates/<file>.layout --check
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/_shared/ui/templates/<file>.layout --canvas-width 1920 --canvas-height 1080
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/_shared/ui/templates/<file>.layout --canvas-width 1280 --canvas-height 720
```

`--check` tests that the file parses and is sound, printing OK and a widget count; it is not a geometry check. The JSON is the parser's geometry, with `right_ref` and `bottom_ref` subtracting the offset inward (`parse.py:791` and `:792`, `:803` and `:804`; `../layout-geometry.md`).

The `*.rects.1920.json` and `*.rects.1280.json` files beside each template are the predicted rect of every widget at those sizes. Compare a live widget tree against them; matching rects do not prove anything is drawn. Each node carries its rect, `ignore_pointer` and `clickable`, which is true only for buttons, edit boxes, check boxes, sliders and combo boxes.

`hud_overlay` and `scroll_list` have no clickable widget, so a check that looks only at clickable widgets says nothing about them. Check these names are on screen:

| File | Widgets that must be on screen |
|---|---|
| `modal_panel.layout` | `BtnYes`, `BtnNo` |
| `hud_overlay.layout` | `HudBadge`, `HudIcon`, `HudLabel`, `HudValue` |
| `form_row.layout` | `RowEdit` |
| `scroll_list.layout` | `ScrollListPanel`, `ScrollList`, `ScrollContent` |

Two things look like defects and are the contract. In `hud_overlay` every widget has `ignore_pointer` 1, because a HUD must not take the aim; there, a zero size or an off screen rect is the real mistake. In `scroll_list`, `ScrollContent` has `ignore_pointer` 1 and height 0 because the engine grows it at runtime (`"Size To Content V" 1`); do not give it a height, or mistake 4 comes back. A zero size on `ScrollListPanel` is a real mistake.

The vanilla lines the template comments cite: `BadgesPanel` at `P:\gui\layouts\day_z_hud.layout:514`, the `Wetness` badge icon at `:534`, and an `ignorepointer 1` example at `:446`.

## The four construction mistakes

### Invisible panel

The widget tree is right, the rects match, the tree reports the right color, and the panel is not on screen; text floats over the world. A `PanelWidgetClass` draws only through a style whose `Normal` state has a non-empty `Center` image, and style names belong to one widget type.

| Style | Belongs to | What `Normal` draws |
|---|---|---|
| `Colorable` | `WindowWidget` (`P:\gui\layouts\dialog.layout:16`) | `WhitePixel` |
| `ColorablePanel` | `PanelWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3388`) | Nothing, `Center=""` |
| `rover_sim_colorable` | `PanelWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3284`) | `WhitePixel` |

Vanilla sets `rover_sim_colorable` on 641 panels; `ColorablePanel` (6 uses) is the wrong guess. Open `P:\gui\looknfeel\dayzwidgets.styles`, find `<Widget Name="PanelWidget">` (line 3233) and read the `Center` of the `Normal` state (`../styles-format.md`).

### Title clipped on both sides

A centred title longer than its box loses letters on both ends: a `TextWidgetClass` with `"text halign" center` does not wrap, and `text_proportion` sizes text by height, not width. The templates use `MultilineTextWidgetClass` with `wrap 1`, as 337 of 339 vanilla multiline text widgets do. `wrap` on a `TextWidgetClass` appears on none of 1,403 vanilla text widgets and does nothing in game (`../text-sizing-and-rendering.md`).

### White button, white label

An `EmptyHighlight` button looks fine until it takes focus; then its body fills white and the white label disappears. Its `Focus` state has `Center="WhitePixel"` (style at `P:\gui\looknfeel\dayzwidgets.styles:2224`, `Focus` at `:2236`, the item at `:2238`). The templates set the body `color 1 0 0 1` (not `"text color"`) and `inheritalpha 0`, as `P:\gui\layouts\dialog.layout:31` to `:42` does; 14 of the 28 vanilla `EmptyHighlight` buttons set `inheritalpha 0`.

### List does not scroll

The content is taller than the box, the wheel does nothing, and there is no scrollbar: the `ScrollWidgetClass` has no spacer child. The first child of the 54 vanilla scroll widgets is a `GridSpacer` 25 times, a `WrapSpacer` 12, a `Panel` 8, a `Frame` 4 and something else or nothing 5. The template uses a direct `GridSpacerWidgetClass` child with `size 1 0`, `vexactsize 1` and `"Size To Content V" 1`, as `P:\gui\layouts\new_ui\options\keybindings_selectors\keybinding_container.layout:35` to `:54` does. That vanilla spacer has no children in the file; script fills it. Do not add sample rows under it.

## How far they are checked

The geometry of `modal_panel` and `form_row` was seen in game on 1.29; `hud_overlay` and `scroll_list` have not been loaded in game, and none has been loaded on 1.30. The offline parser checks format and geometry only. Load a template from `$profile:` and look at a frame before you trust a color or a wrap.
