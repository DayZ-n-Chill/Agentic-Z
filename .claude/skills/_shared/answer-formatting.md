# Formatting answers grounded in vanilla source

When answering a DayZ question (especially RAG-grounded ones), use the full markdown surface Claude Code renders so the answer is scannable at a glance, not a wall of prose. Tier 3 pack; Tier 2 (`dayz-conventions.md`) points here. Defaults that apply to every DayZ agent and skill:

- **Inline code for every identifier.** Class names (`PlayerBase`), method names (`OnBleedingBegin()`), file paths (`P:\scripts\3_game\dayzgame.c`), constants (`TICK_INTERVAL_SEC`), and field names (`m_BleedingBits`) all go in backticks. Bare prose names disappear in monospace; backticks make them pop.
- **Fenced code blocks for snippets, with language tags.** Use ` ```c ` for Enforce Script, ` ```cpp ` for `config.cpp`, ` ```xml ` for `types.xml`/economy files, ` ```json ` for `cfggameplay.json`. Even short 2-3 line excerpts go in a fence — syntax highlight + visual separation is the win.
- **Tables for multi-class / multi-field summaries.** When explaining a system that spans 2+ classes (e.g. `BleedingSourcesManagerBase` / `Server` / `Remote`), put their roles, key methods, and side in a table rather than three paragraphs. Same for damage-zone enumerations, inventory slot lists, gameplay-effect-widget types.
- **Numbered lists for flow.** "Damage hits → server adds bit → bit syncs → client spawns particle" is a flow, not a paragraph. Number each step. Readers can map cause/effect immediately.
- **Headers for major sections.** `##` for the top-level subject, `###` for subsystems within. Don't over-section; 3-5 headers in a normal-sized answer is the ceiling.
- **Cite `path:line_start-line_end`** inline (already required by Tier 2's cite-then-verify rule) — this also doubles as visual anchoring.
- **Don't paraphrase the snippet block.** The MCP tool result already shows the user the raw snippets. The follow-up answer should synthesize, contrast, or explain — not restate. Brief synthesis only.

What not to use: colors (not rendered), images (not rendered), HTML (escaped), collapsible sections (not supported), ANSI escapes (not supported). Stick to CommonMark + GFM.

This rule applies regardless of which DayZ agent is answering — script-specialist, ui-specialist, server-admin, debugger, reviewer, all of them.
