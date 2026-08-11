"""dayz-init Step 1: setup-complete check.

Prints the cached project root if it exists and looks fully set up
(scaffolded mod + state file); prints nothing otherwise. Always exits 0.

Usage:
    python .claude/skills/dayz-init/check_setup.py
"""
from state import cached_project_root, is_setup_complete


def main() -> int:
    project = cached_project_root()
    if project and is_setup_complete(project):
        print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
