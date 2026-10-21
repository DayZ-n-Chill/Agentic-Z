"""dayz-health: store gate results per mod and render a health page for each.

  health.py [show] <ModName> [--json]
  health.py [show] --all [--json]
  health.py record <ModName> <kind> [FILE] [--json]

Every result is one JSON file under .server/!Health/<ModName>/results/, named
by its UTC time and kind (build, lint, ingame, behavior or review). /dayz-gate
writes one per run (and a lint result for each build run). `record` stores
any other result: the JSON output of /dayz-lint or /dayz-gate, or a
dayz-mod-reviewer report as text. FILE defaults to standard input.

`show` rebuilds health.md and health.html next to the results: the last
build, the last test, open findings (those in the newest result of each kind)
and the history. `record` and /dayz-gate rebuild them too.

The first output line is OK (exit 0) or ERROR (exit 2: bad arguments, no
project, unreadable report). See SKILL.md.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import skill_helpers as h  # noqa: E402

SCHEMA = 1
KINDS = ("build", "lint", "ingame", "behavior", "review")
KIND_LABELS = {"build": "Build", "lint": "Lint", "ingame": "In-game test", "behavior": "Behavior test", "review": "Review"}
TEST_KINDS = ("ingame", "behavior")
HEALTH_DIR = Path(".server") / "!Health"
KEEP = 200          # results kept per mod; older ones are deleted when a new one is stored
HISTORY_ROWS = 50   # rows in the page's history table
MOD_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
SEVERITY_ORDER = {"fail": 0, "critical": 0, "error": 0, "warn": 1, "warning": 1, "nit": 2}
# dayz-mod-reviewer report line: `<SEVERITY> path:line: what is wrong, and the fix -> <owner>`
REVIEW_LINE_RE = re.compile(
    r"^\s*[-*]?\s*(?P<sev>CRITICAL|WARN|NIT)\b[:\s]+(?P<where>\S+?)(?::(?P<line>\d+))?:\s+(?P<text>.+?)"
    r"(?:\s+->\s+(?P<owner>[\w:-]+))?\s*$"
)


class HealthError(Exception):
    """Bad input to the health store (exit 2)."""


# --- store ----------------------------------------------------------------------

def mod_dir(project_dir: Path, mod: str) -> Path:
    if not MOD_RE.match(mod) or ".." in mod:
        raise HealthError(f"not a mod name: {mod!r}")
    return project_dir / HEALTH_DIR / mod


def _finding(severity: str, text: str, file: Optional[str] = None, line: Optional[int] = None,
             category: str = "", owner: str = "", fix: str = "", count: int = 1) -> dict:
    return {"severity": severity, "category": category, "file": file or "", "line": line,
            "text": text, "owner": owner, "fix": fix, "count": count}


def _triaged(f: dict) -> tuple[str, str]:
    """(owner, fix) from a finding's triage: a known error names both, a new one goes to the debugger."""
    t = f.get("triage") or {}
    if t.get("status") == "known":
        return t.get("owner_agent", ""), t.get("fix", "")
    return ("dayz-mod-debugger", "") if t else ("", "")


def from_gate(report: dict) -> dict:
    """A /dayz-gate report (build, ingame or behavior) as a stored result."""
    findings = []
    for f in report.get("failures", []):
        owner, fix = _triaged(f)
        findings.append(_finding("fail", f["text"], f.get("file"), f.get("line"), f.get("category", ""),
                                 owner, fix, f.get("count", 1)))
    warnings = len(report.get("warnings", [])) + report.get("warnings_not_listed", 0)
    result = {"kind": report["mode"], "verdict": report["verdict"], "findings": findings, "warnings": warnings}
    if report.get("checks"):
        result["checks"] = [{"id": c["id"], "status": c["status"], "reason": c.get("reason", "")} for c in report["checks"]]
    lint = report.get("lint")
    if report["mode"] == "build" and lint and lint["verdict"] != "PASS":
        result["summary"] = "stopped at lint, nothing was packed"
    elif report.get("checks"):
        passed = sum(c["status"] == "PASS" for c in report["checks"])
        result["summary"] = f"{passed} of {len(report['checks'])} checks passed"
    return result


