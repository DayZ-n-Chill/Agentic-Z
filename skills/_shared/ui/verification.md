# Verifying a UI

What a passing automated check proves about a UI and what only a look at the screen can, which offline tool answers which question, how to test another resolution, and the traps in host helpers, logs and black frames. Name collisions are in `widget-name-collisions.md`; the in game test bridge is in `ui-test-bridge.md`.

Facts in this file were measured in game on 1.29 unless a line cites `P:\`.

## A passing check proves the contract, not the picture

A modal dialog passed every automated case, 11 through the API and 10 through real mouse clicks: correct end states, values in order, unicode intact, no overlapping buttons, and rects that matched the offline prediction to the decimal. A person looking at the screen then found three defects in under a minute:

1. The panel background was not drawn at all, because its style name belonged to another widget type (`styles-format.md`).
2. A 29 character title was clipped on both sides.
3. Most buttons needed two clicks; the first went to gaining focus.

No automated check can reach those three:

- A widget tree reports the declared color, which was right; what failed was the drawing, and nothing reads pixels.
- A `TextWidget` cannot give its text back: `class TextWidget` (`P:\scripts\1_core\proto\enwidgets.c:189`) has no getter, and the only `GetText` calls are on `MultilineEditBoxWidget` (`:318`), `EditBoxWidget` (`:349`) and `ButtonWidget` (`:389`). A clipped title is invisible to any check you can write.
- A scripted click calls the handler directly. It skips hit testing, draw order and `IGNOREPOINTER` (`:78`).

So a passing check closes the contract (names, bindings, states) and nothing else. Drawing and interaction need a person, or a screenshot a person inspects, or a vision model asked for a measurement rather than a verdict. Make the screenshot required evidence.

Text on a test screen tells the tester what to do, never what the result should be. A test dialog that said "'no' must not come out", meaning the returned value, was read as "the No button should not be there" and reported as a bug.

## Which offline tool answers which question

| Question | Tool |
|---|---|
| What does the widget say: text, color, image, any key | `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` |
| Is the starting layout sound | `parse.py --check` (the templates in `templates/`) |
| Where is the widget: rect, click point, reachable or not | `/dayz-layout-preview`; the running game is the reference |
| Do names and `#STR_` keys match the scripts and stringtable | `ui_reconcile.py` (`plan-to-implementation.md`) |

- `parse.py` collapses an inline `position` into its own format; do not use it for geometry.
- A layout reader must keep the `\` in Windows paths; one that strips it corrupts every image and font path. The UI lab tool keeps it.
- A rect predictor built on fractions of the parent does not model layouts made only of exact widgets. For those, read the layout into a flat list with parent links and check containment, nesting, draw order and `visible 0` by adding up the ancestors' offsets.

## What the HTML viewer can and cannot show

`python scripts/tools/dayz-layout-viewer/build_viewer.py <layout>` writes a `.preview.html` with views for 1080p, 1440p, 21:9 and 720p (`layout-html-preview.md`). From its code in `scripts/tools/dayz-layout-viewer/dayz_layout_viewer/html_template.py`:

- It models text layout: size from `text_proportion` (`:110` to `:112`), wrapping (`:116`), `text halign` and `text valign` (`:104`, `:105`, `:115`), and clipping (`:117`).
- It cannot tell whether your string fits. Its font is a browser stand in (Bahnschrift, Roboto Condensed or Arial Narrow, `:73`) where the game uses Metron atlases, and a `#STR_` key is drawn as the bracketed key, not the translation (`:107`): vanilla's `dialog_input_text.layout` shows `#STR_TextInputDialogRoot_MessageText0` (`P:\gui\layouts\dialog_input_text.layout:116`). Shipped text is always keys.
- It lays exact units out as pixels at every view (`scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py:772` to `:775`), while the engine scales them with the screen height (`checklist-and-troubleshooting.md`, "Declare all four unit flags"). Trust a view other than 1080p only for widgets with no exact ancestor.
- It defaults `wrap` to 1 (`:116`), so it wraps text the game clips on one line.

Trust it for where a box is and whether text of that size would overflow it, never for whether the shipped string fits.

## Testing another resolution

The diag client keeps the render resolution of its `-x` and `-y` arguments and scales the finished picture to the window; it does not lay the UI out again. With the window changed from 1920x1080 to 1280x720, every field of a panel shrank by exactly 2/3, and a widget with an exact size of 1 reported a width of 0.667. Had the UI been laid out again it would still be 1.

- Start the client again with other `-x` and `-y` values to test a resolution; resizing the window proves nothing. Read the viewport in the widget tree to confirm what you got: the same request has given 1280x720 one time and 846x461 another.
- Resizing the window from the host is not safe: it killed one client at 1942x1136 with no script error.
- No scaling code in the mod does not mean no scaling. The engine scales; a search of the mod cannot see it, so check a prediction that rests on "there is no scaler" in game.

## Host helpers and DPI

With Windows display scaling at 150%, a helper that is not DPI aware gets virtual coordinates: `GetClientRect` gave 1280x720 for a real 1921x1080. A resize request checked in the same wrong space then passed with nothing moved. A helper that measures or moves the game window first calls `ctypes.windll.shcore.SetProcessDpiAwareness(2)`, falling back to `user32.SetProcessDPIAware()`. If its numbers disagree with what the game reports in physical pixels, the helper is wrong.

## Logs and frames

- The test mod's own log lines go to `script_<date>.log`, not to the `.RPT`; a check that searches only the RPT finds nothing. DayZ writes one log file per run, so count a pattern over the run's files, not from an offset inside one file.
- A black capture does not mean the game is broken. Check first with a call that does not depend on pixels, such as the camera state; if the client is alive and rendering, the cause is on the host (a monitor that is off or a locked session), and every question only pixels can answer is lost for that session.
- After every session, search the RPT for `Cannot open layout`.

## Still open

- Whether a procedural texture string set as `image0` in a layout draws. From script it fails with "Bad texture name" (`widget-classes.md`); from a layout it logs nothing, which is not the same as drawing.
- Whether a `TextWidget` with no `wrap` attribute at all wraps; `wrap 1` and `wrap 0` both clip (`text-sizing-and-rendering.md`). Widget rects cannot answer it, because a widget reports its declared size either way; only a frame can.
