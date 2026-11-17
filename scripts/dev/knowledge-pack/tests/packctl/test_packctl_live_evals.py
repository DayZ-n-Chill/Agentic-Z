from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from packctl.cli import main
from packctl.live_evals import _grade_answer, run_live_eval_case, validate_live_eval_case
from packctl_testlib import require_tree_root


def _valid_case() -> dict[str, object]:
    return {
        "schema_version": 1,
        "case_id": "basebuilding-part-id-cap",
        "family": "persistence",
        "skill_under_test": "dayz-basebuilding",
        "question": (
            "Audit the fixture and finish with a CITATIONS: block containing "
            "one path:line citation per line."
        ),
        "fixtures": {
            "fixture/config.cpp": "first line\nknown line\n",
        },
        "graders": [
            {"type": "contains_all", "values": ["93", "42", "94"]},
            {"type": "regex_any", "patterns": [r"three\s+ints", r"31\s+bits"]},
            {"type": "citations_resolve"},
        ],
        "citation_roots": ["fixture", "pack"],
        "arms": ["with_skill", "without_skill"],
        "runs_per_arm": 5,
        "pass_rule": {
            "min_pass_with_skill": 0.8,
            "max_pass_without_skill": 0.2,
        },
        "min_discrimination": 0.6,
    }


