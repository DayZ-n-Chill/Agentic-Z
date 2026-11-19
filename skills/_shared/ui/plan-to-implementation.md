# From UI plan to built UI

Why a DayZ UI so often comes out different from its plan, and the loop that closes the gap: a widget spec written before the `.layout`, the Workbench Layout Editor and its two registrations, the offline and in game iteration loop, and a parity check at the end.

## The five habits that close most of the gap

1. Choose the unit of each widget knowing what it is: exact (`1`) is 1/1080 of the screen height and keeps the widget's shape at every resolution; proportional (`0`) stretches with the parent. Never rescale exact widgets from script.
2. If you use the Layout Editor, register imagesets and styles twice: in `dayz.gproj` so the editor shows them and in `config.cpp` so the game loads them.
3. Keep the mockup inside what widgets can do. Gradients, rounded corners, web fonts and scanlines have no `.layout` equivalent, so a mockup that uses them cannot be built as drawn.
4. Run the offline checks before every in game test: script validator, name and key reconciler, then a rough render. They catch the crashes and the "half my UI vanished" cases cheaply.
5. Check the build against the plan, not only the syntax: every planned widget exists with the planned name and unit, every `Binding_Name` matches a controller property, and a screenshot at the target resolution matches the calibrated mockup.

## Why the built UI differs from the plan

- Exact units are 1/1080 of the screen height on both axes, measured in game (`checklist-and-troubleshooting.md`, "Declare all four unit flags"). The engine comment says "Uses physical resolution" (`P:\scripts\1_core\proto\enwidgets.c:68`); the drawn frame disagrees. An exact layout keeps its share of the screen height at every resolution, and at another aspect ratio only the horizontal room changes. What does break is a script that rescales exact widgets by height/1080 again, which scales them twice (`text-sizing-and-rendering.md`).
- Colors move. The player's HUD brightness relights every widget (`theme-and-color.md`), and most mods set their final colors in script with `SetColor` after `CreateWidgets`, so a preview of the `.layout` alone cannot know them. Record the intended colors in the spec.
- Script spacers overwrite the children's geometry. A widget whose `scriptclass` derives from `SpacerBase` (`VerticalSpacer`, `HorizontalSpacer`) sets `EXACTPOS` and `EXACTSIZE` on every child in `OnWidgetScriptInit` and `OnChildAdd` (`P:\scripts\3_game\gui\spacers\spacerbase.c:8` to `:17` and `:32` to `:35`), so a proportional size you wrote is dropped in game while the editor still shows it.
- The editor and the game read different registrations (below). Register one side only and they disagree by construction.
- A mockup font size in pixels does not represent `text_proportion` or how each face takes its size (`text-sizing-and-rendering.md`). Calibrate it or label it an approximation.
- `UIManager.IsScaledMode()` and `SetScaledMode(bool)` are an engine wide UI scale switch (`P:\scripts\3_game\tools\uimanager.c:55` and `:56`). When the same layout has another size on one player's machine, check it before touching the layout.
- `EditBoxWidget` has no text alignment call (its class body is `P:\scripts\1_core\proto\enwidgets.c:347` to `:351`). Plan single line inputs left aligned, or lay a `TextWidget` over the box.

## Layouts that hold at every resolution

- Proportional widgets scale with the parent and stretch with its aspect; pin them to an edge or the centre with `halign` and `valign` `*_ref` anchors (`valign` 4,687 times and `halign` 4,064 times in the 227 layouts under `P:\gui\layouts`).
- Exact widgets keep their shape and scale with the screen height, not a pixel size: a 1 unit border is 2/3 of a pixel at 720p (how the engine rasterises that is not measured). Mixing exact and proportional axes on one widget is normal.
- A full screen 16:9 background, with the same position, size, anchors and `fixaspect` as vanilla's (`P:\gui\layouts\loading.layout:36` to `:55`):

  ```text
  ImageWidgetClass Background {
   size 0.16 0.09
   hexactpos 0
   vexactpos 0
   hexactsize 0
   vexactsize 0
   halign center_ref
   valign center_ref
   fixaspect outside
   "stretch mode" stretch_w_h
   image0 "MyMod/gui/textures/bg_co.edds"
  }
  ```

