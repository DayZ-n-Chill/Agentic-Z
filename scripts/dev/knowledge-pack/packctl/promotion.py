from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .common import (
    canonical_json_bytes,
    durable_rename,
    durable_write_bytes,
    durable_write_json,
    finding,
    git_commit,
    git_is_dirty,
    git_output,
    git_tracked_files,
    is_relative_contract_path,
    is_within,
    load_json,
    make_report,
    sha256_bytes,
    sha256_file,
    sort_findings,
    sync_directory,
    sync_tree,
    tree_digest,
    write_json,
)
from .validation import SOURCE_MAP_PATH


REQUIRED_SKILL_TARGETS = {"claude_user_skills", "agents_user_skills"}
ADJUDICATIONS_PATH = Path("promotions/adjudications.json")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PROMOTION_EXECUTABLE_SUFFIXES = {".ps1", ".psm1", ".bat", ".cmd", ".py"}
# The closed alias list. It is closed in both directions: the scanner only
# reports these tokens, and `_load_promotion_config` rejects a configured alias
# that is not here -- so a payload whose hardcoded path uses a token missing
# from this tuple is neither reported nor localisable, and ships unrunnable.
PROMOTION_PATH_PLACEHOLDERS = (
    "<you>",
    "<runbooks>",
    "<dayz-projects>",
    "<vault>",
    "<skill-source>",
    "<vanilla>",
    "<cf-root>",
    "<claude-appdata>",
    "<tmp>",
)
PROMOTION_PLACEHOLDER_SCANNER_EXCLUSIONS = frozenset(
    {
        # Detector corpus: these carry placeholder tokens because they
        # implement or exercise a detector, not because an operator has to
        # localise them before the file will run.
        "packctl/promotion.py",
        "tests/packctl/test_promotion.py",
        "tests/packctl/test_validation.py",
    }
)
# Prose that reads correctly in the published pack but names something different
# on an installed tree. Unlike a path placeholder, the repository text is the
# finished public wording, so nothing here has to be localised before a file is
# usable and the placeholder scanner deliberately ignores these.
PROMOTION_PHRASE_PLACEHOLDERS = (
    "an external ODOL->MLOD converter (not distributed with this pack)",
    "external ODOL->MLOD converter",
)
# Phrase aliases also reach documentation, which path aliases never do: 31
# published .md files carry <vault>-style tokens on purpose, so widening the
# path-alias suffix set would make the scanner reject them.
PROMOTION_LOCALIZABLE_TEXT_SUFFIXES = {".md"}
PathAliasMap = dict[str, dict[str, str]]
_UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_RECEIPT_V2_EXTRA = frozenset({"installation_id", "bootstrap"})
_PLAN_V2_EXTRA = frozenset({"installation_id", "bootstrap"})


def _is_canonical_uuid_v4(value: object) -> bool:
    if not isinstance(value, str) or _UUID_V4_PATTERN.fullmatch(value) is None:
        return False
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return False
    return parsed.version == 4 and str(parsed) == value


def _path_is_link(path: Path) -> bool:
    try:
        return path.is_symlink() or _is_junction(path)
    except OSError:
        return False


def _abspath_is_within(path: Path, root: Path) -> bool:
    path_abs = os.path.normcase(os.path.abspath(str(path)))
    root_abs = os.path.normcase(os.path.abspath(str(root)))
    return path_abs == root_abs or path_abs.startswith(root_abs + os.sep)


def _logical_chain_linked(path: Path, ceiling: Path) -> bool:
    current = Path(os.path.abspath(str(path)))
    ceiling_abs = Path(os.path.abspath(str(ceiling)))
    while True:
        if _path_is_link(current):
            return True
        if os.path.normcase(str(current)) == os.path.normcase(str(ceiling_abs)):
            return False
        parent = current.parent
        if parent == current or not _abspath_is_within(current, ceiling_abs):
            return False
        current = parent


def _bindings_linked_within_allowed(
    logical: Path,
    allowed: list[Path],
    *,
    resolved: Path | None = None,
) -> bool:
    try:
        resolved_path = (
            resolved
            if resolved is not None
            else Path(os.path.abspath(str(logical))).resolve(strict=False)
        )
    except OSError:
        resolved_path = Path(os.path.abspath(str(logical)))
    return any(
        _logical_chain_linked(logical, root)
        for root in allowed
        if is_within(resolved_path, root)
    )


def _directory_is_empty(path: Path) -> bool:
    if _path_is_link(path) or not path.is_dir():
        return False
    try:
        return next(path.iterdir(), None) is None
    except OSError:
        return False


def _target_absent_or_typed_empty(path: Path, kind: object) -> str | None:
    if _path_is_link(path):
        return "linked"
    try:
        exists = path.exists()
    except OSError:
        return "nonempty"
    if not exists:
        return None
    if kind == "tree":
        if not path.is_dir() or path.is_symlink():
            return "type-mismatch"
        try:
            return None if next(path.iterdir(), None) is None else "nonempty"
        except OSError:
            return "nonempty"
    if kind == "file":
        try:
            if not path.is_file() or path.is_symlink() or path.stat().st_size != 0:
                return "type-mismatch" if path.is_dir() or not path.is_file() else "nonempty"
        except OSError:
            return "nonempty"
        return None
    return "invalid-kind"


def _git_is_ancestor(root: Path, commit: str) -> bool:
    try:
        git_output(root, "merge-base", "--is-ancestor", commit, "HEAD")
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _route_contains(repo_path: str, kind: object, output_path: str) -> bool:
    if kind == "file":
        return output_path == repo_path
    if kind != "tree":
        return False
    if repo_path == ".":
        return True
    prefix = repo_path.rstrip("/") + "/"
    return output_path == repo_path or output_path.startswith(prefix)


def _tracked_projection(root: Path, repo_path: str, kind: object) -> list[str]:
    tracked = git_tracked_files(root)
    if kind == "file":
        return [Path(repo_path).name] if repo_path in tracked else []
    prefix = "" if repo_path == "." else repo_path.rstrip("/") + "/"
    return [
        relative if not prefix else relative[len(prefix) :]
        for relative in tracked
        if not prefix or relative.startswith(prefix)
    ]


def _payload_localizable(
    source: Path,
    source_root: Path | None,
    suffixes: set[str],
) -> bool:
    if source.suffix.lower() not in suffixes:
        return False
    if source_root is None:
        return True
    resolved_root = source_root.resolve(strict=True)
    resolved_source = source.resolve(strict=True)
    if not is_within(resolved_source, resolved_root):
        raise ValueError("projected source escapes repository")
    relative = resolved_source.relative_to(resolved_root).as_posix()
    return relative not in PROMOTION_PLACEHOLDER_SCANNER_EXCLUSIONS


def _is_localizable_payload(
    source: Path,
    source_root: Path | None,
) -> bool:
    return _payload_localizable(
        source,
        source_root,
        PROMOTION_EXECUTABLE_SUFFIXES,
    )


def _is_phrase_localizable_payload(
    source: Path,
    source_root: Path | None,
) -> bool:
    return _payload_localizable(
        source,
        source_root,
        PROMOTION_EXECUTABLE_SUFFIXES | PROMOTION_LOCALIZABLE_TEXT_SUFFIXES,
    )


def _path_alias_has_valid_context(text: str, start: int, kind: str) -> bool:
    if kind != "path" or start == 0:
        return True
    return text[start - 1] in " \t\r\n'\"=([{,;"


def _localized_payload_bytes(
    source: Path,
    path_aliases: PathAliasMap,
    source_root: Path | None,
) -> bytes:
    payload = source.read_bytes()
    if not path_aliases:
        return payload
    mapped: list[str] = []
    if _is_localizable_payload(source, source_root):
        mapped.extend(
            alias
            for alias in PROMOTION_PATH_PLACEHOLDERS
            if alias in path_aliases
        )
    if _is_phrase_localizable_payload(source, source_root):
        mapped.extend(
            alias
            for alias in PROMOTION_PHRASE_PLACEHOLDERS
            if alias in path_aliases
        )
    if not mapped:
        return payload
    # Longest first: one configured phrase can contain another, and regex
    # alternation would otherwise settle for the shorter prefix.
    mapped.sort(key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(alias) for alias in mapped))
    text = payload.decode("utf-8")

    def replace_alias(match: re.Match[str]) -> str:
        token = match.group(0)
        alias_config = path_aliases[token]
        if not _path_alias_has_valid_context(
            text, match.start(), alias_config["kind"]
        ):
            raise ValueError("path alias occurrence has invalid context")
        return alias_config["value"]

    localized = pattern.sub(replace_alias, text)
    return localized.encode("utf-8")


def _projected_file_hash(
    source: Path,
    path_aliases: PathAliasMap | None,
    source_root: Path | None,
) -> str:
    if path_aliases and (
        _is_localizable_payload(source, source_root)
        or _is_phrase_localizable_payload(source, source_root)
    ):
        return sha256_bytes(
            _localized_payload_bytes(source, path_aliases, source_root)
        )
    return sha256_file(source)


def _projection_entries(
    source: Path,
    kind: str,
    source_files: object,
    *,
    path_aliases: PathAliasMap | None = None,
    source_root: Path | None = None,
) -> list[tuple[str, str]]:
    if (
        not isinstance(source_files, list)
        or not source_files
        or not all(
            isinstance(item, str)
            and item != "."
            and is_relative_contract_path(item)
            for item in source_files
        )
        or source_files != sorted(set(source_files))
    ):
        raise ValueError("invalid source projection")
    if kind == "file":
        if source_files != [source.name] or not source.is_file():
            raise ValueError("invalid file projection")
        return [
            (
                source.name,
                _projected_file_hash(source, path_aliases, source_root),
            )
        ]
    if kind != "tree" or not source.is_dir():
        raise ValueError("invalid tree projection")
    resolved_source = source.resolve(strict=True)
    entries: list[tuple[str, str]] = []
    for relative in source_files:
        candidate = (source / relative).resolve(strict=True)
        if not candidate.is_file() or not is_within(candidate, resolved_source):
            raise ValueError("projected source escapes its route")
        entries.append(
            (
                relative,
                _projected_file_hash(candidate, path_aliases, source_root),
            )
        )
    return entries


def _projection_digest(
    source: Path,
    kind: str,
    source_files: object,
    *,
    path_aliases: PathAliasMap | None = None,
    source_root: Path | None = None,
) -> str:
    entries = _projection_entries(
        source,
        kind,
        source_files,
        path_aliases=path_aliases,
        source_root=source_root,
    )
    if kind == "file":
        return entries[0][1]
    material = bytearray()
    for relative, file_hash in sorted(
        entries,
        key=lambda entry: Path(entry[0]),
    ):
        material.extend(relative.encode("utf-8"))
        material.extend(b"\0")
        material.extend(file_hash.encode("ascii"))
        material.extend(b"\n")
    return sha256_bytes(bytes(material))


def _plan_digest(plan: dict[str, object]) -> str:
    material = dict(plan)
    material.pop("plan_digest", None)
    return sha256_bytes(canonical_json_bytes(material))


def _load_object(path: Path, code: str) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    try:
        value = load_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [
            finding(
                code,
                path=path.name,
                line=1,
                message="A promotion contract cannot be loaded as JSON.",
                evidence=type(error).__name__,
            )
        ]
    if not isinstance(value, dict):
        return None, [
            finding(
                code,
                path=path.name,
                line=1,
                message="A promotion contract root must be an object.",
                evidence=type(value).__name__,
            )
        ]
    return value, []


def _routing_findings(
    root: Path,
    promotion_map: dict[str, object],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if set(promotion_map) != {"schema_version", "artifacts"} or promotion_map.get("schema_version") != 1 or not isinstance(promotion_map.get("artifacts"), list):
        return [
            finding(
                "PROMOTION-ROUTING-INVALID",
                path="promotion-map.json",
                line=1,
                message="The promotion map does not match schema v1.",
                evidence="Expected schema_version and artifacts.",
            )
        ]
    required = {
        "artifact_id",
        "repo_path",
        "artifact_kind",
        "applicability",
        "vault_targets",
        "skill_target_ids",
    }
    allowed = required | {"not_applicable_reason"}
    routes_by_id: dict[str, list[dict[str, object]]] = {}
    for index, route in enumerate(promotion_map["artifacts"]):
        if not isinstance(route, dict) or not required.issubset(route) or set(route) - allowed:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="A promotion route has invalid fields.",
                    evidence=f"artifacts[{index}]",
                )
            )
            continue
        artifact_id = str(route["artifact_id"])
        routes_by_id.setdefault(artifact_id, []).append(route)
        if len(routes_by_id[artifact_id]) > 1:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="Promotion artifact identifiers must be unique.",
                    evidence=artifact_id,
                )
            )
        repo_path = str(route["repo_path"])
        if not is_relative_contract_path(repo_path):
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="A route repo_path is not a safe relative path.",
                    evidence=artifact_id,
                )
            )
            continue
        source = root / repo_path
        kind = route["artifact_kind"]
        if kind not in {"file", "tree"} or not source.exists() or (kind == "file") != source.is_file():
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path=repo_path,
                    line=0,
                    message="A routed source is missing or has the wrong artifact kind.",
                    evidence=f"artifact_id={artifact_id} kind={kind}",
                )
            )
        if not isinstance(route["vault_targets"], list) or not route["vault_targets"]:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="Every route requires at least one vault target.",
                    evidence=artifact_id,
                )
            )
        skill_targets = set(route["skill_target_ids"]) if isinstance(route["skill_target_ids"], list) else set()
        applicability = route["applicability"]
        if applicability == "domain_invariant":
            if skill_targets != REQUIRED_SKILL_TARGETS:
                findings.append(
                    finding(
                        "PROMOTION-ROUTING-INVALID",
                        path="promotion-map.json",
                        line=1,
                        message="A domain invariant must route to both installed skill roots.",
                        evidence=f"artifact_id={artifact_id} targets={sorted(skill_targets)}",
                    )
                )
        elif applicability in {"governance", "tooling"}:
            if not skill_targets and not str(route.get("not_applicable_reason", "")).strip():
                findings.append(
                    finding(
                        "PROMOTION-NOT-APPLICABLE-INVALID",
                        path="promotion-map.json",
                        line=1,
                        message="A route without skill targets requires a concrete reason.",
                        evidence=artifact_id,
                    )
                )
        else:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="A route has an unsupported applicability.",
                    evidence=f"artifact_id={artifact_id}",
                )
            )

    try:
        source_map = load_json(root / SOURCE_MAP_PATH)
        expected = [
            (
                str(item["routing_artifact_id"]),
                str(item["output_path"]),
            )
            for item in source_map["artifacts"]
            if isinstance(item, dict)
        ]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        expected = []
    for artifact_id, output_path in sorted(expected):
        matching_routes = routes_by_id.get(artifact_id, [])
        if not any(
            _route_contains(
                str(route.get("repo_path", "")),
                route.get("artifact_kind"),
                output_path,
            )
            for route in matching_routes
        ):
            findings.append(
                finding(
                    "PROMOTION-UNROUTED",
                    path=SOURCE_MAP_PATH,
                    line=0,
                    message=(
                        "A source-map output is not contained by its named "
                        "promotion route."
                    ),
                    evidence=f"artifact_id={artifact_id} output_path={output_path}",
                )
            )
    return sort_findings(findings)


