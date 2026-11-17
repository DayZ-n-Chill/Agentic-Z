# Admin UI patterns: floating windows, ESP overlays, extended widget calls

Patterns for admin style tools: resizable floating windows, world to screen labels, skeleton drawing on a `CanvasWidget`, box selection, runtime scaling to the screen, a numpad menu, an orbit camera preview and looking around with a menu open.

**How facts are marked here.** The patterns are not yet checked on `P:\` or in game: treat each code block as a sketch and check every call before you copy it. Names that start with `LB` (`LBWidgetUtils`, `LBAdminMenuFrame`, `LBGapHandler`) are helper classes of the sketches that you write yourself, not vanilla. The vanilla calls the sketches lean on were checked on `P:\` (DayZ 1.30):

- `SetSort(int sort, bool immedUpdate = true)` is at `P:\scripts\1_core\proto\enwidgets.c:130`, `SetScreenPos` and `SetScreenSize` at `P:\scripts\1_core\proto\enwidgets.c:142-143`, and `SetRotation(float roll, float pitch, float yaw, ...)` at `P:\scripts\1_core\proto\enwidgets.c:146`.
- `GetWidgetUnderCursor()`, `CancelWidgetDragging()` and `GetDragWidget()` are global functions at `P:\scripts\1_core\proto\enwidgets.c:184-186`. `GetMousePos(out int x, out int y)` and the global `GetScreenSize(out int x, out int y)` are at `P:\scripts\1_core\proto\ensystem.c:329-331`, and `GetMouseState(MouseState index)` at `P:\scripts\1_core\proto\ensystem.c:326`.
- `CanvasWidget` (`DrawLine`, `Clear`) is at `P:\scripts\1_core\proto\enwidgets.c:341-345`.
- `SliderWidget` is at `P:\scripts\1_core\proto\enwidgets.c:358-367`, `XComboBoxWidget` at `P:\scripts\1_core\proto\enwidgets.c:407-416`, `BaseListboxWidget` at `P:\scripts\1_core\proto\enwidgets.c:425-433` and `TextListboxWidget` at `P:\scripts\1_core\proto\enwidgets.c:439-458`.
- `PlayerPreviewWidget` (`UpdateItemInHands`, `SetPlayer`, `GetDummyPlayer`, `Refresh`) is at `P:\scripts\3_game\gameplay.c:305-313`.
- `GetScreenPos(vector world_pos)` is at `P:\scripts\3_game\global\game.c:963`, `SceneGetEntitiesInBox` at `P:\scripts\4_world\entities\dayzplayerutils.c:75`, `GetBonePositionWS(int pivot)` at `P:\scripts\3_game\entities\object.c:238` and the player's `GetBoneIndexByName(string pBoneName)` at `P:\scripts\3_game\human.c:1417`.
- `MissionGameplay` overrides `OnKeyPress(int key)` at `P:\scripts\5_mission\mission\missiongameplay.c:742` and handles `WindowsResizeEventTypeID` at `P:\scripts\5_mission\mission\missiongameplay.c:788`. `RemoveActiveInputExcludes` and `AddActiveInputExcludes` are declared on `Mission` at `P:\scripts\3_game\gameplay.c:798-800`, and `ShowUICursor(bool visible)` at `P:\scripts\3_game\tools\uimanager.c:244`.

Rule numbers below ("rule 3") point at `rules-and-checklist.md` in this folder.

---

## Contents

- [1. Resizable floating window system](#1-resizable-floating-window-system)
- [2. ESP: world to screen every frame](#2-esp-world-to-screen-every-frame)
- [3. Skeleton rendering on a CanvasWidget](#3-skeleton-rendering-on-a-canvaswidget)
- [4. Box selection](#4-box-selection)
- [5. Widget calls, extended](#5-widget-calls-extended)
- [6. Scaling to the screen resolution](#6-scaling-to-the-screen-resolution)
- [7. PIN and numpad menu](#7-pin-and-numpad-menu)
- [8. Camera preview in a menu](#8-camera-preview-in-a-menu)
- [9. Looking around without closing the menu](#9-looking-around-without-closing-the-menu)

## 1. Resizable floating window system

IDE like windowing with drag, resize from every edge, pin to stay and z priority:

**Architecture:**
- `LBAdminMenuFrame` base class — one per panel (PlayerInfo, ESP, ItemSpawner, etc)
- Each frame: own layout loaded into shared frame container with header/resize handles
- `LBAdminMenuMain` registers frames by classname → `typename.Spawn()` instantiation
- Frame order user-configurable via drag & drop with persistent save

**Resize from 8 edges/corners:**
```
// Detect which edge is under cursor
if (LBWidgetUtils.IsUnderMouse(resize_bottom_right)) { resizeBottom = true; resizeRight = true; }
// Per-frame update:
if (resizeBottom) {
    int diffY = dragStartY - mouseY;
    dragStartY = mouseY;
    float w, h;
    frame.GetScreenSize(w, h);
    frame.SetScreenSize(w, h - diffY);
}
// Clamp to min size + screen bounds
```

**Window persistence:**
- Save: position/size normalized by `heightScale` (DPI scaling)
- Restore: multiply by `heightScale` on load
- 9 preset slots: each stores all window positions/sizes → hotkey switch

**Z-priority:** `frame.SetSort(120)` for focused, `frame.SetSort(0)` for unfocused.
Exception: frames that hold a `MapWidget` or an `ItemPreviewWidget` get a lower sort (a workaround for a render bug; not checked in game).

---

## 2. ESP: world to screen every frame

Render labels for thousands of entities in world space:

```
// Setup: scan all entities
DayZPlayerUtils.SceneGetEntitiesInBox("0 -1000 0", Vector(mapSize, 10000, mapSize), allItems);

