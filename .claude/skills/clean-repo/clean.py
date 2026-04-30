"""clean-repo: Wipe all template-managed artifacts before pushing changes.

Orchestrator — discovers every `<domain>-clean-workspace` skill under
.claude/skills/ and invokes its clean.py with --include-server --yes
(or --dry-run if this script was invoked with --dry-run).

Each domain owns its own cleanup logic; this skill just runs them all.

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
WARN = "[WARN] "
FAIL = "[FAIL] "


def find_cleanup_skills() -> list[Path]:
    """Return every <domain>-clean-workspace skill folder containing a clean.py.

    Folders starting with `_` (like _shared/) are skipped — they're helpers,
    not skills.
    """
    cleanups: list[Path] = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue
        if not child.name.endswith("-clean-workspace"):
            continue
        if not (child / "clean.py").is_file():
            continue
        cleanups.append(child)
    return cleanups


def confirm(prompt: str = "Proceed? [y/N]: ") -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wipe all template-managed artifacts across every domain."
    )
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run each domain cleanup with --dry-run (lists without removing).",
    )
    args = parser.parse_args()

    skills = find_cleanup_skills()
    if not skills:
        print(f"{OK} No domain cleanup skills found.")
        return 0

    print(f"Will run {len(skills)} cleanup skill(s):")
    for skill in skills:
        print(f"  /{skill.name}")
    print()

    if not args.dry_run and not args.yes:
        if not sys.stdin.isatty():
            sys.exit(f"{FAIL} Refusing to proceed without --yes when stdin is not a TTY.")
        if not confirm():
            print("Aborted.")
            return 0

    failed: list[str] = []
    for skill in skills:
        clean_script = skill / "clean.py"
        cmd = [sys.executable, str(clean_script), "--include-server"]
        cmd.append("--dry-run" if args.dry_run else "--yes")

        print()
        print(f"=== /{skill.name} ===")
        sys.stdout.flush()
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failed.append(skill.name)

    print()
    if failed:
        print(f"{FAIL} {len(failed)} skill(s) failed: {', '.join(failed)}")
        return 1
    print(f"{OK} All cleanup skills completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
