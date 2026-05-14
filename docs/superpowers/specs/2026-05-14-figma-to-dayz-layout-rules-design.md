# Figma to DayZ `.layout` Rules — Design

**Date:** 2026-05-14
**Branch:** feature/figma-to-dayz-agents
**Status:** Brainstorm spec, awaiting user review before implementation plan

## Problem

The three agents shipped in commit 05e01a5 (`figma-node-normalizer`, `figma-to-dayz-layout`, `dayz-layout-validator`) are built on a wrong premise: they treat DayZ `.layout` files as XML with PascalCase tags and HTML-style attributes.

The actual format, documented in `.claude/skills/_shared/enscript/references/gui_layout.md` and visible in every vanilla layout under `P:\gui\` (and the in-repo example `enscript/examples/11_hud_plain_text.layout`), is a custom **property-file format**:

```
FrameWidgetClass HudOverlay {
 position 0 0
 size 1 1
 hexactpos 0
 vexactpos 0
 {
  TextWidgetClass LabelMain {
   text "Status: OK"
   "exact text" 1
   "text halign" right
  }
 }
}
```

Not:

```xml
<WrapSpacerWidget orientation="vertical">
    <TextWidget />
</WrapSpacerWidget>
```

Workbench rejects every file the current `figma-to-dayz-layout` agent produces. The downstream `dayz-layout-validator` operates as an XML cleaner and would have to be rewritten to even diagnose the problem.

## Solution shape

Two-phase fix.

**Phase 1 (this spec, then implementation):** Author a single shared rules document at `.claude/skills/_shared/figma-to-dayz-rules.md`. Same `_shared/` folder pattern already used by `dayz-conventions.md` and `enscript-style.md`. This doc is the source of truth for everything Figma-to-DayZ.

**Phase 2 (follow-up implementation):** Surgically patch the three agents to reference the rules doc and correct their inline format claims. No agent duplicates the rules; they cite.

## Phase 1 deliverable: `figma-to-dayz-rules.md`

Section outline:

1. **The format is not XML.** Opening warning. Show the property-file shape (one widget block with properties + nested child block). Two-line rule: "Class names end in `Class`. Properties are bare key-value pairs, never `=`, never quoted attributes."

2. **Format cheat sheet (inline).** Six to ten lines: how a widget block looks, how properties work, how multi-word keys are quoted, how the child `{ }` block goes inside the parent's braces after all properties. Point at `enscript/references/gui_layout.md` for the exhaustive widget catalog and property reference.

3. **Figma to DayZ widget mapping.** Single table. Corrects the existing agent's mapping by appending `Class` to every widget name and adding widgets the current agent missed (`EditBoxWidgetClass`, `CheckBoxWidgetClass`, `SliderWidgetClass`, `XComboBoxWidgetClass`, `ProgressBarWidgetClass`, `RichTextWidgetClass`, `MultilineTextWidgetClass`, `ItemPreviewWidgetClass`, `PlayerPreviewWidgetClass`).

4. **Naming prefix taxonomy.** Extends the existing `btn_`/`txt_`/`img_`/`list_`/`grid_`/`modal_` set with form inputs: `edit_` (EditBox), `check_` (CheckBox), `slider_` (Slider), `drop_` (XComboBox), `bar_` (ProgressBar), `preview_` (ItemPreview or PlayerPreview, disambiguated by content). Used to break ties when a Figma layer kind is generic.

5. **Auto layout translation.** Figma vertical/horizontal auto layout maps to `WrapSpacerWidgetClass`. Repeating-grid frames map to `GridSpacerWidgetClass`. Scrollable frames map to `ScrollWidgetClass`. Critical note: DayZ has no flexbox, so children do not carry layout attributes. The spacer widget configures the layout via its own properties, and children just sit inside it. Implementation must verify the exact orientation/sizing properties against vanilla via the dayz-rag MCP before authoring.

6. **Coordinate translation.** Figma pixels are absolute. DayZ uses position/size pairs together with `hexactpos`/`vexactpos`/`hexactsize`/`vexactsize` toggles (0 = relative 0..1 fraction of parent, 1 = pixel). Rule of thumb: relative for full-area containers and proportional regions, pixel for fixed-size buttons, icons, and labels. Never emit a position without its matching toggle.

7. **Color translation.** Figma hex / RGB / RGBA to DayZ space-separated floats `R G B A` in 0..1. Worked example: `#FF5050` at 80% alpha becomes `color 1 0.314 0.314 0.8`. Never emit hex strings, CSS rgba(), or 0..255 ints.

