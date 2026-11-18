# Imagesets, draw order, layout typos and image progress bars

Four layout findings: an imageset's file name is not its set name (with the imageset text format), widgets draw in file order, a typo stops the parser, and image based and segmented progress bars. Each says what was checked on `P:\` (DayZ 1.30) and what is not yet checked on `P:\` or in game.

## 1. An imageset's file name is not its set name

Each `.imageset` file under `P:\gui\imagesets\` has two names:

1. **Filename** — e.g. `dayz_gui.imageset` on disk.
2. **Internal set name** — the `Name` value at the top of the file (`Name "dayz_gui"` at `P:\gui\imagesets\dayz_gui.imageset:2`), also shown in Workbench's right panel `ImageSet` tab. This is what scripts must use in `LoadImageFile(0, "set:NAME image:IMG")`.

The two can differ. When a script passes the file name instead of the set name the image does not appear and nothing is logged.

**Workflow when adding a new imageset:**
1. Create `.imageset` in Workbench.
2. **Check the `ImageSet` tab** for the actual Set name.
3. Use THAT name in scripts.

**The text format.** An `.imageset` is plain text and can be read and patched without Workbench:

```text
ImageSetClass {
 Name "<setname>"
 RefSize W H
 Textures {
  ImageSetTextureClass { mpix N path "{GUID}Gui/imagesets/x.edds" }
 }
 Images {
  ImageSetDefClass X { Name "X" Pos x y Size w h Flags N }
 }
}
```

The header shape is at `P:\gui\imagesets\ccgui_enforce.imageset:1-10`.

Checked on `P:\`: the `Name` line of the vanilla imagesets. `/dayz-build-imageset` writes the set name for you when it builds an imageset.

---

## 2. Widgets draw in file order, so the background goes first

Workbench draws widgets in the order they appear in the `.layout` file, top to bottom. If a background widget is placed below other widgets in the file, it will be drawn ON TOP of them in-game (covering them).

Rule: the background image widget is the first child in its parent block.

If Workbench reorders during edit (e.g. when adding new widgets), cut and paste the background widget back to the top via plain-text editor before saving.

Not yet checked on `P:\`: there is no vanilla code to cite for the draw order. `Widget.SetSort` (`P:\scripts\1_core\proto\enwidgets.c:130`) changes the order from script.

---

## 3. A typo in a layout breaks the file from that point on

The `.layout` parser loads widgets in order until the first syntax error, then stops. Widgets defined after the broken line never appear and nothing says why.

**Symptom you may see:** "all my widgets after the new <X> widget disappeared" → look for a typo or missing brace at the boundary.

Workbench is not the only validator. This repo has two offline checks: the script validator under `scripts/tools/dayz-script-validator/` (brace balance, XML format, missing layout files) and `/dayz-layout-preview`. The matching rule is rule 4 in `checklist-and-troubleshooting.md` (brace counts must match).

---

## 4. Image based progress bars, and tile mode for segmented bars

DayZ supports image based `ProgressBarWidget` styles, defined in `P:\gui\looknfeel\dayzwidgets.styles` (the `ProgressBarWidget` block starts at line 39). Not yet checked on `P:\`: the vanilla sprites use 0 to 255 alpha (8 bit), and a 1x1 px sprite can be scaled to any size without blur.

**Segmented bar trick.**

The vanilla imageset has an image named `ProgressMenuTileFull` (`P:\gui\imagesets\ccgui_enforce.imageset:4181-4186`, 6 by 8 px, `Flags 3`, where the untiled `ProgressMenuDefaultFullFocus` entry just above it has `Flags 0`). Not yet checked: it has transparent left and right edges and its tile flag set. When a progress bar is wider than this image the engine tiles it across the widget, and the transparent edges become gaps between the repeated colored part. That gives a segmented bar without a custom sprite.

**Use case:** custom HUD bars (health, food, hydration) with a retro tick-mark style.

Checked on `P:\`: the entry name, its size and its `Flags` value. Not checked: that `Flags 3` is the tile flag and how the tiled bar looks in game. Open the imageset in Workbench before relying on it.
