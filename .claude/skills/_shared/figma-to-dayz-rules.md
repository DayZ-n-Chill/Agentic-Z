# Figma to DayZ `.layout` Rules

Canonical translation rules for the Figma-to-DayZ pipeline (`figma-node-normalizer` → `figma-to-dayz-layout` → `dayz-layout-validator`). Cited by all three agents.

For the exhaustive widget catalog and property reference, see [`enscript/references/gui_layout.md`](enscript/references/gui_layout.md). This doc covers translation rules only.

---

## 1. The format is not XML

DayZ `.layout` files use a custom property-file format. They are not XML, not JSON, not YAML.

```
WidgetClassNameClass WidgetName {
 property value
 property value
 {
  ChildWidgetClass ChildName {
   property value
  }
 }
}
```

Three rules that cover the syntax:

- Class names always end in `Class`. `FrameWidget` is wrong, `FrameWidgetClass` is right.
- Properties are bare key-value pairs on their own line. No `=`, no `:`, no semicolons, no quoted attribute values. The value follows the key separated by a space.
- The child `{ }` block goes inside the parent's braces, AFTER all of the parent's own properties. A widget may have multiple child blocks (the second is conventionally for `ScriptParamsClass` parameter blocks).

Multi-word property keys are quoted, values still are not:

```
text "Status: OK"
"exact text" 1
"exact text size" 18
"text halign" right
```

Loaded in script via `GetGame().GetWorkspace().CreateWidgets("gui/layouts/MyMod/file.layout", parent)`.

---

## 2. Format cheat sheet

Minimum viable widget block:

```
PanelWidgetClass MyPanel {
 color 0.0863 0.0863 0.0863 0.902
 position 0 0
 size 460 340
 halign center_ref
 valign center_ref
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
}
```

Six properties every visible widget cares about:

| Property | What |
| --- | --- |
| `position X Y` | X and Y offset from parent's anchor point |
| `size W H` | Width and height |
| `hexactpos` | `1` = position is pixels, `0` = fraction of parent width (0..1) |
| `vexactpos` | `1` = position is pixels, `0` = fraction of parent height (0..1) |
| `hexactsize` | `1` = size is pixels, `0` = fraction of parent width |
| `vexactsize` | `1` = size is pixels, `0` = fraction of parent height |

Alignment anchors place the widget against a side or center of the parent. `halign` values: `left`, `right`, `center_ref`, `left_ref`, `right_ref`. `valign` values: `top`, `bottom`, `center_ref`, `top_ref`, `bottom_ref`. The `_ref` variants use the parent's reference frame, not its raw bounds.

See `enscript/references/gui_layout.md` for the full property catalog (`ignorepointer`, `priority`, `disabled`, `clipchildren`, fonts, styles, etc.) and the full widget class list.

---

## 3. Figma to DayZ widget mapping

Layer kind is the primary signal. Naming prefix breaks ties when the kind is generic. All widget names end in `Class`.

| Figma source | DayZ widget |
| --- | --- |
| Top-level frame | `FrameWidgetClass` |
| Frame with solid fill / background | `PanelWidgetClass` |
| Modal / window with title bar | `WindowWidgetClass` |
| Text layer | `TextWidgetClass` |
| Text layer with rich-text formatting | `RichTextWidgetClass` |
| Multi-line read-only text block | `MultilineTextWidgetClass` |
| Image / image fill / vector icon | `ImageWidgetClass` |
| Rectangle named `btn_*` | `ButtonWidgetClass` |
| Single-line input | `EditBoxWidgetClass` |
| Multi-line input | `MultilineEditBoxWidgetClass` |
| Password input | `PasswordEditBoxWidgetClass` |
| Checkbox / toggle | `CheckBoxWidgetClass` |
| Slider | `SliderWidgetClass` |
| Progress bar | `ProgressBarWidgetClass` |
| Dropdown / select | `XComboBoxWidgetClass` |
| Scrollable container | `ScrollWidgetClass` |
| Repeating list of rows | `TextListboxWidgetClass` (columns) or `GridSpacerWidgetClass` (free-form children) |
| Repeating grid of cells | `GridSpacerWidgetClass` |
| Frame with auto layout, flowing children | `WrapSpacerWidgetClass` |
| 3D item display | `ItemPreviewWidgetClass` |
| 3D character display | `PlayerPreviewWidgetClass` |
| Map surface | `MapWidgetClass` |
| Video playback | `VideoWidgetClass` |

---

## 4. Naming prefix taxonomy

Used when the Figma layer kind is generic (a rectangle, a frame) and the type must be inferred from the name.

| Prefix | Widget |
| --- | --- |
| `btn_` | `ButtonWidgetClass` |
| `txt_` | `TextWidgetClass` |
| `img_` | `ImageWidgetClass` |
| `edit_` | `EditBoxWidgetClass` |
| `check_` | `CheckBoxWidgetClass` |
| `slider_` | `SliderWidgetClass` |
| `drop_` | `XComboBoxWidgetClass` |
| `bar_` | `ProgressBarWidgetClass` |
| `list_` | `TextListboxWidgetClass` or `ScrollWidgetClass` (pick by content) |
| `grid_` | `GridSpacerWidgetClass` |
| `modal_` | `FrameWidgetClass` wrapping a `PanelWidgetClass` body |
| `preview_` | `ItemPreviewWidgetClass` (item content) or `PlayerPreviewWidgetClass` (player content) |
| `panel_` | `PanelWidgetClass` |