def lint_from_gate(report: dict) -> dict:
    """The lint step of a /dayz-gate build report as its own stored result."""
    findings = [
        _finding("fail", f["text"], f.get("file"), f.get("line"), "lint", *_triaged(f))
        for f in report.get("failures", []) if f.get("category") == "lint"
    ]
    findings += [
        _finding("warn", f["text"], f.get("file"), f.get("line"), "lint", *_triaged(f))
        for f in report.get("warnings", []) if f.get("category") == "lint"
    ]
    lint = report["lint"]
    return {"kind": "lint", "verdict": lint["verdict"], "findings": findings, "warnings": lint["warnings"]}


def from_lint(report: dict) -> dict:
    """/dayz-lint --json output as a stored result."""
    findings = []
    for f in report.get("findings", []):
        owner, fix = _triaged(f)
        severity = "fail" if f.get("severity") == "error" else "warn"
        findings.append(_finding(severity, f.get("message") or f["text"], f.get("file"), f.get("line"),
                                 f.get("rule", "lint"), owner, fix))
    return {"kind": "lint", "verdict": report["verdict"], "findings": findings, "warnings": report.get("warnings", 0)}


def from_review_text(text: str) -> dict:
    """A dayz-mod-reviewer report: first line PASS or FAIL, then one line per finding."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or lines[0].strip().upper() not in ("PASS", "FAIL"):
        raise HealthError("a review report starts with a PASS or FAIL line")
    findings = []
    for line in lines[1:]:
        m = REVIEW_LINE_RE.match(line)
        if m:
            sev = m["sev"].lower()
            findings.append(_finding("fail" if sev == "critical" else sev, m["text"], m["where"],
                                     int(m["line"]) if m["line"] else None, "review", m["owner"] or ""))
    return {"kind": "review", "verdict": lines[0].strip().upper(), "findings": findings,
            "warnings": sum(f["severity"] != "fail" for f in findings)}


def parse_report(kind: str, text: str) -> dict:
    """Turn what `record` was given into a stored result of `kind`."""
    if kind not in KINDS:
        raise HealthError(f"kind must be one of {', '.join(KINDS)}")
    brace = text.find("{")
    data = None
    if brace >= 0:
        try:
            data = json.loads(text[brace:])
        except json.JSONDecodeError:
            data = None
    if kind == "review" and data is None:
        return from_review_text(text)
    if not isinstance(data, dict) or data.get("verdict") not in ("PASS", "FAIL"):
        raise HealthError("the report is not JSON with a PASS or FAIL verdict (run the gate or lint with --json)")
    if kind == "review":
        findings = [_finding(str(f.get("severity", "warn")).lower(), f["text"], f.get("file"), f.get("line"),
                             "review", f.get("owner", "")) for f in data.get("findings", [])]
        return {"kind": "review", "verdict": data["verdict"], "findings": findings,
                "warnings": sum(f["severity"] != "fail" for f in findings)}
    if kind == "lint":
        return from_lint(data)
    if data.get("mode") != kind:
        raise HealthError(f"the report is a {data.get('mode')!r} gate report, not {kind!r}")
    return from_gate(data)


def store(project_dir: Path, mod: str, result: dict, now: Optional[datetime] = None) -> Path:
    """Write one result file and prune the oldest beyond KEEP. Returns its path."""
    now = now or datetime.now(timezone.utc)
    folder = mod_dir(project_dir, mod) / "results"
    folder.mkdir(parents=True, exist_ok=True)
    record = {"schema": SCHEMA, "mod": mod, "time": now.strftime("%Y-%m-%dT%H:%M:%SZ"), **result}
    path = folder / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{result['kind']}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    for old in sorted(folder.glob("*.json"))[:-KEEP]:
        old.unlink()
    return path


def record_gate(project_dir: Path, report: dict, now: Optional[datetime] = None) -> list[Path]:
    """Store a /dayz-gate report (plus its lint step) and rebuild the mod's pages."""
    now = now or datetime.now(timezone.utc)
    paths = []
    if report["mode"] == "build" and report.get("lint"):
        paths.append(store(project_dir, report["mod"], lint_from_gate(report), now))
    paths.append(store(project_dir, report["mod"], from_gate(report), now))
    render(project_dir, report["mod"])
    return paths


