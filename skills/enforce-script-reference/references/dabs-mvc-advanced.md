# Dabs Framework MVC — Advanced Patterns & Gotchas

Patterns and traps for the third-party Dabs Framework's MVC classes, as met in shipped mods. They describe that framework and are not yet checked on `P:\` or against the Dabs source. What was read in the Dabs source is in `skills/_shared/enscript/integrations/dabs_framework.md`; the full UI material is in the `dayz-ui-development` skill.

## Architecture Overview

Dabs MVC provides data-binding UI for DayZ:
- **ViewController** — data model with bound properties
- **ScriptView** — view + event handler, creates widgets from layout
- **ViewBinding** (scriptclass in layout) — auto-binds widget to controller property
- **Relay_Command** (ScriptParams in layout) — routes button clicks to controller methods
- **ObservableCollection** — data-bound list of ScriptView items
- **Two_Way_Binding** — bidirectional binding (e.g., EditBox ↔ property)
- **NotifyPropertyChanged** — triggers UI update from controller

---

## Critical gotchas, met in production

### 1. NotifyPropertyChanged with a string literal (unconfirmed failure)

```
// Seen to fail in one mod (not reproduced, not checked against the Dabs source)
ctrl.NotifyPropertyChanged("HeaderTitle");

// Fallback if the literal form fails in your build
string propName = "HeaderTitle";
ctrl.NotifyPropertyChanged(propName);
```

A literal is valid Enforce Script: syntax rule 5 in `hard-rules.md` says string literals as function arguments work, vanilla passes them everywhere (`RegisterNetSyncVariableBool("m_EM.m_IsSwichedOn")`, `P:\scripts\3_game\entities\entityai.c:218`), and the Dabs integration file named above calls `NotifyPropertyChanged("FieldName")` with a literal. Write the literal, and use the local variable only if a literal fails in your own build.

### 2. ScriptView Constructor Calls CreateWidgets

`new ScriptView()` internally calls `CreateWidgets()` which needs a valid `WorkspaceWidget`. This means:

- **never** instantiate ScriptView from RPC context (no workspace available)
- **never** instantiate during early init before workspace exists
- **Pre-create** in `MissionGameplay.OnInit()`, then show/hide

```
// CRASH
void OnRPC(...)
{
    m_View = new MyMod_SorterView();  // CreateWidgets fails → crash
}

// CORRECT
override void OnInit()
{
    m_View = new MyMod_SorterView();  // workspace available here
}
```

### 3. Auto-Bind Fails Inside ButtonWidget Children

Dabs MVC auto-bind looks up widgets by name matching controller properties. **But**: for widgets nested inside a `ButtonWidget`, auto-bind and `FindAnyWidget` can return incorrect (non-null) references.

```
// In layout:
ButtonWidgetClass TabOut0 {
    {
        ImageWidgetClass TabOut0Bg { ... }   // auto-bind may get wrong ref
        TextWidgetClass TabOut0Text { ... }  // auto-bind may get wrong ref
    }
}

// SOLUTION — manual child-walk after auto-bind
ImageWidget FindBtnChildBg(Widget root, string btnName)
{
    Widget btn = root.FindAnyWidget(btnName);
    if (!btn)
        return null;

    Widget child = btn.GetChildren();
    while (child)
    {
        ImageWidget img = ImageWidget.Cast(child);
        if (img)
            return img;
        child = child.GetSibling();
    }
    return null;
}

TextWidget FindBtnChildText(Widget root, string btnName)
{
    Widget btn = root.FindAnyWidget(btnName);
    if (!btn)
        return null;

    Widget child = btn.GetChildren();
    while (child)
    {
        TextWidget txt = TextWidget.Cast(child);
        if (txt)
            return txt;
        child = child.GetSibling();
    }
    return null;
}
```

Call these in an `EnsureBindings()` method after view creation to overwrite any incorrect auto-binds.

### 4. Relay_Command Double-Fire

Dabs ScriptView.OnClick processes Relay_Command internally. If you also override OnClick and call `super.OnClick()`, the button handler fires twice.

For toggle-based actions (tab selection, checkbox), double-fire means the action cancels itself out — appearing to do nothing.

