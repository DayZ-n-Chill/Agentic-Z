---
name: clean-repo
---

## Overview

Wipe ALL template-managed artifacts across every domain so the repo is ready to push. Orchestrator — discovers and runs every domain's `&lt;domain&gt;-clean-workspace` skill in turn (currently just `dayz-clean-workspace`). Future domains plug in here automatically when they ship their own cleanup skill following the naming convention. Interactive confirmation by default; --yes skips it; --dry-run lists what each domain would clean.

# /clean-repo

Wipe everything the template's skills created across all domains so the repo is ready to push to git. This is the "nuke the workspace" button.

It's a thin orchestrator: it finds every `.claude/skills/<domain>-clean-workspace/` skill and invokes its `clean.py` with `--include-server --yes`. Each domain owns its own cleanup logic; this skill just runs them all.

Currently runs:

- `/dayz-clean-workspace` — DayZ scaffolds, junctions, deploy dirs, server staging.

Additional `<domain>-clean-workspace` skills plug in automatically when they follow the same convention.

## How to run

```cmd
python .claude\skills\clean-repo\clean.py [--yes] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `--yes` | no | Skip the interactive confirmation prompt. Required when stdin isn't a TTY. |
| `--dry-run` | no | Run each domain cleanup with `--dry-run` (lists what would be removed without removing anything). Always exits 0. |

Each child skill is invoked with `--include-server --yes` so the cleanup is unconditional and complete.

## Discovery

`clean-repo` scans `.claude/skills/` for any folder whose name ends with `-clean-workspace` and contains a `clean.py`. Folders starting with `_` (like `_shared/`) are skipped.

To add your new domain to the wipe: build a `<domain>-clean-workspace` skill that takes `--yes`, `--dry-run`, and `--include-server` flags. `clean-repo` picks it up automatically with no configuration here.

## Refuses to run if

- Stdin isn't a TTY and `--yes` wasn't passed.

It does **not** gate on `/dayz-preflight` — clean-repo is domain-agnostic. Each child cleanup gates on its own preflight as appropriate.

## Output

```
Will run 1 cleanup skill(s):
  /dayz-clean-workspace

Proceed? [y/N]: y

=== /dayz-clean-workspace ===
... (DayZ cleanup output) ...

[OK]    All cleanup skills completed.
```

`--dry-run` form passes `--dry-run` to each child so they list rather than remove.

## When to use this vs. a single domain cleanup

| Goal | Use |
|---|---|
| Wipe just one project's DayZ artifacts | `/dayz-clean-workspace --mod <Name>` |
| Wipe all DayZ artifacts (mods + server staging) | `/dayz-clean-workspace --include-server --yes` |
| Wipe everything across every domain (pre-push reset) | `/clean-repo --yes` |

## Do not

- Don't add domain-specific knowledge to this skill. Domain rules live in each `<domain>-clean-workspace` skill. This is pure orchestration.
- Don't pass extra flags to child skills beyond `--include-server --yes` (or `--dry-run` when in dry mode). Keep the contract simple — each cleanup runs at "wipe everything safely" mode.
- Don't gate on any specific domain's preflight. Each child skill gates itself if its domain requires environment setup; clean-repo stays out of that.
