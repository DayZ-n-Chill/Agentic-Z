"""Entry point for /dayz-init.

First run: setup wizard (env -> intent -> plan -> execute -> hub).
Subsequent runs: hub mode (added in Task 12).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from detect import cwd  # noqa: E402
from env_check import run_all, classify, Severity  # noqa: E402
from intent import gather_intent  # noqa: E402
from plan import build_steps, render_plan, execute  # noqa: E402
from prompts import ask_yes_no  # noqa: E402
from state import (  # noqa: E402
    cached_project_root,
    is_setup_complete,
    write_state,
)


def run_wizard() -> int:
    print("/dayz-init")
    print()
    print("── Environment ──")
    issues = run_all()
    autofix, hard_stop = classify(issues)

    if hard_stop:
        print("\nCan't proceed. Need to fix:\n")
        for issue in hard_stop:
            print(f"  • {issue.message}")
            if issue.fix_link:
                print(f"    {issue.fix_link}")
        print("\nWhen done, re-run: /dayz-init")
        print("(I'll pick up where I left off.)")
        return 2

    if not issues:
        print("✓ Environment ready.")
    else:
        for issue in autofix:
            print(f"! {issue.message}")

    intent = gather_intent()
    steps = build_steps(intent, autofix)

    print()
    print(render_plan(steps))
    print()
    if not ask_yes_no("Continue?", default=True):
        print("Aborted. Re-run /dayz-init when ready.")
        return 1

    print("\n── Execute ──")
    failed_at = execute(steps)
    if failed_at:
        print(f"\nStopped at step {failed_at}/{len(steps)}.")
        print("Re-run /dayz-init to drop into the hub and retry.")
        return 1

    write_state(
        intent.project_path,
        {
            "rag_choice": intent.rag_choice,
            "last_intent": {
                "mod_name": intent.mod_name,
                "is_new": intent.is_new,
                "server_map": intent.server_map,
            },
        },
    )

    print("\n✓ Setup complete.")
    print("(Hub mode arrives in Task 12. For now, re-run /dayz-init.)")
    return 0


def main(argv: list[str] | None = None) -> int:
    project = cached_project_root()
    if project is not None and is_setup_complete(project):
        # Hub mode arrives in Task 12. For now, message and exit.
        print(f"Project '{project.name}' is set up. Hub mode coming in Task 12.")
        return 0
    return run_wizard()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
