"""dayz-init Step 2: environment check.

Prints one line per issue:
    HARD <name> <message> [<fix_link>]   - user must act; stop the wizard
    AUTO <name> <message>                - fixable automatically; add to plan
Prints OK when there are no issues. Always exits 0 (warnings are not errors).

Usage:
    python .claude/skills/dayz-init/check_env.py
"""
from env_check import classify, run_all


def main() -> int:
    issues = run_all()
    auto, hard = classify(issues)
    for issue in hard:
        print("HARD", issue.name, issue.message, issue.fix_link or "")
    for issue in auto:
        print("AUTO", issue.name, issue.message)
    if not issues:
        print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
