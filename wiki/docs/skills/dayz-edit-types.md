---
name: dayz-edit-types
---

## Overview

Adds, updates or removes one &lt;type&gt; entry in a DayZ Central Economy types.xml (nominal, min, lifetime, restock, category, usage, value), backing the file up first. Use when a mod item needs a spawn entry, a loot value needs tuning, or an entry must be deleted.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-edit-types

Edit a DayZ Central Economy `types.xml` file programmatically: add a new spawn entry, update an existing one, or remove one. When the edit changes the file, it is backed up to `types.xml.bak` first.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\types_edit.py" <types.xml> <ClassName> [options]
python "<skill-dir>\types_edit.py" <types.xml> <ClassName> --remove
```

| Argument | Notes |
|---|---|
| `<types.xml>` | Path to the types.xml file. Typically `.server/<instance>/mission/db/types.xml`. |
| `<ClassName>` | The `name` attribute of the `<type>` block to upsert / remove. |
| `--remove` | Remove the entry instead of upserting. Other field flags ignored. |
| `--nominal N` | Target spawn count. Default for new entries: 1. |
| `--min N` | Minimum spawn count. Default for new entries: 0. |
| `--lifetime S` | Despawn timeout in seconds. Default for new entries: 3888000 (45 days). |
| `--restock S` | Restock interval in seconds. Default for new entries: 0. |
| `--cost N` | Spawn cost / weight. Default for new entries: 100. |
| `--category CAT` | Sets `<category name="CAT"/>`. Single value (replaces any existing). |
| `--usage TAG` | Add a `<usage name="TAG"/>`. Repeatable. Replaces all existing usages on the entry. |
| `--value TAG` | Add a `<value name="TAG"/>`. Repeatable. Replaces all existing values on the entry. |
| `--tag TAG` | Add a `<tag name="TAG"/>`. Repeatable. Replaces all existing tags on the entry. |

## What it does

1. Preflight gate.
2. Read and parse `<types.xml>` (comments are kept). Locate the `<type name="<ClassName>">` block.
3. Upsert mode (default):
   - If the block exists, update only the fields passed. Untouched fields stay as-is.
   - If the block doesn't exist, create one. Fields not passed get the defaults above, plus the standard `<flags .../>` element.
4. Remove mode (`--remove`): delete the block.
5. If nothing changed (entry already matches, or the entry to remove is absent), stop: no backup, no write.
6. Otherwise copy the file to `<types.xml>.bak` (overwriting any prior backup) and write the updated tree back.

Formatting: comments survive the round trip, but the whole file is re-indented with 4 spaces and gets an `<?xml version='1.0' encoding='utf-8'?>` declaration. Attribute order and blank lines are not preserved, so expect a whitespace diff the first time a hand-formatted file is edited.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `<types.xml>` doesn't exist.
- `<types.xml>` isn't valid XML.
- The root element is not `<types>` (for example `events.xml` or `globals.xml` passed by mistake).
- `<ClassName>` appears in more than one `<type>` block; merge them by hand first. Duplicates of other names only print a `[WARN]` listing them.
- `--nominal`, `--min`, `--lifetime`, `--restock` or `--cost` is negative (argparse usage error, exit 2).
- `--min` or `--nominal` would leave the entry with `min` greater than `nominal` (checked against the entry's existing or default value for the flag you did not pass). The file is left unchanged.

## Output

Add a new entry:

```
[OK]    Added <type name="MyMod_Vest"> nominal=1, min=0, lifetime=3888000, cost=100
[OK]    Backup: .server\chernarus\mission\db\types.xml.bak
[OK]    Wrote .server\chernarus\mission\db\types.xml
```

Update an existing entry:

```
[OK]    Updated <type name="MyMod_Vest">: nominal 1 -> 5, lifetime 3888000 -> 7776000
[OK]    Backup: .server\chernarus\mission\db\types.xml.bak
[OK]    Wrote .server\chernarus\mission\db\types.xml
```

Nothing to do:

```
[OK]    <type name="MyMod_Vest"> already matches; no change
```

## Do not

- Don't edit `<flags>` granular attributes (`count_in_cargo`, etc.); there is no option for them.
- Don't rely on `types.xml.bak` as history: each changing run overwrites it, so it only holds the file as it was before the most recent edit. Commit or copy the file yourself before a series of edits you may want to undo.
