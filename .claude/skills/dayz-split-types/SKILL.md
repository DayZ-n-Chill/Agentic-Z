---
name: dayz-split-types
description: "Splits a monolithic DayZ types.xml into per-category files under db/types/ and registers them in cfgeconomycore.xml, backing up every changed file. Use when a mission's types.xml has grown too large to edit by hand or a server owner wants categorized economy files."
argument-hint: "<path-to-types.xml>"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-split-types

Take a monolithic `types.xml` and split it into categorized XML files under a `types/` subdirectory next to it, then point `cfgeconomycore.xml` (in the parent directory) at the non-empty ones and empty the original `types.xml`.

This skill wraps [DayZ-n-Chill/DayZ-TypeSplitterPro](https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro). The upstream `typeSplitter.py` is vendored under `vendor/`; this skill adds the CLI front-end (path argument, preflight gate, backups, the `<ce folder>` fix, emptying the original, result verification).

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\split.py" <path-to-types.xml>
```

Typical:

```cmd
python "<skill-dir>\split.py" .server\chernarus\mission\db\types.xml
```

## What it does

1. Preflight gate.
2. Validate that `<types.xml>` exists, has at least one `<type>` entry, and that `cfgeconomycore.xml` is one directory up (DayZ standard layout: `<mission>/cfgeconomycore.xml` + `<mission>/db/types.xml`).
3. Back up `types.xml`, `cfgeconomycore.xml` and any existing `types/` folder to `<name>.<YYYYMMDD-HHMMSS>.bak` beside them. Every run makes new backups, so reruns never replace an earlier one.
4. Copy the vendored `typeSplitter.py` next to `types.xml` (the upstream script finds `types.xml` through its own `__file__`), run it, then remove the temporary copy.
5. Fix `cfgeconomycore.xml`. The Central Economy reads a `<ce folder="...">` path relative to the mission root (vanilla keeps `env/` there, for example), but upstream writes `folder="types"` while the files are in `db/types/`. The wrapper rewrites the attribute to `db/types` and copies back any other `<ce>` blocks from the backup, which upstream deletes.
6. Verify the result: `types/` exists, every non-empty category file is listed under `<ce folder="db/types">`, and every listed file exists at `<mission>/<folder>/<name>`. The upstream script only logs its errors and always exits 0, so this check decides success. Exits 1 if a category file is not listed; a listed file that does not exist (for example from a restored custom `<ce>` block) is a warning.
7. Replace `types.xml` with an empty `<types>` stub. The server always loads `db/types.xml`, so leaving the full file in place would load every type twice and edits to the split files would not be the only definition. The original is in this run's backup.

## What gets created

- `<dir>/types/`, holding one file for each of the 19 categories: `ammo`, `armbands`, `ammo_boxes`, `animals`, `contamination`, `flags`, `staticObjs`, `vehicles`, `wrecks`, `zombies`, `seasonal`, `clothes`, `explosives`, `containers`, `food`, `tools`, `weapons`, `vehicleParts`, `uncategorized` (each `.xml`). Categories with no entries are still written as an empty `<types/>` file. Any existing `types/` folder is deleted and regenerated (after being backed up).
- `types.xml.<stamp>.bak`, `cfgeconomycore.xml.<stamp>.bak` and, if `types/` existed, `types.<stamp>.bak/`: backups from this run. Delete old ones when you no longer need them.
- `<mission>/cfgeconomycore.xml`: rewritten with one `<ce folder="db/types">` block listing each non-empty category file, followed by the `<ce>` blocks it had before. Upstream's formatter keeps only `<classes>` (its `<rootclass>` entries) and `<defaults>`; comments and any other element are dropped, so compare against the backup if you had hand edits.
- `<mission>/db/types.xml`: replaced with an empty `<types>` stub (see step 7). To split again, restore it from a `types.xml.<stamp>.bak` backup first.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `<types.xml>` doesn't exist, isn't named `types.xml`, isn't valid XML, or has no `<type>` entries (already split).
- `cfgeconomycore.xml` isn't in the parent directory (the upstream tool requires that layout).

## Output

```
[OK]    Backup: .server\chernarus\mission\db\types.xml.20261020-170428.bak
[OK]    Backup: .server\chernarus\mission\cfgeconomycore.xml.20261020-170428.bak
... (typeSplitter logging) ...

[OK]    Split into 14 non-empty category files in .server\chernarus\mission\db\types
        ammo.xml
        ammo_boxes.xml
        ... (more)
[OK]    Updated .server\chernarus\mission\cfgeconomycore.xml (<ce folder="db/types">)
[OK]    Emptied types.xml: its 2364 entries now load from db/types/ (original kept in types.xml.20261020-170428.bak)
```

## Attribution

The categorization logic and `cfgeconomycore.xml` formatting belong to [DayZ-n-Chill/DayZ-TypeSplitterPro](https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro). To update the vendored copy, fetch the latest upstream `typeSplitter.py` and replace `vendor/typeSplitter.py`, keeping its attribution header.

## Do not

- Don't modify the vendored `typeSplitter.py` to add features. Contribute upstream and re-vendor, so this skill stays a thin wrapper.
- Don't rely on the `.bak` files alone for a mission you care about. Commit the mission folder or copy it elsewhere first.
