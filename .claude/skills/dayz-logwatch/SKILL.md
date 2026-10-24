---
name: dayz-logwatch
description: "Watches the server and client script and RPT logs of a running test session and triages each new error line the moment it appears: a known error prints its fix and owner, a new one is flagged for dayz-mod-debugger. Use while you play a test session started with /dayz-launch-test."
argument-hint: "[--server <instance>] [--since MINUTES] [--duration S | --until-closed] [--interval S] [--mod <ModName>] [--json] | --dir <folder> ..."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-logwatch

A script follows the test session's log files and runs every new error line through the same triage as `/dayz-gate` (`.claude/skills/dayz-gate/triage.py`). It starts no process and changes no file. The AI only reads the flagged lines and hands each one to its owner.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\logwatch.py" [--server <instance>] [--since MINUTES] [--duration S | --until-closed] [--interval S] [--mod <ModName>] [--json]
python "<skill-dir>\logwatch.py" --dir <folder> [--dir <folder> ...] [--since MINUTES] [--duration S | --until-closed] [--interval S] [--mod <ModName>] [--json]
```

| Argument | Notes |
|---|---|
| `--server` | Test server instance added with `/dayz-add-server`. Repeat it for more than one. Default: every instance under `.server/`. |
| `--dir` | Watch these folders instead of the project's session folders. |
| `--since` | Read files changed in the last MINUTES from their start. Default 0: only lines written after the watch starts. A negative value stops with exit 2. |
| `--duration` | Stop after S seconds. Must be more than 0; 0 or a negative value stops with exit 2. |
| `--until-closed` | Stop once the game client has been seen running and then closes (checked every 5 seconds). The client is the `DayZDiag_x64.exe` whose command line has no `-server`, so a server left running after you close the client window does not keep the watch going. If the client never starts within 300 seconds, stop with `session never started`. If the process list cannot be read (PowerShell missing, or its `Get-CimInstance Win32_Process` query fails) 3 checks in a row, stop with `cannot read process list` instead of guessing; use `--duration` on such a machine. Not allowed with `--duration`. |
| `--interval` | Seconds between reads (default 1). Must be at least 0.1; a smaller or negative value stops with exit 2. |
| `--mod` | Mod name, filled into fixes that mention `<ModName>`. |
| `--json` | One JSON object per line instead of text. |

Without `--duration` or `--until-closed` it runs until Ctrl+C. When the AI runs it, start it in the background with `--until-closed` and read its output as it comes in.

It watches `.server/<instance>/Profiles/` (the server's RPT and script logs) and `.server/!ClientDiagLogs/` (the client's), in the project cached by `/dayz-init`. Only `.rpt` and `.log` files at the top of those folders are read. A folder that does not exist yet is watched once it appears.

## When to start it

DayZ writes a new RPT and script log each launch, and a file that appears after the watch starts is read from its first line. So start the watch first, then `/dayz-launch-test`, and every line of the session is seen. With `--until-closed` the watch waits for the game client to start, then stops when you close the client window, even though the server keeps running until you close it or run `/dayz-stop-test`. If the session is already running, use `--since 5` to read the files it wrote in the last five minutes from the start.

## Output and exit codes

Text output starts with the folders it watches, then one block per error the first time it is seen:

```
Watching 2 folder(s) for new .rpt and .log lines (stops on its own):
  .server/chernarus/Profiles
  .server/!ClientDiagLogs
known script-unknown-type -> dayz-script-specialist  .server/chernarus/Profiles/script_2026-10-21_10-00-00.log:12
      SCRIPT    (E): @"MyVest/scripts/4_World/Vest.c,12": Unknown type 'CCConfig'
      fix: ...
new   -> dayz-mod-debugger  .server/!ClientDiagLogs/script_2026-10-21_10-00-03.log:40
      SCRIPT    (E): ...
Stopped (session closed) after 312 s: 2 error(s), 1 known, 1 new, 4 repeat(s) not shown.
```

With `--json` each error is `{"event": "error", "status": "known" or "new", "id", "meaning", "fix", "owner_agent", "file", "line", "text", "category", "fingerprint", "count"}` (`count` is always 1 here, on the first sighting; repeats are only counted in the summary) and the last line is `{"event": "summary", "stopped", "seconds", "errors", "known", "new", "repeats"}`. A `new` error has `owner_agent` set to `dayz-mod-debugger` and no `id`, `meaning` or `fix`.

An error line is one that triage classifies (compile errors, NULL pointers, missing classes, textures, models or config entries, crashes) or one that matches a known entry. The same error again, in any file and with any timestamp, has the same fingerprint and is only counted. A new `crash*.log` file is reported as a `new` crash for the debugger, and so is one written in the last MINUTES with `--since`.

Exit code 0 means no error line was seen, 1 means at least one was, and 2 means it could not run (a bad `--duration`, `--since` or `--interval` value, no cached project and no `--dir`, no `.server/` folder, an unknown instance, or a broken known-errors or learned file: bad JSON, a bad regex, or a shipped entry without `pattern`) or, with `--until-closed`, that the session never started or the process list could not be read. Exit 1 takes precedence: if errors were seen (for example with `--since`) before either of those stops, the exit code is 1.

## Then

- Hand each `known` error to its `owner_agent` with the fix. Owner `user` means the user has to act.
- Send the `new` ones to `dayz-mod-debugger` with the file and line. Once it names the cause, record it with `triage.py --learn` (see `/dayz-gate`) so the next watch knows it.

## Do not

- Don't edit `known-errors.json` to silence a line. Fix the mod, or teach triage with `--learn`.
- Don't treat a quiet watch as a pass. `/dayz-gate ingame` gives the verdict; the watch only shows errors while you play.
