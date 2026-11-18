# Floating windows, colour, hover and scaling

How a mod's draggable window takes the cursor without a full screen modal, gives input back, and handles colour, button hover and screen size. Written for Dabs `ScriptView` windows, but the calls are vanilla. Binding traps are in `dabs-mvc-advanced.md`.

## Taking input without a modal

Lock game input, show the cursor and disable the player's own input, so the player cannot shoot or eat while the window is open. `Input.ChangeGameFocus(int add, int input_device = -1)` is declared at `P:\scripts\3_game\tools\input.c:20` and `UIManager.ShowUICursor(bool visible)` at `P:\scripts\3_game\tools\uimanager.c:244`.

```c
void DoOpen()
{
    Input inp = GetGame().GetInput();
    if (inp)
        inp.ChangeGameFocus(1);
    UIManager uiMgr = GetGame().GetUIManager();
    if (uiMgr)
        uiMgr.ShowUICursor(true);
    m_FocusLocked = true;
    PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
    if (player && player.GetInputController())
        player.GetInputController().SetDisabled(true);
}
```

Close in the exact reverse order: enable the input controller, hide the cursor, then `ChangeGameFocus(-1)` and clear `m_FocusLocked`. Never use `INPUT_EXCLUDE_ALL` or a modal overlay for a floating window. Never use `PlayerControlDisable`; vanilla marks it deprecated (`P:\scripts\3_game\gameplay.c:796`).

The view can be destroyed while open, so release the same things in its destructor. Guard with `if (GetGame())`, always re-enable the input controller, and undo the focus and cursor only when `m_FocusLocked` is set.

## Dragging by the header

```c
override bool OnMouseButtonDown(Widget w, int x, int y, int button)
{
    if (button != 0 || (w != HeaderFrame && w != HeaderBg))
        return false;
    m_Dragging = true;
    float panelX, panelY;
    SorterPanel.GetScreenPos(panelX, panelY);
    m_DragOffX = x - panelX;
    m_DragOffY = y - panelY;
    return true;
}
```

Clear `m_Dragging` in `OnMouseButtonUp` on button 0. While dragging, in `Update(float dt)`, read `GetMousePos(mx, my)` (`P:\scripts\1_core\proto\ensystem.c:329`) and move the panel with `SorterPanel.SetPos(mx - m_DragOffX, my - m_DragOffY)`.

## Colour

Reported by mod authors, not checked on `P:\`: UI colours look 30 to 50 percent darker in game than in a browser, an alpha below `0x30` (48) is effectively invisible, and below `0x14` (20) it is always invisible. Keep every colour in one set of ARGB constants, lifted to suit:

| Constant | Value | Use |
|---|---|---|
| `COL_BG` | `0xEB1E1E1E` | Window background |
| `COL_HEADER` | `0xF0252A36` | Header |
| `COL_BTN` | `0xFF253550` | Button |
| `COL_BTN_HOVER` | `0xFF304060` | Button under the cursor, about 30 percent lighter |
| `COL_TEXT`, `COL_TEXT_MID` | `0xFFB0C0D0`, `0xFF8090A0` | Main and secondary text |
| `COL_SEPARATOR` | `0x30FFFFFF` | Separator line, at the lowest visible alpha |
| `COL_GREEN`, `COL_RED` | `0xFF4ADE80`, `0xFFF87171` | Accent and warning |

To colour an image widget, give it a plain white procedural texture first, then tint it:

```c
PanelBg.LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)");
PanelBg.SetColor(COL_BG);
```

## Hover without framework support

Cache each button background and its normal colour when the window opens. In `OnMouseEnter`, walk up from the widget to its `ButtonWidget`, find its background image (see `dabs-mvc-advanced.md`, section "Auto binding inside a `ButtonWidget`"), restore the previous highlight and set `COL_BTN_HOVER`. In `OnMouseLeave`, restore it and clear the reference.

The two handlers take different arguments: `OnMouseEnter(Widget w, int x, int y)` and `OnMouseLeave(Widget w, Widget enterW, int x, int y)` (`P:\scripts\1_core\proto\enwidgets.c:665` and `:666`). Return false from both so the event carries on.

## Scaling for other resolutions

Layouts are usually drawn for 1080 lines. Scale by screen height, read with `GetScreenSize(out int x, out int y)` (`P:\scripts\1_core\proto\ensystem.c:331`):

```c
class MyMod_UIScaler
{
    static float ComputeScale()
    {
        int screenW, screenH;
        GetScreenSize(screenW, screenH);
        return screenH / 1080.0;
    }

    static void ScaleWidget(Widget w, float scale)
    {
        if (!w || Math.AbsFloat(scale - 1.0) < 0.01)
            return;
        float ww, wh;
        w.GetSize(ww, wh);
        w.SetSize(ww * scale, wh * scale);
    }
}
```
