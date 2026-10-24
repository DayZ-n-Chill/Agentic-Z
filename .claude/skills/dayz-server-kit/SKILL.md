---
name: dayz-server-kit
description: "Zips what a server owner needs to run a DayZ mod: types.xml entries for every spawnable class, the cfgeconomycore.xml lines that load them, the load order and the public .bikey. Never packs a .biprivatekey. Use when a mod is released, alongside /dayz-release-pack."
argument-hint: "<ModName> [--mission <folder or instance>] [--deps CF ...] [--out <folder>] [--json] | --mod-dir <folder> [...]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-server-kit

A script gathers the files and writes one zip. It starts no process and needs no DayZ Tools. The AI only reads the warnings, for example which entries are placeholders, and decides whether to rerun with a mission or real values.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\server_kit.py" <ModName> [options]
python "<skill-dir>\server_kit.py" --mod-dir <folder> [options]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--mod-dir` | Use any folder instead. Its name is the mod name unless `<ModName>` is given too. |
| `--mission` | A mission folder, or a test server instance name from `/dayz-add-server` (`chernarus` means `.server\chernarus\mission\`), to copy real types entries from. With `--mod-dir` the instance is looked up in the current folder, then in the project cached by `/dayz-init`. |
| `--deps` | Dependency mods in load order, with or without `@` (`--deps CF`). |
| `--out` | Output folder. Default `output\<ModName>-release\`, the same folder `/dayz-release-pack` writes to. |
| `--json` | Print the report as JSON. |

## What the zip holds

`<ModName>-server-kit.zip`:

| Member | What it is |
|---|---|
| `<ModName>_ce/types.xml` | A `<type>` entry for every spawnable class (scope 2 in `CfgVehicles`, `CfgWeapons` or `CfgMagazines`). |
| `cfgeconomycore-lines.xml` | `<ce folder="<ModName>_ce">` with `<file name="types.xml" type="types" />`. The folder is relative to the mission folder, so the owner puts `<ModName>_ce\` next to `db\`. |
| `load-order.txt` | The `-mod=` order, dependencies first, and any non vanilla `requiredAddons`. |
| `keys/<name>.bikey` | Each public key from `Keys\` in the mod or `P:\Mods\@<ModName>\Keys\`. |
| `README.txt` | What each file is for, and which entries are placeholders. |

Types entries are taken in this order, first match wins:

1. Every `<type>` in the mod's own types files: any `*.xml` under the mod folder whose root is `<types>` (not under `Addons`, `Keys` or `.git`).
2. With `--mission`: the entries for the mod's classes in `db\types.xml` and in every `type="types"` file its `cfgeconomycore.xml` lists, so a mission split by `/dayz-split-types` works.
3. A placeholder for each class still missing: the vanilla element order with `nominal` and `min` at 0, so the item does not spawn until the owner tunes it. Each one carries a `placeholder values` comment.

## Keys

Only `.bikey` files are packed. A `.biprivatekey` lets anyone sign PBOs as the author, so the script never reads one into the zip and refuses to write a zip that would hold one. A private key found inside the mod folder raises the `private-key-in-mod` warning: move it out of the mod.

## Warnings and exit codes

Exit 0 means the zip was written, with `[WARN]` lines for `placeholder-types`, `deps-unmapped`, `scope-unknown`, `no-bikey` and `private-key-in-mod` (the last four as in `/dayz-release-pack`). Exit 2 means it could not run: bad arguments, no cached project, no mod folder, no `config.cpp`, a `config.cpp` that does not parse, or a `--mission` that is not a folder or an instance.

## Do not

- Don't hand out a kit with placeholder entries without telling server owners to tune them.
- Don't copy a key into the zip by hand.
