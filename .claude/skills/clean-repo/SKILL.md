---
name: clean-repo
description: "Removes every template-managed artifact across all domains by running each domain's clean-workspace skill after one combined dry run and prompt. Use when the user wants a full pre-push reset; for one domain or one mod, use that domain's cleanup skill instead."
argument-hint: "[--yes] [--dry-run]"
disable-model-invocation: true
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`.

# /clean-repo

Remove everything the template's skills created, across all domains, so the repo is ready to push.

This is a thin orchestrator. It finds every `.claude/skills/<domain>-clean-workspace/` skill and runs its `clean.py`. Each domain owns its own cleanup logic. Today that is only `/dayz-clean-workspace` (DayZ scaffolds, junctions, deploy dirs and server staging).

## How to run

```cmd
python "<skill-dir>\clean.py" [--yes] [--dry-run]
```

| Argument | Notes |
|---|---|
| `--yes` | Skip the confirmation prompt. Required when stdin isn't a TTY. |
| `--dry-run` | Show the combined plan and stop without removing anything. |

### From an agent shell

The agent's shell is not a TTY, so the script cannot prompt there. Ask in chat instead:

1. Run `python "<skill-dir>\clean.py" --dry-run`.
2. Show the user the combined plan it printed.
3. Ask in chat whether to remove everything listed. Stop if they do not clearly say yes.
4. On a yes, run `python "<skill-dir>\clean.py" --yes`.

## What it does

1. Without `--dry-run` or `--yes`, refuses (exit 2) if stdin isn't a TTY, before running anything.
2. Runs each child with `--include-server --dry-run` and prints the output under a `=== /<skill> (--dry-run) ===` header. That output is the combined plan. If any child's dry run fails, stops with exit 1 and removes nothing.
3. With `--dry-run`, stops here with exit 0.
4. Asks once, `Remove everything listed above? [y/N]`, unless `--yes` was passed. Any answer other than `y` or `yes` aborts with exit 0.
5. Runs each child with `--include-server --yes` under a `=== /<skill> (--yes) ===` header. Exits 1 if any child failed, 0 otherwise.

It does not gate on `/dayz-preflight`, because it is domain-agnostic. Each child gates on its own preflight.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Completed, dry run completed, user aborted, or no cleanup skills found |
| 1 | A child's dry run or cleanup failed |
| 2 | Not a TTY and `--yes` not passed |

## Discovery

Any folder in `.claude/skills/` whose name ends in `-clean-workspace` and contains `clean.py` is picked up. Folders starting with `_` are skipped. A new domain plugs in by shipping a `<domain>-clean-workspace` skill that accepts `--include-server`, `--dry-run` and `--yes`.

## When to use this vs. a single domain cleanup

| Goal | Use |
|---|---|
| Remove one mod's DayZ artifacts | `/dayz-clean-workspace --mod <Name>` |
| Remove all DayZ artifacts (mods and server staging) | `/dayz-clean-workspace --include-server` |
| Remove everything across every domain before a push | `/clean-repo` |
