# LBGroups UI patterns: what a large production mod does

The UI patterns of LBmaster_Groups, one of DayZ's most advanced mods: groups, chat, map markers,
compass, GPS minimap, player list, admin menu, and color and position managers. Use it to copy a pattern
for a map, HUD, chat or settings UI, or when a mod depends on LBmaster_Core and should reuse its helpers.

Everything about `LB*` classes here is third-party mod behaviour (LBmaster_Groups and LBmaster_Core), not
vanilla, and is not checked on `P:\`. The code samples keep that mod's own
brace style. The vanilla engine calls the patterns rest on were checked on `P:\`:

| Vanilla API | Declared at |
|---|---|
| `MapWidget`: `ClearUserMarks`, `AddUserMark`, `GetMapPos`, `SetMapPos`, `GetScale`, `SetScale`, `MapToScreen`, `ScreenToMap` | `P:\scripts\3_game\gameplay.c:322-333` |
| `CanvasWidget.DrawLine`, `Clear` | `P:\scripts\1_core\proto\enwidgets.c:343-344` |
| `ScrollWidget`: `GetVScrollPos01`, `VScrollStep`, `VScrollToPos01`, `VScrollToWidget` | `P:\scripts\1_core\proto\enwidgets.c:497-501` |
| `TextWidget`: `SetTextExactSize`, `SetOutline`, `GetOutlineSize`, `SetShadow`, `GetShadowSize`, `GetShadowColor` | `P:\scripts\1_core\proto\enwidgets.c:193-201` |
| `Widget.SetRotation`, `Widget.AddChild` | `P:\scripts\1_core\proto\enwidgets.c:146`, `:161` |
| `CGame.GetScreenPos(vector world_pos)` | `P:\scripts\3_game\global\game.c:963` |
| `IngameHudVisibility.HUD_HIDE_FLAGS`, `IsContextFlagActive` | `P:\scripts\5_mission\gui\ingamehudvisibility.c:43`, `:120` |
| `ChatInputMenu.m_BackInputWrapper` (section 14) | `P:\scripts\5_mission\gui\chat\chatinputmenu.c:5`, `:15` |
| `string.Format` (section 21) | `P:\scripts\1_core\proto\enstring.c:526` |

The "device mod" notes below say where each pattern fits in a mod with interactive devices (a phone, an
ATM, a terminal).

---

## 1. Layout manager: a central layout registry

LBGroups decouples layout paths from code via a registry pattern. All layouts are
registered by friendly name at mod init, then created anywhere by name.

```
// Registration (modded class LBLayoutManager, constructor):
RegisterLayout("GroupUI", "LBmaster_Groups/gui/layouts/menu/mapmenu_default.layout");
RegisterLayout("ChatItem", "LBmaster_Groups/gui/layouts/helper/day_z_chat_item.layout");
RegisterLayout("3DMarker", "LBmaster_Groups/gui/layouts/helper/3dmarker.layout");

// Usage anywhere:
Widget w = LBLayoutManager.Get().CreateLayout("ChatItem", parentWidget);
// Or without parent (appended to screen root):
Widget w2 = LBLayoutManager.Get().CreateLayout("3DMarker");
```

**Benefits**: One place to change paths, layouts swappable per theme/skin,
no scattered hardcoded paths. Future phone/PC mod: register different layout
sets per device type.

---

## 2. ConnectClassWidgetVariables: auto-binding

Maps class member variables to widgets by matching variable name to widget name
in the layout tree. Eliminates dozens of FindAnyWidget calls.

```
// Class with variables named same as widgets in layout:
class LBGroupManagePage {
    EditBoxWidget searchbox;
    ButtonWidget btn_kick, btn_leave, btn_upgrade;
    TextWidget txt_groupname;
    Widget playerlist_members, panel_list;
}

// Single call binds all matching names:
ConnectClassWidgetVariables(this, rootWidget, excludeArray, renameArray);

// excludeArray: skip these variable names (e.g. {"rootWidget", "buttonWidget"})
// renameArray: pairs {"varName", "widgetName", "varName2", "widgetName2"}
//   Maps variable "mapWidget" to layout widget named "Map":
GetConnectRenameFields() { return {"mapWidget", "Map", "mapNotFound", "MapNotFound"}; }
```

**Key insight**: The rename array is pairs, not a map. Every even index is a
variable name, every odd index is the widget name to bind it to.

---

## 3. MapWidget API: full map interaction

```
// Convert screen coords to map world coords:
vector worldPos = mapWidget.ScreenToMap(Vector(screenX, screenY, 0));

