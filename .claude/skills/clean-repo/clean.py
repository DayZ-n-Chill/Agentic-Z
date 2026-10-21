"""clean-repo: remove all template-managed artifacts before pushing changes.

Orchestrator. Discovers every `<domain>-clean-workspace` skill under
.claude/skills/, runs each one's clean.py with --include-server --dry-run to
build a combined plan, asks for confirmation, then runs each with
--include-server --yes.

Each domain owns its own cleanup logic; this skill just runs them all.

Maintainer rules: keep domain-specific knowledge out of this file (it belongs
in each <domain>-clean-workspace skill), and pass children nothing beyond
--include-server plus --dry-run or --yes, the contract every child accepts.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

OK = "[OK]   "
FAIL = "[FAIL] "


def find_cleanup_skills(skills_dir: Path | None = None) -> list[Path]:
    """Return every <domain>-clean-workspace skill folder containing a clean.py.

    Folders starting with `_` (like _shared/) are skipped: they're helpers,
    not skills.
    """
    root = skills_dir or SKILLS_DIR
    return [
        child
        for child in sorted(root.iterdir())
        if child.is_dir()
        and not child.name.startswith("_")
        and child.name.endswith("-clean-workspace")
        and (child / "clean.py").is_file()
    ]


def confirm(prompt: str = "Proceed? [y/N]: ") -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def run_children(skills: list[Path], mode_flag: str) -> list[str]:
    """Run each skill's clean.py with --include-server <mode_flag>. Return names that failed."""
    failed: list[str] = []
    for skill in skills:
        print()
        print(f"=== /{skill.name} ({mode_flag}) ===")
        sys.stdout.flush()
        cmd = [sys.executable, str(skill / "clean.py"), "--include-server", mode_flag]
        if subprocess.run(cmd).returncode != 0:
            failed.append(skill.name)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove all template-managed artifacts across every domain."
    )
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the combined plan (each domain cleanup with --dry-run) and stop.",
    )
    args = parser.parse_args(argv)

    if not args.dry_run and not args.yes and not sys.stdin.isatty():
        print(f"{FAIL} Refusing to proceed without --yes when stdin is not a TTY.", file=sys.stderr)
        return 2

    skills = find_cleanup_skills()
    if not skills:
        print(f"{OK} No domain cleanup skills found.")
        return 0

    print(f"Plan from {len(skills)} cleanup skill(s): {', '.join('/' + s.name for s in skills)}")
    failed = run_children(skills, "--dry-run")
    print()
    if failed:
        print(f"{FAIL} Dry run failed for: {', '.join(failed)}. Nothing was removed.", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"{OK} Dry run complete. Nothing was removed.")
        return 0

    if not args.yes and not confirm("Remove everything listed above? [y/N]: "):
        print("Aborted. Nothing was removed.")
        return 0

    failed = run_children(skills, "--yes")
    print()
    if failed:
        print(f"{FAIL} {len(failed)} cleanup skill(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"{OK} All cleanup skills completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
