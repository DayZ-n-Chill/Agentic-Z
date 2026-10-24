"""Answer tests (evals) for the Agentic-Z agents.

Sends every question in evals/questions/<agent>.json to its agent with
`claude -p --agent <name>`, scores each answer with plain string and regex
checks, and writes a results file. With --baseline it compares the run
against evals/baseline.json and exits 1 when any agent scored lower or lost a
question it passed before. --update-baseline refuses a run where a question
errored, so a missing claude CLI can never be recorded as a score of 0, and
stamps each entry it writes with the date, the model and `claude --version`.
The model is the id claude reports it answered with (from `--output-format
json`), so a change of the CLI default model shows in the baseline.
A failed comparison prints those for the baseline entry and for this run.
The results file is rewritten after every question, so a crash or a killed
process keeps every answer collected so far. An answer that is not valid UTF-8,
or any other failure while asking or scoring one question, counts as an errored
question and the run goes on. Ctrl+C stops the run, still writes the results
file with the questions asked so far (the one it was on marked as an error) and
exits 130 without touching the baseline. Without --baseline, exit 0 only means
the run finished, not that the questions passed.

Run with: py scripts/dev/run_evals.py [--agent NAME] [--dry-run] [--baseline]
          [--update-baseline] [--out FILE] [--timeout SECONDS] [--model MODEL]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[2]
QUESTIONS_DIR = REPO / "evals" / "questions"
BASELINE = REPO / "evals" / "baseline.json"
AGENTS_DIR = REPO / ".claude" / "agents"
RESULTS_DIR = REPO / "output" / "evals"

# --allowedTools only grants these without a prompt; it does not take the other
# tools away. The agent keeps its own tools (Edit and Write for the specialists)
# and the project's allow rules, so the editing and shell tools are also
# removed with --disallowedTools. Then an eval run cannot edit the repo. The
# Agent (Task) tool goes too, since a subagent brings its own edit and shell
# tools, and so do the web tools: an answer must come from P:\, not the web.
# MultiEdit is not listed: Claude Code no longer has that tool, and since
# 2.1.308 a deny rule naming an unknown tool makes `claude -p --agent` exit 1.
READ_ONLY_TOOLS = [
    "Read", "Glob", "Grep",
    "mcp__dayz-rag__search_dayz_source", "mcp__plugin_agentic-z_dayz-rag__search_dayz_source",
    "mcp__dayz-rag__get_dayz_file", "mcp__plugin_agentic-z_dayz-rag__get_dayz_file",
    "mcp__dayz-rag__list_indexed_sources", "mcp__plugin_agentic-z_dayz-rag__list_indexed_sources",
]
DENIED_TOOLS = ["Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task", "WebFetch", "WebSearch"]

REGEX_PREFIX = "re:"


def _compile(pattern: str) -> re.Pattern:
    return re.compile(pattern[len(REGEX_PREFIX):], re.IGNORECASE | re.MULTILINE)


def check_matches(answer: str, check: str) -> bool:
    """A check is a plain case-insensitive substring, or a regex after 're:'."""
    if check.startswith(REGEX_PREFIX):
        return bool(_compile(check).search(answer))
    return check.lower() in answer.lower()


def _norm_path(text: str) -> str:
    return text.replace("\\", "/").lower()


def score(answer: str, question: dict) -> dict:
    """Score one answer. It passes only when every check passes."""
    failed = []
    for check in question.get("must_include", []):
        if not check_matches(answer, check):
            failed.append(f"missing: {check}")
    for check in question.get("must_not_include", []):
        if check_matches(answer, check):
            failed.append(f"forbidden: {check}")
    cite = question.get("cite")
    if cite and _norm_path(cite) not in _norm_path(answer):
        failed.append(f"no citation of: {cite}")
    return {"id": question["id"], "passed": not failed, "failed_checks": failed}


def file_hashes(paths: list[str]) -> dict[str, str | None]:
    """Hash each repo-relative path, None when it is missing, so a run can prove a file was left alone."""
    out = {}
    for rel in paths:
        f = REPO / rel
        out[rel] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    return out


def changed_files(before: dict[str, str | None], after: dict[str, str | None]) -> list[str]:
    return [f"changed: {rel}" for rel in before if before[rel] != after.get(rel)]


def validate(path: Path) -> tuple[dict, list[str]]:
    """Load a question file and list every problem with it."""
    problems = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"{path.name}: {exc}"]
    agent = data.get("agent")
    if agent != path.stem:
        problems.append(f"{path.name}: agent must be {path.stem!r}, got {agent!r}")
    if not (AGENTS_DIR / f"{path.stem}.md").exists():
        problems.append(f"{path.name}: no agent file .claude/agents/{path.stem}.md")
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        return data, problems + [f"{path.name}: needs a non-empty questions list"]
    seen = set()
    for i, q in enumerate(questions):
        where = f"{path.name} question {q.get('id', i)}"
        if q.get("id") in seen or not q.get("id"):
            problems.append(f"{where}: id missing or repeated")
        seen.add(q.get("id"))
        if not q.get("question"):
            problems.append(f"{where}: question is empty")
        if not q.get("must_include"):
            problems.append(f"{where}: must_include is empty")
        if not q.get("verified"):
            problems.append(f"{where}: verified is empty (name the P: path and line or the agent rule checked)")
        for check in q.get("must_include", []) + q.get("must_not_include", []):
            if check.startswith(REGEX_PREFIX):
                try:
                    _compile(check)
                except re.error as exc:
                    problems.append(f"{where}: bad regex {check!r}: {exc}")
        for rel in q.get("unchanged", []):
            if not (REPO / rel).is_file():
                problems.append(f"{where}: unchanged file {rel} does not exist")
    return data, problems


def load_suites(agents: list[str] | None) -> tuple[list[dict], list[str]]:
    paths = sorted(QUESTIONS_DIR.glob("*.json"))
    if agents:
        wanted = set(agents)
        missing = wanted - {p.stem for p in paths}
        paths = [p for p in paths if p.stem in wanted]
        if missing:
            return [], [f"no question file for {name}" for name in sorted(missing)]
    suites, problems = [], []
    for path in paths:
        data, found = validate(path)
        problems += found
        if not found:
            suites.append(data)
    return suites, problems


def build_command(exe: str, agent: str, model: str | None = None) -> list[str]:
    """The claude command line for one question: read-only tools, editing and shell tools removed."""
    cmd = [exe, "-p", "--agent", agent,
           "--allowedTools", ",".join(READ_ONLY_TOOLS),
           "--disallowedTools", ",".join(DENIED_TOOLS),
           "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    return cmd


def run_tree(cmd: list[str], stdin: str, timeout: int) -> subprocess.CompletedProcess:
    """Run cmd and, on timeout, kill its whole process tree before raising TimeoutExpired.

    On Windows `claude` resolves to claude.CMD, so the child is cmd.exe and the
    real claude.exe is a grandchild. subprocess.run's timeout kills only cmd.exe;
    the grandchild keeps the output pipes open and the run hangs for good.

    The pipes are read as bytes and decoded here: decoding inside communicate()
    would turn an answer that is not valid UTF-8 into an uncaught error that ends
    the whole run. Such an answer raises RuntimeError, so it is recorded as an
    errored question and the run goes on.
    """
    posix = os.name != "nt"
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=REPO, start_new_session=posix)
    try:
        out, err = proc.communicate(stdin.encode("utf-8"), timeout=timeout)
    except subprocess.TimeoutExpired:
        if posix:
            os.killpg(proc.pid, 9)
        else:
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.communicate()
        raise
    try:
        text = out.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"claude output is not valid UTF-8: {exc}") from exc
    return subprocess.CompletedProcess(cmd, proc.returncode, text.replace("\r\n", "\n"),
                                       err.decode("utf-8", errors="replace"))


class Answer(str):
    """An agent's answer text, carrying the model id claude says produced it (None when unknown)."""

    def __new__(cls, text: str, model: str | None = None):
        obj = super().__new__(cls, text)
        obj.model = model
        return obj


