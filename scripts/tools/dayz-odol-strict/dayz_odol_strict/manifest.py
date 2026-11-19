import hashlib
import json
import os
from pathlib import Path
import re

from .errors import OdolStrictError


PINNED_MANIFEST_SHA256 = (
    "485852927678f79d9d7660ae194db009"
    "6bb5ba70faf90ca8aea00559903bd09a"
)
MANIFEST_SCHEMA = "odol-backend-manifest-v1"
BACKEND_API = "odol_reader.ODOL.from_bytes-v1"


def verify_backend_manifest(
    backend_root,
    manifest_path,
    expected_manifest_sha256=PINNED_MANIFEST_SHA256,
):
    root = Path(backend_root)
    path = Path(manifest_path)
    if not root.is_dir() or not path.is_file():
        raise OdolStrictError(
            "ODOL_BACKEND_MISSING",
            "backend root or manifest is unavailable",
        )
    root = root.resolve()
    try:
        manifest_bytes = path.read_bytes()
    except OSError:
        raise OdolStrictError(
            "ODOL_BACKEND_MISSING", "backend manifest is unavailable"
        )
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_hash != expected_manifest_sha256:
        _drift("backend manifest hash does not match the pinned identity")
    try:
        value = json.loads(manifest_bytes.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _drift("backend manifest is not strict UTF-8 JSON")
    if not isinstance(value, dict) or set(value) != {
        "api_id", "files", "manifest_id", "schema_version",
    }:
        _drift("backend manifest fields are invalid")
    if value["schema_version"] != MANIFEST_SCHEMA or \
            value["api_id"] != BACKEND_API or \
            not isinstance(value["manifest_id"], str) or \
            not value["manifest_id"]:
        _drift("backend manifest identity is invalid")
    files_value = value["files"]
    if not isinstance(files_value, list) or not files_value:
        _drift("backend manifest must pin at least one file")

    verified_files = []
    seen = set()
    for item in files_value:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            _drift("backend file entry is invalid")
        relative_text = item["path"]
        expected_hash = item["sha256"]
        if not isinstance(relative_text, str) or not relative_text or \
                "\\" in relative_text:
            _drift("backend file path must be a relative POSIX path")
        relative = Path(relative_text)
        if relative.is_absolute() or relative.drive or \
                any(part in ("", ".", "..") for part in relative.parts):
            _drift("backend file path escapes its root")
        if relative_text in seen:
            _drift("backend file paths must be unique")
        seen.add(relative_text)
        if not isinstance(expected_hash, str) or \
                re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
            _drift("backend file hash is invalid")
        candidate = (root / relative).resolve()
        try:
            contained = os.path.commonpath((root, candidate)) == os.fspath(
                root
            )
        except ValueError:
            contained = False
        if not contained:
            _drift("backend file resolves outside its root")
        if not candidate.is_file():
            raise OdolStrictError(
                "ODOL_BACKEND_MISSING",
                "a pinned backend file is unavailable",
            )
        try:
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError:
            raise OdolStrictError(
                "ODOL_BACKEND_MISSING",
                "a pinned backend file is unavailable",
            )
        if actual_hash != expected_hash:
            _drift("a pinned backend file hash changed")
        verified_files.append({
            "path": relative_text,
            "sha256": expected_hash,
        })
    if "odol_reader.py" not in seen:
        _drift("backend manifest does not pin odol_reader.py")
    return {
        "api_id": value["api_id"],
        "files": verified_files,
        "manifest_id": value["manifest_id"],
        "manifest_sha256": manifest_hash,
        "root": root,
    }


def _drift(message):
    raise OdolStrictError("ODOL_BACKEND_DRIFT", message)
