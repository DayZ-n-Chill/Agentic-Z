---
name: sync-skills
---

## Overview

Links every skill in this repo's .claude/skills/ into each agent CLI's home skills folder (Claude Code, Codex, Gemini or any in agents.json) so all of them see the same slash commands. Use when you have just cloned the repo, added, removed or renamed a skill, or moved the repo.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\<other>\`. For first-time bootstrap from a fresh clone (before any harness is loaded), run the literal command `python .claude\skills\sync-skills\sync.py` from the repo root.

# /sync-skills

The bootstrap. **Links, not copies.** The single source of truth is `<repo>/.claude/skills/`; this skill creates symlinks (or junctions on Windows) in each agent CLI's home so every agent discovers the same slash commands. Nothing is copied, no skill content lives outside the repo, and editing a skill in the repo is instantly live in every agent.

The reason the agent home dirs are involved at all: Claude Code reads the repo's `.claude/skills/` directly, but Codex and Gemini only scan their own home dirs. The links bridge that gap without duplicating files.

## Side effect for Claude Code: the skills become global

`~/.claude/skills/` is Claude Code's personal skills folder, which it loads in every project, not just this repo. By default this skill links into it, so after a run:

- Every `/dayz-*` skill is available in every Claude Code project on this machine.
- If the Agentic-Z plugin is also installed, each skill shows up twice: once from the plugin (`agentic-z:dayz-build-pbo`) and once from the link (`dayz-build-pbo`). Inside this repo Claude Code also reads `.claude/skills/` directly, so the Claude link adds nothing here.

To keep Claude Code project-scoped, leave it out: `python "<skill-dir>\sync.py" --skip claude`. That only stops new links; remove existing ones by deleting the links under `~/.claude/skills/` (`cmd /c rmdir` on each link removes the link, not the repo folder). The default still links all agents in `agents.json`, Claude included.

## When to run it

- **Right after cloning the repo** — step two, before doing real work. None of the slash commands work in Codex or Gemini until this runs (Claude Code reads from the repo's `.claude/skills/` directly, but Codex and Gemini only read from their home dirs).
- **After adding a new skill** to `.claude/skills/`.
- **After deleting a skill** — orphan links pointing at the now-missing source get pruned.
- **After moving the repo** to a different path. Links still pointing at the old location are reported as `[FOREIGN]`; rerun with `--force` to retarget them.

## How to run

```cmd
python "<skill-dir>\sync.py"
```

Optional flags:

```cmd
python "<skill-dir>\sync.py" --agents claude codex     # subset
python "<skill-dir>\sync.py" --skip claude             # everything except Claude Code
python "<skill-dir>\sync.py" --dry-run                 # preview, no writes
python "<skill-dir>\sync.py" --force                   # take over links that point at another clone
```

## Where the per-agent skills folders live

Resolved from `agents.json`. Defaults:

| Agent  | Env var(s) checked first                | Default path |
|--------|------------------------------------------|--------------|
| Claude | `CLAUDE_CONFIG_DIR`                     | `~/.claude/skills` |
| Codex  | `CODEX_HOME`                            | `~/.codex/skills`  |
| Gemini | `GEMINI_CLI_HOME` then `GEMINI_HOME`    | `~/.gemini/skills` |

To support a new agent later, append an entry to `.claude/skills/sync-skills/agents.json` — no code change needed.

## What it does, per skill, per agent

For every folder under `.claude/skills/<name>/` containing `SKILL.md`, plus `_shared/`. `_shared/` is not a skill, but agents read the shared reference docs through `~/.claude/skills/_shared/` from other projects, so it is linked too. Other folders starting with `_` are skipped.

| Existing state in `<home>/skills/<name>` | Action |
|---|---|
| Link already points at the repo skill | `[OK]` no-op |
| Link points at a different path inside this repo (stale) | `[REFRESH]` retarget to the right skill |
| Link points outside this repo (another clone, or the repo's old location) | `[FOREIGN]` left alone and counted as skipped; with `--force` it is retargeted (`[REFRESH]`) |
| Path doesn't exist | `[LINK]` create new link |
| Real folder, not a link | `[SKIP]` warn — don't clobber user-installed skills |
| Orphan link in target dir, points back into this repo at a path that's gone | `[PRUNE]` remove the link |

Link targets are compared after normalising separators and, on Windows, case (`os.path.normcase`), so `C:\Repo` and `c:\repo` count as the same place.

## Output

One line per skill per agent, then a summary. Example (trimmed). The repo count is from this repo at the time of writing (44 skills plus `_shared`); the summary counts are made up for illustration, and yours depend on what each agent home already holds:

```
Repo skills: 45  (H:\Projects\Agentic-Z\.claude\skills)
  - _shared
  - agentic-z-update
  ...

[claude] C:\Users\you\.claude\skills
  [OK]      _shared
  [LINK]    dayz-new-skill  (junction)
  ...

[codex] C:\Users\you\.codex\skills
  [FOREIGN] dayz-preflight: points at D:\old-clone\.claude\skills\dayz-preflight; rerun with --force to take ownership
  ...

Summary
      linked: 2
          ok: 95
   refreshed: 0
     skipped: 1
      pruned: 0
      failed: 0
```

Exits 1 if any link operation failed, and 2 if `agents.json` is missing or malformed, `--agents`/`--skip` names an unknown agent, or the repo's `.claude/skills/` folder is missing.

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
