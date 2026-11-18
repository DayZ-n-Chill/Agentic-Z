# UI pack

Reference for `dayz-ui-specialist`: the `.layout` format, the widget API, styles, the vanilla menus and HUD, Dabs Framework MVC, DayZ Expansion patterns, group, map and admin tool patterns, and results measured on a running client. Open only the file the task needs.

Follow `skills/_shared/dayz-conventions.md` and the UI rules in `skills/_shared/conventions/ui.md`; where this pack and those rules differ, the rules win. The short, checked UI files are `skills/_shared/enscript/references/gui_layout.md`, `skills/_shared/enscript/references/widget_api.md` and `skills/_shared/figma-to-dayz-rules.md`; read them first and come here for depth. A design that comes from Figma goes through the Figma pipeline (`figma-node-normalizer`, `figma-to-dayz-layout`, `dayz-layout-validator`); this pack covers the scripts and polish afterwards.

The runnable tools are elsewhere: `/dayz-layout-preview` draws a layout at several screen sizes and generates preview panels, `/dayz-build-imageset` packs sprites, `/dayz-lint` checks the mod setup, and `scripts/tools/` holds the script validator, the UI reconciler, the layout parser and the HTML viewer.

**How facts are marked.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). "Measured in game" means the result was measured on a running client (DayZ 1.29 unless a line says otherwise) and is not yet checked on `P:\`. Facts about Dabs Framework, DayZ Expansion or the DayZ MCP bridge are third party behaviour, not vanilla, and say which product they describe.

## Which task, which file

| Your task | Read first | Then |
|---|---|---|
| Planning any new UI (menu, HUD, panel) | `plan-to-implementation.md` (the spec table, and why UI ends up different from the plan) | The workflow below |
| "It looks different in game than designed, or at another resolution" | `plan-to-implementation.md` | Rule 3 in `checklist-and-troubleshooting.md`; `text-sizing-and-rendering.md` |
| A new menu opened by a key, menu IDs, a pause style menu | `vanilla-menus-map.md` | `script-recipes.md` (input and cursor) |
| Extending the HUD, hiding or showing HUD groups | `vanilla-menus-map.md` (HUD chain and visibility flags) | |
| Action info panels, construction grids on the cursor (1.30) | `hud-action-info-panels.md` | `ui-changes-1-30.md` |
| Porting a UI mod to DayZ 1.30 | `ui-changes-1-30.md` | `layout-variants.md` |
| Writing or debugging a `.layout` file | `layout-format.md` | Rules 1 to 4 in `checklist-and-troubleshooting.md` |
| Changing a vanilla layout (hide, recolor or add a widget) without replacing it | `layout-variants.md` | `skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md` for the `gui` prefix PBO |
| Starting from a ready layout (modal, HUD overlay, form row, scroll list) | `templates/README.md` | That template, then rules 1 to 4 |
| Iterating a design without repacking | `hot-iteration.md` | `verification.md` |
| Borders, buttons with press feedback, 9-slice, a themed panel | `styles-format.md` | |
| Dabs MVC (ScriptView, bindings, commands, animations) | `skills/_shared/enscript/integrations/dabs_framework.md`, then `dabs-mvc-internals.md` | Rules 15 to 18 in `checklist-and-troubleshooting.md` |
| Expansion menus or HUD | `expansion-mvc-patterns.md`, `expansion-market-menu.md` | |
| A widget method signature, preview widgets, rotation and transform | `widget-prototypes.md` | Or search `P:\scripts\1_core\proto\enwidgets.c` |
| Map, canvas, 3D markers, compass, chat, admin windows | `group-map-hud-patterns.md`, `admin-ui-patterns.md` | |
| Toggles, layouts that avoid overlap, tabs, hover, drag and drop | `interactive-patterns.md` | |
| A recolor or retheme request | `theme-and-color.md` (scope it before you estimate) | `layout-variants.md` |
| Text: stringtable keys, CSV header, preview panels | `localization.md` | |
| Text that is clipped, does not wrap or changes size with resolution | `text-sizing-and-rendering.md` | |
| Imagesets, draw order, a layout typo, image progress bars | `imagesets-draw-order-progress-bars.md` | |
| A check passed but the UI is wrong; widget names collide; a probe lies | `verification.md` | |
| A scripted camera, an interface opened from a vehicle seat, a loading screen | `cameras-seats-loading-screens.md` | |
| An in game color test panel and an A/B comparison | `color-test-harness.md` | `theme-and-color.md` |
| Engine protos, rich text markup, early assumptions that were wrong, open runtime tests | `fact-ledger.md` | |
| Which widgets and attributes real layouts use, and what a static renderer can show | `layout-corpus-counts.md` | `layout-format.md` |
| A keybind to open the UI (`inputs.xml`, `inputs=` in config.cpp) | `skills/_shared/enscript/integrations/input_bindings.md` | `vanilla-menus-map.md` for polling in `OnUpdate` |
| A symptom you cannot place | The troubleshooting table in `checklist-and-troubleshooting.md` | |

**Files to read with care.** `admin-ui-patterns.md` and `group-map-hud-patterns.md` describe third party mods and carry few vanilla citations: treat their code as a pattern to adapt, and check each call against `P:\scripts\1_core\proto\enwidgets.c`. A line that says "Corrected" with a date states what is true now and keeps the older wrong claim visible so nobody brings it back.

## Files

| File | What it holds |
|---|---|
| `checklist-and-troubleshooting.md` | The 18 numbered build rules, the delivery checklist and the symptom to fix table. |
| `plan-to-implementation.md` | Why a built UI differs from the plan, the spec table, Workbench's Layout Editor and its two registrations, the iteration loop and the parity check. |
| `layout-format.md` | The `.layout` syntax: every attribute, unit flag, anchor, `ScriptParamsClass`, and how often vanilla uses each. |
| `layout-corpus-counts.md` | Widget and attribute counts over real vanilla and mod layouts, and what an offline renderer can show. |
| `layout-variants.md` | Changing vanilla widgets in place on 1.30: layout variants, `Prefab` IDs, the `gui` prefix PBO, shadowing an imageset or the styles file. |
| `ui-changes-1-30.md` | What changed in the vanilla UI in 1.30, what breaks and how to migrate. |
| `hud-action-info-panels.md` | The cursor's action info panels and construction grids (1.30). |
| `vanilla-menus-map.md` | Which vanilla menu is which file and layout, menu ID registration, the `UIScriptedMenu` contract, the HUD chain, the inventory and the focus model. |
| `widget-prototypes.md` | Widget method signatures per class, the flag enums, preview widgets, rotation and transform. |
| `styles-format.md` | `.styles` files: states, 9-slice items, `Colorable`, a custom style, the 1.30 `ActionWidget` gradient. |
| `script-recipes.md` | Binding widgets, event signatures, locking input, the cursor, background blur, alignment flags, layout parameters to a script class, text styling, registering styles and imagesets, `defines[]`. |
| `interactive-patterns.md` | Toggles, layouts that avoid overlap, cards, tabs, a draggable window, status bars, hover states, validated input. |
| `theme-and-color.md` | Where UI colors come from, scoping a recolor, why a mod must not call `SetLV`, alpha that is too low, the 3D preview lighting knob. |
| `localization.md` | `stringtable.xml` and `stringtable.csv`, the CSV header the engine needs, generated preview panels. |
| `text-sizing-and-rendering.md` | Whether `wrap` works, how each font takes its size, which widgets honor a layout alpha, transparent images, rendering UI onto a model. |
| `imagesets-draw-order-progress-bars.md` | Imageset file name against set name, draw order by file order, what a layout typo does, image and segmented progress bars. |
| `hot-iteration.md` | Iterating a layout on the running client from `$profile:` without repacking, and its traps. |
| `verification.md` | What an automated check, a probe or the MCP bridge can prove about a UI, name collisions, window resizing, DPI, ESC with a focused EditBox, stale probe files. |
| `cameras-seats-loading-screens.md` | Leaving a scripted camera cleanly, an interface opened from a vehicle seat, hooking the loading screen. |
| `dabs-mvc-internals.md` | How Dabs Framework's MVC behaves: lifecycle, command dispatch, observables, `WidgetAnimator`, `LinearColor`, `ScriptViewMenu`. |
| `expansion-mvc-patterns.md` | How DayZ Expansion builds views: `ExpansionScriptView`, menus, the tick timer, `ExpansionUIManager`, observable collections, dialogs, client settings, HUD registration. |
| `expansion-market-menu.md` | The Expansion Market menu end to end: MVC, its state machine, confirmation before the RPC, the server's price recheck and the RPC handshake. |
| `group-map-hud-patterns.md` | Group and map UI from a large production mod: layout registry, map and canvas calls, 3D markers, compass, text width, chat, dirty checks, tabs, color picker, settings, ping. |
| `admin-ui-patterns.md` | Floating windows, ESP overlays, resizable widgets and a free camera from admin tools. |
| `fact-ledger.md` | Engine protos, the Dabs source, rich text markup, early assumptions that turned out wrong, runtime tests still open. |
| `color-test-harness.md` | An in game color test panel and the A/B protocol. |
| `templates/README.md` | The four starting layouts, their predicted rects, the stringtable they need and the construction mistakes they prevent. |
| `templates/panel-contract.md` | Widget names and options of the generated preview panels (`chat_feed.layout`, `info_panel.layout`, `mini_hud.layout`). |

## The standard workflow

Follow this for any UI you build.

1. **Spec before layout.** Fill the widget tree spec table (`plan-to-implementation.md`): every visual element gets a widget class, a name (the contract for `FindAnyWidget` and bindings), a unit mode and a color source (layout attribute or script `SetColor`). A mockup must stay inside what widgets can do: no gradients, web fonts or rounded corners, because a `.layout` has no equivalent.
2. **Write the `.layout`** in brace format (never XML: an XML layout crashes the client), with anchors and `position 0 0`, the four unit flags declared (rule 3), and `#STR_` keys for all text.
3. **Check the mod setup**: `/dayz-lint <ModName>`.
4. **Check the UI contract** with the script validator and the reconciler, from the repo root:

   ```cmd
   python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
   python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
   ```

   The validator checks braces, XML format, that each layout file exists, the `$PBOPREFIX$` path and the `OnMouseLeave` parameter count. The reconciler matches every `FindAnyWidget` name against the layouts and every `#STR` key against `stringtable.xml` or `stringtable.csv`, with "did you mean" hints; `--strict` turns its warnings into a failure. The validator exits 0 for pass, 1 for fail and 2 for warnings only: gate on the `errors` list in its JSON output, or treat 2 as a pass.
