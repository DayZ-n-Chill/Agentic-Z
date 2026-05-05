# Agentic-Z update — design

**Date:** 2026-05-05
**Author:** brainstorm with Brian (DayZ n' Chill)
**Status:** spec — ready for review before writing-plans

## Goal

Make `/agentic-z-update` safe enough that users can run it without losing their customizations, and visible enough that they know when an update is available without polling manually. Cover both:

1. **Template updates** (agents, skills, conventions, docs) pulled from upstream `DayZ-n-Chill/Agentic-Z` `main`.
2. **Prebuilt search-index updates** published as GitHub release assets.

Out of scope: auto-applying anything destructive without explicit user confirmation.

## Background

Today `/agentic-z-update` works by hard-overwriting template paths via `git checkout upstream/main -- <path>`. That blows away any local customization to a template file (e.g. someone added personal notes to `dayz-script-specialist.md`). There is no notification when upstream is ahead. The user has to remember to run the command. Path-based scoping already protects `workspace/`, `output/`, `.claude/local-memory/`, etc. — that part stays.

## Architecture

Two pieces, deliberately separate:

| Piece | What it does | When it runs |
|---|---|---|
| **A. Smart update command** | Three-way merge per template file with conflict detection and per-file confirm | Manually via `/agentic-z-update` |
| **B. Notification hook** | Quiet check on session start, prints a one-liner if upstream is ahead | Automatic via Claude Code `SessionStart` hook |

A is the safety mechanism. B is the visibility mechanism. They share the underlying drift detection but have different I/O surfaces.

## A. Smart update command

### Three-way classification

For each file in the template-managed paths, compare three blobs:

- **`baseline`** — the file at the SHA the user last successfully merged from upstream
- **`local`** — the file currently on disk in the user's clone
- **`upstream`** — the file at upstream `main`'s tip

The `baseline` SHA is stored at `.claude/.upstream-baseline` (one line, gitignored, per-clone). On first run with no baseline, treat the entire current state as the baseline (no warnings).

Classification table:

| local vs baseline | upstream vs baseline | local vs upstream | Status | Action |
|---|---|---|---|---|
| same | same | same | `unchanged` | no-op |
| same | different | different | `safe-overwrite` | apply upstream |
| missing | exists | exists | `new` | apply upstream |
| different | same | different | `local-only-edit` | leave alone |
| different | different | different | `conflict` | flag, ask user |
| same | missing | missing | `deleted-clean` | delete |
| different | missing | exists | `deleted-conflict` | flag, ask user |
| missing | missing | missing | n/a | skip |

### Preview output

```
Agentic-Z update preview (upstream main: a4b8c12, baseline: 6a0f7e5)

  Template files: 14 changed
    safe to apply:        11 files
    new files added:       2 files
    deletions (clean):     1 file
  Conflicts (need your call): 2 files
    .claude/agents/dayz-script-specialist.md
      ▸ both you and upstream edited this since baseline
      ▸ keep mine / take upstream / show diff
    .claude/skills/_shared/dayz-conventions.md
      ▸ same kind of conflict

  Search index: newer prebuilt available (you have v0.1.0, latest v0.2.0)
                Run /dayz-search-download to fetch separately.

  Apply 14 file changes? (y/n/per-file)
```

User responses:

- `y` — apply the safe-to-apply / new / deletions; LEAVE conflicts alone (user must resolve manually before next update).
- `n` — abort, no changes.
- `per-file` — interactive picker walks each conflict: keep / take / diff / skip.

### CLI flags

| Flag | Behavior |
|---|---|
| (default) | Preview, prompt, apply |
| `--check` | Preview only, exit 1 if changes pending, exit 0 if up to date |
| `--quiet` | Pair with `--check`; prints one line on drift, silent on no-change. Used by the SessionStart hook. |
| `--yes` | Skip the confirm prompt (CI / scripted) |
| `--per-file` | Interactive picker for conflicts (instead of just-apply-non-conflicts behavior) |
| `--force` | Override the dirty-tree check (existing) |
| `--no-sync` | Skip post-merge `sync-skills` run (existing) |

### Lock file

`.claude/.upstream-update.lock` (gitignored). Created at start of `--yes` or interactive apply, deleted at end. Contains:

```json
{ "pid": 12345, "started_at": "2026-05-05T14:23:00Z" }
```

If a second `agentic-z-update` invocation finds a lock:

- **If `pid` is still alive** → refuse, regardless of lock age: `"Another update is running (PID 12345, started Ns ago). If you're sure it's stuck, delete .claude/.upstream-update.lock"`. A long merge with many conflicts can legitimately take >5 min; we never overlap with a live process.
- **If `pid` is dead** → treat as stale (the previous run crashed before releasing). Overwrite the lock and proceed. The 5-min age threshold is no longer used; PID liveness is the single source of truth.

The hook (`--check --quiet`) does NOT take the lock — it's read-only.

### Atomic baseline write

Baseline file written via temp file + rename so partial write can't corrupt:

```python
tmp = baseline_path.with_suffix(".tmp")
tmp.write_text(new_sha)
tmp.replace(baseline_path)
```

## B. Session-start notification hook

Wired in `.claude/settings.json`:

```json
"hooks": {
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python \"$CLAUDE_PROJECT_DIR/.claude/skills/agentic-z-update/update.py\" --check --quiet",
          "timeout": 10
        }
      ]
    }
  ]
}
```

Output:
- Up to date → silent (exit 0)
- Behind → one line: `agentic-z: 7 new template commits + new search index v0.2.0 available. Run /agentic-z-update.`
- Network error → silent (timeout 10s, fail open)

Cost: one shallow `git fetch upstream` + a few `git rev-parse` calls + one HTTPS call to GitHub Releases API. ~50-200ms when warm, ~1s when cold.

## Search index update check

`/agentic-z-update` and the SessionStart hook also surface prebuilt-index availability.

### Detection

1. Read local `~/.claude/dayz-search-index/release-tag.txt` (single line, written by `dayz-search-download` after a successful download). If absent, skip the check — user built the index locally or never installed.
2. Hit `GET https://api.github.com/repos/DayZ-n-Chill/Agentic-Z/releases/latest`.
3. Find the asset matching the `dayz-search-index-*.tar.gz` prefix; extract its tag.
4. If GitHub tag != local tag (and looks newer per a simple SemVer comparison) → flag in the preview / hook nudge.

### Important

`/agentic-z-update` does NOT auto-download the index. It's ~200MB and the user might be on metered. The notification just tells them `/dayz-search-download` is the command to run. They run it explicitly.

### Edge cases

- `release-tag.txt` missing (built locally instead of downloaded) → skip check silently
- Offline / GitHub rate-limited → skip silently in hook, warn but continue in `/agentic-z-update --check`
- Local tag newer than latest release → don't suggest downgrade

## Storage and gitignore

| Path | Purpose | Gitignored? |
|---|---|---|
| `.claude/.upstream-baseline` | Last-pulled upstream SHA | yes — added by this PR |
| `.claude/.upstream-update.lock` | Concurrency lock | yes — added by this PR |
| `~/.claude/dayz-search-index/release-tag.txt` | Written by `dayz-search-download` after install (already exists today). The auto-update command reads it to check for newer releases. | n/a (lives outside repo) |

## Edge cases (not yet covered above)

| Case | Behavior |
|---|---|
| Fresh clone, no baseline file | First `--check` quietly initializes baseline = current upstream HEAD. No notification on the very first session. |
| `upstream` remote not yet added | `--check` adds it silently (matches current `ensure_upstream` behavior) |
| User on a fork with diverged branch | Compare against `upstream/main`, not the user's local branch. User's commits don't pollute the comparison. |
| User offline | `git fetch` fails → hook silently passes (timeout 10s). Don't spam errors at session start. |
| Conflict in 5+ files | Print `5 conflicts. Run /agentic-z-update --per-file to resolve.` Don't dump 5 diffs in the hook output. |
| Binary files (e.g. images in `wiki/static/img/`) | Treat as opaque blobs. "conflict" if both diverged. Per-file picker offers keep / take, no diff. |
| User created a NEW agent locally with same name as a NEW upstream agent | Both "new" branch — flag as conflict, user picks which one wins. |
| Stale baseline (someone hand-edited it, SHA isn't in git history) | Fall back to "everything is conflict" — safe default. |
| Two `agentic-z-update` runs simultaneously | First creates lock; second refuses while the first PID is alive, regardless of how long the first has been running. Stale locks (dead PID) are taken over automatically. |
| Crash mid-merge before baseline write | Baseline still points to OLD SHA. Next run sees the half-applied state as user customizations on some files — flagged as `conflict`. Worst case: noisy preview, no data loss. |

## Implementation outline

Each step independently committable:

1. **Infrastructure** — gitignore entries, helpers to read/write baseline + lock files. Pure functions; no behavior change yet.
2. **`classify_per_file(baseline, local, upstream)`** — pure function returning the status enum. Add unit tests (~15 cases covering existence + equality combos).
3. **`--check` flag** — wires classify into a preview, no apply. Used by the hook too.
4. **Preview + prompt** — replace existing `git checkout` calls with conditional apply driven by user confirm.
5. **`--yes` and `--per-file` flags** — add the non-interactive paths.
6. **Lock file** — wrap the apply path with lock acquisition / release.
7. **Search index update check** — add the `manifest.json` read + GitHub API call. Integrate into `--check` output and hook.
8. **SessionStart hook entry in `.claude/settings.json`.**
9. **SKILL.md update** — document new flags, baseline file, hook behavior.

## Testing plan

| Layer | Approach |
|---|---|
| Unit | `classify_per_file` — 15 cases (combinations of exists/missing for each blob, equal/diverged combos). Pure function, no git needed. |
| Integration | Scratch git repo with 3 files. Simulate scenarios (clean update, conflict, deletion, new file, lock present). Run `update.py --check` and `update.py --yes`, assert exit codes and final file states. |
| Manual smoke | After implementation lands, dispatch on this repo against an artificial upstream branch with one of each scenario before merging. |

Per the L1 rule (TDD-off-for-DayZ), this is **Python infra** (not DayZ work), so unit tests for `classify_per_file` are appropriate and worth writing.

## Out of scope (explicitly)

- Rolling back failed merges. If a merge breaks somewhere, user can `git restore` themselves.
- 3-way diff for binary blobs — just pick keep / take in the per-file picker.
- Rich diffs in the preview — single-line `M N additions, M deletions` per file is enough; user can `git diff` for detail.
- Auto-applying the search index download (size + bandwidth concern).
- A GUI. Terminal prompts only.
- Detecting Voyage account tier for the index check (handled separately in `feat/voyage-tier-check`).

## Files touched in this PR

| File | Change |
|---|---|
| `.claude/skills/agentic-z-update/update.py` | Rewrite per Section A — three-way merge, preview, prompt, lock, baseline write, search-index check |
| `.claude/skills/agentic-z-update/SKILL.md` | Update for new flags, baseline file, hook behavior |
| `.claude/skills/agentic-z-update/test_update.py` | Unit tests for `classify_per_file` |
| `.claude/settings.json` | Add `SessionStart` hook |
| `.gitignore` | Add `.claude/.upstream-baseline` and `.claude/.upstream-update.lock` |

## Open questions for review

None at design level. All decisions explicit above.
