# Color pickers

How to build a color editor where sliders and edit boxes stay in step, and how to reuse the finished picker of a group mod's core library without its three lifetime traps.

The patterns come from a large production group and map mod; `My*` names are its helper classes and are not vanilla, and the picker's behaviour is the mod's, not checked on `P:\`. The vanilla calls are cited.

## Sliders and edit boxes in step

Each channel has a `SliderWidget` and an `EditBoxWidget`, and each updates the other from its own change event. Clamp typed values to 0 to 255:

```c
SliderWidget slider_r, slider_g, slider_b;
EditBoxWidget edit_r, edit_g, edit_b;
Widget preview;

bool OnSliderUpdate(SliderWidget slider, EditBoxWidget edit)
{
    edit.SetText("" + slider.GetCurrent());
    UpdatePreview();
    return true;
}

bool OnTextUpdated(SliderWidget slider, EditBoxWidget edit)
{
    int val = Math.Min(255, Math.Max(0, edit.GetText().ToInt()));
    edit.SetText("" + val);
    slider.SetCurrent(val);
    UpdatePreview();
    return true;
}

void UpdatePreview()
{
    preview.SetColor(ARGB(255, slider_r.GetCurrent(), slider_g.GetCurrent(), slider_b.GetCurrent()));
}
```

`SetCurrent` and `GetCurrent` are at `P:\scripts\1_core\proto\enwidgets.c:363` and `:364`; `EditBoxWidget.GetText()` returns the string directly (`:349`).

## Reusing the group mod's picker

When your mod already depends on the group mod's core library, don't build a dialog: its picker has A, R, G and B sliders each paired with an edit box, a hex field and a live swatch, and its layout is already registered with the library's layout manager (`ui-architecture.md`, "Layouts by name").

```c
MyColorPicker(Widget parent, ScriptCaller selectCallback, int color_ = -1, MyColorConfig colorCfg_ = null, bool allowAlpha_ = true)
```

- `allowAlpha_ = false` hides the alpha panel, and `GetColor()` then returns `ARGB(255, r, g, b)`.
- `parent` must not be null; the constructor calls `parent.GetScreenPos()` without a check.
- The callback is `void OnColorPicked(int color)`.

These come from adding a route color to a GPS overlay built on that library:

- Never release the owning `ref` inside the picker's own callback. The picker calls `callback.Invoke(GetColor())` and then `delete this`, and its destructor unlinks its root. Clearing your `ref` in the callback drops the last strong reference while the picker is still running, so the `delete this` that follows hits a dead object and the game crashes as the player confirms. Keep the member, leave it alone in the callback, and let the next `new` overwrite it, as the library's own call site does.
- The picker outlives the menu that opened it. Its root has no parent and is only placed against your widget, so it sits on the workspace, not inside your menu. Closing the map leaves it on screen with a callback into a hidden owner. Release the reference in the owner's `OnHide()`; that is safe there because none of the picker's code is running.
- A color change does not repaint an overlay guarded by a dirty check that ignores style. Add a style revision to the check at every draw site (`map-and-markers.md`, "Refresh only on change"). A mod that draws the same route on the map and on the HUD has two draw sites; search for the draw call to find both.

Save the choice with a flat settings class (`hud-overlays.md`, "Settings saved per server").

A swatch stretched across a whole button looks fine in orange and makes the label unreadable when the player picks white. Keep the button's own background and show the swatch as a small square beside the label.
