"""Helpers for /dayz-record-correction: find the Agentic-Z repo root, and compare the
repo checks before and after an edit so only failures the edit caused are reported.

    python check.py root <skill-dir>
    python check.py baseline --root <repo> [--out <file.json>] [--timeout <seconds>]
    python check.py compare  --root <repo> [--baseline <file.json>] [--timeout <seconds>]
                             [--max-age-hours <hours>]

`root` prints JSON and exits 0 for a usable clone or a plugin install, 2 otherwise.
`baseline` runs pytest and docs-sync --check and saves what already fails.
`compare` runs them again and exits 1 only when a failure is new since the baseline.
`baseline` and `compare` exit 2 when the baseline file cannot be written or read.
The baseline records the repo root and when it was made; `compare` exits 2 when the
baseline belongs to another root or is older than --max-age-hours (default 12), so it
never diffs against a stale or foreign baseline.
The baseline file defaults to record-correction-baseline.json in the system temp folder,
so the same command works from cmd, PowerShell and Git Bash. The full pytest run takes
several minutes; each check is stopped after --timeout seconds and counted as a failure.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SKILL_NAME = "dayz-record-correction"
REQUIRED = (Path("skills/_shared/dayz-conventions.md"), Path(".claude/CLAUDE.md"))
PYTEST_CMD = [sys.executable, "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider",
              ".claude", "skills", "scripts/dev", "hooks"]
DOCS_CMD = [sys.executable, ".claude/skills/docs-sync/sync.py", "--check"]
DEFAULT_BASELINE = Path(tempfile.gettempdir()) / "record-correction-baseline.json"
DEFAULT_TIMEOUT = 1200  # seconds per check; the full pytest run takes about 5 minutes
DEFAULT_MAX_AGE_HOURS = 12.0  # a baseline older than this is from an earlier session

_SUMMARY = re.compile(r"^(FAILED|ERROR) (.+)$")
# docs-sync prints "file:line: message", or "file: message" for a problem about a whole file.
_DOCS_PROBLEM = re.compile(r"^(wiki/\S+?)(?::\d+)?: (.+)$")


def resolve_root(skill_dir: str) -> dict:
    """Follow links from the skill folder and say whether it is a clone, a plugin, or unknown."""
    resolved = Path(skill_dir).resolve()
    parts = [p.lower() for p in resolved.parts]
    for i in range(len(parts) - 2):
        if parts[i:i + 3] == [".claude", "plugins", "cache"]:
            return {"kind": "plugin", "resolved": str(resolved), "root": None, "missing": []}
    if (resolved.name.lower() == SKILL_NAME and resolved.parent.name.lower() == "skills"
            and resolved.parents[1].name.lower() != ".claude"):
        root = resolved.parents[1]
        missing = [str(r) for r in REQUIRED if not (root / r).is_file()]
        return {"kind": "clone", "resolved": str(resolved), "root": str(root), "missing": missing}
    return {"kind": "unknown", "resolved": str(resolved), "root": None, "missing": []}


def pytest_failures(output: str) -> list[str]:
    """Test ids from pytest's short summary (FAILED/ERROR lines).

    The id ends at the first " - " (pytest's separator before the message) that is not
    inside [...], so a parametrized id with spaces or dashes, such as test_x[a - b], is
    kept whole.
    """
    found = []
    for line in output.splitlines():
        m = _SUMMARY.match(line.strip())
        if m:
            test_id = _split_id(m.group(2))
            if test_id and test_id not in found:
                found.append(test_id)
    return found


def _split_id(rest: str) -> str:
    """The test id part of 'id - message', ignoring ' - ' inside the parameter brackets."""
    depth = 0
    for i, ch in enumerate(rest):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(depth - 1, 0)
        elif depth == 0 and rest.startswith(" - ", i):
            return rest[:i].strip()
    return rest.strip()


def docs_problems(output: str) -> list[str]:
    """docs-sync problems with the wiki line number dropped, so a shifted line is not 'new'.

    Duplicates are kept: two identical problems in one file are two problems, and
    diff() compares them as counts.
    """
    found = []
    for line in output.splitlines():
        m = _DOCS_PROBLEM.match(line.strip())
        if m:
            found.append(f"{m.group(1)}: {m.group(2)}")
    return found


def _run(name: str, cmd: list, root: str, runner, timeout: int):
    """Run one check with a progress line and a timeout; (returncode, output), or None on timeout."""
    print(f"running {name} (can take several minutes) ...", file=sys.stderr, flush=True)
    try:
        r = runner(cmd, cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run_checks(root: str, runner=subprocess.run, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run both checks from the repo root and return what fails."""
    t = _run("pytest", PYTEST_CMD, root, runner, timeout)
    if t is None:
        tests = [f"pytest timed out after {timeout}s"]
    else:
        tests = pytest_failures(t[1])
        if t[0] != 0 and not tests:
            # A crash, or exit 1 with a summary the parser could not read, is not a pass.
            tests = [f"pytest exited {t[0]} without a failure summary"]
    d = _run("docs-sync --check", DOCS_CMD, root, runner, timeout)
    if d is None:
        docs = [f"docs-sync timed out after {timeout}s"]
    else:
        docs = docs_problems(d[1])
        if d[0] != 0 and not docs:
            # A crash or a refusal (missing wiki, traceback) lists no problems but is not a pass.
            docs = [f"docs-sync exited {d[0]} without a problem list"]
    return {"pytest": tests, "docs": docs}


def diff(before: dict, after: dict) -> dict:
    """New failures (more copies in after than before) and fixed ones (more copies in before).

    Compared as counts, so a second copy of a problem the baseline already had shows as new.
    """
    out = {}
    for key in ("pytest", "docs"):
        b, a = Counter(before.get(key, [])), Counter(after.get(key, []))
        out[key] = {"new": list((a - b).elements()), "fixed": list((b - a).elements())}
    return out


def _same_root(a: str, b: str) -> bool:
    """True when two paths name the same folder (links resolved, case ignored on Windows)."""
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))