---

## 5. Layout translation: anchors first, spacers only when needed

This is the section most likely to be mishandled. Read it once carefully.

**The vanilla DayZ idiom is absolute pixel positioning with alignment anchors.** Every shipping vanilla `.layout` under `P:\gui\` and every example layout in this repo uses absolute `position`/`size` plus `halign`/`valign` anchors. Spacer widgets exist but are reserved for cases the anchor system genuinely cannot express.

### Default: absolute + anchor

For a Figma frame with auto layout, the default translation is:

- Each child becomes a widget with its own `position`/`size` derived from the Figma layer's pixel bounds.
- Use `halign` and `valign` to anchor the child against the parent's reference frame instead of computing absolute coords against the screen.
- Set `hexactpos`/`vexactpos`/`hexactsize`/`vexactsize` based on whether each axis should be pixel-fixed (`1`) or relative to the parent (`0`).

This produces output that matches vanilla style and reads cleanly in Workbench.

### When to reach for spacer widgets

Use `WrapSpacerWidgetClass` or `GridSpacerWidgetClass` only when:

- The Figma frame contains a **truly dynamic** repeating list or grid (N children where N is determined at runtime by data, not designed in Figma)
- OR the design relies on children flowing and wrapping based on container width (rare in DayZ UIs)

A static row of three buttons described in Figma auto-layout is NOT a spacer case. It is three `ButtonWidgetClass` widgets with `position`/`size` derived from their Figma bounds.

### When to reach for `ScrollWidgetClass`

When a Figma frame is marked as overflow-scrollable, or when its content height exceeds the visible region by design.

### Property nuances for spacer widgets

Spacer widget configuration is not fully documented in `gui_layout.md`. Before emitting a spacer with specific orientation, cell size, or column count, the implementer must verify against vanilla via the dayz-rag MCP (`search_dayz_source` with `file_type="layout"`) and grep `P:\gui\` for live examples. Do not invent property names. If a spacer's exact configuration is unclear, prefer the absolute-positioning fallback for the static case and flag the dynamic case in the handoff for `dayz-ui-specialist` to wire correctly in Workbench.

---

## 6. Coordinate translation

Figma uses absolute pixel coordinates. DayZ uses position/size pairs paired with `hexactpos`/`vexactpos` toggles. Translation by case:

| Case | Translation |
| --- | --- |
| Full-area container (root frame, full-screen overlay) | `position 0 0`, `size 1 1`, all four toggles `0` (relative) |
| Centered modal (fixed size, centered in parent) | `position 0 0`, `size W H` in pixels, `halign center_ref`, `valign center_ref`, all four toggles `1` |
| Fixed-size button or icon | `position X Y` in pixels, `size W H` in pixels, all four toggles `1` |
| Stretched-width element pinned to top of parent | `position 0 Y`, `size 1 H`, `hexactpos 0`, `hexactsize 0`, `vexactpos 1`, `vexactsize 1` |
| Element anchored to right edge with fixed offset | `position X Y`, `halign right_ref`, plus pixel toggles |

Always emit a position together with its matching `hexactpos`/`vexactpos` toggle. Same for size and `hexactsize`/`vexactsize`. A position without a toggle is ambiguous and Workbench may not load it as intended.

---

## 7. Color translation

DayZ colors are `R G B A` space-separated floats in 0..1, lowercase keyword `color`:

```
color 1 1 1 1               // white, opaque
color 0.0863 0.0863 0.0863 0.902   // vanilla dark panel
color 1 0.2 0.2 1           // red
color 0 0 0 0.5             // black, 50% alpha
```

Translation table:

| Figma form | DayZ form |
| --- | --- |
| `#FFFFFF` | `1 1 1 1` |
| `#000000` | `0 0 0 1` |
| `#FF5050` | `1 0.314 0.314 1` |
| `rgba(0, 0, 0, 0.5)` | `0 0 0 0.5` |
| `rgb(220, 220, 220)` | `0.863 0.863 0.863 1` |

Never emit hex strings, CSS `rgba()`, named colors, or 0..255 integers. The alpha is the fourth float on the `color` line, never a separate `opacity` property.

---

## 8. Font translation

DayZ ships SDF fonts under `gui/fonts/`. Default mapping for common Figma font choices:

| Figma intent | DayZ font path |
| --- | --- |
| Standard body text | `gui/fonts/sdf_MetronBook24` |
| Lighter / secondary body | `gui/fonts/sdf_MetronLight24` |
| Large heading | `gui/fonts/sdf_MetronBook72` |
| Serif accent (rare) | `gui/fonts/AmorSerifPro-Bold16` |

Pixel size is controlled separately from the font's numeric suffix. To render at a specific pixel size:

```
font "gui/fonts/sdf_MetronBook24"
"exact text" 1
"exact text size" 18
"bold text" 1
```

