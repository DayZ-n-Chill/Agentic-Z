# From UI plan to implementation: why the build differs from the plan, and how to close the gap

Why a DayZ UI so often comes out different from what was planned, and a concrete loop that closes the gap: a widget tree spec written before the `.layout`, the Workbench Layout Editor and its two asset registrations, the offline and in game iteration loop, and a parity check at the end.

**How facts are marked here.** A `P:\` path with a line points into the vanilla data on `P:\` (read on a `P:\` holding 1.30). A line marked "not checked on `P:\`" is behaviour seen in practice that was not confirmed against the vanilla files. In game measurements say so. A line with neither is a hint.

---

## 0. The five moves that close most of the gap

1. **Pick the unit per widget, knowing what each one is** (section 1.1, section 2): exact (`1`) is 1/1080 of the screen height and keeps a widget's shape at every resolution; proportional (`0`) stretches with the parent. Never rescale exact widgets from script.
2. **If you use the Workbench Layout Editor, register your imagesets and styles twice**: in `dayz.gproj` (so the editor previews them) and in `config.cpp` `class defs` (so the game loads them). Missing either side is a direct mockup against game divergence (section 3).
3. **Keep the design mockup inside the widget model.** No gradients, rounded corners, web fonts, scanlines or other CSS only effects: none has a `.layout` equivalent, so a mockup that uses them cannot be built as drawn (section 1.6, section 5).
4. **Run the offline gate before every in game test**: script validator, name and `#STR` reconciliation, then an approximate render. It is cheap and catches the crashes and the "half my UI vanished" cases (section 4, section 6).
5. **Check what was built against the plan, not just the syntax.** Every planned widget exists with the planned name and mode, every `Binding_Name` matches a controller property, and a screenshot at the target resolution is compared with the calibrated mockup (section 6).

---

## 1. Why the built UI differs from the plan

Six independent mechanisms. Each is a real reason the in game result differs from what was drawn or specified; knowing which one bit you is half the fix.

### 1.1 Exact flags mean units of 1/1080 of the screen height

`hexactpos`, `vexactpos`, `hexactsize` or `vexactsize` set to `1` switches that axis to exact units. Measured in game, the engine draws `declared x height / 1080` pixels on both axes whatever the width (rule 3 in `checklist-and-troubleshooting.md`, which holds the measurements). The header comment says "physical resolution" (`P:\scripts\1_core\proto\enwidgets.c:68-71`); the drawn frame disagrees. A layout in exact units keeps its share of the screen height at every resolution measured; at another aspect ratio only the horizontal room changes. The divergence that does come with exact units is made by script: a script that rescales exact widgets by height/1080 scales them twice (`text-sizing-and-rendering.md`, "Text sizing laws").

### 1.2 Colors move away from what you authored

- The player's HUD brightness relights every widget (`theme-and-color.md`, "Color system"). Author honest ARGB, check it at a dimmed HUD, and do not pre-boost values.
- Most mods set final colors in script with `SetColor(ARGB(...))` after `CreateWidgets`, not in the `.layout`. A static preview of the `.layout` alone cannot know the real colors, so the plan records intended colors separately.

### 1.3 Script driven spacers overwrite authored child geometry

Any widget with a `SpacerBase` derived `scriptclass` (such as `VerticalSpacer` or `HorizontalSpacer`) forces `EXACTPOS | EXACTSIZE` onto every child at init and in `OnChildAdd`, then places the children in exact units. Proportional position and size you authored on those children is dropped in game while the editor preview still shows it. Evidence: `child.SetFlags(WidgetFlags.EXACTPOS | WidgetFlags.EXACTSIZE, false)` in `OnWidgetScriptInit` and `OnChildAdd` (`P:\scripts\3_game\gui\spacers\spacerbase.c:13-19` and `:32-37`).

### 1.4 The Workbench preview differs from the game unless assets are registered on both sides

Custom imagesets and `.styles` render in the Layout Editor only if `dayz.gproj` lists them; the game loads them only if `config.cpp` `class defs` lists them. Register one side and not the other and the mockup and the build disagree by construction (section 3).

### 1.5 The mockup uses features with no `.layout` equivalent

A freeform HTML or CSS mockup (a web font, a radial gradient, scanlines, rounded corners) maps to no widget attribute, so the build cannot match it and the gap is judged by eye between two hand made pictures. Rule: every visual element in the mockup maps to a widget class and a checked attribute, or it does not go in the plan.

