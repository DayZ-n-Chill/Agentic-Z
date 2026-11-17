from __future__ import annotations

import json
from pathlib import Path

from packctl_testlib import require_tree_root, write_json

from packctl.evals import run_eval_case, validate_eval_case


def case_value(*, include_evidence: bool = True) -> dict[str, object]:
    evidence = {"answer.txt": "Demo() exists in fixture.c:1\n"} if include_evidence else {}
    return {
        "schema_version": 1,
        "case_id": "eval-api",
        "family": "api",
        "prompt": "Use only the supplied fixture and cite evidence.",
        "fixtures": {
            "fixture.c": "class Demo { void Demo(); }\n",
        },
        "assertions": [
            {
                "assertion_id": "mentions-demo",
                "type": "contains",
                "value": "Demo()",
                "evidence": ["answer.txt"],
            },
            {
                "assertion_id": "rejects-fake",
                "type": "not_contains",
                "value": "FakeApi()",
                "evidence": ["answer.txt"],
            },
        ],
        "grader": {"type": "mechanical"},
        "required_evidence": ["answer.txt"],
        "variants": [
            {
                "variant_id": "current",
                "skill_revision": "skill-current",
                "baseline_revision": "absent",
                "runner_id": "fixture",
                "expected_verdict": "PASS",
                "response": "Use Demo(); verified in fixture.c:1.",
                "evidence": evidence,
                "tokens_input": 11,
                "tokens_output": 7,
            },
            {
                "variant_id": "absent",
                "skill_revision": "absent",
                "baseline_revision": "absent",
                "runner_id": "fixture",
                "expected_verdict": "FAIL",
                "response": "Use FakeApi().",
                "evidence": {"answer.txt": "No source supplied.\n"},
                "tokens_input": 9,
                "tokens_output": 4,
            },
        ],
    }


def test_eval_case_schema_accepts_pilot_contract(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"
    write_json(case_path, case_value())

    assert validate_eval_case(case_path) == []


def test_eval_run_emits_evidence_backed_grading(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"
    output = tmp_path / "run"
    write_json(case_path, case_value())

    report = run_eval_case(case_path, "current", output)

    assert report["verdict"] == "PASS"
    grading = json.loads((output / "grading.json").read_text(encoding="utf-8"))
    assert grading["case_id"] == "eval-api"
    assert grading["variant_id"] == "current"
    assert grading["skill_revision"] == "skill-current"
    assert grading["baseline_revision"] == "absent"
    assert grading["duration_ms"] >= 0
    assert grading["tokens_total"] == 18
    assert all(item["passed"] for item in grading["assertions"])
    assert grading["evidence"]["answer.txt"]["sha256"]
    assert grading["verdict"] == "PASS"


def test_eval_missing_evidence_fails_even_if_text_assertion_passes(
    tmp_path: Path,
) -> None:
    case_path = tmp_path / "case.json"
    output = tmp_path / "run"
    write_json(case_path, case_value(include_evidence=False))

    report = run_eval_case(case_path, "current", output)

    assert report["verdict"] == "FAIL"
    assert [item["code"] for item in report["findings"]] == [
        "EVAL-MISSING-EVIDENCE"
    ]
    grading = json.loads((output / "grading.json").read_text(encoding="utf-8"))
    assert grading["verdict"] == "FAIL"


def test_eval_variants_use_fresh_declared_workspace_only(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"
    write_json(case_path, case_value())
    first = tmp_path / "current"
    second = tmp_path / "absent"

    run_eval_case(case_path, "current", first)
    run_eval_case(case_path, "absent", second)

    grading_a = json.loads((first / "grading.json").read_text(encoding="utf-8"))
    grading_b = json.loads((second / "grading.json").read_text(encoding="utf-8"))
    assert grading_a["workspace_files"] == ["fixture.c"]
    assert grading_b["workspace_files"] == ["fixture.c"]
    assert grading_a["workspace_id"] != grading_b["workspace_id"]
    assert grading_b["verdict"] == "FAIL"


def test_versioned_cases_and_stardz_negatives_are_mechanical() -> None:
    root = require_tree_root("evals/cases/stardz-negatives.json")
    cases = sorted((root / "evals/cases").glob("*.json"))

    assert {path.stem for path in cases} == {
        "api-enforce",
        "api-index-liveness",
        "build-artifact-postcondition",
        "companion-lifecycle-authority",
        "persistence",
        "persistence-deprecated-api",
        "persistence-migration-rollback",
        "persistence-mod-version",
        "stardz-negatives",
        "ui-layout",
    }
    for path in cases:
        assert validate_eval_case(path) == []
    stardz = json.loads(
        (root / "evals/cases/stardz-negatives.json").read_text(encoding="utf-8")
    )
    assert {variant["variant_id"] for variant in stardz["variants"]} == {
        "autoptr",
        "overload",
        "managed",
        "jsonloadfile",
        "ondrop",
        "dabs",
    }
    assert all(assertion["type"] == "not_contains" for assertion in stardz["assertions"])
