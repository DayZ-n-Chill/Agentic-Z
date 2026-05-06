# Server-instance layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move DayZ test-server runtime from `workspace/_server/` to `.server/<instance>/`, identify each test environment by free-form instance name (decoupled from map), per-instance isolation of mission/server-profiles/client-profiles. Skill rename `/dayz-add-map` to `/dayz-add-server`. New `/dayz-migrate-server` for one-shot migration.

**Architecture:** Project-relative path resolution (`PROJECT_DIR / ".server"`) keeps plugin distribution and repo-clone distribution behaving identically. Instance is the folder name; the map link is encoded in `serverDZ.cfg`'s `template = ...` line. Old `workspace/_server/` layout is detected and refused with a hint to run the migration skill, so users never end up half-migrated.

**Tech Stack:** Python 3 (skill scripts), Markdown (skill docs and L1 docs), JSON (plugin manifest), `.gitignore`. No new dependencies. No test framework added; verification is end-to-end against the user's real DayZ install (matches how the rest of this codebase is validated).

**Note on TDD:** This codebase has no python test infrastructure for skills. Adding pytest scaffolding for one refactor is scope creep ruled out by L1 ("Don't add features beyond what the task requires"). Each task ends with a manual verification step that runs the skill and inspects filesystem state. Treat that as the test.

**Specification:** [docs/superpowers/specs/2026-05-06-server-instance-layout-design.md](../specs/2026-05-06-server-instance-layout-design.md)

---

## File Structure

**New files:**
- `.claude/skills/dayz-add-server/SKILL.md`
- `.claude/skills/dayz-add-server/add_server.py`
- `.claude/skills/dayz-migrate-server/SKILL.md`
- `.claude/skills/dayz-migrate-server/migrate.py`
- `scripts/add-server.bat`

**Modified files:**
- `.claude/skills/dayz-launch-test/SKILL.md`
- `.claude/skills/dayz-launch-test/launch.py`
- `.claude/skills/dayz-clean-workspace/SKILL.md`
- `.claude/skills/dayz-clean-workspace/clean.py`
- `.claude/skills/_shared/dayz-conventions.md`
- `.claude-plugin/plugin.json`
- `CLAUDE.md`
- `AGENTS.md`
- `GEMINI.md`
- `docs/dayz-modding.md`
- `docs/README.md`
- `README.md`
- `.gitignore`

**Deleted files:**
- `.claude/skills/dayz-add-map/SKILL.md`
- `.claude/skills/dayz-add-map/add_map.py`
- `.claude/skills/dayz-add-map/__pycache__/` (if present)
- `scripts/add-map.bat`

**Auto-regenerated (via `/docs-sync`, no hand edit):**
- `wiki/docs/intro.mdx`
- `wiki/docs/dayz-modding.md`
- `wiki/docs/dayz-conventions.md`
- `wiki/docs/skills/dayz-add-map.md` (deleted)
- `wiki/docs/skills/dayz-add-server.md` (created)
- `wiki/docs/skills/dayz-migrate-server.md` (created)
- `wiki/docs/skills/dayz-launch-test.md`
- `wiki/docs/skills/dayz-clean-workspace.md`

---

## Task 1: Create `dayz-add-server` skill

**Files:**
- Create: `.claude/skills/dayz-add-server/SKILL.md`
- Create: `.claude/skills/dayz-add-server/add_server.py`

- [ ] **Step 1: Create `add_server.py`**

```python
"""dayz-add-server: Set up a DayZ test server instance under .server/<instance>/.

Each instance is a self-contained test environment: mission copy, serverDZ.cfg,
server profile dir, client profile dir. Decoupled from map name so the user can
run multiple variants of the same map (chernarus, chernarus-hardcore, etc.).

This is the setup half of the local-test loop. /dayz-launch-test is the run
half and refuses to run for an instance that hasn't been added yet.

Refuses to run if the legacy workspace/_server/ folder still exists. Run
/dayz-migrate-server first.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

# REPO_ROOT = where this skill ships from (plugin or template clone).
# PROJECT_DIR = user's project (where .server/ lives). Differ in plugin mode.
REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
SERVER_ROOT = PROJECT_DIR / ".server"
LEGACY_SERVER_ROOT = PROJECT_DIR / "workspace" / "_server"

KNOWN_MAPS: dict[str, str] = {
    "chernarus": "dayzOffline.chernarusplus",
    "livonia": "dayzOffline.enoch",
    "sakhal": "dayzOffline.sakhal",
}

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _load_preflight_module():
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight module at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_preflight = _load_preflight_module()
find_dayz_server = _preflight.find_dayz_server


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def gate_on_old_layout() -> None:
    """Refuse to run if workspace/_server/ still exists. Forces explicit migration."""
    if LEGACY_SERVER_ROOT.exists():
        sys.exit(
            f"{FAIL} Old layout detected at {LEGACY_SERVER_ROOT.relative_to(PROJECT_DIR)}.\n"
            "       The server runtime moved from workspace/_server/ to .server/.\n"
            "       Run: python .claude/skills/dayz-migrate-server/migrate.py"
        )


def resolve_map_name(instance: str, map_arg: str | None) -> str:
    """Pick the map alias for this instance.

    If --map was given, use it. Otherwise, if the instance name is itself a
    known map alias, use it as the map. Otherwise fail and force the user to
    be explicit, since we have no way to guess the mission template from a
    free-form name like 'my-test-server'.
    """
    if map_arg:
        return map_arg
    if instance in KNOWN_MAPS:
        return instance
    sys.exit(
        f"{FAIL} '{instance}' is not a known map alias and --map was not given.\n"
        f"       Specify --map (one of: {', '.join(KNOWN_MAPS)}, or a custom\n"
        "       mission folder name like dayzOffline.namalsk)."
    )


def resolve_mission_template(map_name: str) -> str:
    return KNOWN_MAPS.get(map_name, map_name)


def ensure_mission(template: str, mission_dir: Path, refresh: bool) -> None:
    """Ensure <instance>/mission/ exists, copied from DayZ Server install.

    Folder is named `mission/` regardless of template (the launcher pins the
    path explicitly via -mission=<abspath>, so the engine doesn't care).
    """
    already_present = mission_dir.exists() and any(mission_dir.iterdir())

    if already_present and not refresh:
        print(f"{OK} Mission already present: {mission_dir.relative_to(PROJECT_DIR)}")
        return

    server_root = find_dayz_server()
    if server_root is None:
        sys.exit(
            f"{FAIL} DayZ Server install not found.\n"
            "       Required to copy mission templates. Install via Steam (Tools section,\n"
            "       free, appid 223350), or manually populate\n"
            f"       {mission_dir.relative_to(PROJECT_DIR)} with mission content."
        )

    src = server_root / "mpmissions" / template
    if not src.exists():
        available = []
        mp = server_root / "mpmissions"
        if mp.exists():
            available = sorted(p.name for p in mp.iterdir() if p.is_dir())
        avail_str = "\n".join(f"          {n}" for n in available) or "          (none)"
        sys.exit(
            f"{FAIL} Mission template '{template}' not found in DayZ Server install at\n"
            f"       {src}\n"
            f"       Available templates in DayZ Server's mpmissions/:\n{avail_str}"
        )

    mission_dir.parent.mkdir(parents=True, exist_ok=True)
    if mission_dir.exists():
        shutil.rmtree(mission_dir)
        action = "Refreshed"
    else:
        action = "Copied"
    shutil.copytree(src, mission_dir)
    print(f"{OK} {action} {mission_dir.relative_to(PROJECT_DIR)}  (from DayZ Server install)")


def setup_instance_dir(instance: str, template: str) -> None:
    """Ensure .server/<instance>/ has serverDZ.cfg + server-profiles/ + client-profiles/."""
    inst_dir = SERVER_ROOT / instance
    server_profiles = inst_dir / "server-profiles"
    client_profiles = inst_dir / "client-profiles"
    server_profiles.mkdir(parents=True, exist_ok=True)
    client_profiles.mkdir(parents=True, exist_ok=True)

    cfg_path = inst_dir / "serverDZ.cfg"
    if not cfg_path.exists():
        cfg_path.write_text(default_server_cfg(instance, template), encoding="utf-8")
        print(f"{OK} Wrote default {cfg_path.relative_to(PROJECT_DIR)}")
    else:
        cfg = cfg_path.read_text(encoding="utf-8")
        if "allowFilePatching" not in cfg:
            cfg = cfg.rstrip() + "\nallowFilePatching = 1;\n"
            cfg_path.write_text(cfg, encoding="utf-8")
            print(f"{OK} Appended allowFilePatching = 1 to {cfg_path.relative_to(PROJECT_DIR)}")
        else:
            print(f"{OK} {cfg_path.relative_to(PROJECT_DIR)} unchanged (already configured)")

    print(f"{OK} {server_profiles.relative_to(PROJECT_DIR)} ready")
    print(f"{OK} {client_profiles.relative_to(PROJECT_DIR)} ready")


def default_server_cfg(instance: str, template: str) -> str:
    return dedent(
        f"""\
        // DayZ server config for instance: {instance} (mission: {template})
        // Generated by /dayz-add-server. Edit freely. The skill won't overwrite this once
        // it exists, but it WILL re-add `allowFilePatching = 1;` if you remove it
        // (clients launch with -filePatching and the server refuses connection without
        // this setting).
        hostname        = "Local Test ({instance})";
        password        = "";
        passwordAdmin   = "";
        maxPlayers      = 4;
        verifySignatures = 0;
        forceSameBuild  = 0;
        allowFilePatching = 1;
        disableVoN      = 0;
        disable3rdPerson = 0;
        instanceId      = 1;
        persistent      = 0;

        class Missions
        {{
            class DayZ
            {{
                template = "{template}";
            }};
        }};
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up a DayZ test server instance under .server/<instance>/.")
    parser.add_argument(
        "instance",
        help=(
            "Free-form instance name (becomes .server/<instance>/). If the name "
            f"matches a known map alias ({', '.join(KNOWN_MAPS)}), --map defaults "
            "to that map; otherwise --map is required."
        ),
    )
    parser.add_argument(
        "--map",
        dest="map_arg",
        default=None,
        help=(
            f"Map alias (one of: {', '.join(KNOWN_MAPS)}) or full mission template "
            "folder name (e.g. dayzOffline.namalsk). Defaults to <instance> when "
            "<instance> is itself a known alias."
        ),
    )
    parser.add_argument(
        "--refresh-mission",
        action="store_true",
        help="Re-copy the mission folder from DayZ Server install, overwriting local edits.",
    )
    args = parser.parse_args()

    gate_on_preflight()
    print()
    gate_on_old_layout()

    map_name = resolve_map_name(args.instance, args.map_arg)
    template = resolve_mission_template(map_name)
    print(f"{OK} Instance: {args.instance}  (map: {map_name}, mission: {template})")

    inst_dir = SERVER_ROOT / args.instance
    mission_dir = inst_dir / "mission"

    ensure_mission(template, mission_dir, refresh=args.refresh_mission)
    setup_instance_dir(args.instance, template)

    print()
    print(f"Instance '{args.instance}' is ready. Next:")
    print(f"  /dayz-build-pbo <ModName>")
    print(f"  /dayz-launch-test <ModName> --server {args.instance}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create `SKILL.md`**

```markdown
---
name: dayz-add-server
description: Set up a DayZ test server instance under .server/<instance>/. Copies the mission template from DayZ Server install if missing, creates per-instance serverDZ.cfg, server-profiles/, client-profiles/. Each instance is fully isolated so you can run multiple variants of the same map (chernarus, chernarus-hardcore, etc.) without cross-contamination. Refuses if the legacy workspace/_server/ layout exists; run /dayz-migrate-server first. Required before /dayz-launch-test for a given instance. Use --refresh-mission to re-copy mission content after a DayZ update.
---

