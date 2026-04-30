---
name: dayz-clean-workspace
description: Remove DayZ scaffolds and their deployed artifacts. For each scaffolded mod under workspace/<ModName>/, removes the workspace folder, the P:\<ModName>\ junction (only if it points at our workspace), and the P:\Mods\@<ModName>\ deployed dir. Never touches mods you didn't scaffold (subscribed/installed mods at !Workshop are safe). --include-server also removes workspace/_server/. Interactive confirmation by default; --yes skips it.
---

# /dayz-clean-workspace

Reset the DayZ workspace by removing scaffolds and their deployed artifacts. Safe — only removes mods that match a `workspace/<ModName>/` scaffold (folder containing `config.cpp` + `$PBOPREFIX$`). User-installed / subscribed mods under `<DayZ install>\!Workshop\` are never touched.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-clean-workspace\clean.py [--mod <Name>] [--include-server] [--yes] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `--mod <Name>` | no | Target a specific mod by name. Default: all scaffolded mods under `workspace/`. |
| `--include-server` | no | Also remove `workspace/_server/` (mission copies, per-map cfg, profiles, !ClientDiagLogs). |
| `--yes` | no | Skip the interactive confirmation prompt. Required when stdin isn't a TTY. |
| `--dry-run` | no | Print what would be removed; touch nothing. Always exit 0. |

## What it removes (per scaffolded mod)

For each `workspace/<ModName>/` containing `config.cpp` + `$PBOPREFIX$`:

| Artifact | Removed when |
|---|---|
| `P:\<ModName>\` junction | It exists AND points at `workspace/<ModName>/`. (If the link points elsewhere or isn't a link, it's left alone — could be the user's own setup.) |
| `P:\Mods\@<ModName>\` deployed dir | It exists. (`P:\Mods\` is your `!Workshop` junction; this only removes the `@<ModName>` subfolder, not the workshop folder itself.) |
| `workspace/<ModName>/` | Always (it's the scaffold we're cleaning). |

With `--include-server`, also removes `workspace/_server/` (mission copies, all per-map configs, all profiles, !ClientDiagLogs). Use this for a full reset; otherwise the server staging stays so you don't have to re-copy missions next time.

## What it WILL NOT touch

- Mods you installed via Steam Workshop or DayZ Launcher (they live under `<DayZ install>\!Workshop\@<Subscribed>\` and only `@<scaffold-name>` matches are removed).
- `P:\<Name>\` junctions or folders that don't correspond to a `workspace/<Name>/` scaffold.
- `P:\Mods\` itself (the junction stays — only the `@<ModName>\` subfolders within it that match scaffolds are removed).
- Anything outside `workspace/`, `P:\<ModName>\` for matched names, or `P:\Mods\@<ModName>\` for matched names.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `--mod <Name>` is given but `workspace/<Name>/` isn't a scaffolded mod (no `config.cpp` / `$PBOPREFIX$`).
- Stdin isn't a TTY and `--yes` wasn't passed (refuses to silently destroy without an explicit confirmation).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

Plan: 4 item(s) to remove
  (junction) P:\TestThisBitch
  (deployed) P:\Mods\@TestThisBitch
  (workspace) workspace\TestThisBitch
  (server staging) workspace\_server

Proceed? [y/N]: y

[OK]    removed (junction): P:\TestThisBitch
[OK]    removed (deployed): P:\Mods\@TestThisBitch
[OK]    removed (workspace): workspace\TestThisBitch
[OK]    removed (server staging): workspace\_server

[OK]    Cleaned 4 item(s).
```

`--dry-run` form prints the plan with `would remove` prefix and exits without changes.

## Do not

- Don't add the ability to remove arbitrary `P:\Mods\@<X>\` entries that don't correspond to a `workspace/<X>/` scaffold. The match-on-scaffold rule is what makes this skill safe to run against a machine with subscribed mods.
- Don't follow junctions during removal. Use `cmd /c rmdir` (which removes the junction without descending into the target). Plain `rm -rf` on a junction is unreliable on Windows / Git Bash.
- Don't gate this skill behind any "are you sure" beyond the `--yes` / TTY confirmation. Two prompts are noise.
