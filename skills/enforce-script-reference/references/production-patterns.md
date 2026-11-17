# Production UI patterns: Enforce Script best practices

Patterns for UI code in production Enforce Script mods. They address common issues in UI state management, view binding, animation, memory, and event handling that cause crashes, leaks, or visual bugs in production.

The snippets are third-party mod design patterns, not vanilla code. `ScriptView`, `ViewController`, `ViewBinding`, `ObservableCollection` and `NotifyPropertyChanged` belong to the third-party Dabs Framework (`skills/_shared/enscript/integrations/dabs_framework.md`), and `WidgetAnimator` is not a vanilla class (no hit under `P:\scripts\`): treat it as the mod's own helper. A line cited as `P:\...:N` was opened on `P:\`.

---

## UI State Management

### Tracking Active UI State (Hover, Selection, Focus)

When UI widgets change visual state (color, text, position) based on user interaction, you must maintain a consistent cache of the previous state to restore it correctly.

**Pattern: Hover Color Cache**

Maintain a `map` or `ref array` of widget-to-color bindings (vanilla keys maps by `Widget` too, for example `m_RadialItemCards` at `P:\scripts\3_game\gui\effects\radialmenu.c:17`). When a widget enters hover state, save its original color BEFORE changing it. When it exits hover or becomes disabled, restore from cache.

```
// Member field in View class
protected ref map<Widget, int> m_HoverColorCache;

// In constructor
m_HoverColorCache = new map<Widget, int>;

// When applying initial state (ApplyInitialColors)
void CacheColor(Widget wid, int color)
{
    if (m_HoverColorCache && wid)
    {
        m_HoverColorCache.Insert(wid, color);
    }
}

// On hover enter
bool OnMouseEnter()
{
    if (!m_IsOpen)
        return false;

    // Find the target widget (button, panel, etc)
    Widget target = GetEventTarget();
    if (target)
    {
        // Fetch original color from cache
        int originalCol;
        if (FindCachedColor(target, originalCol))
        {
            int hoverCol = ModifyColor(originalCol, 0.8f); // brighten or adjust
            target.SetColor(hoverCol);
            m_HoveredWidget = target;
        }
    }
    return true;
}

// On hover exit
bool OnMouseLeave()
{
    if (!m_IsOpen)
        return false;

    if (m_HoveredWidget)
    {
        int restoreCol;
        if (FindCachedColor(m_HoveredWidget, restoreCol))
        {
            m_HoveredWidget.SetColor(restoreCol);
        }
        m_HoveredWidget = null;
    }
    return true;
}

// Helper: look up cached color; returns false when the widget has none.
// Do not signal "not found" with -1: an opaque ARGB color is a negative int, and 0xFFFFFFFF is -1.
protected bool FindCachedColor(Widget wid, out int color)
{
    if (!m_HoverColorCache || !wid)
        return false;

    return m_HoverColorCache.Find(wid, color);
}
```

**Key rules**:
1. Always cache color/state BEFORE modifying it.
2. Guard all cache lookups with null checks.
3. On disable (SetControlsEnabled), update the cache to the new disabled color so hover restore doesn't flash the old bright color.
4. On drag start, restore hover immediately — don't let the widget stay in hover state while moving.
5. On close, clear hover tracking to prevent stale state.

---

### Disabling/Enabling UI Elements Consistently

When a UI panel becomes disabled (unpaired, waiting, loading), all interactive widgets must change appearance AND maintain correct hover behavior.

**Pattern: Centralized DisableControl**

```
// In View class
protected void SetControlsEnabled(bool enabled)
{
    // List all control widgets that have visual feedback
    ref array<Widget> controls = new array<Widget>;
    // (populate from FindAnyWidget or member refs)

    for (int i = 0; i < controls.Count(); i = i + 1)
    {
        Widget ctrl = controls.Get(i);
        if (!ctrl)
            continue;

        if (enabled)
        {
            int originalCol;
            if (FindCachedColor(ctrl, originalCol))
            {
                ctrl.SetColor(originalCol);
            }
        }
        else
        {
            // Disabled state: dim the widget
            int dimmedCol = 0xFF151E2E; // or theme-specific dim color
            ctrl.SetColor(dimmedCol);

            // IMPORTANT: Update cache so future hovers don't use old bright color
            CacheColor(ctrl, dimmedCol);
        }
    }
}
```

**Key rules**:
1. When disabling, not only change widget color but also UPDATE the cached color.
2. When re-enabling, restore from cache (cache should have the original bright color from ApplyInitialColors).
3. Clear any active hover tracking when disabling — if a button was hovered and you disable it, don't leave m_HoveredWidget pointing to it.

---

## View Binding Best Practices

### What to Bind vs What to Control Manually

Not everything should use ObservableCollection auto-binding. Binding is powerful for bulk updates but has overhead and can hide bugs.

**Pattern: Selective Binding**

```
// Good: Bind large, frequently-changed lists
class MyView extends ScriptView
{
    protected ObservableCollection m_Items; // Bind this
    protected ViewBinding m_ItemsBinding;

    // In OnInit or similar
    void RefreshItems()
    {
        // Clear and refill m_Items, binding handles UI update automatically
        m_Items.Clear();
        for (int i = 0; i < sourceData.Count(); i = i + 1)
        {
            m_Items.Insert(new MyItemView(sourceData.Get(i)));
        }
    }
}

// Good: Manually control single-item updates
void UpdateSelectedItem(MyItemView item)
{
    if (!item)
        return;

    // Don't rebuild entire list, just update the one item's visual properties
    Widget itemWidget = FindAnyWidget("ItemWidget_" + item.GetId());
    if (itemWidget)
    {
        TextWidget label = TextWidget.Cast(itemWidget.FindAnyWidget("Label"));
        if (label)
        {
            label.SetText(item.GetName());
        }
    }
}

// Avoid: Binding single values that change once
class BAD_View extends ScriptView
{
    protected string m_Title; // Don't bind this, just set widget text once
    protected ViewBinding m_TitleBinding; // Unnecessary overhead

    void SetTitle(string newTitle)
    {
        m_Title = newTitle;
        // Binding will trigger, view updates... overkill for one value.
    }
}
```

**Key rules**:
1. Bind collections (ObservableCollection) that change frequently.
2. Bind individual values only if they change often OR if you're enforcing data-driven UI (e.g., MVVM pattern).
3. For one-time initialization or rare updates, use FindAnyWidget + SetText/SetColor directly.
4. When binding, ensure the view class (MyItemView) has proper NotifyPropertyChanged calls — if binding is set up but NotifyPropertyChanged isn't called, the UI won't update.

---

### Circular References in Collections

When ObservableCollection holds views that reference back to the controller, you must break the cycle in destructors.

**Pattern: Destructor Cleanup**

```
// In tag view that references controller
class TagView extends ScriptView
{
    protected ref SorterController m_OwnerController;

    void ~TagView()
    {
        // Break circular reference: collection holds TagView, TagView holds controller
        m_OwnerController = null;
    }
}

// In controller that holds collection
class SorterController
{
    protected ref ObservableCollection m_TagsList;

    void ClearCollections()
    {
        // MUST call Clear in DoClose, not just let panel close
        if (m_TagsList)
        {
            m_TagsList.Clear(); // Triggers destructors of all TagViews
        }
    }

    void ~SorterController()
    {
        // Final safety net
        ClearCollections();
    }
}

// In View that uses controller
class SorterView extends ScriptView
{
    void DoClose()
    {
        m_IsOpen = false;

        // Clear collections BEFORE hiding panel
        SorterController ctrl = SorterController.Cast(GetController());
        if (ctrl)
        {
            ctrl.ClearCollections();
        }

        // Hide UI
        GetLayoutRoot().Show(false);
    }
}
```

**Key rules**:
1. Always null references in destructors, especially back-references to parent objects.
2. Call Clear() on collections when the panel closes, don't rely on GC to eventually collect.
3. Test: close panel, open again, close again — if objects don't release, you have a leak.

---

## Animation Management

### Preventing Stale Animations (Overlapping Cancel)

When canceling a previous animation to start a new one, you must cancel by reference, not by widget alone. Multiple animations can queue on the same widget.

**Pattern: Tracked Animation Cancellation**

```
class AnimatedPanel extends ScriptView
{
    protected ref WidgetAnimator m_ActiveAnimator;

    void PlayHoverAnimation(Widget target)
    {
        // Cancel previous animation first
        CancelActiveAnimation();

        // Create new animation
        WidgetAnimator anim = new WidgetAnimator(target, .5f); // 0.5s duration
        anim.AnimateColor(target, 0xFFFFFFFF, 0); // white, 0ms delay

        m_ActiveAnimator = anim;
    }

    void PlayExitAnimation(Widget target)
    {
        // Cancel hover anim, don't stack
        CancelActiveAnimation();

        WidgetAnimator anim = new WidgetAnimator(target, .3f);
        anim.AnimateColor(target, 0xFF808080, 0); // gray

        m_ActiveAnimator = anim;
    }

    protected void CancelActiveAnimation()
    {
        if (m_ActiveAnimator)
        {
            m_ActiveAnimator.Unlink(); // Stop immediately
            m_ActiveAnimator = null;
        }
    }

    void ~AnimatedPanel()
    {
        CancelActiveAnimation();
    }
}
```

**Key rules**:
1. Store the animator reference so you can cancel it later.
2. Call Unlink() to stop an animation, not just discard the reference (GC may not call it immediately).
3. Cancel before starting a new animation on the same widget to prevent stacking.
4. Cancel in destructor to ensure no animation outlives the view.

---

### Batching Updates (Minimize Redraws)

In tight loops or frequent updates, batch multiple widget changes before the next frame.

**Pattern: Deferred Update**

```
class ScrollingList extends ScriptView
{
    protected ref array<ItemWidget> m_VisibleItems;
    protected bool m_UpdatePending;

    void OnContentsChanged()
    {
        // Don't update immediately; mark pending and do once per frame
        m_UpdatePending = true;
    }

    void Update(float deltaTime)
    {
        if (!m_UpdatePending)
            return;

        m_UpdatePending = false;

        // Do all updates in one batch
        for (int i = 0; i < m_VisibleItems.Count(); i = i + 1)
        {
            ItemWidget item = m_VisibleItems.Get(i);
            RefreshItemVisuals(item);
        }
    }

    void RefreshItemVisuals(ItemWidget item)
    {
        // Multiple widget.Set* calls — batched together
        TextWidget nameLabel = TextWidget.Cast(item.FindAnyWidget("NameLabel"));
        if (nameLabel)
        {
            nameLabel.SetText(item.GetName());
        }

        ImageWidget icon = ImageWidget.Cast(item.FindAnyWidget("Icon"));
        if (icon)
        {
            icon.SetImage(item.GetIcon());
        }

        ProgressBarWidget bar = ProgressBarWidget.Cast(item.FindAnyWidget("ProgressBar"));
        if (bar)
        {
            bar.SetCurrent(item.GetProgress());
        }
    }
}
```

**Key rules**:
1. Collect changes in a pending flag, apply them in one Update() call.
2. Avoid updating the same widget multiple times in the same frame from different code paths.

---

## Memory and Leak Prevention

### Static Instance Cleanup (RefCount Awareness)

Static singleton instances hold a permanent reference. Use weak refs or explicit nulling on cleanup.

**Pattern: Static Singleton with Proper Cleanup**

```
class SorterView extends ScriptView
{
    protected static ref SorterView s_Instance; // RefCount = 1 always

    static SorterView Get()
    {
        return s_Instance;
    }

    static void Create()
    {
        if (!s_Instance)
        {
            s_Instance = new SorterView();
        }
    }

    void Cleanup()
    {
        // Release input lock and static reference
        if (GetGame())
        {
            GetGame().GetInput().ResetGameFocus();
        }

        // CORRECT: null instead of delete
        s_Instance = null; // GC decrement refcount and runs destructor
    }

    void ~SorterView()
    {
        // Release input, clear collections, etc.
        if (GetGame())
        {
            GetGame().GetInput().ResetGameFocus();
        }
    }
}
```

**Key rules**:
1. Never use `delete` on objects — use null assignment instead.
2. Always null the static reference in a Cleanup() method to allow GC.
3. Put cleanup code in destructor so it runs regardless of whether GC or explicit cleanup triggers it.
4. Test: call Cleanup(), create new instance, confirm old instance is destroyed (add print to destructor).

---

### Temporary Allocations in Update Loops

Don't create arrays, maps, or objects inside frequently-called methods. Reuse member fields.

**Pattern: Preallocated Member Arrays**

```
class DataManager extends ScriptView
{
    // Good: Reuse arrays in each Update
    protected ref array<Object> m_TempObjectList;
    protected ref map<string, bool> m_TempValidIds;

    void DataManager()
    {
        m_TempObjectList = new array<Object>;
        m_TempValidIds = new map<string, bool>;
    }

    void PruneInvalidEntities()
    {
        // Clear and reuse instead of new
        m_TempObjectList.Clear();
        m_TempValidIds.Clear();

        // Populate (GetObjectsAtPosition fills an array<Object>; cast what you need)
        GetGame().GetObjectsAtPosition(pos, 100, m_TempObjectList, null);

        for (int i = 0; i < m_TempObjectList.Count(); i = i + 1)
        {
            EntityAI ent = EntityAI.Cast(m_TempObjectList.Get(i));
            if (ent && IsValidForSorter(ent))
            {
                m_TempValidIds.Insert(ent.GetType(), true);
            }
        }
    }
}
```

There is no `GetGame().GetWorld().QueryEntitiesInRange(...)` in vanilla (no hit under `P:\scripts\`); the query above is the vanilla `GetObjectsAtPosition` (`P:\scripts\3_game\global\game.c:923`).

**Bad pattern**:
```
void PruneInvalidEntities()
{
    ref array<EntityAI> tmpList = new array<EntityAI>; // WRONG: new every frame
    tmpList.Clear();
    // ... operations ...
    // tmpList leaks or fragments heap
}
```

**Key rules**:
1. Allocate temporary arrays/maps once in constructor.
2. Clear() before use each frame; don't `new` every time.
3. Measure with EnProfiler if you suspect allocation churn.

---

## Event Handler Patterns

### Dispatch Table vs If Chains

Large branching logic in event handlers should use dispatch tables to avoid stack overhead and bugs.

**Pattern: Dispatch Table for Buttons**

```
class ControllerWithManyButtons extends ViewController
{
    protected ref map<Widget, string> m_ButtonDispatchMap;

    void ControllerWithManyButtons()
    {
        m_ButtonDispatchMap = new map<Widget, string>;
    }

    void OnInit()
    {
        RegisterButton("BtnSort", "OnSortClicked");
        RegisterButton("BtnSave", "OnSaveClicked");
        RegisterButton("BtnClose", "OnCloseClicked");
        RegisterButton("BtnRefresh", "OnRefreshClicked");
        RegisterButton("BtnSettings", "OnSettingsClicked");
    }

    protected void RegisterButton(string widgetName, string actionName)
    {
        Widget btn = GetLayoutRoot().FindAnyWidget(widgetName);
        if (btn)
        {
            m_ButtonDispatchMap.Insert(btn, actionName);
        }
    }

    void OnButtonPress(Widget button)
    {
        string action = "";
        if (m_ButtonDispatchMap.Find(button, action))
        {
            // Dispatch by name
            if (action == "OnSortClicked")
            {
                OnSortClicked();
            }
            else if (action == "OnSaveClicked")
            {
                OnSaveClicked();
            }
            else if (action == "OnCloseClicked")
            {
                OnCloseClicked();
            }
            else if (action == "OnRefreshClicked")
            {
                OnRefreshClicked();
            }
            else if (action == "OnSettingsClicked")
            {
                OnSettingsClicked();
            }
        }
    }

    // Individual handlers (kept small)
    void OnSortClicked()
    {
        // Action
    }

    void OnSaveClicked()
    {
        // Action
    }

    // ... etc
}
```

**Advantages**:
1. Easy to add new buttons: register in OnInit, add handler method.
2. Button handlers are isolated and testable.
3. Avoids massive nested if/else chains that hide bugs.

**Alternative: Explicit if chain** (acceptable for < 5 buttons):
```
void OnButtonPress(Widget button)
{
    if (button == m_BtnSort)
    {
        OnSortClicked();
    }
    else if (button == m_BtnSave)
    {
        OnSaveClicked();
    }
    else if (button == m_BtnClose)
    {
        OnCloseClicked();
    }
}
```

**Key rules**:
1. Keep individual handlers small and focused.
2. Use dispatch tables for > 5 button types.
3. Always null-check widget references before using in dispatch.

---

### Input Lock Timing (Focus Management)

When a modal UI panel opens, lock input to prevent game interaction. When it closes, unlock immediately.

**Pattern: Input Lock/Unlock**

```
class ModalView extends ScriptView
{
    void DoOpen()
    {
        m_IsOpen = true;
        GetLayoutRoot().Show(true);

        // Lock input: prevents player move, interact, etc.
        if (GetGame())
        {
            GetGame().GetInput().ChangeGameFocus(1); // adds 1 to the focus counter
        }
    }

    void DoClose()
    {
        m_IsOpen = false;

        // Unlock input BEFORE hiding (so UI state is consistent)
        if (GetGame())
        {
            GetGame().GetInput().ChangeGameFocus(-1); // takes back the 1 added in DoOpen
        }

        GetLayoutRoot().Show(false);
    }

    void ~ModalView()
    {
        // Safety: if destroyed while open, unlock
        if (m_IsOpen && GetGame())
        {
            GetGame().GetInput().ChangeGameFocus(-1);
        }
    }
}
```

`ChangeGameFocus(int add, ...)` adds its argument to a focus counter; it does not set a mode (`P:\scripts\3_game\tools\input.c:20`). So a close call of `ChangeGameFocus(0)` changes nothing and leaves the lock on. Pair each `ChangeGameFocus(1)` with a `ChangeGameFocus(-1)`, as vanilla's `UIScriptedMenu` does in `LockControls` and `UnlockControls` (`P:\scripts\3_game\tools\uiscriptedmenu.c:89`, `:113`), or call `ResetGameFocus()` to set the counter to 0 (`P:\scripts\3_game\tools\input.c:27`). `GetGame().GetInput().SetDisabled(...)` does not compile: the `Input` class has no such method. `SetDisabled` is on `HumanInputController` (`P:\scripts\3_game\human.c:22`), reached through the player's `GetInputController()` (`:1458`), if you also need to freeze the character's own input.

**Key rules**:
1. Lock in Open, unlock in Close.
2. Unlock BEFORE hiding the panel to ensure UI state consistency.
3. Always unlock in destructor (if destroyed while open, prevent player getting stuck).
4. Test: open panel, press WASD — player should not move. Close panel — player moves again.

---

## Summary

These patterns solve:
- Visual glitches (color flashing, hover state persisting)
- Memory leaks (uncleaned collections, stale static references)
- Animation bugs (overlapping animations, not canceling previous)
- Input problems (getting stuck with UI focus locked)
- Performance issues (allocating temporary objects every frame)

Apply these patterns consistently across your UI controllers and views for stable, production-ready Enforce Script.

## DayZ 1.30: `DoOnce` and action UI

`class DoOnce` (`P:\scripts\3_game\doonce.c:1`) is a process-wide "run this reflected method once per key". `DoOnce.Run(string key, Class target, string fnName, Param params = null)` (`:12`) sets the key then `g_Game.GameScript.CallFunctionParams`. Use it for one-shot init, not as a per-frame debounce (that is still the single tick manager of timer rule 23 in `hard-rules.md`). `HasRun` / `Clear` at `:30` / `:37`.

Action HUD (not Dabs): vanilla can **show** an action whose `CanBeStarted()` is false (info panels, `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18-21`). The client manager will not `ActionStart` it: it tests `CanBeStarted()` first (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336-337`). Do not treat "visible on the cursor" as "F will run". Gate client-only presentation on `DayZPlayer.IsFirstRenderFrame()` (`P:\scripts\3_game\dayzplayer.c:1186-1189`) when the sim ticks more than once per render frame.