- On console and TV, `keepsafezone` (246 uses under `P:\gui\layouts`) keeps safe margins. Focus is the global `SetFocus` and `GetFocus` pair (`vanilla-menus-map.md`, "Focus and gamepad").

## The Layout Editor and its two registrations

DayZ Tools Workbench has a visual Layout Editor, the early Enfusion one; Arma Reforger documents the same workflow as "Layout Creation". `/dayz-launch-workbench` opens Workbench on a mod's `dayz.gproj`. Use the editor to place and preview, and keep the brace format file as the source of truth. The registrations below are Workbench and mod behaviour, not checked on `P:\`.

- For the editor to show custom imagesets or styles, list them in the `imageSets{}` and `widgetStyles{}` blocks of `GameProjectClass` in `dayz.gproj`, then restart Workbench. Keep a `dayz.gproj` per mod (`/dayz-add-scaffold <ModName> --piece workbench` writes one) instead of editing the global one next to `workbenchApp.exe`.
- For the game to load them, list them in `config.cpp` (`script-recipes.md`, "Styles, imagesets and defines in config.cpp").
- Missing `dayz.gproj` leaves them blank in the editor; missing `config.cpp` leaves them blank in game.
- Unverified (not checked here): a `MapWidget` cannot be resized in the editor directly; change its type, resize, then change it back.

## The iteration loop

How fast each change reaches the game:

- A diag client and server with `-filePatching` (and `allowFilePatching=1` in `serverDZ.cfg`) read loose `.c` files with no PBO rebuild and skip BattlEye and signing; `/dayz-launch-test` starts both. There is no script hot reload: a mission restart picks up `.c` changes, and `config.cpp` changes always need a rebuild.
- A `.layout` under `$profile:` is read again on every `CreateWidgets`, so an edit shows on the next open with no restart; a `.layout` under an addon prefix comes only from the PBO (`hot-iteration.md`). Dabs `ScriptView.ReloadAll()`, diag builds only, follows the same rule (`dabs-mvc-internals.md`).

The tools:

- Script validator: `python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>` (JSON out; exit 0 pass, 1 fail, 2 warnings only). For UI it finds an XML layout, a layout referenced from `.c` but missing (a crash no null check can catch), a `$PBOPREFIX$` path mismatch, and an `OnMouseLeave` with three parameters, which compiles and never fires.
- Reconciler: `ui_reconcile.py`, below.
- Offline preview: `/dayz-layout-preview <file.layout>` draws PNGs at several screen sizes and flags widgets that leave the screen or have no area. It draws no fonts, styles or textures, applies no script calls, and places exact units as pixels unless `scaled 1` is set, so only the 1080 high view places exact widgets like the game. Trust it for gross layout only.
- `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` prints what a layout says; `--check` tests its structure.
- `DbgUI`, vanilla's immediate mode debug panel (`P:\scripts\1_core\proto\dbgui.c:59` to `:126`): `SliderFloat`, `InputFloat`, `Button`, `Combo`, `Check`, `PlotLive`, `Begin`, `End` and `FloatOverride`. Called every frame from `OnUpdate`, a slider panel driving `SetPos`, `SetColor` or `SetTextExactSize` on a live menu tunes it in real time; then write the numbers into the `.layout`.
- A key toggled test menu in a small test mod opens the UI on demand; `color-test-harness.md` is a full one for colors.

The loop:

1. Write the `.layout` in brace format, in the editor or by hand.
2. Run the script validator and fix every finding.
3. Run the reconciler.
4. Preview with `/dayz-layout-preview` and compare the 1080 high view with the mockup for gross layout.
5. Build with `/dayz-build-pbo` and run with `/dayz-launch-test`, with the test menu and a `DbgUI` panel if you need one.
6. After the session, search the RPT for `Cannot open layout`; a clean load writes none. Take a screenshot at the target resolution and compare it with the calibrated mockup. Put all pending UI checks into one session.

## The UI spec

Write this before any `.layout`; it is the contract the parity check tests. `/dayz-scope-mod` writes the mod level spec it belongs to.

| Widget name | Class | Parent | Unit (prop or exact) | Pos | Size | Anchors | Text or `#STR_` key | `Binding_Name` or handler | Color source (layout or script) |
|---|---|---|---|---|---|---|---|---|---|

