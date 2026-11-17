from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        data = canonical_json_bytes(value)
    else:
        data = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


_WINDOWS_TRANSIENT_RENAME_ERRORS = frozenset({5, 32, 33})
_WINDOWS_RENAME_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.0)


def _windows_move_file_ex(
    source: Path,
    destination: Path,
    flags: int,
) -> tuple[bool, int, str]:
    import ctypes

    move_file_ex = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    ).MoveFileExW
    move_file_ex.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    move_file_ex.restype = ctypes.c_int
    if move_file_ex(str(source), str(destination), flags):
        return True, 0, ""
    error = ctypes.get_last_error()
    return False, error, ctypes.FormatError(error)


def _sleep_before_windows_rename_retry(delay: float) -> None:
    time.sleep(delay)


def durable_rename(
    source: Path,
    destination: Path,
    *,
    replace: bool,
) -> None:
    source = Path(source)
    destination = Path(destination)
    if os.name == "nt":
        flags = 0x00000008
        if replace:
            flags |= 0x00000001
        for attempt in range(len(_WINDOWS_RENAME_RETRY_DELAYS) + 1):
            moved, error, message = _windows_move_file_ex(
                source,
                destination,
                flags,
            )
            if moved:
                return
            source_exists = source.exists() or source.is_symlink()
            destination_exists = (
                destination.exists() or destination.is_symlink()
            )
            retryable_state = source_exists and (
                replace or not destination_exists
            )
            if (
                error not in _WINDOWS_TRANSIENT_RENAME_ERRORS
                or attempt == len(_WINDOWS_RENAME_RETRY_DELAYS)
                or not retryable_state
            ):
                raise OSError(
                    None,
                    message,
                    str(destination),
                    error,
                )
            _sleep_before_windows_rename_retry(
                _WINDOWS_RENAME_RETRY_DELAYS[attempt]
            )
    if replace:
        os.replace(source, destination)
    else:
        if source.is_file():
            os.link(source, destination, follow_symlinks=False)
            source.unlink()
        else:
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(str(destination))
            os.rename(source, destination)
    sync_directory(destination.parent)


def durable_write_bytes(
    path: Path,
    data: bytes,
    *,
    create_only: bool,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.packctl-tmp-{uuid.uuid4().hex}"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        view = memoryview(data)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        if temporary.read_bytes() != data:
            raise OSError("durable write readback mismatch")
        durable_rename(
            temporary,
            path,
            replace=not create_only,
        )
        if path.read_bytes() != data:
            raise OSError("durable publish readback mismatch")
    finally:
        temporary.unlink(missing_ok=True)


def durable_write_json(
    path: Path,
    value: object,
    *,
    create_only: bool,
) -> bytes:
    data = canonical_json_bytes(value)
    durable_write_bytes(path, data, create_only=create_only)
    return data


def sync_tree(path: Path) -> None:
    path = Path(path)
    if path.is_file():
        _sync_file(path)
        return
    directories = [path]
    for child in sorted(path.rglob("*")):
        if child.is_file():
            _sync_file(child)
        elif child.is_dir():
            directories.append(child)
    if os.name != "nt":
        for directory in reversed(directories):
            sync_directory(directory)


def _sync_file(path: Path) -> None:
    mode = "r+b" if os.name == "nt" else "rb"
    original_mode: int | None = None
    if os.name == "nt":
        file_stat = path.stat()
        if file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
            original_mode = file_stat.st_mode
            path.chmod(original_mode | stat.S_IWRITE)
    try:
        with path.open(mode) as handle:
            os.fsync(handle.fileno())
    finally:
        if original_mode is not None:
            path.chmod(original_mode)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finding(
    code: str,
    *,
    severity: str = "error",
    path: str = "",
    line: int = 0,
    message: str,
    evidence: str,
) -> dict[str, object]:
    if severity not in SEVERITY_RANK:
        raise ValueError(f"Unsupported severity: {severity}")
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "line": int(line),
        "message": message,
        "evidence": evidence,
    }


def sort_findings(
    findings: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_RANK[str(item["severity"])],
            str(item["code"]),
            str(item["path"]),
            int(item["line"]),
            str(item["message"]),
        ),
    )


def verdict_for(findings: Iterable[dict[str, object]]) -> str:
    severities = {str(item["severity"]) for item in findings}
    if "error" in severities:
        return "FAIL"
    if "warning" in severities:
        return "WARN"
    return "PASS"


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    return result.stdout


def git_commit(root: Path) -> str:
    try:
        return git_output(root, "rev-parse", "HEAD").strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_tracked_files(root: Path) -> list[str]:
    # Mid-merge, git ls-files prints an unmerged path once per index stage
    # (up to three times); each tracked path is listed once, in sorted order.
    output = git_output(root, "ls-files", "-z")
    return sorted({item.replace("\\", "/") for item in output.split("\0") if item})


def git_is_dirty(root: Path) -> bool:
    try:
        return bool(git_output(root, "status", "--porcelain=v1", "-z"))
    except (OSError, subprocess.CalledProcessError):
        return True


def make_report(
    command: str,
    root: Path,
    findings: Iterable[dict[str, object]],
    *,
    checks: dict[str, object] | None = None,
    artifacts: dict[str, object] | None = None,
) -> dict[str, object]:
    ordered = sort_findings(findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "source_commit": git_commit(root),
        "verdict": verdict_for(ordered),
        "findings": ordered,
        "checks": checks or {},
        "artifacts": artifacts or {},
    }


def exit_code_for(report: dict[str, object]) -> int:
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict) and artifacts.get("exit_code") == 2:
        return 2
    return 1 if report["verdict"] == "FAIL" else 0


def posix_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_relative_contract_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\0" in value:
        return False
    if "\\" in value or value.startswith("/") or Path(value).drive:
        return False
    return ".." not in Path(value).parts


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def tree_digest(path: Path) -> str:
    if not path.exists():
        return "absent"
    if path.is_file():
        return sha256_file(path)
    entries = [
        (item.relative_to(path).as_posix(), sha256_file(item))
        for item in sorted(path.rglob("*"))
        if item.is_file()
    ]
    digest = hashlib.sha256()
    for relative, file_hash in entries:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()
