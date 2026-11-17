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
| **L1 — Default rules** | Apply to every clone, every agent, every skill. | `.claude/CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (three filenames so each CLI finds its own; same content in each) |
| **L2 — DayZ conventions** | Apply when working inside the DayZ domain. | `skills/_shared/dayz-conventions.md` (core, read by every DayZ agent) plus topic files in `skills/_shared/conventions/` (config, assets, scripts, ui, server) loaded per task |
| **L3 — Agents and knowledge packs** | Loaded only when the task needs them. | `agents/<name>.md`, `skills/<name>/SKILL.md` plus its scripts, and the knowledge packs under `skills/_shared/` (EnScript patterns, Figma-to-DayZ rules and one pack per topic, indexed in `skills/_shared/README.md`) |

L3 files that do DayZ modding work include a one-line reference to L2: *"Follow `skills/_shared/dayz-conventions.md`."* Routing and utility files (for example `dayz-router`, `/dayz-route`, `/dayz-statusline`, `/sync-skills`) do not.

## How agents and skills find their rules

When invoked on a task, an agent should:

1. Read the L1 file for the CLI in use (`.claude/CLAUDE.md` / `AGENTS.md` / `GEMINI.md`).
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
│   │   ├── conventions/                # L2 topic files (config, assets, scripts, ui, server)
│   │   ├── README.md                   # index of every knowledge pack file
│   │   ├── <topic>/                    # knowledge packs: vehicles, models, animation, ... (L3)
│   │   ├── knowledge/                  # cross-cutting DayZ notes pack (L3)
│   │   └── scripts/                    # shared helper scripts (Linux and API index helpers)
│   └── <skill>/                        # one folder per skill (most are dayz-*)
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
├── .claude/CLAUDE.md                   # L1 rules (Claude Code reads this)
├── AGENTS.md                           # L1 rules (Codex reads this)
├── GEMINI.md                           # L1 rules (Gemini reads this)
├── docs/                               # this folder
├── evals/                              # answer tests per agent, plus the mechanical cases/ and the live/ cases (see docs/evals.md)
├── mods/agentic-z-panel/               # Claude Code panel plugin (one-click DayZ buttons)
├── scripts/                            # ad-hoc helper scripts
│   ├── setup/, dayz/, dev/             # .bat wrappers around the skills, grouped by audience
│   ├── tools/                          # offline Python tools (see docs/knowledge-pack-tools.md)
│   └── dev/knowledge-pack/             # packctl: validation, packaging and promotion tooling (see docs/knowledge-pack-maintenance.md)
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

The exact text lives in `.claude/CLAUDE.md` / `AGENTS.md` / `GEMINI.md`. Summary:

- **Communication — answer first, caveat after.** When asked for something an agent can't literally do, deliver the underlying answer via available tools and mention the limitation as a one-liner *after*, never as the lead.
- **Tooling — pick the fastest tool for the job.** Default to Python; cmd `.bat` for trivial wrappers; PowerShell only when explicitly asked or genuinely faster; Bash for trivial one-liners only; prefer dedicated `Read` / `Edit` / `Write` / `Grep` / `Glob` over shelling out.
- **Doc maintenance — plain copies.** `.claude/CLAUDE.md`, `AGENTS.md`, `GEMINI.md` hold the same content. Edit all three together.
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

### Reference and pipeline skills

Most of these 41 skills are reference skills: the agent loads one when a task touches its topic, and reads the reference file the skill points at. Some also ship offline scripts. [`compatibility-matrix.md`](compatibility-matrix.md) says which DayZ build each skill that has a row there was checked on and how.

#### Vehicles

| Command | Purpose |
|---|---|
| [`/dayz-vehicles`](../skills/dayz-vehicles/SKILL.md) | Check a ground or water vehicle model offline (get-in memory points, seat selections, wheel axis, drawn sections and bone references in a binarized model) and find the right file of the vehicle pack |
| [`/dayz-motorbikes`](../skills/dayz-motorbikes/SKILL.md) | Reference for motorbikes in DayZ 1.30: `MotorbikeScript`, the two-wheel simulation, kickstand, kickstart and pick-up actions and the motorbike HUD |
| [`/dayz-aviation`](../skills/dayz-aviation/SKILL.md) | Reference for planes, seaplanes and helicopters on a `CarScript` base: flight physics in script, flight inputs, rotor and control surface animation, cockpit dials and buoyancy |
| [`/rip-vehicle-import`](../skills/rip-vehicle-import/SKILL.md) | Guide for importing a ripped racing-game car with moving doors, hood and trunk into a drivable DayZ car: contract deltas, check allowlist, visual signoff and a classification viewer |

#### Models, textures and 3D

| Command | Purpose |
|---|---|
| [`/dayz-model-pipeline`](../skills/dayz-model-pipeline/SKILL.md) | Build a complete DayZ object from scratch or from an outside mesh: geometry in headless Blender, a `.p3d` assembled with py3d, textures, `.rvmat`, `model.cfg` and the config entries |
| [`/dayz-p3d-inspector`](../skills/dayz-p3d-inspector/SKILL.md) | Extract every LOD, memory point, selection and named property of a `.p3d` into one JSON, edit memory points in a 3D viewer, and build a new `.p3d` from it |
| [`/dayz-3d-viewer`](../skills/dayz-3d-viewer/SKILL.md) | Turn an MLOD `.p3d` with its `.paa` and `.rvmat` files into a `.glb` and a standalone HTML viewer; convert `.paa` to `.png` |
| [`/dayz-proxy-align`](../skills/dayz-proxy-align/SKILL.md) | Read the proxies of an MLOD `.p3d`, align them in a browser editor against the worn clothing, and write them back with py3d |
| [`/dayz-texture-pipeline`](../skills/dayz-texture-pipeline/SKILL.md) | Plan, write and check texture and material work: which map each suffix needs, `.rvmat` authoring, hidden selection wiring and damage materials |
| [`/uv-clean-atlas`](../skills/uv-clean-atlas/SKILL.md) | Build clean UV atlases for hard-surface meshes with headless Blender, and audit any UV set for overlap, island count and density |
| [`/3d-generation-harness`](../skills/3d-generation-harness/SKILL.md) | Run a 3D model build as a gated pipeline: intake, research, plan with tests, build per component, adversarial review, fix loop and ship gate |
| [`/ai-3d-to-dayz`](../skills/ai-3d-to-dayz/SKILL.md) | Front end for AI-generated props: image or text to 3D, cleanup, retopology, UVs, normal bake, PBR maps and the handoff to `.p3d`, `.paa` and `.rvmat` |
| [`/blender-assembly`](../skills/blender-assembly/SKILL.md) | Rules and a helper library for building models in Blender through Blender MCP tools |
| [`/blender-visual-review`](../skills/blender-visual-review/SKILL.md) | Render a Blender model from several angles, check the images against a defect checklist, and confirm each fix by rendering the same angles again |

#### Animation, characters and clothing

| Command | Purpose |
|---|---|
| [`/dayz-animation-pipeline`](../skills/dayz-animation-pipeline/SKILL.md) | Produce and change DayZ animations end to end: `model.cfg` skeletons, `AnimationSources`, RTM and SEAnim files, the animation graphs, rider poses and weapons in hands |
| [`/blender-animation`](../skills/blender-animation/SKILL.md) | Author motion in a live Blender through the Blender MCP server: keyframes, poses, IK, cycles, physics bakes, preview renders and the `.txa` export for DayZ |
| [`/dayz-realistic-animation-director`](../skills/dayz-realistic-animation-director/SKILL.md) | Direct realistic DayZ animation from creation to in-game verification, with measurable motion contracts and stated evidence levels |
| [`/mixamo-retarget`](../skills/mixamo-retarget/SKILL.md) | Experimental: retarget Mixamo or any FBX or DAE animation onto a custom Blender rig, including the DayZ skeleton |
| [`/ardy-motion-generation`](../skills/ardy-motion-generation/SKILL.md) | Install and run NVIDIA ARDY locally under WSL2 to generate full-body locomotion for the DayZ survivor |
| [`/dayz-characters`](../skills/dayz-characters/SKILL.md) | Import and author humanoids on the vanilla character bases (infected, survivors, NPCs): rigging, weights, LODs, config and ragdoll, plus an offline winding gate |
| [`/dayz-clothing`](../skills/dayz-clothing/SKILL.md) | Build, fix and diagnose worn clothing (the `_m` and `_f` models): the worn model and `model.cfg` contract, a staged build, an alignment viewer and an FBX handoff |

#### World and game systems

| Command | Purpose |
|---|---|
| [`/dayz-basebuilding`](../skills/dayz-basebuilding/SKILL.md) | Reference for buildable structures on `BaseBuildingBase`: kits, the `Construction` config block, build and dismantle actions, the bit mask save and damage zones |
| [`/dayz-persistence`](../skills/dayz-persistence/SKILL.md) | Reference for persistence: `OnStoreSave` and `OnStoreLoad` streams, Community Framework ModStorage, format changes and rollback, sidecar JSON files |
| [`/rigorous-data-audit`](../skills/rigorous-data-audit/SKILL.md) | Audit procedure for mods where a bug loses player progression: mechanical checks, eight audit angles, and every finding verified against the real file |
| [`/dayz-doors`](../skills/dayz-doors/SKILL.md) | Reference for doors on buildings and static props: `class Doors`, the `model.cfg` skeleton and rotations, doors opened by a button, and the 1.30 lock rules |
| [`/dayz-underground`](../skills/dayz-underground/SKILL.md) | Reference for underground areas in DayZ 1.30: terrain holes, underground triggers and the player's underground state |
| [`/dayz-environment-hazards`](../skills/dayz-environment-hazards/SKILL.md) | Reference for the DayZ 1.30 hazards: sandstorm, heat stroke, dust agents and protective gear |
| [`/dayz-physics-engine`](../skills/dayz-physics-engine/SKILL.md) | Reference for engine physics in script: the `dBody` API, collision layers, raycasts, contact damage, thrown objects, ragdoll and fall damage |
| [`/dayz-sound-system`](../skills/dayz-sound-system/SKILL.md) | Reference for mod audio: `CfgSoundShaders` and `CfgSoundSets`, playing sound sets from script, sounds the server starts and the `NoiseSystem` |
| [`/dayz-weapons`](../skills/dayz-weapons/SKILL.md) | Reference for the entity side of a firearm: `.p3d` selections and memory points, the player bone remap, `CfgWeapons` inheritance, magazines and fire modes |
| [`/dayz-ai-patterns`](../skills/dayz-ai-patterns/SKILL.md) | Reference for AI behaviour patterns studied in the DayZ Expansion AI module: state machine, threat and targeting, pathfinding and groups, and the vanilla `NoiseSystem` |

#### Scripting, UI and workflow

| Command | Purpose |
|---|---|
| [`/enforce-script-reference`](../skills/enforce-script-reference/SKILL.md) | Deep reference for writing and reviewing Enforce Script: hard rules, compiler and runtime traps, script layers, memory, RPC, synced variables and timers |
| [`/dayz-ui-development`](../skills/dayz-ui-development/SKILL.md) | Reference for building UI: menus, HUD overlays, `.layout` files, widgets, `.styles`, imagesets, stringtables, Dabs Framework MVC and the 1.30 UI changes |
| [`/dayz-mod-dev`](../skills/dayz-mod-dev/SKILL.md) | Reading guide and rule set for developing a mod as a whole on DayZ 1.30 or later (vanilla, Community Framework, Expansion), on Windows or Linux |
| [`/dayz-mod-workflow`](../skills/dayz-mod-workflow/SKILL.md) | Protocol for implementing and debugging a mod: the client and server data map, API checks, a checklist per file type, the error catalog and the debug order |
| [`/dayz-feature-spec`](../skills/dayz-feature-spec/SKILL.md) | Define and quality-gate a feature before it is implemented: success criteria, Given/When/Then scenarios and a forward contract for every name the next phase uses |
| [`/dayz-test-ingame`](../skills/dayz-test-ingame/SKILL.md) | Reference for testing in the running game: the build, deploy and launch cycle with `-filePatching`, server and mission config, scripted test cells and the AutoTest mod |
| [`/dayz-mcp-verify`](../skills/dayz-mcp-verify/SKILL.md) | Test a mod in the running game through the dayz-mcp MCP server: spawn, capture, raycast and read telemetry, then write a PASS or FAIL report. Needs DayZ-MCP, which is optional and installed separately ([`dayz-mcp.md`](dayz-mcp.md)) |
| [`/dayz-pbo-reverse-engineering`](../skills/dayz-pbo-reverse-engineering/SKILL.md) | Study a mod somebody else built: classify its PBOs from their headers, extract them with ExtractPbo, and sweep for patterns with a `path:line` ledger |
| [`/systematic-debugging`](../skills/systematic-debugging/SKILL.md) | Find the root cause of a failure before any fix is proposed: observe, trace, test one hypothesis, make one change |
| [`/task-observer`](../skills/task-observer/SKILL.md) | Watch a work session for ways to improve skills: log corrections and repeated workflows as observations, and review them into staged skill updates |

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
| [`/agentic-z-update`](../.claude/skills/agentic-z-update/SKILL.md) | Pull the latest template improvements into your clone without touching `workspace/` |
| [`/docs-sync`](../.claude/skills/docs-sync/SKILL.md) | Detect drift between canonical sources and the React wiki; `--apply` writes mirrors |
| [`/clean-repo`](../.claude/skills/clean-repo/SKILL.md) | Orchestrator — run every domain's cleanup skill |

**MCP server:** [`dayz-rag`](../.claude/mcp/dayz-rag/README.md) — exposes `search_dayz_source`, `get_dayz_file` and `list_indexed_sources` to the DayZ agents. Reads the LanceDB index under `~/.claude/dayz-search-index/`, built with `/dayz-search-index` or installed with `/dayz-search-download`.

**Native prereqs** (per machine, one-time install):

- **DayZ Tools** (Steam) — for AddonBuilder, WorkDrive, ImageToPAA
- **DayZ game** (Steam) — for the diag client used in `/dayz-launch-test`
- **DayZ Server** (Steam appid 223350) — only for the initial mission bootstrap; can be uninstalled after
- **Voyage AI API key** *(only for RAG)* — `VOYAGE_API_KEY` in `.env` powers `/dayz-search-index` and query-time embedding via `voyage-code-3`. The last full source build embedded about 66M tokens (52,048 chunks, before windowing); the current indexer produces about 62K chunks, and its local estimate of about 96M tokens runs high. Check Voyage's pricing first. Or run `/dayz-search-download` to pull the maintainer's prebuilt index from GitHub releases instead of building locally.

L2 conventions: [`skills/_shared/dayz-conventions.md`](../skills/_shared/dayz-conventions.md) (core) and the topic files in [`skills/_shared/conventions/`](../skills/_shared/conventions/).

**Full walkthrough — prerequisites, quick start, env vars, troubleshooting:** [`docs/dayz-modding.md`](dayz-modding.md).

## Knowledge packs

Tier 3 reference files under `skills/_shared/`, loaded one file at a time when a task needs it. [`skills/_shared/README.md`](../skills/_shared/README.md) is the index of every pack file; each pack folder's own `README.md` says which file answers which question. Facts about the game cite the vanilla file on `P:\` by path and line.

| Pack | Covers |
|---|---|
| `_shared/enscript-style.md` and `_shared/enscript-style/` | Enforce Script code style |
| `_shared/enscript/` | Enforce Script patterns, API notes and worked examples |
| `_shared/vehicles/` | Cars, boats, helicopters, planes and motorbikes: import, config, `model.cfg`, doors, lights, get-in, build and debug |
| `_shared/models/` | LODs, memory points, selections, proxies, named properties, UV mapping and texturing with several `.rvmat` files |
| `_shared/animation/` | `model.cfg` animations, RTM files and the animation graph |
| `_shared/wearables/` | Clothing, characters, slots and proxies |
| `_shared/weapons/` | Weapon config and classes, magazines and ammo, attachments, recoil and fire modes, muzzle effects |
| `_shared/persistence/` | Save and load, versioning and migration, base building, the data audit |
| `_shared/physics/` | Weight, collision, dropping, throwing and contact |
| `_shared/audio-fx/` | Sound config, the sound engine API and effects |
| `_shared/textures/` | Texture suffixes, `.rvmat` materials and checking the look |
| `_shared/ai/` | Infected, animals and human AI |
| `_shared/knowledge/` | Cross-cutting notes: mission lifecycle, script networking, the native surface, Workbench scripting, DayZ 1.30 build history, working rules |
| Single files in `_shared/` | Answer formatting, `Container_Base`, Figma to DayZ rules, py3d MLOD notes, Linux and Proton, skill resolution |

Skills also carry their own packs in `<skill>/references/`.

## Tools, evals and other docs

| Path | What it holds |
|---|---|
| `scripts/tools/` | The offline Python tools: the script validator `/dayz-lint` runs as its second stage, py3d for DayZ `.p3d` files, model, layout and animation-format checkers, and viewers. [`knowledge-pack-tools.md`](knowledge-pack-tools.md) says what each does and picks one by symptom or task |
| `scripts/dev/knowledge-pack/` | The validation, packaging and promotion tooling (`packctl`) with its tests. [`knowledge-pack-maintenance.md`](knowledge-pack-maintenance.md) explains it |
| `evals/` | Answer tests per agent, plus the mechanical `cases/` and the `live/` cases. See [`evals.md`](evals.md) |
| [`compatibility-matrix.md`](compatibility-matrix.md) | Which DayZ build each skill with a row there was checked on and how |
| [`dayz-mcp.md`](dayz-mcp.md) | The optional DayZ-MCP server for in-game automation, installed separately |
| [`knowledge-pack-product-spec.md`](knowledge-pack-product-spec.md) | The product definition for the reference skills and tools, with what is finished and what is open |
| [`knowledge-pack-authoring-lessons.md`](knowledge-pack-authoring-lessons.md) | Rules for writing skills, helper scripts and tests, each from a defect that shipped and was fixed |

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
| `dayz-vehicle-specialist` | Cars, boats, helicopters and motorbikes |
| `dayz-weapon-specialist` | Weapons, magazines, ammo, attachments, recoil and fire modes |
| `dayz-wearables-specialist` | Clothing, characters, inventory slots, protection, color variants and proxies |
| `dayz-animation-specialist` | `model.cfg` animations, RTM files and the Blender handoff |
| `dayz-audio-fx-specialist` | Sound shaders, sound sets and particle effects; any lead can call it |
| `dayz-physics-specialist` | Weight, collision LODs, dropping, throwing and contact; any lead can call it |
| `figma-node-normalizer` | Cleans a Figma frame so it can be converted |
| `figma-to-dayz-layout` | Turns a cleaned Figma frame into a DayZ `.layout`, and repairs one the validator failed |
| `dayz-layout-validator` | Checks generated `.layout` files without editing them; the UI gate |

Plus `agent-creator` for scaffolding new agent definitions to the standard template.