// Center map on position:
mapWidget.SetMapPos(position);

// Get/set zoom level:
float scale = mapWidget.GetScale();
mapWidget.SetScale(0.2);

// Get current center:
vector center = mapWidget.GetMapPos();

// Clear vanilla user marks:
mapWidget.ClearUserMarks();
```

**GPS minimap pattern** — MapWidget with fixed zoom tracking player:
```
void Update() {
    vector pos = GetGame().GetCurrentCameraPosition();
    mapWidget.SetScale(zoom);        // fixed zoom (e.g. 0.25)
    mapWidget.SetMapPos(pos);        // center on player
    // Rotate player icon to camera direction:
    if (markerWrapper && markerWrapper.icon) {
        float angle = GetCurrentAngle();
        markerWrapper.icon.SetRotation(0, 0, angle - 180);
    }
}
```

**MapWidget raster ignores inherited parent transform (measured in-game 2026-08-22).** Rotating an ancestor of a `MapWidget` does **not** rotate the drawn map. Measured on the tree `rootFrame > panelMap > mapWidget > iconPane > headingArrow`: applying `SetRotation` on `rootFrame` deforms `headingArrow` — a descendant of the `mapWidget`, two levels below — as expected, while the raster that `mapWidget` itself paints, in the middle of that same chain, stays axis-aligned. The transform propagates through the tree; the map raster renderer discards it. Confirmed by a scanline measurement and by eye on screen. Consequence: a heading-up navigation HUD **cannot** be made by rotating a `MapWidget`. Compose the map with `ImageWidget` (e.g. a tile mosaic) and rotate those, which do honour the transform. `MapWidget` is for north-up with translation — `SetMapPos` works and the map follows the vehicle — not for heading.

---

## 4. CanvasWidget: drawing overlay

Used for circles (zones), fog of war, custom drawing on map.

```
CanvasWidget drawCanvas;
drawCanvas = CanvasWidget.Cast(mapWidget.FindAnyWidget("drawCanvas"));

// Clear all drawings:
drawCanvas.Clear();

// Draw line (used internally by circle rendering):
// drawCanvas.DrawLine(x1, y1, x2, y2, width, color);
```

**The canvas overlays the map** — child widget inside MapWidget named "drawCanvas".
There's also an "iconPane" widget for icon positioning.

---

## 5. 3D marker projection: world to screen

Project world positions onto screen for floating 3D markers:

```
vector screenPos = GetGame().GetScreenPos(worldPosition);
float x = screenPos[0];
float y = screenPos[1];
float z = screenPos[2]; // z <= 0 means behind camera

// Check bounds:
if (x <= 0 || x >= screenWidth || y <= 0 || y >= screenHeight || z <= 0) {
    widget.Show(false);   // off-screen or behind camera
    return;
}
widget.SetPos(x, y);
widget.Show(true);
```

**Centering on position** — for ping/player markers:
```
if (ShouldCenterWidget()) {
    x = x - widthMainWidget;   // half-width
    y = y - heightMainWidget;  // half-height
}
```

---

## 6. Compass strip: bearing-based widget positioning

Camera direction → marker angle → strip position:

```
// Get camera bearing:
vector dir = GetGame().GetCurrentCameraDirection();
vector angles = dir.VectorToAngles();
float cameraAngle = angles[0];
if (cameraAngle > 180)
    cameraAngle = cameraAngle - 360;

// Move compass image (strip that slides):
compassImage.SetPos((-cameraAngle / 180.0) - 1.0, 0);

// Position marker on compass:
float markerAngle = GetMarkerAngle();           // relative to camera
float posX = (markerAngle / 180.0) - 0.5;
if (posX < -1)
    posX = posX + 2;
