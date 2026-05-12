---
name: dayz-edit-types
---

## Overview

Programmatically add, update, or remove an entry in DayZ's types.xml. Upserts a `&lt;type name="..."&gt;` block with the given attrs (nominal, min, lifetime, restock, cost, category, usage, value, tag). Auto-backs up the file before modifying. Idempotent — re-running with the same args is a no-op or a clean update.

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-edit-types

Edit a DayZ Central Economy `types.xml` file programmatically — add a new spawn entry, update an existing one, or remove one. Backs up the file to `types.xml.bak` before any change.

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
2. Read and parse `<types.xml>`. Locate the `<type name="<ClassName>">` block (or note its absence).
3. **Upsert mode (default):**
   - If the block exists, update only the fields you passed. Untouched fields stay as-is.
   - If the block doesn't exist, create one. Fields you didn't pass get DayZ defaults (see table above). Always includes the standard `<flags ... />` element.
4. **Remove mode (`--remove`):** delete the block entirely. No-op if it didn't exist.
5. Back up to `<types.xml>.bak` (overwriting any prior backup).
6. Write the updated tree back to `<types.xml>`.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `<types.xml>` doesn't exist.
- `<types.xml>` isn't valid XML.

## Output

Add new entry:

```
[OK]    Added <type name="MyMod_Vest"> with 1/0 lifetime 3888000 cost 100
[OK]    Backup: workspace\_server\missions\dayzOffline.chernarusplus\db\types.xml.bak
[OK]    Wrote workspace\_server\missions\dayzOffline.chernarusplus\db\types.xml
```

Update existing:

```
[OK]    Updated <type name="MyMod_Vest">: nominal 1 -> 5, lifetime 3888000 -> 7776000
[OK]    Backup written
[OK]    types.xml updated
```

Remove:

```
[OK]    Removed <type name="MyMod_Vest">
[OK]    types.xml updated
```

## Do not

- Don't touch `<flags>` granular attributes (`count_in_cargo`, etc.) — there's no flag for that yet because most modders never edit them once defaults are set. Add flags as separate options later if real demand emerges.
- Don't rewrite the whole file's whitespace / formatting. Edit in place via `xml.etree.ElementTree`; preserve the user's structure as much as possible.
- Don't skip the backup. The `.bak` is cheap insurance; the user might paste in args wrong.
