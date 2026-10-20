"""dayz-clean-workspace: Remove DayZ scaffolds and their deployed artifacts.

The project is the one cached by /dayz-init (same as build and deploy). For each
managed mod under <project>/workspace/<ModName>/ (a native scaffold with
config.cpp + $PBOPREFIX$, or a /dayz-import-mod link):
  - P:\\<ModName>\\           removed only if it is a link whose target is workspace/<ModName>/
  - P:\\Mods\\@<ModName>\\     removed only if its ownership marker matches <ModName>
  - workspace/<ModName>/     folder removed recursively; a link is removed without
                             touching the external source it points at

Mods without a workspace entry (subscribed or hand-placed under !Workshop) are
never touched. The ownership rules live in .claude/skills/_shared/skill_helpers.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL


def is_scaffolded_mod(path: Path) -> bool:
    """A workspace entry is managed if EITHER:
      - it is a directory link (symlink/junction): only /dayz-new-mod and
        /dayz-import-mod create links under workspace/, so the link itself is
        the ownership signal. Covers bare imports made with --no-scaffold.
      - it is a real directory with config.cpp + $PBOPREFIX$ (native scaffold).
    """
    if not path.is_dir():
        return False
    if h.is_link(path):
        return True
    return (path / "config.cpp").exists() and (path / "$PBOPREFIX$").exists()


def discover_mods(workspace: Path, target: str | None) -> list[Path]:
    if target:
        path = workspace / target
        if not is_scaffolded_mod(path):
            sys.exit(
                f"{FAIL} workspace\\{target} is not a managed mod.\n"
                "       Expected an imported mod link, or a folder with config.cpp and $PBOPREFIX$."
            )
        return [path]
    if not workspace.exists():
        return []
    return sorted(p for p in workspace.iterdir() if is_scaffolded_mod(p))


def find_artifacts(mod_path: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    """Return (plan, warnings) for one mod.

    Plan order matters: the P:\\ junction is broken first, then the deployed
    dir, then the workspace entry last. Warnings name artifacts deliberately
    skipped so the user can act on them by hand.
    """
    artifacts: list[tuple[str, Path]] = []
    warnings: list[str] = []
    name = mod_path.name

    p_junction = P_DRIVE / name
    target = h.link_target(p_junction)
    if target is not None and h.paths_equal(target, mod_path):
        artifacts.append(("junction", p_junction))

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

    artifacts.append(("workspace-link" if h.is_link(mod_path) else "workspace", mod_path))
    return artifacts, warnings


def remove_artifact(kind: str, path: Path) -> None:
    if kind in ("junction", "workspace-link"):
        # Never recurse into a link's target: shutil.rmtree on a Windows
        # junction walks into it and would delete an imported mod's external
        # source. cmd /c rmdir removes only the link.
        subprocess.run(["cmd", "/c", "rmdir", str(path)], check=True, capture_output=True, text=True)
    else:
        shutil.rmtree(path)


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
        help="Also remove .server/ at the project root (all instances and client logs).",
    )
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be removed without removing anything.",
    )
    args = parser.parse_args()

    project_dir = h.resolve_project_dir()
    h.gate_on_preflight()
    print()
    print(f"{OK} Project: {project_dir}")
    workspace = project_dir / "workspace"

    plan: list[tuple[str, Path]] = []
    warnings: list[str] = []
    for mod in discover_mods(workspace, args.mod):
        mod_plan, mod_warnings = find_artifacts(mod)
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
            print(f"{FAIL} could not remove ({kind}) {path}: {e}")
            return 1
        print(f"{OK} removed ({kind}): {_display(path, project_dir)}")

    print()
    print(f"{OK} Cleaned {len(plan)} item(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
