# Agentic-Z

**An AI Agent Stack for DayZ Modding**, with first-class support for Claude Code, Codex, and Gemini. Clone it to start a new DayZ mod, import a 3D model, set up a server, or tune the economy. Every project inherits opinionated rules, specialist agents, slash-command skills, and a semantic-search RAG over the vanilla engine source (Voyage AI `voyage-code-3` embeddings stored locally in LanceDB). Your AI shows up DayZ-fluent on day one.

## Quick start

```cmd
git clone <this-repo> my-mod
cd my-mod
python .claude\skills\sync-skills\sync.py
```

After that, all three supported agent CLIs (Claude Code, Codex, Gemini) discover the same slash commands: Claude Code through the installed agentic-z plugin (plus the four repo-only skills in `.claude/skills/`), Codex and Gemini through the links. From inside Claude Code you can also run `/sync-skills` instead of the python command.

Then walk through [`docs/dayz-modding.md`](dayz-modding.md) for prerequisites (DayZ Tools, P:\ drive setup, vanilla data extraction) and the end-to-end workflow.

## Architecture — three tiers

| Tier | Scope | Where it lives |
|---|---|---|
| **L1 — Default rules** | Apply to every clone, every agent, every skill. | `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (three filenames so each CLI finds its own; same content in each) |
| **L2 — DayZ conventions** | Apply when working inside the DayZ domain. | `skills/_shared/dayz-conventions.md` (core, read by every DayZ agent) plus topic files in `skills/_shared/conventions/` (config, assets, scripts, ui, server) loaded per task |
| **L3 — Agents and knowledge packs** | Loaded only when the task needs them. | `agents/<name>.md`, `skills/<name>/SKILL.md` plus its scripts, and the packs under `skills/_shared/` (EnScript patterns, Figma-to-DayZ rules) |

L3 files that do DayZ modding work include a one-line reference to L2: *"Follow `skills/_shared/dayz-conventions.md`."* Routing and utility files (for example `dayz-router`, `/dayz-route`, `/dayz-statusline`, `/sync-skills`) do not.

## How agents and skills find their rules

When invoked on a task, an agent should:

1. Read the L1 file for the CLI in use (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
2. Read the specific agent or skill being run (L3).
3. If L3 references the DayZ conventions file (L2), read the core file and any topic files under `skills/_shared/conventions/` that L3 names.
4. Obey all three tiers; the more specific tier wins ties.

## File structure

```
<repo>/
├── agents/                             # DayZ agent definitions (L3)
├── skills/                             # skill definitions (L3) + L2 shared
│   ├── _shared/
│   │   ├── dayz-conventions.md         # L2 core rules for the DayZ domain
│   │   └── conventions/                # L2 topic files (config, assets, scripts, ui, server)
│   └── dayz-*/                         # one folder per DayZ skill
│       ├── SKILL.md
│       └── *.py                        # helper scripts, when the skill has any
├── .claude/
│   ├── skills/                         # repo-only skills
│   │   └── sync-skills/                # bootstrap skill
│   │       ├── SKILL.md
│   │       ├── sync.py
│   │       └── agents.json             # list of agent CLIs to sync into
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

1. Create `skills/my-skill/`.
2. Add `SKILL.md` with frontmatter (`name`, `description`) and a "How to run" section.
3. Add the actual script (e.g. `my-skill.py`).
4. Add it to the `skills` list in `.claude-plugin/plugin.json` so the plugin ships it, and run `/sync-skills` so Codex and Gemini discover it. To test it in Claude Code before it is published, run `/sync-skills --agents claude`.

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
- **Scope — finish what was asked, then stop.** Keep going until the job is done properly, then stop instead of inventing new work. Graders and fixers fix only real mistakes: wrong facts, failing tests, docs that don't match the code, or bugs. "Would be nice" ideas go in [`docs/wishlist.md`](wishlist.md) and are never built during the job. Nothing the user didn't ask for is added without asking first.
- **Subagent routing — DayZ work goes to dayz-* specialists.** For a new DayZ request, run `/dayz-route` first; when it returns `next: dayz-router`, ask the `dayz-router` agent (Haiku) and follow its JSON. When a Superpowers workflow dispatches a subagent for DayZ work, use the matching `dayz-*` specialist instead of a generic agent. Role-to-specialist table in [`docs/dayz-modding.md`](dayz-modding.md).

