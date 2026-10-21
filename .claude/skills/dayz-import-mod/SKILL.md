---
name: dayz-import-mod
description: "Links a DayZ mod folder kept elsewhere on disk into workspace/<ModName>/, or clones a GitHub link there, and creates its P:\\<ModName>\\ junction, so build, launch and clean skills work on it, offering to add missing scaffold files. Refuses Steam Workshop links. Use when you want to work on a mod repo kept outside the workspace or the user pastes a GitHub link to a mod."
argument-hint: "--source <path|github-link> [--name <ModName>] [--author <handle>] [--scaffold | --no-scaffold]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-import-mod

Bring an existing DayZ mod into Agentic-Z without copying it. The skill creates a directory link at `workspace/<ModName>/` pointing at your external folder (and the matching `P:\<ModName>\` junction) so all the DayZ skills - `/dayz-build-pbo`, `/dayz-launch-workbench`, `/dayz-clean-workspace`, etc. - operate on it like a native scaffold. Then it scans for missing scaffold pieces and asks per-piece whether to fill them in.

Use this when:

- You have an existing mod repo somewhere on disk (`C:\Users\you\repos\MyMod`, `D:\dayz-stuff\MyMod`, etc.) and don't want to move or duplicate it inside the Agentic-Z workspace.
- You're collaborating on a mod whose canonical location is somewhere else (a separate git repo, a shared drive) and just need it visible to the toolchain.

Paste a GitHub link instead of a path and the repo is cloned straight into `workspace/<ModName>/` (see "GitHub links" below). A Steam Workshop link is refused.

Alternative: clone your mod directly into `workspace/<ModName>/`. It then still needs the `P:\<ModName>\` link that build and launch skills check for: run `/dayz-add-scaffold <ModName> --piece junction`, then `/dayz-add-scaffold <ModName>` for any missing scaffold files.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\import_mod.py" [--source <path>] [--name <ModName>] [--scaffold | --no-scaffold] [--author <handle>]
```

| Argument | Required? | Notes |
|---|---|---|
| `--source <path>` | yes (or interactive) | Path to the existing mod folder (absolute or relative, `~` expanded), or a GitHub link to clone. If omitted on a TTY, the skill prompts for a path. |
| `--name <ModName>` | no | Override the name the mod is imported under. Defaults to the source folder's basename, validated against `[A-Za-z][A-Za-z0-9_]{0,63}`. Required if the basename has spaces or other invalid characters. |
| `--scaffold` | no | Auto-yes for every "scaffold this missing piece?" prompt. Required for non-TTY use when missing pieces would otherwise prompt. |
| `--no-scaffold` | no | Auto-no - link only, never write into the source folder. |
| `--author <handle>` | no | Author handle for a scaffolded `config.cpp`, cached for future runs. Same resolution chain as `/dayz-new-mod` (flag, cache, prompt) and used only when `config.cpp` is written. Pass it on a non-TTY run with `--scaffold` when no handle is cached yet. |

## What it does

1. Gates on `/dayz-preflight`.
2. Resolves and validates the source path (must exist, be a directory, not be inside `<repo>/workspace/`, not be a UNC path).
3. Derives the mod name (from `--name` or source basename), validates the name pattern.
4. Refuses if `workspace/<Name>/` already exists, or if `P:\<Name>\` exists pointing somewhere else (auto-cleans a stale link pointing at our about-to-be-created `workspace/<Name>/`).
   Also refuses, before linking anything, when scaffold pieces are missing, stdin is not a TTY, and neither `--scaffold` nor `--no-scaffold` was passed.
5. Creates `workspace/<Name>` → source path (symlink, junction fallback).
6. Creates `P:\<Name>\` → `workspace/<Name>` (matching `/dayz-new-mod`'s pattern, so `/dayz-clean-workspace` can detect it via the existing junction-target check). If this fails, the workspace link is rolled back.
   Then, like `/dayz-new-mod`, points the `/dayz-init` project cache at this project.
7. Scans for missing scaffold pieces (`config.cpp`, `$PBOPREFIX$`, `workbench/dayz.gproj`).
8. For each missing piece:
   - `--scaffold` → write it
   - `--no-scaffold` → skip
   - TTY default → prompt `Add to your source folder? [y/N]:`
9. Each "yes" is written by `/dayz-add-scaffold`'s writer, called in-process (one writer for both skills, and preflight runs only once). If a write fails or the writer skips the piece (for example `config.cpp` needs an author handle, none is cached and `--author` was not passed on a non-TTY run, or `workbench/` is skipped because DayZ Tools is not detected), the links stay in place, the skill names each failed piece with its retry command (`/dayz-add-scaffold <ModName> --piece <piece>`) and exits 1.

## GitHub links

`--source` also takes a git link:

- `https://github.com/<owner>/<repo>`, with or without `.git` or `https://`
- `https://github.com/<owner>/<repo>/tree/<branch>` clones that branch
- any other `https://.../<repo>.git` or `git@host:.../<repo>.git` remote

The mod name comes from the repo name (or `--name`). The repo is cloned with `git` straight into `workspace/<ModName>/` as a real folder, because a clone has no other home on disk. It then gets the same `P:\<ModName>\` junction, project cache update and scaffold check as a folder import, and accepted pieces are written into the clone. The same refusals apply before anything is cloned (the name, an existing `workspace/<Name>/`, a `P:\<Name>\` that points elsewhere). If a later step refuses (a non-TTY run with missing pieces and no `--scaffold` or `--no-scaffold`, or the junction fails), the clone is deleted again so a retry starts clean. `git` must be on `PATH`, and a private repo needs your usual git credentials. The scaffold check looks at the repo root, so a repo that keeps the mod in a subfolder needs a folder import of that subfolder instead.

`/dayz-clean-workspace --mod <Name>` never deletes a folder that holds `.git`, so it refuses a clone and prints the `rmdir` command. Push anything you want to keep, then delete the folder by hand (`cmd /c rmdir /s /q workspace\<Name>`) and remove the `P:\<Name>\` junction (`cmd /c rmdir P:\<Name>`). The import prints both commands at the end.

## Workshop links

A Steam Workshop link (`steamcommunity.com/sharedfiles/filedetails/?id=...` or `steam://url/CommunityFilePage/...`) is refused before preflight runs. A Workshop item holds the packed mod: PBOs with binarized models and configs, often signed or protected by its author, so there is no source in it to work on. The message says to import your own source folder or repo instead, or to ask the author for the source and their permission.

## Output

```
... (preflight output)

Path to existing mod folder: C:\Users\me\repos\MyMod
[OK]    Source validated: C:\Users\me\repos\MyMod
[INFO]  Derived mod name: MyMod
[OK]    workspace\MyMod -> C:\Users\me\repos\MyMod (junction)
[OK]    P:\MyMod -> workspace\MyMod (junction)

Scaffolding check:
  [OK]    config.cpp present
  [WARN]  $PBOPREFIX$ missing (needed for /dayz-build-pbo)
  [WARN]  workbench/dayz.gproj missing (needed for /dayz-launch-workbench --mod)

  Add $PBOPREFIX$ to your source folder? [y/N]: y
[OK]    $PBOPREFIX$ written
  Add workbench/dayz.gproj to your source folder? [y/N]: y
[OK]    workbench/dayz.gproj written (mod paths + filesystem mounts injected)
[OK]    workbench/DayZSetting.xml copied

Next steps:
  - Open in Workbench: /dayz-launch-workbench --mod MyMod
  - Build: /dayz-build-pbo MyMod
  - Remove the import (keeps your source intact): /dayz-clean-workspace --mod MyMod
```

## Refuses to run if

- `/dayz-preflight` returns non-zero (typically `P:\` not mounted).
- `--source` is a Steam Workshop link.
- `--source` missing and stdin isn't a TTY.
- Source path doesn't exist, isn't a directory, or is a UNC path (`\\server\share\...` - junctions can't target them on Windows).
- Source path is inside `<repo>/workspace/` (avoids self-referential / circular links). The error points at `/dayz-add-scaffold <Name> --piece junction`, which links a mod that is already in `workspace/`.
- Derived/given mod name fails the pattern (`[A-Za-z][A-Za-z0-9_]{0,63}`).
- `workspace/<Name>/` already exists (won't clobber).
- A git link is given and `git` is not on `PATH`, or `git clone` fails (its last lines are shown).
- `P:\<Name>\` exists as a real folder, or as a link pointing somewhere other than the new `workspace/<Name>/`.
- Non-TTY run with missing scaffold pieces and neither `--scaffold` nor `--no-scaffold` was passed. This check runs before any link is created, so nothing is left half-done.

### Stale-junction auto-clean

Same behavior as `/dayz-new-mod`: if `P:\<Name>\` exists as a junction pointing at the about-to-be-created `workspace/<Name>/`, the stale link is removed and the skill proceeds. Handles the case where a prior import was cleaned up but the junction wasn't.

## Cleanup behavior

`/dayz-clean-workspace --mod <Name>` recognizes imported mods automatically:

- The `workspace/<Name>/` link is removed via `cmd /c rmdir` (no recursion into the link target). Your source folder is never touched.
- The `P:\<Name>\` junction is removed (per existing logic: only when its target matches `workspace/<Name>/`).
- The `P:\Mods\@<Name>\` deployed dir is removed if it has the Agentic-Z ownership marker (written by `/dayz-build-pbo` and `/dayz-deploy-pbo`).

The plan labels an imported mod `(workspace-link) workspace\MyMod` (link removed, source kept) and a native scaffold `(workspace) workspace\NativeMod` (folder and contents removed).

## Do not

- Don't move or copy the source folder. The whole point of import is non-invasive - the source stays where it is.
- Don't write into the source folder unless the user explicitly answers yes to a scaffolding prompt (or passes `--scaffold`). The user's external repo has its own conventions; we don't surprise them.
- Don't bypass the preflight gate.
- Don't allow imports from inside `workspace/`. Self-referential or circular links break tooling and serve no purpose.
- Don't try to be clever about UNC paths or remote drives. Junctions can only target local paths; refuse with a clear hint.