### 1.6 Smaller divergence sources

- `text_proportion` (text size as a fraction of the widget height) drives most vanilla text scaling, and a mockup `font-size` in pixels does not represent it. Calibrate the mockup or label it an approximation (`text-sizing-and-rendering.md`, "Mockup fidelity").
- `UIManager.IsScaledMode()` and `SetScaledMode(bool)` are an engine level UI scale switch (`P:\scripts\3_game\tools\uimanager.c:55-56`). Check it when the same layout has a different size on one player's machine, before touching the layout.
- `EditBoxWidget` has no text alignment call (its class body is `P:\scripts\1_core\proto\enwidgets.c:347-351`). Plan single line inputs left aligned, or lay a `TextWidget` over it.

---

## 2. Authoring layouts that hold at every resolution

- **Proportional (flags 0):** position and size are fractions of the parent, so the widget scales with the parent and stretches with its aspect. Pin it to an edge or the center of the parent with `halign` and `valign` `*_ref` anchors (`valign` 4,687 times and `halign` 4,064 times across the 227 layouts under `P:\gui\layouts` on 1.30).
- **Exact (flags 1):** units of 1/1080 of the screen height, so the widget keeps its shape and scales with the screen height. It does not keep a pixel size: by that law a 1 unit border is 2/3 of a pixel at 720p (how the engine rasterizes that was not measured). Mixing exact and proportional axes on one widget is the vanilla norm (rule 3).
- **Full screen 16:9 background that holds at every resolution:**

  ```text
  ImageWidgetClass Background {
      size 0.16 0.09                 // 16% x 9% (not 1.0 1.0)
      hexactpos 0 vexactpos 0 hexactsize 0 vexactsize 0
      halign center_ref
      valign center_ref
      fixaspect outside              // vanilla values seen: fixwidth (most common), inside, outside, none
      "stretch mode" stretch_w_h
      image0 "MyMod/gui/textures/bg_co.edds"   // 16:9 source, 2048x1024 for large monitors
  }
  ```

  The vanilla widget sets the same position, size, anchor and `fixaspect` values (`P:\gui\layouts\loading.layout:36-55`).
- **Console and TV:** the `keepsafezone` attribute (246 times under `P:\gui\layouts` on 1.30) keeps TV safe margins. Gamepad and keyboard focus is the global `SetFocus(Widget)` and `GetFocus()` pair; `SetActiveWindow` has no vanilla callers, so do not design around it. The vanilla focus model is in `vanilla-menus-map.md`, section 7.

---

## 3. The Workbench Layout Editor and the two registrations

DayZ Tools Workbench has a visual Layout Editor for `.layout` files (the early Enfusion editor; Arma Reforger documents the same workflow as "Layout Creation"). It is the most direct way to make the plan and the build the same file. DayZ layouts are still often written by hand: use the editor for placing and previewing, and keep the brace format file as the source of truth. `/dayz-launch-workbench` opens Workbench on a mod's `dayz.gproj`.

