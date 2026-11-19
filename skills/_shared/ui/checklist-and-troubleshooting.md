# UI build rules and troubleshooting

The rules every `.layout` file and UI script follows, the checklist to run before a UI is called done, and a table from symptom to fix. The Tier 2 UI rules in `skills/_shared/conventions/ui.md` win where the two differ; this file links to them instead of repeating them.

## Layout rules

### A leaf widget needs no child block

An empty `{ }` child block on a leaf widget is a harmless habit, not a requirement. Vanilla leaves it out: `TextWidgetClass ActionListItem0` closes straight after its properties in the shipped HUD (`P:\gui\layouts\day_z_hud.layout:48` to `:60`). Vanilla leaves the block out on 5,315 of 5,337 leaves and never writes an empty one; mods write it on about a fifth of their leaves. Both forms load, and a scan of 376 layouts from five production mods parsed every one without it. The UI lab keeps a fixture for this, a `ButtonWidgetClass` leaf with only properties (`scripts/tools/dayz-ui-lab/probe/AZ_UIProbe/gui/layouts/leaf-without-child-block.layout`). Don't write a check that demands the block.

What does break loading:

- Unbalanced braces. The parser loads widgets from the top until the first syntax error and then stops, so everything after it never appears. When half the UI is missing, check brace balance and the file format first.
- A layout written as XML (`<?xml?>` or `<GUI><class type=...>`, which some design kit tools emit). It crashes inside the native `CreateWidgets` even when every widget name and `#STR` key matches.

The one real use of an anonymous block on a leaf is to hold `ScriptParamsClass`, in a block of its own (157 of 157 cases; see `layout-scriptclass.md`). To see what loaded, `MissionBase.DumpCurrentUILayout()` prints every widget of the current menu with visible and hidden totals (`P:\scripts\5_mission\mission\missionbase.c:378` to `:398`).

### Frames and panels draw nothing alone

A `FrameWidgetClass` is never visible. A `PanelWidgetClass` is visible only when its `style` gives it a 9-slice (`styles-format.md`).

- For a plain background, use an `ImageWidgetClass` with `ignorepointer 1` and `stretch 1`.
- Since DayZ 1.30 vanilla also uses styled containers: `style ActionWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3700`) is set on `GridSpacerWidgetClass ActionTargetsCursorWidget` (`P:\gui\layouts\day_z_hud.layout:2400`), and the prompt rows inside it are plain `PanelWidgetClass` widgets (`PanelWidgetClass item`, `day_z_hud.layout:2424`). Before 1.30 those rows were image widgets with `linear_gradient.edds` or `card_drop.edds`.
- Because those rows are panels, an `ImageWidget.Cast` of them is null on 1.30. The rule and its lines are in `conventions/ui.md`, "Layout and widget rules"; migration is in `ui-changes-1-30.md`.
- A procedural texture from script, `LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")` then `SetColor(...)`, fails with "Bad texture name" and "LoadImageFile can't load" and leaves the widget without a texture (measured in game on 1.29). Ship a 1x1 white `.edds`, or use a `Colorable` style with a `WhitePixel` center (`styles-format.md`). The same string as `image0` in a layout logs no error, but whether it draws is not confirmed (`verification.md`).

### Declare all four unit flags

`hexactpos`, `vexactpos`, `hexactsize` and `vexactsize` choose the unit of each value.

- `0` is a fraction of the parent, 0.0 to 1.0. Vanilla mostly uses it: across the 227 layouts under `P:\gui\layouts`, `hexactsize 0` appears 6,167 times and `hexactsize 1` 3,265 times. `ImageWidgetClass ImageBackground` sets all four to 0 (`P:\gui\layouts\loading.layout:36` to `:55`).
- `1` is exact units, and one exact unit is 1/1080 of the screen height on both axes (measured in game on 1.29, not checked on 1.30). The screen is always 1080 units tall and `1080 x width / height` units wide: 1920 at 16:9, 2560 at 2560x1080. A 400 unit panel 16 units from the right edge drew 400 px wide and 16 px from the edge at 1920x1080 and at 2560x1080, and 267 px wide and 11 px from the edge at 1280x720. Heights from 461 to 1108 were measured; 1440 was not.
- The engine header says otherwise: the comment on `EXACTPOS` reads "Uses physical resolution (g_iWidth, h_iHeight)" (`P:\scripts\1_core\proto\enwidgets.c:68`). The measurement says that comment does not describe what is drawn. `enscript/references/gui_layout.md`, `figma-to-dayz-rules.md` and the `/dayz-layout-preview` renderer describe exact values as pixels; when the difference matters, check the layout at 720p in game.
- A layout that fits in 1080 units of height fits vertically everywhere; only the horizontal room changes with the aspect ratio. Don't reason in physical pixels, and don't rescale exact widgets from script by `height / 1080`: the engine already did, and the script doubles it (`text-sizing-and-rendering.md`).
- Exact keeps a widget's shape and scales it with the screen height. Proportional stretches it with the parent. At 16:9 the two agree at every measured resolution; at another aspect ratio a proportional width follows the screen width and an exact width does not.
- For a full screen background, copy vanilla: `size 0.16 0.09` with `halign center_ref`, `valign center_ref` and `fixaspect outside` (`loading.layout:36` to `:55`).
- Mixing exact and proportional axes on one widget is normal: 50.8 percent of 8,671 vanilla widgets do it. The top profiles are exact position with proportional size (1,892 widgets) and exact position with proportional width and exact height (1,182).
- The usual vanilla idiom is an anchor plus zero offset: `halign` or `valign` with a `*_ref` value and `position 0 0` (70 percent of exact position widgets), where the unit makes no difference.
- `MultilineTextWidgetClass` is all proportional in 93 percent of cases; text, frame and panel widgets favour an exact position anchor with a proportional size.
- Leaving all four out gives proportional in practice; 42 vanilla widgets do, `FrameWidgetClass FrameWidget` among them (`P:\gui\layouts\day_z_ingamemenu.layout:1`, `size 1 1`, no flags). Declare them anyway, for the reader.

