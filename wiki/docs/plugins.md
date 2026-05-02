---
sidebar_position: 4
sidebar_label: Plugins
title: Plugins
---

# Plugins

Two optional plugins extend Agentic-Z when you want them. Both are off by default — set them up only if you want what they offer.

| Plugin | What it adds | Setup time |
|---|---|---|
| **Superpowers** | Opinionated workflows: TDD red-green-refactor, plan-first, brainstorm-first, four-phase systematic debugging. | 2 minutes |
| **Obsidian vault** | Graph-view navigation across `CLAUDE.md`, agents, skills, and docs in your editor. Backlinks panel surfaces "where else is this mentioned." | 5 minutes |

## Superpowers

[Superpowers](https://github.com/obra/superpowers) is a Claude Code plugin marketplace by Jesse Vincent (obra) that adds opinionated engineering workflows. When enabled, slash commands like `/brainstorming`, `/writing-plans`, `/executing-plans`, `/test-driven-development`, and `/systematic-debugging` become available.

### When it helps

- General code work in `scripts/`, `.claude/skills/`, or any non-DayZ Python/JS you write.
- Debugging anything where the bug isn't obvious from the first error.
- New features that benefit from a brainstorm + written plan before code.

### When to skip it

DayZ work. Enforce Script has no test runner, so TDD doesn't apply. The L2 conventions explicitly carve out the DayZ surface from these workflows. Trivial edits and one-line fixes also don't need a brainstorm + plan + TDD cycle.

### Setup

1. Open `.claude/settings.json` (create it if it doesn't exist).
2. Add `obra/superpowers` to `extraKnownMarketplaces`:

   ```json
   {
     "extraKnownMarketplaces": [
       {
         "name": "obra/superpowers",
         "source": "github:obra/superpowers"
       }
     ]
   }
   ```

3. Restart Claude Code so it picks up the marketplace.
4. Install the plugin with `/plugin install superpowers@obra` (or whatever the marketplace prompts for).
5. Type `/` to confirm the new commands appear: `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, etc.

When you ask for general code work, the agent is now expected to use these workflows. When you're working on DayZ, it should ignore them per the L2 carve-out.

## Obsidian vault

The repo root works as an [Obsidian](https://obsidian.md) vault. Open it as a vault to navigate the agent stack visually: `CLAUDE.md` ↔ `.claude/agents/` ↔ `.claude/skills/` ↔ `docs/` via graph view + backlinks. Same files the agents read; same files you can browse.

### When it helps

- Visualizing how agents reference shared conventions, where a skill is mentioned, what depends on what.
- Navigating large agent stacks once you start adding your own.
- Reading the docs comfortably outside a code editor.

### When to skip it

If you're only running Agentic-Z from a CLI and never opening it as a knowledge base, Obsidian adds nothing. Pure consumers of the slash commands don't need it.

### Setup

1. Install [Obsidian](https://obsidian.md/download) (free, all platforms).
2. Open Obsidian → **Open folder as vault** → pick the Agentic-Z repo root.
3. On first open, Obsidian detects the checked-in `.obsidian/` workspace config and prompts to install the recommended community plugins:
   - **Dataview** — query notes like a database
   - **Templater** — note templates and snippets
   - **Excalidraw** — sketch and diagram inside notes
   - **Outliner** — better outline editing
   - **Git** — commit and pull from inside Obsidian

   Accept to enable the repo-managed defaults, or skip if you prefer your own setup.

4. Switch to the **graph view** (Ctrl/Cmd + G) to see the agent stack as a network. Click any node to jump to that file. Backlinks (Ctrl/Cmd + Shift + Backspace) show every place that references the current file.

### Things to know

- Per-user auto-memory still lives at `~/.claude/projects/<repo>/memory/`, not in the vault.
- Don't move files into `.obsidian/` — the agents and slash commands read from `.claude/` and the repo root, not from Obsidian's metadata.
- Edits in Obsidian write plain markdown. Nothing breaks the file format the agents need.
