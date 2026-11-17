# Verifying a UI: what automated checks, probes and test harnesses can and cannot prove

What a passing automated UI check does not tell you, how two layouts with the same widget names make one of them unreachable, why resizing the game window does not test another resolution, and the traps in the probes and harnesses used to check a UI on a running client.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). Everything described as measured was measured in game by the source author on DayZ 1.29.163709, mostly on the LFPowerGrid mod (his own); none of it is yet repeated here. The verbs `ui_tree`, `ui_click`, `ui_set_text`, `ui_reload_layout`, `capture_screenshot`, `camera_get` and `logs_since` belong to the DayZ MCP bridge, a third party test harness described in `skills/dayz-mcp-verify/` and `skills/dayz-test-ingame/`; facts about them are harness facts, not game facts. The measurement logs, captures and probe layouts stay with the source author; dates and run labels are kept so a result can be traced.

---

## Contents

- [A passing automated check says nothing about how the UI looks](#a-passing-automated-check-says-nothing-about-how-the-ui-looks)
- [Which offline tool answers which question](#which-offline-tool-answers-which-question)
- [What the HTML viewer models and what it does not](#what-the-html-viewer-models-and-what-it-does-not)
- [Clicks on ScriptViews cannot be automated through the MCP bridge](#clicks-on-scriptviews-cannot-be-automated-through-the-mcp-bridge)
- [Two layouts with the same names](#two-layouts-with-the-same-names)
- [Fixing a name collision: renaming the root is enough](#fixing-a-name-collision-renaming-the-root-is-enough)
- [Resizing the window does not test another resolution](#resizing-the-window-does-not-test-another-resolution)
- [A host helper that is not DPI aware lies, and the check passes anyway](#a-host-helper-that-is-not-dpi-aware-lies-and-the-check-passes-anyway)
- [ESC does not close while an EditBox has focus](#esc-does-not-close-while-an-editbox-has-focus)
- [A file based probe needs a freshness mark](#a-file-based-probe-needs-a-freshness-mark)
- [Procedural texture: fails from script, silent from a layout](#procedural-texture-fails-from-script-silent-from-a-layout)
- [What the UI verbs return](#what-the-ui-verbs-return)
- [ui_reload_layout: the full contract](#ui_reload_layout-the-full-contract)
- [Test a scoping mechanism with a case that can fail](#test-a-scoping-mechanism-with-a-case-that-can-fail)
- [Preview and resize rules from the sorter panel session](#preview-and-resize-rules-from-the-sorter-panel-session)
- [Log marker trap](#log-marker-trap)
- [A black frame may not come from the game](#a-black-frame-may-not-come-from-the-game)
- [Questions still open](#questions-still-open)

## A passing automated check says nothing about how the UI looks

Measured 2026-08-19. A full acceptance run of a modal dialog passed 11 API cases and then 10 of 10 cases driven by real mouse clicks: correct end states, values in the declared order, unicode kept intact, no overlapping buttons, and widget rects that matched the offline prediction to the decimal. While all of that was green, a person looking at the screen found three defects in under a minute:

1. The panel background was not drawn at all (white text over the game world), because the style name was valid for a different widget type.
2. A 29 character title was clipped on both sides.
3. Most buttons needed two clicks; the first seemed to be spent on gaining focus.

None of the three can be reached from the automation path, and that is by design, not by accident:

- **`ui_tree` returns the color, and the color was correct.** What failed was the drawing, and no verb reads pixels.
- **The harness cannot read text.** The bridge fills `text` only for `EditBoxWidget`, `MultilineEditBoxWidget` and `ButtonWidget`; a `TextWidget`, `MultilineTextWidget` or `RichTextWidget` is reported with `text_readable=false` and an empty string. That follows the engine: `class TextWidget` (`P:\scripts\1_core\proto\enwidgets.c:189`) declares no text getter, and the only `GetText` declarations in that file are on `MultilineEditBoxWidget` (`:318`), `EditBoxWidget` (`:349`) and `ButtonWidget` (`:389`). A clipped title is invisible to every check you can write.
- **`ui_click` is not a click.** It finds the handler through `GetScript` or `GetUserData` and calls `OnClick(target, 0, 0, mouseButton)` with the coordinates fixed at zero. It skips hit testing, draw order and `IGNOREPOINTER` (`P:\scripts\1_core\proto\enwidgets.c:78`) by construction.

**Working rule.** For any UI deliverable, a passing automated check closes the **contract** (names, bindings, states) and nothing else. Drawing and interaction need a person, or a screenshot that a person inspects (or a vision model that is asked for a measurement, not a verdict). Make the screenshot mandatory evidence in the acceptance steps, not an optional extra.

**When a person is the instrument, the text on the test screen is part of the instrument.** A test dialog said (in Spanish) "'no' must not come out", meaning the returned `choice` value. The tester read it as "the No button should not be there" and reported a bug. Text shown to the tester says what to **do**, never what the expected result is.

## Which offline tool answers which question

Two different questions need two different readers of a `.layout` file, and neither does the other's job:

| Question | Tool |
|---|---|
| **What** does the widget say (text, color, image, any key)? | `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` |
| **Where** is the widget (rect, click center, whether it can be reached)? | A geometry parser. The source author used `layout_ast.py` and `ui_rects.py` from his separate tooling repo, which is **not** part of this repo. Here, `/dayz-layout-preview` draws the rects, and the running game is the reference. |

- `parse.py` collapses an inline `position` into its own format; do not use it for geometry.
- An older parser, `renderer/parse.py` from the source author's research folder, silently strips `\` from Windows paths. It was replaced by the UI lab tool under `scripts/tools/dayz-ui-lab/`; do not bring it back.
- `ui_rects.py predict` does not model layouts made only of exact flag widgets (its own header says so). For those, the source author parsed the layout into a flat list with parent and child links and typed attributes, and checked containment, nesting, draw order and `visible 0` by adding up the ancestors' offsets.
- The offline check for the starting layouts in `<skill-dir>\templates\` is `parse.py --check`. A script named `ui_rect_lint.py` that older notes mention is not part of this repo.

## What the HTML viewer models and what it does not

`python scripts/tools/dayz-layout-viewer/build_viewer.py <layout>` writes a self contained `.preview.html` with viewport switches for 1080p, 1440p, 21:9 and 720p. Read out of its code by the source author on 2026-08-20 (line numbers are in `scripts/tools/dayz-layout-viewer/dayz_layout_viewer/html_template.py` as he read it; open the file again before relying on a line):

- It **does** model text layout: font size from `text_proportion` (`:110-112`), wrapping (`:116`), `text halign` and `text valign` (`:104-105`, `:115`), and it clips with `overflow:hidden` (`:117`).
- It **cannot** tell you whether **your string** fits, for two reasons. The font is a browser substitute (Bahnschrift, Roboto Condensed or Arial Narrow, `:73`) where the engine uses the Metron bitmap atlases, so glyph widths differ. And a `#STR_` key is drawn as the bracketed key, not the translated sentence (`:107`): run on vanilla's `dialog_input_text.layout`, it shows `#STR_TextInputDialogRoot_MessageText0`. Since production text is always `#STR_` keys, that is the normal case.
- **It lays exact units out as pixels at every viewport** (`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py:772-775`), while the engine scales them with the screen height (rule 3 in `rules-and-checklist.md`). At any viewport other than 1080p it misplaces exact widgets and everything inside them. Trust those views only for widgets with no exact ancestor. Corrected on 2026-10-03: this step used to say the viewports let you "see exact flag breakage without a build".
- `wrap` defaults to **1** in the preview (`:116`), so a widget that never declared `wrap` still wraps there. The game does not wrap a `TextWidget` (`text-sizing-and-rendering.md`), so the preview shows two lines where the game clips one.

So: trust it for **where a box is and whether text of that size would overflow it**; never for whether the shipped string fits. That question needs a build. Two older copies of the source skill disagreed here ("structure and anchoring only" against "trust it for text"); neither was right.

## Clicks on ScriptViews cannot be automated through the MCP bridge

Measured 2026-08-29 with a healthy bridge (version 10 on both sides, `bridge_status ready=true`) on the LFPowerGrid sorter panel, which is a Dabs `ScriptView` and not a `UIScriptedMenu`:

- `ui_tree` with an empty `path` returns `no_menu`. The walker looks for the active scripted menu, and a `ScriptView` is not one. There is no widget tree to inspect by that route.
- `ui_click` returns `not_handled` on buttons that exist and are visible on screen. Why a generic handler search misses a Dabs view is explained in `dabs-framework.md` ("Click dispatch and external automation").

**The control that makes the second result conclusive, and that you must always repeat.** `not_handled` on a button that has a permission guard is ambiguous: the harness may not be reaching the handler, or the controller may be rejecting the action as designed. Those are opposite conclusions. Tell them apart by also clicking a widget that has **no** guard. Here the close button (`BtnCloseX`), always allowed and independent of power or link state, also returned `not_handled`, and a later capture showed the panel still open: the click did nothing. Without that second click the result could have been recorded as "verified, the guard rejects it", which would have been false.

What this means when you plan a test cycle:

- Take widget names from the `.layout` (`ButtonWidgetClass <Name>`), not from a live tree.
- Any check that depends on clicking, typing into an EditBox, switching tabs or closing with ESC belongs to a person with a real mouse.
- A verb that ships inside the deployed bridge PBO is not necessarily callable: the tool registry of the bridge's daemon is fixed when it starts, so `key_press` and `player_respawn` were in the version 10 PBO and did not exist as tools. And a verb that is callable does not necessarily reach the handler.

## Two layouts with the same names

Measured 2026-09-04, with the LFPowerGrid sorter's test variant and its production layout loaded at once. This is the most expensive structural mistake and the easiest to make: copy a `.layout` to make a test or debug variant and leave the widget names as they were.

```
LFPG_Sorter.layout            185 widgets
test/LFPG_Sorter_TEST.layout  213 widgets
names in both                 124    (SorterRoot, SorterPanel, HeaderFrame, BtnCloseX,
                                      BtnSave, every CatBtnN, every Edit* ...)
only in the test layout        89    (Builder*, CatchAllRow*, BtnPreview*)
```

A third layout of the same mod (a different screen) also had a `BtnCloseX`.

Measured consequences:

- `FindAnyWidget("SorterPanel")` (`P:\scripts\1_core\proto\enwidgets.c:169`) and the bridge's name resolver **cannot tell the two apart**. The earlier symptom was a `ui_click` that returned `not_handled`: it had silently resolved to the production widget, whose `OnClick` handles nothing because its view is not open.
- **Scoping by an ancestor does not always save you.** The chain of the test layout's `BtnCloseX` is `SorterRoot`, `SorterPanel`, `HeaderFrame`, `BtnCloseX`, and all three ancestors collide too. No ancestor is unique, so the button cannot be reached by name at all.
- **The other root only has to exist, not be open.** Creating a view once at mission init and hiding it (rule 9 in `rules-and-checklist.md`) keeps the production root alive for the whole session. The ambiguity is permanent.

**Rule.** Widget names are an API contract (the spec table in `plan-to-implementation.md`). A test or debug variant **prefixes all its names** (`TEST_`, `Dbg_`), or it cannot be addressed. In LFPowerGrid the 89 names found only in the test layout were the only ones that worked; of the 124 shared ones, none did.

**A cheap offline check.** Before approving a layout variant, count the names both files share:

```python
import re, io
def names(p):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    return set(re.findall(r'^\s*\w+WidgetClass\s+(\w+)\s*\{', s, re.M))
print(sorted(names(PROD) & names(TEST)))   # must be empty
```

### The A/B test that shows when the collision appears

Measured 2026-09-05. Same call, same session; the only change between the two rows is opening the variant panel:

| State | `ui_tree(root:"SorterRoot", path:"BtnCloseX")` |
|---|---|
| Variant closed | Resolves to **production**: 26x26 at x=688, `visible_hierarchy: 0`, `SorterRoot@0` |
| Variant open | **`ambiguous_path`** |

1. The production root **always exists** (created once and hidden), even when its screen was never opened. The variant's root is created when the variant opens.
2. So the collision is not occasional: as soon as the variant opens, **every** shared name, the root included, stops resolving.
3. `visible_hierarchy: 0` together with `visible: 1` is the mark of a root that was created and hidden. It tells you which of the two the resolver gave you.

## Fixing a name collision: renaming the root is enough

Measured 2026-09-04. Before you prefix 227 widgets, check whether **one** is enough. The bridge's resolver contract, as its source states it:

> `root` names a widget that must be unique in the whole workspace; `path` is then a name resolved inside that scope. Without `root`, `path` is resolved over the whole workspace, ScriptView roots included: 0 matches is `widget_not_found`, 2 or more is `ambiguous_path`, and the first widget with that name is never chosen.

The resolver counts matches **under the scope**. So when the variant's root is unique, its whole tree can be addressed again (`ui_tree`, `ui_click` and `ui_set_text` with `root: "TEST_SorterRoot"`), even though the other names still collide.

In LFPowerGrid that was **one line**: `FrameWidgetClass SorterRoot` became `TEST_SorterRoot` in the test layout. Checked before touching anything: `SorterRoot` appeared exactly twice in the whole mod (the production declaration and the test one), with no string literal in any `.c` file, no `Binding_Name` and no member field. Five more bytes, the same brace balance, and the production file unchanged byte for byte.

**Why check that first.** Prefixing everything looks like the obvious fix and is the expensive one. A Dabs MVC view has **three naming systems that overlap**, and renaming widgets touches all three:

| System | Count in that mod | Renaming the widget breaks it when |
|---|---|---|
| Widget name in the `.layout` | 227 | (this is the goal) |
| Member field filled by `LoadWidgetsAsVariables` (member `X` matches widget `X`) | 139 | You do not rename the member too |
| `Binding_Name` of a `ViewBinding` | 15 | You rename the member (it points at the controller **property**, not at the widget) |

The last two pull in opposite directions: renaming the members repairs the automatic binding and breaks `Binding_Name`; leaving them kills the automatic binding. It can be solved (in that mod 122 members had a manual `FindAnyWidget`, 11 were found by walking a button's children or by a name built as `btnName + "Bg"` that follows the rename by itself, and only 6 were exposed), but the failure is a **silent null**, and the only real check is another in game session after a PBO rebuild.

**Rule.** When you meet `ambiguous_path`, the first question is not "how do I rename everything?" but **"is there an ancestor I can make unique?"** When there is, the fix is one line and can be verified offline. A full prefix is still right for a **new** layout, where it costs nothing; on a live MVC layout it is a refactor with its own test cycle.

**Mind where the `.layout` is read from.** The game reads it **from the PBO**. Only `$profile:` is read from disk again on each load (`hot-iteration.md`). A rename in the source folder is not live until the next build; until then the client still sees the old name.

**Checks that close a root rename, all offline:**

1. Search the name in the **whole** mod (`.layout`, `.c` and `config.cpp`) and count the hits.
2. Is it a `Binding_Name`? Is it a member field? When it is neither, the change is one line.
3. After the edit: the layout parses, the root and widget counts are the same as before, the brace balance is the same, and the production file is unchanged byte for byte.
4. The new name is declared once and does not appear in the production layout.

## Resizing the window does not test another resolution

Measured 2026-09-04. This rules out the method that looks obvious for the most common UI complaint ("it looks different at another resolution").

DayZDiag keeps the render resolution it was given with `-x` and `-y` on the command line and **scales the finished picture** to the window. **It does not lay the UI out again.** Measured with the same probe before and after the window's client area was changed to 1280x720 from the host:

| Panel field | Window 1920x1080 | Window 1280x720 | Ratio |
|---|---|---|---|
| `size_w` | 820 | 546.667 | 2/3 |
| `size_h` | 600 | 400 | 2/3 |
| `pos_x` | 550 | 366.667 | 2/3 |
| `pos_y` | 240 | 160 | 2/3 |

Everything changed by the same factor, 1280/1920. The clear mark: a widget declared with an exact size of 1 reported `screen_w = 0.6666666865`. Had the engine laid the UI out again, an exact size of 1 would still be 1.

Two consequences that cost time when missed:

- To test another resolution, **start the client again with different `-x` and `-y`**. The window offers no shortcut.
- **No scaling code in the mod does not prove there is no scaling.** In this case it had been correctly established that the view contains no `UIScaler` or `ScaleWidget`, and from that it was wrongly concluded that the numbers would come out unscaled. The engine does the scaling; no search of the mod can see it. When a prediction rests on "there is no scaler", the check is a measurement in game, not a text search.

## A host helper that is not DPI aware lies, and the check passes anyway

Measured 2026-09-04. With Windows display scaling at 150%, a process that is not DPI aware gets **virtualized** coordinates:

```
GetWindowRect  -> 1295 x 757     real 1943 x 1136
GetClientRect  -> 1280 x 720     real 1921 x 1080
position       -> (1080, 56)     real (1620, 84)
```

The danger is not the reading but the **check**. A window resize to "1280x720" was requested (in logical units that is 1920x1080 physical, so no change), and the check `client_rect == requested` compared logical with logical and **passed without anything having moved**. A check that compares two values from the wrong space detects nothing.

**Rule.** A helper that measures or moves the game window first calls `ctypes.windll.shcore.SetProcessDpiAwareness(2)` (falling back to `user32.SetProcessDPIAware()`). A cheap cross check: the bridge's `capture_screenshot` returns `window.rect` **and** `client_surface.rect_window` in physical pixels. When your helper does not match them, your helper is the one that is wrong.

## ESC does not close while an EditBox has focus

Measured 2026-09-04. The ESC handler of the LFPowerGrid sorter view, read in its source:

```c
Widget focused = GetFocus();
if (focused)
{
    EditBoxWidget editCheck = EditBoxWidget.Cast(focused);
    if (editCheck)
    {
        SetFocus(null);   // uses up the ESC and does NOT close
        return true;
    }
}
DoClose();
```

`GetFocus()` and `SetFocus(Widget w)` are the vanilla globals at `P:\scripts\1_core\proto\enwidgets.c:702` and `:698`. The code's own comment calls it "double ESC: the first clears the EditBox focus, the second closes the panel". It is a sound pattern for the player. The problem is the observer effect: **when the harness's command hook is an invisible `EditBoxWidget`** (the usual way to send commands without a keyboard) and some call leaves it focused, the first ESC goes to it and the panel does not close. The probe changes what it measures.

What to do: make the hook a widget that cannot hold focus (`ignorepointer 1` is not enough: it must not be focused), or call `SetFocus(null)` after typing into it, or test closing with the real button and not with ESC.

## A file based probe needs a freshness mark

Measured 2026-09-04. The sorter's test hook answers by writing a JSON file into the profile folder. The JSON carries state (`open`, `powered`, `paired`, `status`, `rule_count`) but **no freshness mark**: no timestamp, no sequence number, no echo of the command with an id.

With the panel **closed**, sending a `dump` command leaves the file **byte identical** (same modified time, same hash), because the view's polling does not run while it is closed. A naive consumer reads the file, sees `"open": true` from the **previous** dump and concludes the panel is still open. The opposite of the truth.

**Rules for any UI probe that answers through a file:**

- The consumer compares the **modified time and hash before and after** each command. No change means the command was not processed, and the content is not an answer.
- Better: the probe writes a `seq` value or echoes the command it received, so freshness lives **inside** the file and does not depend on the filesystem.
- Do not write a check that asks the probe for a value it **cannot emit**. A dump with `"open": false` is impossible when closing the view stops the polling. Before you set the expected value, ask whether the instrument is still alive in that state.

## Procedural texture: fails from script, silent from a layout

Measured 2026-09-04 and narrowed on 2026-09-05, DayZ 1.29.163709. Rule 2 in `rules-and-checklist.md` carried this warning with an older date; it was confirmed again in the client RPT, four or five times per boot:

```
RESOURCES (E): Bad texture name '#(argb,8,8,3)color(1,1,1,1,CO)'
GUI       (E): ImageWidget::LoadImageFile can't load '#(argb,8,8,3)color(1,1,1,1,CO)'
```

It is not a harmless warning: the `ImageWidget` is left without a texture. The fallbacks stay the same: a 1x1 white `.edds`, or a `Colorable` style with a `WhitePixel` center (`styles-format.md`).

The same string, same build, same RPT, by two routes:

- From **script** (`ImageWidget.LoadImageFile`): 5 `Bad texture name` lines and 4 `LoadImageFile can't load` lines, all while the mod starts.
- From a **layout** (`image0` on an `ImageWidgetClass`): **no new lines** in the RPT. The log was flowing at the time: the client script log grew, including the `ok=0` of a `layout_not_found` that was triggered on purpose.

**The limit you must not skip:** this shows the layout route **logs no error**, not that the texture is drawn. Telling "loads fine" from "fails silently" needs someone to look at pixels, and that half was not done. Do not count it as a proven fallback.

## What the UI verbs return

Measured 2026-09-04; a contract change from what the source author's August notes described. `ui_set_text` and `ui_click` now return:

```json
"ui_request": {
  "requested_path": "BuilderTabCategory",
  "requested_root": "",
  "requested_text": "",
  "matched_path": "/@0/SorterRoot@1/SorterPanel@0/BuilderFrame@0/BuilderTabCategory@0"
}
```

- Evidence no longer has to be written down by hand.
- **`matched_path` shows the resolver's decision**, which is exactly what you need to diagnose a name collision. The `@N` on each segment is the index among siblings: `SorterRoot@1` tells you there are at least two.
- When a name is ambiguous the resolver **no longer guesses**: it returns `ambiguous_path` where it used to resolve silently. A silent bug became a readable error, but a plain name in `path` stops working as soon as a second widget with that name exists.

## ui_reload_layout: the full contract

Measured 2026-09-05 without repacking the mod: every probe layout was loaded from `$profile:`, which is what makes hot reload useful (`hot-iteration.md`).

**Correction: `ui_reload_layout` replaces; it does not stack.** The source skill used to say, in its entry for `hot-iteration.md`, that "a second load stacks instead of replacing". Measured, for this verb, it does not:

```
ui_reload_layout($profile:uiprobe.layout, reload)   twice
ui_tree(path="ProbeMarker")
  -> ONE node, matched_path "/@0/ProbeRoot@0/ProbeMarker@0"
  -> no ambiguous_path
```

Had it stacked, there would be two `ProbeMarker` widgets and the resolver would have returned `ambiguous_path`, which is what it returns when there really are two (next section). The most likely reading of the older warning: it described a manual `CreateWidgets`, which does leave the previous root in place. The `ui_reload_layout` verb unlinks before it loads. Keep the two apart: stacking is a risk of the manual path, not of this verb.

| Call | Measured result |
|---|---|
| `reload` with `$profile:<file>.layout` | Loads from disk **with no PBO**; returns the engine's rects for the whole tree |
| `reload` twice | **Replaces** (one tree) |
| `close` | `ui.nodes: []`, and afterwards the widget is `widget_not_found`: it really unlinks |
| `reload` with a file that does not exist | `layout_not_found`, and **the client stays alive** |

Three facts from the same probe:

- The preview root reports `screen_w` and `screen_h` of 1920x1080: the engine's viewport, not the size of the system window (see the two sections on window size above).
- **A child's position is relative to its parent.** A child with `position 110 110` inside a parent at `position 100 100` reports `screen_x` and `screen_y` of 210 and 210. Easy to forget when reading a `matched_path`.
- A `TextWidget` again reported `text: ""` and `text_readable: 0`. It has no getter, and the harness does not invent a label.

## Test a scoping mechanism with a case that can fail

Measured 2026-09-05. Before you trust that scoping by `root` solves a name collision, **test it with a case where you can tell success from luck**. The probe: two sibling subtrees, each with a child of the same name and **different sizes**. The size is what turns "it picked one" into "it picked the right one" (a count is not an identity).

```
ScopeProbeRoot
├── ScopeAlpha  └── SharedChild   50x50  at (210,210)    green
└── ScopeBeta   └── SharedChild   70x70  at (1210,210)   red
```

| Call | Result |
|---|---|
| `path:"SharedChild"` with no root | `ambiguous_path` |
| `root:"ScopeAlpha", path:"SharedChild"` | **50x50 at (210,210)**, `.../ScopeAlpha@0/SharedChild@0` |
| `root:"ScopeBeta", path:"SharedChild"` | **70x70 at (1210,210)**, `.../ScopeBeta@0/SharedChild@0` |

The mechanism works and picks correctly. That confirms the fix above: **a unique root makes its whole tree addressable again**, even when its children share names with another tree.

## Preview and resize rules from the sorter panel session

Measured 2026-08-29 on a `$profile:` preview of the LFPowerGrid sorter (an 820x600 layout, 250 widgets, at 1920x1080 and 1280x720). The rules from that session about text and color are in `text-sizing-and-rendering.md`; these are the ones about verification:

- **Resizing the window from the host is not safe everywhere.** It killed one client at 1942x1136 (the process died, with no script crash) and worked on another at 846x461. The safe way to sweep resolutions is to start the client again with a width and height, and to **check the viewport in the tree**: a request for 1280x720 gave exactly 1280x720 that time, while an earlier run got 846x461 from the same request. The mapping is not stable.
- **A `$profile:` preview is drawing with no menu behind it.** Clicking the window gives focus to the game and the camera **captures the mouse** (the cursor disappears and no further click arrives). ESC, which opens the vanilla menu, gives it back. No click on a preview widget works; test interaction on the real panel.
- **Geometry of a layout made only of exact flag widgets** is not modelled by the rect predictor; see "Which offline tool answers which question" above.

## Log marker trap

Measured 2026-09-04. Calling `logs_since(max_lines=1)` to "mark now" returns a marker whose offset falls at the **start** of the file when the log is under the 256 KiB cap. A check that assumes "nothing before marker M0 is startup noise" then swallows the whole startup. DayZ logs are already one per run (the file name carries the launch date), so to count a pattern, **count over the run's files and date each hit**; do not trust the offset.

Related: the mod's probe writes to `script_<date>.log`, **not** to the `.RPT`. A control that searches only the RPT finds nothing and makes it look as if the probe never ran.

## A black frame may not come from the game

Measured 2026-09-05. `capture_screenshot` returned `frame_client_all_black` three times in a row while the client was **perfectly healthy**: `camera_get` returned `player_camera_active` with a real position and direction, and the window was visible, not minimized, inside its rect and in the foreground. The time of day in the world was ruled out (setting it to 12:00 changed nothing). Most likely cause: the monitor was off or the Windows session was locked; it was the middle of the night.

**Rule.** Before you diagnose the game from a black frame, use a client verb that does **not** depend on pixels (`camera_get` works) to check that the client is alive and rendering. When it is, the problem is on the host, not in the mod. Treat every question that only pixels can answer as lost for that session.

## Questions still open

The probes for these were set up and their frames never read (no pixels that night):

- **Is a procedural texture declared in a layout drawn?** See the limit stated under "Procedural texture" above.
- **Does a `TextWidget` with no `wrap` attribute wrap?** The frames of 2026-08-22 answered it for `wrap 1` and `wrap 0` (neither wraps; `text-sizing-and-rendering.md`); the row with no attribute was not read. The probe layout offers three rows with the same long text (no `wrap`, `wrap 1`, `wrap 0`) plus a `MultilineTextWidget` to compare. The rects cannot answer: a widget reports its declared size whether its text wraps or overflows. **The eye decides.**

To pick them up again, a display that is switched on is enough: load the probe layout from `$profile:` and capture a frame.
