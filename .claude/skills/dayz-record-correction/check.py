"""Helpers for /dayz-record-correction: find the Agentic-Z repo root, and compare the
repo checks before and after an edit so only failures the edit caused are reported.

    python check.py root <skill-dir>
    python check.py baseline --root <repo> --out <file.json>
    python check.py compare  --root <repo> --baseline <file.json>

`root` prints JSON and exits 0 for a usable clone or a plugin install, 2 otherwise.
`baseline` runs pytest and docs-sync --check and saves what already fails.
`compare` runs them again and exits 1 only when a failure is new since the baseline.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "dayz-record-correction"
REQUIRED = (Path(".claude/skills/_shared/dayz-conventions.md"), Path("CLAUDE.md"))
PYTEST_CMD = [sys.executable, "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider",
              ".claude", "scripts/dev", "hooks"]
DOCS_CMD = [sys.executable, ".claude/skills/docs-sync/sync.py", "--check"]

_SUMMARY = re.compile(r"^(FAILED|ERROR) (\S+?)(?: - .*)?$")
_DOCS_PROBLEM = re.compile(r"^(wiki/\S+?):\d+: (.+)$")


def resolve_root(skill_dir: str) -> dict:
    """Follow links from the skill folder and say whether it is a clone, a plugin, or unknown."""
    resolved = Path(skill_dir).resolve()
    parts = [p.lower() for p in resolved.parts]
    for i in range(len(parts) - 2):
        if parts[i:i + 3] == [".claude", "plugins", "cache"]:
            return {"kind": "plugin", "resolved": str(resolved), "root": None, "missing": []}
    if (resolved.name.lower() == SKILL_NAME and resolved.parent.name.lower() == "skills"
            and resolved.parent.parent.name.lower() == ".claude"):
        root = resolved.parents[2]
        missing = [str(r) for r in REQUIRED if not (root / r).is_file()]
        return {"kind": "clone", "resolved": str(resolved), "root": str(root), "missing": missing}
    return {"kind": "unknown", "resolved": str(resolved), "root": None, "missing": []}


def pytest_failures(output: str) -> list[str]:
    """Test ids from pytest's short summary (FAILED/ERROR lines)."""
    found = []
    for line in output.splitlines():
        m = _SUMMARY.match(line.strip())
        if m and m.group(2) not in found:
            found.append(m.group(2))
    return found


def docs_problems(output: str) -> list[str]:
    """docs-sync problems with the wiki line number dropped, so a shifted line is not 'new'."""
    found = []
    for line in output.splitlines():
        m = _DOCS_PROBLEM.match(line.strip())
        if m:
            key = f"{m.group(1)}: {m.group(2)}"
            if key not in found:
                found.append(key)
    return found


def run_checks(root: str, runner=subprocess.run) -> dict:
    """Run both checks from the repo root and return what fails."""
    t = runner(PYTEST_CMD, cwd=root, capture_output=True, text=True)
    d = runner(DOCS_CMD, cwd=root, capture_output=True, text=True)
    tests = pytest_failures(t.stdout + t.stderr)
    if t.returncode not in (0, 1) and not tests:
        tests = [f"pytest exited {t.returncode} without a failure summary"]
    return {"pytest": tests, "docs": docs_problems(d.stdout + d.stderr)}


def diff(before: dict, after: dict) -> dict:
    """New failures (in after, not before) and fixed ones (in before, not after)."""
    out = {}
    for key in ("pytest", "docs"):
        b, a = before.get(key, []), after.get(key, [])
        out[key] = {"new": [x for x in a if x not in b], "fixed": [x for x in b if x not in a]}
    return out


def main(argv=None, runner=subprocess.run) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("root")
    r.add_argument("skill_dir")
    b = sub.add_parser("baseline")
    b.add_argument("--root", required=True)
    b.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--root", required=True)
    c.add_argument("--baseline", required=True)
    a = p.parse_args(argv)

    if a.cmd == "root":
        info = resolve_root(a.skill_dir)
        print(json.dumps(info, indent=2))
        ok = info["kind"] == "plugin" or (info["kind"] == "clone" and not info["missing"])
        return 0 if ok else 2
    if a.cmd == "baseline":
        result = run_checks(a.root, runner)
        Path(a.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"baseline saved to {a.out}: {len(result['pytest'])} failing test(s), "
              f"{len(result['docs'])} wiki problem(s) before the edit")
        return 0
    before = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
    d = diff(before, run_checks(a.root, runner))
    for key, label in (("pytest", "test"), ("docs", "wiki problem")):
        for x in d[key]["new"]:
            print(f"NEW {label}: {x}")
        for x in d[key]["fixed"]:
            print(f"fixed {label}: {x}")
    new = len(d["pytest"]["new"]) + len(d["docs"]["new"])
    print(f"{new} new failure(s) since the baseline" if new else "[OK] no new failures since the baseline")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
