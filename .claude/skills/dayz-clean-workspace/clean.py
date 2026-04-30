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
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace"
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
SERVER_ROOT = WORKSPACE / "_server"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def is_scaffolded_mod(path: Path) -> bool:
    """Folder is a /dayz-new-mod scaffold iff it has config.cpp AND $PBOPREFIX$."""
    if not path.is_dir():
        return False
    return (path / "config.cpp").exists() and (path / "$PBOPREFIX$").exists()


def discover_mods(target: str | None) -> list[Path]:
    if not WORKSPACE.exists():
        return []
    if target:
        path = WORKSPACE / target
        if not is_scaffolded_mod(path):
            sys.exit(
                f"{FAIL} {path.relative_to(REPO_ROOT)} is not a scaffolded mod "
                "(missing config.cpp or $PBOPREFIX$)."
            )
        return [path]
    return sorted(p for p in WORKSPACE.iterdir() if is_scaffolded_mod(p))


def _normalize(p: Path) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def junction_targets_workspace(junction: Path, mod_path: Path) -> bool:
    try:
        target = os.readlink(junction)
    except OSError:
        return False
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return _normalize(Path(target)) == _normalize(mod_path)


def find_artifacts(mod_path: Path) -> list[tuple[str, Path]]:
    """Order matters: junction first (so it's broken before workspace removal),
    then deployed dir, then workspace dir last."""
    artifacts: list[tuple[str, Path]] = []
    name = mod_path.name

    p_junction = P_DRIVE / name
    if os.path.lexists(p_junction) and junction_targets_workspace(p_junction, mod_path):
        artifacts.append(("junction", p_junction))

    deployed = MODS_ROOT / f"@{name}"
    if deployed.exists():
        artifacts.append(("deployed", deployed))

    artifacts.append(("workspace", mod_path))
    return artifacts


def remove_artifact(kind: str, path: Path, dry_run: bool) -> None:
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path

    if dry_run:
        print(f"{OK} would remove ({kind}): {rel}")
        return

    if kind == "junction":
        subprocess.run(
            ["cmd", "/c", "rmdir", str(path)], check=True, capture_output=True, text=True
        )
    else:
        shutil.rmtree(path)
    print(f"{OK} removed ({kind}): {rel}")


def confirm(prompt: str = "Proceed? [y/N]: ") -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove DayZ scaffolds and their deployed artifacts.")
    parser.add_argument("--mod", help="Target a specific mod by name (default: all scaffolded mods).")
    parser.add_argument(
        "--include-server",
        action="store_true",
        help="Also remove workspace/_server/ (server staging dir).",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Skip the interactive confirmation prompt."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be removed without removing anything.",
    )
    args = parser.parse_args()

    gate_on_preflight()
    print()

    mods = discover_mods(args.mod)
    plan: list[tuple[str, Path]] = []
    for mod in mods:
        plan.extend(find_artifacts(mod))
    if args.include_server and SERVER_ROOT.exists():
        plan.append(("server staging", SERVER_ROOT))

    if not plan:
        print(f"{OK} Nothing to clean.")
        return 0

    print(f"Plan: {len(plan)} item(s) to remove")
    for kind, path in plan:
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            rel = path
        print(f"  ({kind}) {rel}")

    if args.dry_run:
        print()
        print("(--dry-run) nothing removed.")
        return 0

    if not args.yes:
        print()
        if not sys.stdin.isatty():
            sys.exit(
                f"{FAIL} Refusing to remove without --yes when stdin is not a TTY."
            )
        if not confirm():
            print("Aborted.")
            return 0

    print()
    for kind, path in plan:
        try:
            remove_artifact(kind, path, dry_run=False)
        except Exception as e:
            print(f"{FAIL} could not remove ({kind}) {path}: {e}")
            return 1

    print()
    print(f"{OK} Cleaned {len(plan)} item(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
