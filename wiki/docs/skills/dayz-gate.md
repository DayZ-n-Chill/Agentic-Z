---
name: dayz-gate
---

## Overview

Runs the orchestrator's build and in-game gates as scripts instead of agent turns: build packs the mod and checks AddonBuilder output; ingame runs a test session and checks the new log lines. Failures are triaged against known errors. Use when gating a finished wave.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-gate

Script versions of the `dayz-build-checker` and `dayz-ingame-tester` gates. They run the existing skill scripts as subprocesses and apply the same rules those agents follow, so a wave costs one command and a short report instead of two agent runs. The gates gate on `/dayz-preflight` through the scripts they call.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\gate.py" build <ModName> [--json]
python "<skill-dir>\gate.py" ingame <ModName> [--deps CF ...] [--server <instance>] [--port N] [--timeout S] [--settle S] [--ready-pattern REGEX] [--json]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--deps` | `ingame`: dependency mods in load order, with or without `@` (`--deps CF`). Required when `config.cpp`'s `requiredAddons` lists anything not starting with `DZ_`; map each to the `@mod` under `P:\Mods\` that ships it. |
| `--server` | `ingame`: instance added with `/dayz-add-server` (default `chernarus`). `--port` default `2302`. |
| `--timeout` | `ingame`: seconds to wait for the client to reach the mission (default 300). |
| `--settle` | `ingame`: seconds to keep reading after that, to catch spawn-time errors (default 30). |
| `--ready-pattern` | `ingame`: regex in the client script log that means the mission is running. Default `Creating Mission: mpmissions\__cur_mp.`, printed by vanilla `CreateMission()` (`P:\scripts\5_mission\somemission.c`) when the client joins. |
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

## What `build` does

1. Stops any running `DayZDiag_x64.exe` with `/dayz-stop-test` (a session holds the PBO open).
2. Runs `/dayz-build-pbo <ModName>`. FAIL on a non-zero exit (every `[FAIL]` line is quoted with its hint), or on any AddonBuilder line after the command echo that reports an error, or a warning about missing files, textures or unknown classes.
3. Bundles ("Bundle / umbrella mods" in `.claude/skills/_shared/conventions/config.md`): with no `config.cpp` and a payload in `workspace/<ModName>/Addons/*.pbo`, the build is skipped and `/dayz-deploy-pbo <ModName>` runs instead; it must exit 0, and every `[FAIL]` and every `[WARN]` about a missing `.bisign` fails the gate. A bundle with a linker `config.cpp` gets both, build first.

## What `ingame` does

1. Stops any running session, records the size of every log in `.server/<instance>/Profiles/` and `.server/!ClientDiagLogs/`, then runs `/dayz-launch-test <deps...> <ModName> --server <instance>`. A launch refusal is a FAIL with its `[FAIL]` lines.
2. Polls the new log lines every 2 s until the ready line appears in the client script log plus `--settle` seconds, or `--timeout` (FAIL: no ready signal). It stops early on a `Can't compile ... script module` line, a new `crash*.log`, or a server or client process exiting (FAIL: crash).
3. Always stops the session with `/dayz-stop-test`, then judges only the lines written after step 1, with the `dayz-ingame-tester` rules:
   - Fail: script compile errors, missing config entries, textures or models, crashes; `NULL pointer` and `Can't find` errors only when they name the mod.
   - A line names the mod when it, or its stack trace, mentions the mod's folder, its `$PBOPREFIX$` root, or a class the mod declares (top-level classes in `config.cpp`'s `Cfg*` blocks and non-modded script classes).
   - Vanilla noise: a line that names nothing of the mod and also appears in a vanilla-only run, meaning one of the two newest older sessions in the same folder whose RPT `CLI params:` line has no `@<ModName>` (plus the script logs created within 30 s after that RPT). Noise is listed, not failed. With no such run the line is a warning.

## Triage

`triage.py` fingerprints each line (timestamps, absolute paths, hex addresses and numbers normalized, lowercased) and matches it against `known-errors.json` (regex entries shipped with the repo) and the project's learned file `.claude/local-memory/dayz-gate-known-errors.json`. Run it on its own for any log:

```cmd
python "<skill-dir>\triage.py" <log-file> [...] [--mod <ModName>] [--mod-dir workspace\<ModName>] [--json]
```

After a reviewer has diagnosed a `new` result, record it so the next run sees it as known:

```cmd
python "<skill-dir>\triage.py" --learn <id> --fingerprint "<fingerprint or raw log line>" [--meaning "..." --fix "..." --owner <agent>]
```

An existing `<id>` lends its meaning, fix and owner; a new id needs all three. Learned entries go to the per-project file, never into the shipped `known-errors.json`; add an entry there by hand (with a `source`) when the error is general.

## Limits

- The ready line is the vanilla client print when it joins a multiplayer mission. A mod that replaces `CreateMission` or the mission flow needs `--ready-pattern`.
- AddonBuilder diagnostics are matched by keyword (`error`, `failed`, `undefined base class`, and warning lines that mention missing, not found or unknown class), since AddonBuilder, CfgConvert and Binarize word their messages differently. A non-zero exit with no matching line still fails, with the last 25 output lines as the failure's `context`.
- Dependency mapping from `requiredAddons` to `@mods` is not automatic; pass `--deps`.

## Do not

- Don't use the gate while the user is playing a test session: it stops every `DayZDiag_x64.exe` first.
- Don't edit `known-errors.json` from `--learn`; learned fingerprints are per project.