def baseline_problem(before, root: str, max_age_hours: float, now: float):
    """Why this baseline cannot be trusted for a compare in root, or None when it can."""
    if not isinstance(before, dict) or not all(
            isinstance(before.get(k), list) for k in ("pytest", "docs")):
        return "it has no pytest and docs failure lists"
    if not isinstance(before.get("root"), str) or not isinstance(before.get("created"), (int, float)):
        return "it records no repo root or creation time (made by an older check.py)"
    if not _same_root(before["root"], root):
        return f"it was made for {before['root']}, not {Path(root).resolve()}"
    age = now - before["created"]
    if age < 0:
        return "its creation time is in the future"
    if age > max_age_hours * 3600:
        return f"it is {age / 3600:.1f} hours old, older than --max-age-hours {max_age_hours:g}"
    return None


def main(argv=None, runner=subprocess.run, now=time.time) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("root")
    r.add_argument("skill_dir")
    b = sub.add_parser("baseline")
    b.add_argument("--root", required=True)
    b.add_argument("--out", default=str(DEFAULT_BASELINE))
    b.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    c = sub.add_parser("compare")
    c.add_argument("--root", required=True)
    c.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    c.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    c.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    a = p.parse_args(argv)

    if a.cmd == "root":
        info = resolve_root(a.skill_dir)
        print(json.dumps(info, indent=2))
        ok = info["kind"] == "plugin" or (info["kind"] == "clone" and not info["missing"])
        return 0 if ok else 2
    if a.cmd == "baseline":
        result = run_checks(a.root, runner, a.timeout)
        saved = {"root": str(Path(a.root).resolve()), "created": now(), **result}
        try:
            Path(a.out).write_text(json.dumps(saved, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"[FAIL] could not write the baseline to {a.out}: {e}", file=sys.stderr)
            return 2
        print(f"baseline saved to {a.out}: {len(result['pytest'])} failing test(s), "
              f"{len(result['docs'])} wiki problem(s) before the edit")
        return 0
    try:
        before = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[FAIL] no baseline at {a.baseline}; run `check.py baseline` before the edit",
              file=sys.stderr)
        return 2
    except (OSError, ValueError) as e:
        print(f"[FAIL] could not read the baseline {a.baseline}: {e}; run `check.py baseline` again",
              file=sys.stderr)
        return 2
    problem = baseline_problem(before, a.root, a.max_age_hours, now())
    if problem:
        print(f"[FAIL] the baseline {a.baseline} cannot be used: {problem}; "
              "run `check.py baseline` again before the edit", file=sys.stderr)
        return 2
    d = diff(before, run_checks(a.root, runner, a.timeout))
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
