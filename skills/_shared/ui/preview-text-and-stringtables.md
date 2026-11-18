# Text in a layout preview

What a layout loaded from `$profile:` shows about text: when a `#STR_` key resolves, why reading the text back can't tell you, how glyph height follows the widget box and `text_proportion`, and when a PBO's own stringtable is not read. The reload loop itself is in `hot-iteration.md`; the full text sizing rules are in `text-sizing-and-rendering.md`.

All of it is measured in game on DayZ 1.29 at 1280x720 and 1920x1080, each claim checked on a captured frame. The engine calls are cited on `P:\`.

## `#STR_` keys resolve in a preview

One frame, four widgets:

| Widget | Text in the layout | On screen |
|---|---|---|
| Title | A key defined by another loaded mod's stringtable | The mod's text |
| Message | A literal, no key | The text, wrapped over two lines |
| BtnNo | The vanilla key `#STR_CfgWheel0` ("Wheel") | Its translation in the client's language |
| BtnYes | A key no stringtable defines | `STR_UI_YES`, as written |

So when a key prints raw, the preview is not the cause; the key is not defined. A template that ships `#STR_` keys without a stringtable looks broken on first run, which is why `templates/stringtable.csv` ships beside the template layouts.

An unresolved key logs nothing; no RPT line matched `STR_UI_`. It also can't wrap: `STR_UI_MODAL_MESSAGE` is one token with no spaces, `wrap` breaks on spaces, and the result looked like a title clipped at both ends. The same widget with real words wrapped correctly.

## Reading the text back proves nothing

In the same frame the bridge's `ui_tree` reported `BtnNo.text == "#STR_CfgWheel0"` while the screen showed the translation. The engine substitutes at draw time and returns what was assigned, so a check that reads widget text and fails it for starting with `#` reports a fault that isn't there. Only two of seven widgets were readable at all; no `MultilineTextWidgetClass` was. Judge keys from the frame.

## Glyph height follows the box

`templates/form_row.layout` loaded on its own has a root of `size 1 1`, so its `RowLabel` box is the whole screen (435x720 px at 720p) and draws one screen filling letter. Change only the root to `size 0.30 0.05` and `RowLabel` becomes 130x36 px and draws readable text. An oversized body comes from the box, not the font. This holds for an unnumbered bitmap face (`Metron`, `MetronBook` included) and for an SDF face with no size key; a numbered bitmap face such as `Metron22` keeps its own pixel size (`text-sizing-and-rendering.md`).

## `text_proportion` works on TextWidget only

On `TextWidgetClass` the attribute is honoured and linear. Box height 108 px:

| In the widget block | Glyph height |
|---|---|
| Nothing | 80 px |
| `text_proportion 0.20` | 16 px |
| `"exact text" 0` and `text_proportion 0.20` | 16 px |
| `"exact text" 0` and `text_proportion 0.60` | 47 px |
| `"exact text" 1` and `text_proportion 0.20` | 12 px |

The first four fit glyph = 0.74 x `text_proportion` x box height, with the attribute defaulting to 1.0. The 0.74 is the cap height of `sdf_MetronBook24` inside its em box, so another font has another constant; the straight line is what carries over. Glyph heights were read after removing the window frame from the capture and checking that the gaps between boxes held no glyph rows.

- `"exact text" 0` is not needed. In a corpus of 821 layouts it sits beside `text_proportion` in 82.6 percent of blocks against a 3.1 percent base rate, but the frame shows the same 16 px with and without it. How people write is not what the engine reads.
- `"exact text" 1` gives 12 px, the font's own size, which matches `SetTextExactSize`, whose header says "Exact Text flag must be enabled" (`P:\scripts\1_core\proto\enwidgets.c:192`).
- Where the attribute sits in the block does not matter; first after `name` and last both gave 16 px.

On `MultilineTextWidgetClass` the attribute is ignored: the same box, font and `text_proportion 0.20` draw 80 px, the same as declaring nothing, and six different values on one multiline widget all drew the same. `MultilineTextWidget extends TextWidget` (`enwidgets.c:219`) and inherits `SetTextProportion` (`:216`), yet the layout attribute does nothing; an inherited method is not a working behaviour. `wrap 1` on a multiline does change the size (80 px to 54 px, and 63 px once the text really splits), but never toward the requested proportion.

## A PBO whose stringtable is not read

A test addon's `.layout` that exists only inside its PBO, loaded by the addon prefix, draws, so the PBO mounts and serves files. In the same panel a key from that PBO's own `stringtable.csv` printed as its name with the leading `#` stripped: the engine treated it as a key, looked it up and found nothing. A vanilla key in the same frame resolved.

Three `CfgMods` differences from a working mod were tested, one addon each, all in one frame, with every PBO unpacked again after deployment to confirm its `stringtable.csv` was inside:

| Added to `CfgMods` | The addon's key on screen |
|---|---|
| Nothing | Raw |
| `prefix = "..."` | Raw |
| `dependencies[] = {"Game","World","Mission"}` | Raw |
| Prefix, dependencies, picture, action, author, authorID, version and a non empty `units[]` | Raw |

None of them is the missing piece. The remaining difference from the working mod is a `class defs` block that declares script modules; that is the next thing to test, not a conclusion. In practice it matters little, since every real mod has scripts and real mods' keys resolve. It does mean a stringtable only addon is not a valid minimal test, and the failure is silent end to end.

## Packing the stringtable

A stringtable is read from the PBO at load, so unlike a `$profile:` layout it doesn't reload hot. AddonBuilder's binarize pass applies a file whitelist and drops `.csv` from the PBO: pack with `-packonly`, or add the extension to the include list. In one workspace a `config.bin` from that same pass did not register at all, and the mod mounted silently broken.
