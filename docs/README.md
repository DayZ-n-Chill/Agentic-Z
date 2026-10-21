# Agentic-Z

**An AI Agent Stack for DayZ Modding**, with first-class support for Claude Code, Codex, and Gemini. Clone it to start a new DayZ mod, import a 3D model, set up a server, or tune the economy. Every project inherits opinionated rules, specialist agents, slash-command skills, and a semantic-search RAG over the vanilla engine source (Voyage AI `voyage-code-3` embeddings stored locally in LanceDB). Your AI shows up DayZ-fluent on day one.

## Quick start

```cmd
git clone <this-repo> my-mod
cd my-mod
python .claude\skills\sync-skills\sync.py
```

After that, all three supported agent CLIs (Claude Code, Codex, Gemini) discover the same slash commands. From inside Claude Code you can also run `/sync-skills` instead of the python command.

Then walk through [`docs/dayz-modding.md`](dayz-modding.md) for prerequisites (DayZ Tools, P:\ drive setup, vanilla data extraction) and the end-to-end workflow.

## Architecture — three layers

| Layer | Scope | Where it lives |
|---|---|---|
| **L1 — Default rules** | Apply to every clone, every agent, every skill. | `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (three filenames so each CLI finds its own; same content in each) |
| **L2 — DayZ conventions** | Apply when working inside the DayZ domain. | `.claude/skills/_shared/dayz-conventions.md` (core, read by every DayZ agent) plus topic files in `.claude/skills/_shared/conventions/` (config, assets, scripts, ui, server) loaded per task |
| **L3 — Specific agent or skill** | The actual unit of work. | `.claude/agents/<name>.md` or `.claude/skills/<name>/SKILL.md`, plus its scripts |

L3 files include a one-line reference to L2: *"Follow `.claude/skills/_shared/dayz-conventions.md`."*

## How agents and skills find their rules

When invoked on a task, an agent should:

1. Read the L1 file for the CLI in use (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
2. Read the specific agent or skill being run (L3).
3. If L3 references the DayZ conventions file (L2), read the core file and any topic files under `.claude/skills/_shared/conventions/` that L3 names.
4. Obey all three layers; the more specific layer wins ties.

## File structure

```
<repo>/
├── .claude/
│   ├── agents/                         # DayZ agent definitions (L3)
│   ├── skills/                         # skill definitions (L3) + L2 shared
│   │   ├── _shared/
│   │   │   ├── dayz-conventions.md     # L2 core rules for the DayZ domain
│   │   │   └── conventions/            # L2 topic files (config, assets, scripts, ui, server)
│   │   ├── sync-skills/                # bootstrap skill
│   │   │   ├── SKILL.md
│   │   │   ├── sync.py
│   │   │   └── agents.json             # list of agent CLIs to sync into
│   │   └── dayz-*/                     # one folder per DayZ skill
│   │       ├── SKILL.md
│   │       └── *.py
│   ├── agent-memory/                   # gitignored, per-agent memory written at runtime
│   ├── local-memory/                   # gitignored, per-clone: user/machine notes and skill state
│   └── settings.local.json             # gitignored, per-clone Claude Code settings
├── CLAUDE.md                           # L1 rules (Claude Code reads this)
├── AGENTS.md                           # L1 rules (Codex reads this)
├── GEMINI.md                           # L1 rules (Gemini reads this)
├── docs/                               # this folder
├── evals/                              # answer tests per agent (see docs/evals.md)
├── mods/agentic-z-panel/               # Claude Code panel plugin (one-click DayZ buttons)
├── scripts/                            # ad-hoc helper scripts
├── workspace/                          # in-progress mods (workspace/<ModName>/)
├── .server/                            # local test-server instances (.server/<instance>/)
└── output/                             # one-shot deliverables
```

## How to add things

### Add a new skill

1. Create `.claude/skills/my-skill/`.
2. Add `SKILL.md` with frontmatter (`name`, `description`) and a "How to run" section.
3. Add the actual script (e.g. `my-skill.py`).
4. Run `/sync-skills` to make it discoverable in all agent CLIs.

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
| **Path** | `<repo>/.claude/local-memory/` |
| **Committed?** | No (gitignored) |
| **Scope** | Per-clone — each project has its own; nothing leaks across clones |
| **Used for** | User/machine-specific notes and skill state: paths peculiar to your box, the cached author handle, and `/dayz-init`'s `dayz-current-project.txt` (the project root other DayZ skills read) and `dayz-init-state.json` (the active mod) |
| **Never used for** | Rules, conventions, project knowledge — those go in the repo at L1 (template-wide) or L2 (DayZ-specific) so they travel with every clone |

## Default rules in this template (L1)

The exact text lives in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`. Summary:

