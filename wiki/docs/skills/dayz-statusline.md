---
name: dayz-statusline
---

## Overview

Installs a one-line DayZ status line showing whether P:\ is mounted, the active mod, whether DayZDiag is running and the RAG index age, and can remove it. Use when the user wants DayZ environment state always visible instead of running /dayz-preflight or the /dayz-init hub.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-statusline

Puts DayZ environment state in Claude Code's status line, for example:

```text
P: mounted | mod MyVest | Diag off | RAG 3d old
```

| Segment | Source |
|---|---|
| `P: mounted` / `P: NOT mounted` | whether `P:\` exists |
| `mod <Name>` / `no active mod` / `no project (/dayz-init)` | the project cache and active mod written by `/dayz-init` (read through `dayz-init/state.py`) |
| `Diag running` / `Diag off` | any `DayZDiag_x64.exe` process (server or client) |
| `RAG <age> old` / `RAG not indexed` | `indexed_at` in `~/.claude/dayz-search-index/manifest.json` |

## How to run

```cmd
:: Install (safe to re-run; re-run after a plugin update to point at the new path)
python "<skill-dir>\install.py"

:: Remove (restores the status line it replaced, if any)
python "<skill-dir>\install.py" --remove

:: Show what is set
python "<skill-dir>\install.py" --status
```

Run from the project root, the folder Claude Code was started in: the setting goes into that folder's `.claude\settings.local.json`. The line shows up after the next message.

## What install does

1. Reads `.claude\settings.local.json` (refuses, changing nothing, if it is not valid JSON).
2. If our status line is already set, stops: nothing to do.
3. Copies the file to `settings.local.json.bak`, and records any status line it replaces in `.claude\local-memory\dayz-statusline.json`.
4. Sets `statusLine` to run `statusline.py` with a 10-second `refreshInterval`, so the Diag and `P:\` segments catch up while the session is idle.

`--remove` only touches a status line this skill installed: it puts back the recorded one, or deletes the `statusLine` key.

## Why a skill and not the plugin

A plugin cannot set the main `statusLine`: plugin settings accept only `agent` and `subagentStatusLine` (plugins reference, `settings`). So the plugin ships the script and this skill writes the setting into your project's local settings, which are per machine and gitignored. The installed command holds the script's absolute path, and a plugin update moves the plugin folder, so re-run the install after updating.

## Speed and failure

The script reads the session JSON on stdin for the project folder, and caches the `P:\`, process and index checks in `%TEMP%\agentic-z-statusline.json` for 5 seconds. The process check uses a Windows process snapshot instead of spawning `tasklist`. A full run takes about 0.2 s, mostly Python start-up. Any error prints `DayZ status unavailable` instead of an error. It needs `python` on `PATH`, like the other skills.

Does not gate on `/dayz-preflight`: it only edits a settings file, and the status line exists to show a broken environment.
