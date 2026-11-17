# Color test harness: an in game panel that measures how UI colors are drawn

`LF_ColorTest` is a tiny diagnostic mod: F7 opens a panel with 10 swatches of known ARGB colors, so a screenshot shows how far the drawn colors sit from their hex values. It was written to measure the effect of `Widget.SetLV`.

**This is a diagnostic harness, not a pattern to copy.** It calls `Widget.SetLV(0)` on purpose, to measure. A mod must not do this: `SetLV` and `SetTextLV` are `proto static` and global (`P:\scripts\1_core\proto\enwidgets.c:114-117`), and vanilla uses them to apply the brightness the player chose (`SetHudBrightness` at `P:\scripts\3_game\dayzgame.c:3910-3914`). When you run this test, put the value back when you close it. See `theme-and-color.md`, "Color system".

Two more things to know before you run it:

- The harness paints its swatches with the procedural texture `#(argb,8,8,3)color(1,1,1,1,CO)`. Measured in game on DayZ 1.29: `ImageWidget.LoadImageFile` rejects that string ("Bad texture name"), which leaves the swatch without a texture (`rules-and-checklist.md`, rule 2). When the swatches come out wrong, ship a 1x1 white `.edds` and load that.
- The result this harness produced was first read as "`SetLV(0)` fixes dark colors" and later retracted: it measured the test machine's HUD brightness setting (`lfpg-knowledge-base.md`, finding 6).

The harness code below is not yet checked in game on 1.30.

## What it does
- F7 opens a panel with 10 rectangles of known ARGB colors
- Shows the hex value of each color next to it
- Tests `Widget.SetLV(0)` upon opening to see if it normalizes colors
- You take a screenshot of the panel and compare it with the expected hex values
- Second test: comment out the SetLV(0) line, reload, screenshot again
- Comparing both screenshots gives the exact darkening factor

## Files

### config.cpp
```cpp
class CfgPatches
{
    class LF_ColorTest
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = { "DZ_Scripts", "DZ_Data" };
    };
};

class CfgMods
{
    class LF_ColorTest
    {
        type = "mod";
        name = "LF_ColorTest";
        dir = "LF_ColorTest";
        class defs
        {
            class missionScriptModule
            {
                value = "";
                files[] = { "LF_ColorTest/scripts/5_Mission" };
            };
        };
    };
};
```

### $PBOPREFIX$
```
LF_ColorTest
```

### scripts/5_Mission/LF_ColorTest.c

