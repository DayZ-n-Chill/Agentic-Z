---
name: docs-sync
description: Sync the Docusaurus wiki at `wiki/docs/` with the canonical sources (`.claude/agents/`, `.claude/skills/`, `docs/`, L1 files). Pure-Python: detects drift, applies the Docusaurus transform (frontmatter trim, agent badge HTML, example-block parser, MDX-tag escape), prunes orphan wiki pages whose canonical source was deleted.
---

# /docs-sync

Keep `wiki/docs/` in sync with canonical sources. One pure-Python script, two modes:

1. **Drift detector** (`--check`, fast, no LLM cost) — lists what's out of sync. Wired to the Stop hook.
2. **Apply** (`--apply`) — runs the deterministic Docusaurus transform and writes every mirror; prunes orphan wiki pages.

The transform used to live in a `docs-wiki-sync` agent that needed to be dispatched manually, so wiki updates rotted between dispatches. The transforms are deterministic, so they're now in `apply.py` and run from the same script as drift detection.

## When to run it

- After editing any `.claude/agents/<name>.md` or `.claude/skills/<name>/SKILL.md`.
- After editing `docs/*.md` or the L1 files (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
- After adding a new agent or skill (mirrors get created automatically).
- Whenever the Stop hook flags drift at the end of a session.

## How to run

**Just check what's out of sync** (no writes):

```cmd
python .claude\skills\docs-sync\sync.py --check
```

**Apply the sync** (writes mirrors and prunes orphans):

```cmd
python .claude\skills\docs-sync\sync.py --apply
```

**Preview what `--apply` would do** (no writes, no deletions):

```cmd
python .claude\skills\docs-sync\sync.py --apply --dry-run
```

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
docs-sync: 2 file(s) need wiki sync. Run `python .claude/skills/docs-sync/sync.py --apply` to update the wiki.
```

The hook never auto-applies edits — you decide when to run the sync.
