# Preview panel contract

The widget names, defaults and command line of the generated preview panels: `chat_feed.layout`, `info_panel.layout` and `mini_hud.layout` in this folder. They are loaded from `$profile:` and filled at runtime, so every text starts empty (`text ""`) and no `#STR_` key appears: a stringtable does not travel with a loose `.layout`.

Load a panel with `CreateWidgets` and fill a text with `FindAnyWidget` and `SetText`, as `../hot-iteration.md` shows. `FindAnyWidget` searches the whole tree (`P:\scripts\1_core\proto\enwidgets.c:169`), so show one panel at a time: `Unlink()` the previous root before loading the next.

## Widget names

`feed`, a chat or log:

| Name | Class | Set with `SetText` |
|---|---|---|
| `FeedRoot` | `FrameWidgetClass` | No; full screen host, `size 1 1`, `ignorepointer 1`, `priority 2000` |
| `FeedPanel` | `PanelWidgetClass` | No; `style rover_sim_colorable` |
| `TitleText` | `TextWidgetClass` | Yes, always present |
| `FeedLine0` to `FeedLine<N-1>` | `TextWidgetClass` | Yes, one per row |

`info`, labels and values:

| Name | Class | Set with `SetText` |
|---|---|---|
| `InfoRoot` | `FrameWidgetClass` | No |
| `InfoPanel` | `PanelWidgetClass` | No |
| `TitleText` | `TextWidgetClass` | Yes, always present |
| `Label0` to `Label<N-1>` | `TextWidgetClass` | Yes |
| `Value0` to `Value<N-1>` | `TextWidgetClass` | Yes |

`hud`, a small HUD:

| Name | Class | Set with `SetText` |
|---|---|---|
| `HudRoot` | `FrameWidgetClass` | No; `priority 100`, whole tree `ignorepointer 1` |
| `HudPanel` | `PanelWidgetClass` | No; `halign left`, `valign top` |
| `TitleText` | `TextWidgetClass` | Only when `--title` is given |
| `FeedLine0` to `FeedLine<N-1>` | `TextWidgetClass` | Yes |

`--title` writes its text into the comment at the top of the file, not into the widget, which stays `text ""`. Set the visible title with `SetText` on `TitleText`.

## The generator

The generator is `skills/dayz-layout-preview/gen_panel_layout.py`:

```text
python gen_panel_layout.py <feed|info|hud> --rows N [--title TEXT] --out FILE [--width W] [--height H] [--x X] [--y Y]
python gen_panel_layout.py --self-test
```

Units are fractions of the screen (all four exact flags 0); `--x` and `--y` place the panel's top left corner.

| Kind | `--width` | `--height` | `--x` | `--y` |
|---|---|---|---|---|
| `feed` | 0.32 | 0.45 | 0.02 | 0.50 |
| `info` | 0.28 | 0.40 | 0.02 | 0.04 |
| `hud` | 0.22 | 0.10 | 0.76 | 0.04 |

The grammar and attributes follow a panel layout loaded in game from `$profile:`; the extra HUD chrome comes from `hud_overlay.layout`. Files are UTF-8 with no byte order mark and LF line ends, and hold no absolute paths. The three panels in this folder came from:

```text
python gen_panel_layout.py feed --rows 10 --title "CHAT" --out chat_feed.layout
python gen_panel_layout.py info --rows 6 --title "STATUS" --out info_panel.layout
python gen_panel_layout.py hud --rows 2 --out mini_hud.layout
```

`--self-test` writes the three panels next to the script and checks that braces balance, every name is unique and each `FeedLineK` or `ValueK` appears once, then prints `SELFTEST PASS` or `SELFTEST FAIL`.

To see a panel in game, copy it to `$profile:`, unlink the previous one, load it with `CreateWidgets("$profile:<file>.layout")`, then `SetText` on the names above.
