---
name: dayz-ui-development
description: "Reference for building DayZ UI in Enforce Script: menus, HUD overlays, .layout files, widgets, .styles, imagesets, stringtables, Dabs Framework MVC (ScriptView, ViewBinding, Relay_Command, WidgetAnimator), DayZ Expansion UI patterns, group and map UI patterns, admin windows, map and canvas widgets, and the DayZ 1.30 UI changes and layout variants. Use when you write, fix or review a menu, HUD, panel, dialog or .layout, when CreateWidgets crashes, half the UI is missing, a widget is invisible or not clickable, FindAnyWidget returns null, a button click does not fire, text is clipped or does not wrap, colors look dark, the UI looks different from the mockup or at another resolution, a recolor or retheme is asked for, or ESC does not close a menu. Not for general Enforce Script (enforce-script-reference), turning a Figma design into a layout (the Figma pipeline) or launching the game (/dayz-launch-test)."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-ui-development

What is known about DayZ UI work: the `.layout` format, the widget API, styles, the vanilla menus and HUD, Dabs Framework MVC, DayZ Expansion patterns, group, map and admin tool patterns, and a long list of results measured on a running client. This skill is reference plus one small offline generator and four starting layouts; the skills that build, launch and check a mod gate on `/dayz-preflight` themselves.

Follow `skills/_shared/dayz-conventions.md` and the UI rules in `skills/_shared/conventions/ui.md`; where this skill and those rules differ, the rules win. The short, checked UI packs are `skills/_shared/enscript/references/gui_layout.md`, `skills/_shared/enscript/references/widget_api.md` and `skills/_shared/figma-to-dayz-rules.md`; read them first and come here for depth.