# /dayz-add-server

Set up a self-contained test server instance for local DayZ mod testing. Each instance lives under `.server/<instance>/` and owns its mission copy, server config, server logs, and client logs. Run as many instances as you want, including multiple variants of the same map.

This is the **setup** half of the test loop. `/dayz-launch-test` is the **run** half, and refuses to run for an instance you haven't added yet.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-add-server\add_server.py <instance> [--map <name>] [--refresh-mission]
```

| Argument | Required? | Notes |
|---|---|---|
| `<instance>` | yes | Free-form instance name. Becomes the folder name under `.server/`. Examples: `chernarus`, `chernarus-hardcore`, `loot-test`, `livonia-pvp`. |
| `--map` | no | Map alias (`chernarus`, `livonia`, `sakhal`) or full mission template folder name (e.g. `dayzOffline.namalsk`). When omitted, `<instance>` is used as the map alias if it matches a known one; otherwise the skill fails and asks for `--map`. |
| `--refresh-mission` | no | Re-copy the mission folder from DayZ Server install, **overwriting any local edits**. Use after a DayZ update brings new mission content. Without this flag, an existing mission folder is left alone. |

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Old-layout gate**: refuses if `workspace/_server/` still exists, with a hint to run `/dayz-migrate-server`.
3. **Resolve map and mission template**: turns the instance name and `--map` flag into the canonical mission folder name via the alias table.
4. **Mission copy**: if `.server/<instance>/mission/` doesn't exist (or `--refresh-mission` was passed), copies it from `<DayZServer>/mpmissions/<template>/`. Folder is renamed to `mission/` regardless of template (the launcher pins the path explicitly).
5. **Instance directory**: ensures `.server/<instance>/` exists with:
   - `serverDZ.cfg`: default config pointing at the right mission template, with `allowFilePatching = 1;`
   - `server-profiles/`: server-side log dir
   - `client-profiles/`: client-side log dir (per-instance, so RPTs don't mix across instances)
   If `serverDZ.cfg` already exists, the existing config is preserved; only `allowFilePatching = 1;` is auto-appended if missing.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `workspace/_server/` still exists (run `/dayz-migrate-server` first).
- DayZ Server install isn't found AND the mission isn't already in `.server/<instance>/mission/`. (Install DayZ Server free from Steam appid 223350 for the initial copy. Once the mission is local, DayZ Server is no longer required.)
- `<instance>` isn't a known map alias and `--map` wasn't given. (We have no way to guess the mission template from a free-form name.)
- DayZ Server install lacks the requested mission template (e.g. `--map dayzOffline.namalsk` but DayZ Server doesn't ship namalsk; either provide the mission manually under `.server/<instance>/mission/` or correct the name).

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    Instance: chernarus-hardcore  (map: chernarus, mission: dayzOffline.chernarusplus)
[OK]    Copied .server\chernarus-hardcore\mission  (from DayZ Server install)
[OK]    Wrote default .server\chernarus-hardcore\serverDZ.cfg
[OK]    .server\chernarus-hardcore\server-profiles ready
[OK]    .server\chernarus-hardcore\client-profiles ready

Instance 'chernarus-hardcore' is ready. Next:
  /dayz-build-pbo <ModName>
  /dayz-launch-test <ModName> --server chernarus-hardcore
```

If everything is already set up, the skill no-ops the relevant steps and reports them as `[OK]` (already present).

## Editing what this skill creates

