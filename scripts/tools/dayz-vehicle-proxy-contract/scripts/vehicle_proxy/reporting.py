from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .audit import AuditInputError, AuditResult


def _json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise AuditInputError(f"report is not strict JSON: {error}") from error
    return (text + "\n").encode("utf-8")


def _summary_bytes(result: AuditResult) -> bytes:
    lines = [
        f"vehicle: {result.vehicle}",
        f"overall_status: {result.overall_status}",
        f"alignment_status: {result.alignment_status}",
        f"nodes: {len(result.nodes)}",
        f"findings: {len(result.findings)}",
    ]
    for finding in result.findings:
        lines.append(
            f"{finding.severity} {finding.code} "
            f"{finding.piece}@{finding.host_lod:g} {finding.path}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _lod_overview(result: AuditResult) -> dict[str, Any]:
    return {
        "vehicle": result.vehicle,
        "nodes": [
            {
                "piece": item.node.piece,
                "host_lod": item.node.host_lod,
                "proxy_basename": item.node.proxy_basename,
                "proxy_path": str(item.node.proxy_path),
                "internal_lods": [preview.internal_lod for preview in item.previews],
                "eligible_operations": list(item.eligible_operations),
            }
            for item in result.nodes
        ],
    }


_REPORT_NAMES = ("report.json", "summary.txt", "lod-overview.json")


@dataclass(frozen=True)
class ReportSnapshot:
    path: Path
    identity: tuple[int, int, int, int]
    sha256: str


def _identity(stat_result: os.stat_result) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def report_files(result: AuditResult) -> dict[str, bytes]:
    return {
        "report.json": _json_bytes(result.as_dict()),
        "summary.txt": _summary_bytes(result),
        "lod-overview.json": _json_bytes(_lod_overview(result)),
    }


def write_report_tree(result: AuditResult, root: Path) -> None:
    """Write reports only inside a caller-owned private directory."""
    root = Path(root)
    if not root.is_dir():
        raise AuditInputError(f"private report root is not a directory: {root}")
    if any(root.iterdir()):
        raise AuditInputError(f"private report root is not empty: {root}")
    try:
        for name, payload in report_files(result).items():
            with (root / name).open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
    except OSError as error:
        raise AuditInputError(f"cannot build report tree in {root}: {error}") from error


def _capture_matching_report(path: Path, expected: bytes) -> ReportSnapshot:
    try:
        with path.open("rb") as handle:
            handle_before = _identity(os.fstat(handle.fileno()))
            path_before = _identity(path.stat())
            payload = handle.read()
            handle_after = _identity(os.fstat(handle.fileno()))
            path_after = _identity(path.stat())
    except OSError as error:
        raise AuditInputError(f"cannot capture existing audit report {path}: {error}") from error
    if not (
        handle_before == path_before == handle_after == path_after
        and len(payload) == handle_before[2]
        and payload == expected
    ):
        raise AuditInputError(
            f"existing audit report does not match current evidence: {path}"
        )
    return ReportSnapshot(
        path,
        handle_before,
        hashlib.sha256(payload).hexdigest().upper(),
    )


def require_matching_reports(
    result: AuditResult, root: Path
) -> tuple[ReportSnapshot, ...]:
    root = Path(root)
    if not root.is_dir():
        raise AuditInputError(f"existing preview output is not an audit directory: {root}")
    expected = report_files(result)
    try:
        actual_names = {item.name for item in root.iterdir()}
        if actual_names != set(_REPORT_NAMES):
            raise AuditInputError(
                f"existing preview output is not the exact audit report set: {root}"
            )
        return tuple(
            _capture_matching_report(root / name, expected[name])
            for name in _REPORT_NAMES
        )
    except OSError as error:
        raise AuditInputError(f"cannot verify existing audit reports in {root}: {error}") from error


def verify_report_snapshots(snapshots: tuple[ReportSnapshot, ...]) -> None:
    for snapshot in snapshots:
        try:
            with snapshot.path.open("rb") as handle:
                handle_before = _identity(os.fstat(handle.fileno()))
                path_before = _identity(snapshot.path.stat())
                digest = hashlib.sha256()
                total = 0
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
                    total += len(block)
                handle_after = _identity(os.fstat(handle.fileno()))
                path_after = _identity(snapshot.path.stat())
        except OSError as error:
            raise AuditInputError(
                f"existing audit report generation is unavailable: {snapshot.path}: {error}"
            ) from error
        if not (
            handle_before
            == path_before
            == handle_after
            == path_after
            == snapshot.identity
            and total == snapshot.identity[2]
            and digest.hexdigest().upper() == snapshot.sha256
        ):
            raise AuditInputError(
                f"existing audit report generation changed during preview: {snapshot.path}"
            )


def write_reports(result: AuditResult, out: Path) -> None:
    destination = Path(out)
    if os.path.lexists(destination):
        raise AuditInputError(f"audit output already exists: {destination}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        transaction = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.vehicle-proxy-reports-",
                dir=destination.parent,
            )
        )
    except OSError as error:
        raise AuditInputError(f"cannot create report transaction: {error}") from error
    committed = False
    try:
        write_report_tree(result, transaction)
        if os.path.lexists(destination):
            raise AuditInputError(f"audit output already exists: {destination}")
        try:
            os.rename(transaction, destination)
        except FileExistsError as error:
            raise AuditInputError(f"audit output already exists: {destination}") from error
        except OSError as error:
            raise AuditInputError(
                f"cannot publish complete report tree {destination}: {error}"
            ) from error
        committed = True
    finally:
        if not committed:
            try:
                shutil.rmtree(transaction)
            except OSError:
                pass


def atomic_json(path: Path, value: Any) -> None:
    destination = Path(path)
    payload = _json_bytes(value)
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except OSError as error:
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
        raise AuditInputError(f"cannot publish JSON {destination}: {error}") from error
