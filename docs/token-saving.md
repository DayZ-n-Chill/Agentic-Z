# Token-saving layer

Status: **shipped** (merged in PR #53).

## Why

Most of what the mod team does between "the user asks" and "the user sees a result" is mechanical: build, launch, read logs, decide who handles a task. Each of those steps costs model tokens today. This layer moves the mechanical parts into plain scripts, hooks and Claude Code features, so the model only spends tokens on judgment work: planning, writing code and configs, review, and real diagnosis.

## The pieces

| # | Piece | Replaces | Status |
|---|---|---|---|
| 1 | Script-only gates (`/dayz-gate`) | `dayz-build-checker` and `dayz-ingame-tester` agent runs | built |
| 2 | Log triage with known-error fingerprints | Debugger runs for errors seen before | built |
| 3 | Router: keyword rules, then a Haiku `dayz-router`, Jev when a TypeSafe key exists | Big-model routing of every request | built |
| 4 | Edit hooks: syntax check for `config.cpp` and `.layout`, other-mod guard; paste-in prompt hook | Failed review rounds caused by typos; model turns spent working out what was pasted | built |
| 5 | Status line | Agents and users running preflight just to check state | built |
| 6 | Cheaper models for simple roles | Top-model runs for mechanical agents | built |
| 7 | Smaller rules loading (Tier 2 split by topic) | Every DayZ agent loading the whole 239-line rules file | built |
| 8 | Launcher buttons (Claude Code mod) | Model turns to open Workbench, Object Builder, mount P:, stop a test | built |
| 9 | A no-token wrapper for every runnable skill | Asking Claude to run a script you could run yourself | built |
| 10 | Shorter skill and agent descriptions | Text loaded into every session | built |

## 1. Script-only gates

**What it is.** `/dayz-gate` (`skills/dayz-gate/gate.py`) runs the orchestrator's two DayZ gates as a script. It calls the existing skill scripts as subprocesses and applies the rules written in `dayz-build-checker` and `dayz-ingame-tester`:

- `build` first runs `/dayz-lint` on the mod. Its errors are failures and its warnings are warnings, and when lint fails the gate stops there, without stopping a running session or building. When lint passes, it stops any running `DayZDiag_x64.exe` (with `/dayz-stop-test`), runs `/dayz-build-pbo`, and fails on a non-zero exit, a `[FAIL]` line, or an AddonBuilder error or warning about missing files, textures or unknown classes. A payload-only bundle (no `config.cpp`, PBOs in `Addons/`) skips the build and must pass `/dayz-deploy-pbo` with no `[FAIL]` and no missing `.bisign`; a bundle with a linker `config.cpp` gets both.
- `ingame` stops any session, notes the size of every server and client log, runs `/dayz-launch-test`, and polls the new lines until the client script log shows `Creating Mission: mpmissions\__cur_mp.` (the vanilla print when the client joins) plus 30 s, or 5 minutes pass. It stops early on a script-module compile failure, a new crash log, or a server or client process exiting, and always stops the session. Then it judges only the new lines: compile errors, missing config entries, textures or models and crashes fail; `NULL pointer` and `Can't find` fail when they or their stack trace name the mod's folder, `$PBOPREFIX$` or classes. A line that names nothing of the mod is vanilla noise when it also appears in an older session without `@<ModName>`, and a warning when no such session exists.

**How to use it.** The orchestrator runs it per wave:

```cmd
python skills\dayz-gate\gate.py build MyVest --json
python skills\dayz-gate\gate.py ingame MyVest --deps CF --server chernarus --json
```

The first output line is `PASS` (exit 0), `FAIL` (exit 1) or `ERROR` (exit 2). The JSON lists each failure with its log file, line, stack trace, the mod files it points to, and its triage (section 2). On exit 2 (bad arguments, no cached project, a lint error that stops `/dayz-lint` from running at all, the stop step failed, or the gate crashed) the orchestrator falls back to the `dayz-build-checker` or `dayz-ingame-tester` agent; an exit 2 that asks for `--deps` is fixed by passing them.

**What it saves.** Two gate agent runs per wave, each of which read skill output and several log files into context. A passing wave now costs one command and a few lines of JSON; a failing one costs the failing lines only, deduplicated, with vanilla noise and warnings capped at 30 each.

**Limits.** The ready line assumes the vanilla mission flow; a mod that replaces it passes `--ready-pattern`. AddonBuilder messages are matched by keyword, not by a documented format. Dependencies are not derived from `requiredAddons`: the gate refuses (exit 2) when `config.cpp` needs non-vanilla addons and no `--deps` were given. It stops every `DayZDiag_x64.exe`, so it must not run while the user is playing a test session.

## 2. Log triage

**What it is.** `skills/dayz-gate/triage.py` fingerprints a log line (timestamps, absolute paths, hex addresses and numbers normalized, lowercased) and matches it against `known-errors.json`: entries `{id, pattern, meaning, fix, owner_agent, source}` seeded from the repo's documented errors (filePatching `0x00020005`, mission without `main()`, script module compile failures, unknown types, `Can't find`, undefined functions, `NULL pointer`, missing textures, models and config entries, and the build and launch refusals such as an unmounted `P:\`, a missing junction or a `$PBOPREFIX$` mismatch). Two entries check the mod's source instead of the log: a `modded class` with an extends clause, and a `config.cpp` without `CfgPatches`. Every gate failure comes back `known`, with the fix and the owning agent, or `new`.

**How to use it.** The gate runs it on every failure. The orchestrator sends `known` failures straight to the lead whose team has the owner (or runs the named skill itself, or tells the user when the owner is `user`), and only `new` ones to `dayz-mod-debugger`. On its own:

```cmd
python skills\dayz-gate\triage.py .server\chernarus\Profiles\script_2026-10-20_12-00-02.log --mod MyVest --mod-dir workspace\MyVest
python skills\dayz-gate\triage.py --learn null-pointer --fingerprint "<line or fingerprint>"
python skills\dayz-gate\triage.py --learn my-new-id --fingerprint "<line>" --meaning "..." --fix "..." --owner dayz-script-specialist
```

`--learn` writes to the project's `.claude/local-memory/dayz-gate-known-errors.json`, never to the shipped catalog.

**What it saves.** A debugger run, with its log reading, for every error the team has seen before. The fix reaches the right worker in the same turn as the gate verdict.

**Limits.** Regex entries match the first catalog hit, so order in `known-errors.json` matters. Learned entries match the exact fingerprint only. A known match names the usual cause; when the fix doesn't work, the second round should go to the debugger.

## 3. Router

**What it is.** `/dayz-route` decides who handles a new DayZ request (a skill, an agent, or the whole team) in up to three stages, cheapest first. Every stage returns the same JSON: `{"route", "kind": "skill|agent|team", "confidence": 0-1, "source": "rules|jev|router", "args"}`.

1. **Keyword rules** (`skills/dayz-route/rules.json`, free). Regex patterns per route: "build MyVest" goes to `/dayz-build-pbo` with `args.mod`, "launch the test" to `/dayz-launch-test`, "stop" to `/dayz-stop-test`, types.xml or spawn questions to `dayz-server-admin`, config.cpp to `dayz-config-specialist`, pasted crash log lines to `/dayz-gate` triage (then only the new ones to `dayz-mod-debugger`), a pasted `<type>` chunk to `/dayz-edit-types` merge, a GitHub or Workshop link to `/dayz-import-mod`, and "build me a ... mod" to the orchestrator. A request that matches two different routes counts as multi-step and is not trusted.
2. **Jev** (`jev.py`), only when `TYPESAFE_API_KEY` is set. One TypeSafe Choice question over the same targets plus `other`, with a 5 second timeout. Any failure falls through quietly, with the reason in `note`.
3. **`dayz-router` agent**, pinned to Haiku, with only `Read`. It returns the same JSON line.

**How to use it.** The main session runs it first for a new DayZ request (the routing section of `CLAUDE.md` says so):

```cmd
python skills\dayz-route\route.py "build MyVest" --json
```

A result with a `route` is followed directly. `{"route": null, "next": "dayz-router"}` means: dispatch the `dayz-router` agent with the request.

**What it saves.** Common requests (build, launch, stop, types.xml, config.cpp, crash logs, whole-mod builds) are routed by a script in milliseconds with no model tokens. The rest go to Jev or to a Haiku run instead of the top model.

**Limits.** Rules are English keywords, so unusual phrasing falls through to the later stages. The 0.8 threshold is a starting value, not tuned on real traffic. With a key set, the request text is sent to `api.typesafe.ai`. To add a route, edit `rules.json` and the list in `agents/dayz-router.md`; a test fails if they differ or if a target has no skill or agent file.

## 4. Edit hooks

Two Python hooks in `hooks/` run on every `Edit`, `Write` and `MultiEdit`. The plugin loads them from `hooks/hooks.json`; a clone of this repo loads the same scripts from `.claude/settings.json`. Each hook command runs `python` when it works and otherwise the `py` launcher (so the Microsoft Store alias, which exits 9009, is skipped); both hooks use no network and finish in about 0.1 s.

- **Syntax check** (`hooks/edit_check.py`, PostToolUse). After an edit to `config.cpp` (anywhere), a `.cpp` or `.hpp` under a `workspace/` folder, or a `.layout`, it re-reads the file and checks:
  - config files: balanced braces, `};` after every class body, `;` after every property and array, `[]` on array properties, `,` (not `;`) between array elements, closed strings and comments;
  - layouts: the brace format (XML is refused), balanced blocks, one root widget, child widgets inside the parent's bare `{ }` children block, properties inside a widget block.

  A clean file produces no output. On a problem, Claude gets each `file:line` and its fix next to the edit result and corrects it in the same turn. On a mounted P:\ it reports no false alarms on the 1,087 vanilla and community `config.cpp` and `.layout` files there (a `.hpp` outside `workspace/`, such as `P:\DZ\data\basicdefines.hpp`, is not checked).
- **Scope guard** (`hooks/scope_guard.py`, PreToolUse). While `/dayz-scope-mod <Mod>` is active (it writes `.claude/local-memory/dayz-active-scope.json`), any Edit, Write or MultiEdit to another mod's `workspace/<Other>/`, `P:\<Other>\` or `P:\Mods\@<Other>\`, and any Bash or PowerShell command whose redirect, copy, move, delete or in-place edit targets one, is denied with a reason that names the active mod and how to change scope. It backs up the deny rules `/dayz-scope-mod` writes, and also covers mod folders created after the scope was set: every other top-level `workspace/` folder counts as a mod, except helper folders whose names start with `_` (such as `workspace/_notes/`).

A third hook, the **paste-in router** (`hooks/paste_router.py`, UserPromptSubmit), runs on every prompt and only adds context; it never blocks one. It looks at what was pasted:

- DayZ error lines (a crash log, RPT or `script.log`) are triaged right in the hook against `/dayz-gate`'s known errors and the project's learned ones. The context lists each known error with its fix and owner, and the new lines, which are the only ones for `dayz-mod-debugger`.
- `<type name=...>` blocks are parsed and checked, and the context points at `/dayz-edit-types --merge` with any problems listed.
- A Figma link starts the Figma pipeline, a GitHub link points at `/dayz-import-mod --source <link>`, and a Steam Workshop link is refused with the reason (packed, binarized and often protected content).
- A screenshot (`[Image #n]`) gets the short rule: a UI problem to `dayz-ui-specialist`, a texture or material problem to `dayz-asset-specialist`, an error or wrong behavior to `dayz-script-specialist`.

Cheap regexes run first and the triage and `types.xml` code loads only for a matching paste, so a normal prompt costs about 0.1 s (mostly Python starting) and a 20,000 line log under a second. Any error inside the hook is swallowed.

Check a file by hand: `python hooks/edit_check.py --file workspace/MyMod/config.cpp` (prints problems, exits 1 when it finds any).

**Saves:** the review round, or the failed AddonBuilder or Workbench run, that a missing `;` or `}` otherwise costs, plus the tokens of reading the binarize error back. The model sees nothing when the file is clean.

**Limits:** it is a structure check, not a binarizer. It doesn't know class names, inheritance, value types or macro expansion (macro lines are skipped), and it skips files over 2 MB. A clone that also has the plugin installed wires each hook twice, but the plugin copy steps aside when the project has its own copy, so each problem is reported once.

## 5. Status line

`/dayz-statusline` puts one line of DayZ state under the prompt:

```text
P: mounted | mod MyVest | Diag off | RAG 3d old
```

That is whether `P:\` is mounted, the active mod from `/dayz-init`, whether a `DayZDiag_x64.exe` server or client is running, and how old the RAG search index is.

Install, check and remove it from the project root:

```cmd
python skills/dayz-statusline/install.py
python skills/dayz-statusline/install.py --status
python skills/dayz-statusline/install.py --remove
```

Install writes `statusLine` into `.claude/settings.local.json` after backing the file up to `settings.local.json.bak`. It is safe to re-run, and `--remove` restores any status line it replaced. A plugin can't set the main status line itself (plugin settings accept only `agent` and `subagentStatusLine`), which is why this is a skill. Plugin users re-run the install after a plugin update, because the plugin folder moves.

**Saves:** the preflight or hub run that an agent or user otherwise starts only to answer "is P: mounted, is a test running, which mod am I on". The status line costs no model tokens.

**Limits:** a run takes about 0.2 s, mostly Python start-up. The `P:\`, process and index checks are cached for 5 seconds, and the line refreshes every 10 seconds while idle. The process check is Windows-only; elsewhere it shows `Diag off`. Any error prints `DayZ status unavailable` instead of failing.

## 6. Cheaper models

Two release workers are pinned to cheaper models in their frontmatter, each with a comment marking it as a deliberate cost decision:

- `dayz-build-engineer` runs on `haiku`: it runs `/dayz-stop-test`, `/dayz-build-pbo`, `/dayz-deploy-pbo`, `/dayz-add-server` and `/dayz-launch-test` in a fixed order and quotes their output.
- `dayz-docs-writer` runs on `sonnet`: it writes plain docs, but its classname list depends on reading `config.cpp` inheritance and `scope` correctly, which is more than Haiku should be trusted with.
- `dayz-router` (piece 3) also runs on `haiku`.

Every other agent stays on the inherited session model because its output is judgment that later steps build on: the orchestrator, leads and architect plan the work, the specialists write code, configs and assets, and the gatekeepers (`dayz-mod-reviewer`, `dayz-mod-debugger`, `dayz-layout-validator`, `dayz-build-checker`, `dayz-ingame-tester`) decide pass or fail.

**Saves:** every release wave runs the build engineer and docs writer once per mod, so those runs now cost Haiku and Sonnet rates instead of the session model's.

**Limits:** a per-call `model` that the caller passes, or `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, overrides the pin (sub-agents docs, model precedence). If the build engineer starts misreading skill output, move it to `sonnet`.

## 7. Smaller rules loading

**What it is.** Tier 2 is split by topic. `skills/_shared/dayz-conventions.md` is now the short core every DayZ agent and skill reads: EnScript style pointer, environment and preflight gate, environment variables, the RAG index, project layout, testing basics, the search rule, and a topic index table. The topic sections moved verbatim into `skills/_shared/conventions/`:

| Topic file | Sections | Lines |
|---|---|---|
| `conventions/config.md` | Config conventions, `inventorySlot` string vs array, Bundle / umbrella mods | 52 |
| `conventions/assets.md` | Asset conventions, LOD canonical resolutions | 32 |
| `conventions/scripts.md` | Script conventions, Client and server ownership | 56 |
| `conventions/ui.md` | UI scripting realities, Reference packs for UI work | 24 |
| `conventions/server.md` | Server / economy, Test server instances (`.server/`), Mission and DayZ Server install notes | 27 |

**How to use it.** Each agent's Tier 2 line names the core file plus its topic files, for example `Follow Tier 2 (skills/_shared/dayz-conventions.md plus skills/_shared/conventions/scripts.md)`. Script, Workbench, AI and persistence specialists load `scripts.md`; config specialist, build checker, build engineer and wearables specialist `config.md`; the weapon specialist `config.md` (plus `scripts.md` for script it writes); asset, animation and physics specialists and object builder `assets.md`; UI specialist, Figma node normalizer, Figma-to-layout and layout validator `ui.md`; server admin, map specialist and in-game tester `server.md`; audio-FX and vehicle specialists `config.md` and `scripts.md`; the architect `scripts.md` and `assets.md`; the debugger `scripts.md` and `server.md`; the reviewer the topic files its change touches (usually config, assets and scripts). The orchestrator, lead and docs writer read the core only. A new rule goes in the core only when every DayZ agent needs it; otherwise in its topic file (`/dayz-record-correction` says so).

**What it saves.** Measured in lines of Tier 2 text loaded per agent run:

- Old file: 239 lines (22,655 characters, about 5,700 tokens). Core now: 143 lines (13,718 characters, about 3,400 tokens).
- Per agent, before and after: orchestrator, lead, docs writer 239 to 143 (40% less); script, Workbench, AI and persistence specialists 239 to 199 (17%); UI specialist, Figma node normalizer, Figma-to-layout, layout validator 239 to 167 (30%); server admin, map specialist, in-game tester 239 to 170 (29%); asset, animation and physics specialists, object builder 239 to 175 (27%); config specialist, build checker, build engineer, weapon and wearables specialists 239 to 195 (18%); debugger 239 to 226 (5%); architect 239 to 231 (3%); audio-FX and vehicle specialists 239 to 251 (5% more); reviewer with all three of its usual topics 239 to 283 (18% more).
- Across one run of each of the 28 agents that read Tier 2: 6,692 to 5,320 lines (21% less; 634,340 to 502,709 characters). Every DayZ skill reads only the core, so each skill load drops from 239 to 143 lines (40%).

**Limits.** The saving depends on agents loading only the topic files their line names; nothing enforces that. Each topic file carries a 4-line header, and the topic files have grown since the split, so an agent that loads every topic reads about 95 lines more than the old single file. The React wiki (`wiki/src/content/`) describes the core and the topic files by hand and does not mirror either one; `/docs-sync` checks that wiki against the source and does not copy these files.

## 8. Launcher buttons

**What it is:** `agentic-z-panel`, a Claude Code mod that ships as a second plugin in the same marketplace (`mods/agentic-z-panel/`). It adds a panel beside the chat with the DayZ state and one-click buttons. The buttons run the skill scripts directly, so none of them cost model tokens.

**Install:**

```text
/plugin install agentic-z-panel@dayz-n-chill
```

Then run `/dayz-panel` to open the panel.

**What the panel shows:** whether P: is mounted, the active mod (from `/dayz-init`), and whether a DayZ test session is running.

**Buttons (with keys while the panel has focus):**

| Button | Key | Runs |
|---|---|---|
| Mount P: | `p` | `dayz-workdrive/mount.py` |
| Build PBO | `b` | `dayz-build-pbo/build.py <active mod>` |
| Launch test | `l` | `dayz-launch-test/launch.py <active mod>` |
| Stop test | `s` | `dayz-stop-test/stop_test.bat` |
| Open Workbench | `w` | `dayz-launch-workbench/launch.py --mod <active mod>` |
| Open Object Builder | `o` | `dayz-launch-objectbuilder/launch.py` |
| Check test logs | `t` | `dayz-logwatch/logwatch.py --since 30 --duration 3 --mod <active mod>` |
| Health page | `h` | `dayz-health/health.py <active mod>` |
| Release pack | `k` | `dayz-release-pack/release_pack.py <active mod>` |
| Ask vanilla (a text field) | Enter | `dayz-ask/ask.py "<question>"` |
| Refresh | `r` | re-checks the state |

Each run shows a toast when it finishes and keeps the result line (the first `[FAIL]` line, or the last output line) in the panel.

**Where it finds Agentic-Z:** the clone that holds the session folder (that folder or its nearest parent with the Agentic-Z skills, so a session started in `workspace\MyVest` works), otherwise the newest version in the plugin cache.

**Limits:** Windows only, like the rest of Agentic-Z. Launch uses the default server instance; pick another with `/dayz-launch-test --server`. Checked with `claude plugin validate` and a test (`claude plugin test mods/agentic-z-panel`) that draws the panel on all four surfaces and presses Build. A second test presses the two check buttons, a third the logs, health and release pack buttons, and a fourth types a question into the ask field. The other tests press every remaining button, check that a second press while an action runs starts nothing, that the mod buttons only show a toast when there is no active mod, that the panel picks the newest plugin cache version by number, that a session started in a subfolder of the clone still finds it, that a press uses a mod picked with `/dayz-init` after the panel opened, that a plugin install finds the project state file above a subfolder, and that it says so when Agentic-Z is not found. CI runs pytest and the docs-sync check, not the panel tests, so `scripts/dev/test_repo_integrity.py` also checks that every script a button names exists.

**Version 0.2.0** adds three buttons: Check build (`c`, `/dayz-gate build`), Check in game (`g`, `/dayz-gate ingame`) and Deploy prebuilt PBOs (`d`, `/dayz-deploy-pbo`).

**Version 0.3.0** adds Check test logs (`t`, `/dayz-logwatch`), Health page (`h`, `/dayz-health`), Release pack (`k`, `/dayz-release-pack`) and an ask field (`/dayz-ask`). The logs button reads the session lines of the last 30 minutes once and stops after three seconds, so it returns like the other buttons; run `/dayz-logwatch --until-closed` to follow a whole session. The ask field shows the verdict and the first citations; the mobile app draws no text field, so it has no ask field there.

## 9. No-token wrappers

**What it is:** every skill that runs a script now has a `.bat` in `scripts\dayz\`, `scripts\setup\` or `scripts\dev\`. Run it from a terminal; no AI is involved. `scripts\README.md` lists all 45 with an example each.

**New in this pass:** `status.bat`, `gate.bat`, `triage.bat`, `route.bat`, `deploy-pbo.bat`, `cot-bootstrap.bat`, `build-imageset.bat`, `p3d-audit.bat` and `setup\statusline.bat`.

**Fixed:** `dayz-search.bat` (the terminal search over the RAG index) crashed on start because its script looked for the search server one folder too high. It runs again.

**Kept honest by tests:** the repo integrity test now fails if a wrapper points at a script that does not exist, or if a runnable skill has no wrapper. Only the two reference-only skills (`dayz-particles`, `dayz-record-correction`) have none, because they have no script.

**When to use the slash command instead:** when Claude should run the step inside a bigger task and read the result for you. The skill is the AI's manual for the script; the script is the same either way.

## 10. Shorter descriptions

**What it is:** Claude Code loads every skill and agent description into every session, so Claude knows they exist. The bodies load only when used. Every description was rewritten to say what it does and when to use it, without implementation detail, and each agent keeps one example instead of two or three.

**Saved (measured at commit 0ee441d, when the repo had 34 skills and 22 agents):** 31,301 characters down to 22,907, about 2,100 tokens off every session before any work starts.

| | Before | After |
|---|---|---|
| 34 skills | 12,848 | 9,246 |
| 22 agents | 18,453 | 13,661 |

Skills and agents added since then have brought the total back to about 35,100 characters (44 skills about 13,000; 30 agents about 22,100).

**Limits:** fourteen skill descriptions run 301 to 424 characters where cutting would drop a trigger phrase or a who-calls-whom fact (for example `dayz-p3d-audit`'s list of symptoms). Agent descriptions run 470 to 1,230 characters because each keeps one example.
