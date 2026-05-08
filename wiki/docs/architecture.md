---
sidebar_position: 1
sidebar_label: Architecture
title: Architecture
---

# Architecture

How Agentic-Z is organized internally and how agents find their rules.

## Three layers

| Layer | Scope | Where it lives |
|---|---|---|
| **L1 — Default rules** | Apply to every clone, every agent, every skill. | `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (three filenames so each CLI finds its own; same content in each) |
| **L2 — DayZ conventions** | Apply when working inside the DayZ domain. | `.claude/skills/_shared/dayz-conventions.md` |
| **L3 — Specific agent or skill** | The actual unit of work. | `.claude/agents/&lt;name&gt;.md` or `.claude/skills/&lt;name&gt;/SKILL.md`, plus its scripts |

L3 files include a one-line reference to L2: *"Follow `.claude/skills/_shared/dayz-conventions.md`."*

## How agents and skills find their rules

When invoked on a task, an agent should:

1. Read the L1 file for the CLI in use (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
2. Read the specific agent or skill being run (L3).
3. If L3 references the DayZ conventions file (L2), read it.
4. Obey all three layers; the more specific layer wins ties.

## Default rules at L1

The exact text lives in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`. Summary:

- **Communication — answer first, caveat after.** When asked for something an agent can't literally do, deliver the underlying answer via available tools and mention the limitation as a one-liner *after*, never as the lead.
- **Tooling — pick the fastest tool for the job.** Default to Python; cmd `.bat` for trivial wrappers; PowerShell only when explicitly asked or genuinely faster; Bash for trivial one-liners only; prefer dedicated `Read` / `Edit` / `Write` / `Grep` / `Glob` over shelling out.
- **Doc maintenance — plain copies.** `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` hold the same content. Edit all three together.
- **Bootstrap — run `/sync-skills` after cloning.** Required to make Codex and Gemini see the slash commands. (Plugin installs don't need this.)
- **Memory — local-memory only, never for rules.** User/machine notes only; rules go in the repo.
- **Model routing — match model to task.** Searches/research → Sonnet subagent; trivial file-find → Haiku subagent; coding/design → main Opus thread. See [model-routing](./model-routing).
- **Prompt conventions — caps are a finite signal.** Uppercase section headers are structural; inline `MUST` / `NEVER` / `ALWAYS` are behavioral and measurably affect model compliance, but only when rare.

## File structure (clone-based view)

If you installed Agentic-Z as a Claude Code plugin, you don't need to know this layout — Claude Code handles it. This is what the source repo looks like for clone-based users and contributors.

```
&lt;repo&gt;/
├── .claude/
│   ├── agents/                         # DayZ agent definitions (L3)
│   ├── skills/                         # skill definitions (L3) + L2 shared
│   │   ├── _shared/
│   │   │   └── dayz-conventions.md     # L2 rules for the DayZ domain
│   │   ├── sync-skills/                # bootstrap skill
│   │   │   ├── SKILL.md
│   │   │   ├── sync.py
│   │   │   └── agents.json             # list of agent CLIs to sync into
│   │   └── dayz-*/                     # one folder per DayZ skill
│   │       ├── SKILL.md
│   │       └── *.py
│   ├── agent-memory/                   # per-agent memory (committed)
│   ├── local-memory/                   # gitignored, per-clone, user/machine notes only
│   └── settings.local.json             # per-clone Claude Code settings
├── .claude-plugin/
│   ├── plugin.json                     # plugin manifest
│   └── marketplace.json                # marketplace catalog
├── CLAUDE.md                           # L1 rules (Claude Code reads this)
├── AGENTS.md                           # L1 rules (Codex reads this)
├── GEMINI.md                           # L1 rules (Gemini reads this)
├── docs/                               # canonical long-form docs
├── scripts/                            # helper .bat/.py wrappers (subfoldered by audience)
│   ├── setup/                          # pre-Claude bootstrap
│   ├── dayz/                           # daily DayZ workflow
│   └── dev/                            # template-author tools
├── wiki/                               # the Docusaurus site you're reading
├── workspace/                          # in-progress mods (workspace/&lt;ModName&gt;/)
└── output/                             # one-shot deliverables
```

## How to add things

### Add a new skill

1. Create `.claude/skills/my-skill/`.
2. Add `SKILL.md` with frontmatter (`name`, `description`) and a "How to run" section.
3. Add the actual script (e.g. `my-skill.py`).
4. Run `/sync-skills` to make it discoverable in all agent CLIs.
5. If the skill should ship to plugin users, register it in `.claude-plugin/plugin.json`.

### Add a new agent CLI

Append an entry to `.claude/skills/sync-skills/agents.json`:

```json
{
  "name": "newagent",
  "env_home_vars": ["NEWAGENT_HOME"],
  "default_home": "~/.newagent",
  "skills_subdir": "skills"
}
```

Run `/sync-skills` — the new agent's home gets links for every existing skill.

## Local memory

| | |
|---|---|
| **Path** | `&lt;repo&gt;/.claude/local-memory/` |
| **Committed?** | No (gitignored) |
| **Scope** | Per-clone — each project has its own; nothing leaks across clones |
| **Used for** | User/machine-specific notes only — paths peculiar to your box, email addresses, anything that doesn't belong in the repo |
| **Never used for** | Rules, conventions, project knowledge — those go in the repo at L1 (template-wide) or L2 (DayZ-specific) so they travel with every clone |
