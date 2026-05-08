# Contributing to Agentic-Z

This guide is for people who want to improve the Agentic-Z toolbox itself: new skills, agent improvements, bug fixes, docs. If you're here to use the toolkit to build a DayZ mod, see the [README](README.md) instead.

## Clone and set up

```cmd
git clone https://github.com/DayZ-n-Chill/Agentic-Z.git
cd Agentic-Z
python .claude\skills\sync-skills\sync.py
```

`sync-skills` symlinks (or junctions on Windows) the repo's `.claude/skills/` into Claude Code, Codex, and Gemini home dirs so all three discover the same slash commands during local testing. Restart or reload your agent session after running it.

## Branch rules

- Branch from `develop`, never from `main`.
- PR target is `develop`. The `main` branch is for landed, released work only.
- Branch naming: `feature/<thing>`, `fix/<thing>`, `docs/<thing>`.

## Standard contribution flow

1. Cut a branch from `develop`.
2. Make your changes. Keep each commit focused.
3. Run the affected skill's Python script manually to verify it works end-to-end.
4. Open a PR against `develop`. The description should explain what changed and why.
5. Address review feedback.
6. Merge once approved.

## What belongs here

- `.claude/skills/` — slash-command skills (Python + SKILL.md).
- `.claude/agents/` — DayZ specialist agent definitions.
- `.claude/mcp/` — MCP server code (dayz-rag, etc.).
- `docs/` — deep documentation.
- `scripts/` — thin `.bat` wrappers around skills, grouped by audience:
  - `scripts/setup/` — pre-Claude bootstrap (workdrive, sync-skills, agentic-z-update, preflight, setup-objectbuilder)
  - `scripts/dayz/` — daily DayZ workflow (build, launch, scaffold, types, search, etc.)
  - `scripts/dev/` — template-author tools (clean-repo, docs-sync, wiki-cleaning + WCAG audit Python helpers)
- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` — L1 rules (edit all three together; same content in each).

## What does NOT belong here

- User mod source. Your DayZ mod lives in your own repo (or under `workspace/<ModName>/` here). Run `/dayz-init` to scaffold or import; the wizard caches the project root so other skills find it.
- `.server/` staging folders. Server instances belong in the user's project, not in this template.
- Generated or local-only files. `output/`, `.claude/local-memory/`, `.claude/settings.local.json` are gitignored for a reason.

## Testing a new skill

1. Place your skill folder at `.claude/skills/<my-skill>/` with `SKILL.md` and your script.
2. Run `sync-skills` so the CLI picks it up.
3. Run the script directly: `python .claude\skills\<my-skill>\<script>.py [args]`.
4. Fix issues, commit, open PR.

## Docs

If you add or rename a skill, update:
- The SKILL.md (frontmatter `name:` and `description:`).
- The skills table in `README.md` and `docs/README.md`.
- `docs/dayz-modding.md` if the skill appears in the workflow section.
- The plugin manifests in `.claude-plugin/` if the skill should be exposed to plugin users.

Do not touch `wiki/` — it regenerates via `/docs-sync` from the canonical sources.
