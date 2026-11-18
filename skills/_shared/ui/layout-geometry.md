# Layout geometry

How to work out each widget's screen rectangle from the `.layout` alone, how anchors move a widget, and why the children of a spacer ignore their own position and size. A tool that predicts rects, such as `/dayz-layout-preview`, rests on these rules.

## The arithmetic

Walk the tree depth first, carrying the parent's absolute box `(px, py, pw, ph)`; the root's parent is the screen. For each widget:

```text
s = screen_height / 1080                    # one exact unit
w = size_x * s          if hexactsize == 1  else size_x * pw
h = size_y * s          if vexactsize == 1  else size_y * ph
x = px + position_x * s if hexactpos  == 1  else px + position_x * pw
y = py + position_y * s if vexactpos  == 1  else py + position_y * ph
```

A missing `position` is `0 0`. Exact units are 1/1080 of the screen height (`checklist-and-troubleshooting.md`, "Declare all four unit flags"), so a predictor that treats them as pixels is right only at 1080 pixels high. `resolve_geometry` in `scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py` still uses the pixel form, and so do the HTML viewer and `/dayz-layout-preview` unless `scaled 1` is set.

Measured in game at 1920x1080, the formula matched the engine to within 0.00003 of a pixel on six widgets at three depths of nesting, and again on five buttons.

## Anchors

- `halign center_ref` centres the widget in its parent and then adds the position: `x = px + (pw - w) / 2 + position_term`, where `position_term` is the exact or fraction term above. `valign center_ref` does the same vertically. On the live HUD, `Zeroing` declares `center_ref`, `hexactpos 0` and position `0.06`, and its centre is drawn 103.7 px right of its parent's centre, exactly 0.06 times the parent's 1728 px width; its mirror `WeaponMode` at `-0.06` lands 103.7 px left. With `position 0 0`, the usual case in vanilla, adding and ignoring the position give the same answer.
- `halign right_ref` and `valign bottom_ref` subtract the offset: it is a distance inward from that edge, `x = px + pw - w - position_term`. Adding it is wrong.

Measured on `HudFrameWidget` at 1920x1080, exact position rows only, so the numbers are pixels:

| Widget | Anchor | Declared offset | Drawn edge minus parent edge |
|---|---|---|---|
| `BadgesPanel` | `right_ref` | 252 | -252 |
| `Blood` | `right_ref` | 43 | -43 |
| `Hungry` | `right_ref` | 139 | -139 |
| `Thirsty` | `right_ref` | 182 | -182 |
| `BloodType` | `right_ref` | -4 | +4 |
| `BadgesSpacer` | `bottom_ref` | 23.5 | -23.5 |
| `VoiceLevelsPanel` | `bottom_ref` | 80 | -80 |
| `TemperatureValueBottom` | `bottom_ref` | -12 | +12 |

The two negative offsets settle it: a widget declared at `-4` is drawn 4 px outside its parent's right edge, which only the subtracting rule predicts. `BadgesPanel` is declared at `P:\gui\layouts\day_z_hud.layout:552`.

## Children of a spacer

A child of a spacer (`SpacerBaseWidget`, `SpacerWidget`, `GridSpacerWidget`, `WrapSpacerWidget` or `ScrollWidget`, `P:\scripts\1_core\proto\enwidgets.c:460` to `:481`) declares a box the parent then recomputes, so its `position` and `size` in the file say nothing about where it is drawn. A geometry check that skips this rule produces confident nonsense: a "clickable widget with a zero box" rule fired 15 times on shipped Expansion layouts, and every hit was a button with `size 0.0 1.0` under a `GridSpacerWidget`, an ordinary idiom.

Script spacers do the same from script: any widget whose `scriptclass` derives from `SpacerBase` sets `EXACTPOS` and `EXACTSIZE` on every child in `OnWidgetScriptInit` and `OnChildAdd` and then places them (`P:\scripts\3_game\gui\spacers\spacerbase.c:13` to `:19` and `:32` to `:37`). A proportional size you wrote on those children is dropped in game while the Workbench preview still shows it.

Measured in game:

- A `WrapSpacerWidgetClass` with `"Size To Content V" 1` stacks children of mixed heights and grows with them. A window holding frames, a thin panel, text and a nested `GridSpacerWidgetClass` list ended right after its last child with 4, 6 and 20 rows. Vanilla stacks its pause menu buttons the same way (`P:\gui\layouts\day_z_ingamemenu.layout:99`, the `bottom` spacer).
- `"size to text v" 1` grows a text widget at runtime, and the grown text paints over the next sibling. Give such widgets a clipping container or room below.

## Positions a script reads

- `GetPos` returns the position relative to the parent; `GetScreenPos` returns the absolute screen position. Drag code needs the second.
- A child at `position 110 110` inside a parent at `100 100` reports a screen position of 210, 210.
- Resizing the game window scales the finished picture and does not lay the UI out again; test another resolution by starting the client with other `-x` and `-y` values (`verification.md`).
