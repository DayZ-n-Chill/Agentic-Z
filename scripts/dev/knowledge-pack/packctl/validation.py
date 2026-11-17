from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

from .generated import scan as scan_generated
from .common import (
    config_path,
    finding,
    git_tracked_files,
    is_relative_contract_path,
    load_json,
    make_report,
    sort_findings,
)


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
ALLOWED_SKILL_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
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
    allowlist_path = config_path(root, LINK_ALLOWLIST_PATH)
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
    for relative in git_tracked_files(root):
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
                            message="A tracked file contains a user-specific absolute path.",
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
                            message="A tracked file contains a token-shaped secret.",
                            evidence="[REDACTED]",
                        )
                    )
                    break
    return sort_findings(findings)


def validate_license_file(root: Path) -> list[dict[str, object]]:
    root = Path(root).resolve()
    if (root / "LICENSE").is_file():
        return []
    return [
        finding(
            "LICENSE-MISSING",
            path="LICENSE",
            line=0,
            message="The repository-level license is missing.",
            evidence="Expected LICENSE.",
        )
    ]


CLAIM_MARKER_PATTERN = re.compile(
    r"(?:\[EXACT\]\[(CLAIM-[A-Z0-9][A-Z0-9-]*)\]|claim:\s*(CLAIM-[A-Z0-9][A-Z0-9-]*))"
)


def validate_claims(root: Path) -> list[dict[str, object]]:
    """Check claim markers under skills/ against the claim registry.

    A marker is `[EXACT][CLAIM-ID]` or `claim: CLAIM-ID` in a tracked text file
    under skills/. Each marker needs an entry in sources/claims.json that names
    the same file and a line range holding the marker, and each entry needs its
    marker. The registry file is optional: without it no claim is registered,
    so every marker is reported.
    """
    root = Path(root).resolve()
    findings: list[dict[str, object]] = []
    registry_path = config_path(root, CLAIMS_PATH)
    registry: object = {"schema_version": 1, "claims": []}
    if registry_path.is_file():
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
    required_root = {"schema_version", "claims"}
    if not isinstance(registry, dict) or set(registry) != required_root or registry.get("schema_version") != 1 or not isinstance(registry.get("claims"), list):
        return [
            finding(
                "CLAIM-SCHEMA-INVALID",
                path=CLAIMS_PATH,
                line=1,
                message="The claim registry root does not match schema v1.",
                evidence="Expected schema_version and claims.",
            )
        ]
    claim_required = {
        "claim_id",
        "path",
        "line_start",
        "line_end",
        "evidence_locator",
        "observed_at",
        "verification_level",
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
        if (
            not is_relative_contract_path(claim["path"])
            or not isinstance(claim["line_start"], int)
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
                    message="A claim has an invalid path, range or verification level.",
                    evidence=claim_id,
                )
            )
            continue
        claims_by_id[claim_id] = claim

    seen_markers: set[str] = set()
    for relative in git_tracked_files(root):
        if not relative.startswith("skills/"):
            continue
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
                            message="A claim marker has no registry entry.",
                            evidence=claim_id,
                        )
                    )
                    continue
                if (
                    claim["path"] != relative
                    or not (int(claim["line_start"]) <= line_number <= int(claim["line_end"]))
                ):
                    findings.append(
                        finding(
                            "CLAIM-RANGE-MISMATCH",
                            path=relative,
                            line=line_number,
                            message="A claim marker lies outside its registered file or line range.",
                            evidence=claim_id,
                        )
                    )
    for claim_id in sorted(set(claims_by_id) - seen_markers):
        findings.append(
            finding(
                "CLAIM-MARKER-MISSING",
                path=CLAIMS_PATH,
                line=1,
                message="A registered claim has no marker in its file.",
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
    marker -- no normalization, no BOM, no CRLF variant. An edit inside a sealed
    body, such as a global rename sweep, shows up here as drift.

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
    editing it by hand, or changing the source without regenerating, is a validation
    failure. The rule lives in `packctl.generated` so the writer and this checker cannot
    disagree about what "in sync" means.
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

    A squash merge can commit `<<<<<<< HEAD`, `=======` and `>>>>>>> <commit>`
    lines into a file, and no other check reports them.

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
        "skills": validate_skills(root),
        "moved_exact": validate_moved_exact(root),
        "generated": validate_generated(root),
        "conflict_markers": validate_conflict_markers(root),
        "claims": validate_claims(root),
        "links": validate_links(root),
        "privacy": validate_privacy(root),
        "license_file": validate_license_file(root),
    }
    findings = [item for result in checks.values() for item in result]
    check_summary = {
        name: {"finding_count": len(result), "verdict": "FAIL" if any(item["severity"] == "error" for item in result) else ("WARN" if result else "PASS")}
        for name, result in checks.items()
    }
    return make_report("validate", root, findings, checks=check_summary)
