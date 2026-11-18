# Widget styles

How the `style` attribute of a layout widget finds its style, what a `.styles` file holds, which states and 9-slice items each widget type uses, which vanilla style draws what, and how to add a mod's own styles. `style` is the third most common layout attribute.

The vanilla file is `P:\gui\looknfeel\dayzwidgets.styles`: 28 widget types and more than 130 styles. Counts are over the vanilla layouts under `P:\gui\layouts`.

## How a layout picks a style

- `style NAME` is always unquoted and one token. Vanilla layouts use it 3,134 times and never quote it.
- The layout class maps to the `<Widget Name>` of the styles file by dropping the `Class` suffix: `TextWidgetClass` reads `<Widget Name="TextWidget">`. Under that rule every vanilla reference resolves.
- Style names belong to their widget type. `TextWidget` has `Normal` and `Bold`, `MultilineTextWidget` and `RichTextWidget` use `DayZNormal` and `DayZBold`, and `HtmlWidget` has only `DayZNormal` (`P:\gui\looknfeel\dayzwidgets.styles:3883`). A style used on two widget types is declared under both.
- A name borrowed from another type fails without a load error, a warning or a log line: the widget gets nothing to draw, so its `color` never paints and text floats over the world.
- Unverified (not tested in game): which style a widget gets when it names none. More than 4,000 vanilla widgets leave `style` out. `Widget.GetStyleName()` (`P:\scripts\1_core\proto\enwidgets.c:133`) can tell you in game.
- A style cannot change at runtime. Script has `GetStyleName()` and the global `LoadWidgetStyles(string filename)` (`:693`) and no `SetStyle`; change looks through the style's own states, `SetColor` or `Show`.

## File format

```xml
<WidgetStyles>
    <Widget Name="PanelWidget">
        <Style Name="MyMod_Outline" Font="gui/fonts/MetronBook" ImageSet="my_set" Color="4294967295">
            <State Name="Normal">
                <Item Name="Center" Image="SomeImage" />
            </State>
        </Style>
    </Widget>
</WidgetStyles>
```

- `Color` is a decimal packed 32 bit color; `4294967295` is `0xFFFFFFFF`, opaque white, on 105 of 128 vanilla styles. Every other vanilla value only changes transparency.
- `Font` is a sized atlas (`gui/fonts/sdf_MetronLight24`) or a family with no size (`gui/fonts/MetronBook`), resolved through the `gui/fonts/<family>.xml` descriptors that list the baked sizes.
- `ImageSet` and each `Image` are the imageset's registered name and an image name in it, never file paths. Vanilla styles use six sets, mostly `dayz_gui`, `rover_imageset`, `ccgui_enforce` and `empty`. A mod style may use a vanilla imageset.
- An empty `Image=""` draws nothing for that slice and state.

## States

The whole vocabulary is `Normal`, `Pushed`, `Highlight`, `Focus`, `Disabled`, `Mark`, `Checked`, `Crossed` and `Empty`. There is no `Hover` (mouse over is `Highlight`) and no `Pressed` (it is `Pushed`).

| Widget type | States |
|---|---|
| `ButtonWidget` | `Normal`, `Pushed`, `Highlight`, `Focus`, `Disabled` (`P:\gui\looknfeel\dayzwidgets.styles:1598` to `:1642`) |
| `XComboBoxWidget` | `Normal`, `Focus`, `Highlight`, `Disabled` |
| List boxes, `EditBoxWidget`, `PasswordEditBoxWidget`, `SliderWidget` | `Normal`, `Focus`, `Disabled` |
| `MultilineEditBoxWidget` | `Normal`, `Focus` |
| Progress bars, window, panel, smart panel, scroll and spacers | `Normal`, `Disabled` |
| `CheckBoxWidget` | `Normal`, `Disabled`, `Mark` (checked, image `MarkDone`), `Highlight` |
| `ThreeStateCheckboxWidget` | `Checked`, `Crossed`, `Empty`, `Disabled`, `Highlight`; no `Normal` |
| The four graph widgets | `Normal` |
| `TextWidget`, `MultilineTextWidget`, `RichTextWidget`, `HtmlWidget` | No states: font and color only |

## 9-slice items per widget type

The base set is `LeftTop`, `Top`, `RightTop`, `Right`, `RightBottom`, `Bottom`, `LeftBottom`, `Left` and `Center`. Button, edit box, password edit box, panel, scroll, both spacers and the graph widgets use exactly that.

| Widget type | Items |
|---|---|
| `ProgressBarWidget` | The nine plus a `Bar*` copy of all nine; `Center` is the trough, `BarCenter` the fill |
| `SimpleProgressBarWidget` | Only the `Bar*` nine |
| `SliderWidget` | The nine plus the `Bar*` nine |
| `WindowWidget` | The nine plus a `Title*` copy for the title bar |
| `XComboBoxWidget` | The nine plus `ArrowLeft` and `ArrowRight` |
| `SmartPanelWidget` | The nine plus `Overlay` |
| `CheckBoxWidget`, `ThreeStateCheckboxWidget` | One item, `CheckBox` |
| `MultilineEditBoxWidget` | One item, `Highlight`, the selection; the single line edit box has none |
| List boxes (generic, universal, server browser, text) | The same 31 items: edges named `TopCenter` and so on, a `Header*` nine, `TitleLeftCenter`, `TitleCenter`, `TitleRightCenter`, `TitleCenterSeparator`, `Separator`, `TopSeparator`, `BottomSeparator`, `ScrollBarTop`, `ScrollBarCenter`, `ScrollBarBottom`, `Highlight`, `LeftTopWithTitle` and `RightTopWithTitle` |

