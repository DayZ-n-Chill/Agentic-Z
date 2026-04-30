# Prompt conventions

Why agent and skill files in this repo look the way they do. Read this before writing or editing anything in `.claude/agents/` or `.claude/skills/`.

## TL;DR

- **Uppercase section headers** (`## NAME`, `## ROLE`, `## CONSTRAINTS`) are structural — for tooling and scannability, not for the model.
- **Inline caps directives** (`MUST`, `NEVER`, `ALWAYS`, `DO NOT`, `CRITICAL`) are behavioral — they measurably increase model compliance, but only when used sparingly.
- **Lowercase prose for everything else.** Caps are a finite signal; spending them on decoration burns the budget you need for real rules.

## Why caps directives work

Capitalized directives like `MUST`, `MUST NOT`, `SHALL`, `SHOULD`, and `MAY` come from **RFC 2119**, the IETF's "Key words for use in RFCs to Indicate Requirement Levels." That convention is everywhere in the training data: protocol specs, security standards, API contracts, compliance docs. Whenever a document needed an unambiguous rule that a reader couldn't talk themselves out of, the author capitalized the verb.

LLMs have absorbed that pattern. Anthropic's own prompting guide explicitly recommends using caps for critical instructions, and in practice:

- *"you must not delete files"* — gets rationalized away ("the user clearly wants this resolved, deleting seems necessary…")
- *"you MUST NOT delete files"* — held to as a hard rule

Same words, measurably different compliance rates. This is real, not folklore.

## Why caps work *only when rare*

Caps function as a salience boost. The boost exists **because most surrounding text is lowercase** — caps stand out against the baseline. If a file is wall-to-wall `EVERY AGENT MUST ALWAYS DO X AND NEVER DO Y`, the model treats that as the author's normal voice and the emphasis evaporates. You end up with noisy prose AND no compliance lift — worst of both.

The signal is finite. Spend it on rules that, if violated, would mean the agent failed its job.

## How to decide whether to cap something

Apply this test to any directive you're tempted to capitalize:

> If I remove the caps and read the sentence aloud, does it still feel like an absolute rule?

- **Yes** → leave it lowercase. The grammar already carries the weight.
- **No, removing the caps would let the model rationalize an exception** → keep it capped.

Examples from the existing agents that pass the test:

- `DO NOT write fixes yourself` (mod-reviewer's whole identity is "audit, don't fix" — without caps the model would slip into fixing)
- `NEVER on params/returns/locals/typedefs` (a hard EnScript rule with no exceptions)
- `MUST conform to the style guide` (non-negotiable, blocks the work otherwise)

Examples that would *fail* the test (and should stay lowercase):

- `you must read the file before editing` — already enforced by tooling, no rationalization risk
- `you should always be helpful` — vague, not actionable, no specific failure mode
- `IMPORTANT: this is a tip about formatting` — decoration; the word "tip" already framed it

## Section headers — different rule

Section headers (`## NAME`, `## ROLE`, `## CAPABILITIES`, `## CONSTRAINTS`, `## EXAMPLES`) are uppercase by convention but for a different reason: the `agent-creator` skill validates the template structure, and consistent caps make sections greppable and visually distinct from inline content. Doesn't change model behavior — could be lowercase and nothing would break.

If you're authoring a new agent, follow the existing template exactly (uppercase headers, no trailing colons, blank line after each heading). The structural rules are enforced by `agent-creator`; deviating from them just makes the file fail validation.

## Quick checklist for writing a new agent or skill

1. Section headers: uppercase `## NAME`, `## ROLE`, etc. — match the existing template.
2. Inline caps: reserve `MUST` / `NEVER` / `ALWAYS` / `DO NOT` for actual hard rules. Apply the "remove the caps and re-read" test.
3. Default to lowercase prose. Trust the grammar.
4. If half the bullets in a section are capped, you've over-spent the signal — demote some to lowercase.
