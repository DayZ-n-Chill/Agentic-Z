---
name: dayz-split-types
---

# /dayz-split-types

Take a monolithic `types.xml` and split it into 18 categorized XML files (`ammo.xml`, `weapons.xml`, `vehicles.xml`, `food.xml`, `clothes.xml`, etc.) under a `types/` subdirectory next to it. Auto-updates `cfgeconomycore.xml` (in the parent directory) with the new file references. Backs up the original first.

This skill wraps **[DayZ-n-Chill/DayZ-TypeSplitterPro](https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro)** by DayZ-n-Chill. The upstream `typeSplitter.py` is vendored verbatim under `vendor/`; this skill provides a CLI front-end (path arg, preflight gate, backup, output verification).

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-split-types\split.py <path-to-types.xml>
```

Typical:

```cmd
python .claude\skills\dayz-split-types\split.py workspace\_server\missions\dayzOffline.chernarusplus\db\types.xml
```

## What it does

1. Preflight gate.
2. Validate `<types.xml>` exists and `cfgeconomycore.xml` is one directory up (DayZ standard layout: `<mission>/cfgeconomycore.xml` + `<mission>/db/types.xml`).
3. Back up `<types.xml>` to `<types.xml>.bak`.
4. Copy the vendored `typeSplitter.py` next to your `types.xml` (the upstream script uses `__file__` to find `types.xml`), run it with `python`, then remove the temp copy.
5. Verify `<dir>/types/` was created and report the categorized files written.

## What gets created

- `<dir>/types/` — directory containing one XML per category (only categories with at least one entry are emitted):
  - `ammo.xml`, `armbands.xml`, `ammo_boxes.xml`, `animals.xml`, `contamination.xml`, `flags.xml`, `staticObjs.xml`, `vehicles.xml`, `wrecks.xml`, `zombies.xml`, `seasonal.xml`, `clothes.xml`, `explosives.xml`, `containers.xml`, `food.xml`, `tools.xml`, `weapons.xml`, `vehicleParts.xml`, `uncategorized.xml`
- `<types.xml>.bak` — backup of the original.
- `<mission>/cfgeconomycore.xml` — updated with `<ce folder="types">` + `<file name="..." type="types"/>` entries pointing at each new categorized file.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `<types.xml>` doesn't exist or isn't named `types.xml`.
- `cfgeconomycore.xml` isn't in the parent directory (the upstream tool requires that layout).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    Backup: workspace\_server\missions\dayzOffline.chernarusplus\db\types.xml.bak
... (typeSplitter logging) ...
[OK]    Split into 14 files in workspace\_server\missions\dayzOffline.chernarusplus\db\types
        ammo.xml
        ammo_boxes.xml
        animals.xml
        ... (more)
[OK]    Updated workspace\_server\missions\dayzOffline.chernarusplus\cfgeconomycore.xml
```

## Attribution

The categorization logic and `cfgeconomycore.xml` formatting belong to **[DayZ-n-Chill/DayZ-TypeSplitterPro](https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro)**. This skill is a CLI wrapper around the vendored upstream script. To update the vendored copy, fetch the latest from the upstream repo and replace `vendor/typeSplitter.py`.

## Do not

- Don't modify the vendored `typeSplitter.py` to add features. If you need new categorization or behavior, contribute upstream and re-vendor — this skill stays a thin wrapper so updates remain trivial.
- Don't run this without a backup of the mission. Even with our `.bak`, splitting + cfgeconomycore rewrite is a meaningful change. Commit your mission edits to git or copy the mission folder elsewhere first if you're paranoid.
