# Map widgets and markers

How to drive a `MapWidget` from script, draw over it with a canvas, drag markers on it, follow the player with a minimap, and refresh markers only when something changed. Markers in the 3D world and the compass are in `world-markers-and-compass.md`.

The patterns come from a large production group and map mod. `My*` names stand for that mod's helper classes, which you write yourself; their behaviour is third party, not vanilla, and not checked on `P:\`. The vanilla calls are cited.

## The map calls

`MapWidget` (`P:\scripts\3_game\gameplay.c:321` to `:333`):

| Call | Does |
|---|---|
| `GetMapPos()`, `SetMapPos(vector worldPos)` | Read or set the world point at the map's center |
| `GetScale()`, `SetScale(float scale)` | Read or set the zoom |
| `ScreenToMap(vector screenPos)` | Screen point to world position |
| `MapToScreen(vector worldPos)` | World position to a screen point |
| `AddUserMark(vector pos, string text, int color, string texturePath)` | A named, colored vanilla mark |
| `ClearUserMarks()` | Removes all user marks |

`MapToScreen` returns a point relative to the screen, not to the widget. Subtract the widget's own screen position for widget local coordinates:

```c
vector screenPos = mapWidget.MapToScreen(worldPosition);
float wx, wy;
mapWidget.GetScreenPos(wx, wy);
vector local = screenPos - Vector(wx, wy, 0);
```

`AddUserMark` is enough for simple markers; the group mod's compatibility layer for a zone mod adds its zone marks this way without its own marker system.

## A minimap that follows the player

A `MapWidget` at a fixed zoom, recentred every update, with the player icon turned to the camera heading:

```c
void Update()
{
    mapWidget.SetScale(zoom); // a fixed zoom, for example 0.25
    mapWidget.SetMapPos(GetGame().GetCurrentCameraPosition());
    if (markerWrapper && markerWrapper.icon)
        markerWrapper.icon.SetRotation(0, 0, GetCurrentAngle() - 180);
}
```

The map raster ignores rotation (measured in game). Rotating an ancestor of a `MapWidget` turns its other descendants: in the tree `rootFrame`, `panelMap`, `mapWidget`, `iconPane`, `headingArrow`, a `SetRotation` on `rootFrame` turns `headingArrow`, two levels under the map, while the raster the map paints stays axis aligned. So a heading up navigation display can't be made by rotating a `MapWidget`. Build it from `ImageWidget` tiles, which do follow the rotation, and keep `MapWidget` for north up maps that move with `SetMapPos`.

## Drawing on the map

Put a `CanvasWidget` named `drawCanvas` inside the `MapWidget`, beside an `iconPane` for icons, so it overlays the map. `DrawLine` and `Clear` are at `P:\scripts\1_core\proto\enwidgets.c:343` and `:344`:

```c
CanvasWidget drawCanvas = CanvasWidget.Cast(mapWidget.FindAnyWidget("drawCanvas"));
drawCanvas.Clear();

// a thick horizontal line is a filled rectangle
void MyMod_DrawFilledRect(CanvasWidget canvas, float x, float y, float w, float h, int color)
{
    canvas.DrawLine(x, y + h / 2, x + w, y + h / 2, h, color);
}
```

The group mod draws zone circles and a fog of war this way, thousands of merged rectangles a frame, placed with `MapToScreen`.

## Dragging markers

```c
override bool OnDrag(Widget w, int x, int y)
{
    mapMarkerManager.OnDragStart(w);
    return true;
}

override bool OnDrop(Widget w, int x, int y, Widget reciever)
{
    vector worldpos = mapWidget.ScreenToMap(Vector(x, y, 0));
    worldpos[1] = GetGame().SurfaceY(worldpos[0], worldpos[2]);
    MyMarker marker = mapMarkerManager.FindMarkerByMainWidget(w);
    if (marker)
    {
        marker.SetPosition(worldpos);
        marker.SendPositionToServer();
    }
    mapMarkerManager.OnDragStop(w);
    return true;
}
```

`SurfaceY(float x, float z)` is at `P:\scripts\3_game\global\game.c:1176`. Vanilla spells the drop parameter `reciever`. A marker the player may move uses a separate layout (`MapMarker_Dragable`) with `draggable 1`; the others don't set it.

## Refresh only on change

Rebuilding every marker every frame costs too much. Compare cheap counts first, then a hash of what is drawn:

```c
bool NeedMarkerRefresh()
{
    bool need = false;
    int groupMarkers = grp.markers.Count() + grp.pings.Count() + grp.members.Count();
    if (groupMarkers != lastGroupMarkerCount)
    {
        lastGroupMarkerCount = groupMarkers;
        need = true;
    }
    int staticHash = 0;
    foreach (MyServerMarker m : mgr.staticMarkers)
        staticHash += m.CalcHash();
    if (staticHash != lastServerMarkerHash)
    {
        lastServerMarkerHash = staticHash;
        need = true;
    }
    return need;
}

// on the marker: every property that changes how it looks
int CalcHash(bool includePosition)
{
    int hash = type + uid + name.Hash() + colorA * 4546546 + colorR * 52412;
    hash += (int)circleRadius * 546353;
    return hash;
}
```

A canvas overlay guarded this way often checks map position, scale, path, player position and canvas size, but not style, so a new color stays invisible until the player moves the map. Give the shared style a revision counter, bump it whenever the style changes, and compare it at every draw site (`color-picker.md`).
