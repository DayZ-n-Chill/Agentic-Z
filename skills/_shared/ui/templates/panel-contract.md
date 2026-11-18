# Contract: UI panels on demand

Layouts made to be loaded from `$profile:` with `ui_reload_layout` and filled at runtime with `ui_set_text` (which finds a widget with `FindAnyWidget` by `name`). Every text is authored empty (`text ""`). `#STR_` keys are not allowed: a stringtable does not travel with a loose `.layout`.

`ui_reload_layout` and `ui_set_text` are commands of the in-game test harness described in `../hot-iteration.md`; they are tool behaviour, not vanilla script, and are not yet checked on `P:\`.

`FindAnyWidget` searches the whole tree, so show only one of these panels at a time (`Unlink` it, or call `ui_reload_layout(mode="close")`, before loading the next one).

## Widget names by panel kind

Every TextWidget starts at `text ""`. The caller sets the string.

### `feed` (chat or log)

| name | class | set with `ui_set_text` |
|---|---|---|
| `FeedRoot` | FrameWidgetClass | no (full screen host, `size 1 1`, `ignorepointer 1`, `priority 2000`) |
| `FeedPanel` | PanelWidgetClass | no (`style rover_sim_colorable`) |
| `TitleText` | TextWidgetClass | yes (always present) |
| `FeedLine0` to `FeedLine{N-1}` | TextWidgetClass | yes, one line per row |

### `info` (label and value)

| name | class | set with `ui_set_text` |
|---|---|---|
| `InfoRoot` | FrameWidgetClass | no |
| `InfoPanel` | PanelWidgetClass | no |
| `TitleText` | TextWidgetClass | yes (always present) |
| `Label0` to `Label{N-1}` | TextWidgetClass | yes |
| `Value0` to `Value{N-1}` | TextWidgetClass | yes |

### `hud` (minimal HUD)

| name | class | set with `ui_set_text` |
|---|---|---|
| `HudRoot` | FrameWidgetClass | no (`priority 100`, whole tree `ignorepointer 1`) |
| `HudPanel` | PanelWidgetClass | no (`halign left` and `valign top`) |
| `TitleText` | TextWidgetClass | only when `--title` is passed |
| `FeedLine0` to `FeedLine{N-1}` | TextWidgetClass | yes |

`--title` does not write its text into the widget (the widget stays `text ""`); the text goes into the comment at the top of the file. Set the visible title with `ui_set_text` on `TitleText`.

## Command line

```
python gen_panel_layout.py <feed|info|hud> --rows N [--title TEXT] --out FILE
                           [--width W] [--height H] [--x X] [--y Y]
python gen_panel_layout.py --self-test
```

Units are fractions of the screen (the four `hexact*` and `vexact*` flags are 0). `--x` and `--y` place the top left corner of the panel.

Defaults:

| kind | --width | --height | --x | --y |
|---|---|---|---|---|
| feed | 0.32 | 0.45 | 0.02 | 0.50 |
| info | 0.28 | 0.40 | 0.02 | 0.04 |
| hud  | 0.22 | 0.10 | 0.76 | 0.04 |

The grammar and the attribute set are those of a ladder panel layout that was tested in game with `ui_reload_layout`. The extra HUD chrome comes from `hud_overlay.layout` in this folder. Files are written as UTF-8 without a BOM, with LF line ends. A `.layout` holds no absolute paths.

The generator is `skills/dayz-layout-preview/gen_panel_layout.py`. Examples (the three results are in this folder; `--self-test` writes fresh copies next to the generator):

```
python gen_panel_layout.py feed --rows 10 --title "CHAT" --out chat_feed.layout
python gen_panel_layout.py info --rows 6 --title "STATUS" --out info_panel.layout
python gen_panel_layout.py hud --rows 2 --out mini_hud.layout
```

## Checking

`python gen_panel_layout.py --self-test` writes the three example layouts next to the script and checks each one: `{` and `}` counts match, every `name` is unique, and each declared `FeedLineK` or `ValueK` appears exactly once. It prints `SELFTEST PASS` or `SELFTEST FAIL`.

To see a panel in game, copy the `.layout` to `$profile:`, call `ui_reload_layout(path="$profile:<file>.layout")` (unlink the previous panel first), then call `ui_set_text` with the names above.