**How facts are marked.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). "Measured in game" means the result was measured on a running client (DayZ 1.29 unless a line says otherwise); those results are not yet checked on `P:\`. Facts about Dabs Framework, DayZ Expansion or the DayZ MCP bridge are third party mod or tool behaviour, not vanilla, and say which product they describe. Each reference file repeats this at its top.

## Which task, which file

| Your task | Read first | Then |
|---|---|---|
| Planning any new UI (menu, HUD, panel) | `references/plan-to-implementation.md` (the spec table, and why UI ends up different from the plan) | The workflow below |
| "It looks different in game than designed, or at another resolution" | `references/plan-to-implementation.md` | Rule 3 in `references/rules-and-checklist.md`; `references/text-sizing-and-rendering.md` |
| A design that comes from Figma | The Figma pipeline (`figma-node-normalizer`, `figma-to-dayz-layout`, `dayz-layout-validator`); rules in `skills/_shared/figma-to-dayz-rules.md` | This skill for scripts and polish afterwards |
| A new menu opened by a key, menu IDs, a pause style menu | `references/vanilla-menus-map.md` (registration, strategies) | `references/script-recipes.md` (input and cursor) |
| Extending the HUD, hiding or showing HUD groups | `references/vanilla-menus-map.md` (HUD chain and visibility flags) | |
| Action info panels, construction grids on the cursor (1.30) | `references/hud-action-info-panels.md` | `references/dayz-130-ui-changes.md` |
| Porting a UI mod to DayZ 1.30 | `references/dayz-130-ui-changes.md` | `references/layout-variants-130.md` |
| Writing or debugging a `.layout` file | `references/layout-format.md` | Rules 1 to 4 in `references/rules-and-checklist.md` |
| Changing a vanilla layout (hide, recolor or add a widget) without replacing it | `references/layout-variants-130.md` | `skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md` for the `gui` prefix PBO with `fsShadowing` |
| Starting from a ready layout (modal, HUD overlay, form row, scroll list) | `templates/README.md` | That template, then rules 1 to 4 |
| Iterating a design without repacking | `references/hot-iteration.md` | `references/verification-and-automation.md` |
| Borders, buttons with press feedback, 9-slice, a themed panel | `references/styles-format.md` | |
| Dabs MVC (ScriptView, bindings, commands, animations) | `skills/_shared/enscript/integrations/dabs_framework.md`, then `references/dabs-framework.md` | Rules 15 to 18 |
| Expansion menus or HUD | `references/expansion-mvc-patterns.md`, `references/expansion-market-menu-pattern.md` | |
| A widget method signature | `references/widget-api.md` | Or search `P:\scripts\1_core\proto\enwidgets.c` |
| Tilting a panel onto a world surface (widget rotation and transform) | `references/widget-api.md` | `references/text-sizing-and-rendering.md` (render to texture is dead) |
| Map, canvas, 3D markers, admin windows | `references/lbgroups-patterns.md`, `references/admin-ui-patterns.md` | |
| A recolor or retheme request | `references/theme-and-color.md` (scope it before you estimate) | `references/layout-variants-130.md` |
| Text: stringtable keys, CSV header, preview panels | `references/localization.md` | |
| Text that is clipped, does not wrap or changes size with resolution | `references/text-sizing-and-rendering.md` | |
| A check passed but the UI is wrong; widget names collide; a probe lies | `references/verification-and-automation.md` | |
| A scripted camera, an interface opened from a vehicle seat, a loading screen | `references/cameras-seats-loading-screens.md` | |
| A keybind to open the UI (`inputs.xml`, `inputs=` in config.cpp) | `skills/_shared/enscript/integrations/input_bindings.md` | `references/vanilla-menus-map.md` for polling in `OnUpdate` |
| A symptom you cannot place | The troubleshooting table in `references/rules-and-checklist.md` | |

**Files to read with care.** `references/advanced-patterns.md` once held three invented API names; read its corrections note at the top before you copy code from it. `references/admin-ui-patterns.md` and `references/lbgroups-patterns.md` carry few file and line citations: treat their code as a pattern to adapt, and check each call against `P:\scripts\1_core\proto\enwidgets.c`. A line that says "Corrected" with a date states what is true now and keeps the older wrong claim visible so nobody brings it back.

## The standard workflow

Follow this for any UI you build.

1. **Spec before layout.** Fill the widget tree spec table (`references/plan-to-implementation.md`): every visual element gets a widget class, a name (the contract for `FindAnyWidget` and bindings), a unit mode and a color source (layout attribute or script `SetColor`). A mockup must stay inside what widgets can do: no gradients, web fonts or rounded corners, because a `.layout` has no equivalent.
2. **Write the `.layout`** in brace format (never XML: an XML layout crashes the client), with anchors and `position 0 0`, the four unit flags declared (rule 3), and `#STR_` keys for all text.
3. **Check the mod setup**: `/dayz-lint <ModName>`.
4. **Check the UI contract** with the script validator and the reconciler, from the repo root:

   ```cmd
   python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
   python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
   ```

   The validator checks braces, XML format, that each layout file exists, the `$PBOPREFIX$` path and the `OnMouseLeave` parameter count. The reconciler matches every `FindAnyWidget` name against the layouts and every `#STR` key against `stringtable.xml` or `stringtable.csv`, with "did you mean" hints; no compiler catches those, and `--strict` turns its warnings into a failure. The validator exits 0 for pass, 1 for fail and **2 for warnings only**: gate on the `errors` list in its JSON output, or treat 2 as a pass.
5. **Preview offline.** `/dayz-layout-preview <file.layout>` draws PNGs at several screen sizes. The HTML viewer, `python scripts/tools/dayz-layout-viewer/build_viewer.py <layout>`, writes a `.preview.html` you switch between 1080p, 1440p, 21:9 and 720p. Both are approximations: trust them for where a box is, never for whether your shipped string fits, and read `references/verification-and-automation.md` ("What the HTML viewer models and what it does not") before you trust a view other than 1080p. To read what a layout says (text, color, image, any key) use `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>`.
6. **Build, deploy and look at it in game**: `/dayz-build-pbo`, `/dayz-launch-test`, and `skills/dayz-test-ingame/` for the test loop. After the session, search the RPT for `Cannot open layout`, take a screenshot at 1080p and at one other resolution (start the client with a different `-x` and `-y`; resizing the window proves nothing), and compare with the calibrated mockup. Put all pending UI checks into one session.
7. **Parity check before you call it done**: the spec table against the built layout, the bindings and the in game screenshot (`references/plan-to-implementation.md`), then the delivery checklist in `references/rules-and-checklist.md`.

When something is wrong in game:

- `MissionBase.DumpCurrentUILayout()` (`P:\scripts\5_mission\mission\missionbase.c:378`) prints the current menu's whole widget tree with visibility.
- The DbgUI immediate mode panel (`P:\scripts\1_core\proto\dbgui.c`) is for live tuning.
- Dabs `ScriptView.ReloadAll()` reloads every Dabs layout, in diag builds only (`references/dabs-framework.md`).