- **Mission folder** at `.server/<instance>/mission/` is yours to edit. The server runs with `-filePatching` so edits to `init.c`, `cfggameplay.json`, `db/types.xml`, etc. are live on the next launch.
- **`serverDZ.cfg`** at `.server/<instance>/serverDZ.cfg` is yours to tune (max players, persistence, etc.). The skill never overwrites your edits, but it WILL re-add `allowFilePatching = 1;` if you remove it (without that, clients with `-filePatching` can't connect).

## Do not

- Don't edit missions inside the DayZ Server Steam install; edit the workspace copy.
- Don't move `.server/` into `workspace/`. The split is deliberate: `workspace/` is for active mod sources, `.server/` is for runtime artifacts.
```

- [ ] **Step 3: Verify it runs**

Run: `python .claude\skills\dayz-add-server\add_server.py --help`
Expected: argparse usage output listing `instance`, `--map`, `--refresh-mission` arguments. Exit 0.

(End-to-end behavioral verification happens in Task 13 against the full migrated environment.)

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/dayz-add-server/SKILL.md .claude/skills/dayz-add-server/add_server.py
git commit -m "feat(dayz): add dayz-add-server skill (replaces dayz-add-map, instance-based)"
```

---

## Task 2: Create `dayz-migrate-server` skill

**Files:**
- Create: `.claude/skills/dayz-migrate-server/SKILL.md`
- Create: `.claude/skills/dayz-migrate-server/migrate.py`

- [ ] **Step 1: Create `migrate.py`**

```python
"""dayz-migrate-server: One-shot migration from workspace/_server/ to .server/<instance>/.

For each old map directory under workspace/_server/maps/<map>/, creates a new
instance at .server/<map>/ with:
  - mission/ (copied from workspace/_server/missions/<template>/, renamed)
  - serverDZ.cfg (moved)
  - server-profiles/ (moved from workspace/_server/maps/<map>/profiles/)
  - client-profiles/ (assigned the contents of workspace/_server/!ClientDiagLogs/
    for the alphabetically-first migrated instance only; other instances start empty)

Idempotent: re-running on a partially-migrated state continues from where it
stopped. Leaves workspace/_server/ intact. User deletes manually after verifying
the new instances launch correctly.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"

LEGACY_SERVER_ROOT = PROJECT_DIR / "workspace" / "_server"
LEGACY_MISSIONS_DIR = LEGACY_SERVER_ROOT / "missions"
LEGACY_MAPS_DIR = LEGACY_SERVER_ROOT / "maps"
LEGACY_CLIENT_DIAG = LEGACY_SERVER_ROOT / "!ClientDiagLogs"

SERVER_ROOT = PROJECT_DIR / ".server"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def read_template_from_cfg(cfg_path: Path) -> str | None:
    """Parse `template = "...";` from a serverDZ.cfg. Returns the mission folder
    name (e.g. dayzOffline.chernarusplus) or None if not found.
    """
    if not cfg_path.is_file():
        return None
    try:
        content = cfg_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'template\s*=\s*"([^"]+)"', content)
    return m.group(1) if m else None


def discover_old_maps() -> list[str]:
    """Return the list of map directory names under workspace/_server/maps/."""
    if not LEGACY_MAPS_DIR.is_dir():
        return []
    return sorted(p.name for p in LEGACY_MAPS_DIR.iterdir() if p.is_dir())


def plan_migration(rename_to: str | None) -> list[dict]:
    """Build the migration plan.

    Each entry: {
        "instance": str,
        "old_map_dir": Path,
        "old_cfg": Path,
        "old_profiles": Path,
        "template": str | None,
        "new_inst_dir": Path,
    }
    """
    old_maps = discover_old_maps()
    if not old_maps:
        return []

    if rename_to and len(old_maps) != 1:
        sys.exit(
            f"{FAIL} --instance-name only valid when exactly one old map directory exists.\n"
            f"       Found: {', '.join(old_maps)}\n"
            "       Re-run without --instance-name; each old map becomes an instance\n"
            "       named after the old map directory."
        )

    plan = []
    for map_name in old_maps:
        instance = rename_to if rename_to else map_name
        old_map_dir = LEGACY_MAPS_DIR / map_name
        old_cfg = old_map_dir / "serverDZ.cfg"
        old_profiles = old_map_dir / "profiles"
        template = read_template_from_cfg(old_cfg)
        plan.append({
            "instance": instance,
            "old_map_dir": old_map_dir,
            "old_cfg": old_cfg,
            "old_profiles": old_profiles,
            "template": template,
            "new_inst_dir": SERVER_ROOT / instance,
        })
    return plan


def print_plan(plan: list[dict]) -> None:
    print(f"Migration plan: {len(plan)} instance(s)")
    for entry in plan:
        rel_old = entry["old_map_dir"].relative_to(PROJECT_DIR)
        rel_new = entry["new_inst_dir"].relative_to(PROJECT_DIR)
        tmpl = entry["template"] or "(template not found in cfg)"
        print(f"  {rel_old}  ->  {rel_new}  (mission template: {tmpl})")
    if LEGACY_CLIENT_DIAG.exists() and plan:
        first = plan[0]["instance"]
        rel_diag = LEGACY_CLIENT_DIAG.relative_to(PROJECT_DIR)
        rel_target = (SERVER_ROOT / first / "client-profiles").relative_to(PROJECT_DIR)
        print(f"  {rel_diag}  ->  {rel_target}  (orphaned shared client logs assigned to first instance)")


def migrate_instance(entry: dict) -> None:
    """Materialize one instance from one old map dir."""
    instance = entry["instance"]
    new_inst = entry["new_inst_dir"]
    old_cfg = entry["old_cfg"]
    old_profiles = entry["old_profiles"]
    template = entry["template"]

    new_inst.mkdir(parents=True, exist_ok=True)

    # Mission: copy from legacy missions dir (named after template) into <inst>/mission/
    new_mission = new_inst / "mission"
    if not new_mission.exists():
        if template is None:
            print(f"{WARN} {instance}: no `template = ...` line in serverDZ.cfg; skipping mission copy")
        else:
            old_mission = LEGACY_MISSIONS_DIR / template
            if old_mission.is_dir():
                shutil.copytree(old_mission, new_mission)
                print(f"{OK} Copied mission for '{instance}': {new_mission.relative_to(PROJECT_DIR)}")
            else:
                print(f"{WARN} {instance}: legacy mission folder '{old_mission.relative_to(PROJECT_DIR)}' not found; mission/ will be empty")

    # serverDZ.cfg: move
    new_cfg = new_inst / "serverDZ.cfg"
    if not new_cfg.exists() and old_cfg.is_file():
        shutil.move(str(old_cfg), str(new_cfg))
        print(f"{OK} Moved serverDZ.cfg for '{instance}'")

    # Server profiles: move
    new_server_profiles = new_inst / "server-profiles"
    if not new_server_profiles.exists():
        if old_profiles.is_dir():
            shutil.move(str(old_profiles), str(new_server_profiles))
            print(f"{OK} Moved server profiles for '{instance}'")
        else:
            new_server_profiles.mkdir(parents=True, exist_ok=True)
            print(f"{OK} Created empty server-profiles for '{instance}' (no legacy profiles found)")

    # Client profiles: empty by default (the orphaned shared !ClientDiagLogs/ is
    # handled in migrate_orphaned_client_logs, only for the first instance).
    new_client_profiles = new_inst / "client-profiles"
    new_client_profiles.mkdir(parents=True, exist_ok=True)


def migrate_orphaned_client_logs(plan: list[dict]) -> None:
    """The old shared workspace/_server/!ClientDiagLogs/ has no per-instance affinity.
    Assign it to the alphabetically-first migrated instance and warn the user.
    """
    if not LEGACY_CLIENT_DIAG.exists() or not plan:
        return
    first_inst = plan[0]["instance"]
    target = SERVER_ROOT / first_inst / "client-profiles"
    target.mkdir(parents=True, exist_ok=True)

    # Move contents (not the folder itself) so we don't clobber the empty target dir.
    moved_any = False
    for child in list(LEGACY_CLIENT_DIAG.iterdir()):
        dest = target / child.name
        if dest.exists():
            print(f"{WARN} {dest.relative_to(PROJECT_DIR)} already exists; leaving {child.name} in place")
            continue
        shutil.move(str(child), str(dest))
        moved_any = True

    if moved_any:
        print(f"{OK} Moved orphaned client logs into '{first_inst}' client-profiles")
        print(f"{WARN} Old layout did not isolate client logs by map. Logs were assigned to the")
        print(f"       first instance ('{first_inst}') alphabetically. Manually redistribute to")
        print("       other instances if you want them attributed differently.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate workspace/_server/ to .server/<instance>/ layout."
    )
    parser.add_argument(
        "--instance-name",
        default=None,
        help=(
            "Override the migrated instance name. Only valid when exactly one "
            "old map directory exists (otherwise instance names default to old "
            "map directory names)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned migration; do not move or copy anything.",
    )
    args = parser.parse_args()

    gate_on_preflight()
    print()

    if not LEGACY_SERVER_ROOT.exists():
        print(f"{OK} No legacy workspace/_server/ found. Nothing to migrate.")
        return 0

    plan = plan_migration(args.instance_name)
    if not plan:
        print(f"{WARN} workspace/_server/ exists but contains no map directories at maps/.")
        print(f"       Inspect manually and delete workspace/_server/ if appropriate.")
        return 0

    print_plan(plan)
    if args.dry_run:
        print()
        print("(--dry-run) nothing migrated.")
        return 0

    print()
    SERVER_ROOT.mkdir(parents=True, exist_ok=True)
    for entry in plan:
        migrate_instance(entry)
    migrate_orphaned_client_logs(plan)

    print()
    print(f"{OK} Migration complete. New instances under {SERVER_ROOT.relative_to(PROJECT_DIR)}/")
    print()
    print(f"{WARN} Legacy workspace/_server/ has been left intact.")
    print("       Verify the new instances launch correctly:")
    for entry in plan:
        print(f"         /dayz-launch-test <ModName> --server {entry['instance']}")
    print("       Then delete the legacy folder manually:")
    print("         cmd /c rmdir /s /q workspace\\_server")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create `SKILL.md`**

```markdown
---
name: dayz-migrate-server
description: One-shot migration from the legacy workspace/_server/ layout to .server/<instance>/. For each old map directory at workspace/_server/maps/<map>/, creates a matching .server/<map>/ instance with mission/, serverDZ.cfg, server-profiles/, client-profiles/. Mission folders are copied (not moved), and renamed to mission/. The orphaned shared !ClientDiagLogs/ is assigned to the alphabetically-first migrated instance. Idempotent. Leaves the legacy folder intact for the user to delete after verification.
---

# /dayz-migrate-server

Migrate from the legacy DayZ test-server layout (`workspace/_server/`) to the new instance-based layout (`.server/<instance>/`). One-shot; subsequent skills (`/dayz-add-server`, `/dayz-launch-test`, `/dayz-clean-workspace`) all refuse to run while the legacy folder still exists, so this is a hard gate.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-migrate-server\migrate.py [--instance-name <name>] [--dry-run]
```

| Argument | Required? | Notes |
|---|---|---|
| `--instance-name` | no | Override the new instance name. Only valid when exactly one old map directory exists (`workspace/_server/maps/` has exactly one child). With multiple maps, instance names always default to old map directory names. |
| `--dry-run` | no | Print the planned migration; touch nothing. |

## What it does

1. **Preflight gate**: runs `/dayz-preflight`; halts on non-zero.
2. **Detect legacy layout**: exits 0 if `workspace/_server/` doesn't exist.
3. **Plan**: for each `workspace/_server/maps/<map>/` directory, plan a new instance at `.server/<map>/` (or `.server/<--instance-name>/` if exactly one map and the flag was given).
4. **Migrate per instance:**
   - `mission/`: **copied** (not moved) from `workspace/_server/missions/<template>/` (the template name comes from the old `serverDZ.cfg`'s `template = "..."` line). Mission folder is renamed to `mission/` regardless of original name. Mission stays a copy because multiple old maps may have shared one template; moving would break the others.
   - `serverDZ.cfg`: moved.
   - `server-profiles/`: moved from old `profiles/`.
   - `client-profiles/`: created empty.
5. **Orphaned shared client logs**: `workspace/_server/!ClientDiagLogs/` contents are moved into the alphabetically-first migrated instance's `client-profiles/`, with a printed warning that the old layout did not isolate client logs and the user can manually redistribute.
6. **Leaves legacy intact**: `workspace/_server/` remains for the user to inspect and delete manually after verifying the new instances launch.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `--instance-name` is given but more than one old map directory exists.

## Output (success)

```
DayZ preflight
... (preflight output)
Preflight complete.

Migration plan: 1 instance(s)
  workspace\_server\maps\chernarus  ->  .server\chernarus  (mission template: dayzOffline.chernarusplus)
  workspace\_server\!ClientDiagLogs  ->  .server\chernarus\client-profiles  (orphaned shared client logs assigned to first instance)

[OK]    Copied mission for 'chernarus': .server\chernarus\mission
[OK]    Moved serverDZ.cfg for 'chernarus'
[OK]    Moved server profiles for 'chernarus'
[OK]    Moved orphaned client logs into 'chernarus' client-profiles
[WARN]  Old layout did not isolate client logs by map. Logs were assigned to the
        first instance ('chernarus') alphabetically. Manually redistribute to
        other instances if you want them attributed differently.

[OK]    Migration complete. New instances under .server/

[WARN]  Legacy workspace/_server/ has been left intact.
        Verify the new instances launch correctly:
          /dayz-launch-test <ModName> --server chernarus
        Then delete the legacy folder manually:
          cmd /c rmdir /s /q workspace\_server
```

## Do not

- Don't run this skill twice without inspecting the result. It's idempotent (safe to re-run on partial state) but the second run is a no-op once `.server/<instance>/` directories already have content.
- Don't auto-delete `workspace/_server/` from the migration. The legacy folder is left intact deliberately so the user can verify the new instances work before committing to the move.
```

- [ ] **Step 3: Verify it runs**

Run: `python .claude\skills\dayz-migrate-server\migrate.py --help`
Expected: argparse usage with `--instance-name` and `--dry-run`. Exit 0.

(Behavioral verification of actual migration happens in Task 13.)

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/dayz-migrate-server/SKILL.md .claude/skills/dayz-migrate-server/migrate.py
git commit -m "feat(dayz): add dayz-migrate-server skill for one-shot legacy server migration"
```

---

## Task 3: Update `dayz-launch-test` for `.server/` and `--server` flag

**Files:**
- Modify: `.claude/skills/dayz-launch-test/launch.py`
- Modify: `.claude/skills/dayz-launch-test/SKILL.md`

- [ ] **Step 1: Replace constants block in `launch.py`**

Current (lines 24-34):
```python
REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
WORKSPACE = PROJECT_DIR / "workspace"
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
SERVER_ROOT = WORKSPACE / "_server"
MISSIONS_DIR = SERVER_ROOT / "missions"
MAPS_DIR = SERVER_ROOT / "maps"
CLIENT_DIAG_LOGS = SERVER_ROOT / "!ClientDiagLogs"
```

Replace with:
```python
REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
SERVER_ROOT = PROJECT_DIR / ".server"
LEGACY_SERVER_ROOT = PROJECT_DIR / "workspace" / "_server"
```

`MISSIONS_DIR`, `MAPS_DIR`, and `CLIENT_DIAG_LOGS` are deleted (paths now derived per-instance). `WORKSPACE` is no longer needed in this file.

- [ ] **Step 2: Replace `KNOWN_MAPS` block to rename default**

Find (around lines 49-55):
```python
KNOWN_MAPS: dict[str, str] = {
    "chernarus": "dayzOffline.chernarusplus",
    "livonia": "dayzOffline.enoch",
    "sakhal": "dayzOffline.sakhal",
}
DEFAULT_MAP = "chernarus"
```

Replace with:
```python
KNOWN_MAPS: dict[str, str] = {
    "chernarus": "dayzOffline.chernarusplus",
    "livonia": "dayzOffline.enoch",
    "sakhal": "dayzOffline.sakhal",
}
DEFAULT_INSTANCE = "chernarus"
```

- [ ] **Step 3: Add the old-layout gate**

Below `gate_on_preflight()` definition (after the function ends, around line 84), add:

```python
def gate_on_old_layout() -> None:
    """Refuse to run if workspace/_server/ still exists. Forces explicit migration."""
    if LEGACY_SERVER_ROOT.exists():
        sys.exit(
            f"{FAIL} Old layout detected at {LEGACY_SERVER_ROOT.relative_to(PROJECT_DIR)}.\n"
            "       The server runtime moved from workspace/_server/ to .server/.\n"
            "       Run: python .claude/skills/dayz-migrate-server/migrate.py"
        )
```

- [ ] **Step 4: Replace `verify_map_environment` with `verify_instance_environment`**

Find the entire `verify_map_environment` function (around lines 142-181) and replace with:

```python
def verify_instance_environment(instance: str) -> tuple[Path, Path, Path, Path]:
    """Verify .server/<instance>/ has serverDZ.cfg + mission/ + server-profiles/ + client-profiles/.

    Does NOT create anything (mission, cfg); that's /dayz-add-server's job.
    Hard-fails with a hint if the instance hasn't been added yet.

    Returns (cfg_path, server_profile_dir, mission_path, client_profile_dir).
    """
    inst_dir = SERVER_ROOT / instance
    mission_path = inst_dir / "mission"
    cfg_path = inst_dir / "serverDZ.cfg"
    server_profile_dir = inst_dir / "server-profiles"
    client_profile_dir = inst_dir / "client-profiles"

    missing = []
    if not mission_path.exists():
        missing.append(f"mission folder: {mission_path.relative_to(PROJECT_DIR)}")
    if not cfg_path.exists():
        missing.append(f"server cfg: {cfg_path.relative_to(PROJECT_DIR)}")
    if missing:
        details = "\n".join(f"          - {m}" for m in missing)
        sys.exit(
            f"{FAIL} Instance '{instance}' is not set up. Missing:\n{details}\n"
            f"       Run: python .claude/skills/dayz-add-server/add_server.py {instance}"
        )

    # Existing cfg: auto-append allowFilePatching=1 if missing (clients launch
    # with -filePatching; without this setting the server refuses connection,
    # error 0x00020005). This is the only mutation the launch skill performs.
    cfg = cfg_path.read_text(encoding="utf-8")
    if "allowFilePatching" not in cfg:
        cfg = cfg.rstrip() + "\nallowFilePatching = 1;\n"
        cfg_path.write_text(cfg, encoding="utf-8")
        print(f"{OK} Appended allowFilePatching = 1 to {cfg_path.relative_to(PROJECT_DIR)}")

    server_profile_dir.mkdir(parents=True, exist_ok=True)
    client_profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"{OK} Instance: {instance}")
    print(f"{OK} Instance dir: {inst_dir.relative_to(PROJECT_DIR)}")
    return cfg_path, server_profile_dir, mission_path, client_profile_dir