def load_results(project_dir: Path, mod: str) -> list[dict]:
    """Stored results for a mod, newest first. Files that don't parse are skipped."""
    folder = mod_dir(project_dir, mod) / "results"
    results = []
    for path in sorted(folder.glob("*.json"), reverse=True) if folder.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("kind") in KINDS:
            results.append(data)
    return results


# --- health ---------------------------------------------------------------------

def health(project_dir: Path, mod: str) -> dict:
    """What the page shows: latest result per kind, last build and test, open findings, history."""
    results = load_results(project_dir, mod)
    latest = {}
    for r in results:
        latest.setdefault(r["kind"], r)
    tests = [r for r in results if r["kind"] in TEST_KINDS]
    open_findings, seen = [], set()
    for kind in KINDS:
        for f in latest.get(kind, {}).get("findings", []):
            key = (f.get("file"), f.get("line"), f.get("text"))
            if key not in seen:
                seen.add(key)
                open_findings.append({**f, "from": kind})
    open_findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 3))
    return {
        "mod": mod,
        "latest": latest,
        "last_build": latest.get("build"),
        "last_test": tests[0] if tests else None,
        "open_findings": open_findings,
        "history": results,
    }


def _when(r: dict) -> str:
    return r["time"].replace("T", " ").replace("Z", " UTC")


def _where(f: dict) -> str:
    return f"{f['file']}:{f['line']}" if f.get("line") else (f.get("file") or "")


def _result_line(r: Optional[dict]) -> str:
    if r is None:
        return "never run"
    detail = f", {r['summary']}" if r.get("summary") else ""
    return f"{r['verdict']} ({KIND_LABELS[r['kind']]}, {_when(r)}{detail})"


def _counts(r: dict) -> tuple[int, int]:
    fails = sum(f["severity"] in ("fail", "critical", "error") for f in r.get("findings", []))
    return fails, r.get("warnings", 0)