def _path_alias_config_findings(
    config: dict[str, object],
) -> tuple[PathAliasMap, list[dict[str, object]]]:
    if "path_aliases" not in config:
        return {}, []
    value = config.get("path_aliases")
    if not isinstance(value, dict):
        return {}, [
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="path_aliases must be an object.",
                evidence=type(value).__name__,
            )
        ]
    aliases: PathAliasMap = {}
    findings: list[dict[str, object]] = []
    for alias, item in value.items():
        is_path_alias = (
            isinstance(alias, str) and alias in PROMOTION_PATH_PLACEHOLDERS
        )
        is_phrase_alias = (
            isinstance(alias, str) and alias in PROMOTION_PHRASE_PLACEHOLDERS
        )
        if not is_path_alias and not is_phrase_alias:
            findings.append(
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="A path alias is outside the closed alias list.",
                    evidence=str(alias),
                )
            )
            continue
        if not isinstance(item, dict) or set(item) != {"kind", "value"}:
            findings.append(
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="A path alias entry has invalid fields.",
                    evidence=alias,
                )
            )
            continue
        kind = item.get("kind")
        alias_value = item.get("value")
        # The two vocabularies do not mix: a path placeholder cannot claim to be
        # prose, and a phrase cannot borrow the path-context rule.
        allowed_kinds = {"phrase"} if is_phrase_alias else {"path", "fragment"}
        if (
            kind not in allowed_kinds
            or not isinstance(alias_value, str)
            or not alias_value.strip()
        ):
            findings.append(
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="A path alias kind or value is invalid.",
                    evidence=alias,
                )
            )
            continue
        if kind == "path":
            candidate = Path(alias_value)
            valid = candidate.is_absolute() and candidate.exists()
        else:
            candidate = Path(alias_value)
            valid = (
                "\\" not in alias_value
                and "/" not in alias_value
                and not candidate.drive
                and ".." not in alias_value
            )
        if not valid:
            findings.append(
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="A path alias value violates its kind contract.",
                    evidence=f"{alias}:{kind}",
                )
            )
            continue
        aliases[alias] = {
            "kind": str(kind),
            "value": alias_value,
        }
    return aliases, sort_findings(findings)


def _target_config_findings(
    config: dict[str, object],
) -> tuple[
    dict[str, Path],
    list[Path],
    list[Path],
    Path | None,
    PathAliasMap,
    str | None,
    list[dict[str, object]],
]:
    findings: list[dict[str, object]] = []
    required = {
        "schema_version",
        "allowed_physical_roots",
        "forbidden_physical_roots",
        "backup_root",
        "targets",
    }
    fields = set(config)
    version = config.get("schema_version")
    v1_fields = fields == required or fields == required | {"path_aliases"}
    v2_fields = (
        fields == required | {"installation_id"}
        or fields == required | {"path_aliases", "installation_id"}
    )
    if (version == 1 and not v1_fields) or (version == 2 and not v2_fields) or version not in {1, 2}:
        return {}, [], [], None, {}, None, [
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="The local target configuration does not match schema v1 or v2.",
                evidence="Invalid top-level fields.",
            )
        ]
    path_aliases, alias_findings = _path_alias_config_findings(config)
    findings.extend(alias_findings)
    installation_id: str | None = None
    if version == 2:
        if not _is_canonical_uuid_v4(config.get("installation_id")):
            return {}, [], [], None, path_aliases, None, [
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="installation_id must be a canonical lowercase UUID v4.",
                    evidence="installation_id",
                )
            ]
        installation_id = str(config["installation_id"])
    try:
        allowed = [
            Path(item).resolve(strict=True)
            for item in config["allowed_physical_roots"]
        ]
        forbidden = [
            Path(item).resolve(strict=False)
            for item in config["forbidden_physical_roots"]
        ]
        backup_logical = Path(str(config["backup_root"]))
        backup_root = backup_logical.resolve(strict=True)
    except (OSError, TypeError) as error:
        return {}, [], [], None, path_aliases, installation_id, [
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="A configured physical root cannot be resolved.",
                evidence=type(error).__name__,
            )
        ]
    for raw_root in config["allowed_physical_roots"]:
        if _path_is_link(Path(str(raw_root))):
            findings.append(
                finding(
                    "PROMOTION-TARGET-LINKED",
                    path="allowed_physical_roots",
                    line=0,
                    message="A configured allowed root is a symlink or junction.",
                    evidence=str(raw_root),
                )
            )
    if (
        _path_is_link(backup_logical)
        or _contains_links(backup_logical)
        or _bindings_linked_within_allowed(
            backup_logical,
            allowed,
            resolved=backup_root,
        )
    ):
        findings.append(
            finding(
                "PROMOTION-BACKUP-LINKED",
                path="backup_root",
                line=0,
                message="The configured backup root is linked or contains a link.",
                evidence="backup_root",
            )
        )
    if any(is_within(backup_root, blocked) for blocked in forbidden):
        findings.append(
            finding(
                "PROMOTION-BACKUP-FORBIDDEN",
                path="backup_root",
                line=0,
                message="The configured backup root resolves inside a forbidden root.",
                evidence="backup_root",
            )
        )
    elif not any(is_within(backup_root, root) for root in allowed):
        findings.append(
            finding(
                "PROMOTION-BACKUP-ESCAPE",
                path="backup_root",
                line=0,
                message="The configured backup root resolves outside all allowlisted roots.",
                evidence="backup_root",
            )
        )
    targets: dict[str, Path] = {}
    if not isinstance(config["targets"], dict):
        findings.append(
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="targets must be an object.",
                evidence=type(config["targets"]).__name__,
            )
        )
        return (
            targets,
            allowed,
            forbidden,
            backup_root,
            path_aliases,
            installation_id,
            sort_findings(findings),
        )
    for target_id, item in config["targets"].items():
        if not isinstance(item, dict) or set(item) != {"path", "ownership", "writable"}:
            findings.append(
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="A target configuration has invalid fields.",
                    evidence=str(target_id),
                )
            )
            continue
        target_path = Path(os.path.abspath(Path(str(item["path"]))))
        if _path_is_link(target_path):
            findings.append(
                finding(
                    "PROMOTION-TARGET-LINKED",
                    path=str(target_id),
                    line=0,
                    message="A configured target root is a symlink or junction.",
                    evidence=str(target_id),
                )
            )
            continue
        if not target_path.exists() or not target_path.is_dir():
            findings.append(
                finding(
                    "PROMOTION-TARGET-MISSING",
                    path=str(target_id),
                    line=0,
                    message="A configured target root does not exist.",
                    evidence=str(target_id),
                )
            )
            continue
        resolved = target_path.resolve(strict=True)
        if any(is_within(resolved, blocked) for blocked in forbidden):
            findings.append(
                finding(
                    "PROMOTION-TARGET-FORBIDDEN",
                    path=str(target_id),
                    line=0,
                    message="A configured target resolves inside a forbidden root.",
                    evidence=str(target_id),
                )
            )
            continue
        if not any(is_within(resolved, root) for root in allowed):
            findings.append(
                finding(
                    "PROMOTION-TARGET-ESCAPE",
                    path=str(target_id),
                    line=0,
                    message="A configured target resolves outside all allowlisted roots.",
                    evidence=str(target_id),
                )
            )
            continue
        if _bindings_linked_within_allowed(
            target_path,
            allowed,
            resolved=resolved,
        ):
            findings.append(
                finding(
                    "PROMOTION-TARGET-LINKED",
                    path=str(target_id),
                    line=0,
                    message="A configured target root is a symlink or junction.",
                    evidence=str(target_id),
                )
            )
            continue
        if item["ownership"] != "user_owned" or item["writable"] is not True:
            findings.append(
                finding(
                    "PROMOTION-TARGET-READONLY",
                    path=str(target_id),
                    line=0,
                    message="A target is not explicitly user-owned and writable.",
                    evidence=str(target_id),
                )
            )
            continue
        targets[str(target_id)] = target_path
    return (
        targets,
        allowed,
        forbidden,
        backup_root,
        path_aliases,
        installation_id,
        sort_findings(findings),
    )


def _executable_placeholder_findings(
    routes: list[dict[str, object]],
    path_aliases: PathAliasMap,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    scanned: set[str] = set()
    for route in routes:
        source = Path(str(route["_resolved_source"]))
        repo_path = str(route["repo_path"])
        if route["artifact_kind"] == "file":
            candidates = [(repo_path, source)]
        else:
            candidates = [
                (
                    (Path(repo_path) / str(relative)).as_posix(),
                    source / str(relative),
                )
                for relative in route["_source_files"]
            ]
        for relative, candidate in candidates:
            if relative in PROMOTION_PLACEHOLDER_SCANNER_EXCLUSIONS:
                continue
            if candidate.suffix.lower() not in PROMOTION_EXECUTABLE_SUFFIXES:
                continue
            try:
                resolved = candidate.resolve(strict=True)
                key = os.path.normcase(str(resolved))
                if key in scanned:
                    continue
                scanned.add(key)
                lines = resolved.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as error:
                findings.append(
                    finding(
                        "PROMOTION-SOURCE-INVALID",
                        path=relative,
                        line=0,
                        message=(
                            "An executable source payload cannot be scanned "
                            "safely."
                        ),
                        evidence=type(error).__name__,
                    )
                )
                continue
            for line_number, line in enumerate(lines, 1):
                folded = line.casefold()
                for token in PROMOTION_PATH_PLACEHOLDERS:
                    search_start = 0
                    while True:
                        start = folded.find(token, search_start)
                        if start < 0:
                            break
                        observed = line[start : start + len(token)]
                        alias_config = path_aliases.get(token)
                        exact_and_configured = (
                            observed == token and alias_config is not None
                        )
                        if exact_and_configured and _path_alias_has_valid_context(
                            line, start, alias_config["kind"]
                        ):
                            search_start = start + len(token)
                            continue
                        if exact_and_configured:
                            message = (
                                "An executable path alias is not at the start "
                                "of a path."
                            )
                        else:
                            message = (
                                "An executable path alias has no exact local "
                                "configuration."
                            )
                        findings.append(
                            finding(
                                "PROMOTION-CONFIG-INVALID",
                                path="local-targets.json",
                                line=1,
                                message=message,
                                evidence=f"{relative}:{line_number} {observed}",
                            )
                        )
                        break
    return sort_findings(findings)


def _adjudications_from_value(
    value: dict[str, object],
) -> tuple[dict[tuple[str, str], str], list[dict[str, object]]]:
    if (
        set(value) != {"schema_version", "adjudications"}
        or value.get("schema_version") != 1
        or not isinstance(value.get("adjudications"), list)
    ):
        return {}, [
            finding(
                "PROMOTION-ADJUDICATION-INVALID",
                path=ADJUDICATIONS_PATH.as_posix(),
                line=1,
                message="The promotion adjudications do not match schema v1.",
                evidence="Expected schema_version and adjudications.",
            )
        ]
    required = {"artifact_id", "target_id", "observed_digest", "reason"}
    adjudications: dict[tuple[str, str], str] = {}
    findings: list[dict[str, object]] = []
    for index, entry in enumerate(value["adjudications"]):
        valid = (
            isinstance(entry, dict)
            and set(entry) == required
            and all(isinstance(entry[field], str) for field in required)
            and bool(entry["artifact_id"].strip())
            and bool(entry["target_id"].strip())
            and bool(entry["reason"].strip())
            and SHA256_PATTERN.fullmatch(entry["observed_digest"]) is not None
        )
        if not valid:
            findings.append(
                finding(
                    "PROMOTION-ADJUDICATION-INVALID",
                    path=ADJUDICATIONS_PATH.as_posix(),
                    line=1,
                    message="A promotion adjudication has invalid fields.",
                    evidence=f"adjudications[{index}]",
                )
            )
            continue
        key = (entry["artifact_id"], entry["target_id"])
        if key in adjudications:
            findings.append(
                finding(
                    "PROMOTION-ADJUDICATION-INVALID",
                    path=ADJUDICATIONS_PATH.as_posix(),
                    line=1,
                    message="Promotion adjudications must be unique per target.",
                    evidence=f"artifact_id={key[0]} target_id={key[1]}",
                )
            )
            continue
        adjudications[key] = entry["observed_digest"]
    return adjudications, sort_findings(findings)


def _load_adjudications(
    root: Path,
) -> tuple[dict[tuple[str, str], str], list[dict[str, object]]]:
    path = root / ADJUDICATIONS_PATH
    if not path.exists():
        return {}, []
    value, findings = _load_object(path, "PROMOTION-ADJUDICATION-INVALID")
    if value is None:
        return {}, findings
    adjudications, contract_findings = _adjudications_from_value(value)
    return adjudications, sort_findings([*findings, *contract_findings])


def _advance_matching_adjudications(plan: dict[str, object]) -> None:
    root = Path(str(plan["source_root"])).resolve(strict=False)
    path = root / ADJUDICATIONS_PATH
    if not path.exists():
        return
    value, load_findings = _load_object(
        path,
        "PROMOTION-ADJUDICATION-INVALID",
    )
    if value is None:
        first = load_findings[0]
        raise _PromotionIntegrityError(
            "PROMOTION-ADJUDICATION-INVALID",
            str(first["evidence"]),
        )
    adjudications, contract_findings = _adjudications_from_value(value)
    if contract_findings:
        first = contract_findings[0]
        raise _PromotionIntegrityError(
            "PROMOTION-ADJUDICATION-INVALID",
            str(first["evidence"]),
        )

    advances: dict[tuple[str, str], str] = {}
    for operation in plan["operations"]:
        before_digest = str(operation["before_digest"])
        after_digest = str(operation["after_digest"])
        if before_digest == after_digest:
            continue
        artifact_id = str(operation["artifact_id"])
        for target_id in operation["logical_target_ids"]:
            key = (artifact_id, str(target_id))
            if adjudications.get(key) == before_digest:
                advances[key] = after_digest
    if not advances:
        return

    for entry in value["adjudications"]:
        key = (str(entry["artifact_id"]), str(entry["target_id"]))
        after_digest = advances.get(key)
        if after_digest is not None:
            entry["observed_digest"] = after_digest
    durable_write_json(path, value, create_only=False)


_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "transaction_id",
        "source_commit",
        "artifact_ids",
        "target_ids",
        "operations",
        "verdict",
        "completed_at",
    }
)
_RECEIPT_OPERATION_FIELDS = frozenset(
    {
        "artifact_id",
        "physical_alias",
        "logical_target_ids",
        "before_digest",
        "after_digest",
    }
)


def _nonempty_sorted_unique_strings(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
        and value == sorted(set(value))
    )


def _receipt_claimed_pairs(
    receipt: object,
) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if not isinstance(receipt, dict):
        return pairs
    operations = receipt.get("operations")
    if not isinstance(operations, list):
        return pairs
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        artifact_id = operation.get("artifact_id")
        target_ids = operation.get("logical_target_ids")
        if (
            not isinstance(artifact_id, str)
            or not artifact_id.strip()
            or not isinstance(target_ids, list)
        ):
            continue
        for target_id in target_ids:
            if isinstance(target_id, str) and target_id.strip():
                pairs.add((artifact_id, target_id))
    return pairs


def _receipt_schema_version(receipt: dict[str, object]) -> int | None:
    fields = set(receipt)
    version = receipt.get("schema_version")
    if fields == _RECEIPT_FIELDS and version == 1:
        return 1
    if (
        fields == _RECEIPT_FIELDS | _RECEIPT_V2_EXTRA
        and version == 2
        and _is_canonical_uuid_v4(receipt.get("installation_id"))
        and isinstance(receipt.get("bootstrap"), bool)
    ):
        return 2
    return None