```

- [ ] **Step 5: Update `main()` for `--server` flag and new flow**

Find the entire `main()` function (around lines 272-344) and replace with:

```python
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch local DayZ server + client with one or more built mods."
    )
    parser.add_argument("modnames", nargs="+", help="Mod names already built (PBO must exist).")
    parser.add_argument(
        "--server",
        default=DEFAULT_INSTANCE,
        help=(
            f"Server instance to launch on (default: {DEFAULT_INSTANCE}). "
            "Must have been added via /dayz-add-server."
        ),
    )
    parser.add_argument("--port", type=int, default=2302, help="Server port (default: 2302).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved commands without launching anything.",
    )
    args = parser.parse_args()

    gate_on_preflight()
    print()
    gate_on_old_layout()
    verify_built_mods(args.modnames)
    diag_exe = resolve_diag_client()
    cfg_path, server_profile_dir, mission_path, client_profile_dir = verify_instance_environment(args.server)

    display = read_client_display_prefs()

    # Absolute mod paths so the engine resolves -mod=<arg> correctly regardless
    # of the working directory the subprocess inherits.
    mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in args.modnames)
    server_cmd = build_server_cmd(
        diag_exe, mod_arg, args.port, cfg_path, server_profile_dir, mission_path
    )
    client_cmd = build_client_cmd(diag_exe, mod_arg, args.port, client_profile_dir, display)

    if args.dry_run:
        print()
        print(f"[DRY-RUN] Server cmd: {' '.join(server_cmd)}")
        print(f"[DRY-RUN] Client cmd: {' '.join(client_cmd)}")
        return 0

    print()
    print(f"[Launch] Server: {' '.join(server_cmd)}")
    sys.stdout.flush()
    server_proc = subprocess.Popen(server_cmd)
    print(f"{OK} Server PID: {server_proc.pid}")
    print("        Waiting 5s for server to start listening...")
    sys.stdout.flush()
    time.sleep(5)

    print()
    print(f"[Launch] Client: {' '.join(client_cmd)}")
    sys.stdout.flush()
    client_proc = subprocess.Popen(client_cmd)
    print(f"{OK} Client PID: {client_proc.pid}")

    print()
    print("Both running. Close the windows manually to stop.")
    print(f"  Server PID: {server_proc.pid}    Client PID: {client_proc.pid}")
    print(f"  Server logs: {server_profile_dir.relative_to(PROJECT_DIR)}")
    print(f"  Client logs: {client_profile_dir.relative_to(PROJECT_DIR)}")
    return 0