### Balance the braces

Count opening and closing braces before every in game test.

## Script rules

- Null check `GetGame()` in every destructor; it returns null during shutdown.
- Null check `GetWorkspace()` before `CreateWidgets()`; it is null during early init.
- Null check every `FindAnyWidget()` and `Cast()` result. A missing layout file is a different failure: it crashes inside the native `CreateWidgets` before any null check runs, which is why the validator in the checklist below exists.
- A vanilla `ScriptedWidgetEventHandler` gets no events until you call `SetHandler(this)` (`P:\scripts\1_core\proto\enwidgets.c:172`). A Dabs `ViewController` installs its own handler on the layout root, so a Dabs view doesn't call it (`dabs-mvc-internals.md`).
- `FindAnyWidget()` has been seen returning the wrong widget for children inside a `ButtonWidget` in a production mod; not checked on vanilla widgets. Walk the button's children yourself. Dabs `LoadWidgetsAsVariables` is one `FindAnyWidget` per field, so it has the same problem: keep a button's children in arrays, not named fields.
- In Dabs Framework, `new ScriptView()` calls `CreateWidgets()` itself. Never construct a view from an RPC handler or early init, where the workspace can be null. Create it once at mission init and show or hide it later. A view created once and hidden keeps its widget tree, and its widget names, for the whole session (measured in game; `widget-name-collisions.md`, "Widget names are a contract").

## Enforce Script limits

- No ternary operator; it does not compile.
- `++`, `--`, `foreach`, `+=`, `-=`, string literals as arguments and statements over several lines all work.
- Declare a variable before the conditional when several branches use it.
- Give every variable an explicit type and every member field the `m_` prefix.

The language rules with their vanilla citations are in `skills/_shared/enscript/patterns/language_workarounds.md` and `skills/_shared/enscript-style.md`.

## Dabs MVC rules

Checked against the Workshop copy of Dabs Framework, not vanilla; file lines are in `dabs-mvc-internals.md`.

- `NotifyPropertyChanged("X")` updates only the bindings whose `Binding_Name` is `"X"`. An empty string updates every binding, which is expensive.
- A command handler returns true when it handled the click. `ViewController.OnClick` returns true as soon as `InvokeCommand` reports handled. A handler that returns false or is `void` makes `ViewBinding.InvokeCommand` walk up the parent chain and call the same function name on each ancestor.
- A `Relay_Command` fires only from a `ButtonWidget` (in `OnClick`) and a `CheckBoxWidget` (in `OnChange`).
- An item in an `ObservableCollection` that holds a reference back to its controller leaks: the collection stores `ref array<ref T>` and nothing breaks the cycle. Null the back reference in the item's destructor.
- `map<Widget, T>` works; Dabs's own `ViewBindingHashMap` is `typedef map<Widget, ViewBinding>`.

## Delivery checklist

Run both tools from the repo root and fix every finding:

```cmd
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

The validator exits 0 for pass, 1 for fail and 2 for warnings only, so a check that treats any non zero exit as failure rejects a clean tree. Gate on the `errors` list in its JSON output, or treat 2 as a pass. The reconciler fails on a widget name or `#STR` key that matches nothing. `/dayz-lint` covers the mod setup; these two cover the UI contract.

Layout:

- [ ] Brace format, not XML; braces balanced.
- [ ] All four unit flags on every widget.
- [ ] Anchors (`halign` and `valign` with `*_ref`, `position 0 0`) for anything that must hold at other resolutions.
- [ ] Backgrounds are an `ImageWidgetClass` with `ignorepointer 1` and `stretch 1`, or a 9-slice style.
- [ ] Widget names unique and matching the spec table; they are the contract for `FindAnyWidget` and bindings.
- [ ] All player text comes from `#STR_` keys (`localization.md`).
- [ ] `ScriptParamsClass` sits in a block of its own.
- [ ] Every `ImageWidgetClass` that shows transparency has `mode blend` and `"src alpha" 1` (`text-sizing-and-rendering.md`).

