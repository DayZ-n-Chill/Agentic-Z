# Server-instance layout: move and reshape

**Status:** design
**Date:** 2026-05-06
**Branch:** feature/server-instance-layout

## Problem

Local DayZ test-server runtime currently lives at `workspace/_server/` and is keyed by **map name**. Two real defects:

1. **Server runtime is mixed in with mod sources.** `workspace/` is supposed to be active mod work; sharing it with server runtime (mission copies, RPT logs, BattlEye state, profiles) clutters the dev surface.
2. **Map name is the wrong identity for a test instance.** A user wants multiple variants of the same map (vanilla chernarus, modded-loot chernarus, hardcore-rules chernarus). Today `workspace/_server/maps/chernarus/` collides for all of them, and the mission folder under `workspace/_server/missions/dayzOffline.chernarusplus/` is even more shared (every map running that template uses the one folder).

Plus a smaller smell: client-side diag logs all dump into one shared `workspace/_server/!ClientDiagLogs/`, so switching between servers mixes RPTs.

## Goals

- Move server runtime out of `workspace/` to a dedicated top-level location.
- Identify each test setup by a free-form **instance name**, not by map.
- Per-instance isolation: each instance owns its mission copy, server config, server logs, and client logs. No cross-contamination.
- Same behavior in plugin distribution and repo-clone distribution (skills resolve paths relative to project CWD; this falls out for free).

## Non-goals

- **Mod source layout is unchanged.** `workspace/<ModName>/` still holds in-progress mod projects.
- **Build-artifact destination is unchanged.** `.pbo` files still deploy to `P:\Mods\@<ModName>\Addons\` because that is the path the engine and DayZ Tools expect.
- **No backward-compatibility alias for the old `workspace/_server/` path.** Migration is explicit and one-shot (see Migration section).

## Final layout

```
project/
├── .server/                                 # was workspace/_server/
│   └── <instance>/                          # was maps/<map>/, now free-form
│       ├── mission/                         # per-instance mission copy (was missions/<template>/, shared)
│       ├── serverDZ.cfg                     # has `template = "dayzOffline.chernarusplus";` line
│       ├── server-profiles/                 # was profiles/  (server RPT, script.log, BE state)
│       └── client-profiles/                 # was !ClientDiagLogs/  (client RPT, script.log, BE state, Users/, DataCache/)
├── workspace/<ModName>/                     # unchanged
└── ...
```

**Mission folder named `mission/` (not `dayzOffline.chernarusplus/`).** The launcher pins the path explicitly via `-mission=<absolute path>`, so the engine does not care what the folder is called. The `template = ...` line in `serverDZ.cfg` keeps the link to the original DayZ template.

**Per-instance client profiles** means switching from `chernarus` to `chernarus-hardcore` does not mix RPTs and does not carry the player's `Users/` profile across. For test instances this is a feature: a fresh player profile per instance is what you usually want.

## Skill changes

### Rename: `/dayz-add-map` to `/dayz-add-server`

The thing this skill creates is a server profile (mission copy plus serverDZ.cfg plus profile dirs), not "a map". Rename the skill folder, the SKILL.md frontmatter, and the python module accordingly.

**New CLI:**

```
/dayz-add-server <instance> [--map <mapname>] [--refresh-mission]
```

| Argument | Required? | Notes |
|---|---|---|
| `<instance>` | yes | Free-form instance name. Becomes the `.server/<instance>/` folder. |
| `--map` | no | Map alias (`chernarus`, `livonia`, `sakhal`) or full mission template name. When omitted, `<instance>` is used as the map alias if it matches a known one; otherwise the skill fails and tells the user to specify `--map`. |
| `--refresh-mission` | no | Re-copy the mission template from DayZ Server install, overwriting local edits. Same semantics as today. |

**Behavior:**

1. Preflight gate (unchanged).
2. Refuse to run if `workspace/_server/` exists. Print: "Old layout detected. Run `/dayz-migrate-server` first." This forces explicit migration.
3. Resolve the mission template from `--map` or instance name.
4. If `.server/<instance>/mission/` does not exist (or `--refresh-mission`), copy the mission template into it.
5. Write or preserve `.server/<instance>/serverDZ.cfg`. Auto-append `allowFilePatching = 1;` if missing.
6. Create `.server/<instance>/server-profiles/` and `.server/<instance>/client-profiles/`.

### Update: `/dayz-launch-test`

**New CLI:**

```
/dayz-launch-test <ModName> [<ModName2> ...] [--server <instance>] [--port N] [--dry-run]
```

`--map` becomes `--server`. Default value: `chernarus`, for muscle memory. If `chernarus` is not a real instance, fail with hint to run `/dayz-add-server chernarus` (or list existing instances).

**Behavior changes:**

- Server cmdline: `-config=.server/<instance>/serverDZ.cfg -profiles=.server/<instance>/server-profiles -mission=.server/<instance>/mission`
- Client cmdline: `-profiles=.server/<instance>/client-profiles` (was the shared `workspace/_server/!ClientDiagLogs/`)
- Refuse to run if `workspace/_server/` exists, with the same migration hint as `/dayz-add-server`.

### Update: `/dayz-clean-workspace`

Currently cleans `workspace/_server/` when `--include-server` is passed. Change to clean `.server/` instead. Same flag, same semantics, new path. Refuse to run with `--include-server` if `workspace/_server/` still exists, with the same migration hint as the other skills (we never silently leave the old folder behind).

### New: `/dayz-migrate-server`

One-shot, explicit migration. Idempotent.

**CLI:**

```
/dayz-migrate-server [--instance-name <name>] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `--instance-name` | no | Name to give the migrated instance. Default: inferred from `workspace/_server/maps/`'s single child folder, or `chernarus` if multiple maps existed (with a warning). |
| `--dry-run` | no | Print the planned moves, take no action. |