def parse_output(text: str) -> Answer:
    """The answer and model id from `claude -p --output-format json` output.

    The CLI prints either one result object or a list of events ending in one.
    The model is the one in the result's modelUsage that wrote the most output
    tokens, so a small background model call never names the run.
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise RuntimeError(f"claude output is not JSON: {text.strip()[:200]}") from exc
    events = data if isinstance(data, list) else [data]
    result = next((e for e in reversed(events) if isinstance(e, dict) and e.get("type") == "result"), None)
    if result is None:
        raise RuntimeError("claude output has no result event")
    if result.get("is_error"):
        raise RuntimeError(f"claude reported an error: {str(result.get('result'))[:500]}")
    usage = result.get("modelUsage") or {}
    model = max(usage, key=lambda m: (usage[m] or {}).get("outputTokens", 0)) if usage else None
    return Answer(result.get("result") or "", model)


def ask(agent: str, question: str, timeout: int, model: str | None = None) -> str:
    """Ask one agent one question through the Claude Code CLI and return its answer (an Answer)."""
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI not found on PATH")
    cmd = build_command(exe, agent, model)
    # The question goes in on stdin so Windows quoting never mangles code snippets.
    proc = run_tree(cmd, question, timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    return parse_output(proc.stdout)


def write_results(out: Path, results: dict) -> None:
    """Write the results file through a temporary file, so a crash mid-write never leaves it half-written."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    os.replace(tmp, out)