// Per frame:
vector camPos = g_Game.GetCurrentCameraPosition();
for (int i = 0; i < allItems.Count(); i++) {
    EntityAI item = allItems.Get(i);
    vector pos = item.GetPosition();

    // Use head bone for living entities
    PlayerBase pb = PlayerBase.Cast(item);
    if (pb) {
        int bone = pb.GetBoneIndexByName("Head");
        if (bone != -1) pos = pb.GetBonePositionWS(bone);
    }

    float distance = vector.Distance(pos, camPos);
    vector screen = g_Game.GetScreenPos(pos);

    if (screen[2] > 0 && screen[0] > 0 && screen[1] > 0) { // Behind camera check
        widget.SetScreenPos(screen[0], screen[1]);
        widget.Show(true);
        widget.SetSort(1000 - ((int)Math.Clamp(distance, 0, 1000))); // Nearer = higher z
        distanceText.SetText("(" + ((int)distance) + "m)");
    } else {
        widget.Show(false);
    }
}
```

**Entity registration pattern:**
- Each entity class (`ItemBase`, `PlayerBase`, `AnimalBase`, `ZombieBase`, `CarScript`, `BoatScript`) has modded constructor that adds to ESP if enabled
- `EEHealthLevelChanged` updates health indicator
- `EEItemLocationChanged` re-adds/removes when item moves to/from ground

---

## 3. Skeleton rendering on a CanvasWidget

```
CanvasWidget canvas; // Cleared each frame with canvas.Clear()

void DrawBones(PlayerBase player, int thickness, TStringArray boneNames) {
    vector lastScreen; bool lastVisible = false;
    foreach (string boneName : boneNames) {
        int bone = player.GetBoneIndexByName(boneName);
        if (bone < 0) continue;
        vector world = player.GetBonePositionWS(bone);
        vector screen = g_Game.GetScreenPos(world);
        if (screen[2] <= 0) { lastVisible = false; continue; }
        if (lastVisible) {
            canvas.DrawLine(screen[0], screen[1], lastScreen[0], lastScreen[1], thickness, color);
        }
        lastScreen = screen; lastVisible = true;
    }
}
```

Bone chains for players: pelvis→spine→spine1→spine2→spine3→neck→neck1→head→face_forehead
Arms: lefthand→leftforearmroll→leftforearm→leftarmroll→leftarm→neck→rightarm...
Legs: righttoebase→rightfoot→rightlegroll→rightleg→rightupleg→pelvis

Adaptive thickness: 3px at <10m, 2px at <100m, 1px beyond.

---

## 4. Box selection

```
// On shift+drag start:
GetMousePos(selectX, selectY);
panel_selection.Show(true);

// Per frame during drag:
int mouseX, mouseY; GetMousePos(mouseX, mouseY);
int w = mouseX - selectX, h = mouseY - selectY;
int x = selectX, y = selectY;
if (w < 0) { x = mouseX; w = -w; }
if (h < 0) { y = mouseY; h = -h; }
panel_selection.SetScreenPos(x, y);
panel_selection.SetScreenSize(w, h);

