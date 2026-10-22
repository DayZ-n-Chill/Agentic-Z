---
name: dayz-gate
---

## Overview

Runs the build, in-game, behavior and visual gates as scripts, with PASS or FAIL, triaged failures and a stored result for each. Use when gating a finished wave or checking a mod builds, loads, works and looks right in game.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-gate

Script versions of the `dayz-build-checker` and `dayz-ingame-tester` gates, plus a behavior gate that tests what each new item does and a visual gate that compares screenshots of the game with the expected look. They run the existing skill scripts as subprocesses and apply the same rules those agents follow, so a wave costs one command and a short report instead of two agent runs. The gates gate on `/dayz-preflight` through the scripts they call.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\gate.py" build <ModName> [--json]
python "<skill-dir>\gate.py" ingame <ModName> [--deps CF ...] [--server <instance>] [--port N] [--timeout S] [--settle S] [--ready-pattern REGEX] [--json]
python "<skill-dir>\gate.py" behavior <ModName> [--checks FILE] [--deps CF ...] [--server <instance>] [--port N] [--timeout S] [--done-timeout S] [--ready-pattern REGEX] [--json]
python "<skill-dir>\gate.py" behavior <ModName> [--checks FILE] [--server <instance>] --prepare-only
python "<skill-dir>\gate.py" behavior <ModName> [--checks FILE] [--server <instance>] --logs [FILE ...] [--json]
python "<skill-dir>\gate.py" visual <ModName> [--shots FILE] [--deps CF ...] [--server <instance>] [--port N] [--timeout S] [--threshold R] [--ready-pattern REGEX] [--json]
python "<skill-dir>\gate.py" visual <ModName> [--shots FILE] [--threshold R] --compare [DIR] [--json]
python "<skill-dir>\gate.py" visual <ModName> [--shots FILE] --accept [DIR] [--shot ID ...] [--json]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--deps` | `ingame`, `behavior`, `visual`: dependency mods in load order, with or without `@` (`--deps CF`). Required when `config.cpp`'s `requiredAddons` lists anything not starting with `DZ_`; map each to the `@mod` under `P:\Mods\` that ships it. |
| `--server` | `ingame`, `behavior`, `visual`: instance added with `/dayz-add-server` (default `chernarus`). `--port` default `2302`. |
| `--timeout` | `ingame`, `behavior`, `visual`: seconds to wait for the client to reach the mission (default 300). |
| `--settle` | `ingame` only: seconds to keep reading after that, to catch spawn-time errors (default 30). `visual` has no `--settle`: it reads until its last shot is taken. |
| `--done-timeout` | `behavior` only: the most seconds to wait for the test mission's `DONE` line after the client joins (default 600). The gate stops as soon as that line appears. |
| `--ready-pattern` | `ingame`, `behavior` and `visual` in-game runs: regex in the client script log that means the mission is running. Default `Creating Mission: mpmissions\__cur_mp.`, printed by vanilla `CreateMission()` (`P:\scripts\5_mission\somemission.c`) when the client joins. |
| `--checks` | `behavior`: the checks file. Default `output/<ModName>-plan/behavior-checks.json`, which `dayz-mod-architect` writes with the plan. |
| `--prepare-only` | `behavior`: write the instance copy and stop. The first line is `PREPARED` (exit 0). |
| `--logs` | `behavior`: judge the logs of a session that already ran instead of launching one. With no files it reads the copy's server script logs. |
| `--shots` | `visual`: the shots file. Default `output/<ModName>-plan/visual-shots.json`. |
| `--threshold` | `visual`: the share of pixels, 0 to 1, that may differ for a shot that sets no threshold of its own. It beats the shots file's `threshold`; the default is 0.01. |
| `--compare` | `visual`: compare captures already taken instead of launching. With no folder it uses the newest run. |
| `--accept` | `visual`: copy captures into the baselines. With no folder it uses the newest run; `--shot` limits it to some shots (`--shot` without `--accept` is refused, exit 2). The first line is `ACCEPTED` (exit 0). |
| `--json` | Print the full report as JSON after the verdict line. |

## Output and exit codes

The first line is the verdict: `PASS` (exit 0), `FAIL` (exit 1) or `ERROR` (exit 2: bad arguments, no cached project, `/dayz-stop-test` failed, a dependency list is needed, or the gate crashed). Then a short summary, or with `--json`:

```json
{
  "verdict": "FAIL", "mode": "ingame", "mod": "MyVest",
  "steps": [{"step": "stop-session", "result": "no DayZDiag session running"}, {"step": "dayz-launch-test", "rc": 0}, ...],
  "ready": {"file": "script_2026-10-20_12-00-31.log", "line": 214, "text": "SCRIPT : Creating Mission: mpmissions\\__cur_mp.chernarusplus\\mission.c"},
  "failures": [{
    "category": "null_pointer", "file": ".server\\!ClientDiagLogs\\script_...log", "line": 230,
    "text": "SCRIPT    (E): NULL pointer to instance", "context": ["Class: 'MyVest_Helper'", "Stack trace:", "MyVest/scripts/4_World/vest.c:42"],
    "points_to": ["MyVest/scripts/4_World/vest.c"], "count": 1,
    "triage": {"status": "known", "id": "null-pointer", "fix": "...", "owner_agent": "dayz-script-specialist", "fingerprint": "..."}
  }],
  "warnings": [...], "noise": [...], "baseline": ["...older vanilla-only RPT..."],
  "source_findings": [...]
}
```

Each failure carries `triage`: `known` (with `id`, `meaning`, `fix` and `owner_agent`) or `new` (send it to `dayz-mod-debugger`). Owner `user` means the user has to act (mount `P:`, install tools); owner `dayz-orchestrator` means a skill run fixes it. On a FAIL, `source_findings` lists known defects found in the mod's source (a `modded class` with an extends clause, a `config.cpp` without `CfgPatches`); they don't change the verdict. Warnings and noise are deduplicated and capped at 30 entries each.

Every `PASS` or `FAIL` is stored for `/dayz-health` under `.server/!Health/<ModName>/results/` (a `build` run stores its lint step too), and the mod's health page is rebuilt. The report then gains `"health"`, the path of the page's Markdown file. If storing fails, the report gains `"health_error"` instead and the verdict stays the same. An `ERROR` and `--prepare-only` store nothing.

## What `build` does

1. Runs `/dayz-lint <ModName>` first. Any lint error is a FAIL (category `lint`, file and line from the lint finding, triaged by its `lint-<rule>` entry) and the gate stops there, leaving a running session alone. Lint warnings join the report's warnings, and the report gains `"lint": {"verdict", "errors", "warnings"}`.
2. Stops any running `DayZDiag_x64.exe` with `/dayz-stop-test` (a session holds the PBO open).
3. Runs `/dayz-build-pbo <ModName>`. FAIL on a non-zero exit (every `[FAIL]` line is quoted with its hint), or on any AddonBuilder line after the command echo that reports an error, or a warning about missing files, textures or unknown classes.
4. Bundles ("Bundle / umbrella mods" in `.claude/skills/_shared/conventions/config.md`): with no `config.cpp` and a payload in `workspace/<ModName>/Addons/*.pbo`, the build is skipped and `/dayz-deploy-pbo <ModName>` runs instead; it must exit 0, and every `[FAIL]` and every `[WARN]` about a missing `.bisign` fails the gate. A bundle with a linker `config.cpp` gets both, build first.

## What `ingame` does

1. Stops any running session, records the size of every log in `.server/<instance>/Profiles/` and `.server/!ClientDiagLogs/`, then runs `/dayz-launch-test <deps...> <ModName> --server <instance>`. A launch refusal is a FAIL with its `[FAIL]` lines.
2. Polls the new log lines every 2 s until the ready line appears in the client script log plus `--settle` seconds, or `--timeout` (FAIL: no ready signal). It stops early on a `Can't compile ... script module` line, a new `crash*.log`, or a server or client process exiting (FAIL: crash).
3. Always stops the session with `/dayz-stop-test`, then judges only the lines written after step 1, with the `dayz-ingame-tester` rules:
   - Fail: script compile errors, missing config entries, textures or models, crashes; `NULL pointer` and `Can't find` errors only when they name the mod.
   - A line names the mod when it, or its stack trace, mentions the mod's folder, its `$PBOPREFIX$` root, or a class the mod declares (top-level classes in `config.cpp`'s `Cfg*` blocks and non-modded script classes).
   - Vanilla noise: a line that names nothing of the mod and also appears in a vanilla-only run, meaning one of the two newest older sessions in the same folder whose RPT `CLI params:` line has no `@<ModName>` (plus the script logs created within 30 s after that RPT). Noise is listed, not failed. With no such run the line is a warning.

## What `behavior` does

1. Reads the checks file and refuses a bad one (exit 2) before touching anything. Stops any running session.
2. Copies `.server/<instance>/` to `.server/<instance>-behavior/`: `serverDZ.cfg`, `mission/` without its `storage_*` persistence folders, the `<template>/` junction that `/dayz-launch-test` needs, and `Profiles/`. A previous copy is replaced; its logs stay. Your own instance is never changed.
3. Adds a test mission to the copy's `init.c`: the class `AZ_BehaviorTest` above `main()` and an `AZ_BehaviorTest.Start();` call as the last line of `main()`.
4. Runs the `ingame` flow on the copy, so every `ingame` rule still applies. The test mission waits for the first player (up to 240 s), waits 10 s more, empties the player's hands and clothing slots, then runs one check per second and prints to the server script log:

   ```text
   [AZ-BEHAVIOR] START <count>
   [AZ-BEHAVIOR] PASS <check id>
   [AZ-BEHAVIOR] FAIL <check id> <reason>
   [AZ-BEHAVIOR] DONE
   ```

5. Reads those lines. A check passes only on its `PASS` line. A `FAIL` line, or no line at all (the mission never started, or a script error stopped it first), fails the check. A new `START` line starts over, so the newest run in the logs wins. When there is no `START` line at all and the session shows nothing else wrong (the client joined, no crash, no script error), the verdict is `ERROR`, not `FAIL`: the gate's own test mission did not run, so it says nothing about the mod.

The report adds `checks` (one entry per check with `status`, `reason`, `file` and `line`) and `behavior` (`started`, `done`, and `unexpected` ids that are not in the checks file). Each failed check is a failure with category `behavior` and its `check` id; triage marks it `new`, so it goes to `dayz-mod-debugger` with the reason line.

### Checks file

`dayz-mod-architect` writes one check per feature, each with an `id`, a `feature`, an `item` and one of the actions `spawn`, `hands`, `wear`, `attach` or `cargo`. The format and what each action does are in [checks-file.md](checks-file.md); read it before writing or fixing a checks file.

### Running it by hand

`--prepare-only` writes the copy. Launch it with `/dayz-launch-test <ModName> --server <instance>-behavior`, stop it with `/dayz-stop-test`, then judge it with `behavior <ModName> --logs`.

## What `visual` does

1. Reads the shots file and refuses a bad one (exit 2) before touching anything.
2. Runs the `ingame` flow on your instance, so every `ingame` rule still applies. At each shot's `at` second after the client joins, it brings the client window to the front and saves its picture to `output/<ModName>-visual/runs/<date_time>/<id>.png`. The session stops two seconds after the last shot.
3. Compares each capture with `output/<ModName>-visual/baseline/<id>.png`. Both images are shrunk to 640 pixels wide, which averages away single pixel noise. A pixel counts as changed when its colour distance, weighted toward brightness the way the eye sees it (the pixelmatch measure), is above a tenth of the largest possible. A shot fails when the share of changed pixels is above its threshold. Areas in its `ignore` list are left out.
4. Writes `<id>.diff.png` next to each capture: the baseline in pale grey, changed pixels in red and ignored areas in blue.

Each shot ends as one of these:

| Status | Means | Failure text |
|---|---|---|
| `PASS` | the share of changed pixels is at or under the threshold | |
| `FAIL` | too many pixels changed, or the capture is a different size from the baseline | `[visual:diff] <id>: ...` |
| `NEW` | the shot has no baseline yet | `[visual:no-baseline] <id>: ...` |
| `MISSING` | no capture: the window was hidden or minimized, or the session ended first | `[visual:no-capture] <id>: ...` |

Every status but `PASS` fails the gate. The report adds `shots` (one entry per shot with `status`, `ratio`, `threshold`, `capture`, `baseline`, `diff` and `reason`) and `visual` (the run and baseline folders). Triage marks each failure `known` with owner `user`, because only a person can say whether a new look is right: look at the capture and the diff, then accept it with `--accept --shot <id>` or send it to the specialist who owns that part of the screen.

The first run of a shot is always `NEW`. Look at its capture, accept it, and later runs compare against it. Keep the baselines with the project; the runs folder is ignored by git.

### Shots file

Each shot has an `id`, a `feature` and an `at` second, with an optional `threshold` and `ignore` areas. The format is in [shots-file.md](shots-file.md); read it before writing or fixing a shots file.

## Triage

`triage.py` fingerprints each line (timestamps, absolute paths, hex addresses and numbers normalized, lowercased) and matches it against `known-errors.json` (regex entries shipped with the repo) and the project's learned file `.claude/local-memory/dayz-gate-known-errors.json`. Run it on its own for any log:

```cmd
python "<skill-dir>\triage.py" <log-file> [...] [--mod <ModName>] [--mod-dir workspace\<ModName>] [--json]
```

### Pasted logs

When the user pastes a crash log or RPT instead of naming a file, triage the pasted text. Pipe it on stdin, or pass it with `--text`:

```cmd
python "<skill-dir>\triage.py" --stdin --json < pasted.txt
python "<skill-dir>\triage.py" --text "<pasted log>" --json
```

Results look the same as for a file, with `file` set to `<pasted>` and `line` counted within the paste. Give the user the cause and fix of each `known` result and hand it to its `owner_agent`. Dispatch `dayz-mod-debugger` with only the `new` lines and the log around them. The paste-in hook (`hooks/paste_router.py`) already runs this triage on every prompt that holds DayZ error lines and adds the result to the conversation, so for a pasted log you usually only act on its list.

After a reviewer has diagnosed a `new` result, record it so the next run sees it as known:

```cmd
python "<skill-dir>\triage.py" --learn <id> --fingerprint "<fingerprint or raw log line>" [--meaning "..." --fix "..." --owner <agent>]
```

An existing `<id>` lends its meaning, fix and owner; a new id needs all three. Learned entries go to the per-project file, never into the shipped `known-errors.json`; add an entry there by hand (with a `source`) when the error is general.

## Limits

- The ready line is the vanilla client print when it joins a multiplayer mission. A mod that replaces `CreateMission` or the mission flow needs `--ready-pattern`.
- AddonBuilder diagnostics are matched by keyword (`error`, `failed`, `undefined base class`, and warning lines that mention missing, not found or unknown class), since AddonBuilder, CfgConvert and Binarize word their messages differently. A non-zero exit with no matching line still fails, with the last 25 output lines as the failure's `context`.
- Dependency mapping from `requiredAddons` to `@mods` is not automatic; pass `--deps`.
- The behavior test mission only knows the five actions above. A feature that needs more (driving, firing, eating) has no check yet; say so in the plan.
- The test player is stripped once before the checks and each check deletes what it made, so no check can prove two items work together on the player.
- The test mission's engine calls are checked against vanilla `P:\scripts`, and the injector and parser are tested on fixture missions and logs, but the mission has not yet run in a live session. If it fails to start there (for example an Enforce compile error in the injected `AZ_BehaviorTest` class), the gate reports `ERROR` rather than failing the mod, unless the session also shows a mod error.
- The visual compare and baselines are tested on fixture images. The window capture is Windows only and has not yet run against a live client. It copies what is on screen, so the client must run windowed (the `/dayz-launch-test` default) and stay uncovered while the gate runs. It captures only the visible window of the client's own process, and when Windows will not bring that window to the front the shot is `MISSING`, not compared against something else.
- A shot is taken at a time, not at a game event, and the test player stands where the server spawns it. Shots that need the player in one place or a menu open need the mod (or a future test mission) to put them there; screens that move on their own need a higher threshold or `ignore` areas.
- The visual gate needs Pillow: `py -m pip install -r "<skill-dir>\requirements.txt"`.

## Do not

- Don't use the gate while the user is playing a test session: it stops every `DayZDiag_x64.exe` first.
- Don't edit `known-errors.json` from `--learn`; learned fingerprints are per project.
- Don't `--accept` a capture nobody has looked at; the baseline is the expected look.
