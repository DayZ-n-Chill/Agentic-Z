"""dayz-clean-workspace: Remove DayZ scaffolds and their deployed artifacts.

The project is the one cached by /dayz-init (same as build and deploy). For each
managed mod under <project>/workspace/<ModName>/ (a /dayz-import-mod link, or a
real folder without .git that P:\\<ModName>\\ links to or whose deployed dir
carries the ownership marker; see unmanaged_reason):
  - workspace/<ModName>/     a real folder is emptied first and removed last; a link
                             is removed last without touching the source it points at
  - P:\\Mods\\@<ModName>\\     removed only if its ownership marker matches <ModName>
                             (the marker goes last)
  - P:\\<ModName>\\           removed only if it is a link whose target is workspace/<ModName>/

The order keeps the proof of ownership (the P:\\ junction and the marker) until
everything that can be held open is gone, so a run stopped by a locked file can
be rerun and finish. It also refuses while DayZDiag_x64.exe or workbenchApp.exe
is running, since those hold files in exactly these folders.

Mods without a workspace entry (subscribed or hand-placed under !Workshop) are
never touched. The ownership rules live in .claude/skills/_shared/skill_helpers.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL

# /dayz-new-mod owns the mod-name rule; build and deploy use the same check.
_nm = h.load_module("dayz_new_mod_module", h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py")


# Where /dayz-health keeps each mod's gate results (.server/!Health/<ModName>/).
HEALTH_DIR = Path(".server") / "!Health"

# Processes that keep files open in the folders this removes: the test server
# and client from /dayz-launch-test, and Workbench from /dayz-launch-workbench.
BLOCKING_EXES = ("DayZDiag_x64.exe", "workbenchApp.exe")


def has_junction_to(path: Path) -> bool:
    """True when P:\\<Name>\\ is a link pointing at this workspace folder (made by /dayz-new-mod)."""
    target = h.link_target(P_DRIVE / path.name)
    return target is not None and h.paths_equal(target, path)


def is_dir_link(path: Path) -> bool:
    """True for a directory symlink or junction, including a broken one.

    A link whose target was moved or deleted reports is_dir() False, so the
    link's own directory attribute (from lstat) decides on Windows. A file
    symlink is not a directory link: rmdir cannot remove it.
    """
    if not h.is_link(path):
        return False
    attrs = getattr(os.lstat(path), "st_file_attributes", None)
    if attrs is not None:
        return bool(attrs & 0x10)  # FILE_ATTRIBUTE_DIRECTORY on the link itself
    return path.is_dir() or not path.exists()


def unmanaged_reason(path: Path) -> str | None:
    """None when the workspace entry is managed (safe to remove), else why it is not.

    Managed means one of:
      - a directory link (symlink/junction), even one whose target is gone:
        only /dayz-import-mod creates links under workspace/, and removing one
        never touches its target.
      - a real directory with no .git inside that the toolkit demonstrably
        created: P:\\<Name>\\ is a junction to it (/dayz-new-mod), or
        P:\\Mods\\@<Name>\\ carries the ownership marker for <Name>
        (/dayz-build-pbo or /dayz-deploy-pbo).
    config.cpp + $PBOPREFIX$ alone are not proof: a hand-placed mod has them too.
    """
    # Before is_dir(): a broken imported link is not a folder any more, but its
    # link, P:\\<Name> junction and deploy folder must still be removable.
    if is_dir_link(path):
        return None
    if not path.is_dir():
        return "not a folder"
    if (path / ".git").exists():
        return "it contains .git (a repository; its history would be lost)"
    if has_junction_to(path) or h.owns_deploy_dir(MODS_ROOT / f"@{path.name}", path.name):
        return None
    return (
        f"no proof the toolkit created it (no P:\\{path.name} junction pointing at it\n"
        f"        and no ownership marker in P:\\Mods\\@{path.name})"
    )


def _manual_hint(path: Path) -> str:
    return f"If you are sure it can go, remove it by hand: cmd /c rmdir /s /q \"{path}\""


def discover_mods(workspace: Path, target: str | None) -> tuple[list[Path], list[str]]:
    """Return (managed mods, warnings for real mod folders that were skipped)."""
    if target is not None:
        path = workspace / target
        if not path.exists() and not h.is_link(path):
            sys.exit(
                f"{FAIL} workspace\\{target} not found, so there is nothing to clean.\n"
                "       Check the name (the folder name under workspace\\), or run without --mod\n"
                "       and with --dry-run to list every managed mod."
            )
        reason = unmanaged_reason(path)
        if reason is not None:
            sys.exit(
                f"{FAIL} workspace\\{target} is not a managed mod: {reason}.\n"
                "       Managed means an imported mod link, or a folder without .git that has a\n"
                "       P:\\<Name> junction to it or a P:\\Mods\\@<Name>\\ ownership marker.\n"
                f"       {_manual_hint(path)}"
            )
        return [path], []
    if not workspace.exists():
        return [], []
    mods: list[Path] = []
    warnings: list[str] = []
    for p in sorted(workspace.iterdir()):
        reason = unmanaged_reason(p)
        if reason is None:
            mods.append(p)
        elif p.is_dir() and (p / "config.cpp").exists():
            warnings.append(f"skipping workspace\\{p.name}: {reason}.\n        {_manual_hint(p)}")
    return mods, warnings


def find_artifacts(mod_path: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    """Return (plan, warnings) for one mod.

    Plan order matters. The proofs of ownership (the P:\\ junction and the
    deployed dir's marker) must outlive every step that a locked file can
    stop, or a rerun no longer sees the mod as managed. So a real workspace
    folder is emptied first (the step Workbench or DayZ most often blocks),
    then the deployed dir goes with its marker last, then the junction, and
    the now-empty workspace folder (or the imported link) goes last. Warnings
    name artifacts deliberately skipped so the user can act on them by hand.
    """
    artifacts: list[tuple[str, Path]] = []
    warnings: list[str] = []
    name = mod_path.name
    is_link = h.is_link(mod_path)

    if not is_link:
        artifacts.append(("workspace-files", mod_path))

    deployed = MODS_ROOT / f"@{name}"
    if deployed.exists():
        if h.owns_deploy_dir(deployed, name):
            artifacts.append(("deployed", deployed))
        else:
            warnings.append(
                f"{deployed}\\ exists but has no Agentic-Z ownership marker\n"
                f"        ({h.SCAFFOLD_MARKER} missing or content mismatch).\n"
                "        Skipping: it could be a subscribed mod or a hand-placed folder.\n"
                f"        If it is yours, remove it manually: cmd /c rmdir /s /q \"{deployed}\""
            )

    if has_junction_to(mod_path):
        artifacts.append(("junction", P_DRIVE / name))

    artifacts.append(("workspace-link" if is_link else "workspace", mod_path))
    return artifacts, warnings


def _remove_entry(path: Path) -> None:
    """Remove one file, folder or link; a link is removed without touching its target."""
    if h.is_link(path):
        try:
            os.rmdir(path)  # a directory symlink or junction: removes only the link
        except NotADirectoryError:
            path.unlink()  # a file symlink
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _clear_dir(path: Path, last: str | None = None) -> None:
    """Remove everything inside path, keeping the folder. The child named `last` goes after the rest."""
    for child in sorted(path.iterdir()):
        if child.name != last:
            _remove_entry(child)
    if last is not None and (path / last).exists():
        (path / last).unlink()


def remove_artifact(kind: str, path: Path) -> None:
    if kind in ("junction", "workspace-link"):
        # Never recurse into a link's target: shutil.rmtree on a Windows
        # junction walks into it and would delete an imported mod's external
        # source. cmd /c rmdir removes only the link.
        subprocess.run(["cmd", "/c", "rmdir", str(path)], check=True, capture_output=True, text=True)
    elif kind == "workspace-files":
        _clear_dir(path)
    elif kind == "workspace":
        path.rmdir()  # emptied by the workspace-files step that ran first
    elif kind == "deployed":
        # The marker goes last: if a locked .pbo stops this, the marker still
        # proves ownership and a rerun can finish.
        _clear_dir(path, last=h.SCAFFOLD_MARKER)
        path.rmdir()
    else:
        shutil.rmtree(path)


def running_blockers() -> list[str]:
    """The BLOCKING_EXES that are running now (tasklist, one query per name)."""
    found = []
    for exe in BLOCKING_EXES:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        ).stdout
        if f'"{exe.lower()}"' in out.lower():
            found.append(exe)
    return found


def _display(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


def confirm(prompt: str = "Proceed? [y/N]: ") -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove DayZ scaffolds and their deployed artifacts.")
    parser.add_argument("--mod", help="Target a specific mod by name (default: all managed mods).")
    parser.add_argument(
        "--include-server",
        action="store_true",
        help="Also remove .server/ at the project root (all instances, client logs and /dayz-health results).",
    )
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be removed without removing anything.",
    )
    args = parser.parse_args()
    if args.mod is not None:
        # Before anything touches disk: a name like ..\Other would reach outside workspace\.
        # Exits with "Invalid mod name" and the rule.
        _nm.validate_name(args.mod)

    project_dir = h.resolve_project_dir()
    h.gate_on_preflight()
    print()
    print(f"{OK} Project: {project_dir}")
    workspace = project_dir / "workspace"

    plan: list[tuple[str, Path]] = []
    mods, warnings = discover_mods(workspace, args.mod)
    for mod in mods:
        mod_plan, mod_warnings = find_artifacts(mod)
        # The mod's /dayz-health results go too, or /dayz-health --all keeps
        # listing a deleted mod. --include-server removes all of .server/ anyway.
        health = project_dir / HEALTH_DIR / mod.name
        # First, before any proof of ownership is touched.
        if health.is_dir() and not args.include_server:
            mod_plan.insert(0, ("health", health))
        plan.extend(mod_plan)
        warnings.extend(mod_warnings)

    if args.include_server:
        if (workspace / "_server").exists():
            sys.exit(
                f"{FAIL} Legacy layout detected at workspace\\_server.\n"
                "       --include-server targets .server/ at the project root. Delete the\n"
                "       legacy folder manually; that layout is no longer supported."
            )
        server_root = project_dir / ".server"
        if server_root.exists():
            plan.append(("server staging", server_root))

    for warning in warnings:
        print(f"{WARN} {warning}")
    if warnings:
        print()

    if not plan:
        print(f"{OK} Nothing to clean.")
        return 0

    print(f"Plan: {len(plan)} item(s) to remove")
    for kind, path in plan:
        print(f"  ({kind}) {_display(path, project_dir)}")

    blockers = running_blockers()
    if blockers:
        blocked = (
            f"{', '.join(blockers)} is running and can hold files open in these folders.\n"
            "       Stop the test session with /dayz-stop-test and close Workbench, then rerun."
        )
        if not args.dry_run:
            sys.exit(f"{FAIL} {blocked}")
        print()
        print(f"{WARN} {blocked}")

    if args.dry_run:
        print()
        print("(--dry-run) nothing removed.")
        return 0

    if not args.yes:
        print()
        if not sys.stdin.isatty():
            sys.exit(f"{FAIL} Refusing to remove without --yes when stdin is not a TTY.")
        if not confirm():
            print("Aborted.")
            return 0

    print()
    for kind, path in plan:
        try:
            remove_artifact(kind, path)
        except (OSError, subprocess.CalledProcessError) as e:
            # rmdir's own message ("Access is denied." etc.) is in e.stderr.
            detail = (getattr(e, "stderr", "") or str(e)).strip()
            print(f"{FAIL} could not remove ({kind}) {path}: {detail}")
            return 1
        print(f"{OK} removed ({kind}): {_display(path, project_dir)}")

    print()
    print(f"{OK} Cleaned {len(plan)} item(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
