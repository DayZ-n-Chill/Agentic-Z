---
name: dayz-record-correction
description: "Turns the user's correction of how the mod team built something into a written rule with good and bad examples, confirms it, and saves it where every agent follows it. Use whenever the user corrects the team's code, config, structure or behavior, or says \"remember this\" or \"always/never do X\"."
argument-hint: "[what the user corrected]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-record-correction

The user's corrections are how the team learns. Nothing is written without their yes.

This is a meta-skill that edits rule files, not DayZ content, so like `/dayz-scope-mod` it does not gate on `/dayz-preflight`. The Tier 2 rules it adds to live in `.claude/skills/_shared/dayz-conventions.md` and its topic files in `.claude/skills/_shared/conventions/`; read the relevant section there before drafting so the new rule matches what is already written.

## 1. Draft the rule

```
Rule: <one sentence, in the user's words>
Why: <one line>
Good: <a short example>
Bad: <the version the user corrected>
Tier: 1 | 2 | 3 (<file>)
```

Pick the tier by scope:

- **Tier 1**: how any agent works in this repo, DayZ or not (reporting, tooling, file locations). Goes in `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`, all three with the same text.
- **Tier 2**: true for all DayZ work (Enforce Script style, config patterns, asset rules). Goes in `.claude/skills/_shared/dayz-conventions.md` if every DayZ agent needs it, otherwise in the matching topic file under `.claude/skills/_shared/conventions/` (config, assets, scripts, ui, server).
- **Tier 3**: about one kind of work. Goes in that agent's file under `.claude/agents/` or the matching knowledge pack under `.claude/skills/_shared/`.

Once you have picked a tier, search all three tiers for a rule that overlaps (Grep the key words across `CLAUDE.md`, `.claude/skills/_shared/dayz-conventions.md`, `.claude/skills/_shared/conventions/*.md`, `.claude/agents/*.md` and `.claude/skills/_shared/**/*.md` (the knowledge packs live in subfolders such as `_shared/enscript/`), all relative to the Agentic-Z repo root that step 3 shows how to find):

- An overlapping rule in the right tier: propose an edit to that rule instead of a new one.
- An overlapping rule in the wrong tier (for example a DayZ-wide rule sitting in one agent's file): propose moving it to the right tier and merging the correction into it, so the rule lives in one place.
- Overlapping rules in two tiers: propose merging them into the one tier that fits.

## 2. Ask the user

Show the draft and ask for yes, a change, or no. Keep it short.

## 3. Write it (only after yes)

First find where this skill really lives. `/sync-skills` exposes it through a link (a junction on Windows) under `~/.claude/skills/`, and the harness reports the link path as the base directory, so resolve the link before deciding anything:

```cmd
python -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "<skill-dir>"
```

`os.path.realpath` follows symlinks and junctions. Then read the resolved path:

- Under `~/.claude/plugins/cache/` (for example `C:\Users\<you>\.claude\plugins\cache\...`): a plugin install.
- Ending in `\.claude\skills\dayz-record-correction`: a clone. The Agentic-Z repo root is three levels up from it (the folder that holds `.claude\`), and every file the tiers name (`CLAUDE.md`, `.claude\skills\_shared\dayz-conventions.md`, `.claude\agents\...`) is relative to that root, not to the current project.

- In a clone, edit the file the tier names under that repo root, even when the session was started in another project. Keep the edit small and in the file's existing style.
- In a clone, if the edited file is under `.claude\agents\` or `.claude\skills\` (a `SKILL.md`, `.claude\skills\_shared\dayz-conventions.md` or a topic file under `.claude\skills\_shared\conventions\`), run `/docs-sync` so the wiki mirror under `wiki\docs\` stays in sync. Otherwise the Stop hook reports wiki drift at the end of the session.
- In a plugin install, the plugin's files are replaced on every update. Write the rule under a `## Agentic-Z rules` heading in whichever of the project's `CLAUDE.md`, `AGENTS.md` and `GEMINI.md` exist, with the same text in each, and say that's why. For a Tier 1 rule, create any of the three that are missing, so Claude Code, Codex and Gemini all see it. For a Tier 2 or Tier 3 rule, create all three the same way when none of them exists.

## 3b. Check it (clones only)

From the repo root, run the tests and the wiki drift check. They need pytest and pyyaml once: `python -m pip install pytest pyyaml`.

```cmd
python -m pytest -q .claude scripts/dev hooks
python .claude/skills/docs-sync/sync.py --check
```

The root `pytest.ini` skips `.claude/worktrees/`, where Claude Code keeps full copies of the repo for its worktree sessions, so the run sees only this checkout.

An edit to an agent file or a rules file can break the repo tests (for example `test_route.py` checks the agent list against `rules.json`). If either command fails because of your edit, fix the problem or revert the edit, then run both again. A failure in a test file outside the area you edited (for example a skill test that also fails with your edit undone) is not a reason to revert; report it instead.

## 4. Say what changed

One line: the rule and the file it went into. When `/docs-sync` ran, also name the wiki page it updated, for example `wiki\docs\agents\dayz-config-specialist.md`. In a clone, add the result of step 3b: tests passed and the wiki is in sync, or what failed and whether you fixed or reverted it.
