# Model Routing — Match Model to Task

How agents in this template should pick a model for the work in front of them. The wrong choice burns latency or shallows the answer; the right choice does neither.

## The model ladder (Claude)

| Model | ID | Speed | Strength | Use for |
|---|---|---|---|---|
| **Haiku 4.5** | `claude-haiku-4-5-20251001` | Fastest | Light | Pure file-find, "where is X defined", trivial lookups (1 grep, no synthesis) |
| **Sonnet 4.6** | `claude-sonnet-4-6` | ~2–3× faster than Opus | Balanced | "Tell me about X / how does Y work" — research and synthesis across multiple sources |
| **Opus 4.7** | `claude-opus-4-7` | Slowest | Deepest reasoning | Coding, editing, planning, debugging, design decisions |

Other CLIs (Codex, Gemini) have analogous tiers — same principle applies even if model names differ.

## When to use each

**Decide by what the answer is, not by topic.**

- "Summarize what's already there" → search → **Sonnet subagent** (default), or **Haiku subagent** if it's a single grep.
- "Produce a change" (write/edit code, design, debug) → work → **main Opus thread**.
- Unsure? Default to Sonnet. The cost of mismatching down (Haiku for a depth question) is a thin answer the user has to re-ask. The cost of mismatching up (Opus for a lookup) is 30–60s of wasted latency.

## Why fan-out is the wrong default

Running searches inline on the main Opus thread costs:
- ~10–20s per tool result while Opus generates the next "thinking" block
- Multi-step search (3+ tool calls) → 30–60s of wall-clock for a sub-second lookup
- All search results land in main context, polluting it for the actual work

Dispatching to a subagent (`Agent` tool with `model: "sonnet"`) sidesteps both: the subagent runs searches at its own faster pace, summarizes, and returns one bounded result to the main thread.

## The pattern

```
Lookup / research / "tell me about X"
  → Agent(subagent_type: "Explore", model: "sonnet", prompt: "<bounded research prompt>")
  → returns summary; main thread synthesizes for the user

Trivial file-find / "where is X defined"
  → Agent(subagent_type: "Explore", model: "haiku", prompt: "<single grep prompt>")
  → returns path/line; main thread cites it

Coding / editing / debugging / design
  → main Opus thread, no dispatch
```

When dispatching, **bound the report**: word limit, file:line citations required, no padding. A summary in the main context is the goal — not raw tool output.

## Common mistakes

- **Opus for searches.** Slow + no extra value. The model isn't smarter at "find this file"; it's just slower at writing the response.
- **Haiku for design questions.** Fast but skips connections across files. Sonnet's synthesis is what makes "tell me about vehicles" usable.
- **Fanning out 3+ parallel searches inline.** Parallel doesn't help main-thread speed — main thread blocks on the slowest one, then has to write a long summary at Opus speed.
- **Duplicating the subagent's work in the main thread.** If you delegated search, trust the summary; don't re-run the searches.

## Reading more

- The agent-side rule lives in user memory: `feedback_route_searches_to_sonnet.md` (governs default behavior in every Claude Code session).
- L1 rule reference is in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`.