def run(suites: list[dict], timeout: int, model: str | None = None,
        save: Callable[[dict], None] | None = None) -> dict:
    """Ask every question. Ctrl+C stops the run: the question it was on is recorded
    as an error, results["interrupted"] is set, and the answers so far are kept.
    Any other exception while asking or scoring a question is recorded as an
    error for that question and the run goes on. save, when given, is called
    with the results after every question."""
    results = {"run_at": datetime.now().isoformat(timespec="seconds"), "agents": {}}
    for suite in suites:
        agent = suite["agent"]
        rows = []
        models: set[str] = set()  # the model ids claude reported for this agent's answers
        for q in suite["questions"]:
            print(f"{agent} / {q['id']} ...", flush=True)
            try:
                before = file_hashes(q.get("unchanged", []))
                answer = ask(agent, q["question"], timeout, model)
                if getattr(answer, "model", None):
                    models.add(answer.model)
                row = score(answer, q)
                row["failed_checks"] += changed_files(before, file_hashes(list(before)))
                row["passed"] = not row["failed_checks"]
            except Exception as exc:  # one bad question must not end a run of hundreds
                answer = ""
                row = {"id": q["id"], "passed": False, "error": True, "failed_checks": [f"error: {exc}"]}
            except KeyboardInterrupt:
                results["interrupted"] = True
                answer = ""
                row = {"id": q["id"], "passed": False, "error": True, "failed_checks": ["error: interrupted"]}
            row["answer"] = answer
            print(f"  {'PASS' if row['passed'] else 'FAIL'} {'; '.join(row['failed_checks'])}", flush=True)
            rows.append(row)
            results["agents"][agent] = {"score": sum(r["passed"] for r in rows), "total": len(rows),
                                        "questions": rows}
            if models:
                results["agents"][agent]["model"] = ", ".join(sorted(models))
            if save:
                try:
                    save(results)
                except KeyboardInterrupt:  # save writes through a temporary file, so the last good copy stays
                    results["interrupted"] = True
            if results.get("interrupted"):
                break
        if results.get("interrupted"):
            break
    return results


def passed_ids(entry: dict) -> list[str]:
    return sorted(r["id"] for r in entry["questions"] if r["passed"])


def compare(results: dict, baseline: dict, require_baseline: bool = False) -> list[str]:
    """List every agent whose score fell below its baseline or that lost a passed question.

    A baseline entry with a "passed" list is compared question by question, so
    a run that passes as many questions but different ones is still caught.
    Only the passed ids still asked in this run count, so a question that was
    renamed or removed from its question file does not count as lost. An entry
    without a "passed" list is compared by score. With require_baseline (the --baseline check), an agent with no baseline
    entry is listed too, since a drop could never be caught for it.
    """
    drops = []
    for agent, entry in results["agents"].items():
        before = baseline.get(agent, {})
        if before.get("score") is None:
            if require_baseline:
                drops.append(f"{agent}: no baseline entry; record one with --update-baseline")
            continue
        if "passed" in before and "questions" in entry:
            # Only questions still in the question file count: a renamed or removed
            # question cannot be asked again, so it must not block the gate forever.
            # Every kept question passing also means the score did not fall below
            # the baseline for the questions that are still there.
            kept = set(before["passed"]) & {r["id"] for r in entry["questions"]}
            lost = sorted(kept - set(passed_ids(entry)))
            if lost:
                drops.append(f"{agent}: no longer passes {', '.join(lost)}")
        elif entry["score"] < before["score"]:
            drops.append(f"{agent}: {entry['score']}/{entry['total']} is below the baseline {before['score']}")
    return drops


def claude_version() -> str | None:
    """The `claude --version` line, or None when the CLI is missing or does not answer."""
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def run_info(model: str | None) -> dict:
    """What produced a run: the model passed with --model (or the CLI default) and the claude version.

    Each agent's entry also gets the model id claude reported, which wins over this.
    """
    return {"model": model or "claude CLI default", "claude_version": claude_version() or "unknown"}