def _write_case(tmp_path: Path, value: dict[str, object]) -> Path:
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(value, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    return case_path


def test_live_schema_accepts_valid_case(tmp_path: Path) -> None:
    assert validate_live_eval_case(_write_case(tmp_path, _valid_case())) == []


@pytest.mark.parametrize("forbidden", ["response", "expected_verdict"])
def test_live_schema_rejects_tautological_answer_fields(
    tmp_path: Path,
    forbidden: str,
) -> None:
    value = _valid_case()
    value[forbidden] = "forbidden"

    findings = validate_live_eval_case(_write_case(tmp_path, value))

    assert [item["code"] for item in findings] == ["LIVE-EVAL-SCHEMA-INVALID"]


def test_live_schema_rejects_two_runs_per_arm(tmp_path: Path) -> None:
    value = _valid_case()
    value["runs_per_arm"] = 2

    findings = validate_live_eval_case(_write_case(tmp_path, value))

    assert [item["code"] for item in findings] == ["LIVE-EVAL-SCHEMA-INVALID"]


def test_live_schema_requires_exact_arm_pair(tmp_path: Path) -> None:
    value = _valid_case()
    value["arms"] = ["without_skill", "with_skill"]

    findings = validate_live_eval_case(_write_case(tmp_path, value))

    assert [item["code"] for item in findings] == ["LIVE-EVAL-SCHEMA-INVALID"]



_PASS_ANSWER = (
    "The cap is 93; id 42 is duplicated and id 94 is out of range. "
    "The mechanism uses three ints.\n"
    "CITATIONS:\n"
    "fixture/config.cpp:2 \"known line\""
)
_FAIL_ANSWER = (
    "I cannot determine the invariant.\n"
    "CITATIONS:\n"
    "fixture/config.cpp:2 \"known line\""
)


def _write_fake_runner(
    tmp_path: Path,
    with_answers: list[str],
    without_answers: list[str],
    *,
    raw_stdout: str | None = None,
    contaminate_without_skill: bool = False,
) -> Path:
    runner = tmp_path / "fake_runner.py"
    scripted = json.dumps(
        {
            "with_skill": with_answers,
            "without_skill": without_answers,
        },
        ensure_ascii=False,
    )
    source = f'''\
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.load(sys.stdin)
raw_stdout = {raw_stdout!r}
if raw_stdout is not None:
    print(raw_stdout)
    raise SystemExit(0)
if {contaminate_without_skill!r} and not payload["skill_mounted"]:
    leaked = Path(payload["workspace"]) / ".claude" / "skills" / "leaked" / "SKILL.md"
    leaked.parent.mkdir(parents=True, exist_ok=True)
    leaked.write_text("leak", encoding="utf-8")
answers = {scripted}
arm = "with_skill" if payload["skill_mounted"] else "without_skill"
print(json.dumps({{
    "answer": answers[arm][payload["run_index"]],
    "model": "fake-model",
    "meta": {{"effort": "low"}},
}}, ensure_ascii=False))
'''
    runner.write_text(source, encoding="utf-8", newline="\n")
    return runner


def _run_scripted_case(
    tmp_path: Path,
    with_answers: list[str],
    without_answers: list[str],
    *,
    raw_stdout: str | None = None,
    contaminate_without_skill: bool = False,
) -> dict[str, object]:
    root = tmp_path / "pack"
    skill = root / "skills" / "dayz-basebuilding" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# test skill\n", encoding="utf-8", newline="\n")
    case_path = _write_case(tmp_path, _valid_case())
    runner = _write_fake_runner(
        tmp_path,
        with_answers,
        without_answers,
        raw_stdout=raw_stdout,
        contaminate_without_skill=contaminate_without_skill,
    )
    return run_live_eval_case(root, case_path, runner, tmp_path / "reports")


def test_case_passing_in_both_arms_is_vacuous_and_does_not_count(
    tmp_path: Path,
) -> None:
    summary = _run_scripted_case(
        tmp_path,
        [_PASS_ANSWER] * 5,
        [_PASS_ANSWER] * 5,
    )

    assert summary["discrimination_verdict"] == "VACUOUS"
    assert summary["counts_as_evidence"] is False
    assert summary["arms"]["with_skill"]["pass_rate"] == 1.0
    assert summary["arms"]["without_skill"]["pass_rate"] == 1.0
    finding_item = next(
        item
        for item in summary["findings"]
        if item["code"] == "LIVE-EVAL-CASE-NOT-DISCRIMINATING"
    )
    assert finding_item["message"] == (
        "The case passes without the skill, so it measures nothing."
    )
    assert finding_item["evidence"] == "with=1.0 without=1.0"


def test_case_with_five_to_zero_split_is_discriminating(tmp_path: Path) -> None:
    summary = _run_scripted_case(
        tmp_path,
        [_PASS_ANSWER] * 5,
        [_FAIL_ANSWER] * 5,
    )

    assert summary["discrimination_verdict"] == "DISCRIMINATING"
    assert summary["counts_as_evidence"] is True
    assert summary["arms"]["with_skill"]["pass_rate"] == 1.0
    assert summary["arms"]["without_skill"]["pass_rate"] == 0.0
    summary_path = (
        tmp_path
        / "reports"
        / "basebuilding-part-id-cap"
        / "summary.json"
    )
    assert json.loads(summary_path.read_text(encoding="utf-8")) == summary


def test_case_with_two_of_five_skill_runs_is_inconclusive(tmp_path: Path) -> None:
    summary = _run_scripted_case(
        tmp_path,
        [_PASS_ANSWER, _PASS_ANSWER, _FAIL_ANSWER, _FAIL_ANSWER, _FAIL_ANSWER],
        [_FAIL_ANSWER] * 5,
    )

    assert summary["discrimination_verdict"] == "INCONCLUSIVE"
    assert summary["counts_as_evidence"] is False
    assert summary["arms"]["with_skill"]["pass_rate"] == 0.4
    assert summary["arms"]["without_skill"]["pass_rate"] == 0.0


def _citation_result(tmp_path: Path, answer: str) -> dict[str, object]:
    root = tmp_path / "pack"
    workspace = tmp_path / "workspace"
    fixture = workspace / "fixture" / "config.cpp"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("first line\nknown line\n", encoding="utf-8", newline="\n")
    results = _grade_answer(_valid_case(), answer, root, workspace)
    return next(result for result in results if result["type"] == "citations_resolve")


def test_citations_reject_nonexistent_path(tmp_path: Path) -> None:
    result = _citation_result(
        tmp_path,
        'CITATIONS:\nfixture/missing.cpp:1 "known line"',
    )

    assert result["passed"] is False
    assert result["evidence"][0]["reason"] == "unresolved"


def test_citations_reject_line_out_of_range(tmp_path: Path) -> None:
    result = _citation_result(
        tmp_path,
        "CITATIONS:\nfixture/config.cpp:99",
    )

    assert result["passed"] is False
    assert result["evidence"][0]["reason"] == "line-out-of-range"


def test_citations_reject_mismatched_quoted_text(tmp_path: Path) -> None:
    result = _citation_result(
        tmp_path,
        'CITATIONS:\nfixture/config.cpp:2 "invented line"',
    )

    assert result["passed"] is False
    assert result["evidence"][0]["reason"] == "quote-mismatch"


def test_citations_require_citations_block(tmp_path: Path) -> None:
    result = _citation_result(tmp_path, "No citations were supplied.")

    assert result["passed"] is False
    assert result["evidence"][0]["reason"] == "missing-block"


def test_without_skill_tree_contamination_rejects_case(tmp_path: Path) -> None:
    summary = _run_scripted_case(
        tmp_path,
        [_PASS_ANSWER] * 5,
        [_FAIL_ANSWER] * 5,
        contaminate_without_skill=True,
    )

    assert summary["counts_as_evidence"] is False
    assert summary["discrimination_verdict"] == "INCONCLUSIVE"
    assert "LIVE-EVAL-ARM-CONTAMINATED" in {
        item["code"] for item in summary["findings"]
    }
    without_run = summary["arms"]["without_skill"]["runs"][0]
    assert without_run["skills_tree_sha256_before"] != (
        without_run["skills_tree_sha256_after"]
    )
    assert without_run["passed"] is False


def test_non_json_runner_output_is_a_failed_run_not_a_case_error(
    tmp_path: Path,
) -> None:
    summary = _run_scripted_case(
        tmp_path,
        [_PASS_ANSWER] * 5,
        [_FAIL_ANSWER] * 5,
        raw_stdout="not-json",
    )

    assert summary["case_id"] == "basebuilding-part-id-cap"
    assert summary["counts_as_evidence"] is False
    assert "LIVE-EVAL-RUNNER-INVALID" in {
        item["code"] for item in summary["findings"]
    }
    all_runs = [
        run
        for arm in summary["arms"].values()
        for run in arm["runs"]
    ]
    assert len(all_runs) == 10
    assert all(run["response"].strip() == "not-json" for run in all_runs)
    assert all(run["passed"] is False for run in all_runs)


def test_eval_live_subcommand_runs_case_and_writes_summary(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    skill = root / "skills" / "dayz-basebuilding" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# test skill\n", encoding="utf-8", newline="\n")
    case_path = _write_case(tmp_path, _valid_case())
    runner = _write_fake_runner(
        tmp_path,
        [_PASS_ANSWER] * 5,
        [_FAIL_ANSWER] * 5,
    )
    report_root = tmp_path / "reports"

    exit_code = main(
        [
            "eval",
            "live",
            "--root",
            str(root),
            "--case",
            str(case_path),
            "--runner",
            str(runner),
            "--report",
            str(report_root),
        ]
    )

    assert exit_code == 0
    summary = json.loads(
        (
            report_root
            / "basebuilding-part-id-cap"
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["discrimination_verdict"] == "DISCRIMINATING"


def test_seed_case_is_valid_and_fixture_does_not_reveal_invariant() -> None:
    root = require_tree_root("evals/live/schema.json")
    case_path = root / "evals" / "live" / "cases" / "basebuilding-part-id-cap.json"

    assert validate_live_eval_case(case_path) == []
    case = json.loads(case_path.read_text(encoding="utf-8"))
    fixture = case["fixtures"]["fixture/config.cpp"]
    ids = [int(value) for value in re.findall(r"\bid\s*=\s*(\d+)\s*;", fixture)]

    assert "93" not in fixture
    assert "syncparts" not in fixture.lower()
    assert "bit" not in fixture.lower()
    assert len(ids) != len(set(ids))
    assert any(value > 93 for value in ids)


def test_every_shipped_case_is_valid_and_does_not_leak_its_graders() -> None:
    root = require_tree_root("evals/live/schema.json")
    case_dir = root / "evals" / "live" / "cases"
    cases = sorted(case_dir.glob("*.json"))

    assert cases, "no live eval cases are shipped"
    for case_path in cases:
        assert validate_live_eval_case(case_path) == [], case_path.name
        case = json.loads(case_path.read_text(encoding="utf-8"))
        assert case["case_id"] == case_path.stem, case_path.name
        # A contains_all token printed in the question would let an answer pass
        # by echoing the prompt, which is the tautology the seed case guards
        # against by hand.
        question = case["question"]
        for grader in case["graders"]:
            for value in grader.get("values", []):
                assert value not in question, f"{case_path.name}: {value}"


def test_claude_code_adapter_builds_verified_isolated_command() -> None:
    import importlib.util

    root = require_tree_root("evals/live/schema.json")
    adapter_path = root / "evals" / "live" / "runners" / "claude-code.py"
    spec = importlib.util.spec_from_file_location("live_eval_claude_code", adapter_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    command = module._claude_command(
        "claude",
        model="model-id",
        effort="high",
        prompt="Audit the fixture.",
    )

    assert command == [
        "claude",
        "-p",
        "Audit the fixture.",
        "--bare",
        "--model",
        "model-id",
        "--effort",
        "high",
        "--settings",
        "{}",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format",
        "json",
    ]
    assert "--max-turns" not in command
    assert "--skill" not in command
