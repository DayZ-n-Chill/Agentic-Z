"""Tests for the evals runner. The claude call is always mocked; nothing here asks a real agent.

Run with: py -m pytest scripts/dev/test_run_evals.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
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


def _suite(tmp_path, agent="dayz-script-specialist", questions=None):
    questions = questions or [{"id": "q1", "question": "Which layer?", "must_include": ["4_World"]}]
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


def test_every_question_file_is_valid():
    suites, problems = run_evals.load_suites(None)
    assert problems == []
    assert {s["agent"] for s in suites} >= set(FIRST_AGENTS)


# Running

def test_ask_builds_read_only_claude_command(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["input"] = cmd, kwargs["input"]
        return subprocess.CompletedProcess(cmd, 0, stdout="answer", stderr="")
    monkeypatch.setattr(run_evals.shutil, "which", lambda name: "claude")
    monkeypatch.setattr(run_evals.subprocess, "run", fake_run)
    assert run_evals.ask("dayz-mod-reviewer", "Q?", timeout=5) == "answer"
    cmd = seen["cmd"]
    assert cmd[:4] == ["claude", "-p", "--agent", "dayz-mod-reviewer"]
    tools = cmd[cmd.index("--allowedTools") + 1]
    assert "Edit" not in tools.split(",") and "Write" not in tools.split(",")
    assert seen["input"] == "Q?"


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
    monkeypatch.setattr(run_evals.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom"))
    with pytest.raises(RuntimeError, match="boom"):
        run_evals.ask("a", "q", timeout=5)


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
        return "FAIL line 1"
    monkeypatch.setattr(run_evals, "ask", editing_ask)
    suite = {"agent": "a", "questions": [
        {"id": "keep", "question": "keep", "must_include": ["FAIL"], "unchanged": ["gated.layout"]},
        {"id": "edit", "question": "edit", "must_include": ["FAIL"], "unchanged": ["gated.layout"]},
    ]}
    rows = run_evals.run([suite], timeout=5)["agents"]["a"]["questions"]
    assert rows[0]["passed"]
    assert not rows[1]["passed"]
    assert rows[1]["failed_checks"] == ["changed: gated.layout"]


def test_validate_rejects_missing_unchanged_file(tmp_path):
    questions = [{"id": "q", "question": "x", "must_include": ["a"], "unchanged": ["evals/nope.layout"]}]
    _, problems = run_evals.validate(_suite(tmp_path, questions=questions))
    assert any("unchanged file evals/nope.layout does not exist" in p for p in problems)


def test_dry_run_asks_nothing(capsys):
    assert run_evals.main(["--dry-run"]) == 0
    assert "question files are valid" in capsys.readouterr().out


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
