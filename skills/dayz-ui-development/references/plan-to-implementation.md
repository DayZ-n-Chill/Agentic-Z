# From UI plan to implementation: why the build differs from the plan, and how to close the gap

Added 2026-07-03. This file exists because of one recurring failure: **the UI never comes out
like it was planned.** It answers *why* that happens in DayZ/Enfusion specifically, and gives a
concrete author → preview → build → verify loop plus a plan/spec artifact and a parity gate.

Evidence: a `path:line` citation points into the vanilla data on `P:\` (read on a `P:\` holding 1.30).
A line marked "not checked on `P:\`" is a behaviour seen in practice that was not confirmed
against the vanilla files. In-game measurements say what was measured and when. If a line has
neither, treat it as a hint.

---

## 0. TL;DR — the five moves that close most of the gap

1. **Pick the unit per widget, knowing what each one is** (section 1.1, section 2): exact (= 1) is 1/1080 of
   the screen height and keeps a widget's shape at every resolution; proportional (= 0) stretches
   with the parent. Never rescale exact widgets from script. *(corrected 2026-10-03: this move
   said «**Author in proportional units (flags = 0) by default**, exact pixels (= 1) only for
   things that must be pixel-true. All-exact layouts look right at 1080p and wrong everywhere
   else».
   A shipped all-exact panel measured right at 1920x1080, 1280x720 and 2560x1080.)*
2. **If you use the Workbench Layout Editor, register your imagesets/styles twice** — in
   `dayz.gproj` (so the editor previews them) and in `config.cpp class defs` (so the game loads
   them). Missing either side is a direct mockup-vs-game divergence (section 3).
3. **Keep the design mockup inside the widget model.** No gradients, border-radius, web fonts,
   scanlines, CSS-only effects — none have a `.layout` equivalent, so a mockup that uses them is
   unimplementable as drawn and guarantees divergence (section 1.6, section 5).
4. **Run the offline gate before every in-game test**: linter → name/#STR reconciliation →
   approximate render. Cheap; catches the crashes and the "half my UI vanished" cases (section 4, section 6).
5. **Verify implemented-against-plan, not just syntax.** Every planned widget must exist with the
   planned name/mode; every `Binding_Name` must match a controller property; screenshot at the
   target resolution and diff against the calibrated mockup (section 6).

---

## 1. Why implemented UI diverges from the plan — the root-cause catalog

Six independent mechanisms. Each is a real, verified reason the in-game result differs from what
was drawn or specified. Knowing which one bit you is half the fix.

### 1.1 Exact flags mean units of 1/1080 of the screen height, not pixels and not "defined position"
`hexactpos/vexactpos/hexactsize/vexactsize 1` switches that axis to **exact units**: the engine
draws `declared × height/1080` px on both axes, whatever the width (measured in game at heights
461 to 1108 and at 2560x1080; `rules-and-checklist.md` rule 3). A layout in exact units keeps its share of the
screen height at every resolution measured; at another aspect ratio only the horizontal room
changes.
- The header comments say otherwise: `P:\scripts\1_core\proto\enwidgets.c:68-71` — `EXACTPOS //< Uses
  physical resolution (g_iWidth, h_iHeight)`, `HEXACTSIZE //< Uses physical resolution (g_iWidth)`.
  The frame decides: a 400-unit panel drew 400 px wide at 1920x1080 and at 2560x1080, and
  267 px at 1280x720.
- `0` = **fraction of parent (0.0–1.0)**. Vanilla predominantly uses proportional: over
  the 227 layouts under `P:\gui\layouts` on 1.30, `hexactsize 0` appears 6167× vs `hexactsize 1`
  3265×, about two to one.
- The divergence that does come with exact units is script-made: a script that rescales exact
  widgets by height/1080 scales them twice (`text-sizing-and-rendering.md`, "Text sizing laws").
- *(corrected 2026-10-03)* This section was titled «Exact flags mean physical pixels», said a
  layout authored at 1920×1080 «occupies a different fraction of the screen at 2560×1440,
  ultrawide, or console», said an exact layout «will only work on 1 resolution and 1
  aspect ratio» and called it «the single
  most common cause of "looked right in my mockup, wrong in-game."» The in-game measurements
  above contradict the pixel reading: at 16:9 the fraction stayed the same at every height
  measured, and at 2560x1080 only the horizontal fraction changed. 2560×1440 itself was not
  measured, and nothing measured how common the cause is.

