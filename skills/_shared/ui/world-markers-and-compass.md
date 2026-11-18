# World markers, compass and pings

How to pin a widget to a point in the world, slide a compass strip with the camera heading, place a marker on the compass, and drop a ping where the crosshair points. Markers on the map are in `map-and-markers.md`.

The patterns come from a large production group and map mod; `My*` names are its helper classes and are not vanilla. The vanilla calls are cited.

## A widget pinned to a world point

`GetScreenPos(vector world_pos)` (`P:\scripts\3_game\global\game.c:963`) returns screen x and y in pixels, and in index 2 what the engine comment calls the "distance between camera and world_pos" (`:962`). The group mod treats a value of zero or less as behind the camera; the comment does not say so, so that sign is not checked on `P:\`. `GetScreenPosRelative(vector world_pos)` (`:965`) returns x and y as 0 to 1 instead, which suits a marker placed by fraction in a full screen parent.

```c
vector screenPos = GetGame().GetScreenPos(worldPosition);
float x = screenPos[0];
float y = screenPos[1];
if (x <= 0 || x >= screenWidth || y <= 0 || y >= screenHeight || screenPos[2] <= 0)
{
    widget.Show(false); // off screen or behind the camera
    return;
}
if (ShouldCenterWidget())
{
    x -= widthMainWidget;  // half the width
    y -= heightMainWidget; // half the height
}
widget.SetPos(x, y);
widget.Show(true);
```

The group mod centers ping and player markers on the point. `SetPos` takes layout units, so pixel values land in the right place only when the widget's position is exact and the screen is 1080 high; with pixels from `GetScreenPos` use `SetScreenPos(x, y)` (`P:\scripts\1_core\proto\enwidgets.c:142`) instead.

## A compass strip

Read the camera heading with `GetCurrentCameraDirection()` (`game.c:732`), fold it into -180 to 180, and slide the strip image by it:

```c
vector angles = GetGame().GetCurrentCameraDirection().VectorToAngles();
float cameraAngle = angles[0];
if (cameraAngle > 180)
    cameraAngle -= 360;
compassImage.SetPos((-cameraAngle / 180.0) - 1.0, 0);
```

Place a marker on the strip by its angle relative to the camera:

```c
float MyMod_GetMarkerAngle(vector markerPosition, float currentCameraAngle)
{
    vector dir = (GetGame().GetCurrentCameraPosition() - markerPosition).Normalized();
    float angle = dir.VectorToAngles()[0] - currentCameraAngle + 360;
    while (angle > 180)
        angle -= 360;
    return angle;
}

float posX = (MyMod_GetMarkerAngle(markerPosition, cameraAngle) / 180.0) - 0.5;
if (posX < -1)
    posX += 2;
compassWidget.SetPos(posX, 0);
```

## A ping where the crosshair points

Cast a ray from the camera 2,000 m along its direction against terrain, buildings and vehicles, and put the marker at the hit. `RayCastBullet` is at `P:\scripts\3_game\global\dayzphysics.c:211`:

```c
void MyMod_AddPing()
{
    vector camPos = GetGame().GetCurrentCameraPosition();
    vector camDir = GetGame().GetCurrentCameraDirection().Normalized() * 2000.0;
    Object hitObj;
    vector hitPos, hitNormal;
    float fraction;
    PhxInteractionLayers layers = PhxInteractionLayers.TERRAIN | PhxInteractionLayers.BUILDING | PhxInteractionLayers.VEHICLE;
    DayZPhysics.RayCastBullet(camPos, camPos + camDir, layers, GetGame().GetPlayer(), hitObj, hitPos, hitNormal, fraction);

    MyMarker marker = new MyMarker();
    marker.SetupMarker(MyMarkerType.GROUP_PING, playerName, "", hitPos);
    group.AddMarker(marker);
}
```

## Player list rows

A row hides itself for an offline member, colors its health bar between two configured colors, and switches distance from meters to kilometres at 1,000 m:

```c
void UpdateWidget()
{
    if (!member || !member.online)
    {
        Show(false);
        return;
    }
    healthbar.SetColor(MyConverter.MixColors(colorFull, colorZero, member.health / 100.0));
    playername.SetText(member.name);

    float dist = vector.Distance(member.position, cameraPos);
    if (dist < 1000)
        distance.SetText("" + (int)dist + "m");
    else
        distance.SetText("" + ((int)(dist / 100)) / 10.0 + "km");
}
```
