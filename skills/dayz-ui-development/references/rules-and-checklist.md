# UI rules, delivery checklist and troubleshooting table

The 18 numbered rules for `.layout` files and UI script (each one traced to a real crash or a real visual failure), the checklist to run before a UI is called done, and a symptom to fix table. Other files in this folder refer to these rules by number.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). "Measured in game" means the source author measured it on a running client (DayZ 1.29 unless a line says otherwise); those results are not yet checked on `P:\` or in game here. Facts about Dabs Framework, LBmaster mods or LFPowerGrid name the mod they come from. A line that starts "Corrected" keeps an older wrong claim visible on purpose, so nobody brings it back.

---

## Contents

- [Layout rules (1 to 4)](#layout-rules-every-layout-file)
- [Script rules (5 to 10)](#script-rules-every-c-file)
- [Enforce Script restrictions (11 to 14)](#enforce-script-restrictions-all-code)
- [Dabs MVC rules (15 to 18)](#dabs-mvc-rules)
- [Delivery checklist](#delivery-checklist)
- [Troubleshooting](#troubleshooting-common-ui-failures-and-quick-fixes)

## Layout rules (every .layout file)

### 1. A leaf widget does not need an empty child block

An empty `{ }` child block on a leaf widget is a harmless habit, not a requirement.

- Vanilla layouts leave it out all the time. `TextWidgetClass ActionListItem0` at `P:\gui\layouts\day_z_hud.layout:45` closes straight after its properties and ships in the production HUD.
- Counted by the source author on 2026-07-04: vanilla leaves the block out on 99.6% of leaves (5,315 of 5,337) and writes an empty `{ }` zero times. Mods write it on 22.6% of leaves. Either form loads.
- What does break loading: **unbalanced braces**, and **layouts written as XML** (`<?xml?>` or `<GUI><class type=...>`, which some design kit tools emit). An XML layout crashes inside the native `CreateWidgets` even when every widget name and `#STR` key reconciles (seen in the LFGungame mod: four layouts, fixed by converting them to brace format).
- The parser loads widgets from the top until the first syntax error and then stops. Widgets after the error never appear, which is the classic "half my UI is missing" symptom. When a widget is missing, check brace balance and file format first, not leaf blocks.
- The one real use of an anonymous block on a leaf is to hold `ScriptParamsClass`, in a block of its own (157 of 157 cases in the source author's corpus; see `layout-format.md`).
- Vanilla has a tree dumper for exactly this: `MissionBase.DumpCurrentUILayout()` (`P:\scripts\5_mission\mission\missionbase.c:378-398`) prints every widget of the current menu with visible and invisible totals.

Corrected on 2026-07-03 and again on 2026-07-24. The older rule, "every widget, leaf widgets included, needs an explicit child block or the parser crashes or hangs", is refuted; do not bring it back. Evidence the source author gives: a first party fixture, `leaf-without-child-block.layout` under `scripts/tools/dayz-ui-lab/probe/LF_UIProbe/gui/layouts/`, is a `ButtonWidgetClass` leaf with only properties, and a corpus check parsed 376 of 376 layouts from VPP, DayZ Expansion, TraderPlus, TraderX and LFPowerGrid without the rule. The wrong claim is kept visible because it had already been built on: a linter detector named `LAYOUT-LEAF-MISSING-BRACES` was written from it, its 83 tests passed while certifying a false rule, and all 28 of its "true positives" were false. That detector is quarantined.

### 2. FrameWidgetClass and PanelWidgetClass draw nothing by themselves

A `FrameWidgetClass` is never visible. A `PanelWidgetClass` is visible only when a `style` gives it a 9-slice (see `styles-format.md`).

- Up to DayZ 1.29 (reported by the source; 1.29 is not on `P:\`): use an `ImageWidgetClass` with `ignorepointer 1` and `stretch 1` for a visible background.
- DayZ 1.30: vanilla uses styled containers. `style ActionWidget` is defined at `P:\gui\looknfeel\dayzwidgets.styles:3700` and set on `GridSpacerWidgetClass ActionTargetsCursorWidget` at `P:\gui\layouts\day_z_hud.layout:2287`; the prompt rows inside it are plain `PanelWidgetClass` widgets (`PanelWidgetClass item` at `P:\gui\layouts\day_z_hud.layout:2294`). The source reports these rows were `ImageWidgetClass` with `linear_gradient.edds` or `card_drop.edds` before 1.30.
- **1.30 breaking change:** `ImageWidget.Cast(m_Root.FindAnyWidget("interact"))` (and the same for `"item"`) returns null in 1.30, and the next `LoadImageFile` or `SetColor` call is a null pointer error. Keep the result as a plain `Widget`: vanilla scripts declare no `PanelWidget` class to cast to (Tier 2, `skills/_shared/conventions/ui.md`, "Layout and widget rules"). Details: `dayz-130-ui-changes.md`.
- Procedural texture from script: `LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")` followed by `SetColor(ARGB(...))`. Measured in game on DayZ 1.29 (LFPowerGrid, confirmed again on 2026-09-04): this fails with "Bad texture name" and "LoadImageFile can't load", and the widget is left without a texture. Fallbacks: ship a 1x1 white `.edds` and load that, or use a `Colorable` style with a `WhitePixel` center (`styles-format.md`). The same string written as `image0` in a layout logs no error, but whether it draws was not confirmed (`verification-and-automation.md`).

### 3. Declare all four position and size mode flags (0 or 1)

The four flags `hexactpos`, `vexactpos`, `hexactsize` and `vexactsize` choose the **unit** of the value. They do not decide whether the value "counts".

- **`0` = a fraction of the parent (0.0 to 1.0).** This is what vanilla mostly uses: across the 227 layouts under `P:\gui\layouts`, `hexactsize 0` appears 6,164 times and `hexactsize 1` 3,263 times (counted on `P:\`; the source author counted 5,851 against 2,727 on an earlier dump). `ImageWidgetClass ImageBackground` in `P:\gui\layouts\loading.layout:36-55` sets all four to 0.
- **`1` = exact units. Measured in game: one exact unit is 1/1080 of the screen height, on both axes.** The engine draws `declared x height / 1080` pixels whatever the width, so the screen is always 1080 units tall and `1080 x width / height` units wide (1920 at 16:9, 2560 at 2560x1080). Measured at heights 461, 720, 900, 1080 and 1108 (widget rects read back from the running client, 2026-08-28 and 2026-08-29) and on a shipped panel (SimpleGroup, 2026-09-28): a 400 unit panel 16 units from the right edge drew 400 px wide and 16 px from the edge at 1920x1080 and at 2560x1080, and 267 px wide and 11 px from the edge at 1280x720. A height of 1440 was not measured.
- A layout that fits in 1080 units of height fits vertically at every resolution; only the horizontal room changes with the aspect ratio.
- Do not reason in physical pixels (a reviewer who did flagged an overflow that did not exist). Do not rescale exact widgets from script by `height / 1080`: the engine already did, and the script doubles it (`text-sizing-and-rendering.md`).
- The engine header disagrees with the measurement. The comment on `EXACTPOS` in `WidgetFlags` reads "Uses physical resolution (g_iWidth, h_iHeight)" (`P:\scripts\1_core\proto\enwidgets.c:68-71`). The source author's measurements say that comment does not describe what is drawn. This repo's other UI packs (`skills/_shared/enscript/references/gui_layout.md`, `skills/_shared/figma-to-dayz-rules.md`) still describe exact values as pixels; until someone repeats the measurement here, treat "1/1080 of the height" as the measured claim and "pixels" as the documented one, and check a layout at 720p in game when the difference matters.
- Choosing: exact (1) keeps a widget's shape and scales it with the screen height. Proportional (0) stretches it with its parent. At 16:9 the two agree at every resolution measured; at another aspect ratio a proportional width follows the screen width and an exact width does not.
- For a full screen background that works at every resolution, copy the vanilla pattern: `size 0.16 0.09` with `halign center_ref`, `valign center_ref` and `fixaspect outside` (`P:\gui\layouts\loading.layout:36-55`).
- Mixing exact and proportional axes on one widget is the vanilla norm (50.8% of 8,671 vanilla widgets in the source author's count of 2026-07-04; the top profiles are exact position with proportional size, 1,892 widgets, and exact position with proportional width and exact height, 1,182). An older warning that mixing is fragile is refuted.
- The dominant vanilla idiom is **anchor plus zero offset**: `halign` or `valign` with a `*_ref` value, `position 0 0` (70% of exact position widgets have `position 0 0`, where the unit makes no difference), and a proportional or exact height size.
- Defaults by class, for a spec table: `MultilineTextWidgetClass` is all proportional in 93% of cases; text, frame and panel widgets favor an exact position anchor with a proportional size.
- Leaving all four flags out gives proportional in practice. 42 vanilla widgets do, production menu roots among them: `FrameWidgetClass FrameWidget` at `P:\gui\layouts\day_z_ingamemenu.layout:1` has `size 1 1` and no flags. Still declare them, for the reader.

Corrected on 2026-10-03. This rule's heading used to add "do NOT default them to 1", after a 2026-07-03 note that called the old "always set all four to 1" advice a top cause of layouts that look different at other resolutions. That note said `1` means physical screen pixels, that an all exact layout authored at 1080p takes a different share of the screen at 1440p, ultrawide or console, and that the rule was to default to proportional and keep exact for elements that must be pixel true. Measured in game, exact units keep their share of the screen height at every height above, and at another aspect ratio they keep their size in height units.

### 4. Brace counts must match

Count the opening and closing braces before every in game test.

## Script rules (every .c file)

### 5. Null check GetGame() in every destructor

It returns null during shutdown.

### 6. Null check GetWorkspace() before CreateWidgets()

The workspace is null during early init.

### 7. Null check every FindAnyWidget() and Cast() result

A missing layout file is a different failure: it crashes inside the native `CreateWidgets` before any null check runs. The linter catches that one (see the checklist below).

### 8. FindAnyWidget() returned wrong references for widgets inside a ButtonWidget

Reported from LFPowerGrid production, not reproduced here. Walk the button's children yourself, or use helper functions. Dabs `LoadWidgetsAsVariables` is one `FindAnyWidget` per field and nothing more (`dabs-framework.md`), so it inherits the problem: store the children of a button in arrays, not in named fields.

### 9. new ScriptView() calls CreateWidgets() itself

Dabs Framework fact. Never construct a view from an RPC handler or early init, where the workspace can be null. Create the view once at mission init and show or hide it later.

A consequence measured on 2026-09-04: a view created once and hidden keeps its whole widget tree alive for the session, so its widget names stay taken (`verification-and-automation.md`, "Two layouts with the same names").

### 10. SetHandler(this) is required for a vanilla ScriptedWidgetEventHandler

`SetHandler(ScriptedWidgetEventHandler eventHandler)` is declared at `P:\scripts\1_core\proto\enwidgets.c:172`. Without it no event reaches your handler. Dabs `ViewController` installs its own handler on the layout root (`dabs-framework.md`, "Event flow"), so a Dabs view does not call it.

## Enforce Script restrictions (all code)

11. No ternary operator. It does not compile.
12. `++` and `--`, `foreach`, `+=` and `-=`, string literals as parameters, and statements spread over several lines all work (seen in LBmaster production code).
13. Declare a variable before the conditional when several branches use it.
14. Give every variable an explicit type, and every member field the `m_` prefix.

The language rules themselves, with their vanilla citations, are in `skills/_shared/enscript/patterns/language_workarounds.md` and the style guide `skills/_shared/enscript-style.md`.

## Dabs MVC rules

Framework facts, checked against the Workshop copy of Dabs Framework; details and file lines are in `dabs-framework.md`.

15. **`NotifyPropertyChanged("X")` is safe.** It updates only the bindings whose `Binding_Name` is `"X"`. It does not scan or overwrite other controller fields. Calling it with an empty string updates every binding, which is expensive; avoid it.
16. **Command handlers must return true when they handled the click.** `ViewController.OnClick` returns true as soon as `InvokeCommand` reports handled, and `super.OnClick` is not called then, so the old wording "Relay_Command plus a manual OnClick fires twice" was imprecise. The real risk is a handler that returns false or is declared `void`: `ViewBinding.InvokeCommand` then walks up the parent chain and calls the same function name on each ancestor. Also, a `Relay_Command` fires only from a `ButtonWidget` (in `OnClick`) and a `CheckBoxWidget` (in `OnChange`); no other widget type dispatches commands. Corrected on 2026-07-05.
17. **An item in an `ObservableCollection` that holds a reference back to its controller is a circular reference leak.** The collection stores `ref array<ref T>`, and nothing breaks the cycle. Null the back reference in the item's destructor.
18. **`map<Widget, T>` works.** Dabs's `ViewBindingHashMap` is `typedef map<Widget, ViewBinding>` and is used throughout `ViewController.c`. An earlier claim that it crashes was probably caused by something else.

---

## Delivery checklist

Updated 2026-07-05 to match the corrected rules and the tools.

### Automated first (run both, fix every finding)

- [ ] `python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>` reports no errors
- [ ] `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` exits 0 (a failure is a typo in a widget name or a `#STR` key)

Both paths are relative to the Agentic-Z repo root; run them from there or give the full path. The validator's exit codes are 0 for pass, 1 for fail and **2 for warnings only**, so a clean tree with warnings exits 2 and a check written as "exit code not 0 means failure" rejects it. Gate on the length of the `errors` list in its JSON output, or treat 2 as a pass. `/dayz-lint` covers the mod setup (config.cpp, prefix, script modules); these two cover the UI contract.

### Layout (.layout)

- [ ] Brace format, not XML (`<?xml` or `<GUI>` crashes the client); braces balanced
- [ ] All four unit flags declared on every widget (0 = fraction of the parent, 1 = exact units; rule 3)
- [ ] Anchors (`halign` and `valign` with `*_ref`, plus `position 0 0`) for placement that must survive other resolutions
- [ ] Backgrounds: an `ImageWidgetClass` with `ignorepointer 1` and `stretch 1`, or a 9-slice style (`styles-format.md`)
- [ ] Widget names unique and matching the spec table (they are the contract for `FindAnyWidget` and for bindings)
- [ ] All text the player sees comes from `#STR_` keys in the stringtable (`localization.md`)
- [ ] `ScriptParamsClass` in a block of its own, never mixed with child widgets
- [ ] Every `ImageWidgetClass` that must show transparency has `mode blend` and `"src alpha" 1` (`text-sizing-and-rendering.md`)

### Script (.c)

- [ ] `GetGame()` null checked in destructors; `GetWorkspace()` null checked before `CreateWidgets`
- [ ] Every `FindAnyWidget` and `Cast` result null checked (a missing layout file still crashes inside `CreateWidgets`; the null check cannot save you, which is what the validator is for)
- [ ] Input locked on open, unlocked on close and in the destructor (the focus counts for each device must balance)
- [ ] HUD overlays: the root is `Unlink()`ed in `OnMissionFinish` (`P:\scripts\5_mission\mission\missiongameplay.c:266`), or ghost widgets stack up across sessions
- [ ] Dabs: command handlers return true; no `OnShow` or `OnHide` overrides on a `ScriptView`; ESC wired by hand
- [ ] No ternary operators; `m_` prefix on members; variables declared before the branches that share them

### Fidelity (the check that was always missing)

- [ ] Offline preview compared with the mockup by eye (`/dayz-layout-preview`, or the HTML viewer `python scripts/tools/dayz-layout-viewer/build_viewer.py <layout>`), and labelled as an approximation
- [ ] In game screenshot at 1080p and at one other resolution, compared with the calibrated mockup
- [ ] Every row of the spec table exists in the built layout with the planned name, class and unit mode (the parity check in `plan-to-implementation.md`)

---

## Troubleshooting: common UI failures and quick fixes

| Symptom | Root cause | Fix |
|---|---|---|
| Widget not clickable | `ignorepointer 1` on the widget or an ancestor | Remove it from interactive widgets; keep it only on decoration |
| Text overlaps the widget below | Absolute positioning plus visibility that changes | Recalculate positions after every change (`advanced-patterns.md`, section 1), or use a spacer |
| Button click does not fire | No `SetHandler(this)` in a vanilla handler | Call `SetHandler` when the layout is created; not needed with a Dabs `ViewController` |
| `OnMouseLeave` never fires | Three parameters instead of four | The signature is `OnMouseLeave(Widget w, Widget enterW, int x, int y)` (`P:\scripts\1_core\proto\enwidgets.c:666`) |
| Colors look darker than their hex values | The player's HUD brightness setting, applied globally by vanilla | Design against it. Do not call `Widget.SetLV(0)`: it is `proto static` and overwrites the player's setting (`theme-and-color.md`) |
| Alpha below about 48 is invisible | The engine clamps low alpha | Keep alpha at 0x30 (48) or more. Measured bracket: 0x12 invisible, 0x26 visible |
| A `Relay_Command` runs more than once | The handler returned false or is `void`, so it was called again up the parent chain | Command handlers return true when handled (rule 16) |
| EditBox text does not update | The binding was not notified | Call `NotifyPropertyChanged("FieldName")` after changing the value |
| Layout crashes the game on load | An XML format layout, unbalanced braces, or a missing layout file (the crash is inside native `CreateWidgets`; no null check runs) | Brace format only; run the validator (its XML format and missing layout file checks). Not caused by a missing leaf `{ }` (rule 1) |
| UI right at 1080p, wrong at other resolutions | Not the exact flags: they scale with the screen height (rule 3). Look for a script that also scales exact widgets by height/1080 (double scaling), bitmap glyphs that do not shrink with their boxes, or a proportional width at another aspect ratio | Drop the script side scaling; size bitmap text for the smallest height you support; check in game at 720p and at your widest aspect. The HTML viewer lays exact units out as pixels at every viewport, so its views other than 1080p misplace exact widgets (`verification-and-automation.md`) |
| Half the UI is missing (widgets after some point never appear) | The parser stops at the first syntax error and loads what came before | Check brace balance at or before the first missing widget; `MissionBase.DumpCurrentUILayout()` shows what loaded |
| An imageset or style shows in Workbench but not in game (or the reverse) | It was registered in only one of the two places | Register it in both `dayz.gproj` (editor) and `config.cpp` `class defs` (game); see `plan-to-implementation.md` |
| Scroll content does not scroll | No spacer child in the `ScrollWidget` | Add a `WrapSpacerWidget` or `GridSpacerWidget` as its direct child |
| A UI image comes out as a flat white box | The texture path does not resolve | Check the path first, not the color or the style: a missing UI texture fills the slot with white (255,255,255) and writes nothing to the RPT (measured 2026-08-19) |
| Reloading a layout at runtime draws two copies, or clicks land on nothing | A manual `CreateWidgets` adds a second tree; it does not replace the first | `Unlink()` the previous root before every load (`hot-iteration.md`) |
| `ImageWidget` invisible when created from script | No image loaded | Load an image first. The procedural texture string fails on DayZ 1.29 (rule 2); ship a 1x1 white `.edds` or use a `Colorable` style |
| `FindAnyWidget` cast is null for `interact` or `item` in the HUD (1.30) | Those widgets are `PanelWidgetClass` in the 1.30 `day_z_hud.layout` | Hold it as a plain `Widget`, not `ImageWidget`: `Widget w = m_Root.FindAnyWidget("interact");`. Vanilla scripts declare no `PanelWidget` class to cast to |
| A `ViewBinding` does not update the UI | `Binding_Name` does not match | The `Binding_Name` in `ScriptParamsClass` must equal the controller property name exactly |
| `CreateWidgets` crashes | Called from an RPC or early init | Create views at mission init, when `GetWorkspace()` is valid (rule 9) |
| Widget draw order wrong | Children overlap in the wrong order | `Widget.SetSort(int)` (`P:\scripts\1_core\proto\enwidgets.c:130`): a higher value draws later, on top. `SetSort(1000 - priority)` orders by priority |
| Map markers do not update | A full refresh every frame is too expensive | Dirty check: compare counts or hashes and refresh only on change (`lbgroups-patterns.md`) |
| A 3D marker shows when it is behind the camera | The z depth from `GetScreenPos` was not checked | `GetGame().GetScreenPos(pos)` returns depth in index 2; when it is 0 or less the point is behind the camera, so hide the marker |
| EditBox `OnChange` does not fire | No handler set | Create a `ScriptedWidgetEventHandler` and call `editBox.SetHandler(handler)`; needed in vanilla, not with Dabs |
| Chat text overflows | A `TextWidget` does not wrap | Measure with a hidden `TextWidget` (`SetText`, `Update`, `GetScreenSize`) before placing the text, or use a `MultilineTextWidget` with `wrap 1` |
| Widget not destroyed | `Show(false)` used where the widget should go | `widget.Unlink()` destroys the widget and all its children (`P:\scripts\1_core\proto\enwidgets.c:173`); `Show(false)` only hides |
| ComboBox selection resets | Items cleared and added again without keeping the selection | Save `GetCurrentItem()` before `ClearAll()` and restore it with `SetCurrentItem()` afterwards |
| Slider value and EditBox out of step | The binding goes one way only | Do both directions: slider `OnChange` updates the edit box text, edit box `OnChange` updates the slider |
