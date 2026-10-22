---
name: dayz-edit-types
description: "Adds, updates or removes one <type> entry in a DayZ Central Economy types.xml (nominal, min, lifetime, restock, category, usage, value), or checks a pasted chunk of many <type> entries and merges them all, backing the file up first. Use when a mod item needs a spawn entry, a loot value needs tuning, an entry must be deleted, or the user pastes types.xml entries."
argument-hint: "<types.xml> (<ClassName> [--nominal N] [--min N] [--lifetime S] [...] | <ClassName> --remove | --merge <chunk|->) [--dry-run]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-edit-types

Edit a DayZ Central Economy `types.xml` file programmatically: add a new spawn entry, update an existing one, or remove one. When the edit changes the file, it is backed up to `types.xml.bak` first.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\types_edit.py" <types.xml> <ClassName> [options] [--dry-run]
python "<skill-dir>\types_edit.py" <types.xml> <ClassName> --remove [--dry-run]
```

| Argument | Notes |
|---|---|
| `<types.xml>` | Path to the types.xml file. Typically `.server/<instance>/mission/db/types.xml`. |
| `<ClassName>` | The `name` attribute of the `<type>` block to upsert / remove. |
| `--remove` | Remove the entry instead of upserting. Other field flags ignored. |
| `--merge <chunk\|->` | Instead of a `<ClassName>`: check every `<type>` in a pasted chunk (a file, or `-` for stdin) and merge them all in one write. See Merge a pasted chunk below. |
| `--dry-run` | Works in every mode. Reports the change and the name warnings, then writes nothing (no backup either). Use it to preview an edit, since every write re-indents the whole file. |
| `--nominal N` | Target spawn count. Default for new entries: 1. |
| `--min N` | Minimum spawn count. Default for new entries: 0. |
| `--lifetime S` | Despawn timeout in seconds. Default for new entries: 14400 (4 hours, the usual vanilla loot lifetime; storage items such as barrels use 3888000). |
| `--restock S` | Restock interval in seconds. Default for new entries: 0. |
| `--cost N` | Spawn cost / weight. Default for new entries: 100. |
| (no flag) | New entries also get `<quantmin>-1</quantmin>` and `<quantmax>-1</quantmax>` (not a quantity item), as every vanilla `<type>` has. Existing entries keep their values. |
| `--category CAT` | Sets `<category name="CAT"/>`. Single value (replaces any existing). |
| `--usage TAG` | Add a `<usage name="TAG"/>`. Repeatable. Replaces all existing usages on the entry. |
| `--value TAG` | Add a `<value name="TAG"/>`. Repeatable. Replaces all existing values on the entry. |
| `--tag TAG` | Add a `<tag name="TAG"/>`. Repeatable. Replaces all existing tags on the entry. |

## What it does

1. Preflight gate.
2. Read and parse `<types.xml>` (comments are kept). Locate the `<type name="<ClassName>">` block.
3. Upsert mode (default):
   - If the block exists, update only the fields passed. Untouched fields stay as-is.
   - If the block doesn't exist, create one. Fields not passed get the defaults above, plus the vanilla standard flags (`count_in_map=1`, everything else 0). Children are written in vanilla order: `nominal`, `lifetime`, `restock`, `min`, `quantmin`, `quantmax`, `cost`, `flags`, then `category`, `tag`, `usage`, `value`. An edit that adds a name puts it in the same place among the existing children.
4. Remove mode (`--remove`): delete the block.
5. Name check (upsert mode): the entry's `<category>`, `<usage>`, `<value>` and `<tag>` names are checked against the mission's `cfglimitsdefinition.xml`, found next to `db/` (`<types.xml>\..\..\`). A `user=` group is checked against `cfglimitsdefinitionuser.xml` when it exists; without that file `user=` groups are not checked. Each name the file does not define prints `[WARN] usage name "Militar" is not defined in cfglimitsdefinition.xml`, because the Central Economy ignores or rejects it. The edit still goes ahead. When `cfglimitsdefinition.xml` is not there (a types file kept in a mod folder), the check is skipped with a note.
6. If nothing changed (entry already matches, or the entry to remove is absent), or `--dry-run` was passed, stop: no backup, no write.
7. Otherwise copy the file to `<types.xml>.bak` (overwriting any prior backup) and write the updated tree back.

## Merge a pasted chunk

When the user pastes `types.xml` entries, save the text to a file (or pipe it on stdin with `-`) and merge it:

```cmd
python "<skill-dir>\types_edit.py" <types.xml> --merge <chunk.xml> [--dry-run]
python "<skill-dir>\types_edit.py" <types.xml> --merge - < chunk.xml
```

The chunk can be bare `<type>` blocks or a whole `<types>` file, with or without the XML declaration. Every entry is checked before anything is written. These are errors, and any one of them stops the whole merge with the file unchanged:

- a `<type>` without a name, or a name listed twice in the chunk
- a count, lifetime, restock or cost that is not a whole number or is negative
- `min` greater than `nominal`
- `quantmin` or `quantmax` outside -1 and 0 to 100, or `quantmin` greater than `quantmax`
- a `<flags>` value other than 0 or 1
- a `<category>`, `<usage>`, `<value>` or `<tag>` without a name
- a name the target file already lists twice

A missing standard child (`nominal`, `lifetime`, `restock`, `min`, `quantmin`, `quantmax`, `cost`, `flags`), an unknown element or an unknown flag is a `[WARN]` and does not stop the merge. So is a category, usage, value or tag name that the mission's `cfglimitsdefinition.xml` does not define (the same name check as upsert mode, skipped with a note when that file is absent).

Then each entry is merged: a new name is added at the end, a name already in the file has its whole block replaced where it stands, and an identical block is left alone. The file is backed up to `types.xml.bak` once and written once. `--dry-run` checks and reports the same lines and writes nothing.

```
[OK]    Checked 2 <type> entries
[OK]    Added <type name="MyMod_Vest">
[OK]    Replaced <type name="AKM">: nominal 10 -> 12, min 5 -> 6
[OK]    Backup: .server\chernarus\mission\db\types.xml.bak
[OK]    Wrote .server\chernarus\mission\db\types.xml
```

Formatting: comments survive the round trip, both inside `<types>` and before or after it (such as a `<!-- MyMod types -->` header line), but the whole file is re-indented with 4 spaces and gets an `<?xml version='1.0' encoding='utf-8'?>` declaration. Attribute order and blank lines are not preserved, so expect a whitespace diff the first time a hand-formatted file is edited.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- Neither `<ClassName>` nor `--merge` is given, or both are (argparse usage error, exit 2).
- `<types.xml>` doesn't exist.
- `<types.xml>` isn't valid XML.
- The root element is not `<types>` (for example `events.xml` or `globals.xml` passed by mistake).
- `<ClassName>` appears in more than one `<type>` block; merge them by hand first. Duplicates of other names only print a `[WARN]` listing them.
- `--nominal`, `--min`, `--lifetime`, `--restock` or `--cost` is negative (argparse usage error, exit 2).
- `--min` or `--nominal` would leave the entry with `min` greater than `nominal` (checked against the entry's existing or default value for the flag you did not pass). The file is left unchanged.

## Output

Add a new entry:

```
[OK]    Added <type name="MyMod_Vest"> nominal=1, min=0, lifetime=14400, cost=100
[OK]    Backup: .server\chernarus\mission\db\types.xml.bak
[OK]    Wrote .server\chernarus\mission\db\types.xml
```

Update an existing entry:

```
[OK]    Updated <type name="MyMod_Vest">: nominal 1 -> 5, lifetime 14400 -> 28800
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
