---
name: dayz-clean-workspace
description: "Removes mod scaffolds the toolkit created, with their P:\\ junction and deploy folder, and optionally .server/. Never deletes a git repo, a hand-placed mod or an imported mod's source. Use when you want to delete a mod from the workspace or reset the project."
argument-hint: "[--mod <Name>] [--include-server] [--yes] [--dry-run]"
disable-model-invocation: true
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-clean-workspace

Reset the DayZ workspace of the project cached by `/dayz-init` (the same project `/dayz-build-pbo` and `/dayz-deploy-pbo` use) by removing managed mods and what was produced for them. Subscribed or hand-placed mods under `<DayZ install>\!Workshop\` are never touched. Ownership rules come from `.claude/skills/_shared/skill_helpers.py`, shared with build and deploy.

A workspace entry is managed when it is either:

- **an imported link** made by `/dayz-import-mod`: only the link is removed (`cmd /c rmdir`). The external source folder it points at is never touched.
- **a real folder the toolkit provably created**, with no `.git` inside: `P:\<ModName>\` is a junction pointing at it (made by `/dayz-new-mod`), or `P:\Mods\@<ModName>\` carries the ownership marker for `<ModName>` (written by `/dayz-build-pbo` and `/dayz-deploy-pbo`). It is removed recursively.

`config.cpp` and `$PBOPREFIX$` alone are not proof, since a hand-placed mod has them too. A real folder that contains `.git`, or has neither proof, is never deleted: a sweep skips it with a `[WARN]` naming the reason (only for folders with a `config.cpp`; other folders are skipped silently), `--mod <Name>` refuses, and both print the `cmd /c rmdir /s /q` command to remove it by hand.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\clean.py" [--mod <Name>] [--include-server] [--yes] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `--mod <Name>` | no | Target one mod. Default: every managed mod under `workspace/`. |
| `--include-server` | no | Also remove `.server/` at the project root (all instances: missions, configs, profiles, client logs). Refuses if legacy `workspace/_server/` still exists. |
| `--yes` | no | Skip the confirmation prompt. Required when stdin isn't a TTY. |
| `--dry-run` | no | Print the plan and exit 0 without removing anything. |

### From an agent (non-TTY shell)

The agent's shell has no TTY, so the `Proceed? [y/N]` prompt can't be answered there and the script refuses without `--yes`. Run it in three steps:

1. Run with `--dry-run` (plus the same `--mod` / `--include-server` flags) and show the user the printed plan and any `[WARN]` lines.
2. Ask the user in chat to confirm that exact plan.
3. Only after an explicit yes, rerun the same command with `--yes`. If the user declines, stop.

## What it removes (per managed mod)

Removal runs in this order, so the junction is broken before its target goes:

| Artifact | Removed when |
|---|---|
| `P:\<ModName>\` junction | It is a link pointing at `workspace/<ModName>/`. A link pointing elsewhere, or a real folder, is left alone. |
| `P:\Mods\@<ModName>\` deployed dir | It contains `.agentic-z-scaffold` with content `<ModName>`. `/dayz-build-pbo` and `/dayz-deploy-pbo` write this marker on every successful run. Without it the dir is skipped with a `[WARN]` and a manual `rmdir` hint. |
| `workspace/<ModName>/` | Always, for a managed mod. Shown as `workspace` (folder removed with its contents) or `workspace-link` (link removed, source kept). |

A deployed dir from before the marker existed is skipped. Rebuild with `/dayz-build-pbo <ModName>` to write the marker, or remove it yourself with `cmd /c rmdir /s /q P:\Mods\@<ModName>` once you have confirmed it is yours.

With `--include-server`, `.server/` is removed too. Leave it out to keep server staging, so the next `/dayz-launch-test` doesn't need `/dayz-add-server` again.

## What it will not touch

- Mods installed through Steam Workshop or the DayZ Launcher.
- `P:\<Name>\` links or folders, and `P:\Mods\@<Name>\` folders, with no matching `workspace/<Name>/` entry.
- `P:\Mods\` itself.
- The external source folder behind an imported mod.
- A workspace folder that contains `.git`, or that has no `P:\<Name>\` junction to it and no ownership marker (for example a mod you copied in by hand).

## Refuses to run if

- No project is cached (run `/dayz-init`).
- `/dayz-preflight` returns non-zero.
- `--mod <Name>` names a workspace entry that is not managed: not an imported link, and either it contains `.git` or there is no `P:\<Name>\` junction to it and no ownership marker in `P:\Mods\@<Name>\`.
- `--include-server` is given while legacy `workspace/_server/` exists. Delete that folder by hand; the layout is no longer supported.
- Stdin isn't a TTY and `--yes` wasn't passed.

## Output

```
[OK]    Project: C:\...\MyProject
Plan: 4 item(s) to remove
  (junction) P:\NativeMod
  (deployed) P:\Mods\@NativeMod
  (workspace) workspace\NativeMod
  (workspace-link) workspace\ImportedMod

Proceed? [y/N]: y

[OK]    removed (junction): P:\NativeMod
[OK]    removed (deployed): P:\Mods\@NativeMod
[OK]    removed (workspace): workspace\NativeMod
[OK]    removed (workspace-link): workspace\ImportedMod

[OK]    Cleaned 4 item(s).
```

`--dry-run` prints the plan, then `(--dry-run) nothing removed.`

If a removal fails, the skill prints `[FAIL]  could not remove (<kind>) <path>: <error>` (for a link, `<error>` is `rmdir`'s own message), stops without trying the remaining items, and exits 1. Fix the cause (often a file held open by DayZ or Workbench) and rerun; already-removed items are simply no longer in the plan. If the junction was removed but the workspace folder was not, and no ownership marker exists, the rerun no longer finds proof for that folder: it prints the `[WARN]` with the manual `rmdir` command instead.

## Do not

- Don't add a way to remove `P:\Mods\@<X>\` entries that have no `workspace/<X>/` entry. Matching on the workspace is what makes this safe on a machine with subscribed mods.
- Don't remove links with `shutil.rmtree` or `rm -rf`; both can walk into a junction's target. `cmd /c rmdir` removes only the link.
- Don't add a second confirmation beyond `--yes` or the TTY prompt.
