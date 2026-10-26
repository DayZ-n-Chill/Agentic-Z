"""dayz-init Step 1: setup-complete check.

Prints the project root when this clone has an active mod recorded by
/dayz-init that still exists under workspace/; prints nothing otherwise.
Always exits 0.

Usage:
    python skills/dayz-init/check_setup.py
"""
from state import PROJECT_DIR, cached_project_root, is_setup_complete


def main() -> int:
    project = cached_project_root()
    if project is not None and project.resolve() == PROJECT_DIR and is_setup_complete(project):
        print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
