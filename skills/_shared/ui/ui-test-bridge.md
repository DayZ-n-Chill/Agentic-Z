# Testing a UI through the test bridge

What the DayZ MCP bridge's UI calls return and where they stop working: Dabs views, reloading a layout from `$profile:`, ESC with a focused edit box, and probes that answer through a file. The bridge is a third party test tool described in `skills/dayz-launch-test/references/mcp/`; facts about its calls are tool behaviour, not game behaviour. All of it was measured in game on 1.29.

## Clicks on Dabs views cannot be automated

On a panel built as a Dabs `ScriptView`, not a `UIScriptedMenu`, with a healthy bridge:

- `ui_tree` with an empty path returns `no_menu`: it walks the active scripted menu, and a `ScriptView` is not one.
- `ui_click` returns `not_handled` on buttons that exist and are on screen. Why a generic handler search misses a Dabs view is in `dabs-mvc-internals.md`, "How a click reaches the handler".

`not_handled` on a button with a permission check is ambiguous: the bridge may not reach the handler, or the handler may refuse as designed. Always click a widget with no check as well. Here the always allowed close button also returned `not_handled` and a capture showed the panel still open, so the click did nothing at all.

- Take widget names from the `.layout`, not from a live tree.
- Any check that needs clicking, typing into an edit box, switching tabs or closing with ESC belongs to a person with a real mouse.
- A call shipped in the bridge's PBO is not always callable: the daemon fixes its tool list when it starts, so `key_press` and `player_respawn` were in the PBO and not available as tools.

## What ui_set_text and ui_click return

Both return the resolver's decision:

```json
"ui_request": {
  "requested_path": "BuilderTabCategory",
  "requested_root": "",
  "requested_text": "",
  "matched_path": "/@0/MyMod_PanelRoot@1/MyMod_Panel@0/BuilderFrame@0/BuilderTabCategory@0"
}
```

- `@N` is the index among siblings, so `MyMod_PanelRoot@1` means at least two roots exist: the clue to a name collision (`widget-name-collisions.md`).
- An ambiguous name returns `ambiguous_path` instead of a guess, and a missing one `widget_not_found`. A `root` must be unique in the whole workspace; `path` is then resolved inside it.

## ui_reload_layout

| Call | Result |
|---|---|
| `reload` with `$profile:<file>.layout` | Loads from disk with no PBO and returns the engine's rects for the whole tree |
| `reload` twice | Replaces the tree; one copy, no `ambiguous_path` |
| `close` | Unlinks the tree; the widget is then `widget_not_found` |
| `reload` with a missing file | `layout_not_found`, and the client stays alive |

A manual `CreateWidgets` called twice does leave the first root in place; the bridge call unlinks before it loads. The preview root reports the engine's viewport (1920x1080), not the window size. A `TextWidget` reports `text: ""` and `text_readable: 0`, because it has no getter.

A layout previewed from `$profile:` has no menu behind it: clicking the window gives focus to the game and the camera captures the mouse, and ESC, which opens the vanilla menu, gives it back. No click on a preview widget works; test interaction on the real panel.

## ESC with a focused edit box

A common ESC handler clears an edit box's focus instead of closing:

```c
Widget focused = GetFocus();
if (focused && EditBoxWidget.Cast(focused))
{
    SetFocus(null);   // uses up this ESC, does not close
    return true;
}
DoClose();
```

`GetFocus()` and `SetFocus(Widget w)` are at `P:\scripts\1_core\proto\enwidgets.c:702` and `:698`. That is sound for players. It breaks a test whose command hook is an invisible `EditBoxWidget`: if a call leaves the hook focused, the first ESC goes to it and the panel stays open. Make the hook a widget that cannot take focus (`ignorepointer 1` is not enough), call `SetFocus(null)` after typing into it, or test closing with the real button.

## Probes that answer through a file

A test hook that answers by writing JSON to the profile folder needs a freshness mark. Without one, a command sent while the panel is closed leaves the file byte for byte the same, because the view's polling stops while it is closed, and a reader sees `"open": true` from the previous dump.

- Compare the file's modified time and hash before and after each command; no change means the command was not handled.
- Better, have the probe write a sequence number or echo the command it got.
- Never expect a value the probe cannot write: a dump saying `"open": false` is impossible if closing stops the polling.
- A marker taken with `logs_since(max_lines=1)` points at the start of the file while the log is under its 256 KiB cap, so a check that treats everything before it as startup noise swallows the whole startup.
