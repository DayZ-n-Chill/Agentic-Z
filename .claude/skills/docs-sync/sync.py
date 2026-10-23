"""Read-only drift check between the repository and the wiki.

The wiki in wiki/ is written by hand. This script never writes to it; it only
reports where the wiki and the repository disagree:

  - a skill folder under .claude/skills/ that the wiki's skills list
    (wiki/src/content/skills-table.md) does not name, or a skill the list names
    that has no folder;
  - an agent file under .claude/agents/ that the wiki's "All agents" table
    (wiki/src/content/guide.md) does not name, or an agent the table names that
    has no file;
  - a home page count (wiki/src/App.jsx STATS: agents, skills, hooks) that does
    not match the repository.

Modes:
  --check (default)  Print the report. Exits 1 when the wiki and the repo
                     disagree, so CI can gate on it.
  --check --quiet    How the Stop hook runs it: prints nothing when they agree,
                     else one {"systemMessage": ...} JSON line, the hook output
                     Claude Code shows the user. Always exits 0.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SKILLS_TABLE = Path("wiki/src/content/skills-table.md")
AGENTS_PAGE = Path("wiki/src/content/guide.md")
AGENTS_HEADING = "### All agents"
HOME_PAGE = Path("wiki/src/App.jsx")


def hook_notice(message: str) -> None:
    """Print a message for the Stop hook (--quiet) as hook JSON output.

    Claude Code sends a command hook's plain stdout on exit 0 to the debug log,
    not the transcript; a `systemMessage` field is what it shows the user.
    """
    print(json.dumps({"systemMessage": message}))


def repo_skills() -> set[str]:
    """Skill folders that hold a SKILL.md. Folders starting with _ are shared packs."""
    root = REPO_ROOT / ".claude" / "skills"
    if not root.is_dir():
        return set()
    return {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "SKILL.md").is_file()}


def repo_agents() -> set[str]:
    root = REPO_ROOT / ".claude" / "agents"
    if not root.is_dir():
        return set()
    return {p.stem for p in root.glob("*.md")}


def repo_hooks() -> set[str]:
    """Hook scripts in hooks/, leaving out their tests."""
    root = REPO_ROOT / "hooks"
    if not root.is_dir():
        return set()
    return {p.stem for p in root.glob("*.py") if not p.name.startswith("test_")}


def _first_cell(line: str) -> str:
    return line.split("|")[1] if line.count("|") >= 2 else ""


def wiki_skills() -> set[str] | None:
    """Skills named in the first column of the wiki's skills list, as `/name`."""
    path = REPO_ROOT / SKILLS_TABLE
    if not path.is_file():
        return None
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        names.update(re.findall(r"`/([a-z0-9-]+)`", _first_cell(line)))
    return names


def wiki_agents() -> set[str] | None:
    """Agents named in the first column of the "All agents" table, as `name`.

    One row can name several agents ("**Build checker and in-game tester**
    `dayz-build-checker` `dayz-ingame-tester`").
    """
    path = REPO_ROOT / AGENTS_PAGE
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(AGENTS_HEADING) + 1
    except ValueError:
        return None
    names: set[str] = set()
    for line in lines[start:]:
        if line.startswith("#"):
            break
        names.update(re.findall(r"`([a-z0-9-]+)`", _first_cell(line)))
    return names


def wiki_counts() -> dict[str, int]:
    """The home page counts from STATS in App.jsx, e.g. ['30', 'agents']."""
    path = REPO_ROOT / HOME_PAGE
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    return {label: int(n) for n, label in re.findall(r"\['(\d+)',\s*'(agents|skills|hooks)'\]", text)}


def detect_drift() -> list[str]:
    """Return one line per disagreement between the wiki and the repository."""
    problems: list[str] = []

    for kind, have, listed, where in (
        ("skill", repo_skills(), wiki_skills(), SKILLS_TABLE.as_posix()),
        ("agent", repo_agents(), wiki_agents(), f"{AGENTS_PAGE.as_posix()} ({AGENTS_HEADING[4:]})"),
    ):
        if listed is None:
            problems.append(f"Cannot find the wiki's {kind} list in {where}.")
            continue
        for name in sorted(have - listed):
            problems.append(f"The {kind} {name} is in the repo but not in {where}.")
        for name in sorted(listed - have):
            problems.append(f"{where} names the {kind} {name}, which is not in the repo.")

    actual = {"agents": len(repo_agents()), "skills": len(repo_skills()), "hooks": len(repo_hooks())}
    for label, n in sorted(wiki_counts().items()):
        if n != actual[label]:
            problems.append(f"{HOME_PAGE.as_posix()} says {n} {label}; the repo has {actual[label]}.")

    return problems


def report(problems: list[str], quiet: bool) -> int:
    """Print the report. Returns 1 when problems are found; --quiet always returns 0."""
    if not problems:
        if not quiet:
            print("docs-sync: the wiki matches the repo.")
        return 0

    if quiet:
        hook_notice(f"docs-sync: {len(problems)} place(s) where the wiki and the repo disagree. Run /docs-sync.")
        return 0

    print(f"docs-sync: {len(problems)} place(s) where the wiki and the repo disagree.")
    for line in problems:
        print(f"  - {line}")
    print()
    print("The wiki is written by hand. Fix it under wiki/src/, then run this check again.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report where the wiki and the repo disagree (default).")
    parser.add_argument("--quiet", action="store_true", help="Stop hook mode: JSON notice only, always exit 0.")
    args = parser.parse_args(argv)
    return report(detect_drift(), args.quiet)


if __name__ == "__main__":
    sys.exit(main())
