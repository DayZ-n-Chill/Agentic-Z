# /dayz-init: onboarding wizard + mission-control hub

**Status:** design
**Date:** 2026-05-06
**Branch:** TBD (currently brainstormed on `feature/cleanup`; will likely land on its own feature branch off develop)

## Problem

Onboarding into Agentic-Z today is a six-command chain run against a wall of unfixed prerequisites:

```
/dayz-preflight
/dayz-set-project <abs-path>
/dayz-new-mod MyMod    OR  /dayz-import-mod --source <path>
/dayz-add-server chernarus
/dayz-build-pbo MyMod
/dayz-launch-test MyMod --server chernarus
```

Five distinct UX defects in this chain:

1. **Prerequisite cliff.** Before the first command runs, the user has to install DayZ, DayZ Tools, DayZ Server, mount `P:\`, junction `P:\Mods\` to `!Workshop`, extract vanilla data, and install Python. Most give up before `/dayz-preflight`.
2. **No discoverability between commands.** Each skill ends silently. The user has to keep the README open to know what comes next.
3. **First-success is too far from install.** Six commands minimum, even on the happy path.
4. **Failure messages do not point at fixes.** `P:\ not mounted` reports the symptom and stops; nothing offers to mount it.
5. **Optional vs required is unclear.** Is `/dayz-set-project` one-time? Does `/dayz-search-download` block other commands? Users guess.

The current docs work around this by being long. The actual fix is to compress the first-run experience into a single discoverable command and let it ask for what it needs.

## Goals

- A single command (`/dayz-init`) is the front door for all DayZ work in Agentic-Z.
- First run sets up one mod end-to-end: env autofix, scaffold (or import), project cache, optional test-server stage, optional build, optional launch.
- Every subsequent run drops the user into a mission-control hub showing project state and the actions they typically want next.
- The wizard never forces an action the user did not opt into. Server stage, PBO build, and diag launch are all yes/no prompts during the intent phase.
- The 24 existing slash skills stay usable standalone. `/dayz-init` orchestrates them; it does not replace them.
- Re-runs are idempotent. After a hard prereq miss or a mid-execution failure, re-running picks up where it left off.

## Non-goals

- **Per-skill output formatting** (success/failure messages on individual `/dayz-*` skills) is a separate UX pass.
- **Agent definitions, RAG, the wiki, the website (`agentic-z.com`)** are unchanged by this work.
- **No first-run hooks or auto-fire behavior.** The plugin install does not silently launch anything; the user types `/dayz-init` themselves. Discoverability comes from the README, the plugin description, and gating error messages on stateful skills.
- **No replacement of existing skills.** `/dayz-build-pbo`, `/dayz-launch-test`, `/dayz-stop-test`, and friends remain standalone-callable.
- **No multi-mod hub view.** The hub shows the cached project. `init another mod` and `switch project` are menu items, not a separate UI.

## Solution shape

`/dayz-init` is a stateful command with two visible phases:

| Phase | When it runs | What it does |
|---|---|---|
| **Setup wizard** | First run, or any run before required steps complete | Asks intent, presents plan, runs steps the user opted into |
| **Mission-control hub** | Every run after required steps complete | Shows project status, offers actions, returns to hub on completion |

Both phases live behind the same command name. The user does not switch modes; they always type `/dayz-init` and the command picks the right view based on disk state.

## Decisions made

The brainstorm walked through eight strategic calls. Each is recorded below with the reasoning so future readers can re-evaluate when context shifts.

### 1. Single wizard command, not signposting or auto-healing alone

Considered: keep the six-command chain but add "next: /dayz-X" lines (signpost), or run an auto-healing preflight only. Picked the wizard because the prereq cliff plus the chain length plus the discoverability gap are all fixed by collapsing the first-run experience into one command. Signposting alone leaves the prereq cliff. Auto-healing alone leaves the chain.

### 2. Pure prompt-driven, zero positional args

Considered: positional mod name with prompt-for-the-rest, or smart-detect from cwd. Picked pure prompts because (a) `/dayz-init` is invoked rarely per project so prompt friction is acceptable, (b) the prompts double as discoverability for what knobs exist, (c) Brian's stated preference: "user input is really going to be needed".

### 3. Plan-then-go consent, not per-step confirmation

Considered: a y/N gate before every action (most explicit), or single-confirmation after a printed plan. Picked plan-then-go because per-step gates contradict the existing "don't ask redundant confirmation questions" rule, and the plan summary itself is the consent surface ("here is everything I am about to do, OK?").

### 4. Hard prereq miss: stop + Steam link + idempotent re-run

Considered: pause-and-poll until prereqs appear. Picked stop-and-resume because Steam app installs can run for 20+ minutes and locking the Claude session that long is a non-starter. Re-runs are idempotent so the user is not penalized for the extra command.

### 5. After first-run success: hub mode, not exit

Considered: pure init that exits with `already set up`, or hint-card-on-exit. Picked hub mode because the user's primary follow-on actions (rebuild, relaunch, tail logs, open Workbench) are far more frequent than re-init. Anchoring all of them behind `/dayz-init` makes the command meaningful every time the user types it.

### 6. Hub layout: rich status, flat 10-action menu

Considered: lean menu with submenu for less-common actions. Picked rich-and-flat because the user benefits from seeing full state at a glance (PBO age, server status, diag PID, RAG mode, audit recency). Flat menu means one keystroke to anything; submenus add a layer for the sake of saving vertical pixels.

### 7. Mid-execution failure: stop, surface, resume

Considered: roll-back to clean slate, or recovery menu (retry / skip / open file / bail). Picked stop-and-resume because (a) it matches the existing "stop and surface errors immediately" rule, (b) the hub itself is exactly the recovery menu (after the wizard fails and exits, re-running `/dayz-init` shows the hub with current state and the user picks the obvious next action), (c) roll-back throws away successful work and is destructive in cases where the user might have already started editing.

### 8. Wizard scope ends at setup; build and launch are opt-in

Considered: wizard always ends in a launched diag, or always ends after build. Picked opt-in because (a) new mods would attempt to build a stub `config.cpp` that does not yet have meaningful content, (b) the user might not want a chernarus server specifically, (c) the wizard's job is "set up the working environment", not "decide testing strategy". The user opts into server stage, PBO build, and diag launch via prompts; the plan reflects only what they accepted.

## Detailed flows

### First-run, happy path (full opt-in)

```
/dayz-init

