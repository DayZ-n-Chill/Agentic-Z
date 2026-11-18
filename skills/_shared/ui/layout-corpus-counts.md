# What shipped layouts use

Which widget classes and attributes real `.layout` files use and how often, what the less common attributes mean, and which layout checks hold up against shipped files and which only raise false alarms. The full syntax is in `layout-format.md`; an offline preview of a layout is in `layout-html-preview.md`.

The class and attribute counts come from 459 `.layout` files on a `P:\` that held vanilla plus unpacked third party mods, and the check calibration from a second scan of 819 layouts (vanilla, third party and in house mods). Both include third party layouts, so they differ from a vanilla only count. Engine facts cite the vanilla file on `P:\`.

## Widget classes

Over 459 layouts:

| Class | Count | Class | Count |
|---|---|---|---|
| `TextWidgetClass` | 2,645 | `ItemPreviewWidgetClass` | 65 |
| `PanelWidgetClass` | 2,090 | `ProgressBarWidgetClass` | 54 |
| `ImageWidgetClass` | 2,072 | `CanvasWidgetClass` | 29 |
| `FrameWidgetClass` | 1,341 | `ContentWidgetClass` (use unclear) | 20 |
| `ButtonWidgetClass` | 1,325 | `SpacerWidgetClass` | 17 |
| `GridSpacerWidgetClass` | 1,160 | `MapWidgetClass` | 16 |
| `EditBoxWidgetClass` | 508 | `ThreeStateCheckboxWidgetClass` | 10 |
| `CheckBoxWidgetClass` | 446 | `MultilineEditBoxWidgetClass` | 9 |
| `MultilineTextWidgetClass` | 351 | `VideoWidgetClass` | 5 |
| `WrapSpacerWidgetClass` | 294 | `PlayerPreviewWidgetClass` | 5 |
| `RichTextWidgetClass` | 244 | `SmartPanelWidgetClass` (use unclear) | 3 |
| `TextListboxWidgetClass` | 133 | `EmbededWidgetClass` (spelled this way) | 3 |
| `SliderWidgetClass` | 129 | `HtmlWidgetClass` | 2 |
| `ScrollWidgetClass` | 95 | `ServerBrowserWidgetClass` | 1 |
| `XComboBoxWidgetClass` | 81 | `PasswordEditBoxWidgetClass` (masked input) | 1 |
| `WindowWidgetClass` | 66 | | |

Nine classes (text, image, frame, panel, button, grid spacer, wrap spacer, scroll and edit box) make up 87 percent of all widgets, 11,530 of 13,220. Check box, multiline text, rich text, slider, combo box and text list box add about 10 percent more. Item preview, map, player preview, canvas, video and HTML widgets draw game state that a `.layout` alone can't show.

## Attributes

The top attributes over a sample of 300 layouts:

| Attribute | Count | Meaning |
|---|---|---|
| `size` | 10,349 | Unit set by `hexactsize` and `vexactsize` |
| `vexactsize`, `hexactsize` | 10,302, 10,256 | `0` fraction of the parent, `1` exact units of 1/1080 of the screen height (measured in game) |
| `vexactpos`, `hexactpos` | 10,242 each | Same units for position |
| `position` | 7,778 | |
| `ignorepointer` | 7,494 | `1` passes mouse events through |
| `valign`, `halign` | 4,518, 4,157 | `top`, `center`, `bottom`, `left`, `right`, a `*_ref` anchor, or `0` to `2` |
| `visible` | 4,173 | |
| `style` | 3,412 | A style from a `.styles` file (`styles-format.md`) |
| `text` | 3,210 | |
| `color` | 3,074 | R G B A as floats 0 to 1 |
| `clipchildren` | 2,833 | Clips children to the box |
| `font` | 2,350 | |
| `mode` | 1,697 | Image blend mode keyword |
| `priority` | 1,440 | Draw order hint within the parent |
| `image0` | 1,360 | A path or `#(argb,8,8,3)color(R,G,B,A,CO)` |
| `Margin`, `Padding` | 1,329, 1,322 | Spacer outer margin and inner padding |
| `inheritalpha` | 1,129 | `1` multiplies alpha with the parent's |
| `Rows`, `Columns` | 1,069, 1,060 | Grid spacer |
| `scaled` | 939 | Resolution scaling toggle |
| `draggable` | 884 | Sets the `DRAGGABLE` flag |
| `filter` | 756 | Texture filtering |
| `content_valign`, `content_halign` | 694, 591 | Alignment inside a spacer |
| `wrap` | 505 | Word wrap on text widgets |
| `scriptclass` | 489 | `"ViewBinding"` or a controller class |
| `userID` | 467 | Integer for lookup from script |
| `fixaspect` | 461 | Keeps the image's aspect ratio |
| `text_proportion` | 437 | Text size as a fraction of the widget height |
| `nocache` | 376 | Skips the texture cache |
| `disabled` | 317 | `DISABLED` flag |
| `stretch` | 258 | `1` makes the image fill the widget |
| `imageTexture` | 173 | Alternative to `image0` |
| `keepsafezone` | 163 | TV safe margins |
| `Progress` | 154 | A progress bar's starting value |

