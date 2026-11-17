from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .common import finding, is_relative_contract_path, load_json, sort_findings, write_json


LIVE_EVAL_ARMS = ["with_skill", "without_skill"]
LIVE_EVAL_GRADER_TYPES = {"contains_all", "regex_any", "citations_resolve"}
_FORBIDDEN_ANSWER_FIELDS = {
    "response",
    "expected_verdict",
    "tokens_input",
    "tokens_output",
}
_ROOT_FIELDS = {
    "schema_version",
    "case_id",
    "family",
    "skill_under_test",
    "question",
    "fixtures",
    "graders",
    "citation_roots",
    "arms",
    "runs_per_arm",
    "pass_rule",
    "min_discrimination",
}


def _schema_finding(message: str, evidence: str) -> dict[str, object]:
    return finding(
        "LIVE-EVAL-SCHEMA-INVALID",
        path="",
        line=0,
        message=message,
        evidence=evidence,
    )


def _forbidden_answer_field(value: object) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_ANSWER_FIELDS:
                return key
            nested = _forbidden_answer_field(child)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for child in value:
            nested = _forbidden_answer_field(child)
            if nested is not None:
                return nested
    return None


def _is_rate(value: object, *, positive: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return (0 < value <= 1) if positive else (0 <= value <= 1)


def validate_live_eval_case(case_path: Path) -> list[dict[str, object]]:
    case_path = Path(case_path)
    try:
        value = load_json(case_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [
            _schema_finding(
                "The live evaluation case is not valid JSON.",
                type(error).__name__,
            )
        ]
    if not isinstance(value, dict):
        return [
            _schema_finding(
                "The live evaluation case root must be an object.",
                type(value).__name__,
            )
        ]
    forbidden = _forbidden_answer_field(value)
    if forbidden is not None:
        return [
            _schema_finding(
                "The live evaluation case contains a forbidden answer field.",
                forbidden,
            )
        ]
    if set(value) != _ROOT_FIELDS:
        return [
            _schema_finding(
                "The live evaluation case has invalid top-level fields.",
                f"missing={sorted(_ROOT_FIELDS - set(value))} "
                f"unknown={sorted(set(value) - _ROOT_FIELDS)}",
            )
        ]

    findings: list[dict[str, object]] = []
    if value["schema_version"] != 1:
        findings.append(_schema_finding("Unsupported live evaluation schema.", str(value["schema_version"])))
    for field in ("case_id", "skill_under_test"):
        field_value = value[field]
        if not isinstance(field_value, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]*", field_value) is None:
            findings.append(_schema_finding(f"{field} has an invalid format.", str(field_value)))
    if not isinstance(value["family"], str) or not value["family"].strip():
        findings.append(_schema_finding("family must not be empty.", repr(value["family"])))
    if not isinstance(value["question"], str) or "CITATIONS:" not in value["question"]:
        findings.append(_schema_finding("question must require a CITATIONS: block.", "question"))

    fixtures = value["fixtures"]
    if not isinstance(fixtures, dict):
        findings.append(_schema_finding("fixtures must be an object.", type(fixtures).__name__))
    else:
        for relative, content in fixtures.items():
            if not isinstance(relative, str) or not is_relative_contract_path(relative) or not isinstance(content, str):
                findings.append(_schema_finding("A fixture path/content is invalid.", str(relative)))

    graders = value["graders"]
    if not isinstance(graders, list) or not graders:
        findings.append(_schema_finding("graders must be a non-empty array.", "graders"))
    else:
        for index, grader in enumerate(graders):
            context = f"graders[{index}]"
            if not isinstance(grader, dict) or grader.get("type") not in LIVE_EVAL_GRADER_TYPES:
                findings.append(_schema_finding("A grader type is unsupported.", context))
                continue
            grader_type = grader["type"]
            required = {"type"}
            if grader_type == "contains_all":
                required.add("values")
                items = grader.get("values")
            elif grader_type == "regex_any":
                required.add("patterns")
                items = grader.get("patterns")
            else:
                items = None
            if set(grader) != required:
                findings.append(_schema_finding("A grader has invalid fields.", context))
                continue
            if grader_type in {"contains_all", "regex_any"}:
                if (
                    not isinstance(items, list)
                    or not items
                    or not all(isinstance(item, str) and item for item in items)
                ):
                    findings.append(_schema_finding("A grader needs non-empty text items.", context))
                    continue
                if grader_type == "regex_any":
                    try:
                        for pattern in items:
                            re.compile(pattern)
                    except re.error as error:
                        findings.append(_schema_finding("A regex grader has an invalid pattern.", str(error)))

    citation_roots = value["citation_roots"]
    if (
        not isinstance(citation_roots, list)
        or not citation_roots
        or len(citation_roots) != len(set(citation_roots))
        or not set(citation_roots).issubset({"fixture", "pack"})
    ):
        findings.append(_schema_finding("citation_roots is invalid.", repr(citation_roots)))
    if value["arms"] != LIVE_EVAL_ARMS:
        findings.append(_schema_finding("arms must be the exact live evaluation pair.", repr(value["arms"])))
    runs_per_arm = value["runs_per_arm"]
    if isinstance(runs_per_arm, bool) or not isinstance(runs_per_arm, int) or runs_per_arm < 3:
        findings.append(_schema_finding("runs_per_arm must be an integer of at least 3.", repr(runs_per_arm)))

    pass_rule = value["pass_rule"]
    pass_rule_fields = {"min_pass_with_skill", "max_pass_without_skill"}
    if not isinstance(pass_rule, dict) or set(pass_rule) != pass_rule_fields:
        findings.append(_schema_finding("pass_rule has invalid fields.", repr(pass_rule)))
    else:
        for field in sorted(pass_rule_fields):
            if not _is_rate(pass_rule[field]):
                findings.append(_schema_finding(f"{field} must be between 0 and 1.", repr(pass_rule[field])))
    if not _is_rate(value["min_discrimination"], positive=True):
        findings.append(
            _schema_finding(
                "min_discrimination must be greater than 0 and at most 1.",
                repr(value["min_discrimination"]),
            )
        )
    return sort_findings(findings)


EMPTY_SKILLS_TREE_SHA256 = hashlib.sha256(b"").hexdigest()
_CITATION_LINE = re.compile(
    r'^(?P<path>.+):(?P<line>[1-9][0-9]*)(?:\s+"(?P<quote>.*)")?$'
)


def _skills_tree_sha256(skills_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        (item for item in skills_root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(skills_root).as_posix(),
    ):
        digest.update(path.relative_to(skills_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _materialize_workspace(
    root: Path,
    workspace: Path,
    case: dict[str, object],
    *,
    skill_mounted: bool,
) -> Path:
    skills_root = workspace / ".claude" / "skills"
    skills_root.mkdir(parents=True)
    if skill_mounted:
        skill_name = str(case["skill_under_test"])
        source = root / "skills" / skill_name
        if not source.is_dir():
            raise FileNotFoundError(f"Skill not found: {skill_name}")
        shutil.copytree(source, skills_root / skill_name)
    for relative, content in sorted(case["fixtures"].items()):
        destination = workspace / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
    return skills_root


def _resolve_citations(
    case: dict[str, object],
    answer: str,
    root: Path,
    workspace: Path,
) -> tuple[bool, list[dict[str, object]]]:
    if "CITATIONS:" not in answer:
        return False, [{"citation": "", "passed": False, "reason": "missing-block"}]
    citation_text = answer.rsplit("CITATIONS:", 1)[1]
    citation_lines = [line.strip() for line in citation_text.splitlines() if line.strip()]
    if not citation_lines:
        return False, [{"citation": "", "passed": False, "reason": "empty-block"}]

    details: list[dict[str, object]] = []
    fixtures = case["fixtures"]
    roots = set(case["citation_roots"])
    root_resolved = root.resolve()
    for citation in citation_lines:
        match = _CITATION_LINE.fullmatch(citation)
        if match is None:
            details.append({"citation": citation, "passed": False, "reason": "invalid-format"})
            continue
        relative = match.group("path")
        line_number = int(match.group("line"))
        quote = match.group("quote")
        source: Path | None = None
        source_kind = ""
        if "fixture" in roots and relative in fixtures:
            source = workspace / relative
            source_kind = "fixture"
        elif "pack" in roots and is_relative_contract_path(relative):
            candidate = (root / relative).resolve()
            if candidate.is_relative_to(root_resolved) and candidate.is_file():
                source = candidate
                source_kind = "pack"
        if source is None or not source.is_file():
            details.append({"citation": citation, "passed": False, "reason": "unresolved"})
            continue
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            details.append({"citation": citation, "passed": False, "reason": "unreadable"})
            continue
        if line_number > len(lines):
            details.append({"citation": citation, "passed": False, "reason": "line-out-of-range"})
            continue
        line = lines[line_number - 1]
        if quote is not None and quote != line:
            details.append({"citation": citation, "passed": False, "reason": "quote-mismatch"})
            continue
        details.append({"citation": citation, "passed": True, "root": source_kind})
    return all(item["passed"] for item in details), details


def _grade_answer(
    case: dict[str, object],
    answer: str,
    root: Path,
    workspace: Path,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for grader in case["graders"]:
        grader_type = grader["type"]
        evidence: object
        if grader_type == "contains_all":
            missing = [value for value in grader["values"] if value not in answer]
            passed = not missing
            evidence = {"missing": missing}
        elif grader_type == "regex_any":
            matched = [
                pattern
                for pattern in grader["patterns"]
                if re.search(pattern, answer) is not None
            ]
            passed = bool(matched)
            evidence = {"matched": matched}
        else:
            passed, evidence = _resolve_citations(case, answer, root, workspace)
        results.append(
            {
                "type": grader_type,
                "passed": passed,
                "evidence": evidence,
            }
        )
    return results


def _runner_invalid(evidence: str) -> dict[str, object]:
    return finding(
        "LIVE-EVAL-RUNNER-INVALID",
        path="",
        line=0,
        message="The live evaluation runner returned an invalid result.",
        evidence=evidence,
    )


def _invoke_runner(
    runner_path: Path,
    *,
    prompt: str,
    workspace: Path,
    skill_mounted: bool,
    run_index: int,
) -> tuple[dict[str, object] | None, dict[str, object] | None, str]:
    command = (
        [sys.executable, str(runner_path)]
        if runner_path.suffix.lower() == ".py"
        else [str(runner_path)]
    )
    payload = {
        "prompt": prompt,
        "workspace": str(workspace),
        "skill_mounted": skill_mounted,
        "run_index": run_index,
    }
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=workspace,
            check=False,
        )
    except OSError as error:
        return None, _runner_invalid(type(error).__name__), ""
    if completed.returncode != 0:
        return None, _runner_invalid(f"exit={completed.returncode}"), completed.stdout
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return None, _runner_invalid(type(error).__name__), completed.stdout
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("answer"), str)
        or not isinstance(result.get("model"), str)
        or not result["model"].strip()
        or not isinstance(result.get("meta"), dict)
    ):
        return None, _runner_invalid("missing-or-invalid-answer-model-meta"), completed.stdout
    return result, None, completed.stdout


def _arm_summary(runs: list[dict[str, object]]) -> dict[str, object]:
    passed_count = sum(1 for run in runs if run["passed"])
    hashes = sorted({str(run["skills_tree_sha256_before"]) for run in runs})
    return {
        "pass_count": passed_count,
        "pass_rate": passed_count / len(runs),
        "skills_tree_sha256": hashes[0] if len(hashes) == 1 else hashes,
        "runs": runs,
    }



def run_live_eval_case(
    root: Path,
    case_path: Path,
    runner_path: Path,
    report_root: Path,
) -> dict[str, object]:
    root = Path(root).resolve()
    case_path = Path(case_path).resolve()
    runner_path = Path(runner_path).resolve()
    report_root = Path(report_root).resolve()
    schema_findings = validate_live_eval_case(case_path)
    if schema_findings:
        summary = {
            "schema_version": 1,
            "case_id": case_path.stem,
            "model": None,
            "effort": None,
            "runs_per_arm": 0,
            "arms": {},
            "discrimination_verdict": "INCONCLUSIVE",
            "counts_as_evidence": False,
            "findings": schema_findings,
            "verdict": "FAIL",
        }
        destination = report_root / case_path.stem / "summary.json"
        write_json(destination, summary)
        return summary

    case = load_json(case_path)
    findings: list[dict[str, object]] = []
    runs_by_arm: dict[str, list[dict[str, object]]] = {
        "with_skill": [],
        "without_skill": [],
    }
    contaminated = False
    for arm in LIVE_EVAL_ARMS:
        skill_mounted = arm == "with_skill"
        for run_index in range(case["runs_per_arm"]):
            with tempfile.TemporaryDirectory(
                prefix=f".packctl-live-eval-{case['case_id']}-{arm}-{run_index}-",
                dir=root,
            ) as temporary:
                workspace = Path(temporary)
                skills_root = _materialize_workspace(
                    root,
                    workspace,
                    case,
                    skill_mounted=skill_mounted,
                )
                hash_before = _skills_tree_sha256(skills_root)
                runner_result: dict[str, object] | None = None
                runner_finding: dict[str, object] | None = None
                raw_stdout = ""
                if not skill_mounted and hash_before != EMPTY_SKILLS_TREE_SHA256:
                    contaminated = True
                    runner_finding = finding(
                        "LIVE-EVAL-ARM-CONTAMINATED",
                        path="",
                        line=0,
                        message="The without_skill arm contains skill files.",
                        evidence=f"before={hash_before}",
                    )
                else:
                    runner_result, runner_finding, raw_stdout = _invoke_runner(
                        runner_path,
                        prompt=case["question"],
                        workspace=workspace,
                        skill_mounted=skill_mounted,
                        run_index=run_index,
                    )
                hash_after = _skills_tree_sha256(skills_root)
                if not skill_mounted and hash_after != EMPTY_SKILLS_TREE_SHA256:
                    contaminated = True
                    runner_finding = finding(
                        "LIVE-EVAL-ARM-CONTAMINATED",
                        path="",
                        line=0,
                        message="The without_skill arm contains skill files.",
                        evidence=f"before={hash_before} after={hash_after}",
                    )
                if runner_finding is not None:
                    findings.append(runner_finding)
                if runner_result is None:
                    grader_results = [
                        {
                            "type": grader["type"],
                            "passed": False,
                            "evidence": {"reason": "runner-invalid"},
                        }
                        for grader in case["graders"]
                    ]
                    answer = raw_stdout
                    model: str | None = None
                    meta: dict[str, object] = {}
                else:
                    answer = runner_result["answer"]
                    model = runner_result["model"]
                    meta = runner_result["meta"]
                    grader_results = _grade_answer(
                        case,
                        answer,
                        root,
                        workspace,
                    )
                runs_by_arm[arm].append(
                    {
                        "run_index": run_index,
                        "skill_mounted": skill_mounted,
                        "skills_tree_sha256_before": hash_before,
                        "skills_tree_sha256_after": hash_after,
                        "response": answer,
                        "model": model,
                        "meta": meta,
                        "graders": grader_results,
                        "passed": runner_result is not None
                        and runner_finding is None
                        and all(result["passed"] for result in grader_results),
                    }
                )

    arms = {
        arm: _arm_summary(runs_by_arm[arm])
        for arm in LIVE_EVAL_ARMS
    }
    with_rate = arms["with_skill"]["pass_rate"]
    without_rate = arms["without_skill"]["pass_rate"]
    pass_rule = case["pass_rule"]
    if contaminated:
        discrimination_verdict = "INCONCLUSIVE"
    elif without_rate > pass_rule["max_pass_without_skill"]:
        discrimination_verdict = "VACUOUS"
        findings.append(
            finding(
                "LIVE-EVAL-CASE-NOT-DISCRIMINATING",
                path=case_path.name,
                line=0,
                message="The case passes without the skill, so it measures nothing.",
                evidence=f"with={with_rate} without={without_rate}",
            )
        )
    elif (
        with_rate < pass_rule["min_pass_with_skill"]
        or with_rate - without_rate < case["min_discrimination"]
    ):
        discrimination_verdict = "INCONCLUSIVE"
    else:
        discrimination_verdict = "DISCRIMINATING"

    models = sorted(
        {
            run["model"]
            for runs in runs_by_arm.values()
            for run in runs
            if run["model"] is not None
        }
    )
    efforts = sorted(
        {
            str(run["meta"]["effort"])
            for runs in runs_by_arm.values()
            for run in runs
            if "effort" in run["meta"]
        }
    )
    counts_as_evidence = discrimination_verdict == "DISCRIMINATING" and not contaminated
    summary = {
        "schema_version": 1,
        "case_id": case["case_id"],
        "model": models[0] if len(models) == 1 else models,
        "effort": efforts[0] if len(efforts) == 1 else efforts,
        "runs_per_arm": case["runs_per_arm"],
        "arms": arms,
        "discrimination_verdict": discrimination_verdict,
        "counts_as_evidence": counts_as_evidence,
        "findings": sort_findings(findings),
        "verdict": (
            "PASS"
            if counts_as_evidence and not findings
            else "WARN"
            if discrimination_verdict == "INCONCLUSIVE" and not findings
            else "FAIL"
        ),
    }
    destination = report_root / case["case_id"] / "summary.json"
    write_json(destination, summary)
    return summary