def _receipt_contract_is_canonical(
    path: Path,
    receipt: dict[str, object],
) -> bool:
    schema = _receipt_schema_version(receipt)
    if (
        schema is None
        or receipt.get("verdict") != "PASS"
        or not isinstance(receipt.get("transaction_id"), str)
        or re.fullmatch(r"[0-9a-f]{24}", receipt["transaction_id"]) is None
        or path.name != f"{receipt['transaction_id']}.json"
        or not isinstance(receipt.get("source_commit"), str)
        or re.fullmatch(
            r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
            receipt["source_commit"],
        )
        is None
        or not _nonempty_sorted_unique_strings(receipt.get("artifact_ids"))
        or not _nonempty_sorted_unique_strings(receipt.get("target_ids"))
        or not isinstance(receipt.get("operations"), list)
        or not receipt["operations"]
        or not isinstance(receipt.get("completed_at"), str)
    ):
        return False
    try:
        completed = datetime.fromisoformat(
            receipt["completed_at"].replace("Z", "+00:00")
        )
        if completed.tzinfo is None:
            return False
    except ValueError:
        return False

    aliases: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    artifact_ids: set[str] = set()
    target_ids: set[str] = set()
    for operation in receipt["operations"]:
        if not isinstance(operation, dict) or set(operation) != _RECEIPT_OPERATION_FIELDS:
            return False
        artifact_id = operation.get("artifact_id")
        alias = operation.get("physical_alias")
        logical_target_ids = operation.get("logical_target_ids")
        before_digest = operation.get("before_digest")
        after_digest = operation.get("after_digest")
        if (
            not isinstance(artifact_id, str)
            or not artifact_id.strip()
            or not isinstance(alias, str)
            or re.fullmatch(r"physical-[0-9]+", alias) is None
            or alias in aliases
            or not _nonempty_sorted_unique_strings(logical_target_ids)
            or not isinstance(before_digest, str)
            or (
                before_digest != "absent"
                and SHA256_PATTERN.fullmatch(before_digest) is None
            )
            or not isinstance(after_digest, str)
            or SHA256_PATTERN.fullmatch(after_digest) is None
        ):
            return False
        aliases.add(alias)
        artifact_ids.add(artifact_id)
        for target_id in logical_target_ids:
            key = (artifact_id, target_id)
            if key in pairs:
                return False
            pairs.add(key)
            target_ids.add(target_id)
    return (
        receipt["artifact_ids"] == sorted(artifact_ids)
        and receipt["target_ids"] == sorted(target_ids)
    )


def _pairs_have_matching_adjudications(
    pairs: set[tuple[str, str]],
    adjudications: dict[tuple[str, str], str],
    observed_digests: dict[tuple[str, str], str],
) -> bool:
    return bool(pairs) and all(
        key in observed_digests
        and adjudications.get(key) == observed_digests[key]
        for key in pairs
    )


def _append_scoped_receipt_finding(
    findings: list[dict[str, object]],
    *,
    code: str,
    path: str,
    message: str,
    evidence: str,
    pairs: set[tuple[str, str]],
    adjudications: dict[tuple[str, str], str],
    observed_digests: dict[tuple[str, str], str],
) -> None:
    if _pairs_have_matching_adjudications(
        pairs, adjudications, observed_digests
    ):
        return
    findings.append(
        finding(
            code,
            path=path,
            line=1,
            message=message,
            evidence=evidence,
        )
    )


