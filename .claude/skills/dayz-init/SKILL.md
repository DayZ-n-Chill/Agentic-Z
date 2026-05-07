---
name: dayz-init
description: Front door for all DayZ work in Agentic-Z. First run is a setup wizard (env check, intent prompts, plan, execute). Every run after drops you into a mission-control hub for the cached project. Wraps the existing /dayz-* skills, never replaces them.
---

# /dayz-init

Single command for everything onboarding-related. First run scaffolds (or imports) a mod, junctions `P:\<Mod>\`, caches the project root, optionally stages a test server, optionally builds a PBO, optionally launches the diag client. Every run after that drops into a hub showing project state with a flat action menu.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-init\init.py
```

No arguments. The wizard asks for everything it needs.

## What it does (first run)

1. Environment phase: detects `P:\` mount, DayZ Tools, vanilla data, Python, `P:\Mods\` junction. Auto-fixes what it can. Hard-stops with steam:// links for what it cannot.
2. Intent phase: prompts new vs import, mod name (default = cwd basename or CfgPatches class), project path (default = cwd), opt-in for server stage / PBO build / diag launch, RAG setup if no Voyage key.
3. Plan phase: prints every action it is about to take, asks one Y/N to continue.
4. Execute phase: runs each step, streams output, halts on first failure with a state-preserving exit.
5. Drops into the hub.

## What it does (subsequent runs)

Detects existing setup from disk markers and the state file. Drops directly into the hub: project status block plus a flat 10-action menu (build & launch, stop diag, tail log, open in workbench, etc.).

## State file

`<project>/.agentic-z/state.json`. Tracks RAG decision, last build status, intent choices that disk inspection cannot derive. Setup completion is derived from disk, not the state file.
