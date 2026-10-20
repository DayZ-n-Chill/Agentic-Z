---
name: docs-sync
description: "Mirrors canonical agent, skill and doc files into the Docusaurus wiki at wiki/docs/: detects drift, applies the deterministic Docusaurus transform, and prunes orphan wiki pages. Use when you have edited .claude/agents/, a SKILL.md, docs/dayz-modding.md, docs/model-routing.md or the shared DayZ conventions, or when the Stop hook reports wiki drift."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`.

# /docs-sync

Keep `wiki/docs/` in sync with canonical sources. One pure-Python script, two modes:

1. **Drift detector** (`--check`, the default) lists what's out of sync: missing mirrors, sources newer than their mirror (by modification time), and orphan wiki pages. Wired to the Stop hook.
2. **Apply** (`--apply`) runs the deterministic Docusaurus transform in `apply.py`, writes every mirror whose content changed, and prunes orphan agent and skill pages.

## When to run it

- After editing any `.claude/agents/<name>.md` or `.claude/skills/<name>/SKILL.md`.
- After editing `docs/dayz-modding.md`, `docs/model-routing.md` or `.claude/skills/_shared/dayz-conventions.md`.
- After adding a new agent or skill (mirrors get created automatically).
- Whenever the Stop hook flags drift at the end of a session.

## How to run

**Just check what's out of sync** (no writes):

```cmd
python "<skill-dir>\sync.py" --check
```

**Apply the sync** (writes mirrors and prunes orphans):

```cmd
python "<skill-dir>\sync.py" --apply
```

**Preview what `--apply` would do** (changes nothing on disk, not even timestamps):

```cmd
python "<skill-dir>\sync.py" --apply --dry-run
```

## What gets synced

| Canonical | Wiki mirror |
|---|---|
| `.claude/agents/<name>.md` | `wiki/docs/agents/<name>.md` |
| `.claude/skills/<name>/SKILL.md` | `wiki/docs/skills/<name>.md` |
| `.claude/skills/_shared/dayz-conventions.md` | `wiki/docs/dayz-conventions.md` |
| `docs/dayz-modding.md` | `wiki/docs/dayz-modding.md` |
| `docs/model-routing.md` | `wiki/docs/model-routing.md` |

Other wiki pages (`intro.mdx`, `install.mdx`, `architecture.md` and so on) are hand-written and not touched. Within `wiki/docs/agents/` and `wiki/docs/skills/`, files starting with `_` and `about.md` are hand-written and never pruned.

The Docusaurus transform (`apply.py`):
- Skills: frontmatter trimmed to `name`; the description becomes an `## Overview` section.
- Agents: frontmatter trimmed to `name`, `model`, `color`, `memory`; a badge row is injected; `<example>` blocks in the description become styled example cards (`<commentary>` dropped).
- Bodies: HTML comments and literal MDX-breaking tags and curly braces outside code fences are escaped or stripped so MDX can render the page.
- Docs: copied as is.

## Stop hook integration

The drift detector (`sync.py --check`) is wired to Claude Code's Stop hook. When Claude finishes a response, if any canonical file changed without its wiki mirror being updated, you'll see a one-line notice:

```
docs-sync: 2 file(s) need wiki sync. Run /docs-sync.
```

The hook never auto-applies edits — you decide when to run the sync.
