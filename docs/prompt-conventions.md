# Prompt conventions

Why agent and skill files in this repo look the way they do. Read this before writing or editing anything in `.claude/agents/` or `.claude/skills/`.

## TL;DR

- **Agent file shape** follows the lean standard in `.claude/agents/agent-creator.md` ("What a good agent file looks like"): frontmatter, a role sentence, then only the sections the role needs, with plain sentence-case headings.
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

## Agent file shape

The structure of an agent file is set by `agent-creator` (`.claude/agents/agent-creator.md`, section "What a good agent file looks like"). In short:

- Frontmatter: `name` and a third-person `description` that works as the delegation contract, with 1 to 3 short `<example>` blocks. Descriptions load into every session, so keep them short.
- Minimal `tools`; `memory: project` with no memory section in the body.
- Body: a role sentence, then only load-bearing sections (workflow, domain rules, constraints, handoffs, report), usually 10 to 60 lines.
- No `## NAME` heading and no PURPOSE / CAPABILITIES / INPUT / OUTPUT scaffolding. Use plain sentence-case headings such as `## Workflow` or `## Report`.
- Point at shared docs (`.claude/skills/_shared/...`) instead of pasting their rules.

Headings are for the reader, not the model; their case doesn't change behavior. The caps budget above applies to inline directives only.

## Quick checklist for writing a new agent or skill

1. Shape: match the `agent-creator` standard (role sentence, load-bearing sections only, references over inlining).
2. Inline caps: reserve `MUST` / `NEVER` / `ALWAYS` / `DO NOT` for actual hard rules. Apply the "remove the caps and re-read" test.
3. Default to lowercase prose. Trust the grammar.
4. If half the bullets in a section are capped, you've over-spent the signal — demote some to lowercase.