```

- [ ] **Step 6: Remove no-longer-used `resolve_mission_template` function**

Find the `resolve_mission_template` function (around lines 132-139) and delete it. The launcher no longer needs to resolve a map name to a template; the cfg's `template = ...` line is the canonical source and the launcher just consumes the mission folder path directly.

- [ ] **Step 7: Update the docstring at the top of the file**

Find lines 1-11 (module docstring) and replace with:

```python
"""dayz-launch-test: Launch a local DayZ Diag server + diag client for a built mod.

Verifies state and launches. Setup (mission copy, per-instance serverDZ.cfg,
profile dirs) is the responsibility of /dayz-add-server. This skill refuses to
run if the instance hasn't been added yet, or if the legacy workspace/_server/
layout still exists (run /dayz-migrate-server first).

Always launches the server first per L2 conventions (DayZ cannot be tested
standalone). Both server and client run from DayZDiag_x64.exe with -filePatching.

See SKILL.md for full usage.
"""
```

- [ ] **Step 8: Verify it runs**

Run: `python .claude\skills\dayz-launch-test\launch.py --help`
Expected: argparse usage showing `modnames`, `--server` (not `--map`), `--port`, `--dry-run`. Exit 0.

- [ ] **Step 9: Rewrite `SKILL.md`**

Open `.claude/skills/dayz-launch-test/SKILL.md` and replace its entire content with:

```markdown
---
name: dayz-launch-test
description: Launch a local DayZ Diag server plus the diag client connecting to it (run-only, does no setup). Verifies the instance has been added via /dayz-add-server; refuses with a clear hint otherwise. Refuses if the legacy workspace/_server/ folder still exists (run /dayz-migrate-server first). --server selects the instance (chernarus default). Always loads server alongside client per L2 conventions.
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
2. **Old-layout gate**: refuses if `workspace/_server/` still exists (run `/dayz-migrate-server`).
3. **Built-mod check**: for each mod, verifies at least one `.pbo` exists in `P:\Mods\@<ModName>\Addons\`. Fails fast with a hint to run `/dayz-build-pbo` if missing.
4. **Diag client resolution**: finds `DayZDiag_x64.exe` via `find_dayz_diag()` (env var, DayZ game install, Steam paths). Hard-fails if missing. Both client and server run from the same diag binary; the server adds `-server`. Retail `DayZ_x64.exe` and `DayZServer_x64.exe` are NOT used; both block past the loading screen with `-filePatching` enabled.
5. **Instance state verification**: confirms `.server/<instance>/mission/` AND `.server/<instance>/serverDZ.cfg` exist. Hard-fails with a hint to run `/dayz-add-server <instance>` if either is missing. The only mutation this skill performs on an existing cfg is auto-appending `allowFilePatching = 1;` if absent.
6. **Launch server**: spawns `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/server-profiles -mission=<instance>/mission -mod=@Mod1;@Mod2 -filePatching -port=<port>`.
7. **Wait 5s** for the server to start listening.
8. **Launch client**: spawns `DayZDiag_x64.exe -profiles=<instance>/client-profiles -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=<port> -filePatching` plus the display flags from per-clone preferences.
9. **Print PIDs and exit.** Both processes run independently. Close the windows manually to stop them, or run `/dayz-stop-test`.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `workspace/_server/` still exists (run `/dayz-migrate-server` first).
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
```

- [ ] **Step 10: Verify SKILL.md links and references are correct**

Run: `Grep "dayz-add-map\|workspace/_server\|!ClientDiagLogs\|--map" .claude\skills\dayz-launch-test\SKILL.md`
Expected: zero matches. The SKILL.md should reference only `dayz-add-server`, `.server/`, `client-profiles/`, and `--server`.

- [ ] **Step 11: Commit**

```bash
git add .claude/skills/dayz-launch-test/launch.py .claude/skills/dayz-launch-test/SKILL.md
git commit -m "refactor(dayz): launch-test consumes .server/<instance>/, --server flag"
```

---

## Task 4: Update `dayz-clean-workspace` for `.server/` and old-layout gate

**Files:**
- Modify: `.claude/skills/dayz-clean-workspace/clean.py`
- Modify: `.claude/skills/dayz-clean-workspace/SKILL.md`

- [ ] **Step 1: Update constants in `clean.py`**

Find:
```python
SERVER_ROOT = WORKSPACE / "_server"
```

Replace with:
```python
SERVER_ROOT = PROJECT_DIR / ".server"
LEGACY_SERVER_ROOT = WORKSPACE / "_server"
```

- [ ] **Step 2: Add legacy-layout gate inside `main()`**

Find this block in `main()` (around line 234):
```python
    if args.include_server and SERVER_ROOT.exists():
        plan.append(("server staging", SERVER_ROOT))
```

Replace with:
```python
    if args.include_server:
        if LEGACY_SERVER_ROOT.exists():
            sys.exit(
                f"{FAIL} Legacy layout detected at {LEGACY_SERVER_ROOT.relative_to(PROJECT_DIR)}.\n"
                "       --include-server now targets .server/ at the project root, not\n"
                "       workspace/_server/. Run: python .claude/skills/dayz-migrate-server/migrate.py\n"
                "       (or remove the legacy folder manually if it is no longer wanted)."
            )
        if SERVER_ROOT.exists():
            plan.append(("server staging", SERVER_ROOT))
```

- [ ] **Step 3: Update the module docstring**

Find lines 1-13 (top of file) and update the description block. Replace:

```python
"""dayz-clean-workspace: Remove DayZ scaffolds and their deployed artifacts.

For each scaffolded mod under workspace/<ModName>/ (signature: contains
config.cpp + $PBOPREFIX$):
  - workspace/<ModName>/             -> always removed
  - P:\\<ModName>\\                   -> removed only if it's a junction/symlink
                                        whose target is workspace/<ModName>/
  - P:\\Mods\\@<ModName>\\            -> removed if present

Safe: user-installed mods at <DayZ install>\\!Workshop\\@<Subscribed>\\ are
never touched (the match-on-scaffold rule is what guarantees this).

See SKILL.md for full usage.
"""
```

with:

```python
"""dayz-clean-workspace: Remove DayZ scaffolds and their deployed artifacts.

For each scaffolded mod under workspace/<ModName>/ (signature: contains
config.cpp + $PBOPREFIX$):
  - workspace/<ModName>/             -> always removed
  - P:\\<ModName>\\                   -> removed only if it's a junction/symlink
                                        whose target is workspace/<ModName>/
  - P:\\Mods\\@<ModName>\\            -> removed if present

With --include-server, also removes .server/ at the project root. Refuses if
the legacy workspace/_server/ folder still exists (run /dayz-migrate-server
first; this skill does not handle the migration itself).

Safe: user-installed mods at <DayZ install>\\!Workshop\\@<Subscribed>\\ are
never touched (the match-on-scaffold rule is what guarantees this).

See SKILL.md for full usage.
"""
```

- [ ] **Step 4: Verify it runs**

Run: `python .claude\skills\dayz-clean-workspace\clean.py --dry-run`
Expected: prints plan or "Nothing to clean.", does not crash. Exit 0.

- [ ] **Step 5: Update `SKILL.md`**

Open `.claude/skills/dayz-clean-workspace/SKILL.md`. Two edits:

**Edit A:** In the frontmatter `description` field, replace `--include-server also removes workspace/_server/.` with `--include-server also removes .server/ (refuses if legacy workspace/_server/ still exists; run /dayz-migrate-server first).`

**Edit B:** Find this row in the args table (around line 26):
```markdown
| `--include-server` | no | Also remove `workspace/_server/` (mission copies, per-map cfg, profiles, !ClientDiagLogs). |
```

Replace with:
```markdown
| `--include-server` | no | Also remove `.server/` at the project root (all instances: missions, configs, profiles, client logs). Refuses if legacy `workspace/_server/` still exists. |
```

**Edit C:** Find this paragraph (around line 45):
```markdown
With `--include-server`, also removes `workspace/_server/` (mission copies, all per-map configs, all profiles, !ClientDiagLogs). Use this for a full reset; otherwise the server staging stays so you don't have to re-copy missions next time.
```

Replace with:
```markdown
With `--include-server`, also removes `.server/` at the project root (all instances under it: missions, configs, profiles, client logs). Use this for a full reset; otherwise the server staging stays so you don't have to re-copy missions next time. If `workspace/_server/` (the legacy layout) still exists, this skill refuses with a hint to run `/dayz-migrate-server` first; we don't silently leave the old folder behind.
```

- [ ] **Step 6: Verify SKILL.md no longer references the old layout**

Run: `Grep "workspace/_server\|!ClientDiagLogs" .claude\skills\dayz-clean-workspace\SKILL.md`
Expected: matches only inside the new "refuses if legacy ... still exists" hint. No other references.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/dayz-clean-workspace/clean.py .claude/skills/dayz-clean-workspace/SKILL.md
git commit -m "refactor(dayz): clean-workspace --include-server targets .server/, refuses on legacy layout"
```

---

## Task 5: Update `.claude-plugin/plugin.json` skill registry

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Update `description` and `skills` array**

Find:
```json
  "description": "AI agent stack for DayZ modding. Ships 11 specialist subagents and 23 DayZ skills covering the full mod pipeline (preflight, scaffold, build PBO, launch test, types.xml, RAG indexers, p3d audit/debin, particle effects), plus the dayz-rag MCP server for semantic search over vanilla Enforce Script and the Bohemia community wiki.",
```

Replace `23 DayZ skills` with `24 DayZ skills` (we're adding migrate-server while replacing add-map; net +1).

In the `skills` array, find:
```json
    "./.claude/skills/dayz-add-map",
```

Replace with:
```json
    "./.claude/skills/dayz-add-server",
    "./.claude/skills/dayz-migrate-server",
