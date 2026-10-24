"""dayz-init Step 2: environment check (read-only).

Prints one line per issue, then exits:
    HARD <name> <message> [<fix_link>]   user must act
    AUTO <name> <message>                /dayz-init fixes it
    OK                                   nothing to do
Always exits 0; the agent reads the lines.

Usage:
    python .claude/skills/dayz-init/check_env.py
"""
from env_check import classify, run_all


def main() -> int:
    auto, hard = classify(run_all())
    for issue in hard:
        print("HARD", issue.name, issue.message, *([issue.fix_link] if issue.fix_link else []))
    for issue in auto:
        print("AUTO", issue.name, issue.message)
    if not (auto or hard):
        print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
