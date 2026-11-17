from __future__ import annotations

import json
import re
import tempfile
import time
import uuid
from pathlib import Path

from .common import (
    finding,
    is_relative_contract_path,
    load_json,
    make_report,
    sha256_bytes,
    sort_findings,
    write_json,
)


EVAL_FAMILIES = {"api", "ui", "persistence"}
ASSERTION_TYPES = {"contains", "not_contains", "regex"}


def _schema_finding(message: str, evidence: str) -> dict[str, object]:
    return finding(
        "EVAL-SCHEMA-INVALID",
        path="",
        line=0,
        message=message,
        evidence=evidence,
    )


def validate_eval_case(case_path: Path) -> list[dict[str, object]]:
    case_path = Path(case_path)
    try:
        value = load_json(case_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [_schema_finding("The evaluation case is not valid JSON.", type(error).__name__)]
    root_required = {
        "schema_version",
        "case_id",
        "family",
        "prompt",
        "fixtures",
        "assertions",
        "grader",
        "required_evidence",
        "variants",
    }
    if not isinstance(value, dict) or set(value) != root_required:
        return [
            _schema_finding(
                "The evaluation case has invalid top-level fields.",
                (
                    f"missing={sorted(root_required - set(value))} "
                    f"unknown={sorted(set(value) - root_required)}"
                    if isinstance(value, dict)
                    else type(value).__name__
                ),
            )
        ]
    findings: list[dict[str, object]] = []
    if value["schema_version"] != 1:
        findings.append(_schema_finding("Unsupported evaluation schema.", str(value["schema_version"])))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(value["case_id"])):
        findings.append(_schema_finding("case_id has an invalid format.", str(value["case_id"])))
    if value["family"] not in EVAL_FAMILIES:
        findings.append(_schema_finding("family is not supported.", str(value["family"])))
    if not str(value["prompt"]).strip():
        findings.append(_schema_finding("prompt must not be empty.", "prompt"))
    if not isinstance(value["fixtures"], dict):
        findings.append(_schema_finding("fixtures must be an object.", type(value["fixtures"]).__name__))
    else:
        for relative, content in value["fixtures"].items():
            if not is_relative_contract_path(relative) or not isinstance(content, str):
                findings.append(_schema_finding("A fixture path/content is invalid.", str(relative)))
    assertion_required = {"assertion_id", "type", "value", "evidence"}
    if not isinstance(value["assertions"], list) or not value["assertions"]:
        findings.append(_schema_finding("assertions must be a non-empty array.", "assertions"))
    else:
        assertion_ids: set[str] = set()
        for index, assertion in enumerate(value["assertions"]):
            if not isinstance(assertion, dict) or set(assertion) != assertion_required:
                findings.append(_schema_finding("An assertion has invalid fields.", f"assertions[{index}]"))
                continue
            assertion_id = str(assertion["assertion_id"])
            if assertion_id in assertion_ids:
                findings.append(_schema_finding("Duplicate assertion_id.", assertion_id))
            assertion_ids.add(assertion_id)
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", assertion_id):
                findings.append(_schema_finding("assertion_id has an invalid format.", assertion_id))
            if assertion["type"] not in ASSERTION_TYPES:
                findings.append(_schema_finding("An assertion type is unsupported.", str(assertion["type"])))
            if not isinstance(assertion["value"], str):
                findings.append(_schema_finding("An assertion value must be text.", assertion_id))
            if (
                not isinstance(assertion["evidence"], list)
                or not assertion["evidence"]
                or not all(is_relative_contract_path(item) for item in assertion["evidence"])
            ):
                findings.append(_schema_finding("An assertion needs safe evidence paths.", assertion_id))
    if value["grader"] != {"type": "mechanical"}:
        findings.append(_schema_finding("Only the mechanical grader is accepted.", repr(value["grader"])))
    if (
        not isinstance(value["required_evidence"], list)
        or not all(is_relative_contract_path(item) for item in value["required_evidence"])
    ):
        findings.append(_schema_finding("required_evidence contains an invalid path.", "required_evidence"))
    variant_required = {
        "variant_id",
        "skill_revision",
        "baseline_revision",
        "runner_id",
        "expected_verdict",
        "response",
        "evidence",
        "tokens_input",
        "tokens_output",
    }
    if not isinstance(value["variants"], list) or len(value["variants"]) < 2:
        findings.append(_schema_finding("At least two variants are required.", "variants"))
    else:
        variant_ids: set[str] = set()
        for index, variant in enumerate(value["variants"]):
            if not isinstance(variant, dict) or set(variant) != variant_required:
                findings.append(_schema_finding("A variant has invalid fields.", f"variants[{index}]"))
                continue
            variant_id = str(variant["variant_id"])
            if variant_id in variant_ids:
                findings.append(_schema_finding("Duplicate variant_id.", variant_id))
            variant_ids.add(variant_id)
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", variant_id):
                findings.append(_schema_finding("variant_id has an invalid format.", variant_id))
            for field in ("skill_revision", "baseline_revision", "runner_id"):
                if not str(variant[field]).strip():
                    findings.append(_schema_finding(f"{field} must not be empty.", variant_id))
            if variant["expected_verdict"] not in {"PASS", "FAIL"}:
                findings.append(_schema_finding("expected_verdict must be PASS or FAIL.", variant_id))
            if not isinstance(variant["response"], str) or not isinstance(variant["evidence"], dict):
                findings.append(_schema_finding("Variant response/evidence has an invalid type.", variant_id))
            elif not all(
                is_relative_contract_path(path) and isinstance(content, str)
                for path, content in variant["evidence"].items()
            ):
                findings.append(_schema_finding("Variant evidence has an invalid path/content.", variant_id))
            for field in ("tokens_input", "tokens_output"):
                if not isinstance(variant[field], int) or variant[field] < 0:
                    findings.append(_schema_finding(f"{field} must be a non-negative integer.", variant_id))
    return sort_findings(findings)