5. **Preview offline.** `/dayz-layout-preview <file.layout>` draws PNGs at several screen sizes. The HTML viewer, `python scripts/tools/dayz-layout-viewer/build_viewer.py <layout>`, writes a `.preview.html` you switch between 1080p, 1440p, 21:9 and 720p. Both are approximations: trust them for where a box is, never for whether your shipped string fits, and read `verification.md` before you trust a view other than 1080p. To read what a layout says (text, color, image, any key) use `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>`.
6. **Build, deploy and look at it in game**: `/dayz-build-pbo`, `/dayz-launch-test`, and the test loop in `skills/dayz-launch-test/references/`. After the session, search the RPT for `Cannot open layout`, take a screenshot at 1080p and at one other resolution (start the client with a different `-x` and `-y`; resizing the window proves nothing), and compare with the calibrated mockup. Put all pending UI checks into one session.
7. **Parity check before you call it done**: the spec table against the built layout, the bindings and the in game screenshot (`plan-to-implementation.md`), then the delivery checklist in `checklist-and-troubleshooting.md`.

When something is wrong in game:

- `MissionBase.DumpCurrentUILayout()` (`P:\scripts\5_mission\mission\missionbase.c:378`) prints the current menu's whole widget tree with visibility.
- The DbgUI immediate mode panel (`P:\scripts\1_core\proto\dbgui.c`) is for live tuning.
- Dabs `ScriptView.ReloadAll()` reloads every Dabs layout, in diag builds only (`dabs-mvc-internals.md`).

