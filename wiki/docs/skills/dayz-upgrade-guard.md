---
name: dayz-upgrade-guard
---

## Overview

Snapshots every vanilla class on P:\ (script classes with their parent and method signatures, config classes with their parent and the properties they set). After a DayZ update it takes a new snapshot, diffs it with the last one and lists the mod classes whose vanilla parents changed, with file:line and the reason. Can rebuild the search index afterwards. Use before and after a DayZ update, or when a mod broke after one.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-upgrade-guard

A DayZ update can move a vanilla class to a new parent, drop a method your mod overrides, or stop setting a config property your item inherits. The mod still packs, then fails in game. This skill finds those classes before you test.

A script does the work: it reads the vanilla files on `P:\`, saves a snapshot and compares two snapshots against your mod's classes. It starts no game and needs no DayZ Tools. The AI only reads the findings and hands each one to its owner.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## When to run it

1. **Before** a DayZ update, while `P:\` still holds the old game data: `snapshot`.
2. Update DayZ and unpack the new game data to `P:\` as you normally do.
3. **After** the update: `check`. It takes a new snapshot and compares it with the one from step 1.

If there is no earlier snapshot, `check` saves the first one as the baseline and says so. Run it again after the next update.

## How to run

```cmd
python "<skill-dir>\upgrade_guard.py" snapshot [--label 1.28]
python "<skill-dir>\upgrade_guard.py" check [<ModName> ...] [--mod-dir <folder>] [--label <text>] [--reindex] [--json]
python "<skill-dir>\upgrade_guard.py" diff [--old <snapshot> --new <snapshot>] [<ModName> ...] [--mod-dir <folder>] [--json]
```

| Argument | Notes |
|---|---|
| `snapshot` | Read every vanilla class and save a snapshot. `--label` adds text to the file name, such as the game version. |
| `check` | Take a snapshot now, diff it with the newest saved one and check the mods. When nothing changed it keeps the old snapshot instead of saving a copy. `--label` adds text to the new snapshot's file name. |
| `diff` | Compare two saved snapshots without reading `P:\`. With no `--old` and `--new` it uses the two newest. Use it to see a report again. |
| `<ModName>` | A mod under `workspace/` in the project cached by `/dayz-init`. With no name and no `--mod-dir`, every mod in `workspace/` is checked. |
| `--mod-dir` | Check this folder too. Repeat it for more folders. |
| `--reindex` | With `check`: when vanilla changed, rebuild the search index (`/dayz-search-index --full`) so search answers match the new files. It uses Voyage tokens, so it only runs when you ask. |
| `--json` | Print the full report as JSON after the verdict line. Stdout then holds only those two parts; the reindex note and the indexer's output go to stderr. |
| `--store`, `--p-root` | Another snapshot folder (default `~/.claude/dayz-upgrade-guard/`) or game data root (default `P:\`). |

## What a snapshot holds

| Kind | Read from | Kept per class |
|---|---|---|
| Script | every `.c` under `P:\scripts\` and `P:\DZ\` | parent, file and line, every method with its signature (default values and `override` dropped). Vanilla `modded class` parts are merged into the class. |
| Config | every `config.cpp` under `P:\DZ\` | the classes one level inside each `Cfg*` class, keyed in lower case as `cfgvehicles/clothing`, since config class names ignore case (vanilla writes both `CfgVehicles` and `cfgVehicles`): the name as vanilla spells it, parent, file and line, the names of the properties and subclasses it sets. A class that several addons extend is merged. |

A snapshot of the full game data takes about ten seconds and is about 10 MB.

A snapshot saved before config keys became case blind (format 1) is refused with an ERROR. Take a new snapshot; if the game has already been updated, the new one becomes the baseline for the next update.

## What it flags

| Reason | Means |
|---|---|
| `parent-removed` | A vanilla class your class is built on no longer exists. |
| `parent-changed` | A vanilla class in your class's chain now extends something else. |
| `override-removed` | Your class overrides a method that no vanilla class in its chain has any more. |
| `override-changed` | The vanilla method your class overrides has a new signature. |
| `members-removed` | No vanilla class in your item's config chain sets a property or subclass your item inherited and does not set itself any more. |
| `redeclared-parent` | Your config declares a vanilla class again with the old parent, and vanilla now gives it another. |

A script `modded class X` is checked against X itself; `class Y extends X` is checked against X. A script class built on another script class of the same mod (`MyVest extends MyVest_Base extends Clothing`) is followed through the mod's classes and checked against the first vanilla class, here `Clothing`. Config classes are not followed this way. A config class is checked against its direct parent in the same `Cfg*` class, so it is checked only when that parent is vanilla. A config class whose parent is a class of the mod (`MyVest_Black : MyVest_ColorBase`) is skipped and not counted; the mod base itself is checked when its own parent is vanilla. Classes built on other mods are not vanilla, so they are skipped too.

## Output and exit codes

The first line is the verdict: `PASS` (exit 0, no mod class affected), `FAIL` (exit 1, at least one) or `ERROR` (exit 2: bad arguments, no game data on `P:\`, fewer than two snapshots to diff, or a mod folder that does not exist). A missing mod folder is caught before `check` saves anything, so a mistyped name never uses up the update. `snapshot` prints the saved path instead. With `--json`, the first `check` prints `{"verdict": "PASS", "baseline": "<path>"}` after the verdict line.

```
FAIL
  old: ...\20261021-052257-1.27.json
  new: ...\20261104-190112-1.28.json
  Vanilla: script classes 4 added, 0 removed, 1 new parents, 3 with removed or changed methods; config classes ...
    script Clothing now extends ItemBase (was Clothing_Base)
  MyVest: 12 class(es) built on vanilla, 1 affected
  - workspace/MyVest/scripts/4_World/MyVest.c:3  MyVest_Base (from Clothing)
      parent-changed: vanilla Clothing now extends ItemBase (was Clothing_Base)
  Owners: script findings go to dayz-script-specialist, config findings to dayz-config-specialist.
```

## After a FAIL

- Script findings go to `dayz-script-specialist`, config findings to `dayz-config-specialist`. Each looks up the new vanilla class with the search tools and fixes the mod.
- Then run `/dayz-lint` and `/dayz-gate build` on the mod.

## Limits

- It compares class shapes, not behaviour. A method that keeps its signature but works differently is not flagged; `/dayz-gate ingame` and `/dayz-gate behavior` catch that.
- Config property values are not compared, only whether a property is still set.
- `#ifdef` branches are read as if all were on.
- `check` always compares with the newest saved snapshot. After an update the first `check` saves the new snapshot, so running `check` again says the vanilla classes did not change. Use `diff` to see the update report again.

## Do not

- Don't delete old snapshots before the after update `check` has run; it needs the one from before the update.
