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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.getcwd()).resolve()
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
    print(f"{OK} Project: {PROJECT_DIR}")

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
