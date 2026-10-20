---
name: dayz-record-correction
description: Turns the user's correction of how the mod team built something into a written rule with a good and bad example, gets their yes, and saves it in the right tier so every agent follows it from then on. Use whenever the user corrects the team's code, config, structure or behavior, or says "remember this" or "always/never do X".
argument-hint: "[what the user corrected]"
---

# /dayz-record-correction

The user's corrections are how the team learns. Nothing is written without their yes.

This is a meta-skill that edits rule files, not DayZ content, so like `/dayz-scope-mod` it does not gate on `/dayz-preflight`. The Tier 2 rules it adds to live in `.claude/skills/_shared/dayz-conventions.md`; read the relevant section there before drafting so the new rule matches what is already written.

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
- **Tier 2**: true for all DayZ work (Enforce Script style, config patterns, asset rules). Goes in `.claude/skills/_shared/dayz-conventions.md`.
- **Tier 3**: about one kind of work. Goes in that agent's file under `.claude/agents/` or the matching knowledge pack under `.claude/skills/_shared/`.

If an existing rule already covers it, propose an edit to that rule instead of a new one.

## 2. Ask the user

Show the draft and ask for yes, a change, or no. Keep it short.

## 3. Write it (only after yes)

First tell which install you are in from this skill's own base directory: a path under `~/.claude/plugins/cache/` (for example `C:\Users\<you>\.claude\plugins\cache\...`) means a plugin install; anything else (the repo's `.claude/skills/`, or a `~/.claude/skills/` link made by `/sync-skills` that points back into a repo) means a clone.

- In a clone, edit the file the tier names. Keep the edit small and in the file's existing style.
- In a plugin install, the plugin's files are replaced on every update. Write the rule to the user's project `CLAUDE.md` under a `## Agentic-Z rules` heading instead, and say that's why.

## 4. Say what changed

One line: the rule and the file it went into.
