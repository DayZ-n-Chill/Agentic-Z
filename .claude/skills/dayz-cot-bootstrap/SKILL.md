---
name: dayz-cot-bootstrap
disable-model-invocation: true
description: Bootstrap Community-Online-Tools (COT) admin permissions on a DayZ test server in one shot. Auto-prepends @CF + @Community-Online-Tools to the mod chain, launches the server + client, waits for your character to spawn (detected when COT writes the per-player files), kills the session, grants you the `admin` role in your Players JSON, flips every ` 0` to ` 2` in your personal `Permissions/<id>.txt` file, then relaunches. Per-player grant only — `Roles/everyone.txt` is never touched. Requires /dayz-init + /dayz-add-server + /dayz-build-pbo first.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-cot-bootstrap

One-shot workflow for getting COT admin on a fresh test instance. COT writes its `PermissionsFramework/Players/<id>.json` and `PermissionsFramework/Permissions/<id>.txt` (along with the global `Roles/{admin,everyone}.txt`) on first server boot once a player has loaded in; those per-player files don't exist before that and can't be edited ahead of time. So the workflow is forced into two passes:

1. **First pass:** boot the server + client, let your character spawn so COT generates your per-player files, then kill the session.
2. **Edit:** add the `admin` role to **your** Players JSON, then flip ` 0` → ` 2` in **your** `Permissions/<id>.txt`. `Roles/everyone.txt` and the other `Roles/*.txt` files are left alone — this is a strictly per-player grant.
3. **Second pass:** relaunch with the same mod chain. You're now COT admin.

This skill automates all three steps. Counterpart to `/dayz-launch-test` — same launch contract, plus the COT-specific bootstrap dance.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\bootstrap.py" <ModName> [<ModName2> ...] [--server <instance>] [--port N] [--timeout SEC]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName> ...` | yes | One or more mod names already built (PBO must exist at `P:\Mods\@<ModName>\Addons\`). `@CF` and `@Community-Online-Tools` are auto-prepended to the mod chain — don't pass them yourself. |
| `--server` | no | Server instance to launch on. Default `chernarus`. Must have been added via `/dayz-add-server`. |
| `--port` | no | Server port. Default `2302`. |
| `--timeout` | no | Seconds to wait for your character to load on the first pass before giving up. Default `600` (10 minutes). |

## What it does

1. **Preflight gate** — runs `/dayz-preflight`; halts on non-zero.
2. **Project root** — reads `~/.claude/local-memory/dayz-current-project.txt`.
3. **Mod check** — verifies `@CF` + `@Community-Online-Tools` are subscribed at `P:\Mods\` and that each user-passed mod has at least one PBO. Prepends CF + COT to the mod chain (dedup).
4. **Instance check** — confirms `<project>/.server/<instance>/serverDZ.cfg` and the mission folder exist; auto-appends `allowFilePatching = 1;` if missing.
5. **First pass: launch** — spawns server, waits for it to bind UDP port, spawns client.
6. **Wait for COT registration** — polls `<project>/.server/<instance>/Profiles/PermissionsFramework/Players/*.json` for new files appearing. The first JSON written is COT registering your character. (Files present before launch are ignored, only newly-created or newly-modified files count.) On a solo test box there's normally exactly one player and exactly one new file.
7. **Kill session** — `taskkill /IM DayZDiag_x64.exe /F` on both server and client.
8. **Edit perms (per-player only)**:
   - For each triggered Players JSON file: insert `"admin"` into its `Roles[]` array (idempotent — skips if already present).
   - For each triggered player's `Permissions/<id>.txt`: replace every line ending in ` 0` with ` 2`. The script waits up to 15s for that file to appear (COT writes the JSON and the personal perms file close together but not always simultaneously). Space between perm name and digit is preserved.
   - **`Roles/everyone.txt` and the rest of `Roles/*.txt` are NEVER modified.** Flipping `everyone.txt` would silently grant every connecting player full admin, which is unsafe even on a solo box and is not the COT-intended scoping.
9. **Second pass: relaunch** — same mod chain, same instance. You're COT admin on entry.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- No project is cached (run `/dayz-init` first to set up the wizard cache).
- `@CF` or `@Community-Online-Tools` is not subscribed in Steam Workshop. (Check `P:\Mods\@CF\Addons\` and `P:\Mods\@Community-Online-Tools\Addons\`.)
- Any user-passed mod has no PBO (run `/dayz-build-pbo <ModName>` first).
- `DayZDiag_x64.exe` is not found.
- The selected `--server` hasn't been added yet (run `/dayz-add-server <instance>` first).
- The first pass times out without a Players JSON appearing. Usually means the client failed to connect or your character never spawned. Check `<project>/.server/<instance>/Profiles/script.log` and the latest `DayZDiag_x64_*.RPT` (in either `Profiles/` or `<project>/.server/!ClientDiagLogs/`) for errors.

## Idempotency

Re-running on the same instance:

- If your player JSON already has `"admin"` in Roles, the JSON edit is a no-op.
- If your personal `Permissions/<id>.txt` is already all ` 2`s, the flip is a no-op.
- `Roles/everyone.txt` and the other `Roles/*.txt` files are not read or written, so re-runs cannot drift their contents.
- The wait step still triggers on re-runs — COT touches your Players JSON when you reconnect, so the second pass behaves the same as the first.

## Output (success)

```
[Pass 1/2] Launching server + client to generate COT permission files...
[OK]    Server PID: 12345    Client PID: 67890
        Waiting up to 600s for COT to register your character...
        (watching <project>/.server/<instance>/Profiles/PermissionsFramework/Players/)
[OK]    Detected new player file: flFK...HTY.json

[OK]    Killed 2 DayZDiag_x64.exe process(es).

[Edit] Applying COT admin permissions (per-player only)...
[OK]    Granted admin to flFK...HTY
[OK]    flFK...HTY.txt: flipped 156 line(s) from 0 -> 2

[Pass 2/2] Relaunching with admin permissions...
[OK]    Server PID: 13579    Client PID: 24680

You are now COT admin on '<instance>'. Open the COT menu in-game (default keybind: BACKSPACE).
  Server logs: <project>/.server/<instance>/Profiles
  Client logs: <project>/.server/!ClientDiagLogs
```

## Do not

- Don't pass `CF` or `Community-Online-Tools` as mod names — they're auto-prepended. Passing them manually is a no-op (dedup) but it's noise.
- Don't run this skill if the user just wants a normal launch — that's `/dayz-launch-test`. This skill is only for the COT admin bootstrap dance.
- Don't try to write the perm files before the first pass. They don't exist until COT initializes for a connected player; pre-creating them confuses COT and may get overwritten.
- Don't kill the running session manually mid-skill — the skill manages its own server/client lifecycle. If something hangs, Ctrl+C the skill and run `/dayz-stop-test` to clean up.
- Don't broaden the grant by editing `Roles/everyone.txt` (or any `Roles/*.txt`). The skill is intentionally per-player. Solo test boxes have exactly one player; grant goes to that player's JSON + `Permissions/<id>.txt` only.