compassWidget.SetPos(posX, 0);
```

Marker angle calculation:
```
float GetMarkerAngle() {
    vector camPos = GetGame().GetCurrentCameraPosition();
    vector dir = camPos - markerPosition;
    dir = dir.Normalized();
    vector angles = dir.VectorToAngles();
    float angle = angles[0] - currentCameraAngle + 360;
    while (angle > 180)
        angle = angle - 360;
    return angle;
}
```

---

## 7. Text width measurement: the hidden widget trick

Measure rendered text width before placing (used for chat word-wrapping):

```
class LBTextLengthCalculator {
    private TextWidget widget;

    void LBTextLengthCalculator() {
        // Create off-screen measurement widget:
        widget = TextWidget.Cast(LBLayoutManager.Get().CreateLayout("TextLengthTester"));
    }

    float GetTextLength(string text, int size) {
        widget.SetTextExactSize(size);
        widget.SetText(text);
        widget.Update();         // force layout recalculation
        float width, height;
        widget.GetScreenSize(width, height);
        width = width / screenWidth;  // normalize to 0-1
        return width;
    }
}
```

**Use case**: Multi-line chat wrapping — split message into words,
accumulate until measured width exceeds max, then wrap.

---

## 8. Chat ring buffer: efficient message display

LBGroups implements chat with a fixed-size ring buffer of pre-created
ChatLine widgets that reposition instead of creating/destroying:

```
const int LINE_COUNT = 100;
const int VISIBLE_LINES_COUNT = 12;
int m_LastLine = 0;

// Add message: advance ring pointer, set content, reposition all lines
void AddInternal(ChatMessageEventParams params) {
    m_LastLine = (m_LastLine + 1) % m_Lines.Count();
    ChatLine line = m_Lines.Get(m_LastLine);
    line.Set(params);

    for (int i = 0; i < m_Lines.Count(); i = i + 1) {
        line = m_Lines.Get((m_LastLine + 1 + i) % LINE_COUNT);
        line.m_RootWidget.SetPos(0, i * m_LineHeight);
    }
}
```

**Chat open/close pause pattern** — when chat menu opens, pause fade timers,
show all; on close, resume timers:
```
void OnChatMenuOpened() {
    foreach (ChatLine line : m_Lines) {
        line.m_FadeTimer.Pause();
        line.m_TimeoutTimer.Pause();
        line.m_RootWidget.Show(true);
    }
}
void OnChatMenuClosed() {
    foreach (ChatLine line : m_Lines) {
        line.m_FadeTimer.Continue();
        line.m_TimeoutTimer.Continue();
    }
}
```

**Chat scroll** with ScrollWidget:
```
void OnMouseWheel(int count) {
    float max = Math.Clamp(addedMessages / LINE_COUNT, 0, 1.0);
    rootPositionWidget.VScrollStep(count);
    float pos = 1.0 - rootPositionWidget.GetVScrollPos01();
    if (pos > max)
        rootPositionWidget.VScrollToPos01(1.0 - max);
}
```

---

## 9. Dirty-check pattern: hash-based refresh

Avoid full marker re-render every frame. Compare counts and hashes:

```
int lastGroupMarkerCount = 0;
int lastServerMarkerHash = 0;
int lastPrivateMarkerCount = 0;

bool NeedMarkerRefresh() {
    bool need = false;

    // Count check (cheap):
    int groupMarkers = grp.markers.Count() + grp.pings.Count() + grp.members.Count();
    if (groupMarkers != lastGroupMarkerCount) {
        lastGroupMarkerCount = groupMarkers;
        need = true;
    }

    // Hash check (detects content changes without full compare):
    int staticHash = 0;
    foreach (LBServerMarker m : mgr.staticMarkers) {
        staticHash = staticHash + m.CalcHash();
    }
    if (staticHash != lastServerMarkerHash) {
        lastServerMarkerHash = staticHash;
        need = true;
    }

    return need;
}
```

Hash function on marker (combines all visual properties):
```
int CalcHash(bool includePosition) {
    int hash = type + uid + name.Hash() + colorA * 4546546 + colorR * 52412;
    hash = hash + ((int) circleRadius) * 546353;
    return hash;
}
```

---

## 10. Page and tab system: dynamic multi-page UI

Architecture: array of `LBGroupPage` objects, each with:
- `buttonWidget` (tab button, created dynamically)
- `rootWidget` (page content panel)
- `pageID` / `pageSubID` for grouping tabs
- priority for button ordering via `Widget.SetSort()`

```
// Init: create pages and buttons
void InitPages() {
    pages.Clear();
    InitPage(new LBInfoPage(LBPageSettingsType.INFO));
    InitPage(new LBGroupCreatePage(LBPageSettingsType.GROUP));
    InitPage(new LBGroupManagePage(LBPageSettingsType.GROUP));
    // Pages sharing pageID share the same tab button
}

