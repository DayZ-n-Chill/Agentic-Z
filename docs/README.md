# Agentic-Z

**An AI Agent Stack for DayZ Modding**, with first-class support for Claude Code, Codex, and Gemini. Clone it to start a new DayZ mod, import a 3D model, set up a server, or tune the economy. Every project inherits opinionated rules, specialist agents, slash-command skills, and a local RAG over the vanilla engine source. Your AI shows up DayZ-fluent on day one.

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
| **L2 — DayZ conventions** | Apply when working inside the DayZ domain. | `.claude/skills/_shared/dayz-conventions.md` |
| **L3 — Specific agent or skill** | The actual unit of work. | `.claude/agents/<name>.md` or `.claude/skills/<name>/SKILL.md`, plus its scripts |

L3 files include a one-line reference to L2: *"Follow `.claude/skills/_shared/dayz-conventions.md`."*

## How agents and skills find their rules

When invoked on a task, an agent should:

1. Read the L1 file for the CLI in use (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
2. Read the specific agent or skill being run (L3).
3. If L3 references the DayZ conventions file (L2), read it.
4. Obey all three layers; the more specific layer wins ties.

## File structure

```
<repo>/
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
├── CLAUDE.md                           # L1 rules (Claude Code reads this)
├── AGENTS.md                           # L1 rules (Codex reads this)
├── GEMINI.md                           # L1 rules (Gemini reads this)
├── docs/                               # this folder
├── scripts/                            # ad-hoc helper scripts
├── workspace/                          # in-progress mods (workspace/<ModName>/)
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
| **Used for** | User/machine-specific notes only — paths peculiar to your box, email addresses, anything that doesn't belong in the repo |
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

The slash commands cover the complete mod lifecycle: env preflight, project scaffold + `P:\` junction, PBO build via DayZ Tools' AddonBuilder, server map setup, local server+client launch, and cleanup.

| Command | Purpose |
|---|---|
| [`/dayz-preflight`](../.claude/skills/dayz-preflight/SKILL.md) | Verify environment (P:\ mounted, Tools installed, vanilla data extracted) |
| [`/dayz-mount-p`](../.claude/skills/dayz-mount-p/SKILL.md) | Mount `P:\` without opening DayZ Tools (auto-resolves work drive from `settings.ini`) |
| [`/dayz-new-mod`](../.claude/skills/dayz-new-mod/SKILL.md) | Scaffold `workspace/<ModName>/` + create `P:\<ModName>\` junction |
| [`/dayz-build-pbo`](../.claude/skills/dayz-build-pbo/SKILL.md) | Pack and deploy to `P:\Mods\@<ModName>\Addons\<ModName>.pbo` |
| [`/dayz-add-map`](../.claude/skills/dayz-add-map/SKILL.md) | Set up a test map under `workspace/_server/` |
| [`/dayz-launch-test`](../.claude/skills/dayz-launch-test/SKILL.md) | Start local Diag server + client with the mod loaded |
| [`/dayz-stop-test`](../.claude/skills/dayz-stop-test/SKILL.md) | Kill running DayZDiag_x64.exe processes |
| [`/dayz-pack-texture`](../.claude/skills/dayz-pack-texture/SKILL.md) | PNG/TGA → `.paa` via ImageToPAA |
| [`/dayz-types-edit`](../.claude/skills/dayz-types-edit/SKILL.md) | Programmatically edit a single `<type>` in `types.xml` |
| [`/dayz-types-split`](../.claude/skills/dayz-types-split/SKILL.md) | Split monolithic `types.xml` into 18 categorized files |
| [`/dayz-rag-index`](../.claude/skills/dayz-rag-index/SKILL.md) | Build the semantic-search index over vanilla DayZ source (powers the `dayz-rag` MCP server) |
| [`/dayz-rag-wiki-index`](../.claude/skills/dayz-rag-wiki-index/SKILL.md) | Index the Bohemia community wiki into the same DB |
| [`/dayz-rag-download`](../.claude/skills/dayz-rag-download/SKILL.md) | Pull prebuilt vector index from GitHub releases instead of building locally |
| [`/dayz-clean-workspace`](../.claude/skills/dayz-clean-workspace/SKILL.md) | Remove DayZ scaffolds and their deployed artifacts |
| [`/clean-repo`](../.claude/skills/clean-repo/SKILL.md) | Orchestrator — run every domain's cleanup skill |
| [`/docs-sync`](../.claude/skills/docs-sync/SKILL.md) | Detect drift between canonical sources and the Docusaurus wiki; invoke `docs-wiki-sync` agent to apply updates |

**MCP server:** [`dayz-rag`](../.claude/mcp/dayz-rag/README.md) — exposes `search_dayz_source`, `get_dayz_file`, `list_indexed_sources` to every DayZ specialist agent. Backed by the index built via `/dayz-rag-index`.

**Native prereqs** (per-clone, one-time install):

- **DayZ Tools** (Steam) — for AddonBuilder, WorkDrive, ImageToPAA
- **DayZ game** (Steam) — for the diag client used in `/dayz-launch-test`
- **DayZ Server** (Steam appid 223350) — only for the initial mission bootstrap; can be uninstalled after
- **Voyage AI API key** *(only for RAG)* — `VOYAGE_API_KEY` in `.env` powers `/dayz-rag-index` and query-time embedding via `voyage-code-3` (200M-token free tier covers ~3 full rebuilds). Or run `/dayz-rag-download` to pull the maintainer's prebuilt index from GitHub releases instead of building locally.

L2 conventions: [`.claude/skills/_shared/dayz-conventions.md`](../.claude/skills/_shared/dayz-conventions.md).

**Full walkthrough — prerequisites, quick start, env vars, troubleshooting:** [`docs/dayz-modding.md`](dayz-modding.md).

## DayZ agents

Specialist agents live under `.claude/agents/` and cover the major DayZ surfaces:

| Agent | Focus |
|---|---|
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
| `docs-wiki-sync` | Keep `wiki/` (Docusaurus) in sync with canonical docs/agents/skills sources; default model: sonnet |

Plus `agent-creator` for scaffolding new agent definitions to the standard template.
