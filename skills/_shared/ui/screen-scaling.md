# Scaling script pixels to the screen

How to keep sizes and positions that script sets in screen pixels the same on every resolution, which values need the multiplier, and which the engine already scales for you.

The pattern comes from admin tools and is not checked in game except where a line says so. `MyWidgetUtils` and `MyGapHandler` are helper classes you write yourself.

## One scale, taken from the height

Design at 1920 by 1080 and scale at run time. Read the screen with the global `GetScreenSize(out int x, out int y)` (`P:\scripts\1_core\proto\ensystem.c:331`):

```c
class MyWidgetUtils
{
    static int screenWidth, screenHeight;
    static float heightScale; // screenHeight / 1080
    static float widthScale;  // screenWidth / 1920, rarely used

    static void UpdateScreenDimensions()
    {
        GetScreenSize(screenWidth, screenHeight);
        heightScale = screenHeight / 1080.0;
        widthScale = screenWidth / 1920.0;
    }
}
```

Call it once at start and again on `WindowsResizeEventTypeID`, the event `MissionGameplay` already handles (`P:\scripts\5_mission\mission\missiongameplay.c:788`).

Use `heightScale` for every dimension, widths included, so squares stay square on any aspect ratio:

```c
txt.SetTextExactSize(16 * MyWidgetUtils.heightScale);          // 16 px at 1080p
img.SetScreenSize(300 * MyWidgetUtils.heightScale, 200 * MyWidgetUtils.heightScale);       // 300 by 200 at 1080p
widget.SetScreenPos(500 * MyWidgetUtils.heightScale, 300 * MyWidgetUtils.heightScale);     // 500, 300 in 1080p space
float gap = 10.0 * MyWidgetUtils.heightScale;
```

`SetScreenPos` and `SetScreenSize` are at `P:\scripts\1_core\proto\enwidgets.c:142` and `:143`; `SetTextExactSize` at `:193`.

## Saving window rects

Divide by the scale when you save and multiply when you restore, so a saved rect is in 1080p space and still fits after the player changes resolution:

```c
entry.windowX = x / MyWidgetUtils.heightScale;
entry.windowY = y / MyWidgetUtils.heightScale;
entry.windowW = w / MyWidgetUtils.heightScale;
entry.windowH = h / MyWidgetUtils.heightScale;

widget.SetScreenPos(entry.windowX * MyWidgetUtils.heightScale, entry.windowY * MyWidgetUtils.heightScale);
widget.SetScreenSize(entry.windowW * MyWidgetUtils.heightScale, entry.windowH * MyWidgetUtils.heightScale);
```

## Gaps, image fit and text fit

A margin that follows resolution: a `ScriptedWidgetEventHandler` reads `gapHorizontal` and `gapVertical` from the layout through the `reference` keyword and shrinks its root, which is sized as a fraction of its parent:

```c
float newW = width - gapHorizontal * MyWidgetUtils.heightScale / parentW;
float newH = height - gapVertical * MyWidgetUtils.heightScale / parentH;
root.SetSize(newW, newH);
```

Fit an image inside a box and keep its aspect ratio by scaling on the tighter axis:

```c
float scale = Math.Min(containerW / imgW, containerH / imgH);
img.SetScreenSize(imgW * scale, imgH * scale);
```

Find the largest font size that fits the parent's width. `Update()` (`enwidgets.c:164`) makes the widget recalculate before you read its size:

```c
void MyMod_FitText(TextWidget txt, int maxSize, int minSize)
{
    float w, h, parentW, parentH;
    txt.GetParent().GetScreenSize(parentW, parentH);
    for (int size = maxSize; size >= minSize; size--)
    {
        txt.SetTextExactSize(size);
        txt.Update();
        txt.GetScreenSize(w, h);
        if (w < parentW * 0.9)
            break;
    }
}
```

## What needs no multiplier

| Value | Why |
|---|---|
| Layout values between 0 and 1 (fraction of the parent) | The engine sizes them from the parent. |
| Children of a `SpacerWidget` or `WrapSpacerWidget` | They flow inside the spacer at any resolution. |
| `SetSize(w, h)` with fractions | Fraction of the parent. |
| Exact unit values in a layout, and `SetSize` on an exact widget | The engine already draws exact units at screen height over 1080 (measured in game; see `checklist-and-troubleshooting.md`). Multiplying again scales them twice: `SetSize` 480 drew 320 at 720p. |

Only pixel values need the multiplier: `SetScreenSize`, `SetScreenPos`, `SetTextExactSize`, pixel gaps, and any fixed distance used for hit tests or screen math. The layout key `"exact text size"` on an SDF font already scales with the screen height (`text-sizing-and-rendering.md`); whether `SetTextExactSize` does the same is not measured.
