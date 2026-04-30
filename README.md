# Agentic-Z

**An AI Agent Stack for DayZ Modding** — clone it, and your repo comes pre-loaded with specialist agents, slash commands, and a local RAG index that turn Claude Code, Codex, or Gemini CLI into a competent DayZ modding co-author.

> **Branch note:** `DayZAgents` (this branch) is the DayZ-only build. The multi-domain template lives on a separate branch.

---

## What you get

- **11 DayZ specialist agents** covering scripts, configs, assets, maps, UI, server admin, debugging, and Workbench plugins.
- **21 slash-command skills** that drive DayZ Tools end-to-end — preflight, scaffold, build PBOs, launch a local diag server + client, manage `types.xml`, etc.
- **A semantic-search RAG** over the vanilla DayZ source (Enforce Script, configs, layouts, materials) plus the Bohemia community wiki, exposed to every agent through the `dayz-rag` MCP server. Embeddings via Voyage AI (`voyage-code-3`, 200M-token free tier covers ~3 full rebuilds). Or skip the build entirely with `/dayz-rag-download` and pull the prebuilt index from GitHub releases.
- **Three-CLI support out of the box.** The same agents and skills work in Claude Code, Codex CLI, and Gemini CLI. One `sync-skills` run wires them all up.

---

## Quick start

```cmd
git clone <this-repo> my-dayz-mod
cd my-dayz-mod
python .claude\skills\sync-skills\sync.py
```

That symlinks the repo's `.claude/skills/` into each agent CLI's home directory so all three discover the same slash commands. Inside Claude Code you can also run `/sync-skills` instead.

Then, from any of the agent CLIs:

```text
/dayz-preflight                       # verify env (P:\ mounted, Tools installed, vanilla data extracted)
/dayz-rag-download                    # pull prebuilt vanilla+wiki vector index from GitHub releases (~1 min)
/dayz-new-mod MyMod                   # scaffold workspace/MyMod/ + create P:\MyMod\ junction
/dayz-add-map chernarus               # set up a test map under workspace/_server/
/dayz-build-pbo MyMod                 # pack and deploy to P:\Mods\@MyMod\Addons\
/dayz-launch-test MyMod               # local diag server + client, mod loaded
```

`/dayz-rag-download` is optional but recommended for fresh clones — it avoids the ~25-30 min `/dayz-rag-index` build and the Voyage API token cost. Skip it if you're on a custom DayZ branch and need recall against your local source.

Full prerequisites, env-var overrides, and troubleshooting: **[`docs/dayz-modding.md`](docs/dayz-modding.md)**.

---

## Prerequisites (one-time, per machine)

| What | Why |
|---|---|
| **DayZ** (Steam) | The diag client (`DayZDiag_x64.exe`) ships next to retail and is what `/dayz-launch-test` runs. |
| **DayZ Tools** (Steam, free) | AddonBuilder, P-drive mounting, ImageToPAA. |
| **DayZ Server** (Steam, appid 223350) | Only for the initial mission template bootstrap; can be uninstalled afterward. |
| **`P:\` mounted** | Engine and Tools both read from `P:\`. Mount via DayZ Tools or `/dayz-mount-p`. Doesn't auto-mount across reboots. |
| **`P:\Mods\` junction → `<DayZ install>\!Workshop\`** | One-time `mklink /J` so built PBOs land where the engine actually loads mods. |
| **Vanilla data on `P:\`** | DayZ Tools → "Extract Game Data". Your configs inherit from `ItemBase`, `Inventory_Base`, etc. |
| **Python 3.8+** on `PATH` | The skills are Python scripts. |

RAG embeddings run through Voyage AI's hosted API (`voyage-code-3`, code-tuned, 1024-dim). A free Voyage account includes 200M tokens — enough for ~3 full rebuilds of the vanilla DayZ corpus. Add `VOYAGE_API_KEY=pa-…` to `.env` at the repo root before running `/dayz-rag-index`. If you'd rather skip the build entirely, `/dayz-rag-download` pulls the maintainer's prebuilt index from GitHub releases (~1 minute, no API key needed for download — but query-time embedding still needs the key).

---

## Architecture — three layers

| Layer | Scope | Where it lives |
|---|---|---|
| **L1 — Default rules** | Every clone, every agent, every skill. | `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (same content; one filename per CLI) |
| **L2 — DayZ conventions** | When working inside the DayZ domain. | `.claude/skills/_shared/dayz-conventions.md` |
| **L3 — Specific agent / skill** | The unit of work. | `.claude/agents/<name>.md` or `.claude/skills/<name>/SKILL.md` |

L3 files reference L2 in one line. The more specific layer wins ties.

---

## Repo layout