// Hit test all ESP widgets:
foreach widget: if (x < wX && y < wY && x+w >= wX && y+h >= wY) → selected
```

---

## 5. Widget calls, extended

### TextListboxWidget (full API)
```
list.AddItem(text, data, column, row)  // data = Param1<Class> for object storage
list.SetItem(row, text, data, column)  // Update existing
list.SetItemColor(row, column, ARGB)   // Per-cell color
list.GetItemData(row, column, out data) // Read stored data
list.GetSelectedRow()                   // -1 if none
list.GetNumItems()                      // Total count
list.SelectRow(int)                     // Programmatic selection
list.ClearItems()                       // Clear all
```

### SliderWidget (full API)
```
slider.SetMinMax(min, max)
slider.SetStep(step)
slider.SetCurrent(value)
float val = slider.GetCurrent()
```

### XComboBoxWidget
```
combo.ClearAll()
combo.AddItem(text)
combo.SetCurrentItem(index)
int idx = combo.GetCurrentItem()
```

### ImageWidget
```
image.LoadImageFile(0, "path/to/icon.paa")
image.SetColor(ARGB(255, 0, 255, 0))
```

### TextWidget extras
```
txt.SetTextExactSize(int pixelSize)  // Exact pixel font size
txt.SetOutline(size, ARGB_color)     // Outline with separate alpha
int outlineColor = txt.GetOutlineColor()
int outlineSize = txt.GetOutlineSize()
```

### Widget extras
```
widget.SetSort(int)              // Z-order (higher = in front)
widget.SetRotation(x, y, z)     // Degrees
Widget.Update()                  // Force layout recalculate
```

### Global functions
```
Widget GetWidgetUnderCursor()    // Hit test at mouse pos
GetMousePos(out int x, out int y)
SetFocus(Widget)                 // null = clear focus
CancelWidgetDragging()
Widget GetDragWidget()
GetMouseState(MouseState.LEFT) & MB_PRESSED_MASK  // Raw mouse state
```

### PlayerPreviewWidget
```
m_CharacterPanelWidget.SetPlayer(player)       // Set displayed player
m_CharacterPanelWidget.UpdateItemInHands(item)  // Update held item
m_CharacterPanelWidget.GetDummyPlayer()         // Get preview dummy
m_CharacterPanelWidget.Refresh()                // Force refresh
```

---

## 6. Scaling to the screen resolution

Design base: **1920x1080**. Everything scales proportionally at runtime. This approach is for values set from script in screen pixels; it is not needed for exact values written in a `.layout` (see "What does not need scaling" below).

### Core variables

```
static int screenWidth, screenHeight;
static float heightScale;    // screenHeight / 1080.0
static float widthScale;     // screenWidth / 1920.0

static void UpdateScreenDimensions() {
    GetScreenSize(screenWidth, screenHeight);
    heightScale = ((float) screenHeight) / 1080.0;
    widthScale  = ((float) screenWidth) / 1920.0;
}
```

Called once in the `DayZGame` constructor and again on the `WindowsResizeEventTypeID` event.

### The rule: heightScale for everything

`heightScale` is used for **all** dimensions — including widths. This keeps elements
square/proportional on any resolution. `widthScale` exists but is almost never used.

```
// Text: "16px at 1080p"
float realSize = 16 * LBWidgetUtils.heightScale;
txt.SetTextExactSize(realSize);

// Image: "300×200 at 1080p"
img.SetScreenSize(300 * heightScale, 200 * heightScale);

// Gap/margin: "10px at 1080p"
float gap = 10.0 * heightScale;

// Position: "place at 500,300 in 1080p coords"
widget.SetScreenPos(500 * heightScale, 300 * heightScale);
```

### Saving and restoring window properties

Normalize to 1080p-space when saving, scale back when restoring:

```
// SAVE — divide out the scale
entry.windowX = x / LBWidgetUtils.heightScale;
entry.windowY = y / LBWidgetUtils.heightScale;
entry.windowW = w / LBWidgetUtils.heightScale;
entry.windowH = h / LBWidgetUtils.heightScale;

