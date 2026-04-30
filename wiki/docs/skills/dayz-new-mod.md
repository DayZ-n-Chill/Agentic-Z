---
name: dayz-new-mod
description: Scaffold a new DayZ mod project under workspace/&lt;ModName&gt;/ with the standard skeleton (config.cpp stub, $PBOPREFIX$, scripts/3_Game/4_World/5_Mission, data, gui, workbench/, README). Workbench folder gets a copy of the official dayz.gproj + DayZSetting.xml from DayZ Tools, with the mod's script paths injected so Workbench can compile vanilla + mod together. First run prompts for an author handle and caches it in .claude/local-memory/.
---

# /dayz-new-mod

Create a new DayZ mod project workspace conforming to `.claude/skills/_shared/dayz-conventions.md`. Gates on `/dayz-preflight` first per the L2 rule that every DayZ skill MUST preflight before doing work — refuses to run if `P:\` is not mounted, even though scaffolding itself only writes under `workspace/`.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-new-mod\new_mod.py &lt;ModName&gt; [--author "YourHandle"]
```

| Argument | Required? | Notes |
|---|---|---|
| `&lt;ModName&gt;` | yes | Folder name and `CfgPatches` class name. Must start with a letter; letters, digits, underscores only; max 64 chars. |
| `--author` | no | Author handle written into `config.cpp` and cached for future runs. If omitted, the skill checks the cache, then prompts interactively, then fails. |

## Author handle resolution

First hit wins:

1. `--author "Name"` flag — also writes to the cache for next time.
2. Cached value at `.claude/local-memory/dayz-author.txt` (per-clone, gitignored).
3. Interactive prompt if stdin is a TTY — written to cache after.
4. Hard fail with instructions otherwise.

To change your handle later: re-run with `--author "NewHandle"`, or edit / delete `.claude/local-memory/dayz-author.txt`.

## What it creates

```
workspace/&lt;ModName&gt;/
├── config.cpp                 # CfgPatches + CfgMods stub, no content classes yet
├── $PBOPREFIX$                # contains: &lt;ModName&gt;
├── README.md                  # light onboarding notes
├── scripts/
│   ├── 3_Game/.gitkeep
│   ├── 4_World/.gitkeep
│   └── 5_Mission/.gitkeep
├── data/.gitkeep
├── gui/.gitkeep
└── workbench/
    ├── dayz.gproj             # vanilla project file + this mod's script paths
    └── DayZSetting.xml        # vanilla Workbench settings
```

### The `workbench/` folder

Open this mod in Workbench via `/dayz-launch-workbench --mod &lt;ModName&gt;` (it loads `workbench/dayz.gproj`). The gproj is a copy of the official `dayz.gproj` shipped with DayZ Tools (`Bin\Workbench\`), with this mod's script paths injected into the `game`/`world`/`mission` modules so Workbench compiles and lints vanilla + your mod together — same as the engine does at runtime.

If DayZ Tools isn't installed when you run `/dayz-new-mod`, the folder is still created but the `.gproj`/`.xml` are skipped with a warning; rerun the scaffold or copy the files manually once Tools is installed.

Plus a directory junction:

```
P:\&lt;ModName&gt;\  -> workspace/&lt;ModName&gt;/   (symlink, falls back to junction on Windows)
```

The `config.cpp` stub registers the three Enforce Script modules (3_Game, 4_World, 5_Mission) so script files dropped into those folders are loaded automatically. No `CfgVehicles` / `CfgWeapons` / `CfgMagazines` entries — add those when you have content to declare.

### Why the P:\ junction

DayZ Tools' AddonBuilder reads source folders from `P:\` and resolves `$PBOPREFIX$` relative to it. Our convention keeps source under `workspace/&lt;ModName&gt;/` (under git, in your editor of choice), but the engine and Tools expect to see it at `P:\&lt;ModName&gt;\`. Creating the junction at scaffold time means:

- You edit files in `workspace/&lt;ModName&gt;/` like any normal repo file.
- AddonBuilder, the engine, and any DayZ tooling see them at `P:\&lt;ModName&gt;\` automatically.
- `dayz-build-pbo` doesn't need to manage the junction — it just verifies it exists.
- No copies, no de-sync.

Junctions don't require admin; symlinks do (Windows only creates them automatically when Developer Mode is on or the process is elevated). The skill tries symlink first, falls back to junction.

## Refuses to run if

- `/dayz-preflight` returns non-zero (typically `P:\` not mounted) — preflight runs first and propagates its exit code.
- `&lt;ModName&gt;` fails the name pattern.
- `workspace/&lt;ModName&gt;/` already exists (won't clobber an in-progress project).
- `P:\&lt;ModName&gt;\` exists as a real folder (won't clobber non-link content).
- `P:\&lt;ModName&gt;\` exists as a link pointing somewhere other than `workspace/&lt;ModName&gt;/` (won't redirect a junction the user set up for a different project).
- No author handle is available and stdin is not a TTY.

### Stale-junction auto-clean

If `P:\&lt;ModName&gt;\` exists as a junction or symlink whose target is the about-to-be-scaffolded `workspace/&lt;ModName&gt;/` (typically because a prior scaffold's workspace folder was deleted but the junction wasn't), the skill removes the stale link automatically and proceeds. This handles the common cleanup case where you `rm -rf workspace/&lt;ModName&gt;/` to start over.

If junction creation fails after scaffolding (permission error, filesystem weirdness), the workspace folder is rolled back so you can retry cleanly.

## Output

```
[OK]    Created workspace/MyMod/
[OK]    config.cpp written (author: YourHandle)
[OK]    $PBOPREFIX$ written
[OK]    Skeleton folders created
[OK]    README.md written
[OK]    workbench/dayz.gproj written (mod paths injected)
[OK]    workbench/DayZSetting.xml copied
[OK]    P:\MyMod junction -> workspace\MyMod

Next steps:
  - Add Enforce Script files under workspace/MyMod/scripts/3_Game (or 4_World, 5_Mission)
  - Add models/textures/materials under workspace/MyMod/data
  - Add UI layouts under workspace/MyMod/gui
  - Open in Workbench: /dayz-launch-workbench --mod MyMod
  - When ready, /dayz-build-pbo to pack and deploy to P:\Mods\@MyMod\Addons\
```

## Do not

- Don't pre-populate `data/` or `gui/` with sample assets — the user adds those when they have real content.
- Don't auto-commit the new project to git. The user decides whether to track it.
- Don't bypass the preflight gate — every DayZ skill follows the same rule, scaffolding included. (See L2 conventions.)
