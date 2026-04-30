---
name: dayz-add-map
description: Set up a DayZ test map under workspace/_server/. Copies the mission template from DayZ Server install if missing, creates workspace/_server/maps/<map>/serverDZ.cfg and profiles/. One-time per map (re-runs are safe and idempotent). Required before /dayz-launch-test on a given map. Use --refresh-mission to re-copy the mission after a DayZ update.
---

# /dayz-add-map

Set up a map environment for local DayZ mod testing. Copies the mission template (`dayzOffline.chernarusplus`, etc.) from DayZ Server install into the editable workspace, and creates the per-map `serverDZ.cfg` + `profiles/` directory. Idempotent — safe to re-run.

This is the **setup** half of the test loop. `/dayz-launch-test` is the **run** half, and refuses to run for a map you haven't added yet.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-add-map\add_map.py <map> [--refresh-mission]
```

| Argument | Required? | Notes |
|---|---|---|
| `<map>` | yes | Map name. Known aliases: `chernarus` → `dayzOffline.chernarusplus`, `livonia` → `dayzOffline.enoch`, `sakhal` → `dayzOffline.sakhal`. Custom missions: pass the mission folder name directly (e.g. `dayzOffline.namalsk`). |
| `--refresh-mission` | no | Re-copy the mission folder from DayZ Server install, **overwriting any local edits**. Use after a DayZ update brings new mission content. Without this flag, an existing mission folder is left alone. |

## What it does

1. **Preflight gate** — runs `/dayz-preflight`; halts on non-zero.
2. **Resolve mission template** — turns the friendly map name into the canonical mission folder name via the alias table.
3. **Mission copy** — if `workspace/_server/missions/<template>/` doesn't exist (or `--refresh-mission` was passed), copies it from `<DayZServer>/mpmissions/<template>/`. DayZ Server install is required for this step (resolved via `find_dayz_server`); after the copy, DayZ Server can be uninstalled.
4. **Map directory** — ensures `workspace/_server/maps/<map>/` exists with:
   - `serverDZ.cfg` — a default config pointing at the right mission template, with `allowFilePatching = 1;` (required for diag-mode testing).
   - `profiles/` — an empty directory ready to receive server-side logs.
   If `serverDZ.cfg` already exists, the existing config is preserved; only `allowFilePatching = 1;` is auto-appended if missing.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- DayZ Server install isn't found AND the mission isn't already in `workspace/_server/missions/`. (Install DayZ Server free from Steam appid 223350 for the initial copy. Once the mission is local, DayZ Server is no longer required.)
- DayZ Server install lacks the requested mission template (e.g. `--map dayzOffline.namalsk` but DayZ Server doesn't ship namalsk; either provide the mission manually under `workspace/_server/missions/` or correct the name).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    Mission: dayzOffline.chernarusplus
[OK]    Copied workspace\_server\missions\dayzOffline.chernarusplus  (from DayZ Server install)
[OK]    Wrote default workspace\_server\maps\chernarus\serverDZ.cfg
[OK]    Created workspace\_server\maps\chernarus\profiles\

Map 'chernarus' is ready. Next:
  /dayz-build-pbo <ModName>      (build the mod)
  /dayz-launch-test <ModName> --map chernarus   (launch)
```

If everything is already set up, the skill no-ops the relevant steps and reports them as `[OK]` (already present).

With `--refresh-mission`:

```
[OK]    Mission: dayzOffline.chernarusplus
[OK]    Refreshed workspace\_server\missions\dayzOffline.chernarusplus  (re-copied from DayZ Server)
[OK]    workspace\_server\maps\chernarus\serverDZ.cfg unchanged
```

## Editing what this skill creates

- **Mission folder** at `workspace/_server/missions/<template>/` is yours to edit. The server runs with `-filePatching` so edits to `init.c`, `cfggameplay.json`, `db/types.xml`, etc. are live on the next launch.
- **`serverDZ.cfg`** at `workspace/_server/maps/<map>/serverDZ.cfg` is yours to tune (max players, persistence, etc.). The skill never overwrites your edits, but it WILL re-add `allowFilePatching = 1;` if you remove it (without that, clients with `-filePatching` can't connect).

## Do not

- Don't edit missions inside the DayZ Server Steam install — edit the workspace copy.
- Don't gitignore `workspace/_server/` template-wide. This is a per-project decision (some users want their mission edits and per-map cfgs tracked). The template doesn't enforce.
- Don't put runtime logs (`profiles/*.RPT`, `profiles/*.log`) in version control if you do track `_server/`. Add a project-local `.gitignore` if needed.
