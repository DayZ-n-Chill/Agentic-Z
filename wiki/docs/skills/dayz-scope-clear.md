---
name: dayz-scope-clear
---

# /dayz-scope-clear

Counterpart to `/dayz-scope-mod`. Removes the deny rules that block Edit/Write to sibling mods, returning the agent to unrestricted Edit/Write across all mods.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-scope-clear\clear.py
```

No arguments. Same effect as:

```cmd
python .claude\skills\dayz-scope-mod\scope.py --clear
```

## What it does

1. Reads `.claude/local-memory/dayz-active-scope.json` to find the rules added by `/dayz-scope-mod`.
2. Removes exactly those rules from `permissions.deny` in `.claude/settings.local.json`.
3. Deletes `.claude/local-memory/dayz-active-scope.json`.
4. No-op if no scope is currently active.

## Output

```
[OK]    Cleared scope (was: SuperMedKit). Removed 6 deny rule(s).
```

Or:

```
[INFO]  No active scope. Nothing to clear.
```

## Does NOT gate on `/dayz-preflight`

Same exception precedent as `/dayz-stop-test`: this skill operates on settings files, not on `P:\` content. Safe to run without the environment being ready.

## Do not

- Don't manually edit deny rules. Re-run `/dayz-scope-mod <Mod>` to refresh, or this skill to clear.
