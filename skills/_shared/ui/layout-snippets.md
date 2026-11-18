# Layout snippets and checks

Copyable `.layout` blocks for the common pieces of a menu, the checks to run on a layout before delivery, and the mistakes that cost the most. Whole starting layouts are in `templates/README.md`; the attribute meanings are in `layout-attributes.md`.

## Before you deliver a layout

- Brace format, not XML, with as many `{` as `}`.
- All four unit flags on every widget, each axis chosen on purpose (mixing exact and proportional axes on one widget is normal).
- Every background is an `ImageWidgetClass`, or a `PanelWidgetClass` with a style that draws; a frame, or a panel with no style, draws nothing.
- Every background has `ignorepointer 1` and `stretch 1`; no `EditBox` or `Button` has `ignorepointer 1`.
- Widget names are unique in the whole layout. `FindAnyWidget` returns one match, so a repeated name returns the wrong widget.
- Colors are floats from 0 to 1, not 0 to 255.
- Scrolling or overflowing containers have `clipchildren 1`.
- Layout paths use forward slashes and the exact case of the files.
- No byte order mark and no trailing whitespace.
- For Dabs Framework: `scriptclass "ViewBinding"` only on bound children, never on the root (the root then gets two controllers), and a `ScriptParamsClass` with `Relay_Command` in every bound button.

## A colored background

```text
ImageWidgetClass PanelBg {
 position 0 0
 size 400 300
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 stretch 1
 ignorepointer 1
 color 0.12 0.12 0.12 0.92
}
```

The alpha here is ignored on an image with no texture (`text-sizing-and-rendering.md`); mix the wash into an opaque color if you need it, or use a `PanelWidgetClass` with `style rover_sim_colorable`.

## A button with a background, a label and a command

```text
ButtonWidgetClass BtnSave {
 position 10 10
 size 100 30
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  ImageWidgetClass BtnSaveBg {
   size 1 1
   hexactpos 0
   vexactpos 0
   hexactsize 0
   vexactsize 0
   stretch 1
   ignorepointer 1
  }
  TextWidgetClass BtnSaveText {
   size 1 1
   hexactpos 0
   vexactpos 0
   hexactsize 0
   vexactsize 0
   font "gui/fonts/Metron"
   "text halign" center
   "text valign" center
   text "#STR_MYMOD_SAVE"
   ignorepointer 1
  }
 }
 {
  ScriptParamsClass {
   Relay_Command "BtnSave"
  }
 }
}
```

Vanilla names a button's parts `X_panel` and `X_label` and `ButtonSetText`, `ButtonSetColor` and `ButtonSetTextColor` find them from the button's name (`P:\scripts\5_mission\gui\ingamemenu.c:392` to `:415`). Follow that and generic helpers work on your buttons. Dabs auto binding can miss the children of a button; find them by walking the button's children if it does.

## An edit box bound both ways (Dabs Framework)

```text
EditBoxWidgetClass EditPrefix {
 scriptclass "ViewBinding"
 Two_Way_Binding 1
 position 14 116
 size 286 28
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 font "gui/fonts/MetronBook"
}
```

## A scrolling list

```text
ScrollWidgetClass RulesScroll {
 position 0 30
 size 319 400
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 clipchildren 1
 "Scrollbar V" 1
 {
  GridSpacerWidgetClass RulesList {
   size 1 0
   hexactpos 0
   vexactpos 0
   hexactsize 0
   vexactsize 1
   Columns 1
   "Size To Content V" 1
  }
 }
}
```

A scroll widget with no spacer child does not scroll. The spacer starts at height 0 and grows at runtime; do not give it a height. Vanilla's own pair is `group_scroll` and its spacer `group_content`, with `"Size To Content V" 1` and `Columns 1` (`P:\gui\layouts\new_ui\options\keybindings_selectors\keybinding_container.layout:26` to `:53`).

## A full screen click blocker

```text
ImageWidgetClass ClickBlocker {
 size 1 1
 hexactpos 0
 vexactpos 0
 hexactsize 0
 vexactsize 0
 color 0 0 0 0.004
 stretch 1
 ignorepointer 1
}
```

Keep `ignorepointer 1`: the blocker is visual only. `ChangeGameFocus(1)` and `HumanInputController.SetDisabled(true)` stop the clicks reaching the game (`script-recipes.md`).

## Mistakes that cost the most

- A `FrameWidgetClass` never draws, and a `PanelWidgetClass` draws only through a style whose `Normal` state has a `Center` image (`styles-format.md`).
- The player's HUD brightness darkens every widget. Author honest colors, check them at a dimmed HUD, and never call `SetLV` (`theme-and-color.md`).
- An alpha of `0x12` drew nothing and `0x26` drew (measured in game). Keep anything that must be seen at `0x30` or more.
- `SetSort` replaces the order; only `SetFlags` adds and `ClearFlags` takes away (`P:\scripts\1_core\proto\enwidgets.c:128` to `:131`).
- Load JSON with `JsonFileLoader<T>.LoadFile(filename, data, errorMessage)`: it reads the whole file with `ReadFile` up to `READ_FILE_LENGTH`, 100,000,000 bytes (`P:\scripts\3_game\tools\jsonfileloader.c:3`, `:7` and `:19`). The older `JsonLoadFile` builds the text line by line with `FGets` and is marked "use JsonFileLoader::LoadFile instead" (`:104` to `:119`). A JSON file cut short at about 64 KB is reported for the older line by line route; the limit itself is not checked on `P:\`.
