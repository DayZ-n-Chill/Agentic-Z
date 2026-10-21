---
name: dayz-cot-bootstrap
---

## Overview

Grants the developer Community-Online-Tools (COT) admin on a local DayZ test server in one run: launches with COT, waits for its permission files, grants the player admin and relaunches. Never edits Roles/everyone.txt. Use when you need COT admin on a test instance after /dayz-add-server and /dayz-build-pbo.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-cot-bootstrap

One-shot workflow for getting COT admin on a test instance. COT writes a player's `PermissionsFramework/Players/<id>.json` and `PermissionsFramework/Permissions/<id>.txt` only after that player has loaded in, so they cannot be edited ahead of time. The skill therefore runs two passes:

1. **First pass:** boot server and client, wait until COT writes your per-player files, then stop the session.
2. **Edit:** add the `admin` role to **your** Players JSON and flip ` 0` to ` 2` in **your** `Permissions/<id>.txt`. `Roles/everyone.txt` and the other `Roles/*.txt` files are never touched.
3. **Second pass:** relaunch with the same mod chain. You're now COT admin.

It uses the same launch contract as `/dayz-launch-test`.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\bootstrap.py" [<ModName> ...] [--server <instance>] [--port N] [--timeout SEC]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName> ...` | no | Your built mods (PBO at `P:\Mods\@<ModName>\Addons\`). `@CF` and `@Community-Online-Tools` are always prepended; with no names, only those two load. |
| `--server` | no | Server instance to launch on. Default `chernarus`. Must have been added via `/dayz-add-server`. |
| `--port` | no | Server port. Default `2302`. |
| `--timeout` | no | Seconds to wait on the first pass for COT to register your character. Default `600`. |

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Project root**: reads the root `/dayz-init` cached in `.claude/local-memory/dayz-current-project.txt`.
3. **Mod check**: verifies `@CF` and `@Community-Online-Tools` have PBOs under `P:\Mods\`, prepends them to the chain (dropping duplicates), and checks every mod in the chain has at least one PBO.
4. **Instance check**: the same check `/dayz-launch-test` runs (cfg `template = "...";` line, an active `allowFilePatching = 1;` line, `mission/`, and the template junction). Anything missing, including a commented-out or `0` `allowFilePatching`, refuses with a hint to run `/dayz-add-server <instance>`, which fixes the cfg.
5. **First pass**: checks UDP `--port` is free (same check as `/dayz-launch-test`; refuses with `port <port> in use; run /dayz-stop-test or pass --port` if not), spawns the server, waits for it to bind its UDP port, spawns the client.
6. **Wait for COT**: polls `.server/<instance>/Profiles/PermissionsFramework/Players/*.json` for a file that is new or newer than before the launch. If the server or client process exits first, the wait ends at once; on that or on timeout it stops the session and exits 1, pointing at `script.log` and the RPT in `Profiles/` and at `.server/!ClientDiagLogs/`.
7. **Stop session**: kills only the two processes this run started (waiting up to 30 s each); other `DayZDiag_x64.exe` processes are left alone.
8. **Edit perms (per player)**: adds `"admin"` to each triggered player's `Roles[]` (no-op if present), waits up to 15 s for that player's `Permissions/<id>.txt`, and replaces every line ending in ` 0` with ` 2`. If any JSON cannot be parsed or any perms file never appears, it exits 1 without starting pass 2.
9. **Second pass**: checks the port again, relaunches with the same mod chain and instance, prints the PIDs, and exits 0.

## Refuses to run if

- `/dayz-preflight` returns non-zero, or no project is cached (run `/dayz-init`).
- `@CF` or `@Community-Online-Tools` has no PBOs under `P:\Mods\` (subscribe in Steam Workshop).
- Any mod in the chain has no PBO (run `/dayz-build-pbo <ModName>`).
- `DayZDiag_x64.exe` is not found.
- The `--server` instance is not set up (run `/dayz-add-server <instance>`).
- UDP `--port` is already in use before a pass launches. Run `/dayz-stop-test` or pass another `--port`. If this happens on pass 2 (a pass-1 process did not release the port), the permission edits are already saved; rerun once the port is free.

It exits 1 mid-run when the server never binds its port, when the server or client exits or no Players JSON appears before `--timeout` (check `Profiles/script.log` and the latest RPT in `Profiles/` or `.server/!ClientDiagLogs/`), or when the permission edit fails.

## Re-running

Safe on the same instance: an existing `admin` role and an all-` 2` perms file are left as they are, and `Roles/*.txt` is never read or written. COT touches your Players JSON when you reconnect, so the wait step still triggers.

## Output (success, abridged)

```
[Pass 1/2] Booting so COT can generate permission files for your character.
...
[OK]    Detected player file: flFK...HTY.json

[Stop] Stopping the pass-1 server and client before editing perm files...

[Edit] Applying COT admin permissions (per-player only)...
[OK]    Granted admin to flFK...HTY
[OK]    flFK...HTY.txt: flipped 156 line(s) from 0 -> 2

[Pass 2/2] Relaunching with admin permissions applied.
...
You are now COT admin on 'chernarus'. Open the COT menu in-game (default keybind: BACKSPACE).
```

## Do not

- Don't use this for a normal launch; that's `/dayz-launch-test`.
- Don't pre-create the perm files; COT writes them for a connected player and may overwrite them.
- Don't close the game windows mid-run; the skill manages both passes. If something hangs, Ctrl+C and run `/dayz-stop-test`.
- Don't broaden the grant by editing `Roles/everyone.txt` (or any `Roles/*.txt`): that would make every connecting player an admin.