- Every visual element of the mockup is a row with a real widget class. What only CSS can express is not in the plan.
- Choose the unit of each widget up front.
- Name every widget you will `FindAnyWidget` or bind; that name is the contract.
- Record where each color comes from, so the in game color is planned, not discovered.

Accepted when every row exists in the built layout with its planned name and unit, every `Binding_Name` resolves to a controller property, every `#STR_` key resolves in the stringtable, and the in game screenshot matches the calibrated mockup at 1080p and at one other resolution.

## The parity check

The delivery checklist in `checklist-and-troubleshooting.md` is mostly syntax. This ties the build back to the plan.

Loading:

1. Every `CreateWidgets(path)` names a file that exists and is brace format. A missing file is a native crash, and the `if (!root)` after it never runs. The script validator checks both.
2. Braces balance in every layout, and none is XML.
3. Every layout path starts with the `$PBOPREFIX$` prefix, and `gui/` with its `.layout`, `.imageset`, `.fnt`, `.styles`, `.edds`, `.paa` and `.xml` files is packed. AddonBuilder packs only the extensions on its copy list, so a UI that works locally and is missing for everyone else is usually a packing filter miss.

Names and keys, with `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` (exit 0 clean, 1 a likely typo, 2 warnings; `--json` for machine output):

4. Every literal `FindAnyWidget("X")` or `FindWidget("A/B/C")` in `.c` matches a widget in some layout of the addon, case sensitive. A close miss fails with a "did you mean" hint; no match at all is a warning, since the name can be vanilla or made at runtime.
5. Every `#STR_` key in layouts and `.c` literals exists in `stringtable.xml` or `stringtable.csv`, case blind. Names and keys built at runtime are skipped.
6. Every `Binding_Name` and `Relay_Command` matches a controller property or method exactly. This one is still manual: search both sides.

Built against plan:

7. Every widget in the spec exists with its planned name, class and unit; nothing planned is missing and nothing unplanned crept in.
8. Preview with `/dayz-layout-preview` for gross layout; trust only the in game screenshot for pixels, colors and fonts.
9. Screenshot at 1080p and at one other resolution, by starting the client with other `-x` and `-y` values (`verification.md`). A difference at the other resolution means a script rescaling exact widgets, a bitmap face that does not shrink with its box, or a proportional width at another aspect. Blank assets mean a missing registration. Wrong colors mean HUD brightness or a script `SetColor`.

## Facts the loop leans on

- A native dialog with no layout of your own: `GetUIManager().ShowDialog(caption, text, id, DBT_YESNO, DBB_YES, DMT_QUESTION, handler)`; the answer arrives in `OnModalResult(w, x, y, code, result)` with `code == id` (`P:\scripts\3_game\tools\uimanager.c:21` to `:45`).
- A HUD overlay extends `ScriptedWidgetEventHandler`, not `UIScriptedMenu`, and must `Unlink()` its root in `OnMissionFinish`, or its widgets carry into the next session and stack after a server hop.
- Fonts are baked bitmap atlases, one `.fnt` and `.edds` pair per size (119 `.fnt` files under `P:\gui\fonts`: `metron12` to `metron58`, `sdf_metronlight24` to `sdf_metronlight72` and more). A layout names one size file (`font "gui/fonts/sdf_MetronLight42"`); there is no arbitrary point size at runtime, and a custom TTF is converted in Workbench to a `.fnt` and `.edds` per size. Not checked on `P:\`: the conversion, and that the Layout Editor cannot list a mod's own font (put the `.fnt` in `P:\gui\fonts` for the preview and write the path in the mod's layout by hand).
- Imagesets are plain text and can be patched without Workbench (`imagesets-draw-order-progress-bars.md`); `/dayz-build-imageset` builds one from PNG sprites.
- Rich text can put imageset icons inside text, `<image set="dayz_gui" name="icon_pin"/>`, for key hints. Vanilla does it for controller prompts: `<image set="xbox_buttons" name="A" />` passed to `SetText` (`P:\scripts\3_game\dayzgame.c:2209`). The rest of the markup is in `engine-widget-facts.md`.
- A layout snippet written as XML (`<?xml?>` with `<Widget>` tags) is the format that crashes `CreateWidgets`; never copy one, even from a tutorial whose script advice is sound. Web searches for "DayZ mod menu" turn up cheat and malware templates; take signatures from `P:\scripts`.