def _relocated_v1_receipt(
    root: Path,
    plan: dict[str, object],
    transaction_id: str,
) -> Path | None:
    """Where a schema-1 receipt sealed in a removed checkout lives in ``root``.

    Schema 1 binds a receipt to the checkout that applied it: the sealed plan
    records that checkout as ``source_root`` and the receipt under it. A
    promotion run from a temporary worktree leaves its receipt committed to
    the repository, and once the worktree is removed the receipt can only be
    read from another checkout. Check and journal sweep accept that move under
    one rule: the sealed ``receipt_path`` is
    ``<source_root>/promotions/receipts/<transaction_id>.json`` and no longer
    exists; in ``root`` the same relative path, with no link on the way, is a
    regular file whose bytes are the blob HEAD stores. Callers still match it
    against the sealed plan and the COMMIT receipt hash, and a check lets it
    explain only targets under this installation's roots
    (``_sealed_targets_within``) and, among those, only the concrete paths it
    wrote that the check writes again (``_same_target_path``). Returns the
    path in ``root``, or None (also when the sealed path cannot be read).
    """
    if plan.get("schema_version") == 2:
        return None
    relative = Path("promotions") / "receipts" / f"{transaction_id}.json"
    sealed_root = plan.get("source_root")
    sealed_path = plan.get("receipt_path")
    if not isinstance(sealed_root, str) or not isinstance(sealed_path, str):
        return None
    expected_sealed = os.path.normcase(
        os.path.normpath(str(Path(sealed_root) / relative))
    )
    if os.path.normcase(os.path.normpath(sealed_path)) != expected_sealed:
        return None
    try:
        os.lstat(sealed_path)
    except FileNotFoundError:
        pass  # gone: the only state in which the copy here may stand in for it
    except OSError:
        return None  # present but unreadable is not gone
    else:
        return None
    candidate = root / relative
    for step in (root / "promotions", root / "promotions" / "receipts", candidate):
        if step.is_symlink() or _is_junction(step):
            return None
    if not candidate.is_file():
        return None
    try:
        head_blob = subprocess.run(
            ["git", "cat-file", "blob", f"HEAD:{relative.as_posix()}"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
        on_disk = candidate.read_bytes()
    except (OSError, subprocess.CalledProcessError):
        return None
    if head_blob != on_disk:
        return None
    return candidate


def _sealed_targets_within(
    plan: dict[str, object],
    target_roots: dict[str, Path],
) -> bool:
    """True when every target the sealed plan wrote is under the root that this
    installation configures for the same logical target.

    A receipt explains the bytes of the directories it wrote. Read from
    another checkout, it may only explain this installation's targets if they
    are those directories, so a repository that shares the backup root but
    installs elsewhere cannot borrow it.
    """
    operations = plan.get("operations")
    if not isinstance(operations, list):
        return False
    for operation in operations:
        paths = operation.get("logical_target_paths") if isinstance(operation, dict) else None
        if not isinstance(paths, dict) or not paths:
            return False
        for target_id, raw_path in paths.items():
            target_root = target_roots.get(str(target_id))
            if target_root is None or not isinstance(raw_path, str):
                return False
            root_text = os.path.normcase(os.path.normpath(str(target_root)))
            path_text = os.path.normcase(os.path.normpath(raw_path))
            if path_text != root_text and not path_text.startswith(
                root_text.rstrip("\\/") + os.sep
            ):
                return False
    return True


def _sealed_logical_paths(plan: dict[str, object]) -> dict[tuple[str, str], str]:
    """(artifact_id, target_id) -> the logical path the sealed plan wrote."""
    paths: dict[tuple[str, str], str] = {}
    for operation in plan.get("operations") or []:
        if not isinstance(operation, dict):
            continue
        for target_id, raw_path in (operation.get("logical_target_paths") or {}).items():
            if isinstance(raw_path, str):
                paths[(str(operation.get("artifact_id")), str(target_id))] = raw_path
    return paths


def _same_target_path(sealed: str | None, current: str | None) -> bool:
    if not isinstance(sealed, str) or not isinstance(current, str):
        return False
    return os.path.normcase(os.path.normpath(sealed)) == os.path.normcase(
        os.path.normpath(current)
    )


def _sealed_receipt_transitions(
    root: Path,
    backup_root: Path,
    path: Path,
    receipt: dict[str, object],
    *,
    portable: bool = False,
    target_roots: dict[str, Path] | None = None,
    current_paths: dict[tuple[str, str], str] | None = None,
) -> tuple[
    list[tuple[tuple[str, str], str, str, str]],
    str | None,
    str,
]:
    transaction_id = str(receipt["transaction_id"])
    relocated_paths: dict[tuple[str, str], str] | None = None
    try:
        receipt_bytes = path.read_bytes()
        plan, events = _load_transaction(backup_root / transaction_id)
    except (OSError, _PromotionIntegrityError) as error:
        evidence = (
            error.evidence
            if isinstance(error, _PromotionIntegrityError)
            else _exception_evidence(error)
        )
        return [], "PROMOTION-RECEIPT-UNSEALED", evidence
    terminal = _terminal_event(events)
    if terminal is None or terminal.get("event_type") != "COMMIT":
        return [], "PROMOTION-RECEIPT-UNSEALED", "commit-event-missing"
    completed_at = terminal["payload"].get("completed_at")
    receipt_hash = terminal["payload"].get("receipt_hash")
    if (
        not isinstance(completed_at, str)
        or not isinstance(receipt_hash, str)
        or SHA256_PATTERN.fullmatch(receipt_hash) is None
    ):
        return [], "PROMOTION-RECEIPT-UNSEALED", "commit-payload-invalid"
    expected_receipt = _receipt_value(plan, completed_at)
    expected_path = Path(str(plan["receipt_path"])).resolve(strict=False)
    if portable:
        if (
            receipt != expected_receipt
            or str(receipt.get("source_commit")) != str(plan.get("source_commit"))
        ):
            return (
                [],
                "PROMOTION-RECEIPT-JOURNAL-MISMATCH",
                "receipt-does-not-match-sealed-plan",
            )
        if not _git_is_ancestor(root, str(receipt["source_commit"])):
            return (
                [],
                "PROMOTION-RECEIPT-COMMIT-NOT-ANCESTOR",
                str(receipt["source_commit"]),
            )
    else:
        read_path = os.path.normcase(str(path.resolve(strict=False)))
        sealed_here = (
            os.path.normcase(str(expected_path)) == read_path
            and Path(str(plan["source_root"])).resolve(strict=False) == root
        )
        relocated = (
            None
            if sealed_here
            else _relocated_v1_receipt(root, plan, transaction_id)
        )
        if receipt != expected_receipt or not (
            sealed_here
            or (
                relocated is not None
                and os.path.normcase(str(relocated.resolve(strict=False)))
                == read_path
            )
        ):
            return (
                [],
                "PROMOTION-RECEIPT-JOURNAL-MISMATCH",
                "receipt-does-not-match-sealed-plan",
            )
        if not sealed_here and (
            target_roots is None or not _sealed_targets_within(plan, target_roots)
        ):
            return (
                [],
                "PROMOTION-RECEIPT-JOURNAL-MISMATCH",
                "relocated-receipt-targets-outside-installation",
            )
        if not sealed_here:
            relocated_paths = _sealed_logical_paths(plan)
    if (
        receipt_bytes != canonical_json_bytes(expected_receipt)
        or sha256_bytes(receipt_bytes) != receipt_hash
    ):
        return [], "PROMOTION-RECEIPT-HASH-MISMATCH", "receipt-hash-mismatch"
    transitions: list[tuple[tuple[str, str], str, str, str]] = []
    for operation in receipt["operations"]:
        for target_id in operation["logical_target_ids"]:
            key = (str(operation["artifact_id"]), str(target_id))
            if relocated_paths is not None and not _same_target_path(
                relocated_paths.get(key), (current_paths or {}).get(key)
            ):
                # Read from another checkout, a receipt explains only the
                # concrete paths it wrote that this check writes again.
                continue
            transitions.append(
                (
                    (str(operation["artifact_id"]), str(target_id)),
                    str(operation["before_digest"]),
                    str(operation["after_digest"]),
                    transaction_id,
                )
            )
    return transitions, None, ""


def _causal_receipt_head(
    transitions: list[tuple[str, str, str]],
) -> tuple[str | None, str | None, str]:
    transitions_by_transaction: dict[str, list[tuple[str, str]]] = {}
    transaction_order: list[str] = []
    for before_digest, after_digest, transaction_id in transitions:
        if transaction_id not in transitions_by_transaction:
            transitions_by_transaction[transaction_id] = []
            transaction_order.append(transaction_id)
        transitions_by_transaction[transaction_id].append(
            (before_digest, after_digest)
        )

    if not transaction_order:
        return None, "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS", "no-unique-state"

    latest_head: str | None = None
    for transaction_id in transaction_order:
        outgoing: dict[tuple[str, str], tuple[str, str]] = {}
        incoming: dict[tuple[str, str], tuple[str, str]] = {}
        no_op_states: set[tuple[str, str]] = set()
        seen_edges: set[
            tuple[tuple[str, str], tuple[str, str]]
        ] = set()
        for before_digest, after_digest in transitions_by_transaction[
            transaction_id
        ]:
            before_occurrence = (before_digest, transaction_id)
            after_occurrence = (after_digest, transaction_id)
            if before_digest == after_digest:
                no_op_states.add(before_occurrence)
                continue
            edge = (before_occurrence, after_occurrence)
            if edge in seen_edges:
                return (
                    None,
                    "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
                    f"duplicate-transition:{transaction_id}",
                )
            seen_edges.add(edge)
            prior_outgoing = outgoing.get(before_occurrence)
            if prior_outgoing is not None:
                return (
                    None,
                    "PROMOTION-RECEIPT-HISTORY-FORK",
                    f"fork-at:{before_digest}",
                )
            prior_incoming = incoming.get(after_occurrence)
            if prior_incoming is not None:
                return (
                    None,
                    "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
                    f"multiple-preimages:{after_digest}",
                )
            outgoing[before_occurrence] = after_occurrence
            incoming[after_occurrence] = before_occurrence

        if not seen_edges:
            if len(no_op_states) == 1:
                latest_head = next(iter(no_op_states))[0]
                continue
            return (
                None,
                "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
                "no-unique-state",
            )

        nodes = set(outgoing) | set(incoming)
        visited: set[tuple[str, str]] = set()
        for start in nodes:
            trail: set[tuple[str, str]] = set()
            current = start
            while current in outgoing and current not in visited:
                if current in trail:
                    return (
                        None,
                        "PROMOTION-RECEIPT-HISTORY-CYCLE",
                        f"cycle-at:{current[0]}",
                    )
                trail.add(current)
                current = outgoing[current]
            visited.update(trail)

        roots = nodes - set(incoming)
        heads = nodes - set(outgoing)
        if len(roots) != 1 or len(heads) != 1:
            return (
                None,
                "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
                f"roots={len(roots)} heads={len(heads)}",
            )
        current = next(iter(roots))
        connected = {current}
        while current in outgoing:
            current = outgoing[current]
            connected.add(current)
        if connected != nodes or not no_op_states.issubset(heads):
            return (
                None,
                "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
                "disconnected-or-non-head-no-op",
            )
        latest_head = next(iter(heads))[0]

    return latest_head, None, ""


def _latest_receipt_digests(
    root: Path,
    backup_root: Path,
    adjudications: dict[tuple[str, str], str],
    observed_digests: dict[tuple[str, str], str],
    *,
    installation_id: str | None = None,
    target_roots: dict[str, Path] | None = None,
    current_paths: dict[tuple[str, str], str] | None = None,
) -> tuple[dict[tuple[str, str], str], list[dict[str, object]], dict[str, int]]:
    receipts_root = root / "promotions" / "receipts"
    transitions_by_key: dict[
        tuple[str, str], list[tuple[str, str, str]]
    ] = {}
    sealed_receipts: list[
        tuple[
            datetime,
            str,
            list[tuple[tuple[str, str], str, str, str]],
        ]
    ] = []
    findings: list[dict[str, object]] = []
    matching = 0
    genesis = 0
    empty_meta = {"matching": 0, "genesis": 0}
    if not receipts_root.exists():
        return {}, findings, empty_meta
    for path in receipts_root.glob("*.json"):
        if path.is_symlink() or _is_junction(path):
            findings.append(
                finding(
                    "PROMOTION-RECEIPT-INVALID",
                    path=path.name,
                    line=1,
                    message="A promotion receipt is linked or unsafe.",
                    evidence=path.name,
                )
            )
            continue
        receipt, load_findings = _load_object(
            path,
            "PROMOTION-RECEIPT-INVALID",
        )
        findings.extend(load_findings)
        if receipt is None:
            continue
        pairs = _receipt_claimed_pairs(receipt)
        if not _receipt_contract_is_canonical(path, receipt):
            _append_scoped_receipt_finding(
                findings,
                code="PROMOTION-RECEIPT-INVALID",
                path=path.name,
                message="A promotion receipt is not canonical.",
                evidence=path.name,
                pairs=pairs,
                adjudications=adjudications,
                observed_digests=observed_digests,
            )
            continue
        schema = _receipt_schema_version(receipt)
        foreign = installation_id is not None and (
            schema != 2 or str(receipt.get("installation_id")) != installation_id
        )
        if foreign:
            continue
        if installation_id is not None:
            matching += 1
        transitions, issue_code, issue_evidence = _sealed_receipt_transitions(
            root,
            backup_root,
            path,
            receipt,
            portable=installation_id is not None,
            target_roots=target_roots,
            current_paths=current_paths,
        )
        if issue_code is not None:
            _append_scoped_receipt_finding(
                findings,
                code=issue_code,
                path=path.name,
                message=(
                    "A promotion receipt is not bound to its canonical "
                    "sealed COMMIT evidence."
                ),
                evidence=issue_evidence,
                pairs=pairs,
                adjudications=adjudications,
                observed_digests=observed_digests,
            )
            continue
        # Sealing above proves this receipt timestamp is the journal COMMIT
        # timestamp. It is therefore safe to use as the semantic order.
        completed_at = datetime.fromisoformat(
            str(receipt["completed_at"]).replace("Z", "+00:00")
        )
        sealed_receipts.append(
            (
                completed_at,
                str(receipt["transaction_id"]),
                transitions,
            )
        )
        if receipt.get("bootstrap") is True:
            genesis += 1

    for _, _, transitions in sorted(
        sealed_receipts,
        key=lambda batch: (batch[0], batch[1]),
    ):
        for key, before_digest, after_digest, transaction_id in transitions:
            transitions_by_key.setdefault(key, []).append(
                (before_digest, after_digest, transaction_id)
            )

    history: dict[tuple[str, str], str] = {}
    for key in sorted(transitions_by_key):
        if observed_digests.get(key) == "absent":
            continue
        head, issue_code, issue_evidence = _causal_receipt_head(
            transitions_by_key[key]
        )
        if issue_code is not None:
            _append_scoped_receipt_finding(
                findings,
                code=issue_code,
                path="promotions/receipts",
                message=(
                    "Promotion receipt history does not have one causal head."
                ),
                evidence=(
                    f"artifact_id={key[0]} target_id={key[1]} "
                    f"detail={issue_evidence}"
                ),
                pairs={key},
                adjudications=adjudications,
                observed_digests=observed_digests,
            )
            continue
        if head is not None:
            history[key] = head
    return history, sort_findings(findings), {"matching": matching, "genesis": genesis}

def _target_is_empty(path: Path) -> bool:
    try:
        if path.is_dir() and not path.is_symlink():
            return next(path.iterdir(), None) is None
        if path.is_file() and not path.is_symlink():
            return path.stat().st_size == 0
    except OSError:
        return False
    return False


def _target_preimage_findings(
    operations: list[dict[str, object]],
    receipt_digests: dict[tuple[str, str], str],
    adjudications: dict[tuple[str, str], str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for operation in operations:
        actual = str(operation["before_digest"])
        if actual == "absent":
            continue
        target = Path(str(operation["target_path"]))
        # Every logical target must be explained on its own key. Callers pass
        # pre-dedup operations, which carry exactly one id, so today this is one
        # iteration; the dedup that merges ids runs later and mutates these dicts
        # in place. Checking only the first id would silently accept a target
        # whose remaining ids have no receipt and no adjudication.
        for raw_target_id in operation["logical_target_ids"]:
            key = (str(operation["artifact_id"]), str(raw_target_id))
            expected = receipt_digests.get(key)
            if expected == actual or adjudications.get(key) == actual:
                continue
            if expected is None and _target_is_empty(target):
                continue
            findings.append(
                finding(
                    "PROMOTION-TARGET-UNEXPLAINED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message=(
                        "The promotion target contains bytes no previous receipt "
                        "explains."
                    ),
                    evidence=(
                        f"target={raw_target_id} "
                        f"expected={expected or 'none'} actual={actual}"
                    ),
                )
            )
    return sort_findings(findings)


def _skill_name(skill_file: Path) -> str | None:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(r"(?m)^name:\s*['\"]?([a-z0-9-]+)", text)
    return match.group(1) if match else None


def _legacy_overlap_findings(
    routes: list[dict[str, object]],
    targets: dict[str, Path],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for route in routes:
        if route["applicability"] != "domain_invariant":
            continue
        source_name = _skill_name(Path(route["_resolved_source"]) / "SKILL.md")
        if not source_name:
            continue
        destination_name = Path(str(route["repo_path"])).name
        for target_id in route["skill_target_ids"]:
            root = targets.get(str(target_id))
            if root is None:
                continue
            for skill_file in sorted(root.glob("*/SKILL.md")):
                if skill_file.parent.name == destination_name:
                    continue
                if _skill_name(skill_file) == source_name:
                    findings.append(
                        finding(
                            "PROMOTION-LEGACY-OVERLAP",
                            path=str(target_id),
                            line=0,
                            message="A legacy installed skill overlaps the promoted skill name.",
                            evidence=f"skill={source_name} legacy={skill_file.parent.name}",
                        )
                    )
    return sort_findings(findings)


def _destination_findings(
    destination: Path,
    artifact_id: str,
    allowed: list[Path],
    forbidden: list[Path],
    *,
    ceiling: Path | None = None,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    resolved = destination.resolve(strict=False)
    parent = destination.parent
    parent_resolved = parent.resolve(strict=False)
    if (
        (ceiling is not None and _logical_chain_linked(parent, ceiling))
        or _bindings_linked_within_allowed(
            parent,
            allowed,
            resolved=parent_resolved,
        )
    ):
        findings.append(
            finding(
                "PROMOTION-TARGET-LINKED",
                path=artifact_id,
                line=0,
                message=(
                    "A routed destination or parent binding is a symlink "
                    "or junction."
                ),
                evidence=artifact_id,
            )
        )
    if any(is_within(resolved, blocked) for blocked in forbidden):
        findings.append(
            finding(
                "PROMOTION-TARGET-FORBIDDEN",
                path=artifact_id,
                line=0,
                message="A routed destination resolves inside a forbidden root.",
                evidence=artifact_id,
            )
        )
    elif not any(is_within(resolved, root) for root in allowed):
        findings.append(
            finding(
                "PROMOTION-TARGET-ESCAPE",
                path=artifact_id,
                line=0,
                message="A routed destination resolves outside all allowlisted roots.",
                evidence=artifact_id,
            )
        )
    if _contains_links(resolved):
        findings.append(
            finding(
                "PROMOTION-TARGET-LINKED",
                path=artifact_id,
                line=0,
                message=(
                    "A routed destination contains a symlink or junction "
                    "that cannot be restored by digest alone."
                ),
                evidence=artifact_id,
            )
        )
    return findings


def _unlink_plan(plan_path: Path | None) -> None:
    if plan_path is not None:
        plan_path.unlink(missing_ok=True)


def _bootstrap_bound_findings(
    backup_root: Path | None,
    operations: list[dict[str, object]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if backup_root is None:
        findings.append(
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="backup_root",
                line=0,
                message="Bootstrap requires a resolved backup root.",
                evidence="backup_root",
            )
        )
        return findings
    if _path_is_link(backup_root) or _contains_links(backup_root):
        findings.append(
            finding(
                "PROMOTION-BACKUP-LINKED",
                path="backup_root",
                line=0,
                message="Bootstrap requires an unlinked backup root.",
                evidence="backup_root",
            )
        )
    elif not _directory_is_empty(backup_root):
        findings.append(
            finding(
                "PROMOTION-BACKUP-NONEMPTY",
                path="backup_root",
                line=0,
                message="Bootstrap requires a completely empty backup root.",
                evidence="backup_root",
            )
        )
    for operation in operations:
        kind = operation["artifact_kind"]
        for target_id, logical_value in operation["logical_target_paths"].items():
            reason = _target_absent_or_typed_empty(Path(str(logical_value)), kind)
            if reason is None:
                continue
            code = (
                "PROMOTION-TARGET-TYPE-MISMATCH"
                if reason == "type-mismatch"
                else "PROMOTION-TARGET-LINKED"
                if reason == "linked"
                else "PROMOTION-TARGET-NONEMPTY"
            )
            findings.append(
                finding(
                    code,
                    path=str(operation["artifact_id"]),
                    line=0,
                    message=(
                        "Bootstrap requires each destination to be absent "
                        "or empty with the routed artifact kind."
                    ),
                    evidence=f"target={target_id} reason={reason}",
                )
            )
    return sort_findings(findings)


def check_promotion(
    root: Path,
    promotion_map_path: Path,
    local_targets_path: Path,
    plan_path: Path | None,
    *,
    bootstrap: bool = False,
) -> dict[str, object]:
    root = Path(root).resolve()
    promotion_map_path = Path(promotion_map_path).resolve()
    local_targets_path = Path(local_targets_path).resolve()
    plan_path = Path(plan_path).resolve() if plan_path is not None else None
    findings: list[dict[str, object]] = []
    if git_is_dirty(root):
        findings.append(
            finding(
                "PROMOTION-DIRTY",
                path=".",
                line=0,
                message="Promotion requires a clean source commit.",
                evidence="git status --porcelain is non-empty",
            )
        )
    promotion_map, map_load_findings = _load_object(
        promotion_map_path, "PROMOTION-ROUTING-INVALID"
    )
    config, config_load_findings = _load_object(
        local_targets_path, "PROMOTION-CONFIG-INVALID"
    )
    findings.extend(map_load_findings)
    findings.extend(config_load_findings)
    if promotion_map is None or config is None:
        return make_report("promote check", root, findings)
    findings.extend(_routing_findings(root, promotion_map))
    (
        targets,
        allowed,
        forbidden,
        backup_root,
        path_aliases,
        installation_id,
        target_findings,
    ) = _target_config_findings(config)
    findings.extend(target_findings)
    if bootstrap and installation_id is None:
        findings.append(
            finding(
                "PROMOTION-BOOTSTRAP-UNSUPPORTED",
                path="local-targets.json",
                line=1,
                message="promote --bootstrap requires local target contract v2.",
                evidence="schema_version",
            )
        )
    if bootstrap and plan_path is None:
        findings.append(
            finding(
                "PROMOTION-BOOTSTRAP-PLAN-REQUIRED",
                path=".",
                line=0,
                message="promote --bootstrap requires --plan.",
                evidence="plan",
            )
        )
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    routes: list[dict[str, object]] = []
    for route_value in promotion_map["artifacts"]:
        route = dict(route_value)
        route["_resolved_source"] = str(
            (root / str(route["repo_path"])).resolve(strict=True)
        )
        route["_source_files"] = _tracked_projection(
            root,
            str(route["repo_path"]),
            route["artifact_kind"],
        )
        if not route["_source_files"]:
            findings.append(
                finding(
                    "PROMOTION-SOURCE-UNTRACKED",
                    path=str(route["repo_path"]),
                    line=0,
                    message="A promotion route has no tracked source files.",
                    evidence=str(route["artifact_id"]),
                )
            )
        if not is_within(Path(str(route["_resolved_source"])), root):
            findings.append(
                finding(
                    "PROMOTION-SOURCE-ESCAPE",
                    path=str(route["repo_path"]),
                    line=0,
                    message="A routed source resolves outside the repository.",
                    evidence=str(route["artifact_id"]),
                )
            )
        routes.append(route)
    findings.extend(_legacy_overlap_findings(routes, targets))
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    findings.extend(_executable_placeholder_findings(routes, path_aliases))
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    adjudications, adjudication_findings = _load_adjudications(root)
    findings.extend(adjudication_findings)
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    commit = git_commit(root)
    raw_operations: list[dict[str, object]] = []
    for route in routes:
        source = Path(str(route["_resolved_source"]))
        source_files = list(route["_source_files"])
        try:
            after_digest = _projection_digest(
                source,
                str(route["artifact_kind"]),
                source_files,
                path_aliases=path_aliases,
                source_root=root,
            )
        except (OSError, ValueError) as error:
            findings.append(
                finding(
                    "PROMOTION-SOURCE-INVALID",
                    path=str(route["repo_path"]),
                    line=0,
                    message="A tracked source projection cannot be read safely.",
                    evidence=f"{route['artifact_id']}:{type(error).__name__}",
                )
            )
            continue
        artifact_id = str(route["artifact_id"])
        for target_id in route["vault_targets"]:
            target_root = targets.get(str(target_id))
            if target_root is None:
                findings.append(
                    finding(
                        "PROMOTION-TARGET-MISSING",
                        path=str(target_id),
                        line=0,
                        message="A routed target has no valid local configuration.",
                        evidence=artifact_id,
                    )
                )
                continue
            logical_destination = target_root / artifact_id / commit
            destination = logical_destination.resolve(strict=False)
            findings.extend(
                _destination_findings(
                    logical_destination,
                    artifact_id,
                    allowed,
                    forbidden,
                    ceiling=target_root,
                )
            )
            raw_operations.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_kind": route["artifact_kind"],
                    "source_path": str(source),
                    "source_files": source_files,
                    "target_path": str(destination),
                    "logical_target_ids": [str(target_id)],
                    "logical_target_paths": {
                        str(target_id): str(logical_destination)
                    },
                    "before_digest": tree_digest(destination),
                    "after_digest": after_digest,
                    "target_role": "vault",
                }
            )
        for target_id in route["skill_target_ids"]:
            target_root = targets.get(str(target_id))
            if target_root is None:
                findings.append(
                    finding(
                        "PROMOTION-TARGET-MISSING",
                        path=str(target_id),
                        line=0,
                        message="A routed target has no valid local configuration.",
                        evidence=artifact_id,
                    )
                )
                continue
            logical_destination = (
                target_root / Path(str(route["repo_path"])).name
            )
            destination = logical_destination.resolve(strict=False)
            findings.extend(
                _destination_findings(
                    logical_destination,
                    artifact_id,
                    allowed,
                    forbidden,
                    ceiling=target_root,
                )
            )
            raw_operations.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_kind": route["artifact_kind"],
                    "source_path": str(source),
                    "source_files": source_files,
                    "target_path": str(destination),
                    "logical_target_ids": [str(target_id)],
                    "logical_target_paths": {
                        str(target_id): str(logical_destination)
                    },
                    "before_digest": tree_digest(destination),
                    "after_digest": after_digest,
                    "target_role": "skill",
                }
            )
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    observed_digests: dict[tuple[str, str], str] = {}
    current_paths: dict[tuple[str, str], str] = {}
    for operation in raw_operations:
        for target_id in operation["logical_target_ids"]:
            observed_digests[(str(operation["artifact_id"]), target_id)] = str(
                operation["before_digest"]
            )
            current_paths[(str(operation["artifact_id"]), target_id)] = str(
                operation["logical_target_paths"][target_id]
            )
    receipt_digests, receipt_findings, receipt_meta = _latest_receipt_digests(
        root,
        backup_root,
        adjudications,
        observed_digests,
        installation_id=installation_id,
        target_roots=targets,
        current_paths=current_paths,
    )
    findings.extend(receipt_findings)
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    if installation_id is not None:
        if bootstrap:
            if receipt_meta["matching"] > 0:
                findings.append(
                    finding(
                        "PROMOTION-INSTALLATION-EXISTS",
                        path="promotions/receipts",
                        line=1,
                        message=(
                            "promote --bootstrap requires zero receipts for "
                            "this installation_id."
                        ),
                        evidence=installation_id,
                    )
                )
        elif receipt_meta["genesis"] == 0:
            findings.append(
                finding(
                    "PROMOTION-INSTALLATION-UNINITIALIZED",
                    path="promotions/receipts",
                    line=1,
                    message=(
                        "A v2 installation requires exactly one sealed "
                        "genesis receipt."
                    ),
                    evidence=installation_id,
                )
            )
        elif receipt_meta["genesis"] != 1:
            findings.append(
                finding(
                    "PROMOTION-INSTALLATION-GENESIS-CONFLICT",
                    path="promotions/receipts",
                    line=1,
                    message="A v2 installation has more than one genesis receipt.",
                    evidence=f"genesis={receipt_meta['genesis']}",
                )
            )
        if any(item["severity"] == "error" for item in findings):
            _unlink_plan(plan_path)
            return make_report("promote check", root, findings)

    if bootstrap:
        findings.extend(
            _bootstrap_bound_findings(backup_root, raw_operations)
        )
        if any(item["severity"] == "error" for item in findings):
            _unlink_plan(plan_path)
            return make_report("promote check", root, findings)

    findings.extend(
        _target_preimage_findings(
            raw_operations,
            receipt_digests,
            adjudications,
        )
    )
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)

    deduped: dict[str, dict[str, object]] = {}
    for operation in raw_operations:
        key = os.path.normcase(str(Path(str(operation["target_path"])).resolve(strict=False)))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = operation
        else:
            if (
                existing["after_digest"] != operation["after_digest"]
                or existing["source_path"] != operation["source_path"]
            ):
                findings.append(
                    finding(
                        "PROMOTION-ALIAS-CONFLICT",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message="Two logical targets alias one path with different content.",
                        evidence=",".join(
                            sorted(
                                set(existing["logical_target_ids"])
                                | set(operation["logical_target_ids"])
                            )
                        ),
                    )
                )
            existing["logical_target_ids"] = sorted(
                set(existing["logical_target_ids"]) | set(operation["logical_target_ids"])
            )
            existing_paths = existing["logical_target_paths"]
            operation_paths = operation["logical_target_paths"]
            for target_id, logical_path in operation_paths.items():
                prior = existing_paths.get(target_id)
                if prior is not None and prior != logical_path:
                    findings.append(
                        finding(
                            "PROMOTION-ALIAS-CONFLICT",
                            path=str(operation["artifact_id"]),
                            line=0,
                            message=(
                                "One logical target identifier maps to multiple "
                                "paths."
                            ),
                            evidence=str(target_id),
                        )
                    )
                existing_paths[target_id] = logical_path
    if any(item["severity"] == "error" for item in findings):
        _unlink_plan(plan_path)
        return make_report("promote check", root, findings)
    operations = sorted(deduped.values(), key=lambda item: os.path.normcase(str(item["target_path"])))
    for index, operation in enumerate(operations, 1):
        operation["physical_alias"] = f"physical-{index:04d}"
    drifted = [
        operation
        for operation in operations
        if operation["before_digest"] != operation["after_digest"]
    ]
    if drifted:
        findings.append(
            finding(
                "PROMOTION-DRIFT",
                severity="warning",
                path="",
                line=0,
                message="One or more configured targets differ from the source commit.",
                evidence=f"operation_count={len(drifted)}",
            )
        )
    transaction_material = {
        "source_commit": commit,
        "promotion_map_hash": sha256_file(promotion_map_path),
        "local_targets_hash": sha256_file(local_targets_path),
        "installation_id": installation_id,
        "bootstrap": bool(bootstrap),
        "operations": [
            {
                "artifact_id": item["artifact_id"],
                "physical_alias": item["physical_alias"],
                "target_path": item["target_path"],
                "logical_target_ids": item["logical_target_ids"],
                "logical_target_paths": item["logical_target_paths"],
                "source_files": item["source_files"],
                "before_digest": item["before_digest"],
                "after_digest": item["after_digest"],
            }
            for item in operations
        ],
    }
    transaction_id = sha256_bytes(
        canonical_json_bytes(transaction_material) + os.urandom(32)
    )[:24]
    receipt_path = root / "promotions" / "receipts" / f"{transaction_id}.json"
    plan = {
        "schema_version": 2 if installation_id is not None else 1,
        "transaction_id": transaction_id,
        "source_root": str(root),
        "source_commit": commit,
        "promotion_map_path": str(promotion_map_path),
        "promotion_map_hash": transaction_material["promotion_map_hash"],
        "local_targets_path": str(local_targets_path),
        "local_targets_hash": transaction_material["local_targets_hash"],
        "backup_root": str(backup_root),
        "allowed_physical_roots": [str(path) for path in allowed],
        "forbidden_physical_roots": [str(path) for path in forbidden],
        "receipt_path": str(receipt_path),
        "artifact_ids": sorted({str(item["artifact_id"]) for item in operations}),
        "target_ids": sorted(
            {
                target_id
                for item in operations
                for target_id in item["logical_target_ids"]
            }
        ),
        "operations": operations,
    }
    if installation_id is not None:
        plan["installation_id"] = installation_id
        plan["bootstrap"] = bool(bootstrap)
    plan["plan_digest"] = _plan_digest(plan)
    artifacts: dict[str, object] = {
        "operation_count": len(operations),
        "logical_target_count": len(plan["target_ids"]),
    }
    if plan_path is not None:
        write_json(plan_path, plan)
        artifacts["plan_path"] = str(plan_path)
    return make_report(
        "promote check",
        root,
        findings,
        artifacts=artifacts,
    )


def _copy_projected_file(
    source: Path,
    destination: Path,
    path_aliases: PathAliasMap | None,
    source_root: Path | None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if path_aliases and (
        _is_localizable_payload(source, source_root)
        or _is_phrase_localizable_payload(source, source_root)
    ):
        destination.write_bytes(
            _localized_payload_bytes(source, path_aliases, source_root)
        )
        shutil.copystat(source, destination)
    else:
        shutil.copy2(source, destination)


def _copy_artifact(
    source: Path,
    destination: Path,
    kind: str,
    source_files: object | None = None,
    *,
    path_aliases: PathAliasMap | None = None,
    source_root: Path | None = None,
) -> None:
    if kind == "tree" and source_files is None:
        if path_aliases:
            raise ValueError("localized tree copy requires a source projection")
        shutil.copytree(source, destination)
    elif kind == "tree":
        entries = _projection_entries(
            source,
            kind,
            source_files,
            path_aliases=path_aliases,
            source_root=source_root,
        )
        destination.mkdir(parents=True, exist_ok=False)
        for relative, _ in entries:
            _copy_projected_file(
                source / relative,
                destination / relative,
                path_aliases,
                source_root,
            )
    else:
        if source_files is not None:
            _projection_entries(
                source,
                kind,
                source_files,
                path_aliases=path_aliases,
                source_root=source_root,
            )
        _copy_projected_file(
            source,
            destination,
            path_aliases,
            source_root,
        )
    sync_tree(destination)
    sync_directory(destination.parent)


def _projection_has_path_placeholders(
    source: Path,
    destination: Path,
    kind: str,
    source_files: object,
    source_root: Path,
) -> tuple[str, str, int] | None:
    entries = _projection_entries(source, kind, source_files)
    resolved_source_root = source_root.resolve(strict=True)
    for relative, _ in entries:
        if kind == "file":
            source_file = source
            destination_file = destination
        else:
            source_file = source / relative
            destination_file = destination / relative
        if not _is_localizable_payload(source_file, source_root):
            continue
        text = destination_file.read_bytes().decode("utf-8")
        for token in PROMOTION_PATH_PLACEHOLDERS:
            match = re.search(re.escape(token), text, re.IGNORECASE)
            if match is None:
                continue
            projected_file = source_file.resolve(strict=True).relative_to(
                resolved_source_root
            ).as_posix()
            observed = match.group(0)
            line_number = text.count("\n", 0, match.start()) + 1
            return projected_file, observed, line_number
    return None


def _remove_artifact(path: Path) -> None:
    if not _path_is_link(path) and not path.exists():
        return
    if path.is_dir() and not _path_is_link(path):
        shutil.rmtree(path, onerror=_retry_readonly_removal)
    else:
        _unlink_readonly_artifact(path)


def _fault(
    fault_at: str | None,
    boundary: str,
    index: int | None = None,
    *,
    aliases: tuple[str, ...] = (),
) -> None:
    value = boundary if index is None else f"{boundary}:{index}"
    candidates = {value}
    for alias in aliases:
        candidates.add(alias if index is None else f"{alias}:{index}")
    if fault_at in candidates:
        raise RuntimeError(f"fault injection at {value}")


def _terminate(
    boundary: str,
    index: int | None = None,
    *,
    recovery: bool,
    explicit: str | None = None,
) -> None:
    value = boundary if index is None else f"{boundary}:{index}"
    environment_name = (
        "PACKCTL_RECOVER_TERMINATE_AT"
        if recovery
        else "PACKCTL_TERMINATE_AT"
    )
    if explicit == value or os.environ.get(environment_name) == value:
        os._exit(97)


def _is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    if checker is not None:
        return bool(checker())
    # Path.is_junction is new in Python 3.12. Before it, read the reparse tag
    # of the link itself, as ntpath.isjunction does.
    if os.name != "nt":
        return False
    try:
        return os.lstat(path).st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    except (OSError, ValueError):
        return False


def _contains_links(path: Path) -> bool:
    if path.is_symlink() or _is_junction(path):
        return True
    if not path.is_dir():
        return False
    for current, directories, files in os.walk(path, followlinks=False):
        current_path = Path(current)
        for name in [*directories, *files]:
            candidate = current_path / name
            if candidate.is_symlink() or _is_junction(candidate):
                return True
    return False


def _validate_plan_paths(plan: dict[str, object]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    root = Path(str(plan["source_root"])).resolve(strict=True)
    allowed = [Path(item).resolve(strict=True) for item in plan["allowed_physical_roots"]]
    forbidden = [Path(item).resolve(strict=False) for item in plan["forbidden_physical_roots"]]
    backup_root = Path(str(plan["backup_root"])).resolve(strict=True)
    if any(is_within(backup_root, blocked) for blocked in forbidden):
        findings.append(
            finding(
                "PROMOTION-BACKUP-FORBIDDEN",
                path="backup_root",
                line=0,
                message="The planned backup root resolves inside a forbidden root.",
                evidence="backup_root",
            )
        )
    elif not any(is_within(backup_root, allowed_root) for allowed_root in allowed):
        findings.append(
            finding(
                "PROMOTION-BACKUP-ESCAPE",
                path="backup_root",
                line=0,
                message="The planned backup root resolves outside all allowlisted roots.",
                evidence="backup_root",
            )
        )
    for operation in plan["operations"]:
        source = Path(str(operation["source_path"])).resolve(strict=True)
        target = Path(str(operation["target_path"])).resolve(strict=False)
        if not is_within(source, root):
            findings.append(
                finding(
                    "PROMOTION-SOURCE-ESCAPE",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned source resolves outside the repository.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        if any(is_within(target, blocked) for blocked in forbidden):
            findings.append(
                finding(
                    "PROMOTION-TARGET-FORBIDDEN",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned target resolves inside a forbidden root.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        elif not any(is_within(target, allowed_root) for allowed_root in allowed):
            findings.append(
                finding(
                    "PROMOTION-TARGET-ESCAPE",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned target resolves outside all allowlisted roots.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        for target_id, logical_value in operation["logical_target_paths"].items():
            logical_target = Path(str(logical_value)).resolve(strict=False)
            if any(is_within(logical_target, blocked) for blocked in forbidden):
                findings.append(
                    finding(
                        "PROMOTION-TARGET-FORBIDDEN",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message=(
                            "A planned logical target resolves inside a "
                            "forbidden root."
                        ),
                        evidence=str(target_id),
                    )
                )
            elif not any(
                is_within(logical_target, allowed_root)
                for allowed_root in allowed
            ):
                findings.append(
                    finding(
                        "PROMOTION-TARGET-ESCAPE",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message=(
                            "A planned logical target resolves outside all "
                            "allowlisted roots."
                        ),
                        evidence=str(target_id),
                    )
                )
    return sort_findings(findings)


def _promotion_state_findings(
    plan: dict[str, object],
    root: Path,
    path_aliases: PathAliasMap,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if git_commit(root) != plan["source_commit"] or git_is_dirty(root):
        findings.append(
            finding(
                "PROMOTION-SOURCE-CHANGED",
                path=".",
                line=0,
                message="The source commit/worktree changed after promote --check.",
                evidence=f"expected_commit={plan['source_commit']}",
            )
        )
    for operation in plan["operations"]:
        source = Path(str(operation["source_path"]))
        target = Path(str(operation["target_path"]))
        resolved_target = target.resolve(strict=False)
        if os.path.normcase(str(resolved_target)) != os.path.normcase(str(target)):
            findings.append(
                finding(
                    "PROMOTION-TARGET-CHANGED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A sealed physical target no longer resolves to itself.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        elif _contains_links(target):
            findings.append(
                finding(
                    "PROMOTION-TARGET-LINKED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message=(
                        "A sealed target contains a symlink or junction "
                        "that cannot be restored by digest alone."
                    ),
                    evidence=str(operation["physical_alias"]),
                )
            )
        for target_id, logical_value in operation["logical_target_paths"].items():
            logical_target = Path(str(logical_value)).resolve(strict=False)
            if os.path.normcase(str(logical_target)) != os.path.normcase(str(target)):
                findings.append(
                    finding(
                        "PROMOTION-LOGICAL-TARGET-CHANGED",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message=(
                            "A logical target no longer resolves to its sealed "
                            "physical destination."
                        ),
                        evidence=str(target_id),
                    )
                )
        try:
            source_digest = _projection_digest(
                source,
                str(operation["artifact_kind"]),
                operation["source_files"],
                path_aliases=path_aliases,
                source_root=root,
            )
        except (OSError, ValueError):
            source_digest = "invalid"
        if source_digest != operation["after_digest"]:
            findings.append(
                finding(
                    "PROMOTION-SOURCE-CHANGED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned source digest changed after promote --check.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        if tree_digest(target) != operation["before_digest"]:
            findings.append(
                finding(
                    "PROMOTION-TARGET-CHANGED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message=(
                        "A target changed after promote --check; "
                        "compare-and-swap rejected."
                    ),
                    evidence=str(operation["physical_alias"]),
                )
            )
    return sort_findings(findings)


_PLAN_FIELDS = {
    "schema_version",
    "transaction_id",
    "source_root",
    "source_commit",
    "promotion_map_path",
    "promotion_map_hash",
    "local_targets_path",
    "local_targets_hash",
    "backup_root",
    "allowed_physical_roots",
    "forbidden_physical_roots",
    "receipt_path",
    "artifact_ids",
    "target_ids",
    "operations",
    "plan_digest",
}


def _plan_contract_is_canonical(plan: dict[str, object]) -> bool:
    fields = set(plan)
    version = plan.get("schema_version")
    if fields == _PLAN_FIELDS and version == 1:
        return True
    if fields == _PLAN_FIELDS | _PLAN_V2_EXTRA and version == 2:
        return (
            _is_canonical_uuid_v4(plan.get("installation_id"))
            and isinstance(plan.get("bootstrap"), bool)
        )
    return False


_EVENT_FIELDS = {
    "schema_version",
    "sequence",
    "transaction_id",
    "event_type",
    "previous_event_hash",
    "payload",
    "event_hash",
}
_EVENT_TYPES = {
    "PENDING",
    "STAGE_READY",
    "BACKUP_READY",
    "TARGET_PUBLISHED",
    "POST_VERIFIED",
    "PRE_RESTORED",
    "COMMIT",
    "ABORT",
}
_TERMINAL_EVENTS = {"COMMIT", "ABORT"}


class _PromotionIntegrityError(RuntimeError):
    def __init__(self, code: str, evidence: str) -> None:
        super().__init__(evidence)
        self.code = code
        self.evidence = evidence


def _exception_evidence(error: BaseException) -> str:
    if isinstance(error, OSError):
        winerror = getattr(error, "winerror", None)
        if isinstance(winerror, int):
            return f"{type(error).__name__}:winerror={winerror}"
        errno = getattr(error, "errno", None)
        if isinstance(errno, int):
            return f"{type(error).__name__}:errno={errno}"
    return type(error).__name__


def _lock_path_for_root(root: Path) -> Path:
    return root.parent / f".{root.name}.packctl.lock"


def _lock_anchor(path: Path) -> Path:
    current = Path(os.path.abspath(str(path)))
    while True:
        parent = current.parent
        if parent.exists() or parent == current:
            return current
        current = parent


class _RootLocks:
    def __init__(self, roots: list[Path]) -> None:
        self.roots = roots
        self.descriptors: list[int] = []

    def __enter__(self) -> "_RootLocks":
        try:
            for root in self.roots:
                lock_path = _lock_path_for_root(root)
                descriptor = os.open(
                    lock_path,
                    os.O_RDWR | os.O_CREAT,
                    0o600,
                )
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"\0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(
                            descriptor,
                            fcntl.LOCK_EX | fcntl.LOCK_NB,
                        )
                except OSError:
                    os.close(descriptor)
                    raise _PromotionIntegrityError(
                        "PROMOTION-LOCK-ACTIVE",
                        os.path.normcase(str(root)),
                    )
                self.descriptors.append(descriptor)
        except Exception:
            self._release()
            raise
        return self

    def _release(self) -> None:
        for descriptor in reversed(self.descriptors):
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                os.close(descriptor)
        self.descriptors.clear()

    def __exit__(self, *_: object) -> None:
        self._release()


def _integrity_report(
    command: str,
    root: Path,
    error: _PromotionIntegrityError,
    *,
    transaction_root: Path | None = None,
) -> dict[str, object]:
    artifacts: dict[str, object] = {
        "requires_intervention": True,
        "exit_code": 2,
    }
    if transaction_root is not None:
        artifacts["transaction_root"] = str(transaction_root)
    return make_report(
        command,
        root,
        [
            finding(
                error.code,
                path="",
                line=0,
                message="Promotion evidence or state failed closed.",
                evidence=error.evidence,
            )
        ],
        artifacts=artifacts,
    )


def _lock_roots_for_plan(plan: dict[str, object]) -> list[Path]:
    allowed_roots = [
        Path(str(item)).resolve(strict=True)
        for item in plan["allowed_physical_roots"]
    ]
    protected = [
        Path(str(operation["target_path"])).resolve(strict=False)
        for operation in plan["operations"]
    ]
    protected.append(Path(str(plan["backup_root"])).resolve(strict=True))
    selected: dict[str, Path] = {}
    for path in protected:
        candidates = [
            allowed
            for allowed in allowed_roots
            if is_within(path, allowed)
        ]
        if not candidates:
            raise _PromotionIntegrityError(
                "PROMOTION-TARGET-ESCAPE",
                "lock-root-unresolved",
            )
        root = max(candidates, key=lambda candidate: len(candidate.parts))
        selected[os.path.normcase(str(root))] = root
        anchor = _lock_anchor(path)
        selected[os.path.normcase(str(anchor))] = anchor
    return sorted(
        selected.values(),
        key=lambda path: os.path.normcase(str(path)),
    )


def _read_events(transaction_root: Path) -> list[dict[str, object]]:
    events_root = transaction_root / "events"
    if (
        not events_root.is_dir()
        or events_root.is_symlink()
        or _is_junction(events_root)
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "events-root-missing-or-unsafe",
        )
    paths = sorted(events_root.glob("*.json"), key=lambda path: path.name)
    if not paths:
        return []
    events: list[dict[str, object]] = []
    previous_hash = "0" * 64
    terminal_seen = False
    for sequence, path in enumerate(paths):
        if (
            path.name != f"{sequence:08d}.json"
            or path.is_symlink()
            or _is_junction(path)
        ):
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                "event-sequence-invalid",
            )
        try:
            event = load_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                f"event-unreadable:{type(error).__name__}",
            ) from error
        if not isinstance(event, dict) or set(event) != _EVENT_FIELDS:
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                "event-schema-invalid",
            )
        if (
            event.get("schema_version") != 1
            or event.get("sequence") != sequence
            or event.get("transaction_id") != transaction_root.name
            or event.get("event_type") not in _EVENT_TYPES
            or event.get("previous_event_hash") != previous_hash
            or not isinstance(event.get("payload"), dict)
            or terminal_seen
        ):
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                "event-contract-invalid",
            )
        material = dict(event)
        event_hash = material.pop("event_hash")
        if (
            not isinstance(event_hash, str)
            or event_hash != sha256_bytes(canonical_json_bytes(material))
        ):
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                "event-hash-mismatch",
            )
        if sequence == 0 and event["event_type"] != "PENDING":
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                "first-event-not-pending",
            )
        if sequence > 0 and event["event_type"] == "PENDING":
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                "duplicate-pending",
            )
        terminal_seen = event["event_type"] in _TERMINAL_EVENTS
        previous_hash = event_hash
        events.append(event)
    return events


def _append_event(
    transaction_root: Path,
    event_type: str,
    payload: dict[str, object],
) -> dict[str, object]:
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unsupported promotion event: {event_type}")
    events = _read_events(transaction_root)
    if events and events[-1]["event_type"] in _TERMINAL_EVENTS:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "event-after-terminal",
        )
    sequence = len(events)
    previous_hash = (
        str(events[-1]["event_hash"]) if events else "0" * 64
    )
    material: dict[str, object] = {
        "schema_version": 1,
        "sequence": sequence,
        "transaction_id": transaction_root.name,
        "event_type": event_type,
        "previous_event_hash": previous_hash,
        "payload": payload,
    }
    event = dict(material)
    event["event_hash"] = sha256_bytes(canonical_json_bytes(material))
    try:
        plan_value = load_json(transaction_root / "plan.json")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            f"sealed-plan-unreadable:{type(error).__name__}",
        ) from error
    if not isinstance(plan_value, dict):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "sealed-plan-invalid",
        )
    _validate_event_semantics(plan_value, [*events, event])
    durable_write_json(
        transaction_root / "events" / f"{sequence:08d}.json",
        event,
        create_only=True,
    )
    return event


def _validate_event_semantics(
    plan: dict[str, object],
    events: list[dict[str, object]],
) -> None:
    operations = {
        str(operation["physical_alias"]): operation
        for operation in plan["operations"]
    }
    changed = {
        alias
        for alias, operation in operations.items()
        if operation["before_digest"] != operation["after_digest"]
    }
    per_type: dict[str, set[str]] = {
        "STAGE_READY": set(),
        "BACKUP_READY": set(),
        "TARGET_PUBLISHED": set(),
        "PRE_RESTORED": set(),
    }
    singleton_counts = {"POST_VERIFIED": 0, "COMMIT": 0, "ABORT": 0}
    for event in events[1:]:
        event_type = str(event["event_type"])
        payload = event["payload"]
        if event_type in per_type:
            alias = payload.get("physical_alias")
            if (
                not isinstance(alias, str)
                or alias not in operations
                or alias in per_type[event_type]
            ):
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    f"{event_type.lower()}-alias-invalid",
                )
            operation = operations[alias]
            if event_type == "STAGE_READY":
                valid = (
                    alias in changed
                    and payload.get("after_digest")
                    == operation["after_digest"]
                )
            elif event_type == "BACKUP_READY":
                valid = (
                    alias in per_type["STAGE_READY"]
                    and payload.get("before_digest")
                    == operation["before_digest"]
                    and payload.get("existed")
                    == (operation["before_digest"] != "absent")
                )
            elif event_type == "TARGET_PUBLISHED":
                valid = (
                    alias in per_type["BACKUP_READY"]
                    and payload.get("after_digest")
                    == operation["after_digest"]
                )
            else:
                valid = set(payload) == {"physical_alias"}
            if not valid:
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    f"{event_type.lower()}-payload-invalid",
                )
            per_type[event_type].add(alias)
        elif event_type in singleton_counts:
            singleton_counts[event_type] += 1
            if singleton_counts[event_type] != 1:
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    f"duplicate-{event_type.lower()}",
                )
            if event_type == "POST_VERIFIED" and (
                per_type["TARGET_PUBLISHED"] != changed
                or per_type["PRE_RESTORED"]
                or payload.get("operation_count") != len(operations)
                or payload.get("logical_target_count")
                != len(plan["target_ids"])
            ):
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    "post-verified-before-all-targets",
                )
            if event_type == "COMMIT" and (
                singleton_counts["POST_VERIFIED"] != 1
                or singleton_counts["ABORT"] != 0
                or per_type["PRE_RESTORED"]
            ):
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    "commit-without-post-verification",
                )
            if event_type == "ABORT" and (
                per_type["PRE_RESTORED"] != set(operations)
                or singleton_counts["COMMIT"] != 0
            ):
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    "abort-without-all-pre-restored",
                )


