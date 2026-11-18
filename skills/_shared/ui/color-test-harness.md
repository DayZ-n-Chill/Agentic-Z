# Color test panel

How to build a small diagnostic mod that shows ten swatches of known ARGB colors in game, and how to run the two screenshot comparison that tells you how far drawn colors sit from their hex values. Where UI colors come from is in `theme-and-color.md`.

This panel is a measuring tool, not a pattern to copy. It calls `Widget.SetLV(0)` on purpose. A mod never does: `SetLV` and `SetTextLV` are `proto static` and set one global value for every widget (`P:\scripts\1_core\proto\enwidgets.c:115` and `:117`), and vanilla uses them to apply the HUD brightness the player chose (`SetHudBrightness`, `P:\scripts\3_game\dayzgame.c:3910` to `:3914`). Close the game after each test so the player's value comes back.

The code is not checked in game on 1.30.

## What the result means

The darkening this panel measures is the player's HUD brightness setting, not a renderer fault. `SetLV` takes a value from -15 to 0, where lower is darker and 0 is the default (`enwidgets.c:114`). A test client whose brightness slider is turned down draws every swatch darker; `SetLV(0)` brightens them only because it overrides that setting. Design against the player's setting; never reset it (`engine-widget-facts.md`, "The global HUD brightness").

## The mod

Three files under `workspace/ColorTest/`. The swatches need a texture: a procedural texture string such as `#(argb,8,8,3)color(1,1,1,1,CO)` is rejected by `LoadImageFile` with "Bad texture name" (measured in game on 1.29; see `checklist-and-troubleshooting.md`, "Frames and panels draw nothing alone"), so ship a 1x1 white texture as `ColorTest/data/white.edds`.

`config.cpp`:

```cpp
class CfgPatches
{
    class ColorTest
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = { "DZ_Scripts", "DZ_Data" };
    };
};

class CfgMods
{
    class ColorTest
    {
        type = "mod";
        name = "ColorTest";
        dir = "ColorTest";
        class defs
        {
            class missionScriptModule
            {
                value = "";
                files[] = { "ColorTest/scripts/5_Mission" };
            };
        };
    };
};
```

`$PBOPREFIX$` holds the single line `ColorTest`.

`scripts/5_Mission/ColorTest.c` builds the panel from script with `WorkspaceWidget.CreateWidget(type, left, top, width, height, flags, color, sort, parent)` (`P:\scripts\1_core\proto\enwidgets.c:179`) and toggles it on F7:

```c
class ColorTestPanel
{
    protected static ref ColorTestPanel s_Instance;
    protected Widget m_Root;
    protected bool m_Open;

    static void Toggle()
    {
        if (!s_Instance)
            s_Instance = new ColorTestPanel();
        if (s_Instance.m_Open)
            s_Instance.Close();
        else
            s_Instance.Open();
    }

    void ~ColorTestPanel()
    {
        if (m_Root)
            m_Root.Unlink();
    }

    void Open()
    {
        if (!m_Root)
            Build();
        if (!m_Root)
            return;
        // Test A keeps these two lines; test B comments them out.
        Widget.SetLV(0);
        Widget.SetTextLV(0);
        m_Root.Show(true);
        m_Open = true;
    }

    void Close()
    {
        if (m_Root)
            m_Root.Show(false);
        m_Open = false;
    }

    protected Widget Add(WorkspaceWidget ws, WidgetType type, int x, int y, int w, int h, int color, int extraFlags)
    {
        int flags = WidgetFlags.VISIBLE | WidgetFlags.EXACTPOS | WidgetFlags.EXACTSIZE | WidgetFlags.IGNOREPOINTER | extraFlags;
        return ws.CreateWidget(type, x, y, w, h, flags, color, 0, m_Root);
    }

    protected void Build()
    {
        WorkspaceWidget ws = GetGame().GetWorkspace();
        if (!ws)
            return;
        m_Root = ws.CreateWidget(FrameWidgetTypeID, 100, 100, 420, 520, WidgetFlags.VISIBLE | WidgetFlags.EXACTPOS | WidgetFlags.EXACTSIZE, 0, 50000);
        if (!m_Root)
            return;

        ImageWidget bg = ImageWidget.Cast(Add(ws, ImageWidgetTypeID, 0, 0, 420, 520, ARGB(240, 20, 20, 20), WidgetFlags.STRETCH));
        if (bg)
            bg.LoadImageFile(0, "ColorTest/data/white.edds");
        TextWidget title = TextWidget.Cast(Add(ws, TextWidgetTypeID, 10, 10, 400, 30, ARGB(255, 255, 255, 255), 0));
        if (title)
            title.SetText("ColorTest - F7 to close");

        array<int> colors = { 0xFFFF0000, 0xFF00FF00, 0xFF0000FF, 0xFFFFFFFF, 0xFF808080,
            0xFF404040, 0xFF34D399, 0xFFF87171, 0xFF60A5FA, 0x80FFFFFF };
        array<string> labels = { "FF FF0000 red", "FF 00FF00 green", "FF 0000FF blue", "FF FFFFFF white", "FF 808080 gray 50%",
            "FF 404040 gray 25%", "FF 34D399 emerald", "FF F87171 light red", "FF 60A5FA light blue", "80 FFFFFF white at half alpha" };

        for (int i = 0; i < colors.Count(); i++)
        {
            int y = 50 + i * 46;
            ImageWidget swatch = ImageWidget.Cast(Add(ws, ImageWidgetTypeID, 10, y, 80, 40, colors[i], WidgetFlags.STRETCH));
            if (swatch)
            {
                swatch.LoadImageFile(0, "ColorTest/data/white.edds");
                swatch.SetColor(colors[i]);
            }
            TextWidget label = TextWidget.Cast(Add(ws, TextWidgetTypeID, 100, y, 310, 40, ARGB(255, 220, 220, 220), 0));
            if (label)
                label.SetText(labels[i]);
        }
    }
}

modded class MissionGameplay
{
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);
        if (key == KeyCode.KC_F7)
            ColorTestPanel.Toggle();
    }
}
```

Compare the key with its `KeyCode` name (`KC_F7`, `P:\scripts\1_core\proto\ensystem.c:222`), not a raw number.

## Running the comparison

1. Pack the mod with `/dayz-build-pbo` and load it with `/dayz-launch-test`.
2. Press F7 and take a screenshot. This is test A, with `SetLV(0)` active.
3. Close the game, comment out the `SetLV` and `SetTextLV` lines, pack and launch again.
4. Press F7 and take a second screenshot. This is test B.
5. Keep both screenshots and the RPT.

Reading them:

- Test A matches the hex values: the darkening comes from the LV value, which is the player's brightness setting. Design against it.
- Test A is still dark: the darkening comes from the renderer, not LV.
- In both, measure each swatch against its hex value. The 50 percent gray is the easiest: if `808080` reads as `5C5C5C`, that ratio is the darkening factor.