Script:

- [ ] `GetGame()` checked in destructors, `GetWorkspace()` before `CreateWidgets`, every `FindAnyWidget` and `Cast` result checked.
- [ ] Input locked on open and unlocked on close and in the destructor, so the focus counts per device balance.
- [ ] A HUD overlay's root is `Unlink()`ed in `OnMissionFinish` (`P:\scripts\5_mission\mission\missiongameplay.c:266`), or ghost widgets stack up across sessions.
- [ ] Dabs: command handlers return true, no `OnShow` or `OnHide` override on a `ScriptView`, Esc wired by hand.

Fidelity:

- [ ] The offline preview (`/dayz-layout-preview`) compared with the mockup by eye and labelled as an approximation.
- [ ] An in game screenshot at 1080p and at one other resolution, compared with the calibrated mockup.
- [ ] Every row of the spec table exists in the built layout with its planned name, class and unit mode (the parity check in `plan-to-implementation.md`).

## Symptom to fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Widget not clickable | `ignorepointer 1` on it or an ancestor | Keep `ignorepointer` on decoration only. |
| Text overlaps the widget below | Fixed positions with visibility that changes | Recalculate positions after each change, or use a spacer (`stacking-and-clickability.md`). |
| Button click does nothing | No `SetHandler(this)` in a vanilla handler | Call it when the layout is created. |
| `OnMouseLeave` never fires | Three parameters instead of four | `OnMouseLeave(Widget w, Widget enterW, int x, int y)` (`P:\scripts\1_core\proto\enwidgets.c:666`). |
| Colors darker than their hex values | The player's HUD brightness, applied globally | Design against it; never call `Widget.SetLV()` (`theme-and-color.md`). |
| A very faint color is invisible | The engine drops low alpha | 0x12 is invisible and 0x26 visible (measured in game); keep alpha at 0x30 or more. |
| A `Relay_Command` runs more than once | The handler returned false or is `void` | Return true when handled. |
| EditBox text does not update | The binding was not notified | `NotifyPropertyChanged("FieldName")` after the change. |
| The game crashes loading a layout | XML format, unbalanced braces or a missing layout file | Brace format only; run the validator. A missing leaf `{ }` is never the cause. |
| Right at 1080p, wrong elsewhere | Script scaling exact widgets again, bitmap glyphs that don't shrink, or a proportional width at another aspect ratio | Drop the script scaling, size bitmap text for the smallest height, check in game at 720p and your widest aspect. `/dayz-layout-preview` places exact units as pixels unless `scaled 1` is set (`verification.md`). |
| Half the UI is missing | The parser stopped at the first syntax error | Check braces at or before the first missing widget; `DumpCurrentUILayout()` shows what loaded. |
| An imageset or style works in Workbench but not in game, or the reverse | Registered in only one place | Register in `dayz.gproj` and in `config.cpp` `class defs` (`plan-to-implementation.md`). |
| Scroll content does not scroll | No spacer child | Give the `ScrollWidget` a `WrapSpacerWidget` or `GridSpacerWidget` as its direct child. |
| An image is a flat white box | The texture path does not resolve | Check the path first; a missing UI texture draws white and logs nothing (measured in game). |
| A runtime reload draws two copies, or clicks hit nothing | `CreateWidgets` adds a second tree | `Unlink()` the old root before every load (`hot-iteration.md`). |
| An `ImageWidget` made from script is invisible | No image loaded | Load a 1x1 white `.edds` or use a `Colorable` style. |
| The `interact` or `item` cast is null on 1.30 | They are `PanelWidgetClass` | Hold them as `Widget`; vanilla declares no `PanelWidget` class. |
| A `ViewBinding` does not update | `Binding_Name` does not match | Make it equal the controller property name exactly. |
| `CreateWidgets` crashes | Called from an RPC or early init | Create views at mission init. |
| Draw order wrong | Siblings overlap in the wrong order | `SetSort(int)` (`enwidgets.c:130`): higher draws later, on top. `SetSort(1000 - priority)` orders by priority. |
| Map markers lag or cost too much | Full refresh every frame | Refresh only when a count or hash changes (`map-and-markers.md`). |
| A 3D marker shows behind the camera | Depth from `GetScreenPos` not checked | Hide it when index 2 is 0 or less. |
| EditBox `OnChange` never fires | No handler set | `editBox.SetHandler(handler)`; not needed with Dabs. |
| Chat text overflows | A `TextWidget` does not wrap | Measure with a hidden `TextWidget` first, or use a `MultilineTextWidget` with `wrap 1`. |
| A widget never goes away | `Show(false)` only hides | `Unlink()` destroys it and its children (`enwidgets.c:173`). |
| ComboBox selection resets | Items cleared and refilled | Save `GetCurrentItem()` before `ClearAll()` and restore it after. |
| Slider and EditBox disagree | The binding goes one way | Update each from the other's `OnChange`. |