```c
// LF_ColorTest: DayZ color diagnostics
// F7 opens and closes the panel

class LF_ColorTestPanel
{
    protected static ref LF_ColorTestPanel s_Instance;
    protected Widget m_Root;
    protected bool m_Open;

    static void Toggle()
    {
        if (!s_Instance)
        {
            s_Instance = new LF_ColorTestPanel();
        }

        if (s_Instance.m_Open)
        {
            s_Instance.Close();
        }
        else
        {
            s_Instance.Open();
        }
    }

    void LF_ColorTestPanel()
    {
        m_Open = false;
    }

    void ~LF_ColorTestPanel()
    {
        if (m_Root)
        {
            m_Root.Unlink();
        }
    }

    void Open()
    {
        if (!m_Root)
        {
            Build();
        }

        if (!m_Root)
        {
            return;
        }

        // ===== TEST: SetLV(0) to normalize colors (diagnostic only) =====
        // First test: with this line active. Screenshot.
        // Second test: comment out this line. Screenshot.
        Widget.SetLV(0);
        Widget.SetTextLV(0);
        // ==================================================

        m_Root.Show(true);
        m_Open = true;
        Print("[ColorTest] Panel opened. SetLV(0) applied.");
    }

    void Close()
    {
        if (m_Root)
        {
            m_Root.Show(false);
        }
        m_Open = false;
        Print("[ColorTest] Panel closed.");
    }

    protected void Build()
    {
        WorkspaceWidget ws = GetGame().GetWorkspace();
        if (!ws)
        {
            Print("[ColorTest] ERROR: workspace null");
            return;
        }

        // Root frame
        int rootFlags = WidgetFlags.VISIBLE;
        rootFlags = rootFlags | WidgetFlags.EXACTPOS;
        rootFlags = rootFlags | WidgetFlags.EXACTSIZE;
        m_Root = ws.CreateWidget(FrameWidgetTypeID, 100, 100, 420, 520, rootFlags, 0, 50000);
        if (!m_Root)
        {
            Print("[ColorTest] ERROR: could not create root");
            return;
        }

        // Background
        int bgFlags = WidgetFlags.VISIBLE;
        bgFlags = bgFlags | WidgetFlags.EXACTPOS;
        bgFlags = bgFlags | WidgetFlags.EXACTSIZE;
        bgFlags = bgFlags | WidgetFlags.IGNOREPOINTER;
        bgFlags = bgFlags | WidgetFlags.STRETCH;
        Widget bgW = ws.CreateWidget(ImageWidgetTypeID, 0, 0, 420, 520, bgFlags, ARGB(240, 20, 20, 20), 0, m_Root);
        ImageWidget bg = ImageWidget.Cast(bgW);
        if (bg)
        {
            string texPath = "#(argb,8,8,3)color(1,1,1,1,CO)";
            bg.LoadImageFile(0, texPath);
            bg.SetColor(ARGB(240, 20, 20, 20));
        }

        // Title
        int txtFlags = WidgetFlags.VISIBLE;
        txtFlags = txtFlags | WidgetFlags.EXACTPOS;
        txtFlags = txtFlags | WidgetFlags.EXACTSIZE;
        txtFlags = txtFlags | WidgetFlags.IGNOREPOINTER;
        Widget titleW = ws.CreateWidget(TextWidgetTypeID, 10, 10, 400, 30, txtFlags, ARGB(255, 255, 255, 255), 0, m_Root);
        TextWidget title = TextWidget.Cast(titleW);
        if (title)
        {
            string titleText = "LF ColorTest - F7 to close";
            title.SetText(titleText);
        }

        // 10 color swatches
        // Each: known ARGB → ImageWidget + TextWidget with hex label
        ref array<int> colors = new array<int>();
        ref array<string> labels = new array<string>();

        colors.Insert(ARGB(255, 255, 0, 0));
        labels.Insert("FF FF0000 Pure red");

        colors.Insert(ARGB(255, 0, 255, 0));
        labels.Insert("FF 00FF00 Pure green");

        colors.Insert(ARGB(255, 0, 0, 255));
        labels.Insert("FF 0000FF Pure blue");

        colors.Insert(ARGB(255, 255, 255, 255));
        labels.Insert("FF FFFFFF White");

        colors.Insert(ARGB(255, 128, 128, 128));
        labels.Insert("FF 808080 Gray 50%");

        colors.Insert(ARGB(255, 64, 64, 64));
        labels.Insert("FF 404040 Gray 25%");

        colors.Insert(ARGB(255, 52, 211, 153));
        labels.Insert("FF 34D399 Emerald 400");

        colors.Insert(ARGB(255, 248, 113, 113));
        labels.Insert("FF F87171 Red 400");

        colors.Insert(ARGB(255, 96, 165, 250));
        labels.Insert("FF 60A5FA Blue 400");

        colors.Insert(ARGB(128, 255, 255, 255));
        labels.Insert("80 FFFFFF White 50% alpha");

        int i = 0;
        int yOffset = 50;
        int swatchH = 40;
        int gap = 6;

        for (i = 0; i < colors.Count(); i = i + 1)
        {
            int cy = yOffset + (i * (swatchH + gap));
            int col = colors.Get(i);
            string lab = labels.Get(i);

            // Color swatch
            int swFlags = WidgetFlags.VISIBLE;
            swFlags = swFlags | WidgetFlags.EXACTPOS;
            swFlags = swFlags | WidgetFlags.EXACTSIZE;
            swFlags = swFlags | WidgetFlags.IGNOREPOINTER;
            swFlags = swFlags | WidgetFlags.STRETCH;
            Widget swW = ws.CreateWidget(ImageWidgetTypeID, 10, cy, 80, swatchH, swFlags, col, 0, m_Root);
            ImageWidget sw = ImageWidget.Cast(swW);
            if (sw)
            {
                string swTex = "#(argb,8,8,3)color(1,1,1,1,CO)";
                sw.LoadImageFile(0, swTex);
                sw.SetColor(col);
            }

            // Label
            int lbFlags = WidgetFlags.VISIBLE;
            lbFlags = lbFlags | WidgetFlags.EXACTPOS;
            lbFlags = lbFlags | WidgetFlags.EXACTSIZE;
            lbFlags = lbFlags | WidgetFlags.IGNOREPOINTER;
            Widget lbW = ws.CreateWidget(TextWidgetTypeID, 100, cy, 310, swatchH, lbFlags, ARGB(255, 220, 220, 220), 0, m_Root);
            TextWidget lb = TextWidget.Cast(lbW);
            if (lb)
            {
                lb.SetText(lab);
            }

            // Log
            string logMsg = "[ColorTest] Swatch ";
            logMsg = logMsg + i.ToString();
            logMsg = logMsg + ": ";
            logMsg = logMsg + lab;
            Print(logMsg);
        }

        Print("[ColorTest] Panel built with 10 swatches.");
    }
}

modded class MissionGameplay
{
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);

        // Compare against the KeyCode name, not a raw number.
        if (key == KeyCode.KC_F7)
        {
            LF_ColorTestPanel.Toggle();
        }
    }
}
```

## User instructions

1. Create the mod as `workspace/LF_ColorTest/` with the files above, then pack it with `/dayz-build-pbo`
2. Load the mod on the local test server with `/dayz-launch-test`
3. In game: press F7
4. **Test A**: Screenshot of the panel (with SetLV(0) active)
5. Close game
6. Comment the lines `Widget.SetLV(0)` and `Widget.SetTextLV(0)` in the script
7. Reload
8. **Test B**: Screenshot of the panel (without SetLV)
9. Keep both screenshots and the `.RPT`

## What we are looking for

Comparing Test A vs Test B:
- If Test A shows colors identical to the hex values, the darkening comes from the LV value. That is the player's HUD brightness setting, so it is a thing to design against, not to reset
- If Test A remains dark, the darkening comes from the renderer, not LV
- In both: measure how much darker each swatch is vs the expected hex
  (50% gray above all: if 808080 looks like 5C5C5C, that gives the factor)