```
// SOLUTION — intercept in OnClick, dispatch directly, return true
override bool OnClick(Widget w, int x, int y, int button)
{
    if (!m_IsOpen || !w || button != 0)
    {
        return super.OnClick(w, x, y, button);
    }

    // Walk up to find enclosing ButtonWidget
    Widget check = w;
    ButtonWidget btn = null;
    while (check)
    {
        btn = ButtonWidget.Cast(check);
        if (btn)
            break;
        check = check.GetParent();
    }
    if (!btn)
        return super.OnClick(w, x, y, button);

    string bName = btn.GetName();
    MyMod_SorterController ctrl = MyMod_SorterController.Cast(GetController());
    if (!ctrl)
        return super.OnClick(w, x, y, button);

    // Direct dispatch — bypasses Relay_Command, no double-fire
    string nTab0 = "TabOut0";
    if (bName == nTab0) { ctrl.TabOut0(); return true; }
    // ... more buttons ...

    // Unknown button → delegate to base for Relay_Command
    return super.OnClick(w, x, y, button);
}
```

### 5. ObservableCollection Circular Reference Leak

When ObservableCollection items (ScriptView) hold a back-reference to the parent controller, clearing the collection doesn't break the cycle.

```
// THE CYCLE:
// Controller → TagsList (ObservableCollection)
//   → TagView (ScriptView)
//     → TagController → m_OwnerController → Controller  ← CYCLE

// SOLUTION — break in item destructor
void ~MyMod_SorterTagView()
{
    MyMod_SorterTagController ctrl = MyMod_SorterTagController.Cast(GetController());
    if (ctrl)
    {
        ctrl.m_OwnerController = null;  // break cycle
    }
}
```

### 6. ObservableCollection Parent Chain Broken

ObservableCollection items sometimes lose their parent reference when callbacks fire. Don't traverse parent chain from collection items — pass the controller reference directly.

```
// WRONG — parent traversal
void OnItemClick()
{
    ScriptView parent = ScriptView.Cast(GetParent());  // may be null
    // ...
}

// CORRECT — direct reference passed at creation
void SetData(..., MyMod_SorterController ownerCtrl)
{
    ctrl.m_OwnerController = ownerCtrl;  // direct ref
}
```

### 7. scriptclass on Root Widget Causes Double Controller

In the layout file, if the root widget has `scriptclass "ViewBinding"` and the ScriptView's `GetControllerType()` returns a controller typename, Workbench creates two controller instances.

```
// WRONG — layout root has scriptclass
FrameWidgetClass SorterRoot {
    scriptclass "ViewBinding"   // ← REMOVE THIS
    ...
}

// CORRECT — ScriptView handles controller creation via GetControllerType()
FrameWidgetClass SorterRoot {
    size 1 1
    ...
}
```

---

## Floating Window Pattern (No ModalOverlay)

For draggable windows that don't block the entire screen:

### Input Locking (Cursor Only, Not Full Modal)

```
void DoOpen()
{
    // Lock game input, show cursor
    Input inp = GetGame().GetInput();
    if (inp)
    {
        inp.ChangeGameFocus(1);
    }
    UIManager uiMgr = GetGame().GetUIManager();
    if (uiMgr)
    {
        uiMgr.ShowUICursor(true);
    }
    m_FocusLocked = true;

    // Disable player actions (prevent shooting, eating, etc.)
    PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
    if (player)
    {
        HumanInputController hic = player.GetInputController();
        if (hic)
        {
            hic.SetDisabled(true);
        }
    }

    // Do not use INPUT_EXCLUDE_ALL or ModalOverlay
    // Do not use PlayerControlDisable (deprecated, causes issues)
}

void DoClose()
{
    // Reverse in EXACT opposite order
    PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
    if (player)
    {
        HumanInputController hic = player.GetInputController();
        if (hic)
        {
            hic.SetDisabled(false);
        }
    }

    UIManager uiMgr = GetGame().GetUIManager();
    if (uiMgr)
    {
        uiMgr.ShowUICursor(false);
    }

    Input inp = GetGame().GetInput();
    if (inp)
    {
        inp.ChangeGameFocus(-1);
    }
    m_FocusLocked = false;
}
```

### Drag Implementation

```
override bool OnMouseButtonDown(Widget w, int x, int y, int button)
{
    if (button != 0)
        return false;

    // Only drag from header area
    if (w == HeaderFrame || w == HeaderBg)
    {
        m_Dragging = true;
        float panelX;
        float panelY;
        SorterPanel.GetScreenPos(panelX, panelY);
        m_DragOffX = x - panelX;
        m_DragOffY = y - panelY;
        return true;
    }
    return false;
}

override bool OnMouseButtonUp(Widget w, int x, int y, int button)
{
    if (button == 0 && m_Dragging)
    {
        m_Dragging = false;
        return true;
    }
    return false;
}

// In Update(float dt):
if (m_Dragging)
{
    int mx;
    int my;
    GetMousePos(mx, my);
    float newX = mx - m_DragOffX;
    float newY = my - m_DragOffY;
    SorterPanel.SetPos(newX, newY);
}
```

