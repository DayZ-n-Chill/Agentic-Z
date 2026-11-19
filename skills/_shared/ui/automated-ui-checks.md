# Automated UI checks

What a script-driven UI check can and cannot do in DayZ: finding a Dabs view, calling a click handler, loading a layout from `$profile:`, ESC with a focused edit box, and probes that answer through a file. The engine calls are cited from `P:\`; the behaviour around them was measured in game on DayZ 1.29.

## Dabs views are not menus

A panel built as a Dabs `ScriptView`, not a `UIScriptedMenu`, is invisible to anything that starts from the active menu: `GetGame().GetUIManager().GetMenu()` returns a `UIScriptedMenu` (`P:\scripts\3_game\tools\uimanager.c:59`), and a `ScriptView` is not one. Start a widget search from the view's own root instead.

Calling a click handler from script is not a mouse click. `ScriptedWidgetEventHandler.OnClick(Widget w, int x, int y, int button)` (`P:\scripts\1_core\proto\enwidgets.c:658`) can be called directly with the coordinates at zero, and that skips hit testing, draw order and `IGNOREPOINTER` (`enwidgets.c:78`). A generic search that walks up the parents for a handler misses a valid Dabs view; why is in `dabs-mvc-internals.md`, "How a click reaches the handler". On a measured Dabs panel such a call reached no handler on buttons that existed and were on screen, and a screenshot showed the panel still open.

A click that reports "not handled" on a button with a permission check is ambiguous: the call may not reach the handler, or the handler may refuse as designed. Always click a widget with no check as well.

- Take widget names from the `.layout`, not from a live tree.
- Any check that needs clicking, typing into an edit box, switching tabs or closing with ESC belongs to a person with a real mouse.

## Finding a widget by name

`FindAnyWidget` searches the whole tree under the widget it is called on (`P:\scripts\1_core\proto\enwidgets.c:169`), so a name that appears under two roots resolves to whichever comes first. Two copies of a panel root on screen is the usual cause of a click or a text going to the wrong widget; see `widget-name-collisions.md`. Positions read back from a widget are relative to its parent: a child at `position 110 110` inside a parent at `position 100 100` sits at 210, 210 on screen.

## Loading a layout from the profile folder

| Step | Result (measured in game) |
|---|---|
| `CreateWidgets` with `$profile:<file>.layout` | Loads from disk with no PBO |
| `CreateWidgets` twice | Leaves the first root in place, so two copies exist; unlink the old root first |
| `Unlink` on the root | Removes the tree; `FindAnyWidget` then returns null |
| A missing file | Kills the client inside the native call; guard every load with `FileExist` (`hot-iteration.md`, "The four traps") |

`CreateWidgets` is at `P:\scripts\1_core\proto\enwidgets.c:181`. The preview root reports the engine's viewport (1920x1080), not the window size. A `TextWidget` has `SetText` but no getter (`enwidgets.c:189` to `:215`), so a check cannot read back the text it set; read it from your own script or look at the screen.

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
- When a check marks a place in `script.log` to read only later lines, take the mark as the file's size in bytes at that moment, not as a line near the start, or the whole startup counts as new.
