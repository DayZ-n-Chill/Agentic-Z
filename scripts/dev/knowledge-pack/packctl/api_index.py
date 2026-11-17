from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from .common import (
    canonical_json_bytes,
    finding,
    is_relative_contract_path,
    make_report,
    sha256_bytes,
    sha256_file,
    sort_findings,
    write_json,
)


API_SCHEMA_VERSION = 1
CLASS_PATTERN = re.compile(
    r"^\s*(?:(?:modded|inherited)\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)"
)
METHOD_PATTERN = re.compile(
    r"^\s*(?:(?:override|static|proto|native|protected|private|const|final|event)\s+)*"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*<[^>]+>)?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)"
)


def _strip_comments_preserve_lines(text: str) -> str:
    output: list[str] = []
    index = 0
    block = False
    string_quote: str | None = None
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if block:
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                block = False
                index += 2
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if string_quote:
            output.append(char)
            if char == "\\" and next_char:
                output.append(next_char)
                index += 2
                continue
            if char == string_quote:
                string_quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            string_quote = char
            output.append(char)
            index += 1
            continue
        if char == "/" and next_char == "*":
            output.extend((" ", " "))
            block = True
            index += 2
            continue
        if char == "/" and next_char == "/":
            while index < len(text) and text[index] != "\n":
                output.append(" ")
                index += 1
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _record_with_hash(record: dict[str, object]) -> dict[str, object]:
    value = dict(record)
    value["record_hash"] = sha256_bytes(
        canonical_json_bytes(record).rstrip(b"\n")
    )
    return value