## Rules that hold everywhere

The 18 numbered rules, each traced to a real crash or visual failure, are in `references/rules-and-checklist.md`. The ones that cost the most when missed:

- **Brace format, balanced braces.** An XML layout or a missing layout file crashes inside the native `CreateWidgets`, where no null check can help. The parser stops at the first syntax error and silently drops every widget after it.
- **A `FrameWidgetClass` is never visible, and a `PanelWidgetClass` only with a style.** In 1.30 the vanilla action prompt rows are `PanelWidgetClass` (`P:\gui\layouts\day_z_hud.layout:2294`), so an `ImageWidget.Cast` of them is null.
- **Declare all four unit flags.** `0` is a fraction of the parent. `1` is exact units, measured in game as 1/1080 of the screen height on both axes; do not rescale exact widgets from script.
- **Null check `GetGame()` in destructors, `GetWorkspace()` before `CreateWidgets`, and every `FindAnyWidget` and `Cast` result.**
- **A vanilla handler needs `SetHandler(this)`** (`P:\scripts\1_core\proto\enwidgets.c:172`). `OnMouseLeave` takes four parameters, `OnMouseEnter` three (`P:\scripts\1_core\proto\enwidgets.c:665-666`).
- **Never call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod.** They are global and overwrite the player's HUD brightness setting (`references/theme-and-color.md`).
- **Dabs command handlers return true**, a Dabs menu does not close on ESC by itself, and constructing a `ScriptView` calls `CreateWidgets`, so never construct one from an RPC handler.
- **Widget names are a contract.** A test copy of a layout that keeps the original names cannot be addressed (`references/verification-and-automation.md`).
- **A passing automated check proves the contract, not the picture.** A screenshot that a person looks at is mandatory evidence.

## What to read

| Question | Read |
|---|---|
| What are the 18 rules, the delivery checklist and the symptom to fix table? | `references/rules-and-checklist.md` |
| Why does my UI differ from the plan, how do I write the spec table, what is the iteration loop and the parity check? How do Workbench's Layout Editor and the two asset registrations fit in? | `references/plan-to-implementation.md` |
| What is the `.layout` syntax: every attribute, unit flag, anchor, `ScriptParamsClass`, and how often vanilla uses each? | `references/layout-format.md` |
| What does a corpus of real vanilla and mod layouts show about widget and attribute frequency, and how do the offline renderer and the Dabs path fix work? | `references/layout-empirical-corpus.md` |
| How do I change vanilla widgets in place on 1.30 (layout variants, `Prefab` IDs, the `gui` prefix PBO, shadowing an imageset or the styles file)? | `references/layout-variants-130.md` |
| What changed in the vanilla UI in 1.30, what breaks and how do I migrate? | `references/dayz-130-ui-changes.md` |
| How do the cursor's action info panels and construction grids work (1.30)? | `references/hud-action-info-panels.md` |
| Which vanilla menu is which file and layout, how are menu IDs registered, what is the `UIScriptedMenu` contract, the HUD chain, the inventory architecture and the focus model? | `references/vanilla-menus-map.md` |
| What is the signature of a widget method, and which methods exist on which widget class (preview widgets, rotation and transform included)? | `references/widget-api.md` |
| How do `.styles` files work: states, 9-slice items, `Colorable`, a custom style, the 1.30 `ActionWidget` gradient? | `references/styles-format.md` |
| How do I bind widgets automatically, what are the event signatures, how do I lock input, show the cursor, blur the background, set alignment flags, pass layout parameters to a script class, style text, register styles and imagesets, or use `defines[]`? | `references/script-recipes.md` |
| Toggles, layouts that avoid overlap, tabs, hover states, drag and drop? | `references/advanced-patterns.md` |
| Where do UI colors come from, how do I scope a recolor, what is Colorful UI, why must I not call `SetLV`, what alpha is too low? | `references/theme-and-color.md` |
| How do `stringtable.xml` and `stringtable.csv` work, which CSV header does the engine need, and how do I generate preview panels? | `references/localization.md` |
| Does `wrap` work, how does each font take its size, which widgets honor a layout alpha, what does a transparent image need, can I render UI onto a model? | `references/text-sizing-and-rendering.md` |
| How do I iterate a layout on the running client from `$profile:` without repacking, and what are the traps? | `references/hot-iteration.md` |
| What can an automated check, a probe or the MCP bridge prove about a UI, and what not? Name collisions, window resizing, DPI, ESC with a focused EditBox, stale probe files, `ui_reload_layout`? | `references/verification-and-automation.md` |
| How do I leave a scripted camera cleanly, open an interface from a vehicle seat, or hook the loading screen? | `references/cameras-seats-loading-screens.md` |
| How does Dabs Framework's MVC really behave: lifecycle, command dispatch, observables, `WidgetAnimator`, `LinearColor`, `ScriptViewMenu`? | `references/dabs-framework.md` |
| How does DayZ Expansion build views: `ExpansionScriptView`, `ExpansionScriptViewMenu` show and hide (blur, control lock), the opt in tick timer, `ExpansionUIManager`, observable collections, a sub view per row, composable dialogs, client settings by dot path, HUD registration? | `references/expansion-mvc-patterns.md` |
| How is the Expansion Market menu built end to end: MVC, the seven state machine, confirmation before the RPC, the server's price recheck, reserve, stock, money, spawn and save, trader permissions, the four step RPC handshake? | `references/expansion-market-menu-pattern.md` |
| How do I build group and map UI: layout manager registry, map widget calls, canvas drawing, 3D marker projection, compass strip, text width measuring, chat ring buffer, dirty checks, tabs, color picker, drag and drop on the map, JSON settings, tactical ping? | `references/lbgroups-patterns.md` |
| How do admin tools build floating windows, ESP overlays, resizable widgets and a free camera? | `references/admin-ui-patterns.md` |
| Which UI facts were verified in production use of a shipped mod (80 and more)? | `references/lfpg-knowledge-base.md` |
| How do I build an in game color test panel and run an A/B comparison? | `references/color-test-harness.md` |
| Which vanilla classes does a loading screen mod hook, why is an imageset's file name not its set name, how does file order decide draw order, what does a layout typo do, and how do image based and segmented progress bars work? | `references/community-findings.md` |
| Which starting layout do I copy, and which four construction mistakes do the templates prevent? | `templates/README.md` |
| What are the widget names of the generated preview panels? | `<skill-dir>\scripts\CONTRACT.md` |

