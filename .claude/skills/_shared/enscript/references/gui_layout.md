# Reference: GUI Layout Format

Layout files define the widget tree for DayZ's GUI. They use a **custom property-file format** (not XML). Files are loaded via `GetGame().GetWorkspace().CreateWidgets(path, parentWidget)` (`GetWorkspace` `P:\scripts\3_game\global\game.c:85`, `CreateWidgets` `P:\scripts\1_core\proto\enwidgets.c:181`).

Every class, property and value below was checked against the vanilla layouts in `P:\gui\layouts\` and the widget classes in `P:\scripts\1_core\proto\enwidgets.c`. A citation names the first vanilla file that uses it.

---

## Contents

- [File Format](#file-format)
- [Coordinate System](#coordinate-system)
- [Colors](#colors)
- [Widget Class Names](#widget-class-names)
- [Common Properties](#common-properties)
- [TextListboxWidget — Columns](#textlistboxwidget--columns)
- [ItemPreviewWidget — 3D Item Display](#itempreviewwidget--3d-item-display)
- [PlayerPreviewWidget — 3D Player/Character Display](#playerpreviewwidget--3d-playercharacter-display)
- [Loading Layout Files in Script](#loading-layout-files-in-script)
- [Available Fonts (common choices)](#available-fonts-common-choices)

## File Format

```
WidgetClassNameClass WidgetName {
 property value
 property value
 {
  ChildWidgetClass ChildName {
   property value
  }
 }
}
```

- One `ClassName WidgetName { }` per widget
- Properties are bare key-value pairs on separate lines — no `=`, no semicolons
- Children go inside a nested `{ }` block **after** all properties of the parent
- A widget can have multiple child blocks (e.g. one for layout children, one for `ScriptParamsClass`)
- Multi-word property keys are quoted: `"exact text" 1`, `"text halign" center`

The smallest vanilla example is `P:\gui\layouts\camera_checkerboard.layout:1` to `:8`.

---

## Coordinate System

| Property | Value | Meaning |
|---|---|---|
| `hexactpos 1` | pixel | X position in pixels |
| `hexactpos 0` | relative | X position as 0..1 fraction of parent width |
| `vexactpos 1` | pixel | Y position in pixels |
| `vexactpos 0` | relative | Y position as 0..1 fraction of parent height |
| `hexactsize 1` | pixel | Width in pixels |
| `hexactsize 0` | relative | Width as 0..1 fraction of parent |
| `vexactsize 1` | pixel | Height in pixels |
| `vexactsize 0` | relative | Height as 0..1 fraction of parent |

A relative root that fills its parent is `P:\gui\layouts\camera_checkerboard.layout:2` to `:7` (`size 1 1` with all four toggles at 0).

```
// 200×48 pixels, top-left at pixel (8, 16)
position 8 16
size 200 48
hexactpos 1
vexactpos 1
hexactsize 1
vexactsize 1
```

---

## Colors

Colors are `R G B A` float values, each in range 0.0 to 1.0 (`color 1 1 1 1` at `P:\gui\layouts\day_z_assignments.layout:10`):

```
color 1 1 1 1          // white, fully opaque
color 1 0.2 0.2 1      // red
color 0 0 0 0.5        // black, 50% transparent
color 0.0863 0.0863 0.0863 0.902   // dark panel background
```

---

## Widget Class Names

| Class | Script type | Use | First vanilla use |
|---|---|---|---|
| `FrameWidgetClass` | `Widget` | Invisible container / root | `camera_checkerboard.layout:1` |
| `PanelWidgetClass` | `Widget` | Solid background panel (use `color`) | `day_z_assignments.layout:25` |
| `WindowWidgetClass` | `Widget` | Bordered dialog window | `day_z_assignments.layout:6` |
| `TextWidgetClass` | `TextWidget` (`enwidgets.c:189`) | Static / dynamic label | `day_z_assignments.layout:59` |
| `RichTextWidgetClass` | `RichTextWidget` (`:224`) | Markup-formatted text | `day_z_connection_dialogue.layout:131` |
| `MultilineTextWidgetClass` | `MultilineTextWidget` (`:219`) | Read-only wrapping text block | `day_z_connection_dialogue.layout:76` |
| `ImageWidgetClass` | `ImageWidget` (`:247`) | Image / icon (`image0 "set:X image:Y"`) | `camera_checkerboard.layout:9` |
| `ButtonWidgetClass` | `ButtonWidget` (`:381`) | Clickable button | `day_z_assignments.layout:79` |
| `EditBoxWidgetClass` | `EditBoxWidget` (`:347`) | Single-line text input | `day_z_chat_input.layout:23` |
| `MultilineEditBoxWidgetClass` | `MultilineEditBoxWidget` (`:313`) | Multi-line text input | `day_z_inventory_note.layout:51` |
| `PasswordEditBoxWidgetClass` | `PasswordEditBoxWidget` (`:353`) | Masked password input | `dialog_input_password.layout:101` |
| `TextListboxWidgetClass` | `TextListboxWidget` (`:439`) | Scrollable list with columns | `day_z_assignments.layout:35` |
| `CheckBoxWidgetClass` | `CheckBoxWidget` (`:418`) | Checkbox | `day_z_server_browser_item.layout:24` |
| `SliderWidgetClass` | `SliderWidget` (`:358`) | Horizontal slider | `day_z_server_browser_new.layout:336` |
| `ProgressBarWidgetClass` | `ProgressBarWidget` (`:377`) | Read-only progress bar | `day_z_hud.layout:2389` |
| `ScrollWidgetClass` | `ScrollWidget` (`:481`) | Scroll container | `camera_tools/camera_tools.layout:268` |
| `ItemPreviewWidgetClass` | `ItemPreviewWidget` (`P:\scripts\3_game\gameplay.c:286`) | Live 3D item render | `debug/debug_item.layout:42` |
| `PlayerPreviewWidgetClass` | `PlayerPreviewWidget` (`P:\scripts\3_game\gameplay.c:305`) | Live 3D player render | `inventory_new/medium/day_z_inventory_new.layout:204` |
| `GridSpacerWidgetClass` | `GridSpacerWidget` (`:473`) | Grid auto-layout container | `day_z_connection_dialogue.layout:14` |
| `WrapSpacerWidgetClass` | `WrapSpacerWidget` (`:477`) | Wrapping flow-layout container | `day_z_chat_item.layout:1` |
| `MapWidgetClass` | `MapWidget` (`P:\scripts\3_game\gameplay.c:322`) | In-game map surface | `day_z_map.layout:54` |
| `VideoWidgetClass` | `VideoWidget` (`:543`) | Video playback | `new_ui/video_player.layout:19` |
| `XComboBoxWidgetClass` | `XComboBoxWidget` (`:407`) | Drop-down combo box | `day_z_server_browser_new.layout:296` |
| `SpacerWidgetClass` | `SpacerWidget` (`:465`) | Auto-layout row or column container (`Padding`, `Margin`) | `new_ui/options/msstore/keybinding_menu.layout:422` |
| `CanvasWidgetClass` | `CanvasWidget` (`:341`) | Surface that script draws lines on | `day_z_map.layout:544` |
| `ThreeStateCheckboxWidgetClass` | none in `P:\scripts` | Checkbox with a third, mixed state | `day_z_server_browser_new.layout:236` |
| `EmbededWidgetClass` (vanilla spelling) | none in `P:\scripts` (`EmbededWidgetTypeID`, `:33`) | Embeds another `.layout` named by its `layout` property, with `ScriptParamsClass` values | `examples/buttontemplatetest.layout:10` |

Script type lines without a file are in `P:\scripts\1_core\proto\enwidgets.c`; layout files are under `P:\gui\layouts\`.

Four more classes appear in vanilla layouts but belong to the game's own screens, so a mod has no use for them: `HtmlWidgetClass` (`HtmlWidget`, `P:\scripts\3_game\gameplay.c:316`; the book and note pages, `day_z_book.layout:62`), `ServerBrowserWidgetClass` (`day_z_server_browser_new.layout:118`), `SmartPanelWidgetClass` (`xbox/day_z_title_screen.layout:13`) and `ContentWidgetClass` (`day_z_hud.layout:2345`).

---

## Common Properties

```
// Visibility / interaction
visible 1          // show (1) or hide (0) on load
ignorepointer 1    // passes mouse events through (for overlays)
disabled 1         // greys out and blocks input
priority 5         // z-order (higher = in front); default 0
draggable 1        // widget can be dragged

