---
name: sync-skills
---

## Overview

Sync this repo's `.claude/skills/` into each agent CLI's home `skills/` directory (Claude Code, Codex, Gemini, plus anything added to `agents.json` later) so all of them auto-discover the same slash commands. Idempotent. Refreshes mismatched links, prunes orphans, falls back from symlink to junction on Windows. Run this right after cloning the repo, and any time you add or remove a skill.

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`. For first-time bootstrap from a fresh clone (before any harness is loaded), use the literal repo-relative path: `python "<skill-dir>\sync.py"` from the repo root.

# /sync-skills

The bootstrap. **Links, not copies.** The single source of truth is `<repo>/.claude/skills/`; this skill creates symlinks (or junctions on Windows) in each agent CLI's home so every agent discovers the same slash commands. Nothing is copied, no skill content lives outside the repo, and editing a skill in the repo is instantly live in every agent.

The reason the agent home dirs are involved at all: Claude Code reads the repo's `.claude/skills/` directly, but Codex and Gemini only scan their own home dirs. The links bridge that gap without duplicating files.

## When to run it

- **Right after cloning the repo** — step two, before doing real work. None of the slash commands work in Codex or Gemini until this runs (Claude Code reads from the repo's `.claude/skills/` directly, but Codex and Gemini only read from their home dirs).
- **After adding a new skill** to `.claude/skills/`.
- **After deleting a skill** — orphan links pointing at the now-missing source get pruned.
- **After moving the repo** to a different path — mismatched links get refreshed.

## How to run

```cmd
python "<skill-dir>\sync.py"
```

Optional flags:

```cmd
python "<skill-dir>\sync.py" --agents claude codex     # subset
python "<skill-dir>\sync.py" --dry-run                 # preview, no writes
```

## Where the per-agent skills folders live

Resolved from `agents.json`. Defaults:

| Agent  | Env var(s) checked first                | Default path |
|--------|------------------------------------------|--------------|
| Claude | `CLAUDE_HOME`                           | `~/.claude/skills` |
| Codex  | `CODEX_HOME`                            | `~/.codex/skills`  |
| Gemini | `GEMINI_CLI_HOME` then `GEMINI_HOME`    | `~/.gemini/skills` |

To support a new agent later, append an entry to `.claude/skills/sync-skills/agents.json` — no code change needed.

## What it does, per skill, per agent

For every folder under `.claude/skills/<name>/` containing `SKILL.md` (folders starting with `_` like `_shared/` are skipped — they're helpers, not skills):

| Existing state in `<home>/skills/<name>` | Action |
|---|---|
| Link already points at the repo skill | `[OK]` no-op |
| Link points elsewhere (stale) | `[REFRESH]` retarget to the repo |
| Path doesn't exist | `[LINK]` create new link |
| Real folder, not a link | `[SKIP]` warn — don't clobber user-installed skills |
| Orphan link in target dir, points back into this repo at a path that's gone | `[PRUNE]` remove the link |

## Output

Plain text, one line per skill per agent, plus a summary:

```
Repo skills: 1  (G:\AI-Templates\.claude\skills)
  - sync-skills

[claude] C:\Users\...\.claude\skills
  [OK]      sync-skills

[codex] C:\Users\...\.codex\skills
  [LINK]    sync-skills  (junction)

...

Summary
    linked: 2
        ok: 1
 refreshed: 0
   skipped: 0
    pruned: 0
    failed: 0
```

Non-zero exit if any operation failed.

## Steps

1. Run `python "<skill-dir>\sync.py"` (no args = all agents).
2. Read the per-agent output. Confirm the skill counts match what's in `.claude/skills/`.
3. Reload each agent session so it picks up the new entries:
   - **Claude Code:** restart the CLI / reopen the chat.
   - **Codex:** restart.
   - **Gemini CLI:** `/skills reload`, then `/skills list` will show them.

## Do not

- Don't edit skills inside `<home>/skills/<name>/` — those are links into the repo. Edit them in `<repo>/.claude/skills/<name>/` and changes are live everywhere.
- Don't commit anything outside the repo. The agent home dirs are out-of-tree.
- Don't bother running with elevation just to get symlinks instead of junctions on Windows. They behave identically for skill discovery.