def _load_transaction(
    transaction_root: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    raw_transaction_root = Path(transaction_root)
    if raw_transaction_root.is_symlink() or _is_junction(
        raw_transaction_root
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "transaction-root-linked",
        )
    transaction_root = raw_transaction_root.resolve(strict=False)
    if (
        not re.fullmatch(r"[0-9a-f]{24}", transaction_root.name)
        or not transaction_root.is_dir()
        or transaction_root.is_symlink()
        or _is_junction(transaction_root)
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "transaction-root-invalid",
        )
    plan_path = transaction_root / "plan.json"
    if (
        not plan_path.is_file()
        or plan_path.is_symlink()
        or _is_junction(plan_path)
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "sealed-plan-missing-or-unsafe",
        )
    try:
        plan = load_json(plan_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            f"sealed-plan-unreadable:{type(error).__name__}",
        ) from error
    if (
        not isinstance(plan, dict)
        or not _plan_contract_is_canonical(plan)
        or plan.get("transaction_id") != transaction_root.name
        or _plan_digest(plan) != plan.get("plan_digest")
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "sealed-plan-invalid",
        )
    backup_root = Path(str(plan["backup_root"])).resolve(strict=True)
    if transaction_root.parent.resolve(strict=True) != backup_root:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "transaction-backup-root-mismatch",
        )
    source_root = Path(str(plan["source_root"])).resolve(strict=False)
    sealed_receipt_path = Path(str(plan["receipt_path"]))
    receipt_path = sealed_receipt_path.resolve(strict=False)
    expected_receipt = (
        source_root
        / "promotions"
        / "receipts"
        / f"{transaction_root.name}.json"
    ).resolve(strict=False)
    if (
        os.path.normcase(str(receipt_path))
        != os.path.normcase(str(expected_receipt))
        or os.path.normcase(str(receipt_path))
        != os.path.normcase(str(sealed_receipt_path))
        or not is_within(receipt_path, source_root)
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "receipt-path-invalid",
        )
    allowed = [
        Path(str(item)).resolve(strict=True)
        for item in plan["allowed_physical_roots"]
    ]
    forbidden = [
        Path(str(item)).resolve(strict=False)
        for item in plan["forbidden_physical_roots"]
    ]
    if (
        not any(is_within(backup_root, root) for root in allowed)
        or any(is_within(backup_root, root) for root in forbidden)
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "backup-root-outside-contract",
        )
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"])).resolve(strict=False)
        if (
            not any(is_within(target, root) for root in allowed)
            or any(is_within(target, root) for root in forbidden)
        ):
            raise _PromotionIntegrityError(
                "PROMOTION-JOURNAL-INVALID",
                f"target-outside-contract:{operation['physical_alias']}",
            )
    events = _read_events(transaction_root)
    if not events:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "pending-event-missing",
        )
    if events[0]["payload"].get("plan_digest") != plan["plan_digest"]:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "pending-plan-digest-mismatch",
        )
    _validate_event_semantics(plan, events)
    return plan, events


