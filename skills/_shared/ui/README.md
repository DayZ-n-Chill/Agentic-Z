# UI pack

Reference for building DayZ menus and HUDs: the `.layout` format, the widget calls, styles, the vanilla menus and HUD, Dabs Framework and DayZ Expansion views, map, chat and admin tool patterns, and what a running client showed when measured. Written for `dayz-ui-specialist`; any DayZ worker may load one file of it when a task needs it.

Follow `skills/_shared/dayz-conventions.md` and the UI rules in `skills/_shared/conventions/ui.md`; where this pack and those rules differ, the rules win. Read the short, checked files first (`skills/_shared/enscript/references/gui_layout.md`, `skills/_shared/enscript/references/widget_api.md` and `skills/_shared/figma-to-dayz-rules.md`) and come here for depth. A design from Figma goes through the Figma pipeline (`figma-node-normalizer`, `figma-to-dayz-layout`, `dayz-layout-validator`); this pack covers the scripts and polish after it.

Every vanilla fact cites the file on `P:\` it came from, checked on DayZ 1.30; when a line has moved, Grep the class or key name in the same file. "Measured in game" means a running client showed it (DayZ 1.29 unless the line says otherwise) and `P:\` can't confirm it. Facts about Dabs Framework, DayZ Expansion, other mods or the DayZ MCP bridge come from those products' own scripts, not vanilla, and each file says which.

The tools live elsewhere: `/dayz-layout-preview` draws a layout at several screen sizes, `/dayz-build-imageset` packs sprites, `/dayz-lint` checks the mod setup, and `scripts/tools/` holds the script validator, the UI reconciler, the layout parser and the HTML viewer.

## Which file to open

| Question | File |
|---|---|
| How do I plan a new menu, HUD or panel, and why does the built UI drift from the plan | `plan-to-implementation.md` |
| Which rules does every layout and UI script follow, and what do I check before calling it done | `checklist-and-troubleshooting.md` |
| How is a `.layout` written, and which widget classes exist and draw | `layout-format.md` |
| What does each layout attribute do: unit flags, anchors, color, text | `layout-attributes.md` |
| Where will a widget land on screen, and why do children of a spacer ignore their size | `layout-geometry.md` |
| Which layout blocks can I copy, and what do I check before delivering a layout | `layout-snippets.md` |
| How does a `scriptclass` handler get its `ScriptParamsClass` values, and how does a layout name a style | `layout-scriptclass.md` |
| Which widgets and attributes do shipped layouts use, and which layout checks are worth writing | `layout-corpus-counts.md` |
| What can an HTML preview of a layout show | `layout-html-preview.md` |
| How do I change a vanilla layout in place on 1.30 without replacing it | `layout-variants.md` |
| What changed in the vanilla UI in 1.30 and how do I port a mod | `ui-changes-1-30.md` |
| How do the 1.30 cursor's tool and material panels work, and how do I add one | `hud-action-info-panels.md` |
| Which vanilla menu is which file, how do I register a menu ID, how does the HUD chain work | `vanilla-menus-map.md` |
| What can every widget do from script: the base class, flags, globals and what rotation really draws | `widget-prototypes.md` |
| What are the methods of each widget class, and which widgets can give their text back | `widget-classes.md` |
| How do I show a 3D item or player in the UI | `preview-widgets.md` |
| Which less obvious widget calls exist, what does the HUD brightness do, how does rich text markup behave | `engine-widget-facts.md` |
| How do `.styles` files, 9-slice borders and press feedback work | `styles-format.md` |
| How do I bind widgets, lock input, show the cursor, blur the background, register styles and imagesets | `script-recipes.md` |
| How do mod menus build tabs, row lists, search, press twice to confirm, server set colors and click sounds | `menu-script-patterns.md` |
| Why do widgets overlap when some hide, and why won't one take clicks | `stacking-and-clickability.md` |
| How do I build a toggle or number fields that convert as the player types | `form-controls.md` |
| How do I build an info card or a set of tabs | `cards-and-tabs.md` |
| How do I drag a window by its header, add hover feedback, or fade a status message | `dragging-hover-and-status.md` |
| Where do UI colors come from, and how do I scope a recolor | `theme-and-color.md` |
| How do I measure drawn colors against their hex values in game | `color-test-harness.md` |
| How do I keep sliders and edit boxes in step, or reuse a mod's color picker | `color-picker.md` |
| How do stringtable keys, the CSV header and generated preview panels work | `localization.md` |
| Why is text clipped, unwrapped or a different size at another resolution | `text-sizing-and-rendering.md` |
| Which name does script use for an imageset, why does the background go first, how do I make a segmented bar | `imagesets-draw-order-progress-bars.md` |
| How do I iterate a layout on the running client without repacking | `hot-iteration.md` |
| Why does a `#STR_` key print raw, and how does `text_proportion` behave | `preview-text-and-stringtables.md` |
| What can an automated check prove about a UI, and how do I test another resolution | `verification.md` |
| Why can't a widget be reached by name when a test copy of its layout is loaded | `widget-name-collisions.md` |
| What do the MCP bridge's UI calls return, and where do they stop working | `ui-test-bridge.md` |
| How do I leave a scripted camera, open a UI from a vehicle seat, or hook the loading screen | `cameras-seats-loading-screens.md` |
| How do I keep script pixel sizes right at every resolution | `screen-scaling.md` |
| How do admin tools build floating windows, labels over objects and a free look menu | `admin-ui-patterns.md` |
| How do I drive a map widget, draw on it, drag markers and refresh only on change | `map-and-markers.md` |
| How do I pin a widget to a world point, build a compass strip or drop a ping | `world-markers-and-compass.md` |
| How do I replace the chat, wrap its text and reuse its lines | `chat-ui.md` |
| When does a mod's HUD element show, and how are its position and colors saved | `hud-overlays.md` |
| How do I structure a large UI: layouts by name, pages, an event bus, an RPC dispatcher | `ui-architecture.md` |
| How do Dabs views, bindings and commands behave | `dabs-mvc-internals.md`, after `skills/_shared/enscript/integrations/dabs_framework.md` |
| How do Dabs collections, two way binding, `WidgetAnimator` and `LinearColor` work | `dabs-observables-and-animation.md` |
| What does a Dabs `ScriptViewMenu` do for me, and which prefab layouts ship with Dabs | `dabs-menus-and-prefabs.md` |
| How does DayZ Expansion build its views and menus | `expansion-mvc-patterns.md` |
| How does the Expansion Market menu talk to the server | `expansion-market-menu.md` |
| Where does Expansion keep its settings and saved files, and how do I detect it | `expansion-settings-and-persistence.md` |
| Which starting layout fits (modal, HUD overlay, form row, scroll list) | `templates/README.md` |
| Which widget names do the generated preview panels use | `templates/panel-contract.md` |
| How do I bind a key to open the UI | `skills/_shared/enscript/integrations/input_bindings.md` |