// Page switching:
void ChangePageTo(LBGroupPage page) {
    if (currentPage)
        currentPage.OnHide();
    currentPage = page;
    page.OnShow();
}

// Tab button ordering via Widget.SetSort():
btnWidget.SetSort(1000 - priority);  // higher priority = earlier position
```

**Conditional pages**: `OnTopButtonClicked` checks if page can show
(e.g. "manage" page only shows if player has a group):
```
override bool OnTopButtonClicked(Widget w) {
    if (super.OnTopButtonClicked(w)) {
        PlayerBase pb = PlayerBase.Cast(GetGame().GetPlayer());
        return pb && pb.GetLBGroup() != null;
    }
    return false;
}
```

---

## 11. Color picker pattern: slider and EditBox kept in sync

Common pattern for ARGB color editors:

```
SliderWidget slider_r, slider_g, slider_b;
EditBoxWidget edit_r, edit_g, edit_b;
Widget colorPreview;

// Slider → EditBox:
bool OnSliderUpdate(SliderWidget slider, EditBoxWidget edit) {
    edit.SetText("" + slider.GetCurrent());
    UpdatePreview();
    return true;
}

// EditBox → Slider:
bool OnTextUpdated(SliderWidget slider, EditBoxWidget edit) {
    int val = edit.GetText().ToInt();
    val = Math.Min(255, Math.Max(0, val));
    edit.SetText("" + val);
    slider.SetCurrent(val);
    UpdatePreview();
    return true;
}

// Preview:
void UpdatePreview() {
    preview.SetColor(ARGB(255, slider_r.GetCurrent(), slider_g.GetCurrent(), slider_b.GetCurrent()));
}
```

> **If the mod already depends on LBmaster_Core, do not build this dialog.** `LBColorPicker` is a finished, reusable component; see section 31 for its API, its two lifetime traps and the redraw it does not trigger.

---

## 12. ScriptInvoker: global event bus

Decoupled observer pattern used throughout LBGroups for cross-system events:

```
// Declaration (static on config class):
class LBColorManager_ {
    static ref ScriptInvoker Event_OnColorChange = new ScriptInvoker();
}

// Subscribe (in constructor):
void MyComponent() {
    LBColorManager_.Event_OnColorChange.Insert(OnColorChanged);
}

// Unsubscribe (in the destructor, every time; prevents dangling callbacks):
void ~MyComponent() {
    if (LBColorManager_.Event_OnColorChange)
        LBColorManager_.Event_OnColorChange.Remove(OnColorChanged);
}

// Fire event:
static void InvokeOnChanged() {
    Event_OnColorChange.Invoke();
}
```

**Events used by LBGroups**: OnColorChange, OnPositionChange, OnLayoutChanged,
OnScreenSizeChanged, StreamerModeChanged, GPSChanged, OnConfigReceived.

**In a device mod**: fits device state broadcasts, UI theme changes and a
phone notification system.

---

## 13. HUD overlay pattern: conditional display

All HUD elements (compass, GPS, player list, chat) follow same pattern:

```
void UpdateHud(float timeslice) {
    IngameHud hud = IngameHud.Cast(GetGame().GetMission().GetHud());
    if (!hud) {
        Show(false);
        return;
    }
    bool visible = false;
    if (hud.LBIsHudVisible()              // HUD not hidden
        && featureEnabled                   // server config allows it
        && LBPlayerUtils.IsClientPlayerAlive()  // player alive
        && !GetGame().GetUIManager().GetMenu())  // no menu open
    {
        visible = true;
    }
    Show(visible);
    if (visible)
        Update();
}
```

**HUD visibility helper** (version-safe):
```
modded class IngameHud {
    bool LBIsHudVisible() {
    #ifdef DAYZ_1_26
        return IsHudVisible();
    #else
        return !GetHudVisibility().IsContextFlagActive(IngameHudVisibility.HUD_HIDE_FLAGS);
    #endif
    }
}
```

---

## 14. Modded class widget hijack: replace a vanilla layout

Pattern to completely replace a vanilla widget layout while preserving API:

```
modded class ChatInputMenu {
    override Widget Init() {
        Widget old = super.Init();    // Call super (inits internal vars we need)
        old.Unlink();                 // Immediately destroy the vanilla widget

        // Create our replacement:
        layoutRoot = LBLayoutManager.Get().CreateLayout("ChatInput");
        m_edit_box = EditBoxWidget.Cast(layoutRoot.FindAnyWidget("InputEditBoxWidget"));
        return layoutRoot;
    }
}
```

`super.Init()` must be called first because it initializes
internal variables (like `m_BackInputWrapper`) that cause NPE if missing.
Then immediately `Unlink()` the old widget.

---

## 15. Drag and drop on the map: marker repositioning

```
// Start drag:
override bool OnDrag(Widget w, int x, int y) {
    mapMarkerManager.OnDragStart(w);
    return true;
}

