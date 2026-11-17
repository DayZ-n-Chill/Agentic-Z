from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

from .generated import scan as scan_generated
from .common import (
    finding,
    git_tracked_files,
    is_relative_contract_path,
    load_json,
    make_report,
    sha256_file,
    sort_findings,
)


SOURCE_MAP_PATH = "sources/source-map.json"
CLAIMS_PATH = "sources/claims.json"
LINK_ALLOWLIST_PATH = "sources/link-allowlist.json"
VERIFICATION_LEVELS = {
    "runtime_verified",
    "source_verified",
    "offline_tested",
    "cross_checked",
    "historical",
    "unverified",
}
SOURCE_DECISIONS = {"adopt", "keep_pack", "merge", "reject"}
EXCLUSION_REASONS = {
    "generated",
    "cache",
    "backup",
    "project_evidence",
    "superseded",
    "license_restricted",
}
ALLOWED_SKILL_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
FORBIDDEN_PAYLOAD_LICENSES = (
    "GPL",
    "DPL-ND",
    "CC-NC",
    "PROPRIETARY",
    "UNKNOWN",
)
TEXT_SUFFIXES = {
    ".bat",
    ".c",
    ".cfg",
    ".cpp",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".xml",
    ".yml",
    ".yaml",
}


def _source_schema_finding(message: str, evidence: str) -> dict[str, object]:
    return finding(
        "SOURCE-SCHEMA-INVALID",
        path=SOURCE_MAP_PATH,
        line=1,
        message=message,
        evidence=evidence,
    )


def _load_source_map(root: Path) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    path = root / SOURCE_MAP_PATH
    if not path.is_file():
        return None, [
            finding(
                "SOURCE-MAP-MISSING",
                path=SOURCE_MAP_PATH,
                line=0,
                message="The versioned source map is missing.",
                evidence="Expected sources/source-map.json.",
            )
        ]
    try:
        value = load_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [_source_schema_finding("The source map is not valid JSON.", str(error))]
    if not isinstance(value, dict):
        return None, [_source_schema_finding("The source map root must be an object.", type(value).__name__)]
    return value, []


