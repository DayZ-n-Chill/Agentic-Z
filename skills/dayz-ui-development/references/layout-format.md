# The `.layout` file format: syntax, widget classes, attributes and geometry

The brace syntax of a DayZ `.layout` file, every widget class and attribute seen in shipped layouts, the script API that goes with them, copyable layout patterns, and the arithmetic that turns a layout into screen rectangles.

Engine facts cite the vanilla file on `P:\`; those lines were re-read on a `P:\` holding 1.30. Counts over layout corpora, in-game measurements and third-party mod behaviour (Dabs Framework, DayZ Expansion, Community Online Tools and other mods) are not checked on `P:\`. The dated "corrected" notes are kept on purpose: they record claims that were measured and withdrawn, so nobody reintroduces them.

## Format Overview

`.layout` files use Enfusion brace format (not XML — an XML-format layout crashes native
CreateWidgets). Syntax: `WidgetClassName WidgetName { properties { children } }`

**Leaf `{ }` blocks are optional** (corrected 2026-07-05; the old "must have or the parser
crashes" claim here was refuted — vanilla omits them 99.6% of the time). What actually breaks
loading: unbalanced braces and XML format. See `rules-and-checklist.md` rule 1 for the full corrected semantics.

---

## File syntax the overview omits

The grammar above is the common authored shape. Three syntax facts are
missing from it; a new parser or tool that only implements the overview
will mis-read real files.

### A file may have more than one top-level widget

A `.layout` is a **sequence** of widget declarations, not a single root.
A parser that calls `parse_widget()` once and stops drops every sibling
after the first — silent degradation, no exception. The parser in this
repo collects roots until EOF (`LayoutDoc.roots`;
`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`, `Parser.parse_layout`) and
its fixture asserts `rootCount == 2`
(`scripts/tools/dayz-ui-lab/tests/test_parser.py`,
`test_multiroot_bom_block_comments_and_float_edges`).

This is a **parser / file-format** contract. The in-game probe fixtures
(`scripts/tools/dayz-ui-lab/probe/LF_UIProbe/`) are each a single root — `CreateWidgets` on a multi-root file
was not probed.

### Line continuation: `\` + newline inserts exactly one LF

Measured **in-game**, DayZDiag `1.29.163451`, 2026-07-28.

A quoted string may continue onto the next physical line by closing the
quotes, writing a backslash, then a newline, then the next quoted
fragment. The probe fixture
(`scripts/tools/dayz-ui-lab/probe/LF_UIProbe/gui/layouts/continuation.layout.template`):

```
text "Alpha"\
    "Beta"
```

`ButtonWidget.GetText(out string)` on that attribute returns `len=10`
and the value `"Alpha\nBeta"` — five + one newline + four. Bare
concatenation would be 9. The same length and the same value come back
from an LF source and from a CRLF source: the engine normalizes the
source EOL before the join.

Evidence: the two `LF_UI_PROBE_RESULT` lines the probe wrote to the RPT between
`[LF_UI_PROBE_BEGIN]` and `[LF_UI_PROBE_END]` (the RPT itself is not kept in this repo):

- `case=continuation-lf|status=loaded|len=10|value=<Alpha` / `Beta>`
- `case=continuation-crlf|status=loaded|len=10|value=<Alpha` / `Beta>`

The probe writes those lines from `GetText`
(`scripts/tools/dayz-ui-lab/probe/LF_UIProbe/scripts/5_Mission/LF_UIProbe_Mission.c`,
`ProbeContinuation`). Resolved 2026-07-28.
The RPT itself is written as CRLF; its 49,768 bytes contain neither a
lone LF nor a lone CR, so a literal CR in the string would have shown
up as a bare CR and a literal CRLF would have been `len=11`. The
logical value is therefore one LF, identical for both sources.

The parser implements this join
(`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`, `_scan_continuation`). A
parser that treats `\` as an unexpected character cannot read the
TraderX tooltip layouts that use the form (`BuyTooltip.layout`,
`CustomizeTooltip.layout`, `SellTooltip.layout`, `testTooltip.layout`;
third-party mod files, not vanilla).

### Block comments and leading/trailing-dot floats

Gotcha 8 below documents `//` line comments. That is not the whole
lexer. A tokenizer that only matches `//` and `-?\d+\.\d+` mis-reads:

- block comments `/* … */`
- floats with no digit before or after the point: `.5`, `1.`

The tokenizer accepts both (`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`,
`NUMBER_RE` and the `/*` branch in `tokenize`). Its tests cover them
(`scripts/tools/dayz-ui-lab/tests/test_parser.py`,
`test_multiroot_bom_block_comments_and_float_edges`). A validator fixture
already uses a leading-dot float:
`scripts/tools/dayz-script-validator/tests/fixtures/layout_braces/ok_inline_widget.layout`
(`size .5 -0.5`).

This is **offline syntax**, not an in-game measurement.

### Widget names: in the header, or a `Name` line

