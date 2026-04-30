---
name: dayz-launch-test
description: Launch a local DayZ Diag server plus the diag client connecting to it (run-only — does no setup). Verifies the map has been added via /dayz-add-map; refuses with a clear hint otherwise. --map selects the map (chernarus default). Always loads server alongside client per L2 conventions.
---

# /dayz-launch-test

Run-only: launches a local DayZ test session for one or more built mods. Always starts the **server first**, then the **client** connecting to it — DayZ cannot be tested standalone (per L2 conventions). Both run from `DayZDiag_x64.exe` with `-filePatching` for fast iteration on Enforce Script and config edits.

**Prerequisite:** the map you're testing on must have been added via `/dayz-add-map &lt;map&gt;` first. This skill does no setup — it verifies state and runs.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-launch-test\launch.py &lt;ModName&gt; [&lt;ModName2&gt; ...] [--map &lt;name&gt;] [--port N] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `&lt;ModName&gt; ...` | yes | One or more mod names already built. Each must have `P:\Mods\@&lt;ModName&gt;\Addons\&lt;ModName&gt;.pbo` present (build with `/dayz-build-pbo` first). |
| `--map` | no | Map / mission to test on. Default `chernarus`. Known aliases: `chernarus` → `dayzOffline.chernarusplus`, `livonia` → `dayzOffline.enoch`, `sakhal` → `dayzOffline.sakhal`. Custom missions: pass the actual mission folder name (e.g. `--map dayzOffline.namalsk`). |
| `--port` | no | Server port. Default `2302`. |
| `--dry-run` | no | Print the resolved server and client commands, then exit 0. Useful for verifying paths and arg construction without firing up the game. |

## Layout (under `workspace/_server/`)

```
workspace/_server/
├── !ClientDiagLogs/                       # client `-profiles=` dir
│   ├── Users/                             # player profile (DayZ creates)
│   ├── DataCache/                         # client cache
│   ├── BattlEye/                          # client BE state
│   ├── DayZDiag_x64_*.RPT                 # client RPT logs
│   └── script_*.log                       # client script logs
├── missions/                              # editable mission copies
│   ├── dayzOffline.chernarusplus/         # bootstrapped from DayZ Server install
│   ├── dayzOffline.enoch/                 # on first run; user-editable thereafter
│   └── dayzOffline.sakhal/
└── maps/                                  # per-map test environments
    ├── chernarus/
    │   ├── serverDZ.cfg                   # cfg for chernarus testing
    │   └── profiles/                      # server-side logs, BattlEye, etc.
    ├── livonia/
    │   ├── serverDZ.cfg
    │   └── profiles/
    └── sakhal/
        ├── serverDZ.cfg
        └── profiles/
```

The **client** uses `workspace/_server/!ClientDiagLogs/` as its `-profiles=` directory — all client-side diag artifacts get contained inside that one folder. The **server** uses per-map `workspace/_server/maps/&lt;map&gt;/profiles/` so server-side logs stay isolated by map.

The mission folders are **editable copies**, not the originals. Edit `workspace/_server/missions/dayzOffline.chernarusplus/init.c` (etc.) freely — `-filePatching` makes the server read your edits live. Each map has its own `serverDZ.cfg` so per-map tuning (player count, time of day, persistence) doesn't bleed across maps.

## What it does

1. **Preflight gate** — runs `/dayz-preflight`; halts on non-zero.
2. **Built-mod check** — for each mod, verifies `P:\Mods\@&lt;ModName&gt;\Addons\&lt;ModName&gt;.pbo` exists. Fails fast with a hint to run `/dayz-build-pbo` if missing.
3. **Diag client resolution** — finds `DayZDiag_x64.exe` via `find_dayz_diag()` (env var → DayZ game install → Steam paths). **Hard-fails** if missing. Both client and server run from the same diag binary; the server adds `-server`. Retail `DayZ_x64.exe` and `DayZServer_x64.exe` are NOT used — both block past the loading screen with `-filePatching` enabled.
4. **Map state verification** — confirms `workspace/_server/missions/&lt;template&gt;/` exists AND `workspace/_server/maps/&lt;map&gt;/serverDZ.cfg` exists. **Hard-fails with a hint to run `/dayz-add-map &lt;map&gt;`** if either is missing. The only mutation this skill performs on an existing cfg is auto-appending `allowFilePatching = 1;` if absent.
5. **Launch server** — spawns `DayZDiag_x64.exe -server -config=&lt;map&gt;/serverDZ.cfg -profiles=&lt;map&gt;/profiles -mission=&lt;missions&gt;/&lt;template&gt; -mod=@Mod1;@Mod2 -filePatching -port=&lt;port&gt;`. The `-mission=&lt;absolute path&gt;` flag pins the mission folder explicitly so the engine doesn't look in the wrong `mpmissions/` dir.
6. **Wait 5s** for the server to start listening.
7. **Launch client** — spawns `DayZDiag_x64.exe -profiles=workspace/_server/!ClientDiagLogs -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=&lt;port&gt; -filePatching` plus the display flags from per-clone preferences. The client `-profiles=` points at the `!ClientDiagLogs/` folder so all client-side diag artifacts (`Users/`, `DataCache/`, RPT, script logs, BE state) get contained in that one folder rather than spread across the `_server/` root or polluting the DayZ install dir.
8. **Print PIDs and exit.** Both processes run independently. Close the windows manually to stop them. (A future `/dayz-stop-test` skill can manage shutdown.)

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- Any named mod has no PBO at `P:\Mods\@&lt;ModName&gt;\Addons\&lt;ModName&gt;.pbo`.
- `DayZDiag_x64.exe` is not found (set `DAYZ_DIAG_PATH`, or verify your DayZ install — diag lives next to retail in the DayZ game dir).
- The selected `--map` hasn't been set up yet — `workspace/_server/missions/&lt;template&gt;/` or `workspace/_server/maps/&lt;map&gt;/serverDZ.cfg` is missing. Run `/dayz-add-map &lt;map&gt;` first. (This skill never copies missions or creates configs; setup is a separate, explicit step.)