The files on admin tools, map, chat, HUD overlays and UI structure describe a production mod's patterns, not vanilla: adapt the code and check each call against `P:\scripts\1_core\proto\enwidgets.c`.

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| The game crashes loading a layout | XML format, unbalanced braces or a missing file | `checklist-and-troubleshooting.md` |
| Half the UI is missing | The parser stopped at a syntax error | `imagesets-draw-order-progress-bars.md` |
| Right at 1080p, wrong elsewhere | Script scaling exact widgets again | `screen-scaling.md` |
| An image is a flat white box | The texture path does not resolve | `hot-iteration.md` |
| Colors darker than their hex values | The player's HUD brightness | `engine-widget-facts.md` |
| A widget won't take clicks | `ignorepointer`, a sibling on top, or no handler | `stacking-and-clickability.md` |
| A Dabs command runs twice | The handler returned false or is `void` | `dabs-mvc-internals.md` |
| A `#STR_` key prints raw | The key is not defined, or its addon's stringtable is not read | `preview-text-and-stringtables.md` |
| Anything else | | The table in `checklist-and-troubleshooting.md` |

## The standard workflow

1. Spec before layout. Fill the widget tree spec table (`plan-to-implementation.md`): every visual element gets a widget class, a name (the contract for `FindAnyWidget` and bindings), a unit mode and a color source (layout attribute or script `SetColor`). Keep the mockup inside what widgets can do; a `.layout` has no gradients, web fonts or rounded corners.
2. Write the `.layout` in brace format, never XML, with anchors and `position 0 0`, all four unit flags declared, and `#STR_` keys for all text.
3. Check the mod setup with `/dayz-lint <ModName>`.
4. Check the UI contract from the repo root:

   ```cmd
   python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
   python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
   ```

   The validator checks braces, XML format, that each layout file exists, the `$PBOPREFIX$` path and the `OnMouseLeave` parameter count. The reconciler matches every `FindAnyWidget` name against the layouts and every `#STR` key against `stringtable.xml` or `stringtable.csv`, with "did you mean" hints; `--strict` turns its warnings into a failure. The validator exits 0 for pass, 1 for fail and 2 for warnings only, so gate on the `errors` list in its JSON output or treat 2 as a pass.
