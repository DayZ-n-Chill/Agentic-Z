---
name: dayz-balance
description: "Compares a DayZ mod's item stats with similar vanilla items and flags outliers with file:line and the vanilla median. Use it after writing item configs, or when the user asks whether an item is overpowered, too heavy or balanced."
argument-hint: "<ModName> [--json] [--ratio 1.5] [--min-peers 3] | --mod-dir <folder> [--vanilla-root P:\\]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-balance

A script reads the mod's `config.cpp` files and the unpacked vanilla configs on `P:\DZ\`, and measures each mod item against the vanilla items that share its parent class. It checks weight, health, damage, protection, cargo capacity and maximum quantity, and lists every stat far outside vanilla with file:line, the vanilla median and the closest vanilla items. It starts no process and needs no DayZ Tools. Reading all of `P:\DZ\` takes about five seconds. The script only measures. The AI reads the outliers and asks whether each one is intended; a mod may want a tougher vest on purpose.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\balance.py" <ModName> [--json]
python "<skill-dir>\balance.py" --mod-dir <folder> [--json]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--mod-dir` | Check any folder instead. Its name is the mod name unless `<ModName>` is given too. |
| `--vanilla-root` | The folder that holds the unpacked `DZ\` data. Default `P:\`. |
| `--ratio` | How many times above or below the vanilla median a value must be to count. Default `1.5`. |
| `--min-peers` | The fewest vanilla items needed to judge a stat. Default `3`. |
| `--json` | Print the full report as JSON after the verdict line. |

Run `/dayz-lint` first if the config has never been checked. A `config.cpp` that does not parse stops balance with an error.

## What it compares

Only stats the mod sets itself, on the item or on a mod base class above it. A stat the item inherits from vanilla is the vanilla value and is never flagged.

| Stat | Read from |
|---|---|
| `weight` | `weight` |
| `health` | `DamageSystem > GlobalHealth > Health > hitpoints` |
| `damage.health`, `damage.blood`, `damage.shock` | `DamageApplied > Health, Blood, Shock > damage` in `CfgAmmo`, the damage a bullet or melee hit deals |
| `protection.<kind>.<type>` | `DamageSystem > GlobalArmor > <kind> > <type> > damage`, for example `protection.projectile.health`. These are multipliers on damage taken, so a low value means more protection. |
| `protection.<name>` | `Protection > <name>`, for example `protection.biological` on masks. These are coverage, so a high value means more protection: the best vanilla mask has `biological=1` and weaker ones `0.25`. |
| `capacity` | `itemsCargoSize[]`, as width times height in cells |
| `quantity` | `varQuantityMax` |

An item is a class with `scope = 2` in `CfgVehicles`, `CfgWeapons` or `CfgMagazines`. In `CfgAmmo` every class counts unless it sets `scope = 0` itself, because vanilla ammo is `scope = 1` and the melee damage classes inherit `scope = 0`.

## How peers are picked

1. Walk up from the mod item, past any mod base classes, to the nearest vanilla class. For a vest that inherits `PlateCarrierVest` that is `PlateCarrierVest`.
2. The peers are that class and every vanilla item below it, each with its own inherited stats. Classes the mod redefines are left out.
3. When fewer than `--min-peers` peers have the stat, go up one vanilla parent and try again, at most twice. If that is still too few, the stat is not judged.
   3a. A wider group mixes item kinds (a mask's parent `Clothing` also holds backpacks, boots and belts), so after going up a parent only the peers that share an `inventorySlot[]` with the mod item are kept, and the report names the group as, for example, `Clothing in slot Mask`. When that leaves fewer than `--min-peers`, or the item has no slot, the whole group is used.

A value is an outlier when it is outside the peers' whole range and at least `--ratio` times away from their median.

## Output and exit codes

The first line is the verdict: `PASS` (exit 0, no outliers), `FLAG` (exit 1, at least one outlier) or `ERROR` (exit 2: bad arguments, no cached project, no mod folder, no `config.cpp`, one that does not parse, or no vanilla data at `--vanilla-root`). Then one entry per outlier, and the items that were not compared:

```
FLAG
- workspace/MyVest/config.cpp:12  MyVest_Plate health = 5000: tougher than vanilla, 22.22x the median 225 of 6 vanilla items under PlateCarrierVest (range 225 to 225)
    closest: PlateCarrierVest 225, PlateCarrierVest_Black 225, PlateCarrierVest_Camo 225, PlateCarrierVest_Desert 225, PlateCarrierVest_Green 225
  not compared: MyVest_Gadget has no vanilla parent (parent MyVest_Unknown)
  1 outlier(s) in 2 item(s)
```

With `--json` each finding has `item`, `section`, `stat`, `value`, `file`, `line`, `peer_base`, `peer_count`, `median`, `min`, `max`, `direction` (`high` or `low`), `meaning`, `ratio` and the closest `peers`. Items not compared are under `skipped` with a `reason`.

## After the run

- For each outlier, tell the user the item, the stat, the vanilla median and the closest vanilla items, and ask whether it is intended. Do not change a value on your own.
- When the user wants a value changed, hand the class to its owner: clothing and vests to `dayz-wearables-specialist`, firearms, magazines and ammo to `dayz-weapon-specialist`, everything else to `dayz-config-specialist`.

## Limits

- Stats that depend on script code (`OnStoreLoad`, custom damage handling) are not seen.
- Only the four item sections are read. Vehicles are compared like any `CfgVehicles` item, which says little about how they drive.
- `#include` files are not followed, the same as `/dayz-lint`.
