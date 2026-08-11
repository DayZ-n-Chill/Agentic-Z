"""dayz-init Step 5: persist wizard state after a successful setup run.

Caches the project root at ~/.claude/local-memory/dayz-current-project.txt
and writes <project>/.agentic-z/state.json with the intent choices.

Usage:
    python .claude/skills/dayz-init/save_state.py <project_path> \
        --rag skip|paste|pull --mod-name MyMod --is-new true|false --server-map chernarus
"""
import argparse
from pathlib import Path

from state import write_cached_project_root, write_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Write /dayz-init state")
    parser.add_argument("project_path", help="Project root (the mod folder)")
    parser.add_argument("--rag", default="skip", help="RAG choice: skip | paste | pull")
    parser.add_argument("--mod-name", required=True, help="Mod name")
    parser.add_argument(
        "--is-new",
        choices=("true", "false"),
        default="true",
        help="true if scaffolded fresh, false if imported",
    )
    parser.add_argument("--server-map", default="", help="Server map alias (empty if no server)")
    args = parser.parse_args()

    project = Path(args.project_path).resolve()
    write_cached_project_root(project)
    write_state(
        project,
        {
            "rag_choice": args.rag,
            "last_intent": {
                "mod_name": args.mod_name,
                "is_new": args.is_new == "true",
                "server_map": args.server_map,
            },
        },
    )
    print(f"[OK]    State written: {project / '.agentic-z' / 'state.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
