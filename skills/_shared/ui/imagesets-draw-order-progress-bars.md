# Imagesets, draw order and progress bars

Which name a script uses for an imageset, what an `.imageset` file looks like, why the background widget goes first, what a typo does to the rest of a layout, and how to make an image or segmented progress bar.

## The set name, not the file name

An `.imageset` under `P:\gui\imagesets\` has two names: its file name on disk, such as `dayz_gui.imageset`, and the set name on its `Name` line (`Name "dayz_gui"`, `P:\gui\imagesets\dayz_gui.imageset:2`), which Workbench also shows in the `ImageSet` tab of its right panel. Scripts use the set name: `LoadImageFile(0, "set:NAME image:IMG")`. The two can differ, and a script that passes the file name gets no image and no log line.

After you create an imageset in Workbench, read the set name from the `ImageSet` tab and use that in script. `/dayz-build-imageset` writes the set name for you.

An `.imageset` is plain text, so you can read and patch it without Workbench. The header of `P:\gui\imagesets\ccgui_enforce.imageset:1` to `:10`, then one entry:

```cpp
ImageSetClass {
 Name "ccgui_enforce"
 RefSize 1024 1024
 Textures {
  ImageSetTextureClass {
   mpix 3
   path "{52DDD34979EE096E}Gui/imagesets/ccgui_enforce.edds"
  }
 }
 Images {
  ImageSetDefClass ProgressMenuTileFull {
   Name "ProgressMenuTileFull"
   Pos 635 619
   Size 6 8
   Flags 3
  }
```

## The background goes first

Widgets draw in the order they appear in the `.layout`, top to bottom, so a background placed below its siblings draws over them. Make the background the first child of its parent. When Workbench reorders widgets while you edit, move the background back to the top in a text editor before you save. No vanilla script shows this order, so it is not checked on `P:\`; from script, `Widget.SetSort` (`P:\scripts\1_core\proto\enwidgets.c:130`) changes it.

## A typo hides everything after it

The parser loads widgets until the first syntax error and stops. Widgets after the broken line never appear and nothing says why. When everything after a new widget has vanished, look for a typo or a missing brace at that point. Besides Workbench, the script validator under `scripts/tools/dayz-script-validator/` checks brace balance, XML format and missing layout files, and `/dayz-layout-preview` shows what parsed. See `checklist-and-troubleshooting.md`, "Balance the braces".

## Image and segmented progress bars

`ProgressBarWidget` takes image based styles, defined in `P:\gui\looknfeel\dayzwidgets.styles` (its block starts at `:39`). Not checked on `P:\`: the vanilla sprites use 8 bit alpha, and a 1x1 sprite scales to any size without blur.

For a segmented bar without a custom sprite, use the vanilla image `ProgressMenuTileFull` (`ccgui_enforce.imageset:4181` to `:4186`): 6 by 8 px with `Flags 3`, where the untiled `ProgressMenuDefaultFullFocus` just above it has `Flags 0`. On a bar wider than the image the engine repeats it, and its transparent left and right edges become gaps between the colored parts, giving a tick mark style for health, food or water bars. The name, size and `Flags` value are checked on `P:\`; that `Flags 3` means tiling, that the edges are transparent, and how the bar looks in game are not. Open the imageset in Workbench before you rely on it.