`wrap` sits on text widgets and on no spacer widget. Over the full 819 layouts it appears on multiline text about 355 times, rich text 236, HTML 9 and plain text 4; limited to the `gui\` folder the same count gives the 505 above. The 437 for `text_proportion` is the 300 layout sample; over 819 layouts it is 1,048 (679 text, 361 button, 5 rich text, 3 multiline), as `layout-format.md` reports.

On `P:\gui\layouts` (vanilla only), `mode` always takes a keyword: `blend` 1,721 times, `additive` 144 and `opaque` 4 (`P:\gui\layouts\day_z_ingamemenu.layout:74` and `:551`), never a number. `fixaspect` takes a keyword too: `fixwidth` 488, `inside` 67, `outside` 29 and `none` 15 (`day_z_ingamemenu.layout:72` and `:563`).

## What the less common attributes mean

| Attribute | Meaning | How sure |
|---|---|---|
| `style <name>` | A style from a `.styles` file (vanilla `P:\gui\looknfeel\dayzwidgets.styles`), unquoted. Common values: `Bold`, `DayZNormal`, `DayZInventoryButtonAll`, `Default`, `Empty`, `Colorable`, `Editor` | Seen in layouts; what the engine does with each is inferred |
| `mode blend`, `additive`, `opaque` | Image blend mode | Keywords checked on `P:\`; what each draws is not measured |
| `priority N` | Draw order within the parent; higher is on top | Inferred. From script, `SetSort` sets the value outright (`P:\scripts\1_core\proto\enwidgets.c:130`) |
| `image0` to `image7` | Image slots, switched with `SetImage(int)`; `image0` is the default | `LoadImageFile(int num, string name, bool noCache = false)` is at `enwidgets.c:257`; eight slots is not checked |
| `inheritalpha 1` | Alpha multiplied with the parent's | Common in HUDs; seen in game |
| `scaled 1` | Resolution scaling on | Inferred. `SetResolutionScale` exists only on `RenderTargetWidget` (`enwidgets.c:240`), so it isn't what this attribute calls |
| `fixaspect fixwidth`, `inside`, `outside`, `none` | Keeps the image's aspect ratio | Keywords checked on `P:\`; behaviour inferred from the names |
| `keepsafezone 1` | TV safe margins on console | Inferred from the name |
| `text_proportion 0.5` | Text height as a fraction of the widget height. Script side: `SetTextProportion(float)` (`enwidgets.c:216`). Honoured on `TextWidget`, ignored on `MultilineTextWidget` (measured in game; `preview-text-and-stringtables.md`) | API checked on `P:\` |
| `nocache 1` | Skips the texture cache, useful for generated images | Inferred from the name |

## Which layout checks are worth writing

The 819 layout scan was made to calibrate layout checks, so it shows what is normal in shipped files.

- A brace format token parser reads 807 of the 819 files (98.5 percent) without error. The 12 it can't read are XML layouts, which the validator's XML rule already catches (`scripts/tools/dayz-script-validator/scripts/detectors/layout_xml_format.py`). A simple line based parser manages only 469, because of `ScriptParamsClass` blocks (277 files), `{}` on one line (45) and children that open on their own line.
- Two clickable siblings whose rects overlap: 884 cases in 32 files, vanilla included. Even both declared `visible 1` leaves 768, and identical rects 677. Stacking widgets that script toggles is normal, so overlap is not a file defect; only a runtime tree with real visibility can show a problem.
- A child overflowing its parent: 18 cases in 12 files, all deliberate. Vanilla's `details_mode_result` is 6.0 tall as scrollable content (`P:\gui\layouts\new_ui\server_browser\pc\server_browser_tab_pages.layout:1406`).
- A duplicate widget name: 5 files (0.6 percent). A duplicate where at least one is clickable: 1 file, vanilla's `scene_editor`. Rare enough to be a real signal, and it breaks automation, because `FindAnyWidget` returns only one match.
- A class line name that differs from its `name` attribute: none in 819 files.

So four checks are worth writing: a duplicate clickable name, a clickable widget with no size, a duplicate widget name, and a name that differs from its class line. The validator does not have them yet; its layout detectors are `layout_leaf_missing_braces.py`, `layout_xml_format.py`, `es_layout_file_missing.py` and `es_layout_path_pboprefix.py`. Overlap, overflow and `ignorepointer` on a clickable widget fail the calibration, so don't write those.
