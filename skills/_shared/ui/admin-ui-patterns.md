# Admin tool UI

How admin style tools build their screens: floating windows you drag and resize, labels that follow objects in the world, a skeleton drawn on a canvas, box selection, a numpad menu, an orbiting camera preview and looking around while a menu stays open. Scaling script pixel values to the screen is in `screen-scaling.md`.

The code here is a pattern taken from admin tools, not a vanilla excerpt, and it is not checked in game. Check each call against the source column before you copy it. Names that start with `My` (`MyWidgetUtils`, `MyAdminMenuFrame`) are helper classes you write yourself.

## Floating windows

Each panel (player info, ESP, item spawner) is one subclass of a `MyAdminMenuFrame` base. Each frame loads its own layout into a shared container that carries the header and the resize handles. A main menu class registers frames by class name and creates them with `typename.Spawn()`. The player can reorder frames by drag and drop, and the order is saved.

Resize works from all eight edges and corners. Find which handle is under the cursor, then move that edge by the mouse delta every frame and clamp to a minimum size and the screen:

```c
if (MyWidgetUtils.IsUnderMouse(resize_bottom_right)) { resizeBottom = true; resizeRight = true; }

// every frame while dragging
if (resizeBottom)
{
    int diffY = dragStartY - mouseY;
    dragStartY = mouseY;
    float w, h;
    frame.GetScreenSize(w, h);
    frame.SetScreenSize(w, h - diffY);
}
```

`SetScreenSize` and `SetScreenPos` take screen pixels (`P:\scripts\1_core\proto\enwidgets.c:142` and `:143`). Save window positions and sizes divided by the screen scale and multiply them back on load, so a saved layout survives a resolution change (`screen-scaling.md`). The tools keep nine preset slots, each holding every window's rect, switched by hotkey.

Bring the focused frame to the front with `frame.SetSort(120)` and send the others back with `SetSort(0)` (`SetSort(int sort, bool immedUpdate = true)`, `enwidgets.c:130`). Frames holding a `MapWidget` or an `ItemPreviewWidget` get a lower sort; the tools do this to dodge a render bug, which is not checked in game.

## Labels that follow objects

Collect the objects once, then place one label per object every frame. `GetScreenPos(vector world_pos)` (`P:\scripts\3_game\global\game.c:963`) returns screen x and y plus a depth; a depth of zero or less means the point is behind the camera:

```c
DayZPlayerUtils.SceneGetEntitiesInBox("0 -1000 0", Vector(mapSize, 10000, mapSize), allItems);

// every frame
vector camPos = g_Game.GetCurrentCameraPosition();
foreach (EntityAI item : allItems)
{
    vector pos = item.GetPosition();
    PlayerBase pb = PlayerBase.Cast(item);
    if (pb)
    {
        int bone = pb.GetBoneIndexByName("Head");
        if (bone != -1)
            pos = pb.GetBonePositionWS(bone);
    }
    float distance = vector.Distance(pos, camPos);
    vector screen = g_Game.GetScreenPos(pos);
    if (screen[2] > 0 && screen[0] > 0 && screen[1] > 0)
    {
        widget.SetScreenPos(screen[0], screen[1]);
        widget.Show(true);
        widget.SetSort(1000 - (int)Math.Clamp(distance, 0, 1000)); // nearer draws in front
        distanceText.SetText("(" + (int)distance + "m)");
    }
    else
        widget.Show(false);
}
```

Sources: `SceneGetEntitiesInBox` (`P:\scripts\4_world\entities\dayzplayerutils.c:75`), `GetBonePositionWS(int pivot)` (`P:\scripts\3_game\entities\object.c:238`), the player's `GetBoneIndexByName(string pBoneName)` (`P:\scripts\3_game\human.c:1417`).

To register objects, the tools give `ItemBase`, `PlayerBase`, `AnimalBase`, `ZombieBase`, `CarScript` and `BoatScript` a modded constructor that adds the object when the overlay is on. `EEHealthLevelChanged` refreshes the health mark, and `EEItemLocationChanged` adds or removes an item as it moves to or from the ground.

## A skeleton on a canvas

Clear the `CanvasWidget` every frame and draw a line between each pair of visible bones (`DrawLine` and `Clear`, `P:\scripts\1_core\proto\enwidgets.c:341` to `:345`):

```c
void MyMod_DrawBones(CanvasWidget canvas, PlayerBase player, int thickness, int color, TStringArray boneNames)
{
    vector lastScreen;
    bool lastVisible = false;
    foreach (string boneName : boneNames)
    {
        int bone = player.GetBoneIndexByName(boneName);
        if (bone < 0)
            continue;
        vector screen = g_Game.GetScreenPos(player.GetBonePositionWS(bone));
        if (screen[2] <= 0) { lastVisible = false; continue; }
        if (lastVisible)
            canvas.DrawLine(screen[0], screen[1], lastScreen[0], lastScreen[1], thickness, color);
        lastScreen = screen;
        lastVisible = true;
    }
}
```

The bone chains the tools draw, each in order:

| Chain | Bones |
|---|---|
| Spine | `pelvis`, `spine`, `spine1`, `spine2`, `spine3`, `neck`, `neck1`, `head`, `face_forehead` |
| Arms | `lefthand`, `leftforearmroll`, `leftforearm`, `leftarmroll`, `leftarm`, `neck`, `rightarm`, and on down the right arm |
| Legs | `righttoebase`, `rightfoot`, `rightlegroll`, `rightleg`, `rightupleg`, `pelvis` |