def _scan_file(
    path: Path,
    *,
    relative_path: str,
    source_revision: str,
) -> list[dict[str, object]]:
    text = _strip_comments_preserve_lines(path.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    class_stack: list[tuple[str, int]] = []
    pending_class: str | None = None
    brace_depth = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        while class_stack and brace_depth < class_stack[-1][1]:
            class_stack.pop()
        class_match = CLASS_PATTERN.match(line)
        if class_match:
            symbol = class_match.group(1)
            signature = line.strip().rstrip("{").strip()
            records.append(
                _record_with_hash(
                    {
                        "symbol": symbol,
                        "kind": "class",
                        "container": class_stack[-1][0] if class_stack else "",
                        "signature": signature,
                        "relative_path": relative_path,
                        "line": line_number,
                        "source_revision": source_revision,
                    }
                )
            )
            pending_class = symbol
        method_match = METHOD_PATTERN.match(line)
        if method_match and not line.lstrip().startswith(
            ("if", "for", "while", "switch", "return")
        ):
            return_type = " ".join(method_match.group(1).split())
            symbol = method_match.group(2)
            arguments = " ".join(method_match.group(3).split())
            records.append(
                _record_with_hash(
                    {
                        "symbol": symbol,
                        "kind": "method",
                        "container": class_stack[-1][0] if class_stack else "",
                        "signature": f"{return_type} {symbol}({arguments})",
                        "relative_path": relative_path,
                        "line": line_number,
                        "source_revision": source_revision,
                    }
                )
            )
        opens = line.count("{")
        closes = line.count("}")
        if pending_class is not None and opens:
            class_stack.append((pending_class, brace_depth + 1))
            pending_class = None
        brace_depth += opens - closes
        while class_stack and brace_depth < class_stack[-1][1]:
            class_stack.pop()
    return records


def _included_files(
    source_root: Path,
    includes: Iterable[str],
) -> tuple[list[Path], list[dict[str, object]]]:
    files: set[Path] = set()
    findings: list[dict[str, object]] = []
    resolved_root = source_root.resolve(strict=True)
    for include in includes:
        if not is_relative_contract_path(include):
            findings.append(
                finding(
                    "API-PATH-ESCAPE",
                    path=str(include),
                    line=0,
                    message="An API-index include is not a safe relative path.",
                    evidence=str(include),
                )
            )
            continue
        candidate = (resolved_root / include).resolve(strict=False)
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            findings.append(
                finding(
                    "API-PATH-ESCAPE",
                    path=str(include),
                    line=0,
                    message="An API-index include resolves outside the allowed root.",
                    evidence=str(include),
                )
            )
            continue
        if not candidate.exists():
            findings.append(
                finding(
                    "API-INCLUDE-MISSING",
                    path=str(include),
                    line=0,
                    message="An API-index include does not exist.",
                    evidence=str(include),
                )
            )
            continue
        candidates = [candidate] if candidate.is_file() else candidate.rglob("*.c")
        for path in candidates:
            resolved = path.resolve(strict=True)
            try:
                resolved.relative_to(resolved_root)
            except ValueError:
                findings.append(
                    finding(
                        "API-PATH-ESCAPE",
                        path=str(include),
                        line=0,
                        message="An included file resolves outside the allowed root.",
                        evidence=str(include),
                    )
                )
                continue
            if resolved.suffix.lower() == ".c":
                files.add(resolved)
    return sorted(files), sort_findings(findings)


def _tree_digest(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_index(
    *,
    source_root: Path,
    includes: list[str],
    output_dir: Path,
    source_id: str,
    source_revision: str,
    dayz_build: str,
) -> dict[str, object]:
    source_root = Path(source_root)
    output_dir = Path(output_dir)
    try:
        files, findings = _included_files(source_root, includes)
    except (OSError, RuntimeError) as error:
        findings = [
            finding(
                "API-ROOT-INVALID",
                path=str(source_root),
                line=0,
                message="The API source root cannot be resolved.",
                evidence=type(error).__name__,
            )
        ]
        files = []
    if findings:
        return make_report("api-index build", source_root, findings)

    records: list[dict[str, object]] = []
    resolved_root = source_root.resolve(strict=True)
    try:
        for path in files:
            records.extend(
                _scan_file(
                    path,
                    relative_path=path.relative_to(resolved_root).as_posix(),
                    source_revision=source_revision,
                )
            )
    except (OSError, UnicodeError) as error:
        return make_report(
            "api-index build",
            source_root,
            [
                finding(
                    "API-SOURCE-READ-ERROR",
                    path="",
                    line=0,
                    message="An included source could not be read as UTF-8.",
                    evidence=type(error).__name__,
                )
            ],
        )
    records.sort(
        key=lambda item: (
            item["symbol"],
            item["kind"],
            item["container"],
            item["relative_path"],
            item["line"],
        )
    )
    metadata = {
        "schema_version": API_SCHEMA_VERSION,
        "dayz_build": dayz_build,
        "source_id": source_id,
        "source_revision": source_revision,
        "tree_digest": _tree_digest(files, resolved_root),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "metadata.json", metadata)
    index_bytes = b"".join(
        canonical_json_bytes(record).rstrip(b"\n") + b"\n" for record in records
    )
    (output_dir / "index.jsonl").write_bytes(index_bytes)
    return make_report(
        "api-index build",
        source_root,
        [],
        artifacts={
            "metadata": str(output_dir / "metadata.json"),
            "index": str(output_dir / "index.jsonl"),
            "record_count": len(records),
        },
    )


def query_index(
    index_dir: Path,
    symbol: str,
    *,
    expected_build: str | None = None,
    expected_schema: int = API_SCHEMA_VERSION,
) -> dict[str, object]:
    index_dir = Path(index_dir)
    findings: list[dict[str, object]] = []
    try:
        metadata = json.loads(
            (index_dir / "metadata.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        findings.append(
            finding(
                "API-INDEX-INVALID",
                path="metadata.json",
                line=0,
                message="API index metadata cannot be loaded.",
                evidence=type(error).__name__,
            )
        )
        metadata = {}
    if metadata.get("schema_version") != expected_schema:
        findings.append(
            finding(
                "API-SCHEMA-MISMATCH",
                path="metadata.json",
                line=0,
                message="The API index schema does not match the requested schema.",
                evidence=f"expected={expected_schema} actual={metadata.get('schema_version')}",
            )
        )
    if expected_build is not None and metadata.get("dayz_build") != expected_build:
        findings.append(
            finding(
                "API-BUILD-MISMATCH",
                path="metadata.json",
                line=0,
                message="The API index build does not match the requested DayZ build.",
                evidence=f"expected={expected_build} actual={metadata.get('dayz_build')}",
            )
        )
    if findings:
        report = make_report("api-index query", index_dir, findings)
        report["records"] = []
        return report
    records: list[dict[str, object]] = []
    try:
        for line in (index_dir / "index.jsonl").read_text(encoding="utf-8").splitlines():
            if line:
                record = json.loads(line)
                if record.get("symbol") == symbol:
                    records.append(record)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        report = make_report(
            "api-index query",
            index_dir,
            [
                finding(
                    "API-INDEX-INVALID",
                    path="index.jsonl",
                    line=0,
                    message="The API index records cannot be loaded.",
                    evidence=type(error).__name__,
                )
            ],
        )
        report["records"] = []
        return report
    report = make_report("api-index query", index_dir, [])
    report["records"] = records
    return report