8. **Font translation.** Default Figma-to-DayZ font mapping table targeting the SDF fonts shipped in vanilla (`gui/fonts/sdf_MetronBook24`, `sdf_MetronLight24`, `sdf_MetronBook72`, etc.). Pair with `"exact text" 1` + `"exact text size" N` to control pixel size independently of the font's name suffix.

9. **Hard NO list.** Surface-level red flags that mean the output is wrong, used by both the generator (to avoid) and the validator (to remove):
   - XML tags (`<…>`, `</…>`, `/>`)
   - `=` between key and value
   - Quoted attribute values (`name="foo"`)
   - Semicolons as line terminators
   - CSS-style properties (`borderRadius`, `display`, `flex`, `justifyContent`, `alignItems`, `boxShadow`, `padding`, `margin`)
   - Opacity as percentage (`opacity: 0.8` or `80%`). DayZ uses the alpha channel inside the `color` property.

10. **Worked example.** A small Figma frame description (status HUD with title + value text), the normalized JSON the normalizer would emit, and the corresponding `.layout` output in the correct property-file format. Three-stage view so future readers can trace every transformation.

## Phase 2: agent patches (not authored in Phase 1)

After the rules doc lands and Brian reviews it, the three agents are patched:

- **`figma-node-normalizer`** — small. The closing handoff line currently says "ready for figma-to-dayz-layout to convert into `.layout` XML." Drop "XML." Add a one-line reference to the rules doc so the agent knows what the downstream format looks like (avoids producing JSON shapes the generator cannot consume).

- **`figma-to-dayz-layout`** — major. Strip every XML-shaped example. Replace the GOOD / BAD pattern blocks with property-file equivalents. Update the widget mapping table to use `*WidgetClass` suffixes. Add a prominent "see `figma-to-dayz-rules.md` for the canonical translation rules" pointer near the top. Keep the workflow steps and the Figma-MCP interaction logic, those are correct.

- **`dayz-layout-validator`** — medium. Replace XML-parser language ("every opening tag must close", "well-formed", "mismatched openers / closers", "single root") with property-file equivalents ("every widget block has matching braces", "child block is nested inside the parent's braces", "root is one top-level widget"). Keep the cite-against-vanilla principle. Keep the CSS-attribute-removal list, expand it from the Hard NO list in the rules doc.

## Open questions / risks to resolve at implementation time

- **WrapSpacerWidget orientation mechanism.** The `gui_layout.md` reference does not document how vertical vs horizontal is set on `WrapSpacerWidgetClass`. Implementation MUST verify against vanilla via dayz-rag (`search_dayz_source` with `file_type="layout"`) before authoring section 5 of the rules doc.
- **GridSpacerWidget configuration.** Same as above. Need to confirm the cell-size, columns, and spacing properties from vanilla.
- **Color tokens via Figma variables.** If a Figma file uses variables for color tokens, the normalizer can resolve them with `get_variable_defs`. Whether the rules doc prescribes a Figma-token-to-DayZ-theme mapping is deferred to a Phase 3 if the need arises.

## Out of scope

- Widget script (`.c`) authoring. Owned by `dayz-ui-specialist` downstream.
- Anchor and alignment polish beyond what the prefix taxonomy and coordinate rules cover.
- Workbench-side visual validation. The rules ensure the file opens; pixel fidelity is a human-in-the-loop step.
- Figma write APIs and Code Connect mapping. The pipeline is read-only on the Figma side.
- Any change to `enscript/references/gui_layout.md`. That file is correct and stays the catalog.

## Success criteria

- A new `figma-to-dayz-layout` run produces a `.layout` file that opens in Workbench without rejection.
- `dayz-layout-validator` recognizes the property-file format and can strip CSS-isms without rewriting good content.
- A worked example in the rules doc round-trips: Figma frame description, normalized JSON, valid `.layout` output, all matching one another's structure.
- The three agents do not redundantly redefine format rules; each one cites `figma-to-dayz-rules.md`.