**Behavior:**

1. Preflight gate.
2. Detect `workspace/_server/`. If absent, exit 0 with "nothing to migrate".
3. For each `workspace/_server/maps/<map>/` directory, plan a move into `.server/<instance>/` (one instance per old map directory; instance name = old map name unless `--instance-name` overrides). Mission folder is copied from `workspace/_server/missions/<template>/` to `.server/<instance>/mission/`, renamed from the original `dayzOffline.<x>` folder name to the canonical `mission/` (one copy per migrated instance, even if the old layout shared one folder across maps). Profiles move from `workspace/_server/maps/<map>/profiles/` to `.server/<instance>/server-profiles/`. The single shared `workspace/_server/!ClientDiagLogs/` is moved to `.server/<instance>/client-profiles/` for the **alphabetically-first migrated instance**, with a printed note that the old layout did not isolate client logs and the user can manually redistribute if desired.
4. After successful migration, `workspace/_server/` is left intact and the user is told to delete it manually once they have verified the new layout works. We do not auto-delete during migration.

## Gitignore

Template ships this `.gitignore` rule:

```gitignore
# Server runtime: ignore everything by default, track user-edited files
.server/*/
!.server/*/serverDZ.cfg
!.server/*/mission/
!.server/*/mission/**
```

User-edited `serverDZ.cfg` and `mission/` contents (init.c, cfggameplay.json, types.xml, etc.) are tracked. Logs, profiles, BE state, storage, and the rest of the runtime junk are ignored.

This is a policy change. The current L1 docs say "don't gitignore `workspace/_server/` template-wide; it's a per-project decision." With `.server/` we are opinionated. Users who want different behavior can edit `.gitignore` in their clone.

## Files touched

**Skill code (rename + edit):**

- `.claude/skills/dayz-add-map/` to `.claude/skills/dayz-add-server/` (folder rename)
  - `SKILL.md` (rewrite frontmatter, content, new CLI)
  - `add_map.py` to `add_server.py` (rewrite)
- `.claude/skills/dayz-launch-test/SKILL.md` (rename `--map` to `--server`, point at `.server/` paths)
- `.claude/skills/dayz-launch-test/launch.py` (same)
- `.claude/skills/dayz-clean-workspace/SKILL.md` (target `.server/` instead of `workspace/_server/`)
- `.claude/skills/dayz-clean-workspace/clean.py` (same)
- `.claude/skills/dayz-migrate-server/` (new folder)
  - `SKILL.md`
  - `migrate.py`

**Plugin manifest:**

- `.claude-plugin/plugin.json` (replace `dayz-add-map` registration with `dayz-add-server`, add `dayz-migrate-server`)

**Shared conventions:**

- `.claude/skills/_shared/dayz-conventions.md` (any references to `workspace/_server/` or `dayz-add-map`)

**L1 docs:**

- `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (the `workspace/_server/` paragraph in the Repository Use section, plus any skill-name references)
- `docs/dayz-modding.md` (skill-name references, layout description)
- `docs/README.md`
- `README.md`

**Helper scripts:**

- `scripts/add-map.bat` to `scripts/add-server.bat`

**Wiki mirror (auto-regenerated by `/docs-sync`, no hand edit):**

- `wiki/docs/intro.mdx`, `wiki/docs/dayz-modding.md`, `wiki/docs/dayz-conventions.md`, `wiki/docs/skills/dayz-add-map.md`, `wiki/docs/skills/dayz-launch-test.md`

**Repo `.gitignore`:** add the `.server/` rule above.

## Risks

- **`/dayz-clean-workspace` changing target without flag bump.** A user with old muscle memory who runs `--include-server` after this change will clean `.server/` instead of `workspace/_server/`. If they have not migrated yet, that is harmless (their old folder is untouched). But the skill should refuse if `workspace/_server/` still exists, telling the user to migrate first. (Same gate as the other skills.)
- **Mission folder rename to `mission/`.** Most mission scripts use paths relative to mission root, so renaming should be safe. Rare scripts that hardcode `dayzOffline.chernarusplus` in absolute form will break. Mitigation: document in the skill output that the folder is named `mission/` and to use mission-relative paths.
- **`--server` default value of `chernarus`.** If a user has only one instance with a different name (say they ran `/dayz-add-server my-test --map chernarus`), `/dayz-launch-test <Mod>` fails with "no instance named `chernarus`." They have to either name their instance `chernarus` or pass `--server my-test` explicitly. Acceptable; the alternative (smart default = "the only instance you have") is fragile.

## Open questions

None at the time of writing. All design decisions have been confirmed.

## Implementation sketch

This spec hands off to `/superpowers:writing-plans` next. Implementation is roughly:

1. Create `dayz-add-server` skill (folder + python + SKILL.md).
2. Create `dayz-migrate-server` skill.
3. Update `dayz-launch-test` and `dayz-clean-workspace` for new path and renamed flag.
4. Update plugin manifest, L1 docs, shared conventions, README, scripts.
5. Add `.gitignore` rule.
6. Delete the old `dayz-add-map` skill folder.
7. Run `/sync-skills` and `/docs-sync` to propagate.
8. Manual verification: scaffold a fresh instance, launch it, confirm logs land in the right place. Then run migration on the existing `workspace/_server/` and verify the migrated instance launches.
