# Previewing a layout as HTML

What a static HTML preview of a `.layout` can and can't show, how to run the repo's viewer, and when a preview needs more than the core widget set. For a picture drawn at several screen sizes use `/dayz-layout-preview`; for a layout on the running client use `hot-iteration.md`.

## Running the viewer

```cmd
python scripts/tools/dayz-layout-viewer/build_viewer.py <input.layout> [-o output.preview.html] [--layout-root DIR]
```

Open the `.html` in a browser. It switches between 1080p, 1440p, 21:9 and 720p. `verification.md`, section "What the HTML viewer can and cannot show", lists what the viewer adds over a plain static preview.

## What a static preview can show

| Aspect | Shown | How |
|---|---|---|
| The nine core classes (frame, image, text, button, edit box, scroll, grid spacer, wrap spacer, panel) | Yes | They make up 87 percent of shipped widgets (`layout-corpus-counts.md`) |
| Position and size, both unit modes, `halign` and `valign` anchors | Yes | |
| `color` | Yes | As a background or text color |
| Generated color images `#(argb,...)color(...)` | Yes | As a flat color |
| `.paa` textures | No | Needs a texture decoder, such as the one in `scripts/tools/dayz-3d-viewer/` |
| `text "..."` | Yes | A `#STR_KEY` key shows as the placeholder `[#STR_KEY]` |
| Dabs `scriptclass "ViewBinding"` | Yes | Not drawn; the binding name shows as a placeholder when the widget has no text |
| `ScriptParamsClass` | Yes | Not drawn |
| `Relay_Command` | Yes | Only in the hover info, as `relay -> <command>` |
| `Metron` against `MetronBook` | Yes | As a heavier and a lighter weight |
| `text halign`, `text valign` | Yes | |
| `clipchildren`, `ignorepointer`, `visible 0` | Yes | `clipchildren` and `visible 0` as CSS `overflow: hidden` and `display: none`; `ignorepointer` only in the hover info |
| Animations | No | A static picture |
| Live binding data | No | Placeholders only |
| Item preview, map and player preview widgets | No | They need game state |
| `style` | No | Until the preview reads `.styles` files |

A static preview has drawn a large sorter menu layout (196 widgets) with its row and tag layouts, and third party layouts such as `BaseBuildingPlus/Book.layout`, `CodeLock/enterComboCode.layout` and `A6_Gunplay/ItemStatsDisplay`.

Its output can apply default colors when a layout sets none (mods usually color widgets from script with `SetColor`), outline each widget by type, show binding names as badges, and show a widget's type, name, position, size, `ignorepointer` and relay command on hover.

## Its limits

- It can't match colors exactly. Mods call `SetColor(ARGB)` after `CreateWidgets`, which a file can't reveal, so default colors are a guess from widget names such as `PanelBg` or `HeaderBg`.
- It can't use the game font. Metron is Bohemia's own; a preview falls back to Bahnschrift, Roboto Condensed or Arial Narrow, and spacing differs by about 5 percent.
- It doesn't run script. Widgets placed or resized at run time, such as a restack after a visibility change (`stacking-and-clickability.md`), stay where the file puts them.
- It ignores `style`.

## When a preview needs more

Extend a preview when you use widgets outside the core nine regularly, when you want to preview a vanilla menu (they lean heavily on `style`, so the preview has to read `.styles` files), when you need rich text `<image>` and `<font>` tags drawn, or when you need multiline text broken into lines. For each addition, count how shipped layouts use the attribute (`layout-corpus-counts.md`), check it against the engine declarations in `P:\scripts\1_core\proto\enwidgets.c` (summarised in `widget-prototypes.md`), and test it on one layout of your own and one third party layout.
