# The `.styles` system: how a layout picks a style, what a style holds, and how to add one

How the `style` attribute of a layout widget resolves, the format and state names of a `.styles` file, the 9-slice items each widget type expects, which vanilla styles exist, and the recipe for a mod's own styles. `style` is the third most common layout attribute.

Built from a full parse of `P:\gui\looknfeel\dayzwidgets.styles` (4,462 lines in 1.29; 4,596 lines in 1.30, 28 widget
types, 130+ styles) cross-checked against all vanilla `.layout` files, plus the group mod's core library
shipped-mod example (third-party, not checked on `P:\`) and the `enwidgets.c` protos. Every count was reproduced by a second,
independent pass. The counts come from 1.29 data unless a line says 1.30; the `path:line` citations were read on a `P:\` holding 1.30,
and the lines given are the 1.30 lines.

## 1. How a layout selects a style

- Attribute: `style NAME` — **always unquoted, one token** (3,134 occurrences across the 214 vanilla
  layouts; zero quoted forms exist).
- The engine maps the layout widget class to the styles-file `<Widget Name>` by **stripping the
  `Class` suffix**: `TextWidgetClass` → `<Widget Name="TextWidget">`. Under this mapping **all 3,134
  vanilla refs resolve — zero dangling** (mechanism corroborated by the perfect data-side
  correspondence; not traced in engine binaries).
- **Style names are scoped to their widget type**: `TextWidget` has `Normal`/`Bold` while
  MultilineText/RichText use `DayZNormal`/`DayZBold` and Html has only `DayZNormal`
  (`P:\gui\looknfeel\dayzwidgets.styles:3883-3885`) — the same name can mean different things
  under different widget types, and a style must be declared under every widget type that uses it.
- **Default when `style` is omitted: unknown offline** `[verify in-game]`. 4,000+ vanilla widgets
  omit it (192 text widgets ship with neither `style` nor `font`), so an engine fallback exists, but
  nothing in scripts names it. `Widget.GetStyleName()` (`P:\scripts\1_core\proto\enwidgets.c:133`) can settle it in-game.
- Runtime API is read-only + load-only: `GetStyleName()` getter and global
  `LoadWidgetStyles(string filename)` (`P:\scripts\1_core\proto\enwidgets.c:693`). There is **no SetStyle/SetStyleName** —
  a widget's style cannot be changed at runtime; plan state changes via styles' own State system or
  script SetColor/Show.

## 2. File format

```xml
<WidgetStyles>
    <Widget Name="PanelWidget">                                   <!-- widget TYPE (class minus 'Class') -->
        <Style Name="MyStyle" Font="gui/fonts/MetronBook" ImageSet="my_set" Color="4294967295">
            <State Name="Normal">
                <Item Name="Center" Image="SomeImagesetImage" />  <!-- 9-slice items -->
            </State>
        </Style>
    </Widget>
</WidgetStyles>
```

- **Color** = decimal packed 32-bit color; `4294967295` = 0xFFFFFFFF opaque white (82% of styles,
  105/128). Every non-white value in the vanilla file is a transparency setting (alpha byte 0x00),
  not a hue.
- **Font** accepts two forms: size-suffixed atlas (`gui/fonts/sdf_MetronLight24`) or **size-less
  family** (`gui/fonts/MetronBook`) resolved via `gui/fonts/<family>.xml` `fontGenerator` descriptors
  that enumerate the baked sizes.
- **ImageSet** + each Item's **Image** refer to the imageset's registered name (line-2 `Name` field
  of the `.imageset`) and an image Name inside it — never file paths. Vanilla styles use 6 sets:
  `dayz_gui` (85 styles), `rover_imageset` (18), `ccgui_enforce` (14), `empty` (9), plus 2 minor.
  A mod style may freely reference a vanilla imageset.
- Empty `Image=""` on a slice/state is presumed to draw nothing (consistent with vanilla data;
  engine behavior inferred, not tested).

## 3. State vocabulary (complete — nothing else exists in the vanilla file)

`Normal, Pushed, Highlight, Focus, Disabled, Mark, Checked, Crossed, Empty`

- There is **no 'Hover'** (mouse-over = `Highlight`) and **no 'Pressed'** (= `Pushed`).
- Per widget kind:
  - **ButtonWidget** = Normal/Pushed/Highlight/Focus/Disabled
  - **XComboBoxWidget** = Normal/Focus/Highlight/Disabled
  - **listbox family + EditBox/PasswordEditBox/Slider** = Normal/Focus/Disabled
  - **MultilineEditBoxWidget** = Normal/Focus only (no Disabled)
  - **ProgressBar/SimpleProgressBar/Window/Panel/SmartPanel/Scroll/GridSpacer/WrapSpacer** =
    Normal/Disabled only
  - **CheckBoxWidget** = Normal/Disabled/Mark(=checked, Image "MarkDone")/Highlight
  - **ThreeStateCheckboxWidget** = Checked/Crossed/Empty/Disabled/Highlight (no Normal)
  - **graph widgets** (4) = Normal only
  - **TextWidget/MultilineText/RichText/Html** = no `<State>` blocks at all (font+color only,
    self-closing `<Style/>`)

## 4. Item-name contracts per widget type (the 9-slice system)

Base 9-slice: `LeftTop/Top/RightTop/Right/RightBottom/Bottom/LeftBottom/Left/Center` — exactly the
set for ButtonWidget, EditBoxWidget, PasswordEditBoxWidget, PanelWidget, ScrollWidget,
GridSpacerWidget, WrapSpacerWidget and the 4 graph widgets.

Extensions:
- **ProgressBarWidget** = 9 + a `Bar*` mirror of all 9 (18 items; Default style: `Center` = trough
  image, `BarCenter` = fill image, frame slices empty).
- **SimpleProgressBarWidget** = only the `Bar*` 9-set.
- **SliderWidget** = frame 9 + `Bar*` 9 (18).
- **WindowWidget** = 9 + a `Title*` mirror of all 9 (18) for the title bar.
- **XComboBoxWidget** = 9 + `ArrowLeft` + `ArrowRight` (11).
- **SmartPanelWidget** = 9 + `Overlay` (10).
- **CheckBoxWidget / ThreeStateCheckboxWidget** = a single Item named `CheckBox`.
- **MultilineEditBoxWidget** = a single Item named `Highlight` (text-selection highlight). The
  single-line EditBoxWidget style has no Highlight item — plain 9-slice border only.
- **Listbox family** (GenericListbox/UniversalListbox/ServerBrowser/TextListbox) = identical 31-item
  union: 9-slice with `*Center` edge naming (`TopCenter/BottomCenter/LeftCenter/RightCenter`) +
  `Header*` 9-set + `TitleLeftCenter/TitleCenter/TitleRightCenter` + `TitleCenterSeparator` +
  `Separator/TopSeparator/BottomSeparator` + `ScrollBarTop/ScrollBarCenter/ScrollBarBottom` +
  `Highlight` + `LeftTopWithTitle/RightTopWithTitle`.

## 5. The 'Colorable' mechanism (why script SetColor works on styled widgets)

`ButtonWidget/Colorable` (`P:\gui\looknfeel\dayzwidgets.styles:2167-2223`): `Color="0"` + `Center Item = "WhitePixel"`
(a 1×1 white region, `P:\gui\imagesets\rover_imageset.imageset:11-14`) in **all 5 states** → the widget renders a
white pixel that script `SetColor(ARGB)` then tints. **This is the verified mechanism behind the
skill fact "ButtonWidget.SetColor() works directly, no LoadImageFile needed"** — it holds for styles
whose Center is a white/colorable image (the WhitePixel Center is the load-bearing part;
`WindowWidget/Colorable` keeps Color=white and is still colorable via its WhitePixel Center).

Also style-driven for free: ButtonWidget/Default overlays
`alpha_176` on Pushed (`P:\gui\looknfeel\dayzwidgets.styles:1617`), `alpha_128` on Focus (`:1639`) and
`alpha_64` on Disabled (`:1650`) — **picking `style Default` on a button gives
working press/focus/disabled visual feedback with zero script**. Its `Normal` state has every
slice empty (`P:\gui\looknfeel\dayzwidgets.styles:1598-1608`), so at rest it draws no body. A button declared with a `color` and no
`style` drew no fill in game, while the same frame's `style Colorable` button did (measured in game
).

## 6. Style inventory (what exists to pick from — most-used names)

28 widget types have styles; **ImageWidget and FrameWidget have no entry** (never styleable).
Top vanilla usage: `PanelWidget/rover_sim_colorable` 577×, `GridSpacerWidget/DayZDefaultPanel` 455×,
`PanelWidget/blank` 210×, `TextWidget/Normal` 174×, `ButtonWidget/Colorable` 174×.

Highlights per type (full inventory in the styles file itself):
- TextWidget: `Normal, Bold, Light, None` · MultilineText/RichText: `DayZNormal, DayZBold` · Html: `DayZNormal`
- ButtonWidget (22): `Default, Colorable, Empty, EmptyHighlight, MainMenu, MenuDefault, Editor,
  InventoryActionMenu, OldStyle, DayZDefaultButton(+NoBorder/Bottom/Sides/Top/All/_DisabledState),
  DayZInventoryButton(All/Top/Bottom/Right/Left)`
- PanelWidget (22+): `rover_sim_colorable, blank, Outline, ColorablePanel, editor_quad,
  editor_quad_dark, dashed, DayZDefaultPanel(+Left/Right/Top/Bottom/Sides), ToolbarWidget,
  UIDefaultPanel, rover_sim_black(_2), InventoryPanel, EditorPanel, editor_selection`,
  **`ActionWidget` (DayZ 1.30)**
- ProgressBarWidget: `Default, DayZLoading, Stamina, Quantity, Loading`
- Styles exist for XComboBox/SmartPanel/Html/ThreeStateCheckbox/graph widgets too. Seven types have
  styles but no instance in any vanilla layout: the 4 graph widgets (BasicGraph, RingBufferGraph,
  TimeBasedGraph, TimeBasedGraphWithAxes), GenericListboxWidget, UniversalListboxWidget and
  SimpleProgressBarWidget.

### The `ActionWidget` style (added in DayZ 1.30)

In DayZ 1.30 (`P:\gui\looknfeel\dayzwidgets.styles:3700-3723`), a new style `ActionWidget`
was introduced for `PanelWidget`. The same name is declared again under `GridSpacerWidget`
(`:4280`) and `WrapSpacerWidget` (`:4570`), as the rule of section 1 requires for a style used on
more than one widget type. The `PanelWidget` declaration:

```xml
<!-- [EXACT] P:\gui\looknfeel\dayzwidgets.styles:3700 -->
<Style Name="ActionWidget" Font="gui/fonts/AmorSerifPro-Bold" ImageSet="dayz_gui" Color="0">
    <State Name="Disabled">
        <Item Name="Bottom" Image="ActionWidgetGradientBottom" />
        <Item Name="Center" Image="ActionWidgetGradientCenter" />
        <Item Name="Left" Image="ActionWidgetGradientLeft" />
        <Item Name="LeftBottom" Image="ActionWidgetGradientLeftBottom" />
        <Item Name="LeftTop" Image="ActionWidgetGradientLeftTop" />
        <Item Name="Right" Image="ActionWidgetGradientRight" />
        <Item Name="RightBottom" Image="ActionWidgetGradientRightBottom" />
        <Item Name="RightTop" Image="ActionWidgetGradientRightTop" />
        <Item Name="Top" Image="ActionWidgetGradientTop" />
    </State>
    <State Name="Normal">
        <Item Name="Bottom" Image="ActionWidgetGradientBottom" />
        <Item Name="Center" Image="ActionWidgetGradientCenter" />
        <Item Name="Left" Image="ActionWidgetGradientLeft" />
        <Item Name="LeftBottom" Image="ActionWidgetGradientLeftBottom" />
        <Item Name="LeftTop" Image="ActionWidgetGradientLeftTop" />
        <Item Name="Right" Image="ActionWidgetGradientRight" />
        <Item Name="RightBottom" Image="ActionWidgetGradientRightBottom" />
        <Item Name="RightTop" Image="ActionWidgetGradientRightTop" />
        <Item Name="Top" Image="ActionWidgetGradientTop" />
    </State>
</Style>
```

**What it does:** It builds a parametric 9-slice gradient frame around interaction widgets using cut slices
from the `dayz_gui` imageset (`ActionWidgetGradient*`).
Where the HUD uses it, read on a `P:\` holding 1.30.164014: `style ActionWidget` sits on the two
`GridSpacerWidgetClass` containers of the action cursor:
`ActionTargetsCursorWidget` (`P:\gui\layouts\day_z_hud.layout:2271`, style at `:2287`) and `ItemActions` (`:3844`, style at `:3859`).
The five interaction widgets inside (`item` at `:2294`, `interact` `:2477`, `continuous_interact` `:2755`,
`single` `:3033`, `continuous` `:3249`) are `PanelWidgetClass` with no `style` line of their own.
In 1.29 the interaction prompts were `ImageWidgetClass` widgets loading `linear_gradient.edds` or
`card_drop.edds`; that half cannot be read on a 1.30 `P:\`.

## 7. Custom-style recipe (production-proven, the group mod's core library)

1. **File** `<ModDir>/gui/styles/<name>.styles` — one `<Widget>` block per target widget type (the
   style must be declared separately under each type it will be used on; the group mod's core library declares
   `My_Clean_outline` twice: under PanelWidget and GridSpacerWidget, `my.styles:2-27/28-53`).
   The outline-only trick: Normal state sets the 8 border slices to `Image="pixel"` and
   `Center=""`.
2. **Registration** in `config.cpp` inside `CfgMods > <ModName> > class defs`:
   ```cpp
   class widgetStyles { files[] = {"MyMod/gui/styles/my.styles"}; };
   class imageSets    { files[] = {"MyMod/gui/imagesets/my_set.imageset"}; };
   ```
   (prefix-relative path, no leading slash). **An unregistered .styles file is inert** —
   the group mod ships a dead `customStyles.styles` with no registration and no refs: anti-example.
3. **Usage**: `style My_Clean_outline` on matching widget classes in the mod's layouts.
   Registration is **global**: the group mod uses the style registered by its Core dependency
   (requiredAddons) without registering anything itself.
4. **Merge semantics**: a mod `.styles` file adds styles to existing vanilla widget types —
   additive merge with `dayzwidgets.styles`, not replacement (evidenced by shipped layouts mixing
   `My_Clean_outline` and vanilla `rover_sim_colorable` in the same file; runtime semantics inferred
   from shipped-mod structure). Custom styles may reference vanilla fonts and imagesets.
5. **Workbench preview**: also register the .styles/.imageset in `dayz.gproj` or the Layout Editor
   renders them blank — see `plan-to-implementation.md`, section 3 (dual registration).

## 8. Practical guidance

- Building a themed panel/button UI? **Reach for a style before hand-composing Image+Text widgets**:
  a 9-slice style gives borders, state feedback (press/focus/disabled) and script-tintability
  (WhitePixel Center + SetColor) declaratively.
- Debugging "my style does nothing": (1) is the style declared under this widget's type (Class-suffix
  stripped)? (2) is the .styles file registered in `config.cpp class defs > widgetStyles`? (3) does
  the ImageSet name (not filename) resolve? (4) for Workbench preview, is it in dayz.gproj?
- The HTML renderer (`scripts/tools/dayz-layout-viewer/build_viewer.py`) does not resolve styles — styled widgets preview as
  invisible/plain. Note it in the spec and rely on in-game verification for styled chrome.


---

## Before writing `style X`, check the block of that widget type (measured in game)

The style namespace is **per widget type**, and a name borrowed from another
type fails **silently**: no load error, no warning, no log line. The widget
simply has no ImageSet to tint, so its `color` never paints and you get text
floating over the game world.

Real case, cost a full in-game session to notice and a human to see it:
`MCPDialogPanel` is a `PanelWidgetClass` and declared `style Colorable`.

- `<Widget Name="WindowWidget">` does declare `Colorable` (6 styles: Default,
  rover_sim_black, rover_sim_black_2, Colorable, Simple, debugUI).
- `<Widget Name="PanelWidget">` declares 21 styles (22 on 1.30, which adds `ActionWidget`) and **none** is
  `Colorable`: the block runs from `P:\gui\looknfeel\dayzwidgets.styles:3233` to `:3724`, and its two
  nearest names are `rover_sim_colorable` (`:3284`) and `ColorablePanel` (`:3388`).

### The obvious-looking replacement is a second trap (measured the same night)

`ColorablePanel` does exist for `PanelWidget`, so switching to it passes the
name check above — and still paints nothing. Its `Normal` state is
`<Item Name="Center" Image="" />`: an empty skin. The rename fixed the grep and
not the pixel, and the panel stayed invisible through a full repack, deploy and
relaunch. Two in-game cycles spent on a name.

The real equivalent of `WindowWidget/Colorable` is
**`PanelWidget/rover_sim_colorable`**: `Center="WhitePixel"` +
`Color="4294967295"`, the identical mechanism — a white pixel tinted by the
widget's own `color`. It is also the most-used panel style in all of vanilla
(577x, section 6 above), in `day_z_hud.layout`,
`day_z_connection_dialogue.layout`, `day_z_ingamemenu.layout` and about 100 layouts in all
under `P:\gui\layouts` on 1.30.

**Pick a style by what it draws, never by what it is called.** `ColorablePanel`
sounds like the panel flavour of `Colorable` and is not; `rover_sim_colorable`
sounds like simulation chrome and is exactly it. The mechanical query is one
pass over the file: inside `<Widget Name="<YourType>">`, list the styles whose
`<State Name="Normal">` carries a **non-empty** `Center` image. Anything with
`Center=""` is a no-op skin however promising the name, and the engine will
never tell you.

So the name was real, the layout looked plausible, vanilla itself uses
`style Colorable` on `P:\gui\layouts\dialog.layout:1-16` — but that is a
`WindowWidgetClass`. Same word, different type, nothing painted.

**The check is mechanical:** open `P:\gui\looknfeel\dayzwidgets.styles`, find
`<Widget Name="<YourWidgetType>">`, confirm the style name is inside that block.
Having seen the name in another working layout proves nothing.

**And grep the XML as XML.** This file is `<WidgetStyles><Widget Name=...>
<Style Name=... ImageSet=.../>`. A grep written for the brace format returns
zero hits and reads as "that style does not exist anywhere" — a false negative
that sounds like an answer.
