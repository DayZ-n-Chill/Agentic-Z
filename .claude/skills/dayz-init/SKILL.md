---
name: dayz-init
description: Front door for DayZ work in an Agentic-Z clone. On first run it checks the environment, asks a few setup questions, then scaffolds or imports a mod, records it as the active mod and optionally sets up a test server, builds and launches. Later runs show a status hub and dispatch actions to the existing /dayz-* skills. Use when the user starts DayZ modding in a clone, says "init" or "set up DayZ", or wants a status overview and next action for their mod.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-init

The agent is the wizard: it runs the scripts below with Bash and asks the user questions with AskUserQuestion. None of the scripts prompt for input. Every action goes through the sibling skill that owns it; this skill never re-implements them.

Follow `.claude/skills/_shared/dayz-conventions.md`. This skill does not gate on `/dayz-preflight` itself, because its own environment check covers the same ground and also fixes `P:\` first. Every child skill it runs gates on preflight.

State is per clone, in `.claude/local-memory/` (gitignored): `dayz-current-project.txt` (the project root other DayZ skills read) and `dayz-init-state.json` (the active mod). The project root is the clone: `$CLAUDE_PROJECT_DIR`, else the current directory. Mods live in `workspace/<ModName>/`, test servers in `.server/<instance>/`.

## Step 1: setup check

```
python "<skill-dir>\check_setup.py"
```

If it prints a path, setup is done: go to Step 6. If it prints nothing, continue.

## Step 2: environment check

```
python "<skill-dir>\check_env.py"
```

Read-only. Prints `OK`, or one line per issue (always exits 0):

- `AUTO p_drive`: `P:\` is not mounted. Mount it now without asking (non-destructive), then re-run `check_env.py`, because the `P:\` checks are skipped while it is unmounted:
  ```
  python "<skill-dir>\dispatch.py" mount-p
  ```
  If the mount fails, show its output and stop.
- `HARD <name> ...`: DayZ Tools missing, vanilla data not extracted, `P:\Mods` the wrong shape (or missing with no DayZ install found), or Python too old. Tell the user what is wrong and the fix or link on the line, then stop. They re-run `/dayz-init` after fixing it.

A missing `P:\Mods` is not an issue when the DayZ install's `!Workshop` folder exists: `/dayz-preflight`, which the first child skill in Step 5 runs, creates the junction.

## Step 3: setup questions

Ask with one AskUserQuestion call (up to 4 questions), putting the usual choice first:

1. New mod or import an existing mod folder?
2. Test server: chernarus, livonia, sakhal, or none. Other maps need `/dayz-add-server` with the mission folder name.
3. Build the PBO now? (yes / no)
4. Launch DayZ Diag now? (yes / no; only offered when a server was picked; launching implies building)

Then ask in chat for the free-text values:

- Mod name (letters, digits and underscores, starting with a letter). For an import, offer the source folder's name as the default.
- Import only: the source folder path, and whether to write missing scaffold pieces into it (`--scaffold`) or only link it (`--no-scaffold`).
- New mod only, when `.claude/local-memory/dayz-author.txt` does not exist: the author handle shown in mod descriptions.

## Step 4: show the plan

```
python "<skill-dir>\plan.py" --mod <ModName> [--import-from <path> --scaffold|--no-scaffold] [--author <handle>] [--server <map>] [--build] [--launch]
```

Prints the numbered plan, for example:

```
Plan:
  1. Scaffold workspace\MyMod
  2. Record MyMod as the active mod
  3. Set up the chernarus test server
  4. Build MyMod.pbo
  5. Launch DayZ Diag with MyMod on chernarus
```

Scaffolding or importing is skipped when `workspace\<ModName>\` already exists (a folder or a link, including a `--no-scaffold` import that has no `config.cpp` yet), so re-running `/dayz-init` for an existing mod just makes it active. Show the plan in chat. Don't ask for a yes/no: the user already chose everything in it, and none of it is destructive.

## Step 5: run the plan

Same command plus `--execute`. Each step's output streams through; the first failing step stops the run, and the script exits with that step's exit code. Tell the user which step failed and what the child skill said. Exit 2 means the environment check failed again or a value was missing.

| Step | Runs |
|---|---|
| new-mod | `dayz-new-mod\new_mod.py <ModName> [--author <handle>]` |
| import-mod | `dayz-import-mod\import_mod.py --source <path> --name <ModName> --scaffold\|--no-scaffold` |
| record | writes the two state files above |
| add-server | `dayz-add-server\add_server.py <map> --map <map>` |
| build | `dayz-build-pbo\build.py <ModName>` |
| launch | `dayz-launch-test\launch.py <ModName> --server <map>` |

`/dayz-new-mod` creates the `P:\<ModName>` junction itself. When the plan succeeds, go to Step 6.

## Step 6: hub

```
python "<skill-dir>\hub_status.py"
```

Shows the active mod, PBO age, test servers, whether DayZ Diag is running, and search status. Then ask "What next?" with AskUserQuestion and dispatch the choice. Repeat until the user is done.

| Choice | Do |
|---|---|
| Build and launch | `dispatch.py build`, then `dispatch.py launch --server <instance>` (ask for the instance if there are several; offer add-server if there are none) |
| Stop DayZ Diag | `dispatch.py stop` |
| Show the server log | Read the newest `script*.log` in `.server\<instance>\Profiles\` |
| Open in Workbench | `dispatch.py workbench` |
| Open in Object Builder | `dispatch.py objectbuilder` |
| Review the mod | Hand `workspace\<ModName>\` to the dayz-mod-reviewer agent |
| Add a test server | `dispatch.py add-server --server <map>` |
| Set up search | See "Search (optional)" below, then `dispatch.py search-download` |
| Set up or switch to another mod | Go back to Step 3 for that mod; `plan.py` skips scaffolding for a mod that already exists |

All `dispatch.py` actions default `--mod` to the active mod and exit with the child skill's exit code (2 when a required value is missing). `python "<skill-dir>\dispatch.py" --list` prints the actions.

## Search (optional)

Only when the user asks for it. The dayz-rag MCP server needs a Voyage AI key and an installed index (Voyage `voyage-code-3` embeddings in LanceDB under `~/.claude/dayz-search-index/`). The user adds `VOYAGE_API_KEY=pa-...` to `.env` at the project root themselves (don't ask them to paste the key into chat), then runs `/dayz-search-download` for the prebuilt index or `/dayz-search-index` to build it locally.