def _create_transaction(
    plan: dict[str, object],
) -> Path:
    backup_root = Path(str(plan["backup_root"]))
    transaction_id = str(plan["transaction_id"])
    transaction_root = backup_root / transaction_id
    initializing_root = backup_root / f".{transaction_id}.packctl-init"
    initializing_transaction = initializing_root / transaction_id
    initializing_root.mkdir(exist_ok=False)
    try:
        initializing_transaction.mkdir(exist_ok=False)
        sync_directory(initializing_root)
        (initializing_transaction / "events").mkdir(exist_ok=False)
        sync_directory(initializing_transaction)
        durable_write_json(
            initializing_transaction / "plan.json",
            plan,
            create_only=True,
        )
        _append_event(
            initializing_transaction,
            "PENDING",
            {"plan_digest": plan["plan_digest"]},
        )
        durable_rename(
            initializing_transaction,
            transaction_root,
            replace=False,
        )
        try:
            initializing_root.rmdir()
            sync_directory(backup_root)
        except OSError:
            pass
        return transaction_root
    except Exception:
        _remove_artifact(initializing_root)
        raise


def _logical_state_valid(
    operation: dict[str, object],
    expected_digest: object,
) -> bool:
    target = Path(str(operation["target_path"]))
    for logical_value in operation["logical_target_paths"].values():
        logical = Path(str(logical_value))
        if (
            os.path.normcase(str(logical.resolve(strict=False)))
            != os.path.normcase(str(target.resolve(strict=False)))
            or tree_digest(logical) != expected_digest
        ):
            return False
    return True


def _require_logical_bindings(plan: dict[str, object]) -> None:
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"]))
        for target_id, logical_value in operation[
            "logical_target_paths"
        ].items():
            logical = Path(str(logical_value))
            if (
                os.path.normcase(str(logical.resolve(strict=False)))
                != os.path.normcase(str(target.resolve(strict=False)))
            ):
                raise _PromotionIntegrityError(
                    "PROMOTION-LOGICAL-TARGET-CHANGED",
                    str(target_id),
                )


def _require_physical_bindings(plan: dict[str, object]) -> None:
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"]))
        if os.path.normcase(str(target.resolve(strict=False))) != os.path.normcase(
            str(target)
        ):
            raise _PromotionIntegrityError(
                "PROMOTION-TARGET-CHANGED",
                str(operation["physical_alias"]),
            )


def _require_unlinked_targets(plan: dict[str, object]) -> None:
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"]))
        if _contains_links(target):
            raise _PromotionIntegrityError(
                "PROMOTION-FOREIGN-TARGET",
                f"{operation['physical_alias']}:linked-target",
            )


def _require_plan_state(
    plan: dict[str, object],
    *,
    state: str,
    code: str,
) -> None:
    key = "before_digest" if state == "PRE" else "after_digest"
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"]))
        expected = operation[key]
        if tree_digest(target) != expected or not _logical_state_valid(
            operation,
            expected,
        ):
            raise _PromotionIntegrityError(
                code,
                f"{operation['physical_alias']}:{state}",
            )