// Drop: convert screen→world, update marker:
override bool OnDrop(Widget w, int x, int y, Widget reciever) {
    vector worldpos = mapWidget.ScreenToMap(Vector(x, y, 0));
    worldpos[1] = GetGame().SurfaceY(worldpos[0], worldpos[2]);

    LBMarker marker = mapMarkerManager.FindMarkerByMainWidget(w);
    if (marker) {
        marker.SetPosition(worldpos);
        marker.SendPositionToServer();
    }
    mapMarkerManager.OnDragStop(w);
    return true;
}
```

**Drag toggle**: markers can be made draggable/non-draggable. Uses separate
layout for draggable markers (`MapMarker_Dragable` with `draggable 1` flag).

---

## 16. Client-side persistent config: per-server settings

LBGroups saves client preferences (colors, positions, visibility) per server
using JSON files in the profile directory:

```
class LBColorManager_ : LBConfigBase {
    ref array<ref Param2<string, int>> colors = new array<ref Param2<string, int>>();

    // Default color system — get-or-create with fallback:
    int GetColor(string colorStr, int defaultColor) {
        foreach (Param2<string, int> color : colors) {
            if (color && color.param1 == colorStr)
                return color.param2;
        }
        // Not found → insert default:
        colors.Insert(new Param2<string, int>(colorStr, defaultColor));
        return defaultColor;
    }

    void SetColor(string colorStr, int colorARGB) {
        foreach (Param2<string, int> color : colors) {
            if (color && color.param1 == colorStr) {
                color.param2 = colorARGB;
                return;
            }
        }
        colors.Insert(new Param2<string, int>(colorStr, colorARGB));
    }
}
```

**Position manager** uses `Param3<string, vector, int>` (name, position, alignment).
Same get-or-create pattern. Loaded from JSON, saved on settings close.

**In a device mod (ATM, phone)**: This is how to persist user preferences
(theme colors, widget positions, notification settings) per server.

---

## 17. Widget position manager: moveable HUD elements

Each HUD element has a configurable screen position + alignment:

```
typedef Param3<string, ref vector, int> LBWidgetPosition;

// Get position with default:
vector pos = positionManager.GetPosition("Minimap", Vector(0.97, 0.83, 0), 8);
int alignIndex = positionManager.GetIndex("Minimap");

// Apply:
LBWidgetUtils.SetWidgetAlignmentIndex(widget, alignIndex);
LBWidgetUtils.SetWidgetPositionIndex(widget, pos, alignIndex);
```

**Alignment indices**: 0=top-left, 2=top-right, 6=bottom-left, 8=bottom-right.
Position is relative to the alignment anchor (0-1 range).

---

## 18. Player list with health bars

Dynamic list with color-interpolated health:

```
void UpdateWidget() {
    if (!member || !member.online) {
        Show(false);
        return;
    }
    // Health bar color: lerp between full and empty colors
    int color = GetColor(member.health);
    healthbar.SetColor(color);
    playername.SetText(member.name);
}