## Styles that draw a tintable fill

`SetColor` tints a styled widget only when its style draws a white image. `WhitePixel` is a 1x1 white region of `rover_imageset` (`P:\gui\imagesets\rover_imageset.imageset:11`).

| Style | Type | Normal state | Use |
|---|---|---|---|
| `Colorable` | `ButtonWidget` | `Center` `WhitePixel` in all five states, `Color="0"` (`P:\gui\looknfeel\dayzwidgets.styles:2167`) | A button `SetColor` can fill |
| `Colorable` | `WindowWidget` | `WhitePixel` centre, white color | Vanilla dialogs (`P:\gui\layouts\dialog.layout:16`) |
| `rover_sim_colorable` | `PanelWidget` | `WhitePixel` in all nine slices (`:3284`) | The panel to tint; 641 uses in 100 vanilla layouts |
| `ColorablePanel` | `PanelWidget` | Every slice `Image=""` (`:3388`) | Draws nothing despite its name |
| `Default` | `ButtonWidget` | Every slice empty (`:1598` to `:1608`) | Draws no body at rest; `alpha_176` on `Pushed` (`:1617`), `alpha_128` on `Focus` (`:1639`), `alpha_64` on `Disabled` (`:1650`) |
| `EmptyHighlight` | `ButtonWidget` | Empty, but `Focus` has `Center` `WhitePixel` (`:2224`, `:2236`, `:2238`) | Fills white on focus; set a body `color` |

`PanelWidget` has no `Colorable`: its block runs from `P:\gui\looknfeel\dayzwidgets.styles:3233` to `:3724`. Pick a style by what it draws, never by its name. Inside `<Widget Name="<YourType>">`, list the styles whose `Normal` state has a non-empty `Center`; anything with `Center=""` paints nothing and the engine never says so. The file is XML: a search written for the brace format finds nothing and reads like "that style does not exist".

Measured in game: a button with a `color` and no `style` drew no fill, while a `style Colorable` button in the same frame did. A `PanelWidget` with `style Colorable` drew nothing, and switching it to `ColorablePanel` still drew nothing.

## Vanilla styles to pick from

`ImageWidget` and `FrameWidget` have no styles. The most used are `PanelWidget/rover_sim_colorable`, `GridSpacerWidget/DayZDefaultPanel`, `PanelWidget/blank`, `TextWidget/Normal` and `ButtonWidget/Colorable`.

- `TextWidget`: `Normal`, `Bold`, `Light`, `None`.
- `ButtonWidget` (22): `Default`, `Colorable`, `Empty`, `EmptyHighlight`, `MainMenu`, `MenuDefault`, `Editor`, `InventoryActionMenu`, `OldStyle`, the `DayZDefaultButton` family and the `DayZInventoryButton` family.
- `PanelWidget` (22): `rover_sim_colorable`, `blank`, `Outline`, `ColorablePanel`, `editor_quad`, `editor_quad_dark`, `dashed`, the `DayZDefaultPanel` family, `ToolbarWidget`, `UIDefaultPanel`, `rover_sim_black`, `rover_sim_black_2`, `InventoryPanel`, `EditorPanel`, `editor_selection` and, new in 1.30, `ActionWidget`.
- `WindowWidget` (6): `Default`, `rover_sim_black`, `rover_sim_black_2`, `Colorable`, `Simple`, `debugUI`.
- `ProgressBarWidget`: `Default`, `DayZLoading`, `Stamina`, `Quantity`, `Loading`.
- Seven types have styles and no vanilla layout uses them: the four graph widgets, `GenericListboxWidget`, `UniversalListboxWidget` and `SimpleProgressBarWidget`.

`ActionWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3700`) builds a 9-slice gradient frame from the `ActionWidgetGradient*` images of `dayz_gui` in its `Normal` and `Disabled` states. It is declared again under `GridSpacerWidget` (`:4280`) and `WrapSpacerWidget` (`:4570`). The HUD sets it on the two action cursor containers, `ActionTargetsCursorWidget` (`P:\gui\layouts\day_z_hud.layout:2271`, style at `:2287`) and `ItemActions` (`:3844`, style at `:3859`); the prompt rows inside are `PanelWidgetClass` with no style of their own (`ui-changes-1-30.md`).

## A mod's own styles

A group mod's core library ships a working example; this recipe follows it.

1. Write `MyMod/gui/styles/mymod.styles` with one `<Widget>` block per widget type the style is used on. For an outline only frame, set the eight border slices to `Image="pixel"` and `Center=""`.
2. Register it in `config.cpp`, `CfgMods`, `class defs`: `class widgetStyles { files[] = {"MyMod/gui/styles/mymod.styles"}; };` (`script-recipes.md`). An unregistered file does nothing.
3. Use it with `style MyMod_Outline` on widgets of a matching class. Registration is global: a mod that requires the one registering a style can use it without registering anything.
4. A mod file adds styles to the vanilla widget types; shipped layouts mix mod and vanilla styles in one file. That is read from shipped mods, not measured. A shadow PBO of `dayzwidgets.styles` itself replaces the whole file (`layout-variants.md`).
5. For the Workbench Layout Editor, list the file in `dayz.gproj` too, or the editor draws it blank (`plan-to-implementation.md`).

When a style does nothing, check in order: is it declared under this widget's type; is the `.styles` file registered; does the `ImageSet` name (not file name) resolve; for the editor, is it in `dayz.gproj`. The HTML viewer does not read styles, so styled widgets preview plain; check styled chrome in game.
