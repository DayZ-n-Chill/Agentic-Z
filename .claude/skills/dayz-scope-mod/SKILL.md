---
name: dayz-scope-mod
description: Scopes the agent to one mod under workspace/<ModName>/ by adding Edit deny rules to .claude/settings.local.json for every other mod's workspace folder, P:\<other>\ junction and P:\Mods\@<other>\ deploy folder (plus the game's real !Workshop\@<other>\ folder), so Edit and Write cannot touch sibling mods. Reads stay broad. Use when a session or subagent should work on a single mod; run --clear to lift the scope.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-scope-mod

Scope the agent to a single DayZ mod. While scoped, the agent can read anywhere but cannot Edit or Write to any other mod's source, P:\ junction, or workshop deploy dir. Designed for sessions where you're iterating on one mod and don't want a wrong-instinct call to land in a sibling mod.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
:: Scope to a specific mod
python "<skill-dir>\scope.py" <ModName>

:: Show current scope (or "no active scope")
python "<skill-dir>\scope.py" --status

:: Lift the scope
python "<skill-dir>\scope.py" --clear
```

## What it does

1. Validates `<ModName>` exists at `workspace/<ModName>/` (refuses unknown names, and names that permission rules would read as pattern syntax: `*`, `?` or `[` anywhere, or a leading `!` or `#`; `!` and `#` mid-name are fine because gitignore syntax treats them specially only at the start of a pattern).
2. Reads `.claude/settings.local.json`, removes any rules previously added by this skill (idempotent re-run).
3. Enumerates sibling mods under `workspace/` (every directory except the active mod and dotted folders). Refuses if a sibling's name breaks the same rule.
4. For each sibling mod, appends deny rules to `permissions.deny`:
   - `Edit(/workspace/<other>/**)` (a leading `/` anchors at Claude Code's primary working directory, so start Claude Code from the project root)
   - `Edit(//p/<other>/**)` (`//` is absolute; Claude Code normalizes `P:\` to `/p/` before matching)
   - `Edit(//p/Mods/@<other>/**)`
   - `Edit(//<drive>/<DayZ game>/!Workshop/@<other>/**)`, the real folder behind the `P:\Mods` junction, e.g. `Edit(//c/Program Files (x86)/Steam/steamapps/common/DayZ/!Workshop/@OtherMod/**)`. The game is located with `find_dayz_game()` from `/dayz-preflight`; if it is not found this rule is skipped with an `[INFO]` line.

   Claude Code checks file writes against `Edit(...)` rules only, so one `Edit` rule blocks both the Edit and Write tools. `Write(path)` rules are accepted but never matched, which is why the skill does not write them.
5. Writes back `.claude/settings.local.json`.
6. Records the active mod and the rules this run actually appended (a matching rule you already had is skipped, left in place and not recorded, so `--clear` never removes it) in `.claude/local-memory/dayz-active-scope.json` so `--clear` can undo precisely what was set.

## What it does not do

- **Not a full sandbox.** Repo-wide files (`.claude/`, `scripts/`, `docs/`, root configs) stay writable so the agent can keep editing the template and tooling. Only sibling mods are protected.
- **Only partly covers Bash.** Edit deny rules also cover file commands Claude Code recognizes in Bash (such as `sed` or `tee`) and redirection targets, but a script or command that writes files indirectly still goes through. This skill protects the high-frequency accidents (Edit/Write) without pretending to be a security boundary. Use this as a guardrail, not a jail.
- **Does not auto-update on new mods.** If you add a new mod after scoping, re-run `/dayz-scope-mod <ActiveMod>` to refresh the deny list with the new sibling.
- **Does not gate on `/dayz-preflight`.** This is a meta-skill that operates on settings files, not on `P:\` content. Safe to run without preflight passing.

## When to run

- At the start of a session focused on a single mod.
- After importing or scaffolding a new mod that you then want to lock into.
- Before delegating work to a subagent that might fan out across the workspace.

Skip when:

- Working across multiple mods in the same session.
- Doing template/infrastructure work (skill edits, agent edits, docs).

## Output

```
DayZ scope: SuperMedKit

[OK]    Mod found: workspace\SuperMedKit
[INFO]  Sibling mods detected: 2 (OtherModA, OtherModB)
[OK]    Added 8 Edit deny rules to .claude\settings.local.json
[OK]    Active scope recorded at .claude\local-memory\dayz-active-scope.json

Reads remain broad. Edit and Write to other mods are blocked.
Run /dayz-scope-mod --clear (or scope.py --clear) to lift.
```

If only one mod exists:

```
DayZ scope: SuperMedKit

[OK]    Mod found: workspace\SuperMedKit
[INFO]  No sibling mods to deny. Scope is set, but no rules were needed.
```

If `<ModName>` does not exist:

```
[FAIL]  workspace\NoSuchMod does not exist.
        Known mods:
          - SuperMedKit
        Scaffold first: /dayz-new-mod NoSuchMod  or  /dayz-import-mod --source <path>
```

## Do not

- Don't edit the deny rules manually. Re-run the skill to get them right and to keep `dayz-active-scope.json` in sync.
- Don't rely on this for security against malicious agents. It blocks high-frequency accidents only.
- Don't run with `--clear` and forget to re-scope: every Edit and Write to any mod becomes possible again.
