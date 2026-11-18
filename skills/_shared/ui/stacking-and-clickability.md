# Stacking widgets and making them clickable

How to keep widgets from overlapping when some of them hide, and how to find out why a widget ignores clicks. Toggles and number fields are in `form-controls.md`, cards and tabs in `cards-and-tabs.md`; dragging, hover and status messages are in `dragging-hover-and-status.md`.

The script samples are patterns built on vanilla calls, not vanilla excerpts, and are not run in game; the calls they rely on are cited.

## What the layout system gives you

- Outside spacer widgets, positions are fixed; there is no flexbox. `WrapSpacerWidgetClass` and `GridSpacerWidgetClass` place their own children.
- Siblings draw in tree order, so later siblings sit on top and catch clicks first. `SetSort(int sort)` (`P:\scripts\1_core\proto\enwidgets.c:130`) changes that; a higher value draws on top.
- A widget with `ignorepointer 1` takes no mouse events itself, but its children still do: the pause menu's `continuebtn` (`P:\gui\layouts\day_z_ingamemenu.layout:122`) is clickable inside `WrapSpacerWidgetClass bottom`, which sets `ignorepointer 1` (`:99` to `:101`).
- Enforce Script has no ternary operator, and a local has method scope, not block scope: declare a name once at the top of the method, not in two `if` blocks (`checklist-and-troubleshooting.md`, "Enforce Script limits"; `skills/_shared/enscript/references/language_compile.md`, "Compiler traps").

## Restacking after a change

A hidden widget still holds its place. When visibility or content changes, walk the widgets top to bottom and place each visible one under the last:

```c
void MyMod_RecalculateLayout()
{
    float yPos = HEADER_HEIGHT;
    float w, h;

    if (m_HeaderWidget.IsVisible())
    {
        m_HeaderWidget.SetPos(MARGIN, yPos);
        m_HeaderWidget.GetSize(w, h);
        yPos += h + SPACING;
    }

    m_ContentPanel.SetPos(MARGIN, yPos);
    m_ContentPanel.GetSize(w, h);
    yPos += h + SPACING;

    if (m_ItemList.Count() > 0)
    {
        m_ListPanel.Show(true);
        m_ListPanel.SetPos(MARGIN, yPos);
        m_ListPanel.GetSize(w, h);
        yPos += h + SPACING;
    }
    else
        m_ListPanel.Show(false);
}
```

Call it when the UI opens and closes, after every `Show(bool)`, after items are added or removed, and once after the layout is first created. In a Dabs `ScriptView` that means in your constructor after `super` has built the layout; Dabs has no `OnShow` and no binding hook (`dabs-mvc-internals.md`).

For many small rows, let a spacer do it. A `WrapSpacerWidgetClass` with an exact width and a proportional height grows with its children and flows them down:

```c
ScrollWidgetClass ContentScroll {
 position 0 74
 size 720 490
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  WrapSpacerWidgetClass ContentFlow {
   position 0 0
   size 720 0
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 0
   {
    FrameWidgetClass Item1 {
     size 720 40
    }
    FrameWidgetClass Item2 {
     size 720 40
    }
   }
  }
 }
}
```

The spacer places the rows for you, at the cost of less control over the exact gaps.

## When a widget ignores clicks

Work down this list:

1. `ignorepointer 1` on the widget itself. Keep it on decoration only: backgrounds, labels, separators. A parent's `ignorepointer` does not block its children, as the pause menu shows, so check the widget, not its ancestors.
2. Visibility and size. `visible 0` on the widget or any ancestor stops input, and a widget with no area can't be clicked.
3. Something on top. A later sibling covers it. Reorder the tree, or give the covering widget a lower `SetSort` value.
4. No handler. A plain `ScriptedWidgetEventHandler` gets nothing until `SetHandler(this)` (`enwidgets.c:172`). A `UIScriptedMenu` gets the events of its own layout without it; vanilla `InGameMenu` overrides `OnClick` and never calls `SetHandler` (`P:\scripts\5_mission\gui\ingamemenu.c:161`). Check the signatures: `OnClick(Widget w, int x, int y, int button)` and `OnMouseButtonDown(Widget w, int x, int y, int button)` (`enwidgets.c:668`).
5. Game focus. Without `ChangeGameFocus(1)` (`P:\scripts\3_game\tools\input.c:20`) when the UI opens, clicks go to the game world.
6. Position. `hexactpos 1` and `vexactpos 1` place the widget in exact units of 1/1080 of the screen height from the parent (measured in game; `checklist-and-troubleshooting.md`, "Declare all four unit flags"); `0` places it by fraction, and `size 1 1` fills the parent. A wrong mix can put the widget outside where you click.

## Symptom to fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Widget not clickable | `ignorepointer 1` on the widget itself | Remove it from interactive widgets. |
| Child of an `ignorepointer 1` parent not clickable | Not the parent's flag | Look for a sibling on top, no area, or no handler. |
| Later siblings block clicks | Tree order | Reorder, or a lower `SetSort` on the blocker. |
| Text overlaps what is below | No restack after a visibility change | Call the restack after each change. |
| `OnClick` never fires | No handler, or the wrong signature | `SetHandler(this)` on a plain handler; four parameters. |
| `OnMouseLeave` never fires | Three parameters instead of four | `OnMouseLeave(Widget w, Widget enterW, int x, int y)` (`enwidgets.c:666`). |
| Colors darker than their values | The player's HUD brightness | Design against it; never call `Widget.SetLV(0)` (`theme-and-color.md`). |
| Scroll does nothing | No spacer inside the `ScrollWidget` | Add a `WrapSpacerWidgetClass` or `GridSpacerWidgetClass` child. |
| An animation jumps | Too short a duration | 200 to 500 ms with an easing curve. |
| EditBox text invisible | Text color equals the background, or unset | Set the color in the layout or with `SetColor`. |
| Widget has no size | `size 1 1` with proportional flags in a parent that has no size | Check the size values against the flags. |
| Tab switch leaves old content | The previous panel wasn't hidden | Hide every panel but the active one (`cards-and-tabs.md`). |
| A status message vanishes mid fade | Fade longer than the auto hide delay | Keep the fade (500 ms) well under the delay (3,000 ms). |

Test overlap at more than one resolution; a card that fits at 1080p can collide at 720p.