```

- [ ] **Step 2: Verify JSON parses**

Run: `python -c "import json; json.load(open('.claude-plugin/plugin.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore(plugin): register dayz-add-server and dayz-migrate-server, drop dayz-add-map"
```

---

## Task 6: Update `.claude/skills/_shared/dayz-conventions.md`

**Files:**
- Modify: `.claude/skills/_shared/dayz-conventions.md`

- [ ] **Step 1: Replace the server-staging paragraph**

Find lines 99-104 (the bullet starting `**Server staging area lives at \`workspace/_server/\`**`):

```markdown
- **Server staging area lives at `workspace/_server/`**, with two subtrees and the client profile at the root:
  - `workspace/_server/missions/<mission-template>/`: **editable copies** of mission folders (e.g. `dayzOffline.chernarusplus/`). Created by `/dayz-add-map` on demand from DayZ Server's `mpmissions/`; user-editable thereafter (server runs with `-filePatching` so edits are live). Never edit the original DayZ Server install.
  - `workspace/_server/maps/<map-name>/`: per-map `serverDZ.cfg` + `profiles/`. Created by `/dayz-add-map`. Each map (chernarus, livonia, sakhal, custom) has its own config + server-side log/BattlEye state so tuning doesn't bleed across maps.
  - `workspace/_server/!ClientDiagLogs/` is the **client `-profiles=` directory**. All client-side diag artifacts (`Users/`, `DataCache/`, `BattlEye/`, RPT logs, script logs) get contained in that one folder rather than spreading across the `_server` root or polluting the DayZ game install dir.
- **Setup vs run is split into two skills.** `/dayz-add-map <map>` does setup (mission copy + per-map cfg + profiles). `/dayz-launch-test <mod> --map <map>` does run (verify + spawn). The launch skill never copies missions, never writes cfgs from scratch; it refuses with a hint to run `/dayz-add-map` if state is missing. Only mutation launch does is auto-append `allowFilePatching = 1;` to an existing cfg that lacks it.
- **Never gitignore `workspace/_server/` template-wide.** It's a per-clone decision: some users want their tuned cfgs and edited missions tracked in their project's git, others don't. The template doesn't enforce.
```

Replace with:

```markdown
- **Server runtime lives at `.server/<instance>/`** at the project root (not under `workspace/`). Each instance is fully self-contained:
  - `.server/<instance>/mission/`: **editable copy** of the mission folder. Created by `/dayz-add-server` on demand from DayZ Server's `mpmissions/<template>/`; user-editable thereafter (server runs with `-filePatching` so edits are live). Never edit the original DayZ Server install. Folder is named `mission/` regardless of template (the launcher pins the path explicitly via `-mission=<abspath>`).
  - `.server/<instance>/serverDZ.cfg`: per-instance server config. The `template = "..."` line links the instance to its DayZ mission base. Each instance can have totally different tuning (player count, persistence, time of day) without bleeding across instances.
  - `.server/<instance>/server-profiles/`: server-side log dir (RPT, script.log, BattlEye state).
  - `.server/<instance>/client-profiles/`: client-side `-profiles=` dir. Per-instance, so RPTs and player profiles don't mix when switching between instances.
- **Instance is the unit of identity, not map.** A user can run multiple variants of the same map (chernarus vanilla vs chernarus-hardcore) by adding two instances. `serverDZ.cfg`'s `template` field is the only place the map link is encoded.
- **Setup vs run is split into two skills.** `/dayz-add-server <instance>` does setup (mission copy + per-instance cfg + profile dirs). `/dayz-launch-test <mod> --server <instance>` does run (verify + spawn). The launch skill never copies missions, never writes cfgs from scratch; it refuses with a hint to run `/dayz-add-server` if state is missing. Only mutation launch does is auto-append `allowFilePatching = 1;` to an existing cfg that lacks it.
- **Legacy `workspace/_server/` layout is migrated via `/dayz-migrate-server`.** All three runtime skills (`/dayz-add-server`, `/dayz-launch-test`, `/dayz-clean-workspace --include-server`) refuse to run while `workspace/_server/` still exists. Migration is one-shot and idempotent; the legacy folder is left intact for the user to delete after verifying.
- **`.server/` is gitignored by default.** Logs, profiles, BE state, storage, and the rest of the runtime junk are not tracked. User-edited `serverDZ.cfg` and `mission/` contents are tracked via negation patterns in `.gitignore`.
```

- [ ] **Step 2: Update the two related paragraphs about mission paths**

Find lines 122-123:
```markdown
- The launch skill passes `-mission=<absolute path to workspace/_server/missions/<template>>` to pin the mission folder explicitly (the engine otherwise looks in the diag binary's local `mpmissions/`, which doesn't exist in the DayZ game install).
- DayZ Server install (Steam appid 223350) is **only required for the initial mission bootstrap**. After missions are copied to `workspace/_server/missions/`, DayZ Server can be uninstalled; the workspace copy is the source of truth.
```

Replace with:
```markdown
- The launch skill passes `-mission=<absolute path to .server/<instance>/mission>` to pin the mission folder explicitly (the engine otherwise looks in the diag binary's local `mpmissions/`, which doesn't exist in the DayZ game install).
- DayZ Server install (Steam appid 223350) is **only required for the initial mission bootstrap**. After missions are copied into `.server/<instance>/mission/`, DayZ Server can be uninstalled; the workspace copy is the source of truth.
```

- [ ] **Step 3: Verify no stale references**

Run: `Grep "workspace/_server\|dayz-add-map\|!ClientDiagLogs" .claude\skills\_shared\dayz-conventions.md`
Expected: zero matches. (If any remain, edit them by hand and re-grep until clean.)

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/_shared/dayz-conventions.md
git commit -m "docs(conventions): rewrite server-runtime section for .server/<instance>/ layout"
```

---

## Task 7: Update L1 docs (CLAUDE.md, AGENTS.md, GEMINI.md)

**Files:**
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`
- Modify: `GEMINI.md`

These three files hold identical content (per L1 working-conventions rule). Make the same edits in all three.

- [ ] **Step 1: Update the workspace bullet in `CLAUDE.md`**

Find line 53 in `CLAUDE.md`:
```markdown
- `workspace/` is for **in-progress mod projects**: anything you're actively iterating on across sessions (DayZ mod sources, test server setup). Each mod gets its own subfolder (`workspace/<ModName>/`); shared server scaffolding lives at `workspace/_server/`.
```

Replace with:
```markdown
- `workspace/` is for **in-progress mod projects**: anything you're actively iterating on across sessions. Each mod gets its own subfolder (`workspace/<ModName>/`).
- `.server/` (project root) holds **DayZ test-server runtime**, one folder per instance (`.server/<instance>/{mission, serverDZ.cfg, server-profiles, client-profiles}`). Created by `/dayz-add-server`. Multiple instances allowed (e.g. chernarus, chernarus-hardcore). Gitignored by default except for `serverDZ.cfg` and `mission/` contents.
```

- [ ] **Step 2: Apply the same edit to `AGENTS.md` and `GEMINI.md`**

These files mirror `CLAUDE.md`. Apply the identical replacement.

- [ ] **Step 3: Verify no stale references in any of the three files**

Run for each file:
- `Grep "workspace/_server\|dayz-add-map" CLAUDE.md`
- `Grep "workspace/_server\|dayz-add-map" AGENTS.md`
- `Grep "workspace/_server\|dayz-add-map" GEMINI.md`