Thickness drops with distance: 3 pixels under 10 m, 2 under 100 m, 1 beyond.

## Box selection

On shift and drag, remember the start with `GetMousePos(out int x, out int y)` (`P:\scripts\1_core\proto\ensystem.c:329`), then every frame stretch a panel from the start to the cursor, flipping when the drag goes left or up:

```c
int mouseX, mouseY;
GetMousePos(mouseX, mouseY);
int x = selectX, y = selectY;
int w = mouseX - selectX, h = mouseY - selectY;
if (w < 0) { x = mouseX; w = -w; }
if (h < 0) { y = mouseY; h = -h; }
panel_selection.SetScreenPos(x, y);
panel_selection.SetScreenSize(w, h);
```

A label is selected when its screen position falls inside `x`, `y`, `x + w`, `y + h`.

## Widget calls the tools lean on

| Widget | Calls | Source |
|---|---|---|
| `TextListboxWidget` | `AddItem(text, userData, column, row = -1)`, `SetItem(position, text, userData, column)`, `GetItemData(row, column, out data)`, `SetItemColor(row, column, color)` | `P:\scripts\1_core\proto\enwidgets.c:439` to `:458` |
| Any list box | `ClearItems()`, `GetNumItems()`, `SelectRow(row)`, `GetSelectedRow()` (`-1` when nothing is selected) | `enwidgets.c:425` to `:433` |
| `SliderWidget` | `SetMinMax(min, max)`, `SetStep(step)`, `SetCurrent(value)`, `GetCurrent()` | `enwidgets.c:358` to `:367` |
| `XComboBoxWidget` | `ClearAll()`, `AddItem(text)`, `SetCurrentItem(n)`, `GetCurrentItem()` | `enwidgets.c:407` to `:416` |
| `ImageWidget` | `LoadImageFile(num, name, noCache = false)` | `enwidgets.c:257` |
| `TextWidget` | `SetTextExactSize(size)`, `SetOutline(outlineSize, argb)`, `GetOutlineSize()`, `GetOutlineColor()` | `enwidgets.c:193` to `:198` |
| `Widget` | `SetSort(sort)` (higher draws in front), `SetRotation(roll, pitch, yaw)` in degrees, `Update()` to recalculate the layout now | `enwidgets.c:130`, `:146`, `:164` |
| Global | `GetWidgetUnderCursor()`, `CancelWidgetDragging()`, `GetDragWidget()` | `enwidgets.c:184` to `:186` |
| Global | `SetFocus(Widget w)`, `null` clears focus | `enwidgets.c:698` |
| Global | `GetMouseState(MouseState index)`; test the raw button with `GetMouseState(MouseState.LEFT) & MB_PRESSED_MASK`, as the vanilla comment shows (`:324`). No script declares `MB_PRESSED_MASK`; its declaration is commented out (`:319`), so whether the engine provides it is not checked on `P:\` | `P:\scripts\1_core\proto\ensystem.c:326` |
| `PlayerPreviewWidget` | `SetPlayer`, `UpdateItemInHands`, `GetDummyPlayer`, `Refresh` | `P:\scripts\3_game\gameplay.c:305` to `:313` |

## A numpad menu

Catch keys in `MissionGameplay.OnKeyPress(int key)` (`P:\scripts\5_mission\mission\missiongameplay.c:742`) and pass them to the open menu:

```c
modded class MissionGameplay
{
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);
        MyMod_PinMenu pinMenu;
        if (Class.CastTo(pinMenu, g_Game.GetUIManager().GetMenu()))
            pinMenu.OnKeyNumpadPressed(key);
    }
}
```

This calls `super` first because it only listens. When the mod consumes a key that vanilla also binds and prompts for (F is the vanilla action key), return without calling `super.OnKeyPress`, or the mod and the vanilla action manager both act on the same press (seen in a mod, not checked on `P:\`).

The `KeyCode` names to map are `KC_0` to `KC_9`, `KC_NUMPAD0` to `KC_NUMPAD9`, `KC_BACK` (`P:\scripts\1_core\proto\ensystem.c:171`), `KC_RETURN` (`:185`) and `KC_NUMPADENTER` (`:253`).

## An orbiting camera preview

A garage style menu shows a vehicle or item from a camera that circles it:

```c
float height = Math.Sin(Math.DEG2RAD * angle) * distance;
float cosR = Math.Cos(Math.DEG2RAD * rotation) * distance;
float sinR = Math.Sin(Math.DEG2RAD * rotation) * distance;
vector cameraPos = center + Vector(sinR, height, cosR);
```

One tool hides the scene by spawning an invisible building at a height of 109 m, showing the items inside it and setting the world time to noon every frame. Not checked in game.

## Looking around with a menu open

Drop the menu's input excludes and hide the cursor to let the player turn the camera, then put both back (`RemoveActiveInputExcludes` and `AddActiveInputExcludes`, `P:\scripts\3_game\gameplay.c:798` to `:800`; `ShowUICursor(bool visible)`, `P:\scripts\3_game\tools\uimanager.c:244`):

```c
Mission mission = g_Game.GetMission();
mission.RemoveActiveInputExcludes({"menu", "movement", "aiming"}, true);
g_Game.GetUIManager().ShowUICursor(false);

// back to the menu
mission.AddActiveInputExcludes({"movement", "aiming", "menu"});
g_Game.GetUIManager().ShowUICursor(true);
```