## Output (success — first run)

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    BuildTest PBO present: P:\Mods\@BuildTest\Addons\BuildTest.pbo
[OK]    Diag client: C:\Program Files (x86)\Steam\steamapps\common\DayZ\DayZDiag_x64.exe
[OK]    First-run setup: copying missions from C:\Program Files (x86)\Steam\steamapps\common\DayZServer\mpmissions
        copied: dayzOffline.chernarusplus
        copied: dayzOffline.enoch
        copied: dayzOffline.sakhal
[OK]    Wrote default workspace\_server\maps\chernarus\serverDZ.cfg
[OK]    Map: chernarus  (mission: dayzOffline.chernarusplus)
[OK]    Map dir: workspace\_server\maps\chernarus

[Launch] Server: DayZDiag_x64.exe -server -config=...\chernarus\serverDZ.cfg -profiles=...\chernarus\profiles -mission=...\dayzOffline.chernarusplus -mod=@BuildTest -filePatching -port=2302
[OK]    Server PID: 12345
        Waiting 5s for server to start listening...

[Launch] Client: DayZDiag_x64.exe -mod=@BuildTest -connect=127.0.0.1 -port=2302 -filePatching
[OK]    Client PID: 67890

Both running. Close the windows manually to stop.
  Server PID: 12345    Client PID: 67890
  Logs: workspace\_server\maps\chernarus\profiles
```

Subsequent runs skip the mission-copy step.

## Output (`--dry-run`)

Same as above through map setup, then:

```
[DRY-RUN] Server cmd: DayZDiag_x64.exe -server -config=... -mission=... -mod=@BuildTest -filePatching -port=2302
[DRY-RUN] Client cmd: DayZDiag_x64.exe -mod=@BuildTest -connect=127.0.0.1 -port=2302 -filePatching
```

No processes spawned. Exit 0.

## Editing missions

The whole point of the workspace mission copies is that you can edit them freely:

- `workspace/_server/missions/dayzOffline.chernarusplus/init.c` — server-side mission entrypoint (the `main()` function the engine looks for; logs warn "PlayerConnect will stay disabled" if it's missing or malformed).
- `workspace/_server/missions/dayzOffline.chernarusplus/db/types.xml` — Central Economy (spawn rates, lifetimes).
- `workspace/_server/missions/dayzOffline.chernarusplus/cfggameplay.json` — runtime gameplay tuning.

With `-filePatching`, edits show up on the next server launch (or instantly via script reload, depending on what you change). Keep edits to the workspace copy; the original DayZ Server install is not modified.

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

These map to DayZ launch flags `-window`, `-x=&lt;width&gt;`, `-y=&lt;height&gt;`. The defaults exist because mod testing on an ultra-wide / large monitor in fullscreen is painful; 1080p windowed is comfortable for iteration. Edit the file freely — the skill won't overwrite it once it exists. Set `"windowed": false` for fullscreen, change resolution to whatever your monitor likes.

The file is in `.claude/local-memory/` (gitignored, per-clone) — your monitor setup doesn't belong in the repo, and other users of the template clone can pick their own values.

## Editing per-map server config

Each map's `serverDZ.cfg` is independent. Tweak `workspace/_server/maps/chernarus/serverDZ.cfg` to change Chernarus testing parameters (max players, persistence, host name) without touching Livonia. The skill won't overwrite an existing cfg, but it WILL re-add `allowFilePatching = 1;` if you remove it (clients connect with `-filePatching` and the server refuses without that setting).

## Do not

- Don't try to launch the client without the server. DayZ has no offline / single-player mode for mod testing.
- Don't substitute retail `DayZ_x64.exe` or `DayZServer_x64.exe` for the diag binary. Retail blocks past the loading screen with `-filePatching` enabled; mod development requires diag for both ends.
- Don't re-implement DayZ install path discovery — import `find_dayz_diag` from `dayz-preflight/preflight.py`. (Mission copying lives in `/dayz-add-map` and uses `find_dayz_server`; this skill doesn't.)
- Don't add bootstrap / setup logic to this skill. Setup is `/dayz-add-map`'s job; this skill verifies and runs only. Two skills, one responsibility each.
- Don't edit missions inside the original DayZ Server install — edit the workspace copy under `workspace/_server/missions/&lt;template&gt;/`.
- Don't auto-kill the spawned processes. The user closes them manually for now. Adding a process-lifecycle skill is a separate concern.
- Don't bake user-specific tuning into the default `serverDZ.cfg` template. Keep it minimal; let the user edit per-map cfgs to taste.
