---
name: agentic-z-update
description: Pulls the latest Agentic-Z template files (agents, skills, conventions, docs) from upstream into the current clone with a per-file three-way merge, leaving workspace/ mod work untouched, and commits the result. Refuses on uncommitted template changes unless --force. Use when the user asks to update Agentic-Z or pull template improvements, or when the SessionStart nudge reports that upstream is ahead.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`.

# /agentic-z-update

Pull template improvements (agents, skills, conventions, docs) from upstream `DayZ-n-Chill/Agentic-Z`'s `main` branch into the current clone. Three guarantees:

1. **`workspace/` mod work is never touched.** All changes are limited to template-managed paths.
2. **Local customizations to template files are not overwritten silently.** A per-file three-way merge detects when both the clone and upstream edited the same file and leaves it alone unless the user picks "take" in `--per-file` mode.
3. **No two updates can run at once.** A PID-based lock prevents concurrent invocations.

The first run in a clone records a baseline (the SHA of upstream `main` at that moment). Every later run compares the local file, the file at the baseline and upstream's current file to decide what to do per file.

## How to run

```cmd
python "<skill-dir>\update.py" [--check] [--quiet] [--yes] [--per-file] [--force] [--dry-run] [--no-sync]
```

## Flags

| Flag | Behavior |
|---|---|
| (default) | Preview drift, prompt y/N, apply safe changes (conflicts left alone) |
| `--check` | Preview only; exits 1 if changes pending, 0 if up to date |
| `--quiet` | With `--check`: single-line output for hooks |
| `--yes` | Skip the confirmation prompt (CI / scripted use) |
| `--per-file` | Walk each conflict interactively: keep / take / diff / skip |
| `--force` | Override the dirty-tree check |
| `--dry-run` | Show preview, do not apply |
| `--no-sync` | Skip the post-merge `sync-skills` run (useful when Claude Code is the only agent CLI in use) |

## Automatic commit

When at least one file is applied, the skill stages exactly the applied paths and creates one commit:

```
chore: pull Agentic-Z upstream (<first 8 chars of upstream SHA>)
```

It then records the upstream SHA in `.claude/.upstream-baseline`. If `git commit` fails (for example, a pre-commit hook rejects it), the changes stay staged and the skill prints a warning; nothing is rolled back. Unresolved conflicts are never part of the commit. Tell the user about this commit when reporting results.

## Per-file status meanings

| Status | What it means | Default action |
|---|---|---|
| `unchanged` | Local file matches upstream | nothing |
| `safe-overwrite` | Not edited locally, upstream changed it | apply upstream |
| `new` | New file from upstream | apply upstream |
| `local-only-edit` | Only the clone edited it (upstream unchanged) | leave alone |
| `conflict` | Both the clone and upstream edited it | leave alone (use `--per-file` to resolve) |
| `deleted-clean` | Upstream removed it, not customized locally | delete |
| `deleted-conflict` | Upstream removed it, customized locally | leave alone |

## What gets updated

Template-managed paths only:

```
.claude/agents/
.claude/skills/
.claude/mcp/
docs/
wiki/
scripts/
CLAUDE.md
AGENTS.md
GEMINI.md
README.md
```

What stays untouched:

```
workspace/                  # in-progress mods
output/                     # one-shot deliverables
.claude/local-memory/       # gitignored, per-clone notes
.claude/settings.local.json # local Claude Code settings
.env                        # gitignored API keys
```

## When to run

- After a new Agentic-Z release.
- When a new agent or skill has shipped upstream.
- Periodically (monthly is fine).

## When not to run

- Mid-merge or mid-rebase.
- With uncommitted changes to template files (it refuses; commit first, or pass `--force`).
- On a fork that has diverged heavily from upstream main (manual cherry-pick is safer).

## Files this skill creates

- `.claude/.upstream-baseline` — SHA of last upstream merge. Gitignored.
- `.claude/.upstream-update.lock` — concurrency lock during apply phase. Gitignored.

## SessionStart hook

A `SessionStart` hook runs `update.py --check --quiet` at the start of every Claude Code session in this repo. It prints a one-line nudge if upstream is ahead OR if a newer prebuilt search index is available. Silent on no-change. Configured in `.claude/settings.json`.

To disable temporarily: comment out the `SessionStart` block in `.claude/settings.json`.

## Search index notification

If `/dayz-search-download` was run before, this skill also checks whether the installed GitHub release of the search index has been superseded. The check is read-only and never downloads; it only suggests running `/dayz-search-download`.

To skip the check: ensure `~/.claude/dayz-search-index/release-tag.txt` doesn't exist (the check is silent when no installed tag is recorded).

## After updating

- Restart the agent CLIs (Claude Code, Codex, Gemini) so they pick up new agents and skills.
- Run `/dayz-preflight` to confirm the environment still works.

## Refuse rules (exit 1)

- Not a git repo: "Run from inside an Agentic-Z clone."
- Uncommitted changes in template paths (skipped with `--force`, and not checked by `--check`). Nothing is fetched or changed.
- The `upstream` remote points somewhere else: prints the `git remote set-url` fix.
- `git fetch` fails (with `--check --quiet` this exits 0 silently so the hook stays quiet).
- Non-interactive shell at the confirmation prompt without `--yes`.