## Rules that cost the most when missed

The full list is in `checklist-and-troubleshooting.md`.

- **Brace format, balanced braces.** An XML layout or a missing layout file crashes inside the native `CreateWidgets`, where no null check can help. The parser stops at the first syntax error and silently drops every widget after it.
- **A `FrameWidgetClass` is never visible, and a `PanelWidgetClass` only with a style.** In 1.30 the vanilla action prompt rows are `PanelWidgetClass` (`P:\gui\layouts\day_z_hud.layout:2294`), so an `ImageWidget.Cast` of them is null.
- **Declare all four unit flags.** `0` is a fraction of the parent. `1` is exact units, measured in game as 1/1080 of the screen height on both axes; do not rescale exact widgets from script.
- **Null check `GetGame()` in destructors, `GetWorkspace()` before `CreateWidgets`, and every `FindAnyWidget` and `Cast` result.**
- **A vanilla handler needs `SetHandler(this)`** (`P:\scripts\1_core\proto\enwidgets.c:172`). `OnMouseLeave` takes four parameters, `OnMouseEnter` three (`P:\scripts\1_core\proto\enwidgets.c:665-666`).
- **Never call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod.** They are global and overwrite the player's HUD brightness setting (`theme-and-color.md`).
- **Dabs command handlers return true**, a Dabs menu does not close on ESC by itself, and constructing a `ScriptView` calls `CreateWidgets`, so never construct one from an RPC handler.
- **Widget names are a contract.** A test copy of a layout that keeps the original names cannot be addressed (`verification.md`).
- **A passing automated check proves the contract, not the picture.** A screenshot that a person looks at is mandatory evidence.

## On Linux

The Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`. For UI work only this changes:

- The UI lab tool under `scripts/tools/dayz-ui-lab/` (parsing, checking and offline rendering of `.layout` files) is Python and runs natively.
- Workbench starts under Proton (`dayz-proton.sh gui Workbench`), but its layout and imageset editors were not verified there.
- Packing uses dayzmake 1.0.0 or later in place of AddonBuilder; the helper scripts are in `scripts/tools/dayz-linux/`. An HTML preview is not an in game sign off: keep the widget, binding and runtime checks above.

When the UI has to end in a mod that builds, loads and ships, follow the loop in `skills/dayz-launch-test/references/mod-loop.md` and use `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate` for the steps.