[VERIFIED file-format, 2026-10-28] Most vanilla layouts put a widget's name in its header:
`FrameWidgetClass FrameWidget {` (`P:\gui\layouts\day_z_ingamemenu.layout:1`). A few leave it out of the header,
which then holds the class alone or the class and the widget's ID, and give the name as the widget's
first property: `FrameWidgetClass {` then `Name "HudFrameWidget"`, and
`RichTextWidgetClass "{00000000E4E67D3A}" {` then `Name "DefaultActionWidget"`
(lines 1-2 and 11-12 of `day_z_hud.layout` on 1.30.164200). Vanilla ships both forms in one build, so the game reads both.
On a `P:\` holding 1.30.164014, where `day_z_hud.layout` still has the names in its headers, the second
form can be read at `P:\gui\layouts\xbox\day_z_ingamemenu_xbox.layout:232-233`
(`WrapSpacerWidgetClass "{00000000CDEFDF47}" {` then `Name "top"`).
On 1.30.164200, 10 of the 227 vanilla layouts have ID headers: `day_z_hud.layout` and nine
console, Xbox, debug and editor layouts. 1.30.164014 has the same nine, and 1.29 none of its 216.
The ID is the one a 1.30 layout variant puts in `Prefab`; how it is derived: `layout-variants-130.md` section 1.
`day_z_hud.layout` changed form in 1.30.164200: each of its 292 widgets gives its name on a
`Name` line (its other three blocks are `ScriptParamsClass`, with no name), so the file went from
5,176 lines on 1.30.164014 to 5,468, and the citations of it in this skill give the 1.30.164200
line. Other lines changed with it: 115 colors, positions and sizes are rounded to three decimals,
and the 12 images whose names hold `mtl_down` have `mode blend` where they had `mode additive`.
The other vanilla layouts this skill cites are the same files on 1.30.164014 and 1.30.164200, and
on 1.29 where 1.29 has them (it has neither `action_info_spacer.layout` nor
`SimpleIconTemplate.layout`).

The parser in `scripts/tools/dayz-ui-lab` takes the token after the class as the name, so on a layout in the second form it
reports the ID string, or an empty name, and keeps the real name as a `Name` attribute
(`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`, `Parser.parse_widget`; run on `day_z_hud.layout` of
both builds on 2026-10-28).

---

## Complete Widget Class Catalog

### Container Widgets (no visual rendering)

| Layout Class | Script Class | Renders | Notes |
|---|---|---|---|
| `FrameWidgetClass` | `Widget` | no | Invisible container, most common parent |
| `ScrollWidgetClass` | `ScrollWidget` | no | Scrollable container, auto-scrollbars |
| `GridSpacerWidgetClass` | `GridSpacerWidget` | no | Auto-layout grid (ObservableCollection target) |
| `WrapSpacerWidgetClass` | `WrapSpacerWidget` | no | Wrapping flow layout (ObservableCollection target) |

### Visual Widgets

| Layout Class | Script Class | Renders | Notes |
|---|---|---|---|
| `ImageWidgetClass` | `ImageWidget` | yes | Background, icons, colored panels |
| `TextWidgetClass` | `TextWidget` | Text only | Static/bound text display |
| `RichTextWidgetClass` | `RichTextWidget` | Rich text | Supports inline `<image>`, `<font>`, `<b>` tags |
| `ButtonWidgetClass` | `ButtonWidget` | Minimal | Clickable, receives OnClick events |
| `EditBoxWidgetClass` | `EditBoxWidget` | yes | Single-line text input |
| `MultilineEditBoxWidgetClass` | `MultilineEditBoxWidget` | yes | Multi-line text input |
| `CheckBoxWidgetClass` | `CheckBoxWidget` | yes | Toggle checkbox |
| `XComboBoxWidgetClass` | `XComboBoxWidget` | yes | Dropdown selector |
| `SliderWidgetClass` | `SliderWidget` | yes | Value slider (min/max/step) |
| `ProgressBarWidgetClass` | `ProgressBarWidget` | yes | Progress indicator |
| `SimpleProgressBarWidgetClass` | `SimpleProgressBarWidget` | yes | Simpler progress variant |
| `CanvasWidgetClass` | `CanvasWidget` | no | Programmatic drawing (DrawLine) |
| `VideoWidgetClass` | `VideoWidget` | yes | Video playback |
| `RTTextureWidgetClass` | `RTTextureWidget` | yes | Render target (3D model preview) |

### Special / MVC Widgets

| Layout Class | Notes |
|---|---|
| `ScriptParamsClass` | Holds MVC params: `Relay_Command`, `Two_Way_Binding` |

### Corpus-verified additions (2026-07-04 — classes the tables above omitted; counts from the 459-layout corpus)

| Layout Class | Count | Notes |
|---|---|---|
| `PanelWidgetClass` | 2,090 | 2nd most-used class in the corpus. Container; renders only via a `style` (9-slice) — without one it is invisible like Frame |
| `MultilineTextWidgetClass` | 351 | Multi-line static text (word-wraps; distinct from MultilineEditBox) |
| `TextListboxWidgetClass` | 133 | Row/column list (AddItem/GetSelectedRow API in the widget table of `script-recipes.md`) |
| `WindowWidgetClass` | 66 | Titled window chrome |
| `ItemPreviewWidgetClass` | 65 | 3D item render; script API `SetItem(EntityAI)/SetView(idx)` — `P:\scripts\3_game\gameplay.c:286-301` |
| `ThreeStateCheckboxWidgetClass` | 10 | CheckBox variant |
| `PlayerPreviewWidgetClass` | 5 | 3D player render; `SetPlayer(DayZPlayer)` — `P:\scripts\3_game\gameplay.c:305-312` |
| `PasswordEditBoxWidgetClass` | 1 | EditBox with masked input |

Attributes the property reference below omits (corpus counts): `priority` (1,440 — layout-side
z-order, higher = on top), `mode` (1,697 — image blend mode), `inheritalpha` (1,129 — multiply
alpha with parent), `userID` (467 — int id for `FindAnyWidgetById`), `text_proportion` (437 —
text size as fraction of widget height; the vanilla text-scaling mechanism), `scaled` (939),
`fixaspect` (461 — keyword values: `fixwidth`/`inside`/`outside`/`none`, not 0/1), `keepsafezone`
(163). Full frequency table in `layout-empirical-corpus.md` section 2.

The counts in the paragraph above (`text_proportion` 437 and the rest) are the
2026-05-13 300-layout sample in `layout-empirical-corpus.md` section 2. They are not
the 819-file 2026-08-19 counts later in this file (`text_proportion` 1048 =
679+361+5+3). Keep both; different corpora.

---

## Widget Properties — Complete Reference

### Positioning & Sizing

```
position X Y              // Position (exact units if hexactpos/vexactpos=1, fraction 0-1 if =0)
size W H                  // Size (exact units if hexactsize/vexactsize=1, fraction 0-1 if =0)
hexactpos 0|1             // 1=exact X position, 0=proportional (0.0-1.0)
vexactpos 0|1             // 1=exact Y position, 0=proportional (0.0-1.0)
hexactsize 0|1            // 1=exact width, 0=proportional (0.0-1.0)
vexactsize 0|1            // 1=exact height, 0=proportional (0.0-1.0)
```

An exact unit is 1/1080 of the screen height, on both axes: the engine draws `declared ×
height/1080` px whatever the width (measured in game at heights 461 to 1108 and at 2560x1080;
`rules-and-checklist.md` rule 3). It is a pixel only at a 1080-pixel-tall screen. *(corrected 2026-10-03: the
comments above said «pixels».)*

**Rule** (corrected 2026-07-04): declare all 4 flags explicitly for readability — but omission
defaults to proportional in practice, not "undefined" (42 vanilla widgets omit all four, incl.
production menu roots like `P:\gui\layouts\day_z_ingamemenu.layout:1`, and render correctly with fractional values).

**Common patterns** (corpus-quantified, 8,671 vanilla widgets):
- **Mixing exact and proportional axes on one widget is the vanilla norm (50.8%)** — the old
  "mixing is fragile" warning here was refuted by ground truth. Top profiles: exact pos +
  proportional size (1,892×) and exact pos + prop width + pixel height (1,182×).
- The dominant positioning idiom is **anchor + zero offset**: `halign/valign *_ref` +
  `position 0 0` (70% of exact-pos widgets have position 0 0) + proportional or height-pixel size.
- Full proportional (0000): 26.0% — e.g. MultilineText is 93% all-proportional.
- Full exact (1111): 21.9% — scales with the screen height like everything exact
  (`rules-and-checklist.md` rule 3). *(corrected 2026-10-03: this line said «reserve for pixel-true chrome; it is what
  breaks off-1080p (exact units = physical resolution, `P:\scripts\1_core\proto\enwidgets.c:68-71`)».)*

### Alignment

```
halign left_ref|center_ref|right_ref    // Horizontal alignment reference
valign top_ref|center_ref|bottom_ref    // Vertical alignment reference
```

Used with proportional positioning. `center_ref` centers the widget relative
to parent. **Heavily used, not rare** (corrected 2026-07-04: 4,518 `valign` +
4,157 `halign` occurrences in the 300-layout corpus — top-10 attributes, more
common than `text` or `color`). Anchoring is central to how vanilla positions
resolution-independent UI: e.g. `day_z_hud.layout` roots use `halign center_ref`
+ `valign center_ref` with proportional size; `loading.layout` anchors its 16:9
background the same way. Misunderstood anchors are a classic source of "looks
right in the mockup, lands elsewhere in-game".

**Offset sign of `halign right_ref` / `valign bottom_ref` — settled
2026-08-19, read back from the engine.** The offset is **subtracted**: it is a
distance measured inward from the reference edge, not a displacement added to
it. The resolver (`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`,
`resolve_geometry`) uses that form; the additive form
`parent_right - width + px` is wrong.

Measured with `ui_tree` over `HudFrameWidget` on a live client (DayZ
1.29.163709, 1920x1080), comparing each anchored widget's drawn edge against
its parent's. Only `hexactpos` / `vexactpos == 1` rows are quoted, so on this
1080-pixel-tall screen the numbers are pixels and no unit conversion sits
between the layout and the measurement (exact units scale with the screen
height: `rules-and-checklist.md` rule 3):

| widget | anchor | declared offset | drawn edge − parent edge |
|---|---|---|---|
| `BadgesPanel` | `right_ref` | 252 | −252 |
| `BadgesSpacer` | `right_ref` | 213 | −213 |
| `Blood` | `right_ref` | 43 | −43 |
| `NotifierDivider` | `right_ref` | 86 | −86 |
| `Hungry` | `right_ref` | 139 | −139 |
| `Thirsty` | `right_ref` | 182 | −182 |
| `BloodType` | `right_ref` | **−4** | **+4** |
| `BadgesSpacer` | `bottom_ref` | 23.5 | −23.5 |
| `NotifierDivider` | `bottom_ref` | 30 | −30 |
| `VoiceLevelsPanel` | `bottom_ref` | 80 | −80 |
| `TemperatureValueBottom` | `bottom_ref` | **−12** | **+12** |

The two negative-offset rows are what make this a measurement rather than a
coincidence. A widget declared at `-4` is drawn 4px **outside** its parent's
right edge, and only the subtracting form predicts that; a table of positive
offsets alone would have been satisfied by either rule with a sign flip. Both
axes behave identically, so `bottom_ref` needs no separate treatment.

### Visibility & Interaction

```
visible 0|1               // Initial visibility (0=hidden, 1=visible, default=1)
ignorepointer 0|1         // 1=transparent to mouse events, 0=receives events
clipchildren 0|1           // 1=children clipped to parent bounds (overflow hidden)
```

**Critical**: `ignorepointer 1` on all background ImageWidgets.
Without it, backgrounds steal mouse events from interactive children.

**Tooling trap, not a layout-semantics change.** `visible 0`
is a legal authored value (hidden). In Python, `int(attr(...) or 1)`
turns that 0 into 1 because 0 is falsy — a renderer written that way shows every
hidden widget. Any reader of integer flags (`visible`, and the same
pattern on any other 0-is-valid attribute) must use an explicit
missing-value sentinel, not `x or default`. The parser's
`attr_int` does this (`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`).

### Visual Properties

```
color R G B A             // Color as floats 0.0-1.0 (ImageWidget, TextWidget)
stretch 0|1               // 1=stretch image to fill widget bounds
```

**Color in layout**: Always 0.0-1.0 floats: `color 0.12 0.12 0.12 0.92`
**Color in script**: ARGB 0-255 integers: `widget.SetColor(ARGB(235, 30, 30, 30))`

### Text Properties (TextWidget, RichTextWidget, ButtonWidget)

```
font "gui/fonts/Metron"         // Font path (Metron=bold, MetronBook=regular)
text "LABEL"                     // Static text content
"text halign" left|center|right  // Text horizontal alignment
"text valign" top|center|bottom  // Text vertical alignment
```

**Available fonts** (vanilla DayZ):
- `gui/fonts/Metron` — bold/medium weight, good for headers/labels
- `gui/fonts/MetronBook` — regular weight, good for body text
- `gui/fonts/amorserifpro` — serif font

### Dabs MVC Binding Properties

```
scriptclass "ViewBinding"         // Enable MVC auto-binding (on bound widgets)
Two_Way_Binding 1                 // Enable bidirectional binding (EditBox ↔ property)
```

**In ScriptParamsClass block** (empirically settled 2026-07-04, 157/157 corpus instances:
`ScriptParamsClass` always sits in a dedicated anonymous block containing no child widgets —
the widget's only block on leaves, or a second block when the widget has children; never mixed
into the same block as child widgets. No inner `{ }` inside ScriptParamsClass — that form appeared
only in layouts that copied this file's old example):
```
ScriptParamsClass {
    Relay_Command "MethodName"    // Routes button OnClick to Controller method
}
```

### Scroll Widget Properties (in script)

```
ScrollWidget scroll;
float pos01 = scroll.GetVScrollPos01();  // 0.0-1.0 normalized position
scroll.VScrollToPos01(0.5);              // Scroll to middle
scroll.VScrollToWidget(childWidget);     // Scroll to make child visible
bool visible = scroll.IsScrollbarVisible();
float contentH = scroll.GetContentHeight();
float contentW = scroll.GetContentWidth();
```

### Spacer Widget Properties (in script)

```
SpacerWidget spacer;
spacer.SetContentAlignmentH(WidgetAlignment.WA_CENTER);
spacer.SetContentAlignmentV(WidgetAlignment.WA_TOP);
```

---

## Widget API — Key Script Functions

### Positioning (script-side)

```
// Relative to parent (what GetPos/SetPos use)
widget.GetPos(out float x, out float y);
widget.SetPos(float x, float y);
widget.GetSize(out float w, out float h);
widget.SetSize(float w, float h);

// Absolute screen coordinates
widget.GetScreenPos(out float x, out float y);
widget.SetScreenPos(float x, float y);
widget.GetScreenSize(out float w, out float h);
widget.SetScreenSize(float w, float h);

// NOTE: GetPos returns relative-to-parent. GetScreenPos returns absolute.
// For drag operations, be consistent — use one coordinate space throughout.
```

### Hierarchy Navigation

```
Widget parent = widget.GetParent();
Widget firstChild = widget.GetChildren();
Widget nextSibling = widget.GetSibling();

// Walk all children:
Widget child = parent.GetChildren();
while (child)
{
    // process child
    child = child.GetSibling();
}

// Find by name (recursive)
Widget found = root.FindAnyWidget("WidgetName");

// Find by path. The vanilla comment writes the path with dots:
// FindWidget("widget1.widget2.widget3.mywidget")  (P:\scripts\1_core\proto\enwidgets.c:168)
// A slash form ("Parent/Child/Grandchild") is also seen in mod code; neither form is tested in game here.
Widget found2 = root.FindWidget("Parent.Child.Grandchild");

// Find by integer ID
widget.SetUserID(42);
Widget found3 = root.FindAnyWidgetById(42);
```

### Custom Data Attachment

```
// Attach any Class to a widget (useful for tag/item data)
widget.SetUserData(myDataObject);

// Retrieve
Class data;
widget.GetUserData(data);
MyDataClass myData = MyDataClass.Cast(data);
```

### Dynamic Widget Creation

```
// From layout file (preferred)
Widget root = GetGame().GetWorkspace().CreateWidgets(layoutPath, parentWidget);

// Programmatic creation (rare, for dynamic needs). CreateWidget is a WorkspaceWidget method
// (P:\scripts\1_core\proto\enwidgets.c:179), so call it on the workspace, not on any widget.
Widget w = GetGame().GetWorkspace().CreateWidget(WidgetType, left, top, width, height, flags, color, sort, parent);

// Insert at specific position in child list
parent.AddChildAfter(newChild, afterThisChild);

// Remove from parent
parent.RemoveChild(child);

// Destroy widget and all children
widget.Unlink();
```

### Visual Effects

```
// Text outline (size in pixels, ARGB color)
textWidget.SetOutline(1, 0xFF000000);       // 1px black outline
int outSize = textWidget.GetOutlineSize();

// Text shadow
textWidget.SetShadow(2, 0x80000000, 0.8, 1.0, 1.0);  // size, color, opacity, offsetX, offsetY

// Text exact pixel size (requires exact text flag)
textWidget.SetTextExactSize(14);  // 14px

// Get rendered text dimensions
int textW;
int textH;
textWidget.GetTextSize(textW, textH);

// Text elision (truncate with "..."). RichTextWidget only (P:\scripts\1_core\proto\enwidgets.c:229).
richTextWidget.ElideText(0, 200.0, "...");  // line 0, max 200px, suffix "..."

// Alpha masking (circular reveals, wipes, etc.)
imageWidget.LoadMaskTexture("path/to/mask.edds");
imageWidget.SetMaskProgress(0.5);         // 0.0-1.0
imageWidget.SetMaskTransitionWidth(0.1);  // soft edge
```

### Performance

```
// Both calls below exist only on RenderTargetWidget (P:\scripts\1_core\proto\enwidgets.c:236-240),
// not on every widget.
// Render every N frames (reduce GPU cost)
renderTarget.SetRefresh(2, 0);  // render every 2nd frame, offset 0

// Resolution scaling of the render target
renderTarget.SetResolutionScale(1.5, 1.5);  // scale 150%

// Global widget brightness [-15, 0], 0=normal (P:\scripts\1_core\proto\enwidgets.c:114-117).
// Shown so you can recognize the calls. Do not make them from a mod: they are global and
// vanilla drives them from the player's HUD brightness setting (gotcha 3 below).
SetLV(-2.0);       // darken all widgets
SetTextLV(-1.0);   // darken text only
```

### Z-Order

```
// Sort order (higher = rendered on top)
widget.SetSort(50000);   // high value = above most UI
int sort = widget.GetSort();

// NOTE (corrected 2026-07-03): SetSort is an ABSOLUTE set, not additive. The "ADDS to
// existing value" note was a mis-transcription — in enwidgets.c the `//! ADDS the value to
// the existing flag` comment belongs to SetFlags (line 128), and ClearFlags SUBSTRACTS
// (line 131). SetSort (line 130) carries no such comment. It is SetFlags/ClearFlags that
// are additive/subtractive, not SetSort. Layout-side equivalent of z-order: the `priority`
// attribute (higher = on top).
```

### Flags (script-side)

```
// WidgetFlags enum
SOURCEALPHA    // Use source alpha blending
BLEND          // Enable blending
ADDITIVE       // Additive blending
VISIBLE        // Widget visible
HEXACTPOS      // Horizontal exact position (exact units, 1/1080 of screen height)
VEXACTPOS      // Vertical exact position (exact units)
HEXACTSIZE     // Horizontal exact size (exact units)
VEXACTSIZE     // Vertical exact size (exact units)
NOFILTER       // No texture filtering
STRETCH        // Stretch image to fill
IGNOREPOINTER  // Transparent to mouse
CLIPCHILDREN   // Clip children to bounds
DRAGGABLE      // Enable native drag support
NOFOCUS        // Cannot receive focus
RENDER_ALWAYS  // Render even when not visible (rare)
DISABLED       // Widget disabled

// Set/Clear flags
widget.SetFlags(WidgetFlags.IGNOREPOINTER);
widget.ClearFlags(WidgetFlags.VISIBLE);
```

*(corrected 2026-10-03: the four exact flags above said «(pixels)»; exact units are 1/1080 of the
screen height, `rules-and-checklist.md` rule 3.)*

---

## RichTextWidget — Inline Formatting

`RichTextWidget` supports HTML-like inline tags:

```
// In script:
RichTextWidget rtw = RichTextWidget.Cast(root.FindAnyWidget("MyRichText"));
string formatted = "<b>Bold</b> and <font name='gui/fonts/MetronBook'>different font</font>";
rtw.SetText(formatted);

// Inline image from imageset:
string withIcon = "<image set='dayz_gui' name='icon_pin' /> Location";
rtw.SetText(withIcon);
```

**Supported tags**: `<b>`, `<font name='...'>`, `<image set='...' name='...'/>`

---

## Layout Validation Checklist

Before delivering any .layout file:

- [ ] Brace format (not XML); brace count balanced (opens == closes)
- [ ] All 4 unit flags declared on every widget (0 = fraction of parent; 1 = 1/1080 of screen height, `rules-and-checklist.md` rule 3)
- [ ] All ImageWidget backgrounds have `ignorepointer 1`
- [ ] All visible backgrounds use `ImageWidgetClass`, or a `PanelWidgetClass` with a `style` that draws (a Frame, or a Panel with no style, draws nothing)
- [ ] Widget names unique across entire layout
- [ ] No `scriptclass "ViewBinding"` on root widget (causes double controller)
- [ ] EditBox/Button widgets do not have `ignorepointer 1` (need mouse events)
- [ ] `ScriptParamsClass` with `Relay_Command` inside every bound Button
- [ ] Layout path uses forward slashes, correct case (Linux-sensitive PBO)
- [ ] No trailing whitespace or BOM characters
- [ ] Unit choice made per axis on purpose. *(The earlier item here, "all-pixel or all-proportional per widget", is withdrawn: mixing exact and proportional axes on one widget is the vanilla norm, see "Common patterns" above.)*
- [ ] Color values as 0.0-1.0 floats (not 0-255 integers)
- [ ] `clipchildren 1` on scrollable/overflow containers
- [ ] `stretch 1` on ImageWidgets used as backgrounds

---

## Common Layout Patterns

### Colored Background Panel
```
ImageWidgetClass PanelBg {
    position 0 0
    size 400 300
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    stretch 1
    ignorepointer 1
    color 0.12 0.12 0.12 0.92
    {
    }
}
```

### Button with Bg + Text + Relay_Command
```
ButtonWidgetClass BtnSave {
    position 10 10
    size 100 30
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    {
        ImageWidgetClass BtnSaveBg {
            position 0 0
            size 1 1
            hexactpos 0
            vexactpos 0
            hexactsize 0
            vexactsize 0
            stretch 1
            ignorepointer 1
            {
            }
        }
        TextWidgetClass BtnSaveText {
            position 0 0
            size 1 1
            hexactpos 0
            vexactpos 0
            hexactsize 0
            vexactsize 0
            font "gui/fonts/Metron"
            "text halign" center
            "text valign" center
            text "SAVE"
            ignorepointer 1
        }
    }
    {
        ScriptParamsClass {
            Relay_Command "BtnSave"
        }
    }
}
```
*(Corrected 2026-07-04: `ScriptParamsClass` goes in its own second anonymous block — the previous
version of this example put it alongside the child widgets, a form with zero empirical support in
157 corpus instances.)*

### MVC-Bound EditBox with Two-Way Binding
```
EditBoxWidgetClass EditPrefix {
    scriptclass "ViewBinding"
    Two_Way_Binding 1
    position 14 116
    size 286 28
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    font "gui/fonts/MetronBook"
    {
    }
}
```

### Scrollable List Container
```
ScrollWidgetClass RulesScroll {
    position 0 30
    size 319 400
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    clipchildren 1
    {
        GridSpacerWidgetClass RulesList {
            position 0 0
            size 319 0
            hexactpos 1
            vexactpos 1
            hexactsize 1
            vexactsize 0
            {
            }
        }
    }
}
```

### Fullscreen Click Blocker (with ignorepointer!)
```
// v2.7 pattern: ClickBlocker as visual-only element.
// ChangeGameFocus(1) + SetDisabled(true) handle click-through prevention.
// DO NOT remove ignorepointer — it steals mouse events from buttons!
ImageWidgetClass ClickBlocker {
    position 0 0
    size 1 1
    hexactpos 0
    vexactpos 0
    hexactsize 0
    vexactsize 0
    color 0.0 0.0 0.0 0.004
    stretch 1
    ignorepointer 1
    {
    }
}
```

---

## Gotchas & Pitfalls

1. **FrameWidgetClass draws nothing, and PanelWidgetClass draws only through a `style`** — use ImageWidgetClass, or a styled Panel, for backgrounds
2. **Color 0.0-1.0 in layout, 0-255 in script** — mixing causes invisible or wrong-colored widgets
3. **Widget colors are darkened by the player's HUD brightness — do not fight it, and never
   call `SetLV`.** *(Corrected twice. 2026-07-03 retired "boost colors 30%+". 2026-08-22 retired
   its replacement, `SetLV(0)` at init: those setters are `proto static`/global
   (`SetLV` and `SetTextLV`, `P:\scripts\1_core\proto\enwidgets.c:114-117`) and vanilla drives them from
   `EDayZProfilesOptions.HUD_BRIGHTNESS` in `SetHudBrightness`
   (`P:\scripts\3_game\dayzgame.c:3910-3919`), so calling them from a mod overwrites the player's setting.)*
   Author ARGB honestly, pick colors that survive a dimmed HUD, and verify at a non-zero
   brightness. Saturated colors were barely affected; grays and pastels were the ones darkened.
   See `theme-and-color.md`, "Color system".
4. **Low alpha clamps to invisible** — measured bracket: 0x12 invisible, 0x26 visible → threshold in
   (0x12, 0x26]. Keep alpha ≥ 0x30 (48) for must-see elements (corrected 2026-07-04; the old
   two-threshold claim here contradicted the measured data points in `text-sizing-and-rendering.md`)
5. **`scriptclass "ViewBinding"` on root = double controller** — only on bound child widgets
6. **Button children need careful naming** — auto-bind may miss ImageWidget/TextWidget inside ButtonWidget. Use child-walk fallback (FindBtnChildBg/FindBtnChildText pattern)
7. **Widget name collisions** across the layout cause FindAnyWidget to return the wrong widget
8. **Comments are // style** (C++ line comments), not `<!-- -->` XML comments
9. **No semicolons** after property values (unlike config.cpp)
10. **Inline format is valid** but hard to verify: `ImageWidgetClass Bg { position 0 0 size 1 1 ... { } }`
    **Parser contract.** Grouping
    values by physical line collapsed that example into a single attribute
    `position: [0, 0, "size", 1, 1, "stretch", 1, "ignorepointer", 1]`.
    Grouping by key arity (`position` / `size` take two numbers; flags
    take one) keeps `position`, `size`, `stretch` and `ignorepointer`
    apart. The parser in this repo used to group by `peek().line == line`
    (`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py`, `Parser.parse_values`) and,
    on that exact input, emitted only `position` with the collapsed
    list (reproduced 2026-08-19, then fixed the same
    day). It now consumes `ATTRIBUTE_ARITY` tokens per key, which
    fixes the 131 attributes that table lists and no others: a key absent
    from it still falls back to the physical line, so two unknown keys
    written inline still collapse into one (measured 2026-08-19). Any new
    parser must split by key arity, not by the physical line.
11. **`SetSort` is an absolute set** *(corrected 2026-07-03 — the additive `//! ADDS` comment in
    `P:\scripts\1_core\proto\enwidgets.c:128` belongs to `SetFlags`, not `SetSort` at `:130`)*. `SetFlags` adds and
    `ClearFlags` substracts; `SetSort` replaces. Layout-side z-order = the `priority` attribute.