- **Communication — answer first, caveat after.** When asked for something an agent can't literally do, deliver the underlying answer via available tools and mention the limitation as a one-liner *after*, never as the lead.
- **Tooling — pick the fastest tool for the job.** Default to Python; cmd `.bat` for trivial wrappers; PowerShell only when explicitly asked or genuinely faster; Bash for trivial one-liners only; prefer dedicated `Read` / `Edit` / `Write` / `Grep` / `Glob` over shelling out.
- **Doc maintenance — plain copies.** `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` hold the same content. Edit all three together.
- **Bootstrap — run `/sync-skills` after cloning.** Required to make Codex and Gemini see the slash commands.
- **Memory — local-memory only, never for rules.** User/machine notes only; rules go in the repo.
- **Model routing — match model to task.** Searches/research → Sonnet subagent; trivial file-find → Haiku subagent; coding/design → main Opus thread. See [`docs/model-routing.md`](model-routing.md).
- **Prompt conventions — caps are a finite signal.** Uppercase section headers are structural; inline `MUST` / `NEVER` / `ALWAYS` are behavioral and measurably affect model compliance, but only when rare. See [`docs/prompt-conventions.md`](prompt-conventions.md).

## DayZ Modding workflow

Slash commands cover the complete mod lifecycle: setup wizard, env preflight, project scaffold + `P:\` junction, PBO build via DayZ Tools' AddonBuilder, server instance setup, local server+client launch, COT admin bootstrap, asset/types editing, and cleanup. Most skills gate on `/dayz-preflight` first per L2 conventions; the exceptions and their reasons are listed there.

### Front door

| Command | Purpose |
|---|---|
| [`/dayz-init`](../.claude/skills/dayz-init/SKILL.md) | Setup wizard on first run; status hub for the active mod on every run after. Dispatches to the other skills, never replaces them. |

### Bootstrap (one-time per machine)

| Command | Purpose |
|---|---|
| [`/dayz-preflight`](../.claude/skills/dayz-preflight/SKILL.md) | Verify environment (P:\ mounted, Tools installed, vanilla data extracted) |
| [`/dayz-workdrive`](../.claude/skills/dayz-workdrive/SKILL.md) | Mount `P:\` without opening DayZ Tools (auto-resolves work drive from `settings.ini`) |
| [`/dayz-setup-objectbuilder`](../.claude/skills/dayz-setup-objectbuilder/SKILL.md) | One-time machine setup for Object Builder (registry config + sane defaults) |

### Mod scaffolding

| Command | Purpose |
|---|---|
| [`/dayz-new-mod`](../.claude/skills/dayz-new-mod/SKILL.md) | Scaffold `workspace/<ModName>/` + create `P:\<ModName>\` junction |
| [`/dayz-import-mod`](../.claude/skills/dayz-import-mod/SKILL.md) | Symlink an existing mod folder into the workspace + create the junction |
| [`/dayz-add-scaffold`](../.claude/skills/dayz-add-scaffold/SKILL.md) | Add missing scaffold pieces (config.cpp stub, gproj, etc.) to an existing mod folder; `--piece junction` repairs a missing `P:\<ModName>\` link |
| [`/dayz-scope-mod`](../.claude/skills/dayz-scope-mod/SKILL.md) | Lock the agent to one mod via deny rules so it can't clobber siblings |

### Build

| Command | Purpose |
|---|---|
| [`/dayz-build-pbo`](../.claude/skills/dayz-build-pbo/SKILL.md) | Pack and deploy to `P:\Mods\@<ModName>\Addons\<ModName>.pbo` |
| [`/dayz-deploy-pbo`](../.claude/skills/dayz-deploy-pbo/SKILL.md) | Copy prebuilt PBOs and keys from a workspace bundle to `P:\Mods\@<ModName>\` without AddonBuilder |
| [`/dayz-pack-texture`](../.claude/skills/dayz-pack-texture/SKILL.md) | PNG/TGA → `.paa` via ImageToPAA. Validates the suffix against the vanilla set (`_co`, `_ca`, `_nohq`, `_smdi`, `_as`, `_mc` and more) |
| [`/dayz-build-imageset`](../.claude/skills/dayz-build-imageset/SKILL.md) | Pack `.gui-sources/<setname>/*.png` into a DayZ `.imageset` + `.paa` atlas with a 10px gutter; auto-splits into multiple parts when sprites won't fit in 4096x4096 |

### Test loop

| Command | Purpose |
|---|---|
| [`/dayz-add-server`](../.claude/skills/dayz-add-server/SKILL.md) | Set up a test server instance under `.server/<instance>/` |
| [`/dayz-launch-test`](../.claude/skills/dayz-launch-test/SKILL.md) | Start local Diag server + client with the mod loaded |
| [`/dayz-stop-test`](../.claude/skills/dayz-stop-test/SKILL.md) | Kill running DayZDiag_x64.exe processes (escape hatch, no preflight gate) |
| [`/dayz-cot-bootstrap`](../.claude/skills/dayz-cot-bootstrap/SKILL.md) | Two-pass workflow to grant COT admin perms on a fresh test instance |

### Gates, routing and status

| Command | Purpose |
|---|---|
| [`/dayz-gate`](../.claude/skills/dayz-gate/SKILL.md) | Run the build and in-game gates as scripts: build or deploy, launch, read the new log lines, triage failures against known errors |
| [`/dayz-lint`](../.claude/skills/dayz-lint/SKILL.md) | Find errors that would stop a mod loading, before packing, with `file:line` and an owner for each; runs first inside `/dayz-gate build` and `/dayz-build-pbo` |
| [`/dayz-route`](../.claude/skills/dayz-route/SKILL.md) | Pick the skill, agent or team for a request with keyword rules first; prints one JSON decision and says when the `dayz-router` agent is needed |
| [`/dayz-statusline`](../.claude/skills/dayz-statusline/SKILL.md) | Install a status line showing `P:\` mount, active mod, running diag session and search-index age; `--remove` undoes it |

### Editors

| Command | Purpose |
|---|---|
| [`/dayz-launch-workbench`](../.claude/skills/dayz-launch-workbench/SKILL.md) | Open Enfusion Workbench (script + UI editor) detached |
| [`/dayz-launch-objectbuilder`](../.claude/skills/dayz-launch-objectbuilder/SKILL.md) | Open Object Builder (`.p3d` editor) detached |

### Loot economy (`types.xml`)

| Command | Purpose |
|---|---|
| [`/dayz-edit-types`](../.claude/skills/dayz-edit-types/SKILL.md) | Programmatically upsert a single `<type>` in `types.xml` |
| [`/dayz-split-types`](../.claude/skills/dayz-split-types/SKILL.md) | Split monolithic `types.xml` into per-category files and point `cfgeconomycore.xml` at them |

### Specialist tools (deep)

| Command | Purpose |
|---|---|
| [`/dayz-p3d-audit`](../.claude/skills/dayz-p3d-audit/SKILL.md) | Audit `.p3d` models for collision, action targeting, physics, animation issues |
| [`/dayz-particles`](../.claude/skills/dayz-particles/SKILL.md) | Particle effect creation (`.ptc` / `.emat`) without Workbench |

### Search / RAG

| Command | Purpose |
|---|---|
| [`/dayz-search-download`](../.claude/skills/dayz-search-download/SKILL.md) | Pull prebuilt vector index from GitHub releases (recommended fast path) |
| [`/dayz-search-index`](../.claude/skills/dayz-search-index/SKILL.md) | Build the semantic-search index yourself (requires `VOYAGE_API_KEY`) |

### Team rules

| Command | Purpose |
|---|---|
| [`/dayz-record-correction`](../.claude/skills/dayz-record-correction/SKILL.md) | Turn your correction of the mod team into a written rule in the right tier |

### Cleanup

| Command | Purpose |
|---|---|
| [`/dayz-clean-workspace`](../.claude/skills/dayz-clean-workspace/SKILL.md) | Remove DayZ scaffolds and their deployed artifacts |

### Claude Code panel (separate plugin)

| Plugin | Purpose |
|---|---|
| [`agentic-z-panel`](../mods/agentic-z-panel/) | Panel beside the chat with DayZ state and one-click Mount, Build, Launch, Stop, Workbench and Object Builder buttons that run the skill scripts directly. Install with `/plugin install agentic-z-panel@dayz-n-chill`, open with `/dayz-panel` |

### Template maintenance (clone-only, not in plugin marketplace)

| Command | Purpose |
|---|---|
| [`/sync-skills`](../.claude/skills/sync-skills/SKILL.md) | Link `.claude/skills/` into each agent CLI's home dir. Required after clone |
| [`/agentic-z-update`](../.claude/skills/agentic-z-update/SKILL.md) | Pull upstream template improvements into your clone without touching `workspace/` |
| [`/docs-sync`](../.claude/skills/docs-sync/SKILL.md) | Detect drift between canonical sources and the Docusaurus wiki; `--apply` writes mirrors |
| [`/clean-repo`](../.claude/skills/clean-repo/SKILL.md) | Orchestrator — run every domain's cleanup skill |

**MCP server:** [`dayz-rag`](../.claude/mcp/dayz-rag/README.md) — exposes `search_dayz_source`, `get_dayz_file` and `list_indexed_sources` to the DayZ agents. Reads the LanceDB index under `~/.claude/dayz-search-index/`, built with `/dayz-search-index` or installed with `/dayz-search-download`.

**Native prereqs** (per machine, one-time install):

- **DayZ Tools** (Steam) — for AddonBuilder, WorkDrive, ImageToPAA
- **DayZ game** (Steam) — for the diag client used in `/dayz-launch-test`
- **DayZ Server** (Steam appid 223350) — only for the initial mission bootstrap; can be uninstalled after
- **Voyage AI API key** *(only for RAG)* — `VOYAGE_API_KEY` in `.env` powers `/dayz-search-index` and query-time embedding via `voyage-code-3`. A full source build embeds roughly 66M tokens, so check Voyage's pricing first. Or run `/dayz-search-download` to pull the maintainer's prebuilt index from GitHub releases instead of building locally.

L2 conventions: [`.claude/skills/_shared/dayz-conventions.md`](../.claude/skills/_shared/dayz-conventions.md) (core) and the topic files in [`.claude/skills/_shared/conventions/`](../.claude/skills/_shared/conventions/).

**Full walkthrough — prerequisites, quick start, env vars, troubleshooting:** [`docs/dayz-modding.md`](dayz-modding.md).

## DayZ agents

The 22 agents live under `.claude/agents/`. The mod team runs a whole mod; the specialists also take single tasks directly.

| Agent | Focus |
|---|---|
| `dayz-orchestrator` | Plans the build with you, splits it into tasks, tracks it to a test build |
| `dayz-router` | Haiku agent that picks one handler for a request when `/dayz-route` has no confident match |
| `dayz-mod-architect` | Designs the mod's classes, files and task list before work starts |
| `dayz-lead` | Runs one team's workers and its review gates |
| `dayz-build-checker` | Gate: the PBO builds with no AddonBuilder errors |
| `dayz-ingame-tester` | Gate: the mod loads on a diag server and client with clean logs |
| `dayz-build-engineer` | Builds, launches test sessions and deploys after your yes |
| `dayz-docs-writer` | Keeps the mod's README, changelog and classname list current |
| `dayz-asset-specialist` | `.p3d` / `.paa` / `.rvmat` and Workbench asset integration |
| `dayz-config-specialist` | `config.cpp`, CfgPatches, CfgVehicles, CfgWeapons, hidden selections |
| `dayz-map-specialist` | Terrain Builder, DayZ Editor, map objects, clutter, surfaces |
| `dayz-mod-debugger` | Log/RPT/crash analysis, BattlEye diagnosis, performance profiling |
| `dayz-mod-reviewer` | Audit `workspace/<ModName>/` for convention compliance; routes findings to the right specialist |
| `dayz-object-builder` | `.p3d` LODs, named selections, geometry, damage zones |
| `dayz-script-specialist` | Enforce Script — modded classes, RPCs, replication, gameplay logic |
| `dayz-server-admin` | `types.xml`, `init.c`, `cfggameplay.json`, server performance |
| `dayz-ui-specialist` | `.layout` files, widget scripting, HUD/menu, UI theme/color |
| `dayz-workbench-specialist` | Workbench plugin development (editor-time tooling) |
| `figma-node-normalizer` | Cleans a Figma frame so it can be converted |
| `figma-to-dayz-layout` | Turns a cleaned Figma frame into a DayZ `.layout` |
| `dayz-layout-validator` | Checks and cleans generated `.layout` files; the UI gate |

Plus `agent-creator` for scaffolding new agent definitions to the standard template.