// Alignment (relative to parent bounds)
halign center_ref  // vanilla uses: left, center_ref, right_ref
valign center_ref  // vanilla uses: top, bottom, center_ref, bottom_ref

// Text (TextWidgetClass, ButtonWidgetClass, etc.)
text "Hello World"
font "gui/fonts/sdf_MetronBook24"
"exact text" 1         // use fixed pixel size
"exact text size" 16   // pixel font size when exact text = 1
"bold text" 1
"italic text" 1
"text halign" center   // vanilla uses: left, center, right
"text valign" center   // vanilla uses only center

// Image (ImageWidgetClass)
image0 "set:dayz_gui image:DayZLogo"
mode blend             // vanilla uses: blend, additive, opaque
"src alpha" 1
"clamp mode" clamp     // vanilla uses: clamp, border, wrap
"stretch mode" stretch_w_h   // vanilla uses: stretch_w_h, fit_w_center, none

// Style (look and feel from looknfeel/ files)
style Default
style rover_sim_colorable
style Editor
style EmptyHighlight

// Layout helpers
fixaspect inside       // scale preserving aspect ratio; vanilla uses: fixwidth, inside, outside, none
clipchildren 1         // clip child widgets to this widget's bounds

// Script attachment
scriptclass "MyMod_BehaviourClass"   // calls a class by name at runtime
userID 1                              // integer ID readable via widget.GetUserID()
```

Every property and value above appears in `P:\gui\layouts\`, and the value lists are every value vanilla uses there. Examples: `ignorepointer` `consolecursor.layout:2`, `draggable` `day_z_book.layout:35`, `"exact text size"` `day_z_chat_item.layout:23`, `"stretch mode"` `day_z_digital_lock.layout:51`, `scriptclass` `day_z_digital_lock.layout:28`, `userID` `day_z_assignments.layout:89`. `GetUserID()` is `P:\scripts\1_core\proto\enwidgets.c:136`.

---

## TextListboxWidget — Columns

Column definition uses the **`colums`** property, spelled without the second `n` (`colums "text;100"` at `P:\gui\layouts\day_z_mission_loader.layout:72`):

```
TextListboxWidgetClass MyList {
 position 8 8
 size 400 200
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 "title visible" 0
 colums "Name;70;Value;30"   // "ColName;widthPercent;ColName;widthPercent;..."
 font "gui/fonts/sdf_MetronLight24"
 lines 20                    // max visible rows hint
}
```

Script API:
```c
TextListboxWidget list = TextListboxWidget.Cast(root.FindAnyWidget("MyList"));
int row = list.AddItem("Apple", null, 0);   // text, userData, column; returns the row
list.SetItem(row, "x5", null, 1);           // row, text, userData (null or a Class), column
list.ClearItems();
int sel = list.GetSelectedRow();
string txt; list.GetItemText(sel, 0, txt);
list.SelectRow(0);
list.EnsureVisible(0);
```

`TextListboxWidget` is `P:\scripts\1_core\proto\enwidgets.c:439`: `AddItem(text, userData, column, row = -1)` `:442`, `SetItem` `:443`, `GetItemText(row, column, out text)` `:454`. `ClearItems` `:427`, `SelectRow` `:429`, `GetSelectedRow` `:430` and `EnsureVisible` `:432` come from `BaseListboxWidget` (`:425`).

---

## ItemPreviewWidget — 3D Item Display

```
ItemPreviewWidgetClass ItemRender {
 position 50 44
 size 280 236
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
}
```

Script API:
```c
ItemPreviewWidget preview = ItemPreviewWidget.Cast(root.FindAnyWidget("ItemRender"));
preview.SetItem(entityAI);                          // bind item; null to clear
preview.SetModelOrientation(Vector(yaw, 0, 0));     // rotate on Y axis
vector ori = preview.GetModelOrientation();
preview.SetView(0);                                 // view index
preview.SetForceFlipEnable(true);
preview.SetForceFlip(true);
```

`ItemPreviewWidget` is `P:\scripts\3_game\gameplay.c:286`: `SetItem` `:288`, `SetView` `:298`, `SetForceFlipEnable` `:300`, `SetForceFlip` `:301`; `SetModelOrientation` and `GetModelOrientation` come from `PreviewWidget` (`:280`, `:281`).

---

## PlayerPreviewWidget — 3D Player/Character Display

```
PlayerPreviewWidgetClass CharPreview {
 size 200 400
 halign center_ref
 valign center_ref
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
}
```

Script API:
```c
PlayerPreviewWidget ppw = PlayerPreviewWidget.Cast(root.FindAnyWidget("CharPreview"));
ppw.SetPlayer(DayZPlayer.Cast(player));
ppw.UpdateItemInHands(itemInHands);
ppw.SetModelOrientation(Vector(yaw, 0, 0));
ppw.Refresh();
```

`PlayerPreviewWidget` is `P:\scripts\3_game\gameplay.c:305`: `UpdateItemInHands` `:307`, `SetPlayer(DayZPlayer)` `:308`, `Refresh` `:312`.

---

## Loading Layout Files in Script

```c
// In UIScriptedMenu.Init():
layoutRoot = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/my_menu.layout");

// Inside another widget:
Widget panel = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/my_panel.layout", parentWidget);

// Get a widget after loading:
TextWidget label = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelTitle"));
```

The path starts with the mod's `$PBOPREFIX$` (the mod name for a `/dayz-new-mod` scaffold), then the folder inside the PBO; use forward slashes.

---

## Available Fonts (common choices)

```
"gui/fonts/sdf_MetronBook24"    // standard body text
"gui/fonts/sdf_MetronLight24"   // lighter weight body text
"gui/fonts/sdf_MetronBook72"    // large heading
"gui/fonts/AmorSerifPro-Bold16" // serif (used in the help screen)
"gui/fonts/Metron"              // not an SDF font
```

First uses in `P:\gui\layouts\`: `sdf_MetronBook24` `day_z_connection_dialogue.layout:12`, `sdf_MetronLight24` `day_z_chat_input.layout:35`, `sdf_MetronBook72` `day_z_connection_dialogue.layout:45`, `AmorSerifPro-Bold16` `help_screen.layout:63`, `Metron` `day_z_connection_lost.layout:21`.