def _validate_input(
    value: object,
    *,
    context: str,
    source_ids: set[str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    required = {
        "source_id",
        "source_revision",
        "source_path",
        "source_hash",
        "license",
        "verification_level",
        "decision",
        "decision_evidence",
    }
    allowed = required
    if not isinstance(value, dict):
        return [_source_schema_finding(f"{context} must be an object.", repr(value))]
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown or missing:
        findings.append(
            _source_schema_finding(
                f"{context} has invalid fields.",
                f"missing={sorted(missing)} unknown={sorted(unknown)}",
            )
        )
        return findings
    if value["source_id"] not in source_ids:
        findings.append(
            _source_schema_finding(
                f"{context} references an unknown source.",
                str(value["source_id"]),
            )
        )
    if not is_relative_contract_path(value["source_path"]):
        findings.append(
            _source_schema_finding(
                f"{context} source_path is not a safe relative POSIX path.",
                str(value["source_path"]),
            )
        )
    if not re.fullmatch(r"[0-9a-f]{64}", str(value["source_hash"])):
        findings.append(
            _source_schema_finding(
                f"{context} source_hash is not lowercase SHA-256.",
                str(value["source_hash"]),
            )
        )
    if value["verification_level"] not in VERIFICATION_LEVELS:
        findings.append(
            _source_schema_finding(
                f"{context} has an unknown verification level.",
                str(value["verification_level"]),
            )
        )
    if value["decision"] not in SOURCE_DECISIONS:
        findings.append(
            _source_schema_finding(
                f"{context} has an unknown reconciliation decision.",
                str(value["decision"]),
            )
        )
    if not str(value["decision_evidence"]).strip() or not str(value["license"]).strip():
        findings.append(
            _source_schema_finding(
                f"{context} has an empty evidence or license field.",
                context,
            )
        )
    return findings


def _validate_source_map_shape(value: dict[str, object]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    required = {
        "schema_version",
        "baseline_commit",
        "claim_baseline_commit",
        "release_id",
        "dayz_build",
        "sources",
        "artifacts",
        "excluded_inputs",
        "generated_artifacts",
    }
    unknown = set(value) - required
    missing = required - set(value)
    if unknown or missing:
        findings.append(
            _source_schema_finding(
                "The source map has invalid top-level fields.",
                f"missing={sorted(missing)} unknown={sorted(unknown)}",
            )
        )
        return findings
    if value["schema_version"] != 1:
        findings.append(
            _source_schema_finding("Unsupported source-map schema.", str(value["schema_version"]))
        )
    for key in ("baseline_commit", "claim_baseline_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(value[key])):
            findings.append(
                _source_schema_finding(f"{key} must be a full lowercase commit.", str(value[key]))
            )
    if not re.fullmatch(r"1\.[0-9]+\.0\.[0-9]+", str(value["dayz_build"])):
        findings.append(
            _source_schema_finding("dayz_build has an invalid format.", str(value["dayz_build"]))
        )
    for key in ("sources", "artifacts", "excluded_inputs", "generated_artifacts"):
        if not isinstance(value[key], list):
            findings.append(_source_schema_finding(f"{key} must be an array.", type(value[key]).__name__))
    if findings:
        return findings

    source_ids: set[str] = set()
    source_allowed = {
        "source_id",
        "kind",
        "revision",
        "license",
        "local_root_id",
        "public_locator",
        "notes",
    }
    for index, item in enumerate(value["sources"]):
        context = f"sources[{index}]"
        if not isinstance(item, dict):
            findings.append(_source_schema_finding(f"{context} must be an object.", repr(item)))
            continue
        required_source = {"source_id", "kind", "revision", "license"}
        unknown_source = set(item) - source_allowed
        missing_source = required_source - set(item)
        if unknown_source or missing_source:
            findings.append(
                _source_schema_finding(
                    f"{context} has invalid fields.",
                    f"missing={sorted(missing_source)} unknown={sorted(unknown_source)}",
                )
            )
            continue
        source_id = str(item["source_id"])
        if source_id in source_ids:
            findings.append(_source_schema_finding("Duplicate source_id.", source_id))
        source_ids.add(source_id)
        if item["kind"] not in {"git", "filesystem", "archive", "web", "authored"}:
            findings.append(_source_schema_finding(f"{context} has an invalid kind.", str(item["kind"])))
        if not str(item["revision"]).strip() or not str(item["license"]).strip():
            findings.append(_source_schema_finding(f"{context} has an empty revision/license.", source_id))

    artifact_allowed = {
        "artifact_id",
        "output_path",
        "distribution_role",
        "distribution_reason",
        "license",
        "verification_level",
        "routing_artifact_id",
        "hash_policy",
        "output_hash",
        "inputs",
    }
    artifact_required = {
        "artifact_id",
        "output_path",
        "distribution_role",
        "license",
        "verification_level",
        "routing_artifact_id",
        "hash_policy",
        "inputs",
    }
    for index, item in enumerate(value["artifacts"]):
        context = f"artifacts[{index}]"
        if not isinstance(item, dict):
            findings.append(_source_schema_finding(f"{context} must be an object.", repr(item)))
            continue
        unknown_artifact = set(item) - artifact_allowed
        missing_artifact = artifact_required - set(item)
        if unknown_artifact or missing_artifact:
            findings.append(
                _source_schema_finding(
                    f"{context} has invalid fields.",
                    f"missing={sorted(missing_artifact)} unknown={sorted(unknown_artifact)}",
                )
            )
            continue
        path = item["output_path"]
        if not is_relative_contract_path(path):
            findings.append(_source_schema_finding(f"{context} output_path is unsafe.", str(path)))
        role = item["distribution_role"]
        policy = item["hash_policy"]
        if role not in {"payload", "repo_only"}:
            findings.append(_source_schema_finding(f"{context} has an invalid distribution role.", str(role)))
        if item["verification_level"] not in VERIFICATION_LEVELS:
            findings.append(_source_schema_finding(f"{context} has an invalid verification level.", str(item["verification_level"])))
        if role == "repo_only" and not str(item.get("distribution_reason", "")).strip():
            findings.append(_source_schema_finding(f"{context} lacks distribution_reason.", str(path)))
        if policy == "self_exempt":
            if path != SOURCE_MAP_PATH or role != "repo_only" or "output_hash" in item:
                findings.append(_source_schema_finding("Only the repo-only source map may be self_exempt.", str(path)))
        elif policy == "sha256":
            if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("output_hash", ""))):
                findings.append(_source_schema_finding(f"{context} lacks a valid output_hash.", str(path)))
        else:
            findings.append(_source_schema_finding(f"{context} has an invalid hash policy.", str(policy)))
        inputs = item.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            findings.append(_source_schema_finding(f"{context} inputs must be a non-empty array.", str(path)))
        else:
            for input_index, source_input in enumerate(inputs):
                findings.extend(
                    _validate_input(
                        source_input,
                        context=f"{context}.inputs[{input_index}]",
                        source_ids=source_ids,
                    )
                )

    excluded_allowed = {
        "source_id",
        "source_revision",
        "source_path",
        "source_hash",
        "reason",
        "decision_evidence",
    }
    for index, item in enumerate(value["excluded_inputs"]):
        context = f"excluded_inputs[{index}]"
        if not isinstance(item, dict):
            findings.append(_source_schema_finding(f"{context} must be an object.", repr(item)))
            continue
        if set(item) != excluded_allowed:
            findings.append(
                _source_schema_finding(
                    f"{context} has invalid fields.",
                    f"missing={sorted(excluded_allowed - set(item))} unknown={sorted(set(item) - excluded_allowed)}",
                )
            )
            continue
        if item["source_id"] not in source_ids:
            findings.append(_source_schema_finding(f"{context} references an unknown source.", str(item["source_id"])))
        if not is_relative_contract_path(item["source_path"]):
            findings.append(_source_schema_finding(f"{context} source_path is unsafe.", str(item["source_path"])))
        if not re.fullmatch(r"[0-9a-f]{64}", str(item["source_hash"])):
            findings.append(_source_schema_finding(f"{context} source_hash is invalid.", str(item["source_hash"])))
        if item["reason"] not in EXCLUSION_REASONS:
            findings.append(_source_schema_finding(f"{context} has an invalid reason.", str(item["reason"])))
        if not str(item["decision_evidence"]).strip():
            findings.append(_source_schema_finding(f"{context} lacks decision evidence.", str(item["source_path"])))

    generated_required = {"artifact_id", "output_path", "generator", "license"}
    for index, item in enumerate(value["generated_artifacts"]):
        context = f"generated_artifacts[{index}]"
        if not isinstance(item, dict) or set(item) != generated_required:
            findings.append(_source_schema_finding(f"{context} has invalid fields.", repr(item)))
            continue
        if not is_relative_contract_path(item["output_path"]):
            findings.append(_source_schema_finding(f"{context} output_path is unsafe.", str(item["output_path"])))
    return findings


def validate_source_map(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    value, findings = _load_source_map(root)
    if value is None:
        return sort_findings(findings)
    shape_findings = _validate_source_map_shape(value)
    findings.extend(shape_findings)
    if shape_findings:
        return sort_findings(findings)

    artifacts: list[dict[str, object]] = value["artifacts"]  # type: ignore[assignment]
    tracked = set(git_tracked_files(root))
    outputs: dict[str, list[dict[str, object]]] = {}
    for item in artifacts:
        outputs.setdefault(str(item["output_path"]), []).append(item)
    receipts_root = root / "promotions" / "receipts"
    receipt_paths = {
        path.relative_to(root).as_posix()
        for path in receipts_root.glob("*.json")
        if path.is_file()
    }
    for path in sorted(receipt_paths - set(outputs)):
        findings.append(
            finding(
                "SOURCE-RECEIPT-UNTRACKED",
                path=path,
                line=0,
                message="A promotion receipt has no source-map artifact.",
                evidence=path,
            )
        )
    for path, duplicates in outputs.items():
        if len(duplicates) > 1:
            findings.append(
                finding(
                    "SOURCE-DUPLICATE",
                    path=path,
                    line=0,
                    message="A tracked output is classified more than once.",
                    evidence=f"artifact_count={len(duplicates)}",
                )
            )
    for path in sorted(tracked - set(outputs)):
        findings.append(
            finding(
                "SOURCE-UNMAPPED",
                path=path,
                line=0,
                message="A Git-tracked file has no source-map artifact.",
                evidence=path,
            )
        )
    for path in sorted(set(outputs) - tracked):
        findings.append(
            finding(
                "SOURCE-OUTPUT-MISSING",
                path=path,
                line=0,
                message="A source-map artifact is not a Git-tracked file.",
                evidence=path,
            )
        )

    for item in artifacts:
        path = str(item["output_path"])
        if item["hash_policy"] == "sha256" and path in tracked:
            actual = sha256_file(root / path)
            if actual != item["output_hash"]:
                findings.append(
                    finding(
                        "SOURCE-HASH-MISMATCH",
                        path=path,
                        line=0,
                        message="The tracked output differs from its source-map hash.",
                        evidence=f"expected={item['output_hash']} actual={actual}",
                    )
                )
        hashes = {str(source_input["source_hash"]) for source_input in item["inputs"]}
        adopted = [source_input for source_input in item["inputs"] if source_input["decision"] == "adopt"]
        if len(hashes) > 1 and len(adopted) > 1:
            findings.append(
                finding(
                    "SOURCE-CONFLICT-UNDECIDED",
                    path=path,
                    line=0,
                    message="Divergent inputs are simultaneously marked authoritative.",
                    evidence=f"adopt_count={len(adopted)} distinct_hashes={len(hashes)}",
                )
            )

    adopted_keys = {
        (str(source_input["source_id"]), str(source_input["source_path"]))
        for item in artifacts
        for source_input in item["inputs"]
    }
    for excluded in value["excluded_inputs"]:  # type: ignore[index]
        key = (str(excluded["source_id"]), str(excluded["source_path"]))
        if key in adopted_keys:
            findings.append(
                finding(
                    "SOURCE-INPUT-DUPLICATE",
                    path=SOURCE_MAP_PATH,
                    line=0,
                    message="An input is both mapped and explicitly excluded.",
                    evidence=f"{key[0]}:{key[1]}",
                )
            )

    generated_paths = {str(item["output_path"]) for item in value["generated_artifacts"]}  # type: ignore[index]
    for path in sorted(generated_paths & tracked):
        findings.append(
            finding(
                "SOURCE-GENERATED-TRACKED",
                path=path,
                line=0,
                message="A generated archive member must not be Git-tracked.",
                evidence=path,
            )
        )
    return sort_findings(findings)


def _parse_frontmatter(path: Path) -> tuple[dict[str, object], int, str | None]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 1, "missing opening delimiter"
    closing = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if closing is None:
        return {}, 1, "missing closing delimiter"
    values: dict[str, object] = {}
    index = 1
    while index < closing:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            index += 1
            continue
        if ":" not in line:
            return values, index + 1, "invalid top-level YAML line"
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if raw in {">", ">-", "|", "|-"}:
            chunks: list[str] = []
            index += 1
            while index < closing and (not lines[index] or lines[index].startswith((" ", "\t"))):
                chunks.append(lines[index].strip())
                index += 1
            values[key] = (" " if raw.startswith(">") else "\n").join(chunks).strip()
            continue
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
            raw = raw[1:-1]
        values[key] = raw
        index += 1
    return values, 1, None


def validate_skills(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    skills_root = root / "skills"
    if not skills_root.exists():
        return findings
    for skill_path in sorted(skills_root.rglob("SKILL.md")):
        relative = skill_path.relative_to(root).as_posix()
        try:
            frontmatter, line, error = _parse_frontmatter(skill_path)
        except (OSError, UnicodeError) as read_error:
            findings.append(
                finding(
                    "SKILL-READ-ERROR",
                    path=relative,
                    line=0,
                    message="The skill could not be read as UTF-8.",
                    evidence=str(read_error),
                )
            )
            continue
        if error:
            findings.append(
                finding(
                    "SKILL-FRONTMATTER-INVALID",
                    path=relative,
                    line=line,
                    message="The skill frontmatter is invalid.",
                    evidence=error,
                )
            )
            continue
        unknown = set(frontmatter) - ALLOWED_SKILL_FIELDS
        if unknown:
            findings.append(
                finding(
                    "SKILL-FRONTMATTER-UNSUPPORTED",
                    path=relative,
                    line=1,
                    message="The skill declares unsupported frontmatter fields.",
                    evidence=",".join(sorted(unknown)),
                )
            )
        name = str(frontmatter.get("name", ""))
        description = str(frontmatter.get("description", ""))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            findings.append(
                finding(
                    "SKILL-NAME-INVALID",
                    path=relative,
                    line=1,
                    message="The skill name must be lowercase hyphen-case and at most 64 characters.",
                    evidence=name,
                )
            )
        if not description:
            findings.append(
                finding(
                    "SKILL-DESCRIPTION-MISSING",
                    path=relative,
                    line=1,
                    message="The skill description is required.",
                    evidence="description is empty",
                )
            )
        elif len(description) > 1024:
            findings.append(
                finding(
                    "SKILL-DESCRIPTION-TOO-LONG",
                    path=relative,
                    line=1,
                    message="The skill description exceeds the official 1024-character cap.",
                    evidence=f"length={len(description)} limit=1024",
                )
            )
    return sort_findings(findings)


def _without_fenced_blocks(lines: Iterable[str]) -> Iterable[tuple[int, str]]:
    fence: str | None = None
    for line_number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        marker_match = re.match(r"(`{3,}|~{3,})", stripped)
        if marker_match:
            marker = marker_match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            yield line_number, ""
            continue
        yield line_number, "" if fence else line


def validate_links(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    allowed_links: set[tuple[str, str]] = set()
    allowlist_path = root / LINK_ALLOWLIST_PATH
    if allowlist_path.is_file():
        try:
            allowlist = load_json(allowlist_path)
            if (
                not isinstance(allowlist, dict)
                or set(allowlist) != {"schema_version", "entries"}
                or allowlist["schema_version"] != 1
                or not isinstance(allowlist["entries"], list)
            ):
                raise ValueError("invalid allowlist root")
            for entry in allowlist["entries"]:
                if (
                    not isinstance(entry, dict)
                    or set(entry) != {"path", "target", "reason"}
                    or not str(entry["reason"]).strip()
                    or not is_relative_contract_path(entry["path"])
                ):
                    raise ValueError("invalid allowlist entry")
                allowed_links.add((str(entry["path"]), str(entry["target"])))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            findings.append(
                finding(
                    "LINK-ALLOWLIST-INVALID",
                    path=LINK_ALLOWLIST_PATH,
                    line=1,
                    message="The local-link allowlist does not match schema v1.",
                    evidence=type(error).__name__,
                )
            )
    markdown_paths = [
        root / path
        for path in git_tracked_files(root)
        if path.lower().endswith(".md") and (root / path).is_file()
    ]
    pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
    for path in markdown_paths:
        relative = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line_number, line in _without_fenced_blocks(lines):
            for match in pattern.finditer(line):
                raw_target = match.group(1).strip()
                if raw_target.startswith("<") and raw_target.endswith(">"):
                    raw_target = raw_target[1:-1]
                target = raw_target.split(maxsplit=1)[0]
                if (
                    not target
                    or target.startswith(("#", "http://", "https://", "mailto:", "data:"))
                    or "<" in target
                    or ">" in target
                ):
                    continue
                target_path = unquote(target.split("#", 1)[0])
                if not target_path:
                    continue
                candidate = (path.parent / target_path).resolve(strict=False)
                try:
                    candidate.relative_to(root)
                except ValueError:
                    findings.append(
                        finding(
                            "LINK-PATH-ESCAPE",
                            path=relative,
                            line=line_number,
                            message="A local Markdown link escapes the repository.",
                            evidence=target,
                        )
                    )
                    continue
                if not candidate.exists():
                    if (relative, target) in allowed_links:
                        continue
                    findings.append(
                        finding(
                            "LINK-BROKEN",
                            path=relative,
                            line=line_number,
                            message="A local Markdown link target does not exist.",
                            evidence=target,
                        )
                    )
    return sort_findings(findings)


def _payload_paths(root: Path) -> list[str]:
    value, _ = _load_source_map(root)
    if value is None or not isinstance(value.get("artifacts"), list):
        return git_tracked_files(root)
    return sorted(
        str(item["output_path"])
        for item in value["artifacts"]
        if isinstance(item, dict) and item.get("distribution_role") == "payload"
    )


def _privacy_scan_paths(root: Path) -> list[str]:
    tracked = set(git_tracked_files(root))
    public_contracts = {
        relative
        for relative in tracked
        if (
            (
                relative.startswith("sources/")
                or relative.startswith("promotions/")
            )
            and Path(relative).suffix.lower() == ".json"
        )
        or relative == "packctl/manifest.schema.json"
    }
    return sorted(set(_payload_paths(root)) | public_contracts)


def validate_privacy(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    private_patterns = [
        re.compile(r"(?i)\b[A-Z]:\\Users\\(?!<)[^\\\s`\"']+\\"),
        re.compile(r"(?i)(?<![A-Za-z0-9_])/Users/(?!<)[^/\s`\"']+/"),
        # A user directory flattened into one path component -- the shape a
        # scrubbed-but-not-really path leaves behind (C--Users-<name>-...).
        # The two patterns above both need separators, so neither can reach it.
        re.compile(r"(?i)\b[A-Z]--Users-(?!<)[A-Za-z0-9_.]+"),
    ]
    secret_patterns = [
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
        re.compile(
            r"""(?ix)
            \b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\b
            \s*[:=]\s*
            ["']
            (?!
                <|\$\{|%|\[REDACTED\]|changeme|example|placeholder
            )
            [^"'\r\n]{8,}
            ["']
            """
        ),
    ]
    for relative in _privacy_scan_paths(root):
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            private_scan_line = line.replace("\\\\", "\\")
            for pattern in private_patterns:
                match = pattern.search(private_scan_line)
                if match:
                    findings.append(
                        finding(
                            "PRIVACY-PRIVATE-PATH",
                            path=relative,
                            line=line_number,
                            message="A public pack file contains a user-specific absolute path.",
                            evidence=match.group(0),
                        )
                    )
                    break
            for pattern in secret_patterns:
                if pattern.search(line):
                    findings.append(
                        finding(
                            "PRIVACY-SECRET",
                            path=relative,
                            line=line_number,
                            message="A public pack file contains a token-shaped secret.",
                            evidence="[REDACTED]",
                        )
                    )
                    break
    return sort_findings(findings)


def validate_licenses(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    if not (root / "LICENSE").is_file():
        findings.append(
            finding(
                "LICENSE-MISSING",
                path="LICENSE",
                line=0,
                message="The repository-level license is missing.",
                evidence="Expected LICENSE.",
            )
        )
    value, _ = _load_source_map(root)
    if value is None or not isinstance(value.get("artifacts"), list):
        return sort_findings(findings)
    for item in value["artifacts"]:
        if not isinstance(item, dict) or item.get("distribution_role") != "payload":
            continue
        license_id = str(item.get("license", "")).strip()
        relative = str(item.get("output_path", ""))
        if not license_id:
            findings.append(
                finding(
                    "LICENSE-UNCOVERED",
                    path=relative,
                    line=0,
                    message="A payload artifact has no license coverage.",
                    evidence="license is empty",
                )
            )
        elif any(marker in license_id.upper() for marker in FORBIDDEN_PAYLOAD_LICENSES):
            findings.append(
                finding(
                    "LICENSE-FORBIDDEN-PAYLOAD",
                    path=relative,
                    line=0,
                    message="A license-restricted source is classified as release payload.",
                    evidence=license_id,
                )
            )
    return sort_findings(findings)


CLAIM_MARKER_PATTERN = re.compile(
    r"(?:\[EXACT\]\[(CLAIM-[A-Z0-9][A-Z0-9-]*)\]|claim:\s*(CLAIM-[A-Z0-9][A-Z0-9-]*))"
)


def validate_claims(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    registry_path = root / CLAIMS_PATH
    if not registry_path.is_file():
        return [
            finding(
                "CLAIM-REGISTRY-MISSING",
                path=CLAIMS_PATH,
                line=0,
                message="The executable-claim registry is missing.",
                evidence=CLAIMS_PATH,
            )
        ]
    try:
        registry = load_json(registry_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [
            finding(
                "CLAIM-SCHEMA-INVALID",
                path=CLAIMS_PATH,
                line=1,
                message="The claim registry is not valid JSON.",
                evidence=str(error),
            )
        ]
    required_root = {"schema_version", "claim_baseline_commit", "claims"}
    if not isinstance(registry, dict) or set(registry) != required_root or registry.get("schema_version") != 1 or not isinstance(registry.get("claims"), list):
        return [
            finding(
                "CLAIM-SCHEMA-INVALID",
                path=CLAIMS_PATH,
                line=1,
                message="The claim registry root does not match schema v1.",
                evidence="Expected schema_version, claim_baseline_commit and claims.",
            )
        ]
    claim_required = {
        "claim_id",
        "artifact_id",
        "line_start",
        "line_end",
        "source_id",
        "source_revision",
        "evidence_locator",
        "license",
        "observed_at",
        "verification_level",
        "promotion_artifact_id",
    }
    claims_by_id: dict[str, dict[str, object]] = {}
    for index, claim in enumerate(registry["claims"]):
        if not isinstance(claim, dict) or set(claim) != claim_required:
            findings.append(
                finding(
                    "CLAIM-SCHEMA-INVALID",
                    path=CLAIMS_PATH,
                    line=1,
                    message="A claim entry has invalid fields.",
                    evidence=f"claims[{index}]",
                )
            )
            continue
        claim_id = str(claim["claim_id"])
        if not re.fullmatch(r"CLAIM-[A-Z0-9][A-Z0-9-]*", claim_id):
            findings.append(
                finding(
                    "CLAIM-SCHEMA-INVALID",
                    path=CLAIMS_PATH,
                    line=1,
                    message="A claim_id has an invalid format.",
                    evidence=claim_id,
                )
            )
        if claim_id in claims_by_id:
            findings.append(
                finding(
                    "CLAIM-DUPLICATE",
                    path=CLAIMS_PATH,
                    line=1,
                    message="A claim_id appears more than once.",
                    evidence=claim_id,
                )
            )
        claims_by_id[claim_id] = claim
        if (
            not isinstance(claim["line_start"], int)
            or not isinstance(claim["line_end"], int)
            or claim["line_start"] < 1
            or claim["line_end"] < claim["line_start"]
            or claim["verification_level"] not in VERIFICATION_LEVELS
        ):
            findings.append(
                finding(
                    "CLAIM-SCHEMA-INVALID",
                    path=CLAIMS_PATH,
                    line=1,
                    message="A claim has an invalid range or verification level.",
                    evidence=claim_id,
                )
            )

    source_map, _ = _load_source_map(root)
    artifact_paths: dict[str, str] = {}
    claim_scan_paths: list[str] = []
    if source_map and isinstance(source_map.get("artifacts"), list):
        artifact_paths = {
            str(item["artifact_id"]): str(item["output_path"])
            for item in source_map["artifacts"]
            if isinstance(item, dict)
        }
        claim_scan_paths = sorted(
            str(item["output_path"])
            for item in source_map["artifacts"]
            if isinstance(item, dict)
            and item.get("distribution_role") == "payload"
        )

    seen_markers: set[str] = set()
    for relative in claim_scan_paths:
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            for match in CLAIM_MARKER_PATTERN.finditer(line):
                claim_id = match.group(1) or match.group(2)
                seen_markers.add(claim_id)
                claim = claims_by_id.get(claim_id)
                if claim is None:
                    findings.append(
                        finding(
                            "CLAIM-UNREGISTERED",
                            path=relative,
                            line=line_number,
                            message="An executable claim marker has no registry entry.",
                            evidence=claim_id,
                        )
                    )
                    continue
                expected_path = artifact_paths.get(str(claim["artifact_id"]))
                if (
                    expected_path != relative
                    or not (int(claim["line_start"]) <= line_number <= int(claim["line_end"]))
                ):
                    findings.append(
                        finding(
                            "CLAIM-RANGE-MISMATCH",
                            path=relative,
                            line=line_number,
                            message="A claim marker lies outside its registered artifact/range.",
                            evidence=claim_id,
                        )
                    )
    for claim_id in sorted(set(claims_by_id) - seen_markers):
        findings.append(
            finding(
                "CLAIM-MARKER-MISSING",
                path=CLAIMS_PATH,
                line=1,
                message="A registered claim has no marker in its artifact.",
                evidence=claim_id,
            )
        )
    return sort_findings(findings)


MOVED_EXACT_OPEN_RE = re.compile(
    rb'<!-- MOVED-EXACT source="([^"]*)" sha256="([0-9A-Fa-f]{64})" -->\n'
)
MOVED_EXACT_CLOSE = b"<!-- END MOVED-EXACT -->"


def validate_moved_exact(root: Path) -> list[dict[str, object]]:
    """Check that every MOVED-EXACT block still hashes to its own pin.

    The seal marks a passage moved verbatim out of another file, and its sha256
    is over the raw bytes between the opening comment's newline and the closing
    marker -- no normalization, no BOM, no CRLF variant. Measured 2026-08-24
    against the seven seals in the tree: four matched that rule and three did
    not, and nothing had ever run the comparison, so a global rename sweep
    edited two sealed bodies and went unnoticed for nine days.

    An unterminated opening marker is reported too. Without that, deleting the
    closing marker would silently exempt a block instead of failing it.
    """
    findings: list[dict[str, object]] = []
    skills_root = root / "skills"
    if not skills_root.is_dir():
        return findings
    for path in sorted(skills_root.rglob("*.md")):
        raw = path.read_bytes()
        rel = path.relative_to(root).as_posix()
        for match in MOVED_EXACT_OPEN_RE.finditer(raw):
            line = raw.count(b"\n", 0, match.start()) + 1
            source = match.group(1).decode("utf-8", "replace")
            pinned = match.group(2).decode("ascii").upper()
            end = raw.find(MOVED_EXACT_CLOSE, match.end())
            if end < 0:
                findings.append(
                    finding(
                        "SKILL-MOVED-EXACT-UNCLOSED",
                        path=rel,
                        line=line,
                        message="A MOVED-EXACT block has no closing marker, so its pin is never checked.",
                        evidence=f"source={source} pinned={pinned[:12]} close-marker=absent",
                    )
                )
                continue
            actual = hashlib.sha256(raw[match.end():end]).hexdigest().upper()
            if actual != pinned:
                findings.append(
                    finding(
                        "SKILL-MOVED-EXACT-DRIFT",
                        path=rel,
                        line=line,
                        message="A MOVED-EXACT body no longer hashes to the sha256 recorded in its own seal.",
                        evidence=f"source={source} pinned={pinned[:12]} actual={actual[:12]}",
                    )
                )
    return sort_findings(findings)


def validate_generated(root: Path) -> list[dict[str, object]]:
    """Check every file that declares itself generated against the source it names.

    A copy exists because `dayz_3d_viewer` installs non-editable, so the package cannot
    reach `skills/_shared/` by walking parents. The copy is therefore a build artifact:
    editing it by hand, or changing the source without regenerating, is a build failure
    rather than a divergence nobody notices. The rule lives in `packctl.generated` so the
    writer and this checker cannot disagree about what "in sync" means.
    """
    return sort_findings(
        [
            finding(
                item["code"],
                path=item["path"],
                message=item["message"],
                evidence=item["evidence"],
            )
            for item in scan_generated(root)
        ]
    )


# A marker line as git writes it at the default size of 7: one of these
# characters 7 times from column 0, then a space, a tab or the end of the line.
# A longer run, such as a ruler or a longer setext underline, is not a marker.
CONFLICT_MARKER_PATTERN = re.compile(rb"([<|=>])\1{6}(?:[ \t]|$)")


def validate_conflict_markers(root: Path) -> list[dict[str, object]]:
    """Report git merge-conflict markers left in tracked files.

    The squash of #52 (3e22429) committed `<<<<<<< HEAD`, `=======` and
    `>>>>>>> 4de8b5a...` into CHANGELOG.md, and every other check passed it.

    Every tracked file git would merge as text (no NUL byte in its first 8000
    bytes, git's binary test) is read as bytes and split on line feeds, so the
    line numbers are git's; fenced blocks are read too, since a conflict inside
    a code example is still a conflict. `<<<<<<<` and `>>>>>>>` lines always
    count. `=======` and `|||||||` lines count only between a `<<<<<<<` line and
    the next `>>>>>>>` line: alone, `=======` is also the setext underline of a
    7-letter heading. Git never indents a marker, so a document can show one by
    indenting it.
    """
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    # Mid-merge, git lists an unmerged path once per index stage: read it once.
    for relative in sorted(set(git_tracked_files(root))):
        path = root / relative
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue
        in_hunk = False
        for line_number, line in enumerate(data.split(b"\n"), 1):
            if line.endswith(b"\r"):
                line = line[:-1]
            match = CONFLICT_MARKER_PATTERN.match(line)
            if match is None:
                continue
            marker = match.group(1)
            if marker in (b"=", b"|") and not in_hunk:
                continue
            if marker == b"<":
                in_hunk = True
            elif marker == b">":
                in_hunk = False
            findings.append(
                finding(
                    "MERGE-CONFLICT-MARKER",
                    path=relative,
                    line=line_number,
                    message="A tracked file contains a git merge-conflict marker.",
                    evidence=line[:80].decode("utf-8", "replace"),
                )
            )
    return sort_findings(findings)


def validate_repo(root: Path) -> dict[str, object]:
    root = Path(root).resolve()
    checks = {
        "source_map": validate_source_map(root),
        "skills": validate_skills(root),
        "moved_exact": validate_moved_exact(root),
        "generated": validate_generated(root),
        "conflict_markers": validate_conflict_markers(root),
        "claims": validate_claims(root),
        "links": validate_links(root),
        "privacy": validate_privacy(root),
        "licenses": validate_licenses(root),
    }
    findings = [item for result in checks.values() for item in result]
    check_summary = {
        name: {"finding_count": len(result), "verdict": "FAIL" if any(item["severity"] == "error" for item in result) else ("WARN" if result else "PASS")}
        for name, result in checks.items()
    }
    return make_report("validate", root, findings, checks=check_summary)
