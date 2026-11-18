# Dragging, hover and status messages

How to make a window the player can drag by its header, give a button hover feedback, and show a status message that fades out. Restacking and click problems are in `stacking-and-clickability.md`; admin style windows that resize from every edge are in `admin-ui-patterns.md`.

The samples are patterns built on vanilla calls, not vanilla excerpts, and are not run in game. They use a vanilla `UIScriptedMenu`, which receives the events of its own layout and has a per frame `Update(float timeslice)` (`P:\scripts\3_game\tools\uiscriptedmenu.c:195`).

## A window dragged by its header

`ScriptedWidgetEventHandler` has no mouse move event; its full list runs from `OnClick` to `OnEvent` (`P:\scripts\1_core\proto\enwidgets.c:656` to `:686`). An `OnMouseMove` override is never called. Start the drag on button down, follow the mouse in `Update` with `GetMousePos` (`P:\scripts\1_core\proto\ensystem.c:329`), and stop on button up:

```c
class MyMod_WindowMenu extends UIScriptedMenu
{
    protected Widget m_Window;
    protected Widget m_Header;
    protected float m_DragOffsetX, m_DragOffsetY;
    protected bool m_IsDragging;

    override bool OnMouseButtonDown(Widget w, int x, int y, int button)
    {
        if (w != m_Header)
            return false;
        float wndX, wndY;
        m_Window.GetScreenPos(wndX, wndY);
        m_DragOffsetX = wndX - x;
        m_DragOffsetY = wndY - y;
        m_IsDragging = true;
        return true;
    }

    override bool OnMouseButtonUp(Widget w, int x, int y, int button)
    {
        if (!m_IsDragging)
            return false;
        m_IsDragging = false;
        return true;
    }

    override void Update(float timeslice)
    {
        super.Update(timeslice);
        if (!m_IsDragging)
            return;
        int mouseX, mouseY, screenW, screenH;
        GetMousePos(mouseX, mouseY);
        GetScreenSize(screenW, screenH);
        float w, h;
        m_Window.GetScreenSize(w, h);
        float newX = Math.Clamp(mouseX + m_DragOffsetX, 0, screenW - w);
        float newY = Math.Clamp(mouseY + m_DragOffsetY, 0, screenH - h);
        m_Window.SetScreenPos(newX, newY);
    }
}
```

`OnMouseButtonDown` and `OnMouseButtonUp` are at `enwidgets.c:668` and `:669`. The header needs `ignorepointer 0` so it catches the press; its title text keeps `ignorepointer 1`. Storing the offset at the press keeps the window from jumping to the cursor, and the clamp keeps it on screen.

The other route is the native `WidgetFlags.DRAGGABLE` (`enwidgets.c:84`) with the `OnDrag`, `OnDragging` and `OnDrop` events (`:676` to `:679`).

## Hover feedback

A `ButtonWidget` shows no hover state unless its style defines one, so tint it from the hover events (not checked on `P:\`; the vanilla pause menu tints a child panel from script the same way, see `text-sizing-and-rendering.md`):

```c
override bool OnMouseEnter(Widget w, int x, int y)
{
    ImageWidget btnBg = ImageWidget.Cast(w.FindWidget("BtnBg"));
    if (btnBg)
        btnBg.SetColor(ARGB(255, 70, 70, 80));
    return false; // let the parent see it too
}

override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
{
    ImageWidget btnBg = ImageWidget.Cast(w.FindWidget("BtnBg"));
    if (btnBg)
        btnBg.SetColor(ARGB(255, 45, 45, 55));
    return false;
}
```

`OnMouseEnter` takes three parameters and `OnMouseLeave` four, `(Widget w, Widget enterW, int x, int y)` (`enwidgets.c:665` and `:666`). With three, the leave method is a different overload and is never called. With Dabs Framework, `WidgetAnimator.AnimateColor(btnBg, color, 150)` fades the tint instead of switching it (`dabs-observables-and-animation.md`).

## A status message that fades out

A hidden bar with a background and centred text, shown with a message and hidden again after three seconds:

```c
FrameWidgetClass StatusBar {
 visible 0
 size 400 40
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  ImageWidgetClass StatusBg {
   size 1 1
   hexactpos 0
   vexactpos 0
   hexactsize 0
   vexactsize 0
   stretch 1
   ignorepointer 1
  }
  TextWidgetClass StatusText {
   position 8 12
   size 384 16
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   font "gui/fonts/Metron"
   "text halign" center
   "text valign" center
   ignorepointer 1
  }
 }
}
```

```c
void ShowStatus(string text, int color)
{
    m_StatusText.SetText(text);
    m_StatusText.SetColor(color);
    m_StatusBar.Show(true);
    WidgetAnimator.Animate(m_StatusBg, WidgetAnimatorProperty.COLOR_A, 1.0, 200);
    GetGame().GetCallQueue(CALL_CATEGORY_GUI).CallLater(HideStatus, 3000, false);
}

void HideStatus()
{
    WidgetAnimator.Animate(m_StatusBg, WidgetAnimatorProperty.COLOR_A, 0.0, 500);
    GetGame().GetCallQueue(CALL_CATEGORY_GUI).CallLater(HideStatusNow, 500, false);
}

void HideStatusNow()
{
    m_StatusBar.Show(false);
}
```

The fades use Dabs Framework's `WidgetAnimator`, which takes milliseconds; without Dabs, drop those two lines and the bar simply appears and disappears. `CallLater` takes the method itself (`P:\scripts\2_gamelib\tools.c:61`); a method named by a string needs `CallLaterByName` (`:63`). Keep the fade out (500 ms) well under the delay before it (3,000 ms).
