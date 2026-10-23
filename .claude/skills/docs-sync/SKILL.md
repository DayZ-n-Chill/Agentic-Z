---
name: docs-sync
description: "Checks that the wiki in wiki/ matches the repo: every agent and skill is listed, nothing listed is gone, and the home page counts are right. Read only; it never edits the wiki. Use after adding, removing or renaming an agent or skill, or when the Stop hook reports a mismatch."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`.

# /docs-sync

The wiki in `wiki/` is written by hand. This skill checks it against the repo and reports where they disagree. It never writes to the wiki; you fix what it reports.

## When to run it

- After adding, removing or renaming an agent in `.claude/agents/` or a skill in `.claude/skills/`.
- After adding or removing a hook script in `hooks/`.
- Whenever the Stop hook reports a mismatch at the end of a session.

## How to run

```cmd
python "<skill-dir>\sync.py" --check
```

`--check` is the default, so `python "<skill-dir>\sync.py"` does the same. It needs only Python.

## What it checks

| Repo | Wiki |
|---|---|
| Every folder in `.claude/skills/` with a `SKILL.md` (folders starting with `_` are shared packs and skipped) | Named as `` `/<skill>` `` in the first column of `wiki/src/content/skills-table.md` |
| Every file in `.claude/agents/` | Named as `` `<agent>` `` in the first column of the "All agents" table in `wiki/src/content/guide.md`. One row can name several agents. |
| The counts of agents, skills and hook scripts (`hooks/*.py`, not tests) | The `agents`, `skills` and `hooks` numbers in `STATS` in `wiki/src/App.jsx` |

It reports both directions: something in the repo that the wiki leaves out, and something the wiki names that is no longer in the repo.

## Exit codes

| Code | Means |
|---|---|
| 0 | The wiki matches the repo, or `--quiet` was set (the Stop hook never fails a session). |
| 1 | `--check` found a mismatch. |
| 2 | Usage error, such as an unknown option. |

CI runs `sync.py --check` in `.github/workflows/tests.yml`, so a wiki that no longer matches the repo fails the build. Fix the wiki under `wiki/src/` and commit it.

## Stop hook integration

The check is wired to Claude Code's Stop hook in `.claude/settings.json` as `sync.py --check --quiet`. Claude Code only logs a command hook's plain stdout (to the debug log) when it exits 0; what it shows the user is a `systemMessage` field in JSON output. So under `--quiet` the script prints nothing when the wiki matches, and otherwise one JSON line, which appears as a notice when Claude finishes a response:

```
{"systemMessage": "docs-sync: 2 place(s) where the wiki and the repo disagree. Run /docs-sync."}
```
