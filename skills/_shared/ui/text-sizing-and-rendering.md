# Text sizing and rendering

How the engine really draws text and images: `wrap` does nothing on a `TextWidget`, how each kind of font takes its size, which widgets honor a layout alpha, the blend settings a transparent image needs, why a mockup's font size misleads, and why drawing UI onto a model from script does not work.

Everything described as measured was read per pixel off captures of a running 1.29 client and is not repeated on 1.30. Exact units are 1/1080 of the screen height (`checklist-and-troubleshooting.md`, "Declare all four unit flags").

## wrap does nothing on a TextWidget

The counts show `wrap` written on `TextWidgetClass` 4 times (`layout-attributes.md`); a count cannot show whether the engine honors it. In game it does not. Three widgets with the same 260 by 150 exact box, the same `text_proportion 0.14` and the same twelve word string:

| Widget class | Declares | Draws |
|---|---|---|
| `TextWidgetClass` | `wrap 1` | One line, clipped in the middle of a word |
| `TextWidgetClass` | `wrap 0` | The same clipped line |
| `MultilineTextWidgetClass` | `wrap 1` | Five lines, every word visible |

The multiline widget shows the room was there. Text set from script and text written in the layout gave the same result. Script has no switch either: `WidgetFlags` has no text wrap flag (`P:\scripts\1_core\proto\enwidgets.c:57` to `:85`), and `NOWRAP` (`:63`) is a texture flag ("Do not do texture wrapping"). The file's only other `wrap` name, `class WrapSpacerWidget` (`:477`), is a flow layout container, so `CreateWidget(TextWidgetTypeID, ...)` with `SetFlags(...)` cannot ask for wrap either. Wrapped text means `MultilineTextWidgetClass`, and it does not wrap unless it declares `wrap 1`: with the attribute left out it drew one long clipped line.

## How each face takes its size

- An unnumbered bitmap face (`gui/fonts/Metron`, `MetronBook`) or an SDF face with no size key (no `"exact text size"`, no `text_proportion`) takes its glyph height from the widget box. `sdf_MetronBook24` drew glyphs 0.74 of the box height at 720p (`preview-text-and-stringtables.md`). Bitmap `Metron` and `MetronBook` on text without descenders drew 10 px of ink in an 18 unit box and 14 px in a 24 unit box at 1920x1080, and 7 and 8 px at 1280x720: 0.5 to 0.6 of the box at both, nothing clipped. One reading went the other way: a 20 unit box (8.5 px tall in an 846x461 window; whether this reading came from that window or a 1600x900 one was not recorded) drew the same clipped glyph as a 40 unit one.
- The face definition lists one atlas per size, 12, 14, 16, 22, 28, 48 and 58 (`P:\gui\fonts\metron.xml`). The readings fit an engine that picks an atlas by box height with nothing below 12; not verified.
- Exact rects scale by height/1080 and their glyphs scale with them. A script that then shrank the rects again with `SetSize` (0.444 at 720p) did not shrink the glyphs, and the text was cut off. Leave such scaling out and both scale together.
- A numbered bitmap face (`gui/fonts/Metron14`, `MetronBook12`, `Metron22` and the like) keeps its pixel size at every resolution, whatever its box. In one panel the ink of four such texts was 13, 10, 8 and 14 px at 1920x1080 and 13, 9, 8 and 14 px at 1280x720, so text that filled half its box at 1080p filled three quarters at 720p. `MetronBook12` labels that filled 84% of their box at 1080p touched both edges at 720p. Size such text for the smallest height you support: at 720p the box is two thirds of its 1080p size and the glyph is not. Do not set sentences in `MetronBook12`. Vanilla uses numbered faces (`font "gui/fonts/Metron14"`, `P:\gui\layouts\day_z_hud.layout:2077`).
- `"exact text size" N` on a `TextWidgetClass` with an SDF face draws about N px per 1080 of screen height and scales with the boxes. That is vanilla's inventory header: `font "gui/fonts/sdf_MetronLight24"`, `"exact text" 1`, `"exact text size" 20` (`P:\gui\layouts\inventory_new\closable_header.layout:139` to `:158`). `sdf_MetronBook24` at N=24 drew 17 px of ink at 1920x1080 and 2560x1080 and 12 px at 1280x720; at N=20 a Latin character advances about 10.5 px at 1080p. Pick this for text that must keep its proportions.
- `"exact text size" N` with the bitmap `gui/fonts/Metron` also scaled with the window, but smaller: N=20 was about 3 px tall at 461 px high and about 9 px at 900.
- Vanilla's dialog recipe on `RichTextWidgetClass` (`"exact text" 1`, `"exact text size" 20`, `"size to text h" 1`, `"size to text v" 1`, `wrap 1`, `clipchildren 1`) keeps its glyphs the same physical size at every resolution, a cap height of about 10 px. Use it for constant legibility; it will not follow the panel size.
- `text_proportion` follows no clean law across boxes or resolutions: 0.5 in a 40 high box drew a 9 px cap at 461 and 8 px at 900, and in an 80 high box went from 13 to 21. Calibrate it per widget by eye.
- A type hierarchy with fonts alone means numbered faces (`Metron12`, `Metron14`, `Metron16`, `MetronBook12`, `MetronBook14`). With unnumbered faces the hierarchy is the box heights.
- Glyphs do not shrink in step with the scale: a word that fit a 62 px box at 1080p lost its last letter at 0.667 and needed 70. Allow 10 to 15% over the width measured at 1080p, and check at the smallest size you support.
- Glyphs bleed 1 to 2 px left of the widget rect. Pad text 4 to 8 px from the edge of a colored box.