```
<repo>/
├── .claude/
│   ├── agents/             # 11 DayZ specialists + agent-creator + docs-wiki-sync (L3)
│   ├── skills/             # 20 slash-command skills (L3) + L2 shared conventions
│   │   ├── _shared/dayz-conventions.md
│   │   ├── sync-skills/    # bootstrap: link skills into Claude/Codex/Gemini home dirs
│   │   └── dayz-*/         # one folder per DayZ skill
│   ├── mcp/dayz-rag/       # local RAG MCP server (search_dayz_source, get_dayz_file, ...)
│   ├── agent-memory/       # per-agent committed memory
│   ├── local-memory/       # gitignored, per-clone, user/machine notes only
│   └── settings.local.json # per-clone Claude Code settings
├── CLAUDE.md / AGENTS.md / GEMINI.md   # L1 rules (one per CLI, same content)
├── docs/                   # deep docs (DayZ workflow, model routing)
├── wiki/                   # Docusaurus mirror of docs/agents/skills
├── workspace/              # in-progress mods (workspace/<ModName>/) and _server/
└── output/                 # one-shot deliverables
```

---

## DayZ skills (slash commands)

All gate on `/dayz-preflight` first per L2.

| Command | Purpose |
|---|---|
| [`/dayz-preflight`](.claude/skills/dayz-preflight/SKILL.md) | Verify env (P:\ mounted, Tools installed, vanilla data extracted). |
| [`/dayz-mount-p`](.claude/skills/dayz-mount-p/SKILL.md) | Mount `P:\` without opening DayZ Tools. |
| [`/dayz-new-mod`](.claude/skills/dayz-new-mod/SKILL.md) | Scaffold `workspace/<ModName>/` + `P:\<ModName>\` junction. |
| [`/dayz-build-pbo`](.claude/skills/dayz-build-pbo/SKILL.md) | Pack and deploy to `P:\Mods\@<ModName>\Addons\<ModName>.pbo`. |
| [`/dayz-add-map`](.claude/skills/dayz-add-map/SKILL.md) | Set up a test map under `workspace/_server/`. |
| [`/dayz-launch-test`](.claude/skills/dayz-launch-test/SKILL.md) | Local diag server + client with mod loaded. |
| [`/dayz-stop-test`](.claude/skills/dayz-stop-test/SKILL.md) | Kill running `DayZDiag_x64.exe` processes. |
| [`/dayz-launch-workbench`](.claude/skills/dayz-launch-workbench/SKILL.md) | Open Enfusion Workbench (script + UI editor) detached. |
| [`/dayz-launch-objectbuilder`](.claude/skills/dayz-launch-objectbuilder/SKILL.md) | Open Object Builder (`.p3d` editor) detached. |
| [`/dayz-setup-objectbuilder`](.claude/skills/dayz-setup-objectbuilder/SKILL.md) | One-time machine setup for Object Builder. |
| [`/dayz-pack-texture`](.claude/skills/dayz-pack-texture/SKILL.md) | PNG/TGA → `.paa` via ImageToPAA. Validates `_co` / `_nohq` / `_smdi` suffix. |
| [`/dayz-types-edit`](.claude/skills/dayz-types-edit/SKILL.md) | Programmatically upsert a single `<type>` in `types.xml`. |
| [`/dayz-types-split`](.claude/skills/dayz-types-split/SKILL.md) | Split monolithic `types.xml` into 18 categorized files. |
| [`/dayz-rag-index`](.claude/skills/dayz-rag-index/SKILL.md) | Build the vanilla-source semantic-search index. |
| [`/dayz-rag-wiki-index`](.claude/skills/dayz-rag-wiki-index/SKILL.md) | Index the Bohemia community wiki into the same DB. |
| [`/dayz-rag-download`](.claude/skills/dayz-rag-download/SKILL.md) | Pull prebuilt vector index from GitHub releases instead of building locally. |
| [`/dayz-clean-workspace`](.claude/skills/dayz-clean-workspace/SKILL.md) | Remove DayZ scaffolds and their deployed artifacts. |
| [`/clean-repo`](.claude/skills/clean-repo/SKILL.md) | Repo-wide cleanup orchestrator across every domain. |
| [`/sync-skills`](.claude/skills/sync-skills/SKILL.md) | Link `.claude/skills/` into each agent CLI's home dir. |
| [`/docs-sync`](.claude/skills/docs-sync/SKILL.md) | Detect drift between sources and the Docusaurus wiki. |

---

## DayZ specialist agents

| Agent | Focus |
|---|---|
| [`dayz-script-specialist`](.claude/agents/dayz-script-specialist.md) | Enforce Script — modded classes, RPCs, replication, gameplay logic. |
| [`dayz-config-specialist`](.claude/agents/dayz-config-specialist.md) | `config.cpp`, CfgPatches, CfgVehicles, CfgWeapons, hidden selections. |
| [`dayz-asset-specialist`](.claude/agents/dayz-asset-specialist.md) | `.p3d` / `.paa` / `.rvmat` and Workbench asset integration. |
| [`dayz-object-builder`](.claude/agents/dayz-object-builder.md) | `.p3d` LODs, named selections, geometry, damage zones. |
| [`dayz-map-specialist`](.claude/agents/dayz-map-specialist.md) | Terrain Builder, DayZ Editor, map objects, clutter, surfaces. |
| [`dayz-ui-specialist`](.claude/agents/dayz-ui-specialist.md) | `.layout` files, widget scripting, HUD/menu, UI theme. |
| [`dayz-server-admin`](.claude/agents/dayz-server-admin.md) | `types.xml`, `init.c`, `cfggameplay.json`, server performance. |
| [`dayz-mod-debugger`](.claude/agents/dayz-mod-debugger.md) | Log/RPT/crash analysis, BattlEye diagnosis, performance profiling. |
| [`dayz-mod-reviewer`](.claude/agents/dayz-mod-reviewer.md) | Audit `workspace/<ModName>/` for convention compliance; routes findings. |
| [`dayz-workbench-specialist`](.claude/agents/dayz-workbench-specialist.md) | Workbench plugin development (editor-time tooling). |
| [`docs-wiki-sync`](.claude/agents/docs-wiki-sync.md) | Keep `wiki/` in sync with canonical sources. |

Plus [`agent-creator`](.claude/agents/agent-creator.md) for scaffolding new agent definitions.

---

## Default rules (L1) at a glance

The full text lives in `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`.

- **Communication — answer first, caveat after.** Deliver the underlying answer via available tools; mention any limitation as a one-liner *after*, never as the lead.
- **Tooling — pick the fastest tool for the job.** Default Python; `cmd`/`.bat` for trivial Windows wrappers; PowerShell only when explicitly asked or genuinely faster; prefer dedicated `Read` / `Edit` / `Write` / `Grep` / `Glob`.
- **Doc maintenance — plain copies.** Edit `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` together.
- **Bootstrap — `/sync-skills` after cloning.** Required so Codex and Gemini see the slash commands.
- **Memory — `local-memory/` only, never for rules.** User/machine-specific notes only; rules go in the repo.
- **Model routing — match model to task.** Searches → Sonnet subagent; trivial file-find → Haiku; coding/design → main Opus thread. Details in [`docs/model-routing.md`](docs/model-routing.md).

---

## Documentation

- **[`docs/README.md`](docs/README.md)** — architecture overview, how to add skills/agents, local-memory rules.
- **[`docs/dayz-modding.md`](docs/dayz-modding.md)** — full DayZ workflow, prerequisites, env vars, troubleshooting.
- **[`docs/model-routing.md`](docs/model-routing.md)** — when to use Opus / Sonnet / Haiku and the subagent patterns.
- **[`docs/prompt-conventions.md`](docs/prompt-conventions.md)** — why agent and skill files use caps the way they do (RFC 2119 directives, when to cap, when to stay lowercase).
- **`wiki/`** — Docusaurus build of the docs (kept in sync via `/docs-sync`).

---

## Adding things

**A new skill:** create `.claude/skills/my-skill/`, add `SKILL.md` with `name`/`description` frontmatter and a "How to run" section, drop the script in. Run `/sync-skills` to make it discoverable in all agent CLIs.

**A new agent CLI:** append an entry to `.claude/skills/sync-skills/agents.json` and run `/sync-skills`. The new home gets links for every skill automatically.

---

## Community & contributing

**Join us on Discord: [discord.gg/dayznchill](https://discord.gg/dayznchill)**

Agentic-Z is built by and for the DayZ modding community, and contributions are **highly encouraged**. Every agent, skill, and convention in this repo started as a real problem someone hit while shipping a mod — the more modders contribute, the sharper the toolkit gets for everyone.

In the Discord you can:

- **Learn how to become a contributor.** New contributors are walked through the repo layout, the L1/L2/L3 rule structure, and how to land a first PR.
- **Propose new agents and skills.** If you keep solving the same problem by hand, that's a skill waiting to be written. Pitch it in Discord and we'll help shape it.
- **Report bugs and rough edges.** Path resolution quirks, AddonBuilder errors, agent prompts that miss the mark — all welcome.
- **Share what you've built.** Mods, server setups, custom agents, RAG indexes over your own assets. The toolkit improves fastest when people show what they shipped with it.
- **Help refine and enhance the product.** Docs improvements, troubleshooting entries, better defaults, new MCP integrations — every contribution compounds.

Whether you're a seasoned Enforce Script developer, a server admin, a 3D artist, or just learning DayZ modding for the first time, there's a place for your work here. The goal is a tool that makes DayZ modding accessible and enjoyable for everyone — and that only happens with community input.

---

## License

See [`LICENSE`](LICENSE). Copyright (c) 2026 Brian Orr (DayZ n' Chill). Free to use for developing DayZ modifications.