## Files in this skill besides the references

| File | What it is |
|---|---|
| `<skill-dir>\scripts\gen_panel_layout.py` | Offline generator for preview panels (a chat or log feed, a label and value panel, a minimal HUD) made for the hot iteration loop. `python "<skill-dir>\scripts\gen_panel_layout.py" --self-test` checks brace balance and unique names without the game. It reads and writes only the files you name, so it does not gate on `/dayz-preflight`. Usage is in `references/localization.md` and `<skill-dir>\scripts\CONTRACT.md`. |
| `scripts/chat_feed.layout`, `scripts/info_panel.layout`, `scripts/mini_hud.layout` | Panels the generator produced, ready to load. |
| `templates/modal_panel.layout`, `templates/hud_overlay.layout`, `templates/form_row.layout`, `templates/scroll_list.layout` | Starting layouts to copy. |
| `templates/*.rects.1280.json`, `templates/*.rects.1920.json` | The predicted rect of every template widget at 1280x720 and 1920x1080, to compare with a live tree. |
| `templates/stringtable.csv` | The seven `#STR_` keys the templates use, with the seven column header the engine needs. |

Outside an agent session, `scripts\dayz\ui-gen-panel.bat` runs `gen_panel_layout.py` with the same arguments.

## On Linux

Everything above is the Windows workflow. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`; only this changes for UI work:

- The UI lab tool under `scripts/tools/dayz-ui-lab/` (parsing, checking and offline rendering of `.layout` files) is Python and runs natively.
- Workbench starts under Proton (`dayz-proton.sh gui Workbench`), but its layout and imageset editors were **not verified** there. `P:\gui\...` is the extracted vanilla data under the directory that `dayz-proton.sh init` maps.
- Packing uses dayzmake 1.0.0 or later in place of AddonBuilder. The helper scripts are in `skills/_shared/scripts/` (`dayz-client-headless.sh` takes retail client screenshots against the native server; with the Expansion bundle, switch its spawn selector off first). An HTML preview is not an in game sign off: keep the widget, binding and runtime checks of this skill.

## Building, testing and publishing the mod

When the UI has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow the loop in the `dayz-mod-dev` skill, and use `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate` for the steps.
