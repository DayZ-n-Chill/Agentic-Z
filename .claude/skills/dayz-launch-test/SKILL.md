---
name: dayz-launch-test
description: Launch a local DayZ Diag server plus the diag client connecting to it (run-only, does no setup). Verifies the instance has been added via /dayz-add-server; refuses with a clear hint otherwise. Refuses if the legacy workspace/_server/ folder still exists (delete it manually; that layout is no longer supported). --server selects the instance (chernarus default). Always loads server alongside client per L2 conventions.
---

# /dayz-launch-test

Run-only: launches a local DayZ test session for one or more built mods. Always starts the **server first**, then the **client** connecting to it (DayZ cannot be tested standalone, per L2 conventions). Both run from `DayZDiag_x64.exe` with `-filePatching` for fast iteration on Enforce Script and config edits.

**Prerequisite:** the instance you're testing on must have been added via `/dayz-add-server <instance>` first. This skill does no setup; it verifies state and runs.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-launch-test\launch.py <ModName> [<ModName2> ...] [--server <instance>] [--port N] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName> ...` | yes | One or more mod names already built. Each must have at least one `.pbo` at `P:\Mods\@<ModName>\Addons\` (build with `/dayz-build-pbo` first). |
| `--server` | no | Server instance to launch on. Default `chernarus`. Must have been added via `/dayz-add-server`. |
| `--port` | no | Server port. Default `2302`. |
| `--dry-run` | no | Print the resolved server and client commands, then exit 0. Useful for verifying paths and arg construction without firing up the game. |

## Layout (under `.server/`)

```
.server/
└── <instance>/
    ├── mission/                        # mission copy (per-instance)
    ├── serverDZ.cfg                    # has `template = ...` line for map link
    ├── server-profiles/                # server-side RPT, script.log, BattlEye state
    └── client-profiles/                # client-side RPT, script.log, BattlEye state, Users/, DataCache/
```

The mission folder is an **editable copy**, not the original. Edit `.server/<instance>/mission/init.c` (etc.) freely. `-filePatching` makes the server read your edits live.

Each instance has its own `serverDZ.cfg` so per-instance tuning (player count, time of day, persistence) doesn't bleed across instances. Each instance also has its own `client-profiles/`, so client RPTs from different instances don't mix.

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Old-layout gate**: refuses if `workspace/_server/` still exists. Delete the folder manually; that layout is no longer supported.
3. **Built-mod check**: for each mod, verifies at least one `.pbo` exists in `P:\Mods\@<ModName>\Addons\`. Fails fast with a hint to run `/dayz-build-pbo` if missing.
4. **Diag client resolution**: finds `DayZDiag_x64.exe` via `find_dayz_diag()` (env var, DayZ game install, Steam paths). Hard-fails if missing. Both client and server run from the same diag binary; the server adds `-server`. Retail `DayZ_x64.exe` and `DayZServer_x64.exe` are NOT used; both block past the loading screen with `-filePatching` enabled.
5. **Instance state verification**: confirms `.server/<instance>/mission/` AND `.server/<instance>/serverDZ.cfg` exist. Hard-fails with a hint to run `/dayz-add-server <instance>` if either is missing. The only mutation this skill performs on an existing cfg is auto-appending `allowFilePatching = 1;` if absent.
6. **Launch server**: spawns `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/server-profiles -mission=<instance>/mission -mod=@Mod1;@Mod2 -filePatching -port=<port>`.
7. **Wait 5s** for the server to start listening.
8. **Launch client**: spawns `DayZDiag_x64.exe -profiles=<instance>/client-profiles -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=<port> -filePatching` plus the display flags from per-clone preferences.
9. **Print PIDs and exit.** Both processes run independently. Close the windows manually to stop them, or run `/dayz-stop-test`.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `workspace/_server/` still exists. Delete it manually; the legacy layout is no longer supported.
- Any named mod has no `.pbo` at `P:\Mods\@<ModName>\Addons\`.
- `DayZDiag_x64.exe` is not found.
- The selected `--server` hasn't been added yet (`.server/<instance>/mission/` or `.server/<instance>/serverDZ.cfg` missing). Run `/dayz-add-server <instance>` first.

## Output (success)

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    BuildTest PBO present: P:\Mods\@BuildTest\Addons\BuildTest.pbo
[OK]    Diag client: C:\Program Files (x86)\Steam\steamapps\common\DayZ\DayZDiag_x64.exe
[OK]    Instance: chernarus
[OK]    Instance dir: .server\chernarus

[Launch] Server: DayZDiag_x64.exe -server -config=...\chernarus\serverDZ.cfg -profiles=...\chernarus\server-profiles -mission=...\chernarus\mission -mod=@BuildTest -filePatching -port=2302
[OK]    Server PID: 12345
        Waiting 5s for server to start listening...

[Launch] Client: DayZDiag_x64.exe -profiles=...\chernarus\client-profiles -mod=@BuildTest -connect=127.0.0.1 -port=2302 -filePatching
[OK]    Client PID: 67890

Both running. Close the windows manually to stop.
  Server PID: 12345    Client PID: 67890
  Server logs: .server\chernarus\server-profiles
  Client logs: .server\chernarus\client-profiles
```

## Output (`--dry-run`)

Same as above through state verification, then:

```
[DRY-RUN] Server cmd: DayZDiag_x64.exe -server -config=... -mission=... -mod=@BuildTest -filePatching -port=2302
[DRY-RUN] Client cmd: DayZDiag_x64.exe -profiles=... -mod=@BuildTest -connect=127.0.0.1 -port=2302 -filePatching
```

No processes spawned. Exit 0.

## Editing missions

The whole point of the per-instance mission copy is that you can edit it freely:

- `.server/<instance>/mission/init.c`: server-side mission entrypoint (the `main()` function the engine looks for).
- `.server/<instance>/mission/db/types.xml`: Central Economy.
- `.server/<instance>/mission/cfggameplay.json`: runtime gameplay tuning.

With `-filePatching`, edits show up on the next server launch. Keep edits to the workspace copy; the original DayZ Server install is not modified.

## Client display preferences

The diag client reads display preferences from a per-clone JSON file at:

```
.claude/local-memory/dayz-client-display.json
```

Created on first launch with these defaults:

```json
{
  "windowed": true,
  "width": 1920,
  "height": 1080
}
```

These map to DayZ launch flags `-window`, `-x=<width>`, `-y=<height>`. Edit the file freely.

## Do not

- Don't try to launch the client without the server. DayZ has no offline / single-player mode for mod testing.
- Don't substitute retail `DayZ_x64.exe` or `DayZServer_x64.exe` for the diag binary.
- Don't re-implement DayZ install path discovery; import `find_dayz_diag` from `dayz-preflight/preflight.py`.
- Don't add bootstrap / setup logic to this skill. Setup is `/dayz-add-server`'s job; this skill verifies and runs only.
- Don't auto-kill the spawned processes. The user closes them manually.