The two registrations (Workbench and mod behaviour, not checked on `P:\`):

- For the **Layout Editor to preview** custom imagesets or `.styles`, list them in `dayz.gproj` (the `GameProjectClass` `imageSets{}` and `widgetStyles{}` blocks), then restart Workbench. Keep a `dayz.gproj` per mod (`/dayz-add-scaffold <ModName> --piece workbench` writes one) instead of editing the global one next to `workbenchApp.exe`.
- For the **game to load** the same assets, list them in `config.cpp`:

  ```cpp
  class CfgPatches { /* ... */ };
  class defs {
      class imageSets    { files[] = { "MyMod/gui/imagesets/my_set.imageset" }; };
      class widgetStyles { files[] = { "MyMod/gui/styles/my.styles" }; };
  };
  ```

  The full `CfgMods` form is in `skills/_shared/enscript/references/widget_api.md`, "Imagesets in layouts and script".
- Missing the `dayz.gproj` side leaves images and styles blank in the editor. Missing the `config.cpp` side leaves them blank in game.
- Editor quirk (not checked here): a `MapWidget` cannot be resized directly; change its type to another class, resize, then switch back.

---

## 4. The offline to in game iteration loop

### 4.1 How fast each change reaches the game

- A Diag client and server with `-filePatching` (and `allowFilePatching=1` in `serverDZ.cfg`) read raw `.c` files without a PBO rebuild and skip BattlEye and signing. `/dayz-launch-test` starts both.
- There is no script hot reload: a mission restart picks up `.c` changes, and `config.cpp` changes always need a PBO rebuild.
- A `.layout` under `$profile:` is read from disk again on every `CreateWidgets`, so a layout edit shows on the next menu open, in seconds and with no restart; a `.layout` under an addon prefix is served only by the PBO. Measured in game; the loop and its traps are in `hot-iteration.md`. Dabs Framework's `ScriptView.ReloadAll()` (Diag builds only) rebuilds every live view from the same paths, so it follows the same rule (`dabs-mvc-internals.md`).

### 4.2 Tools on disk

- **Script validator:** `python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>` (JSON on stdout; exit 0 pass, 1 fail, 2 warnings only). Its UI checks: an XML format layout (crashes `CreateWidgets`), a layout file referenced from `.c` but missing (a crash no null check can catch), a `$PBOPREFIX$` path mismatch, and an `OnMouseLeave` with three parameters (compiles, never fires). Make this step 1 of the delivery checklist.
- **Reconciler:** `ui_reconcile.py` (section 6.2).
- **Offline preview:** `/dayz-layout-preview <file.layout>` draws PNGs at several screen sizes and flags widgets that leave the screen or have no area. It is an approximation: fonts, styles and textures are not drawn, script side `SetColor`, `SetPos` and `SetText` are not applied, and it lays exact units out as pixels unless `scaled 1` is set, so only a 1080 high view places exact widgets the way the game does (section 1.1). Trust it for gross layout, never for pixels or colors.
- **Reading a layout's values:** `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` prints what a layout says (text, color, image, any key) and `--check` tests its structure.
- **`DbgUI`** (vanilla immediate mode debug UI) for live tuning without a rebuild: `P:\scripts\1_core\proto\dbgui.c:59-126` has `SliderFloat`, `InputFloat`, `Button`, `Combo`, `Check`, `PlotLive`, `Begin` and `End`, plus `FloatOverride`. Call it every frame from `OnUpdate`; a slider panel that drives `SetPos`, `SetColor` or `SetTextExactSize` on a live menu tunes the UI in real time, then you write the final numbers into the `.layout`.
- **A keybind toggled test menu** in a small harness mod opens the UI under test on demand; `color-test-harness.md` is a complete one for colors.
- **After the session:** search the RPT for `Cannot open layout <path>`; a clean load writes none. Put all in game checks into one session.

### 4.3 The loop

1. Write the `.layout` in brace format (the Layout Editor for placing, or by hand).
2. Run the script validator and fix every finding.
3. Run the reconciler (section 6.2).
4. Preview with `/dayz-layout-preview` and compare the 1080 high view with the design mockup for gross layout.
5. Build with `/dayz-build-pbo` and run with `/dayz-launch-test`, with a keybind toggled test menu; add a `DbgUI` slider panel for live tuning if you need one.
6. After the session: search the RPT for `Cannot open layout`, take a screenshot at the target resolution and compare it with the calibrated mockup (section 6.3).

---

## 5. The UI spec (write it before any `.layout`)

Write this small spec first; it is the forward contract for the UI (`/dayz-scope-mod` writes the mod level spec it belongs to).

**5.1 Widget tree spec table**, one row per widget the plan needs:

| Widget name | Class | Parent | Mode (prop or exact) | Pos | Size | Anchor (h and valign) | Text or #STR | Binding_Name or handler | Color source (layout or script) |
|---|---|---|---|---|---|---|---|---|---|

Rules for filling it:

- Every visual element in the mockup is a row with a real widget class. If it can only be expressed as a CSS effect, it is not in the plan (section 1.5).
- Choose the mode per widget up front (section 2).
- Name every widget you will `FindAnyWidget` or bind; the name in this table is the contract section 6 checks.
- Record where each color comes from (layout attribute or script `SetColor`), so the in game color is planned, not discovered.

**5.2 Acceptance criteria:** every row's widget exists in the built layout with the planned name and mode; every `Binding_Name` resolves to a controller property; every `#STR` key resolves in the stringtable; the in game screenshot matches the calibrated mockup at 1080p and at one other resolution.

---

## 6. The parity check (the closing check)

The delivery checklist in `checklist-and-troubleshooting.md` is mostly syntax (braces, flags, null checks). This check ties the build back to the plan.

### 6.1 Offline load check

1. Every `CreateWidgets(path)` resolves to a file that exists and is brace format, not XML. A missing file is a native crash; the `if (!root)` after `CreateWidgets` never runs. The script validator checks both.
2. Braces balance in every layout, and it holds no XML.
3. Every layout path starts with the `$PBOPREFIX$` prefix, and `gui/` with its `*.layout`, `*.imageset`, `*.fnt`, `*.styles`, `*.edds`, `*.paa` and `*.xml` files is actually packed. AddonBuilder packs only the extensions in its copy list, so a UI that works locally and is missing for others is usually a packing filter miss.

### 6.2 Name and key reconciliation

Run `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` (exit 0 clean, 1 fail with a likely typo, 2 warnings to check; `--json` for machine output). It checks the whole addon at once:

4. Every string literal `FindAnyWidget("X")` or `FindWidget("A/B/C")` in `.c` resolves to a widget in some `.layout` of the addon. The lookup is case sensitive, so a case only difference fails. A close but unequal name fails with a "did you mean" hint (a typo or rename gives a silent null, then a crash on `Cast`); a name with no match is a warning (it can be vanilla or created at runtime).
5. Every `#STR_...` key used in layouts and `.c` string literals exists in the addon's `stringtable.xml` or `stringtable.csv` (case insensitive; a typo fails with a hint, anything else is a warning). Names and keys built from variables or by concatenation cannot be resolved statically and are skipped.
6. Every `Binding_Name` and `Relay_Command` matches a controller property or method exactly. This is still manual: search both sides.

### 6.3 Built against plan

7. Every widget in the section 5 spec table exists in the built layout with the planned name, class and mode; nothing planned is missing and nothing unplanned crept in.
8. Preview the `.layout` with `/dayz-layout-preview` and compare it with the mockup for gross layout; trust only the in game screenshot for pixels, colors and fonts.
9. Take an in game screenshot at 1080p and at one other resolution (start the client with a different `-x` and `-y`; resizing the window proves nothing, `verification.md`) and compare it with the calibrated mockup. A difference at the other resolution means a script rescaling exact widgets, a bitmap face that does not shrink with its box (`text-sizing-and-rendering.md`) or a proportional width at another aspect ratio (section 1.1). Blank assets mean a missing registration (section 3). Wrong colors mean HUD brightness or a script `SetColor` (section 1.2).

---

## 7. Facts that feed the above

- **Native modal with no layout of your own:** `GetUIManager().ShowDialog(caption, text, id, DBT_YESNO, DBB_YES, DMT_QUESTION, handler)`; the result arrives in `OnModalResult(w, x, y, code, result)` with `code == id` (`P:\scripts\3_game\tools\uimanager.c:21-45`).
- **HUD overlays** extend `ScriptedWidgetEventHandler`, not `UIScriptedMenu`, and must `Unlink()` their root in `OnMissionFinish` or the widgets leak into the next session (stacked ghost HUDs after a server hop). Menu registration, the `UIScriptedMenu` contract and its input locking are in `vanilla-menus-map.md`.
- **Fonts are pre-baked bitmap atlases**, one `.fnt` and `.edds` pair per size (119 `.fnt` files under `P:\gui\fonts` on 1.30: `metron12`, `14`, `16`, `22`, `28`, `48`, `58`, `sdf_metronlight24`, `30`, `36`, `42`, `72` and more). A layout names one size file (`font "gui/fonts/sdf_MetronLight42"`); you cannot ask for an arbitrary point size at runtime, and a custom TTF must be converted in Workbench to a `.fnt` and `.edds` per size. How each face takes its size on screen was measured: `text-sizing-and-rendering.md`. Not checked on `P:\`: the conversion itself, and that Workbench cannot list a mod's own font in the Layout Editor (the workaround is to drop the `.fnt` into `P:\gui\fonts` for the preview and write the font path in the mod's `.layout` by hand).
- **Imagesets** are plain text and can be read and patched without Workbench; the format and the set name rule are in `imagesets-draw-order-progress-bars.md`, and `/dayz-build-imageset` builds one from PNG sprites.
- **`RichTextWidget` can place imageset icons inside text** with `<image set="dayz_gui" name="icon_pin"/>`, for keybind hints that mix text and icons. Not checked on `P:\`; the markup rules are in `fact-ledger.md`.
- **Reading UI material outside this repo:** layout snippets written as XML (`<?xml?>` with `<Widget>` tags) are the format that crashes `CreateWidgets`; never copy one, even from a tutorial whose script advice is sound. Web searches for "DayZ mod menu" surface cheat and malware template repositories; take signatures from `P:\scripts` instead.
