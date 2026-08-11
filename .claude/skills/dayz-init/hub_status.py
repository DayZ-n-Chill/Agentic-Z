"""dayz-init Step 6: render the hub status block for a project.

Usage:
    python .claude/skills/dayz-init/hub_status.py <project_path>
"""
import argparse
import sys
from pathlib import Path

from hub import gather_status, render_status

# The status block uses Unicode box-drawing chars; Windows consoles default to
# cp1252, so force UTF-8 (mirrors what the other dayz skills print safely).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render /dayz-init hub status")
    parser.add_argument("project_path", help="Project root (the mod folder)")
    args = parser.parse_args()

    project = Path(args.project_path).resolve()
    if not project.is_dir():
        print(f"[FAIL]  Project path does not exist: {project}")
        return 1
    print(render_status(gather_status(project)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
