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

# REPO_ROOT = where this skill ships from. PROJECT_DIR = user's project.
REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
WORKSPACE = PROJECT_DIR / "workspace"
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
SERVER_ROOT = PROJECT_DIR / ".server"
LEGACY_SERVER_ROOT = WORKSPACE / "_server"

# Ownership marker written by dayz-build-pbo at P:\Mods\@<ModName>\<MARKER>.
# The deployed dir is removed only when this file exists AND its content
# matches the modname - this is what makes us safe against name collisions
# with subscribed mods or anything else the user dropped under !Workshop.
SCAFFOLD_MARKER = ".agentic-z-scaffold"

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
    """Folder is a managed mod if EITHER:
      - it's a real directory with config.cpp + $PBOPREFIX$ (native /dayz-new-mod scaffold), OR
      - it's a directory link (symlink/junction) under workspace/ - those only get
        created by /dayz-new-mod or /dayz-import-mod, so the link itself is the
        ownership marker. This covers bare imports where the user opted out of
        scaffolding (--no-scaffold) and the linked source has neither file.
    """
    if not path.is_dir():
        return False
    if _is_link(path):
        return True
    return (path / "config.cpp").exists() and (path / "$PBOPREFIX$").exists()


def _is_link(path: Path) -> bool:
    """True if path is a symlink OR a Windows junction (NTFS reparse point).

    Critical for safe removal: shutil.rmtree on a junction recurses into the
    target and would destroy an imported mod's external source folder.
    os.path.islink is True for symlinks but False for junctions, so we also
    check the reparse-point attribute via os.lstat on Windows.
    """
    if os.path.islink(path):
        return True
    if os.name == "nt":
        try:
            st = os.lstat(path)
        except OSError:
            return False
        # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)
    return False


def _resolve_link_target(path: Path) -> Path | None:
    """Return the link target (without \\\\?\\ prefix) or None if not a link."""
    try:
        target = os.readlink(path)
    except OSError:
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return Path(target)


def discover_mods(target: str | None) -> list[Path]:
    if not WORKSPACE.exists():
        return []
    if target:
        path = WORKSPACE / target
        if not is_scaffolded_mod(path):
            sys.exit(
                f"{FAIL} {path.relative_to(PROJECT_DIR)} is not a scaffolded mod "
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


def deployed_owned_by_us(deployed: Path, modname: str) -> bool:
    """The deployed dir is ours iff it contains the scaffold marker file with
    matching content. This protects against name collisions: a subscribed mod
    or hand-placed @<X> folder under !Workshop has no marker and stays put.
    """
    marker = deployed / SCAFFOLD_MARKER
    if not marker.is_file():
        return False
    try:
        return marker.read_text(encoding="utf-8").strip() == modname
    except OSError:
        return False


def find_artifacts(mod_path: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    """Order matters: junction first (so it's broken before workspace removal),
    then deployed dir, then workspace dir last.

    Returns (plan, warnings). Warnings flag artifacts we deliberately skipped
    so the user can act on them manually.
    """
    artifacts: list[tuple[str, Path]] = []
    warnings: list[str] = []
    name = mod_path.name

    p_junction = P_DRIVE / name
    if os.path.lexists(p_junction) and junction_targets_workspace(p_junction, mod_path):
        artifacts.append(("junction", p_junction))

    deployed = MODS_ROOT / f"@{name}"
    if deployed.exists():
        if deployed_owned_by_us(deployed, name):
            artifacts.append(("deployed", deployed))
        else:
            warnings.append(
                f"P:\\Mods\\@{name}\\ exists but has no Agentic-Z ownership marker\n"
                f"        ({SCAFFOLD_MARKER} missing or content mismatch).\n"
                "        Skipping - could be a subscribed mod or hand-placed folder.\n"
                f"        If it's actually yours, remove manually: cmd /c rmdir /s /q P:\\Mods\\@{name}"
            )

    if _is_link(mod_path):
        artifacts.append(("workspace-link", mod_path))
    else:
        artifacts.append(("workspace", mod_path))
    return artifacts, warnings


def remove_artifact(kind: str, path: Path, dry_run: bool) -> None:
    try:
        rel = path.relative_to(PROJECT_DIR)
    except ValueError:
        rel = path

    if dry_run:
        print(f"{OK} would remove ({kind}): {rel}")
        return

    if kind in ("junction", "workspace-link"):
        # Critical: never recurse into a link's target. shutil.rmtree on a
        # Windows junction would walk the target and delete an imported mod's
        # external source folder. cmd /c rmdir removes the link itself.
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
    warnings: list[str] = []
    for mod in mods:
        mod_plan, mod_warnings = find_artifacts(mod)
        plan.extend(mod_plan)
        warnings.extend(mod_warnings)
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

    for warning in warnings:
        print(f"{WARN} {warning}")
    if warnings:
        print()

    if not plan:
        print(f"{OK} Nothing to clean.")
        return 0

    print(f"Plan: {len(plan)} item(s) to remove")
    for kind, path in plan:
        try:
            rel = path.relative_to(PROJECT_DIR)
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
