---
name: dayz-init
---

## Overview

Front door for all DayZ work in Agentic-Z. First run is a setup wizard (env check, intent prompts, plan, execute). Every run after drops you into a mission-control hub for the cached project. Wraps the existing /dayz-* skills, never replaces them.

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-init

The agent IS the wizard. Don't launch a separate Python wizard or new console — Claude Code's Bash tool is non-interactive, so any `input()`-driven Python wizard would hang. Instead, the agent orchestrates by:

1. Running the env check via Bash (read-only, no prompts).
2. Detecting whether setup is already complete; if so, jump straight to the hub.
3. Asking the user intent questions via **AskUserQuestion** (chat-native, no terminal copy-paste).
4. Running each underlying skill (`dayz-new-mod`, `dayz-add-server`, etc.) via Bash.
5. After execution, looping in a chat-based hub: show status block, ask "what now?" via AskUserQuestion, dispatch the chosen action.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## Step 1 — Setup-complete check

Run this via Bash to see if the cached project root exists and looks set up. If it prints a path, jump to **Step 6 (hub)**. If it prints nothing, fall through to Step 2.

```
python "<skill-dir>\check_setup.py"
```

## Step 2 — Environment check

Run the env check via Bash and capture output. The script exits 0 even on warnings; only hard-stop issues (no `P:\`, no DayZ Tools) require user action.

```
python "<skill-dir>\check_env.py"
```

- If the output contains `HARD` lines: tell the user what's broken and the steam:// or doc link, then stop. No further automation until they fix it and re-run.
- Otherwise: continue. Note any `AUTO` items (e.g. `P:\` not mounted, `P:\Mods\` junction missing) — they get added to the plan in Step 4.

## Step 3 — Intent prompts (AskUserQuestion)

Auto-derive defaults: mod name = cwd basename (sanitized), project path = cwd. Show those as the *first* option in each AskUserQuestion call so the user can accept with one click.

Batch into two calls (AskUserQuestion caps at 4 questions per call):

**Call A:** new vs. import; build PBO now; launch diag now; test server now.
**Call B (only if "test server now" = yes):** map (chernarus / livonia / sakhal / namalsk).
**Call C (only if `VOYAGE_API_KEY` not set):** RAG setup (skip / paste key / pull prebuilt).

For mod name and project path: if the cwd-derived defaults are sensible, use them silently. Only ask in chat ("What should the mod be called?") if the cwd basename is empty or ambiguous (e.g. `Agentic-Z` itself — that's the template root, not a mod).

If the user says "launch diag" but not "build PBO", auto-include build. State this in chat ("launch implies build, adding PBO step").

## Step 4 — Plan render

Print the ordered plan in chat — one bullet per step. Format:

```
Plan:
  • Mount P:\ (auto-fix)
  • Scaffold MyMod at G:\path\to\MyMod
  • Junction P:\MyMod\
  • Stage chernarus server
  • Build MyMod.pbo
  • Launch DayZDiag with MyMod on chernarus
```

No Y/N gate after this. Per `feedback_just_execute`: when the user has answered the intent questions, ship it. Confirmation is only for destructive/external actions, which scaffolding + junctioning are not.

## Step 5 — Execute

Run each step via Bash, in order. Stream the output. On the first non-zero exit, stop and tell the user which step failed and what the underlying skill said. Don't continue past a failure.

Mapping (step kind → command):

| Kind             | Command                                                                                          |
|------------------|--------------------------------------------------------------------------------------------------|
| `autofix:p_drive` | `python "<skill-dir>\..\dayz-workdrive\mount.py"`                                                   |
| `autofix:mods_junction` | `cmd /c mklink /J P:\Mods "<DayZ install>\!Workshop"`                                       |
| `scaffold`        | `python "<skill-dir>\..\dayz-new-mod\new_mod.py" <ModName> --path <project_path>`                  |
| `import_mod`      | `python "<skill-dir>\..\dayz-import-mod\import_mod.py" --source <project_path> --name <ModName>`   |
| `junction_mod`    | `cmd /c mklink /J P:\<ModName> <project_path>`                                                   |
| `stage_server`    | `python "<skill-dir>\..\dayz-add-server\add_server.py" <instance> --map <map>`                     |
| `build_pbo`       | `python "<skill-dir>\..\dayz-build-pbo\build.py" <ModName>`                                        |
| `launch_diag`     | `python "<skill-dir>\..\dayz-launch-test\launch.py" <ModName> --server <instance>`                 |

After all steps succeed, write the state file (caches the project root and records the intent choices):

```
python "<skill-dir>\save_state.py" <project_path> --rag <skip|paste|pull> --mod-name <name> --is-new <true|false> --server-map <map>
```

Omit `--server-map` if no test server was staged.

Then drop into Step 6.

## Step 6 — Hub loop

Render the status block via Bash:

```
python "<skill-dir>\hub_status.py" <project_path>
```

Then use AskUserQuestion to ask "what now?" with options matching the existing hub action list (build & launch, stop diag, tail log, open in workbench, open in objectbuilder, run mod reviewer, set voyage key, add test server, init another mod, switch project, quit). Dispatch the chosen action via Bash, then loop back to "what now?" until the user picks "quit".

Hub-action commands match the table in Step 5. For "tail log" and "stop diag" the dispatch is the corresponding standalone skill (`dayz-stop-test`, etc.).

## State file

`<project>/.agentic-z/state.json`. Tracks RAG decision, last build status, intent choices that disk inspection cannot derive. Setup completion is derived from disk, not the state file.

## When to fall back to direct CLI

Power users who want to bypass the AI orchestration can still run `python "<skill-dir>\init.py"` directly in their own terminal — the Python wizard is preserved as an escape hatch. But the agent never invokes it, because Bash subprocesses can't pass keystrokes to it.
