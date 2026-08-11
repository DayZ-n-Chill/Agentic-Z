---
name: agentic-z-update
---

## Overview

Pull the latest Agentic-Z template improvements (agents, skills, conventions, docs) from upstream into your clone, without touching your DayZ mod work in workspace/. Adds the upstream remote on first run, fetches, shows a changelog, then merges only template-managed paths. Re-runs sync-skills automatically. Refuses if your working tree is dirty unless --force is passed.

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`.

# /agentic-z-update

Pull template improvements (agents, skills, conventions, docs) from upstream `DayZ-n-Chill/Agentic-Z`'s `main` branch into your clone. Three guarantees:

1. **Your `workspace/` mod work is never touched.** Path scoping limits all changes to template-managed paths only.
2. **Your customizations to template files are not overwritten silently.** A three-way merge per file detects when both you and upstream edited the same file, and asks before doing anything destructive.
3. **No two updates can run at once.** A PID-based lock prevents concurrent invocations.

The first time you run this in a clone, it bootstraps the baseline (the SHA of upstream `main` at install time). From then on, every run compares (your local file) vs (the file at baseline) vs (upstream's current file) to decide what to do per file.

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
| `--no-sync` | Skip the post-merge `sync-skills` run (useful if you only use Claude Code) |

## Per-file status meanings

| Status | What it means | Default action |
|---|---|---|
| `unchanged` | Your file matches upstream | nothing |
| `safe-overwrite` | You didn't edit, upstream did | apply upstream |
| `new` | New file from upstream | apply upstream |
| `local-only-edit` | Only you edited it (upstream unchanged) | leave alone |
| `conflict` | Both you and upstream edited it | leave alone (use `--per-file` to resolve) |
| `deleted-clean` | Upstream removed it, you didn't customize | delete |
| `deleted-conflict` | Upstream removed it, you customized it | leave alone |

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
workspace/                  # your in-progress mods
output/                     # one-shot deliverables
.claude/local-memory/       # gitignored, per-clone notes
.claude/settings.local.json # your local Claude Code settings
.env                        # gitignored, your API keys
```

## When to run

- After a new Agentic-Z release.
- When you hear about a new agent or skill that you want.
- Periodically (monthly is fine).

## When NOT to run

- Mid-merge or mid-rebase.
- With uncommitted changes to template files (it'll refuse — commit first, or pass `--force`).
- On a fork that has diverged heavily from upstream main (manual cherry-pick is safer).

## Files this skill creates

- `.claude/.upstream-baseline` — SHA of last upstream merge. Gitignored.
- `.claude/.upstream-update.lock` — concurrency lock during apply phase. Gitignored.

## SessionStart hook

A `SessionStart` hook runs `update.py --check --quiet` at the start of every Claude Code session in this repo. It prints a one-line nudge if upstream is ahead OR if a newer prebuilt search index is available. Silent on no-change. Configured in `.claude/settings.json`.

To disable temporarily: comment out the `SessionStart` block in `.claude/settings.json`.

## Search index notification

If you previously ran `/dayz-search-download`, this skill ALSO checks whether the GitHub release you installed has been superseded. The check is read-only — it never auto-downloads (the index is ~200MB). Just nudges you to run `/dayz-search-download` when a newer release ships.

To skip the check: ensure `~/.claude/dayz-search-index/release-tag.txt` doesn't exist (the check is silent when no installed tag is recorded).

## After updating

- Restart your agent CLIs (Claude Code, Codex, Gemini) so they pick up the new agents/skills.
- Run `/dayz-preflight` to verify your environment still works.

## Refuse rules

- Not a git repo → fail with "run from inside an Agentic-Z clone."
- Working tree has uncommitted changes in template paths → fail unless `--force`.
- Upstream remote exists but points elsewhere → fail with instructions to fix.
- Network failure on `git fetch` → fail with the underlying error.