## Which widgets honor a layout alpha

- The alpha in `color R G B A` on an `ImageWidget` with no texture is ignored when drawn: three panels at alpha 0.25 drew full strength, though the widget tree reports the value. Such a widget does draw a flat opaque fill. Mix the wash into an opaque color first (`c = base x (1 - a) + wash x a`, alpha 1 in the layout), or set the color from script.
- A `PanelWidgetClass` with `style rover_sim_colorable`, which has `WhitePixel` in all nine slices (`P:\gui\looknfeel\dayzwidgets.styles:3284` to `:3307`), honors it: `color 0 0 0 0` drew nothing and `1 0 0 1` a red fill. Partial alphas were not measured.
- A `ButtonWidgetClass` with a `color` and no `style` drew no fill, while a `style Colorable` button in the same frame did. `style Default` draws nothing at rest either: every `Normal` slice is empty (`P:\gui\looknfeel\dayzwidgets.styles:1597` to `:1608`).
- Vanilla's pause menu works around that: an invisible `ButtonWidgetClass continuebtn` over a `continuebtn_panel` child that script tints and a `continuebtn_label` (`P:\gui\layouts\day_z_ingamemenu.layout:122` to `:158`), with `ColorHighlight` and `ColorNormal` finding `_panel` and `_label` from the button's name (`P:\scripts\5_mission\gui\ingamemenu.c:365` to `:415`).

## Transparent images need blend state

An alpha channel in the PNG or PAA is not enough. Every `ImageWidgetClass` that shows transparency declares:

```text
mode blend
"src alpha" 1
```

Without them the image draws as an opaque black rectangle with the art inside it (an A/B test in game). Vanilla's `ProjectedCrossHair` declares both (`P:\gui\layouts\day_z_hud.layout:2263` and `:2264`). A strip its parent must clip needs `clipchildren 1` on the parent (`P:\gui\layouts\day_z_hud.layout:555`); there is no `clipping` attribute.

## Mockups: calibrate them, and never edit a layout from one

A CSS `font-size` in pixels does not represent what the game draws, so an arbitrary mockup font wraps and overlaps differently.

- Calibrate the mockup font per face and resolution from a measured frame: the face's own pixel size for a numbered bitmap face, about N x height/1080 for an SDF face with `"exact text size"` N, and 0.74 x `text_proportion` x box height only where that was measured (`sdf_MetronBook24` on `TextWidgetClass`). Or label it "an approximation, not what the game draws".
- Never change the real `.layout` (switch a widget to multiline, move it, shrink text) to fix something seen only in an uncalibrated mockup. Mark it "check in game" first. A 25 px mockup title that wrapped over its subtitle led to a needless switch to `MultilineTextWidget`; the calibrated render, about 18 px, fit on one line.

## UI on a model surface from script does not work

`SetGUIWidget(IEntity ent, int index, RTTextureWidget w)` is declared with a comment that the widget can be used in a shader as `$rendertarget` (`P:\scripts\1_core\proto\enwidgets.c:634` to `:637`). In the 1.29 runtime the render target is never filled from its child widgets:

- `SetObjectTexture(idx, "$rendertarget")` on a hidden selection paints empty black. The token resolves; a texture that does not exist paints white.
- `ImageWidget.SetImageTexture(0, rtt)` (`:258`) on the same target paints the white of a missing texture.

Vanilla never uses it: `SetGUIWidget` and `RTTextureWidget` appear nowhere in `P:\scripts` outside that declaration, and no layout under `P:\gui\layouts` has an `RTTextureWidgetClass`. The other direction works: the world drawn into the UI through a `RenderTargetWidget` and `SetWidgetWorld` (`P:\scripts\2_gamelib\entities\rendertarget.c:66`).

Live content on a model goes the physical way:

- `SetObjectTexture` and `SetObjectMaterial` per hidden selection. They do not replicate: keep an int the server owns, apply it on both sides, and assert it again from a watchdog.
- Bones driven by `model.cfg` animations; `SetAnimationPhase` replicates from the server.
- Hiding by a transparent texture, since a `type="hide"` animation kills the whole baked `Animations` block.

A 2D panel pinned to the screen over the projected surface never matches a surface seen at an angle, in orientation or in size. That is structural, not a matter of tuning; it ruled out a GPS screen drawn on a car dashboard.
