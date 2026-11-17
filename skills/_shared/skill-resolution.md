# Skill resolution: the same skill from two places

What to do when one skill name is installed twice: once as a personal skill in `~/.claude/skills/<name>` (on Windows `%USERPROFILE%\.claude\skills\<name>`) and once through a plugin (`<plugin>:<name>`). This file covers duplication that already exists. For the check to run before a plugin is installed, see "Before installing a new plugin" below.

This is a rule about agent tooling, not about the game, so it cites no vanilla file.

## How the duplication happens here

- The Agentic-Z plugin serves every skill under `skills/` with the `agentic-z:` prefix (`agentic-z:dayz-p3d-audit`).
- `/sync-skills --agents claude` links the same skills into `~/.claude/skills/`, where they load under the bare name (`dayz-p3d-audit`). `.claude/skills/sync-skills/SKILL.md` explains why Claude Code is left out of a plain `/sync-skills` run for this reason.
- A user may also keep an own, patched copy of a skill in `~/.claude/skills/` (for example `dayz-p3d-audit` or `dayz-particles`) and then install a plugin that ships a skill with the same name.

In each case both copies stay reachable: the bare name and the prefixed name.

## Default

With no written project policy, the personal copy in `~/.claude/skills/<name>` wins over the plugin copy (`<plugin>:<name>`), because a personal copy usually carries patches made for that user.

## Per-skill policy (decide when a conflict is found)

1. **The personal copy came from the plugin and the plugin now has the same patch.** Delete the personal copy and use the plugin copy. Compare the two `SKILL.md` files with a diff before deleting anything, and read "What the measurement showed" below first: the plugin folder you diff against may not be the copy that is served.
2. **The personal copy differs a lot** (its own `P:\` paths, numbers tuned to one setup, sections for the user's own mods). Keep the personal copy and switch off the plugin's copy of that one skill with `/plugin manage <plugin>`.
3. **Not sure.** Keep both and write the conflict down where every agent reads it:

```markdown
## Skill resolution overrides
- For `dayz-p3d-audit`: use `<namespace>:dayz-p3d-audit` because <reason>. Last checked YYYY-MM-DD.
```

## Write the decision where agents see it

Once decided, record the override so that Claude Code, Codex and Gemini all call the same copy and none of them has to work the conflict out again each session:

- A decision that holds for one machine (which personal copies exist there) goes in `.claude/local-memory/`.
- A decision that holds for the project goes in the three agent files, edited together: `.claude/CLAUDE.md`, `AGENTS.md` and `GEMINI.md`.

## Before installing a new plugin

List the personal skills (`ls ~/.claude/skills/`) and compare the names with the plugin's manifest (`.claude-plugin/plugin.json` in the plugin). Decide the per-skill policy before installing, not after noticing the conflict.

## What goes wrong otherwise

A plugin is installed without checking for conflicts, the duplication is found three sessions later, and nobody decides. Both versions then live side by side for good, agents call whichever one their search order finds first, and the user cannot tell why the skill behaves differently from one session to the next.

## What the measurement showed (2026-08-24)

The default above ("the personal copy wins") was written first as policy and measured later. The measurement was made on 2026-08-24 on one Windows machine with the Claude desktop app, and has not been repeated in this repo. One duplicated skill was called by both of its names and the base directory each call reported was read:

| Call | Loads from |
|---|---|
| `mixamo-retarget` (bare name) | `%USERPROFILE%\.claude\skills\mixamo-retarget` |
| `anthropic-skills:mixamo-retarget` (prefixed) | `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\<uuid>\<uuid>\skills\mixamo-retarget` |

The default held. Two things were missing from it, and they are the ones that cause damage:

1. **"Wins" is true for the bare name only.** Both copies stay servable. The prefixed name loads the plugin copy, and both names are in the catalog of every session. Fixing the personal copy therefore does not retire the other one: an agent that writes `anthropic-skills:<name>` gets the old version with nothing to say it is old. In the measurement the served plugin copy was 19 days behind and lacked a fix that the personal copy had.
2. **There is a third folder tree, and it is neither of the two you can edit.** What the prefix serves is not the folder the plugin was packaged from. It is a copy the app writes under `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\`, with a manifest and a reconciler that deletes unregistered items within minutes. More than one install can sit there at once, with different contents. A hand edit in that tree does not survive; the supported way to register a skill there is a `.skill` file and the app's "Save skill" button.

The same measurement counted five skill root folders on that machine and four different versions of one skill servable at the same time.

**What this changes in policy 1** ("delete the personal copy, use the plugin copy"): before deleting anything, check which of the plugin trees is really served, and with what content. A diff against the folder the plugin was packaged from can come up clean while the served copy is something else.

**A one-minute check:** call the skill by both names, then compare the base directory and one distinctive line of the body. If they differ, the duplication is still being served and is not resolved.
