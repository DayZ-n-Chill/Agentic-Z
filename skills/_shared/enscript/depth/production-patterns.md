# UI state patterns

How shipped mods keep a panel's hover, disabled and animated states consistent, batch widget updates, lock and release input, and what an action on the cursor promises. Binding, collection and singleton lifetimes are in `ui-view-lifecycle.md`.

These are third-party mod patterns, not vanilla code. `ScriptView`, `ViewController`, `ViewBinding`, `ObservableCollection` and `NotifyPropertyChanged` belong to the Dabs Framework (`../integrations/dabs_framework.md`). `WidgetAnimator` is not a vanilla class (nothing under `P:\scripts\` declares it); treat it as the mod's own helper.

## Hover colour cache

Cache each widget's colour before you change it, and restore from the cache. Vanilla keys maps by `Widget` too (`m_RadialItemCards`, `P:\scripts\3_game\gui\effects\radialmenu.c:17`).

```c
protected ref map<Widget, int> m_HoverColorCache = new map<Widget, int>;
protected Widget m_HoveredWidget;

void CacheColor(Widget w, int color)
{
    if (w)
        m_HoverColorCache.Insert(w, color);
}

protected bool FindCachedColor(Widget w, out int color)
{
    if (!w)
        return false;
    return m_HoverColorCache.Find(w, color);
}

void MyMod_HoverEnter(Widget target)
{
    int original;
    if (!m_IsOpen || !FindCachedColor(target, original))
        return;
    target.SetColor(MyMod_Lighten(original));
    m_HoveredWidget = target;
}

void MyMod_HoverLeave()
{
    int original;
    if (m_HoveredWidget && FindCachedColor(m_HoveredWidget, original))
        m_HoveredWidget.SetColor(original);
    m_HoveredWidget = null;
}
```

Report "not found" with the `bool`, never with `-1`: an opaque ARGB colour is a negative `int`, and `0xFFFFFFFF` is `-1`.

- Cache a colour before changing it, and null check every lookup.
- When a drag starts, restore the hover colour at once, and clear hover tracking when the panel closes.

## Disabling controls

When a panel becomes unavailable (unpaired, waiting, loading), dim every control and write the dimmed colour into the cache, so a later hover does not flash the old bright colour. Re-enabling restores the colour cached when the panel first applied its colours. If the hovered control is disabled, clear `m_HoveredWidget` too.

```c
protected void SetControlsEnabled(bool enabled)
{
    foreach (Widget ctrl : m_Controls)
    {
        if (!ctrl)
            continue;
        if (enabled)
        {
            int original;
            if (FindCachedColor(ctrl, original))
                ctrl.SetColor(original);
            continue;
        }
        ctrl.SetColor(MYMOD_COL_DIMMED);   // for example 0xFF151E2E
        CacheColor(ctrl, MYMOD_COL_DIMMED);
    }
}
```

`m_Controls` is a member array filled once from `FindAnyWidget` or member references, not a new array per call.

## One animation at a time

Keep a reference to the running animator and cancel it before starting another on the same widget, or they stack:

```c
protected ref WidgetAnimator m_ActiveAnimator;

void PlayHover(Widget target)
{
    CancelActiveAnimation();
    m_ActiveAnimator = new WidgetAnimator(target, 0.5);
    m_ActiveAnimator.AnimateColor(target, 0xFFFFFFFF, 0);
}

protected void CancelActiveAnimation()
{
    if (!m_ActiveAnimator)
        return;
    m_ActiveAnimator.Unlink();
    m_ActiveAnimator = null;
}
```

Stop it with `Unlink()` rather than only dropping the reference, and cancel it in the destructor so no animation outlives the view.

## Batch widget updates

When contents change often, set a pending flag and refresh once in the next `Update`, instead of updating the same widget from several code paths in one frame:

```c
void OnContentsChanged()
{
    m_UpdatePending = true;
}

void Update(float deltaTime)
{
    if (!m_UpdatePending)
        return;
    m_UpdatePending = false;
    foreach (MyMod_ItemWidget item : m_VisibleItems)
        RefreshItemVisuals(item);   // SetText, SetImage, SetCurrent together
}
```

## Locking input for a panel

`Input.ChangeGameFocus(int add, ...)` adds to a focus counter; it does not set a mode (`P:\scripts\3_game\tools\input.c:20`). So `ChangeGameFocus(0)` on close changes nothing and leaves the lock on. Pair each `ChangeGameFocus(1)` with `ChangeGameFocus(-1)`, as vanilla's `UIScriptedMenu` does in `LockControls` and `UnlockControls` (`P:\scripts\3_game\tools\uiscriptedmenu.c:89`, `:113`), or call `ResetGameFocus()` to set the counter to 0 (`input.c:27`).

- Lock in open; on close, release before hiding the panel.
- In the destructor, release if the view was still open, so the player is never left stuck.
- `GetGame().GetInput().SetDisabled(...)` does not compile; `Input` has no such method. To freeze the character's own input, use `SetDisabled` on `HumanInputController` (`P:\scripts\3_game\human.c:22`), reached through the player's `GetInputController()` (`:1458`).
- Check it: with the panel open, WASD must not move the player; after closing, it must.

The floating window version, with cursor and drag, is in `dabs-floating-windows.md`.

## What the action cursor promises

Vanilla can show an action whose `CanBeStarted()` is false, such as an info panel (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18` to `:21`), but the client manager tests `CanBeStarted()` before `ActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336` and `:337`). Visible on the cursor does not mean the key will run it.

Gate client-only presentation on `DayZPlayer.IsFirstRenderFrame()` (`P:\scripts\3_game\dayzplayer.c:1186` to `:1189`) when the simulation ticks more than once per render frame. For one-time initialisation, `DoOnce.Run(string key, Class target, string fnName, Param params = null)` (`P:\scripts\3_game\doonce.c:12`) records the key, then calls the method through `g_Game.GameScript.CallFunctionParams`; `HasRun` and `Clear` are at `:30` and `:37`. It is not a per-frame debounce; periodic work still runs from one manager (`hard-rules.md`, section "Timers").
