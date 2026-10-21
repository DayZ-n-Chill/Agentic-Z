---
name: dayz-release-pack
---

## Overview

Writes the release texts for a DayZ mod in one go: the Steam Workshop description, a changelog entry from the mod's git history, the classname list from config.cpp and the server owner install notes. Every fact comes from the mod's files; anything the script cannot know is a warning to settle. Use when a mod is ready to publish or update on the Workshop.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-release-pack

A script reads the mod and writes four files. It starts no process except `git`, needs no DayZ Tools and takes about a second. The AI only reads the warnings, settles them and rereads the texts before they are published.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\release_pack.py" <ModName> [options]
python "<skill-dir>\release_pack.py" --mod-dir <folder> [options]
```

| Argument | Notes |
|---|---|
| `<ModName>` | A mod under `workspace/<ModName>/` in the project cached by `/dayz-init`. |
| `--mod-dir` | Use any folder instead. Its name is the mod name unless `<ModName>` is given too. |
| `--version` | The version for the changelog heading and the Workshop text. Default `Unreleased`. |
| `--since` | Git ref the changelog starts after. Default: the latest tag when the mod folder is its own repository. Inside a bigger repository (an Agentic-Z clone) it is the newest `chore(release)` commit that touched the mod folder, and the script prints which one. With no such commit the entry lists the folder's whole history and warns `changelog-full-history`. |
| `--deps` | Dependency mods in load order, with or without `@` (`--deps CF`). Map each non vanilla `requiredAddons` entry to the Workshop mod that ships it. |
| `--out` | Output folder. Default `output\<ModName>-release\`. |
| `--json` | Print the report as JSON. |

## What it writes

| File | Built from |
|---|---|
| `workshop-description.txt` | Steam BBCode: the title and summary from `mod.cpp` (`name`, `overview`) or the first paragraph of `README.md`, the spawnable items, the requirements, a server owner line and the changes. |
| `changelog.md` | One entry: `## <version> (<date>)` with `Added` (`feat:`), `Fixed` (`fix:`) and `Changed` (everything else) from the commits that touched the mod folder. Merges and `chore(release)` commits are left out. |
| `classnames.md` | Every class in `CfgVehicles`, `CfgWeapons` and `CfgMagazines` whose scope is 2, with section, parent and display name. Scope is followed through parents in the same file, and `public`, `protected` and `private` count as 2, 1 and 0. |
| `server-install.md` | Copy the `@mod`, copy the `.bikey` into `keys\`, the `-mod=` load order, the types files from `/dayz-server-kit`, restart. |

The docs writer merges `changelog.md` into `workspace/<ModName>/CHANGELOG.md` and the classnames into the README.

## Warnings

The script exits 0 with `[WARN]` lines when something needs a person or the AI:

| Warning | What to do |
|---|---|
| `summary-missing` | Neither `mod.cpp` nor `README.md` has a summary, so the Workshop text holds a placeholder line. Write one sentence there. |
| `deps-unmapped` | `requiredAddons` lists addons that are not vanilla. Find the Workshop mod that ships each and rerun with `--deps`. |
| `scope-unknown` | A class sets no scope and takes it from a parent outside the mod. Check each one in `classnames.md` under "Check by hand". |
| `no-bikey` | No `.bikey` in `Keys\` or `P:\Mods\@<ModName>\Keys\`. Sign the PBO before release. |
| `private-key-in-mod` | A `.biprivatekey` sits inside the mod folder. It is never written anywhere, but move it out of the mod so it can never ship. |
| `no-git` | The mod folder is not in a git repository, so the changelog entry is empty. |
| `changelog-full-history` | The mod sits inside a bigger repository and no `chore(release)` commit touched its folder, so the entry lists every change it ever had. Rerun with `--since <ref>` to limit the entry, or commit the release as `chore(release): <version>` so the next run starts after it. |
| `changelog-empty` | No commits touched the mod folder since the start ref, so the entry lists no changes. Commit the changes first, or pass an earlier `--since`. |

Exit 2 means it could not run: bad arguments, no cached project, no mod folder, no `config.cpp`, a `config.cpp` that does not parse (run `/dayz-lint`), or a `--since` ref that is not in the history.

## Then

Run `/dayz-server-kit <ModName>` to zip the types entries, the `cfgeconomycore.xml` lines, the load order and the public key for server owners. It writes to the same release folder.

## Do not

- Don't publish the Workshop text with a placeholder line or a `[WARN]` still open.
- Don't type classnames or dependencies by hand into the texts; fix the mod and rerun.
