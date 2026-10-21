---
name: dayz-lint
---

## Overview

Finds errors that would stop a DayZ mod loading, before it is packed: config.cpp syntax, CfgPatches, requiredAddons, $PBOPREFIX$ and its P: link, script modules, modded classes, missing files and bad suffixes. Prints PASS or FAIL with file:line findings, each with an owner and a fix. Runs first inside /dayz-gate build and /dayz-build-pbo; use it alone to check a mod while you work.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-lint

A script reads the mod's files and reports every problem it is sure of. It starts no process, needs no DayZ Tools, and takes under a second. The AI only reads the findings and hands each one to its owner.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\lint.py" <ModName> [--json]
python "<skill-dir>\lint.py" --mod-dir <folder> [--json]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--mod-dir` | Lint any folder instead. Its name is the mod name unless `<ModName>` is given too. |
| `--json` | Print the full report as JSON after the verdict line. |

You don't need to run it before a build: `/dayz-gate build` and `/dayz-build-pbo` run it first and stop on any error.

## Output and exit codes

The first line is the verdict: `PASS` (exit 0, warnings allowed), `FAIL` (exit 1, at least one error) or `ERROR` (exit 2: bad arguments, no cached project, or the mod folder does not exist). Then one line per finding and its owner:

```
FAIL
- workspace/MyVest/config.cpp:5  error cfgpatches-field: CfgPatches class MyVest has no units[] array.
    -> dayz-config-specialist: Give every CfgPatches class units[] = {...}; weapons[] = {...}; and requiredAddons[] = {...}; ...
  1 error(s), 0 warning(s)
```

With `--json`:

```json
{
  "verdict": "FAIL", "mod": "MyVest", "mod_dir": "...", "errors": 1, "warnings": 0,
  "findings": [{
    "rule": "cfgpatches-field", "severity": "error", "file": "workspace/MyVest/config.cpp", "line": 5,
    "message": "CfgPatches class MyVest has no units[] array.",
    "text": "[lint:cfgpatches-field] CfgPatches class MyVest has no units[] array.",
    "triage": {"status": "known", "id": "lint-cfgpatches-field", "meaning": "...", "fix": "...", "owner_agent": "dayz-config-specialist", "fingerprint": "..."}
  }]
}
```

Each rule has a `lint-<rule>` entry in `.claude/skills/dayz-gate/known-errors.json` with its meaning, fix and owner, so lint findings are triaged the same way as log lines. Owner `user` means the user has to act; owner `dayz-orchestrator` means a skill run fixes it.

## Rules

Errors fail the lint. Warnings are listed and do not.

| Rule | Severity | Finds |
|---|---|---|
| `config-missing` | error | No `config.cpp`. A payload-only bundle (prebuilt `Addons\*.pbo`, no `config.cpp`) passes with a note instead. |
| `config-syntax` | error | Unbalanced braces, a missing `;` or `};`, an array without `[]`, `;` between array elements. Same grammar as the edit hook (`hooks/edit_check.py`). The structure rules below wait until the syntax is fixed. |
| `cfgpatches-missing`, `cfgpatches-empty` | error | No `class CfgPatches`, or one with no patch class inside. |
| `cfgpatches-field` | error | A patch class without `units[]`, `weapons[]` or `requiredAddons[]`, or one of them written without `[]`. |
| `required-addon-name` | error | An entry that is not a class name (a path, a `.pbo`, an `@mod` folder, a space), the mod's own patch class, or a `DZ_` name that no vanilla config on `P:\DZ\` or `P:\scripts\` declares. |
| `required-addon-duplicate` | warning | The same entry twice. |
| `pboprefix-missing`, `pboprefix-mismatch` | error | No `$PBOPREFIX$`, or one that does not hold exactly the mod name, which `/dayz-build-pbo` needs. |
| `p-link` | error | `P:\<prefix>\` is missing, is a real folder, or points away from the mod folder. |
| `p-not-mounted` | warning | `P:\` is not mounted, so the link and the vanilla `DZ_` names were not checked. |
| `script-module-path` | error | A `CfgMods` script module lists a folder outside the mod or one that does not exist. |
| `script-module-layer` | error | A module lists another layer's folder, for example `worldScriptModule` with `3_Game`. |
| `script-module-unlisted` | error | A `scripts/` folder holds `.c` files that no module lists, so they never compile. |
| `modded-class-extends` | error | `modded class Foo extends Foo` or `modded class Foo: Foo`, a silent no-op. |
| `script-suffix` | warning | A file under `scripts/` that is not `.c`, so it is never compiled. Dot files such as `.gitkeep` are skipped. |
| `missing-model`, `missing-texture`, `missing-file` | error | A path in `config.cpp` or a `.rvmat` that starts with the prefix but names a file that is not in the mod. Paths into vanilla or other mods are not checked. |
| `absolute-path` | error | A disk path (`P:\...`, `workspace\...`) where the game expects a path from the prefix. |
| `texture-format` | error | A `.png`, `.tga`, `.jpg` or `.dds` where the game needs a `.paa`. |
| `texture-suffix` | warning | A texture in `hiddenSelectionsTextures[]` or a `.rvmat` `texture` without a role suffix such as `_co`, `_nohq` or `_smdi`. |
| `rvmat-syntax` | error | A `.rvmat` with an unclosed string or comment. |

## Inside the build check

- `/dayz-gate build` lints first. On an error it reports FAIL with the lint findings as failures (category `lint`, triaged against `known-errors.json`) and does not stop a running session or build. The JSON report gains `"lint": {"verdict", "errors", "warnings"}`; lint warnings join the report's warnings.
- `/dayz-build-pbo` lints right after it reads the project cache, before `/dayz-preflight`. On an error it prints `[FAIL]` with each `file:line` and exits 1. It leaves the `P:\<ModName>\` link to its own junction check.

## Limits

- Lint checks files, not behaviour. Script compile errors still surface in `/dayz-gate ingame`.
- Paths into vanilla or another mod are not checked, and non vanilla `requiredAddons` names are only checked for shape. `/dayz-gate ingame --deps` covers those at run time.
- `#include` files are not followed.

## Do not

- Don't edit `known-errors.json` to silence a finding; fix the mod or, if lint is wrong, the rule in `lint.py` with a test.