def _md(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(data: dict) -> str:
    out = [f"# {data['mod']} health", ""]
    if not data["history"]:
        out += ["No gate results yet. Run `/dayz-gate build " + data["mod"] + "` to start the history.", ""]
        return "\n".join(out)
    out += [f"* Last build: {_result_line(data['last_build'])}",
            f"* Last test: {_result_line(data['last_test'])}",
            f"* Open findings: {len(data['open_findings'])}", ""]
    out += ["## Latest result per gate", "", "| Gate | Result | When | Failures | Warnings |", "| --- | --- | --- | --- | --- |"]
    for kind in KINDS:
        r = data["latest"].get(kind)
        if r is None:
            out.append(f"| {KIND_LABELS[kind]} | never run | | | |")
        else:
            fails, warns = _counts(r)
            out.append(f"| {KIND_LABELS[kind]} | {r['verdict']} | {_when(r)} | {fails} | {warns} |")
    out += ["", "## Open findings", ""]
    if data["open_findings"]:
        out += ["| Severity | Gate | Where | What | Owner | Fix |", "| --- | --- | --- | --- | --- | --- |"]
        for f in data["open_findings"]:
            text = f["text"] + (f" (x{f['count']})" if f.get("count", 1) > 1 else "")
            out.append(f"| {f['severity']} | {KIND_LABELS[f['from']]} | {_md(_where(f))} | {_md(text)} | "
                       f"{_md(f.get('owner', ''))} | {_md(f.get('fix', ''))} |")
    else:
        out.append("None.")
    behavior = data["latest"].get("behavior")
    if behavior and behavior.get("checks"):
        out += ["", "## Behavior checks (latest run)", "", "| Check | Result | Reason |", "| --- | --- | --- |"]
        out += [f"| {_md(c['id'])} | {c['status']} | {_md(c.get('reason', ''))} |" for c in behavior["checks"]]
    out += ["", "## History", "", "| When | Gate | Result | Failures | Warnings |", "| --- | --- | --- | --- | --- |"]
    for r in data["history"][:HISTORY_ROWS]:
        fails, warns = _counts(r)
        out.append(f"| {_when(r)} | {KIND_LABELS[r['kind']]} | {r['verdict']} | {fails} | {warns} |")
    if len(data["history"]) > HISTORY_ROWS:
        out.append(f"\n{len(data['history']) - HISTORY_ROWS} older results are not shown.")
    return "\n".join(out) + "\n"


HTML_STYLE = """
:root { --bg: #ffffff; --fg: #1a1a1a; --muted: #555555; --line: #d0d0d0; --head: #f2f2f2;
        --pass: #0b6b2e; --fail: #a4161a; --warn: #7a4b00; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161616; --fg: #ececec; --muted: #b0b0b0; --line: #3a3a3a; --head: #222222;
          --pass: #7ee2a0; --fail: #ff9a9a; --warn: #f5c76b; }
}
body { background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; margin: 0 auto;
       max-width: 72rem; padding: 1rem; }
h1, h2 { line-height: 1.2; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; }
th, td { border: 1px solid var(--line); padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }
th { background: var(--head); }
.muted { color: var(--muted); }
.PASS { color: var(--pass); font-weight: 600; }
.FAIL, .fail, .critical, .error { color: var(--fail); font-weight: 600; }
.warn, .warning { color: var(--warn); font-weight: 600; }
code { overflow-wrap: anywhere; }
"""


def _e(text) -> str:
    return html.escape(str(text if text is not None else ""))


def _badge(value: str) -> str:
    return f'<span class="{_e(value)}">{_e(value)}</span>'


def _table(caption: str, head: list[str], rows: list[list[str]]) -> str:
    """Rows are already escaped HTML cells."""
    th = "".join(f'<th scope="col">{_e(c)}</th>' for c in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return (f'<div class="table-wrap"><table><caption class="muted">{_e(caption)}</caption>'
            f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>")


def render_html(data: dict) -> str:
    mod = data["mod"]
    parts = [f"<h1>{_e(mod)} health</h1>"]
    if not data["history"]:
        parts.append(f"<p>No gate results yet. Run <code>/dayz-gate build {_e(mod)}</code> to start the history.</p>")
    else:
        parts.append("<ul>"
                     f"<li>Last build: {_e(_result_line(data['last_build']))}</li>"
                     f"<li>Last test: {_e(_result_line(data['last_test']))}</li>"
                     f"<li>Open findings: {len(data['open_findings'])}</li></ul>")
        rows = []
        for kind in KINDS:
            r = data["latest"].get(kind)
            if r is None:
                rows.append([_e(KIND_LABELS[kind]), '<span class="muted">never run</span>', "", "", ""])
            else:
                fails, warns = _counts(r)
                rows.append([_e(KIND_LABELS[kind]), _badge(r["verdict"]), _e(_when(r)), str(fails), str(warns)])
        parts += ["<h2>Latest result per gate</h2>",
                  _table("Newest result of each gate", ["Gate", "Result", "When", "Failures", "Warnings"], rows)]
        parts.append("<h2>Open findings</h2>")
        if data["open_findings"]:
            rows = [[_badge(f["severity"]), _e(KIND_LABELS[f["from"]]), f"<code>{_e(_where(f))}</code>",
                     _e(f["text"] + (f" (x{f['count']})" if f.get("count", 1) > 1 else "")),
                     _e(f.get("owner", "")), _e(f.get("fix", ""))] for f in data["open_findings"]]
            parts.append(_table("Findings in the newest result of each gate",
                                ["Severity", "Gate", "Where", "What", "Owner", "Fix"], rows))
        else:
            parts.append("<p>None.</p>")
        behavior = data["latest"].get("behavior")
        if behavior and behavior.get("checks"):
            rows = [[_e(c["id"]), _badge(c["status"]), _e(c.get("reason", ""))] for c in behavior["checks"]]
            parts += ["<h2>Behavior checks (latest run)</h2>", _table("One row per check", ["Check", "Result", "Reason"], rows)]
        rows = []
        for r in data["history"][:HISTORY_ROWS]:
            fails, warns = _counts(r)
            rows.append([_e(_when(r)), _e(KIND_LABELS[r["kind"]]), _badge(r["verdict"]), str(fails), str(warns)])
        parts += ["<h2>History</h2>", _table("Newest first", ["When", "Gate", "Result", "Failures", "Warnings"], rows)]
        if len(data["history"]) > HISTORY_ROWS:
            parts.append(f'<p class="muted">{len(data["history"]) - HISTORY_ROWS} older results are not shown.</p>')
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{_e(mod)} health</title>\n<style>{HTML_STYLE}</style>\n</head>\n<body>\n<main>\n"
            + "\n".join(parts) + "\n</main>\n</body>\n</html>\n")


def render(project_dir: Path, mod: str) -> tuple[dict, Path, Path]:
    """Rebuild health.md and health.html for one mod."""
    data = health(project_dir, mod)
    folder = mod_dir(project_dir, mod)
    folder.mkdir(parents=True, exist_ok=True)
    md, page = folder / "health.md", folder / "health.html"
    md.write_text(render_markdown(data), encoding="utf-8")
    page.write_text(render_html(data), encoding="utf-8")
    return data, md, page


def mods_with_results(project_dir: Path) -> list[str]:
    root = project_dir / HEALTH_DIR
    return sorted(p.name for p in root.iterdir() if (p / "results").is_dir()) if root.is_dir() else []


# --- cli ------------------------------------------------------------------------

def _rel(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


def _summary(data: dict, md: Path, page: Path, project_dir: Path) -> dict:
    return {
        "mod": data["mod"],
        "last_build": data["last_build"],
        "last_test": data["last_test"],
        "open_findings": data["open_findings"],
        "results": len(data["history"]),
        "markdown": _rel(md, project_dir),
        "html": _rel(page, project_dir),
    }


def _print_summary(s: dict) -> None:
    print(f"  {s['mod']}: last build {_result_line(s['last_build'])}; last test {_result_line(s['last_test'])}; "
          f"{len(s['open_findings'])} open finding(s); {s['results']} result(s)")
    print(f"    {s['markdown']}")
    print(f"    {s['html']}")


def main(argv: Optional[list[str]] = None, stdin=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("show", "record", "-h", "--help"):
        argv.insert(0, "show")
    parser = argparse.ArgumentParser(description="Store gate results per mod and render health pages.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="Rebuild and summarize the health page of a mod (or every mod).")
    s.add_argument("mod", nargs="?")
    s.add_argument("--all", action="store_true", help="Every mod with stored results.")
    s.add_argument("--json", action="store_true")
    r = sub.add_parser("record", help="Store a lint, gate or review result.")
    r.add_argument("mod")
    r.add_argument("kind", choices=KINDS)
    r.add_argument("file", nargs="?", type=Path, help="The report (default: standard input).")
    r.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    if args.cmd == "show" and bool(args.mod) == args.all:
        return _error("give one <ModName> or --all", args.json)

    try:
        project_dir = h.resolve_project_dir()
        if args.cmd == "record":
            text = args.file.read_text(encoding="utf-8-sig") if args.file else (stdin or sys.stdin).read()
            path = store(project_dir, args.mod, parse_report(args.kind, text))
            mods = [args.mod]
        else:
            path = None
            mods = mods_with_results(project_dir) if args.all else [args.mod]
        summaries = [_summary(*render(project_dir, m), project_dir) for m in mods]
    except SystemExit:  # resolve_project_dir already printed why on stderr
        return _error("no usable project: run /dayz-init", args.json)
    except (HealthError, OSError, UnicodeDecodeError) as e:
        return _error(str(e), args.json)

    print("OK")
    if args.json:
        out = {"mods": summaries}
        if path is not None:
            out["recorded"] = _rel(path, project_dir)
        print(json.dumps(out, indent=2))
        return 0
    if path is not None:
        print(f"  recorded {_rel(path, project_dir)}")
    if not summaries:
        print("  no gate results stored yet")
    for summary in summaries:
        _print_summary(summary)
    return 0


def _error(message: str, as_json: bool) -> int:
    print("ERROR")
    print(json.dumps({"verdict": "ERROR", "error": message}, indent=2) if as_json else f"  {message}")
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