int GetColor(float health) {
    int colorFull = LBColorManager.Get.GetColor("Playerlist entry full health");
    int colorZero = LBColorManager.Get.GetColor("Playerlist entry zero health");
    float ratio = health / 100.0;
    return LBConverter.MixColors(colorFull, colorZero, ratio);
}
```

**Distance display** with unit switching:
```
float dist = vector.Distance(member.position, cameraPos);
if (dist < 1000) {
    distance.SetText("" + ((int) dist) + "m");
} else {
    float km = ((float)((int)(dist / 100))) / 10;
    distance.SetText("" + km + "km");
}
```

---

## 19. Tactical ping: raycast and marker

Place marker where crosshair points using physics raycast:

```
void AddPing() {
    vector camPos = GetGame().GetCurrentCameraPosition();
    vector camDir = GetGame().GetCurrentCameraDirection().Normalized() * 2000.0;

    Object hitObj;
    vector hitPos, hitNormal;
    float fraction;
    PhxInteractionLayers layers = PhxInteractionLayers.TERRAIN
        | PhxInteractionLayers.BUILDING | PhxInteractionLayers.VEHICLE;

    DayZPhysics.RayCastBullet(camPos, camPos + camDir, layers,
        GetGame().GetPlayer(), hitObj, hitPos, hitNormal, fraction);

    LBMarker marker = new LBMarker();
    marker.SetupMarker(LBMarkerType.GROUP_PING, playerName, "", hitPos);
    group.AddMarker(marker);
}
```

---

## 20. Chat input override: EditBox with an event handler

EditBox events require SetHandler pattern:

```
class ChatEventHandler : ScriptedWidgetEventHandler {
    EditBoxWidget m_edit_box;
    ChatInputMenu chatMenu;

    void ChatEventHandler(ChatInputMenu menu) {
        chatMenu = menu;
        m_edit_box = menu.GetEditBox();
        m_edit_box.SetHandler(this);   // binds events to this handler
    }

    override bool OnChange(Widget w, int x, int y, bool finished) {
        return chatMenu.OnChangeLB(w, x, y, finished);
    }
}
```

**`finished` parameter on OnChange**: `true` when Enter is pressed (submit),
`false` on each keystroke. LBGroups uses this for chat send:
```
if (!finished)
    return false;  // still typing
string text = m_edit_box.GetText();
SendChatMessage(text);
```

---

## 21. Float to string formatting

Enforce Script has `string.Format` (`P:\scripts\1_core\proto\enstring.c:526`), but its `%1` to `%9`
placeholders take no precision, so there is no printf-style way to fix the number of decimals. Manual
decimal formatting:

```
string FloatToString(float f, bool addPoint) {
    string txt = "" + f;
    int index = txt.IndexOf(".");
    if (addPoint) {
        if (index > 0)
            txt = txt.Substring(0, index + 2);  // 1 decimal
        else
            txt = txt + ".0";
    } else {
        if (index > 0)
            txt = txt.Substring(0, index);       // integer part only
    }
    return txt;
}
```

---

## 22. Feature flags: compile-time subsystem toggling

```
#ifndef LB_DISABLE_CHAT
    // Entire chat subsystem compiled only if not disabled
    modded class Chat { ... }
    modded class ChatInputMenu { ... }
#endif

#ifdef LBmaster_GroupDLCPlotpole
    // Territory/plotpole features only with DLC
#endif

#ifdef DAYZ_1_26
    // Version-specific API differences
#endif
```

**In a device mod**: Use this pattern for optional subsystems (CCTV, battery, phone).
Servers can disable features they don't want without script errors.

---

## 23. RPC dispatcher: registered callback pattern

Central RPC handler with registered callbacks per RPC type:

```
class LB_RPC_AG_Client : LB_RPCHandler {
    void LB_RPC_AG_Client() {
        RegisterRPC(LBGroupRPCs.GROUP_RPC, ScriptCaller.Create(OnGroupRPC));
        RegisterRPC(LBGroupRPCs.LB_GLOBAL_CHAT, ScriptCaller.Create(OnChatMessage));
        // ... more registrations
    }