5. Preview offline. `/dayz-layout-preview <file.layout>` draws PNGs at several screen sizes, and `python scripts/tools/dayz-layout-viewer/build_viewer.py <layout>` writes an HTML preview (`layout-html-preview.md`). Both are approximations: trust them for where a box is, never for whether your string fits, and read `verification.md` before you trust any view but 1080p. To read what a layout says, use `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>`.
6. Build, deploy and look at it in game with `/dayz-build-pbo`, `/dayz-launch-test` and the test loop in `skills/dayz-launch-test/references/`. Search the RPT for `Cannot open layout`, take a screenshot at 1080p and at one other resolution (start the client with a different `-x` and `-y`; resizing the window proves nothing), and compare with the mockup. Put all pending UI checks into one session.
7. Before you call it done, compare the spec table with the built layout, the bindings and the screenshot (`plan-to-implementation.md`), then run the delivery checklist in `checklist-and-troubleshooting.md`.

When something is wrong in game, `MissionBase.DumpCurrentUILayout()` (`P:\scripts\5_mission\mission\missionbase.c:378`) prints the current menu's whole widget tree with visibility, the DbgUI panel (`P:\scripts\1_core\proto\dbgui.c`) tunes values live, and in diag builds Dabs `ScriptView.ReloadAll()` reloads every Dabs layout (`dabs-mvc-internals.md`).

## Rules that cost the most when missed

The full list is in `checklist-and-troubleshooting.md`.

- Write layouts in brace format with balanced braces. An XML layout or a missing layout file crashes inside the native `CreateWidgets`, where no null check helps, and the parser drops every widget after the first syntax error.
- A `FrameWidgetClass` never draws, and a `PanelWidgetClass` draws only with a style. On 1.30 the vanilla action prompt rows are panels (`PanelWidgetClass item`, `P:\gui\layouts\day_z_hud.layout:2424`), so an `ImageWidget.Cast` of them is null.
- Declare all four unit flags. `0` is a fraction of the parent; `1` is exact units of 1/1080 of the screen height on both axes (measured in game). Don't rescale exact widgets from script.
- Null check `GetGame()` in destructors, `GetWorkspace()` before `CreateWidgets`, and every `FindAnyWidget` and `Cast` result.
- A plain handler needs `SetHandler(this)` (`P:\scripts\1_core\proto\enwidgets.c:172`). `OnMouseLeave` takes four parameters and `OnMouseEnter` three (`enwidgets.c:665` and `:666`).
- Never call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod; they are global and overwrite the player's HUD brightness (`engine-widget-facts.md`).
- Dabs command handlers return true, a Dabs menu doesn't close on Esc by itself, and constructing a `ScriptView` calls `CreateWidgets`, so never construct one from an RPC handler.
- Widget names are a contract. A test copy of a layout that keeps the original names can't be addressed (`widget-name-collisions.md`).
- A passing automated check proves the contract, not the picture. A screenshot a person has looked at is required.

## On Linux

The Proton setup, the tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`. For UI work only this changes:

- The UI lab under `scripts/tools/dayz-ui-lab/` (parsing, checking and offline rendering of `.layout` files) is Python and runs natively.
- Workbench starts under Proton (`dayz-proton.sh gui Workbench`), but its layout and imageset editors are not checked there.
- Packing uses dayzmake 1.0.0 or later in place of AddonBuilder; the helper scripts are in `scripts/tools/dayz-linux/`. An HTML preview is not an in game sign off; keep the widget, binding and runtime checks above.

When the UI has to end in a mod that builds, loads and ships, follow the loop in `skills/dayz-launch-test/references/mod-loop.md` with `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`.