// RESTORE — multiply back
widget.SetScreenPos(entry.windowX * heightScale, entry.windowY * heightScale);
widget.SetScreenSize(entry.windowW * heightScale, entry.windowH * heightScale);
```

This means saved positions work correctly if the user changes resolution between sessions.

### Dynamic gaps (LBGapHandler pattern)

`ScriptedWidgetEventHandler` for margins that adapt to resolution:

```
// gapHorizontal/gapVertical come from layout via 'reference' keyword
float newW = width - ((float) gapHorizontal) * LBWidgetUtils.heightScale / parentW;
float newH = height - ((float) gapVertical) * LBWidgetUtils.heightScale / parentH;
root.SetSize(newW, newH);
```

### Image fit that keeps the aspect ratio

Scale image to fit container while maintaining aspect ratio:

```
// Get image natural size + container size
float imgW, imgH, containerW, containerH;
// Calculate scale factors
float scaleW = containerW / imgW;
float scaleH = containerH / imgH;
// If fits at natural size → use it. Otherwise scale by limiting axis
float min = Math.Min(scaleW, scaleH);
img.SetScreenSize(imgW * min, imgH * min);
```

### Auto fitting text size

Loop to find largest font that fits within parent width:

```
void FitText(TextWidget txt, int maxSize, int minSize) {
    float w, h, parentW, parentH;
    txt.GetParent().GetScreenSize(parentW, parentH);
    int current = maxSize;
    while (current >= minSize) {
        txt.SetTextExactSize(current);
        txt.Update();  // Force layout recalc
        txt.GetScreenSize(w, h);
        if (w < parentW * 0.9)
            break;
        --current;
    }
}
```

### What does not need scaling

- **Layout coordinates in 0.0–1.0 range** (relative/proportional) — engine handles these
- **SpacerWidget/WrapSpacerWidget children** — auto-flow is resolution-independent
- **Widget.SetSize(w, h)** with values 0.0–1.0 — these are proportional to parent
- **Exact-flag layout values, and `SetSize` on an exact widget** — the engine already draws
  them at height/1080 (rule 3, measured in game; added 2026-10-03). A script that multiplies them again
  scales them twice (`SetSize` 480 rendered 320 at 720p).

**Only pixel-absolute values need the multiplier:** `SetScreenSize`, `SetScreenPos`,
`SetTextExactSize`, pixel gaps, and any hardcoded distances used in hit-testing or
screen-space math. *(2026-10-03: the layout key `"exact text size"` N on an SDF face already
scales with the screen height (`text-sizing-and-rendering.md`); whether `SetTextExactSize` does the
same was not measured.)*

---

## 7. PIN and numpad menu

Keyboard intercept via `MissionGameplay.OnKeyPress(int key)`:
```
override void OnKeyPress(int key) {
    super.OnKeyPress(key);
    UIScriptedMenu menu = g_Game.GetUIManager().GetMenu();
    MyPinMenu pinMenu;
    if (Class.CastTo(pinMenu, menu))
        pinMenu.OnKeyNumpadPressed(key);
}
```

`KeyCode` names to map: `KC_NUMPAD0` to `KC_NUMPAD9`, `KC_0` to `KC_9`, `KC_BACK`, `KC_NUMPADENTER`, `KC_RETURN` (the enum is in `P:\scripts\1_core\proto\ensystem.c`; `KC_BACK` is at line 171 and `KC_NUMPAD0` at line 239).

---

## 8. Camera preview in a menu

Orbital camera for showing vehicles/items in garage-style UI:

```
// Calculate orbital position:
float height = Math.Sin(Math.DEG2RAD * angle) * distance;
float cos = Math.Cos(Math.DEG2RAD * rotation) * distance;
float sin = Math.Sin(Math.DEG2RAD * rotation) * distance;
vector cameraPos = center + Vector(sin, height, cos);
```

Blackbox pattern for a garage style preview (not checked in game): spawn an invisible building at y=109, show the items inside it, and set the world time to noon every frame.

---

## 9. Looking around without closing the menu

Toggle cursor visibility + input exclusions for camera control inside UI:
```
// Start looking around:
Mission mission = g_Game.GetMission();
mission.RemoveActiveInputExcludes({"menu", "movement", "aiming"}, true);
g_Game.GetUIManager().ShowUICursor(false);

// Stop:
mission.AddActiveInputExcludes({"movement", "aiming", "menu"});
g_Game.GetUIManager().ShowUICursor(true);
```