def _receipt_value(
    plan: dict[str, object],
    completed_at: str,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": plan["schema_version"],
        "transaction_id": plan["transaction_id"],
        "source_commit": plan["source_commit"],
        "artifact_ids": plan["artifact_ids"],
        "target_ids": plan["target_ids"],
        "operations": [
            {
                "artifact_id": operation["artifact_id"],
                "physical_alias": operation["physical_alias"],
                "logical_target_ids": operation["logical_target_ids"],
                "before_digest": operation["before_digest"],
                "after_digest": operation["after_digest"],
            }
            for operation in plan["operations"]
        ],
        "verdict": "PASS",
        "completed_at": completed_at,
    }
    if plan.get("schema_version") == 2:
        receipt["installation_id"] = plan["installation_id"]
        receipt["bootstrap"] = plan["bootstrap"]
    return receipt


def _publish_or_verify_receipt(
    plan: dict[str, object],
    commit_event: dict[str, object],
    *,
    receipt_path: Path | None = None,
) -> Path:
    completed_at = commit_event["payload"].get("completed_at")
    receipt_hash = commit_event["payload"].get("receipt_hash")
    if not isinstance(completed_at, str) or not isinstance(
        receipt_hash,
        str,
    ):
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "commit-payload-invalid",
        )
    receipt = _receipt_value(plan, completed_at)
    receipt_bytes = canonical_json_bytes(receipt)
    if sha256_bytes(receipt_bytes) != receipt_hash:
        raise _PromotionIntegrityError(
            "PROMOTION-JOURNAL-INVALID",
            "commit-receipt-hash-invalid",
        )
    if receipt_path is None:
        receipt_path = Path(str(plan["receipt_path"]))
    if receipt_path.exists() or receipt_path.is_symlink():
        try:
            existing = receipt_path.read_bytes()
        except OSError as error:
            raise _PromotionIntegrityError(
                "PROMOTION-RECEIPT-CONFLICT",
                _exception_evidence(error),
            ) from error
        if existing != receipt_bytes:
            raise _PromotionIntegrityError(
                "PROMOTION-RECEIPT-CONFLICT",
                "existing-receipt-differs",
            )
        return receipt_path
    try:
        durable_write_bytes(
            receipt_path,
            receipt_bytes,
            create_only=True,
        )
    except FileExistsError:
        if not receipt_path.is_file() or receipt_path.read_bytes() != receipt_bytes:
            raise _PromotionIntegrityError(
                "PROMOTION-RECEIPT-CONFLICT",
                "receipt-create-race",
            )
    return receipt_path


def _operation_paths(
    operation: dict[str, object],
    transaction_id: str,
) -> tuple[Path, Path, Path, Path]:
    target = Path(str(operation["target_path"]))
    return (
        target.parent / f".{target.name}.packctl-stage-{transaction_id}",
        target.parent / f".{target.name}.packctl-old-{transaction_id}",
        target.parent
        / f".{target.name}.packctl-recover-stage-{transaction_id}",
        target.parent
        / f".{target.name}.packctl-recover-post-{transaction_id}",
    )


def _ensure_known_residue(
    path: Path,
    allowed_digests: set[object],
    alias: str,
) -> None:
    if not _path_is_link(path) and not path.exists():
        return
    if _contains_links(path) or tree_digest(path) not in allowed_digests:
        raise _PromotionIntegrityError(
            "PROMOTION-FOREIGN-TARGET",
            f"{alias}:{path.name}",
        )


def _recorded_aliases(
    events: list[dict[str, object]],
    event_type: str,
) -> set[str]:
    return {
        str(event["payload"].get("physical_alias"))
        for event in events
        if event["event_type"] == event_type
    }


def _rollback_to_pre(
    plan: dict[str, object],
    transaction_root: Path,
    *,
    terminate_at: str | None,
    rollback_fault: bool,
    discardable_stages: set[Path] | None = None,
) -> None:
    if rollback_fault:
        raise RuntimeError("rollback fault injection")
    transaction_id = str(plan["transaction_id"])
    events = _read_events(transaction_root)
    restored = _recorded_aliases(events, "PRE_RESTORED")
    staged = _recorded_aliases(events, "STAGE_READY")
    discardable_stages = discardable_stages or set()
    for index in reversed(range(len(plan["operations"]))):
        operation = plan["operations"][index]
        alias = str(operation["physical_alias"])
        target = Path(str(operation["target_path"]))
        before_digest = operation["before_digest"]
        after_digest = operation["after_digest"]
        stage, old, recovery_stage, recovery_post = _operation_paths(
            operation,
            transaction_id,
        )
        _ensure_known_residue(old, {before_digest}, alias)
        _ensure_known_residue(recovery_stage, {before_digest}, alias)
        _ensure_known_residue(recovery_post, {after_digest}, alias)
        current = tree_digest(target)
        if current not in {before_digest, after_digest, "absent"}:
            raise _PromotionIntegrityError(
                "PROMOTION-FOREIGN-TARGET",
                f"{alias}:target",
            )

        if before_digest != "absent" and current != before_digest:
            backup = transaction_root / alias
            if _contains_links(backup) or tree_digest(backup) != before_digest:
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    f"{alias}:backup-invalid",
                )
            if not recovery_stage.exists():
                _copy_artifact(
                    backup,
                    recovery_stage,
                    "tree" if backup.is_dir() else "file",
                )
            _terminate(
                "after_recovery_stage",
                index,
                recovery=True,
                explicit=terminate_at,
            )

        if current == after_digest and before_digest != after_digest:
            if recovery_post.exists() or recovery_post.is_symlink():
                raise _PromotionIntegrityError(
                    "PROMOTION-FOREIGN-TARGET",
                    f"{alias}:duplicate-post",
                )
            durable_rename(target, recovery_post, replace=False)
            current = "absent"
            _terminate(
                "after_recovery_old_move",
                index,
                recovery=True,
                explicit=terminate_at,
            )

        if before_digest == "absent":
            if current != "absent":
                raise _PromotionIntegrityError(
                    "PROMOTION-FOREIGN-TARGET",
                    f"{alias}:expected-absence",
                )
        elif current == "absent":
            if tree_digest(recovery_stage) != before_digest:
                raise _PromotionIntegrityError(
                    "PROMOTION-JOURNAL-INVALID",
                    f"{alias}:recovery-stage-invalid",
                )
            durable_rename(recovery_stage, target, replace=False)
        elif current != before_digest:
            raise _PromotionIntegrityError(
                "PROMOTION-FOREIGN-TARGET",
                f"{alias}:unexpected-state",
            )
        _terminate(
            "after_pre_publish",
            index,
            recovery=True,
            explicit=terminate_at,
        )
        if tree_digest(target) != before_digest or not _logical_state_valid(
            operation,
            before_digest,
        ):
            raise _PromotionIntegrityError(
                "PROMOTION-ROLLBACK-FAILED",
                f"{alias}:pre-readback",
            )
        _terminate(
            "after_pre_verified",
            index,
            recovery=True,
            explicit=terminate_at,
        )
        if alias not in restored:
            _append_event(
                transaction_root,
                "PRE_RESTORED",
                {"physical_alias": alias},
            )
            restored.add(alias)
        if stage.exists() or _path_is_link(stage):
            if _contains_links(stage):
                raise _PromotionIntegrityError(
                    "PROMOTION-FOREIGN-TARGET",
                    f"{alias}:{stage.name}",
                )
            if stage in discardable_stages:
                _remove_artifact(stage)
            elif alias in staged:
                _ensure_known_residue(stage, {after_digest}, alias)
                _remove_artifact(stage)
            else:
                raise _PromotionIntegrityError(
                    "PROMOTION-FOREIGN-TARGET",
                    f"{alias}:{stage.name}",
                )
        for residue, allowed_digests in (
            (old, {before_digest}),
            (recovery_stage, {before_digest}),
            (recovery_post, {after_digest}),
        ):
            _ensure_known_residue(residue, allowed_digests, alias)
            _remove_artifact(residue)

    _require_plan_state(
        plan,
        state="PRE",
        code="PROMOTION-ROLLBACK-FAILED",
    )
    events = _read_events(transaction_root)
    if events[-1]["event_type"] not in _TERMINAL_EVENTS:
        _append_event(
            transaction_root,
            "ABORT",
            {"completed_at": datetime.now(timezone.utc).isoformat()},
        )
    _terminate(
        "after_abort",
        recovery=True,
        explicit=terminate_at,
    )


def _terminal_event(
    events: list[dict[str, object]],
) -> dict[str, object] | None:
    if events and events[-1]["event_type"] in _TERMINAL_EVENTS:
        return events[-1]
    return None


def _validate_terminal_transaction(
    plan: dict[str, object],
    events: list[dict[str, object]],
) -> None:
    terminal = _terminal_event(events)
    if terminal is None:
        raise _PromotionIntegrityError(
            "PROMOTION-RECOVERY-REQUIRED",
            f"{plan['transaction_id']}:pending",
        )
    receipt_path = Path(str(plan["receipt_path"]))
    if terminal["event_type"] == "COMMIT":
        _require_plan_state(
            plan,
            state="POST",
            code="PROMOTION-COMMIT-STATE-INVALID",
        )
        _advance_matching_adjudications(plan)
        _publish_or_verify_receipt(plan, terminal)
    else:
        _require_plan_state(
            plan,
            state="PRE",
            code="PROMOTION-ABORT-STATE-INVALID",
        )
        if receipt_path.exists() or receipt_path.is_symlink():
            raise _PromotionIntegrityError(
                "PROMOTION-RECEIPT-CONFLICT",
                f"{plan['transaction_id']}:receipt-after-abort",
            )


def _scan_transactions(
    backup_root: Path,
    *,
    live_root: Path | None = None,
) -> None:
    try:
        transaction_roots = sorted(
            (
                child
                for child in backup_root.iterdir()
                if re.fullmatch(r"[0-9a-f]{24}", child.name)
            ),
            key=lambda path: path.name,
        )
    except OSError as error:
        raise _PromotionIntegrityError(
            "PROMOTION-RECOVERY-REQUIRED",
            f"backup-root-unreadable:{type(error).__name__}",
        ) from error
    for transaction_root in transaction_roots:
        try:
            prior_plan, prior_events = _load_transaction(transaction_root)
            terminal = _terminal_event(prior_events)
            if terminal is None:
                raise _PromotionIntegrityError(
                    "PROMOTION-RECOVERY-REQUIRED",
                    f"{transaction_root.name}:pending",
                )
            historical_path = Path(str(prior_plan["receipt_path"]))
            if (
                prior_plan.get("schema_version") == 2
                and live_root is not None
            ):
                receipt_path = (
                    Path(live_root)
                    / "promotions"
                    / "receipts"
                    / f"{transaction_root.name}.json"
                )
            else:
                # Same selection rule as a check (_relocated_v1_receipt): the
                # copy in live_root counts only while the sealed path is gone.
                receipt_path = historical_path
                if live_root is not None:
                    relocated = _relocated_v1_receipt(
                        Path(live_root),
                        prior_plan,
                        transaction_root.name,
                    )
                    if relocated is not None:
                        receipt_path = relocated
            if terminal["event_type"] == "COMMIT":
                if (
                    not receipt_path.exists()
                    and not receipt_path.is_symlink()
                ):
                    raise _PromotionIntegrityError(
                        "PROMOTION-RECOVERY-REQUIRED",
                        f"{transaction_root.name}:receipt-missing",
                    )
                _publish_or_verify_receipt(
                    prior_plan,
                    terminal,
                    receipt_path=receipt_path,
                )
            elif receipt_path.exists() or receipt_path.is_symlink():
                raise _PromotionIntegrityError(
                    "PROMOTION-RECEIPT-CONFLICT",
                    f"{transaction_root.name}:receipt-after-abort",
                )
        except _PromotionIntegrityError as error:
            if error.code in {
                "PROMOTION-JOURNAL-INVALID",
                "PROMOTION-RECEIPT-CONFLICT",
                "PROMOTION-COMMIT-STATE-INVALID",
                "PROMOTION-ABORT-STATE-INVALID",
            }:
                evidence = (
                    f"{transaction_root.name}:{error.code}:"
                    f"{error.evidence}"
                )
            else:
                evidence = f"{transaction_root.name}:{error.evidence}"
            raise _PromotionIntegrityError(
                "PROMOTION-RECOVERY-REQUIRED",
                evidence,
            ) from error


def recover_promotion(
    transaction_root: Path,
    *,
    terminate_at: str | None = None,
) -> dict[str, object]:
    transaction_root = Path(transaction_root).absolute()
    fallback_root = transaction_root.parent
    try:
        plan, events = _load_transaction(transaction_root)
        root = Path(str(plan["source_root"])).resolve(strict=False)
        with _RootLocks(_lock_roots_for_plan(plan)):
            plan, events = _load_transaction(transaction_root)
            _require_physical_bindings(plan)
            _require_logical_bindings(plan)
            _require_unlinked_targets(plan)
            terminal = _terminal_event(events)
            if terminal is not None:
                _validate_terminal_transaction(plan, events)
                return make_report(
                    "promote recover",
                    root,
                    [],
                    artifacts={
                        "transaction_root": str(transaction_root),
                        "decision": terminal["event_type"],
                        "receipt_path": (
                            str(plan["receipt_path"])
                            if terminal["event_type"] == "COMMIT"
                            else ""
                        ),
                    },
                )
            _rollback_to_pre(
                plan,
                transaction_root,
                terminate_at=terminate_at,
                rollback_fault=False,
            )
            return make_report(
                "promote recover",
                root,
                [],
                artifacts={
                    "transaction_root": str(transaction_root),
                    "decision": "ABORT",
                },
            )
    except _PromotionIntegrityError as error:
        return _integrity_report(
            "promote recover",
            locals().get("root", fallback_root),
            error,
            transaction_root=transaction_root,
        )
    except Exception as error:
        wrapped = _PromotionIntegrityError(
            "PROMOTION-ROLLBACK-FAILED",
            _exception_evidence(error),
        )
        return _integrity_report(
            "promote recover",
            locals().get("root", fallback_root),
            wrapped,
            transaction_root=transaction_root,
        )


def _load_plan_path_aliases(
    plan: dict[str, object],
) -> tuple[PathAliasMap, list[dict[str, object]]]:
    config, findings = _load_object(
        Path(str(plan["local_targets_path"])),
        "PROMOTION-CONFIG-INVALID",
    )
    if config is None:
        return {}, findings
    path_aliases, alias_findings = _path_alias_config_findings(config)
    return path_aliases, sort_findings([*findings, *alias_findings])


def _load_apply_plan(
    plan_path: Path,
) -> tuple[dict[str, object] | None, Path, list[dict[str, object]]]:
    plan, findings = _load_object(plan_path, "PROMOTION-PLAN-INVALID")
    if plan is None:
        return None, plan_path.parent, findings
    root = Path(str(plan.get("source_root", "."))).resolve()
    if not _plan_contract_is_canonical(plan):
        return None, root, [
            finding(
                "PROMOTION-PLAN-INVALID",
                path=plan_path.name,
                line=1,
                message="The promotion plan does not match the sealed schema.",
                evidence="Invalid plan fields.",
            )
        ]
    if _plan_digest(plan) != plan["plan_digest"]:
        return None, root, [
            finding(
                "PROMOTION-PLAN-TAMPERED",
                path=plan_path.name,
                line=1,
                message="The promotion plan changed after it was sealed.",
                evidence="plan_digest mismatch",
            )
        ]
    contract_findings: list[dict[str, object]] = []
    for path_field, hash_field in (
        ("promotion_map_path", "promotion_map_hash"),
        ("local_targets_path", "local_targets_hash"),
    ):
        try:
            actual_hash = sha256_file(Path(str(plan[path_field])))
        except OSError:
            actual_hash = "unreadable"
        if actual_hash != plan[hash_field]:
            contract_findings.append(
                finding(
                    "PROMOTION-CONTRACT-CHANGED",
                    path=Path(str(plan[path_field])).name,
                    line=1,
                    message="A promotion contract changed after promote --check.",
                    evidence=hash_field,
                )
            )
    contract_findings.extend(_validate_plan_paths(plan))
    live_config, live_load_findings = _load_object(
        Path(str(plan["local_targets_path"])),
        "PROMOTION-CONFIG-INVALID",
    )
    if live_config is None:
        contract_findings.extend(live_load_findings)
    else:
        *_, live_findings = _target_config_findings(live_config)
        contract_findings.extend(live_findings)
    return plan, root, sort_findings(contract_findings)


