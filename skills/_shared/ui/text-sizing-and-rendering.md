# Text sizing and rendering laws: wrap, fonts, alpha, blending, render to texture

What the engine actually draws, as measured on a running client: `wrap` does nothing on a `TextWidget`, how each kind of font takes its size, why a mockup's pixel font size misleads, which widgets honor a layout alpha, the blend settings a transparent image needs, and why drawing UI onto a model surface from script does not work.

**How facts are marked here.** A `P:\` path with a line was checked on `P:\` (DayZ 1.30). Everything described as measured was measured in game, on DayZ 1.29.163709 unless a line says otherwise, by reading pixels on full resolution captures; none of it is yet repeated on 1.30. "Rule 3" is rule 3 in `checklist-and-troubleshooting.md` (exact units are 1/1080 of the screen height).

---

## Contents

- [wrap does nothing on a TextWidget](#wrap-does-nothing-on-a-textwidget)
- [Text sizing laws](#text-sizing-laws)
- [Layout alpha: which widgets honor it](#layout-alpha-which-widgets-honor-it)
- [Mockup fidelity](#mockup-fidelity-calibrate-to-the-game-and-do-not-edit-a-layout-from-a-mockup)
- [Transparent ImageWidgets need blend state](#transparent-imagewidgets-need-blend-state)
- [Render to texture from script is dead in DayZ 1.29](#render-to-texture-from-script-is-dead-in-dayz-129)

## wrap does nothing on a TextWidget

Two different claims are easy to mix up here, and only one of them comes from counting files.

- The census in `layout-format.md` shows that the `wrap` attribute **is written** on `TextWidgetClass` (4 times) and on `RichTextWidgetClass` (236 times) in an 819 layout corpus. A count cannot show whether the engine **honors** it: four occurrences are just as consistent with four layouts setting an attribute that does nothing.
- An in game probe settled it: **it does not.**

The probe: DayZDiag 1.29.163709, a live client, one `.layout` with three widgets side by side. All three had the same box (260x150, `hexactsize` and `vexactsize`), the same `text_proportion 0.14` and the same string of twelve Spanish number words, `UNO DOS TRES CUATRO CINCO SEIS SIETE OCHO NUEVE DIEZ ONCE DOCE` (kept as tested, since the clip point below is quoted from it).

| Widget class | Declares | Draws |
|---|---|---|
| `TextWidgetClass` | `wrap 1` | One line, clipped in the middle of a word at `SEIS S` |
| `TextWidgetClass` | `wrap 0` | One line, clipped at the same word |
| `MultilineTextWidgetClass` | `wrap 1` | Five lines, all twelve words visible |

- `wrap 1` and `wrap 0` on a `TextWidget` cannot be told apart in the frame.
- The `MultilineTextWidget` is the positive control, and it is what makes the negative result count: five wrapped lines fit in the same 150 px box, so the `TextWidget` had the room and did not use it.
- It was run twice by two independent routes, with text set at runtime (`SetText`) and with text written in the `.layout`, and gave the same result. So the missing wrap is not a side effect of the runtime setter.
- The instrument was the drawn frame, not `GetTextSize()`: with an exact size the box cannot grow, so wrap can only show as line breaks inside it.

So the four corpus occurrences are what the census could not rule out: layouts that set an attribute that does nothing. `MultilineTextWidget` is not just the reliable choice for wrapping text. It is the only one.

That fits the script side, where there is no switch either. The `WidgetFlags` enum has no text wrap flag (`P:\scripts\1_core\proto\enwidgets.c:57-85`, 26 entries). `NOWRAP` at `P:\scripts\1_core\proto\enwidgets.c:63` is a texture flag ("Do not do texture wrapping"), and the file's only other `wrap` name, `class WrapSpacerWidget` at `P:\scripts\1_core\proto\enwidgets.c:477`, is a flow layout container, not a flag. `CreateWidget(TextWidgetTypeID, ...)` plus `SetFlags(...)` cannot express wrap, and the probe shows the layout attribute cannot either.

## Text sizing laws

Measured. One probe layout, loaded from `$profile:` and reloaded while the client ran (cases A to G), the same strings, measured per pixel at two viewports on the same running client (846x461, then 1600x900). The face laws add the panels of a shipped group mod, loaded the same way and captured at 1920x1080, 1280x720 and 2560x1080. Rules to design by:

- **An unnumbered bitmap face (`gui/fonts/Metron`, `MetronBook`) or an SDF face, with no size key (no `"exact text size"`, no `text_proportion`), takes its glyph height from the widget box.** A numbered bitmap face (`Metron14` and the like) does not; see the next bullet.
  - `sdf_MetronBook24` at 720p: glyph height = 0.74 x box height (`hot-iteration.md`).
  - Bitmap `gui/fonts/Metron` and `MetronBook` in the group mod's shipped panel, on text without descenders: 10 px of ink in an 18 unit box and 14 px in a 24 unit box at 1920x1080; 7 and 8 px at 1280x720. That is 0.5 to 0.6 of the box at both sizes, with nothing clipped. A plan built on a glyph of about 22 px that ignores its box predicted clipping that did not happen.
  - One reading goes the other way: in the probe, case G (a 20 unit box) drew the same glyph as case F (a 40 unit box), clipped. At which of the two resolutions was not recorded; at 846x461 that box is 8.5 px tall.
  - The font definition lists one atlas per size: 12, 14, 16, 22, 28, 48 and 58 (`P:\gui\fonts\metron.xml`). The readings are consistent with the engine picking an atlas by box height, with nothing smaller than 12 for a box too short for it. Not verified.
  - A corollary that closed a real bug: rects with exact flags scale by height/1080 (rule 3) and the glyphs scale with them. A script that then shrank the rects with `SetSize` (x0.444 at 720p) did not shrink the glyphs, and the text was cut off. Leave the scaler out and both scale together for free.
  - Corrected. This bullet used to say the font only default "scales with the viewport and ignores the widget box", so a half height box would show the same glyphs, clipped.
- **A numbered bitmap face (`gui/fonts/Metron14`, `MetronBook12`, `Metron22` and so on) keeps its pixel size at every resolution, whatever its box.**
  - The same panel, same pair of captures: the ink of its `Metron22`, `Metron14`, `MetronBook12` and `Metron22` texts was 13, 10, 8 and 14 px at 1920x1080 and 13, 9, 8 and 14 px at 1280x720. So 0.46 to 0.50 of the box became 0.68 to 0.75 as the boxes shrank to two thirds.
  - `MetronBook12` labels that filled about 84% of their box at 1080p touched both edges at 720p, and a `MetronBook12` sentence became unreadable.
  - Size such text for the smallest height you support. At 720p the box is two thirds of its 1080p size and the glyph is not, so text that must fit there fills at most two thirds of its box at 1080p, padding included. A rule of thumb of about 75% held in that panel; by the arithmetic it overflows at 720p unless the glyph shrinks (one `Metron14` text did, by one pixel).
  - Do not set sentences in `MetronBook12`.
- **`"exact text size" N` follows a different law for each widget class and face.**
  - On `TextWidgetClass` with an SDF face, the text is drawn at about N px per 1080 of screen height and scales with the boxes. This is vanilla's inventory header recipe: `font "gui/fonts/sdf_MetronLight24"`, `"exact text" 1` and `"exact text size" 20` (`P:\gui\layouts\inventory_new\closable_header.layout:139-158`). The group panel's title in `sdf_MetronBook24` at N=24 drew 17 px of ink (no descender) at 1920x1080 and at 2560x1080, and 12 px at 1280x720. At N=20 the advance is about 10.5 px per Latin character at 1080p. This is the face to pick for text that must keep its proportions.
  - On `TextWidgetClass` with the bitmap `gui/fonts/Metron`, the drawn size scaled with the viewport too, but smaller: N=20 was unreadable (about 3 px) at a 461 px high window and about a 9 px cap height at 900.
  - Inside the dialog recipe on `RichTextWidgetClass` (`"exact text" 1`, `"exact text size" 20`, `"size to text h"` and `"size to text v"` 1, `wrap 1`, `clipchildren 1`) the glyphs stay **physically constant** across resolutions (cap height about 10 px at both). Use that recipe when you want constant physical legibility, and accept that it will not follow the panel size.
- **`text_proportion` follows no clean, steadily rising law across boxes or resolutions.** The same 0.5 on a 40 high box drew a 9 px cap at 461 and 8 px at 900 (it did not scale); on an 80 high box it went from 13 to 21 (it did). Treat it as a knob you calibrate per widget by looking, never as a predictable scaling mechanism.
- **`MultilineTextWidgetClass` does not wrap unless `wrap 1` is declared.** The probe above showed `MultilineTextWidget` with `wrap 1` wraps; this probe showed the attribute's default is no wrap (one long clipped line). Always declare `wrap 1` on multiline text.
- **`"size to text v" 1` really grows the box at runtime** (declared 60, reported by the engine as 36 while its siblings scaled to 25.6), and the grown text paints over the next sibling. Give size to text widgets a clipping container or reserved room.
- **Glyphs bleed about 1 to 2 px to the left of the widget rect** (the first glyph's bearing and anti aliasing; seen on a live frame and confirmed per pixel: the background edge was exactly on the rect and the glyph 1 px outside it). Never start text flush against the edge of a colored box. Pad at least 4 to 8 px horizontally.

### Rules from the sorter panel preview

Measured on a `$profile:` preview of an 820x600 layout with 250 widgets (a sorter panel, at 1920x1080 and 1280x720):

1. **`visible 0` declared in a `.layout` works.** Overlapping section roots, overlays and badges start hidden with no script (the engine tree reports `visible:0` and `visible_hierarchy:0`). Pattern for sections you switch between: N identical overlapping roots, the active one `visible 1` and the rest `visible 0`; script only toggles the roots, which removes the gap that stacked sections leave.
2. **Glyphs do not shrink in step with the scale factor.** A box that fits at 1080p can clip at a factor of 0.667 (the word "POWERED" lost its D in a 62 px box and needed 70). Size a text box for the worst factor you support and check there; allow 10 to 15% over the width measured at 1080p.
3. **A type hierarchy in font only mode means numbered faces.** `gui/fonts/Metron12`, `Metron14`, `Metron16`, `MetronBook12` and `MetronBook14` exist and vanilla uses them (`font "gui/fonts/Metron14"` at `P:\gui\layouts\day_z_hud.layout:1965`). Unnumbered faces (`Metron`, `MetronBook`) take their size from the box, so with them the hierarchy is the box heights. Numbered bitmap faces keep their pixel size at every resolution; text that must scale with the panel wants an SDF face with `"exact text size"`. `text_proportion` stays ruled out (it is not consistent across resolutions). Corrected: this rule used to say unnumbered faces "yield about 22 px and offer no fine hierarchy".
4. **Pre-mixed color tokens were validated end to end on a real panel.** The engine tree returns the declared float exactly, and the frame shows the pure color (the declared alpha is ignored, see the next section). Recipe: `c = base x (1 - a) + wash x a`, and always alpha 1 in the layout.
5. Layout generation can be delegated. A complete table spec (name, class, rect, flags, color and font for every widget) plus a mechanical check (each name exactly once, no legacy names, bindings present, allowed fonts only, alpha 1, one attribute per line) let a small model produce 3,400 correct lines at the first attempt. The two real defects were caught by looking at the frame (a clipped glyph), not by the text check.

The remaining rules from that session are about verification and are in `verification.md`.

## Layout alpha: which widgets honor it

- **The alpha in a layout `color R G B A` on an `ImageWidget` with no texture is ignored when the frame is composed.** Three panels declared with alpha 0.25 drew their source color at full strength, measured per pixel. The value does reach the engine (the widget tree reports it). On that widget, translucent washes declared in the layout do not exist: mix the wash into an opaque color beforehand, or call `SetColor` at runtime. An `ImageWidget` with no texture does paint a flat opaque fill (confirmed twice).
- **A `PanelWidgetClass` with `style rover_sim_colorable` does honor the alpha.** That style has `WhitePixel` in all nine slices (`P:\gui\looknfeel\dayzwidgets.styles:3284-3307`). `color 0 0 0 0` drew nothing and `1 0 0 1` a red fill (measured; partial alphas were not measured).
- **A `ButtonWidgetClass` with a `color` and no `style` drew no fill at all**, while a `style Colorable` button in the same frame did. `style Default` draws nothing in its `Normal` state either: every slice is empty (`P:\gui\looknfeel\dayzwidgets.styles:1597-1608`).
- Vanilla's pause menu buttons are built around that: an invisible `ButtonWidgetClass continuebtn` over a child `continuebtn_panel` that script tints, plus a `continuebtn_label` (`P:\gui\layouts\day_z_ingamemenu.layout:122-158`). The script side is `ColorHighlight` and `ColorNormal`, which find `_panel` and `_label` by the button's name (`P:\scripts\5_mission\gui\ingamemenu.c:365-415`).

## Mockup fidelity: calibrate to the game, and do not edit a layout from a mockup

When you build an HTML or preview mockup of a `.layout`, the mockup's CSS `font-size` in px does not represent what the game draws. An arbitrary mockup font wraps and overlaps differently from the game. How the game sizes text depends on the face (previous section): faces that follow their box, numbered bitmap faces that keep their pixel size, and SDF faces with `"exact text size"` N that scale with the screen height.

- **Calibrate** the mockup font per face and resolution, from a measured frame:
  - the face's own pixel size for a numbered bitmap face;
  - about N x height/1080 for an SDF face with `"exact text size"` N;
  - glyph = 0.74 x `text_proportion` x box height only where that was measured (`sdf_MetronBook24` on `TextWidgetClass`, `hot-iteration.md`), since `text_proportion` on the bitmap `Metron` did not scale cleanly.
  - Or label the mockup clearly as "an approximation, not what the game draws".
- **Do not change the real `.layout`** (turn a widget into a `MultilineTextWidget`, move positions, shrink text) to fix something seen only in an unfaithful mockup. Mark it "verify in game" first; the game may already draw it correctly. This rule comes from a real case: a 25 px mockup title wrapped and overlapped the subtitle, which triggered a change of the title to a `MultilineTextWidget` that the calibrated render (about 18 px, roughly `text_proportion` 0.34) did not need.

## Transparent ImageWidgets need blend state

An alpha channel in a PNG or PAA is not enough. Every `ImageWidgetClass` that must show transparency declares both lines in its `.layout`:

```text
mode blend
"src alpha" 1
```

Without them the usual symptom is an opaque black rectangle the size of the widget with the art still visible inside. An A/B test in game isolated this. It matches vanilla: `ImageWidgetClass ProjectedCrossHair` declares `mode blend` and `"src alpha" 1` at `P:\gui\layouts\day_z_hud.layout:2263-2264`. Check this while writing the layout and again at delivery.

For a strip or tape that its parent must clip, the attribute is `clipchildren 1` (for example at `P:\gui\layouts\day_z_hud.layout:555`), not `clipping`.

## Render to texture from script is dead in DayZ 1.29

`SetGUIWidget(IEntity ent, int index, RTTextureWidget w)` is declared at `P:\scripts\1_core\proto\enwidgets.c:634-637`, with a comment that the widget can be referenced in a shader as `$rendertarget`. Measured in the 1.29 runtime: it does not work. The render target is never filled from its child widgets. Do not spend time on it.

Two in game probes, both negative:

- `SetObjectTexture(idx, "$rendertarget")` on a hidden selection paints empty black. The token resolves, so this is not a typo; a texture that does not exist would paint white.
- An `ImageWidget.SetImageTexture(0, rtt)` that mirrors the same render target paints the white of a missing texture (`SetImageTexture` is at `P:\scripts\1_core\proto\enwidgets.c:258`). The producer is dead for both consumers.

Vanilla does not use it: `SetGUIWidget` and `RTTextureWidget` appear nowhere in `P:\scripts` outside that declaration file, and no layout under `P:\gui\layouts` has an `RTTextureWidgetClass`. No mod is known to use it either. The opposite direction works: the world drawn into the UI, through a `RenderTargetWidget` and `SetWidgetWorld` (`P:\scripts\2_gamelib\entities\rendertarget.c:66`). It is UI drawn onto a surface that is dead.

Live content on a model surface goes the physical way:

- `SetObjectTexture` and `SetObjectMaterial` per hidden selection. These do not replicate: keep an int the server owns, apply it on both sides, and assert it again from a watchdog.
- Bones driven by `model.cfg` rotation and translation animations (`SetAnimationPhase` replicates natively from the server).
- Hiding by overriding with a transparent texture (a `type="hide"` animation kills the whole baked `Animations` block).

A 2D panel anchored to the screen over the projected quad's bounding box never matches a surface seen at an angle, in orientation or in size. That is structural, not a matter of tuning. The full case was a GPS screen on a car dashboard in a vehicle mod.
