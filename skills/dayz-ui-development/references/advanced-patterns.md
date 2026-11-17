# Advanced UI patterns: stacking, toggles, tabs, drag, status bars, hover, input fields

Worked layout and script sketches for interactive UI: keeping widgets from overlapping when visibility changes, a sliding toggle, a clickability checklist, cards, tabs, a draggable window, a fading status bar, hover effects and validated input fields.

**Read this first: the code here is pseudocode until you check it.** The file came with no source citations, and an audit of it against the vanilla scripts found calls that do not exist. Three are confirmed broken and are left in the sketches so the correction stays visible:

1. **`OnMouseMove(Widget w, int x, int y, int oldx, int oldy)`** (section 6, the draggable window). `ScriptedWidgetEventHandler` has no `OnMouseMove` event: its full list is `OnClick` to `OnEvent` at `P:\scripts\1_core\proto\enwidgets.c:656-686`. The override is never called, so dragging silently does nothing. Reported by the source for DayZ 1.29 and not checked here (only 1.30 is on `P:\`): the one `OnMouseMove` in the 1.29 scripts was a Workbench plugin hook (`workbenchapi.c:91`), not a widget event. **Fix:** drive the drag from `OnMouseButtonDown` plus a per frame `Update()` that polls `GetMousePos()` (the approach `admin-ui-patterns.md` section 1 uses), or use the native `DRAGGABLE` flag with the `OnDrag`, `OnDragging` and `OnDrop` events.
2. **`Dabs_WidgetAnimator.Create(w).AnimateProperty(...)` and `.AnimateColor(...)`** (sections 2, 7 and 8). No such class or factory exists in Dabs Framework. The real calls are static methods on `WidgetAnimator`: `WidgetAnimator.Animate(w, WidgetAnimatorProperty.POSITION_Y, end, ms)`, `AnimateEx` and `AnimateColor` (see `dabs-framework.md`, "WidgetAnimator"). There is no `Dabs_` prefix and no `Create()`.
3. **`SetSort(SortOrderEnum.LOWER)` and `GetUApi().GetInputManager().AddActionListener(this)`** (sections 2 and 3). `SortOrderEnum` does not exist: `SetSort` takes a plain `int`, declared at `P:\scripts\1_core\proto\enwidgets.c:130`, and a higher value draws on top. `UAInputAPI` has no `GetInputManager()`. To read an input every frame use `GetUApi().GetInputByName("UAxxx").LocalPress()` (`GetInputByName` is declared at `P:\scripts\3_game\inputapi\uainput.c:218`). The action must be declared in `inputs.xml` and that file named in `config.cpp`, or `GetInputByName` returns null and the call crashes; see `skills/_shared/enscript/integrations/input_bindings.md`.

Also wrong in the sketches: several `ScriptView` examples use `m_root` (Dabs exposes `m_LayoutRoot` and `GetLayoutRoot()`) and override `OnShow()` on a class that `extends ScriptView` (Dabs `ScriptView` has no `OnShow`; that hook belongs to `UIScriptedMenu` and to Expansion's `ExpansionScriptViewMenu`). Rebuild the sketch on the vanilla `ScriptedWidgetEventHandler` and `UIScriptedMenu` calls before copying it.

Everything else in this file is vendored, not yet checked on `P:\`. Rule numbers ("rule 3") point at `rules-and-checklist.md` in this folder.

---

## Contents

- [1. Anti-overlap strategy: dynamic Y stacking](#1-anti-overlap-strategy-dynamic-y-stacking)
- [2. Toggle switch pattern](#2-toggle-switch-pattern-eurbtc-selector)
- [3. Clickability debugging guide](#3-clickability-debugging-guide)
- [4. Card or info panel pattern](#4-card-or-info-panel-pattern)
- [5. Tab system pattern](#5-tab-system-pattern)
- [6. Floating draggable window pattern](#6-floating-draggable-window-pattern)
- [7. Status bar or notification pattern](#7-status-bar-or-notification-pattern)
- [8. Button with hover effect](#8-button-with-hover-effect)
- [9. Input field with validation](#9-input-field-with-validation)
- [10. Troubleshooting table](#10-troubleshooting-table)
- [Summary: design rules](#summary-design-rules)

## Overview

These are patterns for complex interactive UI elements. They target the most common failures: overlapping widgets, unclickable elements, visual glitches and animation problems.

**Key constraints:**
- Outside spacer widgets, layout positioning is absolute (there is no flexbox). `WrapSpacerWidgetClass` and `GridSpacerWidgetClass` place their own children, as section 1 shows
- Enforce Script has **no ternary operator** (the only confirmed restriction). `++`, `+=` and `foreach` all work (seen in LBmaster and LBGroups production code)
- All widgets render in tree order (later siblings on top)
- Mouse events propagate through `ignorepointer` flag

---

## 1. Anti-overlap strategy: dynamic Y stacking

**Problem:** Widgets overlap when content visibility changes dynamically. Without explicit recalculation, hidden widgets don't reduce layout space.

**Rule:** Calculate cumulative Y offsets for all positioned elements after ANY Show/Hide change.

### Pattern: Explicit Position Calculator

```c
// In your ViewController script:
void RecalculateLayout()
{
    float yPos = HEADER_HEIGHT;  // Start below header

    // Widget 1: conditional display
    if (m_HeaderWidget.IsVisible())
    {
        m_HeaderWidget.SetPos(MARGIN, yPos);
        float w, h;
        m_HeaderWidget.GetSize(w, h);
        yPos = yPos + h + SPACING;  // Advance by height + gap
    }

    // Widget 2: always visible, positioned after Widget 1
    m_ContentPanel.SetPos(MARGIN, yPos);
    float w2, h2;
    m_ContentPanel.GetSize(w2, h2);
    yPos = yPos + h2 + SPACING;

    // Widget 3: only if content has items
    if (m_ItemList.Count() > 0)
    {
        m_ListPanel.Show(true);
        m_ListPanel.SetPos(MARGIN, yPos);
        float w3, h3;
        m_ListPanel.GetSize(w3, h3);
        yPos = yPos + h3 + SPACING;
    }
    else
    {
        m_ListPanel.Show(false);  // Collapse completely
    }
}

// Call after every visibility or content change:
override void OnShow()
{
    super.OnShow();
    RecalculateLayout();
}

void OnItemsUpdated()
{
    // ... update list ...
    RecalculateLayout();  // Reflow layout after content change
}
```

**Call RecalculateLayout() in:**
- `OnShow()`
- `OnHide()`
- After calling `Show(bool)` or `Hide()` on any widget
- After changing array counts (items added/removed)
- In `ScriptView.OnBinding()` to initial-layout

### Alternative: WrapSpacer for Automatic Flow

For simpler layouts with many small items, use `WrapSpacerWidgetClass`:

```
ScrollWidgetClass ContentScroll {
    position 0 74
    size 720 490
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    {
        WrapSpacerWidgetClass ContentFlow {
            position 0 0
            size 720 0              // Height grows automatically
            hexactpos 1  vexactpos 1
            hexactsize 1  vexactsize 0  // vexactsize 0 = auto height
            {
                // Child items auto-flow vertically
                FrameWidgetClass Item1 { position 0 0  size 720 40 ... }
                FrameWidgetClass Item2 { position 0 0  size 720 40 ... }
                // More items...
            }
        }
    }
}
```

**Advantages:** Automatic Y positioning, scales with content.
**Disadvantage:** Less control over exact spacing.

---

## 2. Toggle switch pattern (EUR/BTC selector)

**Problem:** Simple checkbox or dropdown toggles look broken and are hard to click.

**Solution:** Animated slide toggle with two button areas and moving indicator.

### Layout Structure

```
FrameWidgetClass CurrencyToggle {
    position 12 126
    size 200 32
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    {
        // Background track (decorative, ignorepointer)
        ImageWidgetClass ToggleBg {
            position 0 0
            size 200 32
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            stretch 1
            ignorepointer 1
            { }
        }

        // Sliding indicator (moves when selected, ignorepointer)
        ImageWidgetClass ToggleIndicator {
            position 0 0              // Starts on left
            size 100 32               // Half width
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            stretch 1
            ignorepointer 1
            { }
        }

        // Left option button (clickable)
        ButtonWidgetClass OptionLeft {
            position 0 0
            size 100 32
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            {
                TextWidgetClass OptionLeftText {
                    position 0 0
                    size 1 1
                    hexactpos 0  vexactpos 0  hexactsize 0  vexactsize 0
                    font "gui/fonts/Metron"
                    "text halign" center
                    "text valign" center
                    text "EUR"
                    ignorepointer 1  // Text doesn't block clicks
                    { }
                }
            }
        }

        // Right option button (clickable)
        ButtonWidgetClass OptionRight {
            position 100 0            // Positioned on right half
            size 100 32
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            {
                TextWidgetClass OptionRightText {
                    position 0 0
                    size 1 1
                    hexactpos 0  vexactpos 0  hexactsize 0  vexactsize 0
                    font "gui/fonts/Metron"
                    "text halign" center
                    "text valign" center
                    text "BTC"
                    ignorepointer 1  // Text doesn't block clicks
                    { }
                }
            }
        }
    }
}
```

### Script: Animation and State

```c
class CurrencyToggleController extends ScriptView
{
    private ImageWidget m_ToggleIndicator;
    private TextWidget m_OptionLeftText;
    private TextWidget m_OptionRightText;
    private bool m_IsBtc = false;

    override void OnShow()
    {
        super.OnShow();
        m_ToggleIndicator = ImageWidget.Cast(m_root.FindAnyWidget("ToggleIndicator"));
        m_OptionLeftText = TextWidget.Cast(m_root.FindAnyWidget("OptionLeftText"));
        m_OptionRightText = TextWidget.Cast(m_root.FindAnyWidget("OptionRightText"));

        GetUApi().GetInputManager().AddActionListener(this);
    }

    override bool OnClick(Widget w, int x, int y, int button)
    {
        if (w.GetName() == "OptionLeft")
        {
            SelectCurrency(false);  // Select EUR
            return true;
        }
        if (w.GetName() == "OptionRight")
        {
            SelectCurrency(true);   // Select BTC
            return true;
        }
        return false;
    }

    void SelectCurrency(bool isBtc)
    {
        m_IsBtc = isBtc;

        // Animate slide: move indicator to match selected side
        float targetX = 0;
        if (isBtc)
            targetX = 100;  // Move to right half

        // Slide animation (200ms ease-out)
        Dabs_WidgetAnimator animator = Dabs_WidgetAnimator.Create(m_ToggleIndicator);
        animator.AnimateProperty(Dabs_WidgetAnimatorProperty.POSITION_X, targetX, 200, Dabs_WidgetAnimatorEasing.EASE_OUT_CUBIC);

        // Update text colors
        int activeColor = ARGB(255, 255, 255, 255);    // White
        int inactiveColor = ARGB(255, 128, 128, 128);  // Gray

        // No ternary in Enforce! Use if/else:
        int leftColor = inactiveColor;
        int rightColor = activeColor;
        if (!isBtc)
        {
            leftColor = activeColor;
            rightColor = inactiveColor;
        }

        m_OptionLeftText.SetColor(leftColor);
        m_OptionRightText.SetColor(rightColor);
    }
};
```

**Key points:**
- Buttons are exactly half the parent width (100px each)
- Indicator starts at position 0, animates to 100 when BTC is selected
- Text uses `ignorepointer 1` so clicks reach the button
- All colors updated without ternary operator
- Animation duration 200ms provides smooth but snappy feedback

---

## 3. Clickability debugging guide

### Checklist: Widget Not Responding to Clicks

1. **Check `ignorepointer 1` flag**
   - REMOVE from all interactive widgets (ButtonWidget, EditBoxWidget, etc.)
   - ONLY keep on decorative widgets (backgrounds, labels, separators)
   - Parent's `ignorepointer 1` blocks child clicks even if child doesn't have it

2. **Check widget visibility and size**
   - Is `visible 0` set anywhere? (Disables interaction completely)
   - Is `size` set to 0 0? Widget with zero area can't be clicked
   - Check all ancestors in tree for visibility

3. **Check overlapping widgets**
   - Widgets render in tree order: **later siblings render on top and catch clicks first**
   - Use `SetSort()` to reorder, or restructure the tree so interactive widget is last
   - Example:
     ```c
     // This background will block clicks on button:
     ImageWidget bg = ...;        // declared later in tree
     ButtonWidget btn = ...;      // declared earlier
     // FIX: Reorder tree OR call:
     bg.SetSort(SortOrderEnum.LOWER);
     ```

4. **Check handler registration**
   - For custom ScriptedWidgetEventHandler, call `SetHandler(this)` in OnShow()
   - ButtonWidget calls handler automatically, but custom classes need explicit registration
   - Verify `OnClick()` or `OnMouseButtonDown()` has correct signature:
     ```c
     override bool OnClick(Widget w, int x, int y, int button)
     override bool OnMouseButtonDown(Widget w, int x, int y, int button)
     ```

5. **Check game focus**
   - Without `ChangeGameFocus(1)` in the main UI class, mouse clicks go to game world, not UI
   - Verify focus is set when UI opens

6. **Check exact positioning**
   - `hexactpos 1 vexactpos 1` = exact coords from the parent, in units of 1/1080 of the screen
     height (rule 3, measured in game; corrected 2026-10-03: this said "exact pixel coords from parent")
   - `hexactpos 0 vexactpos 0` = fill parent (size 1 1 means full parent)
   - Mismatched pos/size can place widget outside clickable bounds

---

## 4. Card or info panel pattern

For self-contained info displays (ATM balance cards, status cards, inventory slots):

### Layout: Card Container

```
FrameWidgetClass CardPrice {
    position 12 46
    size 93 52
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    {
        // Background fill
        ImageWidgetClass CardPriceBg {
            position 0 0
            size 1 1
            hexactpos 0  vexactpos 0  hexactsize 0  vexactsize 0  // Fill parent
            stretch 1
            ignorepointer 1
            { }
        }

        // Label (top, small text)
        TextWidgetClass CardPriceLabel {
            position 8 4
            size 77 16
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            font "gui/fonts/MetronBook"
            "text halign" left
            "text valign" center
            ignorepointer 1
            { }
        }

        // Value (bottom, large text)
        TextWidgetClass CardPriceValue {
            position 8 24
            size 77 22
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            font "gui/fonts/Metron"
            "text halign" left
            "text valign" center
            ignorepointer 1
            { }
        }
    }
}
```

### Script: Populate Card Data

```c
void UpdatePriceCard(float currentPrice, float change)
{
    TextWidget label = TextWidget.Cast(m_root.FindAnyWidget("CardPriceLabel"));
    TextWidget value = TextWidget.Cast(m_root.FindAnyWidget("CardPriceValue"));

    label.SetText("Current Price");
    string priceStr = currentPrice.ToString();
    value.SetText(priceStr);

    // Color based on change direction
    int color = ARGB(255, 100, 200, 100);  // Green
    if (change < 0)
        color = ARGB(255, 200, 100, 100);  // Red

    value.SetColor(color);
}
```

**Key:**
- Parent FrameWidget is fixed size (93x52)
- Background uses `hexactsize 0 vexactsize 0` (fill) + `size 1 1` (full parent)
- Text uses `hexactsize 1 vexactsize 1` (exact units, 1/1080 of the screen height: rule 3;
  corrected 2026-10-03 from "(exact pixels)")
- All child widgets have `ignorepointer 1` (decorative)
- Optional: add click handler to parent for card interaction

---

## 5. Tab system pattern

For switchable tab content (ATM Cash/Account, Sorter output tabs):

### Layout: Tab Panel Container

```
FrameWidgetClass TabContainer {
    position 0 60
    size 400 300
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    {
        // Tab buttons (horizontal bar)
        FrameWidgetClass TabButtonBar {
            position 0 0
            size 400 32
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            {
                ButtonWidgetClass TabBtnCash {
                    position 0 0
                    size 200 32
                    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
                    {
                        TextWidgetClass { text "Cash" ignorepointer 1 ... }
                    }
                }
                ButtonWidgetClass TabBtnAccount {
                    position 200 0
                    size 200 32
                    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
                    {
                        TextWidgetClass { text "Account" ignorepointer 1 ... }
                    }
                }
            }
        }

        // Content panels (stacked, only one visible)
        FrameWidgetClass CashPanel {
            position 0 32
            size 400 268
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            visible 1
            {
                // Content widgets for Cash tab
            }
        }
        FrameWidgetClass AccountPanel {
            position 0 32
            size 400 268
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            visible 0  // Hidden by default
            {
                // Content widgets for Account tab
            }
        }
    }
}
```

### Script: Tab Switching

```c
class TabController extends ScriptView
{
    private FrameWidget m_CashPanel;
    private FrameWidget m_AccountPanel;
    private int m_ActiveTab = 0;  // 0 = Cash, 1 = Account

    override void OnShow()
    {
        super.OnShow();
        m_CashPanel = FrameWidget.Cast(m_root.FindAnyWidget("CashPanel"));
        m_AccountPanel = FrameWidget.Cast(m_root.FindAnyWidget("AccountPanel"));
    }

    override bool OnClick(Widget w, int x, int y, int button)
    {
        if (w.GetName() == "TabBtnCash")
        {
            SelectTab(0);
            return true;
        }
        if (w.GetName() == "TabBtnAccount")
        {
            SelectTab(1);
            return true;
        }
        return false;
    }

    void SelectTab(int index)
    {
        m_ActiveTab = index;

        // Show/hide content panels
        bool showCash = (index == 0);
        bool showAccount = (index == 1);
        m_CashPanel.Show(showCash);
        m_AccountPanel.Show(showAccount);

        // Visual feedback on tab buttons (highlight active)
        int inactiveColor = ARGB(255, 40, 40, 45);
        int activeColor = ARGB(255, 60, 60, 70);

        // Get button backgrounds (if they have them)
        Widget cashBtn = m_root.FindAnyWidget("TabBtnCash");
        Widget acctBtn = m_root.FindAnyWidget("TabBtnAccount");

        int cashColor = inactiveColor;
        int acctColor = inactiveColor;
        if (index == 0)
            cashColor = activeColor;
        if (index == 1)
            acctColor = activeColor;

        // Update colors (assumes buttons have background image named "BtnBg")
        ImageWidget cashBg = ImageWidget.Cast(cashBtn.FindWidget("BtnBg"));
        ImageWidget acctBg = ImageWidget.Cast(acctBtn.FindWidget("BtnBg"));
        if (cashBg) cashBg.SetColor(cashColor);
        if (acctBg) acctBg.SetColor(acctColor);
    }
};
```

---

## 6. Floating draggable window pattern

For movable windows (LFPG Sorter container, modal dialogs):

### Layout: Window Frame with Header

```
FrameWidgetClass SorterWindow {
    position 100 100
    size 600 400
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    {
        // Draggable header
        FrameWidgetClass WindowHeader {
            position 0 0
            size 600 32
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            {
                ImageWidgetClass HeaderBg {
                    position 0 0
                    size 1 1
                    hexactpos 0  vexactpos 0  hexactsize 0  vexactsize 0
                    stretch 1
                    ignorepointer 0  // Header MUST be clickable
                    { }
                }
                TextWidgetClass WindowTitle {
                    position 8 8
                    size 500 16
                    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
                    font "gui/fonts/Metron"
                    text "Sorter"
                    ignorepointer 1
                    { }
                }
            }
        }

        // Content area
        FrameWidgetClass WindowContent {
            position 0 32
            size 600 368
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            {
                // Content widgets...
            }
        }
    }
}
```

### Script: Drag Handler

```c
class DraggableWindowController extends ScriptView
{
    private FrameWidget m_SorterWindow;
    private FrameWidget m_WindowHeader;
    private float m_DragOffsetX;
    private float m_DragOffsetY;
    private bool m_IsDragging = false;

    override void OnShow()
    {
        super.OnShow();
        m_SorterWindow = FrameWidget.Cast(m_root);
        m_WindowHeader = FrameWidget.Cast(m_root.FindAnyWidget("WindowHeader"));
    }

    override bool OnMouseButtonDown(Widget w, int x, int y, int button)
    {
        if (w == m_WindowHeader)
        {
            m_IsDragging = true;

            // Store offset between click point and window position
            float wndX, wndY;
            m_SorterWindow.GetPos(wndX, wndY);
            m_DragOffsetX = wndX - x;
            m_DragOffsetY = wndY - y;

            return true;  // Consume event
        }
        return false;
    }

    override bool OnMouseMove(Widget w, int x, int y, int oldx, int oldy)
    {
        if (m_IsDragging)
        {
            // Move window with mouse, maintaining offset
            float newX = x + m_DragOffsetX;
            float newY = y + m_DragOffsetY;

            // Clamp to screen bounds
            float screenW, screenH;
            GetScreenSize(screenW, screenH);
            if (newX < 0) newX = 0;
            if (newY < 0) newY = 0;
            if (newX + 600 > screenW) newX = screenW - 600;
            if (newY + 400 > screenH) newY = screenH - 400;

            m_SorterWindow.SetPos(newX, newY);
            return true;
        }
        return false;
    }

    override bool OnMouseButtonUp(Widget w, int x, int y, int button)
    {
        if (m_IsDragging)
        {
            m_IsDragging = false;
            return true;
        }
        return false;
    }
};
```

**Key:**
- Header must NOT have `ignorepointer 1` (needs to capture clicks)
- Store offset on MouseDown to smooth dragging
- Clamp position to screen bounds to prevent window leaving viewport

---

## 7. Status bar or notification pattern

For temporary status messages with fade-out (ATM feedback, transaction complete):

### Layout: Status Bar

```
FrameWidgetClass StatusBar {
    position 0 0
    size 400 40
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    visible 0
    {
        ImageWidgetClass StatusBg {
            position 0 0
            size 1 1
            hexactpos 0  vexactpos 0  hexactsize 0  vexactsize 0
            stretch 1
            ignorepointer 1
            { }
        }
        TextWidgetClass StatusText {
            position 8 12
            size 384 16
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            font "gui/fonts/Metron"
            "text halign" center
            "text valign" center
            ignorepointer 1
            { }
        }
    }
}
```

### Script: Show/Hide with Fade

```c
class StatusNotifier extends ScriptView
{
    private FrameWidget m_StatusBar;
    private TextWidget m_StatusText;
    private ImageWidget m_StatusBg;

    override void OnShow()
    {
        super.OnShow();
        m_StatusBar = FrameWidget.Cast(m_root.FindAnyWidget("StatusBar"));
        m_StatusText = TextWidget.Cast(m_root.FindAnyWidget("StatusText"));
        m_StatusBg = ImageWidget.Cast(m_root.FindAnyWidget("StatusBg"));
        m_StatusBar.Show(false);  // Hidden by default
    }

    void ShowStatus(string text, int color)
    {
        // Set text and color
        m_StatusText.SetText(text);
        m_StatusText.SetColor(color);
        m_StatusBar.Show(true);

        // Fade in (animate alpha from 0 to 1)
        Dabs_WidgetAnimator animator = Dabs_WidgetAnimator.Create(m_StatusBg);
        animator.AnimateProperty(Dabs_WidgetAnimatorProperty.COLOR_A, 1.0, 200);

        // Auto-hide after 3 seconds
        GetGame().GetCallQueue(CALL_CATEGORY_GUI).CallLater(this, "HideStatus", 3000, false);
    }

    void HideStatus()
    {
        // Fade out (animate alpha from current to 0)
        Dabs_WidgetAnimator animator = Dabs_WidgetAnimator.Create(m_StatusBg);
        animator.AnimateProperty(Dabs_WidgetAnimatorProperty.COLOR_A, 0.0, 500);

        // Hide widget after fade completes
        GetGame().GetCallQueue(CALL_CATEGORY_GUI).CallLater(this, "HideStatusImmediate", 500, false);
    }

    void HideStatusImmediate()
    {
        m_StatusBar.Show(false);
    }
};
```

---

## 8. Button with hover effect

Reported by the source: a `ButtonWidget` shows no hover state unless its style defines one, so hover feedback is done in event handlers (the vanilla pause menu tints a child panel from script the same way, see `text-sizing-and-rendering.md`):

### Script: Hover Animation

```c
override bool OnMouseEnter(Widget w, int x, int y)
{
    // Lighten background on hover
    ImageWidget btnBg = ImageWidget.Cast(w.FindWidget("BtnBg"));
    if (btnBg)
    {
        int hoverColor = ARGB(255, 70, 70, 80);
        Dabs_WidgetAnimator animator = Dabs_WidgetAnimator.Create(btnBg);
        animator.AnimateColor(hoverColor, 150);
    }
    return false;  // Don't consume — let parent handle
}

override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
{
    // OnMouseLeave has 4 params (w, enterW, x, y).
    // This is asymmetric with OnMouseEnter's 3 params.
    // Wrong signature = silent failure.

    // Darken background on leave
    ImageWidget btnBg = ImageWidget.Cast(w.FindWidget("BtnBg"));
    if (btnBg)
    {
        int normalColor = ARGB(255, 45, 45, 55);
        Dabs_WidgetAnimator animator = Dabs_WidgetAnimator.Create(btnBg);
        animator.AnimateColor(normalColor, 150);
    }
    return false;
}
```

`OnMouseLeave` takes four parameters, `(Widget w, Widget enterW, int x, int y)` (`P:\scripts\1_core\proto\enwidgets.c:666`). With three, the method is a different overload and is never called.

---

## 9. Input field with validation

For numeric inputs (BTC ATM amount, price fields) with cross-calculation:

### Layout: Input Field

```
FrameWidgetClass AmountInput {
    position 0 0
    size 200 24
    hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
    {
        ImageWidgetClass InputBg {
            position 0 0
            size 1 1
            hexactpos 0  vexactpos 0  hexactsize 0  vexactsize 0
            stretch 1
            ignorepointer 1
            { }
        }
        EditBoxWidgetClass EditBtcAmount {
            position 4 4
            size 192 16
            hexactpos 1  vexactpos 1  hexactsize 1  vexactsize 1
            font "gui/fonts/Metron"
            "text halign" left
            "text valign" center
            { }
        }
    }
}
```

### Script: Validation and Cross-Calculation

```c
class AmountInputController extends ScriptView
{
    private EditBoxWidget m_EditBtcAmount;
    private EditBoxWidget m_EditEurAmount;
    private float m_BtcPrice = 45000.0;
    private float m_MaxBtc = 10.0;

    override void OnShow()
    {
        super.OnShow();
        m_EditBtcAmount = EditBoxWidget.Cast(m_root.FindAnyWidget("EditBtcAmount"));
        m_EditEurAmount = EditBoxWidget.Cast(m_root.FindAnyWidget("EditEurAmount"));
    }

    override bool OnChange(Widget w, int x, int y, bool finished)
    {
        if (w == m_EditBtcAmount)
        {
            string raw = m_EditBtcAmount.GetText();

            // Parse float (Enforce: no float(), use ToFloat())
            float val = raw.ToFloat();

            // Validate: clamp to range
            if (val < 0)
                val = 0;
            if (val > m_MaxBtc)
                val = m_MaxBtc;

            // Cross-calculate EUR equivalent
            float eurVal = val * m_BtcPrice;
            string eurStr = eurVal.ToString();
            m_EditEurAmount.SetText(eurStr);

            return true;
        }

        if (w == m_EditEurAmount)
        {
            string raw = m_EditEurAmount.GetText();
            float val = raw.ToFloat();

            // Reverse: EUR to BTC
            float btcVal = val / m_BtcPrice;
            if (btcVal < 0) btcVal = 0;
            if (btcVal > m_MaxBtc) btcVal = m_MaxBtc;

            string btcStr = btcVal.ToString();
            m_EditBtcAmount.SetText(btcStr);

            return true;
        }

        return false;
    }
};
```

---

## 10. Troubleshooting table

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Widget not clickable | `ignorepointer 1` on widget or parent | Remove from interactive widgets; only use on decorative elements |
| Text overlaps content below | No `RecalculateLayout()` after Show/Hide | Call `RecalculateLayout()` after visibility changes |
| Button doesn't fire OnClick | Missing `SetHandler(this)` or custom handler | Check handler registration; verify OnClick signature has 4 params |
| Colors look wrong or dark | The player's HUD brightness setting, applied globally by vanilla | Design against it. Never call `Widget.SetLV(0)`: it is `proto static` and overwrites the player's setting (`SetHudBrightness` at `P:\scripts\3_game\dayzgame.c:3910-3914`) |
| OnMouseLeave never fires | Wrong param count (3 instead of 4) | Use 4 params: `OnMouseLeave(Widget w, Widget enterW, int x, int y)` |
| Scroll doesn't work | No content widget inside ScrollWidget | Add WrapSpacerWidgetClass or GridSpacerWidgetClass as child |
| Animation jumps instead of smooth | animPeriod too small (< 100ms) | Use 200-500ms duration with appropriate easing |
| EditBox text invisible | Text color same as background or not set | Set text color explicitly in layout or script: `SetColor(ARGB(...))` |
| Widget size 0x0 (not visible) | `hexactsize 0 vexactsize 0` with `size 1 1` misuse | Verify exact size values match intended dimensions |
| Later siblings block clicks | Widget tree order (later renders on top) | Reorder the tree or call `SetSort` with a lower `int` (the `SortOrderEnum` in the section 3 sketch does not exist) |
| Parent blocks child clicks | Parent has `ignorepointer 1` but child doesn't | Parent's flag blocks even if child is interactive |
| Window dragging stutters | Drag offset calculation wrong | Recalculate offset at each move: `currentPos - mouseX` |
| Tab switching doesn't hide old content | `Show(false)` not called on previous tab | Explicitly hide all non-active tabs in `SelectTab()` |
| Status message fades wrong | Fade duration not matched to auto-hide delay | Ensure fade-out duration (500ms) << auto-hide timeout (3000ms) |

---

## Summary: design rules

1. **All positioning is absolute.** Calculate Y offsets explicitly for dynamic layouts.
2. **Later widgets render on top.** Interactive widgets must be last in tree or use `SetSort()`.
3. **`ignorepointer` blocks clicks.** Use ONLY on decorative elements.
4. **Enforce Script has no ternary.** Use if/else for conditional values.
5. **OnMouseLeave has 4 params.** Wrong count = silent failure.
6. **Call `RecalculateLayout()` after changes.** Don't rely on automatic reflow.
7. **Animate with WidgetAnimator for smoothness.** Direct position/color changes look jerky.
8. **Test overlap at different resolutions.** Screen size affects card layouts.
