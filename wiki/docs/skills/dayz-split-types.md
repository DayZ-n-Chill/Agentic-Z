---
name: dayz-split-types
---

## Overview

Splits a monolithic DayZ types.xml into per-category files (ammo, weapons, vehicles, food, clothes, and so on) under db/types/ and rewrites cfgeconomycore.xml to reference them, making timestamped backups of both files and any existing types/ folder first. Wraps the vendored DayZ-n-Chill DayZ-TypeSplitterPro script. Use when a mission's types.xml has grown too large to edit by hand or a server owner wants categorized economy files.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-split-types

Take a monolithic `types.xml` and split it into categorized XML files under a `types/` subdirectory next to it, then point `cfgeconomycore.xml` (in the parent directory) at the non-empty ones.

This skill wraps [DayZ-n-Chill/DayZ-TypeSplitterPro](https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro). The upstream `typeSplitter.py` is vendored under `vendor/`; this skill adds the CLI front-end (path argument, preflight gate, backups, result verification).

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
2. Validate that `<types.xml>` exists and `cfgeconomycore.xml` is one directory up (DayZ standard layout: `<mission>/cfgeconomycore.xml` + `<mission>/db/types.xml`).
3. Back up `types.xml`, `cfgeconomycore.xml` and any existing `types/` folder to `<name>.<YYYYMMDD-HHMMSS>.bak` beside them. Every run makes new backups, so reruns never replace an earlier one.
4. Copy the vendored `typeSplitter.py` next to `types.xml` (the upstream script finds `types.xml` through its own `__file__`), run it, then remove the temporary copy.
5. Verify the result: `types/` exists and every non-empty category file is listed in `cfgeconomycore.xml`. The upstream script only logs its errors and always exits 0, so this check decides success. Exits 1 if anything is missing.

## What gets created

- `<dir>/types/`, holding one file for each of the 19 categories: `ammo`, `armbands`, `ammo_boxes`, `animals`, `contamination`, `flags`, `staticObjs`, `vehicles`, `wrecks`, `zombies`, `seasonal`, `clothes`, `explosives`, `containers`, `food`, `tools`, `weapons`, `vehicleParts`, `uncategorized` (each `.xml`). Categories with no entries are still written as an empty `<types/>` file. Any existing `types/` folder is deleted and regenerated (after being backed up).
- `types.xml.<stamp>.bak`, `cfgeconomycore.xml.<stamp>.bak` and, if `types/` existed, `types.<stamp>.bak/`: backups from this run. Delete old ones when you no longer need them.
- `<mission>/cfgeconomycore.xml`: rewritten with one `<ce folder="types">` block listing each non-empty category file. Upstream removes every existing `<ce>` element and drops comments, so custom `<ce>` folders must be re-added by hand.

`types.xml` itself is left in place and unchanged.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `<types.xml>` doesn't exist or isn't named `types.xml`.
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
[OK]    Updated .server\chernarus\mission\cfgeconomycore.xml
```

## Attribution

The categorization logic and `cfgeconomycore.xml` formatting belong to [DayZ-n-Chill/DayZ-TypeSplitterPro](https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro). To update the vendored copy, fetch the latest upstream `typeSplitter.py` and replace `vendor/typeSplitter.py`, keeping its attribution header.

## Do not

- Don't modify the vendored `typeSplitter.py` to add features. Contribute upstream and re-vendor, so this skill stays a thin wrapper.
- Don't rely on the `.bak` files alone for a mission you care about. Commit the mission folder or copy it elsewhere first.