### Destructor Safety

Always release input in destructor — view can be destroyed while open:

```
void ~MyMod_SorterView()
{
    if (GetGame())
    {
        PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
        if (player)
        {
            HumanInputController hic = player.GetInputController();
            if (hic)
            {
                hic.SetDisabled(false);
            }
        }

        if (m_FocusLocked)
        {
            Input inp = GetGame().GetInput();
            if (inp)
            {
                inp.ChangeGameFocus(-1);
            }
            UIManager uiMgr = GetGame().GetUIManager();
            if (uiMgr)
            {
                uiMgr.ShowUICursor(false);
            }
            m_FocusLocked = false;
        }
    }
}
```

---

## Color System for DayZ (30-50% Darker)

DayZ renders UI colors 30-50% darker than browser. Define all colors as constants with compensation:

```
// Color constants (ARGB format, compensated for DayZ gamma)
static const int COL_BG         = 0xEB1E1E1E;  // dark background
static const int COL_HEADER     = 0xF0252A36;  // header
static const int COL_BTN        = 0xFF253550;  // button normal
static const int COL_BTN_HOVER  = 0xFF304060;  // button hover (+30%)
static const int COL_TEXT       = 0xFFB0C0D0;  // primary text
static const int COL_TEXT_MID   = 0xFF8090A0;  // secondary text
static const int COL_SEPARATOR  = 0x30FFFFFF;  // separator (alpha 0x30 minimum!)
static const int COL_GREEN      = 0xFF4ADE80;  // accent green
static const int COL_RED        = 0xFFF87171;  // warning red

// Alpha below 0x30 (48/255) is invisible in DayZ
// Alpha below 0x14 (20/255) is guaranteed invisible
```

### Applying Colors in Script

```
static const string PROC_WHITE = "#(argb,8,8,3)color(1,1,1,1,CO)";

void ApplyColors()
{
    if (PanelBg)
    {
        string tex = PROC_WHITE;
        PanelBg.LoadImageFile(0, tex);
        PanelBg.SetColor(COL_BG);
    }
}
```

---

## Hover System Pattern

For button hover effects without Dabs-native hover support:

```
// Cache button backgrounds and their colors on open
ref array<Widget> m_CacheWidgets;
ref array<int> m_CacheColors;
Widget m_HoveredBg;

// In OnMouseEnter: find enclosing button, highlight its Bg
override bool OnMouseEnter(Widget w, int x, int y)
{
    // Walk up to ButtonWidget
    Widget check = w;
    ButtonWidget btn = null;
    while (check)
    {
        btn = ButtonWidget.Cast(check);
        if (btn)
            break;
        check = check.GetParent();
    }
    if (!btn)
        return false;

    // Find the Bg child of this button
    ImageWidget bg = FindBtnChildBg(GetLayoutRoot(), btn.GetName());
    if (bg && bg != m_HoveredBg)
    {
        // Restore previous hover
        if (m_HoveredBg)
        {
            RestoreColor(m_HoveredBg);
        }
        m_HoveredBg = bg;
        bg.SetColor(COL_BTN_HOVER);
    }
    return false;
}

// Note: OnMouseLeave has 4 parameters (asymmetric with OnMouseEnter's 3)
override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
{
    if (m_HoveredBg)
    {
        RestoreColor(m_HoveredBg);
        m_HoveredBg = null;
    }
    return false;
}
```

---

## Resolution Scaling Pattern

DayZ UI is designed for 1080p. For other resolutions, scale dynamically:

```
class MyMod_UIScaler
{
    static float ComputeScale()
    {
        int screenW;
        int screenH;
        GetScreenSize(screenW, screenH);
        float scale = screenH / 1080.0;
        return scale;
    }

    static void ScaleWidget(Widget w, float scale)
    {
        if (!w)
            return;
        // Skip if already at ~1.0 (1080p)
        float diff = scale - 1.0;
        if (diff < 0.0)
            diff = -diff;
        if (diff < 0.01)
            return;

        float ww;
        float wh;
        w.GetSize(ww, wh);
        ww = ww * scale;
        wh = wh * scale;
        w.SetSize(ww, wh);
    }
}
```
