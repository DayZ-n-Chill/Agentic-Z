---
sidebar_position: 4
sidebar_label: Plugins
title: Plugins
---

# Plugins

Optional plugins extend Agentic-Z when you want them. Off by default - set up only if you want what they offer.

| Plugin | What it adds | Setup time |
|---|---|---|
| **Superpowers** | Opinionated workflows: TDD red-green-refactor, plan-first, brainstorm-first, four-phase systematic debugging. | 2 minutes |

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
