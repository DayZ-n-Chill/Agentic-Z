# Layout file syntax and widget classes

How a `.layout` file is written: the brace grammar, the lexer details a tool must handle, the two ways a widget gives its name, and which widget classes exist and draw.

A `.layout` uses the Enfusion brace format, not XML: an XML layout crashes the native `CreateWidgets`, where no null check can catch it. Attributes are in `layout-attributes.md`, screen rects in `layout-geometry.md`, copyable blocks and the delivery checks in `layout-snippets.md`.

## The grammar

A widget is `WidgetClassName WidgetName { properties { children } }`. Properties are one per line, with no semicolons (unlike `config.cpp`). Comments are `//` line comments or `/* ... */` blocks, never `<!-- -->`.

- An empty leaf block `{ }` is optional. What breaks loading is unbalanced braces and XML; the parser stops at the first syntax error and drops every widget after it without a word (`checklist-and-troubleshooting.md`).
- A file is a sequence of widgets, not a single root, so a reader that parses one widget and stops loses every sibling after it without an error. The parser in `scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py` (`Parser.parse_layout`) collects roots until the end of the file. Whether `CreateWidgets` keeps every root of such a file is not measured.
- Inline form is valid: `ImageWidgetClass Bg { position 0 0 size 1 1 stretch 1 }`. A reader must split values by the number of values each key takes (`position` and `size` two, a flag one), not by the physical line, or the whole line collapses into one attribute. `parse.py` does this through its `ATTRIBUTE_ARITY` table; a key missing from that table still falls back to the physical line.
- Floats may have no digit before or after the point: `.5` and `1.` are both valid (`size .5 -0.5` in `scripts/tools/dayz-script-validator/tests/fixtures/layout_braces/ok_inline_widget.layout`).

## Strings that continue on the next line

A quoted string can carry on to the next line: close the quotes, write a backslash, a newline, then the next quoted part.

```text
text "Alpha"\
    "Beta"
```

Measured in game: `ButtonWidget.GetText(out string)` (`P:\scripts\1_core\proto\enwidgets.c:389`) returns `"Alpha\nBeta"`, ten characters, so the join inserts exactly one line feed. A file saved with CRLF gives the same ten characters; the engine normalises line ends before the join. Some trader mod tooltip layouts use this form, so a reader that rejects `\` cannot open them. `parse.py` handles it in `_scan_continuation`.

## Widget names: in the header or on a Name line

Most vanilla layouts put the name in the header: `FrameWidgetClass FrameWidget {` (`P:\gui\layouts\day_z_ingamemenu.layout:1`). Some leave it out of the header, which then holds the class alone or the class and the widget's ID, and give the name as the first property: `WrapSpacerWidgetClass "{00000000CDEFDF47}" {` then `Name "top"` (`P:\gui\layouts\xbox\day_z_ingamemenu_xbox.layout:232` and `:233`). Ten of the 227 vanilla layouts on `P:\` use the ID form: the in game HUD `day_z_hud.layout` (`ActionListItem0` at `P:\gui\layouts\day_z_hud.layout:48` and `:49`) and nine console, Xbox, debug or editor layouts. The game reads both forms, so a tool must read both, and a script that looks up a HUD widget by name still finds it.

The ID is the one a 1.30 layout variant writes in `Prefab`; how it is derived is in `layout-variants.md`. `parse.py` takes the token after the class as the name, so on the second form it reports the ID string or an empty name and keeps the real name as a `Name` attribute (`Parser.parse_widget`).

## Containers

| Layout class | Script class | Draws | Notes |
|---|---|---|---|
| `FrameWidgetClass` | `Widget` | no | Invisible container, the most common parent |
| `PanelWidgetClass` | `Widget` | only through a `style` | Without a style it is invisible like a frame; vanilla scripts declare no `PanelWidget` class |
| `ScrollWidgetClass` | `ScrollWidget` | no | Scrolls a spacer child |
| `GridSpacerWidgetClass` | `GridSpacerWidget` | no | Places its children in a grid |
| `WrapSpacerWidgetClass` | `WrapSpacerWidget` | no | Flows its children and wraps them to the next row |
| `SpacerWidgetClass` | `SpacerWidget` | no | Base of the two spacers above |
| `WindowWidgetClass` | `Widget` | through a `style` | Window with a title bar; no `WindowWidget` script class exists |

The spacer family is declared at `P:\scripts\1_core\proto\enwidgets.c:460` (`SpacerBaseWidget`), `:465`, `:473`, `:477` and `:481` (`ScrollWidget`). A spacer recomputes its children's boxes, which matters for geometry (`layout-geometry.md`).

## Widgets that draw

| Layout class | Script class | Notes |
|---|---|---|
| `ImageWidgetClass` | `ImageWidget` | Backgrounds, icons, colored panels |
| `TextWidgetClass` | `TextWidget` | One line of text; does not wrap (`text-sizing-and-rendering.md`) |
| `MultilineTextWidgetClass` | `MultilineTextWidget` | Wrapping text with `wrap 1` |
| `RichTextWidgetClass` | `RichTextWidget` | Markup and inline imageset icons |
| `HtmlWidgetClass` | `HtmlWidget` | Rich text that loads a file, for notes and books |
| `ButtonWidgetClass` | `ButtonWidget` | Takes `OnClick`; its body draws through its style |
| `EditBoxWidgetClass`, `PasswordEditBoxWidgetClass` | `EditBoxWidget`, `PasswordEditBoxWidget` | One line of input; the second masks it |
| `MultilineEditBoxWidgetClass` | `MultilineEditBoxWidget` | Several lines of input |
| `CheckBoxWidgetClass`, `ThreeStateCheckboxWidgetClass` | `CheckBoxWidget` | Toggle |
| `XComboBoxWidgetClass` | `XComboBoxWidget` | Value picker with arrows |
| `SliderWidgetClass` | `SliderWidget` | Value between a minimum and a maximum |
| `ProgressBarWidgetClass`, `SimpleProgressBarWidgetClass` | `ProgressBarWidget`, `SimpleProgressBarWidget` | Bars |
| `TextListboxWidgetClass` | `TextListboxWidget` | Rows and columns |
| `CanvasWidgetClass` | `CanvasWidget` | Lines drawn from script |
| `VideoWidgetClass` | `VideoWidget` | Video playback |
| `MapWidgetClass` | `MapWidget` | The map (`P:\scripts\3_game\gameplay.c:322`) |
| `ItemPreviewWidgetClass`, `PlayerPreviewWidgetClass` | `ItemPreviewWidget`, `PlayerPreviewWidget` | 3D renders (`preview-widgets.md`) |
| `RTTextureWidgetClass` | `RTTextureWidget` | "Texture used as render target for children widgets" (`P:\scripts\1_core\proto\enwidgets.c:28`); dead from script (`text-sizing-and-rendering.md`) |

`ScriptParamsClass` is not a widget: it holds the parameters a `scriptclass` receives (`layout-scriptclass.md`). Which classes and attributes real layouts use, and how often, is in `layout-corpus-counts.md`.
