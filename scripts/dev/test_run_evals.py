"""Tests for the evals runner. The claude call is always mocked; nothing here asks a real agent.

Run with: py -m pytest scripts/dev/test_run_evals.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("run_evals", Path(__file__).with_name("run_evals.py"))
run_evals = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_evals)

FIRST_AGENTS = ["dayz-script-specialist", "dayz-config-specialist", "dayz-mod-reviewer"]


@pytest.fixture(autouse=True)
def no_real_claude(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("tests must not call claude")
    monkeypatch.setattr(run_evals.subprocess, "run", refuse)
    monkeypatch.setattr(run_evals, "claude_version", lambda: "9.9.9 (Claude Code)")


def _suite(tmp_path, agent="dayz-script-specialist", questions=None):
    questions = questions or [{"id": "q1", "question": "Which layer?", "must_include": ["4_World"],
                               "verified": "P:/scripts/4_World"}]
    path = tmp_path / f"{agent}.json"
    path.write_text(json.dumps({"agent": agent, "questions": questions}), encoding="utf-8")
    return path


# Scoring

def test_plain_check_is_case_insensitive_substring():
    assert run_evals.check_matches("Put it in 4_world.", "4_World")
    assert not run_evals.check_matches("Put it in 5_Mission.", "4_World")


def test_regex_check():
    assert run_evals.check_matches("class Apple: Edible_Base", r"re:class\s+Apple\s*:\s*Edible_Base")
    assert not run_evals.check_matches("class Apple_Big: Apple", r"re:class\s+Apple\s*:\s*Edible_Base")


def test_regex_anchor_matches_first_line_only_with_A():
    answer = "**FAIL**\nCRITICAL x\nPASS would be wrong"
    assert run_evals.check_matches(answer, r"re:\A\W*FAIL")
    assert not run_evals.check_matches(answer, r"re:\A\W*PASS")


def test_score_passes_when_every_check_passes():
    q = {"id": "q", "must_include": ["SetSynchDirty"], "must_not_include": ["re:\\byes\\b"],
         "cite": "3_game/entities/entityai.c"}
    row = run_evals.score("Call SetSynchDirty, see P:\\scripts\\3_game\\entities\\entityai.c:3064", q)
    assert row == {"id": "q", "passed": True, "failed_checks": []}


def test_score_lists_each_failure():
    q = {"id": "q", "must_include": ["SetSynchDirty"], "must_not_include": ["yes"], "cite": "entityai.c"}
    row = run_evals.score("yes, just do it", q)
    assert not row["passed"]
    assert row["failed_checks"] == ["missing: SetSynchDirty", "forbidden: yes", "no citation of: entityai.c"]


# Question files

def test_validate_accepts_good_file(tmp_path):
    data, problems = run_evals.validate(_suite(tmp_path))
    assert problems == []
    assert data["agent"] == "dayz-script-specialist"


@pytest.mark.parametrize("questions, expected", [
    ([{"id": "q", "question": "x", "must_include": []}], "must_include is empty"),
    ([{"id": "q", "question": "", "must_include": ["a"]}], "question is empty"),
    ([{"id": "q", "question": "x", "must_include": ["re:("]}], "bad regex"),
    ([{"id": "q", "question": "x", "must_include": ["a"]}] * 2, "id missing or repeated"),
])
def test_validate_reports_problems(tmp_path, questions, expected):
    _, problems = run_evals.validate(_suite(tmp_path, questions=questions))
    assert any(expected in p for p in problems), problems


def test_dry_run_rejects_question_without_verified(monkeypatch, tmp_path):
    # docs/evals.md: `verified` is required for every shipped question, for every agent.
    _suite(tmp_path, agent="dayz-docs-writer",
           questions=[{"id": "q", "question": "x", "must_include": ["a"]}])
    monkeypatch.setattr(run_evals, "QUESTIONS_DIR", tmp_path)
    _, problems = run_evals.validate(tmp_path / "dayz-docs-writer.json")
    assert any("verified is empty" in p for p in problems), problems
    assert run_evals.main(["--dry-run"]) == 2


def test_validate_rejects_unknown_agent(tmp_path):
    _, problems = run_evals.validate(_suite(tmp_path, agent="dayz-nobody"))
    assert any("no agent file" in p for p in problems)


@pytest.mark.parametrize("agent", FIRST_AGENTS)
def test_shipped_question_files_are_valid(agent):
    data, problems = run_evals.validate(run_evals.QUESTIONS_DIR / f"{agent}.json")
    assert problems == []
    assert len(data["questions"]) >= 5
    for q in data["questions"]:
        assert q.get("verified"), f"{agent}/{q['id']} has no verified source"


def test_no_vanilla_human_ai_rejects_an_answer_that_does_not_open_with_no():
    data, _ = run_evals.validate(run_evals.QUESTIONS_DIR / "dayz-ai-specialist.json")
    q = next(q for q in data["questions"] if q["id"] == "no-vanilla-human-ai")
    assert run_evals.score("**No.** Vanilla AI is only DayZInfected and AnimalBase.", q)["passed"]
    # A wrong answer that says "no" somewhere and mentions infected must still fail.
    assert not run_evals.score("Sure, inherit SurvivorBase. There is no extra setup; infected are separate.", q)["passed"]


def test_long_range_optic_slot_rejects_a_wrong_yes_that_says_not_elsewhere():
    data, _ = run_evals.validate(run_evals.QUESTIONS_DIR / "dayz-weapon-specialist.json")
    q = next(q for q in data["questions"] if q["id"] == "long-range-optic-slot")
    assert run_evals.score("Use weaponOpticsLRS. **No vanilla weapon offers the slot:** only the optic lists it.", q)["passed"]
    assert run_evals.score("List weaponOpticsLRS. No vanilla gun lists the slot in attachments[].", q)["passed"]
    assert run_evals.score("Add weaponOpticsLRS. Vanilla weapons don't list it anywhere.", q)["passed"]
    # A wrong answer that says "not" somewhere must still fail.
    assert not run_evals.score(
        "Use weaponOpticsLRS. Yes, the vanilla SVD offers it, so you do not need a custom proxy.", q)["passed"]


def test_every_question_file_is_valid():
    suites, problems = run_evals.load_suites(None)
    assert problems == []
    assert {s["agent"] for s in suites} >= set(FIRST_AGENTS)


# Running

def test_ask_builds_read_only_claude_command(monkeypatch):
    seen = {}

    def fake_run(cmd, stdin, timeout):
        seen["cmd"], seen["input"], seen["timeout"] = cmd, stdin, timeout
        return subprocess.CompletedProcess(cmd, 0, stdout=_claude_json("answer"), stderr="")
    monkeypatch.setattr(run_evals.shutil, "which", lambda name: "claude")
    monkeypatch.setattr(run_evals, "run_tree", fake_run)
    assert run_evals.ask("dayz-mod-reviewer", "Q?", timeout=5, model="opus") == "answer"
    cmd = seen["cmd"]
    assert cmd[cmd.index("--output-format") + 1] == "json"
    assert cmd[:4] == ["claude", "-p", "--agent", "dayz-mod-reviewer"]
    tools = cmd[cmd.index("--allowedTools") + 1]
    assert "Edit" not in tools.split(",") and "Write" not in tools.split(",")
    assert seen["input"] == "Q?"
    assert seen["timeout"] == 5
    assert cmd[-2:] == ["--model", "opus"]


def _claude_json(text, usage=None, as_list=False, is_error=False):
    """What `claude -p --output-format json` prints: one result object, or a list of events ending in one."""
    result = {"type": "result", "subtype": "success", "is_error": is_error, "result": text,
              "modelUsage": usage if usage is not None else {"claude-opus-5-5": {"outputTokens": 40}}}
    if as_list:
        return json.dumps([{"type": "system", "subtype": "init", "model": "claude-opus-5-5"}, result])
    return json.dumps(result)


@pytest.mark.parametrize("as_list", [False, True])
def test_parse_output_returns_answer_and_the_model_that_wrote_it(as_list):
    """A baseline stamped 'claude CLI default' cannot show that the default model changed under it."""
    usage = {"claude-haiku-4-5": {"outputTokens": 3}, "claude-opus-5-5": {"outputTokens": 900}}
    answer = run_evals.parse_output(_claude_json("Use 4_World.", usage, as_list=as_list))
    assert answer == "Use 4_World."
    assert answer.model == "claude-opus-5-5"


def test_parse_output_without_model_usage_has_no_model():
    assert run_evals.parse_output(_claude_json("ok", usage={})).model is None


@pytest.mark.parametrize("text, message", [
    ("plain text answer", "not JSON"),
    (json.dumps([{"type": "system"}]), "no result event"),
    (_claude_json("rate limited", is_error=True), "reported an error"),
])
def test_parse_output_raises_on_unusable_output(text, message):
    with pytest.raises(RuntimeError, match=message):
        run_evals.parse_output(text)


def test_baseline_records_the_model_claude_reported(monkeypatch, tmp_path):
    """The resolved id wins over 'claude CLI default' and over an alias passed with --model."""
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask",
                        lambda agent, q, timeout, model=None: run_evals.Answer("", "claude-opus-5-5"))
    args = ["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"), "--update-baseline"]
    assert run_evals.main(args) == 0
    assert json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]["model"] == "claude-opus-5-5"
    assert run_evals.main(args + ["--model", "opus"]) == 0
    assert json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]["model"] == "claude-opus-5-5"
    results = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert results["agents"]["dayz-script-specialist"]["model"] == "claude-opus-5-5"


def test_failed_check_names_the_model_claude_reported(monkeypatch, tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask",
                        lambda agent, q, timeout, model=None: run_evals.Answer("", "claude-sonnet-5"))
    baseline.write_text(json.dumps({"dayz-script-specialist": {
        "score": 3, "total": 5, "recorded": "2026-01-02", "model": "claude-opus-5-5", "claude_version": "1.0.0"}}),
        encoding="utf-8")
    args = ["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"), "--baseline"]
    assert run_evals.main(args) == 1
    err = capsys.readouterr().err
    assert "baseline: recorded 2026-01-02, model claude-opus-5-5, claude 1.0.0" in err
    assert re.search(r"this run: recorded \d{4}-\d{2}-\d{2}, model claude-sonnet-5, claude 9\.9\.9", err)


def test_command_removes_editing_and_shell_tools():
    """--allowedTools alone does not take an agent's own Edit and Write away.

    MultiEdit must not be denied: Claude Code dropped that tool, and since
    2.1.308 a deny rule for an unknown tool makes every eval call exit 1.
    """
    cmd = run_evals.build_command("claude", "dayz-config-specialist", model="opus")
    denied = cmd[cmd.index("--disallowedTools") + 1].split(",")
    assert "MultiEdit" not in denied
    for tool in ("Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task", "WebFetch", "WebSearch"):
        assert tool in denied
    allowed = cmd[cmd.index("--allowedTools") + 1].split(",")
    assert not set(allowed) & set(denied)
    assert cmd[-2:] == ["--model", "opus"]


def test_ask_raises_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(run_evals.shutil, "which", lambda name: "claude")
    monkeypatch.setattr(run_evals, "run_tree",
                        lambda cmd, stdin, timeout: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom"))
    with pytest.raises(RuntimeError, match="boom"):
        run_evals.ask("a", "q", timeout=5)


def test_timeout_kills_grandchild_that_holds_the_pipes():
    """On Windows `claude` is claude.CMD, so claude.exe is a grandchild that holds stdout.

    A timeout that kills only the direct child left the eval run hanging until
    the grandchild exited on its own (the server-admin run hung for over an hour).
    """
    grandchild = "import time; time.sleep(60)"
    child = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(60)"
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_evals.run_tree([sys.executable, "-c", child], "", timeout=3)
    assert time.monotonic() - started < 30


def test_run_tree_raises_runtime_error_for_output_that_is_not_utf8():
    """Decoding inside communicate() raised an uncaught UnicodeDecodeError that ended the whole run."""
    child = "import sys; sys.stdout.buffer.write(b'ok \\xff\\xfe bad'); sys.stdout.flush()"
    with pytest.raises(RuntimeError, match="not valid UTF-8"):
        run_evals.run_tree([sys.executable, "-c", child], "", timeout=30)


def test_run_tree_round_trips_utf8_and_normalises_newlines():
    child = "import sys; data = sys.stdin.buffer.read(); sys.stdout.buffer.write(data + b'\\r\\nline2')"
    proc = run_evals.run_tree([sys.executable, "-c", child], "Größe ✓", timeout=30)
    assert proc.returncode == 0
    assert proc.stdout == "Größe ✓\nline2"


def test_undecodable_answer_is_an_error_and_the_run_keeps_going(monkeypatch, tmp_path):
    monkeypatch.setattr(run_evals.shutil, "which", lambda name: "claude")
    bad = "import sys; sys.stdout.buffer.write(b'\\xff'); sys.stdout.flush()"
    good = f"import sys; sys.stdout.write({_claude_json('Use 4_World.')!r})"
    real_run_tree = run_evals.run_tree
    monkeypatch.setattr(run_evals, "run_tree", lambda cmd, stdin, timeout:
                        real_run_tree([sys.executable, "-c", bad if stdin == "q1" else good], stdin, timeout))
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    _suite(tmp_path, questions=[
        {"id": "q1", "question": "q1", "must_include": ["4_World"], "verified": "x"},
        {"id": "q2", "question": "q2", "must_include": ["4_World"], "verified": "x"},
    ])
    monkeypatch.setattr(run_evals, "QUESTIONS_DIR", tmp_path)
    out = tmp_path / "r.json"
    assert run_evals.main(["--out", str(out), "--update-baseline"]) == 1
    rows = json.loads(out.read_text(encoding="utf-8"))["agents"]["dayz-script-specialist"]["questions"]
    assert rows[0]["error"] and "not valid UTF-8" in rows[0]["failed_checks"][0]
    assert rows[1]["passed"]
    assert not baseline.exists()


def test_interrupted_run_keeps_a_partial_results_file(monkeypatch, tmp_path):
    """Ctrl+C used to end the run with no results file, losing every answer already paid for."""
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    calls = []

    def interrupted_ask(agent, q, timeout, model=None):
        calls.append(q)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return "4_World"
    monkeypatch.setattr(run_evals, "ask", interrupted_ask)
    out = tmp_path / "r.json"
    assert run_evals.main(["--agent", "dayz-script-specialist", "--agent", "dayz-config-specialist",
                           "--out", str(out), "--update-baseline"]) == 130
    assert len(calls) == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["interrupted"] is True
    assert list(data["agents"]) == ["dayz-config-specialist"]
    rows = data["agents"]["dayz-config-specialist"]["questions"]
    assert len(rows) == 2 and data["agents"]["dayz-config-specialist"]["total"] == 2
    assert rows[1] == {"id": rows[1]["id"], "passed": False, "error": True,
                       "failed_checks": ["error: interrupted"], "answer": ""}
    assert json.loads(baseline.read_text(encoding="utf-8")) == {}


def test_results_file_holds_each_answer_before_the_next_question_is_asked(monkeypatch, tmp_path):
    """The results file used to be written only after the last question, so a crash lost every answer."""
    out = tmp_path / "r.json"
    seen = []

    def checking_ask(agent, q, timeout, model=None):
        if seen:
            rows = json.loads(out.read_text(encoding="utf-8"))["agents"]["dayz-script-specialist"]["questions"]
            assert [r["answer"] for r in rows] == seen
        seen.append(f"4_World {len(seen)}")
        return seen[-1]
    monkeypatch.setattr(run_evals, "ask", checking_ask)
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(seen) == data["agents"]["dayz-script-specialist"]["total"] >= 2
    assert not any(r.get("error") for r in data["agents"]["dayz-script-specialist"]["questions"])
    assert data["claude_version"] == "9.9.9 (Claude Code)"
    assert not out.with_name(out.name + ".tmp").exists()


def test_unexpected_exception_is_an_error_row_and_the_run_keeps_going(monkeypatch):
    """Only RuntimeError, OSError and TimeoutExpired used to be caught; anything else ended the run."""
    def fake_ask(agent, question, timeout, model=None):
        if question == "q1":
            raise ValueError("boom")
        return "Use 4_World."
    monkeypatch.setattr(run_evals, "ask", fake_ask)
    suite = {"agent": "a", "questions": [
        {"id": "q1", "question": "q1", "must_include": ["4_World"]},
        {"id": "q2", "question": "q2", "must_include": ["4_World"]},
    ]}
    rows = run_evals.run([suite], timeout=5)["agents"]["a"]["questions"]
    assert rows[0]["error"] and rows[0]["failed_checks"] == ["error: boom"]
    assert rows[1]["passed"]


def test_cite_matches_a_short_cite_inside_a_longer_answer_path_as_documented():
    q = {"id": "c", "must_include": [], "cite": "3_game/entities/entityai.c"}
    assert run_evals.score(r"See P:\scripts\3_Game\Entities\EntityAI.c:120", q)["passed"]
    long_cite = {"id": "c", "must_include": [], "cite": r"P:\scripts\3_game\entities\entityai.c"}
    assert not run_evals.score("See 3_game/entities/entityai.c", long_cite)["passed"]


def test_run_scores_and_counts_errors_as_failures(monkeypatch):
    answers = {"q1": "Use 4_World.", "q2": RuntimeError("claude exited 1")}

    def fake_ask(agent, question, timeout, model=None):
        value = answers[question]
        if isinstance(value, Exception):
            raise value
        return value
    monkeypatch.setattr(run_evals, "ask", fake_ask)
    suite = {"agent": "a", "questions": [
        {"id": "q1", "question": "q1", "must_include": ["4_World"]},
        {"id": "q2", "question": "q2", "must_include": ["x"]},
    ]}
    result = run_evals.run([suite], timeout=5)["agents"]["a"]
    assert (result["score"], result["total"]) == (1, 2)
    assert result["questions"][1]["failed_checks"][0].startswith("error:")


def test_run_fails_a_question_whose_unchanged_file_was_edited(monkeypatch, tmp_path):
    monkeypatch.setattr(run_evals, "REPO", tmp_path)
    target = tmp_path / "gated.layout"
    target.write_text("FrameWidgetClass root {\n}\n", encoding="utf-8")

    def editing_ask(agent, question, timeout, model=None):
        if question == "edit":
            target.write_text("changed", encoding="utf-8")
        elif question == "delete":
            target.unlink()
        return "FAIL line 1"
    monkeypatch.setattr(run_evals, "ask", editing_ask)
    suite = {"agent": "a", "questions": [
        {"id": "keep", "question": "keep", "must_include": ["FAIL"], "unchanged": ["gated.layout"]},
        {"id": "edit", "question": "edit", "must_include": ["FAIL"], "unchanged": ["gated.layout"]},
        {"id": "delete", "question": "delete", "must_include": ["FAIL"], "unchanged": ["gated.layout"]},
    ]}
    rows = run_evals.run([suite], timeout=5)["agents"]["a"]["questions"]
    assert rows[0]["passed"]
    assert not rows[1]["passed"]
    assert rows[1]["failed_checks"] == ["changed: gated.layout"]
    assert not rows[2]["passed"]
    assert rows[2]["failed_checks"] == ["changed: gated.layout"]


def test_validate_rejects_missing_unchanged_file(tmp_path):
    questions = [{"id": "q", "question": "x", "must_include": ["a"], "unchanged": ["evals/nope.layout"]}]
    _, problems = run_evals.validate(_suite(tmp_path, questions=questions))
    assert any("unchanged file evals/nope.layout does not exist" in p for p in problems)


def test_dry_run_asks_nothing(capsys):
    suites, problems = run_evals.load_suites(None)
    assert not problems
    assert run_evals.main(["--dry-run"]) == 0
    lines = capsys.readouterr().out.splitlines()
    expected = [f"would ask: claude -p --agent {s['agent']}  [{q['id']}]" for s in suites for q in s["questions"]]
    assert expected
    assert [line for line in lines if line.startswith("would ask: ")] == expected
    total = sum(len(s["questions"]) for s in suites)
    assert lines[-1] == f"{total} questions for {len(suites)} agents; question files are valid."


def test_main_passes_model_and_timeout_to_ask(monkeypatch, tmp_path):
    """Without this, --model opus could quietly run the CLI default while the baseline still records 'opus'."""
    calls = []

    def recording_ask(agent, q, timeout, model=None):
        calls.append((agent, timeout, model))
        return ""
    monkeypatch.setattr(run_evals, "ask", recording_ask)
    out = tmp_path / "r.json"
    assert run_evals.main(["--agent", "dayz-script-specialist", "--model", "opus", "--timeout", "7",
                           "--out", str(out)]) == 0
    assert calls
    assert set(calls) == {("dayz-script-specialist", 7, "opus")}
    assert json.loads(out.read_text(encoding="utf-8"))["model"] == "opus"


def test_unknown_agent_is_an_input_error():
    assert run_evals.main(["--dry-run", "--agent", "dayz-nobody"]) == 2


def test_main_writes_results_file(monkeypatch, tmp_path):
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "")
    out = tmp_path / "results.json"
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["agents"]["dayz-script-specialist"]["total"] >= 5


# Gating

def test_compare_flags_only_drops():
    results = {"agents": {"a": {"score": 4, "total": 5}, "b": {"score": 5, "total": 5}, "c": {"score": 1, "total": 1}}}
    baseline = {"a": {"score": 5}, "b": {"score": 4}}
    assert run_evals.compare(results, baseline) == ["a: 4/5 is below the baseline 5"]


def test_baseline_check_fails_for_an_agent_with_no_baseline():
    results = {"agents": {"a": {"score": 5, "total": 5}, "c": {"score": 1, "total": 1}}}
    baseline = {"a": {"score": 5}}
    assert run_evals.compare(results, baseline, require_baseline=True) == [
        "c: no baseline entry; record one with --update-baseline"]


def test_baseline_gate_fails_without_an_entry_but_update_records_it(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "")
    args = ["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json")]
    assert run_evals.main(args + ["--baseline"]) == 1
    assert run_evals.main(args + ["--update-baseline"]) == 0
    assert run_evals.main(args + ["--baseline"]) == 0


def test_baseline_gate_exit_codes(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "")
    out = str(tmp_path / "r.json")
    args = ["--agent", "dayz-script-specialist", "--out", out]

    baseline.write_text(json.dumps({"dayz-script-specialist": {"score": 0, "total": 5}}), encoding="utf-8")
    assert run_evals.main(args + ["--baseline"]) == 0

    baseline.write_text(json.dumps({"dayz-script-specialist": {"score": 3, "total": 5}}), encoding="utf-8")
    assert run_evals.main(args + ["--baseline"]) == 1
    assert run_evals.main(args + ["--update-baseline"]) == 1
    assert json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]["score"] == 3


def test_update_baseline_records_raised_score(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "4_World")
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"),
                           "--update-baseline"]) == 0
    assert json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]["score"] >= 1


def test_shipped_baseline_covers_known_agents():
    baseline = json.loads(run_evals.BASELINE.read_text(encoding="utf-8"))
    for agent, entry in baseline.items():
        assert (run_evals.QUESTIONS_DIR / f"{agent}.json").exists()
        assert 0 <= entry["score"] <= entry["total"]


def test_shipped_baseline_has_every_question_file():
    baseline = json.loads(run_evals.BASELINE.read_text(encoding="utf-8"))
    missing = [p.stem for p in sorted(run_evals.QUESTIONS_DIR.glob("*.json")) if p.stem not in baseline]
    assert not missing, f"no baseline for {missing}; run scripts\\dev\\evals.bat --agent <name> --update-baseline"


def test_shipped_baseline_entries_record_passed_questions():
    """compare() checks lost questions only for entries with a "passed" list; without it that check is dead."""
    baseline = json.loads(run_evals.BASELINE.read_text(encoding="utf-8"))
    for agent, entry in baseline.items():
        assert "passed" in entry, f"{agent}: baseline entry has no passed list; rerun with --update-baseline"
        data = json.loads((run_evals.QUESTIONS_DIR / f"{agent}.json").read_text(encoding="utf-8"))
        ids = {q["id"] for q in data["questions"]}
        assert set(entry["passed"]) <= ids, f"{agent}: passed names unknown questions {set(entry['passed']) - ids}"
        assert len(set(entry["passed"])) == entry["score"], f"{agent}: passed list does not match the score"
        assert entry["total"] == len(ids), f"{agent}: total {entry['total']} != {len(ids)} questions"


def test_shipped_baseline_entries_record_what_produced_them():
    """scores_of() stamps every entry it writes; an entry without the stamp was not recorded by a real run,
    and drop_report would print 'not recorded' for it, hiding whether a drop came with a model or CLI change."""
    baseline = json.loads(run_evals.BASELINE.read_text(encoding="utf-8"))
    for agent, entry in baseline.items():
        missing = [k for k in ("recorded", "model", "claude_version") if not entry.get(k)]
        assert not missing, f"{agent}: baseline entry lacks {missing}; rerun with --agent {agent} --update-baseline"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["recorded"]), f"{agent}: recorded is not a date"


def _results(agent, passed, failed):
    rows = [{"id": i, "passed": True} for i in passed] + [{"id": i, "passed": False} for i in failed]
    return {"agents": {agent: {"score": len(passed), "total": len(rows), "questions": rows}}}


def test_compare_catches_swapped_questions_at_the_same_score():
    """A run that passes as many questions as the baseline, but different ones, must not pass the gate."""
    baseline = {"a": {"score": 2, "total": 3, "passed": ["q1", "q2"]}}
    assert run_evals.compare(_results("a", ["q2", "q3"], ["q1"]), baseline) == ["a: no longer passes q1"]
    assert run_evals.compare(_results("a", ["q1", "q2", "q3"], []), baseline) == []


def test_baseline_gate_fails_when_a_passed_question_now_fails(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    data, _ = run_evals.validate(run_evals.QUESTIONS_DIR / "dayz-script-specialist.json")
    ids = [q["id"] for q in data["questions"]]
    # The baseline says the first question passed; this run passes the second one instead.
    baseline.write_text(json.dumps({"dayz-script-specialist": {"score": 1, "total": len(ids), "passed": [ids[0]]}}),
                        encoding="utf-8")
    by_text = {q["question"]: q for q in data["questions"]}
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None:
                        " ".join(by_text[q]["must_include"]) + " " + by_text[q].get("cite", "")
                        if by_text[q]["id"] == ids[1] else "")
    args = ["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json")]
    assert run_evals.main(args + ["--baseline"]) == 1
    assert run_evals.main(args + ["--update-baseline"]) == 1
    assert json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]["passed"] == [ids[0]]


def test_update_baseline_records_the_passed_questions(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "")
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"),
                           "--update-baseline"]) == 0
    entry = json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]
    assert entry["passed"] == [] and entry["score"] == 0


def test_update_baseline_stamps_date_model_and_claude_version(monkeypatch, tmp_path):
    """Without the stamp a later drop cannot be told apart from a model or CLI change."""
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "")
    args = ["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"), "--update-baseline"]
    assert run_evals.main(args + ["--model", "opus"]) == 0
    entry = json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]
    assert entry["model"] == "opus"
    assert entry["claude_version"] == "9.9.9 (Claude Code)"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["recorded"])
    assert run_evals.main(args) == 0
    assert json.loads(baseline.read_text(encoding="utf-8"))["dayz-script-specialist"]["model"] == "claude CLI default"
    results = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert results["claude_version"] == "9.9.9 (Claude Code)"


def test_failed_baseline_check_names_what_produced_the_baseline_and_the_run(monkeypatch, tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "")
    baseline.write_text(json.dumps({"dayz-script-specialist": {
        "score": 3, "total": 5, "recorded": "2026-01-02", "model": "sonnet", "claude_version": "1.0.0"}}),
        encoding="utf-8")
    args = ["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"), "--model", "haiku"]
    assert run_evals.main(args + ["--baseline"]) == 1
    err = capsys.readouterr().err
    assert "baseline: recorded 2026-01-02, model sonnet, claude 1.0.0" in err
    assert re.search(r"this run: recorded \d{4}-\d{2}-\d{2}, model haiku, claude 9\.9\.9 \(Claude Code\)", err)
    assert run_evals.main(args + ["--update-baseline"]) == 1
    assert "baseline: recorded 2026-01-02, model sonnet" in capsys.readouterr().err


def test_failed_check_says_not_recorded_for_an_old_entry():
    results = {"run_at": "2026-03-04T05:06:07", "model": "opus", "claude_version": "2.0.0", "agents": {}}
    lines = run_evals.drop_report(["a: 1/5 is below the baseline 5"], results, {"a": {"score": 5}})
    assert lines == ["a: 1/5 is below the baseline 5",
                     "  baseline: recorded unknown date, model not recorded, claude not recorded",
                     "  this run: recorded 2026-03-04, model opus, claude 2.0.0"]


@pytest.mark.parametrize("which, proc, expected", [
    (None, None, None),
    ("claude", subprocess.CompletedProcess([], 0, "2.1.400 (Claude Code)\n", ""), "2.1.400 (Claude Code)"),
    ("claude", subprocess.CompletedProcess([], 1, "", "boom"), None),
    ("claude", OSError("gone"), None),
])
def test_claude_version(monkeypatch, which, proc, expected):
    monkeypatch.undo()
    monkeypatch.setattr(run_evals.shutil, "which", lambda name: which)

    def fake_run(cmd, **kwargs):
        assert cmd[1:] == ["--version"]
        if isinstance(proc, Exception):
            raise proc
        return proc
    monkeypatch.setattr(run_evals.subprocess, "run", fake_run)
    assert run_evals.claude_version() == expected


def test_update_baseline_refuses_a_run_where_claude_is_missing(monkeypatch, tmp_path):
    """Without the claude CLI every question errors; that must not become a first baseline of 0."""
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals.shutil, "which", lambda name: None)
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"),
                           "--update-baseline"]) == 1
    assert json.loads(baseline.read_text(encoding="utf-8")) == {}


def test_update_baseline_refuses_when_one_question_times_out(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    calls = []

    def flaky_ask(agent, q, timeout, model=None):
        calls.append(q)
        if len(calls) == 2:
            raise subprocess.TimeoutExpired("claude", timeout)
        return ""
    monkeypatch.setattr(run_evals, "ask", flaky_ask)
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"),
                           "--update-baseline"]) == 1
    assert not baseline.exists()


def _shipped_question(agent, qid):
    data = json.loads((run_evals.REPO / "evals" / "questions" / f"{agent}.json").read_text(encoding="utf-8"))
    return next(q for q in data["questions"] if q["id"] == qid)


@pytest.mark.parametrize("answer", [
    "PlaySoundSet bails out because the sound is already set; call StopSoundSet first.",
    "m_EngineLoop still holds the normal loop, so PlaySoundSet returns true. Call StopSoundSet(m_EngineLoop) first.",
    "The EffectSound is not null, so it returns early. Fix: StopSoundSet, then PlaySoundSetLoop.",
])
def test_restart_loop_question_accepts_correct_wordings(answer):
    """The old two-lookahead regex failed a correct 'already set ... StopSoundSet' answer."""
    q = _shipped_question("dayz-audio-fx-specialist", "restart-loop-needs-stop")
    assert run_evals.score(answer, q)["passed"]


def test_restart_loop_question_rejects_an_answer_without_stop():
    q = _shipped_question("dayz-audio-fx-specialist", "restart-loop-needs-stop")
    assert not run_evals.score("The sound is already set, so use a different sound set name.", q)["passed"]


def test_shader_range_question_does_not_score_the_unverified_unit():
    """No P: file states the unit of CfgSoundShaders range, so the question must not score one."""
    q = _shipped_question("dayz-audio-fx-specialist", "shader-range-unit")
    checks = " ".join(q["must_include"] + q.get("must_not_include", []))
    assert "met" not in checks and "unverified" in q["verified"]
    assert run_evals.score("The range key sets it, for example range=100.", q)["passed"]


@pytest.mark.parametrize("answer", [
    "Instead of multiplying by a wet factor, it returns -0.15 outright (miscgameplayfunctions.c:1381).",
    "It does not multiply heatIsolation; the drenched branch of miscgameplayfunctions.c returns -0.15 directly.",
    "Vanilla returns -0.15 and no multiplication happens, see miscgameplayfunctions.c.",
])
def test_drenched_question_accepts_correct_wordings(answer):
    """The old 'multipl ... 0.15' pattern failed a correct 'instead of multiplying ... returns -0.15' answer."""
    q = _shipped_question("dayz-wearables-specialist", "drenched-insulation")
    assert run_evals.score(answer, q)["passed"]


@pytest.mark.parametrize("answer", [
    "It multiplies it by -0.15, see miscgameplayfunctions.c.",
    "0.9 * -0.15 gives the value, see miscgameplayfunctions.c; -0.15 is the factor.",
    "heatIsolation is multiplied by -0.15 per miscgameplayfunctions.c.",
    "It uses a multiplier of -0.15 (miscgameplayfunctions.c).",
])
def test_drenched_question_rejects_the_multiplier_claim(answer):
    q = _shipped_question("dayz-wearables-specialist", "drenched-insulation")
    assert not run_evals.score(answer, q)["passed"]


# Renamed questions and Ctrl+C outside ask()

def test_compare_ignores_passed_ids_no_longer_in_the_question_file():
    """A renamed or removed question used to count as lost, so --update-baseline refused forever."""
    baseline = {"a": {"score": 2, "total": 2, "passed": ["old", "q2"]}}
    assert run_evals.compare(_results("a", ["new", "q2"], []), baseline) == []
    assert run_evals.compare(_results("a", ["q2"], []), baseline) == []
    assert run_evals.compare(_results("a", ["new"], ["q2"]), baseline) == ["a: no longer passes q2"]


def test_update_baseline_records_a_renamed_question(monkeypatch, tmp_path):
    agent = "dayz-script-specialist"
    questions = tmp_path / "questions"
    questions.mkdir()
    _suite(questions, agent, [{"id": "new", "question": "Which layer?", "must_include": ["4_World"],
                               "verified": "P:/scripts/4_World"}])
    monkeypatch.setattr(run_evals, "QUESTIONS_DIR", questions)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({agent: {"score": 1, "total": 1, "passed": ["old"]}}), encoding="utf-8")
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "4_World")
    assert run_evals.main(["--agent", agent, "--out", str(tmp_path / "r.json"), "--update-baseline"]) == 0
    entry = json.loads(baseline.read_text(encoding="utf-8"))[agent]
    assert entry["passed"] == ["new"] and entry["score"] == 1


def _interrupt(*args, **kwargs):
    raise KeyboardInterrupt


def test_ctrl_c_while_hashing_unchanged_files_exits_130(monkeypatch, tmp_path):
    """file_hashes() ran outside the try block, so Ctrl+C there ended in a traceback."""
    monkeypatch.setattr(run_evals, "file_hashes", _interrupt)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "4_World")
    out = tmp_path / "r.json"
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(out)]) == 130
    data = json.loads(out.read_text(encoding="utf-8"))
    rows = data["agents"]["dayz-script-specialist"]["questions"]
    assert data["interrupted"] is True and len(rows) == 1 and rows[0]["failed_checks"] == ["error: interrupted"]


def test_ctrl_c_while_saving_results_exits_130(monkeypatch, tmp_path):
    """save() ran outside the try block, so Ctrl+C while writing the results file ended in a traceback."""
    real_write = run_evals.write_results
    calls = []

    def write_once_interrupted(out, results):
        calls.append(out)
        if len(calls) == 1:
            raise KeyboardInterrupt
        real_write(out, results)
    monkeypatch.setattr(run_evals, "write_results", write_once_interrupted)
    monkeypatch.setattr(run_evals, "ask", lambda agent, q, timeout, model=None: "4_World")
    out = tmp_path / "r.json"
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(out)]) == 130
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["interrupted"] is True and len(data["agents"]["dayz-script-specialist"]["questions"]) == 1


def test_ctrl_c_before_the_first_question_exits_130(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run_evals, "BASELINE", baseline)
    monkeypatch.setattr(run_evals, "run_info", _interrupt)
    assert run_evals.main(["--agent", "dayz-script-specialist", "--out", str(tmp_path / "r.json"),
                           "--update-baseline"]) == 130
    assert json.loads(baseline.read_text(encoding="utf-8")) == {}
