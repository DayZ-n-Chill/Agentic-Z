---
name: dayz-import-mod
description: Import an existing DayZ mod folder (clone or local repo living outside this workspace) into workspace/<ModName>/ via a directory link, and create the matching P:\<ModName>\ junction so the rest of the DayZ skills (build, launch, clean) work on it. Optionally fills in missing scaffold pieces (config.cpp, $PBOPREFIX$, workbench/dayz.gproj) by prompting y/N per piece. Source folder is never moved or copied - the link points at it where it lives.
argument-hint: "--source <path> [--name <ModName>] [--scaffold | --no-scaffold]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-import-mod

Bring an existing DayZ mod into Agentic-Z without copying it. The skill creates a directory link at `workspace/<ModName>/` pointing at your external folder (and the matching `P:\<ModName>\` junction) so all the DayZ skills - `/dayz-build-pbo`, `/dayz-launch-workbench`, `/dayz-clean-workspace`, etc. - operate on it like a native scaffold. Then it scans for missing scaffold pieces and asks per-piece whether to fill them in.

Use this when:

- You have an existing mod repo somewhere on disk (`C:\Users\you\repos\MyMod`, `D:\dayz-stuff\MyMod`, etc.) and don't want to move or duplicate it inside the Agentic-Z workspace.
- You're collaborating on a mod whose canonical location is somewhere else (a separate git repo, a shared drive) and just need it visible to the toolchain.

Alternative: clone your mod directly into `workspace/<ModName>/` - no import needed.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\import_mod.py" [--source <path>] [--name <ModName>] [--scaffold | --no-scaffold]
```

| Argument | Required? | Notes |
|---|---|---|
| `--source <path>` | yes (or interactive) | Path to the existing mod folder (absolute or relative, `~` expanded). If omitted on a TTY, the skill prompts for it. |
| `--name <ModName>` | no | Override the name the mod is imported under. Defaults to the source folder's basename, validated against `[A-Za-z][A-Za-z0-9_]{0,63}`. Required if the basename has spaces or other invalid characters. |
| `--scaffold` | no | Auto-yes for every "scaffold this missing piece?" prompt. Required for non-TTY use when missing pieces would otherwise prompt. |
| `--no-scaffold` | no | Auto-no - link only, never write into the source folder. |

## What it does

1. Gates on `/dayz-preflight`.
2. Resolves and validates the source path (must exist, be a directory, not be inside `<repo>/workspace/`, not be a UNC path).
3. Derives the mod name (from `--name` or source basename), validates the name pattern.
4. Refuses if `workspace/<Name>/` already exists, or if `P:\<Name>\` exists pointing somewhere else (auto-cleans a stale link pointing at our about-to-be-created `workspace/<Name>/`).
5. Creates `workspace/<Name>` → source path (symlink, junction fallback).
6. Creates `P:\<Name>\` → `workspace/<Name>` (matching `/dayz-new-mod`'s pattern, so `/dayz-clean-workspace` can detect it via the existing junction-target check).
7. Scans for missing scaffold pieces (`config.cpp`, `$PBOPREFIX$`, `workbench/dayz.gproj`).
8. For each missing piece:
   - `--scaffold` → write it
   - `--no-scaffold` → skip
   - TTY default → prompt `Add to your source folder? [y/N]:`
9. Each "yes" delegates to `/dayz-add-scaffold --piece <name> <ModName>` so the writer logic stays in one place.

## Output

```
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
- `--source` missing and stdin isn't a TTY.
- Source path doesn't exist, isn't a directory, or is a UNC path (`\\server\share\...` - junctions can't target them on Windows).
- Source path is inside `<repo>/workspace/` (avoids self-referential / circular links - the mod is already in workspace, no import needed).
- Derived/given mod name fails the pattern (`[A-Za-z][A-Za-z0-9_]{0,63}`).
- `workspace/<Name>/` already exists (won't clobber).
- `P:\<Name>\` exists as a real folder, or as a link pointing somewhere other than the new `workspace/<Name>/`.
- Non-TTY run with missing scaffold pieces and neither `--scaffold` nor `--no-scaffold` was passed (refuses to silently skip without an explicit decision).

### Stale-junction auto-clean

Same behavior as `/dayz-new-mod`: if `P:\<Name>\` exists as a junction pointing at the about-to-be-created `workspace/<Name>/`, the stale link is removed and the skill proceeds. Handles the case where a prior import was cleaned up but the junction wasn't.

## Cleanup behavior

`/dayz-clean-workspace --mod <Name>` recognizes imported mods automatically:

- The `workspace/<Name>/` link is removed via `cmd /c rmdir` (no recursion into the link target). **Your source folder is never touched.**
- The `P:\<Name>\` junction is removed (per existing logic: only when its target matches `workspace/<Name>/`).
- The `P:\Mods\@<Name>\` deployed dir is removed if it has the Agentic-Z ownership marker (written by `/dayz-build-pbo`).

The plan output distinguishes imported mods from native scaffolds:

```
(workspace-link) workspace\MyMod -> C:\Users\me\repos\MyMod   (link removed; source kept)
(workspace)      workspace\NativeMod                          (folder + contents removed)
```

## Do not

- Don't move or copy the source folder. The whole point of import is non-invasive - the source stays where it is.
- Don't write into the source folder unless the user explicitly answers yes to a scaffolding prompt (or passes `--scaffold`). The user's external repo has its own conventions; we don't surprise them.
- Don't bypass the preflight gate.
- Don't allow imports from inside `workspace/`. Self-referential or circular links break tooling and serve no purpose.
- Don't try to be clever about UNC paths or remote drives. Junctions can only target local paths; refuse with a clear hint.
