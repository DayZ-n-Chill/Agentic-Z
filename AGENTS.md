# Repository Guidelines

This file provides foundational guidance for agents working in this repository.

## Purpose

This repo is **Agentic-Z** — an AI Agent Stack for DayZ Modding, with first-class support for Claude Code, Codex, and Gemini. Cloning it starts a new DayZ mod project. Every clone inherits the same scaffolding: rules, agents, skills, helper scripts.

## The three tiers

Every agent works from three tiers. When two disagree, the more specific tier wins, and no tier repeats another.

| Tier | What it holds | Where it lives | Loads |
|---|---|---|---|
| 1 · Repo rules (L1) | How every agent works here: communication, tooling, memory, routing, file locations. | This file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) | Every agent, every task |
| 2 · DayZ rules (L2) | Enforce Script style, config patterns, asset rules, environment, vanilla search. | `.claude/skills/_shared/dayz-conventions.md` (core) + `.claude/skills/_shared/conventions/*.md` (topics) | All DayZ work |
| 3 · Agents and knowledge packs | The agents in `.claude/agents/`, the skills, and the packs under `.claude/skills/_shared/` (EnScript patterns, Figma-to-DayZ rules). | Their own files | Only what the task needs |

Corrections from the user go into the right tier through `/dayz-record-correction`.

## Default rules (apply to every clone)

These are the L1 (Tier 1) rules of the template. They apply to every clone of this repo, every agent, every skill. DayZ-specific rules live separately at `.claude/skills/_shared/dayz-conventions.md` and are referenced from the individual agent/skill files that need them.

**Skim summary:**

1. **Communication** — answer first, caveat after.
2. **Tooling** — dedicated tools (`Read`/`Edit`/`Write`/`Glob`/`Grep`) first; Python for non-trivial; PowerShell only when faster.
3. **Memory** — `.claude/local-memory/` for user/machine notes; never for rules.
4. **Subagent routing**. For DayZ work, dispatch the matching `dayz-*` specialist instead of generic Superpowers agents. Role-to-specialist table in `docs/dayz-modding.md`.
5. **Scope** — finish exactly what was asked, then stop; fix only real mistakes; "would be nice" ideas go in `docs/wishlist.md`.

### Scope — finish what was asked, then stop

- **Finish the job.** Keep working until what was asked is done properly and checked.
- **Then stop.** Once it is done, don't keep going by inventing new work.
- **Fix only real mistakes.** Graders, reviewers and fixers count only concrete defects: a wrong fact, a failing test, a doc that doesn't match the code, or a bug. Style preferences and missing extras are not defects.
- **Wishes go on the wishlist.** Any "would be nice to add" idea goes in `docs/wishlist.md` and is never built during the job.
- **Never add what wasn't asked for.** Ask the user first.

### Communication — answer first, caveat after

When asked for something an agent can't literally do (read a UI pane, see the screen, access a closed system), infer what the user actually wants and deliver it via available tools. Mention the limitation as a one-liner *after* the answer, never as the lead. Example: "Here's the markdownlint output your Problems pane is showing — note I can't read the pane directly, but the underlying linter is the same." Not: "I can't read the Problems pane."

### Tooling — pick the fastest tool for the job

- **Dedicated tools first** — `Read`, `Edit`, `Write`, `Glob`, `Grep`. They run in-process (no cold start), return structured output (line-numbered Reads, sorted Globs, output-mode Greps), and handle Windows paths without quoting drama. They replace shell-side `cat`/`head`/`tail`, `sed`/regex-replace, `echo > file`, `find -name`/`ls -R`, and `grep -r`/`rg` respectively. Use them whenever they fit. They do **not** replace process-invocation tools (`git`, `npm`, `taskkill`, `subst`) — those still go through Bash/PowerShell.
- **Default to Python** for non-trivial work that doesn't fit a dedicated tool — parsing, loops, JSON/XML, file ops with logic, anything multi-step. ~150ms cold start.
- **cmd `.bat`** is fine for trivial Windows-native wrappers (calling an `.exe`, junctions, taskkill, etc.).
- **PowerShell** is allowed, but only when (a) you explicitly ask for it, or (b) it's genuinely faster than the alternatives for the task. Avoid as a default — PowerShell's cold-start (~1.5s) and folder traversal are slow compared to Python.
- **Bash** for trivial one-liners only; cold-start is similar to PowerShell on Windows.

### Memory — `.claude/local-memory/` only, never for rules

User/machine-specific notes go in `<repo>/.claude/local-memory/` (gitignored, per-clone). Never store rules or conventions there — those go in the repo so they travel with every clone. L1 rules live in this file; L2 DayZ rules live at `.claude/skills/_shared/dayz-conventions.md`.

### Subagent routing for DayZ work

**Route new DayZ requests cheaply first.** For a new DayZ request, run `/dayz-route` before picking a handler and follow its result when it names a route (it is confident only at 0.8 or more). When it returns `"next": "dayz-router"`, ask the `dayz-router` agent (Haiku) and follow its JSON. Jev, TypeSafe's routing model, is used automatically between the two when `TYPESAFE_API_KEY` is set.

When a Superpowers workflow (`/brainstorming`, `/executing-plans`, `/requesting-code-review`, `/dispatching-parallel-agents`, etc.) needs to dispatch a subagent and the work touches DayZ, route to the matching `dayz-*` specialist via the Agent tool. Generic Superpowers agents (e.g. `superpowers:code-reviewer`) don't know Enforce Script conventions and will miss DayZ-specific traps like the `modded class` no-extends rule or engine classes that can't be modded.

