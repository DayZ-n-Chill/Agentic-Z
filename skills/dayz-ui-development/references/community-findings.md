# UI findings: loading screens, imageset names, draw order, layout typos, image progress bars

Five UI findings. Each one says what was checked on `P:\` (DayZ 1.30) and what is not yet checked on `P:\` or in game.

## UI-1. Loading screen modding: the vanilla classes to hook

**Read `cameras-seats-loading-screens.md` ("Loading screen hook contract") together with this finding.** It is newer and replaces two parts of the example below: the `Timer` used to rotate backgrounds and the hand written `.edds` files.

Four classes can be hooked, all in `P:\scripts\3_game\dayzgame.c`:

- `LoginScreenBase` extends `UIScriptedMenu` at `P:\scripts\3_game\dayzgame.c:63`.
- `LoginQueueBase` extends `LoginScreenBase` at `P:\scripts\3_game\dayzgame.c:110`.
- `LoginTimeBase` extends `LoginScreenBase` at `P:\scripts\3_game\dayzgame.c:213`.
- `LoadingScreen` at `P:\scripts\3_game\dayzgame.c:704` is not a `UIScriptedMenu`. It owns `m_WidgetRoot` directly.

These are the lines on DayZ 1.30. Older game builds have the same classes at other lines, so search for the class name on another version.

`modded class LoginQueueBase extends UIScriptedMenu` is wrong syntax. `modded class` takes no `extends` clause; it changes the existing class. The correct form is `modded class LoginQueueBase { ... }`. The inheritance chain is already `LoginQueueBase`, `LoginScreenBase`, `UIScriptedMenu`.

**`LoadingScreen` fields to use in an override.** The fields are declared at `P:\scripts\3_game\dayzgame.c:706-724` and filled from `m_WidgetRoot.FindAnyWidget` in the constructor at `P:\scripts\3_game\dayzgame.c:729-743`:

```c
TextWidget   m_ModdedWarning;          // "ModdedWarning" — set in m_WidgetRoot.FindAnyWidget
ImageWidget  m_ImageWidgetBackground;  // "ImageBackground"
ImageWidget  m_ImageLogoMid;           // "ImageLogoMid"
ImageWidget  m_ImageLogoCorner;        // "ImageLogoCorner"
ImageWidget  m_ImageLoadingIcon;       // "ImageLoadingIcon"
ImageWidget  m_ImageBackground;        // also "ImageBackground" (alias cast)
ProgressBarWidget m_ProgressLoading;   // "LoadingBar"
TextWidget   m_TextWidgetTitle;        // "TextWidget"
TextWidget   m_TextWidgetStatus;       // "StatusText"
ref Timer    m_Timer;                  // exists, lazy-init pattern OK
```

**Override pattern.** `LoadingScreen` has a plain `void Show()` at `P:\scripts\3_game\dayzgame.c:848` to override:

```c
modded class LoadingScreen
{
    protected ref TStringArray m_LoadingImageNames = {
        "MyMod/data/loading_01.edds",
        "MyMod/data/loading_02.edds"
    };
    protected int   m_CurrentImageIndex;
    protected const float CYCLE_INTERVAL = 15.0;

    override void Show()
    {
        if (m_LoadingImageNames.Count() == 0) {
            super.Show();
            return;
        }
        m_CurrentImageIndex = Math.RandomInt(0, m_LoadingImageNames.Count());
        ApplyCurrentImage();
        m_ImageLogoMid.Show(false);
        m_ImageLogoCorner.Show(false);
        m_ModdedWarning.Show(false);

        if (!m_Timer) m_Timer = new Timer();
        m_Timer.Run(CYCLE_INTERVAL, this, "CycleImage", NULL, true);
        super.Show();
    }

    void CycleImage()
    {
        if (!m_ImageWidgetBackground || m_LoadingImageNames.Count() == 0) return;
        m_CurrentImageIndex++;
        if (m_CurrentImageIndex >= m_LoadingImageNames.Count())
            m_CurrentImageIndex = 0;
        ApplyCurrentImage();
    }

    protected void ApplyCurrentImage()
    {
        string path = m_LoadingImageNames.Get(m_CurrentImageIndex);
        m_ImageWidgetBackground.LoadImageFile(0, path);
    }
}
```

`LoadImageFile(0, path)` accepts either a direct `.edds` or `.paa` path or the imageset form `"set:NAME image:NAME"` (the second form is for imagesets, see UI-2 for the name pitfall). Not yet checked in game.

`LoadMaskTexture(path)` (`P:\scripts\1_core\proto\enwidgets.c:282`) loads the alpha mask layer that vanilla loading screens use. Not yet checked in game: passing `""` removes the vanilla mask.

Open question, not yet checked in game: whether the layout can be swapped from `Show()`.

Checked on `P:\`: the four class declarations, the field list and the `FindAnyWidget` names. Not tested in game: the override itself.

---

## UI-2. An imageset's file name is not its set name

Each `.imageset` file under `P:\gui\imagesets\` has two names:

1. **Filename** — e.g. `dayz_gui.imageset` on disk.
2. **Internal set name** — the `Name` value at the top of the file (`Name "dayz_gui"` at `P:\gui\imagesets\dayz_gui.imageset:2`), also shown in Workbench's right panel `ImageSet` tab. This is what scripts must use in `LoadImageFile(0, "set:NAME image:IMG")`.

The two can differ. When a script passes the file name instead of the set name the image does not appear and nothing is logged.

**Workflow when adding a new imageset:**
1. Create `.imageset` in Workbench.
2. **Check the `ImageSet` tab** for the actual Set name.
3. Use THAT name in scripts.

Checked on `P:\`: the `Name` line of the vanilla imagesets. `/dayz-build-imageset` writes the set name for you when it builds an imageset.

---

## UI-3. Widgets draw in file order, so the background goes first

Workbench draws widgets in the order they appear in the `.layout` file, top to bottom. If a background widget is placed below other widgets in the file, it will be drawn ON TOP of them in-game (covering them).

Rule: the background image widget is the first child in its parent block.

If Workbench reorders during edit (e.g. when adding new widgets), cut and paste the background widget back to the top via plain-text editor before saving.

Not yet checked on `P:\`: there is no vanilla code to cite for the draw order. `Widget.SetSort` (`P:\scripts\1_core\proto\enwidgets.c:130`) changes the order from script.

---

## UI-4. A typo in a layout breaks the file from that point on

The `.layout` parser loads widgets in order until the first syntax error, then stops. Widgets defined after the broken line never appear and nothing says why.

**Symptom you may see:** "all my widgets after the new <X> widget disappeared" → look for a typo or missing brace at the boundary.

Workbench is not the only validator. This repo has two offline checks: the script validator under `scripts/tools/dayz-script-validator/` (brace balance, XML format, missing layout files) and `/dayz-layout-preview`. The matching rule is rule 4 in `rules-and-checklist.md` (brace counts must match).

---

## UI-5. Image based progress bars, and tile mode for segmented bars

DayZ supports image based `ProgressBarWidget` styles, defined in `P:\gui\looknfeel\dayzwidgets.styles` (the `ProgressBarWidget` block starts at line 39). Not yet checked on `P:\`: the vanilla sprites use 0 to 255 alpha (8 bit), and a 1x1 px sprite can be scaled to any size without blur.

**Segmented bar trick.**

The vanilla imageset has an image named `ProgressMenuTileFull` (`P:\gui\imagesets\ccgui_enforce.imageset:4181-4186`, 6 by 8 px, `Flags 3`, where the untiled `ProgressMenuDefaultFullFocus` entry just above it has `Flags 0`). Not yet checked: it has transparent left and right edges and its tile flag set. When a progress bar is wider than this image the engine tiles it across the widget, and the transparent edges become gaps between the repeated colored part. That gives a segmented bar without a custom sprite.

**Use case:** custom HUD bars (health, food, hydration) with a retro tick-mark style.

Checked on `P:\`: the entry name, its size and its `Flags` value. Not checked: that `Flags 3` is the tile flag and how the tiled bar looks in game. Open the imageset in Workbench before relying on it.