### 1.2 Colors are re-lit by the engine (global LV), and a script `SetColor` can override the layout
Two things move color away from what you authored:
- Global LV darkening — which is the player's HUD brightness, not an engine constant. There is
  no fix to apply: `SetLV`/`SetTextLV` are `proto static` (`P:\scripts\1_core\proto\enwidgets.c:114-117`) and vanilla
  drives them from `EDayZProfilesOptions.HUD_BRIGHTNESS` (`P:\scripts\3_game\dayzgame.c:3910-3919`), so calling
  them from a mod overwrites the player's choice. Author honest ARGB, verify at a dimmed HUD,
  and do not pre-boost values either.
- Most mods set final colors in **script** via `SetColor(ARGB)` after `CreateWidgets`, not in the
  `.layout`. So a static preview of the `.layout` alone cannot know the real colors — the plan
  must record intended colors separately, and the renderer's colors are best-effort only.
- `ImageWidget.SetColor()` **modulates/tints** the texture (multiplies), it does not repaint pixels
  — an already-colored image gets desaturated, not recolored. Author recolorable art white/greyscale
  and tint via `SetColor`. (Not checked on `P:\`.)

### 1.3 3D-object brightness inside widgets is a separate knob
Item/player previews render dark unless you touch `Widget.SetObjectLighting(float [0,1], default 1)`
(`P:\scripts\1_core\proto\enwidgets.c:118-119`) — distinct from `SetLV`. If a planned inventory/preview panel "looks murky"
in-game but fine in the mockup, this is why.

### 1.4 Script-driven spacers overwrite authored child geometry at runtime
Any widget carrying a `SpacerBase`-derived `scriptclass` (e.g. `VerticalSpacer`, `HorizontalSpacer`)
has `EXACTPOS|EXACTSIZE` forced onto every child at init and on `OnChildAdd`, and the spacer then repositions children in
exact units (section 1.1) — so proportional pos/size you authored on those children is **silently discarded**
in-game while the editor preview still shows the authored values.
- Evidence: `P:\scripts\3_game\gui\spacers\spacerbase.c:13-19` and `P:\scripts\3_game\gui\spacers\spacerbase.c:32-37`
  (`child.SetFlags(WidgetFlags.EXACTPOS | WidgetFlags.EXACTSIZE, false)` inside
  `OnWidgetScriptInit`/`OnChildAdd`).

### 1.5 Workbench editor preview ≠ game unless assets are registered on both sides
Custom imagesets and `.styles` render in the Workbench **Layout Editor** only if listed in
`dayz.gproj`; the **game** only loads them if listed in `config.cpp class defs`. Register one side
and not the other and the mockup and the build disagree by construction. Full mechanism in section 3.

### 1.6 The design mockup uses features with no `.layout` equivalent
When the "plan" is a freeform HTML/CSS mockup (Google-Fonts web font, radial-gradient, scanlines,
border-radius), none of those map to a widget attribute, so the implementation *cannot* match by
definition and the gap is judged by eye between two hand-made artifacts.
- Seen in practice: a design mockup that used a CDN font and gradients could not be matched, and the
  mockup later rebuilt from the real `.layout` files had to be labelled "positions and colors taken
  from the real `.layout` files … Not the exact pixel of the engine".
- **Rule:** the design mockup must stay inside the widget model — every visual element maps to a
  widget class + a verified attribute, or it doesn't go in the plan.

### 1.7 Bonus divergence sources worth a glance
- `text_proportion` (text size as a fraction of widget height) drives most vanilla text scaling; an
  arbitrary mockup `font-size` px does not represent it — calibrate the mockup or label it
  "approximation" (see `text-sizing-and-rendering.md`, "Mockup fidelity").
- `UIManager.IsScaledMode()/SetScaledMode(bool)` is an engine-level UI scale toggle
  (`P:\scripts\3_game\tools\uimanager.c:55-56`) — check it when "same layout, different size on a
  player's machine" before touching the layout.
- `EditBoxWidget` cannot center its text (no alignment API; `P:\scripts\1_core\proto\enwidgets.c:347-351`) — plan single-line
  inputs left-aligned or fake it with a `TextWidget` overlay.

---

## 2. Authoring resolution-independent layouts (what section 1.1 means in practice)

- **Proportional (flags 0):** position/size are fractions of the parent, so the widget scales with
  the parent and stretches with its aspect. Use `halign`/`valign` `*_ref` anchors to pin to an
  edge/center of the parent (`valign` 4,687× + `halign` 4,064× across the 227 layouts under
  `P:\gui\layouts` on 1.30 — heavily used, not "rare").
- **Exact (flags 1):** units of 1/1080 of the screen height, so the widget keeps its shape and
  scales with the screen height. It does not keep a pixel size: by that law a 1-unit border is
  2/3 of a pixel at 720p (how the engine rasterizes it was not measured).
  Mixing exact and proportional axes on one widget is the vanilla norm (`rules-and-checklist.md` rule 3, corpus
  refinements).
- *(corrected 2026-10-03)* This section was titled «the fix for section 1.1» and said: «Default to
  proportional (flags 0)», «so the UI scales with resolution and aspect», «**Reach for exact
  (flags 1) only** for elements that must keep a pixel size (icon tiles, 1px borders, fixed-size
  buttons). Mixing pixel-pos + proportional-size on the same widget is fragile under resize —
  keep a widget all-exact or all-proportional.» Exact widgets scale with the screen height
  (section 1.1), and `rules-and-checklist.md` rule 3 had already refuted the mixing warning from the corpus on
  2026-07-04.
- **Canonical resolution-independent full-screen 16:9 background:**
  ```
  ImageWidgetClass Background {
      size 0.16 0.09                 // 16% × 9%  (not 1.0 1.0)
      hexactpos 0 vexactpos 0 hexactsize 0 vexactsize 0
      halign center_ref
      valign center_ref
      fixaspect outside              // vanilla values seen: fixwidth (most common), inside, outside, none
      "stretch mode" stretch_w_h
      image0 "MyMod/gui/textures/bg_co.edds"   // 16:9 source, 2048×1024 recommended for large monitors
      { }
  }
  ```
  Evidence: `P:\gui\layouts\loading.layout:36-55` (the vanilla widget sets these same position,
  size, anchor and `fixaspect` values).
- **Console/TV:** the `keepsafezone` attribute (246× under `P:\gui\layouts` on 1.30) respects TV-safe margins. Gamepad/
  keyboard focus = the global `SetFocus(Widget)/GetFocus()` pair — *(corrected 2026-07-04:
  `SetActiveWindow` has zero vanilla call sites; do not design around it)*. Vanilla conventions:
  console menus `SetFocus(defaultButton)` in Init, hover and focus share one highlight path
  (OnMouseEnter/OnFocus → same ColorHighlight), device hot-swap via
  `GetOnInputDeviceChanged().Insert(fn)` + Remove in destructor. Full model:
  `vanilla-menus-map.md`, section 7.

---

## 3. The Workbench Layout Editor (the WYSIWYG tool) + dual registration

**Yes, DayZ Tools Workbench includes a WYSIWYG Layout Editor for `.layout` files** (the early
Enfusion editor; same workflow Arma Reforger documents as "Layout Creation" — create the
`UI/layouts` tree, right-click → new `.layout`, double-click to open in the Layout Editor). It is the
most direct way to make the plan and the implementation the same artifact instead of two.

Reality check: it exists, but it is not a silver bullet — DayZ layouts are still commonly
written by hand. Use the editor for visual positioning/preview; keep the brace-format file as source of truth.

**The double-registration rule (verified mechanism of editor-vs-game divergence):**
- For the **Layout Editor to preview** your custom imagesets / `.styles`, register them in
  **`dayz.gproj`** (`GameProjectClass` `imageSets{}` / `widgetStyles{}` blocks), then restart
  Workbench. **Common practice: keep a per-mod dayz.gproj instead of
  hand-editing the global one next to `workbenchApp.exe`** — a copyable example: Community Online
  Tools ships `JM/COT/Workbench/dayz.gproj` (complete GameProjectClass with `FileSystemPathClass
  Name "Game Root" Directory "P:"` + imageSets/widgetStyles/ScriptModules blocks). Another route is
  to generate the gproj from a template and copy it to the Workbench folder, after which Workbench
  auto-loads the mod's `.c`, `.layout` and `.styles` files. (Third-party mod behaviour and Workbench
  behaviour; not checked on `P:\`.)
- For the **game to load** the same assets, register them in **`config.cpp`**:
  ```cpp
  class CfgPatches { /* ... */ };
  class defs {
      class imageSets    { files[] = { "MyMod/gui/imagesets/my_set.imageset" }; };
      class widgetStyles { files[] = { "MyMod/gui/styles/my.styles" }; };
  };
  ```
- Missing `dayz.gproj` side → images/styles blank in the editor mockup. Missing `config.cpp` side →
  blank in-game. Keep both in sync or the plan and the build disagree.
- Workbench launch recipe (not checked here; `/dayz-launch-workbench` opens Workbench on a mod's gproj): run
  `workbenchApp.exe` with cwd = DayZ install,
  `-mod=<relative;prefixes;to;each;mod>` (semicolon-separated, each pointing at the folder with the
  `CfgMods` config.cpp), `-newErrorsAreWarnings=1`, `-profiles=...`; kill any running instance first.
- Editor quirk (not checked here): a `MapWidget` cannot be resized directly — change its type to
  another class, resize, switch back.

---

## 4. The offline → in-game iteration loop

What to write is covered elsewhere in this skill; this section is how to see it fast. The loop is
assembled from the tools under `scripts/tools/` and keybind-toggled test harnesses.

### 4.1 Iteration mechanics (verified)
- Client + server as `DayZDiag_x64.exe` + `-filePatching` + `serverDZ.cfg allowFilePatching=1` lets
  you edit raw `.c` without a PBO rebuild, and skips BattlEye + `.bisign` signing (harness mods are
  cheap to deploy). `/dayz-launch-test` starts the Diag server and client for you.
- **There is no script hot-reload**: a mission restart is required to pick up `.c` changes, and
  `config.cpp` changes always require a full PBO rebuild. `-clear` on AddonBuilder avoids stale
  `-temp`.
- **Layout hot reload (measured in game 2026-08-19; details in `hot-iteration.md`).** A raw
  `.layout` can be re-read from disk when a menu is closed and reopened, which cuts UI iteration from
  rebuild+reconnect (~3-10 min) to edit-file + reopen-menu (seconds), with no restart, but only from
  one place. A `.layout` under
  an addon prefix is served only by the PBO, loose files included, but a `.layout` under `$profile:` is
  re-read from disk on every `CreateWidgets`, which gives the seconds-long loop.
  **Dabs UIs:** Dabs Framework has `static ScriptView.ReloadAll()` under `#ifdef DIAG_DEVELOPER`
  (`MVC/ScriptView.c`; Dabs source, not on P:\, not yet checked), which unlinks and rebuilds every
  live ScriptView's layout. The same rule applies to it: the rebuild reads the layout from wherever
  its path points. A view whose layout sits under its mod's addon prefix still shows a disk edit only
  after a repack; point the view's layout path under `$profile:` (`hot-iteration.md`) to get the
  seconds-long loop from a keybind or DbgUI button.

### 4.2 Tools on disk
- **Pre-PBO linter** — `scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>` (JSON
  to stdout; exit 0 PASS / 1 FAIL / 2 WARN). Four UI detectors: XML-format layout
  (crashes `CreateWidgets`), layout-file-missing (referenced from `.c` but absent → un-guardable CTD),
  `$PBOPREFIX$` path mismatch (→ crash + ghost menu), 3-param `OnMouseLeave` (compiles, never fires).
  A fifth, the leaf-brace detector, is quarantined because its rule was false (`rules-and-checklist.md`
  rule 1). **Make this step 1 of the delivery checklist.**
- **What to distrust in a naive `.layout`→HTML renderer.** A first-generation renderer (v1, not in
  this repo) had 15+ fidelity bugs, and any static preview can repeat them: `visible 0` ignored, `text_proportion`
  never modelled (all text ~14px), `halign right_ref/bottom_ref` sign inverted, script-side centering
  not emulated, GridSpacer/WrapSpacer/Scroll layout not implemented, only the first root parsed,
  companion-`.c` color/text extraction by fragile regex that emits plausible-but-wrong output with no
  warning. Such a preview is good for gross layout/text sanity; never trust its pixels or colors.
- **Renderer v2 — the faithful offline previewer** —
  `python scripts/tools/dayz-layout-viewer/build_viewer.py <in.layout> [-o out.preview.html] [--layout-root DIR]`.
  Uses the layout parser `scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py` (tokenizer + parser +
  geometry resolver) and bundles the resolved geometry
  at 4 resolutions (1080p / 1440p / ultrawide 21:9 / 720p) into one self-contained `*.preview.html` that
  opens in any browser with no server. Improvements over v1 that matter for fidelity: **respects
  `visible 0`** (v1 rendered hidden widgets), **models `text_proportion`** (font-size = proportion ×
  widget-height; v1 pinned all text ~14px), renders all roots (v1 only the first), surfaces parser
  diagnostics (missing-child-block etc.), badges anchors the resolver marks `assumed` (center/right/
  bottom_ref phase-1), badges spacer containers (children auto-laid-out in-game), shows MVC
  `Binding_Name`/`Relay_Command`, and a resolution switcher. In it exact widgets keep their declared
  px at every viewport while proportional widgets scale; the engine scales both (section 1.1), so off-1080p
  that difference is the previewer's, not the game's. *(corrected 2026-10-03: this called the
  switcher «the money feature» that makes «the exact-flag divergence VISIBLE», so «you SEE which
  parts of the layout break off-1080p before ever launching the game».)* Still an
  approximation (real Metron fonts, PAA/EDDS textures shown hatched, and script-side `SetColor`/`SetPos`
  are not emulated — trust in-game for pixels/colors/fonts). Self-tested headless 2026-07-03 on
  the vanilla `loading.layout` and `day_z_hud.layout` and on one mod layout
  (0 pageerrors, all toggles + resolution switch verified).
- **In-game harnesses (keybind-toggled test menus).** Three test mods.
  `LF_ColorTest` is reproduced in `color-test-harness.md`; the other two are described, not shipped.
  - `LF_ColorTest` — F7 (scancode 65) panel of 10 known-ARGB swatches + SetLV(0) A/B protocol (a
    measurement only; a mod must not call `SetLV`, section 1.2).
  - `LFPG_UITest` — P key (scancode 25) panel: RichText markup, VideoWidget, widget-creation perf
    (300/500 items + live FPS). Header comment says "type uitest in chat" but the real opener is P.
  - `LF_UILab` — grave/º key (scancode 41) Dabs-MVC test-lab with TestRunner/TestCase, PASS/FAIL
    `[UILab]`-prefixed RPT lines, ExportToLog cheat-sheet. **~90% unbuilt** (only the V00 self-test is
    registered) and its `config.cpp` still carries error E01 (`requiredAddons[] { "DabsFramework" }` —
    must be `"DF_Scripts"`/`"DF_GUI"`). Fix E01 before reusing; then it is the ready scaffold for a
    keybind-toggled UI harness.
- **`DbgUI` (vanilla immediate-mode debug UI) — instant live tuning, no rebuild.**
  `P:\scripts\1_core\proto\dbgui.c:59-126` exposes `SliderFloat/InputFloat/Button/Combo/Check/PlotLive/Begin/End` +
  `FloatOverride`. Call per-frame from `OnUpdate`; a DbgUI slider panel driving `SetPos/SetColor/
  SetTextExactSize` on a live menu gives real-time UI tweaking, then bake the final numbers into the
  `.layout`. (DiagMenu proper needs DayZDiag + WIN+ALT; DbgUI itself compiles in retail.)
- **Cheap post-test gate:** grep the RPT for `Cannot open layout <path>` — present when a layout fails
  to load (a clean load produces zero). Also grep your
  harness `[UILab]`/LOG_TAG PASS/FAIL lines. Group all in-game checks into one session.

### 4.3 The loop, assembled
1. Author `.layout` in **brace** format (Layout Editor for visual placement, or by hand).
2. `python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>` → fix all findings.
3. Reconciliation gate (section 6.2): `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon>` — FindAnyWidget
   names + `#STR` keys cross-checked against layouts + stringtable.
4. Faithful-ish preview: `build_viewer.py <layout>` (v2 — respects `visible`, models `text_proportion`;
   its resolution switcher draws exact widgets as pixels, so only its 1080p view places them as the
   game does, section 1.1). Open the `*.preview.html` and diff the 1080p view against the design mockup for
   gross layout. *(corrected 2026-10-03: this step said the «resolution switcher exposes exact-flag
   breakage» and had you «flip through resolutions».)*
5. Build with `/dayz-build-pbo` and run with `/dayz-launch-test` (DayZDiag, no signing; the `dayz-test-ingame`
   skill covers the in-game checks) with a keybind-toggled test menu (LF_ColorTest / LFPG_UITest pattern). Optionally add a DbgUI slider panel for live tuning.
6. Post-session: grep RPT for `Cannot open layout` + harness PASS/FAIL; screenshot at target
   resolution; diff vs the calibrated mockup (section 6.3).

---

## 5. The UI plan/spec artifact (write this before any `.layout`)

Produce this small artifact first; it is the forward contract for
the UI (it mirrors the `dayz-feature-spec` skill).

**5.1 Widget-tree spec table** — one row per widget the plan requires:

| Widget name | Class | Parent | Mode (prop/exact) | Pos | Size | Anchor (h/valign) | Text/#STR | Binding_Name / handler | Color source (layout vs script) |
|---|---|---|---|---|---|---|---|---|---|

Rules for filling it:
- Every visual element in the mockup must appear as a row with a real widget **class** (no element
  that only exists as a CSS effect). If it can't be expressed as a widget + verified attribute, it is
  not in the plan (section 1.6).
- Choose **Mode** per widget up front (section 2): exact keeps its shape, proportional stretches with
  its parent.
- Name every widget you will `FindAnyWidget`/bind — the name in this table is the contract section 6 checks.
- Record where each color comes from (layout attribute vs script `SetColor`) so the preview's
  limitations are known and the in-game color is planned, not discovered.

**5.2 Acceptance criteria (forward contract):** derive them from what the consumer needs, not from
internal consistency — "every row's widget exists in the built layout with the planned name and mode;
every `Binding_Name` resolves to a controller property; every `#STR` resolves in stringtable; the
build screenshots within tolerance of the calibrated mockup at 1080p and one non-1080p resolution."

---

## 6. The plan → implementation parity gate (the closing check)

The delivery checklist in `rules-and-checklist.md` is mostly syntax (braces, flags, null-checks). Add this gate that ties
the build back to the plan. A crashing UI merge once passed points 1/4/5 before an in-game
test, so this gate catches real failures.

### 6.1 Offline load gate (automate where possible)
1. Every `CreateWidgets(path)` resolves to a file that exists and is **brace** format (not XML).
   *(A missing file is an un-guardable native CTD — the `if(!root)` after `CreateWidgets` never runs.
   linter: layout-file-missing + XML-format.)*
2. Brace balance per layout (opens == closes); zero XML characters. *(linter: XML-format; count
   the braces yourself.)*
3. `$PBOPREFIX$`/packaging: every layout path starts with the prefix, and `gui/` (plus
   `*.layout;*.imageset;*.fnt;*.styles;*.edds;*.paa;*.xml`) actually ships — AddonBuilder only packs
   extensions in its copy-list, so a working-locally / missing-for-others UI is usually a packaging
   filter miss. *(linter: PBOPREFIX path.)*

### 6.2 Name / key reconciliation (automated 2026-07-03)
Run `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` (exit 0 clean / 1 FAIL
typo-likely / 2 WARN verify; `--json` for machine output). It cross-checks the whole addon at once:
4. Every string-literal `FindAnyWidget("X")` / `FindWidget("A/B/C")` in `.c` resolves to a widget
   present in some `.layout` of the addon (case-sensitive; a case-only diff is a FAIL — runtime lookup
   is case-sensitive). A close-but-unequal name is FAIL with a "did you mean" suggestion (typo/rename →
   silent null → crash on Cast); a name with no match is WARN (could be vanilla or dynamically created).
5. Every `#STR_...` used in layouts and `.c` string literals exists in the addon's `stringtable.xml`
   or legacy `stringtable.csv` (case-insensitive; typo → FAIL with suggestion, else WARN).
   Verified 2026-07-03 on two mods: clean on a small test mod (28 refs, 0 findings) and on a large
   production mod (22 refs + 143 #STR over 261 CSV keys, 0 FAIL) — and it surfaced a real dangling
   `CreateWidgets` on a missing layout there. Known false negative: names/keys built from variables or
   concatenation are not resolvable statically and are skipped by design.
6. Every `Binding_Name` / `Relay_Command` matches a controller property/method exactly (still manual —
   grep both sides).

### 6.3 Implemented-against-plan (the fidelity check)
7. Every widget in the section 5 spec table exists in the built layout with the planned **name, class, and
   mode**; nothing planned is missing, nothing unplanned crept in.
8. Render the written `.layout` with `scripts/tools/dayz-layout-viewer/build_viewer.py` (or
   `/dayz-layout-preview`) and eyeball it against the mockup for gross
   layout — then trust only the in-game screenshot for pixels/colors/fonts.
9. Screenshot in-game at 1080p **and** one non-1080p resolution; diff against the calibrated mockup.
   Resolution divergence here = a script rescaling exact widgets, a bitmap face that does not
   shrink with its box (`text-sizing-and-rendering.md`, "Text sizing laws") or a proportional width at another aspect
   (section 1.1); asset-blank divergence = dual-registration (section 3); color divergence = SetLV / script
   SetColor (section 1.2).

---

## 7. Condensed verified facts that feed the above

Menu lifecycle (see also `vanilla-menus-map.md` and `expansion-mvc-patterns.md`):
- Two opening APIs: `UIManager.EnterScriptedMenu(int id, parent)` creates+opens by **registered
  MenuID** (routes through `Mission.CreateScriptedMenu(id)` — a modded menu opened by ID must be added
  to a `modded ... CreateScriptedMenu(int id)` switch that calls `menu.SetID(id)` on the new instance;
  a common bug puts `SetID` in the wrong branch, leaving `MENU_UNKNOWN`); `ShowScriptedMenu(menu,
  parent)` shows an already-constructed instance. `P:\scripts\3_game\tools\uimanager.c`,
  `P:\scripts\3_game\dayzgame.c:1415-1421`, `P:\scripts\5_mission\mission\missionbase.c:198-354`, `P:\scripts\3_game\tools\uiscriptedmenu.c:136-153`.
- Vanilla MenuID range is 1..48 (`P:\scripts\3_game\constants.c:176-223`, `MENU_ANY`..
  `MENU_UNDERGROUND_TRIGGER_EDITOR`); pick an arbitrary high int for custom menus (e.g. 98765).
- `UIScriptedMenu.OnShow()` auto-calls `LockControls()` and `OnHide()` auto-`UnlockControls()` — per
  device `ChangeGameFocus(±1, INPUT_DEVICE_MOUSE/KEYBOARD/GAMEPAD)` + cursor. Overriding OnShow/OnHide
  without `super` skips input locking; adding your own `ChangeGameFocus` on top double-counts the
  stack. `IsHandlingPlayerDeathEvent()` returns true by default → the menu force-`Close()`s on player
  death; override to `false` to survive death. `P:\scripts\3_game\tools\uiscriptedmenu.c:80-134`,
  `P:\scripts\3_game\tools\uiscriptedmenu.c:173-192`, `P:\scripts\3_game\tools\uiscriptedmenu.c:603-611`.
- Native modal (no custom layout): `GetUIManager().ShowDialog(caption, text, id, DBT_YESNO, DBB_YES,
  DMT_QUESTION, handler)` → result to `OnModalResult(w,x,y,code,result)` where `code==id`.
  `P:\scripts\3_game\tools\uimanager.c:21-45`.
- HUD overlays extend `ScriptedWidgetEventHandler` (not `UIScriptedMenu`); must `Unlink()` the root in
  `OnMissionFinish` or widgets leak into the next session (stacked ghost HUDs after server hops).
  `inputs.xml` actions must be referenced in `config.cpp class inputs` or `GetInputByName` returns null
  and crashes. (Not checked on `P:\`.)

Widgets worth knowing beyond the common ones:
- `ItemPreviewWidget` (`SetItem(EntityAI)/SetView(idx)/SetModelPosition/Orientation`) and
  `PlayerPreviewWidget` (`SetPlayer/UpdateItemInHands/Refresh/...`).
  `P:\scripts\3_game\gameplay.c:276-312`. Create via `GetWorkspace().CreateWidget(ItemPreviewWidgetTypeID, ...)`, then `SetItem` on
  a client-side object.
- `OnDraggingOver(Widget w, int x, int y, Widget reciever)` exists between OnDragging and OnDrop
  (`P:\scripts\1_core\proto\enwidgets.c:678`); it is in the event list of `script-recipes.md`.

Fonts (bitmap-atlas reality):
- Fonts are pre-baked bitmap atlases, one `.fnt`+`.edds` pair per size (`gui/fonts`: metron12/14/16/
  22/28/48/58, sdf_metronlight24/30/36/42/72, …; 119 `.fnt` files in `P:\gui\fonts` on 1.30). Layouts reference a specific size
  file (`font "gui/fonts/sdf_MetronLight42"`). You cannot request an arbitrary point size at runtime;
  a custom TTF must be converted in Workbench to `.fnt/.edds` per needed size. `"exact text" 1` pins
  rendering to the registered bitmap sizes; with it off, the engine scales the bitmap to any size.
  (The conversion and scaling behaviour is not checked on `P:\`.)
- Workbench has no way to register a custom widget font for a mod so its Layout Editor lists it —
  workaround: drop `.fnt` into `P:\gui\fonts` for preview, then hand-edit the mod's `.layout` font
  paths. `.fnt` files are not hand-editable atlas descriptors. (Workbench behaviour, not checked here.)

Imagesets:
- `.imageset` is plain-text, hand-editable — no Workbench needed to read/patch:
  `ImageSetClass { Name "<setname>" RefSize W H  Textures { ImageSetTextureClass { mpix N path
  "{GUID}Gui/imagesets/x.edds" } }  Images { ImageSetDefClass X { Name "X" Pos x y  Size w h
  Flags N } } }`. The `Name` on line 2 is what scripts use in `set:NAME image:IMG` — the filename is
  irrelevant. The `ImageSetClass` header: `P:\gui\imagesets\ccgui_enforce.imageset:1-10`
  (+ `ProgressMenuTileFull … Flags 3` at :4181-4186, tiling flag for segmented progress bars).
- Imagesets can be built without Workbench: `/dayz-build-imageset` packs PNG sprites into the
  `.imageset` and its atlas. The standalone **DayZ Imageset Editor** (v1.4, 2026-06) is a drag-drop
  atlas editor and compiler that also unpacks vanilla imagesets and exports element PNGs.
- `RichTextWidget` can embed imageset icons inline: `<image set="dayz_gui" name="icon_pin"/>` — mix
  text and icons (keybind hints) in one widget. (Not checked on `P:\`.)

---

## 8. Vanilla files and tools this file rests on

Vanilla ground truth on `P:\`: `P:\scripts\1_core\proto\enwidgets.c` and `dbgui.c` beside it,
`P:\scripts\3_game\tools\uimanager.c` and `uiscriptedmenu.c`, `P:\scripts\3_game\constants.c`,
`P:\scripts\3_game\gameplay.c`, `P:\scripts\3_game\gui\spacers\spacerbase.c`, `P:\gui\layouts\day_z_hud.layout`
and `loading.layout`, `P:\gui\imagesets\ccgui_enforce.imageset`, `P:\gui\fonts\`. Tooling:
`scripts/tools/dayz-script-validator/`, `scripts/tools/dayz-ui-lab/` and `scripts/tools/dayz-layout-viewer/`.

Three cautions when reading UI material outside this repo:

- Layout snippets written as XML (`<?xml?>` + `<Widget>/<Attribute>` tags) are the format that
  crashes native `CreateWidgets` (section 6.1). Never copy a layout snippet in that form, even from
  a tutorial whose script-side advice is sound.
- The Arma Reforger "Layout Creation" workflow describes the same early-Enfusion Layout Editor DayZ
  uses; confirm the exact editor menu path in the DayZ Tools Workbench itself.
- For signature lookups, read the vanilla scripts on `P:\scripts`. GitHub searches for "DayZ mod
  menu" surface cheat and malware template repos; never take UI code from them.