**Figma-to-DayZ work has its own pipeline.** When the input is a Figma URL, fileKey, or node ID and the target is a DayZ `.layout`, dispatch the three-stage pipeline in order: `figma-node-normalizer` → `figma-to-dayz-layout` → `dayz-layout-validator` (gate mode). Do not author the `.layout` inline or via `dayz-ui-specialist` alone — the canonical translation rules live at `.claude/skills/_shared/figma-to-dayz-rules.md` and only the pipeline applies them. After the pipeline finishes, `dayz-ui-specialist` handles polish, widget scripts, and Workbench wiring. When `dayz-ui-specialist` is handed a Figma input it returns to its caller, and the caller (`dayz-lead` or the main session) runs the pipeline.

Heuristic: anything under `workspace/<ModName>/`, `.claude/skills/dayz-*/`, `P:\`, or DayZ file types (`.c`, `.layout`, `.p3d`, `.paa`, `.rvmat`, `config.cpp`, `types.xml`) is DayZ work. See the role-to-specialist table at `docs/dayz-modding.md` ("Superpowers ↔ DayZ specialist routing").

For non-DayZ work (Python skills, scripts, infra, the wiki), Superpowers' generic agents are fine.

## Repository Use

- **Bootstrap**: After cloning, run `/sync-skills` (or `python .claude/skills/sync-skills/sync.py`). This links the repo's `.claude/skills/` into the Codex and Gemini home dirs so they discover the same slash commands Claude Code reads from the repo directly (`--agents claude` also links into Claude Code's home, making the skills global there). The agent list lives in `.claude/skills/sync-skills/agents.json` — adding a new agent CLI later is a one-entry edit.
- Agent definitions live in `.claude/agents/`.
- Agent memory lives in `.claude/agent-memory/` (per-user, gitignored; auto-created on first write).
- Reusable skills live in `.claude/skills/`.
- Local settings live in `.claude/settings.local.json` (per-user, gitignored). Project-wide settings go in `.claude/settings.json`.
- Keep the repository root clean.
- `output/` is the **default destination for one-shot deliverables** — documents, decks, generated files, and other artifacts the user takes elsewhere. Goes under `output/<descriptive-folder>/` unless the user names a different destination.
- `workspace/` is for **in-progress mod projects** — anything you're actively iterating on across sessions. Each mod gets its own subfolder (`workspace/<ModName>/`).
- `.server/` (project root) holds **DayZ test-server runtime**: one folder per instance (`.server/<instance>/{mission, serverDZ.cfg, Profiles}`) plus a shared top-level `.server/!ClientDiagLogs/` for the client `-profiles=` dir. Created by `/dayz-add-server`. Multiple instances allowed (e.g. chernarus, chernarus-hardcore). Gitignored as a whole: every machine's test server is its own, and `/dayz-add-server` recreates it.
- `scripts/` is for **helper automation** — Python, PowerShell, batch, etc. that *produces* content elsewhere. Tools, not products.
- Exceptions to the `output/` rule, none of which move:
  - Agent memory stays in `.claude/agent-memory/`.
  - Skill-bundled helper scripts (e.g. `preflight.py` next to its `SKILL.md`) stay inside their skill folder under `.claude/skills/`.
  - **DayZ mods**: project workspaces live under `workspace/<ModName>/`, and built `.pbo`s deploy to `P:\Mods\@<ModName>\Addons\` (the symlinked Workshop folder on the P-drive). Nothing under `output/`. This is inherent to how DayZ Tools and the game expect mod content to be laid out — the P-drive is mounted by DayZ Tools and is the only place the engine looks for in-development mods. DayZ skills must preflight that `P:\` is mounted and halt with a clear message if not.

## Working Conventions

- **Doc maintenance**: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` hold the same content. Three filenames so each agent CLI auto-loads its own. Edit all three together when one changes. No SYNC markers, symlinks, or shared imports.
- Keep agent instructions self-contained so they can run without prior conversation context.
- Keep skills self-contained so they can run without prior conversation context.
- When modifying agent definitions in `.claude/agents/`, preserve the established structure and keep edits surgical.
- When modifying reusable skills in `.claude/skills/`, keep them focused, explicit, and portable.
- Use workspace tools and existing agents before adding new ad hoc logic.
- Do not create new root-level helper scripts; use `scripts/` for ad hoc automation.
- When an agent or skill creates a deliverable, write it under `output/<descriptive-folder>/` by default. Only deviate when the user names a specific destination, or when the destination is inherent to the task (e.g. deploying to a real server path, editing in-place inside an existing project).
- Treat generated files and local settings as workflow artifacts unless a change is intentionally meant to be versioned.

## Environment Notes

- This is a Windows workspace.
- There is no app source tree. Tests are pytest files placed next to the code they cover. Validate changes with `python -m pytest -q .claude scripts/dev hooks`, which is what CI runs in `.github/workflows/tests.yml`, and after agent or skill changes also run `python .claude/skills/docs-sync/sync.py --check`, which checks the React wiki under `wiki/` against the repo.
- Slash skill discovery is agent-specific. Claude Code reads the repo's `.claude/skills/` plus `$CLAUDE_CONFIG_DIR/skills` or `$HOME/.claude/skills`. Codex reads the repo's `.agents/skills/` and `$HOME/.agents/skills`. Gemini reads the workspace's `.gemini/skills/` or `.agents/skills/` and `$HOME/.gemini/skills` or `$HOME/.agents/skills`. To make the repo's `.claude/skills/` appear in Codex and Gemini too, run `/sync-skills` (or `python .claude/skills/sync-skills/sync.py`). It symlinks each repo skill into each agent's skills directory (Claude Code's only with `--agents claude`; `--unlink` removes the links) without moving the source files; falls back to junctions on Windows when symlinks need elevation. Afterward, restart/reload the agent session; in Gemini CLI, run `/skills reload` before `/skills list`.
