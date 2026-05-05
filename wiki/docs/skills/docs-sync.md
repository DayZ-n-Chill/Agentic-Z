---
name: docs-sync
---

# /docs-sync

Keep `wiki/docs/` in sync with canonical sources. Two layers:

1. **Drift detector** (Python, fast, no LLM cost) — lists what's out of sync.
2. **Sync agent** (`docs-wiki-sync`, model: sonnet by default) — applies the Docusaurus transform and writes updates.

## When to run it

- After editing any `.claude/agents/<name>.md` or `.claude/skills/<name>/SKILL.md`.
- After editing `docs/*.md` or the L1 files (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
- After adding a new agent or skill (mirrors get created and tables updated).
- Whenever the Stop hook flags drift at the end of a session.

## How to run

**Just check what's out of sync** (no writes):

```cmd
python .claude\skills\docs-sync\sync.py --check
```

**Apply the sync** (invokes the `docs-wiki-sync` agent):

Tell Claude Code: *"Run the docs-wiki-sync agent."* The agent reads the drift report, applies the Docusaurus transform, and writes the updated wiki files.

## Model selection

The agent defaults to **sonnet** — fast and accurate for routine sync work. Override when needed:

- **opus** — large rewrites, complex prose synthesis, or you want maximum quality.
- **haiku** — purely mechanical 1:1 file mirror with no judgement calls.

Tell the agent: *"Use opus for this sync"* or *"use haiku, just mirror the files"*. You can always ask for a different model — the default is the recommendation, not a constraint.

## What gets synced

| Canonical | Wiki mirror |
|---|---|
| `.claude/agents/<name>.md` | `wiki/docs/agents/<name>.md` |
| `.claude/skills/<name>/SKILL.md` | `wiki/docs/skills/<name>.md` |
| `.claude/skills/_shared/dayz-conventions.md` | `wiki/docs/dayz-conventions.md` |
| `docs/dayz-modding.md` | `wiki/docs/dayz-modding.md` |
| `docs/model-routing.md` | `wiki/docs/model-routing.md` |
| Agents/skills tables in `docs/README.md` | Tables in `wiki/docs/intro.md` |

The Docusaurus transform applied during sync:
- Reduces frontmatter to fields Docusaurus uses (`name`, `model`, `color`, `memory`).
- HTML-escapes `<example>` / `<commentary>` blocks so MDX doesn't try to render them as components.
- Injects badge rows for agents.

## Stop hook integration

The drift detector (`sync.py --check`) is wired to Claude Code's Stop hook. After each session, if any canonical file changed without its wiki mirror being updated, you'll see a one-line notice:

```
docs-sync: 2 file(s) need wiki sync. Run /docs-sync.
```

The hook never auto-applies edits — you decide when to run the sync.