Expected: zero matches in each. (If any references remain to the old skill name or path, replace them with `dayz-add-server` and `.server/<instance>/` respectively.)

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md AGENTS.md GEMINI.md
git commit -m "docs(L1): server runtime moved from workspace/_server/ to .server/<instance>/"
```

---

## Task 8: Update `docs/dayz-modding.md`

**Files:**
- Modify: `docs/dayz-modding.md`

- [ ] **Step 1: Replace `dayz-add-map` references**

Run: `Grep -n "dayz-add-map" docs/dayz-modding.md`

For each line returned, replace `dayz-add-map` with `dayz-add-server`. Where the surrounding text says "test map" or "per-map", update to "test instance" / "per-instance". Specifically:

Find line 9:
```markdown
3. **`/dayz-add-map`**: sets up a test map under `workspace/_server/`: copies the mission template, creates the per-map `serverDZ.cfg` + `profiles/`. One-time per map.
```

Replace with:
```markdown
3. **`/dayz-add-server`**: sets up a test server instance under `.server/<instance>/`: copies the mission template, creates per-instance `serverDZ.cfg` + `server-profiles/` + `client-profiles/`. One-time per instance. Multiple variants of the same map allowed.
```

Find line 14:
```markdown
6. **`/dayz-clean-workspace`**: DayZ-only cleanup. Removes scaffolds and their deployed artifacts (workspace folders, `P:\<ModName>\` junctions that target our workspace, `P:\Mods\@<ModName>\` deploy dirs). Match-on-scaffold rule keeps your subscribed mods safe. `--include-server` also removes `workspace/_server/`.
```

Replace with:
```markdown
6. **`/dayz-clean-workspace`**: DayZ-only cleanup. Removes scaffolds and their deployed artifacts (workspace folders, `P:\<ModName>\` junctions that target our workspace, `P:\Mods\@<ModName>\` deploy dirs). Match-on-scaffold rule keeps your subscribed mods safe. `--include-server` also removes `.server/`.
```

- [ ] **Step 2: Replace the `python add_map.py` example invocation**

Find line 64:
```markdown
python .claude\skills\dayz-add-map\add_map.py chernarus
```

Replace with:
```markdown
python .claude\skills\dayz-add-server\add_server.py chernarus
```

Update the surrounding comment lines 62-63 if they mention "test map":
```
:: 3. Set up a test map (only the first time per map; copies mission template,
::    creates per-map serverDZ.cfg + profiles/)
```
to
```
:: 3. Set up a test server instance (one-time per instance; copies mission template,
::    creates per-instance serverDZ.cfg + profile dirs)
```

- [ ] **Step 3: Replace the `workspace/_server/` references in the launch flow steps**

Find lines 211-215:
```markdown
4. **First-run only:** if `workspace/_server/missions/` is empty, copy missions from DayZ Server install's `mpmissions/` (resolved via `find_dayz_server`). After this initial copy, DayZ Server can be uninstalled; the workspace copy is the editable source.
5. Ensure `workspace/_server/maps/<map>/serverDZ.cfg` and `profiles/` exist for the selected map (default `chernarus`). Default cfg is written on first run; existing cfgs are preserved but `allowFilePatching = 1;` is auto-appended if missing.
6. Spawn the server: `DayZDiag_x64.exe -server -config=<map>/serverDZ.cfg -profiles=<map>/profiles -mission=<missions>/<template> -mod=@Mod1;@Mod2 -filePatching -port=<port>`. The `-mission=<absolute path>` flag pins the mission folder explicitly; the engine otherwise looks in the binary's local `mpmissions/`, which doesn't exist in the DayZ game install.
7. Wait 5 seconds for the server to start listening.
8. Spawn the client: `DayZDiag_x64.exe -profiles=workspace/_server/!ClientDiagLogs -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=<port> -filePatching`. **The client must be DayZ Diag, not retail**: retail `DayZ_x64.exe` blocks past the loading screen with `-filePatching`. The client `-profiles=` points at `workspace/_server/!ClientDiagLogs/` so all client-side diag artifacts (`Users/`, `DataCache/`, `BattlEye/`, RPT, script logs) get contained in that one folder.
```

Replace with:
```markdown
4. **First-run only:** the instance must have been added via `/dayz-add-server <instance>`, which copies the mission template from DayZ Server's `mpmissions/` into `.server/<instance>/mission/`. After this initial copy, DayZ Server can be uninstalled.
5. Verify `.server/<instance>/serverDZ.cfg` and `.server/<instance>/mission/` exist for the selected instance (default `chernarus`). Existing cfgs are preserved but `allowFilePatching = 1;` is auto-appended if missing.
6. Spawn the server: `DayZDiag_x64.exe -server -config=<instance>/serverDZ.cfg -profiles=<instance>/server-profiles -mission=<instance>/mission -mod=@Mod1;@Mod2 -filePatching -port=<port>`. The `-mission=<absolute path>` flag pins the mission folder explicitly.
7. Wait 5 seconds for the server to start listening.
8. Spawn the client: `DayZDiag_x64.exe -profiles=<instance>/client-profiles -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=<port> -filePatching`. **The client must be DayZ Diag, not retail**: retail `DayZ_x64.exe` blocks past the loading screen with `-filePatching`. The client `-profiles=` points at `.server/<instance>/client-profiles/` so all client-side diag artifacts get contained per-instance.
```

- [ ] **Step 4: Update the artifacts table**

Find lines 300-301:
```markdown
| `workspace/_server/missions/<template>/` | **Editable copies** of DayZ mission folders (`dayzOffline.chernarusplus`, etc.) | `/dayz-launch-test` first run (bootstrapped from DayZ Server install) |
| `workspace/_server/maps/<map>/` | Per-map `serverDZ.cfg` + `profiles/` (logs, BattlEye state). One folder per map you test on. | `/dayz-launch-test` first run for each map |
```

Replace with:
```markdown
| `.server/<instance>/mission/` | **Editable copy** of a DayZ mission folder (one per instance). | `/dayz-add-server` (bootstrapped from DayZ Server install) |
| `.server/<instance>/serverDZ.cfg` | Per-instance server config. Tunable. | `/dayz-add-server` (default written on first add; preserved thereafter) |
| `.server/<instance>/server-profiles/` | Server-side logs and BattlEye state. | `/dayz-add-server` (created empty); populated by `/dayz-launch-test` |
| `.server/<instance>/client-profiles/` | Client-side logs, player profile, BattlEye state. | `/dayz-add-server` (created empty); populated by `/dayz-launch-test` |
```

- [ ] **Step 5: Update line 305 (gitignore note)**

Find:
```markdown
The `_server-profile/` folder is preserved across runs so logs accumulate and your `serverDZ.cfg` edits stick. If you want it gitignored in your project, add `workspace/_server/` to `.gitignore`: the skill leaves that decision to you.
```

Replace with:
```markdown
`.server/` is gitignored by default except for `serverDZ.cfg` and `mission/` contents (so your tuned configs and mission edits stay in version control while logs and profiles do not). Override the gitignore in your clone if you want different behavior.
```

- [ ] **Step 6: Update lines 380-383 (mission troubleshooting)**

Find:
```markdown
- `workspace/_server/missions/<template>/` exists (default chernarus → `dayzOffline.chernarusplus`).
- That folder has an `init.c` with a proper `main()` function.

`/dayz-launch-test` passes `-mission=<absolute path to workspace/_server/missions/<template>>` so the engine doesn't look in the wrong `mpmissions/` location. If the workspace mission copy got corrupted or partially deleted, remove the affected folder and re-run the skill; it'll re-copy from DayZ Server install.
```

Replace with:
```markdown
- `.server/<instance>/mission/` exists (default chernarus instance is created by `/dayz-add-server chernarus`).
- That folder has an `init.c` with a proper `main()` function.

`/dayz-launch-test` passes `-mission=<absolute path to .server/<instance>/mission>` so the engine doesn't look in the wrong `mpmissions/` location. If the mission copy got corrupted or partially deleted, run `/dayz-add-server <instance> --refresh-mission` to re-copy from DayZ Server install.
```

- [ ] **Step 7: Verify no stale references**

Run: `Grep "dayz-add-map\|workspace/_server\|!ClientDiagLogs" docs/dayz-modding.md`
Expected: zero matches.

- [ ] **Step 8: Commit**

```bash
git add docs/dayz-modding.md
git commit -m "docs(dayz): rewrite server-runtime sections for .server/<instance>/ layout"
```

---

## Task 9: Update `docs/README.md`, root `README.md`, and rename helper script

**Files:**
- Modify: `docs/README.md`
- Modify: `README.md`
- Rename: `scripts/add-map.bat` to `scripts/add-server.bat`

- [ ] **Step 1: Find references in both READMEs**

Run: `Grep -n "dayz-add-map\|workspace/_server" docs/README.md README.md`

For each match, replace `dayz-add-map` with `dayz-add-server` and `workspace/_server/` with `.server/`. Adjust surrounding prose where needed (e.g. "test map" -> "test server instance", "per-map" -> "per-instance"). Be concise; do not invent new content beyond updating the path/name references.

- [ ] **Step 2: Rename the helper script**

```bash
git mv scripts/add-map.bat scripts/add-server.bat
```

- [ ] **Step 3: Update the bat file's contents**

Open `scripts/add-server.bat`. Replace its content with:

```bat
@echo off
REM Thin wrapper around the /dayz-add-server skill. Forwards all arguments.
REM See .claude\skills\dayz-add-server\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-add-server\add_server.py" %*
```

- [ ] **Step 4: Verify**

Run: `Grep "dayz-add-map\|workspace/_server" docs/README.md README.md scripts/add-server.bat`
Expected: zero matches.

- [ ] **Step 5: Commit**

```bash
git add docs/README.md README.md scripts/add-server.bat
git commit -m "docs(readme): point examples at /dayz-add-server and .server/"
```

---

## Task 10: Add `.gitignore` rule for `.server/`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Read current `.gitignore`**

Run: `Read .gitignore`

- [ ] **Step 2: Append the `.server/` block**

Append the following block at the end of `.gitignore` (preserve all existing content):

```gitignore

# DayZ test-server runtime (.server/<instance>/). Logs, profiles, and storage are
# runtime junk and should not be tracked. User-edited serverDZ.cfg and mission/
# contents stay tracked via negation patterns.
.server/*/
!.server/*/serverDZ.cfg
!.server/*/mission/
!.server/*/mission/**
```

- [ ] **Step 3: Verify the patterns work**

Run: `git check-ignore -v .server/test/server-profiles/foo.log .server/test/serverDZ.cfg .server/test/mission/init.c 2>&1 || true`
Expected behavior:
- `.server/test/server-profiles/foo.log` is ignored (matched by `.server/*/`)
- `.server/test/serverDZ.cfg` is NOT ignored (negated by `!.server/*/serverDZ.cfg`)
- `.server/test/mission/init.c` is NOT ignored (negated by `!.server/*/mission/**`)

If git outputs different behavior, double-check the negation patterns match exactly as shown above.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore(gitignore): ignore .server/ runtime, track serverDZ.cfg and mission/ edits"
```

---

## Task 11: Delete the old `dayz-add-map` skill folder

**Files:**
- Delete: `.claude/skills/dayz-add-map/SKILL.md`
- Delete: `.claude/skills/dayz-add-map/add_map.py`
- Delete: `.claude/skills/dayz-add-map/__pycache__/` (if exists)

- [ ] **Step 1: Remove the skill folder**

```bash
git rm -r .claude/skills/dayz-add-map
```

If pycache is not tracked (it shouldn't be), the `git rm -r` will only delete tracked files. Manually clean any leftover untracked pycache:

Run: `Bash rm -rf .claude/skills/dayz-add-map`

- [ ] **Step 2: Verify removal**

Run: `Glob .claude/skills/dayz-add-map/**`
Expected: zero matches.

- [ ] **Step 3: Final stale-reference sweep across the repo**

Run: `Grep "dayz-add-map\|add_map.py" --output_mode files_with_matches`
Expected: matches only inside `wiki/docs/...` (regenerated by docs-sync) and possibly inside this plan file or the spec file. No matches in skill code, plugin manifest, L1 docs, or live docs/ files.

If any unexpected matches appear, fix them by hand and append to the relevant prior commit (or make a small follow-up commit).

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(dayz): remove deprecated dayz-add-map skill"
```

---

## Task 12: Sync skills and wiki

**Files:**
- Run external scripts; touches per-user agent home dirs and `wiki/docs/`.

- [ ] **Step 1: Sync skills into agent home dirs**

Run: `python .claude\skills\sync-skills\sync.py`
Expected: Confirms the renamed/new skill folders are linked into `$HOME/.claude/skills/`, `$HOME/.codex/skills/`, `$HOME/.gemini/skills/`. Old `dayz-add-map` is pruned.

- [ ] **Step 2: Sync wiki**

Invoke the docs-wiki-sync agent (or run `/docs-sync`) to regenerate the Docusaurus mirror under `wiki/docs/`. The agent will detect:
- `wiki/docs/skills/dayz-add-map.md` is orphaned (delete)
- `wiki/docs/skills/dayz-add-server.md` is missing (create)
- `wiki/docs/skills/dayz-migrate-server.md` is missing (create)
- `wiki/docs/skills/dayz-launch-test.md`, `wiki/docs/skills/dayz-clean-workspace.md`, `wiki/docs/dayz-conventions.md`, `wiki/docs/dayz-modding.md`, `wiki/docs/intro.mdx` drifted (update)

- [ ] **Step 3: Verify wiki state**

Run: `Glob wiki/docs/skills/dayz-*.md`
Expected: includes `dayz-add-server.md` and `dayz-migrate-server.md`; does NOT include `dayz-add-map.md`.

- [ ] **Step 4: Commit**

```bash
git add wiki/
git commit -m "docs(wiki): regenerate Docusaurus mirror after server-instance refactor"
```

---

## Task 13: End-to-end manual verification

**Files:**
- No code changes. Runs the new skills against the user's real DayZ install and inspects filesystem state.

This task is the practical equivalent of an integration test. It must pass before merging.

- [ ] **Step 1: Verify the legacy folder still exists (precondition for the migration test)**

Run: `Bash test -d workspace/_server && echo "legacy present" || echo "legacy absent"`
Expected: `legacy present`. (If absent, you're testing on a clean checkout; skip the migration step and start at Step 4.)

- [ ] **Step 2: Run a dry-run migration**

Run: `python .claude\skills\dayz-migrate-server\migrate.py --dry-run`
Expected: prints a plan showing one or more `workspace\_server\maps\<map>` -> `.server\<instance>` mappings. Exit 0. No filesystem changes.

- [ ] **Step 3: Run the real migration**

Run: `python .claude\skills\dayz-migrate-server\migrate.py`
Expected:
- `.server/<instance>/mission/`, `serverDZ.cfg`, `server-profiles/`, `client-profiles/` all present for each migrated instance.
- Original `workspace/_server/` is untouched (mission folders, !ClientDiagLogs/, maps/<map>/serverDZ.cfg are gone since they were moved, but the empty `workspace/_server/` directory shell is left intact).
- Console prints the "delete legacy folder manually" hint.

Run: `Glob .server/**/serverDZ.cfg` and `Glob .server/**/mission/init.c`
Expected: at least one of each.

- [ ] **Step 4: Verify the legacy gates fire correctly**

While `workspace/_server/` is still on disk, run:
- `python .claude\skills\dayz-add-server\add_server.py chernarus-test`
- `python .claude\skills\dayz-launch-test\launch.py SomeMod --dry-run`
- `python .claude\skills\dayz-clean-workspace\clean.py --include-server --dry-run`

Each should fail with `[FAIL]` and the migration hint. Exit non-zero.

- [ ] **Step 5: Delete the legacy folder manually**

Run: `Bash rm -rf workspace/_server`

- [ ] **Step 6: Test fresh `add-server`**

Run: `python .claude\skills\dayz-add-server\add_server.py chernarus-hardcore --map chernarus`
Expected:
- Creates `.server/chernarus-hardcore/{mission,serverDZ.cfg,server-profiles,client-profiles}`
- Mission is the chernarus template
- serverDZ.cfg has `template = "dayzOffline.chernarusplus"` and `allowFilePatching = 1;`

- [ ] **Step 7: Test launch (dry-run)**

Run: `python .claude\skills\dayz-launch-test\launch.py SomeMod --server chernarus-hardcore --dry-run`
(Substitute `SomeMod` with a mod that's actually built on this machine, or accept the failure at the built-mod check; the goal here is to confirm the path-resolution and arg-construction logic.)

If a built mod is available, expected: prints server cmd and client cmd referencing `.server/chernarus-hardcore/` paths. Exit 0. No processes spawned.

- [ ] **Step 8: Test clean (dry-run)**

Run: `python .claude\skills\dayz-clean-workspace\clean.py --include-server --dry-run`
Expected: lists `.server` as a "server staging" entry to be removed. Exit 0. No filesystem changes.

- [ ] **Step 9: Final repo grep for stale references**

Run: `Grep "dayz-add-map\|workspace/_server\|!ClientDiagLogs" --output_mode files_with_matches`
Expected matches: only inside `docs/superpowers/` (this plan file and the spec file reference the old names by design, since they describe the migration). No matches in live skill code, L1 docs, plugin manifest, conventions, README, or wiki.

If any unexpected matches appear, fix and amend the relevant commit, OR make a follow-up cleanup commit.

- [ ] **Step 10: Push and open PR**

```bash
git push -u origin feature/server-instance-layout
gh pr create --base develop --title "feat(dayz): server-instance layout under .server/" --body "$(cat <<'EOF'
## Summary
- Moves DayZ test-server runtime from `workspace/_server/` to `.server/<instance>/`
- Identifies test environments by free-form instance name, not map name (multiple variants of the same map supported)
- Per-instance isolation: each instance owns its mission copy, server config, server logs, and client logs
- Renames `/dayz-add-map` to `/dayz-add-server`; renames `--map` flag to `--server` on `/dayz-launch-test`
- Adds `/dayz-migrate-server` for one-shot migration; old runtime skills refuse while legacy layout exists
- Opinionated `.gitignore` default: ignores `.server/*/` runtime junk, tracks `serverDZ.cfg` and `mission/`

Spec: `docs/superpowers/specs/2026-05-06-server-instance-layout-design.md`
Plan: `docs/superpowers/plans/2026-05-06-server-instance-layout.md`

## Test plan
- [x] `/dayz-migrate-server --dry-run` shows expected plan
- [x] `/dayz-migrate-server` produces correct `.server/<instance>/` layout
- [x] All three runtime skills refuse while `workspace/_server/` exists
- [x] `/dayz-add-server <new-instance> --map chernarus` creates a fresh instance
- [x] `/dayz-launch-test <Mod> --server <instance> --dry-run` resolves `.server/<instance>/` paths correctly
- [x] `/dayz-clean-workspace --include-server --dry-run` lists `.server/` for removal
- [x] No stale references to `dayz-add-map` or `workspace/_server/` outside spec/plan/wiki

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

**Spec coverage:** Walking through the spec sections:
- Final layout (`.server/<instance>/{mission, serverDZ.cfg, server-profiles, client-profiles}`); Tasks 1, 2, 3, 4 implement.
- Skill rename `dayz-add-map` to `dayz-add-server`: Task 1 creates the new skill, Task 11 deletes the old.
- Launch flag rename `--map` to `--server`: Task 3.
- Clean-workspace target update; Task 4.
- New `dayz-migrate-server`: Task 2.
- Plugin manifest; Task 5.
- L1 docs; Task 7.
- Shared conventions; Task 6.
- `docs/dayz-modding.md`: Task 8.
- README, helper script; Task 9.
- Gitignore; Task 10.
- Wiki regen; Task 12.
- End-to-end verification; Task 13.

All spec items have tasks.

**Placeholder scan:** No "TBD", "TODO", "implement later", "appropriate error handling", "similar to Task N", or other placeholders. Every code change includes the actual code. Every command includes the actual command.

**Type / signature consistency:**
- `verify_instance_environment(instance: str)` returns 4-tuple `(cfg_path, server_profile_dir, mission_path, client_profile_dir)` in Task 3 Step 4; Task 3 Step 5 unpacks four values from it. Match.
- Task 5 says skill count `23` -> `24`. Verify: existing manifest lists 23 skill paths. After this work: -1 (dayz-add-map removed) +2 (add-server, migrate-server) = 24. Match.
- Task 1's `add_server.py` defines `gate_on_old_layout`. Task 3's `launch.py` defines its own `gate_on_old_layout` (separate file scope, same name, same body). Both call sites match. OK.
- `KNOWN_MAPS` table is identical in `add_server.py` and `launch.py`. Same as today's `add_map.py` / `launch.py` pair. OK.