── Environment ──
✓ Python 3.11.7
✓ DayZ Tools found
✓ Vanilla data extracted
! P:\ not mounted, will mount
! P:\Mods\ junction missing, will create

── Intent ──
? Are you  › starting a new mod
            importing an existing repo
? Mod name           [MyMod]              ← cwd basename for new; CfgPatches class name for import
? Project path       [G:\repos\MyMod]     ← cwd
? Set up a test server?  [Y/n] y
? Map?                   [chernarus]
? Build PBO now?         [y/N] y
? Launch DayZ now?       [y/N] y
? RAG setup          › skip for now           ← only asked if VOYAGE_API_KEY is not already set
                       paste Voyage key
                       pull prebuilt index

── Plan ──
  • Mount P:\, junction P:\Mods\
  • Scaffold MyMod at G:\repos\MyMod
  • Junction P:\MyMod\, cache project
  • Stage chernarus server
  • Build MyMod.pbo
  • Launch DayZDiag with mod loaded
Continue? [Y/n] y

── Execute ──
[1/6] Mounting P:\               ✓
[2/6] Junctioning P:\Mods\       ✓
[3/6] Scaffolding MyMod          ✓
[4/6] Junctioning P:\MyMod\      ✓
[5/6] Staging chernarus server   ✓
[6/6] Building MyMod.pbo         ✓

→ drops into hub
```

### First-run, minimal path (server only, no build, no launch)

```
[same env + intent prompts, with build=N and launch=N]

── Plan ──
  • Mount P:\, junction P:\Mods\
  • Scaffold MyMod at G:\repos\MyMod
  • Junction P:\MyMod\, cache project
  • Stage chernarus server
Continue? [Y/n] y

[1/4] ... [4/4] ✓
Setup complete.

→ drops into hub
```

### Hub on first arrival (after minimal-path setup)

```
── /dayz-init  •  MyMod ──
Path:    G:\repos\MyMod
PBO:     not built yet
Server:  chernarus, staged (not running)
Diag:    not running
RAG:     skipped
Audit:   never run

Edit your mod files, then:

? what now
 › build & launch
   stop diag
   tail server log
   open in workbench
   open in objectbuilder
   run mod reviewer
   set voyage key
   init another mod
   switch project
   quit
```

### Hub when no server was staged

If the user said no to server stage during init, the hub shows `Server: not configured` and the menu adds an `add test server` action. The `build & launch` action prompts inline ("no server configured, set one up first?") if the user picks it without one.

```
── /dayz-init  •  MyMod ──
Path:    G:\repos\MyMod
PBO:     not built yet
Server:  not configured
...

