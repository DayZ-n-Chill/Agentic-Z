"""Tests for the eval material imported with the knowledge pack.

Covers evals/cases/ (mechanical cases with canned answers), evals/live/ (live
cases, their schema and the Claude Code adapter) and the link from every
imported case to the question it became in evals/questions/. Nothing here
calls claude.

Run with: py -m pytest scripts/dev/test_kp_evals.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EVALS = REPO / "evals"
CASES = sorted((EVALS / "cases").glob("*.json"))
LIVE_CASES = sorted((EVALS / "live" / "cases").glob("*.json"))
ADAPTER = EVALS / "live" / "runners" / "claude-code.py"

# Each imported case and the question ids it became. stardz-negatives held six
# claims, so it became six questions.
CASE_QUESTIONS = {
    "api-enforce": ("dayz-script-specialist", ["api-enforce"]),
    "api-index-liveness": ("dayz-script-specialist", ["api-index-liveness"]),
    "stardz-negatives": ("dayz-script-specialist", [
        "stardz-negatives-autoptr", "stardz-negatives-overload", "stardz-negatives-managed",
        "stardz-negatives-jsonloadfile", "stardz-negatives-ondrop", "stardz-negatives-dabs"]),
    "persistence": ("dayz-persistence-specialist", ["persistence"]),
    "persistence-deprecated-api": ("dayz-persistence-specialist", ["persistence-deprecated-api"]),
    "persistence-migration-rollback": ("dayz-persistence-specialist", ["persistence-migration-rollback"]),
    "persistence-mod-version": ("dayz-persistence-specialist", ["persistence-mod-version"]),
    "basebuilding-part-id-cap": ("dayz-persistence-specialist", ["basebuilding-part-id-cap"]),
    "ui-layout": ("dayz-ui-specialist", ["ui-layout"]),
    "build-artifact-postcondition": ("dayz-build-checker", ["build-artifact-postcondition"]),
    "companion-lifecycle-authority": ("dayz-ingame-tester", ["companion-lifecycle-authority"]),
    "physics-bake-then-remove": ("dayz-animation-specialist", ["physics-bake-then-remove"]),
    "easing-overshoot-audit": ("dayz-animation-specialist", ["easing-overshoot-audit"]),
    "video-output-gate-order": ("dayz-animation-specialist", ["video-output-gate-order"]),
    "txa-add-spine-up-export": ("dayz-animation-specialist", ["txa-add-spine-up-export"]),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _adapter():
    spec = importlib.util.spec_from_file_location("kp_live_eval_claude_code", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _questions(agent: str) -> dict[str, dict]:
    return {q["id"]: q for q in _load(EVALS / "questions" / f"{agent}.json")["questions"]}


# Mechanical cases

def test_mechanical_cases_are_shipped():
    assert len(CASES) == 10


@pytest.mark.parametrize("path", CASES, ids=lambda p: p.stem)
def test_mechanical_case_has_the_schema_fields(path):
    schema = _load(EVALS / "schema.json")
    case = _load(path)
    assert set(case) == set(schema["required"])
    assert case["case_id"] == path.stem
    assert case["family"] in schema["properties"]["family"]["enum"]
    assert len(case["variants"]) >= 2
    variant_fields = set(schema["properties"]["variants"]["items"]["required"])
    for variant in case["variants"]:
        assert set(variant) == variant_fields
        assert set(case["required_evidence"]) <= set(variant["evidence"])


def _holds(assertion: dict, response: str) -> bool:
    kind, value = assertion["type"], assertion["value"]
    if kind == "contains":
        return value in response
    if kind == "not_contains":
        return value not in response
    return re.search(value, response) is not None


@pytest.mark.parametrize("path", CASES, ids=lambda p: p.stem)
def test_mechanical_case_variants_get_their_expected_verdict(path):
    """A variant passes when every assertion holds for its canned response."""
    case = _load(path)
    for variant in case["variants"]:
        verdict = "PASS" if all(_holds(a, variant["response"]) for a in case["assertions"]) else "FAIL"
        assert verdict == variant["expected_verdict"], variant["variant_id"]


# Live cases

def test_live_cases_are_shipped():
    assert len(LIVE_CASES) == 5


@pytest.mark.parametrize("path", LIVE_CASES, ids=lambda p: p.stem)
def test_live_case_is_well_formed_and_does_not_leak_its_graders(path):
    schema = _load(EVALS / "live" / "schema.json")
    case = _load(path)
    assert set(case) == set(schema["required"])
    assert case["case_id"] == path.stem
    assert "CITATIONS:" in case["question"]
    assert case["arms"] == ["with_skill", "without_skill"]
    assert case["runs_per_arm"] >= 3
    assert all(name.startswith("fixture/") for name in case["fixtures"])
    for grader in case["graders"]:
        assert grader["type"] in {"contains_all", "regex_any", "citations_resolve"}
        for pattern in grader.get("patterns", []):
            re.compile(pattern)
        # A token the question prints would let an answer pass by echoing the question.
        for value in grader.get("values", []):
            assert value not in case["question"], value


def test_part_id_fixture_does_not_reveal_the_limit():
    fixture = _load(EVALS / "live" / "cases" / "basebuilding-part-id-cap.json")["fixtures"]["fixture/config.cpp"]
    ids = [int(v) for v in re.findall(r"\bid\s*=\s*(\d+)\s*;", fixture)]
    assert "93" not in fixture and "syncparts" not in fixture.lower()
    assert len(ids) != len(set(ids)) and any(v > 93 for v in ids)
    # The question for our runner reads the same fixture from evals/fixtures/.
    assert (EVALS / "fixtures" / "dayz-persistence-specialist" / "part_id_cap_config.cpp").read_text(
        encoding="utf-8") == fixture


@pytest.mark.parametrize("path", LIVE_CASES, ids=lambda p: p.stem)
def test_live_case_matches_its_schema(path):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(_load(path), _load(EVALS / "live" / "schema.json"))


@pytest.mark.parametrize("path", CASES, ids=lambda p: p.stem)
def test_mechanical_case_matches_its_schema(path):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(_load(path), _load(EVALS / "schema.json"))


# The Claude Code adapter

def test_adapter_builds_an_isolated_command():
    command = _adapter()._claude_command("claude", model="model-id", effort="high", prompt="Audit the fixture.")
    assert command == [
        "claude", "-p", "Audit the fixture.", "--bare", "--model", "model-id", "--effort", "high",
        "--settings", "{}", "--strict-mcp-config", "--no-session-persistence", "--output-format", "json",
    ]


def test_adapter_checks_its_input():
    adapter = _adapter()
    good = {"prompt": "Q?", "workspace": "w", "skill_mounted": True, "run_index": 0}
    assert adapter._validate_input(dict(good)) == good
    for bad in ({**good, "extra": 1}, {**good, "prompt": " "}, {**good, "workspace": ""},
                {**good, "skill_mounted": 1}, {**good, "run_index": -1}, {**good, "run_index": True}, []):
        with pytest.raises(ValueError):
            adapter._validate_input(bad)


def test_adapter_reads_the_answer_from_claude_json():
    adapter = _adapter()
    assert adapter._answer_from_result({"result": "the answer"}) == "the answer"
    with pytest.raises(ValueError):
        adapter._answer_from_result({"result": None})


def test_adapter_refuses_to_run_without_a_model_and_effort(monkeypatch, capsys):
    adapter = _adapter()

    def refuse(*args, **kwargs):
        raise AssertionError("the adapter must not start claude without a model and an effort")

    monkeypatch.setattr(adapter.subprocess, "run", refuse)
    request = json.dumps({"prompt": "Q?", "workspace": str(REPO), "skill_mounted": False, "run_index": 0})
    monkeypatch.delenv("PACKCTL_LIVE_EVAL_MODEL", raising=False)
    monkeypatch.setenv("PACKCTL_LIVE_EVAL_EFFORT", "high")
    monkeypatch.setattr(adapter.sys, "stdin", io.StringIO(request))
    assert adapter.main() == 2
    monkeypatch.setenv("PACKCTL_LIVE_EVAL_MODEL", "model-id")
    monkeypatch.setenv("PACKCTL_LIVE_EVAL_EFFORT", "fastest")
    monkeypatch.setattr(adapter.sys, "stdin", io.StringIO(request))
    assert adapter.main() == 2
    assert "claude-code adapter error: ValueError" in capsys.readouterr().err


# The link to our question format

def test_every_imported_case_is_listed():
    assert {p.stem for p in CASES + LIVE_CASES} == set(CASE_QUESTIONS)


@pytest.mark.parametrize("case_id", sorted(CASE_QUESTIONS))
def test_imported_case_has_its_questions(case_id):
    agent, ids = CASE_QUESTIONS[case_id]
    questions = _questions(agent)
    for qid in ids:
        assert qid in questions, f"evals/questions/{agent}.json has no question {qid}"
        q = questions[qid]
        assert q["question"].startswith("Answer only, do not edit any file")
        assert q.get("verified") and q.get("must_include")


def test_unrun_imported_questions_are_not_claimed_as_passed_without_a_run():
    """The baseline may list an imported question as passed only after a real run has stamped a newer date."""
    baseline = _load(EVALS / "baseline.json")
    for agent, ids in CASE_QUESTIONS.values():
        entry = baseline[agent]
        claimed = set(entry["passed"]) & set(ids)
        assert not claimed or entry["recorded"] > "2026-11-17", f"{agent}: {sorted(claimed)}"


def test_imported_eval_files_are_english_ascii_text():
    # The multiplication sign sits inside one grader regex, the dash inside two canned evidence lines.
    allowed = {"×", "—"}
    for path in CASES + LIVE_CASES + [ADAPTER, EVALS / "schema.json", EVALS / "live" / "schema.json"]:
        odd = {ch for ch in path.read_text(encoding="utf-8") if ord(ch) > 127} - allowed
        assert not odd, f"{path.name}: {sorted(odd)}"