12. **`GetPos` returns relative-to-parent**, `GetScreenPos` returns absolute — critical for drag
13. **JSON file > 64KB causes truncation** in DayZ file I/O (not checked on `P:\`). Split large data across multiple files or compress.
14. **ImageSets** (`set:dayz_gui image:icon_name`) only work with `LoadImageFile` on ImageWidget or inline in RichTextWidget — not in layout `color` property.

---

## Production Patterns

Patterns common in shipped DayZ mods with polished UIs. They are mod
practice, not vanilla behaviour, and are not checked on `P:\`.

### Pattern: Imageset Icons

DayZ ships with built-in icon imagesets. No .edds needed.

```
// In script — load icon from vanilla imageset
ImageWidget icon = ImageWidget.Cast(root.FindAnyWidget("MyIcon"));
if (icon)
{
    string iconPath = "set:dayz_gui image:icon_pin";
    icon.LoadImageFile(0, iconPath);
}

// In RichTextWidget — inline icon
RichTextWidget rtw = RichTextWidget.Cast(root.FindAnyWidget("MyRichText"));
if (rtw)
{
    string rt = "<image set='dayz_gui' name='icon_pin' /> Location found";
    rtw.SetText(rt);
}
```

Common vanilla imagesets: `dayz_gui`, `dayz_inventory`, `dayz_crosshairs`.
Custom imagesets can be registered via `config.cpp` → `CfgMods` → `defs` → `imageSets`.

### Pattern: Tabbed Category Navigation

Trader and market menus use tab bars for item categories.
Pattern: ButtonWidget per tab → shared content panel → swap visibility.

```
// Data model: which tab is active
protected int m_ActiveTab;

// Activate tab N
void SelectTab(int idx)
{
    m_ActiveTab = idx;

    // Visual: highlight active tab, dim others
    int i;
    for (i = 0; i < m_TabCount; i = i + 1)
    {
        bool isActive = (i == idx);
        ImageWidget tabBg = m_TabBgs[i];
        if (tabBg)
        {
            if (isActive)
            {
                tabBg.SetColor(COL_TAB_ACTIVE);
            }
            else
            {
                tabBg.SetColor(COL_TAB_INACTIVE);
            }
        }
    }

    // Content: show/hide panels or repopulate list
    RefreshContent();
}
```

### Pattern: Scrollable Item List with Dynamic Rows

```
// Layout structure:
// ScrollWidgetClass ItemScroll {
//     GridSpacerWidgetClass ItemList {  // or WrapSpacerWidgetClass
//         // children added dynamically from script
//     }
// }

// Script — populate list
void PopulateItems(array<ItemData> items)
{
    // Clear previous children
    Widget child = m_ItemList.GetChildren();
    while (child)
    {
        Widget next = child.GetSibling();
        child.Unlink();  // destroy widget + children
        child = next;
    }

    // Create new rows from layout prefab
    int i;
    string rowLayout = "MyMod/gui/layouts/ItemRow.layout";
    for (i = 0; i < items.Count(); i = i + 1)
    {
        Widget row = GetGame().GetWorkspace().CreateWidgets(rowLayout, m_ItemList);
        if (!row)
            continue;

        // Populate row data
        TextWidget nameW = TextWidget.Cast(row.FindAnyWidget("ItemName"));
        if (nameW)
        {
            nameW.SetText(items[i].m_Name);
        }
        // ... price, icon, etc.
    }
}
```

**Performance note**: For lists > 50 items, consider virtual scrolling —
only create visible rows + buffer, recycle on scroll. Creating
all rows upfront causes lag on servers with 1000+ items.

### Pattern: Search/Filter Bar

```
// EditBox for search input
// In layout:
// EditBoxWidgetClass SearchInput { ... Two_Way_Binding 1 ... }

// In controller — filter on text change
string SearchText;  // bound to SearchInput via ViewBinding

void OnSearchChanged()
{
    string query = SearchText;
    query.ToLower();

    // Filter visible items
    int i;
    for (i = 0; i < m_AllItems.Count(); i = i + 1)
    {
        string itemName = m_AllItems[i].m_Name;
        itemName.ToLower();

        bool match = false;
        if (query == "")
        {
            match = true;
        }
        else if (itemName.IndexOf(query) >= 0)
        {
            match = true;
        }
        m_ItemWidgets[i].Show(match);
    }
}
```

### Pattern: Confirmation Dialog

Two-phase button: first press → "Confirm?" state + timer → second press → execute.

```
protected bool m_ConfirmActive;
protected float m_ConfirmTimer;

void BtnDangerousAction()
{
    if (!m_ConfirmActive)
    {
        m_ConfirmActive = true;
        m_ConfirmTimer = 3.0;  // 3 seconds to confirm

        string confirmLabel = "Confirm?";
        if (BtnText)
        {
            BtnText.SetText(confirmLabel);
        }
        if (BtnBg)
        {
            BtnBg.SetColor(COL_RED);
        }
        return;
    }

    // Second press — execute action
    m_ConfirmActive = false;
    ExecuteDangerousAction();
    RestoreButtonNormal();
}

// In Update(dt): expire confirmation
if (m_ConfirmActive)
{
    m_ConfirmTimer = m_ConfirmTimer - dt;
    if (m_ConfirmTimer <= 0.0)
    {
        m_ConfirmActive = false;
        RestoreButtonNormal();
    }
}
```

### Pattern: Status Feedback Toast

Temporary status message that auto-fades.

```
protected float m_FeedbackTimer;
protected string m_FeedbackMsg;

void ShowFeedback(string msg, float durationS)
{
    m_FeedbackMsg = msg;
    m_FeedbackTimer = durationS;

    if (StatusLabel)
    {
        StatusLabel.SetText(msg);
        StatusLabel.SetColor(COL_GREEN);
    }
}

// In Update(dt):
if (m_FeedbackTimer > 0.0)
{
    m_FeedbackTimer = m_FeedbackTimer - dt;
    if (m_FeedbackTimer <= 0.0)
    {
        if (StatusLabel)
        {
            string defaultStatus = "READY";
            StatusLabel.SetText(defaultStatus);
            StatusLabel.SetColor(COL_TEXT_DIM);
        }
    }
}
```

### Pattern: Server-Configurable UI Colors

The DayZ Expansion market menu lets server owners configure menu colors via JSON.
Pattern: load color config from server settings, apply at menu open.

```
class MyMenuColors
{
    int BaseBackground;
    int HeaderBackground;
    int ButtonNormal;
    int ButtonHover;
    int TextPrimary;
    int TextSecondary;
    int AccentColor;

    void SetDefaults()
    {
        BaseBackground = ARGB(235, 30, 30, 30);
        HeaderBackground = ARGB(240, 37, 42, 54);
        ButtonNormal = ARGB(255, 37, 53, 80);
        // ... etc
    }
}

// On menu open — apply server-configured or default colors
void ApplyColorScheme(MyMenuColors scheme)
{
    if (!scheme)
        return;

    if (PanelBg)
    {
        string tex = "#(argb,8,8,3)color(1,1,1,1,CO)";
        PanelBg.LoadImageFile(0, tex);
        PanelBg.SetColor(scheme.BaseBackground);
    }
    // ... apply to all themed widgets
}
```

### Pattern: RTTextureWidget for 3D Item Preview

The DayZ Expansion market menu shows 3D item previews in the UI using RTTextureWidget.

```
// In layout:
// RTTextureWidgetClass ItemPreview3D {
//     position 10 10
//     size 200 200
//     ... 4 exact flags ...
//     { }
// }

// In script — set up 3D preview
// Note: requires entity creation for the preview object
// and camera setup — complex pattern; the DayZ Expansion market
// menu is a full implementation. Key API:
// RTTextureWidget has SetRTTextureWidget() on EntityAI
// for rendering entity to UI texture.
```

### Pattern: HUD Overlay

For HUD elements that persist across menus:

```
// Create in MissionGameplay.OnInit (or OnUpdate with once-guard)
// Layout: fullscreen frame, children positioned absolutely
// Use `root.SetSort(1000)` to layer above game HUD but below menus

// Critical: HUD widgets must NOT use ChangeGameFocus/ShowUICursor
// They are passive overlays — no input interception

// Update in MissionGameplay.OnUpdate:
if (m_HudWidget && m_HudWidget.IsVisible())
{
    UpdateHudData();
}
```

### Pattern: Sound Feedback

```
// UI click sound (vanilla)
static void PlayUIClick()
{
    SEffectManager.PlaySound("Backpack_SoundSet", vector.Zero);
}

// UI action sound (more noticeable)
static void PlayUIAction()
{
    SEffectManager.PlaySound("pickUpBackPack_Metal_SoundSet", vector.Zero);
}
```

Use sparingly — on button clicks and confirmations, not on hover or tab switch.

---

## ScriptClass — Attaching Script Handlers to Layout Widgets

### Basic Pattern
A widget can have a `scriptclass` property pointing to a ScriptedWidgetEventHandler.
The engine instantiates it and calls `OnWidgetScriptInit`:

Layout:
```
EditBoxWidgetClass myInput {
    scriptclass "MyValidator_Number"
    position 10 10
    size 200 30
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    {
    }
}
```

Script:
```
class MyValidator_Number : ScriptedWidgetEventHandler {
    Widget root;

    void OnWidgetScriptInit(Widget w) {
        root = w;
        w.SetHandler(this);  // required for events
        // Called once when layout is created
    }

    override bool OnChange(Widget w, int x, int y, bool finished) {
        // validate input...
        return false;
    }
}
```

### ScriptParamsClass — Passing Parameters from Layout to Script

The `reference` keyword in the handler class marks fields that receive values
from the layout's ScriptParamsClass block:

Script:
```
class MyGapHandler : ScriptedWidgetEventHandler {
    reference int gapHorizontal;    // populated from layout
    reference int gapVertical;      // populated from layout
    Widget root;

    void OnWidgetScriptInit(Widget w) {
        root = w;
        // gapHorizontal and gapVertical already have values from layout
        w.SetHandler(this);
    }
}
```

Layout:
```
PanelWidgetClass myPanel {
    scriptclass "MyGapHandler"
    position 0 0
    size 1 1
    hexactpos 1
    vexactpos 1
    hexactsize 0
    vexactsize 0
    {
    }
    {
        ScriptParamsClass {
            gapHorizontal -10
            gapVertical -10
        }
    }
}
```

Note: ScriptParamsClass goes in a second child block of the widget.
The first `{ }` is for child widgets, the second `{ ScriptParamsClass { ... } }` is for params.

### Use Cases for ScriptClass
- **Validators**: Number-only, float-only, steamid format validation on EditBox
- **Gap/margin handlers**: Dynamic sizing based on parent
- **Auto-scroll**: Clip children based on scroll position
- **Tooltip triggers**: Show tooltip on hover
- **Drag handlers**: Custom drag-and-drop behavior
- **Loading animations**: Rotating/pulsing icon widgets

---

## Styles in Layout

Reference a registered style in layout:
```
PanelWidgetClass myBorder {
    style MyMod_Clean_outline
    color 1 1 1 1
    ...
}
```
The style name must match one registered in a .styles file declared in config.cpp,
under the block of this widget's type.
Styles provide state-based rendering with 9-slice image support from ImageSets. The state names
are `Normal`, `Pushed`, `Highlight`, `Focus` and `Disabled` for a button
(the `State` blocks at `P:\gui\looknfeel\dayzwidgets.styles:1598-1642`); there is no `Pressed`
and no `Hover`. The whole system is in `styles-format.md`.


---

## Computing a widget's absolute screen rect offline (measured 2026-08-19)

Everything below is arithmetic over the `.layout` alone: no game, no
resolution-specific asset, no runtime. It is what lets a tool say "BtnOk is at
(850.56, 812.16) 218.88x60.48 at 1920x1080" and then point at that spot in a
screenshot.

Walk the tree depth-first carrying the parent's absolute box `(px, py, pw, ph)`;
the root's parent box is the screen. For each widget:

```
s = screen_height / 1080                     # exact units, `rules-and-checklist.md` rule 3
w = size_x * s           if hexactsize == 1   else size_x * pw
h = size_y * s           if vexactsize == 1   else size_y * ph
x = px + position_x * s  if hexactpos  == 1   else px + position_x * pw
y = py + position_y * s  if vexactpos  == 1   else py + position_y * ph
```

`halign center_ref` centres the widget and its `position_x` is then applied on
top: `x = px + (pw - w) / 2 + position_term`, where `position_term` is the same
exact-or-fraction expression as the general case above. `valign center_ref`
does the same vertically. An absent `position` behaves as `0 0`.

*(corrected 2026-10-03)* The exact branches used the declared value as pixels
(`w = size_x if hexactsize == 1`), which holds only on a 1080-pixel-tall screen.
The 1920x1080 calibration below is unaffected (`s = 1`); the 1280x720 table it
mentions was computed by hand with the same formula, not read from the engine.
`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py:772-775` still uses the pixel form.

**Corrected 2026-08-19.** This paragraph used to say `position_x` is *ignored*
under `center_ref`. The engine adds it. Measured on the live HUD: `Zeroing`
declares `halign center_ref` with `hexactpos 0` and a `position` of `0.06`, and
is drawn with its centre **+103.7px** from its parent's centre — exactly
`0.06 × 1728`, its parent's width. Its mirror `WeaponMode` declares `-0.06` and
lands at **−103.7**. The two rules agree whenever `position` is `0 0`, which is
the common case in vanilla layouts, and that is why the wrong one survived a
calibration.

**Calibration, not belief.** Predicted values matched a live `ui_tree` capture
on 6 nodes across 3 nesting depths with a maximum delta of **3e-5**
(`MCPDialogPanel` predicted 595.20/162.00/729.60/756.00 vs engine
595.2000122070312/162.0/729.5999755859375/756.0), and again in-flight on 5
buttons at 1920x1080. The same arithmetic reproduced a hand-computed table at
1280x720 exactly.

### The exception that makes the rule useless if you skip it

A child of a widget from the **spacer family** declares a box the parent then
recomputes, so its `position`/`size` in the file carry no information. The
family, verified in the engine proto:
`SpacerBaseWidget` (`P:\scripts\1_core\proto\enwidgets.c:460`), `SpacerWidget` (`:465`),
`GridSpacerWidget` (`:473`), `WrapSpacerWidget` (`:477`) and `ScrollWidget`
(`:481`). Corpus usage (this 819-file 2026-08-19 sweep, not the 459-file
2026-05-13 table in `layout-empirical-corpus.md` section 1): GridSpacer 1414,
WrapSpacer 600, Spacer 17.

Ignoring this produces confident nonsense: a geometry check that flagged
"clickable widget with a zero box" fired 15 times across 4 shipped Expansion
layouts (`option_accept_button`, `option_promote_button`, and so on, all `size 0.0 1.0`)
and every single one was a `ButtonWidget` under a `GridSpacerWidget`, i.e. a
normal authoring idiom, not a defect.

### Spacers, measured in game (SimpleGroup, 2026-09-28)

- **`WrapSpacerWidgetClass` + `"Size To Content V" 1` stacks children of mixed
  heights and grows with them.** A window holding frames, a 3-unit panel, text
  and a nested `GridSpacerWidgetClass` list (`Columns 1`, `Rows 100`) ended
  right after its last child with 4, 6 and 20 rows. Vanilla stacks its
  pause-menu buttons the same way (`P:\gui\layouts\day_z_ingamemenu.layout:99-120`, `bottom`).
- **Attribute keys are case-sensitive, and an unknown key is ignored without a
  word.** A `GridSpacerWidgetClass` declaring `columns 1` / `rows 0` laid its
  rows out side by side; in the same frame, a list declaring `Columns 1` /
  `Rows 100` stacked them. Not isolated: the `rows` value differs too. Vanilla
  spells them `Columns` / `Rows` (1060 `Columns`, `layout-empirical-corpus.md`
  section 2); a gate comparing every attribute key with its spelling in the vanilla
  corpus caught it.

## Which widget classes actually carry which text attribute (819 layouts, 2026-08-19)

Guessing this from one example is how you invent an API. Measured distribution
over the whole corpus (vanilla + third-party + ours):

| Attribute | Where it actually appears |
|---|---|
| `wrap` (604) | MultilineTextWidget 355, RichTextWidget 236, HtmlWidget 9, TextWidget 4 |
| `text_proportion` (1048) | TextWidget 679, ButtonWidget 361, RichTextWidget 5, MultilineTextWidget 3 |
| `"exact text"` (2888) | TextWidget 2135, MultilineTextWidget 352, RichTextWidget 292, EditBox 87, HtmlWidget 13, MultilineEditBox 5 |

Do not collapse these with `layout-empirical-corpus.md` section 2 (2026-05-13, 300
layouts): that sample lists `text_proportion` 437 and `wrap` 505. Same
attributes, smaller population — settled 2026-08-19 by re-counting the full
corpus with two independent instruments, which agree that `wrap` hosts are text
widgets and that **no spacer widget carries it**; section 2's "WrapSpacer wrap mode"
label was wrong and is corrected there. Restricting the new census to the `gui\`
subtree reproduces section 2's 505.

Totals move by about 1% between instruments (`text_proportion` 1048–1055,
`wrap` 604–616) because the population differs by a file or two and the rare
hosts are attributed differently. **The hosts are what this table is for, and
they reproduce exactly**: `text_proportion` is above all a TextWidget attribute
(679), not a button one, and `wrap` does occur on RichTextWidget (236) and on
TextWidget (4).

Two consequences worth holding on to:

- **`text_proportion` sizes the text as a fraction of the widget's height.** It
  does not make a long single-line string fit horizontally. Nothing does: the
  only ways out are wrapping onto more lines (needs Multiline/RichText) or
  capping the string length before it reaches the widget.
- Vanilla's own dialog text is a `RichTextWidgetClass` combining
  `"exact text" 1` + `"exact text size" 20` + `"size to text h" 1` +
  `"size to text v" 1` + `wrap 1` + `clipchildren 1`
  (`P:\gui\layouts\dialog.layout:95-113`). That is the canonical "text that fits"
  recipe; copy it whole rather than cherry-picking one attribute.