Further reading (not L1 rules): [`docs/model-routing.md`](model-routing.md) for matching the model to the task, and [`docs/prompt-conventions.md`](prompt-conventions.md) for caps use: headings are plain sentence case and are for the reader, since their case doesn't change behavior; inline `MUST` / `NEVER` / `ALWAYS` can help an absolute rule stand out, but only when rare (a writing habit, not a measured result).

## DayZ Modding workflow

Slash commands cover the complete mod lifecycle: setup wizard, env preflight, project scaffold + `P:\` junction, PBO build via DayZ Tools' AddonBuilder, server instance setup, local server+client launch, COT admin bootstrap, asset/types editing, and cleanup. Most skills gate on `/dayz-preflight` first per L2 conventions; the exceptions and their reasons are listed there.

### Front door

| Command | Purpose |
|---|---|
| [`/dayz-init`](../skills/dayz-init/SKILL.md) | Setup wizard on first run; status hub for the active mod on every run after. Dispatches to the other skills, never replaces them. |

### Bootstrap (one-time per machine)

| Command | Purpose |
|---|---|
| [`/dayz-preflight`](../skills/dayz-preflight/SKILL.md) | Verify environment (P:\ mounted, Tools installed, vanilla data extracted) |
| [`/dayz-workdrive`](../skills/dayz-workdrive/SKILL.md) | Mount `P:\` without opening DayZ Tools (auto-resolves work drive from `settings.ini`) |
| [`/dayz-setup-objectbuilder`](../skills/dayz-setup-objectbuilder/SKILL.md) | One-time machine setup for Object Builder (registry config + sane defaults) |

### Mod scaffolding

| Command | Purpose |
|---|---|
| [`/dayz-new-mod`](../skills/dayz-new-mod/SKILL.md) | Scaffold `workspace/<ModName>/` + create `P:\<ModName>\` junction |
| [`/dayz-import-mod`](../skills/dayz-import-mod/SKILL.md) | Symlink an existing mod folder into the workspace + create the junction |
| [`/dayz-add-scaffold`](../skills/dayz-add-scaffold/SKILL.md) | Add missing scaffold pieces (config.cpp stub, gproj, etc.) to an existing mod folder; `--piece junction` repairs a missing `P:\<ModName>\` link |
| [`/dayz-recipe`](../skills/dayz-recipe/SKILL.md) | Start a plan from a recipe (new weapon, new vest, new craftable): classes, vanilla parents checked on `P:\`, files, tasks per team and behavior checks, for `dayz-mod-architect` to finish |
| [`/dayz-scope-mod`](../skills/dayz-scope-mod/SKILL.md) | Lock the agent to one mod via deny rules so it can't clobber siblings |

### Build

| Command | Purpose |
|---|---|
| [`/dayz-build-pbo`](../skills/dayz-build-pbo/SKILL.md) | Pack and deploy to `P:\Mods\@<ModName>\Addons\<ModName>.pbo` |
| [`/dayz-deploy-pbo`](../skills/dayz-deploy-pbo/SKILL.md) | Copy prebuilt PBOs and keys from a workspace bundle to `P:\Mods\@<ModName>\` without AddonBuilder |
| [`/dayz-pack-texture`](../skills/dayz-pack-texture/SKILL.md) | PNG/TGA → `.paa` via ImageToPAA. Validates the suffix against the vanilla set (`_co`, `_ca`, `_nohq`, `_smdi`, `_as`, `_mc` and more) |
| [`/dayz-build-imageset`](../skills/dayz-build-imageset/SKILL.md) | Pack `.gui-sources/<setname>/*.png` into a DayZ `.imageset` + `.paa` atlas with a 10px gutter; auto-splits into multiple parts when sprites won't fit in 4096x4096 |
| [`/dayz-layout-preview`](../skills/dayz-layout-preview/SKILL.md) | Draw a `.layout` as PNGs at several screen sizes and flag widgets that fall off screen or have no area |

### Test loop

| Command | Purpose |
|---|---|
| [`/dayz-add-server`](../skills/dayz-add-server/SKILL.md) | Set up a test server instance under `.server/<instance>/` |
| [`/dayz-launch-test`](../skills/dayz-launch-test/SKILL.md) | Start local Diag server + client with the mod loaded |
| [`/dayz-stop-test`](../skills/dayz-stop-test/SKILL.md) | Kill running DayZDiag_x64.exe processes (escape hatch, no preflight gate) |
| [`/dayz-cot-bootstrap`](../skills/dayz-cot-bootstrap/SKILL.md) | Two-pass workflow to grant COT admin perms on a fresh test instance |
| [`/dayz-logwatch`](../skills/dayz-logwatch/SKILL.md) | Watch a test session's server and client logs and triage each new error line as it appears: a known error prints its fix and owner, a new one goes to `dayz-mod-debugger` |

### Gates, routing and status

| Command | Purpose |
|---|---|
| [`/dayz-gate`](../skills/dayz-gate/SKILL.md) | Run the build, in-game, behavior and visual gates as scripts: build or deploy, launch, read the new log lines, run a test mission that spawns and uses each new item, compare screenshots with stored baselines, triage failures against known errors |
| [`/dayz-lint`](../skills/dayz-lint/SKILL.md) | Find errors that would stop a mod loading, before packing, with `file:line` and an owner for each; runs first inside `/dayz-gate build` and `/dayz-build-pbo` |
| [`/dayz-conflict-check`](../skills/dayz-conflict-check/SKILL.md) | Find `$PBOPREFIX$`, path and class name collisions with CF, COT and Expansion from their configs and PBO headers, without extracting them; `--ingame` then runs the in-game gate with them loaded |
| [`/dayz-upgrade-guard`](../skills/dayz-upgrade-guard/SKILL.md) | Snapshot vanilla classes before a DayZ update, then list the mod classes whose vanilla parents changed and optionally rebuild the search index |
| [`/dayz-balance`](../skills/dayz-balance/SKILL.md) | Compare item stats (weight, health, damage, protection, capacity, quantity) with similar vanilla items on `P:\DZ\` and flag outliers with `file:line` |
| [`/dayz-route`](../skills/dayz-route/SKILL.md) | Pick the skill, agent or team for a request with keyword rules first; prints one JSON decision and says when the `dayz-router` agent is needed |
| [`/dayz-statusline`](../skills/dayz-statusline/SKILL.md) | Install a status line showing `P:\` mount, active mod, running diag session and search-index age; `--remove` undoes it |
| [`/dayz-health`](../skills/dayz-health/SKILL.md) | Write a mod's health page from the stored gate results: last build, last test, open findings and the history of every gate run |

### Editors

| Command | Purpose |
|---|---|
| [`/dayz-launch-workbench`](../skills/dayz-launch-workbench/SKILL.md) | Open Enfusion Workbench (script + UI editor) detached |
| [`/dayz-launch-objectbuilder`](../skills/dayz-launch-objectbuilder/SKILL.md) | Open Object Builder (`.p3d` editor) detached |

### Loot economy (`types.xml`)

| Command | Purpose |
|---|---|
| [`/dayz-edit-types`](../skills/dayz-edit-types/SKILL.md) | Add, update or remove one `<type>` in `types.xml`, or check and merge a pasted chunk of entries (backs the file up first when it changes) |
| [`/dayz-split-types`](../skills/dayz-split-types/SKILL.md) | Split monolithic `types.xml` into per-category files and point `cfgeconomycore.xml` at them |

### Release

| Command | Purpose |
|---|---|
| [`/dayz-release-pack`](../skills/dayz-release-pack/SKILL.md) | Write the Workshop description, a changelog entry from the mod's history, the classname list and server owner install notes in one go |
| [`/dayz-server-kit`](../skills/dayz-server-kit/SKILL.md) | Zip the `types.xml` entries, `cfgeconomycore.xml` lines, load order and the public `.bikey` for server owners; never packs a `.biprivatekey` |

### Specialist tools (deep)

| Command | Purpose |
|---|---|
| [`/dayz-p3d-audit`](../skills/dayz-p3d-audit/SKILL.md) | Audit `.p3d` models for collision, action targeting, physics, animation issues |
| [`/dayz-particles`](../skills/dayz-particles/SKILL.md) | Particle effect creation (`.ptc` / `.emat`) without Workbench |

### Search / RAG

| Command | Purpose |
|---|---|
| [`/dayz-search-download`](../skills/dayz-search-download/SKILL.md) | Pull prebuilt vector index from GitHub releases (recommended fast path) |
| [`/dayz-search-index`](../skills/dayz-search-index/SKILL.md) | Build the semantic-search index yourself (requires `VOYAGE_API_KEY`) |
| [`/dayz-ask`](../skills/dayz-ask/SKILL.md) | Answer a plain English question about vanilla DayZ with `path:line` citations checked against `P:\`; falls back to a keyword search when there is no index or key |

### Team rules

| Command | Purpose |
|---|---|
| [`/dayz-record-correction`](../skills/dayz-record-correction/SKILL.md) | Turn your correction of the mod team into a written rule in the right tier |

### Cleanup

| Command | Purpose |
|---|---|
| [`/dayz-clean-workspace`](../skills/dayz-clean-workspace/SKILL.md) | Remove DayZ scaffolds and their deployed artifacts |

### Claude Code panel (separate plugin)

| Plugin | Purpose |
|---|---|
| [`agentic-z-panel`](../mods/agentic-z-panel/) | Panel beside the chat with DayZ state and one-click Mount, Build, Check, Deploy, Launch, Stop, Workbench, Object Builder, test logs, health page and release pack buttons, plus an ask field for vanilla questions, that run the skill scripts directly. Install with `/plugin install agentic-z-panel@dayz-n-chill`, open with `/dayz-panel` |

### Template maintenance (clone-only, not in plugin marketplace)

| Command | Purpose |
|---|---|
| [`/sync-skills`](../.claude/skills/sync-skills/SKILL.md) | Link `skills/` and `.claude/skills/` into each agent CLI's home dir. Required after clone |
| [`/agentic-z-update`](../.claude/skills/agentic-z-update/SKILL.md) | Pull upstream template improvements into your clone without touching `workspace/` |
| [`/docs-sync`](../.claude/skills/docs-sync/SKILL.md) | Detect drift between canonical sources and the Docusaurus wiki; `--apply` writes mirrors |
| [`/clean-repo`](../.claude/skills/clean-repo/SKILL.md) | Orchestrator — run every domain's cleanup skill |

**MCP server:** [`dayz-rag`](../.claude/mcp/dayz-rag/README.md) — exposes `search_dayz_source`, `get_dayz_file` and `list_indexed_sources` to the DayZ agents. Reads the LanceDB index under `~/.claude/dayz-search-index/`, built with `/dayz-search-index` or installed with `/dayz-search-download`.

**Native prereqs** (per machine, one-time install):

- **DayZ Tools** (Steam) — for AddonBuilder, WorkDrive, ImageToPAA
- **DayZ game** (Steam) — for the diag client used in `/dayz-launch-test`
- **DayZ Server** (Steam appid 223350) — only for the initial mission bootstrap; can be uninstalled after
- **Voyage AI API key** *(only for RAG)* — `VOYAGE_API_KEY` in `.env` powers `/dayz-search-index` and query-time embedding via `voyage-code-3`. The last full source build embedded about 66M tokens (52,048 chunks, before windowing); the current indexer produces about 62K chunks, and its local estimate of about 96M tokens runs high. Check Voyage's pricing first. Or run `/dayz-search-download` to pull the maintainer's prebuilt index from GitHub releases instead of building locally.

L2 conventions: [`skills/_shared/dayz-conventions.md`](../skills/_shared/dayz-conventions.md) (core) and the topic files in [`skills/_shared/conventions/`](../skills/_shared/conventions/).

**Full walkthrough — prerequisites, quick start, env vars, troubleshooting:** [`docs/dayz-modding.md`](dayz-modding.md).

## DayZ agents

The 30 agents live under `agents/`. The mod team runs a whole mod; the specialists also take single tasks directly.

| Agent | Focus |
|---|---|
| `dayz-orchestrator` | Plans the build with you, splits it into tasks, tracks it to a test build |
| `dayz-router` | Haiku agent that picks one handler for a request when `/dayz-route` has no confident match |
| `dayz-mod-architect` | Designs the mod's classes, files and task list before work starts |
| `dayz-lead` | Runs one team's workers and its review gates |
| `dayz-build-checker` | Gate: the PBO builds with no AddonBuilder errors |
| `dayz-ingame-tester` | Gate: the mod loads on a diag server and client with clean logs |
| `dayz-build-engineer` | Builds the PBO (or deploys a bundle's PBOs), sets up the test server and launches a test session for you to play |
| `dayz-docs-writer` | Keeps the mod's README, changelog and classname list current, and writes the Workshop text and server kit with `/dayz-release-pack` and `/dayz-server-kit` |
| `dayz-asset-specialist` | `.paa` textures via `/dayz-pack-texture` and `.rvmat` materials (hands `.p3d` and `model.cfg` to `dayz-object-builder`) |
| `dayz-config-specialist` | `config.cpp`, CfgPatches, CfgVehicles, inheritance, hidden selections |
| `dayz-map-specialist` | Terrain Builder, DayZ Editor, map objects, clutter, surfaces |
| `dayz-mod-debugger` | Traces failures in `script.log`, RPT, `crash.log` and BattlEye logs to a file and line and names the worker who fixes it; fixes nothing |
| `dayz-mod-reviewer` | Audit `workspace/<ModName>/` for convention compliance; routes findings to the right specialist |
| `dayz-object-builder` | `.p3d` LODs, named selections, geometry, damage zones |
| `dayz-script-specialist` | Enforce Script — modded classes, RPCs, replication, gameplay logic |
| `dayz-server-admin` | Mission and economy files: `types.xml`, `events.xml`, `cfgeventspawns.xml`, `cfgeconomycore.xml`, `cfgspawnabletypes.xml`, `cfggameplay.json`, `init.c`; receives the persistence data audit |
| `dayz-ui-specialist` | `.layout` files, widget scripting, HUD/menu, UI theme/color |
| `dayz-workbench-specialist` | Workbench plugin development (editor-time tooling) |
| `dayz-persistence-specialist` | Data that survives a server restart: save and load code, save versions, base building, the data audit before release |
| `dayz-ai-specialist` | Infected, animals and human AI such as patrols and guards |
| `dayz-vehicle-specialist` | Cars, boats and helicopters |
| `dayz-weapon-specialist` | Weapons, magazines, ammo, attachments, recoil and fire modes |
| `dayz-wearables-specialist` | Clothing, characters, inventory slots, protection, color variants and proxies |
| `dayz-animation-specialist` | `model.cfg` animations, RTM files and the Blender handoff |
| `dayz-audio-fx-specialist` | Sound shaders, sound sets and particle effects; any lead can call it |
| `dayz-physics-specialist` | Weight, collision LODs, dropping, throwing and contact; any lead can call it |
| `figma-node-normalizer` | Cleans a Figma frame so it can be converted |
| `figma-to-dayz-layout` | Turns a cleaned Figma frame into a DayZ `.layout`, and repairs one the validator failed |
| `dayz-layout-validator` | Checks generated `.layout` files without editing them; the UI gate |

Plus `agent-creator` for scaffolding new agent definitions to the standard template.