The font's name suffix (e.g. `24`) is the SDF generation size, not the render size. Always pair `"exact text" 1` with `"exact text size" <px>` when you want a deterministic on-screen size.

---

## 9. Hard NO list

Surface red flags that the output is wrong. The generator must never emit these. The validator must strip them on contact.

- **XML syntax**: `<Tag>`, `</Tag>`, `/>`, `name="value"` attribute pairs, namespace prefixes.
- **`=` between key and value.** DayZ is `key value`, not `key = value`.
- **Quoted attribute values.** Bare values only. The exception is text strings (`text "Hello"`) and multi-word KEYS (`"exact text" 1`).
- **Semicolons** as line terminators.
- **CSS-flavored property names**: `borderRadius`, `border-radius`, `display`, `flex`, `flexDirection`, `justifyContent`, `alignItems`, `boxShadow`, `box-shadow`, `padding`, `margin`, `gap`.
- **Opacity as a separate property or percentage.** Alpha lives as the fourth float on `color`.
- **camelCase or kebab-case attribute names.** DayZ properties are lowercase single words or quoted multi-word keys.
- **Self-closing tags.** Empty widgets still need `{ }` braces.
- **Inventing widget classes that do not end in `Class`.** Verify every unknown widget against vanilla before emitting it.

---

## 10. Worked example

A small status HUD: dark panel, title text, body text, close button. Bottom-right of the screen, 320 by 120 pixels.

### Input (Figma node, summarized)

```
Frame "StatusCard"  auto-layout vertical
  fill: #161616 80% opacity
  size: 320 x 120 px
  position: bottom-right, 24px from each edge
  children:
    Text "txt_title"  "Status: OK"  Metron Book 18px bold
    Text "txt_body"   "Subtitle"    Metron Light 12px
    Rectangle "btn_close"  "Close" label, Metron Book 14px
```

### Normalizer output (JSON, semantic)

```json
{
  "name": "status_card",
  "type": "panel",
  "layout": "vertical",
  "padding": { "top": 8, "right": 8, "bottom": 8, "left": 8 },
  "size": { "width": 320, "height": 120 },
  "style": { "color": "#161616", "alpha": 0.8 },
  "anchor": { "halign": "right", "valign": "bottom", "offsetX": 24, "offsetY": 24 },
  "children": [
    { "name": "txt_title", "type": "text", "text": "Status: OK",
      "font": "metron_book_18_bold" },
    { "name": "txt_body",  "type": "text", "text": "Subtitle",
      "font": "metron_light_12" },
    { "name": "btn_close", "type": "button", "text": "Close",
      "font": "metron_book_14" }
  ]
}
```

### Generator output (`.layout`, property-file)

```
FrameWidgetClass StatusHud {
 position 0 0
 size 1 1
 hexactpos 0
 vexactpos 0
 hexactsize 0
 vexactsize 0
 {
  PanelWidgetClass StatusCard {
   color 0.0863 0.0863 0.0863 0.8
   position 24 24
   size 320 120
   halign right_ref
   valign bottom_ref
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   style rover_sim_colorable
   {
    TextWidgetClass txt_title {
     ignorepointer 1
     position 8 8
     size 304 24
     hexactpos 1
     vexactpos 1
     hexactsize 1
     vexactsize 1
     text "Status: OK"
     font "gui/fonts/sdf_MetronBook24"
     "exact text" 1
     "exact text size" 18
     "bold text" 1
     "text halign" left
     "text valign" center
    }
    TextWidgetClass txt_body {
     ignorepointer 1
     position 8 36
     size 304 18
     hexactpos 1
     vexactpos 1
     hexactsize 1
     vexactsize 1
     text "Subtitle"
     font "gui/fonts/sdf_MetronLight24"
     "exact text" 1
     "exact text size" 12
     "text halign" left
     "text valign" center
    }
    ButtonWidgetClass btn_close {
     position 8 8
     size 80 28
     halign right_ref
     valign bottom_ref
     hexactpos 1
     vexactpos 1
     hexactsize 1
     vexactsize 1
     style Default
     text "Close"
     font "gui/fonts/sdf_MetronBook24"
     "exact text" 1
     "exact text size" 14
    }
   }
  }
 }
}
```

Each stage's shape mirrors the next: the Figma frame becomes the normalized JSON node, which becomes the `.layout` widget block. Names survive end to end so `FindAnyWidget("btn_close")` works from script.

---

## Agent usage

- **`figma-node-normalizer`** uses sections 4 (prefixes) and 6 to decide what to keep, what to flatten, what to label. Its output JSON should carry enough metadata that the generator never has to re-guess.
- **`figma-to-dayz-layout`** uses every section. The widget mapping table is its primary lookup. Section 5 is the most common place to go wrong, treat it as required reading.
- **`dayz-layout-validator`** uses section 9 (Hard NO list) as its strip list, sections 1 and 2 to verify well-formedness, and sections 3 and 4 to confirm widget classes against the catalog.

When the format claims in any individual agent's `.md` file disagree with this doc, this doc wins. The agents are documentation; this is the spec.