    void OnGroupRPC() {
        int type = 0;
        if (!ctx.Read(type))
            return;
        pb.GetLBGroup().OnRPCClient(type, ctx);
    }
}
```

**Sub-dispatch pattern** — group-level RPC further dispatches to marker RPCs:
```
void OnRPCClient(int type, ParamsReadContext ctx) {
    if (type == LBGroupRPCs.ADD) {
        // handle add
    } else if (type > LBGroupRPCs.START_MARKER_RPC) {
        int uid;
        ctx.Read(uid);
        LBMarker marker = FindAnyMarkerByUID(uid);
        if (marker)
            marker.OnMarkerRPCClient(type, ctx);
    }
}
```

---

## 24. Screen size change handling

Respond to resolution changes dynamically:

```
// Global event:
static ref ScriptInvoker Event_OnScreenSizeChanged = new ScriptInvoker();

// Subscribe:
LBWidgetUtils.Event_OnScreenSizeChanged.Insert(OnSizeChange);

// Handler — recalculate sizes/positions:
void OnSizeChange() {
    float width = 300 * LBWidgetUtils.widthScale;  // scale factor
    float height = 300 * LBWidgetUtils.widthScale;
    layoutRoot.SetSize(width, height);
    UpdatePosition();
}
```

---

## Where these patterns fit in a device mod

| LBGroups pattern | Device mod application |
|---|---|
| Layout Manager registry | Phone/ATM layout swapping per device skin |
| ConnectClassWidgetVariables | Reduce boilerplate in all UI classes |
| ScriptInvoker events | Device state broadcasts, UI refresh triggers |
| Client-side config | ATM user preferences (theme, shortcuts) |
| Color manager | Customizable UI themes for phone/ATM |
| Position manager | Moveable HUD elements (phone notifications, minimap) |
| Text measurement | Phone chat bubble sizing, ATM receipt formatting |
| Ring buffer chat | Phone messaging app |
| 3D marker projection | Device location markers, waypoints |
| Page/tab system | Phone app pages, ATM menu screens |
| Dirty-check hash | Efficient device list refresh |
| Tactical ping raycast | Quick-place markers from phone app |
| Feature flags | Optional subsystems per server config |

---

## 25. MapWidget.MapToScreen: world to map pixel

Convert world coordinates to pixel position within the map widget:

```
vector screenPos = mapWidget.MapToScreen(worldPosition);
// Returns pixel coords relative to the screen, not to the widget
// Subtract widget screen position to get widget-local coords:
float wx, wy;
mapWidget.GetScreenPos(wx, wy);
vector local = screenPos - Vector(wx, wy, 0);
```

Used by FOW drawer to position fog rectangles on the map.

---

## 26. MapWidget.AddUserMark: vanilla map markers

Add colored named markers directly to the vanilla map widget:

```
mapWidget.AddUserMark(worldPos, "Marker Name", ARGB(255,255,0,0), "path/icon.paa");
mapWidget.ClearUserMarks();  // remove all user marks
```

Used by PVEZ compat layer to add zone markers without the full
LBMarker system.

---

## 27. TextWidget advanced formatting

```
// Exact pixel size (not relative):
textWidget.SetTextExactSize(14);

// Shadow (size, color, intensity 0.0-1.0):
textWidget.SetShadow(1, ARGB(255,0,0,0), 0.8);

// Outline (size, color):
textWidget.SetOutline(1, ARGB(200,0,0,0));

// Read current values:
int shadowSize = textWidget.GetShadowSize();
int shadowColor = textWidget.GetShadowColor();
int outlineSize = textWidget.GetOutlineSize();
```

Used by chat to dynamically adjust text border visibility
based on user settings.

---

## 28. Widget.AddChild: dynamic reparenting

Move a widget from one parent to another at runtime:

```
// Move chat from vanilla root to custom positioned root:
if (!atDefault) {
    customParent.AddChild(chatWidget);
} else {
    vanillaRoot.AddChild(chatWidget);
}
```

**Use case**: Toggle between fixed and free-floating HUD positions.
Widget keeps all its children when reparented.

---

## 29. CanvasWidget.DrawLine: full API

```
// DrawLine(x1, y1, x2, y2, width, color)
// A thick horizontal line acts as a filled rectangle:
void DrawFilledRect(float x, float y, float w, float h, int color) {
    drawCanvas.DrawLine(x, y + h / 2, x + w, y + h / 2, h, color);
}

drawCanvas.Clear();  // wipe all drawn content
```

FOW draws thousands of merged rectangles per frame this way.
The canvas must be a child of the MapWidget to overlay correctly.

---

## 30. ScrollWidget: programmatic scroll control

```
ScrollWidget scroll;

