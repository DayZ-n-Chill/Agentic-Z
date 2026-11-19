---
name: dayz-lint
description: "Finds errors that would stop a DayZ mod loading, before it is packed: config.cpp syntax, CfgPatches, requiredAddons, $PBOPREFIX$ and its P: link, script modules, modded classes, missing files and bad suffixes, then the code itself (Enforce Script, .layout, inputs.xml and .rvmat rules of the script validator). Prints PASS or FAIL with file:line findings, each with an owner and a fix. Runs first inside /dayz-gate build and /dayz-build-pbo; use it alone to check a mod while you work."
argument-hint: "<ModName> [--json] [--external-scripts <folder>] | --mod-dir <folder> [--json] [--external-scripts <folder>]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-lint

A script reads the mod's files and reports every problem it is sure of, in two stages run by the one command:

1. **Setup**: `config.cpp`, `CfgPatches`, the prefix and its link, script modules and files (the [Rules](#rules) table).
2. **Code**: the script validator in `scripts/tools/dayz-script-validator/` reads the Enforce Script, `.layout`, `config.cpp`, `inputs.xml` and `.rvmat` files themselves (the [Code rules](#code-rules-second-stage) table).

It starts no process and needs no DayZ Tools. The code stage reads the vanilla scripts on `P:\scripts\` when they are there, which adds roughly 10 to 15 seconds on a full `P:\scripts\` (under a second without it). The AI only reads the findings and hands each one to its owner.

Follow `skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\lint.py" <ModName> [--json] [--external-scripts <folder>]
python "<skill-dir>\lint.py" --mod-dir <folder> [--json] [--external-scripts <folder>]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. A plain folder name: a name that is `.` or `..`, or contains `/`, `\` or `:`, is refused with ERROR; pass a path with `--mod-dir`. |
| `--mod-dir` | Lint any folder instead. Its name is the mod name unless `<ModName>` is given too. Paths in findings and fixes are shown from the current folder. |
| `--json` | Print the full report as JSON after the verdict line. |
| `--external-scripts` | The folder of a mod this one depends on (the folder that holds its `config.cpp`), for example Community Framework. Its classes then count as declared in the code stage. Repeatable. A folder that does not exist is an ERROR. |

You don't need to run it before a build: `/dayz-gate build` and `/dayz-build-pbo` run it first and stop on any error.

## Output and exit codes

The first line on stdout is always the verdict: `PASS` (exit 0, warnings allowed), `FAIL` (exit 1, at least one error) or `ERROR` (exit 2: bad arguments, no cached project, or the mod folder does not exist). On `ERROR` the next line says why (with `--json`, a `{"verdict": "ERROR", "error": "..."}` object), and nothing is printed on stderr first. Otherwise one line per finding and its owner:

```
FAIL
- workspace/MyVest/config.cpp:5  error cfgpatches-field: CfgPatches class MyVest: units must be an array, units[] = {...};.
    -> dayz-config-specialist: Write it as an array: units[] = {...}; weapons[] = {...}; requiredAddons[] = {...}; ...
  1 error(s), 0 warning(s)
```

With `--json`:

```json
{
  "verdict": "FAIL", "mod": "MyVest", "mod_dir": "...", "errors": 1, "warnings": 0,
  "findings": [{
    "rule": "cfgpatches-field", "severity": "error", "file": "workspace/MyVest/config.cpp", "line": 5,
    "message": "CfgPatches class MyVest: units must be an array, units[] = {...};.",
    "text": "[lint:cfgpatches-field] CfgPatches class MyVest: units must be an array, units[] = {...};.",
    "triage": {"status": "known", "id": "lint-cfgpatches-field", "meaning": "...", "fix": "...", "owner_agent": "dayz-config-specialist", "fingerprint": "..."}
  }]
}
```

A code-stage finding has the same fields plus `"stage": "code"`, and its `rule` is the validator's rule id:

```
- workspace/MyVest/scripts/4_World/vest.c:5  error ES-RESERVED-WORD-IDENTIFIER: 'local' is an Enforce keyword and cannot name a variable, member or parameter. ...
    -> dayz-script-specialist: Rename the variable, member or parameter.
  not checked ES-UNDEFINED-CLASS-REF: config.cpp requires JM_CF_Scripts, and no scanned root declares it in CfgPatches. ...
```

A `not checked` line names a code rule that could not judge this mod, with the reason: `P:\scripts\` is missing, or the mod depends on a mod whose folder was not passed with `--external-scripts`. It is not a finding and does not change the verdict, but that rule did not pass either. The report gains `"code": {"errors", "warnings", "files", "skipped": [{"rule", "reason"}]}` for the stage; `errors` and `warnings` at the top count both stages. A payload-only bundle has no `code` entry.

Each setup rule has a `lint-<rule>` entry in `skills/dayz-gate/known-errors.json` with its meaning, fix and owner, so lint findings are triaged the same way as log lines. Owner `user` means the user has to act; owner `dayz-orchestrator` means a skill run fixes it. Fixes that name `workspace/<ModName>/` are rewritten to the folder actually linted. For a `--mod-dir` folder outside the cached project's `workspace\`, where `/dayz-add-scaffold` refuses to run, the `p-link`, `pboprefix-missing` and `config-missing` fixes say what to create by hand (or point at `/dayz-import-mod`) instead.

## Rules

A finding is an error only when it stops the mod packing or loading. Everything else is a warning. Errors fail the lint, and so the gate and the build. Warnings are listed and do not.

| Rule | Severity | Finds |
|---|---|---|
| `config-missing` | error | No `config.cpp`. A payload-only bundle (prebuilt `Addons\*.pbo`, no `config.cpp`) passes with a note instead. |
| `config-syntax` | error | Unbalanced braces, a missing `;` or `};`, an array without `[]`, `;` between array elements. Same grammar as the edit hook (`hooks/edit_check.py`). The structure rules below wait until the syntax is fixed. |
| `cfgpatches-missing`, `cfgpatches-empty` | error | No `class CfgPatches`, or one with no patch class inside. |
| `cfgpatches-field` | error | `units`, `weapons` or `requiredAddons` written without `[]`, so it is not an array. |
| `cfgpatches-field-missing` | warning | A patch class without `units[]` or `weapons[]`. The engine tolerates it: vanilla `DZ_data_aiconfigs` in `P:\DZ\data\aiconfigs\config.cpp:3` has an empty body. |
| `required-addons-missing` | error | A patch class without `requiredAddons[]`, so its config can load before the vanilla classes it changes. |
| `required-addon-name` | error | An entry that is not a class name (a path, a `.pbo`, an `@mod` folder, a space), the mod's own patch class, or a `DZ_` name that no vanilla config on `P:\DZ\` or `P:\scripts\` declares. |
| `required-addon-duplicate` | warning | The same entry twice. |
| `pboprefix-missing`, `pboprefix-mismatch` | error | No `$PBOPREFIX$`, or one that does not hold exactly the mod name, which `/dayz-build-pbo` needs. |
| `pboprefix-encoding` | error | A `$PBOPREFIX$` that is UTF-16 (what Windows PowerShell 5.1 writes for `echo <ModName> > $PBOPREFIX$`) or not valid UTF-8, so its prefix cannot be read. Save it as plain ASCII or UTF-8 holding only the mod name. The other rules still run. |
| `p-link` | error | `P:\<prefix>\` is missing, is a real folder, or points away from the mod folder. A link that reaches the mod folder through another junction (the `/dayz-import-mod` layout, `P:\<prefix>` to `workspace\<ModName>` to the source) counts as pointing at it. The fix is `/dayz-add-scaffold <ModName> --piece junction` for a mod in the cached project's `workspace\`; for a `--mod-dir` folder outside it, `/dayz-import-mod --source <folder>` or `mklink /J P:\<prefix> <folder>`. |
| `p-not-mounted` | warning | `P:\` is not mounted, so the link and the vanilla `DZ_` names were not checked. |
| `script-module-path` | error | A `CfgMods` script module lists a folder outside the mod or one that does not exist. |
| `script-module-layer` | error | A module lists another layer's folder, for example `worldScriptModule` with `3_Game`. |
| `script-module-unlisted` | warning | A `scripts/` folder holds `.c` files that no module lists. The mod still loads; the engine just ignores those files. |
| `modded-class-extends` | error | `modded class Foo extends Foo` or `modded class Foo: Foo`, a silent no-op. Also caught when the `extends` or `:` is on the next line; the finding names the line holding `modded`. Commented-out code is ignored; `//` and `/*` inside a string are not comments. |
| `script-suffix` | warning | A file under `scripts/` that is not `.c`, so it is never compiled. Dot files such as `.gitkeep` are skipped. |
| `missing-model`, `missing-texture`, `missing-file` | error | A path in `config.cpp` or a `.rvmat` that starts with the prefix but names a file that is not in the mod. Paths into vanilla or other mods are not checked. |
| `absolute-path` | error | A disk path (`P:\...`, `workspace\...`) where the game expects a path from the prefix. |
| `texture-format` | error | A `.png`, `.tga`, `.jpg`, `.jpeg`, `.bmp` or `.dds` where the game needs a `.paa`. That is the only finding for the reference: whether the image exists is not checked, since the fix replaces the path. |
| `texture-suffix` | warning | A texture in `hiddenSelectionsTextures[]` or a `.rvmat` `texture` without a role suffix such as `_co`, `_nohq` or `_smdi`. |
| `rvmat-syntax` | error | A `.rvmat` with an unclosed string or comment. |

## Code rules (second stage)

The second stage runs every rule of the script validator on the mod folder and reports its findings in the shape above. The validator's FAIL findings are errors and its WARN findings are warnings, with one exception: a file that is not UTF-8 (`INPUT-ENCODING-ERROR`) is a warning, because the engine still loads it and only the code rules cannot read it. The owner and fix of each rule come from the `CODE_RULES` table in `lint.py`; a `lint-<rule>` entry in `known-errors.json` or a learned entry wins when one matches. Log-line entries of `known-errors.json` are not matched against code findings.

| Rules | Owner | Finds |
|---|---|---|
| `ES-*` on `.c` files, `INPUT-ENCODING-ERROR` | `dayz-script-specialist` | Code the compiler refuses (an unknown class, a reserved word as a name, unbalanced brackets, a variable declared twice, a cast between unrelated types, a `modded class` of an engine class, a wrong override) and code that compiles but fails at run time (an unchecked `ctx.Read`, a sync variable written without `SetSynchDirty()`). |
| `CONFIG-*`, `ES-CONFIG-*`, `ES-ATTACHMENTS-*` | `dayz-config-specialist` | An `inputs.xml` that `CfgMods` does not register or whose root element is wrong, a nested class whose base is not forward-declared, `attachments[] +=` over a class from another PBO, a `P:\` path in `config.cpp`. |
| `LAYOUT-*`, `ES-LAYOUT-*`, `ES-ONMOUSELEAVE-PARAM-COUNT` | `dayz-ui-specialist` | A `.layout` in XML format, a layout path in script that does not start with the prefix or names no file, an `OnMouseLeave` handler that never fires. |
| `RVMAT-*` | `dayz-asset-specialist` | `shader = NormalMapMacro;` and a `P:\` path in a `.rvmat`. |

`scripts/tools/dayz-script-validator/RULES.md` describes the rules, the evidence behind each and what each one leaves unjudged.

Run on its own, the validator (`scripts/tools/dayz-script-validator/scripts/script_validator.py`) answers in its own shape: a JSON report whose root keys are `status`, `errors` and `warnings`, and exit code 0 for PASS, 1 for FAIL and 2 for warnings only. A script that calls it directly gates on the error count, not on a non-zero exit. `/dayz-lint` already does that and turns the result into its own verdict above.

To tell whether a change brought in an error, lint the mod before the change and again after it and compare the findings: a finding only in the second run belongs to the change. This catches a reference left dangling by a deleted or renamed file, which a grep for the symbol misses.

Three rules (`ES-UNDEFINED-CLASS-REF`, `ES-VARIABLE-NAMED-AS-TYPE`, `ES-UNDEFINED-BUILTIN-METHOD`) need the vanilla scripts on `P:\scripts\`, and their verdicts hold for the game build those scripts come from. `ES-UNDEFINED-CLASS-REF` also needs every non-vanilla mod in `requiredAddons[]` passed with `--external-scripts`. Without them the rule is listed as `not checked`.

## Inside the build check

- `/dayz-gate build` lints first, both stages. On an error it reports FAIL with the lint findings as failures (category `lint`; a setup finding is triaged against `known-errors.json`, a code finding keeps the triage lint gave it) and does not stop a running session or build. The JSON report gains `"lint": {"verdict", "errors", "warnings"}`; lint warnings join the report's warnings.
- `/dayz-build-pbo` lints, both stages, after its preflight and workspace checks. On an error it prints `[FAIL]` with each `file:line` and exits 1. It leaves the `P:\<ModName>\` link to its own junction check.
- Neither passes `--external-scripts`, so for a mod that depends on another mod `ES-UNDEFINED-CLASS-REF` is not checked there. Run `/dayz-lint <ModName> --external-scripts <folder>` to get its verdict.

## Limits

- Lint checks files, not behaviour. The code stage is a set of rules, not a compiler: a PASS means no rule fired, so other script compile errors still surface in `/dayz-gate ingame`.
- Paths into vanilla or another mod are not checked, and non vanilla `requiredAddons` names are only checked for shape. `/dayz-gate ingame --deps` covers those at run time.
- `#include` files are not followed.
- A path with a `P:\` drive in `config.cpp` or a `.rvmat` can be listed twice, once by each stage (`absolute-path` and `CONFIG-PDRIVE-PATH` or `RVMAT-PDRIVE-PATH`). One fix clears both.

## Do not

- Don't edit `known-errors.json` to silence a finding; fix the mod or, if lint is wrong, the rule in `lint.py` (a setup rule) or in `scripts/tools/dayz-script-validator/` (a code rule) with a test.
