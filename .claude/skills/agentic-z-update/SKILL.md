---
name: agentic-z-update
description: Pull the latest Agentic-Z template improvements (agents, skills, conventions, docs) from upstream into your clone, without touching your DayZ mod work in workspace/. Adds the upstream remote on first run, fetches, shows a changelog, then merges only template-managed paths. Re-runs sync-skills automatically. Refuses if your working tree is dirty unless --force is passed.
---

# /agentic-z-update

Pull infrastructure updates from `https://github.com/DayZ-n-Chill/Agentic-Z` into your clone. Agents, skills, L1 docs, L2 conventions, scripts. Your `workspace/<ModName>/`, `output/`, `.claude/local-memory/`, and any settings you've changed locally are left alone.

## When to run

- After a new Agentic-Z release.
- When you hear about a new agent or skill that you want.
- Periodically (monthly is fine).

## When NOT to run

- Mid-merge or mid-rebase.
- With uncommitted changes to template files (it'll refuse — commit first).
- On a fork that has diverged heavily from upstream main (manual cherry-pick is safer).

## How to run

```cmd
python .claude\skills\agentic-z-update\update.py [--force] [--dry-run] [--no-sync]
```

| Argument | Required? | Notes |
|---|---|---|
| `--force` | no | Skip the dirty-tree check. Risky — uncommitted edits in template paths may be clobbered. |
| `--dry-run` | no | Show what would change (commit log + file list) without merging or running sync-skills. |
| `--no-sync` | no | Skip the post-merge `/sync-skills` re-run. Useful if you only use Claude Code. |

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

## Steps performed

1. Verify the current directory is a git repo.
2. Verify the working tree is clean (`--force` overrides this).
3. Add `https://github.com/DayZ-n-Chill/Agentic-Z.git` as the `upstream` remote if missing.
4. Fetch `upstream/main`.
5. Show commit log: `upstream/main` since the merge-base with your current branch.
6. Merge only the template paths via `git checkout upstream/main -- <paths>`. Your branch's HEAD doesn't change; only the working-tree files in those paths get updated.
7. Stage the result and create a single commit `chore: pull Agentic-Z upstream (<short-sha>)`.
8. Re-run `/sync-skills` so any new skills get linked into Codex/Gemini home dirs.
9. Print a summary: files changed, commits pulled, next-step suggestions.

## Conflict handling

If a template file has been modified locally and ALSO modified upstream, the merge fails for that file. The skill:

- Reports the conflicted path.
- Leaves your local version untouched.
- Continues merging non-conflicted paths.
- Prints the list of skipped files at the end so you can resolve manually.

You can resolve a single file by running:

```cmd
git checkout upstream/main -- <path>      # take upstream version
git checkout HEAD -- <path>               # take your version
git diff upstream/main HEAD -- <path>     # see the difference
```

## After updating

- Restart your agent CLIs (Claude Code, Codex, Gemini) so they pick up the new agents/skills.
- Run `/dayz-preflight` to verify your environment still works.
- Read `git log -p` on the merge commit if you want to see what changed.

## Refuse rules

- Not a git repo → fail with "run from inside an Agentic-Z clone."
- Working tree has uncommitted changes in template paths → fail unless `--force`.
- Upstream remote exists but points elsewhere → fail with instructions to fix.
- Network failure on `git fetch` → fail with the underlying error.
