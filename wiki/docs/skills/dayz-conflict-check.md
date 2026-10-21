---
name: dayz-conflict-check
---

## Overview

Compares a mod with other mods under P:\Mods (CF, COT and Expansion by default, when present) and reports $PBOPREFIX$ and path collisions, shared CfgPatches and config class names, script classes declared twice and modded classes both mods override. Reads only unpacked configs and scripts and PBO headers; never extracts or copies another mod. Prints PASS or FAIL with file:line findings, each with an owner and a fix. --ingame then runs /dayz-gate ingame with those mods loaded. Use before releasing a mod that runs beside CF, COT or Expansion.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-conflict-check

A script reads your mod and the other mods and lists every name and path you share with them. It starts no process unless you add `--ingame`, and takes about a second even against the whole Expansion bundle. The AI only reads the findings and hands each one to its owner.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\conflict_check.py" <ModName> [--against MOD ... | --all] [--json]
python "<skill-dir>\conflict_check.py" --mod-dir <folder> [--against MOD ... | --all] [--json]
python "<skill-dir>\conflict_check.py" <ModName> --ingame [--server <instance>] [--port N] [--json]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--mod-dir` | Check any folder instead. Its name is the mod name unless `<ModName>` is given too. |
| `--against` | The mods to compare with, in load order: names under the mods folder (`CF` or `@CF`) or folder paths, such as an unpacked mod source on `P:\`. |
| `--all` | Compare with every `@mod` under the mods folder. |
| `--mods-root` | The folder that holds the `@mods`. Default `P:\Mods`. |
| `--ingame` | After the scan, run `/dayz-gate ingame <ModName> --deps <the same mods>`. Needs a built PBO and a server from `/dayz-add-server`. |
| `--server`, `--port` | `--ingame` only: the test instance (default `chernarus`) and port (default `2302`). |
| `--json` | Print the full report as JSON after the verdict line. |

With no `--against` or `--all` it compares with `@CF`, `@Community-Online-Tools` and the Expansion mods that are there. When `@DayZ-Expansion-Bundle` is there it is used alone, since it holds every Expansion part; otherwise each `@DayZ-Expansion*` folder is used, Core first. Your own `@<ModName>` is never compared with itself.

## What it reads, and what it never does

- **Your mod:** `$PBOPREFIX$`, every `config.cpp` and every `.c` file under the mod folder.
- **A packed mod:** only the header of each `.pbo` in its `Addons` folder: the `prefix` and the list of file names. The packed data after the header is never read, so their config and script classes are not compared. `--ingame` covers those at run time.
- **An unpacked mod:** an addon folder inside `Addons` that holds a `config.cpp`, or a source folder passed to `--against`. Its `$PBOPREFIX$`, `config.cpp` and `.c` files are read for names only.
- It never extracts a PBO, never writes to another mod's folder and never copies their files or code. The report holds class names, prefixes and paths, nothing else.

## Rules

Errors fail the check. Warnings are listed and do not.

| Rule | Severity | Finds |
|---|---|---|
| `prefix-same` | error | Your `$PBOPREFIX$` is the prefix of one of their addons. |
| `prefix-nested` | warning | One prefix sits inside the other, so the two can ship the same path. |
| `path-collision` | error | A file of yours has the same game path (prefix plus file) as one of theirs. |
| `cfgpatches-collision` | error | A `CfgPatches` class with the same name as one of theirs. |
| `class-collision` | error | A class one level inside a `Cfg` section (such as `CfgVehicles`) that they define too, when you do not require them. |
| `class-override` | warning | The same, but one of their `CfgPatches` classes is in your `requiredAddons[]`, so you change their class on purpose. |
| `vanilla-class-overlap` | warning | Both mods change a vanilla class, read from `P:\DZ\`. The mod loaded last wins each property it sets. |
| `script-class-collision` | error | A script `class` or `enum` they declare too. The scripts would not compile together. |
| `modded-class-overlap` | warning | A `modded class` both mods override. Each override must call `super` or the other mod loses its code. |
| `script-name-match` | warning | Their PBO header lists a `.c` file named after one of your classes, so they may declare or mod it too. |

Names are compared without case. Comments, strings and preprocessor lines are skipped. Forward declarations such as `class Clothing;` are not definitions.

## Output and exit codes

The first line is the verdict: `PASS` (exit 0, warnings allowed), `FAIL` (exit 1, at least one error, or the in-game gate did not pass) or `ERROR` (exit 2: bad arguments, no cached project, no mod folder, an `--against` mod that is not there, or no mods to compare with). Then one block per finding:

```
FAIL
- workspace/MyVest/$PBOPREFIX$  error prefix-same: $PBOPREFIX$ JM\CF\Scripts is also the prefix of @CF.
    theirs: @CF/Addons/scripts.pbo
    -> dayz-config-specialist: Give $PBOPREFIX$ a folder only your mod uses, usually the mod name, and move the files with it.
  scanned @CF: 3 PBO header(s), 0 unpacked addon(s)
  1 error(s), 0 warning(s)
```

With `--json` each finding has `rule`, `severity`, `mod` (theirs), `where` (yours, `file:line`), `other` (theirs), `message`, `owner` and `fix`, and `scanned` lists each compared mod with its PBO header count, unpacked addon count and any `.pbo` whose header could not be read. With `--ingame` the report gains `"ingame": {"deps", "server", "rc", "verdict", "report"}`, where `report` is the `/dayz-gate ingame` JSON.

## Limits

- Packed mods give only prefixes, paths and script file names. A `script-name-match` is a hint from a file name, not proof; `--ingame` gives the real answer.
- Classes are compared one level inside each `Cfg` section. Nested classes and `#include` files are not followed.
- Two of their mods are never compared with each other; only your mod with each of them.
- Without `P:\DZ\` a vanilla class both mods change is reported as `class-collision` or `class-override`, and the note says so.

## Do not

- Don't extract, unpack or copy another mod to get more out of this check. Use `--ingame`, or ask the user for that mod's source.
- Don't rename another mod's classes. Fix your own mod.