? what now
 › build & launch       ← prompts to set up server first if missing
   add test server      ← appears when none configured
   open in workbench
   ...
```

### Hard prereq miss

```
/dayz-init

── Environment ──
✓ Python 3.11.7
✗ DayZ Tools not installed
✗ Vanilla data not extracted

Can't proceed. Need to fix:

  1. DayZ Tools (Steam app, free)
     steam://install/830640
     Open Steam now? [Y/n] y
     (opening...)

  2. Vanilla data extracted to P:\
     After Tools installs, run it once:
     → Tools menu → Extract Game Data

When done, re-run: /dayz-init
(I'll pick up where I left off.)
```

### Mid-execution failure

```
[5/6] Staging chernarus server   ✓
[6/6] Building MyMod.pbo         ...

✗ AddonBuilder failed:
  config.cpp line 14: undefined base class 'ItemBaseFoo'

Stopped at step 6/6.
Done so far is preserved.
  • Project cached
  • Scaffold + junctions
  • Server staged
  • PBO not built
  • Diag not launched

Fix config.cpp, then re-run: /dayz-init
(I'll drop you into the hub; pick "build & launch" to retry.)
```

The recovery model is state-based, not in-flight-plan-based. After the wizard exits, the user re-runs `/dayz-init`, the command sees that required setup is complete, and drops into the hub. The hub shows `PBO: build failed at 12:04, see G:\repos\MyMod\.server\addonbuilder.log`. From there, `build & launch` retries.

This is why the hub design and the failure model were chosen together. The hub IS the recovery menu.

## Hub action behavior

Each hub menu pick wraps an existing slash skill or composite of skills. After completion, control returns to the hub.

| Menu item | Wraps | Confirms? | Notes |
|---|---|---|---|
| `build & launch` | `/dayz-build-pbo` then `/dayz-launch-test` | no | Default-selected on hub entry. Prompts inline if no server configured. |
| `stop diag` | `/dayz-stop-test` | yes | Destructive enough to warrant a single y/N. |
| `tail server log` | streams `<project>/.server/<instance>/server-profiles/script.log` | no | Read-only. ctrl-c returns to hub. |
| `open in workbench` | `/dayz-launch-workbench --mod <Name>` | no | Detached spawn. |
| `open in objectbuilder` | `/dayz-launch-objectbuilder --mod <Name>` | no | Detached spawn. |
| `run mod reviewer` | dispatches `dayz-mod-reviewer` agent | no | Output streams in main session, then returns. |
| `set voyage key` | prompts for key, writes `.env` at repo root, runs `/dayz-search-download` | no | Idempotent. |
| `add test server` | `/dayz-add-server <map>` | no | Only appears in menu when no server is configured. |
| `init another mod` | restarts the wizard, replaces cached project | yes | Destructive: clears the cache. |
| `switch project` | shows known projects (from disk markers), changes cache | no | Lists every dir under `P:\Mods\@*` with the agentic-z scaffold marker. |
| `quit` | exits hub | no | User can re-run `/dayz-init` any time. |

## Discoverability

Three surfaces only:

1. **README quickstart** rewrites to lead with `/dayz-init`. The current six-command block is replaced. The full chain is documented further down for reference, not for instruction.
2. **Plugin marketplace description** mentions `/dayz-init` as the entry.
3. **Gating error messages** on stateful skills point at `/dayz-init`. Examples:
   - `/dayz-build-pbo` without a cached project: "no project cached. Run /dayz-init to set up."
   - `/dayz-launch-test` without a staged server: "no server configured. Run /dayz-init to add one."

Non-stateful skills stay open: `/dayz-preflight`, `/dayz-search-download`, `/dayz-search-index`, `/dayz-workdrive` work standalone with no init prerequisite.

No first-run hooks, no auto-fire on plugin install, no welcome banner.

## Relationship to existing skills

| Existing skill | Status under `/dayz-init` |
|---|---|
| `/dayz-preflight` | Wizard runs it implicitly during env phase. Still standalone-callable. |
| `/dayz-set-project` | Wizard caches as a side effect. Standalone use becomes rare but supported. |
| `/dayz-workdrive` | Wizard runs implicitly when `P:\` is unmounted. Standalone-callable. |
| `/dayz-new-mod` | Wizard runs for the "new" intent. Standalone use still supported (e.g., scripted scaffolds). |
| `/dayz-import-mod` | Wizard runs for the "import" intent. Standalone use still supported. |
| `/dayz-add-scaffold` | Wizard runs after import if pieces are missing. |
| `/dayz-add-server` | Wizard runs if user opts in. Hub exposes via `add test server`. Standalone-callable for adding more servers. |
| `/dayz-build-pbo` | Hub wraps via `build & launch`. Standalone for headless rebuilds, CI. |
| `/dayz-launch-test` | Hub wraps via `build & launch`. Standalone for re-launching with different flags. |
| `/dayz-stop-test` | Hub wraps via `stop diag`. Standalone for emergency-stop. |
| `/dayz-launch-workbench` | Hub wraps via `open in workbench`. Standalone-callable. |
| `/dayz-launch-objectbuilder` | Hub wraps via `open in objectbuilder`. Standalone-callable. |
| `/dayz-search-download` | Hub wraps via `set voyage key`. Standalone-callable. |
| Other skills | Untouched. |

The wizard does not subsume any skill, even ones it always invokes. Every skill remains a first-class command. The wizard is an orchestrator with its own UX surface.

## Open questions

### Naming

Considered: `/dayz-init` (current pick), `/dayz` (clean but bare), `/dayz-go` (punchy, vague), `/dayz-mod` (verb-form, clean), `/dayz-hub` (explicit, ugly).

The case for keeping `/dayz-init`: precedent in `npm init`, `git init`. Familiar. Already on the table.

The case for renaming: hub mode runs forever. "Init" implies one-time setup. New users typing `/dayz-init` after initial setup might wonder if they are about to wipe state.

Resolution deferred. Implementation lands as `/dayz-init`. If the hub-mode-forever-after-init shape feels wrong in practice during dogfooding, we rename in a follow-up. The rename itself is cheap (skill folder, frontmatter, docs).

### State file format and recovery model

Wizard idempotency is **state-based, not plan-based.** The wizard and the hub both read disk state on startup (presence of scaffold markers, junctions, project cache, server staging, recent PBO, audit log timestamps). They do NOT persist an in-flight execution plan that gets resumed mid-step.

This means after a mid-execution failure, the wizard exits, the user re-runs `/dayz-init`, and the command sees "required setup is complete" and drops into the hub. The hub action the user picks (typically `build & launch`) is the retry.

A small state file at `<project>/.agentic-z/state.json` may still be useful for things disk inspection cannot easily express: last successful build timestamp, last AddonBuilder error message, RAG skip decision, etc. Format and exact contents to be decided in the implementation plan.

### "switch project" project discovery

Hub's `switch project` menu lists known agentic-z-scaffolded projects. Source of truth: scan `P:\Mods\@*\` for the `.agentic-z-scaffold` marker and read each marker for the project root path. Confirm during implementation that this scan is fast enough for hub responsiveness.

## Out of scope (explicit)

- Touching agent definitions, the dayz-rag MCP server, or the wiki.
- Per-skill stdout/stderr formatting.
- The agentic-z.com website.
- Replacing or deprecating any existing slash skill.
- Editor integration (VSCode hooks, etc.).
- Live RPT tail in a separate window. The hub's `tail server log` action streams in the same session.
- Multi-machine sync of cached project state.

## Implementation hints (for the writing-plans phase)

The plan should decompose into independent landable pieces:

1. **Wizard skeleton.** New skill at `.claude/skills/dayz-init/`. SKILL.md, `init.py` orchestrator. Implements env phase, intent prompts, plan rendering, plan execution. No hub mode yet. Calls existing skills as subprocesses or in-process.
2. **State file format and idempotency.** `<project>/.agentic-z/state.json` schema. Wizard reads on startup, decides whether to enter wizard or hub, resumes correctly after partial completion.
3. **Hub mode.** Status block rendering. Menu rendering. Action dispatch. Wraps existing skills.
4. **Gating in stateful skills.** Update `/dayz-build-pbo`, `/dayz-launch-test`, `/dayz-add-server` etc. to error with a pointer to `/dayz-init` when prereqs are missing.
5. **Discoverability changes.** README rewrite. Plugin marketplace description update.
6. **Migration / coexistence.** Existing users of the chained workflow are not broken. The wizard detects existing scaffolds and treats them as already-complete.

Each step is shippable on its own. Steps 1+2 together give a usable wizard without the hub. Step 3 adds the hub. Step 4 hardens the gating. Steps 5+6 polish the rollout.
