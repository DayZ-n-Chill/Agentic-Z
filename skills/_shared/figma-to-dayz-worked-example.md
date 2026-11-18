# Figma to DayZ worked example

One small HUD card carried through all three stages of the Figma pipeline: the Figma node, the normalizer's JSON and the generator's `.layout`. The rules it follows are in `figma-to-dayz-rules.md`; section numbers below are that file's sections.

The anchors and style match vanilla: `halign right_ref` and `valign bottom_ref` at `P:\gui\layouts\day_z_hud.layout:558` and `:559`, `style rover_sim_colorable` at `P:\gui\layouts\camera_tools\camera_tools.layout:391`, and `style Default` at `P:\gui\layouts\camera_tools\camera_tools.layout:960`.

A small status HUD: dark panel, title text, body text, close button. Bottom-right of the screen, 320 by 120 pixels.

## Input (Figma node, summarized)

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

## Normalizer output (JSON, semantic)

```json
{
  "name": "StatusCard",
  "type": "panel",
  "layout": "vertical",
  "spacing": 4,
  "padding": { "top": 8, "right": 8, "bottom": 8, "left": 8 },
  "size": { "width": 320, "height": 120 },
  "sizing": { "width": "fixed", "height": "fixed" },
  "style": { "color": "#161616", "alpha": 0.8 },
  "anchor": { "halign": "right", "valign": "bottom", "offsetX": 24, "offsetY": 24 },
  "children": [
    { "name": "txt_title", "type": "text", "layout": "none", "spacing": 0,
      "padding": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
      "size": { "width": 304, "height": 24 },
      "sizing": { "width": "fixed", "height": "hug" },
      "text": "Status: OK", "font": "metron_book_18_bold", "children": [] },
    { "name": "txt_body", "type": "text", "layout": "none", "spacing": 0,
      "padding": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
      "size": { "width": 304, "height": 18 },
      "sizing": { "width": "fixed", "height": "hug" },
      "text": "Subtitle", "font": "metron_light_12", "children": [] },
    { "name": "btn_close", "type": "button", "layout": "none", "spacing": 0,
      "padding": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
      "size": { "width": 80, "height": 28 },
      "sizing": { "width": "hug", "height": "hug" },
      "text": "Close", "font": "metron_book_14", "children": [] }
  ]
}
```

Every node, leaves included, carries the eight core fields: `name`, `type`, `layout`, `spacing`, `padding`, `size`, `sizing` and `children`. The generator reads `sizing` on each axis to pick the size toggle (section 5), so a node without it cannot be made responsive. A child of a `layout: none` parent, or a child Figma marks as absolutely positioned inside an auto-layout frame, also carries `position`, `{ "x", "y" }` in pixels from the parent's top-left corner, since no auto-layout places it. So does every child of an auto-layout parent whose primary or counter-axis alignment is anything but start (center, end, space-between, baseline), since the flow would put it in the wrong place; the other children of `horizontal` and `vertical` parents omit it. When `position` is present, the generator uses it instead of computing a flow position. The other fields (`text`, `font`, `style`, `anchor`) appear only when the source node carries that data.

For example, an icon at x=200, y=10 inside a free-placed 240 by 40 header frame:

```json
{ "name": "panel_header", "type": "panel", "layout": "none", "spacing": 0,
  "padding": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
  "size": { "width": 240, "height": 40 },
  "sizing": { "width": "fixed", "height": "fixed" },
  "children": [
    { "name": "img_icon", "type": "image", "layout": "none", "spacing": 0,
      "padding": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
      "size": { "width": 20, "height": 20 },
      "sizing": { "width": "fixed", "height": "fixed" },
      "position": { "x": 200, "y": 10 }, "children": [] }
  ]
}
```

The generator writes that child as `position 200 10` with `hexactpos 1` and `vexactpos 1` (section 6, "Fixed-size button or icon").

## Generator output (`.layout`, property-file)

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
     position 8 58
     size 80 28
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

The three children carry no `position` because their vertical auto-layout parent places them: each one's `y` is the parent's top padding plus the heights of the siblings before it plus one `spacing` per sibling before it, so `txt_body` is at 8 + 24 + 4 = 36 and `btn_close` at 8 + 24 + 4 + 18 + 4 = 58, and each `x` is the left padding, 8. Both axes of all three children are pixel-sized; a `fill` axis would instead take position `0` with its position toggle `0` (section 6).

Each stage's shape mirrors the next: the Figma frame becomes the normalized JSON node, which becomes the `.layout` widget block. Names survive end to end so `FindAnyWidget("btn_close")` works from script.
