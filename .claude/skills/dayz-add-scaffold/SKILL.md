---
name: dayz-add-scaffold
description: Add missing DayZ mod scaffolding pieces (config.cpp stub, $PBOPREFIX$, workbench/dayz.gproj + DayZSetting.xml, README, .gitkeeps) into an EXISTING workspace/<ModName>/ folder. Idempotent - never overwrites files that are already present. Used by /dayz-import-mod after symlinking an external mod, but also runnable directly when you cloned a mod into workspace/ manually and want the standard skeleton filled in.
---

# /dayz-add-scaffold

Companion to `/dayz-new-mod`. Where `dayz-new-mod` creates a fresh project from nothing, `dayz-add-scaffold` fills missing scaffold pieces into a folder that already exists - without touching anything that's already there.

Use this when:

- You cloned someone else's mod into `workspace/<ModName>/` and need `workbench/dayz.gproj` to open it in Workbench, or `$PBOPREFIX$` to build it.
- You used `/dayz-import-mod` to symlink an external repo and answered yes to the "scaffold this missing piece?" prompt - the import skill calls this skill to do the actual writing.
- You're upgrading an older scaffold that pre-dates the workbench-folder convention.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-add-scaffold\add_scaffold.py <ModName> [--piece config|prefix|workbench|readme|skeleton|all] [--author "YourHandle"]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName>` | yes | Folder name under `workspace/`. The folder must already exist (real or a link). Same `[A-Za-z][A-Za-z0-9_]{0,63}` pattern as `/dayz-new-mod`. |
| `--piece` | no | Default `all` = scan and add only missing pieces. Pick one to scaffold a single piece even if others are missing. |
| `--author` | no | Author handle for `config.cpp`. Same resolution chain as `/dayz-new-mod`: flag → cache → interactive prompt → fail. Skipped if config.cpp already exists. |

### Pieces

| Piece | What it writes | When |
|---|---|---|
| `config` | `config.cpp` (CfgPatches + CfgMods stub) | only if missing |
| `prefix` | `$PBOPREFIX$` (contains `<ModName>`) | only if missing |
| `workbench` | `workbench/dayz.gproj` (vanilla copy + injected mod paths + dual FileSystem mounts) and `workbench/DayZSetting.xml` | gproj only if missing; xml only if missing. Skips with warning if DayZ Tools not detected. |
| `readme` | `README.md` (light onboarding notes) | only if missing |
| `skeleton` | `scripts/3_Game/`, `scripts/4_World/`, `scripts/5_Mission/`, `data/`, `gui/` (each with `.gitkeep`) | each subfolder only if missing |
| `all` | runs every piece above in order | default |

Whatever piece you pick, the skill is **idempotent** - running it twice on the same folder is a no-op the second time.

## Refuses to run if

- `/dayz-preflight` returns non-zero (typically `P:\` not mounted) - preflight runs first and propagates its exit code.
- `<ModName>` fails the name pattern.
- `workspace/<ModName>/` does not exist. This skill never creates the top-level mod folder - that's `/dayz-new-mod` (for fresh) or `/dayz-import-mod` (for external).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

Scaffolding workspace/MyMod/

  [SKIP]  config.cpp present
  [OK]    $PBOPREFIX$ written
  [SKIP]  README.md present
  [OK]    Skeleton folders created (3 added, 2 already present)
  [OK]    workbench/dayz.gproj written (mod paths + filesystem mounts injected)
  [OK]    workbench/DayZSetting.xml copied

[OK]    2 piece(s) added, 2 piece(s) already present.
```

If everything is already present:

```
[OK]    Nothing to add - workspace/MyMod is already fully scaffolded.
```

## What it does not do

- Does NOT create `workspace/<ModName>/` itself. The folder must exist first.
- Does NOT create the `P:\<ModName>\` junction. That's `/dayz-new-mod` and `/dayz-import-mod`.
- Does NOT touch the deployed dir at `P:\Mods\@<ModName>\`. That's `/dayz-build-pbo`.
- Does NOT overwrite existing files. If you have your own `config.cpp` or `$PBOPREFIX$`, the skill leaves them alone.
- Does NOT git-add or commit anything. The user decides whether to track scaffold pieces.

## Do not

- Don't add an `--overwrite` flag. Idempotency without surprise overwrites is the contract; if you want to regenerate a piece, delete it manually and re-run.
- Don't move per-piece writers out of `dayz-new-mod`'s `new_mod.py`. We import from there to keep templates in one place; both skills must produce byte-identical output for the same inputs.
- Don't bypass the preflight gate.