// Scroll by steps (mouse wheel):
scroll.VScrollStep(count);  // positive = down, negative = up

// Get/set normalized scroll position (0.0 = top, 1.0 = bottom):
float pos = scroll.GetVScrollPos01();
scroll.VScrollToPos01(0.5);  // scroll to middle

// Chat uses inverted scroll + clamp:
float pos = 1.0 - scroll.GetVScrollPos01();
float max = Math.Clamp(addedMessages / LINE_COUNT, 0, 1.0);
if (pos > max)
    scroll.VScrollToPos01(1.0 - max);
```

---

## 31. LBColorPicker reuse: ownership, lifetime, and the redraw it does not trigger

Measured 2026-09-03 while adding a configurable route colour to a GPS route overlay built on
LBmaster_Core. Three traps, each found only after the code was written.

**Do not build a colour dialog when the mod already depends on LBmaster_Core.** `LBColorPicker`
is finished: A/R/G/B sliders each paired with an EditBox, a hex field and a live swatch, layout
already registered as `"ColorPicker"` (`LBmaster_Core/scripts/3_Game/LBmaster_Core/LBLayoutManager.c:50`).
Section 11 above is for the case where LBmaster_Core is not a dependency.

```
LBColorPicker(Widget parent, ScriptCaller selectCallback, int color_ = -1,
              LBColorConfig colorCfg_ = null, bool allowAlpha_ = true)
// LBmaster_Core/scripts/3_Game/LBmaster_Core/GUI/Helper/LBColorPicker.c:21
```

- `allowAlpha_ = false` hides the alpha panel and `GetColor()` returns `ARGB(255, r, g, b)`
  (`LBColorPicker.c:217`) — the three-channel RGB picker most features actually want.
- `parent` must not be null: the constructor calls `parent.GetScreenPos()` unguarded.
- Callback signature is `void OnColorPicked(int color)`.

### Trap 1 — never release the owning `ref` inside the picker's own callback

The component self-destructs: `callback.Invoke(GetColor())` and only **then** `delete this`
(`LBColorPicker.c:194-196`), with a destructor that unlinks its root widget. Clearing the owner's
`ref` from inside the callback drops the last strong reference while the object is still running,
and the `delete this` that follows operates on an already-invalidated object — a crash shape at
the exact moment the player confirms.

The production pattern keeps the member and never touches it in the callback. In LBmaster_Core's only
call site the sole assignments are the declaration and the three `new`
(`GUI/Helper/WidgetLinker/LBWidget_Linked_Var.c:12`, `:221`, `:225`, `:245`; callback at `:179`).
Let the next `new` overwrite it.

### Trap 2 — the picker outlives the menu that opened it

Its root is created with **no parent** (`LBLayoutManager.Get().CreateLayout("ColorPicker")`) and
is merely positioned against the caller's widget, so it is a workspace-level overlay, not a child
of the menu. Closing the map leaves it on screen with a callback pointing at a hidden owner.
Release the reference in the owner's `OnHide()`. The same assignment that is unsafe inside the
callback is correct here, because none of the picker's code is on the stack.

### Trap 3 — a colour change does not repaint a dirty-checked overlay

A canvas overlay guarded by a dirty-check (section 9) compares map position, scale, path revision,
player position and canvas size — never style. A new colour therefore stays invisible until the
player happens to move the map, which reads as "the setting does nothing".

Give the shared style object a revision counter, bump it wherever the cached style is invalidated,
and add the comparison to the dirty chain **at every draw site**. A mod that draws the same route
on the big map and on the HUD has two of them, and fixing one leaves the other stale — grep the
draw call, do not rely on memory of where it is used.

### Persisting the choice, and one visual trap

Persistence is plain vanilla: a flat DTO plus
`JsonFileLoader<T>.SaveFile("$profile:<Mod>/client_settings.json", ...)`, preceded by
`MakeDirectory("$profile:<Mod>")` so the first save succeeds on a clean profile. Treat an absent,
unparseable or out-of-range value as "use the default" rather than as an error.

A swatch stretched across the whole button looks right in orange and becomes unreadable the moment
the player picks white, because the label sits on top of it. Keep the button's own background and
put the swatch in a small fixed square beside the label.