def _assertion_result(assertion: dict[str, object], response: str) -> bool:
    assertion_type = str(assertion["type"])
    value = str(assertion["value"])
    if assertion_type == "contains":
        return value in response
    if assertion_type == "not_contains":
        return value not in response
    if assertion_type == "regex":
        return re.search(value, response) is not None
    return False


def run_eval_case(
    case_path: Path,
    variant_id: str,
    output_dir: Path,
) -> dict[str, object]:
    case_path = Path(case_path).resolve()
    output_dir = Path(output_dir).resolve()
    started = time.perf_counter_ns()
    schema_findings = validate_eval_case(case_path)
    if schema_findings:
        return make_report("eval run", case_path.parent, schema_findings)
    case = load_json(case_path)
    variant = next(
        (item for item in case["variants"] if item["variant_id"] == variant_id),
        None,
    )
    if variant is None:
        return make_report(
            "eval run",
            case_path.parent,
            [
                finding(
                    "EVAL-VARIANT-MISSING",
                    path=case_path.name,
                    line=0,
                    message="The requested evaluation variant does not exist.",
                    evidence=variant_id,
                )
            ],
        )

    workspace_id = uuid.uuid4().hex
    workspace_files: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"packctl-eval-{workspace_id}-") as temporary:
        workspace = Path(temporary)
        for relative, content in sorted(case["fixtures"].items()):
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
        workspace_files = sorted(
            path.relative_to(workspace).as_posix()
            for path in workspace.rglob("*")
            if path.is_file()
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_metadata: dict[str, dict[str, object]] = {}
    for relative, content in sorted(variant["evidence"].items()):
        destination = evidence_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
        encoded = content.encode("utf-8")
        evidence_metadata[relative] = {
            "sha256": sha256_bytes(encoded),
            "bytes": len(encoded),
        }

    required = set(case["required_evidence"])
    for assertion in case["assertions"]:
        required.update(assertion["evidence"])
    missing_evidence = sorted(required - set(variant["evidence"]))
    findings: list[dict[str, object]] = []
    if missing_evidence:
        findings.append(
            finding(
                "EVAL-MISSING-EVIDENCE",
                path=case_path.name,
                line=0,
                message="The grader cannot prove its assertions without all required evidence.",
                evidence=",".join(missing_evidence),
            )
        )

    assertion_results: list[dict[str, object]] = []
    response = str(variant["response"])
    for assertion in case["assertions"]:
        passed = _assertion_result(assertion, response)
        assertion_results.append(
            {
                "assertion_id": assertion["assertion_id"],
                "type": assertion["type"],
                "value": assertion["value"],
                "passed": passed,
                "evidence": assertion["evidence"],
            }
        )
        if not passed:
            findings.append(
                finding(
                    "EVAL-ASSERTION-FAILED",
                    path=case_path.name,
                    line=0,
                    message="A mechanical evaluation assertion failed.",
                    evidence=str(assertion["assertion_id"]),
                )
            )

    duration_ms = max(0, (time.perf_counter_ns() - started) // 1_000_000)
    grading = {
        "schema_version": 1,
        "case_id": case["case_id"],
        "family": case["family"],
        "variant_id": variant["variant_id"],
        "skill_revision": variant["skill_revision"],
        "baseline_revision": variant["baseline_revision"],
        "runner_id": variant["runner_id"],
        "expected_verdict": variant["expected_verdict"],
        "response": response,
        "response_sha256": sha256_bytes(response.encode("utf-8")),
        "duration_ms": duration_ms,
        "tokens_input": variant["tokens_input"],
        "tokens_output": variant["tokens_output"],
        "tokens_total": variant["tokens_input"] + variant["tokens_output"],
        "assertions": assertion_results,
        "evidence": evidence_metadata,
        "workspace_id": workspace_id,
        "workspace_files": workspace_files,
        "verdict": "FAIL" if findings else "PASS",
    }
    write_json(output_dir / "grading.json", grading)
    return make_report(
        "eval run",
        case_path.parent,
        findings,
        artifacts={"grading": str(output_dir / "grading.json")},
    )
