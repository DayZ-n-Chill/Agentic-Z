# Reference: GUI Layout Format

Layout files define the widget tree for DayZ's GUI. They use a **custom property-file format** (not XML). Files are loaded via `GetGame().GetWorkspace().CreateWidgets(path, parentWidget)`.

---

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

Colors are `R G B A` float values, each in range 0.0 to 1.0:

```
color 1 1 1 1          // white, fully opaque
color 1 0.2 0.2 1      // red
color 0 0 0 0.5        // black, 50% transparent
color 0.0863 0.0863 0.0863 0.902   // dark panel background
```

---

## Widget Class Names

| Class | Script type | Use |
|---|---|---|
| `FrameWidgetClass` | `Widget` | Invisible container / root |
| `PanelWidgetClass` | `Widget` | Solid background panel (use `color`) |
| `WindowWidgetClass` | `Widget` | Bordered dialog window |
| `TextWidgetClass` | `TextWidget` | Static / dynamic label |
| `RichTextWidgetClass` | `RichTextWidget` | Markup-formatted text |
| `MultilineTextWidgetClass` | `Widget` | Read-only wrapping text block |
| `ImageWidgetClass` | `ImageWidget` | Image / icon (`image0 "set:X image:Y"`) |
| `ButtonWidgetClass` | `ButtonWidget` | Clickable button |
| `EditBoxWidgetClass` | `EditBoxWidget` | Single-line text input |
| `MultilineEditBoxWidgetClass` | `Widget` | Multi-line text input |
| `PasswordEditBoxWidgetClass` | `Widget` | Masked password input |
| `TextListboxWidgetClass` | `TextListboxWidget` | Scrollable list with columns |
| `CheckBoxWidgetClass` | `CheckBoxWidget` | Checkbox |
| `SliderWidgetClass` | `SliderWidget` | Horizontal slider |
| `ProgressBarWidgetClass` | `ProgressBarWidget` | Read-only progress bar |
| `ScrollWidgetClass` | `Widget` | Scroll container |
| `ItemPreviewWidgetClass` | `ItemPreviewWidget` | Live 3D item render |
| `PlayerPreviewWidgetClass` | `PlayerPreviewWidget` | Live 3D player render |
| `GridSpacerWidgetClass` | `Widget` | Grid auto-layout container |
| `WrapSpacerWidgetClass` | `Widget` | Wrapping flow-layout container |
| `MapWidgetClass` | `Widget` | In-game map surface |
| `VideoWidgetClass` | `Widget` | Video playback |
| `XComboBoxWidgetClass` | `Widget` | Drop-down combo box |

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
halign center_ref  // horizontal: left, right, center_ref, right_ref, left_ref
valign center_ref  // vertical:   top,  bottom, center_ref, bottom_ref

// Text (TextWidgetClass, ButtonWidgetClass, etc.)
text "Hello World"
font "gui/fonts/sdf_MetronBook24"
"exact text" 1         // use fixed pixel size
"exact text size" 16   // pixel font size when exact text = 1
"bold text" 1
"italic text" 1
"text halign" center   // left, center, right
"text valign" center   // top, center, bottom

// Image (ImageWidgetClass)
image0 "set:dayz_gui image:DayZLogo"
mode blend
"src alpha" 1
"clamp mode" clamp
"stretch mode" stretch_w_h

// Style (look and feel from looknfeel/ files)
style Default
style rover_sim_colorable
style Editor
style EmptyHighlight

// Layout helpers
fixaspect inside       // scale preserving aspect ratio; inside, outside, fixwidth
clipchildren 1         // clip child widgets to this widget's bounds

// Script attachment
scriptclass "MyMod_BehaviourClass"   // calls a class by name at runtime
userID 1                              // integer ID readable via widget.GetUserID()
```

---

## TextListboxWidget — Columns

Column definition uses the **`colums`** property (engine typo — one 'n'):

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
int row = list.AddItem("Apple",    null, 0);   // returns row index
list.SetItem(row, "x5",      null, 1);         // set column 1 text
list.SetItem(row, userData,  null, 0);         // userData can be null or Class
list.ClearItems();
int sel = list.GetSelectedRow();
string txt; list.GetItemText(sel, 0, txt);
list.SelectRow(0);
list.EnsureVisible(0);
```

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
preview.SetView(0);                                 // 0-N views from config
preview.SetForceFlipEnable(true);
preview.SetForceFlip(true);
```

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

---

## Loading Layout Files in Script

```c
// In UIScriptedMenu.Init():
layoutRoot = GetGame().GetWorkspace().CreateWidgets("gui/layouts/MyMod/my_menu.layout");

// Inside another widget:
Widget panel = GetGame().GetWorkspace().CreateWidgets("gui/layouts/MyMod/my_panel.layout", parentWidget);

// Get a widget after loading:
TextWidget label = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelTitle"));
```

Path is relative to the game data root (PBO packing root). Use forward slashes.

---

## Available Fonts (common choices)

```
"gui/fonts/sdf_MetronBook24"    // standard body text
"gui/fonts/sdf_MetronLight24"   // lighter weight body text
"gui/fonts/sdf_MetronBook72"    // large heading
"gui/fonts/AmorSerifPro-Bold16" // serif (used in keybindings help)
"gui/fonts/Metron"              // legacy (non-SDF, avoid for new work)
```