def provenance(entry: dict) -> str:
    """One line naming the date, model and claude version an entry or run was recorded with."""
    return (f"recorded {entry.get('recorded') or 'unknown date'}, model {entry.get('model') or 'not recorded'}, "
            f"claude {entry.get('claude_version') or 'not recorded'}")


def errors_of(results: dict) -> list[str]:
    """Every question that errored (claude missing, nonzero exit, timeout, output not UTF-8) as agent/id."""
    return [f"{a}/{r['id']}" for a, e in results["agents"].items() for r in e["questions"] if r.get("error")]


def scores_of(results: dict) -> dict:
    """Baseline entries for a run: the scores plus the date, model and claude version that produced them."""
    stamp = {"recorded": results["run_at"][:10], "claude_version": results.get("claude_version")}
    return {a: {"score": e["score"], "total": e["total"], "passed": passed_ids(e),
                "recorded": stamp["recorded"], "model": e.get("model") or results.get("model"),
                "claude_version": stamp["claude_version"]}
            for a, e in results["agents"].items()}


def drop_report(drops: list[str], results: dict, baseline: dict) -> list[str]:
    """The drops, each followed by what produced the baseline entry and this run, so a model or CLI change shows."""
    lines = []
    for d in drops:
        agent = d.split(":", 1)[0]
        resolved = results["agents"].get(agent, {}).get("model")
        now = provenance({"recorded": results["run_at"][:10], **results, **({"model": resolved} if resolved else {})})
        lines += [d, f"  baseline: {provenance(baseline.get(agent, {}))}", f"  this run: {now}"]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Agentic-Z answer tests (evals).")
    parser.add_argument("--agent", action="append", help="only this agent (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="check the question files and list the calls, ask nothing")
    parser.add_argument("--baseline", action="store_true", help="fail when a score is below evals/baseline.json")
    parser.add_argument("--update-baseline", action="store_true", help="write these scores to evals/baseline.json")
    parser.add_argument("--out", type=Path, help="results file (default output/evals/results-<time>.json)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per question (default 900)")
    parser.add_argument("--model", help="model to pass to claude")
    args = parser.parse_args(argv)

    suites, problems = load_suites(args.agent)
    if problems:
        for p in problems:
            print(f"ERROR {p}", file=sys.stderr)
        return 2

    if args.dry_run:
        for suite in suites:
            for q in suite["questions"]:
                print(f"would ask: claude -p --agent {suite['agent']}  [{q['id']}]")
        total = sum(len(s["questions"]) for s in suites)
        print(f"{total} questions for {len(suites)} agents; question files are valid.")
        return 0

    out = args.out or RESULTS_DIR / f"results-{datetime.now():%Y%m%d-%H%M%S}.json"
    try:
        info = run_info(args.model)
        results = run(suites, args.timeout, args.model, save=lambda r: write_results(out, {**r, **info}))
        results.update(info)
        write_results(out, results)
    except KeyboardInterrupt:
        # Stopped before the first question or while writing the final file: the
        # results file holds whatever run() already saved.
        print("run interrupted: baseline not checked or updated", file=sys.stderr)
        return 130
    for agent, entry in results["agents"].items():
        print(f"{agent}: {entry['score']}/{entry['total']}")
    print(f"results: {out}")
    if results.get("interrupted"):
        print("run interrupted: the results file holds the questions asked so far; "
              "baseline not checked or updated", file=sys.stderr)
        return 130

    code = 0
    if args.baseline:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        drops = compare(results, baseline, require_baseline=True)
        for line in drop_report(drops, results, baseline):
            print(line if line.startswith(" ") else f"REGRESSION {line}", file=sys.stderr)
        code = 1 if drops else 0
    if args.update_baseline:
        errors = errors_of(results)
        if errors:
            print(f"baseline not updated: these questions errored: {', '.join(errors)}", file=sys.stderr)
            return 1
        baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        drops = compare(results, baseline)
        if drops:
            print("baseline not updated: a score went down or a passed question was lost", file=sys.stderr)
            for line in drop_report(drops, results, baseline):
                print(line, file=sys.stderr)
            return 1
        baseline.update(scores_of(results))
        BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"baseline updated: {BASELINE}")
    return code


if __name__ == "__main__":
    sys.exit(main())