def apply_promotion(
    plan_path: Path,
    *,
    fault_at: str | None = None,
    rollback_fault: bool = False,
) -> dict[str, object]:
    plan_path = Path(plan_path).resolve()
    plan, root, findings = _load_apply_plan(plan_path)
    path_aliases: PathAliasMap = {}
    if plan is not None:
        path_aliases, alias_findings = _load_plan_path_aliases(plan)
        findings = sort_findings([*findings, *alias_findings])
    if plan is None or findings:
        return make_report("promote apply", root, findings)
    transaction_id = str(plan["transaction_id"])
    backup_base = Path(str(plan["backup_root"]))
    transaction_root = backup_base / transaction_id
    owned_stages: set[Path] = set()
    transaction_created = False
    try:
        with _RootLocks(_lock_roots_for_plan(plan)):
            locked_plan, locked_root, locked_findings = _load_apply_plan(
                plan_path
            )
            locked_aliases: PathAliasMap = {}
            if locked_plan is not None:
                locked_aliases, alias_findings = _load_plan_path_aliases(
                    locked_plan
                )
                locked_findings = sort_findings(
                    [*locked_findings, *alias_findings]
                )
            if locked_plan is None or locked_findings:
                return make_report(
                    "promote apply",
                    locked_root,
                    locked_findings,
                )
            if locked_plan != plan or locked_aliases != path_aliases:
                return make_report(
                    "promote apply",
                    root,
                    [
                        finding(
                            "PROMOTION-PLAN-TAMPERED",
                            path=plan_path.name,
                            line=1,
                            message=(
                                "The promotion plan changed during lock "
                                "acquisition."
                            ),
                            evidence="locked plan or aliases differ",
                        )
                    ],
                )
            if plan.get("bootstrap") is True:
                locked_findings = _bootstrap_bound_findings(
                    Path(str(plan["backup_root"])),
                    list(plan["operations"]),
                )
                if locked_findings:
                    return make_report(
                        "promote apply",
                        root,
                        locked_findings,
                    )
            _scan_transactions(backup_base, live_root=root)
            locked_findings = _promotion_state_findings(
                plan,
                root,
                path_aliases,
            )
            if locked_findings:
                return make_report(
                    "promote apply",
                    root,
                    locked_findings,
                )
            transaction_root = _create_transaction(plan)
            transaction_created = True
            _terminate("after_pending", recovery=False)
            _fault(fault_at, "after_pending")

            for index, operation in enumerate(plan["operations"]):
                source = Path(str(operation["source_path"]))
                target = Path(str(operation["target_path"]))
                alias = str(operation["physical_alias"])
                if operation["before_digest"] == operation["after_digest"]:
                    placeholder = _projection_has_path_placeholders(
                        source,
                        target,
                        str(operation["artifact_kind"]),
                        operation["source_files"],
                        root,
                    )
                    if placeholder is not None:
                        projected_file, token, line_number = placeholder
                        raise _PromotionIntegrityError(
                            "PROMOTION-PLACEHOLDER-IN-EXECUTABLE",
                            (
                                f"{alias}:readback "
                                f"{projected_file}:{line_number} {token}"
                            ),
                        )
                    continue
                stage, old, recovery_stage, recovery_post = _operation_paths(
                    operation,
                    transaction_id,
                )
                for residue in (stage, old, recovery_stage, recovery_post):
                    if residue.exists() or _path_is_link(residue):
                        raise RuntimeError(
                            f"preexisting transaction residue for {alias}"
                        )
                target.parent.mkdir(parents=True, exist_ok=True)
                owned_stages.add(stage)
                _copy_artifact(
                    source,
                    stage,
                    str(operation["artifact_kind"]),
                    operation["source_files"],
                    path_aliases=path_aliases,
                    source_root=root,
                )
                if tree_digest(stage) != operation["after_digest"]:
                    raise RuntimeError(
                        f"staging verification failed for {alias}"
                    )
                placeholder = _projection_has_path_placeholders(
                    source,
                    stage,
                    str(operation["artifact_kind"]),
                    operation["source_files"],
                    root,
                )
                if placeholder is not None:
                    projected_file, token, line_number = placeholder
                    raise _PromotionIntegrityError(
                        "PROMOTION-PLACEHOLDER-IN-EXECUTABLE",
                        (
                            f"{alias}:staging-readback "
                            f"{projected_file}:{line_number} {token}"
                        ),
                    )
                _append_event(
                    transaction_root,
                    "STAGE_READY",
                    {
                        "physical_alias": alias,
                        "after_digest": operation["after_digest"],
                    },
                )
                _terminate("after_stage", index, recovery=False)
                _fault(
                    fault_at,
                    "after_stage",
                    index,
                    aliases=("after_staging",),
                )

                if (
                    _contains_links(target)
                    or os.path.normcase(
                        str(target.resolve(strict=False))
                    )
                    != os.path.normcase(str(target))
                    or tree_digest(target) != operation["before_digest"]
                ):
                    raise _PromotionIntegrityError(
                        "PROMOTION-TARGET-CHANGED",
                        f"{alias}:changed-before-backup",
                    )
                backup = transaction_root / alias
                existed = target.exists() or target.is_symlink()
                if existed:
                    _copy_artifact(
                        target,
                        backup,
                        (
                            "tree"
                            if target.is_dir() and not target.is_symlink()
                            else "file"
                        ),
                    )
                    if tree_digest(backup) != operation["before_digest"]:
                        raise RuntimeError(
                            f"backup verification failed for {alias}"
                        )
                else:
                    durable_write_bytes(
                        transaction_root / f"{alias}.absent",
                        b"absent\n",
                        create_only=True,
                    )
                _append_event(
                    transaction_root,
                    "BACKUP_READY",
                    {
                        "physical_alias": alias,
                        "before_digest": operation["before_digest"],
                        "existed": existed,
                    },
                )
                _terminate("after_backup", index, recovery=False)
                _fault(fault_at, "after_backup", index)

                if (
                    _contains_links(target)
                    or os.path.normcase(
                        str(target.resolve(strict=False))
                    )
                    != os.path.normcase(str(target))
                    or tree_digest(target) != operation["before_digest"]
                ):
                    raise _PromotionIntegrityError(
                        "PROMOTION-TARGET-CHANGED",
                        f"{alias}:changed-after-backup",
                    )
                if existed:
                    durable_rename(target, old, replace=False)
                _terminate("after_old_move", index, recovery=False)
                _fault(fault_at, "after_old_move", index)
                durable_rename(stage, target, replace=False)
                _terminate("after_publish", index, recovery=False)
                if tree_digest(target) != operation["after_digest"]:
                    raise RuntimeError(
                        f"readback verification failed for {alias}"
                    )
                placeholder = _projection_has_path_placeholders(
                    source,
                    target,
                    str(operation["artifact_kind"]),
                    operation["source_files"],
                    root,
                )
                if placeholder is not None:
                    projected_file, token, line_number = placeholder
                    raise _PromotionIntegrityError(
                        "PROMOTION-PLACEHOLDER-IN-EXECUTABLE",
                        (
                            f"{alias}:target-readback "
                            f"{projected_file}:{line_number} {token}"
                        ),
                    )
                _append_event(
                    transaction_root,
                    "TARGET_PUBLISHED",
                    {
                        "physical_alias": alias,
                        "after_digest": operation["after_digest"],
                    },
                )
                _terminate("after_target_event", index, recovery=False)
                _fault(
                    fault_at,
                    "after_publish",
                    index,
                    aliases=("after_replace",),
                )
                _fault(fault_at, "after_readback", index)

            _require_plan_state(
                plan,
                state="POST",
                code="PROMOTION-POST-VERIFY-FAILED",
            )
            _append_event(
                transaction_root,
                "POST_VERIFIED",
                {
                    "operation_count": len(plan["operations"]),
                    "logical_target_count": len(plan["target_ids"]),
                },
            )
            _terminate("after_post_verified", recovery=False)
            _fault(fault_at, "after_post_verified")

            for operation in plan["operations"]:
                stage, old, recovery_stage, recovery_post = _operation_paths(
                    operation,
                    transaction_id,
                )
                for residue, allowed in (
                    (stage, {operation["after_digest"]}),
                    (old, {operation["before_digest"]}),
                    (recovery_stage, {operation["before_digest"]}),
                    (recovery_post, {operation["after_digest"]}),
                ):
                    _ensure_known_residue(
                        residue,
                        allowed,
                        str(operation["physical_alias"]),
                    )
                    _remove_artifact(residue)

            _require_plan_state(
                plan,
                state="POST",
                code="PROMOTION-POST-VERIFY-FAILED",
            )
            completed_at = datetime.now(timezone.utc).isoformat()
            receipt = _receipt_value(plan, completed_at)
            receipt_hash = sha256_bytes(canonical_json_bytes(receipt))
            commit_event = _append_event(
                transaction_root,
                "COMMIT",
                {
                    "completed_at": completed_at,
                    "receipt_hash": receipt_hash,
                },
            )
            _terminate("after_commit", recovery=False)
            _fault(fault_at, "after_commit")
            _advance_matching_adjudications(plan)
            receipt_path = _publish_or_verify_receipt(plan, commit_event)
            return make_report(
                "promote apply",
                root,
                [],
                artifacts={
                    "receipt_path": str(receipt_path),
                    "transaction_root": str(transaction_root),
                    "operation_count": len(plan["operations"]),
                    "logical_target_count": len(plan["target_ids"]),
                },
            )
    except _PromotionIntegrityError as error:
        if error.code == "PROMOTION-LOCK-ACTIVE":
            return _integrity_report(
                "promote apply",
                root,
                error,
                transaction_root=(
                    transaction_root
                    if transaction_root.exists()
                    else None
                ),
            )
        if not transaction_created:
            return _integrity_report(
                "promote apply",
                root,
                error,
                transaction_root=(
                    transaction_root
                    if transaction_root.exists()
                    else None
                ),
            )
        try:
            with _RootLocks(_lock_roots_for_plan(plan)):
                _, events = _load_transaction(transaction_root)
                if _terminal_event(events) is not None:
                    return _integrity_report(
                        "promote apply",
                        root,
                        error,
                        transaction_root=transaction_root,
                    )
                _rollback_to_pre(
                    plan,
                    transaction_root,
                    terminate_at=None,
                    rollback_fault=rollback_fault,
                    discardable_stages=owned_stages,
                )
        except Exception as rollback_error:
            wrapped = (
                rollback_error
                if isinstance(rollback_error, _PromotionIntegrityError)
                else _PromotionIntegrityError(
                    "PROMOTION-ROLLBACK-FAILED",
                    _exception_evidence(rollback_error),
                )
            )
            return make_report(
                "promote apply",
                root,
                [
                    finding(
                        "PROMOTION-APPLY-FAILED",
                        path=plan_path.name,
                        line=0,
                        message=(
                            "Promotion failed and did not publish a "
                            "success receipt."
                        ),
                        evidence=_exception_evidence(error),
                    ),
                    finding(
                        "PROMOTION-ROLLBACK-FAILED",
                        path=plan_path.name,
                        line=0,
                        message=(
                            "Rollback could not restore and verify all PRE "
                            "states."
                        ),
                        evidence=wrapped.evidence,
                    ),
                ],
                artifacts={
                    "transaction_root": str(transaction_root),
                    "requires_intervention": True,
                    "exit_code": 2,
                },
            )
        return make_report(
            "promote apply",
            root,
            [
                finding(
                    "PROMOTION-APPLY-FAILED",
                    path=plan_path.name,
                    line=0,
                    message=(
                        "Promotion failed, restored PRE, and did not "
                        "publish a success receipt."
                    ),
                    evidence=(
                        f"{error.code} {error.evidence}"
                        if error.code
                        == "PROMOTION-PLACEHOLDER-IN-EXECUTABLE"
                        else error.code
                    ),
                )
            ],
            artifacts={"transaction_root": str(transaction_root)},
        )
    except Exception as error:
        if not transaction_created:
            if transaction_root.exists():
                return _integrity_report(
                    "promote apply",
                    root,
                    _PromotionIntegrityError(
                        "PROMOTION-JOURNAL-INVALID",
                        "transaction-initialization-incomplete",
                    ),
                    transaction_root=transaction_root,
                )
            return make_report(
                "promote apply",
                root,
                [
                    finding(
                        "PROMOTION-APPLY-FAILED",
                        path=plan_path.name,
                        line=0,
                        message=(
                            "Promotion failed before publishing a "
                            "transaction."
                        ),
                        evidence=_exception_evidence(error),
                    )
                ],
            )
        try:
            with _RootLocks(_lock_roots_for_plan(plan)):
                _, events = _load_transaction(transaction_root)
                if _terminal_event(events) is not None:
                    return _integrity_report(
                        "promote apply",
                        root,
                        _PromotionIntegrityError(
                            "PROMOTION-RECOVERY-REQUIRED",
                            _exception_evidence(error),
                        ),
                        transaction_root=transaction_root,
                    )
                _rollback_to_pre(
                    plan,
                    transaction_root,
                    terminate_at=None,
                    rollback_fault=rollback_fault,
                    discardable_stages=owned_stages,
                )
        except Exception as rollback_error:
            evidence = (
                rollback_error.evidence
                if isinstance(rollback_error, _PromotionIntegrityError)
                else _exception_evidence(rollback_error)
            )
            return make_report(
                "promote apply",
                root,
                [
                    finding(
                        "PROMOTION-APPLY-FAILED",
                        path=plan_path.name,
                        line=0,
                        message=(
                            "Promotion failed and did not publish a "
                            "success receipt."
                        ),
                        evidence=_exception_evidence(error),
                    ),
                    finding(
                        "PROMOTION-ROLLBACK-FAILED",
                        path=plan_path.name,
                        line=0,
                        message=(
                            "Rollback could not restore and verify all PRE "
                            "states."
                        ),
                        evidence=evidence,
                    ),
                ],
                artifacts={
                    "transaction_root": str(transaction_root),
                    "requires_intervention": True,
                    "exit_code": 2,
                },
            )
        return make_report(
            "promote apply",
            root,
            [
                finding(
                    "PROMOTION-APPLY-FAILED",
                    path=plan_path.name,
                    line=0,
                    message=(
                        "Promotion failed, restored PRE, and did not "
                        "publish a success receipt."
                    ),
                    evidence=_exception_evidence(error),
                )
            ],
            artifacts={"transaction_root": str(transaction_root)},
        )


def _make_removable(path: Path, error: BaseException) -> None:
    import stat

    if os.name != "nt" or not isinstance(error, PermissionError):
        raise error
    file_stat = path.stat()
    if not file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
        raise error
    path.chmod(file_stat.st_mode | stat.S_IWRITE)


def _retry_readonly_removal(
    function,
    raw_path: str,
    exc_info: tuple[object, BaseException, object],
) -> None:
    _make_removable(Path(raw_path), exc_info[1])
    function(raw_path)


def _unlink_readonly_artifact(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError as error:
        _make_removable(path, error)
        path.unlink()
