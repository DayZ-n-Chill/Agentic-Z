# Skill resolution: the same skill from two places

What to do when one skill name is installed twice: once as a personal skill in `~/.claude/skills/<name>` (on Windows `%USERPROFILE%\.claude\skills\<name>`) and once through a plugin (`<plugin>:<name>`).

## How the duplication happens here

- The Agentic-Z plugin serves every skill under `skills/` with the `agentic-z:` prefix (`agentic-z:dayz-p3d-audit`).
- `/sync-skills --agents claude` links the same skills into `~/.claude/skills/`, where they load under the bare name (`dayz-p3d-audit`). `.claude/skills/sync-skills/SKILL.md` explains why a plain `/sync-skills` run leaves Claude Code out for this reason, and how `--unlink` removes the links.
- A user may also keep a patched copy of a skill in `~/.claude/skills/` and then install a plugin that ships a skill with the same name.

In each case both copies stay reachable: the bare name and the prefixed name.

## Which copy loads

- The bare name loads the personal copy in `~/.claude/skills/<name>`.
- The prefixed name loads the plugin copy. Fixing the personal copy therefore does not retire the plugin copy: an agent that writes `<plugin>:<name>` still gets the plugin version, with nothing to say it is older.
- In the Claude desktop app, the prefixed name loads from a copy the app keeps under `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\`, not from the folder the plugin was packaged from. The app reconciles that folder and deletes hand edits in it; register a skill there with a `.skill` file (`scripts/dev/pack_skill.py`) and the app's "Save skill" button.

With no written project policy, treat the personal copy as the one that wins, because it usually carries patches made for that user.

## Per-skill policy

1. **The personal copy came from the plugin and the plugin now has the same patch.** Delete the personal copy and use the plugin copy. Diff the two `SKILL.md` files first, and diff against the copy that is actually served (see "Which copy loads"), not only the folder the plugin was packaged from.
2. **The personal copy differs a lot** (its own `P:\` paths, numbers tuned to one setup, sections for the user's own mods). Keep the personal copy. `claude plugin disable <plugin>` turns off the whole plugin with all its skills; use it only when no other skill of the plugin is needed. Otherwise leave the plugin on and write an override that names the bare personal skill, in the format under policy 3.
3. **Not sure.** Keep both and write the conflict down where every agent reads it:

```markdown
## Skill resolution overrides
- For `dayz-p3d-audit`: use `<namespace>:dayz-p3d-audit` because <reason>. Last checked YYYY-MM-DD.
```

## Write the decision where agents see it

- A decision that holds for one machine (which personal copies exist there) goes in `.claude/local-memory/`.
- A decision that holds for the project goes in the three agent files, edited together: `.claude/CLAUDE.md`, `AGENTS.md` and `GEMINI.md`.

## Before installing a new plugin

List the personal skills (`ls ~/.claude/skills/`) and compare the names with the plugin's manifest (`.claude-plugin/plugin.json` in the plugin). Decide the per-skill policy before installing, not after noticing the conflict.

## A one-minute check

Call the skill by both names, then compare the base directory each call reports and one distinctive line of the body. If they differ, the duplication is still being served and is not resolved.
